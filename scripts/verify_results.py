"""Read-only integrity and scientific-policy checks. No estimation or resampling."""
from pathlib import Path
import ast,csv,hashlib,json,re,sys,zipfile
from urllib.parse import unquote
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
SELF={'validation/checksums/files.json','metadata/public_file_manifest.csv'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def csvrows(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def verify():
 failures=[];checks={}
 index=json.loads((ROOT/'validation/checksums/files.json').read_text(encoding='utf-8'))
 actual={p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts}
 expected={r['target_path'] for r in index}|SELF
 if actual!=expected:failures.append({'inventory_missing':sorted(expected-actual),'inventory_extra':sorted(actual-expected)})
 for r in index:
  p=ROOT/r['target_path']
  if not p.is_file() or sha(p)!=r['target_sha256'] or p.stat().st_size!=r['size_bytes']:failures.append({'hash_mismatch':r['target_path']})
 checks['hashed_payload_files']=len(index)
 # Explicit self-reference boundary: these two indexes have no self-hash.
 checks['unhashed_index_files']=sorted(SELF)
 links=0
 for p in ROOT.rglob('*.md'):
  for link in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
   link=link.strip('<>');target=link.split('#')[0]
   if not target or re.match(r'^[a-z]+:',target):continue
   q=(p.parent/unquote(target)).resolve();links+=1
   if not q.is_relative_to(ROOT) or not q.exists():failures.append({'broken_link':p.relative_to(ROOT).as_posix(),'target':link})
 checks['relative_links_checked']=links
 mapping=csvrows(ROOT/'metadata/manuscript_to_files.csv')
 expected_items=[f'Figure {n}' for n in range(1,8)]+[f'Table {n}' for n in range(1,7)]+[f'S{n} Table' for n in range(1,19)]+[f'S{n} Fig' for n in range(1,4)]
 if [r['item'] for r in mapping]!=expected_items:failures.append({'item_matrix':'expected34 ordered unique items'})
 checks['manuscript_logical_items']=len(mapping)
 ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'};si=ROOT/'journal_submission';formula_count=0;formula_missing_cache=0;si_count=0
 for n in range(1,19):
  p=si/f'S{n} Table.xlsx'
  with zipfile.ZipFile(p) as z:
   if z.testzip():failures.append({'zip_crc':p.name})
   sheets=ET.fromstring(z.read('xl/workbook.xml')).findall('s:sheets/s:sheet',ns)
   if n in (3,18) and len(sheets)!=(5 if n==3 else 8):failures.append({'si_sheets':p.name})
   for name in z.namelist():
    if name.startswith('xl/worksheets/') and name.endswith('.xml'):
     for c in ET.fromstring(z.read(name)).findall('.//s:c',ns):
      if c.find('s:f',ns) is not None:
       formula_count+=1
       if c.find('s:v',ns) is None:formula_missing_cache+=1
  si_count+=1
 for n in (1,2,3):
  p=si/f'S{n} Fig.tif';header=p.read_bytes()[:4]
  if header not in (b'II*\x00',b'MM\x00*'):failures.append({'tiff_header':p.name})
  si_count+=1
 if len(list(si.iterdir()))!=21:failures.append({'journal_directory':'expected21 attachments only'})
 if formula_count!=762 or formula_missing_cache:failures.append({'SI_formulas':formula_count,'missing_cache':formula_missing_cache})
 checks.update(journal_files=si_count,SI_formula_count=formula_count,SI_formula_caches_present=formula_missing_cache==0)
 primary=[r for r in csvrows(ROOT/'reference/statistics/lp_final_coefficients.csv') if r.get('group')=='PRIMARY' or str(r.get('model','')).startswith('PRIMARY_')]
 if len(primary)!=39:failures.append({'primary_frozen_rows':len(primary)})
 for r in primary:
  h=int(float(r['horizon']))
  if int(float(r['N']))!=335-h or int(float(r['maxlags']))!=max(12,h+1):failures.append({'primary_sample_HAC':r['model'],'h':h})
 checks['frozen_primary_rows']=len(primary)
 ic=csvrows(ROOT/'reference/s18/S1/lp_lag_information_criteria.csv')
 design_keys={(r['outcome'],r['horizon'],r['p']) for r in ic}
 if len(design_keys)!=195:failures.append({'S18_unique_designs':len(design_keys)})
 checks['S18_frozen_designs']=len(design_keys)
 checks['S18_IC_rows_including_three_criteria']=len(ic)
 for p in ROOT.rglob('*.py'):
  try:ast.parse(p.read_text(encoding='utf-8-sig'))
  except SyntaxError as e:failures.append({'syntax':p.relative_to(ROOT).as_posix(),'error':str(e)})
  if p.is_symlink():failures.append({'symlink':str(p)})
 checks['python_files_parsed']=len(list(ROOT.rglob('*.py')))
 status=json.loads((ROOT/'RELEASE_STATUS.json').read_text(encoding='utf-8'))
 return {'integrity_status':'PASS' if not failures else 'FAIL','checks':checks,'failures':failures,'release_status':status['status'],'release_blockers':status.get('remaining_gates',[]),'new_statistical_estimation':False,'new_bootstrap_or_DWB':False}
if __name__=='__main__':
 result=verify();print(json.dumps(result,indent=2));sys.exit(0 if result['integrity_status']=='PASS' else 1)
