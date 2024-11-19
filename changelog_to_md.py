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
    """
    '### Changed',
    '### Removed',
    """
    if suffix == 'Uncategorized':
        return suffix

    fixed = (
        'FIX',
        'BUG FIX',
        'FIX BUG',
        'BACKPORT BUG FIX',
        'FIX CRITICAL BUG',
        'BUG FIX (GNOME)',
    )
    if suffix.upper() in fixed:
        return 'Fixed'

    added = ('FEATURE')
    if suffix.upper() in added:
        return 'Added'

    other = ()
    if suffix in other:
        return 'Uncategorized'

    return None


REX_LAUNCHPAD_BUG = re.compile(
    r'https:\/\/bugs\.launchpad\.net\/backintime\/\+bug\/(\d{6,8})')

REX_LAUNCHPAD_BUG2 = re.compile(
    r'.+LP\:#(\d{6,8})')

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

LAUNCHPAD_BASE_URL = 'https://bugs.launchpad.net/backintime/+bug/'
LAUNCHPAD_BASE_URL3 = 'https://launchpad.net/bugs/'
LAUNCHPAD_BASE_URL4 = 'https://bugs.launchpad.net/bugs/'
GITHUB_ISSUE_BASE_URL = 'https://github.com/bit-team/backintime/issues/'
GITHUB_PULL_BASE_URL = 'https://github.com/bit-team/backintime/pull/'

github_link_cache = {}


def format_links(content):
    # https://bugs.launchpad.net/backintime/+bug
    # Launchpad Bug Links

    for bug_id in REX_LAUNCHPAD_BUG.findall(content):
        old_link = f'{LAUNCHPAD_BASE_URL}{bug_id}'
        new_link = f'[Launchpad#{bug_id}]({old_link})'
        content = content.replace(old_link, new_link)

    for bug_id in REX_LAUNCHPAD_BUG2.findall(content):
        old_link = f'LP:#{bug_id}'
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

        try:
            new_link = github_link_cache[github_id]
        except KeyError:
            new_link = f'{GITHUB_ISSUE_BASE_URL}{github_id}'
            print(f'Check link {new_link} …')

            # PullRequest?
            if not requests.get(new_link).ok:
                new_link = f'{GITHUB_PULL_BASE_URL}{github_id}'

            github_link_cache[github_id] = new_link

        content = content.replace(old_link, f'[{old_link}]({new_link})')

    for bug_id in REX_GITHUB_ISSUE_URL.findall(content):
        old_link = f'{GITHUB_ISSUE_BASE_URL}{bug_id}'
        new_link = f'[#{bug_id}]({old_link})'
        content = content.replace(old_link, new_link)

    return content


def process_items(items):
    result = defaultdict(list)

    rex_suffix = re.compile(r'^\*\s*([^:]+):\s*(.+)')

    for i in items:

        try:
            suffix, content = rex_suffix.search(i).groups()
        except AttributeError:
            suffix = 'Uncategorized'
            content = i[2:]  # cut bullet

        std_suffix = get_std_suffix(suffix)

        if std_suffix is None:
            content = suffix + ': ' + content
            std_suffix = 'Uncategorized'

        content = format_links(content)

        result[std_suffix].append(content)

    return result


def process_raw_results(raw_result):
    result = []

    # Extract version and date
    rex_ver_date = re.compile(
        r'^Version (\d+\.\d+.*) \((.+)\)$')

    for heading, items in raw_result:
        version, date = rex_ver_date.search(heading).groups()

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
