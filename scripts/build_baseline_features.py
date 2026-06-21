#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from baseline_tail_slope import tail_slope_prediction
from data_paths import load_sample_submission, resolve_test_dir, resolve_train_dir


ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "features"
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"


def slope_stats(values: np.ndarray, md: np.ndarray) -> tuple[float, float]:
    if len(values) < 3:
        return float("nan"), float("nan")
    slopes = np.diff(values) / np.diff(md)
    slopes = slopes[np.isfinite(slopes)]
    if len(slopes) == 0:
        return float("nan"), float("nan")
    return float(np.median(slopes)), float(np.std(slopes))


def baseline_confidence(known_count: int, target_count: int, slope_std: float, gr_missing_rate: float) -> float:
    score = 0.0
    if np.isfinite(slope_std):
        score = float(1.0 / (1.0 + slope_std))
    score *= float(min(known_count / max(target_count, 1), 2.0) / 2.0)
    if np.isfinite(gr_missing_rate):
        score *= float(1.0 - min(gr_missing_rate, 1.0) * 0.5)
    return float(max(score, 0.0))


def target_rows_for(df: pd.DataFrame) -> np.ndarray:
    return np.flatnonzero(df["TVT_input"].isna().to_numpy())


def build_frame(df: pd.DataFrame, split: str, well: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_rows = target_rows_for(df)
    baseline_pred = tail_slope_prediction(df, target_rows, tail_window=200)

    known_mask = ~df["TVT_input"].isna().to_numpy()
    known_count = int(known_mask.sum())
    target_count = int(len(target_rows))
    known_md = df.loc[known_mask, "MD"].to_numpy(dtype=float)
    known_tvt = df.loc[known_mask, "TVT_input"].to_numpy(dtype=float)
    slope_med, slope_std = slope_stats(known_tvt, known_md)
    gr_missing_rate = float(df.loc[target_rows, "GR"].isna().mean()) if target_count else float("nan")
    conf = baseline_confidence(known_count, target_count, slope_std, gr_missing_rate)

    last_known_row = int(np.flatnonzero(known_mask)[-1]) if known_mask.any() else 0
    last_known_md = float(df.loc[known_mask, "MD"].iloc[-1]) if known_mask.any() else float(df["MD"].iloc[0])
    last_known_tvt = float(df.loc[known_mask, "TVT_input"].iloc[-1]) if known_mask.any() else float(df["TVT"].iloc[0])
    first_known_tvt = float(df.loc[known_mask, "TVT_input"].iloc[0]) if known_mask.any() else float(df["TVT"].iloc[0])

    frame = pd.DataFrame(
        {
            "well": well,
            "split": split,
            "row": target_rows,
            "id": [f"{well}_{int(row)}" for row in target_rows],
            "baseline_tvt": baseline_pred,
            "known_rows": known_count,
            "target_rows": target_count,
            "known_ratio": float(known_count / max(len(df), 1)),
            "target_ratio": float(target_count / max(len(df), 1)),
            "last_known_row": last_known_row,
            "last_known_md": last_known_md,
            "last_known_tvt": last_known_tvt,
            "first_known_tvt": first_known_tvt,
            "distance_from_last_known_row": target_rows - last_known_row,
            "distance_from_last_known_md": df.loc[target_rows, "MD"].to_numpy(dtype=float) - last_known_md,
            "baseline_slope_median": slope_med,
            "baseline_slope_std": slope_std,
            "baseline_confidence": conf,
            "gr_missing_rate": gr_missing_rate,
            "baseline_tail_window": 200,
            "baseline_pred_delta_from_last_known": baseline_pred - last_known_tvt,
            "baseline_pred_delta_from_first_known": baseline_pred - first_known_tvt,
            "baseline_pred_delta_from_known_span": baseline_pred - float(np.nanmean(known_tvt)) if len(known_tvt) else baseline_pred,
        }
    )

    if len(target_rows):
        frame["baseline_md_step"] = np.diff(np.r_[last_known_md, df.loc[target_rows, "MD"].to_numpy(dtype=float)])
        frame["baseline_tvt_step"] = np.diff(np.r_[last_known_tvt, baseline_pred])
    else:
        frame["baseline_md_step"] = []
        frame["baseline_tvt_step"] = []

    if split == "train":
        residual = pd.DataFrame(
            {
                "well": well,
                "split": split,
                "row": target_rows,
                "id": [f"{well}_{int(row)}" for row in target_rows],
                "truth_tvt": df.loc[target_rows, "TVT"].to_numpy(dtype=float),
                "baseline_tvt": baseline_pred,
            }
        )
        residual["residual_target"] = residual["truth_tvt"] - residual["baseline_tvt"]
    else:
        residual = pd.DataFrame(columns=["well", "split", "row", "id", "truth_tvt", "baseline_tvt", "residual_target"])
    return frame, residual


def iter_wells(data_dir: Path, limit_wells: int | None) -> list[Path]:
    files = sorted(data_dir.glob("*__horizontal_well.csv"))
    if limit_wells is not None:
        files = files[:limit_wells]
    return files


def reset_outputs() -> None:
    FEATURE_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    for path in [
        FEATURE_DIR / "baseline_features_train.csv",
        FEATURE_DIR / "baseline_features_test.csv",
        FEATURE_DIR / "residual_targets.csv",
        OUTPUT_DIR / "baseline_predictions_train_hidden.csv",
        OUTPUT_DIR / "baseline_predictions_test.csv",
        REPORT_DIR / "residual_target_report.md",
    ]:
        path.unlink(missing_ok=True)


def write_residual_report(residual_df: pd.DataFrame) -> None:
    abs_resid = residual_df["residual_target"].abs()
    by_well = (
        residual_df.groupby("well", as_index=False)
        .agg(
            rows=("id", "count"),
            residual_rmse=("residual_target", lambda s: float(np.sqrt(np.mean(np.square(s.to_numpy(dtype=float)))))),
            residual_mae=("residual_target", lambda s: float(np.mean(np.abs(s.to_numpy(dtype=float))))),
            residual_bias=("residual_target", lambda s: float(np.mean(s.to_numpy(dtype=float)))),
            target_span=("truth_tvt", lambda s: float(np.nanmax(s) - np.nanmin(s))),
        )
        .sort_values("residual_rmse", ascending=False)
    )
    report = [
        "# Residual Target Report",
        "",
        f"- Target rows: {len(residual_df):,}",
        f"- Residual RMSE around baseline: {float(np.sqrt(np.mean(np.square(residual_df['residual_target'].to_numpy(dtype=float))))):.4f}",
        f"- Residual MAE around baseline: {float(np.mean(abs_resid.to_numpy(dtype=float))):.4f}",
        f"- Residual bias around baseline: {float(np.mean(residual_df['residual_target'].to_numpy(dtype=float))):.4f}",
        "",
        "## Residual Quantiles",
        "",
        residual_df["residual_target"].quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]).round(4).to_frame("residual_target").to_markdown(),
        "",
        "## Worst Wells By Residual RMSE",
        "",
        by_well.head(15).round(4).to_markdown(index=False),
    ]
    (REPORT_DIR / "residual_target_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def build_split(split: str, data_dir: Path, limit_wells: int | None) -> None:
    feature_rows = []
    residual_rows = []
    prediction_rows = []
    for path in iter_wells(data_dir, limit_wells):
        well = path.name.split("__")[0]
        df = pd.read_csv(path)
        frame, residual = build_frame(df, split, well)
        feature_rows.append(frame)
        residual_rows.append(residual)
        prediction_rows.append(frame[["id", "well", "row", "baseline_tvt"]].copy())

    if feature_rows:
        baseline_features = pd.concat(feature_rows, ignore_index=True)
        baseline_features.to_csv(FEATURE_DIR / f"baseline_features_{split}.csv", index=False)

    if residual_rows and split == "train":
        residual_df = pd.concat(residual_rows, ignore_index=True)
        residual_df.to_csv(FEATURE_DIR / "residual_targets.csv", index=False)
        residual_df[["id", "baseline_tvt", "truth_tvt", "residual_target"]].to_csv(
            OUTPUT_DIR / "baseline_predictions_train_hidden.csv", index=False
        )

    if prediction_rows and split == "test":
        pd.concat(prediction_rows, ignore_index=True).to_csv(OUTPUT_DIR / "baseline_predictions_test.csv", index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build baseline feature tables for residual modeling.")
    parser.add_argument("--limit-wells", type=int, default=None, help="Limit the number of wells per split for smoke tests.")
    args = parser.parse_args()

    reset_outputs()

    # Touch sample submission so this script fails fast when the competition bundle is incomplete.
    _ = load_sample_submission()

    build_split("train", resolve_train_dir(), args.limit_wells)
    build_split("test", resolve_test_dir(), args.limit_wells)
    if (FEATURE_DIR / "residual_targets.csv").exists():
        write_residual_report(pd.read_csv(FEATURE_DIR / "residual_targets.csv"))
    print(f"Wrote baseline features to {FEATURE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
