"""MyVoc 数据管理页面 — Streamlit 工具

查看单词及对应的学习记录，支持删除单词（级联删除学习记录）。

运行方式:
    pip install streamlit
    streamlit run myvoc/admin.py
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# 数据库路径 — 与 myvoc.database 逻辑一致
# ---------------------------------------------------------------------------

try:
    from myvoc.database import get_db_path

    DB_PATH = Path(str(get_db_path()))
except ImportError:
    # 直接运行（不在包内）时的回退路径
    DB_PATH = Path.home() / "AppData" / "Local" / "myvoc" / "myvoc" / "myvoc.db"

# ---------------------------------------------------------------------------
# 数据加载
# ---------------------------------------------------------------------------

def _load_all_data() -> dict:
    """一次性加载所有数据，返回结构化字典"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    words = conn.execute("SELECT * FROM words ORDER BY id").fetchall()
    records = conn.execute(
        "SELECT * FROM learning_records ORDER BY learn_date DESC, id"
    ).fetchall()
    sessions = conn.execute(
        "SELECT * FROM daily_sessions ORDER BY session_date"
    ).fetchall()

    conn.close()

    # 按 word_id 聚合学习记录
    records_by_word: dict[int, list] = {}
    for r in records:
        wid = r["word_id"]
        records_by_word.setdefault(wid, []).append(dict(r))

    return {
        "words": [dict(w) for w in words],
        "records_by_word": records_by_word,
        "sessions": [dict(s) for s in sessions],
    }

# ---------------------------------------------------------------------------
# 辅助显示
# ---------------------------------------------------------------------------

STAGE_LABELS = [
    "新词 · 今天复习",
    "1 天后复习",
    "2 天后复习",
    "4 天后复习",
    "7 天后复习",
    "15 天后复习",
    "30 天后复习",
    "已毕业 🎓",
]


def stage_tag(row: dict) -> str:
    """返回学习阶段的 emoji 标签"""
    stage = row.get("stage", 0)
    interval = row.get("interval", 0)
    next_date = row.get("next_review_date")

    if stage >= len(STAGE_LABELS):
        return "🎓 已毕业"
    if stage == 0 and interval == 0 and not next_date:
        return "🆕 新词"
    label = STAGE_LABELS[min(stage, len(STAGE_LABELS) - 1)]
    if next_date:
        return f"{label} ({next_date})"
    return label


def _correct_color(correct: int, wrong: int) -> str:
    total = correct + wrong
    if total == 0:
        return "#888"
    ratio = correct / total
    if ratio >= 0.8:
        return "#2e7d32"
    if ratio >= 0.5:
        return "#f57f17"
    return "#c62828"


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="MyVoc 管理面板", layout="wide", page_icon="📖")
    st.title("📖 MyVoc 单词管理面板")

    # 加载数据（带缓存）
    @st.cache_data(ttl=30)
    def _cached_load() -> dict:
        return _load_all_data()

    data = _cached_load()
    words = data["words"]
    records_by_word = data["records_by_word"]
    sessions = data["sessions"]

    # ---- 顶部统计卡片 ----
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总单词数", len(words))
    total_records = sum(len(v) for v in records_by_word.values())
    col2.metric("学习记录", total_records)
    col3.metric("会话数", len(sessions))
    graduated = sum(1 for rlist in records_by_word.values() for r in rlist if r["stage"] >= 7)
    col4.metric("已毕业", graduated)

    # ---- 搜索与筛选 ----
    st.divider()
    with st.sidebar:
        st.header("筛选")
        search = st.text_input("搜索单词", placeholder="输入英文或中文...").lower()
        min_stage = st.slider("最低阶段", 0, 7, 0)
        show_graduated_only = st.toggle("仅显示已毕业")
        sort_by = st.radio("排序", ["ID", "单词", "正确率", "阶段"], index=1)
        st.divider()
        st.caption(f"数据库: {DB_PATH}")
        st.caption(f"记录数: {len(words)} 单词, {total_records} 记录")

    # ---- 过滤单词列表 ----
    filtered = words
    if search:
        filtered = [
            w for w in filtered
            if search in (w.get("word", "") or "").lower()
            or search in (w.get("meaning", "") or "").lower()
        ]
    if min_stage > 0:
        ids_with_stage: set[int] = set()
        for wid, rlist in records_by_word.items():
            if any(r["stage"] >= min_stage for r in rlist):
                ids_with_stage.add(wid)
        if ids_with_stage:
            ids_set = {w["id"] for w in filtered}
            filtered = [w for w in filtered if w["id"] in ids_with_stage]
        else:
            filtered = []
    if show_graduated_only:
        filtered = [
            w for w in filtered
            if any(r["stage"] >= 7 for r in records_by_word.get(w["id"], []))
        ]

    # 排序
    if sort_by == "单词":
        filtered = sorted(filtered, key=lambda w: (w.get("word") or ""))
    elif sort_by == "正确率":
        filtered = sorted(filtered, key=lambda w: _word_accuracy(w["id"], records_by_word))
    elif sort_by == "阶段":
        filtered = sorted(filtered, key=lambda w: _word_max_stage(w["id"], records_by_word), reverse=True)
    # ID 排序默认就是

    st.subheader(f"单词列表 — {len(filtered)} / {len(words)}")

    # ---- 逐词展开 ----
    for word in filtered:
        wid = word["id"]
        w_records = records_by_word.get(wid, [])
        correct = sum(r["correct_count"] for r in w_records)
        wrong = sum(r["wrong_count"] for r in w_records)
        accuracy = f"{correct * 100 // (correct + wrong):.0f}%" if (correct + wrong) > 0 else "—"

        # 最新一条记录
        latest = w_records[0] if w_records else None
        stage_label = stage_tag(latest) if latest else "未学习"

        with st.expander(
            f"**{word.get('word', '?')}**  "
            f"{' | '.join(filter(None, [word.get('phonetic',''), stage_label, accuracy]))}",
            expanded=False,
        ):
            # 单词信息行
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 1, 1])
            c1.markdown(f"**{word.get('word', '?')}**")
            c2.caption(word.get("phonetic", "") or "—")
            c3.caption(word.get("meaning", "") or "（无释义）")
            c4.caption(f"录入: {word.get('created_at', '?')}")

            # 删除按钮 / 确认删除
            if st.session_state.get("pending_delete") == wid:
                pw = st.session_state.get("pending_word", "?")
                st.warning(f"确定删除 **{pw}** 及其所有学习记录？")
                _ck, _ok, _cn = st.columns([2, 1, 1])
                if _ok.button("确认删除", key=f"confirm_{wid}", use_container_width=True):
                    _delete_word(wid)
                    st.success(f"已删除 **{pw}**")
                    del st.session_state["pending_delete"]
                    del st.session_state["pending_word"]
                    st.rerun()
                if _cn.button("取消", key=f"cancel_{wid}", use_container_width=True):
                    del st.session_state["pending_delete"]
                    del st.session_state["pending_word"]
                    st.rerun()
                st.stop()
            else:
                st.button(
                    "🗑️ Del",
                    key=f"del_{wid}",
                    help=f"删除单词 '{word.get('word', '?')}' 及其所有学习记录",
                    use_container_width=True,
                )

            st.divider()

            if not w_records:
                st.info("📭 暂无学习记录")
            else:
                # 学习记录表格
                # 统计
                total_correct = sum(r["correct_count"] for r in w_records)
                total_wrong = sum(r["wrong_count"] for r in w_records)
                total = total_correct + total_wrong
                ratio = _correct_color(total_correct, total_wrong)
                acc_text = ''
                if total > 0:
                    acc_text = f' · 正确率 {total_correct * 100 // total}%'
                st.markdown(
                    f'**累计** 正确: <span style="color:{ratio}">{total_correct}</span> / '
                    f'错误: <span style="color:{ratio}">{total_wrong}</span>'
                    f'{acc_text}',
                    unsafe_allow_html=True,
                )
                st.divider()

                # 逐条记录
                for r in w_records:
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.caption(f"📅 {r['learn_date']}")
                    c2.caption(f"阶段 {r['stage']} · 间隔 {r['interval']} 天")
                    c3.caption(f"下次: {r['next_review_date'] or '—'}")
                    ratio = _correct_color(r["correct_count"], r["wrong_count"])
                    c4.caption(
                        f'正: <span style="color:{ratio}">{r["correct_count"]}</span> / '
                        f'错: <span style="color:{ratio}">{r["wrong_count"]}</span>',
                        unsafe_allow_html=True,
                    )
                    c5.caption(f"{r['last_result'] or '—'} · {r['last_review_at'] or '—'}")

            # 音频链接（如果有）
            if word.get("audio_url"):
                st.audio(word["audio_url"], format="audio/mpeg")


def _word_accuracy(word_id: int, records_by_word: dict) -> float:
    """计算单词累计正确率（0~1），无记录返回 None（排前面）"""
    records = records_by_word.get(word_id, [])
    correct = sum(r["correct_count"] for r in records)
    wrong = sum(r["wrong_count"] for r in records)
    total = correct + wrong
    if total == 0:
        return 0.0
    return correct / total


def _word_max_stage(word_id: int, records_by_word: dict) -> int:
    """返回单词最高阶段"""
    records = records_by_word.get(word_id, [])
    return max((r["stage"] for r in records), default=0)


def _delete_word(word_id: int) -> None:
    """级联删除单词及其所有学习记录（与 cli.py delete 逻辑一致）"""
    conn = sqlite3.connect(str(DB_PATH))
    try:
        # 先删除从表数据（避免外键约束失败）
        conn.execute("DELETE FROM learning_records WHERE word_id = ?", (word_id,))
        # 从 daily_sessions.word_ids 中移除
        rows = conn.execute("SELECT id, word_ids FROM daily_sessions").fetchall()
        for row in rows:
            ids = json.loads(row["word_ids"] or "[]")
            if word_id in ids:
                ids.remove(word_id)
                conn.execute(
                    "UPDATE daily_sessions SET word_ids = ? WHERE id = ?",
                    (json.dumps(ids), row["id"]),
                )
        conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
