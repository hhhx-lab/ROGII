# Data Contract Report

## Data Version

- Zip path: `None`
- Zip size bytes: None
- Zip SHA256: `None`
- Raw file count: 2327
- Created at UTC: 2026-06-21T10:18:44.862212+00:00

## File Inventory

| item                   |   expected |   actual |
|:-----------------------|-----------:|---------:|
| train_horizontal       |        773 |      773 |
| train_typewell         |        773 |      773 |
| train_png              |        773 |      773 |
| test_horizontal        |          3 |        3 |
| test_typewell          |          3 |        3 |
| sample_submission_rows |        nan |    14151 |

## Horizontal Summary

| split   |   files |    rows |   tvt_input_missing_rate |   gr_missing_rate |   critical_errors |   warnings |
|:--------|--------:|--------:|-------------------------:|------------------:|------------------:|-----------:|
| test    |       3 |   19221 |                   0.732  |            0.2146 |                 0 |          0 |
| train   |     773 | 5092255 |                   0.7332 |            0.2939 |                 0 |          8 |

## EDA Inventory Cross-Check

| item                   |   eda_report |   contract_actual | matches   |
|:-----------------------|-------------:|------------------:|:----------|
| train_horizontal       |          773 |               773 | True      |
| train_typewell         |          773 |               773 | True      |
| train_png              |          773 |               773 | True      |
| test_horizontal        |            3 |                 3 | True      |
| test_typewell          |            3 |                 3 | True      |
| sample_submission_rows |        14151 |             14151 | True      |

## Contract Result

- Critical errors: 0
- Warnings: 11
- Summary CSV: `outputs\data_contract_summary.csv`
- Data version JSON: `outputs\data_version.json`

## Critical Errors

- None

## Warnings

- test well 000d7d20 typewell has no Geology column; TVT/GR are available and Geology is optional in visible test
- test well 00bbac68 typewell has no Geology column; TVT/GR are available and Geology is optional in visible test
- test well 00e12e8b typewell has no Geology column; TVT/GR are available and Geology is optional in visible test
- data\raw\train\03a935ae__horizontal_well.csv warnings: all_empty=ANCC, dtype=-, md_monotonic=True
- data\raw\train\1b1eba53__horizontal_well.csv warnings: all_empty=ANCC, dtype=-, md_monotonic=True
- data\raw\train\4c2208f5__horizontal_well.csv warnings: all_empty=ANCC, dtype=-, md_monotonic=True
- data\raw\train\727a3a10__horizontal_well.csv warnings: all_empty=ANCC, dtype=-, md_monotonic=True
- data\raw\train\81bf5923__horizontal_well.csv warnings: all_empty=ANCC, dtype=-, md_monotonic=True
- data\raw\train\9dfff011__horizontal_well.csv warnings: all_empty=EGFDL, dtype=-, md_monotonic=True
- data\raw\train\a8ed028a__horizontal_well.csv warnings: all_empty=ANCC, dtype=-, md_monotonic=True
- data\raw\train\d7eb0be8__horizontal_well.csv warnings: all_empty=ANCC, dtype=-, md_monotonic=True

## Downstream Rule

All training and validation scripts must read `outputs/data_version.json` and write the same hash into their reports. If this hash changes, old model metrics are not directly comparable.

## Test Typewell Boundary

Visible test typewell files contain `TVT` and `GR` but not `Geology`. The contract treats `Geology` as required for training typewell files and optional for test typewell files, so modeling code must not assume test Geology labels are available.
