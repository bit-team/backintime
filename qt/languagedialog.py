import gettext
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog,
                             QWidget,
                             QScrollArea,
                             QGridLayout,
                             QVBoxLayout,
                             QFrame,
                             QDialogButtonBox,
                             QLabel,
                             QPushButton,
                             QRadioButton,
                             QSizePolicy,
                             )
import tools
import qttools


class LanguageDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle(_('Language selection'))

        scroll = QScrollArea(self)
        # scroll.setWidgetResizable(True)
        # scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setWidget(self._language_widget())

        button = QDialogButtonBox(QDialogButtonBox.Apply)
        # button.clicked.connect(self.slot_button)
        button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(scroll)
        layout.addWidget(button)

    def _language_widget(self):
        """
        nativ | ownlocal -> tooltip: english (code)
        """
        grid = QGridLayout()
        wdg = QWidget(self)
        wdg.setLayout(grid)

        # System default
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

        # 3 columns
        per_col_n = len(sorted_codes) / 3
        per_col_n = int(per_col_n) + 1

        col = 1
        for idx, code in enumerate(sorted_codes, 2):
            names = langs[code]

            if None in names[:2]:
                label = names[2]
            else:
                native = f'{names[1]} | ' \
                    if qttools.can_render(names[1], wdg) else ''
                label = f'{native}{names[0]}'

            r = QRadioButton(label, self)
            r.setToolTip('{} ({})'.format(names[2], code))
            r.toggled.connect(self.slot_radio)
            r.lang_code = code

            row = idx - ((col - 1) * per_col_n)
            if row > per_col_n:
                row = 1
                col = col + 1

            grid.addWidget(r, row, col)

        wdg.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        return wdg

    def slot_radio(self, val):
        btn = self.sender()

        if btn.isChecked():
            print(f'{btn.lang_code=}')

    def slot_button(self):
        print('X'*44)
