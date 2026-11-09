# MiniMax 交付任务契约

本目录的交付目标是让一个代码修改任务可以被重新审计，而不是只保留一次成功运行的截图或本地状态。

- 初始业务文件：`demo/before/ticket_tool.py`。
- 模型交付文件：`demo/after/ticket_tool.py`，只能由阶段 B 的模型输出产生。
- 固定验收集：`demo/tests/test_regression.py` 和 `demo/tests/test_target.py`；阶段 A、阶段 B 都使用相同文件。
- 当前规格：`demo/specs/requirements_v2.json`；阶段 A 先导入 v1，再覆盖同一运行目录中的规格并导入 v2。
- 真实资料索引：每个 `.runs/<run>/catalog` 是本作品专用的嵌入式 seekdb 数据目录，查询返回结果带路径、符号、版本和文件哈希。
- 状态索引：每个 `.runs/<run>/state` 是本作品专用的 PowerContext SQLite 后端；阶段 B 后必须用新进程读取状态。
- 模型允许修改的业务范围：阶段 B 补丁工具只接受隔离目录中的 `ticket_tool.py` 完整替换，不能写验收测试、规格、证据或其他题目目录。

评审入口：

```bash
python verify.py --output evidence/recheck-module
python audit_delivery.py --output evidence/recheck-delivery
```

两个输出目录都应使用新的空目录。`verify.py` 不调用模型；`audit_delivery.py` 读取提交中的真实 MiniMax 证据，重新验证模型请求、返回代码、差异、测试哈希、seekdb 上下文和 PowerContext 新进程恢复，并在成功时写出 `all_required_gates_passed: true` 与 `local_eligible_points: 20`。这两个字段表示本地复核结果，不代表比赛平台已经给分。
