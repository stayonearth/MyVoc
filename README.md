# MyVoc

命令行单词记忆训练工具，基于**艾宾浩斯遗忘曲线**智能调度复习。

详见：[使用说明.md](使用说明.md)

---

## 数据库恢复

项目根目录 `db/restore_db.sql` 保存了当前 SQLite 数据库的完整备份（含所有单词、学习记录和会话数据）。如果数据库文件损坏或表结构被改错，可通过此脚本恢复。

**恢复步骤：**

```bash
# 确认数据库文件路径
python -c "from myvoc.database import get_db_path; print(get_db_path())"

# 执行恢复
sqlite3 <数据库路径> < db/restore_db.sql
```

**示例：**

```bash
sqlite3 "C:\Users\fly2M\AppData\Local\myvoc\myvoc\myvoc.db" < db/restore_db.sql
```

恢复完成后重新启动程序即可，数据与原库完全一致。建议数据有重要变动后重新导出备份。
