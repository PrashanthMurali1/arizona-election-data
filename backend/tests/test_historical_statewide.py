"""Historical coverage, complete rosters, and independently published totals."""
import json
from pathlib import Path
import pytest
import os
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]

def test_reviewed_difference_does_not_hide_other_source_errors():
    import copy
    from scripts.import_data import reconcile
    data = json.loads((ROOT / 'data/processed/1994.json').read_text(encoding='utf-8'))
    assert reconcile(data)['status'] == 'verified' and 'reviewed_county_differences' not in data
    bad = copy.deepcopy(data)
    bad['candidates'][0]['county_votes']['04001'] += 1
    assert reconcile(bad)['status'] == 'incomplete'
    # The one-vote Crawford difference was a transcription omission (Yavapai 1); losing that cell must fail again.
    bad = copy.deepcopy(data)
    crawford = next(c for c in bad['candidates'] if 'CRAWFORD' in c['name'])
    crawford['county_votes']['04025'] -= 1
    assert reconcile(bad)['status'] == 'incomplete'

@pytest.mark.parametrize('year', [1994, 1998, 2002, 2006, 2010])
@pytest.mark.parametrize('office', ['governor', 'attorney-general'])
def test_historical_coverage(year, office):
    from scripts.import_data import reconcile
    path = ROOT / 'data/processed' / (f'{year}.json' if office == 'governor' else f'attorney-general/{year}.json')
    data = json.loads(path.read_text(encoding='utf-8'))
    if office == 'attorney-general':
        assert '\\' not in data['reference_path']
    reference = ROOT / data.get('reference_path', f'data/raw/{year}-governor-transcription.csv')
    report = reconcile(data, reference)
    assert report['status'] == 'verified'
    assert all(c['difference'] == 0 for c in report['candidates'])
    assert report['complete_county_count'] == 15
    expected = {'governor': {1994:10,1998:7,2002:10,2006:6,2010:7}, 'attorney-general':{1994:2,1998:3,2002:3,2006:2,2010:2}}
    assert len(data['candidates']) == expected[office][year]

@pytest.fixture
def preserve_report():
    path = ROOT / 'data/processed/reconciliation.json'
    original = path.read_bytes()
    yield
    path.write_bytes(original)

def test_historical_import_api_and_repeatability(tmp_path, preserve_report):
    env = {**os.environ, 'DATABASE_URL': 'sqlite:///' + str(tmp_path / 'history.db'), 'PYTHONUTF8':'1'}
    def run(*args):
        result = subprocess.run([sys.executable, '-X', 'utf8', *args], cwd=ROOT, env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout[-2000:] + result.stderr[-2000:]
    run('-m','alembic','-c','backend/alembic.ini','upgrade','head')
    for office in ('governor','attorney-general'):
        run('scripts/import_data.py','--office',office,'--year','2014')
    # Validate the API and compare existing records across two complete imports.
    run('-c', '''
import json, subprocess, sys
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.database import engine
with TestClient(app) as client:
    paths = ['/api/elections/az-2014-'+o for o in ['governor','attorney-general']]
    before = [client.get(p).json() for p in paths]
    for repeat in range(2):
        for office in ['governor','attorney-general']:
            subprocess.run([sys.executable,'-X','utf8','scripts/import_data.py','--office',office],check=True,stdout=subprocess.DEVNULL)
        assert [client.get(p).json() for p in paths] == before
        for year in [1994,1998,2002,2006,2010]:
            for office in ['governor','attorney-general']:
                base=f'/api/elections/az-{year}-{office}'
                response=client.get(base)
                assert response.status_code==200, response.text
                discrepancy = False
                assert response.json()['election']['status']=='verified'
                rows=client.get(base+'/counties').json()
                assert len(rows)==15
                assert sum(r['total_votes'] for r in rows)==response.json()['statewide']['total_votes']-(1 if discrepancy else 0)
                if year==1994 and office=='governor':
                    state=response.json()['statewide']
                    crawford=next(c for c in state['candidates'] if 'CRAWFORD' in c['name'])
                    assert crawford['votes']==11 and crawford['percent'] is not None
                    assert state['total_votes']==1129607
                    assert state['turnout']['percent']==55.59
                    assert state['turnout']['ballots_cast']==1153724
                expected_turnout={1994:(55.59,1153724,2075322),1998:(45.82,1037550,2264301),2002:(56.33,1255615,2229180),2006:(60.47,1553032,2568401),2010:(55.65,1750840,3146418)}
                turnout=response.json()['statewide']['turnout']
                assert (turnout['percent'],turnout['ballots_cast'],turnout['registered_voters'])==expected_turnout[year]
                assert all(r['turnout']['percent'] is not None and r['turnout']['ballots_cast'] is not None and r['turnout']['registered_voters'] is not None for r in rows)
engine.dispose()
''')
