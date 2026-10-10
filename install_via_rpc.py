# -*- coding: utf-8 -*-
"""开发调试用：经应用中心内部 Unix socket RPC 做全新安装测试。

Fresh install test: uninstall -> install 0.6.0 -> check ui/ extraction.

普通用户请直接用应用中心「手动安装」，无需运行本脚本。
本脚本依赖飞牛应用中心的内部接口，仅作者调试时使用，飞牛版本变化可能失效。
"""
import http.client, json, socket, sys, time

SOCK = "/var/run/com.trim.app.center.sock"
# 改成你 NAS 上实际存放 fpk 的路径，别把个人目录提交到公开仓库
FPK = "/tmp/sashealth_0.6.1_x86.fpk"

class UnixConn(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost")
        self.path_ = path
    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(90)
        s.connect(self.path_)
        self.sock = s

def rpc(conn, path, body):
    conn.request("POST", path, body=json.dumps(body).encode(),
                 headers={"Content-Type": "application/json"})
    raw = conn.getresponse().read().decode("utf-8", "replace")
    try:
        return json.loads(raw)
    except Exception:
        return {"_raw": raw[:300]}

def wait_task(conn, tid, secs=120):
    for i in range(secs // 3):
        s2 = rpc(conn, "/rpc/v1/common/status", {"taskId": tid})
        d = s2.get("data") or {}
        if d.get("status") in (2, 3, -1):
            return d
        time.sleep(3)
    return {"status": "timeout"}

conn = UnixConn(SOCK)

# uninstall
r = rpc(conn, "/rpc/v1/uninstall/task", {"appName": "sashealth"})
tid = (r.get("data") or {}).get("taskId")
print("UNINSTALL:", json.dumps(r, ensure_ascii=False)[:150])
if tid:
    print(" ->", wait_task(conn, tid).get("status"))
time.sleep(3)

# stage
r = rpc(conn, "/rpc/v1/download/task", {"packageSourceType": "file", "path": FPK})
tid = (r.get("data") or {}).get("downloadTaskId")
if not tid:
    sys.exit("stage failed")
d = {}
for i in range(25):
    st = rpc(conn, "/rpc/v1/download/status", {"downloadTaskId": tid})
    d = st.get("data") or {}
    if d.get("status") in (2, 3, -1):
        break
    time.sleep(2)
print("STAGED:", d.get("status") == 2)

# fresh install
body = {"appName": "sashealth", "version": "0.6.1",
        "packageType": d.get("packageType") or "fpk",
        "systemParameters": {"agreedToProtocol": True, "installVolumeID": 7,
                             "dataVolumeId": 7, "immediateStart": True},
        "customParameters": [], "language": "zh-CN"}
r2 = rpc(conn, "/rpc/v1/install/task", body)
tid2 = (r2.get("data") or {}).get("taskId")
print("INSTALL task:", json.dumps(r2, ensure_ascii=False)[:150])
if tid2:
    print("INSTALL ->", wait_task(conn, tid2, 150).get("status"))

