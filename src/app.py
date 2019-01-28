import rollbar
import schedule
import time
from ddtrace import patch_all
from ddtrace import tracer

from tasks.add_comment_counts import add_comment_counts
from tasks.add_domains import add_domains
from tasks.populate import populate
from tasks.prune import prune_starred

from utility import client_factory
from utility import nb_logging

patch_all()

rollbar.init('00b402fc0da54ed1af8687d4c4389911')
logger = nb_logging.setup_logger('app')

from datadog import initialize
initialize(statsd_host='dd_agent')

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
        logger.info('Finished scheduled populate task')
    else:
        logger.info('SHOULD_POPULATE is %s; not running populate task'.format(config.get('SHOULD_POPULATE')))
    if 'True' == config.get('SHOULD_ADD_DOMAINS'):
        logger.info('Running scheduled add_domains task')
        add_domains()
        logger.info('Finished scheduled add_domains task')
    else:
        logger.info('SHOULD_ADD_DOMAINS is %s; not running add_domains task'.format(config.get('SHOULD_ADD_DOMAINS')))


def periodic_add_comment_counts():
    config = get_config('add_comment_counts')
    if 'True' == config.get('SHOULD_ADD_COMMENT_COUNTS'):
        logger.info('Running scheduled add_comment_counts task')
        add_comment_counts()
        logger.info('Finished scheduled add_comment_counts task')
    else:
        logger.info('SHOULD_ADD_COMMENT_COUNTS is %s; not running add_comment_counts task'.format(config.get('SHOULD_ADD_COMMENT_COUNTS')))


def periodic_prune_starred():
    config = get_config('prune_starred')
    if 'True' == config.get('SHOULD_PRUNE_STARRED'):
        logger.info('Running scheduled prune_starred task')
        prune_starred()
        logger.info('Finished scheduled prune_starred task')
    else:
        logger.info('SHOULD_PRUNE_STARRED is %s; not running prune_starred task'.format(config.get('SHOULD_PRUNE_STARRED')))


if __name__ == '__main__':
    logger.info('Started')

    schedule.every().hour.do(periodic_populate)
    schedule.every().hour.do(periodic_add_comment_counts)
    schedule.every().day.at('23:00').do(periodic_prune_starred)

    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            rollbar.report_exc_info()
            raise e
        time.sleep(60)
