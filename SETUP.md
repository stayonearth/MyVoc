# MyVoc 初始化指南

## 快速开始

### 1. 安装依赖

```bash
pip install -e .
```

这会安装以下核心依赖：
- `click>=8.0` - 命令行框架
- `rich>=13.0` - 终端美化输出
- `appdirs>=1.4.4` - 跨平台应用数据目录

### 2. （可选）安装音频播放功能

```bash
pip install -e ".[audio]"
```

如果不需要单词发音功能，可以跳过此步骤。

### 3. 开始使用

```bash
python -m myvoc add          # 录入单词
python -m myvoc learn        # 背诵模式
python -m myvoc test         # 考核模式
python -m myvoc status       # 查看学习状态
```

## 环境要求

- Python >= 3.8
- 数据库会自动创建在：`C:\Users\用户名\AppData\Local\myvoc\myvoc\myvoc.db`

## 命令说明

### 基础命令
- `add` - 录入单词（自动查询音标和释义）
- `learn` - 背诵模式（手动/自动两种节奏）
- `test` - 考核模式（看中文写英文）
- `del <单词>` - 删除单词
- `status` - 查看学习统计

### 音频补全（优化版）
- `addaudio` - 只补全今天新添加的单词（推荐日常使用）
- `addaudio -f` - 强制补全所有单词（首次使用或需要全面补全时）

**使用建议**：每天录入新词后运行 `python -m myvoc addaudio` 即可，速度快且不会重复处理。

### 数据库备份
- `backup-db` - 备份数据库到 `db/` 目录
- `restore-db` - 从备份恢复数据库

## 配置文件

配置文件：`config.json`

详细配置说明见 [使用说明.md](使用说明.md)

## 更新日志

### 2026-08-27 优化
1. 修复 pyproject.toml 构建配置错误
2. 降低 Python 版本要求至 3.8+
3. 将音频播放改为可选依赖
4. 优化 `addaudio` 命令：默认只处理今天新词，节省时间
