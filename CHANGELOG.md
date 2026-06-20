<!---
SPDX-FileCopyrightText: © 2023 Christian BUHTZ <c.buhtz@posteo.jp>

SPDX-License-Identifier: GPL-2.0-or-later

This file is part of the program "Back In Time" which is released under GNU
General Public License v2 (GPLv2). See LICENSES directory or go to
<https://spdx.org/licenses/GPL-2.0-or-later.html>
-->
# Changelog
[![Common Changelog](https://common-changelog.org/badge.svg)](https://common-changelog.org)
## [2.0.0] (Unreleased Development)

### Changed
 
- **Rewritten from scratch**: Mount subsystem (backend and encryption).
  Behavior is intended to remain unchanged; regressions cannot be fully ruled
  out. ([PR#2449](https://github.com/bit-team/backintime/pull/2449))
- **Breaking**: Minimal Python version 3.13 increased
- Default mountpoint permissions changed from 700 to 711
  ([PR#2451](https://github.com/bit-team/backintime/pull/2451)) to avoid
  FUSE mount failures when accessing via different user contexts.
- Changelog migrated to _Common Changelog_ standard
- Build: Changelog shipped as HTML
- GUI: Improved import config dialog on first start (Dominic Maluski, @maluskid, [#2483](https://github.com/bit-team/backintime/issues/2483))
- Expert Options: Deprecate and warn about disabled SSH remote checks
  if one of these two options is (non-default) disabled: "Check if remote host
  is online", "Check if remote host supports all necessary commands"
  ([#2482](https://github.com/bit-team/backintime/issues/2482))
- Clear up license and copyright situation of `qt/serviceHelper.py`
  ([#1986](https://github.com/bit-team/backintime/issues/1986))
- GUI: Schedule mode "Repeatedly (anacron)" re-phrased and extended with
  explanations ([#2507](https://github.com/bit-team/backintime/issues/2507))

### Added
- Gocryptfs for SSH encrypted profiles
  ([PR#2486](https://github.com/bit-team/backintime/pull/2486))
- Dependencies:
  - build: `pandoc` to convert markdown changelog into HTML
  - runtime-cli: `gocryptfs`

### Removed
- **Breaking**: EncFS support including existing EncFS profiles
  ([PR#2492](https://github.com/bit-team/backintime/pull/2492))
- **Breaking**: Global config file support
  ([PR#2493](https://github.com/bit-team/backintime/issues/2493))
- Dependency: `encfs`
- CLI:
  - Switch `--keep-mount`
  - Command `decode` because of EncFS removal ([#1734](https://github.com/bit-team/backintime/issues/1734))
  - Command `benchmark-cipher` ([#2120](https://github.com/bit-team/backintime/issues/2120))
- SSH Cipher ([#2176](https://github.com/bit-team/backintime/issues/2176))
- Config examples
- Languages Faroese, Croatian, Vietnames and Norwegian (Nynorsk)
  ([#2080](https://github.com/bit-team/backintime/issues/2080))
- GUI Expert Options:
  - "Check if remote host is online" ([#2482](https://github.com/bit-team/backintime/issues/2482)).
  - "Check if remote host supports all necessary commands" ([#2482](https://github.com/bit-team/backintime/issues/2482)).
- Test targets in Makefiles. Use a regular Python test runner (e.g. pytest) instead.

## Fixed
- **Breaking**: "Remove backups older than" value was stored only as years ([#2460](https://github.com/bit-team/backintime/issues/2460))
- Prevent crash in case a plugin fails ([#2447](https://github.com/bit-team/backintime/issues/2447))
- Include SSH_AUTH_SOCK in cron environment to enable SSH agent access (Dan Kortschak, [@kortschak](https://github.com/kortschak), [#2506](https://github.com/bit-team/backintime/issues/2506))
- Schedule mode "Repeatedly" using "Hourly" units is now consistent with other units ([#2507](https://github.com/bit-team/backintime/issues/2507))
- Crash when use Btrfs-subvolume as backup destination (Daidalos [@D4id4los](https://github.com/D4id4los), [#2487](https://github.com/bit-team/backintime/issues/2487))

## [1.6.1] (2026-02-10)

### Fixed

- SSH-Key selector widget handle binary keys, missing but configured keys ([#2399](https://github.com/bit-team/backintime/issues/2399), [#2400](https://github.com/bit-team/backintime/issues/2400))
- SSH-Key selector widget is more robust on unexpected edge cases ([#2399](https://github.com/bit-team/backintime/issues/2399), [#2400](https://github.com/bit-team/backintime/issues/2400))
- Install backintime-config man page in correct location

## [1.6.0] (2026-02-08)

### Changed

- **Breaking** Disable EncFS for creation of new backup profiles ([#2315](https://github.com/bit-team/backintime/issues/2315), [#1734](https://github.com/bit-team/backintime/issues/1734))
- **Breaking** A "snapshot" now is a "backup" ([#1929](https://github.com/bit-team/backintime/issues/1929))
- **Breaking** Deprecated and removed make targets: "test", "test-v", "unittest", "unittest-v"
- Manpage backintime-config moved from section 1 to 5 ([#1773](https://github.com/bit-team/backintime/issues/1773))
- New dependency "bash" for root mode starter script "backintime-qt_polkit" ([#2328](https://github.com/bit-team/backintime/issues/2328))
- New dependency (runtime GUI) to "python3-pyqt6.qtsvg" for loading SVG icons ([#1961](https://github.com/bit-team/backintime/issues/1961))
- Disable scheduling widget in GUI if cron/crontab is missing ([#2245](https://github.com/bit-team/backintime/issues/2245), [@m4rcu5](https://github.com/m4rcu5) Marcus von Dam)
- Expert Options replaced two checkboxes with single widget to configure symlink copying behavior ([#1652](https://github.com/bit-team/backintime/issues/1652))
- "Repeatedly (anacron)" scheduling behave consistent. Reversed minor bug introduced with 060324e ([#1791](https://github.com/bit-team/backintime/issues/1791)) in 1.5.3 ([#2250](https://github.com/bit-team/backintime/issues/2250))
- Stricter permissions (600) for fileinfo.bz2 and takesnapshot.log.bz2 ([#2235](https://github.com/bit-team/backintime/issues/2235))
- Unlocking ssh-agent use "force" instead of "prefer" for SSH_ASKPASS_REQUIRE ([#2170](https://github.com/bit-team/backintime/issues/2170)) ([@daviewales](https://github.com/daviewales))
- Stop passing window ID when inhibiting suspend via D-Bus power manager ([#2084](https://github.com/bit-team/backintime/issues/2084))
- Reorder DBUS service provider list for suspend mode inhibition ([#2084](https://github.com/bit-team/backintime/issues/2084))
- Man pages generated from AsciiDoc, except backintime-config ([#2085](https://github.com/bit-team/backintime/issues/2085))
- Deprecate command "benchmark-cipher" ([#2120](https://github.com/bit-team/backintime/issues/2120))
- Deprecate command "snapshots-path" ([#2130](https://github.com/bit-team/backintime/issues/2130))
- Deprecate commands "snapshots-list", "snapshots-list-path", "last-snapshots" and "last-snapshot-path" ([#2130](https://github.com/bit-team/backintime/issues/2130))
- Deprecate command "smart-remove" ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Deprecate command "backup-job" ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Deprecate command "remove-and-do-not-ask-again" ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Deprecate command "decode" ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Deprecate flag-like command aliases (e.g. "--backup" for "backup") ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Deprecate argument flag "--profile-id" ([#2125](https://github.com/bit-team/backintime/issues/2125))
- Deprecate argument flag "--share-path" ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Deprecate use of SSH Cipher ([#2143](https://github.com/bit-team/backintime/issues/2143))
- Prefer ed25519 SSH keys (if present) for new created profiles ([#2094](https://github.com/bit-team/backintime/issues/2094))
- Generating new SSH key will use default key type provided by ssh-keygen ([#2194](https://github.com/bit-team/backintime/issues/2194))
- Open man page and changelog in a text dialog
- Minimum PyLint version increased to 4.0.0

### Added

- Language Georgian (ka)
- Gocryptfs for local encrypted profiles ([#1897](https://github.com/bit-team/backintime/issues/1897), [#1734](https://github.com/bit-team/backintime/issues/1734), [@germar](https://github.com/germar), [@daviewales](https://github.com/daviewales))
- Dialog to suggest commonly used files/dirs/patterns for backup exclusion ([#2309](https://github.com/bit-team/backintime/issues/2309))
- Systray icon can be forced to Dark or Light
- Application logo and symbolic systray icon ([#1961](https://github.com/bit-team/backintime/issues/1961), Gregory Deseck [@gregorydk](https://github.com/gregorydk))
- Root mode indicator in status bar ([#1964](https://github.com/bit-team/backintime/issues/1964))
- Option to not using an explicit SSH key file. In consequence this supports extern key agents and SSH clients own configuration ([#1146](https://github.com/bit-team/backintime/issues/1146))
- SSH-Key selector widget in Manage profiles dialog ([#1146](https://github.com/bit-team/backintime/issues/1146), [#2094](https://github.com/bit-team/backintime/issues/2094), [#2095](https://github.com/bit-team/backintime/issues/2095), [#2275](https://github.com/bit-team/backintime/issues/2275) [@m4rcu5](https://github.com/m4rcu5) Marcus van Dam)
- "ETA" value in status bar ([#2101](https://github.com/bit-team/backintime/issues/2101))
- Shutdown confirmation dialog ([#2102](https://github.com/bit-team/backintime/issues/2102)) (Huaide Jiang [@LatiosInAltoMare](https://github.com/LatiosInAltoMare))
- Check and warn if include list entries do not exists in backup source ([#1586](https://github.com/bit-team/backintime/issues/1586)) ([@rafaelhdr](https://github.com/rafaelhdr))
- Asciidoctor as build dependence ([#2085](https://github.com/bit-team/backintime/issues/2085))
- Command "show" to replace "snapshots-list", "snapshots-list-path", "last-snapshots" and "last-snapshot-path" ([#2130](https://github.com/bit-team/backintime/issues/2130))
- Command "prune" to replace "smart-remove" ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Flag "--background" for command "backup" to replace command "backup-job" ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Flag "--skip-confirmation" for command "remove" to replace command "remove-and-do-not-ask-again" ([#2124](https://github.com/bit-team/backintime/issues/2124))
- Flag "--profile" accept ID's beside names only ([#2125](https://github.com/bit-team/backintime/issues/2125))
- Flag "-p" as alias for "--profile" ([#2125](https://github.com/bit-team/backintime/issues/2125))
- "Less storage space" threshold to warn the user ([#2110](https://github.com/bit-team/backintime/issues/2110)) ([@fest6](https://github.com/fest6))
- Remember size and position of Manage profiles dialog
- User-callback editor offer a default script in case no script exists ([#1331](https://github.com/bit-team/backintime/issues/1331))

### Removed

- **Breaking** Drop Python support for version 3.9 & 3.10 ([#2129](https://github.com/bit-team/backintime/issues/2129))
- Stop using QWindow.winId() ([#2084](https://github.com/bit-team/backintime/issues/2084))
- UI translation in Bosnian, Thai, and Occidental/Interlingue ([#1914](https://github.com/bit-team/backintime/issues/1914))
- LICENSE file in favor of LICENSES directory and LICENSES.md file
- SSH Cipher configuration in Manage profiles dialog ([#2143](https://github.com/bit-team/backintime/issues/2143))

### Fixed

- Crash in config restore dialog
- Consider symbolic icons as fallbacks ([#2345](https://github.com/bit-team/backintime/issues/2345), [#2289](https://github.com/bit-team/backintime/issues/2289))
- Warn users and prevent backups to exFAT volumes due to lack of hardlink support ([#2337](https://github.com/bit-team/backintime/issues/2337))
- Show proper message to users when root mode fails due to inactive or missing polkit agent ([#2328](https://github.com/bit-team/backintime/issues/2328), Derek Veit [@DerekVeit](https://github.com/DerekVeit))
- Crash in Compare snapshots dialog (aka Snapshots dialog) when comparing/diff two backups ([#2327](https://github.com/bit-team/backintime/issues/2327) Michael Neese [@madic-creates](https://github.com/madic-creates))
- File view and Compare Backups dialog now open the clicked item correctly even with multiple selection or single-click-to-open enabled ([#2330](https://github.com/bit-team/backintime/issues/2330))
- Crash in Compare snapshots dialog (aka Snapshots dialog) when comparing/diff two backups ([#2327](https://github.com/bit-team/backintime/issues/2327) Michael Neese [@madic-creates](https://github.com/madic-creates))
- Enforce UTF-8 encoding in takesnapshot.log and some other files ([#2298](https://github.com/bit-team/backintime/issues/2298))
- Attribute error about missing 'cbCopyUnsafeLinks' ([#2279](https://github.com/bit-team/backintime/issues/2279))
- Use LC_ALL instead of LC_TIME to set the locale
- Optimize subparsers and usage output ([#2132](https://github.com/bit-team/backintime/issues/2132))
- Re-design about dialog ([#1936](https://github.com/bit-team/backintime/issues/1936))
- Stop waking up monitor when inhibit suspend on backup starts ([#714](https://github.com/bit-team/backintime/issues/714), [#1090](https://github.com/bit-team/backintime/issues/1090))
- Avoid shutdown confirmation dialog on Budgie and Cinnamon desktop environments ([#788](https://github.com/bit-team/backintime/issues/788))
- Crash in "Manage profiles" dialog when using "qt6ct" ([#2128](https://github.com/bit-team/backintime/issues/2128))
- **Breaking** Systray process no longer exposes sensitive backup profile information when the desktop session belongs to another user ([#2237](https://github.com/bit-team/backintime/issues/2237), reported and co-authored by [@samo-sk](https://github.com/samo-sk))
- Allow in BITs root-mode opening URLs in extern browse

## [1.5.6] (2025-10-05)

### Fixed

- Always use 0 as window ID value when inhibiting suspend via D-Bus power manager ([#2084](https://github.com/bit-team/backintime/issues/2084), [#2268](https://github.com/bit-team/backintime/issues/2268), [#2192](https://github.com/bit-team/backintime/issues/2192))
- Crash in "Manage profiles" dialog when using "qt6ct" ([#2128](https://github.com/bit-team/backintime/issues/2128))
- Open online changelog if local CHANGES file is missing ([#2266](https://github.com/bit-team/backintime/issues/2266))
- Disable opening browser (e.g. project website) in root-mode

## [1.5.5] (2025-06-05)

### Fixed

- Unlocking SSH keys with passphrases on new created profiles ([#2164](https://github.com/bit-team/backintime/issues/2164)) ([@davidfjoh](https://github.com/davidfjoh))

## [1.5.4] (2025-03-24)

### Uncategorized

- Breaking Change: Auto-remove rules "Free inodes" and "Free space" disabled by default in new created profiles ([#1976](https://github.com/bit-team/backintime/issues/1976))
- Fix!: Smart-remove rule "Keep one snapshots per week or the last week" use calendar weeks
- Doc: Remove & Retention (formally known as Auto-/Smart-Remove) with improved GUI and user manual section ([#2000](https://github.com/bit-team/backintime/issues/2000))

### Changed

- Completed license information to conform to REUSE.software and SPDX standards.
- More clear and intense warning about EncFS deprecation and removal ([#1904](https://github.com/bit-team/backintime/issues/1904))
- Updated desktop entry files
- Move several values from config file into new introduce state file ($XDG_STATE_HOME/backintime.json)

### Fixed

- Exclude patterns are now case-sensitive when added ([#2040](https://github.com/bit-team/backintime/issues/2040))
- The width of the fourth column in files view is now saved
- Snapshot compare copy symlink as symlink ([#1902](https://github.com/bit-team/backintime/issues/1902)) (Peter Sevens [@sevens](https://github.com/sevens))
- Crash when comparing a snapshot with a symlink pointing to a nonexistent target (Peter Sevens [@sevens](https://github.com/sevens))
- Crash (KeyError) opening language setup dialog with unknown locale/language

### Added

- Open user manual (local if available otherwise online) via Help menu
- Toolbar context menu to display the buttons in different combinations with icons and text ([#1105](https://github.com/bit-team/backintime/issues/1105), [#2002](https://github.com/bit-team/backintime/issues/2002)) (Samuel Moore [@s4moore](https://github.com/s4moore))
- Add offset minutes to hourly schedules (David Gibbs [@fallingrock](https://github.com/fallingrock))

## [1.5.3] (2024-11-13)

### Uncategorized

- Doc: User manual (build with MkDocs) ([#1838](https://github.com/bit-team/backintime/issues/1838)) (Kosta Vukicevic [@stcksmsh](https://github.com/stcksmsh))
- Doc: User-callback topic in user manual ([#1659](https://github.com/bit-team/backintime/issues/1659))
- Refactor!: Remove unused config field "user_callback.no_logging" ([#1887](https://github.com/bit-team/backintime/issues/1887))
- Refactor!: Remove eCryptFS check for home folder ([#1855](https://github.com/bit-team/backintime/issues/1855))
- Build: Replace "pycodestyle" linter with "flake8" ([#1839](https://github.com/bit-team/backintime/issues/1839))

### Added

- Support language Interlingua (Occidental)
- Warn if destination directory is formatted as NTFS ([#1854](https://github.com/bit-team/backintime/issues/1854)) (David Gibbs [@fallingrock](https://github.com/fallingrock))
- Support fcron ([#610](https://github.com/bit-team/backintime/issues/610))
- User message about release candidate ([#1906](https://github.com/bit-team/backintime/issues/1906))

### Fixed

- Prevent duplicates in Exclude/Include list of Manage Profiles dialog
- Fix Qt segmentation fault when canceling out of unconfigured BiT ([#1095](https://github.com/bit-team/backintime/issues/1095)) (Derek Veit [@DerekVeit](https://github.com/DerekVeit))
- Correct global flock fallbacks ([#1834](https://github.com/bit-team/backintime/issues/1834)) (Timothy Southwick [@NickNackGus](https://github.com/NickNackGus))
- Use SSH key password only if it is valid, otherwise request it from user ([#1852](https://github.com/bit-team/backintime/issues/1852)) (David Wales [@daviewales](https://github.com/daviewales))

### Changed

- **Breaking**: Minimal Python version 3.9 required ([#1731](https://github.com/bit-team/backintime/issues/1731))
- **Breaking**: Auto migration of config version 4 or lower not longer supported ([#1857](https://github.com/bit-team/backintime/issues/1857))
- Dependency: Remove libnotify-bin (notify-send) ([#1156](https://github.com/bit-team/backintime/issues/1156))
- Dependency: PyFakeFS minimal version 5.6 ([#1911](https://github.com/bit-team/backintime/issues/1911))
- General tab and its Schedule section
- Own module for Manage Profiles dialog and separate Generals tab code ([#1865](https://github.com/bit-team/backintime/issues/1865))
- Remove class OrderedSet
- Remove os.system() from class Execute
- Systray notifications send utilize DBUS instead of notify-send ([#1156](https://github.com/bit-team/backintime/issues/1156)) (Felix Stupp [@Zocker1999NET](https://github.com/Zocker1999NET))

## [1.5.2] (2024-08-06)

### Fixed

- Ensure crontab with ending newline ([#781](https://github.com/bit-team/backintime/issues/781))

### Uncategorized

- Fix(translation): Correct corrupt translated strings in Basque, Islandic and Spanish causing application crashes ([#1828](https://github.com/bit-team/backintime/issues/1828))
- Build(translation): Language helper script processing syntax checks on po-files

## [1.5.1] (2024-07-27)

### Fixed

- Use correct port to ping SSH Proxy ([#1815](https://github.com/bit-team/backintime/issues/1815))

## [1.5.0] (2024-07-26)

### Uncategorized

- Dependency: Migration to PyQt6
- Breaking Change: EncFS deprecation warning ([#1735](https://github.com/bit-team/backintime/issues/1735), [#1734](https://github.com/bit-team/backintime/issues/1734))
- Breaking Change: GUI started with --debug does no longer add --debug to the crontab for scheduled profiles. 
- Chore!: Remove "debian" folder ([#1548](https://github.com/bit-team/backintime/issues/1548))
- Build: Enable several PyLint rules ([#1755](https://github.com/bit-team/backintime/issues/1755), [#1766](https://github.com/bit-team/backintime/issues/1766))
- Build: Add AppStream meta data ([#1642](https://github.com/bit-team/backintime/issues/1642))
- Build: PyLint unit test is skipped if PyLint isn't installed, but will always run on TravisCI ([#1634](https://github.com/bit-team/backintime/issues/1634))
- Build: Git commit hash is presevered while "make install" ([#1637](https://github.com/bit-team/backintime/issues/1637))
- Build: Fix bash-completion symlink creation while installing & adding --diagnostics ([#1615](https://github.com/bit-team/backintime/issues/1615))
- Build: TravisCI use PyQt (except arch "ppc64le")

### Added

- Warn if Cron is not running ([#1747](https://github.com/bit-team/backintime/issues/1747))
- Profile and GUI allow to activate debug output for scheduled jobs by adding '--debug' to crontab entry ([#1616](https://github.com/bit-team/backintime/issues/1616), contributed by [@stcksmsh](https://github.com/stcksmsh) Kosta Vukicevic)
- Support SSH proxy (jump) host ([#1688](https://github.com/bit-team/backintime/issues/1688)) ([@cgrinham](https://github.com/cgrinham), Christie Grinham)
- Support rsync '--one-file-system' in Expert Options ([#1598](https://github.com/bit-team/backintime/issues/1598))
- "*-dev" version strings contain last commit hash ([#1637](https://github.com/bit-team/backintime/issues/1637))

### Fixed

- Global flock fallback to single-user mode if insufficient permissions ([#1743](https://github.com/bit-team/backintime/issues/1743), [#1751](https://github.com/bit-team/backintime/issues/1751))
- Fix Qt segmentation fault with uninstall ExtraMouseButtonEventFilter when closing main window ([#1095](https://github.com/bit-team/backintime/issues/1095))
- Names of weekdays and months translated correct ([#1729](https://github.com/bit-team/backintime/issues/1729))
- Global flock for multiple users ([#1122](https://github.com/bit-team/backintime/issues/1122), [#1676](https://github.com/bit-team/backintime/issues/1676))
- "Backup folders" list does reflect the selected snapshot ([#1585](https://github.com/bit-team/backintime/issues/1585)) ([@rafaelhdr](https://github.com/rafaelhdr) Rafael Hurpia da Rocha)
- Validation of diff command settings in compare snapshots dialog ([#1662](https://github.com/bit-team/backintime/issues/1662)) ([@stcksmsh](https://github.com/stcksmsh) Kosta Vukicevic)
- Open symlinked folders in file view ([#1476](https://github.com/bit-team/backintime/issues/1476))
- Respect dark mode using color roles ([#1601](https://github.com/bit-team/backintime/issues/1601))
- "Highly recommended" exclusion pattern in "Manage Profile" dialog's "Exclude" tab show missing only ([#1620](https://github.com/bit-team/backintime/issues/1620))
- `make install` ignored $(DEST) in file migration part ([#1630](https://github.com/bit-team/backintime/issues/1630))

### Removed

- Context menu in LogViewDialog ([#1578](https://github.com/bit-team/backintime/issues/1578))
- Field "filesystem_mount" and "snapshot_version" in "info" file ([#1684](https://github.com/bit-team/backintime/issues/1684))

### Changed

- Replace Config.user() with getpass.getuser() ([#1694](https://github.com/bit-team/backintime/issues/1694))

## [1.4.3] (2024-01-30)

### Added

- Exclude 'SingletonLock' and 'SingletonCookie' (Discord) and 'lock' (Mozilla Firefox) files by default (part of [#1555](https://github.com/bit-team/backintime/issues/1555))

### Uncategorized

- Work around: Relax `rsync` exit code 23: Ignore instead of error now (part of [#1587](https://github.com/bit-team/backintime/issues/1587))
- Feature (experimental): Add new snapshot log filter `rsync transfer failures (experimental)` to find them easier (they are normally not shown as "error").  
- Improve: Launcher for BiT GUI (root) does not enforce Wayland anymore but uses same settings as for BiT GUI (userland) ([#1350](https://github.com/bit-team/backintime/issues/1350))
- Change of semantics: BiT running as root never disables suspend during taking a backup ("inhibit suspend") even though this may have worked before in BiT <= v1.4.1 sometimes (required to fix [#1592](https://github.com/bit-team/backintime/issues/1592))
- Build: Use PyLint in unit testing to catch E1101 (no-member) errors.
- Build: Activate PyLint warning W1401 (anomalous-backslash-in-string).
- Build: Add codespell config.
- Build: Allow manual specification of python executable (--python=PYTHON_PATH) in common/configure and qt/configure
- Build: All starter scripts do use an absolute path to the python executable by default now via common/configure and qt/configure ([#1574](https://github.com/bit-team/backintime/issues/1574))
- Build: Install dbus configuration file to /usr/share not /etc ([#1596](https://github.com/bit-team/backintime/issues/1596))
- Build: `configure` does delete old installed files (`qt4plugin.py` and `net.launchpad.backintime.serviceHelper.conf`) that were renamed or moved in a previous release ([#1596](https://github.com/bit-team/backintime/issues/1596))
- Translation: Minor modifications in source strings and updating language files.
- Improved: qtsystrayicon.py, qt5_probing.py, usercallbackplugin.py and all parts of app.py 

### Fixed

- 'qt5_probing.py' hangs when BiT is run as root and no user is logged into a desktop environment ([#1592](https://github.com/bit-team/backintime/issues/1592) and [#1580](https://github.com/bit-team/backintime/issues/1580))
- Launching BiT GUI (root) hangs on Wayland without showing the GUI ([#836](https://github.com/bit-team/backintime/issues/836))
- Disabling suspend during taking a backup ("inhibit suspend") hangs when BiT is run as root and no user is logged into a desktop environment ([#1592](https://github.com/bit-team/backintime/issues/1592))
- RTE: module 'qttools' has no attribute 'initate_translator' with encFS when prompting the user for a password ([#1553](https://github.com/bit-team/backintime/issues/1553)).
- Schedule dropdown menu used "minutes" instead of "hours".
- Unhandled exception "TypeError: 'NoneType' object is not callable" in tools.py function __log_keyring_warning ([#820](https://github.com/bit-team/backintime/issues/820)). 

### Changed

- Solved circular dependency between tools.py and logger.py to fix [#820](https://github.com/bit-team/backintime/issues/820)

## [1.4.1] (2023-10-01)

### Uncategorized

- Dependency: Add "qt translations" to GUI runtime dependencies ([#1538](https://github.com/bit-team/backintime/issues/1538)).
- Build: Unit tests do generically ignore all instead of well-known warnings now ([#1539](https://github.com/bit-team/backintime/issues/1539)).
- Build: Warnings about missing Qt translation now are ignored while testing ([#1537](https://github.com/bit-team/backintime/issues/1537)).

### Fixed

- GUI didn't start when "show hidden files" button was on ([#1535](https://github.com/bit-team/backintime/issues/1535)).

## [1.4.0] (2023-09-14)

### Uncategorized

- Project: Renamed branch "master" to "main" and started "gitflow" branching model.
- GUI Change: View last (snapshot) log button in GUI uses "document-open-recent" icon now instead of "document-new" ([#1386](https://github.com/bit-team/backintime/issues/1386))
- Breaking change: Minimal Python version 3.8 required ([#1358](https://github.com/bit-team/backintime/issues/1358)).
- Documentation: Removed outdated docbook ([#1345](https://github.com/bit-team/backintime/issues/1345)).
- Testing: TravisCI now can use dbus
- Build: Introduced .readthedocs.yaml as asked by ReadTheDocs.org ([#1443](https://github.com/bit-team/backintime/issues/1443)).
- Dependency: The oxygen icons should be installed with the BiT Qt GUI since they are used as fallback in case of missing icons
- Translation: Strings to translate now easier to understand for translators ([#1448](https://github.com/bit-team/backintime/issues/1448), [#1457](https://github.com/bit-team/backintime/issues/1457), [#1462](https://github.com/bit-team/backintime/issues/1462), [#1465](https://github.com/bit-team/backintime/issues/1465)).
- Translation: Improved completeness of translations and additional modifications of source strings ([#1454](https://github.com/bit-team/backintime/issues/1454), [#1512](https://github.com/bit-team/backintime/issues/1512))
- Translation: Plural forms support ([#1488](https://github.com/bit-team/backintime/issues/1488)).

### Changed

- Renamed qt4plugin.py to systrayiconplugin.py (we are using Qt5 for years now ;-)
- Removed unfinished feature "Full system backup" ([#1526](https://github.com/bit-team/backintime/issues/1526))

### Fixed

- AttributeError: can't set attribute 'showHiddenFiles' in app.py ([#1532](https://github.com/bit-team/backintime/issues/1532))
- Check SSH login works on machines with limited commands ([#1442](https://github.com/bit-team/backintime/issues/1442))
- Missing icon in SSH private key button ([#1364](https://github.com/bit-team/backintime/issues/1364))
- Master issue for missing or empty system-tray icon ([#1306](https://github.com/bit-team/backintime/issues/1306))
- System-tray icon missing or empty (GUI and cron) ([#1236](https://github.com/bit-team/backintime/issues/1236))
- Improve KDE plasma icon compatibility ([#1159](https://github.com/bit-team/backintime/issues/1159))
- Unit test fails on some machines due to warning "Ignoring XDG_SESSION_TYPE=wayland on Gnome..." ([#1429](https://github.com/bit-team/backintime/issues/1429))
- Generation of config-manpage caused an error with Debian's Lintian ([#1398](https://github.com/bit-team/backintime/issues/1398)).
- Return empty list in smartRemove ([#1392](https://github.com/bit-team/backintime/issues/1392), [Debian#973760](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=973760))
- Taking a snapshot reports `rsync` errors now even if no snapshot was taken ([#1491](https://github.com/bit-team/backintime/issues/1491))
- takeSnapshot() recognizes errors now by also evaluating the rsync exit code ([#489](https://github.com/bit-team/backintime/issues/489)) 
- The error user-callback is now always called if an error happened while taking a snapshot ([#1491](https://github.com/bit-team/backintime/issues/1491))
- D-Bus serviceHelper error "LimitExceeded: Maximum length of command line reached (100)": 
- Treat rsync exit code 24 as INFO instead of ERROR ([#1506](https://github.com/bit-team/backintime/issues/1506))
- Add support for ChainerBackend class as keyring which iterates over all supported keyring backends ([#1410](https://github.com/bit-team/backintime/issues/1410))

### Added

- Introduce new error codes for the "error" user callback (as part of [#1491](https://github.com/bit-team/backintime/issues/1491)):  
- The `rsync` exit code is now contained in the snapshot log (part of [#489](https://github.com/bit-team/backintime/issues/489)). Example: 
- Exclude /swapfile by default ([#1053](https://github.com/bit-team/backintime/issues/1053))
- Rearranged menu bar and its entries in the main window ([#1487](https://github.com/bit-team/backintime/issues/1487), [#1478](https://github.com/bit-team/backintime/issues/1478)).
- Configure user interface language via config file and GUI.
- Translation in Persian and Vietnamese ([#1460](https://github.com/bit-team/backintime/issues/1460)).
- Message to users (after 10 starts of BIT Gui) to motivate them contributing translations ([#1473](https://github.com/bit-team/backintime/issues/1473)).

### Removed

- Handling and checking of user group "fuse" ([#1472](https://github.com/bit-team/backintime/issues/1472)).
- Translation in Canadian English, British English and Javanese ([#1455](https://github.com/bit-team/backintime/issues/1455)).

## [1.3.3] (2023-01-04)

### Added

- New command line argument "--diagnostics" to show helpful info for better issue support ([#1100](https://github.com/bit-team/backintime/issues/1100))
- Write all log output to stderr; do not pollute stdout with INFO and WARNING messages anymore ([#1337](https://github.com/bit-team/backintime/issues/1337))

### Uncategorized

- GUI change: Remove Exit button from the toolbar ([#172](https://github.com/bit-team/backintime/issues/172))
- GUI change: Define accelerator keys for menu bar and tabs, as well as toolbar shortcuts ([#1104](https://github.com/bit-team/backintime/issues/1104))
- Desktop integration: Update .desktop file to mark Back In Time as a single main window program ([#1258](https://github.com/bit-team/backintime/issues/1258))
- Documentation update: Correct description of profile<N>.schedule.time in backintime-config manpage ([#1270](https://github.com/bit-team/backintime/issues/1270))
- Translation update: Brazilian Portuguese ([#1267](https://github.com/bit-team/backintime/issues/1267))
- Translation update: Italian ([#1110](https://github.com/bit-team/backintime/issues/1110), [#1123](https://github.com/bit-team/backintime/issues/1123))
- Translation update: French ([#1077](https://github.com/bit-team/backintime/issues/1077))
- Testing: Fix a test fail when dealing with an empty crontab ([#1181](https://github.com/bit-team/backintime/issues/1181))
- Testing: Fix a test fail when dealing with an empty config file ([#1305](https://github.com/bit-team/backintime/issues/1305))
- Testing: Skip "test_quiet_mode" (does not work reliably)
- Testing: Improve "test_diagnostics_arg" (introduced with [#1100](https://github.com/bit-team/backintime/issues/1100)) to no longer fail 
- Testing: Numerous fixes and extensions to testing ([#1115](https://github.com/bit-team/backintime/issues/1115), [#1213](https://github.com/bit-team/backintime/issues/1213), [#1279](https://github.com/bit-team/backintime/issues/1279), [#1280](https://github.com/bit-team/backintime/issues/1280), [#1281](https://github.com/bit-team/backintime/issues/1281), [#1285](https://github.com/bit-team/backintime/issues/1285), [#1288](https://github.com/bit-team/backintime/issues/1288), [#1290](https://github.com/bit-team/backintime/issues/1290), [#1293](https://github.com/bit-team/backintime/issues/1293), [#1309](https://github.com/bit-team/backintime/issues/1309), [#1334](https://github.com/bit-team/backintime/issues/1334))

### Fixed

- RTE "reentrant call inside io.BufferedWriter" in logFile.flush() during backup ([#1003](https://github.com/bit-team/backintime/issues/1003))
- Incompatibility with rsync 3.2.4 or later because of rsync's "new argument protection" ([#1247](https://github.com/bit-team/backintime/issues/1247)). Deactivate "--old-args" rsync argument earlier recommended to users as a workaround.
- DeprecationWarnings about invalid escape sequences.
- AttributeError in "Diff Options" dialog ([#898](https://github.com/bit-team/backintime/issues/898))
- Settings GUI: "Save password to Keyring" was disabled due to "no appropriate keyring found" ([#1321](https://github.com/bit-team/backintime/issues/1321))
- Back in Time did not start with D-Bus error   
- Avoid logging errors while waiting for a target drive to be mounted ([#1142](https://github.com/bit-team/backintime/issues/1142), [#1143](https://github.com/bit-team/backintime/issues/1143), [#1328](https://github.com/bit-team/backintime/issues/1328))
- [Arch Linux] AUR pkg "backintime-git": Build tests fails and installation is aborted ([#1233](https://github.com/bit-team/backintime/issues/1233), fixed with [#921](https://github.com/bit-team/backintime/issues/921))
- Wrong systray icon showing in Wayland ([#1244](https://github.com/bit-team/backintime/issues/1244))

## [1.3.2] (2022-03-12)

### Fixed

- Tests no longer work with Python 3.10 ([#1175](https://github.com/bit-team/backintime/issues/1175))

## [1.3.1] (2021-07-05)

### Uncategorized

- bump version, forgot to push branch to Github before releasing

## [1.3.0] (2021-07-04)

### Uncategorized

- Merge PR: Fix FileNotFoundError exception in mount.mounted, Thanks tatokis ([PR #1157](https://github.com/bit-team/backintime/pull/1157))
- Merge PR: qt/plugins/notifyplugin: Fix setting self.user, not local variable, Thanks Zocker1999NET ([PR #1155](https://github.com/bit-team/backintime/pull/1155))
- Merge PR: Use Link Color instead of lightGray as not to break theming, Thanks newhinton ([PR #1153](https://github.com/bit-team/backintime/pull/1153))
- Merge PR: Match old and new rsync version format, Thanks TheTimeWalker ([PR #1139](https://github.com/bit-team/backintime/pull/1139))
- Merge PR: 'TempPasswordThread' object has no attribute 'isAlive', Thanks FMeinicke ([PR #1135](https://github.com/bit-team/backintime/pull/1135))
- Merge PR: Keep permissions of an existing mountpoint from being overridden, Thanks bentolor ([PR #1058](https://github.com/bit-team/backintime/pull/1058))

### Fixed

- YEAR missing in config ([#1023](https://github.com/bit-team/backintime/issues/1023))
- SSH module didn't send identification string while checking if remote host is available ([#1030](https://github.com/bit-team/backintime/issues/1030))

## [1.2.1] (2019-08-25)

### Fixed

- TypeError in backintime.py if mount failed while running a snapshot ([#1005](https://github.com/bit-team/backintime/issues/1005))

## [1.2.0] (2019-04-27)

### Fixed

- Exit code is linked to the wrong status message ([#906](https://github.com/bit-team/backintime/issues/906))
- AppName showed 'python3' instead of 'Back In Time' ([#950](https://github.com/bit-team/backintime/issues/950))
- configured cipher is not used with all ssh-commands ([#934](https://github.com/bit-team/backintime/issues/934))
- 'make test' fails because local SSH server is running on non-standard port ([#945](https://github.com/bit-team/backintime/issues/945))
- 23:00 is missing in the list of every day hours ([#736](https://github.com/bit-team/backintime/issues/736))
- ssh-agent output changed ([#840](https://github.com/bit-team/backintime/issues/840))
- exception on making backintime folder world writable ([#812](https://github.com/bit-team/backintime/issues/812))
- stat free space for snapshot folder instead of backintime folder ([#733](https://github.com/bit-team/backintime/issues/733))
- backintime root crontab doesn't run; missing line-feed 0x0A on last line ([#781](https://github.com/bit-team/backintime/issues/781))
- IndexError in inhibitSuspend ([#772](https://github.com/bit-team/backintime/issues/772))
- polkit CheckAuthorization: race condition in privilege authorization ([CVE-2017-7572](https://www.cve.org/CVERecord?id=CVE-2017-7572))
- OSError when running backup-job from systemd ([#720](https://github.com/bit-team/backintime/issues/720))
- restore filesystem-root without 'Full rsync mode' with ACL and/or xargs activated broke whole system ([#708](https://github.com/bit-team/backintime/issues/708))
- use current folder if no file is selected in files view ([#687](https://github.com/bit-team/backintime/issues/687), [#685](https://github.com/bit-team/backintime/issues/685))
- don't reload profile after editing profile name ([#706](https://github.com/bit-team/backintime/issues/706))
- Exception in FileInfo
- failed to restore suid permissions ([#661](https://github.com/bit-team/backintime/issues/661))
- on remount user-callback got called AFTER trying to mount ([#654](https://github.com/bit-team/backintime/issues/654))
- confirm restore dialog has no scroll bar ([#625](https://github.com/bit-team/backintime/issues/625))
- DEFAULT_EXCLUDE not deletable ([#634](https://github.com/bit-team/backintime/issues/634))
- GUI status bar unreadable ([#612](https://github.com/bit-team/backintime/issues/612))
- udev schedule not working ([#605](https://github.com/bit-team/backintime/issues/605))
- decode path spooled from /etc/mtab ([PR #607](https://github.com/bit-team/backintime/pull/607))
- in snapshots.py, gives more helpful advice if a lock file is present that shouldn't be.  ([#601](https://github.com/bit-team/backintime/issues/601))
- Fail to create remote snapshot path with spaces ([#567](https://github.com/bit-team/backintime/issues/567))
- broken new_snapshot can run into infinite saveToContinue loop ([#583](https://github.com/bit-team/backintime/issues/583))
- udev schedule didn't work with LUKS encrypted drives ([#466](https://github.com/bit-team/backintime/issues/466))
- sshMaxArg failed on none default ssh port ([#581](https://github.com/bit-team/backintime/issues/581))
- failed if remote host send SSH banner ([#581](https://github.com/bit-team/backintime/issues/581))
- incorrect handling of IPv6 addresses ([#577](https://github.com/bit-team/backintime/issues/577))
- Snapshot Log View freeze on big log files ([#456](https://github.com/bit-team/backintime/issues/456))
- 'inotify_add_watch failed: file or directory not found' after deleting snapshot
- a continued snapshot was not incremental ([#557](https://github.com/bit-team/backintime/issues/557))
- config backup in snapshot had wrong name if using --config option
- Can't open files with spaces in name ([#552](https://github.com/bit-team/backintime/issues/552))
- BIT-root won't start from .desktop file ([#549](https://github.com/bit-team/backintime/issues/549))
- Keyring doesn't work with KDE Plasma5 ([#545](https://github.com/bit-team/backintime/issues/545))
- Qt4 built-in phrases where not translated ([Debian#816197](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=816197))
- configure ignore unknown args ([#547](https://github.com/bit-team/backintime/issues/547))
- snapshots-list on command-line was not sorted
- SHA256 ssh-key fingerprint was not detected
- new snapshot did not show up after finished
- TimeLine headers were not correct
- wildcards ? and [] wasn't recognized correctly
- last char of last element in tools.get_rsync_caps got cut off
- TypeError in tools.get_git_ref_hash
- don't include empty values in list ([#521](https://github.com/bit-team/backintime/issues/521))
- bash-completion doesn't work for backintime-qt4
- 'make unittest' incorrectly used 'coverage' by default ([#522](https://github.com/bit-team/backintime/issues/522))
- pm-utils is deprecated; Remove dependency ([#519](https://github.com/bit-team/backintime/issues/519))

### Uncategorized

- minor changes to allow running BiT inside Docker ([PR #959](https://github.com/bit-team/backintime/pull/959))
- remove progressbar on systray icon until BiT has it's own icon ([#902](https://github.com/bit-team/backintime/issues/902))
- clarify 'nocache' option ([#857](https://github.com/bit-team/backintime/issues/857))
- create a config-backup in root dir if backup is encrypted ([#556](https://github.com/bit-team/backintime/issues/556))
- move progressbar under statusbar
- alleviate default exclude [Tt]rash* ([#759](https://github.com/bit-team/backintime/issues/759))
- enable high DPI scaling ([#732](https://github.com/bit-team/backintime/issues/732))
- Smart Remove try to keep healthy snapshots ([#703](https://github.com/bit-team/backintime/issues/703))
- ask for restore-to path before confirm ([#678](https://github.com/bit-team/backintime/issues/678))
- fix 'Back in Time (root)' on wayland ([#640](https://github.com/bit-team/backintime/issues/640))
- sort int values in config numerical instead if alphabetical ([#175](https://github.com/bit-team/backintime/issues/175)#issuecomment-272941811)
- set timestamp directly after new snapshot ([#584](https://github.com/bit-team/backintime/issues/584))
- add shortcut CTRL+H for toggle show hidden files to fileselect dialog ([#378](https://github.com/bit-team/backintime/issues/378))
- redesign restore menu ([#661](https://github.com/bit-team/backintime/issues/661))
- add ability to disable SSH command- and ping-check ([#647](https://github.com/bit-team/backintime/issues/647))
- enable bwlimit for local profiles ([#646](https://github.com/bit-team/backintime/issues/646))
- import remote host-key into known_hosts from Settings
- copy public SSH key to remote host from Settings
- create a new SSH key from Settings
- rename debian package from backintime-qt4 into backintime-qt
- rename paths and methods from *qt4* into *qt*
- rename executable backintime-qt4 into backintime-qt
- new config version 6, rename qt4 keys into qt, add new domain for schedule
- check crontab entries on every GUI startup ([#129](https://github.com/bit-team/backintime/issues/129))
- start a new ssh-agent instance only if necessary
- add cli command 'shutdown' ([#596](https://github.com/bit-team/backintime/issues/596))
- make LogView and Settings Dialog non-modal ([#608](https://github.com/bit-team/backintime/issues/608))
- port to Qt5/pyqt5 ([#518](https://github.com/bit-team/backintime/issues/518))
- Recognize changes on previous runs while continuing new snapshots
- Add pause, resume and stop function for running snapshots ([#474](https://github.com/bit-team/backintime/issues/474), [#195](https://github.com/bit-team/backintime/issues/195))
- use rsync to save permissions
- replace os.system calls with subprocess.Popen
- automatically refresh log view if a snapshot is currently running
- make full-rsync mode default, remove the other mode
- use rsync to remove snapshots which will give a nice speedup ([#151](https://github.com/bit-team/backintime/issues/151))
- open temporary local copy of files instead of original backup on double-click in GUI
- open current log directly from systray icon during taking a snapshot
- use Monospace font in logview
- Fix lintian warning: manpage-has-errors-from-man: bad argument name 'P'
- Do not print 'SnapshotID' or 'SnapshotPath' if running 'snapshots-list' command (and other) with '--quiet'
- Remove dependency 'ps'
- rewrite huge parts of snapshots.py

### Removed

- unused and undocumented userscript plugin
- dependency for extended 'find' command on remote host
- backwards compatibility to version < 1.0

### Added

- contextmenu for logview dialog which can copy, exclude and decode lines
- 'Edit user-callback' dialog
- cli command 'smart-remove'
- option to decrypt paths in systray menu with mode ssh-encrypted
- tool-tips to restore menu
- --share-path option
- restore option --only-new
- button 'Take snapshot with checksums'

### Changed

- default configure option to --no-fuse-group as Ubuntu >= 12.04 don't need fuse group-membership anymore

## [1.1.24] (2017-11-07)

### Fixed

- shell injection in notify-send ([#834](https://github.com/bit-team/backintime/issues/834), [CVE-2017-16667](https://www.cve.org/CVERecord?id=CVE-2017-16667))

## [1.1.22] (2017-10-28)

### Fixed

- stat free space for snapshot folder instead of backintime folder ([#733](https://github.com/bit-team/backintime/issues/733))
- backintime root crontab doesn't run; missing line-feed 0x0A on last line ([#781](https://github.com/bit-team/backintime/issues/781))
- can't open files with spaces in name ([#552](https://github.com/bit-team/backintime/issues/552))

## [1.1.20] (2017-04-09)

### Fixed

- polkit CheckAuthorization: race condition in privilege authorization ([CVE-2017-7572](https://www.cve.org/CVERecord?id=CVE-2017-7572))

## [1.1.18] (2017-03-29)

### Fixed

- manual snapshots from GUI didn't work ([#728](https://github.com/bit-team/backintime/issues/728))

## [1.1.16] (2017-03-28)

### Fixed

- start a new ssh-agent instance only if necessary ([#722](https://github.com/bit-team/backintime/issues/722))
- OSError when running backup-job from systemd ([#720](https://github.com/bit-team/backintime/issues/720))

## [1.1.14] (2017-03-05)

### Fixed

- udev schedule not working ([#605](https://github.com/bit-team/backintime/issues/605))
- Keyring doesn't work with KDE Plasma5 ([#545](https://github.com/bit-team/backintime/issues/545))
- nameError in tools.make_dirs ([#622](https://github.com/bit-team/backintime/issues/622))
- use current folder if no file is selected in files view
- restore filesystem-root without 'Full rsync mode' with ACL and/or xargs activated broke whole system ([#708](https://github.com/bit-team/backintime/issues/708))

## [1.1.12] (2016-01-11)

### Fixed

- remove x-terminal-emulator dependency ([#515](https://github.com/bit-team/backintime/issues/515))
- AttributeError in About Dialog ([#515](https://github.com/bit-team/backintime/issues/515))

## [1.1.10] (2016-01-09)

### Fixed

- failed to remove empty lock file ([#505](https://github.com/bit-team/backintime/issues/505))
- Restore the correct file owner and group fail if they are not present in system ([#58](https://github.com/bit-team/backintime/issues/58))
- QObject::startTimer error on closing app
- FileNotFoundError while starting pw-cache from source
- suppress warning about failed inhibit suspend if run as root ([#500](https://github.com/bit-team/backintime/issues/500))
- UI blocked/grayed out while removing snapshot ([#487](https://github.com/bit-team/backintime/issues/487))
- pw-cache failed on leftover PID file, using ApplicationInstance now ([#468](https://github.com/bit-team/backintime/issues/468))
- failed to parse some arguments ([#492](https://github.com/bit-team/backintime/issues/492))
- failed to start GUI if launched from systray icon
- deleted snapshot is still listed in Timeline if using mode SSH ([#493](https://github.com/bit-team/backintime/issues/493))
- PermissionError while deleting readonly files on sshfs mounted share ([#490](https://github.com/bit-team/backintime/issues/490))
- create new encrypted profiles with encfs >= 1.8.0 failed ([#477](https://github.com/bit-team/backintime/issues/477))
- AttributeError in common/tools.py if keyring is missing ([#473](https://github.com/bit-team/backintime/issues/473))
- remote rename of 'new_snapshot' folder sometimes isn't recognized locally; rename local now (https://answers.launchpad.net/questions/271792)

### Uncategorized

- Add Icon 'show-hidden' ([#507](https://github.com/bit-team/backintime/issues/507))
- subclass ApplicationInstance in GUIApplicationInstance to reduce redundant code
- speed up app start by adding snapshots to timeline in background thread
- add warning on failed permission restore ([#58](https://github.com/bit-team/backintime/issues/58))
- continue an unfinished new_snapshot if possible ([#400](https://github.com/bit-team/backintime/issues/400))
- Add Nautilus-like shortcuts for navigating in file browser ([#483](https://github.com/bit-team/backintime/issues/483))
- speed up mounting of SSH+encrypted profiles
- Move source code and bug tracking to GitHub

### Added

- Modify for Full System Backup button to settings page, to change some profile settings
- get|set_list_value to configfile
- unittest (thanks to Dorian, Alexandre, Aurélien and Gregory from IAGL)

## [1.1.8] (2015-09-28)

### Fixed

- unlock private SSH key run into 5sec timeout if password is empty
- BiT freeze when activate 'Decode path' in 'Snapshot Log View'
- empty gray window appears when starting the gui as root ([Launchpad#1493020](https://bugs.launchpad.net/backintime/+bug/1493020))
- gnu_find_suffix_support doesn't set back to True ([Launchpad#1487781](https://bugs.launchpad.net/backintime/+bug/1487781))
- lintian warning dbus-policy-without-send-destination
- dbus exception if dbus systembus is not running
- depend on virtual package cron-daemon instead of cron for compatibility with other cron implementations ([Debian#776856](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=776856))
- wasn't able to start from alternate install dir ([Launchpad#478689](https://bugs.launchpad.net/backintime/+bug/478689))
- wasn't able to start from source dir
- 'Inhibit Suspend' fails with 'org.freedesktop.PowerManagement.Inhibit' ([Launchpad#1485242](https://bugs.launchpad.net/backintime/+bug/1485242))
- No mounting while selecting a secondary profile in the gui ([Launchpad#1481267](https://bugs.launchpad.net/backintime/+bug/1481267))
- fix for bug [Launchpad#1419466](https://bugs.launchpad.net/backintime/+bug/1419466) broke crontab on Slackware
- fix for bug [Launchpad#1431305](https://bugs.launchpad.net/backintime/+bug/1431305) broke pw-cache on Ubuntu
- bash-complete
- Settings accepted empty strings for Host/User/Profile-ID ([Launchpad#1477733](https://bugs.launchpad.net/backintime/+bug/1477733))
- IndexError on 'check_remote_commands' due to too long args ([Launchpad#1471930](https://bugs.launchpad.net/backintime/+bug/1471930))
- Makefile has no uninstall target ([Launchpad#1469152](https://bugs.launchpad.net/backintime/+bug/1469152))

### Uncategorized

- show current app name and profile ID in syslog ([Launchpad#906213](https://bugs.launchpad.net/backintime/+bug/906213))
- Show 'Profiles' dropdown only in 'Last Log Viewer', add 'Snapshots' dropdown in 'Snapshot Log Viewer' ([Launchpad#1478219](https://bugs.launchpad.net/backintime/+bug/1478219))
- do not restore permission if they are identical with current permissions
- security issue: do not run user-callback in a shell
- apply timestamps-in-gzip.patch from Debian backintime/1.1.6-1 package
- run multiple smart-remove jobs in one screen session ([Launchpad#1487781](https://bugs.launchpad.net/backintime/+bug/1487781))
- use native Python code to check mountpoint
- Add expert option for stdout and stderr redirection in cronjobs (https://answers.launchpad.net/questions/270105)
- show 'man backintime' on Help; remove link to backintime.le-web.org ([Launchpad#1475995](https://bugs.launchpad.net/backintime/+bug/1475995))
- add --local-backup, --no-local-backup and --delete option to restore on command-line ([Launchpad#1467239](https://bugs.launchpad.net/backintime/+bug/1467239))
- rewrite command-line argument parsing. Now using argparse

### Added

- option to not log user-callback output
- error messages if PID file creation fail
- Warning about unsupported filesystems
- --debug argument
- 'backup on restore' option to confirm dialog
- check-config command for command-line
- expert option SSH command prefix

### Removed

- shebang in common/askpass.py and common/create-manpage-backintime-config.py

## [1.1.6] (2015-06-27)

### Uncategorized

- show Profile name in systrayicon menu
- make own Exceptions a childclass from BackInTimeException
- Specifying the SSH private key whenever ssh is called ([Launchpad#1433682](https://bugs.launchpad.net/backintime/+bug/1433682))
- add to in-/exclude directly from mainwindow ([Launchpad#1454856](https://bugs.launchpad.net/backintime/+bug/1454856))
- add option to run Smart Remove in background on remote host ([Launchpad#1457210](https://bugs.launchpad.net/backintime/+bug/1457210))
- Use current profile when starting GUI from Systray

### Fixed

- encrypted remote backup hangs on 'start encfsctl encode process' ([Launchpad#1455925](https://bugs.launchpad.net/backintime/+bug/1455925))
- missing profile<N>.name crashed GUI
- Segmentation fault caused by two QApplication instances ([Launchpad#1463732](https://bugs.launchpad.net/backintime/+bug/1463732))
- no Changes [C] log entries with 'Check for changes' disabled ([Launchpad#1463367](https://bugs.launchpad.net/backintime/+bug/1463367))
- some changed options from Settingsdialog where not respected during automatic tests after hitting OK
- python version check fails on python 3.3 ([Launchpad#1463686](https://bugs.launchpad.net/backintime/+bug/1463686))
- pw-cache didn't start on Mint KDE because of missing stdout and stderr ([Launchpad#1431305](https://bugs.launchpad.net/backintime/+bug/1431305))
- failed to restore file names with white spaces using CLI ([Launchpad#1435602](https://bugs.launchpad.net/backintime/+bug/1435602))
- UnboundLocalError with 'last_snapshot' in _free_space ([Launchpad#1437623](https://bugs.launchpad.net/backintime/+bug/1437623))

### Removed

- consolekit from dependencies

## [1.1.4] (2015-03-22)

### Uncategorized

- add option to keep new snapshot with 'full rsync mode' regardless of changes ([Launchpad#1434722](https://bugs.launchpad.net/backintime/+bug/1434722))
- remove base64 encoding for passwords as it doesn't add any security but broke the password process ([Launchpad#1431305](https://bugs.launchpad.net/backintime/+bug/1431305))
- add confirm dialog before restoring ([Launchpad#438079](https://bugs.launchpad.net/backintime/+bug/438079))
- cache uuid in config so it doesn't fail if the device isn't plugged in ([Launchpad#1426881](https://bugs.launchpad.net/backintime/+bug/1426881))
- prevent snapshots from being removed with restore and delete; show warning if restore and delete filesystem root (https://answers.launchpad.net/questions/262837)
- use 'crontab' instead of 'crontab -' to read from stdin ([Launchpad#1419466](https://bugs.launchpad.net/backintime/+bug/1419466))

### Fixed

- wrong quote in 'Save config file'
- Deleting the last snapshot does not update the last_snapshot symlink ([Launchpad#1434724](https://bugs.launchpad.net/backintime/+bug/1434724))
- Wrong status text in the tray icon ([Launchpad#1429400](https://bugs.launchpad.net/backintime/+bug/1429400))
- restore permissions of lots of files made BackInTime unresponsive ([Launchpad#1428423](https://bugs.launchpad.net/backintime/+bug/1428423))
- failed to restore file owner and group
- OSError in free_space; add alternate method to get free space
- ugly theme while running as root on Gnome based DEs ([Launchpad#1418447](https://bugs.launchpad.net/backintime/+bug/1418447))
- UnicodeError thrown if filename has broken charset ([Launchpad#1419694](https://bugs.launchpad.net/backintime/+bug/1419694))

### Added

- option to run only one snapshot at a time
- warning about wrong Python version in configure
- bash-completion

## [1.1.2] (2015-02-04)

### Uncategorized

- sort 'Backup folders' in main window
- save in- and exclude sort order
- use PolicyKit to install Udev rules
- move compression from install to build in Makefiles
- use pkexec to start backintime-qt4 as root

## [1.1.0] (2015-01-15)

### Added

- tooltips for rsync options
- more user-callback events (on App start and exit, on mount and unmount)
- context menu to files view
- more default exclude; remove [Cc]ache* from exclude
- option for custom rsync-options
- ProgressBar for rsync
- progress for smart-remove
- --gksu/--gksudo arg to qt4/configure

### Uncategorized

- make only one debian/control
- multiselect files to restore ([Launchpad#1135886](https://bugs.launchpad.net/backintime/+bug/1135886))
- force run manual snapshots on battery ([Launchpad#861553](https://bugs.launchpad.net/backintime/+bug/861553))
- backup encfs config to local config folder
- apply 'install-docs-move.patch' from Debian package by Jonathan Wiltshire
- add restore option to delete new files during restore ([Launchpad#1371951](https://bugs.launchpad.net/backintime/+bug/1371951))
- use flock to prevent two instances running at the same time
- restore config dialog added ([Launchpad#480391](https://bugs.launchpad.net/backintime/+bug/480391))
- inhibit suspend/hibernate while take_snapshot or restore
- use more reliable code for get_user
- implement anacrons functions inside BIT => more flexible schedules and no new timestamp if there was an error
- automatically run in background if started with 'backintime --backup-job'
- fix typos and style warnings in manpages reported by Lintian (https://lintian.debian.org/full/jmw@debian.org.html#backintime_1.0.34-0.1)
- add exclude files by size ([Launchpad#823719](https://bugs.launchpad.net/backintime/+bug/823719))
- optional run 'rsync' with 'nocache' ([Launchpad#1344528](https://bugs.launchpad.net/backintime/+bug/1344528))
- mark invalid exclude pattern with mode ssh-encrypted
- make Settingsdialog tabs scrollable
- remove colon (: ) restriction in exclude pattern
- prevent starting new snapshot if restore is running
- add top-level directory for tarball ([Launchpad#1359076](https://bugs.launchpad.net/backintime/+bug/1359076))
- multi selection in timeline => remove multiple snapshots with one click
- print warning if started with sudo
- ask to include symlinks target instead link ([Launchpad#1117709](https://bugs.launchpad.net/backintime/+bug/1117709))
- port to Python 3.x
- returncode >0 if there was an error ([Launchpad#1040995](https://bugs.launchpad.net/backintime/+bug/1040995))
- Enable user-callback script to cancel a backup by returning a non-zero exit code.
- merge backintime-notify into backintime-qt4
- remember last path for each profile ([Launchpad#1254870](https://bugs.launchpad.net/backintime/+bug/1254870))
- sort include and exclude list ([Launchpad#1193149](https://bugs.launchpad.net/backintime/+bug/1193149))
- Timeline show tooltip 'Last check'
- show hidden files in FileDialog ([Launchpad#995925](https://bugs.launchpad.net/backintime/+bug/995925))
- add button text for all buttons ([Launchpad#992020](https://bugs.launchpad.net/backintime/+bug/992020))
- add shortcuts ([Launchpad#686694](https://bugs.launchpad.net/backintime/+bug/686694))
- add menubar ([Launchpad#528851](https://bugs.launchpad.net/backintime/+bug/528851))
- port KDE4 GUI to pure Qt4 to replace both KDE4 and Gnome GUI

### Removed

- 'Auto Host/User/Profile-ID' as this is more confusing than helping
- snapshots from commandline
- old status-bar message after a snapshot crashed.

### Fixed

- check procname of pid-locks ([Launchpad#1341414](https://bugs.launchpad.net/backintime/+bug/1341414))
- Port check failed on IPv6 ([Launchpad#1361634](https://bugs.launchpad.net/backintime/+bug/1361634))
- 'inotify_add_watch failed' while closing BIT
- systray icon didn't show up ([Launchpad#658424](https://bugs.launchpad.net/backintime/+bug/658424))

## [1.0.40] (2014-11-02)

### Uncategorized

- use fingerprint to check if ssh key was unlocked correctly (https://answers.launchpad.net/questions/256408)
- add fallback method to get UUID (https://answers.launchpad.net/questions/254140)

### Fixed

- 'Attempt to unlock mutex that was not locked'... this time for good

## [1.0.38] (2014-10-01)

### Fixed

- 'Attempt to unlock mutex that was not locked' in gnomeplugin (https://answers.launchpad.net/questions/255225)
- housekeeping by gnome-session-daemon might delete backup and original data ([Launchpad#1374343](https://bugs.launchpad.net/backintime/+bug/1374343))
- Type Error in 'backintime --decode' ([Launchpad#1365072](https://bugs.launchpad.net/backintime/+bug/1365072))
- take_snapshot didn't wait for snapshot folder come available if notifications are disabled ([Launchpad#1332979](https://bugs.launchpad.net/backintime/+bug/1332979))

### Uncategorized

- compare os.path.realpath instead of os.stat to get devices UUID

## [1.0.36] (2014-08-06)

### Uncategorized

- remove UbuntuOne from exclude ([Launchpad#1340131](https://bugs.launchpad.net/backintime/+bug/1340131))
- Gray out 'Add Profile' if 'Main Profile' isn't configured yet ([Launchpad#1335545](https://bugs.launchpad.net/backintime/+bug/1335545))
- Don't check for fuse group-membership if group doesn't exist
- disable keyring for root

### Fixed

- backintime-kde4 as root failed to load ssh-key ([Launchpad#1276348](https://bugs.launchpad.net/backintime/+bug/1276348))
- kdesystrayicon.py crashes because of missing environ ([Launchpad#1332126](https://bugs.launchpad.net/backintime/+bug/1332126))
- OSError if sshfs/encfs is not installed ([Launchpad#1316288](https://bugs.launchpad.net/backintime/+bug/1316288))
- TypeError in config.py check_config() (https://bugzilla.redhat.com/show_bug.cgi?id=1091644)
- unhandled exception in create_last_snapshot_symlink() ([Launchpad#1269991](https://bugs.launchpad.net/backintime/+bug/1269991))

## [1.0.34] (2013-12-21)

### Uncategorized

- sync/flush all disks before shutdown ([Launchpad#1261031](https://bugs.launchpad.net/backintime/+bug/1261031))

### Fixed

- BIT running as root shutdown after snapshot, regardless of option checked ([Launchpad#1261022](https://bugs.launchpad.net/backintime/+bug/1261022))

## [1.0.32] (2013-12-13)

### Fixed

- cron scheduled snapshots won't start with 1.0.30

## [1.0.30] (2013-12-12)

### Uncategorized

- scheduled and manual snapshots use --config
- make configure scripts portable ([Launchpad#377429](https://bugs.launchpad.net/backintime/+bug/377429))
- add symlink last_snapshot ([Launchpad#787118](https://bugs.launchpad.net/backintime/+bug/787118))
- add option to run rsync with 'nice' or 'ionice' on remote host ([Launchpad#1240301](https://bugs.launchpad.net/backintime/+bug/1240301))
- add Shutdown button to shutdown system after snapshot has finished ([Launchpad#838742](https://bugs.launchpad.net/backintime/+bug/838742))
- wrap long lines for syslog

### Fixed

- udev rule doesn't finish ([Launchpad#1249466](https://bugs.launchpad.net/backintime/+bug/1249466))
- multiple errors in PPA build process; reorganize updateversion.sh
- Mate and xfce desktop didn't show systray icon ([Launchpad#658424](https://bugs.launchpad.net/backintime/+bug/658424)/comments/31)
- Ubuntu Lucid doesn't provide SecretServiceKeyring ([Launchpad#1243911](https://bugs.launchpad.net/backintime/+bug/1243911))
- 'gksu backintime-gnome' failed with dbus.exceptions.DBusException

### Added

- virtual package backintime-kde for PPA

## [1.0.28] (2013-10-19)

### Removed

- config on 'apt-get purge'

### Added

- more options for configure scripts; update README
- udev schedule (run BIT as soon as the drive is connected)

### Fixed

- AttributeError with python-keyring>1.6.1 ([Launchpad#1234024](https://bugs.launchpad.net/backintime/+bug/1234024))
- TypeError: KDirModel.removeColumns() is a private method in kde4/app.py ([Launchpad#1232694](https://bugs.launchpad.net/backintime/+bug/1232694))
- sshfs mount disconnect after a while due to some firewalls (add ServerAliveInterval) (https://answers.launchpad.net/backintime/+question/235685)
- Ping fails if ICMP is disabled on remote host ([Launchpad#1226718](https://bugs.launchpad.net/backintime/+bug/1226718))
- KeyError in getgrnam if there is no 'fuse' group ([Launchpad#1225561](https://bugs.launchpad.net/backintime/+bug/1225561))
- anacrontab won't work with profilename with spaces ([Launchpad#1224620](https://bugs.launchpad.net/backintime/+bug/1224620))
- NameError in tools.move_snapshots_folder ([Launchpad#871466](https://bugs.launchpad.net/backintime/+bug/871466))
- KPassivePopup is not defined ([Launchpad#871475](https://bugs.launchpad.net/backintime/+bug/871475))
- ValueError while reading pw-cache PID (https://answers.launchpad.net/backintime/+question/235407)

### Uncategorized

- add '--checksum' commandline option ([Launchpad#886021](https://bugs.launchpad.net/backintime/+bug/886021))
- multi selection for include and exclude list ([Launchpad#660753](https://bugs.launchpad.net/backintime/+bug/660753))

## [1.0.26] (2013-09-07)

### Uncategorized

- add feature: keep min free inodes
- roll back commit 836.1.5 (check free-space on ssh remote host): statvfs DOES work over sshfs. But not with quite outdated sshd
- add feature: restore from command line; add option --config
- use 'ps ax' to check if 'backintime --pw-cache' is still running
- mount after locking, unmount before unlocking in take_snapshot
- redirect logger.error and .warning to stderr; new argument --quiet
- deactivate 'Save Password' if no keyring is available
- use Password-cache for user-input too
- handle two Passwords
- add 'SSH encrypted': mount / with encfs reverse and sync encrypted with rsync. EXPERIMENTAL!
- add 'Local encrypted': mount encfs

### Added

- daily anacron schedule
- delete button and 'list only equal' in Snapshot dialog; multiSelect in snapshot list
- manpage backintime-config and config-examples
- option --bwlimit for rsync

### Fixed

- Restore makes files public during the operation
- Cannot keep modifications to cron ([Launchpad#698106](https://bugs.launchpad.net/backintime/+bug/698106))
- cannot stat 'backintime-kde4-root.desktop.kdesudo' ([Launchpad#696659](https://bugs.launchpad.net/backintime/+bug/696659))
- unreadable dark KDE color schemes ([Launchpad#1184920](https://bugs.launchpad.net/backintime/+bug/1184920))
- permission denied if remote uid wasn't the same as local uid

## [1.0.24] (2013-05-08)

### Uncategorized

- hide check_for_canges if full_rsync_mode is checked
- DEFAULT_EXCLUDE system folders with /foo/* so at least the folder itself will backup
- DEFAULT_EXCLUDE /run; exclude MOUNT_ROOT with higher priority and not with DEFAULT_EXCLUDE anymore
- 'Save Password' default off to avoid problems with existing profiles
- if restore uid/gid failed try to restore at least gid
- SSH need to store permissions in separate file with "Full rsync mode" because remote user might not be able to store ownership
- switch to 'find -exec cmd {} +' ([Launchpad#1157639](https://bugs.launchpad.net/backintime/+bug/1157639))

### Fixed

- 'CalledProcessError' object has no attribute 'strerror'
- quote rsync remote path with spaces
- restore permission failed on "Full rsync mode"
- glib.GError: Unknown internal child: selection
- GtkWarning: Unknown property: GtkLabel.margin-top
- check keyring backend only if password is needed

### Changed

- all indent tabs to 4 spaces

## [1.0.22] (2013-03-26)

### Uncategorized

- check free-space on ssh remote host (statvfs didn't work over sshfs)

### Added

- Password storage mode ssh
- "Full rsync mode" (can be faster but ...)

### Fixed

- "Restore to..." failed due to spaces in directory name ([Launchpad#1096319](https://bugs.launchpad.net/backintime/+bug/1096319))
- host not found in known_hosts if port != 22 ([Launchpad#1130356](https://bugs.launchpad.net/backintime/+bug/1130356))
- sshtools.py used not POSIX conform conditionals

## [1.0.20] (2012-12-15)

### Fixed

- restore remote path with spaces using mode ssh returned error

## [1.0.18] (2012-11-17)

### Uncategorized

- Fix packages: man & translations
- Map multiple arguments for gettext so they can be rearranged by translators

### Fixed

- [Launchpad#1077446](https://bugs.launchpad.net/backintime/+bug/1077446)
- [Launchpad#1078979](https://bugs.launchpad.net/backintime/+bug/1078979)
- [Launchpad#1079479](https://bugs.launchpad.net/backintime/+bug/1079479)

## [1.0.16] (2012-11-15)

### Uncategorized

- Fix a package dependency problem ... this time for good ([Launchpad#1077446](https://bugs.launchpad.net/backintime/+bug/1077446))

## [1.0.14] (2012-11-09)

### Fixed

- a package dependency problem

## [1.0.12] (2012-11-08)

### Uncategorized

- Add links to: website, documentation, report a bug, answers, faq
- Use libnotify for gnome/kde4 notifications instead of gnome specific libraries
- Add more schedule options: every 30 min, every 2 hours, every 4 hours, every 6 hours & every 12 hours

### Fixed

- [Launchpad#1059247](https://bugs.launchpad.net/backintime/+bug/1059247)
- wrong path if restore system root
- glade (xml) files did not translate
- [Launchpad#1073867](https://bugs.launchpad.net/backintime/+bug/1073867)

### Added

- generic mount-framework
- mode 'SSH' for backups on remote host using ssh protocol.

## [1.0.10] (2012-03-06)

### Added

- "Restore to ..." in replacement of copy (with or without drag & drop) because copy don't restore user/group/rights

## [1.0.8] (2011-06-18)

### Fixed

- [Launchpad#723545](https://bugs.launchpad.net/backintime/+bug/723545)
- [Launchpad#705237](https://bugs.launchpad.net/backintime/+bug/705237)
- [Launchpad#696663](https://bugs.launchpad.net/backintime/+bug/696663)
- [Launchpad#671946](https://bugs.launchpad.net/backintime/+bug/671946)

## [1.0.6] (2011-01-02)

### Fixed

- [Launchpad#676223](https://bugs.launchpad.net/backintime/+bug/676223)
- [Launchpad#672705](https://bugs.launchpad.net/backintime/+bug/672705)

### Uncategorized

- Smart remove: configurable options ([Launchpad#406765](https://bugs.launchpad.net/backintime/+bug/406765))

## [1.0.4] (2010-10-28)

### Uncategorized

- SettingsDialog: show highly recommended excludes
- Option to use checksum to detect changes ([Launchpad#666964](https://bugs.launchpad.net/backintime/+bug/666964))
- Option to select log verbosity ([Launchpad#664423](https://bugs.launchpad.net/backintime/+bug/664423))
- Gnome: use gloobus-preview if installed

### Fixed

- [Launchpad#664783](https://bugs.launchpad.net/backintime/+bug/664783)

## [1.0.2] (2010-10-16)

### Uncategorized

- reduce log file (no more duplicate "Compare with..." lines)
- declare backintime-kde4 packages as a replacement of backintime-kde

## [1.0] (2010-10-16)

### Uncategorized

- add '.dropbox*' to default exclude patterns ([Launchpad#628172](https://bugs.launchpad.net/backintime/+bug/628172))
- add option to take a snapshot at every boot ([Launchpad#621810](https://bugs.launchpad.net/backintime/+bug/621810))
- add continue on errors ([Launchpad#616299](https://bugs.launchpad.net/backintime/+bug/616299))
- add expert options: copy unsafe links & copy links
- "user-callback" replace "user.callback" and receive profile information
- documentation: on-line only (easier to maintain)
- merge with: lp:~dave2010/backintime/minor-edits
- merge with: lp:~mcfonty/backintime/unique-snapshots-view
- reduce memory usage during compare with previous snapshot process
- custom backup hour (for daily backups or mode): [Launchpad#507451](https://bugs.launchpad.net/backintime/+bug/507451)
- smart remove was slightly changed ([Launchpad#502435](https://bugs.launchpad.net/backintime/+bug/502435))
- make backup on restore optional
- fix bug that could cause "ghost" folders in snapshots (LP: 406092)
- fix bug that converted / into // ([Launchpad#455149](https://bugs.launchpad.net/backintime/+bug/455149))
- remove "schedule per included directory" (profiles do that) (+ bug [Launchpad#412470](https://bugs.launchpad.net/backintime/+bug/412470))
- fig bug: [Launchpad#489380](https://bugs.launchpad.net/backintime/+bug/489380)
- update Slovak translation (Tomáš Vadina <kyberdev@gmail.com>)
- multiple profiles support
- GNOME: fix notification
- backintime snapshot folder is restructured to ../backintime/machine/user/profile_id/
- added a desktop file for kdesu and a test if kdesu or kdesudo should be used ([Launchpad#389988](https://bugs.launchpad.net/backintime/+bug/389988))
- added expert option to disable snapshots when on battery ([Launchpad#388178](https://bugs.launchpad.net/backintime/+bug/388178))
- fix bug handling big files by the GNOME GUI ([Launchpad#409130](https://bugs.launchpad.net/backintime/+bug/409130))
- fix bug in handling of & characters by GNOME GUI ([Launchpad#415848](https://bugs.launchpad.net/backintime/+bug/415848))
- fix a security bug in chmods before snapshot removal ([Launchpad#419774](https://bugs.launchpad.net/backintime/+bug/419774))
- snapshots are stored entirely read-only ([Launchpad#386275](https://bugs.launchpad.net/backintime/+bug/386275))
- fix exclude patterns in KDE4 ([Launchpad#432537](https://bugs.launchpad.net/backintime/+bug/432537))
- fix opening german files with external applications in KDE ([Launchpad#404652](https://bugs.launchpad.net/backintime/+bug/404652))
- changed default exclude patterns to caches, thumbnails, trashbins, and backups ([Launchpad#422132](https://bugs.launchpad.net/backintime/+bug/422132))
- write access to snapshot folder is checked & change to snapshot version 2 ([Launchpad#423086](https://bugs.launchpad.net/backintime/+bug/423086))
- fix small bugs (a.o. [Launchpad#474307](https://bugs.launchpad.net/backintime/+bug/474307))
- Used a more standard crontab syntax ([Launchpad#409783](https://bugs.launchpad.net/backintime/+bug/409783))
- Stop the "Over zealous removal of crontab entries" ([Launchpad#451811](https://bugs.launchpad.net/backintime/+bug/451811))

### Fixed

- xattr
- [Launchpad#588841](https://bugs.launchpad.net/backintime/+bug/588841)
- [Launchpad#588215](https://bugs.launchpad.net/backintime/+bug/588215)
- [Launchpad#588393](https://bugs.launchpad.net/backintime/+bug/588393)
- [Launchpad#426400](https://bugs.launchpad.net/backintime/+bug/426400)
- [Launchpad#575022](https://bugs.launchpad.net/backintime/+bug/575022)
- [Launchpad#571894](https://bugs.launchpad.net/backintime/+bug/571894)
- [Launchpad#553441](https://bugs.launchpad.net/backintime/+bug/553441)
- [Launchpad#550765](https://bugs.launchpad.net/backintime/+bug/550765)
- [Launchpad#507246](https://bugs.launchpad.net/backintime/+bug/507246)
- [Launchpad#538855](https://bugs.launchpad.net/backintime/+bug/538855)
- [Launchpad#386230](https://bugs.launchpad.net/backintime/+bug/386230)
- [Launchpad#527039](https://bugs.launchpad.net/backintime/+bug/527039)
- [Launchpad#520956](https://bugs.launchpad.net/backintime/+bug/520956)
- [Launchpad#520930](https://bugs.launchpad.net/backintime/+bug/520930)
- [Launchpad#521223](https://bugs.launchpad.net/backintime/+bug/521223)
- [Launchpad#516066](https://bugs.launchpad.net/backintime/+bug/516066)
- [Launchpad#512813](https://bugs.launchpad.net/backintime/+bug/512813)
- [Launchpad#503859](https://bugs.launchpad.net/backintime/+bug/503859)
- [Launchpad#501285](https://bugs.launchpad.net/backintime/+bug/501285)
- [Launchpad#493558](https://bugs.launchpad.net/backintime/+bug/493558)
- [Launchpad#441628](https://bugs.launchpad.net/backintime/+bug/441628)
- [Launchpad#489319](https://bugs.launchpad.net/backintime/+bug/489319)
- [Launchpad#447841](https://bugs.launchpad.net/backintime/+bug/447841)
- [Launchpad#412695](https://bugs.launchpad.net/backintime/+bug/412695)

### Added

- error log and error log view dialog (Gnome & KDE4)
- ionice support for user/cron backup process
- the possibility to include other snapshot folders within a profile, it can only read those, there is not a GUI implementation yet
- a tag suffix to the snapshot_id, to avoid double snapshot_ids

## [0.9.26] (2009-05-19)

### Uncategorized

- update translations from Launchpad
- Fix a bug in smart-remove algorithm ([Launchpad#376104](https://bugs.launchpad.net/backintime/+bug/376104))
- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- use only 'folder' term (more consistent with GNOME/KDE)
- add 'expert option': enable/disable nice for cron jobs
- GNOME & KDE4: refresh snapshots button force files view to update too
- you can include a backup parent directory (backup directory will auto-exclude itself)

### Fixed

- [Launchpad#374477](https://bugs.launchpad.net/backintime/+bug/374477)
- [Launchpad#375113](https://bugs.launchpad.net/backintime/+bug/375113)
- some small bugs

### Added

- '--no-check' option to configure scripts

## [0.9.24] (2009-05-07)

### Uncategorized

- update translations
- KDE4: fix python string <=> QString problems
- KDE4 FilesView/SnapshotsDialog: ctrl-click just select (don't execute)
- KDE4: fix crush after "take snapshot" process ([Launchpad#366241](https://bugs.launchpad.net/backintime/+bug/366241))
- store basic permission in a special file so it can restore them correctly (event from NTFS)
- implement Gnome/KDE4 systray icons and user.callback as plugins
- reorganize code: common/GNOME/KDE4
- GNOME: break the big glade file in multiple file
- backintime is no longer aware of 'backintime-gnome' and 'backintime-kde4'  

### Added

- config version

## [0.9.22.1] (2009-04-27)

### Fixed

- French translation

## [0.9.22] (2009-04-24)

### Uncategorized

- update translations from Launchpad
- KDE4: fix some translation problems
- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- create directory now use python os.makedirs (replace use of mkdir command)
- KDE4: fix a crush related to QString - python string conversion
- GNOME & KDE4 SettingsDialog: if schedule automatic backups per directory is set, global schedule is hidden
- GNOME FilesView: thread "*~" files (backup files) as hidden files
- GNOME: use gtk-preferences icon for SettingsDialog (replace gtk-execute icon)
- expert option: $XDG_CONFIG_HOME/backintime/user.callback (if exists) is called a different steps 
- add more command line options: --snapshots-list, --snapshots-list-path, --last-snapshot, --last-snapshot-path
- follow FreeDesktop directories specs:  
- new install system: use more common steps (./configure; make; sudo make install)

### Removed

- --safe-links for save/restore (this means copy symlinks as symlinks)

## [0.9.20] (2009-04-06)

### Uncategorized

- smart remove: fix an important bug and make it more verbose in syslog
- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)

## [0.9.18] (2009-04-02)

### Uncategorized

- update translations from Launchpad
- update Slovak translation (Tomáš Vadina <kyberdev@gmail.com>)
- update French translation (Michel Corps <mahikeulbody@gmail.com>)
- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- GNOME bugfix: fix a crush in files view for files with special characters (ex: "a%20b")
- GNOME SettingsDialog bugfix: if snapshots path is a new created folder, snapshots navigation (files view) don't work
- update doc
- GNOME & KDE4 MainWindow: Rename "Places" list with "Snapshots"
- GNOME SettingsDialog bugfix: modify something, then press cancel. If you reopen the dialog it show wrong values (the ones before cancel)
- GNOME & KDE4: add root mode menu entries (use gksu for gnome and kdesudo for kde)
- GNOME & KDE4: MainWindow - Files view: if the current directory don't exists in current snapshot display a message
- SettingDialog: add an expert option to enable to schedule automatic backups per directory
- SettingDialog: schedule automatic backups - if the application can't find crontab it show an error
- SettingDialog: if the application can't write in snapshots directory there should be an error message
- GNOME & KDE4: rework settings dialog
- SettingDialog: add an option to enable/disable notifications

### Added

- Polish translation (Paweł Hołuj <pholuj@gmail.com>)
- cron in common package dependencies

## [0.9.16.1] (2009-03-16)

### Fixed

- a bug/crush for French version

## [0.9.16] (2009-03-13)

### Uncategorized

- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)
- update Swedish translation (Niklas Grahn <terra.unknown@yahoo.com>)
- update French translation (Michel Corps <mahikeulbody@gmail.com>)
- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- update Slovenian translation (Vanja Cvelbar <cvelbar@gmail.com>)
- don't show the snapshot that is being taken in snapshots list
- GNOME & KDE4: when the application starts and snapshots directory don't exists show a messagebox
- give more information for 'take snapshot' progress (to prove that is not blocked)
- MainWindow: rename 'Timeline' column with 'Snapshots'
- when it tries to take a snapshot if the snapshots directory don't exists  
- GNOME & KDE4: add notify if the snapshots directory don't exists
- KDE4: rework MainWindow

### Added

- Slovak translation (Tomáš Vadina <kyberdev@gmail.com>)

## [0.9.14] (2009-03-05)

### Uncategorized

- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- update Swedish translation (Niklas Grahn <terra.unknown@yahoo.com>)
- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)
- update French translation (Michel Corps <mahikeulbody@gmail.com>)
- GNOME & KDE4: rework MainWindow
- GNOME & KDE4: rework SettingsDialog
- GNOME & KDE4: add "smart" remove

## [0.9.12] (2009-02-28)

### Fixed

- now if you include ".abc" folder and exclude ".*", ".abc" will be saved in the snapshot
- bookmarks with special characters

### Uncategorized

- KDE4: add help

### Added

- Slovenian translation (Vanja Cvelbar <cvelbar@gmail.com>)

## [0.9.10] (2009-02-24)

### Added

- Swedish translation (Niklas Grahn <terra.unknown@yahoo.com>)

### Uncategorized

- KDE4: drop and drop from backintime files view to any file manager

### Fixed

- fix a segfault when running from cron

## [0.9.8] (2009-02-20)

### Uncategorized

- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)
- unsafe links are ignored (that means that a link to a file/directory outside of include directories are ignored)
- KDE4: add copy to clipboard
- KDE4: sort files by name, size or date
- cron 5/10 minutes: replace multiple lines with a single crontab line using divide (*/5 or */10)
- cron: when called from cron redirect output (stdout & stderr) to /dev/null

### Fixed

- unable to restore files that contains space char in their name

## [0.9.6] (2009-02-09)

### Uncategorized

- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)
- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- GNOME: update docbook
- KDE4: add snapshots dialog
- GNOME & KDE4: add update snapshots button
- GNOME: handle special folders icons (home, desktop)

## [0.9.4] (2009-01-30)

### Uncategorized

- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- gnome: better handling of 'take snapshot' status icon
- KDE4 (>= 4.1): first version (not finished)
- update man

## [0.9.2] (2009-01-16)

### Uncategorized

- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)
- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- replace diff with rsync to check if a new snapshot is needed
- code cleanup

### Fixed

- if you add "/a" in include directories and "/a/b" in exclude patterns, "/a/b*" items 
- it does not include ".*" items even if they are not excluded  

### Added

- show hidden & backup files toggle button for files view

## [0.9] (2009-01-09)

### Uncategorized

- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)
- make deb packages more debian friendly (thanks to Michael Wiedmann <mw@miwie.in-berlin.de>)
- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- better separation between common and gnome specific files and  
- code cleanup

### Fixed

- when you open snapshots dialog for the second time ( or more ) and you make a diff  

## [0.8.20] (2008-12-22)

### Fixed

- sorting files/directories by name is now case insensitive

### Uncategorized

- getmessages.sh: ignore "gtk-" items (this are gtk stock item ids and should not be changed)

## [0.8.18] (2008-12-17)

### Uncategorized

- update man/docbook

### Added

- sort columns in MainWindow/FileView (by name, by size or by date) and SnapshotsDialog (by date)

### Fixed

- German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)

## [0.8.16] (2008-12-11)

### Uncategorized

- add Drag & Drop from MainWindow: FileView/SnapshotsDialog to Nautilus
- update German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)

## [0.8.14] (2008-12-07)

### Added

- more command line parameters ( --version, --snapshots, --help )

### Fixed

- a crush for getting info on dead symbolic links

### Uncategorized

- when taking a new backup based on the previous one don't copy the previous extra info (ex: name)
- copy unsafe links when taking a snapshot

## [0.8.12] (2008-12-01)

### Added

- German translation (Michael Wiedmann <mw@miwie.in-berlin.de>)
- SnapshotNameDialog
- Name/Remove snapshot in main toolbar

### Changed

- the way it detects if the mainwindow is the active window (no dialogs)

### Uncategorized

- toolbars: show icons only
- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)

## [0.8.10] (2008-11-22)

### Uncategorized

- SnapshotsDialog: add right-click popup-menu and a toolbar with copy & restore buttons
- use a more robust backup lock file
- log using syslog
- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)

### Fixed

- a small bug in copy to clipboard

## [0.8.8] (2008-11-19)

### Uncategorized

- SnapshotsDialog: add diff
- update Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)

## [0.8.6] (2008-11-17)

### Fixed

- change backup path crush

### Added

- SnapshotsDialog

## [0.8.2] (2008-11-14)

### Uncategorized

- add right-click menu in files list: open (using gnome-open), copy (you can paste in Nautilus), restore (for snapshots only)

### Added

- Copy toolbar button for files list

## [0.8.1] (2008-11-10)

### Added

- every 5/10 minutes automatic backup

## [0.8] (2008-11-07)

### Uncategorized

- don't show backup files (*~)
- makedeb.sh: make a single package with all languages included
- install.sh: install all languages
- the application can be started with a 'path' to a folder or file as command line parameter
- when the application start, if it is already running pass its command line to the first instance (this allow a basic integration with file-managers - see README)

### Added

- backup files to default exclude patterns (*~)
- English manual (man)
- English help (docbook)
- help button in main toolbar

### Fixed

- when the application was started a second time it raise the first application's window but not always focused

## [0.7.4] (2008-11-03)

### Uncategorized

- if there is already a GUI instance running raise it

### Added

- Spanish translation (Francisco Manuel García Claramonte <franciscomanuel.garcia@hispalinux.es>)

## [0.7.2] (2008-10-28)

### Uncategorized

- better integration with gnome icons (use mime-types)
- remember last path
- capitalize month in timeline (bug in french translation)

## [0.7] (2008-10-22)

### Fixed

- cron segfault
- a crush when launched the very first time (not configured)

### Uncategorized

- multi-lingual support

### Added

- French translation

## [0.6.4] (2008-10-20)

### Removed

- About & Settings dialogs from the pager

### Uncategorized

- allow only one instance of the application

## [0.6.2] (2008-10-16)

### Uncategorized

- remember window position & size

## [0.6] (2008-10-13)

### Uncategorized

- when it make a snapshot it display an icon in systray area
- the background color for group items in timeline and places reflect more 
- during restore only restore button is grayed ( even if everything is blocked )

## [0.5.1] (2008-10-10)

### Added

- size & date columns in files view

### Changed

- some texts

## [0.5] (2008-10-03)

### Uncategorized

- This is the first release.

<!-- Template
## Unreleased
### Changed
### Added
### Removed
### Fixed
-->

[2.0.0]: https://github.com/bit-team/backintime/releases/tag/v2.0.0
[1.6.2]: https://github.com/bit-team/backintime/releases/tag/v1.6.2
[1.6.1]: https://github.com/bit-team/backintime/releases/tag/v1.6.1
[1.6.0]: https://github.com/bit-team/backintime/releases/tag/v1.6.0
[1.5.6]: https://github.com/bit-team/backintime/releases/tag/v1.5.6
[1.5.5]: https://github.com/bit-team/backintime/releases/tag/v1.5.5
[1.5.4]: https://github.com/bit-team/backintime/releases/tag/v1.5.4
[1.5.3]: https://github.com/bit-team/backintime/releases/tag/v1.5.3
[1.5.2]: https://github.com/bit-team/backintime/releases/tag/v1.5.2
[1.5.1]: https://github.com/bit-team/backintime/releases/tag/v1.5.1
[1.5.0]: https://github.com/bit-team/backintime/releases/tag/v1.5.0
[1.4.3]: https://github.com/bit-team/backintime/releases/tag/v1.4.3
[1.4.1]: https://github.com/bit-team/backintime/releases/tag/v1.4.1
[1.4.0]: https://github.com/bit-team/backintime/releases/tag/v1.4.0
[1.3.3]: https://github.com/bit-team/backintime/releases/tag/v1.3.3
[1.3.2]: https://github.com/bit-team/backintime/releases/tag/v1.3.2
[1.3.1]: https://github.com/bit-team/backintime/releases/tag/v1.3.1
[1.3.0]: https://github.com/bit-team/backintime/releases/tag/v1.3.0
[1.2.1]: https://github.com/bit-team/backintime/releases/tag/v1.2.1
[1.2.0]: https://github.com/bit-team/backintime/releases/tag/v1.2.0
[1.1.24]: https://github.com/bit-team/backintime/releases/tag/v1.1.24
[1.1.22]: https://github.com/bit-team/backintime/releases/tag/v1.1.22
[1.1.20]: https://github.com/bit-team/backintime/releases/tag/v1.1.20
[1.1.18]: https://github.com/bit-team/backintime/releases/tag/v1.1.18
[1.1.16]: https://github.com/bit-team/backintime/releases/tag/v1.1.16
[1.1.14]: https://github.com/bit-team/backintime/releases/tag/v1.1.14
[1.1.12]: https://github.com/bit-team/backintime/releases/tag/v1.1.12
[1.1.10]: https://github.com/bit-team/backintime/releases/tag/v1.1.10
[1.1.8]: https://github.com/bit-team/backintime/releases/tag/v1.1.8
[1.1.6]: https://github.com/bit-team/backintime/releases/tag/v1.1.6
[1.1.4]: https://github.com/bit-team/backintime/releases/tag/v1.1.4
[1.1.2]: https://github.com/bit-team/backintime/releases/tag/v1.1.2
[1.1.0]: https://github.com/bit-team/backintime/releases/tag/v1.1.0
[1.0.40]: https://github.com/bit-team/backintime/releases/tag/v1.0.40
[1.0.38]: https://github.com/bit-team/backintime/releases/tag/v1.0.38
[1.0.36]: https://github.com/bit-team/backintime/releases/tag/v1.0.36
[1.0.34]: https://github.com/bit-team/backintime/releases/tag/v1.0.34
[1.0.32]: https://github.com/bit-team/backintime/releases/tag/v1.0.32
[1.0.30]: https://github.com/bit-team/backintime/releases/tag/v1.0.30
[1.0.28]: https://github.com/bit-team/backintime/releases/tag/v1.0.28
[1.0.26]: https://github.com/bit-team/backintime/releases/tag/v1.0.26
[1.0.24]: https://github.com/bit-team/backintime/releases/tag/v1.0.24
[1.0.22]: https://github.com/bit-team/backintime/releases/tag/v1.0.22
[1.0.20]: https://github.com/bit-team/backintime/releases/tag/v1.0.20
[1.0.18]: https://github.com/bit-team/backintime/releases/tag/v1.0.18
[1.0.16]: https://github.com/bit-team/backintime/releases/tag/v1.0.16
[1.0.14]: https://github.com/bit-team/backintime/releases/tag/v1.0.14
[1.0.12]: https://github.com/bit-team/backintime/releases/tag/v1.0.12
[1.0.10]: https://github.com/bit-team/backintime/releases/tag/v1.0.10
[1.0.8]: https://github.com/bit-team/backintime/releases/tag/v1.0.8
[1.0.6]: https://github.com/bit-team/backintime/releases/tag/v1.0.6
[1.0.4]: https://github.com/bit-team/backintime/releases/tag/v1.0.4
[1.0.2]: https://github.com/bit-team/backintime/releases/tag/v1.0.2
[1.0]: https://github.com/bit-team/backintime/releases/tag/v1.0
[0.9.26]: https://github.com/bit-team/backintime/releases/tag/v0.9.26
[0.9.24]: https://github.com/bit-team/backintime/releases/tag/v0.9.24
[0.9.22.1]: https://github.com/bit-team/backintime/releases/tag/v0.9.22.1
[0.9.22]: https://github.com/bit-team/backintime/releases/tag/v0.9.22
[0.9.20]: https://github.com/bit-team/backintime/releases/tag/v0.9.20
[0.9.18]: https://github.com/bit-team/backintime/releases/tag/v0.9.18
[0.9.16.1]: https://github.com/bit-team/backintime/releases/tag/v0.9.16.1
[0.9.16]: https://github.com/bit-team/backintime/releases/tag/v0.9.16
[0.9.14]: https://github.com/bit-team/backintime/releases/tag/v0.9.14
[0.9.12]: https://github.com/bit-team/backintime/releases/tag/v0.9.12
[0.9.10]: https://github.com/bit-team/backintime/releases/tag/v0.9.10
[0.9.8]: https://github.com/bit-team/backintime/releases/tag/v0.9.8
[0.9.6]: https://github.com/bit-team/backintime/releases/tag/v0.9.6
[0.9.4]: https://github.com/bit-team/backintime/releases/tag/v0.9.4
[0.9.2]: https://github.com/bit-team/backintime/releases/tag/v0.9.2
[0.9]: https://github.com/bit-team/backintime/releases/tag/v0.9
[0.8.20]: https://github.com/bit-team/backintime/releases/tag/v0.8.20
[0.8.18]: https://github.com/bit-team/backintime/releases/tag/v0.8.18
[0.8.16]: https://github.com/bit-team/backintime/releases/tag/v0.8.16
[0.8.14]: https://github.com/bit-team/backintime/releases/tag/v0.8.14
[0.8.12]: https://github.com/bit-team/backintime/releases/tag/v0.8.12
[0.8.10]: https://github.com/bit-team/backintime/releases/tag/v0.8.10
[0.8.8]: https://github.com/bit-team/backintime/releases/tag/v0.8.8
[0.8.6]: https://github.com/bit-team/backintime/releases/tag/v0.8.6
[0.8.2]: https://github.com/bit-team/backintime/releases/tag/v0.8.2
[0.8.1]: https://github.com/bit-team/backintime/releases/tag/v0.8.1
[0.8]: https://github.com/bit-team/backintime/releases/tag/v0.8
[0.7.4]: https://github.com/bit-team/backintime/releases/tag/v0.7.4
[0.7.2]: https://github.com/bit-team/backintime/releases/tag/v0.7.2
[0.7]: https://github.com/bit-team/backintime/releases/tag/v0.7
[0.6.4]: https://github.com/bit-team/backintime/releases/tag/v0.6.4
[0.6.2]: https://github.com/bit-team/backintime/releases/tag/v0.6.2
[0.6]: https://github.com/bit-team/backintime/releases/tag/v0.6
[0.5.1]: https://github.com/bit-team/backintime/releases/tag/v0.5.1
[0.5]: https://github.com/bit-team/backintime/releases/tag/v0.5
