"""CLI 入口 — Click 命令定义

MVP 阶段只有 add 命令，后续逐步加入 learn/test/today/status。
"""

from __future__ import annotations

import json

import click

from myvoc.config import load_config


@click.group()
@click.version_option(version="0.1.0", prog_name="myvoc")
def cli():
    """MyVoc - 单词记忆训练工具"""
    load_config()


@cli.command()
@click.option("--skip-unknown", is_flag=True, help="跳过查不到释义的单词")
def add(skip_unknown: bool) -> None:
    """录入单词：逐行输入英文单词或词组，自动查词后入库

    每行可以输入多个单词（空格分隔）或词组（用引号包裹），回车后逐个查词显示。
    词组示例: "take off" 或 'put up with'
    按 Ctrl+D (Unix) / Ctrl+Z (Windows) 结束输入。
    """
    import sys
    import shlex
    from myvoc.dictionary import lookup_word
    from myvoc.dao import upsert_word, create_session
    from rich.console import Console
    from rich.status import Status

    console = Console()
    console.print("[录入模式] 输入完成后按 [cyan]Ctrl+Z[/cyan] (Windows) 或 [cyan]Ctrl+D[/cyan] (Unix) 结束")
    console.print("[dim]提示：词组请用引号包裹，如 \"take off\" 或 'put up with'[/dim]")
    console.print("-" * 50)

    added = []
    failed = []
    manual_added = []

    while True:
        # 先输出提示符（Rich Console 会自动 flush stdout）
        console.print("\n(输入单词，或 Ctrl+Z 结束) → ", soft_wrap=True, end="")
        try:
            # input() 的 EOFError 最可靠，且与 Rich 输出不冲突
            line = input()
        except (EOFError, KeyboardInterrupt):
            break
        words_text = line.strip()
        if not words_text:
            continue

        # 使用 shlex.split() 智能分割：保留引号内的词组，去除引号本身
        try:
            raw_words = shlex.split(words_text)
        except ValueError as e:
            console.print(f"  [yellow][ERROR][reset] 输入格式错误: {e}")
            continue

        for raw_word in raw_words:
            word = raw_word.strip().lower()
            if not word:
                continue

            # 查词：显示动态加载提示
            with Status(f"  正在查询 [bold]{word}[/bold]...", spinner="dots"):
                info = lookup_word(word)

            if info:
                upsert_word(word, info["phonetic"], info["meaning"])
                added.append(word)
                console.print(f"  [green][OK][reset] {word}  {info['phonetic']}  {info['meaning']}")
            else:
                meaning = click.prompt(f"  [{word}] 未查询到释义，请手动输入中文释义", default="")
                if meaning:
                    upsert_word(word, "", meaning, source="manual")
                    added.append(word)
                    manual_added.append(word)
                    console.print(f"  [green][OK][reset] {word}  (手动)  {meaning}")
                elif not skip_unknown:
                    failed.append(word)
                    console.print(f"  [yellow][SKIP][reset] {word}（未提供释义且 --skip-unknown 未设置）")

    # 创建会话
    if added:
        create_session(added)

    click.echo()
    click.echo("=" * 50)
    total_manual = len(manual_added)
    total_skip = len(failed)
    msg = f"录入完成：共录入 {len(added)} 个单词"
    if total_manual:
        msg += f"，其中 {total_manual} 个手动补充"
    if total_skip:
        msg += f"，跳过 {total_skip} 个"
    click.echo(msg)


# ---------------------------------------------------------------------------
# 背诵模式导航辅助函数
# ---------------------------------------------------------------------------


def _show_manual_nav(console: "Console", idx: int, total: int) -> None:
    """显示手动模式的导航提示"""
    hint = f"[dim]  [{idx}/{total}]"
    if idx > 1:
        hint += " [PgUp] 上一个"
    else:
        hint += " [PgUp] 已在第一个"
    hint += " | [PgDn]/[回车] 下一个"
    hint += " | [q] 退出[/dim]"
    console.print(hint)


def _read_key_manual(console: "Console", current_idx: int, word_count: int) -> int:
    """读取手动模式下的按键，返回下一个单词的索引（0-based）

    返回 -1 表示退出。
    返回 word_count 表示已到达末尾。
    """
    import msvcrt

    while True:
        key = msvcrt.getch()

        # ── 普通字符 ──────────────────────────────
        if key != b'\x00' and key != b'\xe0':
            # Enter 键：进入下一个单词
            if key in (b'\x0d', b'\x0a'):
                if current_idx >= word_count - 1:
                    return word_count  # 已到最后一个，退出循环
                return current_idx + 1
            ch = key.decode('ascii', errors='ignore').lower()
            if ch == 'q':
                console.print("\n已退出背诵模式。")
                return -1  # 退出信号

        # ── 扩展键（方向键 / 翻页键）──────────────
        ext = msvcrt.getch()
        key_combo = key + ext

        if key_combo == b'\xe0\x48':     # ↑ 上箭头
            if current_idx > 0:
                return current_idx - 1
            console.print("\n[dim]已在第一个单词，无法上翻[/dim]")
            return current_idx
        if key_combo == b'\xe0\x50':     # ↓ 下箭头
            if current_idx >= word_count - 1:
                return word_count  # 已到最后一个，退出循环
            return current_idx + 1
        if key_combo == b'\xe0\x21':     # PgUp
            if current_idx > 0:
                return current_idx - 1
            console.print("\n[dim]已在第一个单词，无法上翻[/dim]")
            return current_idx
        if key_combo == b'\xe0\x22':     # PgDn
            if current_idx >= word_count - 1:
                return word_count  # 已到最后一个，退出循环
            return current_idx + 1


@cli.command()
@click.option("--auto", is_flag=True, help="自动模式：每个单词显示指定时长后自动切换")
@click.option("--count", type=int, default=None, help="只背诵前 N 个单词")
def learn(auto: bool, count: int | None) -> None:
    """背诵模式：依次显示单词的英文、音标、中文释义，并播放发音

    手动模式导航：
        [↓] / [PgDn] 下一个
        [↑] / [PgUp] 上一个（第一个时停留并提示）
        [回车] / [q] 退出
    """
    from myvoc.dao import get_today_session, get_words_by_ids
    from myvoc.config import get as conf_get
    from myvoc.audio import play_audio
    from rich.console import Console
    import sys
    import time

    console = Console()
    session = get_today_session()
    if not session or not session.word_ids:
        click.echo("今天还没有录入单词，请先运行 `myvoc add`。")
        return

    words = get_words_by_ids(session.word_ids)
    if not words:
        click.echo("今天还没有录入单词，请先运行 `myvoc add`。")
        return

    if count:
        words = words[:count]

    total = len(words)
    mode_text = "自动" if auto else "手动"
    console.print(f"\n[bold]== 背诵模式 · {mode_text} · 第 1 / {total} 个 ==[/bold]\n")

    auto_interval = conf_get("learning.auto_interval_seconds", 5)
    audio_enabled = conf_get("learning.play_audio", False)

    idx = 0
    while idx < total:
        word = words[idx]
        console.clear()
        console.print(f"[bold]== 背诵模式 · {mode_text} · 第 {idx + 1} / {total} 个 ==[/bold]")
        console.print("-" * 40)
        console.print(f"\n  [bold]{word.word}[/bold]")
        if audio_enabled and word.audio_url:
            play_audio(word.audio_url, auto_mode=auto)
        if word.phonetic:
            console.print(f"  {word.phonetic}")
        if word.meaning:
            console.print(f"\n  {word.meaning}")
        else:
            console.print(f"\n  （无释义）")
        console.print("-" * 40)

        if auto:
            console.print(f"[dim][{auto_interval}秒后自动切换] [q] 退出[/dim]")
            try:
                time.sleep(auto_interval)
            except KeyboardInterrupt:
                console.print("\n已退出背诵模式。")
                return
        else:
            _show_manual_nav(console, idx + 1, total)
            result = _read_key_manual(console, idx, total)
            if result == -1:
                return
            idx = result


@cli.command()
@click.argument("limit", type=int, required=False, default=None)
def test(limit: int | None) -> None:
    """考核模式：显示中文释义，输入英文单词作答

    答对 -> stage+1，更新复习间隔
    答错 -> stage-2，难度系数降低
    持续循环直到所有单词都答对才退出（可随时按 'q' 退出）

    参数:
        LIMIT: 可选，今日测试的最大单词数。不指定则使用配置中的默认值。
               如果小于今日新增单词数，则以新增单词数为准。

    示例:
        myvoc test      # 使用配置中的默认上限（如 150）
        myvoc test 30   # 今日最多测试 30 个单词
    """
    import time

    from myvoc.config import get as conf_get
    from myvoc.dao import get_test_queue, get_today_session, save_test_progress, update_record, get_words_by_ids
    from myvoc.audio import play_audio

    queue = get_test_queue()
    if not queue:
        click.echo("今日考核已完成。")
        return

    # 检查每日测试上限（跨调用的累计数）
    # 如果命令行指定了 limit，则使用命令行参数；否则使用配置
    daily_limit = limit if limit is not None else conf_get("testing.session_limit", 150)

    # 计算今日新增单词数（未答过的）
    today_word_ids = get_today_session().word_ids if get_today_session() else []
    today_progress = get_today_session()
    daily_tested = 0
    tested_ids_set = set()

    if today_progress and today_progress.test_progress:
        for item in today_progress.test_progress:
            if isinstance(item, str) and item.startswith("_daily_test_count:"):
                try:
                    daily_tested = int(item.split(":", 1)[1])
                except (ValueError, IndexError):
                    pass
                break
        tested_ids_set = {item for item in today_progress.test_progress if isinstance(item, int)}

    new_unanswered = [wid for wid in today_word_ids if wid not in tested_ids_set]
    new_unanswered_count = len(new_unanswered)

    # 如果 daily_limit 小于今日新增单词数，则以新增单词数为准
    if daily_limit and new_unanswered_count > 0:
        original_limit = daily_limit
        daily_limit = max(daily_limit, new_unanswered_count)
        if limit is not None and original_limit < new_unanswered_count:
            click.echo(f"提示：今日新增 {new_unanswered_count} 个单词，已将测试上限从 {original_limit} 调整为 {daily_limit}")
            click.echo()

    if daily_limit and daily_tested >= daily_limit:
        # 已达到每日上限
        # 检查是否有新的未答词（仅今日会话中但还未答过的）
        if new_unanswered:
            click.echo(f"已达到今日测试上限（已测试 {daily_tested} / {daily_limit} 题）。")
            click.echo(f"但有 {len(new_unanswered)} 个新增单词尚未答过。")
            if click.confirm("是否继续答这些新词？", default=False):
                # 继续，但只答新词
                new_word_objs = get_words_by_ids(new_unanswered)
                queue = new_word_objs
            else:
                click.echo("已退出考核模式。")
                return
        else:
            click.echo(f"已达到今日测试上限（已测试 {daily_tested} / {daily_limit} 题）。")
            return
    elif daily_limit:
        remaining = daily_limit - daily_tested
        queue = queue[:remaining]

    if not queue:
        click.echo("今日考核已完成。")
        return

    total = len(queue)
    total_correct_count = 0
    total_wrong_count = 0

    # 已实际回答的单词 ID（用于崩溃恢复）
    answered_ids = []

    click.echo("== 考核模式 ==")
    click.echo(f"共 {total} 个单词")
    click.echo("提示：持续循环直到所有单词都答对才结束（可随时按 'q' 退出）\n")

    # 持续循环直到所有单词都答对
    round_num = 1
    while queue:
        click.echo(f"\n{'='*50}")
        click.echo(f"第 {round_num} 轮：剩余 {len(queue)} 个单词")
        click.echo('='*50)

        wrong_words = []

        # 当前轮次的测试
        for idx, word in enumerate(queue, 1):
            click.clear()
            click.echo(f"== 考核模式 · 第 {round_num} 轮 · 第 {idx} / {len(queue)} 题 ==")
            click.echo("-" * 50)
            click.echo(f"\n  释义：{word.meaning if word.meaning else '（无释义）'}")
            answer = click.prompt("\n  请输入英文（或 'q' 退出）", default="", show_default=False).strip()

            if answer.lower() == 'q':
                click.echo(f"\n已退出考核模式。")
                save_test_progress(answered_ids)
                # 显示统计
                if total_correct_count + total_wrong_count > 0:
                    click.echo()
                    click.echo("=" * 50)
                    total_answered = total_correct_count + total_wrong_count
                    accuracy = f"{total_correct_count*100//total_answered}%" if total_answered else "N/A"
                    click.echo(f"本次统计：共答题 {total_answered} 次，正确 {total_correct_count}，错误 {total_wrong_count}，正确率 {accuracy}")
                    click.echo("=" * 50)
                return

            if answer.lower() == word.word.lower():
                update_record(word.id, is_correct=True)
                total_correct_count += 1
                answered_ids.append(word.id)
                click.echo(f"\n  [正确] {word.word}")
                if word.phonetic:
                    click.echo(f"  {word.phonetic}")
            else:
                update_record(word.id, is_correct=False)
                total_wrong_count += 1
                answered_ids.append(word.id)
                click.echo(f"\n  [错误] 正确答案：{word.word}")
                if word.phonetic:
                    click.echo(f"  {word.phonetic}")
                if word.audio_url:
                    play_audio(word.audio_url)
                if word.meaning:
                    click.echo(f"  释义：{word.meaning}")
                wrong_words.append(word)

                time.sleep(1.5)  # 给时间阅读正确答案

            click.echo("-" * 50)

        # 更新队列：只保留答错的单词进入下一轮
        queue = wrong_words
        round_num += 1

    # 所有单词都答对了
    # 保存最终进度（已实际回答的词）并更新每日测试计数
    daily_tested_today = daily_tested + len(answered_ids)
    save_test_progress(answered_ids, daily_test_count=daily_tested_today)

    # 统计
    click.echo()
    click.echo("=" * 50)
    click.echo("🎉 恭喜！所有单词都答对了！")
    total_answered = total_correct_count + total_wrong_count
    accuracy = f"{total_correct_count*100//total_answered}%" if total_answered else "N/A"
    click.echo(f"本次统计：共答题 {total_answered} 次，正确 {total_correct_count}，错误 {total_wrong_count}，正确率 {accuracy}")
    click.echo(f"完成轮次：{round_num - 1} 轮")
    click.echo("=" * 50)


@cli.command('del')
@click.argument('words', nargs=-1, required=True)
def delete(words):
    """删除词表中指定的单词。

    用法: myvoc del word1 word2 word3
    """
    from myvoc.dao import _conn, get_word

    conn = _conn()
    deleted = []
    not_found = []

    for word in words:
        w = get_word(word)
        if w:
            # 先删除从表数据（避免外键约束失败）
            conn.execute("DELETE FROM learning_records WHERE word_id = ?", (w.id,))

            # 从 daily_sessions.word_ids 中移除该 ID
            rows = conn.execute(
                "SELECT id, word_ids FROM daily_sessions"
            ).fetchall()
            for row in rows:
                ids = json.loads(row["word_ids"] or "[]")
                if w.id in ids:
                    ids.remove(w.id)
                    conn.execute(
                        "UPDATE daily_sessions SET word_ids = ? WHERE id = ?",
                        (json.dumps(ids), row["id"]),
                    )

            conn.execute("DELETE FROM words WHERE id = ?", (w.id,))
            conn.commit()
            deleted.append(word)
        else:
            not_found.append(word)

    click.echo(f"删除完成：成功 {len(deleted)} 个" +
               (f"，未找到 {len(not_found)} 个" if not_found else ""))
    if deleted:
        click.echo(f"  已删除：{', '.join(deleted)}")
    if not_found:
        click.echo(f"  未找到：{', '.join(not_found)}")


@cli.command()
@click.option("--count", type=int, default=None, help="只补全前 N 个单词")
@click.option("-f", "--force", is_flag=True, help="强制处理所有单词（默认只处理今天新添加的）")
def addaudio(count: int | None, force: bool) -> None:
    """补全单词的音频 URL 及音标

    默认只补全今天新添加的单词，使用 -f 参数强制处理所有单词。

    用法:
      myvoc addaudio               # 只补全今天的新词
      myvoc addaudio -f            # 补全所有单词
      myvoc addaudio --count 10    # 只补全前 10 个（从今天新词开始）
      myvoc addaudio -f --count 10 # 强制模式下只补全前 10 个
    """
    from myvoc.dao import get_all_words, update_audio_url, update_word_phonetic
    from myvoc.dictionary import fetch_audio_url
    from datetime import date
    import time

    words = get_all_words()

    # 如果不是强制模式，只处理今天新添加的单词
    if not force:
        today = date.today().isoformat()
        words = [w for w in words if w.created_at and w.created_at.startswith(today)]
        if not words:
            click.echo("今天没有新添加的单词，使用 -f 参数处理所有单词")
            return

    if count:
        words = words[:count]

    total = len(words)
    ok_count = 0
    skip_count = 0
    fail_count = 0

    mode_label = "全部单词" if force else "今天新词"
    click.echo(f"== 音频补全模式 ({mode_label}) ==")
    click.echo()

    for idx, word in enumerate(words, 1):
        click.echo(f"[{idx}/{total}] {word.word:<15} ", nl=False)

        # 已有音频则跳过
        if word.audio_url:
            click.echo("[SKIP] 已有音频")
            skip_count += 1
            continue

        # 词组（含空格）跳过音频查询
        if ' ' in word.word:
            click.echo("[SKIP] 词组跳过")
            skip_count += 1
            continue

        # 查询 API
        result = fetch_audio_url(word.word)
        if result:
            update_audio_url(word.word, result["audio_url"])
            click.echo("[OK]")
            ok_count += 1

            if result["phonetic"]:
                update_word_phonetic(word.word, result["phonetic"])
        else:
            click.echo("[FAIL] 未找到")
            fail_count += 1

        # 控制请求频率（0.5 秒间隔）
        time.sleep(0.5)

    # 统计
    click.echo()
    click.echo("=" * 40)
    click.echo(f"补全完成：成功 {ok_count}，跳过 {skip_count}，失败 {fail_count}")
    click.echo("=" * 40)


# ---------------------------------------------------------------------------
# 系统状态
# ---------------------------------------------------------------------------


def _print_srs_intro(console: "Console") -> None:
    """打印艾宾浩斯 SRS 方法介绍"""
    console.print("\n[dim]" + "-" * 52 + "[/dim]")
    console.print("[bold]记忆方法：艾宾浩斯间隔重复（SRS）[/bold]\n")

    console.print("  德国心理学家艾宾浩斯发现：遗忘在学习后立即开始，")
    console.print("  且最初速度很快。间隔重复（Spaced Repetition System）")
    console.print("  利用这一规律，在即将遗忘的临界点安排复习，从而")
    console.print("  以最少次数把短期记忆转为长期记忆。\n")

    console.print("[bold]当前系统的 SRS 参数：[/bold]")
    from myvoc.config import get
    base_intervals = get("ebbinghaus.base_intervals", [0, 1, 2, 4, 7, 15, 30])
    max_stage = get("ebbinghaus.max_stage", 7)
    ease_lower = 1.3

    console.print("  * 阶段 0（新词）-> 今天复习")
    for i in range(1, len(base_intervals)):
        console.print(f"  * 阶段 {i} -> 间隔 {base_intervals[i]} 天复习")
    console.print(f"  * 最大阶段：{max_stage}（达到后视为已毕业）")
    console.print(f"  * 难度下限：ease factor {ease_lower}\n")

    console.print("[bold]每次考核的影响：[/bold]")
    console.print("  答对 -> 进入下一阶段，间隔按 base_intervals 递增")
    console.print("  答错 -> 退回 2 个阶段，难度系数 -0.2（下次间隔变短）")
    console.print("  难度系数越小，复习间隔越短，系统会更频繁地考你\n")

    console.print("[bold]给你的学习建议：[/bold]")
    console.print("  1. 每天坚持，不要积累大量到期单词 — 每天少量复习效果最好")
    console.print("  2. 答错了不要沮丧，退回 2 阶意味着系统认为你需要更多练习")
    console.print("  3. 如果某个词反复出错，尝试联想记忆法（编故事、拆词根）")
    console.print("  4. 录入新词时尽量用完整释义，避免只记片段的浅层记忆")
    console.print("  5. 用 [cyan]myvoc status[/cyan] 定期查看学习状态，及时调整节奏")


@cli.command()
def status() -> None:
    """查看当前学习状态统计

    显示词汇概况、阶段分布、常错词、到期复习提醒，
    以及艾宾浩斯间隔重复方法说明。
    """
    from datetime import date
    from myvoc.database import init_db
    from rich.console import Console
    from rich.table import Table

    console = Console()
    conn = init_db()

    # ========================= 1. 系统概览 =========================
    total_words = conn.execute("SELECT COUNT(*) AS cnt FROM words").fetchone()["cnt"]
    today_str = date.today().isoformat()
    session = conn.execute(
        "SELECT * FROM daily_sessions WHERE session_date = ?", (today_str,)
    ).fetchone()
    total_records = conn.execute("SELECT COUNT(*) AS cnt FROM learning_records").fetchone()["cnt"]
    total_sessions = conn.execute("SELECT COUNT(*) AS cnt FROM daily_sessions").fetchone()["cnt"]

    console.rule("[bold]系统概览[/bold]")
    console.print(f"  总词汇量：[bold]{total_words}[/bold] 个")
    console.print(f"  今日录入：[bold]{session['total_words'] if session else 0}[/bold] 个")
    console.print(f"  学习记录：[bold]{total_records}[/bold] 条")
    console.print(f"  学习会话：[bold]{total_sessions}[/bold] 次")

    # ========================= 2. 阶段分布 =========================
    console.print()
    console.rule("[bold]阶段分布[/bold]")

    stage_rows = conn.execute(
        "SELECT stage, COUNT(*) AS cnt FROM learning_records GROUP BY stage ORDER BY stage"
    ).fetchall()

    stage_labels = [
        "新词（阶段 0）",
        "1 天后复习",
        "2 天后复习",
        "4 天后复习",
        "7 天后复习",
        "15 天后复习",
        "30 天后复习",
        "已毕业",
    ]

    stage_map = {r["stage"]: r["cnt"] for r in stage_rows}
    stages_displayed = []
    for i in range(len(stage_labels)):
        cnt = stage_map.get(i, 0)
        stages_displayed.append(f"[{i}] {cnt} 个")
    console.print("  ".join(stages_displayed))

    # 未进入学习记录的单词数
    learned_ids = conn.execute(
        "SELECT DISTINCT word_id FROM learning_records"
    ).fetchall()
    learned_set = {r["word_id"] for r in learned_ids}
    if len(learned_set) < total_words:
        unlearned = total_words - len(learned_set)
        console.print(f"  未开始学习：[bold]{unlearned}[/bold] 个\n")

    # ========================= 3. 到期复习 & 新词 =========================
    console.rule("[bold]复习提醒[/bold]")

    overdue_rows = conn.execute(
        """SELECT COUNT(*) AS cnt FROM learning_records
           WHERE next_review_date <= ?""", (today_str,)
    ).fetchone()

    # 新词 = 今日会话中但无学习记录的
    new_count = 0
    if session:
        new_ids = session["word_ids"] or []
        if new_ids:
            reviewed = conn.execute(
                f"SELECT DISTINCT word_id FROM learning_records "
                f"WHERE word_id IN ({','.join('?' * len(new_ids))})",
                new_ids,
            ).fetchall()
            reviewed_set = {r["word_id"] for r in reviewed}
            new_count = len([wid for wid in new_ids if wid not in reviewed_set])
        else:
            new_count = 0

    console.print(f"  到期需复习：[bold]{overdue_rows['cnt']}[/bold] 个")
    console.print(f"  新词待学：  [bold]{new_count}[/bold] 个\n")

    # ========================= 4. 最常错的词 =========================
    console.rule("[bold]最常错的词 TOP 30（累计错误次数最多）[/bold]")

    top_wrong_rows = conn.execute(
        """SELECT w.word, w.meaning, lr.wrong_count, lr.correct_count
           FROM learning_records lr
           JOIN words w ON lr.word_id = w.id
           WHERE lr.wrong_count > 0
           ORDER BY lr.wrong_count DESC
           LIMIT 30"""
    ).fetchall()

    if not top_wrong_rows:
        console.print("  [dim]暂无数据，先学习一些单词吧![/dim]\n")
    else:
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("#", style="dim", width=4)
        table.add_column("单词", style="bold", max_width=15)
        table.add_column("释义", max_width=35)
        table.add_column("错误", justify="right", style="red")
        table.add_column("正确", justify="right", style="green")
        for idx, r in enumerate(top_wrong_rows, 1):
            wc = r["wrong_count"]
            cc = r["correct_count"]
            ratio = f"{cc * 100 // (cc + wc)}%" if (cc + wc) > 0 else "—"
            meaning = (r["meaning"] or "（无释义）").replace("\n", " ")
            table.add_row(
                str(idx),
                r["word"],
                meaning[:35],
                f"[red]{wc}[/red]",
                f"[green]{cc} ({ratio})[/green]",
            )
        console.print(table)

    # ========================= 5. 最新错的词 =========================
    console.print()
    console.rule("[bold]最新错的词 TOP 30（最近答错过）[/bold]")

    recent_wrong_rows = conn.execute(
        """SELECT w.word, w.meaning, lr.wrong_count, lr.correct_count,
                  lr.last_result, lr.last_review_at
           FROM learning_records lr
           JOIN words w ON lr.word_id = w.id
           WHERE lr.last_result = 'wrong'
           ORDER BY lr.last_review_at DESC
           LIMIT 30"""
    ).fetchall()

    if not recent_wrong_rows:
        console.print("  [dim]暂无数据，多练习几轮再来看![/dim]\n")
    else:
        table = Table(show_header=True, header_style="bold", box=None)
        table.add_column("#", style="dim", width=4)
        table.add_column("单词", style="bold", max_width=15)
        table.add_column("释义", max_width=30)
        table.add_column("累计错", justify="right", style="red")
        table.add_column("累计对", justify="right", style="green")
        table.add_column("正确率", justify="right", width=7)
        table.add_column("最近错", justify="right", max_width=12)
        for idx, r in enumerate(recent_wrong_rows, 1):
            cc = r["correct_count"]
            wc = r["wrong_count"]
            pct = f"{cc * 100 // (cc + wc)}%" if (cc + wc) > 0 else "—"
            color = "red" if (cc + wc) > 0 and cc / (cc + wc) < 0.5 else ("yellow" if (cc + wc) > 0 and cc / (cc + wc) < 0.8 else "green")
            meaning = (r["meaning"] or "（无释义）").replace("\n", " ")
            last_at = r["last_review_at"]
            if last_at:
                # 只显示日期部分，截取前10字符（YYYY-MM-DD HH:MM:SS -> YYYY-MM-DD）
                last_at_display = last_at[:10]
            else:
                last_at_display = "—"
            table.add_row(
                str(idx),
                r["word"],
                meaning[:30],
                f"[red]{wc}[/red]",
                f"[green]{cc}[/green]",
                f"[{color}]{pct}[/{color}]",
                last_at_display,
            )
        console.print(table)

    # ========================= 6. 到期单词列表 =========================
    if overdue_rows["cnt"] > 0:
        console.print()
        console.rule("[bold]到期待复习的单词")
        max_show = 20
        review_words = conn.execute(
            """SELECT w.word, w.meaning, lr.stage, lr.next_review_date
               FROM learning_records lr
               JOIN words w ON lr.word_id = w.id
               WHERE lr.next_review_date <= ?
               ORDER BY lr.stage ASC, lr.next_review_date ASC
               LIMIT ?""",
            (today_str, max_show),
        ).fetchall()

        if len(review_words) > max_show:
            console.print(f"  共 {overdue_rows['cnt']} 个到期，仅显示前 {max_show} 个：\n")
        for r in review_words:
            stage_label = stage_labels[r["stage"]] if r["stage"] < len(stage_labels) else f"阶段 {r['stage']}"
            meaning = (r["meaning"] or "")[:25]
            console.print(f"  [bold]{r['word']}[/bold]  {stage_label}  [{meaning}]")

    # ========================= 7. 艾宾浩斯方法介绍 =========================
    console.print()
    _print_srs_intro(console)


# ---------------------------------------------------------------------------
# 数据库备份 / 恢复
# ---------------------------------------------------------------------------


@cli.command("backup-db")
@click.option("--out", "output_path", type=click.Path(), default=None,
              help="指定输出文件路径 (默认: db/backup_YYYY-MM-DD.sql)")
def backup_db(output_path: str | None) -> None:
    """将整个单词库备份为 SQL 脚本

    默认备份到 db/backup_YYYY-MM-DD.sql。
    使用 myvoc restore-db 可以从此备份恢复。
    """
    from myvoc.database import init_db
    from pathlib import Path

    if output_path:
        # 自定义输出路径
        conn = init_db()
        p = Path(output_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            with p.open("w", encoding="utf-8") as f:
                for line in conn.iterdump():
                    f.write(line + "\n")
        except Exception as exc:
            click.echo(f"[FAIL] 备份失败: {exc}")
            conn.close()
            return

        # 统计
        word_count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        record_count = conn.execute("SELECT COUNT(*) FROM learning_records").fetchone()[0]
        session_count = conn.execute("SELECT COUNT(*) FROM daily_sessions").fetchone()[0]
        conn.close()

        click.echo(f"[OK] 数据库已备份: {p}")
        click.echo(f"     单词 {word_count} 个, 学习记录 {record_count} 条, 会话 {session_count} 次")
    else:
        from myvoc.backup import backup_db as _backup
        _backup()


@cli.command("restore-db")
@click.option("--force", is_flag=True, help="跳过确认直接恢复")
@click.option("--file", "restore_file", type=click.Path(), default=None,
              help="指定备份文件路径（与 --select 互斥）")
@click.option("--select", "select_idx", type=int, default=None,
              help="指定恢复的备份序号（1-based），配合 --force 可完全非交互式恢复")
def restore_db(force: bool, restore_file: str | None, select_idx: int | None) -> None:
    """从 SQL 备份文件恢复数据库

    列出 db/ 目录下的所有备份文件，选择后恢复。
    恢复会覆盖当前数据库，请谨慎操作。

    配合 --select 和 --force 可完全非交互式恢复:
      myvoc restore-db --select 1 --force

    使用 --file 指定任意备份文件路径直接恢复:
      myvoc restore-db --file /path/to/backup.sql --force
    """
    from myvoc.backup import restore_db as _restore

    if restore_file and select_idx is not None:
        click.echo("[ERROR] --file 和 --select 只能指定一个")
        return

    _restore(force=force, select_idx=select_idx, restore_file=restore_file)
