#    Copyright (C) 2012-2022 Germar Reitze, Taylor Raack
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
import gettext
import subprocess
import re
import shutil
import tempfile
from datetime import datetime
from distutils.version import StrictVersion

import config
import password
import password_ipc
import tools
import sshtools
import logger
from mount import MountControl
from exceptions import MountException, EncodeValueError
_=gettext.gettext

class EncFS_mount(MountControl):
    """
    Mount encrypted paths with encfs.
    """
    def __init__(self, *args, **kwargs):
        #init MountControl
        super(EncFS_mount, self).__init__(*args, **kwargs)

        self.setattrKwargs('path', self.config.localEncfsPath(self.profile_id), **kwargs)
        self.setattrKwargs('reverse', False, **kwargs)
        self.setattrKwargs('config_path', None, **kwargs)
        self.setattrKwargs('password', None, store = False, **kwargs)
        self.setattrKwargs('hash_id_1', None, **kwargs)
        self.setattrKwargs('hash_id_2', None, **kwargs)

        self.setDefaultArgs()

        self.mountproc = 'encfs'
        self.log_command = '%s: %s' % (self.mode, self.path)
        self.symlink_subfolder = None

    def _mount(self):
        """
        mount the service
        """
        if self.password is None:
            self.password = self.config.password(self.parent, self.profile_id, self.mode)
        logger.debug('Provide password through temp FIFO', self)
        thread = password_ipc.TempPasswordThread(self.password)
        env = self.env()
        env['ASKPASS_TEMP'] = thread.temp_file
        with thread.starter():
            encfs = [self.mountproc, '--extpass=backintime-askpass']
            if self.reverse:
                encfs += ['--reverse']
            if not self.isConfigured():
                encfs += ['--standard']
            encfs += [self.path, self.currentMountpoint]
            logger.debug('Call mount command: %s'
                         %' '.join(encfs),
                         self)

            proc = subprocess.Popen(encfs, env = env,
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT,
                                    universal_newlines = True)
            output = proc.communicate()[0]
            self.backupConfig()
            if proc.returncode:
                raise MountException(_('Can\'t mount \'%(command)s\':\n\n%(error)s') \
                                        % {'command': ' '.join(encfs), 'error': output})

    def preMountCheck(self, first_run = False):
        """
        check what ever conditions must be given for the mount
        """
        self.checkFuse()
        if first_run:
            self.checkVersion()
        return True

    def env(self):
        """
        return environment with encfs configfile
        """
        env = os.environ.copy()
        cfg = self.configFile()
        if os.path.isfile(cfg):
            env['ENCFS6_CONFIG'] = cfg
        return env

    def configFile(self):
        """
        return encfs config file
        """
        f = '.encfs6.xml'
        if self.config_path is None:
            cfg = os.path.join(self.path, f)
        else:
            cfg = os.path.join(self.config_path, f)
        return cfg

    def isConfigured(self):
        """
        check if encfs config file exist. If not and if we are in settingsdialog
        ask for password confirmation. _mount will then create a new config
        """
        cfg = self.configFile()
        if os.path.isfile(cfg):
            logger.debug('Found encfs config in %s'
                         %cfg, self)
            return True
        else:
            logger.debug('No encfs config in %s'
                         %cfg, self)
            msg = _('Config for encrypted folder not found.')
            if not self.tmp_mount:
                raise MountException(msg)
            else:
                if not self.config.askQuestion(msg + _('\nCreate a new encrypted folder?')):
                    raise MountException(_('Cancel'))
                else:
                    pw = password.Password(self.config)
                    password_confirm = pw.passwordFromUser(self.parent, prompt = _('Please confirm password'))
                    if self.password == password_confirm:
                        return False
                    else:
                        raise MountException(_('Password doesn\'t match'))

    def checkVersion(self):
        """
        check encfs version.
        1.7.2 had a bug with --reverse that will create corrupt files
        """
        logger.debug('Check version', self)
        if self.reverse:
            proc = subprocess.Popen(['encfs', '--version'],
                                    stdout = subprocess.PIPE,
                                    stderr = subprocess.STDOUT,
                                    universal_newlines = True)
            output = proc.communicate()[0]
            m = re.search(r'(\d\.\d\.\d)', output)
            if m and StrictVersion(m.group(1)) <= StrictVersion('1.7.2'):
                logger.debug('Wrong encfs version %s' %m.group(1), self)
                raise MountException(_('encfs version 1.7.2 and before has a bug with option --reverse. Please update encfs'))

    def backupConfig(self):
        """
        create a backup of encfs config file into local config folder
        so in cases of the config file get deleted or corrupt user can restore
        it from there
        """
        cfg = self.configFile()
        if not os.path.isfile(cfg):
            logger.warning('No encfs config in %s. Skip backup of config file.' %cfg, self)
            return
        backup_folder = self.config.encfsconfigBackupFolder(self.profile_id)
        tools.makeDirs(backup_folder)
        old_backups = os.listdir(backup_folder)
        old_backups.sort(reverse = True)
        if len(old_backups):
            last_backup = os.path.join(backup_folder, old_backups[0])

            #don't create a new backup if config hasn't changed
            if tools.md5sum(cfg) == \
               tools.md5sum(last_backup):
                logger.debug('Encfs config did not change. Skip backup', self)
                return

        new_backup_file = '.'.join((os.path.basename(cfg), datetime.now().strftime('%Y%m%d%H%M')))
        new_backup = os.path.join(backup_folder, new_backup_file)
        logger.debug('Create backup of encfs config %s to %s'
                     %(cfg, new_backup), self)
        shutil.copy2(cfg, new_backup)


class EncFS_SSH(EncFS_mount):
    """
    Mount encrypted remote path with sshfs and encfs.
    Mount / with encfs --reverse.
    rsync will then sync the encrypted view on / to the remote path
    """

    def __init__(self,
                 cfg=None,
                 profile_id=None,
                 mode=None,
                 parent=None,
                 *args,
                 **kwargs):
        """
        """

        self.config = cfg

        if self.config is None:
            self.config = config.Config.instance()

        self.profile_id = profile_id

        if self.profile_id is None:
            self.profile_id = self.config.currentProfile()

        self.mode = mode

        if self.mode is None:
            self.mode = self.config.snapshotsMode(self.profile_id)

        self.parent = parent
        self.args = args
        self.kwargs = kwargs

        self.ssh = sshtools.SSH(
            *self.args, symlink=False, **self.splitKwargs('ssh'))

        self.rev_root = EncFS_mount(
            *self.args, symlink=False, **self.splitKwargs('encfs_reverse'))

        super(EncFS_SSH, self).__init__(
            *self.args, **self.splitKwargs('encfs'))

    def mount(self, *args, **kwargs):
        """
        call mount for sshfs, encfs --reverse and encfs
        register 'encfsctl encode' in config.ENCODE
        """
        logger.debug('Mount sshfs', self)
        self.ssh.mount(*args, **kwargs)
        #mount fsroot with encfs --reverse first.
        #If the config does not exist already this will make sure
        #the new created config works with --reverse
        if not os.path.isfile(self.configFile()):
            #encfs >= 1.8.0 changed behavior when ENCFS6_CONFIG environ variable
            #file does not exist. It will not create a new one anymore but just fail.
            #As encfs would create the config in /.encfs6.xml (which will most likly fail)
            #we need to mount a temp folder with reverse first and copy the config when done.
            logger.debug('Mount temp folder with encfs --reverse to create a new encfs config', self)
            with tempfile.TemporaryDirectory() as src:
                tmp_kwargs = self.splitKwargs('encfs_reverse')
                tmp_kwargs['path'] = src
                tmp_kwargs['config_path'] = src
                tmp_mount = EncFS_mount(*self.args, symlink = False, **tmp_kwargs)
                tmp_mount.mount(*args, **kwargs)
                tmp_mount.umount()
                cfg = tmp_mount.configFile()
                if os.path.isfile(cfg):
                    logger.debug('Copy new encfs config %s to its original place %s' %(cfg, self.ssh.currentMountpoint), self)
                    shutil.copy2(cfg, self.ssh.currentMountpoint)
                else:
                    logger.error('New encfs config %s not found' %cfg, self)
        logger.debug('Mount local filesystem root with encfs --reverse', self)
        self.rev_root.mount(*args, **kwargs)

        logger.debug('Mount encfs', self)
        kwargs['check'] = False
        ret = super(EncFS_SSH, self).mount(*args, **kwargs)
        self.config.ENCODE = Encode(self)
        return ret

    def umount(self, *args, **kwargs):
        """
        close 'encfsctl encode' process and set config.ENCODE back to the dummy class.
        call umount for encfs, encfs --reverse and sshfs
        """
        self.config.ENCODE.close()
        self.config.ENCODE = Bounce()
        logger.debug('Unmount encfs', self)
        super(EncFS_SSH, self).umount(*args, **kwargs)
        logger.debug('Unmount local filesystem root mount encfs --reverse', self)
        self.rev_root.umount(*args, **kwargs)
        logger.debug('Unmount sshfs', self)
        self.ssh.umount(*args, **kwargs)

    def preMountCheck(self, *args, **kwargs):
        """
        call preMountCheck for sshfs, encfs --reverse and encfs
        """
        if self.ssh.preMountCheck(*args, **kwargs) and \
           self.rev_root.preMountCheck(*args, **kwargs) and \
           super(EncFS_SSH, self).preMountCheck(*args, **kwargs):
                return True

    def splitKwargs(self, mode):
        """
        split all given arguments for the desired mount class
        """
        d = self.kwargs.copy()
        d['cfg']        = self.config
        d['profile_id'] = self.profile_id
        d['mode']       = self.mode
        d['parent']     = self.parent
        if mode == 'ssh':
            if 'path' in d:
                d.pop('path')
            if 'ssh_path' in d:
                d['path'] = d.pop('ssh_path')
            if 'ssh_password' in d:
                d['password'] = d.pop('ssh_password')
            else:
                d['password'] = self.config.password(parent = self.parent, profile_id = self.profile_id, mode = self.mode)
            if 'hash_id' in d:
                d.pop('hash_id')
            if 'hash_id_2' in d:
                d['hash_id'] = d['hash_id_2']
            return d

        elif mode == 'encfs':
            d['path'] = self.ssh.currentMountpoint
            d['hash_id_1'] = self.rev_root.hash_id
            d['hash_id_2'] = self.ssh.hash_id
            if 'encfs_password' in d:
                d['password'] = d.pop('encfs_password')
            else:
                d['password'] = self.config.password(parent = self.parent, profile_id = self.profile_id, mode = self.mode, pw_id = 2)
            return d

        elif mode == 'encfs_reverse':
            d['reverse'] = True
            d['path'] = '/'
            d['config_path'] = self.ssh.currentMountpoint
            if 'encfs_password' in d:
                d['password'] = d.pop('encfs_password')
            else:
                d['password'] = self.config.password(parent = self.parent, profile_id = self.profile_id, mode = self.mode, pw_id = 2)
            if 'hash_id' in d:
                d.pop('hash_id')
            if 'hash_id_1' in d:
                d['hash_id'] = d['hash_id_1']
            return d

class Encode(object):
    """
    encode path with encfsctl.
    ENCFS_SSH will replace config.ENCODE whit this
    """
    def __init__(self, encfs):
        self.encfs = encfs
        self.password = self.encfs.password
        self.chroot = self.encfs.rev_root.currentMountpoint
        if not self.chroot[-1] == os.sep:
            self.chroot += os.sep
        self.remote_path = self.encfs.ssh.path
        if not self.remote_path[-1] == os.sep:
            self.remote_path += os.sep

        #precompile some regular expressions
        self.re_asterisk = re.compile(r'\*')
        self.re_separate_asterisk = re.compile(r'(.*?)(\*+)(.*)')

    def __del__(self):
        self.close()

    def startProcess(self):
        """
        start 'encfsctl encode' process in pipe mode.
        """
        thread = password_ipc.TempPasswordThread(self.password)
        env = self.encfs.env()
        env['ASKPASS_TEMP'] = thread.temp_file
        with thread.starter():
            logger.debug('start \'encfsctl encode\' process', self)
            encfsctl = ['encfsctl', 'encode', '--extpass=backintime-askpass', '/']
            logger.debug('Call command: %s'
                         %' '.join(encfsctl),
                         self)
            self.p = subprocess.Popen(encfsctl, env = env, bufsize = 0,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    universal_newlines = True)

    def path(self, path):
        """
        write plain path to encfsctl stdin and read encrypted path from stdout
        """
        if not 'p' in vars(self):
            self.startProcess()
        if not self.p.returncode is None:
            logger.warning('\'encfsctl encode\' process terminated. Restarting.', self)
            del self.p
            self.startProcess()
        self.p.stdin.write(path + '\n')
        ret = self.p.stdout.readline().strip('\n')
        if not len(ret) and len(path):
            logger.debug('Failed to encode %s. Got empty string'
                         %path, self)
            raise EncodeValueError()
        return ret

    def exclude(self, path):
        """
        encrypt paths for snapshots.takeSnapshot exclude list.
        After encoding the path a wildcard would not match anymore
        so all paths with wildcards are ignored. Only single and double asterisk
        that will match a full file or folder name will work.
        """
        if tools.patternHasNotEncryptableWildcard(path):
            return None

        enc = ''
        m = self.re_asterisk.search(path)
        if not m is None:
            path_ = path[:]
            while True:
                #search for foo/*, foo/*/bar, */bar or **/bar
                #but not foo* or foo/*bar
                m = self.re_separate_asterisk.search(path_)
                if m is None:
                    return None
                if m.group(1):
                    if not m.group(1).endswith(os.sep):
                        return None
                    enc = os.path.join(enc, self.path(m.group(1)))
                enc = os.path.join(enc, m.group(2))
                if m.group(3):
                    if not m.group(3).startswith(os.sep):
                        return None
                    m1 = self.re_asterisk.search(m.group(3))
                    if m1 is None:
                        enc = os.path.join(enc, self.path(m.group(3)))
                        break
                    else:
                        path_ = m.group(3)
                        continue
                else:
                    break
        else:
            enc = self.path(path)
        if os.path.isabs(path):
            return os.path.join(os.sep, enc)
        return enc

    def include(self, path):
        """
        encrypt paths for snapshots.takeSnapshot include list.
        """
        return os.path.join(os.sep, self.path(path))

    def remote(self, path):
        """
        encode the path on remote host starting from backintime/host/user/...
        """
        enc_path = self.path(path[len(self.remote_path):])
        return os.path.join(self.remote_path, enc_path)

    def close(self):
        """
        stop encfsctl process
        """
        if 'p' in vars(self) and self.p.returncode is None:
            logger.debug('stop \'encfsctl encode\' process', self)
            self.p.communicate()

class Bounce(object):
    """
    Dummy class that will simply return all input.
    This is the standard for config.ENCODE
    """
    def __init__(self):
        self.chroot = os.sep

    def path(self, path):
        return path

    def exclude(self, path):
        return path

    def include(self, path):
        return path

    def remote(self, path):
        return path

    def close(self):
        pass

class Decode(object):
    """
    decode path with encfsctl.
    """
    def __init__(self, cfg, string = True):
        self.config = cfg
        self.mode = cfg.snapshotsMode()
        if self.mode == 'local_encfs':
            self.password = cfg.password(pw_id = 1)
        elif self.mode == 'ssh_encfs':
            self.password = cfg.password(pw_id = 2)
        self.encfs = cfg.SNAPSHOT_MODES[self.mode][0](cfg)
        self.remote_path = cfg.sshSnapshotsPath()
        if not self.remote_path:
            self.remote_path = './'
        if not self.remote_path[-1] == os.sep:
            self.remote_path += os.sep

        #german translation changed from Snapshot to Schnappschuss.
        #catch both variants otherwise old logs wouldn't get decoded.
        takeSnapshot = _('Take snapshot').replace('Schnappschuss', '(?:Schnappschuss|Snapshot)')

        #precompile some regular expressions
        host, port, user, path, cipher = cfg.sshHostUserPortPathCipher()
        #replace: --exclude"<crypted_path>" or --include"<crypted_path>"
        self.re_include_exclude = re.compile(r'(--(?:ex|in)clude=")(.*?)(")')

        #replace: 'USER@HOST:"PATH<crypted_path>"'
        self.re_remote_path =     re.compile(r'(\'%s@%s:"%s)(.*?)("\')' %(user, host, path))

        #replace: --link-dest="../../<crypted_path>"
        self.re_link_dest =       re.compile(r'(--link-dest="\.\./\.\./)(.*?)(")')

        #search for: [C] <f+++++++++ <crypted_path>
        self.re_change = re.compile(r'(^\[C\] .{11} )(.*)')

        #search for: [I] Take snapshot (rsync: BACKINTIME: <f+++++++++ <crypted_path>)
        #            [I] Take snapshot (rsync: deleting <crypted_path>)
        #            [I] Take snapshot (rsync: rsync: readlink_stat("...mountpoint/<crypted_path>")
        #            [I] Take snapshot (rsync: rsync: send_files failed to open "...mountpoint/<crypted_path>": Permission denied (13))
        #            [I] Take snapshot (rsync: file has vanished: "...mountpoint/<crypted_path>")
        #            [I] Take snapshot (rsync: <crypted_path>)
        pattern = []
        pattern.append(r' BACKINTIME: .{11} ')
        pattern.append(r' deleting ')
        pattern.append(r' rsync: readlink_stat\(".*?mountpoint/')
        pattern.append(r' rsync: send_files failed to open ".*?mountpoint/')
        pattern.append(r' file has vanished: ".*?mountpoint/')
        pattern.append(r' ')
        self.re_info = re.compile(r'(^(?:\[I\] )?%s \(rsync:(?:%s))(.*?)(\).*|".*)' % (takeSnapshot, '|'.join(pattern)))

        #search for: [E] Error: rsync readlink_stat("...mountpoint/<crypted_path>")
        #            [E] Error: rsync: send_files failed to open "...mountpoint/<crypted_path>": Permission denied (13)
        #            [E] Error: rsync: recv_generator: failed to stat "<remote_path>/<crypted_path>": File name too long (36)
        #            [E] Error: rsync: recv_generator: mkdir "<remote_path>/<crypted_path>": File name too long (36)
        pattern = []
        pattern.append(r' rsync: readlink_stat\(".*?mountpoint/')
        pattern.append(r' rsync: send_files failed to open ".*?mountpoint/')
        if self.remote_path == './':
            pattern.append(r' rsync: recv_generator: failed to stat "/home/[^/]*/')
            pattern.append(r' rsync: recv_generator: mkdir "/home/[^/]*/')
        else:
            pattern.append(r' rsync: recv_generator: failed to stat ".*?{}'.format(self.remote_path))
            pattern.append(r' rsync: recv_generator: mkdir ".*?{}'.format(self.remote_path))
        pattern.append(r' rsync: .*?".*?mountpoint/')
        self.re_error = re.compile(r'(^(?:\[E\] )?Error:(?:%s))(.*?)(".*)' % '|'.join(pattern))

        #search for: [I] ssh USER@HOST cp -aRl "PATH<crypted_path>"* "PATH<crypted_path>"
        self.re_info_cp= re.compile(r'(^\[I\] .*? cp -aRl "%s/)(.*?)("\* "%s/)(.*?)(")' % (path, path))

        #search for all chars except *
        self.re_all_except_asterisk = re.compile(r'[^\*]+')

        #search for: <crypted_path> -> <crypted_path>
        self.re_all_except_arrow = re.compile(r'(.*?)((?: [-=]> )+)(.*)')

        #skip: [I] Take snapshot (rsync: sending incremental file list)
        #      [I] Take snapshot (rsync: building file list ... done)
        #      [I] Take snapshot (rsync: sent 26569703 bytes  received 239616 bytes  85244.26 bytes/sec)
        #      [I] Take snapshot (rsync: total size is 9130263449  speedup is 340.56)
        #      [I] Take snapshot (rsync: rsync error: some files/attrs were not transferred (see previous errors) (code 23) at main.c(1070) [sender=3.0.9])
        #      [I] Take snapshot (rsync: rsync warning: some files vanished before they could be transferred (code 24) at main.c(1070) [sender=3.0.9])
        pattern = []
        pattern.append(r'sending incremental file list')
        pattern.append(r'building file list ... done')
        pattern.append(r'sent .*? received')
        pattern.append(r'total size is .*? speedup is')
        pattern.append(r'rsync error: some files/attrs were not transferred')
        pattern.append(r'rsync warning: some files vanished before they could be transferred')
        self.re_skip = re.compile(r'^(?:\[I\] )?%s \(rsync: (%s)' % (takeSnapshot, '|'.join(pattern)))

        self.string = string
        if string:
            self.newline = '\n'
        else:
            self.newline = b'\n'

    def __del__(self):
        self.close()

    def startProcess(self):
        """
        start 'encfsctl decode' process in pipe mode.
        """
        thread = password_ipc.TempPasswordThread(self.password)
        env = os.environ.copy()
        env['ASKPASS_TEMP'] = thread.temp_file
        with thread.starter():
            logger.debug('start \'encfsctl decode\' process', self)
            encfsctl = ['encfsctl', 'decode', '--extpass=backintime-askpass', self.encfs.path]
            logger.debug('Call command: %s'
                         %' '.join(encfsctl),
                         self)
            self.p = subprocess.Popen(encfsctl, env = env,
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      universal_newlines = self.string,   #return string (if True) or bytes
                                      bufsize = 0)

    def path(self, path):
        """
        write crypted path to encfsctl stdin and read plain path from stdout
        if stdout is empty (most likly because there was an error) return crypt path
        """
        if self.string:
            assert isinstance(path, str), 'path is not str type: %s' % path
        else:
            assert isinstance(path, bytes), 'path is not bytes type: %s' % path
        if not 'p' in vars(self):
            self.startProcess()
        if not self.p.returncode is None:
            logger.warning('\'encfsctl decode\' process terminated. Restarting.', self)
            del self.p
            self.startProcess()
        self.p.stdin.write(path + self.newline)
        ret = self.p.stdout.readline()
        ret = ret.strip(self.newline)
        if ret:
            return ret
        return path

    #TODO: rename this, 'list' is corrupting sphinx doc
    def list(self, list_):
        """
        decode a list of paths
        """
        output = []
        for path in list_:
            output.append(self.path(path))
        return output

    def log(self, line):
        """
        decode paths in takesnapshot.log
        """
        #rsync cmd
        if line.startswith('[I] rsync') or line.startswith('[I] nocache rsync'):
            line = self.re_include_exclude.sub(self.replace, line)
            line = self.re_remote_path.sub(self.replace, line)
            line = self.re_link_dest.sub(self.replace, line)
            return line
        #[C] Change lines
        m = self.re_change.match(line)
        if not m is None:
            return m.group(1) + self.pathWithArrow(m.group(2))
        #[I] Information lines
        m = self.re_skip.match(line)
        if not m is None:
            return line
        m = self.re_info.match(line)
        if not m is None:
            return m.group(1) + self.pathWithArrow(m.group(2)) + m.group(3)
        #[E] Error lines
        m = self.re_error.match(line)
        if not m is None:
            return m.group(1) + self.path(m.group(2)) + m.group(3)
        #cp cmd
        m = self.re_info_cp.match(line)
        if not m is None:
            return m.group(1) + self.path(m.group(2)) + m.group(3) + self.path(m.group(4)) + m.group(5)
        return line

    def replace(self, m):
        """
        return decoded string for re.sub
        """
        decrypt = self.re_all_except_asterisk.sub(self.pathMatch, m.group(2))
        if os.path.isabs(m.group(2)):
            decrypt = os.path.join(os.sep, decrypt)
        return m.group(1) + decrypt + m.group(3)

    def pathMatch(self, m):
        """
        return decoded path of a match object
        """
        return self.path(m.group(0))

    def pathWithArrow(self, path):
        """
        rsync print symlinks like 'dest -> src'. This will decode both and also normal paths
        """
        m = self.re_all_except_arrow.match(path)
        if not m is None:
            return self.path(m.group(1)) + m.group(2) + self.path(m.group(3))
        else:
            return self.path(path)

    def remote(self, path):
        """
        decode the path on remote host starting from backintime/host/user/...
        """
        assert isinstance(path, bytes), 'path is not bytes type: %s' % path

        remote_path = self.remote_path.encode()
        dec_path = self.path(path[len(remote_path):])
        return os.path.join(remote_path, dec_path)

    def close(self):
        """
        stop encfsctl process
        """
        if 'p' in vars(self) and self.p.returncode is None:
            logger.debug('stop \'encfsctl decode\' process', self)
            self.p.communicate()
