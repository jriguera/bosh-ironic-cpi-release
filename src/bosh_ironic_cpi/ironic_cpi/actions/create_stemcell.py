#!/usr/bin/env python
# -*- encoding: utf-8 -*-
"""
BOSH OpenStack Ironic CPI
"""
# Python 2 and 3 compatibility
from __future__ import unicode_literals

import shutil
import tempfile
import tarfile
import hashlib
import os.path
import StringIO

from ironic_cpi.action import CPIAction
from ironic_cpi.action import CPIActionError
from ironic_cpi.actions.repositories.repository import RepositoryManager
from ironic_cpi.actions.repositories.repository import RepositoryError
# Import all repository implementations
from ironic_cpi.actions.repositories.webdav import WebDav



class Create_Stemcell(CPIAction):
    action = 'create_stemcell'

    def __init__(self, context):
        super(Create_Stemcell, self).__init__(context)
        self.repository = RepositoryManager(self.logger)

    @staticmethod
    def md5(fname):
        hash_md5 = hashlib.md5()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    ##
    # Creates a new OpenStack Image using stemcell image. It requires access
    # to the OpenStack Glance service.
    #
    # @param [String] image_path Local filesystem path to a stemcell image
    # @param [Hash] cloud_properties CPI-specific properties
    # @return [String] Image UUID of the stemcell
    def run(self, config):
        image_path = self.args[0]
        image_params = self.args[1]
        self.logger.debug("Creating stemcell with params: %s" % (image_params))
        if image_params['disk_format'] != 'qcow2':
            msg = "Disk format '%s' unknown!" % (image_params['disk_format'])
            long_msg = "The disk format is not supported, please use 'qcow2'"
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)  
        if image_params['container_format'] != 'bare':
            msg = "Container format '%s' unknown!" % (image_params['container_format'])
            long_msg = "The container format is not supported, use 'bare'"
            self.logger.error(long_msg)
            raise CPIActionError(msg, long_msg)
        repository =  self.repository.manage(config['stemcell'])
        stemcell_id = self.settings.stemcell_id_format.format(**image_params)
        image_id = stemcell_id + self.settings.stemcell_image_ext
        image_meta = stemcell_id + self.settings.stemcell_metadata_ext
        tmp_dir = tempfile.mkdtemp('_create_stemcell')
        try:
            self.logger.debug("Extracting '%s' to '%s'" % (image_path, tmp_dir))
            with tarfile.open(image_path, 'r') as tar:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                    
                
                safe_extract(tar, tmp_dir)
                root_image = os.path.join(tmp_dir, self.settings.stemcell_image)
                root_md5 = self.md5(root_image)
                self.logger.debug("MD5sum(%s): '%s'" % (root_image, root_md5))
                # Send the file to the repository
                self.logger.debug("Uploading image '%s' to repository" % (image_id))
                repository.put(root_image,  image_id)
                # Create md5 file and append the original name
                self.logger.debug("Uploading metadata '%s' to repository" % (image_meta))
                meta_content = '{0} {1}\n'.format(root_md5, image_params['name'])
                repository.put(StringIO.StringIO(meta_content), image_meta)
        except RepositoryError as e:
            msg = "Cannot save '%s' in the repository" % (stemcell_id)
            long_msg = msg + ': %s' % (e)
            self.logger.error(msg)
            raise CPIActionError(msg, long_msg)
        except Exception as e:
            msg = "%s: %s" % (type(e).__name__, e)
            self.logger.error(msg)
            raise CPIActionError(msg, msg)
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir)
        self.logger.debug("Done. Stemcell id: '%s' created" % (stemcell_id))
        return stemcell_id


# EOF

