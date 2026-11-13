# Per-model smoke + concurrency stress for all 5 image models (via local gateway 8792)
# Run: python per_model_stress.py
import json
import statistics
import threading
import time
import urllib.request

GATEWAY = "http://127.0.0.1:8792"
MODELS = [
    "funai-picsta-15", "funai-flux-krea-10", "funai-photon-11",
    "funai-flux-schnell-13", "funai-fluxklein-16",
]
PROMPTS = ["dragon", "castle", "ocean", "forest", "robot"]


def gen(model, prompt):
    body = json.dumps({"model": model, "prompt": prompt, "n": 1}).encode()
    req = urllib.request.Request(
        GATEWAY + "/v1/images/generations", data=body, method="POST",
        headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw = r.read(500)
            return r.status, time.time() - t0, raw
    except urllib.error.HTTPError as e:
        return e.code, time.time() - t0, e.read(300)
    except Exception as e:
        return -1, time.time() - t0, str(e).encode()


def per_model_smoke():
    print("== per-model smoke (1 req each) ==")
    ok = 0
    for m, p in zip(MODELS, PROMPTS):
        code, ms, raw = gen(m, p)
        url = ""
        try:
            url = json.loads(raw)["data"][0]["url"]
        except Exception:
            url = raw[:80].decode(errors="ignore")
        mark = "PASS" if code == 200 and "storage.cognise.art" in url else "FAIL"
        if mark == "PASS":
            ok += 1
        print(f"{m:22s} {code} {ms*1000:6.0f}ms {mark} {url[:70]}")
    print(f"smoke: {ok}/{len(MODELS)} PASS")


def concurrency(n=10):
    print(f"== concurrency {n} (distinct single nouns, round-robin models) ==")
    nouns = ["cat", "dog", "sun", "moon", "tree",
             "flower", "house", "car", "bird", "fire"]
    codes, times = [], []
    lock = threading.Lock()

    def worker(i):
        code, ms, raw = gen(MODELS[i % len(MODELS)], nouns[i % len(nouns)])
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
          f"max={max(times)*1000:.0f}ms "
          f"pass={sum(1 for c in codes if c == 200)}/{n}")


if __name__ == "__main__":
    per_model_smoke()
    concurrency()
