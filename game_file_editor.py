"""User-authorized game file editor for Agent Evolution.

Edits only files inside directories explicitly granted to the local runtime.
Designed for saves, configs, mod/add-on data and other user-owned game data.
It refuses executable/APK/DEX/native-binary targets and never attempts to
bypass Android scoped storage, DRM or anti-cheat protections.
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POLICY = ROOT / "game_file_policy.json"
AUDIT = ROOT / "game_file_audit.json"
DEFAULT = {
    "enabled": True,
    "allowed_roots": [],
    "max_file_mb": 32,
    "backup_before_edit": True,
    "allowed_extensions": [".json", ".json5", ".txt", ".ini", ".cfg", ".conf", ".xml", ".yaml", ".yml", ".properties", ".mcfunction", ".mcstructure", ".dat", ".sav", ".save"],
    "blocked_extensions": [".apk", ".aab", ".dex", ".jar", ".so", ".exe", ".dll", ".elf"],
}

def load(p, default):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return dict(default)

def save(p, data): p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def audit(action, ok, detail=""):
    d=load(AUDIT,{"events":[]})
    proof=hashlib.sha256(f"{time.time()}|{action}|{detail}".encode()).hexdigest()
    d.setdefault("events",[]).append({"ts":time.time(),"action":action,"ok":bool(ok),"detail":detail[:1000],"proof":proof})
    d["events"]=d["events"][-3000:]
    save(AUDIT,d)

class GameFileEditor:
    def __init__(self): self.p={**DEFAULT,**load(POLICY,DEFAULT)}
    def _path(self, raw):
        if not self.p.get("enabled",True): raise PermissionError("game file editing disabled")
        p=Path(raw).expanduser().resolve()
        roots=[Path(x).expanduser().resolve() for x in self.p.get("allowed_roots",[])]
        if not roots: raise PermissionError("No user-authorized game data root is configured")
        if not any(p==r or r in p.parents for r in roots): raise PermissionError("Path is outside authorized game-data roots")
        ext=p.suffix.lower()
        if ext in self.p.get("blocked_extensions",[]): raise PermissionError("Executable/protected file type is blocked")
        allowed=self.p.get("allowed_extensions",[])
        if allowed and ext not in allowed: raise PermissionError(f"File type {ext or '<none>'} is not enabled")
        if p.exists() and p.is_file() and p.stat().st_size > int(self.p.get("max_file_mb",32))*1024*1024: raise ValueError("File exceeds configured size limit")
        return p
    def discover(self):
        from game_file_discovery import discover
        return discover()
    def list_files(self, root):
        r=self._path(root)
        if not r.is_dir(): raise ValueError("Root must be a directory")
        out=[]
        for p in r.rglob("*"):
            if p.is_file() and p.suffix.lower() in self.p.get("allowed_extensions",[]):
                out.append({"path":str(p),"size":p.stat().st_size})
        audit("list",True,str(r)); return out[:5000]
    def read(self, path):
        p=self._path(path)
        if not p.is_file(): raise FileNotFoundError(path)
        data=p.read_bytes()
        try: text=data.decode("utf-8")
        except UnicodeDecodeError: text=None
        audit("read",True,str(p)); return {"path":str(p),"size":len(data),"sha256":hashlib.sha256(data).hexdigest(),"text":text}
    def write(self, path, content):
        p=self._path(path)
        if isinstance(content,str): data=content.encode("utf-8")
        else: data=bytes(content)
        if len(data)>int(self.p.get("max_file_mb",32))*1024*1024: raise ValueError("Content exceeds configured size limit")
        p.parent.mkdir(parents=True,exist_ok=True)
        backup=None
        if p.exists() and self.p.get("backup_before_edit",True):
            backup=p.with_name(p.name+f".agentbak-{int(time.time())}")
            shutil.copy2(p,backup)
        tmp=p.with_name(p.name+".agenttmp")
        tmp.write_bytes(data); os.replace(tmp,p)
        audit("write",True,json.dumps({"path":str(p),"backup":str(backup) if backup else None}))
        return {"ok":True,"path":str(p),"size":len(data),"sha256":hashlib.sha256(data).hexdigest(),"backup":str(backup) if backup else None}
    def patch_text(self,path,old,new,replace_all=False):
        current=self.read(path)
        if current["text"] is None: raise ValueError("File is not UTF-8 text; use a game-specific adapter")
        count=current["text"].count(old)
        if count==0: raise ValueError("Target text not found")
        if not replace_all and count!=1: raise ValueError(f"Target occurs {count} times; specify replace_all")
        updated=current["text"].replace(old,new,-1 if replace_all else 1)
        return self.write(path,updated)

if __name__=="__main__":
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    l=sub.add_parser("list"); l.add_argument("root")
    r=sub.add_parser("read"); r.add_argument("path")
    w=sub.add_parser("write"); w.add_argument("path"); w.add_argument("content")
    p=sub.add_parser("patch"); p.add_argument("path"); p.add_argument("old"); p.add_argument("new"); p.add_argument("--all",action="store_true")
    a=ap.parse_args(); e=GameFileEditor()
    if a.cmd=="list": out=e.list_files(a.root)
    elif a.cmd=="read": out=e.read(a.path)
    elif a.cmd=="write": out=e.write(a.path,a.content)
    else: out=e.patch_text(a.path,a.old,a.new,a.all)
    print(json.dumps(out,indent=2))
