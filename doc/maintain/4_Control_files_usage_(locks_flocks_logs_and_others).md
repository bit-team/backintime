# Usage of control files in _Back In Time_ (developer documentation)

Table of contents:

* [TLDR ;-)](#tldr--)
* [_Back In Time_ commands that use lock files](#back-in-time-commands-that-use-lock-files)
   + [`backup`](#backup)
   + [`restore`](#restore)
   + [`shutdown`](#shutdown)
* [List of known control files](#list-of-known-control-files)
   + [GUI (application) lock files (`app.lock.pid`)](#gui-application-lock-files-applockpid)
   + [Global flock file `/tmp/backintime.lock`](#global-flock-file-tmpbackintimelock)
   + [Backup lock files (`worker<Profile ID>.lock.flock`)](#backup-lock-files-workerprofile-idlockflock)
   + [Backup progress file (`worker<PID>.progress`)](#backup-progress-file-workerpidprogress)
   + [`takesnapshot_<profile ID>.log`](#takesnapshot_profile-idlog)
   + [`restore_<profile ID>.log`](#restore_profile-idlog)
   + [Raise file (`app.lock.raise`)](#raise-file-applockraise)
   + [`save_to_continue` flag file in new snapshots](#save_to_continue-flag-file-in-new-snapshots)
   + [Restore lock file (`restore<Profile ID>.lock`)](#restore-lock-file-restoreprofile-idlock)
* [See also](#see-also)
   + [_Back in Time_ FAQ](#back-in-time-faq)
   + [Linux advisory locks](#linux-advisory-locks)

Notes:

- The logic is based on the the source code of
  [_Back In Time_ v1.4.1](https://github.com/bit-team/backintime/releases/tag/v1.4.1)
  and all source code references point to v1.4.1.
  The code may look differently and even the logic may have been changed
  in later versions.

- Tables in this markdown file are generated using https://www.tablesgenerator.com/markdown_tables
  with `Line breaks as "br"` enabled.

- Whenever `<Profile ID>` is mentioned it means the profile number of the configuration.
  **For the profile ID 1 no number is used but an empty string**
  (why this confusing exception is made is unclear).



## TLDR ;-)

_Back In Time_ uses control files to prevent that multiple instances
work in parallel and conflicts may occur (eg. taking a snapshot for the same
profile in two different processes).

The most important control file is `worker<Profile ID>.lock` which is used
to avoid starting the same backup twice in parallel.

The `<Profile ID>` is empty for the default profile (1).

It also uses another exclusively locked file named `worker<Profile ID>.lock.flock`
to serialize the access of checking for another running backup
of _Back In Time_.

_Back In Time_ does only start a new backup job (for the same profile)
if the control file does not exist.

Lock files are stored by default in the folder `~/.local/share/backintime` and
contain the process id (also known as PID - see `man ps`) and process name of
the running backup process.

The PID is used [to check if the process that created the
lock file is still running](https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/applicationinstance.py#L78-L79) and delete or overwrite the lock file
with a new instance.



## _Back In Time_ commands that use lock files

### `backup`

Takes a snapshot after checking that no other snapshot or restore is running at the same time:

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/snapshots.py#L713-L729

If a snapshot or restore is running a warning (not an error!) is issued and
**no** new snapshot is taken!

Another control file named `worker<Profile ID>.lock.flock` is used to serialize access to the `worker*.lock` file
**before** a new one is created (via a “flock” = blocking advisory lock on the file).

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/applicationinstance.py#L47-L48

This table shows the control file focused execution sequence of the [`snapshots.py#backup()` function](https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/snapshots.py#L680):

| Step | worker<Profile ID>.lock.flock                                                                                    | worker<Profile ID>.lock                                   | restore<Profile ID>.lock.flock                                                                                    | restore<profile ID>.lock                                   | /tmp/backintime.lock                                                                                                                                                                       | Other actions                            | Relevant code snippets                                                                                                                                                                                                                                                                                                                                                                           |
|------|------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|      | Control file to serialize access to the `worker*.lock` file (via a “flock” = blocking advisory lock on the file) | Control file to indicate a running backup                 | Control file to serialize access to the `restore*.lock` file (via a “flock” = blocking advisory lock on the file) | Control file to indicate a running restore                 | Global control file to prevent running backups or restores on multiple snapshots from different profiles or users at the same time (only if `global.use_flock` option is `True` in config) | Executed logic not related to lock files | Taken from the source code of BiT v1.4.1                                                                                                                                                                                                                                                                                                                                                         |
| 1    | Create file and set flock                                                                                        |                                                           |                                                                                                                   |                                                            |                                                                                                                                                                                            |                                          | instance = ApplicationInstance(self.config.takeSnapshotInstanceFile(), False, flock = True)                                                                                                                                                                                                                                                                                                      |
| 2    |                                                                                                                  |                                                           |                                                                                                                   |                                                            |                                                                                                                                                                                            |                                          | restore_instance = ApplicationInstance(self.config.restoreInstanceFile(), False)                                                                                                                                                                                                                                                                                                                 |
| 3    |                                                                                                                  | Check if exists:<br>→ Yes: Exit without taking a snapshot |                                                                                                                   |                                                            |                                                                                                                                                                                            |                                          | instance.check() == not True?                                                                                                                                                                                                                                                                                                                                                                    |
| 4    |                                                                                                                  |                                                           |                                                                                                                   | Check if exists:<br>-> Yes: Exit without taking a snapshot |                                                                                                                                                                                            |                                          | restore_instance.check() == not True?                                                                                                                                                                                                                                                                                                                                                            |
| 5    |                                                                                                                  | Create file                                               |                                                                                                                   |                                                            |                                                                                                                                                                                            |                                          | instance.startApplication()                                                                                                                                                                                                                                                                                                                                                                      |
| 6    | Release flock and delete file                                                                                    |                                                           |                                                                                                                   |                                                            |                                                                                                                                                                                            |                                          | self.flockUnlock()  # within startApplication()                                                                                                                                                                                                                                                                                                                                                  |
| 7    |                                                                                                                  |                                                           |                                                                                                                   |                                                            | Create file and set flock                                                                                                                                                                  |                                          | self.flockExclusive()  # global flock to block backups from other profiles or users (and run them serialized)                                                                                                                                                                                                                                                                                    |
| 8    |                                                                                                                  |                                                           |                                                                                                                   |                                                            |                                                                                                                                                                                            | Take the snapshot using rsync            | self.takeSnapshot(sid, now, include_folders)                                                                                                                                                                                                                                                                                                                                                     |
| 9    |                                                                                                                  |                                                           |                                                                                                                   |                                                            |                                                                                                                                                                                            | Perform user-callback calls              | In case of errors call eg.<br>self.config.PLUGIN_MANAGER.error(5, msg)  # no snapshot and errors<br>self.config.PLUGIN_MANAGER.error(6, sid.displayID) # snapshot with errors<br>If a new snapshot was taken (complete or incomplete due to errors):<br>self.config.PLUGIN_MANAGER.newSnapshot(sid, sid.path()) #new snapshot  (if taken)<br>Finally:<br>self.config.PLUGIN_MANAGER.processEnd() |
| 10   |                                                                                                                  | Delete file                                               |                                                                                                                   |                                                            |                                                                                                                                                                                            |                                          | instance.exitApplication()                                                                                                                                                                                                                                                                                                                                                                       |
| 11   |                                                                                                                  |                                                           |                                                                                                                   |                                                            | Release flock and delete file                                                                                                                                                              |                                          | self.flockRelease()                                                                                                                                                                                                                                                                                                                                                                              |



### `restore`

Before restoring one or more files from a snapshot _Back In Time_ checks
if a restore is already running (using the restore lock file `restore<Profile ID>.lock`)
and exits with a warning (**not an error!**).

This table shows the control file focused execution sequence of the [`snapshots.py#restore()` function](https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/snapshots.py#L416:

| Step | worker<Profile ID>.lock.flock                                                                                    | worker<Profile ID>.lock                   | restore<Profile ID>.lock.flock                                                                                    | restore<profile ID>.lock                                       | /tmp/backintime.lock                                                                                                                                                                       | Other actions                            | Relevant code snippets                                                                                |
|------|------------------------------------------------------------------------------------------------------------------|-------------------------------------------|-------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|-------------------------------------------------------------------------------------------------------|
|      | Control file to serialize access to the `worker*.lock` file (via a “flock” = blocking advisory lock on the file) | Control file to indicate a running backup | Control file to serialize access to the `restore*.lock` file (via a “flock” = blocking advisory lock on the file) | Control file to indicate a running restore                     | Global control file to prevent running backups or restores on multiple snapshots from different profiles or users at the same time (only if `global.use_flock` option is `True` in config) | Executed logic not related to lock files | Taken from the source code of BiT v1.4.1                                                              |
| 1    |                                                                                                                  |                                           | Create file and set flock                                                                                         |                                                                |                                                                                                                                                                                            |                                          | instance = ApplicationInstance(pidFile=self.config.restoreInstanceFile(), autoExit=False, flock=True) |
| 2    |                                                                                                                  |                                           |                                                                                                                   | Check if exists:<br>→ Yes: Exit without restoring the snapshot |                                                                                                                                                                                            |                                          | instance.check() == not True?                                                                         |
| 3    |                                                                                                                  |                                           |                                                                                                                   | Create file                                                    |                                                                                                                                                                                            |                                          | instance.startApplication()                                                                           |
| 4    |                                                                                                                  |                                           | Release flock and delete file                                                                                     |                                                                |                                                                                                                                                                                            |                                          | self.flockUnlock()  # within startApplication()                                                       |
| 5    |                                                                                                                  |                                           |                                                                                                                   |                                                                |                                                                                                                                                                                            | Restore the snapshot using rsync         | proc = tools.Execute(cmd […]                                                                          |
| 6    |                                                                                                                  |                                           |                                                                                                                   | Delete file                                                    |                                                                                                                                                                                            |                                          | instance.exitApplication()                                                                            |



### `shutdown`

This command shuts down the computer after the current snapshot has finished.
It polls the worker lock file to recognize running backups.

It is implemented in the function `backintime.py#shutdown()`:

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/backintime.py#L805-L819

This table shows the control file focused execution sequence of the function:

| Step | worker<Profile ID>.lock.flock                                                                                    | worker<Profile ID>.lock                                   | restore<Profile ID>.lock.flock                                                                                    | restore<profile ID>.lock                   | /tmp/backintime.lock                                                                                                                                                                       | Other actions                                           | Relevant code snippets                                                                              |
|------|------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|--------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
|      | Control file to serialize access to the `worker*.lock` file (via a “flock” = blocking advisory lock on the file) | Control file to indicate a running backup                 | Control file to serialize access to the `restore*.lock` file (via a “flock” = blocking advisory lock on the file) | Control file to indicate a running restore | Global control file to prevent running backups or restores on multiple snapshots from different profiles or users at the same time (only if `global.use_flock` option is `True` in config) | Executed logic not related to lock files                | Taken from the source code of BiT v1.4.1                                                            |
| 1    |                                                                                                                  |                                                           |                                                                                                                   |                                            |                                                                                                                                                                                            | Prepare lock file checking (without using a flock file) | instance = ApplicationInstance(cfg.takeSnapshotInstanceFile()                                       |
| 2    |                                                                                                                  | Check if exists:<br>→ No: Exit (no active snapshot)       |                                                                                                                   |                                            |                                                                                                                                                                                            |                                                         | if not instance.busy():    logger.info('There is no active snapshot for profile %s. Skip shutdown.' |
| 3    |                                                                                                                  | Check if exists:<br>→ Yes: Wait 5 seconds and check again |                                                                                                                   |                                            |                                                                                                                                                                                            |                                                         | while instance.busy():    logger.debug('Snapshot is still active. Wait for shutdown.')    sleep(5)  |
| 4    |                                                                                                                  |                                                           |                                                                                                                   |                                            |                                                                                                                                                                                            | shutdown computer                                       | sd.shutdown()                                                                                       |



## List of known control files

### GUI (application) lock files (`app.lock.pid`)

An **application lock file** named `app.lock.pid` is used for the _Back In Time_ application (GUI) 
to avoid starting more than one instance of the application (GUI) for the same user.

The name and path of the application lock file  is defined in two locations
(which should be refactored into one single place).

Path and base file name in `config.py#appInstanceFile()`:

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/config.py#L1369-L1370

The file extension `.pid` is added in `guiapplicationinstance.py#__init__()`:

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/guiapplicationinstance.py#L35



### Global flock file `/tmp/backintime.lock`

You can prevent taking multiple snapshots from different profiles or users to be
run at the same time.

BiT has a global configuration option for that named `global.use_flock` (see `man backintime-config`)
which can also be set in the GUI in the `Options` tab of the `Manage profiles` dialog.
It is named `Run only one snapshot at a time`.

Other snapshots will be blocked until the current snapshot is done.
This is a global option. So it will affect all profiles **for this user**.
But you need to activate this for every other user too
if you want enable this option for all users.

Technically a global flock file  ("flock") `/tmp/backintime.lock` is created
(with an advisory lock to serialize access):

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/config.py#L1356-L1358



### Backup lock files (`worker<Profile ID>.lock.flock`)

The name and path of the worker process lock file for running snapshots is defined in
`config.py#takeSnapshotInstanceFile()`:

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/config.py#L1388-L1391

Only for the default profile ID (1) no number is used resulting in `worker.lock`
(why this confusing exception is made is unclear):

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/config.py#L1372-L1377



### Backup progress file (`worker<PID>.progress`)

_Back In Time_ starts `rsync` as separate process.
To read the progress, errors and results of `rsync` a `worker<PID>.progress' file
is used (written by `rsync` and read + filtered by _Back In Time_):

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/snapshots.py#L858



### `takesnapshot_<profile ID>.log`

TODO



### `restore_<profile ID>.log`

TODO



### Raise file (`app.lock.raise`)

TODO (what is the purpose of this?)

Defined:
https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/guiapplicationinstance.py#L32-L33

Called via timer:
https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/qt/app.py#L389-L393

RaiseCMD passed in the main() entry point:
https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/qt/app.py#L1979



### `save_to_continue` flag file in new snapshots

This flag file is set for new snapshots initially.

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/snapshots.py#L2749-L2763

In `snapshots.py#takeSnapshot()` it is then decided if the existing snapshot can be used to "continue"
taking a snapshot or to delete the contained files and restart taking the snapshot:

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/snapshots.py#L1140-L1166

TODO How exactly does this work? Could we use this to implement a "retry" feature for failed snapshots?



### Restore lock file (`restore<Profile ID>.lock`)

The name and path of the restore process lock file `restore<Profile ID>.lock`
for running restores is defined in

`config.py#restoreInstanceFile()`:

https://github.com/bit-team/backintime/blob/25c2115b42904ec4a4aee5ba1d73bd97cb5d8b31/common/config.py#L1444-L1447

The flock file to serialize write access to the lock file (via a blocking advisory lock on the file)
is different from the backup flock file: `restore<Profile ID>.lock.flock`



## See also

### _Back in Time_ FAQ

The [FAQ](https://github.com/bit-team/backintime/blob/dev/FAQ.md) gives answers
for some problems caused by lock files.



### Linux advisory locks

See `man 2 fcntl` and https://linuxhandbook.com/file-locking/

> 1.  Advisory Locking
>
> The advisory locking system will not force the forces and will only work if both processes are participating in locking.
> For example, process A acquires the lock and starts given tasks with a file.
> And if process B starts without acquiring a lock, it can interrupt the ongoing task with process A.
> So the condition for making an advisory lock is to ensure each process participates in locking.
> the flock command which allows users to handle tasks related to advisory locking
