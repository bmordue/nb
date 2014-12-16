__author__ = 'ben'

NB_ENDPOINT = 'https://newsblur.com'
NB_HN_FEED_ID = 6
NB_CREDENTIALS = {'username': 'bmordue', 'password': 'tester'}
DATABASE_NAME = 'stories.sqlite'
MAX_PARSE = 50 # max number of Newsblur starred stories to process
BATCH_SIZE = 10 # how many batches to parse and enter in DB in one go
