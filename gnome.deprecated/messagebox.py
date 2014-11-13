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


import os
import os.path

import pygtk
pygtk.require("2.0")
import gtk
import gettext
import gobject

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

def text_input_dialog( parent, config, title, default_value = '', prompt = None, hide_input = False , timeout = None):
    
    builder = gtk.Builder()
    builder.set_translation_domain('backintime')

    glade_file = os.path.join(config.get_app_path(), 'gnome',
            'textinputdialog.glade')

    builder.add_from_file(glade_file)

    dialog = builder.get_object( 'TextInputDialog' )
    dialog.set_title( title )
    if not parent is None:
        dialog.set_transient_for( parent )
        
    prompt_text = builder.get_object('prompt_text')
    if not prompt is None:
        prompt_text.set_text(prompt)
        prompt_text.set_visible(True)
    
    edit = builder.get_object( 'edit_text' )
    
    if hide_input:
        edit.set_visibility(False)

    if not default_value is None:
        edit.set_text( default_value )

    edit.grab_focus()
    
    if not timeout is None:
        gobject.timeout_add(1000 * timeout, dialog.destroy)
    
    text = None
    if gtk.RESPONSE_OK == dialog.run():
        text = edit.get_text()
    else:
        text = default_value

    dialog.destroy()
    return text  

def ask_password_dialog(parent, config, title, prompt, timeout = None):
    password = text_input_dialog(parent, config, title,
                    prompt = prompt,
                    hide_input = True, timeout = timeout)
    return(password)
