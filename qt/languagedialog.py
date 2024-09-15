# SPDX-FileCopyrightText: © 2023 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""Dialog window to choose GUI display language."""
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (QApplication,
                             QDialog,
                             QWidget,
                             QScrollArea,
                             QGridLayout,
                             QLayout,
                             QVBoxLayout,
                             QDialogButtonBox,
                             QRadioButton,
                             QLabel,
                             QToolTip,
                             )
import tools
import languages
import qttools

LOW_RESOLUTION_WIDTH = 1024


class LanguageDialog(QDialog):
    """Dialog to choose GUI language."""
    def __init__(self, used_language_code: str, configured_language_code: str):
        super().__init__()

        self.language_code = None
        self.used_language_code = used_language_code
        self.configured_language_code = configured_language_code

        self.setWindowTitle(_('Setup language'))
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

        scroll = QScrollArea(self)
        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self._language_widget())
        self._scroll = scroll

        # Fit the width of scrollarea to its content
        new_width = self._calculate_scroll_area_width()
        self._scroll.setMinimumWidth(new_width)

        buttonbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Ok,
            self)

        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(buttonbox)

    def _calculate_scroll_area_width(self):
        """Credits:
         - https://stackoverflow.com/a/9081579/4865723
         - https://stackoverflow.com/a/76738806/4865723
        """
        widget_width = self._scroll.widget().sizeHint().width()
        scrollbar_width = self._scroll.verticalScrollBar().sizeHint().width()

        return widget_width + scrollbar_width

    def _create_radio_button(self, lang_code, label, tooltip) -> QRadioButton:
        r = QRadioButton(label, self)
        r.setToolTip(tooltip)
        r.toggled.connect(self.slot_radio)
        r.lang_code = lang_code

        # Is it the current used AND configured language?
        if (r.lang_code == self.used_language_code
                and r.lang_code == self.configured_language_code):

            r.setChecked(True)

        # "System default"
        elif self.configured_language_code == '' and r.lang_code is None:
            r.setChecked(True)

        return r

    def _language_widget(self):
        grid = QGridLayout()
        widget = QWidget(self)
        widget.setLayout(grid)

        # Entry: System default language
        label = 'System default'
        translated_label = _('System default')

        # If translation for that term exists...
        if label != translated_label:
            # ...combine source and translated version.
            label = f'{label}\n{translated_label}'

        r = self._create_radio_button(
            lang_code=None,
            label=label,
            tooltip=_('Use operating systems language.')
        )
        grid.addWidget(r, 1, 1)

        # Sort by language code but keep English on top
        langs = tools.get_language_names(self.used_language_code)
        sorted_codes = sorted(langs.keys())
        sorted_codes.remove('en')
        sorted_codes = ['en'] + sorted_codes

        # Number of columns used for radio buttons
        number_of_columns = 3

        # Low-resolution screens (XGA or less)
        if QApplication.primaryScreen().size().width() <= LOW_RESOLUTION_WIDTH:
            # Use one columns less
            number_of_columns -= 1

        # Calculate number of entries (rows) per column
        per_col_n = len(sorted_codes) / number_of_columns
        per_col_n = int(per_col_n) + 1

        col = 1
        for idx, code in enumerate(sorted_codes, 2):
            names = langs[code]

            try:
                label = names[0]
            except TypeError:
                # Happens when no name for the language codes is available.
                # "names" is "None" in that case.
                label = code
                tooltip = f'Language code "{code}" unknown.'
            else:
                # Add language name in its native representation
                # if Native letters available in current font
                # but prevent duplications like e.g. "Deutsch\nDeutsch"
                if label != names[1] and qttools.can_render(names[1], widget):
                    label = f'{names[1]}\n{label}'

                # Tooltip: Language code
                tooltip = f'{names[2]} ({code})'

                # Tooltip: completeness of translation
                try:
                    complete = languages.completeness[code]
                except KeyError:
                    pass
                else:
                    tooltip = tooltip + '\n' \
                        + _('Translated: {percent}').format(
                            percent=f'{complete}%')

            # Create button
            r = self._create_radio_button(code, label, tooltip)

            # Calculate buttons location
            row = idx - ((col - 1) * per_col_n)
            if row > per_col_n:
                row = 1
                col = col + 1

            # Add the button
            grid.addWidget(r, row, col)

        return widget

    def slot_radio(self, _):
        """Radio button state toggled."""
        btn = self.sender()

        if btn.isChecked():
            self.language_code = btn.lang_code


class ApproachTranslatorDialog(QDialog):
    """Present a message to the users to motivate them contributing to the
    translation of Back In Time.
    """

    # (2023-08): Move to packages meta-data (pyproject.toml).
    _URL_PLATFORM = 'https://translate.codeberg.org/engage/backintime'
    _URL_PROJECT = 'https://github.com/bit-team/backintime'

    @classmethod
    def _complete_text(cls, language, percent):

        txt = _(
            'Hello'
            '\n'
            'You have used Back In Time in the {language} '
            'language a few times by now.'
            '\n'
            'The translation of your installed version of Back In Time '
            'into {language} is {perc} complete. Regardless of your '
            'level of technical expertise, you can contribute to the '
            'translation and thus Back In Time itself.'
            '\n'
            'Please visit the {translation_platform_url} if you wish '
            'to contribute. For further assistance and questions, '
            'please visit the {back_in_time_project_website}.'
            '\n'
            'We apologize for the interruption, and this message '
            'will not be shown again. This dialog is available at '
            'any time via the help menu.'
            '\n'
            'Your Back In Time Team'
        )

        # Wrap paragraphs in <p> tags.
        result = ''
        for t in txt.split('\n'):
            result = f'{result}<p>{t}</p>'

        # Insert data in placeholder variables.
        platform_url \
            = f'<a href="{cls._URL_PLATFORM}">' \
            + _('translation platform') \
            + '</a>'

        project_url \
            = f'<a href="{cls._URL_PROJECT}">Back In Time ' \
            + _('Website') \
            + ' </a>'

        result = result.format(
            language=f'<strong>{language}</strong>',
            perc=f'<strong>{percent} %</strong>',
            translation_platform_url=platform_url,
            back_in_time_project_website=project_url
        )

        return result

    def __init__(self, parent, language_name, completeness):
        super().__init__(parent)

        # screen_width = QApplication.primaryScreen().size().width()
        # min_width = 300 if screen_width <= 1080 else 450
        self.setMinimumWidth(400)

        # Note: Take into account that not only the
        self.setWindowTitle(_('Your translation'))
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)

        txt = self._complete_text(language_name, completeness)
        widget = QLabel(txt, self)
        widget.setWordWrap(True)
        widget.setOpenExternalLinks(True)
        widget.linkHovered.connect(self.slot_link_hovered)

        button = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, self)
        button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(widget)
        layout.addWidget(button)

        self._fix_size()

    def _fix_size(self):
        """The dialog is resized so it fits the content of the QLabel.

        Credits: https://stackoverflow.com/a/77012305/4865723
        """
        best = QLayout.closestAcceptableSize(self, QSize(self.width(), 1))

        if self.height() < best.height():
            self.resize(best)

    def resizeEvent(self, event):
        """See `_fixSize()`  for details."""
        super().resizeEvent(event)

        if event.oldSize().width() != event.size().width():
            QTimer.singleShot(0, self._fix_size)

        elif event.spontaneous():
            self._fix_size()

    def slot_link_hovered(self, url):
        """Show URL in tooltip without anoing http-protocol prefixf."""
        QToolTip.showText(QCursor.pos(), url.replace('https://', ''))
