#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

from ironic_cpi.action import CPIAction
from ironic_cpi.action import CPIActionError
from ironic_cpi.actions.ironic import connect as Ironic

from ironicclient import exceptions as ironic_exception



class Reboot_VM(CPIAction):
    action = 'reboot_vm'

    ##
    # Reboots the VM. Assume that VM can be either be powered on or off at the 
    # time of the call
    #
    # @param [String] vm_cid cloud ID of the VM to check,
    #   returned from create_vm
    def run(self, config):
        vm_cid = self.args[0]
        ironic = Ironic(config['ironic'], self.logger)
        self.logger.debug("Rebooting server '%s'" % vm_cid)
        try:
            node = ironic.node.set_power_state(vm_cid, 'reboot')
        except ironic_exception.ClientException as e:
            msg = "Error performing reboot of server '%s'" % vm_cid
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)

