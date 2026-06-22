#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pandas.api.types import is_numeric_dtype

from data_paths import load_sample_submission, resolve_sample_submission_path
from rogii_utils import (
    DATA_DIR,
    DATA_VERSION_PATH,
    OUTPUT_DIR,
    REPORT_DIR,
    ROOT,
    TEST_DIR,
    TEST_HORIZONTAL_COLUMNS,
    TEST_TYPEWELL_COLUMNS,
    TRAIN_DIR,
    TRAIN_HORIZONTAL_COLUMNS,
    TYPEWELL_COLUMNS,
    ensure_project_dirs,
    missing_rate,
    parse_submission_ids,
    sha256_file,
    well_id_from_path,
)


SUMMARY_PATH = OUTPUT_DIR / "data_contract_summary.csv"
REPORT_PATH = REPORT_DIR / "data_contract_report.md"
EDA_REPORT_PATH = REPORT_DIR / "eda_summary.md"
ZIP_PATH = ROOT / "data" / "rogii-wellbore-geology-prediction.zip"
EXPECTED_COUNTS = {
    "train_horizontal": 773,
    "train_typewell": 773,
    "train_png": 773,
    "test_horizontal": 3,
    "test_typewell": 3,
}


def collect_wells(pattern: str, directory: Path) -> dict[str, Path]:
    return {well_id_from_path(path): path for path in sorted(directory.glob(pattern))}


def parse_eda_inventory() -> dict[str, int]:
    if not EDA_REPORT_PATH.exists():
        return {}
    text = EDA_REPORT_PATH.read_text()
    patterns = {
        "train_horizontal": r"Train horizontal CSV files:\s*([\d,]+)",
        "train_typewell": r"Train typewell CSV files:\s*([\d,]+)",
        "train_png": r"Train PNG visualizations:\s*([\d,]+)",
        "test_horizontal": r"Visible test horizontal CSV files:\s*([\d,]+)",
        "test_typewell": r"Visible test typewell CSV files:\s*([\d,]+)",
        "sample_submission_rows": r"Sample submission rows:\s*([\d,]+)",
    }
    values: dict[str, int] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            values[key] = int(match.group(1).replace(",", ""))
    return values


def check_columns(path: Path, required_columns: list[str], split: str, kind: str) -> dict[str, object]:
    df = pd.read_csv(path)
    missing_columns = [col for col in required_columns if col not in df.columns]
    all_empty_columns = [col for col in required_columns if col in df.columns and bool(df[col].isna().all())]
    dtype_warnings = []
    for col in required_columns:
        if col not in df.columns:
            continue
        if col != "Geology" and not is_numeric_dtype(df[col]):
            dtype_warnings.append(f"{col}:{df[col].dtype}")

    md_monotonic = None
    if "MD" in df.columns:
        md_monotonic = bool(df["MD"].is_monotonic_increasing)

    row_index_continuous = bool((df.index.to_numpy() == range(len(df))).all())

    return {
        "split": split,
        "kind": kind,
        "well": well_id_from_path(path),
        "path": str(path.relative_to(ROOT)),
        "rows": len(df),
        "columns": len(df.columns),
        "missing_columns": ",".join(missing_columns),
        "all_empty_columns": ",".join(all_empty_columns),
        "dtype_warnings": ",".join(dtype_warnings),
        "tvt_input_missing_rate": missing_rate(df["TVT_input"]) if "TVT_input" in df else None,
        "gr_missing_rate": missing_rate(df["GR"]) if "GR" in df else None,
        "md_monotonic": md_monotonic,
        "row_index_continuous": row_index_continuous,
        "critical_error_count": len(missing_columns),
        "warning_count": len(all_empty_columns) + len(dtype_warnings) + (0 if md_monotonic in {True, None} else 1),
    }


def write_data_version(train_horizontal: dict[str, Path], test_horizontal: dict[str, Path], sample_rows: int) -> dict[str, object]:
    raw_files = [path for path in DATA_DIR.rglob("*") if path.is_file()]
    data_version = {
        "zip_path": str(ZIP_PATH.relative_to(ROOT)) if ZIP_PATH.exists() else None,
        "zip_size_bytes": ZIP_PATH.stat().st_size if ZIP_PATH.exists() else None,
        "zip_sha256": sha256_file(ZIP_PATH) if ZIP_PATH.exists() else None,
        "raw_file_count": len(raw_files),
        "train_well_count": len(train_horizontal),
        "test_well_count": len(test_horizontal),
        "sample_submission_rows": sample_rows,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    DATA_VERSION_PATH.write_text(json.dumps(data_version, indent=2, ensure_ascii=False) + "\n")
    return data_version


def main() -> int:
    ensure_project_dirs()

    train_horizontal = collect_wells("*__horizontal_well.csv", TRAIN_DIR)
    train_typewell = collect_wells("*__typewell.csv", TRAIN_DIR)
    train_png = {well_id_from_path(path): path for path in sorted(TRAIN_DIR.glob("*.png"))}
    test_horizontal = collect_wells("*__horizontal_well.csv", TEST_DIR)
    test_typewell = collect_wells("*__typewell.csv", TEST_DIR)

    critical_errors: list[str] = []
    warnings: list[str] = []
    records: list[dict[str, object]] = []

    for key, expected in EXPECTED_COUNTS.items():
        actual = {
            "train_horizontal": len(train_horizontal),
            "train_typewell": len(train_typewell),
            "train_png": len(train_png),
            "test_horizontal": len(test_horizontal),
            "test_typewell": len(test_typewell),
        }[key]
        if actual != expected:
            critical_errors.append(f"{key} count mismatch: expected {expected}, actual {actual}")

    for well in sorted(set(train_horizontal) | set(train_typewell) | set(train_png)):
        missing = []
        if well not in train_horizontal:
            missing.append("horizontal")
        if well not in train_typewell:
            missing.append("typewell")
        if well not in train_png:
            missing.append("png")
        if missing:
            critical_errors.append(f"train well {well} missing {','.join(missing)}")
        else:
            records.append(check_columns(train_horizontal[well], TRAIN_HORIZONTAL_COLUMNS, "train", "horizontal"))
            records.append(check_columns(train_typewell[well], TYPEWELL_COLUMNS, "train", "typewell"))

    for well in sorted(set(test_horizontal) | set(test_typewell)):
        missing = []
        if well not in test_horizontal:
            missing.append("horizontal")
        if well not in test_typewell:
            missing.append("typewell")
        if missing:
            critical_errors.append(f"test well {well} missing {','.join(missing)}")
        else:
            records.append(check_columns(test_horizontal[well], TEST_HORIZONTAL_COLUMNS, "test", "horizontal"))
            records.append(check_columns(test_typewell[well], TEST_TYPEWELL_COLUMNS, "test", "typewell"))
            test_typewell_columns = pd.read_csv(test_typewell[well], nrows=0).columns.tolist()
            if "Geology" not in test_typewell_columns:
                warnings.append(
                    f"test well {well} typewell has no Geology column; TVT/GR are available and Geology is optional in visible test"
                )

    sample_rows = 0
    try:
        sample_path = resolve_sample_submission_path()
        sample = pd.read_csv(sample_path)
    except FileNotFoundError:
        sample_path = None
        sample = load_sample_submission()
        warnings.append("sample_submission.csv is missing; synthesized submission ids from data/test hidden TVT_input rows")
    if len(sample):
        sample_rows = len(sample)
        try:
            parsed = parse_submission_ids(sample)
        except Exception as exc:
            critical_errors.append(f"sample_submission id parse failed: {exc}")
            parsed = pd.DataFrame()
        if len(parsed):
            unknown_wells = sorted(set(parsed["well"]) - set(test_horizontal))
            if unknown_wells:
                critical_errors.append(f"sample_submission contains wells not in test: {unknown_wells[:10]}")
            for well, part in parsed.groupby("well"):
                if well not in test_horizontal:
                    continue
                rows = len(pd.read_csv(test_horizontal[well], usecols=["MD"]))
                invalid = part[(part["row"] < 0) | (part["row"] >= rows)]
                if len(invalid):
                    critical_errors.append(f"sample_submission has {len(invalid)} invalid row ids for well {well}")

    data_version = write_data_version(train_horizontal, test_horizontal, sample_rows)
    actual_counts = {
        "train_horizontal": len(train_horizontal),
        "train_typewell": len(train_typewell),
        "train_png": len(train_png),
        "test_horizontal": len(test_horizontal),
        "test_typewell": len(test_typewell),
        "sample_submission_rows": sample_rows,
    }
    eda_inventory = parse_eda_inventory()
    eda_inventory_rows = []
    if eda_inventory:
        for key, actual in actual_counts.items():
            eda_value = eda_inventory.get(key)
            matches = eda_value == actual
            eda_inventory_rows.append({"item": key, "eda_report": eda_value, "contract_actual": actual, "matches": matches})
            if not matches:
                critical_errors.append(f"EDA inventory mismatch for {key}: eda={eda_value}, actual={actual}")
    else:
        warnings.append("reports/eda_summary.md is missing or inventory could not be parsed; data contract cannot compare against EDA report")

    summary = pd.DataFrame(records)
    if len(summary):
        critical_errors.extend(
            summary.loc[summary["critical_error_count"] > 0, ["path", "missing_columns"]]
            .apply(lambda row: f"{row['path']} missing columns: {row['missing_columns']}", axis=1)
            .tolist()
        )
        warnings.extend(
            summary.loc[summary["warning_count"] > 0, ["path", "all_empty_columns", "dtype_warnings", "md_monotonic"]]
            .apply(
                lambda row: (
                    f"{row['path']} warnings: all_empty={row['all_empty_columns'] or '-'}, "
                    f"dtype={row['dtype_warnings'] or '-'}, md_monotonic={row['md_monotonic']}"
                ),
                axis=1,
            )
            .tolist()
        )
    summary.to_csv(SUMMARY_PATH, index=False)

    inventory = pd.DataFrame(
        [
            {"item": "train_horizontal", "expected": EXPECTED_COUNTS["train_horizontal"], "actual": len(train_horizontal)},
            {"item": "train_typewell", "expected": EXPECTED_COUNTS["train_typewell"], "actual": len(train_typewell)},
            {"item": "train_png", "expected": EXPECTED_COUNTS["train_png"], "actual": len(train_png)},
            {"item": "test_horizontal", "expected": EXPECTED_COUNTS["test_horizontal"], "actual": len(test_horizontal)},
            {"item": "test_typewell", "expected": EXPECTED_COUNTS["test_typewell"], "actual": len(test_typewell)},
            {"item": "sample_submission_rows", "expected": None, "actual": sample_rows},
        ]
    )

    horizontal_summary = (
        summary[summary["kind"].eq("horizontal")]
        .groupby("split", dropna=False)
        .agg(
            files=("path", "count"),
            rows=("rows", "sum"),
            tvt_input_missing_rate=("tvt_input_missing_rate", "mean"),
            gr_missing_rate=("gr_missing_rate", "mean"),
            critical_errors=("critical_error_count", "sum"),
            warnings=("warning_count", "sum"),
        )
        .reset_index()
        if len(summary)
        else pd.DataFrame()
    )
    eda_inventory_summary = pd.DataFrame(eda_inventory_rows)

    lines = [
        "# Data Contract Report",
        "",
        "## Data Version",
        "",
        f"- Zip path: `{data_version['zip_path']}`",
        f"- Zip size bytes: {data_version['zip_size_bytes']}",
        f"- Zip SHA256: `{data_version['zip_sha256']}`",
        f"- Raw file count: {data_version['raw_file_count']}",
        f"- Created at UTC: {data_version['created_at']}",
        "",
        "## File Inventory",
        "",
        inventory.to_markdown(index=False),
        "",
        "## Horizontal Summary",
        "",
        horizontal_summary.round(4).to_markdown(index=False) if len(horizontal_summary) else "_No files checked._",
        "",
        "## EDA Inventory Cross-Check",
        "",
        eda_inventory_summary.to_markdown(index=False) if len(eda_inventory_summary) else "_EDA inventory was not available._",
        "",
        "## Contract Result",
        "",
        f"- Critical errors: {len(critical_errors)}",
        f"- Warnings: {len(warnings)}",
        f"- Summary CSV: `{SUMMARY_PATH.relative_to(ROOT)}`",
        f"- Data version JSON: `{DATA_VERSION_PATH.relative_to(ROOT)}`",
        "",
        "## Critical Errors",
        "",
    ]
    lines.extend([f"- {item}" for item in critical_errors] or ["- None"])
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in warnings[:100]] or ["- None"])
    if len(warnings) > 100:
        lines.append(f"- ... {len(warnings) - 100} additional warnings omitted from report; see summary CSV.")
    lines.extend(
        [
            "",
            "## Downstream Rule",
            "",
            "All training and validation scripts must read `outputs/data_version.json` and write the same hash into their reports. If this hash changes, old model metrics are not directly comparable.",
            "",
            "## Test Typewell Boundary",
            "",
            "Visible test typewell files contain `TVT` and `GR` but not `Geology`. The contract treats `Geology` as required for training typewell files and optional for test typewell files, so modeling code must not assume test Geology labels are available.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines))

    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {DATA_VERSION_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"critical_errors={len(critical_errors)} warnings={len(warnings)}")
    return 1 if critical_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
