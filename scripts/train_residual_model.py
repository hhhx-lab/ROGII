#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import SGDRegressor
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "features"
OUTPUT_DIR = ROOT / "outputs"
MODEL_DIR = ROOT / "models"
REPORT_DIR = ROOT / "reports"
SUBMISSION_DIR = ROOT / "submissions"


BASELINE_META_COLS = ["well", "split", "row", "id"]
RESIDUAL_META_COLS = ["well", "split", "row", "id", "truth_tvt", "baseline_tvt", "residual_target"]
LEFTOVER_META_COLS = [
    "well",
    "split",
    "row",
    "id",
    "truth_tvt",
    "baseline_tvt",
    "residual_target",
    "geometry_oof_residual",
    "leftover_target",
    "abs_geometry_residual",
]
PART3_WELL_COLS = [
    "gr_quality_score",
    "typewell_quality_score",
    "risk_score",
    "baseline_confidence",
    "route_suggestion",
]
DIAGNOSTICS_PATH = OUTPUT_DIR / "part3_diagnostics.csv"
GEOMETRY_OOF_PATH = OUTPUT_DIR / "residual_geometry_oof.csv"
GEOMETRY_TEST_PATH = OUTPUT_DIR / "residual_geometry_test_predictions.csv"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    feature_files: list[str]
    feature_cols: list[str]
    output_oof: str
    output_cv: str
    output_test: str
    output_report: str
    output_submission: str
    model_dir_name: str
    max_rows_per_well: int = 0
    model_family: str = "sgd"
    output_model: str | None = None
    output_config: str | None = None
    output_feature_list: str | None = None
    target_csv: str = "residual_targets.csv"
    target_col: str = "residual_target"
    stack_geometry_correction: bool = False
    merge_well_diagnostics: bool = False


SPECS: dict[str, ModelSpec] = {
    "geometry": ModelSpec(
        name="geometry",
        feature_files=["baseline_features_{split}.csv", "geometry_features_{split}.csv"],
        feature_cols=[
            "baseline_tvt",
            "known_rows",
            "target_rows",
            "known_ratio",
            "target_ratio",
            "last_known_row",
            "distance_from_last_known_row",
            "baseline_slope_median",
            "baseline_slope_std",
            "baseline_confidence",
            "gr_missing_rate",
            "baseline_pred_delta_from_last_known",
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
        ],
        output_oof="residual_geometry_oof.csv",
        output_cv="residual_geometry_cv_by_well.csv",
        output_test="residual_geometry_test_predictions.csv",
        output_report="residual_geometry_cv_report.md",
        output_submission="geometry_residual_submission.csv",
        model_dir_name="residual_geometry_hgb",
    ),
    "gr": ModelSpec(
        name="gr",
        feature_files=["gr_features_{split}.csv"],
        feature_cols=[
            "baseline_tvt",
            "known_rows",
            "target_rows",
            "known_ratio",
            "target_ratio",
            "last_known_row",
            "distance_from_last_known_row",
            "baseline_slope_median",
            "baseline_slope_std",
            "baseline_confidence",
            "gr_missing_rate",
            "baseline_pred_delta_from_last_known",
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
            "GR",
            "GR_is_missing",
            "GR_filled_interpolate",
            "GR_global_median_fill",
            "GR_gradient",
            "GR_second_diff",
            "GR_abs_gradient",
            "GR_trend_sign",
            "GR_local_zscore_25",
            "GR_peak_proxy_25",
            "GR_trough_proxy_25",
            "GR_volatility_25",
            "gr_quality_score",
            "GR_roll_mean_25",
            "GR_roll_std_25",
            "GR_roll_mean_50",
            "GR_roll_std_50",
            "GR_roll_missing_rate_25",
        ],
        output_oof="residual_gr_oof.csv",
        output_cv="residual_gr_cv_by_well.csv",
        output_test="residual_gr_test_predictions.csv",
        output_report="residual_gr_cv_report.md",
        output_submission="gr_residual_submission.csv",
        model_dir_name="residual_gr_hgb",
    ),
    "typewell": ModelSpec(
        name="typewell",
        feature_files=["gr_features_{split}.csv", "typewell_features_{split}.csv", "alignment_features_{split}.csv"],
        feature_cols=[
            "baseline_tvt",
            "known_rows",
            "target_rows",
            "known_ratio",
            "target_ratio",
            "last_known_row",
            "distance_from_last_known_row",
            "baseline_slope_median",
            "baseline_slope_std",
            "baseline_confidence",
            "gr_missing_rate",
            "baseline_pred_delta_from_last_known",
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
            "GR",
            "GR_is_missing",
            "GR_filled_interpolate",
            "GR_global_median_fill",
            "GR_gradient",
            "GR_second_diff",
            "GR_abs_gradient",
            "GR_trend_sign",
            "GR_local_zscore_25",
            "GR_peak_proxy_25",
            "GR_trough_proxy_25",
            "GR_volatility_25",
            "gr_quality_score",
            "GR_roll_mean_25",
            "GR_roll_std_25",
            "GR_roll_mean_50",
            "GR_roll_std_50",
            "GR_roll_missing_rate_25",
            "typewell_tvt_min",
            "typewell_tvt_max",
            "typewell_gr_mean",
            "typewell_gr_std",
            "typewell_gr_missing_rate",
            "typewell_gr_at_baseline",
            "typewell_interp_gradient",
            "typewell_out_of_range",
            "typewell_boundary_margin",
            "typewell_nearest_tvt_distance",
            "typewell_rows",
            "typewell_quality_score",
            "typewell_gr_window_mean_25",
            "typewell_gr_window_std_25",
            "typewell_gr_window_count_25",
            "typewell_gr_window_missing_rate_25",
            "alignment_window_index",
            "alignment_window_start_row",
            "alignment_window_end_row",
            "alignment_window_size",
            "alignment_window_gr_mean",
            "alignment_window_gr_std",
            "alignment_window_gr_missing_rate",
            "alignment_window_baseline_start",
            "alignment_window_baseline_end",
            "best_offset",
            "best_similarity",
            "second_best_similarity",
            "similarity_margin",
            "alignment_confidence",
            "alignment_enabled_flag",
            "alignment_support_fraction",
            "alignment_corr",
            "alignment_mae_norm",
            "alignment_gr",
        ],
        output_oof="residual_typewell_oof.csv",
        output_cv="residual_typewell_cv_by_well.csv",
        output_test="residual_typewell_test_predictions.csv",
        output_report="residual_typewell_cv_report.md",
        output_submission="typewell_residual_submission.csv",
        model_dir_name="residual_typewell_hgb",
    ),
}

SPECS["xgb"] = ModelSpec(
    name="xgb",
    feature_files=SPECS["geometry"].feature_files,
    feature_cols=SPECS["geometry"].feature_cols,
    output_oof="residual_xgb_oof.csv",
    output_cv="residual_xgb_cv_by_well.csv",
    output_test="residual_xgb_test_predictions.csv",
    output_report="residual_xgb_cv_report.md",
    output_submission="xgb_residual_submission.csv",
    model_dir_name="residual_xgb",
    max_rows_per_well=0,
    model_family="tree",
    output_model="residual_xgb_model.pkl",
    output_config="residual_xgb_config.json",
    output_feature_list="residual_xgb_feature_list.txt",
)

XGB_LEFTOVER_EXTRA_COLS = [
    "abs_geometry_residual",
    "alignment_confidence",
    "alignment_support_fraction",
    "alignment_enabled_flag",
    "gr_quality_score",
    "typewell_quality_score",
    "risk_score",
]

SPECS["xgb_leftover"] = ModelSpec(
    name="xgb_leftover",
    feature_files=[
        "baseline_features_{split}.csv",
        "geometry_features_{split}.csv",
        "alignment_features_{split}.csv",
    ],
    feature_cols=SPECS["geometry"].feature_cols + XGB_LEFTOVER_EXTRA_COLS,
    output_oof="residual_xgb_leftover_oof.csv",
    output_cv="residual_xgb_leftover_cv_by_well.csv",
    output_test="residual_xgb_leftover_test_predictions.csv",
    output_report="residual_xgb_leftover_cv_report.md",
    output_submission="xgb_leftover_submission.csv",
    model_dir_name="residual_xgb_leftover",
    max_rows_per_well=0,
    model_family="tree",
    output_model="residual_xgb_leftover_model.pkl",
    output_config="residual_xgb_leftover_config.json",
    output_feature_list="residual_xgb_leftover_feature_list.txt",
    target_csv="leftover_targets.csv",
    target_col="leftover_target",
    stack_geometry_correction=True,
    merge_well_diagnostics=True,
)


def load_csv(path: Path, usecols: list[str] | None = None, dtype: dict[str, str] | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, usecols=usecols, dtype=dtype, low_memory=False)
    for col in ("well", "split", "id"):
        if col in frame.columns:
            frame[col] = frame[col].astype("string")
    return frame


def merge_dedup(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    keys = {"well", "split", "row", "id"}
    keep = [c for c in right.columns if c in keys or c not in left.columns]
    right = right[keep]
    return left.merge(right, on=["well", "split", "row", "id"], how="left", validate="one_to_one")


def append_aligned(left: pd.DataFrame, right: pd.DataFrame) -> pd.DataFrame:
    join_keys = ["well", "split", "row", "id"]
    if len(left) != len(right):
        return merge_dedup(left, right)
    keep = [c for c in right.columns if c not in left.columns or c in join_keys]
    keep = [c for c in keep if c not in join_keys]
    return pd.concat([left.reset_index(drop=True), right[keep].reset_index(drop=True)], axis=1)


def load_feature_frame(path: Path, desired_cols: list[str], include_baseline_tvt: bool = False) -> pd.DataFrame:
    header = pd.read_csv(path, nrows=0).columns.tolist()
    keep = [c for c in BASELINE_META_COLS if c in header]
    keep += [
        c
        for c in desired_cols
        if c in header and c not in BASELINE_META_COLS and (include_baseline_tvt or c != "baseline_tvt")
    ]
    if include_baseline_tvt and "baseline_tvt" in header and "baseline_tvt" not in keep:
        keep.append("baseline_tvt")
    return load_csv(path, usecols=keep)


def load_part3_well_features() -> pd.DataFrame:
    if not DIAGNOSTICS_PATH.exists():
        return pd.DataFrame(columns=["well", *PART3_WELL_COLS])
    frame = pd.read_csv(DIAGNOSTICS_PATH, dtype={"well": "string"})
    if "split" in frame.columns:
        frame = frame[frame["split"].fillna("train").ne("test")].copy()
    keep = ["well"] + [col for col in PART3_WELL_COLS if col in frame.columns]
    return frame[keep].drop_duplicates("well", keep="last")


def merge_well_features(frame: pd.DataFrame, well_features: pd.DataFrame) -> pd.DataFrame:
    if well_features.empty or "well" not in well_features.columns:
        return frame
    extra = [col for col in well_features.columns if col not in frame.columns or col == "well"]
    return frame.merge(well_features[extra], on="well", how="left", validate="many_to_one")


def compute_sample_weights(df: pd.DataFrame) -> np.ndarray:
    counts = df.groupby("well", sort=False).size()
    weights = df["well"].map(lambda well: 1.0 / np.sqrt(float(counts[well]))).to_numpy(dtype=float)
    if not np.isfinite(weights).all() or weights.sum() <= 0:
        return np.ones(len(df), dtype=float)
    return weights * (len(weights) / weights.sum())


def target_meta_cols(spec: ModelSpec) -> list[str]:
    if spec.target_csv == "leftover_targets.csv":
        return [col for col in LEFTOVER_META_COLS if col != "abs_geometry_residual" or spec.merge_well_diagnostics]
    return RESIDUAL_META_COLS


def load_target_frame(spec: ModelSpec) -> pd.DataFrame:
    path = FEATURE_DIR / spec.target_csv
    header = pd.read_csv(path, nrows=0).columns.tolist()
    if spec.target_csv == "leftover_targets.csv":
        desired = [
            "well",
            "split",
            "row",
            "id",
            "truth_tvt",
            "baseline_tvt",
            "residual_target",
            "geometry_oof_residual",
            "leftover_target",
            "abs_geometry_residual",
        ]
    else:
        desired = RESIDUAL_META_COLS
    usecols = [col for col in desired if col in header]
    frame = load_csv(path, usecols=usecols)
    for col in ("truth_tvt", "baseline_tvt", "residual_target", "geometry_oof_residual", "leftover_target", "abs_geometry_residual"):
        if col in frame.columns:
            frame[col] = frame[col].astype("float64")
    return frame


def load_geometry_test_residuals(test_df: pd.DataFrame) -> pd.Series:
    if not GEOMETRY_TEST_PATH.exists():
        raise FileNotFoundError(
            f"{GEOMETRY_TEST_PATH} is missing; run scripts/train_residual_model.py --spec geometry first"
        )
    geometry_test = pd.read_csv(GEOMETRY_TEST_PATH, dtype={"id": "string"})
    if "tvt" in geometry_test.columns:
        geometry_test = geometry_test.rename(columns={"tvt": "geometry_pred"})
    elif "final_pred" in geometry_test.columns:
        geometry_test = geometry_test.rename(columns={"final_pred": "geometry_pred"})
    else:
        raise ValueError(f"{GEOMETRY_TEST_PATH} must contain tvt or final_pred")
    merged = test_df[["id", "baseline_tvt"]].merge(geometry_test[["id", "geometry_pred"]], on="id", how="left", validate="one_to_one")
    return merged["geometry_pred"] - merged["baseline_tvt"]


def load_feature_bundle(split: str, files: list[str], feature_cols: list[str], include_baseline_tvt: bool = False) -> pd.DataFrame:
    frame = None
    for pattern in files:
        path = FEATURE_DIR / pattern.format(split=split)
        print(f"loading {path.name}", flush=True)
        part = load_feature_frame(path, feature_cols, include_baseline_tvt=include_baseline_tvt)
        if frame is None:
            frame = part
        else:
            frame = append_aligned(frame, part)
    if frame is None:
        raise ValueError(f"No feature files loaded for {split}")
    return frame


def resolve_tree_backend() -> str:
    try:
        import xgboost  # noqa: F401

        return "xgboost"
    except Exception:
        return "hist_gradient_boosting"


def fit_sgd_model(x: pd.DataFrame, y: pd.Series, params: dict[str, object]) -> object:
    model = make_pipeline(
        StandardScaler(),
        SGDRegressor(
            loss="squared_error",
            alpha=float(params.get("alpha", 0.0005)),
            max_iter=int(params.get("max_iter", 30)),
            tol=float(params.get("tol", 1e-3)),
            random_state=int(params.get("random_state", 42)),
            penalty="l2",
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=3,
            average=True,
        ),
    )
    sample_weight = params.get("sample_weight")
    if sample_weight is not None:
        model.fit(x, y, sgdregressor__sample_weight=sample_weight)
    else:
        model.fit(x, y)
    return model


def fit_tree_model(x: pd.DataFrame, y: pd.Series, params: dict[str, object]) -> object:
    backend = str(params.get("model_backend") or resolve_tree_backend())
    random_state = int(params.get("random_state", 42))
    max_iter = int(params.get("max_iter", 30))
    if backend == "xgboost":
        try:
            from xgboost import XGBRegressor

            model = XGBRegressor(
                objective="reg:squarederror",
                n_estimators=max_iter,
                max_depth=int(params.get("max_depth", 4)),
                learning_rate=float(params.get("learning_rate", 0.05)),
                subsample=float(params.get("subsample", 0.9)),
                colsample_bytree=float(params.get("colsample_bytree", 0.9)),
                reg_lambda=float(params.get("reg_lambda", 1.0)),
                random_state=random_state,
                n_jobs=max(1, int(params.get("n_jobs", 1))),
                tree_method=str(params.get("tree_method", "hist")),
            )
            sample_weight = params.get("sample_weight")
            if sample_weight is not None:
                model.fit(x, y, sample_weight=sample_weight)
            else:
                model.fit(x, y)
            setattr(model, "_rogii_backend", "xgboost")
            return model
        except Exception as exc:
            print(f"xgboost backend unavailable during fit ({exc}); falling back to HistGradientBoostingRegressor", flush=True)

    model = HistGradientBoostingRegressor(
        loss="squared_error",
        learning_rate=float(params.get("learning_rate", 0.05)),
        max_iter=max_iter,
        max_leaf_nodes=int(params.get("max_leaf_nodes", 31)),
        l2_regularization=float(params.get("l2_regularization", 0.0)),
        min_samples_leaf=int(params.get("min_samples_leaf", 20)),
        random_state=random_state,
    )
    sample_weight = params.get("sample_weight")
    if sample_weight is not None:
        model.fit(x, y, sample_weight=sample_weight)
    else:
        model.fit(x, y)
    setattr(model, "_rogii_backend", "hist_gradient_boosting")
    return model


def fit_model(x: pd.DataFrame, y: pd.Series, params: dict[str, object]) -> object:
    model_family = str(params.get("model_family", "sgd"))
    if model_family == "tree":
        return fit_tree_model(x, y, params)
    if model_family == "sgd":
        return fit_sgd_model(x, y, params)
    raise ValueError(f"Unknown model family: {model_family}")


def thin_by_well(df: pd.DataFrame, max_rows_per_well: int) -> pd.DataFrame:
    if max_rows_per_well <= 0 or len(df) == 0:
        return df.copy()
    pieces: list[pd.DataFrame] = []
    for _, group in df.groupby("well", sort=False):
        group = group.sort_values("row", kind="mergesort")
        if len(group) > max_rows_per_well:
            sample_idx = np.linspace(0, len(group) - 1, num=max_rows_per_well, dtype=int)
            sample_idx = np.unique(sample_idx)
            group = group.iloc[sample_idx]
        pieces.append(group)
    return pd.concat(pieces, ignore_index=True)


def compute_feature_importance(model: object, cols: list[str]) -> pd.DataFrame:
    coef = None
    if hasattr(model, "named_steps") and "sgdregressor" in getattr(model, "named_steps", {}):
        inner = model.named_steps["sgdregressor"]
        coef = getattr(inner, "coef_", None)
    if coef is not None:
        values = np.abs(np.asarray(coef, dtype=float)).ravel()
        if len(values) == len(cols) and np.isfinite(values).any() and not np.allclose(values.sum(), 0.0):
            values = values / max(values.sum(), 1e-12)
            return pd.DataFrame({"feature": cols, "importance": values}).sort_values("importance", ascending=False)
    if hasattr(model, "feature_importances_"):
        values = np.asarray(getattr(model, "feature_importances_"), dtype=float).ravel()
        if len(values) == len(cols) and np.isfinite(values).any() and not np.allclose(values.sum(), 0.0):
            values = values / max(values.sum(), 1e-12)
            return pd.DataFrame({"feature": cols, "importance": values}).sort_values("importance", ascending=False)
    return pd.DataFrame({"feature": cols, "importance": np.zeros(len(cols), dtype=float)})


def train_oof(
    train_df: pd.DataFrame,
    fit_df: pd.DataFrame,
    cols: list[str],
    params: dict[str, float | int],
    target_col: str = "residual_target",
) -> tuple[np.ndarray, dict[str, float], pd.DataFrame]:
    wells = train_df["well"].astype(str).drop_duplicates().to_numpy()
    unique_wells = len(wells)
    n_splits = min(max(int(params.get("n_splits", 5)), 2), unique_wells)
    splitter = GroupKFold(n_splits=n_splits)
    oof = np.zeros(len(train_df), dtype=float)
    fold_rows = []
    fold_backends: list[str] = []
    use_sample_weight = bool(params.get("use_sample_weight", True))

    for fold_id, (train_idx, valid_idx) in enumerate(splitter.split(np.zeros((unique_wells, 1)), groups=wells), start=1):
        print(f"  fold {fold_id}/{n_splits}: training", flush=True)
        train_wells = set(wells[train_idx])
        valid_wells = set(wells[valid_idx])
        train_block = fit_df[fit_df["well"].isin(train_wells)]
        valid_mask = train_df["well"].isin(valid_wells)
        fold_params = dict(params)
        if use_sample_weight:
            fold_params["sample_weight"] = compute_sample_weights(train_block)
        model = fit_model(train_block[cols], train_block[target_col], fold_params)
        fold_backends.append(str(getattr(model, "_rogii_backend", params.get("model_backend", "unknown"))))
        preds = model.predict(train_df.loc[valid_mask, cols])
        oof[valid_mask.to_numpy()] = preds
        fold_rows.append(
            {
                "fold": fold_id,
                "rmse": float(mean_squared_error(train_df.loc[valid_mask, target_col], preds) ** 0.5),
                "rows": int(valid_mask.sum()),
            }
        )
        print(f"  fold {fold_id}/{n_splits}: done", flush=True)

    metrics = {
        "rmse": float(mean_squared_error(train_df[target_col], oof) ** 0.5),
        "mae": float(np.mean(np.abs(train_df[target_col].to_numpy(dtype=float) - oof))),
        "bias": float(np.mean(oof - train_df[target_col].to_numpy(dtype=float))),
        "backend": ",".join(sorted(set(fold_backends))) if fold_backends else str(params.get("model_backend", "unknown")),
    }
    return oof, metrics, pd.DataFrame(fold_rows)


def build_report(spec: ModelSpec, metrics: dict[str, float], fold_df: pd.DataFrame, per_well: pd.DataFrame, feature_importance: pd.DataFrame, train_rows: int, fit_rows: int) -> str:
    fit_fraction = float(fit_rows / train_rows) if train_rows else 0.0
    lines = [
        f"# Residual {spec.name.capitalize()} CV Report",
        "",
        f"- Backend: `{metrics.get('backend', 'unknown')}`",
        f"- CV backend: `{metrics.get('cv_backend', metrics.get('backend', 'unknown'))}`",
        f"- Training rows before thinning: {train_rows:,}",
        f"- Training rows after thinning: {fit_rows:,}",
        f"- Fit fraction: {fit_fraction:.6f}",
        f"- Max rows per well: {spec.max_rows_per_well}",
        f"- OOF RMSE: {metrics['rmse']:.4f}",
        f"- OOF MAE: {metrics['mae']:.4f}",
        f"- OOF bias: {metrics['bias']:.4f}",
        "",
        "## Fold RMSE",
        "",
        fold_df.sort_values("rmse", ascending=False).round(4).to_markdown(index=False),
        "",
        "## Worst Wells",
        "",
        per_well.head(15).round(4).to_markdown(index=False),
        "",
        "## Best Wells",
        "",
        per_well.tail(15).sort_values("rmse").round(4).to_markdown(index=False),
        "",
        "## Top Features",
        "",
        feature_importance.head(20).round(4).to_markdown(index=False),
    ]
    return "\n".join(lines) + "\n"


def run_spec(
    spec: ModelSpec,
    alpha: float,
    max_iter: int,
    tol: float,
    n_splits: int,
    min_fit_fraction: float,
    tree_backend: str,
    require_xgboost: bool,
    tree_params: dict[str, object],
) -> None:
    MODEL_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    SUBMISSION_DIR.mkdir(exist_ok=True)

    if spec.stack_geometry_correction and not (FEATURE_DIR / spec.target_csv).exists():
        raise FileNotFoundError(
            f"{FEATURE_DIR / spec.target_csv} is missing; run scripts/build_leftover_targets.py first"
        )

    print(f"[{spec.name}] loading targets from {spec.target_csv}", flush=True)
    residual_targets = load_target_frame(spec)

    train_df = load_feature_bundle("train", spec.feature_files, spec.feature_cols, include_baseline_tvt=False)
    train_df = append_aligned(residual_targets, train_df)
    if spec.merge_well_diagnostics:
        train_df = merge_well_features(train_df, load_part3_well_features())

    missing = [c for c in spec.feature_cols if c not in train_df.columns]
    if missing:
        raise KeyError(f"Missing required feature columns for {spec.name}: {missing}")
    train_df = train_df.sort_values(["well", "row"], kind="mergesort").reset_index(drop=True)
    if spec.target_col not in train_df.columns:
        raise KeyError(f"Missing target column {spec.target_col} for {spec.name}")

    fit_df = thin_by_well(train_df, spec.max_rows_per_well)
    fit_fraction = float(len(fit_df) / len(train_df)) if len(train_df) else 0.0
    if fit_fraction < min_fit_fraction:
        raise RuntimeError(
            f"[{spec.name}] fit fraction {fit_fraction:.6f} is below required {min_fit_fraction:.6f}. "
            f"train_rows={len(train_df)} fit_rows={len(fit_df)} max_rows_per_well={spec.max_rows_per_well}. "
            "Use --max-rows-per-well 0 for full training, or lower --min-fit-fraction only for an explicit sampled experiment."
        )
    if spec.model_family == "tree":
        model_backend = resolve_tree_backend() if tree_backend == "auto" else tree_backend
        if require_xgboost and model_backend != "xgboost":
            raise RuntimeError(
                f"[{spec.name}] --require-xgboost was set, but resolved backend is {model_backend}. "
                "Install xgboost in the run environment or remove --require-xgboost for a fallback experiment."
            )
    else:
        model_backend = "sgd"
    params = {
        "model_family": spec.model_family,
        "model_backend": model_backend,
        "alpha": alpha,
        "max_iter": max_iter,
        "tol": tol,
        "n_splits": n_splits,
        **tree_params,
    }
    oof, metrics, fold_df = train_oof(train_df, fit_df, spec.feature_cols, params, target_col=spec.target_col)
    train_df["oof_residual_pred"] = oof
    if spec.stack_geometry_correction:
        if "geometry_oof_residual" not in train_df.columns:
            raise KeyError(f"{spec.name} requires geometry_oof_residual in {spec.target_csv}")
        train_df["geometry_correction"] = train_df["geometry_oof_residual"]
        train_df["stacked_correction"] = train_df["geometry_correction"] + train_df["oof_residual_pred"]
        train_df["final_pred"] = train_df["baseline_tvt"] + train_df["stacked_correction"]
    else:
        train_df["final_pred"] = train_df["baseline_tvt"] + train_df["oof_residual_pred"]
    train_df["abs_error"] = np.abs(train_df["truth_tvt"] - train_df["final_pred"])

    fit_params = dict(params)
    if params.get("use_sample_weight", True):
        fit_params["sample_weight"] = compute_sample_weights(fit_df)
    model = fit_model(fit_df[spec.feature_cols], fit_df[spec.target_col], fit_params)
    feature_importance = compute_feature_importance(model, spec.feature_cols)
    actual_backend = str(getattr(model, "_rogii_backend", model_backend))
    if require_xgboost and spec.model_family == "tree" and actual_backend != "xgboost":
        raise RuntimeError(
            f"[{spec.name}] --require-xgboost was set, but actual fitted backend is {actual_backend}. "
            "The run is not a true XGBoost training run."
        )
    metrics["cv_backend"] = metrics.get("backend", model_backend)
    metrics["backend"] = actual_backend
    params["requested_model_backend"] = model_backend
    params["model_backend"] = actual_backend
    model_path = MODEL_DIR / (spec.output_model or f"{spec.model_dir_name}.pkl")
    with model_path.open("wb") as fh:
        pickle.dump(model, fh)

    config_path = MODEL_DIR / (spec.output_config or f"{spec.model_dir_name}_config.json")
    with config_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "model_name": spec.name,
                "model_family": spec.model_family,
                "model_backend": actual_backend,
                "requested_model_backend": model_backend,
                "features": spec.feature_cols,
                "target_csv": spec.target_csv,
                "target_col": spec.target_col,
                "stack_geometry_correction": spec.stack_geometry_correction,
                "params": params,
                "metrics": metrics,
                "final_tvt_metrics": {
                    "rmse": float(mean_squared_error(train_df["truth_tvt"], train_df["final_pred"]) ** 0.5),
                    "mae": float(np.mean(np.abs(train_df["truth_tvt"] - train_df["final_pred"]))),
                    "bias": float(np.mean(train_df["final_pred"] - train_df["truth_tvt"])),
                },
                "train_rows": int(len(train_df)),
                "fit_rows": int(len(fit_df)),
                "fit_fraction": fit_fraction,
                "n_splits": int(n_splits),
                "max_rows_per_well": int(spec.max_rows_per_well),
            },
            fh,
            indent=2,
            ensure_ascii=False,
        )
    feature_list_path = MODEL_DIR / (spec.output_feature_list or f"{spec.model_dir_name}_feature_list.txt")
    feature_list_path.write_text("\n".join(spec.feature_cols) + "\n", encoding="utf-8")

    oof_path = OUTPUT_DIR / spec.output_oof
    oof_cols = [
        "well",
        "split",
        "row",
        "id",
        "truth_tvt",
        "baseline_tvt",
        spec.target_col,
        "oof_residual_pred",
        "final_pred",
        "abs_error",
    ]
    if spec.stack_geometry_correction:
        oof_cols.insert(8, "geometry_correction")
        oof_cols.insert(9, "stacked_correction")
    if "residual_target" not in oof_cols and "residual_target" in train_df.columns:
        oof_cols.insert(7, "residual_target")
    oof_cols = [col for col in oof_cols if col in train_df.columns]
    train_df[oof_cols].to_csv(oof_path, index=False)
    per_well = (
        train_df.groupby("well", as_index=False)
        .agg(
            rmse=("abs_error", lambda s: float(np.sqrt(np.mean((s.to_numpy(dtype=float)) ** 2)))),
            mean_abs_error=("abs_error", "mean"),
            bias=("final_pred", lambda s: float(np.mean(s.to_numpy(dtype=float) - train_df.loc[s.index, "truth_tvt"].to_numpy(dtype=float)))),
            rows=("id", "count"),
        )
        .sort_values("rmse", ascending=False)
    )
    cv_path = OUTPUT_DIR / spec.output_cv
    per_well.to_csv(cv_path, index=False)

    test_df = load_feature_bundle("test", spec.feature_files, spec.feature_cols, include_baseline_tvt=True)
    if spec.merge_well_diagnostics:
        test_diag = load_part3_well_features()
        if not test_diag.empty:
            test_df = merge_well_features(test_df, test_diag)
    if spec.stack_geometry_correction and "abs_geometry_residual" in spec.feature_cols:
        geometry_residual = load_geometry_test_residuals(test_df)
        test_df["abs_geometry_residual"] = geometry_residual.abs()
    missing_test = [c for c in spec.feature_cols if c not in test_df.columns]
    if missing_test:
        raise KeyError(f"Missing required test columns for {spec.name}: {missing_test}")
    test_df = test_df.sort_values(["well", "row"], kind="mergesort").reset_index(drop=True)
    test_df["residual_pred"] = model.predict(test_df[spec.feature_cols])
    if spec.stack_geometry_correction:
        test_df["geometry_correction"] = load_geometry_test_residuals(test_df)
        test_df["stacked_correction"] = test_df["geometry_correction"] + test_df["residual_pred"]
        test_df["final_pred"] = test_df["baseline_tvt"] + test_df["stacked_correction"]
    else:
        test_df["final_pred"] = test_df["baseline_tvt"] + test_df["residual_pred"]
    test_out_path = OUTPUT_DIR / spec.output_test
    test_df[["id", "final_pred"]].rename(columns={"final_pred": "tvt"}).to_csv(test_out_path, index=False)
    submission_path = SUBMISSION_DIR / spec.output_submission
    test_df[["id", "final_pred"]].rename(columns={"final_pred": "tvt"}).to_csv(submission_path, index=False)

    report = build_report(spec, metrics, fold_df, per_well, feature_importance, len(train_df), len(fit_df))
    (REPORT_DIR / spec.output_report).write_text(report, encoding="utf-8")
    feature_importance.to_csv(REPORT_DIR / f"{spec.model_dir_name}_feature_importance.csv", index=False)

    print(f"Wrote {oof_path}")
    print(f"Wrote {cv_path}")
    print(f"Wrote {test_out_path}")
    print(f"Wrote {submission_path}")
    print(f"Wrote {REPORT_DIR / spec.output_report}")
    print(f"Wrote {REPORT_DIR / f'{spec.model_dir_name}_feature_importance.csv'}")
    print(f"Wrote {model_path}")
    print(f"Wrote {config_path}")
    print(f"Wrote {feature_list_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train residual model families.")
    parser.add_argument("--spec", choices=sorted(SPECS.keys()) + ["all"], default="xgb")
    parser.add_argument("--alpha", type=float, default=0.0005)
    parser.add_argument("--max-iter", type=int, default=30)
    parser.add_argument("--tol", type=float, default=1e-3)
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument(
        "--no-sample-weight",
        action="store_true",
        help="Disable per-well sample weights during residual training.",
    )
    parser.add_argument("--tree-backend", choices=["auto", "xgboost", "hist_gradient_boosting"], default="auto")
    parser.add_argument("--require-xgboost", action="store_true", help="Fail instead of falling back when the selected tree backend is not XGBoost.")
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--max-depth", type=int, default=4)
    parser.add_argument("--subsample", type=float, default=0.9)
    parser.add_argument("--colsample-bytree", type=float, default=0.9)
    parser.add_argument("--reg-lambda", type=float, default=1.0)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--tree-method", default="hist")
    parser.add_argument("--max-leaf-nodes", type=int, default=31)
    parser.add_argument("--min-samples-leaf", type=int, default=20)
    parser.add_argument("--l2-regularization", type=float, default=0.0)
    parser.add_argument(
        "--max-rows-per-well",
        type=int,
        default=None,
        help="Override per-well training cap. Use 0 for full-row training. Defaults are full-row for leaderboard candidates.",
    )
    parser.add_argument(
        "--min-fit-fraction",
        type=float,
        default=0.95,
        help="Fail before fitting if sampled training uses less than this fraction of train rows.",
    )
    args = parser.parse_args()

    tree_params = {
        "learning_rate": args.learning_rate,
        "max_depth": args.max_depth,
        "subsample": args.subsample,
        "colsample_bytree": args.colsample_bytree,
        "reg_lambda": args.reg_lambda,
        "n_jobs": args.n_jobs,
        "tree_method": args.tree_method,
        "max_leaf_nodes": args.max_leaf_nodes,
        "min_samples_leaf": args.min_samples_leaf,
        "l2_regularization": args.l2_regularization,
        "use_sample_weight": not args.no_sample_weight,
    }
    specs = SPECS.values() if args.spec == "all" else [SPECS[args.spec]]
    for spec in specs:
        if args.max_rows_per_well is not None:
            spec = replace(spec, max_rows_per_well=args.max_rows_per_well)
        run_spec(
            spec,
            args.alpha,
            args.max_iter,
            args.tol,
            args.n_splits,
            args.min_fit_fraction,
            args.tree_backend,
            args.require_xgboost,
            tree_params,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
