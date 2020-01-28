"""
Debugging stuff
"""

import logging
import inspect
import pprint

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class DontPrint:
    pass


DONT_PRINT = DontPrint()


DEBUG_FORMAT = '@@@ {}'
LESSER_DEBUG_FORMAT = '  @ {}'


def lesser_debug_print(s):
    print(LESSER_DEBUG_FORMAT.format(s))


def debug_print(s=DONT_PRINT, **kwargs):
    if s is not DONT_PRINT:
        print(DEBUG_FORMAT.format(s))
    
    first = True
    for k, v in kwargs.items():
        if s is DONT_PRINT and first:
            debug_print('{} = {}'.format(k, v))
        else:
            lesser_debug_print('{} = {}'.format(k, v))

        first = False


def print_vars(**kwargs):
    for k, v in kwargs.items():
        pretty = pprint.pformat(v)
        debug_print('{}: {} = {}'.format(type(v), k, pretty))


def print_spacer(level=3):
    if level == 1:
        c = '#'
    elif level == 2:
        c = '='
    else:
        c = '-'

    print(c * 80)


def print_location(**kwargs):
    """
    :param kwargs: Pass in the arguments to the function and they will be printed too!
    """
    try:
        stack = inspect.stack()[1]
        debug_print('{}:{} {}()'.format(stack[1], stack[2], stack[3]))
    except Exception:
        debug_print('UNKNOWN LOCATION')

    for k, v in kwargs.items():
        lesser_debug_print('{} = {}'.format(k, v))
