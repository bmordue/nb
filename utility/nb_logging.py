import logging
import sys

def setup_logger(name):
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG, format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    return logging.getLogger(name)
