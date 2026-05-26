import json
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QPushButton, QLabel, QFileDialog, QMessageBox,
                               QComboBox, QInputDialog, QListWidget, QApplication, QToolButton,
                               QMenuBar, QToolBar, QStatusBar, QDockWidget, QMenu, QSplitter)
from PySide6.QtCore import Qt, QMimeData, QPoint, QTimer, QSize
from PySide6.QtGui import QDrag, QColor, QPen, QKeySequence, QShortcut, QAction

from ui.editor_view import EditorView
from ui.property_dock import PropertyDock
from core.block_widget import BlockWidget
from core.theme_manager import theme
from ui.search_dialog import SearchDialog
from ui.minimap_view import MinimapView
from core.preview_runner import PreviewRunner
from core.project_manager import ProjectManager
from ui.project_tree_dock import ProjectTreeDock
from ui.welcome_overlay import WelcomeOverlay
from ui.asset_preview_dock import AssetPreviewDock
from ui.code_preview_dock import CodePreviewDock

ICONS = {
    'save': '', 'open': '', 'export': '', 'undo': '↩', 'redo': '↪',
    'copy': '', 'cut': '', 'paste': '', 'delete': '', 'search': '',
    'grid': '', 'minimap': '', 'theme': '', 'characters': '',
    'align': '', 'zoom_in': '+', 'zoom_out': '-', 'fit': '⛶',
    'ports': ''
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Visual Novel Maker (Modular)")
        self.resize(1400, 900)
        
        self.project_manager = ProjectManager()
        from core.vn_scene import VNScene
        self.scene = VNScene()
        self.scene.parent_window = self

        self.preview_runner = PreviewRunner(self.scene, self)
        self.preview_runner.error_occurred.connect(lambda msg: QMessageBox.critical(self, "Ошибка превью", msg))

        self._current_zoom = 1.0
        self.sidebar_block_buttons = []

        self._setup_actions()
        self._create_menus()
        self._create_status_bar() 

        self._setup_layout()

        self.welcome_overlay = WelcomeOverlay(self.view.viewport())
        self.welcome_overlay.raise_()
        self.welcome_overlay.open_recent_project.connect(self._open_recent_project_slot)
        self.welcome_overlay.btn_new.clicked.connect(self.new_project)
        self.welcome_overlay.btn_open.clicked.connect(self.load_project)

        self.tree_dock = ProjectTreeDock(self.project_manager, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tree_dock)
        self.tree_dock.hide()

        self._connect_signals()
        self.apply_theme()
        self._update_project_state_ui()
        self._refresh_welcome_overlay()

    def _refresh_welcome_overlay(self):
        """Обновляет список недавних проектов на стартовом экране"""
        if hasattr(self, 'welcome_overlay') and hasattr(self, 'project_manager'):
            recent = self.project_manager.get_recent_projects()
            self.welcome_overlay.update_recent_projects(recent)

    def _open_recent_project_slot(self, path):
        """Обрабатывает клик по недавнему проекту"""
        self.welcome_overlay.hide()
        
        self._load_project_by_path(path)

    def _load_project_by_path(self, path):
        """Загружает проект по указанному пути (без диалога выбора)"""
        from pathlib import Path
        path_obj = Path(path)
        
        if not path_obj.exists() or not (path_obj / "project.json").exists():
            QMessageBox.critical(self, "Ошибка", f"Проект не найден или поврежден:\n{path}")
            self._refresh_welcome_overlay() 
            self.welcome_overlay.show()
            return

        try:
            self.project_manager.load_project(str(path_obj))
            
            import json
            with open(self.project_manager.project_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.scene.clear()
            self.scene.load_project_data(data)
            
            self.label_list.clear()
            for lbl in self.scene.labels.keys():
                self.label_list.addItem(lbl)
            self.scene.switch_label("start")

            self.project_manager.add_to_recent_projects(str(path_obj)) 
            self._update_project_state_ui()

            QTimer.singleShot(100, self._force_refresh_code)
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить проект:\n{str(e)}")
            self._refresh_welcome_overlay()
            self.welcome_overlay.show()

    def _force_refresh_code(self):
        """Принудительно обновляет код в панели, если проект открыт"""
        if hasattr(self, 'scene') and self.scene:
            self.scene.notify_code_change()

    def _setup_actions(self):
        """Создает глобальные действия для меню и хоткеев"""
        self.act_save = QAction(f"{ICONS['save']} Сохранить проект", self, shortcut="Ctrl+S", triggered=self.save_project)
        self.act_load = QAction(f"{ICONS['open']} Загрузить проект", self, shortcut="Ctrl+O", triggered=self.load_project)
        self.act_export_txt = QAction(f"{ICONS['export']} В TXT", self, triggered=self.export_to_txt)
        self.act_export_html = QAction(f"{ICONS['export']} В HTML", self, triggered=self.export_to_html)
        self.act_export_rpy = QAction(f"{ICONS['export']} В Ren'Py (.rpy)", self, triggered=self.export_to_rpy)

        self.act_undo = self.scene.undo_stack.createUndoAction(self, f"{ICONS['undo']} Отменить")
        self.act_redo = self.scene.undo_stack.createRedoAction(self, f"{ICONS['redo']} Повторить")
        self.act_copy = QAction(f"{ICONS['copy']} Копировать", self, shortcut="Ctrl+C", triggered=self.scene.copy_selected)
        self.act_paste = QAction(f"{ICONS['paste']} Вставить", self, shortcut="Ctrl+V", triggered=self.scene.paste_blocks)
        self.act_delete = QAction(f"{ICONS['delete']} Удалить", self, triggered=self._delete_selected)
        self.act_search = QAction(f"{ICONS['search']} Поиск...", self, shortcut="Ctrl+F", triggered=self.show_search)
        
        self.act_grid = QAction(f"{ICONS['grid']} Показать сетку", self, checkable=True, checked=self.scene.grid_enabled, triggered=self.scene.toggle_grid)
        self.act_ports = QAction(f"{ICONS['ports']} Точки связи при наведении", self, checkable=True, checked=True)
        self.act_ports.triggered.connect(self._toggle_ports_hover)
        self.act_show_props = QAction("Панель свойств", self, 
                                    checkable=True, checked=True,
                                    triggered=self._toggle_prop_dock)
        self.act_show_tree = QAction("Структура проекта", self,
                                    checkable=True, checked=True,
                                    triggered=self._toggle_tree_dock)
        self.act_show_assets = QAction("Ассеты", self,
                                    checkable=True, checked=False,
                                    triggered=self._toggle_asset_dock)
        self.act_show_code = QAction( "Код Ren'Py ", self,
                                checkable=True, checked=True,
                                triggered=self._toggle_code_dock)
        self.act_zoom_in = QAction(f"{ICONS['zoom_in']} Приблизить", self, 
                                shortcut="Ctrl+=", triggered=self._zoom_in)
        self.act_zoom_out = QAction(f"{ICONS['zoom_out']} Отдалить", self, 
                                shortcut="Ctrl+-", triggered=self._zoom_out)
        self.act_fit = QAction(f"{ICONS['fit']} Вместить", self, 
                                shortcut="Ctrl+0", triggered=self._fit_view)

        self.act_chars = QAction(f"{ICONS['characters']} Менеджер персонажей", self, shortcut="Ctrl+Shift+C", triggered=self.open_characters_manager)
        self.act_realign = QAction(f"{ICONS['align']} Выровнять блоки", self, shortcut="Ctrl+Shift+L", triggered=self.scene.realign_blocks)
        self.act_collapse_all = QAction("Свернуть/Развернуть все", self, 
                                checkable=True, 
                                triggered=self._toggle_all_blocks_collapse)
        self.act_auto_layout = QAction("Умная расстановка", self, 
                                   shortcut="Ctrl+Shift+A", 
                                   triggered=self.scene.smart_auto_layout)
        self.act_minimap = QAction(f"{ICONS['minimap']} Мини-карта", self, 
                               checkable=True, checked=False,
                               triggered=self._toggle_minimap)

    def _create_menus(self):
        mb = self.menuBar()
        mb.setStyleSheet("""
            QMenuBar {
                background: transparent;
                padding: 4px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background: #334155;
            }
            QMenu {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px;
            }
            QMenu::item {
                padding: 6px 24px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #3B82F6;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 8px;
            }
        """)

        file_menu = mb.addMenu("Файл")
        file_menu.addAction("Новый проект (Ctrl+N)", self.new_project)
        file_menu.addSeparator()
        file_menu.addActions([self.act_load, self.act_save])
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu("Экспорт сценария...")
        export_menu.addAction(self.act_export_txt)
        export_menu.addAction(self.act_export_html)
        export_menu.addAction(self.act_export_rpy)
        file_menu.addSeparator()
        file_menu.addAction(QAction("Выход", self, shortcut="Ctrl+Q", triggered=self.close))

        edit_menu = mb.addMenu("Редактор")
        edit_menu.addActions([self.act_undo, self.act_redo])
        edit_menu.addSeparator()
        edit_menu.addActions([self.act_copy, self.act_paste, self.act_delete])
        edit_menu.addSeparator()
        edit_menu.addAction(self.act_search)

        view_menu = mb.addMenu("Вид")
        view_menu.addAction(self.act_grid)
        view_menu.addAction(self.act_ports)
        view_menu.addAction(self.act_minimap)
        view_menu.addAction(self.act_collapse_all)
        view_menu.addSeparator()
        panels_menu = view_menu.addMenu("Панели")
        panels_menu.addAction(self.act_show_props)
        panels_menu.addAction(self.act_show_tree)
        panels_menu.addAction(self.act_show_assets)
        panels_menu.addAction(self.act_show_code)
        
        view_menu.addSeparator()
        view_menu.addActions([self.act_zoom_in, self.act_zoom_out, self.act_fit])
        
        themes_menu = view_menu.addMenu(f"{ICONS['theme']} Тема оформления")
        for t in theme.get_available_themes():
            a = themes_menu.addAction(t)
            a.triggered.connect(lambda checked, name=t: (theme.set_theme(name), self.apply_theme()))

        tools_menu = mb.addMenu("Инструменты")
        self.act_preview = QAction("▶ Запустить предпросмотр (F5)", self, shortcut="F5")
        self.act_preview.triggered.connect(self._start_preview)
        tools_menu.addAction(self.act_preview)
        tools_menu.addAction(self.act_chars)
        tools_menu.addAction(self.act_realign)
        tools_menu.addAction(self.act_auto_layout)
        tools_menu.addSeparator()

        help_menu = mb.addMenu("Справка")
        help_menu.addAction(QAction("О программе", self, triggered=self.show_about))

    def _create_status_bar(self):
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готов")
        
        self.label_coords = QLabel("X: 0 Y: 0")
        self.status_bar.addPermanentWidget(self.label_coords)

        self.btn_toggle_code = QPushButton("Код")
        self.btn_toggle_code.setCheckable(True)
        self.btn_toggle_code.setChecked(False) 
        self.btn_toggle_code.setToolTip("Показать/скрыть панель ко Ren'Py")
        self.btn_toggle_code.clicked.connect(self._toggle_code_dock_via_button)
        self.status_bar.addPermanentWidget(self.btn_toggle_code)

    def _toggle_code_dock_via_button(self, checked):
        """Вызывается кнопкой в статус-баре"""
        self._toggle_code_dock(checked)

    def _setup_layout(self):
        central = QWidget()
        self.setCentralWidget(central)
        self.main_splitter = QSplitter(Qt.Horizontal, central)

        self.sidebar_widget = QWidget()
        sl = QVBoxLayout(self.sidebar_widget)
        sl.setSpacing(8)
        sl.setContentsMargins(8, 8, 8, 8)
        
        lbl_title = QLabel("Сцены (Labels)")
        lbl_title.setStyleSheet("font-weight: bold; font-size: 12px;")
        sl.addWidget(lbl_title)
        
        self.label_list = QListWidget()
        self.label_list.addItem("start")
        self.label_list.currentTextChanged.connect(self.on_label_changed)
        sl.addWidget(self.label_list)
        
        btn_add_label = QPushButton("+ Новый Label")
        btn_add_label.clicked.connect(self.add_label_dialog)
        sl.addWidget(btn_add_label)
        
        sl.addWidget(QLabel("─" * 20))
        sl.addWidget(QLabel("Добавить блок"))
        
        for t in ["Текст", "Спрайт", "Задний фон", "Музыка", "Звук", "Анимация спрайта", "Выбор ответа"]:
            btn = QPushButton(f"+ {t}")
            self.sidebar_block_buttons.append(btn)
            _orig_press = btn.mousePressEvent
            def _on_mouse_press(event, b=btn, orig=_orig_press, tp=t):
                if event.button() != Qt.LeftButton: return orig(event)
                self._start_block_drag(event, b, tp, orig)
            btn.mousePressEvent = _on_mouse_press
            btn.clicked.connect(lambda _, tp=t: self.scene.add_block(tp))
            sl.addWidget(btn)
        sl.addStretch()

        self.view = EditorView(self.scene)

        self.minimap = MinimapView(self.view)
        self.minimap.hide()
        self.minimap.setParent(self.view)
        self.view.installEventFilter(self)

        self.prop_dock_widget = PropertyDock(self.scene)
        self.prop_dock = QDockWidget("Свойства блока", self)
        self.prop_dock.setWidget(self.prop_dock_widget)
        self.prop_dock.setObjectName("prop_dock")
        self.prop_dock.visibilityChanged.connect(self.act_show_props.setChecked)

        self.main_splitter.addWidget(self.sidebar_widget)
        self.main_splitter.addWidget(self.view)

        self.main_splitter.setSizes([240, 900])     
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(4)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.main_splitter)

        self.tree_dock = ProjectTreeDock(self.project_manager, self)
        self.tree_dock.setObjectName("tree_dock")
        self.tree_dock.visibilityChanged.connect(self.act_show_tree.setChecked)

        self.asset_dock = AssetPreviewDock(self.project_manager, self)
        self.asset_dock.setObjectName("asset_dock")
        self.asset_dock.visibilityChanged.connect(self.act_show_assets.setChecked)

        self.addDockWidget(Qt.RightDockWidgetArea, self.prop_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.tree_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.asset_dock)
        
        self.tabifyDockWidget(self.prop_dock, self.tree_dock)
        self.tabifyDockWidget(self.tree_dock, self.asset_dock)
        self.prop_dock.raise_()  
        self.tree_dock.hide()   
        self.asset_dock.hide()

        from ui.code_preview_dock import CodePreviewDock
        self.code_dock = CodePreviewDock(self)
        self.code_dock.setObjectName("code_preview_dock")
        self.code_dock.visibilityChanged.connect(self.act_show_code.setChecked)
        
        self.addDockWidget(Qt.BottomDockWidgetArea, self.code_dock)
        
        self.code_dock.hide() 

    def _update_minimap_position(self):
        """Фиксирует мини-карту в правом верхнем углу EditorView"""
        if hasattr(self, 'minimap') and self.minimap.isVisible():
            margin = 15
            x = self.view.width() - self.minimap.width() - margin
            y = margin
            self.minimap.move(max(margin, x), y)

    def resizeEvent(self, event):
        """Обновляем позицию при ресайзе главного окна"""
        super().resizeEvent(event)
        self._update_minimap_position()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.view and event.type() == QEvent.Resize:
            self._update_minimap_position()
            
            if hasattr(self, 'welcome_overlay') and self.welcome_overlay.isVisible():
                self.welcome_overlay.resize(self.view.viewport().size())
                
        return super().eventFilter(obj, event)

    def _connect_signals(self):
        self.scene.selectionChanged.connect(self._on_block_selected)
        self.scene.mouseMoved.connect(self._update_status_coords)
        
        self.scene.codeChanged.connect(self._update_code_panel)

        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self.close)

    def _update_code_panel(self, script_content):
        """Безопасное обновление панели кода"""
        if hasattr(self, 'code_dock') and self.code_dock.isVisible():
            self.code_dock.update_code(script_content)

    def show_about(self):
        QMessageBox.about(self, "О программе", 
            "Visual Novel Maker\n\n"
            "Визуальный редактор для создания визуальных новелл\n"
            "Версия 1.0\n\n"
            "Используйте меню для всех операций с проектом")

    def _delete_selected(self):
        if self.scene:
            self.scene.delete_selected_items()

    def _update_status_coords(self, x, y):
        self.label_coords.setText(f"X: {int(x)} Y: {int(y)}")

    def _on_block_selected(self):
        if not hasattr(self, 'scene') or self.scene is None: return
        try:
            selected = self.scene.selectedItems()
        except RuntimeError: return

        block = next((item for item in selected if isinstance(item, BlockWidget)), None)
        if hasattr(self, 'prop_dock_widget'):
            self.prop_dock_widget.set_block(block)
            
        if block:
            self.status_bar.showMessage(f"Выбран блок: {block.block_type}")
        else:
            self.status_bar.showMessage("Готов")

    def _start_block_drag(self, event, button, block_type, original_handler):
        drag = QDrag(button)
        mime = QMimeData()
        mime.setText(block_type)
        drag.setMimeData(mime)
        pixmap = button.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos() - button.rect().topLeft())
        
        if drag.exec(Qt.MoveAction) == Qt.IgnoreAction:
            original_handler(event)

    
    def toggle_minimap(self):
        self.status_bar.showMessage("Миникарта пока не реализована")

    def on_label_changed(self, label_name):
        if label_name: 
            self.scene.switch_label(label_name)
            QTimer.singleShot(100, lambda: self.view.fit_to_content())

    def add_label_dialog(self):
        name, ok = QInputDialog.getText(self, "Новый Label", "Введите имя: ")
        if ok and name:
            if self.scene.add_label(name):
                self.label_list.addItem(name)
                items = self.label_list.findItems(name, Qt.MatchExactly)
                if items: self.label_list.setCurrentItem(items[0])
                self.scene.switch_label(name)
            else:
                QMessageBox.warning(self, "Ошибка", "Label уже существует")

    def save_project(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить", "", "JSON (*.json)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.scene.serialize_project(), f, indent=2, ensure_ascii=False)
                self.status_bar.showMessage(f"Проект сохранен: {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def load_project(self):
        path, _ = QFileDialog.getOpenFileName(self, "Открыть", "", "JSON (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                self.scene.load_project_data(data)
                self.label_list.clear()
                for name in self.scene.labels: self.label_list.addItem(name)
                self.scene.switch_label("start")
                self.status_bar.showMessage(f"Проект загружен: {os.path.basename(path)}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", str(e))

    def export_to_rpy(self):
        self.status_bar.showMessage("Экспорт в Ren'Py...")
        from code_generator import CodeGenerator
        gen = CodeGenerator(self.scene.characters, self.scene.labels)
        script = gen.generate_full_script()
        
        path, _ = QFileDialog.getSaveFileName(self, "Export Ren'Py", "script.rpy")
        if path:
            with open(path, "w", encoding="utf-8") as f: f.write(script)
            self.status_bar.showMessage("Экспорт в Ren'Py завершен!")

    def export_to_txt(self):
        path, _ = QFileDialog.getSaveFileName(self, "TXT", "", "Text (*.txt)")
        if not path: return
        self._export_txt_logic(path)

    def _export_txt_logic(self, path):
        data = self.scene.serialize_project()
        lines = ["📜 СЦЕНАРИЙ", "="*40]
        for label, blocks in data.get("labels", {}).items():
            sorted_blocks = sorted(blocks, key=lambda b: b.get("y", 0))
            lines.append(f"\n🏷️ {label}")
            for b in sorted_blocks:
                btype = b.get("type")
                p = b.get("properties", {})
                if btype == "Текст": lines.append(f"  {p.get('char', '???')}: {p.get('text', '')}")
                elif btype == "Выбор ответа": lines.append(f"  🔀 {p.get('choices', [])}")
        with open(path, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        self.status_bar.showMessage("TXT сохранен!")

    def export_to_html(self):
        path, _ = QFileDialog.getSaveFileName(self, "HTML", "", "HTML (*.html)")
        if path:
            self.status_bar.showMessage("HTML сохранен!")

    def show_search(self):
        if not hasattr(self, 'search_dialog') or self.search_dialog is None:
            self.search_dialog = SearchDialog(self.scene, self)
        self.search_dialog.show()
        self.search_dialog.raise_()
        self.search_dialog.activateWindow()

    def open_characters_manager(self):
        from ui.characters_dialog import CharactersDialog
        CharactersDialog(self.scene, self).exec()

    def apply_theme(self):
        theme.apply()
        c = theme.get()
        
        dock_style = f"""
            QMainWindow {{
                background: {c['bg_main']};
            }}
            QDockWidget {{ 
                titlebar-close-icon: url(transparent); 
                titlebar-normal-icon: url(transparent);
            }}
            QDockWidget::title {{ 
                background: {c['bg_surface']}; 
                color: {c['text_secondary']}; 
                padding-left: 8px; height: 24px;
                font-weight: bold;
                border-bottom: 1px solid {c['border']};
            }}
            QDockWidget::close-button, QDockWidget::float-button {{
                background: {c['bg_surface']};
                color: {c['text_muted']};
                border: none;
                subcontrol-origin: margin;
            }}
            QListWidget {{
                background: {c['bg_input']};
                color: {c['text_main']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QListWidget::item {{
                padding: 4px;
                border-radius: 2px;
            }}
            QListWidget::item:selected {{
                background: {c['primary']};
                color: white;
            }}
            QStatusBar {{
                background: {c['bg_surface']};
                color: {c['text_secondary']};
                border-top: 1px solid {c['border']};
            }}
        """
        self.setStyleSheet(dock_style)
        
        self.view.viewport().update()
        self.scene.update()
        
        btn_qss = f"""
            QPushButton {{
                background: {c['bg_input']}; color: {c['text_main']};
                border: 1px solid {c['border']}; border-radius: 4px;
                text-align: left; padding: 6px 10px;
            }}
            QPushButton:hover {{ background: {c['bg_hover']}; border-color: {c['primary']}; }}
            QPushButton:pressed {{ background: {c['primary']}; color: white; }}
        """
        for btn in self.sidebar_block_buttons:
            btn.setStyleSheet(btn_qss)

        for item in self.scene.items():
            if isinstance(item, BlockWidget):
                item.refresh_theme()
            elif hasattr(item, 'update_style'): 
                item.update_style(QColor(theme.color('edge_color')))

        if hasattr(self, 'code_dock'):
            self.code_dock.refresh_theme()
        
        self.view.viewport().update()
        self.scene.update()

    def new_project(self):
        if self.project_manager.is_project_open:
            from core.block_widget import BlockWidget
            has_blocks = any(isinstance(item, BlockWidget) for item in self.scene.items())
            if has_blocks:
                reply = QMessageBox.question(
                    self, "Новый проект", 
                    "Сохранить текущий проект перед созданием нового?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if reply == QMessageBox.Save:
                    self.save_project()
                elif reply == QMessageBox.Cancel:
                    return

        renpy_sdk = self.preview_runner.get_renpy_path()
        
        if not renpy_sdk or not os.path.exists(renpy_sdk):
            QMessageBox.information(self, "Настройка", 
                "Для создания проекта нужно указать, где у вас установлен Ren'Py (SDK).\n"
                "Это нужно, чтобы скопировать базовые файлы (картинки, стили).")
            
            renpy_sdk = QFileDialog.getExistingDirectory(
                self, "Укажите папку с Ren'Py SDK", "", QFileDialog.ShowDirsOnly
            )
            if not renpy_sdk: return 
            self.preview_runner.set_renpy_path(renpy_sdk)

        project_name, ok_name = QInputDialog.getText(self, "Имя проекта", "Введите название вашей новеллы:")
        if not ok_name or not project_name: return

        save_dir = QFileDialog.getExistingDirectory(
            self, "Где создать папку с проектом?", "", QFileDialog.ShowDirsOnly
        )
        if not save_dir: return

        try:
            self.project_manager.create_project_from_renpy(renpy_sdk, project_name.strip(), save_dir)
            
            self.scene.clear()
            self.scene.labels = {"start": []}
            self.scene.current_label = "start"
            self.scene.undo_stack.clear()

            self.label_list.clear()
            self.label_list.addItem("start")
            self.scene.switch_label("start", skip_sync=True)
            
            self._update_project_state_ui()

            self.project_manager.add_to_recent_projects(self.project_manager.project_path)
            
            QMessageBox.information(self, "Готово", f"Проект '{project_name}' успешно создан!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка создания", str(e))

    def _toggle_ports_hover(self):
        """Обработчик переключения видимости портов при наведении."""
        self.scene.show_ports_on_hover = self.act_ports.isChecked()
        if not self.scene.show_ports_on_hover:
            self.scene.hide_all_ports()
        status = "ВКЛ" if self.act_ports.isChecked() else "ВЫКЛ"
        self.status_bar.showMessage(f"🔗 Точки связи при наведении: {status}")

    def _collapse_all_blocks(self):
        """Сворачивает все блоки на сцене"""
        count = 0
        for item in self.scene.items():
            if isinstance(item, BlockWidget) and hasattr(item, 'toggle_collapsed'):
                if not item.collapsed:
                    item.toggle_collapsed()
                    count += 1
        self.status_bar.showMessage(f"📭 Свернуто блоков: {count}")

    def _expand_all_blocks(self):
        """Разворачивает все блоки на сцене"""
        count = 0
        for item in self.scene.items():
            if isinstance(item, BlockWidget) and hasattr(item, 'toggle_collapsed'):
                if item.collapsed:
                    item.toggle_collapsed()
                    count += 1
        self.status_bar.showMessage(f"📮 Развернуто блоков: {count}")

    def _toggle_all_blocks_collapse(self):
        """Глобальное переключение состояния всех блоков + настройка для новых"""
        is_collapsed = self.act_collapse_all.isChecked()
        
        self.scene.default_block_collapsed = is_collapsed

        count = 0
        for item in self.scene.items():
            if isinstance(item, BlockWidget):
                item.set_collapsed_state(is_collapsed)
                count += 1
                
        self.scene.update()
        self.view.viewport().update()
        
        status = "Свернуть" if is_collapsed else "Развернуть"
        self.status_bar.showMessage(f"📭 Режим '{status} все блоки' активирован (изменено: {count})")

    def _toggle_minimap(self):
        """Показать/скрыть мини-карту"""
        if self.act_minimap.isChecked():
            self.minimap.show()
            self.minimap.raise_()  
            self._update_minimap_position()
            self.status_bar.showMessage("🗺️ Мини-карта включена")
        else:
            self.minimap.hide()
            self.status_bar.showMessage("🗺️ Мини-карта выключена")

    def _start_preview(self):
        if self.preview_runner.is_running():
            self.preview_runner.stop()
            self.status_bar.showMessage("⏹ Предпросмотр остановлен")
        else:
            self.status_bar.showMessage("🚀 Запуск предпросмотра...")
            self.preview_runner.run()


    def _update_project_state_ui(self):
        is_open = self.project_manager.is_project_open

        if is_open:
            self.welcome_overlay.hide()
            self.sidebar_widget.show()
            
            if hasattr(self, 'prop_dock'): self.prop_dock.show()
            if hasattr(self, 'tree_dock'): 
                self.tree_dock.show()
                self.tree_dock.refresh()
            if hasattr(self, 'asset_dock'): 
                self.asset_dock.show()
                self.asset_dock.refresh()
            
            if hasattr(self, 'code_dock'):
                self.code_dock.show()
                self.act_show_code.setChecked(True)
            else:
                self._toggle_code_dock(True)

            self.act_save.setEnabled(True)
            self.act_export_txt.setEnabled(True)
            self.act_export_html.setEnabled(True)
            self.act_export_rpy.setEnabled(True)
            
            if hasattr(self, 'btn_toggle_code'):
                self.btn_toggle_code.setEnabled(True)
                
            self.status_bar.showMessage(f"📂 Проект открыт: {self.project_manager.project_path.name}")

        else:
            self.welcome_overlay.show()
            self.welcome_overlay.raise_()
            
            self.sidebar_widget.hide()
            if hasattr(self, 'prop_dock'): self.prop_dock.hide()
            if hasattr(self, 'tree_dock'): self.tree_dock.hide()
            if hasattr(self, 'asset_dock'): self.asset_dock.hide()
            
            if hasattr(self, 'code_dock'):
                self.code_dock.hide()
                self.act_show_code.setChecked(False)
            
            if hasattr(self, 'btn_toggle_code'):
                self.btn_toggle_code.setEnabled(False)
                self.btn_toggle_code.setChecked(False)

            self.act_save.setEnabled(False)
            self.act_export_txt.setEnabled(False)
            self.act_export_html.setEnabled(False)
            self.act_export_rpy.setEnabled(False)
            
            self.status_bar.showMessage("👋 Добро пожаловать! Создайте или откройте проект.")

    def new_project(self):
        """Создание нового проекта через копирование шаблона Ren'Py"""
        if self.project_manager.is_project_open:
            from core.block_widget import BlockWidget
            has_blocks = any(isinstance(item, BlockWidget) for item in self.scene.items())
            if has_blocks:
                reply = QMessageBox.question(
                    self, "Новый проект",
                    "Сохранить текущий проект перед созданием нового?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if reply == QMessageBox.Save:
                    self.save_project()
                elif reply == QMessageBox.Cancel:
                    return

        renpy_sdk = self.preview_runner.get_renpy_path()
        
        if not renpy_sdk or not os.path.exists(renpy_sdk):
            QMessageBox.information(self, "Настройка", 
                "Для создания проекта нужно указать, где у вас установлен Ren'Py (SDK).\n"
                "Это нужно, чтобы скопировать базовые файлы (картинки, стили).")
            
            renpy_sdk = QFileDialog.getExistingDirectory(
                self, "Укажите папку с Ren'Py SDK", "", QFileDialog.ShowDirsOnly
            )
            if not renpy_sdk: 
                return 
            self.preview_runner.set_renpy_path(renpy_sdk)

        project_name, ok_name = QInputDialog.getText(self, "Имя проекта", "Введите название вашей новеллы:")
        if not ok_name or not project_name.strip():
            return

        save_dir = QFileDialog.getExistingDirectory(
            self, "Где создать папку с проектом?", "", QFileDialog.ShowDirsOnly
        )
        if not save_dir:
            return

        try:
            self.project_manager.create_project_from_renpy(renpy_sdk, project_name.strip(), save_dir)
            
            self.scene.clear()
            self.scene.labels = {"start": []}
            self.scene.current_label = "start"
            self.scene.undo_stack.clear()

            self.label_list.clear()
            self.label_list.addItem("start")
            self.scene.switch_label("start", skip_sync=True)
            
            self._update_project_state_ui()
            
            QMessageBox.information(self, "Готово", f"Проект '{project_name}' успешно создан!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка создания", str(e))

    def load_project(self):
        """Загрузка существующего проекта"""
        if self.project_manager.is_project_open:
            from core.block_widget import BlockWidget
            has_blocks = any(isinstance(item, BlockWidget) for item in self.scene.items())
            if has_blocks:
                reply = QMessageBox.question(
                    self, "Открыть проект",
                    "Сохранить текущий проект?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
                )
                if reply == QMessageBox.Save:
                    self.save_project()
                elif reply == QMessageBox.Cancel:
                    return

        path = QFileDialog.getExistingDirectory(
            self, "Открыть проект", "",
            QFileDialog.ShowDirsOnly
        )
        if not path:
            return

        if not os.path.exists(os.path.join(path, "project.json")):
            QMessageBox.critical(self, "Ошибка", "В выбранной папке нет файла project.json")
            return

        try:
            self.project_manager.load_project(path)
            
            import json
            with open(self.project_manager.project_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.scene.clear()
            self.scene.load_project_data(data)
            
            self.label_list.clear()
            for lbl in self.scene.labels.keys():
                self.label_list.addItem(lbl)
            self.scene.switch_label("start")

            self.project_manager.add_to_recent_projects(path)

            self._update_project_state_ui()
            
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить проект:\n{str(e)}")

    def save_project(self):
        """Сохранение проекта"""
        if not self.project_manager.is_project_open:
            return
            
        self.scene._sync_current_label()
        data = self.scene.serialize_project()
        
        try:
            self.project_manager.save_scene_data(data)
            self.status_bar.showMessage(f"💾 Проект сохранен")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def export_to_rpy(self):
        """Экспорт в Ren'Py"""
        if not self.project_manager.is_project_open:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте или создайте проект!")
            return
            
        self.status_bar.showMessage("📤 Экспорт в Ren'Py...")
        from code_generator import CodeGenerator
        gen = CodeGenerator(self.scene.characters, self.scene.labels)
        
        try:
            self.project_manager.export_script(gen)
            self.status_bar.showMessage("Скрипт успешно экспортирован!")
            QMessageBox.information(self, "Готово", "script.rpy обновлен!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))


    def _zoom_in(self):
        """Приближение с проверкой границ"""
        if self.view._current_zoom < self.view._max_zoom:
            factor = 1.15
            new_zoom = self.view._current_zoom * factor
            if new_zoom <= self.view._max_zoom:
                self.view.scale(factor, factor)
                self.view._current_zoom = new_zoom

    def _zoom_out(self):
        """Отдаление с проверкой границ"""
        if self.view._current_zoom > self.view._min_zoom:
            factor = 0.85
            new_zoom = self.view._current_zoom * factor
            if new_zoom >= self.view._min_zoom:
                self.view.scale(factor, factor)
                self.view._current_zoom = new_zoom

    def _fit_view(self):
        """Вместить всё в окно с учетом ограничений"""
        self.view.fit_to_content()

    def _toggle_prop_dock(self, checked):
        """Показать/скрыть панель свойств"""
        if hasattr(self, 'prop_dock'):
            if checked:
                self.prop_dock.show()
                self.prop_dock.raise_()
            else:
                self.prop_dock.hide()

    def _toggle_tree_dock(self, checked):
        """Показать/скрыть древо проекта"""
        if hasattr(self, 'tree_dock'):
            if checked:
                self.tree_dock.show()
                self.tree_dock.raise_()
            else:
                self.tree_dock.hide()

    def _toggle_asset_dock(self, checked):
        """Показать/скрыть панель ассетов"""
        if hasattr(self, 'asset_dock'):
            if checked:
                self.asset_dock.show()
                self.asset_dock.raise_()
                self.asset_dock.refresh()
            else:
                self.asset_dock.hide()

    def _toggle_code_dock(self, checked):
        if not hasattr(self, 'code_dock'):
            from ui.code_preview_dock import CodePreviewDock
            self.code_dock = CodePreviewDock(self)
            self.code_dock.setObjectName("code_preview_dock")
            self.addDockWidget(Qt.BottomDockWidgetArea, self.code_dock)
            self.code_dock.visibilityChanged.connect(self._sync_code_visibility)

        if checked:
            self.code_dock.show()
            self.code_dock.raise_()
            self.scene.notify_code_change()
        else:
            self.code_dock.hide()

    def _sync_code_visibility(self, visible):
        """Синхронизирует состояние кнопки в статус-баре и действия в меню"""
        if hasattr(self, 'btn_toggle_code'):
            self.btn_toggle_code.setChecked(visible)
        if hasattr(self, 'act_show_code'):
            self.act_show_code.setChecked(visible)