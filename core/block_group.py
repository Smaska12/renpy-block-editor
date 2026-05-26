import uuid
from PySide6.QtWidgets import QGraphicsRectItem, QGraphicsTextItem, QInputDialog, QMenu, QColorDialog, QApplication
from PySide6.QtGui import QColor, QPen, QBrush, QFont, QCursor
from PySide6.QtCore import Qt, QPointF, QRectF
from core.theme_manager import theme

class BlockGroup(QGraphicsRectItem):
    def __init__(self, scene, blocks, title="Группа", group_id=None):
        super().__init__()
        self.scene_ref = scene
        self.blocks = blocks
        self.title_text = title
        self.group_id = group_id

        self.is_resizing = False
        self.resize_handle = None
        self.resize_start_pos = None
        self.resize_start_rect = None

        c = theme.get()
        self.setPen(QPen(QColor(c['border_light']), 2, Qt.DashLine))
        bg_color = QColor(c['primary'])
        bg_color.setAlpha(30)
        self.setBrush(QBrush(bg_color))

        self.setZValue(-1)
        self.setFlag(QGraphicsRectItem.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsRectItem.ItemSendsScenePositionChanges, True)
        self.setAcceptHoverEvents(True)

        self.title_item = QGraphicsTextItem(self)
        self.title_item.setPlainText(title)
        self.title_item.setDefaultTextColor(QColor(c['text_main']))
        font = QFont()
        font.setBold(True)
        font.setPixelSize(18)
        self.title_item.setFont(font)

        self._update_bounds()

    def _update_bounds(self):
        if not self.blocks: return

        rect = self.blocks[0].sceneBoundingRect()
        for b in self.blocks[1:]:
            rect = rect.united(b.sceneBoundingRect())

        padding = 40
        new_scene_rect = rect.adjusted(-padding, -padding + 20, padding, padding)

        local_top_left = self.mapFromScene(new_scene_rect.topLeft())
        self.setRect(local_top_left.x(), local_top_left.y(), new_scene_rect.width(), new_scene_rect.height())

        self.title_item.setPos(local_top_left.x() + 10, local_top_left.y() - 15)

    def _get_resize_handle(self, pos):
        rect = self.rect()
        handle_size = 12
        corners = {
            'top_left': QRectF(rect.left() - handle_size, rect.top() - handle_size, handle_size * 2, handle_size * 2),
            'top_right': QRectF(rect.right() - handle_size, rect.top() - handle_size, handle_size * 2, handle_size * 2),
            'bottom_left': QRectF(rect.left() - handle_size, rect.bottom() - handle_size, handle_size * 2, handle_size * 2),
            'bottom_right': QRectF(rect.right() - handle_size, rect.bottom() - handle_size, handle_size * 2, handle_size * 2),
        }
        sides = {
            'top': QRectF(rect.left(), rect.top() - handle_size, rect.width(), handle_size * 2),
            'bottom': QRectF(rect.left(), rect.bottom() - handle_size, rect.width(), handle_size * 2),
            'left': QRectF(rect.left() - handle_size, rect.top(), handle_size * 2, rect.height()),
            'right': QRectF(rect.right() - handle_size, rect.top(), handle_size * 2, rect.height()),
        }
        for name, area in {**corners, **sides}.items():
            if area.contains(pos):
                return name
        return None

    def hoverMoveEvent(self, event):
        if self.is_resizing: return
        pos = event.pos()
        handle = self._get_resize_handle(pos)
        if handle:
            if 'left' in handle or 'right' in handle: self.setCursor(QCursor(Qt.SizeHorCursor))
            elif 'top' in handle or 'bottom' in handle: self.setCursor(QCursor(Qt.SizeVerCursor))
            elif handle in ['top_left', 'bottom_right']: self.setCursor(QCursor(Qt.SizeFDiagCursor))
            elif handle in ['top_right', 'bottom_left']: self.setCursor(QCursor(Qt.SizeBDiagCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            handle = self._get_resize_handle(event.pos())
            if handle:
                self.is_resizing = True
                self.resize_handle = handle
                self.resize_start_pos = event.scenePos()
                self.resize_start_rect = self.rect()
                event.accept()
                return
            else:
                self.setSelected(True)
                
        if not self.is_resizing:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Изменяет размер группы и обновляет позицию заголовка"""
        if self.is_resizing and self.resize_handle:
            delta = event.scenePos() - self.resize_start_pos
            new_rect = QRectF(self.resize_start_rect)
            
            if 'left' in self.resize_handle: new_rect.setLeft(new_rect.left() + delta.x())
            if 'right' in self.resize_handle: new_rect.setRight(new_rect.right() + delta.x())
            if 'top' in self.resize_handle: new_rect.setTop(new_rect.top() + delta.y())
            if 'bottom' in self.resize_handle: new_rect.setBottom(new_rect.bottom() + delta.y())
            
            if new_rect.width() < 150: new_rect.setWidth(150)
            if new_rect.height() < 80: new_rect.setHeight(80)
            
            self.setRect(new_rect)
            self.title_item.setPos(new_rect.left() + 10, new_rect.top() - 15)
            event.accept()
            return
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_resizing:
            self.is_resizing = False
            self.resize_handle = None
            self.setCursor(QCursor(Qt.ArrowCursor))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionChange:
            if self.blocks:
                proposed_pos = value
                current_pos = self.pos()
                if self.scene_ref and self.scene_ref.grid_enabled:
                    if not (QApplication.keyboardModifiers() & Qt.ShiftModifier):
                        snapped_x, snapped_y = self.scene_ref.snap_pos(proposed_pos.x(), proposed_pos.y())
                        proposed_pos = QPointF(snapped_x, snapped_y)

                delta = proposed_pos - current_pos
                for block in self.blocks:
                    if getattr(block, 'group_ref', None) == self:
                        block.setPos(block.pos() + delta)
                        if self.scene_ref:
                            self.scene_ref.update_connections_for_block(block)
                return proposed_pos
        return super().itemChange(change, value)

    def contextMenuEvent(self, event):
        menu = QMenu()
        menu.addAction("✏️ Переименовать", self._rename_group)
        menu.addAction("🎨 Изменить цвет", self._change_color)
        menu.addSeparator()
        menu.addAction("📦 Разгруппировать", self.ungroup)
        menu.addSeparator()
        menu.addAction("🗑️ Удалить группу", self.delete_group)
        menu.exec(event.screenPos())

    def delete_group(self):
        """Полностью удаляет группу (но оставляет блоки)"""
        for b in self.blocks:
            b.group_ref = None
        if self.scene_ref and self in self.scene_ref.groups:
            self.scene_ref.groups.remove(self)
        if self.scene():
            self.scene().removeItem(self)

    def _rename_group(self):
        new_name, ok = QInputDialog.getText(None, "Переименовать", "Новое имя:", text=self.title_text)
        if ok and new_name.strip():
            self.title_text = new_name.strip()
            self.title_item.setPlainText(new_name.strip())

    def _change_color(self):
        current_color = self.pen().color()
        color = QColorDialog.getColor(current_color, None, "Цвет группы")
        if color.isValid():
            self.setPen(QPen(color, 2, Qt.DashLine))
            bg = QColor(color)
            bg.setAlpha(30)
            self.setBrush(QBrush(bg))

    def ungroup(self):
        for b in self.blocks: b.group_ref = None
        if self.scene_ref and self in self.scene_ref.groups:
            self.scene_ref.groups.remove(self)
        if self.scene():
            self.scene().removeItem(self)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._rename_group()
        super().mouseDoubleClickEvent(event)

    def remove_block(self, block):
        if block in self.blocks:
            self.blocks.remove(block)
            block.group_ref = None
            if not self.blocks: self.ungroup()

    def add_block(self, block):
        if block not in self.blocks:
            self.blocks.append(block)
            block.group_ref = self

    def serialize(self):
        return {
            "group_id": getattr(self, "group_id", str(uuid.uuid4())),
            "title": self.title_text, 
            "color": self.pen().color().name(),  
            "block_ids": [b.block_id for b in getattr(self, "blocks", [])]
        }