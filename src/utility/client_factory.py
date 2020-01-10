from connectors.SqliteClient import SqliteClient
from connectors.NewsblurConnector import NewsblurConnector
from utility import nb_logging
import os

logger = nb_logging.setup_logger('client_factory')
SECRETS_DIR = os.getenv('SECRETS_DIR', '/run/secrets/')


def get_secret(name):
    with open(os.path.join(SECRETS_DIR, name), 'r') as f:
        secret = f.read().strip()
    return secret


def get_db_client():
    logger.debug('DB: sqlite file')
    return SqliteClient()


def get_newsblur_client():
    db_client = get_db_client()

    username = get_secret('NB_USERNAME')
    password = get_secret('NB_PASSWORD')

    return NewsblurConnector(db_client.read_config(), username, password)
