#    Copyright (C) 2012-2016 Germar Reitze, Taylor Raack
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

import os
import grp
import subprocess
import gettext
import string
import random
import tempfile
import socket
from time import sleep

import config
import logger
import tools
import password_ipc
from mount import MountControl
from exceptions import MountException
import bcolors

_=gettext.gettext

class SSH(MountControl):
    """
    Mount remote path with sshfs. The real take_snapshot process will use
    rsync over ssh. Other commands run remote over ssh.
    """
    def __init__(self, *args, **kwargs):
        #init MountControl
        super(SSH, self).__init__(*args, **kwargs)

        self.setattr_kwargs('user', self.config.get_ssh_user(self.profile_id), **kwargs)
        self.setattr_kwargs('host', self.config.get_ssh_host(self.profile_id), **kwargs)
        self.setattr_kwargs('port', self.config.get_ssh_port(self.profile_id), **kwargs)
        self.setattr_kwargs('path', self.config.get_snapshots_path_ssh(self.profile_id), **kwargs)
        self.setattr_kwargs('cipher', self.config.get_ssh_cipher(self.profile_id), **kwargs)
        self.setattr_kwargs('private_key_file', self.config.get_ssh_private_key_file(self.profile_id), **kwargs)
        self.setattr_kwargs('nice', self.config.is_run_nice_on_remote_enabled(self.profile_id), store = False, **kwargs)
        self.setattr_kwargs('ionice', self.config.is_run_ionice_on_remote_enabled(self.profile_id), store = False, **kwargs)
        self.setattr_kwargs('nocache', self.config.is_run_nocache_on_remote_enabled(self.profile_id), store = False, **kwargs)
        self.setattr_kwargs('password', None, store = False, **kwargs)

        if not self.path:
            self.path = './'
        self.set_default_args()

        # config strings used in ssh-calls
        self.user_host_path = '%s@%s:%s' % (self.user, self.host, self.path)
        self.user_host = '%s@%s' % (self.user, self.host)

        # ssh_options contains port but can be extended to include cipher, customkeyfile, etc
        self.ssh_options = ['-p', str(self.port)]
        self.ssh_options += ['-o', 'ServerAliveInterval=240']

        # specifying key file here allows to override for potentially
        # conflicting .ssh/config key entry
        self.ssh_options += ['-o', 'IdentityFile=%s' % self.private_key_file]

        self.mountproc = 'sshfs'
        self.symlink_subfolder = None
        self.log_command = '%s: %s' % (self.mode, self.user_host_path)

        self.private_key_fingerprint = tools.getSshKeyFingerprint(self.private_key_file)
        if not self.private_key_fingerprint:
            logger.warning('Couldn\'t get fingerprint for private key %(path)s. '
                           'Most likely because the public key %(path)s.pub wasn\'t found. '
                           'Using fallback to private keys path instead. '
                           'But this can make troubles with passphrase-less keys.'
                           %{'path': self.private_key_file},
                           self)
            self.private_key_fingerprint = self.private_key_file
        self.unlock_ssh_agent()

    def _mount(self):
        """
        mount the service
        """
        sshfs = [self.mountproc] + self.ssh_options
        if not self.cipher == 'default':
            sshfs.extend(['-o', 'Ciphers=%s' % self.cipher])
        sshfs.extend(['-o', 'idmap=user',
                      '-o', 'cache_dir_timeout=2'])

        sshfs.extend([self.user_host_path, self.mountpoint])
        #bugfix: sshfs doesn't mount if locale in LC_ALL is not available on remote host
        #LANG or other envirnoment variable are no problem.
        env = os.environ.copy()
        if 'LC_ALL' in list(env.keys()):
            env['LC_ALL'] = 'C'
        logger.debug('Call mount command: %s'
                     %' '.join(sshfs),
                     self)
        try:
            subprocess.check_call(sshfs, env = env)
        except subprocess.CalledProcessError:
            raise MountException( _('Can\'t mount %s') % ' '.join(sshfs))

    def pre_mount_check(self, first_run = False):
        """
        check what ever conditions must be given for the mount to be done successful
        raise MountException( _('Error discription') ) if service can not mount
        return True if everything is okay
        all pre|post_[u]mount_check can also be used to prepare things or clean up
        """
        self.check_ping_host()
        self.check_fuse()
        if first_run:
            self.unlock_ssh_agent(force = True)
            self.check_known_hosts()
        self.check_login()
        if first_run:
            self.check_cipher()
        self.check_remote_folder()
        if first_run:
            self.check_remote_commands()
        return True

    def unlock_ssh_agent(self, force = False):
        """
        using askpass.py to unlock private key in ssh-agent
        """
        env = os.environ.copy()
        env['SSH_ASKPASS'] = 'backintime-askpass'
        env['ASKPASS_PROFILE_ID'] = self.profile_id
        env['ASKPASS_MODE'] = self.mode

        if force:
            #remove private key first so we can check if the given password is valid
            logger.debug('Remove private key %s from ssh agent' % self.private_key_file, self)
            proc = subprocess.Popen(['ssh-add', '-d', self.private_key_file],
                                    stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    universal_newlines = True)
            proc.communicate()

        proc = subprocess.Popen(['ssh-add', '-l'],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
        output = proc.communicate()[0]
        if force or not output.find(self.private_key_fingerprint) >= 0:
            logger.debug('Add private key %s to ssh agent' % self.private_key_file, self)
            password_available = any([self.config.get_password_save(self.profile_id),
                                      self.config.get_password_use_cache(self.profile_id),
                                      not self.password is None
                                      ])
            logger.debug('Password available: %s' %password_available, self)
            if not password_available and not tools.check_x_server():
                #we need to unlink stdin from ssh-add in order to make it
                #use our own backintime-askpass.
                #But because of this we can NOT use getpass inside backintime-askpass
                #if password is not saved and there is no x-server.
                #So, let's just keep ssh-add asking for the password in that case.
                alarm = tools.Alarm()
                alarm.start(10)
                try:
                    proc = subprocess.call(['ssh-add', self.private_key_file])
                    alarm.stop()
                except tools.Timeout:
                    pass
            else:
                if self.password:
                    logger.debug('Provide password through temp FIFO', self)
                    thread = password_ipc.TempPasswordThread(self.password)
                    env['ASKPASS_TEMP'] = thread.temp_file
                    thread.start()

                proc = subprocess.Popen(['ssh-add', self.private_key_file],
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        env = env,
                                        preexec_fn = os.setsid,
                                        universal_newlines = True)
                output, error = proc.communicate()
                if proc.returncode:
                    logger.error('Failed to unlock SSH private key %s: %s'
                                 %(self.private_key_file, error),
                                 self)

                if self.password:
                    thread.stop()

            proc = subprocess.Popen(['ssh-add', '-l'],
                                    stdout = subprocess.PIPE,
                                    universal_newlines = True)
            output = proc.communicate()[0]
            if not output.find(self.private_key_fingerprint) >= 0:
                logger.debug('Was not able to unlock private key %s' %self.private_key_file, self)
                raise MountException( _('Could not unlock ssh private key. Wrong password '
                                        'or password not available for cron.'))
        else:
            logger.debug('Private key %s is already unlocked in ssh agent'
                         %self.private_key_file, self)

    def check_login(self):
        """
        check passwordless authentication to host
        """
        logger.debug('Check login', self)
        ssh = ['ssh', '-o', 'PreferredAuthentications=publickey']
        ssh.extend(self.ssh_options + [self.user_host])
        ssh.extend(self.config.ssh_prefix_cmd(self.profile_id, cmd_type = list))
        ssh.extend(['echo', '"Hello"'])
        try:
            subprocess.check_call(ssh, stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            raise MountException( _('Password-less authentication for %(user)s@%(host)s '
                                    'failed. Look at \'man backintime\' for further '
                                    'instructions.')  % {'user' : self.user, 'host' : self.host})

    def check_cipher(self):
        """
        check if both host and localhost support cipher
        """
        if not self.cipher == 'default':
            logger.debug('Check cipher', self)
            ssh = ['ssh']
            ssh.extend(['-o', 'Ciphers=%s' % self.cipher])
            ssh.extend(self.ssh_options + [self.user_host])
            ssh.extend(self.config.ssh_prefix_cmd(self.profile_id, cmd_type = list))
            ssh.extend(['echo', '"Hello"'])
            proc = subprocess.Popen(ssh,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE,
                                    universal_newlines = True)
            err = proc.communicate()[1]
            if proc.returncode:
                logger.debug('Ciper %s is not supported' %self.config.SSH_CIPHERS[self.cipher], self)
                raise MountException( _('Cipher %(cipher)s failed for %(host)s:\n%(err)s')
                                      % {'cipher' : self.config.SSH_CIPHERS[self.cipher], 'host' : self.host, 'err' : err})

    def benchmark_cipher(self, size = '40'):
        temp = tempfile.mkstemp()[1]
        print('create random data file')
        subprocess.call(['dd', 'if=/dev/urandom', 'of=%s' % temp, 'bs=1M', 'count=%s' % size])
        keys = list(self.config.SSH_CIPHERS.keys())
        keys.sort()
        for cipher in keys:
            if cipher == 'default':
                continue
            print('%s%s:%s' %(bcolors.BOLD, cipher, bcolors.ENDC))
            for i in range(2):
                # scp uses -P instead of -p for port
                subprocess.call(['scp', '-P', str(self.port), '-c', cipher, temp, self.user_host_path])
        ssh = ['ssh']
        ssh.extend(self.ssh_options + [self.user_host])
        ssh.extend(self.config.ssh_prefix_cmd(self.profile_id, cmd_type = list))
        ssh.extend(['rm', os.path.join(self.path, os.path.basename(temp)) ])
        subprocess.call(ssh)
        os.remove(temp)

    def check_known_hosts(self):
        """
        check ssh_known_hosts
        """
        logger.debug('Check known hosts file', self)
        for host in (self.host, '[%s]:%s' % (self.host, self.port)):
            proc = subprocess.Popen(['ssh-keygen', '-F', host],
                                    stdout=subprocess.PIPE,
                                    universal_newlines = True)
            output = proc.communicate()[0] #subprocess.check_output doesn't exist in Python 2.6 (Debian squeeze default)
            if output.find('Host %s found' % host) >= 0:
                logger.debug('Host %s was found in known hosts file' % host, self)
                return True
        logger.debug('Host %s is not in known hosts file' %self.host, self)
        raise MountException( _('%s not found in ssh_known_hosts.') % self.host)

    def check_remote_folder(self):
        """
        check if remote folder exists and is write- and executable.
        Create folder if it doesn't exist.
        """
        logger.debug('Check remote folder', self)
        cmd  = 'd=0;'
        cmd += 'test -e %s || d=1;' % self.path                 #path doesn't exist. set d=1 to indicate
        cmd += 'test $d -eq 1 && mkdir %s; err=$?;' % self.path #create path, get errorcode from mkdir
        cmd += 'test $d -eq 1 && exit $err;'                    #return errorcode from mkdir
        cmd += 'test -d %s || exit 11;' % self.path #path is no directory
        cmd += 'test -w %s || exit 12;' % self.path #path is not writeable
        cmd += 'test -x %s || exit 13;' % self.path #path is not executable
        cmd += 'exit 20'                             #everything is fine
        ssh = ['ssh']
        ssh.extend(self.ssh_options + [self.user_host])
        ssh.extend(self.config.ssh_prefix_cmd(self.profile_id, cmd_type = list))
        ssh.extend([cmd])
        logger.debug('Call command: %s' %' '.join(ssh), self)
        try:
            subprocess.check_call(ssh,
                                  stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as ex:
            logger.debug('Command returncode: %s' %ex.returncode, self)
            if ex.returncode == 20:
                #clean exit
                pass
            elif ex.returncode == 11:
                raise MountException( _('Remote path exists but is not a directory:\n %s') % self.path)
            elif ex.returncode == 12:
                raise MountException( _('Remote path is not writeable:\n %s') % self.path)
            elif ex.returncode == 13:
                raise MountException( _('Remote path is not executable:\n %s') % self.path)
            else:
                raise MountException( _('Couldn\'t create remote path:\n %s') % self.path)
        else:
            #returncode is 0
            logger.info('Create remote folder %s' %self.path, self)

    def check_ping_host(self):
        """
        connect to remote port and check if it is open
        """
        logger.debug('Check ping host', self)
        count = 0
        while count < 5:
            try:
                with socket.create_connection((self.host, self.port), 2.0) as s:
                    result = s.connect_ex(s.getpeername())
            except:
                result = -1
            if result == 0:
                logger.debug('Host %s is available' %self.host, self)
                return
            logger.debug('Could not ping host %s. Try again' %self.host, self)
            count += 1
            sleep(0.2)
        if result != 0:
            logger.debug('Failed pinging host %s' %self.host, self)
            raise MountException( _('Ping %s failed. Host is down or wrong address.') % self.host)

    def check_remote_commands(self, retry = False):
        """
        try all relevant commands for take_snapshot on remote host.
        specialy embedded Linux devices using 'BusyBox' sometimes doesn't
        support everything that is need to run backintime.
        also check for hardlink-support on remote host.
        """
        logger.debug('Check remote commands', self)
        def maxArg():
            if retry:
                raise MountException("Checking commands on remote host didn't return any output. "
                                     "We already checked the maximum argument lenght but it seem like "
                                     "there is an other problem")
            logger.warning('Looks like the command was to long for remote SSHd. We will test max arg length now and retry.',
                           self)
            import sshMaxArg
            mid = sshMaxArg.test_ssh_max_arg(self.user_host)
            sshMaxArg.reportResult(self.host, mid)
            self.config.set_ssh_max_arg_length(mid, self.profile_id)
            return self.check_remote_commands(retry = True)

        #check rsync
        tmp_file = tempfile.mkstemp()[1]
        rsync = tools.get_rsync_prefix( self.config ) + ' --dry-run --chmod=Du+wx %s ' % tmp_file
        rsync += '"%s@%s:%s"' % (self.user, self.host, self.path)
        logger.debug('Check rsync command: %s' %rsync, self)

        #use os.system for compatiblity with snapshots.py
        err = os.system(rsync)
        if err:
            logger.debug('Rsync command returnd error: %s' %err, self)
            os.remove(tmp_file)
            raise MountException( _('Remote host %(host)s doesn\'t support \'%(command)s\':\n'
                                    '%(err)s\nLook at \'man backintime\' for further instructions')
                                    % {'host' : self.host, 'command' : rsync, 'err' : err})
        os.remove(tmp_file)

        #check cp chmod find and rm
        remote_tmp_dir = os.path.join(self.path, 'tmp_%s' % self.random_id())
        head  = 'tmp=%s ; ' % remote_tmp_dir
        #first define a function to clean up and exit
        head += 'cleanup(){ '
        head += 'test -e $tmp/a && rm $tmp/a >/dev/null 2>&1; '
        head += 'test -e $tmp/b && rm $tmp/b >/dev/null 2>&1; '
        head += 'test -e smr.lock && rm smr.lock >/dev/null 2>&1; '
        head += 'test -e $tmp && rmdir $tmp >/dev/null 2>&1; '
        head += 'exit $1; }; '
        tail = []
        #create tmp_RANDOM dir and file a
        cmd  = 'test -e $tmp || mkdir $tmp; touch $tmp/a; '
        tail.append(cmd)

        #try to create hardlink b from a
        cmd  = 'echo \"cp -aRl SOURCE DEST\"; cp -aRl $tmp/a $tmp/b >/dev/null; err_cp=$?; '
        cmd += 'test $err_cp -ne 0 && cleanup $err_cp; '
        tail.append(cmd)
        #list inodes of a and b
        cmd  = 'ls -i $tmp/a; ls -i $tmp/b; '
        tail.append(cmd)
        #try to chmod
        cmd  = 'echo \"chmod u+rw FILE\"; chmod u+rw $tmp/a >/dev/null; err_chmod=$?; '
        cmd += 'test $err_chmod -ne 0 && cleanup $err_chmod; '
        tail.append(cmd)
        #try to find and chmod
        cmd  = 'echo \"find PATH -type f -exec chmod u-wx \"{}\" \\;\"; '
        cmd += 'find $tmp -type f -exec chmod u-wx \"{}\" \\; >/dev/null; err_find=$?; '
        cmd += 'test $err_find -ne 0 && cleanup $err_find; '
        tail.append(cmd)
        #try find suffix '+'
        cmd  = 'find $tmp -type f -exec chmod u-wx \"{}\" + >/dev/null; err_gnu_find=$?; '
        cmd += 'test $err_gnu_find -ne 0 && echo \"gnu_find not supported\"; '
        tail.append(cmd)
        #try to rm -rf
        cmd  = 'echo \"rm -rf PATH\"; rm -rf $tmp >/dev/null; err_rm=$?; '
        cmd += 'test $err_rm -ne 0 && cleanup $err_rm; '
        tail.append(cmd)
        #try nice -n 19
        if self.nice:
            cmd  = 'echo \"nice -n 19\"; nice -n 19 true >/dev/null; err_nice=$?; '
            cmd += 'test $err_nice -ne 0 && cleanup $err_nice; '
            tail.append(cmd)
        #try ionice -c2 -n7
        if self.ionice:
            cmd  = 'echo \"ionice -c2 -n7\"; ionice -c2 -n7 true >/dev/null; err_nice=$?; '
            cmd += 'test $err_nice -ne 0 && cleanup $err_nice; '
            tail.append(cmd)
        #try nocache
        if self.nocache:
            cmd  = 'echo \"nocache\"; nocache true >/dev/null; err_nocache=$?; '
            cmd += 'test $err_nocache -ne 0 && cleanup $err_nocache; '
            tail.append(cmd)
        #try screen, bash and flock used by smart-remove running in background
        if self.config.get_smart_remove_run_remote_in_background(self.profile_id):
            cmd  = 'echo \"screen -d -m bash -c ...\"; screen -d -m bash -c \"true\" >/dev/null; err_screen=$?; '
            cmd += 'test $err_screen -ne 0 && cleanup $err_screen; '
            cmd += 'echo \"(flock -x 9) 9>smr.lock\"; bash -c \"(flock -x 9) 9>smr.lock\" >/dev/null; err_flock=$?; '
            cmd += 'test $err_flock -ne 0 && cleanup $err_flock; '
            tail.append(cmd)
        #if we end up here, everything should be fine
        cmd = 'echo \"done\"'
        tail.append(cmd)

        maxLength = self.config.ssh_max_arg_length(self.profile_id)
        additionalChars = len('echo ""') + len(self.config.ssh_prefix_cmd(self.profile_id, cmd_type = str))

        ssh = ['ssh']
        ssh.extend(self.ssh_options + [self.user_host])
        ssh.extend(self.config.ssh_prefix_cmd(self.profile_id, cmd_type = list))
        output = ''
        err = ''
        returncode = 0
        for cmd in tools.splitCommands(tail,
                                       head = head,
                                       maxLength = maxLength - additionalChars):
            if cmd.endswith('; '):
                cmd += 'echo ""'
            c = ssh[:]
            c.extend([cmd])
            try:
                logger.debug('Call command: %s' %' '.join(c), self)
                proc = subprocess.Popen(c,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines = True)
                ret = proc.communicate()
            except OSError as e:
                #Argument list too long
                if e.errno == 7:
                    logger.debug('Argument list too log (Python exception)', self)
                    return maxArg()
                else:
                    raise
            logger.debug('Command stdout: %s' %ret[0], self)
            logger.debug('Command stderr: %s' %ret[1], self)
            logger.debug('Command returncode: %s' %proc.returncode, self)
            output += ret[0].strip('\n') + '\n'
            err    += ret[1].strip('\n') + '\n'
            returncode += proc.returncode
            if proc.returncode:
                break

        output_split = output.strip('\n').split('\n')

        while True:
            if output_split and not output_split[-1]:
                output_split = output_split[:-1]
            else:
                break

        if not output_split:
            return maxArg()

        gnu_find_suffix_support = True
        for line in output_split:
            if line.startswith('gnu_find not supported'):
                gnu_find_suffix_support = False
        self.config.set_gnu_find_suffix_support(gnu_find_suffix_support, self.profile_id)

        if returncode or not output_split[-1].startswith('done'):
            for command in ('cp', 'chmod', 'find', 'rm', 'nice', 'ionice', 'nocache', 'screen', '(flock'):
                if output_split[-1].startswith(command):
                    raise MountException( _('Remote host %(host)s doesn\'t support \'%(command)s\':\n'
                                            '%(err)s\nLook at \'man backintime\' for further instructions')
                                            % {'host' : self.host, 'command' : output_split[-1], 'err' : err})
            raise MountException( _('Check commands on host %(host)s returned unknown error:\n'
                                    '%(err)s\nLook at \'man backintime\' for further instructions')
                                    % {'host' : self.host, 'err' : err})

        i = 1
        inode1 = 'ABC'
        inode2 = 'DEF'
        for line in output_split:
            if line.startswith('cp'):
                try:
                    inode1 = output_split[i].split(' ')[0]
                    inode2 = output_split[i+1].split(' ')[0]
                except IndexError:
                    pass
                if not inode1 == inode2:
                    raise MountException( _('Remote host %s doesn\'t support hardlinks') % self.host)
            i += 1

    def random_id(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for x in range(size))
