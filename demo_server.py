# FunAI upstream proxy demo server
# cognise.art/api/* passthrough with the hardcoded app token,
# vicuna.cognise.art/* passthrough for chat V3 (server currently denies).
# Run: python demo_server.py  (listens on 127.0.0.1:8791)

from flask import Flask, request, Response
import requests

APP = Flask(__name__)
COGNISE = "https://cognise.art"
VICUNA = "https://vicuna.cognise.art"
FIXED_TOKEN = "7bb91a6699cc3794750101ce0354d80195f07c04"
UA = "okhttp/5.5.0"
TIMEOUT = 60

HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
       "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length"}


def _relay(base, path_override=None):
    url = base + (path_override if path_override else request.full_path)
    if not path_override and url.endswith("?"):
        url = url[:-1]
    headers = {k: v for k, v in request.headers.items() if k.lower() not in HOP}
    headers["User-Agent"] = UA
    if url.startswith(COGNISE):
        headers.setdefault("Authorization", "token " + FIXED_TOKEN)
    resp = requests.request(
        request.method, url,
        data=request.get_data() or None,
        headers=headers, timeout=TIMEOUT, allow_redirects=True)
    out = Response(resp.content, resp.status_code)
    for k, v in resp.headers.items():
        if k.lower() not in HOP and k.lower() != "content-encoding":
            out.headers[k] = v
    return out


@APP.after_request
def _cors(resp):
    resp.headers.setdefault("Access-Control-Allow-Origin", "*")
    resp.headers.setdefault("Access-Control-Allow-Headers", "Authorization, Content-Type")
    resp.headers.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
    return resp


@APP.route("/health")
def health():
    return {"ok": True, "upstreams": [COGNISE, VICUNA]}


@APP.route("/api/<path:rest>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def api(rest):
    return _relay(COGNISE)


@APP.route("/media/<path:rest>", methods=["GET"])
def media(rest):
    return _relay(COGNISE)


@APP.route("/vicuna/<path:rest>", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def vicuna(rest):
    # upstream has no /vicuna prefix; strip it and forward query string
    qs = "?" + request.query_string.decode() if request.query_string else ""
    return _relay(VICUNA, "/" + rest + qs)


if __name__ == "__main__":
    APP.run(host="127.0.0.1", port=8791, threaded=True)
