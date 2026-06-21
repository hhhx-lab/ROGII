#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from baseline_tail_slope import tail_slope_prediction
from build_part3_diagnostics import compute_quality
from data_paths import resolve_test_dir, resolve_train_dir


ROOT = Path(__file__).resolve().parents[1]
FEATURE_DIR = ROOT / "features"


ROLL_WINDOWS = (25, 50, 100, 200)
TYPEWELL_WINDOWS = (25.0, 50.0)
ALIGNMENT_OFFSETS = np.array([-200.0, -100.0, -50.0, -25.0, 0.0, 25.0, 50.0, 100.0, 200.0])
ALIGNMENT_WINDOW_ROWS = 128


def median_or_zero(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return 0.0
    return float(np.median(finite))


def fill_with_interpolation(values: np.ndarray) -> np.ndarray:
    series = pd.Series(values, dtype=float)
    if series.notna().sum() == 0:
        return np.zeros(len(series), dtype=float)
    fallback = median_or_zero(series.to_numpy(dtype=float))
    return series.interpolate(limit_direction="both").bfill().ffill().fillna(fallback).to_numpy(dtype=float)


def safe_nanmean(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan")
    return float(np.mean(finite))


def safe_nanstd(values: np.ndarray) -> float:
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return float("nan")
    return float(np.std(finite))


def safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return 0.0
    x = x[mask]
    y = y[mask]
    x = x - np.mean(x)
    y = y - np.mean(y)
    denom = float(np.linalg.norm(x) * np.linalg.norm(y))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(x, y) / denom)


def compute_gr_feature_frame(df: pd.DataFrame, target_rows: np.ndarray, baseline_pred: np.ndarray, quality: dict[str, float], well: str, split: str) -> pd.DataFrame:
    gr = df["GR"].to_numpy(dtype=float)
    md = df["MD"].to_numpy(dtype=float)
    x = df["X"].to_numpy(dtype=float)
    y = df["Y"].to_numpy(dtype=float)
    z = df["Z"].to_numpy(dtype=float)

    gr_missing = pd.isna(gr)
    gr_fill = fill_with_interpolation(gr)
    gr_global_median = median_or_zero(gr)
    known_mask = ~df["TVT_input"].isna().to_numpy()
    last_known_row = int(np.flatnonzero(known_mask)[-1]) if known_mask.any() else 0
    last_known_md = float(md[last_known_row]) if known_mask.any() else float(md[0])

    frame = pd.DataFrame(
        {
            "well": well,
            "split": split,
            "row": target_rows,
            "id": [f"{well}_{int(row)}" for row in target_rows],
            "MD": md[target_rows],
            "X": x[target_rows],
            "Y": y[target_rows],
            "Z": z[target_rows],
            "row_position": target_rows / max(len(df) - 1, 1),
            "known_rows": quality["known_rows"],
            "target_rows": quality["target_rows"],
            "known_ratio": quality["known_ratio"],
            "target_ratio": quality["target_ratio"],
            "last_known_row": last_known_row,
            "last_known_MD": last_known_md,
            "baseline_tvt": baseline_pred,
            "baseline_slope_median": quality["baseline_slope_median"],
            "baseline_slope_std": quality["baseline_slope_std"],
            "baseline_confidence": quality["baseline_confidence"],
            "gr_missing_rate": quality["gr_missing_rate"],
            "gr_quality_score": quality["gr_quality_score"],
            "typewell_rows": quality["typewell_rows"],
            "typewell_quality_score": quality["typewell_quality_score"],
            "risk_score": quality["risk_score"],
            "route_suggestion": quality["route_suggestion"],
            "GR": gr[target_rows],
            "GR_is_missing": gr_missing[target_rows].astype(int),
            "GR_filled_interpolate": gr_fill[target_rows],
            "GR_global_median_fill": np.where(np.isfinite(gr), gr, gr_global_median)[target_rows],
            "GR_filled_ffill": pd.Series(gr).ffill().bfill().fillna(gr_global_median).to_numpy(dtype=float)[target_rows],
            "GR_filled_bfill": pd.Series(gr).bfill().ffill().fillna(gr_global_median).to_numpy(dtype=float)[target_rows],
        }
    )

    frame["distance_from_last_known_row"] = frame["row"] - frame["last_known_row"]
    frame["distance_from_last_known_md"] = frame["MD"] - frame["last_known_MD"]
    frame["distance_from_first_hidden_row"] = frame["row"] - int(target_rows.min())

    filled = frame["GR_filled_interpolate"].to_numpy(dtype=float)
    if len(filled) >= 2:
        frame["GR_gradient"] = np.gradient(filled, frame["MD"].to_numpy(dtype=float), edge_order=1)
        frame["GR_second_diff"] = np.gradient(frame["GR_gradient"].to_numpy(dtype=float), frame["MD"].to_numpy(dtype=float), edge_order=1)
    else:
        frame["GR_gradient"] = 0.0
        frame["GR_second_diff"] = 0.0
    frame["GR_abs_gradient"] = np.abs(frame["GR_gradient"])
    frame["GR_trend_sign"] = np.sign(frame["GR_gradient"]).astype(float)

    for window in ROLL_WINDOWS:
        roll = pd.Series(gr_fill).rolling(window=window, min_periods=1)
        frame[f"GR_roll_mean_{window}"] = roll.mean().to_numpy(dtype=float)[target_rows]
        frame[f"GR_roll_std_{window}"] = roll.std(ddof=0).fillna(0.0).to_numpy(dtype=float)[target_rows]
        frame[f"GR_roll_min_{window}"] = roll.min().to_numpy(dtype=float)[target_rows]
        frame[f"GR_roll_max_{window}"] = roll.max().to_numpy(dtype=float)[target_rows]
        frame[f"GR_roll_median_{window}"] = roll.median().to_numpy(dtype=float)[target_rows]
        frame[f"GR_roll_range_{window}"] = frame[f"GR_roll_max_{window}"] - frame[f"GR_roll_min_{window}"]
        valid = (~gr_missing).astype(float)
        frame[f"GR_roll_valid_count_{window}"] = pd.Series(valid).rolling(window=window, min_periods=1).sum().to_numpy(dtype=float)[target_rows]
        frame[f"GR_roll_missing_rate_{window}"] = 1.0 - frame[f"GR_roll_valid_count_{window}"] / np.minimum(window, np.arange(len(df)) + 1)[target_rows]

    base_roll = frame["GR_roll_mean_25"].to_numpy(dtype=float)
    base_roll_std = frame["GR_roll_std_25"].replace(0.0, np.nan).to_numpy(dtype=float)
    frame["GR_local_zscore_25"] = (filled - base_roll) / base_roll_std
    frame["GR_peak_proxy_25"] = filled - frame["GR_roll_min_25"].to_numpy(dtype=float)
    frame["GR_trough_proxy_25"] = frame["GR_roll_max_25"].to_numpy(dtype=float) - filled
    grad_vol = pd.Series(np.gradient(gr_fill, md, edge_order=1) if len(gr_fill) >= 2 else np.zeros(len(gr_fill), dtype=float))
    frame["GR_volatility_25"] = grad_vol.rolling(window=25, min_periods=1).std(ddof=0).fillna(0.0).to_numpy(dtype=float)[target_rows]

    return frame


def typewell_window_stats(tvt: np.ndarray, gr: np.ndarray, centers: np.ndarray, window: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    valid = np.isfinite(gr)
    filled = np.where(valid, gr, 0.0)
    csum = np.concatenate(([0.0], np.cumsum(filled)))
    csum2 = np.concatenate(([0.0], np.cumsum(filled * filled)))
    ccount = np.concatenate(([0], np.cumsum(valid.astype(np.int64))))

    left = np.searchsorted(tvt, centers - window, side="left")
    right = np.searchsorted(tvt, centers + window, side="right")
    span = np.maximum(right - left, 1)
    count = ccount[right] - ccount[left]
    sums = csum[right] - csum[left]
    sums2 = csum2[right] - csum2[left]

    mean = np.divide(sums, count, out=np.full(centers.shape, np.nan, dtype=float), where=count > 0)
    ex2 = np.divide(sums2, count, out=np.full(centers.shape, np.nan, dtype=float), where=count > 0)
    std = np.sqrt(np.clip(ex2 - mean * mean, 0.0, None))
    missing_rate = 1.0 - count / span
    return mean, std, count.astype(float), missing_rate.astype(float)


def build_typewell_features(typewell: pd.DataFrame, target_rows: np.ndarray, baseline_pred: np.ndarray, well: str, split: str, quality: dict[str, float]) -> pd.DataFrame:
    typewell = typewell.sort_values("TVT").reset_index(drop=True)
    tw_tvt = typewell["TVT"].to_numpy(dtype=float)
    tw_gr = typewell["GR"].to_numpy(dtype=float)
    tw_gr_valid = tw_gr[np.isfinite(tw_gr)]
    tw_gr_fill = fill_with_interpolation(tw_gr)
    if len(tw_tvt) >= 2:
        tw_grad = np.gradient(tw_gr_fill, tw_tvt, edge_order=1)
    else:
        tw_grad = np.zeros_like(tw_tvt)

    candidate_tvt = baseline_pred.astype(float)
    interp_gr = np.interp(candidate_tvt, tw_tvt, tw_gr_fill, left=np.nan, right=np.nan)
    interp_grad = np.interp(candidate_tvt, tw_tvt, tw_grad, left=np.nan, right=np.nan)
    nearest_idx = np.searchsorted(tw_tvt, candidate_tvt, side="left")
    left_idx = np.clip(nearest_idx - 1, 0, len(tw_tvt) - 1)
    right_idx = np.clip(nearest_idx, 0, len(tw_tvt) - 1)
    nearest_dist = np.minimum(np.abs(candidate_tvt - tw_tvt[left_idx]), np.abs(candidate_tvt - tw_tvt[right_idx]))

    features = pd.DataFrame(
        {
            "well": well,
            "split": split,
            "row": target_rows,
            "id": [f"{well}_{int(row)}" for row in target_rows],
            "baseline_tvt": candidate_tvt,
            "typewell_tvt_min": float(np.nanmin(tw_tvt)),
            "typewell_tvt_max": float(np.nanmax(tw_tvt)),
            "typewell_gr_mean": float(np.nanmean(tw_gr_valid)) if len(tw_gr_valid) else float("nan"),
            "typewell_gr_std": float(np.nanstd(tw_gr_valid)) if len(tw_gr_valid) else float("nan"),
            "typewell_gr_missing_rate": float(np.isnan(tw_gr).mean()),
            "typewell_gr_at_baseline": interp_gr,
            "typewell_interp_gradient": interp_grad,
            "typewell_out_of_range": ((candidate_tvt < tw_tvt[0]) | (candidate_tvt > tw_tvt[-1])).astype(int),
            "typewell_boundary_margin": np.minimum(candidate_tvt - tw_tvt[0], tw_tvt[-1] - candidate_tvt),
            "typewell_nearest_tvt_distance": nearest_dist,
            "typewell_rows": len(typewell),
            "typewell_quality_score": quality["typewell_quality_score"],
            "gr_quality_score": quality["gr_quality_score"],
            "baseline_confidence": quality["baseline_confidence"],
            "route_suggestion": quality["route_suggestion"],
        }
    )

    for window in TYPEWELL_WINDOWS:
        mean, std, count, miss = typewell_window_stats(tw_tvt, tw_gr, candidate_tvt, window)
        suffix = int(window)
        features[f"typewell_gr_window_mean_{suffix}"] = mean
        features[f"typewell_gr_window_std_{suffix}"] = std
        features[f"typewell_gr_window_count_{suffix}"] = count
        features[f"typewell_gr_window_missing_rate_{suffix}"] = miss

    return features


def alignment_similarity(horizontal_gr: np.ndarray, typewell_tvt: np.ndarray, typewell_gr: np.ndarray, candidate_tvt: np.ndarray, offsets: np.ndarray) -> tuple[float, float, float, float, float, float, float, float]:
    best_score = -np.inf
    second_score = -np.inf
    best_offset = float("nan")
    best_corr = float("nan")
    best_mae_norm = float("nan")
    best_support = 0.0

    horizontal_gr = horizontal_gr.astype(float)
    valid_h = np.isfinite(horizontal_gr)
    if valid_h.sum() < 5:
        return best_offset, best_score, second_score, 0.0, 0.0, 0.0, 0.0, 0.0

    for offset in offsets:
        tw_interp = np.interp(candidate_tvt + offset, typewell_tvt, typewell_gr, left=np.nan, right=np.nan)
        mask = np.isfinite(tw_interp) & valid_h
        support = float(mask.mean())
        if mask.sum() < max(20, len(horizontal_gr) // 20):
            score = -np.inf
            corr = 0.0
            mae_norm = np.inf
        else:
            hh = horizontal_gr[mask]
            tt = tw_interp[mask]
            hh_std = float(np.std(hh)) or 1.0
            tt_std = float(np.std(tt)) or 1.0
            corr = safe_corr(hh, tt)
            mae_norm = float(np.mean(np.abs(hh - tt)) / (hh_std + 1e-6))
            score = corr - 0.35 * mae_norm + 0.2 * support
        if score > best_score:
            second_score = best_score
            best_score = score
            best_offset = float(offset)
            best_corr = corr
            best_mae_norm = mae_norm
            best_support = support
        elif score > second_score:
            second_score = score

    confidence = max(0.0, best_score) * max(0.0, best_score - second_score if np.isfinite(second_score) else best_score)
    enabled = float(confidence > 0.05 and best_support >= 0.2)
    return best_offset, best_score, second_score, confidence, enabled, best_support, best_corr, best_mae_norm


def build_alignment_features(horizontal: pd.DataFrame, typewell: pd.DataFrame, target_rows: np.ndarray, well: str, split: str, quality: dict[str, float], baseline_pred: np.ndarray) -> pd.DataFrame:
    typewell = typewell.sort_values("TVT").reset_index(drop=True)
    tw_tvt = typewell["TVT"].to_numpy(dtype=float)
    tw_gr = typewell["GR"].to_numpy(dtype=float)
    tw_gr_fill = fill_with_interpolation(tw_gr)
    h_gr = horizontal["GR"].to_numpy(dtype=float)[target_rows]

    records = []
    for window_index, start in enumerate(range(0, len(target_rows), ALIGNMENT_WINDOW_ROWS)):
        end = min(start + ALIGNMENT_WINDOW_ROWS, len(target_rows))
        window_rows = target_rows[start:end]
        window_baseline = baseline_pred[start:end]
        window_h_gr = h_gr[start:end]

        best_offset, best_score, second_score, confidence, enabled, support, corr, mae_norm = alignment_similarity(
            window_h_gr,
            tw_tvt,
            tw_gr_fill,
            window_baseline,
            ALIGNMENT_OFFSETS,
        )

        route = quality["route_suggestion"]
        if confidence > 0.04 and quality["gr_quality_score"] >= 0.12 and quality["typewell_quality_score"] >= 0.48:
            route = "typewell_alignment"
        elif quality["gr_quality_score"] >= 0.10:
            route = "gr_residual"
        elif quality["baseline_confidence"] >= 0.10:
            route = "geometry_residual"
        else:
            route = "baseline_fallback"

        for row, candidate_tvt, gr_value in zip(window_rows, window_baseline, window_h_gr):
            records.append(
                {
                    "well": well,
                    "split": split,
                    "row": int(row),
                    "id": f"{well}_{int(row)}",
                    "baseline_tvt": float(candidate_tvt),
                    "alignment_window_index": window_index,
                    "alignment_window_start_row": int(window_rows[0]),
                    "alignment_window_end_row": int(window_rows[-1]),
                    "alignment_window_size": len(window_rows),
                    "alignment_window_gr_mean": safe_nanmean(window_h_gr),
                    "alignment_window_gr_std": safe_nanstd(window_h_gr),
                    "alignment_window_gr_missing_rate": float(np.isnan(window_h_gr).mean()) if len(window_h_gr) else float("nan"),
                    "alignment_window_baseline_start": float(window_baseline[0]),
                    "alignment_window_baseline_end": float(window_baseline[-1]),
                    "best_offset": best_offset,
                    "best_similarity": best_score,
                    "second_best_similarity": second_score,
                    "similarity_margin": best_score - second_score if np.isfinite(second_score) else np.nan,
                    "alignment_confidence": confidence,
                    "alignment_enabled_flag": enabled,
                    "alignment_support_fraction": support,
                    "alignment_corr": corr,
                    "alignment_mae_norm": mae_norm,
                    "route_suggestion": route,
                    "gr_quality_score": quality["gr_quality_score"],
                    "baseline_confidence": quality["baseline_confidence"],
                    "typewell_quality_score": quality["typewell_quality_score"],
                    "alignment_gr": gr_value,
                }
            )

    return pd.DataFrame.from_records(records)


def append_csv(frame: pd.DataFrame, path: Path) -> None:
    header = not path.exists()
    frame.to_csv(path, mode="a", header=header, index=False)


def reset_outputs() -> None:
    FEATURE_DIR.mkdir(exist_ok=True)
    for name in [
        "gr_features_train.csv",
        "gr_features_test.csv",
        "typewell_features_train.csv",
        "typewell_features_test.csv",
        "alignment_features_train.csv",
        "alignment_features_test.csv",
    ]:
        path = FEATURE_DIR / name
        if path.exists():
            path.unlink()


def build_split(split: str, data_dir: Path) -> None:
    for path in sorted(data_dir.glob("*__horizontal_well.csv")):
        well = path.name.split("__")[0]
        h = pd.read_csv(path)
        t = pd.read_csv(data_dir / f"{well}__typewell.csv")
        target_rows = np.flatnonzero(h["TVT_input"].isna().to_numpy())
        if len(target_rows) == 0:
            continue

        h.attrs["typewell_rows"] = len(t)
        h.attrs["typewell_has_geology"] = "Geology" in t.columns
        h.attrs["typewell_path"] = str(data_dir / f"{well}__typewell.csv")
        quality = compute_quality(h)

        baseline_pred = tail_slope_prediction(h, target_rows, tail_window=200)
        gr_frame = compute_gr_feature_frame(h, target_rows, baseline_pred, quality, well, split)
        typewell_frame = build_typewell_features(t, target_rows, baseline_pred, well, split, quality)
        align_frame = build_alignment_features(h, t, target_rows, well, split, quality, baseline_pred)

        append_csv(gr_frame, FEATURE_DIR / f"gr_features_{split}.csv")
        append_csv(typewell_frame, FEATURE_DIR / f"typewell_features_{split}.csv")
        append_csv(align_frame, FEATURE_DIR / f"alignment_features_{split}.csv")


def main() -> int:
    reset_outputs()
    build_split("train", resolve_train_dir())
    build_split("test", resolve_test_dir())
    print(f"Wrote feature tables to {FEATURE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
