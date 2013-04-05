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
import gettext


_=gettext.gettext


class ConfigFile:
    def __init__( self ):
        self.dict = {}
        self.error_handler = None
        self.question_handler = None

    def set_error_handler( self, handler ):
        self.error_handler = handler

    def set_question_handler( self, handler ):
        self.question_handler = handler

    def clear_handlers( self ):
        self.error_handler = None
        self.question_handler = None

    def notify_error( self, message ):
        if self.error_handler is None:
            return
        self.error_handler( message )

    def ask_question( self, message ):
        if self.question_handler is None:
            return False
        return self.question_handler( message )

    def save( self, filename ):
        try:
            file = open( filename, 'w' )
            keys = self.dict.keys()
            keys.sort()
            for key in keys:
                file.write( "%s=%s\n" % ( key, self.dict[key] ) )
            file.close()
        except:
            pass

    def load( self, filename, **kwargs ):
        self.dict = {}
        self.append( filename, **kwargs )

    def append( self, filename, maxsplit = -1 ):
        lines = []

        try:
            file = open( filename, 'r' )
            lines = file.readlines()
            file.close()
        except:
            pass

        for line in lines:
            items = line.split( '=', maxsplit )
            if len( items ) == 2:
                self.dict[ items[ 0 ] ] = items[ 1 ][ : -1 ]

    def remap_key( self, old_key, new_key ):
        if old_key != new_key:
            if self.dict.has_key( old_key ):
                if not self.dict.has_key( new_key ):
                    self.dict[ new_key ] = self.dict[ old_key ]
                del self.dict[ old_key ]

    def has_value( self, key ):
        return self.dict.has_key( key )

    def get_str_value( self, key, default_value = '' ):
        if self.dict.has_key( key ):
            return self.dict[ key ]
        else:
            return default_value

    def set_str_value( self, key, value ):
        self.dict[ key ] = value

    def get_int_value( self, key, default_value = 0 ):
        try:
            return int( self.dict[ key ] )
        except:
            return default_value

    def set_int_value( self, key, value ):
        self.set_str_value( key, str( value ) )

    def get_bool_value( self, key, default_value = False ):
        try:
            val = self.dict[ key ]
            if "1" == val or "TRUE" == val.upper():
                return True
            return False
        except:
            return default_value

    def set_bool_value( self, key, value ):
        if value:
            self.set_str_value( key, 'true' )
        else:
            self.set_str_value( key, 'false' )

    def remove_key( self, key ):
        if self.dict.has_key( key ):
            del self.dict[ key ]

    def remove_keys_starts_with( self, prefix ):
        remove_keys = []

        for key in self.dict.iterkeys():
            if key.startswith( prefix ):
                remove_keys.append( key )

        for key in remove_keys:
            del self.dict[ key ]

    def get_keys(self):
        return self.dict.keys()

class ConfigFileWithProfiles( ConfigFile ):
    def __init__( self, default_profile_name = '' ):
        ConfigFile.__init__( self )

        self.default_profile_name = default_profile_name
        self.current_profile_id = '1'

    def load( self, filename ):
        self.current_profile_id = '1'
        ConfigFile.load( self, filename )

    def append( self, filename ):
        ConfigFile.append( self, filename )

        found = False
        profiles = self.get_profiles()
        for profile_id in profiles:
            if profile_id == self.current_profile_id:
                found = True
                break

        if not found and len( profiles ) > 0:
            self.current_profile_id = profiles[0]

        if self.get_int_value( 'profiles.version' ) <= 0:
            rename_keys = []

            for key in self.dict.iterkeys():
                if key.startswith( 'profile.0.' ):
                    rename_keys.append( key )

            for old_key in rename_keys:
                new_key = 'profile1.' + old_key[ 10 :  ]
                self.dict[ new_key ] = self.dict[ old_key ]
                del self.dict[ old_key ]

        if self.get_int_value( 'profiles.version' ) != 1:
            self.set_int_value( 'profiles.version', 1 )

    def get_profiles( self ):
        return self.get_str_value( 'profiles', '1' ).split(':')

    def get_profiles_sorted_by_name( self ):
        profiles_unsorted = self.get_profiles()
        if len( profiles_unsorted ) <= 1:
            return profiles_unsorted

        profiles_dict = {}

        for profile_id in profiles_unsorted:
            profiles_dict[ self.get_profile_name( profile_id ).upper() ] = profile_id

        keys = profiles_dict.keys()
        keys.sort()

        profiles_sorted = []
        for key in keys:
            profiles_sorted.append( profiles_dict[key] )

        return profiles_sorted

    def get_current_profile( self ):
        return self.current_profile_id

    def set_current_profile( self, profile_id ):
        profiles = self.get_profiles()

        for id in profiles:
            if id == profile_id:
                self.current_profile_id = profile_id
                return True

        return False

    def set_current_profile_by_name( self, name ):
        profiles = self.get_profiles()

        for profile_id in profiles:
            if self.get_profile_name( profile_id ) == name:
                self.current_profile_id = profile_id
                return True

        return False

    def profile_exists( self, profile_id ):
        profiles = self.get_profiles()

        for id in profiles:
            if id == profile_id:
                return True

        return False

    def profile_exists_by_name( self, name ):
        profiles = self.get_profiles()

        for profile_id in profiles:
            if self.get_profile_name( profile_id ) == name:
                return True

        return False

    def get_profile_name( self, profile_id = None ):
        return self.get_profile_str_value( 'name', self.default_profile_name, profile_id )

    def add_profile( self, name ):
        profiles = self.get_profiles()

        for profile_id in profiles:
            if self.get_profile_name( profile_id ) == name:
                self.notify_error( _('Profile "%s" already exists !') % name )
                return None

        new_id = 1
        while True:
            ok = True

            for profile in profiles:
                if profile == str(new_id):
                    ok = False
                    break

            if ok:
                break

            new_id = new_id + 1

        new_id = str( new_id )

        profiles.append( new_id )
        self.set_str_value( 'profiles', ':'.join(profiles) )

        self.set_profile_str_value( 'name', name, new_id )
        return new_id

    def remove_profile( self, profile_id = None ):
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
        if profile_id is None:
            profile_id = self.current_profile_id
        return 'profile' + profile_id + '.' + key

    def remove_profile_key( self, key, profile_id = None ):
        self.remove_key( self._get_profile_key_( key, profile_id ) )

    def remove_profile_keys_starts_with( self, prefix, profile_id = None ):
        self.remove_keys_starts_with( self._get_profile_key_( prefix, profile_id ) )

    def has_profile_value( self, key, profile_id = None ):
        return self.dict.has_key( self._get_profile_key_( key, profile_id ) )

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
