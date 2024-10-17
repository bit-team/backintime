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


class ExpertOptionsTab(QDialog):
    """The 'Expert Options' tab in the Manage Profiles dialog."""

    def __init__(self, parent):
        super().__init__(parent=parent)

        self._parent_dialog = parent

        tab_layout = QVBoxLayout(self)

        label = QLabel('<strong>{}</strong> {}'.format(
            _('Caution:'),
            _('These options are for advanced configurations. Modify '
              'only if fully aware of their implications.')))
        label.setWordWrap(True)
        tab_layout.addWidget(label)

        # --- rsync with nice ---
        tab_layout.addWidget(QLabel(
            _("Run 'rsync' with '{cmd}':").format(cmd='nice')))

        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)  # left indent
        tab_layout.addLayout(grid)

        self.cbNiceOnCron = QCheckBox(
            _('as cron job')
            + self._default_string(self.config.DEFAULT_RUN_NICE_FROM_CRON),
            self)
        grid.addWidget(self.cbNiceOnCron, 0, 1)

        self.cbNiceOnRemote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_NICE_ON_REMOTE),
            self)
        grid.addWidget(self.cbNiceOnRemote, 1, 1)

        # --- rsync with ionice ---
        tab_layout.addWidget(QLabel(
            _("Run 'rsync' with '{cmd}':").format(cmd='ionice')))
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 20)
        tab_layout.addLayout(grid)

        self.cbIoniceOnCron = QCheckBox(
            _('as cron job')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_FROM_CRON),
            self)
        grid.addWidget(self.cbIoniceOnCron, 0, 1)

        self.cbIoniceOnUser = QCheckBox(
            _('when taking a manual snapshot')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_FROM_USER),
            self)
        grid.addWidget(self.cbIoniceOnUser, 1, 1)

        self.cbIoniceOnRemote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_IONICE_ON_REMOTE),
            self)
        grid.addWidget(self.cbIoniceOnRemote, 2, 1)

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

        self.cbNocacheOnLocal = QCheckBox(
            _('on local machine')
            + self._default_string(self.config.DEFAULT_RUN_NOCACHE_ON_LOCAL),
            self)
        grid.addWidget(self.cbNocacheOnLocal, 1, 1)
        self.cbNocacheOnLocal.setEnabled(nocache_available)

        self.cbNocacheOnRemote = QCheckBox(
            _('on remote host')
            + self._default_string(self.config.DEFAULT_RUN_NOCACHE_ON_REMOTE),
            self)
        grid.addWidget(self.cbNocacheOnRemote, 2, 1)

        # --- redirect output ---
        self.cbRedirectStdoutInCron = QCheckBox(
            _('Redirect stdout to /dev/null in cronjobs.')
            + self._default_string(
                self.config.DEFAULT_REDIRECT_STDOUT_IN_CRON),
            self)
        qttools.set_wrapped_tooltip(
            self.cbRedirectStdoutInCron,
            _('Cron will automatically send an email with attached output '
              'of cronjobs if an MTA is installed.')
        )
        tab_layout.addWidget(self.cbRedirectStdoutInCron)

        self.cbRedirectStderrInCron = QCheckBox(
            _('Redirect stderr to /dev/null in cronjobs.')
            + self._default_string(
                self.config.DEFAULT_REDIRECT_STDERR_IN_CRON),
            self)
        qttools.set_wrapped_tooltip(
            self.cbRedirectStderrInCron,
            _('Cron will automatically send an email with attached errors '
              'of cronjobs if an MTA is installed.')
        )
        tab_layout.addWidget(self.cbRedirectStderrInCron)

        # bandwidth limit
        hlayout = QHBoxLayout()
        tab_layout.addLayout(hlayout)

        self.spbBwlimit = QSpinBox(self)
        self.spbBwlimit.setSuffix(' ' + _('KB/sec'))
        self.spbBwlimit.setSingleStep(100)
        self.spbBwlimit.setRange(0, 1000000)

        self.cbBwlimit = StateBindCheckBox(
            _('Limit rsync bandwidth usage:'), self, self.spbBwlimit)
        hlayout.addWidget(self.cbBwlimit)
        hlayout.addWidget(self.spbBwlimit)
        hlayout.addStretch()

        qttools.set_wrapped_tooltip(
            self.cbBwlimit,
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

        self.cbPreserveAcl = QCheckBox(_('Preserve ACL'), self)
        qttools.set_wrapped_tooltip(
            self.cbPreserveAcl,
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
        tab_layout.addWidget(self.cbPreserveAcl)

        self.cbPreserveXattr = QCheckBox(
            _('Preserve extended attributes (xattr)'), self)
        qttools.set_wrapped_tooltip(
            self.cbPreserveXattr,
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
        tab_layout.addWidget(self.cbPreserveXattr)

        self.cbCopyUnsafeLinks = QCheckBox(
            _('Copy unsafe links (works only with absolute links)'), self)
        qttools.set_wrapped_tooltip(
            self.cbCopyUnsafeLinks,
            [
                "Uses 'rsync --copy-unsafe-links'. From 'man rsync':",
                'This tells rsync to copy the referent of symbolic links that '
                'point outside the copied tree. Absolute symlinks are also '
                'treated like ordinary files, and so are any symlinks in the '
                'source path itself when --relative is used. This option has '
                'no additional effect if --copy-links was also specified.'
            ]
        )
        tab_layout.addWidget(self.cbCopyUnsafeLinks)

        self.cbCopyLinks = QCheckBox(
            _('Copy links (dereference symbolic links)'), self)
        qttools.set_wrapped_tooltip(
            self.cbCopyLinks,
            [
                "Uses 'rsync --copy-links'. From 'man rsync':",
                'When symlinks are encountered, the item that they point to '
                '(the referent) is copied, rather than the symlink. In older '
                'versions of rsync, this option also had the side-effect of '
                'telling the receiving side to follow symlinks, such as '
                'symlinks to directories. In a modern rsync such as this one,'
                ' you will need to specify --keep-dirlinks (-K) to get this '
                'extra behavior. The only exception is when sending files to '
                'an rsync that is too old to understand -K -- in that case, '
                'the -L option will still have the side-effect of -K on that '
                'older receiving rsync.'
            ]
        )
        tab_layout.addWidget(self.cbCopyLinks)

        # one file system option
        self.cbOneFileSystem = QCheckBox(
            _('Restrict to one file system'), self)
        qttools.set_wrapped_tooltip(
            self.cbOneFileSystem,
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
        tab_layout.addWidget(self.cbOneFileSystem)

        # additional rsync options
        tooltip = _('Options must be quoted e.g. {example}.').format(
            example='--exclude-from="/path/to/my exclude file"')

        self.txtRsyncOptions = QLineEdit(self)
        self.txtRsyncOptions.editingFinished.connect(
            self._slot_rsync_options_editing_finished)
        self.txtRsyncOptions.setToolTip(tooltip)

        self.cbRsyncOptions = StateBindCheckBox(
            _('Paste additional options to rsync'),
            self,
            self.txtRsyncOptions)

        self.cbRsyncOptions.setToolTip(tooltip)

        # ssh prefix
        tooltip = [
            _('Prefix to run before every command on remote host.'),
            _("Variables need to be escaped with \\$FOO. This doesn't touch "
              'rsync. So to add a prefix for rsync use "{example_value}" with '
              '{rsync_options_value}.').format(
                  example_value=self.cbRsyncOptions.text(),
                  rsync_options_value \
                      ='--rsync-path="FOO=bar:\\$FOO /usr/bin/rsync"'),
            '',
            '{default}: {def_value}'.format(
                default=_('default'),
                def_value=self.config.DEFAULT_SSH_PREFIX)
        ]
        self.txtSshPrefix = QLineEdit(self)
        qttools.set_wrapped_tooltip(self.txtSshPrefix, tooltip)
        self.cbSshPrefix = StateBindCheckBox(
            _('Add prefix to SSH commands'), self, self.txtSshPrefix)
        qttools.set_wrapped_tooltip(self.cbSshPrefix, tooltip)

        sub_grid = QGridLayout()
        sub_grid.addWidget(self.cbRsyncOptions, 0, 0)
        sub_grid.addWidget(self.txtRsyncOptions, 0, 1)
        sub_grid.addWidget(self.cbSshPrefix, 1, 0)
        sub_grid.addWidget(self.txtSshPrefix, 1, 1)
        tab_layout.addLayout(sub_grid)

        self.cbSshCheckPing = QCheckBox(_('Check if remote host is online'))
        qttools.set_wrapped_tooltip(
            self.cbSshCheckPing,
            _('Warning: If disabled and the remote host is not available, '
              'this could lead to some weird errors.')
        )
        self.cbSshCheckCommands = QCheckBox(
            _('Check if remote host supports all necessary commands.'))
        qttools.set_wrapped_tooltip(
            self.cbSshCheckCommands,
            _('Warning: If disabled and the remote host does not support all '
              'necessary commands, this could lead to some weird errors.')
        )
        tab_layout.addWidget(self.cbSshCheckPing)
        tab_layout.addWidget(self.cbSshCheckCommands)

        #
        tab_layout.addStretch()


    @property
    def config(self) -> config.Config:
        return self._parent_dialog.config

    def _default_string(self, value: bool) -> str:
        return ' ' + _('(default: {})').format(
            _('enabled') if value else _('disabled'))

    def load_values(self):
        self.cbNiceOnCron.setChecked(self.config.niceOnCron())
        self.cbIoniceOnCron.setChecked(self.config.ioniceOnCron())
        self.cbIoniceOnUser.setChecked(self.config.ioniceOnUser())
        self.cbNiceOnRemote.setChecked(self.config.niceOnRemote())
        self.cbIoniceOnRemote.setChecked(self.config.ioniceOnRemote())
        self.cbNocacheOnLocal.setChecked(
            self.config.nocacheOnLocal() and self.cbNocacheOnLocal.isEnabled())
        self.cbNocacheOnRemote.setChecked(self.config.nocacheOnRemote())
        self.cbRedirectStdoutInCron.setChecked(
            self.config.redirectStdoutInCron())
        self.cbRedirectStderrInCron.setChecked(
            self.config.redirectStderrInCron())
        self.cbBwlimit.setChecked(self.config.bwlimitEnabled())
        self.spbBwlimit.setValue(self.config.bwlimit())
        self.cbPreserveAcl.setChecked(self.config.preserveAcl())
        self.cbPreserveXattr.setChecked(self.config.preserveXattr())
        self.cbCopyUnsafeLinks.setChecked(self.config.copyUnsafeLinks())
        self.cbCopyLinks.setChecked(self.config.copyLinks())
        self.cbOneFileSystem.setChecked(self.config.oneFileSystem())
        self.cbRsyncOptions.setChecked(self.config.rsyncOptionsEnabled())
        self.txtRsyncOptions.setText(self.config.rsyncOptions())
        self.cbSshPrefix.setChecked(self.config.sshPrefixEnabled())
        self.txtSshPrefix.setText(self.config.sshPrefix())
        self.cbSshCheckPing.setChecked(self.config.sshCheckPingHost())
        self.cbSshCheckCommands.setChecked(self.config.sshCheckCommands())

    def store_values(self):
        self.config.setNiceOnCron(self.cbNiceOnCron.isChecked())
        self.config.setIoniceOnCron(self.cbIoniceOnCron.isChecked())
        self.config.setIoniceOnUser(self.cbIoniceOnUser.isChecked())
        self.config.setNiceOnRemote(self.cbNiceOnRemote.isChecked())
        self.config.setIoniceOnRemote(self.cbIoniceOnRemote.isChecked())
        self.config.setNocacheOnLocal(self.cbNocacheOnLocal.isChecked())
        self.config.setNocacheOnRemote(self.cbNocacheOnRemote.isChecked())
        self.config.setRedirectStdoutInCron(
            self.cbRedirectStdoutInCron.isChecked())
        self.config.setRedirectStderrInCron(
            self.cbRedirectStderrInCron.isChecked())
        self.config.setBwlimit(self.cbBwlimit.isChecked(),
                               self.spbBwlimit.value())
        self.config.setPreserveAcl(self.cbPreserveAcl.isChecked())
        self.config.setPreserveXattr(self.cbPreserveXattr.isChecked())
        self.config.setCopyUnsafeLinks(self.cbCopyUnsafeLinks.isChecked())
        self.config.setCopyLinks(self.cbCopyLinks.isChecked())
        self.config.setOneFileSystem(self.cbOneFileSystem.isChecked())
        self.config.setRsyncOptions(self.cbRsyncOptions.isChecked(),
                                    self.txtRsyncOptions.text())
        self.config.setSshPrefix(self.cbSshPrefix.isChecked(),
                                 self.txtSshPrefix.text())
        self.config.setSshCheckPingHost(self.cbSshCheckPing.isChecked())
        self.config.setSshCheckCommands(self.cbSshCheckCommands.isChecked())

    def update_items_state(self, enabled: bool):
        self.cbNiceOnRemote.setEnabled(enabled)
        self.cbIoniceOnRemote.setEnabled(enabled)
        self.cbNocacheOnRemote.setEnabled(enabled)
        self.cbSshPrefix.setVisible(enabled)
        self.txtSshPrefix.setVisible(enabled)
        self.cbSshCheckPing.setVisible(enabled)
        self.cbSshCheckCommands.setVisible(enabled)

    def _slot_rsync_options_editing_finished(self):
        """When editing the rsync options is finished warn and remove
        --old-args option if present.
        """
        txt = self.txtRsyncOptions.text()

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
            self.txtRsyncOptions.setText(txt)
