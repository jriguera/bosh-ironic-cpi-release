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

class Delete_Disk(CPIAction):
    action = 'delete_disk'

    ##
    # Deletes disk. Assume that disk was detached from all VMs.
    #
    # @param disk_cid [String]: Cloud ID of the disk to delete;
    #  returned from create_disk.
    def run(self, config):
        disk_cid = self.args[0]
        self.logger.debug("Deleted disk '%s'" % disk_cid)


