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


def clip_series(series: pd.Series, lower: float, upper: float) -> pd.Series:
    return series.clip(lower=lower, upper=upper)


def safe_rmse(y_true: pd.Series, y_pred: pd.Series) -> float:
    return float(mean_squared_error(y_true.to_numpy(dtype=float), y_pred.to_numpy(dtype=float)) ** 0.5)


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


def build_variant(frame: pd.DataFrame, variant: str) -> pd.Series:
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
    parser.add_argument("--clip-lower", type=float, default=9000.0)
    parser.add_argument("--clip-upper", type=float, default=13000.0)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    SUBMISSION_DIR.mkdir(exist_ok=True)

    baseline_test = load_predictions(OUTPUT_DIR / "baseline_predictions_test.csv", "baseline_tvt")
    geometry_test = load_predictions(OUTPUT_DIR / "residual_geometry_test_predictions.csv", "geometry_tvt")
    diag = load_diagnostics(OUTPUT_DIR / "part3_diagnostics.csv").rename(columns={"route_suggestion": "route"})
    oof_baseline = load_baseline_oof(OUTPUT_DIR / "baseline_predictions_train_hidden.csv")
    oof_geometry = load_oof(OUTPUT_DIR / "residual_geometry_oof.csv", "geometry_tvt")

    sample = load_sample_submission()[["id"]].copy()

    test_frame = sample.merge(baseline_test, on="id", how="left", validate="one_to_one")
    test_frame = test_frame.merge(geometry_test, on="id", how="left", validate="one_to_one")
    test_frame["route"] = test_frame["id"].str.split("_", n=1).str[0].map(diag.set_index("well")["route"].to_dict())
    test_frame["confidence"] = test_frame["route"].map(ROUTE_CONFIDENCE).fillna(0.5)
    test_frame["geometry_tvt"] = test_frame["geometry_tvt"].fillna(test_frame["baseline_tvt"])
    test_frame["disagreement"] = (test_frame["geometry_tvt"] - test_frame["baseline_tvt"]).abs()
    test_frame["balanced_tvt"] = args.baseline_weight * test_frame["baseline_tvt"] + args.geometry_weight * test_frame["geometry_tvt"]

    test_frame["conservative_tvt"] = build_variant(test_frame, "conservative")
    test_frame["balanced_tvt"] = build_variant(test_frame, "balanced")
    test_frame["aggressive_tvt"] = build_variant(test_frame, "aggressive")

    for col in ["conservative_tvt", "balanced_tvt", "aggressive_tvt"]:
        test_frame[col] = clip_series(test_frame[col], args.clip_lower, args.clip_upper)

    oof_frame = oof_baseline.merge(oof_geometry, on=["id", "well"], how="inner", validate="one_to_one", suffixes=("_baseline", "_geometry"))
    mismatch = (oof_frame["truth_tvt_baseline"] - oof_frame["truth_tvt_geometry"]).abs().max()
    if pd.notna(mismatch) and mismatch > 1e-6:
        raise ValueError(f"OOF truth mismatch between baseline and geometry inputs: {mismatch}")
    oof_frame["truth_tvt"] = oof_frame["truth_tvt_baseline"]
    oof_frame = oof_frame.drop(columns=["truth_tvt_baseline", "truth_tvt_geometry"])
    oof_frame = oof_frame.merge(diag[["well", "route"]], on="well", how="left")
    oof_frame["confidence"] = oof_frame["route"].map(ROUTE_CONFIDENCE).fillna(0.5)
    oof_frame["geometry_tvt"] = oof_frame["geometry_tvt"].fillna(oof_frame["baseline_tvt"])
    oof_frame["disagreement"] = (oof_frame["geometry_tvt"] - oof_frame["baseline_tvt"]).abs()
    oof_frame["balanced_tvt"] = args.baseline_weight * oof_frame["baseline_tvt"] + args.geometry_weight * oof_frame["geometry_tvt"]
    oof_frame["conservative_tvt"] = build_variant(oof_frame, "conservative")
    oof_frame["aggressive_tvt"] = build_variant(oof_frame, "aggressive")
    oof_frame["balanced_tvt"] = build_variant(oof_frame, "balanced")
    for col in ["conservative_tvt", "balanced_tvt", "aggressive_tvt"]:
        oof_frame[col] = clip_series(oof_frame[col], args.clip_lower, args.clip_upper)

    # Baseline and geometry OOF already measure different targets; compute comparison against truth.
    cv_summary = pd.DataFrame(
        [
            {"variant": "baseline", "rmse": safe_rmse(oof_frame["truth_tvt"], oof_frame["baseline_tvt"])},
            {"variant": "geometry", "rmse": safe_rmse(oof_frame["truth_tvt"], oof_frame["geometry_tvt"])},
            {"variant": "balanced", "rmse": safe_rmse(oof_frame["truth_tvt"], oof_frame["balanced_tvt"])},
            {"variant": "conservative", "rmse": safe_rmse(oof_frame["truth_tvt"], oof_frame["conservative_tvt"])},
            {"variant": "aggressive", "rmse": safe_rmse(oof_frame["truth_tvt"], oof_frame["aggressive_tvt"])},
        ]
    )

    conservative_submission = build_submission_frame(sample["id"], test_frame["conservative_tvt"])
    balanced_submission = build_submission_frame(sample["id"], test_frame["balanced_tvt"])
    aggressive_submission = build_submission_frame(sample["id"], test_frame["aggressive_tvt"])

    validate_submission(conservative_submission, sample)
    validate_submission(balanced_submission, sample)
    validate_submission(aggressive_submission, sample)

    conservative_submission.to_csv(SUBMISSION_DIR / "conservative_submission.csv", index=False)
    balanced_submission.to_csv(SUBMISSION_DIR / "balanced_submission.csv", index=False)
    aggressive_submission.to_csv(SUBMISSION_DIR / "aggressive_submission.csv", index=False)

    oof_frame.to_csv(OUTPUT_DIR / "blend_oof.csv", index=False)
    oof_frame[["id", "well", "route", "confidence", "disagreement", "baseline_tvt", "geometry_tvt", "conservative_tvt", "balanced_tvt", "aggressive_tvt"]].to_csv(
        OUTPUT_DIR / "blend_cv_by_well.csv", index=False
    )

    manifest = {
        "model_members": ["baseline_tail_slope", "geometry_residual", "part3_router"],
        "weights": {
            "baseline": args.baseline_weight,
            "geometry": args.geometry_weight,
        },
        "clip_lower": args.clip_lower,
        "clip_upper": args.clip_upper,
        "routes": test_frame["route"].value_counts(dropna=False).to_dict(),
        "row_count": int(len(test_frame)),
    }
    (OUTPUT_DIR / "submission_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = [
        "# Ensemble Report",
        "",
        "## CV Summary",
        "",
        cv_summary.round(4).to_markdown(index=False),
        "",
        "## Test Routing",
        "",
        test_frame["route"].value_counts(dropna=False).rename("count").to_frame().to_markdown(),
        "",
        "## Submission Files",
        "",
        "- `submissions/conservative_submission.csv`",
        "- `submissions/balanced_submission.csv`",
        "- `submissions/aggressive_submission.csv`",
    ]
    (REPORT_DIR / "ensemble_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("Wrote ensemble submissions and manifest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
