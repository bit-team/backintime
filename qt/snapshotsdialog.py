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
"""Stuff around the snapshots dialog.

That dialog will be removed and its functionality integrated into the main
window and its timeline widget."""
import os
import subprocess
import shlex

from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (QCheckBox,
                             QDialog,
                             QDialogButtonBox,
                             QGridLayout,
                             QHBoxLayout,
                             QLabel,
                             QLineEdit,
                             QMenu,
                             QPushButton,
                             QToolBar,
                             QVBoxLayout)
from PyQt6.QtCore import (Qt,
                          QThread,
                          QUrl)

from timeline import TimeLine
from bitwidgets import SnapshotCombo
import tools
import restoredialog
import messagebox
import snapshots
import logger
from inhibitsuspend import InhibitSuspend

DIFF_PARAMS = '%1 %2'

if tools.checkCommand('meld'):
    DIFF_CMD = 'meld'
elif tools.checkCommand('kompare'):
    DIFF_CMD = 'kompare'
else:
    DIFF_CMD = ''


class DiffOptionsDialog(QDialog):
    """Dialog to setup diff options"""

    def __init__(self, parent):
        super(DiffOptionsDialog, self).__init__(parent)
        self.config = parent.config

        import icon
        self.setWindowIcon(icon.DIFF_OPTIONS)
        self.setWindowTitle(_('Options about comparing backups'))

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
        if not tools.checkCommand(cmd):
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
    """The main snapshots dialog

    Dev note (buhtz, 2025-07-29): Scheduled to removed and replaced be features
    in the main window.
    """

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
        self.setWindowTitle(_('Backups'))

        self.mainLayout = QVBoxLayout(self)

        # path
        self.editPath = QLineEdit(self.path, self)
        self.editPath.setReadOnly(True)
        self.mainLayout.addWidget(self.editPath)

        # list different snapshots only
        self.cbOnlyDifferentSnapshots = QCheckBox(
            _('Differing backups only'), self)
        self.mainLayout.addWidget(self.cbOnlyDifferentSnapshots)
        self.cbOnlyDifferentSnapshots.stateChanged.connect(
            self.cbOnlyDifferentSnapshotsChanged)

        # list equal snapshots only
        layout = QHBoxLayout()
        self.mainLayout.addLayout(layout)
        self.cbOnlyEqualSnapshots = QCheckBox(
            _('List only backups that are equal to:'), self)
        self.cbOnlyEqualSnapshots.stateChanged.connect(
            self.cbOnlyEqualSnapshotsChanged)
        layout.addWidget(self.cbOnlyEqualSnapshots)

        self.comboEqualTo = SnapshotCombo(self)
        self.comboEqualTo.currentIndexChanged.connect(self.comboEqualToChanged)
        self.comboEqualTo.setEnabled(False)
        layout.addWidget(self.comboEqualTo)

        # deep check
        self.cbDeepCheck = QCheckBox(
            _('Deep check (more accurate, but slow)'), self)
        self.mainLayout.addWidget(self.cbDeepCheck)
        self.cbDeepCheck.stateChanged.connect(self.cbDeepCheckChanged)

        # toolbar
        self.toolbar = QToolBar(self)
        self.toolbar.setFloatable(False)
        self.mainLayout.addWidget(self.toolbar)

        # toolbar restore
        menuRestore = QMenu(self)
        action = menuRestore.addAction(icon.RESTORE, _('Restore'))
        action.triggered.connect(self.restoreThis)
        action = menuRestore.addAction(icon.RESTORE_TO, _('Restore to …'))
        action.triggered.connect(self.restoreThisTo)

        self.btnRestore = self.toolbar.addAction(icon.RESTORE, _('Restore'))
        self.btnRestore.setMenu(menuRestore)
        self.btnRestore.triggered.connect(self.restoreThis)

        # btn delete
        self.btnDelete = self.toolbar.addAction(icon.DELETE_FILE, _('Delete'))
        self.btnDelete.triggered.connect(self.btnDeleteClicked)

        # btn select_all
        self.btnSelectAll = self.toolbar.addAction(
            icon.SELECT_ALL, _('Select All'))
        self.btnSelectAll.triggered.connect(self.btnSelectAllClicked)

        # snapshots list
        self.timeLine = TimeLine(self)
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

        self.comboDiff = SnapshotCombo(self)
        layout.addWidget(self.comboDiff, 2)

        # buttons
        buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel)
        self.btnGoto = buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.btnCancel = buttonBox.button(
            QDialogButtonBox.StandardButton.Cancel)
        self.btnGoto.setText(_('Go To'))
        btnDiffOptions = buttonBox.addButton(
            _('Options'), QDialogButtonBox.ButtonRole.HelpRole)
        btnDiffOptions.setIcon(icon.DIFF_OPTIONS)

        self.mainLayout.addWidget(buttonBox)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        btnDiffOptions.clicked.connect(self.btnDiffOptionsClicked)

        self.cbDeepCheck.setEnabled(False)

        full_path = self.sid.pathBackup(self.path)
        if os.path.islink(full_path):
            self.cbDeepCheck.hide()
        elif os.path.isdir(full_path):
            self.cbOnlyDifferentSnapshots.hide()
            self.cbOnlyEqualSnapshots.hide()
            self.comboEqualTo.hide()
            self.cbDeepCheck.hide()

        # update list and combobox
        self.UpdateSnapshotsAndComboEqualTo()

    def addSnapshot(self, sid):
        self.timeLine.addSnapshot(sid)

        # add to combo
        self.comboDiff.add_snapshot_id(sid)

        if self.sid == sid:
            self.comboDiff.set_current_snapshot_id(sid)
        self.comboDiff.check_selection()

    def updateSnapshots(self):
        self.timeLine.clear()
        self.comboDiff.clear()

        equal_to_sid = self.comboEqualTo.current_snapshot_id()

        if self.cbOnlyEqualSnapshots.isChecked() and equal_to_sid:
            equal_to = equal_to_sid.pathBackup(self.path)
        else:
            equal_to = False

        snapshotsFiltered = self.snapshots.filter(
            base_sid=self.sid,
            base_path=self.path,
            snapshotsList=self.snapshotsList,
            list_diff_only=self.cbOnlyDifferentSnapshots.isChecked(),
            flag_deep_check=self.cbDeepCheck.isChecked(),
            list_equal_to=equal_to
        )

        for sid in snapshotsFiltered:
            self.addSnapshot(sid)

        self.updateToolbar()

    def UpdateComboEqualTo(self):
        self.comboEqualTo.clear()
        snapshotsFiltered = self.snapshots.filter(
            self.sid, self.path, self.snapshotsList)

        for sid in snapshotsFiltered:
            self.comboEqualTo.add_snapshot_id(sid)

            if sid == self.sid:
                self.comboEqualTo.set_current_snapshot_id(sid)

        self.comboEqualTo.check_selection()

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
        sids = self.timeLine.selected_snapshot_ids()

        if not sids:
            enable_restore = False
            enable_delete = False

        elif len(sids) == 1:
            enable_restore = not sids[0].isRoot
            enable_delete = not sids[0].isRoot

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
        sid = self.timeLine.current_snapshot_id()
        if not sid.isRoot:
            # pylint: disable-next=E1101
            restoredialog.restore(self, sid, self.path)

    def restoreThisTo(self):
        # See #1485 as related bug report
        sid = self.timeLine.current_snapshot_id()
        if not sid.isRoot:
            # pylint: disable-next=E1101
            restoredialog.restore(self, sid, self.path, None)

    def timeLineChanged(self):
        self.updateToolbar()

    def timeLineExecute(self, _item, _column):
        if self.qapp.keyboardModifiers() and Qt.ControlModifier:
            return

        sid = self.timeLine.current_snapshot_id()
        if not sid:
            return

        full_path = sid.pathBackup(self.path)
        if not os.path.exists(full_path):
            return

        # prevent backup data from being accidentally overwritten
        # by create a temporary local copy and only open that one
        if not isinstance(self.sid, snapshots.RootSnapshot):
            full_path = self.parent.tmpCopy(full_path, sid)

        QDesktopServices.openUrl(QUrl(full_path))

    def btnDiffClicked(self):
        sid1 = self.timeLine.current_snapshot_id()
        sid2 = self.comboDiff.current_snapshot_id()
        if not sid1 or not sid2:
            return

        path1 = sid1.pathBackup(self.path)
        path2 = sid2.pathBackup(self.path)

        # check if the 2 paths are different
        if path1 == path2:
            messagebox.critical(
                self, _('It is not possible to compare a backup to '
                        'itself, as the comparison would be redundant.')
            )
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

        logger.debug(f'Compare two backups with command {cmd}.')

        subprocess.Popen(shlex.split(cmd))

    def _update_btn_diff(self):
        """Enable the Compare button if diff command is set otherwise Disable
        it."""
        cmd = self.config.strValue('qt.diff.cmd', DIFF_CMD)
        self.btnDiff.setDisabled(not cmd)

    def btnDiffOptionsClicked(self):
        DiffOptionsDialog(self).exec()
        self._update_btn_diff()

    def comboEqualToChanged(self, _index):
        self.updateSnapshots()

    def btnDeleteClicked(self):
        items = self.timeLine.selectedItems()

        if not items:
            return

        if len(items) == 1:
            msg = _(
                'Really delete {file_or_dir} in backup {backup_id}?').format(
                        file_or_dir=f'"{self.path}"',
                        backup_id=f'"{items[0].snapshot_id}"')

        else:
            msg = _('Really delete {file_or_dir} in {count} backups?').format(
                        file_or_dir=f'"{self.path}"', count=len(items))

        msg = msg + '\n' + _('WARNING: This cannot be revoked.')

        if messagebox.question(msg):

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
            msg = _('Exclude {path} from future backups?').format(
                path=f'"{self.path}"')

            if self.path not in exclude:

                if messagebox.question(msg):
                    exclude.append(self.path)
                    self.config.setExclude(exclude)

    def btnSelectAllClicked(self):
        """
        select all expect 'Now'
        """
        self.timeLine.clearSelection()
        for item in self.timeLine.iter_snapshot_items():
            if not isinstance(item.snapshot_id, snapshots.RootSnapshot):
                item.setSelected(True)

    def accept(self):
        sid = self.timeLine.current_snapshot_id()
        if sid:
            self.sid = sid
        super(SnapshotsDialog, self).accept()


class RemoveFileThread(QThread):
    """
    remove files in background thread so GUI will not freeze
    """

    def __init__(self, parent, items):
        self.parent = parent
        # self.config = parent.config
        self.snapshots = parent.snapshots
        self.items = items
        super(RemoveFileThread, self).__init__(parent)

    def run(self):
        with InhibitSuspend(reason='deleting files'):

            for item in self.items:

                self.snapshots.deletePath(item.snapshot_id, self.parent.path)

                try:
                    item.setHidden(True)

                except RuntimeError:
                    # item has been deleted
                    # probably because user refreshed treeview
                    pass
