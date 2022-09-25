#    Back In Time
#    Copyright (C) 2008-2022 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License along
#    with this program; if not, write to the Free Software Foundation, Inc.,
#    51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import os
import sys
import gettext
import argparse
import atexit
import subprocess
from datetime import datetime
from time import sleep
import json

import config
import logger
import snapshots
import tools
import sshtools
import mount
import password
import encfstools
import cli
from exceptions import MountException
from applicationinstance import ApplicationInstance

_ = gettext.gettext

RETURN_OK = 0
RETURN_ERR = 1
RETURN_NO_CFG = 2

parsers = {}

def takeSnapshotAsync(cfg, checksum = False):
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

def takeSnapshot(cfg, force = True):
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
        cfg (config.Config):    config that should be used
    """
    try:
        hash_id = mount.Mount(cfg = cfg).mount()
    except MountException as ex:
        logger.error(str(ex))
        sys.exit(RETURN_ERR)
    else:
        cfg.setCurrentHashId(hash_id)

def _umount(cfg):
    """
    Unmount external filesystems.

    Args:
        cfg (config.Config):    config that should be used
    """
    try:
        mount.Mount(cfg = cfg).umount(cfg.current_hash_id)
    except MountException as ex:
        logger.error(str(ex))

def createParsers(app_name = 'backintime'):
    """
    Define parsers for commandline arguments.

    Args:
        app_name (str):         string representing the current application
    """
    global parsers

    #define debug
    debugArgsParser = argparse.ArgumentParser(add_help = False)
    debugArgsParser.add_argument('--debug',
                                 action = 'store_true',
                                 help = 'Increase verbosity.')

    #define config argument
    configArgsParser = argparse.ArgumentParser(add_help = False)
    configArgsParser.add_argument('--config',
                                 metavar = 'PATH',
                                 type = str,
                                 action = 'store',
                                 help = 'Read config from %(metavar)s. ' +
                                        'Default = ~/.config/backintime/config')

    configArgsParser.add_argument('--share-path',
                                 metavar = 'PATH',
                                 type = str,
                                 action = 'store',
                                 help = 'Write runtime data (locks, messages, log and mountpoints) to %(metavar)s.')

    #define common arguments which are used for all commands
    commonArgsParser = argparse.ArgumentParser(add_help = False, parents = [configArgsParser, debugArgsParser])
    profileGroup = commonArgsParser.add_mutually_exclusive_group()
    profileGroup.add_argument    ('--profile',
                                  metavar = 'NAME',
                                  type = str,
                                  action = 'store',
                                  help = 'Select profile by %(metavar)s.')
    profileGroup.add_argument    ('--profile-id',
                                  metavar = 'ID',
                                  type = int,
                                  action = 'store',
                                  help = 'Select profile by %(metavar)s.')
    commonArgsParser.add_argument('--quiet',
                                  action = 'store_true',
                                  help = 'Be quiet. Suppress messages on stdout.')

    #define arguments which are only used by snapshots-path, snapshots-list-path and last-snapshot-path
    snapshotPathParser = argparse.ArgumentParser(add_help = False)
    snapshotPathParser.add_argument('--keep-mount',
                                    action = 'store_true',
                                    help = "Don't unmount on exit.")

    #define arguments which are used by rsync commands (backup and restore)
    rsyncArgsParser = argparse.ArgumentParser(add_help = False)
    rsyncArgsParser.add_argument('--checksum',
                                 action = 'store_true',
                                 help = 'force to use checksum for checking if files have been changed.')

    #define arguments for snapshot remove
    removeArgsParser = argparse.ArgumentParser(add_help = False)
    removeArgsParser.add_argument('SNAPSHOT_ID',
                                  type = str,
                                  action = 'store',
                                  nargs = '*',
                                  help = 'ID of snapshots which should be removed.')

    #define main argument parser
    parser = argparse.ArgumentParser(prog = app_name,
                                     parents = [commonArgsParser],
                                     description = '%(app)s - a simple backup tool for Linux.'
                                                   % {'app': config.Config.APP_NAME},
                                     epilog = "For backwards compatibility commands can also be used with trailing '--'. "
                                              "All listed arguments will work with all commands. Some commands have extra arguments. "
                                              "Run '%(app_name)s <COMMAND> -h' to see the extra arguments."
                                              % {'app_name': app_name})
    parsers['main'] = parser
    parser.add_argument('--version', '-v',
                        action = 'version',
                        version = '%(prog)s ' + str(config.Config.VERSION),
                        help = "show %(prog)s's version number.")
    parser.add_argument('--license',
                        action = printLicense,
                        nargs = 0,
                        help = "show %(prog)s's license.")
    parser.add_argument('--diagnostics',
                        action = printDiagnostics,
                        nargs = 0,
                        help = "show helpful info for better support in case of issues (in JSON format)")

    #######################
    ### define commands ###
    #######################
    epilog = "Run '%(app_name)s -h' to get help for additional arguments. " %{'app_name': app_name}
    epilogCommon = epilog + 'Additional arguments: --config, --debug, --profile, --profile-id, --quiet'
    epilogConfig = epilog + 'Additional arguments: --config, --debug'

    subparsers = parser.add_subparsers(title = 'Commands', dest = 'command')
    command = 'backup'
    nargs = 0
    aliases = [(command, nargs), ('b', nargs)]
    description = 'Take a new snapshot. Ignore if the profile ' +\
                  'is not scheduled or if the machine runs on battery.'
    backupCP =             subparsers.add_parser(command,
                                                 parents = [rsyncArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    backupCP.set_defaults(func = backup)
    parsers[command] = backupCP

    command = 'backup-job'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Take a new snapshot in background only '      +\
                  'if the profile is scheduled and the machine ' +\
                  'is not on battery. This is use by cron jobs.'
    backupJobCP =          subparsers.add_parser(command,
                                                 parents = [rsyncArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    backupJobCP.set_defaults(func = backupJob)
    parsers[command] = backupJobCP

    command = 'benchmark-cipher'
    nargs = '?'
    aliases.append((command, nargs))
    description = 'Show a benchmark of all ciphers for ssh transfer.'
    benchmarkCipherCP =    subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    benchmarkCipherCP.set_defaults(func = benchmarkCipher)
    parsers[command] = benchmarkCipherCP
    benchmarkCipherCP.add_argument              ('FILE_SIZE',
                                                 type = int,
                                                 action = 'store',
                                                 default = 40,
                                                 nargs = '?',
                                                 help = 'File size used to for benchmark.')

    command = 'check-config'
    description = 'Check the profiles configuration and install crontab entries.'
    checkConfigCP =        subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    checkConfigCP.add_argument                  ('--no-crontab',
                                                 action = 'store_true',
                                                 help = 'Do not install crontab entries.')
    checkConfigCP.set_defaults(func = checkConfig)
    parsers[command] = checkConfigCP

    command = 'decode'
    nargs = '*'
    aliases.append((command, nargs))
    description = "Decode paths with 'encfsctl decode'"
    decodeCP =             subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    decodeCP.set_defaults(func = decode)
    parsers[command] = decodeCP
    decodeCP.add_argument                       ('PATH',
                                                 type = str,
                                                 action = 'store',
                                                 nargs = '*',
                                                 help = 'Decode PATH. If no PATH is specified on command line ' +\
                                                 'a list of filenames will be read from stdin.')

    command = 'last-snapshot'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Show the ID of the last snapshot.'
    lastSnapshotCP =       subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    lastSnapshotCP.set_defaults(func = lastSnapshot)
    parsers[command] = lastSnapshotCP

    command = 'last-snapshot-path'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Show the path of the last snapshot.'
    lastSnapshotsPathCP =  subparsers.add_parser(command,
                                                 parents = [snapshotPathParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    lastSnapshotsPathCP.set_defaults(func = lastSnapshotPath)
    parsers[command] = lastSnapshotsPathCP

    command = 'pw-cache'
    nargs = '*'
    aliases.append((command, nargs))
    description = 'Control Password Cache for non-interactive cronjobs.'
    pwCacheCP =            subparsers.add_parser(command,
                                                 epilog = epilogConfig,
                                                 help = description,
                                                 description = description)
    pwCacheCP.set_defaults(func = pwCache)
    parsers[command] = pwCacheCP
    pwCacheCP.add_argument                      ('ACTION',
                                                 action = 'store',
                                                 choices = ['start', 'stop', 'restart', 'reload', 'status'],
                                                 nargs = '?',
                                                 help = 'Command to send to Password Cache daemon.')

    command = 'remove'
    nargs = '*'
    aliases.append((command, nargs))
    description = 'Remove a snapshot.'
    removeCP =             subparsers.add_parser(command,
                                                 parents = [removeArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    removeCP.set_defaults(func = remove)
    parsers[command] = removeCP

    command = 'remove-and-do-not-ask-again'
    nargs = '*'
    aliases.append((command, nargs))
    description = "Remove snapshots and don't ask for confirmation before. Be careful!"
    removeDoNotAskCP =     subparsers.add_parser(command,
                                                 parents = [removeArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    removeDoNotAskCP.set_defaults(func = removeAndDoNotAskAgain)
    parsers[command] = removeDoNotAskCP

    command = 'restore'
    nargs = '*'
    aliases.append((command, nargs))
    description = 'Restore files.'
    restoreCP =            subparsers.add_parser(command,
                                                 parents = [rsyncArgsParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    restoreCP.set_defaults(func = restore)
    parsers[command] = restoreCP
    backupGroup = restoreCP.add_mutually_exclusive_group()
    restoreCP.add_argument                      ('WHAT',
                                                 type = str,
                                                 action = 'store',
                                                 nargs = '?',
                                                 help = 'Restore file or folder WHAT.')

    restoreCP.add_argument                      ('WHERE',
                                                 type = str,
                                                 action = 'store',
                                                 nargs = '?',
                                                 help = "Restore to WHERE. An empty argument '' will restore to original destination.")

    restoreCP.add_argument                      ('SNAPSHOT_ID',
                                                 type = str,
                                                 action = 'store',
                                                 nargs = '?',
                                                 help = 'Which SNAPSHOT_ID should be used. This can be a snapshot ID or ' +\
                                                 'an integer starting with 0 for the last snapshot, 1 for the second to last, ... ' +\
                                                 'the very first snapshot is -1')

    restoreCP.add_argument                      ('--delete',
                                                 action = 'store_true',
                                                 help = 'Restore and delete newer files which are not in the snapshot. ' +\
                                                 'WARNING: deleting files in filesystem root could break your whole system!!!')

    backupGroup.add_argument                    ('--local-backup',
                                                 action = 'store_true',
                                                 help = 'Create backup files before changing local files.')

    backupGroup.add_argument                    ('--no-local-backup',
                                                 action = 'store_true',
                                                 help = 'Temporary disable creation of backup files before changing local files. ' +\
                                                 'This can be switched of permanently in Settings, too.')

    restoreCP.add_argument                      ('--only-new',
                                                 action = 'store_true',
                                                 help = 'Only restore files which does not exist or are newer than ' +\
                                                        'those in destination. Using "rsync --update" option.')

    command = 'shutdown'
    nargs = 0
    description = 'Shutdown the computer after the snapshot is done.'
    shutdownCP =           subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    shutdownCP.set_defaults(func = shutdown)
    parsers[command] = shutdownCP

    command = 'smart-remove'
    nargs = 0
    description = 'Remove snapshots based on "Smart Remove" pattern.'
    smartRemoveCP =        subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    smartRemoveCP.set_defaults(func = smartRemove)
    parsers[command] = smartRemoveCP

    command = 'snapshots-list'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Show a list of snapshots IDs.'
    snapshotsListCP =      subparsers.add_parser(command,
                                                 parents = [snapshotPathParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    snapshotsListCP.set_defaults(func = snapshotsList)
    parsers[command] = snapshotsListCP

    command = 'snapshots-list-path'
    nargs = 0
    aliases.append((command, nargs))
    description = "Show the path's to snapshots."
    snapshotsListPathCP =  subparsers.add_parser(command,
                                                 parents = [snapshotPathParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    snapshotsListPathCP.set_defaults(func = snapshotsListPath)
    parsers[command] = snapshotsListPathCP

    command = 'snapshots-path'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Show the path where snapshots are stored.'
    snapshotsPathCP =      subparsers.add_parser(command,
                                                 parents = [snapshotPathParser],
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    snapshotsPathCP.set_defaults(func = snapshotsPath)
    parsers[command] = snapshotsPathCP

    command = 'unmount'
    nargs = 0
    aliases.append((command, nargs))
    description = 'Unmount the profile.'
    unmountCP =            subparsers.add_parser(command,
                                                 epilog = epilogCommon,
                                                 help = description,
                                                 description = description)
    unmountCP.set_defaults(func = unmount)
    parsers[command] = unmountCP

    #define aliases for all commands with trailing --
    group = parser.add_mutually_exclusive_group()
    for alias, nargs in aliases:
        if len(alias) == 1:
            arg = '-%s' % alias
        else:
            arg = '--%s' % alias
        group.add_argument(arg,
                           nargs = nargs,
                           action = PseudoAliasAction,
                           help = argparse.SUPPRESS)

def startApp(app_name = 'backintime'):
    """
    Start the requested command or return config if there was no command
    in arguments.

    Args:
        app_name (str): string representing the current application

    Returns:
        config.Config:  current config if no command was given in arguments
    """
    createParsers(app_name)
    #open log
    logger.APP_NAME = app_name
    logger.openlog()

    #parse args
    args = argParse(None)

    #add source path to $PATH environ if running from source
    if tools.runningFromSource():
        tools.addSourceToPathEnviron()

    #warn about sudo
    if tools.usingSudo() and os.getenv('BIT_SUDO_WARNING_PRINTED', 'false') == 'false':
        os.putenv('BIT_SUDO_WARNING_PRINTED', 'true')
        logger.warning("It looks like you're using 'sudo' to start %(app)s. "
                       "This will cause some troubles. Please use either 'sudo -i %(app_name)s' "
                       "or 'pkexec %(app_name)s'."
                       %{'app_name': app_name, 'app': config.Config.APP_NAME})

    #call commands
    if 'func' in dir(args):
        args.func(args)
    else:
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
            #only add new values if it isn't set already or if there really IS a value
            if getattr(args, key, None) is None or value:
                setattr(args, key, value)

    #first parse the main parser without subparsers
    #otherwise positional args in subparsers will be to greedy
    #but only if -h or --help is not involved because otherwise
    #help will not work for subcommands
    mainParser = parsers['main']
    sub = []
    if '-h' not in sys.argv and '--help' not in sys.argv:
        for i in mainParser._actions:
            if isinstance(i, argparse._SubParsersAction):
                #remove subparsers
                mainParser._remove_action(i)
                sub.append(i)
    args, unknownArgs = mainParser.parse_known_args(args)
    #read subparsers again
    if sub:
        [mainParser._add_action(i) for i in sub]

    #parse it again for unknown args
    if unknownArgs:
        subArgs, unknownArgs = mainParser.parse_known_args(unknownArgs)
        join(args, subArgs)

    #finally parse only the command parser, otherwise we miss
    #some arguments from command
    if unknownArgs and 'command' in args and args.command in parsers:
        commandParser = parsers[args.command]
        subArgs, unknownArgs = commandParser.parse_known_args(unknownArgs)
        join(args, subArgs)

    if 'debug' in args:
        logger.DEBUG = args.debug

    dargs = vars(args)
    logger.debug('Arguments: %s | unknownArgs: %s'
                 %({arg:dargs[arg] for arg in dargs if dargs[arg]},
                   unknownArgs))

    #report unknown arguments
    #but not if we run aliasParser next because we will parse again in there
    if unknownArgs and not ('func' in args and args.func is aliasParser):
        mainParser.error('Unknown Argument(s): %s' % ', '.join(unknownArgs))
    return args

def printHeader():
    """
    Print application name, version and legal notes.
    """
    version = config.Config.VERSION
    # Git info is now only shown via --diagnostics
    # ref, hashid = tools.gitRevisionAndHash()
    # if ref:
    #     version += " git branch '{}' hash '{}'".format(ref, hashid)
    print('')
    print('Back In Time')
    print('Version: ' + version)
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
        args (argparse.Namespace): Previously parsed arguments
        check (bool): If ``True`` check if config is valid

    Returns:
        config.Config:  current config with requested profile selected

    Raises:
        SystemExit:     1 if ``profile`` or ``profile_id`` is no valid profile
                        2 if ``check`` is ``True`` and config is not configured
    """
    cfg = config.Config(
        config_path=args.config,
        data_path=args.share_path
    )

    logger.debug('config file: %s' % cfg._LOCAL_CONFIG_PATH)
    logger.debug('share path: %s' % cfg._LOCAL_DATA_FOLDER)
    logger.debug('profiles: %s' % ', '
                 .join('%s=%s' % (x, cfg.profileName(x))
                       for x in cfg.profiles()))

    if 'profile_id' in args and args.profile_id:

        if not cfg.setCurrentProfile(args.profile_id):
            logger.error('Profile-ID not found: %s' % args.profile_id)

            sys.exit(RETURN_ERR)

    if 'profile' in args and args.profile:

        if not cfg.setCurrentProfileByName(args.profile):
            logger.error('Profile not found: %s' % args.profile)

            sys.exit(RETURN_ERR)

    if check and not cfg.isConfigured():
        logger.error('%(app)s is not configured!' %{'app': cfg.APP_NAME})

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

class printLicense(argparse.Action):
    """
    Print custom license
    """
    def __init__(self, *args, **kwargs):
        super(printLicense, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        cfg = config.Config()
        print(cfg.license())
        sys.exit(RETURN_OK)

class printDiagnostics(argparse.Action):
    """
    Print information that is helpful for the support team
    to narrow down problems and bugs.
    The info is printed using the machine- and human-readable JSON format
    """

    def __init__(self, *args, **kwargs):
        super(printDiagnostics, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        """
        """

        cfg = config.Config()

        # TODO Refactor into a separate functions in a new diagnostics.py
        # when more info is added
        ref, hashid = tools.gitRevisionAndHash()
        git_branch = "Unknown"
        git_commit = "Unknown"

        if ref:
            git_branch = ref
            git_commit = hashid

        diagnostics = dict(
            app_name=config.Config.APP_NAME,
            app_version=config.Config.VERSION,
            app_git_branch=git_branch,
            app_git_commit=git_commit,
            user_callback=cfg.takeSnapshotUserCallback()
        )

        print(json.dumps(diagnostics, indent=4))

        sys.exit(RETURN_OK)

def backup(args, force = True):
    """
    Command for force taking a new snapshot.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments
        force (bool):   take the snapshot even if it wouldn't need to or would
                        be prevented (e.g. running on battery)

    Raises:
        SystemExit:     0 if successful, 1 if not
    """
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    ret = takeSnapshot(cfg, force)
    sys.exit(int(ret))

def backupJob(args):
    """
    Command for taking a new snapshot in background. Mainly used for cronjobs.
    This will run the snapshot inside a daemon and detach from it. It will
    return immediately back to commandline.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    cli.BackupJobDaemon(backup, args).start()

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

    sd = tools.ShutDown()
    if not sd.canShutdown():
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
    Command for printing a list of all snapshots pathes in current profile.

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

def lastSnapshot(args):
    """
    Command for printing the very last snapshot in current profile.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    sid = snapshots.lastSnapshot(cfg)
    if sid:
        if args.quiet:
            msg = '{}'
        else:
            msg = 'SnapshotID: {}'
        print(msg.format(sid), file=force_stdout)
    else:
        logger.error("There are no snapshots in '%s'" % cfg.profileName())
    _umount(cfg)
    sys.exit(RETURN_OK)

def lastSnapshotPath(args):
    """
    Command for printing the path of the very last snapshot in
    current profile.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    sid = snapshots.lastSnapshot(cfg)
    if sid:
        if args.quiet:
            msg = '{}'
        else:
            msg = 'SnapshotPath: {}'
        print(msg.format(sid.path()), file=force_stdout)
    else:
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

def benchmarkCipher(args):
    """
    Command for transferring a file with scp to remote host with all
    available ciphers and print its speed and time.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    if cfg.snapshotsMode() in ('ssh', 'ssh_encfs'):
        ssh = sshtools.SSH(cfg)
        ssh.benchmarkCipher(args.FILE_SIZE)
        sys.exit(RETURN_OK)
    else:
        logger.error("SSH is not configured for profile '%s'!" % cfg.profileName())
        sys.exit(RETURN_ERR)

def pwCache(args):
    """
    Command for starting password cache daemon.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0 if daemon is running, 1 if not
    """
    force_stdout = setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    ret = RETURN_OK
    daemon = password.Password_Cache(cfg)
    if args.ACTION and args.ACTION != 'status':
        getattr(daemon, args.ACTION)()
    elif args.ACTION == 'status':
        print('%(app)s Password Cache: ' % {'app': cfg.APP_NAME}, end=' ', file = force_stdout)
        if daemon.status():
            print(cli.bcolors.OKGREEN + 'running' + cli.bcolors.ENDC, file = force_stdout)
            ret = RETURN_OK
        else:
            print(cli.bcolors.FAIL + 'not running' + cli.bcolors.ENDC, file = force_stdout)
            ret = RETURN_ERR
    else:
        daemon.run()
    sys.exit(ret)

def decode(args):
    """
    Command for decoding paths given paths with 'encfsctl'.
    Will listen on stdin if no path was given.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    if cfg.snapshotsMode() not in ('local_encfs', 'ssh_encfs'):
        logger.error("Profile '%s' is not encrypted." % cfg.profileName())
        sys.exit(RETURN_ERR)
    _mount(cfg)
    d = encfstools.Decode(cfg)
    if not args.PATH:
        while True:
            try:
                path = input()
            except EOFError:
                break
            if not path:
                break
            print(d.path(path), file = force_stdout)
    else:
        print('\n'.join(d.list(args.PATH)), file = force_stdout)
    d.close()
    _umount(cfg)
    sys.exit(RETURN_OK)

def remove(args, force = False):
    """
    Command for removing snapshots.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments
        force (bool):   don't ask before removing (BE CAREFUL!)

    Raises:
        SystemExit:     0
    """
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    _mount(cfg)
    cli.remove(cfg, args.SNAPSHOT_ID, force)
    _umount(cfg)
    sys.exit(RETURN_OK)

def removeAndDoNotAskAgain(args):
    """
    Command for removing snapshots without asking before remove
    (BE CAREFUL!)

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0
    """
    remove(args, True)

def smartRemove(args):
    """
    Command for running Smart-Remove from Terminal.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0 if okay
                        2 if Smart-Remove is not configured
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
        logger.info('Smart Remove will remove {} snapshots'.format(len(del_snapshots)))
        sn.smartRemove(del_snapshots, log = logger.info)
        _umount(cfg)
        sys.exit(RETURN_OK)
    else:
        logger.error('Smart Remove is not configured.')
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
                delete = args.delete,
                backup = backup,
                only_new = args.only_new)
    _umount(cfg)
    sys.exit(RETURN_OK)

def checkConfig(args):
    """
    Command for checking the config file.

    Args:
        args (argparse.Namespace):
                        previously parsed arguments

    Raises:
        SystemExit:     0 if config is okay, 1 if not
    """
    force_stdout = setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    if cli.checkConfig(cfg, crontab = not args.no_crontab):
        print("\nConfig %(cfg)s profile '%(profile)s' is fine."
              % {'cfg': cfg._LOCAL_CONFIG_PATH,
                 'profile': cfg.profileName()},
              file = force_stdout)
        sys.exit(RETURN_OK)
    else:
        print("\nConfig %(cfg)s profile '%(profile)s' has errors."
              % {'cfg': cfg._LOCAL_CONFIG_PATH,
                 'profile': cfg.profileName()},
              file = force_stdout)
        sys.exit(RETURN_ERR)

if __name__ == '__main__':
    startApp()
