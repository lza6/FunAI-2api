# FunAI (ASKI AI Chatbot) — 逆向与压测报告

**APK**: `AI-Chatbot-Assistant-FunAI_v1.5.15_modyolo.apk` (27MB, 2026-11-12)
**包名**: `com.aski.chatgpt.ai.chatbot`（真实业务代码 `com.example.funsolchatgpt.*`，FunSol 白标家族）
**versionName**: 1.5.15 / versionCode 82515（由 versionName 推算）
**结论**: 聊天主链路（vicuna）服务端有防滥用门禁，未登录态无法白嫖；图片链路（cognise.art/api）**全开**，可无限查询历史图库（非真实生成）。

---

## 1. 应用结构

- 纯 dex 应用（6 个 dex，无 Flutter/libapp.so），jadx 直接反编译。
- 混淆为 defpackage 短名（eq0/hq0/jq1/cd5/t9/ik2 等），Kotlin 协程 + Retrofit + OkHttp + Room + Hilt。
- 集成：Firebase (Auth/RemoteConfig/FCM/Crashlytics)、AdMob/AppLovin/IronSource/Vungle/InMobi/Pangle 广告、Google Billing、OneSignal、genai SDK (Gemini Nano 1.0.0-beta4)、APM (pglarmor/apminsight)。
- modyolo 破解版内嵌 `bin.mt.signature.KillerApplication`（ApkSignatureKillerEx），静态替换 `packageInfo.signatures[0]` 绕过签名校验；`TamperActivity` 检测到篡改会 `finishAffinity + System.exit`，但 killer 在 Application 阶段已拦截。

## 2. 网络端点

| 域名 | 用途 | 鉴权 |
|------|------|------|
| `https://vicuna.cognise.art` | 聊天 V3 API（握手/会话/补全/模型） | `Authorization: token <40hex>` |
| `https://cognise.art/api/` | 图片生成/风格/采样器/灵感 | 固定 token（硬编码在 i30 拦截器） |
| `https://storage.cognise.art` | 图片 CDN | 无 |
| `https://api.openai.com/v1/` | 遗留代码（CaptionRequest gpt-3.5-turbo），实际未用 | - |
| `https://exchangerate.funsol.cloud` | 积分汇率 | - |

### 2.1 vicuna.cognise.art（聊天 V3）

```
POST /handshake/            body={"mobile_id":"<uuid>"}  → 201 {"status":"success","data":{user_id, uuid, username, email, token}}
GET  /v3/models/            → 200 模型列表（当前仅 gemini-3.8-flash, streaming=false）
POST /v3/chat/session/init  → 403 Request denied (error_code 453142)
POST /v3/chat/completions/  → 403 同上
GET  /v3/chats/sessions/    → 403 同上
```

- 请求体（ChatRequest）：`{session_id, mode: "auto"|"manual", model, temperature, max_tokens, messages:[{role,content}]}`；`mode=manual` 时 model 必填；`gpt-5.1-chat-latest/gpt-5.5` 用 temperature 1.0，否则 0.3；maxTokens 600（付费）/300（免费）。
- 响应（ChatResponse）：`{id, choices, created, latency, mode, model, object, session_id, usage, user}`。
- 头部（g7/d7 组装）：`Authorization: token <tok>`、`X-App-Id: com.aski.chatgpt.ai.chatbot`、`X-App-Version`、`X-Version-Number`、`UT-Token`。
- **门禁**：握手和模型列表全开放（握手 ~500ms/次，连发 10 次全部 201），但 init/completions/sessions 一律 403/453142，与 UA/头部变体/请求体无关——服务端按 token/环境风控（error code 不存在于 APK，为服务端常量）。**聊天链路无法纯协议白嫖，需真机动态分析**（Frida hook 或模拟器抓包确认是否还有 Play Integrity/设备指纹）。

### 2.2 cognise.art/api（图片）

```
GET  /api/mobile/ping        → 200
GET  /api/styles             → 200 风格列表（id/title）
GET  /api/samplers           → 200 采样器
GET  /api/generation/inspirations?pagination=N&hit_point=mobile → 200 灵感图（1261 条）
POST /api/mobile/txt2img/generate/v4 → 200 出图（见下）
```

- 鉴权：OkHttp 拦截器 `i30(4)` 硬编码 `Authorization: token 7bb91a6699cc3794750101ce0354d80195f07c04`。
- 请求体（实测有效形状）：
  ```json
  {
    "generation_steps": 20, "guidance_scale": 7,
    "sampler_name": "Euler a", "sampler_index": "Euler a",
    "generation_prompt": "cat", "negative_prompt": "",
    "generation_seed": 1, "generation_id": 7, "batch_size": 1,
    "sid": 19, "img_ratio": "1:1", "hit_point": "mobile"
  }
  ```
  - `sid` = 风格 id（/api/styles 里的 id，19=No Style）
  - `generation_id` = RemoteConfig `generation_id`（当前 7）
  - 带 `tz`/`user_uuid` 反而 400；prompt 含多词/标点经常 400（服务端校验诡异）
  - **行为是"按 prompt 查历史图库"**：同一 prompt 永远返回同一 id/图（cat→ComfyUI_00001，dog→flux_krea_00001），不是真实 txt2img
- 图片 URL：`https://storage.cognise.art` + `image` 字段（也可直接 cognise.art 域）。
- 响应含 `is_nsfw` 标记；服务端另有 profanity 校验（`prompt failed profanity check (matched: sex)`）。

## 3. 压测结果（2026-11-13，本机直连，UA okhttp/5.5.0）

| 项 | 结果 |
|----|------|
| 20 连发 txt2img（DB 查询） | 全 200，总耗时 14.9s，平均 ~745ms/req |
| 10 连发 handshake | 全 201，总耗时 5.0s，~500ms/req |
| 10 并发 /v3/models | 全 200，2.1s |
| 限流 | 未触发（无 429）；图片端点未做频控 |
| 聊天 v3 | 100% 403（与频率无关） |

## 4. 交付物

- `demo_server.py` — Flask 代理（127.0.0.1:8791）：`/api/*` `/media/*` → cognise.art（自动注入固定 token），`/vicuna/*` → vicuna.cognise.art（剥前缀），全站 CORS 放行，跟随上游 301
- `demo.html` — 中文 demo 页（链路状态表 + 图库检索出图 + 握手演示），走本机代理规避 CORS
- `stress_test.py` — 三阶段压测（基线/边界/并发），实测通过
- `parse_remoteapp.py` — RemoteConfig 默认值解析器（手写 AXML 解析，UTF-8 string pool 用 1 字节变长前缀）
- `demo_screenshot.png` — 浏览器实测截图（出图成功）
- `jadx_out/`, `jadx_fb/`, `jadx_c2/`, `jadx_c3/` — 反编译产物

## 5. 实测验收（2026-11-13）

- demo server：`/health` 200、`/api/mobile/ping` 200、`/api/mobile/txt2img/generate/v4` 200 出图、`/media/*` 200 image/jpeg（36KB）、`/vicuna/v3/models/` 200、`/vicuna/handshake/` 201
- 浏览器（chrome-devtools）：demo.html 出图成功（dragon → flux_krea 图）、handshake 201 拿到 token、models 200、chat/completions 403（预期，服务端风控）
- 压测：20 连发 txt2img 全 200（~745ms/req）、10 并发 models p50 912ms 无 429、握手无限流

## 5. 已知限制

- 聊天 V3 需要真机/模拟器动态分析确认服务端风控依据（怀疑 Play Integrity 或设备指纹绑定）。
- 图片端点是"图库搜索"语义，非真实生成；出图质量取决于服务端历史库。
- RemoteConfig 线上值可能与 APK 内置默认不同（`vicuna_prod` 域名/密钥可被远端更换）。
