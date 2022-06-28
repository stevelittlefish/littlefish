"""
Custom logging handlers and utilities
"""

import logging

from . import ansi

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class ColourLogHandler(logging.StreamHandler):
    def __init__(self, show_timestamps, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.formatters = {
            logging.DEBUG: logging.Formatter(
                get_coloured_logging_format(
                    ansi.LIGHT_GREY, show_timestamps=show_timestamps
                )
            ),
            logging.INFO: logging.Formatter(
                get_coloured_logging_format(
                    ansi.GREEN, show_timestamps=show_timestamps
                )
            ),
            logging.WARNING: logging.Formatter(
                get_coloured_logging_format(
                    ansi.YELLOW, show_timestamps=show_timestamps
                )
            ),
            logging.ERROR: logging.Formatter(
                get_coloured_logging_format(
                    ansi.LIGHT_RED, show_timestamps=show_timestamps
                )
            ),
            logging.CRITICAL: logging.Formatter(
                get_coloured_logging_format(
                    ansi.LIGHT_RED, show_timestamps=show_timestamps
                )
            ),
            'DEFAULT': logging.Formatter(
                get_coloured_logging_format(
                    ansi.DARK_GREY, show_timestamps=show_timestamps
                )
            ),
        }

    def format(self, record):
        formatter = self.formatters.get(record.levelno, self.formatters['DEFAULT'])
        return formatter.format(record)


def get_coloured_logging_format(level_colour, show_timestamps=False):
    """
    :return Standardized coloured logging format for a specific level
    """
    logging_format = '{level_colour}%(levelname)s{colon_colour}:{name_colour}%(name)s{colon_colour}:{reset}%(message)s'

    if show_timestamps:
        logging_format = '{time_colour}%(asctime)s{reset} ' + logging_format
    
    return logging_format.format(
        time_colour=ansi.CYAN,
        reset=ansi.RESET,
        level_colour=level_colour,
        colon_colour=ansi.DARK_GREY,
        name_colour=ansi.PURPLE
    )


def get_logging_format(show_timestamps=False):
    """
    :return Standardized logging format
    """
    logging_format = '%(levelname)s:%(name)s:%(message)s'

    if show_timestamps:
        logging_format = '%(asctime)s ' + logging_format
    
    return logging_format


def initialise_logging(debug_mode, show_timestamps=False, colour=False):
    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    handlers = []
    if colour:
        handlers.append(ColourLogHandler(show_timestamps))
    else:
        handlers.append(logging.StreamHandler())
    
    logging_format = get_logging_format(show_timestamps=show_timestamps)

    if debug_mode:
        logging.basicConfig(level=logging.DEBUG, format=logging_format, datefmt=DATE_FORMAT, handlers=handlers)
        log.debug('Starting in DEBUG mode')
    else:
        logging.basicConfig(level=logging.INFO, format=logging_format, datefmt=DATE_FORMAT, handlers=handlers)
        log.info('Logging set to INFO')
