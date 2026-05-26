from pathlib import Path
import shutil
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QComboBox,
                               QSlider, QSpinBox, QPushButton, QHBoxLayout, QCheckBox,
                               QScrollArea, QSizePolicy, QFileDialog, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from core.theme_manager import theme

class PropertyDock(QWidget):
    def __init__(self, scene_ref, parent=None):
        super().__init__(parent)
        self.scene = scene_ref
        self.current_block = None
        self.widgets = {}
        self.widgets_meta = {}
        self.blocking_signals = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self.title_label = QLabel("Свойства блока")
        self.title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.color('text_main')}; margin-bottom: 4px;")
        layout.addWidget(self.title_label)

        self.form_container = QWidget()
        self.form_layout = QFormLayout(self.form_container)
        self.form_layout.setSpacing(6)
        self.form_layout.setContentsMargins(0, 4, 0, 0)
        
        self.form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        self.form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setWidget(self.form_container)
        
        layout.addWidget(self.scroll_area)

        self.empty_label = QLabel("Выберите блок на холсте", alignment=Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {theme.color('text_muted')}; padding: 20px;")
        layout.addWidget(self.empty_label)
        layout.addStretch()

    def set_block(self, block):
        self.setUpdatesEnabled(False)
        self._clear_form()
        self.current_block = block
        
        if not block:
            self.empty_label.show()
            self.scroll_area.hide()
            self.title_label.setText("Свойства блока")
        else:
            self.empty_label.hide()
            self.scroll_area.show()
            self.title_label.setText(f"🔹 {block.block_type}")
            
            self.blocking_signals = True
            self._build_form(block.block_type, block.get_properties())
            self.blocking_signals = False
            
        self.setUpdatesEnabled(True)
        self.updateGeometry()
        QTimer.singleShot(0, self._fit_form_to_available_space)

    def _fit_form_to_available_space(self):
        """Заставляет форму занять всё доступное место"""
        if self.current_block:
            self.form_layout.activate()
            self.scroll_area.updateGeometry()
            self.updateGeometry()

    def _clear_form(self):
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget(): 
                child.widget().deleteLater()
        self.widgets.clear()
        self.widgets_meta.clear()

    def _build_form(self, block_type, props):
        chars = list(self.scene.characters.keys())

        if block_type == "Текст":
            self._add_combo("character", "Персонаж:", chars, props.get("character"), tip="Имя персонажа из менеджера")
            self._add_line("text", "Диалог:", props.get("text", ""), tip="Текст реплики")
            self._add_combo("transition", "Переход:", ["None", "dissolve", "fade", "move", "ease"], props.get("transition", "None"), tip="Эффект появления")
            self._add_checkbox("interact", "Интерактив:", props.get("interact", True), tip="Если выкл., текст покажется автоматически")
            self._add_file_picker("voice", "Голос:", props.get("voice", ""), "Audio (*.ogg *.wav *.mp3)", tip="Файл озвучки")

        elif block_type == "Выбор ответа":
            self._build_choices(props.get("choices", [{"text": "Вариант 1", "target": "start", "condition": ""}]))

        elif block_type == "Спрайт":
            self._add_combo("character", "Персонаж:", chars, props.get("character"), tip="Целевой персонаж")
            self._add_combo("action", "Действие:", ["show", "hide", "replace"], props.get("action", "show"), tip="show - показать, hide - скрыть")
            self._add_file_picker("sprite_name", "Файл спрайта:", props.get("sprite_name", ""), "Images (*.png *.jpg *.webp)", tip="Имя файла изображения")
            self._add_line("expression", "Выражение:", props.get("expression", ""), tip="Напр: happy, sad (для заметок)")
            self._add_combo("position", "Позиция:", ["center", "left", "right", "truecenter", "custom"], props.get("position", "center"), tip="Стандартная позиция")
            
            if props.get("position") == "custom":
                self._add_slider("xalign", "X:", props.get("xalign", 0.5), tip="Горизонтальная позиция (0.0 - 1.0)")
                self._add_slider("yalign", "Y:", props.get("yalign", 1.0), tip="Вертикальная позиция (0.0 - 1.0)")
                
            self._add_spin("zoom", "Масштаб:", props.get("zoom", 1.0), 0.1, 3.0, 0.05, tip="Размер спрайта")
            self._add_combo("transition", "Переход:", ["None", "dissolve", "fade", "move"], props.get("transition", "dissolve"), tip="Эффект появления")

        elif block_type == "Задний фон":
            self._add_file_picker("bg_name", "Имя фона:", props.get("bg_name", ""), "Images (*.png *.jpg *.webp)", tip="Файл фонового изображения")
            self._add_combo("transition", "Переход:", ["None", "fade", "dissolve", "move"], props.get("transition", "fade"), tip="Эффект смены сцены")
            self._add_checkbox("clear_layer", "Очистить слой (scene):", props.get("clear_layer", True), tip="Скроет все спрайты перед показом нового фона")

        elif block_type in ["Музыка", "Звук"]:
            ch = "music" if block_type == "Музыка" else "sound"
            filter_str = "Audio (*.mp3 *.ogg *.wav)"
            self._add_file_picker("name", f"Файл {ch}:", props.get("name", ""), filter_str, tip="Путь к аудиофайлу")
            self._add_combo("action", "Действие:", ["play", "stop", "queue"], props.get("action", "play"), tip="play - играть, stop - остановить")
            self._add_slider("volume", "Громкость:", props.get("volume", 0.8), tip="Уровень громкости от 0.0 до 1.0")
            if ch == "music":
                self._add_spin("fadein", "Fade In (с):", props.get("fadein", 1.0), 0.0, 5.0, 0.1, tip="Время плавного появления")
                self._add_checkbox("loop", "Зациклить:", props.get("loop", True), tip="Повторять трек бесконечно")
            else:
                self._add_spin("fadeout", "Fade Out (с):", props.get("fadeout", 0.0), 0.0, 5.0, 0.1, tip="Время плавного затухания")

        elif block_type == "Анимация спрайта":
            self._add_combo("character", "Персонаж: ", chars, props.get("character"), tip="Целевой персонаж")
            
            sprite_combo = QComboBox()
            sprite_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            
            sprites = []
            if self.scene.parent_window and self.scene.parent_window.project_manager.is_project_open:
                pm = self.scene.parent_window.project_manager
                base = pm.game_path / "images" / "characters"
                char = props.get("character", "Мысли")
                target = base if char == "Мысли" else base / char
                
                if target.exists():
                    sprites = [f.name for f in target.iterdir() if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']]
                    sprites.sort()

            sprite_combo.addItems(sprites)
            if props.get("sprite_name") in sprites:
                sprite_combo.setCurrentText(props.get("sprite_name"))
            elif sprites:
                sprite_combo.setCurrentIndex(0)

            self.widgets["sprite_name"] = sprite_combo
            self.widgets_meta["sprite_name"] = {'type': 'combo', 'items': sprites}
            
            sprite_combo.currentTextChanged.connect(lambda v: self._on_prop_change("sprite_name", v))
            
            self.form_layout.addRow("Спрайт: ", sprite_combo)

            self._add_combo("anim_type", "Тип движения: ", ["move", "ease", "linear", "zoom"], props.get("anim_type", "move"), tip="Тип трансформации")
            self._add_spin("duration", "Длительность (с): ", props.get("duration", 1.0), 0.1, 10.0, 0.1, tip="Сколько секунд займет анимация")
            self._add_slider("start_x", "Начало X: ", props.get("start_x", 0.2), tip="Начальная горизонтальная позиция")
            self._add_slider("end_x", "Конец X: ", props.get("end_x", 0.8), tip="Конечная горизонтальная позиция")
            self._add_combo("easing", "Сглаживание: ", ["linear", "easein", "easeout", "easeinout"], props.get("easing", "linear"), tip="Кривая скорости")


    def update_property_value(self, key, value):
        if key not in self.widgets: return
        widget = self.widgets[key]
        was_blocked = widget.blockSignals(True)
        try:
            if isinstance(widget, QComboBox):
                text_val = str(value).strip()
                idx = widget.findText(text_val)
                if idx >= 0: widget.setCurrentIndex(idx)
                else: widget.setCurrentText(text_val)
            elif isinstance(widget, QLineEdit):
                if widget.text() != str(value): widget.setText(str(value))
            elif isinstance(widget, QSlider):
                int_val = int(float(value) * 100)
                if widget.value() != int_val: widget.setValue(int_val)
            elif isinstance(widget, QSpinBox):
                step = self.widgets_meta.get(key, {}).get('step', 0.1)
                calculated_val = int(round(float(value) / step))
                if widget.value() != calculated_val: widget.setValue(calculated_val)
            elif isinstance(widget, QCheckBox):
                bool_val = bool(value)
                if widget.isChecked() != bool_val: widget.setChecked(bool_val)
        finally:
            widget.blockSignals(was_blocked)
            widget.update()

    def refresh_character_list(self):
        if not self.current_block or 'character' not in self.widgets: return
        combo = self.widgets['character']
        current = combo.currentText()
        chars = list(self.scene.characters.keys())
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(chars)
        if current in chars: combo.setCurrentText(current)
        elif chars: combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _add_combo(self, key, label, items, current, tip=""):
        combo = QComboBox()
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        combo.addItems(items)
        if current and current in items: combo.setCurrentText(current)
        elif items:
            if "Мысли" in items: combo.setCurrentText("Мысли")
            else: combo.setCurrentIndex(0)
        combo.setToolTip(tip)
        combo.currentTextChanged.connect(lambda v: self._on_prop_change(key, v))
        self.form_layout.addRow(label, combo)
        self.widgets[key] = combo

    def _add_line(self, key, label, text, tip=""):
        line = QLineEdit(text)
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.setToolTip(tip)
        line.textChanged.connect(lambda v: self._on_prop_change(key, v))
        self.form_layout.addRow(label, line)
        self.widgets[key] = line
        self.widgets_meta[key] = {'type': 'line'}

    def _add_slider(self, key, label, value, tip=""):
        slider = QSlider(Qt.Horizontal)
        slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        slider.setRange(0, 100)
        slider.setValue(int(value * 100))
        slider.setToolTip(tip)
        slider.valueChanged.connect(lambda v: self._on_prop_change(key, v / 100.0))
        self.form_layout.addRow(label, slider)
        self.widgets[key] = slider
        self.widgets_meta[key] = {'type': 'slider'}

    def _add_spin(self, key, label, value, min_v, max_v, step, tip=""):
        spin = QSpinBox()
        spin.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        spin.setRange(int(min_v/step), int(max_v/step))
        spin.setValue(int(value/step))
        spin.setSingleStep(1)
        spin.setSuffix(f" ({step})")
        spin.setToolTip(tip)
        spin.valueChanged.connect(lambda v: self._on_prop_change(key, v * step))
        self.form_layout.addRow(label, spin)
        self.widgets[key] = spin
        self.widgets_meta[key] = {'type': 'spin', 'step': step}

    def _add_checkbox(self, key, label, checked, tip=""):
        cb = QCheckBox()
        cb.setChecked(checked)
        cb.setToolTip(tip)
        cb.toggled.connect(lambda v: self._on_prop_change(key, v))
        self.form_layout.addRow(label, cb)
        self.widgets[key] = cb
        self.widgets_meta[key] = {'type': 'check'}

    def _add_file_picker(self, key, label, default, filter_str, tip=""):
        row = QWidget()
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(4)
        
        line = QLineEdit(default)
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.setToolTip(tip)
        line.textChanged.connect(lambda v: self._on_prop_change(key, v))
        
        btn = QPushButton("📂")
        btn.setFixedWidth(42) 
        btn.setToolTip("Выбрать файл")
        btn.clicked.connect(lambda: self._browse_file(key, line, filter_str))
        
        lay.addWidget(line, 1) 
        lay.addWidget(btn)    
        self.form_layout.addRow(label, row)
        self.widgets[key] = line

    def _browse_file(self, key, line_edit, filter_str):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", filter_str)
        if not path: return
        
        block = self.current_block
        if not block or not block.scene_ref or not hasattr(block.scene_ref, 'parent_window'):
            line_edit.setText(os.path.basename(path))
            return
        
        main_window = block.scene_ref.parent_window
        pm = main_window.project_manager
        if not pm.is_project_open:
            line_edit.setText(os.path.basename(path))
            return
        
        src = Path(path)
        block_type = block.block_type
        
        target_dir = None
        if block_type == "Спрайт" and key == "sprite_name":
            char_name = block._props.get("character", "").strip()
            if char_name and char_name != "Мысли":
                target_dir = pm.game_path / "images" / "characters" / char_name
            else:
                target_dir = pm.game_path / "images" / "characters"
        elif block_type == "Задний фон" and key == "bg_name":
            target_dir = pm.game_path / "images" / "backgrounds"
        elif block_type == "Музыка" and key == "name":
            target_dir = pm.game_path / "audio" / "music"
        elif block_type == "Звук" and key == "name":
            target_dir = pm.game_path / "audio" / "sound"
        elif block_type == "Текст" and key == "voice":
            target_dir = pm.game_path / "audio" / "voice"
        else:
            line_edit.setText(src.name)
            return
        
        if not target_dir:
            line_edit.setText(src.name)
            return
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        dest = target_dir / src.name
        if dest.exists():
            base = src.stem
            suffix = src.suffix
            counter = 1
            while dest.exists():
                new_name = f"{base}_{counter}{suffix}"
                dest = target_dir / new_name
                counter += 1
        
        try:
            shutil.copy2(src, dest)
            line_edit.setText(dest.name) 
            if hasattr(main_window, 'asset_dock'): 
                main_window.asset_dock.refresh()
            if hasattr(main_window, 'tree_dock'): 
                main_window.tree_dock.refresh()
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось скопировать файл:\n{e}")
            line_edit.setText(src.name)

    def _build_choices(self, choices):
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0,0,0,0)
        c_layout.setSpacing(4)
        self.widgets["choice_widgets"] = []

        if not choices:
            choices = [{"text": "Вариант 1", "target": "start", "condition": ""}]
            
        for item in choices:
            if isinstance(item, dict):
                self._add_choice_row_dict(c_layout, item)
            else:
                self._add_choice_row_dict(c_layout, {"text": item[0], "target": item[1], "condition": ""})

        btn = QPushButton("+ Добавить вариант")
        btn.clicked.connect(lambda: self._add_choice_row_dict(c_layout))
        c_layout.addWidget(btn)
        self.form_layout.addRow("Варианты:", container)
        self.widgets["choices_container"] = container

    def _add_choice_row_dict(self, layout, data=None):
        if not data: data = {"text": "Вариант", "target": "start", "condition": ""}
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0,0,0,0)
        lay.setSpacing(4)

        entry = QLineEdit(data.get("text", ""))
        entry.setPlaceholderText("Текст варианта")
        entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        entry.textChanged.connect(self._sync_choices)

        combo = QComboBox()
        combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        combo.addItems(["start"] + [k for k in self.scene.labels.keys() if k != "start"])
        combo.setCurrentText(data.get("target", "start"))
        combo.currentTextChanged.connect(self._sync_choices)

        cond = QLineEdit(data.get("condition", ""))
        cond.setPlaceholderText("условие (напр. points > 5)")
        cond.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cond.textChanged.connect(self._sync_choices)

        lay.addWidget(QLabel("Текст:"), 0)
        lay.addWidget(entry, 2)
        lay.addWidget(combo, 1)
        lay.addWidget(QLabel("If:"), 0)
        lay.addWidget(cond, 2)

        layout.addWidget(row)
        self.widgets["choice_widgets"].append((entry, combo, cond))
        self._sync_choices()

    def _sync_choices(self):
        if "choice_widgets" not in self.widgets: return
        
        choices = []
        for entry, combo, cond in self.widgets["choice_widgets"]:
            choice_data = {
                "text": entry.text(),
                "target": combo.currentText(),
                "condition": cond.text()
            }
            if choice_data["text"] and choice_data["target"]:
                choices.append(choice_data)
        
        if choices:  
            self._on_prop_change("choices", choices)
        
        if self.current_block and hasattr(self.current_block, 'update_choice_display'):
            self.current_block.update_choice_display()

    def _on_prop_change(self, key, value):
        if self.blocking_signals or not self.current_block: return
        
        was_collapsed = getattr(self.current_block, 'collapsed', False)
        old_val = self.current_block._props.get(key)
        self.current_block.update_properties({key: value})
        
        from core.commands import SetPropertyCommand
        self.scene.undo_stack.push(SetPropertyCommand(self.current_block, key, old_val, value))
        
        if was_collapsed and not self.current_block.collapsed:
            self.current_block.toggle_collapsed()
            
        self.scene.notify_code_change()

    def refresh_theme(self):
        c = theme.get()
        self.title_label.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {c['text_main']}; margin-bottom: 2px;")
        self.empty_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 13px;")
        
        for i in range(self.form_layout.rowCount()):
            lbl = self.form_layout.itemAt(i, QFormLayout.LabelRole)
            if lbl and lbl.widget():
                lbl.widget().setStyleSheet(f"color: {c['text_secondary']}; font-size: 12px; font-weight: 500;")