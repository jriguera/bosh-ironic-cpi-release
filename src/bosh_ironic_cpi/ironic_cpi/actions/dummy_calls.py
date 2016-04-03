#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals, print_function

from ironic_cpi.action import CPIAction
from ironic_cpi.action import CPIActionError



class Dummy_Call(CPIAction):
    pass



class Dummy_Call2(CPIAction):
    def run(self, args):
        return "dummy2"



class Dummy_Call3(CPIAction):
    def run(self, args):
        msg = "Dummy Error"
        long_msg = "Exception dummy"
        raise CPIActionError(msg, long_msg)


# EOF
