from connectors.MySqlClient import MySqlClient
import os
from utility import nb_logging

logger = nb_logging.setup_logger('client_factor')


def get_db_client():
    host = os.getenv('DB_HOST')
    user = os.getenv('DB_USER')
    password = os.getenv('DB_PASS')
    logger.debug('host: {}'.format(host))
    return MySqlClient(host=host, user=user, password=password,
                       db_name=os.getenv('DB_NAME', 'nb'))
