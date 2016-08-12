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

class ApplicationInstance:
    '''class used to handle one application instance mechanism

    pid_file:   full path of file used to save pid and procname
    auto_exit:  automatically call sys.exit if there is an other
                instance running
    flock:      use file-locks to make sure only one instance
                is checking at the same time

    tests:
    test/test_applicationinstance.TestApplicationInstance.test_create_and_remove_pid_file
    test/test_applicationinstance.TestApplicationInstance.test_write_pid_file
    test/test_applicationinstance.TestApplicationInstance.test_existing_process_with_correct_procname
    test/test_applicationinstance.TestApplicationInstance.test_existing_process_with_wrong_procname
    test/test_applicationinstance.TestApplicationInstance.test_existing_process_with_wrong_pid
    test/test_applicationinstance.TestApplicationInstance.test_killing_existing_process
    test/test_applicationinstance.TestApplicationInstance.test_non_existing_process
    test/test_applicationinstance.TestApplicationInstance.test_leftover_empty_lockfile
    '''

    def __init__( self, pid_file, auto_exit = True, flock = False ):
        '''specify the file used to save the application instance pid
        '''
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
        '''unlock and clean up
        '''
        self.flockUnlock()

    def check( self, auto_exit = False ):
        '''check if the current application is already running
        returns True if this is the only application instance

        auto_exit:  automatically call sys.exit if there is an other
                    instance running
        '''
        #check if the pidfile exists
        if not os.path.isfile( self.pid_file ):
            logger.debug('No PID file', self)
            return True

        self.pid, self.procname = self.readPidFile()

        #check if the process with specified by pid exists
        if 0 == self.pid:
            logger.debug('PID is 0', self)
            return True

        try:
            os.kill( self.pid, 0 )	#this will raise an exception if the pid is not valid
        except OSError as err:
            if err.errno == errno.ESRCH:
                #no such process
                logger.debug('No process with PID {}'.format(self.pid), self)
                return True
            else:
                raise

        #check if the process has the same procname
        if self.procname and self.procname != self.readProcName(self.pid):
            logger.debug("Process name doesn't match {} | {}".format(self.procname, self.readProcName(self.pid)), self)
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
        procname = self.readProcName(pid)

        try:
            with open( self.pid_file, 'wt' ) as f:
                f.write( pid + '\n' + procname )
        except OSError as e:
            logger.error('Failed to write PID file %s: [%s] %s' %(e.filename, e.errno, e.strerror))

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

        tests:
        test/test_applicationinstance.TestApplicationInstance.test_thread_write_without_flock
        test/test_applicationinstance.TestApplicationInstance.test_flock_exclusive
        '''
        try:
            self.flock_file = open(self.pid_file + '.flock', 'w')
            fcntl.flock(self.flock_file, fcntl.LOCK_EX)
        except OSError as e:
            logger.error('Failed to write flock file %s: [%s] %s' %(e.filename, e.errno, e.strerror))

    def flockUnlock(self):
        '''remove the exclusive lock. Second instance can now continue
        but should find it self to be obsolet.
        '''
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

    def readProcName(self, pid):
        try:
            with open('/proc/%s/cmdline' % pid, 'r') as f:
                return f.read().strip('\n')
        except OSError as e:
            logger.warning('Failed to read process name from %s: [%s] %s' %(e.filename, e.errno, e.strerror))
            return ''

    def readPidFile(self):
        '''read the pid and procname from the file

        pid: Process Indicator (int)
        '''
        pid = 0
        procname = ''
        try:
            with open( self.pid_file, 'rt' ) as f:
                data = f.read()
            data = data.split('\n', 1)
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
