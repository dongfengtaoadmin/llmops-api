# 数据库迁移开发指南

## 一、日常开发流程（加字段/改表）

适用于”已经有迁移、已经有数据”的项目。

### 步骤 1：保证数据库是最新版本

```bash
flask --app app.http.app db upgrade
```

### 步骤 2：修改模型代码

在 `internal/model/app.py` 里加/改字段，例如：

```python
type = Column(String(255), default=””, nullable=False)
```

### 步骤 3：生成迁移文件

```bash
flask --app app.http.app db migrate -m "add dataset"
```

### 步骤 4：手工检查并修改迁移文件

- 找到刚生成的 `internal/migration/versions/xxxx_add_type_to_app.py`
- 如果是给已有表加 `NOT NULL` 字段，需要使用 `server_default` 来处理已有数据：

```python
with op.batch_alter_table('app', schema=None) as batch_op:
    batch_op.add_column(
        sa.Column('type', sa.String(length=255), nullable=False, server_default='')
    )
    batch_op.alter_column('type', server_default=None)
```

### 步骤 5：执行升级

把迁移真正落到数据库：

```bash
flask --app app.http.app db upgrade
```

---

## 二、特殊情况：刚拉项目/新建库时

### 初始化（仅首次）

```bash
flask --app app.http.app db init
```

> 注意：你项目已经有了迁移，可以忽略这一步。

### 后续流程

按照上面的日常开发流程执行：**migrate → 检查迁移 → upgrade**

---

## 三、核心流程总结

```
修改模型代码 → 生成迁移文件 → 检查迁移文件 → 执行升级
```

**示例：调整 app 表字段**

```bash
# 1. 生成迁移（模型改了但还没有对应的迁移文件时，这一步不能省）
flask --app app.http.app db migrate -m “调整 app 表字段”

# 2. 应用到数据库（只做一次即可，会把数据库从当前 revision 升到最新 head）
flask --app app.http.app db upgrade
```
