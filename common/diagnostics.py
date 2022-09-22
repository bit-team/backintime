"""short doc

long doc

"""
import sys
import os
import pathlib
import pwd
import platform
import locale
import subprocess
import json
import re
import config


def collect_diagnostics():
    """Collect information's about environment and versions of tools and
    packages used by Back In Time.

    The informatinos can be used e.g. for debugging and but reports.

    Returns:
       dict: A nested dictionary.
    """
    result = {}

    USER_REPLACED = 'UsernameReplaced'

    pwd_struct = pwd.getpwuid(os.getuid())

    cfg = config.Config.instance()

    # === BACK IN TIME ===
    distro_path = _determine_distro_package_folder()

    result['backintime'] = {
        'name': cfg.APP_NAME,
        'version': cfg.VERSION,
        'config-version': config.Config.CONFIG_VERSION,
        'distribution-package': str(distro_path),
        'started-from': str(pathlib.Path(config.__file__).parent),
        'running_as_root': pwd_struct.pw_name == 'root',
    }

    # get different *PATH variables from config object
    path_names = [
        '_APP_PATH',
        '_DOC_PATH',
        '_LOCAL_DATA_FOLDER',
        '_LOCAL_CONFIG_FOLDER',
        '_LOCAL_MOUNT_ROOT',
        '_MOUNT_ROOT',
    ]

    for pn in path_names:
        result['backintime'][pn] = getattr(cfg, pn)

    # Git repo
    git_info = get_git_repository_info(distro_path)

    if git_info:

        for key in git_info:
            result['backintime'][f'git-{key}'] = git_info[key]

    # == HOST setup ===
    result['host-setup'] = {
        # Kernel & Architecture
        'platform': platform.platform(),
        # OS Version (and maybe name)
        'system': '{} {}'.format(platform.system(), platform.version()),
    }


    # content of /etc/os-release
    try:
        osrelease = platform.freedesktop_os_release()  # since Python 3.10

    except AttributeError:  # refactor: when we drop Python 3.9 support
        # read and parse the os-release file ourself
        fp = pathlib.Path('/etc') / 'os-release'

        try:
            with fp.open('r') as handle:
                osrelease = handle.read()

        except FileNotFoundError:
            osrelease = '(os-release file not found)'

        else:
            osrelease = re.findall('PRETTY_NAME=\"(.*)\"', osrelease)[0]

    result['host-setup']['os-release'] = osrelease

    # Display system (X11 or Wayland)
    # This doesn't catch all edge cases.
    # For more detials see: https://unix.stackexchange.com/q/202891/136851
    result['host-setup']['display-system'] = os.environ.get(
        'XDG_SESSION_TYPE', '($XDG_SESSION_TYPE not set)')

    # locale (system language etc)
    result['host-setup']['locale'] = ', '.join(locale.getlocale())

    # PATH environment variable
    result['host-setup']['PATH'] = os.environ.get('PATH', '($PATH unknown)')

    # === PYTHON setup ===
    python = '{} {} {} {}'.format(
        platform.python_version(),
        ' '.join(platform.python_build()),
        platform.python_implementation(),
        platform.python_compiler()
    )

    # Python branch and revision if available
    branch = platform.python_branch()
    if branch:
        python = '{} branch: {}'.format(python, branch)
    rev = platform.python_revision()
    if rev:
        python = '{} rev: {}'.format(python, rev)

    result['python-setup'] = {
        'python': python,
        'sys.path': sys.path,
    }

    # Qt
    try:
        import PyQt5.QtCore
    except ImportError:
        qt = '(Can not import PyQt5)'
    else:
        qt = 'PyQt {} / Qt {}'.format(PyQt5.QtCore.PYQT_VERSION_STR,
                                      PyQt5.QtCore.QT_VERSION_STR)
    finally:
        result['python-setup']['qt'] = qt

    # === EXTERN TOOL ===
    result['external-programs'] = {}

    # rsync
    # rsync >= 3.2.6: -VV return a json
    # rsync <= 3.2.5 and > (somewhere near) 3.1.3: -VV return the same as -V
    # rsync <= (somewhere near) 3.1.3: -VV doesn't exists
    # rsync == 3.1.3 (Ubuntu 20 LTS) doesn't even know '-V'

    # This work when rsync understand -VV and return json or human readable
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
        result['external-programs']['shell-version'] = shell_version.split('\n')[0]

    result = json.loads(
        json.dumps(result).replace(pwd_struct.pw_name, USER_REPLACED)
    )

    return result


def _get_extern_versions(cmd,
                         pattern=None,
                         try_json=False,
                         error_pattern=None):
    """Get the version of an external tools using ``subprocess.Popen()``.

    Args:
        cmd (list): Commandline arguments that will be passed to `Popen()`.
        pattern (str): A regex pattern to extract the version string from the
                       commands output.
        try_json (bool): Interpet the output as json first (default: False).
        error_pattern (str): Regex pattern to identify a message in the output
                             that indicates an error.

    """

    try:
        # as context manager to prevent ResourceWarning's
        with subprocess.Popen(cmd,
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
            match = re.findall(error_pattern, error_output)

            if match:
                return None

        # some tools use "stderr" for version infos
        if not std_output:
            result = error_output
        else:
            result = std_output

        # Expect JSON string
        if try_json:

            try:
                result = json.loads(result)

            except json.decoder.JSONDecodeError:
                # Wasn't a json. Try regex in the next block.
                pass

            else:
                # No regex parsing because it was json
                pattern = None

        # extract version string
        if pattern:
            result = re.findall(pattern, result)[0]

    return result.strip()


def get_git_repository_info(path=None):
    """Return the current branch and last commit hash.

    Credits: https://stackoverflow.com/a/51224861/4865723

    Args:
        path (pathlib.Path): Path with '.git' folder in (default is
                             current working directory).

    Returns:
        (dict): Dict with keys "branch" and "hash" if it is a git repo,
                otherwise an `None`.
    """

    if not path:
        path = pathlib.Path.cwd()

    git_folder = path / '.git'

    if not git_folder.exists():
        return None

    result = {}

    # branch name
    with (git_folder / 'HEAD').open('r') as handle:
        val = handle.read()

    if val.startswith('ref: '):
        result['branch'] = '/'.join(val.split('/')[2:]).strip()

    else:
        result['branch'] = '(detached HEAD)'
        result['hash'] = val

        return result

    # commit hash
    with (git_folder / 'refs' / 'heads' / result['branch']) \
         .open('r') as handle:
        result['hash'] = handle.read().strip()

    return result


def _determine_distro_package_folder():
    """Return the projects root folder.

    In Python terms it is the "Distribution Package" not the "Modules
    Package".

    Development info: The function become obslet when migrating the project
    to the "src" layout.
    """

    # "current" folder
    path = pathlib.Path(__file__)

    # level of highest folder named "backintime"
    bit_idx = path.parts.index('backintime')

    # cut the path to that folder
    path = pathlib.Path(*(path.parts[:bit_idx+1]))

    return path
