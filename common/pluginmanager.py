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

tools.registerBackintimePath('common')
tools.registerBackintimePath('plugins')

import logger
from exceptions import StopException

class Plugin:
    def __init__(self):
        return

    def init(self, snapshots):
        return True

    def isGui(self):
        return False

    def processBegin(self):
        return

    def processEnd(self):
        return

    def error(self, code, message):
        return

    def newSnapshot(self, snapshot_id, snapshot_path):
        return

    def message(self, profile_id, profile_name, level, message, timeout):
        return

    def appStart(self):
        return

    def appExit(self):
        return

    def mount(self, profileID = None):
        return

    def unmount(self, profileID = None):
        return

class PluginManager:
    def __init__(self):
        self.plugins = []
        self.hasGuiPlugins = False
        self.loaded = False

    def load(self, snapshots = None, cfg = None, force = False):
        if self.loaded and not force:
            return

        if snapshots is None:
            import snapshots as snapshots_
            snapshots = snapshots_.Snapshots(cfg)

        self.loaded = True
        self.plugins = []
        self.hasGuiPlugins = False

        loadedPlugins = []
        for path in ('plugins', 'common/plugins', 'qt/plugins'):
            fullPath = tools.backintimePath(path)
            if os.path.isdir(fullPath):
                logger.debug('Register plugin path %s' %fullPath, self)
                tools.registerBackintimePath(path)
                for f in os.listdir(fullPath):
                    if f not in loadedPlugins and f.endswith('.py') and not f.startswith('__'):
                        try:
                            module = __import__(f[: -3])
                            module_dict = module.__dict__

                            for key, value in list(module_dict.items()):
                                if key.startswith('__'):
                                    continue

                                if type(value) is type:
                                    if issubclass(value, Plugin):
                                        plugin = value()
                                        if plugin.init(snapshots):
                                            logger.debug('Add plugin %s' %f, self)
                                            if plugin.isGui():
                                                self.hasGuiPlugins = True
                                                self.plugins.insert(0, plugin)
                                            else:
                                                self.plugins.append(plugin)
                            loadedPlugins.append(f)
                        except BaseException as e:
                            logger.error('Failed to load plugin %s: %s' %(f, str(e)), self)

    def processBegin(self):
        ret_val = True
        for plugin in self.plugins:
            try:
                plugin.processBegin()
            except StopException:
                ret_val = False
            except BaseException as e:
                self.logError(plugin, e)
        return ret_val

    def processEnd(self):
        for plugin in reversed(self.plugins):
            try:
                plugin.processEnd()
            except BaseException as e:
                self.logError(plugin, e)

    def error(self, code, message = ''):
        for plugin in self.plugins:
            try:
                plugin.error(code, message)
            except BaseException as e:
                self.logError(plugin, e)

    def newSnapshot(self, snapshot_id, snapshot_path):
        for plugin in self.plugins:
            try:
                plugin.newSnapshot(snapshot_id, snapshot_path)
            except BaseException as e:
                self.logError(plugin, e)

    def message(self, profile_id, profile_name, level, message, timeout = -1):
        for plugin in self.plugins:
            try:
                plugin.message(profile_id, profile_name, level, message, timeout)
            except BaseException as e:
                self.logError(plugin, e)

    def appStart(self):
        for plugin in reversed(self.plugins):
            try:
                plugin.appStart()
            except BaseException as e:
                self.logError(plugin, e)

    def appExit(self):
        for plugin in reversed(self.plugins):
            try:
                plugin.appExit()
            except BaseException as e:
                self.logError(plugin, e)

    def mount(self, profileID = None):
        for plugin in reversed(self.plugins):
            try:
                plugin.mount(profileID)
            except BaseException as e:
                self.logError(plugin, e)

    def unmount(self, profileID = None):
        for plugin in reversed(self.plugins):
            try:
                plugin.unmount(profileID)
            except BaseException as e:
                self.logError(plugin, e)

    def logError(self, plugin, e):
        logger.error('Plugin %s %s failed: %s'
                     %(plugin.__module__,               #plugin name
                       sys._getframe(1).f_code.co_name, #method name
                       str(e)),                         #exception
                     self, 1)
