"""Safe local Android control bridge for Agent Evolution.

The cloud farm cannot directly control a physical Android phone. This bridge is
intended for a local agent runtime on the phone. It talks to a companion Android
AccessibilityService on 127.0.0.1 and provides audited, allowlisted actions.
"""
from __future__ import annotations
import hashlib, json, os, time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
POLICY_FILE = ROOT / "android_control_policy.json"
AUDIT_FILE = ROOT / "android_control_audit.json"
DEFAULT = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 8787,
    "allow_launch_package": True,
    "allow_open_https": True,
    "allow_tap_text": True,
    "allow_type_text": True,
    "allow_navigation": True,
    "max_actions_per_task": 50,
    "request_timeout_seconds": 5,
    "allowed_packages": [],
}

def load(path, default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return dict(default)

def audit(action, ok, detail=""):
    d = load(AUDIT_FILE, {"events": []})
    proof = hashlib.sha256(f"{time.time()}|{action}|{detail}".encode()).hexdigest()
    d.setdefault("events", []).append({"ts": time.time(), "action": action, "ok": ok, "detail": detail[:500], "proof": proof})
    d["events"] = d["events"][-2000:]
    AUDIT_FILE.write_text(json.dumps(d, indent=2), encoding="utf-8")

class AndroidController:
    def __init__(self):
        self.p = {**DEFAULT, **load(POLICY_FILE, DEFAULT)}
        self.actions = 0
    def _guard(self):
        if not self.p["enabled"]: raise PermissionError("Android control disabled")
        if self.actions >= int(self.p["max_actions_per_task"]): raise TimeoutError("Android action budget exhausted")
        self.actions += 1
    def call(self, action, payload=None):
        self._guard(); payload = payload or {}
        body = json.dumps({"action": action, "payload": payload}).encode()
        url = f"http://{self.p['host']}:{self.p['port']}/command"
        try:
            r = urlopen(Request(url, data=body, headers={"Content-Type":"application/json"}), timeout=float(self.p["request_timeout_seconds"]))
            out = json.loads(r.read().decode())
            audit(action, bool(out.get("ok")), json.dumps(payload))
            return out
        except Exception as e:
            audit(action, False, str(e)); return {"ok": False, "error": str(e)}
    def launch_app(self, package):
        if not self.p["allow_launch_package"]: raise PermissionError("Launch disabled")
        allowed = self.p.get("allowed_packages", [])
        if allowed and package not in allowed: raise PermissionError("Package not allowlisted")
        return self.call("launch_package", {"package": package})
    def open_url(self, url):
        if not self.p["allow_open_https"] or urlparse(url).scheme != "https": raise ValueError("Only HTTPS URLs are allowed")
        return self.call("open_url", {"url": url})
    def tap_text(self, text): return self.call("tap_text", {"text": text})
    def type_text(self, text): return self.call("type_text", {"text": text})
    def back(self): return self.call("back")
    def home(self): return self.call("home")
    def recents(self): return self.call("recents")
    def tap_point(self, x, y): return self.call("tap_point", {"x": float(x), "y": float(y)})
    def swipe(self, x1, y1, x2, y2, duration_ms=350):
        return self.call("swipe", {"x1":float(x1),"y1":float(y1),"x2":float(x2),"y2":float(y2),"duration_ms":int(duration_ms)})
    def screen_state(self): return self.call("screen_state")

if __name__ == "__main__":
    print(json.dumps({"android_control": "local companion bridge", "host": DEFAULT["host"], "port": DEFAULT["port"], "cloud_runner_direct_phone_control": False}, indent=2))
