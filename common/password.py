#    Copyright (c) 2012-2013 Germar Reitze
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
import keyring

import config
import configfile
import tools
import password_ipc

_=gettext.gettext

class Daemon:
    """
    A generic daemon class.
   
    Usage: subclass the Daemon class and override the run() method
    
    Daemon Copyright by Sander Marechal
    License CC BY-SA 3.0
    http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    """
    def __init__(self, pidfile, stdin='/dev/null', stdout='/dev/stdout', stderr='/dev/null'):
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
        
class Password_Cache(Daemon):
    """
    Password_Cache get started on User login. It provides passwords for
    BIT cronjobs because keyring is not available when the User is not
    logged in. Does not start if there is no password to cache
    (e.g. no profile allows to cache).
    """
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
        self.fifo = password_ipc.FIFO(self.config.get_password_cache_fifo())
        
        if self.config.get_keyring_backend() == 'kde':
            keyring.set_keyring(keyring.backend.KDEKWallet())
        else:
            keyring.set_keyring(keyring.backend.GnomeKeyring())
    
    def run(self):
        """
        wait for password request on FIFO and answer with password
        from self.db through FIFO.
        """
        tools.save_env(self.config)
        if tools.check_home_encrypt():
            sys.stdout.write('Home is encrypt. Doesn\'t make sense to cache passwords. Quit.')
            sys.exit(0)
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
                self.fifo.write(answer, 5)
            except IOError as e:
                sys.stderr.write('Error in writing answer to FIFO: %s\n' % e.strerror)
            except KeyboardInterrupt: 
                print('Quit.')
                break
            except tools.Timeout:
                sys.stderr.write('FIFO timeout\n')
            except StandardError as e:
                sys.stderr.write('ERROR: %s\n' % str(e))
        
    def _reload_handler(self, signum, frame):
        """
        reload passwords during runtime.
        """
        sys.stdout.write('Reloading\n')
        del(self.db)
        self.db = {}
        self._collect_passwords()
        
    def _collect_passwords(self):
        """
        search all profiles in config and collect passwords from keyring.
        """
        profiles = self.config.get_profiles()
        for profile_id in profiles:
            mode = self.config.get_snapshots_mode(profile_id)
            if mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
                if self.config.get_password_save(profile_id):
                    if self.config.get_password_use_cache(profile_id):
                        service_name = self.config.get_keyring_service_name(profile_id, mode)
                        user_name = self.config.get_keyring_user_name(profile_id)
                            
                        password = keyring.get_password(service_name, user_name)
                        if password is None:
                            continue
                        #add some snakeoil
                        pw_base64 = base64.encodestring(password)
                        self.db[profile_id] = pw_base64

class Password(object):
    """
    provide passwords for BIT either from keyring, Password_Cache or 
    by asking User.
    """
    def __init__(self, cfg = None):
        self.config = cfg
        if self.config is None:
            self.config = config.Config()
        self.pw_cache = Password_Cache(self.config)
        self.fifo = password_ipc.FIFO(self.config.get_password_cache_fifo())
        self.db = {}
        
        if self.config.get_keyring_backend() == 'kwallet':
            keyring.set_keyring(keyring.backend.KDEKWallet())
        else:
            keyring.set_keyring(keyring.backend.GnomeKeyring())
    
    def get_password(self, parent, profile_id, mode, only_from_keyring = False):
        """
        based on profile settings return password from keyring,
        Password_Cache or by asking User.
        """
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
                password = self._get_password_from_user(parent, profile_id, mode)
            else:
                password = ''
        self._set_password_db(profile_id, mode, password)
        return password
        
    def _get_password_from_keyring(self, profile_id, mode):
        """
        get password from system keyring (seahorse). The keyring is only
        available if User is logged in.
        """
        service_name = self.config.get_keyring_service_name(profile_id, mode)
        user_name = self.config.get_keyring_user_name(profile_id)
        return keyring.get_password(service_name, user_name)
    
    def _get_password_from_pw_cache(self, profile_id):
        """
        get password from Password_Cache
        """
        if self.pw_cache:
            self.fifo.write(profile_id, timeout = 5)
            pw_base64 = self.fifo.read(timeout = 5)
            return base64.decodestring(pw_base64)
        else:
            return ''
    
    def _get_password_from_user(self, parent, profile_id, mode):
        """
        ask user for password. This does even work when run as cronjob
        and user is logged in.
        """
        prompt = _('Enter Password for profile \'%(profile)s\' mode %(mode)s: ') % {'profile': self.config.get_profile_name(profile_id), 'mode': self.config.SNAPSHOT_MODES[mode][1]}
        
        gnome = os.path.join(self.config.get_app_path(), 'gnome')
        kde   = os.path.join(self.config.get_app_path(), 'kde4')
        for path in (gnome, kde):
            if os.path.isdir(path):
                sys.path = [path] + sys.path
                break
        
        x_server = tools.check_x_server()
        import_successful = False
        if x_server:
            try:
                import messagebox
                import_successful = True
            except ImportError:
                pass
            
        if not import_successful or not x_server:
            import getpass
            alarm = tools.Alarm()
            alarm.start(300)
            try:
                password = getpass.getpass(prompt)
                alarm.stop()
            except tools.Timeout:
                password = ''
            return password
        
        password = messagebox.ask_password_dialog(parent, self.config, 'Back in Time',
                    prompt = prompt,
                    timeout = 300)
        return password
        
    def _set_password_db(self, profile_id, mode, password):
        """
        internal Password cache. Prevent to ask password several times
        during runtime.
        """
        if not profile_id in self.db.keys():
            self.db[profile_id] = {}
        self.db[profile_id][mode] = password
    
    def set_password(self, password, profile_id, mode):
        """
        store password to keyring (seahorse). If caching is allowed
        reload Password_Cache
        """
        if mode in self.config.SNAPSHOT_MODES_NEED_PASSWORD:
            service_name = self.config.get_keyring_service_name(profile_id, mode)
            user_name = self.config.get_keyring_user_name(profile_id)
            if self.config.get_password_save(profile_id):
                keyring.set_password(service_name, user_name, password)
                if self.config.get_password_use_cache(profile_id):
                    if self.pw_cache.status():
                        self.pw_cache.reload()
            self._set_password_db(profile_id, mode, password)
