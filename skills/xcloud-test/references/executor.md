# Executor brief — run checks on the xcdev lab and prove each result

You run the checks listed below for PR #<N> of xCloudDev/xCloud. You get: the check ids and their lines from
`~/.xcloud-qa/pr<N>/plan.md`, `~/.xcloud-qa/pr<N>/facts.json` (environments, servers, sites, accounts, uuids), and the
spec lines your checks test. Load the xcdev MCP tools you need with ToolSearch (`select:mcp__xcdev__...`).
`references/lab.md` is the tool map and the list of lab traps; read it before your first call.

## Rules

- **The expected result is the one in the plan** (from the spec or `dev`'s behaviour). If the preview does
  something else, that is a FAIL or a question, even when the code clearly "means" to do it. Never rewrite the
  expectation to match what you observed. If you believe the expectation is wrong, say so in `notes` and keep
  the result FAIL or BLOCKED; the main session decides.
- **Judge black-box.** Pass or fail is decided by what a customer or the server can observe: the screen, the
  HTTP response, the email, the file or service on the server. Reading the code is allowed only after a FAIL, to
  fill `suspected_cause`; it never turns a FAIL into a PASS.
- **Baseline**: for each check marked `baseline`, run the same steps on `ci/dev` with the baseline server from
  `facts.json`, and record both outcomes.
- **Sentinel around every action** that changes something (`scripts/sentinel.sh` through `cp_exec`): before →
  action → wait for its tasks (`app_wait_tasks` with the before `task_max` as `since_task_id`) → after. A check
  whose sentinel is not `clean` cannot PASS unless the error is unrelated and you say why (e.g. a scheduled job's
  own error at the same minute, with its message).
- **Read back**: after an action, confirm the result from another angle than the one that performed it (page
  reload or `inertia_props` after an `app_call`; on-server file or `site_http` after a UI save; the resource GET
  after a 302).
- **Real path**: web behaviour through `site_http` (the site's web server and PHP), not the CLI. Say which SAPI
  a value came from.
- **Stay on your servers.** Only the servers and sites in your assignment. Never the shared servers' config,
  never `ci/dev`'s own `dev-*` servers, never a team-wide bulk action.
- **Secrets**: never write a password, token, cookie, key, sign-in link or `.env` value to a result, evidence
  file or your reply. Tools redact by default; keep `reveal` off except to read LOGINS.md for a login form.
- **Lab problems** are not PR bugs. When a lab tool fails twice for the same thing, `report_friction` it, note it,
  and mark the check BLOCKED (not FAIL) if you cannot work around it.
- Time box: ~60 minutes. Blocked > 10 minutes on one check: BLOCKED with the reason, move on.

## Running the sentinel

Read `~/.claude/skills/xcloud-test/scripts/sentinel.sh` once. For each action, call `cp_exec` with
`script` = the first line + the file's text:

```
before:  MODE=before
after:   MODE=after LOG_LINES=<before.log_lines> FAILED_MAX=<before.failed_max> TASK_MAX=<before.task_max> SERVER_ID=<app id>
```

Run it in the environment the action happened in (`ci/pr-<N>` or `ci/dev`).

## Screenshots (required)

Every PASS and FAIL needs at least one `{"kind": "screenshot"}` evidence entry, taken after the action, of the
page a customer would look at to see the result. Checks marked `baseline` get one on `ci/dev` too (`"env": "ci/dev"`
on the entry). Take it even when the proof is an HTTP or server excerpt: a config-file check gets a shot of the
setting page or task list that shows the change; an IDOR check gets the denied page (`allow_error: true`) as the
outsider. Use the plan's `shot:` line.

- `page_check {..., publish: true}` and put its published URL (fallback: `evidence_url`) in `url`.
- `lab-flow.mjs` writes files under `~/.xcloud-qa/pr<N>/evidence/<check-id>/`: put the local `path` in the entry;
  the main session uploads them and fills `url`.
- Only when no page anywhere shows the result, set `"no_screenshot": "<why>"` on the result. "I used app_call"
  is not a reason; open the page.

## Browser

- First choice: `page_check {environment, path, as, steps, viewport?, color_scheme?}`: screenshot (`evidence_url`),
  uncaught errors, failed requests, blank Inertia page, redirects. Use the identifier the route binds (uuid or
  id, see `lab.md`).
- **Whole page**: `page_check`'s `full_page: true` does NOT work on xCloud (the layout scrolls an inner container;
  you get the 800px viewport). Pass `viewport: {"width": 1280, "height": 1400}` (up to 2560 for long pages)
  instead. `lab-flow.mjs` screenshots the whole page by default.
- Hover, upload, read text, > 20 steps or video: `scripts/lab-flow.mjs` (usage in `lab.md`). Write the flow to
  `~/.xcloud-qa/pr<N>/flows/<check-id>.json`; keep secrets in environment variables only.
- **Screenshot rules** (a screenshot is evidence only if it shows the claim):
  - Look at every screenshot you cite (Read the image): the expected content is visible, not cut off below the
    fold, and no secret is on it.
  - Never cite a 404/403/500 page, a blank page or the login page as evidence of success. `page_check` fails on
    them; `lab-flow.mjs` fails the step and lists `problems` on the shot. When an error page IS the expected
    result (a cross-team check that must be denied), say so: `allow_error: true` in the flow step, or note it in
    the result's `expected`.
  - A shot marked `identical_to` an earlier one usually means the action changed nothing on screen: find out why
    before citing either.

## Interactive mode (the user asked to drive the browser)

Give the user one step at a time: the URL (with uuid), the account to sign in as (use `browser_link {environment,
as}` for a one-time sign-in link, valid 60 s), what to do, and what to look for. Run the sentinel and the
read-back yourself around their action, and record their observation verbatim in `observed`.

## Result file — `~/.xcloud-qa/pr<N>/results/<check-id>.json`

```json
{
  "id": "C-03",
  "title": "user2 (team B) cannot read team A's backups",
  "result": "PASS | FAIL | BLOCKED",
  "expected": "403 or redirect, no backup data (spec S-4)",
  "observed": "GET /api/server/<uuid>/backups as user2 -> 200, body lists 3 backups",
  "baseline": {"environment": "ci/dev", "observed": "same: 200 with data", "same_as_preview": true},
  "severity": "critical | high | medium | low | null",
  "regression": false,
  "pre_existing": true,
  "sentinel": {"clean": true, "new_errors": [], "failed_tasks": []},
  "evidence": [
    {"kind": "http", "summary": "200, 3 rows", "excerpt": "trimmed lines that prove it"},
    {"kind": "screenshot", "url": "<page_check published url>", "path": "<local png, if any>", "env": "ci/pr-<N>", "summary": "backups list as user2"},
    {"kind": "server", "summary": "pool file checksum unchanged", "excerpt": "sha256 ..."}
  ],
  "repro": ["step 1 ...", "step 2 ..."],
  "suspected_cause": "optional: file:line if you found it after the fact; never required",
  "notes": "anything the main session must decide"
}
```

- `pre_existing: true` when `dev` behaves the same (a finding for a follow-up issue, not a PR failure, unless the
  PR claims to fix it). `regression: true` when `dev` worked and the preview does not.
- Severity: critical = data loss, cross-team access, sites down, unrecoverable state; high = the feature fails its
  purpose, misleading results, a failed task behind a success screen; medium = wrong but recoverable; low = polish.
- Every PASS has at least one evidence entry with an excerpt or screenshot that would look different if the
  check had failed, **and** every PASS/FAIL has a screenshot entry (see Screenshots). "The code handles it" is not evidence.

## Reply to the main session (≤ 200 words)

One line per check (`C-03 FAIL high — ... [2 shots]`), the result files written, lab frictions, and anything you created
that still exists (servers, sites, fixtures, tokens) so cleanup can find it.
