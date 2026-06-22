#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from part2_utils import FEATURE_DIR, OUTPUT_DIR, REPORT_DIR, ROOT, data_hash_short
from rogii_utils import regression_metrics


GEOMETRY_OOF_PATH = OUTPUT_DIR / "residual_geometry_oof.csv"
RESIDUAL_TARGETS_PATH = FEATURE_DIR / "residual_targets.csv"
LEFTOVER_PATH = FEATURE_DIR / "leftover_targets.csv"
REPORT_PATH = REPORT_DIR / "leftover_target_report.md"


def main() -> int:
    FEATURE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)

    if not GEOMETRY_OOF_PATH.exists():
        raise FileNotFoundError(
            f"{GEOMETRY_OOF_PATH} is missing; run scripts/train_residual_model.py --spec geometry first"
        )
    if not RESIDUAL_TARGETS_PATH.exists():
        raise FileNotFoundError(
            f"{RESIDUAL_TARGETS_PATH} is missing; run scripts/build_baseline_features.py first"
        )

    geometry = pd.read_csv(
        GEOMETRY_OOF_PATH,
        dtype={"id": "string", "well": "string", "split": "string"},
    )
    targets = pd.read_csv(
        RESIDUAL_TARGETS_PATH,
        dtype={"id": "string", "well": "string", "split": "string"},
    )

    required_geometry = {"id", "well", "split", "row", "truth_tvt", "baseline_tvt", "oof_residual_pred"}
    missing_geometry = required_geometry - set(geometry.columns)
    if missing_geometry:
        raise ValueError(f"{GEOMETRY_OOF_PATH} missing columns: {sorted(missing_geometry)}")

    frame = targets.merge(
        geometry[
            [
                "id",
                "oof_residual_pred",
            ]
        ].rename(columns={"oof_residual_pred": "geometry_oof_residual"}),
        on="id",
        how="inner",
        validate="one_to_one",
    )
    if len(frame) != len(targets):
        raise ValueError(
            f"leftover target merge dropped rows: targets={len(targets)} merged={len(frame)}"
        )

    truth = frame["truth_tvt"].to_numpy(dtype=float)
    baseline = frame["baseline_tvt"].to_numpy(dtype=float)
    geometry_residual = frame["geometry_oof_residual"].to_numpy(dtype=float)
    frame["geometry_pred_tvt"] = baseline + geometry_residual
    frame["leftover_target"] = truth - frame["geometry_pred_tvt"]
    frame["abs_geometry_residual"] = np.abs(geometry_residual)
    frame["abs_leftover_target"] = np.abs(frame["leftover_target"])

    out_cols = [
        "well",
        "split",
        "row",
        "id",
        "truth_tvt",
        "baseline_tvt",
        "residual_target",
        "geometry_oof_residual",
        "geometry_pred_tvt",
        "leftover_target",
        "abs_geometry_residual",
        "abs_leftover_target",
    ]
    frame[out_cols].to_csv(LEFTOVER_PATH, index=False)

    residual_metrics = regression_metrics(frame["residual_target"], np.zeros(len(frame)))
    leftover_metrics = regression_metrics(frame["leftover_target"], np.zeros(len(frame)))
    geometry_metrics = regression_metrics(truth, frame["geometry_pred_tvt"])

    report = {
        "data_hash": data_hash_short(),
        "rows": int(len(frame)),
        "wells": int(frame["well"].nunique()),
        "source_geometry_oof": str(GEOMETRY_OOF_PATH.relative_to(ROOT)),
        "residual_target_std": float(frame["residual_target"].std()),
        "leftover_target_std": float(frame["leftover_target"].std()),
        "geometry_oof_rmse": geometry_metrics["rmse"],
        "leftover_target_mean_abs": float(frame["abs_leftover_target"].mean()),
    }
    lines = [
        "# Leftover Target Report",
        "",
        "Fold-safe leftover targets are built from geometry **OOF** residuals only.",
        "",
        "```text",
        "leftover_target = truth_tvt - (baseline_tvt + geometry_oof_residual)",
        "```",
        "",
        "## Summary",
        "",
        pd.DataFrame([report]).T.rename(columns={0: "value"}).to_markdown(),
        "",
        "## Metrics",
        "",
        "| target | rmse | mae | p95_abs_error |",
        "|:---|---:|---:|---:|",
        f"| residual_target | {residual_metrics['rmse']:.4f} | {residual_metrics['mae']:.4f} | {residual_metrics['p95_abs_error']:.4f} |",
        f"| geometry_oof | {geometry_metrics['rmse']:.4f} | {geometry_metrics['mae']:.4f} | {geometry_metrics['p95_abs_error']:.4f} |",
        f"| leftover_target | {leftover_metrics['rmse']:.4f} | {leftover_metrics['mae']:.4f} | {leftover_metrics['p95_abs_error']:.4f} |",
        "",
        f"- Output: `{LEFTOVER_PATH.relative_to(ROOT)}`",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote {LEFTOVER_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"rows={len(frame)} wells={frame['well'].nunique()} leftover_std={frame['leftover_target'].std():.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())