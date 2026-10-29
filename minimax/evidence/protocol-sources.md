# MiniMax 协议核对与真实接入

核对日期：2026-10-29。以下链接为协议依据；实际模型调用另见 `stage-b/attempt-02/`。

- [MiniMax 国内 OpenAI SDK](https://platform.minimax.cn/docs/api-reference/text-openai-api)：国内 base URL 为 `https://api.minimax.cn/v1`，本次真实运行使用该地址和 `MiniMax-M3.1-Flash`。
- [MiniMax OpenAI SDK](https://platform.minimax.io/docs/api-reference/text-openai-api)：兼容 Chat Completions，国际站 base URL 为 `https://api.minimax.io/v1`，响应的最终文本在 `choices[0].message.content`。`max_tokens` 是包括 thinking 在内的输出上限；旧模型可能把 thinking 放在 `<think>` 标签内，新模型也可能提供 `reasoning_content`。
- [MiniMax Model Invocation](https://platform.minimax.io/docs/guides/text-generation)：官方 curl 示例使用 `POST /v1/chat/completions` 和 Bearer 认证；接口支持非流式调用。

本作品使用 httpx 直接实现上述协议，只做单轮文本/完整代码文件生成，不使用工具调用或多轮 reasoning。客户端不保留 `reasoning_content`，去除完整 `<think>…</think>` 段，残缺标签拒收，不保存原始响应体或认证头。

本次页面列出的模型包括 `MiniMax-M3.1-Flash` 和 `MiniMax-M3`。**代码不指定默认模型**，配置中的 `MINIMAX_MODEL` 必须填写到账套餐实际支持的准确模型 ID；文档列出不等于本账户获得权限。Base URL 同样由账户所在服务区域决定，须使用其 OpenAI 兼容 `/v1` 地址。国内与国际地址均已核对；配置仍由调用者账户区域决定，不在代码中硬编码。

每次阶段 B 最多两次请求：一次真实服务预检，一次代码生成；没有自动重试。HTTP 操作超时 120 秒（连接 15 秒）；输出 16384 tokens，响应体 1000000 字节，最终代码文本 100000 字节；预检上限 4096 tokens（包含 thinking）。预检若因 thinking 用完输出额度而失败，会明确失败，不能声称服务验证成功。401/403、429、网络/超时、非 JSON、截断响应分别报错，错误体不写证据。

`tests/test_minimax_client.py` 使用 `httpx.MockTransport`，`tests/test_patches.py` 只将 `VALUE = 1` 替换成 `VALUE = 2`，均为 **fixture 单元测试**，不是 MiniMax 开发记录。补丁层只允许标记隔离目录下 `ticket_tool.py` 的完整替换；校验语法、路径、符号链接和硬链接，不允许改测试。该机制限制文件写入范围，**不是恶意 Python 的执行沙箱**；运行模型代码应使用无凭据的隔离测试环境。

真实运行发现本机直连会超时；客户端现遵循 HTTPX 标准环境代理配置，依赖 `httpx[socks]==0.28.1` 支持 SOCKS，锁定 `socksio==1.0.0`。代理设置及凭据不写证据。首次失败与修复后成功调用均保留，参见 `stage-b/network-recovery.json` 和各 attempt 目录。
