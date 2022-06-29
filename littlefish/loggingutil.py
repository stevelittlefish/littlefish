"""
Custom logging handlers and utilities
"""

import logging

from . import ansi

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


class ColourLogHandler(logging.StreamHandler):
    def __init__(self, show_timestamps, celery_mode, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.formatters = {
            logging.DEBUG: logging.Formatter(
                get_coloured_logging_format(
                    ansi.GREEN, show_timestamps=show_timestamps, celery_mode=celery_mode
                )
            ),
            logging.INFO: logging.Formatter(
                get_coloured_logging_format(
                    ansi.LIGHT_GREEN, show_timestamps=show_timestamps, celery_mode=celery_mode
                )
            ),
            logging.WARNING: logging.Formatter(
                get_coloured_logging_format(
                    ansi.YELLOW, show_timestamps=show_timestamps, celery_mode=celery_mode
                )
            ),
            logging.ERROR: logging.Formatter(
                get_coloured_logging_format(
                    ansi.LIGHT_RED, show_timestamps=show_timestamps, celery_mode=celery_mode
                )
            ),
            logging.CRITICAL: logging.Formatter(
                get_coloured_logging_format(
                    ansi.LIGHT_RED, show_timestamps=show_timestamps, celery_mode=celery_mode
                )
            ),
            'DEFAULT': logging.Formatter(
                get_coloured_logging_format(
                    ansi.DARK_GREY, show_timestamps=show_timestamps, celery_mode=celery_mode
                )
            ),
        }

    def format(self, record):
        formatter = self.formatters.get(record.levelno, self.formatters['DEFAULT'])
        return formatter.format(record)


def get_base_logging_format_template(show_timestamps, celery_mode):
    meta_format = '{time}{level}{colon}{name}{colon}{message}'

    time = ''
    if show_timestamps:
        time = '{time_colour}%(asctime)s{reset} '

    level = '{level_colour}%(levelname)s'

    colon = '{colon_colour}:'

    if celery_mode:
        name = '{process_name_colour}%(processName)s'
    else:
        name = '{name_colour}%(name)s'

    message = '{reset}%(message)s'

    format_template = meta_format.format(
        time=time,
        level=level,
        colon=colon,
        name=name,
        message=message
    )

    return format_template


def get_coloured_logging_format(level_colour, show_timestamps=False, celery_mode=False):
    """
    :return Standardized coloured logging format for a specific level
    """
    logging_format = get_base_logging_format_template(
        show_timestamps=show_timestamps,
        celery_mode=celery_mode
    )

    return logging_format.format(
        time_colour=ansi.CYAN,
        reset=ansi.RESET,
        level_colour=level_colour,
        colon_colour=ansi.DARK_GREY,
        name_colour=ansi.BLUE,
        process_name_colour=ansi.PURPLE
    )


def get_logging_format(show_timestamps=False, celery_mode=False):
    """
    :return Standardized logging format
    """
    logging_format = get_base_logging_format_template(
        show_timestamps=show_timestamps,
        celery_mode=celery_mode
    )

    return logging_format.format(
        time_colour='',
        reset='',
        level_colour='',
        colon_colour='',
        name_colour='',
        process_name_colour=''
    )


def initialise_logging(debug_mode, show_timestamps=False, colour=False):
    # Remove all handlers associated with the root logger object.
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    handlers = []
    if colour:
        handlers.append(ColourLogHandler(show_timestamps, False))
    else:
        handlers.append(logging.StreamHandler())
    
    logging_format = get_logging_format(show_timestamps=show_timestamps)

    if debug_mode:
        logging.basicConfig(level=logging.DEBUG, format=logging_format, datefmt=DATE_FORMAT, handlers=handlers)
        log.debug('Starting in DEBUG mode')
    else:
        logging.basicConfig(level=logging.INFO, format=logging_format, datefmt=DATE_FORMAT, handlers=handlers)
        log.info('Logging set to INFO')
