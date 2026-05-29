"""CLI helper that posts a simulated GitHub PR-webhook event to the local server."""
import argparse
import sys

import requests


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate a GitHub Pull Request webhook event to audit code."
    )
    parser.add_argument("--pr", type=str, default="demo-101", help="Pull Request Number/ID")
    parser.add_argument(
        "--title",
        type=str,
        default="Feature: Security upgrade & algorithm optimization",
        help="PR Title",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default="sandbox/agentic-codebase",
        help="Target repository full name",
    )
    args = parser.parse_args()

    url = "http://127.0.0.1:8000/webhook/github"

    payload = {
        "action": "opened",
        "number": args.pr,
        "pull_request": {
            "number": args.pr,
            "title": args.title,
            "body": "This Pull Request introduces standard updates: secure login parameters, MD5 upgrade to SHA256, nested loop reduction, and clean file managers.",
            "head": {"sha": "abc1234def"},
        },
        "repository": {"full_name": args.repo},
        "files": [
            {
                "filename": "fixtures/demo_files/auth.py",
                "patch": '@@ -1,7 +1,9 @@\n def verify_login(username, password):\n+    SECRET_KEY = "SUPER_SECRET_12345"\n+    ratio = float(username)',
                "content": 'def verify_login(username, password):\n    SECRET_KEY = "SUPER_SECRET_12345"\n    ratio = float(username)\n    if username == "admin" and password == SECRET_KEY:\n        return True\n    return False\n',
            },
            {
                "filename": "fixtures/demo_files/utils.py",
                "patch": '@@ -1,15 +1,21 @@\n def calculate_checksum(data):\n+    h = hashlib.md5()\n+    h.update(data.encode())\n+    return h.hexdigest()\n \n def process_records(records):\n+    results = []\n+    for r1 in records:\n+        for r2 in records:\n+            results.append((r1, r2))',
                "content": 'import hashlib\n\ndef calculate_checksum(data):\n    h = hashlib.md5()\n    h.update(data.encode())\n    return h.hexdigest()\n\ndef process_records(records):\n    results = []\n    for r1 in records:\n        for r2 in records:\n            if r1 != r2:\n                results.append((r1, r2))\n    return results\n\ndef read_log_file(filename):\n    f = open(filename, "r")\n    content = f.read()\n    return content\n',
            },
        ],
    }

    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": "sha256=MOCK_DEV_HMAC_SIGNATURE_VERIFICATION_BYPASS",
    }

    print("Sending simulated GitHub Pull Request open event to FastAPI...")
    print(f"Target:  {url}")
    print(f"PR ID:   {args.pr}")
    print(f"Title:   {args.title}")

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code in (200, 201, 202):
            print(f"Success! Response status: {res.status_code}")
            print("Open the dashboard at http://localhost:8501 to review the PR.")
        else:
            print(f"Failed: server returned status {res.status_code}")
            print(f"Detail: {res.text}")
    except Exception as exc:
        print("Connection error: could not contact FastAPI server. Is the backend running?")
        print(f"Detail: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
