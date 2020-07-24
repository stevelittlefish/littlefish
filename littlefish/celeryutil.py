"""
Utilities to manage Celery
"""

import logging
from functools import wraps
import datetime

from celery import current_task

from littlefish import lfsmailer
from littlefish import redisutil


__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


class CeleryEmailHandler(lfsmailer.LfsSmtpHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = datetime.datetime.utcnow()

    def emit(self, record):
        # Catch errors from reseting sqlalchemy connections on startup
        now = datetime.datetime.utcnow()
        if now - self.created < datetime.timedelta(seconds=20) and 'reset or similar' in record.message:
            print('Not sending error email (startup error): {}'.format(record.message))
        else:
            super().emit(record)

    def add_details(self, message):
        return message


def get_enable_celery_error_reporting_function(site_name, from_address):
    """
    Use this to enable error reporting.  You need to put the following in your tasks.py or wherever you
    want to create your celery instance:

    celery = Celery(__name__)

    enable_celery_email_logging = get_enable_celery_error_reporting_function('My Website [LIVE]', 'errors@mywebsite.com')
    after_setup_logger.connect(enable_celery_email_logging)
    after_setup_task_logger.connect(enable_celery_email_logging)
    """
    def enable_celery_email_logging(sender, signal, logger, loglevel, logfile, format, colorize, **kwargs):
        from celery import current_app
        log.info('>> Initialising Celery task error reporting for logger {}'.format(logger.name))
        
        send_errors = current_app.conf['CELERY_SEND_TASK_ERROR_EMAILS']
        send_warnings = current_app.conf['CELERY_SEND_TASK_WARNING_EMAILS']

        if send_errors or send_warnings:
            error_email_subject = '{} Celery ERROR!'.format(site_name)
            celery_handler = CeleryEmailHandler(from_address, current_app.conf['ADMIN_EMAILS'],
                                                error_email_subject)

            if send_warnings:
                celery_handler.setLevel(logging.WARNING)
            else:
                celery_handler.setLevel(logging.ERROR)
            
            logger.addHandler(celery_handler)

    return enable_celery_email_logging


def init_celery(app, celery):
    """
    Initialise Celery and set up logging

    :param app: Flask app
    :param celery: Celery instance
    """
    celery.conf.update(app.config)
    
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    
    return celery


def non_overlapping(blocking, key=None, timeout=None):
    """
    Celery decorator to make tasks "non-overlapping". When an instance of this task starts
    while another instance is already running:

    If blocking is set to True then the second task will wait for the first task's lock to be
    released.

    If blocking is set to False then the second task will abort.

    :param blocking: Whether or not to wait for the existing task to finish
    :param key: If set, this is the key used in Redis for locking. Otherwise the key is generated
                from the task name
    :param timeout: If set, this is how long the lock can be held for, in seconds, before being
                    automatically released
    """
    def decorator(f):
        @wraps(f)
        def outer(*args, **kwargs):
            base_key = key
            if base_key is None:
                base_key = current_task.name

            if not base_key:
                raise Exception('No key for non-overlapping task!')

            lock = redisutil.get_non_overlapping_task_lock(base_key, timeout)

            if blocking:
                # Blocking - will wait for the lock
                with lock:
                    return f(*args, **kwargs)
            else:
                # Non-blocking - will give up if the lock isn't free
                return_value = None
                raised_exception = None
                has_lock = None

                try:
                    has_lock = lock.acquire(blocking=False)
                    if has_lock:
                        return_value = f(*args, **kwargs)
                    else:
                        log.info('Aborting task - already running')
                except Exception as e:
                    raised_exception = e
                finally:
                    if has_lock:
                        lock.release()
                    
                    if raised_exception:
                        raise raised_exception

                    return return_value

        return outer
    return decorator


def non_overlapping_block(f):
    return non_overlapping(True)(f)


def non_overlapping_discard(f):
    return non_overlapping(False)(f)


