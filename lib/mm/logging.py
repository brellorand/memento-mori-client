"""
Logging helpers
"""

from functools import partial
from logging import LogRecord, Formatter, getLogger, basicConfig, DEBUG, INFO

from colored import stylize, fg

__all__ = ['init_logging', 'log_initializer', 'ENTRY_FMT_DETAILED']

ENTRY_FMT_DETAILED = '%(asctime)s %(levelname)s %(threadName)s %(name)s %(lineno)d %(message)s'


def init_logging(verbose: int):
    log_fmt = ENTRY_FMT_DETAILED if verbose > 1 else '%(message)s'
    basicConfig(level=DEBUG if verbose else INFO, format=log_fmt)

    formatter = ColorLogFormatter(log_fmt)
    for handler in getLogger().handlers:
        handler.setFormatter(formatter)


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
