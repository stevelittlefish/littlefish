"""
Utilities to implement extra functionality using Redis
"""

import logging
import contextlib

import redis

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


connection = None
LOCK_TIMEOUT = None
GLOBAL_KEY_PREFIX = None

# Key templates for locks
LOCK_KEY_NON_OVERLAPPING_TASK = 'locks:non-overlapping:{base_key}'


@contextlib.contextmanager
def multi_key_lock(keys, timeout=None):
    if isinstance(keys, str):
        raise ValueError('You can\'t pass a single string into this function!')
    
    # Check for duplicates in list
    if len(keys) != len(set(keys)):
        raise ValueError('The passed in keyset contains duplicates: "{}"'.format(
            '", "'.join(keys)
        ))

    # Sort keys into alphabetical order
    keys = sorted(keys)
    
    if timeout is None:
        timeout = LOCK_TIMEOUT

    locks = []
    for key in keys:
        lock = connection.lock(format_key(key), timeout=timeout)
        locks.append(lock)
        
        log.debug('Acquiring lock "{}"'.format(lock.name))
        lock.acquire(blocking=True)
    
    log.debug('All locks acquired!')

    # Do whatever it is that needs doing!
    try:
        yield
    finally:
        # Now we release the locks in reverse order
        locks = reversed(locks)

        for lock in locks:
            log.debug('Releasing lock "{}"'.format(lock.name))
            lock.release()


def init(app):
    """
    Initialise this library.  The following config variables need to be in your Flask config:

    REDIS_HOST: The host of the Redis server
    REDIS_PORT: The port of the Redis server
    REDIS_PASSWORD: The password used to connect to Redis or None
    REDIS_GLOBAL_KEY_PREFIX: A short string unique to your application i.e. 'MYAPP'.  This will be turned into
                             a prefix like '~~MYAPP~~:' and will be used to allow multiple applications to share
                             a single redis server
    REDIS_LOCK_TIMEOUT: An integer with the number of seconds to wait before automatically releasing a lock.
                        A good number is 60 * 5 for 5 minutes.  This stops locks from being held indefinitely
                        if something goes wrong, but bear in mind this can also cause concurrency issues if
                        you ave a locking process that takes longer than this timeout!
    """
    global connection, LOCK_TIMEOUT, GLOBAL_KEY_PREFIX

    host = app.config['REDIS_HOST']
    port = app.config['REDIS_PORT']
    password = app.config['REDIS_PASSWORD']
    
    GLOBAL_KEY_PREFIX = '~~{}~~:'.format(app.config['REDIS_GLOBAL_KEY_PREFIX'])
    LOCK_TIMEOUT = app.config['REDIS_LOCK_TIMEOUT']

    connection = redis.StrictRedis(host=host, port=port, password=password)


def format_key(name):
    return '{}{}'.format(GLOBAL_KEY_PREFIX, name)


def get_lock(name, timeout=None):
    if timeout is None:
        timeout = LOCK_TIMEOUT

    return connection.lock(format_key(name), timeout=timeout)


def get_non_overlapping_task_lock(base_key, timeout=None):
    """
    Returns a lock for non-overlapping tasks

    :param base_key: The unique identifier, usually the task name
    """
    key = LOCK_KEY_NON_OVERLAPPING_TASK.format(base_key=base_key)
    return get_lock(key, timeout=timeout)


