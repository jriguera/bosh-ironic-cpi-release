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
from ironic_cpi.actions.ironic import connect as Ironic
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
        metadata_items = [
            {'op': 'remove', 'path': "/instance_info/bosh_defined"},
            {'op': 'remove', 'path': "/instance_info/image_source"},
            {'op': 'remove', 'path': "/instance_info/image_checksum"},
            {'op': 'remove', 'path': "/instance_info/configdrive"},
            {'op': 'remove', 'path': "/instance_info/disks"},
            {'op': 'remove', 'path': "/instance_uuid"},
            {'op': 'remove', 'path': "/name"}
        ]
        try:
            ironic.node.update(node_uuid, metadata_items)
        except ironic_exception.ClientException as e:
            msg = "Error deleting metadata of server '%s'" % (node_uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            #raise CPIActionError(msg, long_msg)


    def _delete_configdrive(self, config, uuid):
        self.logger.info("Deleting configdrive for server '%s'" % uuid)
        delete_files = config.get('create_files', '').lower() in ['1', 'yes', 'true']
        try:
            repository =  self.repository.manage(config)
            configdrive = Configdrive(
                uuid, self.logger, self.settings.configdrive_ext)
            configdrive.delete(repository, delete_files)
        except Exception as e:
            msg = "%s: %s" % (type(e).__name__, e)
            self.logger.error(msg)
            raise CPIActionError(msg, msg)


    def _delete_registry(self, registry):
        try:
            registry.delete()
        except RegistryError as e:
            msg = "Cannot delete registry configuration"
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)


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
        # Sort of timeout for waiting in ironic loops. 30s x 40 is the limit
        ironic_timer = self.settings.ironic_sleep_times
        ironic_sleep = self.settings.ironic_sleep_seconds
        # Delete Registry configuration
        registry = Registry(config['registry'], vm_cid, self.logger)
        self._delete_registry(registry)
        # Configdrive metadata repository
        self._delete_configdrive(config['metadata'], vm_cid)
        # Undefine the node in Ironic to make it available
        ironic = Ironic(config['ironic'], self.logger)
        # Retrieve the value from the metadata
        clean = None
        delete = False
        self.logger.debug("Retrieving metadata for server '%s'" % (vm_cid))
        try:
            node = ironic.node.get(vm_cid)
            delete = bool(node.instance_info['bosh_defined'])
        except ironic_exception.ClientException as e:
            msg = "Error getting server info '%s'" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        except:
            msg = "Error getting metadata of server '%s'" % (vm_cid)
            long_msg = msg + ": %s" % (e)
            self.logger.warning(long_msg)
        if node.provision_state != 'available':
            self.logger.debug("Deleting (cleaning) server '%s'" % (vm_cid))
            try:
                ironic.node.set_provision_state(vm_cid, 'deleted')
                while ironic_timer > 0:
                    status = ironic.node.states(vm_cid).provision_state
                    if status == 'available':
                        msg = "Server '%s' status '%s'" % (vm_cid, status)
                        self.logger.debug(msg)
                        break
                    msg = "Server '%s' status '%s', waiting" % (vm_cid, status)
                    self.logger.debug(msg)
                    time.sleep(ironic_sleep)
                    ironic_timer -= 1
                else:
                    msg = "Server '%s' did not become available after %ds"
                    msg = msg % (vm_cid,
                        (self.settings.ironic_sleep_times * ironic_sleep))
                    long_msg = msg + ": timeout"
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)
            except ironic_exception.ClientException as e:
                msg = "Error performing cleaning of server '%s'" % (vm_cid)
                long_msg = msg + ": %s" % (e)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
        # Delete meta definitions on Ironic
        self._delete_ironic_metadata(ironic, vm_cid)
        # Delete the node from Ironic
        if delete:
            self.logger.debug("Powering off server '%s'" % (vm_cid))
            try:
                ironic.node.set_power_state(vm_cid, 'off')
            except ironic_exception.ClientException as e:
                msg = "Error powering off server '%s' on Ironic" % (vm_cid)
                long_msg = msg + ": %s" % (e)
                self.logger.warning(long_msg)
            # Wait 1m
            time.sleep(ironic_sleep * 2)
            self.logger.debug("Deleting server from Ironic '%s'" % (vm_cid))
            try:
                ironic.node.delete(vm_cid)
            except ironic_exception.ClientException as e:
                msg = "Error deleting server '%s' on Ironic" % (vm_cid)
                long_msg = msg + ": %s" % (e)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)


