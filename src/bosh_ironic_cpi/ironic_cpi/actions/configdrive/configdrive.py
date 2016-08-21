#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import os
import shutil
import tempfile
import json
import StringIO
import logging

from ironic_cpi.actions.repositories.repository import RepositoryError

# Import ironic libs
from ironicclient import exceptions as ironic_exception
from ironicclient.common import utils



class ConfigdriveError(Exception):
    """
    Base class for all ConfigDrive Exceptions
    """

    def __init__(self, message):
        self.message = message

    def __repr__(self):
        name = self.__class__.__name__
        show = "<%s (%s)>" % (name, self.message)
        return show

    def __str__(self):
        return self.message



class Configdrive(object):

    def __init__(self, node_uuid, file_ext='.cfgd', logger=None):
        self.node_uuid = node_uuid
        self.configdrive_ext = file_ext
        self.meta_data = {'instance-id': self.node_uuid}
        self.user_data = {'server': {'name': self.node_uuid }}
        self.configdrive_id = self.node_uuid + self.configdrive_ext
        self.logger = logger
        if not logger:
            self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initializing class %s" % (self.__class__.__name__))


    def set_meta_data(self, public_keys=[]):
        # meta_data
        self.meta_data['public-keys'] = {}
        if public_keys:
            counter = 0
            for key in public_keys:
                index = str(counter)
                self.meta_data['public-keys'][index] = {'openssh-key': key}
                counter += 1
        else:
            self.meta_data['public-keys']['0'] = {'openssh-key': ''}


    def set_user_data(self, registry, nameservers=[], networks={}):
        # user_data
        self.user_data['registry'] = {'endpoint': registry }
        if nameservers:
            self.user_data['dns'] = {'nameserver': nameservers}
        if networks:
            self.user_data['networks'] = networks
        else:
            # Create one default dynamic network
            self.user_data['networks']['default'] = {
                'type': 'dynamic',
                'use_dhcp': True
            }


    def delete(self, repository, delete_files=True):
        self.logger.debug("Deleting configdrive metadata '%s'" % (self.node_uuid))
        try:
            if repository.exists(self.configdrive_id):
                repository.delete(self.configdrive_id)
                if delete_files:
                    basedir = self.node_uuid + '/ec2/latest/'
                    try:
                        repository.delete(basedir + 'user-data')
                        repository.delete(basedir + 'meta-data.json')
                        repository.rmdir(self.node_uuid)
                    except:
                        pass
                self.logger.info("Configdrive metadata '%s' deleted" % (self.node_uuid))
            else:
                self.logger.info("Configdrive metadata '%s' not found" % (self.node_uuid))
        except RepositoryError as e:
            msg = "Error accessing '%s' on repository: %s" % (self.node_uuid, e)
            self.logger.error(msg)
            raise ConfigdriveError(msg)


    def create(self, repository, create_files=True):
        # Create a temp folder
        try:
            tmp_dir = tempfile.mkdtemp('_configdrive')
            tmp_dir_base = os.path.join(tmp_dir,'ec2', 'latest')
            os.makedirs(tmp_dir_base)
            if create_files:
                if not repository.exists(self.node_uuid + '/ec2/latest/'):
                    repository.mkdir(self.node_uuid + '/ec2/latest')
            # user-data.json
            user_data_tmp_file = os.path.join(tmp_dir_base,'user-data')
            cfgdrive_user_json = json.dumps(
                self.user_data, indent=4, separators=(',', ': '))
            with open(user_data_tmp_file, 'w') as outfile:
                outfile.write(cfgdrive_user_json)
            if create_files:
                repository.put(
                    StringIO.StringIO(cfgdrive_user_json),
                    self.node_uuid + '/ec2/latest/user-data')
            # meta-data.json
            meta_data_tmp_file = os.path.join(tmp_dir_base,'meta-data.json')
            cfgdrive_meta_json = json.dumps(
                self.meta_data, indent=4, separators=(',', ': '))
            with open(meta_data_tmp_file, 'w') as outfile:
                outfile.write(cfgdrive_meta_json)
            if create_files:
                repository.put(
                    StringIO.StringIO(cfgdrive_meta_json),
                    self.node_uuid + '/ec2/latest/meta-data.json')
            # Create it using Ironic utils
            self.logger.debug("Creating configdrive volume")
            configdrive = utils.make_configdrive(tmp_dir)
            self.logger.debug("Uploading configdrive to repository")
            repository.put(StringIO.StringIO(configdrive), self.configdrive_id)
        except ironic_exception.ClientException as e:
            msg = "Error creating configdrive volume %s" % (e)
            self.logger.error(msg)
            raise ConfigdriveError(msg)
        except RepositoryError as e:
            msg = "Cannot save configdrive '%s' in the repository: %s" % (self.configdrive_id, e)
            self.logger.error(msg)
            raise ConfigdriveError(msg)
        except Exception as e:
            msg = "%s: %s" % (type(e).__name__, e)
            self.logger.error(msg)
            raise ConfigdriveError(msg)
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir)
        self.logger.info("Configdrive created with id '%s' in the repository" % (self.configdrive_id))
        return self.configdrive_id


