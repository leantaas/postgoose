import logging
from os import getenv
from typing import Union

APP_NAME = "postgoose"


# These formats should be used with caution
# because they will break if you try to configure
# them without running in a lambda
# due to `aws_request_id` argument

# Provided for reference - this is Amazon's default format for lambda logs
DEFAULT_LAMBDA_LOG_FORMAT = "[%(levelname)s] %(asctime)s.%(msecs)dZ %(aws_request_id)s %(message)s"
CUSTOM_LAMBDA_LOG_FORMAT = "[{levelname}] {asctime}|{aws_request_id}|{module}:{lineno} - {message}"
STANDARD_LOG_FORMAT = "[{levelname}] {asctime}|{module}:{lineno} - {message}"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

DEFAULT_LOG_LEVEL = logging.INFO

IS_LAMBDA = True if getenv("AWS_LAMBDA_FUNCTION_NAME") else False


def initialize_logger(level: int = DEFAULT_LOG_LEVEL):
    """
    initialize_logger
    """
    if len(logging.getLogger().handlers) > 0:
        # This ensures that a pre-existing root logger
        # will be formatted using our formatter
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_handler = root_logger.handlers[0]
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        if IS_LAMBDA:
            fmt = CUSTOM_LAMBDA_LOG_FORMAT
        else:
            fmt = STANDARD_LOG_FORMAT
        formatter = logging.Formatter(fmt, datefmt=DATE_FORMAT, style="{")
        root_handler.setFormatter(formatter)
    else:
        # This will configure the root logger with a
        # simple stream handler
        logging.basicConfig(
            format=STANDARD_LOG_FORMAT,
            level=logging.INFO,
            datefmt="%m-%d-%y %H:%M:%S",
            style="{"
        )
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(level)


def get_app_logger(name: str = None):
    """
    get_app_logger
    """
    initialize_logger()
    if name:
        logger_name = f"{APP_NAME}.{name}"
    else:
        logger_name = APP_NAME
    return logging.getLogger(logger_name)
