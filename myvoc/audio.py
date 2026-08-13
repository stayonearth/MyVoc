"""音频播放模块 — 为 learn 命令提供单词发音功能

使用 playsound 播放 Youdao TTS 生成的 MP3 音频。
音频先下载到本地缓存，避免重复下载。

支持两种播放模式：
- 手动模式：阻塞等待音频播放完毕
- 自动模式：后台线程播放，不阻塞自动切换计时
"""

from __future__ import annotations

import hashlib
import logging
import os
import platform
import threading
import urllib.request

logger = logging.getLogger(__name__)

# 临时音频缓存目录（用户数据目录下）
_AUDIO_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".myvoc", "audio_cache")


def _ensure_cache_dir() -> str:
    """确保缓存目录存在"""
    os.makedirs(_AUDIO_CACHE_DIR, exist_ok=True)
    return _AUDIO_CACHE_DIR


def _audio_filename(audio_url: str) -> str:
    """从 Youdao TTS URL 提取单词名作为文件名"""
    # 格式: https://dict.youdao.com/dictvoice?audio=<word>&type=0
    query = audio_url.split("?", 1)[1] if "?" in audio_url else ""
    # 提取 audio= 参数
    for param in query.split("&"):
        if param.startswith("audio="):
            word = param.split("=", 1)[1]
            # 过滤非法字符，确保是合法文件名
            valid = "".join(c for c in word if c.isalnum() or c in "._-")
            if valid:
                return f"{valid}.mp3"
    # 兜底：用 URL hash
    h = hashlib.md5(audio_url.encode()).hexdigest()[:8]
    return f"audio_{h}.mp3"


def _download_audio(audio_url: str) -> str | None:
    """下载音频到本地缓存，返回文件路径；失败返回 None"""
    try:
        filename = _audio_filename(audio_url)
        filepath = os.path.join(_ensure_cache_dir(), filename)

        # 如果已缓存则直接返回
        if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
            return filepath

        req = urllib.request.Request(audio_url, headers={"User-Agent": "MyVoc/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        if len(data) < 100:
            return None
        with open(filepath, "wb") as f:
            f.write(data)
        return filepath
    except Exception as exc:
        logger.debug("音频下载失败 [%s]: %s", audio_url, exc)
        return None


def play_audio(audio_url: str, auto_mode: bool = False) -> None:
    """播放单词发音

    Args:
        audio_url: Youdao TTS MP3 URL（如 https://dict.youdao.com/dictvoice?audio=abandon&type=0）
        auto_mode: True=自动模式（后台线程 + 5秒超时），False=手动模式（阻塞等听完）
    """
    if not audio_url:
        return

    try:
        from playsound import playsound
    except ImportError:
        logger.warning("playsound 未安装，音频播放已禁用")
        return

    filepath = _download_audio(audio_url)
    if not filepath:
        return

    system = platform.system()

    if system == "Windows" and not auto_mode:
        # 手动模式：阻塞播放
        try:
            playsound(filepath)
        except Exception as exc:
            logger.debug("音频播放失败 [%s]: %s", filepath, exc)
    else:
        # 自动模式 或 非 Windows：后台线程
        def _play() -> None:
            try:
                playsound(filepath)
            except Exception as exc:
                logger.debug("音频播放失败 [%s]: %s", filepath, exc)

        thread = threading.Thread(target=_play, daemon=True)
        thread.start()

        if auto_mode:
            thread.join(timeout=5.0)
