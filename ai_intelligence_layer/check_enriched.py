#!/usr/bin/env python3
"""
Simple check script to fetch enriched telemetry from the enrichment service
and print a compact preview. Uses only the Python standard library so it
runs without extra dependencies.

Usage:
  python3 check_enriched.py          # fetch default 10 records
  python3 check_enriched.py 5        # fetch 5 records
"""
import sys
import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 else 10
URL = f"http://localhost:8000/enriched?limit={LIMIT}"

def main():
    req = Request(URL, headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            print(f"Fetched {len(data)} records from enrichment service at {URL}")
            if len(data) == 0:
                print("No records returned.")
                return
            # Print preview of first record
            print("--- First record preview ---")
            print(json.dumps(data[0], indent=2)[:2000])
            print("--- End preview ---")
    except HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        sys.exit(2)
    except URLError as e:
        print(f"URL Error: {e.reason}")
        sys.exit(3)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(4)

if __name__ == '__main__':
    main()
