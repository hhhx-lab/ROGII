#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from part2_utils import FEATURE_DIR, MODEL_DIR, OUTPUT_DIR, REPORT_DIR, ROOT
from rogii_utils import DATA_DIR, SUBMISSION_DIR, assert_data_contract_ready, parse_submission_ids


AUDIT_PATH = REPORT_DIR / "part2_completion_audit.md"
REQUIRED_FEATURES = [
    FEATURE_DIR / "baseline_features_train.parquet",
    FEATURE_DIR / "baseline_features_test.parquet",
    FEATURE_DIR / "geometry_features_train.parquet",
    FEATURE_DIR / "geometry_features_test.parquet",
    FEATURE_DIR / "residual_targets.parquet",
]
REQUIRED_MODELS = [
    MODEL_DIR / "residual_geometry_hgb.pkl",
    MODEL_DIR / "residual_geometry_config.json",
    MODEL_DIR / "residual_geometry_feature_list.txt",
]
REQUIRED_OUTPUTS = [
    OUTPUT_DIR / "residual_geometry_oof.csv",
    OUTPUT_DIR / "residual_geometry_cv_by_well.csv",
    OUTPUT_DIR / "residual_geometry_test_predictions.csv",
    OUTPUT_DIR / "residual_geometry_multimask_by_split.csv",
    OUTPUT_DIR / "residual_geometry_multimask_overall.csv",
]
REQUIRED_REPORTS = [
    REPORT_DIR / "residual_target_report.md",
    REPORT_DIR / "residual_geometry_cv_report.md",
    REPORT_DIR / "residual_geometry_failure_analysis.md",
    REPORT_DIR / "residual_geometry_feature_importance.md",
    REPORT_DIR / "residual_geometry_multimask_report.md",
    REPORT_DIR / "residual_geometry_server_runbook.md",
]
REQUIRED_SUBMISSIONS = [SUBMISSION_DIR / "geometry_residual_submission.csv"]


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def count_csv_rows(path: Path) -> int:
    with path.open("rb") as handle:
        line_count = sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1024 * 1024), b""))
    return max(0, line_count - 1)


def main() -> int:
    assert_data_contract_ready()
    checks: list[dict[str, object]] = []

    for path in REQUIRED_FEATURES:
        checks.append({"check": f"required feature exists: {path.relative_to(ROOT)}", "status": pass_fail(path.exists())})
    for path in REQUIRED_MODELS:
        checks.append({"check": f"required model artifact exists: {path.relative_to(ROOT)}", "status": pass_fail(path.exists())})
    for path in REQUIRED_OUTPUTS:
        checks.append({"check": f"required output exists: {path.relative_to(ROOT)}", "status": pass_fail(path.exists())})
    for path in REQUIRED_REPORTS:
        checks.append({"check": f"required report exists: {path.relative_to(ROOT)}", "status": pass_fail(path.exists())})
    for path in REQUIRED_SUBMISSIONS:
        checks.append({"check": f"required submission exists: {path.relative_to(ROOT)}", "status": pass_fail(path.exists())})

    if all(path.exists() for path in REQUIRED_FEATURES):
        baseline_train = pd.read_parquet(FEATURE_DIR / "baseline_features_train.parquet", columns=["id", "well", "row"])
        geometry_train = pd.read_parquet(FEATURE_DIR / "geometry_features_train.parquet", columns=["id", "well", "row"])
        targets = pd.read_parquet(FEATURE_DIR / "residual_targets.parquet", columns=["id", "well", "row", "residual_target"])
        baseline_test = pd.read_parquet(FEATURE_DIR / "baseline_features_test.parquet", columns=["id", "well", "row"])
        geometry_test = pd.read_parquet(FEATURE_DIR / "geometry_features_test.parquet", columns=["id", "well", "row"])
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
                "check": "features cover 773 train wells",
                "status": pass_fail(targets["well"].nunique() == 773),
                "evidence": int(targets["well"].nunique()),
            }
        )

    config_path = MODEL_DIR / "residual_geometry_config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        feature_columns = list(config.get("feature_columns", []))
        forbidden = {"well", "ANCC", "ASTNU", "ASTNL", "EGFDU", "EGFDL", "BUDA", "TVT", "TVT_input"}
        checks.append(
            {
                "check": "model config records feature columns and selected alpha",
                "status": pass_fail(bool(feature_columns) and "selected_alpha" in config),
                "evidence": f"features={len(feature_columns)}, alpha={config.get('selected_alpha')}",
            }
        )
        checks.append(
            {
                "check": "feature list excludes well id, truth and training-only formation surfaces",
                "status": pass_fail(not (forbidden & set(feature_columns))),
                "evidence": ",".join(sorted(forbidden & set(feature_columns))),
            }
        )
        runbook = (REPORT_DIR / "residual_geometry_server_runbook.md").read_text() if (REPORT_DIR / "residual_geometry_server_runbook.md").exists() else ""
        checks.append(
            {
                "check": "server runbook documents full-row training command",
                "status": pass_fail("ROGII_PART2_TRAIN_ROWS_PER_WELL=0" in runbook),
            }
        )

    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    if (SUBMISSION_DIR / "geometry_residual_submission.csv").exists():
        submission = pd.read_csv(SUBMISSION_DIR / "geometry_residual_submission.csv")
        checks.append(
            {
                "check": "geometry residual submission matches sample format",
                "status": pass_fail(len(submission) == len(sample) and list(submission.columns) == list(sample.columns) and submission["tvt"].notna().all()),
                "evidence": f"rows={len(submission)}",
            }
        )
        checks.append(
            {
                "check": "geometry residual submission covers sample wells",
                "status": pass_fail(parse_submission_ids(submission)["well"].nunique() == parse_submission_ids(sample)["well"].nunique()),
                "evidence": int(parse_submission_ids(submission)["well"].nunique()),
            }
        )

    if (OUTPUT_DIR / "residual_geometry_oof.csv").exists() and (FEATURE_DIR / "residual_targets.parquet").exists():
        target_rows = len(pd.read_parquet(FEATURE_DIR / "residual_targets.parquet", columns=["id"]))
        oof_rows = count_csv_rows(OUTPUT_DIR / "residual_geometry_oof.csv")
        checks.append(
            {
                "check": "OOF predictions cover every residual target row",
                "status": pass_fail(oof_rows == target_rows),
                "evidence": f"oof={oof_rows}, targets={target_rows}",
            }
        )

    if (OUTPUT_DIR / "residual_geometry_cv_by_well.csv").exists():
        cv = pd.read_csv(OUTPUT_DIR / "residual_geometry_cv_by_well.csv")
        checks.append(
            {
                "check": "per-well residual CV covers 773 wells",
                "status": pass_fail(cv["well"].nunique() == 773),
                "evidence": int(cv["well"].nunique()),
            }
        )

    multimask_overall_path = OUTPUT_DIR / "residual_geometry_multimask_overall.csv"
    multimask_by_split_path = OUTPUT_DIR / "residual_geometry_multimask_by_split.csv"
    if multimask_overall_path.exists() and multimask_by_split_path.exists():
        required_masks = {"original_hidden", "trailing_short", "trailing_long", "mid_contiguous", "random_contiguous"}
        overall = pd.read_csv(multimask_overall_path)
        by_split = pd.read_csv(multimask_by_split_path)
        checks.append(
            {
                "check": "multi-mask residual validation covers required mask types",
                "status": pass_fail(required_masks.issubset(set(overall["mask_type"]))),
                "evidence": ",".join(sorted(set(overall["mask_type"]))),
            }
        )
        split_counts = by_split.groupby("mask_type")["split_id"].nunique().to_dict()
        checks.append(
            {
                "check": "multi-mask residual validation covers every train well per mask",
                "status": pass_fail(all(split_counts.get(mask, 0) == 773 for mask in required_masks)),
                "evidence": json.dumps(split_counts, sort_keys=True),
            }
        )
        checks.append(
            {
                "check": "multi-mask residual metrics are finite",
                "status": pass_fail(overall[["baseline_rmse", "geometry_rmse", "rmse_improvement"]].notna().all().all()),
            }
        )

    report_texts = []
    for path in REQUIRED_REPORTS:
        if path.exists():
            report_texts.append(path.read_text())
    joined_reports = "\n".join(report_texts)
    checks.append(
        {
            "check": "reports state promotion decision or server readiness",
            "status": pass_fail("Promotion decision" in joined_reports and "Full-Row Training" in joined_reports),
        }
    )

    checks_df = pd.DataFrame(checks)
    failed = checks_df[checks_df["status"].eq("FAIL")]
    lines = [
        "# Part 2 Completion Audit",
        "",
        f"- Checks: {len(checks_df)}",
        f"- Failures: {len(failed)}",
        "",
        "## Checks",
        "",
        checks_df.fillna("").to_markdown(index=False),
        "",
        "## Result",
        "",
        "PASS" if len(failed) == 0 else "FAIL",
        "",
    ]
    AUDIT_PATH.write_text("\n".join(lines))
    print(f"Wrote {AUDIT_PATH}")
    print(f"checks={len(checks_df)} failures={len(failed)}")
    return 1 if len(failed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
