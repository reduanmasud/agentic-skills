# Report — shape and verdict

`scripts/results.py report ~/.xcloud-qa/pr<N>` renders `report.md` (full) and `comment.md` (compact, for the PR)
from `plan.md`, `facts.json` and `results/*.json`. Then the main session edits the prose: the summary, and
which findings belong to this PR versus `dev`.

## Verdict rules

| Verdict | When |
|---|---|
| ❌ **NEEDS CHANGES** | any FAIL with `regression: true`, or a FAIL of a primary check or suspect with severity critical/high; behaviour that contradicts the issue or the PR's own description; a role or team boundary broken; a success screen over a failed task or logged error; a logic flaw that misleads customers; the PR is superseded by `dev` |
| ⚠️ **PARTIALLY VERIFIED** | a primary check BLOCKED; the bug could not be reproduced on `ci/dev` first; a stack/release the change touches was not covered |
| ✅ **READY TO MERGE** | every primary check and suspect PASS with evidence, the sentinel clean, no failure mode worse than `dev`'s |
| **CONDITIONAL** | a flaw the user explicitly confirmed as intended: name who confirmed it and when |

- **Pre-existing** findings (same on `dev`) are listed in their own section and never decide the verdict, unless
  the PR claims to fix them or makes them worse.
- When in doubt between READY and PARTIALLY VERIFIED, choose PARTIALLY VERIFIED and say what is missing.
- Security findings (cross-team access, data exposure): describe in general terms in the PR comment; the exact
  route and steps go into a private issue or the KazTrack doc.

## comment.md (one PR comment, updated in place)

```
🤖 **QA — PR #<N>**: <verdict>

Tested: `<branch>` <merged onto dev @ sha | head @ sha> on the xcdev lab · <servers: Ubuntu/stack/DB list> ·
roles: <accounts> · baseline: ci/dev @ <sha>

| # | Check | Result | Note |
|---|---|---|---|
| C-01 | <primary claim> | ✅ / ❌ / ⚠️ | one line (dev: <baseline>) |

**Findings in this PR**
1. <severity> — <one line> (C-xx)

**Pre-existing on dev** (follow-up issues, not blocking)
- …

<2-4 sentence summary> · Full report: <KazTrack link or "local">
```

## report.md (full)

1. Verdict and why (3 lines)
2. What the PR claims, and the spec it was tested against (S/N lines, short)
3. Suspects: spec vs code differences, and what each turned out to be
4. Environment: preview sha + mode, baseline sha, servers (release, stack, DB), sites, accounts and fixtures,
   planted customer states
5. Results: one section per check: expected, observed, baseline, sentinel, evidence (excerpts, screenshot links),
   repro steps for every FAIL
6. Findings in this PR (severity order), each with repro steps and evidence; black-box (`BB-`) findings
   marked as such
6b. Language: the static audit's counts for this PR's strings, the languages checked live, and each confirmed
   `[lang]` finding (screenshot or email excerpt, language named)
7. Pre-existing findings
8. Not covered, and why (each one; the reader decides whether it matters)
9. Lab friction (one line each; also sent with `report_friction`)
10. Cleanup: what was created and removed

Screenshots are required in both forms: `report.md` embeds every check's shots under its section, `comment.md`
gets a `**Screenshots**` block (findings first, then primary claim, preview vs `ci/dev`). `page_check` `evidence_url`
links need lab Access, so before `results.py report`:
1. `page_check` shots without a public URL: `evidence_publish {id}`.
2. Local files: the uploader does not recurse, so run it once per folder (`lab-flow.mjs` writes `evidence/<check-id>/`):
   `for d in ~/.xcloud-qa/pr<N>/evidence ~/.xcloud-qa/pr<N>/evidence/*/; do python3 ~/.claude/skills/xcloud-test/scripts/upload_screenshots.py --dir "$d" --pr <N> --json; done`
   (Cloudinary; check `CLOUDINARY_*` env first) and write each URL into the matching evidence entry's `url`.
3. Read every image: it shows the claim and no secret.
