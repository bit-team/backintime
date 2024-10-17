# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Module with an improved check box widget."""
from PyQt6.QtWidgets import QCheckBox, QWidget


class StateBindCheckBox(QCheckBox):
    """A check box binding other widgets enabled states to its own check state.

    If the check box is checked all bound widgets are enabled. If the box is
    not checked all bound widgets are disabled.
    """

    def __init__(self,
                 text: str,
                 parent: QWidget,
                 bind: QWidget = None):
        """
        Args:
            text: Label for this check box.
            parent: The parent widget.
            bind: One or a list of widgets to bind.
        """
        super().__init__(text=text, parent=parent)

        self._widgets = []

        if bind:
            self.bind(bind)

        self.stateChanged.connect(self._slot_state_changed)

    def bind(self, widget: QWidget) -> None:
        """The enabled state of `widget` is bound to the check state of the
        check box.

        Args:
            widget: The widget to bind.
        """
        self._widgets.append(widget)
        self._slot_state_changed(self.isChecked())

    def _slot_state_changed(self, state) -> None:
        """Set the enabled state of each bound widget based on the check state
        of the box."""
        for wdg in self._widgets:
            wdg.setEnabled(state)
