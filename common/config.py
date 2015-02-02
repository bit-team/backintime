#    Back In Time
#    Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import datetime
import gettext
import socket
import random
import re
try:
    import pwd
except ImportError:
    import getpass
    pwd = None

import configfile
import tools
import logger
import mount
import sshtools
import encfstools
##import dummytools
import password
import pluginmanager

_=gettext.gettext

gettext.bindtextdomain( 'backintime', '/usr/share/locale' )
gettext.textdomain( 'backintime' )


class Config( configfile.ConfigFileWithProfiles ):
    APP_NAME = 'Back In Time'
    VERSION = '1.1.1'
    COPYRIGHT = 'Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze'
    CONFIG_VERSION = 5

    NONE = 0
    AT_EVERY_BOOT = 1
    _5_MIN = 2
    _10_MIN = 4
    _30_MIN = 7
    HOUR = 10
    _1_HOUR = 10
    _2_HOURS = 12
    _4_HOURS = 14
    _6_HOURS = 16
    _12_HOURS = 18
    CUSTOM_HOUR = 19
    DAY = 20
    REPEATEDLY = 25
    UDEV = 27
    WEEK = 30
    MONTH = 40
    YEAR = 80

    DISK_UNIT_MB = 10
    DISK_UNIT_GB = 20

    AUTOMATIC_BACKUP_MODES = {
                NONE : _('Disabled'),
                AT_EVERY_BOOT : _('At every boot/reboot'),
                _5_MIN: _('Every 5 minutes'),
                _10_MIN: _('Every 10 minutes'),
                _30_MIN: _('Every 30 minutes'),
                _1_HOUR : _('Every hour'),
                _2_HOURS : _('Every 2 hours'),
                _4_HOURS : _('Every 4 hours'),
                _6_HOURS : _('Every 6 hours'),
                _12_HOURS : _('Every 12 hours'),
                CUSTOM_HOUR : _('Custom Hours'),
                DAY : _('Every Day'),
                REPEATEDLY : _('Repeatedly (anacron)'),
                UDEV : _('When drive get connected (udev)'),
                WEEK : _('Every Week'),
                MONTH : _('Every Month')
                }

    REMOVE_OLD_BACKUP_UNITS = {
                DAY : _('Day(s)'),
                WEEK : _('Week(s)'),
                YEAR : _('Year(s)')
                }

    REPEATEDLY_UNITS = {
                HOUR : _('Hour(s)'),
                DAY : _('Day(s)'),
                WEEK : _('Week(s)'),
                MONTH : _('Month(s)')
                }

    MIN_FREE_SPACE_UNITS = { DISK_UNIT_MB : 'Mb', DISK_UNIT_GB : 'Gb' }

    DEFAULT_EXCLUDE = [ '.gvfs', '.cache/*', '.thumbnails*', '[Tt]rash*',       \
                        '*.backup*', '*~', '.dropbox*', '/proc/*', '/sys/*',    \
                        '/dev/*', '/run/*', '/etc/mtab',                        \
                        '/var/cache/apt/archives/*.deb', 'lost+found/*',        \
                        '/tmp/*', '/var/tmp/*', '/var/backups/*', '.Private' ]

    DEFAULT_RUN_NICE_FROM_CRON   = True
    DEFAULT_RUN_NICE_ON_REMOTE   = False
    DEFAULT_RUN_IONICE_FROM_CRON = True
    DEFAULT_RUN_IONICE_FROM_USER = False
    DEFAULT_RUN_IONICE_ON_REMOTE = False
    DEFAULT_RUN_NOCACHE_ON_LOCAL  = False
    DEFAULT_RUN_NOCACHE_ON_REMOTE = False

    exp = _(' EXPERIMENTAL!')
    SNAPSHOT_MODES = {
                #mode           : (<mounttools>,            'ComboBox Text',        need_pw|lbl_pw_1,       need_2_pw|lbl_pw_2 ),
                'local'         : (None,                    _('Local'),             False,                  False ),
                'ssh'           : (sshtools.SSH,            _('SSH'),               _('SSH private key'),   False ),
                'local_encfs'   : (encfstools.EncFS_mount,  _('Local encrypted'),   _('Encryption'),        False ),
                'ssh_encfs'     : (encfstools.EncFS_SSH,    _('SSH encrypted'),     _('SSH private key'),   _('Encryption') )
                ##'dummy'       : (dummytools.Dummy,        'Dummy',                'Dummy',                False )
                }

    SSH_CIPHERS =  {'default':    _('Default'),
                    'aes128-ctr': _('AES128-CTR'),
                    'aes192-ctr': _('AES192-CTR'),
                    'aes256-ctr': _('AES256-CTR'),
                    'arcfour256': _('ARCFOUR256'),
                    'arcfour128': _('ARCFOUR128'),
                    'aes128-cbc': _('AES128-CBC'),
                    '3des-cbc':   _('3DES-CBC'),
                    'blowfish-cbc': _('Blowfish-CBC'),
                    'cast128-cbc': _('Cast128-CBC'),
                    'aes192-cbc': _('AES192-CBC'),
                    'aes256-cbc': _('AES256-CBC'),
                    'arcfour':    _('ARCFOUR') }

    ENCODE = encfstools.Bounce()
    PLUGIN_MANAGER = pluginmanager.PluginManager()

    def __init__( self, config_path = None ):
        configfile.ConfigFileWithProfiles.__init__( self, _('Main profile') )

        self._APP_PATH =  os.path.dirname( os.path.abspath( os.path.dirname( __file__ ) ) )
        self._DOC_PATH = '/usr/share/doc/backintime-common'
        if os.path.exists( os.path.join( self._APP_PATH, 'LICENSE' ) ):
            self._DOC_PATH = self._APP_PATH

        self._GLOBAL_CONFIG_PATH = '/etc/backintime/config'

        HOME_FOLDER = os.path.expanduser( '~' )
        DATA_FOLDER = '.local/share'
        CONFIG_FOLDER = '.config'
        BIT_FOLDER = 'backintime'
        self._LOCAL_DATA_FOLDER = os.path.join(HOME_FOLDER, DATA_FOLDER, BIT_FOLDER)
        self._LOCAL_CONFIG_FOLDER = os.path.join(HOME_FOLDER, CONFIG_FOLDER, BIT_FOLDER)

        self._MOUNT_ROOT = os.path.join(DATA_FOLDER, BIT_FOLDER, 'mnt')
        self._LOCAL_MOUNT_ROOT = os.path.join(HOME_FOLDER, self._MOUNT_ROOT)

        tools.make_dirs( self._LOCAL_CONFIG_FOLDER )
        tools.make_dirs( self._LOCAL_DATA_FOLDER )

        self._DEFAULT_CONFIG_PATH = os.path.join( self._LOCAL_CONFIG_FOLDER, 'config' )
        if config_path is None:
            self._LOCAL_CONFIG_PATH = self._DEFAULT_CONFIG_PATH
        else:
            self._LOCAL_CONFIG_PATH = config_path
        old_path = os.path.join( self._LOCAL_CONFIG_FOLDER, 'config2' )

        if os.path.exists( old_path ):
            if os.path.exists( self._LOCAL_CONFIG_PATH ):
                os.system( "rm \"%s\"" % old_path )
            else:
                os.system( "mv \"%s\" \"%s\"" % ( old_path, self._LOCAL_CONFIG_PATH ) )

        self.load( self._GLOBAL_CONFIG_PATH )
        self.append( self._LOCAL_CONFIG_PATH )

        if self.get_int_value( 'config.version', self.CONFIG_VERSION ) < self.CONFIG_VERSION:

            if self.get_int_value( 'config.version', self.CONFIG_VERSION ) < 2:
                #remap old items
                self.remap_key( 'BASE_BACKUP_PATH', 'snapshots.path' )
                self.remap_key( 'INCLUDE_FOLDERS', 'snapshots.include_folders' )
                self.remap_key( 'EXCLUDE_PATTERNS', 'snapshots.exclude_patterns' )
                self.remap_key( 'AUTOMATIC_BACKUP', 'snapshots.automatic_backup_mode' )
                self.remap_key( 'REMOVE_OLD_BACKUPS', 'snapshots.remove_old_snapshots.enabled' )
                self.remap_key( 'REMOVE_OLD_BACKUPS_VALUE', 'snapshots.remove_old_snapshots.value' )
                self.remap_key( 'REMOVE_OLD_BACKUPS_UNIT', 'snapshots.remove_old_snapshots.unit' )
                self.remap_key( 'MIN_FREE_SPACE', 'snapshots.min_free_space.enabled' )
                self.remap_key( 'MIN_FREE_SPACE_VALUE', 'snapshots.min_free_space.value' )
                self.remap_key( 'MIN_FREE_SPACE_UNIT', 'snapshots.min_free_space.unit' )
                self.remap_key( 'DONT_REMOVE_NAMED_SNAPSHOTS', 'snapshots.dont_remove_named_snapshots' )
                self.remap_key( 'DIFF_CMD', 'gnome.diff.cmd' )
                self.remap_key( 'DIFF_CMD_PARAMS', 'gnome.diff.params' )
                self.remap_key( 'LAST_PATH', 'gnome.last_path' )
                self.remap_key( 'MAIN_WINDOW_X', 'gnome.main_window.x' )
                self.remap_key( 'MAIN_WINDOW_Y', 'gnome.main_window.y' )
                self.remap_key( 'MAIN_WINDOW_WIDTH', 'gnome.main_window.width' )
                self.remap_key( 'MAIN_WINDOW_HEIGHT', 'gnome.main_window.height' )
                self.remap_key( 'MAIN_WINDOW_HPANED1_POSITION', 'gnome.main_window.hpaned1' )
                self.remap_key( 'MAIN_WINDOW_HPANED2_POSITION', 'gnome.main_window.hpaned2' )

            if self.get_int_value( 'config.version', self.CONFIG_VERSION ) < 3:
                self.remap_key( 'snapshots.path', 'profile1.snapshots.path' )
                self.remap_key( 'snapshots.include_folders', 'profile1.snapshots.include_folders' )
                self.remap_key( 'snapshots.exclude_patterns', 'profile1.snapshots.exclude_patterns' )
                self.remap_key( 'snapshots.automatic_backup_mode', 'profile1.snapshots.automatic_backup_mode' )
                self.remap_key( 'snapshots.remove_old_snapshots.enabled', 'profile1.snapshots.remove_old_snapshots.enabled' )
                self.remap_key( 'snapshots.remove_old_snapshots.value', 'profile1.snapshots.remove_old_snapshots.value' )
                self.remap_key( 'snapshots.remove_old_snapshots.unit', 'profile1.snapshots.remove_old_snapshots.unit' )
                self.remap_key( 'snapshots.min_free_space.enabled', 'profile1.snapshots.min_free_space.enabled' )
                self.remap_key( 'snapshots.min_free_space.value', 'profile1.snapshots.min_free_space.value' )
                self.remap_key( 'snapshots.min_free_space.unit', 'profile1.snapshots.min_free_space.unit' )
                self.remap_key( 'snapshots.dont_remove_named_snapshots', 'profile1.snapshots.dont_remove_named_snapshots' )

            if self.get_int_value( 'config.version', self.CONFIG_VERSION ) < 4:
                # version 4 uses as path backintime/machine/user/profile_id
                # but must be able to read old paths
                profiles = self.get_profiles()
                self.set_bool_value( 'update.other_folders', True )
                logger.info( "Update to config version 4: other snapshot locations" )

                for profile_id in profiles:
                    old_folder = self.get_snapshots_path( profile_id )
                    other_folder = os.path.join( old_folder, 'backintime' )
                    other_folder_key = 'profile' + str( profile_id ) + '.snapshots.other_folders'
                    self.set_str_value( other_folder_key, other_folder )
                    tag = str( random.randint(100, 999) )
                    logger.info( "Random tag for profile %s: %s" %( profile_id, tag ) )
                    self.set_profile_str_value( 'snapshots.tag', tag, profile_id )

            if self.get_int_value( 'config.version', self.CONFIG_VERSION ) < 5:
                logger.info( "Update to config version 5: other snapshot locations" )
                profiles = self.get_profiles()
                for profile_id in profiles:
                    #change include
                    old_values = self.get_include_v4( profile_id )
                    values = []
                    for value in old_values:
                        values.append( ( value, 0 ) )
                    self.set_include( values, profile_id )

                    #change exclude
                    old_values = self.get_exclude_v4( profile_id )
                    self.set_exclude( old_values, profile_id )

                    #remove keys
                    self.remove_profile_key( 'snapshots.include_folders', profile_id )
                    self.remove_profile_key( 'snapshots.exclude_patterns', profile_id )

            self.set_int_value( 'config.version', self.CONFIG_VERSION )
            self.save()

        self.current_hash_id = 'local'
        self.pw = None
        self.force_use_checksum = False
        self.xWindowId = None
        self.inhibitCookie = None
        self.setupUdev = tools.SetupUdev()

    def save( self ):
        configfile.ConfigFile.save( self, self._LOCAL_CONFIG_PATH )

    def check_config( self ):
        profiles = self.get_profiles()

        checked_profiles = []

        for profile_id in profiles:
            profile_name = self.get_profile_name( profile_id )
            snapshots_path = self.get_snapshots_path( profile_id )

            #check snapshots path
            if not snapshots_path:
                self.notify_error( _('Profile: "%s"') % profile_name + '\n' + _('Snapshots folder is not valid !') )
                return False

            #check include
            include_list = self.get_include( profile_id )

            if not include_list:
                self.notify_error( _('Profile: "%s"') % profile_name + '\n' + _('You must select at least one folder to backup !') )
                return False

            snapshots_path2 = snapshots_path + '/'

            for item in include_list:
                if item[1] != 0:
                    continue

                path = item[0]
                if path == snapshots_path:
                    self.notify_error( _('Profile: "%s"') % profile_name + '\n' + _('You can\'t include backup folder !') )
                    return False

                if len( path ) >= len( snapshots_path2 ):
                    if path[ : len( snapshots_path2 ) ] == snapshots_path2:
                        self.notify_error( _('Profile: "%s"') %  self.get_current_profile() + '\n' + _('You can\'t include a backup sub-folder !') )
                        return False

            checked_profiles.append( ( profile_id, profile_name ) )

        return True

    def get_user( self ):
        '''portable way to get username
        cc by-sa 3.0      http://stackoverflow.com/a/19865396/1139841
        author: techtonik http://stackoverflow.com/users/239247/techtonik
        '''
        if pwd:
            return pwd.getpwuid(os.geteuid()).pw_name
        else:
            return getpass.getuser()

    def get_pid(self):
        return str(os.getpid())

    def get_host(self):
        return socket.gethostname()

    def get_snapshots_path( self, profile_id = None, mode = None, tmp_mount = False ):
        if mode is None:
            mode = self.get_snapshots_mode(profile_id)
        if self.SNAPSHOT_MODES[mode][0] == None:
            #no mount needed
            #?Where to save snapshots in mode 'local'. This path must contain a 
            #?folderstructure like 'backintime/<HOST>/<USER>/<PROFILE_ID>';absolute path
            return self.get_profile_str_value( 'snapshots.path', '', profile_id )
        else:
            #mode need to be mounted; return mountpoint
            symlink = self.get_snapshots_symlink(profile_id = profile_id, tmp_mount = tmp_mount)
            return os.path.join(self._LOCAL_MOUNT_ROOT, symlink)

    def get_snapshots_full_path( self, profile_id = None, version = None ):
        '''Returns the full path for the snapshots: .../backintime/machine/user/profile_id/'''
        if version is None:
            version = self.get_int_value( 'config.version', self.CONFIG_VERSION )

        if version < 4:
            return os.path.join( self.get_snapshots_path( profile_id ), 'backintime' )
        else:
            host, user, profile = self.get_host_user_profile( profile_id )
            return os.path.join( self.get_snapshots_path( profile_id ), 'backintime', host, user, profile )

    def set_snapshots_path( self, value, profile_id = None, mode = None ):
        """Sets the snapshot path to value, initializes, and checks it"""
        if not value:
            return False

        if profile_id == None:
            profile_id = self.get_current_profile()

        if mode is None:
            mode = self.get_snapshots_mode( profile_id )

        if not os.path.isdir( value ):
            self.notify_error( _( '%s is not a folder !' ) % value )
            return False

        #Initialize the snapshots folder
        print("Check snapshot folder: %s" % value)

        host, user, profile = self.get_host_user_profile( profile_id )

        full_path = os.path.join( value, 'backintime', host, user, profile )
        if not os.path.isdir( full_path ):
            print("Create folder: %s" % full_path)
            tools.make_dirs( full_path )
            if not os.path.isdir( full_path ):
                self.notify_error( _( 'Can\'t write to: %s\nAre you sure you have write access ?' % value ) )
                return False

            path1 = os.path.join( value, 'backintime' )
            os.system( "chmod a+rwx \"%s\"" % path1 )

            path1 = os.path.join( value, 'backintime', host )
            os.system( "chmod a+rwx \"%s\"" % path1 )

        #Test write access for the folder
        check_path = os.path.join( full_path, 'check' )
        tools.make_dirs( check_path )
        if not os.path.isdir( check_path ):
            self.notify_error( _( 'Can\'t write to: %s\nAre you sure you have write access ?' % full_path ) )
            return False

        os.rmdir( check_path )
        if self.SNAPSHOT_MODES[mode][0] is None:
            self.set_profile_str_value( 'snapshots.path', value, profile_id )
        return True

    def get_snapshots_mode( self, profile_id = None ):
        #?Use mode (or backend) for this snapshot. Look at 'man backintime' 
        #?section 'Modes'.;local|local_encfs|ssh|ssh_encfs
        return self.get_profile_str_value( 'snapshots.mode', 'local', profile_id )

    def set_snapshots_mode( self, value, profile_id = None ):
        self.set_profile_str_value( 'snapshots.mode', value, profile_id )

    def get_snapshots_symlink(self, profile_id = None, tmp_mount = False):
        if profile_id is None:
            profile_id = self.current_profile_id
        symlink = '%s_%s' % (profile_id, self.get_pid())
        if tmp_mount:
            symlink = 'tmp_%s' % symlink
        return symlink

    def set_current_hash_id(self, hash_id):
        self.current_hash_id = hash_id

    def get_hash_collision(self):
        #?Internal value used to prevent hash collisions on mountpoints. Do not change this.
        return self.get_int_value( 'global.hash_collision', 0 )

    def increment_hash_collision(self):
        value = self.get_hash_collision() + 1
        self.set_int_value( 'global.hash_collision', value )

    def get_snapshots_path_ssh( self, profile_id = None ):
        #?Snapshot path on remote host. If the path is relative (no leading '/') 
        #?it will start from remote Users homedir. An empty path will be replaced 
        #?with './'. This path must contain a folderstructure like 
        #?'backintime/<HOST>/<USER>/<PROFILE_ID>';absolute or relative path
        return self.get_profile_str_value( 'snapshots.ssh.path', '', profile_id )

    def get_snapshots_full_path_ssh( self, profile_id = None, version = None ):
        '''Returns the full path for the snapshots: .../backintime/machine/user/profile_id/'''
        if version is None:
            version = self.get_int_value( 'config.version', self.CONFIG_VERSION )
        path = self.get_snapshots_path_ssh( profile_id )
        if not path:
            path = './'
        if version < 4:
            return os.path.join( path, 'backintime' )
        else:
            host, user, profile = self.get_host_user_profile( profile_id )
            return os.path.join( path, 'backintime', host, user, profile )

    def set_snapshots_path_ssh( self, value, profile_id = None ):
        self.set_profile_str_value( 'snapshots.ssh.path', value, profile_id )
        return True

    def get_ssh_host( self, profile_id = None ):
        #?Remote host used for mode 'ssh' and 'ssh_encfs'.;IP or domain address
        return self.get_profile_str_value( 'snapshots.ssh.host', '', profile_id )

    def set_ssh_host( self, value, profile_id = None ):
        self.set_profile_str_value( 'snapshots.ssh.host', value, profile_id )

    def get_ssh_port( self, profile_id = None ):
        #?SSH Port on remote host.;0-65535
        return self.get_profile_int_value( 'snapshots.ssh.port', '22', profile_id )

    def set_ssh_port( self, value, profile_id = None ):
        self.set_profile_int_value( 'snapshots.ssh.port', value, profile_id )

    def get_ssh_cipher( self, profile_id = None ):
        #?Cipher that is used for encrypting the SSH tunnel. Depending on the 
        #?environment (network bandwidth, cpu and hdd performance) a different 
        #?cipher might be faster.;default | aes192-cbc | aes256-cbc | aes128-ctr | 
        #?aes192-ctr | aes256-ctr | arcfour | arcfour256 | arcfour128 | aes128-cbc | 
        #?3des-cbc | blowfish-cbc | cast128-cbc
        return self.get_profile_str_value( 'snapshots.ssh.cipher', 'default', profile_id )

    def set_ssh_cipher( self, value, profile_id = None ):
        self.set_profile_str_value( 'snapshots.ssh.cipher', value, profile_id )

    def get_ssh_user( self, profile_id = None ):
        #?Remote SSH user;;local users name
        return self.get_profile_str_value( 'snapshots.ssh.user', self.get_user(), profile_id )

    def set_ssh_user( self, value, profile_id = None ):
        self.set_profile_str_value( 'snapshots.ssh.user', value, profile_id )

    def get_ssh_host_port_user_path_cipher(self, profile_id = None ):
        host = self.get_ssh_host(profile_id)
        port = self.get_ssh_port(profile_id)
        user = self.get_ssh_user(profile_id)
        path = self.get_snapshots_path_ssh(profile_id)
        cipher = self.get_ssh_cipher(profile_id)
        if not path:
            path = './'
        return (host, port, user, path, cipher)

    def get_ssh_private_key_file(self, profile_id = None):
        ssh = self.get_ssh_private_key_folder()
        default = ''
        for file in ['id_dsa', 'id_rsa', 'identity']:
            private_key = os.path.join(ssh, file)
            if os.path.isfile(private_key):
                default = private_key
                break
        #?Private key file used for password-less authentication on remote host.
        #?;absolute path to private key file;~/.ssh/id_dsa
        file = self.get_profile_str_value( 'snapshots.ssh.private_key_file', default, profile_id )
        if file:
            return file
        return default

    def get_ssh_private_key_folder(self):
        return os.path.join(os.path.expanduser('~'), '.ssh')

    def set_ssh_private_key_file( self, value, profile_id = None ):
        self.set_profile_str_value( 'snapshots.ssh.private_key_file', value, profile_id )

    #ENCFS
    def get_local_encfs_path( self, profile_id = None ):
        #?Where to save snapshots in mode 'local_encfs'. The encrypted path must contian 
        #?a folderstructure like 'backintime/<HOST>/<USER>/<PROFILE_ID>';absolute path
        return self.get_profile_str_value( 'snapshots.local_encfs.path', '', profile_id )

    def set_local_encfs_path( self, value, profile_id = None ):
        self.set_profile_str_value( 'snapshots.local_encfs.path', value, profile_id )

##	def get_dummy_host( self, profile_id = None ):
##		return self.get_profile_str_value( 'snapshots.dummy.host', '', profile_id )
##
##	def set_dummy_host( self, value, profile_id = None ):
##		self.set_profile_str_value( 'snapshots.dummy.host', value, profile_id )
##
##	def get_dummy_port( self, profile_id = None ):
##		return self.get_profile_int_value( 'snapshots.dummy.port', '22', profile_id )
##
##	def set_dummy_port( self, value, profile_id = None ):
##		self.set_profile_int_value( 'snapshots.dummy.port', value, profile_id )
##
##	def get_dummy_user( self, profile_id = None ):
##		return self.get_profile_str_value( 'snapshots.dummy.user', self.get_user(), profile_id )
##
##	def set_dummy_user( self, value, profile_id = None ):
##		self.set_profile_str_value( 'snapshots.dummy.user', value, profile_id )

    def get_password_save( self, profile_id = None, mode = None ):
        if mode is None:
            mode = self.get_snapshots_mode(profile_id)
        #?Save password to system keyring (gnome-keyring or kwallet). 
        #?<MODE> must be the same as \fIprofile<N>.snapshots.mode\fR
        return self.get_profile_bool_value( 'snapshots.%s.password.save' % mode, False, profile_id )

    def set_password_save( self, value, profile_id = None, mode = None ):
        if mode is None:
            mode = self.get_snapshots_mode(profile_id)
        self.set_profile_bool_value( 'snapshots.%s.password.save' % mode, value, profile_id )

    def get_password_use_cache( self, profile_id = None, mode = None ):
        if mode is None:
            mode = self.get_snapshots_mode(profile_id)
        default = not tools.check_home_encrypt()
        #?Cache password in RAM so it can be read by cronjobs. 
        #?Security issue: root might be able to read that password, too. 
        #?<MODE> must be the same as \fIprofile<N>.snapshots.mode\fR;;true if home is not encrypted
        return self.get_profile_bool_value( 'snapshots.%s.password.use_cache' % mode, default, profile_id )

    def set_password_use_cache( self, value, profile_id = None, mode = None ):
        if mode is None:
            mode = self.get_snapshots_mode(profile_id)
        self.set_profile_bool_value( 'snapshots.%s.password.use_cache' % mode, value, profile_id )

    def get_password( self, parent = None, profile_id = None, mode = None, pw_id = 1, only_from_keyring = False ):
        if self.pw is None:
            self.pw = password.Password(self)
        if profile_id is None:
            profile_id = self.get_current_profile()
        if mode is None:
            mode = self.get_snapshots_mode(profile_id)
        return self.pw.get_password(parent, profile_id, mode, pw_id, only_from_keyring)

    def set_password( self, password, profile_id = None, mode = None, pw_id = 1 ):
        if self.pw is None:
            self.pw = password.Password(self)
        if profile_id is None:
            profile_id = self.get_current_profile()
        if mode is None:
            mode = self.get_snapshots_mode(profile_id)
        self.pw.set_password(password, profile_id, mode, pw_id)

    def mode_need_password(self, mode, pw_id = 1):
        need_pw = self.SNAPSHOT_MODES[mode][pw_id + 1]
        if need_pw is False:
            return False
        return True

    def get_keyring_service_name( self, profile_id = None, mode = None, pw_id = 1 ):
        if mode is None:
            mode = self.get_snapshots_mode(profile_id)
        if pw_id > 1:
            return 'backintime/%s_%s' % (mode, pw_id)
        return 'backintime/%s' % mode

    def get_keyring_user_name( self, profile_id = None ):
        if profile_id is None:
            profile_id = self.get_current_profile()
        return 'profile_id_%s' % profile_id

    def get_default_host_user_profile( self, profile_id = None ):
        host = socket.gethostname()
        user = self.get_user()
        profile = profile_id
        if profile is None:
            profile = self.get_current_profile()

        return ( host, user, profile )

    def get_host_user_profile( self, profile_id = None ):
        default_host, default_user, default_profile = self.get_default_host_user_profile( profile_id )
        #?Set Host for snapshot path;;local hostname
        host = self.get_profile_str_value( 'snapshots.path.host', default_host, profile_id )

        #?Set User for snapshot path;;local username
        user = self.get_profile_str_value( 'snapshots.path.user', default_user, profile_id )

        #?Set Profile-ID for snapshot path;1-99999;current Profile-ID
        profile = self.get_profile_str_value( 'snapshots.path.profile', default_profile, profile_id )

        return ( host, user, profile )

    def set_host_user_profile( self, host, user, profile, profile_id = None ):
        self.set_profile_str_value( 'snapshots.path.host', host, profile_id )
        self.set_profile_str_value( 'snapshots.path.user', user, profile_id )
        self.set_profile_str_value( 'snapshots.path.profile', profile, profile_id )

    def get_other_folders_paths( self, profile_id = None ):
        '''Returns the other snapshots folders paths as a list'''
        #?!ignore this in manpage
        value = self.get_profile_str_value( 'snapshots.other_folders', '', profile_id )
        if not value:
            return []

        paths = []

        for item in value.split(':'):
            fields = item.split( '|' )

            path = os.path.expanduser( item )
            path = os.path.abspath( path )

            paths.append( ( path ) )

        return paths

    def get_include_v4( self, profile_id = None ):
        #?!ignore this in manpage
        value = self.get_profile_str_value( 'snapshots.include_folders', '', profile_id )
        if not value:
            return []

        paths = []

        for item in value.split(':'):
            fields = item.split( '|' )

            path = os.path.expanduser( fields[0] )
            path = os.path.abspath( path )

            if len( fields ) >= 2:
                automatic_backup_mode = int( fields[1] )
            else:
                automatic_backup_mode = self.get_automatic_backup_mode()

            paths.append( path )

        return paths

    def get_include( self, profile_id = None ):
        #?Quantity of include entrys.;1-99999;\-1
        size = self.get_profile_int_value( 'snapshots.include.size', -1, profile_id )
        if size <= 0:
            return []

        include = []

        for i in range( 1, size + 1 ):
            #?Include this file or folder. <I> must be a counter 
            #?starting with 1;absolute path
            value = self.get_profile_str_value( "snapshots.include.%s.value" % i, '', profile_id )
            if value:
                #?Specify if \fIprofile<N>.snapshots.include.<I>.value\fR 
                #?is a folder (0) or a file (1).;0|1
                type = self.get_profile_int_value( "snapshots.include.%s.type" % i, 0, profile_id )
                include.append( ( value, type ) )

        return include

    def set_include( self, list_, profile_id = None ):
        old_size = self.get_profile_int_value( 'snapshots.include.size', 0, profile_id )

        counter = 0
        for value in list_:
            if value[0]:
                counter = counter + 1
                self.set_profile_str_value( "snapshots.include.%s.value" % counter, value[0], profile_id )
                self.set_profile_int_value( "snapshots.include.%s.type" % counter, value[1], profile_id )

        self.set_profile_int_value( 'snapshots.include.size', counter, profile_id )

        if counter < old_size:
            for i in range( counter + 1, old_size + 1 ):
                self.remove_profile_key( "snapshots.include.%s.value" % i, profile_id )
                self.remove_profile_key( "snapshots.include.%s.type" % i, profile_id )

    def get_exclude_v4( self, profile_id = None ):
        '''Gets the exclude patterns: conf version 4'''
        #?!ignore this in manpage
        value = self.get_profile_str_value( 'snapshots.exclude_patterns', '.gvfs:.cache*:[Cc]ache*:.thumbnails*:[Tt]rash*:*.backup*:*~', profile_id )
        if not value:
            return []
        return value.split( ':' )

    def get_exclude( self, profile_id = None ):
        '''Gets the exclude patterns'''
        #?Quantity of exclude entrys.;1-99999;\-1
        size = self.get_profile_int_value( 'snapshots.exclude.size', -1, profile_id )
        if size < 0:
            return self.DEFAULT_EXCLUDE

        exclude = []
        for i in range( 1, size + 1 ):
            #?Exclude this file or folder. <I> must be a counter 
            #?starting with 1;file, folder or pattern (relative or absolute)
            value = self.get_profile_str_value( "snapshots.exclude.%s.value" % i, '', profile_id )
            if value:
                exclude.append( value )

        return exclude

    def set_exclude( self, list_, profile_id = None ):
        old_size = self.get_profile_int_value( 'snapshots.exclude.size', 0, profile_id )

        counter = 0
        for value in list_:
            if value:
                counter = counter + 1
                self.set_profile_str_value( "snapshots.exclude.%s.value" % counter, value, profile_id )

        self.set_profile_int_value( 'snapshots.exclude.size', counter, profile_id )

        if counter < old_size:
            for i in range( counter + 1, old_size + 1 ):
                self.remove_profile_key( "snapshots.exclude.%s.value" % i, profile_id )

    def exclude_by_size_enabled(self, profile_id = None):
        #?Enable exclude files by size.
        return self.get_profile_bool_value('snapshots.exclude.bysize.enabled', False, profile_id)

    def set_exclude_by_size_enabled(self, value, profile_id = None):
        self.set_profile_bool_value('snapshots.exclude.bysize.enabled', value, profile_id)

    def exclude_by_size(self, profile_id = None):
        #?Exclude files bigger than value in Mb. 
        #?With 'Full rsync mode' disabled this will only affect new files 
        #?because for rsync this is a transfer option, not an exclude option. 
        #?So big files that has been backed up before will remain in snapshots 
        #?even if they had changed.
        return self.get_profile_int_value('snapshots.exclude.bysize.value', 500, profile_id)

    def set_exclude_by_size(self, value, profile_id = None):
        self.set_profile_int_value('snapshots.exclude.bysize.value', value, profile_id)

    def get_tag( self, profile_id = None ):
        #?!ignore this in manpage
        return self.get_profile_str_value( 'snapshots.tag', str(random.randint(100, 999)), profile_id )

    def get_automatic_backup_mode( self, profile_id = None ):
        #?Which shedule used for crontab. Note that the crontab entry is only 
        #?generated during saving in settings dialog. If you don't run a GUI 
        #?version of BackInTime you'll have to create the crontab entry on your 
        #?own.\n 0 = Disabled\n 1 = at every boot\n 2 = every 5 minute\n
        #? 4 = every 10 minute\n 7 = every 30 minute\n10 = every hour\n
        #?12 = every 2 hours\n14 = every 4 hours\n16 = every 6 hours\n
        #?18 = every 12 hours\n19 = custom defined hours\n20 = every day\n
        #?25 = daily anacron\n27 = when drive get connected\n30 = every week\n
        #?40 = every month\n80 = every year
        #?;0|1|2|4|7|10|12|14|16|18|19|20|25|27|30|40|80;0
        return self.get_profile_int_value( 'snapshots.automatic_backup_mode', self.NONE, profile_id )

    def set_automatic_backup_mode( self, value, profile_id = None ):
        self.set_profile_int_value( 'snapshots.automatic_backup_mode', value, profile_id )

    def get_automatic_backup_time( self, profile_id = None ):
        #?What time the cronjob should run? Only valid for 
        #?\fIprofile<N>.snapshots.automatic_backup_mode\fR >= 20;0-24
        return self.get_profile_int_value( 'snapshots.automatic_backup_time', 0, profile_id )

    def set_automatic_backup_time( self, value, profile_id = None ):
        self.set_profile_int_value( 'snapshots.automatic_backup_time', value, profile_id )

    def get_automatic_backup_day( self, profile_id = None ):
        #?Which day of month the cronjob should run? Only valid for 
        #?\fIprofile<N>.snapshots.automatic_backup_mode\fR >= 40;1-28
        return self.get_profile_int_value( 'snapshots.automatic_backup_day', 1, profile_id )

    def set_automatic_backup_day( self, value, profile_id = None ):
        self.set_profile_int_value( 'snapshots.automatic_backup_day', value, profile_id )

    def get_automatic_backup_weekday( self, profile_id = None ):
        #?Which day of week the cronjob should run? Only valid for 
        #?\fIprofile<N>.snapshots.automatic_backup_mode\fR = 30;1 = monday \- 7 = sunday
        return self.get_profile_int_value( 'snapshots.automatic_backup_weekday', 7, profile_id )

    def set_automatic_backup_weekday( self, value, profile_id = None ):
        self.set_profile_int_value( 'snapshots.automatic_backup_weekday', value, profile_id )

    def get_custom_backup_time( self, profile_id = None ):
        #?Custom hours for cronjob. Only valid for 
        #?\fIprofile<N>.snapshots.automatic_backup_mode\fR = 19
        #?;comma separated int (8,12,18,23) or */3;8,12,18,23
        return self.get_profile_str_value( 'snapshots.custom_backup_time', '8,12,18,23', profile_id )

    def set_custom_backup_time( self, value, profile_id = None ):
        self.set_profile_str_value( 'snapshots.custom_backup_time', value, profile_id )

    def get_automatic_backup_anacron_period(self, profile_id = None):
        #?How many units to wait between new snapshots with anacron? Only valid
        #?for \fIprofile<N>.snapshots.automatic_backup_mode\fR = 25|27
        return self.get_profile_int_value('snapshots.automatic_backup_anacron_period', 1, profile_id)

    def set_automatic_backup_anacron_period(self, value, profile_id = None):
        self.set_profile_int_value('snapshots.automatic_backup_anacron_period', value, profile_id)

    def get_automatic_backup_anacron_unit(self, profile_id = None):
        #?Units to wait between new snapshots with anacron. 
        #?10 = hours\n20 = days\n30 = weeks\n40 = months\n
        #?Only valid for \fIprofile<N>.snapshots.automatic_backup_mode\fR = 25|27;
        #?10|20|30|40;20
        return self.get_profile_int_value('snapshots.automatic_backup_anacron_unit', self.DAY, profile_id)

    def set_automatic_backup_anacron_unit(self, value, profile_id = None):
        self.set_profile_int_value('snapshots.automatic_backup_anacron_unit', value, profile_id)

    def get_remove_old_snapshots( self, profile_id = None ):
                 #?Remove all snapshots older than value + unit
        return ( self.get_profile_bool_value( 'snapshots.remove_old_snapshots.enabled', True, profile_id ),
                 #?Snapshots older than this times units will be removed
                 self.get_profile_int_value( 'snapshots.remove_old_snapshots.value', 10, profile_id ),
                 #?20 = days\n30 = weeks\n80 = years;20|30|80;80
                 self.get_profile_int_value( 'snapshots.remove_old_snapshots.unit', self.YEAR, profile_id ) )

    def keep_only_one_snapshot( self, profile_id = None ):
        #?NOT YET IMPLEMENTED. Remove all snapshots but one.
        return self.get_profile_bool_value( 'snapshots.keep_only_one_snapshot.enabled', False, profile_id )

    def set_keep_only_one_snapshot( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.keep_only_one_snapshot.enabled', value, profile_id )

    def is_remove_old_snapshots_enabled( self, profile_id = None ):
        return self.get_profile_bool_value( 'snapshots.remove_old_snapshots.enabled', True, profile_id )

    def get_remove_old_snapshots_date( self, profile_id = None ):
        enabled, value, unit = self.get_remove_old_snapshots( profile_id )
        if not enabled:
            return datetime.date( 1, 1, 1 )

        if unit == self.DAY:
            date = datetime.date.today()
            date = date - datetime.timedelta( days = value )
            return date

        if unit == self.WEEK:
            date = datetime.date.today()
            date = date - datetime.timedelta( days = date.weekday() + 7 * value )
            return date

        if unit == self.YEAR:
            date = datetime.date.today()
            return date.replace( day = 1, year = date.year - value )

        return datetime.date( 1, 1, 1 )

    def set_remove_old_snapshots( self, enabled, value, unit, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.remove_old_snapshots.enabled', enabled, profile_id )
        self.set_profile_int_value( 'snapshots.remove_old_snapshots.value', value, profile_id )
        self.set_profile_int_value( 'snapshots.remove_old_snapshots.unit', unit, profile_id )

    def get_min_free_space( self, profile_id = None ):
                 #?Remove snapshots until \fIprofile<N>.snapshots.min_free_space.value\fR 
                 #?free space is reached.
        return ( self.get_profile_bool_value( 'snapshots.min_free_space.enabled', True, profile_id ),
                 #?Keep at least value + unit free space.;1-99999
                 self.get_profile_int_value( 'snapshots.min_free_space.value', 1, profile_id ),
                 #?10 = MB\n20 = GB;10|20;20
                 self.get_profile_int_value( 'snapshots.min_free_space.unit', self.DISK_UNIT_GB, profile_id ) )

    def is_min_free_space_enabled( self, profile_id = None ):
        return self.get_profile_bool_value( 'snapshots.min_free_space.enabled', True, profile_id )

    def get_min_free_space_in_mb( self, profile_id = None ):
        enabled, value, unit = self.get_min_free_space( profile_id )
        if not enabled:
            return 0

        if self.DISK_UNIT_MB == unit:
            return value

        value *= 1024 #Gb
        if self.DISK_UNIT_GB == unit:
            return value

        return 0

    def set_min_free_space( self, enabled, value, unit, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.min_free_space.enabled', enabled, profile_id )
        self.set_profile_int_value( 'snapshots.min_free_space.value', value, profile_id )
        self.set_profile_int_value( 'snapshots.min_free_space.unit', unit, profile_id )

    def min_free_inodes(self, profile_id = None):
        #?Keep at least value % free inodes.;1-15
        return self.get_profile_int_value('snapshots.min_free_inodes.value', 2, profile_id)

    def min_free_inodes_enabled(self, profile_id = None):
        #?Remove snapshots until \fIprofile<N>.snapshots.min_free_inodes.value\fR 
        #?free inodes in % is reached.
        return self.get_profile_bool_value('snapshots.min_free_inodes.enabled', True, profile_id)

    def set_min_free_inodes(self, enabled, value, profile_id = None):
        self.set_profile_bool_value('snapshots.min_free_inodes.enabled', enabled, profile_id)
        self.set_profile_int_value('snapshots.min_free_inodes.value', value, profile_id)

    def get_dont_remove_named_snapshots( self, profile_id = None ):
        #?Keep snapshots with names during smart_remove.
        return self.get_profile_bool_value( 'snapshots.dont_remove_named_snapshots', True, profile_id )

    def set_dont_remove_named_snapshots( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.dont_remove_named_snapshots', value, profile_id )

    def get_smart_remove( self, profile_id = None ):
                 #?Run smart_remove to clean up old snapshots after a new snapshot was created.
        return ( self.get_profile_bool_value( 'snapshots.smart_remove', False, profile_id ),
                 #?Keep all snapshots for X days.
                 self.get_profile_int_value( 'snapshots.smart_remove.keep_all', 2, profile_id ),
                 #?Keep one snapshot per day for X days.
                 self.get_profile_int_value( 'snapshots.smart_remove.keep_one_per_day', 7, profile_id ),
                 #?Keep one snapshot per week for X weeks.
                 self.get_profile_int_value( 'snapshots.smart_remove.keep_one_per_week', 4, profile_id ),
                 #?Keep one snapshot per month for X month.
                 self.get_profile_int_value( 'snapshots.smart_remove.keep_one_per_month', 24, profile_id ) )

    def set_smart_remove( self, value, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.smart_remove', value, profile_id )
        self.set_profile_int_value( 'snapshots.smart_remove.keep_all', keep_all, profile_id )
        self.set_profile_int_value( 'snapshots.smart_remove.keep_one_per_day', keep_one_per_day, profile_id )
        self.set_profile_int_value( 'snapshots.smart_remove.keep_one_per_week', keep_one_per_week, profile_id )
        self.set_profile_int_value( 'snapshots.smart_remove.keep_one_per_month', keep_one_per_month, profile_id )

    def is_notify_enabled( self, profile_id = None ):
        #?Display notifications (errors, warnings) through libnotify.
        return self.get_profile_bool_value( 'snapshots.notify.enabled', True, profile_id )

    def set_notify_enabled( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.notify.enabled', value, profile_id )

    def is_backup_on_restore_enabled( self, profile_id = None ):
        #?Rename existing files before restore into FILE.backup.YYYYMMDD
        return self.get_profile_bool_value( 'snapshots.backup_on_restore.enabled', True, profile_id )

    def set_backup_on_restore( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.backup_on_restore.enabled', value, profile_id )

    def is_run_nice_from_cron_enabled( self, profile_id = None ):
        #?Run cronjobs with 'nice \-n 19'. This will give BackInTime the 
        #?lowest CPU priority to not interupt any other working process.\n
        #?Note that the crontab entry is only generated during saving in 
        #?settings dialog. If you don't run a GUI version of BackInTime 
        #?you'll have to create the crontab entry on your own.
        return self.get_profile_bool_value( 'snapshots.cron.nice', self.DEFAULT_RUN_NICE_FROM_CRON, profile_id )

    def set_run_nice_from_cron_enabled( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.cron.nice', value, profile_id )

    def is_run_ionice_from_cron_enabled( self, profile_id = None ):
        #?Run cronjobs with 'ionice \-c2 \-n7'. This will give BackInTime the 
        #?lowest IO bandwidth priority to not interupt any other working process.\n
        #?Note that the crontab entry is only generated during saving in 
        #?settings dialog. If you don't run a GUI version of BackInTime 
        #?you'll have to create the crontab entry on your own.
        return self.get_profile_bool_value( 'snapshots.cron.ionice', self.DEFAULT_RUN_IONICE_FROM_CRON, profile_id )

    def set_run_ionice_from_cron_enabled( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.cron.ionice', value, profile_id )

    def is_run_ionice_from_user_enabled( self, profile_id = None ):
        #?Run BackInTime with 'ionice \-c2 \-n7' when taking a manual snapshot. 
        #?This will give BackInTime the lowest IO bandwidth priority to not 
        #?interupt any other working process.
        return self.get_profile_bool_value( 'snapshots.user_backup.ionice', self.DEFAULT_RUN_IONICE_FROM_USER, profile_id )

    def set_run_ionice_from_user_enabled( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.user_backup.ionice', value, profile_id )

    def is_run_nice_on_remote_enabled(self, profile_id = None):
        #?Run rsync and other commands on remote host with 'nice \-n 19'
        return self.get_profile_bool_value('snapshots.ssh.nice', self.DEFAULT_RUN_NICE_ON_REMOTE, profile_id)

    def set_run_nice_on_remote_enabled(self, value, profile_id = None):
        self.set_profile_bool_value('snapshots.ssh.nice', value, profile_id)

    def is_run_ionice_on_remote_enabled(self, profile_id = None):
        #?Run rsync and other commands on remote host with 'ionice \-c2 \-n7'
        return self.get_profile_bool_value('snapshots.ssh.ionice', self.DEFAULT_RUN_IONICE_ON_REMOTE, profile_id)

    def set_run_ionice_on_remote_enabled(self, value, profile_id = None):
        self.set_profile_bool_value('snapshots.ssh.ionice', value, profile_id)

    def is_run_nocache_on_local_enabled( self, profile_id = None ):
        #?Run rsync on local machine with 'nocache'. 
        #?This will prevent files from being cached in memory.
        return self.get_profile_bool_value( 'snapshots.local.nocache', self.DEFAULT_RUN_NOCACHE_ON_LOCAL, profile_id )

    def set_run_nocache_on_local_enabled( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.local.nocache', value, profile_id )

    def is_run_nocache_on_remote_enabled(self, profile_id = None):
        #?Run rsync on remote host with 'nocache'. 
        #?This will prevent files from being cached in memory.
        return self.get_profile_bool_value('snapshots.ssh.nocache', self.DEFAULT_RUN_NOCACHE_ON_REMOTE, profile_id)

    def set_run_nocache_on_remote_enabled(self, value, profile_id = None):
        self.set_profile_bool_value('snapshots.ssh.nocache', value, profile_id)

    def bwlimit_enabled( self, profile_id = None ):
        #?Limit rsync bandwidth usage over network. Use this with mode SSH. 
        #?For mode Local you should rather use ionice.
        return self.get_profile_bool_value( 'snapshots.bwlimit.enabled', False, profile_id )

    def set_bwlimit_enabled( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.bwlimit.enabled', value, profile_id )

    def bwlimit( self, profile_id = None ):
        #?Bandwidth limit in KB/sec.
        return self.get_profile_int_value( 'snapshots.bwlimit.value', 3000, profile_id )

    def set_bwlimit( self, value, profile_id = None ):
        self.set_profile_int_value( 'snapshots.bwlimit.value', value, profile_id )

    def is_no_on_battery_enabled( self, profile_id = None ):
        #?Don't take snapshots if the Computer runs on battery.
        return self.get_profile_bool_value( 'snapshots.no_on_battery', False, profile_id )

    def set_no_on_battery_enabled( self, value, profile_id = None ):
        self.set_profile_bool_value( 'snapshots.no_on_battery', value, profile_id )

    def preserve_acl( self, profile_id = None ):
        #?Preserve ACL. The  source  and  destination  systems must have 
        #?compatible ACL entries for this option to work properly.
        return self.get_profile_bool_value( 'snapshots.preserve_acl', False, profile_id )

    def set_preserve_acl( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.preserve_acl', value, profile_id )

    def preserve_xattr( self, profile_id = None ):
        #?Preserve extended attributes (xattr).
        return self.get_profile_bool_value( 'snapshots.preserve_xattr', False, profile_id )

    def set_preserve_xattr( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.preserve_xattr', value, profile_id )

    def copy_unsafe_links( self, profile_id = None ):
        #?This tells rsync to copy the referent of symbolic links that point 
        #?outside the copied tree.  Absolute symlinks are also treated like 
        #?ordinary files.
        return self.get_profile_bool_value( 'snapshots.copy_unsafe_links', False, profile_id )

    def set_copy_unsafe_links( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.copy_unsafe_links', value, profile_id )

    def copy_links( self, profile_id = None ):
        #?When  symlinks  are  encountered, the item that they point to 
        #?(the reference) is copied, rather than the symlink.
        return self.get_profile_bool_value( 'snapshots.copy_links', False, profile_id )

    def set_copy_links( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.copy_links', value, profile_id )

    def rsync_options_enabled( self, profile_id = None ):
        #?Past additional options to rsync
        return self.get_profile_bool_value( 'snapshots.rsync_options.enabled', False, profile_id )

    def set_rsync_options_enabled( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.rsync_options.enabled', value, profile_id )

    def rsync_options( self, profile_id = None ):
        #?rsync options. Options must be quoted e.g. \-\-exclude-from="/path/to/my exclude file"
        return self.get_profile_str_value( 'snapshots.rsync_options.value', '', profile_id )

    def set_rsync_options( self, value, profile_id = None ):
        return self.set_profile_str_value( 'snapshots.rsync_options.value', value, profile_id )

    def continue_on_errors( self, profile_id = None ):
        #?Continue on errors. This will keep incomplete snapshots rather than 
        #?deleting and start over again.
        return self.get_profile_bool_value( 'snapshots.continue_on_errors', True, profile_id )

    def set_continue_on_errors( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.continue_on_errors', value, profile_id )

    def use_checksum( self, profile_id = None ):
        #?Use checksum to detect changes rather than size + time.
        return self.get_profile_bool_value( 'snapshots.use_checksum', False, profile_id )

    def set_use_checksum( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.use_checksum', value, profile_id )

    def log_level( self, profile_id = None ):
        #?Log level used during take_snapshot.\n1 = Error\n2 = Changes\n3 = Info;1-3
        return self.get_profile_int_value( 'snapshots.log_level', 3, profile_id )

    def set_log_level( self, value, profile_id = None ):
        return self.set_profile_int_value( 'snapshots.log_level', value, profile_id )

    def full_rsync( self, profile_id = None ):
        #?Full rsync mode. May be faster but snapshots are not read-only 
        #?anymore and destination file-system must support all linux 
        #?attributes (date, rights, user, group...)
        return self.get_profile_bool_value( 'snapshots.full_rsync', False, profile_id )

    def set_full_rsync( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.full_rsync', value, profile_id )

    def check_for_changes( self, profile_id = None ):
        #?Perform a dry-run before taking snapshots. Don't take a new snapshot 
        #?if nothing has changed.
        return self.get_profile_bool_value( 'snapshots.check_for_changes', True, profile_id )

    def set_check_for_changes( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.check_for_changes', value, profile_id )

    def gnu_find_suffix_support( self, profile_id = None ):
        #?Remote SSH host support GNU find suffix (find \-exec COMMAND {} +).
        return self.get_profile_bool_value( 'snapshots.gnu_find_suffix_support', True, profile_id )

    def find_suffix( self, profile_id = None ):
        if self.gnu_find_suffix_support(profile_id):
            return '+'
        else:
            return '\\;'

    def set_gnu_find_suffix_support( self, value, profile_id = None ):
        return self.set_profile_bool_value( 'snapshots.gnu_find_suffix_support', value, profile_id )

    def get_take_snapshot_user_script( self, step, profile_id = None ):
        #?Run this scrip on events defined by <STEP>.\nPossible events for 
        #?<STEP>:\n  before\n  after\n  new_snapshot\n  error;absolute path
        return self.get_profile_str_value ( "snapshots.take_snapshot.%s.user.script" % step, '', profile_id )

    def set_take_snapshot_user_script( self, step, path, profile_id = None ):
        self.set_profile_str_value( "snapshots.take_snapshot.%s.user.script" % step, path, profile_id )

    def get_take_snapshot_user_script_before( self, profile_id = None ):
        return self.get_take_snapshot_user_script( 'before', profile_id )

    def set_take_snapshot_user_script_before( self, path, profile_id = None ):
        self.set_take_snapshot_user_script( 'before', path, profile_id )

    def get_take_snapshot_user_script_after( self, profile_id = None ):
        return self.get_take_snapshot_user_script( 'after', profile_id )

    def set_take_snapshot_user_script_after( self, path, profile_id = None ):
        self.set_take_snapshot_user_script( 'after', path, profile_id )

    def get_take_snapshot_user_script_new_snapshot( self, profile_id = None ):
        return self.get_take_snapshot_user_script( 'new_snapshot', profile_id = None )

    def set_take_snapshot_user_script_new_snapshot( self, path, profile_id = None ):
        self.set_take_snapshot_user_script( 'new_snapshot', path, profile_id )

    def get_take_snapshot_user_script_error( self, profile_id = None ):
        return self.get_take_snapshot_user_script( 'error', profile_id )

    def set_take_snapshot_user_script_error( self, path, profile_id = None ):
        self.set_take_snapshot_user_script( 'error', path, profile_id )

    def get_app_path( self ):
        return self._APP_PATH

    def get_doc_path( self ):
        return self._DOC_PATH

    def get_app_instance_file( self ):
        return os.path.join( self._LOCAL_DATA_FOLDER, 'app.lock' )

    def __get_file_id__( self, profile_id = None ):
        if profile_id is None:
            profile_id = self.get_current_profile()
        if profile_id == '1':
            return ''
        return profile_id

    def get_take_snapshot_log_file( self, profile_id = None ):
        return os.path.join( self._LOCAL_DATA_FOLDER, "takesnapshot_%s.log" % self.__get_file_id__( profile_id ) )

    def get_take_snapshot_message_file( self, profile_id = None ):
        return os.path.join( self._LOCAL_DATA_FOLDER, "worker%s.message" % self.__get_file_id__( profile_id ) )

    def get_take_snapshot_progress_file( self, profile_id = None ):
        return os.path.join( self._LOCAL_DATA_FOLDER, "worker%s.progress" % self.__get_file_id__( profile_id ) )

    def get_take_snapshot_instance_file( self, profile_id = None ):
        return os.path.join( self._LOCAL_DATA_FOLDER, "worker%s.lock" % self.__get_file_id__( profile_id ) )

    def get_take_snapshot_user_callback( self, profile_id = None ):
        return os.path.join( self._LOCAL_CONFIG_FOLDER, "user-callback" )

    def get_password_cache_folder( self ):
        return os.path.join( self._LOCAL_DATA_FOLDER, "password_cache" )

    def get_password_cache_pid( self ):
        return os.path.join( self.get_password_cache_folder(), "PID" )

    def get_password_cache_fifo( self ):
        return os.path.join( self.get_password_cache_folder(), "FIFO" )

    def get_password_cache_info( self ):
        return os.path.join( self.get_password_cache_folder(), "info" )

    def get_cron_env_file( self ):
        return os.path.join( self._LOCAL_DATA_FOLDER, "cron_env" )

    def get_anacrontab(self, suffix = ''):
        '''Deprecated since 1.1. Just keep this to delete old anacrontab files'''
        return os.path.join(self._LOCAL_CONFIG_FOLDER, 'anacrontab' + suffix)

    def anacrontab_files(self):
        '''list existing old anacrontab files'''
        dirname, basename = os.path.split(self.get_anacrontab())
        for file in os.listdir(dirname):
            if file.startswith(basename):
                yield os.path.join(dirname, file)

    def get_anacron_spool(self):
        return os.path.join(self._LOCAL_DATA_FOLDER, 'anacron')

    def get_anacron_spool_file(self, profile_id = None):
        return os.path.join(self.get_anacron_spool(), self.get_anacron_job_identify(profile_id))

    def get_anacron_job_identify(self, profile_id = None):
        if not profile_id:
            profile_id = self.get_current_profile()
        profile_name = self.get_profile_name(profile_id)
        return profile_id + '_' + profile_name.replace(' ', '_')

    def get_udev_rules_path(self):
        return os.path.join('/etc/udev/rules.d', '99-backintime-%s.rules' % self.get_user())

    def get_restore_log_file( self, profile_id = None ):
        return os.path.join( self._LOCAL_DATA_FOLDER, "restore_%s.log" % self.__get_file_id__( profile_id ) )

    def get_restore_instance_file( self, profile_id = None ):
        return os.path.join( self._LOCAL_DATA_FOLDER, "restore%s.lock" % self.__get_file_id__( profile_id ) )

    def get_last_snapshot_symlink(self, profile_id = None):
        return os.path.join(self.get_snapshots_full_path(profile_id), 'last_snapshot')

    def get_encfsconfig_backup_folder(self, profile_id = None):
        return os.path.join(self._LOCAL_DATA_FOLDER, 'encfsconfig_backup_%s' % self.__get_file_id__( profile_id ))

    def get_license( self ):
        return tools.read_file( os.path.join( self.get_doc_path(), 'LICENSE' ), '' )

    def get_translations( self ):
        return tools.read_file( os.path.join( self.get_doc_path(), 'TRANSLATIONS' ), '' )

    def get_authors( self ):
        return tools.read_file( os.path.join( self.get_doc_path(), 'AUTHORS' ), '' )

    def prepare_path( self, path ):
        if len( path ) > 1:
            if path[ -1 ] == os.sep:
                path = path[ : -1 ]
        return path

    def is_configured( self, profile_id = None ):
        '''Checks if the program is configured'''
        return bool(self.get_snapshots_path(profile_id) and self.get_include(profile_id))

    def can_backup( self, profile_id = None ):
        '''Checks if snapshots_path exists'''
        if not self.is_configured( profile_id ):
            return False

        if not os.path.isdir( self.get_snapshots_full_path( profile_id ) ):
            print("%s does not exist" % self.get_snapshots_full_path( profile_id ))
            return False

        return True

    def is_backup_scheduled(self, profile_id = None):
        '''check if profile is supposed to be run this time'''
        if self.get_automatic_backup_mode(profile_id) not in (self.REPEATEDLY, self.UDEV):
            return True

        #if crontab wasn't updated since upgrading BIT to version without anacron
        #we are most likely started by anacron and should run this task without asking.
        if list(self.anacrontab_files()):
            return True

        last_time = tools.readTimeStamp(self.get_anacron_spool_file(profile_id))
        if not last_time:
            return True

        value = self.get_automatic_backup_anacron_period(profile_id)
        unit = self.get_automatic_backup_anacron_unit(profile_id)

        return self.olderThan(last_time, value, unit)

    def olderThan(self, time, value, unit):
        '''return True if time is older than months, weeks, days or hours'''
        assert isinstance(time, datetime.datetime), 'time is not datetime.datetime type: %s' % time

        now = datetime.datetime.now()

        if unit <= self.HOUR:
            return time < now - datetime.timedelta(hours = value)
        elif unit <= self.DAY:
            return time.date() <= now.date() - datetime.timedelta(days = value)
        elif unit <= self.WEEK:
            return time.date() < now.date() \
                                 - datetime.timedelta(days = now.date().weekday()) \
                                 - datetime.timedelta(weeks = value - 1)
        elif unit <= self.MONTH:
            firstDay = now.date() - datetime.timedelta(days = now.date().day + 1)
            for i in range(value - 1):
                if firstDay.month == 1:
                    firstDay = firstDay.replace(month = 12, year = firstDay.year - 1)
                else:
                    firstDay = firstDay.replace(month = firstDay.month - 1)
            return time.date() < firstDay
        else:
            return True

    def setup_cron( self ):
        system_entry_message = "#Back In Time system entry, this will be edited by the gui:"

        """We have to check if the system_entry_message is in use,
        if not then the entries are most likely from Back In Time 0.9.26
        or earlier."""
        if os.system( "crontab -l | grep '%s' > /dev/null" % system_entry_message ) != 0:
            """Then the system entry message has not yet been used in this crontab
            therefore we assume all entries are system entries and clear them all.
            This is the old behaviour"""
            print("Clearing all Back In Time entries")
            os.system( "crontab -l | grep -v backintime | crontab -" )

        print("Clearing system Back In Time entries")
        os.system( "crontab -l | sed '/%s/{N;/backintime/d;}' | crontab -" % system_entry_message )

        for file in self.anacrontab_files():
            print("Clearing anacrontab")
            os.remove(file)

        self.setupUdev.clean()

        empty = True
        uuid_tmp_fd = None
        profiles = self.get_profiles()

        try:
            for profile_id in profiles:
                profile_name = self.get_profile_name( profile_id )
                print("Profile: %s" % profile_name)
                backup_mode = self.get_automatic_backup_mode( profile_id )
                print("Automatic backup: %s" % self.AUTOMATIC_BACKUP_MODES[ backup_mode ])

                if self.NONE == backup_mode:
                    continue

                if not tools.check_command( 'crontab' ):
                    self.notify_error( _( 'Can\'t find crontab.\nAre you sure cron is installed ?\nIf not you should disable all automatic backups.' ) )
                    return False

                cron_line = ''

                hour = self.get_automatic_backup_time(profile_id) / 100;
                minute = self.get_automatic_backup_time(profile_id) % 100;
                day = self.get_automatic_backup_day(profile_id)
                weekday = self.get_automatic_backup_weekday(profile_id)

                if self.AT_EVERY_BOOT == backup_mode:
                    cron_line = 'echo "{msg}\n@reboot {cmd}"'
                elif self._5_MIN == backup_mode:
                    cron_line = 'echo "{msg}\n*/5 * * * * {cmd}"'
                elif self._10_MIN == backup_mode:
                    cron_line = 'echo "{msg}\n*/10 * * * * {cmd}"'
                elif self._30_MIN == backup_mode:
                    cron_line = 'echo "{msg}\n*/30 * * * * {cmd}"'
                elif self._1_HOUR == backup_mode:
                    cron_line = 'echo "{msg}\n0 * * * * {cmd}"'
                elif self._2_HOURS == backup_mode:
                    cron_line = 'echo "{msg}\n0 */2 * * * {cmd}"'
                elif self._4_HOURS == backup_mode:
                    cron_line = 'echo "{msg}\n0 */4 * * * {cmd}"'
                elif self._6_HOURS == backup_mode:
                    cron_line = 'echo "{msg}\n0 */6 * * * {cmd}"'
                elif self._12_HOURS == backup_mode:
                    cron_line = 'echo "{msg}\n0 */12 * * * {cmd}"'
                elif self.CUSTOM_HOUR == backup_mode:
                    cron_line = 'echo "{msg}\n0 ' + self.get_custom_backup_time( profile_id ) + ' * * * {cmd}"'
                elif self.DAY == backup_mode:
                    cron_line = "echo \"{msg}\n%s %s * * * {cmd}\"" % (minute, hour)
                elif self.REPEATEDLY == backup_mode:
                    if self.get_automatic_backup_anacron_unit(profile_id) <= self.DAY:
                        cron_line = 'echo "{msg}\n*/15 * * * * {cmd}"'
                    else:
                        cron_line = 'echo "{msg}\n0 * * * * {cmd}"'
                elif self.UDEV == backup_mode:
                    if not self.setupUdev.isReady:
                        self.notify_error( _('Could not install Udev rule for profile %(profile_id)s. '
                                             'DBus Service \'%(dbus_interface)s\' '
                                             'wasn\'t available') 
                                            %{'profile_id': profile_id,
                                              'dbus_interface': 'net.launchpad.backintime.serviceHelper'})
                    mode = self.get_snapshots_mode(profile_id)
                    if mode == 'local':
                        dest_path = self.get_snapshots_full_path(profile_id)
                    elif mode == 'local_encfs':
                        dest_path = self.get_local_encfs_path(profile_id)
                    else:
                        self.notify_error( _('Schedule udev doesn\'t work with mode %s') % mode)
                        return False
                    uuid = tools.get_uuid_from_path(dest_path)
                    if uuid is None:
                        self.notify_error( _('Couldn\'t find UUID for "%s"') % dest_path)
                        return False
                    try:
                        self.setupUdev.addRule(self.cron_cmd(profile_id), uuid)
                    except tools.InvalidChar as e:
                        self.notify_error(str(e))
                elif self.WEEK == backup_mode:
                    cron_line = "echo \"{msg}\n%s %s * * %s {cmd}\"" % (minute, hour, weekday)
                elif self.MONTH == backup_mode:
                    cron_line = "echo \"{msg}\n%s %s %s * * {cmd}\"" % (minute, hour, day)

                cmd = self.cron_cmd(profile_id)

                if cron_line:
                    empty = False
                    cron_line = cron_line.replace( '{cmd}', cmd )
                    cron_line = cron_line.replace( '{msg}', system_entry_message )
                    os.system( "( crontab -l; %s ) | crontab -" % cron_line )

            if self.setupUdev.isReady and self.setupUdev.save():
                print('Udev rules added successfully')
        except tools.PermissionDeniedByPolicy as e:
                self.notify_error(str(e))
        except:
            raise
        finally:
            if empty:
                # Leave one system_entry_message in to prevent deleting of manual
                # entries if there is no automatic entry.
                info_message = "#Please don't delete these two lines, or all custom backintime entries are going to be deleted next time you call the gui options!"
                os.system( '(crontab -l; echo "%s"; echo "%s") | crontab -'
                        % (system_entry_message, info_message) )
        return True

    def cron_cmd(self, profile_id):
        cmd = tools.which('backintime') + ' '
        if profile_id != '1':
            cmd += '--profile-id %s ' % profile_id
        if not self._LOCAL_CONFIG_PATH is self._DEFAULT_CONFIG_PATH:
            cmd += '--config %s ' % self._LOCAL_CONFIG_PATH
        cmd += '--backup-job >/dev/null 2>&1'
        if self.is_run_ionice_from_cron_enabled(profile_id) and tools.check_command('ionice'):
            cmd = tools.which('ionice') + ' -c2 -n7 ' + cmd
        if self.is_run_nice_from_cron_enabled( profile_id ) and tools.check_command('nice'):
            cmd = tools.which('nice') + ' -n 19 ' + cmd
        return cmd

if __name__ == "__main__":
    config = Config()
    print("snapshots path = %s" % config.get_snapshots_full_path())
