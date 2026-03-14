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
