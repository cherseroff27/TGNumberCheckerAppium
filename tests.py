import os
from logger_config import Logger
logger = Logger.get_logger(__name__)

logger.info(f"Текущий PATH: {os.environ.get('PATH')}")
logger.info(f"JAVA_HOME: {os.environ.get('JAVA_HOME')}")
logger.info(f"ANDROID_HOME: {os.environ.get('ANDROID_HOME')}")