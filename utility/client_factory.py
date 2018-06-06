import os

from connectors.MySqlClient import MySqlClient
from connectors.dynamo.DynamoDbClient import DynamoDbClient
from utility import constants


def get_db_client():
    return DynamoDbClient()
