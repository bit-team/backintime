# SPDX-FileCopyrightText: © 2008-2022 Oprea Dan
# SPDX-FileCopyrightText: © 2008-2022 Bart de Koning
# SPDX-FileCopyrightText: © 2008-2022 Richard Bailey
# SPDX-FileCopyrightText: © 2008-2022 Germar Reitze
# SPDX-FileCopyrightText: © 2008-2022 Taylor Raak
# SPDX-FileCopyrightText: © 2024 Christian BUHTZ <c.buhtz@posteo.jp>
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of the program "Back In Time" which is released under GNU
# General Public License v2 (GPLv2). See LICENSES directory or go to
# <https://spdx.org/licenses/GPL-2.0-or-later.html>.
"""About Export Options tab"""
from PyQt6.QtWidgets import (QDialog,
                             QVBoxLayout,
                             QHBoxLayout,
                             QGridLayout,
                             QLabel,
                             QSpinBox,
                             QLineEdit,
                             QCheckBox)
import config
import tools
import qttools
import messagebox
from manageprofiles.statebindcheckbox import StateBindCheckBox
from manageprofiles.copylinkswidget import CopySymlinksWidget


class ExpertOptionsTab(QDialog):
    """The 'Expert Options' tab in the Manage Profiles dialog."""
    # pylint: disable=too-many-instance-attributes

    def __init__(self, parent):  # noqa: PLR0915
        # pylint: disable=too-many-statements
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        label = QLabel(
            '<strong>' + _('Caution:') + '</strong> ' + _(
                'These options are for advanced configurations. Modify '
                'only if fully aware of their implications.')
        )
        label.setWordWrap(True)
        tab_layout.addWidget(label)

        # --- rsync with nice ---
        tab_layout.addWidget(QLabel(
            _("Run 'rsync' with '{cmd}':").format(cmd='nice')))

        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)  # left indent
        tab_layout.addLayout(grid)

        self._cb_nice_on_cron = QCheckBox(
            _('as cron job')
            + self._default_string(self.config.DEFAULT_RUN_NICE_FROM_CRON),
            self)
        grid.addWidget(self._cb_nice_on_cron, 0, 1)

        self._cb_nice_on_remote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_NICE_ON_REMOTE),
            self)
        grid.addWidget(self._cb_nice_on_remote, 1, 1)

        # --- rsync with ionice ---
        tab_layout.addWidget(QLabel(
            _("Run 'rsync' with '{cmd}':").format(cmd='ionice')))
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        tab_layout.addLayout(grid)

        self._cb_ionice_on_cron = QCheckBox(
            _('as cron job')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_FROM_CRON),
            self)
        grid.addWidget(self._cb_ionice_on_cron, 0, 1)

        self._cb_ionice_on_user = QCheckBox(
            _('when taking a manual backup')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_FROM_USER),
            self)
        grid.addWidget(self._cb_ionice_on_user, 1, 1)

        self._cb_ionice_on_remote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_ON_REMOTE),
            self)
        grid.addWidget(self._cb_ionice_on_remote, 2, 1)

        # --- rsync with nocache ---
        tab_layout.addWidget(QLabel(
            _("Run 'rsync' with '{cmd}':").format(cmd='nocache')))

        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        tab_layout.addLayout(grid)

        nocache_available = tools.checkCommand('nocache')
        if not nocache_available:
            grid.addWidget(
                QLabel(
                    '<em>'
                    + _("Please install 'nocache' to enable this option.")
                    + '</em>'),
                0,
                1)

        self._cb_nocache_on_local = QCheckBox(
            _('on local machine')
            + self._default_string(self.config.DEFAULT_RUN_NOCACHE_ON_LOCAL),
            self)
        grid.addWidget(self._cb_nocache_on_local, 1, 1)
        self._cb_nocache_on_local.setEnabled(nocache_available)

        self._cb_nocache_on_remote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_NOCACHE_ON_REMOTE),
            self)
        grid.addWidget(self._cb_nocache_on_remote, 2, 1)

        # --- redirect output ---
        self._cb_redirect_stdout_cron = QCheckBox(
            _('Redirect stdout to /dev/null in cronjobs.')
            + self._default_string(
                self.config.DEFAULT_REDIRECT_STDOUT_IN_CRON),
            self)
        qttools.set_wrapped_tooltip(
            self._cb_redirect_stdout_cron,
            _('Cron will automatically send an email with attached output '
              'of cronjobs if an MTA is installed.')
        )
        tab_layout.addWidget(self._cb_redirect_stdout_cron)

        self._cb_redirect_stderr_cron = QCheckBox(
            _('Redirect stderr to /dev/null in cronjobs.')
            + self._default_string(
                self.config.DEFAULT_REDIRECT_STDERR_IN_CRON),
            self)
        qttools.set_wrapped_tooltip(
            self._cb_redirect_stderr_cron,
            _('Cron will automatically send an email with attached errors '
              'of cronjobs if an MTA is installed.')
        )
        tab_layout.addWidget(self._cb_redirect_stderr_cron)

        # bandwidth limit
        hlayout = QHBoxLayout()
        tab_layout.addLayout(hlayout)

        self._spb_bwlimit = QSpinBox(self)
        self._spb_bwlimit.setSuffix(' ' + _('KB/sec'))
        self._spb_bwlimit.setSingleStep(100)
        self._spb_bwlimit.setRange(0, 1000000)

        self._cb_bwlimit = StateBindCheckBox(
            _('Limit rsync bandwidth usage:'), self, self._spb_bwlimit)
        hlayout.addWidget(self._cb_bwlimit)
        hlayout.addWidget(self._spb_bwlimit)
        hlayout.addStretch()

        qttools.set_wrapped_tooltip(
            self._cb_bwlimit,
            [
                "Uses 'rsync --bwlimit=RATE'. From 'man rsync':",
                'This option allows you to specify the maximum transfer rate '
                'for the data sent over the socket, specified in units per '
                'second. The RATE value can be suffixed with a string to '
                'indicate a size multiplier, and may be a fractional value '
                '(e.g. "--bwlimit=1.5m").',
                'If no suffix is specified, the value will be assumed to be '
                'in units of 1024 bytes (as if "K" or "KiB" had been '
                'appended).',
                'See the --max-size option for a description of all the '
                'available suffixes. A value of zero specifies no limit.'
                '',
                'For backward-compatibility reasons, the rate limit will be '
                'rounded to the nearest KiB unit, so no rate smaller than '
                '1024 bytes per second is possible.',
                '',
                'Rsync writes data over the socket in blocks, and this option '
                'both limits the size of the blocks that rsync writes, and '
                'tries to keep the average transfer rate at the requested '
                'limit. Some "burstiness" may be seen where rsync writes out '
                'a block of data and then sleeps to bring the average rate '
                'into compliance.',
                '',
                'Due to the internal buffering of data, the --progress '
                'option may not be an accurate reflection on how fast the '
                'data is being sent. This is because some files can show up '
                'as being rapidly sent when the data is quickly buffered, '
                'while other can show up as very slow when the flushing of '
                'the output buffer occurs. This may be fixed in a future '
                'version.'
            ]
        )

        self._cb_preserve_acl = QCheckBox(_('Preserve ACL'), self)
        qttools.set_wrapped_tooltip(
            self._cb_preserve_acl,
            [
                "Uses 'rsync -A'. From 'man rsync':",
                'This option causes rsync to update the destination ACLs to '
                'be the same as the source ACLs. The option also implies '
                '--perms.',
                '',
                'The source and destination systems must have compatible ACL '
                'entries for this option to work properly. See the '
                '--fake-super option for a way to backup and restore ACLs '
                'that are not compatible.'
            ]
        )
        tab_layout.addWidget(self._cb_preserve_acl)

        self._cb_preserve_xattr = QCheckBox(
            _('Preserve extended attributes (xattr)'), self)
        qttools.set_wrapped_tooltip(
            self._cb_preserve_xattr,
            [
                "Uses 'rsync -X'. From 'man rsync':",
                'This option causes rsync to update the destination extended '
                'attributes to be the same as the source ones.',
                '',
                'For systems that support extended-attribute namespaces, a '
                'copy being done by a super-user copies all namespaces '
                'except system.*. A normal user only copies the user.* '
                'namespace. To be able to backup and restore non-user '
                'namespaces as a normal user, see the --fake-super option.',
                '',
                'Note that this option does not copy rsyncs special xattr '
                'values (e.g. those used by --fake-super) unless you repeat '
                'the option (e.g. -XX). This "copy all xattrs" mode cannot be '
                'used with --fake-super.'
            ]
        )
        tab_layout.addWidget(self._cb_preserve_xattr)

        self._wdg_copy_links = CopySymlinksWidget(self)
        tab_layout.addWidget(self._wdg_copy_links)

        self._cb_copy_unsafe_links = QCheckBox(
            _('Copy external symbolic links as files'),
            self
        )
        qttools.set_wrapped_tooltip(
            self._cb_copy_unsafe_links,
            [
                'If enabled, symbolic links that point outside the backup '
                'source are copied as real files or directories. '
                'Links that point inside the source are kept as links.',
                'This avoids broken links in the backup, but may use more '
                'disk space.',
                'This option is automatically enabled when "Copy symbolic '
                'links as files" is enabled.',
                "Uses 'rsync --copy-unsafe-links'."
            ]
        )
        tab_layout.addWidget(self._cb_copy_unsafe_links)

        self._cb_copy_links = QCheckBox(
            _('Copy symbolic links as files'),
            self
        )
        qttools.set_wrapped_tooltip(
            self._cb_copy_links,
            [
                'If enabled, all symbolic links are replaced with the real '
                'files or directories they point to. This increases backup '
                'size and may store the same files multiple times.',
                "Uses 'rsync --copy-links'."
            ]
        )
        tab_layout.addWidget(self._cb_copy_links)

        # one file system option
        self._cb_one_filesystem = QCheckBox(
            _('Restrict to one file system'), self)
        qttools.set_wrapped_tooltip(
            self._cb_one_filesystem,
            [
                "Uses 'rsync --one-file-system'. From 'man rsync':",
                'This tells rsync to avoid crossing a filesystem boundary '
                'when recursing. This does not limit the user\'s ability '
                'to specify items to copy from multiple filesystems, just '
                'rsync\'s recursion through the hierarchy of each directory '
                'that the user specified, and also the analogous recursion '
                'on the receiving side during deletion. Also keep in mind '
                'that rsync treats a "bind" mount to the same device as '
                'being on the same filesystem.'
            ]
        )
        tab_layout.addWidget(self._cb_one_filesystem)

        # additional rsync options
        tooltip = _('Options must be quoted e.g. {example}.').format(
            example='--exclude-from="/path/to/my exclude file"')

        self._txt_rsync_options = QLineEdit(self)
        self._txt_rsync_options.editingFinished.connect(
            self._slot_rsync_options_editing_finished)
        self._txt_rsync_options.setToolTip(tooltip)

        self._cb_rsync_options = StateBindCheckBox(
            _('Paste additional options to rsync'),
            self,
            self._txt_rsync_options)

        self._cb_rsync_options.setToolTip(tooltip)

        # ssh prefix

        rsync_options_value = '--rsync-path="FOO=bar:\\$FOO /usr/bin/rsync"'
        tooltip = [
            _('Prefix to run before every command on remote host.'),
            _("Variables need to be escaped with \\$FOO. This doesn't touch "
              'rsync. So to add a prefix for rsync use "{example_value}" with '
              '{rsync_options_value}.').format(
                  example_value=self._cb_rsync_options.text(),
                  rsync_options_value=rsync_options_value),
            '',
            _('default') + ': ' + self.config.DEFAULT_SSH_PREFIX
        ]
        self._txt_ssh_prefix = QLineEdit(self)
        qttools.set_wrapped_tooltip(self._txt_ssh_prefix, tooltip)
        self._cb_ssh_prefix = StateBindCheckBox(
            _('Add prefix to SSH commands'), self, self._txt_ssh_prefix)
        qttools.set_wrapped_tooltip(self._cb_ssh_prefix, tooltip)

        sub_grid = QGridLayout()
        sub_grid.addWidget(self._cb_rsync_options, 0, 0)
        sub_grid.addWidget(self._txt_rsync_options, 0, 1)
        sub_grid.addWidget(self._cb_ssh_prefix, 1, 0)
        sub_grid.addWidget(self._txt_ssh_prefix, 1, 1)
        tab_layout.addLayout(sub_grid)

        self._cb_ssh_ping = QCheckBox(_('Check if remote host is online'))
        qttools.set_wrapped_tooltip(
            self._cb_ssh_ping,
            _('Warning: If disabled and the remote host is not available, '
              'this could lead to some weird errors.')
        )
        self._cb_ssh_check_commands = QCheckBox(
            _('Check if remote host supports all necessary commands.'))
        qttools.set_wrapped_tooltip(
            self._cb_ssh_check_commands,
            _('Warning: If disabled and the remote host does not support all '
              'necessary commands, this could lead to some weird errors.')
        )
        tab_layout.addWidget(self._cb_ssh_ping)
        tab_layout.addWidget(self._cb_ssh_check_commands)

        tab_layout.addStretch()

    @property
    def config(self) -> config.Config:
        """The config instance."""
        return self._parent_dialog.config

    def _default_string(self, value: bool) -> str:
        return ' ' + _('(default: {})').format(
            _('enabled') if value else _('disabled'))

    def load_values(self):
        """Load config values into the GUI"""

        self._cb_nice_on_cron.setChecked(self.config.niceOnCron())
        self._cb_ionice_on_cron.setChecked(self.config.ioniceOnCron())
        self._cb_ionice_on_user.setChecked(self.config.ioniceOnUser())
        self._cb_nice_on_remote.setChecked(self.config.niceOnRemote())
        self._cb_ionice_on_remote.setChecked(self.config.ioniceOnRemote())
        self._cb_nocache_on_local.setChecked(
            self.config.nocacheOnLocal()
            and self._cb_nocache_on_local.isEnabled())
        self._cb_nocache_on_remote.setChecked(self.config.nocacheOnRemote())
        self._cb_redirect_stdout_cron.setChecked(
            self.config.redirectStdoutInCron())
        self._cb_redirect_stderr_cron.setChecked(
            self.config.redirectStderrInCron())
        self._cb_bwlimit.setChecked(self.config.bwlimitEnabled())
        self._spb_bwlimit.setValue(self.config.bwlimit())
        self._cb_preserve_acl.setChecked(self.config.preserveAcl())
        self._cb_preserve_xattr.setChecked(self.config.preserveXattr())

        all_links = self.config.copyLinks()
        only_external = self.config.copyUnsafeLinks()
        self._wdg_copy_links.set_values(all_links, only_external)

        self._cb_copy_links.setChecked(self.config.copyLinks())
        self._cb_copy_unsafe_links.setChecked(self.config.copyUnsafeLinks())

        self._cb_one_filesystem.setChecked(self.config.oneFileSystem())
        self._cb_rsync_options.setChecked(self.config.rsyncOptionsEnabled())
        self._txt_rsync_options.setText(self.config.rsyncOptions())
        self._cb_ssh_prefix.setChecked(self.config.sshPrefixEnabled())
        self._txt_ssh_prefix.setText(self.config.sshPrefix())
        self._cb_ssh_ping.setChecked(self.config.sshCheckPingHost())
        self._cb_ssh_check_commands.setChecked(self.config.sshCheckCommands())

    def store_values(self):
        """Store values from GUI into the config"""

        self.config.setNiceOnCron(self._cb_nice_on_cron.isChecked())
        self.config.setIoniceOnCron(self._cb_ionice_on_cron.isChecked())
        self.config.setIoniceOnUser(self._cb_ionice_on_user.isChecked())
        self.config.setNiceOnRemote(self._cb_nice_on_remote.isChecked())
        self.config.setIoniceOnRemote(self._cb_ionice_on_remote.isChecked())
        self.config.setNocacheOnLocal(self._cb_nocache_on_local.isChecked())
        self.config.setNocacheOnRemote(self._cb_nocache_on_remote.isChecked())
        self.config.setRedirectStdoutInCron(
            self._cb_redirect_stdout_cron.isChecked())
        self.config.setRedirectStderrInCron(
            self._cb_redirect_stderr_cron.isChecked())
        self.config.setBwlimit(self._cb_bwlimit.isChecked(),
                               self._spb_bwlimit.value())
        self.config.setPreserveAcl(self._cb_preserve_acl.isChecked())
        self.config.setPreserveXattr(self._cb_preserve_xattr.isChecked())

        # self.config.setCopyUnsafeLinks(self._cb_copy_unsafe_links.isChecked())
        # self.config.setCopyLinks(self._cb_copy_links.isChecked())
        self.config.setCopyLinks(self._wdg_copy_links.all_links)
        self.config.setCopyUnsafeLinks(self._wdg_copy_links.only_external_links)

        self.config.setOneFileSystem(self._cb_one_filesystem.isChecked())
        self.config.setRsyncOptions(self._cb_rsync_options.isChecked(),
                                    self._txt_rsync_options.text())
        self.config.setSshPrefix(self._cb_ssh_prefix.isChecked(),
                                 self._txt_ssh_prefix.text())
        self.config.setSshCheckPingHost(self._cb_ssh_ping.isChecked())
        self.config.setSshCheckCommands(
            self._cb_ssh_check_commands.isChecked())

    def update_items_state(self, enabled: bool):
        """Update state of widgets based on changed profile mode."""
        self._cb_nice_on_remote.setEnabled(enabled)
        self._cb_ionice_on_remote.setEnabled(enabled)
        self._cb_nocache_on_remote.setEnabled(enabled)
        self._cb_ssh_prefix.setVisible(enabled)
        self._txt_ssh_prefix.setVisible(enabled)
        self._cb_ssh_ping.setVisible(enabled)
        self._cb_ssh_check_commands.setVisible(enabled)

    def _slot_rsync_options_editing_finished(self):
        """When editing the rsync options is finished warn and remove
        --old-args option if present.
        """
        txt = self._txt_rsync_options.text()

        if '--old-args' in txt:
            # No translation for this message because it is a rare case.
            messagebox.warning(
                text='Found rsync flag "--old-args". That flag will be removed'
                ' from the options because it conflicts with the flag "-s" '
                '(also known as "--secluded-args" or "--protected-args") which'
                ' is used by Back In Time to force the "new form of argument '
                'protection" in rsync.',
                widget_to_center_on=self
            )

            # Don't leave two-blank spaces between other arguments
            txt = txt.replace('--old-args ', '')
            txt = txt.replace(' --old-args', '')
            txt = txt.replace('--old-args', '')
            self._txt_rsync_options.setText(txt)
