# -*- coding: utf-8 -*-
"""Stop-then-start to clear stuck state."""
import http.client, json, socket, subprocess, time, re

SOCK = "/var/run/com.trim.app.center.sock"

class UnixConn(http.client.HTTPConnection):
    def __init__(self, path):
        super().__init__("localhost")
        self.path_ = path
    def connect(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(60)
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

def wait_task(conn, tid, secs=90):
    for i in range(secs // 3):
        s2 = rpc(conn, "/rpc/v1/common/status", {"taskId": tid})
        d = s2.get("data") or {}
        if d.get("status") in (2, 3, -1):
            return d
        time.sleep(2)
    return {"status": "timeout"}

def kill_port(port):
    p = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
    for line in p.stdout.splitlines():
        if ":" + str(port) + " " in line:
            m = re.search(r"pid=(\d+)", line)
            if m:
                subprocess.run(["kill", "-9", m.group(1)], capture_output=True)
                time.sleep(2)

conn = UnixConn(SOCK)
r = rpc(conn, "/rpc/v1/stop/task", {"appName": "sashealth"})
tid = (r.get("data") or {}).get("taskId")
if tid:
    print("stop ->", wait_task(conn, tid).get("status"))
time.sleep(2)
kill_port(7766)
r = rpc(conn, "/rpc/v1/start/task", {"appName": "sashealth"})
tid = (r.get("data") or {}).get("taskId")
if tid:
    print("start ->", wait_task(conn, tid).get("status"))
time.sleep(3)
try:
    import urllib.request
    with urllib.request.urlopen("http://127.0.0.1:7766/api/status", timeout=8) as resp:
        print("status:", resp.read().decode()[:120])
except Exception as e:
    print("status err:", e)
