#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import time

from ironic_cpi.action import CPIAction
from ironic_cpi.action import CPIActionError
from ironic_cpi.actions.utils.ironic import connect as Ironic
from ironic_cpi.actions.utils.ironic import wait_for_state
from ironic_cpi.actions.utils.utils import boolean
from ironic_cpi.actions.registry.registry import Registry
from ironic_cpi.actions.registry.registry import RegistryError
from ironic_cpi.actions.configdrive.configdrive import Configdrive
from ironic_cpi.actions.configdrive.configdrive import ConfigdriveError
from ironic_cpi.actions.repositories.repository import RepositoryManager
from ironic_cpi.actions.repositories.repository import RepositoryError
# Import all repository implementations here
from ironic_cpi.actions.repositories.webdav import WebDav

# Import ironic exceptions
from ironicclient import exceptions as ironic_exception



class Delete_VM(CPIAction):
    action = 'delete_vm'

    def __init__(self, context):
        super(Delete_VM, self).__init__(context)
        self.repository = RepositoryManager(self.logger)


    def _delete_ironic_metadata(self, ironic, node_uuid):
        self.logger.debug("Deleting metadata on server id '%s'" % (node_uuid))
        metadata_items = [
            {'op': 'remove', 'path': "/instance_info/bosh_defined"},
            {'op': 'remove', 'path': "/instance_info/image_source"},
            {'op': 'remove', 'path': "/instance_info/image_checksum"},
            {'op': 'remove', 'path': "/instance_info/configdrive"},
            {'op': 'remove', 'path': "/instance_info/disks"},
            {'op': 'remove', 'path': "/instance_uuid"},
            {'op': 'remove', 'path': "/name"}
        ]
        for item in metadata_items:
            try:
                ironic.node.update(node_uuid, [item])
            except ironic_exception.ClientException as e:
                msg = "Error deleting metadata on server id '%s'" % (node_uuid)
                long_msg = msg + ": %s" % (e)
                self.logger.warning(long_msg)
                # raise CPIActionError(msg, long_msg)


    def _delete_configdrive(self, config, uuid):
        self.logger.debug("Deleting configdrive for server id '%s'" % (uuid))
        delete_files = boolean(config.get('create_files', ''))
        try:
            repository =  self.repository.manage(config)
            configdrive = Configdrive(uuid, self.settings.configdrive_ext)
            configdrive.delete(repository, delete_files)
        except Exception as e:
            msg = "Error %s: %s" % (type(e).__name__, e)
            self.logger.warning(msg)
            #raise CPIActionError(msg, msg)


    def _delete_registry(self, registry, uuid):
        self.logger.debug("Deleting registry for server id '%s'" % (uuid))
        try:
            registry.delete()
        except RegistryError as e:
            msg = "Error deleting registry configuration for server id '%s'" % (uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.warning(long_msg)
            #raise CPIActionError(msg, long_msg)


    ##
    # Delete the Server.
    # This method will be called while the VM still has persistent disks 
    # attached. It’s important to make sure that IaaS behaves appropriately in 
    # this case and properly disassociates persistent disks from the VM.
    #
    # @param [String] vm_cid cloud ID of the VM to check,
    #   returned from create_vm
    def run(self, config):
        vm_cid = self.args[0]
        ironic_sleep = self.settings.ironic_sleep_seconds
        self.logger.debug("Deleting server id '%s'" % (vm_cid))
        # Delete Registry configuration
        registry = Registry(config['registry'], vm_cid)
        self._delete_registry(registry, vm_cid)
        # Configdrive metadata repository
        self._delete_configdrive(config['metadata'], vm_cid)
        # Undefine the node in Ironic to make it available
        ironic = Ironic(config['ironic'], self.logger)
        # Retrieve the value from the metadata
        defined = 0
        # 1 > server was initially in manageable state
        # 0 > server was initially in active state
        # 2 > server defined by the CPI
        self.logger.debug("Retrieving metadata for server id '%s'" % (vm_cid))
        try:
            node = ironic.node.get(vm_cid)
            defined = int(node.instance_info['bosh_defined'])
        except ironic_exception.ClientException as e:
            msg = "Ignoring error while getting server id '%s' info" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.warning(long_msg)
            #raise CPIActionError(msg, long_msg)
            return
        except:
            msg = "Error getting metadata 'bosh_defined' on server id '%s'" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.warning(long_msg)
        # Delete meta definitions on Ironic
        self._delete_ironic_metadata(ironic, vm_cid)
        if node.provision_state != 'available':
            self.logger.debug("Deleting server id '%s'" % (vm_cid))
            try:
                ironic.node.set_provision_state(vm_cid, 'deleted')
                wait_for_state(self.logger, ironic, vm_cid,
                    self.settings.ironic_sleep_times,
                    self.settings.ironic_sleep_seconds)
            except ironic_exception.ClientException as e:
                msg = "Error performing cleaning of server id '%s'" % (vm_cid)
                long_msg = msg + ": %s" % (e)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
        # http://docs.openstack.org/developer/ironic/deploy/cleaning.html
        # Force manual cleaning steps. If cleaning steps are already defined
        # in ironic, those transitions will cause re-run them 3 times!
        clean = boolean(config['ironic'].get('clean', ''))
        if clean:
            try:
                #  [{'interface': 'deploy', 'step': 'erase_devices'}]
                cleansteps = ast.literal_eval(config['ironic'].get('clean_steps', '[]'))
            except:
                msg = "Error parsing list of clean_steps"
                long_msg = msg + ": Fix Ironic section on CPI configuration file"
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
            try:
                ironic.node.set_provision_state(vm_cid, 'manage')
                wait_for_state(self.logger, ironic, vm_cid,
                    self.settings.ironic_sleep_times,
                    self.settings.ironic_sleep_seconds,
                    'manageable')
                ironic.node.set_provision_state(vm_cid, 'clean', cleansteps=cleansteps)
                wait_for_state(self.logger, ironic, vm_cid,
                    self.settings.ironic_sleep_times,
                    self.settings.ironic_sleep_seconds,
                    'manageable')
                ironic.node.set_provision_state(vm_cid, 'provide')
                wait_for_state(self.logger, ironic, vm_cid,
                    self.settings.ironic_sleep_times,
                    self.settings.ironic_sleep_seconds,
                    'available')
            except ironic_exception.ClientException as e:
                msg = "Error cleaning server id '%s'" % (vm_cid)
                long_msg = msg + ": %s" % (e)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
        if defined == 0:
            # Server was already defined as available
            pass
        elif defined == 1:
            # In this case we assume server was in manageable state
            # so switch it back to the state
            try:
                ironic.node.set_provision_state(vm_cid, 'manage')
            except ironic_exception.ClientException as e:
                msg = "Error setting server id '%s' in manageable status" % (vm_cid)
                long_msg = msg + ": %s" % (e)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
        elif defined == 2:
            # Delete the node from Ironic
            self.logger.debug("Powering off server id '%s'" % (vm_cid))
            try:
                ironic.node.set_power_state(vm_cid, 'off')
            except ironic_exception.ClientException as e:
                msg = "Error powering off server id '%s' via Ironic" % (vm_cid)
                long_msg = msg + ": %s" % (e)
                self.logger.warning(long_msg)
            # Wait 1m
            time.sleep(ironic_sleep * 2)
            self.logger.debug("Deleting server id '%s' on Ironic" % (vm_cid))
            try:
                ironic.node.delete(vm_cid)
            except ironic_exception.ClientException as e:
                msg = "Error deleting server id '%s' on Ironic" % (vm_cid)
                long_msg = msg + ": %s" % (e)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)


# EOF

