#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import shutil
import tempfile
import os
import json
import StringIO
import requests
import time
import ast
try:
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

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

# Import ironic libs
from ironicclient import exceptions as ironic_exception
from ironicclient.common import utils


class Create_VM(CPIAction):
    action = 'create_vm'

    def __init__(self, context):
        super(Create_VM, self).__init__(context)
        self.repository = RepositoryManager(self.logger)


    # Define stemcell image URL and get the md5 checksum
    def _get_stemcell(self, config, stemcell_id):
        # Image repository parameters
        image_id = stemcell_id + self.settings.stemcell_image_ext
        image_meta = stemcell_id + self.settings.stemcell_metadata_ext
        repository =  self.repository.manage(config)
        self.logger.debug("Checking if stemcell '%s' exists" % (stemcell_id))
        try:
            if not repository.exists(image_id) or not repository.exists(image_meta):
                msg = "Cannot find stemcell id '%s'" % stemcell_id
                long_msg = msg + ': %s and/or %s not found on repostitory'
                long_msg = long_msg % (image_id, image_meta)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
            msg = "Stemcell '%s' found on repository" % (stemcell_id)
            self.logger.debug(msg)
        except RepositoryError as e:
            msg = "Error accessing '%s' on repository" % (stemcell_id)
            long_msg = msg + ': %s' % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        stemcell_base_url = config['url']
        if not stemcell_base_url.endswith('/'):
            stemcell_base_url += '/'
        image_url = stemcell_base_url + image_id
        image_md5 = requests.get(stemcell_base_url + image_meta).content
        image_md5 = image_md5.split(' ', 1)[0]
        self.logger.info("Stemcell URL '%s', md5: %s" % (image_url, image_md5))
        return (image_url, image_md5)


    # Update instance id in Ironic with the stemcell and other metadata
    def _set_ironic_metadata(self, ironic, uuid, image_url, image_md5,
                             configdrive_url, agent_id, defined):
        self.logger.info("Defining metadata for new server '%s'" % (uuid))
        try:
            metadata_items = [
                {'value': str(defined), 'path': "/instance_info/bosh_defined"},
                {'value': image_url, 'path': "/instance_info/image_source"},
                {'value': image_md5, 'path': "/instance_info/image_checksum"},
                {'value': configdrive_url, 'path': "/instance_info/configdrive"},
                {'value': [], 'path': "/instance_info/disks"},
                {'value': agent_id, 'path': "/instance_uuid"}
            ]
            for item in metadata_items:
                metadata_item = item
                metadata_item['op'] = "add"
                try:
                    ironic.node.update(uuid, [metadata_item])
                except:
                    metadata_item['op'] = "replace"
                    ironic.node.update(uuid, [metadata_item])
        except ironic_exception.ClientException as e:
            msg = "Error defining server '%s' on Ironic" % (uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)


    # Define the registry configuration
    def _set_registry(self, ironic, registry, uuid, agent_id, agent, blobs_cfg, 
                      disks, env, mac=None, certs=None):
        mbus = agent['mbus']
        try:
            ntp = ast.literal_eval(agent.get('ntp', '[]'))
        except:
            msg = "Cannot parse ntp as list in agent cpi configuration"
            self.logger.error(msg)
            raise CPIActionError(msg, msg)
        # TODO check with Ironic inspector all disk parameters
        system_disk = self.settings.disk_system_device
        # Create blobstore
        blobstore = {
            'options': {},
            'provider': blobs_cfg.get('provider', 'local')
        }
        for key in blobs_cfg:
            if key != 'provider':
                blobstore['options'][key] = blobs_cfg[key]
        try:
            registry.create(
                agent_id, mbus, ntp, system_disk, blobstore, env, certs)
            for net in networks:
                provided_net = networks[net]
                default_mac = None
                if 'default' in provided_net:
                    if 'gateway' in provided_net['default']:
                        default_mac = mac
                dhcp = False
                if 'ip' not in provided_net:
                    dhcp = True
                registry.set_network(
                    net, provided_net, mac=default_mac, dhcp=dhcp)
        except RegistryError as e:
            msg = "Cannot create registry configuration"
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)


    # Define the configdrive
    def _set_configdrive(self, config, uuid, registry, networks=None, mac=None):
        # Get configdrive parameters
        self.logger.info("Creating configdrive for new server '%s'" % (uuid))
        registry_url = registry.url
        create_files = config.get('create_files', '').lower() in ['1', 'yes', 'true']
        try:
            nameservers = ast.literal_eval(config.get('nameservers', '[]'))
        except:
            msg = "Cannot parse nameservers as list in cpi configuration"
            self.logger.error(msg)
            raise CPIActionError(msg, msg)
        try:
            publickeys = ast.literal_eval(config.get('publickeys', '[]'))
        except:
            msg = "Cannot parse publickeys as list in cpi configuration"
            self.logger.error(msg)
            raise CPIActionError(msg, msg)
        # Create configdrive
        try:
            repository =  self.repository.manage(config)
            configdrive = Configdrive(
                uuid, self.logger, self.settings.configdrive_ext)
            configdrive.set_meta_data(public_keys)
            configdrive.set_user_data(registry_url, nameservers, networks, mac)
            configdrive_id = configdrive.create(repository, create_files)
        except Exception as e:
            msg = "%s: %s" % (type(e).__name__, e)
            self.logger.error(msg)
            raise CPIActionError(msg, msg)
        configdrive_base_url = config['url']
        if not configdrive_base_url.endswith('/'):
            configdrive_base_url += '/'
        configdrive_url = configdrive_base_url + configdrive_id
        self.logger.info("Configdrive URL %s" % (configdrive_url))
        return configdrive_url


    ##
    # Creates an Ironic server and waits until it's in running state
    #
    # @param [String] agent_id UUID for the agent that will be used later on by
    #   the director to locate and talk to the agent
    # @param [String] stemcell_id OpenStack image UUID that will be used to
    #   power on new server
    # @param [Hash] resource_pool cloud specific properties describing the
    #   resources needed for this VM
    # @param [Hash] network_spec list of networks and their settings needed for
    #   this VM
    # @param [optional, Array] disk_locality List of disks that might be
    #   attached to this server in the future, can be used as a placement
    #   hint (i.e. server will only be created if resource pool availability
    #   zone is the same as disk availability zone)
    # @param [optional, Hash] environment Data to be merged into agent settings
    # @return [String] OpenStack server UUID
    def run(self, config):
        agent_id = self.args[0]
        stemcell_id = self.args[1]
        resource_pool = self.args[2]
        network_spec = self.args[3]
        disk_locality = self.args[4]
        environment = self.args[5]
        # Stemcell/image
        image_url, image_md5 = self._get_stemcell(config['stemcell'], stemcell_id)
        # Ironic definition
        ironic = Ironic(config['ironic'], self.logger)
        mac = resource_pool.get('mac', None)
        define = False
        try:
            if mac and 'ironic_params' in resource_pool:
                # Define the server in Ironic
                define = True
                ironic_params = resource_pool['ironic_params']
                node = ironic.node.create(**ironic_params)
                # Define the MAC port
                port = {
                    'address': mac,
                    'node_uuid': node.uuid
                }
                try:
                    ironic.port.create(**port)
                except ironic_exception.ClientException as e:
                    msg = "Error creating port '%s' for server '%s'"
                    msg = msg % (mac, node.uuid)
                    long_msg = msg + ": %s. Rollback for deleting server" % (e)
                    self.logger.error(long_msg)
                    ironic.node.delete(node.uuid)
                    raise CPIActionError(msg, long_msg)
            elif mac:
                # Get node by MAC
                try:
                    port = ironic.port.get_by_address(mac)
                    node = ironic.node.get(port.node_uuid)
                except ironic_exception.ClientException as e:
                    msg = "Error, server not found with MAC '%s'" % (mac)
                    long_msg = msg + ": %s" % (e)
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)
            else:
                # TODO: Search all defined nodes for one free
                # TODO Look at inspector data
                msg = "Not implemented!"
                long_msg = msg + ": " + "MAC address not defined"
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
        except ironic_exception.ClientException as e:
            msg = "Error defining server for agent id '%s' on Ironic" % (agent_id)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        # Registry connection configuration
        registry = Registry(config['registry'], node.uuid, self.logger)
        # Configdrive
        configdrive_url = self._set_configdrive(
            config['metadata'], node.uuid, registry, network_spec, mac)
        # Do registry configuration
        self._set_registry(
            ironic, registry, node.uuid, agent_id, config['agent'],
            config['blobstore'], disk_locality, environment, mac)
        # Define the rest of the metadata in ironic properties
        self._set_ironic_metadata(
            ironic, node.uuid, image_url, image_md5, configdrive_url,
            agent_id, define)
        try:
            ironic.node.set_provision_state(node.uuid, 'active', configdrive_url)
        except ironic_exception.ClientException as e:
            msg = "Error provisioning server '%s'" % (node.uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        self.logger.info(
            "Server '%s' defined with agent_id '%s'" % (node.uuid, agent_id))

        # Wait until node is active.
        # An active node means that node was deployed successfully is being
        # rebooted to boot using the stemcell. if it does not wait here,
        # set_vm_metadata will fail because Ironic cannot set metadata while
        # a server is transitioning between states. Moreover the
        # Director timeout of 600s waiting for the agent to become active: a
        # lot of hardware needs more than 600 to complete the entire process
        # (long time for rebooting and posts checks)
        ironic_timer = self.settings.ironic_sleep_times
        ironic_sleep = self.settings.ironic_sleep_seconds
        try:
            while ironic_timer > 0:
                status = ironic.node.states(node.uuid).provision_state
                msg = "Server '%s' status '%s'" % (node.uuid, status)
                self.logger.debug(msg)
                if status == 'deploy failed':
                    # failed!
                    msg = "Error provisioning server '%s'" % (node.uuid)
                    long_msg = msg + ": 'deploy failed'. See Ironic logs."
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)
                if status == 'active':
                    # done
                    break
                time.sleep(ironic_sleep)
                ironic_timer -= 1
            else:
                msg = "Server '%s' did not become 'active' after %ds"
                msg = msg % (node.uuid,
                    (self.settings.ironic_sleep_times * ironic_sleep))
                long_msg = msg + ": timeout"
                logger.self.error(long_msg)
                raise CPIActionError(msg, long_msg)
        except ironic_exception.ClientException as e:
            msg = "Error activating server '%s'" % (node.uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        return node.uuid

# EOF

