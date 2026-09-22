"""Persistent preferences and imported assets, independent of the source files."""
from dataclasses import asdict, dataclass, fields
import json
from pathlib import Path
import shutil
from uuid import uuid4

from PySide6.QtCore import QObject, QStandardPaths, Signal
from ai.difficulty import DIFFICULTIES
from tools.credentials import load_jev_key

AUDIO_DIR = Path(__file__).resolve().parents[1] / "src" / "audio"


@dataclass
class Settings:
    ai_difficulty: str = "normal"
    jev_model: str = "jev-latest"
    music_path: str = str(AUDIO_DIR / "667.mp3")
    win_path: str = str(AUDIO_DIR / "5553.mp3")
    lose_path: str = str(AUDIO_DIR / "5538.mp3")
    music_enabled: bool = True
    effects_enabled: bool = True
    music_loop: bool = True
    music_volume: int = 35
    effects_volume: int = 70
    background_path: str = ""
    background_blur: bool = False


class SettingsStore(QObject):
    changed = Signal()

    def __init__(self, directory=None, parent=None):
        super().__init__(parent)
        self.directory = Path(directory) if directory else Path(
            QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)
        ) / "Gomoku"
        self.path = self.directory / "settings.json"
        self.values = Settings()
        self.jev_api_key = load_jev_key()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                for field in fields(Settings):
                    default = getattr(self.values, field.name)
                    value = data.get(field.name, default)
                    if type(value) is type(default):
                        setattr(self.values, field.name, value)
        except (OSError, ValueError):
            pass
        if self.values.ai_difficulty not in DIFFICULTIES:
            self.values.ai_difficulty = "normal"
        self.values.jev_model = "jev-latest"
        for key in ("music_volume", "effects_volume"):
            setattr(self.values, key, max(0, min(100, getattr(self.values, key))))
        for key in ("music_path", "win_path", "lose_path"):
            if not Path(getattr(self.values, key)).is_file():
                setattr(self.values, key, getattr(Settings(), key))
        if not Path(self.values.background_path).is_file():
            self.values.background_path = ""

    def save(self, values, cropped_image=None, jev_api_key=None):
        values = Settings(**asdict(values))
        self.directory.mkdir(parents=True, exist_ok=True)
        for key in ("music_path", "win_path", "lose_path"):
            source = Path(getattr(values, key)).resolve()
            if not source.is_file():
                raise OSError(f"找不到音频文件：{source.name}")
            if source.parent not in (AUDIO_DIR.resolve(), self.directory.resolve()):
                destination = self.directory / f"{key}-{uuid4().hex}{source.suffix}"
                shutil.copyfile(source, destination)
                setattr(values, key, str(destination))
        if cropped_image is not None:
            destination = self.directory / f"background-{uuid4().hex}.png"
            if not cropped_image.save(str(destination), "PNG"):
                raise OSError("背景图保存失败")
            values.background_path = str(destination)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(values), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        self.values = values
        if jev_api_key is not None:
            self.jev_api_key = jev_api_key
        self.changed.emit()
