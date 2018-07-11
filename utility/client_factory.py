from connectors.MySqlClient import MySqlClient
from utility.NbConfig import NbConfig


def get_db_client():
    config = NbConfig()
    return MySqlClient(host=config.get('DB_HOST'), user=config.get('DB_USER'), password=config.get('DB_PASS'),
                       db_name=config.get('DB_NAME'))
