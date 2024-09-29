# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raak
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""A widget to setup an SSH proxy."""
import getpass
from PyQt6.QtWidgets import (QVBoxLayout,
                             QHBoxLayout,
                             QWidget,
                             QLabel,
                             QLineEdit,
                             QCheckBox)
from PyQt6.QtCore import Qt

import qttools


class SshProxyWidget(QWidget):
    """Used in SSH snapshot profiles on the General tab.

    Dev note by buhtz (2024-04): Just a quick n dirty solution until the
    re-design and re-factoring of the whole dialog.
    """

    def __init__(self, parent, host, port, user):
        super().__init__(parent)

        if host == '':
            port = ''
            user = ''

        elif isinstance(port, int):
            port = str(port)

        vlayout = QVBoxLayout(self)
        # zero margins
        vlayout.setContentsMargins(0, 0, 0, 0)

        self._checkbox = QCheckBox(_('SSH Proxy'), self)
        vlayout.addWidget(self._checkbox)
        self._checkbox.stateChanged.connect(self._slot_checkbox_changed)

        hlayout = QHBoxLayout()
        vlayout.addLayout(hlayout)

        hlayout.addWidget(QLabel(_('Host:'), self))
        self.host_edit = QLineEdit(host, self)
        hlayout.addWidget(self.host_edit)

        hlayout.addWidget(QLabel(_('Port:'), self))
        self.port_edit = QLineEdit(port, self)
        hlayout.addWidget(self.port_edit)

        hlayout.addWidget(QLabel(_('User:'), self))
        self.user_edit = QLineEdit(user, self)
        hlayout.addWidget(self.user_edit)

        if host == '':
            self._disable()

        qttools.set_wrapped_tooltip(
            self,
            _('Connect to the target host via this proxy (also known as a '
              'jump host). See "-J" in the "ssh" command documentation or '
              '"ProxyJump" in "ssh_config" man page for details.')
        )

    def _slot_checkbox_changed(self, state):
        if Qt.CheckState(state) == Qt.CheckState.Checked:
            self._enable()
        else:
            self._disable()

    def _set_default(self):
        """Set GUI elements back to default."""
        self.host_edit.setText('')
        self.port_edit.setText('22')
        self.user_edit.setText(getpass.getuser())

    def _disable(self):
        self._set_default()
        self._enable(False)

    def _enable(self, enable=True):
        # QEdit and QLabel's
        lay = self.layout().itemAt(1)
        for idx in range(lay.count()):
            lay.itemAt(idx).widget().setEnabled(enable)

    def values(self) -> dict[str, str, str]:
        """The widgets values as a dict.

        Returns:
            dict: A 3-item dict with keys "host", "port" and "user".
        """
        if self._checkbox.isChecked():
            return {
                'host': self.host_edit.text(),
                'port': self.port_edit.text(),
                'user': self.user_edit.text(),
            }

        return {
            'host': '',
            'port': '',
            'user': '',
        }
