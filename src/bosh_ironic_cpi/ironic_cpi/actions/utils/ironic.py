#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import time

from ironic_cpi.action import CPIActionError

# Import ironic client
from ironicclient import client as ironic_client
from ironicclient import exceptions as ironic_exception



def connect(config, logger):
    ironic_kwargs = {
        'ironic_url': config['url'],
        'os_project_domain_name': config['auth_domain']
    }
    if 'auth_url' in config:
        ironic_kwargs['os_auth_url'] = config['auth_url']
    if 'auth_token' in config:
        ironic_kwargs['os_auth_token'] = config['auth_token']
    else:
        ironic_kwargs['os_username'] = config['auth_username']
        ironic_kwargs['os_password'] = config['auth_password']
        ironic_kwargs['os_user_domain_name'] = config['auth_domain']
        if 'project_name' in config:
            ironic_kwargs['os_project_name'] = config['project_name']
            ironic_kwargs['os_project_domain_name'] = config['auth_domain']
            ironic_kwargs['os_tenant_name'] = config['project_name']
    if 'region_name' in config:
        ironic_kwargs['os_region_name'] = config['region_name']
    logger.debug("Connecting with Ironic API url: '%s'" % config['url'])
    try:
        ironic = ironic_client.get_client(1, **ironic_kwargs)
    except ironic_exception.ClientException as e:
        msg = "Error connection Ironic API URL '%s'" % config['url']
        long_msg = msg + ': %s' % (e)
        logger.error(msg)
        raise CPIActionError(msg, long_msg)
    logger.info("Session created on Ironic API url: '%s'" % config['url'])
    return ironic


def wait_for_state(logger, ironic, uuid, ironic_timer, ironic_sleep, state='available'):
    # Sort of timeout for waiting in ironic loops. 30s x 40 is the limit
    while ironic_timer > 0:
        status = ironic.node.states(uuid).provision_state
        if status == state:
            logger.debug("Server id '%s' status '%s'" % (uuid, status))
            break
        logger.debug("Server id '%s' status '%s', waiting" % (uuid, status))
        time.sleep(ironic_sleep)
        ironic_timer -= 1
    else:
        msg = "Server id '%s' did not become '%s' after %d s."
        msg = msg % (uuid, state, (self.settings.ironic_sleep_times * ironic_sleep))
        long_msg = msg + ": Timeout Error"
        logger.error(long_msg)
        raise CPIActionError(msg, long_msg)


# EOF

