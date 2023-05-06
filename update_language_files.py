#!/usr/bin/env python3
import sys
from pathlib import Path
from subprocess import run

# In usual GNU gettext environments it would be "locale" (sometimes plurarl
# "locales")
LOCAL_DIR = Path('common') / 'po'
TEMPLATE_PO = LOCAL_DIR / 'messages.pot'
WEBLATE_URL = 'https://translate.codeberg.org/git/backintime/common'
PACKAGE_NAME = 'Back In Time'
PACKAGE_VERSION = Path('VERSION').read_text().strip()
BUG_ADDRESS = 'https://github.com/bit-team/backintime'


# def collect_py_files() -> list[Path]:
#     """Collecting all py-files to be used for extracting translatable strings.

#     This is done here and not with shell wildcards because `xgettext` is not
#     very verbose about which files it do scan. Having that list of files
#     explicit gives more control about verbosity.
#     """

#     def func_exclude_tests(val: Path) -> bool:
#         """Filter to exclude file paths related to unittests."""

#         # Unittest folder
#         if 'test' in val.parts or 'tests' in val.parts:
#             return False

#         # Unittest file
#         if val.stem.startswith('test_'):
#             return False

#         return True

#     result = []
#     for path in [Path('common'), Path('qt')]:
#         result.extend(list(
#             filter(func_exclude_tests, path.glob('**/*.py'))
#         ))

#     return result


def update_po_template():
    """The po template file is update via `xgettext`.

    All files with extension `*.py` are scanned for translateable strings.
    Unittest files and folders are excluded.

    xgettext is used instead of pygettext because the latter is deprecated
    since xgettext is able to handle Python files.
    """

    print(f'Updating PO template file "{TEMPLATE_PO}" ...')

    # Recursive search of Python files excluding unittest files and folders
    find_base = "`find {} -name '*.py' " \
        "-not -name 'test_*' -not -path '*/test/*' -not -path '*/tests/*'`"

    find_common_py = find_base.format('common')
    find_qt_py = find_base.format('qt')

    print('Scanning following files for translatable strings:')
    run(f'ls -1 {find_common_py}', shell=True)
    run(f'ls -1 {find_qt_py}', shell=True)

    cmd = [
        'xgettext',
        '--verbose',
        '--language=Python',
        f'--package-name="{PACKAGE_NAME}"',
        f'--package-version="{PACKAGE_VERSION}"',
        f'--msgid-bugs-address={BUG_ADDRESS}',
        f'--output={TEMPLATE_PO}',
        find_common_py,
        find_qt_py
    ]

    # Because we use shell=True
    cmd = ' '.join(cmd)

    print(f'Execute "{cmd}"')
    run(cmd, shell=True)


def update_po_language_files():
    """
    """

    # Recursive all po-files
    for po_path in LOCAL_DIR.rglob('**/*.po'):

        lang = po_path.stem

        cmd = [
            'msgmerge',
            '--verbose',
            f'--lang={lang}',
            '--update',
            f'{po_path}',
            f'{TEMPLATE_PO}'
        ]

        run(cmd)


def check_existance():
    """Check for existance of essential files.

    Returns:
        Nothing if everything is fine.

    Raises:
        FileNotFoundError
    """
    paths_to_check = [
        LOCAL_DIR,
        TEMPLATE_PO
    ]

    for fp in paths_to_check:
        if not fp.exists():
            raise FileNotFoundError(fp)


def update_from_weblate():
    """
        git clone --no-checkout https://translate.codeberg.org/git/backintime/common
        cd common
        git checkout dev -- common/po/*.po


    """
    import shutil
    import tempfile

    tmp_dir = tempfile.mkdtemp()

    # Clone weblate repo (but empty)
    cmd = [
        'git',
        'clone',
        '--no-checkout',
        WEBLATE_URL,
        tmp_dir
    ]
    print('Execute "{}".'.format(' '.join(cmd)))
    run(cmd)

    # Checkout po files directly into our target repo
    cmd = [
        'git',
        '--git-dir', f'{tmp_dir}/.git',
        #'--work-tree', '.',
        'checkout',
        'dev',  # branch
        '--',
        'common/po/*.po'
    ]
    print('Execute "{}".'.format(' '.join(cmd)))
    run(cmd)

    shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':

    check_existance()

    if 'source' in sys.argv:
        # py_files = collect_py_files()
        update_po_template()
        sys.exit()
        update_po_language_files()
        print('Please check the result via "git diff".')
        sys.exit()

    if 'weblate' in sys.argv:
        update_from_weblate()
        print('Please check the result via "git diff".')
        sys.exit()

    print('Use one of the following argument keywords:\n'
            '  source  - Update the pot and po files with translatable '
            'strings extracted from py files.\n'
            '  weblate - Update the po files with translations from '
            'external translation service Weblate.')

    sys.exit(1)
