#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

from part2_utils import (
    ALPHA_GRID,
    BASELINE_NAME,
    FEATURE_DIR,
    FEATURE_VERSION,
    MODEL_DIR,
    OUTPUT_DIR,
    PART2_SEED,
    data_hash_short,
    ensure_part2_dirs,
    env_float,
    env_int,
    feature_columns_from,
    sample_training_rows,
)
from rogii_utils import ROOT, SUBMISSION_DIR, assert_data_contract_ready, regression_metrics


BASELINE_TRAIN_PATH = FEATURE_DIR / "baseline_features_train.parquet"
BASELINE_TEST_PATH = FEATURE_DIR / "baseline_features_test.parquet"
GEOMETRY_TRAIN_PATH = FEATURE_DIR / "geometry_features_train.parquet"
GEOMETRY_TEST_PATH = FEATURE_DIR / "geometry_features_test.parquet"
TARGET_PATH = FEATURE_DIR / "residual_targets.parquet"

OOF_PATH = OUTPUT_DIR / "residual_geometry_oof.csv"
TEST_PRED_PATH = OUTPUT_DIR / "residual_geometry_test_predictions.csv"
ALPHA_PATH = OUTPUT_DIR / "residual_geometry_alpha_search.csv"
MODEL_PATH = MODEL_DIR / "residual_geometry_hgb.pkl"
CONFIG_PATH = MODEL_DIR / "residual_geometry_config.json"
FEATURE_LIST_PATH = MODEL_DIR / "residual_geometry_feature_list.txt"
SUBMISSION_PATH = SUBMISSION_DIR / "geometry_residual_submission.csv"
SERVER_RUNBOOK_PATH = ROOT / "reports" / "residual_geometry_server_runbook.md"


def load_train_frame() -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    baseline = pd.read_parquet(BASELINE_TRAIN_PATH)
    geometry = pd.read_parquet(GEOMETRY_TRAIN_PATH)
    targets = pd.read_parquet(TARGET_PATH)
    if not (baseline["id"].equals(geometry["id"]) and baseline["id"].equals(targets["id"])):
        raise ValueError("train feature keys are not aligned; rebuild Part 2 features")

    baseline_features = feature_columns_from(baseline)
    geometry_features = feature_columns_from(geometry)
    frame = pd.concat(
        [
            baseline[["split_id", "well", "row", "id", "baseline_tvt"]],
            baseline[baseline_features],
            geometry[geometry_features],
            targets[["true_tvt", "residual_target"]],
        ],
        axis=1,
    )
    feature_columns = baseline_features + geometry_features
    return frame, targets, feature_columns


def load_test_frame(feature_columns: list[str]) -> pd.DataFrame:
    baseline = pd.read_parquet(BASELINE_TEST_PATH)
    geometry = pd.read_parquet(GEOMETRY_TEST_PATH)
    if not baseline["id"].equals(geometry["id"]):
        raise ValueError("test feature keys are not aligned; rebuild Part 2 features")
    frame = pd.concat(
        [
            baseline[["split_id", "well", "row", "id", "baseline_tvt"]],
            baseline[[col for col in feature_columns if col in baseline.columns]],
            geometry[[col for col in feature_columns if col in geometry.columns]],
        ],
        axis=1,
    )
    missing = [col for col in feature_columns if col not in frame.columns]
    if missing:
        raise ValueError(f"test frame missing feature columns: {missing[:10]}")
    return frame[["split_id", "well", "row", "id", "baseline_tvt", *feature_columns]]


def model_params() -> dict[str, object]:
    return {
        "learning_rate": env_float("ROGII_PART2_LEARNING_RATE", 0.05),
        "max_iter": env_int("ROGII_PART2_MAX_ITER", 220),
        "max_leaf_nodes": env_int("ROGII_PART2_MAX_LEAF_NODES", 31),
        "l2_regularization": env_float("ROGII_PART2_L2", 0.05),
        "min_samples_leaf": env_int("ROGII_PART2_MIN_SAMPLES_LEAF", 50),
        "random_state": PART2_SEED,
    }


def fit_model(x: pd.DataFrame, y: pd.Series, params: dict[str, object]) -> HistGradientBoostingRegressor:
    model = HistGradientBoostingRegressor(**params)
    model.fit(x, y)
    return model


def alpha_search(frame: pd.DataFrame, residual_pred: np.ndarray, residual_clip_abs: float) -> pd.DataFrame:
    clipped = np.clip(residual_pred, -residual_clip_abs, residual_clip_abs)
    truth = frame["true_tvt"].to_numpy(dtype=float)
    baseline = frame["baseline_tvt"].to_numpy(dtype=float)
    rows = []
    for alpha in ALPHA_GRID:
        pred = baseline + alpha * clipped
        metrics = regression_metrics(truth, pred)
        rows.append({"alpha": alpha, **metrics})
    return pd.DataFrame(rows).sort_values("rmse")


def main() -> int:
    ensure_part2_dirs()
    data_version = assert_data_contract_ready()
    data_hash = data_hash_short()

    train_rows_per_well = env_int("ROGII_PART2_TRAIN_ROWS_PER_WELL", 600)
    n_splits = env_int("ROGII_PART2_N_SPLITS", 5)
    residual_clip_quantile = env_float("ROGII_PART2_RESIDUAL_CLIP_QUANTILE", 0.995)
    params = model_params()

    frame, _, feature_columns = load_train_frame()
    groups = frame["well"].astype(str)
    residual_target = frame["residual_target"].astype(float)
    residual_clip_abs = float(np.quantile(np.abs(residual_target), residual_clip_quantile))
    oof_pred = np.zeros(len(frame), dtype=np.float32)

    splitter = GroupKFold(n_splits=n_splits)
    fold_rows = []
    for fold, (train_idx, valid_idx) in enumerate(splitter.split(frame[feature_columns], residual_target, groups), start=1):
        train_groups = groups.iloc[train_idx]
        fold_train_rel = sample_training_rows(frame.iloc[train_idx], train_groups, train_rows_per_well, PART2_SEED + fold)
        fold_train_idx = train_idx[fold_train_rel]
        model = fit_model(frame.iloc[fold_train_idx][feature_columns], residual_target.iloc[fold_train_idx], params)
        oof_pred[valid_idx] = model.predict(frame.iloc[valid_idx][feature_columns]).astype(np.float32)
        fold_rows.append(
            {
                "fold": fold,
                "train_wells": int(groups.iloc[train_idx].nunique()),
                "valid_wells": int(groups.iloc[valid_idx].nunique()),
                "train_rows_used": int(len(fold_train_idx)),
                "valid_rows_predicted": int(len(valid_idx)),
            }
        )
        print(f"fold={fold} train_rows_used={len(fold_train_idx)} valid_rows={len(valid_idx)}")

    alpha_results = alpha_search(frame, oof_pred, residual_clip_abs)
    alpha_results.to_csv(ALPHA_PATH, index=False)
    selected_alpha = float(alpha_results.iloc[0]["alpha"])
    residual_pred_clipped = np.clip(oof_pred, -residual_clip_abs, residual_clip_abs)
    geometry_pred = frame["baseline_tvt"].to_numpy(dtype=float) + selected_alpha * residual_pred_clipped

    oof = pd.DataFrame(
        {
            "data_hash": data_hash,
            "split_id": frame["split_id"],
            "well": frame["well"],
            "row": frame["row"].astype(np.int32),
            "id": frame["id"],
            "baseline_tvt": frame["baseline_tvt"].astype("float32"),
            "true_tvt": frame["true_tvt"].astype("float32"),
            "residual_target": frame["residual_target"].astype("float32"),
            "residual_pred_raw": oof_pred.astype("float32"),
            "residual_pred_clipped": residual_pred_clipped.astype("float32"),
            "selected_alpha": np.float32(selected_alpha),
            "geometry_pred_tvt": geometry_pred.astype("float32"),
            "baseline_error": (frame["baseline_tvt"].to_numpy(dtype=float) - frame["true_tvt"].to_numpy(dtype=float)).astype("float32"),
            "geometry_error": (geometry_pred - frame["true_tvt"].to_numpy(dtype=float)).astype("float32"),
        }
    )
    oof.to_csv(OOF_PATH, index=False)

    final_train_idx = sample_training_rows(frame, groups, train_rows_per_well, PART2_SEED + 999)
    final_model = fit_model(frame.iloc[final_train_idx][feature_columns], residual_target.iloc[final_train_idx], params)
    joblib.dump(final_model, MODEL_PATH)
    FEATURE_LIST_PATH.write_text("\n".join(feature_columns) + "\n")

    test = load_test_frame(feature_columns)
    test_raw = final_model.predict(test[feature_columns]).astype(np.float32)
    test_clipped = np.clip(test_raw, -residual_clip_abs, residual_clip_abs)
    test_geometry = test["baseline_tvt"].to_numpy(dtype=float) + selected_alpha * test_clipped
    test_pred = pd.DataFrame(
        {
            "data_hash": data_hash,
            "split_id": test["split_id"],
            "well": test["well"],
            "row": test["row"].astype(np.int32),
            "id": test["id"],
            "baseline_tvt": test["baseline_tvt"].astype("float32"),
            "residual_pred_raw": test_raw.astype("float32"),
            "residual_pred_clipped": test_clipped.astype("float32"),
            "selected_alpha": np.float32(selected_alpha),
            "geometry_pred_tvt": test_geometry.astype("float32"),
        }
    )
    test_pred.to_csv(TEST_PRED_PATH, index=False)
    test_pred[["id", "geometry_pred_tvt"]].rename(columns={"geometry_pred_tvt": "tvt"}).to_csv(SUBMISSION_PATH, index=False)

    config = {
        "run_id": "residual_geometry_hgb_v1",
        "data_version": data_version,
        "data_hash": data_hash,
        "feature_version": FEATURE_VERSION,
        "split_version": "GroupKFold_well_original_hidden_v1",
        "model_class": "sklearn.ensemble.HistGradientBoostingRegressor",
        "params": params,
        "random_seed": PART2_SEED,
        "feature_columns": feature_columns,
        "target_definition": f"residual_target = true_TVT - {BASELINE_NAME}_prediction",
        "sample_weight_mode": "row_weighted_training_with_per_well_row_cap",
        "train_rows_per_well": train_rows_per_well,
        "n_splits": n_splits,
        "residual_clip_config": {
            "clip_abs": residual_clip_abs,
            "source": f"abs residual quantile {residual_clip_quantile}",
        },
        "selected_alpha": selected_alpha,
        "alpha_grid": ALPHA_GRID,
        "fold_rows": fold_rows,
        "local_or_server": "local_sampled" if train_rows_per_well > 0 else "server_full_or_uncapped",
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n")

    SERVER_RUNBOOK_PATH.write_text(
        "\n".join(
            [
                "# Residual Geometry Server Runbook",
                "",
                "The local Part 2 run is intentionally reproducible and can be scaled on a larger machine without changing code.",
                "",
                "## Full-Row Training",
                "",
                "```bash",
                ".venv/bin/python scripts/build_baseline_features.py",
                ".venv/bin/python scripts/build_geometry_features.py",
                "ROGII_PART2_TRAIN_ROWS_PER_WELL=0 \\",
                "ROGII_PART2_MAX_ITER=500 \\",
                ".venv/bin/python scripts/train_residual_model.py",
                ".venv/bin/python scripts/evaluate_model_cv.py",
                "ROGII_PART2_MULTIMASK_TRAIN_ROWS_PER_WELL=0 \\",
                "ROGII_PART2_MULTIMASK_MAX_ITER=500 \\",
                ".venv/bin/python scripts/evaluate_residual_multimask.py",
                ".venv/bin/python scripts/validate_part2_outputs.py",
                "```",
                "",
                "## Local Default",
                "",
                f"- `ROGII_PART2_TRAIN_ROWS_PER_WELL={train_rows_per_well}`",
                f"- selected alpha: `{selected_alpha}`",
                f"- residual clip abs: `{residual_clip_abs:.4f}`",
                "- local multi-mask validation defaults are lighter than full-row server training and are controlled by `ROGII_PART2_MULTIMASK_*` environment variables.",
                "",
                "All generated `features/` and `outputs/` artifacts are reproducible from scripts and should be regenerated on the server after syncing `data/raw/`.",
                "",
            ]
        )
    )

    print(f"Wrote {OOF_PATH}")
    print(f"Wrote {TEST_PRED_PATH}")
    print(f"Wrote {SUBMISSION_PATH}")
    print(f"Wrote {MODEL_PATH}")
    print(f"Wrote {CONFIG_PATH}")
    print(f"selected_alpha={selected_alpha} train_rows={len(frame)} test_rows={len(test)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
