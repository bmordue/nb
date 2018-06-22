import time

from datadog import statsd

from connectors.DbConnector import DbConnector
from connectors.dynamo.DomainModel import DomainModel
from connectors.dynamo.StoryModel import StoryModel
from connectors.dynamo.ErrorModel import ErrorModel
from utility import nb_logging

logger = nb_logging.setup_logger('DynamoDbClient')


class DynamoDbClient(DbConnector):
    def add_comment_count(self, comments_url, count):
        stories = StoryModel.query(comments_url)
        for dummy in stories: #only want the first element...
            story = dummy
        story.comments = count
        story.save()
        statsd.increment('nb.comment_counts_added')

    def add_story(self, nb_hash, added, comments_url, story_url):
        story = StoryModel(comments_url, nb_hash=nb_hash, added=added, url=story_url)
        try:
            story.save()
        except Exception as err:
            logger.error("Caught exception while saving Story model, wait 2 sec and retry")
            statsd.event('Failed to save story', err.message, alert_type='error')
            time.sleep(2)
            story.save()
        statsd.increment('nb.stories_added')

    def close_connection(self): pass

    def ensure_domains_table_exists(self):
        DomainModel.create_table()

    def ensure_stories_table_exists(self):
        StoryModel.create_table()
        ErrorModel.create_table()

    def insert_domain_entry(self, nb_hash, nb_url, domain, toplevel, toplevel_new):
        domain = DomainModel(nb_hash, nb_url=nb_url, domain=domain, toplevel=toplevel, toplevel_new=toplevel_new)
        domain.save()
        statsd.increment('nb.domains_added')

    def list_stories_with_comments_fewer_than(self, threshold):
        stories = StoryModel.scan(StoryModel.comments < threshold and StoryModel.comments >= 0)
        return stories

    def list_stories_without_comment_count(self):
        stories = StoryModel.scan(StoryModel.comments == -1)
        return stories

    # select hash, url from stories
    def list_urls(self):
        stories = StoryModel.scan()
        return list(map(lambda s: {'nb_hash': s.nb_hash, 'url': s.url}, stories))

    def unstar(self, nb_hash):
        story = StoryModel.scan(StoryModel.nb_hash == nb_hash)
        story.starred = False
        story.update(
            actions=[
                StoryModel.starred.set(False)
            ]
        )
        statsd.increment('nb.stars_removed')

    @staticmethod
    def get_expiry_time():
        return int(time.time()) + 24*60*60

    def record_error(self, url, code, headers, body):
        error = ErrorModel(url, status_code=code, headers=headers, body=body,
                           ttl=DynamoDbClient.get_expiry_time())
        error.save()
        statsd.increment('nb.errors_recorded')
