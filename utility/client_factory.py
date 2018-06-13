from connectors.dynamo.DynamoDbClient import DynamoDbClient


def get_db_client():
    return DynamoDbClient()
