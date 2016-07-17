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

from ironic_cpi.actions.repositories.repository import RepositoryManager
from ironic_cpi.actions.repositories.repository import RepositoryError
# Import all repository implementations here
from ironic_cpi.actions.repositories.webdav import WebDav

from ironicclient import exceptions as ironic_exception



class Has_VM(CPIAction):
    action = 'has_vm'

    def __init__(self, context):
        super(Has_VM, self).__init__(context)
        self.repository = RepositoryManager(self.logger)

    ##
    # Checks for VM presence in Ironic
    #
    # @param [String] vm_cid cloud ID of the VM to check,
    #   returned from create_vm
    # @return [Boolean] True if VM is present
    def run(self, config):
        vm_cid = self.args[0]
        configdrive = vm_cid + self.settings.configdrive_ext
        # Ironic check
        ironic = Ironic(config['ironic'], self.logger)
        self.logger.debug("Checking if server '%s' exists in Ironic" % vm_cid)
        node = ironic.node.get(vm_cid)
        if not node:
            self.logger.info("Server '%s' not found in Ironic" % vm_cid)
            return False
        # TODO: Check maintenance status
        # Configdrive metadata repository parameters
        repository =  self.repository.manage(config['metadata'])
        self.logger.debug("Checking if server configdrive '%s' exists" % vm_cid)
        try:
            if not repository.exists(configdrive):
                self.logger.info("Configdrive for server '%s' not found" % vm_cid)
                return False
            self.logger.debug("Configdrive for server '%s' found" % vm_cid)
        except RepositoryError as e:
            msg = "Error accessing server '%s' metadata configdrive" % vm_cid
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        return True

