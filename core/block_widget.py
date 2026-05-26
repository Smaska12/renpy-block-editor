import uuid
from PySide6.QtWidgets import (QGraphicsRectItem, QGraphicsProxyWidget, QVBoxLayout, QHBoxLayout,
QLabel, QPushButton, QLineEdit, QComboBox, QSlider, QSpinBox,
QRadioButton, QMenu, QWidget, QStyle, QGraphicsItem, QApplication,
QCheckBox, QSizePolicy, QMessageBox)
from PySide6.QtCore import Qt, QPointF, QRectF, QTimer, QSize, QUrl
from PySide6.QtGui import QPixmap, QIcon, QPainter, QBrush, QColor, QPen, QPainterPath, QFont
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from .constants import BLOCK_COLORS
from .connection_system import PortItem
from core.theme_manager import theme
from core.focus_widgets import FocusableLineEdit, FocusableComboBox

BLOCK_STYLES = {
    "Текст":           {"color": "#3B82F6", "icon": "💬"},
    "Выбор ответа":    {"color": "#8B5CF6", "icon": "🔀"},
    "Спрайт":          {"color": "#10B981", "icon": "🖼️"},
    "Задний фон":      {"color": "#F59E0B", "icon": "🌄"},
    "Музыка":          {"color": "#EC4899", "icon": "🎵"},
    "Звук":            {"color": "#F97316", "icon": "🔊"},
    "Анимация спрайта":{"color": "#6366F1", "icon": "🎬"},
}

class BlockWidget(QGraphicsRectItem):
    def __init__(self, block_type, scene_ref, x=0, y=0, properties=None):
        super().__init__(0, 0, 260, 100)
        self.setPos(x, y)
        self.block_type = block_type
        self.scene_ref = scene_ref
        self._props = properties or {}
        self.block_id = self._props.get("block_id", str(uuid.uuid4()))
        
        if "collapsed" in self._props:
            self.collapsed = self._props["collapsed"]
        else:
            self.collapsed = getattr(scene_ref, 'default_block_collapsed', False)
            self._props["collapsed"] = self.collapsed

        self.expanded_height = 100
        self.collapse_btn = None

        self.setPen(QPen(Qt.transparent))
        self.setBrush(QBrush(QColor(theme.color('bg_surface')))) 
        
        self.ports = {'in': [], 'out': []}
        self.group_ref = None
        self._setup_ports(self._props)
        self._set_ports_visible(False)

        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)  
        
        # UI-контейнер
        self.ui_widget = QWidget()
        self.ui_widget.setAttribute(Qt.WA_TranslucentBackground)
        self.ui_widget.setStyleSheet("background: transparent;")
        self.main_layout = QVBoxLayout(self.ui_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(4)
        
        self.controls = {}
        
        # Аудио плеер
        self.audio_player = None
        self.audio_output = None
        self.play_btn = None
        
        self._build_ui(self._props)
        
        self.proxy = QGraphicsProxyWidget(self) 
        self.proxy.setZValue(1)
        self.setCacheMode(QGraphicsItem.NoCache)
        self.proxy.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.proxy.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.proxy.setFocusPolicy(Qt.StrongFocus)
        self.proxy.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.proxy.setWidget(self.ui_widget)
        self.ui_widget.setFocusPolicy(Qt.StrongFocus)
        self.ui_widget.setAttribute(Qt.WA_TranslucentBackground)
        self.ui_widget.setMinimumSize(0, 0)
        self.ui_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        QTimer.singleShot(0, self.update_geometry)
        self._update_summary()

    def _setup_ports(self, props):
        self.ports = {'in': [], 'out': []}
        self.ports['in'].append(PortItem('in', 0, self))
        
        if self.block_type != "Выбор ответа":
            self.ports['out'].append(PortItem('out', 0, self))
        
        self._update_port_positions()

    def _update_port_positions(self):
        rect = self.boundingRect()
        w = rect.width()
        
        if self.ports['in']:
            self.ports['in'][0].setPos(w/2, rect.top())
         
        count = len(self.ports['out'])
        if count == 0: return

        if count == 1:
            self.ports['out'][0].setPos(w/2, rect.bottom())
        else: 
            step = w / (count + 1)
            for i, port in enumerate(self.ports['out']):
                port.setPos(step * (i + 1), rect.bottom())

    def _build_ui(self, props):
        c = theme.get()
        style = BLOCK_STYLES.get(self.block_type, {"color": c['primary'], "icon": "🔹"})

        # --- Header ---
        self.header = QWidget()
        self.header.setFixedHeight(32)
        self.header.setStyleSheet(f"background: {style['color']}; border-radius: 8px 8px 0 0;")
        self.header.setCursor(Qt.PointingHandCursor)

        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(8, 0, 6, 0)
        hl.setSpacing(6)
        hl.setAlignment(Qt.AlignVCenter)

        self.title_label = QLabel(f"{style['icon']} {self.block_type}")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        self.title_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        hl.addWidget(self.title_label)

        hl.addStretch()

        self.collapse_btn = QPushButton()
        self.collapse_btn.setFixedSize(26, 26)
        pixmap = QPixmap(26, 26)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", 12, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "▴")
        painter.end()
        
        self.collapse_btn.setIcon(QIcon(pixmap))
        self.collapse_btn.setIconSize(QSize(26, 26))
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid rgba(255,255,255,0.3);
                border-radius: 13px;
                padding: 0px; margin: 0px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.6); }
        """)
        self.collapse_btn.setToolTip("Свернуть/Развернуть")
        self.collapse_btn.clicked.connect(self.toggle_collapsed)
        hl.addWidget(self.collapse_btn, alignment=Qt.AlignVCenter | Qt.AlignRight)

        self.main_layout.addWidget(self.header)

        # --- Controls Container ---
        self.controls_container = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_container)
        self.controls_layout.setContentsMargins(4, 4, 4, 4)
        self.controls_layout.setSpacing(6)
        self._setup_controls(self.controls_layout, props)
        self.main_layout.addWidget(self.controls_container)
        
        # --- Image Preview (ONLY for Sprite and BG) ---
        self.image_preview_label = QLabel()
        self.image_preview_label.setFixedHeight(100)
        self.image_preview_label.setFixedWidth(252)
        self.image_preview_label.setAlignment(Qt.AlignCenter)
        self.image_preview_label.setWordWrap(True)
        self.image_preview_label.setStyleSheet(f"""
            background-color: {c['bg_input']};
            border-radius: 4px;
            border: 1px dashed {c['border']};
            margin: 4px;
        """)
        self.image_preview_label.setText("Нет изображения")
        self.image_preview_label.hide()
        
        self.main_layout.addWidget(self.image_preview_label)

        # --- Summary Label ---
        self.summary_label = QLabel("", self.ui_widget)
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(f"color: {c['block_preview_text']}; font-size: 11px; padding: 6px 8px; background: {c['bg_input']}; border-radius: 4px; margin: 2px;")
        self.main_layout.addWidget(self.summary_label)
        
        # Initial update
        self._update_image_preview()
        self._update_summary()

    def _setup_controls(self, layout, props):
        self.controls.clear()
        chars = list(self.scene_ref.characters.keys()) if hasattr(self.scene_ref, 'characters') else ["Мысли"]
        
        if self.block_type == "Текст":
            self.controls["character"] = self._add_row(layout, "Персонаж: ", self._combo(chars, props.get("character"), key_name="character"))
            self.controls["text"] = self._add_row(layout, "Диалог: ", self._line_edit(props.get("text", "Введите текст..."), "text"))
            self.controls["transition"] = self._add_row(layout, "Переход: ", self._combo(["None", "dissolve", "fade", "move", "ease"], props.get("transition", "None"), key_name="transition"))
            self.controls["interact"] = self._add_row(layout, "Интерактив: ", self._checkbox(props.get("interact", True), "interact"))
            self.controls["voice"] = self._add_row(layout, "Голос: ", self._line_edit(props.get("voice", ""), "voice"))

        elif self.block_type == "Выбор ответа":
            choices = props.get("choices", [{"text": "Вариант 1", "target": "start", "condition": ""}])
            self.controls["choices_data"] = choices
            
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(4)
            
            for i, ch in enumerate(choices, 1):
                text = ch.get("text", f"Вариант {i}")
                target = ch.get("target", "start")
                label = QLabel(f"{i}. {text} → {target}")
                label.setStyleSheet("color: #E2E8F0; font-size: 11px; padding: 2px;")
                layout.addWidget(label)
            
            layout.addWidget(QLabel(f"Всего вариантов: {len(choices)}"))
            
            self.controls["choice_container"] = container
            self.main_layout.addWidget(container)

        elif self.block_type == "Спрайт":
            self.controls["character"] = self._add_row(layout, "Персонаж: ", self._combo(chars, props.get("character"), key_name="character"))
            self.controls["action"] = self._add_row(layout, "Действие: ", self._combo(["show", "hide", "replace"], props.get("action", "show"), key_name="action"))
            self.controls["sprite_name"] = self._add_row(layout, "Файл: ", self._line_edit(props.get("sprite_name", ""), "sprite_name"))
            self.controls["expression"] = self._add_row(layout, "Выражение: ", self._line_edit(props.get("expression", ""), "expression"))
            self.controls["position"] = self._add_row(layout, "Позиция: ", self._combo(["center", "left", "right", "truecenter", "custom"], props.get("position", "center"), key_name="position"))
            
            if props.get("position") == "custom" or self._props.get("position") == "custom":
                self.controls["xalign"] = self._add_row(layout, "X: ", self._slider(props.get("xalign", 0.5), "xalign"))
                self.controls["yalign"] = self._add_row(layout, "Y: ", self._slider(props.get("yalign", 1.0), "yalign"))
                
            self.controls["zoom"] = self._add_row(layout, "Масштаб: ", self._spin(props.get("zoom", 1.0), 0.1, 3.0, 0.05, "zoom"))
            self.controls["transition"] = self._add_row(layout, "Переход: ", self._combo(["None", "dissolve", "fade", "move"], props.get("transition", "dissolve"), key_name="transition"))

        elif self.block_type == "Задний фон":
            self.controls["bg_name"] = self._add_row(layout, "Имя фона: ", self._line_edit(props.get("bg_name", ""), "bg_name"))
            self.controls["transition"] = self._add_row(layout, "Переход: ", self._combo(["None", "fade", "dissolve", "move"], props.get("transition", "fade"), key_name="transition"))
            self.controls["clear_layer"] = self._add_row(layout, "Очистить слой: ", self._checkbox(props.get("clear_layer", True), "clear_layer"))

        elif self.block_type in ["Музыка", "Звук"]:
            ch = "music" if self.block_type == "Музыка" else "sound"
            
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            
            line_edit = self._line_edit(props.get("name", ""), "name")
            row_layout.addWidget(line_edit, 1)
            
            play_btn = QPushButton("▶")
            play_btn.setFixedWidth(30)
            play_btn.setToolTip("Прослушать")
            play_btn.clicked.connect(lambda: self._toggle_audio_play(props.get("name", "")))
            row_layout.addWidget(play_btn)
            
            self.play_btn = play_btn
            self.controls["name"] = self._add_row(layout, f"Файл {ch}: ", row_widget)
            
            self.controls["action"] = self._add_row(layout, "Действие: ", self._combo(["play", "stop", "queue"], props.get("action", "play"), key_name="action"))
            self.controls["volume"] = self._add_row(layout, "Громкость: ", self._slider(props.get("volume", 0.8), "volume"))
            
            if ch == "music":
                self.controls["fadein"] = self._add_row(layout, "Fade In: ", self._spin(props.get("fadein", 1.0), 0.0, 5.0, 0.1, "fadein"))
                self.controls["loop"] = self._add_row(layout, "Зациклить: ", self._checkbox(props.get("loop", True), "loop"))
            else:
                self.controls["fadeout"] = self._add_row(layout, "Fade Out: ", self._spin(props.get("fadeout", 0.0), 0.0, 5.0, 0.1, "fadeout"))

        elif self.block_type == "Анимация спрайта":
            self.controls["character"] = self._add_row(layout, "Персонаж: ", self._combo(chars, props.get("character"), key_name="character"))
            
            sprite_combo = QComboBox()
            sprite_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            
            init_char = props.get("character", "Мысли")
            sprites = self._get_character_sprites(init_char)
            sprite_combo.addItems(sprites)
            
            if props.get("sprite_name") in sprites:
                sprite_combo.setCurrentText(props.get("sprite_name"))
            elif sprites:
                sprite_combo.setCurrentIndex(0)
            
            sprite_combo.currentTextChanged.connect(lambda t: self._prop_change("sprite_name", t))
            self.controls["sprite_name"] = self._add_row(layout, "Спрайт: ", sprite_combo)
            
            char_combo = self.controls["character"]
            char_combo.currentTextChanged.connect(lambda c: self._update_sprite_dropdown_for_character(c))
            
            self.controls["anim_type"] = self._add_row(layout, "Тип движения: ", 
                self._combo(["move", "ease", "linear", "zoom"], props.get("anim_type", "move"), key_name="anim_type"))
            
            self.controls["duration"] = self._add_row(layout, "Длительность (с): ", 
                self._spin(props.get("duration", 1.0), 0.1, 10.0, 0.1, "duration"))
            
            self.controls["start_x"] = self._add_row(layout, "Начало X: ", 
                self._slider(props.get("start_x", 0.2), "start_x"))
            
            self.controls["end_x"] = self._add_row(layout, "Конец X: ", 
                self._slider(props.get("end_x", 0.8), "end_x"))
            
            self.controls["easing"] = self._add_row(layout, "Сглаживание: ", 
                self._combo(["linear", "easein", "easeout", "easeinout"], props.get("easing", "linear"), key_name="easing"))

    def _rebuild_choice_ui(self, layout, choices):
        """Перерисовывает список вариантов внутри блока"""
        for row in self.choice_rows:
            row.deleteLater()
        self.choice_rows.clear()
        
        for i, ch in enumerate(choices):
            row = QWidget()
            row.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 4px; padding: 2px;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 2, 6, 2)
            rl.setSpacing(8)
            
            port_dot = QLabel("●")
            port_dot.setStyleSheet("color: #F59E0B; font-size: 10px;")
            port_dot.setToolTip(f"Выход #{i+1}")
            rl.addWidget(port_dot)
            
            # Текст варианта
            txt_lbl = QLabel(ch.get("text", "Вариант")[:20])
            txt_lbl.setStyleSheet("color: #E2E8F0; font-size: 11px;")
            txt_lbl.setWordWrap(True)
            rl.addWidget(txt_lbl, 1)
            
            # Цель перехода
            target_lbl = QLabel(f"→ {ch.get('target', '?')}")
            target_lbl.setStyleSheet("color: #94A3B8; font-size: 10px;")
            rl.addWidget(target_lbl)
            
            layout.addWidget(row)
            self.choice_rows.append(row)

    def update_choice_display(self):
        """Вызывается при изменении свойств из панели"""
        if self.block_type != "Выбор ответа": return
        choices = self._props.get("choices", [])
        layout = self.controls.get("choice_layout")
        if layout:
            self._rebuild_choice_ui(layout, choices)
        self._setup_ports(self._props)
        self._update_port_positions()
        self.update()

    def _toggle_audio_play(self, filename):
        """Воспроизводит или останавливает аудиофайл"""
        from pathlib import Path
        
        if not filename or not self.scene_ref.parent_window:
            return
        
        clean_filename = Path(str(filename)).name
        
        if 'name' in self.controls:
            widget = self.controls['name']
            if isinstance(widget, QLineEdit):
                if widget.text() != clean_filename:
                    widget.setText(clean_filename)
            else:
                for w in widget.findChildren(QLineEdit):
                    if w.text() != clean_filename:
                        w.setText(clean_filename)
                        break

        pm = self.scene_ref.parent_window.project_manager
        if not pm.is_project_open:
            QMessageBox.warning(None, "Ошибка", "Проект не открыт")
            return
            
        audio_base = pm.game_path / "audio"
        possible_paths = [
            audio_base / "music" / clean_filename,
            audio_base / "sound" / clean_filename,
            audio_base / clean_filename,
            pm.game_path / "images" / "audio" / clean_filename
        ]
        
        audio_path = None
        for p in possible_paths:
            if p.exists():
                audio_path = p
                break
        
        if not audio_path:
            QMessageBox.warning(None, "Ошибка", f"Файл не найден:\n{clean_filename}\n\nПроверьте, что файл лежит в 'game/audio/music' или 'game/audio/sound'.")
            return

        if self.audio_player is None:
            self.audio_output = QAudioOutput()
            self.audio_player = QMediaPlayer()
            self.audio_player.setAudioOutput(self.audio_output)
            self.audio_player.mediaStatusChanged.connect(self._on_media_status_changed)

        if self.audio_player.playbackState() == QMediaPlayer.PlayingState:
            self.audio_player.stop()
            if self.play_btn: self.play_btn.setText("▶")
        else:
            self.audio_player.setSource(QUrl.fromLocalFile(str(audio_path)))
            self.audio_player.play()
            if self.play_btn: self.play_btn.setText("⏹")

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia or status == QMediaPlayer.StoppedState:
            if self.play_btn:
                self.play_btn.setText("▶")

    def _update_image_preview(self):
        """Показывает картинку ТОЛЬКО для Спрайтов и Фонов"""
        if not hasattr(self, 'image_preview_label'):
            return

        if self.block_type not in ['Спрайт', 'Задний фон']:
            self.image_preview_label.hide()
            return

        filename = None
        if self.block_type == 'Спрайт':
            filename = self._props.get('sprite_name')
        elif self.block_type == 'Задний фон':
            filename = self._props.get('bg_name')

        if not filename or not self.scene_ref or not self.scene_ref.parent_window:
            self.image_preview_label.hide()
            return

        pm = self.scene_ref.parent_window.project_manager
        if not pm.is_project_open:
            self.image_preview_label.hide()
            return

        images_path = pm.game_path / "images"
        
        possible_paths = []
        
        if self.block_type == 'Спрайт':
            char_name = self._props.get('character')
            if char_name and char_name != "Мысли":
                possible_paths.append(images_path / "characters" / char_name / filename)
            
            possible_paths.append(images_path / "characters" / filename)
            
            possible_paths.append(images_path / filename)

        elif self.block_type == 'Задний фон':
            possible_paths.append(images_path / "backgrounds" / filename)
            possible_paths.append(images_path / filename)

        file_path = None
        for p in possible_paths:
            if p.exists():
                file_path = p
                break
        
        if file_path:
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    self.image_preview_label.width() - 10, 
                    self.image_preview_label.height() - 10,
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.image_preview_label.setPixmap(scaled_pixmap)
                self.image_preview_label.show()
            else:
                self.image_preview_label.hide()
        else:
            self.image_preview_label.hide()

    def _add_row(self, layout, label_text, widget):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 2, 0, 2)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {theme.color('text_secondary')}; font-size: 12px; min-width: 80px;")
        rl.addWidget(lbl)
        rl.addWidget(widget, 1)
        layout.addWidget(row)
        return widget

    def _combo(self, items, current, key_name=None):
        w = QComboBox()
        w.addItems(items)
        if current in items: 
            w.setCurrentText(current)
        
        if key_name:
            w.setObjectName(key_name)
            
        def on_change(t):
            key = w.objectName() or key_name or "temp"
            self._prop_change(key, t)
            
        w.currentTextChanged.connect(on_change)
        return w

    def _line_edit(self, text, key):
        w = FocusableLineEdit(text)
        w.setObjectName(key)
        w.setMaxLength(200)
        w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        w.setMinimumWidth(100)
        w.textChanged.connect(lambda t: self._prop_change(key, t))
        return w

    def _checkbox(self, checked, key):
        w = QCheckBox()
        w.setChecked(checked)
        w.toggled.connect(lambda c: self._prop_change(key, c))
        return w

    def _slider(self, value, key):
        w = QSlider(Qt.Horizontal)
        w.setRange(0, 100)
        w.setValue(int(value * 100))
        w.valueChanged.connect(lambda v: self._prop_change(key, v/100.0))
        return w

    def _spin(self, value, mn, mx, step, key):
        w = QSpinBox()
        w.setRange(int(mn/step), int(mx/step))
        w.setValue(int(value/step))
        w.setSingleStep(1)
        w.setSuffix(f" ({step})")
        w.valueChanged.connect(lambda v: self._prop_change(key, v*step))
        return w

    def _prop_change(self, key, value):
        validated_value = value
        
        if self.block_type == "Спрайт":
            if key == "sprite_name":
                if not str(value).strip():
                    pass 
            
            if key == "zoom":
                try:
                    z = float(value)
                    if z < 0.1: validated_value = 0.1
                    if z > 5.0: validated_value = 5.0
                except:
                    pass

        elif self.block_type == "Текст":
            if key == "text":
                if not str(value).strip():
                    pass

        old_value = self._props.get(key)
        self._props[key] = validated_value
        
        self._update_summary()
        self.update()
        
        if self.isSelected() and self.scene_ref and self.scene_ref.parent_window:
            main_window = self.scene_ref.parent_window
            prop_dock = getattr(main_window, 'prop_dock_widget', None)
            if prop_dock and prop_dock.current_block is self:
                prop_dock.update_property_value(key, validated_value)
                
        self._validate_block_integrity()
        if self.scene_ref:
            self.scene_ref.notify_code_change()

    def _validate_block_integrity(self):
        """Проверяет блок на критические ошибки и подсвечивает поля"""
        props = self._props
        
        if self.block_type == "Спрайт":
            sprite_name = props.get("sprite_name", "")
            if "sprite_name" in self.controls:
                widget = self.controls["sprite_name"]
                has_error = not str(sprite_name).strip()
                self.set_field_error(widget, has_error)
                
        elif self.block_type == "Текст":
            text_val = props.get("text", "")
            if "text" in self.controls:
                widget = self.controls["text"]
                has_error = not str(text_val).strip()
                self.set_field_error(widget, has_error) 

    def _update_summary(self):
        p = self._props
        if self.block_type == "Текст":
            txt = f"{p.get('character', '')}: {str(p.get('text', ''))[:35]}" + ("..." if len(p.get('text', '')) > 35 else "")
        elif self.block_type == "Выбор ответа":
            txt = f"🔀 Выбор ({len(p.get('choices', []))} вар.)"
        elif self.block_type == "Спрайт":
            txt = f"{'🟢' if p.get('action')=='show' else '🔴'} {p.get('sprite_name', '???')} @ {p.get('position', 'center')}"
        elif self.block_type == "Задний фон":
            txt = f"🖼️ {p.get('bg_name', '???')} ({'scene' if p.get('clear_layer', True) else 'show bg'})"
        elif self.block_type in ["Музыка", "Звук"]:
            import os
            name = p.get('name', '???')
            if name and name != '???':
                name = os.path.basename(name)
            txt = f"{'▶️' if p.get('action')=='play' else '⏹️'} {name}"
        else:
            txt = f"🎬 {p.get('anim_type', 'move')} {p.get('duration', 1)}s"
        
        if hasattr(self, 'summary_label'):
            self.summary_label.setText(txt)
        
        self._update_image_preview()

    def update_geometry(self):
        if not self.scene(): return

        if hasattr(self, 'summary_label'): self.summary_label.setVisible(not self.collapsed)
        if hasattr(self, 'controls_container'): self.controls_container.setVisible(not self.collapsed)
        
        if hasattr(self, 'image_preview_label'):
            should_show_img = (not self.collapsed) and (self.block_type in ['Спрайт', 'Задний фон'])
            self.image_preview_label.setVisible(should_show_img)

        self.ui_widget.setMaximumWidth(260) 
        self.ui_widget.setMinimumSize(0, 0)
        self.ui_widget.setMaximumSize(16777215, 16777215)

        if self.collapsed:
            w, h = 260, 40
        else:
            self.ui_widget.layout().activate()
            self.ui_widget.adjustSize()
            w = 260 
            h = self.ui_widget.height()
            self.expanded_height = h

        self.prepareGeometryChange()
        self.setRect(0, 0, w, h)
        self.proxy.resize(w, h)
        self.proxy.updateGeometry()

        self._update_port_positions()
        self.update()
        self.scene().update()

    def get_properties(self):
        return dict(self._props)

    def update_properties(self, new_props):
        self._props.update(new_props)
        
        if not self.collapsed:
            self.controls_container.deleteLater()
            self.controls_container = QWidget()
            self.controls_layout = QVBoxLayout(self.controls_container)
            self.controls_layout.setContentsMargins(4, 4, 4, 4)
            self.controls_layout.setSpacing(6)
            self.main_layout.insertWidget(1, self.controls_container)
            self._setup_controls(self.controls_layout, self._props)
        
        self._update_summary() 
        self.update()

    def serialize(self):
        return {
            "type": self.block_type,
            "x": self.x(),
            "y": self.y(),
            "block_id": self.block_id,
            "properties": self.get_properties()
        }

    def contextMenuEvent(self, event):
        menu = QMenu()
        if self.collapsed:
            menu.addAction("📮 Развернуть блок", self.toggle_collapsed)
        else:
            menu.addAction("📭 Свернуть блок", self.toggle_collapsed)
        
        menu.addSeparator()
        menu.addAction("🗑️ Удалить", lambda: self.scene_ref.remove_block(self))
        
        other_blocks = [b for b in self.scene_ref.items() if isinstance(b, BlockWidget) and b != self]
        if other_blocks:
            menu.addSeparator()
            menu.addAction("📭 Свернуть все блоки", self._collapse_all_in_scene)
            menu.addAction("📮 Развернуть все блоки", self._expand_all_in_scene)
        
        menu.exec(event.screenPos())

    def _collapse_all_in_scene(self):
        for item in self.scene_ref.items():
            if isinstance(item, BlockWidget) and not item.collapsed:
                item.toggle_collapsed()

    def _expand_all_in_scene(self):
        for item in self.scene_ref.items():
            if isinstance(item, BlockWidget) and item.collapsed:
                item.toggle_collapsed()

    def mousePressEvent(self, event):
        self._drag_start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.scene() and self.scene().grid_enabled:
            from PySide6.QtWidgets import QApplication
            if QApplication.keyboardModifiers() & Qt.ShiftModifier:
                self._check_canvas_expansion()
                return
            x, y = self.scene().snap_pos(self.pos().x(), self.pos().y())
            self.setPos(x, y)
        self._check_canvas_expansion()

    def _check_canvas_expansion(self):
        scene = self.scene()
        if not scene: return
        current_rect = scene.sceneRect()
        block_rect = self.sceneBoundingRect()
        if not current_rect.contains(block_rect.adjusted(-50, -50, 50, 50)):
            scene.update_scene_rect_to_content()

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            if getattr(self, 'group_ref', None) and not self.scene()._is_restoring:
                return value
            if self.scene() and getattr(self.scene(), 'grid_enabled', False):
                if not (QApplication.keyboardModifiers() & Qt.ShiftModifier):
                    x, y = self.scene().snap_pos(value.x(), value.y())
                    return QPointF(x, y)
            return value
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            if self.scene():
                self.scene().update_connections_for_block(self)
                self._check_group_intersection()
        elif change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            if self.scene():
                extra = 8
                dirty_rect = self.boundingRect().adjusted(-extra, -extra, extra, extra)
                self.scene().update(self.mapToScene(dirty_rect).boundingRect())
        return super().itemChange(change, value)

    def _check_group_intersection(self):
        if self.scene() and getattr(self.scene(), '_is_restoring', False): return
        if not self.scene() or not hasattr(self.scene(), 'groups'): return
        block_rect = self.sceneBoundingRect()
        block_center = block_rect.center()
        found_group = None
        for group in self.scene().groups:
            if group.sceneBoundingRect().contains(block_center):
                found_group = group
                break
        if found_group and found_group != self.group_ref:
            if self.group_ref: self.group_ref.remove_block(self)
            found_group.add_block(self)
            self.setSelected(False)
        elif not found_group and self.group_ref:
            intersects = any(g.sceneBoundingRect().intersects(block_rect) for g in self.scene().groups)
            if not intersects:
                self.group_ref.remove_block(self)
                self.setSelected(False)

    def _get_character_sprites(self, char_name):
        """Сканирует папку персонажа и возвращает список картинок"""
        if not self.scene_ref or not self.scene_ref.parent_window:
            return []
        
        pm = self.scene_ref.parent_window.project_manager
        if not pm.is_project_open:
            return []

        base_dir = pm.game_path / "images" / "characters"
        
        if char_name == "Мысли":
            target_dir = base_dir
        else:
            target_dir = base_dir / char_name

        if not target_dir.exists():
            return []

        allowed_exts = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
        try:
            sprites = [f.name for f in target_dir.iterdir() 
                       if f.is_file() and f.suffix.lower() in allowed_exts]
            return sorted(sprites)
        except PermissionError:
            return []

    def _update_sprite_dropdown_for_character(self, char_name):
        """Обновляет дропбокс спрайтов при смене персонажа"""
        if "sprite_name" not in self.controls:
            return
        
        sprite_combo = self.controls["sprite_name"]
        if not isinstance(sprite_combo, QComboBox):
            return

        current_sprite = sprite_combo.currentText()
        new_sprites = self._get_character_sprites(char_name)
        
        sprite_combo.blockSignals(True)
        sprite_combo.clear()
        sprite_combo.addItems(new_sprites)
        
        if current_sprite in new_sprites:
            sprite_combo.setCurrentText(current_sprite)
        elif new_sprites:
            sprite_combo.setCurrentIndex(0)
            
        sprite_combo.blockSignals(False)
        if sprite_combo.currentText():
             self._prop_change("sprite_name", sprite_combo.currentText())

    def mouseReleaseEvent(self, event):
        old_pos = self.pos()
        super().mouseReleaseEvent(event)
        if self.pos() != old_pos:
            from core.commands import BlockMoveCommand
            self.scene().undo_stack.push(BlockMoveCommand(self, old_pos, self.pos()))
            if self.scene() and hasattr(self.scene(), 'update_scene_rect_to_content'):
                self.scene().update_scene_rect_to_content()
                QTimer.singleShot(50, self.scene().update_scene_rect_to_content)

    def refresh_theme(self):
        c = theme.get()
        style = BLOCK_STYLES.get(self.block_type, {"color": c['primary'], "icon": "🔹"})
        self.setBrush(QBrush(QColor(c['bg_surface'])))
        self.setPen(QPen(Qt.transparent))
        if hasattr(self, 'header'):
            self.header.setStyleSheet(f"background: {style['color']}; border-radius: 8px 8px 0 0; padding: 4px;")
        if hasattr(self, 'title_label'):
            self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 13px;")
        if hasattr(self, 'summary_label'):
            self.summary_label.setStyleSheet(f"color: {c['block_preview_text']}; font-size: 11px; padding: 6px 8px; background: {c['bg_input']}; border-radius: 4px;")
        if hasattr(self, 'ui_widget'):
            for widget in self.ui_widget.findChildren(QWidget):
                widget.style().unpolish(widget)
                widget.style().polish(widget)
            self.ui_widget.style().unpolish(self.ui_widget)
            self.ui_widget.style().polish(self.ui_widget)
        for port_list in self.ports.values():
            for port in port_list:
                if hasattr(port, '_update_colors'):
                    port._update_colors()
        self.update()
        if self.scene():
            self.scene().update()

    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setBrush(self.brush())
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(self.boundingRect(), 8, 8)
        if self.isSelected():
            c = theme.get()
            pen = QPen(QColor(c['primary']), 2.5, Qt.DashLine)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            rect = self.boundingRect().adjusted(0, 0, 0, 0)
            painter.drawRoundedRect(rect, 8, 8)
        painter.restore()
 
    def update_from_file(self, filepath):
        import os, shutil
        from pathlib import Path
        
        src = Path(filepath)
        if not src.exists():
            return
            
        filename = src.name
        ext = src.suffix.lower()
        is_image = ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']
        is_audio = ext in ['.mp3', '.ogg', '.wav']
        
        if not is_image and not is_audio:
            return
        
        if not self.scene_ref or not self.scene_ref.parent_window:
            return
        pm = self.scene_ref.parent_window.project_manager
        if not pm.is_project_open:
            return
        
        target_dir = None
        if self.block_type == "Спрайт" and is_image:
            char_name = self._props.get("character", "").strip()
            if char_name and char_name != "Мысли":
                target_dir = pm.game_path / "images" / "characters" / char_name
            else:
                target_dir = pm.game_path / "images" / "characters"
        elif self.block_type == "Задний фон" and is_image:
            target_dir = pm.game_path / "images" / "backgrounds"
        elif self.block_type == "Музыка" and is_audio:
            target_dir = pm.game_path / "audio" / "music"
        elif self.block_type == "Звук" and is_audio:
            target_dir = pm.game_path / "audio" / "sound"
        else:
            self._set_filename_property(filename)
            return
        
        if not target_dir:
            self._set_filename_property(filename)
            return
            
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / filename
        
        if dest.exists():
            base = src.stem
            suffix = src.suffix
            counter = 1
            while dest.exists():
                new_name = f"{base}_{counter}{suffix}"
                dest = target_dir / new_name
                counter += 1
            filename = dest.name
        
        try:
            shutil.copy2(src, dest)
            self._set_filename_property(filename)
            if hasattr(self.scene_ref.parent_window, 'asset_dock'):
                self.scene_ref.parent_window.asset_dock.refresh()
        except Exception as e:
            print(f"Error copying file: {e}")
            self._set_filename_property(filename)

    def _set_filename_property(self, filename):
        """Устанавливает имя файла в соответствующее свойство блока и обновляет UI"""
        from pathlib import Path
        
        clean_filename = Path(str(filename)).name
        
        if 'sprite_name' in self._props:
            self._props['sprite_name'] = clean_filename
            if 'sprite_name' in self.controls:
                self.controls['sprite_name'].setText(clean_filename)
        if 'bg_name' in self._props:
            self._props['bg_name'] = clean_filename
            if 'bg_name' in self.controls:
                self.controls['bg_name'].setText(clean_filename)
        if 'name' in self._props:
            self._props['name'] = clean_filename
            if 'name' in self.controls:
                widget = self.controls['name']
                if isinstance(widget, QLineEdit):
                    widget.setText(clean_filename)
                else:
                    for line_edit in widget.findChildren(QLineEdit):
                        line_edit.setText(clean_filename)
                        break
        
        self._update_summary()
        self.update()
        
        if self.scene_ref:
            self.scene_ref.notify_code_change()

    def set_drag_highlight(self, state):
        if state:
            self.setPen(QPen(QColor("#10B981"), 3, Qt.DashLine))
            self.setZValue(20)
        else:
            self.setZValue(0)
            if self.isSelected():
                self.setPen(QPen(QColor(theme.color('primary')), 2.5, Qt.DashLine))
            else:
                self.setPen(QPen(Qt.transparent))
        self.update()

    def hoverEnterEvent(self, event):
        super().hoverEnterEvent(event)
        scene = self.scene()
        if scene and scene.show_ports_on_hover and not scene.drag_start_port:
            self.show_connection_ports(True)

    def hoverLeaveEvent(self, event):
        super().hoverLeaveEvent(event)
        self.setCursor(Qt.ArrowCursor)
        
        scene = self.scene()
        if scene and scene.show_ports_on_hover and not scene.drag_start_port:
            self.show_connection_ports(False)

    def show_connection_ports(self, show: bool):
        all_ports = self.ports.get('in', []) + self.ports.get('out', [])
        for port in all_ports:
            port.setVisible(show)
            port.update()

    def _set_ports_visible(self, visible: bool):
        all_ports = self.ports.get('in', []) + self.ports.get('out', [])
        for port in all_ports:
            port.setVisible(visible)
            port.update()

    def toggle_collapsed(self):
        self.collapsed = not self.collapsed
        self._props["collapsed"] = self.collapsed
        self.collapse_btn.setText("▾" if self.collapsed else "▴")
        
        if not self.collapsed:
            self.controls_container.deleteLater()
            self.controls_container = QWidget()
            self.controls_layout = QVBoxLayout(self.controls_container)
            self.controls_layout.setContentsMargins(4, 4, 4, 4)
            self.controls_layout.setSpacing(6)
            self.main_layout.insertWidget(1, self.controls_container)
            self._setup_controls(self.controls_layout, self._props)
        
        if hasattr(self, 'summary_label'): 
            self.summary_label.setVisible(not self.collapsed)
        if hasattr(self, 'controls_container'): 
            self.controls_container.setVisible(not self.collapsed)
        
        if hasattr(self, 'image_preview_label'):
            should_show = (not self.collapsed) and (self.block_type in ['Спрайт', 'Задний фон'])
            self.image_preview_label.setVisible(should_show)

        self.ui_widget.layout().invalidate()
        self.ui_widget.adjustSize()
        self.prepareGeometryChange()
        
        if self.collapsed:
            w, h = 260, 36
        else:
            w = 260
            h = self.ui_widget.height()
            self.expanded_height = h

        self.setRect(0, 0, w, h) 
        self.proxy.resize(w, h)
        self.proxy.updateGeometry()
        
        self._update_port_positions()
        if self.scene():
            self.scene().update_connections_for_block(self)
            self.scene().update()

    def set_collapsed_state(self, is_collapsed: bool):
        if getattr(self, 'collapsed', False) == is_collapsed:
            return
        self.toggle_collapsed()

    def __del__(self):
        if self.audio_player:
            self.audio_player.stop()
            self.audio_player.deleteLater()

    def set_field_error(self, widget, has_error):
        """Подсвечивает виджет красным, если есть ошибка"""
        if has_error:
            widget.setStyleSheet("border: 1px solid #EF4444; background-color: rgba(239, 68, 68, 0.1); border-radius: 4px;")
        else:
            c = theme.get()
            widget.setStyleSheet(f"background-color: {c['bg_input']}; border: 1px solid {c['border']}; border-radius: 4px;")