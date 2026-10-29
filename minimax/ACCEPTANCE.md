# 阶段 A 验收对照

**阶段 A 已完成；整题未完成，未提测。** 官方要求六项全部通过才得 20 分。下面不代表平台评测通过或得分，真实 MiniMax 参与和修改后全绿仍待阶段 B。官方依据见 [题面核对](evidence/task-requirements.md)。

| 官方必做项 | 当前状态 | 证据与未完成部分 |
| --- | --- | --- |
| 能够运行 | 阶段 A 已验证，完整流程待 B | 新目录、新虚拟环境和新数据范围按 README 安装及执行成功；[复现证据](evidence/reproduction/)。 |
| MiniMax 实际参与 | 待阶段 B | 适配器与 fixture 不是实际参与；需真实请求、上下文、模型最终代码及对应差异。 |
| 上下文正确 | 阶段 A 已验证 | [v1](evidence/stage-a/context-v1.json) → [v2](evidence/stage-a/context-v2.json)：真实来源完整，STATUS-002 更新为 v2，旧规则不混入。 |
| 数据库实际参与 | 阶段 A 已验证 | [实际上下文和 SQL](evidence/stage-a/context-v2.json)包含真实 seekdb 查询、返回结果、数据库版本与来源。 |
| 状态能够复用 | 阶段 A 已验证 | [写入](evidence/stage-a/state-written.json)与[重启恢复](evidence/stage-a/context-restored.json)：新进程、新客户端读同一 artifact，并选择 call_minimax。 |
| 代码修改有效 | 修改前已验证，修改后待 B | 初始版本回归 9 passed，目标 20 项有效失败；同一测试修改后全绿尚未验证。 |

## 实际验证结果

| 实际命令/验证 | 结果 | 退出码 | 证据 |
| --- | --- | --- | --- |
| `uv run --locked pytest -q` | 44 passed；5 条上游 SQLAlchemy 警告，无失败 | 0 | [日志](evidence/module-tests.txt)、[命令](evidence/module-tests-command.json) |
| 完整 `stage-a --run-dir .runs/stage-a` | 真实导入/检索、规格更新、基线和状态重启全部通过；模型请求 0 | 0 | [报告](evidence/stage-a/report.json) |
| 回归测试（固定 `test_regression.py`） | 9 passed，0 errors，0 skipped | 0 | [命令、哈希与计数](evidence/stage-a/baseline/results.json) |
| 目标测试（固定 `test_target.py`） | 20 failed，0 errors，0 skipped；缺少状态功能导致的有效失败 | 1 | [日志](evidence/stage-a/baseline/target.stdout.txt) |
| 新目录 `uv sync --locked --python 3.12` | 全新虚拟环境按锁文件安装成功 | 0 | [复现证据](evidence/reproduction/) |
| 新目录 `uv run --locked minimax-sdd stage-a --run-dir .runs/demo-final` | 全新演示数据范围再次完成阶段 A | 0 | [复现证据](evidence/reproduction/) |
| 无凭据执行阶段 B | 明确提示缺配置，无网络请求，无伪模型记录 | 2 | [缺配置记录](evidence/missing-config.json) |

初始业务代码 SHA256：
`a3ff1f4c9e24eea67f0e60842fec1d6fbdaffdbeb835c484a534759de36a7092`

真实数据库返回版本：`5.7.25-OceanBase seekdb-v1.4.0.0`。工程资料由真实 seekdb 保存并查询；PowerContext 使用独立 SQLite 持久后端，两者职责没有混淆。

状态写进程 PID `3714950`，读进程 PID `3715772`，客户端实例 ID 不同；两者使用同一 scope 下的 `art_7336ff192bf7438cbc3a196f531a0220@1` 和相同内容摘要。恢复状态直接用于上下文和下一步 `call_minimax`，没有从 JSON 证据或进程缓存恢复。

目标失败均因 CLI 不识别 `--status`、函数不接受 `status` 或缺少规定的非法状态提示，不是依赖、导入或启动错误。验收文件内容哈希一致，没有 skip/xfail，也没有在阶段 A 实现目标功能。

## 当前限制与已解决问题

- MiniMax 凭据文件尚不存在，属于本阶段预期条件，不阻塞阶段 A；本轮未等待或轮询套餐。
- PowerContext 1.4.1 要求 PyMySQL `>=1.2,<1.2.1`；最初尝试 1.1.2 的依赖冲突已通过固定 1.2.0 解决，最终锁定环境及干净安装通过。
- 5 条 SQLAlchemy 上游警告未导致测试失败；原始日志保留。没有其他已知运行阻塞。
- `origin` 已确认是 `Mocairo/powercontext`；推送 dry-run 退出 128，提示无法读取 GitHub 用户名（终端提示禁用）。认证不可用，本分支尚未推送。未强推、未向官方仓库推送。

## 阶段 B 必须补齐

1. 配置仓库外 MiniMax 凭据，验证真实服务并生成业务修改。
2. 保留脱敏任务上下文、模型标识、模型最终代码、补丁应用结果和差异。
3. 同一套目标及回归测试修改后全部通过，保留命令、退出码和版本。
4. 将真实结果写入 PowerContext，生成最终完整验收报告。
5. 若需后续人工修复，独立记录贡献来源，不覆盖模型原始最终输出。

本机已验证运行目录为 `.runs/stage-a`；新环境按 README 创建的是 `.runs/demo-a`。后续命令应选对应目录。比赛平台提测由参赛者操作。
