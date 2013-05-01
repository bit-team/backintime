#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
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


import os.path
import os
import sys
import subprocess
import hashlib
import commands
import signal
import re

import configfile

ON_AC = 0
ON_BATTERY = 1
POWER_ERROR = 255


def get_backintime_path( path ):
    return os.path.join( os.path.dirname( os.path.abspath( os.path.dirname( __file__ ) ) ), path )


def register_backintime_path( path ):
    path = get_backintime_path( path )
    if not path in sys.path:
        sys.path = [path] + sys.path


def read_file( path, default_value = None ):
    ret_val = default_value 

    try:
        file = open( path )
        ret_val = file.read()
        file.close()
    except:
        pass

    return ret_val


def read_file_lines( path, default_value = None ):
    ret_val = default_value 

    try:
        file = open( path )
        ret_val = file.readlines()
        file.close()
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

    if len( cmd ) < 1:
        return False

    if os.path.isfile( cmd ):
        return True

    cmd = read_command_output( "which \"%s\"" % cmd )

    if len( cmd ) < 1:
        return False

    if os.path.isfile( cmd ):
        return True

    return False


def make_dirs( path ):
    path = path.rstrip( os.sep )
    if len( path ) <= 0:
        return

    if not os.path.isdir( path ):
        try:
            os.makedirs( path )
        except:
            pass


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
    #print folder

    try:
        biglist = os.listdir( folder )
        #print biglist
    except:
        pass

    list = []

    for item in biglist:
        #print item + ' ' + str(len( item ))
        if len( item ) != 15 and len( item ) != 19:
            continue
        if os.path.isdir( os.path.join( folder, item, 'backup' ) ):
            #print item
            list.append( item )

    list.sort( reverse = sort_reverse )
    return list


def get_nonsnapshots_list_in_folder( folder, sort_reverse = True ):
    biglist = []
    #print folder

    try:
        biglist = os.listdir( folder )
        #print biglist
    except:
        pass

    list = []

    for item in biglist:
        #print item + ' ' + str(len( item ))
        if len( item ) != 15 and len( item ) != 19:
            list.append( item )
        else: 
            if os.path.isdir( os.path.join( folder, item, 'backup' ) ):
                #print item
                continue
            else:
                list.append( item )

    list.sort( reverse = sort_reverse )
    return list


def move_snapshots_folder( old_folder, new_folder ):
    '''Moves all the snapshots from one folder to another'''
    print "\nMove snapshots from %s to %s" %( old_folder, new_folder )	

    # Fetch a list with snapshots for verification
    snapshots_to_move = get_snapshots_list_in_folder( old_folder )
    snapshots_already_there = []
    if os.path.exists( new_folder ) == True:
        snapshots_already_there = get_snapshots_list_in_folder( new_folder )
    else:
        tools.make_dirs( new_folder )	
    print "To move: %s" % snapshots_to_move
    print "Already there: %s" % snapshots_already_there
    snapshots_expected = snapshots_to_move + snapshots_already_there
    print "Snapshots expected: %s" % snapshots_expected
    
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
        if len( snapshots_already_there ) > 0:
            first_snapshot_path = os.path.join( new_folder, snapshots_to_move[ len( snapshots_to_move ) - 1 ] )
            snapshot_to_hardlink_path =  os.path.join( new_folder, snapshots_already_there[0] )
            _execute( "find \"%s\" -type d -exec chmod u+wx {} \\;" % snapshot_to_hardlink_path )
            cmd = "cp -al \"%s\" \"%s\"" % ( snapshot_to_hardlink_path, first_snapshot_path )
            _execute( cmd )
    
        # Prepare excludes
        nonsnapshots = get_nonsnapshots_list_in_folder( old_folder )
        print "Nonsnapshots: %s" % nonsnapshots
        items = []
        for nonsnapshot in nonsnapshots:
            for item in items:
                if nonsnapshot == item:
                    break
            items.append( "--exclude=\"%s\"" % nonsnapshot )
        rsync_exclude = ' '.join( items )
        #print rsync_exclude
        
        # Move move move
        cmd = "rsync -aEAXHv --delete " + old_folder + " " + new_folder + " " + rsync_exclude
        _execute( cmd )
        _execute ( "find \"%s\" \"%s\" -type d -exec chmod a-w {} \\;" % ( snapshots_to_hardlink_path, first_snapshot_path ) )
        
    # Remove old ones
    snapshots_not_moved = []
    for snapshot in snapshots_to_move:
        if os.path.exists( os.path.join( new_folder, snapshot, "backup" ) ):
            if os.path.exists( os.path.join( old_folder, snapshot) ):
                print "Remove: %s" %snapshot
                path_to_remove = os.path.join( old_folder, snapshot )
                cmd = "find \"%s\" -type d -exec chmod u+wx {} \\;" % path_to_remove #Debian patch
                _execute( cmd )
                cmd = "rm -rfv \"%s\"" % path_to_remove
                _execute( cmd )
            else:
                print "%s was already removed" %snapshot
        else: 
            snapshots_not_moved.append( snapshot )
                
    # Check snapshot list
    if len( snapshots_not_moved ) == 0:
        print "Succes!\n"
        return True
    else:
        print "Error! Not moved: %s\n" %snapshots_not_moved
        return False


def _execute( cmd, callback = None, user_data = None ):
    ret_val = 0

    if callback is None:
        ret_val = os.system( cmd )
    else:
        pipe = os.popen( cmd, 'r' )

        while True:
            line = temp_failure_retry( pipe.readline )
            if len( line ) == 0:
                break
            callback( line.strip(), user_data )

        ret_val = pipe.close()
        if ret_val is None:
            ret_val = 0

    if ret_val != 0:
        print "Command \"%s\" returns %s" % ( cmd, ret_val ) 
    else:
        print "Command \"%s\" returns %s" % ( cmd, ret_val ) 

    return ret_val


def is_process_alive( pid ):
    try:
        os.kill( pid, 0 )	#this will raise an exception if the pid is not valid
    except:
        return False

    return True


def get_rsync_caps():
    data = read_command_output( 'rsync --version' )
    si = data.find( 'Capabilities:' )
    if si < 0:
        return []
    si = data.find( '\n', si )
    if si < 0:
        return []
    ei = data.find( '\n\n', si )
    if ei < 0:
        return []

    data = data[ si + 1 : ei - 1 ]
    data = data.split( '\n' )
    all_caps = ''

    for line in data:
        line = line.strip()
        if len( line ) <= 0:
            continue
        if len( all_caps ) > 0:
            all_caps = all_caps + ' '
        all_caps = all_caps + line

    caps = all_caps.split( ", " )
    #print caps
    #print ( "ACLs" in get_rsync_caps() )
    return caps


def use_rsync_fast( config ):
    return not (config.preserve_acl() or config.preserve_xattr())


def get_rsync_prefix( config, no_perms = True ):
    caps = get_rsync_caps()
    #cmd = 'rsync -aEH'
    cmd = 'rsync'
    cmd = cmd + ' -rtDH'

    if config.use_checksum():
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

    if config.get_snapshots_mode() == 'ssh':
        ssh_port = config.get_ssh_port()
        ssh_cipher = config.get_ssh_cipher()
        if ssh_cipher == 'default':
            ssh_cipher_suffix = ''
        else:
            ssh_cipher_suffix = '-c %s' % ssh_cipher
        cmd = cmd + ' --rsh="ssh -p %s %s"' % ( str(ssh_port), ssh_cipher_suffix)
            
    return cmd + ' '


def temp_failure_retry(func, *args, **kwargs): 
    while True:
        try:
            return func(*args, **kwargs)
        except (os.error, IOError), ex:
            if ex.errno == errno.EINTR:
                continue
            else:
                raise


def _get_md5sum_from_path(path):
    '''return md5sum of path, af available system command md5sum()'''   
    if check_command("md5sum"):
        status,output = commands.getstatusoutput("md5sum '" + path + "'")
        if status == 0:
            md5sum = output.split(" ")[0]
            return md5sum
    # md5sum unavailable or command failed; raise an exception ? a message ? use std lib ? 
    print "warning: md5sum() fail ! used (st_size, st_mttime) instead of md5sum."
    obj  = os.stat(path)
    unique_key = (obj.st_size, int(obj.st_mtime))    
    return unique_key
        
def check_cron_pattern(str):
    '''check if str look like '0,10,13,15,17,20,23' or '*/6' '''
    if str.find(' ') >= 0:
        return False
    try:
        if str.startswith('*/'):
            if int(str[2:]) <= 24:
                return True
            else:
                return False
        list = str.split(',')
        for s in list:
            if int(s) <= 24:
                continue
            else:
                return False
        return True
    except ValueError:
        return False

def check_mountpoint(path):
    '''return True if path is a mountpoint'''
    try:
        subprocess.check_call(['mountpoint', path], stdout=open(os.devnull, 'w'))
    except subprocess.CalledProcessError:
        return False
    return True

def check_home_encrypt():
    '''return True if users home is encrypted'''
    home = os.path.expanduser('~')
    if not check_mountpoint(home):
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
        mount = subprocess.Popen(['mount'], stdout=subprocess.PIPE).communicate()[0]
        r = re.compile('^encfs on %s type fuse' % home)
        for line in mount.split('\n'):
            if r.match(line):
                return True
    return False

def load_env(cfg):
    env = os.environ.copy()
    env_file = configfile.ConfigFile()
    env_file.load(cfg.get_cron_env_file(), maxsplit = 1)
    for key in env_file.get_keys():
        value = env_file.get_str_value(key)
        if not value:
            continue
        if not key in env.keys():
            os.environ[key] = value
    del(env_file)

def save_env(cfg):
    """
    save environ variables to file that are needed by cron
    to connect to keyring. This will only work if the user is logged in.
    """
    env = os.environ.copy()
    env_file = configfile.ConfigFile()
    #ubuntu
    set_env_key(env, env_file, 'GNOME_KEYRING_CONTROL')
    set_env_key(env, env_file, 'DBUS_SESSION_BUS_ADDRESS')
    set_env_key(env, env_file, 'DISPLAY')
    #debian
    set_env_key(env, env_file, 'XAUTHORITY')
    
    env_file.save(cfg.get_cron_env_file())
    del(env_file)

def set_env_key(env, env_file, key):
    if key in env.keys():
        env_file.set_str_value(key, env[key])

class UniquenessSet:
    '''a class to check for uniqueness of snapshots of the same [item]'''
    
    def __init__(self, dc = False, follow_symlink = False): 
        self.deep_check = dc
        self.follow_sym = follow_symlink
        self._uniq_dict = {}      # if not self._uniq_dict[size] -> size already checked with md5sum
        self._size_inode = set()  # if (size,inode) in self._size_inode -> path is a hlink 
        
    def check_for(self, input_path, verb = False):
        '''store a unique key for path, return True if path is unique'''
        # follow symlinks ?
        path = input_path
        if self.follow_sym and os.path.islink(input_path):
            path = os.readlink(input_path)
        # check
        if self.deep_check:
            dum = os.stat(path)
            size,inode  = dum.st_size, dum.st_ino
            # is it a hlink ?
            if (size, inode) in self._size_inode: 
                if verb: print "[deep test] : skip, it's a duplicate (size, inode)" 
                return False   
            self._size_inode.add( (size,inode) )
            if size not in self._uniq_dict.keys(): 
                # first item of that size
                unique_key = size
                if verb: print "[deep test] : store current size ?" 
            else: 
                prev = self._uniq_dict[size]
                if prev:
                    # store md5sum instead of previously stored size
                    md5sum_prev = _get_md5sum_from_path(prev)     
                    self._uniq_dict[size] = None
                    self._uniq_dict[md5sum_prev] = prev      
                    if verb: 
                        print "[deep test] : size duplicate, remove the size, store prev md5sum"                     
                unique_key = _get_md5sum_from_path(path) 
                if verb: print "[deep test] : store current md5sum ?" 
        else:
            # store a tuple of (size, modification time)
            obj  = os.stat(path)
            unique_key = (obj.st_size, int(obj.st_mtime))
            # print "..", path, unique_key 
        # store if not already present, then return True
        if unique_key not in self._uniq_dict.keys():
            if verb: print " >> ok, store !"             
            self._uniq_dict[unique_key] = path
            return True    
        if verb: print " >> skip (it's a duplicate)" 
        return False

class Timeout(Exception):
    pass

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
