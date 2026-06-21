#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

from data_paths import resolve_train_dir


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
OUTPUT_DIR = ROOT / "outputs"
DETAIL_PATH = OUTPUT_DIR / "baseline_cv_by_well.csv"
REPORT_PATH = REPORT_DIR / "baseline_cv_report.md"


def tail_slope_prediction(df: pd.DataFrame, target_rows: np.ndarray, tail_window: int = 200) -> np.ndarray:
    observed = df["TVT_input"].notna().to_numpy()
    if observed.sum() < 2:
        known = df.loc[observed, "TVT_input"].to_numpy(dtype=float)
        fill = float(np.nanmedian(known)) if len(known) else float(df["TVT"].median())
        return np.full(len(target_rows), fill)

    md_obs = df.loc[observed, "MD"].to_numpy(dtype=float)
    tvt_obs = df.loc[observed, "TVT_input"].to_numpy(dtype=float)
    md_pred = df.loc[target_rows, "MD"].to_numpy(dtype=float)

    k = min(tail_window, len(md_obs))
    slopes = np.diff(tvt_obs[-k:]) / np.diff(md_obs[-k:])
    slopes = slopes[np.isfinite(slopes)]
    right_slope = float(np.median(slopes)) if len(slopes) else 1.0

    preds = np.interp(md_pred, md_obs, tvt_obs)

    right = md_pred > md_obs[-1]
    if right.any():
        preds[right] = tvt_obs[-1] + right_slope * (md_pred[right] - md_obs[-1])

    left = md_pred < md_obs[0]
    if left.any():
        first_k = min(tail_window, len(md_obs))
        left_slopes = np.diff(tvt_obs[:first_k]) / np.diff(md_obs[:first_k])
        left_slopes = left_slopes[np.isfinite(left_slopes)]
        left_slope = float(np.median(left_slopes)) if len(left_slopes) else right_slope
        preds[left] = tvt_obs[0] + left_slope * (md_pred[left] - md_obs[0])

    return preds


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    train_dir = resolve_train_dir()
    records = []
    all_true = []
    all_pred = []

    for path in sorted(train_dir.glob("*__horizontal_well.csv")):
        well = path.name.split("__")[0]
        df = pd.read_csv(path)
        target_rows = np.flatnonzero(df["TVT_input"].isna().to_numpy())
        if len(target_rows) == 0:
            continue

        preds = tail_slope_prediction(df, target_rows)
        truth = df.loc[target_rows, "TVT"].to_numpy(dtype=float)
        errors = preds - truth
        rmse = mean_squared_error(truth, preds) ** 0.5

        known_rows = int(df["TVT_input"].notna().sum())
        gr_missing_rate = float(df.loc[target_rows, "GR"].isna().mean())
        md_span = float(df.loc[target_rows, "MD"].max() - df.loc[target_rows, "MD"].min())
        tvt_span = float(truth.max() - truth.min())

        records.append(
            {
                "well": well,
                "rows": len(df),
                "known_rows": known_rows,
                "target_rows": len(target_rows),
                "target_md_span": md_span,
                "target_tvt_span": tvt_span,
                "target_gr_missing_rate": gr_missing_rate,
                "rmse": rmse,
                "mae": float(np.mean(np.abs(errors))),
                "bias": float(np.mean(errors)),
                "p95_abs_error": float(np.quantile(np.abs(errors), 0.95)),
                "max_abs_error": float(np.max(np.abs(errors))),
            }
        )
        all_true.extend(truth.tolist())
        all_pred.extend(preds.tolist())

    detail = pd.DataFrame(records).sort_values("rmse", ascending=False)
    detail.to_csv(DETAIL_PATH, index=False)

    overall_rmse = mean_squared_error(all_true, all_pred) ** 0.5
    abs_err = np.abs(np.asarray(all_pred) - np.asarray(all_true))

    bucketed = detail.assign(
        target_rows_bucket=pd.cut(
            detail["target_rows"],
            bins=[0, 2000, 4000, 6000, 8000, 12000],
            labels=["0-2k", "2k-4k", "4k-6k", "6k-8k", "8k-12k"],
            include_lowest=True,
        )
    )
    bucket_summary = (
        bucketed.groupby("target_rows_bucket", observed=True)
        .agg(wells=("well", "count"), mean_rmse=("rmse", "mean"), median_rmse=("rmse", "median"), max_rmse=("rmse", "max"))
        .reset_index()
    )

    lines = [
        "# Baseline Cross-Validation Report",
        "",
        "## Evaluation Design",
        "",
        "Each training well already contains a `TVT_input` hidden interval and a complete `TVT` truth column. This report treats the `TVT_input` NaN rows as the validation target, predicts them with the tail-slope baseline, and scores against `TVT`.",
        "",
        "## Overall Metrics",
        "",
        f"- Wells evaluated: {len(detail):,}",
        f"- Target rows evaluated: {len(all_true):,}",
        f"- Overall RMSE: {overall_rmse:.4f}",
        f"- Median absolute error: {np.median(abs_err):.4f}",
        f"- P95 absolute error: {np.quantile(abs_err, 0.95):.4f}",
        f"- Max absolute error: {np.max(abs_err):.4f}",
        "",
        "## RMSE by Hidden-Interval Length",
        "",
        bucket_summary.round(4).to_markdown(index=False),
        "",
        "## Worst 20 Wells",
        "",
        detail.head(20).round(4).to_markdown(index=False),
        "",
        "## Best 20 Wells",
        "",
        detail.tail(20).sort_values("rmse").round(4).to_markdown(index=False),
        "",
        "## Engineering Takeaways",
        "",
        "- The tail-slope baseline is now measured across all training wells, so it is a real control target for leaderboard models.",
        "- Any residual model must beat this report overall and reduce the worst-well tail, not merely improve easy wells.",
        "- The worst-well table is the first failure-analysis queue for GR/typewell and structural-discontinuity features.",
        "",
        f"Detailed per-well metrics: `{DETAIL_PATH.relative_to(ROOT)}`",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))
    print(f"Wrote {DETAIL_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"overall_rmse={overall_rmse:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
