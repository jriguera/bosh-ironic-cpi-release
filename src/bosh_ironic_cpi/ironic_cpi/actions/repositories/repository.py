#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import logging

from ironic_cpi.action import CPIActionError



def ExceptionCatch(method):
    """
    Wrapper for methods to catch all Exceptions
    """

    def wrapped_method(self, *args, **kwargs):
        try:
            method(self, *args, **kwargs)
        except Exception as e:
            msg = str(e)
            raise RepositoryError(msg)
    return wrapped_method



class RepositoryCatcher(type):
    """
    Metaclass to wrap all methods
    """

    def __init__(cls, name, bases, dct):
        if not hasattr(cls, 'registry'):
            # this is the base class.  Create an empty registry
            cls.registry = {}
        else:
            # this is a derived class.  Add cls to the registry
            # if the class has the protocol attribute
            try:
                cls.registry[cls.protocol] = cls
            except:
                pass
        # Define a wrapper for each method to catch the Exceptions
        for m in dct:
            if hasattr(dct[m], '__call__'):
                dct[m] = ExceptionCatch(dct[m])
        super(RepositoryCatcher, cls).__init__(name, bases, dct)

    # Metamethods, called on class objects:
    def __getitem__(cls, key):
        return cls.registry[key]

    def __iter__(cls):
        return iter(cls.registry)



class Repository(object):
    __metaclass__ = RepositoryCatcher
    #protocol = ''

    def __init__(self, config, logger=None):
        self.config = config
        self.log(logger)
        self.logger.debug("Initializing class %s" % self.__class__.__name__)

    def log(self, logger=None):
        self.logger = logger
        if not logger:
            self.logger = logging.getLogger(self.__class__.__name__)
    
    def mkdir(self, path):
        pass

    def rmdir(self, path):
        pas

    def delete(self, path):
        pass

    def put(self, local, remote):
        pass

    def get(self, remote, local):
        pass

    def exists(self, remote):
        pass



class RepositoryError(Exception):
    """
    Base class for all Repository Exceptions
    """
    
    def __init__(self, message):
        self.message = message

    def __repr__(self):
        name = self.__class__.__name__
        show = "<%s (%s)>" % (name, self.message)
        return show

    def __str__(self):
        return self.message



class RepositoryManager(object):
    _metarepository = Repository
    repository_config_key = 'repository_type'

    def __init__(self, logger=None):
        self.logger = logger
        if not logger:
            self.logger = logging.getLogger(self.__class__.__name__)
        self.repository = None

    def manage(self, config):
        self.repository = None
        repository_type = config[self.repository_config_key]
        for protocol in self._metarepository:
            repo_class = self._metarepository[protocol]
            msg = "Repository class for protocol %s: %s"
            msg = msg % (protocol, repo_class.__name__)
            self.logger.debug(msg)
            if protocol == repository_type:
                self.repository = repo_class(config, self.logger)
        if not self.repository:
            msg = "Protocol '%s' not supported!" % repository_type
            long_msg = "Not found class to manage repository of type '%s'"
            long_msg = long_msg % repository_type
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        return self.repository


