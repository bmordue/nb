__author__ = 'bmordue'

import constants
import requests
import requests.exceptions
import json
import sqlite3
from bs4 import BeautifulSoup
from time import sleep

if __name__ == "__main__":
    import sys
    import os

#    sys.stdout = open("nb.log", "w")
    if sys.argv[0]:
        constants.MAX_PARSE = sys.argv[0]
    if not os.path.isfile(constants.DATABASE_FILENAME):
        populate()
#    add_comment_counts()
    prune_starred()
    print 'Done.'
    sys.stdout = sys.__stdout__
