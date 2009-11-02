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
import pluginmanager
import tools
import logger
import threading
import time
import gettext

_=gettext.gettext


if len( os.getenv( 'DISPLAY', '' ) ) == 0:
	os.putenv( 'DISPLAY', ':0.0' )


class KDE4Plugin( pluginmanager.Plugin ):

	class Systray( threading.Thread ):
		def __init__( self, snapshots ):
			threading.Thread.__init__( self )
			self.stop_flag = False
			self.snapshots = snapshots
			self.config = snapshots.config

		def start( self ):
			self.stop_flag = False
			threading.Thread.start( self )

		def stop( self ):
			self.stop_flag = True
			try:
				self.join()
			except:
				pass

		def show_popup( self ):
			from PyKDE4.kdeui import KPassivePopup
			from PyQt4.QtCore import QString

			if not self.popup is None:
				self.popup.deleteLater()
				self.popup = None

			if not self.last_message is None:
				self.popup = KPassivePopup.message( self.config.APP_NAME, QString.fromUtf8( self.last_message[1] ), self.status_icon )
				self.popup.setAutoDelete( False )

		def run(self):
			logger.info( '[KDE4Plugin.Systray.run]' )

			from PyQt4.QtCore import QObject, QString, SIGNAL
			from PyKDE4.kdecore import KAboutData, KCmdLineArgs, ki18n
			from PyKDE4.kdeui import KApplication, KSystemTrayIcon, KIcon

			kaboutdata = KAboutData( 'backintime', '', ki18n( self.config.APP_NAME ), self.config.VERSION, ki18n( '' ), KAboutData.License_GPL_V2, ki18n( self.config.COPYRIGHT ), ki18n( '' ), 'http://backintime.le-web.org', 'bit-team@lists.launchpad.net' )
			kaboutdata.setProgramIconName( 'document-save' )

			KCmdLineArgs.init( [sys.argv[0]], kaboutdata )
			kapp = KApplication()

			logger.info( '[KDE4Plugin.Systray.run] begin loop' )

			self.last_message = None

			self.status_icon = KSystemTrayIcon()
			self.status_icon.setIcon( KIcon('document-save') )
			#self.status_icon.actionCollection().clear()
			self.status_icon.setContextMenu( None )
			self.status_icon.show()
			self.popup = None
			QObject.connect( self.status_icon, SIGNAL('activated(QSystemTrayIcon::ActivationReason)'), self.show_popup )
			first_error = self.config.is_notify_enabled()

			while True:
				kapp.processEvents()
			
				if self.stop_flag:
					break

				if not kapp.hasPendingEvents():
					message = self.snapshots.get_take_snapshot_message()
					if message is None and self.last_message is None:
						message = ( 0, _('Working...') )

					if not message is None:
						if message != self.last_message:
							self.last_message = message
							self.status_icon.setToolTip( QString.fromUtf8( self.last_message[1] ) )

							if self.last_message[0] != 0:
								self.status_icon.setIcon( KIcon('document-save-as') )
								if first_error:
									first_error = False
									self.show_popup()
							else:
								self.status_icon.setIcon( KIcon('document-save') )

					time.sleep( 0.2 )
			
			self.status_icon.hide()
			self.status_icon.deleteLater()
			if not self.popup is None:
				self.popup.deleteLater()
				self.popup = None
			time.sleep( 0.2 )
			kapp.processEvents()
			kapp = None
			
			logger.info( '[KDE4Plugin.Systray.run] end loop' )


	def __init__( self ):
		return

	def init( self, snapshots ):
		if not tools.process_exists( 'ksmserver' ):
			return False

		if not tools.check_x_server():
			return False

		if len( tools.read_command_output( "ksmserver --version | grep \"KDE: 4.\"" ) ) <= 0:
			return False

		self.systray = None
		try:
			self.systray = KDE4Plugin.Systray( snapshots )
		except:
			self.systray = None

		return True
	
	def is_gui( self ):
		return True

	def on_process_begins( self ):
		if not self.systray is None:
			self.systray.start()

	def on_process_ends( self ):
		if not self.systray is None:
			self.systray.stop()

	def on_error( self, code, message ):
		return

	def on_new_snapshot( self, snapshot_id, snapshot_path ):
		return


