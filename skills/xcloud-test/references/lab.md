# xcdev lab — tool map, accounts, traps

The lab's own playbook is the MCP resource `xcdev://skills/xcdev-qa` (`ReadMcpResourceTool server: xcdev`).
Read it once per session when something here is unclear; it is the source of truth for the lab.

## Environments

| Need | Tool |
|---|---|
| The PR as it would land | `preview_deploy {pr, mode: "merged_onto_dev"}` → `job_wait` (1.5-6 min; queued builds say `queued_behind`) |
| The PR head as is (hotfix into master) | `preview_deploy {pr, mode: "head"}` |
| Baseline | staging `ci/dev` (plain `dev`). Never touch its own servers `dev-nginx`, `dev-ols`, `dev-docker` |
| A merged/closed PR or an old release | `env_create {workspace: "<yours>", env, ref: <commit or tag>}` (counts against your Allowance) |
| Backing service (ClickHouse, S3) | `service_add {environment, service}` |
| What is deployed | `env_status` (`deploy.lab_build.sha`, `used_by`, `sign_in`) |

URLs: preview `https://lab-ci-pr-<n>.tmp1.dev`, Mailpit `https://lab-ci-pr-<n>-mail.tmp1.dev`.

## Servers and sites

| Need | Tool |
|---|---|
| nginx/ols with MySQL 8 on 24.04, ~30 s | `servers_create {environment, servers: [{name: "q<N>-ng", stack: "nginx"}]}` |
| Docker server | `stack: "docker"` |
| Provisioned by the PR's own code | `fresh: true` (minutes), or `ubuntu: "26.04"`, or `db: "mysql84"`/`"maria"` |
| 22.04 or ARM | `provider: "hetzner"` (+ `type: "cax11"` for ARM). Costs money: max 3 at once, remove as soon as done |
| Keep a failed server to inspect | `keep_on_failure: true` |
| WordPress / blank PHP / Laravel site | `sites_create {environment, sites: [{server: "ci/q<N>-ng", type, label}]}` |
| Docker-compose / one-click app | no tool: `inertia_props` of the create page for the form, then `app_call POST` the app's route; `app_wait_tasks` |
| Remove | `remove {servers: [...]}`, `sites_remove {sites: [...]}` |

Names: `q<N>-<short>` (≤ 31 chars). Servers are created in parallel across servers; sites on one server one at a
time. Lab VMs have ~1.8 GB RAM: memory-gated installs (n8n) refuse; say so, don't fake it.

## Checking things

| Need | Tool |
|---|---|
| A dashboard route as an account | `app_call {environment, method, path, body?, as?}` (default: lab super admin) |
| An Inertia page's props | `inertia_props {environment, path, keys?, as?}` |
| A page in a browser: screenshot, console errors, failed requests, blank page | `page_check {environment, path, as?, steps?, viewport?, color_scheme?, props?}` → `evidence_url` |
| Hover, upload, read text, > 20 steps, video | `scripts/lab-flow.mjs` with `bot_token` (see below) |
| Tasks an action started | `app_wait_tasks {environment, server_id or site_id, since_task_id}`; read `max_task_id` first with `timeout_seconds: 0` |
| A task's full log | `task_log {environment, task}` |
| PHP in the app | `app_tinker {environment, code}` (plain PHP, no shell quoting) |
| Shell in the control plane (logs, DB, Horizon) | `cp_exec {environment, script}` — code in `/workspace/xcloud`, `.env` in `/workspace/shared/.env`, DB `mysql xcloud` |
| Shell / SQL / files on a server | `server_exec`, `server_sql`, `file_get`, `file_put` |
| A site through its own web server and PHP | `site_http {site: "ci/q<N>-ng/<site id>", path, times, body}` |
| Provisioning truth | `server_health {server}` ("provisioned 100 %" in the app is not proof) |
| Poll until a condition | `wait_for {environment or server, check, until}` |
| Monitoring callback | `monitor_now`, `callback_capture` |

## Accounts and data

Seeded in every preview and staging (`/workspace/LOGINS.md`; `file_get ... reveal: true` only to fill a real
login form, never print it):

| Account | Role |
|---|---|
| lab super admin (LOGINS.md) | super_admin, owner of team A (#1) — the default for `app_call` |
| `user1@xcdev.test` | customer, team-admin in team A |
| `user2@xcdev.test` | customer, owner of team B (`pending_billing`: pages redirect to Billing) |
| `support1@` / `support2@xcdev.test` | support staff (support access gate on team resources) |
| `admin@xcdev.test` | admin staff (sees everything by design) |
| `agent@xcdev.test` | agent API bot (server/site pages 403) |

`fixture_create {environment, scenario, params}`: `team_member {team?, role: team-admin|server-admin|site-admin}`,
`active_customer {plan?}` (a second paid team: the clean IDOR target/attacker), `api_token`, `oauth_connections`,
`cookie_consent_accepted`. Undo with `fixture_remove`. `api_token {environment, as, abilities?, ttl_minutes?}`
mints a real Public API token (a handle; the value is shown once: keep it in memory).
`seed_apply catalog` then `rich`: billing-state teams, white-label resellers, invoices (only for billing/WL PRs).

**Lab servers sit in the super admin's team A (#1)**, as the shared servers do: confirm your server's `team_id`
with `app_tinker` before planning role checks. For cross-team checks, `user2` or an
`active_customer` is the outsider; for in-team role checks, `user1` or a `team_member` fixture.

**Uuid or id: read the route.** Newer dashboard routes and the whole Public API bind `{server:uuid}`; older ones
(backups, restore, many `/api/server/{server}/...`) take the integer id. `lab_list` gives the integer id; get the
uuid with `app_tinker`: `echo \App\Models\Server::find(<id>)->uuid;`. A 404 on a page you expect usually means
the wrong one.

## Browser outside page_check

```bash
# 1. MCP bot_token {hours: 2, label: "q<N>"} -> client_id, client_secret (keep in memory only)
# 2. MCP file_get {environment, path: "/workspace/LOGINS.md", reveal: true} -> the account's password
# 3. from the xCloud checkout (Playwright resolves from its node_modules):
CF_ACCESS_CLIENT_ID=... CF_ACCESS_CLIENT_SECRET=... LAB_PASSWORD=... \
  node ~/.claude/skills/xcloud-test/scripts/lab-flow.mjs ~/.xcloud-qa/pr<N>/flows/C-07.json
```

The helper adds the Access headers on `lab-ci-*` hosts only, signs in through the email-first login, dismisses the
cookie banner without consenting, and returns steps, console errors, failed requests and screenshots as JSON. Each
screenshot is the whole page (it grows the viewport past xCloud's inner scroller) and carries the page's HTTP
status, any `problems` (error page, blank page, signed out) and `identical_to` when it repeats an earlier shot; a
problem fails the step unless the step has `allow_error: true`.
Never pass secrets inline in a file or in `playwright-cli run-code` (it echoes the code). Revoke the token at the end.

## Traps seen on real runs

- `lab_list` may list servers and sites under a preview that its app no longer has (after a redeploy). Use
  `env_status` and confirm ids with `app_tinker` before using them.
- The shared servers (`shared-nginx`, `shared-ols`, `shared-docker`) sit in team A of every preview: a team-wide
  bulk action reaches them. Select rows by hand. Never change them; they are rebuilt nightly at 03:30 UTC and get
  new ids in every preview: re-read ids after that time.
- `page_check {full_page: true}` returns only the viewport on xCloud pages (inner scroll container): use
  `viewport: {"width": 1280, "height": 1400}` or taller (reported to the lab team).
- Inertia actions answer 302 for success **and** validation errors (`app_call` loses the flash): confirm in tasks
  or by reading the resource back.
- The control plane cannot be reached from your machine and the lab host has no route to server IPs: HTTP to sites
  goes through `site_http` (from the control plane).
- Servers have no `jq`; python3 is there. Do not install tools on a server under test.
- `service_add minio` is reachable by the browser, not by servers: a backup destination needs an S3 gateway
  container on your own docker server.
- Git-deploy UI: open `/server/{uuid}/site/create?type=deploy-via-git&repo=<url>&account=public` directly.
- A sleeping preview answers 503; a visit never wakes it, `preview_deploy` does.
- A push to the PR while `lab:preview-live` is on redeploys the preview under you: check `env_status` before a
  long run and again if results turn strange.

## Cleanup checklist

`remove {servers}` (preview and `ci/dev`), `sites_remove` for sites on shared servers, `fixture_remove`,
`api_token_revoke`, `bot_token_revoke`, then `lab_list {mine: true}`. Report lab problems with `report_friction`.
