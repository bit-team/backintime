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

import sys
import os
import time
import atexit
import signal
import base64
import subprocess
import gettext
import stat
try:
    import keyring
except ImportError:
    print """Unable to import keyring module
On Debian like systems you probably need to install the following package(s):
python-keyring"""
    sys.exit(1)

import config
import configfile
import tools

_=gettext.gettext

class Timeout(Exception):
    pass
    
class Daemon:
    """
    A generic daemon class.
   
    Usage: subclass the Daemon class and override the run() method
    
    Daemon Copyright by Sander Marechal
    License CC BY-SA 3.0
    http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/null', stderr='/dev/null'):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
   
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
        sys.stdout.write('write pidfile\n')
        atexit.register(self.delpid)
        signal.signal(signal.SIGTERM, self._cleanup_handler)
        pid = str(os.getpid())
        with open(self.pidfile, 'w+') as pidfile:
            pidfile.write("%s\n" % pid)
        os.chmod(self.pidfile, 0600)

    def _cleanup_handler(self, signum, frame):
        self.fifo.delfifo()
        self.delpid()
        sys.exit(0)
        
    def delpid(self):
        try:
            os.remove(self.pidfile)
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
            if err.errno == 3:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print err.strerror
                sys.exit(1)

    def restart(self):
        """
        Restart the daemon
        """
        self.stop()
        self.start()
        
    def reload(self):
        """
        send SIGHUP signal to process
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
            return
        
        # Try killing the daemon process       
        try:
            os.kill(pid, signal.SIGHUP)
        except OSError, err:
            if err.errno == 3:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                sys.stderr.write(err.strerror)
                sys.exit(1)
        
    def status(self):
        """
        return status
        """
        # Get the pid from the pidfile
        try:
            pf = file(self.pidfile,'r')
            pid = int(pf.read().strip())
            pf.close()
        except IOError:
            pid = None

        if not pid:
            return False
        
        # Try killing the daemon process       
        try:
            os.kill(pid, 0)
        except OSError, err:
            if err.errno == 3:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
                    return False
            else:
                sys.stderr.write(err.strerror)
                return False
        return True

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        pass
        
class FIFO(object):
    def __init__(self, fname):
        self.fifo = fname
        
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
            sys.stderr.write('Failed to create FIFO: %s\n' % e.strerror)
            sys.exit(1)
        
    def read(self, timeout = 0):
        #sys.stdout.write('read fifo\n')
        if not self.is_fifo():
            sys.stderr.write('%s is not a FIFO\n' % self.fifo)
            sys.exit(1)
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(timeout)
        with open(self.fifo, 'r') as fifo:
            ret = fifo.read()
        signal.alarm(0)
        return ret
        
    def write(self, string, timeout = 0):
        #sys.stdout.write('write fifo\n')
        if not self.is_fifo():
            sys.stderr.write('%s is not a FIFO\n' % self.fifo)
            sys.exit(1)
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(timeout)
        with open(self.fifo, 'a') as fifo:
            fifo.write(string)
        signal.alarm(0)

    def handler(self, signum, frame):
        raise Timeout()
        
    def is_fifo(self):
        try:
            return stat.S_ISFIFO(os.stat(self.fifo).st_mode)
        except OSError:
            return False
    
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
        self.db = {}
        self.fifo = FIFO(self.config.get_password_cache_fifo())
        
    def start(self):
        self.save_env()
        Daemon.start(self)
        
    def run(self):
        self.save_env()
        self._collect_passwords()
        if len(self.db) == 0:
            sys.stdout.write('Nothing to cache. Quit.')
            sys.exit(0)
        self.fifo.create()
        atexit.register(self.fifo.delfifo)
        signal.signal(signal.SIGHUP, self._reload_handler)
        while True:
            try:
                request = self.fifo.read()
                request = request.split('\n')[0]
                if request in self.db.keys():
                    answer = self.db[request]
                else:
                    answer = ''
                try:
                    self.fifo.write(answer, 5)
                except IOError as e:
                    sys.stderr.write('Error in writing answer to FIFO: %s\n' % e.strerror)
                else:
                    sys.stdout.write('%s: %s\n' % (request, answer)) #Todo: delete debug
            except KeyboardInterrupt: 
                print('Quit.')
                break
            except Timeout as e:
                sys.stderr.write('FIFO timeout\n')
            except StandardError as e:
                sys.stderr.write('ERROR: %s\n' % str(e))
        
    def _reload_handler(self, signum, frame):
        sys.stdout.write('Reloading\n')
        del(self.db)
        self.db = {}
        self._collect_passwords()
        
    def _collect_passwords(self):
        profiles = self.config.get_profiles()
        for profile_id in profiles:
            mode = self.config.get_snapshots_mode(profile_id)
            if mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
                if self.config.get_password_save(profile_id):
                    if self.config.get_password_use_cache(profile_id):
                        service_name = self.config.get_keyring_service_name(profile_id, mode)
                        user_name = self.config.get_keyring_user_name(profile_id)
                            
                        password = keyring.get_password(service_name, user_name)
                        #add some snakeoil
                        pw_base64 = base64.encodestring(password)
                        self.db[profile_id] = pw_base64
        
    def save_env(self):
        """
        save environ variables to file that are needed by cron
        to connect to keyring. This will only work if the user is logged in.
        """
        env = os.environ.copy()
        env_file = configfile.ConfigFile()
        #ubuntu
        self.set_env_key(env, env_file, 'GNOME_KEYRING_CONTROL')
        self.set_env_key(env, env_file, 'DBUS_SESSION_BUS_ADDRESS')
        self.set_env_key(env, env_file, 'DISPLAY')
        
        env_file.save(self.config.get_cron_env_file())
        del(env_file)
        
    def set_env_key(self, env, env_file, key):
        if key in env.keys():
            env_file.set_str_value(key, env[key])

class Password(object):
    def __init__(self, cfg = None):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()
        self.pw_cache = Password_Cache(self.config)
        self.fifo = FIFO(self.config.get_password_cache_fifo())
        self.db = {}
        
    def get_password(self, profile_id, mode, only_from_keyring = False):
        if not mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
            return ''
        try:
            return self.db[profile_id][mode]
        except KeyError:
            pass
        if self.config.get_password_save(profile_id):
            if self.config.get_password_use_cache(profile_id) and not only_from_keyring:
                password = self._get_password_from_pw_cache(profile_id)
            else:
                password = self._get_password_from_keyring(profile_id, mode)
        else:
            if not only_from_keyring:
                password = self._get_password_from_user(profile_id)
            else:
                password = ''
        self._set_password_db(profile_id, mode, password)
        return password
        
    def _get_password_from_keyring(self, profile_id, mode):
        service_name = self.config.get_keyring_service_name(profile_id, mode)
        user_name = self.config.get_keyring_user_name(profile_id)
        return keyring.get_password(service_name, user_name)
    
    def _get_password_from_pw_cache(self, profile_id):
        if self.pw_cache:
            self.fifo.write(profile_id, timeout = 5)
            pw_base64 = self.fifo.read(timeout = 5)
            return base64.decodestring(pw_base64)
        else:
            return ''
    
    def _get_password_from_user(self, profile_id):
        """
        ask user for password. This does even work when run as cronjob
        and user is logged in.
        """
        try:
            subprocess.check_call(['xdpyinfo'],
                                stdout=open(os.devnull, 'w'),
                                stderr=open(os.devnull, 'w'))
        except subprocess.CalledProcessError:
            #DISPLAY is not available anymore
            return ''
        password, error = ('', '')
        signal.signal(signal.SIGALRM, self.handler)
        signal.alarm(20)
        try:
            proc = subprocess.Popen(['zenity', '--password', '--title',
                                    _('"BackInTime profile %s"') % self.config.get_profile_name(profile_id)],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            password, error = proc.communicate()
            signal.alarm(0)
        except Timeout:
            os.kill(proc.pid, signal.SIGKILL)
        if proc.returncode:
            print('Could not get password from user\nERROR %s: %s' %(proc.returncode, error))
        return password

    def handler(self, signum, frame):
        raise Timeout()
        
    def _set_password_db(self, profile_id, mode, password):
        if not profile_id in self.db.keys():
            self.db[profile_id] = {}
        self.db[profile_id][mode] = password
    
    def set_password(self, password, profile_id, mode):
        if mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
            service_name = self.config.get_keyring_service_name(profile_id, mode)
            user_name = self.config.get_keyring_user_name(profile_id)
            if self.config.get_password_save(profile_id):
                keyring.set_password(service_name, user_name, password)
                if self.config.get_password_use_cache(profile_id):
                    if self.pw_cache.status():
                        self.pw_cache.reload()
            self._set_password_db(profile_id, mode, password)
