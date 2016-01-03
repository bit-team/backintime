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

import gettext
import logger

_=gettext.gettext

class ConfigFile(object):
    '''store options in a plain text file in form of:
    key=value
    '''
    def __init__( self ):
        self.dict = {}
        self.error_handler = None
        self.question_handler = None

    def set_error_handler( self, handler ):
        '''register a function that should be called for notifying errors.

        handler:    callable function
        '''
        self.error_handler = handler

    def set_question_handler( self, handler ):
        '''register a function that should be called for asking questions.

        handler:    callable function
        '''
        self.question_handler = handler

    def clear_handlers( self ):
        '''reset error and question handlers.
        '''
        self.error_handler = None
        self.question_handler = None

    def notify_error( self, message ):
        '''call previously registered function to show an error.

        message:    error message (str) that should be shown
        '''
        if self.error_handler is None:
            return
        self.error_handler( message )

    def ask_question( self, message ):
        '''call previously registered function to ask a question.

        message:    question (str) that should be shown
        '''
        if self.question_handler is None:
            return False
        return self.question_handler( message )

    def save( self, filename ):
        '''save all options to file.

        filename:   full path

        tests:
        test/test_configfile.TestConfigFile.test_save
        '''
        try:
            with open( filename, 'wt' ) as f:
                keys = list(self.dict.keys())
                keys.sort()
                for key in keys:
                    f.write( "%s=%s\n" % ( key, self.dict[key] ) )
        except OSError as e:
            logger.error('Failed to save config: %s' %str(e), self)
            self.notify_error(_('Failed to save config: %s') %str(e))
            return False
        return True

    def load( self, filename, **kwargs ):
        '''reset current options and load new options from file.

        filename:   full path

        tests:
        test/test_configfile.TestConfigFile.test_load
        '''
        self.dict = {}
        self.append( filename, **kwargs )

    def append( self, filename, maxsplit = 1 ):
        '''load options from file and append them to current options.

        filename:   full path
        maxsplit:   split lines only n times on '='
        '''
        lines = []

        if not os.path.isfile(filename):
            return
        try:
            with open( filename, 'rt' ) as f:
                lines = f.readlines()
        except OSError as e:
            logger.error('Failed to load config: %s' %str(e), self)
            self.notify_error(_('Failed to load config: %s') %str(e))

        for line in lines:
            items = line.strip('\n').split( '=', maxsplit )
            if len( items ) == 2:
                self.dict[ items[ 0 ] ] = items[ 1 ]

    def remap_key( self, old_key, new_key ):
        '''remap keys to a new key name.

        old_key:    old key name
        new_key:    new key name

        tests:
        test/test_configfile.TestConfigFile.test_remap_key
        '''
        if old_key != new_key:
            if old_key in self.dict:
                if new_key not in self.dict:
                    self.dict[ new_key ] = self.dict[ old_key ]
                del self.dict[ old_key ]

    def has_value( self, key ):
        '''True if key is set.

        key:    string used as key

        tests:
        test/test_configfile.TestConfigFile.test_has_value
        '''
        return key in self.dict

    def get_str_value( self, key, default_value = '' ):
        '''return a 'str' instance of key's value.

        key:            string used as key
        default_value:  return this if key is not set

        tests:
        test/test_configfile.TestConfigFile.test_get_str_value
        test/test_configfile.TestConfigFile.test_get_str_value_default
        '''
        if key in self.dict:
            return self.dict[ key ]
        else:
            return default_value

    def set_str_value( self, key, value ):
        '''set a string value for key.

        key:    string used as key
        value:  store this option

        tests:
        test/test_configfile.TestConfigFile.test_set_str_value
        '''
        self.dict[ key ] = value

    def get_int_value( self, key, default_value = 0 ):
        '''return a 'int' instance of key's value.

        key:            string used as key
        default_value:  return this if key is not set

        tests:
        test/test_configfile.TestConfigFile.test_get_int_value
        test/test_configfile.TestConfigFile.test_get_int_value_default
        '''
        try:
            return int( self.dict[ key ] )
        except:
            return default_value

    def set_int_value( self, key, value ):
        '''set an integer value for key.

        key:    string used as key
        value:  store this option

        tests:
        test/test_configfile.TestConfigFile.test_set_int_value
        '''
        self.set_str_value( key, str( value ) )

    def get_bool_value( self, key, default_value = False ):
        '''return a 'bool' instance of key's value.

        key:            string used as key
        default_value:  return this if key is not set

        tests:
        test/test_configfile.TestConfigFile.test_get_bool_value
        test/test_configfile.TestConfigFile.test_get_bool_value_default
        '''
        try:
            val = self.dict[ key ]
            if "1" == val or "TRUE" == val.upper():
                return True
            return False
        except:
            return default_value

    def set_bool_value( self, key, value ):
        '''set a bool value for key.

        key:    string used as key
        value:  store this option

        tests:
        test/test_configfile.TestConfigFile.test_set_bool_value
        '''
        if value:
            self.set_str_value( key, 'true' )
        else:
            self.set_str_value( key, 'false' )

    def get_list_value(self, key, type_key = 'str:value', default_value = []):
        '''return a list of values

        key:      used base-key
        type_key: 'str:value'               => return str values from key.value
                  'int:type'                => return int values from key.type
                  'bool:enabled'            => return bool values from key.enabled
                  ('str:value', 'int:type') => return tuple of values
        default_value:    defualt value

        size of list must be stored in key.size

        tests:
        test/test_configfile.TestConfigFile.test_get_list_value_default
        test/test_configfile.TestConfigFile.test_get_list_value_int
        test/test_configfile.TestConfigFile.test_get_list_value_str
        test/test_configfile.TestConfigFile.test_get_list_value_bool
        test/test_configfile.TestConfigFile.test_get_list_value_tuple
        test/test_configfile.TestConfigFile.test_get_list_value_tuple_missing_values
        test/test_configfile.TestConfigFile.test_get_list_value_invalid_type
        '''
        def get_value(key, tk):
            t = ''
            if isinstance(tk, str):
                t, k = tk.split(':', maxsplit = 1)
            if t in ('str', 'int', 'bool'):
                func = getattr(self, 'get_%s_value' %t)
                return func('%s.%s' %(key, k))
            raise TypeError('Invalid type_key: %s' %tk)

        size = self.get_int_value('%s.size' %key, -1)
        if size <= 0:
            return default_value

        ret = []
        for i in range(1, size + 1):
            if isinstance(type_key, str):
                ret.append(get_value('%s.%s' %(key, i), type_key))
            elif isinstance(type_key, tuple):
                items = []
                for tk in type_key:
                    items.append(get_value('%s.%s' %(key, i), tk))
                ret.append(tuple(items))
            else:
                raise TypeError('Invalid type_key: %s' %type_key)
        return ret

    def set_list_value(self, key, type_key, value):
        '''set a list of values

        key:      used base-key
        type_key: 'str:value'               => set str values from key.value
                  'int:type'                => set int values from key.type
                  'bool:enabled'            => set bool values from key.enabled
                  ('str:value', 'int:type') => set tuple of values
        value:    that should be stored

        size of list will be stored in key.size

        tests:
        test/test_configfile.TestConfigFile.test_set_list_value_int
        test/test_configfile.TestConfigFile.test_set_list_value_str
        test/test_configfile.TestConfigFile.test_set_list_value_bool
        test/test_configfile.TestConfigFile.test_set_list_value_tuple
        test/test_configfile.TestConfigFile.test_set_list_value_tuple_missing_values
        test/test_configfile.TestConfigFile.test_set_list_value_remove_leftovers
        test/test_configfile.TestConfigFile.test_set_list_value_remove_leftovers_tuple
        test/test_configfile.TestConfigFile.test_set_list_value_invalid_type
        '''
        def set_value(key, tk, v):
            t = ''
            if isinstance(tk, str):
                t, k = tk.split(':', maxsplit = 1)
            if t in ('str', 'int', 'bool'):
                func = getattr(self, 'set_%s_value' %t)
                return func('%s.%s' %(key, k), v)
            raise TypeError('Invalid type_key: %s' %tk)

        if not isinstance(value, (list, tuple)):
            raise TypeError('value has wrong type: %s' %value)

        old_size = self.get_int_value('%s.size' %key, -1)
        self.set_int_value('%s.size' %key, len(value))

        for i, v in enumerate(value, start = 1):
            if isinstance(type_key, str):
                set_value('%s.%s' %(key, i), type_key, v)
            elif isinstance(type_key, tuple):
                for iv, tk in enumerate(type_key):
                    if len(v) > iv:
                        set_value('%s.%s' %(key, i), tk, v[iv])
                    else:
                        self.remove_key('%s.%s.%s' %(key, i, tk.split(':')[1]))
            else:
                raise TypeError('Invalid type_key: %s' %type_key)

        if len(value) < old_size:
            for i in range(len(value) + 1, old_size + 1):
                if isinstance(type_key, str):
                    self.remove_key('%s.%s.%s' %(key, i, type_key.split(':')[1]))
                elif isinstance(type_key, tuple):
                    for tk in type_key:
                        self.remove_key('%s.%s.%s' %(key, i, tk.split(':')[1]))

    def remove_key( self, key ):
        '''remove key from options.

        key:    string used as key

        tests:
        test/test_configfile.TestConfigFile.test_remove_key
        '''
        if key in self.dict:
            del self.dict[ key ]

    def remove_keys_starts_with( self, prefix ):
        '''remove key from options which start with given prefix.

        prefix: prefix for keys (key starts with this string) that should be removed

        tests:
        test/test_configfile.TestConfigFile.test_remove_keys_start_with
        test/test_configfile.TestConfigFile.test_remove_keys_start_with_not_matching_prefix
        '''
        remove_keys = []

        for key in self.dict.keys():
            if key.startswith( prefix ):
                remove_keys.append( key )

        for key in remove_keys:
            del self.dict[ key ]

    def get_keys(self):
        return list(self.dict.keys())

class ConfigFileWithProfiles( ConfigFile ):
    def __init__( self, default_profile_name = '' ):
        ConfigFile.__init__( self )

        self.default_profile_name = default_profile_name
        self.current_profile_id = '1'

    def load( self, filename ):
        '''reset current options and load new options from file.

        filename:   full path

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_load
        '''
        self.current_profile_id = '1'
        super(ConfigFileWithProfiles, self).load(filename)

    def append( self, filename ):
        '''load options from file and append them to current options.

        filename:   full path
        '''
        super(ConfigFileWithProfiles, self).append(filename)

        found = False
        profiles = self.get_profiles()
        for profile_id in profiles:
            if profile_id == self.current_profile_id:
                found = True
                break

        if not found and profiles:
            self.current_profile_id = profiles[0]

        if self.get_int_value( 'profiles.version' ) <= 0:
            rename_keys = []

            for key in self.dict.keys():
                if key.startswith( 'profile.0.' ):
                    rename_keys.append( key )

            for old_key in rename_keys:
                new_key = 'profile1.' + old_key[ 10 :  ]
                self.dict[ new_key ] = self.dict[ old_key ]
                del self.dict[ old_key ]

        if self.get_int_value( 'profiles.version' ) != 1:
            self.set_int_value( 'profiles.version', 1 )

    def get_profiles( self ):
        '''return a list of all available profile IDs. Profile IDs are strings!

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_get_profiles
        '''
        return self.get_str_value( 'profiles', '1' ).split(':')

    def get_profiles_sorted_by_name( self ):
        '''return a list of available profile IDs alphabetical sorted by their names.
        Profile IDs are strings!

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_get_profiles_sorted_by_name
        '''
        profiles_unsorted = self.get_profiles()
        if len( profiles_unsorted ) <= 1:
            return profiles_unsorted

        profiles_dict = {}

        for profile_id in profiles_unsorted:
            profiles_dict[ self.get_profile_name( profile_id ).upper() ] = profile_id

        keys = list(profiles_dict.keys())
        keys.sort()

        profiles_sorted = []
        for key in keys:
            profiles_sorted.append( profiles_dict[key] )

        return profiles_sorted

    def get_current_profile( self ):
        '''return the currently selected profile ID. Profile IDs are strings!

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_current_profile
        '''
        return self.current_profile_id

    def set_current_profile( self, profile_id ):
        '''change the current profile.

        profile_id: valid profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_current_profile
        '''
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        profiles = self.get_profiles()

        for i in profiles:
            if i == profile_id:
                self.current_profile_id = profile_id
                logger.debug('change current profile: %s' %profile_id, self)
                logger.changeProfile(profile_id)
                return True

        return False

    def set_current_profile_by_name( self, name ):
        '''change the current profile.

        name:   valid profile name

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_current_profile_by_name
        '''
        profiles = self.get_profiles()

        for profile_id in profiles:
            if self.get_profile_name( profile_id ) == name:
                self.current_profile_id = profile_id
                logger.debug('change current profile: %s' %name, self)
                logger.changeProfile(profile_id)
                return True

        return False

    def profile_exists( self, profile_id ):
        '''True if the profile exists.

        profile_id: profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_profile_exists
        '''
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        return profile_id in self.get_profiles()

    def profile_exists_by_name( self, name ):
        '''True if the profile exists.

        name:   profile name

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_profile_exists_by_name
        '''
        profiles = self.get_profiles()

        for profile_id in profiles:
            if self.get_profile_name( profile_id ) == name:
                return True

        return False

    def get_profile_name( self, profile_id = None ):
        '''return the name of the profile.

        profile_id: valid profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_get_profile_name
        '''
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        if profile_id is None:
            profile_id = self.current_profile_id
        if profile_id == '1':
            default = self.default_profile_name
        else:
            default = 'Profile %s' % profile_id
        return self.get_profile_str_value( 'name', default, profile_id )

    def add_profile( self, name ):
        '''add a new profile if the name is not already in use.
        Return the new profile ID.

        name:   new profile name

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_add_profile
        '''
        profiles = self.get_profiles()

        for profile_id in profiles:
            if self.get_profile_name( profile_id ) == name:
                self.notify_error( _('Profile "%s" already exists !') % name )
                return None

        new_id = 1
        while True:
            ok = True

            if str(new_id) in profiles:
                ok = False

            if ok:
                break

            new_id = new_id + 1

        new_id = str( new_id )

        profiles.append( new_id )
        self.set_str_value( 'profiles', ':'.join(profiles) )

        self.set_profile_str_value( 'name', name, new_id )
        return new_id

    def remove_profile( self, profile_id = None ):
        '''remove profile and all its keys and values.

        profile_id: valid profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_remove_profile
        '''
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        if profile_id == None:
            profile_id = self.current_profile_id

        profiles = self.get_profiles()
        if len( profiles ) <= 1:
            self.notify_error( _('You can\'t remove the last profile !') )
            return False

        found = False
        index = 0
        for profile in profiles:
            if profile == profile_id:
                self.remove_keys_starts_with( self._get_profile_key_( '', profile_id ) )
                del profiles[index]
                self.set_str_value( 'profiles', ':'.join( profiles ) )
                found = True
                break
            index = index + 1

        if not found:
            return False

        if self.current_profile_id == profile_id:
            self.current_profile_id = '1'

        return True

    def set_profile_name( self, name, profile_id = None ):
        '''change the name of the profile.
        name:       new profile name
        profile_id: valid profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_set_profile_name
        '''
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        if profile_id == None:
            profile_id = self.current_profile_id

        profiles = self.get_profiles()

        for profile in profiles:
            if self.get_profile_name( profile ) == name:
                if profile[0] != profile_id:
                    self.notify_error(  _('Profile "%s" already exists !') % name )
                    return False

        self.set_profile_str_value( 'name', name, profile_id )
        return True

    def _get_profile_key_( self, key, profile_id = None ):
        '''return the prefix for keys with profile. e.g. 'profile1.key'

        key:        key name
        profile_id: valid profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_get_profile_key
        '''
        if isinstance(profile_id, int):
            profile_id = str(profile_id)
        if profile_id is None:
            profile_id = self.current_profile_id
        return 'profile' + profile_id + '.' + key

    def remove_profile_key( self, key, profile_id = None ):
        '''remove the key from profile.

        key:        key name
        profile_id: valid profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_remove_profile_key
        '''
        self.remove_key( self._get_profile_key_( key, profile_id ) )

    def remove_profile_keys_starts_with( self, prefix, profile_id = None ):
        '''remove the keys starting with prefix from profile.

        prefix:     prefix for keys (key starts with this string) that
                    should be removed
        profile_id: valid profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_remove_profile_keys_starts_with
        '''
        self.remove_keys_starts_with( self._get_profile_key_( prefix, profile_id ) )

    def has_profile_value( self, key, profile_id = None ):
        '''True if key is set in profile.

        key:        string used as key
        profile_id: valid profile ID

        tests:
        test/test_configfile.TestConfigFileWithProfiles.test_has_profile_value
        '''
        return self._get_profile_key_( key, profile_id ) in self.dict

    def get_profile_str_value( self, key, default_value = '', profile_id = None ):
        return self.get_str_value( self._get_profile_key_( key, profile_id ), default_value )

    def set_profile_str_value( self, key, value, profile_id = None ):
        self.set_str_value( self._get_profile_key_( key, profile_id ), value )

    def get_profile_int_value( self, key, default_value = 0, profile_id = None ):
        return self.get_int_value( self._get_profile_key_( key, profile_id ), default_value )

    def set_profile_int_value( self, key, value, profile_id = None ):
        self.set_int_value( self._get_profile_key_( key, profile_id ), value )

    def get_profile_bool_value( self, key, default_value = False, profile_id = None ):
        return self.get_bool_value( self._get_profile_key_( key, profile_id ), default_value )

    def set_profile_bool_value( self, key, value, profile_id = None ):
        self.set_bool_value( self._get_profile_key_( key, profile_id ), value )

    def get_profile_list_value(self, key, type_key = 'str:value', default_value = [], profile_id = None):
        return self.get_list_value(self._get_profile_key_(key, profile_id), type_key, default_value)

    def set_profile_list_value(self, key, type_key, value, profile_id = None):
        self.set_list_value(self._get_profile_key_(key, profile_id), type_key, value)
