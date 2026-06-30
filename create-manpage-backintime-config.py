#!/usr/bin/env python3
# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2023 Christian Buhtz <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""This script is a helper to create a manpage about Back In Times's config
file.

The file `common/config.py` is parsed for variable names, default values and
other information. The founder of that script @Germar gave a detailed
description about that script in #1354.

The script reads every line and tries to analyze it:
  - It searches for `DEFAULT` and puts those into a `dict` for later replacing
    the variable with the value.
  - If that didn't match it will look for lines starting with `#?` which is
    basically my own description for the manpage-entry.
    Multiple lines will get merged and stored in `commentline` until the
    processing of the current config option is done. That will reset
    `commentline`.
  - If a line starts with `#` it will be skipped.
  - Next the script searches for lines which ``return`` the config value (like
    `snapshots.ssh.port`. There it will extract the
    key/name (`snapshots.ssh.port`), the default value (`22`),
    the instance (`Int`) and if it is a profile or general value.
  - If the line contains a `List` value like `snapshots.include` it will
    process all values for the list like `snapshots.include.<I>.value` and
    `snapshots.include.<I>.type`.  Also it will add the size like
    `snapshots.include.size`.

In `process_line` it will replace some information with those I wrote manually
in the `#?` description, separated by `;` there is the comment,  value,
force_default and force_var. If there is no forced value it will chose the
value based on the instance with `select_values`
"""
import os
import sys
import re
import inspect
import subprocess
from pathlib import Path
from time import strftime, gmtime
from typing import Any
# Workaround (see #1575)
sys.path.insert(0, str(Path.cwd() / 'common'))
import konfig
import version

MAN = Path.cwd() / 'common' / 'man' / 'C' / 'backintime-config.1'

# Extract multiline string between { and the latest }
REX_DICT_EXTRACT = re.compile(r'\{([\s\S]*)\}')
# Extract attribute name
REX_ATTR_NAME = re.compile(r"self(?:\._conf)?\[['\"](.*)['\"]\]")

CONFIG = os.path.join(PATH, 'config.py')
MAN = os.path.join(PATH, 'man/C/backintime-config.5')

# |--------------------------|
# | GNU Trof (groff) helpers |
# |--------------------------|

def groff_section(section: str) -> str:
    """Section header"""
    return f'.SH {section}\n'


def groff_indented_paragraph(label: str, indent: int=6) -> str:
    """.IP - Indented Paragraph"""
    return f'.IP "{label}" {indent}'


def groff_italic(text: str) -> str:
    """\\fi - Italic"""
    return f'\\fI{text}\\fR'


def groff_bold(text: str) -> str:
    """Bold"""
    return f'\\fB{text}\\fR'


def groff_bold_roman(text: str) -> str:
    """The first part of the text is marked bold the rest is
    roman/normal.

    Used to reference other man pages."""
    return f'.BR {text}\n'


def groff_indented_block(text: str) -> str:
    """
    .RS - Start indented block
    .RE - End indented block
    """
    return f'\n.RS\n{text}\n.RE\n'


def groff_linebreak() -> str:
    """.br - Line break"""
    return '.br\n'


def groff_paragraph_break() -> str:
    """.PP - Paragraph break"""
    return '.PP\n'

# |--------------------|
# | Content generation |
# |--------------------|


def header():
    stamp = strftime('%b %Y', gmtime())
    ver = version.__version__

    content = ''.join([
        f'.TH backintime-config 1 "{stamp}" '
        f'"version {ver}" "USER COMMANDS"\n',

        groff_section('NAME'),
        'config \\- Back In Time configuration file.\n',

        groff_section('SYNOPSIS'),
        '~/.config/backintime/config\n',
        groff_linebreak(),
        '/etc/backintime/config\n',

        groff_section('DESCRIPTION'),
        'Back In Time was developed as pure GUI program and so most '
        'functions are only usable with ',
        groff_bold('backintime-qt'),
        '. But it is possible to use Back In Time e.g. on a '
        'headless server. You have to create the configuration file '
        '(~/.config/backintime/config) manually. Look inside '
        '/usr/share/doc/backintime\\-common/examples/ for examples.\n',

        groff_paragraph_break(),
        'The configuration file has the following format:\n',
        groff_linebreak(),
        'keyword=arguments\n',

        groff_paragraph_break(),
        "Arguments don't need to be quoted. All characters are "
        "allowed except '='.\n",

        groff_paragraph_break(),
        "Run 'backintime check-config' to verify the configfile, "
        "create the snapshot folder and crontab entries.\n",

        groff_section('POSSIBLE KEYWORDS'),
    ])

    return content


def entry_to_groff(name: str,
                   doc: str,
                   values: Any,
                   default: Any,
                   its_type: type) -> None:
    """Generate GNU Troff (groff) markup code for the given config entry."""

    if its_type is not None:
        if isinstance(its_type, str):
            type_name = its_type
        else:
            type_name = its_type.__name__
    else:
        type_name = ''

    ret = f'Type: {type_name:<10}Allowed Values: {values}\n'
    ret += groff_linebreak()
    ret += f'{doc}\n'
    ret += groff_paragraph_break()

    if default is not None:
        ret += f'Default: {default}'

    ret = groff_indented_block(ret)
    ret = groff_indented_paragraph(groff_italic(name)) + ret

    return ret


def footer() -> str:
    content = groff_section('SEE ALSO')
    content += groff_bold_roman('backintime (1),')
    content += groff_bold_roman('backintime-qt (1)')
    content += groff_paragraph_break()
    content += 'Back In Time also has a website: ' \
               'https://github.com/bit-team/backintime\n'

    content += groff_section('AUTHOR')
    content += 'This manual page was written by the ' \
               'Back In Time Team (<bit-dev@python.org>).'

    return content

# |------|
# | Misc |
# |------|


def _get_public_properties(cls: type) -> tuple:
    """Extract the public properties from our target config class."""
    def _is_public_property(val):
        return (
            not val.startswith('_')
            and isinstance(getattr(cls, val), property)
        )

    return tuple(filter(_is_public_property, cls.__dict__.keys()))


def lint_manpage(path: Path) -> bool:
    """Lint the manpage the same way as the Debian Lintian does."""

    print('Linting man page…')

    cmd = [
        'man',
        '--warnings',
        '-E',
        'UTF-8',
        '-l',
        '-Tutf8',
        '-Z',
        str(path)
    ]

    env = dict(
        **os.environ,
        LC_ALL='C.UTF-8',
        # MANROFFSEQ="''",
        MANWIDTH='80',
    )

    try:
        with open('/dev/null', 'w') as devnull:
            result = subprocess.run(
                cmd,
                env=env,
                check=True,
                text=True,
                stdout=devnull,
                stderr=subprocess.PIPE
            )

    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f'Unexpected error: {exc.stderr=}') from exc

    # Report warnings
    if result.stderr:
        print(result.stderr)
        return False

    print('No problems reported.')

    return True


def inspect_properties(cls: type, name_prefix: str = '') -> dict[str, dict]:
    """Collect details about propiertes of the class `cls`.

    All public properties containing a doc string are considered.
    Some values can be specified with a dictionary contained in the doc string
    but don't have to, except the 'values' field containing the allowed values.
    The docstring is used as description ('doc'). The type annotation of the
    return value is used as 'type'. The name of the config field is extracted
    from the code body of the property method.

    Example of a result ::

        {
            'global.hash_collision':
            {
                'values': '0-99999',
                'default': 0,
                'doc': 'Internal value ...',
                'type': 'int'
            },
        }

    Results in a man page entry like this ::

        POSSIBLE KEYWORDS

            global.hash_collision
                Type: int       Allowed Values: 0-99999
                Internal value ...

                Default: 0

    Returns:
        A dictionary indexed by the config option field names.
    """
    # The following fields/properties will produce warnings. But this is
    # expected on happens on purpose. The list is used to "ease" the warning
    # message.
    expect_to_be_ignored = (
        'Konfig.profile_names',
        'Konfig.profile_ids',
        'Konfig.manual_starts_countdown',
        'Profile.include',
        'Profile.exclude',
        'Profile.keep_named_snapshots',
    )

    entries = {}

    # Each public property in the class
    for prop in _get_public_properties(cls):
        attr = getattr(cls, prop)

        # Ignore properties without docstring
        if not attr.__doc__:
            full_prop = f'{cls.__name__}.{prop}'
            ok = '(No problem) ' if full_prop in expect_to_be_ignored else ''
            print(f'{ok}Ignoring "{full_prop}" because of '
                  'missing docstring.')
            continue

        # DEBUG
        # print(f'{cls.__name__}.{prop}')

        # Extract config field name from code (self._conf['config.field'])
        try:
            name = REX_ATTR_NAME.findall(inspect.getsource(attr.fget))[0]
            name = f'{name_prefix}{name}'
        except IndexError as exc:
            full_prop = f'{cls.__name__}.{prop}'
            ok = '(No problem) ' if full_prop in expect_to_be_ignored else ''
            print(f'{ok}Ignoring "{full_prop}" because it is not '
                  'possible to find name of config field in its body.')
            continue

        # Full doc string
        doc = attr.__doc__

        # extract the dict from docstring
        try:
            the_dict = REX_DICT_EXTRACT.search(doc).groups()[0]
        except AttributeError:
            the_dict = ''

        the_dict = '{' + the_dict + '}'

        # remove the dict from docstring
        doc = doc.replace(the_dict, '')

        # Make it a real dict
        the_dict = eval(the_dict)

        # Clean up the docstring from empty lines and other blanks
        doc = ' '.join(line.strip()
                       for line in
                       filter(lambda val: len(val.strip()), doc.split('\n')))

        # store the result
        the_dict['doc'] = doc

        # default value
        if 'default' not in the_dict:
            try:
                the_dict['default'] = cls._DEFAULT_VALUES[name]
            except KeyError:
                pass

        # type (by return value annotation)
        if 'type' not in the_dict:
            return_type = inspect.signature(attr.fget).return_annotation

            if return_type != inspect.Signature.empty:
                the_dict['type'] = return_type

        # type by default values
        if 'type' not in the_dict and 'default' in the_dict:
            the_dict['type'] = type(the_dict['default']).__name__

        # values if bool
        if 'values' not in the_dict:
            if the_dict['type'] == 'bool':
                the_dict['values'] = 'true|false'
            elif the_dict['type'] == 'int':
                the_dict['values'] = '0-99999'
            elif the_dict['type'] == 'str':
                the_dict['values'] = 'text'


        entries[name] = the_dict

        # DEBUG
        # print(f'entries[{name}]={entries[name]}')

    return entries


def main():
    """The classes `Konfig` and `Konfig.Profile` are inspected and relevant
    information is extracted to create a man page of it.

    Only public properties with doc strings are used. The doc strings also
    need to contain a dict with additional information like allowed values and
    default values. The data type is determined form the default value. The
    property name is determined from the property methods name.

    Example ::

        {
            'values': (0, 99999),
            'default': 0,
        }
    """

    # Inspect the classes and extract man page related data from them.
    global_entries = inspect_properties(
        cls=konfig.Konfig,
    )
    profile_entries = inspect_properties(
        cls=konfig.Profile,
        name_prefix='profile<N>.'
    )

    # WORKAROuND:
    # Structure of include/exclude fields can not be easily handled via
    # properties and doc-string inspection. The structure will get
    # modified in the future. Until then we add their man page docu
    # manual.
    inc_exc = {
        'profile<N>.snapshots.exclude.<I>.value': {
            'doc': 'Exclude this file or folder. <I> must be a counter '
                   'starting with 1',
            'values': 'file, folder or pattern (relative or absolute)',
            'default': '',
            'type': 'str'
        },
        # Don't worry. "exclude.<I>.type" does not exist.
        'profile<N>.snapshots.include.<I>.value': {
            'doc': 'Include this file or folder. <I> must be a counter '
                   'starting with 1',
            'values': 'absolute path',
            'default': '',
            'type': 'str'
        },
        'profile<N>.snapshots.include.<I>.type': {
            'doc':
                'Specify if ' + groff_indented_block(
                    'profile<N>.snapshots.include.<I>.value')
                + ' is a folder (0) or a file (1)',
            'values': '0|1',
            'default': 0,
            'type': 'int'
        },
    }

    # Create the man page file
    with MAN.open('w', encoding='utf-8') as handle:
        print(f'Write GNU Troff (groff) markup to "{MAN}".')

        # HEADER
        handle.write(header())

        # PROPERTIES
        for name, entry in {**global_entries, **profile_entries}.items():
            try:
                handle.write(
                    entry_to_groff(
                        name=name,
                        doc=entry['doc'],
                        values=entry['values'],
                        default=entry.get('default', None),
                        its_type=entry.get('type', None),
                    )
                )
            except Exception as exc:
                print(f'{name=} {entry=}')
                raise exc

            handle.write('\n')

        # FOOTER
        handle.write(footer())
        handle.write('\n')

        print('Finished creating man page.')

    lint_manpage(MAN)


if __name__ == '__main__':
    main()
