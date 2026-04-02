#!/usr/bin/env python3
"""
Batch upload QA screenshots to Cloudinary.

Usage:
    python3 upload_screenshots.py --dir qa-screenshots --pr 4334
    python3 upload_screenshots.py --dir qa-screenshots --pr 4334 --json

Requires env vars: CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_RETRIES = 1


def get_cloudinary_config():
    """Read and validate Cloudinary env vars."""
    cloud_name = os.environ.get("CLOUDINARY_CLOUD_NAME")
    api_key = os.environ.get("CLOUDINARY_API_KEY")
    api_secret = os.environ.get("CLOUDINARY_API_SECRET")

    missing = []
    if not cloud_name:
        missing.append("CLOUDINARY_CLOUD_NAME")
    if not api_key:
        missing.append("CLOUDINARY_API_KEY")
    if not api_secret:
        missing.append("CLOUDINARY_API_SECRET")

    if missing:
        print(f"ERROR: Missing env vars: {', '.join(missing)}", file=sys.stderr)
        print("Set them before running this script.", file=sys.stderr)
        sys.exit(1)

    return cloud_name, api_key, api_secret


def find_screenshots(directory):
    """Find all image files in the directory, sorted by name."""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"ERROR: Directory not found: {directory}", file=sys.stderr)
        sys.exit(1)

    files = sorted(
        f for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return files


def upload_file(filepath, cloud_name, api_key, api_secret, public_id):
    """Upload a single file to Cloudinary using HTTP Basic Auth. Returns the secure URL."""
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"

    # Build multipart form data manually (no requests library)
    boundary = "----CloudinaryUploadBoundary9876543210"
    body = bytearray()

    # Add public_id field
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="public_id"\r\n\r\n'.encode()
    body += f"{public_id}\r\n".encode()

    # Add file field
    filename = filepath.name
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    body += f"Content-Type: image/{filepath.suffix.lstrip('.').replace('jpg', 'jpeg')}\r\n\r\n".encode()
    body += filepath.read_bytes()
    body += b"\r\n"

    # Close boundary
    body += f"--{boundary}--\r\n".encode()

    # Build request with Basic Auth
    credentials = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Authorization": f"Basic {credentials}",
        },
        method="POST",
    )

    response = urllib.request.urlopen(req, timeout=30)
    data = json.loads(response.read().decode())
    return data.get("secure_url")


def main():
    parser = argparse.ArgumentParser(description="Upload QA screenshots to Cloudinary")
    parser.add_argument("--dir", default="qa-screenshots", help="Directory containing screenshots (default: qa-screenshots)")
    parser.add_argument("--pr", required=True, help="PR number (used for Cloudinary folder naming)")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output results as JSON only")
    args = parser.parse_args()

    cloud_name, api_key, api_secret = get_cloudinary_config()
    files = find_screenshots(args.dir)

    if not files:
        print(f"No screenshots found in {args.dir}")
        sys.exit(0)

    if not args.json_output:
        print(f"Uploading {len(files)} screenshots to Cloudinary (PR #{args.pr})...")

    results = {}
    failures = []
    for i, filepath in enumerate(files, 1):
        stem = filepath.stem
        public_id = f"qa-pr{args.pr}/{stem}"

        for attempt in range(MAX_RETRIES + 1):
            try:
                secure_url = upload_file(filepath, cloud_name, api_key, api_secret, public_id)
                results[filepath.name] = secure_url
                if not args.json_output:
                    print(f"[{i}/{len(files)}] {filepath.name} -> {secure_url}")
                break
            except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError) as e:
                if attempt < MAX_RETRIES:
                    if not args.json_output:
                        print(f"[{i}/{len(files)}] {filepath.name} — retry ({e})")
                else:
                    failures.append((filepath.name, str(e)))
                    if not args.json_output:
                        print(f"[{i}/{len(files)}] {filepath.name} — FAILED: {e}")

    if args.json_output:
        json.dump(results, sys.stdout, indent=2)
        print()
    else:
        succeeded = len(results)
        total = len(files)
        if failures:
            print(f"\n! {succeeded}/{total} uploaded, {len(failures)} failed")
            for name, err in failures:
                print(f"  FAILED: {name} — {err}")
        else:
            print(f"\n+ {succeeded}/{total} uploaded successfully")

        # Print markdown table
        print("\n--- Markdown snippet (copy to report) ---")
        print("| # | Description | URL |")
        print("|---|-------------|-----|")
        for j, (name, url) in enumerate(results.items(), 1):
            desc = Path(name).stem
            print(f"| {j} | {desc} | [View]({url}) |")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
