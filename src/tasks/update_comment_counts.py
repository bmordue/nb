from datadog import statsd

from utility import client_factory
from utility import nb_logging

logger = nb_logging.setup_logger('update_comment_counts')


# update comment counts for stories that might have had comments added:
# last updated is older than threshold
# comments are still open on story
@statsd.timed('nb.populate.update_comment_counts')
def update_comment_counts():
    logger.info('Update comment counts to stories in DB')
    db_client = client_factory.get_db_client()

    # TODO: write this method in db_client
    rows = db_client.list_comment_count_update_candidates()

    logger.debug('Found %s candidates for updating comment count', len(rows))
    nb_client = client_factory.get_newsblur_client()
    nb_client.login()

    for row in rows:
        url = row[0]
        count = nb_client.get_comment_count(url)
        logger.debug("Count for %s is %s", url, count)
        if count is not None:
            db_client.add_comment_count(url, count)
            statsd.increment('nb.add_comment_counts.comment_counts_added')
    logger.info('Finished updating comment counts')
