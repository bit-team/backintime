"""Collection of helper functions not fitting to other modules.
"""
# Back In Time
# Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey,
# Germar Reitze, Taylor Raack
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
import os
import sys
import pathlib
import subprocess
import shlex
import signal
import re
import errno
import gzip
import tempfile
import gettext
try:
    from collections.abc import MutableSet
except ImportError:
    from collections import MutableSet
import hashlib
import ipaddress
import atexit
from datetime import datetime
from packaging.version import Version
from time import sleep

import logger

# Try to import keyring
is_keyring_available = False
try:
    # Jan 4, 2024 aryoda: The env var BIT_USE_KEYRING is neither documented
    #                     anywhere nor used at all in the code.
    #                     Via "git blame" I have found a commit message saying:
    #                     "block subsequent 'import keyring' if it failed once"
    #                     So I assume it is an internal temporary env var only.
    # Note: os.geteuid() is used instead of tools.isRoot() here
    #       because the latter is still not available here in the global
    #       module code.
    if os.getenv('BIT_USE_KEYRING', 'true') == 'true' and os.geteuid() != 0:
        import keyring
        from keyring import backend
        import keyring.util.platform_
        is_keyring_available = True
except Exception as e:
    is_keyring_available = False
    # block subsequent 'import keyring' if it failed once before
    os.putenv('BIT_USE_KEYRING', 'false')
    logger.warning(f"'import keyring' failed with: {repr(e)}")

# getting dbus imports to work in Travis CI is a huge pain
# use conditional dbus import
ON_TRAVIS = os.environ.get('TRAVIS', 'None').lower() == 'true'
ON_RTD = os.environ.get('READTHEDOCS', 'None').lower() == 'true'

try:
    import dbus
except ImportError:
    if ON_TRAVIS or ON_RTD:
        # python-dbus doesn't work on Travis yet.
        dbus = None
    else:
        raise

import configfile
import bcolors
from applicationinstance import ApplicationInstance
from exceptions import Timeout, InvalidChar, InvalidCmd, LimitExceeded, PermissionDeniedByPolicy
import languages

DISK_BY_UUID = '/dev/disk/by-uuid'

# |-----------------|
# | Handling paths  |
# |-----------------|


def sharePath():
    """Get path where Back In Time is installed.

    This is similar to $XDG_DATA_DIRS (XDG Base Directory Specification).
    If running from source return default ``/usr/share``.

    Returns:
        str: share path like::

                    /usr/share
                    /usr/local/share
                    /opt/usr/share
    """
    share = os.path.abspath(
        os.path.join(__file__, os.pardir, os.pardir, os.pardir)
    )

    if os.path.basename(share) == 'share':
        return share

    return '/usr/share'


def backintimePath(*path):
    """
    Get path inside 'backintime' install folder.

    Args:
        *path (str):    paths that should be joined to 'backintime'

    Returns:
        str:            'backintime' child path like::

                            /usr/share/backintime/common
                            /usr/share/backintime/qt
    """
    return os.path.abspath(os.path.join(__file__, os.pardir, os.pardir, *path))


def docPath():
    """Not sure what this path is about.
    """
    path = pathlib.Path(sharePath()) / 'doc' / 'backintime-common'

    # Dev note (buhtz, aryoda, 2024-02):
    # This piece of code originally resisted in Config.__init__() and was
    # introduced by Dan in 2008. The reason for the existence of this "if"
    # is unclear.

    # Makefile (in common) does only install into share/doc/backintime-common
    # but never into the the backintime "binary" path so I guess the if is
    # a) either a distro-specific exception for a distro package that
    # (manually?) installs the LICENSE into another path
    # b) or a left-over from old code where the LICENSE was installed
    # differently...

    license_file = pathlib.Path(backintimePath()) / 'LICENSE'
    if license_file.exists():
        path = backintimePath()

    return str(path)


# |---------------------------------------------------|
# | Internationalization (i18n) & localization (L10n) |
# |---------------------------------------------------|
_GETTEXT_DOMAIN = 'backintime'
_GETTEXT_LOCALE_DIR = pathlib.Path(sharePath()) / 'locale'


def _determine_current_used_language_code(translation, language_code):
    """Return the language code used by GNU gettext for real.

    Args:
        translation(gettext.NullTranslations): The translation installed.
        language_code(str): Configured language code.

    The used language code can differ from the one in Back In Times config
    file and from the current systems locale.

    It is necessary because of situations where the language is not explicit
    setup in Back In Time config file and GNU gettext do try to find and use a
    language file for the current systems locale. But even this can fail and
    the fallback (source language "en") is used or an alternative locale.
    """

    try:
        # The field "language" is rooted in header of the po-file.
        current_used_language_code = translation.info()['language']

    except KeyError:
        # Workaround:
        # BIT versions 1.3.3 or older don't have the "language" field in the
        # header of their po-files.

        # The approach is to extract the language code from the full filepath
        # of the currently used mo-file.

        # Get the filepath of the used mo-file
        mo_file_path = gettext.find(
            domain=_GETTEXT_DOMAIN,
            localedir=_GETTEXT_LOCALE_DIR,
            languages=[language_code, ] if language_code else None,
        )

        # Extract the language code form that path
        if mo_file_path:
            mo_file_path = pathlib.Path(mo_file_path)
            # e.g /usr/share/locale/de/LC_MESSAGES/backintime.mo
            #                       ^^
            current_used_language_code = mo_file_path.relative_to(
                _GETTEXT_LOCALE_DIR).parts[0]

        else:
            # Workaround: Happens when LC_ALL=C, which in BIT context mean
            # its source language in English.
            current_used_language_code = 'en'

    return current_used_language_code


def initiate_translation(language_code):
    """Initiate Class-based API of GNU gettext.

    Args:
        language_code(str): Language code to use (based on ISO-639).

    It installs the ``_()`` (and ``ngettext()`` for plural forms)  in the
    ``builtins`` namespace and eliminates the need to ``import gettext``
    and declare ``_()`` in each module. The systems current local is used
    if the language code is None.
    """

    if language_code:
        logger.debug(f'Language code "{language_code}".')
    else:
        logger.debug('No language code. Use systems current locale.')

    translation = gettext.translation(
        domain=_GETTEXT_DOMAIN,
        localedir=_GETTEXT_LOCALE_DIR,
        languages=[language_code, ] if language_code else None,
        fallback=True
    )
    translation.install(names=['ngettext'])

    return _determine_current_used_language_code(translation, language_code)


def get_available_language_codes():
    """Return language codes available in the current installation.

    The filesystem is searched for ``backintime.mo`` files and the language
    code is extracted from the full path of that files.

    Return:
        List of language codes.
    """

    # full path of one mo-file
    # e.g. /usr/share/locale/de/LC_MESSAGES/backintime.mo
    mo = gettext.find(domain=_GETTEXT_DOMAIN, localedir=_GETTEXT_LOCALE_DIR)

    if mo:
        mo = pathlib.Path(mo)
    else:
        # Workaround. This happens if LC_ALL=C and BIT don't use an explicit
        # language. Should be re-design.
        mo = _GETTEXT_LOCALE_DIR / 'xy' / 'LC_MESSAGES' / 'backintime.mo'

    # e.g. de/LC_MESSAGES/backintime.mo
    mo = mo.relative_to(_GETTEXT_LOCALE_DIR)

    # e.g. */LC_MESSAGES/backintime.mo
    mo = pathlib.Path('*') / pathlib.Path(*mo.parts[1:])

    mofiles = _GETTEXT_LOCALE_DIR.rglob(str(mo))

    return [p.relative_to(_GETTEXT_LOCALE_DIR).parts[0] for p in mofiles]


def get_language_names(language_code):
    """Return a list with language names in three different flavors.

    Language codes from `get_available_language_codes()` are combined with
    `languages.language_names` to prepare the list.

    Args:
        language_code (str): Usually the current language used by Back In Time.

    Returns:
        A dictionary indexed by language codes with 3-item tuples as
        values. Each tuple contain three representations of the same language:
        ``language_code`` (usually the current locales language),
        the language itself (native) and in English (the source language);
        e.g. ``ja`` (Japanese) for ``de`` (German) locale
        is ``('Japanisch', '日本語', 'Japanese')``.
    """
    result = {}
    codes = ['en'] + get_available_language_codes()

    for c in codes:

        try:
            # A dict with one specific language and how its name is
            # represented in all other languages.
            # e.g. "Japanese" in "de" is "Japanisch"
            # e.g. "Deutsch" in "es" is "alemán"
            lang = languages.names[c]

        except KeyError:
            names = None

        else:
            names = (
                # in currents locale language
                lang[language_code],
                # native
                lang['_native'],
                # in English (source language)
                lang['en']
            )

        result[c] = names

    return result


def get_native_language_and_completeness(language_code):
    """Return the language name in its native flavor and the completeness of
    its translation in percent.

    Args:
        language_code(str): The language code.

    Returns:
        A two-entry tuple with language name as string and a percent as
        integer.
    """
    name = languages.names[language_code][language_code]
    completeness = languages.completeness[language_code]

    return (name, completeness)


# |------------------------------------|
# | Miscellaneous, not categorized yet |
# |------------------------------------|
def registerBackintimePath(*path):
    """
    Add BackInTime path ``path`` to :py:data:`sys.path` so subsequent imports
    can discover them.

    Args:
        *path (str):    paths that should be joined to 'backintime'

    Note:
        Duplicate in :py:func:`qt/qttools.py` because modules in qt folder
        would need this to actually import :py:mod:`tools`.
    """
    path = backintimePath(*path)

    if path not in sys.path:
        sys.path.insert(0, path)


def runningFromSource():
    """
    Check if BackInTime is running from source (without installing).

    Returns:
        bool:   ``True`` if BackInTime is running from source
    """
    return os.path.isfile(backintimePath('common', 'backintime'))


def addSourceToPathEnviron():
    """
    Add 'backintime/common' path to 'PATH' environ variable.
    """
    source = backintimePath('common')
    path = os.getenv('PATH')
    if path and source not in path.split(':'):
        os.environ['PATH'] = '%s:%s' % (source, path)


def get_git_repository_info(path=None, hash_length=None):
    """Return the current branch and last commit hash.

    About the length of a commit hash. There is no strict rule but it is
    common sense that 8 to 10 characters are enough to be unique.

    Credits: https://stackoverflow.com/a/51224861/4865723

    Args:
        path (Path): Path with '.git' folder in (default is
                     current working directory).
        cut_hash (int): Restrict length of commit hash.

    Returns:
        (dict): Dict with keys "branch" and "hash" if it is a git repo,
                otherwise an `None`.
    """

    if not path:
        # Default is current working dir
        path = pathlib.Path.cwd()
    elif isinstance(path, str):
        # WORKAROUND until cmoplete migration to pathlib
        path = pathlib.Path(path)

    git_folder = path / '.git'

    if not git_folder.exists():
        return None

    result = {}

    # branch name
    with (git_folder / 'HEAD').open('r') as handle:
        val = handle.read()

    if not val.startswith('ref: '):
        result['branch'] = '(detached HEAD)'
        result['hash'] = val

    else:
        result['branch'] = '/'.join(val.split('/')[2:]).strip()

        # commit hash
        with (git_folder / 'refs' / 'heads' / result['branch']) \
            .open('r') as handle:
            result['hash'] = handle.read().strip()

    if hash_length:
        result['hash'] = result['hash'][:hash_length]

    return result


def readFile(path, default=None):
    """
    Read the file in ``path`` or its '.gz' compressed variant and return its
    content or ``default`` if ``path`` does not exist.

    Args:
        path (str):             full path to file that should be read.
                                '.gz' will be added automatically if the file
                                is compressed
        default (str):          default if ``path`` does not exist

    Returns:
        str:                    content of file in ``path``
    """
    ret_val = default

    try:
        if os.path.exists(path):

            with open(path) as f:
                ret_val = f.read()

        elif os.path.exists(path + '.gz'):

            with gzip.open(path + '.gz', 'rt') as f:
                ret_val = f.read()

    except:
        pass

    return ret_val


def readFileLines(path, default = None):
    """
    Read the file in ``path`` or its '.gz' compressed variant and return its
    content as a list of lines or ``default`` if ``path`` does not exist.

    Args:
        path (str):             full path to file that should be read.
                                '.gz' will be added automatically if the file
                                is compressed
        default (list):         default if ``path`` does not exist

    Returns:
        list:                   content of file in ``path`` split by lines.
    """
    ret_val = default

    try:
        if os.path.exists(path):
            with open(path) as f:
                ret_val = [x.rstrip('\n') for x in f.readlines()]
        elif os.path.exists(path + '.gz'):
            with gzip.open(path + '.gz', 'rt') as f:
                ret_val = [x.rstrip('\n') for x in f.readlines()]
    except:
        pass

    return ret_val


def checkCommand(cmd):
    """
    Check if command ``cmd`` is a file in 'PATH' environ.

    Args:
        cmd (str):  command

    Returns:
        bool:       ``True`` if command ``cmd`` is in 'PATH' environ
    """
    cmd = cmd.strip()

    if not cmd:
        return False

    if os.path.isfile(cmd):
        return True

    return not which(cmd) is None


def which(cmd):
    """
    Get the fullpath of executable command ``cmd``. Works like
    command-line 'which' command.

    Args:
        cmd (str):  command

    Returns:
        str:        fullpath of command ``cmd`` or ``None`` if command is
                    not available
    """
    pathenv = os.getenv('PATH', '')
    path = pathenv.split(":")
    common = backintimePath('common')

    if runningFromSource() and common not in path:
        path.insert(0, common)

    for directory in path:
        fullpath = os.path.join(directory, cmd)

        if os.path.isfile(fullpath) and os.access(fullpath, os.X_OK):
            return fullpath

    return None


def makeDirs(path):
    """
    Create directories ``path`` recursive and return success.

    Args:
        path (str): fullpath to directories that should be created

    Returns:
        bool:       ``True`` if successful
    """
    path = path.rstrip(os.sep)
    if not path:
        return False

    if os.path.isdir(path):
        return True

    else:

        try:
            os.makedirs(path)
        except Exception as e:
            logger.error("Failed to make dirs '%s': %s"
                         % (path, str(e)), traceDepth=1)

    return os.path.isdir(path)


def mkdir(path, mode=0o755, enforce_permissions=True):
    """
    Create directory ``path``.

    Args:
        path (str): full path to directory that should be created
        mode (int): numeric permission mode

    Returns:
        bool:       ``True`` if successful
    """
    if os.path.isdir(path):
        try:
            if enforce_permissions:
                os.chmod(path, mode)
        except:
            return False

        return True

    else:
        os.mkdir(path, mode)

        if mode & 0o002 == 0o002:
            # make file world (other) writable was requested
            # debian and ubuntu won't set o+w with os.mkdir
            # this will fix it
            os.chmod(path, mode)

    return os.path.isdir(path)


def pids():
    """
    List all PIDs currently running on the system.

    Returns:
        list:   PIDs as int
    """
    return [int(x) for x in os.listdir('/proc') if x.isdigit()]


def processStat(pid):
    """
    Get the stat's of the process with ``pid``.

    Args:
        pid (int):  Process Indicator

    Returns:
        str:        stat from /proc/PID/stat
    """
    try:
        with open('/proc/{}/stat'.format(pid), 'rt') as f:
            return f.read()

    except OSError as e:
        logger.warning('Failed to read process stat from {}: [{}] {}'
                       .format(e.filename, e.errno, e.strerror))
        return ''


def processPaused(pid):
    """
    Check if process ``pid`` is paused (got signal SIGSTOP).

    Args:
        pid (int):  Process Indicator

    Returns:
        bool:       True if process is paused
    """
    m = re.match(r'\d+ \(.+\) T', processStat(pid))

    return bool(m)


def processName(pid):
    """
    Get the name of the process with ``pid``.

    Args:
        pid (int):  Process Indicator

    Returns:
        str:        name of the process
    """
    m = re.match(r'.*\((.+)\).*', processStat(pid))

    if m:
        return m.group(1)


def processCmdline(pid):
    """
    Get the cmdline (command that spawnd this process) of the process with
    ``pid``.

    Args:
        pid (int):  Process Indicator

    Returns:
        str:        cmdline of the process
    """
    try:
        with open('/proc/{}/cmdline'.format(pid), 'rt') as f:
            return f.read().strip('\n')
    except OSError as e:
        logger.warning('Failed to read process cmdline from {}: [{}] {}'.format(e.filename, e.errno, e.strerror))
        return ''

def pidsWithName(name):
    """
    Get all processes currently running with name ``name``.

    Args:
        name (str): name of a process like 'python3' or 'backintime'

    Returns:
        list:       PIDs as int
    """
    # /proc/###/stat stores just the first 16 chars of the process name
    return [x for x in pids() if processName(x) == name[:15]]

def processExists(name):
    """
    Check if process ``name`` is currently running.

    Args:
        name (str): name of a process like 'python3' or 'backintime'

    Returns:
        bool:       ``True`` if there is a process running with ``name``
    """
    return len(pidsWithName(name)) > 0

def processAlive(pid):
    """
    Check if the process with PID ``pid`` is alive.

    Args:
        pid (int):  Process Indicator

    Returns:
        bool:       ``True`` if the process with PID ``pid`` is alive

    Raises:
        ValueError: If ``pid`` is 0 because 'kill(0, SIG)' would send SIG to all
                    processes
    """
    if pid < 0:
        return False
    elif pid == 0:
        raise ValueError('invalid PID 0')
    else:
        try:
            os.kill(pid, 0) #this will raise an exception if the pid is not valid
        except OSError as err:
            if err.errno == errno.ESRCH:
                # ESRCH == No such process
                return False
            elif err.errno == errno.EPERM:
                # EPERM clearly means there's a process to deny access to
                return True
            else:
                raise
        else:
            return True

def checkXServer():
    """
    Check if there is a X11 server running on this system.

    Use ``is_Qt_working`` instead if you want to be sure that Qt is working.

    Returns:
        bool:   ``True`` if X11 server is running
    """
    # Note: Return values of xdpyinfo <> 0 are not clearly documented.
    #       xdpyinfo does indeed return 1 if it prints
    #           xdypinfo: unable to open display "..."
    #       This seems to be undocumented (at least not in the man pages)
    #       and the source is not obvious here:
    #       https://cgit.freedesktop.org/xorg/app/xdpyinfo/tree/xdpyinfo.c
    if checkCommand('xdpyinfo'):
        proc = subprocess.Popen(['xdpyinfo'],
                                stdout = subprocess.DEVNULL,
                                stderr = subprocess.DEVNULL)
        proc.communicate()
        return proc.returncode == 0
    else:
        return False


def is_Qt_working(systray_required=False):
    """
    Check if the Qt GUI library is working (installed and configured)

    This function is contained in BiT CLI (not BiT Qt) to allow Qt
    diagnostics output even if the BiT Qt GUI is not installed.
    This function does NOT add a hard Qt dependency (just "probing")
    so it is OK to be in BiT CLI.

    Args:
        systray_required: Set to ``True`` if the systray of the desktop
        environment must be available too to consider Qt as "working"

    Returns:
        bool: ``True``  Qt can create a GUI
              ``False`` Qt fails (or the systray is not available
                        if ``systray_required`` is ``True``)
    """

    # Spawns a new process since it may crash with a SIGABRT and we
    # don't want to crash BiT if this happens...

    try:
        path = os.path.join(backintimePath("common"), "qt_probing.py")
        cmd = [sys.executable, path]
        if logger.DEBUG:
            cmd.append('--debug')

        with subprocess.Popen(cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True) as proc:

            std_output, error_output = proc.communicate(timeout=30)  # to get the exit code
            # "timeout" fixes #1592 (qt_probing.py may hang as root): Kill after timeout

            logger.debug(f"Qt probing result: exit code {proc.returncode}")

            if proc.returncode != 2 or logger.DEBUG:  # if some Qt parts are missing: Show details
                logger.debug(f"Qt probing stdout:\n{std_output}")
                logger.debug(f"Qt probing errout:\n{error_output}")

            return proc.returncode == 2 or (proc.returncode == 1 and systray_required is False)

    except FileNotFoundError:
        logger.error(f"Qt probing script not found: {cmd[0]}")
        raise

    # Fix for #1592 (qt_probing.py may hang as root): Kill after timeout
    except subprocess.TimeoutExpired:
        proc.kill()
        outs, errs = proc.communicate()
        logger.info("Qt probing sub process killed after timeout without response")
        logger.debug(f"Qt probing stdout:\n{outs}")
        logger.debug(f"Qt probing errout:\n{errs}")

    except Exception as e:
        logger.error(f"Error: {repr(e)}")
        raise


def preparePath(path):
    """
    Removes trailing slash '/' from ``path``.

    Args:
        path (str): absolute path

    Returns:
        str:        path ``path`` without trailing but with leading slash
    """
    path = path.strip("/")
    path = os.sep + path
    return path

def powerStatusAvailable():
    """
    Check if org.freedesktop.UPower is available so that
    :py:func:`tools.onBattery` would return the correct power status.

    Returns:
        bool:   ``True`` if :py:func:`tools.onBattery` can report power status
    """
    if dbus:
        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.UPower',
                                   '/org/freedesktop/UPower')
            return 'OnBattery' in proxy.GetAll('org.freedesktop.UPower',
                            dbus_interface = 'org.freedesktop.DBus.Properties')
        except dbus.exceptions.DBusException:
            pass
    return False

def onBattery():
    """
    Checks if the system is on battery power.

    Returns:
        bool:   ``True`` if system is running on battery
    """
    if dbus:
        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.UPower',
                                   '/org/freedesktop/UPower')
            return bool(proxy.Get('org.freedesktop.UPower',
                                  'OnBattery',
                                  dbus_interface = 'org.freedesktop.DBus.Properties'))
        except dbus.exceptions.DBusException:
            pass
    return False

def rsyncCaps(data = None):
    """
    Get capabilities of the installed rsync binary. This can be different from
    version to version and also on build arguments used when building rsync.

    Args:
        data (str): 'rsync --version' output. This is just for unittests.

    Returns:
        list:       List of str with rsyncs capabilities
    """
    if not data:
        proc = subprocess.Popen(['rsync', '--version'],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
        data = proc.communicate()[0]
    caps = []
    #rsync >= 3.1 does provide --info=progress2
    matchers = [r'rsync\s*version\s*(\d\.\d)', r'rsync\s*version\s*v(\d\.\d.\d)']
    for matcher in matchers:
        m = re.match(matcher, data)
        if m and Version(m.group(1)) >= Version('3.1'):
            caps.append('progress2')
            break

    #all other capabilities are separated by ',' between
    #'Capabilities:' and '\n\n'
    m = re.match(r'.*Capabilities:(.+)\n\n.*', data, re.DOTALL)
    if not m:
        return caps

    for line in m.group(1).split('\n'):
        caps.extend([i.strip(' \n') for i in line.split(',') if i.strip(' \n')])
    return caps


def rsyncPrefix(config,
                no_perms=True,
                use_mode=['ssh', 'ssh_encfs'],
                progress=True):
    """
    Get rsync command and all args for creating a new snapshot. Args are
    based on current profile in ``config``.

    Args:
        config (config.Config): current config
        no_perms (bool):        don't sync permissions (--no-p --no-g --no-o)
                                if ``True``.
                                :py:func:`config.Config.preserveAcl` == ``True`` or
                                :py:func:`config.Config.preserveXattr` == ``True``
                                will overwrite this to ``False``
        use_mode (list):        if current mode is in this list add additional
                                args for that mode
        progress (bool):        add '--info=progress2' to show progress

    Returns:
        list:                   rsync command with all args but without
                                --include, --exclude, source and destination
    """
    caps = rsyncCaps()
    cmd = []

    if config.nocacheOnLocal():
        cmd.append('nocache')

    cmd.append('rsync')

    cmd.extend((
        # recurse into directories
        '--recursive',
        # preserve modification times
        '--times',
        # preserve device files (super-user only)
        '--devices',
        # preserve special files
        '--specials',
        # preserve hard links
        '--hard-links',
        # numbers in a human-readable format
        '--human-readable',
        # use "new" argument protection
        '-s'
    ))

    if config.useChecksum() or config.forceUseChecksum:
        cmd.append('--checksum')

    if config.copyUnsafeLinks():
        cmd.append('--copy-unsafe-links')

    if config.copyLinks():
        cmd.append('--copy-links')
    else:
        cmd.append('--links')

    if config.oneFileSystem():
        cmd.append('--one-file-system')

    if config.preserveAcl() and "ACLs" in caps:
        cmd.append('--acls')  # preserve ACLs (implies --perms)
        no_perms = False

    if config.preserveXattr() and "xattrs" in caps:
        cmd.append('--xattrs')  # preserve extended attributes
        no_perms = False

    if no_perms:
        cmd.extend(('--no-perms', '--no-group', '--no-owner'))
    else:
        cmd.extend(('--perms',          # preserve permissions
                    '--executability',  # preserve executability
                    '--group',         # preserve group
                    '--owner'))         # preserve owner (super-user only)

    if progress and 'progress2' in caps:
        cmd.extend(('--info=progress2',
                    '--no-inc-recursive'))

    if config.bwlimitEnabled():
        cmd.append('--bwlimit=%d' % config.bwlimit())

    if config.rsyncOptionsEnabled():
        cmd.extend(shlex.split(config.rsyncOptions()))

    cmd.extend(rsyncSshArgs(config, use_mode))
    return cmd


def rsyncSshArgs(config, use_mode=['ssh', 'ssh_encfs']):
    """
    Get SSH args for rsync based on current profile in ``config``.

    Args:
        config (config.Config): Current config instance.
        use_mode (list):        If the profiles current mode is in this list
                                add additional args.

    Returns:
        list:                   List of rsync args related to SSH.
    """

    cmd = []

    mode = config.snapshotsMode()

    if mode in ['ssh', 'ssh_encfs'] and mode in use_mode:
        ssh = config.sshCommand(user_host=False,
                                ionice=False,
                                nice=False)

        cmd.append('--rsh=' + ' '.join(ssh))

        if config.niceOnRemote() \
           or config.ioniceOnRemote() \
           or config.nocacheOnRemote():

            rsync_path = '--rsync-path='

            if config.niceOnRemote():
                rsync_path += 'nice -n 19 '

            if config.ioniceOnRemote():
                rsync_path += 'ionice -c2 -n7 '

            if config.nocacheOnRemote():
                rsync_path += 'nocache '

            rsync_path += 'rsync'

            cmd.append(rsync_path)

    return cmd


def rsyncRemove(config, run_local = True):
    """
    Get rsync command and all args for removing snapshots with rsync.

    Args:
        config (config.Config): current config
        run_local (bool):       if True and current mode is ``ssh``
                                or ``ssh_encfs`` this will add SSH options

    Returns:
        list:                   rsync command with all args
    """
    cmd = ['rsync', '-a', '--delete', '-s']
    if run_local:
        cmd.extend(rsyncSshArgs(config))
    return cmd

#TODO: check if we really need this
def tempFailureRetry(func, *args, **kwargs):
    while True:
        try:
            return func(*args, **kwargs)
        except (os.error, IOError) as ex:
            if ex.errno == errno.EINTR:
                continue
            else:
                raise

def md5sum(path):
    """
    Calculate md5sum for file in ``path``.

    Args:
        path (str): full path to file

    Returns:
        str:        md5sum of file
    """
    md5 = hashlib.md5()
    with open(path, 'rb') as f:
        while True:
            data = f.read(4096)
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()

def checkCronPattern(s):
    """
    Check if ``s`` is a valid cron pattern.
    Examples::

        0,10,13,15,17,20,23
        */6

    Args:
        s (str):    pattern to check

    Returns:
        bool:       ``True`` if ``s`` is a valid cron pattern
    """
    if s.find(' ') >= 0:
        return False
    try:
        if s.startswith('*/'):
            if s[2:].isdigit() and int(s[2:]) <= 24:
                return True
            else:
                return False
        for i in s.split(','):
            if i.isdigit() and int(i) <= 24:
                continue
            else:
                return False
        return True
    except ValueError:
        return False


#TODO: check if this is still necessary
def checkHomeEncrypt():
    """
    Return ``True`` if users home is encrypted
    """
    home = os.path.expanduser('~')
    if not os.path.ismount(home):
        return False
    if checkCommand('ecryptfs-verify'):
        try:
            subprocess.check_call(['ecryptfs-verify', '--home'],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            pass
        else:
            return True
    if checkCommand('encfs'):
        proc = subprocess.Popen(['mount'], stdout=subprocess.PIPE, universal_newlines = True)
        mount = proc.communicate()[0]
        r = re.compile('^encfs on %s type fuse' % home)
        for line in mount.split('\n'):
            if r.match(line):
                return True
    return False


def envLoad(f):
    """
    Load environ variables from file ``f`` into current environ.
    Do not overwrite existing environ variables.

    Args:
        f (str):    full path to file with environ variables
    """
    env = os.environ.copy()
    env_file = configfile.ConfigFile()
    env_file.load(f, maxsplit = 1)
    for key in env_file.keys():
        value = env_file.strValue(key)
        if not value:
            continue
        if not key in list(env.keys()):
            os.environ[key] = value
    del(env_file)


def envSave(f):
    """
    Save environ variables to file that are needed by cron
    to connect to keyring. This will only work if the user is logged in.

    Args:
        f (str):    full path to file for environ variables
    """
    env = os.environ.copy()
    env_file = configfile.ConfigFile()
    for key in ('GNOME_KEYRING_CONTROL', 'DBUS_SESSION_BUS_ADDRESS', \
                'DBUS_SESSION_BUS_PID', 'DBUS_SESSION_BUS_WINDOWID', \
                'DISPLAY', 'XAUTHORITY', 'GNOME_DESKTOP_SESSION_ID', \
                'KDE_FULL_SESSION'):
        if key in env:
            env_file.setStrValue(key, env[key])

    env_file.save(f)


def keyringSupported():
    """
    Checks if a keyring (supported by BiT) is available

    Returns:
         bool: ``True`` if a supported keyring could be loaded
    """

    if not is_keyring_available:
        logger.debug('No keyring due to import error.')
        return False

    keyring_config_file_folder = "Unknown"
    try:
        keyring_config_file_folder = keyring.util.platform_.config_root()
    except:
        pass

    logger.debug(f"Keyring config file folder: {keyring_config_file_folder}")

    # Determine the currently active backend
    try:
        # get_keyring() internally calls keyring.core.init_backend()
        # which fixes non-available backends for the first call.
        # See related issue #1321:
        # https://github.com/bit-team/backintime/issues/1321
        # The module name is used instead of the class name
        # to show only the keyring name (not the technical name)
        displayName = keyring.get_keyring().__module__
    except:
        displayName = str(keyring.get_keyring())  # technical class name!

    logger.debug("Available keyring backends:")
    try:
        for b in backend.get_all_keyring():
            logger.debug(b)
    except Exception as e:
        logger.debug("Available backends cannot be listed: " + repr(e))

    available_backends = []

    # Create a list of installed backends that BiT supports (white-listed).
    # This is done by trying to put the meta classes ("class definitions",
    # NOT instances of the class itself!) of the supported backends
    # into the "backends" list

    backends_to_check = [
        (keyring.backends, ['SecretService', 'Keyring']),
        (keyring.backends, ['Gnome', 'Keyring']),
        (keyring.backends, ['kwallet', 'Keyring']),
        (keyring.backends, ['kwallet', 'DBusKeyring']),
        (keyring.backend, ['SecretServiceKeyring']),
        (keyring.backend, ['GnomeKeyring']),
        (keyring.backend, ['KDEWallet']),
        # See issue #1410: ChainerBackend is now supported to solve the
        # problem of configuring the used backend since it iterates over all
        # of them and is to be the default backend now. Please read the issue
        # details to understand the unwanted side-effects the chainer could
        # bring with it.
        # See also:
        # https://github.com/jaraco/keyring/blob/977ed03677bb0602b91f005461ef3dddf01a49f6/keyring/backends/chainer.py#L11  # noqa
        (keyring.backends, ('chainer', 'ChainerBackend')),
    ]

    for backend_package, backends in backends_to_check:
        result = backend_package  # e.g. keyring.backends

        try:
            # Load the backend step-by-step.
            # e.g. When the target is "keyring.backends.Gnome.Keyring" then in
            # a first step "Gnome" part is loaded first and if successful the
            # "keyring" part.
            for b in backends:
                result = getattr(result, b)

        except AttributeError as err:
            # Debug message if backend is not available.
            logger.debug('Metaclass {}.{} not found: {}'
                         .format(backend_package.__name__,
                                 '.'.join(backends),
                                 repr(err)))

        else:
            # Remember the backend class (not an instance) as available.
            available_backends.append(result)

    logger.debug("Available supported backends: " + repr(available_backends))

    if available_backends and isinstance(keyring.get_keyring(), tuple(available_backends)):
        logger.debug("Found appropriate keyring '{}'".format(displayName))
        return True

    logger.debug(f"No appropriate keyring found. '{displayName}' can't be "
                 "used with BackInTime.")
    logger.debug("See https://github.com/bit-team/backintime on how to fix "
                 "this by creating a keyring config file.")

    return False


def password(*args):

    if is_keyring_available:
        return keyring.get_password(*args)
    return None


def setPassword(*args):

    if is_keyring_available:
        return keyring.set_password(*args)
    return False


def mountpoint(path):
    """
    Get the mountpoint of ``path``. If your HOME is on a separate partition
    mountpoint('/home/user/foo') would return '/home'.

    Args:
        path (str): full path

    Returns:
        str:        mountpoint of the filesystem
    """
    path = os.path.realpath(os.path.abspath(path))

    while path != os.path.sep:
        if os.path.ismount(path):
            return path

        path = os.path.abspath(os.path.join(path, os.pardir))

    return path


def decodeOctalEscape(s):
    """
    Decode octal-escaped characters with its ASCII dependence.
    For example '\040' will be a space ' '

    Args:
        s (str):    string with or without octal-escaped characters

    Returns:
        str:        human readable string
    """
    def repl(m):
        return chr(int(m.group(1), 8))
    return re.sub(r'\\(\d{3})', repl, s)


def mountArgs(path):
    """
    Get all /etc/mtab args for the filesystem of ``path`` as a list.
    Example::

        [DEVICE,      MOUNTPOINT, FILESYSTEM_TYPE, OPTIONS,    DUMP, PASS]
        ['/dev/sda3', '/',        'ext4',          'defaults', '0',  '0']
        ['/dev/sda1', '/boot',    'ext4',          'defaults', '0',  '0']

    Args:
        path (str): full path

    Returns:
        list:       mount args
    """
    mp = mountpoint(path)

    with open('/etc/mtab', 'r') as mounts:

        for line in mounts:
            args = line.strip('\n').split(' ')

            if len(args) >= 2:
                args[1] = decodeOctalEscape(args[1])

                if args[1] == mp:
                    return args

    return None


def device(path):
    """
    Get the device for the filesystem of ``path``.
    Example::

        /dev/sda1
        /dev/mapper/vglinux
        proc

    Args:
        path (str): full path

    Returns:
        str:        device
    """
    args = mountArgs(path)

    if args:
        return args[0]

    return None


def filesystem(path):
    """
    Get the filesystem type for the filesystem of ``path``.

    Args:
        path (str): full path

    Returns:
        str:        filesystem
    """
    args = mountArgs(path)
    if args and len(args) >= 3:
        return args[2]
    return None

def _uuidFromDev_via_filesystem(dev):
    """Get the UUID for the block device ``dev`` from ``/dev/disk/by-uuid`` in
    the filesystem.

    Args:
        dev (pathlib.Path): The block device path (e.g. ``/dev/sda1``).

    Returns:
        str: The UUID or ``None`` if nothing found.
    """


    # /dev/disk/by-uuid
    path_DISK_BY_UUID = pathlib.Path(DISK_BY_UUID)

    if not path_DISK_BY_UUID.exists():
        return None

    # Each known uuid
    for uuid_symlink in path_DISK_BY_UUID.glob('*'):

        # Resolve the symlink (get it's target) to get the real device name
        # and compare it with the device we are looking for
        if dev == uuid_symlink.resolve():

            # e.g. 'c7aca0a7-89ed-43f0-a4f9-c744dfe673e0'
            return uuid_symlink.name

    # Nothing found
    return None

def _uuidFromDev_via_blkid_command(dev):
    """Get the UUID for the block device ``dev`` via the extern command
    ``blkid``.

    Hint:
        On most systems the ``blkid`` command is available only for the
        super-user (e.g. via ``sudo``).

    Args:
        dev (pathlib.Path): The block device path (e.g. ``/dev/sda1``).

    Returns:
        str: The UUID or ``None`` if nothing found.
    """

    # Call "blkid" command
    try:
        # If device does not exist, blkid will exit with a non-zero code
        output = subprocess.check_output(['blkid', dev],
                                        stderr = subprocess.DEVNULL,
                                        universal_newlines=True)

    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    # Parse the commands output for a UUID
    try:
        return re.findall(r'.*\sUUID=\"([^\"]*)\".*', output)[0]
    except IndexError:
        # nothing found via the regex pattern
        pass

    return None

def _uuidFromDev_via_udevadm_command(dev):
    """Get the UUID for the block device ``dev`` via the extern command
    ``udevadm``.

    Args:
        dev (pathlib.Path): The block device path (e.g. ``/dev/sda1``).

    Returns:
        str: The UUID or ``None`` if nothing found.
    """
    # Call "udevadm" command
    try:
        output = subprocess.check_output(['udevadm', 'info', f'--name={dev}'],
                                        stderr = subprocess.DEVNULL,
                                        universal_newlines=True)

    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    # Parse the commands output for a UUID
    try:
        return re.findall(r'.*?ID_FS_UUID=(\S+)', output)[0]
    except IndexError:
        # nothing found via the regex pattern
        pass

    return None


def uuidFromDev(dev):
    """
    Get the UUID for the block device ``dev``.

    Args:
        dev (str, pathlib.Path):  block device path

    Returns:
        str:        UUID
    """

    # handle Path objects only
    if not isinstance(dev, pathlib.Path):
        dev = pathlib.Path(dev)

    if dev.exists():
        dev = dev.resolve()  # when /dev/sda1 is a symlink

        # Look at /dev/disk/by-uuid/
        uuid = _uuidFromDev_via_filesystem(dev)
        if uuid:
            return uuid

        # Try extern command "blkid"
        uuid = _uuidFromDev_via_blkid_command(dev)
        if uuid:
            return uuid

    # "dev" doesn't exist in the filesystem

    # Try "udevadm" command at the end
    return _uuidFromDev_via_udevadm_command(dev)


def uuidFromPath(path):
    """
    Get the UUID for the for the filesystem of ``path``.

    Args:
        path (str): full path

    Returns:
        str:        UUID
    """
    return uuidFromDev(device(path))


def filesystemMountInfo():
    """
    Get a dict of mount point string -> dict of filesystem info for
    entire system.

    Returns:
        dict:   {MOUNTPOINT: {'original_uuid': UUID}}
    """
    # There may be multiple mount points inside of the root (/) mount, so
    # iterate over mtab to find all non-special mounts.
    with open('/etc/mtab', 'r') as mounts:
        return {items[1]: {'original_uuid': uuidFromDev(items[0])} for items in
                [mount_line.strip('\n').split(' ')[:2] for mount_line in mounts]
                if uuidFromDev(items[0]) != None}


def isRoot():
    """
    Check if we are root.

    Returns:
        bool:   ``True`` if we are root
    """

    # The EUID (Effective UID) may be different from the UID (user ID)
    # in case of SetUID or using "sudo" (where EUID is "root" and UID
    # is the original user who executed "sudo").
    return os.geteuid() == 0

def usingSudo():
    """
    Check if 'sudo' was used to start this process.

    Returns:
        bool:   ``True`` if the process was started with sudo
    """
    return isRoot() and os.getenv('HOME', '/root') != '/root'

re_wildcard = re.compile(r'(?:\[|\]|\?)')
re_asterisk = re.compile(r'\*')
re_separate_asterisk = re.compile(r'(?:^\*+[^/\*]|[^/\*]\*+[^/\*]|[^/\*]\*+|\*+[^/\*]|[^/\*]\*+$)')

def patternHasNotEncryptableWildcard(pattern):
    """
    Check if ``pattern`` has wildcards ``[ ] ? *``.
    but return ``False`` for ``foo/*``, ``foo/*/bar``, ``*/bar`` or ``**/bar``

    Args:
        pattern (str):  path or pattern to check

    Returns:
        bool:           ``True`` if ``pattern`` has wildcards ``[ ] ? *`` but
                        ``False`` if wildcard look like
                        ``foo/*``, ``foo/*/bar``, ``*/bar`` or ``**/bar``
    """
    if not re_wildcard.search(pattern) is None:
        return True

    if not re_asterisk is None and not re_separate_asterisk.search(pattern) is None:
        return True
    return False

BIT_TIME_FORMAT = '%Y%m%d %H%M'
ANACRON_TIME_FORMAT = '%Y%m%d'

def readTimeStamp(fname):
    """
    Read date string from file ``fname`` and try to return datetime.

    Args:
        fname (str):        full path to timestamp file

    Returns:
        datetime.datetime:  date from timestamp file
    """
    if not os.path.exists(fname):
        logger.debug("no timestamp in '%(file)s'" %
                     {'file': fname})
        return
    with open(fname, 'r') as f:
        s = f.read().strip('\n')
    for i in (ANACRON_TIME_FORMAT, BIT_TIME_FORMAT):
        try:
            stamp = datetime.strptime(s, i)
            logger.debug("read timestamp '%(time)s' from file '%(file)s'" %
                         {'time': stamp,
                          'file': fname})
            return stamp
        except ValueError:
            pass

def writeTimeStamp(fname):
    """
    Write current date and time into file ``fname``.

    Args:
        fname (str):        full path to timestamp file
    """
    now = datetime.now().strftime(BIT_TIME_FORMAT)
    logger.debug("write timestamp '%(time)s' into file '%(file)s'" %
                 {'time': now,
                  'file': fname})
    makeDirs(os.path.dirname(fname))
    with open(fname, 'w') as f:
        f.write(now)

INHIBIT_LOGGING_OUT = 1
INHIBIT_USER_SWITCHING = 2
INHIBIT_SUSPENDING = 4
INHIBIT_IDLE = 8

INHIBIT_DBUS = (
               {'service':      'org.gnome.SessionManager',
                'objectPath':   '/org/gnome/SessionManager',
                'methodSet':    'Inhibit',
                'methodUnSet':  'Uninhibit',
                'interface':    'org.gnome.SessionManager',
                'arguments':    (0, 1, 2, 3)
               },
               {'service':      'org.mate.SessionManager',
                'objectPath':   '/org/mate/SessionManager',
                'methodSet':    'Inhibit',
                'methodUnSet':  'Uninhibit',
                'interface':    'org.mate.SessionManager',
                'arguments':    (0, 1, 2, 3)
               },
               {'service':      'org.freedesktop.PowerManagement',
                'objectPath':   '/org/freedesktop/PowerManagement/Inhibit',
                'methodSet':    'Inhibit',
                'methodUnSet':  'UnInhibit',
                'interface':    'org.freedesktop.PowerManagement.Inhibit',
                'arguments':    (0, 2)
               })

def inhibitSuspend(app_id = sys.argv[0],
                    toplevel_xid = None,
                    reason = 'take snapshot',
                    flags = INHIBIT_SUSPENDING | INHIBIT_IDLE):
    """
    Prevent machine to go to suspend or hibernate.
    Returns the inhibit cookie which is used to end the inhibitor.
    """
    if ON_TRAVIS or dbus is None:
        # no suspend on travis (no dbus either)
        return

    # Fixes #1592 (BiT hangs as root when trying to establish a dbus user session connection)
    # Side effect: In BiT <= 1.4.1 root still tried to connect to the dbus user session
    #              and it may have worked sometimes (without logging we don't know)
    #              so as root suspend can no longer inhibited.
    if isRoot():
        logger.debug("Inhibit Suspend failed because BIT was started as root.")
        return

    if not app_id:
        app_id = 'backintime'
    try:
        if not toplevel_xid:
            toplevel_xid = 0
    except IndexError:
        toplevel_xid = 0

    for dbus_props in INHIBIT_DBUS:
        try:
            #connect directly to the socket instead of dbus.SessionBus because
            #the dbus.SessionBus was initiated before we loaded the environ
            #variables and might not work
            if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                bus = dbus.bus.BusConnection(os.environ['DBUS_SESSION_BUS_ADDRESS'])
            else:
                bus = dbus.SessionBus()  # This code may hang forever (if BiT is run as root via cron job and no user is logged in). See #1592
            interface = bus.get_object(dbus_props['service'], dbus_props['objectPath'])
            proxy = interface.get_dbus_method(dbus_props['methodSet'], dbus_props['interface'])
            cookie = proxy(*[(app_id, dbus.UInt32(toplevel_xid), reason, dbus.UInt32(flags))[i] for i in dbus_props['arguments']])
            logger.debug('Inhibit Suspend started. Reason: {}'.format(reason))
            return (cookie, bus, dbus_props)
        except dbus.exceptions.DBusException:
            pass
    logger.warning('Inhibit Suspend failed.')

def unInhibitSuspend(cookie, bus, dbus_props):
    """
    Release inhibit.
    """
    assert isinstance(cookie, int), 'cookie is not int type: %s' % cookie
    assert isinstance(bus, dbus.bus.BusConnection), 'bus is not dbus.bus.BusConnection type: %s' % bus
    assert isinstance(dbus_props, dict), 'dbus_props is not dict type: %s' % dbus_props
    try:
        interface = bus.get_object(dbus_props['service'], dbus_props['objectPath'])
        proxy = interface.get_dbus_method(dbus_props['methodUnSet'], dbus_props['interface'])
        proxy(cookie)
        logger.debug('Release inhibit Suspend')
        return None
    except dbus.exceptions.DBusException:
        logger.warning('Release inhibit Suspend failed.')
        return (cookie, bus, dbus_props)

def readCrontab():
    """
    Read users crontab.

    Returns:
        list:   crontab lines
    """
    cmd = ['crontab', '-l']
    if not checkCommand(cmd[0]):
        logger.debug('crontab not found.')
        return []
    else:
        proc = subprocess.Popen(cmd,
                                stdout = subprocess.PIPE,
                                stderr = subprocess.PIPE,
                                universal_newlines = True)
        out, err = proc.communicate()
        if proc.returncode or err:
            logger.error('Failed to get crontab lines: %s, %s'
                         %(proc.returncode, err))
            return []
        else:
            crontab = [x.strip() for x in out.strip('\n').split('\n')]
            if crontab == ['']:  # Fixes issue #1181 (line count of empty crontab was 1 instead of 0)
                crontab = []
            logger.debug('Read %s lines from user crontab'
                         %len(crontab))
            return crontab

def writeCrontab(lines):
    """
    Write to users crontab.

    Note:
        This will overwrite the whole crontab. So to keep the old crontab and
        only add new entries you need to read it first with
        :py:func:`tools.readCrontab`, append new entries to the list and write
        it back.

    Args:
        lines (:py:class:`list`, :py:class:`tuple`):
                    lines that should be written to crontab

    Returns:
        bool:       ``True`` if successful
    """
    assert isinstance(lines, (list, tuple)), 'lines is not list or tuple type: %s' % lines
    with tempfile.NamedTemporaryFile(mode = 'wt') as f:
        f.write('\n'.join(lines))
        f.write('\n\n')
        f.flush()
        cmd = ['crontab', f.name]
        proc = subprocess.Popen(cmd,
                                stdout = subprocess.DEVNULL,
                                stderr = subprocess.PIPE,
                                universal_newlines = True)
        out, err = proc.communicate()
    if proc.returncode or err:
        logger.error('Failed to write lines to crontab: %s, %s'
                     %(proc.returncode, err))
        return False
    else:
        logger.debug('Wrote %s lines to user crontab'
                     %len(lines))
        return True

def splitCommands(cmds, head = '', tail = '', maxLength = 0):
    """
    Split a list of commands ``cmds`` into multiple commands with each length
    lower than ``maxLength``.

    Args:
        cmds (list):            commands
        head (str):             command that need to run first on every
                                iteration of ``cmds``
        tail (str):             command that need to run after every iteration
                                of ``cmds``
        maxLength (int):        maximum length a command could be.
                                Don't split if <= 0

    Yields:
        str:                    new command with length < ``maxLength``

    Example::

        head cmds[0] cmds[n] tail
    """
    while cmds:
        s = head
        while cmds and ((len(s + cmds[0] + tail) <= maxLength) or maxLength <= 0):
            s += cmds.pop(0)
        s += tail
        yield s

def isIPv6Address(address):
    """
    Check if ``address`` is a valid IPv6 address.

    Args:
        address (str):  address that should get tested

    Returns:
        bool:           True if ``address`` is a valid IPv6 address
    """
    try:
        return isinstance(ipaddress.IPv6Address(address), ipaddress.IPv6Address)
    except:
        return False

def escapeIPv6Address(address):
    """
    Escape IPv6 Addresses with square brackets ``[]``.

    Args:
        address (str):  address that should be escaped

    Returns:
        str:            ``address`` in square brackets
    """
    if isIPv6Address(address):
        return '[{}]'.format(address)
    else:
        return address

def camelCase(s):
    """
    Remove underlines and make every first char uppercase.

    Args:
        s (str):    string separated by underlines (foo_bar)

    Returns:
        str:        string without underlines but uppercase chars (FooBar)
    """
    return ''.join([x.capitalize() for x in s.split('_')])

def fdDup(old, new_fd, mode = 'w'):
    """
    Duplicate file descriptor `old` to `new_fd` and closing the latter first.
    Used to redirect stdin, stdout and stderr from daemonized threads.

    Args:
        old (str):                  Path to the old file (e.g. /dev/stdout)
        new_fd (_io.TextIOWrapper): file object for the new file
        mode (str):                 mode in which the old file should be opened
    """
    try:
        fd = open(old, mode)
        os.dup2(fd.fileno(), new_fd.fileno())
    except OSError as e:
        logger.debug('Failed to redirect {}: {}'.format(old, str(e)))


class UniquenessSet:
    """
    Check for uniqueness or equality of files.

    Args:
        dc (bool):              if ``True`` use deep check which will compare
                                files md5sums if they are of same size but no
                                hardlinks (don't have the same inode).
                                If ``False`` use files size and mtime
        follow_symlink (bool):  if ``True`` check symlinks target instead of the
                                link
        list_equal_to (str):    full path to file. If not empty only return
                                equal files to the given path instead of
                                unique files.
    """
    def __init__(self, dc = False, follow_symlink = False, list_equal_to = ''):
        self.deep_check = dc
        self.follow_sym = follow_symlink
        self._uniq_dict = {}      # if not self._uniq_dict[size] -> size already checked with md5sum
        self._size_inode = set()  # if (size,inode) in self._size_inode -> path is a hlink
        self.list_equal_to = list_equal_to
        if list_equal_to:
            st = os.stat(list_equal_to)
            if self.deep_check:
                self.reference = (st.st_size, md5sum(list_equal_to))
            else:
                self.reference = (st.st_size, int(st.st_mtime))

    def check(self, input_path):
        """
        Check file ``input_path`` for either uniqueness or equality
        (depending on ``list_equal_to`` from constructor).

        Args:
            input_path (str):   full path to file

        Returns:
            bool:               ``True`` if file is unique and ``list_equal_to``
                                is empty.
                                Or ``True`` if file is equal to file in
                                ``list_equal_to``
        """
        # follow symlinks ?
        path = input_path
        if self.follow_sym and os.path.islink(input_path):
            path = os.readlink(input_path)

        if self.list_equal_to:
            return self.checkEqual(path)
        else:
            return self.checkUnique(path)

    def checkUnique(self, path):
        """
        Check file ``path`` for uniqueness and store a unique key for ``path``.

        Args:
            path (str): full path to file

        Returns:
            bool:       ``True`` if file is unique
        """
        # check
        if self.deep_check:
            dum = os.stat(path)
            size,inode  = dum.st_size, dum.st_ino
            # is it a hlink ?
            if (size, inode) in self._size_inode:
                logger.debug("[deep test]: skip, it's a duplicate (size, inode)", self)
                return False
            self._size_inode.add((size,inode))
            if size not in self._uniq_dict:
                # first item of that size
                unique_key = size
                logger.debug("[deep test]: store current size?", self)
            else:
                prev = self._uniq_dict[size]
                if prev:
                    # store md5sum instead of previously stored size
                    md5sum_prev = md5sum(prev)
                    self._uniq_dict[size] = None
                    self._uniq_dict[md5sum_prev] = prev
                    logger.debug("[deep test]: size duplicate, remove the size, store prev md5sum", self)
                unique_key = md5sum(path)
                logger.debug("[deep test]: store current md5sum?", self)
        else:
            # store a tuple of (size, modification time)
            obj  = os.stat(path)
            unique_key = (obj.st_size, int(obj.st_mtime))
        # store if not already present, then return True
        if unique_key not in self._uniq_dict:
            logger.debug(" >> ok, store!", self)
            self._uniq_dict[unique_key] = path
            return True
        logger.debug(" >> skip (it's a duplicate)", self)
        return False

    def checkEqual(self, path):
        """
        Check if ``path`` is equal to the file in ``list_equal_to`` from
        constructor.

        Args:
            path (str): full path to file

        Returns:
            bool:       ``True`` if file is equal
        """
        st = os.stat(path)
        if self.deep_check:
            if self.reference[0] == st.st_size:
                return self.reference[1] == md5sum(path)
            return False
        else:
            return self.reference == (st.st_size, int(st.st_mtime))


class Alarm(object):
    """
    Establish a callback function that is called after a timeout.

    The implementation uses a SIGALRM signal so
    do not call code in the callback that does not support multi-threading
    (reentrance) or you may cause non-deterministic "random" RTEs.
    """
    def __init__(self, callback = None, overwrite = True):
        """
        Create a new alarm instance

        Args:
            callback: Function to call when the timer ran down
                      (ensure calling only reentrant code).
                      Use ``None`` to throw a ``Timeout`` exception instead.
            overwrite: Is it allowed to (re)start the timer
                       even though the current timer is still running
                       ("ticking"):
                       ``True`` cancels the current timer (if active)
                                and restarts with the new timeout.
                       ``False` silently ignores the start request
                                if the current timer is still "ticking"
        """
        self.callback = callback
        self.ticking = False
        self.overwrite = overwrite

    def start(self, timeout):
        """
        Start the timer (which calls the handler function
        when the timer ran down).

        The start is silently ignored if the current timer is still
        ticking and the the attribute ``overwrite`` is ``False``.

        Args:
            timeout: timer count down in seconds
        """
        if self.ticking and not self.overwrite:
            return
        try:
            # Warning: This code may cause non-deterministic RTEs
            #          if the handler function calls code that does
            #          not support reentrance (see e.g. issue #1003).
            signal.signal(signal.SIGALRM, self.handler)
            signal.alarm(timeout)
        except ValueError:
            pass
        self.ticking = True

    def stop(self):
        """
        Stop timer before it comes to an end
        """
        try:
            signal.alarm(0)
            self.ticking = False
        except:
            pass

    def handler(self, signum, frame):
        """
        This method is called after the timer ran down to zero
        and calls the callback function of the alarm instance.

        Raises:
            Timeout: If no callback function was set for the alarm instance
        """
        self.ticking = False
        if self.callback is None:
            raise Timeout()
        else:
            self.callback()


class ShutDown(object):
    """
    Shutdown the system after the current snapshot has finished.
    This should work for KDE, Gnome, Unity, Cinnamon, XFCE, Mate and E17.
    """
    DBUS_SHUTDOWN ={'gnome':   {'bus':          'sessionbus',
                                'service':      'org.gnome.SessionManager',
                                'objectPath':   '/org/gnome/SessionManager',
                                'method':       'Shutdown',
                                    #methods    Shutdown
                                    #           Reboot
                                    #           Logout
                                'interface':    'org.gnome.SessionManager',
                                'arguments':    ()
                                    #arg (only with Logout)
                                    #           0 normal
                                    #           1 no confirm
                                    #           2 force
                               },
                    'kde':     {'bus':          'sessionbus',
                                'service':      'org.kde.ksmserver',
                                'objectPath':   '/KSMServer',
                                'method':       'logout',
                                'interface':    'org.kde.KSMServerInterface',
                                'arguments':    (-1, 2, -1)
                                    #1st arg   -1 confirm
                                    #           0 no confirm
                                    #2nd arg   -1 full dialog with default logout
                                    #           0 logout
                                    #           1 restart
                                    #           2 shutdown
                                    #3rd arg   -1 wait 30sec
                                    #           2 immediately
                               },
                    'xfce':    {'bus':          'sessionbus',
                                'service':      'org.xfce.SessionManager',
                                'objectPath':   '/org/xfce/SessionManager',
                                'method':       'Shutdown',
                                    #methods    Shutdown
                                    #           Restart
                                    #           Suspend (no args)
                                    #           Hibernate (no args)
                                    #           Logout (two args)
                                'interface':    'org.xfce.Session.Manager',
                                'arguments':    (True,)
                                    #arg        True    allow saving
                                    #           False   don't allow saving
                                    #1st arg (only with Logout)
                                    #           True    show dialog
                                    #           False   don't show dialog
                                    #2nd arg (only with Logout)
                                    #           True    allow saving
                                    #           False   don't allow saving
                               },
                    'mate':    {'bus':          'sessionbus',
                                'service':      'org.mate.SessionManager',
                                'objectPath':   '/org/mate/SessionManager',
                                'method':       'Shutdown',
                                    #methods    Shutdown
                                    #           Logout
                                'interface':    'org.mate.SessionManager',
                                'arguments':    ()
                                    #arg (only with Logout)
                                    #           0 normal
                                    #           1 no confirm
                                    #           2 force
                               },
                    'e17':     {'bus':          'sessionbus',
                                'service':      'org.enlightenment.Remote.service',
                                'objectPath':   '/org/enlightenment/Remote/RemoteObject',
                                'method':       'Halt',
                                    #methods    Halt -> Shutdown
                                    #           Reboot
                                    #           Logout
                                    #           Suspend
                                    #           Hibernate
                                'interface':    'org.enlightenment.Remote.Core',
                                'arguments':    ()
                               },
                    'e19':     {'bus':          'sessionbus',
                                'service':      'org.enlightenment.wm.service',
                                'objectPath':   '/org/enlightenment/wm/RemoteObject',
                                'method':       'Shutdown',
                                    #methods    Shutdown
                                    #           Restart
                                'interface':    'org.enlightenment.wm.Core',
                                'arguments':    ()
                               },
                    'z_freed': {'bus':          'systembus',
                                'service':      'org.freedesktop.login1',
                                'objectPath':   '/org/freedesktop/login1',
                                'method':       'PowerOff',
                                'interface':    'org.freedesktop.login1.Manager',
                                'arguments':    (True,)
                               }
                   }

    def __init__(self):
        self.is_root = isRoot()
        if self.is_root:
            self.proxy, self.args = None, None
        else:
            self.proxy, self.args = self._prepair()
        self.activate_shutdown = False
        self.started = False

    def _prepair(self):
        """
        Try to connect to the given dbus services. If successful it will
        return a callable dbus proxy and those arguments.
        """
        try:
            if 'DBUS_SESSION_BUS_ADDRESS' in os.environ:
                sessionbus = dbus.bus.BusConnection(os.environ['DBUS_SESSION_BUS_ADDRESS'])
            else:
                sessionbus = dbus.SessionBus()
            systembus  = dbus.SystemBus()
        except:
            return((None, None))
        des = list(self.DBUS_SHUTDOWN.keys())
        des.sort()
        for de in des:
            if de == 'gnome' and self.unity7():
                continue
            dbus_props = self.DBUS_SHUTDOWN[de]
            try:
                if dbus_props['bus'] == 'sessionbus':
                    bus = sessionbus
                else:
                    bus = systembus
                interface = bus.get_object(dbus_props['service'], dbus_props['objectPath'])
                proxy = interface.get_dbus_method(dbus_props['method'], dbus_props['interface'])
                return((proxy, dbus_props['arguments']))
            except dbus.exceptions.DBusException:
                continue
        return((None, None))

    def canShutdown(self):
        """
        Indicate if a valid dbus service is available to shutdown system.
        """
        return(not self.proxy is None or self.is_root)

    def askBeforeQuit(self):
        """
        Indicate if ShutDown is ready to fire and so the application
        shouldn't be closed.
        """
        return(self.activate_shutdown and not self.started)

    def shutdown(self):
        """
        Run 'shutdown -h now' if we are root or
        call the dbus proxy to start the shutdown.
        """
        if not self.activate_shutdown:
            return(False)

        if self.is_root:
            self.started = True
            proc = subprocess.Popen(['shutdown', '-h', 'now'])
            proc.communicate()
            return proc.returncode

        if self.proxy is None:
            return(False)

        else:
            self.started = True

            return(self.proxy(*self.args))

    def unity7(self):
        """
        Unity >= 7.0 doesn't shutdown automatically. It will
        only show shutdown dialog and wait for user input.
        """
        if not checkCommand('unity'):
            return False
        proc = subprocess.Popen(['unity', '--version'],
                                stdout = subprocess.PIPE,
                                universal_newlines = True)
        unity_version = proc.communicate()[0]
        m = re.match(r'unity ([\d\.]+)', unity_version)

        return m and Version(m.group(1)) >= Version('7.0') and processExists('unity-panel-service')


class SetupUdev(object):
    """
    Setup Udev rules for starting BackInTime when a drive get connected.
    This is done by serviceHelper.py script (included in backintime-qt)
    running as root though DBus.
    """
    CONNECTION = 'net.launchpad.backintime.serviceHelper'
    OBJECT = '/UdevRules'
    INTERFACE = 'net.launchpad.backintime.serviceHelper.UdevRules'
    MEMBERS = ('addRule', 'save', 'delete')
    def __init__(self):
        if dbus is None:
            self.isReady = False
            return
        try:
            bus = dbus.SystemBus()
            conn = bus.get_object(SetupUdev.CONNECTION, SetupUdev.OBJECT)
            self.iface = dbus.Interface(conn, SetupUdev.INTERFACE)
        except dbus.exceptions.DBusException as e:
            # Only DBusExceptions are  handled to do a "graceful recovery"
            # by working without a serviceHelper D-Bus connection...
            # All other exceptions are still raised causing BiT
            # to stop during startup.
            # if e._dbus_error_name in ('org.freedesktop.DBus.Error.NameHasNoOwner',
            #                           'org.freedesktop.DBus.Error.ServiceUnknown',
            #                           'org.freedesktop.DBus.Error.FileNotFound'):
            logger.warning("Failed to connect to Udev serviceHelper daemon via D-Bus: " + e.get_dbus_name())
            logger.warning("D-Bus message: " + e.get_dbus_message())
            logger.warning("Udev-based profiles cannot be changed or checked due to Udev serviceHelper connection failure")
            conn = None
            # else:
            #     raise
        self.isReady = bool(conn)

    def addRule(self, cmd, uuid):
        """
        Prepare rules in serviceHelper.py
        """
        if not self.isReady:
            return
        try:
            return self.iface.addRule(cmd, uuid)
        except dbus.exceptions.DBusException as e:
            if e._dbus_error_name == 'net.launchpad.backintime.InvalidChar':
                raise InvalidChar(str(e))
            elif e._dbus_error_name == 'net.launchpad.backintime.InvalidCmd':
                raise InvalidCmd(str(e))
            elif e._dbus_error_name == 'net.launchpad.backintime.LimitExceeded':
                raise LimitExceeded(str(e))
            else:
                raise

    def save(self):
        """
        Save rules with serviceHelper.py after authentication
        If no rules where added before this will delete current rule.
        """
        if not self.isReady:
            return
        try:
            return self.iface.save()
        except dbus.exceptions.DBusException as e:
            if e._dbus_error_name == 'com.ubuntu.DeviceDriver.PermissionDeniedByPolicy':
                raise PermissionDeniedByPolicy(str(e))
            else:
                raise

    def clean(self):
        """
        Clean up remote cache
        """
        if not self.isReady:
            return
        self.iface.clean()


class PathHistory(object):
    def __init__(self, path):
        self.history = [path,]
        self.index = 0

    def append(self, path):
        #append path after the current index
        self.history = self.history[:self.index + 1] + [path,]
        self.index = len(self.history) - 1

    def previous(self):
        if self.index == 0:
            return self.history[0]
        try:
            path = self.history[self.index - 1]
        except IndexError:
            return self.history[self.index]
        self.index -= 1
        return path

    def next(self):
        if self.index == len(self.history) - 1:
            return self.history[-1]
        try:
            path = self.history[self.index + 1]
        except IndexError:
            return self.history[self.index]
        self.index += 1
        return path

    def reset(self, path):
        self.history = [path,]
        self.index = 0


class OrderedSet(MutableSet):
    """
    OrderedSet from Python recipe
    http://code.activestate.com/recipes/576694/
    """
    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)


class Execute(object):
    """
    Execute external commands and handle its output.

    Args:

        cmd (:py:class:`str` or :py:class:`list`):
                            command with arguments that should be called.
                            Depending on if this is :py:class:`str` or
                            :py:class:`list` instance the command will be called
                            by either :py:func:`os.system` (deprecated) or
                            :py:class:`subprocess.Popen`
        callback (method):  function which will handle output returned by
                            command (e.g. to extract errors)
        user_data:          extra arguments which will be forwarded to
                            ``callback`` function (e.g. a tuple - which is
                            passed by reference in Python - to "return"
                            results of the callback function as side effect).
        filters (tuple):    Tuple of functions used to filter messages before
                            sending them to the ``callback`` function
        parent (instance):  instance of the calling method used only to proper
                            format log messages
        conv_str (bool):    convert output to :py:class:`str` if True or keep it
                            as :py:class:`bytes` if False
        join_stderr (bool): join stderr to stdout

    Note:
        Signals SIGTSTP ("keyboard stop") and SIGCONT send to Python
        main process will be forwarded to the command.
        SIGHUP will kill the process.
    """
    def __init__(self,
                 cmd,
                 callback = None,
                 user_data = None,
                 filters = (),
                 parent = None,
                 conv_str = True,
                 join_stderr = True):
        self.cmd = cmd
        self.callback = callback
        self.user_data = user_data
        self.filters = filters
        self.currentProc = None
        self.conv_str = conv_str
        self.join_stderr = join_stderr
        # we need to forward parent to have the correct class name in debug log
        if parent:
            self.parent = parent
        else:
            self.parent = self

        if isinstance(self.cmd, list):
            self.pausable = True
            self.printable_cmd = ' '.join(self.cmd)
            logger.debug('Call command "%s"' %self.printable_cmd, self.parent, 2)
        else:
            self.pausable = False
            self.printable_cmd = self.cmd
            logger.warning('Call command with old os.system method "%s"' %self.printable_cmd, self.parent, 2)

    def run(self):
        """
        Start the command.

        Returns:
            int:    return code from the command
        """
        ret_val = 0
        out = ''

        # backwards compatibility with old os.system and os.popen calls
        # TODO Is this still required as the minimal Python version is 3.10++ now?
        # TODO Which Python versions are considered as "old" here?
        if isinstance(self.cmd, str):
            logger.deprecated(self)
            if self.callback is None:
                ret_val = os.system(self.cmd)
            else:
                pipe = os.popen(self.cmd, 'r')

                while True:
                    line = tempFailureRetry(pipe.readline)
                    if not line:
                        break
                    line = line.strip()
                    for f in self.filters:
                        line = f(line)
                    if not line:
                        continue
                    self.callback(line, self.user_data)

                ret_val = pipe.close()
                if ret_val is None:
                    ret_val = 0

        # new and preferred method using subprocess.Popen
        # TODO Which minimal Python version is required to be considered as "new"?
        elif isinstance(self.cmd, (list, tuple)):
            try:
                # register signals for pause, resume and kill
                # Forward these signals (sent to the "backintime" process
                # normally) to the child process ("rsync" normally).
                # Note: SIGSTOP (unblockable stop) cannot be forwarded because
                # it cannot be caught in a signal handler!
                signal.signal(signal.SIGTSTP, self.pause)
                signal.signal(signal.SIGCONT, self.resume)
                signal.signal(signal.SIGHUP, self.kill)
            except ValueError:
                # signal only work in qt main thread
                # TODO What does this imply?
                pass

            if self.join_stderr:
                stderr = subprocess.STDOUT
            else:
                stderr = subprocess.DEVNULL

            logger.debug(f"Starting command '{self.printable_cmd[:min(16, len(self.printable_cmd))]}...'")

            self.currentProc = subprocess.Popen(self.cmd,
                                                stdout = subprocess.PIPE,
                                                stderr = stderr)

            # # TEST code for developers to simulate a killed rsync process
            # if self.printable_cmd.startswith("rsync --recursive"):
            #     self.currentProc.terminate()  # signal 15 (SIGTERM) like "killall" and "kill" do by default
            #     # self.currentProc.send_signal(signal.SIGHUP)  # signal 1
            #     # self.currentProc.kill()  # signal 9
            #     logger.error("rsync killed for testing purposes during development")

            if self.callback:
                for line in self.currentProc.stdout:
                    if self.conv_str:
                        line = line.decode().rstrip('\n')
                    else:
                        line = line.rstrip(b'\n')
                    for f in self.filters:
                        line = f(line)
                    if not line:
                        continue
                    self.callback(line, self.user_data)

            # We use communicate() instead of wait() to avoid a deadlock
            # when stdout=PIPE and/or stderr=PIPE and the child process
            # generates enough output to pipe that it blocks waiting for
            # free buffer. See also:
            # https://docs.python.org/3.10/library/subprocess.html#subprocess.Popen.wait
            out = self.currentProc.communicate()[0]
            # TODO Why is "out" empty instead of containing all stdout?
            #      Most probably because Popen was called with a PIPE as stdout
            #      to directly process each stdout line by calling the callback...

            ret_val = self.currentProc.returncode
            # TODO ret_val is sometimes 0 instead of e.g. 23 for rsync. Why?

            try:
                # reset signal handler to their default
                signal.signal(signal.SIGTSTP, signal.SIG_DFL)
                signal.signal(signal.SIGCONT, signal.SIG_DFL)
                signal.signal(signal.SIGHUP, signal.SIG_DFL)
            except ValueError:
                # signal only work in qt main thread
                # TODO What does this imply?
                pass

        if ret_val != 0:
            msg = 'Command "%s" returns %s%s%s' %(self.printable_cmd, bcolors.WARNING, ret_val, bcolors.ENDC)
            if out:
                msg += ' | %s' %out.decode().strip('\n')
            logger.warning(msg, self.parent, 2)
        else:
            msg = 'Command "%s..." returns %s' %(self.printable_cmd[:min(16, len(self.printable_cmd))], ret_val)
            if out:
                msg += ': %s' %out.decode().strip('\n')
            logger.debug(msg, self.parent, 2)

        return ret_val

    def pause(self, signum, frame):
        """
        Slot which will send ``SIGSTOP`` to the command. Is connected to
        signal ``SIGTSTP``.
        """
        if self.pausable and self.currentProc:
            logger.info('Pause process "%s"' %self.printable_cmd, self.parent, 2)
            return self.currentProc.send_signal(signal.SIGSTOP)

    def resume(self, signum, frame):
        """
        Slot which will send ``SIGCONT`` to the command. Is connected to
        signal ``SIGCONT``.
        """
        if self.pausable and self.currentProc:
            logger.info('Resume process "%s"' %self.printable_cmd, self.parent, 2)
            return self.currentProc.send_signal(signal.SIGCONT)

    def kill(self, signum, frame):
        """
        Slot which will kill the command. Is connected to signal ``SIGHUP``.
        """
        if self.pausable and self.currentProc:
            logger.info('Kill process "%s"' %self.printable_cmd, self.parent, 2)
            return self.currentProc.kill()


class Daemon:
    """
    A generic daemon class.

    Usage: subclass the Daemon class and override the run() method

    Daemon Copyright by Sander Marechal
    License CC BY-SA 3.0
    http://www.jejik.com/articles/2007/02/a_simple_unix_linux_daemon_in_python/
    """
    def __init__(self, pidfile = None, stdin='/dev/null', stdout='/dev/stdout', stderr='/dev/null', umask = 0o022):
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.pidfile = pidfile
        self.umask = umask
        if pidfile:
            self.appInstance = ApplicationInstance(pidfile, autoExit = False, flock = False)

    def daemonize(self):
        """
        "Converts" the current process into a daemon
        (= process running in the background)
        and sends a SIGTERM signal to the current process.
        This is done via the UNIX double-fork magic, see Stevens'
        "Advanced Programming in the UNIX Environment" for details (ISBN 0201563177)
        and this explanation: https://stackoverflow.com/a/6011298
        """
        try:
            pid = os.fork()
            logger.debug('first fork pid: {}'.format(pid), self)
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            logger.error("fork #1 failed: %d (%s)" % (e.errno, str(e)), self)
            sys.exit(1)

        # decouple from parent environment
        logger.debug('decouple from parent environment', self)
        os.chdir("/")
        os.setsid()
        os.umask(self.umask)

        # do second fork
        try:
            pid = os.fork()
            logger.debug('second fork pid: {}'.format(pid), self)
            if pid > 0:
                # exit from second parent
                sys.exit(0)
        except OSError as e:
            logger.error("fork #2 failed: %d (%s)" % (e.errno, str(e)), self)
            sys.exit(1)

        # redirect standard file descriptors
        logger.debug('redirect standard file descriptors', self)

        sys.stdout.flush()
        sys.stderr.flush()
        fdDup(self.stdin, sys.stdin, 'r')
        fdDup(self.stdout, sys.stdout, 'w')
        fdDup(self.stderr, sys.stderr, 'w')

        signal.signal(signal.SIGTERM, self.cleanupHandler)

        if self.pidfile:
            atexit.register(self.appInstance.exitApplication)
            # write pidfile
            logger.debug('write pidfile', self)
            self.appInstance.startApplication()

    def cleanupHandler(self, signum, frame):
        if self.pidfile:
            self.appInstance.exitApplication()
        sys.exit(0)

    def start(self):
        """
        Start the daemon
        """
        # Check for a pidfile to see if the daemon already runs
        if self.pidfile and not self.appInstance.check():
            message = "pidfile %s already exists. Daemon already running?\n"
            logger.error(message % self.pidfile, self)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    def stop(self):
        """
        Stop the daemon
        """
        if not self.pidfile:
            logger.debug("Unattended daemon can't be stopped. No PID file", self)
            return

        # Get the pid from the pidfile
        pid, procname = self.appInstance.readPidFile()

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            logger.error(message % self.pidfile, self)
            return # not an error in a restart

        # Try killing the daemon process
        try:
            while True:
                os.kill(pid, signal.SIGTERM)
                sleep(0.1)
        except OSError as err:
            if err.errno == errno.ESRCH:
                #no such process
                self.appInstance.exitApplication()
            else:
                logger.error(str(err), self)
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
        if not self.pidfile:
            logger.debug("Unattended daemon can't be reloaded. No PID file", self)
            return

        # Get the pid from the pidfile
        pid, procname = self.appInstance.readPidFile()

        if not pid:
            message = "pidfile %s does not exist. Daemon not running?\n"
            logger.error(message % self.pidfile, self)
            return

        # Try killing the daemon process
        try:
            os.kill(pid, signal.SIGHUP)
        except OSError as err:
            if err.errno == errno.ESRCH:
                #no such process
                self.appInstance.exitApplication()
            else:
                sys.stderr.write(str(err))
                sys.exit(1)

    def status(self):
        """
        return status
        """
        if not self.pidfile:
            logger.debug("Unattended daemon can't be checked. No PID file", self)
            return
        return not self.appInstance.check()

    def run(self):
        """
        You should override this method when you subclass Daemon. It will be called after the process has been
        daemonized by start() or restart().
        """
        pass

# def __logKeyringWarning():
#
#     from time import sleep
#     sleep(0.1)
#     # TODO This function may not be thread-safe
#     logger.warning('import keyring failed')
#
#
#
# if is_keyring_available:
#
#     # delay warning to give logger some time to import
#
#     # Jan 4, 2024 aryoda:
#     # This is an assumed work-around for #820 (unhandled exception: NoneType)
#     # but does not seem to fix the problem.
#     # So I have refactored the possible name shadowing of "keyring"
#     # as described in
#     # https://github.com/bit-team/backintime/issues/820#issuecomment-1472971734
#     # and left this code unchanged to wait for user feed-back if it works now.
#     # If the error still occurs I would move the log output call
#     # to the client of this module so that it is certain to assume it is
#     # correctly initialized.
#     # Maybe use backintime.py and app.py for logging...
#     # (don't call tools.keyringSupported() for that because
#     # it produces too much debug logging output whenever it is called
#     # but just query tools.is_keyring_available.
#     from threading import Thread
#     thread = Thread(target=__logKeyringWarning, args=())
#     thread.start()
