#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from data_paths import resolve_test_dir, resolve_train_dir


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"
OUTPUT_PATH = OUTPUT_DIR / "part3_diagnostics.csv"
REPORT_PATH = REPORT_DIR / "part3_diagnostics_report.md"


def slope_stats(values: np.ndarray, md: np.ndarray) -> tuple[float, float]:
    if len(values) < 3:
        return float("nan"), float("nan")
    slopes = np.diff(values) / np.diff(md)
    slopes = slopes[np.isfinite(slopes)]
    if len(slopes) == 0:
        return float("nan"), float("nan")
    return float(np.median(slopes)), float(np.std(slopes))


def compute_quality(df: pd.DataFrame) -> dict[str, float]:
    target_mask = df["TVT_input"].isna().to_numpy()
    known_mask = ~target_mask
    known_count = int(known_mask.sum())
    target_count = int(target_mask.sum())
    gr_missing_rate = float(df.loc[target_mask, "GR"].isna().mean()) if target_count else float("nan")

    known_tvt = df.loc[known_mask, "TVT_input"].to_numpy(dtype=float)
    known_md = df.loc[known_mask, "MD"].to_numpy(dtype=float)
    slope_med, slope_std = slope_stats(known_tvt, known_md)

    baseline_confidence = 0.0
    if np.isfinite(slope_std):
        baseline_confidence = float(1.0 / (1.0 + slope_std))
    baseline_confidence *= float(min(known_count / max(target_count, 1), 2.0) / 2.0)
    baseline_confidence *= float(1.0 - min(gr_missing_rate, 1.0) * 0.5 if np.isfinite(gr_missing_rate) else 0.5)

    gr = df["GR"].to_numpy(dtype=float)
    gr_valid = gr[np.isfinite(gr)]
    if len(gr_valid) >= 3:
        gr_std = float(np.std(gr_valid))
        gr_diff = np.diff(gr_valid)
        gr_vol = float(np.std(gr_diff)) if len(gr_diff) else float("nan")
    else:
        gr_std = float("nan")
        gr_vol = float("nan")

    gr_quality = 0.0
    if np.isfinite(gr_std):
        gr_quality += min(gr_std / 80.0, 1.0)
    if np.isfinite(gr_vol):
        gr_quality += min(gr_vol / 25.0, 1.0)
    gr_quality *= 0.5
    gr_quality *= float(1.0 - min(gr_missing_rate, 1.0) if np.isfinite(gr_missing_rate) else 0.5)

    typewell_path = df.attrs.get("typewell_path")
    typewell_has_geology = bool(df.attrs.get("typewell_has_geology", False))
    typewell_rows = int(df.attrs.get("typewell_rows", 0))
    typewell_quality = 0.0
    if typewell_rows:
        typewell_quality = min(typewell_rows / max(len(df), 1), 1.0)
        if typewell_has_geology:
            typewell_quality = min(typewell_quality + 0.25, 1.0)

    risk = 1.0 - max(baseline_confidence, 0.0)
    if target_count > 0 and target_count > known_count:
        risk += 0.1
    if np.isfinite(gr_missing_rate):
        risk += gr_missing_rate * 0.25
    risk = float(min(max(risk, 0.0), 1.0))

    if gr_quality >= 0.12 and (typewell_quality >= 0.48 or typewell_has_geology):
        route = "typewell_alignment"
    elif gr_quality >= 0.10:
        route = "gr_residual"
    elif baseline_confidence >= 0.10:
        route = "geometry_residual"
    else:
        route = "baseline_fallback"

    return {
        "rows": len(df),
        "known_rows": known_count,
        "target_rows": target_count,
        "known_ratio": float(known_count / max(len(df), 1)),
        "target_ratio": float(target_count / max(len(df), 1)),
        "gr_missing_rate": gr_missing_rate,
        "baseline_slope_median": slope_med,
        "baseline_slope_std": slope_std,
        "baseline_confidence": baseline_confidence,
        "gr_std": gr_std,
        "gr_volatility": gr_vol,
        "gr_quality_score": gr_quality,
        "typewell_rows": typewell_rows,
        "typewell_has_geology": float(typewell_has_geology),
        "typewell_quality_score": typewell_quality,
        "risk_score": risk,
        "route_suggestion": route,
    }


def load_horizontal(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df


def load_typewell(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def main() -> int:
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)

    records = []
    for path in sorted(resolve_train_dir().glob("*__horizontal_well.csv")):
        well = path.name.split("__")[0]
        df = load_horizontal(path)
        typewell_path = resolve_train_dir() / f"{well}__typewell.csv"
        if typewell_path.exists():
            typewell = load_typewell(typewell_path)
            df.attrs["typewell_path"] = str(typewell_path)
            df.attrs["typewell_rows"] = len(typewell)
            df.attrs["typewell_has_geology"] = "Geology" in typewell.columns
        else:
            df.attrs["typewell_path"] = ""
            df.attrs["typewell_rows"] = 0
            df.attrs["typewell_has_geology"] = False
        row = {"well": well, "split": "train", **compute_quality(df)}
        records.append(row)

    test_dir = resolve_test_dir()
    for path in sorted(test_dir.glob("*__horizontal_well.csv")):
        well = path.name.split("__")[0]
        df = load_horizontal(path)
        typewell_path = test_dir / f"{well}__typewell.csv"
        if typewell_path.exists():
            typewell = load_typewell(typewell_path)
            df.attrs["typewell_path"] = str(typewell_path)
            df.attrs["typewell_rows"] = len(typewell)
            df.attrs["typewell_has_geology"] = "Geology" in typewell.columns
        else:
            df.attrs["typewell_path"] = ""
            df.attrs["typewell_rows"] = 0
            df.attrs["typewell_has_geology"] = False
        row = {"well": well, "split": "test", **compute_quality(df)}
        records.append(row)

    out = pd.DataFrame(records)
    out.to_csv(OUTPUT_PATH, index=False)

    summary = out.groupby(out["split"].fillna("train")).agg(
        wells=("well", "count"),
        mean_gr_quality=("gr_quality_score", "mean"),
        mean_baseline_conf=("baseline_confidence", "mean"),
        mean_risk=("risk_score", "mean"),
    )
    train_only = out[out["split"].fillna("train") != "test"].copy()
    route_counts = train_only["route_suggestion"].value_counts().to_dict()

    lines = [
        "# Part 3 Diagnostics",
        "",
        "This report turns the Part 3 ideas into a routing table: estimate GR quality, estimate baseline confidence, mark whether typewell geology exists, and suggest which model family should handle the well.",
        "",
        "## Split Summary",
        "",
        summary.round(4).to_markdown(),
        "",
        "## Route Counts on Train Wells",
        "",
        pd.Series(route_counts, name="count").to_frame().to_markdown(),
        "",
        "## Route Rule",
        "",
        "- `typewell_alignment`: GR is decent and typewell is informative enough to justify an alignment pass.",
        "- `gr_residual`: GR is usable but alignment is not strong enough for direct typewell correction.",
        "- `geometry_residual`: GR is weak, so geometry should dominate.",
        "- `baseline_fallback`: the signal quality is too low for aggressive correction.",
        "",
        f"Diagnostics written to `{OUTPUT_PATH.relative_to(ROOT)}`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n")
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Wrote {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
