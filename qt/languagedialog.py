import gettext
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication,
                             QDialog,
                             QWidget,
                             QScrollArea,
                             QGridLayout,
                             QVBoxLayout,
                             QFrame,
                             QDialogButtonBox,
                             QLabel,
                             QPushButton,
                             QRadioButton,
                             )
import tools
import qttools


class LanguageDialog(QDialog):
    def __init__(self):
        super().__init__()

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
        # button.clicked.connect(self.slot_button)
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

    def _language_widget(self):
        """
        nativ | ownlocal -> tooltip: english (code)
        """
        grid = QGridLayout()
        wdg = QWidget(self)
        wdg.setLayout(grid)

        # Entry: System default language
        r = QRadioButton(
            'System default | {}'.format(_('System default')), self)
        r.setToolTip('X')
        r.lang_code = None
        grid.addWidget(r, 1, 1)

        # Sort by language code but keep English on top
        langs = tools.get_language_names()
        sorted_codes = sorted(langs.keys())
        sorted_codes.remove('en')
        sorted_codes = ['en'] + sorted_codes

        # Number of columns used for radio buttons
        number_of_columns = 3

        # Low-resolution screens (XGA or less)
        if QApplication.primaryScreen().size().width() <= 1024:
            print(QApplication.primaryScreen().size().width())

            # # Approach A: reduce font size in radio buttons
            # # 80% of regular font size.
            # # Qt do not support % values in CSS
            # css = 'QRadioButton{font-size: ' \
            #     + str(int(r.font().pointSize() * 0.8)) \
            #     + 'pt;}'
            # wdg.setStyleSheet(css)

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
                if qttools.can_render(names[1], wdg):
                    label = f'{names[1]} ({label})'

                tooltip = f'{names[2]} ({code})'

            r = QRadioButton(label, self)
            r.setToolTip(tooltip)
            r.toggled.connect(self.slot_radio)
            r.lang_code = code

            row = idx - ((col - 1) * per_col_n)
            if row > per_col_n:
                row = 1
                col = col + 1

            grid.addWidget(r, row, col)

        return wdg

    def slot_radio(self, val):
        btn = self.sender()

        if btn.isChecked():
            print(f'{btn.lang_code=}')

    def slot_button(self):
        print('X'*44)
