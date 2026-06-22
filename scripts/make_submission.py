#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data_paths import load_sample_submission
from postprocess_predictions import run_postprocess
from select_submission_candidate import load_submission_like, parse_postprocess_report, select_best_candidate


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"
SUBMISSION_DIR = ROOT / "submissions"
VARIANT_FILES = {
    "baseline": OUTPUT_DIR / "baseline_predictions_test.csv",
    "conservative": SUBMISSION_DIR / "conservative_submission.csv",
    "balanced": SUBMISSION_DIR / "balanced_submission.csv",
    "aggressive": SUBMISSION_DIR / "aggressive_submission.csv",
    "optimized": SUBMISSION_DIR / "optimized_submission.csv",
    "geometry": SUBMISSION_DIR / "geometry_residual_submission.csv",
    "gated_geometry": SUBMISSION_DIR / "gated_geometry_submission.csv",
    "xgb": SUBMISSION_DIR / "xgb_residual_submission.csv",
    "xgb_leftover": SUBMISSION_DIR / "xgb_leftover_submission.csv",
    "gated_geometry_plus_xgb_leftover": SUBMISSION_DIR / "gated_geometry_plus_xgb_leftover_submission.csv",
}
POSTPROCESSABLE_VARIANTS = {
    "conservative",
    "balanced",
    "aggressive",
    "optimized",
    "geometry",
    "gated_geometry",
    "xgb",
    "xgb_leftover",
    "gated_geometry_plus_xgb_leftover",
}
POSTPROCESS_OOF_FILES = {
    "conservative": OUTPUT_DIR / "blend_oof.csv",
    "balanced": OUTPUT_DIR / "blend_oof.csv",
    "aggressive": OUTPUT_DIR / "blend_oof.csv",
    "optimized": OUTPUT_DIR / "blend_oof.csv",
    "geometry": OUTPUT_DIR / "residual_geometry_oof.csv",
    "gated_geometry": OUTPUT_DIR / "gated_geometry_oof.csv",
    "xgb": OUTPUT_DIR / "residual_xgb_oof.csv",
    "xgb_leftover": OUTPUT_DIR / "residual_xgb_leftover_oof.csv",
    "gated_geometry_plus_xgb_leftover": OUTPUT_DIR / "gated_geometry_plus_xgb_leftover_oof.csv",
}


def load_submission(path: Path) -> pd.DataFrame:
    return load_submission_like(path)


def validate_submission(submission: pd.DataFrame, sample: pd.DataFrame) -> None:
    if len(submission) != len(sample):
        raise ValueError("submission row count mismatch")
    if not submission["id"].astype("string").equals(sample["id"].astype("string")):
        raise ValueError("submission ids are not in sample order")
    if submission["id"].duplicated().any():
        raise ValueError("submission contains duplicated ids")
    if not np.isfinite(submission["tvt"].to_numpy(dtype=float)).all():
        raise ValueError("submission contains NaN or inf")


def write_log(log_path: Path, record: dict[str, object]) -> None:
    log_path.parent.mkdir(exist_ok=True)
    if log_path.exists():
        try:
            history = json.loads(log_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            history = []
    else:
        history = []
    if not isinstance(history, list):
        history = [history]
    history.append(record)
    log_path.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_ensemble_report(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["variant", "rmse"])
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 2 or cells[0] in {"variant", ":-------------"}:
            continue
        try:
            rows.append({"variant": cells[0], "rmse": float(cells[1])})
        except ValueError:
            continue
    return pd.DataFrame(rows, columns=["variant", "rmse"])


def load_cv_summary() -> pd.DataFrame:
    csv_path = OUTPUT_DIR / "ensemble_cv_summary.csv"
    if csv_path.exists():
        summary = pd.read_csv(csv_path)
    else:
        summary = parse_ensemble_report(REPORT_DIR / "ensemble_report.md")
    if summary.empty:
        return summary
    return summary[summary["variant"].isin(VARIANT_FILES)].copy()


def choose_variant(requested: str) -> tuple[str, str, Path, bool]:
    if requested != "auto":
        return requested, "explicit", variant_path(requested), False
    try:
        selected = select_best_candidate(write_report=True)
        return selected.name, "auto_candidate_selection", Path(selected.submission_path), selected.is_postprocessed
    except Exception:
        summary = load_cv_summary()
    available = [variant for variant, path in VARIANT_FILES.items() if path.exists()]
    if not available:
        raise FileNotFoundError("No candidate submission files exist under submissions/")
    if summary.empty:
        fallback = "balanced" if "balanced" in available else available[0]
        return fallback, "auto_fallback_no_cv_summary", variant_path(fallback), False
    summary = summary[summary["variant"].isin(available)].sort_values("rmse", kind="mergesort")
    if summary.empty:
        fallback = "balanced" if "balanced" in available else available[0]
        return fallback, "auto_fallback_no_available_cv_variant", variant_path(fallback), False
    variant = str(summary.iloc[0]["variant"])
    return variant, "auto_oof_best", variant_path(variant), False


def variant_path(variant: str) -> Path:
    try:
        return VARIANT_FILES[variant]
    except KeyError as exc:
        raise ValueError(f"Unknown variant: {variant}") from exc


def postprocess_oof_path(variant: str) -> Path | None:
    return POSTPROCESS_OOF_FILES.get(variant)


def find_guarded_postprocessed_submission(variant: str) -> Path | None:
    report = parse_postprocess_report(REPORT_DIR / "postprocess_report.md")
    if not report.get("available"):
        return None
    if str(report.get("variant") or "") != variant:
        return None
    if str(report.get("decision") or "") != "accepted":
        return None
    expected_oof = postprocess_oof_path(variant)
    report_oof = str(report.get("oof_path") or "").strip()
    if expected_oof is not None:
        if not report_oof:
            return None
        if Path(report_oof).resolve() != expected_oof.resolve():
            return None
    candidate_path = SUBMISSION_DIR / f"{variant}_postprocessed_submission.csv"
    return candidate_path if candidate_path.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the final submission.csv.")
    parser.add_argument("--variant", default="auto", choices=["auto", *VARIANT_FILES.keys()])
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=ROOT / "submission.csv")
    parser.add_argument("--log", type=Path, default=REPORT_DIR / "submission_log.md")
    parser.add_argument("--postprocess-policy", default="auto", choices=["auto", "always", "never"])
    parser.add_argument("--clip-lower", type=float, default=9000.0)
    parser.add_argument("--clip-upper", type=float, default=13000.0)
    args = parser.parse_args()

    sample = load_sample_submission()[["id"]].copy()
    selected_variant, selection_reason, selected_path, already_postprocessed = choose_variant(args.variant)
    input_path = args.input or selected_path
    postprocessed_path = SUBMISSION_DIR / f"{selected_variant}_postprocessed_submission.csv"
    diagnostics_path = OUTPUT_DIR / "postprocess_diagnostics.csv"
    report_path = REPORT_DIR / "postprocess_report.md"

    postprocess_ran = False
    postprocess_used = False
    postprocess_reason = "not_requested"
    if already_postprocessed:
        source_path = input_path
        postprocess_used = True
        postprocess_reason = "selected_candidate_already_postprocessed"
    elif args.postprocess_policy == "always" and selected_variant in POSTPROCESSABLE_VARIANTS:
        oof_path = postprocess_oof_path(selected_variant)
        if oof_path is not None and oof_path.exists():
            run_postprocess(
                variant=selected_variant,
                input_path=input_path,
                output_path=postprocessed_path,
                diagnostics_path=diagnostics_path,
                report_path=report_path,
                oof_path=oof_path,
                clip_lower=args.clip_lower,
                clip_upper=args.clip_upper,
                allow_worse=False,
                min_improvement=0.0,
            )
            postprocess_ran = True
            postprocess_used = True
            source_path = postprocessed_path
            postprocess_reason = "policy_always_ran_guarded_postprocess"
        else:
            source_path = input_path
            postprocess_reason = "missing_candidate_specific_oof"
    elif args.postprocess_policy == "auto":
        guarded = find_guarded_postprocessed_submission(selected_variant)
        if guarded is not None:
            source_path = guarded
            postprocess_used = True
            postprocess_reason = "existing_guarded_postprocessed_submission"
        else:
            source_path = input_path
            postprocess_reason = "auto_policy_kept_raw_candidate"
    else:
        source_path = input_path
        postprocess_reason = "postprocess_disabled"

    submission = load_submission(source_path)
    submission = sample.merge(submission, on="id", how="left", validate="one_to_one")
    if submission["tvt"].isna().any():
        raise ValueError("submission contains missing predictions after alignment")
    submission = submission[["id", "tvt"]]
    validate_submission(submission, sample)
    submission.to_csv(args.output, index=False)

    write_log(
        args.log,
        {
            "requested_variant": args.variant,
            "selected_variant": selected_variant,
            "selection_reason": selection_reason,
            "input": str(input_path),
            "source": str(source_path),
            "output": str(args.output),
            "postprocess_policy": args.postprocess_policy,
            "postprocess_ran": postprocess_ran,
            "postprocess_used": postprocess_used,
            "postprocess_reason": postprocess_reason,
            "postprocessed": str(postprocessed_path) if postprocess_used else "",
            "rows": len(submission),
        },
    )
    print(f"Wrote final submission to {args.output} from {selected_variant} ({selection_reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
