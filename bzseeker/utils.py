from __future__ import print_function

import sys
import time


def to_timestamp(date, dt_format):
    """
    Convert the date with some format into timestamp.

    :type date: str
    :type dt_format: str
    :return: float
    """
    try:
        return time.mktime(time.strptime(date, dt_format))
    except ValueError:
        log_error('Cannot read entered date %s with the %s format!' %
                  (date, dt_format))


def log_error(message, shutdown=True):
    print('ERROR: %s' % message, file=sys.stderr)
    if shutdown:
        sys.exit(1)