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


import pygtk
pygtk.require("2.0")
import gtk
import gettext

import config


_=gettext.gettext


def show_question( parent, config, message ):
	dialog = gtk.MessageDialog( parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO )
	dialog.set_markup( message )
	dialog.set_title( config.APP_NAME )
	retVal = dialog.run()
	dialog.destroy()
	return retVal

def show_error( parent, config, message ):
	dialog = gtk.MessageDialog( parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_OK )
	dialog.set_markup( message )
	dialog.set_title( config.APP_NAME )
	retVal = dialog.run()
	dialog.destroy()
	return retVal

def text_input_dialog( parent, glade, title, default_value = "" ):
	dialog = glade.get_widget( 'TextInputDialog' )
	dialog.set_title( title )
	dialog.set_transient_for( parent )

	edit = glade.get_widget( 'edit_text' )
	edit.set_text( default_value )
	edit.grab_focus()
	
	text = None
	if gtk.RESPONSE_OK == dialog.run():
		text = edit.get_text()

	dialog.hide()
	return text  

