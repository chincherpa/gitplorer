from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Config:
    scan_dirs: list[Path]
    depth: int = 2
    exclude: list[str] = field(default_factory=lambda: [".venv", "node_modules", "__pycache__"])


def load_config() -> Config:
    config_path = Path(".gitplorer.toml")
    if config_path.exists():
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        return Config(
            scan_dirs=[Path(d).expanduser() for d in data.get("scan_dirs", ["~/projects"])],
            depth=data.get("depth", 2),
            exclude=data.get("exclude", [".venv", "node_modules", "__pycache__"]),
        )
    return Config(scan_dirs=[Path("E:/Projects")])
