from utility import constants, client_factory
from utility import nb_logging
import requests
import requests.exceptions
from time import sleep
from datadog import statsd

logger = nb_logging.setup_logger('prune')


# TODO: deprecate in favour of more generic function
# TODO: move statsd bucket names to constants.py
@statsd.timed('nb.prune.remove_star_with_backoff')
def remove_star_with_backoff(story_hash, mycookies):
    backoff = constants.BACKOFF_START
    unstar_url = constants.NB_ENDPOINT + '/reader/mark_story_hash_as_unstarred'
    try:
        resp = requests.post(unstar_url,
                             {'story_hash': story_hash}, cookies=mycookies, verify=constants.VERIFY)
        statsd.increment('nb.http_requests.post')
        while resp.status_code != 200:
            if resp.status_code in [403, 500, 503]:  # exponential backoff
                logger.info("Request for %s returned %s response" % (unstar_url, resp.status_code))
                if backoff < constants.BACKOFF_MAX:
                    logger.info("Backing off %s seconds" % backoff)
                    sleep(backoff)
                    backoff = backoff * constants.BACKOFF_FACTOR
                    resp = requests.post(unstar_url,
                                         {'story_hash': story_hash}, cookies=mycookies,
                                         verify=constants.VERIFY)
                    statsd.increment('nb.http_requests.post')
                else:
                    logger.warn("Giving up after %s seconds for %s" % (backoff, unstar_url))
                    return False
            elif resp.status_code == 520:
                logger.warn("520 response, skipping %s" % unstar_url)
                return False
            else:
                logger.error("Request for %s returned unhandled %s response" %
                             (unstar_url, resp.status_code))
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        logger.info("url is: %s" % unstar_url)
        logger.error(e)
        return False

    return True


@statsd.timed('nb.prune.prune_starred')
def prune_starred():
    logger.info('Remove all stars on stories with less than {0} comments'.format(
        constants.COMMENTS_THRESHOLD))

    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS,
                      verify=constants.VERIFY)
    statsd.increment('nb.http_requests.post')
    mycookies = r.cookies

    db_client = client_factory.get_db_client()
    rows = db_client.list_stories_with_comments_fewer_than(constants.COMMENTS_THRESHOLD)

    removed = 0
    candidates = 0
    for row in rows:
        candidates += 1
        if remove_star_with_backoff(row[0], mycookies):
            db_client.unstar(row[0])
            removed += 1
    logger.info('Successfully removed {0} out of {1} candidate stars'.format(removed, candidates))
    db_client.close_connection()
    logger.info('Finished pruning stars')


@statsd.timed('nb.prune.check_if_starred')
def check_if_starred(story_hash):
    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS,
                      verify=constants.VERIFY)
    statsd.increment('nb.http_requests.post')
    mycookies = r.cookies
    hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes', cookies=mycookies,
                          verify=constants.VERIFY)
    statsd.increment('nb.http_requests.get')
    hashlist = hashes.json()['starred_story_hashes']

    if story_hash in hashlist:
        return True
    else:
        return False
