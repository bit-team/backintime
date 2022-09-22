#    Copyright (C) 2012-2022 Germar Reitze
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
import gettext

import config
import configfile
import tools
import password_ipc
import logger
from exceptions import Timeout

_ = gettext.gettext


class Password_Cache(tools.Daemon):
    """
    Password_Cache get started on User login. It provides passwords for
    BIT cronjobs because keyring is not available when the User is not
    logged in. Does not start if there is no password to cache
    (e.g. no profile allows to cache).
    """
    PW_CACHE_VERSION = 3

    def __init__(self, cfg=None, *args, **kwargs):
        """
        """

        self.config = cfg

        if self.config is None:
            self.config = config.Config()

        cachePath = self.config.passwordCacheFolder()

        if not tools.mkdir(cachePath, 0o700):
            msg = 'Failed to create secure Password_Cache folder'
            logger.error(msg, self)

            raise PermissionError(msg)

        pid = self.config.passwordCachePid()

        super(Password_Cache, self).__init__(pid, umask=0o077, *args, **kwargs)

        self.dbKeyring = {}
        self.dbUsr = {}
        self.fifo = password_ipc.FIFO(self.config.passwordCacheFifo())

        self.keyringSupported = tools.keyringSupported()

    def run(self):
        """
        wait for password request on FIFO and answer with password
        from self.db through FIFO.
        """

        info = configfile.ConfigFile()
        info.setIntValue('version', self.PW_CACHE_VERSION)
        info.save(self.config.passwordCacheInfo())
        os.chmod(self.config.passwordCacheInfo(), 0o600)

        logger.debug('Keyring supported: %s' % self.keyringSupported, self)

        tools.envSave(self.config.cronEnvFile())

        if not self.collectPasswords():
            logger.debug('Nothing to cache. Quit.', self)

            sys.exit(0)

        self.fifo.create()

        atexit.register(self.fifo.delfifo)
        signal.signal(signal.SIGHUP, self.reloadHandler)
        logger.debug('Start loop', self)

        while True:

            try:
                request = self.fifo.read()
                request = request.split('\n')[0]
                task, value = request.split(':', 1)

                if task == 'get_pw':
                    key = value

                    if key in list(self.dbKeyring.keys()):
                        answer = 'pw:' + self.dbKeyring[key]

                    elif key in list(self.dbUsr.keys()):
                        answer = 'pw:' + self.dbUsr[key]

                    else:
                        answer = 'none:'

                    self.fifo.write(answer, 5)

                elif task == 'set_pw':
                    key, value = value.split(':', 1)
                    self.dbUsr[key] = value

            except IOError as e:
                logger.error('Error in writing answer to FIFO: %s' % str(e), self)

            except KeyboardInterrupt:
                logger.debug('Quit.', self)
                break

            except Timeout:
                logger.error('FIFO timeout', self)

            except Exception as e:
                logger.error('ERROR: %s' % str(e), self)

    def reloadHandler(self, signum, frame):
        """
        reload passwords during runtime.
        """
        time.sleep(2)
        cfgPath = self.config._LOCAL_CONFIG_PATH

        self.config = None
        config.Config._instance = None

        self.config = config.Config(cfgPath)
        del(self.dbKeyring)
        self.dbKeyring = {}
        self.collectPasswords()

    def collectPasswords(self):
        """
        search all profiles in config and collect passwords from keyring.
        """
        run_daemon = False
        profiles = self.config.profiles()

        for profile_id in profiles:

            mode = self.config.snapshotsMode(profile_id)

            for pw_id in (1, 2):

                if self.config.modeNeedPassword(mode, pw_id):

                    if self.config.passwordUseCache(profile_id):
                        run_daemon = True

                        if self.config.passwordSave(profile_id) and self.keyringSupported:
                            service_name = self.config.keyringServiceName(profile_id, mode, pw_id)
                            user_name = self.config.keyringUserName(profile_id)

                            password = tools.password(service_name, user_name)

                            if password is None:
                                continue

                            self.dbKeyring['%s/%s' %(service_name, user_name)] = password

        return run_daemon

    def checkVersion(self):
        """
        """
        info = configfile.ConfigFile()
        info.load(self.config.passwordCacheInfo())

        if info.intValue('version') < self.PW_CACHE_VERSION:
            return False

        return True

    def cleanupHandler(self, signum, frame):
        """
        """
        self.fifo.delfifo()
        super(Password_Cache, self).cleanupHandler(signum, frame)


class Password(object):
    """
    Provide passwords for BIT either from keyring, Password_Cache or
    by asking User.
    """

    def __init__(self, cfg=None):
        """
        """
        self.config = cfg

        if self.config is None:
            self.config = config.Config.instance()

        self.cache = Password_Cache(self.config)
        self.fifo = password_ipc.FIFO(self.config.passwordCacheFifo())
        self.db = {}

        self.keyringSupported = tools.keyringSupported()

    def password(self, parent, profile_id, mode, pw_id = 1, only_from_keyring = False):
        """
        based on profile settings return password from keyring,
        Password_Cache or by asking User.
        """
        if not self.config.modeNeedPassword(mode, pw_id):
            return ''
        service_name = self.config.keyringServiceName(profile_id, mode, pw_id)
        user_name = self.config.keyringUserName(profile_id)
        try:
            return self.db['%s/%s' %(service_name, user_name)]
        except KeyError:
            pass
        password = ''
        if self.config.passwordUseCache(profile_id) and not only_from_keyring:
            #from cache
            password = self.passwordFromCache(service_name, user_name)
            if not password is None:
                self.setPasswordDb(service_name, user_name, password)
                return password
        if self.config.passwordSave(profile_id):
            #from keyring
            password = self.passwordFromKeyring(service_name, user_name)
            if not password is None:
                self.setPasswordDb(service_name, user_name, password)
                return password
        if not only_from_keyring:
            #ask user and write to cache
            password = self.passwordFromUser(parent, profile_id, mode, pw_id)
            if self.config.passwordUseCache(profile_id):
                self.setPasswordCache(service_name, user_name, password)
            self.setPasswordDb(service_name, user_name, password)
            return password
        return password

    def passwordFromKeyring(self, service_name, user_name):
        """
        get password from system keyring (seahorse). The keyring is only
        available if User is logged in.
        """
        if self.keyringSupported:
            try:
                return tools.password(service_name, user_name)
            except Exception:
                logger.error('get password from Keyring failed', self)
        return None

    def passwordFromCache(self, service_name, user_name):
        """
        get password from Password_Cache
        """
        if self.cache.status():
            self.cache.checkVersion()
            self.fifo.write('get_pw:%s/%s' %(service_name, user_name), timeout = 5)
            answer = self.fifo.read(timeout = 5)
            mode, pw = answer.split(':', 1)
            if mode == 'none':
                return None
            return pw
        else:
            return None

    def passwordFromUser(self, parent, profile_id = None, mode = None, pw_id = 1, prompt = None):
        """
        ask user for password. This does even work when run as cronjob
        and user is logged in.
        """
        if prompt is None:
            prompt = _('Profile \'%(profile)s\': Enter password for %(mode)s: ') % {'profile': self.config.profileName(profile_id), 'mode': self.config.SNAPSHOT_MODES[mode][pw_id + 1]}

        tools.registerBackintimePath('qt')

        x_server = tools.checkXServer()
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
            except Timeout:
                password = ''
            return password

        password = messagebox.askPasswordDialog(parent, self.config.APP_NAME,
                    prompt = prompt,
                    timeout = 300)
        return password

    def setPasswordDb(self, service_name, user_name, password):
        """
        internal Password cache. Prevent to ask password several times
        during runtime.
        """
        self.db['%s/%s' %(service_name, user_name)] = password

    def setPassword(self, password, profile_id, mode, pw_id):
        """
        store password to keyring and Password_Cache
        """
        if self.config.modeNeedPassword(mode, pw_id):
            service_name = self.config.keyringServiceName(profile_id, mode, pw_id)
            user_name = self.config.keyringUserName(profile_id)

            if self.config.passwordSave(profile_id):
                self.setPasswordKeyring(service_name, user_name, password)

            if self.config.passwordUseCache(profile_id):
                self.setPasswordCache(service_name, user_name, password)

            self.setPasswordDb(service_name, user_name, password)

    def setPasswordKeyring(self, service_name, user_name, password):
        return tools.setPassword(service_name, user_name, password)

    def setPasswordCache(self, service_name, user_name, password):
        if self.cache.status():
            self.cache.checkVersion()
            self.fifo.write('set_pw:%s/%s:%s' %(service_name, user_name, password), timeout = 5)
