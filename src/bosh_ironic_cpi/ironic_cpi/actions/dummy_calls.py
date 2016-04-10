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
    action = 'dummy_call'
    pass



class Dummy_Call2(CPIAction):
    action = 'dummy_call2'

    def run(self, config):
        print("----------------")
        print(config)
        print("----------------")
        print(self.args)
        print("----------------")
        return "dummy2"



class Dummy_Call3(CPIAction):
    def run(self, config):
        msg = "Dummy Error"
        long_msg = "Exception dummy"
        raise CPIActionError(msg, long_msg)


# EOF
