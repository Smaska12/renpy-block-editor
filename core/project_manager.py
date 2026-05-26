import json
import shutil
from PySide6.QtCore import QSettings
from datetime import datetime
from pathlib import Path

class ProjectManager:
    def __init__(self):
        self.project_path = None
        self.game_path = None
        self.project_json = None
        self.is_project_open = False
        self.settings = QSettings("VNMaker", "UI_Settings")

    def create_project_from_renpy(self, renpy_sdk_path, project_name, save_dir):
        """
        Создает проект, копируя шаблон из Ren'Py SDK.
        """
        renpy_path = Path(renpy_sdk_path)
        
        template_path = None
        possible_paths = [
            renpy_path / "the_question",
            renpy_path / "template",
            renpy_path.parent / "template",
            renpy_path / "renpy" / "template"
        ]
        
        for p in possible_paths:
            if p.exists() and (p / "game").exists():
                template_path = p
                break
        
        if not template_path:
            raise FileNotFoundError(
                f"Не найдена папка шаблона ('the_question' или 'template') в пути: {renpy_sdk_path}\n"
                "Убедитесь, что вы выбрали корневую папку SDK."
            )

        dest_project = Path(save_dir) / project_name
        if dest_project.exists():
            raise FileExistsError(f"Проект '{project_name}' уже существует в этой папке.")
        
        try:
            shutil.copytree(template_path, dest_project)
        except Exception as e:
            raise Exception(f"Ошибка копирования файлов шаблона: {e}")

    
        tl_folder = dest_project / "game" / "tl"
        if tl_folder.exists():
            for item in tl_folder.iterdir():
                if item.is_dir() and item.name.lower() != "none":
                    shutil.rmtree(item)
        
        game_folder = dest_project / "game"
        images_folder = game_folder / "images"
        (game_folder / "audio").mkdir(exist_ok=True)
        (game_folder / "libs").mkdir(exist_ok=True)
        (game_folder / "saves").mkdir(exist_ok=True)

        bg_folder = images_folder / "backgrounds"
        bg_folder.mkdir(exist_ok=True)
        
        char_folder = images_folder / "characters"
        char_folder.mkdir(exist_ok=True)
        
        sylvie_folder = char_folder / "sylvie"
        sylvie_folder.mkdir(exist_ok=True)

        audio_folder = game_folder / "audio"
        audio_folder.mkdir(exist_ok=True)
        (audio_folder / "music").mkdir(exist_ok=True)
        (audio_folder / "sound").mkdir(exist_ok=True)

        source_images = game_folder / "images"
        if source_images.exists():
            for item in source_images.iterdir():
                if item.is_file() and item.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                    name_lower = item.name.lower()
                    
                    if name_lower.startswith('bg'):
                        shutil.move(str(item), str(bg_folder / item.name))
                    elif 'sylvie' in name_lower:
                        shutil.move(str(item), str(sylvie_folder / item.name))
                    else:
                        shutil.move(str(item), str(char_folder / item.name))
        
        files_to_remove = [
            "android-icon_background.png",
            "android-icon_foreground.png",
            "android.json",
            "icon.icns",
            "icon.ico",
            "ios-icon.png",
            "ios-launchimage.png",
            "progressive_download.txt"
        ]
        
        for filename in files_to_remove:
            file_path = dest_project / filename
            if file_path.exists():
                file_path.unlink()

        options_file = dest_project / "game" / "options.rpy"
        if options_file.exists():
            lines = options_file.read_text(encoding="utf-8").splitlines(keepends=True)
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if stripped.startswith('define config.name = _("'):
                    new_lines.append(f'define config.name = _("{project_name}")\n')
                elif stripped.startswith('define build.name = "'):
                    new_lines.append(f'define build.name = "{project_name}"\n')
                else:
                    new_lines.append(line)
            
            text = "".join(new_lines)
            
            if not text.endswith("\n"):
                text += "\n"
                
            options_file.write_text(text, encoding="utf-8")

        self.project_path = dest_project
        self.game_path = dest_project / "game"
        self.project_json = dest_project / "project.json"
        
        self.project_json.write_text(json.dumps({
            "characters": {"Мысли": {"color": "#808080"}},
            "labels": {"start": []},
            "connections": [],
            "groups": [],
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "renpy_path": str(renpy_sdk_path),
                "project_name": project_name
            }
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        self.is_project_open = True
        return True

    def load_project(self, path):
        """Загружает существующий проект"""
        self.project_path = Path(path)
        self.game_path = self.project_path / "game"
        self.project_json = self.project_path / "project.json"
        
        if not self.project_json.exists():
            raise FileNotFoundError("Это не проект VN Maker (отсутствует project.json).")
            
        images_folder = self.game_path / "images"
        images_folder.mkdir(exist_ok=True)
        (images_folder / "backgrounds").mkdir(exist_ok=True)
        (images_folder / "characters").mkdir(exist_ok=True)
        
        audio_folder = self.game_path / "audio"
        audio_folder.mkdir(exist_ok=True)
        (audio_folder / "music").mkdir(exist_ok=True)
        (audio_folder / "sound").mkdir(exist_ok=True)
        
        self.is_project_open = True
        return True
    
    def add_to_recent_projects(self, path):
        """Добавляет путь в список недавних проектов без дубликатов"""
        try:
            normalized_path = str(Path(path).resolve())
        except Exception:
            normalized_path = str(path)

        recent = self.settings.value("recent_projects", [], type=list)
        
        recent = [p for p in recent if p != normalized_path]
        
        recent.insert(0, normalized_path)
        
        self.settings.setValue("recent_projects", recent[:10])
        self.settings.sync() 

    def get_recent_projects(self):
        """Возвращает список путей к недавним проектам"""
        return self.settings.value("recent_projects", [], type=list)

    def save_scene_data(self, data):
        """Сохраняет данные сцены в project.json"""
        if not self.is_project_open:
            raise Exception("Проект не открыт")
        
        if self.project_json.exists():
            with open(self.project_json, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                if "metadata" in old_data:
                    data["metadata"] = old_data["metadata"]
        
        with open(self.project_json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def export_script(self, code_generator):
        """Экспортирует сгенерированный код в script.rpy"""
        script = code_generator.generate_full_script()
        script_path = self.game_path / "script.rpy"
        script_path.write_text(script, encoding="utf-8")