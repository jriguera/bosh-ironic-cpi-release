#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

from ironic_cpi.action import CPIAction



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
        vm_id = self.args[0]
        disk_id = self.args[1]
        # Check if disk is for this server (see name format)
        # TODO: Check Inspector data
        # TODO: Update registry with the new disk
        # TODO: Update metadata (for detach_disk and get_disks)
        self.logger.debug("Attached disk '%s' to server '%s'" % (disk_id, vm_id))

