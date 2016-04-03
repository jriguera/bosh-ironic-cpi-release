#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI

Import all modules in this folder automatically
"""
import os.path
import glob

modules = []
for module in glob.glob(os.path.dirname(__file__) + "/*.py"):
    if os.path.isfile(module):
        name = os.path.basename(module)
        if not name.startswith('__'):
            modules.append(name[:-3])

__all__ = modules

