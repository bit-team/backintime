#!/usr/bin/env python3
import sys
import io
import datetime
import pprint
from pathlib import Path
from subprocess import run, check_output

"""This helper script do manage transferring translations to and from the
translation platform (currently Weblate).
"""

# In usual GNU gettext environments it would be "locale" (sometimes plurarl
# "locales")
LOCAL_DIR = Path('common') / 'po'
TEMPLATE_PO = LOCAL_DIR / 'messages.pot'
LANGUAGE_NAMES_PY = Path('common') / 'languages.py'
WEBLATE_URL = 'https://translate.codeberg.org/git/backintime/common'
PACKAGE_NAME = 'Back In Time'
PACKAGE_VERSION = Path('VERSION').read_text().strip()
BUG_ADDRESS = 'https://github.com/bit-team/backintime'
MSGID_COMPLETENESS = '__TRANSLATION_COMPLETENESS__'

def update_po_template():
    """The po template file is update via `xgettext`.

    All files with extension `*.py` are scanned for translatable strings.
    Unittest files and folders are excluded.

    xgettext is used instead of pygettext because the latter is deprecated
    since xgettext is able to handle Python files.
    """

    print(f'Updating PO template file "{TEMPLATE_PO}" …')

    # Recursive search of Python files excluding unittest files and folders
    find_cmd = [
        'find',
        # folders to search in
        'common', 'qt',
        # look for py-files
        '-name', '*.py',
        # exclude files/folders related to unittests
        '-not', '-name', 'test_*',
        '-not', '-path', '*/test/*',
        '-not', '-path', '*/tests/*'
    ]
    print(f'Execute "{find_cmd}".')

    py_files = check_output(find_cmd, text=True).split()

    print('Scan following files for translatable strings:\n{}'
          .format('\n'.join(py_files)))

    cmd = [
        'xgettext',
        '--verbose',
        '--language=Python',
        f'--package-name="{PACKAGE_NAME}"',
        f'--package-version="{PACKAGE_VERSION}"',
        f'--msgid-bugs-address={BUG_ADDRESS}',
        f'--output={TEMPLATE_PO}',
    ]
    cmd.extend(py_files)

    print(f'Execute "{cmd}".')
    run(cmd, check=True)


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
            '--backup=off',  # don't create *.po~ files
            f'{po_path}',
            f'{TEMPLATE_PO}'
        ]

        run(cmd, check=True)


def check_existence():
    """Check for existence of essential files.

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
    """Translations done on Weblate platform are integrated back into the
    repository.

    The Weblate translations live on https://translate.codeberg.org and has
    its own internal git repository. This repository is cloned and the
    po-files copied into the current local (upstream) repository.

    See comments in code about further details.
    """

    import shutil
    import tempfile

    tmp_dir = tempfile.mkdtemp()

    # "Clone" weblate repo into a temporary folder.
    # The folder is kept (nearly) empty. No files are transfered except
    # the hidden ".git" folder.
    cmd = [
        'git',
        'clone',
        '--no-checkout',
        WEBLATE_URL,
        tmp_dir
    ]
    print('Execute "{}".'.format(' '.join(cmd)))
    run(cmd, check=True)

    # Now checkout po-files from that temporary repository but redirect
    # them into the current folder (which is our local upstream repo) instead
    # of the temporary repositories folder.
    cmd = [
        'git',
        # Use temporary/Weblate repo as checkout source
        '--git-dir', f'{tmp_dir}/.git',
        'checkout',
        # branch
        'dev',
        '--',
        'common/po/*.po'
    ]
    print('Execute "{}".'.format(' '.join(cmd)))
    run(cmd, check=True)

    shutil.rmtree(tmp_dir, ignore_errors=True)


def foobar():
    import polib

    new_entry = polib.POEntry(msgid=MSGID_COMPLETENESS, msgstr='16')
    pof.append(new_entry)

    entry = pof.find(st=MSGID_COMPLETENESS, by='msgid')
    if entry:
        pof.remove(entry)


def create_language_names_dict_in_file(language_codes: list) -> str:
    """Create a py-file containing a dict of language names in different
    flavours. The dict is used in the LanguageDialog to display the name of
    each language in the UI's current language and the language's own native
    representation.
    """

    try:
        import babel
    except ImportError:
        raise ImportError('Can not import package "babel". Please install it.')

    # Source language (English) should be included
    if not 'en' in language_codes:
        language_codes.append('en')

    # Don't use defaultdict because pprint can't handle it
    result = {}

    for code in language_codes:
        print(f'Processing language code "{code}"...')

        lang = babel.Locale.parse(code)
        result[code] = {}

        # Native name of the language
        # e.g. 日本語
        result[code]['_native'] = lang.get_display_name(code)

        # Name of the language in all other foreign languages
        # e.g. Japanese, Japanisch, ...
        for c in language_codes:
            result[code][c] = lang.get_display_name(c)

    # Convert dict to python code as a string
    stream = io.StringIO()
    pprint.pprint(result, indent=2, stream=stream, sort_dicts=False)
    stream.seek(0)
    result = stream.read()

    with LANGUAGE_NAMES_PY.open('w', encoding='utf8') as handle:

        handle.write('# Generated at {} with help of package "babel".\n'
                        .format(datetime.datetime.now().strftime('%c') ))
        handle.write('# https://babel.pocoo.org\n')
        handle.write('# https://github.com/python-babel/babel\n')

        handle.write('\nnames = {\n')

        handle.write(result[1:])

    print(f'Result written to {LANGUAGE_NAMES_PY}.')


def update_language_names():
    # Languages code based on the existing po-files
    langs = [po_path.stem for po_path in LOCAL_DIR.rglob('**/*.po')]

    # Some languages missing in the list of language names?
    from common import languages

    try:
        missing_langs = set(langs) - set(languages.names)
    except AttributeError:
        # Under circumstances the languages file is empty
        missing_langs = ['foo']

    if missing_langs:
        print('Create new language name list because of missing '
              f'languages: {missing_langs}')
        create_language_names_dict_in_file(langs)


if __name__ == '__main__':

    check_existence()

    fin_msg = 'Please check the result via "git diff" before commiting.'

    # Scan python source files for translatable strings
    if 'source' in sys.argv:
        update_po_template()
        update_po_language_files()
        print(fin_msg)
        sys.exit()

    # Download translations (as po-files) from Weblate and integrate them
    # into the repository.
    if 'weblate' in sys.argv:
        update_from_weblate()
        update_language_names()
        print(fin_msg)
        sys.exit()

    print('Use one of the following argument keywords:\n'
          '  source  - Update the pot and po files with translatable '
          'strings extracted from py files. (Prepare upload to Weblate)\n'
          '  weblate - Update the po files with translations from '
          'external translation service Weblate. (Download from Weblate)')

    sys.exit(1)
