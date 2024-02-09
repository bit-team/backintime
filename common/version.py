"""Centralize managment about the version.

That file is a workaround until the project migrated to a Python build-system.
See Issue #1575 for details about that migration.
"""
import pathlib
import json
import tools
# Value of this variable is modified via update_version.sh
__version_base__ = '1.4.4-dev'


def _create_full_version_string():
    """Create the version string depending on if and how Back In Time is
    installed and running.

    The value from `__version_base__` is used and extended by latest git
    commit hash depending on availability and the situation.
    """

    # Ignore git if this is a stable release
    if not __version_base__[-4:] == '-dev':
        return __version_base__

    # Actually in a git repo?
    git_info = tools.get_git_repository_info(tools.backintimePath(''), 8)

    if not git_info:
        bit_path = pathlib.Path(tools.backintimePath('common'))
        git_json_file = bit_path / 'git-version.json'

        # Git info file available?
        if git_json_file.exists():
            git_info = json.loads(git_json_file.read_text('utf-8'))

    # git info from current repo or info file
    if git_info:
        return f'{__version_base__}.{git_info["hash"][:8]}'

    # maybe a WARNING?
    # ...

    return __version_base__


# Version string regulary used by the application and presented to users.
__version__ = _create_full_version_string()
