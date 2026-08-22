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
    """录入单词：逐行输入英文单词，自动查词后入库

    每行可以输入多个单词（空格分隔），回车后逐个查词显示。
    按 Ctrl+D (Unix) / Ctrl+Z (Windows) 结束输入。
    """
    import sys
    from myvoc.dictionary import lookup_word
    from myvoc.dao import upsert_word, create_session
    from rich.console import Console
    from rich.status import Status

    console = Console()
    console.print("[录入模式] 输入完成后按 [cyan]Ctrl+Z[/cyan] (Windows) 或 [cyan]Ctrl+D[/cyan] (Unix) 结束")
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

        for raw_word in words_text.split():
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
@click.option("--count", type=int, default=None, help="只考核前 N 个单词")
def test(count: int | None) -> None:
    """考核模式：显示中文释义，输入英文单词作答

    答对 -> stage+1，更新复习间隔
    答错 -> stage-2，难度系数降低
    """
    from myvoc.dao import get_test_queue, update_record
    from myvoc.audio import play_audio

    queue = get_test_queue()
    if not queue:
        click.echo("今日没有待考核的单词，请先运行 `myvoc add` 录入单词。")
        return

    correct_count = 0
    wrong_count = 0
    total = len(queue)

    # 答错的单词收集起来，一轮结束后重测一次
    wrong_words = []

    click.echo("== 考核模式 ==")
    click.echo(f"共 {total} 个单词\n")

    # 主循环：正常队列
    idx = 1
    while queue:
        word = queue.pop(0)

        click.clear()
        click.echo(f"== 考核模式 · 第 {idx} / {total} 题 ==")
        click.echo("-" * 50)
        click.echo(f"\n  释义：{word.meaning if word.meaning else '（无释义）'}")
        answer = click.prompt("\n  请输入英文", default="", show_default=False).strip()

        if answer.lower() == 'q':
            click.echo(f"\n已退出考核模式。（答了 {idx - 1}/{total} 题）")
            return

        if answer.lower() == word.word.lower():
            update_record(word.id, is_correct=True)
            correct_count += 1
            click.echo(f"\n  [正确] {word.word}")
            if word.phonetic:
                click.echo(f"  {word.phonetic}")
        else:
            update_record(word.id, is_correct=False)
            wrong_count += 1
            click.echo(f"\n  [错误] 正确答案：{word.word}")
            if word.phonetic:
                click.echo(f"  {word.phonetic}")
            if word.audio_url:
                play_audio(word.audio_url)
            if word.meaning:
                click.echo(f"  释义：{word.meaning}")
            wrong_words.append(word)

        click.echo("-" * 50)
        idx += 1

    # 重测一轮答错的单词
    if wrong_words:
        click.echo(f"\n有 {len(wrong_words)} 个单词答错了，开始重测：")
        click.echo("=" * 50)

        for idx2, word in enumerate(wrong_words, 1):
            click.clear()
            click.echo(f"== 重测 · 第 {idx2} / {len(wrong_words)} 题 ==")
            click.echo("-" * 50)
            click.echo(f"\n  释义：{word.meaning if word.meaning else '（无释义）'}")
            answer = click.prompt("\n  请输入英文", default="", show_default=False).strip()

            if answer.lower() == 'q':
                click.echo(f"\n已退出重测。")
                break

            if answer.lower() == word.word.lower():
                click.echo(f"\n  [正确] {word.word}")
                if word.phonetic:
                    click.echo(f"  {word.phonetic}")
            else:
                click.echo(f"\n  [错误] 正确答案：{word.word}")
                if word.phonetic:
                    click.echo(f"  {word.phonetic}")
                if word.audio_url:
                    play_audio(word.audio_url)
                if word.meaning:
                    click.echo(f"  释义：{word.meaning}")
            click.echo("-" * 50)

    # 统计
    click.echo()
    click.echo("=" * 50)
    total_answered = correct_count + wrong_count
    accuracy = f"{correct_count*100//total_answered}%" if total_answered else "N/A"
    click.echo(f"考核完成：共 {total_answered} 题，正确 {correct_count}，错误 {wrong_count}，正确率 {accuracy}")
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
@click.option("--phonetic", is_flag=True, help="同时补全音标字段")
def addaudio(count: int | None, phonetic: bool) -> None:
    """补全单词的音频 URL（及可选的音标）

    用法:
      myvoc addaudio               # 补全所有单词
      myvoc addaudio --count 10    # 只补全前 10 个
      myvoc addaudio --phonetic    # 同时补全音标
    """
    from myvoc.dao import get_all_words, update_audio_url, update_word_phonetic
    from myvoc.dictionary import fetch_audio_url
    import time

    words = get_all_words()

    if count:
        words = words[:count]

    total = len(words)
    ok_count = 0
    skip_count = 0
    fail_count = 0

    click.echo("== 音频补全模式 ==")
    click.echo()

    for idx, word in enumerate(words, 1):
        click.echo(f"[{idx}/{total}] {word.word:<15} ", nl=False)

        # 已有音频则跳过
        if word.audio_url:
            click.echo("[SKIP] 已有音频")
            skip_count += 1
            continue

        # 查询 API
        result = fetch_audio_url(word.word)
        if result:
            update_audio_url(word.word, result["audio_url"])
            click.echo("[OK]")
            ok_count += 1

            if phonetic and result["phonetic"]:
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
