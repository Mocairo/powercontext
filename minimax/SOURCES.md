# 来源、版本与许可

核对日期：2026-10-29。本作品未修改已安装的第三方依赖。`uv.lock` 固定完整依赖图及分发文件哈希；下表列明直接使用的关键组件，不以本作品许可替代各依赖自身的条款。

| 组件 | 固定版本/来源 | 许可与核对依据 | 实际用途 |
| --- | --- | --- | --- |
| 官方生态骨架 | [2026-competition-ecosystem](https://github.com/oceanbase/powercontext/tree/2026-competition-ecosystem)，基线 `d647275c308e09b7b623f322a26f5c4e85734fb0` | 基线没有 LICENSE；不推断骨架许可 | 独立参赛分支及 minimax 目录 |
| PowerContext | [PyPI 1.4.1](https://pypi.org/project/powercontext/1.4.1/) | [对应官方标签 LICENSE](https://github.com/oceanbase/powercontext/blob/powercontext-v1.4.1/LICENSE)：Apache-2.0；PyPI license 字段为空，因此以标签许可证核实 | 真实任务状态写入/读取 |
| pylibseekdb | [PyPI 1.4.0.post2](https://pypi.org/project/pylibseekdb/1.4.0.post2/)、[官方绑定仓库](https://github.com/oceanbase/seekdb-bindings) | PyPI 该版本元数据声明 Apache-2.0 | 真实嵌入式 seekdb SQL 数据库 |
| httpx[socks] | [PyPI 0.28.1](https://pypi.org/project/httpx/0.28.1/)、[官方仓库](https://github.com/encode/httpx) | PyPI 该版本元数据声明 BSD-3-Clause | MiniMax HTTP 协议、环境代理及标注 fixture 的传输测试 |
| socksio | [PyPI 1.0.0](https://pypi.org/project/socksio/1.0.0/)、[官方仓库](https://github.com/sethmlarson/socksio) | 安装分发内 `socksio-1.0.0.dist-info/LICENSE`：MIT | HTTPX SOCKS 代理支持 |
| pytest | [PyPI 9.0.2](https://pypi.org/project/pytest/9.0.2/) | PyPI `license_expression=MIT` | 模块、业务和集成测试 |
| PyMySQL | [PyPI 1.2.0](https://pypi.org/project/PyMySQL/1.2.0/) | PyPI `license_expression=MIT` | 数据库依赖环境 |

本作品新增的 `minimax/` 原创源代码、演示合成数据、规格及测试采用 [Apache License 2.0](LICENSE)。业务样例是原创最小工单工具，不复制其他赛题实现或第三方业务数据。`demo/after/ticket_tool.py` 是本次真实 MiniMax-M3.1-Flash 根据初始工程、规格与测试生成的最终代码，原始响应和对应差异保存在 `evidence/stage-b/attempt-02/`；无人工业务修补。LICENSE 只声明本作品新增原创材料的许可，不扩展到其他赛题目录或依赖。

题面要求的整理及公开文档引用仅用于说明来源，不将其声明为原创代码：

- [官方赛题](https://oceanbase.yuque.com/org-wiki-obtech-vh7w9r/hc3pio/qlqnoryzrs7gtqbw)：核对记录在 [task-requirements.md](evidence/task-requirements.md)。
- [MiniMax 国内官方 OpenAI 兼容接口](https://platform.minimax.cn/docs/api-reference/text-openai-api)、[国际接口](https://platform.minimax.io/docs/api-reference/text-openai-api)与[模型调用说明](https://platform.minimax.io/docs/guides/text-generation)：实现依据在 [protocol-sources.md](evidence/protocol-sources.md)。
- [PowerContext 官方源码和文档](https://github.com/oceanbase/powercontext)：使用显式状态 SDK，不复制/改写其内部实现。
- [seekdb 文档](https://docs.seekdb.ai/)：使用其真实数据库绑定，不以 SQLite 或 mock 替代工程检索数据库。
