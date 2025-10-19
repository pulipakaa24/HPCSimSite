#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Iterable, Dict, Any

from hpcsim.enrichment import Enricher


def iter_json_lines(stream) -> Iterable[Dict[str, Any]]:
    for line in stream:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            print(f"Skipping invalid JSON line: {line}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Enrich telemetry JSON lines with HPC-style metrics")
    parser.add_argument("--input", "-i", help="Input file path (JSON lines). Reads stdin if omitted.")
    parser.add_argument("--output", "-o", help="Output file path (JSON lines). Writes stdout if omitted.")
    args = parser.parse_args()

    enricher = Enricher()

    fin = open(args.input, "r") if args.input else sys.stdin
    fout = open(args.output, "w") if args.output else sys.stdout

    try:
        for rec in iter_json_lines(fin):
            enriched = enricher.enrich(rec)
            print(json.dumps(enriched), file=fout)
            fout.flush()
    finally:
        if fin is not sys.stdin:
            fin.close()
        if fout is not sys.stdout:
            fout.close()


if __name__ == "__main__":
    main()
