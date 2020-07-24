"""
Base code for building site session data classes - classes which manage the session dict, and
handle serialisation of data into session compatible types
"""

import logging

from flask import session

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class _NoDefaultType(object):
    pass


# Set default value to this to avoid setting value to None by default
NoDefault = _NoDefaultType()


class SessionVar(object):
    def __init__(self, key, default_value=None):
        self.key = key
        self.default_value = default_value
    
    def __get__(self, instance, owner):
        if instance is None:
            raise Exception('SessionVars can only be set through SessionData instances')

        if instance._has_session_value(self.key):
            json_val = instance._get_session_value(self.key)
            if json_val is None:
                return None
            return self.from_json_val(json_val)

        elif self.default_value == NoDefault:
            raise AttributeError('Attribute "{}" hasn\'t been set for {} instance'.format(
                self.key, owner.__name__
            ))
        else:
            if isinstance(self.default_value, list):
                # Copy list to avoid appending to actual default value
                default_value = self.default_value[:]
            elif isinstance(self.default_value, dict):
                # Copy dict
                default_value = self.default_value.copy()
            else:
                # Just return the default value
                default_value = self.default_value

            return default_value

    def __set__(self, instance, value):
        if instance is None:
            raise Exception('SessionVars can only be set through SessionData instances')
        
        if value is None:
            instance._set_session_value(self.key, None)
        else:
            instance._set_session_value(self.key, self.to_json_val(value))

    def to_json_val(self, val):
        """
        Convert from the datatype of this SessionVar back into a json compatible value.

        This is the method you override to implement the desired type conversion when saving to
        the session
        """
        return val

    def from_json_val(self, json_val):
        """
        Convert from a json compatible value, back into the correct type for this SessionVar.

        This is the method you override to implement the desired type conversion when loading from
        the session
        """
        return json_val


class SessionData(object):
    def __init__(self, version=1, version_key='_v', base_key=None):
        self._version = version
        self._version_key = version_key

        if base_key is None:
            base_key = self.__class__.__name__

        self._base_key = base_key

        if base_key not in session:
            session[self._base_key] = {}
            self._data_dict = session[base_key]
            self.clear()

        self._data_dict = session[base_key]
        
        session_version = self._data_dict.get(version_key, -1)
        if session_version < self._version:
            if self._version > -1:
                log.info('Clearing old session (version = {}, latest version = {}'.format(
                    session_version, self._version
                ))
            self.clear()
        
        # Ensure session is always saved
        session.modified = True

    def clear(self):
        self._data_dict.clear()
        self._data_dict[self._version_key] = self._version
    
    def _has_session_value(self, key):
        return key in self._data_dict

    def _get_session_value(self, key):
        return self._data_dict[key]

    def _set_session_value(self, key, value):
        self._data_dict[key] = value

    def get_data(self):
        """
        :return: the raw data dictionary. This can be used to restore the sessiondata after the
                 flask session is cleared
        """
        return self._data_dict

    def restore_data(self, data_dict):
        """
        Restore the data dict - update the flask session and this object
        """
        session[self._base_key] = data_dict
        self._data_dict = session[self._base_key]

