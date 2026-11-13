# FunAI stress test — baseline / boundary / concurrency
# Run: python stress_test.py
import json
import statistics
import threading
import time
import urllib.request

BASE = "https://cognise.art"
VIC = "https://vicuna.cognise.art"
TOKEN = "7bb91a6699cc3794750101ce0354d80195f07c04"
UA = "okhttp/5.5.0"


def call(url, method="GET", body=None, token=TOKEN):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "token " + token
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, time.time() - t0, r.read(300)
    except urllib.error.HTTPError as e:
        return e.code, time.time() - t0, e.read(300)
    except Exception as e:
        return -1, time.time() - t0, str(e).encode()


def gen_body(prompt, sid=19, seed=1):
    return {"generation_steps": 20, "guidance_scale": 7,
            "sampler_name": "Euler a", "sampler_index": "Euler a",
            "generation_prompt": prompt, "negative_prompt": "",
            "generation_seed": seed, "generation_id": 7, "batch_size": 1,
            "sid": sid, "img_ratio": "1:1", "hit_point": "mobile"}


def baseline():
    print("== baseline ==")
    for label, url, body in [
        ("ping", BASE + "/api/mobile/ping", None),
        ("styles", BASE + "/api/styles", None),
        ("samplers", BASE + "/api/samplers", None),
        ("models", VIC + "/v3/models/", None),
        ("txt2img cat", BASE + "/api/mobile/txt2img/generate/v4", gen_body("cat")),
    ]:
        code, ms, _ = call(url, "POST" if body else "GET", body)
        print(f"{label:14s} {code} {ms*1000:7.0f}ms")


def boundary():
    print("== boundary ==")
    cases = [
        ("empty prompt", gen_body("")),
        ("punct tail", gen_body("cat.")),
        ("stopword pair", gen_body("the cat")),
        ("noun pair", gen_body("red car")),
        ("profanity", gen_body("sex")),
        ("bad style", gen_body("cat", sid=0)),
        ("bad gid", {**gen_body("cat"), "generation_id": 9999}),
    ]
    for label, body in cases:
        code, ms, raw = call(BASE + "/api/mobile/txt2img/generate/v4", "POST", body)
        try:
            msg = json.loads(raw).get("message", "")
        except Exception:
            msg = raw[:60].decode(errors="ignore")
        print(f"{label:14s} {code} {msg}")


def concurrency(n=10):
    print(f"== concurrency {n} ==")
    codes, times = [], []
    lock = threading.Lock()

    def worker(i):
        code, ms, _ = call(VIC + "/v3/models/")
        with lock:
            codes.append(code)
            times.append(ms)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    t0 = time.time()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    total = time.time() - t0
    print(f"codes={codes}")
    print(f"total={total:.1f}s p50={statistics.median(times)*1000:.0f}ms "
          f"max={max(times)*1000:.0f}ms")


if __name__ == "__main__":
    baseline()
    boundary()
    concurrency()
