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

LOCATION = r'(?:e2e[/\\]|(?:production|backend)[/\\]tests[/\\])([a-zA-Z0-9_.]+)(?::(\d{1,5}))?'


def classification(text, default='command_failure'):
    # Match the first failed expectation in this failure block, not an operator
    # from a different test or the alphabetically first operator in all output.
    match = re.search(r'\.(' + '|'.join(sorted(OPERATORS)) + r')\(', text)
    operator = match[1] if match else None
    kind = ('missing_file' if 'FileNotFoundError' in text else
            'timeout' if re.search(r'TimeoutError|Test timeout', text) else
            'assertion' if operator or 'AssertionError' in text else
            'typecheck' if re.search(r'error TS\d{4}', text) else
            'dependency' if re.search(r'npm ERR!|npm error', text) else default)
    return kind, operator


def extract(output):
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', output[-1048576:])
    items = []
    # Playwright prints locations for successful tests too. Only numbered
    # failure sections may produce a test diagnostic; parse each independently.
    failures = list(re.finditer(r'^\s*\d+\)\s+[^\n]*?' + LOCATION + r'[^\n]*', text, re.M))
    for index, match in enumerate(failures):
        if match[1] not in SUITES:
            continue
        end = failures[index + 1].start() if index + 1 < len(failures) else len(text)
        body = text[match.end():end]
        kind, operator = classification(body, 'test_failure')
        item = {'kind': kind, 'suite': match[1]}
        if match[2]:
            item['line'] = int(match[2])
        # Prefer the assertion's stack location over the test declaration line.
        for frame in re.finditer(r'^\s*at\s+[^\n]*?' + LOCATION, body, re.M):
            if frame[1] == match[1] and frame[2]:
                item['line'] = int(frame[2])
                break
        if operator:
            item['operator'] = operator
        if item not in items and len(items) < 12:
            items.append(item)
    if failures:
        return items or [{'kind': classification(text)[0]}]
    # Pytest's final FAILED list identifies failures without including passing
    # cases or unreviewed test titles. Paths and values never leave this module.
    for match in re.finditer(r'^\s*FAILED\s+[^\n]*?' + LOCATION, text, re.M):
        if match[1] not in SUITES:
            continue
        item = {'kind': 'test_failure', 'suite': match[1]}
        if match[2]:
            item['line'] = int(match[2])
        if item not in items and len(items) < 12:
            items.append(item)
    return items or [{'kind': classification(text)[0]}]

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
