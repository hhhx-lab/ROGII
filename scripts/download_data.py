#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


COMPETITION = "rogii-wellbore-geology-prediction"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)

    kaggle = ROOT / ".venv" / "bin" / "kaggle"
    if not kaggle.exists():
        print("Missing Kaggle CLI in .venv. Run: python -m venv .venv && .venv/bin/pip install kaggle", file=sys.stderr)
        return 1

    run([str(kaggle), "competitions", "download", "-c", COMPETITION, "-p", str(DATA_DIR)])
    print(f"Downloaded competition bundle into: {DATA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
