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
import tools
import types

tools.register_backintime_path( 'common' )
tools.register_backintime_path( 'plugins' )


class Plugin:
    def __init__( self ):
        return

    def init( self, snapshots ):
        return True

    def is_gui( self ):
        return False

    def on_process_begins( self ):
        return

    def on_process_ends( self ):
        return

    def on_error( self, code, message ):
        return

    def on_new_snapshot( self, snapshot_id, snapshot_path ):
        return

    def on_message( self, profile_id, profile_name, level, message, timeout ):
        return


class PluginManager:
    def __init__( self ):
        self.plugins = []
        self.has_gui_plugins_ = False
        self.plugins_loaded = False

    def load_plugins( self, snapshots, force = False ):
        if self.plugins_loaded and not force:
            return

        self.plugins_loaded = True
        self.plugins = []
        self.has_gui_plugins_ = False
        
        plugins_path = tools.get_backintime_path( 'plugins' )

        for file in os.listdir( plugins_path ):
            try:
                if file.endswith( '.py' ) and not file.startswith( '__' ):
                    path = os.path.join( plugins_path, file )

                    module = __import__( file[ : -3 ] )
                    module_dict = module.__dict__
                    
                    for key, value in module_dict.items():
                        if key.startswith( '__' ):
                            continue

                        if type(value) is types.ClassType:
                            if issubclass( value, Plugin ):
                                plugin = value()
                                if plugin.init( snapshots ):
                                    if plugin.is_gui():
                                        self.has_gui_plugins_ = True
                                        self.plugins.insert( 0, plugin )
                                    else:
                                        self.plugins.append( plugin )
            except:
                pass

    def has_gui_plugins( self ):
        return self.has_gui_plugins_

    def on_process_begins( self ):
        for plugin in self.plugins:
            try:
                plugin.on_process_begins()
            except:
                pass

    def on_process_ends( self ):
        for plugin in reversed( self.plugins ):
            try:
                plugin.on_process_ends()
            except:
                pass

    def on_error( self, code, message = '' ):
        for plugin in self.plugins:
            try:
                plugin.on_error( code, message )
            except:
                pass

    def on_new_snapshot( self, snapshot_id, snapshot_path ):
        for plugin in self.plugins:
            try:
                plugin.on_new_snapshot( snapshot_id, snapshot_path )
            except:
                pass

    def on_message( self, profile_id, profile_name, level, message, timeout = -1 ):
        for plugin in self.plugins:
            try:
                plugin.on_message( profile_id, profile_name, level, message, timeout )
            except:
                pass

