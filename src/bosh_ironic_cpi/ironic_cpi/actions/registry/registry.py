#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import json
import requests
import copy
import logging
try:
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse



class RegistryError(Exception):
    """
    Base class for all Registry Exceptions
    """

    def __init__(self, message):
        self.message = message

    def __repr__(self):
        name = self.__class__.__name__
        show = "<%s (%s)>" % (name, self.message)
        return show

    def __str__(self):
        return self.message



class Registry(object):

    def __init__(self, config, uuid, logger=None):
        url = urlparse(config['url'])
        username = config.get('username', url.username)
        password = config.get('password', url.password)
        cert = config.get('cacert')
        timeout = config.get('timeout')
        if not url.path.endswith('/'):
            basepath = url.path + '/'
        else:
            basepath = url.path
        self.endpoint = url.scheme + "://" + url.netloc + basepath
        self.endpoint = self.endpoint + 'instances/' + uuid + "/settings"
        self.url = url.scheme + "://"
        if username:
            self.url = self.url + username
            if password:
                self.url = self.url + ':' + password
            self.url += '@'
        self.url = self.url + url.netloc + url.path
        self.session = requests.Session()
        if username:
            self.session.auth = (username, password)
        if timeout:
            self.session.timeout = timeout
        self.session.headers.update({'Accept': 'application/json'})
        self.session.verify = True if cert else False
        self.session.cert = cert if cert else None
        self.logger = logger
        self.uuid = uuid
        if not logger:
            self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Initializing registry %s" % (self.__class__.__name__))


    @staticmethod
    def dict_merge(a, b):
        """
        merges b into a and return merged result
        NOTE: tuples and arbitrary objects are not handled as it is totally 
        ambiguous what should happen
        """
        key = None
        try:
            if (a is None or
                isinstance(a, str) or
                isinstance(a, unicode) or
                isinstance(a, int) or
                isinstance(a, long) or
                isinstance(a, float)):
                # border case for first run or if a is a primitive
                a = b
            elif isinstance(a, list):
                # lists can be only appended
                if isinstance(b, list):
                    for item in b:
                        if item not in a:
                            a.append(b)
                else:
                    if b not in a:
                        a.append(b)
            elif isinstance(a, dict):
                # dicts must be merged
                if isinstance(b, dict):
                    for key in b:
                        if key in a:
                            a[key] = Registry.dict_merge(a[key], b[key])
                        else:
                            a[key] = b[key]
                else:
                    msg = "Cannot merge non-dict '%s' into dict '%s'"
                    raise ValueError(msg % (b, a))
            else:
                msg = "Cannot merge tuples '%s':'%s'"
                raise ValueError(msg % (b, a))
        except TypeError as e:
            msg = "TypeError in key '%s' when merging '%s' into '%s': %s"
            raise TypeError(msg % (key, b, a, e))
        return a


    def read(self):
        settings = None
        try:
            self.logger.debug("Doing HTTP GET '%s'" % (self.endpoint))
            req = self.session.get(self.endpoint)
            if req.status_code == requests.codes.ok:
                result = req.json()
                settings = result['settings']
                if result['status'] != 'ok':
                    msg = "Registry error: %s" % (settings)
                    self.logger.error(msg)
                    raise RegistryError(msg)
                return json.loads(settings)
            else:
                msg = "HTTP GET '%s': %s" % (self.endpoint, req.status_code)
                self.logger.error(msg)
                raise RegistryError(msg)
        except RegistryError:
            raise
        except Exception as e:
            msg = "Error '%s': %s" % (e.__class__.__name__, str(e))
            self.logger.error(msg)
            raise RegistryError(msg)


    def push(self, settings):
        try:
            self.logger.debug("Doing HTTP PUT '%s': %s" % (self.endpoint, settings))
            req = self.session.put(self.endpoint, data=json.dumps(settings))
        except Exception as e:
            msg = "Error '%s': %s" % (e.__class__.__name__, str(e))
            self.logger.error(msg)
            raise RegistryError(msg)
        if req.status_code not in [201, 204]:
            msg = "HTTP PUT '%s': %s" % (self.endpoint, req.status_code)
            self.logger.error(msg)
            raise RegistryError(msg)
        return settings


    def merge(self, settings):
        old_settings = self.read()
        try:
            new_settings = self.dict_merge(old_settings, settings)
        except Exception as e:
            msg = str(e)
            self.logger.error(msg)
            raise RegistryError(msg)
        return self.push(new_settings)


    def delete(self, delete_uuid=False):
        try:
            self.logger.debug("Doing HTTP DELETE '%s'" % (self.endpoint))
            req = self.session.delete(self.endpoint)
        except Exception as e:
            msg = "Error '%s': %s" % (e.__class__.__name__, str(e))
            self.logger.error(msg)
            raise RegistryError(msg)
        if req.status_code not in [requests.codes.ok, requests.codes.no_content]:
            msg = "HTTP DELETE '%s': %s" % (self.endpoint, req.status_code)
            self.logger.error(msg)
            raise RegistryError(msg)
        if delete_uuid:
            url = os.path.split(self.endpoint) + "/"
            try:
                self.logger.debug("Doing HTTP DELETE '%s'" % (url))
                req = self.session.delete(url)
            except Exception as e:
                msg = "Error '%s': %s" % (e.__class__.__name__, str(e))
                self.logger.error(msg)
                raise RegistryError(msg)
            if req.status_code not in [requests.codes.ok, requests.codes.no_content]:
                msg = "HTTP DELETE '%s': %s" % (url, req.status_code)
                self.logger.error(msg)
                raise RegistryError(msg)


    def create(self, agent_id, mbus, ntp=[], disk_system='/dev/sda',
               disk_ephemeral='', blobstore={}, env={}, certs=None):
        # Create registry contents
        registry = {
            'agent_id': agent_id,
            'mbus': mbus,
            'trusted_certs': certs,
            'vm': {
                'name': self.uuid,
                'id': self.uuid
            },
            'blobstore': blobstore,
            'disks': {
                'system': disk_system,
                'ephemeral': disk_ephemeral,
                'persistent': {}
            },
            'networks': {},
            'ntp': ntp,
            'env': env,
        }
        try:
            self.logger.debug("Doing HTTP PUT '%s': %s" % (self.endpoint, registry))
            req = self.session.put(self.endpoint, data=json.dumps(registry))
        except Exception as e:
            msg = "Error '%s': %s" % (e.__class__.__name__, str(e))
            self.logger.error(msg)
            raise RegistryError(msg)
        if req.status_code not in [201, 204]:
            msg = "HTTP PUT '%s': %s" % (self.endpoint, req.status_code)
            self.logger.error(msg)
            raise RegistryError(msg)
        return registry


    def set_disk(self, disk, path, kind='persistent',
                 device_id=None, volume_id=None, lun=None, host=None, fs=None):
        settings = {}
        settings['disks'] = {}
        settings['disks'][kind] = {}
        settings['disks'][kind][disk] = {}
        settings['disks'][kind][disk]['path'] = path
        if device_id != None:
            settings['disks'][kind][disk]['device_id'] = device_id
        if volume_id != None:
            settings['disks'][kind][disk]['volume_id'] = volume_id
        if lun != None:
            settings['disks'][kind][disk]['lun'] = lun
        if host != None:
            settings['disks'][kind][disk]['host_device_id'] = host
        if fs != None:
            settings['disks'][kind][disk]['file_system_type'] = fs
        self.logger.debug("Updating disks '%s'" % (settings))
        self.merge(settings)
        return settings


    def delete_disk(self, disk, kind='persistent'):
        self.logger.debug("Deleting disk '%s' on '%s'" % (disk, self.uuid))
        settings = self.read()
        try:
            del settings['disks'][kind][disk]
        except:
            msg = "Disk %s '%s' not found on '%s'!" % (kind, disk, self.uuid)
            self.logger.error(msg)
            raise RegistryError(msg)
        return self.push(settings)


    def set_network(self, name, spec={}, dns=None, mac=None, dhcp=False):
        settings = {}
        settings['networks'] = {}
        net = copy.deepcopy(spec)
        if 'type' not in net:
            if 'ip' not in net:
                net['type'] = 'dynamic'
            else:
                net['type'] = 'manual'
        if dhcp or net['type'] == 'dynamic':
            net['use_dhcp'] = True
            net['type'] = 'dynamic'
        if dns:
            net['dns'] = dns
        if mac:
            net['mac'] = mac
        settings['networks'][name] = net
        self.logger.debug("Updating '%s' networks '%s'" % (self.uuid, settings))
        return self.merge(settings)


    def delete_network(self, name):
        self.logger.debug("Deleting network '%s' on '%s'" % (name, self.uuid))
        settings = self.read()
        try:
            del settings['networks'][name]
        except:
            msg = "Network '%s' not found on '%s'!" % (name, self.uuid)
            self.logger.error(msg)
            raise RegistryError(msg)
        return self.push(settings)


    def set_env_bosh(self, password=None, keep_root_password=None,
                     remove_dev_tools=None):
        settings = {}
        settings['env'] = {}
        settings['env']['bosh'] = {}
        if password:
            settings['env']['bosh']['password'] = password
        if keep_root_password != None:
            settings['env']['bosh']['keep_root_password'] = keep_root_password
        if remove_dev_tools != None:
            settings['env']['bosh']['remove_dev_tools'] = remove_dev_tools
        self.logger.debug("Updating bosh env settings '%s'" % (settings))
        return self.merge(settings)


    def set_env_persistent_disk_fs(self, persistent_disk_fs='ext4'):
        settings = {}
        settings['env'] = {}
        settings['env']['persistent_disk_fs'] = persistent_disk_fs
        self.logger.debug("Updating bosh env persistent disk fs settings '%s'" % (settings))
        return self.merge(settings)


