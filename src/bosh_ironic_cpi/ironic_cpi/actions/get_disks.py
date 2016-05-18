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

class Get_Disks(CPIAction):
    action = 'get_disks'

    ##
    # Returns list of disks currently attached to the VM.
    # This method is mostly used by the consistency check tool (cloudcheck) 
    # to determine if the VM has required disks attached.
    #
    # @param vm_cid [String]: Cloud ID of the VM.
    # @return disk_cids [List]: Array of disk_cids that are currently attached 
    # to the vm.
    def run(self, config):
        vm_id = self.args[0]
        # TODO: Check Ironic Metadata
        return []

