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

class Has_Disk(CPIAction):
    action = 'has_disk'

    ##
    # Checks for disk presence in the IaaS.
    # This method is mostly used by the consistency check tool (cloudcheck) 
    # to determine if the disk still exists.
    #
    # @param disk_cid [String]: Cloud ID of the disk to delete;
    #  returned from create_disk.
    # @return [Boolean] True if disk is present
    def run(self, config):
        disk_cid = self.args[0]
        self.logger.debug("Checking disk id '%s' existence" % (disk_cid))
        # Assuming always True!
        return True


# EOF

