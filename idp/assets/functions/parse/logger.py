# import sys
from os import environ
import logging

log_level = environ.get('LOG_LEVEL', logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)

# stdout_handler = logging.StreamHandler(sys.stdout)
# logger.addHandler(stdout_handler)