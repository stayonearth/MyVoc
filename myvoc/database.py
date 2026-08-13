"""数据库初始化与建表"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import appdirs

# 默认数据库路径：~/.myvoc/myvoc.db
_DEFAULT_DIR = Path(appdirs.user_data_dir("myvoc", "myvoc"))
_DEFAULT_DB = _DEFAULT_DIR / "myvoc.db"


def get_db_path() -> Path:
    """获取数据库文件路径（可被 config 覆盖）"""
    return _DEFAULT_DB


def init_db(db_path: Path | None = None) -> sqlite3.Connection:
    """连接数据库并建表，返回 Connection"""
    path = db_path or get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row  # 字典式访问
    conn.execute("PRAGMA foreign_keys = ON")
    _create_tables(conn)
    # executescript() 会隐式 commit，之后需要再 commit 一次恢复状态
    conn.commit()
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    """执行建表 SQL"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS words (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            word       TEXT    UNIQUE NOT NULL,
            phonetic   TEXT    DEFAULT '',
            meaning    TEXT    DEFAULT '',
            created_at DATETIME DEFAULT (datetime('now')),
            source     TEXT    DEFAULT 'api'
        );

        CREATE TABLE IF NOT EXISTS learning_records (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id          INTEGER NOT NULL REFERENCES words(id),
            learn_date       DATE    NOT NULL,
            stage            INTEGER DEFAULT 0,
            ease_factor      REAL    DEFAULT 2.5,
            interval         INTEGER DEFAULT 0,
            next_review_date DATE,
            correct_count    INTEGER DEFAULT 0,
            wrong_count      INTEGER DEFAULT 0,
            last_result      TEXT,
            last_review_at   DATETIME
        );

        CREATE TABLE IF NOT EXISTS daily_sessions (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            session_date DATE    UNIQUE NOT NULL,
            word_ids     TEXT    DEFAULT '[]',
            total_words  INTEGER DEFAULT 0
        );
    """)
