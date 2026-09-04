"""Receive-only payout routing policy.
No withdrawal/debit operation exists here. Provider-confirmed incoming payments
are associated with the agent and destination account label for accounting.
Actual customer payments must be sent through the configured approved provider.
"""
import json,os
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).parent
OUT=ROOT/'payout_routing.json'

def main():
    try: ledger=json.loads((ROOT/'verified_payment_ledger.json').read_text()).get('payments',[])
    except Exception: ledger=[]
    destination=os.getenv('PAYOUT_DESTINATION_ID','')
    rows=[]
    for p in ledger:
        if p.get('verified'):
            rows.append({'event_id':p.get('event_id'),'agent_id':p.get('agent_id'),'provider':p.get('provider'),
                         'amount':p.get('amount'),'currency':p.get('currency'),'destination_configured':bool(destination),
                         'destination_id_label':'configured_receive_account' if destination else 'NOT_CONFIGURED',
                         'receive_only':True,'recorded_at':datetime.now(timezone.utc).isoformat()})
    OUT.write_text(json.dumps({'receive_only':True,'no_withdrawals':True,'payments':rows},indent=2,ensure_ascii=False))
    print(f'PAYOUT ROUTER: {len(rows)} verified incoming payments mapped to receive-only routing records.')
if __name__=='__main__': main()
