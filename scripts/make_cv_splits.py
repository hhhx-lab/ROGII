#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from rogii_utils import (
    OUTPUT_DIR,
    REPORT_DIR,
    ROOT,
    TRAIN_DIR,
    assert_data_contract_ready,
    contiguous_true_bounds,
    data_hash_short,
    ensure_project_dirs,
    train_wells,
)


SPLITS_PATH = OUTPUT_DIR / "cv_splits.csv"
REPORT_PATH = REPORT_DIR / "cv_design.md"
MASK_SEED = 20260620


def bounded_window(n_rows: int, start: int, length: int, min_known_before: int) -> tuple[int, int]:
    length = max(20, min(length, n_rows - min_known_before))
    start = max(min_known_before, min(start, n_rows - length))
    end = start + length - 1
    return int(start), int(end)


def exact_window_scores(values: np.ndarray, length: int, min_start: int, max_start: int) -> np.ndarray:
    filled = np.nan_to_num(values.astype(float), nan=0.0)
    prefix = np.concatenate([[0.0], np.cumsum(filled)])
    starts = np.arange(min_start, max_start + 1)
    return (prefix[starts + length] - prefix[starts]) / length


def choose_high_gr_missing(df: pd.DataFrame, rng: np.random.Generator, min_known_before: int) -> tuple[int, int]:
    n_rows = len(df)
    length = max(200, int(round(n_rows * 0.25)))
    length = min(length, n_rows - min_known_before)
    max_start = n_rows - length
    if max_start <= min_known_before:
        return bounded_window(n_rows, min_known_before, n_rows - min_known_before, min_known_before)
    scores = exact_window_scores(df["GR"].isna().to_numpy(dtype=float), length, min_known_before, max_start)
    best = np.flatnonzero(scores == scores.max())
    start = int(best[rng.integers(0, len(best))] + min_known_before)
    return bounded_window(n_rows, start, length, min_known_before)


def choose_high_curvature(df: pd.DataFrame, rng: np.random.Generator, min_known_before: int) -> tuple[int, int]:
    n_rows = len(df)
    length = max(200, int(round(n_rows * 0.20)))
    length = min(length, n_rows - min_known_before)
    max_start = n_rows - length
    if max_start <= min_known_before:
        return bounded_window(n_rows, min_known_before, n_rows - min_known_before, min_known_before)

    md = df["MD"].to_numpy(dtype=float)
    tvt = df["TVT"].to_numpy(dtype=float)
    denom = np.diff(md)
    slope = np.divide(np.diff(tvt), denom, out=np.zeros_like(denom, dtype=float), where=denom != 0)
    curvature = np.concatenate([[0.0], np.abs(np.diff(slope)), [0.0]])
    scores = exact_window_scores(curvature, length, min_known_before, max_start)
    best = np.flatnonzero(scores == scores.max())
    start = int(best[rng.integers(0, len(best))] + min_known_before)
    return bounded_window(n_rows, start, length, min_known_before)


def window_stats(df: pd.DataFrame, start: int, end: int) -> dict[str, float]:
    target = np.arange(start, end + 1)
    md = df.loc[target, "MD"].to_numpy(dtype=float)
    tvt = df.loc[target, "TVT"].to_numpy(dtype=float)
    gr = df.loc[target, "GR"]
    denom = np.diff(md)
    slopes = np.divide(np.diff(tvt), denom, out=np.full_like(denom, np.nan, dtype=float), where=denom != 0)
    slopes = slopes[np.isfinite(slopes)]
    curvature = np.abs(np.diff(slopes)) if len(slopes) > 1 else np.asarray([0.0])
    return {
        "target_rows": int(len(target)),
        "known_rows_before": int(start),
        "known_allowed_start_row": 0,
        "known_allowed_end_row": int(start - 1),
        "md_span": float(md[-1] - md[0]) if len(md) else 0.0,
        "tvt_span": float(np.nanmax(tvt) - np.nanmin(tvt)) if len(tvt) else 0.0,
        "gr_missing_rate": float(gr.isna().mean()) if len(gr) else 0.0,
        "local_slope_mean": float(np.nanmean(slopes)) if len(slopes) else 0.0,
        "local_slope_std": float(np.nanstd(slopes)) if len(slopes) else 0.0,
        "curvature_proxy": float(np.nanmean(curvature)) if len(curvature) else 0.0,
    }


def split_record(well: str, mask_type: str, start: int, end: int, df: pd.DataFrame) -> dict[str, object]:
    stats = window_stats(df, start, end)
    return {
        "split_id": f"{mask_type}__{well}__{start}_{end}",
        "well": well,
        "mask_type": mask_type,
        "start_row": int(start),
        "end_row": int(end),
        **stats,
        "mask_seed": MASK_SEED,
    }


def original_hidden_window(df: pd.DataFrame) -> tuple[int, int]:
    mask = df["TVT_input"].isna().to_numpy()
    return contiguous_true_bounds(mask)


def artificial_windows(df: pd.DataFrame, rng: np.random.Generator) -> dict[str, tuple[int, int]]:
    n_rows = len(df)
    min_known_before = max(100, int(round(n_rows * 0.10)))

    trailing_short_frac = rng.uniform(0.10, 0.25)
    trailing_short_length = int(round(n_rows * trailing_short_frac))

    trailing_long_frac = rng.uniform(0.40, 0.75)
    trailing_long_length = int(round(n_rows * trailing_long_frac))

    mid_length = int(round(n_rows * rng.uniform(0.10, 0.25)))
    mid_center = int(round(n_rows * rng.uniform(0.42, 0.62)))
    mid_start = mid_center - mid_length // 2

    random_length = int(round(n_rows * rng.uniform(0.15, 0.35)))
    random_max_start = max(min_known_before, n_rows - random_length)
    random_start = int(rng.integers(min_known_before, random_max_start + 1))

    return {
        "trailing_short": bounded_window(n_rows, n_rows - trailing_short_length, trailing_short_length, min_known_before),
        "trailing_long": bounded_window(n_rows, n_rows - trailing_long_length, trailing_long_length, min_known_before),
        "mid_contiguous": bounded_window(n_rows, mid_start, mid_length, min_known_before),
        "random_contiguous": bounded_window(n_rows, random_start, random_length, min_known_before),
        "high_gr_missing": choose_high_gr_missing(df, rng, min_known_before),
        "high_curvature": choose_high_curvature(df, rng, min_known_before),
    }


def main() -> int:
    ensure_project_dirs()
    rng = np.random.default_rng(MASK_SEED)
    data_version = assert_data_contract_ready()

    records: list[dict[str, object]] = []
    for well in train_wells():
        df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
        start, end = original_hidden_window(df)
        records.append(split_record(well, "original_hidden", start, end, df))
        for mask_type, (mask_start, mask_end) in artificial_windows(df, rng).items():
            records.append(split_record(well, mask_type, mask_start, mask_end, df))

    splits = pd.DataFrame(records)
    splits.to_csv(SPLITS_PATH, index=False)

    summary = (
        splits.groupby("mask_type")
        .agg(
            wells=("well", "nunique"),
            splits=("split_id", "count"),
            mean_target_rows=("target_rows", "mean"),
            median_target_rows=("target_rows", "median"),
            mean_gr_missing_rate=("gr_missing_rate", "mean"),
            mean_curvature_proxy=("curvature_proxy", "mean"),
        )
        .reset_index()
        .sort_values("mask_type")
    )

    coverage_failures = summary[summary["wells"] < 300]
    lines = [
        "# CV Design",
        "",
        f"- Data hash: `{data_hash_short(data_version)}`",
        f"- Mask seed: `{MASK_SEED}`",
        f"- Train wells: {splits['well'].nunique()}",
        f"- Total splits: {len(splits)}",
        "",
        "## Mask Summary",
        "",
        summary.round(4).to_markdown(index=False),
        "",
        "## Leakage Controls",
        "",
        "- `start_row` to `end_row` defines the validation target interval.",
        "- `known_allowed_start_row` and `known_allowed_end_row` define the only rows whose `TVT_input` may be used by baseline or known-segment features.",
        "- For artificial masks, `TVT_input_masked` must be regenerated by copying `TVT` only outside the target interval and within the allowed known rows.",
        "- `MD/X/Y/Z/GR` inside the target interval are allowed because Kaggle test provides them.",
        "- `TVT` inside the target interval is truth only and must not be used as a feature.",
        "- `local_slope_mean`, `local_slope_std`, and `curvature_proxy` are truth-derived diagnostics for split design and reporting only; model feature builders must not read them as predictors.",
        "- Shared masking logic lives in `rogii_utils.apply_cv_split_mask`, which creates `TVT_input_masked` and removes target/future `TVT_input` visibility.",
        "",
        "## Acceptance",
        "",
        f"- Mask types generated: {splits['mask_type'].nunique()}",
        f"- Minimum wells per mask type: {int(summary['wells'].min())}",
        f"- Coverage failures: {len(coverage_failures)}",
        f"- Split CSV: `{SPLITS_PATH.relative_to(ROOT)}`",
        "",
    ]
    if len(coverage_failures):
        lines.extend(["## Coverage Failures", "", coverage_failures.to_markdown(index=False), ""])
    REPORT_PATH.write_text("\n".join(lines))

    print(f"Wrote {SPLITS_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"mask_types={splits['mask_type'].nunique()} min_wells_per_type={int(summary['wells'].min())}")
    return 1 if len(coverage_failures) else 0


if __name__ == "__main__":
    raise SystemExit(main())
