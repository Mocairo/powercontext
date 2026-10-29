# MiniMax SDD 工程上下文助手：阶段 A

本作品为代码修改任务检索规格、代码和测试，构造带真实来源的上下文，并通过 PowerContext 保存和恢复进展。当前交付为 **接入 MiniMax 前的完整准备版本**：初始工单工具保留原样，新增状态筛选尚未实现。真实模型修改、修改后全绿和最终完整验收留待阶段 B。

官方题面与六项条件见 [题面核对](evidence/task-requirements.md)，当前验收状态见 [ACCEPTANCE.md](ACCEPTANCE.md)。实际验证已完成：模块测试 44 passed、真实数据库/PowerContext 集成及新目录复现通过；业务回归 9 passed，目标 20 项有效失败。

## 环境与安装

使用 Linux x86_64、Python 3.12、Git 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)。首次安装需要访问包仓库；运行阶段 A 不需要 MiniMax 凭据或模型服务。嵌入式 seekdb 是真实数据库，首次启动需要可写磁盘和足够内存；数据存于本作品独立运行目录。

依赖不来自生态分支源码：`powercontext[builtin]==1.4.1`、`pylibseekdb==1.4.0.post2`、`httpx==0.28.1`、`pytest==9.0.2`、`pymysql==1.2.0`，所有传递依赖固定在 `uv.lock`。

从本分支的新 checkout 开始：

```bash
git clone --branch codex/minimax-sdd https://github.com/Mocairo/powercontext.git powercontext-minimax
cd powercontext-minimax/minimax
uv sync --locked --python 3.12
uv run minimax-sdd stage-a --run-dir .runs/demo-a
```

`stage-a` 在新的专用目录创建初始业务副本，从空状态导入 v1 规格、代码和固定测试，进行真实 SQL 检索，更新规格为 v2 后再次检索，运行修改前测试，写入 PowerContext，然后启动新进程读取状态并据此构造下一步上下文。最终生成 `.runs/demo-a/evidence/` 下的运行证据及 `report.json`。请使用尚不存在的运行目录，避免覆盖已有结果。

预期业务测试结果是 **回归 9 项通过，目标 20 项有效失败**。目标测试失败是阶段 A 的正确状态：初始 CLI 不识别 `--status`，函数尚不支持 `status` 参数；不得将它们计为通过。

## 可单独执行的入口

以下命令均从 `minimax/` 执行；`--run-dir` 显式选择本作品的数据范围。

```bash
uv run minimax-sdd init --run-dir .runs/manual
uv run minimax-sdd import --run-dir .runs/manual
uv run minimax-sdd query --run-dir .runs/manual --output .runs/manual/context-v1.json
uv run minimax-sdd update-spec --run-dir .runs/manual
uv run minimax-sdd import --run-dir .runs/manual
uv run minimax-sdd query --run-dir .runs/manual --output .runs/manual/context-v2.json
uv run minimax-sdd baseline --run-dir .runs/manual
uv run minimax-sdd state-save --run-dir .runs/manual
uv run minimax-sdd state-read --run-dir .runs/manual
uv run minimax-sdd query --run-dir .runs/manual
```

规格更新实验只修改 `STATUS-002`：v1 接受大小写不敏感的状态，v2 只接受严格小写。固定目标测试从开始就针对最终 v2 需求；它们在修改前后不变。当前资料与文件内容哈希对应，过期内容不能作为当前要求混入上下文。`demo/specs/requirements_v2.json` 是更新模板，不与 v1 同时作为当前规格导入。

模块单元及集成测试：

```bash
uv run pytest -q
```

这一命令只收集 `tests/`；真实业务验收测试通过 `baseline` 或阶段流程单独执行，避免将预期失败误计为模块失败。直接复核业务初始版本：

```bash
uv run pytest -q demo/tests/test_regression.py
uv run pytest -q demo/tests/test_target.py
```

需要重置时，仅删除本作品有专用标记的单个演示运行目录：

```bash
uv run minimax-sdd reset --run-dir .runs/demo-a
```

重置会删除该演示的数据库、状态与证据；不用于清理共享 PowerContext、其他赛题目录或外部数据库。保留证据时请另选新 `--run-dir`，无需重置。

## 凭据到账后执行阶段 B

将配置放在仓库外，**不要把实际密钥写入仓库或证据**：

```bash
mkdir -p /home/lijx/.config/oceanbase
cp .env.example /home/lijx/.config/oceanbase/minimax.env
chmod 600 /home/lijx/.config/oceanbase/minimax.env
```

编辑文件填写 `MINIMAX_BASE_URL`、`MINIMAX_API_KEY`、`MINIMAX_MODEL`。Base URL 使用账户区域的 MiniMax OpenAI 兼容 HTTPS `/v1` 地址；模型填套餐实际允许的精确 ID，不依赖默认模型。官方协议来源见 [protocol-sources.md](evidence/protocol-sources.md)。

```bash
uv run minimax-sdd stage-b --run-dir .runs/demo-a \
  --config /home/lijx/.config/oceanbase/minimax.env
```

本机本次已验证目录是 `.runs/stage-a`，若直接在交付工作区继续，请将上面命令的 `--run-dir .runs/demo-a` 改为 `--run-dir .runs/stage-a`。新环境按 README 创建的目录仍为 `.runs/demo-a`。

阶段 B 检查配置并调用真实服务预检，读取实际检索上下文及保存状态，发起一次真实代码生成，将返回的 `ticket_tool.py` 应用于新的 `candidate-<runid>` 隔离目录，运行同一套验收测试，保存脱敏调用记录、代码差异和测试日志，再更新 PowerContext 并生成报告。初始 `before` 不被修改，也没有预置最终补丁。

每次最多两次模型请求（预检 + 生成），无自动重试；缺配置立即报可操作错误且不发网络请求。鉴权、限流、超时、无效输出、补丁拒绝和测试失败均如实报告，不能据此宣称验收成功。后续人工修复应独立记录，不覆盖 MiniMax 原始最终代码输出。

补丁工具限定只能写 `ticket_tool.py`，禁止验收测试、路径穿越及链接绕过，并检查 Python 语法。它是文件写入边界，**不是任意 Python 的安全执行沙箱**；阶段 B 应在不含凭据和共享敏感文件的受控执行环境运行。本轮阶段 A 不执行任何模型生成的业务代码。

## 目录与限制

- `src/minimax_sdd/`：导入检索、上下文、状态、模型适配、补丁与 CLI。
- `demo/`：原创初始业务工程、任务、规格及阶段 A/B 固定验收测试。
- `tests/`：模块测试；fixture 明确与真实服务证据区分。
- `evidence/`：题面、协议和实际验证材料。
- `.runs/`：本地独立数据及执行产物，不提交 Git。
- [TECHNICAL.md](TECHNICAL.md)：一页技术说明；[SOURCES.md](SOURCES.md)：来源与许可。

当前不提供完整 Agent 框架、语义向量检索或自动修复循环；结构化/关键词关联足以可靠覆盖样例。没有 MiniMax 真实调用记录，没有修改后全绿记录，没有平台提测或得分声明。

## 实际验证材料与交付状态

[阶段 A 报告](evidence/stage-a/report.json)、[模块测试日志](evidence/module-tests.txt)、[干净目录复现](evidence/reproduction/)和[缺配置验证](evidence/missing-config.json)保留了真实证据。模块测试存在 5 条上游 SQLAlchemy 警告，未导致失败。PowerContext 的 PyMySQL 版本约束已通过固定 1.2.0 解决，无需修改锁文件。

GitHub `origin` 已核对为参赛者仓库，但本次认证不可用，推送 dry-run 失败；当前交付为本地分支及提交，尚未推送。认证恢复后可正常推送 `codex/minimax-sdd`，不要强推。此限制不影响本地阶段 A 验证。
