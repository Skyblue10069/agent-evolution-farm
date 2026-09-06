"""Agent-owned account registry. Stores identities and capability metadata, never passwords/tokens."""
import json,secrets
from pathlib import Path
ROOT=Path(__file__).parent; DB=ROOT/'agent_accounts.json'

def load():
    try:return json.loads(DB.read_text())
    except Exception:return {'version':1,'accounts':[]}

def ensure_account(agent_id,service,kind='research'):
    db=load()
    for a in db['accounts']:
        if a['agent_id']==agent_id and a['service']==service:return a
    a={'account_id':secrets.token_hex(8),'agent_id':agent_id,'service':service,'kind':kind,'status':'unconfigured','credential_ref':None}
    db['accounts'].append(a); DB.write_text(json.dumps(db,indent=2)); return a

def ensure_agents(agent_ids,services=('web_research',)):
    for aid in agent_ids:
        for service in services: ensure_account(aid,service)

if __name__=='__main__':
    try: st=json.loads((ROOT/'state.json').read_text()); ids=[a.get('id') for a in st.get('agents',[]) if a.get('id')]
    except Exception: ids=[]
    ensure_agents(ids); print(f'ACCOUNT REGISTRY: {len(load()["accounts"])} agent account profiles ready; credentials are external secrets.')
