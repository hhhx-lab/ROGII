#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from data_paths import resolve_test_dir, resolve_train_dir


ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "features"

WINDOWS = (25, 50, 100, 200, 500)


def safe_div(numerator: np.ndarray, denominator: np.ndarray, fill: float = 0.0) -> np.ndarray:
    numerator = np.asarray(numerator, dtype=float)
    denominator = np.asarray(denominator, dtype=float)
    out = np.full_like(numerator, fill, dtype=float)
    mask = np.isfinite(numerator) & np.isfinite(denominator) & (np.abs(denominator) > 1e-12)
    out[mask] = numerator[mask] / denominator[mask]
    return out


def zscore(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    mean = np.nanmean(values) if np.isfinite(values).any() else 0.0
    std = np.nanstd(values) if np.isfinite(values).any() else 0.0
    if not np.isfinite(std) or std == 0.0:
        return np.zeros_like(values, dtype=float)
    return (values - mean) / std


def add_rolling_features(frame: pd.DataFrame, base: pd.Series, prefix: str) -> None:
    for window in WINDOWS:
        roll = base.rolling(window=window, min_periods=1)
        frame[f"{prefix}_roll_mean_{window}"] = roll.mean().to_numpy(dtype=float)
        frame[f"{prefix}_roll_std_{window}"] = roll.std(ddof=0).fillna(0.0).to_numpy(dtype=float)
        frame[f"{prefix}_roll_min_{window}"] = roll.min().to_numpy(dtype=float)
        frame[f"{prefix}_roll_max_{window}"] = roll.max().to_numpy(dtype=float)


def build_frame(df: pd.DataFrame, well: str, split: str) -> pd.DataFrame:
    md = df["MD"].to_numpy(dtype=float)
    x = df["X"].to_numpy(dtype=float)
    y = df["Y"].to_numpy(dtype=float)
    z = df["Z"].to_numpy(dtype=float)
    rows = np.arange(len(df))
    target_rows = np.flatnonzero(df["TVT_input"].isna().to_numpy())

    dmd = np.diff(md, prepend=md[0] if len(md) else 0.0)
    dx = np.diff(x, prepend=x[0] if len(x) else 0.0)
    dy = np.diff(y, prepend=y[0] if len(y) else 0.0)
    dz = np.diff(z, prepend=z[0] if len(z) else 0.0)

    dX_dMD = safe_div(dx, dmd)
    dY_dMD = safe_div(dy, dmd)
    dZ_dMD = safe_div(dz, dmd)
    dXY_dMD = np.sqrt(dX_dMD**2 + dY_dMD**2)
    dXYZ_norm = np.sqrt(dx**2 + dy**2 + dz**2)

    if len(md) >= 2:
        ddX_dMD = np.gradient(dX_dMD, md, edge_order=1)
        ddY_dMD = np.gradient(dY_dMD, md, edge_order=1)
        ddZ_dMD = np.gradient(dZ_dMD, md, edge_order=1)
    else:
        ddX_dMD = np.zeros_like(md)
        ddY_dMD = np.zeros_like(md)
        ddZ_dMD = np.zeros_like(md)

    trajectory_speed_proxy = safe_div(dXYZ_norm, np.maximum(np.abs(dmd), 1e-6))
    trajectory_curvature_proxy = np.sqrt(ddX_dMD**2 + ddY_dMD**2 + ddZ_dMD**2)
    inclination_change_proxy = np.abs(ddZ_dMD)
    path_length = np.cumsum(np.r_[0.0, dXYZ_norm[1:]]) if len(dXYZ_norm) else np.array([], dtype=float)

    total_rows = len(df)
    md_span = float(np.nanmax(md) - np.nanmin(md)) if total_rows else float("nan")
    x_span = float(np.nanmax(x) - np.nanmin(x)) if total_rows else float("nan")
    y_span = float(np.nanmax(y) - np.nanmin(y)) if total_rows else float("nan")
    z_span = float(np.nanmax(z) - np.nanmin(z)) if total_rows else float("nan")
    known_mask = ~df["TVT_input"].isna().to_numpy()
    known_rows = int(known_mask.sum())
    target_count = int(len(target_rows))

    frame = pd.DataFrame(
        {
            "well": well,
            "split": split,
            "row": rows,
            "id": [f"{well}_{int(row)}" for row in rows],
            "row_position": rows / max(total_rows - 1, 1),
            "MD": md,
            "X": x,
            "Y": y,
            "Z": z,
            "MD_norm": (md - np.nanmin(md)) / max(md_span, 1e-6),
            "X_centered": x - np.nanmean(x),
            "Y_centered": y - np.nanmean(y),
            "Z_centered": z - np.nanmean(z),
            "X_zscore": zscore(x),
            "Y_zscore": zscore(y),
            "Z_zscore": zscore(z),
            "MD_centered": md - np.nanmean(md),
            "dMD": dmd,
            "dX": dx,
            "dY": dy,
            "dZ": dz,
            "dX_dMD": dX_dMD,
            "dY_dMD": dY_dMD,
            "dZ_dMD": dZ_dMD,
            "dXY_dMD": dXY_dMD,
            "dXYZ_norm": dXYZ_norm,
            "ddX_dMD": ddX_dMD,
            "ddY_dMD": ddY_dMD,
            "ddZ_dMD": ddZ_dMD,
            "trajectory_speed_proxy": trajectory_speed_proxy,
            "trajectory_curvature_proxy": trajectory_curvature_proxy,
            "inclination_change_proxy": inclination_change_proxy,
            "path_length_cum": path_length,
            "path_length_norm": path_length / max(float(path_length[-1]) if len(path_length) else 1.0, 1e-6),
            "well_total_rows": total_rows,
            "well_MD_span": md_span,
            "well_X_span": x_span,
            "well_Y_span": y_span,
            "well_Z_span": z_span,
            "well_known_rows": known_rows,
            "well_target_rows": target_count,
            "well_known_ratio": float(known_rows / max(total_rows, 1)),
            "well_target_ratio": float(target_count / max(total_rows, 1)),
            "well_gr_missing_rate": float(df["GR"].isna().mean()),
        }
    )

    add_rolling_features(frame, pd.Series(z), "Z")
    add_rolling_features(frame, pd.Series(dZ_dMD), "dZ_dMD")
    add_rolling_features(frame, pd.Series(trajectory_curvature_proxy), "curvature")
    add_rolling_features(frame, pd.Series(trajectory_speed_proxy), "speed")

    target_columns = [c for c in frame.columns if c not in {"row", "id", "well", "split"}]
    return frame.loc[target_rows, ["well", "split", "row", "id", *target_columns]].copy()


def append_csv(frame: pd.DataFrame, path: Path) -> None:
    header = not path.exists()
    frame.to_csv(path, mode="a", header=header, index=False)


def reset_outputs() -> None:
    FEATURE_DIR.mkdir(exist_ok=True)
    for name in [
        "geometry_features_train.csv",
        "geometry_features_test.csv",
    ]:
        path = FEATURE_DIR / name
        if path.exists():
            path.unlink()


def build_split(split: str, data_dir: Path, limit_wells: int | None) -> None:
    for idx, path in enumerate(sorted(data_dir.glob("*__horizontal_well.csv"))):
        if limit_wells is not None and idx >= limit_wells:
            break
        well = path.name.split("__")[0]
        df = pd.read_csv(path)
        frame = build_frame(df, well, split)
        append_csv(frame, FEATURE_DIR / f"geometry_features_{split}.csv")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build geometry feature tables.")
    parser.add_argument("--limit-wells", type=int, default=None, help="Limit the number of wells per split for smoke tests.")
    args = parser.parse_args()

    reset_outputs()
    build_split("train", resolve_train_dir(), args.limit_wells)
    build_split("test", resolve_test_dir(), args.limit_wells)
    print(f"Wrote geometry features to {FEATURE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
