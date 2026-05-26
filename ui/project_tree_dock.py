import shutil
import base64
from PySide6.QtWidgets import (QTreeWidgetItem, QDockWidget, QTreeWidget, QMenu, QStyle,
                               QMessageBox, QDialog, QVBoxLayout, QLabel, QScrollArea, 
                               QPushButton, QHBoxLayout, QInputDialog)
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtCore import Qt, QMimeData, QPoint, QIODevice, QBuffer
from pathlib import Path
from core.theme_manager import theme

PROTECTED_ITEMS = {
    'audio', 'cache', 'gui', 'images', 'libs', 'saves', 'tl',
    'gui.rpy', 'gui.rpyc', 'options.rpy', 'options.rpyc',
    'screens.rpy', 'screens.rpyc', 'script.rpy', 'script.rpyc'
}

class ImagePreviewDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Просмотр: {Path(image_path).name}")
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        c = theme.get()
        scroll.setStyleSheet(f"background-color: {c['bg_surface']}; border: none;")
        scroll.setWidgetResizable(True)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            screen_geo = self.screen().geometry()
            max_w = int(screen_geo.width() * 0.8)
            max_h = int(screen_geo.height() * 0.8)
            if pixmap.width() > max_w or pixmap.height() > max_h:
                pixmap = pixmap.scaled(max_w, max_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(pixmap)
            scroll.setWidget(self.image_label)
        else:
            self.image_label.setText("Не удалось загрузить изображение")
            scroll.setWidget(self.image_label)
        layout.addWidget(scroll)
        btn_close = QPushButton("Закрыть")
        btn_close.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)
        if not pixmap.isNull():
            self.resize(min(pixmap.width() + 50, max_w), min(pixmap.height() + 100, max_h))
        else:
            self.resize(400, 300)

class ProjectTreeDock(QDockWidget):
    def __init__(self, project_manager, parent=None):
        super().__init__("Структура проекта", parent)
        self.project_manager = project_manager
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Файлы и папки")
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.setIndentation(15)
        
        self.tree.setDragEnabled(False)
        self.tree.setAcceptDrops(False)
        
        self.setWidget(self.tree)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemEntered.connect(self._on_item_hover)

    def _is_protected(self, item_name):
        return item_name.lower() in PROTECTED_ITEMS

    def _on_item_hover(self, item, column):
        file_path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path_str:
            return
        file_path = Path(file_path_str)
        if file_path.is_file() and file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                scaled = pixmap.scaledToWidth(200, Qt.SmoothTransformation)
                buffer = QBuffer()
                buffer.open(QIODevice.WriteOnly)
                scaled.save(buffer, "PNG")
                data = base64.b64encode(buffer.data()).decode('utf-8')
                buffer.close()
                html_tip = f'<img src="image/png;base64,{data}"/>'
                item.setToolTip(column, html_tip)
        else:
            item.setToolTip(column, str(file_path))

    def refresh(self):
        self.tree.clear()
        if not self.project_manager.is_project_open:
            item = QTreeWidgetItem(["Проект не открыт"])
            item.setForeground(0, Qt.gray)
            self.tree.addTopLevelItem(item)
            return
        root = QTreeWidgetItem([self.project_manager.project_path.name])
        root.setToolTip(0, str(self.project_manager.project_path))
        root.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
        self.tree.addTopLevelItem(root)
        root.setExpanded(True)
        self._add_directory(root, self.project_manager.project_path)
        self.tree.expandToDepth(1)

    def _add_directory(self, parent_item, dir_path):
        try:
            items = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                if item.name in ['__pycache__', '.git', '.vscode', '.idea']:
                    continue
                if item.suffix in ['.pyc', '.pyo']:
                    continue
                child = QTreeWidgetItem([item.name])
                child.setToolTip(0, str(item))
                child.setData(0, Qt.ItemDataRole.UserRole, str(item))
                if item.is_dir():
                    child.setIcon(0, self.style().standardIcon(QStyle.SP_DirIcon))
                    self._add_directory(child, item)
                else:
                    child.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))
                parent_item.addChild(child)
        except PermissionError:
            print(f"[TreeDock] Нет доступа к папке: {dir_path}")
        except Exception as e:
            print(f"[TreeDock] Ошибка при чтении {dir_path}: {e}")

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path:
            return
        path_obj = Path(file_path)
        is_protected = self._is_protected(path_obj.name)
        menu = QMenu()
        menu.addAction("Открыть в проводнике", lambda: self._open_in_explorer(file_path))
        menu.addAction("Копировать путь", lambda: self._copy_path(file_path))
        menu.addSeparator()
        if path_obj.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
            menu.addAction("Просмотреть изображение", lambda: self._preview_image(file_path))
        if path_obj.suffix == '.rpy':
            menu.addAction("Открыть в редакторе", lambda: self._open_in_editor(file_path))
        menu.addSeparator()
        if not is_protected:
            menu.addAction("Переименовать", lambda: self._rename_item(item))
            menu.addAction("Удалить", lambda: self._delete_item(item))
        menu.exec_(self.tree.mapToGlobal(position))

    def _rename_item(self, item):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path:
            return
        path_obj = Path(file_path)
        new_name, ok = QInputDialog.getText(self, "Переименовать", "Новое имя:", text=path_obj.name)
        if ok and new_name and new_name != path_obj.name:
            try:
                path_obj.rename(path_obj.parent / new_name)
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось переименовать: {e}")

    def _delete_item(self, item):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path:
            return
        path_obj = Path(file_path)
        reply = QMessageBox.question(self, "Подтверждение", f"Вы уверены, что хотите удалить {path_obj.name}?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                if path_obj.is_dir():
                    shutil.rmtree(path_obj)
                else:
                    path_obj.unlink()
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось удалить: {e}")

    def _preview_image(self, file_path):
        ImagePreviewDialog(file_path, self).exec_()

    def _on_item_double_clicked(self, item, column):
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not file_path:
            return
        file_path = Path(file_path)
        if file_path.is_dir():
            item.setExpanded(not item.isExpanded())
        elif file_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp', '.gif']:
            self._preview_image(str(file_path))
        elif file_path.suffix == '.rpy':
            self._open_in_editor(str(file_path))

    def _open_in_explorer(self, path):
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl
        path_obj = Path(path)
        if path_obj.is_file():
            path_obj = path_obj.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path_obj)))

    def _copy_path(self, path):
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(str(path))
        if hasattr(self.parent(), 'statusBar'):
            self.parent().statusBar().showMessage(f"Путь скопирован: {path}", 2000)

    def _open_in_editor(self, path):
        import subprocess, sys, os
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path])
            else:
                subprocess.run(["xdg-open", path])
            if hasattr(self.parent(), 'statusBar'):
                self.parent().statusBar().showMessage(f"Файл открыт: {path}", 2000)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось открыть файл:\n{str(e)}")