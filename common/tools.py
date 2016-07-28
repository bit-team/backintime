#    Back In Time
#    Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze, Taylor Raack
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
import sys
import subprocess
import shlex
import signal
import re
import errno
import gzip
import tempfile
import collections
import hashlib
import ipaddress
from datetime import datetime
from distutils.version import StrictVersion
keyring = None
keyring_warn = False
try:
    if os.getenv('BIT_USE_KEYRING', 'true') == 'true' and os.geteuid() != 0:
        import keyring
except:
    keyring = None
    os.putenv('BIT_USE_KEYRING', 'false')
    keyring_warn = True

# getting dbus imports to work in Travis CI is a huge pain
# use conditional dbus import
ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'

try:
    import dbus
except ImportError:
    if ON_TRAVIS or ON_RTD:
        #python-dbus doesn't work on Travis yet.
        dbus = None
    else:
        raise

import configfile
import logger
import bcolors
from exceptions import Timeout, InvalidChar, PermissionDeniedByPolicy

DISK_BY_UUID = '/dev/disk/by-uuid'

def sharePath():
    """
    Get BackInTimes installation base path.

    If running from source return default '/usr/share'

    Returns:
        str:    share path like::

                    /usr/share
                    /usr/local/share
                    /opt/usr/share
    """
    share = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir))
    if os.path.basename(share) == 'share':
        return share
    else:
        return '/usr/share'

def backintimePath(*path):
    """
    Get path inside 'backintime' install folder.

    Args:
        *path (str):    paths that should be joind to 'backintime'

    Returns:
        str:            'backintime' child path like::

                            /usr/share/backintime/common
                            /usr/share/backintime/qt4
    """
    return os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, *path))

def registerBackintimePath(*path):
    """
    Add BackInTime path ``path`` to :py:data:`sys.path` so subsequent imports
    can discover them.

    Args:
        *path (str):    paths that should be joind to 'backintime'

    Note:
        Duplicate in :py:func:`qt4/qt4tools.py` because modules in qt4 folder
        would need this to actually import :py:mod:`tools`.
    """
    path = backintimePath(*path)
    if not path in sys.path:
        sys.path.insert(0, path)

def runningFromSource():
    """
    Check if BackInTime is running from source (without installing).

    Returns:
        bool:   ``True`` if BackInTime is running from source
    """
    return os.path.isfile(backintimePath('common', 'backintime'))

def addSourceToPathEnviron():
    """
    Add 'backintime/common' path to 'PATH' environ variable.
    """
    source = backintimePath('common')
    path = os.getenv('PATH')
    if source not in path.split(':'):
        os.environ['PATH'] = '%s:%s' %(source, path)

def gitRevisionAndHash():
    """
    Get the current Git Branch and the last HashID (shot form) if running
    from source.

    Returns:
        tuple:  two items of either :py:class:`str` instance if running from
                source or ``None``
    """
    ref, hashid = None, None
    gitPath = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, '.git'))
    headPath = os.path.join(gitPath, 'HEAD')
    refPath = ''
    if not os.path.isdir(gitPath):
        return (ref, hashid)
    try:
        with open(headPath, 'rt') as f:
            refPath = f.read().strip('\n')
            if refPath.startswith('ref: '):
                refPath = refPath[5:]
            if refPath:
                refPath = os.path.join(gitPath, refPath)
                ref = os.path.basename(refPath)
    except Exception as e:
        pass
    if os.path.isfile(refPath):
        try:
            with open(refPath, 'rt') as f:
                hashid = f.read().strip('\n')[:7]
        except:
            pass
    return (ref, hashid)

def readFile(path, default = None):
    """
    Read the file in ``path`` or its '.gz' compressed variant and return its
    content or ``default`` if ``path`` does not exist.

    Args:
        path (str):             full path to file that should be read.
                                '.gz' will be added automatically if the file
                                is compressed
        default (str):          default if ``path`` does not exist

    Returns:
        str:                    content of file in ``path``
    """
    ret_val = default

    try:
        if os.path.exists(path):
            with open(path) as f:
                ret_val = f.read()
        elif os.path.exists(path + '.gz'):
            with gzip.open(path + '.gz', 'rt') as f:
                ret_val = f.read()
    except:
        pass

    return ret_val

def readFileLines(path, default = None):
    """
    Read the file in ``path`` or its '.gz' compressed variant and return its
    content as a list of lines or ``default`` if ``path`` does not exist.

    Args:
        path (str):             full path to file that should be read.
                                '.gz' will be added automatically if the file
                                is compressed
        default (list):         default if ``path`` does not exist

    Returns:
        list:                   content of file in ``path`` splitted by lines.
    """
    ret_val = default

    try:
        if os.path.exists(path):
            with open(path) as f:
                ret_val = [x.rstrip('\n') for x in f.readlines()]
        elif os.path.exists(path + '.gz'):
            with gzip.open(path + '.gz', 'rt') as f:
                ret_val = [x.rstrip('\n') for x in f.readlines()]
    except:
        pass

    return ret_val

def checkCommand(cmd):
    """
    Check if command ``cmd`` is a file in 'PATH' environ.

    Args:
        cmd (str):  command

    Returns:
        bool:       ``True`` if command ``cmd`` is in 'PATH' environ
    """
    cmd = cmd.strip()

    if not cmd:
        return False

    if os.path.isfile(cmd):
        return True
    return not which(cmd) is None

def which(cmd):
    """
    Get the fullpath of executable command ``cmd``. Works like
    command-line 'which' command.

    Args:
        cmd (str):  command

    Returns:
        str:        fullpath of command ``cmd`` or ``None`` if command is
                    not available
    """
    pathenv = os.getenv('PATH', '')
    path = pathenv.split(":")
    path.insert(0, os.getcwd())
    for directory in path:
        fullpath = os.path.join(directory, cmd)
        if os.path.isfile(fullpath) and os.access(fullpath, os.X_OK):
            return fullpath
    return None

def makeDirs(path):
    """
    Create directories ``path`` recursive and return success.

    Args:
        path (str): fullpath to directories that should be created

    Returns:
        bool:       ``True`` if successful
    """
    path = path.rstrip(os.sep)
    if not path:
        return False

    if os.path.isdir(path):
        return True
    else:
        try:
            os.makedirs(path)
        except Exception as e:
            logger.error("Failed to make dirs '%s': %s"
                         %(path, str(e)), traceDepth = 1)
    return os.path.isdir(path)

def mkdir(path, mode = 0o755):
    """
    Create directory ``path``.

    Args:
        path (str): full path to directory that should be created
        mode (int): numeric permission mode

    Returns:
        bool:       ``True`` if successful
    """
    if os.path.isdir(path):
        try:
            os.chmod(path, mode)
        except:
            return False
        return True
    else:
        os.mkdir(path, mode)
        if mode & 0o002 == 0o002:
            #make file world (other) writeable was requested
            #debian and ubuntu won't set o+w with os.mkdir
            #this will fix it
            os.chmod(path, mode)
    return os.path.isdir(path)

def pids():
    """
    List all PIDs currently running on the system.

    Returns:
        list:   PIDs as int
    """
    return [int(x) for x in os.listdir('/proc') if x.isdigit()]

def processStat(pid):
    """
    Get the stat's of the process with ``pid``.

    Args:
        pid (int):  Process Indicator

    Returns:
        str:        stat from /proc/PID/stat
    """
    try:
        with open('/proc/{}/stat'.format(pid), 'rt') as f:
            return f.read()
    except OSError as e:
        logger.warning('Failed to read process stat from {}: [{}] {}'.format(e.filename, e.errno, e.strerror))
        return ''

def processPaused(pid):
    """
    Check if process ``pid`` is paused (got signal SIGSTOP).

    Args:
        pid (int):  Process Indicator

    Returns:
        bool:       True if process is paused
    """
    m = re.match(r'\d+ \(.+\) T', processStat(pid))
    return bool(m)

def processName(pid):
    """
    Get the name of the process with ``pid``.

    Args:
        pid (int):  Process Indicator

    Returns:
        str:        name of the process
    """
    m = re.match(r'.*\((.+)\).*', processStat(pid))
    if m:
        return m.group(1)

def processCmdline(pid):
    """
    Get the cmdline (command that spawnd this process) of the process with
    ``pid``.

    Args:
        pid (int):  Process Indicator

    Returns:
        str:        cmdline of the process
    """
    try:
        with open('/proc/{}/cmdline'.format(pid), 'rt') as f:
            return f.read().strip('\n')
    except OSError as e:
        logger.warning('Failed to read process cmdline from {}: [{}] {}'.format(e.filename, e.errno, e.strerror))
        return ''

def pidsWithName(name):
    """
    Get all processes currently running with name ``name``.

    Args:
        name (str): name of a process like 'python3' or 'backintime'

    Returns:
        list:       PIDs as int
    """
    # /proc/###/stat stores just the first 16 chars of the process name
    return [x for x in pids() if processName(x) == name[:15]]

def processExists(name):
    """
    Check if process ``name`` is currently running.

    Args:
        name (str): name of a process like 'python3' or 'backintime'

    Returns:
        bool:       ``True`` if there is a process running with ``name``
    """
    return len(pidsWithName(name)) > 0

def processAlive(pid):
    """
    Check if the process with PID ``pid`` is alive.

    Args:
        pid (int):  Process Indicator

    Returns:
        bool:       ``True`` if the process with PID ``pid`` is alive

    Raises:
        ValueError: If ``pid`` is 0 because 'kill(0, SIG)' would send SIG to all
                    processes
    """
    if pid < 0:
        return False
    elif pid == 0:
        raise ValueError('invalid PID 0')
    else:
        try:
            os.kill(pid, 0)	#this will raise an exception if the pid is not valid
        except OSError as err:
            if err.errno == errno.ESRCH:
                # ESRCH == No such process
                return False
            elif err.errno == errno.EPERM:
                # EPERM clearly means there's a process to deny access to
                return True
            else:
                raise
        else:
            return True

def checkXServer():
    """
    Check if there is a X11 server running on this system.

    Returns:
        bool:   ``True`` if X11 server is running
    """
    proc = subprocess.Popen(['xdpyinfo'],
                            stdout = subprocess.DEVNULL,
                            stderr = subprocess.DEVNULL)
    proc.communicate()
    return proc.returncode == 0

def preparePath(path):
    """
    Removes trailing slash '/' from ``path``.

    Args:
        path (str): absolut path

    Returns:
        str:        path ``path`` without trailing but with leading slash
    """
    path = path.strip("/")
    path = os.sep + path
    return path

def powerStatusAvailable():
    """
    Check if org.freedesktop.UPower is available so that
    :py:func:`tools.onBattery` would return the correct power status.

    Returns:
        bool:   ``True`` if :py:func:`tools.onBattery` can report power status
    """
    if dbus:
        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.UPower',
                                   '/org/freedesktop/UPower')
            return 'OnBattery' in proxy.GetAll('org.freedesktop.UPower',
                            dbus_interface = 'org.freedesktop.DBus.Properties')
        except dbus.exceptions.DBusException:
            pass
    return False

def onBattery():
    """
    Checks if the system is on battery power.

    Returns:
        bool:   ``True`` if system is running on battery
    """
    if dbus:
        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.UPower',
                                   '/org/freedesktop/UPower')
            return bool(proxy.Get('org.freedesktop.UPower',
                                  'OnBattery',
                                  dbus_interface = 'org.freedesktop.DBus.Properties'))
        except dbus.exceptions.DBusException:
            pass
    return False

def rsyncCaps(data = None):
    """
    Get capabilities of the installed rsync binary. This can be different from
    version to version and also on build arguments used when building rsync.

    Args:
        data (str): 'rsync --version' output. This is just for unittests.

    Returns:
        list:       List of str with rsyncs capabilities
    """
    if not data:
        proc = subprocess.Popen(['rsync', '--version'],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
        data = proc.communicate()[0]
    caps = []
    #rsync >= 3.1 does provide --info=progress2
    m = re.match(r'rsync\s*version\s*(\d\.\d)', data)
    if m and StrictVersion(m.group(1)) >= StrictVersion('3.1'):
        caps.append('progress2')

    #all other capabilities are separated by ',' between
    #'Capabilities:' and '\n\n'
    m = re.match(r'.*Capabilities:(.+)\n\n.*', data, re.DOTALL)
    if not m:
        return caps

    for line in m.group(1).split('\n'):
        caps.extend([i.strip(' \n') for i in line.split(',') if i.strip(' \n')])
    return caps

def rsyncPrefix(config,
                no_perms = True,
                use_mode = ['ssh', 'ssh_encfs'],
                progress = True):
    """
    Get rsync command and all args for creating a new snapshot. Args are
    based on current profile in ``config``.

    Args:
        config (config.Config): current config
        no_perms (bool):        don't sync permissions (--no-p --no-g --no-o)
                                if ``True``.
                                :py:func:`config.Config.preserveAcl` == ``True`` or
                                :py:func:`config.Config.preserveXattr` == ``True``
                                will overwrite this to ``False``
        use_mode (list):        if current mode is in this list add additional
                                args for that mode
        progress (bool):        add '--info=progress2' to show progress

    Returns:
        list:                   rsync command with all args but without
                                --include, --exclude, source and destination
    """
    caps = rsyncCaps()
    cmd = []
    if config.nocacheOnLocal():
        cmd.append('nocache')
    cmd.append('rsync')
    cmd.append('-rtDHh')

    if config.useChecksum() or config.forceUseChecksum:
        cmd.append('--checksum')

    if config.copyUnsafeLinks():
        cmd.append('--copy-unsafe-links')

    if config.copyLinks():
        cmd.append('--copy-links')
    else:
        cmd.append('--links')

    if config.preserveAcl() and "ACLs" in caps:
        cmd.append('-A')
        no_perms = False

    if config.preserveXattr() and "xattrs" in caps:
        cmd.append('-X')
        no_perms = False

    if no_perms:
        cmd.extend(('--no-p', '--no-g', '--no-o'))
    else:
        cmd.append('-pEgo')

    if progress and 'progress2' in caps:
        cmd.extend(('--info=progress2', '--no-i-r'))

    if config.rsyncOptionsEnabled():
        cmd.extend(shlex.split(config.rsyncOptions()))

    cmd.extend(rsyncSshArgs(config, use_mode))
    return cmd

def rsyncSshArgs(config, use_mode = ['ssh', 'ssh_encfs']):
    """
    Get SSH args for rsync based on current profile in ``config``.

    Args:
        config (config.Config): current config
        use_mode (list):        if current mode is in this list add additional
                                args for that mode

    Returns:
        list:                   SSH args for rsync
    """
    cmd = []
    mode = config.snapshotsMode()
    if mode in ['ssh', 'ssh_encfs'] and mode in use_mode:
        ssh = config.sshCommand(user_host = False,
                                 ionice = False,
                                 nice = False)
        cmd.append('--rsh=' + ' '.join(ssh))

        if config.bwlimitEnabled():
            cmd.append('--bwlimit=%d' %config.bwlimit())

        if config.niceOnRemote()     \
          or config.ioniceOnRemote() \
          or config.nocacheOnRemote():
            rsync_path = '--rsync-path='
            if config.niceOnRemote():
                rsync_path += 'nice -n 19 '
            if config.ioniceOnRemote():
                rsync_path += 'ionice -c2 -n7 '
            if config.nocacheOnRemote():
                rsync_path += 'nocache '
            rsync_path += 'rsync'
            cmd.append(rsync_path)
    return cmd

def rsyncRemove(config, run_local = True):
    """
    Get rsync command and all args for removing snapshots with rsync.

    Args:
        config (config.Config): current config
        run_local (bool):       if True and current mode is ``ssh``
                                or ``ssh_encfs`` this will add SSH options

    Returns:
        list:                   rsync command with all args
    """
    cmd = ['rsync', '-a', '--delete']
    if run_local:
        cmd.extend(rsyncSshArgs(config))
    return cmd

#TODO: check if we really need this
def tempFailureRetry(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except (os.error, IOError) as ex:
            if ex.errno == errno.EINTR:
                continue
            else:
                raise

def md5sum(path):
    """
    Calculate md5sum for file in ``path``.

    Args:
        path (str): full path to file

    Returns:
        str:        md5sum of file
    """
    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            data = f.read(4096)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()

def checkCronPattern(s):
    """
    Check if ``s`` is a valid cron pattern.
    Examples::

        0,10,13,15,17,20,23
        */6

    Args:
        s (str):    pattern to check

    Returns:
        bool:       ``True`` if ``s`` is a valid cron pattern
    """
    if s.find(' ') >= 0:
        return False
    try:
        if s.startswith('*/'):
            if s[2:].isdigit() and int(s[2:]) <= 24:
                return True
            else:
                return False
        for i in s.split(','):
            if i.isdigit() and int(i) <= 24:
                continue
            else:
                return False
        return True
    except ValueError:
        return False

#TODO: check if this is still necessary
def checkHomeEncrypt():
    """
    Return ``True`` if users home is encrypted
    """
    home = os.path.expanduser('~')
    if not os.path.ismount(home):
        return False
    if checkCommand('ecryptfs-verify'):
        try:
            subprocess.check_call(['ecryptfs-verify', '--home'],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            pass
        else:
            return True
    if checkCommand('encfs'):
        proc = subprocess.Popen(['mount'], stdout=subprocess.PIPE, universal_newlines = True)
        mount = proc.communicate()[0]
        r = re.compile('^encfs on %s type fuse' % home)
        for line in mount.split('\n'):
            if r.match(line):
                return True
    return False

def envLoad(f):
    """
    Load environ variables from file ``f`` into current environ.
    Do not overwrite existing environ variables.

    Args:
        f (str):    full path to file with environ variables
    """
    env = os.environ.copy()
    env_file = configfile.ConfigFile()
    env_file.load(f, maxsplit = 1)
    for key in env_file.keys():
        value = env_file.strValue(key)
        if not value:
            continue
        if not key in list(env.keys()):
            os.environ[key] = value
    del(env_file)

def envSave(f):
    """
    Save environ variables to file that are needed by cron
    to connect to keyring. This will only work if the user is logged in.

    Args:
        f (str):    full path to file for environ variables
    """
    env = os.environ.copy()
    env_file = configfile.ConfigFile()
    for key in ('GNOME_KEYRING_CONTROL', 'DBUS_SESSION_BUS_ADDRESS', \
                'DBUS_SESSION_BUS_PID', 'DBUS_SESSION_BUS_WINDOWID', \
                'DISPLAY', 'XAUTHORITY', 'GNOME_DESKTOP_SESSION_ID', \
                'KDE_FULL_SESSION'):
        if key in env:
            env_file.setStrValue(key, env[key])

    env_file.save(f)

def keyringSupported():
    if keyring is None:
        logger.debug('No keyring due to import errror.')
        return False
    backends = []
    try: backends.append(keyring.backends.SecretService.Keyring)
    except: pass
    try: backends.append(keyring.backends.Gnome.Keyring)
    except: pass
    try: backends.append(keyring.backends.kwallet.Keyring)
    except: pass
    try: backends.append(keyring.backends.kwallet.DBusKeyring)
    except: pass
    try: backends.append(keyring.backend.SecretServiceKeyring)
    except: pass
    try: backends.append(keyring.backend.GnomeKeyring)
    except: pass
    try: backends.append(keyring.backend.KDEKWallet)
    except: pass
    try:
        displayName = keyring.get_keyring().__module__
    except:
        displayName = str(keyring.get_keyring())
    if backends and isinstance(keyring.get_keyring(), tuple(backends)):
        logger.debug("Found appropriate keyring '{}'".format(displayName))
        return True
    logger.debug("No appropriate keyring found. '{}' can't be used with BackInTime".format(displayName))
    return False

def password(*args):
    if not keyring is None:
        return keyring.get_password(*args)
    return None

def setPassword(*args):
    if not keyring is None:
        return keyring.set_password(*args)
    return False

def mountpoint(path):
    """
    Get the mountpoint of ``path``. If your HOME is on a separate partition
    mountpoint('/home/user/foo') would return '/home'.

    Args:
        path (str): full path

    Returns:
        str:        mountpoint of the filesystem
    """
    path = os.path.realpath(os.path.abspath(path))
    while path != os.path.sep:
        if os.path.ismount(path):
            return path
        path = os.path.abspath(os.path.join(path, os.pardir))
    return path

def get_df_output(column, path):
    """
    Get the specified ``column`` from the output of 'df' command for ``path``.

    Args:
        column (str): column name (see 'man df')
        path (str): full path

    Returns:
        str:        value of the specified ``column``
    """
    proc = subprocess.Popen(['df', '--output=' + column, path], stdout=subprocess.PIPE, universal_newlines = True)
    out, err = proc.communicate()
    if proc.returncode or err:
        logger.error('Failed to get column "%s" from df : %s, %s' % (column, proc.returncode, err))
        return None

    result = [x.strip() for x in out.strip('\n').split('\n')]
    if len(result) >= 2:
        return result[1]
    else:
        return None

def device(path):
    """
    Get the device for the filesystem of ``path``.
    Example::

        /dev/sda1
        /dev/mapper/vglinux
        proc

    Args:
        path (str): full path

    Returns:
        str:        device
    """
    return get_df_output('source', mountpoint(path))

def filesystem(path):
    """
    Get the filesystem type for the filesystem of ``path``.

    Args:
        path (str): full path

    Returns:
        str:        filesystem
    """
    return get_df_output('fstype', mountpoint(path))

def uuidFromDev(dev):
    """
    Get the UUID for the block device ``dev``.

    Args:
        dev (str):  block device path

    Returns:
        str:        UUID
    """
    if dev and os.path.exists(dev):
        dev = os.path.realpath(dev)
        for uuid in os.listdir(DISK_BY_UUID):
            if dev == os.path.realpath(os.path.join(DISK_BY_UUID, uuid)):
                return uuid
    c = re.compile(b'.*?ID_FS_UUID=(\S+)')
    try:
        udevadm = subprocess.check_output(['udevadm', 'info', '--name=%s' % dev],
                                          stderr = subprocess.DEVNULL)
        for line in udevadm.split():
            m = c.match(line)
            if m:
                return m.group(1).decode('UTF-8')
    except:
        pass
    return None

def uuidFromPath(path):
    """
    Get the UUID for the for the filesystem of ``path``.

    Args:
        path (str): full path

    Returns:
        str:        UUID
    """
    return uuidFromDev(device(path))

def filesystemMountInfo():
    """
    Get a dict of mount point string -> dict of filesystem info for
    entire system.

    Returns:
        dict:   {MOUNTPOINT: {'original_uuid': UUID}}
    """
    # There may be multiple mount points inside of the root (/) mount, so
    # iterate over mtab to find all non-special mounts.
    with open('/etc/mtab', 'r') as mounts:
        return {items[1]: {'original_uuid': uuidFromDev(items[0])} for items in
                [mount_line.strip('\n').split(' ')[:2] for mount_line in mounts]
                if uuidFromDev(items[0]) != None}

def wrapLine(msg, size=950, delimiters='\t ', new_line_indicator = 'CONTINUE: '):
    """
    Wrap line ``msg`` into multiple lines with each shorter than ``size``. Try
    to break the line on ``delimiters``. New lines will start with
    ``new_line_indicator``.

    Args:
        msg (str):                  string that should get wrapped
        size (int):                 maximum lenght of returned strings
        delimiters (str):           try to break ``msg`` on these characters
        new_line_indicator (str):   start new lines with this string

    Yields:
        str:                        lines with max ``size`` lenght
    """
    if len(new_line_indicator) >= size - 1:
        new_line_indicator = ''
    while msg:
        if len(msg) <= size:
            yield(msg)
            break
        else:
            line = ''
            for look in range(size-1, size//2, -1):
                if msg[look] in delimiters:
                    line, msg = msg[:look+1], new_line_indicator + msg[look+1:]
                    break
            if not line:
                line, msg = msg[:size], new_line_indicator + msg[size:]
            yield(line)

def syncfs():
    """
    Sync any data buffered in memory to disk.

    Returns:
        bool:   ``True`` if successful
    """
    if checkCommand('sync'):
        return(Execute(['sync']).run() == 0)

def isRoot():
    """
    Check if we are root.

    Returns:
        bool:   ``True`` if we are root
    """
    return os.geteuid() == 0

def usingSudo():
    """
    Check if 'sudo' was used to start this process.

    Returns:
        bool:   ``True`` if process was started with sudo
    """
    return isRoot() and os.getenv('HOME', '/root') != '/root'

re_wildcard = re.compile(r'(?:\[|\]|\?)')
re_asterisk = re.compile(r'\*')
re_separate_asterisk = re.compile(r'(?:^\*+[^/\*]|[^/\*]\*+[^/\*]|[^/\*]\*+|\*+[^/\*]|[^/\*]\*+$)')

def patternHasNotEncryptableWildcard(pattern):
    """
    Check if ``pattern`` has wildcards ``[ ] ? *``.
    but return ``False`` for ``foo/*``, ``foo/*/bar``, ``*/bar`` or ``**/bar``

    Args:
        pattern (str):  path or pattern to check

    Returns:
        bool:           ``True`` if ``pattern`` has wildcards ``[ ] ? *`` but
                        ``False`` if wildcard look like
                        ``foo/*``, ``foo/*/bar``, ``*/bar`` or ``**/bar``
    """
    if not re_wildcard.search(pattern) is None:
        return True

    if not re_asterisk is None and not re_separate_asterisk.search(pattern) is None:
        return True
    return False

BIT_TIME_FORMAT = '%Y%m%d %H%M'
ANACRON_TIME_FORMAT = '%Y%m%d'

def readTimeStamp(f):
    """
    Read date string from file ``f`` and try to return datetime.

    Args:
        f (str):            full path to timestamp file

    Returns:
        datetime.datetime:  date from timestamp file
    """
    if not os.path.exists(f):
        return
    with open(f, 'r') as f:
        s = f.read().strip('\n')
    for i in (ANACRON_TIME_FORMAT, BIT_TIME_FORMAT):
        try:
            return datetime.strptime(s, i)
        except ValueError:
            pass

def writeTimeStamp(f):
    """
    Write current date and time into file ``f``.

    Args:
        f (str):            full path to timestamp file
    """
    makeDirs(os.path.dirname(f))
    with open(f, 'w') as f:
        f.write(datetime.now().strftime(BIT_TIME_FORMAT))

INHIBIT_LOGGING_OUT = 1
INHIBIT_USER_SWITCHING = 2
INHIBIT_SUSPENDING = 4
INHIBIT_IDLE = 8

INHIBIT_DBUS = (
               {'service':      'org.gnome.SessionManager',
                'objectPath':   '/org/gnome/SessionManager',
                'methodSet':    'Inhibit',
                'methodUnSet':  'Uninhibit',
                'interface':    'org.gnome.SessionManager',
                'arguments':    (0, 1, 2, 3)
               },
               {'service':      'org.mate.SessionManager',
                'objectPath':   '/org/mate/SessionManager',
                'methodSet':    'Inhibit',
                'methodUnSet':  'Uninhibit',
                'interface':    'org.mate.SessionManager',
                'arguments':    (0, 1, 2, 3)
               },
               {'service':      'org.freedesktop.PowerManagement',
                'objectPath':   '/org/freedesktop/PowerManagement/Inhibit',
                'methodSet':    'Inhibit',
                'methodUnSet':  'UnInhibit',
                'interface':    'org.freedesktop.PowerManagement.Inhibit',
                'arguments':    (0, 2)
               })

def inhibitSuspend(app_id = sys.argv[0],
                    toplevel_xid = None,
                    reason = 'take snapshot',
                    flags = INHIBIT_SUSPENDING | INHIBIT_IDLE):
    """
    Prevent machine to go to suspend or hibernate.
    Returns the inhibit cookie which is used to end the inhibitor.
    """
    if ON_TRAVIS:
        # no suspend on travis (no dbus either)
        return
    if not app_id:
        app_id = 'backintime'
    if not toplevel_xid:
        toplevel_xid = 0

    for dbus_props in INHIBIT_DBUS:
        try:
            #connect directly to the socket instead of dbus.SessionBus because
            #the dbus.SessionBus was initiated before we loaded the environ
            #variables and might not work
            if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                bus = dbus.bus.BusConnection(os.environ['DBUS_SESSION_BUS_ADDRESS'])
            else:
                bus = dbus.SessionBus()
            interface = bus.get_object(dbus_props['service'], dbus_props['objectPath'])
            proxy = interface.get_dbus_method(dbus_props['methodSet'], dbus_props['interface'])
            cookie = proxy(*[(app_id, dbus.UInt32(toplevel_xid), reason, dbus.UInt32(flags))[i] for i in dbus_props['arguments']])
            logger.info('Inhibit Suspend started. Reason: %s' % reason)
            return (cookie, bus, dbus_props)
        except dbus.exceptions.DBusException:
            pass
    if isRoot():
        logger.debug("Inhibit Suspend failed because BIT was started as root.")
        return
    logger.warning('Inhibit Suspend failed.')

def unInhibitSuspend(cookie, bus, dbus_props):
    """
    Release inhibit.
    """
    assert isinstance(cookie, int), 'cookie is not int type: %s' % cookie
    assert isinstance(bus, dbus.bus.BusConnection), 'bus is not dbus.bus.BusConnection type: %s' % bus
    assert isinstance(dbus_props, dict), 'dbus_props is not dict type: %s' % dbus_props
    try:
        interface = bus.get_object(dbus_props['service'], dbus_props['objectPath'])
        proxy = interface.get_dbus_method(dbus_props['methodUnSet'], dbus_props['interface'])
        proxy(cookie)
        logger.info('Release inhibit Suspend')
        return None
    except dbus.exceptions.DBusException:
        logger.warning('Release inhibit Suspend failed.')
        return (cookie, bus, dbus_props)

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
    proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.DEVNULL)
    output = proc.communicate()[0]
    m = re.match(b'\d+\s+(SHA256:\S+|[a-fA-F0-9:]+)\s.*', output)
    if m:
        return m.group(1).decode('UTF-8')

def readCrontab():
    """
    Read users crontab.

    Returns:
        list:   crontab lines
    """
    cmd = ['crontab', '-l']
    if not checkCommand(cmd[0]):
        logger.debug('crontab not found.')
        return []
    else:
        proc = subprocess.Popen(cmd,
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE,
                                universal_newlines = True)
        out, err = proc.communicate()
        if proc.returncode or err:
            logger.error('Failed to get crontab lines: %s, %s'
                         %(proc.returncode, err))
            return []
        else:
            crontab = [x.strip() for x in out.strip('\n').split('\n')]
            logger.debug('Read %s lines from users crontab'
                         %len(crontab))
            return crontab

def writeCrontab(lines):
    """
    Write to users crontab.

    Note:
        This will overwrite the whole crontab. So to keep the old crontab and
        only add new entries you need to read it first with
        :py:func:`tools.readCrontab`, append new entries to the list and write
        it back.

    Args:
        lines (:py:class:`list`, :py:class:`tuple`):
                    lines that should be written to crontab

    Returns:
        bool:       ``True`` if successful
    """
    assert isinstance(lines, (list, tuple)), 'lines is not list or tuple type: %s' % lines
    with tempfile.NamedTemporaryFile(mode = 'wt') as f:
        f.write('\n'.join(lines))
        f.write('\n')
        f.flush()
        cmd = ['crontab', f.name]
        proc = subprocess.Popen(cmd,
                                stdout = subprocess.DEVNULL,
                                stderr = subprocess.PIPE,
                                universal_newlines = True)
        out, err = proc.communicate()
    if proc.returncode or err:
        logger.error('Failed to write lines to crontab: %s, %s'
                     %(proc.returncode, err))
        return False
    else:
        logger.debug('Wrote %s lines to users crontab'
                     %len(lines))
        return True

def splitCommands(cmds, head = '', tail = '', maxLength = 0):
    """
    Split a list of commands ``cmds`` into multiple commands with each length
    lower than ``maxLength``.

    Args:
        cmds (list):            commands
        head (str):             command that need to run first on every
                                iteration of ``cmds``
        tail (str):             command that need to run after every iteration
                                of ``cmds``
        maxLength (int):        maximum length a command could be.
                                Don't split if <= 0

    Yields:
        str:                    new command with length < ``maxLength``

    Example::

        head cmds[0] cmds[n] tail
    """
    while cmds:
        s = head
        while cmds and ((len(s + cmds[0] + tail) <= maxLength) or maxLength <= 0):
            s += cmds.pop(0)
        s += tail
        yield s

def isIPv6Address(address):
    """
    Check if ``address`` is a valid IPv6 address.

    Args:
        address (str):  address that should get tested

    Returns:
        bool:           True if ``address`` is a valid IPv6 address
    """
    try:
        return isinstance(ipaddress.IPv6Address(address), ipaddress.IPv6Address)
    except:
        return False

def escapeIPv6Address(address):
    """
    Escape IPv6 Addresses with square brackets ``[]``.

    Args:
        address (str):  address that should be escaped

    Returns:
        str:            ``address`` in square brackets
    """
    if isIPv6Address(address):
        return '[{}]'.format(address)
    else:
        return address

def camelCase(s):
    """
    Remove underlines and make every first char uppercase.

    Args:
        s (str):    string separated by underlines (foo_bar)

    Returns:
        str:        string without underlines but uppercase chars (FooBar)
    """
    return ''.join([x.capitalize() for x in s.split('_')])

class UniquenessSet:
    """
    Check for uniqueness or equality of files.

    Args:
        dc (bool):              if ``True`` use deep check which will compare
                                files md5sums if they are of same size but no
                                hardlinks (don't have the same inode).
                                If ``False`` use files size and mtime
        follow_symlink (bool):  if ``True`` check symlinks target instead of the
                                link
        list_equal_to (str):    full path to file. If not empty only return
                                equal files to the given path instead of
                                unique files.
    """
    def __init__(self, dc = False, follow_symlink = False, list_equal_to = ''):
        self.deep_check = dc
        self.follow_sym = follow_symlink
        self._uniq_dict = {}      # if not self._uniq_dict[size] -> size already checked with md5sum
        self._size_inode = set()  # if (size,inode) in self._size_inode -> path is a hlink
        self.list_equal_to = list_equal_to
        if list_equal_to:
            st = os.stat(list_equal_to)
            if self.deep_check:
                self.reference = (st.st_size, md5sum(list_equal_to))
            else:
                self.reference = (st.st_size, int(st.st_mtime))

    def check(self, input_path):
        """
        Check file ``input_path`` for either uniqueness or equality
        (depending on ``list_equal_to`` from constructor).

        Args:
            input_path (str):   full path to file

        Returns:
            bool:               ``True`` if file is unique and ``list_equal_to``
                                is empty.
                                Or ``True`` if file is equal to file in
                                ``list_equal_to``
        """
        # follow symlinks ?
        path = input_path
        if self.follow_sym and os.path.islink(input_path):
            path = os.readlink(input_path)

        if self.list_equal_to:
            return self.checkEqual(path)
        else:
            return self.checkUnique(path)

    def checkUnique(self, path):
        """
        Check file ``path`` for uniqueness and store a unique key for ``path``.

        Args:
            path (str): full path to file

        Returns:
            bool:       ``True`` if file is unique
        """
        # check
        if self.deep_check:
            dum = os.stat(path)
            size,inode  = dum.st_size, dum.st_ino
            # is it a hlink ?
            if (size, inode) in self._size_inode:
                logger.debug("[deep test] : skip, it's a duplicate (size, inode)", self)
                return False
            self._size_inode.add((size,inode))
            if size not in self._uniq_dict:
                # first item of that size
                unique_key = size
                logger.debug("[deep test] : store current size ?", self)
            else:
                prev = self._uniq_dict[size]
                if prev:
                    # store md5sum instead of previously stored size
                    md5sum_prev = md5sum(prev)
                    self._uniq_dict[size] = None
                    self._uniq_dict[md5sum_prev] = prev
                    logger.debug("[deep test] : size duplicate, remove the size, store prev md5sum", self)
                unique_key = md5sum(path)
                logger.debug("[deep test] : store current md5sum ?", self)
        else:
            # store a tuple of (size, modification time)
            obj  = os.stat(path)
            unique_key = (obj.st_size, int(obj.st_mtime))
        # store if not already present, then return True
        if unique_key not in self._uniq_dict:
            logger.debug(" >> ok, store !", self)
            self._uniq_dict[unique_key] = path
            return True
        logger.debug(" >> skip (it's a duplicate)", self)
        return False

    def checkEqual(self, path):
        """
        Check if ``path`` is equal to the file in ``list_equal_to`` from
        constructor.

        Args:
            path (str): full path to file

        Returns:
            bool:       ``True`` if file is equal
        """
        st = os.stat(path)
        if self.deep_check:
            if self.reference[0] == st.st_size:
                return self.reference[1] == md5sum(path)
            return False
        else:
            return self.reference == (st.st_size, int(st.st_mtime))

class Alarm(object):
    """
    Timeout for FIFO. This does not work with threading.
    """
    def __init__(self, callback = None, overwrite = True):
        self.callback = callback
        self.ticking = False
        self.overwrite = overwrite

    def start(self, timeout):
        """
        Start timer
        """
        if self.ticking and not self.overwrite:
            return
        try:
            signal.signal(signal.SIGALRM, self.handler)
            signal.alarm(timeout)
        except ValueError:
            pass
        self.ticking = True

    def stop(self):
        """
        Stop timer before it come to an end
        """
        try:
            signal.alarm(0)
            self.ticking = False
        except:
            pass

    def handler(self, signum, frame):
        """
        Timeout occur.
        """
        self.ticking = False
        if self.callback is None:
            raise Timeout()
        else:
            self.callback()

class ShutDown(object):
    """
    Shutdown the system after the current snapshot has finished.
    This should work for KDE, Gnome, Unity, Cinnamon, XFCE, Mate and E17.
    """
    DBUS_SHUTDOWN ={'gnome':   {'bus':          'sessionbus',
                                'service':      'org.gnome.SessionManager',
                                'objectPath':   '/org/gnome/SessionManager',
                                'method':       'Shutdown',
                                    #methods    Shutdown
                                    #           Reboot
                                    #           Logout
                                'interface':    'org.gnome.SessionManager',
                                'arguments':    ()
                                    #arg (only with Logout)
                                    #           0 normal
                                    #           1 no confirm
                                    #           2 force
                               },
                    'kde':     {'bus':          'sessionbus',
                                'service':      'org.kde.ksmserver',
                                'objectPath':   '/KSMServer',
                                'method':       'logout',
                                'interface':    'org.kde.KSMServerInterface',
                                'arguments':    (-1, 2, -1)
                                    #1st arg   -1 confirm
                                    #           0 no confirm
                                    #2nd arg   -1 full dialog with default logout
                                    #           0 logout
                                    #           1 restart
                                    #           2 shutdown
                                    #3rd arg   -1 wait 30sec
                                    #           2 immediately
                               },
                    'xfce':    {'bus':          'sessionbus',
                                'service':      'org.xfce.SessionManager',
                                'objectPath':   '/org/xfce/SessionManager',
                                'method':       'Shutdown',
                                    #methods    Shutdown
                                    #           Restart
                                    #           Suspend (no args)
                                    #           Hibernate (no args)
                                    #           Logout (two args)
                                'interface':    'org.xfce.Session.Manager',
                                'arguments':    (True,)
                                    #arg        True    allow saving
                                    #           False   don't allow saving
                                    #1nd arg (only with Logout)
                                    #           True    show dialog
                                    #           False   don't show dialog
                                    #2nd arg (only with Logout)
                                    #           True    allow saving
                                    #           False   don't allow saving
                               },
                    'mate':    {'bus':          'sessionbus',
                                'service':      'org.mate.SessionManager',
                                'objectPath':   '/org/mate/SessionManager',
                                'method':       'Shutdown',
                                    #methods    Shutdown
                                    #           Logout
                                'interface':    'org.mate.SessionManager',
                                'arguments':    ()
                                    #arg (only with Logout)
                                    #           0 normal
                                    #           1 no confirm
                                    #           2 force
                               },
                    'e17':     {'bus':          'sessionbus',
                                'service':      'org.enlightenment.Remote.service',
                                'objectPath':   '/org/enlightenment/Remote/RemoteObject',
                                'method':       'Halt',
                                    #methods    Halt -> Shutdown
                                    #           Reboot
                                    #           Logout
                                    #           Suspend
                                    #           Hibernate
                                'interface':    'org.enlightenment.Remote.Core',
                                'arguments':    ()
                               },
                    'e19':     {'bus':          'sessionbus',
                                'service':      'org.enlightenment.wm.service',
                                'objectPath':   '/org/enlightenment/wm/RemoteObject',
                                'method':       'Shutdown',
                                    #methods    Shutdown
                                    #           Restart
                                'interface':    'org.enlightenment.wm.Core',
                                'arguments':    ()
                               },
                    'z_freed': {'bus':          'systembus',
                                'service':      'org.freedesktop.login1',
                                'objectPath':   '/org/freedesktop/login1',
                                'method':       'PowerOff',
                                'interface':    'org.freedesktop.login1.Manager',
                                'arguments':    (True,)
                               }
                   }

    def __init__(self):
        self.is_root = isRoot()
        if self.is_root:
            self.proxy, self.args = None, None
        else:
            self.proxy, self.args = self._prepair()
        self.activate_shutdown = False
        self.started = False

    def _prepair(self):
        """
        Try to connect to the given dbus services. If successful it will
        return a callable dbus proxy and those arguments.
        """
        try:
            if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                sessionbus = dbus.bus.BusConnection(os.environ['DBUS_SESSION_BUS_ADDRESS'])
            else:
                sessionbus = dbus.SessionBus()
            systembus  = dbus.SystemBus()
        except:
            return((None, None))
        des = list(self.DBUS_SHUTDOWN.keys())
        des.sort()
        for de in des:
            if de == 'gnome' and self.unity7():
                continue
            dbus_props = self.DBUS_SHUTDOWN[de]
            try:
                if dbus_props['bus'] == 'sessionbus':
                    bus = sessionbus
                else:
                    bus = systembus
                interface = bus.get_object(dbus_props['service'], dbus_props['objectPath'])
                proxy = interface.get_dbus_method(dbus_props['method'], dbus_props['interface'])
                return((proxy, dbus_props['arguments']))
            except dbus.exceptions.DBusException:
                continue
        return((None, None))

    def canShutdown(self):
        """
        Indicate if a valid dbus service is available to shutdown system.
        """
        return(not self.proxy is None or self.is_root)

    def askBeforeQuit(self):
        """
        Indicate if ShutDown is ready to fire and so the application
        shouldn't be closed.
        """
        return(self.activate_shutdown and not self.started)

    def shutdown(self):
        """
        Run 'shutdown -h now' if we are root or
        call the dbus proxy to start the shutdown.
        """
        if not self.activate_shutdown:
            return(False)
        if self.is_root:
            syncfs()
            self.started = True
            proc = subprocess.Popen(['shutdown', '-h', 'now'])
            proc.communicate()
            return proc.returncode
        if self.proxy is None:
            return(False)
        else:
            syncfs()
            self.started = True
            return(self.proxy(*self.args))

    def unity7(self):
        """
        Unity >= 7.0 doesn't shutdown automatically. It will
        only show shutdown dialog and wait for user input.
        """
        if not checkCommand('unity'):
            return False
        proc = subprocess.Popen(['unity', '--version'],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
        unity_version = proc.communicate()[0]
        m = re.match(r'unity ([\d\.]+)', unity_version)
        return m and StrictVersion(m.group(1)) >= StrictVersion('7.0') and processExists('unity-panel-service')

class SetupUdev(object):
    """
    Setup Udev rules for starting BackInTime when a drive get connected.
    This is done by serviceHelper.py script (included in backintime-qt4)
    running as root though DBus.
    """
    CONNECTION = 'net.launchpad.backintime.serviceHelper'
    OBJECT = '/UdevRules'
    INTERFACE = 'net.launchpad.backintime.serviceHelper.UdevRules'
    MEMBERS = ('addRule', 'save', 'delete')
    def __init__(self):
        if dbus is None:
            self.isReady = False
            return
        try:
            bus = dbus.SystemBus()
            conn = bus.get_object(SetupUdev.CONNECTION, SetupUdev.OBJECT)
            self.iface = dbus.Interface(conn, SetupUdev.INTERFACE)
        except dbus.exceptions.DBusException as e:
            if e._dbus_error_name in ('org.freedesktop.DBus.Error.NameHasNoOwner',
                                      'org.freedesktop.DBus.Error.ServiceUnknown',
                                      'org.freedesktop.DBus.Error.FileNotFound'):
                conn = None
            else:
                raise
        self.isReady = bool(conn)

    def addRule(self, cmd, uuid):
        """
        Prepair rules in serviceHelper.py
        """
        if not self.isReady:
            return
        try:
            return self.iface.addRule(cmd, uuid)
        except dbus.exceptions.DBusException as e:
            if e._dbus_error_name == 'net.launchpad.backintime.InvalidChar':
                raise InvalidChar(str(e))
            else:
                raise

    def save(self):
        """
        Save rules with serviceHelper.py after authentication
        If no rules where added before this will delete current rule.
        """
        if not self.isReady:
            return
        try:
            return self.iface.save()
        except dbus.exceptions.DBusException as e:
            if e._dbus_error_name == 'com.ubuntu.DeviceDriver.PermissionDeniedByPolicy':
                raise PermissionDeniedByPolicy(str(e))
            else:
                raise

    def clean(self):
        """
        Clean up remote cache
        """
        if not self.isReady:
            return
        self.iface.clean()

class PathHistory(object):
    def __init__(self, path):
        self.history = [path,]
        self.index = 0

    def append(self, path):
        #append path after the current index
        self.history = self.history[:self.index + 1] + [path,]
        self.index = len(self.history) - 1

    def previous(self):
        if self.index == 0:
            return self.history[0]
        try:
            path = self.history[self.index - 1]
        except IndexError:
            return self.history[self.index]
        self.index -= 1
        return path

    def next(self):
        if self.index == len(self.history) - 1:
            return self.history[-1]
        try:
            path = self.history[self.index + 1]
        except IndexError:
            return self.history[self.index]
        self.index += 1
        return path

    def reset(self, path):
        self.history = [path,]
        self.index = 0

class OrderedSet(collections.MutableSet):
    """
    OrderedSet from Python recipe
    http://code.activestate.com/recipes/576694/
    """
    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

class Execute(object):
    """
    Execute external commands and handle its output.

    Args:

        cmd (:py:class:`str` or :py:class:`list`):
                            command with arguments that should be called.
                            Depending on if this is :py:class:`str` or
                            :py:class:`list` instance the command will be called
                            by either :py:func:`os.system` (deprecated) or
                            :py:class:`subprocess.Popen`
        callback (method):  function which will handle output returned by
                            command
        user_data:          extra arguments which will be forwarded to
                            ``callback`` function
        filters (tuple):    Tuple of functions used to filter messages before
                            sending them to ``callback``
        parent (instance):  instance of the calling method used only to proper
                            format log messages
        conv_str (bool):    convert output to :py:class:`str` if True or keep it
                            as :py:class:`bytes` if False
        join_stderr (bool): join stderr to stdout

    Note:
        Signals SIGTSTP and SIGCONT send to Python main process will be
        forwarded to the command. SIGHUP will kill the process.
    """
    def __init__(self,
                 cmd,
                 callback = None,
                 user_data = None,
                 filters = (),
                 parent = None,
                 conv_str = True,
                 join_stderr = True):
        self.cmd = cmd
        self.callback = callback
        self.user_data = user_data
        self.filters = filters
        self.currentProc = None
        self.conv_str = conv_str
        self.join_stderr = join_stderr
        #we need to forward parent to have the correct class name in debug log
        if parent:
            self.parent = parent
        else:
            self.parent = self

        if isinstance(self.cmd, list):
            self.pausable = True
            self.printable_cmd = ' '.join(self.cmd)
            logger.debug('Call command "%s"' %self.printable_cmd, self.parent, 2)
        else:
            self.pausable = False
            self.printable_cmd = self.cmd
            logger.warning('Call command with old os.system method "%s"' %self.printable_cmd, self.parent, 2)

    def run(self):
        """
        Start the command.

        Returns:
            int:    returncode from command
        """
        ret_val = 0
        out = ''

        #backwards compatibility with old os.system and os.popen calls
        if isinstance(self.cmd, str):
            if self.callback is None:
                ret_val = os.system(self.cmd)
            else:
                pipe = os.popen(self.cmd, 'r')

                while True:
                    line = tempFailureRetry(pipe.readline)
                    if not line:
                        break
                    line = line.strip()
                    for f in self.filters:
                        line = f(line)
                    if not line:
                        continue
                    self.callback(line , self.user_data)

                ret_val = pipe.close()
                if ret_val is None:
                    ret_val = 0

        #new and preferred method using subprocess.Popen
        elif isinstance(self.cmd, (list, tuple)):
            try:
                #register signals for pause, resume and kill
                signal.signal(signal.SIGTSTP, self.pause)
                signal.signal(signal.SIGCONT, self.resume)
                signal.signal(signal.SIGHUP, self.kill)
            except ValueError:
                #signal only work in qt main thread
                pass

            if self.join_stderr:
                stderr = subprocess.STDOUT
            else:
                stderr = subprocess.DEVNULL
            self.currentProc = subprocess.Popen(self.cmd,
                                                stdout = subprocess.PIPE,
                                                stderr = stderr)
            if self.callback:
                for line in self.currentProc.stdout:
                    if self.conv_str:
                        line = line.decode().rstrip('\n')
                    else:
                        line = line.rstrip(b'\n')
                    for f in self.filters:
                        line = f(line)
                    if not line:
                        continue
                    self.callback(line, self.user_data)

            out = self.currentProc.communicate()[0]
            ret_val = self.currentProc.returncode

            try:
                #reset signals to their default
                signal.signal(signal.SIGTSTP, signal.SIG_DFL)
                signal.signal(signal.SIGCONT, signal.SIG_DFL)
                signal.signal(signal.SIGHUP, signal.SIG_DFL)
            except ValueError:
                #signal only work in qt main thread
                pass

        if ret_val != 0:
            msg = 'Command "%s" returns %s%s%s' %(self.printable_cmd, bcolors.WARNING, ret_val, bcolors.ENDC)
            if out:
                msg += ' | %s' %out.decode().strip('\n')
            logger.warning(msg, self.parent, 2)
        else:
            msg = 'Command "%s..." returns %s' %(self.printable_cmd[:min(16, len(self.printable_cmd))], ret_val)
            if out:
                msg += ': %s' %out.decode().strip('\n')
            logger.debug(msg, self.parent, 2)

        return ret_val

    def pause(self, signum, frame):
        """
        Slot which will send ``SIGSTOP`` to the command. Is connected to
        signal ``SIGTSTP``.
        """
        if self.pausable and self.currentProc:
            logger.info('Pause process "%s"' %self.printable_cmd, self.parent, 2)
            return self.currentProc.send_signal(signal.SIGSTOP)

    def resume(self, signum, frame):
        """
        Slot which will send ``SIGCONT`` to the command. Is connected to
        signal ``SIGCONT``.
        """
        if self.pausable and self.currentProc:
            logger.info('Resume process "%s"' %self.printable_cmd, self.parent, 2)
            return self.currentProc.send_signal(signal.SIGCONT)

    def kill(self, signum, frame):
        """
        Slot which will kill the command. Is connected to signal ``SIGHUP``.
        """
        if self.pausable and self.currentProc:
            logger.info('Kill process "%s"' %self.printable_cmd, self.parent, 2)
            return self.currentProc.kill()


def __logKeyringWarning():
    from time import sleep
    sleep(0.1)
    logger.warning('import keyring failed')

if keyring is None and keyring_warn:
    #delay warning to give logger some time to import
    from threading import Thread
    thread = Thread(target = __logKeyringWarning, args = ())
    thread.start()
