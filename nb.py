__author__ = 'bmordue'

import requests
import json
import sqlite3
import constants


def populate():
    print 'Set up DB and add a row for each HN story'
    conn = sqlite3.connect(constants.DATABASE_NAME)
    c = conn.cursor()
    c.execute('''DROP TABLE IF EXISTS stories''')
    c.execute('''CREATE TABLE IF NOT EXISTS stories
             (hash text, hnurl text, url text, added text, comments integer)''')

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
            count = get_comment_count(hnurl)

            cursor.execute("INSERT INTO stories (hash, added, hnurl, url, comments) VALUES (?, ?, ?, ?, ?)",
                           (story['story_hash'], story['story_date'], hnurl, story['story_permalink'], count,))


def get_hn_url(content):
    return content.split('"')[1]


# Parse HN story to find how many comments there are
# Aargh: HN stories are not well-formed XML.
def parse_story(content):
    index = content.find("comments")
    # TODO: fill in the blanks: hop back a few characters, tokenize, take (len-1)th token
    sub = content[index - 5:index]  # assume <100k comments
    comment_count = sub.split()[-1]
    return 0  # comment_count


def get_comment_count(hnurl):
    comment_count = 0

    story = requests.get(hnurl)
    comment_count = parse_story(story.text)

    return comment_count


def comment_counts():
    print 'Assuming DB has been populated, add comment counts for each entry'


if __name__ == "__main__":
    print "__main__"
    populate()
    comment_counts()
