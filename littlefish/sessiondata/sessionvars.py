"""
This contains the SessionVar classes - use these to add variables to your SessionData classes
"""

import logging
import decimal
from collections import Mapping

from .framework import SessionVar as _Var

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class SessionInt(_Var):
    def to_json_val(self, val):
        return int(val)


class SessionStr(_Var):
    def to_json_val(self, val):
        return str(val)


class SessionBool(_Var):
    def to_json_val(self, val):
        return bool(val)


class SessionDecimal(_Var):
    def to_json_val(self, val):
        if not isinstance(val, (decimal.Decimal, int)):
            raise ValueError('SessionDecimal field must be set to a Decimal (or int) value')

        return str(val)

    def from_json_val(self, json_val):
        return decimal.Decimal(json_val)


class SessionDict(_Var):
    def __init__(self, key, template_dict, default_value=None):
        """
        Stores a dictionary in the session

        :param key: The key to store this under
        :param template_dict: Dictionary, mapping dictionary keys onto SessionVars, defining the
                              type of data that should be mapped under each key. The SessionVars'
                              key attributes will be ignored - you can just pass in key=None
        """
        super().__init__(key, default_value=default_value)

        self.template_dict = template_dict

    def to_json_val(self, val):
        # Make sure this is a dict-like object
        if not isinstance(val, Mapping):
            raise ValueError('Non Mapping value "{}" cannot be stored in dict field'
                             .format(val))

        # Check for invalid keys
        for key in val:
            if key not in self.template_dict:
                raise ValueError('Invalid key "{}" in dict to be stored in session: {}'
                                 .format(key, val))

        # Build the dict to be stored
        json_dict = {}
        for key in self.template_dict:
            if key not in val:
                raise ValueError('Key "{}" not found in dict to be stored in session: {}'
                                 .format(key, val))

            session_var = self.template_dict[key]
            json_dict[key] = session_var.to_json_val(val[key])

        return json_dict

    def from_json_val(self, json_val):
        # Check for invalid keys
        for key in json_val:
            if key not in self.template_dict:
                raise ValueError('Invalid key "{}" in dict stored in session: {}'
                                 .format(key, json_val))

        # Build the dict to be stored
        out_dict = {}
        for key in self.template_dict:
            if key not in json_val:
                raise ValueError('Key "{}" not found in dict stored in session: {}'
                                 .format(key, json_val))

            session_var = self.template_dict[key]
            out_dict[key] = session_var.from_json_val(json_val[key])

        return out_dict


class SessionList(_Var):
    def __init__(self, key, item_type, default_value=None):
        """
        :param item_type: SessionVar defining the type of each item in the list.  The key attribute
        of item_type will be ignored - you can just pass in None
        """
        if isinstance(item_type, type):
            raise ValueError('item_type needs to be an instance of a SessionVar and not a class')
        
        super().__init__(key, default_value=default_value)
        
        self.item_type = item_type

    def to_json_val(self, val):
        if not isinstance(val, list):
            raise ValueError('Non list value "{}" cannot be stored in list session variable'
                             .format(val))
        json_list = []
        for i in val:
            json_list.append(self.item_type.to_json_val(i))

        return json_list

    def from_json_val(self, json_val):
        out_list = []
        for i in json_val:
            out_list.append(self.item_type.from_json_val(i))

        return out_list

        
        
