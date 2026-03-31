# Testing Categories

Perform ALL applicable categories for every QA session. Skip a category only if it is genuinely irrelevant to the PR (e.g., no API endpoints → skip API testing).

## Evidence Requirement (Applies to ALL Categories)

**Every test case must produce evidence.** Use this format in the report:

| # | Test Case | Expected | Actual | Evidence | Verdict |
|---|-----------|----------|--------|----------|---------|
| 1 | Login page loads correctly | Login form visible | Form rendered | ![Login](qa-screenshots/01-login.png) | PASS |
| 2 | PHP packages installed on server | lsphp85 packages present | 14 packages found | SSH: `dpkg -l \| grep lsphp85` | PASS |
| 3 | Free user blocked from feature | Upgrade prompt shown | 500 error instead | ![500 error](qa-screenshots/05-error.png) | FAIL |

**Evidence types:** Screenshots, SSH/Command Runner output, Tinker query results, curl responses, browser console/network logs. Code review is NOT evidence.

## Test Case Generation

The checklists below are **starting points** — generate additional PR-specific test cases. For each changed file/feature, create test cases for: happy path, error path, edge cases, role variations, and regression of related features. See Step 4.0 in SKILL.md for minimum counts.

## 4.1 Smoke Testing

**Purpose:** Verify the application is stable and not broken by the PR.

**Checklist:**
- Login page loads, authentication works
- Dashboard loads without errors
- Key pages affected by the PR load correctly
- No HTTP 500 errors on any route
- Check `browser_console_messages` for JavaScript errors on every page
- Check `browser_network_requests` for failed API calls

**xCloud-specific:** After login, verify the dashboard shows servers, sites, and billing data. The sidebar navigation should load all links.

## 4.2 Sanity Testing

**Purpose:** Verify the specific feature or fix introduced by the PR works as intended.

**Checklist:**
- The intended behavior works as described in the PR description
- UI renders correctly (use snapshots to verify element states)
- Database changes are correct (verify via Tinker/SSH)
- API responses are correct (test via curl or Playwright network requests)
- Compare actual behavior against what the PR description claims

**Before/After context is required.** When reporting sanity test results, make it clear what was wrong before and what's working now. The reader should understand the improvement without having to read the PR diff.

```
### 4.2 Sanity Testing — PASS

**Previous behavior:** Free-plan users could access the PHP 8.5 installer via direct URL, bypassing the billing guard. No upgrade prompt was shown.

**After fix:** Free-plan users now see the upgrade prompt when navigating to the PHP version page. The billing guard middleware correctly blocks access.

![Free user sees upgrade prompt on PHP version page](qa-screenshots/04-free-user-upgrade-prompt.png)
```

**Tip:** Read the PR description carefully. Test exactly what it claims to fix or add — this catches cases where the fix is incomplete or addresses a different problem than described.

## 4.3 Regression Testing

**Purpose:** Verify the PR did NOT break existing functionality.

**Checklist:**
- Authentication flows (login, logout, session persistence)
- Dashboard widgets and data display
- Navigation — all sidebar links work
- CRUD operations on affected models
- Permission systems and validation rules
- Previously fixed bugs haven't returned

**xCloud-specific:** Test the pages and features that share code with the PR's changes (identified in Step 1.2 cross-feature analysis).

## 4.4 Scenario Testing

### Happy Path
Normal user workflow with valid inputs, successful submissions, expected navigation. This is the primary use case described in the PR.

### Unhappy Path
Invalid inputs and error conditions:
- Wrong email formats, missing required fields
- Invalid file types, wrong data formats
- Values outside allowed ranges
- Verify error messages are clear, specific, and user-friendly (not raw exceptions)

### Edge Cases
Boundary values and limits:
- Maximum character lengths for text fields
- Zero, negative, or extremely large numeric values
- Empty strings vs. null vs. whitespace
- Large file uploads near size limits
- Unicode, emoji, and special characters in text fields

### Corner Cases
Combined extremes:
- Maximum-length field with special characters
- Rapid form resubmission during processing
- Concurrent operations on the same resource
- Navigating away mid-operation and returning

### Monkey Testing
Random, unscripted interactions:
- Click buttons rapidly multiple times
- Enter unexpected characters: emojis, unicode, SQL fragments (`'; DROP TABLE--`), HTML tags
- Navigate back/forward mid-form
- Submit completely empty forms
- Paste extremely long strings

## 4.4a End-to-End Action Execution (MANDATORY)

**This is the most critical test.** Don't just verify the feature appears in the UI — **actually perform the core action** on staging and verify the full result chain.

The difference between "PHP 8.5 shows an Install button" and "PHP 8.5 was installed, and we verified 14 packages on the server" is the difference between superficial QA and real QA.

**Steps:**
1. **Execute the action:** Click Install, Submit, Create, Delete, Toggle — whatever the PR's primary feature enables
2. **Wait for completion:** Watch for status changes, loading indicators, success/error messages
3. **Verify UI state:** Screenshot the result — does the page reflect the completed action?
4. **Verify server-side state** (for server operations): Use SSH or Command Runner to confirm:
   - Packages installed/removed: `dpkg -l | grep <package>` or `apt list --installed`
   - Config files created/modified: `cat`, `grep` on expected config paths
   - Binaries functional: run the binary (e.g., `php -v`, `node -v`)
   - Services running: `systemctl status <service>`
   - File system changes: `ls -la <path>`, `find <dir> -name <pattern>`
5. **Verify database/meta state:** Use Tinker to confirm records, metadata, and flags are correct
6. **Test related features still work:** After the action, do related features (that depend on the same data) still behave correctly?

> Load `references/ssh-server-commands.md` for SSH verification patterns.

**Command Runner verification (MANDATORY for server operations):**
After step 3 (verify UI state), open Command Runner at `/server/{id}/command-runner` and run the verification command from the matrix in `references/server-verification.md`. Screenshot the Command Runner output — this is your server-side evidence.

Example: After a PHP install shows "Installed" in the UI, run `php8.2 -v && dpkg -l | grep php8.2 | wc -l` in Command Runner. A screenshot showing version string + package count is your server-side evidence. The UI toast alone is NOT sufficient.

> Load `references/server-verification.md` for the full verification matrix and Command Runner step-by-step workflow.

**Site-type feature awareness:** Before testing, check the site type and server stack to determine which UI features are available. WordPress sites have ~12 additional management pages (debug, caching, updates, etc.) that don't exist for other types. Load `references/xcloud-feature-map.md` for the complete site type feature matrix.

## 4.5 API Testing

> Full methodology is in `references/security-testing.md` — load it for auth testing, content type testing, pagination edge cases, and enterprise API specifics.

If the PR introduces or modifies API endpoints, test:
- **Authentication:** Valid token, no token, invalid token
- **Validation:** Missing required fields, wrong types, boundary values
- **Content type handling:** Wrong content types should return 415 or 422
- **Pagination edge cases:** Negative page, huge per_page, page beyond range
- **Enterprise API:** If applicable, test enterprise-specific routes and response format

## 4.6 Security Testing

> Full methodology is in `references/security-testing.md` — load it for IDOR methodology, guard asymmetry testing, XSS payloads, CSRF verification, and policy testing via Tinker.

For every PR, check at minimum:
- **IDOR:** Can User B access User A's resources by changing IDs in URLs?
- **Guard asymmetry:** For every UI-disabled feature, does the backend API also block it?
- **Input sanitization:** Test XSS payloads in all text fields touched by the PR
- **Sensitive data exposure:** Check API responses don't leak passwords, tokens, or full keys
- **Authorization policies:** Verify policy methods via Tinker for affected models

## 4.7 xCloud-Specific Checks

Based on what the PR touches, verify these platform patterns:

### Billing Plan Guards
- Features gated by billing plan should block free users with a proper upgrade prompt (not a 500 error)
- Test with `$server->isFreePlan()` and `$server->team->isTrailMode()` via Tinker
- Verify `upgrade-plan.required` middleware is on relevant routes
- Free plan users should see upgrade prompts, not raw errors or blank pages

### Whitelabel Isolation
- Whitelabel users should only see their own reseller's branding and data
- Resources scoped to whitelabel should not leak across whitelabel boundaries
- Test with a whitelabel user account if the PR touches whitelabel-scoped features

### Enterprise Feature Exclusions
- Enterprise plans have `exclude_features` — verify sidebar hides restricted items
- Backend should return 403 for excluded features, not just hide the UI link
- Check `$team->getMeta('exclude_features', [])` via Tinker

### Team Permissions
- Actions requiring `hasTeamPermission()` should fail for team members without that permission
- Test with a non-owner team member if the PR adds or modifies permission checks
- Verify both UI disabling and backend enforcement

### Server Stack Checks
- Features that exclude certain server stacks (e.g., `docker_nginx`) should hide/disable correctly
- Verify the correct stack enum is checked: `$server->stack->isOpenLiteSpeed()`, `$server->stack->isNginx()`, etc.

### Site Type Handling
- Use `SiteType` enum values, not hardcoded strings
- Verify behavior across relevant site types (WordPress, Laravel, Custom PHP, etc.)

## 4.8 Usability Testing

**Checklist:**
- Broken layouts or misaligned elements
- Confusing navigation or missing breadcrumbs
- Unclear error messages (raw exception text vs. user-friendly message)
- Missing loading states or feedback after actions
- **Table sorting:** If a table has sortable columns, click **every** sortable column header to verify ascending/descending sort works correctly. Different data types (strings, dates, numbers, statuses) can have different sorting bugs — don't just check one column and move on
- Pagination: uses ellipsis for large page counts, correct page sizes
- Responsive behavior if applicable
- Accessibility: buttons have labels, form fields have labels

## 4.9 Performance Observations

**Checklist:**
- Page load times (note anything > 3 seconds)
- N+1 query indicators (check Laravel Debugbar if available, or `laravel.log` for slow queries)
- Heavy SSH script execution times
- Excessive API calls visible in `browser_network_requests`
- Large response payloads

## 4.10 Error Recovery / Failure Path Testing

xCloud runs scripts on remote servers — operations fail in production. Users expect clear feedback and a way to recover. Test what happens when things go wrong.

### General Failure Patterns

- **Mid-operation failure:** If applicable, simulate or observe what happens when a server operation fails. Does the status get stuck on "Installing" / "In progress", or does it correctly transition to "Failed"?
- **Retry behavior:** After a failure, can the user retry? Does it work correctly the second time, or does leftover state cause issues?
- **UI feedback on failure:** Does the user see a clear error message, or does the page just hang? Check for proper error toasts, status badge updates, and log entries.
- **Queue job failures:** Check the `failed_jobs` table via Tinker after operations:
  ```php
  DB::table('failed_jobs')->latest()->first();
  ```
- **Graceful degradation:** If the feature depends on an external service or server state, what happens when that dependency is unavailable?

### xCloud-Specific Failure Scenarios

These are the real-world failures xCloud users hit. If the PR touches any of these areas, test the failure path:

| Scenario | What to check | How to verify |
|----------|---------------|---------------|
| **SSH timeout during script execution** | Does the status get stuck, or does it timeout gracefully? Does the UI show a meaningful error? | Check `failed_jobs` table and `laravel.log` for timeout exceptions |
| **Partial script execution** | If a script installs packages but fails on config, is the state consistent? Can the user retry without duplicating what already succeeded? | SSH to check what was installed vs. what was configured; check model status in Tinker |
| **Queue job timeout** | Long-running jobs (package installs, backups) may exceed the queue timeout. Does the job get retried or marked as failed? | `DB::table('failed_jobs')->latest()->first()` — check the exception message for timeout |
| **Server provisioning failure** | If server creation fails partway, is the server record cleaned up or left in a stuck "creating" state? | Check `$server->status` in Tinker; verify the UI shows a clear failure state |
| **DNS propagation delays** | Site creation may succeed in the database but DNS isn't ready yet. Does the UI handle the interim state? | Navigate to the site immediately after creation — it should show a pending/propagating status, not a broken page |
| **SSL certificate failures** | Let's Encrypt rate limits, DNS not ready, or domain validation fails. Does the error surface clearly? | Check the SSL status in UI and `laravel.log` for certificate-related errors |
| **Concurrent operations on same server** | Two operations dispatched to the same server simultaneously. Does the queue handle ordering, or do scripts collide? | Trigger two actions quickly and check if both complete or if one fails with a lock/conflict error |
| **Disk space exhaustion** | Backup or log rotation fills the disk. Does the operation fail gracefully? | Check `df -h` on the server after heavy operations |

## 4.11 State Transition Testing

xCloud entities have status flows (server: `creating -> active -> suspended`, PHP version: `not_installed -> installing -> installed`, site: `creating -> active`). Invalid transitions cause data corruption and stuck states.

- **Duplicate action prevention:** Can you trigger the same action twice on a resource already in a transitional state? (e.g., click "Install" on a PHP version that's already "Installing")
- **Button/UI state during transitions:** Are action buttons correctly disabled while an operation is in progress?
- **Status consistency:** After an operation completes, does the status in the UI, database, and server meta all agree? Check via:
  - UI: Playwright snapshot of status badges/labels
  - Database: Tinker query on the model's status column
  - Server meta: `$server->getServerInfo(...)` or `$model->getMeta(...)`
- **Invalid state access:** Navigate directly to a URL that assumes a certain state (e.g., site settings page for a site still "creating") — does it handle gracefully?

## 4.12 Idempotency / Double-Submit Testing

Users double-click. Networks retry. Test that repeated actions don't cause duplicate side effects.

- **Rapid double-click:** Click the primary action button twice rapidly — does it dispatch two jobs, create two records, or run two scripts? Use Playwright to click, then immediately click again before the page updates.
- **Form resubmission:** Submit a form, use browser back, submit again — does it create a duplicate?
- **Script idempotency:** If the PR modifies a server script, would running it twice break anything? Check if the script uses guards like `if [ -f ... ]` or `dpkg -l | grep` before installing.
- **API replay:** Send the same API request twice in quick succession via curl — does the backend handle it correctly (idempotency key, duplicate check, or graceful no-op)?

**Real example (PR #4260):** The "Refresh All" button had triple protection: JS guard (`if (refreshing.value) return`), UI disabled (`:disabled="refreshing"`), and loading indicator (`:loading="refreshing"`). And the backend operation was inherently idempotent. Document all layers of protection you find.

## 4.14 Boundary Testing

**Purpose:** Verify the system behaves correctly at the exact edges of valid input ranges — not just "some invalid value" but the precise boundary where valid becomes invalid.

**Methodology:** For each input field or configurable value touched by the PR, identify the valid range and test at these 5 points:

| Point | Example (port field: 1–65535) |
|-------|-------------------------------|
| Below minimum (min - 1) | `0` |
| At minimum | `1` |
| Normal value (mid-range) | `8080` |
| At maximum | `65535` |
| Above maximum (max + 1) | `65536` |

**xCloud-Specific Boundaries:**

| Field / Feature | Valid Range | Test At |
|----------------|-------------|---------|
| SSH port | 1–65535 | 0, 1, 65535, 65536 |
| PHP version | Supported versions enum | Unsupported version string |
| Site name / domain | Valid hostname chars, length limits | Max length, empty, special chars, unicode |
| Server name | Platform naming rules | Max length, spaces, special chars |
| Database name | MySQL naming rules (64 chars max) | 64 chars, 65 chars, reserved words |
| Database username | MySQL limits (32 chars max) | 32 chars, 33 chars, special chars |
| Database password | Min/max length, complexity | Min length, min - 1, max length, max + 1 |
| Cron schedule | Valid cron expressions | Malformed expressions, out-of-range values (minute = 60) |
| Firewall port | 1–65535 | 0, 1, 65535, 65536, non-numeric |
| Environment variable key | Env var naming rules | Spaces, special chars, empty key, very long key |
| Environment variable value | No hard limit but practical limits | Very long values (10KB+), multiline, special chars |
| File upload size | Server/plan configured max | At limit, 1 byte over limit |
| Nginx custom config | Valid nginx directives | Syntax errors, very long rules, special chars |
| PHP ini settings | Setting-specific ranges | memory_limit=0, upload_max_filesize=-1, max_execution_time=999999 |

**Checklist:**
- For each input touched by the PR, identify the valid range from validation rules (`FormRequest`) or database constraints
- Test at minimum, maximum, and one step beyond each boundary
- Verify error messages are specific ("Port must be between 1 and 65535") not generic ("Invalid input")
- Check that boundary values are handled consistently between frontend validation and backend validation
- Verify database constraints match application validation (e.g., VARCHAR(255) matches max length rule)

## 4.15 Negative Testing

**Purpose:** Systematically verify the system rejects invalid, unexpected, and malicious inputs — going beyond "wrong format" to cover type mismatches, wrong-state operations, and malformed data.

**Difference from 4.4 Unhappy Path:** Unhappy Path tests common user mistakes (wrong email format, missing fields). Negative Testing is systematic and adversarial — every input type gets a full battery of invalid patterns, including type mismatches, encoding tricks, and wrong-state operations.

### Data Type Mismatches

| Expected Type | Negative Inputs to Try |
|--------------|------------------------|
| Integer | String, float, boolean, null, empty string, array |
| String | Integer (if strict typing), array, object, null |
| Email | Missing @, double @, no domain, no TLD, spaces |
| URL | Missing protocol, spaces, `javascript:`, `data:`, `ftp:` |
| Boolean | `"yes"`, `"no"`, `2`, `-1`, `"true"` (string), null |
| JSON | Malformed JSON, XML, plain text, empty string |
| Date | Invalid format, future dates where past required, `0000-00-00`, Feb 30 |

### Wrong-State Operations (xCloud-Specific)

Test operations that should be blocked based on current resource state:

| Operation | Invalid State | Expected |
|-----------|--------------|----------|
| Delete a server | Server is "provisioning" | Block with clear error |
| Install PHP version | Already "installing" | Block duplicate operation |
| Deploy site | Site is "creating" | Block with status check |
| Restart service | Server is "disconnected" | Fail gracefully with error |
| Run migration | Another migration is running | Queue or block with message |
| Create site on server | Server is "archived" | Block with clear error |
| Issue SSL certificate | Domain DNS not ready | Fail gracefully with error |
| Access billing feature | Team has no active plan | Show upgrade prompt, not 500 |

### Malformed Data Patterns

Test these patterns against every text input touched by the PR:

```
Empty string: ""
Whitespace only: "   "
Null byte: "test\x00value"
Very long string: "a" × 10000
SQL injection: "'; DROP TABLE--"
Path traversal: "../../etc/passwd"
Command injection: "; rm -rf /"
Newline injection: "value\nX-Header: injected"
Unicode: "тест", "测试", "🚀"
Mixed encoding: "caf\xc3\xa9"
HTML entities: "&lt;script&gt;"
```

### xCloud-Specific Negative Patterns

- **Invalid server stack combinations:** Create a Docker site type on a Nginx server
- **Invalid site type for stack:** OpenClaw site on a non-OpenClaw server
- **Cross-team resource access:** Use another team's server ID in API calls
- **Expired/revoked tokens:** Use a revoked API token for enterprise endpoints
- **Disabled features:** Access a feature excluded via `exclude_features` meta
- **Plan-restricted features:** Access paid features with a free plan (via direct API, bypassing UI)

**Checklist:**
- For each input field, test at least 3 negative patterns from the categories above
- Verify every negative input returns a clear, user-friendly error (not a 500 or raw exception)
- Check that negative inputs don't partially execute (e.g., don't create a half-configured server before failing validation)
- Verify error responses don't leak sensitive information (stack traces, database details, file paths)
- Test wrong-state operations for every status transition the PR touches

## 4.16 Limit Testing

**Purpose:** Verify the system handles resource limits and capacity constraints gracefully — what happens when a user hits the ceiling?

### Plan-Based Resource Limits (xCloud-Specific)

xCloud billing plans restrict resource creation. When a plan limit is reached, the user should see a clear upgrade prompt — not a 500 error or silent failure.

| Resource | Where Limit Is Checked | How to Test |
|----------|----------------------|-------------|
| Max sites per server | Site creation | Create sites up to plan limit, attempt one more |
| Max servers per team | Server creation | Check team's server count vs plan limit via Tinker |
| Max team members | Team member invitation | Invite members up to limit, attempt one more |
| Max databases per server | Database creation | Create databases up to limit, attempt one more |
| Max cron jobs | Cron job creation | Create cron jobs up to limit, attempt one more |
| Max supervisor processes | Supervisor config | Create processes up to limit, attempt one more |
| Max custom domains per site | Domain management | Add domains up to limit, attempt one more |
| Max firewall rules | Firewall management | Add rules up to limit, attempt one more |

**Testing methodology:**
1. Check the current plan limits via Tinker: `$team->activePlan` or relevant plan meta
2. Check current resource count: e.g., `$server->sites()->count()`
3. If near the limit, create resources up to the limit
4. Attempt to exceed the limit — verify the UI shows an upgrade prompt or clear limit message
5. Verify the backend API also blocks the request (not just the UI)

### System & Input Size Limits

| Limit | How to Test | Expected Behavior |
|-------|------------|-------------------|
| Max file upload size | Upload a file at/above the configured limit | Clear error message, not timeout or 500 |
| Max environment variables | Add many env vars to a site's .env | System handles gracefully |
| Max nginx custom rules | Add very long custom nginx configuration | Validation or clear error |
| Max SSH key length | Add an unusually long SSH key | Accepted or clear validation error |
| Max backup size | Trigger backup on a large site | Completes or fails with clear timeout/size message |
| Max concurrent operations | Trigger multiple server operations simultaneously | Queue properly, don't collide |

### Pagination & List Limits

| Scenario | How to Test | Expected Behavior |
|----------|------------|-------------------|
| Empty list (0 items) | View a resource list with no records | Empty state message shown, no errors |
| Single item | View a list with exactly 1 record | Renders correctly, pagination hidden |
| Full page (exactly page size) | View list with exactly N records (default page size) | No pagination or "1 of 1" |
| Multiple pages | View list requiring pagination | Pagination controls work correctly |
| Last page with fewer items | Navigate to last page | Partial page renders correctly |

**Checklist:**
- For each resource type the PR creates or modifies, identify the plan-based limit
- Test at the limit boundary (at limit, one over limit)
- Verify the error/limit message includes the current limit and an upgrade path
- Verify the backend enforces the same limit as the frontend
- Test empty states (0 records) and single-record states for all list views
- For file/data operations, test with large inputs near configured size limits

## 4.17 Combinatorial / Pairwise Testing

**Purpose:** Catch bugs that only appear when specific parameter combinations interact — not from any single value alone but from the way two or more values combine.

**Why this matters in xCloud:** Many features behave differently based on server stack, site type, billing plan, and user role. A PHP install works on Nginx but fails on OLS. A feature is gated for free users but bypassed for whitelabel admins. These interaction bugs are invisible to single-parameter testing.

**Difference from other categories:** Boundary (4.14) tests one field at a time. Negative (4.15) tests invalid inputs. Combinatorial testing uses *valid* values — the bug is in how they combine.

### Methodology

1. **Identify parameters** from the PR — what inputs, configurations, or conditions does the feature depend on?
2. **List valid values** for each parameter
3. **Build a pairwise matrix** — ensure every pair of parameter values appears in at least one test case (full combinatorial is N!, pairwise is manageable)
4. **Execute the matrix** and verify each combination behaves correctly

### When to Apply

Apply when the PR touches code that branches on **2+ independent dimensions**. Look for:
- `match` / `switch` on enums (stack, site type, billing plan)
- `if ($server->stack->isOpenLiteSpeed())` combined with `if ($site->type === SiteType::WORDPRESS)`
- Form fields with interdependencies (selecting a stack changes available site types)
- Policy checks combining role + resource type + action
- Scripts with stack-specific paths or version-specific logic

### xCloud Parameter Sets

Use these pre-built parameter sets when the PR touches the relevant area. Pick only the parameters the PR actually depends on — don't test every combination for every PR.

#### Server Operations (stack-dependent features)

| Parameter | Values |
|-----------|--------|
| Server stack | `nginx`, `openlitespeed`, `docker_nginx`, `openclaw` |
| Ubuntu version | `22.04`, `24.04` |
| Database type | `mysql_8`, `mariadb_10` |

Example pairwise matrix (6 tests cover all pairs instead of 16 full combinations):

| # | Stack | Ubuntu | Database | Test |
|---|-------|--------|----------|------|
| 1 | nginx | 22.04 | mysql_8 | Service restart, PHP management |
| 2 | openlitespeed | 24.04 | mysql_8 | Service restart, PHP management |
| 3 | docker_nginx | 22.04 | mariadb_10 | Container operations |
| 4 | openclaw | 24.04 | mariadb_10 | Gateway operations |
| 5 | nginx | 24.04 | mariadb_10 | Service restart, PHP management |
| 6 | openlitespeed | 22.04 | mariadb_10 | Service restart, PHP management |

#### Site Creation & Management (type × stack)

| Parameter | Values |
|-----------|--------|
| Site type | `wordpress`, `laravel`, `custom-php`, `nodejs`, `docker-compose`, `openclaw` |
| Server stack | `nginx`, `openlitespeed`, `docker_nginx`, `openclaw` |
| PHP version (if applicable) | `8.1`, `8.2`, `8.3`, `8.4` |

Not all combinations are valid — consult the stack-site compatibility matrix in `references/environment-setup.md`. Invalid combinations should be tested too (verify they're rejected gracefully — this overlaps with 4.15 Negative Testing).

Example pairwise subset for a PHP management PR:

| # | Site Type | Stack | PHP Version | What to Verify |
|---|-----------|-------|-------------|----------------|
| 1 | wordpress | nginx | 8.2 | PHP switch works, site stays up |
| 2 | laravel | openlitespeed | 8.3 | lsphp binary used, not system PHP |
| 3 | custom-php | nginx | 8.1 | Oldest supported version works |
| 4 | wordpress | openlitespeed | 8.4 | Latest version + OLS combo |
| 5 | laravel | nginx | 8.4 | Latest version + Nginx combo |

#### User Roles × Billing Plans × Features

| Parameter | Values |
|-----------|--------|
| User role | `owner`, `admin`, `editor`, `viewer` |
| Billing plan | `free`, `starter`, `pro`, `enterprise` |
| Feature action | `view`, `create`, `edit`, `delete` |

This matrix catches "free editor can view but not create" vs "pro editor can create but not delete" type bugs. Focus on the feature the PR touches:

| # | Role | Plan | Action | Expected |
|---|------|------|--------|----------|
| 1 | owner | pro | create | Allowed |
| 2 | editor | free | create | Blocked (plan limit) |
| 3 | viewer | pro | edit | Blocked (role limit) |
| 4 | owner | free | delete | Blocked (plan limit) |
| 5 | admin | enterprise | create | Allowed |
| 6 | editor | starter | view | Allowed |

#### Script Execution (stack × version × operation)

For PRs modifying Blade scripts in `app/Scripts/`:

| Parameter | Values |
|-----------|--------|
| Server stack | `nginx`, `openlitespeed` |
| Target version | Version-specific values from the PR |
| Operation | `install`, `uninstall`, `switch`, `configure` |

Verify each combination produces the correct script commands (e.g., OLS uses `lsphp` binaries, Nginx uses system PHP).

### Building Your Own Pairwise Matrix

For PR-specific parameters not listed above:

1. **List parameters:** Identify 2-4 key parameters from the PR's branching logic
2. **List values:** 2-4 valid values per parameter
3. **Build pairs:** For each pair of parameters, ensure every combination of their values appears in at least one row
4. **Minimum test count:** For N parameters with V values each, pairwise needs roughly V² tests (vs V^N for full combinatorial). Example: 3 params × 4 values = ~16 pairwise tests instead of 64 full

**Practical rule:** If the matrix exceeds 15 test cases, focus on the highest-risk pairs first — combinations involving different server stacks or billing plans are more likely to have bugs than combinations of cosmetic parameters.

### How to Create Test Data for Combinations

Most combinations require Tinker-created records (see `references/environment-setup.md` "Creating Test Servers & Sites"):

```php
// Create servers for each stack you need to test
$nginxServer = Server::create([...  'stack' => 'nginx' ...]);
$olsServer = Server::create([... 'stack' => 'openlitespeed' ...]);

// Create sites for each type × stack combination
$wpOnNginx = Site::create([... 'server_id' => $nginxServer->id, 'type' => 'wordpress' ...]);
$wpOnOls = Site::create([... 'server_id' => $olsServer->id, 'type' => 'wordpress' ...]);
```

Track every record — they all must be cleaned up in Step 8.

### Report Format

Present combinatorial test results as a matrix table:

```markdown
### 4.17 Combinatorial / Pairwise Testing — PASS

**Parameters tested:** Server stack × PHP version × Operation

| # | Stack | PHP Version | Operation | Expected | Actual | Evidence | Verdict |
|---|-------|-------------|-----------|----------|--------|----------|---------|
| 1 | nginx | 8.2 | install | Installed via apt | Installed | ![](qa-screenshots/XX.png) | PASS |
| 2 | OLS | 8.3 | install | Installed via lsphp | Installed | ![](qa-screenshots/XX.png) | PASS |
| 3 | nginx | 8.4 | switch | Default version changed | Changed | Tinker: php_version=8.4 | PASS |
```

**Checklist:**
- Identify all parameters the PR branches on (stack, type, version, role, plan)
- Build a pairwise matrix covering all 2-way parameter interactions
- Create Tinker test data for each combination (track all IDs for cleanup)
- For invalid combinations, verify they're rejected gracefully (cross-reference with 4.15)
- Report results as a matrix table showing each combination tested
