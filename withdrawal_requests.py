"""Owner-controlled withdrawal/use requests.
Agents may request a use of their verified funds, but there is no automatic debit.
Nothing leaves the receiving account until the owner explicitly approves it.
"""
import json
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).parent
OUT=ROOT/'withdrawal_requests.json'

def create_request(agent_id, amount, currency, purpose):
    try: rows=json.loads(OUT.read_text()).get('requests',[])
    except Exception: rows=[]
    req={'request_id':f'req-{len(rows)+1:06d}','agent_id':agent_id,'amount':amount,'currency':currency,
         'purpose':purpose,'status':'awaiting_owner_confirmation','created_at':datetime.now(timezone.utc).isoformat(),
         'owner_confirmation_required':True,'debit_executed':False}
    rows.append(req); OUT.write_text(json.dumps({'receive_only_until_owner_confirms':True,'requests':rows},indent=2,ensure_ascii=False)); return req

def main():
    try: rows=json.loads(OUT.read_text()).get('requests',[])
    except Exception: rows=[]
    print(f'WITHDRAWAL GATE: {len(rows)} request(s); automatic debits are disabled.')
if __name__=='__main__': main()
