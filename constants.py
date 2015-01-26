__author__ = 'ben'

import os

NB_ENDPOINT = 'https://newsblur.com'
NB_HN_FEED_ID = 6
DATABASE_FILENAME = 'stories.sqlite'
MAX_PARSE = 5000 # max number of Newsblur starred stories to process
BATCH_SIZE = 10 # how many batches to parse and enter in DB in one go
NB_USERNAME = os.getenv('NB_USERNAME','No username')
NB_PASSWORD = os.getenv('NB_PASSWORD','No password')
NB_CREDENTIALS = {'username': NB_USERNAME, 'password': NB_PASSWORD}
COMMENTS_THRESHOLD = 20
VERIFY = True # useful to set to False to use with Charles proxy, but this generates loadsa warnings
MAX_BACKOFF = 24*60*60  # in seconds
BACKOFF_START = 5
BACKOFF_FACTOR = 2