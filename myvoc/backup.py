"""数据库备份与恢复 — CLI: myvoc backup-db / myvoc restore-db

备份格式: SQLite .dump 兼容的 SQL 脚本
存储路径: db/backup_YYYY-MM-DD.sql
恢复方式: 读取 SQL 脚本并在目标数据库中 execute_script

使用示例:
    python -m myvoc backup-db        # 备份到 db/backup_2026-08-27.sql
    python -m myvoc restore-db       # 交互式选择备份文件恢复
    python -m myvoc restore-db --force  # 跳过确认直接恢复
"""

from __future__ import annotations

import glob
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from myvoc.database import get_db_path, init_db


# ---------------------------------------------------------------------------
# 备份
# ---------------------------------------------------------------------------

_BACKUP_DIR = Path(__file__).parent.parent / "db"


def backup_db(db_path: Path | None = None) -> str | None:
    """将整个数据库导出为 SQL 脚本到 db/backup_YYYY-MM-DD.sql。

    返回备份文件路径，失败返回 None。
    """
    conn = init_db(db_path)
    try:
        backup_dir = _BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 文件名: backup_YYYY-MM-DD.sql
        ts = datetime.now().strftime("%Y-%m-%d")
        backup_file = backup_dir / f"backup_{ts}.sql"

        # 如果同一天已有备份，追加序号
        counter = 1
        while backup_file.exists():
            backup_file = backup_dir / f"backup_{ts}_{counter:02d}.sql"
            counter += 1

        # 使用 iterdump() 兼容 Python 3.8（dump_database 需要 3.12+）
        with backup_file.open("w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write(line + "\n")

        # 统计信息
        word_count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        record_count = conn.execute("SELECT COUNT(*) FROM learning_records").fetchone()[0]
        session_count = conn.execute("SELECT COUNT(*) FROM daily_sessions").fetchone()[0]
        conn.close()

        print(f"[OK] 数据库已备份: {backup_file}")
        print(f"     单词 {word_count} 个, 学习记录 {record_count} 条, 会话 {session_count} 次")
        return str(backup_file)
    except Exception as exc:
        print(f"[FAIL] 备份失败: {exc}")
        return None


# ---------------------------------------------------------------------------
# 恢复
# ---------------------------------------------------------------------------


def _list_backups() -> list[Path]:
    """列出可用的备份文件（按时间倒序）"""
    pattern = _BACKUP_DIR / "backup_*.sql"
    files = sorted(glob.glob(str(pattern)), reverse=True)
    return [Path(f) for f in files]


def restore_db(db_path: Path | None = None, force: bool = False, select_idx: int | None = None, restore_file: str | None = None) -> bool:
    """从 SQL 备份文件恢复数据库。

    参数:
        db_path:      目标数据库路径（默认使用配置文件中的路径）
        force:        True 则跳过确认
        select_idx:   指定恢复的备份序号（1-based），指定后跳过交互选择
        restore_file: 指定备份文件的完整路径，直接从此文件恢复

    返回:
        True 成功, False 失败或用户取消
    """
    if restore_file is not None:
        # 直接从指定路径恢复
        selected = Path(restore_file)
        if not selected.exists():
            print(f"[ERROR] 备份文件不存在: {selected}")
            return False
    else:
        # 列出 db/ 下的备份文件，让用户选择
        backup_files = _list_backups()
        if not backup_files:
            print("[WARN] 未找到可用备份文件 (在 db/ 下)")
            return False

        print("[可选备份文件]")
        for i, f in enumerate(backup_files, 1):
            print(f"  {i}. {f.name}  ({f.stat().st_size / 1024:.1f} KB)")

        if select_idx is not None:
            if 1 <= select_idx <= len(backup_files):
                idx = select_idx - 1
            else:
                print(f"[ERROR] 无效的序号 {select_idx} (有效范围 1-{len(backup_files)})")
                return False
        else:
            while True:
                try:
                    choice = input(f"\n请选择备份文件 [1-{len(backup_files)}]: ").strip()
                    idx = int(choice) - 1
                    if 0 <= idx < len(backup_files):
                        break
                except (ValueError, KeyboardInterrupt):
                    pass
                print(f"  输入无效，请输入数字 (1-{len(backup_files)}) 或直接 Ctrl+C 取消")

        selected = backup_files[idx]

    print(f"\n将恢复: {selected.name}")

    # 确认
    if not force:
        confirm = input("确认恢复? 当前数据库数据将被覆盖 (y/n): ").strip().lower()
        if confirm != "y":
            print("已取消。")
            return False

    # 执行恢复
    try:
        sql_text = selected.read_text(encoding="utf-8")

        # 创建新的空数据库（不调用 init_db，避免建表冲突）
        target = db_path or get_db_path()
        target.parent.mkdir(parents=True, exist_ok=True)

        # 删除旧数据库
        if target.exists():
            os.remove(str(target))

        # 直接连接并执行脚本（init_db 会先建表，导致冲突）
        new_conn = sqlite3.connect(str(target))
        new_conn.executescript(sql_text)
        new_conn.close()

        # 验证恢复结果
        conn = init_db(target)
        word_count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        record_count = conn.execute("SELECT COUNT(*) FROM learning_records").fetchone()[0]
        session_count = conn.execute("SELECT COUNT(*) FROM daily_sessions").fetchone()[0]
        conn.close()

        print(f"\n[OK] 数据库恢复成功: {selected.name}")
        print(f"     单词 {word_count} 个, 学习记录 {record_count} 条, 会话 {session_count} 次")
        return True
    except Exception as exc:
        print(f"\n[FAIL] 恢复失败: {exc}")
        return False
