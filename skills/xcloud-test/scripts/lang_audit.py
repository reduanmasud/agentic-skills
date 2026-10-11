#!/usr/bin/env python3
"""Static language audit of a PR for xCloud (run from the xCloud checkout).

    lang_audit.py --base origin/dev --head origin/pr/<N>     # strings this PR adds or changes
    lang_audit.py --all                                      # whole repo: coverage + placeholder parity

How xCloud translates (verified 2026-10-07):
- Vue: vue-i18n `$t('English text')` / `t('English text')`; keys ARE the English text, messages lazy-load
  from resources/lang/<lang>.json; silentTranslationWarn is on, so a missing key silently shows English.
- PHP: `__('English text')` / `trans()` / `@lang()` against the same JSON files, and dotted group keys
  (`emails.subject`) against resources/lang/<lang>/<group>.php: a missing group key shows the RAW key.
- Locale: users.language (POST /user/language {lang}), else the white-label brand's language;
  notifications use teams.notification_language (or the brand's).

Static findings are leads, not verdicts: confirm each on the running page or email (references/language.md).
"""
import argparse
import json
import re
import subprocess
import sys

LANG_DIR = "resources/lang"
CALL = re.compile(r"""(?:\$t|(?<![\w$.])t|__|trans|trans_choice|@lang)\(\s*(['"])((?:\\.|(?!\1).)+)\1""")
PLACEHOLDER = re.compile(r":[a-zA-Z_]+|\{[a-zA-Z_0-9]+\}")
GROUP_KEY = re.compile(r"^[a-z][a-z0-9_-]*\.[a-zA-Z0-9_.-]+$")
# literal text between tags, or in user-facing attributes, on an added Vue/Blade line without a translation call
TEMPLATE_TEXT = re.compile(r">\s*([^<>{}]*[A-Za-z]{3,}[^<>{}]*?)\s*<")
ATTR_TEXT = re.compile(r"""\b(?:placeholder|title|label|aria-label|tooltip|text)\s*=\s*"([^"{}]*[A-Za-z]{3,}[^"{}]*)\"""")
SOURCE_EXT = (".vue", ".js", ".ts", ".php")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def lang_files(ref: str) -> dict:
    """{lang: messages} for every resources/lang/<lang>.json at ref."""
    out = {}
    for path in git("ls-tree", "--name-only", f"{ref}:{LANG_DIR}").split():
        if path.endswith(".json"):
            try:
                out[path[:-5]] = json.loads(git("show", f"{ref}:{LANG_DIR}/{path}"))
            except (subprocess.CalledProcessError, json.JSONDecodeError):
                out[path[:-5]] = {}
    return out


def group_has(ref: str, lang: str, key: str) -> bool:
    group, _, rest = key.partition(".")
    try:
        text = git("show", f"{ref}:{LANG_DIR}/{lang}/{group}.php")
    except subprocess.CalledProcessError:
        return False
    return f"'{rest.split('.')[-1]}'" in text or f'"{rest.split(".")[-1]}"' in text


def looks_like_copy(text: str) -> bool:
    """Visible words, not code: skips identifiers ('hidden'), expressions and URLs."""
    if not text or text.startswith(("http", "/", "#", "@", "$")) or "$t" in text:
        return False
    if re.search(r"\?\.|===|!==|&&|\|\||=>|\(\)|\bprops\.|\bthis\.", text):
        return False
    return " " in text or text[:1].isupper()


def placeholders(s: str) -> list:
    return sorted(PLACEHOLDER.findall(s))


def added_lines(base: str, head: str) -> list:
    """[(file, line_no, text)] for lines the PR adds in source files."""
    diff = git("diff", "-U0", f"{base}...{head}", "--", *[f"*{e}" for e in SOURCE_EXT])
    out, file, line_no = [], None, 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            file = raw[6:] if raw.startswith("+++ b/") else None
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line_no = int(m.group(1)) if m else 0
        elif raw.startswith("+") and file and not file.startswith(f"{LANG_DIR}/"):
            out.append((file, line_no, raw[1:]))
            line_no += 1
    return out


def audit_pr(base: str, head: str) -> dict:
    langs = lang_files(head)
    en = langs.get("en", {})
    others = sorted(k for k in langs if k != "en")
    findings, seen = [], set()
    for file, line, text in added_lines(base, head):
        keys = [m.group(2) for m in CALL.finditer(text)]
        for key in keys:
            if key in seen:
                continue
            seen.add(key)
            if GROUP_KEY.match(key) and key not in en:
                missing = [l for l in ["en", *others] if not group_has(head, l, key)]
                if missing:
                    findings.append({"type": "MISSING_GROUP_KEY", "severity": "high" if "en" in missing else "medium",
                                     "file": file, "line": line, "key": key, "languages_missing": missing,
                                     "effect": "raw key shown (e.g. 'emails.subject') where missing"})
                continue
            if key not in en:
                findings.append({"type": "NOT_IN_LANG_FILES", "severity": "medium", "file": file, "line": line, "key": key,
                                 "effect": "not in en.json, so no language translates it: English for every user"})
                continue
            missing = [l for l in others if key not in langs[l]]
            if missing:
                findings.append({"type": "UNTRANSLATED", "severity": "medium", "file": file, "line": line, "key": key,
                                 "languages_missing": missing, "effect": "silently shown in English to those users"})
            src = placeholders(en.get(key, key))
            bad = [l for l in others if key in langs[l] and isinstance(langs[l][key], str) and placeholders(langs[l][key]) != src]
            if bad:
                findings.append({"type": "PLACEHOLDER_MISMATCH", "severity": "high", "file": file, "line": line, "key": key,
                                 "languages": bad, "effect": "values dropped or shown as ':name' in those languages"})
        if file.endswith((".vue", ".blade.php")) and not keys and "<script" not in text:
            for rx in (TEMPLATE_TEXT, ATTR_TEXT):
                for m in rx.finditer(text):
                    literal = m.group(1).strip()
                    if looks_like_copy(literal):
                        findings.append({"type": "HARDCODED_CANDIDATE", "severity": "medium", "file": file, "line": line,
                                         "text": literal[:120], "effect": "not translatable; confirm on the page in another language"})
    counts = {}
    for f in findings:
        counts[f["type"]] = counts.get(f["type"], 0) + 1
    return {"base": base, "head": head, "languages": ["en", *others], "strings_checked": len(seen),
            "counts": counts, "findings": findings}


def audit_all(ref: str) -> dict:
    langs = lang_files(ref)
    en = langs.get("en", {})
    report = {"en_keys": len(en), "languages": {}}
    for l in sorted(k for k in langs if k != "en"):
        d = langs[l]
        mismatch = [k for k, v in d.items() if isinstance(v, str) and k in en and isinstance(en[k], str)
                    and placeholders(v) != placeholders(en[k])]
        report["languages"][l] = {"missing": len(set(en) - set(d)), "placeholder_mismatch": mismatch[:10]}
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--base")
    p.add_argument("--head", default="HEAD")
    p.add_argument("--all", action="store_true")
    a = p.parse_args()
    if a.all:
        result = audit_all(a.head)
    elif a.base:
        result = audit_pr(a.base, a.head)
    else:
        p.error("give --base <ref> [--head <ref>] or --all")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
