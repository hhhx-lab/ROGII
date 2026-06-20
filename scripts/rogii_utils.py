#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"
TRAIN_DIR = DATA_DIR / "train"
TEST_DIR = DATA_DIR / "test"
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"
SUBMISSION_DIR = ROOT / "submissions"
FIGURE_DIR = REPORT_DIR / "figures"
DATA_VERSION_PATH = OUTPUT_DIR / "data_version.json"
DATA_CONTRACT_SUMMARY_PATH = OUTPUT_DIR / "data_contract_summary.csv"
DATA_CONTRACT_REPORT_PATH = REPORT_DIR / "data_contract_report.md"

TRAIN_HORIZONTAL_COLUMNS = [
    "MD",
    "X",
    "Y",
    "Z",
    "ANCC",
    "ASTNU",
    "ASTNL",
    "EGFDU",
    "EGFDL",
    "BUDA",
    "TVT",
    "GR",
    "TVT_input",
]
TEST_HORIZONTAL_COLUMNS = ["MD", "X", "Y", "Z", "GR", "TVT_input"]
TYPEWELL_COLUMNS = ["TVT", "GR", "Geology"]
TEST_TYPEWELL_COLUMNS = ["TVT", "GR"]


def ensure_project_dirs() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    SUBMISSION_DIR.mkdir(exist_ok=True)


def well_id_from_path(path: Path) -> str:
    return path.name.split("__")[0].split(".")[0]


def train_wells() -> list[str]:
    return sorted(well_id_from_path(path) for path in TRAIN_DIR.glob("*__horizontal_well.csv"))


def test_wells() -> list[str]:
    return sorted(well_id_from_path(path) for path in TEST_DIR.glob("*__horizontal_well.csv"))


def parse_submission_ids(sample: pd.DataFrame) -> pd.DataFrame:
    parsed = sample.copy()
    parts = parsed["id"].str.rsplit("_", n=1, expand=True)
    parsed["well"] = parts[0]
    parsed["row"] = parts[1].astype(int)
    return parsed


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_data_version() -> dict[str, object]:
    if not DATA_VERSION_PATH.exists():
        return {}
    return json.loads(DATA_VERSION_PATH.read_text())


def assert_data_contract_ready() -> dict[str, object]:
    if not DATA_VERSION_PATH.exists():
        raise FileNotFoundError("outputs/data_version.json is missing; run scripts/check_data_contract.py first")
    if not DATA_CONTRACT_SUMMARY_PATH.exists():
        raise FileNotFoundError("outputs/data_contract_summary.csv is missing; run scripts/check_data_contract.py first")
    if not DATA_CONTRACT_REPORT_PATH.exists():
        raise FileNotFoundError("reports/data_contract_report.md is missing; run scripts/check_data_contract.py first")

    summary = pd.read_csv(DATA_CONTRACT_SUMMARY_PATH)
    critical_errors = int(summary["critical_error_count"].sum()) if "critical_error_count" in summary else -1
    if critical_errors != 0:
        raise RuntimeError(
            f"data contract is not clean: critical_error_count={critical_errors}; "
            "inspect reports/data_contract_report.md before continuing"
        )
    return load_data_version()


def data_hash_short(data_version: dict[str, object] | None = None) -> str:
    version = data_version if data_version is not None else load_data_version()
    value = str(version.get("zip_sha256", "unknown"))
    return value[:12] if value != "unknown" else value


def contiguous_true_bounds(mask: np.ndarray) -> tuple[int, int]:
    rows = np.flatnonzero(mask)
    if len(rows) == 0:
        raise ValueError("mask does not contain target rows")
    return int(rows[0]), int(rows[-1])


def known_mask_from_bounds(df: pd.DataFrame, start_row: int = 0, end_row: int | None = None) -> np.ndarray:
    end = len(df) - 1 if end_row is None else min(int(end_row), len(df) - 1)
    start = max(0, int(start_row))
    index = np.arange(len(df))
    return (index >= start) & (index <= end) & df["TVT_input"].notna().to_numpy()


def split_target_rows(split: pd.Series | dict[str, object]) -> np.ndarray:
    return np.arange(int(split["start_row"]), int(split["end_row"]) + 1, dtype=int)


def apply_cv_split_mask(df: pd.DataFrame, split: pd.Series | dict[str, object], replace_tvt_input: bool = True) -> pd.DataFrame:
    masked = df.copy()
    masked["TVT_input_masked"] = np.nan

    known_start = max(0, int(split["known_allowed_start_row"]))
    known_end = min(len(masked) - 1, int(split["known_allowed_end_row"]))
    if known_end >= known_start:
        allowed_index = np.arange(known_start, known_end + 1)
        if str(split.get("mask_type", "")) == "original_hidden":
            masked.loc[allowed_index, "TVT_input_masked"] = masked.loc[allowed_index, "TVT_input"]
        else:
            masked.loc[allowed_index, "TVT_input_masked"] = masked.loc[allowed_index, "TVT"]

    target_rows = split_target_rows(split)
    masked.loc[target_rows, "TVT_input_masked"] = np.nan
    if replace_tvt_input:
        masked["TVT_input"] = masked["TVT_input_masked"]
    return masked


def regression_metrics(y_true: Iterable[float], y_pred: Iterable[float]) -> dict[str, float]:
    truth = np.asarray(list(y_true), dtype=float)
    pred = np.asarray(list(y_pred), dtype=float)
    errors = pred - truth
    abs_errors = np.abs(errors)
    return {
        "rmse": float(np.sqrt(np.mean(errors**2))),
        "mae": float(np.mean(abs_errors)),
        "median_abs_error": float(np.median(abs_errors)),
        "p90_abs_error": float(np.quantile(abs_errors, 0.90)),
        "p95_abs_error": float(np.quantile(abs_errors, 0.95)),
        "p99_abs_error": float(np.quantile(abs_errors, 0.99)),
        "max_abs_error": float(np.max(abs_errors)),
        "bias": float(np.mean(errors)),
    }


def _known_md_tvt(df: pd.DataFrame, known_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    md = df.loc[known_mask, "MD"].to_numpy(dtype=float)
    tvt = df.loc[known_mask, "TVT_input"].to_numpy(dtype=float)
    order = np.argsort(md)
    return md[order], tvt[order]


def baseline_constant_last(df: pd.DataFrame, target_rows: np.ndarray, known_mask: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    md_obs, tvt_obs = _known_md_tvt(df, known_mask)
    if len(tvt_obs):
        value = float(tvt_obs[-1])
    else:
        value = float(df["TVT"].median()) if "TVT" in df else 0.0
    return np.full(len(target_rows), value, dtype=float), {"baseline_slope": 0.0}


def baseline_linear_md(df: pd.DataFrame, target_rows: np.ndarray, known_mask: np.ndarray) -> tuple[np.ndarray, dict[str, float]]:
    md_obs, tvt_obs = _known_md_tvt(df, known_mask)
    if len(tvt_obs) < 2:
        return baseline_constant_last(df, target_rows, known_mask)
    md_pred = df.loc[target_rows, "MD"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(md_obs, tvt_obs, 1)
    preds = intercept + slope * md_pred
    return preds.astype(float), {"baseline_slope": float(slope), "linear_intercept": float(intercept)}


def baseline_tail_slope(
    df: pd.DataFrame,
    target_rows: np.ndarray,
    known_mask: np.ndarray,
    tail_window: int = 200,
) -> tuple[np.ndarray, dict[str, float]]:
    md_obs, tvt_obs = _known_md_tvt(df, known_mask)
    if len(tvt_obs) < 2:
        return baseline_constant_last(df, target_rows, known_mask)

    md_pred = df.loc[target_rows, "MD"].to_numpy(dtype=float)
    k = min(int(tail_window), len(md_obs))
    denom = np.diff(md_obs[-k:])
    numer = np.diff(tvt_obs[-k:])
    valid = np.isfinite(denom) & (denom != 0) & np.isfinite(numer)
    slopes = numer[valid] / denom[valid]
    slope = float(np.median(slopes)) if len(slopes) else 0.0

    preds = np.interp(md_pred, md_obs, tvt_obs)
    right = md_pred > md_obs[-1]
    if right.any():
        preds[right] = tvt_obs[-1] + slope * (md_pred[right] - md_obs[-1])

    left = md_pred < md_obs[0]
    if left.any():
        left_k = min(int(tail_window), len(md_obs))
        left_denom = np.diff(md_obs[:left_k])
        left_numer = np.diff(tvt_obs[:left_k])
        left_valid = np.isfinite(left_denom) & (left_denom != 0) & np.isfinite(left_numer)
        left_slopes = left_numer[left_valid] / left_denom[left_valid]
        left_slope = float(np.median(left_slopes)) if len(left_slopes) else slope
        preds[left] = tvt_obs[0] + left_slope * (md_pred[left] - md_obs[0])

    return preds.astype(float), {"baseline_slope": slope, "tail_window": float(tail_window)}


BASELINE_CONFIGS: list[dict[str, object]] = [
    {"baseline": "B0_constant_last", "family": "B0", "tail_window": None},
    {"baseline": "B1_linear_md", "family": "B1", "tail_window": None},
    {"baseline": "B2_tail_slope_k50", "family": "B2", "tail_window": 50},
    {"baseline": "B2_tail_slope_k100", "family": "B2", "tail_window": 100},
    {"baseline": "B2_tail_slope_k200", "family": "B2", "tail_window": 200},
    {"baseline": "B2_tail_slope_k500", "family": "B2", "tail_window": 500},
]


def run_baseline(
    df: pd.DataFrame,
    target_rows: np.ndarray,
    baseline: str,
    known_allowed_start_row: int = 0,
    known_allowed_end_row: int | None = None,
) -> tuple[np.ndarray, dict[str, float]]:
    known_mask = known_mask_from_bounds(df, known_allowed_start_row, known_allowed_end_row)
    if baseline == "B0_constant_last":
        return baseline_constant_last(df, target_rows, known_mask)
    if baseline == "B1_linear_md":
        return baseline_linear_md(df, target_rows, known_mask)
    for config in BASELINE_CONFIGS:
        if config["baseline"] == baseline and config["family"] == "B2":
            return baseline_tail_slope(df, target_rows, known_mask, tail_window=int(config["tail_window"]))
    raise ValueError(f"unknown baseline: {baseline}")


def max_step_jump(values: Iterable[float]) -> float:
    arr = np.asarray(list(values), dtype=float)
    if len(arr) < 2:
        return 0.0
    return float(np.max(np.abs(np.diff(arr))))


def missing_rate(series: pd.Series) -> float:
    return float(series.isna().mean()) if len(series) else 0.0
