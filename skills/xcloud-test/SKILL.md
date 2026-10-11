---
name: xcloud-test
description: Use when deep-testing an xCloud pull request on real servers and real roles in the xcdev lab — QA that hunts for bugs the author cannot see (wrong expectations, neighbour regressions, existing-customer state, role/IDOR leaks, silent job failures, untranslated or broken text in the 20 languages) with spec-first and black-box testing and a before/after comparison against staging `dev`. Trigger on a PR number with "test", "QA", "verify", "break it", "multi-role", "IDOR", or "staging". Falls back to a plain SSH staging server when the lab is unavailable. Do NOT use for writing Pest/Playwright tests, code review without running anything, one-check-at-a-time live verification (use kaztrack-live-verify), or a quick merge-safety pass (use xcloud_qa).
user-invocable: true
disable-model-invocation: false
argument-hint: "[PR-number] [interactive]"
---

# xcloud-test — find the bugs the PR author cannot see

The author ran the unit tests, and the PR code passes them. That proves the code does what the code says,
not what customers need. This skill finds the gap. Four rules come before any procedure:

1. **The expected result never comes from the PR's code.** It comes from the issue, the PR's promises, the
   product docs, support history, how `dev` behaves today, and common sense. An agent that has not read the diff
   writes it down first (`references/oracle.md`). The code shows where to test, not what should happen, and a
   result is judged only by observable behaviour (screen, response, email, server state), never by reading code.
   One explorer tests with no code access at all (`references/blackbox.md`).
2. **Before/after, not after-only.** Reproduce the problem on staging `ci/dev` (plain `dev`), then show the
   preview behaves differently. A fix you never saw broken is PARTIALLY VERIFIED at best.
3. **A success screen or HTTP 200 is not proof.** Every check runs the sentinel (`scripts/sentinel.sh`): new
   `laravel.log` errors, new `failed_jobs`, the tasks the action started and their exit codes. A green toast
   with a failed task is a FAIL.
4. **Real servers, real roles, real paths.** Lab servers provisioned by the PR's own app, seeded accounts
   (`as`), requests through the site's own web server. Never a hand-made `Server::create()` row with a fake IP.
5. **Every check leaves a screenshot.** Text excerpts prove the server side; the screenshot shows what the
   customer sees. Each PASS/FAIL carries at least one `kind: "screenshot"` evidence entry of the dashboard page
   that reflects the result (the setting, the site/server page, the task list, the error), on the preview and,
   for `baseline` checks, on `ci/dev`. Only a check with nothing visible in any page may skip it, with
   `no_screenshot: "<why>"` in its result. `results.py merge` lists every gap under `screenshot_warnings`
   (it does not block): take the missing shots, or confirm the check truly has nothing to show.

Lab tool names below are the xcdev MCP's (`mcp__xcdev__*`, load with ToolSearch). `references/lab.md` maps
each need to a tool and lists the lab traps. Without lab access, use `references/staging-fallback.md`.

## Files

| File | Loaded by | Purpose |
|---|---|---|
| `references/oracle.md` | oracle agent | spec-first expected behaviour, without the diff |
| `references/code-map.md` | code-map agent | entry points, consumers, surfaces, risk class |
| `references/probes.md` | main (Phase 2) + executors | what to try, by risk class: where real bugs hide |
| `references/blackbox.md` | black-box explorer | customer-side exploratory testing, no code access |
| `references/language.md` | main + `[lang]` executors | the 20 languages: static audit, live checks, emails |
| `references/lab.md` | main + executors | xcdev tool map, accounts, fixtures, traps, cleanup |
| `references/executor.md` | executor agents | how to run a check, sentinel, evidence, result schema |
| `references/report.md` | main (Phase 6) | report shape, verdict rules |
| `references/xcloud-feature-map.md` | code-map agent | UI page hints (confirm in `routes/` before use) |
| `references/staging-fallback.md` | main, only without the lab | SSH staging path |
| `scripts/sentinel.sh` | executors (via `cp_exec`) | before/after log, failed-job and task snapshot |
| `scripts/lab-flow.mjs` | executors | browser flows `page_check` cannot do (hover, upload, read, video) |
| `scripts/lang_audit.py` | main (Phase 1) | strings the PR adds: missing translations, placeholders, hardcoded text |
| `scripts/results.py` | main | merge executor results, validate, render the report |

Run state lives in `~/.xcloud-qa/pr<N>/` (outside the repo, so `git status` stays clean): `spec.md`, `codemap.md`, `plan.md`, `facts.json`,
`results/*.json`, `evidence/`, `report.md`. The main session keeps summaries only; sub-agents return ≤ 200 words.

---

## Phase 0 — Intake and deploy (in parallel)

1. `gh pr view <N> --json number,title,body,state,headRefName,baseRefName,headRefOid,files,closingIssuesReferences`
   and `gh api repos/xCloudDev/xCloud/compare/<baseRefName>...<headRefOid> --jq '"behind=\(.behind_by)"'`.
   Not found → stop. CLOSED (not merged) → ask. MERGED → test it with `env_create {ref: <merge commit>}` and say so.
   **Baseline = the PR's base**: into `dev` → staging `ci/dev`; into `master` (hotfix) → your own
   `env_create {workspace: "<yours>", env: "base<N>", ref: "master"}` (start it now, it takes 3-10 min).
2. **Superseded?** `git log origin/dev -S '<a key line the PR adds>' --oneline`. Already on `dev` → report that
   and stop unless the user wants the rest checked.
3. `lab_list {mine: true}`: remove your own leftovers from earlier runs first (ask if they may belong to work in
   progress). `env_status {environment: "ci/pr-<N>"}`: note `used_by`.
4. **Deploy now, in the background**: `preview_deploy {pr: N, mode: "merged_onto_dev"}` (PR into `dev`, what
   would land) or `mode: "head"` (hotfix into `master`, or the user asks). `needs_confirmation` → tell the user
   who is on it; deploy with `confirm_shared: true` only with their OK. Keep the job id; `job_wait` it later.
5. Spawn in **one message**:
   - **Oracle agent**: prompt = `references/oracle.md` + PR number. It must not read the diff.
   - **Code-map agent**: prompt = `references/code-map.md` + PR number.
6. When the deploy job is done: `env_status` again. Confirm `deploy.lab_build.sha` is the commit you meant.
   Print `[Phase 0] PR #N <title> — preview <sha> (<mode>), <behind> behind dev`.

## Phase 1 — Reconcile spec and code (main session)

Read `spec.md` and `codemap.md` (both short by design). Build a table of **suspects**: every place where
- the spec expects something the code does not do (missing case, missing surface, missing role),
- the code does something the spec never asked for (changed default, a new side effect, a widened query),
- the PR description promises something ("graceful", "only affects X", "preserves") — each promise is a claim,
- a consumer or neighbour of the changed code is not mentioned in the PR at all.

Suspects are hypotheses, not findings. Each becomes at least one check in the plan.

Run the language audit (free, static): `python3 ~/.claude/skills/xcloud-test/scripts/lang_audit.py --base
origin/<base> --head origin/pr/<N>` (fetch `refs/pull/<N>/head` first). Every customer-visible finding becomes a
`[lang]` check (`references/language.md`).

## Phase 2 — Plan (one user stop)

Load `references/probes.md`. Write `plan.md`: a numbered list of **checks**, each one line plus fields:

```
C-03  [role] user2 (team B) opens team A's server backups page            env: preview
      expect (spec S-4): 403 or redirect, no data       baseline: same on ci/dev
      how: page_check as user2 + app_call GET /api/server/<A server id>/backups as user2 (id or uuid: whatever the route binds)
      server: q<N>-ng      sentinel: yes      source: suspect X-2
      shot: /server/<uuid>/backups as user2 (preview + ci/dev)
```

Every check names its `shot:`: the page (and account) whose screenshot proves the result. Server-side checks
name the dashboard page that reflects that state; write `shot: none — <why>` only when no page shows it.

Format matters (`scripts/results.py` parses it): each check starts `C-<nn>  [<tag>]`; tag the PR's primary
claim `[primary]` and give each suspect's check `source: suspect …`; those decide the verdict.

Order: (1) the primary claim, reproduced on `ci/dev` and then on the preview; (2) every suspect; (3) every
entry point and surface from the code map; (4) the probe classes `probes.md` selects for this PR's risk class;
(5) `[lang]` checks: the audit's findings plus, for any PR that changes what customers read, one long language
(de), one CJK (ja or sc) and one complex script (th/hi/bn) on the changed pages, and emails it sends.
Merge checks that need the same setup. No quota: a 1-file copy fix may need 4 checks, a provisioning change 25.

Show the user one message: the suspects table, the check list (one line each), the server matrix you will
create, and **at most 3 questions** whose answers change what is tested (intended behaviour the spec could not
settle). Ask for `go`, edits, or answers. If the user passed `interactive`, they will run browser steps
themselves; executors then guide them (see `references/executor.md` → Interactive).

## Phase 3 — Environment

From the plan's matrix, in one go (details and limits in `references/lab.md`):
- **Servers**: `servers_create` in `ci/pr-<N>` (names `q<N>-<short>`), one per stack/release/DB the plan needs;
  `fresh: true` when the PR touches provisioning; Hetzner only for 22.04/ARM (costs money: say so).
  **Baseline**: the same set (or the subset the primary claim needs) in the baseline environment from Phase 0
  (`ci/dev`, or your `master` environment for a hotfix). `job_wait` each job.
- **Sites**: `sites_create` (wordpress, php, laravel). Docker apps and one-click types: through the app's own route
  with `app_call` (see lab.md).
- **People**: seeded accounts (`user1` team-admin of team A, `user2` owner of team B, `support1/2`, `admin`) plus
  `fixture_create` `team_member` (server-admin / site-admin) and `active_customer` when roles are in play;
  `api_token` per account for Public API checks.
- **Customer state** the plan asks for (old provisioning, hand edits, a second site, a stopped service): set it up
  now on the server with `server_exec`, recorded in `facts.json` as what you changed.
- **Confirm in the app**: every server and site id you will use exists in that environment's app
  (`app_tinker`: id, uuid, team_id, status). `lab_list` can list servers the app no longer has.

Write `facts.json`: `pr`, `tested_line` (the one-line "Tested: …" for the report), environments + shas, every
server (ref, app id, uuid, stack, release, db, team), every site (ref, id, uuid, name), every account and role,
token handles (never token values), and what state you planted.

## Phase 4 — Execute

**Split agents by server, never by topic**: checks that restart or rewrite services on one server must run in one
agent, in order. Checks with no server side (UI, API, roles) can be split freely. At most 4 agents per message;
send the next batch when one returns.

Each executor prompt = `references/executor.md` + its check ids from `plan.md` + `facts.json` path + the spec
excerpt for its checks. `[lang]` checks also get `references/language.md`.

In the first batch, also spawn the **black-box explorer**: prompt = `references/blackbox.md` + PR number + the paths
of `spec.md` and `facts.json` only (never the code map, plan or suspects). Give it its own server or site, or a
UI-only scope, so it cannot collide with an executor's server. Skip it only when the PR changes nothing a
customer can observe (say so in the report). Each writes `results/<check-id>.json` and returns ≤ 200 words. Print one line per
returning agent: `[C-03] FAIL — user2 reads team A backups (200, 3 rows)`.

After all return: `python3 ~/.claude/skills/xcloud-test/scripts/results.py merge ~/.xcloud-qa/pr<N>`. It flags
missing result files, PASS/FAIL without evidence,  PASS results whose sentinel shows new errors, FAILs without
repro steps, and anything that looks like a secret. Send each problem back to the agent that owns the check (or
fix the file yourself when it is clerical) until `merge` exits 0. Then go through `screenshot_warnings`: send
each one back for a shot unless the check really has no page that shows its result.

## Phase 5 — Skeptic pass

One agent, prompt: "You are the PR author's toughest reviewer and its most skeptical tester. Read
`~/.xcloud-qa/pr<N>/spec.md`, `plan.md`, `results/`. (a) Which spec claims or suspects have no check, or only a
check whose evidence would also pass on broken code? (b) Pick the two PASS results with the weakest evidence
and re-run them a different way (another role, another stack, another language, through the API instead of the
UI, twice in a row). (c) For each FAIL, could it be an environment artefact (a lab trap from `references/lab.md`, a wrong
id, the shared servers)? Re-check it once. Write results like an executor; return ≤ 200 words."

Add any new checks it proposes to `plan.md` and run them (Phase 4 rules). One skeptic round, not a loop.

## Phase 6 — Report

`python3 ~/.claude/skills/xcloud-test/scripts/results.py report ~/.xcloud-qa/pr<N>` renders `report.md` from the results (shape and verdict
rules: `references/report.md`). Screenshots must be viewable by the reader: publish `page_check` shots
(`publish: true`, or `evidence_publish {id}` afterwards) and upload local `lab-flow.mjs` / `evidence/*.png` files with
`scripts/upload_screenshots.py`; put the public URLs in the results before rendering, so the report embeds them. Read it, fix the prose (summary, what this PR changes vs pre-existing), and
check every screenshot before it is shared: no secret on it. Then ask where it goes: PR comment (one comment,
the compact form), KazTrack doc (full form, PR comment links to it), or local only. Never touch PR labels.

## Phase 7 — Cleanup (always, also after a failed run)

`remove {servers: [...]}` for every `q<N>-*` server in `ci/pr-<N>` **and** `ci/dev`; `fixture_remove` for each
fixture; `api_token_revoke` / `bot_token_revoke` for each token; `lab_list {mine: true}` shows none of this run's
resources. Then `report_friction` once per lab problem that cost you time (the lab team reads them). Print
`[Phase 7] cleanup: <n> servers, <n> fixtures, <n> tokens removed`.

---

## Verdict (details in `references/report.md`)

- **NEEDS CHANGES**: the primary claim fails; behaviour differs from what the PR or issue promises; a regression
  versus `dev`; a role sees or changes what it must not; a task fails or an error is logged behind a success
  screen; a logic flaw that makes the feature mislead users, even if the code "works".
- **PARTIALLY VERIFIED**: a primary check could not run, or the bug could not be reproduced on `dev` first.
- **READY TO MERGE**: every primary check and suspect passed with evidence, no failure mode worse than `dev`'s.
- Problems that exist on `dev` too are **pre-existing findings**, listed separately, not PR failures, unless the
  PR claims to fix them or makes them worse.
