from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, 
                               QPushButton, QLabel, QCheckBox, QListWidget, 
                               QListWidgetItem, QToolButton, QFrame)
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QKeySequence, QShortcut, QCloseEvent
from core.theme_manager import theme

class SearchDialog(QDialog):
    """Компактный диалог поиска по тексту диалогов"""
    
    block_selected = Signal(object)
    
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.setWindowTitle("Поиск")
        self.setModal(False)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.resize(350, 200)
        self.found_blocks = []
        self.current_index = -1
        self.last_selected_block = None
        
        self.setup_ui()
        self.apply_theme()
        
        if parent:
            parent_rect = parent.geometry()
            self.move(parent_rect.right() - self.width() - 20, parent_rect.top() + 60)
        
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self.search_input.setFocus)
        QShortcut(QKeySequence("F3"), self).activated.connect(self.find_next)
        QShortcut(QKeySequence("Shift+F3"), self).activated.connect(self.find_previous)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self.close)

        self._theme_connected = False
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.returnPressed.connect(self.find_next)
        self.search_input.textChanged.connect(self.on_text_changed)
        search_layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("🔍")
        self.search_btn.setFixedWidth(32)
        self.search_btn.setToolTip("Найти")
        self.search_btn.clicked.connect(self.search)
        search_layout.addWidget(self.search_btn)
        
        layout.addLayout(search_layout)
        
        self.case_sensitive = QCheckBox("Aa")
        self.case_sensitive.setToolTip("С учетом регистра")
        layout.addWidget(self.case_sensitive)
        
        self.results_label = QLabel("0 найдено")
        self.results_label.setObjectName("results_label")
        self.results_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.results_label)
        
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(80)
        self.results_list.itemClicked.connect(self.on_result_clicked)
        layout.addWidget(self.results_list)
        
        nav_layout = QHBoxLayout()
        self.prev_btn = QToolButton()
        self.prev_btn.setText("◀")
        self.prev_btn.setToolTip("Предыдущий (Shift+F3)")
        self.prev_btn.clicked.connect(self.find_previous)
        self.prev_btn.setEnabled(False)
        self.prev_btn.setFixedWidth(40)
        
        self.next_btn = QToolButton()
        self.next_btn.setText("▶")
        self.next_btn.setToolTip("Следующий (F3)")
        self.next_btn.clicked.connect(self.find_next)
        self.next_btn.setEnabled(False)
        self.next_btn.setFixedWidth(40)
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)
        
        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("close_btn")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
    
    def apply_theme(self):
        """Применяет текущую тему ко всем элементам"""
        c = theme.get()
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c['bg_surface']};
                border: 1px solid {c['border']};
                border-radius: 6px;
            }}
            QLineEdit {{
                background-color: {c['bg_input']};
                color: {c['text_main']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 2px solid {c['primary']};
            }}
            QPushButton, QToolButton {{
                background-color: {c['primary']};
                color: white;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
            }}
            QPushButton:hover, QToolButton:hover {{
                background-color: {c['primary_hover']};
            }}
            QPushButton#close_btn {{
                background-color: {c['bg_input']};
                color: {c['text_main']};
                border: 1px solid {c['border']};
            }}
            QPushButton#close_btn:hover {{
                background-color: {c['bg_hover']};
                border-color: {c['primary']};
            }}
            QListWidget {{
                background-color: {c['bg_input']};
                color: {c['text_main']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                font-size: 11px;
            }}
            QListWidget::item:selected {{
                background-color: {c['primary']};
                color: white;
            }}
            QListWidget::item {{
                padding: 2px 4px;
            }}
            QLabel {{
                color: {c['text_secondary']};
            }}
            QLabel#results_label {{
                color: {c['text_main']};
                font-weight: bold;
            }}
            QCheckBox {{
                color: {c['text_secondary']};
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                border: 1px solid {c['border']};
                background-color: {c['bg_input']};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {c['primary']};
                border-color: {c['primary']};
            }}
        """)
        
        self.search_input.style().unpolish(self.search_input)
        self.search_input.style().polish(self.search_input)
        self.search_btn.style().unpolish(self.search_btn)
        self.search_btn.style().polish(self.search_btn)
        self.prev_btn.style().unpolish(self.prev_btn)
        self.prev_btn.style().polish(self.prev_btn)
        self.next_btn.style().unpolish(self.next_btn)
        self.next_btn.style().polish(self.next_btn)
        self.results_list.style().unpolish(self.results_list)
        self.results_list.style().polish(self.results_list)
        self.case_sensitive.style().unpolish(self.case_sensitive)
        self.case_sensitive.style().polish(self.case_sensitive)
        
        for widget in self.findChildren(QPushButton):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        for widget in self.findChildren(QLabel):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        for widget in self.findChildren(QLineEdit):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        for widget in self.findChildren(QListWidget):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
    
    def on_theme_changed(self, theme_name):
        """🔹 Вызывается при смене темы в главном окне"""
        QTimer.singleShot(100, self.apply_theme)
    
    def on_text_changed(self, text):
        """Сбрасывает поиск при изменении текста"""
        self.found_blocks = []
        self.current_index = -1
        self.results_list.clear()
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.results_label.setText("0 найдено")
        self._clear_block_selection()
    
    def _clear_block_selection(self):
        """Снимает выделение со всех блоков"""
        if self.last_selected_block and self.last_selected_block.scene():
            self.last_selected_block.setSelected(False)
            self.last_selected_block = None
    
    def search(self):
        """Выполняет поиск по всем блокам"""
        query = self.search_input.text().strip()
        if not query:
            return
        
        self.found_blocks = []
        self.results_list.clear()
        
        case_sensitive = self.case_sensitive.isChecked()
        
        for block in self.scene.items():
            if hasattr(block, 'block_type') and block.block_type == "Текст":
                props = block.get_properties()
                text = props.get('text', '')
                
                if not case_sensitive:
                    text = text.lower()
                    query_cmp = query.lower()
                else:
                    query_cmp = query
                
                if query_cmp in text:
                    start = 0
                    while True:
                        pos = text.find(query_cmp, start)
                        if pos == -1:
                            break
                        
                        self.found_blocks.append((block, pos, text[pos:pos+len(query)]))
                        
                        preview = self._get_preview(props.get('text', ''), pos, 30)
                        char = props.get('character', '')
                        item_text = f"{char}: {preview}" if char else preview
                        
                        item = QListWidgetItem(item_text)
                        item.setData(Qt.UserRole, len(self.found_blocks) - 1)
                        self.results_list.addItem(item)
                        
                        start = pos + 1
        
        count = len(self.found_blocks)
        self.results_label.setText(f"{count} найдено")
        self.prev_btn.setEnabled(count > 0)
        self.next_btn.setEnabled(count > 0)
        
        if count > 0:
            self.current_index = 0
            self._highlight_current_block()
    
    def _get_preview(self, text, pos, length=30):
        """Возвращает превью текста вокруг найденного слова"""
        start = max(0, pos - 15)
        end = min(len(text), pos + length)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""
        return f"{prefix}{text[start:end]}{suffix}"
    
    def find_next(self):
        """Переход к следующему результату"""
        if not self.found_blocks:
            self.search()
            return
        
        if self.current_index < len(self.found_blocks) - 1:
            self.current_index += 1
            self._highlight_current_block()
    
    def find_previous(self):
        """Переход к предыдущему результату"""
        if self.current_index > 0:
            self.current_index -= 1
            self._highlight_current_block()
    
    def _highlight_current_block(self):
        """Подсвечивает текущий блок, снимая выделение с предыдущего"""
        if not self.found_blocks:
            return
        
        if self.last_selected_block and self.last_selected_block.scene():
            self.last_selected_block.setSelected(False)
        
        block, pos, _ = self.found_blocks[self.current_index]
        
        block.setSelected(True)
        self.last_selected_block = block
        
        if self.scene.parent_window and hasattr(self.scene.parent_window, 'view'):
            view = self.scene.parent_window.view
            view.centerOn(block)
        
        for i in range(self.results_list.count()):
            item = self.results_list.item(i)
            if item.data(Qt.UserRole) == self.current_index:
                self.results_list.setCurrentItem(item)
                break
        
        self.results_label.setText(
            f"{self.current_index + 1} из {len(self.found_blocks)}"
        )
    
    def on_result_clicked(self, item):
        """Обработка клика по результату"""
        index = item.data(Qt.UserRole)
        if index is not None:
            self.current_index = index
            self._highlight_current_block()
    
    def closeEvent(self, event: QCloseEvent):
        """🔹 Обработка закрытия окна"""
        self._clear_block_selection()
        event.accept()
    
    def reject(self):
        """🔹 Переопределяем reject для очистки выделения"""
        self._clear_block_selection()
        super().reject()

    def showEvent(self, event):
        """Перекрашивает диалог при каждом открытии, чтобы тема всегда была актуальной."""
        self.apply_theme()
        super().showEvent(event)