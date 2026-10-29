# MiniMax SDD 工程上下文助手

本作品为代码修改任务检索规格、代码和测试，构造带来源的上下文，通过 MiniMax 实际生成业务修改，再用 PowerContext 保存并恢复验证进展。已完成阶段 A 和首次真实阶段 B：**MiniMax-M3.1-Flash 原样生成的代码通过目标 20 项、回归 9 项固定测试，业务代码无需人工修补**。新源目录、新虚拟环境和新数据范围中也已再次完整执行 A→B，并验证新进程状态恢复。平台提测及官方评分尚未执行。

[验收对照](ACCEPTANCE.md)列明六项本地证据；[技术说明](TECHNICAL.md)介绍各组件分工。`demo/before/` 保留初始版本，`demo/after/` 保存实际模型输出对应的交付版本；它不是阶段 B 的预置补丁。

## 环境与安装

使用 Linux x86_64、Python 3.12、Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。独立依赖包括 `powercontext[builtin]==1.4.1`、`pylibseekdb==1.4.0.post2`、`httpx[socks]==0.28.1`、`pytest==9.0.2`、`pymysql==1.2.0`；`uv.lock` 固定全部传递依赖。运行不引用其他赛题的源码或数据库。

分支推送后可从参赛者仓库取得源码；目前推送认证仍受阻，也可使用本地交付工作区：

```bash
git clone --branch codex/minimax-sdd https://github.com/Mocairo/powercontext.git powercontext-minimax
cd powercontext-minimax/minimax
uv sync --locked --python 3.12
```

## 无密钥验证已交付版本

以下命令从 `minimax/` 执行，不调用模型：

```bash
uv run --locked pytest -q
DEMO_WORKSPACE="$PWD/demo/after" uv run --locked pytest -q demo/tests
uv run --locked python demo/after/ticket_tool.py --owner alice --status open
```

已交付业务版本预期 **29 passed、退出码 0**。模块测试只收集 `tests/`，其中 MiniMax 传输与补丁使用明确标识的 fixture；真实 MiniMax 开发记录单独位于 [evidence/stage-b/](evidence/stage-b/)。

## 从空数据重现完整流程

先完成无需模型的准备阶段，使用尚不存在的专用运行目录：

```bash
uv run --locked minimax-sdd stage-a --run-dir .runs/demo-a
```

它创建初始业务副本，导入 v1 规格、代码和测试到真实 seekdb，查询上下文，更新为 v2 并重新查询，运行修改前测试，写入 PowerContext，再启动新进程读取状态并选择下一步。原始测试结果必须是 **回归 9 passed（退出 0）、目标 20 failed（退出 1）**；这是状态功能尚未实现的有效失败，不能计为通过。命令整体校验这些预期后退出 0，证据在 `.runs/demo-a/evidence/`。

需要真实生成时，在仓库外创建配置；已有文件不覆盖：

```bash
mkdir -p /home/lijx/.config/oceanbase
cp -n .env.example /home/lijx/.config/oceanbase/minimax.env
chmod 600 /home/lijx/.config/oceanbase/minimax.env
```

填写 `MINIMAX_BASE_URL`、`MINIMAX_API_KEY`、`MINIMAX_MODEL`。本次实测使用 `https://api.minimax.cn/v1` 和 `MiniMax-M3.1-Flash`；新账户应填写自身区域及套餐支持的精确值，代码不默认选择模型。协议来源见 [protocol-sources.md](evidence/protocol-sources.md)。客户端遵循现有 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY` 和 `NO_PROXY` 配置，SOCKS 支持由锁定依赖提供；不把代理地址或认证信息写入证据。

```bash
uv run --locked minimax-sdd check-config
uv run --locked minimax-sdd stage-b --run-dir .runs/demo-a \
  --config /home/lijx/.config/oceanbase/minimax.env
uv run --locked minimax-sdd query --run-dir .runs/demo-a \
  --output .runs/demo-a/context-after-b.json
```

阶段 B 用真实服务预检和真实代码生成共最多两次请求，读取数据库上下文及恢复状态，只将模型返回的 `ticket_tool.py` 应用到新 `candidate-<runid>` 目录，运行同一套固定测试，保存脱敏请求、最终代码、差异及测试日志，并更新 PowerContext。它不会读取 `demo/after/` 来代替模型输出。最后的 `query` 是新进程，会检索候选代码并读取新的状态 revision。

本机 `.runs/stage-a` 已完成真实生成、测试和源码审查，最终状态为 `local_acceptance_complete`，下一步为参赛者平台提测。直接再次运行 `stage-b` 会被拒绝，避免重复调用。新运行通过测试后会先进入验收审查；重新演示请使用新的 `--run-dir`，不要覆盖历史证据。失败时也不会自动重试；应检查记录，修复实际原因并显式保存恢复操作，或从新的演示目录开始。本次首次直连超时、代理修复、恢复状态和成功重试均保留在 `evidence/stage-b/`。

## 分步入口与数据范围

```bash
uv run --locked minimax-sdd init --run-dir .runs/manual
uv run --locked minimax-sdd import --run-dir .runs/manual
uv run --locked minimax-sdd query --run-dir .runs/manual --output .runs/manual/context-v1.json
uv run --locked minimax-sdd update-spec --run-dir .runs/manual
uv run --locked minimax-sdd import --run-dir .runs/manual
uv run --locked minimax-sdd query --run-dir .runs/manual --output .runs/manual/context-v2.json
uv run --locked minimax-sdd baseline --run-dir .runs/manual
uv run --locked minimax-sdd state-save --run-dir .runs/manual
uv run --locked minimax-sdd state-read --run-dir .runs/manual
```

规格更新仅将 `STATUS-002` 从大小写不敏感改为严格小写；固定目标测试自阶段 A 起按最终 v2 需求编写，修改前后哈希相同。不要将两个规格模板同时作为当前要求导入。源文件变化后，旧索引会被判为过期，需重新导入。

重置仅处理本作品带专用标记的单个演示目录：

```bash
uv run --locked minimax-sdd reset --run-dir .runs/demo-a
```

它会删除该演示的数据库、状态和证据；保留结果时另选新目录即可。不会清理共享服务、外部数据库或其他题目数据。

## 证据与边界

- [初始验证](evidence/stage-a/report.json)：回归通过、目标有效失败，以及规格更新与状态复用。
- [真实模型输出](evidence/stage-b/attempt-02/minimax-final-output.json)、[代码差异](evidence/stage-b/attempt-02/model.patch)、[测试结果](evidence/stage-b/tests-after/results.json)：对应 `demo/after/ticket_tool.py`。
- [独立新环境完整复现](evidence/stage-b/reproduction/)：模块 44 项、交付代码 29 项、完整 A→B 及新进程恢复均通过；第二次真实生成也通过同一验收集。
- [新进程状态恢复](evidence/stage-b/restart-verification.json)：读取阶段 B 的 revision 4，并实际选择 `review_acceptance_report`。
- [最终本地验收](evidence/stage-b/final-acceptance.json)：审查与完整复现后写入 revision 5，新进程再次读取并选择 `submit_on_competition_platform`；该待办不表示已经提测。
- [来源与许可](SOURCES.md)、[证据索引](evidence/README.md)。

补丁工具只允许写隔离目录内的 `ticket_tool.py`，禁止测试、路径穿越及链接绕过；它不是任意 Python 的安全执行沙箱。测试子进程不继承凭据环境，模型代码仍应在受控环境执行。日志不保存密钥、认证头或模型私有思维链。初次网络接入修复由 Codex 完成，交付业务修改则与 MiniMax 最终输出逐字一致。

GitHub `origin` 已确认是 `Mocairo/powercontext`，当前 HTTPS 认证不可用，推送预检退出 128；本地交付与官方平台提测、得分是不同状态。认证恢复后正常推送本任务分支，不强推。阶段 A 的缺配置证据是历史记录，不能解读为当前仍缺少模型配置。
