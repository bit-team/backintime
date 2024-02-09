"""Centralize managment about the version.

That file is a workaround until the project migrated to a Python build-system.
See Issue #1575 for details about that migration.
"""
import tools
# Value of this variable is modified via update_version.sh
__version_base__ = '1.4.4-dev'


def _create_full_version_string():
    return __version_base__


__version__ = _create_full_version_string()
