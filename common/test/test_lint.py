import unittest
import pathlib
import subprocess
from importlib import metadata
from typing import Iterable

# PACKAGE_NAME = 'buhtzology'


class MirrorMirrorOnTheWall(unittest.TestCase):
    """Check all py-files in the package incl. its test files if they are
    compliant to the coding styles (e.g. PEP8).
    """

    def _collect_py_files(self) -> Iterable[pathlib.Path]:
        """All py-files related to that distribution package.

        Dev note (2023-11): Use package metadata after migration to
        pyproject.toml.
        """
        return pathlib.Path.cwd().glob('*.py')

    def test_with_pylint(self):
        """Use Pylint to check for specific error codes."""

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

        # Explicite activate checks
        err_codes = [
            'E1101',  # no-member
            'W0613',  # unused-argument
        ]
        cmd.append('--enable=' + ','.join(err_codes))

        for fp in self._collect_py_files():
            print(fp)
            subprocess.run(cmd + [fp], check=True)
