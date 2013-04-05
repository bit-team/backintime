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
import sys
import copy
import pygtk
pygtk.require("2.0")
import gtk
import gobject
import datetime
import gettext

import config
import snapshots
import tools


_=gettext.gettext


class LogViewDialog(object):
    
    def __init__( self, parent, snapshot_id = None ):
        self.parent = parent
        self.config = parent.config
        self.snapshots = parent.snapshots
        self.profile_id = self.config.get_current_profile()
        self.snapshot_id = snapshot_id
        
        builder = gtk.Builder()
        self.builder = builder
        self.builder.set_translation_domain('backintime')
        
        glade_file = os.path.join(self.config.get_app_path(), 'gnome', 'logviewdialog.glade')
        
        builder.add_from_file(glade_file)
        
        get = builder.get_object
        
        self.dialog = get('LogViewDialog')
        self.dialog.set_transient_for( parent.window )

        signals = { 
                'on_combo_profiles_changed': self.on_combo_profiles_changed,
                'on_combo_filter_changed': self.on_combo_filter_changed,
                'on_cb_auto_scroll_toggled': self.scroll
            }
        
        builder.connect_signals(signals)

        self.cb_auto_scroll = get('cb_auto_scroll')
        self.cb_auto_scroll.hide()

        #log view
        self.txt_log_view = get( 'txt_log_view' )
        
        #profiles
        self.hbox_profiles = get( 'hbox_profiles' )

        self.store_profiles = gtk.ListStore( str, str )
        self.combo_profiles = get( 'combo_profiles' )
        
        text_renderer = gtk.CellRendererText()
        self.combo_profiles.pack_start( text_renderer, True )
        self.combo_profiles.add_attribute( text_renderer, 'text', 0 )
        
        self.combo_profiles.set_model( self.store_profiles )
    
        #filter
        self.store_filter = gtk.ListStore( str, int )
        self.combo_filter = get( 'combo_filter' )
        
        text_renderer = gtk.CellRendererText()
        self.combo_filter.pack_start( text_renderer, True )
        self.combo_filter.add_attribute( text_renderer, 'text', 0 )
        
        self.combo_filter.set_model( self.store_filter )
    
        self.store_filter.append( [ _('All'), 0 ] )
        select_iter = self.store_filter.append( [ _('Errors'), 1 ] )
        set_active = True
        if self.snapshot_id is None or self.snapshots.is_snapshot_failed( self.snapshot_id ):
            self.combo_filter.set_active_iter( select_iter )
            set_active = False
        select_iter = self.store_filter.append( [ _('Changes'), 2 ] )
        if not self.snapshot_id is None and set_active:
            self.combo_filter.set_active_iter( select_iter )
        self.store_filter.append( [ _('Informations'), 3 ] )
        
        #update title
        if not snapshot_id is None:
            self.hbox_profiles.hide()
            self.dialog.set_title( "%s (%s)" % ( self.dialog.get_title(), self.snapshots.get_snapshot_display_name( self.snapshot_id ) ) )
        
        self.update_profiles()
    
    def scroll(self, *args):
        pass
        
    def on_combo_profiles_changed( self, *params ):
        iter = self.combo_profiles.get_active_iter()
        if iter is None:
            return
        
        profile_id = self.store_profiles.get_value( iter, 1 )
        if profile_id != self.profile_id:
            self.profile_id = profile_id
        
        self.update_log_view()
    
    def on_combo_filter_changed( self, *params ):
        self.update_log_view()
    
    def update_profiles( self ):
        profiles = self.config.get_profiles_sorted_by_name()
        
        select_iter = None
        self.store_profiles.clear()

        counter = 0
        for profile_id in profiles:
            counter = counter + 1
            iter = self.store_profiles.append( [ self.config.get_profile_name( profile_id ), profile_id ] )
            if profile_id == self.profile_id:
                select_iter = iter
        
        if not select_iter is None:
            self.combo_profiles.set_active_iter( select_iter )

        if counter <= 1:
            self.hbox_profiles.hide()

        self.update_log_view()
    
    def update_log_view( self ):
        mode = 0
        iter = self.combo_filter.get_active_iter()
        if not iter is None:
            mode = self.store_filter.get_value( iter, 1 )

        if self.snapshot_id is None:
            self.txt_log_view.get_buffer().set_text( self.snapshots.get_take_snapshot_log( mode, self.profile_id ) )
        else:
            self.txt_log_view.get_buffer().set_text( self.snapshots.get_snapshot_log( self.snapshot_id, mode ) )
        
    def run( self ):
        self.dialog.run()
        self.dialog.destroy()


