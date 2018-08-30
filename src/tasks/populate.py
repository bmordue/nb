from datadog import statsd

import time
from utility import client_factory
from utility import nb_logging

from connectors.NewsblurConnector import NewsblurConnector

logger = nb_logging.setup_logger('populate')
config = None


@statsd.timed('nb.populate.populate')
def populate():
    logger.info('Set up DB and add a row for each HN story')

    db_client = client_factory.get_db_client()
    db_client.ensure_stories_table_exists()
    config = db_client.read_config()
    db_client.close_connection()

    nb_client = NewsblurConnector(config)
    nb_client.connect()
    hashlist = nb_client.get_nb_hash_list()

    logger.info('Size of hashlist is %s', len(hashlist))

    batch_size = int(config.get('BATCH_SIZE'))
    logger.debug('Batch size is %s', batch_size)

    i = 0
    count_batches = 0
    batch = []
    batchcounter = 0
    for ahash in hashlist:
        i += 1
        if i >= int(config.get('MAX_PARSE')):
            logger.info('Reached MAX_PARSE (%s)', config.get('MAX_PARSE'))
            break
        if batchcounter >= batch_size:
	    logger.debug('Process batch of %s', batch_size)
            process_batch_with_retries(nb_client.get_story_list(batch), config)
            count_batches += 1
            batchcounter = 0
            batch = []
        batchcounter += 1
        batch.append(ahash)
    logger.debug('Process final batch of %s', len(batch))
    process_batch(nb_client.get_story_list(batch), config)
    count_batches += 1
    logger.info('Finished adding story hashes to DB.')
    logger.info('Processed %s hashes in %s batches.', i, count_batches)

@statsd.timed('nb.populate.process_batch_with_retries')
def process_batch_with_retries(story_list, config):
    process_batch(story_list, config)
#    for backoff in backoff_gen():
#	try:
#	    process_batch(story_list, config)
#	    break
#	except e:
#	    logger.debug('Failed to process batch for %s; backing off % sec', story_list, backoff)
#	    time.sleep(backoff)

def backoff_gen():
    for i in range(0, 4):
        yield 10*(i**2)

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
    statsd.increment('nb.stories.batches_processed')
    db_client.close_connection()

def get_hn_url(content):
    return content.split('"')[1]
