# Activate the existing azelections-prod tunnel

> The activation report below describes the Mac deployment. Windows migration uses the same tunnel and existing routing; follow [Windows deployment and cutover](windows-deployment.md). A new connector can immediately receive live requests. No Windows connector has been activated during migration preparation.

Target: **azelections-prod**, tunnel ID **333d2484-25bd-408c-94d6-a0d1e44bf19c**, zone **azelections.app**. Do not create a replacement tunnel. The target DNS and hostname-scoped rule expressions are retained in `production/cloudflare-target.json`; the proposed application ingress is in `production/cloudflare-route.json`. That ingress file is a template, not permission to overwrite the existing tunnel configuration.

Current status, October 28: **public activation was explicitly approved and completed**. The existing `azelections-prod` connector is running and healthy. Normal DNS and certificate-validated HTTPS work at **https://azelections.app**. HTTP redirects to HTTPS with status 308 and preserves the path/query. All **12 public browser checks passed** serially, including live committed-import SSE delivery and missed-import recovery with selection/sorting preserved. No DNS, Cloudflare route or account API changes were made by the agent; the user configured the route/CNAME in the dashboard.

The connector token remains in an ignored mode-0600 file inside a mode-0700 directory, excluded from Docker builds and logs. It is used only by cloudflared to authenticate with Cloudflare. No account API credential or edit permission was requested for activation. Docker Desktop login startup is confirmed enabled.

## Existing configuration reported by the user

The user checked the authenticated Cloudflare dashboard and confirmed **no published application routes** on `azelections-prod` and **zero DNS records** in the `azelections.app` zone. There is no existing apex record to replace. This is user-confirmed dashboard inventory, not an API inspection by the application. The origin is **HTTP, `http://caddy:80`**. The user subsequently configured the published application route, confirmed the CNAME target, and explicitly approved starting the connector and public verification.

The Compose service is named `frontend` to preserve existing operating commands. It runs Caddy and has Docker network alias **caddy**, listening on port **80**. The Mac exposes only `127.0.0.1:8080` for local viewing. The connector uses the same Docker network; the intended Cloudflare origin is `caddy:80`, not the Mac's loopback address.

## Manual Cloudflare steps — review before saving or activating

The user completed this configuration and approved activation. These recorded steps are retained for review/recovery; do not add duplicate routes or DNS records. No replacement tunnel, account API token or edit API permissions are needed.

1. Open the Cloudflare dashboard → **Networking → Tunnels → azelections-prod**. Confirm tunnel ID `333d2484-25bd-408c-94d6-a0d1e44bf19c`.
2. Open **Routes → Add route → Published application** (some dashboard versions call this **Published application routes** or **Public Hostnames**).
3. Set **Subdomain** to blank, **Domain** to `azelections.app`, and **Path** to blank. The resulting public hostname must be exactly `azelections.app`.
4. Set **Service type: HTTP** and **URL: caddy:80**. If there is a combined URL field instead, enter `http://caddy:80`.
5. Under additional HTTP origin settings, set **HTTP Host Header** to `azelections.app` if needed. Do not configure an HTTPS origin or disable TLS verification; TLS for visitors will terminate at Cloudflare, while this private Docker origin uses HTTP. The final unmatched route should be `http_status:404`.
6. Review the summary: one new hostname route, zero existing routes replaced, one new proxied apex CNAME and no unrelated records changed. Stop here for explicit approval before saving.
7. **After approval**, save the published application route. Cloudflare normally creates the DNS record automatically. In **azelections.app → DNS → Records**, confirm **CNAME**, name **@ / azelections.app**, target **333d2484-25bd-408c-94d6-a0d1e44bf19c.cfargotunnel.com**, **Proxied**, TTL **Auto**. Do not add a duplicate. If the dashboard did not create it, add just this record after confirming it is still absent.
8. In **Caching → Cache Rules**, review existing policy. If necessary, add a rule scoped to `(http.host eq "azelections.app" and starts_with(http.request.uri.path, "/api/"))` with **Cache eligibility: Bypass cache**. Preserve other rules. The backend supplies private browser-cache policies and ETags, which Caddy preserves; shared Cloudflare API caching stays bypassed. See [browser caching](browser-caching.md).
9. Ensure an active Cloudflare edge certificate covers `azelections.app`. If HTTP→HTTPS is not already provided, use a hostname-scoped redirect rule: hostname `azelections.app`, scheme `http`, redirect to the same hostname/path using `https`, preserving the query string. Preserve unrelated zone settings.
10. Confirm the saved route and DNS values, then give explicit approval to start the existing Compose `tunnel` service. The prepared command is `docker compose --profile public up -d --wait tunnel`; **it was run after explicit approval**. The application cannot be declared publicly ready until connector readiness, HTTPS and the public browser/SSE checks pass.

Cloudflare documents automatic DNS creation when adding a dashboard route in its [routing guide](https://developers.cloudflare.com/tunnel/concepts/routing/), and the form workflow in [Publish an application](https://developers.cloudflare.com/tunnel/get-started/).

## Connector-only authentication — selected approach

The user requested least privilege and preservation of the manually created tunnel. **No account API token or edit permissions are required for the selected approach.** Obtain the connector token from Cloudflare → Networking → Tunnels → **azelections-prod** → Add a replica. Copy only the token from the displayed installation command; do not run that installation command or paste it into chat.

From the repository root, enter the connector token at the hidden prompt:

```sh
.venv/bin/python scripts/inspect_cloudflare.py save-connector-token
```

The helper checks the token's embedded tunnel ID before saving it to `.production/secrets/tunnel-token`, mode 0600, which Compose already mounts privately. This local format/ID check is not proof that Cloudflare accepts the token; connector readiness is tested only after activation approval. Saving a token makes no network calls and does not start the connector.

Inspect existing published application routes, apex DNS, cache policy and HTTPS behavior in the authenticated dashboard. Supply non-secret route/DNS details or a local exported configuration for review. Include every published hostname on this tunnel, not just this application: a new connector must reach all origins it may receive traffic for. Do not change or replace the existing configuration merely to match the template.

## Optional read-only API inventory

If the user later chooses automatic inspection, a separate narrowly scoped API token can use Account → Cloudflare Tunnel → Read and Zone → Zone → Read, DNS → Read, Cache Rules → Read, Single Redirect → Read. This is optional, not a prerequisite for connector-only hosting. No edit permission is requested. Enter it with `authenticate`, then inspect:

```sh
.venv/bin/python scripts/inspect_cloudflare.py authenticate
.venv/bin/python scripts/inspect_cloudflare.py inspect
```

The read-only helper confirms the supplied tunnel ID/name in the zone's account and retains DNS/ingress/cache/redirect configuration privately in `.production/cloudflare-inventory.json`. It never calls the write-permission-protected connector-token endpoint and never changes routes, DNS or rules. Neither token is printed. Account API access has not been granted, and the script has not inspected the live account.

## Approval boundary

The intended DNS target is the proxied apex CNAME:

`azelections.app` → `333d2484-25bd-408c-94d6-a0d1e44bf19c.cfargotunnel.com`

The application ingress is `azelections.app` → `http://caddy:80`, HTTP Host header `azelections.app`. The desired catch-all is `http_status:404`. Add a cache-bypass rule for this hostname's `/api/*` only if existing policy does not already provide it, and ensure HTTP requests for this hostname redirect to HTTPS without changing unrelated hostnames.

**Existing configuration must be reviewed before activation.** If it already supplies the required routing, propose zero Cloudflare changes and ask only for connector activation approval. Preserve every unrelated ingress/rule/DNS record, including MX/TXT. If anything conflicts, describe the exact affected settings and obtain approval before the user changes them in the dashboard; do not request broad API edit access. Do not upload the standalone ingress template over existing routes. Save the before-state for rollback and recheck it immediately before applying approved changes.

Present the complete affected-record and rule diff for user approval. Only after approval may public route/DNS/rule changes be applied and the `public` Compose profile started. A saved token or a successful authentication reply is not public-activation approval.

## Docker Desktop login startup

The user enabled Docker Desktop → Settings → General → **Start Docker Desktop when you sign in**. The saved setting was confirmed `AutoStart: true` on October 28, 2026. No live settings file was edited and automatic macOS login was not enabled. Existing container restart policies remain `unless-stopped`; Docker Desktop still needs to run, and the Mac needs power/network availability.

## After approved activation

Use the public activation/check/unpublish commands in [production hosting](production-hosting.md). Verify the connector's `/ready` health check, edge certificate and HTTP→HTTPS, deep links, API and committed-import SSE delivery. The existing browser suite can target the public origin:

```sh
PLAYWRIGHT_BASE_URL=https://azelections.app npm --prefix frontend run test:e2e
```

This includes actual civicAPI participation refreshes from the local scheduler and a browser reconnect test; it does not verify election figures. No public readiness claim is valid until these checks pass.

References: [Cloudflare tunnel token retrieval](https://developers.cloudflare.com/tunnel/reference/tunnel-tokens/), [Cloudflare API token permissions](https://developers.cloudflare.com/fundamentals/api/reference/permissions/), [Docker Desktop settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/).
