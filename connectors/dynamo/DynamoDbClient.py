import time

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

    def add_story(self, nb_hash, added, comments_url, story_url):
        story = StoryModel(comments_url, nb_hash=nb_hash, added=added, url=story_url)
        try:
            story.save()
        except Exception:
            logger.error("Caught exception while saving Story model, wait 1 sec and retry\n")
            time.sleep(1)
            story.save()

    def close_connection(self): pass

    def ensure_domains_table_exists(self):
        DomainModel.create_table()

    def ensure_stories_table_exists(self):
        StoryModel.create_table()
        ErrorModel.create_table()

    def insert_domain_entry(self, nb_hash, nb_url, domain, toplevel, toplevel_new):
        domain = DomainModel(nb_hash, nb_url=nb_url, domain=domain, toplevel=toplevel, toplevel_new=toplevel_new)
        domain.save()

    def list_stories_with_comments_fewer_than(self, threshold):
        stories = StoryModel.scan(StoryModel.comments < threshold)
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
        
    def record_error(self, url, code, headers=None, body=None):
        error = ErrorModel(url, status_code=code, headers=headers, body=body)
        error.save()
