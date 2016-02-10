#    Back In Time
#    Copyright (C) 2008-2016 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import fcntl
import errno

import logger
import tools

class ApplicationInstance:
    """
    Class used to handle one application instance mechanism.

    Args:
        pid_file (str):     full path of file used to save pid and procname
        auto_exit (bool):   automatically call sys.exit if there is an other
                            instance running
        flock (bool):       use file-locks to make sure only one instance
                            is checking at the same time
    """

    def __init__( self, pid_file, auto_exit = True, flock = False ):
        self.pid_file = pid_file
        self.pid = 0
        self.procname = ''
        self.flock_file = None
        if flock:
            self.flockExclusiv()

        if auto_exit:
            if self.check( True ):
                self.start_application()

    def __del__(self):
        self.flockUnlock()

    def check( self, auto_exit = False ):
        """
        Check if the current application is already running

        Args:
            auto_exit (bool):   automatically call sys.exit if there is an other
                                instance running

        Returns:
            bool:               ``True`` if this is the only application
                                instance
        """
        #check if the pidfile exists
        if not os.path.isfile( self.pid_file ):
            return True

        self.pid, self.procname = self.readPidFile()

        #check if the process with specified by pid exists
        if 0 == self.pid:
            return True

        if not tools.is_process_alive(self.pid):
            return True

        #check if the process has the same procname
        #check cmdline for backwards compatibility
        if self.procname and                                    \
           self.procname != tools.process_name(self.pid) and    \
           self.procname != tools.process_cmdline(self.pid):
                return True

        if auto_exit:
            #exit the application
            print("The application is already running !")
            exit(0) #exit raise an exception so don't put it in a try/except block

        return False

    def start_application( self ):
        """
        Called when the single instance starts to save it's pid
        """
        pid = os.getpid()
        procname = tools.process_name(pid)

        try:
            with open( self.pid_file, 'wt' ) as f:
                f.write('{}\n{}'.format(pid, procname))
        except OSError as e:
            logger.error('Failed to write PID file %s: [%s] %s' %(e.filename, e.errno, e.strerror))

        self.flockUnlock()

    def exit_application( self ):
        """
        Called when the single instance exit ( remove pid file )
        """
        try:
            os.remove( self.pid_file )
        except:
            pass

    def flockExclusiv(self):
        """
        Create an exclusive lock to block a second instance while
        the first instance is starting.
        """
        try:
            self.flock_file = open(self.pid_file + '.flock', 'w')
            fcntl.flock(self.flock_file, fcntl.LOCK_EX)
        except OSError as e:
            logger.error('Failed to write flock file %s: [%s] %s' %(e.filename, e.errno, e.strerror))

    def flockUnlock(self):
        """
        Remove the exclusive lock. Second instance can now continue
        but should find it self to be obsolet.
        """
        if self.flock_file:
            fcntl.fcntl(self.flock_file, fcntl.LOCK_UN)
            self.flock_file.close()
            try:
                os.remove(self.flock_file.name)
            except:
                #an other instance was faster
                #race condition while using 'if os.path.exists(...)'
                pass
        self.flock_file = None

    def readPidFile(self):
        """
        Read the pid and procname from the file

        Returns:
            tuple:  tuple of (pid(int), procname(str))
        """
        pid = 0
        procname = ''
        try:
            with open( self.pid_file, 'rt' ) as f:
                data = f.read()
            data = data.split('\n', 1)
            if data[0].isdigit():
                pid = int(data[0])
            if len(data) > 1:
                procname = data[1].strip('\n')
        except OSError as e:
            logger.warning('Failed to read PID and process name from %s: [%s] %s' %(e.filename, e.errno, e.strerror))
        except ValueError as e:
            logger.warning('Failed to extract PID and process name from %s: %s'
                            %(self.pid_file, str(e)))
        return (pid, procname)

if __name__ == '__main__':
    import time

    #create application instance
    app_instance = ApplicationInstance( '/tmp/myapp.pid' )

    #do something here
    print("Start MyApp")
    time.sleep(5)	#sleep 5 seconds
    print("End MyApp")

    #remove pid file
    app_instance.exit_application()
