#!/usr/bin/env python3
"""Deploy a PR's exact head commit to a plain SSH staging server (fallback when the xcdev lab is unavailable).

    python3 deploy_to_staging.py --pr 4334 --ssh forge@1.2.3.4 --path /home/forge/staging.tmp1.dev [--skip-build] [--skip-migrate]

Order: fetch refs/pull/<n>/head -> detached checkout of the head commit -> composer -> migrate -> npm build
-> clear caches -> restart queue workers (Horizon keeps running old code otherwise) -> verify HEAD == PR head.
Refuses to run over uncommitted changes on the server instead of stashing them silently.
Requires: gh CLI, ssh.
"""
import argparse
import json
import shlex
import subprocess
import sys

FRONTEND = ("resources/js/", "resources/css/", "resources/sass/", "package.json", "package-lock.json",
            "yarn.lock", "vite.config", "tailwind.config", "postcss.config")


def run(cmd: list, timeout: int = 300) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip()[-800:] or f"failed: {' '.join(cmd)}")
    return r.stdout.strip()


def remote(ssh: str, path: str, cmd: str, timeout: int = 300) -> str:
    return run(["ssh", ssh, f"cd {shlex.quote(path)} && {cmd}"], timeout=timeout)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--pr", required=True, type=int)
    p.add_argument("--ssh", required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--skip-build", action="store_true", help="skip composer and npm")
    p.add_argument("--skip-migrate", action="store_true")
    a = p.parse_args()

    info = json.loads(run(["gh", "pr", "view", str(a.pr), "--json", "title,state,headRefOid,headRefName,files"]))
    head = info["headRefOid"]
    files = [f["path"] for f in info.get("files", [])]
    print(f"PR #{a.pr} {info['title']} [{info['state']}] head {head[:10]} ({info['headRefName']})")

    steps = []
    dirty = remote(a.ssh, a.path, "git status --porcelain --untracked-files=no")
    if dirty:
        print("ERROR: uncommitted changes on the server; resolve them first (not stashing silently):\n" + dirty)
        return 1
    steps.append(("fetch PR head", f"git fetch origin {shlex.quote(f'refs/pull/{a.pr}/head')}", 300))
    steps.append(("checkout head", f"git checkout --detach {shlex.quote(head)}", 120))
    if not a.skip_build and any(f in ("composer.json", "composer.lock") for f in files):
        steps.append(("composer install", "composer install --no-interaction --prefer-dist --optimize-autoloader", 900))
    if not a.skip_migrate:
        steps.append(("migrate", "php artisan migrate --force", 600))
    if not a.skip_build and any(f.startswith(FRONTEND) for f in files):
        steps.append(("npm build", "npm ci && npm run build", 900))
    steps.append(("clear caches", "php artisan optimize:clear", 120))
    steps.append(("restart workers", "(php artisan horizon:terminate || php artisan queue:restart)", 120))

    for i, (name, cmd, timeout) in enumerate(steps, 1):
        print(f"[{i}/{len(steps)}] {name} ...", end=" ", flush=True)
        try:
            out = remote(a.ssh, a.path, cmd, timeout)
            print("ok" + (" (nothing to migrate)" if "Nothing to migrate" in out else ""))
        except RuntimeError as e:
            print(f"FAILED\n{e}")
            return 1

    deployed = remote(a.ssh, a.path, "git rev-parse HEAD")
    if deployed != head:
        print(f"ERROR: server HEAD {deployed[:10]} != PR head {head[:10]}")
        return 1
    print(f"Deployed PR #{a.pr} @ {head[:10]} (detached). Queue workers restarted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
