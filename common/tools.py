#    Back In Time
#    Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import signal
import re
import errno
import gzip
import tempfile
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
ON_TRAVIS = 'TRAVIS' in os.environ and os.environ['TRAVIS'] == 'true'
try:
    import dbus
except ImportError:
    if ON_TRAVIS:
        #python-dbus doesn't work on Travis yet.
        dbus = None
    else:
        raise

import configfile
import logger
from exceptions import Timeout, InvalidChar, PermissionDeniedByPolicy

ON_AC = 0
ON_BATTERY = 1
POWER_ERROR = 255

DISK_BY_UUID = '/dev/disk/by-uuid'

def get_share_path():
    share = os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, os.pardir))
    if os.path.basename(share) == 'share':
        return share
    else:
        return '/usr/share'

def get_backintime_path(*path):
    return os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, *path))

def register_backintime_path(*path):
    '''find duplicate in qt4/qt4tools.py
    '''
    path = get_backintime_path(*path)
    if not path in sys.path:
        sys.path.insert(0, path)

def running_from_source():
    '''return True if BackInTime was started
    from source folder (without installing)
    '''
    return os.path.isfile(get_backintime_path('common', 'backintime'))

def add_source_to_path_environ():
    source = get_backintime_path('common')
    path = os.getenv('PATH')
    if source not in path.split(':'):
        os.environ['PATH'] = '%s:%s' %(source, path)

def get_git_ref_hash():
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
                hashid = f.read().strip('\n')
        except:
            pass
    return (ref, hashid[:7])

def read_file( path, default_value = None ):
    ret_val = default_value

    try:
        if os.path.exists(path):
            with open( path ) as f:
                ret_val = f.read()
        elif os.path.exists(path + '.gz'):
            with gzip.open(path + '.gz') as f:
                ret_val = f.read().decode()
    except:
        pass

    return ret_val

def read_file_lines( path, default_value = None ):
    ret_val = default_value

    try:
        if os.path.exists(path):
            with open( path ) as f:
                ret_val = f.readlines()
        elif os.path.exists(path + '.gz'):
            with gzip.open(path + '.gz') as f:
                ret_val = [b.decode() for b in f.readlines()]
    except:
        pass

    return ret_val


def read_command_output( cmd ):
    ret_val = ''

    try:
        pipe = os.popen( cmd )
        ret_val = pipe.read().strip()
        pipe.close()
    except:
        return ''

    return ret_val


def check_command( cmd ):
    cmd = cmd.strip()

    if not cmd:
        return False

    if os.path.isfile( cmd ):
        return True
    return not which(cmd) is None

def which(filename):
    """Checks if 'filename' is present in the system PATH."""
    pathenv = os.getenv('PATH', '')
    path = pathenv.split(":")
    path.insert(0, os.getcwd())
    for directory in path:
        fullpath = os.path.join(directory, filename)
        if os.path.isfile(fullpath) and os.access(fullpath, os.X_OK):
            return fullpath
    return None

def make_dirs( path ):
    path = path.rstrip( os.sep )
    if not path:
        return False

    if os.path.isdir(path):
        return True
    else:
        try:
            os.makedirs( path )
        except Exception as e:
            logger.error("Failed to make dirs '%s': %s"
                         %(path, str(e)), traceDepth = 1)
    return os.path.isdir(path)

def process_exists( name ):
    output = read_command_output( "ps -o pid= -C %s" % name )
    return len( output ) > 0


def check_x_server():
    return 0 == os.system( 'xdpyinfo >/dev/null 2>&1' )


def prepare_path( path ):
    path = path.strip( "/" )
    path = os.sep + path
    return path


def power_status_available():
    """Uses the on_ac_power command to detect if the the system is able
    to return the power status."""
    try:
        rt = subprocess.call( 'on_ac_power' )
        if rt == ON_AC or rt == ON_BATTERY:
            return True
    except:
        pass
    return False


def on_battery():
    """Checks if the system is on battery power."""
    if power_status_available ():
        return subprocess.call ( 'on_ac_power' ) == ON_BATTERY
    else:
        return False


def get_snapshots_list_in_folder( folder, sort_reverse = True ):
    biglist = []

    try:
        biglist = os.listdir( folder )
    except:
        pass

    list_ = []

    for item in biglist:
        if len( item ) != 15 and len( item ) != 19:
            continue
        if os.path.isdir( os.path.join( folder, item, 'backup' ) ):
            list_.append( item )

    list_.sort( reverse = sort_reverse )
    return list_


def get_nonsnapshots_list_in_folder( folder, sort_reverse = True ):
    biglist = []

    try:
        biglist = os.listdir( folder )
    except:
        pass

    list_ = []

    for item in biglist:
        if len( item ) != 15 and len( item ) != 19:
            list_.append( item )
        else:
            if os.path.isdir( os.path.join( folder, item, 'backup' ) ):
                continue
            else:
                list_.append( item )

    list_.sort( reverse = sort_reverse )
    return list_


def move_snapshots_folder( old_folder, new_folder ):
    '''Moves all the snapshots from one folder to another'''
    print("\nMove snapshots from %s to %s" %( old_folder, new_folder ))

    # Fetch a list with snapshots for verification
    snapshots_to_move = get_snapshots_list_in_folder( old_folder )
    snapshots_already_there = []
    if os.path.exists( new_folder ) == True:
        snapshots_already_there = get_snapshots_list_in_folder( new_folder )
    else:
        make_dirs( new_folder )
    print("To move: %s" % snapshots_to_move)
    print("Already there: %s" % snapshots_already_there)
    snapshots_expected = snapshots_to_move + snapshots_already_there
    print("Snapshots expected: %s" % snapshots_expected)

    # Check if both folders are within the same os
    device_old = os.stat( old_folder ).st_dev
    device_new = os.stat( new_folder ).st_dev
    if device_old == device_new:
        # Use move
        for snapshot in snapshots_to_move:
            cmd = "mv -f \"%s/%s\" \"%s\"" %( old_folder, snapshot, new_folder )
            _execute( cmd )
    else:
        # Use rsync
        # Prepare hardlinks
        if snapshots_already_there:
            first_snapshot_path = os.path.join( new_folder, snapshots_to_move[ len( snapshots_to_move ) - 1 ] )
            snapshot_to_hardlink_path =  os.path.join( new_folder, snapshots_already_there[0] )
            _execute( "find \"%s\" -type d -exec chmod u+wx {} \\;" % snapshot_to_hardlink_path )
            cmd = "cp -al \"%s\" \"%s\"" % ( snapshot_to_hardlink_path, first_snapshot_path )
            _execute( cmd )

        # Prepare excludes
        nonsnapshots = get_nonsnapshots_list_in_folder( old_folder )
        print("Nonsnapshots: %s" % nonsnapshots)
        items = []
        for nonsnapshot in nonsnapshots:
            for item in items:
                if nonsnapshot == item:
                    break
            items.append( "--exclude=\"%s\"" % nonsnapshot )
        rsync_exclude = ' '.join( items )

        # Move move move
        cmd = "rsync -aEAXHv --delete " + old_folder + " " + new_folder + " " + rsync_exclude
        _execute( cmd )
        _execute ( "find \"%s\" \"%s\" -type d -exec chmod a-w {} \\;" % ( snapshot_to_hardlink_path, first_snapshot_path ) )

    # Remove old ones
    snapshots_not_moved = []
    for snapshot in snapshots_to_move:
        if os.path.exists( os.path.join( new_folder, snapshot, "backup" ) ):
            if os.path.exists( os.path.join( old_folder, snapshot) ):
                print("Remove: %s" %snapshot)
                path_to_remove = os.path.join( old_folder, snapshot )
                cmd = "find \"%s\" -type d -exec chmod u+wx {} \\;" % path_to_remove #Debian patch
                _execute( cmd )
                cmd = "rm -rfv \"%s\"" % path_to_remove
                _execute( cmd )
            else:
                print("%s was already removed" %snapshot)
        else:
            snapshots_not_moved.append( snapshot )

    # Check snapshot list
    if snapshots_not_moved:
        print("Error! Not moved: %s\n" %snapshots_not_moved)
        return False
    print("Succes!\n")
    return True

def _execute( cmd, callback = None, user_data = None ):
    logger.debug("Call command \"%s\"" %cmd, traceDepth = 1)
    ret_val = 0

    if callback is None:
        ret_val = os.system( cmd )
    else:
        pipe = os.popen( cmd, 'r' )

        while True:
            line = temp_failure_retry( pipe.readline )
            if not line:
                break
            callback( line.strip(), user_data )

        ret_val = pipe.close()
        if ret_val is None:
            ret_val = 0

    if ret_val != 0:
        logger.warning("Command \"%s\" returns %s"
                       %(cmd, ret_val),
                       traceDepth = 1)
    else:
        logger.debug("Command \"%s...\" returns %s"
                     %(cmd[:min(16, len(cmd))], ret_val),
                     traceDepth = 1)

    return ret_val


def is_process_alive( pid ):
    try:
        os.kill( pid, 0 )	#this will raise an exception if the pid is not valid
    except:
        return False

    return True


def get_rsync_caps():
    data = read_command_output( 'rsync --version' )
    caps = []
    #rsync >= 3.1 does provide --info=progress2
    m = re.match(r'rsync\s*version\s*(\d\.\d)', data)
    if m and StrictVersion(m.group(1)) >= StrictVersion('3.1'):
        caps.append('progress2')
    si = data.find( 'Capabilities:' )
    if si < 0:
        return caps
    si = data.find( '\n', si )
    if si < 0:
        return caps
    ei = data.find( '\n\n', si )
    if ei < 0:
        return caps

    data = data[ si + 1 : ei - 1 ]
    data = data.split( '\n' )
    all_caps = ''

    for line in data:
        line = line.strip()
        if not line:
            continue
        if all_caps:
            all_caps = all_caps + ' '
        all_caps = all_caps + line

    caps.extend(all_caps.split( ", " ))
    return caps


def use_rsync_fast( config ):
    return not (config.preserve_acl() or config.preserve_xattr())


def get_rsync_prefix( config, no_perms = True, use_modes = ['ssh', 'ssh_encfs'] ):
    caps = get_rsync_caps()
    cmd = ''
    if config.is_run_nocache_on_local_enabled():
        cmd += 'nocache '
    cmd += 'rsync'
    cmd += ' -rtDHh'

    if config.use_checksum() or config.force_use_checksum:
        cmd = cmd + ' --checksum'

    if config.copy_unsafe_links():
        cmd = cmd + ' --copy-unsafe-links'

    if config.copy_links():
        cmd = cmd + ' --copy-links'
    else:
        cmd = cmd + ' --links'

    if config.preserve_acl() and "ACLs" in caps:
        cmd = cmd + ' -A'
        no_perms = False

    if config.preserve_xattr() and "xattrs" in caps:
        cmd = cmd + ' -X'
        no_perms = False

    if no_perms:
        cmd = cmd + ' --no-p --no-g --no-o'
    else:
        cmd = cmd + ' -pEgo'

    if 'progress2' in caps:
        cmd += ' --info=progress2 --no-i-r'

    if config.rsync_options_enabled():
        cmd += ' ' + config.rsync_options()

    mode = config.get_snapshots_mode()
    if mode in ['ssh', 'ssh_encfs'] and mode in use_modes:
        ssh_port = config.get_ssh_port()
        ssh_cipher = config.get_ssh_cipher()
        if ssh_cipher == 'default':
            ssh_cipher_suffix = ''
        else:
            ssh_cipher_suffix = '-c %s' % ssh_cipher
        # specifying key file here allows to override for potentially
        # conflicting .ssh/config key entry
        ssh_private_key = "-o IdentityFile=%s" % config.get_ssh_private_key_file()
        cmd += ' --rsh="ssh -p %s %s %s"' % ( str(ssh_port), ssh_cipher_suffix, ssh_private_key)

        if config.bwlimit_enabled():
            cmd = cmd + ' --bwlimit=%d' % config.bwlimit()

        if config.is_run_nice_on_remote_enabled()     \
          or config.is_run_ionice_on_remote_enabled() \
          or config.is_run_nocache_on_remote_enabled():
            cmd += ' --rsync-path="'
            if config.is_run_nice_on_remote_enabled():
                cmd += 'nice -n 19 '
            if config.is_run_ionice_on_remote_enabled():
                cmd += 'ionice -c2 -n7 '
            if config.is_run_nocache_on_remote_enabled():
                cmd += 'nocache '
            cmd += 'rsync"'

    return cmd + ' '

def temp_failure_retry(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except (os.error, IOError) as ex:
            if ex.errno == errno.EINTR:
                continue
            else:
                raise

def _get_md5sum_from_path(path):
    '''return md5sum of path, af available system command md5sum()'''
    if check_command("md5sum"):
        status,output = subprocess.getstatusoutput("md5sum '" + path + "'")
        if status == 0:
            md5sum = output.split(" ")[0]
            return md5sum
    # md5sum unavailable or command failed; raise an exception ? a message ? use std lib ?
    print("warning: md5sum() fail ! used (st_size, st_mttime) instead of md5sum.")
    obj  = os.stat(path)
    unique_key = (obj.st_size, int(obj.st_mtime))
    return unique_key

def check_cron_pattern(s):
    '''check if s look like '0,10,13,15,17,20,23' or '*/6' '''
    if s.find(' ') >= 0:
        return False
    try:
        if s.startswith('*/'):
            if int(s[2:]) <= 24:
                return True
            else:
                return False
        list_ = s.split(',')
        for s in list_:
            if int(s) <= 24:
                continue
            else:
                return False
        return True
    except ValueError:
        return False

def check_home_encrypt():
    '''return True if users home is encrypted'''
    home = os.path.expanduser('~')
    if not os.path.ismount(home):
        return False
    if check_command('ecryptfs-verify'):
        try:
            subprocess.check_call(['ecryptfs-verify', '--home'],
                                    stdout=open(os.devnull, 'w'),
                                    stderr=open(os.devnull, 'w'))
        except subprocess.CalledProcessError:
            pass
        else:
            return True
    if check_command('encfs'):
        proc = subprocess.Popen(['mount'], stdout=subprocess.PIPE, universal_newlines = True)
        mount = proc.communicate()[0]
        r = re.compile('^encfs on %s type fuse' % home)
        for line in mount.split('\n'):
            if r.match(line):
                return True
    return False

def load_env(f):
    env = os.environ.copy()
    env_file = configfile.ConfigFile()
    env_file.load(f, maxsplit = 1)
    for key in env_file.get_keys():
        value = env_file.get_str_value(key)
        if not value:
            continue
        if not key in list(env.keys()):
            os.environ[key] = value
    del(env_file)

def save_env(f):
    """
    save environ variables to file that are needed by cron
    to connect to keyring. This will only work if the user is logged in.
    """
    env = os.environ.copy()
    env_file = configfile.ConfigFile()
    for i in ('GNOME_KEYRING_CONTROL', 'DBUS_SESSION_BUS_ADDRESS', \
              'DBUS_SESSION_BUS_PID', 'DBUS_SESSION_BUS_WINDOWID', \
              'DISPLAY', 'XAUTHORITY', 'GNOME_DESKTOP_SESSION_ID', \
              'KDE_FULL_SESSION'):
        set_env_key(env, env_file, i)

    env_file.save(f)
    del(env_file)

def set_env_key(env, env_file, key):
    if key in env:
        env_file.set_str_value(key, env[key])

def keyring_supported():
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

def get_password(*args):
    if not keyring is None:
        return keyring.get_password(*args)
    return None

def set_password(*args):
    if not keyring is None:
        return keyring.set_password(*args)
    return False

def get_mountpoint(path):
    '''return MOUNTPOINT for given PATH'''
    path = os.path.realpath(os.path.abspath(path))
    while path != os.path.sep:
        if os.path.ismount(path):
            return path
        path = os.path.abspath(os.path.join(path, os.pardir))
    return path

def get_mount_args(path):
    '''return a tuple of mount arguments from /proc/mounts'''
    mp = get_mountpoint(path)
    with open('/etc/mtab', 'r') as mounts:
        for line in mounts:
            args = line.strip('\n').split(' ')
            if len(args) >= 2 and args[1] == mp:
                return args
    return None

def get_device(path):
    '''return DEVICE for given PATH'''
    args = get_mount_args(path)
    if args:
        return args[0]
    return None

def get_filesystem(path):
    '''return FILESYSTEM for given PATH'''
    args = get_mount_args(path)
    if args and len(args) >= 3:
        return args[2]
    return None

def get_uuid(dev):
    '''return uuid for given block device'''
    if dev and os.path.exists(dev):
        dev = os.path.realpath(dev)
        for uuid in os.listdir(DISK_BY_UUID):
            if dev == os.path.realpath(os.path.join(DISK_BY_UUID, uuid)):
                return uuid
    c = re.compile(b'.*?ID_FS_UUID=(\S+)')
    try:
        udevadm = subprocess.check_output(['udevadm', 'info', '--name=%s' % dev])
        for line in udevadm.split():
            m = c.match(line)
            if m:
                return m.group(1).decode('UTF-8')
    except:
        pass
    return None

def get_uuid_from_path(path):
    return get_uuid(get_device(path))

def wrap_line(msg, size=950, delimiters='\t ', new_line_indicator = 'CONTINUE: '):
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
    """writes any data buffered in memory out to disk
    """
    if check_command('sync'):
        return(_execute('sync') == 0)

def update_cached_fs(dir):
    """changes not made through sshfs on remote files will not be recognized
    immediately because of the local cache. But writing a new file into that
    folder will update local cache.
    """
    with tempfile.NamedTemporaryFile('w', dir = dir) as f:
        f.write('foo')

def isRoot():
    return os.geteuid() == 0

def usingSudo():
    return isRoot() and os.getenv('HOME', '/root') != '/root'

re_wildcard = re.compile(r'(?:\[|\]|\?|\*)')
re_separate_asterisk = re.compile(r'(?:^\*+[^/\*]|[^/\*]\*+[^/\*]|[^/\*]\*+|\*+[^/\*]|[^/\*]\*+$)')

def patternHasNotEncryptableWildcard(pattern):
    '''return True if path has wildcards [ ] ? *
    but return False for foo/*, foo/*/bar, */bar or **/bar
    '''
    if not re_wildcard.search(pattern) is None:
        if re_separate_asterisk.search(pattern) is None:
            return False
        return True
    return False

BIT_TIME_FORMAT = '%Y%m%d %H%M'
ANACRON_TIME_FORMAT = '%Y%m%d'

def readTimeStamp(f):
    '''read date string from file and try to return datetime'''
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
    '''write current date into file'''
    make_dirs(os.path.dirname(f))
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
               } )

def inhibitSuspend( app_id = sys.argv[0],
                    toplevel_xid = None,
                    reason = 'take snapshot',
                    flags = INHIBIT_SUSPENDING | INHIBIT_IDLE):
    '''Prevent machine to go to suspend or hibernate.
    Returns the inhibit cookie which is used to end the inhibitor.
    '''
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
            cookie = proxy(*[ (app_id, dbus.UInt32(toplevel_xid), reason, dbus.UInt32(flags))[i] for i in dbus_props['arguments'] ])
            logger.info('Inhibit Suspend started. Reason: %s' % reason)
            return (cookie, bus, dbus_props)
        except dbus.exceptions.DBusException:
            pass
    if isRoot():
        logger.debug("Inhibit Suspend failed because BIT was started as root.")
        return
    logger.warning('Inhibit Suspend failed.')

def unInhibitSuspend(cookie, bus, dbus_props):
    '''Release inhibit.
    '''
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

def getSshKeyFingerprint(path):
    '''return the hex fingerprint of a given ssh key
    '''
    if not os.path.exists(path):
        return
    cmd = ['ssh-keygen', '-l', '-f', path]
    proc = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = open(os.devnull, 'w'))
    output = proc.communicate()[0]
    m = re.match(b'\d+\s+([a-zA-Z0-9:]+).*', output)
    if m:
        return m.group(1).decode('UTF-8')

def readCrontab():
    '''read a list of lines from users crontab
    '''
    cmd = ['crontab', '-l']
    if not check_command(cmd[0]):
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
    '''write a list of lines to users crontab
    '''
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

def splitCommands(cmds, head = '', tail = '', maxLength = 0, additionalChars = 0):
    while cmds:
        s = head
        while cmds and ((len(s + cmds[0] + tail) + additionalChars <= maxLength) or not maxLength):
            s += cmds.pop(0)
        s += tail
        yield s

class UniquenessSet:
    '''a class to check for uniqueness of snapshots of the same [item]'''
    def __init__(self, dc = False, follow_symlink = False, list_equal_to = False):
        self.deep_check = dc
        self.follow_sym = follow_symlink
        self._uniq_dict = {}      # if not self._uniq_dict[size] -> size already checked with md5sum
        self._size_inode = set()  # if (size,inode) in self._size_inode -> path is a hlink
        self.list_equal_to = list_equal_to
        if list_equal_to:
            st = os.stat(list_equal_to)
            if self.deep_check:
                self.reference = (st.st_size, _get_md5sum_from_path(list_equal_to))
            else:
                self.reference = (st.st_size, int(st.st_mtime))

    def check_for(self, input_path):
        # follow symlinks ?
        path = input_path
        if self.follow_sym and os.path.islink(input_path):
            path = os.readlink(input_path)

        if self.list_equal_to:
            return self.check_equal(path)
        else:
            return self.check_unique(path)

    def check_unique(self, path):
        '''store a unique key for path, return True if path is unique'''
        # check
        if self.deep_check:
            dum = os.stat(path)
            size,inode  = dum.st_size, dum.st_ino
            # is it a hlink ?
            if (size, inode) in self._size_inode:
                logger.debug("[deep test] : skip, it's a duplicate (size, inode)", self)
                return False
            self._size_inode.add( (size,inode) )
            if size not in list(self._uniq_dict.keys()):
                # first item of that size
                unique_key = size
                logger.debug("[deep test] : store current size ?", self)
            else:
                prev = self._uniq_dict[size]
                if prev:
                    # store md5sum instead of previously stored size
                    md5sum_prev = _get_md5sum_from_path(prev)
                    self._uniq_dict[size] = None
                    self._uniq_dict[md5sum_prev] = prev
                    logger.debug("[deep test] : size duplicate, remove the size, store prev md5sum", self)
                unique_key = _get_md5sum_from_path(path)
                logger.debug("[deep test] : store current md5sum ?", self)
        else:
            # store a tuple of (size, modification time)
            obj  = os.stat(path)
            unique_key = (obj.st_size, int(obj.st_mtime))
        # store if not already present, then return True
        if unique_key not in list(self._uniq_dict.keys()):
            logger.debug(" >> ok, store !", self)
            self._uniq_dict[unique_key] = path
            return True
        logger.debug(" >> skip (it's a duplicate)", self)
        return False

    def check_equal(self, path):
        '''return True if path and reference are equal'''
        st = os.stat(path)
        if self.deep_check:
            if self.reference[0] == st.st_size:
                return self.reference[1] == _get_md5sum_from_path(path)
            return False
        else:
            return self.reference == (st.st_size, int(st.st_mtime))

class Alarm(object):
    """
    Timeout for FIFO. This does not work with threading.
    """
    def __init__(self, callback = None):
        self.callback = callback

    def start(self, timeout):
        """
        start timer
        """
        try:
            signal.signal(signal.SIGALRM, self.handler)
            signal.alarm(timeout)
        except ValueError:
            pass

    def stop(self):
        """
        stop timer before it come to an end
        """
        try:
            signal.alarm(0)
        except:
            pass

    def handler(self, signum, frame):
        """
        timeout occur.
        """
        if self.callback is None:
            raise Timeout()
        else:
            self.callback()

class ShutDown(object):
    """Shutdown the system after the current snapshot has finished.
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
                                'arguments':    (True, )
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
        """try to connect to the given dbus services. If successful it will
        return a callable dbus proxy and those arguments.
        """
        try:
            if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                sessionbus = dbus.bus.BusConnection(os.environ['DBUS_SESSION_BUS_ADDRESS'])
            else:
                sessionbus = dbus.SessionBus()
            systembus  = dbus.SystemBus()
        except:
            return( (None, None) )
        des = list(self.DBUS_SHUTDOWN.keys())
        des.sort()
        for de in des:
            if de == 'gnome' and self.unity_7():
                continue
            dbus_props = self.DBUS_SHUTDOWN[de]
            try:
                if dbus_props['bus'] == 'sessionbus':
                    bus = sessionbus
                else:
                    bus = systembus
                interface = bus.get_object(dbus_props['service'], dbus_props['objectPath'])
                proxy = interface.get_dbus_method(dbus_props['method'], dbus_props['interface'])
                return( (proxy, dbus_props['arguments']) )
            except dbus.exceptions.DBusException:
                continue
        return( (None, None) )

    def can_shutdown(self):
        """indicate if a valid dbus service is available to shutdown system.
        """
        return(not self.proxy is None or self.is_root)

    def ask_before_quit(self):
        """indicate if ShutDown is ready to fire and so the application
        shouldn't be closed.
        """
        return(self.activate_shutdown and not self.started)

    def shutdown(self):
        """run 'shutdown -h now' if we are root or
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

    def unity_7(self):
        """Unity >= 7.0 doesn't shutdown automatically. It will
        only show shutdown dialog and wait for user input.
        """
        if not check_command('unity'):
            return False
        unity_version = read_command_output('unity --version')
        m = re.match(r'unity ([\d\.]+)', unity_version)
        return m and StrictVersion(m.group(1)) >= StrictVersion('7.0') and process_exists('unity-panel-service')

class SetupUdev(object):
    """Setup Udev rules for starting BackInTime when a drive get connected.
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
        """prepair rules in serviceHelper.py
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
        """save rules with serviceHelper.py after authentication
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
        """clean up remote cache
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

def __log_keyring_warning():
    from time import sleep
    sleep(0.1)
    logger.warning('import keyring failed')

if keyring is None and keyring_warn:
    #delay warning to give logger some time to import
    import _thread
    _thread.start_new_thread(__log_keyring_warning, ())
    # logger.warning('import keyring failed')
