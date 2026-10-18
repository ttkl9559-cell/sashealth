# -*- coding: utf-8 -*-
"""Build sashealth 0.12.0 - disk health viewer + alerts + update banner."""
import gzip, hashlib, io, math, os, struct, tarfile, zlib

OUT = r"C:\Users\Administrator\AppData\Local\Temp\sashealth_build"
os.makedirs(OUT, exist_ok=True)
AMP = chr(38)

def png_chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

def make_icon(size):
    W = H = size
    base = (30, 110, 200); dark = (18, 70, 130); glyph = (245, 245, 245)
    rows = []; rad = size * 0.20
    for y in range(H):
        row = bytearray([0])
        for x in range(W):
            cx = min(x, W - 1 - x); cy = min(y, H - 1 - y)
            inside = True
            if cx < rad and cy < rad:
                dx = rad - cx; dy = rad - cy
                inside = dx * dx + dy * dy <= rad * rad * 1.25
            if not inside:
                row += bytes((0, 0, 0, 0)); continue
            px = base
            if size >= 48:
                mx = my = size / 2.0
                d = math.hypot(x - mx, y - my)
                R = size * 0.30; th = max(2, size * 0.05)
                ang = math.atan2(-(y - my), x - mx)
                if abs(d - R) <= th / 2:
                    px = glyph if (-0.5 < ang < 2.3) else dark
                nv = (x - mx) * 0.7071 - (y - my) * 0.7071
                nw = (x - mx) * 0.7071 + (y - my) * 0.7071
                if 0 <= nv <= R * 0.72 and abs(nw) <= size * 0.028:
                    px = glyph
                if d <= size * 0.055:
                    px = glyph
            row += bytes((px[0], px[1], px[2], 255))
        rows.append(bytes(row))
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + png_chunk(b"IEND", b""))

def gz(data):
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as g:
        g.write(data)
    return buf.getvalue()

UID, GID, UNAME = 1001, 1001, "runner"

def tar_add(tf, name, data=None, mode=0o644, isdir=False):
    ti = tarfile.TarInfo(name)
    ti.uid = UID; ti.gid = GID; ti.uname = UNAME; ti.gname = UNAME
    ti.mtime = 0
    if isdir:
        ti.type = tarfile.DIRTYPE; ti.mode = 0o755; ti.size = 0
        tf.addfile(ti)
    else:
        ti.mode = mode; ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))

MANIFEST = (
    "appname         = sashealth\n"
    "version         = 0.12.0\n"
    "display_name    = SAS 硬盘健康\n"
    "desc            = SAS/SATA 硬盘 SMART 健康查看器：健康总览、单盘详情、缺陷增长历史快照、异常邮件提醒、Server酱微信推送\n"
    "arch            = x86_64\n"
    "source          = thirdparty\n"
    "desktop_uidir   = ui\n"
    "desktop_applaunchname = sashealth.Application\n"
    "maintainer      = sashealth\n"
    "maintainer_url  = https://github.com/__YOUR_GITHUB_USERNAME__/sashealth\n"
    "distributor     = sashealth\n"
    "distributor_url = https://github.com/__YOUR_GITHUB_USERNAME__/sashealth\n"
    "service_port    = 7766\n"
    "ctl_stop        = true\n"
    "platform        = \n"
    "install_type    = root\n"
    "checksum        = {md5}\n"
)

PRIVILEGE = '{\n    "defaults": {\n        "run-as": "root"\n    }\n}\n'

RESOURCE = ('{\n'
            '    "data-share":\n'
            '    {\n'
            '        "shares": [\n'
            '            {\n'
            '                "name": "sashealth",\n'
            '                "permission":\n'
            '                {\n'
            '                    "rw": ["sashealth"]\n'
            '                }\n'
            '            }\n'
            '        ]\n'
            '    }\n'
            '}\n')

UI_CONFIG = ('{\n'
             '    ".url": {\n'
             '        "sashealth.Application":\n'
             '        {\n'
             '            "title": "SAS 硬盘健康",\n'
             '            "desc": "SAS/SATA 硬盘 SMART 健康查看器",\n'
             '            "icon": "images/icon_{0}.png",\n'
             '            "type": "url",\n'
             '            "port": "7766",\n'
             '            "protocol": "http",\n'
             '            "url": "/",\n'
             '            "allUsers": true\n'
             '        }\n'
             '    }\n'
             '}\n')
CMD_MAIN = '''#!/bin/bash
set -u
APP_NAME="${TRIM_APPNAME:-sashealth}"
APP_DIR="${TRIM_APPDEST:-/var/apps/${APP_NAME}}"
DATA_DIR="${TRIM_PKGVAR:-/vol4/@appdata/${APP_NAME}}"
PORT="${TRIM_SERVICE_PORT:-7766}"
LOG="${DATA_DIR}/sashealth.log"
PID_FILE="${DATA_DIR}/sashealth.pid"

find_server() {
    if [ -d "${APP_DIR}/server" ]; then echo "${APP_DIR}/server"; return 0; fi
    if [ -d "${APP_DIR}/target/server" ]; then echo "${APP_DIR}/target/server"; return 0; fi
    return 1
}

start() {
    mkdir -p "${DATA_DIR}"
    if [ -f "${PID_FILE}" ] __AMP____AMP__ kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
        echo "already running (pid $(cat "${PID_FILE}"))"; return 0
    fi
    SRC=$(find_server) || { echo "ERROR: server dir not found"; return 1; }
    if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
        echo "ERROR: port ${PORT} already in use"; return 1
    fi
    cd "${SRC}" || return 1
    nohup /usr/bin/python3 -u app.py >> "${LOG}" 2>__AMP__1 < /dev/null __AMP__
    PID=$!
    echo "${PID}" > "${PID_FILE}"
    for i in $(seq 1 15); do
        if curl -sf "http://127.0.0.1:${PORT}/api/status" >/dev/null 2>__AMP__1; then
            echo "started (pid ${PID})"; return 0
        fi
        sleep 1
    done
    echo "started (health check timeout)"; return 0
}

stop() {
    if [ -f "${PID_FILE}" ]; then
        kill "$(cat "${PID_FILE}")" 2>/dev/null || true
        rm -f "${PID_FILE}"
    fi
    pkill -f "sashealth.*app.py" 2>/dev/null || true
    pkill -f "app.py" 2>/dev/null || true
    sleep 1
    echo "stopped"
}

status() {
    if [ -f "${PID_FILE}" ] __AMP____AMP__ kill -0 "$(cat "${PID_FILE}")" 2>/dev/null; then
        echo "running (pid $(cat "${PID_FILE}"))"; return 0
    fi
    echo "stopped"; return 1
}

case "${1:-start}" in
    start) start ;;
    stop) stop ;;
    status) status ;;
    restart) stop; sleep 1; start ;;
    *) echo "Usage: $0 {start|stop|status|restart}"; exit 1 ;;
esac
'''.replace("__AMP__", AMP)

INSTALL_CALLBACK = '''#!/bin/bash
set -u
DATA_DIR="${TRIM_PKGVAR:-/vol4/@appdata/${TRIM_APPNAME:-sashealth}}"
mkdir -p "${DATA_DIR}" 2>/dev/null
exit 0
'''
APP_PY = r'''# -*- coding: utf-8 -*-
"""SAS/SATA 硬盘 SMART 健康查看器 for fnOS (root app, stdlib only)."""
import glob, json, os, re, smtplib, socket, subprocess, threading, time
import urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get("TRIM_SERVICE_PORT", "7766"))
DATA_DIR = os.environ.get("TRIM_PKGVAR", "/usr/local/apps/@appdata/sashealth")
SNAP_DIR = os.path.join(DATA_DIR, "snapshots")
SMARTCTL = "/usr/sbin/smartctl"
CACHE_TTL = 60
AUTO_SNAP_SECS = 6 * 3600

os.makedirs(SNAP_DIR, exist_ok=True)
AUTO_FLAG = os.path.join(SNAP_DIR, "autosnap.off")

def autosnap_on():
    return not os.path.exists(AUTO_FLAG)

INTERVAL_FILE = os.path.join(SNAP_DIR, "interval.conf")
INTERVAL_PRESETS = (6, 12, 24, 72, 168)

def read_interval_h():
    try:
        with open(INTERVAL_FILE, encoding="utf-8") as fh:
            v = int(fh.read().strip())
        if v in INTERVAL_PRESETS:
            return v
    except Exception:
        pass
    return 6

SNAP_KEEP_DAYS = 180
SNAP_KEEP_MAX = 500
CHANGE_KEYS = ("defects", "uncorr", "rr_total", "reallocated", "pending")

# ---------------- 邮件通知（配置 / 状态 / 发送） ----------------

NOTIFY_FILE = os.path.join(DATA_DIR, "notify.conf")
MAILSTATE_FILE = os.path.join(DATA_DIR, "mailstate.conf")

MAIL_PROVIDERS = (
    ("qq", "QQ 邮箱", "smtp.qq.com", 465, "ssl"),
    ("163", "163 邮箱", "smtp.163.com", 465, "ssl"),
    ("126", "126 邮箱", "smtp.126.com", 465, "ssl"),
    ("exmail", "腾讯企业邮", "smtp.exmail.qq.com", 465, "ssl"),
    ("gmail", "Gmail（国内网络不可达）", "smtp.gmail.com", 465, "ssl"),
    ("outlook", "Outlook / Office365", "smtp.office365.com", 587, "starttls"),
    ("custom", "自定义", "", 465, "ssl"),
)

DEFAULT_NOTIFY = {
    "on": False, "provider": "qq", "host": "smtp.qq.com", "port": 465,
    "secure": "ssl", "user": "", "password": "", "sender": "", "to": "",
    "sct_on": False, "sct_key": "",
}

FAULT_LABEL = {
    "smart_failed": "SMART 判定失败",
    "uncorr": "不可纠正错误",
    "defects_growth": "缺陷列表增长",
    "pending": "待映射/不可映射扇区",
    "realloc_growth": "重分配扇区增长",
}

def read_notify_cfg():
    cfg = dict(DEFAULT_NOTIFY)
    try:
        with open(NOTIFY_FILE, encoding="utf-8") as fh:
            j = json.load(fh)
        if isinstance(j, dict):
            for k in DEFAULT_NOTIFY:
                if k in j:
                    cfg[k] = j[k]
    except Exception:
        pass
    return cfg

def write_notify_cfg(cfg):
    out = dict(DEFAULT_NOTIFY)
    for k in DEFAULT_NOTIFY:
        if k in cfg:
            out[k] = cfg[k]
    with open(NOTIFY_FILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    return out

def load_state():
    try:
        with open(MAILSTATE_FILE, encoding="utf-8") as fh:
            j = json.load(fh)
        if isinstance(j, dict):
            return j
    except Exception:
        pass
    return {}

def save_state(st):
    try:
        with open(MAILSTATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
    except Exception:
        pass

def disk_key(d):
    s = d.get("serial")
    if s and s != "?":
        return s
    return d.get("dev") or "?"

def short_err(msg):
    m = (msg or "").strip().replace("\n", " ")
    low = m.lower()
    if "auth" in low or "535" in m or "username and password" in low:
        return "认证失败（账号或授权码错误）"
    if "timed out" in low or "timeout" in low:
        return "连接超时"
    if "getaddrinfo" in low or "name or service not known" in low or "11001" in m:
        return "无法解析邮件服务器地址"
    if "refused" in low:
        return "服务器拒绝连接"
    if "550" in m or "recipient" in low:
        return "收件人被拒"
    if "ssl" in low or "certificate" in low:
        return "SSL/TLS 握手失败"
    if "unreachable" in low:
        return "网络不可达"
    if "400" in m or "bad request" in low or "404" in m:
        return "请求被拒（SendKey 可能无效）"
    return (m[:40] + "…") if len(m) > 40 else (m or "未知错误")

APP_VERSION = "0.12.0"
UPDATE_FILE = os.path.join(DATA_DIR, "update.conf")
UPDATE_INTERVAL = 24 * 3600
UPDATE_RETRY = 6 * 3600
RELEASE_LATEST = "https://github.com/ttkl9559-cell/sashealth/releases/latest"

def vtup(v):
    out = []
    for p in (v or "").strip().lstrip("vV").split("."):
        n = ""
        for ch in p:
            if ch.isdigit():
                n += ch
            else:
                break
        out.append(int(n) if n else 0)
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])

def read_update_cache():
    try:
        with open(UPDATE_FILE, encoding="utf-8") as fh:
            j = json.load(fh)
        if isinstance(j, dict):
            return j
    except Exception:
        pass
    return {}

def check_update(force=False):
    now = time.time()
    c = read_update_cache()
    last_try = c.get("last_try") or 0
    wait = UPDATE_RETRY if c.get("err") else UPDATE_INTERVAL
    if not force and now - last_try < wait:
        return c
    latest = c.get("latest") or ""
    url = c.get("url") or ""
    err = ""
    try:
        req = urllib.request.Request(RELEASE_LATEST, method="HEAD")
        req.add_header("User-Agent", "sashealth/%s" % APP_VERSION)
        with urllib.request.urlopen(req, timeout=8) as resp:
            final = resp.geturl() or ""
        tag = final.rstrip("/").split("/")[-1]
        if tag and tag[0] in "vV" and any(ch.isdigit() for ch in tag):
            latest = tag.lstrip("vV")
            url = "https://github.com/ttkl9559-cell/sashealth/releases/tag/v" + latest
    except Exception as e:
        err = short_err(str(e))
    c = {"last_try": now, "latest": latest, "url": url}
    if err:
        c["err"] = err
    try:
        with open(UPDATE_FILE, "w", encoding="utf-8") as fh:
            json.dump(c, fh, ensure_ascii=False)
    except Exception:
        pass
    return c

def update_info(network=False):
    c = check_update() if network else read_update_cache()
    latest = c.get("latest") or ""
    newer = bool(latest) and vtup(latest) > vtup(APP_VERSION)
    return {"current": APP_VERSION, "latest": latest, "newer": newer,
            "url": c.get("url") or ""}

def _update_thread():
    while True:
        try:
            check_update()
        except Exception:
            pass
        time.sleep(3600)

def lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return ""

def send_mail(cfg, subject, body):
    from email.mime.text import MIMEText
    from email.header import Header
    host = (cfg.get("host") or "").strip()
    user = (cfg.get("user") or "").strip()
    pwd = cfg.get("password") or ""
    sender = (cfg.get("sender") or "").strip() or user
    to = (cfg.get("to") or "").strip()
    if not host or not user or not pwd or not to:
        return False, "配置不完整（缺少服务器/账号/授权码/收件人）"
    try:
        port = int(cfg.get("port") or 465)
    except Exception:
        port = 465
    sec = (cfg.get("secure") or "ssl").lower()
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = sender
    msg["To"] = to
    srv = None
    try:
        if sec == "ssl":
            srv = smtplib.SMTP_SSL(host, port, timeout=15)
        else:
            srv = smtplib.SMTP(host, port, timeout=15)
        if sec == "starttls":
            srv.starttls()
        srv.login(user, pwd)
        rcpts = [x.strip() for x in to.split(",") if x.strip()]
        srv.sendmail(sender, rcpts, msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)
    finally:
        if srv is not None:
            try:
                srv.quit()
            except Exception:
                pass

def send_sct(cfg, title, desp):
    """Server酱: POST https://sctapi.ftqq.com/<SendKey>.send (title + desp)."""
    key = (cfg.get("sct_key") or "").strip()
    if not key:
        return False, "未配置 SendKey"
    url = "https://sctapi.ftqq.com/%s.send" % key
    data = urllib.parse.urlencode({"title": title, "desp": desp}).encode()
    try:
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", "replace")
        try:
            j = json.loads(body)
        except Exception:
            j = {}
        if j.get("code") == 0:
            return True, ""
        msg = str(j.get("message") or body[:80] or "未知错误")
        return False, msg
    except Exception as e:
        return False, str(e)

def build_mail(events, ts):
    new = [e for e in events if e["act"] == "new"]
    worse = [e for e in events if e["act"] == "worse"]
    rec = [e for e in events if e["act"] == "recovered"]
    n = len(new) + len(worse)
    if n:
        subject = "[飞牛] 硬盘健康告警 · %d 块异常" % n
    else:
        subject = "[飞牛] 硬盘健康告警 · %d 块已恢复" % len(rec)
    lines = ["检测时间：%s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)), ""]

    def section(title, items):
        lines.append("【%s】" % title)
        for e in items:
            d = e["d"]
            lines.append("%s · %s · %s · %s" % (d.get("vol") or "-", d.get("model") or "?",
                                                d.get("serial") or disk_key(d),
                                                d.get("capacity_h") or "?"))
            lines.append("  故障：%s" % e["text"])
            lines.append("")

    if new:
        section("新增故障", new)
    if worse:
        section("故障恶化", worse)
    if rec:
        section("已恢复", rec)
    ip = lan_ip()
    if ip:
        lines.append("详情：http://%s:%d" % (ip, PORT))
    return subject, "\n".join(lines)

def eval_notify(disks, ts):
    """按状态机判断是否发信。返回快照记录用的 mail 摘要，或 None。"""
    cfg = read_notify_cfg()
    if not cfg.get("on") and not cfg.get("sct_on"):
        return None
    st = load_state()
    dstate = dict(st.get("disks") or {})
    newstate = {}
    for d in disks:
        if d.get("kind"):
            newstate[disk_key(d)] = {"kind": d["kind"], "sev": d.get("sev") or 0,
                                     "reason": d.get("reason")}
    if not st.get("__inited__"):
        save_state({"__inited__": 1, "disks": newstate})
        return None
    events = []
    for d in disks:
        key = disk_key(d)
        kind = d.get("kind")
        old = dstate.get(key)
        if kind:
            if old is None or old.get("kind") != kind:
                events.append({"act": "new", "key": key, "d": d,
                               "text": d.get("reason") or FAULT_LABEL.get(kind, kind)})
            elif (d.get("sev") or 0) > (old.get("sev") or 0):
                events.append({"act": "worse", "key": key, "d": d,
                               "text": "%s（上次 %s）" % (d.get("reason"), old.get("reason") or "-")})
        elif old and old.get("kind"):
            events.append({"act": "recovered", "key": key, "d": d,
                           "text": "故障消失，当前状态：%s" % (d.get("reason") or "")})
    if not events:
        save_state({"__inited__": 1, "disks": newstate})
        return None
    keys = [e["key"] for e in events]
    subject, body = build_mail(events, ts)
    mail_ok = mail_err = None
    sct_ok = sct_err = None
    if cfg.get("on"):
        mail_ok, mail_err = send_mail(cfg, subject, body)
        if not mail_ok:
            mail_err = short_err(mail_err)
    if cfg.get("sct_on"):
        sct_ok, sct_err = send_sct(cfg, subject, body)
        if not sct_ok:
            sct_err = short_err(sct_err)
    if cfg.get("on") and cfg.get("sct_on") and mail_ok and sct_ok:
        save_state({"__inited__": 1, "disks": newstate})
        return {"ok": True, "keys": keys, "subject": subject,
                "mail_ok": True, "sct_ok": True}
    if (not cfg.get("on") or mail_ok) and (not cfg.get("sct_on") or sct_ok):
        save_state({"__inited__": 1, "disks": newstate})
        out = {"ok": True, "keys": keys, "subject": subject,
               "mail_ok": mail_ok, "sct_ok": sct_ok}
        return out
    return {"ok": False, "keys": keys, "subject": subject,
            "mail_ok": mail_ok, "sct_ok": sct_ok,
            "err": mail_err or "", "detail": mail_err or "",
            "sct_err": sct_err or "", "sct_detail": sct_err or ""}

DELTA_KEYS = (("defects", "缺陷数"), ("uncorr", "不可纠正"),
              ("rr_total", "重读/重写"), ("reallocated", "重分配扇区"),
              ("pending", "待映射扇区"))

def compute_deltas(disks_rec, prev_full):
    prev = {}
    if prev_full:
        for d in (prev_full.get("disks") or []):
            prev[disk_key(d)] = d
    out = {}
    for d in disks_rec:
        key = disk_key(d)
        p = prev.get(key)
        chg = []
        if p is None:
            chg.append("新盘加入（无历史基线）")
        else:
            for k, label in DELTA_KEYS:
                a = p.get(k) or 0
                b = d.get(k) or 0
                if b > a:
                    chg.append("%s %d → %d（+%d）" % (label, a, b, b - a))
            if bool(p.get("smart_ok")) != bool(d.get("smart_ok")):
                chg.append("健康判定 %s → %s" % ("PASSED" if p.get("smart_ok") else "FAILED",
                                                "PASSED" if d.get("smart_ok") else "FAILED"))
        if chg:
            out[key] = chg
    return out

# ---------------- 采集 ----------------

def snapshots_differ(a, b):
    da = {d.get("serial"): d for d in (a.get("disks") or [])}
    db = {d.get("serial"): d for d in (b.get("disks") or [])}
    if set(da) != set(db):
        return True
    for k in da:
        for key in CHANGE_KEYS:
            if (da[k].get(key) or 0) != (db[k].get(key) or 0):
                return True
        if bool(da[k].get("smart_ok")) != bool(db[k].get("smart_ok")):
            return True
    return False

def cleanup_snaps():
    snaps = load_snaps()
    cutoff = time.time() - SNAP_KEEP_DAYS * 86400
    victims = [s for s in snaps if s.get("time", 0) < cutoff]
    full = sorted([s for s in snaps if "disks" in s],
                  key=lambda x: x.get("time", 0))
    if len(full) > SNAP_KEEP_MAX:
        victims += full[:-SNAP_KEEP_MAX]
    if full:
        keep = full[-1].get("_file")
        victims = [s for s in victims if s.get("_file") != keep]
    for s in victims:
        try:
            os.remove(os.path.join(SNAP_DIR, s["_file"]))
        except Exception:
            pass

_cache = {"ts": 0, "data": None}

def run_smartctl(args, timeout=25):
    try:
        p = subprocess.run([SMARTCTL] + args, capture_output=True, timeout=timeout)
        try:
            return json.loads(p.stdout.decode("utf-8", "replace"))
        except Exception:
            return {}
    except Exception:
        return {}

def human_size(n):
    if not n: return "?"
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if n < 1000: return "%.0f %s" % (n, unit) if unit == "B" else "%.1f %s" % (n, unit)
        n /= 1000.0
    return "%.1f EB" % n

def discover():
    js = run_smartctl(["--scan", "--json"])
    raw = [d.get("name") for d in (js.get("devices") or []) if d.get("name")]
    seen = set(); devs = []
    for n in raw:
        key = n if n.startswith("/dev/sd") else ("BUS:" + n)
        if key in seen:
            continue
        if not n.startswith("/dev/sd"):
            continue
        seen.add(key); devs.append(n)
    if not devs:
        devs = sorted(glob.glob("/dev/sd?"))
    return devs

def parse_disk(dev, smart_args=None):
    args = ["-a", "--json", "-n", "standby"] + (smart_args or []) + [dev]
    js = run_smartctl(args)
    d = {"dev": dev, "protocol": js.get("device", {}).get("protocol", "?")}
    dt = js.get("device", {}).get("type", "")
    if dt.startswith("megaraid"):
        d["raid_pd"] = dt
    info = js.get("model_family") or ""
    d["model"] = (js.get("model_name") or js.get("scsi_model_name")
                  or ((js.get("vendor", "") + " " + js.get("product", "")).strip())
                  or info or "?")
    d["serial"] = js.get("serial_number") or "?"
    d["fw"] = js.get("firmware_version") or js.get("scsi_revision") or "?"
    cap = js.get("user_capacity", {}).get("bytes")
    d["capacity"] = cap
    d["capacity_h"] = human_size(cap)
    d["rpm"] = js.get("rotation_rate")
    d["ssd"] = bool(js.get("rotation_rate") == 0) or ("SSD" in d["model"].upper())
    st = js.get("smart_status", {})
    d["smart_ok"] = bool(st.get("passed"))
    d["temp"] = js.get("temperature", {}).get("current")
    if d["temp"] is None:
        for a in (js.get("ata_smart_attributes", {}).get("table") or []):
            rv = a.get("raw", {}).get("value", 0) or 0
            if a.get("id") in (194, 190) and rv > 0:
                d["temp"] = rv
                break
    pot = js.get("power_on_time", {})
    d["hours"] = pot.get("hours") if pot.get("hours") is not None else pot.get("minutes", 0) // 60
    d["cycles"] = js.get("power_cycle_count")
    d["standby"] = "standby" in str(js.get("device", {}).get("type", "")) or False
    d["defects"] = 0; d["uncorr"] = 0; d["corrected"] = 0
    d["sata_attrs"] = None; d["reallocated"] = 0; d["pending"] = 0
    if d["protocol"] == "ATA" or js.get("ata_smart_attributes"):
        attrs = js.get("ata_smart_attributes", {}).get("table") or []
        d["sata_attrs"] = [[a.get("id"), a.get("name"), a.get("value"),
                            a.get("worst"), str(a.get("raw", {}).get("value", ""))]
                           for a in attrs]
        for a in attrs:
            aid = a.get("id")
            raw = a.get("raw", {}).get("value", 0) or 0
            if aid == 5: d["reallocated"] = raw
            if aid in (197, 198): d["pending"] += raw
    else:
        d["defects"] = js.get("scsi_grown_defect_list", 0) or 0
        counters = js.get("scsi_error_counter_log") or {}
        ssc = js.get("scsi_start_stop_cycle_counter") or {}
        d["cycles"] = d["cycles"] or ssc.get("accumulated_start_stop_cycles")
        d["rated_cycles"] = ssc.get("specified_cycle_count_over_device_lifetime")
        y = ssc.get("year_of_manufacture"); w = ssc.get("week_of_manufacture")
        d["mfg"] = ("%s 年第 %s 周" % (y, w)) if (y and w) else None
        d["form_factor"] = js.get("form_factor")
        d["rr_total"] = 0
        se = {}
        for side in ("read", "write", "verify"):
            cc = counters.get(side, {}) or {}
            corr = (cc.get("errors_corrected_by_eccfast", 0) or 0) + (cc.get("errors_corrected_by_eccdelayed", 0) or 0)
            rr = cc.get("errors_corrected_by_rereads_rewrites", 0) or 0
            unc = cc.get("total_uncorrected_errors", 0) or 0
            se[side] = {"corr": corr, "rr": rr, "unc": unc,
                        "gb": cc.get("gigabytes_processed", 0) or 0}
            d["rr_total"] += rr
        d["uncorr"] = se["read"]["unc"] + se["write"]["unc"] + se["verify"]["unc"]
        d["corrected"] = se["read"]["corr"] + se["write"]["corr"] + se["verify"]["corr"]
        d["scsi_err"] = se
    return d

def load_snaps():
    items = []
    if os.path.isdir(SNAP_DIR):
        for f in sorted(os.listdir(SNAP_DIR)):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(SNAP_DIR, f), encoding="utf-8") as fh:
                        it = json.load(fh)
                    it["_file"] = f
                    items.append(it)
                except Exception:
                    pass
    return items

def latest_snap_before(snaps, ts):
    best = None
    for s in snaps:
        if "disks" not in s:
            continue
        if s.get("time", 0) <= ts and (best is None or s.get("time", 0) > best.get("time", 0)):
            best = s
    return best

def latest_full_snap():
    fulls = [s for s in load_snaps() if "disks" in s]
    return fulls[-1] if fulls else None

def save_snapshot(disks, auto=False, notify=False):
    disks_rec = [{"dev": d["dev"], "serial": d["serial"], "model": d["model"], "vol": d.get("vol"),
                  "defects": d["defects"], "uncorr": d["uncorr"], "rr_total": d.get("rr_total", 0),
                  "reallocated": d["reallocated"], "pending": d["pending"],
                  "smart_ok": d["smart_ok"], "temp": d["temp"]} for d in disks]
    ts = int(time.time())
    suffix = "-auto" if auto else ""
    prev_full = latest_full_snap()
    if auto and prev_full is not None and not snapshots_differ({"disks": disks_rec}, prev_full):
        rec = {"time": ts, "auto": True, "nochange": True}
        name = time.strftime("%Y%m%d-%H%M%S", time.localtime(ts)) + suffix + ".json"
        with open(os.path.join(SNAP_DIR, name), "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False)
        cleanup_snaps()
        return rec
    rec = {"time": ts, "auto": auto, "disks": disks_rec,
           "deltas": compute_deltas(disks_rec, prev_full)}
    if notify:
        m = eval_notify(disks, ts)
        if m:
            rec["mail"] = m
    name = time.strftime("%Y%m%d-%H%M%S", time.localtime(ts)) + suffix + ".json"
    with open(os.path.join(SNAP_DIR, name), "w", encoding="utf-8") as fh:
        json.dump(rec, fh, ensure_ascii=False)
    if auto:
        cleanup_snaps()
    return rec

def grade(d, prev):
    if not d["smart_ok"]:
        return "r", "SMART 判定失败", "smart_failed", 0
    if d["uncorr"] > 0:
        return "r", "存在 %d 个不可纠正错误" % d["uncorr"], "uncorr", d["uncorr"]
    pd = None
    if prev is not None:
        pd = {disk_key(x): x for x in prev.get("disks", [])}.get(disk_key(d))
    if d["protocol"] != "ATA":
        if pd is not None:
            delta = d["defects"] - (pd.get("defects") or 0)
            if delta > 0:
                return "r", "缺陷列表增长 +%d" % delta, "defects_growth", delta
        if d.get("rr_total", 0) > 0:
            return "y", "存在重读/重写 %d 次" % d["rr_total"], None, 0
        if d["defects"] > 0:
            return "y", "历史缺陷 %d" % d["defects"], None, 0
    else:
        if d["pending"] > 0:
            return "r", "待映射/不可映射扇区 %d" % d["pending"], "pending", d["pending"]
        if pd is not None:
            delta = d["reallocated"] - (pd.get("reallocated") or 0)
            if delta > 0:
                return "r", "重分配扇区增长 +%d" % delta, "realloc_growth", delta
        if d["reallocated"] > 0:
            return "y", "历史重分配扇区 %d" % d["reallocated"], None, 0
    return "g", "正常", None, 0

def vol_map():
    try:
        pr = subprocess.run(["lsblk", "-J", "-o", "NAME,TYPE,MOUNTPOINTS"],
                            capture_output=True, timeout=10)
        js = json.loads(pr.stdout.decode("utf-8", "replace"))
    except Exception:
        return {}
    m = {}
    def walk(node, top):
        for mp in (node.get("mountpoints") or []):
            if mp and mp.startswith("/vol"):
                m.setdefault(top, mp)
        for ch in (node.get("children") or []):
            walk(ch, top)
    for dn in (js.get("blockdevices") or []):
        walk(dn, dn.get("name"))
    return m

def vol_label(mp):
    if not mp:
        return "未挂载"
    num = mp.replace("/vol", "", 1)
    return "存储空间 " + num if num.isdigit() else mp

VD_MODEL_RE = re.compile(
        r"(AVAGO|LSI|MegRAID|MEGARAID|PERC|ServeRAID|iBBU|Supermicro)",
        re.I)

def looks_like_vd(dd):
    """RAID virtual drive passes through as /dev/sdX with controller identity."""
    if VD_MODEL_RE.search(dd.get("model") or ""):
        return True
    if dd.get("protocol") == "ATA" or dd.get("sata_attrs"):
        return False
    return (dd.get("rpm") is None and dd.get("temp") is None
            and dd.get("smart_ok") is False)


def looks_like_vd_re(dd):
    """Model-name-only check, used for PD handles (they are real disks by construction)."""
    return bool(VD_MODEL_RE.search(dd.get("model") or ""))


def storcli_slots():
    """Optional: PD -> enclosure:slot via storcli. Keyed by SN and DID:wrapped."""
    arg_sets = (["/call/eall/sall", "show", "J"], ["/call", "show", "J"])
    for cli in ("/opt/MegaRAID/storcli/storcli64", "/usr/local/bin/storcli64",
                "/usr/bin/storcli64", "/usr/sbin/storcli64", "/usr/sbin/storcli",
                "/opt/MegaRAID/storcli/storcli", "storcli64", "storcli"):
        for args in arg_sets:
            try:
                p = subprocess.run([cli] + args, capture_output=True, text=True, timeout=30)
            except Exception:
                continue
            out = p.stdout or ""
            i = out.find("{")
            if i < 0:
                continue
            try:
                j = json.loads(out[i:])
            except Exception:
                continue
            hits = []

            def walk(node):
                if isinstance(node, dict):
                    if node.get("EID:Slt"):
                        hits.append(node)
                    for v in node.values():
                        walk(v)
                elif isinstance(node, list):
                    for v in node:
                        walk(v)

            walk(j)
            m = {}
            for h in hits:
                slot = str(h.get("EID:Slt"))
                sn = str(h.get("SN") or "").strip()
                did = h.get("DID")
                if sn:
                    m[sn] = slot
                if did is not None:
                    m["DID:%s" % did] = slot
            if m:
                return m
    return None

def has_megaraid():
    """megaraid_sas may be a module or built-in; check both."""
    try:
        if os.path.exists("/sys/module/megaraid_sas"):
            return True
        for p in glob.glob("/sys/class/scsi_host/host*/proc_name"):
            try:
                with open(p) as fh:
                    if "megaraid" in fh.read().lower():
                        return True
            except Exception:
                pass
    except Exception:
        pass
    return False


def discover_mr():
    """Read megaraid PD targets straight from smartctl --scan (numbering + node authoritative)."""
    js = run_smartctl(["--scan", "--json"])
    out = []
    for d in (js.get("devices") or []):
        t = str(d.get("type") or "")
        m = re.match(r"^(?:(sat)\+)?megaraid(?:\+sat)?,(\d+)$", t, re.I)
        if m:
            out.append({"node": str(d.get("name") or ""), "type": t, "n": int(m.group(2))})
    return out


def mr_probe_nodes(preferred=None):
    """Candidate device nodes used to talk to the RAID controller (ioctl vehicle)."""
    nodes = []
    if preferred:
        nodes.append(preferred)
    if os.path.exists("/dev/bus/0"):
        nodes.append("/dev/bus/0")
    nodes += sorted(glob.glob("/dev/sd?"))
    if not nodes:
        nodes = ["/dev/sda"]
    seen = set()
    out = []
    for n in nodes:
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def raid_pds():
    """Fallback blind probe of megaraid PD indices (only when --scan lists no PDs)."""
    node = mr_probe_nodes()[0]
    for prefix in ("megaraid", "sat+megaraid"):
        pds = []
        sigs = set()
        for n in range(0, 32):
            js = run_smartctl(["-H", "--json", "-d", "%s,%d" % (prefix, n), node])
            if not js or "device" not in js:
                continue
            key = (js.get("model_name") or js.get("scsi_model_name") or "",
                   js.get("serial_number") or "", js.get("user_capacity", {}).get("bytes"))
            if key in sigs or key == ("", "", None):
                continue
            sigs.add(key)
            pds.append((n, "%s,%d" % (prefix, n)))
        if pds:
            return pds
    return []

def collect(force=False):
    now = time.time()
    if not force and _cache["data"] and now - _cache["ts"] < CACHE_TTL:
        d = dict(_cache["data"]); d["cached"] = True
        d["autosnap"] = autosnap_on()
        d["interval_h"] = read_interval_h()
        return d
    snaps = load_snaps()
    vm = vol_map()
    disks = []
    vds = []
    found = discover()
    has_mr = has_megaraid()
    for dev in found:
        dd = parse_disk(dev)
        if looks_like_vd(dd):
            vds.append({"dev": dev, "model": dd.get("model"),
                        "capacity_h": dd.get("capacity_h")})
            continue
        dd["grade"], dd["reason"], dd["kind"], dd["sev"] = grade(dd, latest_snap_before(snaps, now))
        dd["vol"] = vol_label(vm.get(dev.replace("/dev/", "")))
        disks.append(dd)
    if (not found or vds) and has_mr:
        slots = storcli_slots()
        targets = discover_mr()
        if not targets:
            targets = [{"node": "", "type": t, "n": n} for (n, t) in raid_pds()]
        node_pool = mr_probe_nodes(targets[0].get("node") if targets else None)[:3]
        for t in targets:
            n = t["n"]
            cands = []
            for nd in ([t.get("node")] + node_pool):
                if nd and nd not in cands:
                    cands.append(nd)
            dd = None
            used = None
            for nd in cands:
                cand = parse_disk(nd, ["-d", t["type"]])
                if cand.get("model") not in (None, "", "?"):
                    dd = cand
                    used = nd
                    break
            if dd is None or looks_like_vd_re(dd):
                continue
            sig = dd.get("serial") or ""
            if sig and any(x.get("serial") == sig for x in disks):
                continue
            dd["dev"] = "PD:%d" % n
            dd["raid_pd"] = t["type"]
            dd["probe_node"] = used
            if slots:
                sl = slots.get(sig) or slots.get("DID:%d" % n)
                if sl:
                    dd["slot"] = sl
            dd["grade"], dd["reason"], dd["kind"], dd["sev"] = grade(dd, latest_snap_before(snaps, now))
            dd["vol"] = "-"
            disks.append(dd)
    def _vkey(d):
        v = d.get("vol") or ""
        num = "".join(ch for ch in v if ch.isdigit())
        return (1 if not num else 0, int(num) if num else 0, d["dev"])
    disks.sort(key=_vkey)
    last_snap = snaps[-1] if snaps else None
    fulls = [s for s in snaps if "disks" in s]
    last_full = fulls[-1] if fulls else None
    auto_due = (last_snap is None or now - last_snap.get("time", 0) > read_interval_h() * 3600)
    if auto_due and autosnap_on():
        save_snapshot(disks, auto=True, notify=True)
        last_snap = load_snaps()[-1]
    data = {"time": int(now), "cached": False, "update": update_info(False), "disks": disks,
            "snapshot_last": last_full.get("time") if last_full else None,
            "last_check": last_snap.get("time") if last_snap else None,
            "autosnap": autosnap_on(), "interval_h": read_interval_h(),
            "vds": vds}
    _cache["ts"] = now; _cache["data"] = data
    return dict(data)

PAGE = r"""<!DOCTYPE html><html lang=zh><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>SAS 硬盘健康</title>
<style>
*{box-sizing:border-box} body{font-family:system-ui,"Microsoft YaHei",sans-serif;margin:0;background:#eef1f5;color:#2b3440}
.hd{background:#1e3a5f;color:#fff;padding:14px 22px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.hd h1{font-size:19px;margin:0;font-weight:600}
.hd .sp{flex:1}
.btn{background:#2d6cdf;color:#fff;border:none;border-radius:6px;padding:7px 14px;font-size:13px;cursor:pointer}
.btn.gh{background:#fff;color:#2d6cdf;border:1px solid #2d6cdf}
.btn:disabled{opacity:.6;cursor:default}
.sum{display:flex;gap:10px;padding:12px 22px;flex-wrap:wrap}
.badge{background:#fff;border-radius:8px;padding:8px 14px;font-size:13px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.badge b{font-size:17px}
.list{padding:6px 22px 24px}.lhd{display:grid;grid-template-columns:26px 96px 200px 150px 92px 96px 64px 120px 88px 1fr;gap:8px;padding:6px 12px;font-size:12px;color:#7a8593}.row{display:grid;grid-template-columns:26px 96px 200px 150px 92px 96px 64px 120px 88px 1fr;gap:8px;align-items:center;background:#fff;border-radius:8px;padding:10px 12px;margin-bottom:8px;cursor:pointer;box-shadow:0 1px 3px rgba(0,0,0,.06);border-left:4px solid #cfd6de;font-size:12.5px}.row.g{border-left-color:#22a559}.row.y{border-left-color:#e6a817}.row.r{border-left-color:#d9433b}.row:hover{box-shadow:0 2px 8px rgba(0,0,0,.12)}.led{width:11px;height:11px;border-radius:50%;display:inline-block}.led.g{background:#22a559}.led.y{background:#e6a817}.led.r{background:#d9433b}.c1{font-weight:600}.c8{color:#5b6673;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}@media (max-width:900px){.lhd{display:none}.row{grid-template-columns:26px 1fr 90px;grid-auto-flow:row;grid-template-rows:auto auto}}
.card{background:#fff;border-radius:10px;padding:13px 15px;cursor:pointer;box-shadow:0 1px 4px rgba(0,0,0,.07);border-left:5px solid #ccc}
.card.g{border-left-color:#22a559}.card.y{border-left-color:#e6a817}.card.r{border-left-color:#d9433b}
.card .t{font-size:14px;font-weight:600;margin-bottom:2px}
.card .m{font-size:12px;color:#7a8593;line-height:1.65}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:5px}
.dot.g{background:#22a559}.dot.y{background:#e6a817}.dot.r{background:#d9433b}
.tag{display:inline-block;font-size:11px;background:#eef3fa;color:#2d6cdf;border-radius:4px;padding:1px 6px;margin-left:6px}
.modal{display:none;position:fixed;inset:0;background:rgba(20,30,45,.45);z-index:9;align-items:center;justify-content:center}
.modal .box{background:#fff;border-radius:12px;max-width:720px;width:92%;max-height:86vh;overflow:auto;padding:20px 24px}
.modal h2{margin:0 0 4px;font-size:17px}.modal .sub{color:#7a8593;font-size:12.5px;margin-bottom:12px}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:8px 0}
th,td{border:1px solid #e3e8ee;padding:5px 8px;text-align:left}
th{background:#f5f8fb}
.kv{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px 14px;font-size:13px;margin:10px 0}
.kv div{background:#f7f9fb;border-radius:6px;padding:6px 10px}
.kv span{color:#7a8593;font-size:11.5px;display:block}
.close{float:right;cursor:pointer;color:#98a2ae;font-size:20px;line-height:1}
.note{font-size:12px;color:#98a2ae;padding:0 22px 6px}
.hsec{margin:4px 22px 26px;background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.hhd{font-weight:600;font-size:14px;margin-bottom:8px}
.hsub{font-weight:400;color:#98a2ae;font-size:12px;margin-left:8px}
.hsec table{margin-top:2px}
.hsec .tm{color:#98a2ae;white-space:nowrap;font-size:12px}
.sn{font-family:Consolas,'Courier New',monospace;color:#8a94a0;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dd{position:relative;display:inline-block}
.ddmenu{display:none;position:absolute;top:110%;left:0;background:#fff;border:1px solid #e3e8ee;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,.12);padding:6px;min-width:132px;z-index:50}
.ddmenu.open{display:block}
.ddmenu button{display:block;width:100%;text-align:left;border:none;background:none;padding:7px 10px;border-radius:6px;font-size:13px;cursor:pointer;color:#333}
.ddmenu button:hover{background:#f0f4f8}
.ddmenu button.cur{color:#2563eb;font-weight:600}
.morewrap{display:flex;justify-content:center;margin:10px 0 2px}
.updbar{margin:12px 22px 0;background:#eef3fa;color:#2d6cdf;border-radius:8px;padding:9px 14px;font-size:13px}
.updbar a{color:#2d6cdf;font-weight:600;text-decoration:none}
.updbar a:hover{text-decoration:underline}
.merr{color:#d9433b}
.nfwarn{background:#fff7e0;color:#8a6d1a;border-radius:8px;padding:8px 12px;font-size:12.5px;margin:8px 0}
.nfrow{display:flex;align-items:center;gap:10px;margin:7px 0}
.nfrow>label{width:118px;flex:none;color:#5b6673;font-size:13px}
.nfinput{flex:1;min-width:0;border:1px solid #d7dee6;border-radius:6px;padding:6px 9px;font-size:13px}
.nfsel{border:1px solid #d7dee6;border-radius:6px;padding:6px 9px;font-size:13px;background:#fff}
.nfcheck{display:flex;align-items:center;gap:8px;font-size:13.5px;font-weight:600;margin:10px 0 4px;cursor:pointer}
.nfhint{font-size:12px;color:#98a2ae;margin:10px 0 4px;line-height:1.7}
.nfmsg{font-size:13px;margin:8px 0;min-height:18px}
.nfmsg.ok{color:#22a559}.nfmsg.bad{color:#d9433b}
.nfbtn{display:flex;gap:10px;justify-content:flex-end;margin-top:8px}
.nfsep{height:1px;background:#e3e8ee;margin:14px 0 4px}
@media (max-width:600px){.kv{grid-template-columns:1fr 1fr}.lhd,.row{grid-template-columns:26px 70px 132px 72px 60px 60px 88px 70px 1fr}.lhd span:nth-child(4),.row .sn{display:none}}
</style></head><body>
<div class=hd><h1>&#128190; SAS 硬盘健康</h1><span class=sp></span>
<button class="btn gh" id=btnsnap onclick=snap()>拍快照</button>
<div class=dd><button class="btn gh" id=btnauto onclick="ddToggle(event)">自动快照: 6小时 &#9662;</button><div class=ddmenu id=ddmenu></div></div>
<button class="btn gh" onclick=notifyOpen()>通知</button>
<button class="btn gh" onclick=histJump()>历史↓</button>
<button class=btn onclick=load(1)>刷新</button></div>
<div class=updbar id=updbar style="display:none"></div>
<div class=sum id=sum></div>
<div class=list id=wrap><div class=lhd><span></span><span>存储空间</span><span>型号</span><span>序列号</span><span>容量</span><span>类型</span><span>温度</span><span>生产日期</span><span>通电</span><span>状态</span></div><div id=grid></div></div>
<div class=note id=note></div><div id=raidhint style="display:none;margin:0 22px 6px;font-size:12px;color:#8a6d1a;background:#fff7e0;border-radius:8px;padding:8px 14px"></div>
<div class=hsec id=histsec><div class=hhd>&#128197; 快照历史<span class=hsub>后台自动检查 · 无变化记为无异常，有变化逐盘列出 · 完整快照保留180天/最多500份 · 邮件发送结果标在明细里</span></div><div id=histbody></div></div>
<div class=modal id=mk onclick="if(event.target==this)this.style.display='none'"><div class=box id=mkbox></div></div>
<div class=modal id=mh onclick="if(event.target==this)this.style.display='none'"><div class=box id=mhbox></div></div>
<div class=modal id=nf onclick="if(event.target==this)this.style.display='none'"><div class=box id=nfbox></div></div>
<script>
let DATA=null;
let HISTALL=false,HISTTOTAL=0;
let NFC=null,NFP=[];
function fmtT(ts){return ts?new Date(ts*1000).toLocaleString('zh-CN',{hour12:false}):'-'}
async function load(force){
  const r=await fetch('/api/disks'+(force?'?force=1':''));DATA=await r.json();render()}
function fmtIv(h){if(h>=48)return (h/24)+'天';return h+'小时'}
function fmtH(h){if(h==null)return '-';if(h<24)return h+'h';return Math.floor(h/24)+'天'}
function ddToggle(e){
  e.stopPropagation();
  const m=document.getElementById('ddmenu');if(!m)return;
  if(m.classList.contains('open')){m.classList.remove('open');return}
  const cur=(DATA&&DATA.autosnap)?(DATA.interval_h||6):0;
  let h='<button onclick="setSnapCfg(0)">关闭'+(cur===0?' ✓':'')+'</button>';
  [6,12,24,72,168].forEach(function(o){
    h+='<button class="'+(o===cur?'cur':'')+'" onclick="setSnapCfg('+o+')">'+fmtIv(o)+(o===cur?' ✓':'')+'</button>';
  });
  m.innerHTML=h;m.classList.add('open');
}
document.addEventListener('click',function(){const m=document.getElementById('ddmenu');if(m)m.classList.remove('open')});
async function setSnapCfg(v){
  try{
    if(v===0){
      const r=await fetch('/api/autosnap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({on:false})});
      const j=await r.json();if(DATA)DATA.autosnap=j.autosnap;
    }else{
      if(!(DATA&&DATA.autosnap)){
        await fetch('/api/autosnap',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({on:true})});
      }
      const r=await fetch('/api/interval',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({hours:v})});
      const j=await r.json();
      if(j.ok&&DATA){DATA.interval_h=j.interval_h;DATA.autosnap=true}
    }
  }catch(e){}
  const ba=document.getElementById('btnauto');
  if(ba)ba.textContent='自动快照: '+((DATA&&DATA.autosnap)?fmtIv((DATA&&DATA.interval_h)||6):'关');
  const m=document.getElementById('ddmenu');if(m)m.classList.remove('open');
}
function render(){
  const ds=DATA.disks;let ng=0,ny=0,nr=0,tmax=null;
  for(const d of ds){if(d.grade==='g')ng++;else if(d.grade==='y')ny++;else if(d.grade==='r')nr++;
    if(d.temp!=null&&(tmax==null||d.temp>tmax))tmax=d.temp}
  const cnt={g:ng,y:ny,r:nr};
  document.getElementById('sum').innerHTML=
   '<div class=badge>磁盘 <b>'+ds.length+'</b></div>'+
   '<div class=badge><span class="dot g"></span>正常 <b>'+cnt.g+'</b></div>'+
   '<div class=badge><span class="dot y"></span>注意 <b>'+cnt.y+'</b></div>'+
   '<div class=badge><span class="dot r"></span>异常 <b>'+cnt.r+'</b></div>'+
   '<div class=badge>最高温度 <b>'+(tmax==null?'-':tmax+'℃')+'</b></div>'+
   '<div class=badge>上次检查 <b>'+fmtT(DATA.last_check||DATA.snapshot_last)+'</b></div>';
  document.getElementById('grid').innerHTML=ds.map((d,i)=>
   '<div class="row '+d.grade+'" onclick=detail('+i+')>'+
   '<span class="led '+d.grade+'"></span>'+
   '<span class=c1>'+((d.vol&&d.vol!=='-')?d.vol:(d.raid_pd?(d.dev||'-'):'-'))+'</span>'+
   '<span>'+d.model.replace(/</g,'&lt;')+'</span>'+
   '<span class=sn title="'+(d.serial||'')+'">'+((d.serial||'-').replace(/</g,'&lt;'))+'</span>'+
   '<span>'+d.capacity_h+'</span>'+
   '<span>'+(d.protocol=='ATA'?'SATA'+(d.ssd?'·SSD':''):'SAS')+(d.raid_pd?'·RAID':'')+(d.slot?'·'+d.slot:'')+'</span>'+
   '<span>'+(d.temp==null?'-':d.temp+'℃')+'</span>'+
   '<span>'+(d.mfg||'-')+'</span>'+
   '<span title="'+(d.hours==null?'':d.hours+' 小时')+'">'+fmtH(d.hours)+'</span>'+
   '<span class=c8>'+d.reason+'</span></div>').join('');
  document.getElementById('note').textContent='数据时间 '+fmtT(DATA.time)+(DATA.cached?'（缓存，点刷新强制重查）':'')+' · 点卡片查看详情';
  const npd=(DATA.disks||[]).filter(function(x){return x.raid_pd}).length;
  const nvd=((DATA.vds)||[]).length;
  const rh=document.getElementById('raidhint');
  if(rh){
    let msg='';
    if(nvd>0){const vs=(DATA.vds||[]).map(function(v){return v.dev+'（'+(v.model||'?')+' '+(v.capacity_h||'')+'）'}).join('、');
      msg+='检测到 RAID 虚拟盘 '+vs+'，其健康由物理盘决定，已从列表排除。'}
    if(npd>0){msg+=(msg?' ':'')+'检测到 '+npd+' 块 RAID 卡物理盘（PD 编号'+((DATA.disks||[]).some(function(x){return x.slot})?'与物理槽位':'')+'显示在类型列）。'}
    if(msg){rh.style.display='block';rh.textContent=msg}else{rh.style.display='none'}
  }
  const ba=document.getElementById('btnauto');
  if(ba)ba.textContent='自动快照: '+((DATA.autosnap)?fmtIv(DATA.interval_h||6):'关');
  const ub=document.getElementById('updbar');
  if(ub){
    const u=DATA.update||null;
    if(u&&u.newer){
      ub.style.display='block';
      ub.innerHTML='发现新版本 v'+u.latest+'（当前 v'+u.current+'） · <a href="'+(u.url||'#')+'" target="_blank" rel="noopener">查看更新说明 →</a>';
    }else{ub.style.display='none'}
  }
  histTable();
}
function detail(i){
  const d=DATA.disks[i];
  let h='<span class=close onclick=mkClose()>×</span><h2>'+d.dev+' '+d.model.replace(/</g,'&lt;')+'</h2>';
  h+='<div class=sub>'+d.capacity_h+' · '+(d.ssd?'SSD':(d.rpm?d.rpm+' rpm':'?'))+' · '+d.protocol+'</div>';
  h+='<div class=kv><div><span>健康判定</span><span style=color:'+(d.smart_ok?'#22a559':'#d9433b')+';font-weight=600>'+(d.smart_ok?'PASSED':'FAILED')+'</span></div>'+
     '<div><span>温度</span>'+(d.temp==null?'-':d.temp+'℃')+'</div>'+
     '<div><span>状态</span>'+d.reason+'</div>'+
     '<div><span>序列号</span>'+d.serial+'</div><div><span>固件</span>'+d.fw+'</div>'+
     '<div><span>通电时长</span>'+(d.hours==null?'-':Math.floor(d.hours/24)+' 天（'+d.hours+' 小时 · 约 '+(d.hours/8760).toFixed(1)+' 年）')+'</div>'+
     '<div><span>启动次数</span>'+(d.cycles==null?'-':d.cycles+(d.rated_cycles?' / 额定'+d.rated_cycles:''))+'</div>';
  if(d.protocol=='ATA'){
    h+='<div><span>重分配扇区</span>'+d.reallocated+'</div><div><span>当前待映射</span>'+d.pending+'</div><div><span>待机</span>'+(d.standby?'是':'否')+'</div></div>';
    if(d.sata_attrs){h+='<table><tr><th>ID</th><th>属性</th><th>当前</th><th>最差</th><th>原始值</th></tr>'+
      d.sata_attrs.map(a=>'<tr><td>'+a[0]+'</td><td>'+a[1]+'</td><td>'+a[2]+'</td><td>'+a[3]+'</td><td>'+a[4]+'</td></tr>').join('')+'</table>'}
  }else{
    h+='<div><span>生产日期</span>'+(d.mfg||'-')+'</div>'+
       '<div><span>增长缺陷数</span>'+d.defects+'</div><div><span>不可纠正错误</span>'+d.uncorr+'</div>'+
       '<div><span>重读/重写</span>'+(d.rr_total||0)+'</div></div>';
    if(d.scsi_err){h+='<div class=sub>错误计数明细（ECC纠错属正常机制，重读/重写与不可纠正才需关注）</div>'+
      '<table><tr><th>方向</th><th>ECC纠正</th><th>重读/重写</th><th>不可纠正</th><th>处理量GB</th></tr>'+
      ['read','write','verify'].map(function(k){return '<tr><td>'+({read:'读',write:'写',verify:'校验'})[k]+
      '</td><td>'+d.scsi_err[k].corr+'</td><td>'+d.scsi_err[k].rr+'</td><td>'+d.scsi_err[k].unc+'</td><td>'+d.scsi_err[k].gb+'</td></tr>'}).join('')+'</table>'}
  }
  document.getElementById('mkbox').innerHTML=h;
  document.getElementById('mk').style.display='flex';
}
function mkClose(){document.getElementById('mk').style.display='none';document.getElementById('mh').style.display='none'}
async function snap(){
  const b=document.getElementById('btnsnap');
  if(b){b.disabled=true;b.textContent='拍快照中…'}
  try{
    const r=await fetch('/api/snapshot',{method:'POST'});
    const j=await r.json();
    if(j.data&&j.data.disks){DATA=j.data;render()}
    else{await load(1)}
  }catch(e){}
  if(b){b.disabled=false;b.textContent='拍快照'}
}
function dlabel(serial,dev){
  let cur=null;
  const ds=(DATA?DATA.disks:[])||[];
  for(const x of ds){if(x.serial===serial){cur=x;break}}
  if(!cur)cur={};
  const mm=((cur.model||'')+'').trim().split(/\s+/).pop()||'';
  const sr=((cur.serial||'')+'');return (cur.vol||'?')+' · '+(dev||cur.dev||'?')+' · '+mm+(sr?' · '+sr:'');
}
function histKey(d){return (d.serial&&d.serial!=='?')?d.serial:(d.dev||'?')}
async function histTable(){
  let items=[],total=0;
  try{
    const r=await fetch('/api/snapshots'+(HISTALL?'?all=1':'?limit=10'));
    const j=await r.json();items=j.items||[];total=j.total||0;
  }catch(e){}
  HISTTOTAL=total;
  let html='<table><tr><th>时间</th><th>类型</th><th>硬盘</th><th>变化明细</th></tr>';
  items.forEach(function(s){
    if(s.nochange){
      html+='<tr><td class=tm>'+fmtT(s.time)+'</td><td>自动</td><td colspan=2>'+
        '<span style=color:#22a559>✔ 无异常（各盘关键计数与上次相同）</span></td></tr>';
      return;
    }
    if(!("disks" in s))return;
    const deltas=s.deltas||{},mail=s.mail||null;let group='';
    (s.disks||[]).forEach(function(d){
      if((d.dev||'').indexOf('/dev/sd')!==0&&(d.dev||'').indexOf('PD:')!==0)return;
      const key=histKey(d);
      const chg=(deltas[key]||[]).slice();
      if(d.smart_ok===false&&chg.join('|').indexOf('健康判定')<0)chg.push('健康判定 FAILED');
      if(mail&&(mail.keys||[]).indexOf(key)>=0){
        if(mail.mail_ok===true)chg.push('<span style=color:#22a559>邮件已发</span>');
        else if(mail.mail_ok===false)chg.push('<span class=merr title="'+String(mail.detail||'').replace(/"/g,'&quot;')+'">邮件发送失败：'+(mail.err||'')+'</span>');
        if(mail.sct_ok===true)chg.push('<span style=color:#22a559>微信已发</span>');
        else if(mail.sct_ok===false)chg.push('<span class=merr title="'+String((mail.sct_detail||mail.sct_err)||'').replace(/"/g,'&quot;')+'">微信推送失败：'+(mail.sct_err||'')+'</span>');
      }
      if(!chg.length)return;
      group+='<tr><td class=tm>'+fmtT(s.time)+'</td><td>'+(s.auto?'自动':'手动')
        +'</td><td>'+dlabel(d.serial,d.dev).replace(/</g,'&lt;')+'</td><td>'+chg.join('；')+'</td></tr>';
    });
    if(group)html+=group;
    else html+='<tr><td class=tm>'+fmtT(s.time)+'</td><td>'+(s.auto?'自动':'手动')
      +'</td><td colspan=2 style=color:#22a559>无变化</td></tr>';
  });
  html+='</table>';
  if(HISTTOTAL>10){
    html+='<div class=morewrap><button class="btn gh" onclick="histMore()">'
      +(HISTALL?'收起':'更多快照（共 '+HISTTOTAL+' 条）')+'</button></div>';
  }
  document.getElementById('histbody').innerHTML=html;
}
function histMore(){HISTALL=!HISTALL;histTable()}
function histJump(){histTable();const e=document.getElementById('histsec');if(e)e.scrollIntoView({behavior:'smooth'})}
function nfClose(){document.getElementById('nf').style.display='none'}
function nfEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;')}
function nfProv(){
  const el=document.getElementById('nfprov');if(!el)return;
  const v=el.value;let p=null;
  for(const x of NFP){if(x[0]===v){p=x;break}}
  if(!p||v==='custom')return;
  document.getElementById('nfhost').value=p[2];
  document.getElementById('nfport').value=p[3];
  document.getElementById('nfsec').value=p[4];
}
function nfForm(){
  const on=!!NFC.on,as=(NFC.autosnap!==false);
  let h='<span class=close onclick=nfClose()>×</span><h2>邮件通知设置</h2>';
  h+='<div class=sub>硬盘报红时发送提醒邮件 · 检测与自动快照同步</div>';
  if(!as){h+='<div class=nfwarn>自动快照已关闭，邮件通知不可用（两者共用同一个检测周期）。请先在上方「自动快照」里选择一个间隔。</div>';}
  if(as){h+='<label class=nfcheck><input type=checkbox id=nfon'+(on?' checked':'')+'> 启用邮件通知</label>';}
  h+='<div class=nfrow><label>邮箱类型</label><select class=nfsel id=nfprov onchange="nfProv()">';
  NFP.forEach(function(p){h+='<option value="'+p[0]+'"'+(NFC.provider===p[0]?' selected':'')+'>'+nfEsc(p[1])+'</option>'});
  h+='</select></div>';
  h+='<div class=nfrow><label>SMTP 服务器</label><input class=nfinput id=nfhost value="'+nfEsc(NFC.host)+'"></div>';
  h+='<div class=nfrow><label>端口 / 加密</label><input class=nfinput style="max-width:110px" id=nfport value="'+(NFC.port||465)+'"><select class=nfsel id=nfsec>';
  [['ssl','SSL'],['starttls','STARTTLS'],['none','不加密']].forEach(function(s){
    h+='<option value="'+s[0]+'"'+(NFC.secure===s[0]?' selected':'')+'>'+s[1]+'</option>'});
  h+='</select></div>';
  h+='<div class=nfrow><label>账号</label><input class=nfinput id=nfuser value="'+nfEsc(NFC.user)+'" placeholder="完整邮箱地址"></div>';
  h+='<div class=nfrow><label>授权码/应用密码</label><input class=nfinput id=nfpwd type=password placeholder="'+(NFC.has_password?'已设置，留空则不修改':'邮箱后台生成的授权码，不是登录密码')+'"></div>';
  h+='<div class=nfrow><label>发件人</label><input class=nfinput id=nfsender value="'+nfEsc(NFC.sender)+'" placeholder="默认与账号相同"></div>';
  h+='<div class=nfrow><label>收件人</label><input class=nfinput id=nfto value="'+nfEsc(NFC.to)+'" placeholder="接收提醒的邮箱"></div>';
  h+='<div class=nfsep></div>';
  h+='<label class=nfcheck><input type=checkbox id=nfscton'+(NFC.sct_on?' checked':'')+'> 微信推送（Server酱）</label>';
  h+='<div class=nfrow><label>SendKey</label><input class=nfinput id=nfsctkey type=password placeholder="'+(NFC.has_sct_key?'已设置，留空则不修改':'sct.ftqq.com 微信扫码登录后复制')+'"></div>';
  h+='<div class=nfhint>邮件：需在邮箱网页端开启 SMTP 并生成「授权码」，不能填登录密码。<br>微信：sct.ftqq.com 注册并关注「方糖」服务号后复制 SendKey，免费版每天限 5 条。<br>红色故障必发；同一故障只提醒一次，数值恶化会再次提醒，恢复正常会补发一条。两个通道可同时启用，互不影响。</div>';
  h+='<div class=nfmsg id=nfmsg></div>';
  h+='<div class=nfbtn><button class="btn gh" id=nfbtntestm onclick=notifyTest("mail")>测试邮件</button><button class="btn gh" id=nfbtntests onclick=notifyTest("sct")>测试微信</button><button class=btn id=nfbtnsave onclick=notifySave()>保存</button></div>';
  return h;
}
async function notifyOpen(){
  const box=document.getElementById('nfbox');
  box.innerHTML='<span class=close onclick=nfClose()>×</span><h2>邮件通知设置</h2><div class=sub>读取中…</div>';
  document.getElementById('nf').style.display='flex';
  try{
    const r=await fetch('/api/notify');const j=await r.json();
    NFC=j;NFP=j.providers||[];
    box.innerHTML=nfForm();
  }catch(e){
    box.innerHTML='<span class=close onclick=nfClose()>×</span><h2>邮件通知设置</h2><div class=sub>读取失败，请关闭后重试</div>';
  }
}
function nfSay(t,ok){const e=document.getElementById('nfmsg');if(e){e.textContent=t;e.className='nfmsg '+(ok?'ok':'bad')}}
function nfCollect(){
  function val(id){const e=document.getElementById(id);return e?e.value:''}
  const on=document.getElementById('nfon');
  const so=document.getElementById('nfscton');
  return {on:(on?!!on.checked:!!(NFC&&NFC.on)),provider:val('nfprov'),host:val('nfhost').trim(),
    port:parseInt(val('nfport')||'465',10),secure:val('nfsec'),user:val('nfuser').trim(),
    password:val('nfpwd'),sender:val('nfsender').trim(),to:val('nfto').trim(),
    sct_on:(so?!!so.checked:!!(NFC&&NFC.sct_on)),sct_key:val('nfsctkey')};
}
async function notifySave(){
  const bs=document.getElementById('nfbtnsave'),bt=document.getElementById('nfbtntest');
  if(bs){bs.disabled=true;bs.textContent='保存中…'}
  if(bt)bt.disabled=true;
  try{
    const r=await fetch('/api/notify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(nfCollect())});
    const j=await r.json();
    if(j.ok){
      NFC=Object.assign({},NFC||{},j.cfg||{});NFC.autosnap=(NFC.autosnap!==false);
      document.getElementById('nfbox').innerHTML=nfForm();
      nfSay('已保存',true);
    }else{nfSay(j.error||'保存失败',false)}
  }catch(e){nfSay('保存失败：网络错误',false)}
  const bs2=document.getElementById('nfbtnsave'),bt2=document.getElementById('nfbtntest');
  if(bs2){bs2.disabled=false;bs2.textContent='保存'}
  if(bt2)bt2.disabled=false;
}
async function notifyTest(ch){
  ch=ch||'mail';
  const bm=document.getElementById('nfbtntestm'),bsx=document.getElementById('nfbtntests'),bs=document.getElementById('nfbtnsave');
  if(bm){bm.disabled=true;bm.textContent='发送中…'}
  if(bsx){bsx.disabled=true;bsx.textContent='发送中…'}
  if(bs)bs.disabled=true;
  nfSay(ch==='sct'?'正在发送微信测试消息…':'正在连接邮件服务器，请稍候…',true);
  const body=nfCollect();body.channel=ch;
  const ctl=new AbortController();
  const tm=setTimeout(function(){ctl.abort()},45000);
  try{
    const r=await fetch('/api/notify/test',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:ctl.signal});
    const j=await r.json();
    if(j.ok)nfSay('已发送：'+(j.channel==='sct'?'微信（请在微信里查看）':'邮件（请查收，含垃圾箱）'),true);
    else nfSay('发送失败：'+(j.err||'未知错误'),false);
  }catch(e){nfSay((e&&e.name==='AbortError')?'发送超时（45 秒无响应）':'发送失败：网络错误',false)}
  clearTimeout(tm);
  const bm2=document.getElementById('nfbtntestm'),bsx2=document.getElementById('nfbtntests'),bs2=document.getElementById('nfbtnsave');
  if(bm2){bm2.disabled=false;bm2.textContent='测试邮件'}
  if(bsx2){bsx2.disabled=false;bsx2.textContent='测试微信'}
  if(bs2)bs2.disabled=false;
}
load(0);setInterval(()=>load(0),300000);
</script></body></html>""".replace("__PORT__", str(PORT))

class H(BaseHTTPRequestHandler):
    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def _json(self, obj, code=200):
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(obj, ensure_ascii=False).encode())
    def _body(self):
        ln = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(ln).decode("utf-8", "replace") if ln else "{}"
        try:
            j = json.loads(raw)
            return j if isinstance(j, dict) else {}
        except Exception:
            return {}
    def _merge_notify(self, body, cur):
        cfg = dict(cur)
        for k in ("provider", "host", "secure", "user", "sender", "to"):
            if k in body:
                cfg[k] = str(body.get(k) or "").strip()
        if "port" in body:
            try:
                cfg["port"] = int(body.get("port") or 465)
            except Exception:
                cfg["port"] = 465
        if "on" in body:
            cfg["on"] = bool(body.get("on"))
        pwd = body.get("password")
        if pwd:
            cfg["password"] = str(pwd).strip()
        if "sct_on" in body:
            cfg["sct_on"] = bool(body.get("sct_on"))
        if "sct_key" in body and str(body.get("sct_key")).strip():
            cfg["sct_key"] = str(body.get("sct_key")).strip()
        return cfg
    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/status":
            self._json({"app": "sashealth", "version": APP_VERSION, "status": "ok"})
        elif path == "/api/disks":
            force = "force=1" in self.path
            self._json(collect(force))
        elif path == "/api/snapshots":
            allf = "all=1" in self.path
            snaps = load_snaps()
            last_full = None
            items = []
            for s in snaps:
                s2 = {k: v for k, v in s.items() if k != "_file"}
                if "disks" in s2:
                    if "deltas" not in s2:
                        s2["deltas"] = compute_deltas(s2["disks"], last_full)
                    last_full = s2
                items.append(s2)
            items.reverse()
            total = len(items)
            if not allf:
                items = items[:10]
            self._json({"items": items, "total": total, "all": allf})
        elif path == "/api/notify":
            cfg = read_notify_cfg()
            out = dict(cfg)
            out["password"] = ""
            out["has_password"] = bool(cfg.get("password"))
            out["sct_key"] = ""
            out["has_sct_key"] = bool(cfg.get("sct_key"))
            out["providers"] = [[p[0], p[1], p[2], p[3], p[4]] for p in MAIL_PROVIDERS]
            out["autosnap"] = autosnap_on()
            self._json(out)
        elif path == "/":
            self._send(200, "text/html; charset=utf-8", PAGE.encode())
        else:
            self._send(404, "text/plain", b"not found")
    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/snapshot":
            data = collect(force=True)
            rec = save_snapshot(data["disks"], auto=False)
            self._json({"ok": True, "time": rec["time"], "data": data})
        elif path == "/api/autosnap":
            on = bool(self._body().get("on"))
            if on:
                if os.path.exists(AUTO_FLAG):
                    os.remove(AUTO_FLAG)
            else:
                open(AUTO_FLAG, "w").close()
            _cache["ts"] = 0
            self._json({"ok": True, "autosnap": on})
        elif path == "/api/interval":
            h = self._body().get("hours")
            try:
                h = int(h)
            except Exception:
                h = 0
            if h not in INTERVAL_PRESETS:
                self._json({"ok": False}, 400)
            else:
                with open(INTERVAL_FILE, "w", encoding="utf-8") as fh:
                    fh.write(str(h))
                _cache["ts"] = 0
                self._json({"ok": True, "interval_h": h})
        elif path == "/api/notify":
            cfg = self._merge_notify(self._body(), read_notify_cfg())
            if cfg.get("on"):
                miss = []
                if not cfg.get("host"): miss.append("SMTP 服务器")
                if not cfg.get("user"): miss.append("账号")
                if not cfg.get("password") and not cfg.get("has_password"):
                    miss.append("授权码/应用密码")
                if not cfg.get("to"): miss.append("收件人")
                if miss:
                    self._json({"ok": False, "error": "请填写：" + "、".join(miss)}, 400)
                    return
            if cfg.get("sct_on") and not cfg.get("sct_key"):
                self._json({"ok": False, "error": "已启用微信推送，请填写 SendKey"}, 400)
                return
            cfg = write_notify_cfg(cfg)
            out = dict(cfg)
            out["password"] = ""
            out["has_password"] = bool(cfg.get("password"))
            out["sct_key"] = ""
            out["has_sct_key"] = bool(cfg.get("sct_key"))
            self._json({"ok": True, "cfg": out})
        elif path == "/api/notify/test":
            body = self._body()
            cfg = self._merge_notify(body, read_notify_cfg())
            ch = str(body.get("channel") or "mail")
            if ch == "sct":
                ok, err = send_sct(cfg, "[飞牛] SAS 硬盘健康 · 测试消息",
                                   "这是一条来自飞牛 sashealth 的测试消息。\n\n"
                                   "收到说明微信推送配置可用，硬盘报红时会自动推送提醒。")
                self._json({"ok": ok, "channel": "sct",
                            "err": "" if ok else short_err(err), "detail": err})
            else:
                ok, err = send_mail(cfg, "[飞牛] SAS 硬盘健康 · 测试邮件",
                                    "这是一封来自飞牛 sashealth 的测试邮件。\n\n"
                                    "收到本邮件说明邮件通知配置可用，硬盘报红时会自动发送提醒。\n")
                self._json({"ok": ok, "channel": "mail",
                            "err": "" if ok else short_err(err), "detail": err})
        else:
            self._send(404, "text/plain", b"not found")
    def log_message(self, *a):
        pass

def _auto_thread():
    while True:
        try:
            if autosnap_on():
                ss = load_snaps()
                last = None
                for s in ss:
                    if last is None or s.get("time", 0) > last.get("time", 0):
                        last = s
                if last is None or time.time() - last.get("time", 0) > read_interval_h() * 3600:
                    collect(force=True)
        except Exception:
            pass
        time.sleep(300)

threading.Thread(target=_auto_thread, daemon=True).start()
threading.Thread(target=_update_thread, daemon=True).start()
ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
'''

# sanity check generated app.py compiles
compile(APP_PY, "app.py", "exec")

UI_CONFIG_APP = UI_CONFIG.replace("images/icon_{0}.png", "images/icon_{0}.png")
app_tar = io.BytesIO()
with tarfile.open(fileobj=app_tar, mode="w", format=tarfile.USTAR_FORMAT) as tf:
    tar_add(tf, "server", isdir=True)
    tar_add(tf, "server/app.py", APP_PY.encode("utf-8"))
    tar_add(tf, "ui", isdir=True)
    tar_add(tf, "ui/config", UI_CONFIG.encode("utf-8"))
    tar_add(tf, "ui/images", isdir=True)
    tar_add(tf, "ui/images/icon_64.png", make_icon(64))
    tar_add(tf, "ui/images/icon_128.png", make_icon(128))
    tar_add(tf, "ui/images/icon_256.png", make_icon(256))
app_tgz = gz(app_tar.getvalue())
md5 = hashlib.md5(app_tgz).hexdigest()

fpk_tar = io.BytesIO()
with tarfile.open(fileobj=fpk_tar, mode="w", format=tarfile.USTAR_FORMAT) as tf:
    tar_add(tf, "app.tgz", app_tgz)
    tar_add(tf, "cmd", isdir=True)
    tar_add(tf, "cmd/install_callback", INSTALL_CALLBACK.encode("utf-8"), 0o755)
    tar_add(tf, "cmd/install_init", b"#!/bin/bash\nexit 0\n", 0o755)
    tar_add(tf, "cmd/main", CMD_MAIN.encode("utf-8"), 0o755)
    tar_add(tf, "cmd/uninstall_callback", b"#!/bin/bash\nexit 0\n", 0o755)
    tar_add(tf, "cmd/uninstall_init", b"#!/bin/bash\nexit 0\n", 0o755)
    tar_add(tf, "cmd/upgrade_callback", b"#!/bin/bash\nexit 0\n", 0o755)
    tar_add(tf, "cmd/upgrade_init", b"#!/bin/bash\nexit 0\n", 0o755)
    tar_add(tf, "config", isdir=True)
    tar_add(tf, "config/privilege", PRIVILEGE.encode("utf-8"))
    tar_add(tf, "config/resource", RESOURCE.encode("utf-8"))
    tar_add(tf, "ICON.PNG", make_icon(128))
    tar_add(tf, "ICON_256.PNG", make_icon(256))
    tar_add(tf, "manifest", MANIFEST.format(md5=md5).encode("utf-8"))
    tar_add(tf, "ui", isdir=True)
    tar_add(tf, "ui/config", UI_CONFIG.encode("utf-8"))
    tar_add(tf, "ui/images", isdir=True)
    tar_add(tf, "ui/images/64.png", make_icon(64))
    tar_add(tf, "ui/images/256.png", make_icon(256))

out_path = os.path.join(OUT, "sashealth_0.12.0_x86.fpk")
with open(out_path, "wb") as f:
    f.write(gz(fpk_tar.getvalue()))
print("built:", out_path, os.path.getsize(out_path), "app.tgz md5:", md5)
