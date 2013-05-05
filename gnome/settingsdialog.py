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
import sys
import copy
import pygtk
pygtk.require("2.0")
import gtk
import gobject
import datetime
import gettext
import subprocess
import keyring

import config
import messagebox
import tools
import mount
import password

_=gettext.gettext


class SettingsDialog(object):
    
    def __init__( self, config, snapshots, parent ):
        
        self.config = config
        self.parent = parent
        self.snapshots = snapshots
        self.profile_id = self.config.get_current_profile()
        
        builder = gtk.Builder()
        self.builder = builder
        self.builder.set_translation_domain('backintime')
        
        glade_file = os.path.join(self.config.get_app_path(),
            'gnome', 'settingsdialog.glade')
        
        builder.add_from_file(glade_file)
        
        get = builder.get_object
        
        self.dialog = get('SettingsDialog')
        self.dialog.set_transient_for( parent.window )
        
        signals = { 
                'on_btn_add_profile_clicked' : self.on_add_profile,
                'on_btn_edit_profile_clicked' : self.on_edit_profile,
                'on_btn_remove_profile_clicked' : self.on_remove_profile,
                'on_btn_add_include_clicked' : self.on_add_include,
                'on_btn_add_include_file_clicked' : self.on_add_include_file,
                'on_btn_remove_include_clicked' : self.on_remove_include,
                'on_btn_add_exclude_clicked' : self.on_add_exclude,
                'on_btn_add_exclude_file_clicked' : self.on_add_exclude_file,
                'on_btn_add_exclude_folder_clicked' : self.on_add_exclude_folder,
                'on_btn_remove_exclude_clicked' : self.on_remove_exclude,
                'on_cb_remove_old_backup_toggled' : self.update_remove_old_backups,
                'on_cb_min_free_space_toggled' : self.update_min_free_space,
                #'on_cb_per_directory_schedule_toggled' : self.on_cb_per_directory_schedule_toggled,
                'on_combo_profiles_changed': self.on_combo_profiles_changed,
                'on_btn_where_clicked': self.on_btn_where_clicked,
                'on_cb_backup_mode_changed': self.on_cb_backup_mode_changed,
                'on_cb_auto_host_user_profile_toggled': self.update_host_user_profile,
                'on_combo_modes_changed': self.on_combo_modes_changed,
                'on_cb_password_save_toggled': self.update_password_save,
                'on_btn_ssh_private_key_file_clicked': self.on_btn_ssh_private_key_file_clicked,
                'on_cb_full_rsync_toggled': self.update_check_for_changes
            }
        
        builder.connect_signals(signals)
        
        #profiles
        self.btn_edit_profile = get( 'btn_edit_profile' )
        self.btn_add_profile = get( 'btn_add_profile' )
        self.btn_remove_profile = get( 'btn_remove_profile' )
        
        self.disable_combo_changed = True
        
        self.store_profiles = gtk.ListStore( str, str )
        
        self.combo_profiles = get( 'combo_profiles' )
        
        text_renderer = gtk.CellRendererText()
        self.combo_profiles.pack_start( text_renderer, True )
        self.combo_profiles.add_attribute( text_renderer, 'text', 0 )
        
        self.combo_profiles.set_model( self.store_profiles )
        
        self.disable_combo_changed = False
        
        #snapshots mode (local, ssh, ...)
        self.store_modes = gtk.ListStore(str, str)
        keys = self.config.SNAPSHOT_MODES.keys()
        keys.sort()
        for key in keys:
            self.store_modes.append([self.config.SNAPSHOT_MODES[key][1], key])
            
        self.combo_modes = get( 'combo_modes' )
        self.combo_modes.set_model( self.store_modes )
        
        self.combo_modes.clear()
        text_renderer = gtk.CellRendererText()
        self.combo_modes.pack_start( text_renderer, True )
        self.combo_modes.add_attribute( text_renderer, 'text', 0 )
        
        self.mode = None
        self.mode_local = get('mode_local')
        self.mode_ssh = get('mode_ssh')
##		self.mode_dummy = get('mode_dummy')
        
        #set current folder
        #self.fcb_where = get( 'fcb_where' )
        #self.fcb_where.set_show_hidden( self.parent.show_hidden_files )
        self.edit_where = get( 'edit_where' )
        
        self.cb_auto_host_user_profile = get('cb_auto_host_user_profile')
        self.lbl_host = get('lbl_host')
        self.txt_host = get('txt_host')
        self.lbl_user = get('lbl_user')
        self.txt_user = get('txt_user')
        self.lbl_profile = get('lbl_profile')
        self.txt_profile = get('txt_profile')
        
        #ssh
        self.txt_ssh_host = get('txt_ssh_host')
        self.txt_ssh_port = get('txt_ssh_port')
        self.txt_ssh_user = get('txt_ssh_user')
        self.txt_ssh_path = get('txt_ssh_path')
        self.txt_private_key_file = get('txt_ssh_private_key_file')
        
        self.store_ssh_cipher = gtk.ListStore(str, str)
        keys = self.config.SSH_CIPHERS.keys()
        keys.sort()
        for key in keys:
            self.store_ssh_cipher.append([self.config.SSH_CIPHERS[key], key])
        
        self.combo_ssh_cipher = get( 'combo_ssh_cipher' )
        self.combo_ssh_cipher.set_model( self.store_ssh_cipher )

        self.combo_ssh_cipher.clear()
        text_renderer = gtk.CellRendererText()
        self.combo_ssh_cipher.pack_start( text_renderer, True )
        self.combo_ssh_cipher.add_attribute( text_renderer, 'text', 0 )
        
##		#dummy
##		self.txt_dummy_host = get('txt_dummy_host')
##		self.txt_dummy_port = get('txt_dummy_port')
##		self.txt_dummy_user = get('txt_dummy_user')

        #password
        self.frame_password = get('password')
        self.txt_password = get('txt_password')
        self.txt_password.set_visibility(False)
        self.cb_password_save = get('cb_password_save')
        self.cb_password_use_cache = get('cb_password_use_cache')

        #automatic backup mode store
        self.store_backup_mode = gtk.ListStore( str, int )
        map = self.config.AUTOMATIC_BACKUP_MODES
        self.rev_automatic_backup_modes = {}
        keys = map.keys()
        keys.sort()
        for key in keys:
            self.rev_automatic_backup_modes[ map[key] ] = key
            self.store_backup_mode.append( [ map[key], key ] )

        #automatic backup time store
        self.store_backup_time = gtk.ListStore( str, int )
        for t in xrange( 0, 2400, 100 ):
            self.store_backup_time.append( [ datetime.time( t/100, t%100 ).strftime("%H:%M"), t ] )

        #automatic backup day store
        self.store_backup_day = gtk.ListStore( str, int )
        for t in xrange( 1, 29 ):
            self.store_backup_day.append( [ str(t), t ] )

        #automatic backup weekday store
        self.store_backup_weekday = gtk.ListStore( str, int )
        for t in xrange( 1, 8 ):
            self.store_backup_weekday.append( [ datetime.date(2011, 11, 6 + t).strftime("%A"), t ] )

        #custom backup time
        self.txt_backup_time_custom = get('txt_backup_time_custom')
        self.lbl_backup_time_custom = get('lbl_backup_time_custom')
        
        #per directory schedule
        #self.cb_per_directory_schedule = get( 'cb_per_directory_schedule' )
        #self.lbl_schedule = get( 'lbl_schedule' )
        
        #setup include folders
        self.list_include = get( 'list_include' )
        
        pix_renderer = gtk.CellRendererPixbuf()
        text_renderer = gtk.CellRendererText()
        
        column = gtk.TreeViewColumn( _('Include files and folders') )
        column.pack_start( pix_renderer, False )
        column.pack_end( text_renderer, True )
        column.add_attribute( pix_renderer, 'stock-id', 1 )
        column.add_attribute( text_renderer, 'markup', 0 )
        self.list_include.append_column( column )
        
        #column = gtk.TreeViewColumn( _('Schedule') )
        #combo_renderer = gtk.CellRendererCombo()
        #combo_renderer.set_property( 'editable', True )
        #combo_renderer.set_property( 'has-entry', False )
        #combo_renderer.set_property( 'model', self.store_backup_mode )
        #combo_renderer.set_property( 'text-column', 0 )
        #combo_renderer.connect( 'edited', self.on_automatic_backup_mode_changed )
        #column.pack_end( combo_renderer, True )
        #column.add_attribute( combo_renderer, 'text', 2 )
        
        #self.include_schedule_column = column
        
        self.store_include = gtk.ListStore( str, str, int ) #, str, int )
        self.list_include.set_model( self.store_include )
        
        #setup exclude patterns
        self.list_exclude = get( 'list_exclude' )
        
        pix_renderer = gtk.CellRendererPixbuf()
        text_renderer = gtk.CellRendererText()
        
        column = gtk.TreeViewColumn( _('Exclude patterns, files or folders') )
        column.pack_start( pix_renderer, False )
        column.pack_end( text_renderer, True )
        column.add_attribute( pix_renderer, 'stock-id', 1 )
        column.add_attribute( text_renderer, 'text', 0 )
        self.list_exclude.append_column( column )
        
        self.store_exclude = gtk.ListStore( str, str )
        self.list_exclude.set_model( self.store_exclude )

        exclude = ''
        i = 1
        prev_lines = 0
        for ex in self.config.DEFAULT_EXCLUDE:
            exclude += ex
            if i < len(self.config.DEFAULT_EXCLUDE):
                exclude += ', '
            if len(exclude)-prev_lines > 80:
                exclude += '\n'
                prev_lines += len(exclude)
        get( 'lbl_highly_recommended_excluded' ).set_text( exclude )

        #setup automatic backup mode
        self.cb_backup_mode = get( 'cb_backup_mode' )
        self.cb_backup_mode.set_model( self.store_backup_mode )
        
        self.cb_backup_mode.clear()
        renderer = gtk.CellRendererText()
        self.cb_backup_mode.pack_start( renderer, True )
        self.cb_backup_mode.add_attribute( renderer, 'text', 0 )
        
        #setup automatic backup time
        self.cb_backup_time = get( 'cb_backup_time' )
        self.cb_backup_time.set_model( self.store_backup_time )

        self.cb_backup_time.clear()
        renderer = gtk.CellRendererText()
        self.cb_backup_time.pack_start( renderer, True )
        self.cb_backup_time.add_attribute( renderer, 'text', 0 )
        
        self.lbl_backup_time = get( 'lbl_backup_time' )

        #setup automatic backup day
        self.cb_backup_day = get( 'cb_backup_day' )
        self.cb_backup_day.set_model( self.store_backup_day )

        self.cb_backup_day.clear()
        renderer = gtk.CellRendererText()
        self.cb_backup_day.pack_start( renderer, True )
        self.cb_backup_day.add_attribute( renderer, 'text', 0 )
        
        self.lbl_backup_day = get( 'lbl_backup_day' )

        #setup automatic backup weekday
        self.cb_backup_weekday = get( 'cb_backup_weekday' )
        self.cb_backup_weekday.set_model( self.store_backup_weekday )

        self.cb_backup_weekday.clear()
        renderer = gtk.CellRendererText()
        self.cb_backup_weekday.pack_start( renderer, True )
        self.cb_backup_weekday.add_attribute( renderer, 'text', 0 )
        
        self.lbl_backup_weekday = get( 'lbl_backup_weekday' )

        self.hbox_backup_time = get( 'hbox_backup_time' )
        
        #setup remove old backups older than
        self.edit_remove_old_backup_value = get( 'edit_remove_old_backup_value' )
        self.cb_remove_old_backup_unit = get( 'cb_remove_old_backup_unit' )
        
        self.store_remove_old_backup_unit = gtk.ListStore( str, int )
        self.cb_remove_old_backup_unit.set_model( self.store_remove_old_backup_unit )
        
        renderer = gtk.CellRendererText()
        self.cb_remove_old_backup_unit.pack_start( renderer, True )
        self.cb_remove_old_backup_unit.add_attribute( renderer, 'text', 0 )
        
        self.store_remove_old_backup_unit.clear()
        map = self.config.REMOVE_OLD_BACKUP_UNITS
        keys = map.keys()
        keys.sort()
        for key in keys:
            self.store_remove_old_backup_unit.append( [ map[ key ], key ] )
        
        self.cb_remove_old_backup = get( 'cb_remove_old_backup' )
        
        #setup min free space
        self.edit_min_free_space_value = get( 'edit_min_free_space_value' )
        self.cb_min_free_space_unit = get( 'cb_min_free_space_unit' )
        
        self.store_min_free_space_unit = gtk.ListStore( str, int )
        self.cb_min_free_space_unit.set_model( self.store_min_free_space_unit )
        
        renderer = gtk.CellRendererText()
        self.cb_min_free_space_unit.pack_start( renderer, True )
        self.cb_min_free_space_unit.add_attribute( renderer, 'text', 0 )
        
        self.store_min_free_space_unit.clear()
        map = self.config.MIN_FREE_SPACE_UNITS
        keys = map.keys()
        keys.sort()
        for key in keys:
            self.store_min_free_space_unit.append( [ map[ key ], key ] )
                
        self.cb_min_free_space = get( 'cb_min_free_space' )
        
        #don't remove named snapshots
        self.cb_dont_remove_named_snapshots = get( 'cb_dont_remove_named_snapshots' )
        
        #smart remove
        self.cb_smart_remove = get( 'cb_smart_remove' )
        self.edit_keep_all = get( 'edit_keep_all' )
        self.edit_keep_one_per_day = get( 'edit_keep_one_per_day' )
        self.edit_keep_one_per_week = get( 'edit_keep_one_per_week' )
        self.edit_keep_one_per_month= get( 'edit_keep_one_per_month' )
        
        #enable notifications
        self.cb_enable_notifications = get( 'cb_enable_notifications' )
        self.cb_backup_on_restore = get( 'cb_backup_on_restore' )
        self.cb_continue_on_errors = get( 'cb_continue_on_errors' )
        self.cb_use_checksum = get( 'cb_use_checksum' )
        self.cb_full_rsync = get( 'cb_full_rsync' )

        #log level
        self.store_log_level = gtk.ListStore( int, str )
        self.combo_log_level = get( 'combo_log_level' )

        text_renderer = gtk.CellRendererText()
        self.combo_log_level.pack_start( text_renderer, True )
        self.combo_log_level.add_attribute( text_renderer, 'text', 1 )
        
        self.combo_log_level.set_model( self.store_log_level )
        
        self.store_log_level.append( [ 0, _('None') ] )
        self.store_log_level.append( [ 1, _('Errors') ] )
        self.store_log_level.append( [ 2, _('Changes & Errors') ] )
        self.store_log_level.append( [ 3, _('All') ] )
        
        #nice & ionice
        self.cb_run_nice_from_cron = get('cb_run_nice_from_cron')
        self.cb_run_ionice_from_cron = get('cb_run_ionice_from_cron')
        self.cb_run_ionice_from_user = get('cb_run_ionice_from_user')
        
        self.cb_preserve_acl = get('cb_preserve_acl')
        self.cb_preserve_xattr = get('cb_preserve_xattr')
        self.cb_copy_unsafe_links = get('cb_copy_unsafe_links')
        self.cb_copy_links = get('cb_copy_links')
        
        #don't run when on battery
        self.cb_no_on_battery = get( 'cb_no_on_battery' )
        if not tools.power_status_available ():
            self.cb_no_on_battery.set_sensitive( False )
            self.cb_no_on_battery.set_tooltip_text( 'Power status not available from system' )

        #check for changes
        self.cb_check_for_changes = get('cb_check_for_changes')

        self.update_profiles()
    
    def error_handler( self, message ):
        messagebox.show_error( self.dialog, self.config, message )
    
    def question_handler( self, message ):
        return gtk.RESPONSE_YES == messagebox.show_question( self.dialog, self.config, message )
    
    #def on_automatic_backup_mode_changed( self, renderer, path, new_text ):
    #	iter = self.store_include.get_iter(path)
    #	self.store_include.set_value( iter, 2, new_text )
    #	self.store_include.set_value( iter, 3, self.rev_automatic_backup_modes[new_text] )
    
    def on_btn_where_clicked( self, button ):
        path = self.edit_where.get_text()
        
        fcd = gtk.FileChooserDialog( _('Snapshots folder'), self.dialog, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
        if len( path ) > 0:
            fcd.set_filename( path )
        
        if fcd.run() == gtk.RESPONSE_OK:
            new_path = tools.prepare_path( fcd.get_filename() )
            fcd.destroy()
            if len( path ) > 0 and new_path != path:
                if not self.question_handler( _('Are you sure you want to change snapshots folder ?') ):
                    return
            self.edit_where.set_text( new_path )
        else:
            fcd.destroy()

    def on_btn_ssh_private_key_file_clicked( self, button ): 
        file = self.txt_private_key_file.get_text()
        
        fcd = gtk.FileChooserDialog( _('SSH private key'), self.dialog, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
        if len( file ) > 0:
            fcd.set_filename( file )
        else:
            fcd.set_filename(self.config.get_ssh_private_key_folder())
        
        if fcd.run() == gtk.RESPONSE_OK:
            new_file = tools.prepare_path( fcd.get_filename() )
            fcd.destroy()
            self.txt_private_key_file.set_text( new_file )
        else:
            fcd.destroy()

    def on_cb_backup_mode_changed( self, *params ):
        iter = self.cb_backup_mode.get_active_iter()
        if iter is None:
            return

        backup_mode = self.store_backup_mode.get_value( iter, 1 )
        
        if backup_mode >= self.config.DAY:
            self.lbl_backup_time.show()
            self.cb_backup_time.show()
        else:
            self.lbl_backup_time.hide()
            self.cb_backup_time.hide()

        if backup_mode == self.config.WEEK:
            self.lbl_backup_weekday.show()
            self.cb_backup_weekday.show()
        else:
            self.lbl_backup_weekday.hide()
            self.cb_backup_weekday.hide()
        
        if backup_mode == self.config.MONTH:
            self.lbl_backup_day.show()
            self.cb_backup_day.show()
        else:
            self.lbl_backup_day.hide()
            self.cb_backup_day.hide()

        if backup_mode == self.config.CUSTOM_HOUR:
            self.lbl_backup_time_custom.show()
            self.txt_backup_time_custom.show()
            self.txt_backup_time_custom.set_sensitive( True )
            self.txt_backup_time_custom.set_text( self.config.get_custom_backup_time( self.profile_id ) )
        else:
            self.lbl_backup_time_custom.hide()
            self.txt_backup_time_custom.hide()

    def update_host_user_profile( self, *params ):
        value = not self.cb_auto_host_user_profile.get_active()
        self.lbl_host.set_sensitive( value )
        self.txt_host.set_sensitive( value )
        self.lbl_user.set_sensitive( value )
        self.txt_user.set_sensitive( value )
        self.lbl_profile.set_sensitive( value )
        self.txt_profile.set_sensitive( value )
        
    def update_password_save(self, *params):
        value = self.cb_password_save.get_active()
        if value and tools.check_home_encrypt():
            value = False
        self.cb_password_use_cache.set_sensitive(value)
        
    def update_check_for_changes(self, *params):
        value = not self.cb_full_rsync.get_active()
        self.cb_check_for_changes.set_sensitive(value)
        
    def on_combo_modes_changed(self, *params):
        iter = self.combo_modes.get_active_iter()
        if iter is None:
            return
            
        active_mode = self.store_modes.get_value( iter, 1 )
        if active_mode != self.mode:
            for mode in self.config.SNAPSHOT_MODES.keys():
                if active_mode == mode:
                    getattr(self, 'mode_%s' % mode).show()
                else:
                    getattr(self, 'mode_%s' % mode).hide()
            self.mode = active_mode
        if active_mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
            self.frame_password.show()
        else:
            self.frame_password.hide()

    def on_combo_profiles_changed( self, *params ):
        if self.disable_combo_changed:
            return
        
        iter = self.combo_profiles.get_active_iter()
        if iter is None:
            return
        
        profile_id = self.store_profiles.get_value( iter, 1 )
        if profile_id != self.profile_id:
            self.save_profile()
            self.profile_id = profile_id
        
        self.update_profile()
    
    def update_profiles( self ):
        self.disable_combo_changed = True
        
        profiles = self.config.get_profiles_sorted_by_name()
        
        select_iter = None
        self.store_profiles.clear()

        for profile_id in profiles:
            iter = self.store_profiles.append( [ self.config.get_profile_name( profile_id ), profile_id ] )
            if profile_id == self.profile_id:
                select_iter = iter
        
        self.disable_combo_changed = False
        
        if not select_iter is None:
            self.combo_profiles.set_active_iter( select_iter )
    
    def update_profile( self ):
        if self.profile_id == '1':
            self.btn_edit_profile.set_sensitive( False )
            self.btn_remove_profile.set_sensitive( False )
        else:
            self.btn_edit_profile.set_sensitive( True )
            self.btn_remove_profile.set_sensitive( True )
            
        #set mode
        i = 0
        iter = self.store_modes.get_iter_first()
        default_mode = self.config.get_snapshots_mode(self.profile_id)
        while not iter is None:
            if self.store_modes.get_value( iter, 1 ) == default_mode:
                self.combo_modes.set_active( i )
                break
            iter = self.store_modes.iter_next( iter )
            i = i + 1
        self.on_combo_modes_changed()
        
        #set current folder
        #self.fcb_where.set_filename( self.config.get_snapshots_path() )
        self.edit_where.set_text( self.config.get_snapshots_path( self.profile_id, mode = 'local' ) )
        self.cb_auto_host_user_profile.set_active( self.config.get_auto_host_user_profile( self.profile_id ) )
        host, user, profile = self.config.get_host_user_profile( self.profile_id )
        self.txt_host.set_text( host )
        self.txt_user.set_text( user )
        self.txt_profile.set_text( profile )
        self.update_host_user_profile()
        
        #ssh
        self.txt_ssh_host.set_text( self.config.get_ssh_host( self.profile_id ) )
        self.txt_ssh_port.set_text( str(self.config.get_ssh_port( self.profile_id )) )
        self.txt_ssh_user.set_text( self.config.get_ssh_user( self.profile_id ) )
        self.txt_ssh_path.set_text( self.config.get_snapshots_path_ssh( self.profile_id ) )
        self.txt_private_key_file.set_text( self.config.get_ssh_private_key_file( self.profile_id ) )
        #set chipher
        i = 0
        iter = self.store_ssh_cipher.get_iter_first()
        default_mode = self.config.get_ssh_cipher(self.profile_id)
        while not iter is None:
            if self.store_ssh_cipher.get_value( iter, 1 ) == default_mode:
                self.combo_ssh_cipher.set_active( i )
                break
            iter = self.store_ssh_cipher.iter_next( iter )
            i = i + 1
        
##		#dummy
##		self.txt_dummy_host.set_text( self.config.get_dummy_host( self.profile_id ) )
##		self.txt_dummy_port.set_text( str(self.config.get_dummy_port( self.profile_id )) )
##		self.txt_dummy_user.set_text( self.config.get_dummy_user( self.profile_id ) )
        
        #password
        password = self.config.get_password( profile_id = self.profile_id, mode = self.mode, only_from_keyring = True )
        if password is None:
            password = ''
        self.txt_password.set_text(password)
        self.cb_password_save.set_active( self.config.get_password_save( self.profile_id, self.mode ) )
        self.cb_password_use_cache.set_active( self.config.get_password_use_cache( self.profile_id, self.mode ) )
        self.update_password_save()
        
        #per directory schedule
        #self.cb_per_directory_schedule.set_active( self.config.get_per_directory_schedule() )
        
        #setup include folders
        #self.update_per_directory_option()
        
        self.store_include.clear()
        include_folders = self.config.get_include( self.profile_id )
        if len( include_folders ) > 0:
            for include_folder in include_folders:
                if include_folder[1] == 0:
                    self.store_include.append( [include_folder[0], gtk.STOCK_DIRECTORY, 0] ) #, self.config.AUTOMATIC_BACKUP_MODES[include_folder[1]], include_folder[1] ] )
                else:
                    self.store_include.append( [include_folder[0], gtk.STOCK_FILE, include_folder[1]] ) #, self.config.AUTOMATIC_BACKUP_MODES[include_folder[1]], include_folder[1] ] )
        
        #setup exclude patterns
        self.store_exclude.clear()
        exclude_patterns = self.config.get_exclude( self.profile_id )
        if len( exclude_patterns ) > 0:
            for exclude_pattern in exclude_patterns:
                self.store_exclude.append( [exclude_pattern, gtk.STOCK_DELETE] )
        
        #setup automatic backup mode
        i = 0
        iter = self.store_backup_mode.get_iter_first()
        default_mode = self.config.get_automatic_backup_mode( self.profile_id )
        while not iter is None:
            if self.store_backup_mode.get_value( iter, 1 ) == default_mode:
                self.cb_backup_mode.set_active( i )
                break
            iter = self.store_backup_mode.iter_next( iter )
            i = i + 1

        #setup automatic backup time
        i = 0
        iter = self.store_backup_time.get_iter_first()
        default_mode = self.config.get_automatic_backup_time( self.profile_id )
        while not iter is None:
            if self.store_backup_time.get_value( iter, 1 ) == default_mode:
                self.cb_backup_time.set_active( i )
                break
            iter = self.store_backup_time.iter_next( iter )
            i = i + 1
        
        #setup automatic backup day
        i = 0
        iter = self.store_backup_day.get_iter_first()
        default_mode = self.config.get_automatic_backup_day( self.profile_id )
        while not iter is None:
            if self.store_backup_day.get_value( iter, 1 ) == default_mode:
                self.cb_backup_day.set_active( i )
                break
            iter = self.store_backup_day.iter_next( iter )
            i = i + 1
        
        #setup automatic backup weekday
        i = 0
        iter = self.store_backup_weekday.get_iter_first()
        default_mode = self.config.get_automatic_backup_weekday( self.profile_id )
        while not iter is None:
            if self.store_backup_weekday.get_value( iter, 1 ) == default_mode:
                self.cb_backup_weekday.set_active( i )
                break
            iter = self.store_backup_weekday.iter_next( iter )
            i = i + 1
        
        self.on_cb_backup_mode_changed()

        #setup custom backup time
        self.txt_backup_time_custom.set_text( self.config.get_custom_backup_time( self.profile_id ) )

        #setup remove old backups older than
        enabled, value, unit = self.config.get_remove_old_snapshots( self.profile_id )
        
        self.edit_remove_old_backup_value.set_value( float( value ) )
        
        i = 0
        iter = self.store_remove_old_backup_unit.get_iter_first()
        while not iter is None:
            if self.store_remove_old_backup_unit.get_value( iter, 1 ) == unit:
                self.cb_remove_old_backup_unit.set_active( i )
                break
            iter = self.store_remove_old_backup_unit.iter_next( iter )
            i = i + 1
        
        self.cb_remove_old_backup.set_active( enabled )
        self.update_remove_old_backups( self.cb_remove_old_backup )
        
        #setup min free space
        enabled, value, unit = self.config.get_min_free_space( self.profile_id )
        
        self.edit_min_free_space_value.set_value( float(value) )
        
        i = 0
        iter = self.store_min_free_space_unit.get_iter_first()
        while not iter is None:
            if self.store_min_free_space_unit.get_value( iter, 1 ) == unit:
                self.cb_min_free_space_unit.set_active( i )
                break
            iter = self.store_min_free_space_unit.iter_next( iter )
            i = i + 1
        
        self.cb_min_free_space.set_active( enabled )
        self.update_min_free_space( self.cb_min_free_space )
        
        #don't remove named snapshots
        self.cb_dont_remove_named_snapshots.set_active( self.config.get_dont_remove_named_snapshots( self.profile_id ) )
        
        #smart remove
        smart_remove, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month = self.config.get_smart_remove( self.profile_id )

        self.cb_smart_remove.set_active( smart_remove )
        self.edit_keep_all.set_value( float(keep_all) )
        self.edit_keep_one_per_day.set_value( float(keep_one_per_day) )
        self.edit_keep_one_per_week.set_value( float(keep_one_per_week) )
        self.edit_keep_one_per_month.set_value( float(keep_one_per_month) )
        
        #enable notifications
        self.cb_enable_notifications.set_active( self.config.is_notify_enabled( self.profile_id ) )
        
        #backup on restore
        self.cb_backup_on_restore.set_active( self.config.is_backup_on_restore_enabled( self.profile_id ) )
    
        #continue on errors
        self.cb_continue_on_errors.set_active( self.config.continue_on_errors( self.profile_id ) )
        
        #use checksum
        self.cb_use_checksum.set_active( self.config.use_checksum( self.profile_id ) )
        
        #use checksum
        self.cb_full_rsync.set_active( self.config.full_rsync( self.profile_id ) )
        self.update_check_for_changes()
        
        #log level
        self.combo_log_level.set_active( self.config.log_level( self.profile_id ) )

        #run 'nice' from cron
        self.cb_run_nice_from_cron.set_active(self.config.is_run_nice_from_cron_enabled( self.profile_id ))

        #run 'ionice' from cron
        self.cb_run_ionice_from_cron.set_active(self.config.is_run_ionice_from_cron_enabled( self.profile_id ))
        
        #run 'ionice' from user
        self.cb_run_ionice_from_user.set_active(self.config.is_run_ionice_from_user_enabled( self.profile_id ))
        
        #don't run when on battery
        self.cb_no_on_battery.set_active( self.config.is_no_on_battery_enabled( self.profile_id ) )
    
        #ACL & xattr
        self.cb_preserve_acl.set_active(self.config.preserve_acl( self.profile_id ))
        self.cb_preserve_xattr.set_active(self.config.preserve_xattr( self.profile_id ))
        self.cb_copy_unsafe_links.set_active(self.config.copy_unsafe_links( self.profile_id ))
        self.cb_copy_links.set_active(self.config.copy_links( self.profile_id ))
        
        #check for changes
        self.cb_check_for_changes.set_active( self.config.check_for_changes( self.profile_id ) )
    
    def save_profile( self ):
        #profile_id = self.config.get_current_profile()
        #snapshots path
        iter = self.combo_modes.get_active_iter()
        mode = self.store_modes.get_value( iter, 1 )
        if self.config.SNAPSHOT_MODES[mode][0] is None:
            snapshots_path = self.edit_where.get_text()
        else:
            snapshots_path = self.config.get_snapshots_path(self.profile_id, mode = mode, tmp_mount = True)
        
        #hack
        if snapshots_path.startswith( '//' ):
            snapshots_path = snapshots_path[ 1 : ]
        
        #include list 
        include_list = []
        iter = self.store_include.get_iter_first()
        while not iter is None:
            #include_list.append( ( self.store_include.get_value( iter, 0 ), self.store_include.get_value( iter, 3 ) ) )
            value = self.store_include.get_value( iter, 0 )
            type = self.store_include.get_value( iter, 2 )
            include_list.append( ( value, type ) )
            iter = self.store_include.iter_next( iter )
        
        #exclude patterns
        exclude_list = []
        iter = self.store_exclude.get_iter_first()
        while not iter is None:
            exclude_list.append( self.store_exclude.get_value( iter, 0 ) )
            iter = self.store_exclude.iter_next( iter )
            
        if self.store_backup_mode.get_value( self.cb_backup_mode.get_active_iter(), 1 ) == self.config.CUSTOM_HOUR:
            if not tools.check_cron_pattern(self.txt_backup_time_custom.get_text()):
                self.error_handler( _('Custom Hours can only be a comma seperate list of hours (e.g. 8,12,18,23) or */3 for periodic backups every 3 hours') )
                return False

        #password
        password = self.txt_password.get_text()

        mount_kwargs = {}
        
        #ssh settings
        ssh_host = self.txt_ssh_host.get_text()
        ssh_port = self.txt_ssh_port.get_text()
        ssh_user = self.txt_ssh_user.get_text()
        ssh_path = self.txt_ssh_path.get_text()
        ssh_private_key_file = self.txt_private_key_file.get_text()
        iter = self.combo_ssh_cipher.get_active_iter()
        ssh_cipher = self.store_ssh_cipher.get_value( iter, 1 )
        if mode == 'ssh':
            mount_kwargs = {'host': ssh_host,
                            'port': int(ssh_port),
                            'user': ssh_user,
                            'path': ssh_path,
                            'cipher': ssh_cipher,
                            'private_key_file': ssh_private_key_file,
                            'password': password
                            }
        
##		#dummy settings
##		dummy_host = self.txt_dummy_host.get_text()
##		dummy_port = self.txt_dummy_port.get_text()
##		dummy_user = self.txt_dummy_user.get_text()
##		if mode == 'dummy':
##			#values must have exactly the same Type (str, int or bool) 
##			#as they are set in config or you will run into false-positive
##			#HashCollision warnings
##			mount_kwargs = {'host': dummy_host,
##							'port': int(dummy_port),
##							'user': dummy_user,
##							'password': password
##							}
            
        if not self.config.SNAPSHOT_MODES[mode][0] is None:
            #pre_mount_check
            mnt = mount.Mount(cfg = self.config, profile_id = self.profile_id, tmp_mount = True)
            try:
                mnt.pre_mount_check(mode = mode, first_run = True, **mount_kwargs)
            except mount.MountException as ex:
                self.error_handler(str(ex))
                return False

            #okay, lets try to mount
            try:
                hash_id = mnt.mount(mode = mode, check = False, **mount_kwargs)
            except mount.MountException as ex:
                self.error_handler(str(ex))
                return False
        
        #check if back folder changed
        #if len( self.config.get_snapshots_path() ) > 0 and self.config.get_snapshots_path() != snapshots_path:
        #   if gtk.RESPONSE_YES != messagebox.show_question( self.dialog, self.config, _('Are you sure you want to change snapshots folder ?') ):
        #	   return False 
        
        #ok let's save to config
        self.config.set_auto_host_user_profile( self.cb_auto_host_user_profile.get_active(), self.profile_id )
        self.config.set_host_user_profile( self.txt_host.get_text(), self.txt_user.get_text(), self.txt_profile.get_text(), self.profile_id )
        self.config.set_snapshots_path( snapshots_path, self.profile_id , mode)
        
        self.config.set_snapshots_mode(mode, self.profile_id)
        
        #save ssh
        self.config.set_ssh_host(ssh_host, self.profile_id)
        self.config.set_ssh_port(ssh_port, self.profile_id)
        self.config.set_ssh_user(ssh_user, self.profile_id)
        self.config.set_snapshots_path_ssh(ssh_path, self.profile_id)
        self.config.set_ssh_cipher(ssh_cipher, self.profile_id)
        self.config.set_ssh_private_key_file(ssh_private_key_file, self.profile_id)

##		#save dummy
##		self.config.set_dummy_host(dummy_host, self.profile_id)
##		self.config.set_dummy_port(dummy_port, self.profile_id)
##		self.config.set_dummy_user(dummy_user, self.profile_id)

        #save password
        if self.cb_password_save.get_active() and mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
            if self.config.get_keyring_backend() == '':
                self.config.set_keyring_backend('gnomekeyring')
            if self.config.get_keyring_backend() == 'kwallet':
                if keyring.backend.KDEKWallet().supported() == 1:
                    keyring.set_keyring(keyring.backend.KDEKWallet())
                else:
                    self.config.set_keyring_backend('gnomekeyring')
            if self.config.get_keyring_backend() == 'gnomekeyring':
                if keyring.backend.GnomeKeyring().supported() == 1:
                    keyring.set_keyring(keyring.backend.GnomeKeyring())
                else:
                    self.error_handler( _('Can\'t connect to gnomekeyring to save password'))
                    return False
        self.config.set_password_save(self.cb_password_save.get_active(), self.profile_id, mode)
        self.config.set_password_use_cache(self.cb_password_use_cache.get_active(), self.profile_id, mode)
        self.config.set_password(password, self.profile_id, mode)

        #if not msg is None:
        #   messagebox.show_error( self.dialog, self.config, msg )
        #   return False

        self.config.set_include( include_list, self.profile_id )
        self.config.set_exclude( exclude_list, self.profile_id )
        
        #global schedule
        self.config.set_automatic_backup_mode( self.store_backup_mode.get_value( self.cb_backup_mode.get_active_iter(), 1 ), self.profile_id )
        self.config.set_automatic_backup_time( self.store_backup_time.get_value( self.cb_backup_time.get_active_iter(), 1 ), self.profile_id )
        self.config.set_automatic_backup_day( self.store_backup_day.get_value( self.cb_backup_day.get_active_iter(), 1 ), self.profile_id )
        self.config.set_automatic_backup_weekday( self.store_backup_weekday.get_value( self.cb_backup_weekday.get_active_iter(), 1 ), self.profile_id )
        self.config.set_custom_backup_time( self.txt_backup_time_custom.get_text(), self.profile_id )
        
        #auto-remove snapshots
        self.config.set_remove_old_snapshots( 
                        self.cb_remove_old_backup.get_active(), 
                        int( self.edit_remove_old_backup_value.get_value() ),
                        self.store_remove_old_backup_unit.get_value( self.cb_remove_old_backup_unit.get_active_iter(), 1 ),
                        self.profile_id )
        self.config.set_min_free_space( 
                        self.cb_min_free_space.get_active(), 
                        int( self.edit_min_free_space_value.get_value() ),
                        self.store_min_free_space_unit.get_value( self.cb_min_free_space_unit.get_active_iter(), 1 ),
                        self.profile_id )
        self.config.set_dont_remove_named_snapshots( self.cb_dont_remove_named_snapshots.get_active(), self.profile_id )
        self.config.set_smart_remove(
                        self.cb_smart_remove.get_active(), 
                        int( self.edit_keep_all.get_value() ),
                        int( self.edit_keep_one_per_day.get_value() ),
                        int( self.edit_keep_one_per_week.get_value() ),
                        int( self.edit_keep_one_per_month.get_value() ),
                        self.profile_id )
        
        #options
        self.config.set_notify_enabled( self.cb_enable_notifications.get_active(), self.profile_id )
        self.config.set_backup_on_restore( self.cb_backup_on_restore.get_active(), self.profile_id )
        self.config.set_continue_on_errors( self.cb_continue_on_errors.get_active(), self.profile_id )
        self.config.set_use_checksum( self.cb_use_checksum.get_active(), self.profile_id )
        self.config.set_full_rsync( self.cb_full_rsync.get_active(), self.profile_id )
        self.config.set_check_for_changes( self.cb_check_for_changes.get_active(), self.profile_id )
        self.config.set_log_level( self.store_log_level.get_value( self.combo_log_level.get_active_iter(), 0 ), self.profile_id )
        
        #expert options
        #self.config.set_per_directory_schedule( self.cb_per_directory_schedule.get_active() )
        self.config.set_run_nice_from_cron_enabled( self.cb_run_nice_from_cron.get_active(), self.profile_id )
        self.config.set_run_ionice_from_cron_enabled( self.cb_run_ionice_from_cron.get_active(), self.profile_id )
        self.config.set_run_ionice_from_user_enabled( self.cb_run_ionice_from_user.get_active(), self.profile_id )
        self.config.set_no_on_battery_enabled( self.cb_no_on_battery.get_active(), self.profile_id )

        self.config.set_preserve_acl( self.cb_preserve_acl.get_active(), self.profile_id )
        self.config.set_preserve_xattr( self.cb_preserve_xattr.get_active(), self.profile_id )
        self.config.set_copy_unsafe_links( self.cb_copy_unsafe_links.get_active(), self.profile_id )
        self.config.set_copy_links( self.cb_copy_links.get_active(), self.profile_id )
        
        #umount
        if not self.config.SNAPSHOT_MODES[mode][0] is None:
            try:
                mnt.umount(hash_id = hash_id)
            except mount.MountException as ex:
                self.error_handler(str(ex))
                return False
        return True
    
    def update_remove_old_backups( self, button ):
        enabled = self.cb_remove_old_backup.get_active()
        self.edit_remove_old_backup_value.set_sensitive( enabled )
        self.cb_remove_old_backup_unit.set_sensitive( enabled )
    
    def update_min_free_space( self, button ):
        enabled = self.cb_min_free_space.get_active()
        self.edit_min_free_space_value.set_sensitive( enabled )
        self.cb_min_free_space_unit.set_sensitive( enabled )
    
    #def on_cb_per_directory_schedule_toggled( self, button ):
    #	self.update_per_directory_option()
    
    #def update_per_directory_option( self ):
    #	if self.cb_per_directory_schedule.get_active():
    #		if self.list_include.get_column(1) == None:
    #			self.list_include.append_column( self.include_schedule_column )
    #		self.cb_backup_mode.hide()
    #		self.lbl_schedule.hide()
    #	else:
    #		if self.list_include.get_column(1) != None:
    #			self.list_include.remove_column( self.include_schedule_column )
    #		self.lbl_schedule.show()
    #		self.cb_backup_mode.show()
    
    def run( self ):
        self.config.set_question_handler( self.question_handler )
        self.config.set_error_handler( self.error_handler )
        
        self.config_copy_dict = copy.copy( self.config.dict )
        
        while True:
            if gtk.RESPONSE_OK == self.dialog.run():
                if not self.validate():
                    continue
            else:
                self.config.dict = self.config_copy_dict
            break
        
        self.config.clear_handlers()
        self.dialog.destroy()
        
    def update_snapshots_location( self ):
        '''Update snapshot location dialog'''
        self.config.set_question_handler( self.question_handler )
        self.config.set_error_handler( self.error_handler )
        self.snapshots.update_snapshots_location()

    def on_add_profile(self, button, data=None):
        
        name = messagebox.text_input_dialog( self.dialog, self.config, _('New profile'), None )
        if name is None:
            return
        if len( name ) <= 0:
            return
    
        profile_id = self.config.add_profile( name )
        if profile_id is None:
            return
    
        self.profile_id = profile_id
        self.update_profiles()
    
    def on_edit_profile( self, button ):
        name = messagebox.text_input_dialog( self.dialog, self.config, _('Rename profile'), None )
        if name is None:
            return
        if len( name ) <= 0:
            return
        
        if not self.config.set_profile_name( name, self.profile_id ):
            return
        
        self.update_profiles()
    
    def on_remove_profile( self, button ):
        if gtk.RESPONSE_YES == messagebox.show_question( self.dialog, self.config, _('Are you sure you want to delete the profile "%s" ?') % self.config.get_profile_name(self.profile_id) ):
            self.config.remove_profile( self.profile_id )
            self.profile_id = '1'
            self.update_profiles()
    
    def on_add_include( self, button ):
        fcd = gtk.FileChooserDialog( _('Include folder'), self.dialog, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
        fcd.set_show_hidden( self.parent.show_hidden_files  )
        
        if fcd.run() == gtk.RESPONSE_OK:
            include_folder = tools.prepare_path( fcd.get_filename() )
            
            iter = self.store_include.get_iter_first()
            while not iter is None:
                if self.store_include.get_value( iter, 0 ) == include_folder:
                    break
                iter = self.store_include.iter_next( iter )
            
            if iter is None:
                #self.store_include.append( [include_folder, gtk.STOCK_DIRECTORY, self.config.AUTOMATIC_BACKUP_MODES[self.config.NONE], self.config.NONE ] )
                self.store_include.append( [ include_folder, gtk.STOCK_DIRECTORY, 0 ] )
        
        fcd.destroy()
    
    def on_add_include_file( self, button ):
        fcd = gtk.FileChooserDialog( _('Include file'), self.dialog, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
        fcd.set_show_hidden( self.parent.show_hidden_files  )
        
        if fcd.run() == gtk.RESPONSE_OK:
            include_file = tools.prepare_path( fcd.get_filename() )
            
            iter = self.store_include.get_iter_first()
            while not iter is None:
                if self.store_include.get_value( iter, 0 ) == include_file:
                    break
                iter = self.store_include.iter_next( iter )
            
            if iter is None:
                #self.store_include.append( [include_folder, gtk.STOCK_DIRECTORY, self.config.AUTOMATIC_BACKUP_MODES[self.config.NONE], self.config.NONE ] )
                self.store_include.append( [ include_file, gtk.STOCK_FILE, 1 ] )
        
        fcd.destroy()
    
    def on_remove_include( self, button ):
        store, iter = self.list_include.get_selection().get_selected()
        if not iter is None:
            store.remove( iter )
    
    def add_exclude_( self, pattern ):
        pattern = pattern.strip()
        if len( pattern ) == 0:
            return
        
        iter = self.store_exclude.get_iter_first()
        while not iter is None:
            if self.store_exclude.get_value( iter, 0 ) == pattern:
                return
            iter = self.store_exclude.iter_next( iter )
        
        self.store_exclude.append( [pattern, gtk.STOCK_DELETE] )
    
    def on_add_exclude( self, button ):
        pattern = messagebox.text_input_dialog( self.dialog, self.config, _('Exclude pattern') )
        if pattern is None:
            return
        
        if pattern.find( ':' ) >= 0:
            messagebox.show_error( self.dialog, self.config, _('Exclude patterns can\'t contain \':\' char !') )
            return

        self.add_exclude_( pattern )
    
    def on_add_exclude_file( self, button ):
        fcd = gtk.FileChooserDialog( _('Exclude file'), self.dialog, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
        fcd.set_show_hidden( self.parent.show_hidden_files  )
        
        if fcd.run() == gtk.RESPONSE_OK:
            pattern = tools.prepare_path( fcd.get_filename() )
            self.add_exclude_( pattern )
        
        fcd.destroy()
    
    def on_add_exclude_folder( self, button ):
        fcd = gtk.FileChooserDialog( _('Exclude folder'), self.dialog, gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK) )
        fcd.set_show_hidden( self.parent.show_hidden_files  )
        
        if fcd.run() == gtk.RESPONSE_OK:
            pattern = tools.prepare_path( fcd.get_filename() )
            self.add_exclude_( pattern )
        
        fcd.destroy()
    
    def on_remove_exclude( self, button ):
        store, iter = self.list_exclude.get_selection().get_selected()
        if not iter is None:
            store.remove( iter )
    
    def on_cancel( self, button ):
        self.dialog.destroy()
    
    def validate( self ):
        if not self.save_profile():
            return False
        
        if not self.config.check_config():
            return False
        
        if not self.config.setup_cron():
            return False
        
        self.config.save()

        #start Password_Cache if not running
        daemon = password.Password_Cache(self.config)
        if not daemon.status():
            try:
                subprocess.check_call(['backintime', '--pw-cache', 'start'], stdout=open(os.devnull, 'w'))
            except subprocess.CalledProcessError:
                messagebox.show_error(self.dialog, self.config, _('start Password Cache failed') )
        return True
    
