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
#        logger.info("Attempt to connect to DB file %s", db_file)
        self.conn = sqlite3.connect(db_file)

    def ensure_domains_table_exists(self):
        create_table_query = '''CREATE TABLE IF NOT EXISTS domains
                 (id INTEGER PRIMARY KEY ASC, nb_hash TEXT UNIQUE,
                 domain TEXT, toplevel TEXT,
                 toplevel_new TEXT, FOREIGN KEY (nb_hash) REFERENCES stories (hash) )'''

        self.execute_wrapper(create_table_query)
        self.conn.commit()
        logger.info('Executed table creation query')

    @statsd.timed(STATSD_PREFIX + 'list_urls')
    def list_urls(self):
        cursor = self.execute_wrapper("SELECT hash, url FROM stories")
        rows = cursor.fetchall()
        logger.info('Found %s results.', len(rows))
        return rows

    @statsd.timed(STATSD_PREFIX + 'insert_domain_entry')
    def insert_domain_entry(self, nb_hash, nb_url, domain, toplevel, toplevel_new):
        self.execute_wrapper(
            '''INSERT OR IGNORE INTO domains (nb_hash, domain, toplevel, toplevel_new) VALUES
            (?, ?, ?, ?)''',
            (nb_hash, domain, toplevel, toplevel_new))
        self.conn.commit()
#        logger.info('Added domain entry for %s', domain)

    def close_connection(self):
        pass
        #self.conn.close() #TODO: FIX

    @statsd.timed(STATSD_PREFIX + 'list_stories_with_comments_fewer_than')
    def list_stories_with_comments_fewer_than(self, threshold):
        cursor = self.execute_wrapper("SELECT hash FROM stories WHERE comments < ? AND starred = 1", (threshold,))
        rows = cursor.fetchall()
        logger.info('Found %s starred stories with fewer than %s comments', len(rows), threshold)
        return rows

    @statsd.timed(STATSD_PREFIX + 'unstar')
    def unstar(self, nb_hash):
        self.execute_wrapper("UPDATE stories SET starred = 0 WHERE hash = ?", (nb_hash,))
        self.conn.commit()

    def ensure_stories_table_exists(self):
        table_setup_query = '''CREATE TABLE IF NOT EXISTS stories
             (hash TEXT UNIQUE, hnurl TEXT, url TEXT, added TEXT, comments INTEGER,
             starred BOOLEAN DEFAULT 1)'''

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.execute_wrapper(table_setup_query)
        self.conn.commit()

        table_setup_query = '''CREATE TABLE IF NOT EXISTS story_hashes (hash TEXT UNIQUE, locked BOOLEAN DEFAULT 0,
              processed BOOLEAN DEFAULT 0, created DATETIME DEFAULT CURRENT_TIMESTAMP, modified DATETIME DEFAULT CURRENT_TIMESTAMP)'''

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.execute_wrapper(table_setup_query)
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'add_story')
    def add_story(self, nb_hash, added, comments_url, story_url):
        insert_story_query = '''INSERT OR IGNORE INTO stories (hash, added, hnurl, url) VALUES (?, ?, ?, ?)'''
        self.execute_wrapper(insert_story_query, (nb_hash, added, comments_url, story_url))
        self.conn.commit()
#        logger.debug('Added story (%s)', nb_hash)

    @statsd.timed(STATSD_PREFIX + 'list_stories_without_comment_count')
    def list_stories_without_comment_count(self):
        query = '''SELECT hnurl FROM stories WHERE comments IS NULL'''
        cursor = self.execute_wrapper(query)
        rows = cursor.fetchall()
        return rows

    @statsd.timed(STATSD_PREFIX + 'add_comment_count')
    def add_comment_count(self, comments_url, count):
        query = '''UPDATE stories SET comments = ? WHERE hnurl = ?'''
        self.execute_wrapper(query, (count, comments_url))
        self.conn.commit()
        logger.info('Added comment count for %s (%s)', comments_url, count)

    def record_error(self, url, code, headers, body):
        pass

    def ensure_config_table_exists(self):
        table_setup_query = '''CREATE TABLE IF NOT EXISTS config
            (config_key TEXT UNIQUE, config_value TEXT)'''
        self.execute_wrapper(table_setup_query)
        self.conn.commit()

    def read_config(self):
        query = '''SELECT * FROM config'''
        cursor = self.execute_wrapper(query)
        rows = cursor.fetchall()
        return NbConfig(dict(rows))

    def write_config(self, config):
        query = '''REPLACE INTO config (config_key, config_value) VALUES (?, ?)'''
        for key in config:
            self.execute_wrapper(query, (key, config[key]))
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'add_hashes')
    def add_hashes(self, hashes):
        query = '''REPLACE INTO story_hashes (hash) VALUES (?)'''
        for a_hash in hashes:
            self.execute_wrapper(query, (a_hash,))
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'read_hashes')
    def read_hashes(self, count):
        query = '''SELECT hash FROM story_hashes WHERE processed <> 1 LIMIT {0}'''.format(count)
#        count = count if count is not None else 20
        logger.debug("read %s hashes query: %s", count, query)
#        cursor = self.execute_wrapper(query, count)
        cursor = self.execute_wrapper(query)
        return cursor.fetchall()

    @statsd.timed(STATSD_PREFIX + 'mark_story_done')
    def mark_story_done(self, story_hash):
        query = '''UPDATE story_hashes SET processed = 1 WHERE hash = ?'''
        self.execute_wrapper(query, (story_hash,))
        self.conn.commit()

    @statsd.timed(STATSD_PREFIX + 'list_comment_count_update_candidates')
    def list_comment_count_update_candidates(self):
        # modified - added < 7 days (comment window) AND now - modified > 1 hr (update interval)
        query = '''SELECT hnurl FROM stories WHERE comments IS NULL'''
        cursor = self.execute_wrapper(query)
        rows = cursor.fetchall()
        return rows

    def execute_wrapper(self, query_str, query_params=None):
        cursor = self.conn.cursor()
        try:
            if query_params is not None:
                cursor.execute(query_str, query_params)
            else:
                cursor.execute(query_str)
        except sqlite3.Error as e:
            logger.error('Failed to execute_wrapper sqlite3 query: %s', query_str)
            logger.error('execute_wrapper, query_params: %s', query_params)
            logger.error('execute_wrapper sqlite3.Error: %s', e.args[0])
        return cursor

