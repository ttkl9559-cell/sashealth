# -*- coding: utf-8 -*-
import importlib.util, os, re, tempfile, time

BASE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(BASE, "build_fpk.py"), encoding="utf-8").read()

m = re.search(r"APP_PY = r'''(.*?)\n'''\n\n# sanity check", src, re.S)
assert m, "APP_PY not found"
app = m.group(1)
print("APP_PY extracted:", len(app), "chars")

m2 = re.search(r'PAGE = r"""(.*?)"""\.replace\("__PORT__", str\(PORT\)\)', app, re.S)
assert m2, "PAGE not found"
page = m2.group(1).replace("__PORT__", "7766")
probe = "<script>document.title='PARSE_OK:'+[typeof load,typeof render,typeof histTable,typeof histMore,typeof notifyOpen,typeof nfForm,typeof notifySave,typeof notifyTest,typeof nfProv].join(',');</script>"
html = page.replace("</body>", probe + "</body>")
open(os.path.join(BASE, "verify_page.html"), "w", encoding="utf-8").write(html)
print("verify_page.html written:", len(html), "chars")

ready = app.replace('threading.Thread(target=_auto_thread, daemon=True).start()', '')
ready = ready.replace('ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()', '')
open(os.path.join(BASE, "verify_app.py"), "w", encoding="utf-8").write(ready)
print("verify_app.py written:", len(ready), "chars")

TMP = os.path.join(tempfile.gettempdir(), "sashealth_test_appdata")
os.makedirs(TMP, exist_ok=True)
os.makedirs(os.path.join(TMP, "snapshots"), exist_ok=True)
for f in os.listdir(TMP):
    p = os.path.join(TMP, f)
    if os.path.isfile(p):
        try: os.remove(p)
        except Exception: pass
os.environ["TRIM_PKGVAR"] = TMP

spec = importlib.util.spec_from_file_location("vapp", os.path.join(BASE, "verify_app.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("module loaded, DATA_DIR =", mod.DATA_DIR)

results = []
def check(name, cond, extra=""):
    results.append((name, bool(cond), str(extra)[:160]))

state = {"ok": True, "sent": []}
def fake_send(cfg, subject, body):
    state["sent"].append((subject, body))
    if state["ok"]:
        return True, ""
    return False, "authentication failed (535)"
mod.send_mail = fake_send

def disk(serial, kind, sev=0, reason="", **kw):
    d = {"dev": "/dev/sd?" if serial == "?" else "/dev/sd1", "serial": serial, "model": "MODEL",
         "capacity_h": "4.0 TB", "vol": "存储空间 3", "defects": 0, "uncorr": 0, "rr_total": 0,
         "reallocated": 0, "pending": 0, "smart_ok": True, "temp": 30, "protocol": "SCSI",
         "grade": "r" if kind else "g", "reason": reason or ("故障" if kind else "正常"),
         "kind": kind, "sev": sev}
    d.update(kw)
    return d

mod.write_notify_cfg({"on": True, "host": "smtp.test", "user": "a@b.c", "password": "x", "to": "d@e.f"})

r = mod.eval_notify([disk("SN1", "uncorr", 5, "存在 5 个不可纠正错误")], int(time.time()))
check("首次基线不发信", r is None and state["sent"] == [], r)

r = mod.eval_notify([disk("SN1", "uncorr", 5, "存在 5 个不可纠正错误")], int(time.time()))
check("同故障未变化不再发", r is None and len(state["sent"]) == 0, r)

r = mod.eval_notify([disk("SN1", "uncorr", 7, "存在 7 个不可纠正错误")], int(time.time()))
check("恶化重发", r is not None and r.get("ok") and len(state["sent"]) == 1, r)
check("主题为N块异常", state["sent"] and "1 块异常" in state["sent"][-1][0], state["sent"][-1][0] if state["sent"] else "")

r = mod.eval_notify([disk("SN1", None)], int(time.time()))
check("红转正常发恢复", r is not None and r.get("ok") and "已恢复" in state["sent"][-1][0], state["sent"][-1][0])

state["ok"] = False
r = mod.eval_notify([disk("SN2", "smart_failed", 0, "SMART 判定失败")], int(time.time()))
check("发送失败不写状态", r is not None and r.get("ok") is False, r)
st = mod.load_state()
check("失败后状态未记录 SN2", "SN2" not in (st.get("disks") or {}), st.get("disks"))
state["ok"] = True
n0 = len(state["sent"])
r = mod.eval_notify([disk("SN2", "smart_failed", 0, "SMART 判定失败")], int(time.time()))
check("失败后自动重试成功", r is not None and r.get("ok") and len(state["sent"]) == n0 + 1, r)

mod.write_notify_cfg({"on": True, "host": "smtp.test", "user": "a@b.c", "password": "x", "to": "d@e.f"})
mod.save_state({})
state["sent"] = []
mod.eval_notify([disk("SN5", "defects_growth", 1, "缺陷列表增长 +1")], int(time.time()))
r = mod.eval_notify([disk("SN5", "defects_growth", 3, "缺陷列表增长 +3")], int(time.time()))
body = state["sent"][-1][1] if state["sent"] else ""
check("正文含存储空间/型号/序列号/容量", all(x in body for x in ["存储空间 3", "MODEL", "SN5", "4.0 TB"]), body[:120])
check("正文含故障内容", "缺陷列表增长" in body, "")
check("正文含检测时间", "检测时间" in body, "")

mod.save_state({})
state["sent"] = []
r = mod.eval_notify([disk("?", "pending", 3, "待映射/不可映射扇区 3")], int(time.time()))
check("无序列号：首次只建基线", r is None, r)
st = mod.load_state()
check("无序列号：设备名兜底入库", "/dev/sd?" in (st.get("disks") or {}), st.get("disks"))
r = mod.eval_notify([disk("?", "pending", 5, "待映射/不可映射扇区 5")], int(time.time()))
check("无序列号：恶化仍可识别", r is not None and r.get("ok"), r)

mod.write_notify_cfg({"on": False, "host": "smtp.test", "user": "a@b.c", "password": "x", "to": "d@e.f"})
mod.save_state({})
n1 = len(state["sent"])
r = mod.eval_notify([disk("SN9", "uncorr", 4, "存在 4 个不可纠正错误")], int(time.time()))
check("总开关关闭不评估不写状态", r is None and len(state["sent"]) == n1 and not mod.load_state(), r)
mod.write_notify_cfg({"on": True, "host": "smtp.test", "user": "a@b.c", "password": "x", "to": "d@e.f"})

g = mod.grade(disk("X1", None, smart_ok=False), None)
check("grade SMART失败=红/smart_failed", g[0] == "r" and g[2] == "smart_failed", g)
g = mod.grade(disk("X1", None, pending=2, protocol="ATA"), None)
check("grade 待映射=红/pending", g[0] == "r" and g[2] == "pending" and g[3] == 2, g)
g = mod.grade(disk("X1", None, reallocated=4, protocol="ATA"), None)
check("grade 历史重分配=黄无kind", g[0] == "y" and g[2] is None, g)
prev = {"disks": [{"serial": "X1", "dev": "/dev/sd1", "defects": 3, "reallocated": 0, "pending": 0, "smart_ok": True}]}
g = mod.grade(disk("X1", None, defects=5), prev)
check("grade 缺陷增长=红且sev=2", g[0] == "r" and g[2] == "defects_growth" and g[3] == 2, g)

deltas = mod.compute_deltas([{"serial": "X1", "dev": "/dev/sd1", "defects": 5, "uncorr": 0,
                              "rr_total": 0, "reallocated": 0, "pending": 0, "smart_ok": True}], prev)
check("compute_deltas 生成缺陷增量", "X1" in deltas and "缺陷数 3" in deltas["X1"][0], deltas)

short = mod.short_err("(535, b'Authentication Credentials Invalid')")
check("错误短文案=认证失败", "认证失败" in short, short)
short2 = mod.short_err("[Errno 11001] getaddrinfo failed")
check("错误短文案=解析失败", "解析" in short2 or "地址" in short2, short2)

print("")
print("=== RESULTS ===")
bad = 0
for name, ok, extra in results:
    print(("PASS  " if ok else "FAIL  ") + name + ("" if ok else ("   <- " + extra)))
    if not ok:
        bad += 1
print("")
print("TOTAL %d, FAIL %d" % (len(results), bad))
