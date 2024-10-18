#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2023 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In time" which is released under GNU
# General Public License v2 (GPLv2). See file/folder LICENSE or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""This helper script does manage transferring translations to and from the
translation platform (currently Weblate).
"""
import sys
import datetime
import re
import tempfile
import string
import shutil
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


def dict_as_code(a_dict: dict, indent_level: int) -> list[str]:
    """Convert a (nested) Python dict into its PEP8 conform as-in-code
    representation.
    """
    tab = ' ' * 4 * indent_level
    result = []
    for key in a_dict:

        # single quotes?
        quote_key = "'" if isinstance(key, str) else ""
        quote_val  = "'" if isinstance(a_dict[key], str) else ""

        # A nested dict
        if isinstance(a_dict[key], dict):
            result.append(f"{tab}{quote_key}{key}{quote_key}: {{")

            result.extend(
                dict_as_code(a_dict[key], indent_level+1))

            result.append(f"{tab}}},")
            continue

        # Regular key: value pair
        result.append(f"{tab}{quote_key}{key}{quote_key}: "
                      f"{quote_val}{a_dict[key]}{quote_val},")

    return result


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


def update_po_language_files(remove_obsolete_entries: bool = False):
    """The po files are updated with the source strings from the pot-file (the
    template for each po-file).

    The GNU gettext utility ``msgmerge`` is used for that.

    The function `update_po_template()` should be called before.
    """

    print(
        'Update language (po) files'
        + ' and remove obsolete entries' if remove_obsolete_entries else ''
    )

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

        if remove_obsolete_entries:
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


def check_syntax_of_po_files():
    """Check all po files of known syntax violations.
    """

    # Match every character except open/closing curly brackets
    rex_reduce = re.compile(r'[^\{\}]')
    # Match every pair of curly brackets
    rex_curly_pair = re.compile(r'\{\}')
    # Extract placeholder/variable names
    rex_names = re.compile(r'\{(.*?)\}')

    def _curly_brackets_balanced(to_check):
        """Check if curly brackes for variable placeholders are balanced."""
        # Remove all characters that are not curly brackets
        reduced = rex_reduce.sub('', to_check)

        # Remove valid pairs of curly brackets
        invalid = rex_curly_pair.sub('', reduced)

        # Catch nested curly brackest like this
        # "{{{}}}", "{{}}"
        # This is valid Python code and won't cause Exceptions. So errors here
        # might be false negative. But despite rare cases where this might be
        # used it is a high possibility that there is a typo in the translated
        # string. BIT won't use constructs like this in strings, so it is
        # handled as an error.
        if rex_curly_pair.findall(invalid):
            print(f'\nERROR: Curly brackets nested: {to_check}')
            return False

        if invalid:
            print(f'\nERROR: Curly brackets not balanced : {to_check}')
            return False

        return True

    def _other_errors(to_check):
        """Check if there are any other errors that could be thrown via
        printing this string."""
        try:
            # That is how print() internally parse placeholders and other
            # things.
            list(string.Formatter().parse(format_string=to_check))

        except Exception as exc:  # pylint: disable=broad-exception-caught
            print(f'\nERROR: {exc} in translation: {to_check}')
            return False

        return True

    def _place_holders(trans_string, src_string, flags):
        """Check if the placeholders between original source string
        and the translated string are identical. Order is ignored.

        To disable this check for a specific string add the translation
        flag "ignore-placeholder-compare" to the entry in the po-file.
        """

        if 'ignore-placeholder-compare' in flags:
            return True

        flagmsg = 'Disable this check with flagging it with ' \
                  '"ignore-placeholder-compare" in its po-file.'

        # Compare number of curly brackets.
        for bracket in tuple('{}'):
            if src_string.count(bracket) != trans_string.count(bracket):
                print(f'\nERROR: Number of "{bracket}" between original '
                      'source and translated string is different.\n'
                      f'Translation: {trans_string}\n{flagmsg}')
                return False

        # Compare variable names
        org_names = rex_names.findall(src_string)
        trans_names = rex_names.findall(trans_string)
        if sorted(org_names) != sorted(trans_names):
            print('\nERROR: Names of placeholders between original source '
                  'and translated string are different.\n'
                  f'Names in original    : {org_names}\n'
                  f'Names in translation : {trans_names}\n'
                  f'Full translation: {trans_string}\n{flagmsg}')
            return False

        return True

    print('Checking syntax of po files...')

    # Each po file
    for po_path in all_po_files_in_local_dir():
        # Language code determined by po-filename
        print(f'{po_path.with_suffix("").name}', end=' ')

        pof = polib.pofile(po_path)

        # Each translated entry
        for entry in pof.translated_entries():
            # Plural form?
            if entry.msgstr_plural or entry.msgid_plural:
                # Ignoring plural form because this is to complex, not logical
                # in all cases and also not worth the effort.
                continue

            if (not _curly_brackets_balanced(entry.msgstr)
                    or not _other_errors(entry.msgstr)
                    or not _place_holders(entry.msgstr,
                                          entry.msgid,
                                          entry.flags)):
                print(f'Source string: {entry.msgid}\n')

    print('')


def all_po_files_in_local_dir():
    """All po files (recursive)."""
    return LOCAL_DIR.rglob('**/*.po')


def create_completeness_dict():
    """Create a simple dictionary indexed by language code and value that
    indicate the completeness of the translation in percent.
    """

    print('Calculate completeness for each language in percent...')

    result = {}

    # each po file in the repository
    for po_path in all_po_files_in_local_dir():
        pof = polib.pofile(po_path)

        result[po_path.stem] = pof.percent_translated()

        pof.save()

    # "en" is the source language
    result['en'] = 100

    # info
    # print(json.dumps(result, indent=4))

    return result


def create_languages_file():
    """Create the languages.py file containing language names and the
    completeness of their translation.

    See the following functions for further details.
    - ``update_language_names()``
    - ``create_completeness_dict()``
    """

    # Convert language names dict to python code as a string
    names_dict = update_language_names()
    content = ['names = {']
    content.extend(dict_as_code(names_dict, 1))
    content.append('}')

    # the same with completeness dict
    compl_dict = create_completeness_dict()
    content.append('')
    content.append('')
    content.append('completeness = {')
    content.extend(dict_as_code(compl_dict, 1))
    content.append('}')

    with LANGUAGE_NAMES_PY.open('w', encoding='utf8') as handle:

        date_now = datetime.datetime.now().strftime('%c')
        handle.write(
            f'# Generated at {date_now} with help\n# of package "babel" '
            'and "polib".\n')
        handle.write('# https://babel.pocoo.org\n')
        handle.write('# https://github.com/python-babel/babel\n')
        handle.write(
            '# pylint: disable=too-many-lines,missing-module-docstring\n')

        handle.write('\n'.join(content))
        handle.write('\n')

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

    # Babel minimum version (because language code "ie")
    from packaging.version import Version
    if Version(babel.__version__) < Version('2.15'):
        raise ImportError(
            f'Babel version 2.15 required. But {babel.__version__} '
            'is installed.')

    # Source language (English) should be included
    if 'en' not in language_codes:
        language_codes.append('en')

    # Don't use defaultdict because pprint can't handle it
    result = {}

    for code in sorted(language_codes):
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
        'Back In &Time',
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

        # # WORKAROUND. See get_shortcut_groups() for details.
        # real['mainwindow'].append('Back In &Time')

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
        update_po_language_files('--remove-obsolete-entries' in sys.argv)
        create_languages_file()
        print(FIN_MSG)
        sys.exit()

    # Download translations (as po-files) from Weblate and integrate them
    # into the repository.
    if 'weblate' in sys.argv:
        update_from_weblate()
        check_syntax_of_po_files()
        create_languages_file()
        print(FIN_MSG)
        sys.exit()

    # Check for redundant &-shortcuts
    if 'shortcuts' in sys.argv:
        check_shortcuts()
        sys.exit()

    # Check for syntax problems (also implicit called via "weblate")
    if 'syntax' in sys.argv:
        check_syntax_of_po_files()
        sys.exit()

    print('Use one of the following argument keywords:\n'
          '  source  - Update the pot and po files with translatable '
          'strings extracted from py files. (Prepare upload to Weblate). '
          'Optional use --remove-obsolete-entries\n'
          '  weblate - Update the po files with translations from '
          'external translation service Weblate. (Download from Weblate)\n'
          '  shortcut - Check po files for redundant keyboard shortcuts '
          'using "&"\n'
          '  syntax - Check syntax of po files. (Also done via "weblate" '
          'command)')

    sys.exit(1)
