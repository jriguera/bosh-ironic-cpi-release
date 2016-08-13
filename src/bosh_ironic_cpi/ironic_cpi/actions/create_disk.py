#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

from ironic_cpi.action import CPIAction
from ironic_cpi.actions.utils.ironic import connect as Ironic



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
        # TODO: do inspector checks
        self.logger.debug("Creating disk size %s MiB for server id '%s' with properties: %s" % (size, properties, vm_cid))
        device = self.settings.disk_persistent_device
        if 'device' in properties:
            device = properties['device']
        ironic = Ironic(config['ironic'], self.logger)
        # Get the MAC address to build the disk id
        try:
            ports = ironic.node.list_ports(vm_cid)
            # 1st mac address (just one)
            mac = ports[0].address
        except Exception as e:
            msg = "Error, cannot get MAC(s) address for server id '%s'" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        # Create diskid by encoding the mac. Useful to decode in
        # attach and detach disk functions
        disk_id = self.settings.encode_disk(mac, device, size)
        self.logger.debug("Created disk '%s'" % (disk_id))
        return disk_id


# EOF

