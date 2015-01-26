__author__ = 'bmordue'

import constants
import requests
import requests.exceptions
import json
import sqlite3
from bs4 import BeautifulSoup
from time import sleep


def populate():
    print 'Set up DB and add a row for each HN story'
    conn = sqlite3.connect(constants.DATABASE_FILENAME)
    c = conn.cursor()
    c.execute('''DROP TABLE IF EXISTS stories''')
    c.execute('''CREATE TABLE IF NOT EXISTS stories
             (hash TEXT UNIQUE, hnurl TEXT, url TEXT, added TEXT, comments INTEGER,
             starred BOOLEAN DEFAULT 1)''')

    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS, verify=constants.VERIFY)
    mycookies = r.cookies

    hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes',
                          cookies=mycookies, verify=constants.VERIFY)

    hashlist = hashes.json()['starred_story_hashes']

    print 'Size of hashlist is ' + str(len(hashlist))

    i = 0
    batch = []
    batchcounter = 0
    for ahash in hashlist:
        i += 1
        if i > constants.MAX_PARSE:
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
    print 'Finished adding story hashes to DB'


# Print 'Process a batch of hashes and add details to DB'
def process_batch(cookie_store, cursor, batch):
    req_str = constants.NB_ENDPOINT + '/reader/starred_stories?'

    for a_hash in batch:
        req_str += 'h=' + a_hash + '&'
    stories = requests.get(req_str, cookies=cookie_store, verify=constants.VERIFY)
    storylist = json.loads(stories.text)['stories']

    for story in storylist:
        if story['story_feed_id'] == constants.NB_HN_FEED_ID:
            hnurl = get_hn_url(story['story_content'])
            cursor.execute("INSERT INTO stories (hash, added, hnurl, url) VALUES (?, ?, ?, ?)",
                           (story['story_hash'], story['story_date'], hnurl, story['story_permalink'],))


# read through DB for rows without comment count, then add it
def add_comment_counts():
    print 'Add comment counts to stories in DB'
    conn = sqlite3.connect(constants.DATABASE_FILENAME)
    cursor = conn.cursor()

    cursor.execute("SELECT hnurl FROM stories WHERE comments IS NULL")
    rows = cursor.fetchall()
    for row in rows:
        url = row[0]
        count = get_comment_count(url)
        if count is not None:
            cursor.execute("UPDATE stories SET comments = ? WHERE hnurl = ?", (count, url))
            conn.commit()
    conn.close()
    print 'Finished adding comment counts'


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
        while (resp.status_code != 200):
            if resp.status_code in [403, 500, 503]:  # exponential backoff
                print "Request for %s returned %s response" % (url, resp.status_code)
                if backoff < constants.MAX_BACKOFF:
                    print "Backing off %s seconds" % backoff
                    sleep(backoff)
                    resp = requests.get(url, verify=constants.VERIFY)
                    backoff = backoff * constants.BACKOFF_FACTOR
                else:
                    print "Giving up after %s seconds for %s" % (backoff, url)
                    return None
            elif resp.status_code == 520:
                print "520 response, skipping %" % url
                return None
            else:
                print "Request for %s returned unhandled %s response" % (url, resp.status_code)
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        print "url is: %s" % url
        print e
        return None

    return on_success(resp)


# TODO: DEPRECATE in favour of request_with_backoff()
def get_comment_count(hnurl):
    comment_count = 0
    try:
        backoff = 5
        story = requests.get(hnurl, verify=constants.VERIFY)
        while (story.status_code != 200):
            if story.status_code in [403, 500, 503]:  # exponential backoff
                print "Request for %s returned %s response" % (hnurl, story.status_code)
                if backoff < constants.MAX_BACKOFF:
                    print "Backing off %s seconds" % backoff
                    sleep(backoff)
                    backoff = backoff * 2
                    story = requests.get(hnurl, verify=constants.VERIFY)
                else:
                    print "Giving up after %s seconds for %s" % (backoff, hnurl)
                    return None
            elif story.status_code == 520:
                print "520 response, skipping %" % hnurl
                return None
            else:
                print "Request for %s returned unhandled %s response" % (hnurl, story.status_code)
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        print "hnurl: " + hnurl
        print e
        return None
    comment_count = parse_story(story.text)
    return comment_count


# TODO: deprecate in favour of more generic function
def remove_star_with_backoff(story_hash, mycookies):
    try:
        backoff = constants.BACKOFF_START
        url = constants.NB_ENDPOINT + '/reader/mark_story_hash_as_unstarred'
        resp = requests.post(url,
                             {'story_hash': story_hash}, cookies=mycookies, verify=constants.VERIFY)
        while (resp.status_code != 200):
            if resp.status_code in [403, 500, 503]:  # exponential backoff
                print "Request for %s returned %s response" % (url, resp.status_code)
                if backoff < constants.MAX_BACKOFF:
                    print "Backing off %s seconds" % backoff
                    sleep(backoff)
                    backoff = backoff * constants.BACKOFF_FACTOR
                    resp = requests.post(url,
                             {'story_hash': story_hash}, cookies=mycookies, verify=constants.VERIFY)
                else:
                    print "Giving up after %s seconds for %s" % (backoff, url)
                    return False
            elif resp.status_code == 520:
                print "520 response, skipping %" % url
                return False
            else:
                print "Request for %s returned unhandled %s response" % (url, resp.status_code)
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        print "url is: %s" % url
        print e
        return False

    return True

# TODO: REMOVE - unused
def remove_star(story_hash, mycookies):
    requests.post(constants.NB_ENDPOINT + '/reader/mark_story_hash_as_unstarred',
                  {'story_hash': story_hash}, cookies=mycookies, verify=constants.VERIFY)
    return True


def prune_starred():
    print 'Remove all stars on stories with less than %i comments' % constants.COMMENTS_THRESHOLD

    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS, verify=constants.VERIFY)
    mycookies = r.cookies

    conn = sqlite3.connect(constants.DATABASE_FILENAME)
    cursor = conn.cursor()
    cursor.execute("SELECT hash FROM stories WHERE comments < ? AND starred = 1", (constants.COMMENTS_THRESHOLD,))
    rows = cursor.fetchall()
    count = 0
    for row in rows:
        if remove_star_with_backoff(row[0], mycookies):
            cursor.execute("UPDATE stories SET starred = 0 WHERE hash = ?", row)
            conn.commit()
            count += 1
    conn.commit()
    conn.close()
    print 'Removed %i out of %i candidate stars' % (count, len(rows))

    print 'Finished pruning stars'


def check_if_starred(story_hash):
    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS, verify=constants.VERIFY)
    mycookies = r.cookies
    hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes', cookies=mycookies,
                          verify=constants.VERIFY)
    hashlist = hashes.json()['starred_story_hashes']

    if story_hash in hashlist:
        return True
    else:
        return False


if __name__ == "__main__":
    print "__main__"
    import sys, os
    sys.stdout = open("nb.log", "w")
    if sys.argv[0]:
        constants.MAX_PARSE = sys.argv[0]
    if not os.path.isfile(constants.DATABASE_FILENAME):
        populate()
    add_comment_counts()
    # prune_starred()
    print 'Done.'
    sys.stdout = sys.__stdout__
