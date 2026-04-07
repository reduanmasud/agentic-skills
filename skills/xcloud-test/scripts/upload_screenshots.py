#!/usr/bin/env python3
"""
Batch upload QA screenshots to Cloudinary with resume support.

Usage:
    python3 upload_screenshots.py --dir qa-screenshots --pr 4334
    python3 upload_screenshots.py --dir qa-screenshots --pr 4334 --json
    python3 upload_screenshots.py --dir qa-screenshots --pr 4334 --batch-size 3
    python3 upload_screenshots.py --dir qa-screenshots --pr 4334 --reset

Features:
    - Batched uploads (default 5/batch) with a pause between batches to avoid rate limits
    - Auto-resume: saves state after every upload — re-run to continue from where it stopped
    - Retries each file up to 3 times with increasing delays before marking as failed
    - --reset flag to ignore saved state and re-upload everything

Requires env vars: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]   # seconds between retry attempts
BATCH_PAUSE = 2.0            # seconds to wait between batches
DEFAULT_BATCH_SIZE = 5
STATE_FILENAME = ".upload-state.json"


# ---------------------------------------------------------------------------
# Config & discovery
# ---------------------------------------------------------------------------

def get_cloudinary_config():
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key    = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")
    missing = [k for k, v in {
        "CLOUDINARY_CLOUD_NAME": cloud_name,
        "CLOUDINARY_API_KEY":    api_key,
        "CLOUDINARY_API_SECRET": api_secret,
    }.items() if not v]
    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return cloud_name, api_key, api_secret


def find_screenshots(directory):
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"ERROR: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)
    return sorted(
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )


# ---------------------------------------------------------------------------
# State (resume) management
# ---------------------------------------------------------------------------

def _state_path(directory):
    return Path(directory) / STATE_FILENAME


def load_state(directory):
    """Return dict of {filename -> cloudinary_url} from a previous run."""
    p = _state_path(directory)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(directory, state):
    """Persist state after every successful upload so a restart can resume."""
    _state_path(directory).write_text(json.dumps(state, indent=2))


def clear_state(directory):
    p = _state_path(directory)
    if p.exists():
        p.unlink()


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def _build_multipart_body(filepath, public_id, boundary):
    body = bytearray()

    def field(name, value):
        nonlocal body
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += f"{value}\r\n".encode()

    field("public_id", public_id)

    mime = filepath.suffix.lstrip(".").replace("jpg", "jpeg")
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{filepath.name}"\r\n'.encode()
    body += f"Content-Type: image/{mime}\r\n\r\n".encode()
    body += filepath.read_bytes()
    body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return bytes(body)


def upload_file(filepath, cloud_name, api_key, api_secret, public_id):
    """Upload one file. Returns secure_url string. Raises on failure."""
    boundary = "----CloudinaryBoundary7654321"
    body     = _build_multipart_body(filepath, public_id, boundary)
    creds    = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()

    req = urllib.request.Request(
        f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload",
        data=body,
        headers={
            "Content-Type":  f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Basic {creds}",
        },
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=60)
    data = json.loads(resp.read().decode())
    return data["secure_url"]


def upload_with_retry(filepath, cloud_name, api_key, api_secret, public_id, quiet):
    """Upload with exponential-backoff retries. Returns (url, error_str)."""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            url = upload_file(filepath, cloud_name, api_key, api_secret, public_id)
            return url, None
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                delay = RETRY_DELAYS[min(attempt, len(RETRY_DELAYS) - 1)]
                if not quiet:
                    print(f"      retry {attempt + 1}/{MAX_RETRIES} in {delay}s ({e})")
                time.sleep(delay)
    return None, str(last_error)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def chunked(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def main():
    parser = argparse.ArgumentParser(description="Upload QA screenshots to Cloudinary")
    parser.add_argument("--dir",        default="qa-screenshots",
                        help="Screenshot directory (default: qa-screenshots)")
    parser.add_argument("--pr",         required=True,
                        help="PR number — used for Cloudinary folder naming")
    parser.add_argument("--json",       action="store_true", dest="json_output",
                        help="Output URL map as JSON only (machine-readable)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Files per batch (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--reset",      action="store_true",
                        help="Ignore saved state and re-upload everything")
    args = parser.parse_args()

    cloud_name, api_key, api_secret = get_cloudinary_config()
    all_files = find_screenshots(args.dir)

    if not all_files:
        print(f"No screenshots found in {args.dir}")
        sys.exit(0)

    # Resume: load state from previous run
    if args.reset:
        clear_state(args.dir)
        state = {}
    else:
        state = load_state(args.dir)

    already_uploaded = set(state.keys())
    pending  = [f for f in all_files if f.name not in already_uploaded]
    total    = len(all_files)
    done     = len(already_uploaded)

    if not args.json_output:
        if done > 0 and pending:
            print(f"Resuming — {done}/{total} already done, {len(pending)} remaining")
        elif done == total:
            print(f"All {total} files already uploaded. Use --reset to re-upload.")
            # Still print the report
        else:
            print(f"Uploading {total} screenshot(s) to Cloudinary (PR #{args.pr})  "
                  f"[batch size: {args.batch_size}]")

    failures = []
    batches  = list(chunked(pending, args.batch_size))

    for batch_idx, batch in enumerate(batches):
        if not args.json_output and len(batches) > 1:
            start_num = done + batch_idx * args.batch_size + 1
            end_num   = min(start_num + len(batch) - 1, total)
            print(f"\nBatch {batch_idx + 1}/{len(batches)}  ({start_num}–{end_num} of {total})")

        for filepath in batch:
            done += 1
            public_id = f"qa-pr{args.pr}/{filepath.stem}"

            url, error = upload_with_retry(
                filepath, cloud_name, api_key, api_secret, public_id,
                quiet=args.json_output,
            )

            if url:
                state[filepath.name] = url
                save_state(args.dir, state)          # persist — safe to interrupt now
                if not args.json_output:
                    print(f"  [{done}/{total}] {filepath.name}")
                    print(f"           -> {url}")
            else:
                failures.append((filepath.name, error))
                if not args.json_output:
                    print(f"  [{done}/{total}] FAILED: {filepath.name} — {error}")

        # Pause between batches (skip after last batch)
        if batch_idx < len(batches) - 1:
            if not args.json_output:
                print(f"  (pause {BATCH_PAUSE}s before next batch...)")
            time.sleep(BATCH_PAUSE)

    # Output
    if args.json_output:
        json.dump(state, sys.stdout, indent=2)
        print()
    else:
        succeeded = len(state)
        print()
        if failures:
            print(f"! {succeeded}/{total} uploaded  |  {len(failures)} failed")
            for name, err in failures:
                print(f"  FAILED: {name} — {err}")
            print(f"\nTip: re-run the same command to resume — "
                  f"already-uploaded files are skipped automatically.")
        else:
            print(f"+ {succeeded}/{total} uploaded successfully")
            clear_state(args.dir)   # clean up state file on full success

        # Markdown table for the report
        print("\n--- Paste into QA report ---")
        print("| # | Screenshot | URL |")
        print("|---|-----------|-----|")
        for idx, (name, url) in enumerate(state.items(), 1):
            desc = Path(name).stem
            print(f"| {idx} | {desc} | [View]({url}) |")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
