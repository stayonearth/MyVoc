"""MyVoc 数据管理页面 — Streamlit 工具（优化版）

查看、搜索、筛选、删除单词。
分页加载 + SQL 筛选 + 按需加载学习记录，解决大数据量卡顿。

运行方式:
    pip install streamlit
    streamlit run myvoc/admin.py
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# 数据库路径 — 与 myvoc.database 逻辑一致
# ---------------------------------------------------------------------------

try:
    from myvoc.database import get_db_path

    DB_PATH = Path(str(get_db_path()))
except ImportError:
    DB_PATH = Path.home() / "AppData" / "Local" / "myvoc" / "myvoc" / "myvoc.db"

# ---------------------------------------------------------------------------
# 数据查询
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


def stage_label(stage: int, next_date: str | None) -> str:
    """返回学习阶段的显示标签。"""
    if stage >= len(STAGE_LABELS):
        return "🎓 已毕业"
    if stage == 0:
        label = "🆕 新词"
    else:
        label = STAGE_LABELS[min(stage, len(STAGE_LABELS) - 1)]
    return f"{label} ({next_date})" if next_date else label


def _conn() -> sqlite3.Connection:
    """获取数据库连接。"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ---- 分页查询 ----

_PER_PAGE = 50
_VALID_SORTS = {"id": "id", "word": "word", "accuracy": None, "stage": None}


def _paginate_page(
    page: int,
    page_size: int,
    search: str = "",
    min_stage: int = 0,
    sort_by: str = "word",
) -> tuple[list[sqlite3.Row], int]:
    """返回 (单词行列表, 总记录数)。

    单次查询完成分页 + 聚合统计（LEFT JOIN + GROUP BY），
    仅在 min_stage > 0 时额外查一次 learning_records。
    """
    # ---- 1. 构建带聚合统计的单词列表 ----
    sql = """
        SELECT w.id, w.word, w.phonetic, w.meaning, w.audio_url,
               w.created_at, lr.latest_stage     AS max_stage,
               lr.latest_date    AS latest_date,
               lr.total_correct  AS total_correct,
               lr.total_wrong    AS total_wrong
          FROM words w
          LEFT JOIN (
              SELECT word_id,
                     MAX(stage)                    AS latest_stage,
                     MAX(next_review_date)          AS latest_date,
                     COALESCE(SUM(correct_count),0) AS total_correct,
                     COALESCE(SUM(wrong_count),0)   AS total_wrong
                FROM learning_records
               GROUP BY word_id
          ) lr ON lr.word_id = w.id
    """
    params: list = []

    # 搜索（同时查 word 和 meaning）
    if search:
        sql += " WHERE (LOWER(w.word) LIKE ? OR LOWER(w.meaning) LIKE ?)"
        q = f"%{search}%"
        params.extend([q, q])

    # 最低阶段过滤（需要预查所有符合条件的 word_id）
    if min_stage > 0:
        ids = _ids_with_stage(_conn(), min_stage)
        if ids:
            placeholders = ",".join("?" * len(ids))
            where_clause = (" AND " if "WHERE" in sql else " WHERE ")
            sql += f"{where_clause}w.id IN ({placeholders})"
            params.extend(ids)
        else:
            return [], 0

    # 排序（安全白名单，防止 SQL 注入）
    order = "w.id ASC"
    sort_key = _VALID_SORTS.get(sort_by)
    if sort_key:
        order = f"w.{sort_key} ASC"
    elif sort_by == "accuracy":
        order = ("COALESCE(lr.total_correct,0) * 100 / "
                 "COALESCE(lr.total_correct + lr.total_wrong, 1) DESC")
    elif sort_by == "stage":
        order = "COALESCE(lr.latest_stage, 0) DESC"

    sql += f" ORDER BY {order} LIMIT ? OFFSET ?"
    params.extend([page_size, page * page_size])

    rows = _conn().execute(sql, params).fetchall()

    # ---- 2. 统计总数（复用 WHERE，去掉 LIMIT/OFFSET） ----
    where_idx = sql.find(" ORDER BY ")
    if where_idx == -1:
        count_part = sql
    else:
        count_part = sql[:where_idx]

    # 用 SELECT COUNT(DISTINCT w.id) 替换首行
    count_sql = "SELECT COUNT(DISTINCT w.id) FROM " + count_part[sql.find(" FROM "):]
    total = _conn().execute(count_sql, params[:-2]).fetchone()[0]
    return rows, total


def _ids_with_stage(conn_ref: sqlite3.Connection, min_stage: int) -> list[int]:
    """返回达到指定阶段及以上的单词 ID 集合。"""
    rows = conn_ref.execute(
        "SELECT DISTINCT word_id FROM learning_records WHERE stage >= ? ORDER BY word_id",
        (min_stage,),
    ).fetchall()
    return [r[0] for r in rows]


# ---- 按需加载学习记录 ----

def _get_learning_records(word_id: int) -> list[dict]:
    """获取某单词的全部学习记录（仅在被展开时调用，单条查询极快）。"""
    rows = _conn().execute(
        "SELECT * FROM learning_records "
        "WHERE word_id = ? ORDER BY learn_date DESC, id DESC",
        (word_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _delete_word(word_id: int) -> None:
    """级联删除单词及其所有学习记录和会话引用。"""
    c = _conn()
    c.execute("DELETE FROM learning_records WHERE word_id = ?", (word_id,))
    rows = c.execute("SELECT id, word_ids FROM daily_sessions").fetchall()
    for row in rows:
        ids = json.loads(row["word_ids"] or "[]")
        if word_id in ids:
            ids.remove(word_id)
            c.execute("UPDATE daily_sessions SET word_ids = ? WHERE id = ?",
                      (json.dumps(ids), row["id"]))
    c.execute("DELETE FROM words WHERE id = ?", (word_id,))
    c.commit()
    c.close()


# ---------------------------------------------------------------------------
# Streamlit UI
# ---------------------------------------------------------------------------

def _render_word_row(word: sqlite3.Row) -> None:
    """渲染一个可展开的单词卡片。"""
    wid = word["id"]
    w_text = word["word"] or "?"
    phonetic = word["phonetic"] or ""
    meaning = word["meaning"] or "（无释义）"
    created = word["created_at"] or "?"

    max_stage = word["max_stage"]
    latest_date = word["latest_date"]
    total_correct = word["total_correct"] or 0
    total_wrong = word["total_wrong"] or 0
    total = total_correct + total_wrong

    # 阶段标签
    if max_stage is not None and max_stage >= 7:
        stage_txt = "🎓 已毕业"
    elif max_stage is None:
        stage_txt = "未学习"
    else:
        stage_txt = stage_label(max_stage, latest_date)

    # 正确率
    acc_txt = f" {total_correct*100//total}%" if total > 0 else "—"

    # 颜色
    if total > 0:
        ratio = total_correct / total
        color = "#2e7d32" if ratio >= 0.8 else ("#f57f17" if ratio >= 0.5 else "#c62828")
    else:
        color = "#888"

    header = (
        f"**{w_text}**  "
        f"{' | '.join(filter(None, [phonetic, stage_txt, acc_txt]))}"
    )

    with st.expander(header, expanded=False):
        # ---- 基本信息行 ----
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
        c1.markdown(f"**{w_text}**")
        c2.caption(phonetic or "—")
        c3.caption(meaning)
        c4.caption(f"录入: {created}")

        # ---- 删除按钮 / 确认 ----
        if st.session_state.get("_admin_pending_delete") == wid:
            st.warning(f"确定删除 **{w_text}** 及其所有学习记录？")
            _ck, _ok, _cn = st.columns([2, 1, 1])
            if _ok.button("确认删除", key=f"confirm_{wid}", use_container_width=True):
                _delete_word(wid)
                st.success(f"已删除 **{w_text}**")
                del st.session_state["_admin_pending_delete"]
                st.rerun()
            if _cn.button("取消", key=f"cancel_{wid}", use_container_width=True):
                del st.session_state["_admin_pending_delete"]
                st.rerun()
            st.stop()
        else:
            st.button(
                "🗑️ Del",
                key=f"del_{wid}",
                help=f"删除单词 '{w_text}' 及其所有学习记录",
                use_container_width=True,
            )

        st.divider()

        # ---- 按需加载学习记录 ----
        w_records = _get_learning_records(wid)

        if not w_records:
            st.info("📭 暂无学习记录")
        else:
            st.markdown(
                f'**累计** 正确: <span style="color:{color}">{total_correct}</span> / '
                f'错误: <span style="color:{color}">{total_wrong}</span>'
                f' · 正确率 {total_correct*100//total}%',
                unsafe_allow_html=True,
            )
            st.divider()

            for r in w_records:
                rc = r["correct_count"]
                rw = r["wrong_count"]
                rt = rc + rw
                rr = rc / rt if rt > 0 else 0
                rcolor = "#2e7d32" if rr >= 0.8 else ("#f57f17" if rr >= 0.5 else "#c62828")
                cols = st.columns(5)
                cols[0].caption(f"📅 {r['learn_date']}")
                cols[1].caption(f"阶段 {r['stage']} · 间隔 {r['interval']} 天")
                cols[2].caption(f"下次: {r['next_review_date'] or '—'}")
                cols[3].caption(
                    f'正: <span style="color:{rcolor}">{rc}</span> / '
                    f'错: <span style="color:{rcolor}">{rw}</span>',
                    unsafe_allow_html=True,
                )
                cols[4].caption(f"{r['last_result'] or '—'} · {r['last_review_at'] or '—'}")

        # 音频
        audio_url = word["audio_url"]
        if audio_url:
            st.audio(audio_url, format="audio/mpeg")


def _stats_data() -> dict:
    """快速统计卡片数据（单次聚合查询）。"""
    c = _conn()
    row = c.execute(
        "SELECT COUNT(*) as wc, "
        "  (SELECT COALESCE(SUM(correct_count),0) FROM learning_records) as tc, "
        "  (SELECT COALESCE(SUM(wrong_count),0) FROM learning_records) as tw, "
        "  (SELECT COUNT(DISTINCT id) FROM daily_sessions) as sc, "
        "  (SELECT COUNT(DISTINCT word_id) FROM learning_records WHERE stage >= 7) as grad "
        "FROM words"
    ).fetchone()
    c.close()
    return {
        "words": row["wc"],
        "records": (row["tc"] or 0) + (row["tw"] or 0),
        "sessions": row["sc"],
        "graduated": row["grad"],
    }


def main() -> None:
    st.set_page_config(page_title="MyVoc 管理面板", layout="wide", page_icon="📖")
    st.title("📖 MyVoc 单词管理面板")

    # ---- 顶部统计 ----
    stats = _stats_data()
    cols = st.columns(4)
    cols[0].metric("总单词数", stats["words"])
    cols[1].metric("学习记录", stats["records"])
    cols[2].metric("会话数", stats["sessions"])
    cols[3].metric("已毕业", stats["graduated"])

    st.divider()

    # ---- 侧边栏筛选 ----
    with st.sidebar:
        st.header("筛选")
        search = st.text_input("搜索单词", placeholder="输入英文或中文...").lower()
        min_stage = st.slider("最低阶段", 0, 7, 0)
        sort_by = st.radio("排序", ["ID", "单词", "正确率", "阶段"], index=1)
        st.divider()
        st.caption(f"数据库: {DB_PATH}")

    # ---- 分页控件（显式 session_state 管理） ----
    if "_admin_page" not in st.session_state:
        st.session_state._admin_page = 0
    if "_admin_page_size" not in st.session_state:
        st.session_state._admin_page_size = _PER_PAGE

    # 页大小选择器
    page_sizes = [20, 50, 100]
    ps = st.selectbox("每页条数", page_sizes,
                      index=page_sizes.index(st.session_state._admin_page_size))
    st.session_state._admin_page_size = ps

    # 计算总页数
    total_pages = max(1, (stats["words"] + ps - 1) // ps) if stats["words"] > 0 else 1

    # 页码输入
    page = st.number_input(
        "页码",
        min_value=0,
        max_value=total_pages - 1,
        value=st.session_state._admin_page,
        key="_admin_page_input",
        help=f"共 {total_pages} 页",
    )
    st.session_state._admin_page = page

    # 筛选改变后超出范围时重置页码
    if page * ps >= stats["words"] and stats["words"] > 0:
        st.session_state._admin_page = total_pages - 1
        page = total_pages - 1

    # ---- 查询 ----
    words, total = _paginate_page(page, ps, search, min_stage, sort_by)

    # ---- 列表 ----
    if total == 0:
        st.info("数据库中没有单词。使用 CLI 添加单词后在此查看。")
    else:
        st.subheader(f"单词列表 — {total} 个单词，每页 {ps} 个")

        # 渲染当前页
        for w in words:
            _render_word_row(w)


if __name__ == "__main__":
    main()
