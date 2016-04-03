#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BOSH Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import sys 
import os

# Append the folder to act as a module
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))
from ironic_cpi.cpi import main 


if __name__ == '__main__':
    sys.exit(main())

# EOF
