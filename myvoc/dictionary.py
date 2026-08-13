"""词典查询 — 有道词典 API 封装

API: https://dict.youdao.com/suggest?num=1&doctype=json&q=单词

返回结构（MVP）：
{
    "result": {"msg": "success", "code": 200},
    "data": {
        "entries": [{"explain": "v. 抛弃，放弃", "entry": "abandon"}],
        "query": "abandon",
        "type": "dict"
    }
}

MVP 阶段只取释义（explain），音标后续补充。

查不到时返回 None。
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from myvoc.config import get

logger = logging.getLogger(__name__)

YOUDAO_URL = "https://dict.youdao.com/suggest?num=1&doctype=json&q={word}"


def _parse_json(text: str) -> dict | None:
    """安全解析 JSON"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def lookup_word(word: str) -> dict | None:
    """查询有道词典，返回 {phonetic, meaning} 或 None"""
    timeout = get("dictionary.timeout_seconds", 5)
    url = YOUDAO_URL.format(word=urllib.parse.quote(word))

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MyVoc/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        resp_data = _parse_json(data)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        logger.warning("词典查询失败 [%s]: %s", word, e)
        return None
    except ValueError as e:
        logger.warning("词典解析失败 [%s]: %s", word, e)
        return None

    if not resp_data:
        return None

    entries = resp_data.get("data", {}).get("entries", [])
    if not entries:
        return None

    # 精确匹配第一个结果
    first = entries[0]
    explain = first.get("explain", "")
    if not explain:
        return None

    # MVP 阶段暂不取音标（API 返回中不含音标）
    return {
        "phonetic": "",
        "meaning": explain,
    }


# ==================== 音频查询 ====================

# Free Dictionary API — 获取音标
PHONETIC_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
# Youdao TTS — 音频 URL（美式/英式）
YOUDAO_TTS_URL_US = "https://dict.youdao.com/dictvoice?audio={word}&type=0"
YOUDAO_TTS_URL_UK = "https://dict.youdao.com/dictvoice?audio={word}&type=1"


def fetch_audio_url(word: str) -> dict | None:
    """混合方案：音标来自 Free Dictionary API，音频 URL 拼接 Youdao TTS

    返回格式：{"audio_url": "https://dict.youdao.com/...", "phonetic": "/əˈbændən/"}
    查不到音标时返回 None
    """
    timeout = get("dictionary.timeout_seconds", 5)
    url = PHONETIC_API_URL.format(word=urllib.parse.quote(word))

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MyVoc/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read().decode("utf-8")
        entries = _parse_json(data)
    except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
        logger.warning("音频查询失败 [%s]: %s", word, e)
        return None
    except ValueError as e:
        logger.warning("音频解析失败 [%s]: %s", word, e)
        return None

    if not entries:
        return None

    # 区分成功/失败响应：成功返回数组，失败返回字典
    if isinstance(entries, dict):
        return None

    entry = entries[0]
    phonetic = entry.get("phonetic", "")
    if not phonetic:
        # 从 phonetics 数组取第一个有 text 的条目
        for p in entry.get("phonetics", []):
            t = p.get("text", "")
            if t:
                phonetic = t
                break

    if not phonetic:
        return None

    # 音频 URL 用 Youdao TTS 格式（无需请求，直接拼接）
    return {
        "audio_url": YOUDAO_TTS_URL_US.format(word=urllib.parse.quote(word)),
        "phonetic": phonetic,
    }
