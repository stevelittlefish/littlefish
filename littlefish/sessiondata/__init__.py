"""
This package contains code for managing session data, by creating SessionData classes, instances
of which map a subset of the session data onto attributes on an object.
"""

import logging

from .framework import SessionData, NoDefault  # noqa
from .sessionvars import *  # noqa

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


