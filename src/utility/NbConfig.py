import os

class NbConfig:
    defaults = {
        'NB_ENDPOINT': 'https://newsblur.com',
        'NB_HN_FEED_ID': '5982259',
        'DB_HOST': os.getenv('DB_HOST','not set'),
        'DB_USER': os.getenv('DB_USER','No username'),
        'DB_PASS': os.getenv('DB_PASS','No password'),
        'DB_NAME': 'nb',
        'MAX_PARSE': '40000', # max number of Newsblur starred stories to process
        'BATCH_SIZE': '10', # how many batches to parse and enter in DB in one go
        'NB_USERNAME': os.getenv('NB_USERNAME','No username'),
        'NB_PASSWORD': os.getenv('NB_PASSWORD','No password'),
        'COMMENTS_THRESHOLD': '20',
        'VERIFY': 'True', # useful to set to False to use with Charles proxy, but this generates loadsa warnings
        'BACKOFF_MAX': '120',  # in seconds,
        'BACKOFF_START': '5',
        'BACKOFF_FACTOR': '2',
        'BACKOFF_ON_520': '10',
        'POLITE_WAIT': '1', # seconds between requests, even if not rate-limited
        'SHOULD_POPULATE': 'True',
        'SHOULD_ADD_COMMENT_COUNTS': 'True',
        'SHOULD_ADD_DOMAINS': 'True',
        'SHOULD_PRUNE_STARRED': 'True'
    }

    def __init__(self, config = None):
        if config is None:
            config = {}
        self.config = config
        self.set_defaults()

    def set_defaults(self):
        for key in self.defaults:
            if key not in self.config:
                self.config[key] = self.defaults[key]

    def get(self, key):
        return self.config[key]
