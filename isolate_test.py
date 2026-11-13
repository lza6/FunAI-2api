# Isolate variable: is failure model-specific or prompt-specific?
# Same prompt across all 5 models + hit-rate probe over common nouns.
# Run: python isolate_test.py
import json
import urllib.request

GATEWAY = "http://127.0.0.1:8792"
MODELS = ["funai-picsta-15", "funai-flux-krea-10", "funai-photon-11",
          "funai-flux-schnell-13", "funai-fluxklein-16"]


def gen(model, prompt):
    body = json.dumps({"model": model, "prompt": prompt, "n": 1}).encode()
    req = urllib.request.Request(
        GATEWAY + "/v1/images/generations", data=body, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read(500))["data"][0]["url"]
    except urllib.error.HTTPError as e:
        return e.code, e.read(120).decode(errors="ignore")
    except Exception as e:
        return -1, str(e)[:80]


print("== same prompt 'cat' across 5 models ==")
for m in MODELS:
    code, out = gen(m, "cat")
    tail = out[-40:] if code == 200 else out
    print(f"{m:22s} {code} {tail}")

print()
print("== hit-rate probe: 12 common nouns on flux-krea-10 ==")
nouns = ["cat", "dog", "dragon", "sun", "moon", "tree",
         "flower", "house", "car", "bird", "fire", "water"]
hit = 0
for p in nouns:
    code, out = gen("funai-flux-krea-10", p)
    ok = code == 200
    hit += ok
    tail = out[-40:] if ok else out[:60]
    print(f"{p:10s} {code} {tail}")
print(f"hit rate: {hit}/{len(nouns)}")
