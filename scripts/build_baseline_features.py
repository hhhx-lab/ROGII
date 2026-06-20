#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

from part2_utils import BASELINE_NAME, FEATURE_DIR, data_hash_short, ensure_part2_dirs, slope_stats, target_rows_from_tvt_input
from rogii_utils import (
    DATA_DIR,
    REPORT_DIR,
    TEST_DIR,
    TRAIN_DIR,
    assert_data_contract_ready,
    parse_submission_ids,
    run_baseline,
    train_wells,
)


BASELINE_TRAIN_PATH = FEATURE_DIR / "baseline_features_train.parquet"
BASELINE_TEST_PATH = FEATURE_DIR / "baseline_features_test.parquet"
TARGET_PATH = FEATURE_DIR / "residual_targets.parquet"
REPORT_PATH = REPORT_DIR / "residual_target_report.md"


def summarize_residual_group(frame: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for value, part in frame.groupby(group_col, observed=True, dropna=False):
        residual = part["residual_target"].astype(float)
        abs_residual = residual.abs()
        rows.append(
            {
                group_col: str(value),
                "rows": len(part),
                "wells": part["well"].nunique(),
                "residual_mean": residual.mean(),
                "residual_std": residual.std(),
                "residual_rmse": float(np.sqrt(np.mean(np.square(residual)))),
                "median_abs_residual": abs_residual.median(),
                "p95_abs_residual": abs_residual.quantile(0.95),
            }
        )
    return pd.DataFrame(rows)


def build_rows(df: pd.DataFrame, well: str, target_rows: np.ndarray, truth_available: bool) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    known_end = int(target_rows[0] - 1)
    known = df.loc[:known_end]
    known_md = known["MD"].to_numpy(dtype=float)
    known_tvt = known["TVT_input"].to_numpy(dtype=float)
    target_md = df.loc[target_rows, "MD"].to_numpy(dtype=float)
    target_gr = df.loc[target_rows, "GR"]
    stats = slope_stats(known_md, known_tvt)

    baseline_tvt, _ = run_baseline(
        df,
        target_rows,
        baseline=BASELINE_NAME,
        known_allowed_start_row=0,
        known_allowed_end_row=known_end,
    )
    b1_tvt, b1_diag = run_baseline(df, target_rows, baseline="B1_linear_md", known_allowed_start_row=0, known_allowed_end_row=known_end)
    b2_50, b2_50_diag = run_baseline(df, target_rows, baseline="B2_tail_slope_k50", known_allowed_start_row=0, known_allowed_end_row=known_end)
    b2_200, b2_200_diag = run_baseline(df, target_rows, baseline="B2_tail_slope_k200", known_allowed_start_row=0, known_allowed_end_row=known_end)
    b2_500, b2_500_diag = run_baseline(df, target_rows, baseline="B2_tail_slope_k500", known_allowed_start_row=0, known_allowed_end_row=known_end)

    target_rows_count = len(target_rows)
    known_rows_count = len(known)
    distance_md = target_md - float(known_md[-1])
    distance_rows = target_rows - known_end
    gr_missing_rate = float(target_gr.isna().mean()) if len(target_gr) else 0.0
    slope_stability = 1.0 / (1.0 + abs(stats["std"]))
    length_penalty = 1.0 / (1.0 + target_rows_count / max(1.0, known_rows_count))
    gr_quality = 1.0 - gr_missing_rate
    baseline_confidence = float(np.clip(0.45 * slope_stability + 0.35 * length_penalty + 0.20 * gr_quality, 0.0, 1.0))

    features = pd.DataFrame(
        {
            "split_id": f"original_hidden__{well}__{int(target_rows[0])}_{int(target_rows[-1])}",
            "well": well,
            "row": target_rows.astype(np.int32),
            "id": [f"{well}_{int(row)}" for row in target_rows],
            "baseline_name": BASELINE_NAME,
            "baseline_tvt": baseline_tvt.astype("float32"),
            "baseline_slope": np.zeros(target_rows_count, dtype="float32"),
            "baseline_tail_window": np.zeros(target_rows_count, dtype="float32"),
            "baseline_local_slope_mean": np.full(target_rows_count, stats["mean"], dtype="float32"),
            "baseline_local_slope_std": np.full(target_rows_count, stats["std"], dtype="float32"),
            "baseline_known_tail_slope_50": np.full(target_rows_count, stats["tail_50"], dtype="float32"),
            "baseline_known_tail_slope_100": np.full(target_rows_count, stats["tail_100"], dtype="float32"),
            "baseline_known_tail_slope_200": np.full(target_rows_count, stats["tail_200"], dtype="float32"),
            "baseline_known_tail_slope_500": np.full(target_rows_count, stats["tail_500"], dtype="float32"),
            "baseline_confidence": np.full(target_rows_count, baseline_confidence, dtype="float32"),
            "baseline_distance_penalty": (1.0 / (1.0 + distance_rows / max(1.0, target_rows_count))).astype("float32"),
            "last_known_row": np.full(target_rows_count, known_end, dtype="int32"),
            "last_known_MD": np.full(target_rows_count, known_md[-1], dtype="float32"),
            "last_known_TVT_input": np.full(target_rows_count, known_tvt[-1], dtype="float32"),
            "distance_row_from_last_known": distance_rows.astype("float32"),
            "distance_MD_from_last_known": distance_md.astype("float32"),
            "known_rows_count": np.full(target_rows_count, known_rows_count, dtype="int32"),
            "target_rows_count": np.full(target_rows_count, target_rows_count, dtype="int32"),
            "known_ratio": np.full(target_rows_count, known_rows_count / len(df), dtype="float32"),
            "target_gr_missing_rate": np.full(target_rows_count, gr_missing_rate, dtype="float32"),
            "b1_linear_md_pred": b1_tvt.astype("float32"),
            "b1_linear_md_slope": np.full(target_rows_count, b1_diag.get("baseline_slope", 0.0), dtype="float32"),
            "b2_tail_slope_k50_pred": b2_50.astype("float32"),
            "b2_tail_slope_k50_slope": np.full(target_rows_count, b2_50_diag.get("baseline_slope", 0.0), dtype="float32"),
            "b2_tail_slope_k200_pred": b2_200.astype("float32"),
            "b2_tail_slope_k200_slope": np.full(target_rows_count, b2_200_diag.get("baseline_slope", 0.0), dtype="float32"),
            "b2_tail_slope_k500_pred": b2_500.astype("float32"),
            "b2_tail_slope_k500_slope": np.full(target_rows_count, b2_500_diag.get("baseline_slope", 0.0), dtype="float32"),
        }
    )

    targets = None
    if truth_available:
        truth = df.loc[target_rows, "TVT"].to_numpy(dtype=float)
        targets = pd.DataFrame(
            {
                "split_id": features["split_id"],
                "well": well,
                "row": target_rows.astype(np.int32),
                "id": features["id"],
                "true_tvt": truth.astype("float32"),
                "baseline_tvt": baseline_tvt.astype("float32"),
                "residual_target": (truth - baseline_tvt).astype("float32"),
                "baseline_name": BASELINE_NAME,
            }
        )
    return features, targets


def main() -> int:
    ensure_part2_dirs()
    data_version = assert_data_contract_ready()
    data_hash = data_hash_short()

    train_feature_parts = []
    target_parts = []
    for well in train_wells():
        df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
        target_rows = target_rows_from_tvt_input(df)
        features, targets = build_rows(df, well, target_rows, truth_available=True)
        train_feature_parts.append(features)
        target_parts.append(targets)

    train_features = pd.concat(train_feature_parts, ignore_index=True)
    targets = pd.concat(target_parts, ignore_index=True)
    train_features.to_parquet(BASELINE_TRAIN_PATH, index=False)
    targets.to_parquet(TARGET_PATH, index=False)

    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    parsed = parse_submission_ids(sample)
    test_feature_parts = []
    for well, part in parsed.groupby("well", sort=True):
        df = pd.read_csv(TEST_DIR / f"{well}__horizontal_well.csv")
        target_rows = part["row"].to_numpy(dtype=int)
        features, _ = build_rows(df, well, target_rows, truth_available=False)
        test_feature_parts.append(features)
    test_features = pd.concat(test_feature_parts, ignore_index=True)
    test_features.to_parquet(BASELINE_TEST_PATH, index=False)

    residual = targets["residual_target"].astype(float)
    target_context = train_features[["id", "target_rows_count", "target_gr_missing_rate"]].copy()
    residual_context = targets.merge(target_context, on="id", how="left", validate="one_to_one")
    residual_context["abs_residual"] = residual_context["residual_target"].abs()
    residual_context["target_length_bucket"] = pd.cut(
        residual_context["target_rows_count"],
        bins=[0, 500, 1500, 3000, 5000, np.inf],
        labels=["0-500", "501-1500", "1501-3000", "3001-5000", "5001+"],
        include_lowest=True,
    )
    residual_context["gr_missing_bucket"] = pd.cut(
        residual_context["target_gr_missing_rate"],
        bins=[-0.001, 0.0, 0.25, 0.50, 0.75, 1.0],
        labels=["0", "0-25%", "25-50%", "50-75%", "75-100%"],
        include_lowest=True,
    )
    residual_context["baseline_abs_error_bucket"] = pd.qcut(
        residual_context["abs_residual"].rank(method="first"),
        q=5,
        labels=["q1_lowest", "q2", "q3", "q4", "q5_highest"],
    )
    by_well = (
        targets.groupby("well")
        .agg(rows=("row", "count"), residual_mean=("residual_target", "mean"), residual_std=("residual_target", "std"))
        .reset_index()
    )
    lines = [
        "# Residual Target Report",
        "",
        f"- Data hash: `{data_hash}`",
        f"- Baseline anchor: `{BASELINE_NAME}`",
        f"- Train rows: {len(targets):,}",
        f"- Train wells: {targets['well'].nunique():,}",
        f"- Test rows: {len(test_features):,}",
        "",
        "## Residual Distribution",
        "",
        pd.DataFrame(
            [
                {
                    "mean": residual.mean(),
                    "std": residual.std(),
                    "p01": residual.quantile(0.01),
                    "p05": residual.quantile(0.05),
                    "p50": residual.quantile(0.50),
                    "p95": residual.quantile(0.95),
                    "p99": residual.quantile(0.99),
                    "min": residual.min(),
                    "max": residual.max(),
                }
            ]
        ).round(4).to_markdown(index=False),
        "",
        "## Residual by Well",
        "",
        by_well.describe(include="all").fillna("").to_markdown(),
        "",
        "## Residual by Target Length",
        "",
        summarize_residual_group(residual_context, "target_length_bucket").round(4).to_markdown(index=False),
        "",
        "## Residual by Baseline Error Bucket",
        "",
        summarize_residual_group(residual_context, "baseline_abs_error_bucket").round(4).to_markdown(index=False),
        "",
        "## Residual by GR Missing Rate",
        "",
        summarize_residual_group(residual_context, "gr_missing_bucket").round(4).to_markdown(index=False),
        "",
        "## Outputs",
        "",
        f"- Baseline train features: `{BASELINE_TRAIN_PATH.relative_to(BASELINE_TRAIN_PATH.parents[1])}`",
        f"- Baseline test features: `{BASELINE_TEST_PATH.relative_to(BASELINE_TEST_PATH.parents[1])}`",
        f"- Residual targets: `{TARGET_PATH.relative_to(TARGET_PATH.parents[1])}`",
        "",
        "## Server Scaling",
        "",
        "Feature generation is full-row and deterministic. Model training can be scaled independently with `ROGII_PART2_TRAIN_ROWS_PER_WELL=0` on a server.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))

    print(f"Wrote {BASELINE_TRAIN_PATH}")
    print(f"Wrote {BASELINE_TEST_PATH}")
    print(f"Wrote {TARGET_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"train_rows={len(train_features)} test_rows={len(test_features)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
