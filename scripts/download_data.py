#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path
from shutil import which


COMPETITION = "rogii-wellbore-geology-prediction"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def resolve_kaggle_cli() -> str | None:
    candidates = [
        ROOT / ".venv" / "Scripts" / "kaggle.exe",
        ROOT / ".venv" / "Scripts" / "kaggle",
        ROOT / ".venv" / "bin" / "kaggle",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return which("kaggle")


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)

    kaggle = resolve_kaggle_cli()
    if kaggle is None:
        print("Missing Kaggle CLI. Run: python -m venv .venv && python -m pip install kaggle", file=sys.stderr)
        return 1

    run([kaggle, "competitions", "download", "-c", COMPETITION, "-p", str(DATA_DIR)])
    print(f"Downloaded competition bundle into: {DATA_DIR}")
    zip_path = DATA_DIR / f"{COMPETITION}.zip"
    if zip_path.exists():
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(DATA_DIR)
        print(f"Extracted: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
