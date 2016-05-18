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
        vm_id = self.args[0]
        disk_id = self.args[1]
        # Check if disk is for this server (see name format) and if it is in
        # Ironic metadata
        # TODO: Update registry!!
        # TODO: Update metadata (for attach_disk and get_disks)
        self.logger.debug("Detached disk '%s' to server '%s'" % (disk_id, vm_id))

