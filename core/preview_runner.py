import os
import subprocess
import tempfile
import shutil
from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtCore import QSettings, QObject, Signal
from code_generator import CodeGenerator

class PreviewRunner(QObject):
    preview_started = Signal()
    preview_stopped = Signal()
    error_occurred = Signal(str)

    def __init__(self, scene, parent_window):
        super().__init__()
        self.scene = scene
        self.parent_window = parent_window
        self.settings = QSettings("VNMaker", "PreviewSettings")
        self.process = None
        self.temp_dir = None

    def get_renpy_path(self):
        return self.settings.value("renpy_sdk_path", "", str)

    def set_renpy_path(self, path):
        self.settings.setValue("renpy_sdk_path", path)

    def is_running(self):
        return self.process is not None and self.process.poll() is None

    def stop(self):
        if self.is_running():
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()
            finally:
                self.process = None
                self._cleanup_temp()
                self.preview_stopped.emit()

    def _cleanup_temp(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try: shutil.rmtree(self.temp_dir)
            except PermissionError: pass
            self.temp_dir = None

    def _copy_assets_to_temp(self, temp_game_dir, project_game_dir):
        temp_images = os.path.join(temp_game_dir, "images")
        temp_audio = os.path.join(temp_game_dir, "audio")
        os.makedirs(temp_images, exist_ok=True)
        os.makedirs(temp_audio, exist_ok=True)

        for sub in ["backgrounds", "characters"]:
            src = os.path.join(project_game_dir, "images", sub)
            if os.path.exists(src):
                shutil.copytree(src, os.path.join(temp_images, sub), dirs_exist_ok=True)
        for sub in ["music", "sound"]:
            src = os.path.join(project_game_dir, "audio", sub)
            if os.path.exists(src):
                shutil.copytree(src, os.path.join(temp_audio, sub), dirs_exist_ok=True)

    def run(self):
        if self.is_running():
            QMessageBox.information(self.parent_window, "Информация", "Предпросмотр уже запущен!")
            return

        renpy_path = self.get_renpy_path()
        if not renpy_path or not os.path.exists(renpy_path):
            renpy_path = self._ask_for_renpy_path()
            if not renpy_path: return
            self.set_renpy_path(renpy_path)

        try:
            self.temp_dir = tempfile.mkdtemp(prefix="vn_preview_")
            game_dir = os.path.join(self.temp_dir, "game")
            os.makedirs(game_dir, exist_ok=True)
        except Exception as e:
            self.error_occurred.emit(f"Ошибка создания временной папки: {str(e)}")
            return

        pm = self.parent_window.project_manager
        if pm.is_project_open and pm.game_path:
            try: self._copy_assets_to_temp(game_dir, str(pm.game_path))
            except Exception as e: self.error_occurred.emit(f"Ошибка копирования ассетов: {str(e)}")

        try:
            gen = CodeGenerator(self.scene.characters, self.scene.labels)
            script_content = gen.generate_full_script()
            with open(os.path.join(game_dir, "script.rpy"), "w", encoding="utf-8") as f:
                f.write(script_content)

            options_content = """\
define config.window = "auto"
define config.default_text_cps = 0
define config.has_autosave = False
define config.gl2 = True
"""
            with open(os.path.join(game_dir, "options.rpy"), "w", encoding="utf-8") as f:
                f.write(options_content)
        except Exception as e:
            self.error_occurred.emit(f"Ошибка генерации скрипта: {str(e)}")
            self._cleanup_temp()
            return

        try:
            renpy_exe = renpy_path
            if os.path.isdir(renpy_path):
                renpy_exe = os.path.join(renpy_path, "renpy.exe" if os.name == 'nt' else "renpy.sh")
            if not os.path.exists(renpy_exe):
                raise FileNotFoundError(f"Не найден исполняемый файл Ren'Py: {renpy_exe}")

            self.process = subprocess.Popen([renpy_exe, self.temp_dir])
            self.preview_started.emit()
        except Exception as e:
            self.error_occurred.emit(f"Не удалось запустить движок: {str(e)}")
            self._cleanup_temp()

    def _ask_for_renpy_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self.parent_window,
            "Укажите путь к исполняемому файлу Ren'Py (renpy.exe или renpy.sh)",
            "",
            "Executables (*)"
        )
        return path