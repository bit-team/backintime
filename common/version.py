"""Centralize managment about the version.

That file is a workaround until the project migrated to a Python build-system.
See Issue #1575 for details about that migration.
"""
import tools
# Value of this variable is modified via update_version.sh
__version_base__ = '1.4.4-dev'


def __getattr__(attr_name):
    """Attribute getter for this module providing access to on-demand created
    variable
    """

    # Regular version string used by the application.
    if attr_name == '__version__':
        return __version_base

    # Ask module for all other attributes
    return getattr(__name__, attr_name)
