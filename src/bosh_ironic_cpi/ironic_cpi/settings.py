
#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import re



class CPISettings(object):
    _instance = None
    _string_booleans_true = ['1', 'yes', 'true', 'on']
    _re_macaddr = re.compile("^([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})$")

    def __new__(cls, *args, **kwargs):
        # Singleton implementation
        if not cls._instance:
            cls._instance = super(CPISettings, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        self.configdrive_ext = '.cfgd'
        self.stemcell_image_ext = '.qcow2'
        self.stemcell_metadata_ext = '.meta'
        self.stemcell_image = 'root.img'
        self.stemcell_id_format = 'stemcell_{os_distro}-{architecture}-{version}'
        # To setup the name in set_vm_metadata
        self.server_name = '{job}-{index}'
        # Sort of timeout for waiting in ironic loops (create_vm, delete_vm).
        # 30s x 40 is the limit
        self.ironic_sleep_times = 40
        self.ironic_sleep_seconds = 30
        # Default settings for registry
        self.disk_system_device = '/dev/sda'
        self.disk_ephemeral_device = '/dev/sdb'
        self.disk_persistent_device = '/dev/sdc'
        # Ironic
        self.ironic_search_state = 'manageable'

    def encode_disk(self, mac, device, size):
        disk_id = mac.replace(':','')
        disk_id = disk_id + '-' + device.replace('/dev/', '', 1).replace('/', '-')
        disk_id = str(int(time.time()*10)) + '-' + disk_id
        return disk_id

    def decode_disk(self, disk_id):
        t, mac, d = disk_id.split('-', 2)
        macaddr = ':'.join([mac[i:i+2] for i in range(0, len(mac), 2)])
        device = '/dev/' + d.replace('-', '/')
        return (macaddr, device)

