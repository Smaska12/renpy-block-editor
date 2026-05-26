from PySide6.QtGui import QUndoCommand
from PySide6.QtCore import QPointF

class BlockMoveCommand(QUndoCommand):
    def id(self) -> int:
        return 1 

    def __init__(self, block, old_pos, new_pos):
        super().__init__("Перемещение блока")
        self.block = block
        self.old_pos = QPointF(old_pos)
        self.new_pos = QPointF(new_pos)

    def redo(self):
        self.block.setPos(self.new_pos)
        if self.block.scene():
            self.block.scene().update_connections_for_block(self.block)

    def undo(self):
        self.block.setPos(self.old_pos)
        if self.block.scene():
            self.block.scene().update_connections_for_block(self.block)

    def mergeWith(self, other: QUndoCommand) -> bool:
        if other.id() != self.id():
            return False
        if isinstance(other, BlockMoveCommand) and other.block is self.block:
            self.new_pos = other.new_pos
            return True
        return False


class SetPropertyCommand(QUndoCommand):
    def __init__(self, block, key, old_val, new_val):
        super().__init__(f"Изменение {key}")
        self.block = block
        self.key = key
        self.old_val = old_val
        self.new_val = new_val

    def redo(self):
        self.block._props[self.key] = self.new_val
        self.block._update_summary()
        self.block.update()

    def undo(self):
        self.block._props[self.key] = self.old_val
        self.block._update_summary()
        self.block.update()


class ConnectionCommand(QUndoCommand):
    def __init__(self, scene, conn_data, is_remove=False):
        super().__init__("Связь" if not is_remove else "Удаление связи")
        self.scene = scene
        self.conn_data = conn_data
        self.is_remove = is_remove
        self.edge_ref = None

    def redo(self):
        if self.is_remove: self._remove()
        else: self._create()

    def undo(self):
        if self.is_remove: self._create()
        else: self._remove()

    def _create(self):
        src = self.scene._get_block_by_id(self.conn_data["source_id"])
        tgt = self.scene._get_block_by_id(self.conn_data["target_id"])
        if src and tgt:
            s_port = src.ports['out'][self.conn_data["source_idx"]]
            t_port = tgt.ports['in'][self.conn_data["target_idx"]]
            self.edge_ref = self.scene._create_connection_edge(s_port, t_port)

    def _remove(self):
        if self.edge_ref and self.edge_ref.scene():
            self.scene.remove_connection(self.edge_ref)