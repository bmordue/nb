class DbConnector:
    def __init__(self):
        pass

    def add_comment_count(self, comments_url, count):
        raise NotImplementedError

    def add_story(self, nb_hash, added, comments_url, story_url):
        raise NotImplementedError

    def close_connection(self):
        raise NotImplementedError

    def ensure_domains_table_exists(self):
        raise NotImplementedError

    def ensure_stories_table_exists(self):
        raise NotImplementedError

    def insert_domain_entry(self, nb_hash, nb_url, domain, toplevel, toplevel_new):
        raise NotImplementedError

    def list_stories_with_comments_fewer_than(self, threshold):
        raise NotImplementedError

    def list_stories_without_comment_count(self):
        raise NotImplementedError

    def list_urls(self):
        raise NotImplementedError

    def unstar(self, nb_hash):
        raise NotImplementedError

    def record_error(self, url, code, headers, body):
        raise NotImplementedError

    def ensure_config_table_exists(self):
        raise NotImplementedError

    def read_config(self):
        raise NotImplementedError
