"""
Utility functions for dealing with files
"""

import logging
import hashlib

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


def extension_from_filename(filename):
    return filename.rsplit('.')[-1]


def read_file(filename):
    with open(filename, 'rb') as f:
        file_data = f.read()
        return file_data


def write_file(filename, data):
    with open(filename, 'wb') as f:
        f.write(data)


def file_md5sum(filename):
    """
    :param filename: The filename of the file to process
    :returns: The MD5 hash of the file
    """
    hash_md5 = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 4), b''):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def bytes_md5sum(bytes_):
    hash_md5 = hashlib.md5()
    hash_md5.update(bytes_)
    return hash_md5.hexdigest()

