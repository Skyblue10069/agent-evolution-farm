"""Game-playing AI layer for Agent Evolution.

Learns from screenshots/state observations and outcomes. It does not bypass
anti-cheat, CAPTCHAs, DRM, or game security controls.
"""
from __future__ import annotations
import json, math, time, hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / 'game_ai_state.json'
POLICY_FILE = ROOT / 'game_ai_policy.json'
DEFAULT_POLICY = {
    'enabled': True,
    'max_actions_per_episode': 300,
    'max_episode_seconds': 900,
    'learning_rate': 0.15,
    'exploration': 0.12,
    'allowed_action_types': ['tap','swipe','back','wait'],
    'forbidden_targets': ['captcha','password','security_challenge'],
}

def load(path, default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return dict(default)

def save(path, data):
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')

class GameLearningAgent:
    def __init__(self, agent_id='unknown'):
        self.agent_id = agent_id
        self.policy = {**DEFAULT_POLICY, **load(POLICY_FILE, DEFAULT_POLICY)}
        self.state = load(STATE_FILE, {'agents': {}})
        self.data = self.state.setdefault('agents', {}).setdefault(agent_id, {
            'games': {}, 'episodes': 0, 'wins': 0, 'losses': 0,
            'total_reward': 0.0, 'skills': {'vision':0.0,'timing':0.0,'planning':0.0,'control':0.0},
            'q': {}, 'lessons': []
        })
        self.started = time.time(); self.actions = 0

    def _key(self, observation, action):
        raw = json.dumps({'o': observation, 'a': action}, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def choose_action(self, observation, candidates):
        """Pick among actions supplied by the game adapter/vision layer."""
        import random
        if not candidates: return {'type':'wait','seconds':0.3}
        if self.actions >= self.policy['max_actions_per_episode'] or time.time()-self.started >= self.policy['max_episode_seconds']:
            return {'type':'wait','seconds':0.1,'stop_episode':True}
        if random.random() < float(self.policy['exploration']):
            action = random.choice(candidates)
        else:
            scored = [(self.data['q'].get(self._key(observation,a),0.0), a) for a in candidates]
            action = max(scored, key=lambda x:x[0])[1]
        if action.get('type') not in self.policy['allowed_action_types']:
            return {'type':'wait','seconds':0.2}
        self.actions += 1
        return action

    def learn(self, observation, action, reward, next_observation=None, terminal=False):
        key = self._key(observation, action)
        old = float(self.data['q'].get(key, 0.0))
        future = 0.0 if terminal else max(self.data['q'].values(), default=0.0)
        lr = float(self.policy['learning_rate'])
        self.data['q'][key] = old + lr * (float(reward) + 0.85*future - old)
        self.data['total_reward'] += float(reward)
        if reward > 0: self.data['skills']['control'] = min(100.0, self.data['skills']['control'] + 0.02)
        if reward < 0: self.data['skills']['planning'] = min(100.0, self.data['skills']['planning'] + 0.03)
        if terminal: self.finish(reward > 0)
        save(STATE_FILE, self.state)

    def finish(self, won):
        self.data['episodes'] += 1
        self.data['wins' if won else 'losses'] += 1
        self.data['lessons'].append({'ts':time.time(),'won':bool(won),'actions':self.actions})
        self.data['lessons'] = self.data['lessons'][-500:]
        save(STATE_FILE, self.state)

if __name__ == '__main__':
    print(json.dumps({'game_ai':'ready','learning':'enabled','agent_scoped_memory':True}, indent=2))
