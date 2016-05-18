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
        stemcell_id = self.args[0]
        image_id = stemcell_id + self.settings.stemcell_image_ext
        image_meta = stemcell_id + self.settings.stemcell_metadata_ext
        repository =  self.repository.manage(config['stemcell'])
        try:
            if repository.exists(image_id):
                repository.delete(image_id)
            if repository.exists(image_meta):
                repository.delete(image_meta)  
        except RepositoryError as e:
            msg = "Cannot delete '%s' from repository" % stemcell_id
            long_msg = msg + ": %s" % (e)
            self.logger.error(msg)
            raise CPIActionError(msg, long_msg)
        self.logger.debug("Stemcell id '%s' deleted" % stemcell_id)

# EOF

