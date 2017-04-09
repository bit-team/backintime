#    Back In Time
#    Copyright (C) 2008-2017 Oprea Dan, Bart de Koning, Richard Bailey, Germar Reitze
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
import subprocess

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

_=gettext.gettext

RETURN_OK = 0
RETURN_ERR = 1
RETURN_NO_CFG = 2

parsers = {}

def take_snapshot_now_async( cfg ):
    '''fork a new backintime process with 'backup' command which will
    take a new snapshot in background.

    cfg:    config.Config instance
    '''
    cmd = []
    if cfg.is_run_ionice_from_user_enabled():
        cmd.extend(('ionice', '-c2', '-n7'))
    cmd.append('backintime')
    if '1' != cfg.get_current_profile():
        cmd.extend(('--profile-id', str(cfg.get_current_profile())))
    if cfg._LOCAL_CONFIG_PATH is not cfg._DEFAULT_CONFIG_PATH:
        cmd.extend(('--config', cfg._LOCAL_CONFIG_PATH))
    if logger.DEBUG:
        cmd.append('--debug')
    cmd.append('backup')

    # child process need to start its own ssh-agent because otherwise
    # it would be lost without ssh-agent if parent will close
    env = os.environ.copy()
    for i in ('SSH_AUTH_SOCK', 'SSH_AGENT_PID'):
        try:
            del env[i]
        except:
            pass
    subprocess.Popen(cmd, env = env, shell = True)

def take_snapshot( cfg, force = True ):
    '''take a new snapshot.

    cfg:    config.Config instance
    force:  take the snapshot even if it wouldn't need to or would be
            prevented (e.g. running on battery)
    '''
    tools.load_env(cfg.get_cron_env_file())
    ret = snapshots.Snapshots( cfg ).take_snapshot( force )
    return ret

def _mount(cfg):
    '''mount external filesystems.

    cfg:    config.Config instance
    '''
    try:
        hash_id = mount.Mount(cfg = cfg).mount()
    except MountException as ex:
        logger.error(str(ex))
        sys.exit(RETURN_ERR)
    else:
        cfg.set_current_hash_id(hash_id)

def _umount(cfg):
    '''unmount external filesystems.

    cfg:    config.Config instance
    '''
    try:
        mount.Mount(cfg = cfg).umount(cfg.current_hash_id)
    except MountException as ex:
        logger.error(str(ex))

def create_parsers(app_name = 'backintime'):
    '''define parsers for commandline arguments.

    app_name:   string representing the current application
    '''
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
                                 help = 'Read config from %(metavar)s.')

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
    description = "Decode pathes with 'encfsctl decode'"
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
                                                 'an integer starting with 0 for the last snapshot, 1 for the overlast, ... ' +\
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

def start_app(app_name = 'backintime'):
    '''start the requested command or return config if there was no command
    in arguments.

    app_name:   string representing the current application
    '''
    create_parsers(app_name)
    #open log
    logger.APP_NAME = app_name
    logger.openlog()

    #parse args
    args = arg_parse(None)

    #add source path to $PATH environ if running from source
    if tools.running_from_source():
        tools.add_source_to_path_environ()

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

def arg_parse(args):
    '''parse arguments given on commandline.

    args:   argparse.ArgumentParser instance that should be enhanced or None

    tests:
    test/test_argparser.TestArgParser.*    (all of them)
    '''
    def join(args, subArgs):
        '''add new arguments to existing ArgumentParser.

        args:       main argparse.ArgumentParser instance that should
                    get new arguments
        subArgs:    second argparse.ArgumentParser instance which have
                    new arguments that should be merged into args
        '''
        for key, value in vars(subArgs).items():
            #only add new values if it isn't set already or if there really IS a value
            if getattr(args, key, None) is None or value:
                setattr(args, key, value)

    #first parse the main parser without subparsers
    #otherwise positional args in subparsers will be to greedy
    mainParser = parsers['main']
    sub = []
    for i in mainParser._actions:
        if isinstance(i, argparse._SubParsersAction):
            #remove subparsers
            mainParser._remove_action(i)
            sub.append(i)
    args, unknownArgs = mainParser.parse_known_args(args)
    #readd subparsers again
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
    '''print application name, version and legal notes.
    '''
    version = config.Config.VERSION
    ref, hashid = tools.get_git_ref_hash()
    if ref:
        version += " git branch '{}' hash '{}'".format(ref, hashid)
    print('')
    print('Back In Time')
    print('Version: ' + version)
    print('')
    print('Back In Time comes with ABSOLUTELY NO WARRANTY.')
    print('This is free software, and you are welcome to redistribute it')
    print("under certain conditions; type `backintime --license' for details.")
    print('')

class PseudoAliasAction(argparse.Action):
    '''translate '--COMMAND' into 'COMMAND' for backwards compatibility.
    '''
    def __call__(self, parser, namespace, values, option_string=None):
        '''translate '--COMMAND' into 'COMMAND' for backwards compatibility.

        parser:
        namespace:
        values:
        option_string:
        '''
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
    '''call commands which where given with leading -- for backwards
    compatibility.

    args:   argparse.ArgumentParser instance
    '''
    logger.info("Run command '%(alias)s' instead of argument '%(replace)s' due to backwards compatibility."
                % {'alias': args.alias, 'replace': args.replace})
    argv = [w.replace(args.replace, args.alias) for w in sys.argv[1:]]
    newArgs = arg_parse(argv)
    if 'func' in dir(newArgs):
        newArgs.func(newArgs)

def getConfig(args, check = True):
    '''load config and change to profile selected on commandline.

    args:   argparse.ArgumentParser instance
    check:  if there is no valid config call sys.exit
    '''
    cfg = config.Config(args.config)
    logger.debug('config file: %s' % cfg._LOCAL_CONFIG_PATH)
    logger.debug('profiles: %s' % cfg.get_profiles())
    if 'profile_id' in args and args.profile_id:
        if not cfg.set_current_profile(args.profile_id):
            logger.error('Profile-ID not found: %s' % args.profile_id)
            sys.exit(RETURN_ERR)
    if 'profile' in args and args.profile:
        if not cfg.set_current_profile_by_name(args.profile):
            logger.error('Profile not found: %s' % args.profile)
            sys.exit(RETURN_ERR)
    if check and not cfg.is_configured():
        logger.error('%(app)s is not configured!' %{'app': cfg.APP_NAME})
        sys.exit(RETURN_NO_CFG)
    if 'checksum' in args:
        cfg.force_use_checksum = args.checksum
    return cfg

def setQuiet(args):
    '''redirect sys.stdout to /dev/null if --quiet was set on commandline.
    Return the original sys.stdout fileobject which can be used to print
    absolute necessary information.

    args:   argparse.ArgumentParser instance
    '''
    force_stdout = sys.stdout
    if args.quiet:
        sys.stdout = open(os.devnull, 'w')
    return force_stdout

class printLicense(argparse.Action):
    '''print custom license
    '''
    def __init__(self, *args, **kwargs):
        super(printLicense, self).__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        cfg = config.Config()
        print(cfg.get_license())
        sys.exit(RETURN_OK)

def backup(args, force = True):
    '''command for taking a new snapshot.

    force:  take the snapshot even if it wouldn't need to or would be
    args:   argparse.ArgumentParser instance
            prevented (e.g. running on battery)
    '''
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    ret = take_snapshot(cfg, force)
    sys.exit(int(not ret))

def backupJob(args):
    '''command for force taking a new snapshot.

    args:   argparse.ArgumentParser instance
    '''
    cli.BackupJobDaemon(backup, args).start()

def snapshotsPath(args):
    '''command for printing the full snapshot path of current profile.

    args:   argparse.ArgumentParser instance
    '''
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    if args.keep_mount:
        _mount(cfg)
    print('SnapshotsPath: %s' % cfg.get_snapshots_full_path(), file=force_stdout)
    sys.exit(RETURN_OK)

def snapshotsList(args):
    '''command for printing a list of all snapshots in current profile.

    args:   argparse.ArgumentParser instance
    '''
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    s = snapshots.Snapshots(cfg)
    snapshots_list = s.get_snapshots_list()
    if snapshots_list:
        for snapshot_id in snapshots_list:
            print('SnapshotID: %s' % snapshot_id, file=force_stdout)
    else:
        logger.error("There are no snapshots in '%s'" % cfg.get_profile_name())
    if not args.keep_mount:
        _umount(cfg)
    sys.exit(RETURN_OK)

def snapshotsListPath(args):
    '''command for printing a list of all snapshots pathes in current profile.

    args:   argparse.ArgumentParser instance
    '''
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    s = snapshots.Snapshots(cfg)
    snapshots_list = s.get_snapshots_list()
    if snapshots_list:
        for snapshot_id in snapshots_list:
            print('SnapshotPath: %s' % s.get_snapshot_path(snapshot_id), file=force_stdout)
    else:
        logger.error("There are no snapshots in '%s'" % cfg.get_profile_name())
    if not args.keep_mount:
        _umount(cfg)
    sys.exit(RETURN_OK)

def lastSnapshot(args):
    '''command for printing the very last snapshot in current profile.

    args:   argparse.ArgumentParser instance
    '''
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    s = snapshots.Snapshots(cfg)
    snapshots_list = s.get_snapshots_list()
    if snapshots_list:
        print('SnapshotID: %s' % snapshots_list[0], file=force_stdout)
    else:
        logger.error("There are no snapshots in '%s'" % cfg.get_profile_name())
    _umount(cfg)
    sys.exit(RETURN_OK)

def lastSnapshotPath(args):
    '''command for printing the path of the very last snapshot in
    current profile.

    args:   argparse.ArgumentParser instance
    '''
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    s = snapshots.Snapshots(cfg)
    snapshots_list = s.get_snapshots_list()
    if snapshots_list:
        print('SnapshotPath: %s' % s.get_snapshot_path(snapshots_list[0]), file=force_stdout)
    else:
        logger.error("There are no snapshots in '%s'" % cfg.get_profile_name())
    if not args.keep_mount:
        _umount(cfg)
    sys.exit(RETURN_OK)

def unmount(args):
    '''command for unmounting all filesystems.

    args:   argparse.ArgumentParser instance
    '''
    setQuiet(args)
    cfg = getConfig(args)
    _mount(cfg)
    _umount(cfg)
    sys.exit(RETURN_OK)

def benchmarkCipher(args):
    '''command for transfering a file with scp to remote host with all
    available ciphers and print its speed and time.

    args:   argparse.ArgumentParser instance
    '''
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    if cfg.get_snapshots_mode() in ('ssh', 'ssh_encfs'):
        ssh = sshtools.SSH(cfg)
        ssh.benchmark_cipher(args.FILE_SIZE)
        sys.exit(RETURN_OK)
    else:
        logger.error("SSH is not configured for profile '%s'!" % cfg.get_profile_name())
        sys.exit(RETURN_ERR)

def pwCache(args):
    '''command for starting password cache daemon.

    args:   argparse.ArgumentParser instance
    '''
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
    '''command for decoding pathes given pathes with 'encfsctl'.
    Will listen on stdin if no path was given.

    args:   argparse.ArgumentParser instance
    '''
    force_stdout = setQuiet(args)
    cfg = getConfig(args)
    if cfg.get_snapshots_mode() not in ('local_encfs', 'ssh_encfs'):
        logger.error("Profile '%s' is not encrypted." % cfg.get_profile_name())
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
    '''command for removing snapshots.

    args:   argparse.ArgumentParser instance
    force:  don't ask before removing (BE CAREFUL!)
    '''
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    _mount(cfg)
    cli.remove(cfg, args.SNAPSHOT_ID, force)
    _umount(cfg)
    sys.exit(RETURN_OK)

def removeAndDoNotAskAgain(args):
    '''command for removing snapshots without asking before remove
    (BE CAREFUL!)

    args:   argparse.ArgumentParser instance
    '''
    remove(args, True)

def restore(args):
    '''command for restoring files from snapshots.

    args:   argparse.ArgumentParser instance
    '''
    setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    _mount(cfg)
    cli.restore(cfg,
                args.SNAPSHOT_ID,
                args.WHAT,
                args.WHERE,
                delete = args.delete,
                backup = args.local_backup,
                no_backup = args.no_local_backup)
    _umount(cfg)
    sys.exit(RETURN_OK)

def checkConfig(args):
    '''command for checking the config file.

    args:   argparse.ArgumentParser instance
    '''
    force_stdout = setQuiet(args)
    printHeader()
    cfg = getConfig(args)
    if cli.checkConfig(cfg, crontab = not args.no_crontab):
        print("\nConfig %(cfg)s profile '%(profile)s' is fine."
              % {'cfg': cfg._LOCAL_CONFIG_PATH,
                 'profile': cfg.get_profile_name()},
              file = force_stdout)
        sys.exit(RETURN_OK)
    else:
        print("\nConfig %(cfg)s profile '%(profile)s' has errors."
              % {'cfg': cfg._LOCAL_CONFIG_PATH,
                 'profile': cfg.get_profile_name()},
              file = force_stdout)
        sys.exit(RETURN_ERR)

if __name__ == '__main__':
    start_app()
