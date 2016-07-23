
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import sys

from ironic_cpi.settings import CPISettings as CPISettings



def is_py3():
    """Check if data can be converted to boolean"""
    return sys.version_info[0] == 3


def boolean(data):
    """Check if data can be converted to boolean"""
    if isinstance(data, bool):
        return data
    elif ((is_py3() and isinstance(data, str)) or
        ((not is_py3()) and isinstance(data, basestring))):
        return data.lower() in CPISettings._string_booleans_true
    else:
        return bool(data)


def is_macaddr(value):
    """Check if value is a MAC address"""
    if CPISettings._re_macaddr.match(value) is None:
        return False
    else:
        return True


def greater_or_equal(base, value):
    """Compare string or figures"""
    if isinstance(base, bool):
        return base == bool(value)
    elif ((is_py3() and isinstance(base, str)) or
        ((not is_py3()) and isinstance(base, basestring))):
        return base == value
    else:
        return float(base) >= float(value)


