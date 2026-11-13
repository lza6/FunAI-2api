# OpenAI 兼容 2API 网关 — FunAI (cognise.art / vicuna.cognise.art)

把 FunAI 的两条上游包装成 OpenAI 协议，供 new-api 直接对接。

## 运行

```powershell
python gateway.py        # 监听 127.0.0.1:8792
```

无需任何环境变量。上游凭证已内置（图片渠道的固定 token 来自 APK 硬编码；聊天渠道 token 每次 handshake 现取）。

## 端点

| OpenAI 端点 | 上游 | 状态 |
|-------------|------|------|
| `GET /v1/models` | cognise `/api/models` + vicuna `/v3/models/` 合并 | ✅ |
| `POST /v1/images/generations` | cognise `/api/mobile/txt2img/generate/v4` | ✅ 可用（图库检索语义） |
| `POST /v1/chat/completions` | vicuna `/handshake/` → `/v3/chat/completions/` | ⚠️ 数据面 403（上游风控 453142），透传错误 |
| `GET /health` | — | ✅ |

## 实测模型列表（gateway /v1/models 返回）

```
gemini-3.8-flash        (chat, vicuna, owned_by=gemini, streaming=false)
funai-picsta-15         (image, cognise generation_id=15)
funai-flux-krea-10      (image, generation_id=10)
funai-photon-11         (image, generation_id=11)
funai-flux-schnell-13   (image, generation_id=13)
funai-fluxklein-16      (image, generation_id=16)
```

> 注意：图片 5 模型实测 generation_id 传任意值返回同一张图（服务端纯按 prompt 查历史库），
> 模型名只是形式区分。聊天 gemini-3.8-flash 当前无法真正出文（403 453142）。

## 快速验证

```bash
# 模型列表
curl http://127.0.0.1:8792/v1/models

# 图片（OpenAI images 协议）
curl http://127.0.0.1:8792/v1/images/generations -H "Content-Type: application/json" ^
  -d "{\"model\":\"funai-flux-krea-10\",\"prompt\":\"dragon\",\"n\":1,\"size\":\"1024x1024\"}"

# 聊天（预期 403 透传，等动态分析突破后自动可用）
curl http://127.0.0.1:8792/v1/chat/completions -H "Content-Type: application/json" ^
  -d "{\"model\":\"gemini-3.8-flash\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}]}"
```
