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
import configfile
import sys
import tools


class DriveInfo( configfile.ConfigFile ):
    def __init__( self, path ):
        configfile.ConfigFile.__init__( self )

        self.path = path
        self.load( self._get_driveinfo_file_() )

        dirty = False

        if sys.platform == 'win32':
            #there is nothing to do
            pass
        else:
            if not self.has_value( 'hardlinks' ):
                self.set_bool_value( 'hardlinks', self._check_hardlinks_() )
                dirty = True

            if not self.has_value( 'permissions' ):
                self.set_bool_value( 'permissions', self._check_perms_() )
                dirty = True

            if not self.has_value( 'usergroup' ):
                self.set_bool_value( 'usergroup', self._check_usergroup_() )
                dirty = True

        if dirty:
            self.save( self._get_driveinfo_file_() )

    def support_hardlinks( self ):
        return self.get_bool_value( 'hardlinks', False )
        
    def support_permissions( self ):
        return self.get_bool_value( 'permissions', False )
        
    def support_usergroup( self ):
        return self.get_bool_value( 'usergroup', False )
        
    def _get_driveinfo_file_( self ):
        return os.path.join( self.path, 'driveinfo' )

    def _check_hardlinks_( self ):
        tmp_path = os.path.join( self.path, 'driveinfo.tmp' )
        tools.make_dirs( tmp_path )
        if not os.path.isdir( tmp_path ):
            return False

        file1_path = os.path.join( tmp_path, 'file1' )
        file2_path = os.path.join( tmp_path, 'file2' )

        ret_val = False

        os.system( "echo abc > \"%s\"" % file1_path )
        os.system( "ln \"%s\" \"%s\"" % ( file1_path, file2_path ) )
        os.system( "echo abc > \"%s\"" % file2_path )

        if os.path.exists( file1_path ) and os.path.exists( file2_path ):
            try:
                info1 = os.stat( file1_path )
                info2 = os.stat( file2_path )

                if info1.st_size == info2.st_size:
                    ret_val = True
            except:
                pass

        os.system( "rm -rf \"%s\"" % tmp_path )
        return ret_val

    def _check_perms_for_file_( self, file_path, mode ):
        ret_val = False

        os.system( "chmod %s \"%s\"" % ( mode, file_path ) )
        try:
            info = "%o" % os.stat( file_path ).st_mode
            info = info[ -3 : ]
            if info == mode:
                ret_val = True
        except:
            pass

        return ret_val

    def _check_perms_( self ):
        tmp_path = os.path.join( self.path, 'driveinfo.tmp' )
        tools.make_dirs( tmp_path )
        if not os.path.isdir( tmp_path ):
            return False

        file_path = os.path.join( tmp_path, 'file' )
        os.system( "echo abc > \"%s\"" % file_path )
        if not os.path.isfile( file_path ):
            return False

        ret_val = False

        if self._check_perms_for_file_( file_path, '111' ):
            if self._check_perms_for_file_( file_path, '700' ):
                if self._check_perms_for_file_( file_path, '600' ):
                    if self._check_perms_for_file_( file_path, '711' ):
                        if self._check_perms_for_file_( file_path, '300' ):
                            if self._check_perms_for_file_( file_path, '666' ):
                                ret_val = True

        os.system( "rm -rf \"%s\"" % tmp_path )
        return ret_val

    def _check_usergroup_( self ):
        tmp_path = os.path.join( self.path, 'driveinfo.tmp' )
        tools.make_dirs( tmp_path )
        if not os.path.isdir( tmp_path ):
            return False

        file_path = os.path.join( tmp_path, 'file' )
        os.system( "echo abc > \"%s\"" % file_path )
        if not os.path.isfile( file_path ):
            return False

        ret_val = False

        uid = os.getuid()
        gid = os.getgid()

        try:
            info = os.stat( file_path )
            if info.st_uid == uid and info.st_gid == gid:
                ret_val = True
        except:
            pass

        if ret_val and uid == 0:
            #try to change the group
            import grp

            #search for another group
            new_gid = gid
            new_name = ''
            for group in grp.getgrall():
                if group.gr_gid != gid:
                    new_gid = group.gr_gid
                    new_name = group.gr_name
                    break

            if new_gid != gid:
                os.system( "chgrp %s \"%s\"" % ( new_name, file_path ) )
                try:
                    info = os.stat( file_path )
                    if info.st_gid != new_gid:
                        ret_val = False
                except:
                    ret_val = False

        os.system( "rm -rf \"%s\"" % tmp_path )
        return ret_val

