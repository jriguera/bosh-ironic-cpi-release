#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals, print_function

import logging
import json

from ironic_cpi.action import CPIAction as CPIAction
from ironic_cpi.action import CPIActionError as CPIActionError



class CPIActionReturn(object):

    def __init__(self, result=None, log="", error=None, logger=None):
        self._output = {}
        self._output['result'] = result
        self._output['log'] = log
        self._output['error'] = error
        logger_name = self.__class__.__name__
        self.logger = logger if logger else logging.getLogger(logger_name)

    @property
    def log(self):
        """Get the log of the Action"""
        return self._output['log']

    @log.setter
    def log(self, msg):
        self._output['log'] = msg
        self.logger.debug(msg)

    @property
    def error(self):
        """Get the ActionError exception"""
        return self._output['error']

    @error.setter
    def error(self, action_error):
        self._output['error'] = action_error
        self._output['result'] = None
        if action_error.log:
            self._output['log'] = action_error.log
            self.logger.error(action_error.log)
        else:
            self.logger.error(action_error.message)

    @property
    def result(self):
        """Get the result of the Action"""
        return self._output['result']

    @result.setter
    def result(self, value):
        self._output['result'] = value

    @staticmethod
    def json(obj):
        if isinstance(obj, CPIActionError):
            return CPIActionError.json(obj)
        elif isinstance(obj, CPIActionReturn):
            return obj._output
        else:
            return obj

    def __repr__(self):
        name = self.__class__.__name__
        output = json.dumps(self._output, default=self.json)
        show = "<%s (%s)" % (name, output)
        return show

    def __str__(self):
        msg = json.dumps(self._output, default=self.json, indent=4, separators=(',', ': '))
        return msg



class CPIManager(object):
    _instance = None
    _registry = None

    def __new__(cls, *args, **kwargs):
        # Singleton implementation
        if not cls._instance:
            cls._registry = CPIAction
            cls._instance = super(CPIManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Just initialize the logger and enumerate the list of CPI loaded
        # Action classes 'CPIAction'
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Actions defined on this CPI")
        for action in self._registry:
            action_class = self._registry[action]
            msg = "%s: %s" % (action, action_class.__name__)
            self.logger.debug(msg)

    def run(self, data, config={}):
        """
        If the CPI method is not defined, it will raise a ValueError, otherwise
        all the errors caused by running the method will be packed in an
        ActionReturn object
        """
        result = CPIActionReturn(logger=self.logger)
        result.log = "Initializing CPI method"
        try:
            action_obj = self._registry.deserialize(data)
        except ValueError as e:
            msg = "CPI Input json data not well-formed: %s" % e
            self.logger.error(msg)
            raise ValueError(msg)
        except KeyError as e:
            key = str(e)
            # If key not is 'method', 'arguments' or 'context', then the key is 
            # the name of the method and it was not found in the registry
            if key not in CPIAction.parameters:
                msg = "CPI method not implemented: %s" % key
            else:
                msg = "CPI Input json data not valid, key '%s' not found" % key
            self.logger.error(msg)
            raise ValueError(msg)
        except Exception as e:
            msg = "Exception: %s" % e
            self.logger.error(msg)
            raise
        self.logger.debug(repr(action_obj))
        result.log = "Running CPI method: %s" % action_obj.name
        try:
            result.result = action_obj.run(config)
        except CPIActionError as e:
            result.error = e
        except Exception as e:
            msg = str(e)
            long_msg = "Exception running '%s': %s" % (action_obj.name, msg)
            result.error = CPIActionError(msg, long_msg, str(type(e)))
        else:
            result.log = "%s" % action_obj.name
        self.logger.debug(repr(result))
        return result

# EOF

