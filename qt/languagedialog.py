import locale
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication,
                             QDialog,
                             QWidget,
                             QScrollArea,
                             QGridLayout,
                             QVBoxLayout,
                             QDialogButtonBox,
                             QRadioButton,
                             )
import tools
import qttools
import logger


class LanguageDialog(QDialog):
    def __init__(self, used_language_code: str, configured_language_code: str):
        super().__init__()

        self.used_language_code = used_language_code
        self.configured_language_code = configured_language_code

        self.setWindowTitle(_('Language selection'))
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, True)

        scroll = QScrollArea(self)
        # scroll.setWidgetResizable(True)
        # scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self._language_widget())
        self._scroll = scroll

        # Fit the width of scrollarea to its content
        new_width = self._calculate_scroll_area_width()
        self._scroll.setMinimumWidth(new_width)

        button = QDialogButtonBox(QDialogButtonBox.Apply, self)
        button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(button)

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

        print(f'{r.lang_code=} {self.used_language_code=} {self.configured_language_code=}')

        # Does this radio button reflect the current used language code?
        if r.lang_code == self.used_language_code:
            # Check this radio button only if its language code is NOT
            # the current systems locale. Because that is represented
            # by another (the first) radio button.
            if not locale.getdefaultlocale()[0].startswith(r.lang_code):
                r.setChecked(True)

        # "System default"
        elif self.configured_language_code == '' and r.lang_code == None:
            r.setChecked(True)

        return r


    def _language_widget(self):
        grid = QGridLayout()
        widget = QWidget(self)
        widget.setLayout(grid)

        # Entry: System default language
        label = 'System default'
        translated_label = _(label)
        if label != translated_label:
            label = f'| {translated_label}'

        tooltip = _('Use operating systems language.')
        code = None
        r = self._create_radio_button(code, label, tooltip)
        grid.addWidget(r, 1, 1)

        # Sort by language code but keep English on top
        langs = tools.get_language_names(self.used_language_code)
        sorted_codes = sorted(langs.keys())
        sorted_codes.remove('en')
        sorted_codes = ['en'] + sorted_codes

        # Number of columns used for radio buttons
        number_of_columns = 3

        # Low-resolution screens (XGA or less)
        if QApplication.primaryScreen().size().width() <= 1024:
            print(QApplication.primaryScreen().size())  # DEBUG

            # # Approach A: reduce font size in radio buttons
            # # 80% of regular font size.
            # # Qt do not support % values in CSS
            # css = 'QRadioButton{font-size: ' \
            #     + str(int(r.font().pointSize() * 0.8)) \
            #     + 'pt;}'
            # widget.setStyleSheet(css)

            # Approach B:
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
                # Native letters available in current font?
                if qttools.can_render(names[1], widget):
                    label = f'{names[1]} ({label})'

                tooltip = f'{names[2]} ({code})'

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

    def slot_radio(self, val):
        btn = self.sender()

        if btn.isChecked():
            logger.debug(f'{btn.lang_code=}', self)
            self.language_code = btn.lang_code
