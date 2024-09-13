# SPDX-FileCopyrightText: © 2023 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""Tests using several linters.

See file common/test/test_lint.py for details.
"""
import unittest
import os
import pathlib
import subprocess
import shutil
from typing import Iterable
try:
    import pycodestyle
    PYCODESTYLE_AVAILABLE = True
except ImportError:
    PYCODESTYLE_AVAILABLE = False

BASE_REASON = ('Using package {0} is mandatory on TravisCI, on '
               'other systems it runs only if `{0}` is available.')

ON_TRAVIS = os.environ.get('TRAVIS', '') == 'true'
TRAVIS_REASON = ('Running linter tests is mandatory on TravisCI only. On '
                 'other machines they will run only if linters available.')

PYLINT_AVAILABLE = shutil.which('pylint') is not None
RUFF_AVAILABLE = shutil.which('ruff') is not None

ANY_LINTER_AVAILABLE = any((
    PYLINT_AVAILABLE,
    RUFF_AVAILABLE,
    PYCODESTYLE_AVAILABLE,
))

# Files in this lists will get the full battery of linters and rule sets.
full_test_files = [pathlib.Path(fp) for fp in (
    'aboutdlg.py',
    'combobox.py',
    'encfsmsgbox.py',
    'test/test_lint.py',
)]

# Not all linters do respect PEP8 (e.g. ruff, PyLint)
PEP8_MAX_LINE_LENGTH = 79


def create_pylint_cmd(include_error_codes=None):
    """Create the pylint base command for later use with subprocess.run().

    Args:
        include_error_codes: List of exclusive rules to check for. If empty all
            default rules are checked.
    """

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
        # prevent false-positive no-module-member errors
        '--extension-pkg-allow-list=PyQt6,PyQt6.QtCore',
        # Because of globally installed GNU gettext functions
        '--additional-builtins=_,ngettext',
        # PEP8 conform line length (see PyLint Issue #3078)
        f'--max-line-length={PEP8_MAX_LINE_LENGTH}',
        # Whitelist variable names
        '--good-names=idx,fp',
        # '--reports=yes',
    ]

    if include_error_codes:
        # Deactivate all checks by default
        cmd.append('--disable=all')
        # Inlcude specific codes only
        cmd.append('--enable=' + ','.join(include_error_codes))

    return cmd


@unittest.skipUnless(ON_TRAVIS or ANY_LINTER_AVAILABLE, TRAVIS_REASON)
class MirrorMirrorOnTheWall(unittest.TestCase):
    """Check all py-files in the package (incl. test files) for lints,
    potential bugs and if they are compliant to the coding styles (e.g. PEP8).
    """

    @classmethod
    def _collect_py_files(cls) -> Iterable[pathlib.Path]:
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
                               'inside the test folder but the current folder '
                               f'is {path}.')

        # Workaround
        path = path.parent

        # Find recursive all py-files.
        py_files = path.rglob('*.py')

        # Exclude full test files
        return filter(lambda fp: fp not in full_test_files, py_files)

    @classmethod
    def setUpClass(cls):
        cls.collected_py_files = cls._collect_py_files()

    @unittest.skipUnless(RUFF_AVAILABLE, BASE_REASON.format('ruff'))
    def test010_ruff_default_ruleset(self):
        """Ruff in default mode."""

        # ATTENTIION: Some settings are found in pyproject.toml
        cmd = [
            'ruff',
            'check',
            # Additionally activate subset of PyLint (PL)
            # and PyCodestyle (E, W) rules
            '--extend-select=PL,E,W',
            # Ignore: redefined-loop-name
            '--ignore=PLW2901',
            '--line-length', str(PEP8_MAX_LINE_LENGTH),
            # Because of globally installed GNU gettext functions
            '--config', 'builtins=["_", "ngettext"]',
            # Ruff counting branches different from PyLint.
            # See: <https://www.reddit.com/r/learnpython/comments/
            #      1buojae/comment/kxu0mp3>
            '--config', 'pylint.max-branches=13',
            '--config', 'flake8-quotes.inline-quotes = "single"',
            '--quiet',
        ]

        cmd.extend(full_test_files)

        proc = subprocess.run(
            cmd,
            check=False,
            universal_newlines=True,
            capture_output=True
        )

        # No errors other then linter rules
        self.assertIn(proc.returncode, [0, 1], proc.stderr)

        error_n = len(proc.stdout.splitlines())
        if error_n > 0:
            print(proc.stdout)

        self.assertEqual(0, error_n, f'Ruff found {error_n} problem(s).')

        # any other errors?
        self.assertEqual(proc.stderr, '')

    @unittest.skipUnless(PYCODESTYLE_AVAILABLE,
                         BASE_REASON.format('pycodestyle'))
    def test020_pycodestyle(self):
        """PEP8 conformance via pycodestyle"""

        style = pycodestyle.StyleGuide(quite=True)
        result = style.check_files(full_test_files)

        self.assertEqual(result.total_errors, 0,
                         f'pycodestyle found {result.total_errors} code '
                         'style error(s)/warning(s).')

    @unittest.skipUnless(PYLINT_AVAILABLE, BASE_REASON.format('PyLint'))
    def test030_pylint_default_ruleset(self):
        """Use Pylint with all default rules to check specific files.
        """

        cmd = create_pylint_cmd()

        # Add py-files
        cmd.extend(full_test_files)

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

    @unittest.skipUnless(PYLINT_AVAILABLE, BASE_REASON.format('PyLint'))
    def test050_pylint_exclusive_ruleset(self):
        """Use Pylint to check for specific rules only.

        Some facts about PyLint
         - It is one of the slowest available linters.
         - It is able to catch lints other linters miss.
        """

        # Explicit activate checks
        err_codes = [
            'C0305',  # trailing-newlines
            'C0325',  # superfluous-parens
            'C0410',  # multiple-imports
            'C0303',  # trailing-whitespace
            'E0100',  # init-is-generator
            'E0101',  # return-in-init
            'E0102',  # function-redefined
            'E0103',  # not-in-loop
            'E0106',  # return-arg-in-generator
            'E0213',  # no-self-argument
            'E0401',  # import-error
            'E0602',  # undefined-variable
            'E1101',  # no-member
            'I0021',  # useless-suppression
            'W0311',  # bad-indentation
            'W0611',  # unused-import
            'W1301',  # unused-format-string-key
            'W1401',  # anomalous-backslash-in-string (invalid escape sequence)
            'W1515',  # forgotten-debug-statement

            # Enable asap. This list is selection of existing (not all!)
            # problems currently exiting in the BIT code base. Quit easy to fix
            # because there count is low.
            # 'R0201',  # no-self-use
            # 'R0202',  # no-classmethod-decorator
            # 'R0203',  # no-staticmethod-decorator
            'R0801',  # duplicate-code
            # 'W0123',  # eval-used
            # 'W0237',  # arguments-renamed
            # 'W0221',  # arguments-differ
            # 'W0404',  # reimported
            # 'W4902',  # deprecated-method
            # 'W4904',  # deprecated-class
            # 'W0603',  # global-statement
            # 'W0614',  # unused-wildcard-import
            # 'W0611',  # unused-import
            # 'W0612',  # unused-variable
            # 'W0707',  # raise-missing-from
        ]

        cmd = create_pylint_cmd(err_codes)

        # Add py-files
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
