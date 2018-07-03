from connectors.MySqlClient import MySqlClient
import utility.constants as constants


def get_db_client():
    return MySqlClient(host=constants.DB_HOST, user=constants.DB_USER, password=constants.DB_PASS,
                       db_name=constants.DB_NAME)
