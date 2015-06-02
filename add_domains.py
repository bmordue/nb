__author__ = 'bmordue'

import constants
import logging
logger = logging.getLogger('NB')

# import requests
# import requests.exceptions
# import json
# # import sqlite3
# from bs4 import BeautifulSoup
# from time import sleep
import MySQLdb


def add_domains():
    CREATE_TABLE_QUERY='''CREATE TABLE IF NOT EXISTS domains
                 (id INTEGER UNIQUE NOT NULL AUTO_INCREMENT, nb_hash VARCHAR(64), domain TEXT UNIQUE, PRIMARY KEY (id), FOREIGN KEY nb_hash REFERENCES stories(hash))'''
    
    conn = MySQLdb.connect (host = constants.DB_HOST,
                            user = constants.DB_USER,
                            passwd = constants.DB_PASS,
                            db = constants.DB_NAME)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_QUERY)

    cursor.execute("SELECT hash, url FROM stories", (constants.COMMENTS_THRESHOLD,))
    rows = cursor.fetchall()
    logger.debug('Found {0} results.'.format(len(rows)))

    for row in rows:
        domain = row[1].split('/')[2]
        nb_hash = row[0]
        logger.debug('Domain is {0}'.format(domain))
        cursor.execute('''INSERT IGNORE INTO domains (nb_hash, domain) VALUES (%s, %s)''', (nb_hash, domain,))
        conn.commit()
            # count += 1
    # conn.commit()
    conn.close()

if __name__ == "__main__":
    add_domains()