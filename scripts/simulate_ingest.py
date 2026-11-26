#!/usr/bin/env python3
"""Script to simulate posting fixture batches to the ingest API.

Usage:
    python scripts/simulate_ingest.py --base-url http://localhost:8000 --token ocl_... --fixture fixtures/ingest_batches.json
"""

import argparse
import json
import sys
from pathlib import Path
import urllib.request
import urllib.error


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate posting fixture batches to OpenClaw Ingest API")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of backend server")
    parser.add_argument("--token", required=True, help="Workstation Bearer token (ocl_...)")
    parser.add_argument(
        "--fixture",
        default="fixtures/ingest_batches.json",
        help="Path to JSON fixture file containing batch or list of batches",
    )
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    if not fixture_path.is_file():
        print(f"Error: Fixture file not found: {fixture_path}", file=sys.stderr)
        sys.exit(1)

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    batches = data if isinstance(data, list) else [data]
    endpoint = f"{args.base_url.rstrip('/')}/v1/ingest"

    print(f"Sending {len(batches)} batch(es) to {endpoint}...")

    for i, batch in enumerate(batches, start=1):
        batch_id = batch.get("batch_id", f"unknown-{i}")
        body_bytes = json.dumps(batch).encode("utf-8")

        req = urllib.request.Request(
            endpoint,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {args.token}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                status = resp.status
                print(
                    f"[{i}/{len(batches)}] Batch '{batch_id}': HTTP {status} - "
                    f"accepted={resp_data.get('accepted')}, "
                    f"rejected={len(resp_data.get('rejected', []))}, "
                    f"duplicate={resp_data.get('duplicate')}"
                )
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f"[{i}/{len(batches)}] Batch '{batch_id}': Failed HTTP {e.code} - {err_body}", file=sys.stderr)
        except urllib.error.URLError as e:
            print(f"[{i}/{len(batches)}] Batch '{batch_id}': Connection error: {e.reason}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
