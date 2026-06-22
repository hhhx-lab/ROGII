#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

from data_paths import load_sample_submission


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"
SUBMISSION_DIR = ROOT / "submissions"


ROUTE_CONFIDENCE = {
    "typewell_alignment": 0.85,
    "gr_residual": 0.65,
    "geometry_residual": 0.55,
    "baseline_fallback": 0.35,
}

BLEND_VARIANTS = ["conservative", "balanced", "aggressive", "optimized"]


def load_predictions(path: Path, name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string"})
    if name in frame.columns:
        return frame[["id", name]]
    if "tvt" in frame.columns:
        frame = frame.rename(columns={"tvt": name})
    elif "final_pred" in frame.columns:
        frame = frame.rename(columns={"final_pred": name})
    elif "baseline_tvt" in frame.columns:
        frame = frame.rename(columns={"baseline_tvt": name})
    else:
        raise ValueError(f"{path} must contain either tvt or final_pred")
    return frame[["id", name]]


def load_oof(path: Path, name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string", "well": "string"})
    if "final_pred" not in frame.columns:
        raise ValueError(f"{path} must contain final_pred")
    return frame[["id", "well", "truth_tvt", "final_pred"]].rename(columns={"final_pred": name})


def load_baseline_oof(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string"})
    if "baseline_tvt" not in frame.columns or "truth_tvt" not in frame.columns:
        raise ValueError(f"{path} must contain baseline_tvt and truth_tvt")
    frame["well"] = frame["id"].str.rsplit("_", n=1).str[0]
    return frame[["id", "well", "truth_tvt", "baseline_tvt"]]


def load_diagnostics(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, dtype={"well": "string"})


def split_diagnostics(diagnostics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = diagnostics.copy()
    if "split" not in frame.columns:
        frame["split"] = "train"
    frame["split"] = frame["split"].fillna("train")
    train = frame[frame["split"].ne("test")].drop_duplicates("well", keep="last").copy()
    test = frame[frame["split"].eq("test")].drop_duplicates("well", keep="last").copy()
    return train, test


def clip_series(series: pd.Series, lower: float, upper: float) -> pd.Series:
    return series.clip(lower=lower, upper=upper)


def safe_rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(mean_squared_error(y_true.to_numpy(dtype=float), y_pred.to_numpy(dtype=float)) ** 0.5)


def markdown_table(frame: pd.DataFrame, index: bool = False) -> str:
    try:
        return frame.to_markdown(index=index)
    except ImportError:
        return frame.to_string(index=index)


def weighted_avg(frame: pd.DataFrame, cols: list[str], weights: dict[str, float]) -> pd.Series:
    total = np.zeros(len(frame), dtype=float)
    norm = np.zeros(len(frame), dtype=float)
    for col in cols:
        w = float(weights.get(col, 0.0))
        if w <= 0.0:
            continue
        total += w * frame[col].to_numpy(dtype=float)
        norm += w
    norm = np.where(norm > 0, norm, 1.0)
    return pd.Series(total / norm, index=frame.index)


def blend_by_weight(frame: pd.DataFrame, geometry_weight: float) -> pd.Series:
    weight = float(np.clip(geometry_weight, 0.0, 1.0))
    baseline = frame["baseline_tvt"].to_numpy(dtype=float)
    geometry = frame["geometry_tvt"].to_numpy(dtype=float)
    return pd.Series((1.0 - weight) * baseline + weight * geometry, index=frame.index)


def best_weight_for(group: pd.DataFrame, grid: np.ndarray) -> tuple[float, float]:
    truth = group["truth_tvt"].to_numpy(dtype=float)
    baseline = group["baseline_tvt"].to_numpy(dtype=float)
    geometry = group["geometry_tvt"].to_numpy(dtype=float)
    best_weight = 0.0
    best_rmse = float("inf")
    for weight in grid:
        pred = (1.0 - weight) * baseline + weight * geometry
        rmse = float(np.sqrt(np.mean((pred - truth) ** 2)))
        if rmse < best_rmse:
            best_rmse = rmse
            best_weight = float(weight)
    return best_weight, best_rmse


def search_route_weights(oof_frame: pd.DataFrame, grid_step: float) -> tuple[dict[str, float], pd.DataFrame]:
    if grid_step <= 0 or grid_step > 1:
        raise ValueError("--weight-grid-step must be in (0, 1]")
    grid = np.round(np.arange(0.0, 1.0 + grid_step / 2.0, grid_step), 6)
    global_weight, global_rmse = best_weight_for(oof_frame, grid)
    rows = [
        {
            "route": "__global__",
            "rows": len(oof_frame),
            "geometry_weight": global_weight,
            "rmse": global_rmse,
        }
    ]
    weights: dict[str, float] = {"__default__": global_weight}
    for route, group in oof_frame.groupby(oof_frame["route"].fillna("baseline_fallback"), dropna=False):
        route_name = str(route)
        weight, rmse = best_weight_for(group, grid)
        weights[route_name] = weight
        rows.append(
            {
                "route": route_name,
                "rows": len(group),
                "geometry_weight": weight,
                "rmse": rmse,
            }
        )
    return weights, pd.DataFrame(rows)


def build_variant(frame: pd.DataFrame, variant: str, route_weights: dict[str, float] | None = None) -> pd.Series:
    baseline = frame["baseline_tvt"]
    geometry = frame["geometry_tvt"]
    route = frame["route"].fillna("baseline_fallback")
    confidence = frame["confidence"].fillna(0.5)
    disagreement = frame["disagreement"].fillna(0.0)

    if variant == "conservative":
        blended = np.where(
            confidence >= 0.7,
            0.8 * baseline + 0.2 * geometry,
            baseline,
        )
        blended = np.where(disagreement > 0.75, baseline, blended)
    elif variant == "balanced":
        route_weight = {
            "typewell_alignment": 0.72,
            "gr_residual": 0.62,
            "geometry_residual": 0.55,
            "baseline_fallback": 0.18,
        }
        local = route.map(route_weight).fillna(0.45).to_numpy(dtype=float)
        blended = (1.0 - local) * baseline.to_numpy(dtype=float) + local * geometry.to_numpy(dtype=float)
    elif variant == "aggressive":
        route_weight = {
            "typewell_alignment": 0.92,
            "gr_residual": 0.78,
            "geometry_residual": 0.64,
            "baseline_fallback": 0.24,
        }
        local = route.map(route_weight).fillna(0.6).to_numpy(dtype=float)
        uplift = np.where(confidence >= 0.7, 0.15 * (geometry.to_numpy(dtype=float) - baseline.to_numpy(dtype=float)), 0.0)
        blended = (1.0 - local) * baseline.to_numpy(dtype=float) + local * geometry.to_numpy(dtype=float) + uplift
        blended = np.where(disagreement > 1.0, 0.5 * baseline.to_numpy(dtype=float) + 0.5 * geometry.to_numpy(dtype=float), blended)
    elif variant == "optimized":
        if route_weights is None:
            raise ValueError("optimized variant requires route_weights")
        default_weight = float(route_weights.get("__default__", 0.5))
        local = route.map(route_weights).fillna(default_weight).to_numpy(dtype=float)
        blended = (1.0 - local) * baseline.to_numpy(dtype=float) + local * geometry.to_numpy(dtype=float)
    else:
        raise ValueError(f"Unknown variant: {variant}")
    return pd.Series(blended, index=frame.index)


def build_submission_frame(ids: pd.Index, preds: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"id": ids.to_numpy(), "tvt": preds.to_numpy(dtype=float)})


def validate_submission(df: pd.DataFrame, sample: pd.DataFrame) -> None:
    if list(df.columns) != ["id", "tvt"]:
        raise ValueError("submission must have exactly id,tvt columns")
    if len(df) != len(sample):
        raise ValueError(f"submission row count mismatch: {len(df)} != {len(sample)}")
    if df["id"].duplicated().any():
        raise ValueError("submission contains duplicated ids")
    if not df["id"].equals(sample["id"]):
        raise ValueError("submission ids are not in the same order as sample submission")
    if not np.isfinite(df["tvt"].to_numpy(dtype=float)).all():
        raise ValueError("submission contains NaN or inf")


def main() -> int:
    parser = argparse.ArgumentParser(description="Blend validated submission variants.")
    parser.add_argument("--geometry-weight", type=float, default=0.65)
    parser.add_argument("--baseline-weight", type=float, default=0.35)
    parser.add_argument("--weight-grid-step", type=float, default=0.05)
    parser.add_argument("--clip-lower", type=float, default=9000.0)
    parser.add_argument("--clip-upper", type=float, default=13000.0)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    SUBMISSION_DIR.mkdir(exist_ok=True)

    baseline_test = load_predictions(OUTPUT_DIR / "baseline_predictions_test.csv", "baseline_tvt")
    geometry_test = load_predictions(OUTPUT_DIR / "residual_geometry_test_predictions.csv", "geometry_tvt")
    diag = load_diagnostics(OUTPUT_DIR / "part3_diagnostics.csv").rename(columns={"route_suggestion": "route"})
    diag_train, diag_test = split_diagnostics(diag)
    oof_baseline = load_baseline_oof(OUTPUT_DIR / "baseline_predictions_train_hidden.csv")
    oof_geometry = load_oof(OUTPUT_DIR / "residual_geometry_oof.csv", "geometry_tvt")

    sample = load_sample_submission()[["id"]].copy()

    test_frame = sample.merge(baseline_test, on="id", how="left", validate="one_to_one")
    test_frame = test_frame.merge(geometry_test, on="id", how="left", validate="one_to_one")
    test_wells = test_frame["id"].str.split("_", n=1).str[0]
    test_route_map = diag_test.set_index("well")["route"].to_dict()
    train_route_map = diag_train.set_index("well")["route"].to_dict()
    test_frame["route"] = test_wells.map(test_route_map).fillna(test_wells.map(train_route_map))
    test_frame["confidence"] = test_frame["route"].map(ROUTE_CONFIDENCE).fillna(0.5)
    test_frame["geometry_tvt"] = test_frame["geometry_tvt"].fillna(test_frame["baseline_tvt"])
    test_frame["disagreement"] = (test_frame["geometry_tvt"] - test_frame["baseline_tvt"]).abs()
    oof_frame = oof_baseline.merge(oof_geometry, on=["id", "well"], how="inner", validate="one_to_one", suffixes=("_baseline", "_geometry"))
    mismatch = (oof_frame["truth_tvt_baseline"] - oof_frame["truth_tvt_geometry"]).abs().max()
    if pd.notna(mismatch) and mismatch > 1e-6:
        raise ValueError(f"OOF truth mismatch between baseline and geometry inputs: {mismatch}")
    oof_frame["truth_tvt"] = oof_frame["truth_tvt_baseline"]
    oof_frame = oof_frame.drop(columns=["truth_tvt_baseline", "truth_tvt_geometry"])
    oof_frame = oof_frame.merge(diag_train[["well", "route"]], on="well", how="left", validate="many_to_one")
    oof_frame["confidence"] = oof_frame["route"].map(ROUTE_CONFIDENCE).fillna(0.5)
    oof_frame["geometry_tvt"] = oof_frame["geometry_tvt"].fillna(oof_frame["baseline_tvt"])
    oof_frame["disagreement"] = (oof_frame["geometry_tvt"] - oof_frame["baseline_tvt"]).abs()

    route_weights, route_weight_report = search_route_weights(oof_frame, args.weight_grid_step)

    for variant in BLEND_VARIANTS:
        test_frame[f"{variant}_tvt"] = build_variant(test_frame, variant, route_weights=route_weights)
        oof_frame[f"{variant}_tvt"] = build_variant(oof_frame, variant, route_weights=route_weights)

    for col in [f"{variant}_tvt" for variant in BLEND_VARIANTS]:
        test_frame[col] = clip_series(test_frame[col], args.clip_lower, args.clip_upper)
        oof_frame[col] = clip_series(oof_frame[col], args.clip_lower, args.clip_upper)

    # Baseline and geometry OOF already measure different targets; compute comparison against truth.
    cv_rows = [
        {"variant": "baseline", "rmse": safe_rmse(oof_frame["truth_tvt"], oof_frame["baseline_tvt"])},
        {"variant": "geometry", "rmse": safe_rmse(oof_frame["truth_tvt"], oof_frame["geometry_tvt"])},
    ]
    cv_rows.extend(
        {"variant": variant, "rmse": safe_rmse(oof_frame["truth_tvt"], oof_frame[f"{variant}_tvt"])}
        for variant in BLEND_VARIANTS
    )
    cv_summary = pd.DataFrame(cv_rows).sort_values("rmse", kind="mergesort").reset_index(drop=True)

    conservative_submission = build_submission_frame(sample["id"], test_frame["conservative_tvt"])
    balanced_submission = build_submission_frame(sample["id"], test_frame["balanced_tvt"])
    aggressive_submission = build_submission_frame(sample["id"], test_frame["aggressive_tvt"])
    optimized_submission = build_submission_frame(sample["id"], test_frame["optimized_tvt"])

    validate_submission(conservative_submission, sample)
    validate_submission(balanced_submission, sample)
    validate_submission(aggressive_submission, sample)
    validate_submission(optimized_submission, sample)

    conservative_submission.to_csv(SUBMISSION_DIR / "conservative_submission.csv", index=False)
    balanced_submission.to_csv(SUBMISSION_DIR / "balanced_submission.csv", index=False)
    aggressive_submission.to_csv(SUBMISSION_DIR / "aggressive_submission.csv", index=False)
    optimized_submission.to_csv(SUBMISSION_DIR / "optimized_submission.csv", index=False)

    oof_frame.to_csv(OUTPUT_DIR / "blend_oof.csv", index=False)
    oof_frame[
        [
            "id",
            "well",
            "route",
            "confidence",
            "disagreement",
            "baseline_tvt",
            "geometry_tvt",
            "conservative_tvt",
            "balanced_tvt",
            "aggressive_tvt",
            "optimized_tvt",
        ]
    ].to_csv(
        OUTPUT_DIR / "blend_cv_by_well.csv", index=False
    )
    cv_summary.to_csv(OUTPUT_DIR / "ensemble_cv_summary.csv", index=False)
    route_weight_report.to_csv(OUTPUT_DIR / "ensemble_route_weights.csv", index=False)

    manifest = {
        "model_members": ["baseline_tail_slope", "geometry_residual", "part3_router"],
        "weights": {
            "baseline": args.baseline_weight,
            "geometry": args.geometry_weight,
        },
        "optimized_route_weights": route_weights,
        "clip_lower": args.clip_lower,
        "clip_upper": args.clip_upper,
        "routes": test_frame["route"].value_counts(dropna=False).to_dict(),
        "row_count": int(len(test_frame)),
        "selected_by_oof": cv_summary.iloc[0].to_dict(),
    }
    (OUTPUT_DIR / "submission_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = [
        "# Ensemble Report",
        "",
        "## CV Summary",
        "",
        markdown_table(cv_summary.round(4), index=False),
        "",
        "## Optimized Route Weights",
        "",
        markdown_table(route_weight_report.round(4), index=False),
        "",
        "## Test Routing",
        "",
        markdown_table(test_frame["route"].value_counts(dropna=False).rename("count").to_frame(), index=True),
        "",
        "## Submission Files",
        "",
        "- `submissions/conservative_submission.csv`",
        "- `submissions/balanced_submission.csv`",
        "- `submissions/aggressive_submission.csv`",
        "- `submissions/optimized_submission.csv`",
    ]
    (REPORT_DIR / "ensemble_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("Wrote ensemble submissions and manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
