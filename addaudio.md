# addaudio 命令实现说明

## 功能

为数据库中的单词批量补全**音标**和**音频 URL**。

## 用法

```bash
# 补全所有单词
python -m myvoc addaudio

# 只补全前 N 个
python -m myvoc addaudio --count 10

# 同时补全音标
python -m myvoc addaudio --phonetic
```

## 实现方法

### 核心方案：混合 API

| 字段 | 来源 | 说明 |
|------|------|------|
| 音标 | Free Dictionary API | `api.dictionaryapi.dev` 返回 IPA 音标 |
| 音频 URL | Youdao TTS | 拼接固定格式的 URL，无需请求 API |

### 音频 URL 为什么直接拼接

Free Dictionary API 的音频托管已下线（返回 502），但其音标数据仍然可用。
Youdao TTS 的音频 URL 格式固定且稳定，可直接拼接：

```
https://dict.youdao.com/dictvoice?audio=<word>&type=0   # 美式
https://dict.youdao.com/dictvoice?audio=<word>&type=1   # 英式
```

实测验证：
- `curl -I "https://dict.youdao.com/dictvoice?audio=abandon&type=0"` → `200 audio/mpeg`
- 返回 MP3 格式，可直接播放

### 代码结构

**1. dictionary.py**

```python
PHONETIC_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
YOUDAO_TTS_URL_US = "https://dict.youdao.com/dictvoice?audio={word}&type=0"

def fetch_audio_url(word: str) -> dict | None:
    """混合方案：音标来自 Free Dictionary API，音频 URL 拼接 Youdao TTS"""
```

实现逻辑：
1. 请求 Free Dictionary API 获取音标
2. 遍历 `phonetics` 数组找到第一个有 `text` 的条目
3. 音频 URL 直接用 Youdao TTS 格式拼接，无需请求

**2. dao.py**

新增 3 个函数：
- `get_all_words()` — 获取所有单词
- `update_audio_url(word, audio_url)` — 更新音频 URL
- `update_word_phonetic(word, phonetic)` — 更新音标

**3. cli.py**

`addaudio` 命令：
1. 获取所有单词，按 `--count` 限制
2. 遍历：已有音频 → SKIP；查询成功 → OK；失败 → FAIL
3. 每请求间隔 0.5 秒
4. `--phonetic` 可选同时更新音标
5. 末尾输出统计

## 数据存储

### 音标存储

| 字段 | 说明 |
|------|------|
| 列名 | `words.phonetic` |
| 格式 | IPA 国际音标字符串 |
| 示例 | `/əˈbændən/`、`/əˈbɪləti/` |
| 长度 | 通常 6-15 字符 |
| 编码 | UTF-8（含 Unicode 音标字符） |

### 音频存储

| 字段 | 说明 |
|------|------|
| 列名 | `words.audio_url` |
| 格式 | 完整 HTTPS URL 字符串 |
| 示例 | `https://dict.youdao.com/dictvoice?audio=abandon&type=0` |
| 格式类型 | MP3（`audio/mpeg`） |
| type 参数 | `0`=美式，`1`=英式 |

### 音频是否可播放

✅ **可播放**。Youdao TTS 返回 `Content-Type: audio/mpeg`，URL 可直接用于：
- 浏览器打开播放
- `curl -o audio.mp3 <URL>` 下载
- 程序中使用音频库播放

## API 详情

### Free Dictionary API（音标）

- **URL**：`https://api.dictionaryapi.dev/api/v2/entries/en/{word}`
- **返回格式**：JSON 数组
- **成功**：`[{ "word": "abandon", "phonetics": [...] }]`
- **失败**：`{ "title": "No Definitions Found", "message": "..." }`
- **音标来源**：`entry.phonetic` 或 `entry.phonetics[].text`
- **注意**：顶部 `phonetic` 字段可能为空，应从 `phonetics` 数组取
- **无音频托管**：`phonetics[].audio` 字段已下线（502），只取音标

### Youdao TTS（音频 URL）

- **URL 格式**：`https://dict.youdao.com/dictvoice?audio={word}&type={0|1}`
- **无需请求**：直接拼接 URL 存储，播放时再请求
- **返回类型**：`audio/mpeg`（MP3）
- **type 参数**：`0` = 美式发音，`1` = 英式发音
- **稳定可靠**：200 OK，长期可用

## 测试结果

| 指标 | 结果 |
|------|------|
| 总单词数 | 84 |
| 成功 | 67（80%） |
| 跳过（已有音频）| 3 |
| 失败 | 14 |

### 失败原因

- **网络错误**：SSL 握手超时、HTTP 502/500
- **词不在词典中**：拼写错误（`criminial`）、生造词（`danager`）、复合词（`daytime`）

## 注意事项

1. 网络依赖：音标查询需访问 `api.dictionaryapi.dev`
2. 速率控制：每请求间隔 0.5 秒，84 词约 42 秒
3. 失败可重试：网络超时可重新运行补漏
4. 部分词查不到：拼写错误、生造词不在词典中
