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

class Create_Disk(CPIAction):
    action = 'create_disk'

    ##
    # Creates disk with specific size. Disk does not belong to any given VM.
    #
    # @param size [Integer]: Size of the disk in MiB.
    # properties [Hash]: Cloud properties hash specified in the deployment
    # manifest under the disk pool.
    # @param vm_cid [String]: Cloud ID of the VM created disk will most likely
    # be attached; it could be used to .optimize disk placement so that disk is
    # located near the VM.
    #
    # @return [String] Disk id
    def run(self, config):
        size = self.args[0]
        properties = self.args[1]
        vm_cid = self.args[2]
        # TODO: inspector checks
        device = self.settings.disk_persistent_device
        if 'device' in properties:
            device = properties['device']
        # Create diskid by encoding the server id. Useful to decode in
        # attach and detach disk functions
        disk_id = device.replace('/dev', vm_cid, 1).replace('/', '-')
        self.logger.debug("Created disk '%s'" % disk_id)
        return disk_id


