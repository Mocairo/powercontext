# 工单演示规格与固定测试

此目录是本作品原创的最小演示工程，不复用第三方业务数据。

- `after/ticket_tool.py`：真实 MiniMax-M3.1-Flash 生成并通过固定 29 项验收测试的交付代码，与原始最终响应逐字一致。
- `before/ticket_tool.py`：阶段 A 初始版本，只实现列出、负责人筛选和 id 升序；没有状态筛选。
- `specs/requirements.json`：导入实验的 v1 规格。
- `specs/requirements_v2.json`：规格更新输入模板，仅 `STATUS-002` 从大小写不敏感更新为严格小写。
- `task.json`：检索任务及允许修改的唯一业务文件。
- `tests/`：阶段 A/B 共用的不可修改验收测试，目标测试遵循更新后的 v2 规格。

规格更新是明确的需求变更实验：先导入 v1 并记录实际检索结果，再用 v2 替换当前规格并重新导入。不要将两个模板同时作为当前要求导入。规格和测试先编写，初始业务版本随后编写；阶段 A 不包含目标业务实现或固定最终补丁。

从仓库根目录运行：

```bash
python minimax/demo/before/ticket_tool.py --owner alice
python -m pytest -q minimax/demo/tests/test_regression.py
python -m pytest -q minimax/demo/tests/test_target.py
```

初始版本预期：回归测试 `9 passed`、退出码 `0`；目标测试 `20 failed`、退出码 `1`。目标失败表现为不识别 `--status`、错误提示不满足规格、`list_tickets` 不支持 `status` 参数。它们不应因缺依赖、导入失败或无法启动而失败。

测试另一个业务工作目录时，设置 `DEMO_WORKSPACE=/absolute/path/to/workspace`。该目录应只包含可由模型修改的 `ticket_tool.py`；验收测试仍使用本目录的同一份文件。

从 `minimax/` 验证已交付修改，不需模型凭据：

```bash
DEMO_WORKSPACE="$PWD/demo/after" uv run --locked pytest -q demo/tests
uv run --locked python demo/after/ticket_tool.py --owner alice --status open
```

预期 29 passed、退出码 0。`after/` 仅供交付代码复核；真实 `stage-b` 从独立初始副本开始并使用新的模型返回，不把该文件当作预置补丁。
