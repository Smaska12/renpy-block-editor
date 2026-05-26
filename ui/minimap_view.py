import sys
from PySide6.QtWidgets import QGraphicsView
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QBrush, QColor
from core.theme_manager import theme

class MinimapView(QGraphicsView):
    def __init__(self, main_view):
        super().__init__()
        self.main_view = main_view
        
        self.setScene(main_view.scene())
        
        self.setRenderHint(QPainter.Antialiasing)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setInteractive(False)  
        self.setMouseTracking(True)
        self.setFixedWidth(200)
        self.setFixedHeight(150)
        
        c = theme.get()
        self.setStyleSheet(f"""
            QGraphicsView {{
                background-color: {c['bg_surface']};
                border: 1px solid {c['border']};
                border-radius: 4px;
            }}
        """)

        self.scale_factor = 0.1
        
        self.viewport_rect = None

        self.scene().sceneRectChanged.connect(self.update_scale)
        
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.update_viewport_rect)
        self.sync_timer.start(50) 
        
        QTimer.singleShot(100, self.update_scale)

    def update_scale(self):
        """Пересчитывает масштаб миникарты под текущий размер всех блоков"""
        if not self.scene(): return
        
        r = self.scene().sceneRect()
        if r.isEmpty(): return
        
        w_scale = (self.width() - 10) / r.width()
        h_scale = (self.height() - 10) / r.height()
        self.scale_factor = min(w_scale, h_scale, 1.0)
        
        self.resetTransform()
        self.scale(self.scale_factor, self.scale_factor)
        
        self.centerOn(r.center())

    def update_viewport_rect(self):
        """Вычисляет, какую часть сцены мы сейчас видим в главном окне"""
        if not self.main_view: return
        
        vp_rect = self.main_view.viewport().rect()
        self.viewport_rect = self.main_view.mapToScene(vp_rect).boundingRect()
        
        self.update()

    def paintEvent(self, event):
        """Отрисовка блоков (сделано через QGraphicsView) и рамки поверх них"""
        super().paintEvent(event)
        
        if self.viewport_rect:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.Antialiasing)
            
            c = theme.get()
            border_color = QColor(c['primary'])
            fill_color = QColor(c['primary'])
            fill_color.setAlpha(40) 
            
            pen = QPen(border_color, 2, Qt.SolidLine)
            painter.setPen(pen)
            painter.setBrush(QBrush(fill_color))
            
            rect_in_minimap = self.mapFromScene(self.viewport_rect).boundingRect()
            
            painter.drawRect(rect_in_minimap)
            painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pan_to(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._pan_to(event.pos())

    def _pan_to(self, view_pos):
        """Перемещает камеру главного окна в точку клика на миникарте"""
        scene_pos = self.mapToScene(view_pos)
        self.main_view.centerOn(scene_pos)