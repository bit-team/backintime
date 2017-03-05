#    Back In Time
#    Copyright (C) 2008-2017 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import tools

tools.register_backintime_path( 'common' )
tools.register_backintime_path( 'plugins' )

import logger
from exceptions import StopException

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

    def on_app_start(self):
        return

    def on_app_exit(self):
        return

    def do_mount(self):
        return

    def do_unmount(self):
        return

class PluginManager:
    def __init__( self ):
        self.plugins = []
        self.has_gui_plugins_ = False
        self.plugins_loaded = False

    def load_plugins( self, snapshots = None, cfg = None, force = False ):
        if self.plugins_loaded and not force:
            return

        if snapshots is None:
            import snapshots as snapshots_
            snapshots = snapshots_.Snapshots(cfg)

        self.plugins_loaded = True
        self.plugins = []
        self.has_gui_plugins_ = False

        loadedPlugins = []
        for path in ('plugins', 'common/plugins', 'qt4/plugins'):
            fullPath = tools.get_backintime_path(path)
            if os.path.isdir(fullPath):
                logger.debug('Register plugin path %s' %fullPath, self)
                tools.register_backintime_path(path)
                for f in os.listdir(fullPath):
                    if f not in loadedPlugins and f.endswith('.py') and not f.startswith('__'):
                        try:
                            module = __import__( f[ : -3 ] )
                            module_dict = module.__dict__

                            for key, value in list(module_dict.items()):
                                if key.startswith( '__' ):
                                    continue

                                if type(value) is type:
                                    if issubclass( value, Plugin ):
                                        plugin = value()
                                        if plugin.init( snapshots ):
                                            logger.debug('Add plugin %s' %f, self)
                                            if plugin.is_gui():
                                                self.has_gui_plugins_ = True
                                                self.plugins.insert( 0, plugin )
                                            else:
                                                self.plugins.append( plugin )
                            loadedPlugins.append(f)
                        except BaseException as e:
                            logger.error('Failed to load plugin %s: %s' %(f, str(e)), self)

    def has_gui_plugins( self ):
        return self.has_gui_plugins_

    def on_process_begins( self ):
        ret_val = True
        for plugin in self.plugins:
            try:
                plugin.on_process_begins()
            except StopException:
                ret_val = False
            except BaseException as e:
                self.log_error(plugin, e)
        return ret_val

    def on_process_ends( self ):
        for plugin in reversed( self.plugins ):
            try:
                plugin.on_process_ends()
            except BaseException as e:
                self.log_error(plugin, e)

    def on_error( self, code, message = '' ):
        for plugin in self.plugins:
            try:
                plugin.on_error( code, message )
            except BaseException as e:
                self.log_error(plugin, e)

    def on_new_snapshot( self, snapshot_id, snapshot_path ):
        for plugin in self.plugins:
            try:
                plugin.on_new_snapshot( snapshot_id, snapshot_path )
            except BaseException as e:
                self.log_error(plugin, e)

    def on_message( self, profile_id, profile_name, level, message, timeout = -1 ):
        for plugin in self.plugins:
            try:
                plugin.on_message( profile_id, profile_name, level, message, timeout )
            except BaseException as e:
                self.log_error(plugin, e)

    def on_app_start( self ):
        for plugin in reversed( self.plugins ):
            try:
                plugin.on_app_start()
            except BaseException as e:
                self.log_error(plugin, e)

    def on_app_exit( self ):
        for plugin in reversed( self.plugins ):
            try:
                plugin.on_app_exit()
            except BaseException as e:
                self.log_error(plugin, e)

    def do_mount( self ):
        for plugin in reversed( self.plugins ):
            try:
                plugin.do_mount()
            except BaseException as e:
                self.log_error(plugin, e)

    def do_unmount( self ):
        for plugin in reversed( self.plugins ):
            try:
                plugin.do_unmount()
            except BaseException as e:
                self.log_error(plugin, e)

    def log_error(self, plugin, e):
        logger.error('Plugin %s %s failed: %s'
                     %(plugin.__module__,               #plugin name
                       sys._getframe(1).f_code.co_name, #method name
                       str(e)),                         #exception
                     self, 1)
