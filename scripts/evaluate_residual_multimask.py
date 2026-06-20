#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from build_baseline_features import build_rows
from build_geometry_features import full_well_geometry, well_level_features
from part2_utils import (
    ALPHA_GRID,
    MODEL_DIR,
    OUTPUT_DIR,
    PART2_SEED,
    REPORT_DIR,
    data_hash_short,
    ensure_part2_dirs,
    env_int,
    feature_columns_from,
    sample_training_rows,
)
from rogii_utils import TRAIN_DIR, assert_data_contract_ready, apply_cv_split_mask, regression_metrics, split_target_rows
from train_residual_model import fit_model, model_params


CV_SPLITS_PATH = OUTPUT_DIR / "cv_splits.csv"
CONFIG_PATH = MODEL_DIR / "residual_geometry_config.json"
BY_SPLIT_PATH = OUTPUT_DIR / "residual_geometry_multimask_by_split.csv"
OVERALL_PATH = OUTPUT_DIR / "residual_geometry_multimask_overall.csv"
REPORT_PATH = REPORT_DIR / "residual_geometry_multimask_report.md"

DEFAULT_MASK_TYPES = [
    "original_hidden",
    "trailing_short",
    "trailing_long",
    "mid_contiguous",
    "random_contiguous",
]


def selected_mask_types() -> list[str]:
    value = ",".join(DEFAULT_MASK_TYPES)
    env_value = __import__("os").environ.get("ROGII_PART2_MULTIMASK_TYPES", value)
    masks = [part.strip() for part in env_value.split(",") if part.strip()]
    return masks or DEFAULT_MASK_TYPES


def add_split_key_columns(frame: pd.DataFrame, split: pd.Series, target_rows: np.ndarray) -> pd.DataFrame:
    out = frame.copy()
    out.insert(0, "id", [f"{split['well']}_{int(row)}" for row in target_rows])
    out.insert(0, "row", target_rows.astype(np.int32))
    out.insert(0, "well", str(split["well"]))
    out.insert(0, "split_id", str(split["split_id"]))
    return out


def geometry_for_split(df: pd.DataFrame, split: pd.Series, target_rows: np.ndarray) -> pd.DataFrame:
    full = full_well_geometry(df)
    target = full.iloc[target_rows].reset_index(drop=True)
    for col, value in well_level_features(df, target_rows).items():
        target[col] = np.float32(value)
    return add_split_key_columns(target, split, target_rows)


def build_mask_frame(splits: pd.DataFrame, mask_type: str) -> tuple[pd.DataFrame, list[str]]:
    baseline_parts = []
    geometry_parts = []
    target_parts = []
    for split in splits[splits["mask_type"].eq(mask_type)].itertuples(index=False):
        split_s = pd.Series(split._asdict())
        well = str(split_s["well"])
        df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
        masked = apply_cv_split_mask(df, split_s, replace_tvt_input=True)
        target_rows = split_target_rows(split_s)

        baseline, targets = build_rows(masked, well, target_rows, truth_available=True)
        baseline["split_id"] = str(split_s["split_id"])
        baseline["mask_type"] = mask_type
        targets["split_id"] = str(split_s["split_id"])
        targets["mask_type"] = mask_type
        geometry = geometry_for_split(masked, split_s, target_rows)
        geometry["mask_type"] = mask_type

        baseline_parts.append(baseline)
        geometry_parts.append(geometry)
        target_parts.append(targets)

    baseline = pd.concat(baseline_parts, ignore_index=True)
    geometry = pd.concat(geometry_parts, ignore_index=True)
    targets = pd.concat(target_parts, ignore_index=True)
    if not (baseline["id"].equals(geometry["id"]) and baseline["id"].equals(targets["id"])):
        raise ValueError(f"feature keys are not aligned for mask_type={mask_type}")

    baseline_features = feature_columns_from(baseline)
    geometry_features = feature_columns_from(geometry)
    feature_columns = baseline_features + geometry_features
    frame = pd.concat(
        [
            baseline[["split_id", "mask_type", "well", "row", "id", "baseline_tvt"]],
            baseline[baseline_features],
            geometry[geometry_features],
            targets[["true_tvt", "residual_target"]],
        ],
        axis=1,
    )
    return frame, feature_columns


def alpha_metrics(frame: pd.DataFrame, residual_pred: np.ndarray, residual_clip_abs: float) -> pd.DataFrame:
    clipped = np.clip(residual_pred, -residual_clip_abs, residual_clip_abs)
    truth = frame["true_tvt"].to_numpy(dtype=float)
    baseline = frame["baseline_tvt"].to_numpy(dtype=float)
    rows = []
    for alpha in ALPHA_GRID:
        rows.append({"alpha": alpha, **regression_metrics(truth, baseline + alpha * clipped)})
    return pd.DataFrame(rows).sort_values("rmse")


def split_metrics(eval_frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for split_id, part in eval_frame.groupby("split_id", sort=True):
        truth = part["true_tvt"].to_numpy(dtype=float)
        baseline = part["baseline_tvt"].to_numpy(dtype=float)
        geometry = part["geometry_pred_tvt"].to_numpy(dtype=float)
        baseline_metrics = regression_metrics(truth, baseline)
        geometry_metrics = regression_metrics(truth, geometry)
        rows.append(
            {
                "split_id": split_id,
                "well": part["well"].iloc[0],
                "mask_type": part["mask_type"].iloc[0],
                "target_rows": len(part),
                "baseline_rmse": baseline_metrics["rmse"],
                "geometry_rmse": geometry_metrics["rmse"],
                "rmse_improvement": baseline_metrics["rmse"] - geometry_metrics["rmse"],
                "baseline_mae": baseline_metrics["mae"],
                "geometry_mae": geometry_metrics["mae"],
                "baseline_p95_abs_error": baseline_metrics["p95_abs_error"],
                "geometry_p95_abs_error": geometry_metrics["p95_abs_error"],
                "baseline_bias": baseline_metrics["bias"],
                "geometry_bias": geometry_metrics["bias"],
            }
        )
    out = pd.DataFrame(rows)
    out["improved"] = out["rmse_improvement"] > 0
    return out


def evaluate_mask(mask_type: str, splits: pd.DataFrame, selected_alpha: float, params: dict[str, object], rows_per_well: int, n_splits: int) -> tuple[pd.DataFrame, dict[str, object]]:
    frame, feature_columns = build_mask_frame(splits, mask_type)
    groups = frame["well"].astype(str)
    residual_target = frame["residual_target"].astype(float)
    residual_clip_abs = float(np.quantile(np.abs(residual_target), 0.995))
    oof_pred = np.zeros(len(frame), dtype=np.float32)

    splitter = GroupKFold(n_splits=n_splits)
    fold_rows = []
    for fold, (train_idx, valid_idx) in enumerate(splitter.split(frame[feature_columns], residual_target, groups), start=1):
        fold_train_rel = sample_training_rows(frame.iloc[train_idx], groups.iloc[train_idx], rows_per_well, PART2_SEED + fold + len(mask_type))
        fold_train_idx = train_idx[fold_train_rel]
        model = fit_model(frame.iloc[fold_train_idx][feature_columns], residual_target.iloc[fold_train_idx], params)
        oof_pred[valid_idx] = model.predict(frame.iloc[valid_idx][feature_columns]).astype(np.float32)
        fold_rows.append({"fold": fold, "train_rows_used": int(len(fold_train_idx)), "valid_rows": int(len(valid_idx))})
        print(f"mask_type={mask_type} fold={fold} train_rows_used={len(fold_train_idx)} valid_rows={len(valid_idx)}")

    alpha_table = alpha_metrics(frame, oof_pred, residual_clip_abs)
    best_alpha = float(alpha_table.iloc[0]["alpha"])
    residual_pred_clipped = np.clip(oof_pred, -residual_clip_abs, residual_clip_abs)
    geometry_pred = frame["baseline_tvt"].to_numpy(dtype=float) + selected_alpha * residual_pred_clipped
    eval_frame = frame[["split_id", "mask_type", "well", "row", "id", "baseline_tvt", "true_tvt"]].copy()
    eval_frame["residual_pred_clipped"] = residual_pred_clipped.astype("float32")
    eval_frame["selected_alpha"] = np.float32(selected_alpha)
    eval_frame["geometry_pred_tvt"] = geometry_pred.astype("float32")

    by_split = split_metrics(eval_frame)
    truth = eval_frame["true_tvt"].to_numpy(dtype=float)
    baseline = eval_frame["baseline_tvt"].to_numpy(dtype=float)
    geometry = eval_frame["geometry_pred_tvt"].to_numpy(dtype=float)
    baseline_overall = regression_metrics(truth, baseline)
    geometry_overall = regression_metrics(truth, geometry)
    overall = {
        "mask_type": mask_type,
        "splits": int(by_split["split_id"].nunique()),
        "wells": int(by_split["well"].nunique()),
        "target_rows": int(len(eval_frame)),
        "selected_alpha": selected_alpha,
        "best_alpha_on_mask": best_alpha,
        "baseline_rmse": baseline_overall["rmse"],
        "geometry_rmse": geometry_overall["rmse"],
        "rmse_improvement": baseline_overall["rmse"] - geometry_overall["rmse"],
        "baseline_mae": baseline_overall["mae"],
        "geometry_mae": geometry_overall["mae"],
        "baseline_p95_abs_error": baseline_overall["p95_abs_error"],
        "geometry_p95_abs_error": geometry_overall["p95_abs_error"],
        "improved_splits": int(by_split["improved"].sum()),
        "degraded_splits": int((~by_split["improved"]).sum()),
        "mean_split_rmse_improvement": float(by_split["rmse_improvement"].mean()),
        "median_split_rmse_improvement": float(by_split["rmse_improvement"].median()),
        "worst_split_degradation": float(by_split["rmse_improvement"].min()),
        "best_split_improvement": float(by_split["rmse_improvement"].max()),
        "residual_clip_abs": residual_clip_abs,
        "fold_rows": fold_rows,
    }
    return by_split, overall


def main() -> int:
    ensure_part2_dirs()
    assert_data_contract_ready()
    if not CV_SPLITS_PATH.exists():
        raise FileNotFoundError("outputs/cv_splits.csv is missing; run scripts/make_cv_splits.py first")
    config = json.loads(CONFIG_PATH.read_text())
    selected_alpha = float(config["selected_alpha"])
    rows_per_well = env_int("ROGII_PART2_MULTIMASK_TRAIN_ROWS_PER_WELL", 300)
    n_splits = env_int("ROGII_PART2_MULTIMASK_N_SPLITS", 5)
    params = model_params()
    params["max_iter"] = env_int("ROGII_PART2_MULTIMASK_MAX_ITER", min(int(params["max_iter"]), 160))

    splits = pd.read_csv(CV_SPLITS_PATH)
    masks = selected_mask_types()
    missing = sorted(set(masks) - set(splits["mask_type"]))
    if missing:
        raise ValueError(f"requested mask types are missing from cv_splits.csv: {missing}")

    all_by_split = []
    overall_rows = []
    data_hash = data_hash_short()
    for mask_type in masks:
        by_split, overall = evaluate_mask(mask_type, splits, selected_alpha, params, rows_per_well, n_splits)
        by_split.insert(0, "data_hash", data_hash)
        overall["data_hash"] = data_hash
        all_by_split.append(by_split)
        overall_rows.append(overall)

    by_split_out = pd.concat(all_by_split, ignore_index=True)
    overall_out = pd.DataFrame(overall_rows)
    by_split_out.to_csv(BY_SPLIT_PATH, index=False)
    overall_out.drop(columns=["fold_rows"]).to_csv(OVERALL_PATH, index=False)

    lines = [
        "# Residual Geometry Multi-Mask Validation",
        "",
        f"- Data hash: `{data_hash}`",
        f"- Mask types: `{', '.join(masks)}`",
        f"- Grouping: `GroupKFold by well`",
        f"- Selected alpha from original hidden run: `{selected_alpha}`",
        f"- Train rows per well cap: `{rows_per_well}`",
        f"- HGB max_iter: `{params['max_iter']}`",
        "",
        "## Overall by Mask",
        "",
        overall_out.drop(columns=["fold_rows"]).round(4).to_markdown(index=False),
        "",
        "## Worst Splits Across Masks",
        "",
        by_split_out.sort_values("rmse_improvement").head(20).round(4).to_markdown(index=False),
        "",
        "## Best Splits Across Masks",
        "",
        by_split_out.sort_values("rmse_improvement", ascending=False).head(20).round(4).to_markdown(index=False),
        "",
        "## Engineering Interpretation",
        "",
        "- This run recomputes TVT-dependent baseline features under each synthetic mask and keeps validation wells disjoint from training wells.",
        "- The local defaults are intentionally lighter than server full-row training; use `ROGII_PART2_MULTIMASK_TRAIN_ROWS_PER_WELL=0` and a larger `ROGII_PART2_MULTIMASK_MAX_ITER` on a server.",
        "- A weak or negative mask result should not block Part 3; it identifies which hidden interval regimes need GR/typewell alignment or conservative blending.",
        "",
        "## Outputs",
        "",
        f"- By split: `{BY_SPLIT_PATH.relative_to(BY_SPLIT_PATH.parents[1])}`",
        f"- Overall: `{OVERALL_PATH.relative_to(OVERALL_PATH.parents[1])}`",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))
    print(f"Wrote {BY_SPLIT_PATH}")
    print(f"Wrote {OVERALL_PATH}")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
