from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
SUBMISSIONS_DIR = ROOT / "submissions"


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def resolve_competition_root() -> Path:
    for candidate in (DATA_DIR, RAW_DATA_DIR):
        if (candidate / "train").exists() or (candidate / "test").exists():
            return candidate
    return DATA_DIR


def resolve_train_dir() -> Path:
    root = resolve_competition_root()
    path = root / "train"
    if path.exists():
        return path
    raise FileNotFoundError(f"Missing train directory under {root}")


def resolve_test_dir() -> Path:
    root = resolve_competition_root()
    path = root / "test"
    if path.exists():
        return path
    raise FileNotFoundError(f"Missing test directory under {root}")


def resolve_sample_submission_path() -> Path:
    candidates = [
        DATA_DIR / "sample_submission.csv",
        RAW_DATA_DIR / "sample_submission.csv",
    ]
    path = _first_existing(candidates)
    if path is None:
        raise FileNotFoundError("Missing sample_submission.csv under data/ or data/raw/")
    return path


def build_sample_submission_from_test() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    test_dir = resolve_test_dir()
    for path in sorted(test_dir.glob("*__horizontal_well.csv")):
        well = path.name.split("__")[0]
        df = pd.read_csv(path, usecols=["TVT_input"])
        for row in df.index[df["TVT_input"].isna()]:
            rows.append({"id": f"{well}_{int(row)}", "tvt": float("nan")})
    if not rows:
        raise FileNotFoundError("Unable to synthesize sample submission: no hidden rows found in data/test")
    return pd.DataFrame(rows, columns=["id", "tvt"])


def load_sample_submission() -> pd.DataFrame:
    for candidate in (DATA_DIR / "sample_submission.csv", RAW_DATA_DIR / "sample_submission.csv"):
        if candidate.exists():
            return pd.read_csv(candidate)
    return build_sample_submission_from_test()


def resolve_horizontal_path(split: str, well: str) -> Path:
    return resolve_competition_root() / split / f"{well}__horizontal_well.csv"


def resolve_typewell_path(split: str, well: str) -> Path:
    return resolve_competition_root() / split / f"{well}__typewell.csv"
