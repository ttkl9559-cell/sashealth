# -*- coding: utf-8 -*-
import os, sys, tempfile
BASE = r"C:\Users\Administrator\Desktop\sashealth-发布"
TMP = os.path.join(tempfile.gettempdir(), "sashealth_ui_appdata")
os.makedirs(os.path.join(TMP, "snapshots"), exist_ok=True)
os.environ["TRIM_PKGVAR"] = TMP
os.environ["TRIM_SERVICE_PORT"] = "7799"
sys.path.insert(0, BASE)
import verify_app as A
from http.server import ThreadingHTTPServer

AUTO = A.PAGE.replace("load(0);setInterval(()=>load(0),300000);",
                      "load(0);setTimeout(function(){notifyOpen()},200);")

class H(A.H):
    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/verify_ui":
            self._send(200, "text/html; charset=utf-8", AUTO.encode())
            return
        A.H.do_GET(self)

print("listening 7799", flush=True)
ThreadingHTTPServer(("127.0.0.1", 7799), H).serve_forever()
