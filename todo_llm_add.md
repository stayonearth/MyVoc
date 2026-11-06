# LLM 增强词汇学习 — 实施方案

## Context

当前 MyVoc 依赖三个免费 API：
- **Youdao 释义 API**（`add` 命令用）— 成功率日益下降
- **Free Dictionary API**（`addaudio` 命令用）— 已 502 不可用
- **Youdao TTS URL** — 仅支持短词，短语处理不佳

用户已有本地 LLM（`qwen36-local`，OpenAI 兼容接口 `http://100.64.0.5:8000/v1`），需要：
1. 用 LLM 生成词汇的**音标**（替换 Free Dictionary API）+ **释义**（增强 Youdao API）+ **例句**（全新）
2. 用本地 TTS（piper-tts）生成语音，支持短语

决策：新增 `llm-add` 命令，不修改现有 `add` 命令；音频用 piper-tts 生成本地 MP3。

---

## 实施步骤

### Step 1: 数据库 — 添加 `example` 列

**文件**: `myvoc/database.py`

在 `init_db()` 函数的 `_create_tables(conn)` 之后，添加列迁移检查（复用已有的 `test_progress` 迁移模式）：

```python
cur = conn.execute("PRAGMA table_info(words)")
columns = {row[1] for row in cur.fetchall()}
if "example" not in columns:
    conn.execute("ALTER TABLE words ADD COLUMN example TEXT DEFAULT ''")
    conn.commit()
```

### Step 2: 数据模型 — 添加 `example` 字段

**文件**: `myvoc/models.py`

在 `Word` dataclass 中添加 `example` 字段：

```python
@dataclass
class Word:
    id: Optional[int] = None
    word: str = ""
    phonetic: str = ""
    meaning: str = ""
    example: str = ""           # NEW: 例句
    created_at: Optional[datetime] = None
    source: str = "api"
    audio_url: str = ""
```

### Step 3: DAO 层 — 扩展 upsert 和新增 update_example

**文件**: `myvoc/dao.py`

1. 扩展 `upsert_word()` 函数签名，添加 `example: str = ""` 参数
2. 修改 INSERT 语句，加入 `example` 列
3. 新增 `update_example(word, example)` 函数（复用 `update_word_phonetic` 模式）

### Step 4: 新建 LLM 词汇查询模块

**新文件**: `myvoc/llm.py`

功能：
- **`lookup_word_llm(word: str) -> dict | None`**: 调用 LLM 返回 `{phonetic, meaning, example}`
- **Prompt 模板**: 要求返回纯 JSON（无 markdown 包裹）
- **JSON 提取**: 处理 markdown code fence（```json ... ```）
- **Reasoning 模型兼容**: 同时读取 `message.content` 和 `message.reasoning`

```python
VOCABULARY_PROMPT = """你是中英双语词汇专家。

为以下单词/短语提供：
1. phonetic: IPA 音标（如 /əˈbændən/）
2. meaning: 中文释义（多个义项用分号分隔）
3. example: 一句英文例句 + 中文翻译

只返回 JSON，格式如下：
{{
  "phonetic": "/.../",
  "meaning": "义项1; 义项2",
  "example": "English example. 中文翻译。"
}}

不要返回其他文字或 markdown 标记。

Word: {word}"""
```

实现细节：
- 使用现有 `openai.OpenAI` 客户端（与 `status --analyze` 共用）
- `temperature=0.3`，`max_tokens=2000`
- 从 `config.get("llm.base_url")` 和 `config.get("llm.model")` 读取配置
- 失败返回 `None`

### Step 5: 音频模块 — 集成 piper-tts

**文件**: `myvoc/audio.py`

1. 添加 `generate_audio_piper(text: str, output_path: str) -> bool`: 使用 piper-tts 生成本地 MP3
2. 添加 `get_local_audio_path(word: str) -> str`: 生成安全的本地文件名（短语用 URL-safe 编码）
3. 修改 `_download_audio()`: 当 `audio_url` 是本地文件路径（已缓存）时直接返回，跳过网络下载

piper-tts 调用方式：
```python
import piper
# 生成 MP3 到文件
with open(output_path, "wb") as f:
    for chunk in piper.speak(text, voice="en_US-lessac-medium.onnx", output_format="mp3"):
        f.write(chunk)
```

### Step 6: CLI — 新增 `llm-add` 命令

**文件**: `myvoc/cli.py`

新增 `cli_add_llm()` 函数（约 150 行），逻辑：
1. 交互式输入单词（与 `add` 相同：逐行输入，Ctrl+D 结束）
2. 对每个词调用 `lookup_word_llm(word)`
3. 成功：存入数据库 `source="llm"`，用 piper-tts 生成本地音频
4. LLM 失败：降级到现有 `lookup_word()`（有道 API）
5. 有道也失败：手动输入释义（同现有行为）
6. 结束后显示统计（成功/失败/降级数量）

### Step 7: CLI — 新增 `enrich` 命令

**文件**: `myvoc/cli.py`

新增 `cli_enrich()` 函数，可选参数：
- `--words WORD ...` 指定词
- `--batch FILE` 从文件读词列表
- `--fields FIELDS` 选择性补全（`meaning`, `example`, `phonetic`）
- `--count N` 限制数量
- `--dry-run` 仅展示不写入

逻辑：对每个词调用 LLM，更新缺失的字段。失败则跳过并记录。

### Step 8: 依赖更新

**文件**: `pyproject.toml`

在 optional dependencies 中添加 `piper-tts`：
```toml
[project.optional-dependencies]
audio = [
    "pygame>=2.0.0",
    "piper-tts>=1.2.0",
]
```

---

## 关键文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `myvoc/database.py` | 修改 | 添加 `example` 列迁移 |
| `myvoc/models.py` | 修改 | `Word` dataclass 添加 `example` 字段 |
| `myvoc/dao.py` | 修改 | 扩展 `upsert_word`，新增 `update_example` |
| `myvoc/llm.py` | **新建** | LLM 词汇查询模块 |
| `myvoc/audio.py` | 修改 | 集成 piper-tts 音频生成 |
| `myvoc/cli.py` | 修改 | 新增 `llm-add` 和 `enrich` 命令 |
| `pyproject.toml` | 修改 | 添加 `piper-tts` 依赖 |

## 验证方式

1. `python -m myvoc llm-add` — 输入几个测试词（含短语），检查数据库中有无释义、例句、音频
2. `python -m myvoc enrich --words "abandon" "break down" "look into"` — 验证批量补全
3. `python -m myvoc learn` — 验证学习模式下音频播放（本地文件路径）
4. 验证 `add` 命令不受影响（向后兼容）
