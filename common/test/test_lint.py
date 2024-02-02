import unittest
import pathlib
import subprocess
from typing import Iterable


class MirrorMirrorOnTheWall(unittest.TestCase):
    """Check all py-files in the package (incl. test files) for lints and
    potential bugs and if they are compliant to the coding styles (e.g. PEP8).
    """

    def _collect_py_files(self) -> Iterable[pathlib.Path]:
        """All py-files related to that distribution package.

        Dev note (2023-11): Use package metadata after migration to
        pyproject.toml.
        """
        path = pathlib.Path.cwd()

        # Make sure we are inside the test folder
        if path.name in ['qt', 'common']:  # happens e.g. on TravisCI
            path = path / 'test'

        if not path.name.startswith('test'):
            raise RuntimeError('Something went wrong. The test should run '
                               'inside the test folder but current folder '
                               f'is {path}.')

        # Workaround
        path = path.parent

        # Find recursive all py-files.
        return path.rglob('**/*.py')

    def test_with_pylint(self):
        """Use Pylint to check for specific error codes.

        Some facts about PyLint
         - It is one of the slowest available linters.
         - It is able to catch lints none of the other linters
        """

        # Pylint base command
        cmd = [
            'pylint',
            # Storing results in a pickle file is unnecessary
            '--persistent=n',
            # autodetec number of parallel jobs
            '--jobs=0',
            # Disable scoring  ("Your code has been rated at xx/10")
            '--score=n',
            # Deactivate all checks by default
            '--disable=all',
            # prevent false-positive no-module-member errors
            '--extension-pkg-whitelist=PyQt5',
            # Because of globally installed GNU gettext functions
            '--additional-builtins=_,ngettext',
            # PEP8 conform line length (see PyLint Issue #3078)
            '--max-line-length=79',
            # Whitelist variable names
            '--good-names=idx,fp',
        ]

        # Explicit activate checks
        err_codes = [
            'E0602',  # undefined-variable
            'E1101',  # no-member
            'W1401',  # anomalous-backslash-in-string (invalid escape sequence)
        ]
        cmd.append('--enable=' + ','.join(err_codes))

        # Add py files
        cmd.extend(self._collect_py_files())

        # print(f'Execute {cmd=}')

        subprocess.run(cmd, check=True)
