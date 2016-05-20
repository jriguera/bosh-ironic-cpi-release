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
try:
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

from ironic_cpi.action import CPIAction
from ironic_cpi.action import CPIActionError
from ironic_cpi.actions.ironic import connect as Ironic

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
        self.logger.debug("Checking if stemcell '%s' exists" % stemcell_id)
        try:
            if not repository.exists(image_id) or not repository.exists(image_meta):
                msg = "Cannot find stemcell id '%s'" % stemcell_id
            	long_msg = msg + ': %s and/or %s not found on repostitory'
            	long_msg = long_msg % (image_id, image_meta)
            	self.logger.error(long_msg)
            	raise CPIActionError(msg, long_msg)
            self.logger.debug("Stemcell '%s' found on repository" % stemcell_id)
        except RepositoryError as e:
            msg = "Error accessing '%s' on repository" % stemcell_id
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
    def _set_ironic_metadata(self, ironic, node_uuid, image_url, image_md5,
                             configdrive_url, agent_id, define):
        try:
            self.logger.info(
                "Defining metadata for new server '%s'" % node_uuid)
            metadata_items = [
                {'value': str(define), 'path': "/instance_info/bosh_defined"},
                {'value': image_url, 'path': "/instance_info/image_source"},
                {'value': image_md5, 'path': "/instance_info/image_checksum"},
                {'value': configdrive_url, 'path': "/instance_info/configdrive"},
                {'value': agent_id, 'path': "/instance_uuid"}
            ]
            for item in metadata_items:
                metadata_item = item
                metadata_item['op'] = "add"
                try:
                    ironic.node.update(node_uuid, [metadata_item])
                except:
                    metadata_item['op'] = "replace"
                    ironic.node.update(node_uuid, [metadata_item])
        except ironic_exception.ClientException as e:
            msg = "Error defining server '%s' on Ironic" % node_uuid
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)


    # Define the configdrive
    def _set_configdrive(self, config, node_uuid, registry, nameserver,
                         networks=None, public_keys=[]):
        configdrive_id = node_uuid + self.settings.configdrive_ext
        repository =  self.repository.manage(config)
        # Create the configdrive contents
        # meta_data
        configdrive_meta_data = {
            'instance-id': node_uuid,
            'public-keys': {}
        }
        counter = 0
        for key in public_keys:
            configdrive_meta_data['public-keys'][str(counter)] = {
                "openssh-key": key
            }
            counter += 1
        # user_data
        configdrive_user_data = {
            'server':   {'name': node_uuid },
            'dns':      {'nameserver': nameserver},
            'registry': {'endpoint': registry}
        }
        if networks:
            configdrive_user_data['networks'] = networks
        # Create a temp folder
        try:
            tmp_dir = tempfile.mkdtemp('_configdrive')
            tmp_dir_base = os.path.join(tmp_dir,'ec2', 'latest')
            os.makedirs(tmp_dir_base)
            if config['create_files']:
                repository.mkdir(node_uuid + '/ec2/latest')
            # user_data.json
            cfgdrive_user_json = json.dumps(configdrive_user_data,
                indent=4, separators=(',', ': '))
            user_data_tmp_file = os.path.join(tmp_dir_base,'user_data.json')
            with open(user_data_tmp_file, 'w') as outfile:
                outfile.write(cfgdrive_user_json)
            if config['create_files']:
                repository.put(
                    StringIO.StringIO(cfgdrive_user_json),
                    node_uuid + '/ec2/latest/user_data.json')
            # meta_data.json
            cfgdrive_meta_json = json.dumps(configdrive_meta_data,
                indent=4, separators=(',', ': '))
            meta_data_tmp_file = os.path.join(tmp_dir_base,'meta_data.json')
            with open(meta_data_tmp_file, 'w') as outfile:
                outfile.write(cfgdrive_meta_json)
            if config['create_files']:
                repository.put(
                    StringIO.StringIO(cfgdrive_meta_json),
                    node_uuid + '/ec2/latest/meta_data.json')
            # Create it using Ironic utils
            self.logger.debug("Creating configdrive volume")
            configdrive = utils.make_configdrive(tmp_dir)
            self.logger.debug("Uploading configdrive to repository")
            repository.put(StringIO.StringIO(configdrive), configdrive_id)
        except ironic_exception.ClientException as e:
            msg = "Error creating configdrive volume"
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        except RepositoryError as e:
            msg = "Cannot save '%s' in the metadata repository" % configdrive_id
            long_msg = msg + ': %s' % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        except Exception as e:
            msg = "%s: %s" % (type(e).__name__, e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, msg)
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir)
        configdrive_base_url = config['url']
        if not configdrive_base_url.endswith('/'):
            configdrive_base_url += '/'
        configdrive_url = configdrive_base_url + configdrive_id
        self.logger.info("Configdrive URL %s" % configdrive_url)
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
        image_url, image_md5 = self._get_stemcell(
            config['stemcell'], stemcell_id)
        # Get configdrive parameters for registry
        registry = config['registry']['endpoint']
        nameservers = [ 
            nameserver.strip() for nameserver in 
                config['registry']['nameservers'].split(',')
        ]
        publickeys = config['registry'].get('publickeys', [])
        # Networks (they are not really needed, it will use DCHP from Ironic)
        networks = config['registry'].get('networks', None)
        # Ironic definition
        ironic = Ironic(config['ironic'], self.logger)
        mac = resource_pool['mac']
        define = False
        try:
            if 'ironic_params' in resource_pool:
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
            else:
                # Get node by MAC
                try:
                    port = ironic.port.get_by_address(mac)
                    node = ironic.node.get(port.node_uuid)
                except ironic_exception.ClientException as e:
                    msg = "Error, server not found with MAC '%s'" % mac
                    long_msg = msg + ": %s" % (e)
                    self.logger.error(long_msg)
                    raise CPIActionError(msg, long_msg)
        except ironic_exception.ClientException as e:
            msg = "Error defining server '%s' on Ironic" % node.uuid
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        # Configdrive
        configdrive_url = self._set_configdrive(config['metadata'],
            node.uuid, registry, nameservers, networks, publickeys)
        # Define the rest of the metadata
        self._set_ironic_metadata(
            ironic, node.uuid, image_url, image_md5, configdrive_url,
            agent_id, define)
        # TODO Registry configuration!!!!!!!!!
        try:
            ironic.node.set_provision_state(node.uuid, 'active', configdrive_url)
        except ironic_exception.ClientException as e:
            msg = "Error provisioning server '%s'" % node.uuid
            long_msg = msg + ": %s" % (e)
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        self.logger.info(
            "Server '%s' defined with agent_id '%s'" % (node.uuid, agent_id))
        return node.uuid

# EOF

