"""
Logging helpers
"""

from functools import partial
from logging import DEBUG, INFO, NOTSET, WARNING, Formatter, LogRecord, StreamHandler, getLogger
from logging.handlers import TimedRotatingFileHandler

from colored import fg, stylize

from .fs import get_user_cache_dir

__all__ = ['init_logging', 'log_initializer', 'ENTRY_FMT_DETAILED']

ENTRY_FMT_DETAILED = '%(asctime)s %(levelname)s %(threadName)s %(name)s %(lineno)d %(message)s'


def init_logging(verbose: int, *, entry_fmt: str = None, file_name: str = None):
    if verbose > 1:
        entry_fmt = ENTRY_FMT_DETAILED
    elif entry_fmt is None:
        entry_fmt = '%(message)s'

    level = WARNING if verbose < 0 else DEBUG if verbose else INFO
    logger = getLogger()
    logger.setLevel(NOTSET)

    stream_handler = StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(ColorLogFormatter(entry_fmt))
    logger.addHandler(stream_handler)

    if file_name:
        log_path = get_user_cache_dir('logs').joinpath(file_name)
        file_handler = TimedRotatingFileHandler(log_path, when='D', backupCount=14, encoding='UTF-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(Formatter(ENTRY_FMT_DETAILED))
        logger.addHandler(file_handler)


def log_initializer(verbose: int):
    return partial(init_logging, verbose)


class ColorLogFormatter(Formatter):
    """
    Uses ANSI escape codes to colorize stdout/stderr logging output.  Colors may be specified by using the ``extra``
    parameter when logging, for example::

        log.error('An error occurred', extra={'color': 'red'})
    """

    def format(self, record: LogRecord) -> str:
        formatted = super().format(record)
        if (color := getattr(record, 'color', None)) and isinstance(color, (str, int)):
            return stylize(formatted, fg(color))

        return formatted
