from tasks.populate import populate, add_comment_counts
from tasks.prune import prune_starred
from tasks.add_domains import add_domains
from utility import nb_logging

logger = nb_logging.setup_logger('NB')

if __name__ == "__main__":
    populate()
    add_comment_counts()
    prune_starred()
    add_domains()
    logger.info('Done.')
