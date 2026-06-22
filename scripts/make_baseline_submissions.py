#!/usr/bin/env python3
from __future__ import annotations

import pandas as pd

from data_paths import load_sample_submission
from rogii_utils import (
    BASELINE_CONFIGS,
    REPORT_DIR,
    ROOT,
    SUBMISSION_DIR,
    TEST_DIR,
    TRAIN_DIR,
    assert_data_contract_ready,
    data_hash_short,
    ensure_project_dirs,
    parse_submission_ids,
    regression_metrics,
    run_baseline,
)


REPORT_PATH = REPORT_DIR / "baseline_submission_report.md"
LEGACY_TAIL_SLOPE_PATH = SUBMISSION_DIR / "baseline_tail_slope_submission.csv"


def submission_path_for(baseline: str):
    return SUBMISSION_DIR / f"{baseline.lower()}_submission.csv"


def main() -> int:
    ensure_project_dirs()
    data_version = assert_data_contract_ready()
    data_hash = data_hash_short(data_version)

    sample = load_sample_submission()
    parsed = parse_submission_ids(sample)
    diagnostics = []

    for config in BASELINE_CONFIGS:
        baseline = str(config["baseline"])
        out = sample.copy()
        local_truth = []
        local_pred = []

        for well, part in parsed.groupby("well", sort=True):
            test = pd.read_csv(TEST_DIR / f"{well}__horizontal_well.csv")
            target_rows = part["row"].to_numpy(dtype=int)
            known_allowed_end_row = int(target_rows.min() - 1)
            preds, baseline_diag = run_baseline(
                test,
                target_rows,
                baseline=baseline,
                known_allowed_start_row=0,
                known_allowed_end_row=known_allowed_end_row,
            )
            out.loc[part.index, "tvt"] = preds

            train_path = TRAIN_DIR / f"{well}__horizontal_well.csv"
            visible_rmse = None
            if train_path.exists():
                truth = pd.read_csv(train_path).loc[target_rows, "TVT"].to_numpy(dtype=float)
                local_truth.extend(truth.tolist())
                local_pred.extend(preds.tolist())
                visible_rmse = regression_metrics(truth, preds)["rmse"]

            diagnostics.append(
                {
                    "data_hash": data_hash,
                    "baseline": baseline,
                    "well": well,
                    "predicted_rows": len(target_rows),
                    "known_allowed_end_row": known_allowed_end_row,
                    "pred_min": float(preds.min()),
                    "pred_max": float(preds.max()),
                    "baseline_slope": baseline_diag.get("baseline_slope"),
                    "visible_train_rmse": visible_rmse,
                }
            )

        path = submission_path_for(baseline)
        out.to_csv(path, index=False)
        if baseline == "B2_tail_slope_k200":
            out.to_csv(LEGACY_TAIL_SLOPE_PATH, index=False)

        if local_truth:
            metrics = regression_metrics(local_truth, local_pred)
            diagnostics.append(
                {
                    "data_hash": data_hash,
                    "baseline": baseline,
                    "well": "__visible_aggregate__",
                    "predicted_rows": len(local_truth),
                    "known_allowed_end_row": None,
                    "pred_min": float(out["tvt"].min()),
                    "pred_max": float(out["tvt"].max()),
                    "baseline_slope": None,
                    "visible_train_rmse": metrics["rmse"],
                }
            )

    diag = pd.DataFrame(diagnostics)
    aggregate = diag[diag["well"].eq("__visible_aggregate__")].sort_values("visible_train_rmse")
    per_well = diag[~diag["well"].eq("__visible_aggregate__")]

    lines = [
        "# Baseline Submission Report",
        "",
        f"- Data hash: `{data_hash}`",
        f"- Submission rows: {len(sample):,}",
        f"- Baselines generated: {len(BASELINE_CONFIGS)}",
        "",
        "## Visible Example Aggregate RMSE",
        "",
        "These visible examples overlap training wells and are format/runtime sanity checks only; do not tune modeling decisions from these three wells.",
        "",
        aggregate.round(4).to_markdown(index=False),
        "",
        "## Per-Well Diagnostics",
        "",
        per_well.round(4).to_markdown(index=False),
        "",
        "## Output Files",
        "",
    ]
    for config in BASELINE_CONFIGS:
        baseline = str(config["baseline"])
        lines.append(f"- `{submission_path_for(baseline).relative_to(ROOT)}`")
    lines.extend(
        [
            f"- `{LEGACY_TAIL_SLOPE_PATH.relative_to(ROOT)}` kept for compatibility with earlier workflow",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines))

    print(f"Wrote {REPORT_PATH}")
    for config in BASELINE_CONFIGS:
        print(f"Wrote {submission_path_for(str(config['baseline']))}")
    print(f"Wrote {LEGACY_TAIL_SLOPE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
