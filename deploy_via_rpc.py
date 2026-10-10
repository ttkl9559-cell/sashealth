# -*- coding: utf-8 -*-
"""开发调试用：经应用中心内部 Unix socket RPC 安装/升级本机 fpk。

Deploy 0.8.1: update -> verify disk -> force reinstall if stale -> start -> verify.

普通用户请直接用应用中心「手动安装」，无需运行本脚本。
本脚本依赖飞牛应用中心的内部接口，仅作者调试时使用，飞牛版本变化可能失效。
"""
import http.client, json, socket, subprocess, time

# 改成你 NAS 上实际存放 fpk 的路径，别把个人目录提交到公开仓库
FPK = "/tmp/sashealth_0.8.1_x86.fpk"
SOCK = "/var/run/com.trim.app.center.sock"

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
        return {"_raw": raw[:200]}

def wait_task(conn, tid, secs=180):
    for i in range(secs // 3):
        s2 = rpc(conn, "/rpc/v1/common/status", {"taskId": tid})
        d = s2.get("data") or {}
        if d.get("status") in (2, 3, -1):
            return d
        time.sleep(3)
    return {"status": "timeout"}

def stage(conn, fpk):
    r = rpc(conn, "/rpc/v1/download/task", {"packageSourceType": "file", "path": fpk})
    tid = (r.get("data") or {}).get("downloadTaskId")
    if not tid:
        return None
    d = {}
    for i in range(25):
        st = rpc(conn, "/rpc/v1/download/status", {"downloadTaskId": tid})
        d = st.get("data") or {}
        if d.get("status") in (2, 3, -1):
            break
        time.sleep(2)
    return d if d.get("status") == 2 else None

def disk_version():
    try:
        with open("/var/apps/sashealth/target/server/app.py", encoding="utf-8") as f:
            for line in f:
                if "0.8.1" in line:
                    return True
    except Exception:
        pass
    return False

def kill_port(port):
    p = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if ":" + str(port) + " " in line:
            import re
            m = re.search(r"pid=(\d+)", line)
            if m:
                subprocess.run(["kill", "-9", m.group(1)], capture_output=True)
                time.sleep(2)

def start(conn):
    r = rpc(conn, "/rpc/v1/start/task", {"appName": "sashealth"})
    tid = (r.get("data") or {}).get("taskId")
    if not tid:
        return "code=%s" % r.get("code")
    for i in range(30):
        s2 = rpc(conn, "/rpc/v1/common/status", {"taskId": tid})
        d = s2.get("data") or {}
        if d.get("status") in (2, 3, -1):
            return d.get("status")
        time.sleep(2)
    return "timeout"

def http_status():
    try:
        import urllib.request
        with urllib.request.urlopen("http://127.0.0.1:7766/api/status", timeout=8) as resp:
            return resp.read().decode()[:120]
    except Exception as e:
        return "err: %s" % e

conn = UnixConn(SOCK)

# path 1: update channel
d = stage(conn, FPK)
if d:
    r2 = rpc(conn, "/rpc/v1/update/task",
             {"appName": "sashealth", "updateVersion": "0.8.1",
              "packageType": d.get("packageType") or "fpk",
              "systemParameters": {"agreedToProtocol": True, "installVolumeID": 7,
                                   "dataVolumeId": 7, "immediateStart": False},
              "customParameters": [], "language": "zh-CN"})
    tid2 = (r2.get("data") or {}).get("taskId")
    if tid2:
        print("update ->", wait_task(conn, tid2).get("status"))
print("disk has 0.8.1:", disk_version())

# path 2: force reinstall if stale
if not disk_version():
    print("update was fake; force reinstall")
    r = rpc(conn, "/rpc/v1/uninstall/task", {"appName": "sashealth"})
    tid = (r.get("data") or {}).get("taskId")
    if tid:
        wait_task(conn, tid)
    time.sleep(3)
    d = stage(conn, FPK)
    if not d:
        raise SystemExit("stage failed")
    body = {"appName": "sashealth", "version": "0.8.1",
            "packageType": d.get("packageType") or "fpk",
            "systemParameters": {"agreedToProtocol": True, "installVolumeID": 7,
                                 "dataVolumeId": 7, "immediateStart": False},
            "customParameters": [], "language": "zh-CN"}
    r2 = rpc(conn, "/rpc/v1/install/task", body)
    tid2 = (r2.get("data") or {}).get("taskId")
    if tid2:
        print("install ->", wait_task(conn, tid2).get("status"))
    print("disk has 0.8.1 (after reinstall):", disk_version())

kill_port(7766)
print("start ->", start(conn))
time.sleep(2)
print("status:", http_status())

