# Test Case Template

## Test Case List Format

Use this format for generating test cases during QA sessions. Every test case must have a number, description, expected result, and evidence type.

### Standard Test Case Table

```markdown
| # | Test Case | Expected Result | Evidence |
|---|-----------|-----------------|----------|
| TC-1 | [Specific action to perform] | [What should happen] | [Screenshot / curl / Tinker / SSH] |
```

### Example (filled):

| # | Test Case | Expected Result | Evidence |
|---|-----------|-----------------|----------|
| TC-1 | Navigate to Dashboard as paid user | Page loads, no 500 errors, console clean | Screenshot |
| TC-2 | Click Security tab on Traffic Analytics | Security tab content loads with 4 sections | Screenshot |
| TC-3 | Access security API without auth token | 401 Unauthenticated | curl output |
| TC-4 | Block IP 10.20.30.40 via Block IP button | Confirmation dialog → IP added to blacklist → button shows "Blocked" | Screenshot + Tinker |

---

## Business Logic Validation (BLV) Test Cases

BLV test cases are special — they test what the feature SHOULD do, not what it currently does. They are designed to FAIL if the logic is flawed.

### BLV Test Case Format

```markdown
| # | Test Case | If Logic Correct | If Logic Flawed | Actual | Verdict |
|---|-----------|------------------|-----------------|--------|---------|
| [BLV] TC-N | [Scenario] | [Expected behavior] | [Flawed behavior] | [What happened] | PASS / LOGIC FLAW |
```

### Example (filled):

| # | Test Case | If Logic Correct | If Logic Flawed | Actual | Verdict |
|---|-----------|------------------|-----------------|--------|---------|
| [BLV] TC-31 | 1 request to /wp-login.php from new IP | NOT flagged as threat | Flagged as LOW threat | Flagged as LOW | **LOGIC FLAW** |
| [BLV] TC-32 | 50 requests to /xmlrpc.php in 1 minute from same IP | Flagged as MEDIUM+ threat | May not flag correctly | Flagged as LOW | **LOGIC FLAW** |
| [BLV] TC-33 | Legitimate user with Chrome 89 browsing normally | NOT flagged | Flagged as Outdated UA | Flagged | **LOGIC FLAW** |

---

## Traceability Matrix Format

Maps every changed file to test cases. No file should have 0 tests.

```markdown
| Changed File | What Changed | Test Cases | Coverage |
|---|---|---|---|
| ControllerName.php | New method: fetchData | TC-1, TC-3, TC-5, TC-7 | 4 tests |
| ComponentName.vue | New UI section | TC-2, TC-4, TC-6 | 3 tests |
```

**Rules:**
- Every changed file needs at least 1 test case
- Controllers/Services: at least 2 per changed method (happy + negative)
- Vue components: at least 1 UI interaction test
- Policies: at least 2 role-based tests (authorized + unauthorized)
- Migrations: at least 1 DB verification via Tinker

---

## Test Execution Log Format

During testing, report progress in this format:

```
[TC-1/48] Smoke: Dashboard loads → PASS
[TC-2/48] Smoke: Traffic Analytics page loads with Security tab → PASS
[TC-3/48] Smoke: Console errors clean → PASS (only DuckDuckGo favicon 404)
[TC-4/48] Sanity: Security tab loads with 4 sections → PASS
...
[BLV] [TC-31/48] Logic: Single login request flagged as threat → LOGIC FLAW
```

---

## Test Results Summary Table (for Report)

```markdown
| Category | Result | Details |
|----------|--------|---------|
| Smoke Testing | PASS/FAIL | [brief summary] |
| Sanity Testing | PASS/FAIL | [brief summary] |
| End-to-End | PASS/FAIL | [brief summary] |
| Security Testing | PASS/FAIL | [brief summary] |
| Role-Based | PASS/FAIL | [brief summary] |
| Regression | PASS/FAIL | [brief summary] |
| Business Logic | PASS/FAIL/LOGIC FLAW | [brief summary — this drives the verdict] |
```

---

## Minimum Test Case Counts

| PR Scope | Minimum | Target | BLV Minimum |
|----------|---------|--------|-------------|
| Small (1-3 files) | 15 | 25+ | 3 if logic gaps found |
| Medium (4-10 files) | 30 | 50+ | 5 if logic gaps found |
| Large (10+ files) | 50 | 80+ | 8 if logic gaps found |

If you generate fewer than the minimum, go back through the exhaustive method (Steps A-F in the skill) and check what you missed.

---

## Verdict Rules

| Condition | Verdict |
|-----------|---------|
| All tests pass, no logic flaws | **PASS** |
| All tests pass, minor observations only | **PASS** (with observations) |
| Tests pass but BLV reveals core logic flaw | **FAIL** (logic flaw) |
| User confirms logic flaw is intentional | **CONDITIONAL PASS** |
| Any critical/high bug found | **FAIL** |
| Feature doesn't work as described in PR | **FAIL** |
