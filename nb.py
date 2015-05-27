__author__ = 'bmordue'

import constants
import nb_logging
# import requests
# import requests.exceptions
# import json
# # import sqlite3
# from bs4 import BeautifulSoup
# from time import sleep

from populate import populate
from populate import add_comment_counts
from prune import prune_starred

if __name__ == "__main__":

    # sys.stdout = open("nb.log", "w")
    # if sys.argv[1]:
    #     constants.MAX_PARSE = sys.argv[1]
    # if not os.path.isfile(constants.DATABASE_FILENAME):
    #     populate()
    
    logger = nb_logging.setup_logger('NB')
    
    populate()
    add_comment_counts()
    prune_starred()
    logger.info('Done.')
