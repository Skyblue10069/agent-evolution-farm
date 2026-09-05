"""Full autonomous cycle: worldwide discovery -> independent brains -> competition -> business evolution.
External submissions and money use remain owner/provider gated.
"""
import subprocess,sys
from pathlib import Path
ROOT=Path(__file__).parent

def run(script,*args):
    cmd=[sys.executable,str(ROOT/script),*args]
    print('\n>>>',' '.join(cmd))
    return subprocess.run(cmd,cwd=ROOT,check=False).returncode

def main():
    run('worldwide_discovery.py','--max-results','6','--max-opportunities','1000')
    run('autonomous_brain.py')
    run('work_preparer.py','--limit','500')
    run('business_factory.py')
    run('business_evolution.py')
    run('payout_router.py')
    print('FULL AUTONOMOUS CYCLE COMPLETE: discovery + brain + competition + business evolution.')
if __name__=='__main__':main()
