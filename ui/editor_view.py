from PySide6.QtWidgets import QGraphicsView, QApplication, QLineEdit, QComboBox, QPlainTextEdit
from PySide6.QtGui import QPainter, QKeySequence, QDragEnterEvent, QDropEvent, QDragMoveEvent, QDragLeaveEvent, QColor, QPen
from PySide6.QtCore import Qt, QPoint
from core.block_widget import BlockWidget
from core.connection_system import ConnectionEdge
from core.theme_manager import theme

class EditorView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(parent)
        self.setScene(scene)
        self.setRenderHint(QPainter.Antialiasing)
        
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        
        self.is_panning = False
        self.mouse_start_pos = QPoint()
        self._highlighted_block = None

        self._min_zoom = 0.1
        self._max_zoom = 3.0
        self._current_zoom = 1.0

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText() or event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if event.mimeData().hasUrls():
            item = self.itemAt(event.pos())
            if self._highlighted_block and self._highlighted_block != item:
                self._highlighted_block.set_drag_highlight(False)
                self._highlighted_block = None
            
            if item and isinstance(item, BlockWidget):
                item.set_drag_highlight(True)
                self._highlighted_block = item
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        if self._highlighted_block:
            self._highlighted_block.set_drag_highlight(False)
            self._highlighted_block = None
        event.accept()

    def dropEvent(self, event: QDropEvent):
        if self._highlighted_block:
            self._highlighted_block.set_drag_highlight(False)
            self._highlighted_block = None

        if event.mimeData().hasUrls():
            target = self._highlighted_block
            if not target:
                selected = [i for i in self.scene().selectedItems() if isinstance(i, BlockWidget)]
                target = selected[0] if selected else None

            if target:
                target.update_from_file(event.mimeData().urls()[0].toLocalFile())
                event.acceptProposedAction()
            return

        if event.mimeData().hasText():
            scene_pos = self.mapToScene(event.pos())
            self.scene().add_block(event.mimeData().text(), {"x": scene_pos.x(), "y": scene_pos.y()})
            event.acceptProposedAction()

    def keyPressEvent(self, event):
        focus = QApplication.focusWidget()
        if isinstance(focus, (QLineEdit, QPlainTextEdit, QComboBox)):
            super().keyPressEvent(event)
            return

        
        if event.matches(QKeySequence.Undo): 
            self.scene().undo()
        elif event.matches(QKeySequence.Redo): 
            self.scene().redo()
        elif event.matches(QKeySequence.Copy): 
            self.scene().copy_selected()
        elif event.matches(QKeySequence.Paste): 
            self.scene().paste_blocks()
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 0.85
            
            new_zoom = self._current_zoom * factor
            if new_zoom < self._min_zoom or new_zoom > self._max_zoom:
                return 
            
            self.scale(factor, factor)
            self._current_zoom = new_zoom
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and event.modifiers() & Qt.AltModifier):
            self.is_panning = True
            self.mouse_start_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.pos() - self.mouse_start_pos
            self.mouse_start_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def fit_to_content(self):
        """Автоматически масштабирует вид, чтобы влезли все блоки"""
        if not self.scene() or not self.scene().items():
            return
            
        rect = self.scene().itemsBoundingRect()
        if rect.isEmpty():
            return
            
        rect = rect.adjusted(-50, -50, 50, 50)
        
        self.resetTransform()
        self._current_zoom = 1.0
        
        self.fitInView(rect, Qt.KeepAspectRatio)
        
        transform = self.transform()
        current_scale = transform.m11()  
        
        if current_scale > self._max_zoom:
            scale_factor = self._max_zoom / current_scale
            self.scale(scale_factor, scale_factor)
            self._current_zoom = self._max_zoom
        elif current_scale < self._min_zoom:
            scale_factor = self._min_zoom / current_scale
            self.scale(scale_factor, scale_factor)
            self._current_zoom = self._min_zoom
        else:
            self._current_zoom = current_scale