"""数据访问层 — DAO

封装 words、learning_records、daily_sessions 三张表的 CRUD。
"""

from __future__ import annotations

import json
import logging
from datetime import date

from myvoc.database import init_db, get_db_path
from myvoc.models import Word, LearningRecord, DailySession

logger = logging.getLogger(__name__)

# 全局数据库连接（单例）
_db_conn = None


def _conn() -> "sqlite3.Connection":
    """获取全局数据库连接（懒初始化）"""
    global _db_conn
    if _db_conn is None:
        _db_conn = init_db()
    return _db_conn


# ==================== Word DAO ====================

def upsert_word(
    word: str,
    phonetic: str = "",
    meaning: str = "",
    source: str = "api",
) -> int:
    """插入或更新单词，返回 word_id。
    如果单词已存在则跳过，返回已有 id。"""
    conn = _conn()
    cur = conn.execute(
        "SELECT id FROM words WHERE word = ?", (word.lower(),)
    )
    row = cur.fetchone()
    if row:
        return row["id"]

    cursor = conn.execute(
        "INSERT INTO words (word, phonetic, meaning, source) VALUES (?, ?, ?, ?)",
        (word.lower(), phonetic, meaning, source),
    )
    conn.commit()
    return cursor.lastrowid


def get_word(word: str) -> Word | None:
    """按单词名查询"""
    conn = _conn()
    row = conn.execute(
        "SELECT * FROM words WHERE word = ?", (word.lower(),)
    ).fetchone()
    if not row:
        return None
    return Word(**dict(row))


def get_words_by_ids(word_ids: list[int]) -> list[Word]:
    """按 ID 列表批量查询"""
    if not word_ids:
        return []
    conn = _conn()
    placeholders = ",".join("?" * len(word_ids))
    rows = conn.execute(
        f"SELECT * FROM words WHERE id IN ({placeholders})", word_ids
    ).fetchall()
    return [Word(**dict(r)) for r in rows]


def get_all_words() -> list[Word]:
    """获取所有单词（按 id 排序）"""
    conn = _conn()
    rows = conn.execute("SELECT * FROM words ORDER BY id").fetchall()
    return [Word(**dict(r)) for r in rows]


def update_audio_url(word: str, audio_url: str) -> bool:
    """更新单词的 audio_url 字段"""
    conn = _conn()
    cursor = conn.execute(
        "UPDATE words SET audio_url = ? WHERE word = ?",
        (audio_url, word.lower()),
    )
    conn.commit()
    return cursor.rowcount > 0


def update_word_phonetic(word: str, phonetic: str) -> bool:
    """更新单词的 phonetic 字段"""
    conn = _conn()
    cursor = conn.execute(
        "UPDATE words SET phonetic = ? WHERE word = ?",
        (phonetic, word.lower()),
    )
    conn.commit()
    return cursor.rowcount > 0


# ==================== LearningRecord DAO ====================

def get_or_create_record(word_id: int, learn_date: date | None = None) -> LearningRecord:
    """获取或创建今日学习记录"""
    conn = _conn()
    if learn_date is None:
        learn_date = date.today()

    row = conn.execute(
        """SELECT * FROM learning_records
           WHERE word_id = ? AND learn_date = ?
           ORDER BY id DESC LIMIT 1""",
        (word_id, learn_date.isoformat()),
    ).fetchone()
    if row:
        return LearningRecord(**dict(row))

    from myvoc.config import get as conf_get
    base_intervals = conf_get("ebbinghaus.base_intervals", [0, 1, 2, 4, 7, 15, 30])

    conn.execute(
        """INSERT INTO learning_records
           (word_id, learn_date, stage, ease_factor, interval, next_review_date)
           VALUES (?, ?, 0, 2.5, 0, ?)""",
        (word_id, learn_date.isoformat(), (learn_date).isoformat()),
    )
    conn.commit()
    return get_or_create_record(word_id, learn_date)


def update_record(word_id: int, is_correct: bool, learn_date: date | None = None) -> None:
    """更新学习记录（答对/答错），驱动艾宾浩斯调度"""
    if learn_date is None:
        learn_date = date.today()

    record = get_or_create_record(word_id, learn_date)
    conn = _conn()

    from myvoc.config import get as conf_get
    base_intervals = conf_get("ebbinghaus.base_intervals", [0, 1, 2, 4, 7, 15, 30])
    ease_lower = 1.3
    ease_upper = 3.0

    if is_correct:
        new_stage = record.stage + 1
        new_interval = base_intervals[min(new_stage, len(base_intervals) - 1)]
        conn.execute(
            """UPDATE learning_records SET
               stage = ?, ease_factor = ?, interval = ?,
               next_review_date = date(?, '+' || ? || ' days'),
               correct_count = correct_count + 1,
               last_result = 'correct',
               last_review_at = datetime('now')
               WHERE id = ?""",
            (new_stage, record.ease_factor, new_interval,
             learn_date.isoformat(), new_interval, record.id),
        )
    else:
        new_stage = max(0, record.stage - 2)
        new_ease = max(ease_lower, record.ease_factor - 0.2)
        conn.execute(
            """UPDATE learning_records SET
               stage = ?, ease_factor = ?, interval = 1,
               next_review_date = date(?, '+1 day'),
               wrong_count = wrong_count + 1,
               last_result = 'wrong',
               last_review_at = datetime('now')
               WHERE id = ?""",
            (new_stage, new_ease, learn_date.isoformat(), record.id),
        )

    conn.commit()


# ==================== DailySession DAO ====================

def create_session(word_names: list[str]) -> int:
    """创建今日会话，返回 session id"""
    conn = _conn()
    today = date.today().isoformat()

    # 检查是否已有今日会话
    row = conn.execute(
        "SELECT * FROM daily_sessions WHERE session_date = ?", (today,)
    ).fetchone()

    word_ids = []
    new_session_id = None
    if row:
        # 追加到已有会话
        existing_ids = json.loads(row["word_ids"] or "[]")
        for name in word_names:
            wid = upsert_word(name, "", "", "api")
            if wid not in existing_ids:
                existing_ids.append(wid)
        word_ids = existing_ids
        conn.execute(
            "UPDATE daily_sessions SET word_ids = ?, total_words = ? WHERE session_date = ?",
            (json.dumps(word_ids), len(word_ids), today),
        )
        new_session_id = row["id"]
    else:
        # 新建会话
        for name in word_names:
            wid = upsert_word(name, "", "", "api")
            word_ids.append(wid)
        cursor = conn.execute(
            "INSERT INTO daily_sessions (session_date, word_ids, total_words) VALUES (?, ?, ?)",
            (today, json.dumps(word_ids), len(word_ids)),
        )
        new_session_id = cursor.lastrowid

    conn.commit()
    return new_session_id


def get_today_session() -> DailySession | None:
    """获取今日会话"""
    conn = _conn()
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT * FROM daily_sessions WHERE session_date = ?", (today,)
    ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["word_ids"] = json.loads(d["word_ids"] or "[]")
    return DailySession(**d)


def get_today_word_ids() -> list[int]:
    """获取今日录入的单词 ID 列表"""
    session = get_today_session()
    return session.word_ids if session else []


def get_latest_record(word_id: int, learn_date: date | None = None) -> dict | None:
    """获取某单词最近一条学习记录"""
    conn = _conn()
    if learn_date is None:
        learn_date = date.today()
    row = conn.execute(
        """SELECT * FROM learning_records
           WHERE word_id = ? AND learn_date = ?
           ORDER BY id DESC LIMIT 1""",
        (word_id, learn_date.isoformat()),
    ).fetchone()
    return dict(row) if row else None


def get_test_queue() -> list[Word]:
    """生成今日考核队列

    队列优先级：
    1. 今日新学单词（从 daily_sessions）
    2. 到期复习单词（next_review_date <= 今天，从 learning_records）
    合并时按 word_id 去重，优先保留 stage 低的（复习进度靠前的）
    """
    today = date.today().isoformat()
    conn = _conn()

    # 1. 今日新学单词 ID
    new_word_ids = get_today_word_ids()

    # 2. 到期复习单词（排除已在新学中的）
    overdue_rows = conn.execute(
        """SELECT DISTINCT lr.word_id
           FROM learning_records lr
           INNER JOIN daily_sessions ds ON lr.learn_date = ds.session_date
           WHERE lr.next_review_date <= ?
             AND NOT EXISTS (
               SELECT 1 FROM json_each(ds.word_ids) j
               WHERE j.value = CAST(lr.word_id AS TEXT)
             )""",
        (today,),
    ).fetchall()
    review_word_ids = [r["word_id"] for r in overdue_rows]

    # 3. 合并去重（新学优先，复习补充）
    all_ids = list(new_word_ids)
    for wid in review_word_ids:
        if wid not in all_ids:
            all_ids.append(wid)

    if not all_ids:
        return []

    words = get_words_by_ids(all_ids)
    # 按 ID 顺序保持队列顺序
    id_map = {w.id: w for w in words}
    return [id_map[wid] for wid in all_ids if wid in id_map]
