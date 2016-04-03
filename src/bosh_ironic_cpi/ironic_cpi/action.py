#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals, print_function

import logging
import json



class MetaCPIAction(type):
    """
    Metaclass to register automatically all the CPI actions
    """

    # using __init__ rather than __new__ here because I want to modify 
    # attributes of the class *after* they have been created
    def __init__(cls, name, bases, dct):
        if not hasattr(cls, 'registry'):
            # this is the base class.  Create an empty registry
            cls.registry = {}
        else:
            # this is a derived class.  Add cls to the registry
            cls.registry[name.lower()] = cls
        super(MetaCPIAction, cls).__init__(name, bases, dct)

    # Metamethods, called on class objects:
    def __getitem__(cls, key):
        return cls.registry[key]

    def __iter__(cls):
        return iter(cls.registry)



class CPIAction(object):
    """
    Base class for all the CPI actions
    """
    __metaclass__ = MetaCPIAction
    parameters = ['method', 'arguments', 'context']

    def __init__(self, context={}):
        self._name = self.__class__.__name__.lower()
        self.logger = logging.getLogger(self.__class__.__name__)
        self._context = context
        self._args = None

    def __repr__(self):
        """Representation of the object"""
        name = self.__class__.__name__
        show = "<%s (%s)>" % (name, self.__class__.serialize(self))
        return show

    def __str__(self):
        """Pretty print json"""
        return self.__class__.serialize(self, True)

    @property
    def name(self):
        """Get the name of the Action"""
        return self._name

    @property
    def args(self):
        """Get the arguments of the Action"""
        return self._args

    @args.setter
    def args(self, arg=[]):
        self._args = arg

    @property
    def context(self):
        """Get the context of the Action"""
        return self._context

    @context.setter
    def context(self, cntxt):
        self._context = cntxt

    @classmethod
    def serialize(cls, action_class, pretty=False):
        """Serialize the object to json"""
        obj = {
            'method': action_class.name,
            'arguments': action_class.args,
            'context': action_class.context
        }
        if pretty:
            data = json.dumps(obj, indent=4, separators=(',', ': '))
        else:
            data = json.dumps(obj)
        return data

    @classmethod
    def deserialize(cls, data):
        """Create the class from json"""
        params = json.loads(data)
        name = params['method']
        action_class = cls.registry[name]
        action_obj = action_class(params['context'])
        action_obj.args = params['arguments']
        return action_obj

    def run(self, config):
        pass



class CPIActionError(Exception):

    def __init__(self, message, long_msg=None, etype=None, ok_to_retry=False):
        """CPI custom error fields"""
        self._error = {}
        self._long_msg = long_msg
        self._error['message'] = message
        self._error['ok_to_retry'] = ok_to_retry
        self._error['type'] = etype
        if etype is None:
            self._error['type'] = self.__class__.__name__

    @property
    def error(self):
        """Get the error structure (dictionary)"""
        return self._error

    @error.setter
    def error(self, e):
        self._error = e

    @property
    def log(self):
        """Get the long error message"""
        return self._long_msg

    @log.setter
    def log(self, msg):
        self._long_msg = msg

    @property
    def message(self):
        """Get the error message string"""
        return self._error['message']

    @property
    def ok_to_retry(self):
        """Get the ok_to_retry field"""
        return self._error['ok_to_retry']

    @property
    def type(self):
        """Get the type"""
        return self._error['type']

    @staticmethod
    def json(obj):
        if isinstance(obj, CPIActionError):
            return obj._error
        else:
            return obj

    def __repr__(self):
        name = self.__class__.__name__
        error = json.dumps(self._error)
        show = "<%s (%s)>" % (name, error)
        return show

    def __str__(self):
        msg = json.dumps(self._error, indent=4, separators=(',', ': '))
        return msg


# EOF

