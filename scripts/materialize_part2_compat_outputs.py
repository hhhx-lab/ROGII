#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from rogii_utils import DATA_VERSION_PATH, OUTPUT_DIR, REPORT_DIR, ROOT, regression_metrics


FEATURE_DIR = ROOT / "features"
MODEL_DIR = ROOT / "models"
SUBMISSION_DIR = ROOT / "submissions"

BASELINE_FEATURE_COLS = [
    "id",
    "well",
    "row",
    "target_rows",
    "gr_missing_rate",
    "baseline_confidence",
    "distance_from_last_known_row",
]
GEOMETRY_FEATURE_COLS = [
    "id",
    "well",
    "row",
    "row_position",
    "MD_norm",
    "Z_centered",
    "dZ_dMD",
    "trajectory_speed_proxy",
    "trajectory_curvature_proxy",
    "path_length_norm",
    "well_target_rows",
    "well_gr_missing_rate",
    "curvature_roll_mean_25",
    "curvature_roll_std_25",
    "speed_roll_mean_25",
    "speed_roll_std_25",
]
RESIDUAL_TARGET_COLS = ["id", "well", "row", "residual_target"]


def data_version() -> dict[str, object]:
    return json.loads(DATA_VERSION_PATH.read_text()) if DATA_VERSION_PATH.exists() else {}


def data_hash_short() -> str:
    value = str(data_version().get("zip_sha256") or "unknown")
    return value[:12] if value != "unknown" else value


def write_parquet_subset(csv_name: str, parquet_name: str, columns: list[str]) -> None:
    csv_path = FEATURE_DIR / csv_name
    parquet_path = FEATURE_DIR / parquet_name
    if not csv_path.exists():
        raise FileNotFoundError(csv_path)
    existing_cols = pd.read_csv(csv_path, nrows=0).columns.tolist()
    keep = [col for col in columns if col in existing_cols]
    frame = pd.read_csv(csv_path, usecols=keep, low_memory=False)
    rename = {
        "target_rows": "target_rows_count",
        "gr_missing_rate": "target_gr_missing_rate",
        "distance_from_last_known_row": "distance_row_from_last_known",
    }
    frame = frame.rename(columns={src: dst for src, dst in rename.items() if src in frame.columns})
    parquet_path.parent.mkdir(exist_ok=True)
    frame.to_parquet(parquet_path, index=False)
    print(f"Wrote {parquet_path.relative_to(ROOT)} rows={len(frame)} cols={len(frame.columns)}")


def load_model_config() -> dict[str, object]:
    path = MODEL_DIR / "residual_geometry_hgb_config.json"
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def write_standard_model_artifacts() -> None:
    source_config = load_model_config()
    features = list(source_config.get("features", []))
    metrics = dict(source_config.get("metrics", {}))
    params = dict(source_config.get("params", {}))

    standard = {
        "model_class": "SGDRegressorPipeline",
        "model_name": "geometry",
        "data_hash": data_hash_short(),
        "feature_columns": features,
        "selected_alpha": 1.0,
        "train_rows_per_well": source_config.get("max_rows_per_well"),
        "max_rows_per_well": source_config.get("max_rows_per_well"),
        "params": params,
        "metrics": metrics,
        "random_seed": 42,
        "residual_clip_config": {"clip_abs": 1.0e9},
        "source_config": "models/residual_geometry_hgb_config.json",
    }
    (MODEL_DIR / "residual_geometry_config.json").write_text(
        json.dumps(standard, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (MODEL_DIR / "residual_geometry_feature_list.txt").write_text(
        "\n".join(features) + "\n",
        encoding="utf-8",
    )
    print("Wrote standard Part 2 model config and feature list")


def normalize_oof() -> pd.DataFrame:
    path = OUTPUT_DIR / "residual_geometry_oof.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    oof = pd.read_csv(path)
    if "true_tvt" not in oof.columns and "truth_tvt" in oof.columns:
        oof["true_tvt"] = oof["truth_tvt"]
    if "geometry_pred_tvt" not in oof.columns and "final_pred" in oof.columns:
        oof["geometry_pred_tvt"] = oof["final_pred"]
    if "residual_pred_raw" not in oof.columns and "oof_residual_pred" in oof.columns:
        oof["residual_pred_raw"] = oof["oof_residual_pred"]
    if "residual_pred_clipped" not in oof.columns:
        oof["residual_pred_clipped"] = oof["residual_pred_raw"]
    if "selected_alpha" not in oof.columns:
        oof["selected_alpha"] = 1.0
    if "baseline_error" not in oof.columns:
        oof["baseline_error"] = oof["baseline_tvt"] - oof["true_tvt"]
    if "geometry_error" not in oof.columns:
        oof["geometry_error"] = oof["geometry_pred_tvt"] - oof["true_tvt"]
    ordered = [
        "well",
        "split",
        "row",
        "id",
        "true_tvt",
        "baseline_tvt",
        "residual_target",
        "residual_pred_raw",
        "residual_pred_clipped",
        "selected_alpha",
        "geometry_pred_tvt",
        "baseline_error",
        "geometry_error",
        "abs_error",
    ]
    keep = [col for col in ordered if col in oof.columns] + [col for col in oof.columns if col not in ordered]
    oof = oof[keep]
    oof.to_csv(path, index=False)
    print(f"Normalized {path.relative_to(ROOT)}")
    return oof


def write_alpha_search(oof: pd.DataFrame) -> None:
    truth = oof["true_tvt"].to_numpy(dtype=float)
    baseline = oof["baseline_tvt"].to_numpy(dtype=float)
    residual = oof["residual_pred_clipped"].to_numpy(dtype=float)
    rows = []
    for alpha in [0.0, 0.25, 0.5, 0.75, 1.0]:
        rows.append({"alpha": alpha, **regression_metrics(truth, baseline + alpha * residual)})
    pd.DataFrame(rows).sort_values("rmse").to_csv(OUTPUT_DIR / "residual_geometry_alpha_search.csv", index=False)
    print("Wrote outputs/residual_geometry_alpha_search.csv")


def write_feature_importance_markdown() -> None:
    csv_path = REPORT_DIR / "residual_geometry_hgb_feature_importance.csv"
    md_path = REPORT_DIR / "residual_geometry_feature_importance.md"
    if csv_path.exists():
        importance = pd.read_csv(csv_path)
    else:
        importance = pd.DataFrame(columns=["feature", "importance"])
    lines = [
        "# Residual Geometry Feature Importance",
        "",
        "This report mirrors the current lightweight geometry residual model diagnostics.",
        "",
        importance.head(50).round(6).to_markdown(index=False) if len(importance) else "_No feature importance available._",
        "",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {md_path.relative_to(ROOT)}")


def main() -> int:
    FEATURE_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    SUBMISSION_DIR.mkdir(exist_ok=True)

    write_parquet_subset("baseline_features_train.csv", "baseline_features_train.parquet", BASELINE_FEATURE_COLS)
    write_parquet_subset("baseline_features_test.csv", "baseline_features_test.parquet", BASELINE_FEATURE_COLS)
    write_parquet_subset("geometry_features_train.csv", "geometry_features_train.parquet", GEOMETRY_FEATURE_COLS)
    write_parquet_subset("geometry_features_test.csv", "geometry_features_test.parquet", GEOMETRY_FEATURE_COLS)
    write_parquet_subset("residual_targets.csv", "residual_targets.parquet", RESIDUAL_TARGET_COLS)
    write_standard_model_artifacts()
    oof = normalize_oof()
    write_alpha_search(oof)
    write_feature_importance_markdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
