import logging
from pathlib import Path
import datetime
import time

class LocalTimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None) -> str:
        return '%s,%03d' % (datetime.datetime.fromtimestamp(record.created).strftime(datefmt or self.datefmt),
                            record.msecs)

def setup_logger(logger):
    logger_level = logging.DEBUG
    Path("./logs/connection_errors").mkdir(parents=True, exist_ok=True)

    formatter = LocalTimeFormatter(
        '%(asctime)s | %(filename)-24s %(funcName)-28s:%(lineno)-5d | %(levelname)-10s - "%(message)s"',
        '%Y-%m-%d %H:%M:%S',
        style='%'
    )

    logger.setLevel(logger_level)
    log_filename = f'logs/{time.strftime("%Y-%m-%d_%H_%M_%S")}.log'
    file_output_handler = logging.FileHandler(log_filename, encoding='utf-8')
    file_output_handler.setFormatter(formatter)
    logger.addHandler(file_output_handler)