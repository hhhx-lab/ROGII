#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from part2_utils import FEATURE_DIR, MODEL_DIR, OUTPUT_DIR, REPORT_DIR, ROOT, env_int
from rogii_utils import TRAIN_DIR, assert_data_contract_ready, regression_metrics


OOF_PATH = OUTPUT_DIR / "residual_geometry_oof.csv"
CV_BY_WELL_PATH = OUTPUT_DIR / "residual_geometry_cv_by_well.csv"
ALPHA_PATH = OUTPUT_DIR / "residual_geometry_alpha_search.csv"
TEST_PRED_PATH = OUTPUT_DIR / "residual_geometry_test_predictions.csv"
MODEL_PATH = MODEL_DIR / "residual_geometry_hgb.pkl"
CONFIG_PATH = MODEL_DIR / "residual_geometry_config.json"
BASELINE_TRAIN_PATH = FEATURE_DIR / "baseline_features_train.parquet"
GEOMETRY_TRAIN_PATH = FEATURE_DIR / "geometry_features_train.parquet"
TARGET_PATH = FEATURE_DIR / "residual_targets.parquet"

CV_REPORT_PATH = REPORT_DIR / "residual_geometry_cv_report.md"
FAILURE_REPORT_PATH = REPORT_DIR / "residual_geometry_failure_analysis.md"
IMPORTANCE_REPORT_PATH = REPORT_DIR / "residual_geometry_feature_importance.md"
BEST_FIG_DIR = REPORT_DIR / "figures" / "residual_geometry_best_improved"
WORST_FIG_DIR = REPORT_DIR / "figures" / "residual_geometry_worst_degraded"


def rmse(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(values**2)))


def build_by_well(oof: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for well, frame in oof.groupby("well", sort=True):
        ordered = frame.sort_values("row")
        correction = ordered["selected_alpha"].to_numpy(dtype=float) * ordered["residual_pred_clipped"].to_numpy(dtype=float)
        jump = np.abs(np.diff(correction)) if len(correction) > 1 else np.asarray([0.0])
        baseline_error = frame["baseline_tvt"].to_numpy(dtype=float) - frame["true_tvt"].to_numpy(dtype=float)
        geometry_error = frame["geometry_pred_tvt"].to_numpy(dtype=float) - frame["true_tvt"].to_numpy(dtype=float)
        rows.append(
            {
                "well": well,
                "rows": len(frame),
                "baseline_rmse": rmse(baseline_error),
                "geometry_rmse": rmse(geometry_error),
                "rmse_improvement": rmse(baseline_error) - rmse(geometry_error),
                "baseline_mae": float(np.mean(np.abs(baseline_error))),
                "geometry_mae": float(np.mean(np.abs(geometry_error))),
                "baseline_bias": float(np.mean(baseline_error)),
                "geometry_bias": float(np.mean(geometry_error)),
                "residual_pred_mean": float(frame["residual_pred_clipped"].mean()),
                "residual_pred_std": float(frame["residual_pred_clipped"].std()),
                "max_residual_correction_jump": float(np.max(jump)) if len(jump) else 0.0,
                "target_rows": len(frame),
            }
        )
    out = pd.DataFrame(rows)
    out["improved"] = out["rmse_improvement"] > 0
    return out.sort_values("rmse_improvement")


def attach_oof_context(oof: pd.DataFrame) -> pd.DataFrame:
    columns = ["id", "target_rows_count", "target_gr_missing_rate", "baseline_confidence", "distance_row_from_last_known"]
    context = pd.read_parquet(BASELINE_TRAIN_PATH, columns=columns)
    return oof.merge(context, on="id", how="left", validate="one_to_one")


def summarize_bias(frame: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for value, part in frame.groupby(group_col, observed=True, dropna=False):
        baseline_error = part["baseline_tvt"].to_numpy(dtype=float) - part["true_tvt"].to_numpy(dtype=float)
        geometry_error = part["geometry_pred_tvt"].to_numpy(dtype=float) - part["true_tvt"].to_numpy(dtype=float)
        rows.append(
            {
                group_col: str(value),
                "rows": len(part),
                "wells": part["well"].nunique(),
                "baseline_bias": float(np.mean(baseline_error)),
                "geometry_bias": float(np.mean(geometry_error)),
                "baseline_rmse": rmse(baseline_error),
                "geometry_rmse": rmse(geometry_error),
                "rmse_improvement": rmse(baseline_error) - rmse(geometry_error),
            }
        )
    return pd.DataFrame(rows)


def diagnostic_tables(oof_context: pd.DataFrame, config: dict[str, object], by_well: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = oof_context["residual_pred_raw"].astype(float)
    clipped = oof_context["residual_pred_clipped"].astype(float)
    alpha = float(config.get("selected_alpha", 1.0))
    clip_abs = float(config.get("residual_clip_config", {}).get("clip_abs", np.nanmax(np.abs(clipped))))
    correction = alpha * clipped
    clip_table = pd.DataFrame(
        [
            {
                "residual_clip_abs": clip_abs,
                "raw_p01": raw.quantile(0.01),
                "raw_p99": raw.quantile(0.99),
                "clipped_p01": clipped.quantile(0.01),
                "clipped_p99": clipped.quantile(0.99),
                "extreme_raw_count": int((raw.abs() >= clip_abs).sum()),
                "max_abs_correction": float(np.max(np.abs(correction))),
                "max_per_well_correction_jump": by_well["max_residual_correction_jump"].max(),
                "p95_per_well_correction_jump": by_well["max_residual_correction_jump"].quantile(0.95),
            }
        ]
    )

    bias_frame = oof_context.copy()
    bias_frame["target_length_bucket"] = pd.cut(
        bias_frame["target_rows_count"],
        bins=[0, 500, 1500, 3000, 5000, np.inf],
        labels=["0-500", "501-1500", "1501-3000", "3001-5000", "5001+"],
        include_lowest=True,
    )
    bias_frame["confidence_bucket"] = pd.cut(
        bias_frame["baseline_confidence"],
        bins=[-0.001, 0.25, 0.50, 0.75, 1.0],
        labels=["0-25%", "25-50%", "50-75%", "75-100%"],
        include_lowest=True,
    )
    bias_frame["predicted_residual_bucket"] = pd.qcut(
        bias_frame["residual_pred_clipped"].rank(method="first"),
        q=5,
        labels=["q1_lowest", "q2", "q3", "q4", "q5_highest"],
    )
    return (
        clip_table,
        summarize_bias(bias_frame, "target_length_bucket"),
        summarize_bias(bias_frame, "confidence_bucket"),
        summarize_bias(bias_frame, "predicted_residual_bucket"),
    )


def metric_row(label: str, truth: np.ndarray, pred: np.ndarray) -> dict[str, object]:
    metrics = regression_metrics(truth, pred)
    return {"model": label, **metrics}


def plot_well(well: str, frame: pd.DataFrame, out_path: Path) -> None:
    df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
    rows = frame["row"].to_numpy(dtype=int)
    known_end = int(rows.min() - 1)

    fig, axes = plt.subplots(4, 1, figsize=(13, 12), constrained_layout=True)
    x_all = np.arange(len(df))
    axes[0].plot(x_all, df["TVT"], color="#222222", linewidth=1.0, label="TVT truth")
    axes[0].scatter(x_all[: known_end + 1], df.loc[:known_end, "TVT_input"], s=4, color="#2c7fb8", label="known TVT_input")
    axes[0].plot(rows, frame["baseline_tvt"], color="#d95f0e", linewidth=0.9, label="baseline")
    axes[0].plot(rows, frame["geometry_pred_tvt"], color="#1b9e77", linewidth=0.9, label="geometry residual")
    axes[0].axvspan(rows.min(), rows.max(), color="#fdd49e", alpha=0.25)
    axes[0].set_title(f"{well} | residual geometry vs baseline")
    axes[0].set_ylabel("TVT")
    axes[0].legend(loc="best", fontsize=8)

    axes[1].plot(rows, frame["residual_target"], color="#555555", linewidth=0.9, label="residual target")
    axes[1].plot(rows, frame["residual_pred_clipped"], color="#7570b3", linewidth=0.9, label="residual pred")
    axes[1].axhline(0, color="#999999", linewidth=0.6)
    axes[1].set_ylabel("Residual")
    axes[1].legend(loc="best", fontsize=8)

    axes[2].plot(rows, np.abs(frame["baseline_error"]), color="#d95f0e", linewidth=0.8, label="baseline abs error")
    axes[2].plot(rows, np.abs(frame["geometry_error"]), color="#1b9e77", linewidth=0.8, label="geometry abs error")
    axes[2].set_ylabel("Abs error")
    axes[2].legend(loc="best", fontsize=8)

    axes[3].plot(x_all, df["GR"], color="#4d4d4d", linewidth=0.8, label="GR")
    axes[3].axvspan(rows.min(), rows.max(), color="#fdd49e", alpha=0.25)
    axes[3].set_ylabel("GR")
    axes[3].set_xlabel("row")
    axes[3].legend(loc="best", fontsize=8)

    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def write_failure_report(oof: pd.DataFrame, by_well: pd.DataFrame) -> None:
    BEST_FIG_DIR.mkdir(parents=True, exist_ok=True)
    WORST_FIG_DIR.mkdir(parents=True, exist_ok=True)

    best = by_well.sort_values("rmse_improvement", ascending=False).head(10)
    worst = by_well.sort_values("rmse_improvement", ascending=True).head(10)
    status_summary = (
        by_well.assign(status=np.where(by_well["improved"], "improved", "degraded"))
        .groupby("status")
        .agg(
            wells=("well", "count"),
            mean_target_rows=("target_rows", "mean"),
            median_target_rows=("target_rows", "median"),
            mean_rmse_improvement=("rmse_improvement", "mean"),
            median_rmse_improvement=("rmse_improvement", "median"),
            mean_residual_pred_std=("residual_pred_std", "mean"),
            p95_residual_correction_jump=("max_residual_correction_jump", lambda x: float(np.quantile(x, 0.95))),
        )
        .reset_index()
    )
    for rank, row in enumerate(best.itertuples(index=False), start=1):
        plot_well(row.well, oof[oof["well"].eq(row.well)], BEST_FIG_DIR / f"{rank:02d}_{row.well}.png")
    for rank, row in enumerate(worst.itertuples(index=False), start=1):
        plot_well(row.well, oof[oof["well"].eq(row.well)], WORST_FIG_DIR / f"{rank:02d}_{row.well}.png")

    lines = [
        "# Residual Geometry Failure Analysis",
        "",
        "## Best Improved Wells",
        "",
        best.round(4).to_markdown(index=False),
        "",
        "## Worst Degraded Wells",
        "",
        worst.round(4).to_markdown(index=False),
        "",
        "## Improved vs Degraded Profile",
        "",
        status_summary.round(4).to_markdown(index=False),
        "",
        "## Diagnostic Figures",
        "",
        f"- Best improved: `{BEST_FIG_DIR.relative_to(ROOT)}`",
        f"- Worst degraded: `{WORST_FIG_DIR.relative_to(ROOT)}`",
        "",
        "## Engineering Notes",
        "",
        "- Positive `rmse_improvement` means residual geometry improved over the conservative baseline.",
        "- Worst degraded wells must be routed conservatively in Part 4 if geometry residual remains noisy.",
        "- This model intentionally excludes complex GR/typewell alignment; Part 3 should explain residual misses with geological signals.",
        "",
    ]
    FAILURE_REPORT_PATH.write_text("\n".join(lines))


def feature_importance(config: dict[str, object]) -> pd.DataFrame:
    csv_path = REPORT_DIR / "residual_geometry_hgb_feature_importance.csv"
    if csv_path.exists():
        importance = pd.read_csv(csv_path)
        if "importance" in importance.columns and "importance_mean" not in importance.columns:
            importance = importance.rename(columns={"importance": "importance_mean"})
        if "importance_std" not in importance.columns:
            importance["importance_std"] = 0.0
        return importance.sort_values("importance_mean", ascending=False)
    return pd.DataFrame(
        {
            "feature": list(config.get("feature_columns", [])),
            "importance_mean": 0.0,
            "importance_std": 0.0,
        }
    )


def main() -> int:
    assert_data_contract_ready()
    if not OOF_PATH.exists():
        raise FileNotFoundError("outputs/residual_geometry_oof.csv is missing; run scripts/train_residual_model.py first")
    config = json.loads(CONFIG_PATH.read_text())
    oof = pd.read_csv(OOF_PATH)
    oof_context = attach_oof_context(oof)
    truth = oof["true_tvt"].to_numpy(dtype=float)
    baseline_pred = oof["baseline_tvt"].to_numpy(dtype=float)
    geometry_pred = oof["geometry_pred_tvt"].to_numpy(dtype=float)

    overall = pd.DataFrame(
        [
            metric_row("baseline", truth, baseline_pred),
            metric_row("geometry_residual", truth, geometry_pred),
        ]
    )
    overall["selected_alpha"] = config["selected_alpha"]
    by_well = build_by_well(oof)
    by_well.to_csv(CV_BY_WELL_PATH, index=False)
    clip_table, bias_by_length, bias_by_confidence, bias_by_predicted_residual = diagnostic_tables(oof_context, config, by_well)
    alpha = pd.read_csv(ALPHA_PATH) if ALPHA_PATH.exists() else pd.DataFrame()

    improved_wells = int(by_well["improved"].sum())
    degraded_wells = int((~by_well["improved"]).sum())
    improvement = float(overall.loc[overall["model"].eq("baseline"), "rmse"].iloc[0] - overall.loc[overall["model"].eq("geometry_residual"), "rmse"].iloc[0])
    promotion = "PROMOTE_TO_PART3_INPUT" if improvement > 0 and improved_wells >= degraded_wells else "KEEP_AS_EXPERIMENTAL_OR_CONSERVATIVE"

    lines = [
        "# Residual Geometry CV Report",
        "",
        f"- Data hash: `{config.get('data_hash', 'unknown')}`",
        f"- Model: `{config.get('model_class', 'unknown')}`",
        f"- Selected alpha: `{config.get('selected_alpha', 1.0)}`",
        f"- Train rows per well cap: `{config.get('train_rows_per_well', '')}`",
        f"- Promotion decision: `{promotion}`",
        "",
        "## Overall Metrics",
        "",
        overall.round(4).to_markdown(index=False),
        "",
        "## Alpha Search",
        "",
        alpha.round(4).to_markdown(index=False) if len(alpha) else "_No alpha search file._",
        "",
        "## Per-Well Summary",
        "",
        pd.DataFrame(
            [
                {
                    "wells": len(by_well),
                    "improved_wells": improved_wells,
                    "degraded_wells": degraded_wells,
                    "mean_rmse_improvement": by_well["rmse_improvement"].mean(),
                    "median_rmse_improvement": by_well["rmse_improvement"].median(),
                    "worst_degradation": by_well["rmse_improvement"].min(),
                    "best_improvement": by_well["rmse_improvement"].max(),
                }
            ]
        ).round(4).to_markdown(index=False),
        "",
        "## Residual Clip and Smoothness",
        "",
        clip_table.round(4).to_markdown(index=False),
        "",
        "## Bias by Target Length",
        "",
        bias_by_length.round(4).to_markdown(index=False),
        "",
        "## Bias by Baseline Confidence",
        "",
        bias_by_confidence.round(4).to_markdown(index=False),
        "",
        "## Bias by Predicted Residual Magnitude",
        "",
        bias_by_predicted_residual.round(4).to_markdown(index=False),
        "",
        "## Outputs",
        "",
        f"- OOF predictions: `{OOF_PATH.relative_to(ROOT)}`",
        f"- Per-well CV: `{CV_BY_WELL_PATH.relative_to(ROOT)}`",
        f"- Test predictions: `{TEST_PRED_PATH.relative_to(ROOT)}`",
        "",
    ]
    CV_REPORT_PATH.write_text("\n".join(lines))
    write_failure_report(oof, by_well)

    importance = feature_importance(config)
    lines = [
        "# Residual Geometry Feature Importance",
        "",
        "Permutation importance is computed on a deterministic sample of training residual rows. It is a model-agnostic diagnostic, not a feature-selection contract.",
        "",
        f"- Sample rows: `{env_int('ROGII_PART2_IMPORTANCE_SAMPLE_ROWS', 20000)}`",
        "",
        importance.head(50).round(6).to_markdown(index=False),
        "",
    ]
    IMPORTANCE_REPORT_PATH.write_text("\n".join(lines))

    print(f"Wrote {CV_BY_WELL_PATH}")
    print(f"Wrote {CV_REPORT_PATH}")
    print(f"Wrote {FAILURE_REPORT_PATH}")
    print(f"Wrote {IMPORTANCE_REPORT_PATH}")
    print(f"promotion={promotion} rmse_improvement={improvement:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
