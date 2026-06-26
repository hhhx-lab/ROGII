#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from part2_utils import ALPHA_GRID, MODEL_DIR, OUTPUT_DIR, REPORT_DIR, ROOT, data_hash_short
from rogii_utils import regression_metrics


BASELINE_OOF_PATH = OUTPUT_DIR / "baseline_predictions_train_hidden.csv"
BASELINE_TEST_PATH = OUTPUT_DIR / "baseline_predictions_test.csv"
GEOMETRY_OOF_PATH = OUTPUT_DIR / "residual_geometry_oof.csv"
GEOMETRY_TEST_PATH = OUTPUT_DIR / "residual_geometry_test_predictions.csv"
ORACLE_ALPHA_PATH = OUTPUT_DIR / "gated_alpha_by_well.csv"
ORACLE_GATED_OOF_PATH = OUTPUT_DIR / "gated_geometry_oof.csv"
DIAGNOSTICS_PATH = OUTPUT_DIR / "part3_diagnostics.csv"

ALPHA_BY_WELL_PATH = OUTPUT_DIR / "learned_gated_alpha_by_well.csv"
OOF_PATH = OUTPUT_DIR / "learned_gated_geometry_oof.csv"
CV_BY_WELL_PATH = OUTPUT_DIR / "learned_gated_geometry_cv_by_well.csv"
TEST_PATH = OUTPUT_DIR / "learned_gated_geometry_test_predictions.csv"
SUBMISSION_PATH = ROOT / "submissions" / "learned_gated_geometry_submission.csv"
CONFIG_PATH = MODEL_DIR / "learned_gated_geometry_config.json"
MODEL_PATH = MODEL_DIR / "learned_gater_model.pkl"
REPORT_PATH = REPORT_DIR / "learned_gated_geometry_cv_report.md"

SAFE_DIAGNOSTIC_COLUMNS = [
    "known_rows",
    "target_rows",
    "known_ratio",
    "target_ratio",
    "gr_missing_rate",
    "baseline_slope_median",
    "baseline_slope_std",
    "baseline_confidence",
    "gr_std",
    "gr_volatility",
    "gr_quality_score",
    "typewell_rows",
    "typewell_has_geology",
    "typewell_quality_score",
    "risk_score",
    "route_suggestion",
]


def rmse(y_true: np.ndarray | pd.Series, y_pred: np.ndarray | pd.Series) -> float:
    return float(mean_squared_error(np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)) ** 0.5)


def read_geometry_oof() -> pd.DataFrame:
    if not GEOMETRY_OOF_PATH.exists():
        raise FileNotFoundError(f"{GEOMETRY_OOF_PATH} is missing; run geometry residual first")
    frame = pd.read_csv(GEOMETRY_OOF_PATH, dtype={"id": "string", "well": "string"}, low_memory=False)
    required = {"id", "well", "truth_tvt", "baseline_tvt", "oof_residual_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{GEOMETRY_OOF_PATH} missing columns: {sorted(missing)}")
    if "final_pred" not in frame.columns:
        frame["final_pred"] = frame["baseline_tvt"] + frame["oof_residual_pred"]
    if "row" not in frame.columns:
        parts = frame["id"].str.rsplit("_", n=1, expand=True)
        frame["row"] = parts[1].astype(int)
    if "split" not in frame.columns:
        frame["split"] = "train"
    return frame


def read_geometry_test() -> pd.DataFrame:
    if not GEOMETRY_TEST_PATH.exists():
        raise FileNotFoundError(f"{GEOMETRY_TEST_PATH} is missing; run geometry residual first")
    baseline = pd.read_csv(BASELINE_TEST_PATH, dtype={"id": "string"})
    geometry = pd.read_csv(GEOMETRY_TEST_PATH, dtype={"id": "string"})
    if "tvt" in geometry.columns:
        geometry = geometry.rename(columns={"tvt": "geometry_pred"})
    elif "final_pred" in geometry.columns:
        geometry = geometry.rename(columns={"final_pred": "geometry_pred"})
    else:
        raise ValueError(f"{GEOMETRY_TEST_PATH} must contain tvt or final_pred")
    frame = baseline.merge(geometry[["id", "geometry_pred"]], on="id", how="left", validate="one_to_one")
    if frame["geometry_pred"].isna().any():
        raise ValueError("geometry test predictions are missing rows after merge")
    frame["well"] = frame["id"].str.rsplit("_", n=1).str[0].astype("string")
    parts = frame["id"].str.rsplit("_", n=1, expand=True)
    frame["row"] = parts[1].astype(int)
    frame["geometry_residual"] = frame["geometry_pred"].astype(float) - frame["baseline_tvt"].astype(float)
    return frame


def residual_summary_from_train(geometry_oof: pd.DataFrame) -> pd.DataFrame:
    work = geometry_oof.copy()
    work["abs_geometry_residual"] = work["oof_residual_pred"].abs()
    work["geometry_residual_std_input"] = work["oof_residual_pred"].astype(float)
    return (
        work.groupby("well", as_index=False)
        .agg(
            geometry_residual_mean=("oof_residual_pred", "mean"),
            geometry_residual_std=("geometry_residual_std_input", "std"),
            geometry_residual_abs_mean=("abs_geometry_residual", "mean"),
            geometry_residual_abs_median=("abs_geometry_residual", "median"),
            geometry_residual_abs_p95=("abs_geometry_residual", lambda s: float(np.quantile(s.to_numpy(dtype=float), 0.95))),
            geometry_residual_abs_max=("abs_geometry_residual", "max"),
            geometry_rows=("id", "count"),
        )
        .fillna(0.0)
    )


def residual_summary_from_test(test_frame: pd.DataFrame) -> pd.DataFrame:
    work = test_frame.copy()
    work["abs_geometry_residual"] = work["geometry_residual"].abs()
    return (
        work.groupby("well", as_index=False)
        .agg(
            geometry_residual_mean=("geometry_residual", "mean"),
            geometry_residual_std=("geometry_residual", "std"),
            geometry_residual_abs_mean=("abs_geometry_residual", "mean"),
            geometry_residual_abs_median=("abs_geometry_residual", "median"),
            geometry_residual_abs_p95=("abs_geometry_residual", lambda s: float(np.quantile(s.to_numpy(dtype=float), 0.95))),
            geometry_residual_abs_max=("abs_geometry_residual", "max"),
            geometry_rows=("id", "count"),
        )
        .fillna(0.0)
    )


def load_diagnostics(split: str) -> pd.DataFrame:
    if not DIAGNOSTICS_PATH.exists():
        return pd.DataFrame(columns=["well"])
    frame = pd.read_csv(DIAGNOSTICS_PATH, dtype={"well": "string"})
    if "split" in frame.columns:
        frame = frame[frame["split"].fillna("train").eq(split)].copy()
    columns = ["well", *[col for col in SAFE_DIAGNOSTIC_COLUMNS if col in frame.columns]]
    return frame[columns].drop_duplicates("well", keep="last")


def build_well_features(split: str, residual_summary: pd.DataFrame) -> pd.DataFrame:
    diagnostics = load_diagnostics(split)
    if diagnostics.empty:
        features = residual_summary.copy()
    else:
        features = diagnostics.merge(residual_summary, on="well", how="outer", validate="one_to_one")
    features["well"] = features["well"].astype("string")
    return features.sort_values("well", kind="mergesort").reset_index(drop=True)


def load_oracle_alpha() -> pd.DataFrame:
    if not ORACLE_ALPHA_PATH.exists():
        raise FileNotFoundError(f"{ORACLE_ALPHA_PATH} is missing; run scripts/build_gated_geometry.py first")
    frame = pd.read_csv(ORACLE_ALPHA_PATH, dtype={"well": "string"})
    required = {"well", "alpha"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{ORACLE_ALPHA_PATH} missing columns: {sorted(missing)}")
    return frame[["well", "alpha"]].rename(columns={"alpha": "oracle_alpha"}).drop_duplicates("well", keep="last")


def feature_matrix(
    frame: pd.DataFrame,
    feature_columns: list[str] | None = None,
    fill_values: dict[str, float] | None = None,
) -> tuple[pd.DataFrame, list[str], dict[str, float]]:
    blocked = {"well", "oracle_alpha"}
    usable = frame.drop(columns=[col for col in blocked if col in frame.columns]).copy()
    categorical = [col for col in ["route_suggestion"] if col in usable.columns]
    for col in usable.columns:
        if col not in categorical:
            usable[col] = pd.to_numeric(usable[col], errors="coerce")
    design = pd.get_dummies(usable, columns=categorical, dummy_na=True)
    if feature_columns is None:
        feature_columns = sorted(design.columns.tolist())
    design = design.reindex(columns=feature_columns, fill_value=0.0)
    for col in design.columns:
        design[col] = pd.to_numeric(design[col], errors="coerce")
    if fill_values is None:
        medians = design.median(numeric_only=True).fillna(0.0)
        fill_values = {col: float(medians.get(col, 0.0)) for col in feature_columns}
    design = design.fillna(fill_values).fillna(0.0)
    return design.astype(float), feature_columns, fill_values


def make_model(model_name: str, random_state: int):
    if model_name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    if model_name == "elasticnet":
        return make_pipeline(StandardScaler(), ElasticNet(alpha=0.02, l1_ratio=0.2, max_iter=10000, random_state=random_state))
    if model_name == "hgb":
        return HistGradientBoostingRegressor(
            max_iter=150,
            learning_rate=0.04,
            max_leaf_nodes=15,
            min_samples_leaf=20,
            l2_regularization=0.05,
            random_state=random_state,
        )
    if model_name == "random_forest":
        return RandomForestRegressor(
            n_estimators=300,
            max_depth=5,
            min_samples_leaf=12,
            random_state=random_state,
            n_jobs=-1,
        )
    raise ValueError(f"unknown model: {model_name}")


def clip_alpha(values: np.ndarray, snap_to_grid: bool) -> np.ndarray:
    clipped = np.clip(np.asarray(values, dtype=float), 0.0, 1.0)
    if not snap_to_grid:
        return clipped
    grid = np.asarray(sorted(set(float(value) for value in ALPHA_GRID)), dtype=float)
    nearest = np.argmin(np.abs(clipped[:, None] - grid[None, :]), axis=1)
    return grid[nearest]


def train_oof_alpha(
    train_features: pd.DataFrame,
    model_name: str,
    n_splits: int,
    random_state: int,
    snap_to_grid: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str], dict[str, float]]:
    wells = train_features["well"].astype(str).to_numpy()
    y = train_features["oracle_alpha"].to_numpy(dtype=float)
    unique_wells = np.unique(wells)
    folds = min(max(2, int(n_splits)), len(unique_wells))
    oof_alpha = np.zeros(len(train_features), dtype=float)
    fold_rows: list[dict[str, object]] = []
    last_feature_columns: list[str] | None = None
    last_fill_values: dict[str, float] | None = None

    splitter = GroupKFold(n_splits=folds)
    for fold, (train_idx, valid_idx) in enumerate(splitter.split(train_features, y, groups=wells), start=1):
        fold_train = train_features.iloc[train_idx].reset_index(drop=True)
        fold_valid = train_features.iloc[valid_idx].reset_index(drop=True)
        x_train, feature_columns, fill_values = feature_matrix(fold_train)
        x_valid, _, _ = feature_matrix(fold_valid, feature_columns=feature_columns, fill_values=fill_values)
        model = make_model(model_name, random_state + fold)
        model.fit(x_train, fold_train["oracle_alpha"].to_numpy(dtype=float))
        pred = clip_alpha(model.predict(x_valid), snap_to_grid=snap_to_grid)
        oof_alpha[valid_idx] = pred
        fold_rows.append(
            {
                "fold": fold,
                "wells": int(len(valid_idx)),
                "alpha_rmse": rmse(fold_valid["oracle_alpha"], pred),
                "alpha_mae": float(mean_absolute_error(fold_valid["oracle_alpha"], pred)),
                "mean_pred_alpha": float(np.mean(pred)),
                "mean_oracle_alpha": float(np.mean(fold_valid["oracle_alpha"])),
            }
        )
        last_feature_columns = feature_columns
        last_fill_values = fill_values

    if last_feature_columns is None or last_fill_values is None:
        raise RuntimeError("failed to build learned gater OOF folds")
    result = train_features[["well", "oracle_alpha"]].copy()
    result["learned_alpha"] = oof_alpha
    result["alpha_error"] = result["learned_alpha"] - result["oracle_alpha"]
    return result, pd.DataFrame(fold_rows), last_feature_columns, last_fill_values


def apply_alpha_to_oof(geometry_oof: pd.DataFrame, alpha_by_well: pd.DataFrame) -> pd.DataFrame:
    out = geometry_oof.merge(alpha_by_well[["well", "learned_alpha", "oracle_alpha"]], on="well", how="left", validate="many_to_one")
    if out["learned_alpha"].isna().any():
        missing = int(out["learned_alpha"].isna().sum())
        raise ValueError(f"learned alpha is missing for {missing} OOF rows")
    out["learned_gated_residual"] = out["learned_alpha"] * out["oof_residual_pred"]
    out["final_pred"] = out["baseline_tvt"] + out["learned_gated_residual"]
    out["abs_error"] = (out["final_pred"] - out["truth_tvt"]).abs()
    return out


def apply_alpha_to_test(test_frame: pd.DataFrame, alpha_by_well: pd.DataFrame, default_alpha: float) -> pd.DataFrame:
    alpha_map = alpha_by_well.set_index("well")["learned_alpha"].to_dict()
    out = test_frame.copy()
    out["learned_alpha"] = out["well"].map(alpha_map).fillna(default_alpha).astype(float)
    out["learned_gated_residual"] = out["learned_alpha"] * out["geometry_residual"]
    out["final_pred"] = out["baseline_tvt"] + out["learned_gated_residual"]
    return out


def per_well_cv(oof: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for well, group in oof.groupby("well", sort=True):
        truth = group["truth_tvt"].to_numpy(dtype=float)
        pred = group["final_pred"].to_numpy(dtype=float)
        baseline = group["baseline_tvt"].to_numpy(dtype=float)
        geometry = group["baseline_tvt"].to_numpy(dtype=float) + group["oof_residual_pred"].to_numpy(dtype=float)
        err = pred - truth
        rows.append(
            {
                "well": well,
                "rows": len(group),
                "rmse": float(np.sqrt(np.mean(err**2))),
                "mae": float(np.mean(np.abs(err))),
                "bias": float(np.mean(err)),
                "baseline_rmse": rmse(truth, baseline),
                "geometry_rmse": rmse(truth, geometry),
                "rmse_improvement_vs_baseline": rmse(truth, baseline) - float(np.sqrt(np.mean(err**2))),
                "rmse_improvement_vs_geometry": rmse(truth, geometry) - float(np.sqrt(np.mean(err**2))),
                "learned_alpha": float(group["learned_alpha"].iloc[0]),
                "oracle_alpha": float(group["oracle_alpha"].iloc[0]),
            }
        )
    return pd.DataFrame(rows).sort_values("rmse", ascending=False)


def report_metrics_table(metrics: dict[str, dict[str, float]]) -> str:
    frame = pd.DataFrame(
        [
            {
                "model": name,
                "rmse": values["rmse"],
                "mae": values["mae"],
                "p95_abs_error": values["p95_abs_error"],
                "bias": values["bias"],
            }
            for name, values in metrics.items()
        ]
    )
    return frame.round(4).to_markdown(index=False)


def write_report(
    metrics: dict[str, dict[str, float]],
    alpha_by_well: pd.DataFrame,
    fold_metrics: pd.DataFrame,
    cv_by_well: pd.DataFrame,
    model_name: str,
    feature_columns: list[str],
    snap_to_grid: bool,
) -> None:
    degraded_vs_baseline = int((cv_by_well["rmse_improvement_vs_baseline"] < 0).sum())
    degraded_vs_geometry = int((cv_by_well["rmse_improvement_vs_geometry"] < 0).sum())
    alpha_summary = alpha_by_well[["oracle_alpha", "learned_alpha", "alpha_error"]].describe().T
    lines = [
        "# Learned Gated Geometry CV Report",
        "",
        "- Candidate type: `learned_gated_residual`",
        "- Eligible for auto submission: `True`",
        "- Formula: `final_tvt = baseline_tvt + learned_alpha * geometry_residual`",
        "- Oracle alpha source: `outputs/gated_alpha_by_well.csv`",
        "",
        "The oracle `gated_geometry` candidate chooses alpha from each well's own truth and is treated only as a diagnostic upper bound. This learned gater predicts alpha from test-available well features under GroupKFold by well.",
        "",
        "## Overall Metrics",
        "",
        report_metrics_table(metrics),
        "",
        "## Learned Alpha CV",
        "",
        fold_metrics.round(6).to_markdown(index=False),
        "",
        "## Alpha Summary",
        "",
        alpha_summary.round(6).to_markdown(),
        "",
        "## Per-Well Risk",
        "",
        f"- Degraded wells vs baseline: `{degraded_vs_baseline}`",
        f"- Degraded wells vs ungated geometry: `{degraded_vs_geometry}`",
        f"- Worst-well RMSE: `{cv_by_well['rmse'].max():.4f}`",
        "",
        "## Worst Wells",
        "",
        cv_by_well.head(20).round(4).to_markdown(index=False),
        "",
        "## Training Config",
        "",
        f"- Model: `{model_name}`",
        f"- Snap alpha to grid: `{snap_to_grid}`",
        f"- Feature columns: `{len(feature_columns)}`",
        "",
        "## Outputs",
        "",
        f"- OOF: `{OOF_PATH.relative_to(ROOT)}`",
        f"- Alpha table: `{ALPHA_BY_WELL_PATH.relative_to(ROOT)}`",
        f"- Submission: `{SUBMISSION_PATH.relative_to(ROOT)}`",
        f"- Config: `{CONFIG_PATH.relative_to(ROOT)}`",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a fold-safe learned gater for geometry residual alpha.")
    parser.add_argument("--model", choices=["ridge", "elasticnet", "hgb", "random_forest"], default="ridge")
    parser.add_argument("--n-splits", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=20260623)
    parser.add_argument("--snap-alpha-grid", action="store_true", help="Snap predicted alpha to the existing alpha grid.")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    SUBMISSION_PATH.parent.mkdir(exist_ok=True)

    geometry_oof = read_geometry_oof()
    geometry_test = read_geometry_test()
    oracle_alpha = load_oracle_alpha()
    train_features = build_well_features("train", residual_summary_from_train(geometry_oof))
    train_features = train_features.merge(oracle_alpha, on="well", how="inner", validate="one_to_one")
    if train_features.empty:
        raise ValueError("no wells available to train learned gater")

    alpha_by_well, fold_metrics, feature_columns, fill_values = train_oof_alpha(
        train_features,
        model_name=args.model,
        n_splits=args.n_splits,
        random_state=args.random_state,
        snap_to_grid=args.snap_alpha_grid,
    )
    learned_oof = apply_alpha_to_oof(geometry_oof, alpha_by_well)
    cv_by_well = per_well_cv(learned_oof)

    all_x, all_feature_columns, all_fill_values = feature_matrix(train_features)
    final_model = make_model(args.model, args.random_state)
    final_model.fit(all_x, train_features["oracle_alpha"].to_numpy(dtype=float))
    feature_columns = all_feature_columns
    fill_values = all_fill_values

    test_features = build_well_features("test", residual_summary_from_test(geometry_test))
    test_x, _, _ = feature_matrix(test_features, feature_columns=feature_columns, fill_values=fill_values)
    test_alpha = clip_alpha(final_model.predict(test_x), snap_to_grid=args.snap_alpha_grid)
    test_alpha_by_well = test_features[["well"]].copy()
    test_alpha_by_well["learned_alpha"] = test_alpha
    test_alpha_by_well["oracle_alpha"] = np.nan
    default_alpha = float(np.mean(alpha_by_well["learned_alpha"]))
    learned_test = apply_alpha_to_test(geometry_test, test_alpha_by_well, default_alpha=default_alpha)

    baseline_metrics = regression_metrics(learned_oof["truth_tvt"], learned_oof["baseline_tvt"])
    geometry_metrics = regression_metrics(
        learned_oof["truth_tvt"],
        learned_oof["baseline_tvt"] + learned_oof["oof_residual_pred"],
    )
    learned_metrics = regression_metrics(learned_oof["truth_tvt"], learned_oof["final_pred"])
    metrics = {
        "baseline": baseline_metrics,
        "geometry_ungated": geometry_metrics,
        "learned_gated_geometry": learned_metrics,
    }
    if ORACLE_GATED_OOF_PATH.exists():
        oracle_oof = pd.read_csv(ORACLE_GATED_OOF_PATH, usecols=["truth_tvt", "final_pred"])
        metrics["oracle_gated_geometry_upper_bound"] = regression_metrics(oracle_oof["truth_tvt"], oracle_oof["final_pred"])

    alpha_out = alpha_by_well.merge(
        train_features.drop(columns=["oracle_alpha"], errors="ignore"),
        on="well",
        how="left",
        validate="one_to_one",
    )
    alpha_out.to_csv(ALPHA_BY_WELL_PATH, index=False)
    learned_oof[
        [
            "well",
            "split",
            "row",
            "id",
            "truth_tvt",
            "baseline_tvt",
            "oof_residual_pred",
            "oracle_alpha",
            "learned_alpha",
            "learned_gated_residual",
            "final_pred",
            "abs_error",
        ]
    ].to_csv(OOF_PATH, index=False)
    cv_by_well.to_csv(CV_BY_WELL_PATH, index=False)
    learned_test[["id", "final_pred"]].rename(columns={"final_pred": "tvt"}).to_csv(TEST_PATH, index=False)
    learned_test[["id", "final_pred"]].rename(columns={"final_pred": "tvt"}).to_csv(SUBMISSION_PATH, index=False)

    model_payload = {
        "model": final_model,
        "feature_columns": feature_columns,
        "fill_values": fill_values,
        "model_name": args.model,
        "snap_alpha_grid": args.snap_alpha_grid,
    }
    with MODEL_PATH.open("wb") as handle:
        pickle.dump(model_payload, handle)

    config = {
        "model_name": "learned_gated_geometry",
        "model_family": "learned_gater",
        "model_backend": args.model,
        "candidate_type": "learned_gated_residual",
        "oracle_candidate": False,
        "diagnostic_only": False,
        "eligible_for_auto_submission": True,
        "formula": "baseline_tvt + learned_alpha * geometry_residual",
        "alpha_target": "oracle alpha from gated_geometry, used only as train label",
        "cv_method": "GroupKFold by well",
        "data_hash": data_hash_short(),
        "n_splits": int(min(max(2, args.n_splits), train_features["well"].nunique())),
        "snap_alpha_grid": bool(args.snap_alpha_grid),
        "feature_columns": feature_columns,
        "metrics": learned_metrics,
        "baseline_metrics": baseline_metrics,
        "geometry_metrics": geometry_metrics,
        "train_wells": int(train_features["well"].nunique()),
        "train_rows": int(len(learned_oof)),
        "fit_rows": int(len(train_features)),
        "fit_fraction": 1.0,
        "outputs": {
            "oof": str(OOF_PATH.relative_to(ROOT)),
            "alpha_by_well": str(ALPHA_BY_WELL_PATH.relative_to(ROOT)),
            "cv_by_well": str(CV_BY_WELL_PATH.relative_to(ROOT)),
            "test_predictions": str(TEST_PATH.relative_to(ROOT)),
            "submission": str(SUBMISSION_PATH.relative_to(ROOT)),
        },
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_report(metrics, alpha_by_well, fold_metrics, cv_by_well, args.model, feature_columns, args.snap_alpha_grid)

    print(f"Wrote {ALPHA_BY_WELL_PATH}")
    print(f"Wrote {OOF_PATH}")
    print(f"Wrote {CV_BY_WELL_PATH}")
    print(f"Wrote {TEST_PATH}")
    print(f"Wrote {SUBMISSION_PATH}")
    print(f"Wrote {MODEL_PATH}")
    print(f"Wrote {CONFIG_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"learned_gated_geometry rmse={learned_metrics['rmse']:.4f} model={args.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
