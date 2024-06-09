import unittest
import os
import pathlib
import subprocess
import shutil
from typing import Iterable

ON_TRAVIS = os.environ.get('TRAVIS', '') == 'true'
PYLINT_AVIALBE = not shutil.which('pylint') is None
PYLINT_REASON = ('Using PyLint is mandatory on TravisCI, on other systems'
                 'it runs only if `pylint` is available.')


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

    @unittest.skipUnless(ON_TRAVIS or PYLINT_AVIALBE, PYLINT_REASON)
    def test_with_pylint(self):
        """Use Pylint to check for specific error codes.

        Some facts about PyLint
         - It is one of the slowest available linters.
         - It is able to catch lints none of the other linters
        """

        # Pylint base command
        cmd = [
            'pylint',
            # Make sure BIT modules can be imported (to detect "no-member")
            '--init-hook=import sys;'
            'sys.path.insert(0, "./../qt");'
            'sys.path.insert(0, "./../common");',
            # Storing results in a pickle file is unnecessary
            '--persistent=n',
            # autodetec number of parallel jobs
            '--jobs=0',
            # Disable scoring  ("Your code has been rated at xx/10")
            '--score=n',
            # Deactivate all checks by default
            '--disable=all',
            # prevent false-positive no-module-member errors
            '--extension-pkg-allow-list=PyQt6,PyQt6.QtCore',
            # Because of globally installed GNU gettext functions
            '--additional-builtins=_,ngettext',
            # PEP8 conform line length (see PyLint Issue #3078)
            '--max-line-length=79',
            # Whitelist variable names
            '--good-names=idx,fp',
            # '--reports=yes',
        ]

        # Explicit activate checks
        err_codes = [
            'E0100',  # init-is-generator
            'E0101',  # return-in-init
            'E0102',  # function-redefined
            'E0103',  # not-in-loop
            'E0106',  # return-arg-in-generator
            'E0401',  # import-error
            'E0602',  # undefined-variable
            'E1101',  # no-member
            'I0021',  # useless-suppression
            # 'W0611',  # unused-import
            'W1301',  # unused-format-string-key
            'W1401',  # anomalous-backslash-in-string (invalid escape sequence)

            # Enable asap. This list is selection of existing (not all!)
            # problems currently exiting in the BIT code base. Quit easy to fix
            # because there count is low.
            # 'C0303',  # trailing-whitespace
            # 'C0305',  # trailing-newlines
            # 'C0324',  # superfluous-parens
            # 'C0410',  # multiple-imports
            # 'E0213',  # no-self-argument
            # 'R0201',  # no-self-use
            # 'R0202',  # no-classmethod-decorator
            # 'R0203',  # no-staticmethod-decorator
            # 'R0801',  # duplicate-code
            # 'W0123',  # eval-used
            # 'W0237',  # arguments-renamed
            # 'W0221',  # arguments-differ
            # 'W0311',  # bad-indentation
            # 'W0404',  # reimported
            # 'W4902',  # deprecated-method
            # 'W4904',  # deprecated-class
            # 'W0603',  # global-statement
            # 'W0614',  # unused-wildcard-import
            # 'W0612',  # unused-variable
            # 'W0707',  # raise-missing-from
        ]

        cmd.append('--enable=' + ','.join(err_codes))

        # Add py files
        cmd.extend(self._collect_py_files())

        r = subprocess.run(
            cmd,
            check=False,
            universal_newlines=True,
            capture_output=True)

        # Count lines except module headings
        error_n = len(list(filter(lambda line: not line.startswith('*****'),
                                  r.stdout.splitlines())))
        print(r.stdout)

        self.assertEqual(0, error_n, f'PyLint found {error_n} problems.')

        # any other errors?
        self.assertEqual(r.stderr, '')
