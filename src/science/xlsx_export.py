"""Small, portable typed CSV -> XLSX writer (Python standard library only)."""
from pathlib import Path
import csv,math,re,zipfile
import xml.etree.ElementTree as ET
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
RNS='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
Q=lambda n:'{'+NS+'}'+n
def xml_bytes(element,namespace):
    ET.register_namespace('',namespace)
    return ET.tostring(element,encoding='utf-8',xml_declaration=True)
def letter(n):
    s=''
    while n:n,r=divmod(n-1,26);s=chr(65+r)+s
    return s
def read_csv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f:rows=list(csv.reader(f))
    headers=rows[0];types=[]
    for j in range(len(headers)):
        values=[r[j] for r in rows[1:] if r[j]!='']
        numeric=bool(values) and all(re.fullmatch(r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?',x) for x in values)
        # Scientific identifiers/dates remain text even if digit-only.
        if headers[j].lower() in ['month','source_row_key','sample_hash','sha256']:numeric=False
        types.append(numeric)
    converted=[headers]
    for row in rows[1:]:
        converted.append([None if v=='' else float(v) if types[j] else v for j,v in enumerate(row)])
    return converted
def write_workbook(sheets,output):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    workbook=ET.Element(Q('workbook'));sheetlist=ET.SubElement(workbook,Q('sheets'))
    relns='http://schemas.openxmlformats.org/package/2006/relationships'
    rels=ET.Element('{'+relns+'}Relationships')
    contentns='http://schemas.openxmlformats.org/package/2006/content-types'
    content=ET.Element('{'+contentns+'}Types')
    for ext,typ in [('rels','application/vnd.openxmlformats-package.relationships+xml'),('xml','application/xml')]:ET.SubElement(content,'{'+contentns+'}Default',Extension=ext,ContentType=typ)
    parts={}
    def override(name,kind):ET.SubElement(content,'{'+contentns+'}Override',PartName='/'+name,ContentType='application/vnd.openxmlformats-officedocument.spreadsheetml.'+kind+'+xml')
    for i,(name,data) in enumerate(sheets,1):
        ET.SubElement(sheetlist,Q('sheet'),name=name,sheetId=str(i),attrib={'{'+RNS+'}id':f'rId{i}'})
        ET.SubElement(rels,'{'+relns+'}Relationship',Id=f'rId{i}',Type=RNS+'/worksheet',Target=f'worksheets/sheet{i}.xml')
        sheet=ET.Element(Q('worksheet'));views=ET.SubElement(sheet,Q('sheetViews'));view=ET.SubElement(views,Q('sheetView'),workbookViewId='0',showGridLines='0')
        ET.SubElement(view,Q('pane'),ySplit='1',topLeftCell='A2',activePane='bottomLeft',state='frozen')
        cols=ET.SubElement(sheet,Q('cols'))
        widths=[]
        for j in range(len(data[0])):
            width=min(48,max(12,max(len(str(r[j] or '')) for r in data[:40])+2))
            widths.append(width)
            ET.SubElement(cols,Q('col'),min=str(j+1),max=str(j+1),width=str(width),customWidth='1')
        sd=ET.SubElement(sheet,Q('sheetData'))
        for r,row in enumerate(data,1):
            lines=max(math.ceil(len(str(v or ''))/max(1,widths[j]-3)) for j,v in enumerate(row))
            rd=ET.SubElement(sd,Q('row'),r=str(r),ht=str(max(32 if r==1 else 26,lines*15+10)),customHeight='1')
            for j,value in enumerate(row,1):
                if value is None:continue
                c=ET.SubElement(rd,Q('c'),r=letter(j)+str(r),s='1' if r==1 else ('2' if isinstance(value,(int,float)) else '0'))
                if isinstance(value,(int,float)):
                    if not math.isfinite(value):raise ValueError('Nonfinite numeric export')
                    ET.SubElement(c,Q('v')).text=repr(value)
                else:
                    c.set('t','inlineStr');ET.SubElement(ET.SubElement(c,Q('is')),Q('t')).text=str(value)
        ET.SubElement(sheet,Q('autoFilter'),ref=f'A1:{letter(len(data[0]))}{len(data)}')
        part=f'xl/worksheets/sheet{i}.xml';parts[part]=xml_bytes(sheet,NS);override(part,'worksheet')
    ET.SubElement(rels,'{'+relns+'}Relationship',Id='styles',Type=RNS+'/styles',Target='styles.xml')
    parts['xl/styles.xml']=f'''<styleSheet xmlns="{NS}"><fonts count="2"><font><sz val="10"/><name val="Arial"/></font><font><b/><sz val="10"/><color rgb="FFFFFFFF"/><name val="Arial"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF31485C"/></patternFill></fill></fills><borders count="1"><border/></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0"><alignment horizontal="center" vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment horizontal="right" vertical="center"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles></styleSheet>'''.encode()
    override('xl/styles.xml','styles');override('xl/workbook.xml','sheet.main')
    parts['xl/workbook.xml']=xml_bytes(workbook,NS);parts['xl/_rels/workbook.xml.rels']=xml_bytes(rels,relns)
    parts['[Content_Types].xml']=xml_bytes(content,contentns)
    parts['_rels/.rels']=f'<Relationships xmlns="{relns}"><Relationship Id="rId1" Type="{RNS}/officeDocument" Target="xl/workbook.xml"/></Relationships>'.encode()
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED) as z:
        for name,content in parts.items():z.writestr(name,content)
    return output
