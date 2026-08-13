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

    click.echo("[录入模式] 输入完成后按 Ctrl+D (Unix) / Ctrl+Z (Windows) 结束")
    click.echo("-" * 50)

    added = []
    failed = []
    manual_added = []

    # 逐行读取 stdin
    for line in sys.stdin:
        words_text = line.strip()
        if not words_text:
            continue

        for raw_word in words_text.split():
            word = raw_word.strip().lower()
            if not word:
                continue

            # 查词
            info = lookup_word(word)
            if info:
                upsert_word(word, info["phonetic"], info["meaning"])
                added.append(word)
                click.echo(f"  [OK] {word}  {info['phonetic']}  {info['meaning']}")
            else:
                meaning = click.prompt(f"  [{word}] 未查询到释义，请手动输入中文释义", default="")
                if meaning:
                    upsert_word(word, "", meaning, source="manual")
                    added.append(word)
                    manual_added.append(word)
                    click.echo(f"  [OK] {word}  (手动)  {meaning}")
                elif not skip_unknown:
                    failed.append(word)
                    click.echo(f"  [SKIP] {word}（未提供释义且 --skip-unknown 未设置）")

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


@cli.command()
@click.option("--auto", is_flag=True, help="自动模式：每个单词显示指定时长后自动切换")
@click.option("--count", type=int, default=None, help="只背诵前 N 个单词")
def learn(auto: bool, count: int | None) -> None:
    """背诵模式：依次显示单词的英文、音标、中文释义"""
    from myvoc.dao import get_today_session, get_words_by_ids
    from myvoc.config import get as conf_get
    import time

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
    click.echo(f"== 背诵模式 · {mode_text} · 第 1 / {total} 个 ==")
    click.echo()

    auto_interval = conf_get("learning.auto_interval_seconds", 5)

    for idx, word in enumerate(words, 1):
        click.clear()
        click.echo(f"== 背诵模式 · {mode_text} · 第 {idx} / {total} 个 ==")
        click.echo("-" * 40)
        click.echo(f"\n  {word.word}")
        if word.phonetic:
            click.echo(f"  {word.phonetic}")
        if word.meaning:
            click.echo(f"\n  {word.meaning}")
        else:
            click.echo(f"\n  （无释义）")
        click.echo("-" * 40)

        if auto:
            click.echo(f"[{auto_interval}秒后自动切换] [q] 退出")
            try:
                time.sleep(auto_interval)
            except KeyboardInterrupt:
                click.echo("\n已退出背诵模式。")
                return
        else:
            click.echo("[回车] 下一个  [q] 退出")
            key = click.prompt("", default="", show_default=False).strip()
            if key.lower() == 'q':
                click.echo("已退出背诵模式。")
                return


@cli.command()
@click.option("--count", type=int, default=None, help="只考核前 N 个单词")
def test(count: int | None) -> None:
    """考核模式：显示中文释义，输入英文单词作答

    答对 -> stage+1，更新复习间隔
    答错 -> stage-2，难度系数降低
    """
    from myvoc.dao import get_test_queue, update_record

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
        else:
            update_record(word.id, is_correct=False)
            wrong_count += 1
            click.echo(f"\n  [错误] 正确答案：{word.word}")
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
            else:
                click.echo(f"\n  [错误] 正确答案：{word.word}")
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
