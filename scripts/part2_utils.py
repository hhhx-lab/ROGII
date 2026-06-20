from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from rogii_utils import DATA_VERSION_PATH, OUTPUT_DIR, REPORT_DIR, ROOT


FEATURE_DIR = ROOT / "features"
MODEL_DIR = ROOT / "models"
PART2_SEED = 20260620
BASELINE_NAME = "B0_constant_last"
ALPHA_GRID = [0.0, 0.25, 0.5, 0.75, 1.0]
FEATURE_VERSION = "part2_geometry_v1"


def ensure_part2_dirs() -> None:
    FEATURE_DIR.mkdir(exist_ok=True)
    MODEL_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text()) if path.exists() else {}


def data_hash_short() -> str:
    version = read_json(DATA_VERSION_PATH)
    value = str(version.get("zip_sha256", "unknown"))
    return value[:12] if value != "unknown" else value


def target_rows_from_tvt_input(df: pd.DataFrame) -> np.ndarray:
    rows = np.flatnonzero(df["TVT_input"].isna().to_numpy())
    if len(rows) == 0:
        raise ValueError("well has no TVT_input hidden target rows")
    return np.arange(int(rows[0]), int(rows[-1]) + 1, dtype=int)


def split_id_for(well: str, target_rows: np.ndarray) -> str:
    return f"original_hidden__{well}__{int(target_rows[0])}_{int(target_rows[-1])}"


def finite_median(values: np.ndarray, default: float = 0.0) -> float:
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    return float(np.median(finite)) if len(finite) else float(default)


def slope_stats(md: np.ndarray, tvt: np.ndarray) -> dict[str, float]:
    if len(md) < 2:
        return {"mean": 0.0, "std": 0.0, "tail_50": 0.0, "tail_100": 0.0, "tail_200": 0.0, "tail_500": 0.0}
    denom = np.diff(md)
    numer = np.diff(tvt)
    slopes = np.divide(numer, denom, out=np.full_like(numer, np.nan, dtype=float), where=denom != 0)
    slopes = slopes[np.isfinite(slopes)]
    result = {
        "mean": float(np.mean(slopes)) if len(slopes) else 0.0,
        "std": float(np.std(slopes)) if len(slopes) else 0.0,
    }
    for window in [50, 100, 200, 500]:
        result[f"tail_{window}"] = finite_median(slopes[-window:] if len(slopes) else [], default=result["mean"])
    return result


def add_key_columns(frame: pd.DataFrame, well: str, target_rows: np.ndarray) -> pd.DataFrame:
    out = frame.copy()
    out.insert(0, "id", [f"{well}_{int(row)}" for row in target_rows])
    out.insert(0, "row", target_rows.astype(np.int32))
    out.insert(0, "well", well)
    out.insert(0, "split_id", split_id_for(well, target_rows))
    return out


def feature_columns_from(frame: pd.DataFrame) -> list[str]:
    blocked = {
        "split_id",
        "well",
        "row",
        "id",
        "true_tvt",
        "baseline_tvt",
        "residual_target",
        "baseline_name",
        "data_hash",
    }
    return [col for col in frame.columns if col not in blocked and pd.api.types.is_numeric_dtype(frame[col])]


def sample_training_rows(frame: pd.DataFrame, groups: pd.Series, rows_per_well: int, seed: int) -> np.ndarray:
    if rows_per_well <= 0:
        return np.arange(len(frame), dtype=int)
    rng = np.random.default_rng(seed)
    indices: list[np.ndarray] = []
    group_array = groups.to_numpy()
    for well in np.unique(group_array):
        well_idx = np.flatnonzero(group_array == well)
        if len(well_idx) > rows_per_well:
            well_idx = rng.choice(well_idx, size=rows_per_well, replace=False)
        indices.append(np.asarray(well_idx, dtype=int))
    return np.concatenate(indices) if indices else np.asarray([], dtype=int)


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    return default if value in {None, ""} else int(value)


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    return default if value in {None, ""} else float(value)
