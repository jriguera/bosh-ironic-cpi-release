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



class Set_VM_Metadata(CPIAction):
    action = 'set_vm_metadata'

    ##
    # Sets VM's metadata to make it easier for operators to categorize VMs 
    # when looking at the IaaS management console.
    #
    # @param [String] vm_cid cloud ID of the VM to check,
    #   returned from create_vm
    # @param [Hash] metadata Collection of key-value pairs. CPI should not rely
    #   on presence of specific keys.
    def run(self, config):
        vm_cid = self.args[0]
        meta = self.args[1]
        # Ironic
        ironic = Ironic(config['ironic'], self.logger)
        name = self.settings.server_name.format(**meta)
        metadata_items = [
            {'value': name, 'path': "/name"},
            {'value': meta['director'], 'path': "/instance_info/bosh_director"},
            {'value': meta['deployment'], 'path': "/instance_info/bosh_deployment"}
        ]
        self.logger.debug("Updating server's '%s' metadata" % vm_cid)
        for item in metadata_items:
            metadata_item = item
            metadata_item['op'] = "add"
            try:
                ironic.node.update(vm_cid, [metadata_item])
            except:
                metadata_item['op'] = "replace"
                try:
                    ironic.node.update(vm_cid, [metadata_item])
                except ironic_exception.ClientException as e:
                    msg = "Error updating server's '%s' metadata" % vm_cid
                    long_msg = msg + ": %s" % (e)
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)

