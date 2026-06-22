#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from data_paths import load_sample_submission
from part2_utils import FEATURE_DIR, MODEL_DIR, OUTPUT_DIR, REPORT_DIR, ROOT
from rogii_utils import SUBMISSION_DIR, assert_data_contract_ready, parse_submission_ids


AUDIT_PATH = REPORT_DIR / "part2_completion_audit.md"

REQUIRED_FEATURES = [
    FEATURE_DIR / "baseline_features_train.csv",
    FEATURE_DIR / "baseline_features_test.csv",
    FEATURE_DIR / "geometry_features_train.csv",
    FEATURE_DIR / "geometry_features_test.csv",
    FEATURE_DIR / "residual_targets.csv",
]
REQUIRED_MODELS = [
    MODEL_DIR / "residual_geometry_hgb.pkl",
    MODEL_DIR / "residual_geometry_hgb_config.json",
    MODEL_DIR / "residual_geometry_hgb_feature_list.txt",
]
REQUIRED_OUTPUTS = [
    OUTPUT_DIR / "residual_geometry_oof.csv",
    OUTPUT_DIR / "residual_geometry_cv_by_well.csv",
    OUTPUT_DIR / "residual_geometry_test_predictions.csv",
]
REQUIRED_REPORTS = [
    REPORT_DIR / "residual_target_report.md",
    REPORT_DIR / "residual_geometry_cv_report.md",
]
REQUIRED_SUBMISSIONS = [SUBMISSION_DIR / "geometry_residual_submission.csv"]

PRIMARY_ARTIFACTS = {
    "geometry": {
        "models": REQUIRED_MODELS,
        "outputs": REQUIRED_OUTPUTS,
        "reports": REQUIRED_REPORTS,
        "submissions": REQUIRED_SUBMISSIONS,
        "config_candidates": [
            MODEL_DIR / "residual_geometry_hgb_config.json",
            MODEL_DIR / "residual_geometry_config.json",
        ],
        "submission_path": SUBMISSION_DIR / "geometry_residual_submission.csv",
        "oof_path": OUTPUT_DIR / "residual_geometry_oof.csv",
        "cv_path": OUTPUT_DIR / "residual_geometry_cv_by_well.csv",
        "label": "geometry residual",
    },
    "xgb": {
        "models": [
            MODEL_DIR / "residual_xgb_model.pkl",
            MODEL_DIR / "residual_xgb_config.json",
            MODEL_DIR / "residual_xgb_feature_list.txt",
        ],
        "outputs": [
            OUTPUT_DIR / "residual_xgb_oof.csv",
            OUTPUT_DIR / "residual_xgb_cv_by_well.csv",
            OUTPUT_DIR / "residual_xgb_test_predictions.csv",
        ],
        "reports": [
            REPORT_DIR / "residual_target_report.md",
            REPORT_DIR / "residual_xgb_cv_report.md",
        ],
        "submissions": [SUBMISSION_DIR / "xgb_residual_submission.csv"],
        "config_candidates": [MODEL_DIR / "residual_xgb_config.json"],
        "submission_path": SUBMISSION_DIR / "xgb_residual_submission.csv",
        "oof_path": OUTPUT_DIR / "residual_xgb_oof.csv",
        "cv_path": OUTPUT_DIR / "residual_xgb_cv_by_well.csv",
        "label": "xgb/tree residual",
    },
}

OPTIONAL_XGB_ARTIFACTS = [
    OUTPUT_DIR / "residual_xgb_oof.csv",
    OUTPUT_DIR / "residual_xgb_cv_by_well.csv",
    OUTPUT_DIR / "residual_xgb_test_predictions.csv",
    REPORT_DIR / "residual_xgb_cv_report.md",
    SUBMISSION_DIR / "xgb_residual_submission.csv",
    MODEL_DIR / "residual_xgb_model.pkl",
    MODEL_DIR / "residual_xgb_config.json",
    MODEL_DIR / "residual_xgb_feature_list.txt",
]


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def count_csv_rows(path: Path) -> int:
    with path.open("rb") as handle:
        line_count = sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1024 * 1024), b""))
    return max(0, line_count - 1)


def markdown_table(frame: pd.DataFrame, index: bool = False) -> str:
    try:
        return frame.to_markdown(index=index)
    except ImportError:
        return frame.to_string(index=index)


def read_columns(path: Path, columns: list[str]) -> pd.DataFrame:
    return pd.read_csv(path, usecols=columns, dtype={"id": "string", "well": "string"}, low_memory=False)


def add_exists_checks(checks: list[dict[str, object]], paths: list[Path], label: str, required: bool = True) -> None:
    for path in paths:
        exists = path.exists()
        checks.append(
            {
                "check": f"{label} exists: {path.relative_to(ROOT)}",
                "status": pass_fail(exists) if required else ("PASS" if exists else "SKIP"),
                "evidence": "present" if exists else "missing",
            }
        )


def validate_feature_alignment(checks: list[dict[str, object]]) -> None:
    if not all(path.exists() for path in REQUIRED_FEATURES):
        return
    baseline_train = read_columns(FEATURE_DIR / "baseline_features_train.csv", ["id", "well", "row"])
    geometry_train = read_columns(FEATURE_DIR / "geometry_features_train.csv", ["id", "well", "row"])
    targets = read_columns(FEATURE_DIR / "residual_targets.csv", ["id", "well", "row", "residual_target"])
    baseline_test = read_columns(FEATURE_DIR / "baseline_features_test.csv", ["id", "well", "row"])
    geometry_test = read_columns(FEATURE_DIR / "geometry_features_test.csv", ["id", "well", "row"])
    checks.append(
        {
            "check": "train feature keys align with residual targets",
            "status": pass_fail(baseline_train["id"].equals(geometry_train["id"]) and baseline_train["id"].equals(targets["id"])),
            "evidence": f"rows={len(targets)}",
        }
    )
    checks.append(
        {
            "check": "test feature keys align",
            "status": pass_fail(baseline_test["id"].equals(geometry_test["id"])),
            "evidence": f"rows={len(baseline_test)}",
        }
    )
    checks.append(
        {
            "check": "residual targets are finite",
            "status": pass_fail(np.isfinite(targets["residual_target"].to_numpy(dtype=float)).all()),
            "evidence": f"rows={len(targets)} wells={targets['well'].nunique()}",
        }
    )


def validate_model_config(checks: list[dict[str, object]], config_candidates: list[Path]) -> None:
    config_path = next((path for path in config_candidates if path.exists()), None)
    if config_path is None:
        return
    config = json.loads(config_path.read_text())
    feature_columns = list(config.get("features") or config.get("feature_columns") or [])
    forbidden = {"well", "ANCC", "ASTNU", "ASTNL", "EGFDU", "EGFDL", "BUDA", "TVT", "TVT_input"}
    checks.append(
        {
            "check": "model config records feature columns",
            "status": pass_fail(bool(feature_columns)),
            "evidence": f"{config_path.relative_to(ROOT)} features={len(feature_columns)}",
        }
    )
    checks.append(
        {
            "check": "feature list excludes well id, truth and training-only formation surfaces",
            "status": pass_fail(not (forbidden & set(feature_columns))),
            "evidence": ",".join(sorted(forbidden & set(feature_columns))),
        }
    )


def validate_submission_file(checks: list[dict[str, object]], path: Path, label: str) -> None:
    if not path.exists():
        return
    sample = load_sample_submission()[["id"]].copy()
    submission = pd.read_csv(path, dtype={"id": "string"})
    if "tvt" not in submission.columns and "final_pred" in submission.columns:
        submission = submission.rename(columns={"final_pred": "tvt"})
    checks.append(
        {
            "check": f"{label} submission matches sample format",
            "status": pass_fail(
                len(submission) == len(sample)
                and "id" in submission.columns
                and "tvt" in submission.columns
                and submission["id"].astype("string").equals(sample["id"].astype("string"))
                and np.isfinite(submission["tvt"].to_numpy(dtype=float)).all()
            ),
            "evidence": f"rows={len(submission)} sample={len(sample)}",
        }
    )
    checks.append(
        {
            "check": f"{label} submission covers sample wells",
            "status": pass_fail(parse_submission_ids(submission)["well"].nunique() == parse_submission_ids(sample)["well"].nunique()),
            "evidence": int(parse_submission_ids(submission)["well"].nunique()),
        }
    )


def validate_oof_coverage(checks: list[dict[str, object]], oof_path: Path, label: str) -> None:
    target_path = FEATURE_DIR / "residual_targets.csv"
    if not oof_path.exists() or not target_path.exists():
        return
    target_rows = count_csv_rows(target_path)
    oof_rows = count_csv_rows(oof_path)
    checks.append(
        {
            "check": f"{label} OOF predictions cover every residual target row",
            "status": pass_fail(oof_rows == target_rows),
            "evidence": f"oof={oof_rows}, targets={target_rows}",
        }
    )


def validate_optional_xgb(checks: list[dict[str, object]]) -> None:
    existing = [path for path in OPTIONAL_XGB_ARTIFACTS if path.exists()]
    if not existing:
        checks.append({"check": "optional xgb/tree residual artifacts", "status": "SKIP", "evidence": "not generated in this run"})
        return
    missing = [path.relative_to(ROOT) for path in OPTIONAL_XGB_ARTIFACTS if not path.exists()]
    checks.append(
        {
            "check": "optional xgb/tree residual artifact set is complete when present",
            "status": pass_fail(not missing),
            "evidence": "missing=" + ",".join(str(path) for path in missing),
        }
    )
    validate_submission_file(checks, SUBMISSION_DIR / "xgb_residual_submission.csv", "xgb/tree residual")
    validate_oof_coverage(checks, OUTPUT_DIR / "residual_xgb_oof.csv", "xgb/tree residual")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Part 2 residual artifacts.")
    parser.add_argument("--primary-spec", choices=sorted(PRIMARY_ARTIFACTS), default="geometry")
    args = parser.parse_args()

    assert_data_contract_ready()
    checks: list[dict[str, object]] = []
    artifacts = PRIMARY_ARTIFACTS[args.primary_spec]

    add_exists_checks(checks, REQUIRED_FEATURES, "required feature")
    add_exists_checks(checks, artifacts["models"], f"required {args.primary_spec} model artifact")
    add_exists_checks(checks, artifacts["outputs"], f"required {args.primary_spec} output")
    add_exists_checks(checks, artifacts["reports"], f"required {args.primary_spec} report")
    add_exists_checks(checks, artifacts["submissions"], f"required {args.primary_spec} submission")

    validate_feature_alignment(checks)
    validate_model_config(checks, artifacts["config_candidates"])
    validate_submission_file(checks, artifacts["submission_path"], artifacts["label"])
    validate_oof_coverage(checks, artifacts["oof_path"], artifacts["label"])

    if artifacts["cv_path"].exists():
        cv = pd.read_csv(artifacts["cv_path"])
        checks.append(
            {
                "check": f"per-well {args.primary_spec} residual CV is finite",
                "status": pass_fail("rmse" in cv.columns and np.isfinite(cv["rmse"].to_numpy(dtype=float)).all()),
                "evidence": f"wells={cv['well'].nunique() if 'well' in cv else 'unknown'}",
            }
        )

    if args.primary_spec != "xgb":
        validate_optional_xgb(checks)

    report_texts = [path.read_text(encoding="utf-8") for path in artifacts["reports"] if path.exists()]
    joined_reports = "\n".join(report_texts)
    checks.append(
        {
            "check": "reports describe residual CV metrics",
            "status": pass_fail("RMSE" in joined_reports or "OOF RMSE" in joined_reports),
        }
    )

    checks_df = pd.DataFrame(checks)
    failed = checks_df[checks_df["status"].eq("FAIL")]
    lines = [
        "# Part 2 Completion Audit",
        "",
        f"- Primary spec: `{args.primary_spec}`",
        f"- Checks: {len(checks_df)}",
        f"- Failures: {len(failed)}",
        "",
        "## Checks",
        "",
        markdown_table(checks_df.fillna(""), index=False),
        "",
        "## Result",
        "",
        "PASS" if len(failed) == 0 else "FAIL",
        "",
    ]
    AUDIT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {AUDIT_PATH}")
    print(f"checks={len(checks_df)} failures={len(failed)}")
    return 1 if len(failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
