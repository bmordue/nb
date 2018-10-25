from datadog import statsd

from utility import client_factory
from utility import nb_logging

from connectors.NewsblurConnector import NewsblurConnector

logger = nb_logging.setup_logger('add_comment_counts')


# read through DB for rows without comment count, then add it
@statsd.timed('nb.populate.add_comment_counts')
def add_comment_counts():
    logger.info('Add comment counts to stories in DB')
    db_client = client_factory.get_db_client()
    rows = db_client.list_stories_without_comment_count()
    logger.debug('Found %s rows', len(rows))
    nb_client = client_factory.get_newsblur_client()
    nb_client.login()

    for row in rows:
        #        url = row.hnurl
        url = row[0]
        count = nb_client.get_comment_count(url)
        logger.debug("Count for %s is %s", url, count)
        if count is not None:
            db_client.add_comment_count(url, count)
            statsd.increment('nb.add_comment_counts.comment_counts_added')
    logger.info('Finished adding comment counts')
