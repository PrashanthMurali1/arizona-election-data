"""Rebuild historical CSV transcriptions from retained indexed canvass excerpts.

This is a reviewed, layout-specific adapter, not a general PDF/OCR parser.
Binary downloads were denied; provenance explicitly records indexed acquisition.
"""
import csv
import hashlib
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES

RAW = ROOT / 'data/raw/historical-statewide'
DATES = {1994:'1994-11-08',1998:'1998-11-03',2002:'2002-11-05',2006:'2006-11-07',2010:'2010-11-02'}
URLS = {y: f'https://apps.azsos.gov/election/{y}/General/Canvass{y}GE.pdf' for y in DATES}
URLS[1994] = 'https://apps.azsos.gov/election/files/hist/canvass1994ge.pdf'

def clean(text):
    return re.sub(r'L\d+(?:@P[\d-]+)?: ', '', text)

def rows_from_block(block):
    block = block.split('* Elected')[0]
    if '<td>' in block:
        rows = [re.findall(r'<td>(.*?)</td>', r, re.S) for r in re.findall(r'<tr>(.*?)</tr>',block,re.S)]
        return [r for r in rows if len(r)==17 and r[0].startswith('(')]
    if '| Candidate |' in block:
        return [[v.strip() for v in line.strip().strip('|').split('|')] for line in block.splitlines() if line.startswith('| (')]
    # Known 1998/2002 indexed text concatenates single-digit county cells.
    # Expand only exact reviewed strings; do not guess at arbitrary merged OCR.
    for merged in ['201000080103000','100010090100000','010000040000000','000000020021000','001100070212001','000000000010000','010000000030000']:
        block = block.replace(merged, ' '.join(merged))
    pattern = r'\((DEM|REP|LBT|IND|RPA|NONE|GRN|Write-In)\)\s*(.*?)\s+((?:[\d,]+\s+){15}[\d,]+)(?=\(|\s*$)'
    return [[f'({party}) {name}',*nums.split()] for party,name,nums in re.findall(pattern,block,re.S)]

def main():
    more = clean((RAW/'contest-excerpts.txt').read_text(encoding='utf-8')).split('--------------------------------------------------------------------------------')
    ag = clean((RAW/'1998-2002-2010-indexed-canvass.txt').read_text(encoding='utf-8')).split('--------------------------------------------------------------------------------')
    old = clean((RAW/'1994-indexed-canvass.txt').read_text(encoding='utf-8'))
    manifest=[]
    for year in DATES:
        for office, heading, end in [('governor','GOVERNOR','STATE SENATOR'),('attorney-general','ATTORNEY GENERAL','STATE TREASURER')]:
            if year==1994:
                block=old.split(f'<td>{heading}</td>',1)[1].split('<td>SECRETARY OF STATE</td>' if office=='governor' else '<td>STATE TREASURER</td>',1)[0]
            else:
                text = more[{1998:0,2002:1,2010:2,2006:3}[year]] if office=='governor' else (more[4] if year==2006 else ag[{1998:0,2002:1,2010:2}[year]])
                block=text.split(heading,1)[1].split(end,1)[0]
            rows=rows_from_block(block)
            expected={'governor':{1994:10,1998:7,2002:10,2006:6,2010:7},'attorney-general':{1994:2,1998:3,2002:3,2006:2,2010:2}}[office][year]
            if len(rows)!=expected:raise ValueError((year,office,len(rows),expected))
            path=ROOT/'data/raw'/ (f'{year}-governor-transcription.csv' if office=='governor' else f'attorney-general/{year}-transcription.csv')
            with path.open('w',encoding='utf-8',newline='') as f:
                writer=csv.writer(f, lineterminator='\n' if office=='governor' else '\r\n');writer.writerow(['party','name','write_in',*[c[0] for c in COUNTIES],'official_statewide'])
                for row in rows:
                    label=html.unescape(' '.join(row[0].split()))
                    party,name=re.match(r'\((.*?)\)\s*(.*)',label).groups()
                    party={'D':'DEM','R':'REP','L':'LBT','I':'IND','N':'NONE','Write-In':'NONE'}.get(party,party)
                    write='write-in' in label.lower()
                    name=re.sub(r'\s*\(Write-[Ii]n\)','',name).replace('*','').strip()
                    votes=[int(v.replace(',','')) for v in row[1:]]
                    if sum(votes[:15])!=votes[15]:
                        print('UNRESOLVED:',year,name,'county sum',sum(votes[:15]),'published total',votes[15])
                    writer.writerow([party,name,str(write).lower(),*votes])
            provenance={'year':year,'office_id':office,'date':DATES[year],'source_url':URLS[year],
                'retrieved_date':'2026-10-31','source_pdf_sha256':None,'reviewed_transcription':path.relative_to(ROOT).as_posix(),
                'transcription_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'notes':'Transcribed from indexed official canvass tables. Direct PDF downloads returned HTTP 403; no original binary retained. Known merged single-digit rows expanded explicitly; all county sums checked against separately published TOTAL. Party labels D/R/L/I/N mapped to DEM/REP/LBT/IND/NONE; Write-In label means no reported party affiliation.',
                'indexed_excerpts':[{ 'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(RAW.glob('*.txt'))]}
            prov=path.with_name(f'{year}-provenance.json') if office=='attorney-general' else RAW/f'{year}-governor-provenance.json'
            prov.write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
            manifest.append(provenance)
            print(year,office,len(rows))
    (RAW/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
