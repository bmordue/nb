__author__ = 'ben'

import os

NB_ENDPOINT = 'https://newsblur.com'
NB_HN_FEED_ID = 6
#DATABASE_FILENAME = 'stories.sqlite'
DB_HOST = os.getenv('DB_HOST','stage.benmordue.co.uk')
# DB_PORT = 5432
DB_USER = os.getenv('DB_USER','No username')
DB_PASS = os.getenv('DB_PASS','No password')
DB_NAME = 'nb_stories'
MAX_PARSE = 9 # max number of Newsblur starred stories to process
BATCH_SIZE = 10 # how many batches to parse and enter in DB in one go
NB_USERNAME = os.getenv('NB_USERNAME','No username')
NB_PASSWORD = os.getenv('NB_PASSWORD','No password')
NB_CREDENTIALS = {'username': NB_USERNAME, 'password': NB_PASSWORD}
COMMENTS_THRESHOLD = 20
VERIFY = True # useful to set to False to use with Charles proxy, but this generates loadsa warnings
BACKOFF_MAX = 24*60*60  # in seconds
BACKOFF_START = 5
BACKOFF_FACTOR = 2
BACKOFF_ON_520 = 30
