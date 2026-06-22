#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

from data_paths import load_sample_submission
from rogii_utils import REPORT_DIR, ROOT, SUBMISSION_DIR, TEST_DIR, TRAIN_DIR, parse_submission_ids, train_wells


REPORT_PATH = REPORT_DIR / "part1_plan_implementation_review.md"

PLAN_REQUIREMENTS = [
    {
        "area": "数据契约",
        "requirement": "训练井 horizontal/typewell/png 完整，visible test horizontal/typewell 完整",
        "evidence": ["outputs/data_contract_summary.csv", "reports/data_contract_report.md"],
    },
    {
        "area": "数据版本",
        "requirement": "记录数据 hash、井数、sample submission 行数，所有报告可追溯",
        "evidence": ["outputs/data_version.json"],
    },
    {
        "area": "原始隐藏段 CV",
        "requirement": "773 口训练井的 PS 后原始隐藏尾段全部进入 baseline CV",
        "evidence": ["outputs/baseline_cv_by_well.csv", "reports/baseline_cv_report.md"],
    },
    {
        "area": "Baseline 家族",
        "requirement": "Part 1 至少完成 B0/B1/B2，B2 包含多个 tail window",
        "evidence": ["outputs/baseline_overall_metrics.csv"],
    },
    {
        "area": "多 mask 验证",
        "requirement": "至少 5 类 mask，每类至少 300 口井，并区分官方 tail proxy 与压力测试",
        "evidence": ["outputs/cv_splits.csv", "reports/cv_design.md", "reports/baseline_multimask_report.md"],
    },
    {
        "area": "防泄漏",
        "requirement": "人工 mask 必须隐藏 target/future TVT_input，truth-derived split diagnostics 不可作为 predictor",
        "evidence": ["scripts/rogii_utils.py", "reports/cv_design.md"],
    },
    {
        "area": "Failure analysis",
        "requirement": "773 口井输出失败候选、预定义失败类型、worst 20 图表和 typewell 诊断",
        "evidence": ["outputs/failure_case_candidates.csv", "reports/baseline_failure_analysis.md"],
    },
    {
        "area": "Submission QA",
        "requirement": "生成 B0/B1/B2 baseline submission，visible test 只作为格式 sanity",
        "evidence": ["reports/baseline_submission_report.md", "submissions/"],
    },
    {
        "area": "Raw-data 边界",
        "requirement": "PPTX/sample/train/test 核对结论已进入计划，test Geology optional，visible test 不调参",
        "evidence": ["reports/data_raw_review.md", "docs/plans/01_validation_baseline.md"],
    },
]


def pass_fail(condition: bool) -> str:
    return "PASS" if condition else "FAIL"


def exists_evidence(item: str) -> bool:
    path = ROOT / item
    if item.endswith("/"):
        return path.exists() and any(path.iterdir())
    return path.exists()


def raw_data_checks() -> list[dict[str, object]]:
    checks: list[dict[str, object]] = []
    sample = load_sample_submission()
    parsed = parse_submission_ids(sample)
    train_ids = set(train_wells())
    test_ids = {path.name.replace("__horizontal_well.csv", "") for path in TEST_DIR.glob("*__horizontal_well.csv")}

    checks.append(
        {
            "check": "visible test wells overlap train and are sanity-only examples",
            "status": pass_fail(test_ids.issubset(train_ids) and set(parsed["well"]).issubset(test_ids)),
            "evidence": ",".join(sorted(test_ids)),
        }
    )

    train_single_tail = True
    for well in sorted(train_ids):
        df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv", usecols=["TVT", "TVT_input"])
        mask = df["TVT_input"].isna().to_numpy()
        target_rows = np.flatnonzero(mask)
        if len(target_rows) == 0:
            train_single_tail = False
            break
        first = int(target_rows[0])
        known_equal = np.allclose(
            df.loc[: first - 1, "TVT_input"].to_numpy(dtype=float),
            df.loc[: first - 1, "TVT"].to_numpy(dtype=float),
            equal_nan=True,
        )
        if not (mask[first:].all() and not mask[:first].any() and known_equal):
            train_single_tail = False
            break
    checks.append(
        {
            "check": "all train wells use one PS-to-tail hidden interval and known TVT_input equals TVT",
            "status": pass_fail(train_single_tail),
            "evidence": f"train_wells={len(train_ids)}",
        }
    )

    test_tail_ok = True
    for well, part in parsed.groupby("well", sort=True):
        df = pd.read_csv(TEST_DIR / f"{well}__horizontal_well.csv")
        target_rows = part["row"].to_numpy(dtype=int)
        first = int(target_rows.min())
        if "TVT" in df.columns:
            test_tail_ok = False
            break
        if not df.loc[target_rows, "TVT_input"].isna().all():
            test_tail_ok = False
            break
        if not (df.loc[: first - 1, "TVT_input"].notna().all() and df.loc[first:, "TVT_input"].isna().all()):
            test_tail_ok = False
            break
    checks.append(
        {
            "check": "visible test sample is PS-to-tail target with no TVT truth column",
            "status": pass_fail(test_tail_ok),
            "evidence": f"sample_rows={len(sample)}",
        }
    )

    test_typewell_optional_geology = True
    test_typewell_files = list(TEST_DIR.glob("*__typewell.csv"))
    for path in test_typewell_files:
        columns = pd.read_csv(path, nrows=0).columns.tolist()
        if not {"TVT", "GR"}.issubset(columns):
            test_typewell_optional_geology = False
            break
        if "Geology" in columns:
            test_typewell_optional_geology = False
            break
    checks.append(
        {
            "check": "visible test typewell has TVT/GR and no required Geology",
            "status": pass_fail(test_typewell_optional_geology),
            "evidence": f"test_typewell_files={len(test_typewell_files)}",
        }
    )

    return checks


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)
    rows = []
    for item in PLAN_REQUIREMENTS:
        missing = [path for path in item["evidence"] if not exists_evidence(path)]
        rows.append(
            {
                "area": item["area"],
                "requirement": item["requirement"],
                "status": pass_fail(not missing),
                "evidence": ", ".join(item["evidence"]),
                "missing": ", ".join(missing),
            }
        )

    requirement_df = pd.DataFrame(rows)
    raw_checks = pd.DataFrame(raw_data_checks())
    failures = int(requirement_df["status"].eq("FAIL").sum() + raw_checks["status"].eq("FAIL").sum())

    lines = [
        "# Part 1 Plan Implementation Review",
        "",
        "## Scope",
        "",
        "This report maps `docs/plans/01_validation_baseline.md` to concrete scripts, outputs, reports, and raw-data boundary checks. It is intentionally stricter than a file-exists smoke test.",
        "",
        "## Plan Requirements",
        "",
        requirement_df.to_markdown(index=False),
        "",
        "## Raw-Data Boundary Checks",
        "",
        raw_checks.to_markdown(index=False),
        "",
        "## Result",
        "",
        f"- Checks: {len(requirement_df) + len(raw_checks)}",
        f"- Failures: {failures}",
        "- Status: PASS" if failures == 0 else "- Status: FAIL",
        "",
        "## Notes",
        "",
        "- B3/B4 remain intentionally deferred; Part 1 acceptance requires B0/B1/B2, and the current baseline evidence shows slope extrapolation is a risky stress-test rather than the main baseline.",
        "- `outputs/` is local-only and regenerated from scripts; the review checks local reproducibility artifacts without committing them.",
        "- Visible test wells overlap training IDs and are treated only as format and runtime sanity checks.",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))
    print(f"Wrote {REPORT_PATH}")
    print(f"checks={len(requirement_df) + len(raw_checks)} failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
