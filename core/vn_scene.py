from PySide6.QtWidgets import QGraphicsScene, QGraphicsPathItem, QApplication, QLineEdit, QPlainTextEdit, QTextEdit
from PySide6.QtGui import QColor, QBrush, QTransform, QPen, QPainterPath, QUndoStack
from PySide6.QtCore import Qt, QLineF, Signal, QPointF, QTimer, QRectF
from .block_widget import BlockWidget
from .connection_system import PortItem, ConnectionEdge
from .block_group import BlockGroup
from core.theme_manager import theme

class VNScene(QGraphicsScene):
    mouseMoved = Signal(float, float)
    codeChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 5000, 5000)
        self.setBackgroundBrush(QBrush(QColor("#0F172A")))
        self.labels = {"start": []}
        self.current_label = "start"
        self.characters = {"Мысли": {"color": "#808080"}}
        self.parent_window = None

        self.grid_enabled = True
        self.grid_size = 25
        self.show_ports = True
        self.show_ports_on_hover = True
        self.undo_stack = QUndoStack(self)
        self.undo_stack.setUndoLimit(60)
        self.clipboard = []

        self.connections = []
        self.label_connections = {}
        self.groups = []
        self._pending_groups = []
        self._pending_connections = []
        self.temp_edge = None
        self.drag_start_port = None
        self._highlighted_port = None
        
        self._is_restoring = False
        self.default_block_collapsed = False

        self._code_update_timer = QTimer(self)
        self._code_update_timer.setSingleShot(True)
        self._code_update_timer.timeout.connect(self._emit_code)

    def toggle_grid(self):
        self.grid_enabled = not self.grid_enabled
        if self.parent_window and hasattr(self.parent_window, 'view'):
            self.parent_window.view.viewport().update()

    def snap_pos(self, x, y, threshold=15):
        if not self.grid_enabled:
            return x, y
        snapped_x = round(x / self.grid_size) * self.grid_size
        snapped_y = round(y / self.grid_size) * self.grid_size
        dist_x = abs(x - snapped_x)
        dist_y = abs(y - snapped_y)
        if dist_x < threshold: x = snapped_x
        if dist_y < threshold: y = snapped_y
        return x, y

    def undo(self): self.undo_stack.undo()
    def redo(self): self.undo_stack.redo()
    def clear_undo(self): self.undo_stack.clear()

    def _get_block_by_id(self, block_id: str):
        return next((b for b in self.items() if hasattr(b, 'block_id') and b.block_id == block_id), None)

    def copy_selected(self):
        self.clipboard = [b.serialize() for b in self.items() if isinstance(b, BlockWidget) and b.isSelected()]
        if self.parent_window and hasattr(self.parent_window, 'statusBar'):
            self.parent_window.statusBar().showMessage(f"Скопировано блоков: {len(self.clipboard)}")

    def paste_blocks(self):
        if not self.clipboard: return
        offset = 30
        for data in self.clipboard:
            new_data = {
                "type": data["type"],
                "x": data["x"] + offset,
                "y": data["y"] + offset,
                "properties": dict(data["properties"])
            }
            if "block_id" in new_data["properties"]:
                import uuid
                new_data["properties"]["block_id"] = str(uuid.uuid4())
            self.add_block(new_data["type"], new_data)

    def mousePressEvent(self, event):
        if not self.itemAt(event.scenePos(), QTransform()):
            for item in self.items():
                if isinstance(item, BlockWidget):
                    item.setSelected(False)
        super().mousePressEvent(event)

    def add_label(self, name):
        if name and name not in self.labels:
            self.labels[name] = []
            return True
        return False

    def switch_label(self, name, skip_sync=False):
        if name not in self.labels: return
        if not skip_sync: self._sync_current_label()
        
        old_connections = list(self.connections)
        
        self.clear()
        self.connections = []
        self.current_label = name
        blocks_data = self.labels.get(name, [])
        self.labels[self.current_label] = []
        
        for data in blocks_data:
            self.add_block(data.get("type", "Текст"), data)
        
        self.restore_groups()
        
        if self._pending_connections:
            current_block_ids = {b.block_id for b in self.get_current_blocks()}
            relevant_connections = [
                c for c in self._pending_connections 
                if c.get("source_id") in current_block_ids and c.get("target_id") in current_block_ids
            ]
            
            for conn in relevant_connections:
                src = self._get_block_by_id(conn.get("source_id"))
                tgt = self._get_block_by_id(conn.get("target_id"))
                if src and tgt:
                    s_idx = conn.get("source_idx", 0)
                    t_idx = conn.get("target_idx", 0)
                    if s_idx < len(src.ports['out']) and t_idx < len(tgt.ports['in']):
                        self._create_connection_edge(src.ports['out'][s_idx], tgt.ports['in'][t_idx])
        
        QTimer.singleShot(50, self._finish_label_switch)

    def _finish_label_switch(self):
        """Вызывается после загрузки лейбла для финализации"""
        self.update_scene_rect_to_content()
        self.update_all_connections() 
        if self.parent_window and hasattr(self.parent_window, 'view'):
            pass

    def update_all_connections(self):
        """Обновляет визуальное отображение всех связей"""
        for conn in self.connections:
            edge = conn.get("edge_ref")
            if edge:
                edge.update_path()

    def _pack_and_fit_after_load(self):
        self.pack_label_compact()
        self.update_scene_rect_to_content()
        if self.parent_window and hasattr(self.parent_window, 'view'):
            self.parent_window.view.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def pack_label_compact(self):
        """Выстраивает блоки в плотную колонку"""
        blocks = self.get_current_blocks()
        if not blocks: return
        
        blocks.sort(key=lambda b: b.y())
        current_y = 20  
        gap = 10        
        
        self._is_restoring = True
        for block in blocks:
            block.setPos(block.x(), current_y)
            block_height = block.boundingRect().height()
            current_y += block_height + gap
        self._is_restoring = False
        
        self.update_scene_rect_to_content()

    def update_scene_rect_to_content(self):
        blocks = self.get_current_blocks()
        if not blocks:
            self.setSceneRect(0, 0, 800, 600)
            return

        for block in blocks:
            if hasattr(block, 'update_geometry'):
                block.update_geometry()
            else:
                block.prepareGeometryChange()
                block.update()

        combined_rect = blocks[0].sceneBoundingRect()
        for block in blocks[1:]:
            combined_rect = combined_rect.united(block.sceneBoundingRect())

        padding = 100
        new_rect = combined_rect.adjusted(-padding, -padding, padding, padding)

        self.setSceneRect(new_rect)

        for view in self.views():
            view.viewport().update()
            view.update()

        self.invalidate()

    def add_block(self, block_type, data=None):
        x = data.get("x", 50) if data else 50
        y = data.get("y", self.get_next_y()) if data else self.get_next_y()
        props = data.get("properties", {}) if data else {}
        block = BlockWidget(block_type, self, x, y, properties=props)
        if data and "block_id" in data:
            block.block_id = data["block_id"]
        elif data and "properties" in data and "block_id" in data["properties"]:
            block.block_id = data["properties"]["block_id"]
        self.addItem(block)
        if not self._is_restoring:
            self.labels[self.current_label].append(block.serialize())
        
        if not self._is_restoring:
            for group in self.groups:
                group_blocks = [b for b in group.blocks if hasattr(b, 'scene_ref') and b.scene_ref == self]
                if group_blocks:
                    group.add_block(block)
                    block.group_ref = group
                    group._update_bounds()
                    break
        
        QTimer.singleShot(0, self.update_scene_rect_to_content)
        return block

    def remove_block(self, block):
        conns_to_remove = []
        for conn in self.connections:
            edge = conn.get("edge_ref")
            if edge and (edge.source_port.parentItem() == block or edge.target_port.parentItem() == block):
                conns_to_remove.append(conn)
                if edge in self.items():
                    self.removeItem(edge)
        for conn in conns_to_remove:
            self.connections.remove(conn)
        self.labels[self.current_label] = [
            b for b in self.labels[self.current_label] 
            if b.get("block_id") != block.block_id
        ]
        self.removeItem(block)
        
        QTimer.singleShot(0, self.update_scene_rect_to_content)

    def get_next_y(self):
        blocks_data = self.labels.get(self.current_label, [])
        if not blocks_data: return 50
        max_bottom = 50
        for b_data in blocks_data:
            y = b_data.get("y", 0)
            h = 100
            if y + h > max_bottom:
                max_bottom = y + h + 15
        return max_bottom

    def get_current_blocks(self):
        return [item for item in self.items() if isinstance(item, BlockWidget)]

    def realign_blocks(self):
        y = 50
        blocks = self.get_current_blocks()
        blocks.sort(key=lambda b: b.y())
        self._is_restoring = True
        for b in blocks:
            b.setPos(b.x(), y)
            y += b.boundingRect().height() + 15
        self._is_restoring = False
        for group in self.groups:
            group._update_bounds()
        self.labels[self.current_label] = [b.serialize() for b in blocks]
        self.update_scene_rect_to_content()
        self.update()

    def smart_auto_layout(self):
        blocks = self.get_current_blocks()
        if not blocks: return
        block_map = {b.block_id: b for b in blocks}
        adjacency = {b.block_id: [] for b in blocks}
        for conn in self.connections:
            src_id = conn.get("source_id")
            tgt_id = conn.get("target_id")
            if src_id in adjacency and tgt_id in block_map:
                adjacency[src_id].append(tgt_id)
        ranks = {b.block_id: 0 for b in blocks}
        for _ in range(50):
            changed = False
            for src_id, targets in adjacency.items():
                for tgt_id in targets:
                    if ranks[tgt_id] <= ranks[src_id]:
                        ranks[tgt_id] = ranks[src_id] + 1
                        changed = True
            if not changed: break
        layers = {}
        for b_id, rank in ranks.items():
            if rank not in layers: layers[rank] = []
            layers[rank].append(block_map[b_id])
        layer_height = 140
        block_spacing_x = 220
        max_width = max((len(layer) * block_spacing_x for layer in layers.values()), default=0)
        center_x = 200 + (max_width / 2)
        self._is_restoring = True
        sorted_ranks = sorted(layers.keys())
        for rank in sorted_ranks:
            layer_blocks = layers[rank]
            layer_blocks.sort(key=lambda b: b.x())
            current_layer_width = (len(layer_blocks) - 1) * block_spacing_x
            start_x = center_x - (current_layer_width / 2)
            y_pos = 50 + (rank * layer_height)
            for i, block in enumerate(layer_blocks):
                new_x = start_x + (i * block_spacing_x)
                block.setPos(new_x, y_pos)
        self._is_restoring = False
        for group in self.groups:
            group._update_bounds()
        self.update_scene_rect_to_content()
        self.update()

    def load_project_data(self, data):
        self.clear()
        self.connections = []
        self.labels = data.get("labels", {"start": []})
        self.characters = data.get("characters", {"Мысли": {"color": "#808080"}})
        if "start" not in self.labels: self.labels["start"] = []
        self.current_label = "start"
        self._pending_connections = data.get("connections", [])
        self._pending_groups = data.get("groups", [])
        
        self.scan_character_folders()

    def _sync_current_label(self):
        if self._is_restoring: return
        if self.current_label in self.labels:
            blocks = self.get_current_blocks()
            if blocks:
                self.labels[self.current_label] = [b.serialize() for b in blocks]

    def notify_code_change(self):
        """Откладывает генерацию кода на 500мс после последнего изменения"""
        self._code_update_timer.stop()
        self._code_update_timer.start(500)

    def _emit_code(self):
        """Генерирует код и отправляет его по сигналу"""
        try:
            from code_generator import CodeGenerator
            self._sync_current_label()
            gen = CodeGenerator(self.characters, self.labels)
            script = gen.generate_full_script()
            self.codeChanged.emit(script)
        except Exception as e:
            print(f"[CodeGen Error] {e}")

    def serialize_project(self):
        self._sync_current_label()
        
        clean_connections = []
        for c in self.connections:
            clean_connections.append({
                "source_id": c["source_id"],
                "source_idx": c["source_idx"],
                "target_id": c["target_id"],
                "target_idx": c["target_idx"]
            })
        
        return {
            "characters": self.characters,
            "labels": self.labels,
            "connections": clean_connections,  
            "groups": [g.serialize() for g in self.groups]
        }

    def update_character_dropdowns(self, deleted_name=None):
        chars = list(self.characters.keys())
        default_char = "Мысли" if "Мысли" in chars else (chars[0] if chars else "")
        for item in self.items():
            if hasattr(item, 'controls') and 'character' in item.controls:
                combo = item.controls['character']
                current = combo.currentText()
                combo.clear()
                combo.addItems(chars)
                if current == deleted_name:
                    combo.setCurrentText(default_char)
                elif current in chars:
                    combo.setCurrentText(current)

    def _restore_connections_async(self):
        if not hasattr(self, '_pending_connections') or not self._pending_connections: return
        block_map = {b.block_id: b for b in self.get_current_blocks()}
        for conn in self._pending_connections:
            src = block_map.get(conn["source_id"])
            tgt = block_map.get(conn["target_id"])
            if src and tgt:
                s_idx = conn.get("source_idx", 0)
                t_idx = conn.get("target_idx", 0)
                if s_idx < len(src.ports['out']) and t_idx < len(tgt.ports['in']):
                    self._create_connection_edge(src.ports['out'][s_idx], tgt.ports['in'][t_idx])
        self._pending_connections = []

        self.update()
        if self.parent_window and hasattr(self.parent_window, 'view'):
            self.parent_window.view.viewport().update()

    def restore_groups(self):
        if not getattr(self, '_pending_groups', []): return
        block_map = {b.block_id: b for b in self.get_current_blocks()}
        for g_data in self._pending_groups:
            group_blocks = [block_map.get(bid) for bid in g_data.get("block_ids", []) if block_map.get(bid)]
            if len(group_blocks) >= 2:
                group = BlockGroup(self, group_blocks, group_id=g_data["group_id"], title=g_data.get("title", "Группа"))
                self.addItem(group)
                self.groups.append(group)
                
                if "color" in g_data:
                    color = QColor(g_data["color"])
                    group.setPen(QPen(color, 2, Qt.DashLine))
                    bg = QColor(color)
                    bg.setAlpha(30)
                    group.setBrush(QBrush(bg))
                    
        self._pending_groups = []

    def _create_connection_edge(self, source_port, target_port):
        for conn in self.connections:
            edge = conn.get("edge_ref")
            if edge and edge.source_port == source_port and edge.target_port == target_port:
                return edge
        edge = ConnectionEdge(source_port, target_port)
        self.addItem(edge)
        source_block = source_port.parentItem()
        target_block = target_port.parentItem()
        self.connections.append({
            "source_id": source_block.block_id,
            "source_idx": source_port.index,
            "target_id": target_block.block_id,
            "target_idx": target_port.index,
            "edge_ref": edge
        })
        return edge

    def update_connections_for_block(self, block):
        for conn in self.connections:
            edge = conn.get("edge_ref")
            if edge and edge.scene() == self:
                if edge.source_port and edge.source_port.parentItem() == block:
                    edge.update_path()
                elif edge.target_port and edge.target_port.parentItem() == block:
                    edge.update_path()

    def remove_connection(self, edge):
        if edge in self.items():
            self.removeItem(edge)
        self.connections = [c for c in self.connections if c.get("edge_ref") != edge]

    def start_connection_drag(self, port):
        self.drag_start_port = port
        self.temp_edge = QGraphicsPathItem()
        self.temp_edge.setPen(QPen(QColor(theme.color('edge_color')), 2, Qt.DashLine))
        self.temp_edge.setZValue(0)
        self.addItem(self.temp_edge)
        self.update_temp_edge(port.scenePos())
        for item in self.items():
            if isinstance(item, BlockWidget):
                item.show_connection_ports(True)

    def mouseMoveEvent(self, event):
        if self.temp_edge and self.drag_start_port:
            self.update_temp_edge(self.drag_start_port.scenePos(), event.scenePos())
            new_target = self._find_drop_target(event.scenePos())
            if new_target != self._highlighted_port:
                if self._highlighted_port:
                    self._highlighted_port.set_highlighted(False)
                self._highlighted_port = new_target
                if new_target:
                    new_target.set_highlighted(True)
        self.mouseMoved.emit(event.scenePos().x(), event.scenePos().y())
        super().mouseMoveEvent(event)

    def _find_drop_target(self, pos, max_dist=25.0):
        for item in self.items(pos):
            if isinstance(item, PortItem) and item.port_type == 'in':
                return item
        for item in self.items(pos):
            if isinstance(item, BlockWidget) and item.ports.get('in'):
                return item.ports['in'][0]
        best_port = None
        best_dist = max_dist
        for item in self.items():
            if isinstance(item, PortItem) and item.port_type == 'in':
                dist = QLineF(item.scenePos(), pos).length()
                if dist < best_dist:
                    best_dist = dist
                    best_port = item
        return best_port

    def mouseReleaseEvent(self, event):
        if self.temp_edge and self.drag_start_port:
            self._finalize_connection(event.scenePos())
            
        super().mouseReleaseEvent(event)

    def update_temp_edge(self, p1, p2=None):
        if not self.temp_edge: return
        path = QPainterPath(p1)
        if p2:
            dy = abs(p2.y() - p1.y())
            cp1 = QPointF(p1.x(), p1.y() + dy * 0.5)
            cp2 = QPointF(p2.x(), p2.y() - dy * 0.5)
            path.cubicTo(cp1, cp2, p2)
        else:
            path.lineTo(p1.x(), p1.y() + 50)
        self.temp_edge.setPath(path)

    def _finalize_connection(self, end_pos):
        if self.temp_edge:
            self.removeItem(self.temp_edge)
            self.temp_edge = None
        for item in self.items():
            if isinstance(item, BlockWidget):
                item.show_connection_ports(False)
        if self._highlighted_port:
            self._highlighted_port.set_highlighted(False)
            self._highlighted_port = None
        if not self.drag_start_port: return
        target_port = self._find_drop_target(end_pos)
        if target_port:
            source_block = self.drag_start_port.parentItem()
            target_block = target_port.parentItem()
            if source_block and target_block and source_block != target_block:
                self._create_connection_edge(self.drag_start_port, target_port)
                from core.commands import ConnectionCommand
                conn_data = {
                    "source_id": source_block.block_id,
                    "source_idx": self.drag_start_port.index,
                    "target_id": target_block.block_id,
                    "target_idx": target_port.index
                }
                self.undo_stack.push(ConnectionCommand(self, conn_data, is_remove=False))
        self.drag_start_port = None

    def group_selected(self):  
        selected = [i for i in self.selectedItems() if isinstance(i, BlockWidget)]
        if len(selected) < 2: return
        for b in selected:
            for g in list(self.groups):
                g.remove_block(b)
        new_group = BlockGroup(self, selected)
        self.addItem(new_group)
        self.groups.append(new_group)
        for b in selected:
            b.group_ref = new_group

    def ungroup_selected(self):
        selected = [i for i in self.selectedItems() if isinstance(i, BlockGroup)]
        for g in selected:
            g.ungroup()

    def keyPressEvent(self, event):
        from PySide6.QtWidgets import QGraphicsProxyWidget

        focus_w = QApplication.focusWidget()
        if isinstance(focus_w, (QLineEdit, QPlainTextEdit, QTextEdit)):
            super().keyPressEvent(event)
            return

        focus_item = self.focusItem()
        if focus_item and isinstance(focus_item, QGraphicsProxyWidget):
            proxy_w = focus_item.widget()
            if proxy_w and isinstance(proxy_w.focusWidget(), (QLineEdit, QPlainTextEdit, QTextEdit)):
                super().keyPressEvent(event)
                return

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            selected_edges = [i for i in self.selectedItems() if isinstance(i, ConnectionEdge)]
            for edge in selected_edges:
                conn_data = next((c for c in self.connections if c.get("edge_ref") == edge), None)
                if conn_data:
                    from core.commands import ConnectionCommand
                    self.undo_stack.push(ConnectionCommand(self, conn_data, is_remove=True))
                    self.remove_connection(edge)
            selected_blocks = [i for i in self.selectedItems() if isinstance(i, BlockWidget)]
            for block in selected_blocks:
                self.remove_block(block)
            return

        elif event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            self.copy_selected()
        elif event.key() == Qt.Key_V and event.modifiers() & Qt.ControlModifier:
            self.paste_blocks()
        elif event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            if event.modifiers() & Qt.ShiftModifier: self.redo()
            else: self.undo()
        elif event.key() == Qt.Key_G and event.modifiers() & Qt.ControlModifier:
            self.group_selected()
            return
        elif event.key() == Qt.Key_U and event.modifiers() & Qt.ControlModifier:
            self.ungroup_selected()
            return

        super().keyPressEvent(event)

    def toggle_ports(self):
        self.show_ports = not self.show_ports
        self.update_ports_visibility()

    def update_ports_visibility(self):
        for item in self.items():
            if hasattr(item, 'ports') and isinstance(item.ports, dict):
                for port_list in item.ports.values():
                    for port in port_list:
                        port.setVisible(self.show_ports)
        self.update()

    def toggle_ports_hover(self):
        self.show_ports_on_hover = not self.show_ports_on_hover
        if not self.show_ports_on_hover:
            self.hide_all_ports()

    def hide_all_ports(self):
        for item in self.items():
            if hasattr(item, 'ports'):
                for port_list in item.ports.values():
                    for port in port_list:
                        port.setVisible(False)
        self.update()

    def scan_character_folders(self):
        """Сканирует папку images/characters и добавляет персонажей"""
        if not self.parent_window or not hasattr(self.parent_window, 'project_manager'):
            return
        
        pm = self.parent_window.project_manager
        if not pm.is_project_open:
            return
        
        char_path = pm.game_path / "images" / "characters"
        if not char_path.exists():
            return
        
        for folder in char_path.iterdir():
            if folder.is_dir() and folder.name not in self.characters:
                self.characters[folder.name] = {"color": "#808080"}
        
        self.update_character_dropdowns()

    def update_character_dropdowns(self, deleted_name=None):
        chars = list(self.characters.keys())
        default_char = "Мысли" if "Мысли" in chars else (chars[0] if chars else "")
        for item in self.items():
            if hasattr(item, 'controls') and 'character' in item.controls:
                combo = item.controls['character']
                current = combo.currentText()
                combo.clear()
                combo.addItems(chars)
                if current == deleted_name:
                    combo.setCurrentText(default_char)
                elif current in chars:
                    combo.setCurrentText(current)

        if self.parent_window and hasattr(self.parent_window, 'prop_dock_widget'):
            prop_dock = self.parent_window.prop_dock_widget
            prop_dock.refresh_character_list()
