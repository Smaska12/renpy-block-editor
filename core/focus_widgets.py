from PySide6.QtWidgets import QLineEdit, QComboBox
from PySide6.QtCore import Qt

class FocusableLineEdit(QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)
        
    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        super().mousePressEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)


class FocusableComboBox(QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.StrongFocus)

    def focusInEvent(self, event):
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)