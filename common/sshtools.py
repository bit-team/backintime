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
import subprocess
import string
import random
import tempfile
import socket
import re
import atexit
import signal
from pathlib import Path
from time import sleep
import logger
import tools
import password
import password_ipc
from mount import MountControl
from exceptions import MountException, NoPubKeyLogin, KnownHost
import bcolors
import version


class SSH(MountControl):
    """
    This is a backend for the mount API :py:class:`mount.MountControl`.
    This will mount the remote path with ``sshfs``, prepare the remote path and
    check that everything is set up correctly for `Back In Time` to run
    snapshots through SSH.

    This class will only mount the remote path. The real takeSnapshot process
    will use rsync over ssh. Other commands run remote over ssh.

    Args:
        cfg (config.Config):    current config
                                (handled by inherited
                                :py:class:`mount.MountControl`)
        user (str):             User name on remote host
        host (str):             Name or IP Address of remote host
        port (int):             Port used by SSHd on remote host
        path (str):             remote path where snapshots are stored. Can be
                                either relative from remote users homedir or
                                an absolute path
        cipher (str):           Cipher used to encrypt the network transfer
        private_key_file (str): Private key which is able to log on with
                                Public/Private Key-Method on remote host
        nice (bool):            use ``nice -n 19`` to run commands with
                                low CPU priority on remote host
        ionice (bool):          use ``ionice -c2 -n7`` to run commands with
                                low IO priority on remote host
        nocache (bool):         use ``nocache`` to deactivate RAM caching of
                                files on remote host
        password (str):         password to unlock the private key
        profile_id (str):       profile ID that should be used
                                (handled by inherited
                                :py:class:`mount.MountControl`)
        hash_id (str):          crc32 hash used to identify
                                identical mountpoints
                                (handled by inherited
                                :py:class:`mount.MountControl`)
        tmp_mount (bool):       if ``True`` mount to a temporary destination
                                (handled by inherited
                                :py:class:`mount.MountControl`)
        parent (QWidget):       parent widget for QDialogs or ``None`` if there
                                is no parent (handled by
                                inherited :py:class:`mount.MountControl`)
        symlink (bool):         if ``True`` set symlink to mountpoint
                                (handled by
                                inherited :py:class:`mount.MountControl`)
        mode (str):             one of ``local``, ``local_encfs``, ``ssh`` or
                                ``ssh_encfs`` (handled by inherited
                                :py:class:`mount.MountControl`)
        hash_collision (int):   global value used to prevent hash collisions
                                on mountpoints (handled by inherited
                                :py:class:`mount.MountControl`)

    Note:
        All Arguments are optional. Default values will be fetched from
        :py:class:`config.Config`. But after changing Settings we need to test
        the new values **before** storing them into :py:class:`config.Config`.
        This is why all values will be added as arguments.
    """

    def __init__(self, *args, **kwargs):

        # init MountControl
        super(SSH, self).__init__(*args, **kwargs)

        # Workaround for linters
        self.user = None
        self.host = None
        self.port = None
        self.cipher = None
        self.proxy_user = None
        self.proxy_host = None
        self.proxy_port = None
        self.nice = None
        self.ionice = None
        self.nocache = None
        self.private_key_file = None
        self.password = None

        self.setattrKwargs(
            'user', self.config.sshUser(self.profile_id), **kwargs)
        self.setattrKwargs(
            'host', self.config.sshHost(self.profile_id), **kwargs)
        self.setattrKwargs(
            'port', self.config.sshPort(self.profile_id), **kwargs)
        self.setattrKwargs(
            'path', self.config.sshSnapshotsPath(self.profile_id), **kwargs)
        self.setattrKwargs(
            'cipher', self.config.sshCipher(self.profile_id), **kwargs)
        self.setattrKwargs(
            'private_key_file',
            self.config.sshPrivateKeyFile(self.profile_id), **kwargs)

        self.setattrKwargs(
            'proxy_user', self.config.sshProxyUser(self.profile_id), **kwargs)
        self.setattrKwargs(
            'proxy_host', self.config.sshProxyHost(self.profile_id), **kwargs)
        self.setattrKwargs(
            'proxy_port', self.config.sshProxyPort(self.profile_id), **kwargs)

        self.setattrKwargs(
            'nice',
            self.config.niceOnRemote(self.profile_id), store=False, **kwargs)
        self.setattrKwargs(
            'ionice',
            self.config.ioniceOnRemote(self.profile_id), store=False, **kwargs)
        self.setattrKwargs(
            'nocache',
            self.config.nocacheOnRemote(self.profile_id),
            store=False,
            **kwargs)
        self.setattrKwargs('password', None, store=False, **kwargs)

        if not self.path:
            self.path = './'

        self.setDefaultArgs()

        # config strings used in ssh-calls
        self.user_host_path \
            = '%s@%s:%s' % (self.user,
                            tools.escapeIPv6Address(self.host),
                            self.path)
        self.user_host = '%s@%s' % (self.user, self.host)

        self.mountproc = 'sshfs'
        self.symlink_subfolder = None
        self.log_command = '%s: %s' % (self.mode, self.user_host_path)

        self.private_key_fingerprint = sshKeyFingerprint(self.private_key_file)

        if not self.private_key_fingerprint:

            logger.warning('Couldn\'t get fingerprint for private '
                           'key %(path)s. '
                           'Most likely because the public key %(path)s.pub '
                           'wasn\'t found. Using fallback to private keys '
                           'path instead. But this can make troubles with '
                           'passphrase-less keys.'
                           % {'path': self.private_key_file},
                           self)
            self.private_key_fingerprint = self.private_key_file

        self.unlockSshAgent()

    def _mount(self):
        """
        Backend mount method. This will call ``sshfs`` to mount the remote
        path.

        Raises:
            exceptions.MountException:  if mount wasn't successful
        """

        sshfs = [self.mountproc]
        sshfs += self.config.sshDefaultArgs(self.profile_id)
        sshfs += ['-p', str(self.port)]

        if not self.cipher == 'default':
            sshfs.extend(['-o', 'Ciphers=%s' % self.cipher])

        sshfs.extend(['-o', 'idmap=user',
                      '-o', 'cache_dir_timeout=2',
                      '-o', 'cache_stat_timeout=2'])

        sshfs.extend([self.user_host_path, self.currentMountpoint])

        # bugfix: sshfs doesn't mount if locale in LC_ALL is not available on
        # remote host
        # LANG or other environment variable are no problem.
        env = os.environ.copy()

        if 'LC_ALL' in list(env.keys()):
            env['LC_ALL'] = 'C'

        logger.debug('Call mount command: %s'
                     % ' '.join(sshfs),
                     self)

        # SSH Proxy (aka Jump host)
        if self.proxy_host:
            sshfs.extend([
                '-o',
                'ssh_command=ssh -J '
                f'{self.proxy_user}@{self.proxy_host}:{self.proxy_port}'
            ])

        logger.debug(f'Execute SSHFS command {sshfs}.')

        proc = subprocess.Popen(sshfs,
                                env=env,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)

        err = proc.communicate()[1]

        if proc.returncode == 0:
            return

        raise MountException(
            "{}\n\n{}".format(
                _('Unable to mount {sshfs}').format(sshfs=" ".join(sshfs)),
                err
            )
        )

    def preMountCheck(self, first_run=False):
        """
        Check that everything is prepared and ready for successfully mount the
        remote path. Default is to run a light version of checks which will
        only make sure the remote host is online, ``sshfs`` is installed and
        the remote folder is available.

        After changing settings this should be run with ``first_run = True``
        to run a full check with all tests.

        Args:
            first_run (bool): Run a full test with all checks.

        Raises:
            exceptions.MountException: If one test failed an we can not mount
                the remote path.
        """

        # Most of the called methods will raise an exception if something is
        # wrong.

        # try to open SSH socket
        self.checkPingHost()

        # sshfs (self.mountproc) installed?
        self.checkFuse()

        if first_run:
            self.unlockSshAgent(force=True)
            self.checkKnownHosts()

        self.checkLogin()

        if first_run:
            self.checkCipher()

        self.checkRemoteFolder()

        if first_run:
            self.checkRemoteCommands()

        return True

    def startSshAgent(self):
        """
        Start a new ``ssh-agent`` if it is not already running.

        Raises:
            exceptions.MountException:  if starting ``ssh-agent`` failed
        """

        SOCK = 'SSH_AUTH_SOCK'
        PID = 'SSH_AGENT_PID'

        if os.getenv(SOCK, '') and os.getenv(PID, ''):
            logger.debug(
                'ssh-agent already running. Skip starting a new one.', self)
            return

        sshAgent = tools.which('ssh-agent')

        if not sshAgent:
            raise MountException(
                _('ssh-agent not found. Please ensure it is installed.'))

        if isinstance(sshAgent, str):
            sshAgent = [sshAgent, ]

        sa = subprocess.Popen(sshAgent,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True)
        out, err = sa.communicate()

        if sa.returncode:
            raise MountException(
                'Failed to start ssh-agent: [{}] {}'
                .format(sa.returncode, err))

        m = re.match(r'.*{}(?:=|\s)([^;]+);.*{}(?:=|\s)(\d+);'
                     .format(SOCK, PID),
                     out,
                     re.DOTALL | re.MULTILINE)
        if m:
            logger.debug('ssh-agent started successful: {}={} | {}={}'
                         .format(SOCK, m.group(1), PID, m.group(2)), self)
            os.environ[SOCK] = m.group(1)
            os.environ[PID] = m.group(2)

            atexit.register(os.kill, int(m.group(2)), signal.SIGKILL)

        else:
            raise MountException(
                'No matching output from ssh-agent: {} | {}'.format(out, err))

    def unlockSshAgent(self, force=False):
        """
        Unlock the private key in ``ssh-agent`` which will provide it for
        all other commands. The password to unlock the key will be provided
        by ``backintime-askpass``.

        Args:
            force (bool): Force to unlock the key by removing it first and add
                it again to make sure, the given values are correct.

        Raises:
            exceptions.MountException: If unlock failed.
        """

        self.startSshAgent()

        env = os.environ.copy()
        env['SSH_ASKPASS'] = 'backintime-askpass'
        env['ASKPASS_PROFILE_ID'] = self.profile_id
        env['ASKPASS_MODE'] = self.mode

        if force:
            # remove private key first so we can check if the given
            # password is valid
            logger.debug(
                'Remove private key %s from ssh agent' % self.private_key_file,
                self)

            proc = subprocess.Popen(['ssh-add', '-d', self.private_key_file],
                                    stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                    universal_newlines=True)
            proc.communicate()

        proc = subprocess.Popen(['ssh-add', '-l'],
                                stdout=subprocess.PIPE,
                                universal_newlines=True)

        output = proc.communicate()[0]

        if force or not output.find(self.private_key_fingerprint) >= 0:

            logger.debug(
                'Add private key %s to ssh agent' % self.private_key_file,
                self)

            password_available = any([
                self.config.passwordSave(self.profile_id),
                self.config.passwordUseCache(self.profile_id),
                self.password is not None
            ])

            logger.debug('Password available: %s' % password_available, self)

            if not password_available and not tools.checkXServer():
                # we need to unlink stdin from ssh-add in order to make it
                # use our own backintime-askpass.
                # But because of this we can NOT use getpass inside
                # backintime-askpass if password is not saved and there is no
                # x-server.
                # So, let's just keep ssh-add asking for the password in
                # that case.

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

                # We need to validate the ssh key password which
                # `backintime-askpass` will provide before calling
                # ssh-add below. See Issue #1852.

                # Validate cached SSH key password:
                proc = subprocess.run(
                        ['ssh-keygen', '-y', '-f', self.private_key_file],
                        capture_output=True,
                        # Ensure ssh-keygen uses backintime-askpass
                        env=env | {'SSH_ASKPASS_REQUIRE': 'prefer'}
                )

                # if backintime-askpass supplied an invalid cached password
                if proc.returncode > 0:
                    pw = password.Password()

                    # pw_id = 1 corresponds to the SSH password
                    # (as opposed to the encryption password)
                    # See qt/settingsdialog.py:SettingsDialog.updateProfile()
                    pw.password(
                        None,
                        self.profile_id,
                        self.mode,
                        pw_id=1,
                        refresh=True,
                    )

                proc = subprocess.Popen(['ssh-add', self.private_key_file],
                                        stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        env=env,
                                        preexec_fn=os.setsid,
                                        universal_newlines=True)

                output, error = proc.communicate()

                if proc.returncode:
                    logger.error('Failed to unlock SSH private key %s: %s'
                                 % (self.private_key_file, error),
                                 self)

                if self.password:
                    thread.stop()

            proc = subprocess.Popen(['ssh-add', '-l'],
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)

            output = proc.communicate()[0]

            if not output.find(self.private_key_fingerprint) >= 0:
                logger.debug(
                    'Was not able to unlock private key %s' %
                    self.private_key_file, self)

                raise MountException(
                    _('Could not unlock ssh private key. Wrong password '
                      'or password not available for cron.'))

        else:
            logger.debug('Private key %s is already unlocked in ssh agent'
                         % self.private_key_file, self)

    def checkLogin(self):
        """Try to login to remote host with public/private-key-method
        (passwordless).

        Raises:
            exceptions.NoPubKeyLogin: If login failed.
        """

        logger.debug('Check login', self)

        # Custom SSH arguments
        custom_ssh_args = [
            '-o',
            'PreferredAuthentications=publickey',
            '-p', str(self.port),
            self.user_host
        ]

        # Create SSH command
        ssh = self.config.sshCommand(cmd=['exit'],
                                     custom_args=custom_ssh_args,
                                     port=False,
                                     user_host=False,
                                     nice=False,
                                     ionice=False,
                                     profile_id=self.profile_id)
        proc = subprocess.Popen(ssh,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)

        err = proc.communicate()[1]

        if proc.returncode:
            raise NoPubKeyLogin(
                'Password-less authentication for %(user)s@%(host)s '
                'failed. Look at \'man backintime\' for further '
                'instructions.' % {
                    'user': self.user,
                    'host': self.host}
                + '\n\n' + err)

    def checkCipher(self):
        """Try to login to remote host with the chosen cipher. This should make
        sure both `localhost` and the remote host support the chosen cipher.

        Raises:
            exceptions.MountException: If login with the cipher failed.
        """

        if not self.cipher == 'default':

            logger.debug('Check cipher', self)

            ssh = self.config.sshCommand(cmd=['exit'],
                                         custom_args=[
                                              '-o',
                                              'Ciphers=%s' % self.cipher,
                                              '-p',
                                              str(self.port),
                                              self.user_host
                                         ],
                                         port=False,
                                         cipher=False,
                                         user_host=False,
                                         nice=False,
                                         ionice=False,
                                         profile_id=self.profile_id)

            proc = subprocess.Popen(ssh,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True)

            err = proc.communicate()[1]

            if proc.returncode:

                logger.debug(
                    'Ciper %s is not supported' %
                    self.config.SSH_CIPHERS[self.cipher], self)

                msg = _('Cipher {cipher} failed for {host}.').format(
                    cipher=self.config.SSH_CIPHERS[self.cipher],
                    host=self.host)

                raise MountException(f'{msg}:\n{err}')

    def benchmarkCipher(self, size=40):
        """
        Rudimental benchmark to compare transfer speed of all available
        ciphers.

        Args:
            size (int):     size of the testfile in MiB
        """

        temp = tempfile.mkstemp()[1]

        print('create random data file')

        subprocess.call([
            'dd',
            'if=/dev/urandom',
            'of=%s' % temp,
            'bs=1M',
            'count=%s' % size
        ])

        keys = list(self.config.SSH_CIPHERS.keys())
        keys.sort()

        for cipher in keys:

            if cipher == 'default':
                continue

            print('%s%s:%s' % (bcolors.BOLD, cipher, bcolors.ENDC))

            for _ in range(2):
                # scp uses -P instead of -p for port
                subprocess.call([
                    'scp',
                    '-P',
                    str(self.port),
                    '-c',
                    cipher,
                    temp,
                    self.user_host_path
                ])

        ssh = self.config.sshCommand(
            cmd=['rm', os.path.join(self.path, os.path.basename(temp))],
            custom_args=['-p', str(self.port), self.user_host],
            port=False,
            cipher=False,
            user_host=False,
            nice=False,
            ionice=False,
            profile_id=self.profile_id)

        subprocess.call(ssh)
        os.remove(temp)

    def checkKnownHosts(self):
        """Check if the remote host is in current users ``known_hosts`` file.

        Raises:
            exceptions.KnownHost: If the remote host wasn't found
                in ``known_hosts`` file.
        """

        logger.debug('Check known hosts file', self)

        for host in (self.host, '[%s]:%s' % (self.host, self.port)):

            proc = subprocess.Popen(['ssh-keygen', '-F', host],
                                    stdout=subprocess.PIPE,
                                    universal_newlines=True)

            # subprocess.check_output doesn't exist
            # in Python 2.6 (Debian squeeze default)
            output = proc.communicate()[0]

            if output.find('Host %s found' % host) >= 0:
                logger.debug(
                    'Host %s was found in known hosts file' % host, self)
                return True

        logger.debug('Host %s is not in known hosts file' % self.host, self)

        raise KnownHost('%s not found in ssh_known_hosts.' % self.host)

    def checkRemoteFolder(self):
        """
        Check the remote path. If the remote path doesn't exist this will
        create it. If it already exist this will check, that it is a folder
        and has correct permissions.

        Raises:
            exceptions.MountException:  if remote path couldn't be created or
                                        doesn't have correct permissions.
        """

        logger.debug('Check remote directory', self)

        cmd = 'd=0;'
        # path doesn't exist. set d=1 to indicate
        cmd += 'test -e "%s" || d=1;' % self.path
        # create path, get errorcode from mkdir
        cmd += 'test $d -eq 1 && mkdir "%s"; err=$?;' % self.path
        # return errorcode from mkdir
        cmd += 'test $d -eq 1 && exit $err;'
        # path is no directory
        cmd += 'test -d "%s" || exit 11;' % self.path
        # path is not writable
        cmd += 'test -w "%s" || exit 12;' % self.path
        # path is not executable
        cmd += 'test -x "%s" || exit 13;' % self.path
        # everything is fine
        cmd += 'exit 20'

        ssh = self.config.sshCommand(
            cmd=[cmd],
            custom_args=['-p', str(self.port), self.user_host],
            port=False,
            user_host=False,
            nice=False,
            ionice=False,
            profile_id=self.profile_id)

        logger.debug('Call command: %s' % ' '.join(ssh), self)

        proc = subprocess.Popen(ssh,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)

        proc.communicate()

        if proc.returncode:

            logger.debug('Command returncode: %s' % proc.returncode, self)

            if proc.returncode == 20:
                # clean exit
                pass

            elif proc.returncode == 11:
                raise MountException('{}:\n{}'.format(
                    _('Remote path exists but is not a directory.'),
                    self.path))

            elif proc.returncode == 12:
                raise MountException('{}:\n{}'.format(
                    _('Remote path is not writable.'),
                    self.path))

            elif proc.returncode == 13:
                raise MountException('{}:\n{}'.format(
                    _('Remote path is not executable.'),
                    self.path))

            else:
                raise MountException('{}:\n{}'.format(
                    _("Couldn't create remote path."),
                    self.path))
        else:

            # returncode is 0
            logger.info(f'Create remote path {self.path}', self)

    def checkPingHost(self):
        """
        Check if the remote host is online. Other than methods name may let
        suppose this does not use Ping (``ICMP``) but try to open a connection
        to the configured port on the remote host. In this way it will even
        work on remote hosts which have ``ICMP`` disabled.

        If connection failed it will retry five times before failing.

        Raises:
            exceptions.MountException: If connection failed most probably
                because remote host is offline.
        """

        if not self.config.sshCheckPingHost(self.profile_id):
            return

        if self.proxy_host:
            ping_host = self.proxy_host
            ping_port = self.proxy_port
        else:
            ping_host = self.host
            ping_port = self.port

        logger.debug(f'Check ping host "{ping_host}:{ping_port}"', self)
        versionString = 'SSH-2.0-backintime_{}\r\n'.format(
            version.__version__).encode()

        count = 0

        while count < 5:

            try:
                with socket.create_connection(
                        (ping_host, ping_port), 2.0) as s:

                    result = s.connect_ex(s.getpeername())
                    s.sendall(versionString)

            except:  # Refactor: too broad exception
                result = -1

            if result == 0:
                logger.debug(
                    f'Host "{ping_host}:{ping_port}" is available', self)
                return

            count += 1
            sleep(0.2)

        if result != 0:
            proxy_msg = f' via proxy "{ping_host}:{ping_port}"' \
                if self.proxy_host else ''
            msg = f'Ping {self.host}{proxy_msg} failed. ' \
                  'Host is down or wrong address.'
            logger.debug(msg, self)

            raise MountException(msg)

    def checkRemoteCommands(self, retry=False):
        """
        Try out all relevant commands used by Back In Time on the remote host
        to make sure snapshots will be successful with the remote host. This
        will also check that hard-links are supported on the remote host. This
        check can be disabled with :py:func:`config.Config.sshCheckCommands`.

        Args:
            retry (bool): Retry to run the commands if it failed because the
                command string was to long.

        Raises:
            exceptions.MountException: If a command is not supported on remote
                host or if hard-links are not supported.
        """

        if not self.config.sshCheckCommands():
            return

        logger.debug('Check remote commands', self)

        def maxArg():
            if retry:
                raise MountException(
                    "Checking commands on remote host didn't return any "
                    "output. We already checked the maximum argument length "
                    "but it seems like there is another problem")

            logger.warning(
                'Looks like the command was to long for remote SSHd. '
                'We will test max arg length now and retry.',
                self)

            import ssh_max_arg
            max_arg_size = ssh_max_arg.probe_max_ssh_command_size(self.config)
            ssh_max_arg.report_result(self.host, max_arg_size)

            self.config.setSshMaxArgLength(max_arg_size, self.profile_id)

            return self.checkRemoteCommands(retry=True)

        remote_tmp_dir_1 = os.path.join(self.path, 'tmp_%s' % self.randomId())
        remote_tmp_dir_2 = os.path.join(self.path, 'tmp_%s' % self.randomId())

        with tempfile.TemporaryDirectory() as tmp:

            tmp_file = os.path.join(tmp, 'a')

            with open(tmp_file, 'wt') as f:
                f.write('foo')

            # check rsync
            rsync1 = tools.rsyncPrefix(
                self.config, no_perms=False, progress=False)
            rsync1.append(tmp_file)
            rsync1.append('%s@%s:%s/' % (
                self.user,
                tools.escapeIPv6Address(self.host),
                remote_tmp_dir_1))

            # check remote rsync hard-link support
            rsync2 = tools.rsyncPrefix(
                self.config, no_perms=False, progress=False)
            rsync2.append(
                '--link-dest=../%s' % os.path.basename(remote_tmp_dir_1))
            rsync2.append(tmp_file)
            rsync2.append('%s@%s:%s/' % (
                self.user,
                tools.escapeIPv6Address(self.host),
                remote_tmp_dir_2))

            for cmd in (rsync1, rsync2):
                logger.debug('Check rsync command: %s' % cmd, self)

                proc = subprocess.Popen(cmd,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True)
                err = proc.communicate()[1]

                if err or proc.returncode:
                    logger.debug(f'rsync command returned error: {err}', self)

                    raise MountException(
                        "Remote host {host} doesn't support '{command}:\n"
                        "{err}\n"
                        "Look at 'man backintime' for further instructions."
                        .format(
                            host=self.host,
                            command=cmd,
                            err=err)
                    )

        # check cp chmod find and rm
        head = 'tmp1="%s"; tmp2="%s"; ' % (remote_tmp_dir_1, remote_tmp_dir_2)

        # first define a function to clean up and exit
        head += 'cleanup(){ '
        head += 'test -e "$tmp1/a" && rm "$tmp1/a" >/dev/null 2>&1; '
        head += 'test -e "$tmp2/a" && rm "$tmp2/a" >/dev/null 2>&1; '
        head += 'test -e smr.lock && rm smr.lock >/dev/null 2>&1; '
        head += 'test -e "$tmp1" && rmdir "$tmp1" >/dev/null 2>&1; '
        head += 'test -e "$tmp2" && rmdir "$tmp2" >/dev/null 2>&1; '
        head += 'test -n "$tmp3" && test -e "$tmp3" && rmdir "$tmp3" >/dev/null 2>&1; '
        head += 'exit $1; }; '
        tail = []

        # list inodes
        cmd = 'ls -i "$tmp1/a"; ls -i "$tmp2/a"; '
        tail.append(cmd)

        # try nice -n 19
        if self.nice:
            cmd = 'echo \"nice -n 19\"; nice -n 19 true >/dev/null; err_nice=$?; '
            cmd += 'test $err_nice -ne 0 && cleanup $err_nice; '
            tail.append(cmd)

        # try ionice -c2 -n7
        if self.ionice:
            cmd = 'echo \"ionice -c2 -n7\"; ionice -c2 -n7 true >/dev/null; err_nice=$?; '
            cmd += 'test $err_nice -ne 0 && cleanup $err_nice; '
            tail.append(cmd)

        # try nocache
        if self.nocache:
            cmd = 'echo \"nocache\"; nocache true >/dev/null; err_nocache=$?; '
            cmd += 'test $err_nocache -ne 0 && cleanup $err_nocache; '
            tail.append(cmd)

        # try screen, bash and flock used by smart-remove running in background
        if self.config.smartRemoveRunRemoteInBackground(self.profile_id):
            cmd = 'echo \"screen -d -m bash -c ...\"; screen -d -m bash -c \"true\" >/dev/null; err_screen=$?; '
            cmd += 'test $err_screen -ne 0 && cleanup $err_screen; '
            tail.append(cmd)

            cmd = 'echo \"(flock -x 9) 9>smr.lock\"; bash -c \"(flock -x 9) 9>smr.lock\" >/dev/null; err_flock=$?; '
            cmd += 'test $err_flock -ne 0 && cleanup $err_flock; '
            tail.append(cmd)

            cmd = 'echo \"rmdir \\$(mktemp -d)\"; tmp3=$(mktemp -d); test -z "$tmp3" && cleanup 1; rmdir $tmp3 >/dev/null; err_rmdir=$?; '
            cmd += 'test $err_rmdir -ne 0 && cleanup $err_rmdir; '
            tail.append(cmd)

        # if we end up here, everything should be fine
        cmd = 'echo \"done\"; cleanup 0'
        tail.append(cmd)

        maxLength = self.config.sshMaxArgLength(self.profile_id)
        additionalChars = len('echo ""') \
            + len(self.config.sshPrefixCmd(self.profile_id, cmd_type=str))

        output = ''
        err = ''
        returncode = 0

        for cmd in tools.splitCommands(tail,
                                       head=head,
                                       maxLength=maxLength-additionalChars):
            if cmd.endswith('; '):
                cmd += 'echo ""'

            c = self.config.sshCommand(
                cmd=[cmd],
                custom_args=['-p', str(self.port), self.user_host],
                port=False,
                user_host=False,
                nice=False,
                ionice=False,
                profile_id=self.profile_id)

            try:
                logger.debug('Call command: %s' % ' '.join(c), self)
                proc = subprocess.Popen(c,
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        universal_newlines=True)
                ret = proc.communicate()

            except OSError as e:

                # Argument list too long
                if e.errno == 7:
                    logger.debug(
                        'Argument list too long (Python exception)', self)

                    return maxArg()

                else:
                    raise

            logger.debug('Command stdout: %s' % ret[0], self)
            logger.debug('Command stderr: %s' % ret[1], self)
            logger.debug('Command returncode: %s' % proc.returncode, self)

            output += ret[0].strip('\n') + '\n'
            err += ret[1].strip('\n') + '\n'
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

        if returncode or not output_split[-1].startswith('done'):

            for command in ('rm', 'nice', 'ionice',
                            'nocache', 'screen', '(flock'):

                if output_split[-1].startswith(command):
                    command = f"'{output_split[-1]}':\n{err}"
                    msg = _("Remote host {host} doesn't support {command}") \
                        .format(host=self.host, command=command)
                    raise MountException('{}\n{}'.format(
                        msg,
                        _("Look at 'man backintime' for further instructions")
                        )
                    )

            msg = _('Check commands on host {host} returned unknown error') \
                .format(host=self.host)
            raise MountException('{}:\n{}n{}'.format(
                msg,
                err,
                _("Look at 'man backintime' for further instructions")))

        inodes = []

        for tmp in (remote_tmp_dir_1, remote_tmp_dir_2):

            for line in output_split:

                m = re.match(r'^(\d+).*?%s' % tmp, line)
                if m:
                    inodes.append(m.group(1))

        logger.debug('remote inodes: ' + ' | '.join(inodes), self)

        if len(inodes) == 2 and inodes[0] != inodes[1]:
            raise MountException(
                _("Remote host {host} doesn't support hardlinks")
                .format(host=self.host))

    def randomId(self, size=6, chars=string.ascii_uppercase + string.digits):
        """
        Create a random string.

        Args:
            size (int):     length of the string
            chars (str):    characters used as basis for the random string

        Returns:
            str:            random string with length ``size``
        """

        return ''.join(random.choice(chars) for x in range(size))


def sshKeyGen(keyfile):
    """
    Generate a new ssh-key pair (private and public key) in ``keyfile`` and
    ``keyfile``.pub

    Args:
        keyfile (str):  path for private key file

    Returns:
        bool:           True if successful; False if ``keyfile`` already exist
                        or if there was an error
    """

    if os.path.exists(keyfile):
        logger.warning(
            'SSH keyfile "{}" already exist. Skip creating a new one'
            .format(keyfile))

        return False

    cmd = ['ssh-keygen', '-t', 'rsa', '-N', '', '-f', keyfile]

    proc = subprocess.Popen(cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)

    err = proc.communicate()[1]

    if proc.returncode:
        logger.error('Failed to create a new ssh-key: {}'.format(err))
    else:
        logger.info('Successfully created new ssh-key "{}"'.format(keyfile))

    return not proc.returncode


def sshCopyIdCommand(
    pubkey,
    user,
    host,
    port='22',
    proxy_user=None,
    proxy_host=None,
    proxy_port='22',
    cipher=None
):
    """
    Generate a ssh-copy-id command to copy the given public ssh-key to a
    remote host.

    Args:
        pubkey (str):   path to the public key file
        user (str):     remote user
        host (str):     remote host
        port (str):     ssh port on remote host
        proxy_user (str):     proxy host user
        proxy_host (str):     proxy host
        proxy_port (str):     proxy host port
        cipher (str):   cipher used for ssh

    Returns:
        list: The ssh-copy-id command as a list.

    Raises:
        FileNotFoundError: If public key file not exist.
    """
    if not Path(pubkey).exists():
        msg = f'SSH public key "{pubkey}" does not exist.'
        logger.error(msg)
        raise FileNotFoundError(msg)

    cmd = [
        'ssh-copy-id',
        # key file
        '-i', pubkey,
        # port
        '-p', str(port),
    ]

    # cipher
    if cipher and cipher != 'default':
        cmd.extend(['-o', 'Ciphers={}'.format(cipher)])

    # proxy
    if proxy_host:
        proxy_jump = f'{proxy_user}@{proxy_host}:{proxy_port}'
        cmd.extend(['-o', f'ProxyJump={proxy_jump}'])

    cmd.append(f'{user}@{host}')

    logger.debug(f'ssh-copy-id command {cmd}')

    return cmd


def sshCopyId(
    pubkey,
    user,
    host,
    port='22',
    proxy_user=None,
    proxy_host=None,
    proxy_port=None,
    askPass='backintime-askpass',
    cipher=None
):
    """
    Copy SSH public key ``pubkey`` to remote ``host``.

    Args:
        pubkey (str):   path to the public key file
        user (str):     remote user
        host (str):     remote host
        port (str):     ssh port on remote host
        askPass (str):  program used to pipe password into ssh
        cipher (str):   cipher used for ssh

    Returns:
        bool:           True if successful
    """
    cmd = sshCopyIdCommand(
        pubkey,
        user,
        host,
        port,
        proxy_user,
        proxy_host,
        proxy_port,
        cipher
    )

    env = os.environ.copy()
    env['SSH_ASKPASS'] = askPass
    env['ASKPASS_MODE'] = 'USER'
    env['ASKPASS_PROMPT'] = '{}\n{}:'.format(
        _('Copy public ssh-key "{pubkey}" to remote host "{host}".').format(
            pubkey=pubkey, host=host),
        _('Please enter a password for "{user}".').format(user=user)
    )
    proc = subprocess.Popen(cmd, env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setsid,  # cut of ssh from current
                                                   # terminal to make it use
                                                   # backintime-askpass
                            universal_newlines=True)

    err = proc.communicate()[1]

    if proc.returncode:
        logger.error('Failed to copy ssh-key "{}" to "{}@{}": [{}] {}'
                     .format(pubkey, user, host, proc.returncode, err))

    else:
        logger.info('Successfully copied ssh-key "{}" to "{}@{}"'
                    .format(pubkey, user, host))

    return not proc.returncode


def sshKeyFingerprint(path):
    """
    Get the hex fingerprint from a given ssh key.

    Args:
        path (str): full path to key file

    Returns:
        str:        hex fingerprint from key
    """

    if not os.path.exists(path):
        return

    cmd = ['ssh-keygen', '-l', '-f', path]

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    output = proc.communicate()[0]

    m = re.match(r'\d+\s+(SHA256:\S+|[a-fA-F0-9:]+)\s.*',
                 output.decode())
    if m:
        return m.group(1)


def sshHostKey(host, port='22'):
    """
    Get the remote host key from ``host``.

    Args:
        host (str): host name or IP address
        port (str): port number of remote ssh-server

    Returns:
        tuple:      three item tuple with (fingerprint, hashed host key,
                    key type)
    """

    for t in ('ecdsa', 'rsa'):
        cmd = ['ssh-keyscan', '-t', t, '-p', port, host]
        proc = subprocess.Popen(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)

        hostKey = proc.communicate()[0].strip()

        if hostKey:
            break

    if hostKey:

        logger.debug('Found {} key for host "{}"'.format(t.upper(), host))

        with tempfile.TemporaryDirectory() as tmp:

            keyFile = os.path.join(tmp, 'key')

            with open(keyFile, 'wb') as f:
                f.write(hostKey + b'\n')

            hostKeyFingerprint = sshKeyFingerprint(keyFile)

            cmd = ['ssh-keygen', '-H', '-f', keyFile]

            proc = subprocess.Popen(cmd,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            proc.communicate()

            with open(keyFile, 'rt') as f:
                hostKeyHash = f.read().strip()

        return (hostKeyFingerprint, hostKeyHash, t.upper())

    return (None, None, None)


def writeKnownHostsFile(key):
    """
    Write host key ``key`` into `~/.ssh/known_hosts`.

    Args:
        key (str):  host key
    """

    sshDir = os.path.expanduser('~/.ssh')

    knownHostFile = os.path.join(sshDir, 'known_hosts')

    if not os.path.isdir(sshDir):
        tools.mkdir(sshDir, 0o700)

    with open(knownHostFile, 'at') as f:
        logger.info('Write host key to {}'.format(knownHostFile))
        f.write(key + '\n')
