from datadog import statsd
from utility import client_factory
from utility import nb_logging

logger = nb_logging.setup_logger('populate')


@statsd.timed('nb.populate.update_hash_list')
def update_hash_list():
    logger.info('Get full list of NB story hashes')

    nb_client = client_factory.get_newsblur_client()
    nb_client.login()
    hash_list = nb_client.get_nb_hash_list()
    logger.info('Size of hashlist retrieved from Newsblur is %s', len(hash_list))
    db_client = client_factory.get_db_client()
    db_client.add_hashes(hash_list)


@statsd.timed('nb.populate.populate')
def populate():
    logger.info('Add a row for each HN story')

    db_client = client_factory.get_db_client()
    db_client.ensure_stories_table_exists()
    config = db_client.read_config()
    db_client.close_connection()

    nb_client = client_factory.get_newsblur_client()
    nb_client.login()

    batch_size = int(config.get('BATCH_SIZE'))
    logger.debug('Batch size is %s', batch_size)
    logger.debug('MAX_PARSE is %s', config.get('MAX_PARSE'))

    i = 0
    count_batches = 0
    while i < int(config.get('MAX_PARSE')):
        batch = db_client.read_hashes(batch_size)
        if not batch:
            logger.warn('No batch (batch %s)', i)
            break
        count_batches += 1
        i += len(batch)
        logger.debug('Process batch of %s', len(batch))
        process_batch_with_retries(nb_client.get_story_list(batch), config)
    logger.info('Finished adding story hashes to DB.')
    logger.info('Processed %s hashes in %s batches.', i, count_batches)


@statsd.timed('nb.populate.process_batch_with_retries')
def process_batch_with_retries(story_list, config):
    process_batch(story_list, config)


def backoff_gen():
    for i in range(0, 4):
        yield 10 * (i ** 2)


# Process a batch of hashes and add details to DB
@statsd.timed('nb.populate.process_batch')
def process_batch(story_list, config):
    db_client = client_factory.get_db_client()
    for story in story_list:
        if story['story_feed_id'] == int(config.get('NB_HN_FEED_ID')):
            hnurl = get_hn_url(story['story_content'])
            db_client.add_story(story['story_hash'], story['story_date'], hnurl,
                                story['story_permalink'])
            statsd.increment('nb.stories_added')
        db_client.mark_story_done(story['story_hash'])
    statsd.increment('nb.stories.batches_processed')
    db_client.close_connection()


def get_hn_url(content):
    return content.split('"')[1]
