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

class Attach_Disk(CPIAction):
    action = 'attach_disk'

    ##
    # Attaches disk to the VM.
    # Typically each VM will have one disk attached at a time to store 
    # persistent data; however, there are important cases when multiple disks 
    # may be attached to a VM. Most common scenario involves persistent data 
    # migration from a smaller to a larger disk. Given a VM with a smaller disk
    # attached, the operator decides to increase the disk size for that VM, so
    # new larger disk is created, it is then attached to the VM. The Agent then
    # copies over the data from one disk to another, and smaller disk 
    # subsequently is detached and deleted.
    # Agent settings should have been updated with necessary information about
    # given disk.
    #
    # @param vm_cid [String]: Cloud ID of the VM.
    # @param disk_cid [String]: Cloud ID of the disk.
    def run(self, config):
        vm_cid = self.args[0]
        disk_id = self.args[1]
        # Decode the device path from the uuid
        device = disk_id.replace(vm_cid, '/dev', 1).replace('-', '/')
        # Update metadata with the disk id (for detach_disk and get_disks)
        ironic = Ironic(config['ironic'], self.logger)
        # Check if disk is attached
        try:
            node = ironic.node.get(vm_cid)
            if disk_id in node.instance_info['disks']:
                msg = "Server '%s' has already attached a disk" % (vm_cid)
                long_msg = msg + ": %s" % (disk_id)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
        except ironic_exception.ClientException as e:
            msg = "Error getting server '%s' metadata disks" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        # Update registry with the new disk
        try:
            registry = Registry(config['registry'], vm_cid, self.logger)
            registry.set_disk(disk_id, device)
        except RegistryError as e:
            msg = "Cannot create disk registry configuration"
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        # Add disk to metadata
        metadata_item = {
            'op': "add",
            'value': disk_id,
            'path': "/instance_info/disks"
        }
        msg = "Adding disk '%s' to server's '%s' metadata" % (disk_id, vm_cid)
        self.logger.debug(msg)
        try:
            ironic.node.update(vm_cid, [metadata_item])
        except ironic_exception.ClientException as e:
            msg = "Error updating server's '%s' metadata" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        msg = "Attached disk '%s' to server '%s'" % (disk_id, vm_cid)
        self.logger.debug(msg)


