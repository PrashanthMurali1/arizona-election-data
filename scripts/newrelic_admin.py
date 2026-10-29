"""Local NerdGraph administration; the user API key never enters CLI arguments."""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def nerdgraph(query, variables=None):
    key = (ROOT / '.production/secrets/newrelic-user-api-key').read_text(encoding='utf-8-sig').strip()
    request = Request('https://api.newrelic.com/graphql',
                      data=json.dumps({'query': query, 'variables': variables or {}}).encode(),
                      headers={'API-Key': key, 'Content-Type': 'application/json'}, method='POST')
    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f'NerdGraph HTTP {exc.code}; credential contents withheld') from None
    if result.get('errors'):
        raise RuntimeError(json.dumps(result['errors']))
    return result['data']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    queries = parser.add_mutually_exclusive_group(required=True)
    queries.add_argument('--query')
    queries.add_argument('--query-file', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = nerdgraph(args.query_file.read_text(encoding='utf-8') if args.query_file else args.query)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(f'Saved {args.output}')
    else:
        print(json.dumps(result, indent=2))
