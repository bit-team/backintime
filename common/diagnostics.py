# SPDX-FileCopyrightText: © 2022 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2).
# See file LICENSE or go to <https://www.gnu.org/licenses/#GPL>.
"""Provides the ability to collect diagnostic information on Back In Time.

These are version numbers of the dependent tools, environment variables,
paths, operating system and the like. This is used to enhance error reports
and to enrich them with the necessary information as uncomplicated as possible.
"""
import sys
import os
import itertools
from pathlib import Path
import pwd
import platform
import locale
import subprocess
import json
import re
import config
import tools
import version


def collect_minimal_diagnostics():
    """Collect minimal information about backintime and the operating system.

    Returns:
       dict: A nested dictionary.
    """
    return {
        'backintime': {
            'name': config.Config.APP_NAME,
            'version': version.__version__,
            'running-as-root': pwd.getpwuid(os.getuid()) == 'root'
        },
        'host-setup': {
            'OS': _get_os_release()
        }
    }


def collect_diagnostics():
    """Collect information about environment, versions of tools and
    packages used by Back In Time.

    The information can be used e.g. for debugging and bug reports.

    Returns:
       dict: A nested dictionary.
    """
    result = collect_minimal_diagnostics()

    # === BACK IN TIME ===

    # work-around: Instantiate to get the user-callback folder
    # (should be singleton)
    cfg = config.Config()

    result['backintime'].update({
        'latest-config-version': config.Config.CONFIG_VERSION,
        'local-config-file': cfg._LOCAL_CONFIG_PATH,
        'local-config-file-found': Path(cfg._LOCAL_CONFIG_PATH).exists(),
        'global-config-file': cfg._GLOBAL_CONFIG_PATH,
        'global-config-file-found': Path(cfg._GLOBAL_CONFIG_PATH).exists(),
        # 'distribution-package': str(distro_path),
        'started-from': str(Path(config.__file__).parent),
        'user-callback': cfg.takeSnapshotUserCallback(),
        'keyring-supported': tools.keyringSupported()
    })

    # Git repo
    bit_root_path = Path(tools.backintimePath(""))
    git_info = tools.get_git_repository_info(bit_root_path)

    if git_info:

        result['backintime']['git-project-root'] = str(bit_root_path)

        for key in git_info:
            result['backintime'][f'git-{key}'] = git_info[key]

    # == HOST setup ===
    result['host-setup'].update({
        # Kernel & Architecture
        'platform': platform.platform(),
        # OS Version (and maybe name)
        'system': f'{platform.system()} {platform.version()}'
    })

    # Display system (X11 or Wayland)
    # This doesn't catch all edge cases.
    # For more details see: https://unix.stackexchange.com/q/202891/136851
    result['host-setup']['display-system'] = os.environ.get(
        'XDG_SESSION_TYPE', '($XDG_SESSION_TYPE not set)')

    # locale (system language etc)
    #
    # Implementation note: With env var "LC_ALL=C" getlocale() will return
    # (None, None).
    # This throws an error in "join()":
    #   TypeError: sequence item 0: expected str instance, NoneType found
    my_locale = locale.getlocale()
    if all(x is None for x in my_locale):
        my_locale = ["(Unknown)"]
    result['host-setup']['locale'] = ', '.join(my_locale)

    # PATH environment variable
    result['host-setup']['PATH'] = os.environ.get('PATH', '($PATH unknown)')

    # RSYNC environment variables
    for var in ['RSYNC_OLD_ARGS', 'RSYNC_PROTECT_ARGS']:
        result['host-setup'][var] = os.environ.get(var, '(not set)')

    # === PYTHON setup ===
    python = ' '.join((
        platform.python_version(),
        ' '.join(platform.python_build()),
        platform.python_implementation(),
        platform.python_compiler()
    ))

    # Python branch and revision if available
    branch = platform.python_branch()
    if branch:
        python = f'{python} branch: {branch}'

    rev = platform.python_revision()
    if rev:
        python = f'{python} rev: {rev}'

    python_executable = Path(sys.executable)

    # Python interpreter
    result['python-setup'] = {
        'python': python,
        'python-executable': str(python_executable),
        'python-executable-symlink': python_executable.is_symlink(),
    }

    # Real interpreter path if it is used via a symlink
    if result['python-setup']['python-executable-symlink']:
        result['python-setup']['python-executable-resolved'] \
            = str(python_executable.resolve())

    result['python-setup']['sys.path'] = sys.path

    result['python-setup']['qt'] = _get_qt_information()

    # === EXTERN TOOL ===
    result['external-programs'] = {}

    # rsync
    # rsync >= 3.2.7: -VV return a json
    # rsync <= 3.2.6 and > (somewhere near) 3.1.3: -VV return the same as -V
    # rsync <= (somewhere near) 3.1.3: -VV doesn't exists
    # rsync == 3.1.3 (Ubuntu 20 LTS) doesn't even know '-V'

    # This works when rsync understands -VV and returns json or human readable
    result['external-programs']['rsync'] = _get_extern_versions(
        ['rsync', '-VV'],
        r'rsync  version (.*)  protocol version',
        try_json=True,
        error_pattern=r'unknown option'
    )

    # When -VV was unknown use -V and parse the human readable output
    if not result['external-programs']['rsync']:
        # try the old way
        result['external-programs']['rsync'] = _get_extern_versions(
            ['rsync', '--version'],
            r'rsync  version (.*)  protocol version'
        )
    elif isinstance(result['external-programs']['rsync'], dict):
        # Rsync (>= 3.2.7)provided its information in JSON format.
        # Remove some irrelevant information.
        for key in ['program', 'copyright', 'url', 'license', 'caveat']:
            try:
                del result['external-programs']['rsync'][key]
            except KeyError:
                pass

    # ssh
    result['external-programs']['ssh'] = _get_extern_versions(['ssh', '-V'])

    # sshfs
    result['external-programs']['sshfs'] \
        = _get_extern_versions(['sshfs', '-V'], r'SSHFS version (.*)\n')

    # EncFS
    # Using "[Vv]" in the pattern because encfs does translate its output.
    # e.g. In German it is "Version" in English "version".
    result['external-programs']['encfs'] \
        = _get_extern_versions(['encfs'], r'Build: encfs [Vv]ersion (.*)\n')

    # Shell
    SHELL_ERR_MSG = '($SHELL not exists)'
    shell = os.environ.get('SHELL', SHELL_ERR_MSG)
    result['external-programs']['shell'] = shell

    if shell != SHELL_ERR_MSG:
        shell_version = _get_extern_versions([shell, '--version'])
        result['external-programs']['shell-version'] \
            = shell_version.split('\n')[0]

    result = _replace_username_paths(
        result=result,
        username=pwd.getpwuid(os.getuid()).pw_name
    )

    return result


def _get_qt_information():
    """Collect Version and Theme information from Qt.

    If environment variable ``DISPLAY`` is set a temporary QApplication
    instances is created.
    """
    # pylint: disable=import-outside-toplevel
    try:
        import PyQt6.QtCore
        import PyQt6.QtGui
        import PyQt6.QtWidgets
    except ImportError:
        return '(Cannot import PyQt6)'

    # Themes
    theme_info = {}

    if tools.checkXServer():  # TODO use tools.is_Qt_working() when stable
        qapp = PyQt6.QtWidgets.QApplication([])
        theme_info = {
            'Theme': PyQt6.QtGui.QIcon.themeName(),
            'Theme Search Paths': PyQt6.QtGui.QIcon.themeSearchPaths(),
            'Fallback Theme': PyQt6.QtGui.QIcon.fallbackThemeName(),
            'Fallback Search Paths': PyQt6.QtGui.QIcon.fallbackSearchPaths()
        }
        qapp.quit()

    return {
        'Version': f'PyQt {PyQt6.QtCore.PYQT_VERSION_STR} '
                   f'/ Qt {PyQt6.QtCore.QT_VERSION_STR}',
        **theme_info
    }


def _get_extern_versions(cmd,
                         pattern=None,
                         try_json=False,
                         error_pattern=None):
    """Get the version of an external tools using :class:`subprocess.Popen`.

    Args:
        cmd (list[str]): Commandline arguments that will be passed
            to ``Popen()``.
        pattern (str) : A regex pattern to extract the version string from the
            commands output.
        try_json (bool): Interpret the output as json first
            (default: ``False``).
            If it could be parsed the result is a dict
        error_pattern (str): Regex pattern to identify a message in the output
            that indicates an error.

    Returns:
        Version information as :obj:`str` or :obj:`dict`.
        The latter is used if the
        ``cmd`` requested offer its information in JSON format.
        ``None`` if the error_pattern did match (to indicate an error).
    """

    try:
        # as context manager to prevent ResourceWarning's
        with subprocess.Popen(cmd,
                              env={'LC_ALL': 'C'},
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True) as proc:
            error_output = proc.stderr.read()
            std_output = proc.stdout.read()

    except FileNotFoundError:
        result = f'(no {cmd[0]})'

    else:
        # Check for errors
        if error_pattern:
            match_result = re.findall(error_pattern, error_output)

            if match_result:
                return None

        # some tools use "stderr" for version info
        result = std_output if std_output else error_output

        # Expect JSON string
        if try_json:

            try:
                result = json.loads(result)

            except json.decoder.JSONDecodeError:
                # Wasn't a json. Try regex in the next block.
                pass

            else:
                return result  # as JSON

        # extract version string
        if pattern:
            result = re.findall(pattern, result)[0]

    return result.strip()  # as string


def _get_os_release():
    """Try to get the name and version of the operating system used.

    First it extract infos from the file ``/etc/os-release``. Because not all
    GNU Linux distributions follow the standards it will also look for
    alternative release files (pattern: ``/etc/*release``).
    See http://linuxmafia.com/faq/Admin/release-files.html for examples.

    Returns:
        A string with the name of the operating system, e.g. "Debian
        GNU/Linux 11 (bullseye)" or a dictionary if alternative release
        files where found.
    """

    def _get_pretty_name_or_content(fp):
        """Return value of PRETTY_NAME from a release file or return the whole
        file content."""

        # Read content from file
        try:
            with fp.open('r') as handle:
                content = handle.read()

        except FileNotFoundError:
            return f'({fp.name} file not found)'

        # Try to extract the pretty name
        try:
            return re.findall('PRETTY_NAME=\"(.*)\"', content)[0]

        except IndexError:
            # Return full content when no PRETTY_NAME was found
            return content

    etc_path = Path('/etc')
    os_files = list(filter(lambda p: p.is_file(),
                           itertools.chain(
                               etc_path.glob('*release*'),
                               etc_path.glob('*version*'))
                           ))

    # "os-release" is standard and should be on top of the list
    fp_osrelease = etc_path / 'os-release'
    try:
        os_files.remove(fp_osrelease)
    except ValueError:
        pass
    else:
        os_files = [fp_osrelease] + os_files

    # each release/version file found
    osrelease = {str(fp): _get_pretty_name_or_content(fp) for fp in os_files}

    # No alternative release files found
    if len(osrelease) == 1:
        return osrelease[str(fp_osrelease)]

    return osrelease


def _replace_username_paths(result, username):
    """User's real ``HOME`` path and login name are replaced with surrogtes.

    This is because of security reasons.

    Args:
        result (dict): Dict possibly containing the username and its home
            path.
        username (str): The user's real login name to look for.

    Returns:
        A dictionary with replacements.
    """

    # Replace home folder user names with this dummy name
    # for privacy reasons
    USER_REPLACED = 'UsernameReplaced'

    # JSON to string
    result = json.dumps(result)

    result = result.replace(f'/home/{username}', f'/home/{USER_REPLACED}')
    result = result.replace(f'~/{username}', f'~/{USER_REPLACED}')

    # string to JSON
    return json.loads(result)
