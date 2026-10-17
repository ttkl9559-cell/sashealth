# -*- coding: utf-8 -*-
"""HTTP-layer regression test: /api/notify/test must answer promptly (no blocked handler)."""
import importlib.util, io, json, os, re, sys, tempfile, threading, time, urllib.request, urllib.error
from http.server import ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
src = io.open(os.path.join(BASE, "build_fpk.py"), encoding="utf-8").read()
m = re.search(r"APP_PY = r'''(.*?)\n'''\n\n# sanity check", src, re.S)
app = m.group(1)
app = app.replace('threading.Thread(target=_auto_thread, daemon=True).start()', '')
app = app.replace('ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()', '')

TMP = os.path.join(tempfile.gettempdir(), "sashealth_http_test")
os.makedirs(os.path.join(TMP, "snapshots"), exist_ok=True)
os.environ["TRIM_PKGVAR"] = TMP
os.environ["TRIM_SERVICE_PORT"] = "7802"
mod = type(sys)("sashealth_http")
mod.__dict__["__file__"] = os.path.join(BASE, "app_inline.py")
exec(compile(app, "app_inline.py", "exec"), mod.__dict__)

calls = []
mod.send_sct = lambda cfg, t, d: (calls.append("sct") or (True, ""))
mod.send_mail = lambda cfg, s, b: (calls.append("mail") or (True, ""))
mod.write_notify_cfg({"on": True, "sct_on": True, "host": "h", "user": "u",
                      "password": "p", "to": "t", "sct_key": "K"})

srv = ThreadingHTTPServer(("127.0.0.1", 7802), mod.H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.5)

results = []
def post(path, payload, timeout=10):
    data = json.dumps(payload).encode()
    r = urllib.request.Request("http://127.0.0.1:7802" + path, data=data,
                               headers={"Content-Type": "application/json"}, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode()), time.time() - t0
    except Exception as e:
        return None, str(e), time.time() - t0

st, j, el = post("/api/notify/test", {"channel": "sct"})
results.append(("POST /api/notify/test (sct) 有响应", st == 200))
results.append(("  响应在 5 秒内（旧版此处永久挂起）", el < 5.0))
results.append(("  ok=true 且走了 sct 通道", isinstance(j, dict) and j.get("ok") is True and calls and calls[-1] == "sct"))
results.append(("  响应含 detail 字段", isinstance(j, dict) and "detail" in j))

st2, j2, el2 = post("/api/notify/test", {"channel": "mail"})
results.append(("POST /api/notify/test (mail) 有响应", st2 == 200 and el2 < 5.0))
results.append(("  ok=true 且走了 mail 通道", isinstance(j2, dict) and j2.get("ok") is True and calls[-1] == "mail"))

st3, j3, el3 = post("/api/notify/test", {})
results.append(("缺省 channel 默认走邮件", st3 == 200 and isinstance(j3, dict) and j3.get("ok") is True and calls[-1] == "mail"))

st4, j4, el4 = post("/api/notify", {"on": True, "sct_on": True, "sct_key": ""})
results.append(("POST /api/notify 不挂起", st4 == 200))
st5, j5, el5 = post("/api/autosnap", {"on": True})
results.append(("POST /api/autosnap 不挂起", st5 == 200))

r = urllib.request.urlopen("http://127.0.0.1:7802/api/notify", timeout=10)
gf = json.loads(r.read().decode())
results.append(("GET /api/notify 脱敏 sct_key", gf.get("sct_key") == "" and gf.get("has_sct_key") is True))
results.append(("GET /api/notify 脱敏 password", gf.get("password") == "" and gf.get("has_password") is True))

calls.clear()
st6, j6, _ = post("/api/notify/test", {"channel": "sct"})
results.append(("严格：点测试微信 -> 只发微信", calls == ["sct"]))
results.append(("  响应回显 channel=sct", isinstance(j6, dict) and j6.get("channel") == "sct"))
calls.clear()
st7, j7, _ = post("/api/notify/test", {"channel": "mail"})
results.append(("严格：点测试邮件 -> 只发邮件", calls == ["mail"]))
results.append(("  响应回显 channel=mail", isinstance(j7, dict) and j7.get("channel") == "mail"))

bad = 0
print("=== HTTP LAYER ===")
for name, ok in results:
    print(("PASS  " if ok else "FAIL  ") + name)
    if not ok:
        bad += 1
print("")
print("HTTP TOTAL %d, FAIL %d" % (len(results), bad))
srv.shutdown()
