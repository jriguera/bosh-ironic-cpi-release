#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals, print_function

__program__ = "ironic_cpi"
__version__ = "v0.1.0"
__author__ = "Jose Riguera"
__year__ = "2016"
__email__ = "jriguera@gmail.com"
__license__ = "MIT"
__purpose__ = "Tell bosh how to talk with OpenStack Ironic"


import sys
import os
import logging 
import logging.config 
import argparse
from argparse import RawTextHelpFormatter
import json
# Python 2 only!
import ConfigParser as configparser

# Append the current folder
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

# Foce the loading of the Meta Class and Base class ...
from ironic_cpi.action import *
# ... and now load all the actions
from ironic_cpi.actions import *
# Load the resources to use here
from ironic_cpi.manager import CPIActionReturn as CPIActionReturn
from ironic_cpi.manager import CPIManager as CPIManager



class CPI(object):
    PROG=__program__
    VERSION=__version__
    FILE="ironic.cfg"
    LOGGING="logging.ini"
    LOGLEVEL=logging.DEBUG
    LOGENVCONF="LOG_CONFIGFILE"
    LOGFORMAT='%(name)s: %(message)s'
    # configuration parameters:
    # section.parameter: required
    PARAMETERS = {
        "ironic": {
            'url': True,
            'auth_token': False,
            'auth_username': False,
            'auth_password': False,
            'project_name': False,
            'region_name': False,
            'auth_domain': False,
            'auth_url': False,
            'cacert': False
        },
        "stemcell": {
            'repository_type': True,
            'url': True,
            'username': False,
            'password': False,
            'cacert': False
        },
        "metadata": {
            'repository_type': True,
            'url': False,
            'username': False,
            'password': False,
            'cacert': False
        }
    }


    def __init__(self):
        self.parser = None
        self.logpath = None
        self.logger = None
        self.folder = os.path.abspath(os.path.dirname(__file__))
        self.setup_parser()
        default_logging_conf = os.path.join(self.folder, self.LOGGING)
        self.setup_logging(default_logging_conf)
        self.args = None

    def setup_parser(self):
        epilog = __purpose__ + '\n'
        epilog += __version__ + ', ' + __year__ + ' '
        epilog += __author__ + ' ' + __email__
    	self.parser = argparse.ArgumentParser(
    	    formatter_class=RawTextHelpFormatter,
    	    description=__doc__, epilog=epilog)
    	g1 = self.parser.add_argument_group('Configuration options')
    	g1.add_argument(
    	    '-c', '--config', type=str,
    	    dest='config', default=self.FILE, help="Configuration file")
        g1.add_argument(
            'infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
        g1.add_argument(
            'outfile', nargs='?', type=argparse.FileType('w'), default=sys.stdout)

    def setup_logging(self, logging_conf=None):
        self.logpath = os.environ.get(self.LOGENVCONF, logging_conf)
        self.logpath = os.path.expandvars(self.logpath)
        logconf = False
        if os.path.isfile(self.logpath):
            try:
                logging.config.fileConfig(self.logpath)
            except Exception as e:
                print("Error '%s': %s" % (self.logpath, e), file=sys.stderr)
                logging.basicConfig(level=self.LOGLEVEL, format=self.LOGFORMAT)
            else:
                logconf = True
        else:
            logging.basicConfig(level=self.LOGLEVEL, format=self.LOGFORMAT)
    	self.logger = logging.getLogger(self.PROG)
    	if not logconf:
            self.logger.info("Using default logging settings")
    	else:
            self.logger.info("Using logging settings from '%s'" % self.logpath)
        return self.logger

    def parse_config(self, arguments=None):
        finalconfig = {}
    	args = self.parser.parse_args(arguments)
        config = configparser.SafeConfigParser()
        try:
            with open(args.config) as fdconfig:
                config.readfp(fdconfig) 
    	except Exception as e:
            msg = "Ignoring configuration file '%s'"
            self.logger.warn(msg % (args.config))
            for section in self.PARAMETERS.keys():
                config.add_section(section)
        else:
            self.logger.info("Read configuration file '%s'" % args.config)
        for section in self.PARAMETERS.keys():
            cfgsection = dict(config.items(section))
    	    for var, required in self.PARAMETERS[section].iteritems():
                try:
                    # build env variables like IRONIC_URL
                    envparameter = section.upper() + '_' + var.upper()
                    cfgsection[var] = os.environ[envparameter]
                    msg = "Reading env variable '%s'" % envparameter
                    self.logger.debug(msg)
                except:
                    pass
                if required and not var in cfgsection:
                    msg = "Variable '%s.%s' not defined and it is required!" 
                    msg = msg % (section, var)
                    self.logger.error(msg)
                    raise ValueError(msg)
            finalconfig[section] = cfgsection
        self.args = args
        return finalconfig



def main():
    program = CPI()
    try:
        config = program.parse_config()
    except ValueError as e:
        return 1
    fdin = program.args.infile
    fdout = program.args.outfile
    # read only first 100k
    data = fdin.read(102400)
    cpi = CPIManager()
    output = cpi.run(data, config)
    fdout.write(str(output) + '\n')
    return 0



if __name__ == '__main__':
    sys.exit(main())


# EOF
