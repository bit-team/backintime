#    Back In Time
#    Copyright (C) 2008-2009 Oprea Dan
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


import os
import os.path
import pluginmanager
import tools
import logger


class UserCallbackPlugin( pluginmanager.Plugin ):
	def __init__( self ):
		return

	def init( self, snapshots ):
		self.config = snapshots.config
		self.callback = self.config.get_take_snapshot_user_callback()
		if not os.path.exists( self.callback ):
			return False
		return True

	def notify_callback( self, args = '' ):
		logger.info( "[UserCallbackPlugin.notify_callback] %s" % args )
		os.system( "sh \"%s\" %s" % ( self.callback, args ) )

	def on_process_begins( self ):
		self.notify_callback( '1' )

	def on_process_ends( self ):
		self.notify_callback( '2' )

	def on_error( self, code, message ):
		if len( message ) <= 0:
			self.notify_callback( "4 %s" % code )
		else:
			self.notify_callback( "4 %s \"%s\"" % ( code, message ) )

	def on_new_snapshot( self, snapshot_id, snapshot_path ):
		self.notify_callback( "3 %s \"%s\"" % ( snapshot_id, snapshot_path ) )

