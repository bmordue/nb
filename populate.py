__author__ = 'bmordue'

import constants
import logging
logger = logging.getLogger('NB')

import requests
import requests.exceptions
import json
# import sqlite3
from bs4 import BeautifulSoup
from time import sleep
import MySQLdb

INSERT_HASH_QUERY='''REPLACE INTO stories (hash, added, hnurl, url) VALUES (%s, %s, %s, %s)'''

TABLE_SETUP_QUERY='''CREATE TABLE IF NOT EXISTS stories
             (hash VARCHAR(64) UNIQUE, hnurl TEXT, url TEXT, added TEXT, comments INTEGER,
             starred BOOLEAN DEFAULT 1)'''

def populate():
    logger.info('Set up DB and add a row for each HN story')
    conn = MySQLdb.connect (host = constants.DB_HOST,
                            user = constants.DB_USER,
                            passwd = constants.DB_PASS,
                            db = constants.DB_NAME)
    c = conn.cursor()

    c.execute(TABLE_SETUP_QUERY)

    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS, verify=constants.VERIFY)
    mycookies = r.cookies

    hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes',
                          cookies=mycookies, verify=constants.VERIFY)

    hashlist = hashes.json()['starred_story_hashes']

    logger.info('Size of hashlist is ' + str(len(hashlist)))

    i = 0
    batch = []
    batchcounter = 0
    for ahash in hashlist:
        i += 1
        if i > constants.MAX_PARSE:
            logger.info('Reached MAX_PARSE ({0})'.format(constants.MAX_PARSE))
            break
        if batchcounter > constants.BATCH_SIZE:
            process_batch(mycookies, c, batch)
            conn.commit()
            batchcounter = 0
            batch = []
        batchcounter += 1
        batch.append(ahash)
    process_batch(mycookies, c, batch)
    conn.commit()
    conn.close()
    logger.info('Finished adding story hashes to DB')


# Print 'Process a batch of hashes and add details to DB'
def process_batch(cookie_store, cursor, batch):
    req_str = constants.NB_ENDPOINT + '/reader/starred_stories?'

    for a_hash in batch:
        req_str += 'h=' + a_hash + '&'
    stories = requests.get(req_str, cookies=cookie_store, verify=constants.VERIFY)
    try:
        storylist = json.loads(stories.text)['stories']

        for story in storylist:
            if story['story_feed_id'] == constants.NB_HN_FEED_ID:
                hnurl = get_hn_url(story['story_content'])
                # thehash = str(story['story_hash'])
                # date = str(story['story_date'])
                # link = str(story['story_permalink'])
                # print "%s; %s; %s; %s " % (thehash, date, hnurl, link,)
                # cursor.execute('''REPLACE INTO stories (hash, added, hnurl, url) VALUES (%s, %s, %s, %s)''', (thehash, date, hnurl, link,))
                cursor.execute(INSERT_HASH_QUERY, (story['story_hash'], story['story_date'], hnurl, story['story_permalink'],))
    except ValueError as e:
        logger.error('Failed to get stories for request {0}'.format(req_str))
        logger.error(e)

                           

# read through DB for rows without comment count, then add it
def add_comment_counts():
    logger.info('Add comment counts to stories in DB')
    conn = MySQLdb.connect (host = constants.DB_HOST,
                            user = constants.DB_USER,
                            passwd = constants.DB_PASS,
                            db = constants.DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT hnurl FROM stories WHERE comments IS NULL")
    rows = cursor.fetchall()
    for row in rows:
        url = row[0]
        count = get_comment_count(url)
        if count is not None:
            cursor.execute("UPDATE stories SET comments = %s WHERE hnurl = %s", (count, url))
            conn.commit()
    conn.close()
    logger.info('Finished adding comment counts')


def get_hn_url(content):
    return content.split('"')[1]


# Parse HN story to find how many comments there are
def parse_story(content):
    soup = BeautifulSoup(content)
    comment_count = len(soup.find_all("span", {"class": "comment"}))
    return comment_count


# eg request_with_backoff(url, on_success)
# eg request_with_backoff(hnurl, parse_story)
# Hmm. Falls down on POSTs. :-( Needs more treatment
# TODO: cf requests PreparedRequest!
def get_with_backoff(url, on_success):
    try:
        backoff = constants.BACKOFF_START
        resp = requests.get(url, verify=constants.VERIFY)
        while resp.status_code != 200:
            if resp.status_code in [403, 500, 503]:  # exponential backoff
                logger.debug("Request for {0} returned {1} response".format(url, resp.status_code))
                if backoff < constants.BACKOFF_MAX:
                    logger.debug("Backing off {0} seconds".format(backoff))
                    sleep(backoff)
                    resp = requests.get(url, verify=constants.VERIFY)
                    backoff = backoff * constants.BACKOFF_FACTOR
                else:
                    logger.debug("Giving up after {0} seconds for {1}".format(backoff, url))
                    return None
            elif resp.status_code == 520:
                logger.debug("520 response, skipping {0} and waiting {1} sec".format(url, constants.BACKOFF_ON_520))
                sleep(constants.BACKOFF_ON_520)
                return None
            else:
                logger.debug("Request for {0} returned unhandled {1} response".format(url, resp.status_code))
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        logger.error("url is: {0}".format(url))
        logger.error(e)
        return None

    return on_success(resp)


# TODO: DEPRECATE in favour of request_with_backoff()
def get_comment_count(hnurl):
    try:
        backoff = 5
        story = requests.get(hnurl, verify=constants.VERIFY)
        while story.status_code != 200:
            if story.status_code in [403, 500, 503]:  # exponential backoff
                logger.debug("Request for {0} returned {1} response".format(hnurl, story.status_code))
                if backoff < constants.MAX_BACKOFF:
                    logger.debug("Backing off {0} seconds".format(backoff))
                    sleep(backoff)
                    backoff *= constants.BACKOFF_FACTOR
                    story = requests.get(hnurl, verify=constants.VERIFY)
                else:
                    logger.debug("Giving up after {0} seconds for {1}".format(backoff, hnurl))
                    return None
            elif story.status_code == 520:
                logger.debug("520 response, skipping {0}".format(hnurl))
                return None
            else:
                logger.debug("Request for {0} returned unhandled {1} response".format(hnurl, story.status_code))
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        logger.error("hnurl: {0}".format(hnurl)
        logger.error(e)
        return None
    return parse_story(story.text)

