"""数据模型 — dataclass 定义"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Word:
    """单词主表实体"""
    id: Optional[int] = None
    word: str = ""
    phonetic: str = ""
    meaning: str = ""
    created_at: Optional[datetime] = None
    source: str = "api"  # api | manual
    audio_url: str = ""


@dataclass
class LearningRecord:
    """学习记录实体，驱动艾宾浩斯调度"""
    id: Optional[int] = None
    word_id: int = 0
    learn_date: Optional[date] = None
    stage: int = 0
    ease_factor: float = 2.5
    interval: int = 0
    next_review_date: Optional[date] = None
    correct_count: int = 0
    wrong_count: int = 0
    last_result: Optional[str] = None  # correct | wrong
    last_review_at: Optional[datetime] = None


@dataclass
class DailySession:
    """每日会话实体"""
    id: Optional[int] = None
    session_date: Optional[date] = None
    word_ids: list[int] | None = None  # JSON 数组
    total_words: int = 0
    test_progress: list[int] | None = None  # JSON 数组，记录已测试的单词 ID
