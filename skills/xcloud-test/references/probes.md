# Probes — where real bugs hide

Pick the sections that match the code map's risk classes. The black-box explorer covers the customer-side
techniques (equivalence classes, boundaries, state transitions, decision tables, error guessing) without code;
executors use this list with the code map in hand. Every probe becomes a check with an expected result
from `spec.md` (or `dev`'s behaviour), never from the PR code. The universal set applies to every PR.

## Universal (every PR)

| Probe | How | Bug it catches |
|---|---|---|
| **Reproduce on dev first** | the issue's steps on `ci/dev` (your own `q<N>-base` server there), then on the preview | fixes that fix nothing; wrong reproduction |
| **Silent failure** | sentinel around every action (`scripts/sentinel.sh`): new `laravel.log` ERROR/CRITICAL, new `failed_jobs`, task exit codes | success toast over a failed job; swallowed SSH errors |
| **Read it back** | after the action, read the resource again (page reload, `inertia_props`, `app_call GET`, on-server file) | state saved in the UI only; stale props; a 302 that hid a validation error |
| **Twice** | run the applying action 2-3 times | duplicate lines/rows, drift, "already exists" errors |
| **Neighbours** | the flows that write the same file or read the same data (from the code map's consumers) | regressions outside the diff |
| **Existing customers** | a server/site/setting made **before** the PR (build it on `ci/dev`'s code, or revert the state by hand on a preview server), then the PR's upgrade path | the change reaches only new resources; old rows misread |
| **The PR's promises** | each promise in `spec.md` → a measurement ("graceful" → request loop during the action) | claims that are not true |

## permissions-roles (and any route the PR adds or changes)

- **Cross-team (IDOR)**: `user2` (team B) against team A's resources by uuid: page (`page_check as`), JSON
  route (`app_call as`), Public API (`api_token as user2`). Expected: 403/404 and **no data in the body**.
  Try read, update and delete separately; a guarded GET with an open POST is common.
- **Inside a team**: `fixture_create team_member` with `server-admin` and `site-admin`; check each role against
  the action. A site-admin acting on a site they were not given; a server-admin on billing.
- **Hidden button ≠ guard**: when the UI hides an action for a role, call the route directly as that role.
- **Public API**: token without the ability (`abilities: ["read:servers"]` for a write) → 403; no token → 401;
  another team's uuid → 403/404; invalid body → 422 with field errors; every new route documented in
  `docs/public/xcloud-public-api.openapi.yaml` with an `operationId` (else no MCP tool).
- **Staff**: support accounts hit the support access gate on team resources; that is by design. **Admins see
  everything by design** (`Gate::before`): never report admin access as a finding.
- **White-label**: a white-label client sees only its reseller's products and branding; xCloud brand strings
  where a reseller's should be.

## billing-limits

- Boundaries from the plan or limit: 0, 1, limit − 1, limit, limit + 1; and an empty data set (division by zero).
- Plan states: `active_customer` (paid), `user2` team B (`pending_billing`), the `seed_apply rich` teams for
  postpaid, enterprise, failed payment, LTD (only when the PR touches billing: it is a heavy seed).
- Guard on both sides: UI blocks the free/limited actor, and the route refuses it when called directly.
- Thresholds that show a number to customers: would normal usage trip them (false positives)?

## web-server-config · php-fpm · site-lifecycle · provisioning · backups-db (real servers)

- **Matrix**: every stack the code map lists (nginx, ols, docker); 24.04 template servers for speed, 26.04 or
  `fresh: true` when provisioning is involved; Hetzner 22.04/ARM only when packages or the OS are.
- **Density**: at least two sites on one server; the change must not touch the other site's config, pool or files
  (checksums before/after with `server_exec`: `sha256sum` of vhosts, pools, `.htaccess`).
- **Effective value through the web server**: a probe file in the docroot read with `site_http body: true`; the
  CLI is a different SAPI (`php -i` is not the FPM pool).
- **Was it applied?**: a config written but the service never reloaded is the classic miss. Compare service PID /
  start time, and count reloads in `/var/log/php<v>-fpm.log`.
- **Availability during the operation**: `site_http times: 50` on every site of the server, started just before
  the action; non-200 counts and p95.
- **Adversarial server state** (plant it with `server_exec`, note it in `facts.json`): a hand-edited config, a
  customer's own override, a file mode 600 / root-owned / `chattr +i`, a deleted directory the change depends on,
  a stopped service, an apt lock, an invalid config already present. Is the failure mode worse than `dev`'s? Is
  the customer told?
- **Task output**: `task_log` for every task the action started; the on-server `/root/.xcloud/<id>.out` holds
  what the DB does not.
- **DB engines** for backups/DB work: mysql8, mysql84, maria.

## jobs-async

- **Double-submit**: click or call the trigger twice quickly; one operation, no deadlock.
- **Interrupted**: leave the page mid-operation, come back: the final state is correct and shown.
- **Stale page**: open the page, change the state elsewhere (`app_call`), act on the stale page without reload.
- **Failure path**: make the job fail (a planted server state) and confirm the UI leaves "processing".

## data-migration

- Run against rows that exist before the migration (the preview's seeded data, or rows you create on `ci/dev`'s
  code and then compare): nulls, old enum values, legacy meta formats, soft-deleted rows.
- Rollback where the PR says it is safe.

## ui-only (and the UI part of any PR)

Checks on the **running page**, not on the `.vue` source:
- **Expectation**: does each changed control do what its label says? (an "Apply" that saves permanently, an
  "Active" badge on a provisioning resource)
- **Feedback**: loading, success and failure states are visible for every action; long operations show progress.
- **Errors**: trigger each error you can; is the message specific and actionable, or "Something went wrong"?
- **Destructive actions**: a confirmation that names the resource; permanence stated.
- **States**: empty list, one item, many (pagination), long names, mobile viewport (`page_check viewport: "mobile"`).
- **Dark mode**: `page_check color_scheme: "dark"` when colours changed.
- **Console**: `page_check` / `lab-flow.mjs` report uncaught errors and failed requests; any is a finding.
- **Language**: see `references/language.md` (static audit + live checks in de, a CJK and a complex script,
  emails in the team's notification language).

## Inputs (forms and API bodies the PR adds or changes)

Empty, whitespace, at the documented limit and one over, 500+ characters, unicode/emoji, `<script>` and quotes
(rendered escaped afterwards?), a value valid for another stack or type. Expect a specific 422/validation message,
never a 500 and never silent acceptance.
