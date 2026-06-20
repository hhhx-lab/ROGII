#!/usr/bin/env python3
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from rogii_utils import (
    OUTPUT_DIR,
    REPORT_DIR,
    ROOT,
    TRAIN_DIR,
    assert_data_contract_ready,
    data_hash_short,
    ensure_project_dirs,
    run_baseline,
)


DETAIL_PATH = OUTPUT_DIR / "baseline_cv_by_well.csv"
OVERALL_PATH = OUTPUT_DIR / "baseline_overall_metrics.csv"
FAILURE_PATH = OUTPUT_DIR / "failure_case_candidates.csv"
REPORT_PATH = REPORT_DIR / "baseline_failure_analysis.md"
FIGURE_DIR = REPORT_DIR / "figures" / "baseline_worst_wells"
FAILURE_TYPES = ["smooth_bias", "slope_change", "abrupt_shift", "gr_transition", "long_extrapolation", "missing_gr"]


def target_rows(df: pd.DataFrame) -> np.ndarray:
    rows = np.flatnonzero(df["TVT_input"].isna().to_numpy())
    return np.arange(int(rows[0]), int(rows[-1]) + 1, dtype=int)


def classify_failure(row: pd.Series, errors: np.ndarray, truth: np.ndarray, preds: np.ndarray, gr: pd.Series) -> tuple[str, str]:
    tags: list[str] = []
    abs_bias = abs(float(row["bias"]))
    rmse = float(row["rmse"])
    mae = float(row["mae"])

    if abs_bias >= max(10.0, 0.75 * mae):
        tags.append("smooth_bias")

    if len(errors) > 10:
        x = np.arange(len(errors), dtype=float)
        error_slope = float(np.polyfit(x, errors, 1)[0])
        if abs(error_slope) * len(errors) >= max(20.0, 0.75 * rmse):
            tags.append("slope_change")

    true_steps = np.abs(np.diff(truth))
    if len(true_steps) and float(np.quantile(true_steps, 0.99)) >= max(0.5, 5 * np.median(true_steps)):
        tags.append("abrupt_shift")

    if float(row["target_rows"]) >= 6000:
        tags.append("long_extrapolation")

    if float(row["target_gr_missing_rate"]) >= 0.50:
        tags.append("missing_gr")
    else:
        gr_values = gr.to_numpy(dtype=float)
        finite = np.isfinite(gr_values)
        if finite.sum() > 10 and float(np.nanpercentile(np.abs(np.diff(gr_values[finite])), 95)) >= 30:
            tags.append("gr_transition")

    if not tags:
        tags.append("slope_change" if rmse >= 50 else "smooth_bias")

    priority = ["abrupt_shift", "gr_transition", "slope_change", "smooth_bias", "long_extrapolation", "missing_gr"]
    primary = next(label for label in priority if label in tags)
    return primary, ",".join(tags)


def typewell_diagnostics(well: str) -> dict[str, object]:
    path = TRAIN_DIR / f"{well}__typewell.csv"
    if not path.exists():
        return {
            "typewell_rows": 0,
            "typewell_tvt_span": np.nan,
            "typewell_gr_missing_rate": np.nan,
            "typewell_geology_label_count": 0,
            "typewell_geology_labels": "",
        }
    typewell = pd.read_csv(path)
    labels = []
    if "Geology" in typewell:
        labels = sorted(typewell["Geology"].dropna().astype(str).unique().tolist())
    return {
        "typewell_rows": len(typewell),
        "typewell_tvt_span": float(typewell["TVT"].max() - typewell["TVT"].min()) if "TVT" in typewell and len(typewell) else np.nan,
        "typewell_gr_missing_rate": float(typewell["GR"].isna().mean()) if "GR" in typewell and len(typewell) else np.nan,
        "typewell_geology_label_count": len(labels),
        "typewell_geology_labels": "|".join(labels[:30]),
    }


def draw_geology_bands(ax: plt.Axes, typewell: pd.DataFrame) -> None:
    if "Geology" not in typewell or typewell["Geology"].dropna().empty:
        return
    labels = typewell["Geology"].fillna("unknown").astype(str).to_numpy()
    tvt = typewell["TVT"].to_numpy(dtype=float)
    if len(tvt) == 0:
        return
    starts = [0]
    for idx in range(1, len(labels)):
        if labels[idx] != labels[idx - 1]:
            starts.append(idx)
    starts.append(len(labels))
    unique_labels = list(dict.fromkeys(labels.tolist()))
    cmap = plt.get_cmap("tab20")
    color_map = {label: cmap(i % 20) for i, label in enumerate(unique_labels)}
    y_min, y_max = ax.get_ylim()
    for left, right in zip(starts[:-1], starts[1:]):
        label = labels[left]
        ax.axvspan(tvt[left], tvt[right - 1], color=color_map[label], alpha=0.08, linewidth=0)
        if right - left > 50:
            ax.text(
                (tvt[left] + tvt[right - 1]) / 2,
                y_max,
                label,
                ha="center",
                va="top",
                fontsize=6,
                rotation=90,
                alpha=0.65,
            )
    ax.set_ylim(y_min, y_max)


def plot_well(well: str, baseline: str, out_path, row: pd.Series) -> None:
    df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
    typewell_path = TRAIN_DIR / f"{well}__typewell.csv"
    typewell = pd.read_csv(typewell_path) if typewell_path.exists() else pd.DataFrame()

    rows = target_rows(df)
    known_end = int(rows[0] - 1)
    truth = df.loc[rows, "TVT"].to_numpy(dtype=float)
    preds, _ = run_baseline(df, rows, baseline=baseline, known_allowed_start_row=0, known_allowed_end_row=known_end)
    errors = preds - truth

    fig, axes = plt.subplots(4, 1, figsize=(13, 12), constrained_layout=True)
    x_all = np.arange(len(df))
    x_target = rows

    axes[0].plot(x_all, df["TVT"], color="#222222", linewidth=1.0, label="TVT truth")
    axes[0].scatter(x_all[: known_end + 1], df.loc[:known_end, "TVT_input"], s=4, color="#2c7fb8", label="known TVT_input")
    axes[0].plot(x_target, preds, color="#d95f0e", linewidth=1.0, label=f"{baseline} prediction")
    axes[0].axvspan(rows[0], rows[-1], color="#fdd49e", alpha=0.25, label="hidden target")
    axes[0].set_title(
        f"{well} | RMSE={row['rmse']:.2f} | type={row['failure_type']} | target_rows={int(row['target_rows'])}"
    )
    axes[0].set_ylabel("TVT")
    axes[0].legend(loc="best", fontsize=8)

    axes[1].plot(x_target, np.abs(errors), color="#7b3294", linewidth=0.9)
    axes[1].set_ylabel("Abs error")
    axes[1].axvspan(rows[0], rows[-1], color="#fdd49e", alpha=0.25)

    axes[2].plot(x_all, df["GR"], color="#1b9e77", linewidth=0.8, label="horizontal GR")
    axes[2].axvspan(rows[0], rows[-1], color="#fdd49e", alpha=0.25)
    axes[2].set_ylabel("Horizontal GR")
    axes[2].legend(loc="best", fontsize=8)

    if len(typewell) and {"TVT", "GR"}.issubset(typewell.columns):
        axes[3].plot(typewell["TVT"], typewell["GR"], color="#4d4d4d", linewidth=0.8, label="typewell GR")
        draw_geology_bands(axes[3], typewell)
        axes[3].set_xlabel("Typewell TVT")
        axes[3].set_ylabel("Typewell GR")
        axes[3].legend(loc="best", fontsize=8)
    else:
        axes[3].text(0.5, 0.5, "No typewell data", ha="center", va="center")
        axes[3].set_axis_off()

    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def main() -> int:
    ensure_project_dirs()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    data_version = assert_data_contract_ready()
    if not DETAIL_PATH.exists() or not OVERALL_PATH.exists():
        raise FileNotFoundError("baseline CV outputs are missing; run scripts/evaluate_baseline_cv.py first")

    data_hash = data_hash_short(data_version)
    detail = pd.read_csv(DETAIL_PATH)
    overall = pd.read_csv(OVERALL_PATH)
    best_baseline = str(overall.sort_values("row_weighted_rmse").iloc[0]["baseline"])
    selected = detail[detail["baseline"].eq(best_baseline)].copy().sort_values("rmse", ascending=False)

    records = []
    for _, row in selected.iterrows():
        well = str(row["well"])
        df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
        rows = target_rows(df)
        truth = df.loc[rows, "TVT"].to_numpy(dtype=float)
        preds, _ = run_baseline(
            df,
            rows,
            baseline=best_baseline,
            known_allowed_start_row=0,
            known_allowed_end_row=int(rows[0] - 1),
        )
        errors = preds - truth
        failure_type, tags = classify_failure(row, errors, truth, preds, df.loc[rows, "GR"])
        typewell_info = typewell_diagnostics(well)
        records.append(
            {
                "data_hash": data_hash,
                "baseline": best_baseline,
                "well": well,
                "rmse": row["rmse"],
                "mae": row["mae"],
                "bias": row["bias"],
                "max_abs_error": row["max_abs_error"],
                "target_rows": row["target_rows"],
                "target_md_span": row["target_md_span"],
                "target_tvt_span": row["target_tvt_span"],
                "target_gr_missing_rate": row["target_gr_missing_rate"],
                "baseline_slope": row["baseline_slope"],
                **typewell_info,
                "failure_type": failure_type,
                "failure_tags": tags,
            }
        )

    candidates = pd.DataFrame(records).sort_values("rmse", ascending=False)
    candidates.to_csv(FAILURE_PATH, index=False)

    worst_20 = candidates.head(20)
    for rank, (_, row) in enumerate(worst_20.iterrows(), start=1):
        plot_well(str(row["well"]), best_baseline, FIGURE_DIR / f"{rank:02d}_{row['well']}.png", row)

    type_counts = (
        candidates["failure_type"]
        .value_counts()
        .reindex(FAILURE_TYPES, fill_value=0)
        .rename_axis("failure_type")
        .reset_index(name="wells")
    )
    tag_counts = (
        candidates["failure_tags"]
        .str.get_dummies(sep=",")
        .sum()
        .reindex(FAILURE_TYPES, fill_value=0)
        .sort_values(ascending=False)
        .rename_axis("failure_tag")
        .reset_index(name="wells")
    )

    lines = [
        "# Baseline Failure Analysis",
        "",
        f"- Data hash: `{data_hash}`",
        f"- Baseline analyzed: `{best_baseline}`",
        f"- Candidate wells: {len(candidates)}",
        f"- Diagnostic figures: `{FIGURE_DIR.relative_to(ROOT)}`",
        "",
        "## Primary Failure Types",
        "",
        type_counts.to_markdown(index=False),
        "",
        "## Failure Tags",
        "",
        tag_counts.to_markdown(index=False),
        "",
        "## Worst 20 Wells",
        "",
        worst_20.round(4).to_markdown(index=False),
        "",
        "## Engineering Interpretation",
        "",
        "- `smooth_bias` indicates a mostly coherent offset and is the cleanest first target for residual modeling.",
        "- `slope_change` and `abrupt_shift` indicate that pure continuation is too weak and geometry/typewell alignment should be prioritized.",
        "- `gr_transition` marks wells where GR morphology can plausibly locate stratigraphic movement.",
        "- `long_extrapolation` and `missing_gr` should route to conservative fallback and uncertainty controls.",
        "- `typewell_*` columns in `failure_case_candidates.csv` are structured checks that the plotted typewell GR and Geology bands exist and can be joined in Part 3.",
        "",
        f"Detailed candidates: `{FAILURE_PATH.relative_to(ROOT)}`",
        "",
    ]
    REPORT_PATH.write_text("\n".join(lines))

    print(f"Wrote {FAILURE_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {len(worst_20)} figures under {FIGURE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
