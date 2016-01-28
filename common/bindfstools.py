#    Copyright (C) 2016 Taylor Raack
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import subprocess
import gettext

from mount import MountControl
import logger
from exceptions import MountException

_=gettext.gettext

class Local(MountControl):
    """
    Mount local path with bindfs. This allows for read-only viewing of snapshots stored on a locally mounted filesystem.
    """

    def __init__(self, *args, **kwargs):
        #init MountControl
        super(Local, self).__init__(*args, **kwargs)

        #First we need to map the settings.
        self.setattr_kwargs('path', self.config.get_local_path(self.profile_id), **kwargs)

        self.set_default_args()
        
        self.mountproc = 'bindfs'
        self.symlink_subfolder = None

        self.log_command = '%s: %s' % (self.mode, self.path)

    def _mount(self):
        """
        mount the local filesystem over bind
        """
        bindfs = [self.mountproc, '-n']

        # use read only mount if requested
        if self.read_only:
            bindfs.extend(['-o', 'ro'])

        bindfs.extend([self.path, self.mountpoint])
        logger.debug('Call mount command: %s'
                     %' '.join(bindfs),
                     self)
        try:
            subprocess.check_call(bindfs)
        except subprocess.CalledProcessError:
            raise MountException( _('Can\'t mount %s') % ' '.join(bindfs))

    def pre_mount_check(self, first_run = False):
        """
        check what ever conditions must be given for the mount to be done successful
        raise MountException( _('Error description') ) if service can not mount
        return True if everything is okay
        all pre|post_[u]mount_check can also be used to prepare things or clean up
        """
        self.check_fuse()
        return True
