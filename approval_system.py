"""Owner approval queue and optional MTN Cameroon payout executor.

Safety model: agents can propose spending, but only an explicit owner approval
can move a proposal to APPROVED. The executor will only submit an outgoing
MTN Cameroon mobile-money payout for an approved proposal when the required
server-side credentials and destination are configured. It never exposes the
secret key to the phone UI.
"""
import json, os, secrets, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from trust_system import can_request, snapshot, load as load_history, sync_from_state

ROOT = Path(__file__).parent
QUEUE = ROOT / "approval_queue.json"


def now(): return datetime.now(timezone.utc).isoformat()

def load():
    try: return json.loads(QUEUE.read_text())
    except Exception: return {"proposals": []}

def save(data): QUEUE.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def create_proposal(agent_id, title, amount, currency="XAF", reason="", recipient=None, details=None):
    """Create a rich owner-review request.

    Agents are expected to work from zero first. A request should explain what
    was already attempted and why owner funds are needed now. The UI is still
    one-click, but the owner gets enough context to make an informed decision.
    """
    data=load(); details=details or {}
    h=snapshot(agent_id)
    if not can_request(agent_id):
        raise PermissionError(f"Funding request blocked: trust={h.get('trust_score',0)}/100, work={h.get('completed_work',0)}; requires trust >=35 and 2 completed work activities.")
    proposal={
        "proposal_id":"apr_"+secrets.token_hex(8), "agent_id":agent_id,
        "title":title, "amount":int(amount), "currency":currency, "reason":reason,
        "request_type":details.get("request_type","work_expense"),
        "why_now":details.get("why_now",""),
        "what_for":details.get("what_for",""),
        "work_already_done":details.get("work_already_done",[]),
        "evidence":details.get("evidence",[]),
        "expected_result":details.get("expected_result",""),
        "expected_revenue":details.get("expected_revenue","unknown"),
        "cost_breakdown":details.get("cost_breakdown",[]),
        "alternatives_considered":details.get("alternatives_considered",[]),
        "risk_if_approved":details.get("risk_if_approved",""),
        "risk_if_rejected":details.get("risk_if_rejected",""),
        "deadline":details.get("deadline",""),
        "success_condition":details.get("success_condition",""),
        "one_time":bool(details.get("one_time",True)),
        "recipient":recipient or {}, "status":"PENDING", "created_at":now(),
        "approved_at":None, "rejected_at":None, "executed_at":None,
        "execution_status":"NOT_REQUESTED", "provider_transfer_id":None, "error":None
    }; data["proposals"].append(proposal); save(data); return proposal

def decide(proposal_id, action):
    action=action.upper()
    if action not in {"APPROVE","REJECT"}: raise ValueError("action must be APPROVE or REJECT")
    data=load()
    for p in data["proposals"]:
        if p["proposal_id"]==proposal_id and p["status"]=="PENDING":
            p["status"]="APPROVED" if action=="APPROVE" else "REJECTED"
            p["approved_at"]=now() if action=="APPROVE" else None; p["rejected_at"]=now() if action=="REJECT" else None
            save(data); return p
    raise KeyError("pending proposal not found")

def execute_mtn(p):
    """Execute one already-approved XAF payout through MTN MoMo Withdrawals.

    Live execution is disabled by default. The exact MTN endpoint is supplied
    through MTN_WITHDRAWALS_URL so the deployment uses the endpoint assigned
    by the approved MTN application rather than assuming a production URL.
    """
    if p.get("status") != "APPROVED":
        raise ValueError("proposal is not approved")
    if p.get("execution_status") in {"SUBMITTED", "EXECUTED"}:
        return p
    if str(p.get("currency", "")).upper() != "XAF":
        raise RuntimeError("MTN Cameroon payout requires an XAF amount. Settle non-XAF earnings to XAF with provider confirmation first.")
    client_id = os.getenv("MTN_CLIENT_ID", "")
    client_secret = os.getenv("MTN_CLIENT_SECRET", "")
    env = os.getenv("MTN_ENV", "sandbox").lower()
    live_enabled = os.getenv("MTN_LIVE_PAYOUT_ENABLED", "false").lower() == "true"
    if env == "production" and not live_enabled:
        raise RuntimeError("Production MTN payouts are disabled. Enable MTN_LIVE_PAYOUT_ENABLED only after MTN approval and required verification.")
    if not client_id or not client_secret:
        raise RuntimeError("MTN_CLIENT_ID and MTN_CLIENT_SECRET are not configured")
    phone = p.get("recipient", {}).get("msisdn") or os.getenv("PAYOUT_MOBILE_MONEY_MSISDN", "")
    if not phone:
        raise RuntimeError("A Cameroon Mobile Money destination is required")
    phone = str(phone).strip()
    if not (phone.startswith("237") and len(phone) == 12 and phone.isdigit()):
        raise RuntimeError("Payout phone must be a 12-digit Cameroon number starting with 237")
    amount = int(p["amount"])
    if amount <= 0:
        raise RuntimeError("Payout amount must be positive")
    token_url = os.getenv("MTN_TOKEN_URL", "https://api.mtn.com/oauth/client_credential/accesstoken?grant_type=client_credentials")
    withdrawal_url = os.getenv("MTN_WITHDRAWALS_URL", "")
    if not withdrawal_url:
        raise RuntimeError("MTN_WITHDRAWALS_URL is not configured; use the endpoint provided by the approved MTN Withdrawals V1 application")
    token_req = urllib.request.Request(token_url, data=b"", headers={"Authorization":"Basic " + __import__('base64').b64encode((client_id+":"+client_secret).encode()).decode(), "Content-Type":"application/x-www-form-urlencoded"}, method="POST")
    try:
        with urllib.request.urlopen(token_req, timeout=30) as r:
            token_data=json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"MTN OAuth error {e.code}: {e.read().decode()[:500]}")
    access_token=token_data.get("access_token")
    if not access_token:
        raise RuntimeError("MTN OAuth response did not contain an access_token")
    payload={"amount":amount,"currency":"XAF","externalId":p["proposal_id"],"payee":{"partyIdType":"MSISDN","partyId":phone}}
    req=urllib.request.Request(withdrawal_url,data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+access_token,"Content-Type":"application/json","X-Reference-Id":p["proposal_id"]},method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw=r.read().decode(); result=json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"MTN Withdrawals API error {e.code}: {e.read().decode()[:500]}")
    data=load()
    for x in data["proposals"]:
        if x["proposal_id"]==p["proposal_id"]:
            x["execution_status"]="SUBMITTED"
            x["executed_at"]=now()
            x["provider_transfer_id"]=result.get("referenceId") or result.get("transaction_id") or result.get("externalId") or p["proposal_id"]
            x["error"]=None
            x["provider"]="mtn"
            x["provider_environment"]=env
            save(data)
            return x
    return p

HTML="""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>Agent Evolution</title><style>
body{font-family:system-ui;margin:0;background:#0f1115;color:#f4f4f5}.wrap{max-width:900px;margin:auto;padding:14px}.card{background:#191c23;border:1px solid #303542;border-radius:18px;padding:16px;margin:10px 0}.amount{font-size:28px;font-weight:850}.meta{color:#aeb6c4;font-size:14px;line-height:1.55}.btn{width:100%;border:0;border-radius:12px;padding:14px;margin-top:10px;font-size:16px;font-weight:800}.approve{background:#4ade80}.reject{background:#f87171}.send{background:#60a5fa}.tabs{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;position:sticky;top:0;padding:8px 0;background:#0f1115;z-index:5}.tab{padding:11px 4px;border:1px solid #303542;background:#191c23;color:white;border-radius:12px;font-weight:800}.hidden{display:none}.pill{display:inline-block;padding:5px 8px;border-radius:999px;background:#272c36;margin:2px;font-size:13px}.bar{height:9px;background:#303542;border-radius:9px;overflow:hidden;margin:8px 0}.fill{height:100%;background:#4ade80}.event{border-left:3px solid #596273;padding:8px 10px;margin:8px 0}.rank{display:flex;align-items:center;gap:10px}.ranknum{font-size:26px;font-weight:900;width:42px}.select{width:100%;padding:12px;border-radius:12px;background:#191c23;color:#fff;border:1px solid #303542;font-size:16px}.chart{width:100%;height:230px;background:#11141a;border-radius:14px;margin-top:10px}.legend{display:flex;gap:8px;flex-wrap:wrap}.stat{font-size:20px;font-weight:800}.small{font-size:12px;color:#8993a3}@media(max-width:600px){.tabs{grid-template-columns:repeat(3,1fr)}.tabs .tab:nth-child(4),.tabs .tab:nth-child(5){display:block}.grid{grid-template-columns:1fr!important}}</style></head><body><div class='wrap'><h1>🔐 Agent Evolution</h1><p class='meta'>Agents work from zero. Trust changes from observed work quality and results. You control every funding decision and every payout execution.</p><div class='tabs'><button class='tab' onclick="show('approvals')">💸 Approvals</button><button class='tab' onclick="show('agents')">🤖 Agents</button><button class='tab' onclick="show('rankings')">🏆 Rankings</button><button class='tab' onclick="show('analytics')">📈 Graphs</button><button class='tab' onclick="show('history')">📜 History</button></div><section id='approvals'><div id='list'>Loading…</div></section><section id='agents' class='hidden'><div id='agentList'>Loading…</div></section><section id='rankings' class='hidden'><div id='rankingList'>Loading…</div></section><section id='analytics' class='hidden'><div class='card'><h2>📈 Agent progress</h2><select id='agentSelect' class='select' onchange='loadAnalytics()'><option>Loading…</option></select><div id='stats'></div><h3>Trust over time</h3><svg id='trustChart' class='chart' viewBox='0 0 800 230' preserveAspectRatio='none'></svg><h3>Verified earnings over time</h3><svg id='earnChart' class='chart' viewBox='0 0 800 230' preserveAspectRatio='none'></svg><h3>Skills over time</h3><select id='skillSelect' class='select' onchange='loadAnalytics()'></select><svg id='skillChart' class='chart' viewBox='0 0 800 230' preserveAspectRatio='none'></svg></div></section><section id='history' class='hidden'><div id='historyList'>Loading…</div></section></div><script>
function formatMoney(m){let e=Object.entries(m||{});return e.length?e.map(([c,v])=>`${Number(v).toFixed(2)} ${c}`).join(' · '):'0'}
function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function show(x){['approvals','agents','rankings','analytics','history'].forEach(y=>document.getElementById(y).classList.toggle('hidden',x!==y));if(x==='agents')loadAgents();if(x==='rankings')loadRankings();if(x==='analytics')loadAnalytics();if(x==='history')loadHistory()}
async function load(){let d=await (await fetch('/api/proposals')).json(),ps=d.proposals||[];document.getElementById('list').innerHTML=ps.length?ps.slice().reverse().map(p=>`<div class='card'><div class='amount'>${p.amount} ${esc(p.currency)}</div><h2>${esc(p.title)}</h2><div class='meta'><b>Agent:</b> ${esc(p.agent_id)}<br><b>Why:</b> ${esc(p.reason||'Not supplied')}<br><b>Why now:</b> ${esc(p.why_now||'Not supplied')}<br><b>Use:</b> ${esc(p.what_for||'Not supplied')}<br><b>Work done:</b> ${esc((p.work_already_done||[]).join(' • ')||'None')}<br><b>Evidence:</b> ${esc((p.evidence||[]).join(' • ')||'None')}<br><b>Expected result:</b> ${esc(p.expected_result||'Not supplied')}<br><b>Expected revenue:</b> ${esc(p.expected_revenue||'Unknown')}<br><b>Costs:</b> ${esc((p.cost_breakdown||[]).join(' • ')||'Not supplied')}<br><b>Alternatives:</b> ${esc((p.alternatives_considered||[]).join(' • ')||'None')}<br><b>Risk if approved:</b> ${esc(p.risk_if_approved||'Not supplied')}<br><b>If rejected:</b> ${esc(p.risk_if_rejected||'Not supplied')}<br><b>Deadline:</b> ${esc(p.deadline||'None')}<br><b>Success condition:</b> ${esc(p.success_condition||'Not supplied')}<br><b>Status:</b> ${esc(p.status)} · <b>Execution:</b> ${esc(p.execution_status)}</div>${p.status==='PENDING'?`<button class='btn approve' onclick="decide('${p.proposal_id}','APPROVE')">✅ Approve</button><button class='btn reject' onclick="decide('${p.proposal_id}','REJECT')">❌ Reject</button>`:''}${p.status==='APPROVED'&&p.execution_status==='NOT_REQUESTED'?`<button class='btn send' onclick="executePayout('${p.proposal_id}')">💸 Execute approved payout</button>`:''}</div>`).join(''):'<p class="meta">No funding requests.</p>'}
async function getAgents(){return (await (await fetch('/api/agents')).json()).agents||[]}
async function loadAgents(){let a=await getAgents();document.getElementById('agentList').innerHTML=a.length?a.slice().sort((x,y)=>(y.trust_score||0)-(x.trust_score||0)).map(x=>{let t=Number(x.trust_score||0);return `<div class='card'><h2>🤖 ${esc(x.name)}</h2><div class='pill'>Trust ${t.toFixed(1)}/100</div><div class='pill'>Work ${x.completed_work||0}</div><div class='pill'>Success ${x.successful_runs||0}</div><div class='pill'>Failures ${x.failures||0}</div><div class='pill'>Earnings ${esc(JSON.stringify(x.earnings_by_currency||{}))}</div><div class='bar'><div class='fill' style='width:${Math.min(100,t)}%'></div></div><div class='meta'>Day ${x.days_active||0} · Generation ${x.generation||0} · Funding requests ${x.funding_requests||0}</div></div>`}).join(''):'<p class="meta">No active agents.</p>'}
async function loadRankings(){let d=await (await fetch('/api/leaderboard')).json(),a=d.leaderboard||[];document.getElementById('rankingList').innerHTML=a.length?a.map((x,i)=>`<div class='card rank'><div class='ranknum'>#${x.rank||i+1}</div><div style='flex:1'><h2>${esc(x.name)}</h2><div class='pill'>Trust ${Number(x.trust||0).toFixed(1)}</div><div class='pill'>Earnings ${esc(formatMoney(x.earnings_by_currency||{}))}</div><div class='pill'>Skills ${Number(x.skill_total||0).toFixed(1)}</div><div class='pill'>Wins ${x.wins||0}</div><div class='meta'>Generation ${x.generation||0} · Work ${x.work||0}</div></div></div>`).join(''):'<p class="meta">No rankings yet.</p>'}
function chart(svgId,vals,label,maxY){let svg=document.getElementById(svgId),w=800,h=230,p=28;svg.innerHTML='';if(!vals.length)return;let mx=Math.max(maxY||0,...vals.map(v=>Number(v)||0),1);let pts=vals.map((v,i)=>{let x=p+(w-2*p)*(vals.length===1?0.5:i/(vals.length-1));let y=h-p-(h-2*p)*(Number(v)||0)/mx;return [x,y]}),path='M'+pts.map(q=>q.join(',')).join(' L');let ns='http://www.w3.org/2000/svg';let pl=document.createElementNS(ns,'path');pl.setAttribute('d',path);pl.setAttribute('fill','none');pl.setAttribute('stroke','white');pl.setAttribute('stroke-width','4');svg.appendChild(pl);let txt=document.createElementNS(ns,'text');txt.setAttribute('x',p);txt.setAttribute('y',20);txt.setAttribute('fill','white');txt.textContent=label+' · max '+mx.toFixed(1);svg.appendChild(txt);}
async function loadAnalytics(){let a=await getAgents(),sel=document.getElementById('agentSelect');if(!a.length)return;if(!sel.options.length||sel.options[0].text==='Loading…'){sel.innerHTML=a.map(x=>`<option value='${esc(x.id)}'>${esc(x.name)}</option>`).join('');}let aid=sel.value||a[0].id;let d=await (await fetch('/api/history')).json(),x=(d.agents||{})[aid];if(!x)return;let snaps=x.snapshots||[];document.getElementById('stats').innerHTML=`<div class='pill'>Current trust <span class='stat'>${Number(x.trust_score||0).toFixed(1)}</span></div><div class='pill'>Verified earnings <span class='stat'>${esc(formatMoney(x.earnings_by_currency||{}))}</span></div><div class='pill'>Work <span class='stat'>${x.completed_work||0}</span></div><div class='pill'>Success <span class='stat'>${x.successful_runs||0}</span></div>`;chart('trustChart',snaps.map(s=>s.trust),'Trust',100);let currencies=[...new Set(snaps.flatMap(s=>Object.keys(s.earnings_by_currency||{})))];let earnCurrency=currencies[0]||'XAF';chart('earnChart',snaps.map(s=>Number((s.earnings_by_currency||{})[earnCurrency]||0)),earnCurrency,null);let skills=Object.keys((snaps[snaps.length-1]||{}).skills||{});let ss=document.getElementById('skillSelect');if(!skills.length)return;let old=ss.value;ss.innerHTML=skills.map(k=>`<option value='${esc(k)}'>${esc(k)}</option>`).join('');if(skills.includes(old))ss.value=old;let sk=ss.value||skills[0];chart('skillChart',snaps.map(s=>Number((s.skills||{})[sk]||0)),sk,100)}
async function loadHistory(){let d=await (await fetch('/api/history')).json(),a=d.agents||{};document.getElementById('historyList').innerHTML=Object.keys(a).length?Object.entries(a).map(([id,x])=>`<div class='card'><h2>📜 ${esc(x.name||id)}</h2><div class='meta'>Trust ${Number(x.trust_score||0).toFixed(1)} · Work ${x.completed_work||0} · Success ${x.successful_runs||0} · Failures ${x.failures||0}</div>${(x.events||[]).slice().reverse().slice(0,30).map(e=>`<div class='event'><b>${esc(e.type)}</b> — ${esc(e.summary)}<br><span class='meta'>Trust change: ${Number(e.trust_delta||0)>=0?'+':''}${e.trust_delta||0} · ${esc(e.timestamp)}</span></div>`).join('')}</div>`).join(''):'<p class="meta">No activity recorded yet.</p>'}
async function decide(id,a){if(!confirm(a==='APPROVE'?'Approve this request?':'Reject this request?'))return;let r=await fetch('/api/decision',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({proposal_id:id,action:a})}),d=await r.json();if(d.error)alert(d.error);load()}
async function executePayout(id){if(!confirm('Execute this already-approved payout now?'))return;let r=await fetch('/api/execute',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams({proposal_id:id})}),d=await r.json();if(d.error)alert(d.error);load()}
load();setInterval(load,5000);</script></body></html>"""

class Handler(BaseHTTPRequestHandler):
    def send_json(self,obj,code=200):
        raw=json.dumps(obj).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path=="/api/proposals": self.send_json(load()); return
        if self.path=="/api/history": self.send_json(load_history()); return
        if self.path=="/api/leaderboard":
            try: state=json.loads((ROOT/"state.json").read_text()); sync_from_state(state)
            except Exception: state={"agents":[]}
            hist=load_history(); rows=[]
            for a in state.get("agents",[]):
                h=hist.get("agents",{}).get(a["id"],{})
                rows.append({"id":a["id"],"name":a.get("name",a["id"]),"trust":h.get("trust_score",0),"verified_revenue_xaf":h.get("verified_revenue",0),"earnings_by_currency":a.get("earnings_by_currency",{}),"skill_total":round(sum(a.get("skills",{}).values()),2),"wins":a.get("wins",0),"work":h.get("completed_work",0),"generation":a.get("generation",0)})
            rows.sort(key=lambda x:(x["verified_revenue_xaf"],x["trust"],x["skill_total"],x["wins"]),reverse=True)
            for i,x in enumerate(rows,1): x["rank"]=i
            self.send_json({"leaderboard":rows}); return
        if self.path=="/api/agents":
            try: state=json.loads((ROOT/"state.json").read_text()); sync_from_state(state)
            except Exception: state={"agents":[]}
            hist=load_history(); agents=[]
            for a in state.get("agents",[]):
                h=hist.get("agents",{}).get(a["id"],{})
                agents.append({**a,"trust_score":h.get("trust_score",0),"completed_work":h.get("completed_work",0),"successful_runs":h.get("successful_runs",0),"failures":h.get("failures",0),"verified_revenue":h.get("verified_revenue",0),"earnings_by_currency":a.get("earnings_by_currency",{}),"funding_requests":h.get("funding_requests",0)})
            self.send_json({"agents":agents}); return
        if self.path=="/":
            raw=HTML.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(raw))); self.end_headers(); self.wfile.write(raw); return
        self.send_error(404)
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0")); body=parse_qs(self.rfile.read(n).decode())
        try:
            if self.path=="/api/decision": self.send_json(decide(body["proposal_id"][0],body["action"][0])); return
            if self.path=="/api/execute":
                pid=body["proposal_id"][0]; p=next(x for x in load()["proposals"] if x["proposal_id"]==pid); self.send_json(execute_mtn(p)); return
            self.send_error(404)
        except Exception as e: self.send_json({"error":str(e)},400)
    def log_message(self,*args): pass

def serve(host="127.0.0.1",port=8080):
    print(f"Owner approval screen: http://{host}:{port}"); ThreadingHTTPServer((host,port),Handler).serve_forever()

if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd")
    c=sub.add_parser("create"); c.add_argument("agent_id"); c.add_argument("title"); c.add_argument("amount",type=int); c.add_argument("--currency",default="XAF"); c.add_argument("--reason",default=""); c.add_argument("--recipient-name",default=""); c.add_argument("--recipient-msisdn",default="")
    d=sub.add_parser("decide"); d.add_argument("proposal_id"); d.add_argument("action",choices=["APPROVE","REJECT"])
    e=sub.add_parser("execute"); e.add_argument("proposal_id")
    sub.add_parser("serve"); a=ap.parse_args()
    if a.cmd=="create": print(json.dumps(create_proposal(a.agent_id,a.title,a.amount,a.currency,a.reason,{"name":a.recipient_name,"msisdn":a.recipient_msisdn}),indent=2))
    elif a.cmd=="decide": print(json.dumps(decide(a.proposal_id,a.action),indent=2))
    elif a.cmd=="execute":
        p=next(x for x in load()["proposals"] if x["proposal_id"]==a.proposal_id); print(json.dumps(execute_mtn(p),indent=2))
    else: serve(os.getenv("APPROVAL_HOST","127.0.0.1"),int(os.getenv("APPROVAL_PORT","8080")))
