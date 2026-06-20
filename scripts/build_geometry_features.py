#!/usr/bin/env python3
from __future__ import annotations

import numpy as np
import pandas as pd

from part2_utils import FEATURE_DIR, add_key_columns, ensure_part2_dirs, slope_stats, target_rows_from_tvt_input
from rogii_utils import DATA_DIR, TEST_DIR, TRAIN_DIR, assert_data_contract_ready, parse_submission_ids, train_wells


GEOMETRY_TRAIN_PATH = FEATURE_DIR / "geometry_features_train.parquet"
GEOMETRY_TEST_PATH = FEATURE_DIR / "geometry_features_test.parquet"
ROLLING_WINDOWS = [25, 50, 100, 200, 500]


def safe_divide(num: np.ndarray, den: np.ndarray) -> np.ndarray:
    return np.divide(num, den, out=np.zeros_like(num, dtype=float), where=den != 0)


def full_well_geometry(df: pd.DataFrame) -> pd.DataFrame:
    md = df["MD"].to_numpy(dtype=float)
    x = df["X"].to_numpy(dtype=float)
    y = df["Y"].to_numpy(dtype=float)
    z = df["Z"].to_numpy(dtype=float)

    d_md = np.r_[0.0, np.diff(md)]
    d_x = np.r_[0.0, np.diff(x)]
    d_y = np.r_[0.0, np.diff(y)]
    d_z = np.r_[0.0, np.diff(z)]
    d_xy = np.sqrt(d_x**2 + d_y**2)
    dz_dmd = safe_divide(d_z, d_md)
    dxy_dmd = safe_divide(d_xy, d_md)
    ddz_dmd = np.r_[0.0, np.diff(dz_dmd)]
    curvature = np.sqrt(ddz_dmd**2 + np.r_[0.0, np.diff(dxy_dmd)] ** 2)

    out = pd.DataFrame(
        {
            "MD": md,
            "X": x,
            "Y": y,
            "Z": z,
            "row_index": np.arange(len(df), dtype=np.int32),
            "row_position": np.arange(len(df), dtype=float) / max(1, len(df) - 1),
            "MD_normalized_within_well": (md - md.min()) / max(1e-6, md.max() - md.min()),
            "Z_normalized_within_well": (z - z.min()) / max(1e-6, z.max() - z.min()),
            "dX": d_x,
            "dY": d_y,
            "dZ": d_z,
            "dMD": d_md,
            "dZ_dMD": dz_dmd,
            "dXY_dMD": dxy_dmd,
            "ddZ_dMD": ddz_dmd,
            "trajectory_curvature_proxy": curvature,
            "inclination_change_proxy": np.abs(ddz_dmd),
        }
    )

    z_series = pd.Series(z)
    dz_series = pd.Series(dz_dmd)
    curv_series = pd.Series(curvature)
    for window in ROLLING_WINDOWS:
        min_periods = max(2, window // 5)
        out[f"rolling_Z_mean_{window}"] = z_series.rolling(window, min_periods=min_periods).mean()
        out[f"rolling_Z_std_{window}"] = z_series.rolling(window, min_periods=min_periods).std()
        out[f"rolling_dZ_dMD_mean_{window}"] = dz_series.rolling(window, min_periods=min_periods).mean()
        out[f"rolling_dZ_dMD_std_{window}"] = dz_series.rolling(window, min_periods=min_periods).std()
        out[f"rolling_curvature_mean_{window}"] = curv_series.rolling(window, min_periods=min_periods).mean()

    fill_values = {
        col: 0.0
        for col in out.columns
        if col.startswith("rolling_") or col in {"dZ_dMD", "dXY_dMD", "ddZ_dMD", "trajectory_curvature_proxy"}
    }
    out = out.fillna(fill_values)
    return out.astype({col: "float32" for col in out.select_dtypes(include=["float64"]).columns})


def well_level_features(df: pd.DataFrame, target_rows: np.ndarray) -> dict[str, float]:
    known_end = int(target_rows[0] - 1)
    known = df.loc[:known_end]
    known_md = known["MD"].to_numpy(dtype=float)
    known_tvt = known["TVT_input"].to_numpy(dtype=float)
    stats = slope_stats(known_md, known_tvt)
    md = df["MD"].to_numpy(dtype=float)
    z = df["Z"].to_numpy(dtype=float)
    return {
        "well_total_rows": float(len(df)),
        "well_MD_span": float(md.max() - md.min()),
        "well_Z_span": float(z.max() - z.min()),
        "well_known_TVT_span": float(np.nanmax(known_tvt) - np.nanmin(known_tvt)) if len(known_tvt) else 0.0,
        "well_known_slope_mean": float(stats["mean"]),
        "well_known_slope_std": float(stats["std"]),
        "well_GR_missing_rate": float(df["GR"].isna().mean()) if "GR" in df else 1.0,
        "well_target_length": float(len(target_rows)),
    }


def build_for_well(df: pd.DataFrame, well: str, target_rows: np.ndarray) -> pd.DataFrame:
    full = full_well_geometry(df)
    target = full.iloc[target_rows].reset_index(drop=True)
    for col, value in well_level_features(df, target_rows).items():
        target[col] = np.float32(value)
    return add_key_columns(target, well, target_rows)


def main() -> int:
    ensure_part2_dirs()
    assert_data_contract_ready()

    train_parts = []
    for well in train_wells():
        df = pd.read_csv(TRAIN_DIR / f"{well}__horizontal_well.csv")
        train_parts.append(build_for_well(df, well, target_rows_from_tvt_input(df)))
    train_features = pd.concat(train_parts, ignore_index=True)
    train_features.to_parquet(GEOMETRY_TRAIN_PATH, index=False)

    sample = pd.read_csv(DATA_DIR / "sample_submission.csv")
    parsed = parse_submission_ids(sample)
    test_parts = []
    for well, part in parsed.groupby("well", sort=True):
        df = pd.read_csv(TEST_DIR / f"{well}__horizontal_well.csv")
        test_parts.append(build_for_well(df, well, part["row"].to_numpy(dtype=int)))
    test_features = pd.concat(test_parts, ignore_index=True)
    test_features.to_parquet(GEOMETRY_TEST_PATH, index=False)

    print(f"Wrote {GEOMETRY_TRAIN_PATH}")
    print(f"Wrote {GEOMETRY_TEST_PATH}")
    print(f"train_rows={len(train_features)} test_rows={len(test_features)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
