#!/usr/bin/env python3
"""Merge, validate and render an xcloud-test run.

    results.py merge  ~/.xcloud-qa/pr<N>   # checks results/ against plan.md, prints problems (exit 1 if any)
    results.py report ~/.xcloud-qa/pr<N>   # writes report.md and comment.md, prints the suggested verdict

plan.md check lines look like `C-03  [role] user2 opens ...` (black-box findings: `BB-01  [bb] ...`); a `[primary]` tag marks the PR's primary claim
and `source: suspect` marks a suspect: both decide the verdict. facts.json and results/<id>.json follow
references/executor.md.
"""
import json
import re
import sys
from pathlib import Path

CHECK_LINE = re.compile(r"^\s*((?:C|BB)-[\w-]+)\s+(?:\[([^\]]+)\]\s+)?(.*)$")
SECRET = re.compile(
    r"(cfast_[A-Za-z0-9]+|\b[0-9a-f]{32}\.access\b|-----BEGIN [A-Z ]*PRIVATE KEY|"
    r"(?i:(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*(?!\[redacted\])[^\s\"',]{6,})|"
    r"\b\d+\|[A-Za-z0-9]{40}\b)"
)
ICON = {"PASS": "✅", "FAIL": "❌", "BLOCKED": "⚠️"}
SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, None: 4}


def load_plan(run: Path) -> dict:
    checks, current = {}, None
    plan = run / "plan.md"
    if not plan.exists():
        return checks
    for line in plan.read_text().splitlines():
        m = CHECK_LINE.match(line)
        if m:
            current = m.group(1)
            tags = (m.group(2) or "").lower()
            checks[current] = {"title": m.group(3).strip(), "primary": "primary" in tags, "suspect": False}
        elif current and "source:" in line and "suspect" in line.lower():
            checks[current]["suspect"] = True
    return checks


def load_results(run: Path) -> dict:
    out = {}
    for f in sorted((run / "results").glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            out[f.stem] = {"id": f.stem, "result": "BLOCKED", "_invalid": str(e)}
            continue
        out[data.get("id", f.stem)] = data
    return out


def screenshots(r: dict) -> list:
    return [e for e in (r.get("evidence") or []) if e.get("kind") == "screenshot"]


def public(url) -> bool:
    return bool(url) and url.startswith("http") and "evidence_url" not in url


def warnings_for(cid: str, r: dict) -> list:
    """Screenshot gaps: reported, never blocking (some checks have nothing to show)."""
    w = []
    shots = screenshots(r)
    if r.get("result") in ("PASS", "FAIL") and not shots and not r.get("no_screenshot"):
        w.append(f"{cid}: no screenshot and no no_screenshot reason")
    for e in shots:
        if not e.get("url") and not e.get("path"):
            w.append(f"{cid}: screenshot entry has neither url nor path")
        elif e.get("path") and not Path(e["path"]).expanduser().exists():
            w.append(f"{cid}: screenshot file missing: {e['path']}")
        elif not public(e.get("url")):
            w.append(f"{cid}: screenshot not published yet ({e.get('path') or e.get('url')})")
    return w


def problems_for(cid: str, r: dict) -> list:
    p = []
    if "_invalid" in r:
        return [f"{cid}: result file is not valid JSON ({r['_invalid']})"]
    res = r.get("result")
    if res not in ICON:
        p.append(f"{cid}: result must be PASS, FAIL or BLOCKED (got {res!r})")
    evidence = r.get("evidence") or []
    if res in ("PASS", "FAIL") and not any((e.get("excerpt") or e.get("url")) for e in evidence):
        p.append(f"{cid}: {res} without an evidence excerpt or screenshot")
    sentinel = r.get("sentinel") or {}
    if res == "PASS" and sentinel and not sentinel.get("clean", True) and "sentinel" not in (r.get("notes") or "").lower():
        p.append(f"{cid}: PASS but the sentinel is not clean and notes do not explain why")
    if res == "FAIL" and not r.get("repro"):
        p.append(f"{cid}: FAIL without repro steps")
    if res == "FAIL" and not r.get("severity"):
        p.append(f"{cid}: FAIL without a severity")
    if not r.get("expected"):
        p.append(f"{cid}: no expected result recorded")
    if SECRET.search(json.dumps(r)):
        p.append(f"{cid}: looks like it contains a secret: redact before sharing")
    return p


def merge(run: Path) -> int:
    plan, results = load_plan(run), load_results(run)
    problems = [f"{cid}: in plan.md but no results/{cid}.json" for cid in plan if cid not in results]
    problems += [f"{cid}: result without a plan.md line" for cid in results if cid not in plan]
    warnings = []
    for cid, r in results.items():
        problems += problems_for(cid, r)
        warnings += warnings_for(cid, r)
    counts = {k: sum(1 for r in results.values() if r.get("result") == k) for k in ICON}
    print(json.dumps({"checks": len(plan), "results": len(results), **counts, "problems": problems,
                      "screenshot_warnings": warnings}, indent=1))
    return 1 if problems else 0


def verdict(plan: dict, results: dict) -> tuple:
    reasons = []
    for cid, r in results.items():
        key = plan.get(cid, {})
        decisive = key.get("primary") or key.get("suspect")
        res, sev = r.get("result"), r.get("severity")
        if res == "FAIL" and (r.get("regression") or (decisive and sev in ("critical", "high")) or sev == "critical") \
                and not r.get("pre_existing"):
            reasons.append(f"{cid} {sev or ''} {r.get('title', '')}".strip())
    if reasons:
        return "❌ NEEDS CHANGES", reasons
    blocked = [cid for cid, r in results.items() if r.get("result") == "BLOCKED" and plan.get(cid, {}).get("primary")]
    missing = [cid for cid, k in plan.items() if k.get("primary") and cid not in results]
    if blocked or missing:
        return "⚠️ PARTIALLY VERIFIED", [f"{c} not verified" for c in blocked + missing]
    return "✅ READY TO MERGE", []


def ev_lines(r: dict) -> list:
    out = []
    for e in r.get("evidence") or []:
        line = f"- {e.get('kind', 'evidence')}: {e.get('summary', '')}"
        if e.get("env"):
            line += f" ({e['env']})"
        if e.get("kind") == "screenshot" and public(e.get("url")):
            out += [line, "", f"  ![{e.get('summary', 'screenshot')}]({e['url']})", ""]
            continue
        if e.get("url"):
            line += f" — [link]({e['url']})"
        elif e.get("path"):
            line += f" — local: `{e['path']}` (not uploaded)"
        out.append(line)
        if e.get("excerpt"):
            out += ["  ```", *[f"  {x}" for x in str(e["excerpt"]).splitlines()[:15]], "  ```"]
    return out


def report(run: Path) -> int:
    plan, results = load_plan(run), load_results(run)
    facts = json.loads((run / "facts.json").read_text()) if (run / "facts.json").exists() else {}
    pr = facts.get("pr", run.name.replace("pr", ""))
    v, reasons = verdict(plan, results)
    order = sorted(results, key=lambda c: (c not in plan, list(plan).index(c) if c in plan else 0))

    def row(cid):
        r = results[cid]
        base = r.get("baseline") or {}
        note = (r.get("observed") or "")[:110]
        if base.get("observed"):
            note += f" (dev: {base['observed'][:50]})"
        title = r.get("title") or plan.get(cid, {}).get("title", "")
        return f"| {cid} | {title[:80]} | {ICON.get(r.get('result'), '?')} | {note.replace('|', '/')} |"

    fails = [results[c] for c in order if results[c].get("result") == "FAIL"]
    this_pr = sorted([r for r in fails if not r.get("pre_existing")], key=lambda r: SEV_ORDER.get(r.get("severity"), 4))
    pre = [r for r in fails if r.get("pre_existing")]

    comment = [f"🤖 **QA — PR #{pr}**: {v}", ""]
    if facts.get("tested_line"):
        comment += [facts["tested_line"], ""]
    comment += ["| # | Check | Result | Note |", "|---|---|---|---|", *[row(c) for c in order], ""]
    if this_pr:
        comment += ["**Findings in this PR**"] + [f"{i}. {r.get('severity')} — {r.get('title')} ({r.get('id')})" for i, r in enumerate(this_pr, 1)] + [""]
    if pre:
        comment += ["**Pre-existing on dev** (follow-up, not blocking)"] + [f"- {r.get('title')} ({r.get('id')})" for r in pre] + [""]
    shot_order = [r for r in this_pr] + [results[c] for c in order if plan.get(c, {}).get("primary") and results[c] not in this_pr]
    shot_lines = []
    for r in shot_order:
        for e in screenshots(r):
            if public(e.get("url")):
                shot_lines.append(f"<details><summary>{r.get('id')} — {e.get('summary', '')} ({e.get('env', 'preview')})</summary>\n\n![{r.get('id')}]({e['url']})\n</details>")
    if shot_lines:
        comment += ["**Screenshots**", *shot_lines, ""]
    unpublished = [f"{r.get('id')}" for r in results.values() for e in screenshots(r) if not public(e.get("url"))]
    comment += ["<summary: edit me> · Full report: <link>"]

    full = [f"# QA report — PR #{pr}", "", f"**Verdict: {v}**", ""]
    full += [f"- {x}" for x in reasons] + ([""] if reasons else [])
    full += ["## Results", "", "| # | Check | Result | Note |", "|---|---|---|---|", *[row(c) for c in order], ""]
    for cid in order:
        r = results[cid]
        full += [f"### {cid} — {r.get('title', '')} — {r.get('result')}", "",
                 f"- Expected: {r.get('expected', '')}", f"- Observed: {r.get('observed', '')}"]
        if r.get("baseline"):
            full.append(f"- Baseline ({r['baseline'].get('environment', 'ci/dev')}): {r['baseline'].get('observed', '')}")
        s = r.get("sentinel") or {}
        if s:
            full.append(f"- Sentinel: {'clean' if s.get('clean') else 'NOT clean'} "
                        f"{json.dumps({k: s[k] for k in ('new_errors', 'failed_tasks') if s.get(k)})[:300]}")
        full += ev_lines(r)
        if r.get("repro"):
            full += ["", "Repro:"] + [f"{i}. {s}" for i, s in enumerate(r["repro"], 1)]
        if r.get("no_screenshot"):
            full.append(f"- No screenshot: {r['no_screenshot']}")
        if r.get("notes"):
            full.append(f"\nNotes: {r['notes']}")
        full.append("")
    full += ["## Pre-existing findings", *([f"- {r.get('title')} ({r.get('id')})" for r in pre] or ["- none"]), "",
             "## Not covered", "- <edit: each gap and why>", "",
             "## Environment", "```json", json.dumps({k: facts[k] for k in facts if k != "tokens"}, indent=1)[:4000], "```"]

    (run / "comment.md").write_text("\n".join(comment) + "\n")
    (run / "report.md").write_text("\n".join(full) + "\n")
    print(json.dumps({"verdict": v, "reasons": reasons, "unpublished_screenshots": sorted(set(unpublished)), "report": str(run / "report.md"), "comment": str(run / "comment.md")}, indent=1))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("merge", "report"):
        sys.exit(__doc__)
    run_dir = Path(sys.argv[2])
    sys.exit(merge(run_dir) if sys.argv[1] == "merge" else report(run_dir))
