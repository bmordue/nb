from ddtrace import patch_all

from tasks.populate import populate
from tasks.add_comment_counts import add_comment_counts
from tasks.prune import prune_starred
from tasks.add_domains import add_domains
from utility.NbConfig import NbConfig

from utility import client_factory
from utility import nb_logging
import rollbar

patch_all()

rollbar.init('00b402fc0da54ed1af8687d4c4389911')
logger = nb_logging.setup_logger('NB')

if __name__ == "__main__":
    db_client = client_factory.get_db_client()
    db_client.ensure_config_table_exists()
    config = db_client.read_config()
    
    # if config.get('SHOULD_POPULATE'):
    #     populate()
    if config.get('SHOULD_ADD_DOMAINS'):
        add_domains()
    if config.get('SHOULD_ADD_COMMENT_COUNTS'):
        add_comment_counts()
    if config.get('SHOULD_PRUNE_STARRED'):
        prune_starred()
    logger.info('Done.')
