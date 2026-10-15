"""Portable plan and opt-in scientific entry. Full reproduction remains unverified."""
from pathlib import Path
import argparse,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('command',choices=['plan','verify','prepare-data','main-lp','stability','s15','full'])
 p.add_argument('--allow-computation',action='store_true')
 a,rest=p.parse_known_args()
 if a.command=='plan':print((ROOT/'config/execution_plan.json').read_text(encoding='utf-8'));return
 if a.command=='verify':
  from verify_results import verify
  result=verify();print(json.dumps(result,indent=2));sys.exit(0 if result['integrity_status']=='PASS' else 1)
 if not a.allow_computation:p.error('Numerical commands require --allow-computation after lawful data access and separate execution authorization. R4A did not execute these commands.')
 if '--r3-authorized' not in rest:rest.append('--r3-authorized')
 subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'scripts/reproduce.py'),a.command,*rest],check=True)
if __name__=='__main__':main()
