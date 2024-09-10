#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
tools.registerBackintimePath('common', 'plugins')
tools.registerBackintimePath('qt', 'plugins')

import logger
from exceptions import StopException

class Plugin:
    """ Interface methods to customize behavior for different backup steps

    Back In Time allows to inform plugins (implemented in Python
    files) about different steps ("events") in the backup process.
    Plugins may implement special behavior to predefined
    "events" that are declared in this interface class
    as methods.

    To implement a new plugin create a new
    class that inherits from this one and implement all
    methods.

    Plugins are loaded by calling :py:func:`PluginManager.load`.
    """
    def __init__(self):
        return

    def init(self, snapshots):
        return True

    def isGui(self):
        """Indicates a GUI-related plugin

        The return value shall indicate if the plugin
        is related to the Back In Time GUI.
        Loaded GUI-related plugins are called before non-GUI-related
        plugins by the PluginManager.

        Returns:
            True if plugin is GUI-related, otherwise False
        """
        return False

    def processBegin(self):
        """Called before a backup process is started.

        A new snapshot is only taken if required (as configured).

        Returns:
            ``None`` (return value will be ignored anyhow)
        """
        return

    def processEnd(self):
        """Called after a backup process has ended

        Returns:
            ``None`` (return value will be ignored anyhow)
        """
        return

    def error(self, code, message):
        """Indicates errors during the backup process

        Called to send errors in the backup process
        (while taking a snapshot) to plugins.

        Args:
            code: A Back In Time error code

                Known error codes:

                1: No or no valid configuration
                   (check the configuration file)
                2: A backup process is already running.
                   Make sure that automatic and manual backups
                   do not run at once.
                3: Snapshots directory not found
                   (eg. when a removable drive is not mounted)
                4: The requested snapshot for "now" already exists.
                   ``message`` contains the SID (snapshot ID) then.
                5: Error while taking a snapshot.
                   ``message`` contains more information (as string).
                6: New snapshot taken but with errors.
                   ``message`` contains the SID (snapshot ID) then.

            message: The error message for the code
                (mostly an empty string by default)

        Returns:
             ``None`` (return value will be ignored anyhow)
        """
        return

    def newSnapshot(self, snapshot_id, snapshot_path):
        """ Called when the backup process has taken a new snapshot.

        A new snapshot is only taken by the backup process
        if required (as configured).

        Args:
            snapshot_id:   The id of the new snapshot
            snapshot_path: The path to the new snapshot
        Returns:
            ``None`` (return value will be ignored anyhow)
        """
        return

    def message(self, profile_id, profile_name, level, message, timeout):
        """ Called to send snapshot-related messages to plugins

        Args:
            profile_id:     Profile ID from configuration
            profile_name:   Profile name from the configuration
            level:          0 = INFO, 1 = ERROR
            message:        Message text
            timeout:        Requested timeout in seconds to process
                            the message. Not used at the moment.
                            (default -1 means "no timeout")

        Returns:
            ``None`` (return value will be ignored anyhow)
        """
        return

    def appStart(self):
        """ Called when the GUI of Back In Time was started.

        Not called when only the CLI command was started without the GUI.

        Returns:
            ``None`` (return value will be ignored anyhow)
        """
        return

    def appExit(self):
        """ Called when the GUI of Back In Time is closed

        Returns:
            ``None`` (return value will be ignored anyhow)
        """
        return

    def mount(self, profileID = None):
        """ Called when mounting a filesystem for the profile may be necessary.

        Args:
            profileID: Profile ID from the configuration

        Returns:
            ``None`` (return value will be ignored anyhow)
        """
        return

    def unmount(self, profileID = None):
        """ Called when unmounting a filesystem for a profile may be necessary

        Args:
            profileID: Profile ID from the configuration

        Returns
            ``None`` (return value will be ignored anyhow)
        """
        return

class PluginManager:
    """ Central interface for loading plugins and calling their API

    Back In Time allows to inform plugins (implemented in Python
    files) about different steps ("events") in the backup process.

    Use this class to load installed plugin classes
    and call their methods (see the interface declared by
    :py:class:`Plugin`).

    Plugins are loaded by calling :py:func:`PluginManager.load`.

    When you call a plugin function of the PluginManager it will
    call this plugin function for all loaded plugins.
    """
    # TODO 09/28/2022: Should inherit from + implement class "Plugin"
    def __init__(self):
        self.plugins = []
        self.hasGuiPlugins = False
        self.loaded = False

    def load(self, snapshots = None, cfg = None, force = False):
        """ Loads plugins

        Loads all plugins from python source code files that are stored
        in one of these plugin sub folders in the installation
        root folder:

            'plugins', 'common/plugins', 'qt/plugins'

        Plugins must inherit from :py:class:`Plugin` otherwise they
        are silently ignored.

        Args:
            snapshots (snapshots.Snapshots): Snapshot info
            cfg (config.Config): Current configuration
            force (bool):       ``True`` to enforce reloading all plugins
                                (``False`` does only load if not already done)

        Returns:
            ``None``
        """
        if self.loaded and not force:
            return

        if snapshots is None:
            import snapshots as snapshots_
            snapshots = snapshots_.Snapshots(cfg)

        self.loaded = True
        self.plugins = []
        self.hasGuiPlugins = False

        loadedPlugins = []

        # TODO 09/28/2022: Move hard coded plugin folders to configuration
        for path in ('plugins', 'common/plugins', 'qt/plugins'):
            fullPath = tools.backintimePath(path)

            if os.path.isdir(fullPath):
                logger.debug('Register plugin path %s' %fullPath, self)
                tools.registerBackintimePath(path)

                for f in os.listdir(fullPath):

                    if f not in loadedPlugins and f.endswith('.py') and not f.startswith('__'):
                        # logger.debug('Probing plugin %s' % f, self)

                        try:
                            module = __import__(f[: -3])
                            module_dict = module.__dict__

                            for key, value in list(module_dict.items()):
                                if key.startswith('__'):
                                    continue

                                if type(value) is type:
                                    # A plugin must implement this class via inheritance
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
