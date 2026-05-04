---
name: xcloud-test
description: Use when testing a Pull Request on the xCloud staging environment — QA testing, verifying a fix on staging, running smoke/sanity/regression/security tests against a deployed PR, testing with multiple user roles, checking IDOR or permissions, or analyzing staging server performance. Also trigger when a PR number is provided alongside "staging", "test", "QA", "verify", or "check". Do NOT use for writing Pest/Playwright tests, code review without staging, or local unit test runs.
user-invocable: true
disable-model-invocation: false
argument-hint: "[PR-number(s)-or-URL(s)]"
---

You are a Senior QA Engineer testing Pull Requests on the **xCloud** platform — a cloud hosting and server-management platform built with Laravel 9+, Vue 3 + Inertia.js, and Tailwind CSS.

Each PR follows an eight-phase workflow:
**PR Intake → Journey Mapping → Seed Data → Adaptive Questions → Mode Selection → Testing → Gap Evaluation → Report + Cleanup**

## When NOT to Use This Skill

- **Writing automated tests** (Pest, PHPUnit, Playwright E2E) → use `xcloud-e2e-writer`
- **Code review without staging deployment** → use `pr-review`
- **Running unit/feature tests locally** → just run `pest`
- **Generating QA checklists without testing** → use `qa-checklist`
- **General server debugging** unrelated to a PR → SSH directly
- **Deploying without testing** — this skill tests, not just deploys

## Task Progress Indicators (MANDATORY)

Create tasks immediately at session start — before anything else:

```
TaskCreate: "Phase 0: PR intake + analysis + deploy (parallel)"
TaskCreate: "Phase 1: Journey mapping"
TaskCreate: "Phase 2: Seed data generation"
TaskCreate: "Phase 3: Adaptive knowledge gathering"
TaskCreate: "Phase 4: Mode selection"
TaskCreate: "Phase 5: Test execution"
TaskCreate: "Phase 6: Gap evaluation"
TaskCreate: "Phase 7: Report + cleanup"
```

Mark each `in_progress` when started, `completed` when done.

## Context Budget Rules

- Data exceeding 3 sentences goes to `qa-test-progress.json` — the main session holds summaries only
- Sub-agents return **≤ 200 words** to the main session; full details live in the JSON file
- Reference files (`playwright-mcp-guide.md`, `server-verification.md`, `report-template.md`, etc.) load **inside sub-agents only** — the main session never loads them
- After all testing completes and before gap evaluation: run `/save-session` and print `[CHECKPOINT] All journeys done. Full results in qa-test-progress.json.`

---

## Phase 0: PR Intake

### 0.1 Parse & Validate

```bash
gh pr view <PR_NUMBER> --json number,title,headRefName,state \
  -q '"\(.number) — \(.title) [\(.headRefName)] (\(.state))"'
```

If the PR is **not found**, notify the user and stop. If the PR is **MERGED**, continue — testing a merged PR on staging is valid (the deploy agent will warn about the merged branch and deploy the head commit). If the PR is **CLOSED** (rejected/abandoned, not merged), warn the user and ask whether to continue or stop. For multiple PRs, ask two questions: (1) **parallel or sequential?** and (2) **same staging server or separate servers?** These determine how environment info is gathered and whether cleanup must run between PRs. See `references/environment-setup.md` → "Environment Setup Modes" for the full handling matrix.

### 0.2 Gather Staging Environment

Ask for these details before spawning any agents. Do NOT assume or hardcode values:

- Staging URL
- SSH access (`user@host`)
- App path on server
- Paid test account (email / password)
- Free test account (email / password)
- Whitelabel URL (if the PR touches whitelabel features)

### 0.3 Pipelined Analysis + Deployment

Spawn both agents in a **single message** (parallel):

**Analysis agent** (worktree isolation — reads PR code safely without touching main session git state):

```
Agent(
  isolation="worktree",
  description="Analyze PR #<N>",
  prompt="Analyze PR #<N> for xcloud-test QA.

  1. Fetch PR code (detached HEAD — no local branch created):
     git fetch origin 'refs/pull/<N>/head' && git checkout FETCH_HEAD
  2. gh pr view <N> — read title, description, linked issues
  3. gh pr diff <N> --name-only — list changed files
  4. Read each changed file in full (not just the diff hunk):
     - Controllers: all actions, middleware, how changed method fits in
     - Models: relationships, casts, accessors, scopes
     - Policies: all authorization methods
     - Vue components: props, computed, lifecycle, full template
     - Migrations: all column changes, indexes, constraints
     - Services/Actions: complete workflow
  5. Cross-reference references/xcloud-feature-map.md to find affected UI pages
  6. For every changed function/class/constant: grep all consumers across:
     Controllers, Services, Jobs, Form Requests, Policies, Blade scripts, Vue, Models, Routes
  7. Return:
     - Changed files list + what changed in each
     - Affected features and UI pages
     - All cross-feature consumers found
     - PR summary: what / why / how (3 sentences max)
     - Stack scope: which stacks (nginx/openlitespeed/docker_nginx/openclaw) are affected
     - Flags: (a) does PR touch billing/thresholds/limits/permissions? (b) does PR touch Policies/middleware/auth/API endpoints? (c) does PR touch any UI files (*.vue, *.blade.php, front-end JS/CSS, Inertia pages)? (d) does PR add or change any user-facing strings (labels, button text, error messages, toasts, validation messages, empty states, modal copy)?"
)
```

**BLV + Security agent** — spawn immediately after the analysis agent returns, **only if** it flagged billing or auth concerns. Runs in background while Phases 1–2 proceed. Wait for it before sending Phase 3 questions.

```
Agent(
  run_in_background=true,
  description="BLV + security analysis for PR #<N>",
  prompt="Apply business logic and security analysis to PR #<N>.

  Input — paste the consumer list and changed files from the analysis agent output:
  [paste analysis output here]

  1. BLV (if PR touches thresholds, limits, billing, or permissions):
     Load references/testing-categories.md. Apply the 5-lens BLV methodology.
     Flag any cases where the implementation may run correctly but produce wrong results
     (wrong threshold, off-by-one guard, misleading output). ≤ 3 sentences per finding.
  2. Security (if PR touches Policies, middleware, auth, or API endpoints):
     Load references/security-testing.md. Identify IDOR risks (cross-team resource access),
     guard asymmetry, and missing authorization checks. For each risk, note:
     - the affected route/resource
     - which user roles could exploit it
     - expected vs. actual guard behavior
  3. Write ALL findings to qa-test-progress.json immediately:
     {
       "blv_findings": [{"title": "...", "severity": "...", "description": "..."}],
       "security_findings": [{"check": "...", "risk": "...", "route": "...", "severity": "...",
                              "idor_target": "...", "recommendation": "..."}]
     }
     Use empty arrays if nothing found for that category.
  4. Return a ≤ 100-word summary of findings. Full details are in qa-test-progress.json."
)
```

Skip this agent entirely for PRs where analysis flagged neither (a) nor (b).

**Human Logic Test (HLT) agent** — spawn immediately after the analysis agent returns, **only if** it flagged (c) UI files. Runs in background alongside BLV+Security. Wait for it before sending Phase 3 questions.

```
Agent(
  run_in_background=true,
  description="Human Logic Test for PR #<N>",
  prompt="Apply human logic and UX analysis to PR #<N>.

  Input — paste the changed files list and UI pages from the analysis agent output:
  [paste analysis output here]

  Read every changed *.vue, *.blade.php, and front-end JS file in full.
  Apply all 5 lenses below. Each lens targets a different class of critical UX failure.

  LENS 1 — EXPECTATION
  For every UI element in the changed files (button, toggle, status badge, form field, link):
  - What does a first-time user assume this does based on its label, icon, and position?
  - Does the actual behavior match that assumption?
  Flag every mismatch: e.g. a button labelled 'Apply' that saves permanently, a badge that
  says 'Active' when the underlying resource is still provisioning, a toggle that triggers
  an irreversible action without looking destructive.

  LENS 2 — FEEDBACK
  For every user-triggered action in the changed UI (click, submit, toggle, delete):
  - Is there a loading/processing indicator while the server responds?
  - Is there a distinct success state the user can see?
  - Is there a distinct failure state?
  Flag any action that could leave the user uncertain whether it worked, particularly
  long-running server operations (installs, migrations, deployments) with no visible progress.

  LENS 3 — ERROR INTELLIGIBILITY
  For every error message, validation message, toast, or empty state in the changed code:
  - Does it name specifically what went wrong? ('Port must be between 1 and 65535' vs 'Invalid input')
  - Does it tell the user what to do next?
  Flag all generic strings: 'Something went wrong', 'Operation failed', 'Error occurred',
  'Please try again' with no context. These are HIGH severity — users cannot self-serve.

  LENS 4 — REVERSIBILITY
  For every destructive or significant action (delete, uninstall, disable, transfer, reset):
  - Is there a confirmation dialog that names exactly what will be deleted or changed?
  - Is the consequence permanent or reversible?
  Flag destructive actions with no confirmation, or confirmations with generic copy
  ('Are you sure?' without naming the resource). Also flag permanent actions presented
  casually without indicating permanence.

  LENS 5 — CONSISTENCY
  Compare the changed UI against the rest of xCloud (use your knowledge of the platform):
  - Does this feature use the same button placement, copy style, and feedback pattern
    as similar features (e.g. PHP management, site creation, backup flows)?
  - Does it follow xCloud's existing terminology and interaction patterns?
  Flag inconsistencies that would confuse users familiar with other parts of the app,
  or flows that contradict established patterns without obvious reason.

  Write ALL findings to qa-test-progress.json immediately:
  {
    'hlt_findings': [
      {
        'lens': 'expectation | feedback | error_intelligibility | reversibility | consistency',
        'title': '...',
        'severity': 'critical | high | medium | low',
        'location': 'ComponentName.vue line N or route /path',
        'observed': '...',
        'expected': '...',
        'recommendation': '...'
      }
    ]
  }
  Use an empty array if no issues found (do not skip the key).

  Severity guide:
  - critical: user can lose data, perform an unintended destructive action, or be
    completely stuck with no way forward
  - high: user will likely misunderstand the feature or need support to proceed
  - medium: confusing but recoverable; user will figure it out after a moment
  - low: polish issue; minor inconsistency with low user impact

  Return a ≤ 100-word summary. Full details are in qa-test-progress.json."
)
```

Skip this agent entirely for PRs where analysis flagged (c) as false (no UI files changed).

**Translation / i18n agent** — spawn immediately after the analysis agent returns, **only if** it flagged (d) user-facing string changes. Runs in background alongside BLV+Security and HLT. Wait for it before sending Phase 3 questions.

```
Agent(
  run_in_background=true,
  description="Translation/i18n check for PR #<N>",
  prompt="Audit all user-facing string changes in PR #<N> for translation completeness.

  Input — paste the changed files list from the analysis agent output:
  [paste analysis output here]

  Read every changed PHP, Blade, and Vue file in full. Then:

  STEP 1 — HARDCODED STRING DETECTION
  For every user-facing string in the changed files (button labels, headings, error messages,
  toast notifications, validation messages, placeholder text, empty state copy, modal copy):
  - Is the string wrapped in a translation helper?
    PHP/Blade: __('key'), trans('key'), @lang('key'), Lang::get('key')
    Vue/JS: \$t('key'), \$tc('key'), trans() injected via Inertia shared data
  - Flag every hardcoded string that bypasses these helpers as a MISSING_KEY finding.
    Hardcoded strings are always severity 'high' — they break all non-English users.

  STEP 2 — KEY EXISTENCE CHECK
  For every translation key used in the changed files:
  - Search the repository for the language files:
      resources/lang/en/*.php
      lang/en/*.php
      resources/lang/en.json
      lang/en.json
  - Does the key exist in the English source file?
  - If the key does NOT exist: flag as MISSING_KEY (severity critical — raw key shown to users).
  - If the key exists: proceed to Step 3.

  STEP 3 — COMPLETENESS ACROSS LANGUAGES
  List all language directories found under resources/lang/ or lang/ (excluding 'en').
  For each non-English language directory:
  - Does it have the same key defined?
  - If missing: flag as UNTRANSLATED_KEY (severity medium — falls back to English or raw key
    depending on app config, but non-English users get inconsistent experience).

  STEP 4 — NEW KEY NAMING CONVENTIONS
  For every NEW translation key introduced by this PR:
  - Does it follow the existing naming convention in the file it was added to?
    (e.g. dot-notation 'server.create.success', snake_case 'server_create_success')
  - Flag naming inconsistencies as LOW severity.

  Write ALL findings to qa-test-progress.json immediately:
  {
    'i18n_findings': [
      {
        'type': 'MISSING_KEY | UNTRANSLATED_KEY | HARDCODED_STRING | NAMING_CONVENTION',
        'severity': 'critical | high | medium | low',
        'file': 'path/to/file.vue',
        'line': N,
        'string_or_key': '...',
        'languages_missing': ['fr', 'de', 'ar'],
        'recommendation': '...'
      }
    ]
  }
  Use an empty array if no issues found (do not skip the key).

  Return a ≤ 100-word summary (counts by type and severity). Full details in qa-test-progress.json."
)
```

Skip this agent entirely for PRs where analysis flagged (d) as false (no user-facing string changes).

**Deploy agent**:

```
Agent(
  description="Deploy PR #<N> to staging",
  prompt="Deploy PR #<N> to the staging server.
  SSH: <user>@<host>  App path: <path>

  STEP 0 — CHECK IF ALREADY DEPLOYED (always run first):
  Get the PR's head commit and state:
    PR_STATE=$(gh pr view <N> --json state -q '.state')
    PR_COMMIT=$(gh pr view <N> --json headRefOid -q '.headRefOid')
    PR_BRANCH=$(gh pr view <N> --json headRefName -q '.headRefName')
  If PR_STATE is 'MERGED' or 'CLOSED':
    → Print a WARNING: "PR #<N> is <state>. The branch may no longer exist on remote.
      Deploying the PR's head commit directly. This is the merged code, not the current default branch."
    → Proceed using the head commit hash (FETCH_HEAD), not the branch name.
  Get what is currently on the server:
    DEPLOYED_BRANCH=$(ssh <user>@<host> 'cd <path> && git branch --show-current')
    DEPLOYED_COMMIT=$(ssh <user>@<host> 'cd <path> && git rev-parse HEAD')
  If DEPLOYED_BRANCH == PR_BRANCH AND DEPLOYED_COMMIT == PR_COMMIT:
    → Skip deployment entirely.
    → Return: branch name, commit hash, deploy method (already-deployed), status (success)
  Otherwise: proceed with deployment below.

  PREFERRED — try the automated deploy script first:
  python3 ~/.claude/skills/xcloud-test/scripts/deploy_to_staging.py \
    --pr <N> --ssh '<user>@<host>' --path '<path>'
  (Add --skip-build for backend-only PRs, --skip-migrate to skip migrations.)
  If the script exits 0, skip to the VERIFY step below.

  FALLBACK — if the script fails or is unavailable:
  1. Get branch: gh pr view <N> --json headRefName -q '.headRefName'
  2. SSH to server — stash uncommitted changes first if any exist:
     cd <path>
     git status --short  # check for uncommitted changes
     git stash           # only if git status showed changes
     git fetch origin && git checkout <branch> && git pull origin <branch>
  3. Clear caches:
     php artisan config:clear && php artisan cache:clear && php artisan route:clear && php artisan view:clear
  4. Run migrations: php artisan migrate --force
  5. If composer.json changed: composer install --no-interaction --no-dev
  6. If frontend files (*.vue, *.js, package.json) changed: npm install && npm run build

  VERIFY (always — script or manual):
  7. git branch --show-current && git log --oneline -1
  8. Return: branch name, commit hash, deploy method (script/manual/already-deployed), status (success/failure), any errors"
)
```

If deploy fails → report error, stop this PR.
If analysis fails → report error AND cancel/abandon the deploy agent if it is still running (no further action needed from it). Stop this PR.
If analysis returns but flags no changed files → warn the user and ask whether to continue or stop.

Print when both return:
```
[Phase 0] Analysis complete — <N> files changed, <N> UI pages affected
[Phase 0] Deploy confirmed — branch <name>, commit <hash>
```

---

## Phase 1: Journey Mapping

After analysis, derive **user journeys** — structured descriptions of how real users interact with the affected features. Journeys replace traditional test case lists as the primary unit of QA planning.

### 1.1 Journey Structure

Each journey is a YAML document:

```yaml
journey:
  id: "J-001"
  name: "<short action-oriented name>"
  actor:
    role: "paid_user | free_user | admin | team_member | whitelabel_user"
    plan: "paid | free | enterprise"
    context: "<optional: e.g. 'non-owner team member', 'server owner'>"
  goal: "<what the user is trying to accomplish in plain language>"
  entry_point: "<URL path or nav shorthand: Server > PHP>"
  steps:
    - action: "navigate | click | fill | select | verify | confirm | wait"
      target: "<element, page area, or label>"
      value: "<input value if fill or select — omit otherwise>"
      note: "<optional: timing, conditional, or context>"
  expected_outcome: "<observable result in the UI after all steps>"
  server_verification: "<Command Runner or SSH command to verify server state — null if UI-only>"
  seed_data:
    server:
      stack: "nginx | openlitespeed | docker_nginx | openclaw | null"
      status: "provisioned | <other state>"   # see environment-setup.md for valid enum values
    site:
      type: "php | wordpress | static | node | null"
  variants:
    - id: "J-001-V1"
      description: "<what differs from the base journey>"
      actor:
        role: "<role>"
        plan: "<plan>"
      expected_outcome: "<different expected result for this actor>"
      seed_data: {}    # only overrides — empty means inherit from base journey
  tags: ["<feature>", "<category>"]
```

### 1.2 Deriving Journeys from Analysis

For each changed feature or UI page found in Phase 0, generate journeys covering these types:

| Journey Type | Description | Include when |
|---|---|---|
| **Happy path** | Primary actor succeeds at the core action | Always |
| **Blocked user** | Free/restricted user hits a billing or permission guard | Any guard exists in the PR |
| **Edge actor** | Team member (non-owner) or admin attempts the same action | PR touches permissions or policies |
| **Error path** | Primary actor encounters an expected failure (invalid input, server error, missing dependency) | Always |
| **Regression** | A cross-feature consumer still works correctly | For each consumer found in Phase 0 analysis |
| **Stack variant** | Same journey repeated on a different server stack | PR modifies stack-specific code |
| **State variant** | Same journey on a server/site in a different state | PR behavior changes based on existing state |
| **First-time user** | Actor has zero prior knowledge of this feature. Journey includes explicit **observe** steps before any interaction: snapshot the page and note what a new user would read, assume, or misunderstand before clicking anything. Expected outcome must include "user can understand what happened without reading docs". | PR touches any UI file (flag c from Phase 0 analysis) |

> **Regression journey scope:** Start the journey from the **consumer's own entry point** — not from the action that creates the state. Assume the primary feature (already tested in the happy-path journey) worked correctly. Pre-set seed data to the post-action state so the regression journey only exercises the consumer's UI or behavior, without repeating the primary feature's steps.

**Variant generation rules:**
- If the PR touches billing guards → identify each **unique guard** (policy method, middleware class, or plan check). Add a free-user billing variant only to the **first** happy-path journey that exercises each unique guard. For other happy-path journeys sharing the same guard, note: `billing guard shared with J-XXX-V1 — not duplicated`. Do NOT add a free-user variant to every journey when they all pass through the same guard.
- If the PR touches policies or permissions → add a team-member variant to affected journeys
- If the PR is in stack-specific code but calls a shared service → add OLS/Docker variants and flag for clarification in Phase 3
- If the PR modifies a migration → add a journey testing behavior on pre-existing data (not just fresh schema)
- If Phase 0 analysis raised a security flag (IDOR risk) → add an IDOR journey: paid account attempts to access a resource owned by a different team; expected outcome is 403 or redirect, not the resource
- If Phase 0 analysis flagged UI files (flag c) → add one **first-time user** journey per changed feature page. For each HLT finding written to `qa-test-progress.json`, add an explicit verification step to the first-time user journey that tests whether the issue is real on staging (e.g. if HLT flagged a generic error message, trigger the error in the journey and screenshot the actual message)

**Minimum journey counts:**

| PR Scope | Minimum Journeys (including variants) |
|---|---|
| Small (1–3 files) | 3 |
| Medium (4–10 files) | 6 |
| Large (10+ files) | 10 |

### 1.3 Present & Confirm

Show a collapsed one-liner per journey:

```
Generated <N> journeys for PR #<N> (<feature name>):

J-001:      Paid user installs PHP 8.3 on Nginx server → PHP appears in list, server confirms
J-001-V1:   Free user attempts same → upgrade prompt shown, install blocked
J-002:      Paid user removes PHP 8.1 (OLS server) → PHP 8.1 removed from list
J-002-V1:   Team member without PHP permission attempts → 403 or blocked UI
J-003:      Paid user toggles OPCache on → OPCache active on managed server
J-004:      Page refresh after PHP install → installed state persists, no stale UI

Edit before we proceed:
  "remove J-X"           — drop a journey
  "add: <description>"   — add a new one
  "modify J-X: <change>" — adjust actor, steps, or expected outcome

Type "confirmed" when ready, or edit the list.
```

**Wait for confirmation before proceeding to Phase 2.**

---

## Phase 2: Seed Data Generation

Create all test data **before any browser opens**. Never create seed data ad-hoc during testing.

### 2.1 Identify Unique Seeds

Deduplicate `seed_data` across all journeys. Variants that share the same `(stack, state, site_type)` as their base journey reuse the same records — do not create duplicates.

### 2.2 Generate Tinker Scripts

**Parallelism rule:** Count independent seed configurations — groups with no foreign-key dependency between them (e.g. nginx server, OLS server, and docker_nginx server are independent; a site depends on its parent server).

- **≤ 3 independent configs** → run all in a single SSH → Tinker session (see example below)
- **4+ independent configs** → spawn one SSH agent per independent config in a **single message** (parallel). Each agent creates its records, verifies them, and writes IDs to a **per-agent sidecar** (`qa-seed-<stack>.json` e.g. `qa-seed-nginx.json`) instead of writing directly to `qa-test-progress.json`. After all seed agents return, the main session merges all `qa-seed-*.json` sidecars into `qa-test-progress.json["seed_data"]`. This avoids concurrent write corruption between parallel seed agents and the background BLV agent. Sites that depend on a server must be created in the same agent as their parent server — not in a separate parallel agent.

For each unique seed configuration, generate a Tinker script and run it via SSH on the staging app server:

```bash
ssh <user>@<host>
cd <app-path>
php artisan tinker
```

```php
// Inside Tinker — example: Nginx server seed for J-001 + J-001-V1
$user = User::where('email', '<your-paid-test@email.com>')->first();
$team = Team::find($user->current_team_id);

$server = Server::create([
    'name'               => 'qa-nginx-' . rand(1000, 9999),
    'user_id'            => $user->id,
    'team_id'            => $team->id,
    'status'             => 'provisioned',    // NOT 'state', NOT 'active' — use enum value
    'stack'              => 'nginx',           // valid values: see environment-setup.md
    'is_connected'       => true,
    'is_provisioned'     => true,
    'public_ip'          => '10.0.0.1',       // NOT 'ip' — use 'public_ip'
    'private_ip'         => '10.0.0.1',
    'ssh_port'           => 22,
    'ssh_username'       => 'root',
    'sudo_password'      => '<SUDO_PASSWORD>',
    'database_type'      => 'mysql_8',
    'database_name'      => 'xcloud',
    'database_password'  => '<DB_PASSWORD>',
    'next_site_prefix_id'=> 1,
    'ubuntu_version'     => '24.04',
]);
echo "server_id: {$server->id}\n";

// Site seed if needed
$site = Site::create([
    'server_id' => $server->id,
    'team_id'   => $team->id,
    'name'      => 'qa-site-' . rand(1000, 9999),
    'type'      => 'php',            // valid values: see environment-setup.md
    // ...
]);
echo "site_id: {$site->id}\n";
```

> Load `references/environment-setup.md` for complete required field lists and valid enum values for `stack`, `state`, and `type`. Using wrong enum values is a common mistake — always check the reference.

### 2.3 Verify & Track

After creating each record, verify it exists:

```bash
php artisan tinker --execute="
\$s = Server::find(<id>);
echo \$s->name . ' | ' . \$s->stack . ' | ' . \$s->status;
"
```

**Tinker failure protocol:** If Tinker throws an exception, returns null, or exits non-zero:
1. Print the exact error message
2. Stop immediately — do not proceed to Phase 3 with null or missing seed IDs
3. Report: `[Phase 2 ERROR] Seed creation failed for <record type>: <error>. Fix the seed script and rerun Phase 2.`
4. Do not silently set IDs to `null` and continue — a missing seed causes silent test failures that look like real bugs

Write all created IDs to `qa-test-progress.json` immediately:

```json
{
  "seed_data": [
    {"type": "server", "id": 42, "name": "qa-nginx-1234", "stack": "nginx", "journeys": ["J-001", "J-001-V1"]},
    {"type": "site",   "id": 17, "name": "qa-site-php",   "site_type": "php", "journeys": ["J-003"]}
  ]
}
```

**Do not proceed to Phase 3 until all seed records are verified.** A missing seed causes silent test failures that look like real bugs.

---

## Phase 3: Adaptive Knowledge Gathering

Seed data is ready. Before selecting a testing mode, resolve ambiguities through adaptive question rounds.

### 3.1 Round Structure

- **Maximum 3 rounds**, **maximum 3 questions per round**
- Every question must trace to a specific journey, changed file, or consumer found in Phase 0
- No generic filler questions — if analysis is unambiguous, that topic gets no question

**Stopping conditions (any one is sufficient):**
- No remaining ambiguities
- You say "proceed", "enough", or "good to go"
- 3 rounds completed

### 3.2 Round 1

Always present all questions in one message. Never drip-feed questions one at a time.

Derive questions from these five categories, but only ask about actual ambiguities found:

**A — Stack scope** (ask if changed code is in a stack-specific file but calls a shared service, or vice versa):
> "The fix is in [file] which is shared across all stacks. Should OLS and Docker get this change, or is Nginx-only intentional?"

**B — Access / billing guards** (ask if UI shows something to free users but backend guard is unclear):
> "The UI shows [feature] to free users. Is there a backend guard I'm missing, or is free access intentional?"

**C — Edge cases** (ask if an operation can fail mid-way, be run twice, or has unclear rollback behavior):
> "What should happen if [operation] fails mid-way — roll back, leave partial state, or show a retry prompt?"

**D — Migration behavior** (ask if a migration touches existing data):
> "If a server already has [config] set, should this migration overwrite it or preserve the existing value?"

**E — Developer insight** (always include both, always last):
> "Anything specific about this PR you're worried about breaking?"
> "Any edge cases you already know about that I should make sure to test?"

```
Round 1 questions (answer what you can — say "proceed" to skip ahead):

1. [stack/access/edge-case question from A–D if applicable]
2. [second question from A–D if applicable]
3. Anything you're worried about breaking? Edge cases you know about?

I'll ask follow-up rounds only if your answers raise new questions.
```

### 3.3 Subsequent Rounds

Only ask a follow-up round if the previous answers introduced new ambiguities. Format identically — questions flow naturally from the previous answers:

```
Follow-up (your answer to Q1 raised a question):

1. You said OLS should also be tested. The OLS path is in [file] — 
   should the same fix apply there, or does OLS handle it differently?
```

### 3.4 Applying Answers to Journeys

After each round, update the journey list:

| Answer | Action |
|---|---|
| "OLS should also be tested" | Add OLS variant journeys; create OLS server seed in Phase 2 if not already present |
| "Free users are blocked server-side" | Confirm blocked-user variant journeys are correct |
| "Free access is intentional" | Remove blocked-user variants, log: "Free access confirmed intentional" |
| "It should roll back on failure" | Add error-path journey testing rollback behavior |
| Developer names a specific edge case | Add it as a new journey |

---

## Phase 4: Mode Selection

Journeys confirmed, seeds ready, questions answered. Present mode options and wait for selection.

```
Ready to test.

<N> journeys  |  <N> seed records created  |  Questions answered

Choose how you want to proceed:

──────────────────────────────────────────────────────────
A)  Pipeline Mode
    Journeys grouped by seed conflicts; up to 4 groups dispatched in parallel per batch.
    You see group results as each batch completes (rolling output).
    Best for: routine PRs, large journey sets, balanced speed and token cost.

B)  Multi-agent Mode
    One agent per journey, all dispatched in parallel.
    You see all results arrive together.
    Best for: time-sensitive PRs, many independent journeys.
    Note: variants sharing seed records run sequentially within each group.

C)  Interactive Mode
    You perform every test step manually. The agent guides you
    step by step through each journey and records your findings.
    You see: every step, every expected result, what to verify.
    Best for: manual-only scenarios (DNS, SSL, email), complex new
              features, or cases where you want full control.
──────────────────────────────────────────────────────────

Which mode? (A / B / C)
```

---

## Phase 5A: Pipeline Mode

**Re-run detection (check before writing anything):** If `qa-test-progress.json` already exists and contains `"pr": "<same PR number>"` with a non-empty `journeys` array, print:
```
[WARNING] qa-test-progress.json already has results for PR #<N>.
Overwriting will lose all previous test data (journeys, bugs, screenshots, blv_findings, security_findings).
Type "overwrite" to proceed, or "abort" to stop.
```
Wait for the user's response before continuing.

**Checkpoint write rule:** Merge into `qa-test-progress.json` — do not overwrite the whole file. Preserve any keys written by earlier phases (particularly `blv_findings`, `security_findings`, and `seed_data`). Only initialize keys that do not already exist. Then group journeys by seed-data conflicts and dispatch in batches.

### Grouping Logic

Before dispatching any agents:
1. **Group by shared seeds** — journeys sharing the same `server_id` or `site_id` belong to one group and run sequentially within that group (base journey first, then its variants)
2. **Independent groups run in parallel** — groups with no shared seed records are dispatched together in one message
3. **Batch size = 4** — dispatch up to 4 groups per message; wait for all groups in a batch to return before sending the next batch

```
# Example: 6 journeys across 4 independent seed groups → all dispatched in ONE message

Group 1 (server_id=42): J-001, J-001-V1    ← share same server; run sequentially inside the agent
Group 2 (server_id=55): J-002, J-002-V1
Group 3 (site_id=17):   J-003              ← standalone
Group 4 (server_id=99): J-004, J-004-V1

# Batch 1 — 4 groups, ONE message:
Agent(description="Execute Group 1: J-001 + J-001-V1 (server_id=42)", prompt="...")
Agent(description="Execute Group 2: J-002 + J-002-V1 (server_id=55)", prompt="...")
Agent(description="Execute Group 3: J-003 (site_id=17)", prompt="...")
Agent(description="Execute Group 4: J-004 + J-004-V1 (server_id=99)", prompt="...")

# If >4 groups exist, wait for Batch 1 to complete, then dispatch Batch 2
```

### Checkpoint File

Merge this structure into `qa-test-progress.json`. For each key, only set it if it does not already exist in the file — never overwrite `blv_findings`, `security_findings`, or `seed_data` written by Phase 0/2:

```json
{
  "pr": "<N>",
  "pr_title": "<title>",
  "session_started": "<ISO timestamp>",
  "env": {
    "staging_url": "<url>",
    "ssh": "<user@host>",
    "app_path": "<path>",
    "paid_account": {"email": "<email>", "password": "<pass>"},
    "free_account": {"email": "<email>", "password": "<pass>"}
  },
  "journeys": {},
  "seed_data": [],
  "bugs_found": [],
  "screenshots": [],
  "blv_findings": [],
  "security_findings": [],
  "hlt_findings": [],
  "i18n_findings": [],
  "summary": {"pass": 0, "fail": 0, "blocked": 0}
}
```

**Merge pseudocode:**
```python
existing = json.load(open("qa-test-progress.json")) if file_exists else {}
defaults = { ...checkpoint schema above... }
merged = {**defaults, **existing}  # existing keys take priority
json.dump(merged, open("qa-test-progress.json", "w"))
```

### Journey Agent Template

```
Agent(
  description="Execute J-<ID>: <journey name>",
  prompt="Execute a single user journey on xCloud staging.

  Journey YAML:
  [paste full journey YAML]

  Environment:
  - Staging URL: <url>
  - Actor: <email> / <password>  (role: <role>, plan: <plan>)
  - Seed data: server_id=<id>, site_id=<id>  (null if not applicable)
  - Screenshots dir: qa-screenshots/pr<N>/

  Playwright prefix: try mcp__plugin_playwright_playwright__ first,
  fall back to mcp__playwright__ if unavailable. Print which is active.

  Instructions:
  1. Load references/playwright-mcp-guide.md for patterns and auth flow

  BROWSER LOCK (acquire BEFORE any browser tool call):
  The Playwright MCP server is a shared singleton — parallel agents would fight over the same
  browser window and share session cookies. Acquire a file lock before opening any browser.

  Lock file: qa-browser.lock
  Acquire (run this shell snippet via SSH or Bash before step 2):
    LOCK_FILE="qa-browser.lock"
    MY_ID="<journey-group-id>"   # e.g. "Group-1-J-001"
    MAX_WAIT=180
    elapsed=0
    while [ -f "$LOCK_FILE" ] && [ $elapsed -lt $MAX_WAIT ]; do
      sleep 5; elapsed=$((elapsed + 5))
    done
    if [ -f "$LOCK_FILE" ]; then
      echo "BROWSER_LOCK_TIMEOUT after ${MAX_WAIT}s — marking all journeys in this group BLOCKED"
      exit 1
    fi
    echo "$MY_ID" > "$LOCK_FILE"
    echo "Browser lock acquired by $MY_ID"

  If the lock acquisition times out: write all journeys in this group as BLOCKED with reason
  "browser_lock_timeout" in their sidecar files and return immediately. Do NOT open a browser.

  2. Open browser, navigate to entry_point, log in as actor
  3. Execute every step in the journey YAML in order
  4. Core cycle per step: Navigate → Snapshot → Interact → Snapshot → Screenshot
  5. Re-snapshot after any DOM change before the next interaction
  6. Screenshot before and after every key state change
  7. Run browser_console_messages after every full page load
  8. If server_verification is not null:
     - Open xCloud UI: Server > Management > Commands
     - Run the verification command
     - Screenshot the output — this is your server-side evidence
  9. Close browser: call browser_close tool. MANDATORY — always call this, even if the journey
     FAILS or is BLOCKED. Never leave a browser session open. If this agent runs multiple journeys
     (a group), call browser_close after each journey before opening a new session for the next.

  BROWSER LOCK RELEASE (run immediately after the final browser_close for this group):
    rm -f "$LOCK_FILE"
    echo "Browser lock released by $MY_ID"

  Release the lock even if the journey FAILS or BLOCKED — never leave the lock file behind.

  IMPORTANT — Do NOT write directly to qa-test-progress.json (concurrent agents will corrupt it).
  Instead, write each journey result to its own sidecar file:
    qa-test-progress.<id>.json   (e.g. qa-test-progress.J-001.json)

  Sidecar file format:
  {
    "journey_id": "<id>",
    "result": "PASS" | "FAIL" | "BLOCKED",
    "steps": [{"step_index": N, "action": "...", "observation": "...", "screenshot_file": "..."}],
    "server_verification_output": "<output or null>",
    "bugs": [{"title": "...", "severity": "...", "root_cause_file": "...", "root_cause_line": N, "screenshot_file": "..."}],
    "screenshots": [{"file": "...", "description": "..."}]
  }

  If this agent handles multiple journeys (a group), write one sidecar file per journey.

  Crash / timeout protocol: If any step throws an unrecoverable error, write the sidecar with
  result='BLOCKED', note the error in steps, close the browser, and return. Never leave
  the sidecar file unwritten — the main session checks for it to detect completion.

  Return to main session (≤ 200 words):
  - Result: PASS / FAIL / BLOCKED
  - Bugs found: one-line per bug with severity
  - Screenshots saved: filenames only
  - Blockers: anything that stopped the journey early
  - Sidecar files written: list filenames"
)

**After each batch completes**, merge all sidecar files into `qa-test-progress.json`:
```python
import json, os
from glob import glob

main = json.load(open("qa-test-progress.json"))   # MUST load before the loop
for sidecar_file in glob("qa-test-progress.J-*.json"):
    data = json.load(open(sidecar_file))
    # journeys is a dict keyed by journey_id
    main["journeys"][data["journey_id"]] = {
        "result": data["result"],
        "steps": data["steps"],
        "server_verification_output": data["server_verification_output"],
    }
    main["bugs_found"].extend(data["bugs"])
    main["screenshots"].extend(data["screenshots"])
    result_key = data["result"].lower()   # "pass" | "fail" | "blocked"
    main["summary"][result_key] = main["summary"].get(result_key, 0) + 1
    os.remove(sidecar_file)   # clean up after merging
json.dump(main, open("qa-test-progress.json", "w"), indent=2)
```

Handle missing sidecar (agent crashed before writing it): after all agents return, check that a sidecar exists for every dispatched journey. For any journey with no sidecar, write a synthetic BLOCKED entry directly into `main["journeys"]` before saving.
```

**After each group agent returns**, print one group summary line — groups may arrive out of order:

```
[Group 1 — server_id=42]  J-001 PASS | J-001-V1 PASS
[Group 2 — server_id=55]  J-002 FAIL — <bug one-liner> | J-002-V1 PASS
[Group 3 — site_id=17]    J-003 BLOCKED — <reason>
```

Within each group agent, the base journey runs first, then its variants sequentially.

---

## Phase 5B: Multi-agent Mode

Group journeys by seed data conflicts first:
- Journeys sharing the same `server_id` or `site_id` → run sequentially within a group
- Independent journeys → run in parallel across groups

Dispatch all groups in a **single message**:

```
# One Agent() call per group — all calls in ONE message
Agent(description="Execute J-001 + J-001-V1 (share server_id=42)", prompt="...")
Agent(description="Execute J-002 + J-002-V1 (share server_id=55)", prompt="...")
Agent(description="Execute J-003 (standalone, site_id=17)", prompt="...")
```

Each agent uses the same template as Pipeline Mode (browser lock, sidecar file, crash protocol all apply identically). After all agents return, run the sidecar merge pseudocode from Phase 5A to collect results into `qa-test-progress.json`. Check for missing sidecars (agent crash) and write synthetic BLOCKED entries for any journey with no sidecar.

---

## Phase 5C: Interactive Mode

The agent is a **test guide**. You perform every browser action. The agent tells you exactly what to do, records what you report, and tracks results in `qa-test-progress.json`.

### Guide Format

For each journey, the agent opens a new section:

```
══════════════════════════════════════════════════════════════
Journey J-001: "Paid user installs PHP 8.3 on Nginx server"
Actor:  Paid user  (use your paid test account)
Server: ID 42 — Nginx stack, provisioned
══════════════════════════════════════════════════════════════

STEP 1 of 5 — Navigate
  → Go to: <staging-url>/servers/42/php
  → What do you see? Type "done" when page loaded, or "issue: <what happened>"
```

After your response, the agent acknowledges and advances:

```
STEP 2 of 5 — Click
  → Click the "Install PHP" button
  → Did a panel or modal open? (yes / no / describe what appeared)
```

After the final step:

```
──────────────────────────────────────────────────────────────
EXPECTED OUTCOME:
  PHP 8.3 appears in the installed PHP list with status "Active"

SERVER VERIFICATION (required — run on managed server via Command Runner):
  → In xCloud: open Server 42 > Management > Commands
  → Run this command: php8.3 --version
  → Paste the output here (or type "skipped" with a reason):

RESULT:
  Type one of: PASS / FAIL / BLOCKED
  Notes (optional — describe anything unexpected):
──────────────────────────────────────────────────────────────
```

The agent records your input and moves to the next journey.

### In-Journey Commands

Type any of these at any prompt during Interactive Mode:

| Command | Effect |
|---|---|
| `done` | Current step complete, advance to next |
| `skip` | Skip this journey (agent asks reason, records as BLOCKED) |
| `bug: <description>` | Record a bug mid-journey without completing remaining steps |
| `note: <text>` | Add a note to the current step |
| `end session` | Stop all remaining journeys and proceed to Phase 6 |

### Failure Handling

When you report an issue, the agent asks for classification:

```
Failure noted at Step 3.

What happened?
  1. Element not found / button missing from page
  2. Got an error message — paste it
  3. Page crashed or reloaded unexpectedly
  4. Wrong data or state shown
  5. Other — describe

This determines the root cause category in the report.
```

The agent records the failure, marks the journey FAIL, and moves to the next journey without waiting.

### Server Verification in Interactive Mode

For every journey with a non-null `server_verification` field, the step is **mandatory** — it is not optional even in Interactive Mode. "UI showed success" is not evidence. The Command Runner output is the evidence.

If you cannot access Command Runner (server not connected, etc.), type `blocked: <reason>`. The journey is marked BLOCKED, not FAIL.

---

## Phase 6: Gap Evaluation

After all journeys complete (any mode), check for coverage gaps before writing the report.

### Coverage Checks

1. **File coverage** — every changed file from Phase 0 maps to at least one completed journey
2. **Consumer coverage** — every cross-feature consumer found in Phase 0 has a regression journey
3. **Variant coverage** — every billing guard and every permission check has a blocked-user variant
4. **Blocked cap** — if more than 2 journeys are BLOCKED, convert at least one to a partial test:
   - Create seed data via Tinker, test the UI and policy behavior without real server-side execution
   - Mark as "Partially tested via Tinker-generated data — server execution not verified"

### Minimum Gap Rule

**Find at least 2 gaps.** If you find zero, describe your coverage check methodology before concluding coverage is complete — premature zero-gap declarations are a common failure mode. Common missed gaps:
- Forgot to test the feature with pre-existing data (only tested on fresh seed)
- Forgot to test browser refresh after a state change
- Forgot the migration behavior on rows that existed before the migration

### Gap Journeys

For each gap found, create a new journey and append it to `qa-test-progress.json`. Then apply the same seed-conflict grouping as Phase 5A/5B — do not run gap journeys strictly one-at-a-time:

1. Group gap journeys by shared seed records
2. Independent groups → dispatch in a **single message** (parallel)
3. Within each group → run sequentially (base before variants)

```
# Example: 3 gap journeys across 2 independent groups — ONE message:
Agent(description="Execute gap J-G001 + J-G002 (share server_id=42)", prompt="...")
Agent(description="Execute gap J-G003 (standalone)", prompt="...")
```

Gap journeys use the same agent template as Phase 5A.

Print: `[Phase 6] <N> gaps found — dispatching <N> journeys in <N> groups`

---

## Phase 7: Reporting + Cleanup

### Step 7.1 — Upload Screenshots (BLOCKING — run first, before report)

```bash
# --json outputs {filename: url} map to stdout; use this to avoid the state-file-deleted-on-success bug.
UPLOAD_JSON=$(python3 ~/.claude/skills/xcloud-test/scripts/upload_screenshots.py \
  --dir qa-screenshots/pr<N> --pr <N> --json)
UPLOAD_EXIT=$?
```

**This is mandatory and must complete before spawning the report agent.** Check the exit code:
- Exit 0 → all uploads succeeded. `UPLOAD_JSON` holds `{"01-login.png": "https://res.cloudinary.com/..."}`.
  **Write back Cloudinary URLs into `qa-test-progress.json`**:
  ```python
  import json, os
  url_map = json.loads(UPLOAD_JSON)          # flat {filename: url} — no "uploaded" wrapper
  main = json.load(open("qa-test-progress.json"))
  for s in main["screenshots"]:
      filename = os.path.basename(s["file"]) # extract "01-login.png" from full path
      if filename in url_map:
          s["cloudinary_url"] = url_map[filename]
  json.dump(main, open("qa-test-progress.json", "w"), indent=2)
  ```
  After write-back, every screenshot entry has a `cloudinary_url` field. The report agent reads this field first; if absent, it falls back to the local `file` path.
- Non-zero exit (partial failure) → `UPLOAD_JSON` still contains URLs for files that did upload; run
  the same write-back above to save partial results, then warn the user and continue with mixed paths.

**This is the only permitted upload method.** Never write a loop, curl command, or custom upload script.

### Step 7.2 — Report + UX Critique + Cleanup (spawn all in parallel after upload)

```
Agent(
  description="Write QA report for PR #<N>",
  prompt="Write the final QA report.
  1. Read qa-test-progress.json completely — this is your only data source
  2. Load references/report-template.md for the mandatory structure
  3. Map journeys to report sections: journey ID = section heading
     Format: '## J-001: <name> — PASS'  or  '## J-002: <name> — FAIL'
  4. Embed screenshots: for each screenshot in qa-test-progress.json screenshots array,
     use screenshots[i].cloudinary_url if present, otherwise fall back to screenshots[i].file
     (local path). Never hardcode paths — always read from the screenshots array.
  5. Every FAIL section needs: root cause file + line number
  6. Every PASS section needs: at least one screenshot as evidence
  7. Section 9 — Security Concerns (MANDATORY — never skip or write 'N/A' without checking):
     a. Load references/security-testing.md for the IDOR report table format
     b. Pull qa-test-progress.json → security_findings array. For each entry, write a
        structured security finding using the format from security-testing.md
     c. Pull any journey tagged 'security' or 'idor' — include their PASS/FAIL results
        and evidence (screenshots + curl/Playwright response) in the section
     d. Include the IDOR report table: | Resource | URL Tested | User A | User B | Expected | Actual |
     e. If security_findings is empty AND no IDOR journeys exist: write
        "No security concerns identified. [list what was checked and why no risks were found]"
        — do NOT write just "No security concerns found" without explanation
  8. Section 5.5 — Logic Flaws: pull qa-test-progress.json → blv_findings array
     and write each finding using the Logic Flaw format from report-template.md
  9. Section 5.6 — Human Logic Findings: pull qa-test-progress.json → hlt_findings array.
     For each finding, write it using the Human Logic format from report-template.md.
     Group by lens (Expectation, Feedback, Error Intelligibility, Reversibility, Consistency).
     If hlt_findings is empty AND no first-time-user journeys exist: write
     'No human logic issues identified. [state which lenses were checked and why no issues found]'
     — do NOT write just 'None' without explaining what was checked.
  10. Section 5.7 — Translation / i18n Issues: pull qa-test-progress.json → i18n_findings array.
      Group by type: HARDCODED_STRING, MISSING_KEY, UNTRANSLATED_KEY, NAMING_CONVENTION.
      For each finding write: file:line, the string or key, affected languages, recommendation.
      If i18n_findings is empty: write 'No translation issues found. [state flag (d) was false
      or list the string changes checked and confirm all use translation helpers with existing keys]'
  11. Write report to QA-Report-PR-<N>.md
  12. Run post-report validation checklist from report-template.md
  13. Return: file path, journey count, PASS/FAIL/BLOCKED counts, security findings count,
      hlt findings count, i18n findings count, validation failures"
)
```

### UX Improvement Recommendations (mandatory for UI PRs — spawn in same message as report agent)

If the PR includes UI changes (flag c from Phase 0), spawn this agent. Skip only for backend-only PRs.

```
Agent(
  run_in_background=true,
  description="UX improvement recommendations for PR #<N>",
  prompt="Write actionable UX improvement recommendations for PR #<N>.

  1. Read qa-test-progress.json completely:
     - hlt_findings array: pre-analysis findings from the HLT agent (Phase 0)
     - journeys dict: look at every first-time-user journey result — PASS/FAIL/BLOCKED
       and the observation notes from each step
     - screenshots array: look at the actual UI screenshots from staging
  2. For each confirmed hlt_finding (severity critical or high):
     Write a concrete improvement recommendation:
     - What the current UI does
     - Why it confuses or risks harm for the user
     - Specific fix: exact copy change, interaction pattern, or component change
     - Effort estimate: low (copy change only) | medium (component change) | high (flow redesign)
  3. For each first-time-user journey that returned FAIL or BLOCKED:
     Write a recommendation explaining what the user encountered and what should change.
  4. Spot-check the screenshots: look for loading states, empty states, error states.
     Flag any screenshot where the UI gives the user no clear signal about what happened.
  5. Format as a prioritized list — critical/high first, then medium, then low.
     Maximum 8 recommendations. Each must be specific and actionable, not generic.
  6. Append to QA-Report-PR-<N>.md under a section:
     ## UX Improvement Recommendations
     ### Critical / High Priority
     ### Medium Priority
     ### Low Priority (Polish)
  7. Return: count of recommendations by severity"
)
```

### Step 7.3 — Report Reassessment (blocking — run after report + UX agents return)

Spawn one final agent to read the completed report and check for gaps before cleanup runs.
**Cleanup must NOT start until this agent returns clean.**

```
Agent(
  description="Report reassessment for PR #<N>",
  prompt="Reassess the QA report for PR #<N> for completeness and accuracy.

  Read both sources in full:
  - QA-Report-PR-<N>.md (the completed report)
  - qa-test-progress.json (the ground truth from testing)

  Run every check below. Return a numbered gap list — be specific (section name + what is missing).
  If zero gaps found, return: 'REPORT COMPLETE — no gaps found.'

  COVERAGE CHECKS:
  1. Journey coverage — every journey ID in qa-test-progress.json['journeys'] has a
     corresponding '## J-<ID>:' heading in the report. Flag any missing journey section.
  2. Bug completeness — every entry in qa-test-progress.json['bugs_found'] has a
     '### Bug #N:' section with all required fields (Severity, Root Cause file+line,
     Steps to Reproduce, Expected Result, Actual Result, embedded screenshot).
     Flag any bug missing a field.
  3. Finding arrays reflected — for each non-empty array in qa-test-progress.json:
     - blv_findings → Section 5.5 present with matching finding count
     - hlt_findings → Section 5.6 present with matching finding count
     - i18n_findings → Section 5.7 present with matching finding count
     - security_findings → Section 9 present with matching finding count
     Flag any array that has entries but no corresponding report section, or where
     the section says 'None' but the array is non-empty.
  4. Screenshot evidence — every PASS journey section has at least one embedded screenshot.
     Every FAIL journey section has at least one embedded screenshot at the failure point.
     Flag any journey section with no images at all.
  5. Section completeness — all 15 required sections are present (Title, PR Summary,
     Test Environment, Tests Performed, Bugs Found, 5.5 Logic Flaws, 5.6 Human Logic,
     5.7 i18n Issues, Observations, Regression Issues, Performance, Security, Areas Not
     Fully Tested, Screenshots Summary, Test Data Cleanup, Final Verdict).
     Flag any missing section.
  6. Final verdict — the verdict (PASS / FAIL / PASS WITH OBSERVATIONS) is consistent
     with the bugs and findings in the report. If critical or high severity bugs exist,
     verdict must be FAIL. Flag any verdict that contradicts the findings.
  7. i18n staging verification — for every HARDCODED_STRING or MISSING_KEY finding in
     i18n_findings: is there a screenshot in the report showing the actual string on staging?
     If a critical/high i18n finding has no staging evidence, flag it.

  Return format:
  GAPS FOUND:
  1. [Section] [what is missing or wrong]
  2. ...

  OR: REPORT COMPLETE — no gaps found."
)
```

If the reassessment returns gaps:
- Fix each gap in `QA-Report-PR-<N>.md` before proceeding to Cleanup
- For missing screenshots: re-open the browser (acquire lock), navigate to the relevant page, capture the evidence, upload, and embed
- Print: `[Phase 7] Report reassessment: <N> gaps found and fixed` or `[Phase 7] Report reassessment: clean`

### Cleanup

Delete all seed records from `qa-test-progress.json` seed_data array in **reverse order** (child records before parents):

```php
php artisan tinker
Site::find(<id>)->forceDelete();    // child first
Server::find(<id>)->forceDelete();  // parent second
```

Verify no orphaned records remain:

```php
echo Server::find(<id>) ? 'EXISTS — not deleted!' : 'Deleted OK';
```

Log cleanup results in the report "Test Data Cleanup" section.

---

## Server Architecture Awareness

xCloud manages **two types of servers** — never confuse them:

| Server | What it is | How to access |
|---|---|---|
| **xCloud app server** | Hosts the xCloud platform (staging.tmp1.dev) | SSH via user-provided credentials |
| **Managed server** | User-owned servers managed by xCloud (e.g., OLS at 107.175.x.x) | **Command Runner** in xCloud UI (Server > Management > Commands) |

Scripts and operations in `app/Scripts/` run on **managed servers**, not the app server. To verify that a script ran correctly, use Command Runner — not SSH to the app server. Screenshot the Command Runner output as your server-side evidence.

---

## Evidence Rules

Every journey result — PASS or FAIL — must have evidence. Evidence = output from actually running the test on staging.

**What counts:**
- Screenshots from Playwright or from you (Interactive Mode) showing the UI state
- Command Runner output showing server-side state
- Tinker query results showing database state
- Browser console output showing errors or clean output

**What does NOT count:**
- "The code handles this case" — that is code review, not QA
- "The diff shows the fix" — reading code is not testing
- "Based on the implementation..." — if you didn't run it on staging, it is not evidence
- UI toast or status badge alone (without Command Runner confirmation for server-modifying operations)

---

## Verdict Rules

| Condition | Verdict |
|---|---|
| All journeys PASS, logic correct | **PASS** |
| All journeys PASS, minor edge-case observations | **PASS with observations** |
| Core feature logic is wrong (wrong threshold, misleading output, incorrect behavior) | **FAIL — logic flaw** |
| User explicitly confirms wrong logic is intentional | **CONDITIONAL PASS** (document confirmation) |
| Any journey FAIL with critical or high severity bug | **FAIL** |

A logic flaw is a FAIL — not an observation. If the feature produces misleading results for users, the feature is broken even if the code runs without errors.

---

## Playwright MCP (for Pipeline and Multi-agent modes)

Inside testing sub-agents, try prefixes in this order:
1. `mcp__plugin_playwright_playwright__browser_*` (preferred)
2. `mcp__playwright__browser_*` (fallback)

Print which is active at agent start: `Using Playwright MCP (plugin version)` or `Falling back to standalone Playwright`.

Core interaction cycle: **Navigate → Snapshot → Interact → Snapshot → Screenshot**

Element refs are ephemeral — always re-snapshot after any DOM mutation before the next interaction.

> Load `references/playwright-mcp-guide.md` inside testing sub-agents for the full tool inventory, auth flow, wait strategies, and xCloud UI patterns.

### Browser Isolation in Parallel Modes

The Playwright MCP server is a **shared singleton process** — all sub-agents connect to the same browser instance. Parallel agents without coordination will:

- Navigate over each other's active page
- Share session cookies (login by Agent 2 logs out Agent 1's session)
- Have `browser_close` from one agent kill every other agent's browser session

**No MCP-level context isolation is available.** `browser_tabs` creates tabs that share the same cookie jar — a second login in a new tab overwrites the first agent's session.

**Solution: file-based mutex (`qa-browser.lock`).**

Each journey agent acquires the lock before its first `browser_navigate` and releases it after its final `browser_close`. Non-browser work (SSH verifications, seed checks, sidecar JSON writes) still runs concurrently across parallel agents — only the actual browser session is serialized.

| Phase | Parallel? |
|---|---|
| Prep (reading journey YAML, SSH seed checks) | Yes — fully concurrent |
| Browser (navigate → interact → screenshot → close) | No — serialized via lock |
| Post-browser (sidecar write, cleanup) | Yes — fully concurrent |

**Lock timeout = 180 seconds.** If a group waits longer than 3 minutes for the browser, it marks its journeys BLOCKED and returns. This prevents a crashed agent from holding the lock forever. After a crash, manually delete `qa-browser.lock` before re-running.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Running browser tests in the main session | Browser runs inside sub-agents (Pipeline/Multi-agent) or by you (Interactive) |
| Writing a screenshot upload loop | One command only: `upload_screenshots.py --dir ... --pr ...` |
| Spawning report agent before upload | Upload must complete (exit 0 checked) before report agent runs |
| Writing "No security concerns" without explanation | Section 9 must state what was checked and why no risks apply |
| Security findings lost after BLV agent returns | BLV+security agent writes to qa-test-progress.json — report reads from there |
| Journey agents writing qa-test-progress.json concurrently | Agents write per-journey sidecar files (qa-test-progress.J-001.json); main session merges after each batch |
| Parallel agents opening the browser without locking | Each group acquires qa-browser.lock before first browser_navigate; releases after final browser_close |
| Second agent's login overwriting first agent's session cookie | Same root cause — browser lock prevents concurrent browser sessions entirely |
| Agent crash leaving qa-browser.lock behind | If browser tests are stuck and qa-browser.lock exists with no active agent, delete it manually |
| Phase 5A checkpoint overwrites blv_findings / security_findings | Checkpoint MERGES into existing file — never full-overwrite; existing keys take priority |
| Re-running skill on same PR without warning | Phase 5A checks for existing results and asks "overwrite or abort" before writing |
| Cloudinary upload done but report still uses local paths | After upload exits 0, write cloudinary_url back into screenshots[] in qa-test-progress.json |
| Leaving browser open after journey | Call browser_close after every journey — even FAIL/BLOCKED |
| Treating UI toast as server-side proof | Run Command Runner verification, screenshot the output |
| Creating seed data during testing | Seed data is created in Phase 2 — before any browser opens |
| Journeys without variants | Every journey needs at least one variant (blocked user or different role) |
| Skipping gap evaluation | Phase 6 is mandatory — if you find zero gaps, you didn't look |
| More than 2 BLOCKED journeys without partial testing | Convert at least one to partial test via Tinker + UI |
| Interactive mode: skipping server verification | Even in manual mode, Command Runner output is required for server-modifying steps |
| Wrong Tinker enum values | Always load `references/environment-setup.md` before creating seed records |
| Confirming journeys without checking feature map | Cross-reference `xcloud-feature-map.md` to catch missing UI pages |
| Reading code instead of testing | Log in, perform the action, screenshot the result. Code reading = review, not QA. |
| "Verified by reviewing the diff" as evidence | Trigger the actual scenario on staging and observe the result |
| Skipping HLT agent for UI PRs | Any PR with Vue/Blade changes gets the HLT agent — it runs in background, costs little, and catches critical UX failures before users hit them |
| Skipping i18n agent when strings changed | Any PR adding/modifying user-facing strings gets the i18n agent — hardcoded strings and missing keys break non-English users silently |
| Starting cleanup before reassessment returns clean | Step 7.3 is a hard gate — cleanup must not run while gaps exist in the report |
| Reassessment agent finding gaps but not fixing them | Every gap the reassessment finds must be fixed in the report before cleanup; don't proceed with known holes |
| First-time user journey skips "observe" steps | These steps are mandatory — snapshot the page and note what a new user reads before any click, not just what happens after |
| HLT finding not verified on staging | Every critical/high HLT finding must have a screenshot from a first-time-user journey proving it exists on staging — not just "code says so" |
| Writing "No human logic issues" without checking all 5 lenses | Section 5.6 must name each lens and state why it found nothing — a blank "none" is always wrong |

---

## Progress Checkpoints

Print a one-line status at every phase boundary and every journey result. Never go more than 60 seconds without output.

```
[Phase 0] PR #<N> validated — <N> files, <N> UI pages affected
[Phase 0] Analysis + deploy agents spawned in parallel
[Phase 0] Deploy confirmed — branch <name>, commit <hash>
[Phase 1] Generated <N> journeys (<N> variants) — waiting for confirmation
[Phase 1] Journeys confirmed
[Phase 2] Seed data: <N> records created and verified
[Phase 3] Round <N> — <N> questions sent
[Phase 3] Knowledge gathering complete
[Phase 4] Mode selected: Pipeline / Multi-agent / Interactive
[Phase 5] [Group N] J-<ID> PASS | J-<ID> FAIL — <bug>    ← one line per group as it arrives
[Phase 6] Gap evaluation: <N> gaps found, <N> journeys added
[Phase 7] Uploading <N> screenshots... (blocking — waiting for exit 0)
[Phase 7] Report agent + UX agent spawned in parallel
[Phase 7] Report written: QA-Report-PR-<N>.md
[Phase 7] Reassessment: <N> gaps found / clean
[Phase 7] Cleaning up <N> seed records...
[Phase 7] Cleanup complete
```
