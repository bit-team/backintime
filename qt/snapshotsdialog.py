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
import subprocess
import shlex

from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *

import tools
import restoredialog
import messagebox
import qttools
import snapshots
import logger

DIFF_PARAMS = '%1 %2'

if tools.checkCommand('meld'):
    DIFF_CMD = 'meld'
elif tools.checkCommand('kompare'):
    DIFF_CMD = 'kompare'
else:
    DIFF_CMD = ''


class DiffOptionsDialog(QDialog):
    def __init__(self, parent):
        super(DiffOptionsDialog, self).__init__(parent)
        self.config = parent.config

        import icon
        self.setWindowIcon(icon.DIFF_OPTIONS)
        self.setWindowTitle(_('Options about comparing snapshots'))

        self.mainLayout = QGridLayout(self)

        cmd = self.config.strValue('qt.diff.cmd', DIFF_CMD)
        params = self.config.strValue('qt.diff.params', DIFF_PARAMS)

        self.mainLayout.addWidget(QLabel(_('Command:')), 0, 0)
        self.editCmd = QLineEdit(cmd, self)
        self.mainLayout.addWidget(self.editCmd, 0, 1)

        self.mainLayout.addWidget(QLabel(_('Parameters:')), 1, 0)
        self.editParams = QLineEdit(params, self)
        self.mainLayout.addWidget(self.editParams, 1, 1)

        self.mainLayout.addWidget(
            QLabel(_('Use %1 and %2 for path parameters')), 2, 1)

        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                     | QDialogButtonBox.StandardButton.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        self.mainLayout.addWidget(buttonBox, 3, 0, 3, 2)

    def accept(self):
        """OK was clicked"""

        # Get values from text dialogs fields
        cmd = self.editCmd.text()
        params = self.editParams.text()

        # Any value?
        if not cmd:
            messagebox.info(_('Please set a diff command or press Cancel.'))
            return

        # Command exists?
        if tools.checkCommand(cmd) == False:
            messagebox.info(_(
                'The command "{cmd}" cannot be found on this system. Please '
                'try something else or press Cancel.').format(cmd=cmd))
            return

        if not params:
            params = DIFF_PARAMS
            messagebox.critical(
                self,
                _('No parameters set for the diff command. Using '
                  'default value "{params}".').format(params=params))

        # save new values
        self.config.setStrValue('qt.diff.cmd', cmd)
        self.config.setStrValue('qt.diff.params', params)
        self.config.save()

        super(DiffOptionsDialog, self).accept()


class SnapshotsDialog(QDialog):
    def __init__(self, parent, sid, path):
        super(SnapshotsDialog, self).__init__(parent)
        self.parent = parent
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.snapshotsList = parent.snapshotsList
        self.qapp = parent.qapp
        import icon

        self.sid = sid
        self.path = path

        self.setWindowIcon(icon.SNAPSHOTS)
        self.setWindowTitle(_('Snapshots'))

        self.mainLayout = QVBoxLayout(self)

        #path
        self.editPath = QLineEdit(self.path, self)
        self.editPath.setReadOnly(True)
        self.mainLayout.addWidget(self.editPath)

        #list different snapshots only
        self.cbOnlyDifferentSnapshots = QCheckBox(
            _('Differing snapshots only'), self)
        self.mainLayout.addWidget(self.cbOnlyDifferentSnapshots)
        self.cbOnlyDifferentSnapshots.stateChanged.connect(self.cbOnlyDifferentSnapshotsChanged)

        #list equal snapshots only
        layout = QHBoxLayout()
        self.mainLayout.addLayout(layout)
        self.cbOnlyEqualSnapshots = QCheckBox(
            _('List only snapshots that are equal to:'), self)
        self.cbOnlyEqualSnapshots.stateChanged.connect(
            self.cbOnlyEqualSnapshotsChanged)
        layout.addWidget(self.cbOnlyEqualSnapshots)

        self.comboEqualTo = qttools.SnapshotCombo(self)
        self.comboEqualTo.currentIndexChanged.connect(self.comboEqualToChanged)
        self.comboEqualTo.setEnabled(False)
        layout.addWidget(self.comboEqualTo)

        # deep check
        self.cbDeepCheck = QCheckBox(_('Deep check (more accurate, but slow)'), self)
        self.mainLayout.addWidget(self.cbDeepCheck)
        self.cbDeepCheck.stateChanged.connect(self.cbDeepCheckChanged)

        #toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.setFloatable(False)
        self.mainLayout.addWidget(self.toolbar)

        #toolbar restore
        menuRestore = QMenu(self)
        action = menuRestore.addAction(icon.RESTORE, _('Restore'))
        action.triggered.connect(self.restoreThis)
        action = menuRestore.addAction(icon.RESTORE_TO, _('Restore to …'))
        action.triggered.connect(self.restoreThisTo)

        self.btnRestore = self.toolbar.addAction(icon.RESTORE, _('Restore'))
        self.btnRestore.setMenu(menuRestore)
        self.btnRestore.triggered.connect(self.restoreThis)

        #btn delete
        self.btnDelete = self.toolbar.addAction(icon.DELETE_FILE, _('Delete'))
        self.btnDelete.triggered.connect(self.btnDeleteClicked)

        #btn select_all
        self.btnSelectAll = self.toolbar.addAction(icon.SELECT_ALL, _('Select All'))
        self.btnSelectAll.triggered.connect(self.btnSelectAllClicked)

        #snapshots list
        self.timeLine = qttools.TimeLine(self)
        self.mainLayout.addWidget(self.timeLine)
        self.timeLine.itemSelectionChanged.connect(self.timeLineChanged)
        self.timeLine.itemActivated.connect(self.timeLineExecute)

        # Diff
        layout = QHBoxLayout()
        self.mainLayout.addLayout(layout)

        self.btnDiff = QPushButton(_('Compare'), self)
        layout.addWidget(self.btnDiff)
        self.btnDiff.clicked.connect(self.btnDiffClicked)
        self._update_btn_diff()

        self.comboDiff = qttools.SnapshotCombo(self)
        layout.addWidget(self.comboDiff, 2)

        #buttons
        buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.btnGoto =   buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.btnCancel = buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        self.btnGoto.setText(_('Go To'))
        btnDiffOptions = buttonBox.addButton(_('Options'), QDialogButtonBox.ButtonRole.HelpRole)
        btnDiffOptions.setIcon(icon.DIFF_OPTIONS)

        self.mainLayout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        btnDiffOptions.clicked.connect(self.btnDiffOptionsClicked)

        #
        self.cbDeepCheck.setEnabled(False)

        full_path = self.sid.pathBackup(self.path)
        if os.path.islink(full_path):
            self.cbDeepCheck.hide()
        elif os.path.isdir(full_path):
            self.cbOnlyDifferentSnapshots.hide()
            self.cbOnlyEqualSnapshots.hide()
            self.comboEqualTo.hide()
            self.cbDeepCheck.hide()

        #update list and combobox
        self.UpdateSnapshotsAndComboEqualTo()

    def addSnapshot(self, sid):
        self.timeLine.addSnapshot(sid)

        #add to combo
        self.comboDiff.addSnapshotID(sid)

        if self.sid == sid:
            self.comboDiff.setCurrentSnapshotID(sid)
        self.comboDiff.checkSelection()

    def updateSnapshots(self):
        self.timeLine.clear()
        self.comboDiff.clear()

        equal_to_sid = self.comboEqualTo.currentSnapshotID()
        if self.cbOnlyEqualSnapshots.isChecked() and equal_to_sid:
            equal_to = equal_to_sid.pathBackup(self.path)
        else:
            equal_to = False
        snapshotsFiltered = self.snapshots.filter(self.sid, self.path,
                                self.snapshotsList,
                                self.cbOnlyDifferentSnapshots.isChecked(),
                                self.cbDeepCheck.isChecked(),
                                equal_to)
        for sid in snapshotsFiltered:
            self.addSnapshot(sid)

        self.updateToolbar()

    def UpdateComboEqualTo(self):
        self.comboEqualTo.clear()
        snapshotsFiltered = self.snapshots.filter(self.sid, self.path, self.snapshotsList)
        for sid in snapshotsFiltered:
            self.comboEqualTo.addSnapshotID(sid)

            if sid == self.sid:
                self.comboEqualTo.setCurrentSnapshotID(sid)

        self.comboEqualTo.checkSelection()

    def UpdateSnapshotsAndComboEqualTo(self):
        self.updateSnapshots()
        self.UpdateComboEqualTo()

    def cbOnlyDifferentSnapshotsChanged(self):
        enabled = self.cbOnlyDifferentSnapshots.isChecked()
        self.cbOnlyEqualSnapshots.setEnabled(not enabled)
        self.cbDeepCheck.setEnabled(enabled)

        self.updateSnapshots()

    def cbOnlyEqualSnapshotsChanged(self):
        enabled = self.cbOnlyEqualSnapshots.isChecked()
        self.comboEqualTo.setEnabled(enabled)
        self.cbOnlyDifferentSnapshots.setEnabled(not enabled)
        self.cbDeepCheck.setEnabled(enabled)

        self.updateSnapshots()

    def cbDeepCheckChanged(self):
        self.updateSnapshots()

    def updateToolbar(self):
        sids = self.timeLine.selectedSnapshotIDs()

        if not sids:
            enable_restore = False
            enable_delete = False
        elif len(sids) == 1:
            enable_restore = not sids[0].isRoot
            enable_delete  = not sids[0].isRoot
        else:
            enable_restore = False
            enable_delete = True
            for sid in sids:
                if sid.isRoot:
                    enable_delete = False

        self.btnRestore.setEnabled(enable_restore)
        self.btnDelete.setEnabled(enable_delete)

    def restoreThis(self):
        # See #1485 as related bug report
        sid = self.timeLine.currentSnapshotID()
        if not sid.isRoot:
            restoredialog.restore(self, sid, self.path)  # pylint: disable=E1101

    def restoreThisTo(self):
        # See #1485 as related bug report
        sid = self.timeLine.currentSnapshotID()
        if not sid.isRoot:
            restoredialog.restore(self, sid, self.path, None)  # pylint: disable=E1101

    def timeLineChanged(self):
        self.updateToolbar()

    def timeLineExecute(self, item, column):
        if self.qapp.keyboardModifiers() and Qt.ControlModifier:
            return

        sid = self.timeLine.currentSnapshotID()
        if not sid:
            return

        full_path = sid.pathBackup(self.path)
        if not os.path.exists(full_path):
            return

        # prevent backup data from being accidentally overwritten
        # by create a temporary local copy and only open that one
        if not isinstance(self.sid, snapshots.RootSnapshot):
            full_path = self.parent.tmpCopy(full_path, sid)

        self.run = QDesktopServices.openUrl(QUrl(full_path))

    def btnDiffClicked(self):
        sid1 = self.timeLine.currentSnapshotID()
        sid2 = self.comboDiff.currentSnapshotID()
        if not sid1 or not sid2:
            return

        path1 = sid1.pathBackup(self.path)
        path2 = sid2.pathBackup(self.path)

        # check if the 2 paths are different
        if path1 == path2:
            messagebox.critical(
                self, _("You can't compare a snapshot to itself."))
            return

        diffCmd = self.config.strValue('qt.diff.cmd', DIFF_CMD)
        diffParams = self.config.strValue('qt.diff.params', DIFF_PARAMS)

        # prevent backup data from being accidentally overwritten
        # by create a temporary local copy and only open that one
        if not isinstance(sid1, snapshots.RootSnapshot):
            path1 = self.parent.tmpCopy(path1, sid1)
        if not isinstance(sid2, snapshots.RootSnapshot):
            path2 = self.parent.tmpCopy(path2, sid2)

        params = diffParams
        params = params.replace('%1', '"%s"' % path1)
        params = params.replace('%2', '"%s"' % path2)

        cmd = diffCmd + ' ' + params

        logger.debug(f'Compare two snapshots with command {cmd}.')

        subprocess.Popen(shlex.split(cmd))

    def _update_btn_diff(self):
        """Enable the Compare button if diff command is set otherwise Disable
        it."""
        cmd = self.config.strValue('qt.diff.cmd', DIFF_CMD)
        self.btnDiff.setDisabled(not cmd)

    def btnDiffOptionsClicked(self):
        DiffOptionsDialog(self).exec()
        self._update_btn_diff()

    def comboEqualToChanged(self, index):
        self.updateSnapshots()

    def btnDeleteClicked(self):
        items = self.timeLine.selectedItems()

        if not items:
            return

        elif len(items) == 1:
            msg = _('Do you really want to delete {file} in snapshot '
                    '{snapshot_id}?').format(
                        file=f'"{self.path}"',
                        snapshot_id=f'"{items[0].snapshotID()}"')

        else:
            msg = _('Do you really want to delete {file} in {count} '
                    'snapshots?').format(
                        file=f'"{self.path}"', count=len(items))

        msg = _('WARNING: This cannot be revoked.')

        answer = messagebox.warningYesNo(self, msg)
        if answer == QMessageBox.StandardButton.Yes:

            for item in items:
                item.setFlags(Qt.ItemFlag.NoItemFlags)

            thread = RemoveFileThread(self, items)
            thread.started.connect(lambda: self.btnGoto.setDisabled(True))
            thread.finished.connect(lambda: self.btnGoto.setDisabled(False))
            thread.started.connect(lambda: self.btnDelete.setDisabled(True))
            thread.finished.connect(lambda: self.btnDelete.setDisabled(False))
            thread.finished.connect(self.UpdateSnapshotsAndComboEqualTo)
            self.btnCancel.clicked.connect(thread.terminate)
            thread.start()

            exclude = self.config.exclude()
            msg = _('Exclude {path} from future snapshots?').format(
                path=f'"{self.path}"')

            if self.path not in exclude:
                answer = messagebox.warningYesNo(self, msg)

                if answer == QMessageBox.StandardButton.Yes:
                    exclude.append(self.path)
                    self.config.setExclude(exclude)

    def btnSelectAllClicked(self):
        """
        select all expect 'Now'
        """
        self.timeLine.clearSelection()
        for item in self.timeLine.iterSnapshotItems():
            if not isinstance(item.snapshotID(), snapshots.RootSnapshot):
                item.setSelected(True)

    def accept(self):
        sid = self.timeLine.currentSnapshotID()
        if sid:
            self.sid = sid
        super(SnapshotsDialog, self).accept()


class RemoveFileThread(QThread):
    """
    remove files in background thread so GUI will not freeze
    """
    def __init__(self, parent, items):
        self.parent = parent
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.items = items
        super(RemoveFileThread, self).__init__(parent)

    def run(self):
        #inhibit suspend/hibernate during delete
        self.config.inhibitCookie = tools.inhibitSuspend(toplevel_xid = self.config.xWindowId,
                                                         reason = 'deleting files')

        for item in self.items:
            self.snapshots.deletePath(item.snapshotID(), self.parent.path)
            try:
                item.setHidden(True)
            except RuntimeError:
                #item has been deleted
                #probably because user refreshed treeview
                pass

        #release inhibit suspend
        if self.config.inhibitCookie:
            self.config.inhibitCookie = tools.unInhibitSuspend(*self.config.inhibitCookie)
