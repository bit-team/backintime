from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QHeaderView, QAbstractItemView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

# Import translation function from tools
from tools import _


class BaseTreeWidget(QTreeWidget):
    """Base class for tree widgets used in Include and Exclude tabs.
    
    This class provides common functionality for tree widgets that display
    files and directories in the profile settings dialog.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setRootIsDecorated(False)
        self.setHeaderLabels([_('Items'), 'Count'])
        
        # Configure header
        header = self.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSectionHidden(1, True)
        
        # Initialize sorting state
        self.sort_loop = False
        header.sortIndicatorChanged.connect(self.custom_sort_order)
        
        # Initialize count for item ordering
        self._count = 0
    
    def custom_sort_order(self, *args):
        """Handle custom sorting order for the tree widget.
        
        This method should be implemented by subclasses to provide
        specific sorting behavior.
        """
        raise NotImplementedError
    
    def add_item(self, text, icon=None, count=None, user_data=None):
        """Add a new item to the tree widget.
        
        Args:
            text (str): The text to display for the item
            icon (QIcon, optional): Icon to display next to the text
            count (int, optional): The count to display in the second column
            user_data (any, optional): User data to store with the item
        
        Returns:
            QTreeWidgetItem: The newly created item
        """
        item = QTreeWidgetItem(self)
        item.setText(0, text)
        
        if icon:
            item.setIcon(0, icon)
            
        # Use provided count or internal counter
        display_count = count if count is not None else self._count
        item.setText(1, str(display_count).zfill(6))
        item.setData(1, Qt.ItemDataRole.UserRole, display_count)
            
        if user_data is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, user_data)
            
        self._count += 1
        return item
    
    def get_selected_items(self):
        """Get all selected items in the tree widget.
        
        Returns:
            list: List of selected QTreeWidgetItems
        """
        return self.selectedItems()
    
    def remove_selected_items(self):
        """Remove all selected items from the tree widget."""
        for item in self.get_selected_items():
            self.takeTopLevelItem(self.indexOfTopLevelItem(item))
            
    def clear(self):
        """Clear all items and reset count."""
        super().clear()
        self._count = 0
        
    def get_count(self):
        """Get the current count value.
        
        Returns:
            int: The current count value
        """
        return self._count 