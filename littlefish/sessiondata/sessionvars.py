"""
This contains the SessionVar classes - use these to add variables to your SessionData classes
"""

import logging
import decimal

from .framework import SessionVar as _Var

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class SessionInt(_Var):
    def to_json_val(self, val):
        return int(val)


class SessionStr(_Var):
    def to_json_val(self, val):
        return str(val)


class SessionDecimal(_Var):
    def to_json_val(self, val):
        if not isinstance(val, (decimal.Decimal, int)):
            raise ValueError('SessionDecimal field must be set to a Decimal (or int) value')

        return str(val)

    def from_json_val(self, json_val):
        return decimal.Decimal(json_val)


