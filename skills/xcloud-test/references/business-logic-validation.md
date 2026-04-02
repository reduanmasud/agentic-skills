# Business Logic Validation Reference

## Why This Exists

Code-conformance testing answers: "Does the code do what the code says?"
Business logic validation answers: "Does the code do what it SHOULD do?"

If a "Threat Detection" feature flags every single request as a threat, code-conformance testing will PASS — the code does exactly what it says. But the feature is broken because the **logic itself is wrong**. This reference teaches you how to catch that.

## When Business Logic Fails = Feature FAIL

**Rule: A business logic flaw in the PR's core feature is a FAIL verdict, not a PASS with observations.**

| Scenario | Verdict |
|----------|---------|
| Feature works as coded, logic is correct | PASS |
| Feature works as coded, minor logic concern (edge case, cosmetic) | PASS with observations |
| Feature works as coded, core logic is flawed (false positives, wrong thresholds, misleading output) | **FAIL** |
| Feature works as coded, core logic is flawed BUT user confirms it's intentional | CONDITIONAL PASS (document user's confirmation) |

A feature that produces misleading results for users is **not working correctly**, even if the code runs without errors.

## The Five-Lens Evaluation

For every feature, evaluate through these lenses BEFORE testing:

### Lens 1: User Perspective
- What would a user of this platform expect this feature to do?
- If the feature shows "4 attackers detected" but 3 are legitimate users, would the user trust it?
- Would a non-technical user be misled by the output?

### Lens 2: Domain Standards
- What do industry standards say? (OWASP, CIS Benchmarks, vendor docs)
- How do competing platforms handle the same feature?
- Are there established thresholds or best practices?

### Lens 3: Common Sense Thresholds
- Does the feature have numeric thresholds? Are they reasonable?
- Is there a minimum floor? (e.g., 1 request should never be flagged as a "threat")
- Would the thresholds produce false positives in normal usage?

### Lens 4: Competitor Behavior
- How do Laravel Forge, Ploi, RunCloud, Cloudways handle this?
- Is xCloud's approach significantly different? If so, is it justified?

### Lens 5: Failure Consequences
- If this logic is wrong, what happens to users?
- Data loss? Security breach? Billing errors? Loss of trust?
- Is this a high-consequence domain where "close enough" is unacceptable?

## How to Apply to Test Cases

### Step 1: Define Expected Behavior BEFORE Reading Code

Write down what the feature SHOULD do based on its name, description, and domain knowledge. Do this BEFORE looking at the implementation details.

```
Feature: Threat Detection
Expected: Flag IPs that exhibit attack patterns (high volume of requests
to sensitive endpoints within a short time window). A single request to
wp-login.php is NOT a threat — it's a user logging in.
```

### Step 2: Compare Expected vs Actual

Read the implementation. For each behavior, classify:

| Expected Behavior | Actual Implementation | Match? |
|---|---|---|
| Minimum request threshold before flagging | No minimum — 1 request = flagged | **MISMATCH** |
| Different weights for different attack types | All types weighted equally | **PARTIAL** |
| Distinguish login attempts from brute force | Any wp-login.php request = suspicious | **MISMATCH** |

### Step 3: Generate BLV Test Cases

For each MISMATCH, create a test case that tests the EXPECTED behavior:

```
[BLV] TC-31: Single legitimate login should NOT be flagged
  Action: 1 POST request to /wp-login.php with valid credentials
  Expected (correct): Not flagged as threat
  Expected (if logic flawed): Flagged as LOW threat
  Verdict: If flagged → LOGIC FLAW (not a bug — a design error)
```

### Step 4: Apply Verdict

- If BLV test cases reveal the core feature produces misleading results → **FAIL**
- If BLV test cases reveal edge-case concerns only → **PASS with observations**
- If user confirms the behavior is intentional → **CONDITIONAL PASS**

## Common Business Logic Mistakes in xCloud

| Feature Type | Common Logic Flaw | How to Catch |
|---|---|---|
| **Threat detection** | No minimum threshold — flags legitimate traffic | Check: does 1 normal request trigger an alert? |
| **Resource limits** | Off-by-one errors — allows limit+1 resources | Test at exact boundary: create limit, then limit+1 |
| **Billing guards** | Checks plan but not trial status, or vice versa | Test: paid user, free user, trial user, expired trial |
| **Rate limiting** | Counts across all users instead of per-user | Test: 2 users each making half the limit |
| **Permission checks** | Frontend hides UI but backend allows API call | Test: hide button for role X, then call API directly as role X |
| **Status transitions** | Allows invalid state changes (e.g., "running" → "provisioning") | Map the state machine, test every disallowed transition |
| **Time-based features** | Uses server timezone instead of user timezone | Test with UTC+12 and UTC-12 users |
| **Percentage calculations** | Division by zero when no data exists | Test with empty dataset |

## Confidence Levels and Interaction Rules

| Confidence | What it means | Action |
|---|---|---|
| **High** | Clear domain standard exists (OWASP, RFC, vendor docs) | Flag as finding, generate BLV test cases automatically |
| **Medium** | Best practices exist but implementations vary | Ask user to confirm before generating BLV test cases |
| **Low** | Agent's judgment call, no clear standard | Present as suggestion, don't generate BLV test cases without user approval |

**CRITICAL CHANGE**: Even at medium/low confidence, if the user confirms the logic is flawed during testing (as happened with the threat threshold issue), immediately upgrade to high confidence and change the verdict to FAIL.

## Verdict Decision Tree

```
Is the core feature's logic correct?
├── YES → Continue to code-conformance testing → PASS/FAIL based on bugs
├── PARTIALLY → Are the gaps in the core behavior or edge cases?
│   ├── Core behavior → FAIL (misleading to users)
│   └── Edge cases → PASS with observations
├── NO → FAIL
└── UNCERTAIN → Ask user
    ├── User says "intentional" → CONDITIONAL PASS
    ├── User says "good catch, it's a bug" → FAIL
    └── User doesn't respond → Test as-is, note in observations
```

## Example: PR #4334 Security Analytics

**What went wrong in the original QA:**
1. Step 1.4 correctly identified the threat threshold gap
2. But classified it as "medium confidence" and downgraded to "observation"
3. Verdict was PASS despite the feature producing false positives
4. User had to point out that a single request being flagged as a threat is an implementation problem

**What should have happened:**
1. Step 1.4 identifies: "1 request = LOW threat" has no minimum floor
2. Generates BLV test case: "1 request to wp-login.php should NOT be flagged"
3. BLV test FAILS (the feature flags it) → Logic Flaw identified
4. User confirms during testing: "this is an implementation problem"
5. Verdict: **FAIL** — core feature produces false positives that mislead users
