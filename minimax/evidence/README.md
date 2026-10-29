# 实测证据索引

所有内容为本机真实执行输出或明确标识的文档来源；没有真实 MiniMax 生成记录。

- `environment.json`：独立运行依赖、真实数据库版本、官方基线和本任务分支。
- `module-tests-command.json`、`module-tests.txt`：最终源码的 44 项模块测试通过，包含真实 seekdb 与 PowerContext 测试；MiniMax 测试使用明确标识的 fixture。
- `stage-a/`：第一次完整阶段 A 的实际输入/输出、子进程命令及退出码。`context-v1.json` → `context-v2.json` 验证规格更新，`state-written.json` → `context-restored.json` 验证跨进程状态复用。
- `stage-a/baseline/`：固定业务测试原始 stdout/stderr/JUnit 与命令、代码及测试哈希；目标 20 项失败是初始版本未实现功能的证据。
- `reproduction/`：新的源文件目录、新虚拟环境和新数据库中的安装与重跑。`verification.json` 对照最终全部 21 个运行源码、测试、规格及锁定依赖文件的哈希，全部相同；`run/report.json` 为最终复现报告。
- `missing-config.json`：仓库外配置缺失时退出 2，未创建客户端、未发送请求。
- `push-preflight.json`：origin 正确，但 GitHub HTTPS 认证不可用，未推送。
- `task-requirements.md`、`protocol-sources.md`、`powercontext-design.md`：题面、协议及 SDK 用法依据。

日志保留真实执行时的绝对路径、PID、artifact ID 和时间。复制到仓库后的 JSON 中路径指向原运行位置，源码和对应日志也随作品交付；新环境重跑会产生新的路径及 ID。原始 pytest 日志中的诊断空白保留，没有改写失败输出。

`reproduction/install.txt` 是同一新虚拟环境的首次锁定安装记录；最终复现使用 `.runs/demo-final` 的新数据目录。Python 依赖下载使用 uv 下载缓存，数据库和 PowerContext 状态从空目录重新建立，未复制任何数据库或状态缓存。最终 44 项模块测试与最后一次阶段 A 使用相同源码。
