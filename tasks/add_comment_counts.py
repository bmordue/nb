from datadog import statsd

from utility import client_factory
from utility import nb_logging

from connectors.NewsblurConnector import NewsblurConnector

import exceptions

logger = nb_logging.setup_logger('add_comment_counts')


# read through DB for rows without comment count, then add it
@statsd.timed('nb.populate.add_comment_counts')
def add_comment_counts():
    logger.info('Add comment counts to stories in DB')
    db_client = client_factory.get_db_client()
    rows = db_client.list_stories_without_comment_count()
    nb_client = NewsblurConnector()
    nb_client.connect()

    try:
        for row in rows:
            url = row.hnurl
            count = nb_client.get_comment_count(url)
            logger.debug("Count for %s is %s", url, count)
            if count is not None:
                db_client.add_comment_count(url, count)
        logger.info('Finished adding comment counts')
    except Exception as e:
        logger.exception("This IP appears to be blacklisted")
        statsd.event('BlacklistedError', e.message, alert_type='error')
