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
        # Decode the device path from the uuid
        device = disk_id.replace(vm_cid, '/dev', 1).replace('-', '/')
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
            registry = Registry(config['registry'], vm_cid, self.logger)
            registry.delete_disk(disk_id)
        except RegistryError as e:
            msg = "Cannot create disk registry configuration"
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        msg = "Removed disk '%s' from server '%s' registry" % (disk_id, vm_cid)
        self.logger.debug(msg)
        # Update metadata (for attach_disk and get_disks)
        disks.remove(disk_id)
        metadata_item = {
            'op': "add",
            'value': disks,
            'path': "/instance_info/disks"
        }
        msg = "Updating disks in server's '%s' metadata" % (vm_cid)
        self.logger.debug(msg)
        try:
            ironic.node.update(vm_cid, [metadata_item])
        except ironic_exception.ClientException as e:
            msg = "Error updating server's '%s' disks metadata" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        msg = "Detached diskid '%s' from server '%s'" % (disk_id, vm_cid)
        self.logger.debug(msg)


