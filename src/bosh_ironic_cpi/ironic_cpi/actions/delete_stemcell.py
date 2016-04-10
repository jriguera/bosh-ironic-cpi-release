#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

from ironic_cpi.action import CPIAction
from ironic_cpi.action import CPIActionError
from ironic_cpi.actions.repositories.repository import RepositoryManager
from ironic_cpi.actions.repositories.repository import RepositoryError
# Import all repository implementations
from ironic_cpi.actions.repositories.webdav import WebDav


class Delete_Stemcell(CPIAction):
    action = 'delete_stemcell'

    def __init__(self, context):
        super(Delete_Stemcell, self).__init__(context)
        self.repository = RepositoryManager(self.logger)

    ##
    # Deletes a stemcell
    #
    # @param [String] stemcell_id, image UUID of the stemcell to be deleted
    # @return [void]
    def run(self, config):
        image_id = self.args[0]
        repository =  self.repository.manage(config['stemcell'])
        try:
            stemcell_id = image_id + '.qcow2'
            if repository.exists(stemcell_id):
                repository.delete(stemcell_id)
            stemcell_md5 = image_id + '.md5'
            if repository.exists(stemcell_md5):
                repository.delete(stemcell_md5)  
        except RepositoryError as e:
            msg = "Cannot delete '%s' from repository" % image_id
            long_msg = msg + ': %s' % (e)
            self.logger.error(msg)
            raise CPIActionError(msg, long_msg)
        self.logger.debug("Stemcell '%s' deleted" % image_id)


# EOF

