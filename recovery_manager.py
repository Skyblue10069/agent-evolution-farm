"""Checkpoint and recovery metadata. Never restores or invents money."""
import json, hashlib
from pathlib import Path

def run(s, root):
    path=Path(root)/"recovery_checkpoint.json"
    payload={"day":s.get("day",0),"alive":sum(a.get("permanent_status")=="alive" for a in s.get("agents",[])),"verified_revenue":s.get("verified_revenue",0),"schema_version":s.get("schema_version")}
    raw=json.dumps(payload,sort_keys=True).encode()
    payload["digest"]=hashlib.sha256(raw).hexdigest()
    path.write_text(json.dumps(payload,indent=2))
    s["last_checkpoint_digest"]=payload["digest"]
