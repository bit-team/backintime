# SPDX-FileCopyrightText: © 2012-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2012-2022 Taylor Raack
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""The module is a messy collection of ssh related stuff. It will be refactored
and reintegrated into other modules. One of its ancestors is sshcore.py.
See Issue #2484.
"""
import os
import subprocess
import re
from pathlib import Path
import logger
import tools
import bitbase


def sshKeyGen(keyfile: str) -> bool:
    """Generate a new pair of SSH keys (private & public) without passphrase.

    Args:
        keyfile: Path for private key file and public (``.pub`` prefix added)

    Returns:
        ``True`` if successful; ``False`` if ``keyfile`` already exist or
        if there was an error.
    """

    if os.path.exists(keyfile):
        logger.warning(f'SSH keyfile "{keyfile}" already exist. '
                       'Skip creating a new one.')

        return False

    cmd = [
        'ssh-keygen',
        # key type (#2194)
        '-t', 'rsa',
        # No passphrase
        '-N', '',
        # Base filename
        '-f', keyfile
    ]

    proc = subprocess.Popen(cmd,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            universal_newlines=True)

    com = proc.communicate()
    rc = proc.returncode

    if rc:
        err = com[1]
        logger.error(f'Failed to create a new SSH key: {err}')

    else:
        logger.info(f'New SSH key created: {keyfile}')

    return not rc


def sshCopyIdCommand(
    pubkey,
    user,
    host,
    port='22',
    proxy_user=None,
    proxy_host=None,
    proxy_port='22',
):
    """
    Generate a ssh-copy-id command to copy the given public ssh-key to a
    remote host.

    Args:
        pubkey (str):   path to the public key file
        user (str):     remote user
        host (str):     remote host
        port (str):     ssh port on remote host
        proxy_user (str):     proxy host user
        proxy_host (str):     proxy host
        proxy_port (str):     proxy host port

    Returns:
        list: The ssh-copy-id command as a list.

    Raises:
        FileNotFoundError: If public key file not exist.
    """
    if not Path(pubkey).exists():
        msg = f'SSH public key "{pubkey}" does not exist.'
        logger.error(msg)
        raise FileNotFoundError(msg)

    cmd = [
        'ssh-copy-id',
        # key file
        '-i', pubkey,
        # port
        '-p', str(port),
    ]

    # proxy
    if proxy_host:
        proxy_jump = f'{proxy_user}@{proxy_host}:{proxy_port}'
        cmd.extend(['-o', f'ProxyJump={proxy_jump}'])

    cmd.append(f'{user}@{host}')

    logger.debug(f'ssh-copy-id command {cmd}')

    return cmd


def sshCopyId(
    pubkey,
    user,
    host,
    port='22',
    proxy_user=None,
    proxy_host=None,
    proxy_port=None,
    askPass='backintime-askpass',
):
    """
    Copy SSH public key ``pubkey`` to remote ``host``.

    Args:
        pubkey (str):   path to the public key file
        user (str):     remote user
        host (str):     remote host
        port (str):     ssh port on remote host
        askPass (str):  program used to pipe password into ssh

    Returns:
        bool:           True if successful
    """
    cmd = sshCopyIdCommand(
        pubkey,
        user,
        host,
        port,
        proxy_user,
        proxy_host,
        proxy_port,
    )

    env = os.environ.copy()
    env['SSH_ASKPASS'] = askPass
    env['ASKPASS_MODE'] = 'USER'
    env['ASKPASS_PROMPT'] = '{}\n{}:'.format(
        _('Copy public SSH key "{pubkey}" to remote host "{host}".').format(
            pubkey=pubkey, host=host),
        _('Please enter a password for "{user}".').format(user=user)
    )
    proc = subprocess.Popen(cmd, env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE,
                            preexec_fn=os.setsid,  # cut of ssh from current
                                                   # terminal to make it use
                                                   # backintime-askpass
                            universal_newlines=True)

    err = proc.communicate()[1]

    if proc.returncode:
        logger.error('Failed to copy ssh-key "{}" to "{}@{}": [{}] {}'
                     .format(pubkey, user, host, proc.returncode, err))

    else:
        logger.info('Successfully copied ssh-key "{}" to "{}@{}"'
                    .format(pubkey, user, host))

    return not proc.returncode


# def _maybe_REACTIVTE_LATER_sshHostKey(host, port='22'):
#     """
#     Get the remote host key from ``host``.

#     Args:
#         host (str): host name or IP address
#         port (str): port number of remote ssh-server

#     Returns:
#         tuple:      three item tuple with (fingerprint, hashed host key,
#                     key type)
#     """

#     for t in ('ecdsa', 'rsa'):
#         cmd = ['ssh-keyscan', '-t', t, '-p', port, host]
#         proc = subprocess.Popen(cmd,
#                                 stdout=subprocess.PIPE,
#                                 stderr=subprocess.DEVNULL)

#         result = proc.communicate()
#         hostKey = result[0].strip()

#         if hostKey:
#             break

#     if hostKey:

#         logger.debug('Found {} key for host "{}"'.format(t.upper(), host))

#         with tempfile.TemporaryDirectory() as tmp:

#             keyFile = os.path.join(tmp, 'key')

#             with open(keyFile, 'wb') as f:
#                 f.write(hostKey + b'\n')

#             hostKeyFingerprint = sshKeyFingerprint(keyFile)

#             cmd = ['ssh-keygen', '-H', '-f', keyFile]

#             proc = subprocess.Popen(cmd,
#                                     stdout=subprocess.DEVNULL,
#                                     stderr=subprocess.DEVNULL)
#             proc.communicate()

#             with open(keyFile, mode='rt', encoding='utf-8') as handle:
#                 hostKeyHash = handle.read().strip()

#         return (hostKeyFingerprint, hostKeyHash, t.upper())

#     return (None, None, None)


def determine_default_ssh_key_filename() -> str | None:
    """Return the default filename for new generated SSH keys used by
    ssh-keygen.

    Return:
        The filename as string or `None` in case of errors.
    """
    proc = subprocess.run(
        ['ssh-keygen', '-N', '""'],
        stdin=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True)

    # Extract the default key file name from that question prompt:
    # "Generating public/private rsa key pair.\nEnter file in which
    # to save the key (/home/user/.ssh/id_rsa): "
    pattern = r'.+\(' + re.escape(str(bitbase.DIR_SSH_KEYS)) + r'\/(.+)\):.*'

    result = re.search(pattern, proc.stdout)
    if result:
        return result.group(1)

    logger.debug('Error determining the default SSH key file name.'
                 f'{proc=} match {result=}')

    return None


def writeKnownHostsFile(key):
    """
    Write host key ``key`` into `~/.ssh/known_hosts`.

    Args:
        key (str):  host key
    """

    sshDir = os.path.expanduser('~/.ssh')

    knownHostFile = os.path.join(sshDir, 'known_hosts')

    if not os.path.isdir(sshDir):
        tools.mkdir(sshDir, 0o700)

    with open(knownHostFile, mode='at', encoding='utf-8') as handle:
        logger.info(f'Write host key to f{knownHostFile}')
        handle.write(key + '\n')


def get_private_ssh_key_files() -> list[Path]:
    """Return a list of existing private key files."""

    # folder containing the key files
    ssh_path = Path.home() / '.ssh'

    try:
        # exclude by filename
        potential_key_files = filter(
            # irrelevant files
            lambda fp: fp.name not in (
                'known_hosts',
                'authorized_keys',
                'config',
                'backup'
            )
            # no public keys
            and fp.suffix != '.pub',
            ssh_path.iterdir()
        )
    except FileNotFoundError:
        potential_key_files = []

    result = []

    # e.g. "-----BEGIN OPENSSH PRIVATE KEY-----"
    # rex = re.compile(r'^-+BEGIN\s\S+\sPRIVATE KEY-+$')
    rex = re.compile(br'^-+BEGIN\s+\S+\s+PRIVATE KEY-+')

    # check content
    for fp in potential_key_files:
        if not fp.is_file():
            continue

        try:
            with fp.open('rb') as handle:
                data = handle.read(4096)  # read max. 4 KB

                # PEM (text based)
                if rex.search(data):
                    result.append(fp)

                # DER / ASN.1 (binary key file) with long keys
                elif data[:2] in (b'\x30\x82', b'\x30\x81'):
                    result.append(fp)

                # DER / ASN.1 (binary key file) with short keys
                elif data[:1] == b'\x30':
                    result.append(fp)

        except OSError:
            # ignore files that cannot be opened (e.g. sockets)
            continue

    # prioritize 'ed25519' keys and move them to the beginning of the list
    result = sorted(result, key=lambda e: 0 if 'ed25519' in e.name else 1)

    return result
