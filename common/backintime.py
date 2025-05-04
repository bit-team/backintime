# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
import os
import sys
import argparse
import atexit
import subprocess
from datetime import datetime
from time import sleep
import json
import pathlib
import tools
# Workaround for situations where startApp() is not invoked.
# E.g. when using --diagnostics and other argparse.Action
tools.initiate_translation(None)
import config
import logger
import snapshots
import sshtools
import mount
import password
import encfstools
import cli
import cliarguments
import clicommands
from bitbase import URL_ENCRYPT_TRANSITION
from diagnostics import collect_diagnostics, collect_minimal_diagnostics
from exceptions import MountException
from applicationinstance import ApplicationInstance
from version import __version__
from shutdownagent import ShutdownAgent

RETURN_OK = 0
RETURN_ERR = 1
RETURN_NO_CFG = 2

parsers = {}


def takeSnapshotAsync(cfg, checksum=False):
    """
    Fork a new backintime process with 'backup' command which will
    take a new snapshot in background.

    Args:
        cfg (config.Config): config that should be used
    """
    cmd = []

    if cfg.ioniceOnUser():
        cmd.extend(('ionice', '-c2', '-n7'))

    cmd.append('backintime')

    if '1' != cfg.currentProfile():
        cmd.extend(('--profile-id', str(cfg.currentProfile())))
    if cfg._LOCAL_CONFIG_PATH is not cfg._DEFAULT_CONFIG_PATH:
        cmd.extend(('--config', cfg._LOCAL_CONFIG_PATH))
    if cfg._LOCAL_DATA_FOLDER is not cfg._DEFAULT_LOCAL_DATA_FOLDER:
        cmd.extend(('--share-path', cfg.DATA_FOLDER_ROOT))
    if logger.DEBUG:
        cmd.append('--debug')
    if checksum:
        cmd.append('--checksum')

    cmd.append('backup')

    # child process need to start its own ssh-agent because otherwise
    # it would be lost without ssh-agent if parent will close
    env = os.environ.copy()

    for i in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID'):
        try:
            del env[i]

        except:
            pass

    subprocess.Popen(cmd, env = env)


def takeSnapshot(cfg, force=True):
    """
    Take a new snapshot.

    Args:
        cfg (config.Config):    config that should be used
        force (bool):           take the snapshot even if it wouldn't need to
                                or would be prevented (e.g. running on battery)

    Returns:
        bool:                   ``True`` if there was an error
    """
    tools.envLoad(cfg.cronEnvFile())
    ret = snapshots.Snapshots(cfg).backup(force)

    return ret


def _mount(cfg):
    """
    Mount external filesystems.

    Args:
        cfg (config.Config): Config that should be used.
    """
    try:
        hash_id = mount.Mount(cfg=cfg).mount()

    except MountException as ex:
        logger.error(str(ex))
        sys.exit(RETURN_ERR)

    else:
        cfg.setCurrentHashId(hash_id)


def _umount(cfg):
    """
    Unmount external filesystems.

    Args:
        cfg (config.Config): Config that should be used.
    """
    try:
        mount.Mount(cfg=cfg).umount(cfg.current_hash_id)

    except MountException as ex:
        logger.error(str(ex))


def encfs_deprecation_warning():
    """Warn about encfs deprecation in syslog.

    See Issue #1734 for details. This function is a workraound and will be
    removed if #1734 is closed.
    """

    # Don't warn if EncFS isn't installed
    if not tools.checkCommand('encfs'):
        return

    # Timestamp file
    xdg_state = os.environ.get('XDG_STATE_HOME', None)
    if xdg_state:
        xdg_state = pathlib.Path(xdg_state)
    else:
        xdg_state = pathlib.Path.home() / '.local' / 'state'
    fp = xdg_state / 'backintime.encfs-warning.timestamp'

    # ensure existence
    if not fp.exists():
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.touch()

    # Calculate age of that file
    delta = datetime.now() - datetime.fromtimestamp(fp.stat().st_mtime)

    # Don't warn if to young
    if delta.days < 30:
        return

    logger.warning('EncFS encrypted profiles are deprecated in Back In Time. '
                   'Removal is schedule for minor release 1.7 in year 2026. '
                   'For details and alternatives '
                   f'read: {URL_ENCRYPT_TRANSITION}')


    # refresh timestamp
    fp.touch()


def startApp(app_name='backintime'):
    """
    Start the requested command or return config if there was no command
    in arguments.

    Args:
        app_name (str): string representing the current application

    Returns:
        config.Config:  current config if no command was given in arguments
    """
    # Workaround (maybe)
    cmd_func = {
        'backup': clicommands.backup,
        'backup-job': clicommands.backup_job,
        'benchmark-cipher': clicommands.benchmark_cipher,
        'check-config': clicommands.check_config,
        'decode': clicommands.decode,
        'last-snapshot': clicommands.last_snapshot,
        'last-snapshot-path': clicommands.last_snapshot_path,
        'pw-cache': clicommands.pw_cache,
        'remove': cliarguments.remove,
        'remove-and-do-not-ask-again': cliarguments.remove_and_donot_ask_again,
    }
    global parsers  # REFACTOR!
    parsers = cliarguments.create_parsers(
        app_name='backintime', cmd_func_dict=cmd_func)

    logger.openlog()

    args = argParse(None)

    # Name, Version, As Root, OS
    msg = ''
    for key, val in collect_minimal_diagnostics().items():
        msg = f'{msg}; {key}: {val}'
    logger.debug(msg[2:])

    # Add source path to $PATH environ if running from source
    if tools.runningFromSource():
        tools.addSourceToPathEnviron()

    # Warn about sudo
    if (tools.usingSudo()
            and os.getenv('BIT_SUDO_WARNING_PRINTED', 'false') == 'false'):

        os.putenv('BIT_SUDO_WARNING_PRINTED', 'true')
        logger.warning(
            "It looks like you're using 'sudo' to start "
            f"{config.Config.APP_NAME}. This will cause some trouble. "
            f"Please use either 'sudo -i {app_name}' or 'pkexec {app_name}'.")

    encfs_deprecation_warning()

    # Call commands
    if 'func' in dir(args):
        args.func(args)
        return None

    # No arguments/commands
    setQuiet(args)
    printHeader()

    return getConfig(args, False)


def argParse(args):
    """
    Parse arguments given on commandline.

    Args:
        args (argparse.Namespace):  Namespace that should be enhanced
                                    or ``None``

    Returns:
        argparser.Namespace:        new parsed Namespace
    """
    def join(args, subArgs):
        """
        Add new arguments to existing Namespace.

        Args:
            args (argparse.Namespace):
                        main Namespace that should get new arguments
            subArgs (argparse.Namespace):
                        second Namespace which have new arguments
                        that should be merged into ``args``
        """
        for key, value in vars(subArgs).items():
            # Only add new values if it isn't set already or if there really IS
            # a value
            if getattr(args, key, None) is None or value:
                setattr(args, key, value)

    # First parse the main parser without subparsers
    # otherwise positional args in subparsers will be to greedy
    # but only if -h or --help is not involved because otherwise
    # help will not work for subcommands
    mainParser = parsers['main']
    sub = []

    if '-h' not in sys.argv and '--help' not in sys.argv:

        for i in mainParser._actions:

            if isinstance(i, argparse._SubParsersAction):
                # Remove subparsers
                mainParser._remove_action(i)
                sub.append(i)

    args, unknownArgs = mainParser.parse_known_args(args)

    # Read subparsers again
    if sub:
        [mainParser._add_action(i) for i in sub]

    # Parse it again for unknown args
    if unknownArgs:
        subArgs, unknownArgs = mainParser.parse_known_args(unknownArgs)
        join(args, subArgs)

    # Finally parse only the command parser, otherwise we miss some arguments
    # from command
    if unknownArgs and 'command' in args and args.command in parsers:
        commandParser = parsers[args.command]
        subArgs, unknownArgs = commandParser.parse_known_args(unknownArgs)
        join(args, subArgs)

    try:
        logger.DEBUG = args.debug
    except AttributeError:
        pass

    args_dict = vars(args)
    used_args = {
        key: args_dict[key]
        for key
        in filter(lambda key: args_dict[key] is not None, args_dict)
    }

    logger.debug(f'Argument(s) used: {used_args}')

    # Report unknown arguments but not if we run aliasParser next because we
    # will parse again in there.
    if unknownArgs and not ('func' in args and args.func is aliasParser):
        mainParser.error(f'Unknown argument(s): {unknownArgs}')

    return args


def printHeader():
    """
    Print application name, version and legal notes.
    """
    print('')
    print('Back In Time')
    print('Version: ' + __version__)
    print('')
    print('Back In Time comes with ABSOLUTELY NO WARRANTY.')
    print('This is free software, and you are welcome to redistribute it')
    print("under certain conditions; type `backintime --license' for details.")
    print('')


class PseudoAliasAction(argparse.Action):
    """
    Translate '--COMMAND' into 'COMMAND' for backwards compatibility.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        """
        Translate '--COMMAND' into 'COMMAND' for backwards compatibility.

        Args:
            parser (argparse.ArgumentParser): NotImplemented
            namespace (argparse.Namespace):   Namespace that should get modified
            values:                           NotImplemented
            option_string:                    NotImplemented
        """
        #TODO: find a more elegant way to solve this
        dest = self.dest.replace('_', '-')
        if self.dest == 'b':
            replace = '-b'
            alias = 'backup'
        else:
            replace = '--%s' % dest
            alias = dest
        setattr(namespace, 'func', aliasParser)
        setattr(namespace, 'replace', replace)
        setattr(namespace, 'alias', alias)


def aliasParser(args):
    """
    Call commands which where given with leading -- for backwards
    compatibility.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments
    """
    if not args.quiet:
        logger.info("Run command '%(alias)s' instead of argument '%(replace)s' due to backwards compatibility."
                    % {'alias': args.alias, 'replace': args.replace})
    argv = [w.replace(args.replace, args.alias) for w in sys.argv[1:]]
    newArgs = argParse(argv)
    if 'func' in dir(newArgs):
        newArgs.func(newArgs)


def getConfig(args, check=True):
    """
    Load config and change to profile selected on commandline.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments
        check (bool):   if ``True`` check if config is valid

    Returns:
        config.Config:  current config with requested profile selected

    Raises:
        SystemExit:     1 if ``profile`` or ``profile_id`` is no valid profile
                        2 if ``check`` is ``True`` and config is not configured
    """
    cfg = config.Config(config_path=args.config, data_path=args.share_path)
    logger.debug('config file: "{}"; share path: "{}"; profiles: "{}"'.format(
        cfg._LOCAL_CONFIG_PATH,
        cfg._LOCAL_DATA_FOLDER,
        ', '.join(f'{profile_id}={cfg.profileName(profile_id)}'
                  for profile_id in cfg.profiles())
    ))

    if 'profile_id' in args and args.profile_id:
        if not cfg.setCurrentProfile(args.profile_id):
            logger.error('Profile-ID not found: %s' % args.profile_id)
            sys.exit(RETURN_ERR)

    if 'profile' in args and args.profile:
        if not cfg.setCurrentProfileByName(args.profile):
            logger.error('Profile not found: %s' % args.profile)
            sys.exit(RETURN_ERR)

    if check and not cfg.isConfigured():
        logger.error('%(app)s is not configured!' % {'app': cfg.APP_NAME})
        sys.exit(RETURN_NO_CFG)

    if 'checksum' in args:
        cfg.forceUseChecksum = args.checksum

    return cfg


def setQuiet(args):
    """
    Redirect :py:data:`sys.stdout` to ``/dev/null`` if ``--quiet`` was set on
    commandline. Return the original :py:data:`sys.stdout` file object which can
    be used to print absolute necessary information.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Returns:
        sys.stdout:     default sys.stdout
    """
    force_stdout = sys.stdout
    if args.quiet:
        # do not replace with subprocess.DEVNULL - will not work
        sys.stdout = open(os.devnull, 'w')
        atexit.register(sys.stdout.close)
        atexit.register(force_stdout.close)
    return force_stdout


def shutdown(args):
    """
    Command for shutting down the computer after the current snapshot has
    finished.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0 if successful; 1 if it failed either because there is
                        no active snapshot for this profile or shutdown is not
                        supported.
    """
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)

    sd = ShutdownAgent()

    if not sd.can_shutdown():
        logger.warning('Shutdown is not supported.')
        sys.exit(RETURN_ERR)

    instance = ApplicationInstance(cfg.takeSnapshotInstanceFile(), False)
    profile = '='.join((cfg.currentProfile(), cfg.profileName()))

    if not instance.busy():
        logger.info('There is no active snapshot for profile %s. Skip shutdown.'
                    %profile)
        sys.exit(RETURN_ERR)

    print('Shutdown is waiting for the snapshot in profile %s to end.\nPress CTRL+C to interrupt shutdown.\n'
          %profile)
    sd.activate_shutdown = True

    try:
        while instance.busy():
            logger.debug('Snapshot is still active. Wait for shutdown.')
            sleep(5)

    except KeyboardInterrupt:
        print('Shutdown interrupted.')

    else:
        logger.info('Shutdown now.')
        sd.shutdown()

    sys.exit(RETURN_OK)


def snapshotsPath(args):
    """
    Command for printing the full snapshot path of current profile.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    if args.keep_mount:
        _mount(cfg)
    if args.quiet:
        msg = '{}'
    else:
        msg = 'SnapshotsPath: {}'
    print(msg.format(cfg.snapshotsFullPath()), file=force_stdout)
    sys.exit(RETURN_OK)


def snapshotsList(args):
    """
    Command for printing a list of all snapshots in current profile.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)

    if args.quiet:
        msg = '{}'
    else:
        msg = 'SnapshotID: {}'
    no_sids = True
    #use snapshots.listSnapshots instead of iterSnapshots because of sorting
    for sid in snapshots.listSnapshots(cfg, reverse = False):
        print(msg.format(sid), file=force_stdout)
        no_sids = False
    if no_sids:
        logger.error("There are no snapshots in '%s'" % cfg.profileName())
    if not args.keep_mount:
        _umount(cfg)
    sys.exit(RETURN_OK)


def snapshotsListPath(args):
    """
    Command for printing a list of all snapshots paths in current profile.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)

    if args.quiet:
        msg = '{}'
    else:
        msg = 'SnapshotPath: {}'
    no_sids = True
    #use snapshots.listSnapshots instead of iterSnapshots because of sorting
    for sid in snapshots.listSnapshots(cfg, reverse = False):
        print(msg.format(sid.path()), file=force_stdout)
        no_sids = False
    if no_sids:
        logger.error("There are no snapshots in '%s'" % cfg.profileName())
    if not args.keep_mount:
        _umount(cfg)
    sys.exit(RETURN_OK)


def unmount(args):
    """
    Command for unmounting all filesystems.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    _umount(cfg)
    sys.exit(RETURN_OK)


def smartRemove(args):
    """
    Command for running Smart-Removal from Terminal.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0 if okay
                        2 if Smart-Removal is not configured
    """
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    sn = snapshots.Snapshots(cfg)

    enabled, keep_all, keep_one_per_day, keep_one_per_week, keep_one_per_month = cfg.smartRemove()
    if enabled:
        _mount(cfg)
        del_snapshots = sn.smartRemoveList(datetime.today(),
                                           keep_all,
                                           keep_one_per_day,
                                           keep_one_per_week,
                                           keep_one_per_month)
        logger.info('Smart Removal will remove {} snapshots'.format(len(del_snapshots)))
        sn.smartRemove(del_snapshots, log = logger.info)
        _umount(cfg)
        sys.exit(RETURN_OK)
    else:
        logger.error('Smart Removal is not configured.')
        sys.exit(RETURN_NO_CFG)


def restore(args):
    """
    Command for restoring files from snapshots.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    _mount(cfg)

    if cfg.backupOnRestore() and not args.no_local_backup:
        backup = True
    else:
        backup = args.local_backup

    cli.restore(cfg,
                args.SNAPSHOT_ID,
                args.WHAT,
                args.WHERE,
                delete=args.delete,
                backup=backup,
                only_new=args.only_new)

    _umount(cfg)

    sys.exit(RETURN_OK)


if __name__ == '__main__':
    startApp()
