from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import QSettings

class ThemeManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        self._initialized = True
        self.settings = QSettings("VNMaker", "UI_Settings")
        saved = self.settings.value("active_theme", "Modern Dark", str)

        self.themes = {
            "Modern Dark": {
                "bg_main": "#0F172A", "bg_surface": "#1E293B", "bg_input": "#0F172A",
                "bg_hover": "#334155", "primary": "#3B82F6", "primary_hover": "#2563EB",
                "secondary": "#6366F1", "success": "#10B981", "warning": "#F59E0B",
                "danger": "#EF4444", "text_main": "#F8FAFC", "text_secondary": "#94A3B8",
                "text_muted": "#64748B", "border": "#334155", "border_light": "#475569",
                "block_content_bg": "#1E293B", "block_preview_text": "#CBD5E1",
                "viewport_bg": "#0B1120", "edge_color": "#60A5FA"
            },
            "Modern Light": {
                "bg_main": "#F8FAFC", "bg_surface": "#FFFFFF", "bg_input": "#FFFFFF",
                "bg_hover": "#E2E8F0", "primary": "#3B82F6", "primary_hover": "#2563EB",
                "secondary": "#6366F1", "success": "#10B981", "warning": "#F59E0B",
                "danger": "#EF4444", "text_main": "#0F172A", "text_secondary": "#475569",
                "text_muted": "#64748B", "border": "#CBD5E1", "border_light": "#94A3B8",
                "block_content_bg": "#F1F5F9", "block_preview_text": "#334155",
                "viewport_bg": "#E2E8F0", "edge_color": "#3B82F6"
            },
            "Nord": {
                "bg_main": "#2E3440", "bg_surface": "#3B4252", "bg_input": "#434C5E",
                "bg_hover": "#4C566A", "primary": "#88C0D0", "primary_hover": "#8FBCBB",
                "secondary": "#81A1C1", "success": "#A3BE8C", "warning": "#EBCB8B",
                "danger": "#BF616A", "text_main": "#ECEFF4", "text_secondary": "#D8DEE9",
                "text_muted": "#4C566A", "border": "#4C566A", "border_light": "#3B4252",
                "block_content_bg": "#3B4252", "block_preview_text": "#D8DEE9",
                "viewport_bg": "#2E3440", "edge_color": "#88C0D0"
            },
            "Dracula": {
                "bg_main": "#282A36", "bg_surface": "#44475A", "bg_input": "#44475A",
                "bg_hover": "#6272A4", "primary": "#BD93F9", "primary_hover": "#FF79C6",
                "secondary": "#8BE9FD", "success": "#50FA7B", "warning": "#F1FA8C",
                "danger": "#FF5555", "text_main": "#F8F8F2", "text_secondary": "#F8F8F2",
                "text_muted": "#6272A4", "border": "#6272A4", "border_light": "#44475A",
                "block_content_bg": "#44475A", "block_preview_text": "#F8F8F2",
                "viewport_bg": "#282A36", "edge_color": "#BD93F9"
            },
            "Gruvbox Dark": {
                "bg_main": "#282828", "bg_surface": "#3C3836", "bg_input": "#3C3836",
                "bg_hover": "#504945", "primary": "#FB4934", "primary_hover": "#CC241D",
                "secondary": "#83A598", "success": "#B8BB26", "warning": "#FABD2F",
                "danger": "#FB4934", "text_main": "#EBDBB2", "text_secondary": "#A89984",
                "text_muted": "#928374", "border": "#504945", "border_light": "#3C3836",
                "block_content_bg": "#3C3836", "block_preview_text": "#D5C4A1",
                "viewport_bg": "#282828", "edge_color": "#FB4934"
            }
        }
        self.current_theme = saved if saved in self.themes else next(iter(self.themes.keys()))

    def get_available_themes(self):
        return list(self.themes.keys())

    def get(self): return self.themes[self.current_theme]
    def color(self, key: str) -> str: return self.get()[key]

    def set_theme(self, name: str):
        if name in self.themes:
            self.current_theme = name
            self.settings.setValue("active_theme", name)
            self.settings.sync()
            self.apply()

    def apply(self):
        app = QApplication.instance()
        if not app: return
        c = self.get()
        
        qss = f"""
            /* Базовые виджеты */
            QMainWindow, QMainWindow > QWidget {{
                background-color: {c['bg_main']};
            }}
            
            QMainWindow {{ 
                background-color: {c['bg_main']};
            }}
            
            /* Центральный виджет и его потомки */
            QWidget {{
                background-color: transparent;
                color: {c['text_main']};
            }}
            
            /* Явно задаём фон для контейнеров */
            QWidget[objectName="centralWidget"],
            QWidget[objectName="sidebar"],
            QWidget[objectName="prop_dock"] {{
                background-color: {c['bg_surface']};
            }}
            
            QLabel {{ 
                color: {c['text_secondary']}; 
                background-color: transparent;
            }}
            
            QPushButton {{
                background-color: {c['primary']}; 
                color: white; 
                border: none;
                padding: 8px 12px; 
                border-radius: 6px; 
                font-weight: bold;
            }}
            
            QPushButton:hover {{ 
                background-color: {c['primary_hover']}; 
            }}
            
            /* Остальные стили без изменений... */
            QListWidget, QTreeWidget {{
                background-color: {c['bg_surface']}; 
                color: {c['text_main']};
                border: 1px solid {c['border']}; 
                border-radius: 4px;
            }}
            
            QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {{
                background-color: {c['bg_input']}; 
                color: {c['text_main']};
                border: 1px solid {c['border']}; 
                border-radius: 4px; 
                padding: 5px;
            }}
            
            QTableWidget {{
                background-color: {c['bg_surface']}; 
                color: {c['text_main']};
                gridline-color: {c['border']}; 
                border: 1px solid {c['border']};
            }}
            
            QGraphicsView {{ 
                background-color: {c['viewport_bg']}; 
            }}
            
            QSlider::groove:horizontal {{ 
                background: {c['border']}; 
                height: 6px; 
                border-radius: 3px; 
            }}
            
            QSlider::handle:horizontal {{ 
                background: {c['primary']}; 
                width: 14px; 
                margin: -4px 0; 
                border-radius: 7px; 
            }}
            
            QRadioButton, QCheckBox {{ 
                color: {c['text_main']}; 
            }}
            
            QScrollBar:vertical {{ 
                background: {c['bg_surface']}; 
                width: 10px; 
                border-radius: 5px; 
            }}
            
            QScrollBar::handle:vertical {{ 
                background: {c['border']}; 
                border-radius: 5px; 
                min-height: 20px; 
            }}
            
            QScrollBar::handle:vertical:hover {{ 
                background: {c['primary']}; 
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ 
                height: 0px; 
            }}
            
            QScrollBar:horizontal {{ 
                background: {c['bg_surface']}; 
                height: 10px; 
                border-radius: 5px; 
            }}
            
            QScrollBar::handle:horizontal {{ 
                background: {c['border']}; 
                border-radius: 5px; 
                min-width: 20px; 
            }}
            
            QScrollBar::handle:horizontal:hover {{ 
                background: {c['primary']}; 
            }}

            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 4px;
                margin: 2px 0;
            }}
            QListWidget::item:hover {{
                background-color: {c['bg_hover']};
            }}
            QListWidget::item:selected {{
                background-color: {c['primary']};
                color: white;
                font-weight: bold;
            }}

            /* Кнопки сайдбара */
            QPushButton {{
                text-align: left;
                padding: 8px 12px;
                border-radius: 6px;
                border: 1px solid transparent;
            }}
            QPushButton:hover {{
                background-color: {c['bg_hover']};
                border-color: {c['border_light']};
            }}
            QPushButton:pressed {{
                background-color: {c['border']};
            }}

            /* Фокус для полей ввода */
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QPlainTextEdit:focus {{
                border: 2px solid {c['primary']};
                background-color: {c['bg_input']};
            }}

            /* Резиновая рамка выделения на холсте */
            QGraphicsView::rubber-band {{
                background-color: {c['bg_hover']};
                border: 2px dashed {c['primary']};
                border-radius: 4px;
            }}
        """
        app.setStyleSheet(qss)

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(c['bg_main']))
        palette.setColor(QPalette.WindowText, QColor(c['text_main']))
        palette.setColor(QPalette.Base, QColor(c['bg_input']))
        palette.setColor(QPalette.Text, QColor(c['text_main']))
        palette.setColor(QPalette.Button, QColor(c['bg_surface']))
        palette.setColor(QPalette.ButtonText, QColor(c['text_main']))
        palette.setColor(QPalette.Highlight, QColor(c['primary']))
        palette.setColor(QPalette.HighlightedText, QColor("white"))
        app.setPalette(palette)

theme = ThemeManager()