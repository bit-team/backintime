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
import time
import fcntl

class ApplicationInstance:
    '''class used to handle one application instance mechanism
    '''

    def __init__( self, pid_file, auto_exit = True, flock = False ):
        '''specify the file used to save the application instance pid
        '''
        self.pid_file = pid_file
        self.flock_file = None
        if flock:
            self.flockExclusiv()

        if auto_exit:
            if self.check( True ):
                self.start_application()

    def __del__(self):
        '''unlock and clean up
        '''
        self.flockUnlock()

    def check( self, auto_exit = False ):
        '''check if the current application is already running, returns True if this is the application instance
        '''
        #check if the pidfile exists
        if not os.path.isfile( self.pid_file ):
            return True

        #read the pid from the file
        pid = 0
        procname = ''
        try:
            with open( self.pid_file, 'rt' ) as file:
                data = file.read()
            data = data.split('\n', 1)
            pid = int(data[0])
            if len(data) > 1:
                procname = data[1].strip('\n')
        except:
            pass

        #check if the process with specified by pid exists
        if 0 == pid:
            return True

        try:
            os.kill( pid, 0 )	#this will raise an exception if the pid is not valid
        except:
            return True

        #check if the process has the same procname
        with open('/proc/%s/cmdline' % pid, 'r') as file:
            if procname and not procname == file.read().strip('\n'):
                return True

        if auto_exit:
            #exit the application
            print("The application is already running !")
            exit(0) #exit raise an exception so don't put it in a try/except block

        return False

    def start_application( self ):
        '''called when the single instance starts to save it's pid
        '''
        pid = str(os.getpid())
        procname = ''
        try:
            with open('/proc/%s/cmdline' % pid, 'r') as file:
                procname = file.read().strip('\n')
        except:
            pass
        with open( self.pid_file, 'wt' ) as file:
            file.write( pid + '\n' + procname )

        self.flockUnlock()

    def exit_application( self ):
        '''called when the single instance exit ( remove pid file )
        '''
        try:
            os.remove( self.pid_file )
        except:
            pass

    def flockExclusiv(self):
        '''create an exclusive lock to block a second instance while
        the first instance is starting.
        '''
        self.flock_file = open(self.pid_file + '.flock', 'w')
        fcntl.flock(self.flock_file, fcntl.LOCK_EX)

    def flockUnlock(self):
        '''remove the exclusive lock. Second instance can now continue
        but should find it self to be obsolet.
        '''
        if self.flock_file:
            fcntl.fcntl(self.flock_file, fcntl.LOCK_UN)
            self.flock_file.close()
            if os.path.exists(self.flock_file.name):
                os.remove(self.flock_file.name)
        self.flock_file = None

if __name__ == '__main__':
    #create application instance
    app_instance = ApplicationInstance( '/tmp/myapp.pid' )

    #do something here
    print("Start MyApp")
    time.sleep(5)	#sleep 5 seconds
    print("End MyApp")

    #remove pid file
    app_instance.exit_application()
