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


import gtk
import glib


def get_snapshot_display_markup( snapshots, snapshot_id ):
	display_name = snapshots.get_snapshot_display_id( snapshot_id )
	name = snapshots.get_snapshot_name( snapshot_id )
	if len( name ) > 0:
		display_name = display_name + ' - <b>' + glib.markup_escape_text( name ) + '</b>'
	return display_name


def run_gtk_update_loop():
	gtk.gdk.window_process_all_updates()
		
	while gtk.events_pending():
		gtk.main_iteration( False )

