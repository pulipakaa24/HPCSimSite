#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path when running this file directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn


if __name__ == "__main__":
    uvicorn.run("hpcsim.api:app", host="0.0.0.0", port=8000, reload=False)
