import math
from PySide6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsEllipseItem, QStyle
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QPolygonF, QPainterPathStroker
from PySide6.QtCore import Qt, QPointF
from core.theme_manager import theme


class PortItem(QGraphicsEllipseItem):
    def __init__(self, port_type, index=0, parent=None):
        super().__init__(-6, -6, 12, 12, parent)
        self.port_type = port_type
        self.index = index
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsFocusable, False)
        self.setZValue(10)
        self._update_colors()

    def set_highlighted(self, is_active: bool):
        """Подсвечивает порт как активную цель для соединения."""
        if is_active:
            self.setBrush(QBrush(QColor(theme.color('success'))))
            self.setPen(QPen(QColor(theme.color('success')), 2.5))
            self.setScale(1.4)
        else:
            self._update_colors()
            self.setScale(1.0)
        self.update()

    def _update_colors(self):
        c = theme.get()
        self.setBrush(QBrush(QColor(c['text_muted'])))
        self.setPen(QPen(QColor(c['border_light']), 1.5))

    def shape(self):
        path = QPainterPath()
        path.addEllipse(self.rect())
        stroker = QPainterPathStroker()
        stroker.setWidth(18)  
        return stroker.createStroke(path)

    def hoverEnterEvent(self, event):
        self.setScale(1.3)  
        self.setBrush(QBrush(QColor(theme.color('primary'))))
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.setScale(1.0)
        self._update_colors()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.port_type == 'out':
            self.scene().start_connection_drag(self)
            event.accept()
        else:
            super().mousePressEvent(event)


class ConnectionEdge(QGraphicsPathItem):
    def __init__(self, source_port, target_port, parent=None):
        super().__init__(parent)
        self.source_port = source_port
        self.target_port = target_port
        self.setZValue(-1)
        self.setFlag(QGraphicsPathItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        
        self.is_hover = False
        
        self.default_color = QColor(theme.color('edge_color'))
        self.hover_color = QColor(theme.color('primary_hover'))
        self.selected_color = QColor(theme.color('secondary'))
        
        self._init_pen()
        self.update_path()

    def _init_pen(self):
        if self.isSelected():
            current_color = self.selected_color
            width = 3.5
            style = Qt.DashLine
        elif self.is_hover:
            current_color = self.hover_color
            width = 3.5
            style = Qt.SolidLine
        else:
            current_color = self.default_color
            width = 2.5
            style = Qt.SolidLine
            
        self.pen_current = QPen(current_color, width, style, Qt.RoundCap, Qt.RoundJoin)
        self.setPen(self.pen_current)

    def hoverEnterEvent(self, event):
        self.is_hover = True
        self._init_pen()
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.is_hover = False
        self._init_pen()
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsPathItem.GraphicsItemChange.ItemSelectedHasChanged:
            self._init_pen()
            self.update()
        return super().itemChange(change, value)

    def update_style(self, color=None):
        if color:
            self.default_color = color
        self._init_pen()
        self.update()

    def shape(self):
        path = QPainterPath()
        path.addPath(self.path())
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        stroker.setCapStyle(Qt.RoundCap)
        return stroker.createStroke(path)

    def update_path(self):
        if not self.source_port or not self.target_port:
            return
        p1 = self.source_port.scenePos()
        p2 = self.target_port.scenePos() 
        
        path = QPainterPath()
        path.moveTo(p1)
        
        dy = abs(p2.y() - p1.y())
        cp1 = QPointF(p1.x(), p1.y() + dy * 0.5)  
        cp2 = QPointF(p2.x(), p2.y() - dy * 0.5)  
        
        path.cubicTo(cp1, cp2, p2)
        self.setPath(path)

    def paint(self, painter, option, widget=None):
        mod_option = option
        mod_option.state &= ~QStyle.State_Selected
        super().paint(painter, mod_option, widget)
        
        if self.path().length() < 2:
            return
            
        p2 = self.target_port.scenePos()
        angle = self.path().angleAtPercent(1.0)
        rad = math.radians(angle)
        size = 8
        
        arrow = QPolygonF([
            QPointF(p2.x(), p2.y()),
            QPointF(p2.x() - size*math.cos(rad - 0.4), p2.y() - size*math.sin(rad - 0.4)),
            QPointF(p2.x() - size*math.cos(rad + 0.4), p2.y() - size*math.sin(rad + 0.4))
        ])
        
        painter.setBrush(self.pen().color())
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(arrow)
        
        if self.isSelected():
            painter.save()
            glow_pen = QPen(self.selected_color, 6, Qt.SolidLine, Qt.RoundCap)
            glow_pen.setStyle(Qt.DotLine)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(self.path())
            painter.restore()