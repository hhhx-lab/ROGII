#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from data_paths import load_sample_submission


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate final ROGII submission format.")
    parser.add_argument("--submission", type=Path, default=ROOT / "submission.csv")
    args = parser.parse_args()

    if not args.submission.exists():
        raise FileNotFoundError(args.submission)

    sample = load_sample_submission()[["id"]].copy()
    submission = pd.read_csv(args.submission, dtype={"id": "string"})

    if list(submission.columns) != ["id", "tvt"]:
        raise ValueError("submission must have exactly columns: id,tvt")
    if len(submission) != len(sample):
        raise ValueError(f"row count mismatch: submission={len(submission)} sample={len(sample)}")
    if not submission["id"].astype("string").equals(sample["id"].astype("string")):
        raise ValueError("submission ids are not in the same order as sample_submission.csv")
    if submission["id"].duplicated().any():
        raise ValueError("submission contains duplicated ids")
    if not np.isfinite(submission["tvt"].to_numpy(dtype=float)).all():
        raise ValueError("submission contains NaN or inf in tvt")

    print(f"Validated {args.submission}: rows={len(submission)}, columns=id,tvt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
