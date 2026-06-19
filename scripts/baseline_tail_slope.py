#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"
SUBMISSION_DIR = ROOT / "submissions"
REPORT_DIR = ROOT / "reports"
SUBMISSION_PATH = SUBMISSION_DIR / "baseline_tail_slope_submission.csv"
REPORT_PATH = REPORT_DIR / "baseline_report.md"


def parse_submission_ids(sample: pd.DataFrame) -> pd.DataFrame:
    parsed = sample.copy()
    parts = parsed["id"].str.rsplit("_", n=1, expand=True)
    parsed["well"] = parts[0]
    parsed["row"] = parts[1].astype(int)
    return parsed


def tail_slope_prediction(df: pd.DataFrame, rows: np.ndarray, tail_window: int) -> np.ndarray:
    observed = df["TVT_input"].notna().to_numpy()
    if observed.sum() < 2:
        return np.full(len(rows), float(df["TVT_input"].dropna().median()))

    md_obs = df.loc[observed, "MD"].to_numpy(dtype=float)
    tvt_obs = df.loc[observed, "TVT_input"].to_numpy(dtype=float)
    md_pred = df.loc[rows, "MD"].to_numpy(dtype=float)

    k = min(tail_window, len(md_obs))
    slopes = np.diff(tvt_obs[-k:]) / np.diff(md_obs[-k:])
    slopes = slopes[np.isfinite(slopes)]
    slope = float(np.median(slopes)) if len(slopes) else 1.0

    preds = np.interp(md_pred, md_obs, tvt_obs)
    right = md_pred > md_obs[-1]
    if right.any():
        preds[right] = tvt_obs[-1] + slope * (md_pred[right] - md_obs[-1])

    left = md_pred < md_obs[0]
    if left.any():
        first_k = min(tail_window, len(md_obs))
        left_slopes = np.diff(tvt_obs[:first_k]) / np.diff(md_obs[:first_k])
        left_slopes = left_slopes[np.isfinite(left_slopes)]
        left_slope = float(np.median(left_slopes)) if len(left_slopes) else slope
        preds[left] = tvt_obs[0] + left_slope * (md_pred[left] - md_obs[0])

    return preds


def main() -> int:
    SUBMISSION_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)

    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    parsed = parse_submission_ids(sample)

    out = sample.copy()
    diagnostics = []
    local_truth = []
    local_pred = []

    for well, part in parsed.groupby("well", sort=True):
        test_path = DATA_DIR / "test" / f"{well}__horizontal_well.csv"
        test = pd.read_csv(test_path)
        rows = part["row"].to_numpy()
        preds = tail_slope_prediction(test, rows, tail_window=200)
        out.loc[part.index, "tvt"] = preds

        known = int(test["TVT_input"].notna().sum())
        diagnostics.append(
            {
                "well": well,
                "rows": len(test),
                "known_tvt_input": known,
                "predicted_rows": len(part),
                "pred_min": float(np.min(preds)),
                "pred_max": float(np.max(preds)),
            }
        )

        train_path = DATA_DIR / "train" / f"{well}__horizontal_well.csv"
        if train_path.exists():
            truth = pd.read_csv(train_path).loc[rows, "TVT"].to_numpy(dtype=float)
            local_truth.extend(truth.tolist())
            local_pred.extend(preds.tolist())

    out.to_csv(SUBMISSION_PATH, index=False)

    lines = [
        "# Baseline Report",
        "",
        "## Method",
        "",
        "This baseline fills the missing evaluation interval per well by extrapolating `TVT_input` from the latest observed segment. It uses the median `dTVT/dMD` slope over the last 200 observed points, then writes predictions in Kaggle submission format.",
        "",
        "## Output",
        "",
        f"- Submission: `{SUBMISSION_PATH.relative_to(ROOT)}`",
        f"- Rows: {len(out):,}",
        "",
        "## Per-Well Diagnostics",
        "",
        pd.DataFrame(diagnostics).round(4).to_markdown(index=False),
        "",
    ]

    if local_truth:
        rmse = mean_squared_error(local_truth, local_pred) ** 0.5
        lines.extend(
            [
                "## Local Visible-Test Check",
                "",
                f"- RMSE against matching train truth for the three visible example wells: {rmse:.4f}",
                "",
                "This check is only a sanity test. It is not a reliable public leaderboard estimate because Kaggle replaces the visible test examples with hidden wells during submission reruns.",
                "",
            ]
        )

    REPORT_PATH.write_text("\n".join(lines))
    print(f"Wrote {SUBMISSION_PATH}")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
