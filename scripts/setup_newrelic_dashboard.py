"""Validate and provision the app's private New Relic dashboard and alert policy.

The User API key is read only by newrelic_admin; never stored in dashboard JSON.
No notification destinations, workflows, paid integrations or app changes.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from newrelic_admin import ROOT, nerdgraph

ACCOUNT = 8675480
APP = 'Arizona Election Explorer (Production)'
ENTITY = 'ODY3NTQ4MHxBUE18QVBQTElDQVRJT058MTEzNDY5NDIwOA'
HEALTH = 'WebTransaction/Function/backend.app.main:health'
SSE = 'WebTransaction/Function/backend.app.main:early_voting_updates'
METRIC = f"entity.guid = '{ENTITY}' AND transactionType = 'Web'"
API_METRIC = f"{METRIC} AND transactionName NOT IN ('{HEALTH}', '{SSE}')"
TRANSACTION = f"appName = '{APP}' AND transactionType = 'Web' AND name NOT IN ('{HEALTH}', '{SSE}')"
LOG = f"application = '{APP}'"
ERRORS = 'count(apm.service.transaction.error.count)'
DURATION = 'count(apm.service.transaction.duration)'
ERROR_RATE = f'100 * {ERRORS} / {DURATION}'
STATE = ROOT / '.production/newrelic-monitoring-state.json'
PLAN = ROOT / 'production/newrelic-dashboard.json'
POLICY_NAME = 'Arizona Election Explorer - Production Health'


def widget(title, query, row, column=1, width=12, height=3, viz='line'):
    return dict(title=title, layout=dict(row=row, column=column, width=width, height=height),
                visualization={'id': 'viz.' + viz},
                rawConfiguration={'nrqlQueries': [{'accountId': ACCOUNT, 'query': query}]})


def markdown(text):
    return dict(title='Scope and interpretation', layout=dict(row=1, column=1, width=12, height=3),
                visualization={'id':'viz.markdown'}, rawConfiguration={'text': text})


def dashboard():
    overview = [markdown(
        '## Arizona Election Explorer — API performance\n'
        'Normal API requests exclude Docker health checks and the long-lived SSE update stream. '
        'Throughput/error volume use APM metrics; latency percentiles and endpoint breakdowns use transaction events '
        '(which can be sampled). Process memory covers the Python backend, not the Windows host. '
        'No browser page-load or infrastructure agent is installed. Alert issues stay in New Relic; no email/SMS workflow.')]
    overview += [
        widget('API requests / minute', f"FROM Metric SELECT rate({DURATION},1 minute) AS 'API RPM' WHERE {API_METRIC} SINCE 60 minutes ago",4,1,4,viz='billboard'),
        widget('API p95 response time (ms)', f"FROM Transaction SELECT percentile(duration*1000,95) AS 'p95 ms' WHERE {TRANSACTION} SINCE 60 minutes ago",4,5,4,viz='billboard'),
        widget('API error rate (%)', f"FROM Metric SELECT {ERROR_RATE} AS 'Error %' WHERE {API_METRIC} SINCE 60 minutes ago",4,9,4,viz='billboard'),
        widget('API latency p50 / p95 / p99 (ms)', f"FROM Transaction SELECT percentile(duration*1000,50,95,99) WHERE {TRANSACTION} SINCE 60 minutes ago TIMESERIES 1 minute",7,1,8),
        widget('API throughput (requests / minute)', f"FROM Metric SELECT rate({DURATION},1 minute) AS 'API RPM' WHERE {API_METRIC} SINCE 60 minutes ago TIMESERIES 1 minute",7,9,4),
        widget('Web errors / minute — includes health and SSE failures', f"FROM Metric SELECT rate(count(apm.service.error.count),1 minute) AS 'Errors/min' WHERE {METRIC} SINCE 60 minutes ago TIMESERIES 1 minute",10,1,6),
        widget('API error rate (%) over time', f"FROM Metric SELECT {ERROR_RATE} AS 'Error %' WHERE {API_METRIC} SINCE 60 minutes ago TIMESERIES 1 minute",10,7,6),
        widget('Endpoints — p95 latency, volume and 5xx (sampled events)', f"FROM Transaction SELECT count(*) AS 'Requests', percentile(duration*1000,95) AS 'p95 ms', filter(count(*),WHERE http.statusCode >= 500) AS '5xx' WHERE {TRANSACTION} SINCE 60 minutes ago FACET name LIMIT 15",13,1,12,4,'table'),
        widget('Database time per API request (ms)', f"FROM Transaction SELECT average(databaseDuration)*1000 AS 'Mean DB ms' WHERE {TRANSACTION} SINCE 60 minutes ago TIMESERIES 1 minute",17,1,6),
        widget('Backend process physical memory (MB)', f"FROM Metric SELECT average(apm.service.memory.physical) AS 'Memory MB' WHERE entity.guid = '{ENTITY}' SINCE 60 minutes ago TIMESERIES 1 minute",17,7,6),
        widget('All web transactions — telemetry continuity', f"FROM Metric SELECT rate({DURATION},1 minute) AS 'All web RPM' WHERE {METRIC} SINCE 60 minutes ago TIMESERIES 1 minute",20,1,6),
        widget('Health-check traffic (excluded from API charts)', f"FROM Metric SELECT rate({DURATION},1 minute) AS 'Health RPM' WHERE {METRIC} AND transactionName = '{HEALTH}' SINCE 60 minutes ago TIMESERIES 1 minute",20,7,6),
    ]
    operations = [markdown(
        '## Errors and refresh operations\n'
        'Forwarded logs are rate-capped and deduplicated: use APM metric panels for error volume, logs for diagnosis. '
        'An empty errors table is normal when no errors were recorded. Refresh runs every six hours in Asia/Kolkata. '
        'A missed-refresh alert arms after it sees a successful live completion; it cannot infer a heartbeat from quiet logs. '
        'Telemetry loss is a reporting-silence check, not an external public HTTPS availability test.')]
    operations += [
        widget('Web errors in last 5 minutes', f"FROM Metric SELECT count(apm.service.error.count) AS 'Errors' WHERE {METRIC} SINCE 5 minutes ago",4,1,4,viz='billboard'),
        widget('Forwarded critical events (capped)', f"FROM Log SELECT filter(count(*), WHERE severity = 'CRITICAL') AS 'Critical' WHERE {LOG} SINCE 60 minutes ago",4,5,4,viz='billboard'),
        widget('Successful refreshes in last 24 hours', f"FROM Log SELECT filter(count(*), WHERE event = 'refresh_completed' AND outcome = 'success') AS 'Successful refreshes' WHERE {LOG} SINCE 24 hours ago",4,9,4,viz='billboard'),
        widget('Error classes from APM', f"FROM TransactionError SELECT count(*) AS 'Errors' WHERE appName = '{APP}' SINCE 60 minutes ago FACET error.class LIMIT 15",7,1,6,viz='bar'),
        widget('Observed HTTP status codes (sampled events)', f"FROM Transaction SELECT count(*) AS 'Requests' WHERE {TRANSACTION} SINCE 60 minutes ago FACET http.statusCode TIMESERIES 1 minute",7,7,6),
        widget('Forwarded warnings/errors by service (capped)', f"FROM Log SELECT count(*) AS 'Forwarded events' WHERE {LOG} AND severity IN ('WARNING','ERROR','CRITICAL') SINCE 60 minutes ago FACET service TIMESERIES 5 minutes",10,1,6),
        widget('Top forwarded failure events (capped)', f"FROM Log SELECT count(*) AS 'Forwarded events' WHERE {LOG} AND severity IN ('ERROR','CRITICAL') SINCE 60 minutes ago FACET service,event LIMIT 15",10,7,6,viz='table'),
        widget('Latest failure diagnostics', f"FROM Log SELECT timestamp,severity,service,event,exception.type,route,correlation_id WHERE {LOG} AND severity IN ('ERROR','CRITICAL') SINCE 24 hours ago LIMIT 30",13,1,12,4,'table'),
        widget('Latest refresh completions — outcome and job ID', f"FROM Log SELECT timestamp,outcome,duration_ms,exit_code,correlation_id WHERE {LOG} AND event = 'refresh_completed' SINCE 2 days ago LIMIT 20",17,1,12,4,'table'),
        widget('Refresh duration (ms)', f"FROM Log SELECT latest(duration_ms) AS 'Refresh duration ms' WHERE {LOG} AND event = 'refresh_completed' SINCE 2 days ago TIMESERIES 1 hour",21,1,6),
        widget('Latest operational warnings', f"FROM Log SELECT timestamp,service,event,feed,correlation_id WHERE {LOG} AND severity = 'WARNING' SINCE 24 hours ago LIMIT 15",21,7,6,viz='table'),
    ]
    for item in operations:
        if item['title'] in {'Successful refreshes in last 24 hours',
                             'Latest refresh completions — outcome and job ID', 'Refresh duration (ms)'}:
            item['rawConfiguration']['ignoreTimeRange'] = True
    return dict(name='Arizona Election Explorer - Production Health', permissions='PRIVATE',
                description='API performance, error spikes and refresh health. Filtered local logs are capped; APM metrics drive volume alerts.',
                pages=[dict(name='API Performance', widgets=overview), dict(name='Errors and Refresh', widgets=operations)])


def term(threshold, duration, priority='CRITICAL', occurrences='ALL', operator='ABOVE'):
    return dict(threshold=threshold, thresholdDuration=duration, priority=priority,
                thresholdOccurrences=occurrences, operator=operator)


def conditions():
    def make(name, query, terms, description, *, window=60, sparse=False, expiration=None):
        signal = dict(aggregationWindow=window, fillOption='NONE')
        signal.update(dict(aggregationMethod='EVENT_TIMER', aggregationTimer=60) if sparse else
                      dict(aggregationMethod='EVENT_FLOW', aggregationDelay=120))
        value = dict(name=name, description=description, enabled=True, nrql={'query':query},
                     signal=signal, terms=terms, valueFunction='SINGLE_VALUE',
                     violationTimeLimitSeconds=86400)
        if expiration:
            value['expiration'] = dict(expirationDuration=expiration, openViolationOnExpiration=True,
                                       closeViolationsOnExpiration=True)
        return value
    return [
        make('Web error burst - 5 minute count', f"FROM Metric SELECT count(apm.service.error.count) WHERE {METRIC}",
             [term(0,300,'WARNING','AT_LEAST_ONCE'),term(4,300,'CRITICAL','AT_LEAST_ONCE')],
             'Warning: at least one web error in a five-minute bucket. Critical: at least five. Includes health/SSE errors. APM metrics, not capped logs.', window=300),
        make('API error rate - sustained', f"FROM Metric SELECT {ERROR_RATE} WHERE {API_METRIC}",
             [term(2,300,'WARNING'),term(5,300)],
             'API error rate above 2% warning or 5% critical for five minutes. Health/SSE excluded. Quiet windows are not fabricated as zero.'),
        make('API p95 latency - sustained', f"FROM Transaction SELECT percentile(duration*1000,95) WHERE {TRANSACTION}",
             [term(500,300,'WARNING'),term(1000,300)],
             'p95 above 500 ms warning or 1000 ms critical for five minutes. Initial conservative limits; excludes health checks and long-lived SSE.'),
        make('APM reporting silent for 5 minutes', f"FROM Metric SELECT {DURATION} WHERE {METRIC}",
             [term(0,300,operator='BELOW')],
             'Loss-of-signal critical after five minutes without web metrics. Existing health checks normally maintain this signal. Not an external HTTPS probe.', expiration=300),
        make('Refresh job failed', f"FROM Log SELECT filter(count(*), WHERE (event = 'refresh_completed' AND outcome = 'failed') OR event = 'refresh_runtime_failed') WHERE {LOG}",
             [term(0,60,occurrences='AT_LEAST_ONCE')],
             'Critical when a forwarded refresh failure is observed. Best effort because forwarding is capped; missed-success alert adds separate coverage.', sparse=True),
        make('Successful refresh missing for 7 hours', f"FROM Log SELECT count(*) WHERE {LOG} AND event = 'refresh_completed' AND outcome = 'success'",
             [term(0,60,operator='BELOW')],
             'Loss-of-signal after seven hours without a successful six-hour refresh. Arms only after the alert engine sees a matching live success. No artificial gap fill.', sparse=True, expiration=25200),
        make('Critical service event observed', f"FROM Log SELECT filter(count(*), WHERE severity = 'CRITICAL') WHERE {LOG}",
             [term(0,60,occurrences='AT_LEAST_ONCE')],
             'Critical for a forwarded CRITICAL event from any app service. Local logs retain full critical events; forwarding caps can drop events.', sparse=True),
    ]


def all_queries(plan):
    found = []
    for page in plan['dashboard']['pages']:
        for item in page['widgets']:
            for query in item['rawConfiguration'].get('nrqlQueries', []):
                found.append((item['title'], query['query']))
    for condition in plan['conditions']:
        found.append((condition['name'], condition['nrql']['query'] + ' SINCE 60 minutes ago'))
    return found


def validate(plan):
    def check(item):
        title, query = item
        result = nerdgraph('query($id:Int!,$q:Nrql!){actor{account(id:$id){nrql(query:$q){results}}}}',
                           {'id':ACCOUNT,'q':query})
        return dict(title=title, results=result['actor']['account']['nrql']['results'])
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(check, all_queries(plan)))
    (ROOT / '.production/newrelic-query-validation.json').write_text(json.dumps(results,indent=2)+'\n')
    print(f'PASS {len(results)} real dashboard/alert queries')


def save(state):
    temporary = STATE.with_suffix('.tmp')
    temporary.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    temporary.replace(STATE)


def apply(plan):
    state = json.loads(STATE.read_text()) if STATE.exists() else {'accountId':ACCOUNT,'conditions':{}}
    if not state.get('dashboardGuid'):
        response = nerdgraph('mutation($id:Int!,$d:DashboardInput!){dashboardCreate(accountId:$id,dashboard:$d){entityResult{guid name} errors{description type}}}',
                             {'id':ACCOUNT,'d':plan['dashboard']})['dashboardCreate']
        if response.get('errors'):
            raise RuntimeError(json.dumps(response['errors']))
        state['dashboardGuid'] = response['entityResult']['guid']
        save(state)
    if not state.get('policyId'):
        response = nerdgraph('mutation($id:Int!,$p:AlertsPolicyInput!){alertsPolicyCreate(accountId:$id,policy:$p){id name}}',
                             {'id':ACCOUNT,'p':{'name':POLICY_NAME,'incidentPreference':'PER_CONDITION'}})['alertsPolicyCreate']
        state['policyId'] = response['id']
        save(state)
    for condition in plan['conditions']:
        if condition['name'] in state['conditions']:
            continue
        response = nerdgraph('mutation($id:Int!,$p:ID!,$c:AlertsNrqlConditionStaticInput!){alertsNrqlConditionStaticCreate(accountId:$id,policyId:$p,condition:$c){id name enabled}}',
                             {'id':ACCOUNT,'p':state['policyId'],'c':condition})['alertsNrqlConditionStaticCreate']
        state['conditions'][condition['name']] = response['id']
        save(state)
        print('Created condition:', response['name'])
    state['dashboardUrl'] = 'https://one.newrelic.com/redirect/entity/' + state['dashboardGuid']
    save(state)
    print(json.dumps(state,indent=2))


def verify(plan):
    state = json.loads(STATE.read_text())
    result = nerdgraph('''query($id:Int!,$guid:EntityGuid!){actor{
      entity(guid:$guid){guid name ... on DashboardEntity{permissions pages{guid name widgets{title layout{column row width height} visualization{id} rawConfiguration}}}}
      account(id:$id){
        alerts{nrqlConditionsSearch{nrqlConditions{id name enabled nrql{query} terms{threshold thresholdDuration priority operator thresholdOccurrences} signal{aggregationWindow aggregationMethod fillOption} expiration{expirationDuration openViolationOnExpiration}}}}
        aiWorkflows{workflows(filters:{}){entities{id name workflowEnabled destinationsEnabled destinationConfigurations{type}} totalCount nextCursor}}
      }
    }}''', {'id':ACCOUNT,'guid':state['dashboardGuid']})
    entity = result['actor']['entity']
    assert entity['permissions'] == 'PRIVATE'
    assert len(entity['pages']) == len(plan['dashboard']['pages'])
    for actual, expected in zip(entity['pages'], plan['dashboard']['pages']):
        assert actual['name'] == expected['name']
        assert len(actual['widgets']) == len(expected['widgets'])
        found = {item['title']:item for item in actual['widgets']}
        for item in expected['widgets']:
            remote = found[item['title']]
            assert remote['rawConfiguration'].get('nrqlQueries') == item['rawConfiguration'].get('nrqlQueries')
            assert remote['layout'] == item['layout']
    conditions_by_id = {item['id']:item for item in result['actor']['account']['alerts']['nrqlConditionsSearch']['nrqlConditions']}
    for condition in plan['conditions']:
        actual = conditions_by_id[state['conditions'][condition['name']]]
        assert actual['enabled'] and actual['nrql']['query'] == condition['nrql']['query']
        assert actual['terms'] == condition['terms']
        if condition.get('expiration'):
            assert actual['expiration']['expirationDuration'] == condition['expiration']['expirationDuration']
            assert actual['expiration']['openViolationOnExpiration']
    workflows = result['actor']['account']['aiWorkflows']['workflows']
    assert not workflows['nextCursor'], 'Review remaining notification workflows before claiming New Relic only'
    active_external = [item for item in workflows['entities'] if item['workflowEnabled'] and item['destinationsEnabled'] and item['destinationConfigurations']]
    assert not active_external, 'Existing external notification workflow requires scope review'
    (ROOT / '.production/newrelic-dashboard-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f"PASS private dashboard: {len(entity['pages'])} pages, {sum(len(p['widgets']) for p in entity['pages'])} widgets; seven enabled conditions; no active external notification workflow")
    print(state['dashboardUrl'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--validate', action='store_true')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    plan = {'accountId':ACCOUNT, 'entityGuid':ENTITY, 'dashboard':dashboard(), 'conditions':conditions()}
    PLAN.write_text(json.dumps(plan,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Prepared',PLAN)
    if args.validate:
        validate(plan)
    if args.apply:
        apply(plan)
    if args.verify:
        verify(plan)
