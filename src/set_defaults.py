from utility.NbConfig import NbConfig
from utility import client_factory
from utility import nb_logging

logger = nb_logging.setup_logger('prune')


if __name__ == "__main__":
    db_client = client_factory.get_db_client()
    db_client.ensure_config_table_exists()
    config = NbConfig({})
    logger.info("Config to write: %s", config.config)
    db_client.write_config(config.config)
    config_read = db_client.read_config()
    logger.info("Config read from DB: %s", config_read.config)
