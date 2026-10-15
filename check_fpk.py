# -*- coding: utf-8 -*-
import gzip, hashlib, io, tarfile

P = r"C:\Users\Administrator\AppData\Local\Temp\sashealth_build\sashealth_0.11.0_x86.fpk"
raw = gzip.decompress(open(P, "rb").read())
tf = tarfile.open(fileobj=io.BytesIO(raw))
names = [m.name for m in tf.getmembers()]
print("fpk entries:", names)
man = tf.extractfile("manifest").read().decode("utf-8")
print("---- manifest ----")
print(man)
app_tgz = tf.extractfile("app.tgz").read()
atf = tarfile.open(fileobj=io.BytesIO(gzip.decompress(app_tgz)))
inner = [m.name for m in atf.getmembers()]
print("app.tgz entries:", inner)
code = atf.extractfile("server/app.py").read().decode("utf-8")
print("code has 0.10.0:", "0.11.0" in code)
print("code has /api/notify:", "/api/notify" in code)
print("code has notify.conf:", "notify.conf" in code)
print("code has mailstate:", "mailstate.conf" in code)
print("code has deltas:", "compute_deltas" in code)
print("md5 matches manifest:", hashlib.md5(app_tgz).hexdigest() in man)
cfg = atf.extractfile("ui/config").read().decode("utf-8")
print("ui/config ok:", "sashealth.Application" in cfg)
