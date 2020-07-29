from connectors.NewsblurConnector import NewsblurConnector
from utility import client_factory
from utility import nb_logging
from datadog import statsd

logger = nb_logging.setup_logger('prune')


@statsd.timed('nb.prune.prune_starred')
def prune_starred():
    db_client = client_factory.get_db_client()
    config = db_client.read_config()
    rows = db_client.list_stories_with_comments_fewer_than(int(config.get('COMMENTS_THRESHOLD')))
    nb_client = client_factory.get_newsblur_client()
    nb_client.login()

    logger.info('Remove all stars on stories with fewer than %s comments', config.get('COMMENTS_THRESHOLD'))

    removed = 0
    candidates = 0
    for row in rows:
        candidates += 1
        if nb_client.remove_star_with_backoff(row[0]):
            db_client.unstar(row[0])
            statsd.increment('nb.prune.stars_removed')
            removed += 1
    logger.info('Successfully removed %s out of %s candidate stars', removed, candidates)
    db_client.close_connection()
    logger.info('Finished pruning stars')
