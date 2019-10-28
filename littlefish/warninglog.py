"""
Functions for saving warning and errors to the database
"""

import logging
import io
import traceback
import datetime

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, BigInteger, String, DateTime, func
import sqlalchemy.exc


__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)

_ERROR_REPORT_THRESHOLD = None

# Database connection
_connection = None

# Session maker
_Session = None

# Database Model
WarningLogMessage = None

# Celery Task
save_warninglog_message_task = None


def init(app, engine_or_connection, celery=None, table_name='warning_log_message'):
    global _ERROR_REPORT_THRESHOLD, _connection, WarningLogMessage, \
        _Session, save_warninglog_message_task
    
    _ERROR_REPORT_THRESHOLD = app.config['WARNINGLOG_ERROR_REPORT_THRESHOLD']
    _connection = engine_or_connection

    BaseModel = declarative_base(bind=_connection)
    _Session = sessionmaker(bind=_connection)

    session = _Session()

    class DatabaseModel(BaseModel):
        __tablename__ = table_name

        id = Column(BigInteger, primary_key=True, nullable=False)
        timestamp = Column(DateTime, nullable=False)
        log_name = Column(String, nullable=False)
        location = Column(String, nullable=False)
        function = Column(String, nullable=True)
        title = Column(String, nullable=False)
        description = Column(String, nullable=False)
        traceback = Column(String, nullable=True)

        def __init__(self, timestamp, log_name, location, function, title, description, traceback=None):
            """
            :param timestamp: The time that the warning was raised
            :param log_name: Name of module (__name__ from python file)
            :param location: Full path and line number, i.e. "littlefish.timetool.py:113"
            :param function: The name of the function, i.e. "format_datetime"
            :param title: Error title (used to deduplicate)
            :param description: Full error string
            :param traceback: Optional string with traceback
            """
            self.timestamp = datetime.datetime.utcnow()
            self.log_name = log_name
            self.location = location
            self.function = function
            self.title = title
            self.description = description
            self.traceback = traceback

    WarningLogMessage = DatabaseModel

    # Create the table if it's missing
    try:
        WarningLogMessage.__table__.create()
    except sqlalchemy.exc.ProgrammingError:
        # Probably already exists so do nothing
        pass

    # Check that the table actually exists by trying to select from it
    try:
        session.query(WarningLogMessage).first()
    except Exception as e:
        raise Exception('Could not query from {}. Table creation probably failed!'.format(table_name), e)
    
    if celery:
        log.info('Using Celery for warninglog')
        save_warninglog_message_task = celery.task(save_warninglog_message)
    else:
        log.info('Not using Celery for warninglog - warnings will be logged in main thread')


def save_warninglog_message(timestamp, log_name, location, function, title, description, traceback=None):
    """
    :param log_name: Name of module (__name__ from python file)
    :param location: Full path and line number, i.e. "littlefish.timetool.py:113"
    :param function: The name of the function, i.e. "format_datetime"
    :param title: Error title (used to deduplicate)
    :param description: Full error string
    :param traceback: Optional string with traceback
    """
    log.info('Warning Log: {} - {}'.format(title, description))
    message = WarningLogMessage(timestamp, log_name, location, function, title, description, traceback)
    session = _Session()
    session.add(message)

    try:
        session.commit()
    except Exception:
        session.rollback()
        log.exception('Error saving warning log message to database: {}'.format(message.strip()))

    session.close()


def _find_caller(stack_info=False):
    """
    Shamelessly stolen from the logging library

    Find the stack frame of the caller so that we can note the source
    file name, line number and function name.
    """
    f = logging.currentframe()
    
    rv = "(unknown file)", 0, "(unknown function)", None
    while hasattr(f, "f_code"):
        co = f.f_code
        sinfo = None
        if stack_info:
            sio = io.StringIO()
            sio.write('Stack (most recent call last):\n')
            traceback.print_stack(f, file=sio)
            sinfo = sio.getvalue()
            if sinfo[-1] == '\n':
                sinfo = sinfo[:-1]
            sio.close()
        rv = (co.co_filename, f.f_lineno, co.co_name, sinfo)
        break
    return rv


class WarningLogSummary(object):
    """
    Used in the summary emails
    """
    def __init__(self, title, count):
        self.title = title
        self.count = count


class WarningLog(object):
    """
    Usage:

    from littlefish.warninglog import WarningLog

    warning_log = WarningLog(__name__)

    def some_function():
        # Log a simple message
        warning_log.log_message('This is a warning!')

        try:
            a = 4 / 0
        except:
            # Log an exception
            warning_log.log_exception('An exception was raised')
    """
    def __init__(self, name):
        self.name = name
    
    def _log(self, location, function, title, description, traceback_string=None):
        """
        Log a message to the WarningLogMessage table
        
        :param location: The filename and number
        :param function: The function name
        :param title: The title - should be the same for all similar errors
        :param description:  Detailed description of the error
        :param traceback_string: String with traceback (optional)
        """
        if WarningLogMessage is None:
            raise Exception('Tried to log a warning with warninglog without '
                            'calling init()')

        message = '{}:{} - {}'.format(self.name, title, description)
        if traceback_string:
            message = '{}\n{}'.format(message, traceback_string)
        
        # If the error has been reported more tha ERROR_REPORT_THRESHOLD today, we need
        # to log an error, otherwise just a warning
        today = datetime.date.today()
        period_start = datetime.datetime(today.year, today.month, today.day)
        
        log_warning = True

        if _ERROR_REPORT_THRESHOLD is not None:
            number_of_errors = 0

            try:
                # Create another session so that we can query from the database even if it's in an inconsistent state
                session = _Session()

                number_of_errors = session.query(WarningLogMessage).filter(
                    WarningLogMessage.title == title,
                    WarningLogMessage.timestamp >= period_start
                ).count()

                session.close()

            except Exception:
                log.exception('Couldn\'t load error count when logging warning')
                number_of_errors = 0

            log_warning = number_of_errors < _ERROR_REPORT_THRESHOLD
        
        if log_warning:
            log.warning(message)
        else:
            log.error('Warning log message has been reported {}/{} times today: {}'.format(
                number_of_errors, _ERROR_REPORT_THRESHOLD, message
            ))
        
        if save_warninglog_message_task:
            # Use Celery if possible
            save_warninglog_message_task.delay(datetime.datetime.utcnow(), self.name, location, function, title,
                                               description, traceback_string)
        else:
            save_warninglog_message(datetime.datetime.utcnow(), self.name, location, function, title,
                                    description, traceback_string)
    
    def log_message(self, title, description='(no further details)'):
        """
        Log a message to the WarningLog table
        
        :param title: The title - should be the same for all similar errors
        :param description:  Detailed description of the error
        """
        file_name, line_number, func, stack_info = _find_caller()
        
        try:
            location = '{}:{}'.format(file_name, line_number)
        except Exception:
            location = 'UNKNOWN:???'
        
        self._log(location, func, title, description)
        
    def log_exception(self, title, description='(no further details)'):
        """
        Log a message with the current traceback
        
        :param title: The title - should be the same for all similar errors
        :param description:  Detailed description of the error
        """
        file_name, line_number, func, stack_info = _find_caller()
        
        f = io.StringIO()
        traceback.print_exc(file=f)
        traceback_string = f.getvalue()
        
        try:
            location = '{}:{}'.format(file_name, line_number)
        except Exception:
            location = 'UNKNOWN:???'
            
        self._log(location, func, title, description, traceback_string)


def get_warninglog_summary(start_timestamp=None, end_timestamp=None):
    """
    If no timestamps are passed in this will return yesterday's data
    """
    now = datetime.datetime.utcnow()
    today = datetime.datetime(year=now.year, month=now.month, day=now.day)
    yesterday = today - datetime.timedelta(days=1)

    if start_timestamp is None:
        start_timestamp = yesterday

    if end_timestamp is None:
        end_timestamp = today

    if end_timestamp <= start_timestamp:
        raise ValueError('Invalid date range: {} to {}'.format(start_timestamp, end_timestamp))
    
    # SELECT title, COUNT(*) FROM warning_log_message GROUP BY title;
    session = _Session()
    rows = session.query(
        WarningLogMessage.title, func.count(WarningLogMessage.id)
    ).filter(
        WarningLogMessage.timestamp >= yesterday,
        WarningLogMessage.timestamp < today
    ).group_by(
        WarningLogMessage.title
    ).order_by(
        WarningLogMessage.title
    ).all()

    summary = []
    for row in rows:
        summary.append(WarningLogSummary(row[0], row[1]))

    return summary
