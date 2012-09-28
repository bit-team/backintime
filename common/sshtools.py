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
from time import sleep

import config
import logger

class SSHException(Exception):
    pass

class SSH:
    def __init__( self, cfg = None , host = False, port = False, user = False, path = False, local_path = False):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()
            
        self.ssh = self.config.get_ssh()
        self.ssh_host = self.config.get_ssh_host()
        self.ssh_port = self.config.get_ssh_port()
        self.ssh_user = self.config.get_ssh_user()
        self.ssh_path = self.config.get_snapshots_path_ssh()
        self.local_path = self.config.get_snapshots_path()
        if host:
            self.ssh = True
            self.ssh_host = host
        if port:
            self.ssh_port = port
        if user:
            self.ssh_user = user
        if path:
            self.ssh_path = path
        if local_path:
            self.local_path = local_path
        self.ssh_user_host_path = '%s@%s:%s' % (self.ssh_user, self.ssh_host, self.ssh_path)
        
    def mount(self):
        if self.is_mounted():
            logger.info('Mountpoint %s is already mounted' % self.local_path)
            self.set_mount_lock()
        else:
            self.check_known_hosts()
            self.check_login()
            self.check_fuse()
            try:
                subprocess.check_call(['sshfs', '-p', str(self.ssh_port), self.ssh_user_host_path, self.local_path])
            except subprocess.CalledProcessError as ex:
                raise SSHException('Can\'t mount sshfs %s' % self.local_path)
            logger.info('mount %s on %s' % (self.ssh_user_host_path, self.local_path))
            self.set_mount_lock()
        return True
        
    def umount(self):
        if self.is_mounted():
            if self.check_mount_lock():
                logger.info('Mountpoint %s still in use. Keep mounted' % self.local_path)
                self.del_mount_lock()
            else:
                logger.info('unmount %s' % self.local_path)
                self.del_mount_lock()
                try:
                    subprocess.check_call(['fusermount', '-u', self.local_path])
                except subprocess.CalledProcessError as ex:
                    raise SSHException('Can\'t unmount sshfs %s' % self.local_path)
        return True
        
    def is_mounted(self):
        """check if path is mounted. return False if not mounted"""
        if not os.path.isdir(self.local_path):
            raise SSHException('sshfs mountpoint %s doesn\'t exist.' % self.local_path)
        try:
            subprocess.check_call(['mountpoint', self.local_path], stdout=open(os.devnull, 'w'))
        except subprocess.CalledProcessError:
            if len(os.listdir(self.local_path)) > 0:
                raise SSHException('mountpoint %s not empty.' % self.local_path)
            return False
        else:
            return True
        
    def set_mount_lock(self):
        pid = str(os.getpid())
        mountlock = os.path.join(self.local_path, '.mount' + pid)
        with open(mountlock, 'w') as f:
            f.write(pid)
        
    def del_mount_lock(self, pid = False):
        if not pid:
            pid = str(os.getpid())
        mountlock = os.path.join(self.local_path, '.mount' + pid)
        os.remove(mountlock)
        
    def check_mount_lock(self):
        """check if no other running process has a mountlock.
           return true if an other process is locked"""
        pid = str(os.getpid())
        files = os.listdir(self.local_path)
        for file in files:
            if not file.startswith('.mount'):
                continue
            file_pid = file[len('.mount'):]
            if file_pid == pid:
                continue
            #check if other process is alive
            if os.path.exists(os.path.join('/proc', file_pid)):
                return True
            else:
                #process is dead.
                self.del_mount_lock(file_pid)
                continue
        return False
        
    def check_fuse(self):
        """check if sshfs is installed and user is part of group fuse"""
        if not self.pathexists('sshfs'):
            raise SSHException('sshfs not found. Please install e.g. \'apt-get install sshfs\'')
        user = os.getlogin()
        fuse_grp_members = grp.getgrnam('fuse')[3]
        if not user in fuse_grp_members:
            raise SSHException('%s is not member of group \'fuse\'. Run \'adduser %s fuse\' and relogin user.' % (user, user))
        
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
                                   self.ssh_user + '@' + self.ssh_host, 'echo', '"Hello"'], stdout=open(os.devnull, 'w'))
        except subprocess.CalledProcessError:
            raise SSHException('Passwordless authentication for %s@%s failed. Please follow http://www.debian-administration.org/articles/152'  % (self.ssh_user, self.ssh_host))
        
    def check_known_hosts(self):
        """check ssh_known_hosts"""
        output = subprocess.Popen(['ssh-keygen', '-F', self.ssh_host], stdout=subprocess.PIPE).communicate()[0] #subprocess.check_output doesn't exist in Python 2.6 (Debian squeeze default)
        if output.find('Host %s found' % self.ssh_host) < 0:
            raise SSHException('%s not found in ssh_known_hosts.' % self.ssh_host)
        