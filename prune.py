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
from statsd import StatsdTimer
import statsd

# TODO: deprecate in favour of more generic function
# TODO: move statsd bucket names to constants.py
@StatsdTimer.wrap('nb.prune.remove_star_with_backoff')
def remove_star_with_backoff(story_hash, mycookies):
    backoff = constants.BACKOFF_START
    unstar_url = constants.NB_ENDPOINT + '/reader/mark_story_hash_as_unstarred'
    try:
        resp = requests.post(unstar_url,
                             {'story_hash': story_hash}, cookies=mycookies, verify=constants.VERIFY)
        statsd.incr('nb.http_requests.post')
        while resp.status_code != 200:
            if resp.status_code in [403, 500, 503]:  # exponential backoff
                print "Request for %s returned %s response" % (unstar_url, resp.status_code)
                if backoff < constants.MAX_BACKOFF:
                    print "Backing off %s seconds" % backoff
                    sleep(backoff)
                    backoff = backoff * constants.BACKOFF_FACTOR
                    resp = requests.post(unstar_url,
                                         {'story_hash': story_hash}, cookies=mycookies, verify=constants.VERIFY)
                    statsd.incr('nb.http_requests.post')
                else:
                    print "Giving up after %s seconds for %s" % (backoff, unstar_url)
                    return False
            elif resp.status_code == 520:
                print "520 response, skipping %s" % unstar_url
                return False
            else:
                print "Request for %s returned unhandled %s response" % (unstar_url, resp.status_code)
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        print "url is: %s" % unstar_url
        print e
        return False

    return True


# TODO: REMOVE - unused
# def remove_star(story_hash, mycookies):
#     requests.post(constants.NB_ENDPOINT + '/reader/mark_story_hash_as_unstarred',
#                   {'story_hash': story_hash}, cookies=mycookies, verify=constants.VERIFY)
#     return True


@StatsdTimer.wrap('nb.prune.prune_starred')
def prune_starred():
    logger.info('Remove all stars on stories with less than {0} comments'.format(constants.COMMENTS_THRESHOLD))

    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS, verify=constants.VERIFY)
    statsd.incr('nb.http_requests.post')
    mycookies = r.cookies

    conn = MySQLdb.connect (host = constants.DB_HOST,
                            user = constants.DB_USER,
                            passwd = constants.DB_PASS,
                            db = constants.DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT hash FROM stories WHERE comments < %s AND starred = 1", (constants.COMMENTS_THRESHOLD,))
    rows = cursor.fetchall()
    logger.info('Found {0} candidates for removal.'.format(len(rows)))
    count = 0
    for row in rows:
        if remove_star_with_backoff(row[0], mycookies):
            cursor.execute("UPDATE stories SET starred = 0 WHERE hash = %s", row)
            conn.commit()
            count += 1
    conn.commit()
    conn.close()
    logger.info('Removed {0} out of {1} candidate stars'.format(count, len(rows)))

    logger.info('Finished pruning stars')


@StatsdTimer.wrap('nb.prune.check_if_starred')
def check_if_starred(story_hash):
    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS, verify=constants.VERIFY)
    statsd.incr('nb.http_requests.post')
    mycookies = r.cookies
    hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes', cookies=mycookies,
                          verify=constants.VERIFY)
    statsd.incr('nb.http_requests.get')
    hashlist = hashes.json()['starred_story_hashes']

    if story_hash in hashlist:
        return True
    else:
        return False

