
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, Signal

class WelcomeOverlay(QWidget):
    open_recent_project = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setAutoFillBackground(True)
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(15, 23, 42, 0.95);
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Visual Novel Maker")
        title.setStyleSheet("font-size: 32px; color: #F8FAFC; font-weight: bold; margin-bottom: 5px;")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Создайте новый проект или откройте существующий.")
        subtitle.setStyleSheet("font-size: 14px; color: #94A3B8; margin-bottom: 20px;")
        subtitle.setAlignment(Qt.AlignCenter)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_new = QPushButton("Создать новый проект")
        self.btn_new.setMinimumHeight(45)
        self.btn_new.setMaximumWidth(250)
        self.btn_new.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6; color: white; font-size: 16px; 
                border-radius: 8px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """)

        self.btn_open = QPushButton("Открыть проект...")
        self.btn_open.setMinimumHeight(40)
        self.btn_open.setMaximumWidth(250)
        self.btn_open.setStyleSheet("""
            QPushButton {
                background-color: #334155; color: #F8FAFC; font-size: 14px; 
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #475569; }
        """)

        btn_layout.addWidget(self.btn_new, alignment=Qt.AlignCenter)
        btn_layout.addWidget(self.btn_open, alignment=Qt.AlignCenter)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(btn_layout)
        
        self.recent_label = QLabel("Недавние проекты:")
        self.recent_label.setStyleSheet("color: #CBD5E1; font-size: 13px; margin-top: 20px; margin-bottom: 5px;")
        self.recent_label.hide() 
        
        self.recent_list = QListWidget()
        self.recent_list.setMaximumWidth(300)
        self.recent_list.setMaximumHeight(150)
        self.recent_list.hide() 
        self.recent_list.setStyleSheet("""
            QListWidget {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px;
            }
            QListWidget::item {
                color: #94A3B8;
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #334155;
                color: white;
            }
        """)
        self.recent_list.itemDoubleClicked.connect(self._on_recent_clicked)
        
        layout.addWidget(self.recent_label, alignment=Qt.AlignCenter)
        layout.addWidget(self.recent_list, alignment=Qt.AlignCenter)
        layout.addStretch()

    def update_recent_projects(self, recent_paths):
        """Обновляет список недавних проектов"""
        self.recent_list.clear()
        
        if not recent_paths:
            self.recent_label.hide()
            self.recent_list.hide()
            return
        
        self.recent_label.show()
        self.recent_list.show()
        
        from pathlib import Path
        for path_str in recent_paths:
            path = Path(path_str)
            if path.exists():
                item = QListWidgetItem(f"{path.name}")
                item.setData(Qt.UserRole, str(path))
                item.setToolTip(str(path))
                self.recent_list.addItem(item)

    def _on_recent_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.open_recent_project.emit(path)

    def resizeEvent(self, event):
        if self.parent():
            self.resize(self.parent().size())
        super().resizeEvent(event)

    def mousePressEvent(self, event): event.accept()
    def mouseMoveEvent(self, event): event.accept()
    def mouseReleaseEvent(self, event): event.accept()
    def wheelEvent(self, event): event.accept()
    def keyPressEvent(self, event): event.accept()