"""
For doing geo ip lookups
"""

import logging

import geoip2.database
import IPy

__author__ = 'Yu Lee Paul (Little Fish Solutions LTD)'


log = logging.getLogger(__name__)

_reader = None


def init(geolite2_path):
    global _reader
    log.info('Loading geoip data from %s' % geolite2_path)
    _reader = geoip2.database.Reader(geolite2_path)


def get_geoip_data(ip):
    if should_ignore_ip_address(ip):
        return None
    return _reader.city(ip)


def should_ignore_ip_address(ip_address):
    ip = IPy.IP(ip_address)
    ip_type = ip.iptype()
    return ip_type == 'PRIVATE' or ip_type == 'LOOPBACK'
