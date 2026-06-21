#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from data_paths import load_sample_submission, resolve_competition_root


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
REPORT_PATH = REPORT_DIR / "eda_summary.md"


def pct(value: float, total: float) -> float:
    return 0.0 if total == 0 else 100.0 * value / total


def main() -> int:
    REPORT_DIR.mkdir(exist_ok=True)

    data_root = resolve_competition_root()
    train_dir = data_root / "train"
    test_dir = data_root / "test"
    sample = load_sample_submission()

    train_horizontal = sorted(train_dir.glob("*__horizontal_well.csv"))
    train_typewell = sorted(train_dir.glob("*__typewell.csv"))
    train_png = sorted(train_dir.glob("*.png"))
    test_horizontal = sorted(test_dir.glob("*__horizontal_well.csv"))
    test_typewell = sorted(test_dir.glob("*__typewell.csv"))

    train_rows = []
    missing = Counter()
    columns = None
    for path in train_horizontal:
        well = path.name.split("__")[0]
        df = pd.read_csv(path)
        columns = list(df.columns)
        train_rows.append(
            {
                "well": well,
                "rows": len(df),
                "md_min": df["MD"].min(),
                "md_max": df["MD"].max(),
                "tvt_min": df["TVT"].min(),
                "tvt_max": df["TVT"].max(),
                "gr_missing": int(df["GR"].isna().sum()),
                "tvt_input_missing": int(df["TVT_input"].isna().sum()),
            }
        )
        missing.update(df.isna().sum().to_dict())

    train_stats = pd.DataFrame(train_rows)

    test_rows = []
    for path in test_horizontal:
        well = path.name.split("__")[0]
        df = pd.read_csv(path)
        sub_rows = sample[sample["id"].str.startswith(f"{well}_")]
        test_rows.append(
            {
                "well": well,
                "rows": len(df),
                "submission_rows": len(sub_rows),
                "gr_missing": int(df["GR"].isna().sum()),
                "tvt_input_missing": int(df["TVT_input"].isna().sum()),
            }
        )
    test_stats = pd.DataFrame(test_rows)

    geology_counts = Counter()
    for path in train_typewell:
        df = pd.read_csv(path, usecols=lambda c: c in {"Geology"})
        if "Geology" in df:
            geology_counts.update(df["Geology"].dropna().astype(str).tolist())

    lines = [
        "# ROGII EDA Summary",
        "",
        "## Dataset Inventory",
        "",
        f"- Train horizontal CSV files: {len(train_horizontal)}",
        f"- Train typewell CSV files: {len(train_typewell)}",
        f"- Train PNG visualizations: {len(train_png)}",
        f"- Visible test horizontal CSV files: {len(test_horizontal)}",
        f"- Visible test typewell CSV files: {len(test_typewell)}",
        f"- Sample submission rows: {len(sample):,}",
        "",
        "## Horizontal Well Columns",
        "",
        "`" + "`, `".join(columns or []) + "`",
        "",
        "## Train Row Statistics",
        "",
        train_stats[["rows", "md_min", "md_max", "tvt_min", "tvt_max", "gr_missing", "tvt_input_missing"]]
        .describe()
        .round(2)
        .to_markdown(),
        "",
        "## Visible Test Summary",
        "",
        test_stats.to_markdown(index=False),
        "",
        "## Missing Values Across Train Horizontal Files",
        "",
        "| Column | Missing values | Missing rate |",
        "|---|---:|---:|",
    ]

    total_train_rows = int(train_stats["rows"].sum())
    for col, count in sorted(missing.items()):
        lines.append(f"| {col} | {int(count):,} | {pct(count, total_train_rows):.2f}% |")

    lines.extend(
        [
            "",
            "## Typewell Geology Labels",
            "",
            "| Label | Count |",
            "|---|---:|",
        ]
    )
    for label, count in geology_counts.most_common():
        lines.append(f"| {label} | {count:,} |")

    lines.extend(
        [
            "",
            "## First Observations",
        "",
        "- The public test folder contains only three example wells; hidden evaluation wells are substituted by Kaggle at submission time.",
        "- `TVT_input` is available before the evaluation interval and missing exactly where `sample_submission.csv` asks for predictions.",
        "- A per-well extrapolation baseline is a strong first sanity check because visible targets continue from the known `TVT_input` segment.",
        "- Stronger models should use cross-well validation rather than trusting the three visible test wells.",
        "",
        f"Data root resolved as: `{data_root.relative_to(ROOT)}`",
    ]
    )

    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
