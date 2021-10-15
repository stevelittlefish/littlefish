"""
System for loading YAML Files into objects (i.e. database models)
"""

import logging
import os
import decimal
import re

import yaml
from littlefish import util

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)

_HTML_COLOUR_REGEX = re.compile(r'^#[0-9a-f]{6}$')


class DataType(object):
    def __init__(self, name, from_yaml, constant_value=None):
        """
        :param name: The name of the type
        :param from_yaml: Function to convert from yaml variable to Python datatype
        :param constant_value: If set, this will always have the same value and will
                               not be loaded from the YAML data
        """
        self.name = name
        self.from_yaml = from_yaml
        self.constant_value = constant_value


# This is mainly used for testing - returns whatever the yaml datatype happens to be
RAW = DataType('!RAW!', lambda x: x)

# This is a special case - fields of this will not be parsed at all, will not be passed into the
# constructor and will not be updated. Use this for sub-models
IGNORE = DataType('!IGNORE!', None)


# This is another special case - use this when some extra field is needed for the import, that
# isn't in the yaml.  This is used when a relation needs to be imported and the original object
# that it's attached to needs to be passed through
def CONSTANT(value):  # noqa
    if value is None:
        raise ValueError('Constant value can\'t be None!')

    return DataType('!CONSTANT!', None, constant_value=value)


def load_single_line_str(s):
    """validates that a string is single line"""
    s = str(s)

    if '\n' in s:
        raise ValueError('String value "{}" contains newline character. HINT: consider using '
                         'yaml ">-" operator for multi-line strings'.format(s))

    return s


# STR only allows single line strings
STR = DataType('str', load_single_line_str)

# MULTI_LINE_STR allows any string with no validation
MULTILINE_STR = DataType('str/multi-line', lambda s: str(s))


def load_int(i):
    if isinstance(i, float):
        raise ValueError('Float value {} passed when integer required'.format(i))
    
    return int(i)


INT = DataType('int', load_int)


def load_decimal(s):
    if isinstance(s, float):
        raise ValueError('Float value {} passed when Decimal required. Please use quoted '
                         'string instead'.format(s))

    return decimal.Decimal(s)


DECIMAL = DataType('Decimal', load_decimal)


def load_html_colour(s):
    s = s.lower().strip()

    if not _HTML_COLOUR_REGEX.match(s):
        raise ValueError('Invalid HTML colour: "{}"'.format(s))

    return s


HTML_COLOUR = DataType('html_colour', load_html_colour)


def load_boolean(b):
    if not isinstance(b, bool):
        raise ValueError('Boolean required, got "{}"'.format(b))

    return b


BOOLEAN = DataType('bool', load_boolean)


class ImportField(object):
    def __init__(self, name, data_type, constructor_field=True, identifier=False,
                 optional=False, default=None, unchangeable=False, no_update=False,
                 python_name=None):
        """
        :param name: The field in the yaml file. By default this is also the spelling of the
                     python field and keyword argument for constructor
        :param data_type: A DataType defining the type of this field
        :param constructor_field: Is this field passed in to the constructor
        :param identifier: If True, this field cannot be changed once it is set and is used to
                           load the object from the database to update it (i.e. it is a unique
                           identifier of the object)
        :param optional: If True, this field doesn't need to be present to import the object. It
                         will be set to None if not present
        :param default: Default value for optional arguments that are not present
        :param unchangeable: If True, this can never be updated after it has been inserted
        :param no_update: This will only be set for new models - existing models will not be updated.
                          The difference between this and unchangeable is that unchangeable fields will
                          raise an error if the value in the yaml file is different from the database,
                          but these will not.
        :param python_name: Use this to override the spelling of the python variable in the model
        """
        if default is not None and not optional:
            raise ValueError('Only optional arguments can have a default!')

        self.name = name
        self.data_type = data_type
        self.constructor_field = constructor_field
        self.identifier = identifier
        self.optional = optional
        self.default = default
        self.unchangeable = unchangeable
        self.no_update = no_update
        self._python_name = python_name

    def from_yaml(self, s):
        try:
            return self.data_type.from_yaml(s)
        except Exception as e:
            error = str(e)
            raise ValueError('Error reading field "{}": {}'.format(self.name, error))

    @property
    def constant_value(self):
        return self.data_type.constant_value

    @property
    def python_name(self):
        if self._python_name:
            return self._python_name

        return self.name


def get_list(data_dict, key, optional=False):
    """
    Extract a list from a data_dict and do a bit of error checking
    """
    if key not in data_dict:
        if optional:
            return None
        else:
            raise ValueError('Key "{}" not present in data'.format(key))

    l = data_dict[key]  # noqa
    if not isinstance(l, list):
        raise ValueError('Key "{}" is not a list'.format(key))

    return l


def load_yaml_from_directory(path):
    """
    Load yaml files from a directory and return a generator with the parsed dicts

    :return: Generator of tuples (filename, data_dict)
    """
    files = os.listdir(path)
    
    for f in files:
        filename = os.path.join(path, f)
        if os.path.isfile(filename) and not f.startswith('.'):
            log.info('Loading {}'.format(filename))
            with open(filename, 'r') as stream:
                data = yaml.load(stream)

                yield filename, data


def import_model(model_class, yaml_data_dict, fields, session, commit=False, silence_no_changes=False,
                 insert_only=False):
    """
    Import a model from a parsed yaml file

    :param model_class: Model class, i.e. Category
    :param data_dict: Dictionary obtained by parsing the yaml file
    :param fields: List of ImportFields defining the structure of the yaml file
    :param session: Database session (i.e. db.session)
    :param commit: Whether to commit to the database (defaults to False)
    :param silence_no_changes: Don't emit a log message when there are no changes
    :param insert_only: Don't update existing data - only insert new data
    """
    model_name = model_class.__name__

    # Make sure there are no duplicates in the fields
    all_field_yaml_names = set()
    all_field_python_names = set()
    for field in fields:
        if field.name in all_field_yaml_names:
            raise ValueError('Multiple fields in list with same name "{}"'.format(field.name))
        all_field_yaml_names.add(field.name)
        
        if field.python_name in all_field_python_names:
            raise ValueError('Miltiple fields in list with same python name "{}"'.format(field.python_name))
        all_field_python_names.add(field.python_name)
    
    # This may seem a little backwards - we process the data first and then validate it afterwards
    # Create a new dict with a combination of the data from data_dict and any relevant defaults.
    # This dict maps name -> value
    data = {}
    for field in fields:
        if field.data_type == IGNORE:
            # Do nothing with this field
            continue

        if field.constant_value:
            data[field.name] = field.constant_value
        elif field.name in yaml_data_dict:
            raw_value = yaml_data_dict[field.name]
            if raw_value is None:
                data[field.name] = None
            else:
                data[field.name] = field.from_yaml(raw_value)
        elif field.optional:
            data[field.name] = field.default

    # Data now contains processed versions of all of the fields in the yaml data

    # Next let's find the identifiers - the fields used to deduplicate this model and to update
    # existing models instead of creating new ones.  We will store these in a dict mapping yaml
    # name -> python name
    identifier_keys = {}
    for field in fields:
        if field.identifier:
            identifier_keys[field.name] = field.python_name
    
    # Loop over python names
    for identifier_key in identifier_keys.values():
        if identifier_key not in data:
            raise ValueError('Indentifier field "{}" not present in data when loading object of '
                             'type {}'.format(identifier_key, model_name))

    # Get the identifier for logging
    identifier = '/'.join([str(data[i]) for i in identifier_keys.values()])
    
    # These lists use the yaml_names
    all_field_keys = []
    required_field_keys = []
    
    # Now that we've loaded the data - it's time to validate that the correct stuff is present!
    for field in fields:
        if not field.constant_value:
            all_field_keys.append(field.name)
            if not field.optional:
                required_field_keys.append(field.name)
    
    # Check that the correct fields have been supplied
    for field in required_field_keys:
        if field not in yaml_data_dict:
            raise Exception('Required field "{}" not present in {} "{}"'.format(
                field, model_name, identifier
            ))

    for field in yaml_data_dict:
        if field not in all_field_keys:
            raise Exception('Unknown field "{}" found in {} "{}"'.format(
                field, model_name, identifier
            ))

    # Create a list of SQLAlchemy filters to load the model if it exists already
    filters = []
    for (yaml_key, python_name) in identifier_keys.items():
        filters.append(getattr(model_class, python_name) == data[yaml_key])
    
    # Load the instance to see if it exists
    model_instance = model_class.query.filter(*filters).one_or_none()
    updating = model_instance is not None

    if updating and insert_only:
        if not silence_no_changes:
            log.info(' X  Not Updating {} "{}"'.format(model_name, identifier))

        return model_instance

    # Convert values and assign to dicts to either pass into constructor, or update the field.
    # We start using python_name instead of name from here on as these dicts will be passed into
    # constructors etc.
    kwargs = {}
    update_fields = {}
    unchangeable_fields = set()

    for field in fields:
        if field.data_type == IGNORE:
            # Don't process this field
            continue
        
        if field.unchangeable:
            unchangeable_fields.add(field.python_name)
        
        # First extract the field from the dict and convert
        if field.name in data:
            # Field is present in parsed file
            value = data[field.name]
        else:
            # This should be impossible
            raise Exception('Required field not present in data dic')

        if not model_instance and field.constructor_field:
            kwargs[field.python_name] = value
        elif not field.identifier and not field.no_update:
            update_fields[field.python_name] = value

    # Now we have our field dicts - time to insert / update the object
    if not model_instance:
        log.info(' * Adding {} "{}"'.format(model_name, identifier))
        model_instance = model_class(**kwargs)
        session.add(model_instance)

    update_logger = util.UpdateLogger('   * ', use_logger=True)

    for field in update_fields:
        new_val = update_fields[field]
        if updating:
            old_val = getattr(model_instance, field)
            if old_val != new_val:
                # Check for unchangeable field being updated
                if field in unchangeable_fields:
                    raise Exception(
                        'Trying to change unchangeable field from {} to {}'.format(
                            old_val, new_val
                        )
                    )

                if isinstance(old_val, str) and len(old_val) > 100 \
                        or isinstance(new_val, str) and len(new_val) > 100:
                    update_logger.log_variable_update(field)
                else:
                    update_logger.log_variable_update(field, old_val, new_val)
        setattr(model_instance, field, new_val)

    if update_logger.has_updates:
        log.info(' * Updating {} "{}"'.format(model_name, identifier))
        update_logger.print_updates()
    elif updating and not silence_no_changes:
        log.info(' * (no changes for {} "{}")'.format(model_name, identifier))
    
    if commit:
        session.commit()

    return model_instance

