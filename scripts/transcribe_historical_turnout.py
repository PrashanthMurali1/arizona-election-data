"""Rebuild official election-wide turnout for the five historical state elections."""
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalize import COUNTIES, URLS

def transcribe(year):
    source = ROOT / f'data/raw/historical-statewide/{year}-turnout-indexed-canvass.txt'
    text = re.sub(r'L\d+(?:@P[\d-]+)?: ', '', source.read_text(encoding='utf-8'))
    labels = ['TOTAL REGISTRATION','TOTAL BALLOTS CAST','PERCENT TOTAL VOTES CAST'] if year==1994 else ['Total Eligible Registration','Total Ballots Cast','Total Voter Turnout Percent']
    values=[]
    for i,label in enumerate(labels):
        if year in (1994,2006):
            block=text.split('<td>'+label+'</td>',1)[1].split('</tr>',1)[0]
            cells=re.findall(r'<td>(.*?)</td>',block)
        elif year in (1998,2002):
            block=text.split(label,1)[1].split(labels[i+1] if i<2 else 'PRECINCTS',1)[0]
            cells=block.split()
            # These text extracts list the statewide TOTAL before county cells.
            cells=cells[1:]+cells[:1]
        else:
            block=text.split(label,1)[1].split(labels[i+1] if i<2 else 'PRECINCTS',1)[0]
            cells=block.split()
        if len(cells)!=16: raise ValueError((year,label,'Expected fifteen counties and a statewide total',len(cells)))
        values.append([float(c) if i==2 else int(c.replace(',','')) for c in cells])
    output=ROOT/f'data/raw/{year}-turnout-transcription.csv'
    with output.open('w',encoding='utf-8',newline='') as f:
        writer=csv.writer(f,lineterminator='\n')
        writer.writerow(['geoid','registered_voters','ballots_cast','percent'])
        for i,geoid in enumerate([g for g,_ in COUNTIES]+['04']):
            writer.writerow([geoid,values[0][i],values[1][i],f'{values[2][i]:.2f}'])
    provenance={'source_url':URLS[year],'page':1,'retrieved_date':'2026-10-31',
        'definition':'Official election-wide ballots cast, eligible registration and turnout percentage as published. Shared by Governor and Attorney General.',
        'source_excerpt':source.relative_to(ROOT).as_posix(),'source_excerpt_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'transcription_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}
    (ROOT/f'data/raw/historical-statewide/{year}-turnout-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    print(year,'turnout retained for 15 counties and statewide:',values[2][-1])

if __name__=='__main__':
    for year in (1994,1998,2002,2006,2010):transcribe(year)
