# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import logger
from applicationinstance import ApplicationInstance


class GUIApplicationInstance(ApplicationInstance):
    """Handle one application instance mechanism.
    """
    def __init__(self, baseControlFile, raiseCmd=''):
        """Specify the base for control files."""
        self.raiseFile = baseControlFile + '.raise'
        self.raiseCmd = raiseCmd

        super(GUIApplicationInstance, self).__init__(
            baseControlFile + '.pid', False, False)

        # Remove raiseFile is already exists
        if os.path.exists(self.raiseFile):
            os.remove(self.raiseFile)

        self.check()
        self.startApplication()

    def check(self):
        """Check if the current application is already running."""
        ret = super(GUIApplicationInstance, self).check(False)
        if not ret:
            print(f'The application is already running. (pid: {self.pid})')

            # Notify raise
            try:
                with open(self.raiseFile, 'wt') as f:
                    f.write(self.raiseCmd)

            except OSError as e:
                logger.error(f'Failed to write raise file {e.filename}: '
                             f'[{e.errno}] {e.strerror}')

            # Exit raise an exception so don't put it in a try/except block
            exit(0)

        else:
            return ret

    def raiseCommand(self):
        """
        check if the application must to be raised
           return None if no raise needed, or a string command to raise
        """
        ret_val = None

        try:
            if os.path.isfile(self.raiseFile):
                with open(self.raiseFile, 'rt') as f:
                    ret_val = f.read()
                os.remove(self.raiseFile)
        except:
            pass

        return ret_val
