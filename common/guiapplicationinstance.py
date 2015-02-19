#    Back In Time
#    Copyright (C) 2008-2015 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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

class GUIApplicationInstance:
    '''class used to handle one application instance mechanism
    '''
    #TODO: check if we could subclass ApplicationInstance
    def __init__( self, base_control_file, raise_cmd = '' ):
        '''specify the base for control files
        '''
        self.pid_file = base_control_file + '.pid'
        self.raise_file = base_control_file + '.raise'
        self.raise_cmd = raise_cmd

        #remove raise_file is already exists
        try:
            os.remove( self.raise_file )
        except:
            pass

        self.check( raise_cmd )
        self.start_application()

    def check( self, raise_cmd ):
        '''check if the current application is already running
        '''
        #check if the pidfile exists
        if not os.path.isfile( self.pid_file ):
            return

        #read the pid from the file
        pid = 0
        procname = ''
        try:
            with open( self.pid_file, 'rt' ) as f:
                data = f.read()
            data = data.split('\n', 1)
            pid = int(data[0])
            if len(data) > 1:
                procname = data[1].strip('\n')
        except:
            pass

        #check if the process with specified by pid exists
        if 0 == pid:
            return

        try:
            os.kill( pid, 0 )	#this will raise an exception if the pid is not valid
        except:
            return

        #check if the process has the same procname
        with open('/proc/%s/cmdline' % pid, 'r') as f:
            if procname and not procname == f.read().strip('\n'):
                return

        #exit the application
        print("The application is already running ! (pid: %s)" % pid)

        #notify raise
        try:
            with open( self.raise_file, 'wt' ) as f:
                f.write( raise_cmd )
        except:
            pass

        exit(0) #exit raise an exception so don't put it in a try/except block

    def start_application( self ):
        '''called when the single instance starts to save it's pid
        '''
        pid = str(os.getpid())
        procname = ''
        try:
            with open('/proc/%s/cmdline' % pid, 'r') as f:
                procname = f.read().strip('\n')
        except:
            pass
        with open( self.pid_file, 'wt' ) as f:
            f.write( pid + '\n' + procname )

    def exit_application( self ):
        '''called when the single instance exit ( remove pid file )
        '''
        try:
            os.remove( self.pid_file )
        except:
            pass

    def raise_command( self ):
        '''check if the application must to be raised
           return None if no raise needed, or a string command to raise
        '''
        ret_val = None

        try:
            if os.path.isfile( self.raise_file ):
                with open( self.raise_file, 'rt' ) as f:
                    ret_val = f.read()
                os.remove( self.raise_file )
        except:
            pass

        return ret_val
