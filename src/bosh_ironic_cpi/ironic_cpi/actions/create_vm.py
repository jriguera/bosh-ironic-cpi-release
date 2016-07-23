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
from ironic_cpi.actions.utils.ironic import connect as Ironic
from ironic_cpi.actions.utils.utils import boolean, is_macaddr, greater_or_equal
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
        self.logger.debug("Checking if stemcell id '%s' exists" % (stemcell_id))
        try:
            if not repository.exists(image_id) or not repository.exists(image_meta):
                msg = "Cannot find stemcell id '%s'" % (stemcell_id)
                long_msg = msg + ": %s and/or %s not found on repostitory" % (image_id, image_meta)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
            self.logger.debug("Stemcell id '%s' found on repository" % (stemcell_id))
        except RepositoryError as e:
            msg = "Error accessing stemcell id '%s' on repository" % (stemcell_id)
            long_msg = msg + ': %s' % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        stemcell_base_url = config['url']
        if not stemcell_base_url.endswith('/'):
            stemcell_base_url += '/'
        image_url = stemcell_base_url + image_id
        image_md5 = requests.get(stemcell_base_url + image_meta).content
        image_md5 = image_md5.split(' ', 1)[0]
        self.logger.debug("Stemcell URL '%s', md5: %s" % (image_url, image_md5))
        return (image_url, image_md5)


    # Update instance id in Ironic with the stemcell and other metadata
    def _set_ironic_metadata(self, ironic, uuid, image_url, image_md5,
                             configdrive_url, agent_id, defined):
        self.logger.debug("Defining metadata for server id '%s'" % (uuid))
        try:
            metadata_items = [
                {'value': str(defined), 'path': "/instance_info/bosh_defined"},
                {'value': image_url, 'path': "/instance_info/image_source"},
                {'value': image_md5, 'path': "/instance_info/image_checksum"},
                {'value': configdrive_url, 'path': "/instance_info/configdrive"},
                {'value': [], 'path': "/instance_info/disks"}
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
            msg = "Error defining metadata for server id '%s' on Ironic" % (uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)


    def _define_networking(self, network_spec, macs, nameservers=[]):
        mac_addrs = list(macs)
        counter = 0
        networks = {}
        for key in network_spec:
            provided_net = network_spec[key]
            network = {}
            mac = None
            if 'ip' in provided_net:
                network['ip'] = provided_net['ip']
                network['netmask'] = provided_net['netmask']
                if 'gateway' in provided_net:
                    network['gateway'] = provided_net['gateway']
                if 'type' in provided_net:
                    network['type'] = provided_net['type']
                else:
                    network['type'] = 'manual'
            else:
                if 'type' not in provided_net:
                    network['type'] = 'dynamic'
                else:
                    network['type'] = provided_net['type']
                if 'use_dhcp' not in provided_net:
                    network['use_dhcp'] = True
            # HACK part
            if 'default' in provided_net:
                # HACK !!!!!
                # Collect the MAC addresses from default array
                # and copy the rest of the parameters
                network['default'] = []
                for item in provided_net['default']:
                    if is_macaddr(item):
                        mac = item
                    else:
                        network['default'].append(item)
            if not mac:
                # HACK
                # It needs an MAC addres so, get the #counter from the macs
                try:
                    mac = mac_addrs[counter]
                except:
                    mac = None
            counter += 1
            if 'dns' in provided_net:
                network['dns'] = provided_net['dns']
            else:
                if nameservers:
                    network['dns'] = nameservers
            if 'mac' in provided_net:
                network['mac'] = provided_net['mac']
            else:
                # The MAC address is asigned to the default network (if
                # default is defined or if there is only one network)
                if mac:
                    network['mac'] = mac
                    # Mac should be in the list of MACs
                    # so remove it to avoid create the fake networks
                    if mac in mac_addrs:
                        mac_addrs.remove(mac)
            if 'preconfigured' in provided_net:
                network['preconfigured'] = provided_net['preconfigured']
            networks[key] = network
        # HACK!
        # Assign internal loopback IPs to the devices which were not configured
        # otherwise the validation checks of the bosh agent will not pass
        counter = 100
        for mac in mac_addrs:
            network = {
                'type': "manual",
                'ip': "127.0.0." + str(counter),
                'netmask': "255.255.255.0",
                'mac': mac,
            }
            networks[mac.replace(':', '-')] = network
            counter += 1
        return networks


    # Define the registry configuration
    def _set_registry(self, ironic, registry, uuid, agent_id, agent,
                      blobstore_cfg, disks, networks, env={}, certs=None):
        self.logger.debug("Defining registry for server id '%s'" % (uuid))
        mbus = agent['mbus']
        try:
            ntp = ast.literal_eval(agent.get('ntp', '[]'))
        except:
            msg = "Error parsing list of ntp servers"
            long_msg = msg + ": Fix agent section on CPI configuration file"
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        # TODO check with Ironic inspector all disk parameters
        system_disk = self.settings.disk_system_device
        ephemeral_disk = self.settings.disk_ephemeral_device
        # Create blobstore
        blobstore = {
            'options': {},
            'provider': blobstore_cfg.get('provider', 'local')
        }
        for key in blobstore_cfg:
            if key != 'provider':
                blobstore['options'][key] = blobstore_cfg[key]
        try:
            registry.create(
                agent_id, mbus, ntp, system_disk, ephemeral_disk, 
                blobstore, env, certs)
            for net in networks:
                registry.set_network(net, networks[net])
        except RegistryError as e:
            msg = "Cannot create registry configuration for server id '%'" % (uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)


    # Define the configdrive
    def _set_configdrive(self, config, uuid, registry, networks):
        # Get configdrive parameters
        self.logger.info("Creating configdrive for server id '%s'" % (uuid))
        registry_url = registry.url
        create_files = boolean(config.get('create_files', ''))
        try:
            nameservers = ast.literal_eval(config.get('nameservers', '[]'))
        except:
            msg = "Error parsing list of nameservers"
            long_msg = msg + ": Fix agent section on CPI configuration file"
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        try:
            publickeys = ast.literal_eval(config.get('publickeys', '[]'))
        except:
            msg = "Error parsing list of publickeys"
            long_msg = msg + ": Fix agent section on CPI configuration file"
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        # Create configdrive
        try:
            repository =  self.repository.manage(config)
            configdrive = Configdrive(uuid, self.settings.configdrive_ext)
            configdrive.set_meta_data(publickeys)
            configdrive.set_user_data(registry_url, nameservers, networks)
            configdrive_id = configdrive.create(repository, create_files)
        except Exception as e:
            msg = "%s: %s" % (type(e).__name__, e)
            self.logger.error(msg)
            raise CPIActionError(msg, msg)
        configdrive_base_url = config['url']
        if not configdrive_base_url.endswith('/'):
            configdrive_base_url += '/'
        configdrive_url = configdrive_base_url + configdrive_id
        self.logger.info("Configdrive URL defined %s" % (configdrive_url))
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
        self.logger.debug("Creating server for agent id '%s'" % (agent_id))
        # Stemcell/image
        image_url, image_md5 = self._get_stemcell(config['stemcell'], stemcell_id)
        # Ironic definition
        ironic = Ironic(config['ironic'], self.logger)
        pxe_macs = resource_pool.get('macs', [])
        define = False
        node = None
        if pxe_macs and 'ironic_params' in resource_pool:
            # Define the server in Ironic, to be deleted in delete_vm,
            # otherwise it will be kept as defined, but ready to use
            define = True
            ironic_params = resource_pool['ironic_params']
            self.logger.debug("Defining server for agent id '%s' with params" % (agent_id))
            try:
                node = ironic.node.create(**ironic_params)
            except ironic_exception.ClientException as e:
                msg = "Error, cannot create server with macs='%s' and provided "
                msg += "ironic_params for agent id '%s'" % (pxe_macs, agent_id)
                long_msg = msg + ": %s" % (e)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
            self.logger.debug("Created server id '%s' for agent id '%s'" % (node.uuid, agent_id))
            # Define the MAC ports
            for mac in pxe_macs:
                port = {
                    'address': mac,
                    'node_uuid': node.uuid
                }
                try:
                    ironic.port.create(**port)
                except ironic_exception.ClientException as e:
                    msg = "Error, cannot create port '%s' for server id '%s'" % (mac, node.uuid)
                    long_msg = msg + ": %s. Deleting server" % (e)
                    self.logger.error(long_msg)
                    ironic.node.delete(node.uuid)
                    raise CPIActionError(msg, long_msg)
        else:
            # TODO: pagination with the nodes!
            if pxe_macs:
                # Get node by MAC(s)
                self.logger.debug("Searching for server definition with MAC(s): %s" % (pxe_macs))
                for mac in pxe_macs:
                    ports = []
                    try:
                        port = ironic.port.get_by_address(mac)
                        node = ironic.node.get(port.node_uuid)
                        break
                    except ironic_exception.ClientException as e:
                        msg = "Not found a server with MAC '%s'" % (mac)
                        long_msg = msg + ": %s" % (e)
                        self.logger.warning(long_msg)
                else:
                    msg = "Error, server not found searching by MAC(s)"
                    long_msg = msg + ": %s" % (pxe_macs)
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)
            else:
                ironic_properties = resource_pool.get('ironic_properties', None)
                self.logger.debug("Searching for server with ironic_properties='%s'" % (ironic_properties))
                try:
                    nodes = ironic.node.list(
                        maintenance=False, 
                        provision_state=self.settings.ironic_search_state,
                        detail=True)
                except ironic_exception.ClientException as e:
                    msg = "Error, unable to get list of servers from Ironic"
                    long_msg = msg + ": %s" % (e)
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)
                for server in nodes:
                    if ironic_properties:
                        # Compare the properties given by the manifest with the
                        # properties of the node
                        # properties': {u'memory_mb': 1, u'cpu_arch': u'x86_64', u'local_gb': 1, u'cpus': 1}
                        try:
                            for key in ironic_properties:
                                if not greater_or_equal(server.properties[key], ironic_properties[key]):
                                    break
                            else:
                                # Node found because all properties are >=
                                node = server
                                break
                        except Exception as e:
                            msg = "Server id '%s' not suitable with provided properties" % (node.uuid)
                            long_msg = msg + ": %s" % (e)
                            self.logger.warning(long_msg)
                    else:
                        # Node found
                        node = server
                        break
                else:
                    msg = "Error, not found server definition on Ironic matching the provided properties"
                    long_msg = msg + ": %s" % (ironic_properties)
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)
            ports = []
            try:
                ports = ironic.node.list_ports(node.uuid)
            except ironic_exception.ClientException as e:
                msg = "Error, cannot get MAC(s) address for server id '%s'" % (node.uuid)
                long_msg = msg + ": %s" % (e)
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
            # Mix all MACs (ports and provided)
            for port in ports:
                if port.address not in pxe_macs:
                    pxe_macs.append(port.address)
        # Registry connection configuration
        registry = Registry(config['registry'], node.uuid)
        # Create network configuration
        networks = self._define_networking(network_spec, pxe_macs)
        # Configdrive
        configdrive_url = self._set_configdrive(config['metadata'], node.uuid, registry, networks)
        # Do registry configuration
        self._set_registry(
            ironic, registry, node.uuid, agent_id, config['agent'],
            config['blobstore'], disk_locality, networks, environment)
        # Define the rest of the metadata in ironic properties
        self._set_ironic_metadata(
            ironic, node.uuid, image_url, image_md5, configdrive_url,
            agent_id, define)
        try:
            ironic.node.set_provision_state(node.uuid, 'active', configdrive_url)
        except ironic_exception.ClientException as e:
            msg = "Error provisioning server id '%s'" % (node.uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        self.logger.info("Provisioning server id '%s' with agent id '%s'" % (node.uuid, agent_id))
        # Wait until node becomes active.
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
                msg = "Server id '%s' status '%s'" % (node.uuid, status)
                self.logger.debug(msg)
                if status == 'deploy failed':
                    # failed!
                    msg = "Error provisioning server id '%s'" % (node.uuid)
                    long_msg = msg + ": 'deploy failed'. See Ironic information."
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)
                if status == 'active':
                    # done
                    break
                time.sleep(ironic_sleep)
                ironic_timer -= 1
            else:
                msg = "Server id '%s' did not become 'active' after %d seconds"
                msg = msg % (node.uuid, (self.settings.ironic_sleep_times * ironic_sleep))
                long_msg = msg + ": Timeout Error"
                self.logger.error(long_msg)
                raise CPIActionError(msg, long_msg)
        except ironic_exception.ClientException as e:
            msg = "Error activating server id '%s' on Ironic" % (node.uuid)
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        self.logger.debug("Agent id '%s' running on '%s'" % (agent_id, node.uuid))
        return node.uuid


# EOF

