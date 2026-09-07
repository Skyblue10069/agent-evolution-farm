"""Dynamic team formation and delegation signals.

Teams are internal planning structures only. They do not fabricate customers,
contracts, revenue or external identities.
"""
import random

def run(s):
    teams=s.setdefault('teams',{'teams':[],'events':[]})
    alive=[a for a in s.get('agents',[]) if a.get('permanent_status')=='alive']
    leaders=[a for a in alive if float(a.get('skills',{}).get('leadership',0))>=20 or float(a.get('skills',{}).get('delegation',0))>=20]
    rng=random.Random(f"teams:{s.get('day',0)}")
    for leader in leaders[:500]:
        h=leader.setdefault('hierarchy',{})
        if h.get('team_interest') is False: continue
        members=[a for a in alive if a.get('id')!=leader.get('id') and a.get('hierarchy',{}).get('parent_id')==leader.get('id')][:5]
        if not members: continue
        team_id=f"team-{leader['id']}-{s.get('day',0)}"
        if any(t.get('id')==team_id for t in teams['teams']): continue
        teams['teams'].append({'id':team_id,'leader_id':leader['id'],'member_ids':[x['id'] for x in members],
                               'created_day':s.get('day',0),'status':'active','goal':'internal task coordination'})
        leader.setdefault('brain',{}).setdefault('lessons',[]).append({'day':s.get('day',0),'source':'team_formation','members':len(members)})
    teams['teams']=teams['teams'][-1000:]
    teams['events'].append({'day':s.get('day',0),'active_teams':len(teams['teams'])})
    teams['events']=teams['events'][-100:]
