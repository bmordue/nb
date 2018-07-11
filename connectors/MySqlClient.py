import warnings

import MySQLdb

from datadog import statsd
from ddtrace import patch_all

from connectors.DbConnector import DbConnector
from utility import nb_logging

logger = nb_logging.setup_logger('MySqlClient')
patch_all()
STATSD_PREFIX = 'nb.MySqlClient.'


class MySqlClient(DbConnector):
    def __init__(self, host, user, password, db_name):
        DbConnector.__init__(self)
        self.host = host
        self.user = user
        self.password = password
        self.db_name = db_name

        self.conn = MySQLdb.connect(host=self.host,
                                    user=self.user,
                                    passwd=self.password,
                                    db=self.db_name)

    def ensure_domains_table_exists(self):
        create_table_query = '''CREATE TABLE IF NOT EXISTS domains
                 (id INTEGER UNIQUE NOT NULL AUTO_INCREMENT, nb_hash VARCHAR(64) UNIQUE, 
                 domain VARCHAR(128), PRIMARY KEY (id), toplevel VARCHAR(128), 
                 toplevel_new VARCHAR(128), FOREIGN KEY (nb_hash) REFERENCES stories (hash) ) 
                 CHARACTER SET utf8'''

        cursor = self.conn.cursor()
        cursor.execute(create_table_query)
        cursor.close()
        self.conn.commit()
        logger.info('Executed table creation query')

    @statsd.timed(STATSD_PREFIX + 'list_urls')
    def list_urls(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT hash, url FROM stories")
        rows = cursor.fetchall()
        cursor.close()
        logger.info('Found %s results.', len(rows))
        return rows

    @statsd.timed(STATSD_PREFIX + 'insert_domain_entry')
    def insert_domain_entry(self, nb_hash, nb_url, domain, toplevel, toplevel_new):
        cursor = self.conn.cursor()
        cursor.execute(
            '''INSERT IGNORE INTO domains (nb_hash, domain, toplevel, toplevel_new) VALUES 
            (%s, %s, %s, %s)''',
            (nb_hash, domain, toplevel, toplevel_new))
        cursor.close()
        self.conn.commit()

    def close_connection(self):
        self.conn.close()
        logger.debug('Closed database connection')

    @statsd.timed(STATSD_PREFIX + 'list_stories_with_comments_fewer_than')
    def list_stories_with_comments_fewer_than(self, threshold):
        cursor = self.conn.cursor()
        cursor.execute("SELECT hash FROM stories WHERE comments < %s AND starred = 1", (threshold,))
        rows = cursor.fetchall()
        cursor.close()
        logger.info('Found %s starred stories with fewer than %s comments', len(rows), threshold)
        return rows

    @statsd.timed(STATSD_PREFIX + 'unstar')
    def unstar(self, nb_hash):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE stories SET starred = 0 WHERE hash = %s", (nb_hash,))
        cursor.close()
        self.conn.commit()

    def ensure_stories_table_exists(self):
        table_setup_query = '''CREATE TABLE IF NOT EXISTS stories
             (hash VARCHAR(64) UNIQUE, hnurl TEXT, url TEXT, added TEXT, comments INTEGER,
             starred BOOLEAN DEFAULT 1) CHARACTER SET utf8'''

        cursor = self.conn.cursor()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cursor.execute(table_setup_query)
        cursor.close()
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'add_story')
    def add_story(self, nb_hash, added, comments_url, story_url):
        insert_story_query = '''INSERT IGNORE INTO stories (hash, added, hnurl, url) VALUES (%s, %s, %s, %s)'''
        cursor = self.conn.cursor()
        cursor.execute(insert_story_query, (nb_hash, added, comments_url, story_url))
        cursor.close()
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'list_stories_without_comment_count')
    def list_stories_without_comment_count(self):
        query = '''SELECT hnurl FROM stories WHERE comments IS NULL'''
        cursor = self.conn.cursor()
        cursor.execute(query)
        cursor.close()
        return cursor.fetchall()

    @statsd.timed(STATSD_PREFIX + 'add_comment_count')
    def add_comment_count(self, comments_url, count):
        query = '''UPDATE stories SET comments = %s WHERE hnurl = %s'''
        cursor = self.conn.cursor()
        cursor.execute(query, (count, comments_url))
        cursor.close()
        self.conn.commit()

    def record_error(self, url, code, headers, body):
        pass
