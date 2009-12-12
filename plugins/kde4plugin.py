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
import time
import gettext
import thread
import subprocess


_=gettext.gettext


if len( os.getenv( 'DISPLAY', '' ) ) == 0:
	os.putenv( 'DISPLAY', ':0.0' )


class KDE4Plugin( pluginmanager.Plugin ):
	def __init__( self ):
		self.process = None
		self.snapshots = None

	def init( self, snapshots ):
		self.snapshots = snapshots

		if not tools.process_exists( 'ksmserver' ):
			return False

		if not tools.check_x_server():
			return False

		if len( tools.read_command_output( "ksmserver --version | grep \"KDE: 4.\"" ) ) <= 0:
			return False

		return True
	
	def is_gui( self ):
		return True

	def update_info( self ):
		from PyQt4.QtCore import QObject, QString, SIGNAL, QEventLoop
		from PyKDE4.kdecore import KAboutData, KCmdLineArgs, ki18n
		from PyKDE4.kdeui import KApplication, KSystemTrayIcon, KIcon

		print "[KDE4Plugin UPDATE] %s" % thread.get_ident()

		if self.app is None:
			return

		self.app.processEvents( QEventLoop.AllEvents, 2000 )
	
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

		self.app.processEvents( QEventLoop.AllEvents, 2000 )

	def show_popup( self ):
		from PyKDE4.kdeui import KPassivePopup
		from PyQt4.QtCore import QString

		if not self.popup is None:
			self.popup.deleteLater()
			self.popup = None

		if not self.last_message is None:
			self.popup = KPassivePopup.message( self.config.APP_NAME, QString.fromUtf8( self.last_message[1] ), self.status_icon )
			self.popup.setAutoDelete( False )

	def on_process_begins( self ):
		try:
			self.process = subprocess.Popen( [ sys.executable, '/usr/share/backintime/kde4/kde4systrayicon.py', self.snapshots.config.get_current_profile() ] )
		except:
			pass

	def on_process_ends( self ):
		if not self.process is None:
			try:
				self.process.terminate()
			except:
				pass

	def on_error( self, code, message ):
		self.update_info()

	def on_new_snapshot( self, snapshot_id, snapshot_path ):
		self.update_info()

