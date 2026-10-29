import asyncio
import json
from unittest.mock import Mock
import pytest
from backend.app.relay_metrics import Recorder,RequestMetrics

def test_asgi_instrumentation_excludes_health_streams_and_never_persists_payloads(tmp_path):
    recorder=Recorder(tmp_path)
    async def downstream(scope,receive,send):
        if scope['path']=='/api/fail':raise RuntimeError('PRIVATE_SENTINEL')
        await send({'type':'http.response.start','status':404 if scope['path']=='/api/missing' else 200,
          'headers':[(b'content-type',b'text/event-stream' if scope['path']=='/api/updates' else b'application/json')]})
        await send({'type':'http.response.body','body':b'PRIVATE_SENTINEL'})
    app=RequestMetrics(downstream,recorder)
    async def run(path):
        async def send(message):pass
        await app({'type':'http','path':path,'query_string':b'token=PRIVATE_SENTINEL'},None,send)
    for path in ('/api/health','/api/updates','/','/api/data','/api/missing'):asyncio.run(run(path))
    with pytest.raises(RuntimeError):asyncio.run(run('/api/fail'))
    value=recorder.snapshot();assert value['requests']==3 and value['errors']==1 and value['client_errors']==1
    recorder.flush();raw=next(tmp_path.glob('*.json')).read_text();assert 'PRIVATE_SENTINEL' not in raw and '/api/' not in raw
    assert sum(value['histogram'])==3
    recorder.folder=tmp_path/'blocked';recorder.folder.write_text('file');recorder.flush()
    # A broken instrumentation observer must not break successful HTTP handling.
    recorder.observe=Mock(side_effect=OSError('SECRET'));asyncio.run(run('/api/data'))
