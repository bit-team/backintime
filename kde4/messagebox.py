#    Copyright (c) 2012-2013 Germar Reitze
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

import sys
from PyKDE4.kdecore import ki18n, KAboutData, KCmdLineArgs
from PyKDE4.kdeui import KApplication, KPasswordDialog
from PyQt4.QtCore import QString, QTimer, SIGNAL

import app

def ask_password_dialog(parent, config, title, prompt, timeout = None):
    if parent is None:
        kapp, kaboutData = app.create_kapplication( config )

    dialog = KPasswordDialog()
    
    timer = QTimer()
    if not timeout is None:
        dialog.connect(timer, SIGNAL("timeout()"), dialog.close)
        timer.setInterval(timeout * 1000)
        timer.start()

    dialog.setPrompt( QString.fromUtf8(prompt))
    dialog.show()
    KApplication.processEvents()

    if parent is None:
        kapp.exec_()
    else:
        dialog.exec_()

    timer.stop()
    password = dialog.password()
    del(dialog)

    return(password)
