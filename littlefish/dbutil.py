"""
Functions for interacting with Flask SQLAlchemy models
"""

import logging

__author__ = 'Stephen Brown (Little Fish Solutions LTD)'

log = logging.getLogger(__name__)


def fast_count(db, Model):  # noqa
    """
    Do a fast but sometimes inaccurate count (postgresql only).

    :param db: SQLAlchemy instance
    :param Model: Model class i.e. User, Order...
    """
    return db.session.execute(
        'SELECT n_live_tup FROM pg_stat_all_tables WHERE relname = :tablename',
        {'tablename': Model.__tablename__}
    ).scalar()
