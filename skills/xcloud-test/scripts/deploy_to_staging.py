#!/usr/bin/env python3
"""
Deploy a PR branch to the xCloud staging server via SSH.

Usage:
    python3 deploy_to_staging.py --pr 4334 --ssh "forge@46.250.234.27" --path "/home/forge/staging.tmp1.dev"
    python3 deploy_to_staging.py --pr 4334 --ssh "forge@1.2.3.4" --path "/home/forge/app" --skip-build
    python3 deploy_to_staging.py --pr 4334 --ssh "forge@1.2.3.4" --path "/home/forge/app" --skip-migrate

Requires: gh CLI, ssh
"""

import argparse
import json
import subprocess
import sys


def run(cmd, capture=True, timeout=300):
    """Run a shell command and return stdout. Raises on failure."""
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Command failed: {cmd}")
    return result.stdout.strip() if capture else ""


def ssh_run(ssh_target, app_path, cmd, timeout=300):
    """Run a command on the remote server via SSH."""
    full_cmd = f'ssh {ssh_target} "cd {app_path} && {cmd}"'
    return run(full_cmd, timeout=timeout)


def step(num, total, description):
    """Print a step header."""
    print(f"[{num}/{total}] {description}...", end=" ", flush=True)


def ok(detail=""):
    """Print success for current step."""
    msg = f"+ {detail}" if detail else "+"
    print(msg)


def fail(detail=""):
    """Print failure for current step."""
    msg = f"FAILED: {detail}" if detail else "FAILED"
    print(msg)


def get_pr_info(pr_number):
    """Get PR info via gh CLI."""
    raw = run(
        f"gh pr view {pr_number} --json number,title,headRefName,headRefOid,state,mergeCommit"
    )
    return json.loads(raw)


def get_changed_files(pr_number):
    """Get list of changed files in the PR."""
    return run(f"gh pr diff {pr_number} --name-only")


def needs_composer(changed_files):
    """Check if composer install is needed."""
    return any(
        f in ("composer.json", "composer.lock")
        for f in changed_files.splitlines()
    )


def needs_npm_build(changed_files):
    """Check if npm build is needed."""
    frontend_patterns = (
        "resources/js/",
        "resources/css/",
        "resources/sass/",
        "package.json",
        "package-lock.json",
        "vite.config",
        "webpack.mix",
        "tailwind.config",
    )
    return any(
        any(line.startswith(p) or line == p for p in frontend_patterns)
        for line in changed_files.splitlines()
    )


def main():
    parser = argparse.ArgumentParser(description="Deploy a PR branch to xCloud staging")
    parser.add_argument("--pr", required=True, help="PR number")
    parser.add_argument("--ssh", required=True, help="SSH target (e.g., forge@1.2.3.4)")
    parser.add_argument("--path", required=True, help="App path on server (e.g., /home/forge/staging.tmp1.dev)")
    parser.add_argument("--skip-build", action="store_true", help="Skip npm install & build")
    parser.add_argument("--skip-migrate", action="store_true", help="Skip database migrations")
    args = parser.parse_args()

    pr_number = args.pr
    ssh_target = args.ssh
    app_path = args.path

    # --- Get PR info ---
    try:
        pr_info = get_pr_info(pr_number)
    except RuntimeError as e:
        print(f"ERROR: Could not fetch PR #{pr_number}: {e}", file=sys.stderr)
        sys.exit(1)

    state = pr_info.get("state", "UNKNOWN")
    branch = pr_info.get("headRefName", "")
    head_oid = pr_info.get("headRefOid", "")
    merge_commit = pr_info.get("mergeCommit", {})
    merge_oid = merge_commit.get("oid", "") if merge_commit else ""
    title = pr_info.get("title", "")

    print(f"Deploying PR #{pr_number} to {ssh_target}:{app_path}")
    print(f"PR: {title}")
    print(f"PR Status: {state} (branch: {branch})")

    # Determine deploy strategy
    if state == "MERGED":
        # PR is merged — check if branch still exists remotely
        try:
            run(f"git ls-remote --heads origin {branch} | grep {branch}")
            deploy_branch = branch
            strategy = f"Deploy branch {branch} (PR merged, branch still exists)"
        except RuntimeError:
            deploy_branch = "master"
            strategy = "Deploy master (PR merged, branch deleted)"
    elif state == "OPEN":
        deploy_branch = branch
        strategy = f"Deploy branch {branch} (PR open)"
    else:
        print(f"ERROR: PR is {state} — cannot deploy", file=sys.stderr)
        sys.exit(1)

    print(f"Strategy: {strategy}")
    print()

    # --- Get changed files for conditional steps ---
    try:
        changed_files = get_changed_files(pr_number)
    except RuntimeError:
        changed_files = ""

    do_composer = needs_composer(changed_files) and not args.skip_build
    do_npm = needs_npm_build(changed_files) and not args.skip_build
    do_migrate = not args.skip_migrate

    # Calculate total steps
    total_steps = 4  # fetch + checkout + pull + cache clear
    if do_migrate:
        total_steps += 1
    if do_composer:
        total_steps += 1
    if do_npm:
        total_steps += 1
    total_steps += 1  # verify

    current_step = 0

    # --- Step 1: Fetch ---
    current_step += 1
    step(current_step, total_steps, "Fetching origin")
    try:
        ssh_run(ssh_target, app_path, "git fetch origin")
        ok()
    except RuntimeError as e:
        fail(str(e))
        sys.exit(1)

    # --- Step 2: Checkout ---
    current_step += 1
    step(current_step, total_steps, f"Checking out {deploy_branch}")
    try:
        ssh_run(ssh_target, app_path, f"git checkout {deploy_branch}")
        ok()
    except RuntimeError:
        # May need to stash first
        try:
            ssh_run(ssh_target, app_path, f"git stash && git checkout {deploy_branch}")
            ok("(stashed local changes)")
        except RuntimeError as e:
            fail(str(e))
            sys.exit(1)

    # --- Step 3: Pull ---
    current_step += 1
    step(current_step, total_steps, f"Pulling latest {deploy_branch}")
    try:
        ssh_run(ssh_target, app_path, f"git pull origin {deploy_branch}")
        ok()
    except RuntimeError as e:
        fail(str(e))
        sys.exit(1)

    # --- Step 4: Clear caches ---
    current_step += 1
    step(current_step, total_steps, "Clearing caches")
    try:
        ssh_run(
            ssh_target, app_path,
            "php artisan config:clear && php artisan cache:clear && php artisan route:clear && php artisan view:clear"
        )
        ok()
    except RuntimeError as e:
        fail(str(e))
        sys.exit(1)

    # --- Step 5: Migrations ---
    if do_migrate:
        current_step += 1
        step(current_step, total_steps, "Running migrations")
        try:
            output = ssh_run(ssh_target, app_path, "php artisan migrate --force")
            detail = "nothing to migrate" if "Nothing to migrate" in output else "applied"
            ok(detail)
        except RuntimeError as e:
            fail(str(e))
            sys.exit(1)

    # --- Step 6: Composer install ---
    if do_composer:
        current_step += 1
        step(current_step, total_steps, "Installing composer dependencies")
        try:
            ssh_run(ssh_target, app_path, "composer install --no-interaction", timeout=600)
            ok()
        except RuntimeError as e:
            fail(str(e))
            sys.exit(1)

    # --- Step 7: NPM build ---
    if do_npm:
        current_step += 1
        step(current_step, total_steps, "Installing npm dependencies + building")
        try:
            ssh_run(ssh_target, app_path, "npm install && npm run build", timeout=600)
            ok()
        except RuntimeError as e:
            fail(str(e))
            sys.exit(1)

    # --- Final: Verify ---
    current_step += 1
    step(current_step, total_steps, "Verifying deployment")
    try:
        deployed_branch = ssh_run(ssh_target, app_path, "git branch --show-current")
        deployed_commit = ssh_run(ssh_target, app_path, "git log --oneline -1")
        commit_hash = deployed_commit.split()[0] if deployed_commit else ""

        # For merged PRs, verify the merge commit is in history
        if state == "MERGED" and merge_oid:
            try:
                ssh_run(ssh_target, app_path, f"git log --oneline | head -20 | grep {merge_oid[:7]}")
                ok(f"merge commit {merge_oid[:7]} found")
            except RuntimeError:
                ok(f"(merge commit not in recent 20 — may be older)")
        else:
            ok()

        print()
        print(f"+ Deployment successful")
        print(f"  Branch: {deployed_branch}")
        print(f"  Commit: {deployed_commit}")
        if state == "MERGED" and merge_oid:
            print(f"  PR merge commit: {merge_oid[:10]}")

    except RuntimeError as e:
        fail(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
