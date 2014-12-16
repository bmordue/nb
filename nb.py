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

    print 'Size of hashlist is ' + str(len(hashlist))   # 3254

    i = 0
    batch = []
    batchcounter = 0
    for hash in hashlist:
        i += 1
        if (i > constants.MAX_PARSE):
            break
        if (batchcounter > constants.BATCH_SIZE):
            processBatch(mycookies, c, batch)
            conn.commit()
            batchcounter = 0
            batch = []
        batchcounter += 1
        batch.append(hash)
    processBatch(mycookies, c, batch)
    conn.commit()
    conn.close()

# Print 'Process a batch of hashes and add details to DB'
def processBatch(cookieStore, cursor, batch):
    reqStr = constants.NB_ENDPOINT + '/reader/starred_stories?'

    for hash in batch:
        reqStr += 'h=' + hash + '&'
    stories = requests.get(reqStr, cookies=cookieStore)
    storylist = json.loads(stories.text)['stories']

    for story in storylist:
        if (story['story_feed_id'] == constants.NB_HN_FEED_ID):
            hnurl = getHNUrl(story['story_content'])
            coCo = getCommentCount(hnurl)

            cursor.execute("INSERT INTO stories (hash, added, hnurl, url, comments) VALUES (?, ?, ?, ?, ?)",
                           (story['story_hash'], story['story_date'], hnurl, story['story_permalink'], coCo,))


def getHNUrl(content):
    return content.split('"')[1]

# Parse HN story to find how many comments there are
# Aargh: HN stories are not well-formed XML.
def parseStory(content):
    index = content.find("comments")
#   TODO: fill in the blanks: hop back a few characters, tokenize, take (len-1)th token
    sub = content[index-5:index] #assume <100k comments
    commentCount = sub.split()[-1]
    return 0 #commentCount

def getCommentCount(hnurl):
    commentCount = 0

    theStory = requests.get(hnurl)
    commentCount = parseStory(theStory.text)

    return commentCount


def commentCounts():
    print 'Assuming DB has been populated, add comment counts for each entry'


if __name__ == "__main__":
    print "__main__"
    populate()
    commentCounts()
