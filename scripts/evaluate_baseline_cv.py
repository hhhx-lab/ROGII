#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from rogii_utils import (
    BASELINE_CONFIGS,
    OUTPUT_DIR,
    REPORT_DIR,
    ROOT,
    TRAIN_DIR,
    assert_data_contract_ready,
    contiguous_true_bounds,
    data_hash_short,
    ensure_project_dirs,
    max_step_jump,
    regression_metrics,
    run_baseline,
    train_wells,
)


DETAIL_PATH = OUTPUT_DIR / "baseline_cv_by_well.csv"
PREDICTION_PATH = OUTPUT_DIR / "baseline_predictions_train_hidden.csv"
OVERALL_PATH = OUTPUT_DIR / "baseline_overall_metrics.csv"
REPORT_PATH = REPORT_DIR / "baseline_cv_report.md"


def target_rows_from_original_hidden(df: pd.DataFrame) -> np.ndarray:
    target_mask = df["TVT_input"].isna().to_numpy()
    start, end = contiguous_true_bounds(target_mask)
    return np.arange(start, end + 1, dtype=int)


def bucket_summary(detail: pd.DataFrame, best_baseline: str) -> pd.DataFrame:
    selected = detail[detail["baseline"].eq(best_baseline)].copy()
    selected["target_rows_bucket"] = pd.cut(
        selected["target_rows"],
        bins=[0, 2000, 4000, 6000, 8000, 12000],
        labels=["0-2k", "2k-4k", "4k-6k", "6k-8k", "8k-12k"],
        include_lowest=True,
    )
    return (
        selected.groupby("target_rows_bucket", observed=True)
        .agg(wells=("well", "count"), mean_rmse=("rmse", "mean"), median_rmse=("rmse", "median"), max_rmse=("rmse", "max"))
        .reset_index()
    )


def subset_summary(detail: pd.DataFrame, best_baseline: str) -> pd.DataFrame:
    selected = detail[detail["baseline"].eq(best_baseline)].copy()
    rows = []
    subsets = {
        "all_wells": selected,
        "long_hidden_top25pct": selected[selected["target_rows"] >= selected["target_rows"].quantile(0.75)],
        "high_gr_missing_top25pct": selected[
            selected["target_gr_missing_rate"] >= selected["target_gr_missing_rate"].quantile(0.75)
        ],
        "high_tvt_span_top25pct": selected[selected["target_tvt_span"] >= selected["target_tvt_span"].quantile(0.75)],
    }
    for name, frame in subsets.items():
        if len(frame) == 0:
            continue
        rows.append(
            {
                "subset": name,
                "wells": len(frame),
                "mean_well_rmse": frame["rmse"].mean(),
                "median_well_rmse": frame["rmse"].median(),
                "max_well_rmse": frame["rmse"].max(),
                "mean_bias": frame["bias"].mean(),
            }
        )
    return pd.DataFrame(rows)


def main() -> int:
    ensure_project_dirs()
    data_version = assert_data_contract_ready()
    data_hash = data_hash_short(data_version)

    records: list[dict[str, object]] = []
    errors_by_baseline: dict[str, list[np.ndarray]] = defaultdict(list)
    truth_by_baseline: dict[str, list[np.ndarray]] = defaultdict(list)
    pred_by_baseline: dict[str, list[np.ndarray]] = defaultdict(list)

    if PREDICTION_PATH.exists():
        PREDICTION_PATH.unlink()
    wrote_header = False

    for well in train_wells():
        df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
        target_rows = target_rows_from_original_hidden(df)
        known_allowed_start_row = 0
        known_allowed_end_row = int(target_rows[0] - 1)
        truth = df.loc[target_rows, "TVT"].to_numpy(dtype=float)
        md_target = df.loc[target_rows, "MD"].to_numpy(dtype=float)

        for config in BASELINE_CONFIGS:
            baseline = str(config["baseline"])
            preds, diagnostics = run_baseline(
                df,
                target_rows,
                baseline=baseline,
                known_allowed_start_row=known_allowed_start_row,
                known_allowed_end_row=known_allowed_end_row,
            )
            metrics = regression_metrics(truth, preds)
            errors = preds - truth
            abs_errors = np.abs(errors)
            errors_by_baseline[baseline].append(errors)
            truth_by_baseline[baseline].append(truth)
            pred_by_baseline[baseline].append(preds)

            records.append(
                {
                    "data_hash": data_hash,
                    "baseline": baseline,
                    "family": config["family"],
                    "tail_window": config["tail_window"],
                    "well": well,
                    "rows": len(df),
                    "known_rows": int(df.loc[:known_allowed_end_row, "TVT_input"].notna().sum()),
                    "target_rows": len(target_rows),
                    "target_start_row": int(target_rows[0]),
                    "target_end_row": int(target_rows[-1]),
                    "target_md_span": float(md_target[-1] - md_target[0]),
                    "target_tvt_span": float(truth.max() - truth.min()),
                    "target_gr_missing_rate": float(df.loc[target_rows, "GR"].isna().mean()),
                    "baseline_slope": diagnostics.get("baseline_slope", np.nan),
                    "max_jump": max_step_jump(preds),
                    "residual_bias": metrics["bias"],
                    **metrics,
                }
            )

            prediction_chunk = pd.DataFrame(
                {
                    "data_hash": data_hash,
                    "baseline": baseline,
                    "well": well,
                    "row": target_rows,
                    "id": [f"{well}_{row}" for row in target_rows],
                    "md": md_target,
                    "true_tvt": truth,
                    "pred_tvt": preds,
                    "error": errors,
                    "abs_error": abs_errors,
                }
            )
            prediction_chunk.to_csv(PREDICTION_PATH, index=False, mode="a", header=not wrote_header)
            wrote_header = True

    detail = pd.DataFrame(records).sort_values(["baseline", "rmse"], ascending=[True, False])
    detail.to_csv(DETAIL_PATH, index=False)

    overall_rows = []
    for config in BASELINE_CONFIGS:
        baseline = str(config["baseline"])
        truth = np.concatenate(truth_by_baseline[baseline])
        preds = np.concatenate(pred_by_baseline[baseline])
        metrics = regression_metrics(truth, preds)
        per_well = detail[detail["baseline"].eq(baseline)]
        overall_rows.append(
            {
                "data_hash": data_hash,
                "baseline": baseline,
                "family": config["family"],
                "tail_window": config["tail_window"],
                "wells": int(per_well["well"].nunique()),
                "target_rows": int(len(truth)),
                "row_weighted_rmse": metrics["rmse"],
                "row_weighted_mae": metrics["mae"],
                "median_abs_error": metrics["median_abs_error"],
                "p90_abs_error": metrics["p90_abs_error"],
                "p95_abs_error": metrics["p95_abs_error"],
                "p99_abs_error": metrics["p99_abs_error"],
                "max_abs_error": metrics["max_abs_error"],
                "bias": metrics["bias"],
                "mean_well_rmse": float(per_well["rmse"].mean()),
                "median_well_rmse": float(per_well["rmse"].median()),
                "worst_well_rmse": float(per_well["rmse"].max()),
            }
        )

    overall = pd.DataFrame(overall_rows).sort_values("row_weighted_rmse")
    overall.to_csv(OVERALL_PATH, index=False)
    best_baseline = str(overall.iloc[0]["baseline"])
    conservative_baseline = "B0_constant_last"
    geometry_stress_baseline = "B2_tail_slope_k200"
    worst_20 = detail[detail["baseline"].eq(best_baseline)].nlargest(20, "rmse")
    best_20 = detail[detail["baseline"].eq(best_baseline)].nsmallest(20, "rmse")
    bucketed = bucket_summary(detail, best_baseline)
    subsets = subset_summary(detail, best_baseline)

    lines = [
        "# Baseline Cross-Validation Report",
        "",
        "## Evaluation Design",
        "",
        "Each training well contains an official-style hidden tail where `TVT_input` is NaN and `TVT` remains available as truth. This report masks nothing else: it scores the original hidden segment and only allows `TVT_input` rows before the hidden interval.",
        "",
        f"- Data hash: `{data_hash}`",
        f"- Wells evaluated: {detail['well'].nunique():,}",
        f"- Target rows per baseline: {int(overall.iloc[0]['target_rows']):,}",
        f"- Baseline families: {', '.join(sorted(detail['family'].unique()))}",
        "",
        "## Overall Metrics by Baseline",
        "",
        overall.round(4).to_markdown(index=False),
        "",
        "## Baseline Selection",
        "",
        f"- Best row-weighted CV baseline: `{best_baseline}`",
        f"- Conservative control baseline: `{conservative_baseline}`",
        f"- Geometry trend stress-test baseline: `{geometry_stress_baseline}`",
        "- B3 robust polynomial and B4 smoothed baseline are intentionally deferred until residual modeling has a stable target; Part 1 acceptance requires B0/B1/B2 and the current evidence shows slope extrapolation is risky.",
        "",
        "## RMSE by Hidden-Interval Length",
        "",
        bucketed.round(4).to_markdown(index=False),
        "",
        "## Robustness Subsets",
        "",
        subsets.round(4).to_markdown(index=False),
        "",
        "## Worst 20 Wells",
        "",
        worst_20.round(4).to_markdown(index=False),
        "",
        "## Best 20 Wells",
        "",
        best_20.round(4).to_markdown(index=False),
        "",
        "## Error Distribution",
        "",
        "- Row-level RMSE drives Kaggle score, but per-well statistics are tracked to prevent a leaderboard gain from hiding unstable wells.",
        "- Worst wells are passed into `scripts/analyze_baseline_failures.py` for failure typing and diagnostic plots.",
        "",
        "## Outputs",
        "",
        f"- Per-well metrics: `{DETAIL_PATH.relative_to(ROOT)}`",
        f"- Row-level predictions: `{PREDICTION_PATH.relative_to(ROOT)}`",
        f"- Overall metrics: `{OVERALL_PATH.relative_to(ROOT)}`",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))

    print(f"Wrote {DETAIL_PATH}")
    print(f"Wrote {PREDICTION_PATH}")
    print(f"Wrote {OVERALL_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"best_baseline={best_baseline} row_weighted_rmse={overall.iloc[0]['row_weighted_rmse']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
