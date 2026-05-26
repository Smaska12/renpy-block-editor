# ui/asset_preview_dock.py
from PySide6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QListWidget, QListWidgetItem, 
                               QToolButton, QFileDialog, QMessageBox, QSizePolicy,
                               QComboBox, QMenu, QStyle)
from PySide6.QtGui import QPixmap, QIcon, QDrag, QPainter
from PySide6.QtCore import Qt, QSize, Signal, QPoint, QMimeData
import shutil
from pathlib import Path
from core.theme_manager import theme

class AssetPreviewDock(QDockWidget):
    """Панель предпросмотра ассетов с навигацией по папкам"""
    asset_selected = Signal(str, str)  
    
    def __init__(self, project_manager, parent=None):
        super().__init__("Ассеты", parent)
        self.project_manager = project_manager
        self.setAllowedAreas(Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        
        self.current_path = None  
        self.path_history = [] 
        
        self.widget = QWidget()
        self.layout = QVBoxLayout(self.widget)
        self.layout.setContentsMargins(4, 4, 4, 4)
        
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(4)
        nav_layout.setContentsMargins(0, 0, 0, 4) 

        btn_style = """
            QToolButton {
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                padding: 4px;
                min-width: 28px;
                min-height: 28px;
            }
            QToolButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            QToolButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """
        
        self.btn_back = QToolButton()
        self.btn_back.setText("◀")
        self.btn_back.setToolTip("Назад")
        self.btn_back.setStyleSheet(btn_style)
        self.btn_back.clicked.connect(self.navigate_back)
        self.btn_back.setEnabled(False)
        
        self.btn_up = QToolButton()
        self.btn_up.setText("▲")
        self.btn_up.setToolTip("Вверх")
        self.btn_up.setStyleSheet(btn_style)
        self.btn_up.clicked.connect(self.navigate_up)
        
        self.btn_home = QToolButton()
        self.btn_home.setText("🏠")
        self.btn_home.setToolTip("В корень images")
        self.btn_home.setStyleSheet(btn_style)
        self.btn_home.clicked.connect(self.navigate_home)
        
        nav_layout.addWidget(self.btn_back)
        nav_layout.addWidget(self.btn_up)
        nav_layout.addWidget(self.btn_home)
        nav_layout.addStretch()
        
        self.layout.addLayout(nav_layout)
        
        btn_layout = QHBoxLayout()
        
        self.btn_refresh = QToolButton()
        self.btn_refresh.setText("🔄")
        self.btn_refresh.setToolTip("Обновить")
        self.btn_refresh.clicked.connect(self.refresh)
        
        self.btn_import = QToolButton()
        self.btn_import.setText("📥")
        self.btn_import.setToolTip("Импортировать файлы")
        self.btn_import.clicked.connect(self.import_assets)
        
        btn_layout.addWidget(self.btn_refresh)
        btn_layout.addWidget(self.btn_import)
        btn_layout.addStretch()
        
        self.layout.addLayout(btn_layout)
        
        self.path_label = QLabel("images/")
        self.path_label.setStyleSheet("font-weight: bold; padding: 4px;")
        self.layout.addWidget(self.path_label)
        
        self.asset_list = QListWidget()
        self.asset_list.setViewMode(QListWidget.IconMode)
        self.asset_list.setResizeMode(QListWidget.Adjust)
        self.asset_list.setGridSize(QSize(90, 90)) 
        self.asset_list.setIconSize(QSize(64, 64))
        self.asset_list.setResizeMode(QListWidget.Adjust)
        self.asset_list.setMovement(QListWidget.Static)
        self.asset_list.setSpacing(5)
        self.asset_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.asset_list.setDragEnabled(True)
        self.asset_list.setAcceptDrops(True)
        self.asset_list.setDropIndicatorShown(True)
        self.asset_list.setDefaultDropAction(Qt.MoveAction)

        c = theme.get()
        self.asset_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {c['bg_input']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 5px;
            }}
            QListWidget::item {{
                background-color: transparent;
                border-radius: 4px;
                margin: 2px;
                padding: 2px;
            }}
            QListWidget::item:hover {{
                background-color: {c['bg_hover']};
            }}
            QListWidget::item:selected {{
                background-color: {c['primary']};
                color: white;
            }}
        """)

        self.asset_list.itemDoubleClicked.connect(self._on_asset_double_click)
        self.asset_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.asset_list.customContextMenuRequested.connect(self._on_asset_context_menu)
        self.layout.addWidget(self.asset_list)
        
        self.setWidget(self.widget)

    def startDrag(self, supportedActions):
        """Начало перетаскивания элемента из списка ассетов"""
        items = self.asset_list.selectedItems()
        if not items:
            return
        
        item = items[0]
        file_path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)
        
        if item_type == "folder":
            return

        mime_data = QMimeData()
        mime_data.setText(str(file_path))
        
        drag = QDrag(self.asset_list)
        drag.setMimeData(mime_data)
        
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        if item_type == "image":
            icon = item.icon()
            if not icon.isNull():
                icon.paint(painter, 0, 0, 64, 64)
        else:
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "📄")
        painter.end()
        
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(32, 32))
        
        drop_action = drag.exec(supportedActions)
        
        if drop_action == Qt.MoveAction:
            pass

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            source_path_str = event.mimeData().text()
            source_path = Path(source_path_str)
            
            target_item = self.asset_list.itemAt(event.pos())
            
            if target_item:
                target_type = target_item.data(Qt.UserRole + 1)
                if target_type == "folder":
                    target_dir = Path(target_item.data(Qt.UserRole))
                else:
                    target_dir = self.current_path
            else:
                target_dir = self.current_path
                
            if source_path.exists() and target_dir.exists():
                try:
                    if target_dir != source_path.parent:
                        shutil.move(str(source_path), str(target_dir / source_path.name))
                        self.refresh()
                        
                        main_window = self.parent()
                        if main_window and hasattr(main_window, 'tree_dock'):
                            main_window.tree_dock.refresh()
                            
                except Exception as e:
                    QMessageBox.warning(self, "Ошибка", f"Не удалось переместить файл:\n{e}")
            
            event.acceptProposedAction()
        
    def refresh(self):
        """Обновляет список ассетов в текущей папке"""
        if not self.project_manager.is_project_open:
            self.asset_list.clear()
            self.asset_list.addItem("Проект не открыт")
            return
        
        images_path = self.project_manager.game_path / "images"
        if not images_path.exists():
            self.asset_list.clear()
            self.asset_list.addItem("Папка images не найдена")
            return
        
        if self.current_path is None:
            self.current_path = images_path
            self.path_history = [str(images_path)] 
        
        self._load_directory(self.current_path)
    
    def _load_directory(self, dir_path):
        """Загружает содержимое директории"""
        self.asset_list.clear()
        
        root_images = self.project_manager.game_path / "images"
        try:
            rel_path = dir_path.relative_to(root_images)
            self.path_label.setText(str(rel_path) if str(rel_path) != '.' else "images/")
        except ValueError:
            self.path_label.setText("images/")
            self.current_path = root_images
        
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            
            for item in items:
                if item.name.startswith('.'):
                    continue
                
                if item.is_dir():
                    folder_item = QListWidgetItem(f"📁 {item.name}")
                    folder_item.setToolTip(str(item))
                    folder_item.setData(Qt.UserRole, str(item))
                    folder_item.setData(Qt.UserRole + 1, "folder")
                    
                    standard_icon = self.style().standardIcon(QStyle.SP_DirIcon)
                    pixmap = standard_icon.pixmap(QSize(64, 64)) 
                    folder_item.setIcon(QIcon(pixmap))
                    
                    folder_item.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
                    
                    self.asset_list.addItem(folder_item)

                elif item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                    rel_path = item.relative_to(self.project_manager.game_path / "images")
                    item_widget = QListWidgetItem(str(rel_path))
                    item_widget.setToolTip(str(item))
                    item_widget.setData(Qt.UserRole, str(item))
                    item_widget.setData(Qt.UserRole + 1, "image")
                    
                    pixmap = QPixmap(str(item))
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item_widget.setIcon(QIcon(pixmap))
                    
                    item_widget.setTextAlignment(Qt.AlignHCenter | Qt.AlignBottom)
                    self.asset_list.addItem(item_widget)
                    
        except Exception as e:
            print(f"Error loading directory: {e}")
            self.asset_list.addItem(f"Ошибка: {e}")
    
    def navigate_back(self):
        """Назад по истории"""
        if len(self.path_history) > 1:
            self.path_history.pop()
            self.current_path = Path(self.path_history[-1])
            self._load_directory(self.current_path)
            self.btn_back.setEnabled(len(self.path_history) > 1)
    
    def navigate_up(self):
        """Вверх на уровень"""
        if not self.project_manager.is_project_open: return
        
        root_images = self.project_manager.game_path / "images"
        
        if self.current_path == root_images:
            return
            
        parent = self.current_path.parent
        if parent == root_images or parent.is_relative_to(root_images.parent): 
             self.path_history.append(str(self.current_path))
             self.current_path = parent
             self._load_directory(parent)
             self.btn_back.setEnabled(True)
    
    def navigate_home(self):
        """В корень images"""
        if self.project_manager.is_project_open:
            self.current_path = self.project_manager.game_path / "images"
            self.path_history = [str(self.current_path)]
            self._load_directory(self.current_path)
            self.btn_back.setEnabled(False)
    
    def _on_asset_double_click(self, item):
        """Обработка двойного клика"""
        file_path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)
        
        if item_type == "folder":
            self.path_history.append(str(file_path))
            self.current_path = Path(file_path)
            self._load_directory(self.current_path)
            self.btn_back.setEnabled(True)
        elif item_type == "image":
            global_pos = self.asset_list.mapToGlobal(self.asset_list.rect().center())
            self._show_use_menu(file_path, global_pos)

    def _on_asset_context_menu(self, pos):
        """Контекстное меню для ассета"""
        item = self.asset_list.itemAt(pos)
        if not item:
            return
        
        file_path = item.data(Qt.UserRole)
        item_type = item.data(Qt.UserRole + 1)
        
        if item_type not in ["image", "audio"]:
            return
        
        global_pos = self.asset_list.mapToGlobal(pos)
        self._show_use_menu(file_path, global_pos)

    def _show_use_menu(self, file_path, global_pos):
        """Показывает меню использования файла с учетом ограничений"""
        menu = QMenu()
        
        ext = Path(file_path).suffix.lower()
        path_obj = Path(file_path)
        
        is_bg_file = 'backgrounds' in str(path_obj).lower()
        is_char_file = 'characters' in str(path_obj).lower() and not is_bg_file
        
        if ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
            if not is_bg_file:
                menu.addAction("🖼️ Использовать как спрайт", 
                            lambda: self._use_as_asset(file_path, 'sprite'))
            
            if not is_char_file:
                
                if not is_char_file or is_bg_file: 
                    menu.addAction("🌄 Использовать как фон", 
                                lambda: self._use_as_asset(file_path, 'bg'))
                
                if not is_bg_file and not is_char_file:
                    menu.addAction("🌄 Использовать как фон", 
                                lambda: self._use_as_asset(file_path, 'bg'))

        elif ext in ['.mp3', '.ogg', '.wav']:
            menu.addAction("🎵 Использовать как музыку", 
                        lambda: self._use_as_asset(file_path, 'music'))
            menu.addAction("🔊 Использовать как звук", 
                        lambda: self._use_as_asset(file_path, 'sound'))
        
        menu.addSeparator()
        menu.addAction("📂 Открыть в проводнике", 
                    lambda: self._open_in_explorer(file_path))
        menu.addAction("📋 Копировать путь", 
                    lambda: self._copy_path(file_path))
        
        menu.exec(global_pos)
    
    def _move_asset_to_category(self, file_path_str, category, char_folder_name=None):
        """
        Перемещает файл в соответствующую папку.
        music -> audio/music
        sound -> audio/sound
        bg -> images/backgrounds
        sprite -> images/characters/[char_folder_name]/ (если указан) или images/characters/
        """
        if not self.project_manager.is_project_open:
            return Path(file_path_str)

        src = Path(file_path_str)
        if not src.exists():
            return src

        game_images = self.project_manager.game_path / "images"
        game_audio = self.project_manager.game_path / "audio"
        
        if category == 'bg':
            target_dir = game_images / "backgrounds"
        elif category == 'sprite':
            target_dir = game_images / "characters"
            if char_folder_name:
                target_dir = target_dir / char_folder_name
        elif category == 'music':
            target_dir = game_audio / "music"
        elif category == 'sound':
            target_dir = game_audio / "sound"
        else:
            return src

        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / src.name

        if src.resolve() == dest.resolve():
            return dest

        if dest.exists() and src.resolve() != dest.resolve():
            base_name = src.stem
            suffix = src.suffix
            counter = 1
            while dest.exists():
                new_name = f"{base_name}_{counter}{suffix}"
                dest = target_dir / new_name
                counter += 1

        try:
            shutil.move(str(src), str(dest))
            print(f"[AssetDock] Moved {src.name} to {category} ({char_folder_name})")
            return dest
        except Exception as e:
            print(f"[AssetDock] Error moving file: {e}")
            return src

    def _get_character_folder_name(self, block=None):
        """
        Определяет имя папки персонажа на основе блока или глобального состояния.
        Возвращает None, если папка не нужна (например, для фона или если персонаж не выбран).
        """
        char_name = None
        
        if block and hasattr(block, '_props'):
            char_name = block._props.get('character')
        
        if not char_name or char_name == "Мысли":
            return None
            
        return char_name

    def _use_as_asset(self, file_path, asset_type):
        """Перемещает файл в нужную папку и создает/обновляет блок"""
        main_window = self.parent()
        if not main_window or not hasattr(main_window, 'scene'):
            return
            
        if not main_window.project_manager.is_project_open:
            return

        scene = main_window.scene
        view = main_window.view
        
        selected_blocks = [item for item in scene.selectedItems() 
                        if hasattr(item, 'block_type')]
        
        target_block = selected_blocks[0] if selected_blocks else None
        
        char_folder_name = None
        if asset_type == 'sprite':
            char_folder_name = self._get_character_folder_name(target_block)

        new_path_obj = self._move_asset_to_category(file_path, asset_type, char_folder_name)
        filename = new_path_obj.name
        
        current_dir = Path(file_path).parent
        if current_dir != new_path_obj.parent:
            self.refresh() 

        if target_block:
            block = target_block
            
            if asset_type == 'sprite':
                if block.block_type in ['Спрайт', 'Анимация спрайта']:
                    block._props['sprite_name'] = filename
                    if 'sprite_name' in block.controls:
                        block.controls['sprite_name'].setText(filename)
            elif asset_type == 'bg':
                if block.block_type == 'Задний фон':
                    block._props['bg_name'] = filename
                    if 'bg_name' in block.controls:
                        block.controls['bg_name'].setText(filename)
            elif asset_type == 'music':
                if block.block_type == 'Музыка':
                    block._props['name'] = filename
                    if 'name' in block.controls:
                        block.controls['name'].setText(filename)
            elif asset_type == 'sound':
                if block.block_type == 'Звук':
                    block._props['name'] = filename
                    if 'name' in block.controls:
                        block.controls['name'].setText(filename)
            
            block._update_summary()
            block.update()
        else:
            center = view.mapToScene(view.viewport().rect().center())
            
            if asset_type == 'sprite':
                block_type = 'Спрайт'
                props = {'sprite_name': filename}
            elif asset_type == 'bg':
                block_type = 'Задний фон'
                props = {'bg_name': filename}
            elif asset_type == 'music':
                block_type = 'Музыка'
                props = {'name': filename}
            elif asset_type == 'sound':
                block_type = 'Звук'
                props = {'name': filename}
            else:
                return
            
            scene.add_block(block_type, {
                "x": center.x() - 140,
                "y": center.y() - 50,
                "properties": props
            })
    
    def import_assets(self):
        """Импортирует файлы с автоматической сортировкой по папкам"""
        if not self.project_manager.is_project_open:
            QMessageBox.warning(self, "Ошибка", "Сначала откройте или создайте проект!")
            return
        
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Импортировать файлы",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif);;Audio (*.mp3 *.ogg *.wav);;All Files (*)"
        )
        
        if not files:
            return
        
        images_path = self.project_manager.game_path / "images"
        audio_base = self.project_manager.game_path / "audio"
        
        images_path.mkdir(parents=True, exist_ok=True)
        (images_path / "backgrounds").mkdir(exist_ok=True)
        (images_path / "characters").mkdir(exist_ok=True)
        
        audio_base.mkdir(parents=True, exist_ok=True)
        (audio_base / "music").mkdir(exist_ok=True)
        (audio_base / "sound").mkdir(exist_ok=True)

        copied_count = 0
        import shutil
        
        for file_path_str in files:
            file_path = Path(file_path_str)
            ext = file_path.suffix.lower()
            dest = None
            
            if ext in ['.mp3', '.ogg', '.wav']:
                name_lower = file_path.name.lower()
                music_keywords = ['bgm', 'ost', 'theme', 'music', 'track', 'loop', 'soundtrack']
                
                if any(kw in name_lower for kw in music_keywords):
                    dest = audio_base / "music" / file_path.name
                else:
                    dest = audio_base / "sound" / file_path.name
                    
            elif ext in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
                if file_path.name.lower().startswith('bg'):
                    dest = images_path / "backgrounds" / file_path.name
                else:
                    dest = images_path / "characters" / file_path.name
            else:
                dest = images_path / file_path.name
                
            try:
                shutil.copy2(file_path, dest)
                copied_count += 1 
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось скопировать {file_path.name}:\n{e}")
        
        if copied_count > 0:
            self.refresh()
            main_window = self.parent()
            if main_window and hasattr(main_window, 'tree_dock'):
                main_window.tree_dock.refresh()
                
            QMessageBox.information(self, "Готово", f"Импортировано файлов: {copied_count}")
    
    def _open_in_explorer(self, path):
        """Открывает папку в проводнике"""
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        
        path_obj = Path(path)
        if path_obj.is_file():
            path_obj = path_obj.parent
        
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path_obj)))
    
    def _copy_path(self, path):
        """Копирует путь в буфер обмена"""
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(str(path))
        
        if hasattr(self.parent(), 'statusBar'):
            self.parent().statusBar().showMessage(f"Путь скопирован", 2000)