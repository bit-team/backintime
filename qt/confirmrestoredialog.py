# SPDX-FileCopyrightText: © 2025 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
#
# Split from app.py
"""Module offering a confirmation dialog shown before restoring backup elements
starts.
"""
from PyQt6.QtWidgets import (QAbstractItemView,
                             QDialog,
                             QDialogButtonBox,
                             QLabel,
                             QListWidget,
                             QVBoxLayout,
                             QWidget)
from bitwidgets import WrappedCheckBox


class ConfirmRestoreDialog(QDialog):
    """A dialog asking user details if and how to perform restoring a specific
    backup or some of backup elements."""

    # pylint: disable-next=too-many-arguments, too-many-positional-arguments
    def __init__(self,
                 parent: QWidget,
                 paths: list[str],
                 to_path: str | None,
                 backup_on_restore: bool,
                 backup_suffix: str):
        super().__init__(parent)
        self.setWindowTitle(_('Question'))

        self._paths = paths
        self._to_path = to_path

        layout = QVBoxLayout()
        self.setLayout(layout)

        # question
        layout.addWidget(self._create_question_label())

        # path list
        layout.addWidget(self._create_paths_list(), stretch=2)

        # three checkboxes
        self._checkbox_backup = self._create_checkbox_backup(
            backup_on_restore, backup_suffix)
        self._checkbox_only_new = self._create_checkbox_only_new()
        self._checkbox_delete = self._create_checkbox_delete()
        layout.addWidget(self._checkbox_backup)
        layout.addWidget(self._checkbox_only_new)
        layout.addWidget(self._checkbox_delete)

        # yes/no buttons
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes
            | QDialogButtonBox.StandardButton.No)
        btn_box.button(QDialogButtonBox.StandardButton.No).setDefault(True)

        layout.addWidget(btn_box)

        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

    def _create_checkbox_backup(self,
                                backup_on_restore: bool,
                                backup_suffix: str
                                ) -> WrappedCheckBox:

        suffix = f'<code>{backup_suffix}</code>'

        label = _('Create backup copies with trailing {suffix} before '
                  'overwriting or removing local elements.'
                  ).format(suffix=suffix)

        tooltip = [
            _("Before restoring, newer versions of files will be renamed "
              "with the appended {suffix}. These files can be removed "
              "with the following command:").format(suffix=suffix),
            f'<code>find ./ -name "*{backup_suffix}" -delete</code>'
        ]

        check_box = WrappedCheckBox(label, tooltip)
        check_box.checked = backup_on_restore

        return check_box

    def _create_checkbox_only_new(self) -> WrappedCheckBox:
        label = _(
            'Only restore elements which do not exist or are newer than those '
            'in destination. Using "{rsync_example}" option.').format(
                rsync_example='<code>rsync --update</code>')

        tooltip = [
            "From 'man rsync':",
            "",
            "This forces rsync to skip any files which exist on the "
            "destination and have a modified time that is newer than the "
            "source file. (If an existing destination file has a "
            "modification time equal to the source file’s, it will be "
            "updated if the sizes are different.)",
            "",
            "Note that this does not affect the copying of dirs, symlinks, "
            "or other special files. Also, a difference of file format "
            "between the sender and receiver is always considered to be "
            "important enough for an update, no matter what date is on the "
            "objects. In other words, if the source has a directory where "
            "the destination has a file, the transfer would occur regardless "
            "of the timestamps.",
            "",
            "This option is a transfer rule, not an exclude, so it doesn’t "
            "affect the data that goes into the file-lists, and thus it "
            "doesn’t affect deletions. It just limits the files that the "
            "receiver requests to be transferred."
        ]

        return WrappedCheckBox(label, tooltip)

    def _create_paths_list(self) -> QListWidget:
        list_widget = QListWidget()
        list_widget.addItems(self._paths)

        list_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection)

        return list_widget

    def _create_checkbox_delete(self) -> WrappedCheckBox:
        label = _('Remove newer elements in original directory.')
        tooltip = _(
            'Restore selected files or directories to the original '
            'destination and delete files or directories which are not in the '
            'backup. Be extremely careful because this will delete files and '
            'directories which were excluded during the creation of the '
            'backup.')

        return WrappedCheckBox(label, tooltip)

    def _create_question_label(self) -> QLabel:
        if self._to_path:
            msg = ngettext(
                # singular
                'Really restore this element into the new directory?',
                # plural
                'Really restore these elements into the new directory?',
                len(self._paths))
            msg = f'{msg}\n{self._to_path}'

            return QLabel(msg)

        msg = ngettext(
            # singular
            'Really restore this element?',
            # plural
            'Really restore these elements?',
            len(self._paths))

        return QLabel(msg)

    def answer(self) -> bool:
        """Show the dialog and return the users answer.
        """
        return self.exec() == QDialog.DialogCode.Accepted

    @property
    def create_backup_copies(self) -> bool:
        """Create backup copies before overwriting/removing."""
        return self._checkbox_backup.isChecked()

    @property
    def only_newer_or_not_existing(self) -> bool:
        """Restore only newer or not existing elements."""
        return self._checkbox_only_new.isChecked()

    @property
    def delete_newer(self) -> bool:
        """Remove newer elements in original folder."""
        return self._checkbox_delete.isChecked()

    def get_values_as_dict(self) -> dict:
        """This is a workaround until more refactoring is done.

        This dict is handed to RestoreDialog to RestoreThread (see kwargs).
        """
        return {
            'backup': self.create_backup_copies,
            'only_new': self.only_newer_or_not_existing,
            'delete': self.delete_newer
        }
