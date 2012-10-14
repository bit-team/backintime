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

import os
import grp
import subprocess
import gettext
from time import sleep

import config
import mount
import logger

_=gettext.gettext

class SSH(mount.MountControl):
    """
    Mount remote path with sshfs. The real take_snapshot process will use
    rsync over ssh. Other commands run remote over ssh.
    """
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
        self.setattr_kwargs('mode', self.config.get_snapshots_mode(self.profile_id), **kwargs)
        self.setattr_kwargs('hash_collision', self.config.get_hash_collision(), **kwargs)
        #start editing from here---------------------------------------------------------
        self.setattr_kwargs('user', self.config.get_ssh_user(self.profile_id), **kwargs)
        self.setattr_kwargs('host', self.config.get_ssh_host(self.profile_id), **kwargs)
        self.setattr_kwargs('port', self.config.get_ssh_port(self.profile_id), **kwargs)
        self.setattr_kwargs('path', self.config.get_snapshots_path_ssh(self.profile_id), **kwargs)
        self.setattr_kwargs('cipher', self.config.get_ssh_cipher(self.profile_id), **kwargs)
            
        self.set_default_args()
            
        self.symlink_subfolder = None
        self.user_host_path = '%s@%s:%s' % (self.user, self.host, self.path)
        self.log_command = '%s: %s' % (self.mode, self.user_host_path)
        
    def _mount(self):
        """mount the service"""
        sshfs = ['sshfs', '-p', str(self.port)]
        if not self.cipher == 'default':
            sshfs.extend(['-o', 'Ciphers=%s' % self.cipher])
        sshfs.extend([self.user_host_path, self.mountpoint])
        try:
            subprocess.check_call(sshfs)
        except subprocess.CalledProcessError as ex:
            raise mount.MountException( _('Can\'t mount %s') % ' '.join(sshfs))
        
    def _umount(self):
        """umount the service"""
        try:
            subprocess.check_call(['fusermount', '-u', self.mountpoint])
        except subprocess.CalledProcessError as ex:
            raise mount.MountException( _('Can\'t unmount sshfs %s') % self.mountpoint)
        
    def pre_mount_check(self):
        """check what ever conditions must be given for the mount to be done successful
           raise MountException( _('Error discription') ) if service can not mount
           return True if everything is okay
           all pre|post_[u]mount_check can also be used to prepare things or clean up"""
        self.check_fuse()
        self.check_known_hosts()
        self.check_login()
        self.check_cipher()
        self.check_remote_folder()
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
        
    def check_fuse(self):
        """check if sshfs is installed and user is part of group fuse"""
        if not self.pathexists('sshfs'):
            raise mount.MountException( _('sshfs not found. Please install e.g. \'apt-get install sshfs\'') )
        user = self.config.get_user()
        fuse_grp_members = grp.getgrnam('fuse')[3]
        if not user in fuse_grp_members:
            raise mount.MountException( _('%s is not member of group \'fuse\'.\n Run \'adduser %s fuse\' as root and relogin user.') % (user, user))
        
    def pathexists(self, filename):
        """Checks if 'filename' is present in the system PATH.
        In other words, it checks if os.execvp(filename, ...) will work.
        shameless stolen from GnuPGInterface;)"""
        pathenv = os.getenv("PATH")
        path = pathenv.split(":")
        for directory in path:
            fullpath = os.path.join(directory, filename)
            if (os.path.exists(fullpath)):
                return True
        return False
        
    def check_login(self):
        """check passwordless authentication to host"""
        try:
            subprocess.check_call(['ssh', '-o', 'PreferredAuthentications=publickey', \
                                   self.user + '@' + self.host, 'echo', '"Hello"'], stdout=open(os.devnull, 'w'))
        except subprocess.CalledProcessError:
            raise mount.MountException( _('Passwordless authentication for %s@%s failed. Please follow:\n http://www.debian-administration.org/articles/152')  % (self.user, self.host))
        
    def check_cipher(self):
        """check if both host and localhost support cipher"""
        if not self.cipher == 'default':
            ssh = ['ssh']
            ssh.extend(['-o', 'Ciphers=%s' % self.cipher])
            ssh.extend([self.user + '@' + self.host, 'echo', '"Hello"'])
            err = subprocess.Popen(ssh, stdout=open(os.devnull, 'w'), stderr=subprocess.PIPE).communicate()[1]
            if err:
                raise mount.MountException( _('Cipher %s failed for %s:\n%s')  % (self.cipher, self.host, err))
            
    def benchmark_cipher(self, size = '40'):
        import tempfile
        temp = tempfile.mkstemp()[1]
        print('create random data file')
        subprocess.call(['dd', 'if=/dev/urandom', 'of=%s' % temp, 'bs=1M', 'count=%s' % size])
        keys = self.config.SSH_CIPHERS.keys()
        keys.sort()
        for cipher in keys:
            if cipher == 'default':
                continue
            print('%s:' % cipher)
            for i in range(2):
                subprocess.call(['scp', '-c', cipher, temp, self.user_host_path])
        subprocess.call(['ssh', '%s@%s' % (self.user, self.host), 'rm', os.path.join(self.path, os.path.basename(temp))])
        os.remove(temp)
        
    def check_known_hosts(self):
        """check ssh_known_hosts"""
        output = subprocess.Popen(['ssh-keygen', '-F', self.host], stdout=subprocess.PIPE).communicate()[0] #subprocess.check_output doesn't exist in Python 2.6 (Debian squeeze default)
        if output.find('Host %s found' % self.host) < 0:
            raise mount.MountException( _('%s not found in ssh_known_hosts.') % self.host)
        
    def check_remote_folder(self):
        """check if remote folder exists and is write- and executable.
           Create folder if it doesn't exist."""
        cmd  = 'd=0;'
        cmd += '[[ -a %s ]] || d=1;' % self.path                 #path doesn't exist. set d=1 to indicate
        cmd += '[[ $d -eq 1 ]] && mkdir %s; err=$?;' % self.path #create path, get errorcode from mkdir
        cmd += '[[ $d -eq 1 ]] && exit $err;'                    #return errorcode from mkdir
        cmd += '[[ -d %s ]] || exit 11;' % self.path #path is no directory
        cmd += '[[ -w %s ]] || exit 12;' % self.path #path is not writeable
        cmd += '[[ -x %s ]] || exit 13;' % self.path #path is not executable
        cmd += 'exit 20'                             #everything is fine
        try:
            subprocess.check_call(['ssh', self.user + '@' + self.host, cmd], stdout=open(os.devnull, 'w'))
        except subprocess.CalledProcessError as ex:
            if ex.returncode == 20:
                #clean exit
                pass
            elif ex.returncode == 11:
                raise mount.MountException( _('Remote path exists but is not a directory:\n %s') % self.path)
            elif ex.returncode == 12:
                raise mount.MountException( _('Remote path is not writeable:\n %s') % self.path)
            elif ex.returncode == 13:
                raise mount.MountException( _('Remote path is not executable:\n %s') % self.path)
            else:
                raise mount.MountException( _('Couldn\'t create remote path:\n %s') % self.path)
        else:
            #returncode is 0
            logger.info('Create remote folder %s' % self.path)
            
