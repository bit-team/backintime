#    Copyright (c) 2012 Germar Reitze
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

import sys, os, time, atexit, signal, tempfile

import config
import tools

class Timeout(Exception):
    pass
    
class Daemon:
    """
    A generic daemon class.
   
    Usage: subclass the Daemon class and override the run() method
    Original by Sander Marechal from:
    http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        
    def __del__(self):
        if os.path.exists(self.pidfile):
            os.remove(self.pidfile)
   
    def daemonize(self):
        """
        do the UNIX double-fork magic, see Stevens' "Advanced
        Programming in the UNIX Environment" for details (ISBN 0201563177)
        http://www.erlenstar.demon.co.uk/unix/faq_2.html#SEC16
        """
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                self.log.write('daemonize exit0 first parent')
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent
                self.log.write('daemonize exit0 second parent')
                sys.exit(0)
        except OSError, e:
            sys.stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            sys.exit(1)

        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = file(self.stdin, 'r')
        so = file(self.stdout, 'a+')
        se = file(self.stderr, 'a+', 0)
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # write pidfile
        atexit.register(self.delpid)
        signal.signal(signal.SIGTERM, self.cleanup_handler)
        pid = str(os.getpid())
        with open(self.pidfile, 'w+') as pidfile:
            pidfile.write("%s\n" % pid)
        os.chmod(self.pidfile, 0600)

    def cleanup_handler(self, signum, frame):
        self.delpid()
        sys.exit(0)
        
    def delpid(self):
        try:
            os.remove(self.pidfile)
            self.fifo.delfifo()
        except:
            pass

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if pid:
            if tools.is_process_alive(pid):
                message = "pidfile %s already exist. Daemon already running?\n"
                sys.stderr.write(message % self.pidfile)
                sys.exit(1)
            else:
                self.delpid()
       
        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            sys.stderr.write(message % self.pidfile)
            return # not an error in a restart

        # Try killing the daemon process       
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError, err:
            err = str(err)
            if err.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print err
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        pass
        
class FIFO(object):
    def __init__(self, cfg, log):
        self.config = cfg
        self.log = log
        self.fifo = self.config.get_password_cache_fifo()
            
    def __del__(self):
        self.delfifo()
        
    def delfifo(self):
        try:
            os.remove(self.fifo)
        except:
            pass
        
    def create(self):
        if os.path.exists(self.fifo):
            self.delfifo()
        try:
            os.mkfifo(self.fifo, 0600)
        except OSError, e:
            self.log.write('Failed to create FIFO: %s' % e)
            sys.exit(1)
        
    def read(self, timeout = 0):
        try:
            signal.signal(signal.SIGALRM, self.handler)
            signal.alarm(timeout)
            with open(self.fifo, 'r') as fifo:
                ret = fifo.read()
            signal.alarm(0)
        except Timeout as ex:
            self.log.write(str(ex))
            ret = ''
        return ret
        
    def write(self, string, timeout = 0):
        try:
            signal.signal(signal.SIGALRM, self.handler)
            signal.alarm(timeout)
            with open(self.fifo, 'a') as fifo:
                fifo.write(string)
            signal.alarm(0)
        except Timeout as ex:
            self.log.write(str(ex))

    def handler(self, signum, frame):
        raise Timeout('FIFO timeout')
    
class Log(object):
    def write(self, string):
        with open('/tmp/bit-daemon.log', 'a') as log:
            log.write('%s: %s\n' % (time.asctime(), string) )
     
class Password_Cache(Daemon):
    def __init__(self, cfg = None, *args, **kwargs):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()
        pw_cache_path = self.config.get_password_cache_folder()
        if not os.path.isdir(pw_cache_path):
            os.mkdir(pw_cache_path, 0700)
        else:
            os.chmod(pw_cache_path, 0700)
        Daemon.__init__(self, self.config.get_password_cache_pid(), *args, **kwargs)
        self.db = {'a': 'AAA', 'b': 'BBB', 'c': 'CCC', 'd': 'DDD'}
        self.log = Log()
        self.fifo = FIFO(self.config, self.log)
        
    def run(self):
        self.fifo.create()
        while True:
            try:
                request = self.fifo.read()
                request = request.split('\n')[0]
                if request in self.db.keys():
                    answer = self.db[request]
                else:
                    answer = 'NONE'
                try:
                    self.fifo.write(answer, 5)
                except IOError as ex:
                    self.log.write('Error in writing answer to FIFO: %s' % str(ex))
                else:
                    self.log.write('%s: %s' % (request, answer))
            except KeyboardInterrupt: 
                print('Quit.')
                break
            except BaseException:
                pass

if __name__ == "__main__":
    daemon = Password_Cache()
    if len(sys.argv) == 1:
        daemon.run()
        sys.exit(0)
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)