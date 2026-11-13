# FunAI-2api → new-api 对接文档（交接执行版）

> 执行者：任何会话按本文档逐步执行即可，无需上下文。
> 前置：本仓库 `gateway.py` 已实测（images 200 / chat 502 透传），上游凭证内置，无额外依赖。

## 0. 结论速览

| 渠道 | 协议形态 | 可用性 | new-api 接入建议 |
|------|----------|--------|------------------|
| FunAI 图片（cognise.art） | OpenAI `/v1/images/generations` 兼容 | ✅ 可用，免费无限流 | **立即接入**，类型选 OpenAI，模型填 5 个 funai-* |
| FunAI 聊天（vicuna） | OpenAI `/v1/chat/completions` 兼容 | ⚠️ 上游 403 风控 | 可先挂占位（自动禁用），等动态突破后无需改配置 |

## 1. 启动网关

```powershell
cd <仓库目录>
python gateway.py     # 127.0.0.1:8792，日志 gateway.log
```

自检（两个都必须过）：

```bash
curl http://127.0.0.1:8792/health
# 期望: {"ok":true,"image_models":[...5个],"chat_models":["gemini-3.8-flash"]}

curl http://127.0.0.1:8792/v1/images/generations -H "Content-Type: application/json" -d "{\"model\":\"funai-flux-krea-10\",\"prompt\":\"dragon\",\"n\":1}"
# 期望: 200 {"created":...,"data":[{"url":"https://storage.cognise.art/media/..."}]}
```

## 2. new-api 添加渠道

new-api 管理后台 → 渠道 → 添加渠道：

| 字段 | 值 |
|------|-----|
| 类型 | OpenAI |
| 名称 | `funai-image`（聊天占位可另建 `funai-chat`） |
| Base URL | `http://127.0.0.1:8792` （同机部署；跨机写实际 IP） |
| 密钥 | 任意非空串（网关不校验，如 `sk-funai-local`） |
| 模型 | `funai-picsta-15,funai-flux-krea-10,funai-photon-11,funai-flux-schnell-13,funai-fluxklein-16,gemini-3.8-flash` |
| 模型重定向 | 不需要（网关已映射） |
| 分组 | 按你站点的计费分组（建议 default） |

保存后点「测试」，图片 5 模型应全绿；`gemini-3.8-flash` 测试会失败（上游 403），属预期——可在渠道里单独把它移到禁用渠道，或保留让错误透传。

## 3. 计费与语义注意（必读）

1. **图库检索语义**：上游按 prompt 在历史生成库精确/模糊匹配，同一 prompt 永远返回同一张图。`size`/`n`/`seed` 等参数不影响结果。prompt 越常见越容易命中（单词英文命中率最高；含 `the/a/my` 等虚词或标点尾缀经常 400 `Invalid Params Sent!`）。
2. **NSFW**：上游有 profanity 检查（命中会返回 `prompt failed profanity check (matched: xxx)`），网关透传为 502。new-api 侧无需额外过滤。
3. **图片 URL 直链**：返回的 `url` 是 `storage.cognise.art` 公网直链，可直接在客户端展示；如需防直链失效可加转存。
4. **聊天 403**：`error.type=upstream_denied`，error_code 453142 是上游防滥用门禁（非频率问题），突破依赖模拟器+Frida 动态分析（Play Integrity/设备指纹假设）。在动态突破前，建议 new-api 不给该模型配倍率、保持禁用。

## 4. 稳定性数据（2026-11-13 实测）

- 20 连发 txt2img：全 200，平均 ~745ms/req
- 10 并发 /v3/models：全 200，p50 912ms，无 429
- 10 连发 handshake：全 201，无限流
- 上游全程无任何鉴权失败/封禁迹象

## 5. 故障排查

| 现象 | 原因 | 处理 |
|------|------|------|
| images 502 `Invalid Params Sent!` | prompt 含停用词/标点/过长 | 换单词或双实词 prompt 重试 |
| images 502 `prompt failed profanity check` | 上游 NSFW 词表 | 属上游策略，透传即可 |
| chat 502 `upstream_denied 453142` | 上游风控 | 等动态突破；协议层已全通 |
| 网关起不来 8792 被占 | 残留进程 | `netstat -ano | findstr 8792` 找 PID taskkill |
| new-api 测试图片超时 | 网关未启动/跨机未放行端口 | 检查 8792 监听与防火墙 |

## 6. 后续可扩展点（可选）

- `demo_server.py`（8791）是透传代理，调试上游用；对接 new-api 用 `gateway.py`（8792）即可，两者可并存。
- 若上游 `/api/models` 下发新模型（Picsta/Flux Krea/Photon/Flux Schnell/fluxklein 之外），在 `gateway.py` 的 `IMAGE_MODELS` 加一行即可。
- 聊天突破后：`gateway.py` 的 chat 分支已按上游 `ChatRequest` 协议拼好（mode=manual、model、temperature、maxTokens≤600），只需上游放行即可自动工作。
