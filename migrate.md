日常开发里，加字段/改表时的命令顺序
以你现在这种“已经有迁移、已经有数据”的项目为例，一般按这套来：
1.先保证数据库是最新版本
flask --app app.http.app db upgrade
1.改模型代码
在 internal/model/app.py 里加/改字段，比如：
type = Column(String(255), default="", nullable=False)
1.生成迁移文件
flask --app app.http.app db migrate -m "add dataset"
1.手工检查并必要时修改迁移文件
- 找到刚生成的 internal/migration/versions/xxxx_add_type_to_app.py
- 如果是给已有表加 NOT NULL 字段，改成类似：
with op.batch_alter_table('app', schema=None) as batch_op:
    batch_op.add_column(
        sa.Column('type', sa.String(length=255), nullable=False, server_default='')
    )
    batch_op.alter_column('type', server_default=None)
1.再执行升级，把迁移真正落到数据库
flask --app app.http.app db upgrade

--------------------------------------------------------------------------------
特殊情况：刚拉项目/新建库时
1.第一次 init（你项目已经有了，可以忽略）
flask --app app.http.app db init
1.按上面那套流程做：migrate → 检查迁移 → upgrade。


先改数据库代码->migrate 生产迁移文件->upgrade


你改的是 app.py 里的字段，正确顺序一般是：
生成迁移（模型改了但还没有对应的迁移文件时，这一步不能省）
flask --app app.http.app db migrate -m "调整 app 表字段"
这会在 migrations/versions/ 里生成新的 revision 文件。
应用到数据库（只做一次即可）
flask --app app.http.app db upgrade
会把数据库从当前 revision 一直升到最新 head。
