#!/usr/bin/env python3
import requests
import re
from collections import defaultdict
from pathlib import Path


def main():
    result = []
    fp = Path('CHANGES')

    items = []

    all_lines = fp.read_text('utf-8').split('\n')
    # PLAUSI
    if not all_lines[0] == 'Back In Time' or not all_lines[1] == '':
        raise ValueError('Unexpected content.\n{all_lines[:4]}')

    def _append_items(items):
        if items:
            result[-1] = (result[-1][0], items[:])
            items = []

        return items

    for line in all_lines[2:]:
        if not line:
            continue

        # bullet point?
        if line[0] in ['*', '-', '+']:
            # new item
            items.append(line)
            continue

        # next line of a bullet point?
        if line[0] == ' ':
            # append to last item
            items[-1] = items[-1] + ' ' + line[0].strip()
            continue

        # everything else
        items = _append_items(items)

        result.append((line, []))

    _append_items(items)

    return result


def get_std_suffix(suffix):
    if suffix == 'Uncategorized':
        return suffix

    fixed = (
        'FIX',
        'BUG FIX',
        'FIX BUG',
        'BACKPORT BUG FIX',
        'FIX CRITICAL BUG',
        'BUG FIX (GNOME)',
        'FIXED',
    )
    if suffix.upper() in fixed:
        return 'Fixed'

    added = (
        'FEATURE',
        'ADDED',
        'ADD',
    )
    if suffix.upper() in added:
        return 'Added'

    changed = (
        'Changed',
        'changed',
        'change',
        'updated',
        'Updated',
        'Refactor',
    )
    if suffix in changed:
        return 'Changed'

    removed = (
        'Removed',
        'remove',
    )
    if suffix in removed:
        return 'Removed'

    other = ()
    if suffix in other:
        return 'Uncategorized'

    return None


REX_LAUNCHPAD_BUG = re.compile(
    r'https:\/\/bugs\.launchpad\.net\/backintime\/\+bug\/(\d{6,8})')

REX_LAUNCHPAD_BUG2 = re.compile(
    r'.+LP\:#(\d{6,8})')

REX_LAUNCHPAD_BUG2B = re.compile(
    r'.+LP\: #(\d{6,8})')

REX_LAUNCHPAD_BUG3 = re.compile(
    r'https:\/\/launchpad\.net\/bugs\/(\d{6,8})')

REX_LAUNCHPAD_BUG4 = re.compile(
    r'https:\/\/bugs\.launchpad\.net\/bugs\/(\d{6,8})')

REX_LAUNCHPAD_BUG5 = re.compile(
    r'(?<!Launchpad)#(\d{6,8})')

REX_GITHUB_IDS = re.compile(
    r'(?<!Launchpad)#(\d+)')

REX_GITHUB_ISSUE_URL = re.compile(
    r'(?<!\]\()https:\/\/github.com\/bit-team\/backintime\/issues\/(\d+)')

REX_DEBIAN_BUG = re.compile(
    r'https:\/\/bugs\.debian\.org\/cgi-bin\/bugreport.cgi\?bug\=(\d{6})')

# extract Issues and PRs #1234 and @nicknames
# REX_NICK_AT = re.compile(r'[@][A-Za-z0-9_]+')
REX_NICK_AT = re.compile(r'(?<![A-Za-z0-9_.])@[A-Za-z0-9_]+')

LAUNCHPAD_BASE_URL = 'https://bugs.launchpad.net/backintime/+bug/'
LAUNCHPAD_BASE_URL3 = 'https://launchpad.net/bugs/'
LAUNCHPAD_BASE_URL4 = 'https://bugs.launchpad.net/bugs/'
GITHUB_BASE_URL = 'https://github.com/'
GITHUB_ISSUE_BASE_URL = 'https://github.com/bit-team/backintime/issues/'
GITHUB_PULL_BASE_URL = 'https://github.com/bit-team/backintime/pull/'

github_link_cache = {}


def format_links(content):
    # https://bugs.launchpad.net/backintime/+bug
    # Launchpad Bug Links
    print(f'format_links: {content}')

    for bug_id in REX_LAUNCHPAD_BUG.findall(content):
        old_link = f'{LAUNCHPAD_BASE_URL}{bug_id}'
        new_link = f'[Launchpad#{bug_id}]({old_link})'
        content = content.replace(old_link, new_link)

    for bug_id in REX_LAUNCHPAD_BUG2.findall(content):
        old_link = f'LP:#{bug_id}'
        new_link = f'[Launchpad#{bug_id}]({LAUNCHPAD_BASE_URL}{bug_id})'
        content = content.replace(old_link, new_link)

    for bug_id in REX_LAUNCHPAD_BUG2B.findall(content):
        old_link = f'LP: #{bug_id}'
        new_link = f'[Launchpad#{bug_id}]({LAUNCHPAD_BASE_URL}{bug_id})'
        content = content.replace(old_link, new_link)

    for bug_id in REX_LAUNCHPAD_BUG3.findall(content):
        old_link = f'{LAUNCHPAD_BASE_URL3}{bug_id}'
        new_link = f'[Launchpad#{bug_id}]({LAUNCHPAD_BASE_URL}{bug_id})'
        content = content.replace(old_link, new_link)

    for bug_id in REX_LAUNCHPAD_BUG4.findall(content):
        old_link = f'{LAUNCHPAD_BASE_URL4}{bug_id}'
        new_link = f'[Launchpad#{bug_id}]({LAUNCHPAD_BASE_URL}{bug_id})'
        content = content.replace(old_link, new_link)

    for bug_id in REX_LAUNCHPAD_BUG5.findall(content):
        old_link = f'#{bug_id}'
        new_link = f'[Launchpad#{bug_id}]({LAUNCHPAD_BASE_URL}{bug_id})'
        content = content.replace(old_link, new_link)

    for github_id in REX_GITHUB_IDS.findall(content):
        old_link = f'#{github_id}'
        new_link = get_github_url_by_id(github_id)
        content = content.replace(old_link, f'[{old_link}]({new_link})')

    for bug_id in REX_GITHUB_ISSUE_URL.findall(content):
        old_link = f'{GITHUB_ISSUE_BASE_URL}{bug_id}'
        new_link = f'[#{bug_id}]({old_link})'
        content = content.replace(old_link, new_link)

    for bug_id in REX_DEBIAN_BUG.findall(content):
        old_link = f'https://bugs.debian.org/cgi-bin/bugreport.cgi?bug={bug_id}'
        new_link = f'[Debian#{bug_id}]({old_link})'
        print(f'{old_link=}\n{new_link=}')
        content = content.replace(old_link, new_link)

    for nick_id in REX_NICK_AT.findall(content):
        old_link = nick_id
        new_link = f'[{nick_id}]({GITHUB_BASE_URL}{nick_id[1:]})'
        content = content.replace(old_link, new_link)

    return content


def get_github_url_by_id(github_id):
    try:
        return github_link_cache[github_id]

    except KeyError:
        url = f'{GITHUB_ISSUE_BASE_URL}{github_id}'
        # print(f'Check link {url} …')

        # PullRequest?
        if not requests.get(url).ok:
            url = f'{GITHUB_PULL_BASE_URL}{github_id}'

        github_link_cache[github_id] = url

    return url


def process_items(items):
    result = defaultdict(list)

    # "* suffix: content"
    rex_suffix = re.compile(r'^\*\s*([^:]+):\s*(.+)')
    rex_suffix = re.compile(r'^\*\s*([^:]+?)(?<!https):\s*(.+)')
    # "* suffix content"
    rex_first_word = re.compile(r'^\*\s*(\w+)\s+(.+)')

    for i in items:

        try:
            if ':' in i:
                suffix, content = rex_suffix.search(i).groups()
            else:
                suffix, content = rex_first_word.search(i).groups()

        except AttributeError:
            suffix = 'Uncategorized'
            content = i[2:]  # cut bullet

        std_suffix = get_std_suffix(suffix)

        if std_suffix is None:
            sep = ': ' if ':' in i else ' '
            content = suffix + sep + content
            std_suffix = 'Uncategorized'

        content = format_links(content)

        content = content.replace('https: //', 'https://')

        # content = explicit_links(content)

        print(f'{std_suffix} :: {content}\n')
        result[std_suffix].append(content)

    return result


def process_raw_results(raw_result):
    result = []

    # Extract version and date
    rex_ver_date = re.compile(
        r'^Version (\d+\.\d+.*) \((.+)\)$')

    for heading, items in raw_result:
        try:
            version, date = rex_ver_date.search(heading).groups()

        except Exception as exc:
            print(f'{heading=} {items=}')
            raise exc

        result.append(
            (
                version,
                date,
                process_items(items)
            )
        )

    return result

def to_markdown(data, fh):
    # reference links added to the end of the markdown File
    ref_links = []

    # Head
    fh.writelines([
        '<!---\n',
        'SPDX-FileCopyrightText: © 2023 Christian BUHTZ '
        '<c.buhtz@posteo.jp>\n\n',
        'SPDX-License-Identifier: GPL-2.0-or-later\n\n',
        'This file is part of the program "Back In Time" which is '
        'released under GNU\n',
        'General Public License v2 (GPLv2). See LICENSES directory or go to\n',
        '<https://spdx.org/licenses/GPL-2.0-or-later.html>\n',
        '-->\n',
    ])
    fh.write('# Changelog\n')
    fh.write('[![Common Changelog](https://common-changelog.org/badge.svg)]'
             '(https://common-changelog.org)\n')

    # Comment about template
    fh.writelines([
        '<!-- Template\n',
        '## Unreleased\n',
        '### Changed\n',
        '### Added\n',
        '### Removed\n',
        '### Fixed\n',
        '-->\n'
    ])

    url = 'https://github.com/bit-team/backintime/releases/tag/v'

    # each release
    for version, date, categories in data:
        fh.write(f'\n## [{version}] ({date})\n')

        ref_links.append(f'[{version}]: {url}{version}\n')

        for cat in categories:
            fh.write(f'\n### {cat}\n\n')
            fh.writelines([f'- {item}\n' for item in categories[cat]])

    handle.write('\n')
    handle.writelines(ref_links)


if __name__ == '__main__':
    raw_result = main()

    result = process_raw_results(raw_result)

    with Path('CHANGELOG.md').open('w', encoding='utf-8') as handle:
        to_markdown(result, handle)
