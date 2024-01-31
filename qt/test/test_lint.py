import unittest
import pathlib
import subprocess
from importlib import metadata
from typing import Iterable

# PACKAGE_NAME = 'buhtzology'


class MirrorMirrorOnTheWall(unittest.TestCase):
    """Check all py-files in the package (incl. test files) for lints and
    potential bugs and if they are compliant to the coding styles (e.g. PEP8).
    """

    def _collect_py_files(self) -> Iterable[pathlib.Path]:
        """All py-files related to that distribution package.

        Dev note (2023-11): Use package metadata after migration to
        pyproject.toml.
        """
        p = pathlib.Path.cwd()

        # Make sure we are inside the test folder
        if p.name in ['qt', 'common']:  # happens e.g. on TravisCI
            p = p / 'test'

        if not p.name.startswith('test'):
            raise Exception('Something went wrong. The test should run inside'
                            f' the test folder but current folder is {p}.')

        # Workaround
        p = p.parent

        # Find recursive all py-files.
        return p.rglob('**/*.py')

    def test_with_pylint(self):
        """Use Pylint to check for specific error codes.

        Some facts about PyLint
         - It is one of the slowest available linters.
         - It is able to catch lints none of the other linters
        """

        # Pylint base command
        cmd = [
            'pylint',
            # prevent false-positive no-module-member errors
            '--extension-pkg-whitelist=PyQt5',
            # Because of globally installed GNU gettext functions
            '--additional-builtins=_,ngettext',
            # Deactivate all checks by default
            '--disable=all'
        ]

        # Explicit activate checks
        err_codes = [
            'E0602',  # undefined-variable
            'E1101',  # no-member
            'W1401',  # anomalous-backslash-in-string (invalid escape sequence)
        ]
        cmd.append('--enable=' + ','.join(err_codes))

        for fp in self._collect_py_files():
            subprocess.run(cmd + [fp], check=True)
