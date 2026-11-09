# 实测证据索引

材料区分阶段 A 历史准备、真实阶段 B 和明确标识的 fixture 测试。真实 MiniMax 开发记录在 `stage-b/attempt-03/`，不是 fixture。

## 阶段 B

- `stage-b/attempt-01/`：首次实际预检直连超时的命令、失败报告和当时上下文。未生成业务修改。
- `stage-b/network-recovery.json`、`retry-state.json`：无认证网络诊断、HTTPX 环境代理及 SOCKS 修复、PowerContext 显式恢复状态。首次失败没有覆盖。
- `stage-b/attempt-03/`：真实预检、任务上下文、`MiniMax-M3.1-Flash` 最终代码、补丁差异、实际测试、重新导入与状态写入。`minimax-final-output.json` 仅保存最终文本和脱敏请求，不含模型私有思维链。
- `stage-b/attempt-03/tests.json`：原封不动的目标和回归测试，20 + 9 全部通过的命令、退出码及代码/测试哈希；历史 `tests-after/` 保留早期成功运行。
- `stage-b/source-review.json`：交付 `demo/after/ticket_tool.py` 与实际模型响应逐字一致，源码审查通过，无后续人工业务修补。
- `stage-b/context-after-b.json`、`context-final.json`：新进程从 PowerContext 读取 revision 3，真实查询候选代码，使用恢复状态选择 `review_acceptance_report`。
- `stage-b/reproduction/`：新源目录、新虚拟环境及独立空数据的完整 A→B 复现。模块 44 项和已交付业务 29 项通过；第二次真实生成也通过目标 20 + 回归 9，随后新进程读取状态并选择验收审查。以其中实际命令和报告为准。
- `stage-b/final-state-written.json`、`context-final.json`、`final-acceptance.json`：源码审查与完整复现完成后真实写入 revision 3，再由新进程读取，选择 `submit_on_competition_platform`。这是待办，不是平台提测记录。
- `delivery-audit.json`、`acceptance.json`：平台兼容入口生成的本地汇总副本；两者均来自无模型调用的 `audit_delivery.py`，包含 `all_required_gates_passed: true` 与 `local_eligible_points: 20`，不代表官方平台评分。

## 阶段 A 历史

- `environment.json`：阶段 A 独立依赖、真实数据库版本、官方基线和本任务分支；当前依赖新增 SOCKS 支持，以 `uv.lock` 为准。
- `module-tests-command.json`、`module-tests.txt`：阶段 A 的 44 项模块测试通过；最新根级 `verify.py` 复核结果保存在 `evidence/recheck-module/`，含真实 seekdb 与 PowerContext 测试；MiniMax 传输使用明确标识的 fixture。
- `stage-a/`：首次完整准备流程。`context-v1.json` → `context-v2.json` 验证规格更新，`state-written.json` → `context-restored.json` 验证跨进程复用。
- `stage-a/baseline/`：固定业务测试原始日志与哈希，目标 20 项有效失败是初始版本缺少功能的证据。
- `reproduction/`：阶段 A 的干净安装与新数据复现；`verification.json` 的源码哈希对应当时准备版本，不宣称等于后续代理修复版本。
- `missing-config.json`：当时配置缺失时退出 2、零请求的历史验证；当前已有真实模型调用。
- `push-preflight.json`：阶段 A 的推送认证失败记录，本轮交付状态由最终报告说明。
- `task-requirements.md`、`protocol-sources.md`、`powercontext-design.md`：题面、协议及 SDK 使用依据。

日志保留实际绝对路径、PID、artifact ID 和时间。导出 JSON 中路径指向原运行位置；相关源码、日志也随作品交付，新环境会产生新的路径和 ID。pytest 原始诊断空白未改写，失败记录未改写为成功。

新环境安装可以复用 uv 下载缓存，但工程数据库和 PowerContext 状态从独立空目录建立，不能复制旧状态来冒充重启或复现。`audit_delivery.py` 的 `local_eligible_points: 20` 仍只是本地复核；平台提测、官方分数与 GitHub 推送状态不由本地测试成功推断。

## 2026-11-09 平台兼容复核

`verify.py` 与 `audit_delivery.py` 的最新输出分别位于 `module-recheck-final-20261109/` 和 `platform-audit-final-20261109/`，均退出 0；根目录的 `delivery-audit.json` 与 `acceptance.json` 是同一审计结果的便利副本。审计结果为 `all_required_gates_passed: true`、`local_eligible_points: 20`，过程不发起新的 MiniMax 请求。
