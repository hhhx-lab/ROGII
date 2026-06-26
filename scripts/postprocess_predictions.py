#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

from data_paths import load_sample_submission


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"
SUBMISSION_DIR = ROOT / "submissions"
OOF_SUMMARY_PATH = OUTPUT_DIR / "postprocess_oof_summary.csv"
OOF_PER_WELL_PATH = OUTPUT_DIR / "postprocess_oof_by_well.csv"

ROUTE_CONFIDENCE = {
    "typewell_alignment": 0.85,
    "gr_residual": 0.65,
    "geometry_residual": 0.55,
    "baseline_fallback": 0.35,
}
SUPPORTED_VARIANTS = [
    "auto",
    "conservative",
    "balanced",
    "aggressive",
    "optimized",
    "geometry",
    "gated_geometry",
    "learned_gated_geometry",
    "xgb",
]
VARIANT_TARGETS: dict[str, tuple[Path, Path]] = {
    "conservative": (SUBMISSION_DIR / "conservative_submission.csv", OUTPUT_DIR / "blend_oof.csv"),
    "balanced": (SUBMISSION_DIR / "balanced_submission.csv", OUTPUT_DIR / "blend_oof.csv"),
    "aggressive": (SUBMISSION_DIR / "aggressive_submission.csv", OUTPUT_DIR / "blend_oof.csv"),
    "optimized": (SUBMISSION_DIR / "optimized_submission.csv", OUTPUT_DIR / "blend_oof.csv"),
    "geometry": (SUBMISSION_DIR / "geometry_residual_submission.csv", OUTPUT_DIR / "residual_geometry_oof.csv"),
    "gated_geometry": (SUBMISSION_DIR / "gated_geometry_submission.csv", OUTPUT_DIR / "gated_geometry_oof.csv"),
    "learned_gated_geometry": (
        SUBMISSION_DIR / "learned_gated_geometry_submission.csv",
        OUTPUT_DIR / "learned_gated_geometry_oof.csv",
    ),
    "xgb": (SUBMISSION_DIR / "xgb_residual_submission.csv", OUTPUT_DIR / "residual_xgb_oof.csv"),
}
SELECTION_JSON = OUTPUT_DIR / "selected_candidate.json"


@dataclass
class RouteStats:
    residual_low: float
    residual_high: float
    step_cap: float


def parse_id(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    parts = out["id"].astype("string").str.rsplit("_", n=1, expand=True)
    out["well"] = parts[0]
    out["row"] = parts[1].astype(int)
    return out


def safe_quantile(values: pd.Series | np.ndarray, q: float, default: float) -> float:
    arr = np.asarray(values, dtype=float)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return float(default)
    return float(np.quantile(arr, q))


def safe_rmse(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> float:
    return float(mean_squared_error(np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)) ** 0.5)


def markdown_table(frame: pd.DataFrame, index: bool = False) -> str:
    try:
        return frame.to_markdown(index=index)
    except ImportError:
        return frame.to_string(index=index)


def load_submission(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string"})
    if list(frame.columns) != ["id", "tvt"]:
        raise ValueError(f"{path} must have exactly id,tvt columns")
    return frame


def load_baseline_test() -> pd.DataFrame:
    path = OUTPUT_DIR / "baseline_predictions_test.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string", "well": "string", "row": "Int64"})
    if "baseline_tvt" not in frame.columns:
        raise ValueError(f"{path} must contain baseline_tvt")
    return frame[["id", "baseline_tvt"]]


def load_route_diagnostics() -> pd.DataFrame:
    path = OUTPUT_DIR / "part3_diagnostics.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"well": "string"})
    if "route_suggestion" in frame.columns:
        frame = frame.rename(columns={"route_suggestion": "route"})
    if "route" not in frame.columns:
        raise ValueError(f"{path} must contain route_suggestion or route")
    for col in ["baseline_confidence", "gr_quality_score", "typewell_quality_score"]:
        if col not in frame.columns:
            frame[col] = 0.0
    return frame[["well", "split", "route", "baseline_confidence", "gr_quality_score", "typewell_quality_score"]]


def load_oof_variant(path: Path, variant: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string", "well": "string"})
    col = f"{variant}_tvt"
    if col not in frame.columns:
        if "final_pred" in frame.columns:
            col = "final_pred"
        elif "tvt" in frame.columns:
            col = "tvt"
        else:
            raise ValueError(f"{path} must contain {variant}_tvt, final_pred, or tvt")
    if "baseline_tvt" not in frame.columns or "truth_tvt" not in frame.columns:
        raise ValueError(f"{path} must contain baseline_tvt and truth_tvt")
    return frame[["id", "well", "truth_tvt", "baseline_tvt", col]].rename(columns={col: "variant_tvt"})


def usable_oof_variant(oof_variant: pd.DataFrame | None, diagnostics_oof: pd.DataFrame, min_well_fraction: float = 0.8) -> pd.DataFrame | None:
    if oof_variant is None:
        return None
    expected_wells = int(diagnostics_oof["well"].nunique()) if "well" in diagnostics_oof else 0
    actual_wells = int(oof_variant["well"].nunique()) if "well" in oof_variant else 0
    if expected_wells and actual_wells < max(1, int(expected_wells * min_well_fraction)):
        return None
    return oof_variant


def route_scores(diagnostics: pd.DataFrame) -> pd.DataFrame:
    out = diagnostics.copy()
    out["route_confidence"] = out["route"].map(ROUTE_CONFIDENCE).fillna(0.5)
    out["confidence"] = (
        0.45 * out["route_confidence"]
        + 0.25 * out["gr_quality_score"].fillna(0.0)
        + 0.20 * out["typewell_quality_score"].fillna(0.0)
        + 0.10 * out["baseline_confidence"].fillna(0.0)
    ).clip(0.0, 1.0)
    return out


def build_route_stats(oof_frame: pd.DataFrame, diagnostics: pd.DataFrame, variant: str) -> tuple[dict[str, RouteStats], RouteStats]:
    frame = oof_frame.merge(diagnostics[["well", "route", "confidence"]], on="well", how="left", validate="many_to_one")
    frame = parse_id(frame)
    frame = frame.sort_values(["well", "row"], kind="mergesort").reset_index(drop=True)
    frame["residual"] = frame["variant_tvt"] - frame["baseline_tvt"]
    frame["residual_step"] = frame.groupby("well")["residual"].diff().abs()

    stats: dict[str, RouteStats] = {}
    for route, group in frame.groupby("route", dropna=False):
        residual = group["residual"]
        step = group["residual_step"].dropna()
        default_step = 18.0 if route == "typewell_alignment" else 24.0 if route == "gr_residual" else 28.0 if route == "geometry_residual" else 36.0
        stats[str(route)] = RouteStats(
            residual_low=safe_quantile(residual, 0.01, -25.0),
            residual_high=safe_quantile(residual, 0.99, 25.0),
            step_cap=safe_quantile(step, 0.99, default_step),
        )

    global_stats = RouteStats(
        residual_low=safe_quantile(frame["residual"], 0.01, -25.0),
        residual_high=safe_quantile(frame["residual"], 0.99, 25.0),
        step_cap=safe_quantile(frame["residual_step"].dropna(), 0.99, 28.0),
    )
    stats["__global__"] = global_stats
    return stats, global_stats


def prepare_frame(frame: pd.DataFrame, baseline_lookup: pd.DataFrame, diagnostics: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out = out.rename(columns={"tvt": "input_tvt"})
    out["submission_order"] = np.arange(len(out), dtype=int)
    out = parse_id(out)
    if "baseline_tvt" not in out.columns:
        out = out.merge(baseline_lookup, on="id", how="left", validate="one_to_one")
    if "baseline_tvt" not in out.columns:
        raise ValueError("Missing baseline_tvt column")
    if out["baseline_tvt"].isna().any():
        raise ValueError("Missing baseline_tvt for some rows")
    out = out.merge(diagnostics, on="well", how="left", validate="many_to_one")
    out["route"] = out["route"].fillna("baseline_fallback")
    out["confidence"] = out["confidence"].fillna(0.5).clip(0.0, 1.0)
    return out


def smooth_and_clip_residuals(frame: pd.DataFrame, stats: dict[str, RouteStats], default_stats: RouteStats) -> pd.DataFrame:
    out = frame.copy()
    out["route_confidence"] = out["route"].map(ROUTE_CONFIDENCE).fillna(0.5)
    out["residual_raw"] = out["input_tvt"] - out["baseline_tvt"]
    out["window"] = np.select(
        [out["confidence"] >= 0.8, out["confidence"] >= 0.65, out["confidence"] >= 0.45],
        [11, 9, 7],
        default=5,
    )
    out["residual_scale"] = (0.25 + 0.75 * out["confidence"]).clip(0.25, 1.0)

    processed_rows = []
    for _, group in out.sort_values(["well", "row"], kind="mergesort").groupby("well", sort=False):
        group = group.copy()
        window = int(group["window"].iloc[0]) if len(group) else 5
        residual = group["residual_raw"].to_numpy(dtype=float)
        smoothed = pd.Series(residual).rolling(window=window, center=True, min_periods=1).median().to_numpy(dtype=float)
        scaled = group["residual_scale"].to_numpy(dtype=float) * smoothed + (1.0 - group["residual_scale"].to_numpy(dtype=float)) * residual
        route = str(group["route"].iloc[0]) if len(group) else "baseline_fallback"
        route_stats = stats.get(route, default_stats)
        clipped = np.clip(scaled, route_stats.residual_low, route_stats.residual_high)
        capped = clipped.copy()
        for idx in range(1, len(capped)):
            step_cap = route_stats.step_cap if np.isfinite(route_stats.step_cap) and route_stats.step_cap > 0 else default_stats.step_cap
            delta = capped[idx] - capped[idx - 1]
            delta = float(np.clip(delta, -step_cap, step_cap))
            capped[idx] = capped[idx - 1] + delta
        group["residual_smoothed"] = smoothed
        group["residual_scaled"] = scaled
        group["residual_clipped"] = clipped
        group["residual_post"] = capped
        group["post_tvt"] = np.clip(group["baseline_tvt"].to_numpy(dtype=float) + capped, 9000.0, 13000.0)
        group["delta_from_input"] = group["post_tvt"] - group["input_tvt"]
        group["step_cap"] = route_stats.step_cap
        group["residual_low"] = route_stats.residual_low
        group["residual_high"] = route_stats.residual_high
        processed_rows.append(group)

    processed = pd.concat(processed_rows, ignore_index=True) if processed_rows else out.copy()
    processed = processed.sort_values("submission_order", kind="mergesort").reset_index(drop=True)
    return processed


def evaluate_oof(post_frame: pd.DataFrame, variant: str, input_col: str = "input_tvt") -> pd.DataFrame:
    before_rmse = safe_rmse(post_frame["truth_tvt"], post_frame[input_col])
    after_rmse = safe_rmse(post_frame["truth_tvt"], post_frame["post_tvt"])
    before_mae = float(np.mean(np.abs(post_frame["truth_tvt"].to_numpy(dtype=float) - post_frame[input_col].to_numpy(dtype=float))))
    after_mae = float(np.mean(np.abs(post_frame["truth_tvt"].to_numpy(dtype=float) - post_frame["post_tvt"].to_numpy(dtype=float))))
    before_p95 = float(np.quantile(np.abs(post_frame["truth_tvt"].to_numpy(dtype=float) - post_frame[input_col].to_numpy(dtype=float)), 0.95))
    after_p95 = float(np.quantile(np.abs(post_frame["truth_tvt"].to_numpy(dtype=float) - post_frame["post_tvt"].to_numpy(dtype=float)), 0.95))
    before_max = float(np.max(np.abs(post_frame["truth_tvt"].to_numpy(dtype=float) - post_frame[input_col].to_numpy(dtype=float))))
    after_max = float(np.max(np.abs(post_frame["truth_tvt"].to_numpy(dtype=float) - post_frame["post_tvt"].to_numpy(dtype=float))))

    per_well = (
        post_frame.groupby("well", as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "rows": len(g),
                    "rmse_before": safe_rmse(g["truth_tvt"], g[input_col]),
                    "rmse_after": safe_rmse(g["truth_tvt"], g["post_tvt"]),
                    "mae_before": float(np.mean(np.abs(g["truth_tvt"].to_numpy(dtype=float) - g[input_col].to_numpy(dtype=float)))),
                    "mae_after": float(np.mean(np.abs(g["truth_tvt"].to_numpy(dtype=float) - g["post_tvt"].to_numpy(dtype=float)))),
                }
            )
        )
        .reset_index(drop=True)
        .sort_values("rmse_after", ascending=False)
    )

    summary = pd.DataFrame(
        [
            {"metric": "rmse_before", "value": before_rmse},
            {"metric": "rmse_after", "value": after_rmse},
            {"metric": "mae_before", "value": before_mae},
            {"metric": "mae_after", "value": after_mae},
            {"metric": "p95_before", "value": before_p95},
            {"metric": "p95_after", "value": after_p95},
            {"metric": "max_before", "value": before_max},
            {"metric": "max_after", "value": after_max},
        ]
    )
    summary["variant"] = variant
    summary["delta"] = summary["value"].diff().fillna(0.0)
    return summary, per_well


def metric_value(summary: pd.DataFrame, metric: str) -> float | None:
    if summary.empty:
        return None
    values = summary.loc[summary["metric"].eq(metric), "value"]
    if values.empty:
        return None
    return float(values.iloc[0])


def postprocess_decision(summary: pd.DataFrame, allow_worse: bool, min_improvement: float) -> dict[str, object]:
    before = metric_value(summary, "rmse_before")
    after = metric_value(summary, "rmse_after")
    if before is None or after is None:
        return {
            "accepted": False,
            "reason": "no_oof_guard_available",
            "rmse_before": before,
            "rmse_after": after,
            "min_improvement": min_improvement,
            "actual_improvement": None,
    }
    if allow_worse:
        return {
            "accepted": True,
            "reason": "allow_worse",
            "rmse_before": before,
            "rmse_after": after,
            "min_improvement": min_improvement,
            "actual_improvement": before - after,
        }
    actual_improvement = before - after
    accepted = actual_improvement >= min_improvement
    return {
        "accepted": bool(accepted),
        "reason": "oof_improvement_guard_passed" if accepted else "oof_improvement_guard_failed",
        "rmse_before": before,
        "rmse_after": after,
        "min_improvement": min_improvement,
        "actual_improvement": actual_improvement,
    }


def postprocess_submission(
    submission: pd.DataFrame,
    variant: str,
    diagnostics: pd.DataFrame,
    baseline_test: pd.DataFrame,
    diagnostics_oof: pd.DataFrame | None = None,
    oof_variant: pd.DataFrame | None = None,
    clip_lower: float = 9000.0,
    clip_upper: float = 13000.0,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, RouteStats], RouteStats]:
    frame = prepare_frame(submission, baseline_test, diagnostics)

    if oof_variant is not None:
        if diagnostics_oof is None:
            diagnostics_oof = diagnostics
        stats, global_stats = build_route_stats(oof_variant, diagnostics_oof, variant)
    else:
        global_stats = RouteStats(residual_low=-25.0, residual_high=25.0, step_cap=28.0)
        stats = {"__global__": global_stats}

    processed = smooth_and_clip_residuals(frame, stats, global_stats)
    processed["post_tvt"] = processed["post_tvt"].clip(lower=clip_lower, upper=clip_upper)

    diagnostics_out = processed[
        [
            "id",
            "well",
            "row",
            "route",
            "confidence",
            "baseline_tvt",
            "input_tvt",
            "residual_raw",
            "residual_smoothed",
            "residual_scaled",
            "residual_clipped",
            "residual_post",
            "post_tvt",
            "delta_from_input",
            "window",
            "step_cap",
            "residual_low",
            "residual_high",
        ]
    ].copy()
    submission_out = processed[["id", "post_tvt"]].rename(columns={"post_tvt": "tvt"})

    if clip_lower is not None and clip_upper is not None:
        submission_out["tvt"] = submission_out["tvt"].clip(lower=clip_lower, upper=clip_upper)

    if oof_variant is not None:
        if diagnostics_oof is None:
            diagnostics_oof = diagnostics
        oof_frame = prepare_frame(oof_variant.rename(columns={"variant_tvt": "tvt"}), oof_variant[["id", "baseline_tvt"]], diagnostics_oof)
        oof_processed = smooth_and_clip_residuals(oof_frame, stats, global_stats)
        oof_processed["post_tvt"] = oof_processed["post_tvt"].clip(lower=clip_lower, upper=clip_upper)
        summary, per_well = evaluate_oof(oof_processed, variant)
    else:
        summary = pd.DataFrame(columns=["metric", "value", "variant", "delta"])
        per_well = pd.DataFrame()

    return submission_out, diagnostics_out, summary, per_well, stats, global_stats


def write_report(
    report_path: Path,
    variant: str,
    oof_path: Path | None,
    summary: pd.DataFrame,
    per_well: pd.DataFrame,
    diagnostics: pd.DataFrame,
    stats: dict[str, RouteStats],
    global_stats: RouteStats,
    decision: dict[str, object] | None = None,
) -> None:
    report_path.parent.mkdir(exist_ok=True)
    decision = decision or {}
    lines = [
        "# Postprocess Report",
        "",
        f"- Variant: `{variant}`",
        f"- OOF path: `{str(oof_path) if oof_path is not None else ''}`",
        f"- Rows: {len(diagnostics):,}",
        f"- Decision: `{'accepted' if decision.get('accepted') else 'rejected'}`",
        f"- Decision reason: `{decision.get('reason', 'unknown')}`",
        f"- RMSE before: `{decision.get('rmse_before')}`",
        f"- RMSE after: `{decision.get('rmse_after')}`",
        f"- Actual RMSE improvement: `{decision.get('actual_improvement')}`",
        f"- Minimum required improvement: `{decision.get('min_improvement')}`",
        "",
        "## OOF Summary",
        "",
        markdown_table(summary.round(4), index=False) if len(summary) else "_No OOF available_",
        "",
        "## Worst Wells",
        "",
        markdown_table(per_well.head(15).round(4), index=False) if len(per_well) else "_No OOF available_",
        "",
        "## Route Stats",
        "",
        markdown_table(
            pd.DataFrame(
                [
                    {
                        "route": route,
                        "residual_low": value.residual_low,
                        "residual_high": value.residual_high,
                        "step_cap": value.step_cap,
                    }
                    for route, value in stats.items()
                    if route != "__global__"
                ]
            ).round(4),
            index=False,
        ),
        "",
        "## Global Stats",
        "",
        markdown_table(
            pd.DataFrame(
                [
                    {
                        "residual_low": global_stats.residual_low,
                        "residual_high": global_stats.residual_high,
                        "step_cap": global_stats.step_cap,
                    }
                ]
            ).round(4),
            index=False,
        ),
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_postprocess(
    variant: str,
    input_path: Path,
    output_path: Path,
    diagnostics_path: Path,
    report_path: Path,
    oof_path: Path | None = None,
    clip_lower: float = 9000.0,
    clip_upper: float = 13000.0,
    allow_worse: bool = False,
    min_improvement: float = 0.0,
) -> pd.DataFrame:
    submission = load_submission(input_path)
    diagnostics_all = route_scores(load_route_diagnostics())
    diagnostics = diagnostics_all[diagnostics_all["split"] == "test"].copy()
    diagnostics_oof = diagnostics_all[diagnostics_all["split"] == "train"].copy()
    baseline_test = load_baseline_test()
    oof_variant = load_oof_variant(oof_path, variant) if oof_path and oof_path.exists() else None
    oof_variant = usable_oof_variant(oof_variant, diagnostics_oof)
    submission_out, diagnostics_out, summary, per_well, stats, global_stats = postprocess_submission(
        submission=submission,
        variant=variant,
        diagnostics=diagnostics,
        baseline_test=baseline_test,
        diagnostics_oof=diagnostics_oof,
        oof_variant=oof_variant,
        clip_lower=clip_lower,
        clip_upper=clip_upper,
    )

    if len(diagnostics_out) != len(submission):
        raise ValueError("Postprocess diagnostics row count mismatch")
    decision = postprocess_decision(summary, allow_worse=allow_worse, min_improvement=min_improvement)
    if not bool(decision["accepted"]):
        submission_out = submission.copy()
        diagnostics_out["post_tvt_guarded"] = diagnostics_out["post_tvt"]
        diagnostics_out["post_tvt"] = diagnostics_out["input_tvt"]
        diagnostics_out["delta_from_input"] = 0.0
    diagnostics_path.parent.mkdir(exist_ok=True)
    diagnostics_out.to_csv(diagnostics_path, index=False)
    if len(summary):
        summary.to_csv(OOF_SUMMARY_PATH, index=False)
    if len(per_well):
        per_well.to_csv(OOF_PER_WELL_PATH, index=False)
    output_path.parent.mkdir(exist_ok=True)
    submission_out.to_csv(output_path, index=False)
    write_report(report_path, variant, oof_path, summary, per_well, diagnostics_out, stats, global_stats, decision=decision)
    return submission_out


def resolve_variant_targets(variant: str) -> tuple[str, Path, Path]:
    if variant == "auto":
        if not SELECTION_JSON.exists():
            raise FileNotFoundError(
                f"{SELECTION_JSON} is required for --variant auto; run select_submission_candidate.py first."
            )
        payload = json.loads(SELECTION_JSON.read_text(encoding="utf-8"))
        selected = payload.get("selected_candidate")
        if not isinstance(selected, dict) or not selected.get("name"):
            raise ValueError(f"{SELECTION_JSON} does not contain a selected candidate.")
        resolved = str(selected["name"])
        submission_path = Path(str(selected.get("submission_path") or ""))
        oof_path = Path(str(selected.get("oof_path") or ""))
        if not submission_path.exists():
            raise FileNotFoundError(f"Selected candidate submission is missing: {submission_path}")
        if not oof_path.exists():
            raise FileNotFoundError(f"Selected candidate OOF is missing: {oof_path}")
        return resolved, submission_path, oof_path

    try:
        submission_path, oof_path = VARIANT_TARGETS[variant]
    except KeyError as exc:
        raise ValueError(f"Unknown variant: {variant}") from exc
    return variant, submission_path, oof_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Postprocess a submission variant and write diagnostics.")
    parser.add_argument(
        "--variant",
        default="auto",
        choices=SUPPORTED_VARIANTS,
        help="Submission variant to postprocess. Use auto to read outputs/selected_candidate.json.",
    )
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--diagnostics", type=Path, default=OUTPUT_DIR / "postprocess_diagnostics.csv")
    parser.add_argument("--report", type=Path, default=REPORT_DIR / "postprocess_report.md")
    parser.add_argument("--oof", type=Path, default=None)
    parser.add_argument("--clip-lower", type=float, default=9000.0)
    parser.add_argument("--clip-upper", type=float, default=13000.0)
    parser.add_argument("--allow-worse", action="store_true", help="Write postprocessed output even when OOF RMSE gets worse.")
    parser.add_argument("--min-improvement", type=float, default=0.0, help="Minimum OOF RMSE improvement required before accepting postprocess.")
    parser.add_argument("--tolerance", type=float, default=0.0, help="Deprecated compatibility option; prefer --min-improvement.")
    args = parser.parse_args()

    resolved_variant, default_input, default_oof = resolve_variant_targets(args.variant)
    input_path = args.input or default_input
    oof_path = args.oof or default_oof
    output_path = args.output or (SUBMISSION_DIR / f"{resolved_variant}_postprocessed_submission.csv")
    run_postprocess(
        variant=resolved_variant,
        input_path=input_path,
        output_path=output_path,
        diagnostics_path=args.diagnostics,
        report_path=args.report,
        oof_path=oof_path,
        clip_lower=args.clip_lower,
        clip_upper=args.clip_upper,
        allow_worse=args.allow_worse,
        min_improvement=args.min_improvement,
    )
    print(f"Wrote postprocessed submission to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
