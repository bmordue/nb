__author__ = 'ben'

import os

NB_ENDPOINT = 'https://newsblur.com'
NB_HN_FEED_ID = 6
DATABASE_NAME = 'stories.sqlite'
MAX_PARSE = 50 # max number of Newsblur starred stories to process
BATCH_SIZE = 10 # how many batches to parse and enter in DB in one go
NB_USERNAME = os.getenv('NB_USERNAME','No username')
NB_PASSWORD = os.getenv('NB_PASSWORD','No password')
NB_CREDENTIALS = {'username': NB_USERNAME, 'password': NB_PASSWORD}
COMMENTS_THRESHOLD = 20