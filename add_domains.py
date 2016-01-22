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
                 (id INTEGER UNIQUE NOT NULL AUTO_INCREMENT, nb_hash VARCHAR(64) UNIQUE, domain VARCHAR(128), PRIMARY KEY (id), toplevel VARCHAR(128),
                 toplevel_new VARCHAR(128),
                   FOREIGN KEY (nb_hash) REFERENCES stories (hash) )'''
    
    conn = MySQLdb.connect (host = constants.DB_HOST,
                            user = constants.DB_USER,
                            passwd = constants.DB_PASS,
                            db = constants.DB_NAME)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_QUERY)

    cursor.execute("SELECT hash, url FROM stories")
    rows = cursor.fetchall()
    logger.debug('Found {0} results.'.format(len(rows)))

    for row in rows:
        domain = row[1].split('/')[2]
    	toplevel = '.'.join(domain.split('.')[-2:])
    	if domain.split('.').len > 2:
    	    toplevel_new = '.'.join(domain.split('.')[1:])
        nb_hash = row[0]
        logger.debug('Domain is {0}'.format(domain))
        if toplevel != toplevel_new:
            logger.debug('toplevel: {0}; toplevel_new" {1}'.format(toplevel, toplevel_new))
        cursor.execute('''INSERT IGNORE INTO domains (nb_hash, domain, toplevel, toplevel_new) VALUES (%s, %s, %s, %s)''', (nb_hash, domain, toplevel,toplevel_new))
    conn.commit()
            # count += 1
    # conn.commit()
    conn.close()

if __name__ == "__main__":
    add_domains()
