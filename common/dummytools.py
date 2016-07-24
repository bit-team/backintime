#    Copyright (C) 2012-2016 Germar Reitze
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

import gettext

import config
import mount

_=gettext.gettext

class Dummy(mount.MountControl):
    """
    This is a template for mounting services. For simple mount services
    all you need to do is:
    - add your settings in qt4/settingsdialog.py
    - add settings in common/config.p
    - modify a copy of this file

    Please use self.currentMountpoint as your local mountpoint.
    This class inherit from mount.MountControl. All methodes from MountControl can
    be used exactly like they were in this class.
    Methodes from MountControl also can be overriden in here if you need
    something different.
    """
    def __init__(self, *args, **kwargs):
        #init MountControl
        super(Dummy, self).__init__(*args, **kwargs)

        self.all_kwargs = {}

        #First we need to map the settings.
        #If <arg> is in kwargs (e.g. if this class is called with dummytools.Dummy(<arg> = <value>)
        #this will map self.<arg> to kwargs[<arg>]; else self.<arg> = <default> from config
        #e.g. self.setattrKwargs(<arg>, <default>, **kwargs)
        self.setattrKwargs('user', self.config.get_dummy_user(self.profile_id), **kwargs)
        self.setattrKwargs('host', self.config.get_dummy_host(self.profile_id), **kwargs)
        self.setattrKwargs('port', self.config.get_dummy_port(self.profile_id), **kwargs)
        self.setattrKwargs('password', self.config.password(parent, self.profile_id), store = False, **kwargs)

        self.setDefaultArgs()

        #if self.currentMountpoint is not the remote snapshot path you can specify
        #a subfolder of self.currentMountpoint for the symlink
        self.symlink_subfolder = None

        self.mountproc = 'dummy'
        self.log_command = '%s: %s@%s' % (self.mode, self.user, self.host)

    def _mount(self):
        """
        mount the service
        """
        #implement your mountprocess here
        pass

    def _umount(self):
        """
        umount the service
        """
        #implement your unmountprocess here
        pass

    def preMountCheck(self, first_run = False):
        """
        check what ever conditions must be given for the mount to be done successful
        raise MountException(_('Error discription')) if service can not mount
        return True if everything is okay
        all pre|post_[u]mount_check can also be used to prepare things or clean up
        """
        return True

    def postMountCheck(self):
        """
        check if mount was successful
        raise MountException(_('Error discription')) if not
        """
        return True

    def preUmountCheck(self):
        """
        check if service is safe to umount
        raise MountException(_('Error discription')) if not
        """
        return True

    def postUmountCheck(self):
        """
        check if umount successful
        raise MountException(_('Error discription')) if not
        """
        return True
