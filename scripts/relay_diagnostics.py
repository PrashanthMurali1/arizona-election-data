"""Standalone module also installed beside the reviewed election worker.

Only structural diagnostics survive. Child text, assertion values, test titles,
URLs, environment and filesystem paths are never serialized.
"""
from datetime import datetime,timezone
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re

SUITES={'catalog.spec.ts','explorer.spec.ts','house.spec.ts','production.spec.ts',
        'test_deploy_worker.py','test_logging.py','test_early_vote_schedule.py','test_early_vote_updates.py'}
OPERATORS={'toContainText','toHaveText','toBeVisible','toHaveCount','toEqual','toBe','toHaveAttribute'}
PHASES={'preflight','fetch','render','build','test','backup','migrate','activate','verify','rollback','adopt'}

def extract(output):
    text=output[-1048576:];items=[]
    # Parse structural test locations; never include the remainder of a line.
    matches=re.finditer(r'(?:e2e[/\\]|production/tests/|backend/tests/)([a-zA-Z0-9_.]+)(?::(\d{1,5}))?',text)
    for match in matches:
        if match[1] not in SUITES: continue
        item={'kind':'test_failure','suite':match[1]}
        if match[2]: item['line']=int(match[2])
        if item not in items and len(items)<12: items.append(item)
    operator=next((op for op in sorted(OPERATORS) if re.search(r'\.'+op+r'\(',text)),None)
    kind=('missing_file' if 'FileNotFoundError' in text else 'timeout' if re.search(r'TimeoutError|Test timeout',text)
          else 'assertion' if operator or 'AssertionError' in text else 'typecheck' if re.search(r'error TS\d{4}',text)
          else 'dependency' if re.search(r'npm ERR!|npm error',text) else 'test_failure' if items else 'command_failure')
    if not items: items=[{'kind':kind}]
    else:
        for item in items:
            item['kind']=kind
            if operator: item['operator']=operator
    return items

def record_failure(home,output,phase,code,commit=None,severity='ERROR'):
    """Best effort: never change deployment behavior if disk/logging fails."""
    try:
        value={'timestamp':datetime.now(timezone.utc).isoformat(),'severity':'WARNING' if severity=='WARNING' else 'ERROR',
               'event':'deployment_command_failed','diagnostics':extract(output)}
        if phase in PHASES: value['phase']=phase
        if type(code) is int: value['exit_code']=code
        if isinstance(commit,str) and re.fullmatch('[0-9a-f]{40}',commit): value['commit_sha']=commit
        folder=Path(home)/'diagnostics';folder.mkdir(parents=True,exist_ok=True)
        handler=RotatingFileHandler(folder/'commands.jsonl',maxBytes=262144,backupCount=3,encoding='utf-8')
        try:
            record=logging.LogRecord('diagnostics',logging.ERROR,'',0,json.dumps(value),(),None)
            handler.emit(record)
        finally: handler.close()
    except Exception: pass
