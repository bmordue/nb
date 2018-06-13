import json
from time import sleep

import requests
import requests.exceptions
from bs4 import BeautifulSoup
from datadog import statsd

from utility import constants, client_factory
from utility import nb_logging

logger = nb_logging.setup_logger('populate')


@statsd.timed('nb.populate.populate')
def populate():
    logger.info('Set up DB and add a row for each HN story')

    db_client = client_factory.get_db_client()
    db_client.ensure_stories_table_exists()
    db_client.close_connection()

    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS,
                      verify=constants.VERIFY)
    statsd.increment('nb.http_requests.post')
    mycookies = r.cookies

    hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes',
                          cookies=mycookies, verify=constants.VERIFY)
    statsd.increment('nb.http_requests.get')
    hashlist = hashes.json()['starred_story_hashes']

    logger.info('Size of hashlist is ' + str(len(hashlist)))

    i = 0
    count_batches = 0
    batch = []
    batchcounter = 0
    for ahash in hashlist:
        i += 1
        if i > constants.MAX_PARSE:
            logger.info('Reached MAX_PARSE ({0})'.format(constants.MAX_PARSE))
            break
        if batchcounter > constants.BATCH_SIZE:
            process_batch(mycookies, batch)
            count_batches += 1
            batchcounter = 0
            batch = []
        batchcounter += 1
        batch.append(ahash)
    process_batch(mycookies, batch)
    count_batches += 1
    logger.info('Finished adding story hashes to DB.')
    logger.info('Processed {0} hashes in {1} batches.'.format(i, count_batches))


# Process a batch of hashes and add details to DB
@statsd.timed('nb.populate.process_batch')
def process_batch(cookie_store, batch):
    # logger.debug("Processing batch: {0}".format(batch))
    req_str = constants.NB_ENDPOINT + '/reader/starred_stories?'

    db_client = client_factory.get_db_client()

    for a_hash in batch:
        req_str += 'h=' + a_hash + '&'
    stories = requests.get(req_str, cookies=cookie_store, verify=constants.VERIFY)
    statsd.increment('nb.http_requests.get')
    try:
        storylist = json.loads(stories.text)['stories']
        # logger.debug("Story list: {0}".format(storylist))

        for story in storylist:
            if story['story_feed_id'] == constants.NB_HN_FEED_ID:
                hnurl = get_hn_url(story['story_content'])
                db_client.add_story(story['story_hash'], story['story_date'], hnurl,
                                    story['story_permalink'])
    except ValueError as e:
        logger.error('Failed to get stories for request {0}'.format(req_str))
        logger.error(e)
        statsd.event('Failed to get stories', e.message, alert_type='error')
        logger.debug(stories.text)

    db_client.close_connection()


# read through DB for rows without comment count, then add it
@statsd.timed('nb.populate.add_comment_counts')
def add_comment_counts():
    logger.info('Add comment counts to stories in DB')
    db_client = client_factory.get_db_client()
    rows = db_client.list_stories_without_comment_count()
    for row in rows:
        url = row.hnurl
        count = get_comment_count(url)
        logger.debug("Count for {0} is {1}".format(url, count))
        if count is not None:
            db_client.add_comment_count(url, count)
    logger.info('Finished adding comment counts')


def get_hn_url(content):
    return content.split('"')[1]


# Parse HN story to find how many comments there are
@statsd.timed('nb.populate.parse_story')
def parse_story(content):
    soup = BeautifulSoup(content)
    comment_count = len(soup.find_all("div", {"class": "comment"}))
    return comment_count


# eg request_with_backoff(url, on_success)
# eg request_with_backoff(hnurl, parse_story)
# Hmm. Falls down on POSTs. :-( Needs more treatment
# TODO: cf requests PreparedRequest!
@statsd.timed('nb.populate.get_with_backoff')
def get_with_backoff(url, on_success):
    db_client = client_factory.get_db_client()
    try:
        backoff = constants.BACKOFF_START
        resp = requests.get(url, verify=constants.VERIFY)
        statsd.increment('nb.http_requests.get')
        while resp.status_code != 200:
            db_client.record_error(url, resp.status_code, str(resp.headers), resp.text)
            if resp.status_code in [403, 500, 503]:  # exponential backoff
                logger.debug("Request for {0} returned {1} response".format(url, resp.status_code))
                if backoff < constants.BACKOFF_MAX:
                    logger.debug("Backing off {0} seconds".format(backoff))
                    sleep(backoff)
                    resp = requests.get(url, verify=constants.VERIFY)
                    statsd.increment('nb.http_requests.get')
                    backoff = backoff * constants.BACKOFF_FACTOR
                else:
                    logger.debug("Giving up after {0} seconds for {1}".format(backoff, url))
                    return None
            elif resp.status_code == 520:
                logger.info("520 response, skipping {0} and waiting {1} sec"
                            .format(url, constants.BACKOFF_ON_520))
                logger.debug("Response headers: {0}".format(resp.headers))
                logger.debug("Response body: {0}".format(resp.text))
                sleep(constants.BACKOFF_ON_520)
                return None
            else:
                logger.debug(
                    "Request for {0} returned unhandled {1} response".format(url, resp.status_code))
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        logger.error("url is: {0}".format(url))
        logger.error(e)
        statsd.event('Request failed', e.message, alert_type='error')
        return None

    return on_success(resp)


# TODO: DEPRECATE in favour of request_with_backoff()
@statsd.timed('nb.populate.get_comment_count')
def get_comment_count(hnurl):
    db_client = client_factory.get_db_client()
    db_client.ensure_stories_table_exists()
    try:
        backoff = 5
        story = requests.get(hnurl, verify=constants.VERIFY)
        statsd.increment('nb.http_requests.get')
        while story.status_code != 200:
            db_client.record_error(hnurl, story.status_code, str(story.headers), story.text)
            if story.status_code in [403, 429, 500, 503]:  # exponential backoff
                logger.debug(
                    "Request for {0} returned {1} response".format(hnurl, story.status_code))
                logger.debug("{0}".format(story.text))
                logger.debug("{0}".format(story.headers))
                if backoff < constants.BACKOFF_MAX:
                    logger.debug("Backing off {0} seconds".format(backoff))
                    sleep(backoff)
                    backoff *= constants.BACKOFF_FACTOR
                    story = requests.get(hnurl, verify=constants.VERIFY)
                    statsd.increment('nb.http_requests.get')
                else:
                    logger.debug("Giving up after {0} seconds for {1}".format(backoff, hnurl))
                    return None
            elif story.status_code in [520]:
                logger.debug(
                    "520 response for {0}; waiting {1} sec".format(hnurl, constants.BACKOFF_ON_520))
                logger.debug("Response headers: {0}".format(story.headers))
                logger.debug("Response body: {0}".format(story.text))
                sleep(constants.BACKOFF_ON_520)
                return None
            else:
                logger.debug("Request for {0} returned unhandled {1} response"
                             .format(hnurl, story.status_code))
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        logger.error("hnurl: {0}".format(hnurl))
        logger.error(e)
        statsd.event('Page render error!', e.message, alert_type='error')
        return None

    return parse_story(story.text)