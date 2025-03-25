from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt
import os

from tools import _
from .tree_widgets import BaseTreeWidget


class IncludeTreeWidget(BaseTreeWidget):
    """Tree widget for displaying included files and directories."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels([_('Include files and directories'), 'Count'])
    
    def custom_sort_order(self, *args):
        """Handle custom sorting for include items."""
        if self.sort_loop:
            return
        self.sort_loop = True
        self.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.sort_loop = False


class IncludeTab(QWidget):
    """Tab for managing included files and directories."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.config = parent.config if parent else None
        
        layout = QVBoxLayout(self)
        
        # Create tree widget
        self.tree = IncludeTreeWidget(self)
        layout.addWidget(self.tree)
        
        # Create button layout
        buttons_layout = QHBoxLayout()
        layout.addLayout(buttons_layout)
        
        # Add buttons
        self.btn_add_file = QPushButton(self.parent.icon.ADD, _('Add file'), self)
        buttons_layout.addWidget(self.btn_add_file)
        self.btn_add_file.clicked.connect(self.add_file)
        
        self.btn_add_dir = QPushButton(self.parent.icon.ADD, _('Add directory'), self)
        buttons_layout.addWidget(self.btn_add_dir)
        self.btn_add_dir.clicked.connect(self.add_directory)
        
        self.btn_remove = QPushButton(self.parent.icon.REMOVE, _('Remove'), self)
        buttons_layout.addWidget(self.btn_remove)
        self.btn_remove.clicked.connect(self.remove_items)
    
    def add_file(self):
        """Add a file to the include list."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            _('Select files to include'),
            os.path.expanduser('~'),
            _('All files (*)')
        )
        
        for path in files:
            if not path:
                continue
                
            if os.path.islink(path) and not self._should_follow_symlink():
                path = self._handle_symlink(path)
                if not path:
                    continue
                    
            path = self.config.preparePath(path)
            self.add_item(path, is_dir=False)
    
    def add_directory(self):
        """Add a directory to the include list."""
        paths = QFileDialog.getExistingDirectory(
            self,
            _('Select directory to include'),
            os.path.expanduser('~')
        )
        
        if not paths:
            return
            
        if os.path.islink(paths) and not self._should_follow_symlink():
            paths = self._handle_symlink(paths)
            if not paths:
                return
                
        paths = self.config.preparePath(paths)
        self.add_item(paths, is_dir=True)
    
    def add_item(self, path, is_dir=True):
        """Add an item to the tree widget.
        
        Args:
            path (str): Path to the file or directory
            is_dir (bool): Whether the path is a directory
        """
        # Check for duplicates
        duplicates = self.tree.findItems(path, Qt.MatchFlag.MatchFixedString)
        if duplicates:
            self.tree.setCurrentItem(duplicates[0])
            return
            
        # Add new item with appropriate icon
        icon = self.parent.icon.FOLDER if is_dir else self.parent.icon.FILE
        self.tree.add_item(path, icon=icon, user_data=0 if is_dir else 1)
        
    def remove_items(self):
        """Remove selected items from the tree widget."""
        self.tree.remove_selected_items()
        
        # Select first item if any remain
        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))
    
    def get_items(self):
        """Get all items in the tree widget.
        
        Returns:
            list: List of (path, type) tuples where type is 0 for directories
                 and 1 for files
        """
        items = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            items.append((item.text(0), item.data(0, Qt.ItemDataRole.UserRole)))
        return items
    
    def load_values(self):
        """Load values from config into the tree widget."""
        self.tree.clear()
        for include in self.config.include():
            self.add_item(include[0], is_dir=(include[1] == 0))
            
    def _should_follow_symlink(self):
        """Check if symlinks should be followed based on config."""
        return (hasattr(self.parent, 'cbCopyUnsafeLinks') and 
                self.parent.cbCopyUnsafeLinks.isChecked()) or \
               (hasattr(self.parent, 'cbCopyLinks') and 
                self.parent.cbCopyLinks.isChecked())
                
    def _handle_symlink(self, path):
        """Handle symlink path, asking user if they want to follow it.
        
        Returns:
            str: Real path if user wants to follow symlink, original path
                if not, or None if user cancels
        """
        answer = QMessageBox.question(
            self,
            _('Symlink found'),
            _(
                '"{path}" is a symlink. The linked target will not be '
                'backed up until you include it, too.\nWould you like '
                'to include the symlink target instead?'
            ).format(path=path)
        )
        
        if answer == QMessageBox.StandardButton.Yes:
            return os.path.realpath(path)
        elif answer == QMessageBox.StandardButton.No:
            return path
        return None 