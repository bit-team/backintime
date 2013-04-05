#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan, Bart de Koning, Richard Bailey
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
import os
import time
import gettext

_=gettext.gettext

if len( os.getenv( 'DISPLAY', '' ) ) == 0:
    os.putenv( 'DISPLAY', ':0.0' )

sys.path = [os.path.join( os.path.dirname( os.path.abspath( os.path.dirname( __file__ ) ) ), 'common' )] + sys.path

import backintime
import config
import tools
import logger
import snapshots

from PyQt4.QtCore import QObject, QString, SIGNAL, QTimer
from PyKDE4.kdecore import KAboutData, KCmdLineArgs, ki18n
from PyKDE4.kdeui import KApplication, KSystemTrayIcon, KIcon


class KDE4SysTrayIcon:
    def __init__( self ):
        self.snapshots = snapshots.Snapshots()
        self.config = self.snapshots.config

        if len( sys.argv ) > 1:
            try:
                profile_id = int( sys.argv[1] )
                self.config.set_current_profile( profile_id )
            except:
                pass

        kaboutdata = KAboutData( 'backintime', '', ki18n( self.config.APP_NAME ), self.config.VERSION, ki18n( '' ), KAboutData.License_GPL_V2, ki18n( self.config.COPYRIGHT ), ki18n( '' ), 'http://backintime.le-web.org', 'bit-team@lists.launchpad.net' )
        kaboutdata.setProgramIconName( 'document-save' )

        KCmdLineArgs.init( [sys.argv[0]], kaboutdata )
        self.kapp = KApplication()

        self.status_icon = KSystemTrayIcon()
        self.status_icon.setIcon( KIcon('document-save') )
        #self.status_icon.actionCollection().clear()
        self.status_icon.setContextMenu( None )
        QObject.connect( self.status_icon, SIGNAL('activated(QSystemTrayIcon::ActivationReason)'), self.show_popup )

        self.first_error = self.config.is_notify_enabled()
        self.popup = None
        self.last_message = None

        self.timer = QTimer()
        QObject.connect( self.timer, SIGNAL('timeout()'), self.update_info )

        self.ppid = os.getppid()

    def prepare_exit( self ):
        self.timer.stop()

        if not self.status_icon is None:
            self.status_icon.hide()
            self.status_icon = None

        if not self.popup is None:
            self.popup.deleteLater()
            self.popup = None

        self.kapp.processEvents()

    def run( self ):
        self.status_icon.show()
        self.timer.start( 500 )

        logger.info( "[kde4systrayicon] begin loop" )

        self.kapp.exec_()
        
        logger.info( "[kde4systrayicon] end loop" )

        self.prepare_exit()

    def show_popup( self ):
        if not self.popup is None:
            self.popup.deleteLater()
            self.popup = None

        if not self.last_message is None:
            self.popup = KPassivePopup.message( self.config.APP_NAME, QString.fromUtf8( self.last_message[1] ), self.status_icon )
            self.popup.setAutoDelete( False )

    def update_info( self ):
        if not tools.is_process_alive( self.ppid ):
            self.prepare_exit()
            self.kapp.exit(0)
            return

        message = self.snapshots.get_take_snapshot_message()
        if message is None and self.last_message is None:
            message = ( 0, _('Working...') )
            
        if not message is None:
            if message != self.last_message:
                self.last_message = message
                self.status_icon.setToolTip( QString.fromUtf8( self.last_message[1] ) )

                if self.last_message[0] != 0:
                    self.status_icon.setIcon( KIcon('document-save-as') )
                    if self.first_error:
                        self.first_error = False
                        self.show_popup()
                else:
                    self.status_icon.setIcon( KIcon('document-save') )
            

if __name__ == '__main__':
    KDE4SysTrayIcon().run()

