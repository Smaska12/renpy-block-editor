from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                               QColorDialog, QMessageBox, QAbstractItemView, QInputDialog, QWidget)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from core.theme_manager import theme

class CharactersDialog(QDialog):
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.scene = scene
        self.setWindowTitle("👥 Управление персонажами")
        self.setModal(True)
        self.resize(650, 450)
        self.selected_color = QColor("#808080")
        self.setup_ui()
        self.refresh_table()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        add_frame = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Имя нового персонажа...")

        self.color_btn = QPushButton("🎨 Цвет")
        self.color_btn.setFixedWidth(80)
        self._update_color_btn_style()
        self.color_btn.clicked.connect(self._pick_color)

        self.add_btn = QPushButton("➕ Добавить")
        self.add_btn.clicked.connect(self._add_character)

        add_frame.addWidget(self.name_input, 1)
        add_frame.addWidget(self.color_btn)
        add_frame.addWidget(self.add_btn)
        layout.addLayout(add_frame)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Имя", "Цвет", "Действия"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 60)
        self.table.setColumnWidth(2, 110)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        layout.addWidget(QLabel("💡 Изменения применяются мгновенно. При удалении персонажа его имя в блоках сбросится на 'Мысли'."))

    def _update_color_btn_style(self):
        c = theme.get()
        text_color = "white" if self.selected_color.lightness() < 128 else c['text_main']
        self.color_btn.setStyleSheet(f"""
            background-color: {self.selected_color.name()};
            color: {text_color};
            font-weight: bold;
            border-radius: 4px;
            border: 1px solid {c['border']};
        """)

    def _pick_color(self):
        color = QColorDialog.getColor(self.selected_color, self, "Выберите цвет реплик")
        if color.isValid():
            self.selected_color = color
            self._update_color_btn_style()

    def _add_character(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя персонажа!")
            return
        if name in self.scene.characters:
            QMessageBox.warning(self, "Ошибка", "Персонаж с таким именем уже существует!")
            return

        if self.scene.parent_window and hasattr(self.scene.parent_window, 'project_manager'):
            pm = self.scene.parent_window.project_manager
            if pm.is_project_open and pm.game_path:
                char_folder = pm.game_path / "images" / "characters" / name
                try:
                    char_folder.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    print(f"Warning: Could not create character folder: {e}")

        self.scene.characters[name] = {"color": self.selected_color.name()}
        self.name_input.clear()
        self.refresh_table()
        self.scene.update_character_dropdowns()

    def _delete_character(self, row):
        name = self.table.item(row, 0).text()
        if name == "Мысли":
            QMessageBox.warning(self, "Запрещено", "Нельзя удалить системного персонажа 'Мысли'!")
            return
        if QMessageBox.question(self, "Подтверждение", f"Удалить персонажа '{name}'?") == QMessageBox.Yes:
            del self.scene.characters[name]
            self.refresh_table()
            self.scene.update_character_dropdowns(deleted_name=name)

    def _edit_character(self, row):
        old_name = self.table.item(row, 0).text()
        old_color = self.scene.characters[old_name]["color"]

        new_name, ok = QInputDialog.getText(self, "Редактировать", "Новое имя:", text=old_name)
        if not ok or not new_name.strip(): return
        new_name = new_name.strip()

        color_dialog = QColorDialog(QColor(old_color), self)
        if color_dialog.exec():
            new_color = color_dialog.selectedColor().name()
        else:
            new_color = old_color

        if new_name != old_name and new_name in self.scene.characters:
            QMessageBox.warning(self, "Ошибка", "Имя уже занято!")
            return

        if new_name != old_name:
            self.scene.characters[new_name] = self.scene.characters.pop(old_name)
            self.scene.characters[new_name]["color"] = new_color
            for item in self.scene.items():
                if hasattr(item, 'controls') and 'character' in item.controls:
                    if item.controls['character'].currentText() == old_name:
                        item.controls['character'].setCurrentText(new_name)
        else:
            self.scene.characters[old_name]["color"] = new_color

        self.refresh_table()
        self.scene.update_character_dropdowns()

    def refresh_table(self):
        self.table.setRowCount(0)
        c = theme.get()
        for name, data in self.scene.characters.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            color_item = QTableWidgetItem()
            color_item.setBackground(QColor(data.get("color", "#808080")))
            self.table.setItem(row, 1, color_item)

            btn_widget = QWidget()
            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0,0,0,0)
            edit_btn = QPushButton("✏️")
            del_btn = QPushButton("🗑️")
            
            edit_btn.clicked.connect(lambda _, r=row: self._edit_character(r))
            del_btn.clicked.connect(lambda _, r=row: self._delete_character(r))
            
            btn_layout.addWidget(edit_btn)
            btn_layout.addWidget(del_btn)
            self.table.setCellWidget(row, 2, btn_widget)