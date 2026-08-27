# MyVoc

**基于艾宾浩斯遗忘曲线的命令行单词记忆工具**

一款智能的词汇学习 CLI 工具，通过科学的间隔重复算法（SRS）帮助你高效记忆单词。

## ✨ 核心特性

- 📚 **智能词典** - 自动查询音标、释义，支持手动补充
- 🧠 **艾宾浩斯 SRS** - 科学安排复习间隔，在遗忘临界点提醒
- ✅ **自动错题重测** - 答错的单词自动加入本轮重测队列
- 🎯 **双模式学习** - 背诵模式（被动记忆）+ 考核模式（主动回忆）
- 💾 **数据本地化** - SQLite 存储，支持备份与恢复
- 🎨 **友好界面** - Rich 驱动的美观终端输出

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd MyVoc

# 安装依赖
pip install -e .

# （可选）安装音频播放功能
pip install -e ".[audio]"
```

### 基础使用

```bash
# 1. 录入单词
python -m myvoc add

# 2. 背诵学习
python -m myvoc learn

# 3. 考核测试
python -m myvoc test

# 4. 查看学习状态
python -m myvoc status
```

## 📖 主要命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `add` | 录入单词（逐行输入，自动查词） | `myvoc add` |
| `learn` | 背诵模式（显示单词、音标、释义） | `myvoc learn --auto` |
| `test` | 考核模式（看中文写英文） | `myvoc test --count 20` |
| `del` | 删除单词 | `myvoc del abandon ability` |
| `addaudio` | 补全音频（默认只处理今天新词） | `myvoc addaudio -f` |
| `status` | 学习统计（词汇量、错词、到期复习） | `myvoc status` |
| `backup-db` | 备份数据库 | `myvoc backup-db` |
| `restore-db` | 恢复数据库 | `myvoc restore-db` |

## 📊 艾宾浩斯 SRS 原理

系统根据记忆曲线自动调度复习：

```
阶段 0（新词）→ 当天复习
阶段 1 → 1 天后
阶段 2 → 2 天后
阶段 3 → 4 天后
阶段 4 → 7 天后
阶段 5 → 15 天后
阶段 6 → 30 天后
```

- ✅ **答对**：进入下一阶段，间隔延长
- ❌ **答错**：退回 2 个阶段，增加练习频率

## 🛠️ 环境要求

- Python >= 3.8
- SQLite 3（内置）
- Windows / macOS / Linux

## 📁 数据存储

- **数据库**：`%LOCALAPPDATA%\myvoc\myvoc\myvoc.db` (Windows)
- **配置**：`config.json`（项目根目录）
- **备份**：`db/backup_YYYY-MM-DD.sql`

## 📚 详细文档

- [使用说明](使用说明.md) - 完整功能说明
- [需求文档](需求.md) - 设计思路与需求分析
- [音频配置](addaudio.md) - 音频功能配置指南

## 🔧 故障排查

### 数据库恢复

如果数据库损坏，可从备份恢复：

```bash
python -m myvoc restore-db
```

或手动指定备份文件：

```bash
python -m myvoc restore-db --file db/backup_2026-08-27.sql --force
```

## 📝 配置示例

编辑 `config.json` 自定义行为：

```json
{
  "learning": {
    "auto_mode": false,
    "auto_interval_seconds": 5,
    "show_phonetic": true
  },
  "testing": {
    "case_sensitive": false,
    "typo_tolerance": 0
  },
  "ebbinghaus": {
    "base_intervals": [0, 1, 2, 4, 7, 15, 30],
    "max_stage": 7
  }
}
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
