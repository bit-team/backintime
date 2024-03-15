#  Back In Time
#  Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey,
#  Germar Reitze
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License along
#  with this program; if not, write to the Free Software Foundation, Inc.,
#  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import pluginmanager
import logger
import gettext
from subprocess import Popen, PIPE
from exceptions import StopException

_ = gettext.gettext


class UserCallbackPlugin(pluginmanager.Plugin):
    """ Executes a script file at different backup steps to customize behavior

    Back In Time allows to inform plugins (implemented in Python
    files) about different steps ("events") in the backup process
    via the :py:class:`pluginmanager.PluginManager`.

    This plugin calls a user-defined script file ("user-callback"). By default
    that file is located in the config folder `$XDG_CONFIG_HOME/backintime/`
    or another folder if command line optioni `--config` is used.

    The user-callback script is called with up to five positional arguments:

    1. The profile ID from the config file (1=Main Profile, ...)
    2. The profile name (from the config file)
    3. A numeric code to indicate the reason why Back In Time
       calls the script (see the method implementation
       for details about the numeric code)
    4. Error code (only if argument 3 has the value "4")
       or snapshot ID (only if argument 3 has the value "3")
    5. Snapshot name (only if argument 3 has the value "3")

    For more details and script examples see:
    https://github.com/bit-team/user-callback

    Notes:
        The user-callback script file is normally implemented as
        shell script but could theoretically be implemented in
        any script language (declared via the hash bang "#!"
        in the first line of the script file.
    """
    def __init__(self):
        logger.openlog()
        return

    def init(self, snapshots):
        self.config = snapshots.config
        self.script = self.config.takeSnapshotUserCallback()

        return os.path.exists(self.script)

    # TODO 09/28/2022: This method should be private (_callback)
    def callback(self, *args, profileID=None):
        if profileID is None:
            profileID = self.config.currentProfile()

        profileName = self.config.profileName(profileID)
        cmd = [self.script, profileID, profileName]
        cmd.extend(str(x) for x in args)

        logger.debug(f'Call user-callback: {" ".join(cmd)}', self)

        if self.config.userCallbackNoLogging():
            stdout, stderr = None, None
        else:
            stdout, stderr = PIPE, PIPE

        try:
            callback = Popen(cmd,
                             stdout=stdout,
                             stderr=stderr,
                             universal_newlines=True)
            output = callback.communicate()

            # Stdout
            if output[0]:
                logger.info("user-callback returned '"
                            + output[0].strip('\n') + "'",
                            self)

            # Stderr
            if output[1]:
                logger.error("user-callback returned '"
                             + output[1].strip('\n') + "'",
                             self)

            if callback.returncode != 0:
                logger.warning(
                    f'user-callback returncode: {callback.returncode}', self)
                raise StopException()

        except OSError as e:
            logger.error(
                f'Exception when trying to run user callback: {e.strerror}',
                self)

    def processBegin(self):
        self.callback('1')

    def processEnd(self):
        self.callback('2')

    def error(self, code, message):
        if not message:
            self.callback('4', code)
        else:
            self.callback('4', code, message)

    def newSnapshot(self, snapshot_id, snapshot_path):
        self.callback('3', snapshot_id, snapshot_path)

    def appStart(self):
        self.callback('5')

    def appExit(self):
        self.callback('6')

    def mount(self, profileID = None):
        self.callback('7', profileID = profileID)

    def unmount(self, profileID = None):
        self.callback('8', profileID = profileID)
