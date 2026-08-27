"""配置加载 — 从 config.json 读取，提供默认值

MVP 阶段使用 JSON 格式（无需第三方依赖）；
后续可切换为 YAML（需 pip install pyyaml）。
"""

from __future__ import annotations

import json
from pathlib import Path

# 配置文件路径
_CONFIG_PATH = Path(__file__).parent.parent / "config.json"

# 默认配置
_DEFAULTS = {
    "learning": {
        "auto_mode": False,
        "auto_interval_seconds": 5,
        "show_phonetic": True,
        "show_meaning_first": False,
        "play_audio": False,
    },
    "testing": {
        "case_sensitive": False,
        "typo_tolerance": 0,  # MVP 精确匹配
        "session_limit": 150,  # 每日测试上限（单词数），跨 test 调用累计
    },
    "ebbinghaus": {
        "base_intervals": [0, 1, 2, 4, 7, 15, 30],
        "max_stage": 7,
        "default_ease_factor": 2.5,
    },
    "dictionary": {
        "provider": "youdao",
        "timeout_seconds": 5,
    },
    "database": {
        "path": "",  # 空字符串 → 使用默认路径
    },
}

_config: dict = {}


def load_config(path: Path | None = None) -> dict:
    """加载配置文件，合并默认值"""
    global _config
    cfg_path = path or _CONFIG_PATH
    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            _config = json.load(f) or {}
    else:
        _config = {}
    # 合并默认值
    _merge_defaults(_config, _DEFAULTS)
    return _config


def _merge_defaults(target: dict, defaults: dict) -> None:
    """递归合并默认值"""
    for key, default_val in defaults.items():
        if key not in target:
            target[key] = default_val
        elif isinstance(default_val, dict) and isinstance(target[key], dict):
            _merge_defaults(target[key], default_val)


def get(key: str, default=None):
    """按点号路径取值，如 config.get('learning.auto_mode')"""
    keys = key.split(".")
    val = _config
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k, default)
        else:
            return default
    return val


def reload(path: Path | None = None) -> dict:
    """重新加载配置"""
    global _config
    _config = {}
    return load_config(path)
