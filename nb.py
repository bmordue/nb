#from ddtrace import patch_all
#patch_all()

from tasks.populate import populate
from tasks.add_comment_counts import add_comment_counts
from tasks.prune import prune_starred
from tasks.add_domains import add_domains
from utility import nb_logging
import rollbar

rollbar.init('00b402fc0da54ed1af8687d4c4389911')
rollbar.report_message('Rollbar is configured correctly')
logger = nb_logging.setup_logger('NB')

if __name__ == "__main__":
    populate()
    add_domains()
    add_comment_counts()
    # prune_starred()
    logger.info('Done.')
