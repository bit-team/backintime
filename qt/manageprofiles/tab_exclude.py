from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QLabel,
                             QCheckBox, QSpinBox, QInputDialog)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QBrush
import os

from tools import _, patternHasNotEncryptableWildcard
from .tree_widgets import BaseTreeWidget


class ExcludeTreeWidget(BaseTreeWidget):
    """Tree widget for displaying excluded files and directories."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels([_('Exclude patterns, files or directories'), 'Count'])
    
    def custom_sort_order(self, *args):
        """Handle custom sorting for exclude items."""
        if self.sort_loop:
            return
        self.sort_loop = True
        self.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.sort_loop = False


class ExcludeTab(QWidget):
    """Tab for managing excluded files and directories."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.config = parent.config if parent else None
        
        layout = QVBoxLayout(self)
        
        # Add SSH warning label
        self.lbl_ssh_warning = QLabel(_(
            "{BOLD}Info{ENDBOLD}: "
            "In 'SSH encrypted' mode, only single or double asterisks are "
            "functional (e.g. {example2}). Other types of wildcards and "
            "patterns will be ignored (e.g. {example1}). Filenames are "
            "unpredictable in this mode due to encryption by EncFS.").format(
                BOLD='<strong>',
                ENDBOLD='</strong>',
                example1="<code>'foo*'</code>, "
                         "<code>'[fF]oo'</code>, "
                         "<code>'fo?'</code>",
                example2="<code>'foo/*'</code>, "
                         "<code>'foo/**/bar'</code>"
            ),
            self
        )
        self.lbl_ssh_warning.setWordWrap(True)
        layout.addWidget(self.lbl_ssh_warning)
        
        # Create tree widget
        self.tree = ExcludeTreeWidget(self)
        layout.addWidget(self.tree)
        
        # Add recommendation label
        self.lbl_recommend = QLabel('', self)
        self.lbl_recommend.setWordWrap(True)
        layout.addWidget(self.lbl_recommend)
        
        # Create button layout
        buttons_layout = QHBoxLayout()
        layout.addLayout(buttons_layout)
        
        # Add buttons
        self.btn_add = QPushButton(self.parent.icon.ADD, _('Add'), self)
        buttons_layout.addWidget(self.btn_add)
        self.btn_add.clicked.connect(self.add_pattern)
        
        self.btn_add_file = QPushButton(self.parent.icon.ADD, _('Add file'), self)
        buttons_layout.addWidget(self.btn_add_file)
        self.btn_add_file.clicked.connect(self.add_file)
        
        self.btn_add_dir = QPushButton(self.parent.icon.ADD, _('Add directory'), self)
        buttons_layout.addWidget(self.btn_add_dir)
        self.btn_add_dir.clicked.connect(self.add_directory)
        
        self.btn_add_default = QPushButton(self.parent.icon.DEFAULT_EXCLUDE,
                                         _('Add default'),
                                         self)
        buttons_layout.addWidget(self.btn_add_default)
        self.btn_add_default.clicked.connect(self.add_default)
        
        self.btn_remove = QPushButton(self.parent.icon.REMOVE, _('Remove'), self)
        buttons_layout.addWidget(self.btn_remove)
        self.btn_remove.clicked.connect(self.remove_items)
        
        # Add size-based exclusion
        size_layout = QHBoxLayout()
        layout.addLayout(size_layout)
        
        self.cb_exclude_by_size = QCheckBox(_('Exclude files bigger than:'), self)
        size_layout.addWidget(self.cb_exclude_by_size)
        
        self.spb_exclude_by_size = QSpinBox(self)
        self.spb_exclude_by_size.setSuffix(' MiB')
        self.spb_exclude_by_size.setRange(0, 100000000)
        size_layout.addWidget(self.spb_exclude_by_size)
        
        # Connect signals
        self.cb_exclude_by_size.stateChanged.connect(
            lambda state: self.spb_exclude_by_size.setEnabled(state))
        self.spb_exclude_by_size.setEnabled(False)
    
    def add_pattern(self):
        """Add a pattern to the exclude list."""
        pattern, ok = QInputDialog.getText(
            self,
            _('Add exclude pattern'),
            _('Enter pattern to exclude:')
        )
        
        if ok and pattern:
            self.add_item(pattern.strip())
    
    def add_file(self):
        """Add a file to the exclude list."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            _('Select files to exclude'),
            os.path.expanduser('~'),
            _('All files (*)')
        )
        
        for path in files:
            if path:
                self.add_item(path)
    
    def add_directory(self):
        """Add a directory to the exclude list."""
        directory = QFileDialog.getExistingDirectory(
            self,
            _('Select directory to exclude'),
            os.path.expanduser('~')
        )
        
        if directory:
            self.add_item(directory)
    
    def add_default(self):
        """Add default exclude patterns."""
        for pattern in self.config.DEFAULT_EXCLUDE:
            self.add_item(pattern)
            
        self._update_recommend_label()
    
    def add_item(self, pattern):
        """Add an item to the tree widget.
        
        Args:
            pattern (str): Pattern to exclude
        """
        # Check for duplicates
        duplicates = self.tree.findItems(pattern, Qt.MatchFlag.MatchFixedString)
        if duplicates:
            self.tree.setCurrentItem(duplicates[0])
            return
            
        # Add new item with appropriate icon
        icon = self.parent.icon.DEFAULT_EXCLUDE if pattern in self.config.DEFAULT_EXCLUDE \
               else self.parent.icon.EXCLUDE
        item = self.tree.add_item(pattern, icon=icon)
        
        # Format item based on current mode
        self._format_item(item)
        
        # Update recommendations
        self._update_recommend_label()
    
    def remove_items(self):
        """Remove selected items from the tree widget."""
        self.tree.remove_selected_items()
        
        # Select first item if any remain
        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
            
        self._update_recommend_label()
    
    def get_items(self):
        """Get all items in the tree widget.
        
        Returns:
            list: List of patterns
        """
        items = []
        for i in range(self.tree.topLevelItemCount()):
            items.append(self.tree.topLevelItem(i).text(0))
        return items
    
    def load_values(self):
        """Load values from config into the tree widget."""
        self.tree.clear()
        for exclude in self.config.exclude():
            self.add_item(exclude)
            
    def _format_item(self, item):
        """Format an exclude item based on current mode.
        
        Args:
            item (QTreeWidgetItem): The item to format
        """
        # Get current mode from parent dialog
        mode = None
        if hasattr(self.parent, '_tab_general'):
            mode = self.parent._tab_general.get_active_snapshots_mode()
        elif hasattr(self.parent, 'comboModes'):
            mode = self.parent.comboModes.currentData()
                
        if mode == 'ssh_encfs' and patternHasNotEncryptableWildcard(item.text(0)):
            # Invalid pattern in SSH encrypted mode
            item.setIcon(0, self.parent.icon.INVALID_EXCLUDE)
            item.setData(
                0,
                Qt.ItemDataRole.ToolTipRole,
                _("Disabled because this pattern is not functional in "
                  "mode 'SSH encrypted'.")
            )
            item.setBackground(0, QPalette().brush(QPalette.ColorGroup.Disabled,
                                                QPalette.ColorRole.Window))
            item.setForeground(0, QPalette().brush(QPalette.ColorGroup.Disabled,
                                                QPalette.ColorRole.Text))
        else:
            # Normal pattern
            item.setBackground(0, QBrush())
            item.setForeground(0, QBrush())
            item.setData(0, Qt.ItemDataRole.ToolTipRole, None)
            
            # Set icon based on whether it's a default pattern
            if item.text(0) in self.config.DEFAULT_EXCLUDE:
                item.setIcon(0, self.parent.icon.DEFAULT_EXCLUDE)
            else:
                item.setIcon(0, self.parent.icon.EXCLUDE)
                
    def _update_recommend_label(self):
        """Update the recommendation label based on current patterns."""
        # Find default patterns that aren't in the list
        current_patterns = {item.text(0) for item in self.tree.findItems('', Qt.MatchFlag.MatchContains)}
        recommend = [pattern for pattern in self.config.DEFAULT_EXCLUDE 
                    if pattern not in current_patterns]
        
        if not recommend:
            text = _('{BOLD}Highly recommended{ENDBOLD}: (All recommendations '
                     'already included.)').format(
                        BOLD='<strong>', ENDBOLD='</strong>')
        else:
            text = _('{BOLD}Highly recommended{ENDBOLD}: {files}').format(
                BOLD='<strong>',
                ENDBOLD='</strong>',
                files=', '.join(sorted(recommend)))
                
        self.lbl_recommend.setText(text) 