import logging
import sys


def setup_logger(name, level=logging.DEBUG):
    logging.basicConfig(stream=sys.stdout, level=logging.WARN,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
