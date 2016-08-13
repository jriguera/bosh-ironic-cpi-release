#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

from ironic_cpi.action import CPIAction
from ironic_cpi.action import CPIActionError
from ironic_cpi.actions.utils.ironic import connect as Ironic
from ironic_cpi.actions.registry.registry import Registry
from ironic_cpi.actions.registry.registry import RegistryError

# Import ironic exceptions
from ironicclient import exceptions as ironic_exception



# ALL Disk operations are fake operations, because we are playing with physical
# hardware, the disks are usually there (e.g /dev/sdb)!
# It could perform some checks using the data provided by Ironic Inspector ...

class Detach_Disk(CPIAction):
    action = 'detach_disk'

    ##
    # Detaches disk from the VM.
    # If the persistent disk is attached to a VM that will be deleted, it’s 
    # more likely delete_vm CPI method will be called without a call to 
    # detach_dis with an expectation that delete_vm will make sure disks are 
    # disassociated from the VM upon its deletion.
    # Agent settings should have been updated to remove information about 
    # given disk.
    #
    # @param vm_cid [String]: Cloud ID of the VM.
    # @param disk_cid [String]: Cloud ID of the disk.
    def run(self, config):
        vm_cid = self.args[0]
        disk_id = self.args[1]
        self.logger.debug("Detaching disk id '%s' from server id '%s'" % (disk_id, vm_cid))
        # Decode the device path from the uuid
        mac, device = self.settings.decode_disk(disk_id)
        ironic = Ironic(config['ironic'], self.logger)
        # Check if disk is for this server (see name format) and if it is in
        # Ironic metadata
        disks = []
        try:
            node = ironic.node.get(vm_cid)
            disks = node.instance_info['disks']
            if disk_id not in disks:
                msg = "Server '%s' has no attached disk" % (vm_cid)
                long_msg = msg + ": %s" % (disk_id)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
        except ironic_exception.ClientException as e:
            msg = "Error getting server '%s' metadata disks" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        # Update registry without the disk
        try:
            registry = Registry(config['registry'], vm_cid)
            registry.delete_disk(disk_id)
        except RegistryError as e:
            msg = "Error deleting disk registry configuration for server id '%s'" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        self.logger.debug("Removed disk id '%s' from server id '%s' registry" % (disk_id, vm_cid))
        # Update metadata (for attach_disk and get_disks)
        disks.remove(disk_id)
        disks_update = {
            'op': "replace",
            'path': "/instance_info/disks",
            'value': disks
        }
        self.logger.debug("Updating disks in server's id '%s' metadata" % (vm_cid))
        try:
            ironic.node.update(vm_cid, [disks_update])
        except ironic_exception.ClientException as e:
            msg = "Error updating server's id '%s' disks metadata" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        self.logger.debug("Detached disk id '%s' from server id '%s'" % (disk_id, vm_cid))


# EOF

