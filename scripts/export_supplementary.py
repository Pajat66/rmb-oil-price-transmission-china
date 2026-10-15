"""Copy the frozen 21 journal attachments to a new external directory; no recalculation."""
from pathlib import Path
import argparse,shutil,json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True);a=p.parse_args()
 out=a.output_dir.expanduser().resolve()
 if out==ROOT or out.is_relative_to(ROOT):p.error('Output must be outside this candidate')
 if out.exists():p.error('Use a new, nonexistent output directory')
 from verify_results import verify
 result=verify()
 if result['integrity_status']!='PASS':raise RuntimeError('Candidate integrity failed')
 out.mkdir(parents=True);records=[]
 for src in sorted((ROOT/'journal_submission').iterdir()):
  dst=out/src.name;shutil.copy2(src,dst)
  assert dst.read_bytes()==src.read_bytes()
  records.append({'filename':src.name,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()})
 print(json.dumps({'status':'FROZEN_COPY_PASS','files':len(records),'new_estimation':False,'records':records},indent=2))
if __name__=='__main__':main()
