#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data_paths import load_sample_submission
from postprocess_predictions import run_postprocess


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"
SUBMISSION_DIR = ROOT / "submissions"


def load_submission(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string"})
    if list(frame.columns) != ["id", "tvt"]:
        raise ValueError(f"{path} must have exactly id,tvt columns")
    return frame


def validate_submission(submission: pd.DataFrame, sample: pd.DataFrame) -> None:
    if len(submission) != len(sample):
        raise ValueError("submission row count mismatch")
    if not submission["id"].astype("string").equals(sample["id"].astype("string")):
        raise ValueError("submission ids are not in sample order")
    if submission["id"].duplicated().any():
        raise ValueError("submission contains duplicated ids")
    if not np.isfinite(submission["tvt"].to_numpy(dtype=float)).all():
        raise ValueError("submission contains NaN or inf")


def write_log(log_path: Path, record: dict[str, object]) -> None:
    log_path.parent.mkdir(exist_ok=True)
    if log_path.exists():
        try:
            history = json.loads(log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    else:
        history = []
    if not isinstance(history, list):
        history = [history]
    history.append(record)
    log_path.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the final submission.csv.")
    parser.add_argument("--variant", default="balanced", choices=["conservative", "balanced", "aggressive"])
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "submission.csv")
    parser.add_argument("--log", type=Path, default=REPORT_DIR / "submission_log.md")
    parser.add_argument("--clip-lower", type=float, default=9000.0)
    parser.add_argument("--clip-upper", type=float, default=13000.0)
    args = parser.parse_args()

    sample = load_sample_submission()[["id"]].copy()
    input_path = args.input or (SUBMISSION_DIR / f"{args.variant}_submission.csv")
    postprocessed_path = SUBMISSION_DIR / f"{args.variant}_postprocessed_submission.csv"
    diagnostics_path = OUTPUT_DIR / "postprocess_diagnostics.csv"
    report_path = REPORT_DIR / "postprocess_report.md"

    if not postprocessed_path.exists():
        run_postprocess(
            variant=args.variant,
            input_path=input_path,
            output_path=postprocessed_path,
            diagnostics_path=diagnostics_path,
            report_path=report_path,
            oof_path=OUTPUT_DIR / "blend_oof.csv",
            clip_lower=args.clip_lower,
            clip_upper=args.clip_upper,
        )

    submission = load_submission(postprocessed_path)
    submission = sample.merge(submission, on="id", how="left", validate="one_to_one")
    if submission["tvt"].isna().any():
        raise ValueError("submission contains missing predictions after alignment")
    submission = submission[["id", "tvt"]]
    validate_submission(submission, sample)
    submission.to_csv(args.output, index=False)

    write_log(
        args.log,
        {
            "variant": args.variant,
            "input": str(input_path),
            "output": str(args.output),
            "postprocessed": str(postprocessed_path),
            "rows": len(submission),
        },
    )
    print(f"Wrote final submission to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
