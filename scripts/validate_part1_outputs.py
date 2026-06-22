#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_paths import load_sample_submission
from rogii_utils import (
    OUTPUT_DIR,
    REPORT_DIR,
    ROOT,
    SUBMISSION_DIR,
    TEST_DIR,
    TRAIN_DIR,
    apply_cv_split_mask,
    assert_data_contract_ready,
    data_hash_short,
    parse_submission_ids,
    split_target_rows,
)


AUDIT_PATH = REPORT_DIR / "part1_completion_audit.md"
PROGRESS_PATH = ROOT / "docs" / "plans" / "01_validation_baseline_progress.md"
REQUIRED_OUTPUTS = [
    OUTPUT_DIR / "data_contract_summary.csv",
    OUTPUT_DIR / "data_version.json",
    OUTPUT_DIR / "baseline_cv_by_well.csv",
    OUTPUT_DIR / "baseline_predictions_train_hidden.csv",
    OUTPUT_DIR / "cv_splits.csv",
    OUTPUT_DIR / "failure_case_candidates.csv",
]
REQUIRED_REPORTS = [
    REPORT_DIR / "data_contract_report.md",
    REPORT_DIR / "baseline_cv_report.md",
    REPORT_DIR / "cv_design.md",
    REPORT_DIR / "baseline_failure_analysis.md",
    REPORT_DIR / "baseline_multimask_report.md",
    REPORT_DIR / "baseline_submission_report.md",
    REPORT_DIR / "part1_quality_review.md",
    REPORT_DIR / "data_raw_review.md",
    REPORT_DIR / "part1_plan_implementation_review.md",
]
SUBMISSION_FILES = [
    SUBMISSION_DIR / "b0_constant_last_submission.csv",
    SUBMISSION_DIR / "b1_linear_md_submission.csv",
    SUBMISSION_DIR / "b2_tail_slope_k50_submission.csv",
    SUBMISSION_DIR / "b2_tail_slope_k100_submission.csv",
    SUBMISSION_DIR / "b2_tail_slope_k200_submission.csv",
    SUBMISSION_DIR / "b2_tail_slope_k500_submission.csv",
    SUBMISSION_DIR / "baseline_tail_slope_submission.csv",
]


def count_csv_rows(path: Path) -> int:
    with path.open("rb") as handle:
        line_count = sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1024 * 1024), b""))
    return max(0, line_count - 1)


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def main() -> int:
    checks: list[dict[str, object]] = []

    for path in REQUIRED_OUTPUTS:
        checks.append({"check": f"required output exists: {path.relative_to(ROOT)}", "status": pass_fail(path.exists())})
    for path in REQUIRED_REPORTS:
        checks.append({"check": f"required report exists: {path.relative_to(ROOT)}", "status": pass_fail(path.exists())})
    checks.append({"check": f"progress document exists: {PROGRESS_PATH.relative_to(ROOT)}", "status": pass_fail(PROGRESS_PATH.exists())})

    data_version = assert_data_contract_ready()
    data_hash = data_hash_short(data_version)
    required_version_fields = {
        "zip_path",
        "zip_size_bytes",
        "zip_sha256",
        "raw_file_count",
        "train_well_count",
        "test_well_count",
        "sample_submission_rows",
        "created_at",
    }
    checks.append(
        {
            "check": "data_version contains required fields",
            "status": pass_fail(required_version_fields.issubset(data_version)),
            "evidence": ",".join(sorted(data_version.keys())),
        }
    )
    checks.append({"check": "train_well_count == 773", "status": pass_fail(data_version.get("train_well_count") == 773)})
    checks.append({"check": "test_well_count == 3", "status": pass_fail(data_version.get("test_well_count") == 3)})

    contract = pd.read_csv(OUTPUT_DIR / "data_contract_summary.csv")
    checks.append(
        {
            "check": "data contract critical errors == 0",
            "status": pass_fail(int(contract["critical_error_count"].sum()) == 0),
            "evidence": int(contract["critical_error_count"].sum()),
        }
    )
    contract_report = (REPORT_DIR / "data_contract_report.md").read_text()
    checks.append(
        {
            "check": "data contract compares against EDA inventory",
            "status": pass_fail("## EDA Inventory Cross-Check" in contract_report and "| False" not in contract_report),
        }
    )
    checks.append(
        {
            "check": "data contract documents optional test typewell Geology",
            "status": pass_fail("optional for test typewell files" in contract_report and "must not assume test Geology" in contract_report),
        }
    )
    raw_review = (REPORT_DIR / "data_raw_review.md").read_text()
    checks.append(
        {
            "check": "raw-data review documents PPTX and sample submission",
            "status": pass_fail("PPTX 共 14 页" in raw_review and "sample_submission.csv" in raw_review),
        }
    )
    checks.append(
        {
            "check": "raw-data review marks visible test as sanity only",
            "status": pass_fail("visible test 只能用于提交格式" in raw_review and "不能当作独立验证集" in raw_review),
        }
    )

    detail = pd.read_csv(OUTPUT_DIR / "baseline_cv_by_well.csv")
    baseline_families = set(detail["family"].dropna().astype(str))
    baseline_names = set(detail["baseline"].dropna().astype(str))
    checks.append(
        {
            "check": "baseline CV covers 773 wells for every baseline",
            "status": pass_fail(detail.groupby("baseline")["well"].nunique().min() == 773),
            "evidence": int(detail.groupby("baseline")["well"].nunique().min()),
        }
    )
    checks.append(
        {
            "check": "baseline families include B0/B1/B2",
            "status": pass_fail({"B0", "B1", "B2"}.issubset(baseline_families)),
            "evidence": ",".join(sorted(baseline_families)),
        }
    )
    checks.append(
        {
            "check": "baseline configs include B2 K variants",
            "status": pass_fail(
                {
                    "B2_tail_slope_k50",
                    "B2_tail_slope_k100",
                    "B2_tail_slope_k200",
                    "B2_tail_slope_k500",
                }.issubset(baseline_names)
            ),
            "evidence": ",".join(sorted(baseline_names)),
        }
    )

    expected_prediction_rows = int(detail["target_rows"].sum())
    actual_prediction_rows = count_csv_rows(OUTPUT_DIR / "baseline_predictions_train_hidden.csv")
    checks.append(
        {
            "check": "row-level baseline predictions cover every target row and baseline",
            "status": pass_fail(actual_prediction_rows == expected_prediction_rows),
            "evidence": f"actual={actual_prediction_rows}, expected={expected_prediction_rows}",
        }
    )

    splits = pd.read_csv(OUTPUT_DIR / "cv_splits.csv")
    mask_coverage = splits.groupby("mask_type")["well"].nunique()
    checks.append(
        {
            "check": "cv_splits has at least 5 mask types",
            "status": pass_fail(splits["mask_type"].nunique() >= 5),
            "evidence": int(splits["mask_type"].nunique()),
        }
    )
    checks.append(
        {
            "check": "each mask type covers at least 300 wells",
            "status": pass_fail(int(mask_coverage.min()) >= 300),
            "evidence": int(mask_coverage.min()),
        }
    )
    checks.append(
        {
            "check": "cv_splits has leakage boundary columns",
            "status": pass_fail({"known_allowed_start_row", "known_allowed_end_row"}.issubset(splits.columns)),
        }
    )
    mask_leakage_ok = True
    mask_evidence = []
    for mask_type, split in splits.groupby("mask_type", sort=True).head(1).groupby("mask_type"):
        row = split.iloc[0]
        df = pd.read_csv(TRAIN_DIR / f"{row['well']}__horizontal_well.csv")
        masked = apply_cv_split_mask(df, row, replace_tvt_input=False)
        targets = split_target_rows(row)
        known_start = int(row["known_allowed_start_row"])
        known_end = int(row["known_allowed_end_row"])
        target_is_hidden = bool(masked.loc[targets, "TVT_input_masked"].isna().all())
        future_is_hidden = bool(masked.loc[known_end + 1 :, "TVT_input_masked"].isna().all()) if known_end + 1 < len(masked) else True
        known_is_visible = bool(masked.loc[known_start:known_end, "TVT_input_masked"].notna().all()) if known_end >= known_start else True
        ok = target_is_hidden and future_is_hidden and known_is_visible
        mask_leakage_ok = mask_leakage_ok and ok
        mask_evidence.append(f"{mask_type}:{ok}")
    checks.append(
        {
            "check": "apply_cv_split_mask hides target and future TVT_input",
            "status": pass_fail(mask_leakage_ok),
            "evidence": ",".join(mask_evidence),
        }
    )
    cv_report = (REPORT_DIR / "cv_design.md").read_text()
    checks.append(
        {
            "check": "truth-derived split diagnostics are documented as non-features",
            "status": pass_fail("truth-derived diagnostics" in cv_report and "must not read them as predictors" in cv_report),
        }
    )
    checks.append(
        {
            "check": "cv_design documents official-tail priority and stress masks",
            "status": pass_fail("Primary leaderboard proxy masks" in cv_report and "Robustness stress-test masks" in cv_report),
        }
    )
    checks.append(
        {
            "check": "cv_design documents optional Geology boundary",
            "status": pass_fail("optional on test typewell files" in cv_report and "Geology-derived columns" in cv_report),
        }
    )

    multimask = pd.read_csv(OUTPUT_DIR / "baseline_multimask_overall.csv")
    checks.append(
        {
            "check": "multi-mask baseline metrics cover all split mask types",
            "status": pass_fail(multimask["mask_type"].nunique() == splits["mask_type"].nunique()),
            "evidence": int(multimask["mask_type"].nunique()),
        }
    )

    failures = pd.read_csv(OUTPUT_DIR / "failure_case_candidates.csv")
    figure_count = len(list((REPORT_DIR / "figures" / "baseline_worst_wells").glob("*.png")))
    checks.append(
        {
            "check": "failure candidates cover 773 wells",
            "status": pass_fail(failures["well"].nunique() == 773),
            "evidence": int(failures["well"].nunique()),
        }
    )
    checks.append(
        {
            "check": "worst-well diagnostic figures count >= 20",
            "status": pass_fail(figure_count >= 20),
            "evidence": figure_count,
        }
    )
    checks.append(
        {
            "check": "failure types are populated",
            "status": pass_fail(failures["failure_type"].notna().all() and failures["failure_type"].nunique() >= 3),
            "evidence": ",".join(sorted(failures["failure_type"].dropna().unique())),
        }
    )
    typewell_columns = {"typewell_rows", "typewell_tvt_span", "typewell_gr_missing_rate", "typewell_geology_label_count", "typewell_geology_labels"}
    checks.append(
        {
            "check": "failure candidates include typewell and Geology diagnostics",
            "status": pass_fail(typewell_columns.issubset(failures.columns) and failures["typewell_geology_label_count"].gt(0).all()),
            "evidence": ",".join(sorted(typewell_columns & set(failures.columns))),
        }
    )
    plan_review = (REPORT_DIR / "part1_plan_implementation_review.md").read_text()
    checks.append(
        {
            "check": "part1 plan implementation review passes",
            "status": pass_fail("- Status: PASS" in plan_review and "Visible test wells overlap training IDs" in plan_review),
        }
    )

    sample = load_sample_submission()
    parsed_sample = parse_submission_ids(sample)
    sample_wells = set(parsed_sample["well"])
    train_well_ids = {path.name.replace("__horizontal_well.csv", "") for path in TRAIN_DIR.glob("*__horizontal_well.csv")}
    test_typewell_has_no_geology = all(
        "Geology" not in pd.read_csv(TEST_DIR / f"{well}__typewell.csv", nrows=0).columns
        for well in sample_wells
    )
    checks.append(
        {
            "check": "visible sample wells overlap train and are not independent validation",
            "status": pass_fail(sample_wells.issubset(train_well_ids)),
            "evidence": ",".join(sorted(sample_wells)),
        }
    )
    checks.append(
        {
            "check": "visible test typewell lacks Geology and scripts must fallback",
            "status": pass_fail(test_typewell_has_no_geology),
            "evidence": f"wells={len(sample_wells)}",
        }
    )
    submission_report = (REPORT_DIR / "baseline_submission_report.md").read_text()
    checks.append(
        {
            "check": "submission report marks visible examples as sanity only",
            "status": pass_fail("sanity checks only" in submission_report and "do not tune" in submission_report),
        }
    )
    for path in SUBMISSION_FILES:
        exists = path.exists()
        if exists:
            submission = pd.read_csv(path)
            valid = len(submission) == len(sample) and list(submission.columns) == list(sample.columns) and submission["tvt"].notna().all()
            well_count = parse_submission_ids(submission)["well"].nunique()
            evidence = f"rows={len(submission)}, wells={well_count}"
        else:
            valid = False
            well_count = 0
            evidence = "missing"
        checks.append(
            {
                "check": f"submission valid: {path.relative_to(ROOT)}",
                "status": pass_fail(valid and parsed_sample["well"].nunique() == well_count),
                "evidence": evidence,
            }
        )

    checks_df = pd.DataFrame(checks)
    failed = checks_df[checks_df["status"].eq("FAIL")]
    lines = [
        "# Part 1 Completion Audit",
        "",
        f"- Data hash: `{data_hash}`",
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
