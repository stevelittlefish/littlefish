"""
Utilities for handling JSON
"""

import logging
import json
from decimal import Decimal

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class DecimalFloatEncoder(json.JSONEncoder):
    """
    Adds ability to encode Decimals as floats.  It's shit but sometimes useful!
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)

        return super().default(obj)
