# FunAI-2api

FunAI（ASKI AI Chatbot，`com.aski.chatgpt.ai.chatbot` v1.5.15 modyolo，FunSol 白标家族）逆向 → 上游协议还原 → OpenAI 兼容 demo 网关 → new-api 对接文档。

> 2026-11-13 逆向完成 · 全部结论均有实测证据 · 上游 cognise.art / vicuna.cognise.art

## 状态总表

| 模块 | 状态 | 说明 |
|------|------|------|
| 静态还原（jadx 全量） | ✅ 完成 | 纯 dex 应用，6 dex，混淆 defpackage 短名 |
| 聊天 V3 协议（vicuna.cognise.art） | ✅ 协议还原 / ⚠️ 数据面被风控 | handshake + models 全开；chat/session/init、chat/completions、chats/sessions 一律 403 `453142`（服务端风控，与 UA/头/体无关） |
| 图片链路（cognise.art/api） | ✅ 全通 | 硬编码 token，txt2img/v4 稳定出图（图库检索语义） |
| 图片生成模型 | ✅ 5 个实测 | /api/models：Picsta(15) / Flux Krea(10) / Photon(11) / Flux Schnell(13) / fluxklein(16)，**generation_id 传任意值返回同一图**（纯按 prompt 查库） |
| 聊天模型 | ✅ 1 个实测 | /v3/models/：gemini-3.8-flash（streaming=false，owned_by=gemini） |
| OpenAI 兼容 demo 网关 | ✅ 完成 | gateway.py：/v1/models + /v1/images/generations + /v1/chat/completions（chat 走 vicuna，403 透传） |
| 压测 | ✅ 完成 | 20 连发 txt2img 全 200 ~745ms/req；10 并发 models p50 912ms；握手无限流 |
| demo 页 | ✅ 浏览器实测 | 出图/握手/模型列表全通过（截图见 docs） |
| new-api 对接 | ✅ 文档就绪 | docs/NEWAPI-INTEGRATION.md（交接给其他会话执行） |
| 聊天 403 突破 | ⏳ 未做 | 需模拟器 + Frida 动态分析（怀疑 Play Integrity/设备指纹） |

## 快速开始

```powershell
# 1. OpenAI 兼容网关（端口 8792）
python gateway.py

# 2. 上游透传代理（端口 8791，demo.html 用）
python demo_server.py

# 3. 压测
python stress_test.py
```

## 可用模型（实测）

### 聊天（vicuna.cognise.art，/v3/models/，无鉴权即可读）

| identifier | owned_by | streaming | context_window | 可用性 |
|------------|----------|-----------|----------------|--------|
| `gemini-3.8-flash` | gemini | false | 0 | ⚠️ 列表可读，chat/completions 被服务端 403 风控 |

APK 内还硬编码引用（远程 config 可下发更多）：`gpt-5.1-chat-latest`、`gpt-5.5`（temperature 1.0，maxTokens 600 付费/300 免费）。

### 图片生成（cognise.art/api，/api/models/，硬编码 token）

| id | name | 视觉标识 | 实测出图 |
|----|------|----------|----------|
| 15 | Picsta | generation-model/2025/12/18/…png | ✅（与 gid 无关，同 prompt 同图） |
| 10 | Flux Krea | flux_krea_blaze.png | ✅ |
| 11 | Photon | juggernaut.png | ✅ |
| 13 | Flux Schnell | fluxSchnell.png | ✅ |
| 16 | fluxklein | — | ✅ |

> 行为本质：`POST /api/mobile/txt2img/generate/v4` 按 prompt 在历史生成库里匹配返回（同 prompt → 同 id 同图，seed/generation_id 改变无效）。真正"生成新图"未证实。风格 id（sid）来自 /api/styles（19=No Style），采样器来自 /api/samplers。

## 目录

```
├── gateway.py            # OpenAI 兼容 2API 网关（new-api 渠道直连目标）
├── demo_server.py        # 上游透传代理（demo.html 后端）
├── demo.html             # 中文 demo 页（出图/握手/模型，浏览器实测通过）
├── stress_test.py        # 基线/边界/并发三阶段压测
├── parse_remoteapp.py    # RemoteConfig 默认值 AXML 解析器（UTF8 pool 1 字节变长前缀）
├── REVERSE_REPORT.md     # 完整逆向报告（端点/协议/鉴权/压测/限制）
├── docs/
│   ├── NEWAPI-INTEGRATION.md   # new-api 对接交接文档（给执行会话）
│   └── demo_screenshot.png     # demo 页实测截图
├── apk_raw/              # APK 解包产物
└── jadx_out/             # jadx 反编译源码
```

## 关键结论

1. **图片渠道可立即对接 new-api**（images API 形态，免费、无限流）——但语义是"历史图库检索"，prompt 命中率决定体验。
2. **聊天渠道被上游风控挡在数据面**，协议层（握手/注册/token 发放）完全打通；突破需动态分析。
3. modyolo 版内嵌 `ApkSignatureKillerEx` 绕过 `TamperActivity` 签名校验。

## License

MIT
