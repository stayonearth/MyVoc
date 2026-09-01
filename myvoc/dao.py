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
    """更新学习记录（答对/答错），驱动艾宾浩斯调度

    查找该单词的最新学习记录并就地更新（不创建新记录）。
    首次测试时创建一条新记录。
    """
    if learn_date is None:
        learn_date = date.today()

    conn = _conn()

    from myvoc.config import get as conf_get
    base_intervals = conf_get("ebbinghaus.base_intervals", [0, 1, 2, 4, 7, 15, 30])
    ease_lower = 1.3

    # 查找该单词的最新记录（不按 learn_date 过滤，只按 id 倒序）
    row = conn.execute(
        "SELECT * FROM learning_records WHERE word_id = ? ORDER BY id DESC LIMIT 1",
        (word_id,),
    ).fetchone()

    if row:
        record = LearningRecord(**dict(row))
    else:
        # 首次测试：创建新记录
        conn.execute(
            """INSERT INTO learning_records
               (word_id, learn_date, stage, ease_factor, interval, next_review_date)
               VALUES (?, ?, 0, 2.5, 0, ?)""",
            (word_id, learn_date.isoformat(), learn_date.isoformat()),
        )
        conn.commit()
        record = get_or_create_record(word_id, learn_date)

    # review_base 直接用传入的 learn_date（本身就是 date 对象）
    review_base = learn_date.isoformat()

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
             review_base, new_interval, record.id),
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
            (new_stage, new_ease, review_base, record.id),
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
    d["test_progress"] = json.loads(d.get("test_progress") or "[]")
    return DailySession(**d)


def save_test_progress(word_ids: list[int], daily_test_count: int | None = None) -> None:
    """将已测试的单词 ID 保存到今天的 daily_session，用于崩溃恢复和每日上限追踪。

    如果今天尚无会话行则新建一条（仅用于记录测试进度，total_words 为 0）。
    在 test_progress JSON 数组中额外存入 "_daily_test_count:N" 标记，
    用于跨调用统计当日已测试的单词总数。

    参数:
        word_ids: 已测试的单词 ID 列表
        daily_test_count: 可选，手动指定当日总测试数（不传则自动计算 len(word_ids)）
    """
    conn = _conn()
    today = date.today().isoformat()
    count = daily_test_count if daily_test_count is not None else len(word_ids)
    # 将每日计数标记追加到数组末尾，格式: "_daily_test_count:N"
    progress = list(word_ids)
    progress.append(f"_daily_test_count:{count}")

    cur = conn.execute(
        "SELECT id FROM daily_sessions WHERE session_date = ?", (today,)
    ).fetchone()
    if cur:
        conn.execute(
            "UPDATE daily_sessions SET test_progress = ? WHERE session_date = ?",
            (json.dumps(progress), today),
        )
    else:
        # 无今日会话：新建一条，只用于保存测试进度
        conn.execute(
            "INSERT INTO daily_sessions (session_date, word_ids, total_words, test_progress) "
            "VALUES (?, ?, ?, ?)",
            (today, json.dumps([]), 0, json.dumps(progress)),
        )
    conn.commit()


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


def get_test_queue(max_size: int | None = None) -> list[Word]:
    """生成今日考核队列

    队列组成：
    1. 新词：今日会话中但没有任何学习记录的词
    2. 到期复习：next_review_date <= 今天（从 learning_records 全局筛选）
    合并去重，每个单词只出现一次（要么在新词，要么在复习中）

    参数:
        max_size: 如果指定，返回前 N 个单词；否则过滤已测试词（test_progress）后全部返回。
    """
    today = date.today().isoformat()
    conn = _conn()

    # 1. 今日会话中的所有单词 ID
    new_word_ids = get_today_word_ids()

    # 2. "新词" = 今日会话中但无 learning_records 的词
    if new_word_ids:
        placeholders = ",".join("?" * len(new_word_ids))
        reviewed_ids = conn.execute(
            f"SELECT DISTINCT word_id FROM learning_records "
            f"WHERE word_id IN ({placeholders})",
            new_word_ids,
        ).fetchall()
        reviewed_set = {r["word_id"] for r in reviewed_ids}
        new_word_ids = [wid for wid in new_word_ids if wid not in reviewed_set]

    # 3. 到期复习单词（全局筛选，不限会话，按到期日升序）
    overdue_rows = conn.execute(
        """SELECT word_id, MIN(next_review_date) AS min_date
           FROM learning_records
           WHERE next_review_date <= ?
           GROUP BY word_id
           ORDER BY min_date ASC, word_id ASC""",
        (today,),
    ).fetchall()
    review_word_ids = [r["word_id"] for r in overdue_rows]

    # 4. 合并去重（新词优先，复习补充）
    all_ids = list(new_word_ids)
    for wid in review_word_ids:
        if wid not in all_ids:
            all_ids.append(wid)

    if not all_ids:
        return []

    # 5. 限制数量
    if max_size is not None:
        all_ids = all_ids[:max_size]
    else:
        # 过滤已测试的词（崩溃恢复）
        session = get_today_session()
        if session and session.test_progress:
            # 只提取数字 ID，忽略字符串标记（如 "_daily_test_count:N"）
            tested_ids = [item for item in session.test_progress if isinstance(item, int)]
            all_ids = [wid for wid in all_ids if wid not in tested_ids]
            if not all_ids:
                return []

    words = get_words_by_ids(all_ids)
    # 按 ID 顺序保持队列顺序
    id_map = {w.id: w for w in words}
    return [id_map[wid] for wid in all_ids if wid in id_map]
