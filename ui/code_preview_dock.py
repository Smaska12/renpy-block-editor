from PySide6.QtWidgets import QDockWidget, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from core.theme_manager import theme

class CodePreviewDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Код Ren'Py", parent)
        
        self.code_editor = QTextEdit()
        self.code_editor.setReadOnly(True)
        self.code_editor.setFont(QFont("Consolas", 9)) 
        self.code_editor.setLineWrapMode(QTextEdit.NoWrap)
        
        self._apply_theme()
        
        self.setWidget(self.code_editor)
        self.setObjectName("code_preview_dock")

    def _apply_theme(self):
        c = theme.get()
        bg = c['bg_input'] if c['bg_input'] != '#FFFFFF' else '#1E1E1E'
        text = c['text_main']
        
        self.code_editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg};
                color: {text};
                border: none; 
                selection-background-color: {c['primary']};
            }}
        """)

    def update_code(self, script_content: str):
        scrollbar = self.code_editor.verticalScrollBar()
        current_scroll = scrollbar.value()
        max_scroll = scrollbar.maximum()
        
        self.code_editor.setPlainText(script_content)
        
        if current_scroll >= max_scroll - 5:
            scrollbar.setValue(scrollbar.maximum())
        else:
            scrollbar.setValue(current_scroll)

    def refresh_theme(self):
        self._apply_theme()