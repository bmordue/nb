import os

from connectors.MySqlClient import MySqlClient
from utility import constants


def get_db_client():
    host = os.getenv('DB_HOST','stage.benmordue.co.uk')
    user = os.getenv('DB_USER','No username')
    password = os.getenv('DB_PASS','No password')
    return MySqlClient(host=host,user=user,password=password,db_name=constants.DB_NAME)
