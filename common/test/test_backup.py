# Back In Time
# Copyright (C) 2016-2019 Germar Reitze
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
import sys
import unittest
from unittest.mock import patch
from datetime import date, datetime
from test import generic

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import config
import snapshots
import tools
from applicationinstance import ApplicationInstance
from pluginmanager import PluginManager
from mount import Mount
from exceptions import MountException

class TestBackup(generic.SnapshotsTestCase):
    @patch('time.sleep') # speed up unittest
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_backup(self, takeSnapshot, sleep):
        takeSnapshot.return_value = [True, False]
        self.assertFalse(self.sn.backup())

        self.assertEqual(takeSnapshot.call_count, 1)
        self.assertIsInstance(takeSnapshot.call_args[0][0], snapshots.SID)
        self.assertIsInstance(takeSnapshot.call_args[0][1], datetime)
        self.assertIsInstance(takeSnapshot.call_args[0][2], list)

    @patch('time.sleep') # speed up unittest
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_no_changes(self, takeSnapshot, sleep):
        takeSnapshot.return_value = [False, False]
        self.assertFalse(self.sn.backup())
        self.assertTrue(takeSnapshot.called)

        sid = takeSnapshot.call_args[0][0]
        newSnapshot = snapshots.NewSnapshot(self.cfg)
        self.assertFalse(newSnapshot.exists())
        self.assertFalse(sid.exists())

    @patch('time.sleep') # speed up unittest
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_with_errors(self, takeSnapshot, sleep):
        takeSnapshot.return_value = [False, True]
        self.assertTrue(self.sn.backup())

    @patch('time.sleep') # speed up unittest
    @patch('tools.onBattery')
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_no_backup_on_battery(self, takeSnapshot, onBattery, sleep):
        self.cfg.setNoSnapshotOnBattery(True)
        takeSnapshot.return_value = [True, False]

        # run on battery
        onBattery.return_value = True
        self.assertFalse(self.sn.backup(force = False))
        self.assertFalse(takeSnapshot.called)

        # force run
        self.assertFalse(self.sn.backup(force = True))
        self.assertTrue(takeSnapshot.called)
        takeSnapshot.reset_mock()

        # ignore Battery
        self.cfg.setNoSnapshotOnBattery(False)
        self.assertFalse(self.sn.backup(force = False))
        self.assertTrue(takeSnapshot.called)

    @patch('time.sleep') # speed up unittest
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_scheduled(self, takeSnapshot, sleep):
        # first run without timestamp
        takeSnapshot.return_value = [True, False]
        self.assertFalse(self.sn.backup(force = False))
        self.assertTrue(takeSnapshot.called)
        takeSnapshot.reset_mock()

        # second run doesn't use an anacron-like schedule
        tools.writeTimeStamp(self.cfg.anacronSpoolFile())
        self.assertFalse(self.sn.backup(force = False))
        self.assertTrue(takeSnapshot.called)
        takeSnapshot.reset_mock()

        # third run uses anacron-like schedule so it should not run
        self.cfg.setScheduleMode(self.cfg.REPEATEDLY)
        self.assertFalse(self.sn.backup(force = False))
        self.assertFalse(takeSnapshot.called)

        # finally force
        self.assertFalse(self.sn.backup(force = True))
        self.assertTrue(takeSnapshot.called)

    @patch('time.sleep') # speed up unittest
    @patch.object(ApplicationInstance, 'check')
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_already_running(self, takeSnapshot, check, sleep):
        check.return_value = False
        takeSnapshot.return_value = [True, False]
        self.assertTrue(self.sn.backup())
        self.assertFalse(takeSnapshot.called)

    @patch('time.sleep') # speed up unittest
    @patch.object(PluginManager, 'processBegin')
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_plugin_prevented_backup(self, takeSnapshot, processBegin, sleep):
        processBegin.return_value = False
        takeSnapshot.return_value = [True, False]
        self.assertTrue(self.sn.backup())
        self.assertFalse(takeSnapshot.called)

    @patch('time.sleep') # speed up unittest
    @patch.object(config.Config, 'isConfigured')
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_not_configured(self, takeSnapshot, isConfigured, sleep):
        isConfigured.return_value = False
        takeSnapshot.return_value = [True, False]
        self.assertTrue(self.sn.backup())
        self.assertFalse(takeSnapshot.called)

    @patch('time.sleep') # speed up unittest
    @patch.object(Mount, 'mount')
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_mount_exception(self, takeSnapshot, mount, sleep):
        mount.side_effect = MountException()
        takeSnapshot.return_value = [True, False]
        self.assertTrue(self.sn.backup())
        self.assertFalse(takeSnapshot.called)

    @patch('time.sleep') # speed up unittest
    @patch.object(Mount, 'umount')
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_umount_exception(self, takeSnapshot, umount, sleep):
        umount.side_effect = MountException()
        takeSnapshot.return_value = [True, False]
        self.assertFalse(self.sn.backup())

    @patch('time.sleep') # speed up unittest
    @patch.object(config.Config, 'canBackup')
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_cant_backup(self, takeSnapshot, canBackup, sleep):
        canBackup.return_value = False
        takeSnapshot.return_value = [True, False]
        self.assertTrue(self.sn.backup())
        self.assertFalse(takeSnapshot.called)

    @patch('time.sleep') # speed up unittest
    @patch('snapshots.Snapshots.takeSnapshot')
    def test_takeSnapshot_exception_cleanup(self, takeSnapshot, sleep):
        takeSnapshot.side_effect = Exception('Boom')
        new = snapshots.NewSnapshot(self.cfg)
        new.makeDirs()
        self.assertTrue(new.exists())
        with self.assertRaises(Exception):
            self.sn.backup()
        self.assertFalse(new.saveToContinue)
        self.assertTrue(new.failed)
