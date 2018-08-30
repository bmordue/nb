from connectors.MySqlClient import MySqlClient
import os


def get_db_client():
    return MySqlClient(host=os.getenv('DB_HOST'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASS'),
                       db_name=os.getenv('DB_NAME', 'nb'))
