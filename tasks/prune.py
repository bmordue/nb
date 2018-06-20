from utility import constants, client_factory
from utility import nb_logging
from datadog import statsd
import connectors.NewsblurConnector

logger = nb_logging.setup_logger('prune')


@statsd.timed('nb.prune.prune_starred')
def prune_starred():
    logger.info('Remove all stars on stories with less than %s comments', constants.COMMENTS_THRESHOLD)

    db_client = client_factory.get_db_client()
    rows = db_client.list_stories_with_comments_fewer_than(constants.COMMENTS_THRESHOLD)
    nb_client = NewsblurConnector()
    nb_client.connect()

    removed = 0
    candidates = 0
    for row in rows:
        candidates += 1
        if nb_client.remove_star_with_backoff(row.nb_hash):
            db_client.unstar(row.nb_hash)
            removed += 1
    logger.info('Successfully removed %s out of %s candidate stars', removed, candidates)
    db_client.close_connection()
    logger.info('Finished pruning stars')
