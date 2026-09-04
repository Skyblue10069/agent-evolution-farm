"""Strict external payment verification.
Only provider-confirmed payment events become verified money. Payments can be
attributed to an agent via provider metadata/custom_id when present.
"""
import base64,json,os,urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent; LEDGER=ROOT/"verified_payment_ledger.json"

def load():
    try:return json.loads(LEDGER.read_text())
    except Exception:return {"payments":[]}
def save(x): LEDGER.write_text(json.dumps(x,indent=2,ensure_ascii=False))

def record_provider_payment(provider,event_id,amount,currency,reference="",agent_id=None):
    amount=float(amount)
    if not event_id or amount<=0: raise ValueError("Invalid provider payment event")
    db=load()
    if any(p.get("provider")==provider and p.get("event_id")==event_id for p in db["payments"]): return False
    db["payments"].append({"provider":provider,"event_id":event_id,"amount":round(amount,2),"currency":currency,
      "verified":True,"verified_at":datetime.now(timezone.utc).isoformat(),"reference":reference,"agent_id":agent_id})
    save(db); return True

def paypal_get_access_token():
    cid=os.getenv("PAYPAL_CLIENT_ID"); secret=os.getenv("PAYPAL_CLIENT_SECRET")
    if not cid or not secret: raise RuntimeError("PayPal credentials not configured")
    base="https://api-m.sandbox.paypal.com" if os.getenv("PAYPAL_MODE","sandbox")=="sandbox" else "https://api-m.paypal.com"
    req=urllib.request.Request(base+"/v1/oauth2/token",data=b"grant_type=client_credentials",
      headers={"Accept":"application/json","Accept-Language":"en_US","Content-Type":"application/x-www-form-urlencoded"})
    req.add_header("Authorization","Basic "+base64.b64encode((cid+":"+secret).encode()).decode())
    with urllib.request.urlopen(req,timeout=20) as r:return base,json.loads(r.read().decode())["access_token"]

def paypal_verify_webhook(headers,body):
    webhook_id=os.getenv("PAYPAL_WEBHOOK_ID")
    if not webhook_id: raise RuntimeError("PAYPAL_WEBHOOK_ID is required")
    base,token=paypal_get_access_token(); payload=json.loads(body)
    verify={"auth_algo":headers.get("PAYPAL-AUTH-ALGO",""),"cert_url":headers.get("PAYPAL-CERT-URL",""),
      "transmission_id":headers.get("PAYPAL-TRANSMISSION-ID",""),"transmission_sig":headers.get("PAYPAL-TRANSMISSION-SIG",""),
      "transmission_time":headers.get("PAYPAL-TRANSMISSION-TIME",""),"webhook_id":webhook_id,"webhook_event":payload}
    req=urllib.request.Request(base+"/v1/notifications/verify-webhook-signature",data=json.dumps(verify).encode(),
      headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read().decode()).get("verification_status")=="SUCCESS",payload

def process_paypal_event(headers,body):
    ok,event=paypal_verify_webhook(headers,body)
    if not ok or event.get("event_type")!="PAYMENT.CAPTURE.COMPLETED": return False
    res=event.get("resource",{}); amount=res.get("amount") or {}
    # Attribution is accepted only from provider event metadata, never guessed.
    agent_id=res.get("custom_id") or res.get("invoice_id")
    return record_provider_payment("paypal",event.get("id",""),amount.get("value",0),amount.get("currency_code",""),
      res.get("id",""),agent_id)
