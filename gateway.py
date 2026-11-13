# FunAI OpenAI 兼容 2API 网关
# cognise.art 图库检索 -> /v1/images/generations (可用)
# vicuna.cognise.art 聊天 V3 -> /v1/chat/completions (数据面被上游风控, 403 透传)
# Run: python gateway.py  (127.0.0.1:8792)

import json
import uuid

import requests
from flask import Flask, Response, jsonify, request

APP = Flask(__name__)
COGNISE = "https://cognise.art"
STORAGE = "https://storage.cognise.art"
VICUNA = "https://vicuna.cognise.art"
FIXED_TOKEN = "7bb91a6699cc3794750101ce0354d80195f07c04"
UA = "okhttp/5.5.0"
TIMEOUT = 60

IMAGE_MODELS = {
    "funai-picsta-15": 15,
    "funai-flux-krea-10": 10,
    "funai-photon-11": 11,
    "funai-flux-schnell-13": 13,
    "funai-fluxklein-16": 16,
}
CHAT_MODELS = ["gemini-3.8-flash"]


def cognise_headers():
    return {"User-Agent": UA, "Authorization": "token " + FIXED_TOKEN}


def vicuna_token():
    r = requests.post(VICUNA + "/handshake/", json={"mobile_id": str(uuid.uuid4())},
                      headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["data"]["token"]


@APP.after_request
def _cors(resp):
    resp.headers.setdefault("Access-Control-Allow-Origin", "*")
    return resp


@APP.route("/health")
def health():
    return {"ok": True, "image_models": list(IMAGE_MODELS), "chat_models": CHAT_MODELS}


@APP.route("/v1/models")
def models():
    data = []
    for name in CHAT_MODELS:
        data.append({"id": name, "object": "model", "owned_by": "gemini"})
    for name in IMAGE_MODELS:
        data.append({"id": name, "object": "model", "owned_by": "cognise"})
    return jsonify({"object": "list", "data": data})


@APP.route("/v1/images/generations", methods=["POST"])
def images():
    body = request.get_json(force=True)
    prompt = (body.get("prompt") or "").strip()
    model = body.get("model") or "funai-flux-krea-10"
    gid = IMAGE_MODELS.get(model, 10)
    if not prompt:
        return jsonify({"error": {"message": "prompt is required"}}), 400

    # OpenAI size -> closest img_ratio accepted by upstream (upstream ignores; DB keyed by prompt)
    payload = {
        "generation_steps": 20, "guidance_scale": 7,
        "sampler_name": "Euler a", "sampler_index": "Euler a",
        "generation_prompt": prompt, "negative_prompt": body.get("negative_prompt", "") or "",
        "generation_seed": 1, "generation_id": gid, "batch_size": 1,
        "sid": 19, "img_ratio": "1:1", "hit_point": "mobile",
    }
    r = requests.post(COGNISE + "/api/mobile/txt2img/generate/v4", json=payload,
                      headers=cognise_headers(), timeout=TIMEOUT)
    try:
        data = r.json()
    except ValueError:
        return jsonify({"error": {"message": f"upstream {r.status_code}"}}), 502
    if data.get("status") != "success":
        return jsonify({"error": {"message": data.get("message", "upstream failed")}}), 502

    import time as _time
    ts = data["data"]["images"][0].get("created_at", 0)
    created = int(_time.time()) if not isinstance(ts, (int, float)) else int(ts)
    out = []
    for img in data["data"]["images"]:
        out.append({"url": STORAGE + img["image"],
                    "revised_prompt": data["data"].get("generation_info", {}).get("prompt", prompt)})
    return jsonify({"created": created, "data": out})


@APP.route("/v1/chat/completions", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    model = body.get("model") or CHAT_MODELS[0]
    msgs = body.get("messages") or []
    if not msgs:
        return jsonify({"error": {"message": "messages required"}}), 400
    last_user = next((m["content"] for m in reversed(msgs) if m.get("role") == "user"), "")
    temperature = body.get("temperature", 0.3)
    max_tokens = min(int(body.get("max_tokens") or 300), 600)

    try:
        token = vicuna_token()
    except Exception as e:
        return jsonify({"error": {"message": f"handshake failed: {e}"}}), 502

    payload = {
        "sessionId": str(uuid.uuid4()), "mode": "manual", "model": model,
        "temperature": temperature, "maxTokens": max_tokens,
        "messages": [{"role": "user", "content": last_user}],
    }
    r = requests.post(VICUNA + "/v3/chat/completions/", json=payload,
                      headers={"User-Agent": UA, "Authorization": "token " + token},
                      timeout=TIMEOUT)
    data = r.json() if "json" in r.headers.get("Content-Type", "") else {"raw": r.text}
    if r.status_code != 200 or (isinstance(data, dict) and data.get("status") != "success"):
        return jsonify({"error": {"message": f"upstream {r.status_code}: {json.dumps(data)[:200]}",
                                  "type": "upstream_denied"}}), 502

    choice = (data["data"].get("choices") or [{}])[0]
    content = (choice.get("message") or {}).get("content", "")
    return jsonify({
        "id": data["data"].get("id", "chatcmpl-funai"), "object": "chat.completion",
        "created": data["data"].get("created", 0), "model": model,
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}],
        "usage": data["data"].get("usage", {}),
    })


if __name__ == "__main__":
    APP.run(host="127.0.0.1", port=8792, threaded=True)
