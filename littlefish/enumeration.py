"""
Base type for types and statuses - python classes for storing types / statuses, ensuring that they
render as a span with a css class and tooltip, and adding database types to automatically
decode them from strings in the database. I have elected not to use python enums because I
hate the way that they handle properties!
"""

import logging

import sqlalchemy.types

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class MetaEnumeration(type):
    def __call__(cls, *args, **kwargs):
        # Create and initialise the instance
        instance = super().__call__(*args, **kwargs)
        
        if not hasattr(cls, 'instances'):
            cls.instances = {}
        
        if instance.code in cls.instances:
            raise ValueError('Code must unique. An instance of {} already exists '
                             'with code {}'.format(cls.__name__, instance.code))

        cls.instances[instance.code] = instance

        return instance


class Enumeration(metaclass=MetaEnumeration):
    """
    Subclass this to create classes for different "Types" and "Statuses", i.e.
    OrderStatus, StaffActionType.

    These are basically enumerations.  They are nowehere near as safe as the standard library
    enum but are more convenient for adding attributes.

    You can use Enumeration.instances to get a dict of instances mapping code onto the instance,
    Enumeration.from_code(code) to get an instance from a code and Enumeration.db_type() to
    get the SQLAlchemy column type.  In jinja scripts you can output them to get a nice span
    with a css class and a tooltip.

    Be sure to override the "css_class" class variable for html rendering.
    """
    # Set this in subclass to change the base css class
    base_css_class = 'unknown'

    def __init__(self, code, description):
        self.code = code
        self.description = description

    @property
    def css_class(self):
        return '{} {}-{}'.format(
            self.base_css_class, self.base_css_class, self.code.replace('_', '-').replace(' ', '-').lower()
        )

    def __html__(self):
        return '<span data-toggle="tooltip" title="{}" class="{}">{}</span>'.format(
            self.description, self.css_class, self.code
        )

    def __str__(self):
        return self.code

    @classmethod
    def from_code(cls, code):
        if not hasattr(cls, 'instances') or code not in cls.instances:
            raise ValueError('Code "{}" is not a valid {}'.format(
                code, cls.__name__
            ))

        return cls.instances[code]

    @classmethod
    def values(cls):
        return cls.instances.values()

    @classmethod
    def db_type(cls):
        """
        :return: SQL Alchemy Type Decorator to pass into database column in model
        """
        class StatusTypeDecorator(sqlalchemy.types.TypeDecorator):
            impl = sqlalchemy.types.String

            def process_bind_param(self, value, dialect):
                if value is None:
                    return None

                if not isinstance(value, cls):
                    raise ValueError('Value must be a valid {}, {} given'
                                     .format(cls.__name__, type(value)))
                return value.code

            def process_result_value(self, value, dialect):
                if value is None:
                    return None

                return cls.from_code(value)

        return StatusTypeDecorator

