__author__ = 'bmordue'

import requests
import json
import sqlite3

nb = 'https://newsblur.com'
HN_FEED_ID = 6
credentials = {'username': 'bmordue', 'password': 'tester'}
commentsXPath = "/x:html/x:body/x:center/x:table/x:tbody/x:tr[3]/x:td/x:table[1]/x:tbody/x:tr[2]/x:td[2]/x:a[2]/text()"


def populate():
    print 'Set up DB and add a row for each HN story'
    conn = sqlite3.connect('stories.db')
    c = conn.cursor()
    c.execute('''DROP TABLE IF EXISTS stories''')
    c.execute('''CREATE TABLE IF NOT EXISTS stories
             (hash text, hnurl text, url text, added text, comments integer)''')
    conn.commit()
    conn.close()

    #    credentials = {'username':'bmordue','password':'tester'}

    r = requests.post(nb + '/api/login', credentials)
    mycookies = r.cookies

    hashes = requests.get(nb + '/reader/starred_story_hashes', cookies=mycookies)

    hashlist = hashes.json()['starred_story_hashes']

    #     firsthash = {'h':hashlist[0]}
    #     firststory = requests.get(nb+'/reader/starred_stories',cookies=mycookies,data=firsthash)
    #     print firststory.text

    #     storylist = []
    #     for page in range(1,10):
    #         resp = requests.get(nb+'/reader/starred_stories&p='+str(page), cookies=mycookies)
    #         storylist = storylist + json.loads(resp.text)['stories']
    #
    #     hn = []
    #     for story in storylist:
    #          if (story['story_feed_id']==HN_FEED_ID):
    # #             hn.append(story)
    #             c.execute("INSERT INTO stories (hash, added, url) VALUES (?, ?, ?)",(story['story_hash'],story['story_date'],story['story_permalink'],))
    print 'Size of hashlist is ' + str(len(hashlist))   # 3254

    MAX_PARSE = 5000
    BATCH_SIZE = 10
    i = 0
    batch = []
    batchcounter = 0
    for hash in hashlist:
        i += 1
        if (i > MAX_PARSE):
            break
        if (batchcounter > BATCH_SIZE):
            processBatch(mycookies, c, batch)
            batchcounter = 0
            batch = []
        batchcounter += 1
        batch.append(hash)
    processBatch(mycookies, c, batch)
    conn.commit()
    conn.close()

#         stories = requests.get(nb+'/reader/starred_stories',cookies=mycookies,data={'h':hash})
#         storylist = json.loads(stories.text)['stories']
#         for story in storylist:
#             if (story['story_feed_id']==HN_FEED_ID):     #  and story['story_hash']==hash)
#                 c.execute("INSERT INTO stories (hash, added, url) VALUES (?, ?, ?)",(story['story_hash'],story['story_date'],story['story_permalink'],))
#                 conn.commit()


def processBatch(cookieStore, cursor, batch):
#    print 'Process a batch of hashes and add details to DB'
    reqStr = nb + '/reader/starred_stories?'
    #    conn = sqlite3.connect('stories.db')
    #    c = conn.cursor()

    #    r = requests.post(nb+'/api/login',credentials)
    #    mycookies = r.cookies

    for hash in batch:
        reqStr += 'h=' + hash + '&'
    #    print ('reqStr: %s', reqStr)
    stories = requests.get(reqStr, cookies=cookieStore)
    storylist = json.loads(stories.text)['stories']
    #    print ('len(storylist): %s', len(storylist))
    for story in storylist:
        if (story['story_feed_id'] == HN_FEED_ID):     #  and story['story_hash']==hash)
            hnurl = getHNUrl(story['story_content'])
            coCo = getCommentCount(hnurl)

            cursor.execute("INSERT INTO stories (hash, added, hnurl, url, comments) VALUES (?, ?, ?, ?, ?)",
                           (story['story_hash'], story['story_date'], hnurl, story['story_permalink'], coCo,))

#            conn.commit()
#    conn.close()


def getHNUrl(content):
    return content.split('"')[1]

# Parse HN story to find how many comments there are
# Aargh: HN stories are not well-formed XML.
def parseStory(content):
    index = content.find("comments")
#   TODO: fill in the blanks: hop back a few characters, tokenize, take (len-1)th token
    sub = comments[index-5:index] #assume <100k comments
    commentCount = sub.split()[-1]
    return commentCount

def getCommentCount(hnurl):
    commentCount = 0
    #url = ''
    #stories = requests.get(nb + '/reader/starred_stories', cookies=mycookies, data=storyHash)
    #for story in stories:
    #    if (story['story_hash'] == storyHash):
    #        url = getHNUrl(story['story_content'])

    theStory = requests.get(hnurl)
    commentCount = parseStory(theStory.text)

    return commentCount


def commentCounts():
    print 'Assuming DB has been populated, add comment counts for each entry'


if __name__ == "__main__":
    populate()
    commentCounts()