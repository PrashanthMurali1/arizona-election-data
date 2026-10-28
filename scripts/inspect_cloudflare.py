"""Read-only inventory for the existing production tunnel; never changes DNS/routes.

Authentication and connector tokens stay in private local files. Run authenticate
in your own terminal: getpass prevents credentials appearing in command arguments.
"""

import argparse
import base64
import json
import os
from getpass import getpass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / ".production/secrets"
API_TOKEN = PRIVATE / "cloudflare-api-token"
CONNECTOR_TOKEN = PRIVATE / "tunnel-token"
TARGET = json.loads((ROOT / "production/cloudflare-target.json").read_text())


def private_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(content)


def connector_matches(token):
    try:
        data = json.loads(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4)))
        return data.get("t") == TARGET["tunnel_id"]
    except (ValueError, TypeError):
        return False


def inspect():
    if not API_TOKEN.is_file():
        raise SystemExit(
            "Cloudflare API credentials missing. Run: .venv/bin/python scripts/inspect_cloudflare.py authenticate"
        )
    session = requests.Session()
    session.headers["Authorization"] = "Bearer " + API_TOKEN.read_text().strip()

    def get(path, **params):
        response = session.get(
            "https://api.cloudflare.com/client/v4/" + path,
            params=params,
            timeout=(5, 30),
            allow_redirects=False,
        )
        if response.status_code == 404:
            return None
        if not response.ok:
            raise RuntimeError(
                f"Cloudflare inventory request failed: HTTP {response.status_code}, {path}. Check scoped token permissions."
            )
        value = response.json()
        if not value.get("success"):
            raise RuntimeError(f"Cloudflare rejected inventory request: {path}")
        return value

    def collection(path, **params):
        result, page = [], 1
        while True:
            value = get(path, per_page=50, page=page, **params)
            if value is None:
                raise RuntimeError(f"Cloudflare collection not found: {path}")
            result.extend(value["result"])
            if page >= value.get("result_info", {}).get("total_pages", 1):
                return result
            page += 1

    zones = collection("zones", name=TARGET["zone"])
    if len(zones) != 1:
        raise RuntimeError("Expected exactly one accessible azelections.app zone")
    zone = zones[0]
    account, zone_id = zone["account"]["id"], zone["id"]
    tunnel_path = f"accounts/{account}/cfd_tunnel/{TARGET['tunnel_id']}"
    tunnel = get(tunnel_path)
    if tunnel is None or tunnel["result"]["name"] != TARGET["tunnel_name"]:
        raise RuntimeError(
            "The supplied tunnel ID/name is not accessible in this zone's account"
        )
    config = get(tunnel_path + "/configurations")
    if config is None:
        raise RuntimeError(
            "Existing tunnel configuration could not be inspected; no replacement will be created"
        )
    records = collection(f"zones/{zone_id}/dns_records")
    rules = {
        phase: get(f"zones/{zone_id}/rulesets/phases/{phase}/entrypoint")
        for phase in ("http_request_cache_settings", "http_request_dynamic_redirect")
    }
    snapshot = {
        "zone": zone,
        "tunnel": tunnel["result"],
        "configuration": config["result"],
        "dns_records": records,
        "rules": rules,
    }
    private_write(
        ROOT / ".production/cloudflare-inventory.json",
        json.dumps(snapshot, indent=2) + "\n",
    )

    def public_ingress(row):
        value = {k: row[k] for k in ("hostname", "path", "service") if k in row}
        parsed = urlsplit(value.get("service", ""))
        if parsed.netloc:
            host = parsed.hostname or ""
            if parsed.port:
                host += f":{parsed.port}"
            value["service"] = urlunsplit((parsed.scheme, host, parsed.path, "", ""))
        return value

    print(
        json.dumps(
            {
                "zone": zone["name"],
                "zone_status": zone["status"],
                "tunnel": TARGET["tunnel_name"],
                "tunnel_id": TARGET["tunnel_id"],
                "apex_records": [
                    {
                        k: r[k]
                        for k in ("id", "type", "name", "content", "proxied")
                        if k in r
                    }
                    for r in records
                    if r["name"] == TARGET["zone"]
                    and r["type"] in {"A", "AAAA", "CNAME"}
                ],
                "ingress": [
                    public_ingress(row)
                    for row in config["result"].get("config", {}).get("ingress", [])
                ],
                "connector_token_saved": CONNECTOR_TOKEN.is_file(),
                "changes_applied": False,
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["authenticate", "save-connector-token", "inspect"]
    )
    args = parser.parse_args()
    if args.action == "authenticate":
        token = getpass("Scoped read-only Cloudflare API token (hidden): ").strip()
        if not token:
            raise SystemExit("No token entered; nothing saved")
        private_write(API_TOKEN, token + "\n")
        print("API token saved privately. No Cloudflare changes made.")
    elif args.action == "save-connector-token":
        token = getpass("azelections-prod connector token (hidden): ").strip()
        if not connector_matches(token):
            raise SystemExit(
                "Token does not identify the supplied tunnel; nothing saved"
            )
        private_write(CONNECTOR_TOKEN, token + "\n")
        print(
            "Connector token saved privately for the supplied tunnel. No public activation or configuration changes made."
        )
    else:
        inspect()


if __name__ == "__main__":
    main()
