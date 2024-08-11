# Back In Time
# Copyright (C) 2016 Taylor Raack
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation,Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import os
import re
import subprocess
import sys
from test import generic
import json

import config
import version

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


class TestBackInTime(generic.TestCase):
    def setUp(self):
        super(TestBackInTime, self).setUp()

    def test_quiet_mode(self):
        output = subprocess.getoutput('python3 backintime.py --quiet')

        # Remove "WARNING:" and "ERROR:" messages from output.
        # They should appear even in quite-mode.
        output = filter(lambda line: not line.startswith('WARNING:')
                        and not line.startswith('ERROR:'),
                        output.split('\n'))
        output = '\n'.join(list(output))

        self.assertEqual('', output)

    def test_local_snapshot_is_successful(self):
        """From BIT initialization through snapshot

        From BIT initialization all the way through successful snapshot on a
        local mount. test one of the highest level interfaces a user could
        work with - the command line ensures that argument parsing,
        functionality, and output all work as expected is NOT intended to
        replace individual method tests, which are incredibly useful as well.

        Development notes (by Buhtz, 2023):
        Multiple tests do compare return codes and output on stdout. It is NOT
        tested what is on the file system. The intention might be a system
        test. But the asserts not qualified to answer the important questions
        and observe the intended behavior.  Heavy refactoring is needed. But
        because of the "level" of that tests it won't happen in the near
        future. Also maintenance costs of this tests are damn high because
        every tiny modification of BIT gives a false fail of this test.

        Development notes (by Buhtz, 2024-05):
        It is just dumb stdout parsing. I tend to remove this test because of
        the calculation of its value and its maintenance costs.
        """

        # ensure that we see full diffs of assert output if there are any
        self.maxDiff = None

        # create pristine source directory with single file
        subprocess.getoutput("chmod -R a+rwx /tmp/test && rm -rf /tmp/test")
        os.mkdir('/tmp/test')

        with open('/tmp/test/testfile', 'w') as f:
            f.write('some data')

        # create pristine snapshot directory
        subprocess.getoutput(
            "chmod -R a+rwx /tmp/snapshots && rm -rf /tmp/snapshots")
        os.mkdir('/tmp/snapshots')

        # remove restored directory
        subprocess.getoutput("rm -rf /tmp/restored")

        # install proper destination filesystem structure and verify output
        proc = subprocess.Popen(["./backintime",
                                 "--config",
                                 "test/config",
                                 "--share-path",
                                 self.sharePath,
                                 "check-config",
                                 # do not overwrite users crontab
                                 "--no-crontab"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

        output, error = proc.communicate()
        msg = 'Returncode: {}\nstderr: {}\nstdout: {}' \
              .format(proc.returncode, error.decode(), output.decode())

        self.assertEqual(proc.returncode, 0, msg)

        self.assertRegex(output.decode(), re.compile(r'''
Back In Time
Version: \d+.\d+.\d+.*

Back In Time comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions; type `backintime --license' for details.

(INFO: Update to config version \d+
)?
 \+--------------------------------\+
 |  Check/prepare snapshot path   |
 \+--------------------------------\+
Check/prepare snapshot path: done

 \+--------------------------------\+
 |          Check config          |
 \+--------------------------------\+
Check config: done

Config .*test/config profile 'Main profile' is fine.''', re.MULTILINE))

        # execute backup and verify output
        proc = subprocess.Popen(["./backintime",
                                 "--config", "test/config",
                                 "--share-path", self.sharePath,
                                 "backup"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, error = proc.communicate()
        msg = 'Returncode: {}\nstderr: {}\nstdout: {}' \
              .format(proc.returncode, error.decode(), output.decode())
        self.assertEqual(proc.returncode, 0, msg)

        self.assertRegex(output.decode(), re.compile(r'''
Back In Time
Version: \d+.\d+.\d+.*

Back In Time comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions; type `backintime --license' for details.
''', re.MULTILINE))

        # Workaround until refactoring was done (Buhtz, Feb.'23)
        # The log output completely goes to stderr.
        # Note: DBus warnings at the begin and end are already ignored by the
        #       regex but if the BiT serviceHelper.py DBus daemon is not
        #       installed at all the warnings also occur in the middle of below
        #       expected INFO log lines so they are removed by filtering here.
        #       The same goes with Gtk warnings.

        line_beginnings_to_exclude = [
            "WARNING",
            "Warning",
        ]

        # Warnings currently known:
        # - "WARNING: D-Bus message:"
        # - "WARNING: Udev-based profiles cannot be changed or checked"
        # - "WARNING: Inhibit Suspend failed"
        # - "Warning: Ignoring XDG_SESSION_TYPE=wayland on Gnome. Use
        #    QT_QPA_PLATFORM=wayland to run on Wayland anyway"

        line_contains_to_exclude = [
            "Gtk-WARNING",
            "qt.qpa.plugin: Could not find the Qt platform plugin",
            'qt.dbus.integration: Could not connect "org.freedesktop.IBus" '
            'to globalEngineChanged(QString)',
        ]

        # remove lines via startswith()
        filtered_log_output = filter(
            lambda line: not any([
                line.startswith(ex) for ex in line_beginnings_to_exclude]),
            error.decode().split('\n')
        )

        # remove lines via __contains__()
        filtered_log_output = filter(
            lambda line: not any([
                ex in line for ex in line_contains_to_exclude]),
            filtered_log_output
        )

        # remove empty lines
        filtered_log_output = filter(
            lambda line: line,
            filtered_log_output
        )

        filtered_log_output = '\n'.join(filtered_log_output)

        self.assertRegex(filtered_log_output, re.compile(r'''INFO: Lock
INFO: Take a new snapshot. Profile: 1 Main profile
INFO: Call rsync to take the snapshot
INFO: Save config file
INFO: Save permissions
INFO: Unlock''', re.MULTILINE))

        # get snapshot id
        subprocess.check_output(["./backintime",
                                 "--config",
                                 "test/config",
                                 "snapshots-list"])

        # execute restore and verify output
        proc = subprocess.Popen(["./backintime",
                                 "--config",
                                 "test/config",
                                 "--share-path",
                                 self.sharePath,
                                 "restore",
                                 "/tmp/test/testfile",
                                 "/tmp/restored",
                                 "0"],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, error = proc.communicate()
        msg = 'Returncode: {}\nstderr: {}\nstdout: {}' \
              .format(proc.returncode, error.decode(), output.decode())
        self.assertEqual(proc.returncode, 0, msg)

        self.assertRegex(output.decode(), re.compile(r'''
Back In Time
Version: \d+.\d+.\d+.*

Back In Time comes with ABSOLUTELY NO WARRANTY.
This is free software, and you are welcome to redistribute it
under certain conditions; type `backintime --license' for details.

''', re.MULTILINE))

        # The log output completely goes to stderr
        self.assertRegex(
            error.decode(),
            re.compile(
                r'''INFO: Restore: /tmp/test/testfile to: /tmp/restored.*''',
                re.MULTILINE
            )
        )

        # verify that files restored are the same as those backed up
        subprocess.check_output(["diff",
                                 "-r",
                                 "/tmp/test",
                                 "/tmp/restored"])

    def test_diagnostics_arg(self):
        # "output" from stdout may currently be polluted with logging output
        # lines from INFO and DEBUG log output.
        # Logging output of WARNING and ERROR is already written to stderr
        # so `check_output` does work here (returns only stdout without
        # stderr).
        output = subprocess.check_output(["./backintime", "--diagnostics"])

        diagnostics = json.loads(output)
        self.assertEqual(diagnostics["backintime"]["name"],
                         config.Config.APP_NAME)
        self.assertEqual(diagnostics["backintime"]["version"],
                         version.__version__)
