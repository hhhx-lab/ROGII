#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

from rogii_utils import (
    BASELINE_CONFIGS,
    OUTPUT_DIR,
    REPORT_DIR,
    ROOT,
    TRAIN_DIR,
    apply_cv_split_mask,
    assert_data_contract_ready,
    data_hash_short,
    ensure_project_dirs,
    max_step_jump,
    regression_metrics,
    run_baseline,
)


SPLITS_PATH = OUTPUT_DIR / "cv_splits.csv"
DETAIL_PATH = OUTPUT_DIR / "baseline_multimask_by_split.csv"
OVERALL_PATH = OUTPUT_DIR / "baseline_multimask_overall.csv"
REPORT_PATH = REPORT_DIR / "baseline_multimask_report.md"


def main() -> int:
    ensure_project_dirs()
    data_version = assert_data_contract_ready()
    if not SPLITS_PATH.exists():
        raise FileNotFoundError("outputs/cv_splits.csv is missing; run scripts/make_cv_splits.py first")

    data_hash = data_hash_short(data_version)
    splits = pd.read_csv(SPLITS_PATH)
    records: list[dict[str, object]] = []

    for well, well_splits in splits.groupby("well", sort=True):
        df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
        for _, split in well_splits.iterrows():
            target_rows = np.arange(int(split["start_row"]), int(split["end_row"]) + 1, dtype=int)
            truth = df.loc[target_rows, "TVT"].to_numpy(dtype=float)
            eval_df = apply_cv_split_mask(df, split, replace_tvt_input=True)
            for config in BASELINE_CONFIGS:
                baseline = str(config["baseline"])
                preds, diagnostics = run_baseline(
                    eval_df,
                    target_rows,
                    baseline=baseline,
                    known_allowed_start_row=int(split["known_allowed_start_row"]),
                    known_allowed_end_row=int(split["known_allowed_end_row"]),
                )
                metrics = regression_metrics(truth, preds)
                records.append(
                    {
                        "data_hash": data_hash,
                        "split_id": split["split_id"],
                        "well": well,
                        "mask_type": split["mask_type"],
                        "baseline": baseline,
                        "family": config["family"],
                        "tail_window": config["tail_window"],
                        "target_rows": int(split["target_rows"]),
                        "known_rows_before": int(split["known_rows_before"]),
                        "gr_missing_rate": float(split["gr_missing_rate"]),
                        "curvature_proxy": float(split["curvature_proxy"]),
                        "baseline_slope": diagnostics.get("baseline_slope", np.nan),
                        "max_jump": max_step_jump(preds),
                        **metrics,
                    }
                )

    detail = pd.DataFrame(records)
    detail.to_csv(DETAIL_PATH, index=False)

    overall_rows = []
    for (mask_type, baseline), frame in detail.groupby(["mask_type", "baseline"], sort=True):
        weights = frame["target_rows"].to_numpy(dtype=float)
        row_weighted_rmse = float(np.sqrt(np.sum((frame["rmse"].to_numpy(dtype=float) ** 2) * weights) / weights.sum()))
        row_weighted_mae = float(np.sum(frame["mae"].to_numpy(dtype=float) * weights) / weights.sum())
        overall_rows.append(
            {
                "data_hash": data_hash,
                "mask_type": mask_type,
                "baseline": baseline,
                "family": frame["family"].iloc[0],
                "tail_window": frame["tail_window"].iloc[0],
                "splits": len(frame),
                "wells": frame["well"].nunique(),
                "target_rows": int(frame["target_rows"].sum()),
                "row_weighted_rmse": row_weighted_rmse,
                "row_weighted_mae": row_weighted_mae,
                "mean_split_rmse": float(frame["rmse"].mean()),
                "median_split_rmse": float(frame["rmse"].median()),
                "worst_split_rmse": float(frame["rmse"].max()),
                "mean_bias": float(frame["bias"].mean()),
            }
        )

    overall = pd.DataFrame(overall_rows).sort_values(["mask_type", "row_weighted_rmse"])
    overall.to_csv(OVERALL_PATH, index=False)

    winners = overall.loc[overall.groupby("mask_type")["row_weighted_rmse"].idxmin()].sort_values("mask_type")
    family_pivot = overall.pivot_table(
        index="mask_type",
        columns="baseline",
        values="row_weighted_rmse",
        aggfunc="first",
    ).reset_index()

    lines = [
        "# Baseline Multi-Mask Report",
        "",
        f"- Data hash: `{data_hash}`",
        f"- Splits evaluated: {detail['split_id'].nunique()}",
        f"- Mask types: {detail['mask_type'].nunique()}",
        f"- Baselines: {detail['baseline'].nunique()}",
        "",
        "## Best Baseline by Mask Type",
        "",
        winners.round(4).to_markdown(index=False),
        "",
        "## Row-Weighted RMSE Pivot",
        "",
        family_pivot.round(4).to_markdown(index=False),
        "",
        "## Acceptance Notes",
        "",
        "- Artificial masks regenerate `TVT_input` from `TVT` only in the allowed known interval.",
        "- Hidden target intervals never expose `TVT` to baseline features.",
        "- This report is split-level only; row-level predictions are intentionally limited to the official-style original hidden CV.",
        "",
        "## Outputs",
        "",
        f"- Split-level metrics: `{DETAIL_PATH.relative_to(ROOT)}`",
        f"- Overall metrics: `{OVERALL_PATH.relative_to(ROOT)}`",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))

    print(f"Wrote {DETAIL_PATH}")
    print(f"Wrote {OVERALL_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"splits={detail['split_id'].nunique()} mask_types={detail['mask_type'].nunique()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
