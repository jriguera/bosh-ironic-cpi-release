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

# Import ironic exceptions
from ironicclient import exceptions as ironic_exception



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
        vm_cid = self.args[0]
        self.logger.debug("Getting list of disks for server id '%s'" % (vm_cid))
        # TODO: Check Ironic Metadata
        # Update metadata with the disk id (for detach_disk and get_disks)
        ironic = Ironic(config['ironic'], self.logger)
        disks = []
        try:
            node = ironic.node.get(vm_cid)
            disks = node.instance_info['disks']
        except ironic_exception.ClientException as e:
            msg = "Error getting server metadata disks for server id '%s'" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        self.logger.debug("Disks attached to server id '%s': %s" % (vm_cid, disks))
        return disks


# EOF

