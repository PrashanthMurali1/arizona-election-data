"""Standalone numeric ASGI instrumentation; also installed in the election app.

No request/response content, headers, URLs, route labels, or exception details
are retained. Completed API requests only; SSE and health checks are excluded.
"""
import bisect
import json
import os
from pathlib import Path
import threading
import time
from uuid import uuid4

BOUNDS=[1,2,5,10,20,50,100,200,500,1000,2000,5000,10000,30000,120000]

class Recorder:
    def __init__(self,folder):
        self.folder=Path(folder);self.identity=uuid4().hex;self.lock=threading.Lock()
        self.requests=0;self.errors=0;self.client_errors=0;self.histogram=[0]*16
        self.stop=threading.Event();self.thread=None
    def observe(self,duration_ms,status):
        with self.lock:
            self.requests+=1;self.errors+=int(status>=500);self.client_errors+=int(400<=status<500)
            self.histogram[bisect.bisect_left(BOUNDS,max(0,duration_ms))]+=1
    def snapshot(self):
        with self.lock:
            return dict(identity=self.identity,requests=self.requests,errors=self.errors,client_errors=self.client_errors,histogram=list(self.histogram))
    def flush(self):
        try:
            self.folder.mkdir(parents=True,exist_ok=True)
            path=self.folder/(self.identity+'.json');staged=path.with_suffix('.next')
            staged.write_text(json.dumps(self.snapshot(),separators=(',',':')),encoding='utf-8');os.replace(staged,path)
            # Retain only recent processes; filename is generated locally.
            for old in self.folder.glob('*.json'):
                if old!=path and time.time()-old.stat().st_mtime>120:old.unlink(missing_ok=True)
        except Exception:pass
    def start(self):
        if self.thread and self.thread.is_alive():return
        self.stop.clear()
        def run():
            while not self.stop.is_set():
                self.flush();self.stop.wait(5)
        self.thread=threading.Thread(target=run,name='relay-request-metrics',daemon=True);self.thread.start()
    def close(self):
        self.stop.set()
        if self.thread:self.thread.join(timeout=.2)

class RequestMetrics:
    def __init__(self,app,recorder):self.app=app;self.recorder=recorder
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or not scope.get('path','').startswith('/api/') or scope.get('path')=='/api/health':
            return await self.app(scope,receive,send)
        started=time.perf_counter();status=500;streaming=False
        async def response(message):
            nonlocal status,streaming
            if message['type']=='http.response.start':
                status=message['status']
                streaming=any(k.lower()==b'content-type' and b'text/event-stream' in v for k,v in message.get('headers',[]))
            await send(message)
        try:await self.app(scope,receive,response)
        except BaseException:
            status=500
            raise
        finally:
            if not streaming:
                try:self.recorder.observe((time.perf_counter()-started)*1000,status)
                except Exception:pass
