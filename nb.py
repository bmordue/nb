__author__ = 'bmordue'

import constants
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
    import sys
    import os

    # sys.stdout = open("nb.log", "w")
    # if sys.argv[1]:
    #     constants.MAX_PARSE = sys.argv[1]
    # if not os.path.isfile(constants.DATABASE_FILENAME):
    #     populate()
    populate()
    add_comment_counts()
    prune_starred()
    print 'Done.'
    sys.stdout = sys.__stdout__
