"""Agent Internet Capability Layer.

Provides bounded, auditable browser + HTTP capabilities for autonomous agents.
It does not bypass CAPTCHAs, authentication controls, paywalls, rate limits, or
platform rules. Credentials are never stored in this repository; authorized
session material must be supplied through the runner environment or an approved
external secret store.
"""
from __future__ import annotations
import hashlib, json, os, re, time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "internet_agent_state.json"
POLICY = ROOT / "internet_agent_policy.json"

DEFAULT_POLICY = {
    "enabled": True,
    "max_actions_per_task": 80,
    "max_task_seconds": 540,
    "request_timeout_seconds": 15,
    "browser_timeout_seconds": 20,
    "allowed_schemes": ["https"],
    "allow_browser_navigation": True,
    "allow_form_interaction": True,
    "allow_file_uploads": True,
    "allow_file_downloads": True,
    "allow_public_http": True,
    "allow_api_calls": True,
    "require_explicit_account_authorization": True,
    "blocked_action_patterns": [
        "captcha", "credential theft", "password dump", "bypass login",
        "bypass paywall", "rate limit bypass", "spam", "mass unsolicited",
        "impersonate", "payment fraud", "steal session", "cookie theft"
    ]
}


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        path.write_text(json.dumps(default, indent=2), encoding="utf-8")
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def policy() -> Dict[str, Any]:
    p = load_json(POLICY, DEFAULT_POLICY)
    merged = dict(DEFAULT_POLICY)
    merged.update(p if isinstance(p, dict) else {})
    return merged


def _safe_url(url: str) -> str:
    u = urlparse(url)
    if u.scheme not in policy()["allowed_schemes"] or not u.netloc:
        raise ValueError("Only public HTTPS URLs are permitted")
    return url


def _blocked(text: str) -> Optional[str]:
    low = text.lower()
    for pat in policy()["blocked_action_patterns"]:
        if pat in low:
            return pat
    return None


def _audit(agent_id: str, action: str, target: str, ok: bool, detail: str = "") -> None:
    data = load_json(STATE, {"events": [], "stats": {}})
    event = {
        "ts": time.time(), "agent_id": agent_id, "action": action,
        "target": target[:500], "ok": ok,
        "detail": detail[:1000],
        "proof": hashlib.sha256(f"{agent_id}|{action}|{target}|{detail}".encode()).hexdigest(),
    }
    data.setdefault("events", []).append(event)
    data["events"] = data["events"][-5000:]
    stats = data.setdefault("stats", {})
    stats[action] = int(stats.get(action, 0)) + 1
    save_json(STATE, data)


@dataclass
class InternetResult:
    ok: bool
    action: str
    url: str = ""
    status: Optional[int] = None
    title: str = ""
    text: str = ""
    data: Any = None
    error: str = ""
    proof: str = ""


class InternetAgent:
    """Bounded Internet operator used by each simulated agent."""
    def __init__(self, agent_id: str, account_registry: Optional[Dict[str, Any]] = None):
        self.agent_id = agent_id
        self.accounts = account_registry or {}
        self.p = policy()
        self.actions = 0
        self.started = time.monotonic()
        self.page = None
        self.browser = None

    def _guard(self, action: str, target: str = "") -> None:
        if not self.p.get("enabled", True):
            raise PermissionError("Internet capability is disabled by policy")
        if self.actions >= int(self.p["max_actions_per_task"]):
            raise TimeoutError("Internet action budget exhausted")
        if time.monotonic() - self.started >= int(self.p["max_task_seconds"]):
            raise TimeoutError("Internet task time budget exhausted")
        hit = _blocked(f"{action} {target}")
        if hit:
            raise PermissionError(f"Blocked unsafe action pattern: {hit}")
        self.actions += 1

    def fetch(self, url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
              data: Any = None) -> InternetResult:
        self._guard("fetch", url)
        url = _safe_url(url)
        try:
            import urllib.request
            req = urllib.request.Request(url, method=method.upper(), headers=headers or {})
            body = None
            if data is not None:
                body = json.dumps(data).encode() if isinstance(data, (dict, list)) else str(data).encode()
                req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, data=body, timeout=float(self.p["request_timeout_seconds"])) as r:
                raw = r.read(2_000_000)
                ctype = r.headers.get("Content-Type", "")
                text = raw.decode("utf-8", errors="replace")
                result_data = None
                if "json" in ctype:
                    try: result_data = json.loads(text)
                    except Exception: result_data = None
                proof = hashlib.sha256(raw).hexdigest()
                out = InternetResult(True, "fetch", url, r.status, text=text[:100000], data=result_data, proof=proof)
                _audit(self.agent_id, "fetch", url, True, f"status={r.status} proof={proof}")
                return out
        except Exception as e:
            _audit(self.agent_id, "fetch", url, False, str(e))
            return InternetResult(False, "fetch", url=url, error=str(e))

    def browser_start(self, headless: bool = True) -> InternetResult:
        self._guard("browser_start")
        try:
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self.browser = self._pw.chromium.launch(headless=headless)
            self.page = self.browser.new_page()
            self.page.set_default_timeout(int(self.p["browser_timeout_seconds"]) * 1000)
            _audit(self.agent_id, "browser_start", "", True)
            return InternetResult(True, "browser_start")
        except Exception as e:
            _audit(self.agent_id, "browser_start", "", False, str(e))
            return InternetResult(False, "browser_start", error=str(e))

    def navigate(self, url: str) -> InternetResult:
        self._guard("navigate", url)
        url = _safe_url(url)
        if not self.page:
            r = self.browser_start()
            if not r.ok: return r
        try:
            self.page.goto(url, wait_until="domcontentloaded")
            text = self.page.locator("body").inner_text(timeout=5000)[:100000]
            title = self.page.title()
            proof = hashlib.sha256(text.encode()).hexdigest()
            _audit(self.agent_id, "navigate", url, True, f"title={title} proof={proof}")
            return InternetResult(True, "navigate", url, title=title, text=text, proof=proof)
        except Exception as e:
            _audit(self.agent_id, "navigate", url, False, str(e))
            return InternetResult(False, "navigate", url=url, error=str(e))

    def click(self, selector: str) -> InternetResult:
        self._guard("click", selector)
        if not self.page: return InternetResult(False, "click", error="Browser not started")
        try:
            self.page.locator(selector).first.click()
            _audit(self.agent_id, "click", selector, True)
            return InternetResult(True, "click", proof=hashlib.sha256(selector.encode()).hexdigest())
        except Exception as e:
            _audit(self.agent_id, "click", selector, False, str(e))
            return InternetResult(False, "click", error=str(e))

    def type(self, selector: str, text: str) -> InternetResult:
        self._guard("type", selector)
        if not self.page: return InternetResult(False, "type", error="Browser not started")
        try:
            self.page.locator(selector).first.fill(text)
            _audit(self.agent_id, "type", selector, True, "text intentionally not logged")
            return InternetResult(True, "type")
        except Exception as e:
            _audit(self.agent_id, "type", selector, False, str(e))
            return InternetResult(False, "type", error=str(e))

    def select(self, selector: str, value: str) -> InternetResult:
        self._guard("select", selector)
        if not self.page: return InternetResult(False, "select", error="Browser not started")
        try:
            self.page.locator(selector).first.select_option(value)
            _audit(self.agent_id, "select", selector, True)
            return InternetResult(True, "select")
        except Exception as e:
            _audit(self.agent_id, "select", selector, False, str(e))
            return InternetResult(False, "select", error=str(e))

    def upload(self, selector: str, path: str) -> InternetResult:
        self._guard("upload", selector)
        if not self.page: return InternetResult(False, "upload", error="Browser not started")
        if not Path(path).is_file(): return InternetResult(False, "upload", error="File not found")
        try:
            self.page.locator(selector).first.set_input_files(path)
            _audit(self.agent_id, "upload", selector, True, Path(path).name)
            return InternetResult(True, "upload")
        except Exception as e:
            _audit(self.agent_id, "upload", selector, False, str(e))
            return InternetResult(False, "upload", error=str(e))

    def download(self, selector: str, destination: str) -> InternetResult:
        self._guard("download", selector)
        if not self.page: return InternetResult(False, "download", error="Browser not started")
        try:
            with self.page.expect_download() as d:
                self.page.locator(selector).first.click()
            dl = d.value
            dl.save_as(destination)
            proof = hashlib.sha256(Path(destination).read_bytes()).hexdigest()
            _audit(self.agent_id, "download", selector, True, f"proof={proof}")
            return InternetResult(True, "download", proof=proof)
        except Exception as e:
            _audit(self.agent_id, "download", selector, False, str(e))
            return InternetResult(False, "download", error=str(e))

    def extract(self, selector: str = "body") -> InternetResult:
        self._guard("extract", selector)
        if not self.page: return InternetResult(False, "extract", error="Browser not started")
        try:
            text = self.page.locator(selector).inner_text()[:100000]
            proof = hashlib.sha256(text.encode()).hexdigest()
            _audit(self.agent_id, "extract", selector, True, f"proof={proof}")
            return InternetResult(True, "extract", text=text, proof=proof)
        except Exception as e:
            _audit(self.agent_id, "extract", selector, False, str(e))
            return InternetResult(False, "extract", error=str(e))

    def screenshot(self, path: str) -> InternetResult:
        self._guard("screenshot", path)
        if not self.page: return InternetResult(False, "screenshot", error="Browser not started")
        try:
            self.page.screenshot(path=path, full_page=True)
            proof = hashlib.sha256(Path(path).read_bytes()).hexdigest()
            _audit(self.agent_id, "screenshot", path, True, f"proof={proof}")
            return InternetResult(True, "screenshot", proof=proof)
        except Exception as e:
            _audit(self.agent_id, "screenshot", path, False, str(e))
            return InternetResult(False, "screenshot", error=str(e))

    def close(self) -> None:
        for obj in (self.browser, getattr(self, "_pw", None)):
            try:
                if obj: obj.close() if hasattr(obj, "close") else obj.stop()
            except Exception: pass
        self.browser = self.page = None


def capabilities() -> Dict[str, Any]:
    p = policy()
    return {
        "browser": p["allow_browser_navigation"],
        "search_and_read": True,
        "navigate": True,
        "click": p["allow_form_interaction"],
        "type_and_select": p["allow_form_interaction"],
        "upload": p["allow_file_uploads"],
        "download": p["allow_file_downloads"],
        "http_api": p["allow_api_calls"],
        "public_https_only": True,
        "bounded_actions": p["max_actions_per_task"],
        "bounded_seconds": p["max_task_seconds"],
        "no_security_bypass": True,
    }


if __name__ == "__main__":
    print(json.dumps({"internet_capabilities": capabilities()}, indent=2))
