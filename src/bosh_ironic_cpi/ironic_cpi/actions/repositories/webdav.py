#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import logging
import requests
try:
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

from ironic_cpi.actions.repositories.repository import RepositoryError
from ironic_cpi.actions.repositories.repository import Repository



class WebDavError(RepositoryError):

    def __init__(self, method, url, code, expected=[], msg=None):
        self._method = method
        self._url = url
        self._code = code
        self._expected = expected
        if msg:
            self.message = msg
        else:
            self._string()
    
    @property
    def method(self):
        """Get the error method"""
        return self._method

    @method.setter
    def method(self, m):
        self._method = m
        self._string()

    @property
    def url(self):
        """Get the URL"""
        return self._url

    @url.setter
    def url(self, u):
        self._url = u
        self._string()

    @property
    def code(self):
        """Get the return code"""
        return self._code

    @code.setter
    def code(self, c):
        self._code = c
        self._string()

    def _string(self):
        message = "Failed to perform <%s:%s>, return code: '%s'"
        if self._expected:
            message = message + ", expected: %s"
            self.message = message % (method, url, code, self._expected)
        else:
            self.message = message % (method, url, code)



class WebDav(Repository):
    """
    Basic implementation of webdav protocol
    Based on https://github.com/amnong/easywebdav
    Because of request library, it uses HTTP_PROXY and HTTPS_PROXY env variables
    """
    DOWNLOAD_CHUNK_SIZE = 8192
    protocol = 'webdav'

    def __init__(self, config, logger=None):
        super(WebDav, self).__init__(config, logger)
        url = urlparse(config['url'])
        self.hosturl = url.netloc
        self.proto = url.scheme
        self.basepath = url.path
        if not self.basepath.endswith('/'):
            self.basepath += '/'
        username = config.get('username', url.username)
        password = config.get('password', url.password)
        cert = config.get('cacert')
        timeout = config.get('timeout')
        self.session = requests.session()
        self.session.stream = True
        if cert:
            self.session.verify = True
            self.session.cert = cert
        if username:
            self.session.auth = (username, password) if password else username
            self.logger.debug("Using auth with username '%s'" % username)
        if timeout:
            self.session.timeout = timeout

    def _send(self, method, path, expected, **kwargs):
        path = path.strip()
        if not path.startswith('/'):
            path = self.basepath + path
        url = self.proto + "://" + self.hosturl + path
        self.logger.debug("%s: %s" % (method, url))
        response = self.session.request(
            method, url, allow_redirects=False, **kwargs)
        if response.status_code not in expected:
            self.logger.error("%s: %s :%" % (method, url, response.status_code))
            raise WebDavError(method, url, response.status_code, expected)
        return response

    def mkdir(self, path):
        codes = [201, 207]
        dirs = [ dir for dir in path.split('/') if dir ]
        full_path = ''
        for d in dirs:
            full_path = full_path + d + '/'
            self._send('MKCOL', full_path, codes)

    def rmdir(self, path):
        codes = [204]
        path = path.rstrip('/') + '/'
        self._send('DELETE', path, codes)

    def delete(self, path):
        codes = [204]
        self._send('DELETE', path, codes)

    def _upload(self, data, remote):
        codes = [200, 201, 204]
        self._send('PUT', remote, codes, data=data)

    def put(self, local, remote):
        if isinstance(local, basestring):
            with open(local, 'rb') as f:
                self._upload(f, remote)
        else:
            self._upload(local, remote)

    def _download(self, fd, response):
        for chunk in response.iter_content(self.DOWNLOAD_CHUNK_SIZE):
            fd.write(chunk)

    def get(self, remote, local):
        codes = [200]
        response = self._send('GET', remote, codes, stream=True)
        try:
            if isinstance(local, basestring):
                with open(local, 'wb') as f:
                    self._download(f, response)
            else:
                self._download(local, response)
        except EnvironmentError as e:    # parent of IOError, OSError
            msg = "Cannot write '%s': %s" % (local, e)
            self.logger.error(msg)
            raise RepositoryError(msg)

    def exists(self, remote):
        codes = [200, 404]
        response = self._send('HEAD', remote, codes)
        return True if response.status_code != 404 else False


