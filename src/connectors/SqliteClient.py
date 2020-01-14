import warnings

import sqlite3
from datadog import statsd

from connectors.DbConnector import DbConnector
from utility import nb_logging
from utility.NbConfig import NbConfig

import rollbar

logger = nb_logging.setup_logger('SqliteClient')

STATSD_PREFIX = 'nb.SqliteClient.'


class SqliteClient(DbConnector):
    def __init__(self):
        DbConnector.__init__(self)
        db_file = 'nb.sqlite'
        logger.info("Attempt to connect to DB file %s", db_file)
        self.conn = sqlite3.connect(db_file)

    def ensure_domains_table_exists(self):
        create_table_query = '''CREATE TABLE IF NOT EXISTS domains
                 (id INTEGER UNIQUE NOT NULL AUTO_INCREMENT, nb_hash VARCHAR(64) UNIQUE, 
                 domain VARCHAR(128), PRIMARY KEY (id), toplevel VARCHAR(128), 
                 toplevel_new VARCHAR(128), FOREIGN KEY (nb_hash) REFERENCES stories (hash) ) 
                 CHARACTER SET utf8'''

        cursor = self.execute_wrapper(create_table_query)
        cursor.close()
        self.conn.commit()
        logger.info('Executed table creation query')

    @statsd.timed(STATSD_PREFIX + 'list_urls')
    def list_urls(self):
        cursor = self.execute_wrapper("SELECT hash, url FROM stories")
        rows = cursor.fetchall()
        cursor.close()
        logger.info('Found %s results.', len(rows))
        return rows

    @statsd.timed(STATSD_PREFIX + 'insert_domain_entry')
    def insert_domain_entry(self, nb_hash, nb_url, domain, toplevel, toplevel_new):
        cursor = self.execute_wrapper(
            '''INSERT IGNORE INTO domains (nb_hash, domain, toplevel, toplevel_new) VALUES 
            (%s, %s, %s, %s)''',
            (nb_hash, domain, toplevel, toplevel_new))
        cursor.close()
        self.conn.commit()
        logger.info('Added domain entry for %s', domain)

    def close_connection(self):
        self.conn.close()

    @statsd.timed(STATSD_PREFIX + 'list_stories_with_comments_fewer_than')
    def list_stories_with_comments_fewer_than(self, threshold):
        cursor = self.execute_wrapper("SELECT hash FROM stories WHERE comments < %s AND starred = 1", (threshold,))
        rows = cursor.fetchall()
        cursor.close()
        logger.info('Found %s starred stories with fewer than %s comments', len(rows), threshold)
        return rows

    @statsd.timed(STATSD_PREFIX + 'unstar')
    def unstar(self, nb_hash):
        cursor = self.execute_wrapper("UPDATE stories SET starred = 0 WHERE hash = %s", (nb_hash,))
        cursor.close()
        self.conn.commit()

    def ensure_stories_table_exists(self):
        table_setup_query = '''CREATE TABLE IF NOT EXISTS stories
             (hash VARCHAR(64) UNIQUE, hnurl TEXT, url TEXT, added TEXT, comments INTEGER,
             starred BOOLEAN DEFAULT 1) CHARACTER SET utf8'''

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cursor = self.execute_wrapper(table_setup_query)
        cursor.close()
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'add_story')
    def add_story(self, nb_hash, added, comments_url, story_url):
        insert_story_query = '''INSERT IGNORE INTO stories (hash, added, hnurl, url) VALUES (%s, %s, %s, %s)'''
        cursor = self.execute_wrapper(insert_story_query, (nb_hash, added, comments_url, story_url))
        cursor.close()
        self.conn.commit()
        logger.info('Added story (%s)', nb_hash)

    @statsd.timed(STATSD_PREFIX + 'list_stories_without_comment_count')
    def list_stories_without_comment_count(self):
        query = '''SELECT hnurl FROM stories WHERE comments IS NULL'''
        cursor = self.execute_wrapper(query)
        rows = cursor.fetchall()
        cursor.close()
        return list(rows)

    @statsd.timed(STATSD_PREFIX + 'add_comment_count')
    def add_comment_count(self, comments_url, count):
        query = '''UPDATE stories SET comments = %s WHERE hnurl = %s'''
        cursor = self.execute_wrapper(query, (count, comments_url))
        cursor.close()
        self.conn.commit()
        logger.info('Added comment count for %s (%s)', comments_url, count)

    def record_error(self, url, code, headers, body):
        pass

    def ensure_config_table_exists(self):
        table_setup_query = '''CREATE TABLE IF NOT EXISTS config
            (config_key VARCHAR(64) UNIQUE, config_value TEXT)
             CHARACTER SET utf8'''
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            cursor = self.execute_wrapper(table_setup_query)
        cursor.close()
        self.conn.commit()

    def read_config(self):
        query = '''SELECT * FROM config'''
        cursor = self.execute_wrapper(query)
        cursor.close()
        rows = cursor.fetchall()
        return NbConfig(dict(rows))

    def write_config(self, config):
        query = '''REPLACE INTO config (config_key, config_value) VALUES (%s, %s)'''
        for key in config:
            cursor = self.execute_wrapper(query, (key, config[key]))
        cursor.close()
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'add_hashes')
    def add_hashes(self, hashes):
        query = '''REPLACE INTO story_hashes VALUES (%s)'''
        cursor = self.conn.cursor()
        for a_hash in hashes:
            cursor.execute(query, a_hash)
        cursor.close()
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'read_hashes')
    def read_hashes(self, count):
        query = '''SELECT * FROM story_hashes WHERE processed <> 1 LIMIT %s'''
        cursor = self.conn.cursor()
        rows = cursor.execute(query, count)
        cursor.close()
        return rows

    @statsd.timed(STATSD_PREFIX + 'mark_story_done')
    def mark_story_done(self, story_hash):
        query = '''UPDATE story_hashes SET processed = 1 WHERE hash = %s'''
        cursor = self.conn.cursor()
        cursor.execute(query, story_hash)
        cursor.close()
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'list_comment_count_update_candidates')
    def list_comment_count_update_candidates(self):
        # modified - added < 7 days (comment window) AND now - modified > 1 hr (update interval)
        query = '''SELECT hnurl FROM stories WHERE comments IS NULL'''
        cursor = self.conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        return list(rows)

    def execute_wrapper(self, query_str, query_params=None):
        cursor = self.conn.cursor()
        try:
            cursor.execute(query_str, query_params)
        except sqlite3.Error:
            logger.error('Failed to execute sqlite3 query: {}', query_str)
        return cursor
