# 本地验收对照

**六项条件已有本地运行证据；平台提测及官方评分尚未执行。** MiniMax 已真实参与状态筛选修改，初始与修改后使用同一份验收测试。官方要求六项全部通过才得 20 分，本地结果不保证官方得分。依据见[题面核对](evidence/task-requirements.md)。

| 官方必做项 | 当前本地状态 | 证据 |
| --- | --- | --- |
| 能够运行 | 已验证 | 新的源码目录、虚拟环境及数据范围中，完整 A→B 与新进程恢复均退出 0；[完整复现](evidence/stage-b/reproduction/)。 |
| MiniMax 实际参与 | 已验证 | `MiniMax-M3.1-Flash` 的[实际任务与上下文](evidence/stage-b/attempt-02/context.json)、[模型最终输出](evidence/stage-b/attempt-02/minimax-final-output.json)、[对应差异](evidence/stage-b/attempt-02/model.patch)。 |
| 上下文正确 | 已验证 | [v1](evidence/stage-a/context-v1.json) → [v2](evidence/stage-a/context-v2.json)，实际请求使用当前规格和必要代码/测试来源。 |
| 数据库实际参与 | 已验证 | [阶段 B 上下文](evidence/stage-b/attempt-02/context.json)包含真实 seekdb SQL、返回资料、版本和来源；修改后重新导入候选代码。 |
| 状态能够复用 | 已验证 | [阶段 A 恢复](evidence/stage-a/context-restored.json)选择模型调用；[阶段 B 新进程恢复](evidence/stage-b/restart-verification.json)读取 revision 4 并选择验收审查。 |
| 代码修改有效 | 已验证 | 修改前目标 20 项有效失败；修改后目标 20/20、回归 9/9 全部通过，0 errors、0 skipped，[固定测试哈希与结果](evidence/stage-b/tests-after/results.json)。 |

## 实际执行

| 命令/验证 | 结果 | 退出码 | 证据 |
| --- | --- | --- | --- |
| 阶段 A `uv run --locked pytest -q` | 44 passed，5 条上游弃用警告 | 0 | [原始模块日志](evidence/module-tests.txt) |
| `stage-a --run-dir .runs/stage-a` | 真实导入/检索、规格更新、初始测试与跨进程复用通过 | 0 | [阶段 A 报告](evidence/stage-a/report.json) |
| 初始回归 / 目标测试 | 9 passed / 20 项有效失败 | 0 / 1 | [初始结果](evidence/stage-a/baseline/results.json) |
| 首次真实 `stage-b` | 预检直连超时，未生成业务代码；请求尝试 1 次 | 1 | [失败记录](evidence/stage-b/attempt-01/report.json) |
| 代理修复后真实 `stage-b` | 真实预检和生成成功；目标 20/20、回归 9/9 | 0 | [执行命令](evidence/stage-b/attempt-02/command.json)、[报告](evidence/stage-b/attempt-02/report.json) |
| 新目录 `uv run --locked pytest -q` | 最终接入代码 44 passed，5 条上游警告 | 0 | [新环境日志](evidence/stage-b/reproduction/) |
| 新目录 `DEMO_WORKSPACE="$PWD/demo/after" uv run --locked pytest -q demo/tests` | 已交付模型代码 29 passed | 0 | [新环境业务日志](evidence/stage-b/reproduction/) |
| 新目录 `stage-a --run-dir .runs/final-repro` → `stage-b --run-dir .runs/final-repro` → 新进程 `query` | 第二次独立真实生成同样通过目标 20 + 回归 9，恢复状态选择验收审查 | 均为 0 | [完整复现证据](evidence/stage-b/reproduction/) |
| 新进程 `query --run-dir .runs/stage-a` | 从 PowerContext 读取候选代码对应 revision 4，下一步为 `review_acceptance_report` | 0 | [恢复校验](evidence/stage-b/restart-verification.json) |

完整 pytest 命令、工作目录、退出码及代码/测试哈希保存在各 `results.json`；没有删除断言、跳过测试或调整预期。

## 代码与贡献来源

- 初始代码 SHA256：`a3ff1f4c9e24eea67f0e60842fec1d6fbdaffdbeb835c484a534759de36a7092`。
- 交付代码 SHA256：`77448e765557902f54e1ebbdd52e86db429ba5d5f49137ec30130ec72f87fc55`。
- [交付业务文件](demo/after/ticket_tool.py)与真实响应中的 `files["ticket_tool.py"]` 逐字一致，[源码复核](evidence/stage-b/source-review.json)确认按实际工单数据筛选、未针对测试 ID 硬编码，无额外文件、网络或进程副作用。
- 业务修改由 MiniMax 生成，无后续人工修补。Codex 完成上下文模块、固定测试、调用和补丁工具，以及此次环境代理接入修复。

真实工程检索数据库返回版本为 `5.7.25-OceanBase seekdb-v1.4.0.0`；PowerContext 1.4.1 另用专用 SQLite 持久后端。阶段 B 写入同一 scope 中的 artifact `art_7336ff192bf7438cbc3a196f531a0220@4`，新进程读取时客户端 ID 和 PID 不同，内容摘要及代码哈希一致。JSON 证据没有被用作状态恢复缓存。

源码审查和完整复现完成后，已将真实完成情况写入 [revision 5](evidence/stage-b/final-state-written.json)，并由另一个新进程[读取和使用](evidence/stage-b/context-final.json)：阶段 `local_acceptance_complete`，下一步 `submit_on_competition_platform`。汇总见[最终本地验收报告](evidence/stage-b/final-acceptance.json)。平台提测仍由参赛者执行。

## 已解决问题与交付边界

首次直连 MiniMax 超时。独立无认证探测确认本机需要既有代理，且原 HTTPX 环境缺少 SOCKS 支持；修复为遵循环境代理并安装 `httpx[socks]==0.28.1`（锁定 `socksio==1.0.0`）。[网络诊断](evidence/stage-b/network-recovery.json)和[恢复状态](evidence/stage-b/retry-state.json)保留失败后显式恢复过程，未覆盖首次记录。每次运行最多预检加生成两次请求，无静默自动重试。首次尝试失败 1 次；主运行成功预检和生成 2 次；新目录独立复现又成功预检和生成 2 次。共 5 次客户端请求尝试、4 个成功响应，其中 2 次实际代码生成。新目录生成结果也通过同一套 29 项测试；交付快照保留主运行版本，不要求不同模型调用返回相同文本。

阶段 A 的[缺配置记录](evidence/missing-config.json)仅说明当时缺配置时零请求退出，目前已具备真实调用证据。上游 SQLAlchemy 弃用警告不影响测试结果。

GitHub `origin` 正确，但 HTTPS 认证预检仍退出 128（无法读取用户名，终端提示禁用），尚未推送。官方提测由参赛者执行；本地成功不等同于远程可见、平台通过或保证得分。
