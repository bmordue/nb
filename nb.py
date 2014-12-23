__author__ = 'bmordue'

import constants
import requests
import json
import sqlite3
from bs4 import BeautifulSoup


def populate():
    print 'Set up DB and add a row for each HN story'
    conn = sqlite3.connect(constants.DATABASE_NAME)
    c = conn.cursor()
    c.execute('''DROP TABLE IF EXISTS stories''')
    c.execute('''CREATE TABLE IF NOT EXISTS stories
             (hash TEXT UNIQUE, hnurl TEXT, url TEXT, added TEXT, comments INTEGER)''')

    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS)
    mycookies = r.cookies

    hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes', cookies=mycookies)

    hashlist = hashes.json()['starred_story_hashes']

    print 'Size of hashlist is ' + str(len(hashlist))  # 3254

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


# Print 'Process a batch of hashes and add details to DB'
def process_batch(cookie_store, cursor, batch):
    req_str = constants.NB_ENDPOINT + '/reader/starred_stories?'

    for a_hash in batch:
        req_str += 'h=' + a_hash + '&'
    stories = requests.get(req_str, cookies=cookie_store)
    storylist = json.loads(stories.text)['stories']

    for story in storylist:
        if story['story_feed_id'] == constants.NB_HN_FEED_ID:
            hnurl = get_hn_url(story['story_content'])
            cursor.execute("INSERT INTO stories (hash, added, hnurl, url) VALUES (?, ?, ?, ?)",
                           (story['story_hash'], story['story_date'], hnurl, story['story_permalink'],))


# read through DB for rows without comment count, then add it
def add_comment_counts():
    conn = sqlite3.connect(constants.DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT hnurl FROM stories WHERE comments IS NULL")
    rows = cursor.fetchall()
    for row in rows:
        url = row[0]
        count = get_comment_count(url)
        cursor.execute("UPDATE stories SET comments = ? WHERE hnurl = ?", (count, url))

    conn.commit()
    conn.close()


def get_hn_url(content):
    return content.split('"')[1]


# Parse HN story to find how many comments there are
def parse_story(content):
    soup = BeautifulSoup(content)
    comment_count = len(soup.find_all("span", {"class": "comment"}))
    return comment_count


def get_comment_count(hnurl):
    comment_count = 0
    try:
        story = requests.get(hnurl)
        comment_count = parse_story(story.text)
    except requests.exceptions.RequestException as e:
        print "hnurl: " + hnurl
        print e
    return comment_count


def remove_favourite(story_hash):
    print ('Remove story with hash %s from NB favourites', story_hash)
    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS)
    mycookies = r.cookies
    resp = requests.post(constants.NB_ENDPOINT + '/reader/mark_story_hash_as_unstarred', {'story_hash':story_hash},cookies=mycookies)


def prune_favourites():
    conn = sqlite3.connect(constants.DATABASE_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT hash FROM stories WHERE (comments < ?)", (constants.COMMENTS_THRESHOLD,))
    rows = cursor.fetchall()
    for row in rows:
        remove_favourite(row[0])

    conn.commit()
    conn.close()


def check_if_favourite(story_hash):
    r = requests.post(constants.NB_ENDPOINT + '/api/login', constants.NB_CREDENTIALS)
    mycookies = r.cookies
    hashes = requests.get(constants.NB_ENDPOINT + '/reader/starred_story_hashes', cookies=mycookies)
    hashlist = hashes.json()['starred_story_hashes']

    if story_hash in hashlist:
        return True
    else:
        return False


if __name__ == "__main__":
    print "__main__"
    populate()
    add_comment_counts()
    prune_favourites()
