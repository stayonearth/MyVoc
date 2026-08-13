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
