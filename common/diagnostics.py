"""short doc

long doc

"""
import pathlib
import os
import pwd
import platform
import locale
import subprocess
import json
import re
import config  # config.Config.VERSION  Refactor after src-layout migration


def collect_diagnostics():
    """Collect information's about environment and versions of tools and
    packages used by Back In Time.

    The informatinos can be used e.g. for debugging and but reports.

    Returns:
       dict: A nested dictionary.
    """
    result = {}

    # === BACK IN TIME ===
    distro_path = _determine_distro_package_folder()

    result['backintime'] = {
        'name': config.Config.APP_NAME,
        'version': config.Config.VERSION,
        'config-version': config.Config.CONFIG_VERSION,
        'distribution-package': str(distro_path),
    }

    result['paths'] = {
        'common': str(pathlib.Path(config.__file__).parent),
    }
    # Git repo
    git_info = get_git_repository_info(distro_path)

    if git_info:

        for key in git_info:
            result['backintime'][f'git-{key}'] = git_info[key]

    # Root
    pwd_struct = pwd.getpwuid(os.getuid())
    result['running_as_root'] = pwd_struct.pw_name == 'root'

    # === PYTHON ===
    result['python'] = '{} {} {} {}'.format(
        platform.python_version(),
        ' '.join(platform.python_build()),
        platform.python_implementation(),
        platform.python_compiler()
    )

    # Python branch and revision if available
    branch = platform.python_branch()
    if branch:
        result['python'] = '{} branch: {}'.format(result['python'], branch)
    rev = platform.python_revision()
    if rev:
        result['python'] = '{} rev: {}'.format(result['python'], rev)

    # === SYSTEM / PLATFORM ===

    # Kernel & Architecture
    result['platform'] = platform.platform()

    # OS Version (and maybe name)
    result['system'] = '{} {}'.format(platform.system(), platform.version())

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

    result['os-release'] = osrelease

    # Display system (X11 or Wayland)
    # This doesn't catch all edge cases.
    # For more detials see: https://unix.stackexchange.com/q/202891/136851
    result['display-system'] = os.environ.get(
        'XDG_SESSION_TYPE', '($XDG_SESSION_TYPE not set)')

    # locale (system language etc)
    result['locale'] = ', '.join(locale.getlocale())

    # === PACKAGES ===
    result['dependencies'] = {}

    # Qt
    try:
        import PyQt5.QtCore
    except ImportError:
        qt = '(Can not import PyQt5)'
    else:
        qt = 'PyQt {} / Qt {}'.format(PyQt5.QtCore.PYQT_VERSION_STR,
                                      PyQt5.QtCore.QT_VERSION_STR)
    finally:
        result['dependencies']['qt'] = qt

    # === EXTERN TOOL ===
    result['external'] = {}

    # rsync
    # rsync >= 3.2.6: -VV return a json
    # rsync <= 3.2.5 and > (somewhere near) 3.1.3: -VV return the same as -V
    # rsync <= (somewhere near) 3.1.3: -VV doesn't exists
    # rsync == 3.1.3 (Ubuntu 20 LTS) doesn't even know '-V'

    # This work when rsync understand -VV and return json or human readable
    result['external']['rsync'] = _get_extern_versions(
        ['rsync', '-VV'],
        r'rsync  version (.*)  protocol version',
        try_json=True,
        error_pattern=r'unknown option'
    )

    # When -VV was unknown use -V and parse the human readable output
    if not result['external']['rsync']:
        # try the old way
        result['external']['rsync'] = _get_extern_versions(
            ['rsync', '--version'],
            r'rsync  version (.*)  protocol version'
        )

    # ssh
    result['external']['ssh'] = _get_extern_versions(['ssh', '-V'])

    # sshfs
    result['external']['sshfs'] \
        = _get_extern_versions(['sshfs', '-V'], r'SSHFS version (.*)\n')

    # EncFS
    # Using "[Vv]" in the pattern because encfs does translate its output.
    # e.g. In German it is "Version" in English "version".
    result['external']['encfs'] \
        = _get_extern_versions(['encfs'], r'Build: encfs [Vv]ersion (.*)\n')

    # Shell
    SHELL_ERR_MSG = '($SHELL not exists)'
    shell = os.environ.get('SHELL', SHELL_ERR_MSG)
    result['external']['shell'] = shell

    if shell != SHELL_ERR_MSG:
        shell_version = _get_extern_versions([shell, '--version'])
        result['external']['shell-version'] = shell_version.split('\n')[0]

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
