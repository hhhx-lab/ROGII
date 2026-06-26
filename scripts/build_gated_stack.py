#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from part2_utils import MODEL_DIR, OUTPUT_DIR, REPORT_DIR, ROOT, data_hash_short
from rogii_utils import regression_metrics


ALPHA_BY_WELL_PATH = OUTPUT_DIR / "gated_alpha_by_well.csv"
GEOMETRY_OOF_PATH = OUTPUT_DIR / "residual_geometry_oof.csv"
XGB_LEFTOVER_OOF_PATH = OUTPUT_DIR / "residual_xgb_leftover_oof.csv"
XGB_LEFTOVER_TEST_PATH = OUTPUT_DIR / "residual_xgb_leftover_test_predictions.csv"
OOF_PATH = OUTPUT_DIR / "gated_geometry_plus_xgb_leftover_oof.csv"
TEST_PATH = OUTPUT_DIR / "gated_geometry_plus_xgb_leftover_test_predictions.csv"
SUBMISSION_PATH = ROOT / "submissions" / "gated_geometry_plus_xgb_leftover_submission.csv"
CONFIG_PATH = MODEL_DIR / "gated_geometry_plus_xgb_leftover_config.json"
CV_BY_WELL_PATH = OUTPUT_DIR / "gated_geometry_plus_xgb_leftover_cv_by_well.csv"
REPORT_PATH = REPORT_DIR / "gated_geometry_plus_xgb_leftover_cv_report.md"


def load_alpha_table() -> pd.DataFrame:
    if not ALPHA_BY_WELL_PATH.exists():
        raise FileNotFoundError(
            f"{ALPHA_BY_WELL_PATH} is missing; run scripts/build_gated_geometry.py first"
        )
    return pd.read_csv(ALPHA_BY_WELL_PATH, dtype={"well": "string"})


def load_geometry_oof() -> pd.DataFrame:
    frame = pd.read_csv(GEOMETRY_OOF_PATH, dtype={"id": "string", "well": "string"})
    required = {"id", "well", "truth_tvt", "baseline_tvt", "oof_residual_pred"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{GEOMETRY_OOF_PATH} missing columns: {sorted(missing)}")
    return frame


def load_xgb_leftover_oof() -> pd.DataFrame:
    if not XGB_LEFTOVER_OOF_PATH.exists():
        raise FileNotFoundError(
            f"{XGB_LEFTOVER_OOF_PATH} is missing; run scripts/train_residual_model.py --spec xgb_leftover first"
        )
    frame = pd.read_csv(XGB_LEFTOVER_OOF_PATH, dtype={"id": "string", "well": "string"})
    if "oof_residual_pred" not in frame.columns:
        raise ValueError(f"{XGB_LEFTOVER_OOF_PATH} must contain oof_residual_pred")
    return frame[["id", "well", "oof_residual_pred"]].rename(columns={"oof_residual_pred": "xgb_leftover_pred"})


def apply_stack(oof: pd.DataFrame, alpha_table: pd.DataFrame) -> pd.DataFrame:
    alpha_map = alpha_table.set_index("well")["alpha"].to_dict()
    out = oof.copy()
    out["alpha"] = out["well"].map(alpha_map).fillna(1.0).astype(float)
    out["combined_residual"] = out["geometry_residual"] + out["xgb_leftover_pred"]
    out["gated_residual"] = out["alpha"] * out["combined_residual"]
    out["final_pred"] = out["baseline_tvt"] + out["gated_residual"]
    out["abs_error"] = (out["final_pred"] - out["truth_tvt"]).abs()
    return out


def build_test(alpha_table: pd.DataFrame) -> pd.DataFrame:
    baseline_test = pd.read_csv(OUTPUT_DIR / "baseline_predictions_test.csv", dtype={"id": "string"})
    geometry_test = pd.read_csv(OUTPUT_DIR / "residual_geometry_test_predictions.csv", dtype={"id": "string"})
    xgb_test = pd.read_csv(XGB_LEFTOVER_TEST_PATH, dtype={"id": "string"})

    if "tvt" in geometry_test.columns:
        geometry_test = geometry_test.rename(columns={"tvt": "geometry_pred"})
    else:
        geometry_test = geometry_test.rename(columns={"final_pred": "geometry_pred"})
    if "tvt" in xgb_test.columns:
        xgb_test = xgb_test.rename(columns={"tvt": "xgb_leftover_pred"})
    else:
        xgb_test = xgb_test.rename(columns={"final_pred": "xgb_leftover_pred"})

    frame = baseline_test.merge(geometry_test[["id", "geometry_pred"]], on="id", how="left", validate="one_to_one")
    frame = frame.merge(xgb_test[["id", "xgb_leftover_pred"]], on="id", how="left", validate="one_to_one")
    frame["well"] = frame["id"].str.rsplit("_", n=1).str[0]
    alpha_map = alpha_table.set_index("well")["alpha"].to_dict()
    frame["alpha"] = frame["well"].map(alpha_map).fillna(1.0).astype(float)
    frame["geometry_residual"] = frame["geometry_pred"] - frame["baseline_tvt"]
    frame["combined_residual"] = frame["geometry_residual"] + frame["xgb_leftover_pred"]
    frame["gated_residual"] = frame["alpha"] * frame["combined_residual"]
    frame["final_pred"] = frame["baseline_tvt"] + frame["gated_residual"]
    return frame


def per_well_cv(oof: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for well, group in oof.groupby("well", sort=True):
        err = group["final_pred"].to_numpy(dtype=float) - group["truth_tvt"].to_numpy(dtype=float)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build alpha-gated geometry + xgb leftover stack candidate.")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    SUBMISSION_PATH.parent.mkdir(exist_ok=True)

    alpha_table = load_alpha_table()
    geometry_oof = load_geometry_oof()
    xgb_oof = load_xgb_leftover_oof()
    oof = geometry_oof.merge(xgb_oof, on=["id", "well"], how="inner", validate="one_to_one")
    oof = oof.rename(columns={"oof_residual_pred": "geometry_residual"})
    stacked_oof = apply_stack(oof, alpha_table)
    test_frame = build_test(alpha_table)
    cv_by_well = per_well_cv(stacked_oof)

    stacked_oof[
        [
            "well",
            "id",
            "truth_tvt",
            "baseline_tvt",
            "geometry_residual",
            "xgb_leftover_pred",
            "alpha",
            "combined_residual",
            "gated_residual",
            "final_pred",
            "abs_error",
        ]
    ].to_csv(OOF_PATH, index=False)
    test_frame[["id", "final_pred"]].rename(columns={"final_pred": "tvt"}).to_csv(TEST_PATH, index=False)
    test_frame[["id", "final_pred"]].rename(columns={"final_pred": "tvt"}).to_csv(SUBMISSION_PATH, index=False)
    cv_by_well.to_csv(CV_BY_WELL_PATH, index=False)

    gated_geometry_oof = None
    gated_geometry_path = OUTPUT_DIR / "gated_geometry_oof.csv"
    if gated_geometry_path.exists():
        gated_geometry_oof = pd.read_csv(gated_geometry_path)

    metrics = regression_metrics(stacked_oof["truth_tvt"], stacked_oof["final_pred"])
    config = {
        "model_name": "gated_geometry_plus_xgb_leftover",
        "model_family": "gated_stack",
        "model_backend": "per_well_alpha_grid",
        "candidate_type": "oracle_gated_stack",
        "oracle_candidate": True,
        "diagnostic_only": True,
        "eligible_for_auto_submission": False,
        "eligibility_reason": "stack reuses per-well oracle alpha from gated_geometry; use learned_gated_geometry or another validated candidate for auto submission",
        "data_hash": data_hash_short(),
        "formula": "baseline + alpha * (geometry_residual + xgb_leftover_residual)",
        "metrics": metrics,
        "train_rows": int(len(stacked_oof)),
        "fit_rows": int(len(stacked_oof)),
        "fit_fraction": 1.0,
        "alpha_source": str(ALPHA_BY_WELL_PATH.relative_to(ROOT)),
        "geometry_source": str(GEOMETRY_OOF_PATH.relative_to(ROOT)),
        "xgb_leftover_source": str(XGB_LEFTOVER_OOF_PATH.relative_to(ROOT)),
    }
    if gated_geometry_oof is not None:
        config["gated_geometry_metrics"] = regression_metrics(
            gated_geometry_oof["truth_tvt"], gated_geometry_oof["final_pred"]
        )
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Gated Geometry + XGB Leftover CV Report",
        "",
        "- Candidate type: `oracle_gated_stack`",
        "- Eligible for auto submission: `False`",
        "",
        "Important: this stack reuses the per-well oracle alpha from `gated_geometry`. It is useful for diagnostics, but it is not a default auto-submission candidate.",
        "",
        "```text",
        "final_tvt = baseline_tvt + alpha * (geometry_residual + xgb_leftover_residual)",
        "```",
        "",
        "## Overall Metrics",
        "",
        f"- Stack RMSE: `{metrics['rmse']:.4f}`",
        f"- Stack MAE: `{metrics['mae']:.4f}`",
        f"- Stack P95: `{metrics['p95_abs_error']:.4f}`",
        f"- Rows: `{len(stacked_oof):,}`",
        f"- Wells: `{stacked_oof['well'].nunique()}`",
        "",
        "## Outputs",
        "",
        f"- `{OOF_PATH.relative_to(ROOT)}`",
        f"- `{SUBMISSION_PATH.relative_to(ROOT)}`",
    ]
    if "gated_geometry_metrics" in config:
        gm = config["gated_geometry_metrics"]
        lines.extend(
            [
                "",
                "## Comparison",
                "",
                f"- gated_geometry RMSE: `{gm['rmse']:.4f}`",
                f"- stack RMSE: `{metrics['rmse']:.4f}`",
                f"- delta: `{gm['rmse'] - metrics['rmse']:.4f}`",
            ]
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {OOF_PATH}")
    print(f"Wrote {SUBMISSION_PATH}")
    print(f"Wrote {CONFIG_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"gated_stack rmse={metrics['rmse']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
