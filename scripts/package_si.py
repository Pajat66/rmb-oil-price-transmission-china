"""Lossless workbook package selection; never estimates or rewrites sheet cells."""
from pathlib import Path
import argparse,json,zipfile,posixpath,hashlib,re,copy
from lxml import etree
S='http://schemas.openxmlformats.org/spreadsheetml/2006/main';REL='http://schemas.openxmlformats.org/package/2006/relationships';R='http://schemas.openxmlformats.org/officeDocument/2006/relationships';CT='http://schemas.openxmlformats.org/package/2006/content-types'
def hashbytes(b):return hashlib.sha256(b).hexdigest()
def xml(b):return etree.fromstring(b,etree.XMLParser(resolve_entities=False,no_network=True))
def serialize(x):return etree.tostring(x,encoding='UTF-8',xml_declaration=True)
def relpart(owner):return '_rels/.rels' if not owner else posixpath.dirname(owner)+'/_rels/'+posixpath.basename(owner)+'.rels'
def target(owner,t):return posixpath.normpath(posixpath.join(posixpath.dirname(owner),t)).lstrip('/')
def subset(source,destination,names):
 source=Path(source);destination=Path(destination)
 if destination.exists():raise FileExistsError(destination)
 with zipfile.ZipFile(source) as z:
  parts={n:z.read(n) for n in z.namelist() if not n.endswith('/')}; infos={i.filename:i for i in z.infolist()}
 root=xml(parts['xl/workbook.xml']);all_sheets=list(root.find('{'+S+'}sheets'));found=[x.get('name') for x in all_sheets]
 if len(set(names))!=len(names) or not set(names)<=set(found):raise ValueError('Missing or repeated sheet selection')
 # Retain original ordering; grouping is based on explicit names, not positions.
 selected=[x for x in all_sheets if x.get('name') in names]
 if [x.get('name') for x in selected]!=names:raise ValueError('Requested order differs from source order')
 selected_ids={x.get('{'+R+'}id') for x in selected};rels=xml(parts['xl/_rels/workbook.xml.rels']);sidmap={x.get('Id'):target('xl/workbook.xml',x.get('Target')) for x in rels}
 selected_parts={sidmap[x.get('{'+R+'}id')] for x in selected};kept_names=set(names)
 for p in selected_parts:
  rt=xml(parts[p])
  for formula in rt.findall('.//{'+S+'}f'):
   # The present source has no formulas. Fail conservatively for unreviewed cross-sheet logic.
   if '!' in (formula.text or '') or '[' in (formula.text or ''):raise ValueError('Unresolved cross-sheet or external formula in '+p)
 if 'xl/calcChain.xml' in parts:raise ValueError('Calc chain requires explicit remapping')
 parent=root.find('{'+S+'}sheets')
 for sh in all_sheets:
  if sh not in selected:parent.remove(sh)
 old_to_new={found.index(x.get('name')):i for i,x in enumerate(selected)}
 defined=root.find('{'+S+'}definedNames')
 if defined is not None:
  for d in list(defined):
   idx=d.get('localSheetId')
   if idx is not None:
    if int(idx) not in old_to_new:defined.remove(d);continue
    d.set('localSheetId',str(old_to_new[int(idx)]))
   text=d.text or ''
   for omitted in set(found)-kept_names:
    if ("'"+omitted.replace("'","''")+"'!") in text or (omitted+'!') in text:raise ValueError('Defined name depends on omitted sheet')
 views=root.find('{'+S+'}bookViews')
 if views is not None:
  for view in views:
   if view.get('activeTab') is not None:view.set('activeTab','0')
   if view.get('firstSheet') is not None:view.set('firstSheet','0')
 for rel in list(rels):
  if rel.get('Type','').endswith('/worksheet') and rel.get('Id') not in selected_ids:rels.remove(rel)
 parts['xl/workbook.xml']=serialize(root);parts['xl/_rels/workbook.xml.rels']=serialize(rels)
 # Follow all retained internal relationships; omit unreachable other worksheets/table parts.
 reachable=set();pending=['']
 while pending:
  owner=pending.pop();rp=relpart(owner)
  if owner:reachable.add(owner)
  if rp in parts:
   reachable.add(rp)
   for rel in xml(parts[rp]):
    if rel.get('TargetMode')=='External':continue
    p=target(owner,rel.get('Target'))
    if p not in parts:raise ValueError('Missing relationship '+p)
    if p not in reachable:pending.append(p)
 reachable.add('[Content_Types].xml')
 types=xml(parts['[Content_Types].xml'])
 for e in list(types):
  if e.tag=='{'+CT+'}Override' and e.get('PartName','').lstrip('/') not in reachable:types.remove(e)
 parts['[Content_Types].xml']=serialize(types)
 # App properties listing sheet names is metadata, not cell content.
 if 'docProps/app.xml' in reachable:
  app=xml(parts['docProps/app.xml']);A=etree.QName(app).namespace;VT='http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
  titles=app.find('{'+A+'}TitlesOfParts')
  if titles is not None:
   vector=titles.find('{'+VT+'}vector')
   if vector is not None:
    for e in list(vector):vector.remove(e)
    vector.set('size',str(len(names)))
    for n in names:etree.SubElement(vector,'{'+VT+'}lpstr').text=n
  hp=app.find('{'+A+'}HeadingPairs')
  if hp is not None:
   children=list(hp.iter('{'+VT+'}i4'))
   if len(children)==1:children[0].text=str(len(names))
   elif children:raise ValueError('Complex app heading metadata requires review')
  parts['docProps/app.xml']=serialize(app)
 destination.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(destination,'w') as out:
  for p in infos:
   if p in reachable:out.writestr(infos[p],parts[p])
 with zipfile.ZipFile(source) as original,zipfile.ZipFile(destination) as derived:
  sheetproof={p:hashbytes(original.read(p))==hashbytes(derived.read(p)) for p in selected_parts}
  protected=[p for p in reachable if p.startswith(('xl/styles','xl/sharedStrings','xl/theme')) or p.startswith('xl/worksheets/') or p.startswith('xl/tables/')]
  protected_proof={p:hashbytes(original.read(p))==hashbytes(derived.read(p)) for p in protected}
  if not all(sheetproof.values()) or not all(protected_proof.values()):raise ValueError('Protected sheet/style/table part changed')
  if derived.testzip():raise ValueError('Output ZIP CRC failed')
 return {'source_sha256':hashbytes(source.read_bytes()),'target_sha256':hashbytes(destination.read_bytes()),'sheets':names,'sheet_xml_byte_identical':sheetproof,'protected_parts_byte_identical':protected_proof,'retained_parts':len(reachable),'changed_metadata_parts':['xl/workbook.xml','xl/_rels/workbook.xml.rels','[Content_Types].xml','docProps/app.xml']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--sheets-json',required=True);args=p.parse_args();print(json.dumps(subset(args.source,args.destination,json.loads(args.sheets_json)),ensure_ascii=False))
if __name__=='__main__':main()
