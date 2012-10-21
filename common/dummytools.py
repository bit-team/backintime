##Copyright (c) 2012 Germar Reitze <germar dot reitze(at)gmx dot de>
##
##Permission is hereby granted, free of charge, to any person obtaining a copy 
##of this software and associated documentation files (the "Software"), to deal 
##in the Software without restriction, including without limitation the rights 
##to use, copy, modify, merge, publish, distribute, sublicense, and/or sell 
##copies of the Software, and to permit persons to whom the Software is 
##furnished to do so, subject to the following conditions:
##
##The above copyright notice and this permission notice shall be included in all
##copies or substantial portions of the Software.
##
##THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
##IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
##FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
##AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
##LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
##OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
##SOFTWARE.

import gettext

import config
import mount

_=gettext.gettext

class Dummy(mount.MountControl):
    """
    This is a template for mounting services. For simple mount services
    all you need to do is:
    - add your settings in gnome|kde/settingsdialog.py (search for the dummy examples)
    - add settings in gnome/settingsdialog.glade (copy GtkFrame 'mode_dummy')
    - add settings in common/config.py (search for the dummy examples)
    - modify a copy of this file
    
    Please use self.mountpoint as your local mountpoint.
    This class inherit from mount.MountControl. All methodes from MountControl can
    be used exactly like they were in this class.
    Methodes from MountControl also can be overriden in here if you need
    something different."""
    def __init__(self, cfg = None, profile_id = None, hash_id = None, tmp_mount = False, **kwargs):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()
            
        self.profile_id = profile_id
        if not self.profile_id:
            self.profile_id = self.config.get_current_profile()
            
        self.tmp_mount = tmp_mount
        self.hash_id = hash_id
            
        #init MountControl
        mount.MountControl.__init__(self)
            
        self.all_kwargs = {}
            
        #First we need to map the settings. 
        #If <arg> is in kwargs (e.g. if this class is called with dummytools.Dummy(<arg> = <value>)
        #this will map self.<arg> to kwargs[<arg>]; else self.<arg> = <default> from config
        #e.g. self.setattr_kwargs(<arg>, <default>, **kwargs)
        self.setattr_kwargs('mode', self.config.get_snapshots_mode(self.profile_id), **kwargs)
        self.setattr_kwargs('hash_collision', self.config.get_hash_collision(), **kwargs)
        #start editing from here---------------------------------------------------------
        self.setattr_kwargs('user', self.config.get_dummy_user(self.profile_id), **kwargs)
        self.setattr_kwargs('host', self.config.get_dummy_host(self.profile_id), **kwargs)
        self.setattr_kwargs('port', self.config.get_dummy_port(self.profile_id), **kwargs)
            
        self.set_default_args()
        
        #if self.mountpoint is not the remote snapshot path you can specify
        #a subfolder of self.mountpoint for the symlink
        self.symlink_subfolder = None
            
        self.log_command = '%s: %s@%s' % (self.mode, self.user, self.host)
        
    def _mount(self):
        """mount the service"""
        #implement your mountprocess here
        pass
        
    def _umount(self):
        """umount the service"""
        #implement your unmountprocess here
        pass
        
    def pre_mount_check(self, first_run = False):
        """check what ever conditions must be given for the mount to be done successful
           raise MountException( _('Error discription') ) if service can not mount
           return True if everything is okay
           all pre|post_[u]mount_check can also be used to prepare things or clean up"""
        return True
        
    def post_mount_check(self):
        """check if mount was successful
           raise MountException( _('Error discription') ) if not"""
        return True
        
    def pre_umount_check(self):
        """check if service is safe to umount
           raise MountException( _('Error discription') ) if not"""
        return True
        
    def post_umount_check(self):
        """check if umount successful
           raise MountException( _('Error discription') ) if not"""
        return True
        