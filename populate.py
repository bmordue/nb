__author__ = 'bmordue'

import constants
import requests
import requests.exceptions
import json
import sqlite3
from bs4 import BeautifulSoup
from time import sleep

INSERT_HASH_QUERY='''INSERT OR REPLACE INTO stories (hash, added, hnurl, url) VALUES (?, ?, ?, ?)'''


def populate():
    print 'Set up DB and add a row for each HN story'
    conn = sqlite3.connect(constants.DATABASE_FILENAME)
    c = conn.cursor()

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
            cursor.execute(INSERT_HASH_QUERY, (story['story_hash'], story['story_date'], hnurl, story['story_permalink'],))
                           

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
        while resp.status_code != 200:
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
                print "520 response, skipping %s" % url
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
    try:
        backoff = 5
        story = requests.get(hnurl, verify=constants.VERIFY)
        while story.status_code != 200:
            if story.status_code in [403, 500, 503]:  # exponential backoff
                print "Request for %s returned %s response" % (hnurl, story.status_code)
                if backoff < constants.MAX_BACKOFF:
                    print "Backing off %s seconds" % backoff
                    sleep(backoff)
                    backoff *= constants.BACKOFF_FACTOR
                    story = requests.get(hnurl, verify=constants.VERIFY)
                else:
                    print "Giving up after %s seconds for %s" % (backoff, hnurl)
                    return None
            elif story.status_code == 520:
                print "520 response, skipping %s" % hnurl
                return None
            else:
                print "Request for %s returned unhandled %s response" % (hnurl, story.status_code)
                raise requests.exceptions.RequestException()
    except requests.exceptions.RequestException as e:
        print "hnurl: " + hnurl
        print e
        return None
    return parse_story(story.text)


