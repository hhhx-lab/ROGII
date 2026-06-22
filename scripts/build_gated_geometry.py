#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

from part2_utils import ALPHA_GRID, MODEL_DIR, OUTPUT_DIR, REPORT_DIR, ROOT, data_hash_short
from rogii_utils import regression_metrics


BASELINE_OOF_PATH = OUTPUT_DIR / "baseline_predictions_train_hidden.csv"
GEOMETRY_OOF_PATH = OUTPUT_DIR / "residual_geometry_oof.csv"
GEOMETRY_TEST_PATH = OUTPUT_DIR / "residual_geometry_test_predictions.csv"
DIAGNOSTICS_PATH = OUTPUT_DIR / "part3_diagnostics.csv"
ALPHA_BY_WELL_PATH = OUTPUT_DIR / "gated_alpha_by_well.csv"
OOF_PATH = OUTPUT_DIR / "gated_geometry_oof.csv"
TEST_PATH = OUTPUT_DIR / "gated_geometry_test_predictions.csv"
SUBMISSION_PATH = ROOT / "submissions" / "gated_geometry_submission.csv"
CONFIG_PATH = MODEL_DIR / "gated_geometry_config.json"
CV_BY_WELL_PATH = OUTPUT_DIR / "gated_geometry_cv_by_well.csv"
REPORT_PATH = REPORT_DIR / "gated_geometry_cv_report.md"


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(mean_squared_error(y_true, y_pred) ** 0.5)


def search_alpha_for_group(
    truth: np.ndarray,
    baseline: np.ndarray,
    geometry_residual: np.ndarray,
    grid: list[float],
) -> tuple[float, float, str]:
    best_alpha = 0.0
    best_rmse = float("inf")
    baseline_rmse = rmse(truth, baseline)
    for alpha in grid:
        pred = baseline + alpha * geometry_residual
        score = rmse(truth, pred)
        if score < best_rmse:
            best_rmse = score
            best_alpha = float(alpha)
    if best_alpha <= 0.0:
        reason = "alpha_grid_selected_baseline"
    elif best_alpha >= 1.0 and best_rmse + 1e-9 < baseline_rmse:
        reason = "alpha_grid_selected_full_geometry"
    elif best_rmse + 1e-9 < baseline_rmse:
        reason = "alpha_grid_partial_geometry"
    else:
        reason = "alpha_grid_no_improvement_vs_baseline"
        best_alpha = 0.0
        best_rmse = baseline_rmse
    return best_alpha, best_rmse, reason


def load_geometry_oof() -> pd.DataFrame:
    if not GEOMETRY_OOF_PATH.exists():
        raise FileNotFoundError(GEOMETRY_OOF_PATH)
    frame = pd.read_csv(GEOMETRY_OOF_PATH, dtype={"id": "string", "well": "string"})
    required = {"id", "well", "truth_tvt", "baseline_tvt", "oof_residual_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{GEOMETRY_OOF_PATH} missing columns: {sorted(missing)}")
    if "final_pred" not in frame.columns:
        frame["final_pred"] = frame["baseline_tvt"] + frame["oof_residual_pred"]
    return frame


def load_baseline_oof() -> pd.DataFrame:
    if not BASELINE_OOF_PATH.exists():
        raise FileNotFoundError(BASELINE_OOF_PATH)
    frame = pd.read_csv(BASELINE_OOF_PATH, dtype={"id": "string"})
    required = {"id", "truth_tvt", "baseline_tvt"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{BASELINE_OOF_PATH} missing columns: {sorted(missing)}")
    return frame


def load_diagnostics() -> pd.DataFrame:
    if not DIAGNOSTICS_PATH.exists():
        return pd.DataFrame()
    frame = pd.read_csv(DIAGNOSTICS_PATH, dtype={"well": "string"})
    if "split" in frame.columns:
        frame = frame[frame["split"].fillna("train").ne("test")].copy()
    return frame.drop_duplicates("well", keep="last")


def build_alpha_table(oof: pd.DataFrame, grid: list[float]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for well, group in oof.groupby("well", sort=True):
        truth = group["truth_tvt"].to_numpy(dtype=float)
        baseline = group["baseline_tvt"].to_numpy(dtype=float)
        geometry_residual = group["oof_residual_pred"].to_numpy(dtype=float)
        geometry_rmse = rmse(truth, group["final_pred"].to_numpy(dtype=float))
        alpha, alpha_rmse, reason = search_alpha_for_group(truth, baseline, geometry_residual, grid)
        rows.append(
            {
                "well": well,
                "rows": len(group),
                "alpha": alpha,
                "alpha_rmse": alpha_rmse,
                "baseline_rmse": rmse(truth, baseline),
                "geometry_rmse": geometry_rmse,
                "rmse_improvement_vs_baseline": rmse(truth, baseline) - alpha_rmse,
                "rmse_improvement_vs_geometry": geometry_rmse - alpha_rmse,
                "gater_reason": reason,
            }
        )
    return pd.DataFrame(rows).sort_values("alpha_rmse", kind="mergesort")


def apply_alpha(oof: pd.DataFrame, alpha_table: pd.DataFrame) -> pd.DataFrame:
    alpha_map = alpha_table.set_index("well")["alpha"].to_dict()
    out = oof.copy()
    out["alpha"] = out["well"].map(alpha_map).fillna(1.0).astype(float)
    out["gated_residual"] = out["alpha"] * out["oof_residual_pred"]
    out["final_pred"] = out["baseline_tvt"] + out["gated_residual"]
    out["abs_error"] = (out["final_pred"] - out["truth_tvt"]).abs()
    return out


def build_test_predictions(alpha_table: pd.DataFrame) -> pd.DataFrame:
    if not GEOMETRY_TEST_PATH.exists():
        raise FileNotFoundError(GEOMETRY_TEST_PATH)
    baseline_test = pd.read_csv(OUTPUT_DIR / "baseline_predictions_test.csv", dtype={"id": "string"})
    geometry_test = pd.read_csv(GEOMETRY_TEST_PATH, dtype={"id": "string"})
    if "tvt" in geometry_test.columns:
        geometry_test = geometry_test.rename(columns={"tvt": "geometry_pred"})
    elif "final_pred" in geometry_test.columns:
        geometry_test = geometry_test.rename(columns={"final_pred": "geometry_pred"})
    else:
        raise ValueError(f"{GEOMETRY_TEST_PATH} must contain tvt or final_pred")

    frame = baseline_test.merge(geometry_test[["id", "geometry_pred"]], on="id", how="left", validate="one_to_one")
    frame["well"] = frame["id"].str.rsplit("_", n=1).str[0]
    alpha_map = alpha_table.set_index("well")["alpha"].to_dict()
    frame["alpha"] = frame["well"].map(alpha_map).fillna(1.0).astype(float)
    frame["geometry_residual"] = frame["geometry_pred"] - frame["baseline_tvt"]
    frame["gated_residual"] = frame["alpha"] * frame["geometry_residual"]
    frame["final_pred"] = frame["baseline_tvt"] + frame["gated_residual"]
    return frame


def per_well_cv(oof: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for well, group in oof.groupby("well", sort=True):
        truth = group["truth_tvt"].to_numpy(dtype=float)
        pred = group["final_pred"].to_numpy(dtype=float)
        err = pred - truth
        rows.append(
            {
                "well": well,
                "rows": len(group),
                "rmse": float(np.sqrt(np.mean(err**2))),
                "mean_abs_error": float(np.mean(np.abs(err))),
                "bias": float(np.mean(err)),
                "alpha": float(group["alpha"].iloc[0]),
            }
        )
    return pd.DataFrame(rows).sort_values("rmse", ascending=False)


def compare_to_baseline(oof: pd.DataFrame, alpha_table: pd.DataFrame) -> tuple[int, int]:
    merged = alpha_table.copy()
    improved = int((merged["rmse_improvement_vs_baseline"] > 0).sum())
    degraded = int((merged["rmse_improvement_vs_baseline"] < 0).sum())
    return improved, degraded


def build_report(
    oof: pd.DataFrame,
    alpha_table: pd.DataFrame,
    geometry_oof: pd.DataFrame,
    grid: list[float],
) -> str:
    gated_metrics = regression_metrics(oof["truth_tvt"], oof["final_pred"])
    geometry_metrics = regression_metrics(geometry_oof["truth_tvt"], geometry_oof["final_pred"])
    baseline_metrics = regression_metrics(oof["truth_tvt"], oof["baseline_tvt"])
    improved, degraded = compare_to_baseline(oof, alpha_table)
    alpha_counts = alpha_table["alpha"].value_counts().sort_index()
    lines = [
        "# Gated Geometry CV Report",
        "",
        "- Model: `per_well_alpha_grid`",
        f"- Data hash: `{data_hash_short()}`",
        f"- Alpha grid: `{grid}`",
        f"- Wells: `{alpha_table['well'].nunique()}`",
        f"- Rows: `{len(oof):,}`",
        "",
        "## Overall Metrics",
        "",
        "| model | rmse | mae | p95_abs_error | bias |",
        "|:---|---:|---:|---:|---:|",
        f"| baseline | {baseline_metrics['rmse']:.4f} | {baseline_metrics['mae']:.4f} | {baseline_metrics['p95_abs_error']:.4f} | {baseline_metrics['bias']:.4f} |",
        f"| geometry_ungated | {geometry_metrics['rmse']:.4f} | {geometry_metrics['mae']:.4f} | {geometry_metrics['p95_abs_error']:.4f} | {geometry_metrics['bias']:.4f} |",
        f"| gated_geometry | {gated_metrics['rmse']:.4f} | {gated_metrics['mae']:.4f} | {gated_metrics['p95_abs_error']:.4f} | {gated_metrics['bias']:.4f} |",
        "",
        "## Alpha Distribution",
        "",
        alpha_counts.rename("wells").to_frame().to_markdown(),
        "",
        "## Per-Well Summary",
        "",
        f"- Improved vs baseline: `{improved}`",
        f"- Degraded vs baseline: `{degraded}`",
        f"- Mean alpha: `{alpha_table['alpha'].mean():.4f}`",
        f"- Wells with alpha < 1.0: `{(alpha_table['alpha'] < 1.0).sum()}`",
        "",
        "## Outputs",
        "",
        f"- OOF: `{OOF_PATH.relative_to(ROOT)}`",
        f"- Alpha table: `{ALPHA_BY_WELL_PATH.relative_to(ROOT)}`",
        f"- Submission: `{SUBMISSION_PATH.relative_to(ROOT)}`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build per-well alpha-gated geometry residual candidate.")
    parser.add_argument(
        "--alpha-grid",
        type=float,
        nargs="+",
        default=ALPHA_GRID,
        help="Alpha values searched per well on OOF rows.",
    )
    args = parser.parse_args()

    grid = sorted({float(value) for value in args.alpha_grid})
    if not grid:
        raise ValueError("alpha grid must not be empty")

    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    SUBMISSION_PATH.parent.mkdir(exist_ok=True)

    geometry_oof = load_geometry_oof()
    baseline_oof = load_baseline_oof()
    oof = geometry_oof.copy()
    if "split" not in oof.columns:
        oof["split"] = "train"
    if "row" not in oof.columns:
        parts = oof["id"].str.rsplit("_", n=1, expand=True)
        oof["row"] = parts[1].astype(int)
    truth_check = oof[["id", "truth_tvt"]].merge(
        baseline_oof[["id", "truth_tvt"]].rename(columns={"truth_tvt": "truth_tvt_baseline"}),
        on="id",
        how="inner",
        validate="one_to_one",
    )
    mismatch = (truth_check["truth_tvt"] - truth_check["truth_tvt_baseline"]).abs().max()
    if pd.notna(mismatch) and mismatch > 1e-6:
        raise ValueError(f"truth mismatch between geometry and baseline OOF: {mismatch}")

    alpha_table = build_alpha_table(oof, grid)
    diagnostics = load_diagnostics()
    if not diagnostics.empty and "well" in diagnostics.columns:
        alpha_table = alpha_table.merge(
            diagnostics[
                [
                    col
                    for col in (
                        "well",
                        "route_suggestion",
                        "baseline_confidence",
                        "gr_quality_score",
                        "typewell_quality_score",
                        "risk_score",
                    )
                    if col in diagnostics.columns
                ]
            ],
            on="well",
            how="left",
        )

    gated_oof = apply_alpha(oof, alpha_table)
    test_frame = build_test_predictions(alpha_table)
    cv_by_well = per_well_cv(gated_oof)
    improved, degraded = compare_to_baseline(gated_oof, alpha_table)

    alpha_table.to_csv(ALPHA_BY_WELL_PATH, index=False)
    gated_oof[
        [
            "well",
            "split",
            "row",
            "id",
            "truth_tvt",
            "baseline_tvt",
            "oof_residual_pred",
            "alpha",
            "gated_residual",
            "final_pred",
            "abs_error",
        ]
    ].to_csv(OOF_PATH, index=False)
    test_frame[["id", "final_pred"]].rename(columns={"final_pred": "tvt"}).to_csv(TEST_PATH, index=False)
    test_frame[["id", "final_pred"]].rename(columns={"final_pred": "tvt"}).to_csv(SUBMISSION_PATH, index=False)
    cv_by_well.to_csv(CV_BY_WELL_PATH, index=False)

    config = {
        "model_name": "gated_geometry",
        "model_family": "gater",
        "model_backend": "per_well_alpha_grid",
        "data_hash": data_hash_short(),
        "alpha_grid": grid,
        "metrics": regression_metrics(gated_oof["truth_tvt"], gated_oof["final_pred"]),
        "baseline_metrics": regression_metrics(gated_oof["truth_tvt"], gated_oof["baseline_tvt"]),
        "geometry_metrics": regression_metrics(geometry_oof["truth_tvt"], geometry_oof["final_pred"]),
        "improved_wells": improved,
        "degraded_wells": degraded,
        "mean_alpha": float(alpha_table["alpha"].mean()),
        "train_rows": int(len(gated_oof)),
        "fit_rows": int(len(gated_oof)),
        "fit_fraction": 1.0,
        "feature_columns": ["oof_residual_pred", "alpha"],
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_PATH.write_text(build_report(gated_oof, alpha_table, geometry_oof, grid), encoding="utf-8")

    print(f"Wrote {OOF_PATH}")
    print(f"Wrote {ALPHA_BY_WELL_PATH}")
    print(f"Wrote {TEST_PATH}")
    print(f"Wrote {SUBMISSION_PATH}")
    print(f"Wrote {CV_BY_WELL_PATH}")
    print(f"Wrote {CONFIG_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(
        "gated_geometry "
        f"rmse={config['metrics']['rmse']:.4f} "
        f"improved_wells={improved} degraded_wells={degraded}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())