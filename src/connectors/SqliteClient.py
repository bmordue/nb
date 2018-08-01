from connectors.DbConnector import DbConnector


class SqliteClient(DbConnector):
    def __init__(self):
	DbConnector.__init__(self)
