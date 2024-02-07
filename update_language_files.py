#!/usr/bin/env python3
"""This helper script does manage transferring translations to and from the
translation platform (currently Weblate).
"""
import sys
import io
import datetime
import json
import re
import tempfile
import shutil
import pprint
from pathlib import Path
from subprocess import run, check_output
from common import languages

try:
    import polib
    print(f'polib version: {polib.__version__}')
except ImportError:
    # pylint: disable-next=raise-missing-from
    raise ImportError('Can not import package "polib". Please install it.')

# In usual GNU gettext environments it would be "locale" (sometimes plurarl
# "locales")
LOCAL_DIR = Path('common') / 'po'
TEMPLATE_PO = LOCAL_DIR / 'messages.pot'
LANGUAGE_NAMES_PY = Path('common') / 'languages.py'
WEBLATE_URL = 'https://translate.codeberg.org/git/backintime/common'
PACKAGE_NAME = 'Back In Time'
PACKAGE_VERSION = Path('VERSION').read_text('utf-8').strip()
BUG_ADDRESS = 'https://github.com/bit-team/backintime'
# RegEx pattern: Character & followed by a word character (extract as group)
REX_SHORTCUT_LETTER = re.compile(r'&(\w)')


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
        '--sort-by-file',
        # '--sort-output',
    ]
    cmd.extend(py_files)

    print(f'Execute "{cmd}".')
    run(cmd, check=True)


def update_po_language_files():
    """The po files are updated with the source strings from the pot-file (the
    template for each po-file).

    The GNU gettext utility ``msgmerge`` is used for that.

    The function `update_po_template()` should be called before.
    """

    # Recursive all po-files
    for po_path in LOCAL_DIR.rglob('**/*.po'):

        lang = po_path.stem

        cmd = [
            'msgmerge',
            '--verbose',
            f'--lang={lang}',
            '--update',
            '--sort-by-file',
            '--backup=off',  # don't create *.po~ files
            f'{po_path}',
            f'{TEMPLATE_PO}'
        ]
        run(cmd, check=True)

        # remove obsolete entries ("#~ msgid)
        cmd = [
            'msgattrib',
            '--no-obsolete',
            f'--output-file={po_path}',
            f'{po_path}'
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

    for file_path in paths_to_check:
        if not file_path.exists():
            raise FileNotFoundError(file_path)


def update_from_weblate():
    """Translations done on Weblate platform are integrated back into the
    repository.

    The Weblate translations live on https://translate.codeberg.org and has
    its own internal git repository. This repository is cloned and the
    po-files copied into the current local (upstream) repository.

    See comments in code about further details.
    """

    tmp_dir = tempfile.mkdtemp()

    # "Clone" weblate repo into a temporary folder.
    # The folder is kept (nearly) empty. No files are transferred except
    # the hidden ".git" folder.
    cmd = [
        'git',
        'clone',
        '--no-checkout',
        WEBLATE_URL,
        tmp_dir
    ]
    print(f'Execute "{cmd}".')
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
    print(f'Execute "{cmd}".')
    run(cmd, check=True)

    shutil.rmtree(tmp_dir, ignore_errors=True)


def create_completeness_dict():
    """Create a simple dictionary indexed by language code and value that
    indicate the completeness of the translation in percent.
    """

    print('Calculate completeness for each language in percent...')

    result = {}

    # each po file in the repository
    for po_path in LOCAL_DIR.rglob('**/*.po'):
        pof = polib.pofile(po_path)

        result[po_path.stem] = pof.percent_translated()

        pof.save()

    # "en" is the source language
    result['en'] = 100

    # info
    print(json.dumps(result, indent=4))

    return result


def create_languages_file():
    """Create the languages.py file containing language names and the
    completeness of their translation.

    See the following functions for further details.
    - ``update_language_names()``
    - ``create_completeness_dict()``
    """

    # Convert language names dict to python code as a string
    names = update_language_names()
    stream = io.StringIO()
    pprint.pprint(names, indent=2, stream=stream, sort_dicts=True)
    stream.seek(0)
    names = stream.read()

    # the same with completeness dict
    compl_dict = create_completeness_dict()
    stream = io.StringIO()
    pprint.pprint(compl_dict, indent=2, stream=stream, sort_dicts=True)
    stream.seek(0)
    completeness = stream.read()

    with LANGUAGE_NAMES_PY.open('w', encoding='utf8') as handle:

        date_now = datetime.datetime.now().strftime('%c')
        handle.write(
            f'# Generated at {date_now} with help of package "babel" '
            'and "polib".\n')
        handle.write('# https://babel.pocoo.org\n')
        handle.write('# https://github.com/python-babel/babel\n')

        handle.write('\nnames = {\n')
        handle.write(names[1:])

        handle.write('\n')

        handle.write('\ncompleteness = {\n')
        handle.write(completeness[1:])

    print(f'Result written to {LANGUAGE_NAMES_PY}.')

    # Completeness statistics (English is excluded)
    compl = list(compl_dict.values())
    compl.remove(100)  # exclude English
    statistic = {
        'compl': round(sum(compl) / len(compl)),
        'n': len(compl),
        '99_100': len(list(filter(lambda val: val >= 99, compl))),
        '90_98': len(list(filter(lambda val: 90 <= val < 99, compl))),
        '50_89': len(list(filter(lambda val: 50 <= val <= 89, compl))),
        'lt50': len(list(filter(lambda val: val < 50, compl)))
    }

    print('STATISTICS')
    print(f'\tTotal completeness: {statistic["compl"]}%')
    print(f'\tNumber of languages (excl. English): {statistic["n"]}')
    print(f'\t100-99% complete: {statistic["99_100"]} languages')
    print(f'\t90-98% complete: {statistic["90_98"]} languages')
    print(f'\t50-89% complete: {statistic["50_89"]} languages')
    print(f'\tless than 50% complete: {statistic["lt50"]} languages')


def create_language_names_dict(language_codes: list) -> dict:
    """Create dict of language names in different flavors.
    The dict is used in the LanguageDialog to display the name of
    each language in the UI's current language and the language's own native
    representation.
    """

    # We keep this import local because it is a rare case that this function
    # will be called. This happens only if a new language is added to BIT.
    try:
        # pylint: disable-next=import-outside-toplevel
        import babel
    except ImportError as exc:
        raise ImportError(
            'Can not import package "babel". Please install it.') from exc

    # Source language (English) should be included
    if 'en' not in language_codes:
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
        for foreign in language_codes:
            result[code][foreign] = lang.get_display_name(foreign)

    return result


def update_language_names() -> dict:
    """See `create_language_names_dict() for details."""

    # Languages code based on the existing po-files
    langs = [po_path.stem for po_path in LOCAL_DIR.rglob('**/*.po')]

    # Some languages missing in the list of language names?
    try:
        missing_langs = set(langs) - set(languages.names)
    except AttributeError:
        # Under circumstances the languages file is empty
        missing_langs = ['foo']

    if missing_langs:
        print('Create new language name list because of missing '
              f'languages: {missing_langs}')

        return create_language_names_dict(langs)

    return languages.names


def get_shortcut_entries(po_file: polib.POFile) -> list[polib.POEntry]:
    """Return list of po-file entries using a shortcut indicator ("&")
    and are not obsolete.
    """
    result = filter(lambda entry: entry.obsolete == 0 and
                    REX_SHORTCUT_LETTER.search(entry.msgid), po_file)

    return list(result)


def get_shortcut_groups() -> dict[str, list]:
    """Return the currently used "shortcut groups" and validate if they are
    up to date with the source strings in "messages.pot".

    Returns:
        A dictionarie indexed by group names with list of source strings.

    Raises:
        ValueError: If the shortcut indicator using source strings are
            modified.
    """

    # Get all entries using a shortcut indicator
    real = get_shortcut_entries(polib.pofile(TEMPLATE_PO))
    # Reduce to their source strings
    real = [entry.msgid for entry in real]

    # Later this list is sliced into multiple groups
    expect = [
        # Main window (menu bar)
        '&Backup',
        '&Restore',
        '&Help',
        # Manage profiles dialog (tabs)
        '&General',
        '&Include',
        '&Exclude',
        '&Auto-remove',
        '&Options',
        'E&xpert Options',
    ]

    # Plausibility check:
    # Difference between the real and expected strings indicate
    # modifications in the GUI and in the shortcut groups.
    if not sorted(real) == sorted(expect):
        # This will happen when the source strings are somehow modified or
        # some strings add or removed.
        # SOLUTION: Look again into the GUI and its commit history what was
        # modified. Update the "expect" list to it.
        raise ValueError(
            f'Source strings with GUI shortcuts in {TEMPLATE_PO} are not as '
            'expected.\n'
            f'  Expected: {sorted(expect)}\n'
            f'      Real: {sorted(real)}')

    # WORKAROUND
    # This source string is not a translateble string but has a shortcut
    # letter.
    # Dev note: From point of view of the translators it might make sense
    # making that string translatable also. But then we risk that our projects
    # name is translated for real.
    expect = ['Back In &Time'] + expect

    return {'mainwindow': expect[:4], 'manageprofile': expect[4:]}


def check_shortcuts():
    """Check for redundant used letters as shortcut indicators in translated
    GUI strings.

    Keyboard shortcuts are indicated via the & in front of a character
    in a GUI string (e.g. a button or tab). For example "B&ackup" can be
    activated with pressing ALT+A. As another example the strings '&Exclude'
    and '&Export' used in the same area of the GUI won't work because both of
    them indicate the 'E' as a shortcut. They need to be unique.

    These situation can happen in translated strings in most cases translators
    are not aware of that feature or problem. It is nearly impossible to
    control this on the level of the translation platform.
    """

    groups = get_shortcut_groups()

    # each po file in the repository
    for po_path in list(LOCAL_DIR.rglob('**/*.po')):

        print(f'******* {po_path} *******')

        # Remember shortcut relevant entries.
        real = {key: [] for key in groups}

        # WORKAROUND. See get_shortcut_groups() for details.
        real['mainwindow'].append('Back In &Time')

        # Entries using shortcut indicators
        shortcut_entries = get_shortcut_entries(polib.pofile(po_path))

        # Group the entries to their shortcut groups
        for entry in shortcut_entries:
            for groupname in real:
                if entry.msgid in groups[groupname]:
                    real[groupname].append(entry.msgstr)

        # Each shortcut group...
        for groupname in real:

            # All shortcut letters used in that group
            letters = ''

            # Collect letters
            for trans in real[groupname]:
                try:
                    letters = letters \
                        + REX_SHORTCUT_LETTER.search(trans).groups()[0]
                except AttributeError:
                    pass

            # Redundant shortcuts? set() do remove duplicates
            if len(letters) > len(set(letters)):
                err_msg = f'Maybe redundant shortcuts in "{po_path}".'

                # Missing shortcuts in translated strings?
                if len(letters) < len(real[groupname]):
                    err_msg = err_msg + ' Maybe missing ones.'

                err_msg = f'{err_msg} Please take a look.\n' \
                    f'        Group: {groupname}\n' \
                    f'       Source: {groups[groupname]}\n' \
                    f'  Translation: {real[groupname]}'

                print(err_msg)


if __name__ == '__main__':

    check_existence()

    FIN_MSG = 'Please check the result via "git diff" before committing.'

    # Scan python source files for translatable strings
    if 'source' in sys.argv:
        update_po_template()
        update_po_language_files()
        create_languages_file()
        print(FIN_MSG)
        sys.exit()

    # Download translations (as po-files) from Weblate and integrate them
    # into the repository.
    if 'weblate' in sys.argv:
        update_from_weblate()
        create_languages_file()
        print(FIN_MSG)
        sys.exit()

    # Check for redundant &-shortcuts
    if 'shortcuts' in sys.argv:
        check_shortcuts()
        sys.exit()

    print('Use one of the following argument keywords:\n'
          '  source  - Update the pot and po files with translatable '
          'strings extracted from py files. (Prepare upload to Weblate)\n'
          '  weblate - Update the po files with translations from '
          'external translation service Weblate. (Download from Weblate)\n'
          '  shortcut - Check po files for redundant keyboard shortcuts '
          'using "&"')

    sys.exit(1)
