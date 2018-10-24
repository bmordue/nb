import rollbar
import schedule
import time
from ddtrace import patch_all

from tasks.add_comment_counts import add_comment_counts
from tasks.add_domains import add_domains
from tasks.populate import populate
from tasks.prune import prune_starred

from utility import client_factory
from utility import nb_logging

patch_all()

rollbar.init('00b402fc0da54ed1af8687d4c4389911')
logger = nb_logging.setup_logger('app')


def get_config(task):
    db_client = client_factory.get_db_client()
    config = db_client.read_config()
    logger.debug('Config for %s: %s', task, config)
    return config


def periodic_populate():
    config = get_config('populate')
    if 'True' == config.get('SHOULD_POPULATE'):
        logger.info('Running scheduled populate task')
        populate()
    else:
        logger.info('SHOULD_POPULATE is %s; not running populate task'.format(config.get('SHOULD_POPULATE')))
    if 'True' == config.get('SHOULD_ADD_DOMAINS'):
        add_domains()
    else:
        logger.info('SHOULD_ADD_DOMAINS is %s; not running add_domains task'.format(config.get('SHOULD_ADD_DOMAINS')))


def periodic_add_comment_counts():
    logger.info('Running scheduled add_comment_counts task')
    config = get_config('add_comment_counts')
    if 'True' == config.get('SHOULD_ADD_COMMENT_COUNTS'):
        add_comment_counts()
    else:
        logger.info('SHOULD_ADD_COMMENT_COUNTS is %s; not running add_comment_counts task'.format(config.get('SHOULD_ADD_COMMENT_COUNTS')))


def periodic_prune_starred():
    logger.info('Running scheduled prune_starred task')
    config = get_config('prune_starred')
    if 'True' == config.get('SHOULD_PRUNE_STARRED'):
        prune_starred()
    else:
        logger.info('SHOULD_PRUNE_STARRED is %s; not running prune_starred task'.format(config.get('SHOULD_PRUNE_STARRED')))


if __name__ == '__main__':
    logger.info('Started')

    schedule.every().hour.do(periodic_populate())
    schedule.every().hour.do(periodic_add_comment_counts())
    schedule.every().day.at('23:00').do(periodic_prune_starred())

    while True:
        logger.info('Run pending scheduled jobs')
        schedule.run_pending()
        time.sleep(60)
