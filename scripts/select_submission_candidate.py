#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error

from data_paths import load_sample_submission


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
REPORT_DIR = ROOT / "reports"
MODEL_DIR = ROOT / "models"
SUBMISSION_DIR = ROOT / "submissions"
DATA_VERSION_PATH = OUTPUT_DIR / "data_version.json"
SELECTION_JSON = OUTPUT_DIR / "selected_candidate.json"
SELECTION_REPORT = REPORT_DIR / "candidate_selection_report.md"

PREDICTION_COLUMNS = ["tvt", "final_pred", "baseline_tvt", "geometry_tvt", "xgb_tvt", "variant_tvt"]
DEFAULT_COVERAGE_THRESHOLD = 0.95


@dataclass(frozen=True)
class CandidateSpec:
    name: str
    kind: str
    oof_path: Path
    pred_col: str
    submission_path: Path
    metadata_paths: tuple[Path, ...] = field(default_factory=tuple)


@dataclass
class VersionInfo:
    status: str = "unknown"
    reason: str = "no artifact version metadata found"
    data_hash: str | None = None
    run_id: str | None = None
    metadata_path: str = ""


@dataclass
class CandidateResult:
    name: str
    kind: str
    status: str
    reason: str
    rmse: float | None = None
    mae: float | None = None
    p95_abs_error: float | None = None
    worst_well_rmse: float | None = None
    degraded_wells: int | None = None
    improved_wells: int | None = None
    rows: int | None = None
    wells: int | None = None
    baseline_rows: int | None = None
    baseline_wells: int | None = None
    coverage_vs_baseline_rows: float | None = None
    coverage_vs_baseline_wells: float | None = None
    common_rmse: float | None = None
    common_mae: float | None = None
    common_p95_abs_error: float | None = None
    common_worst_well_rmse: float | None = None
    common_rows: int | None = None
    common_wells: int | None = None
    eligible: bool = False
    version_status: str = "unknown"
    version_reason: str = ""
    artifact_data_hash: str | None = None
    run_id: str | None = None
    metadata_path: str = ""
    duplicate_ids_dropped: int = 0
    oof_path: str = ""
    submission_path: str = ""
    is_postprocessed: bool = False

    def to_record(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "status": self.status,
            "reason": self.reason,
            "rmse": self.rmse,
            "mae": self.mae,
            "p95_abs_error": self.p95_abs_error,
            "worst_well_rmse": self.worst_well_rmse,
            "degraded_wells": self.degraded_wells,
            "improved_wells": self.improved_wells,
            "rows": self.rows,
            "wells": self.wells,
            "baseline_rows": self.baseline_rows,
            "baseline_wells": self.baseline_wells,
            "coverage_vs_baseline_rows": self.coverage_vs_baseline_rows,
            "coverage_vs_baseline_wells": self.coverage_vs_baseline_wells,
            "common_rmse": self.common_rmse,
            "common_mae": self.common_mae,
            "common_p95_abs_error": self.common_p95_abs_error,
            "common_worst_well_rmse": self.common_worst_well_rmse,
            "common_rows": self.common_rows,
            "common_wells": self.common_wells,
            "eligible": self.eligible,
            "version_status": self.version_status,
            "version_reason": self.version_reason,
            "artifact_data_hash": self.artifact_data_hash,
            "run_id": self.run_id,
            "metadata_path": self.metadata_path,
            "duplicate_ids_dropped": self.duplicate_ids_dropped,
            "oof_path": self.oof_path,
            "submission_path": self.submission_path,
            "is_postprocessed": self.is_postprocessed,
        }


def markdown_table(frame: pd.DataFrame, index: bool = False) -> str:
    try:
        return frame.to_markdown(index=index)
    except ImportError:
        return frame.to_string(index=index)


def safe_rmse(y_true: pd.Series | np.ndarray, y_pred: pd.Series | np.ndarray) -> float:
    return float(mean_squared_error(np.asarray(y_true, dtype=float), np.asarray(y_pred, dtype=float)) ** 0.5)


def safe_ratio(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator in {None, 0}:
        return None
    return float(numerator) / float(denominator)


def relpath(path: Path | str) -> str:
    try:
        return str(Path(path).relative_to(ROOT))
    except Exception:
        return str(path)


def prediction_column(frame: pd.DataFrame, preferred: str | None = None) -> str:
    if preferred and preferred in frame.columns:
        return preferred
    for col in PREDICTION_COLUMNS:
        if col in frame.columns:
            return col
    numeric = [col for col in frame.columns if col != "id" and pd.api.types.is_numeric_dtype(frame[col])]
    if len(numeric) == 1:
        return numeric[0]
    raise ValueError(f"Could not determine prediction column from columns: {list(frame.columns)}")


def load_submission_like(path: Path, sample: pd.DataFrame | None = None, preferred_col: str | None = None) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string"})
    if "id" not in frame.columns:
        raise ValueError(f"{path} must contain id")
    pred_col = prediction_column(frame, preferred_col)
    submission = frame[["id", pred_col]].rename(columns={pred_col: "tvt"})
    submission["id"] = submission["id"].astype("string")
    submission["tvt"] = submission["tvt"].astype(float)
    if sample is not None:
        sample_ids = sample[["id"]].copy()
        sample_ids["id"] = sample_ids["id"].astype("string")
        submission = sample_ids.merge(submission, on="id", how="left", validate="one_to_one")
        if submission["tvt"].isna().any():
            missing = int(submission["tvt"].isna().sum())
            raise ValueError(f"{path} is missing {missing} sample ids")
    if not np.isfinite(submission["tvt"].to_numpy(dtype=float)).all():
        raise ValueError(f"{path} contains NaN or inf predictions")
    return submission[["id", "tvt"]]


def load_oof(path: Path, pred_col: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    frame = pd.read_csv(path, dtype={"id": "string", "well": "string"}, low_memory=False)
    if "truth_tvt" not in frame.columns:
        raise ValueError(f"{path} must contain truth_tvt")
    if "well" not in frame.columns:
        frame["well"] = frame["id"].str.rsplit("_", n=1).str[0]
    actual_pred_col = prediction_column(frame, pred_col)
    out = frame[["id", "well", "truth_tvt", actual_pred_col]].rename(columns={actual_pred_col: "prediction"})
    out["id"] = out["id"].astype("string")
    out["well"] = out["well"].astype("string")
    duplicate_count = int(out["id"].duplicated().sum())
    if duplicate_count:
        out = out.drop_duplicates("id", keep="first").reset_index(drop=True)
    out.attrs["duplicate_ids_dropped"] = duplicate_count
    return out


def candidate_specs() -> list[CandidateSpec]:
    specs = [
        CandidateSpec(
            name="baseline",
            kind="baseline",
            oof_path=OUTPUT_DIR / "baseline_predictions_train_hidden.csv",
            pred_col="baseline_tvt",
            submission_path=OUTPUT_DIR / "baseline_predictions_test.csv",
            metadata_paths=(REPORT_DIR / "baseline_submission_report.md", REPORT_DIR / "baseline_multimask_report.md"),
        ),
        CandidateSpec(
            name="geometry",
            kind="residual",
            oof_path=OUTPUT_DIR / "residual_geometry_oof.csv",
            pred_col="final_pred",
            submission_path=SUBMISSION_DIR / "geometry_residual_submission.csv",
            metadata_paths=(
                MODEL_DIR / "residual_geometry_config.json",
                MODEL_DIR / "residual_geometry_hgb_config.json",
                REPORT_DIR / "residual_geometry_cv_report.md",
            ),
        ),
        CandidateSpec(
            name="xgb",
            kind="tree_residual",
            oof_path=OUTPUT_DIR / "residual_xgb_oof.csv",
            pred_col="final_pred",
            submission_path=SUBMISSION_DIR / "xgb_residual_submission.csv",
            metadata_paths=(MODEL_DIR / "residual_xgb_config.json", REPORT_DIR / "residual_xgb_cv_report.md"),
        ),
    ]
    blend_path = OUTPUT_DIR / "blend_oof.csv"
    for variant in ("conservative", "balanced", "aggressive", "optimized"):
        specs.append(
            CandidateSpec(
                name=variant,
                kind="blend",
                oof_path=blend_path,
                pred_col=f"{variant}_tvt",
                submission_path=SUBMISSION_DIR / f"{variant}_submission.csv",
                metadata_paths=(REPORT_DIR / "ensemble_report.md",),
            )
        )
    return specs


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_current_data_version() -> dict[str, Any]:
    return read_json(DATA_VERSION_PATH)


def meaningful(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in {"", "none", "null", "nan", "unknown"}:
        return None
    return text


def find_key_recursive(obj: Any, keys: set[str]) -> object | None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in keys:
                return value
        for value in obj.values():
            found = find_key_recursive(value, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_key_recursive(value, keys)
            if found is not None:
                return found
    return None


def extract_markdown_metadata(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    text = path.read_text(encoding="utf-8", errors="ignore")
    patterns = {
        "data_hash": r"data hash:\s*`?([A-Za-z0-9_.:-]+)`?",
        "data_version": r"data version:\s*`?([A-Za-z0-9_.:-]+)`?",
        "run_id": r"run id:\s*`?([A-Za-z0-9_.:-]+)`?",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            values[key] = match.group(1)
    return values


def extract_csv_metadata(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    try:
        columns = pd.read_csv(path, nrows=0).columns.tolist()
    except Exception:
        return values
    for key in ("data_hash", "data_version", "run_id"):
        if key not in columns:
            continue
        try:
            sample = pd.read_csv(path, usecols=[key], nrows=1000)
            uniques = [meaningful(value) for value in sample[key].dropna().unique().tolist()]
            uniques = [value for value in uniques if value is not None]
            if len(set(uniques)) == 1:
                values[key] = uniques[0]
        except Exception:
            continue
    return values


def artifact_version_info(spec: CandidateSpec, current_version: dict[str, Any]) -> VersionInfo:
    data_hash: str | None = None
    run_id: str | None = None
    data_version: dict[str, Any] | str | None = None
    source_path: str = ""

    candidate_paths = [spec.oof_path, *spec.metadata_paths]
    for path in candidate_paths:
        if not path.exists():
            continue
        values: dict[str, Any] = {}
        if path.suffix.lower() == ".json":
            data = read_json(path)
            values["data_hash"] = find_key_recursive(data, {"data_hash", "zip_sha256"})
            values["data_version"] = find_key_recursive(data, {"data_version"})
            values["run_id"] = find_key_recursive(data, {"run_id"})
        elif path.suffix.lower() in {".md", ".txt"}:
            values = extract_markdown_metadata(path)
        elif path.suffix.lower() == ".csv":
            values = extract_csv_metadata(path)

        maybe_hash = meaningful(values.get("data_hash"))
        maybe_run = meaningful(values.get("run_id"))
        maybe_version = values.get("data_version")
        if maybe_hash or maybe_run or maybe_version:
            data_hash = maybe_hash or data_hash
            run_id = maybe_run or run_id
            data_version = maybe_version or data_version
            source_path = relpath(path)
            break

    if data_hash is None and data_version is None and run_id is None:
        return VersionInfo(metadata_path=source_path)

    current_hash = meaningful(current_version.get("zip_sha256"))
    if data_hash and current_hash:
        hash_matches = data_hash == current_hash or current_hash.startswith(data_hash) or data_hash.startswith(current_hash)
        if not hash_matches:
            return VersionInfo(
                status="mismatch",
                reason=f"artifact data_hash={data_hash} does not match current zip_sha256={current_hash}",
                data_hash=data_hash,
                run_id=run_id,
                metadata_path=source_path,
            )
        return VersionInfo(
            status="matched",
            reason="artifact data_hash matches current data_version zip_sha256",
            data_hash=data_hash,
            run_id=run_id,
            metadata_path=source_path,
        )

    if isinstance(data_version, dict) and current_version:
        compared = []
        for key in ("raw_file_count", "train_well_count", "test_well_count", "sample_submission_rows", "zip_size_bytes"):
            left = data_version.get(key)
            right = current_version.get(key)
            if left is not None and right is not None:
                compared.append(key)
                if str(left) != str(right):
                    return VersionInfo(
                        status="mismatch",
                        reason=f"artifact data_version.{key}={left} does not match current={right}",
                        data_hash=data_hash,
                        run_id=run_id,
                        metadata_path=source_path,
                    )
        if compared:
            return VersionInfo(
                status="matched",
                reason="artifact data_version count fields match current data_version",
                data_hash=data_hash,
                run_id=run_id,
                metadata_path=source_path,
            )

    return VersionInfo(
        status="unknown",
        reason="artifact has version metadata but current data hash is unavailable or unverifiable",
        data_hash=data_hash,
        run_id=run_id,
        metadata_path=source_path,
    )


def skipped_result(spec: CandidateSpec, reason: str, version: VersionInfo | None = None, status: str = "skipped") -> CandidateResult:
    version = version or VersionInfo()
    return CandidateResult(
        name=spec.name,
        kind=spec.kind,
        status=status,
        reason=reason,
        eligible=False,
        version_status=version.status,
        version_reason=version.reason,
        artifact_data_hash=version.data_hash,
        run_id=version.run_id,
        metadata_path=version.metadata_path,
        oof_path=str(spec.oof_path),
        submission_path=str(spec.submission_path),
    )


def preload_candidate(spec: CandidateSpec, current_version: dict[str, Any]) -> tuple[CandidateResult | None, pd.DataFrame | None]:
    version = artifact_version_info(spec, current_version)
    if version.status == "mismatch":
        return skipped_result(spec, version.reason, version, status="version_mismatch"), None
    if not spec.oof_path.exists():
        return skipped_result(spec, f"missing OOF: {relpath(spec.oof_path)}", version), None
    if not spec.submission_path.exists():
        return skipped_result(spec, f"missing submission/test prediction: {relpath(spec.submission_path)}", version), None
    try:
        frame = load_oof(spec.oof_path, spec.pred_col)
    except Exception as exc:
        return skipped_result(spec, str(exc), version), None
    frame.attrs["version_info"] = version
    return None, frame


def baseline_reference_from_loaded(loaded: dict[str, pd.DataFrame]) -> pd.DataFrame | None:
    baseline = loaded.get("baseline")
    if baseline is None:
        path = OUTPUT_DIR / "baseline_predictions_train_hidden.csv"
        if not path.exists():
            return None
        try:
            baseline = load_oof(path, "baseline_tvt")
        except Exception:
            return None
    return baseline[["id", "well", "truth_tvt", "prediction"]].rename(columns={"prediction": "baseline_prediction"})


def coverage_values(frame: pd.DataFrame, baseline_oof: pd.DataFrame | None) -> tuple[int, int, int | None, int | None, float | None, float | None]:
    rows = int(len(frame))
    wells = int(frame["well"].nunique())
    baseline_rows = int(len(baseline_oof)) if baseline_oof is not None else None
    baseline_wells = int(baseline_oof["well"].nunique()) if baseline_oof is not None else None
    return rows, wells, baseline_rows, baseline_wells, safe_ratio(rows, baseline_rows), safe_ratio(wells, baseline_wells)


def per_well_metrics(frame: pd.DataFrame, baseline_oof: pd.DataFrame | None) -> tuple[pd.DataFrame, int | None, int | None]:
    per_well = (
        frame.groupby("well", as_index=False)
        .agg(
            rows=("id", "count"),
            rmse=("error", lambda s: float(np.sqrt(np.mean(s.to_numpy(dtype=float) ** 2)))),
            mae=("abs_error", "mean"),
        )
        .sort_values("rmse", ascending=False)
    )
    if baseline_oof is None:
        return per_well, None, None

    joined = frame.merge(baseline_oof[["id", "baseline_prediction"]], on="id", how="left", validate="one_to_one")
    joined = joined[joined["baseline_prediction"].notna()].copy()
    if joined.empty:
        return per_well, None, None
    joined["baseline_error"] = joined["baseline_prediction"].astype(float) - joined["truth_tvt"].astype(float)
    baseline_by_well = (
        joined.groupby("well", as_index=False)
        .agg(baseline_rmse=("baseline_error", lambda s: float(np.sqrt(np.mean(s.to_numpy(dtype=float) ** 2)))))
    )
    per_well = per_well.merge(baseline_by_well, on="well", how="left", validate="one_to_one")
    per_well["rmse_improvement_vs_baseline"] = per_well["baseline_rmse"] - per_well["rmse"]
    degraded = int((per_well["rmse_improvement_vs_baseline"] < 0).sum())
    improved = int((per_well["rmse_improvement_vs_baseline"] > 0).sum())
    return per_well, degraded, improved


def score_frame(frame: pd.DataFrame, baseline_oof: pd.DataFrame | None) -> tuple[dict[str, float | int | None], pd.DataFrame]:
    scored = frame.copy()
    scored["error"] = scored["prediction"].astype(float) - scored["truth_tvt"].astype(float)
    scored["abs_error"] = scored["error"].abs()
    per_well, degraded, improved = per_well_metrics(scored, baseline_oof)
    metrics: dict[str, float | int | None] = {
        "rmse": safe_rmse(scored["truth_tvt"], scored["prediction"]),
        "mae": float(np.mean(scored["abs_error"].to_numpy(dtype=float))),
        "p95_abs_error": float(np.quantile(scored["abs_error"].to_numpy(dtype=float), 0.95)),
        "worst_well_rmse": float(per_well["rmse"].max()) if len(per_well) else None,
        "degraded_wells": degraded,
        "improved_wells": improved,
    }
    return metrics, per_well


def score_candidate_frame(
    spec: CandidateSpec,
    frame: pd.DataFrame,
    baseline_oof: pd.DataFrame | None,
    coverage_threshold: float,
) -> tuple[CandidateResult, pd.DataFrame]:
    version: VersionInfo = frame.attrs.get("version_info", VersionInfo())
    if len(frame) == 0:
        return skipped_result(spec, "empty OOF coverage", version), pd.DataFrame()

    rows, wells, baseline_rows, baseline_wells, row_cov, well_cov = coverage_values(frame, baseline_oof)
    metrics, per_well = score_frame(frame, baseline_oof)
    duplicate_ids_dropped = int(frame.attrs.get("duplicate_ids_dropped", 0))
    coverage_ok = True
    coverage_reason = "OOF evaluated on full candidate coverage"
    if baseline_oof is not None:
        row_ok = row_cov is not None and row_cov >= coverage_threshold
        well_ok = well_cov is not None and well_cov >= coverage_threshold
        coverage_ok = row_ok and well_ok
        if not coverage_ok:
            coverage_reason = (
                "insufficient OOF coverage vs baseline "
                f"(rows={row_cov:.4f} wells={well_cov:.4f}, required>={coverage_threshold:.2f})"
            )

    if duplicate_ids_dropped:
        coverage_reason += f"; duplicate ids dropped={duplicate_ids_dropped}"

    result = CandidateResult(
        name=spec.name,
        kind=spec.kind,
        status="available" if coverage_ok else "insufficient_coverage",
        reason=coverage_reason,
        rmse=float(metrics["rmse"]),
        mae=float(metrics["mae"]),
        p95_abs_error=float(metrics["p95_abs_error"]),
        worst_well_rmse=None if metrics["worst_well_rmse"] is None else float(metrics["worst_well_rmse"]),
        degraded_wells=None if metrics["degraded_wells"] is None else int(metrics["degraded_wells"]),
        improved_wells=None if metrics["improved_wells"] is None else int(metrics["improved_wells"]),
        rows=rows,
        wells=wells,
        baseline_rows=baseline_rows,
        baseline_wells=baseline_wells,
        coverage_vs_baseline_rows=row_cov,
        coverage_vs_baseline_wells=well_cov,
        eligible=coverage_ok,
        version_status=version.status,
        version_reason=version.reason,
        artifact_data_hash=version.data_hash,
        run_id=version.run_id,
        metadata_path=version.metadata_path,
        duplicate_ids_dropped=duplicate_ids_dropped,
        oof_path=str(spec.oof_path),
        submission_path=str(spec.submission_path),
    )
    return result, per_well


def parse_postprocess_report(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"available": False, "reason": "missing postprocess report"}
    values: dict[str, object] = {"available": True}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if stripped.startswith("- Variant:"):
            values["variant"] = stripped.split("`")[1] if "`" in stripped else stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Decision:"):
            values["decision"] = stripped.split("`")[1] if "`" in stripped else stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- Decision reason:"):
            values["reason"] = stripped.split("`")[1] if "`" in stripped else stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- OOF path:"):
            values["oof_path"] = stripped.split("`")[1] if "`" in stripped else stripped.split(":", 1)[1].strip()
    return values


def postprocess_candidate_result(
    baseline_oof: pd.DataFrame | None,
    coverage_threshold: float,
    current_version: dict[str, Any],
) -> tuple[CandidateResult | None, pd.DataFrame, CandidateResult | None]:
    guard = parse_postprocess_report(REPORT_DIR / "postprocess_report.md")
    variant = str(guard.get("variant") or "")
    decision = str(guard.get("decision") or "")
    reason = str(guard.get("reason") or "unknown")
    submission_path = SUBMISSION_DIR / f"{variant}_postprocessed_submission.csv" if variant else Path("")
    skipped = CandidateResult(
        name=f"{variant}_postprocessed" if variant else "postprocessed",
        kind="postprocess",
        status="skipped",
        reason=f"postprocess guard decision={decision or 'unknown'} reason={reason}",
        oof_path=str(OUTPUT_DIR / "postprocess_oof_summary.csv"),
        submission_path=str(submission_path) if variant else "",
        is_postprocessed=True,
    )
    if not guard.get("available"):
        return None, pd.DataFrame(), skipped
    if decision != "accepted":
        return None, pd.DataFrame(), skipped

    summary_path = OUTPUT_DIR / "postprocess_oof_summary.csv"
    per_well_path = OUTPUT_DIR / "postprocess_oof_by_well.csv"
    if not summary_path.exists() or not per_well_path.exists() or not submission_path.exists():
        skipped.reason = "postprocess accepted but machine-readable OOF files or submission are missing"
        return None, pd.DataFrame(), skipped

    version = artifact_version_info(
        CandidateSpec(
            name=f"{variant}_postprocessed",
            kind="postprocess",
            oof_path=summary_path,
            pred_col="rmse_after",
            submission_path=submission_path,
            metadata_paths=(REPORT_DIR / "postprocess_report.md",),
        ),
        current_version,
    )
    if version.status == "mismatch":
        skipped.status = "version_mismatch"
        skipped.reason = version.reason
        skipped.version_status = version.status
        skipped.version_reason = version.reason
        return None, pd.DataFrame(), skipped

    summary = pd.read_csv(summary_path)
    per_well = pd.read_csv(per_well_path, dtype={"well": "string"})
    metric = dict(zip(summary["metric"], summary["value"]))
    if "rmse_after" not in metric:
        skipped.reason = "postprocess OOF summary does not contain rmse_after"
        return None, pd.DataFrame(), skipped

    rows = int(per_well["rows"].sum()) if "rows" in per_well else None
    wells = int(per_well["well"].nunique()) if "well" in per_well else None
    baseline_rows = int(len(baseline_oof)) if baseline_oof is not None else None
    baseline_wells = int(baseline_oof["well"].nunique()) if baseline_oof is not None else None
    row_cov = safe_ratio(rows, baseline_rows)
    well_cov = safe_ratio(wells, baseline_wells)
    coverage_ok = True
    coverage_reason = "postprocess guard accepted"
    if baseline_oof is not None:
        coverage_ok = bool(row_cov is not None and row_cov >= coverage_threshold and well_cov is not None and well_cov >= coverage_threshold)
        if not coverage_ok:
            coverage_reason = (
                "postprocess guard accepted but OOF coverage is insufficient "
                f"(rows={row_cov:.4f} wells={well_cov:.4f}, required>={coverage_threshold:.2f})"
            )

    per_well["rmse_improvement_vs_input"] = per_well["rmse_before"] - per_well["rmse_after"]
    result = CandidateResult(
        name=f"{variant}_postprocessed",
        kind="postprocess",
        status="available" if coverage_ok else "insufficient_coverage",
        reason=coverage_reason,
        rmse=float(metric.get("rmse_after")),
        mae=float(metric.get("mae_after", math.nan)),
        p95_abs_error=float(metric.get("p95_after", math.nan)),
        worst_well_rmse=float(per_well["rmse_after"].max()) if len(per_well) else None,
        degraded_wells=int((per_well["rmse_improvement_vs_input"] < 0).sum()) if len(per_well) else None,
        improved_wells=int((per_well["rmse_improvement_vs_input"] > 0).sum()) if len(per_well) else None,
        rows=rows,
        wells=wells,
        baseline_rows=baseline_rows,
        baseline_wells=baseline_wells,
        coverage_vs_baseline_rows=row_cov,
        coverage_vs_baseline_wells=well_cov,
        eligible=coverage_ok,
        version_status=version.status,
        version_reason=version.reason,
        artifact_data_hash=version.data_hash,
        run_id=version.run_id,
        metadata_path=version.metadata_path,
        oof_path=str(summary_path),
        submission_path=str(submission_path),
        is_postprocessed=True,
    )
    return result, per_well, None


def apply_common_comparison(
    results: list[CandidateResult],
    frames: dict[str, pd.DataFrame],
    baseline_oof: pd.DataFrame | None,
    coverage_threshold: float,
) -> dict[str, object]:
    eligible_names = [result.name for result in results if result.eligible and result.name in frames]
    baseline_rows = int(len(baseline_oof)) if baseline_oof is not None else None
    baseline_wells = int(baseline_oof["well"].nunique()) if baseline_oof is not None else None
    if len(eligible_names) < 2:
        return {
            "enabled": False,
            "usable_for_selection": False,
            "used_for_selection": False,
            "reason": "fewer than two full-coverage candidates",
            "common_rows": None,
            "common_wells": None,
            "coverage_vs_baseline_rows": None,
            "coverage_vs_baseline_wells": None,
        }

    common_ids = set(frames[eligible_names[0]]["id"].astype(str))
    for name in eligible_names[1:]:
        common_ids &= set(frames[name]["id"].astype(str))

    common_rows = len(common_ids)
    if common_ids:
        first = frames[eligible_names[0]]
        common_wells = int(first[first["id"].astype(str).isin(common_ids)]["well"].nunique())
    else:
        common_wells = 0
    row_cov = safe_ratio(common_rows, baseline_rows)
    well_cov = safe_ratio(common_wells, baseline_wells)
    usable = bool(row_cov is not None and row_cov >= coverage_threshold and well_cov is not None and well_cov >= coverage_threshold)

    for result in results:
        if result.name not in eligible_names or not common_ids:
            continue
        common = frames[result.name][frames[result.name]["id"].astype(str).isin(common_ids)].copy()
        metrics, _ = score_frame(common, baseline_oof)
        result.common_rmse = float(metrics["rmse"])
        result.common_mae = float(metrics["mae"])
        result.common_p95_abs_error = float(metrics["p95_abs_error"])
        result.common_worst_well_rmse = None if metrics["worst_well_rmse"] is None else float(metrics["worst_well_rmse"])
        result.common_rows = int(len(common))
        result.common_wells = int(common["well"].nunique())

    return {
        "enabled": True,
        "usable_for_selection": usable,
        "used_for_selection": False,
        "reason": "common coverage is reported only; final ranking uses full candidate OOF coverage",
        "common_rows": common_rows,
        "common_wells": common_wells,
        "coverage_vs_baseline_rows": row_cov,
        "coverage_vs_baseline_wells": well_cov,
    }


def collect_candidates(
    coverage_threshold: float = DEFAULT_COVERAGE_THRESHOLD,
) -> tuple[list[CandidateResult], list[CandidateResult], dict[str, pd.DataFrame], dict[str, object], dict[str, Any]]:
    current_version = load_current_data_version()
    loaded: dict[str, pd.DataFrame] = {}
    skipped: list[CandidateResult] = []
    specs_by_name = {spec.name: spec for spec in candidate_specs()}

    for spec in candidate_specs():
        skip_result, frame = preload_candidate(spec, current_version)
        if skip_result is not None:
            skipped.append(skip_result)
        elif frame is not None:
            loaded[spec.name] = frame

    baseline_oof = baseline_reference_from_loaded(loaded)
    evaluated: list[CandidateResult] = []
    per_well: dict[str, pd.DataFrame] = {}
    for name, frame in loaded.items():
        spec = specs_by_name[name]
        result, per_well_frame = score_candidate_frame(spec, frame, baseline_oof, coverage_threshold)
        evaluated.append(result)
        if result.eligible:
            per_well[name] = per_well_frame
        else:
            skipped.append(result)

    post_result, post_per_well, post_skipped = postprocess_candidate_result(baseline_oof, coverage_threshold, current_version)
    if post_result is not None:
        evaluated.append(post_result)
        if post_result.eligible:
            per_well[post_result.name] = post_per_well
        else:
            skipped.append(post_result)
    elif post_skipped is not None:
        skipped.append(post_skipped)

    common_info = apply_common_comparison(evaluated, loaded, baseline_oof, coverage_threshold)
    return evaluated, skipped, per_well, common_info, current_version


def choose_candidate(evaluated: list[CandidateResult], tie_rmse_tolerance: float) -> CandidateResult:
    available = [candidate for candidate in evaluated if candidate.eligible and candidate.status == "available"]
    if not available:
        raise FileNotFoundError("No coverage-sufficient OOF-evaluated candidates were found.")
    ranked = sorted(available, key=lambda c: (float("inf") if c.rmse is None else c.rmse))
    best_rmse = float(ranked[0].rmse)
    tied = [candidate for candidate in ranked if candidate.rmse is not None and candidate.rmse <= best_rmse + tie_rmse_tolerance]
    return min(
        tied,
        key=lambda c: (
            float("inf") if c.worst_well_rmse is None else c.worst_well_rmse,
            float("inf") if c.degraded_wells is None else c.degraded_wells,
            float("inf") if c.p95_abs_error is None else c.p95_abs_error,
        ),
    )


def format_data_version(data_version: dict[str, Any]) -> dict[str, object]:
    keys = ["zip_sha256", "raw_file_count", "train_well_count", "test_well_count", "sample_submission_rows", "created_at"]
    return {key: data_version.get(key) for key in keys if key in data_version}


def result_table(results: list[CandidateResult]) -> pd.DataFrame:
    records = [candidate.to_record() for candidate in results]
    if not records:
        return pd.DataFrame()
    columns = [
        "name",
        "kind",
        "status",
        "eligible",
        "reason",
        "rmse",
        "common_rmse",
        "rows",
        "wells",
        "coverage_vs_baseline_rows",
        "coverage_vs_baseline_wells",
        "worst_well_rmse",
        "degraded_wells",
        "p95_abs_error",
        "version_status",
        "version_reason",
        "duplicate_ids_dropped",
        "oof_path",
        "submission_path",
    ]
    return pd.DataFrame(records)[columns]


def write_outputs(
    selected: CandidateResult,
    evaluated: list[CandidateResult],
    skipped: list[CandidateResult],
    per_well: dict[str, pd.DataFrame],
    common_info: dict[str, object],
    current_version: dict[str, Any],
    tie_rmse_tolerance: float,
    coverage_threshold: float,
) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    available = [candidate for candidate in evaluated if candidate.eligible and candidate.status == "available"]
    baseline_ref = next((candidate for candidate in evaluated if candidate.name == "baseline"), None)
    payload = {
        "current_data_version": format_data_version(current_version),
        "baseline_reference": {
            "rows": baseline_ref.rows if baseline_ref else None,
            "wells": baseline_ref.wells if baseline_ref else None,
            "path": baseline_ref.oof_path if baseline_ref else str(OUTPUT_DIR / "baseline_predictions_train_hidden.csv"),
            "coverage_threshold": coverage_threshold,
        },
        "selected_candidate": selected.to_record(),
        "selection_rule": {
            "primary": "lowest full-coverage OOF RMSE among candidates passing coverage and version checks",
            "coverage_threshold_rows": coverage_threshold,
            "coverage_threshold_wells": coverage_threshold,
            "tie_breakers": ["lowest worst_well_rmse", "fewest degraded_wells", "lowest p95_abs_error"],
            "tie_rmse_tolerance": tie_rmse_tolerance,
            "common_coverage_used_for_selection": False,
        },
        "common_comparison": common_info,
        "available_candidates": [candidate.to_record() for candidate in available],
        "skipped_candidates": [candidate.to_record() for candidate in skipped],
        "evaluated_candidates": [candidate.to_record() for candidate in evaluated],
    }
    SELECTION_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    evaluated_df = result_table(evaluated)
    available_df = result_table(available)
    skipped_df = result_table(skipped)
    selected_per_well = per_well.get(selected.name, pd.DataFrame()).copy()
    if len(selected_per_well):
        selected_per_well = selected_per_well.head(20)

    lines = [
        "# Candidate Selection Report",
        "",
        "## Selection",
        "",
        f"- Selected candidate: `{selected.name}`",
        f"- Selected OOF RMSE: `{selected.rmse}`",
        f"- Selection basis: full candidate OOF RMSE after coverage/version filtering.",
        f"- Tie tolerance: `{tie_rmse_tolerance}`",
        f"- Submission source: `{selected.submission_path}`",
        "",
        "## Baseline Reference",
        "",
        f"- Baseline rows: `{baseline_ref.rows if baseline_ref else None}`",
        f"- Baseline wells: `{baseline_ref.wells if baseline_ref else None}`",
        f"- Required coverage: rows >= `{coverage_threshold:.2f}`, wells >= `{coverage_threshold:.2f}`",
        f"- Current data version: `{json.dumps(format_data_version(current_version), ensure_ascii=False)}`",
        "",
        "## Common Coverage Diagnostic",
        "",
        f"- Enabled: `{common_info.get('enabled')}`",
        f"- Usable for selection: `{common_info.get('usable_for_selection')}`",
        f"- Used for selection: `{common_info.get('used_for_selection')}`",
        f"- Reason: `{common_info.get('reason')}`",
        f"- Common rows: `{common_info.get('common_rows')}`",
        f"- Common wells: `{common_info.get('common_wells')}`",
        f"- Coverage vs baseline rows: `{common_info.get('coverage_vs_baseline_rows')}`",
        f"- Coverage vs baseline wells: `{common_info.get('coverage_vs_baseline_wells')}`",
        "",
        "## Available Candidates",
        "",
        markdown_table(available_df.round(6), index=False) if len(available_df) else "_No available candidates_",
        "",
        "## Evaluated Candidates",
        "",
        markdown_table(evaluated_df.round(6), index=False) if len(evaluated_df) else "_No evaluated candidates_",
        "",
        "## Skipped Or Insufficient Candidates",
        "",
        markdown_table(skipped_df.round(6).fillna(""), index=False) if len(skipped_df) else "_No skipped candidates_",
        "",
        "## Selected Candidate Worst Wells",
        "",
        markdown_table(selected_per_well.round(6), index=False) if len(selected_per_well) else "_No per-well table available_",
        "",
    ]
    SELECTION_REPORT.write_text("\n".join(lines), encoding="utf-8")


def select_best_candidate(
    tie_rmse_tolerance: float = 0.01,
    coverage_threshold: float = DEFAULT_COVERAGE_THRESHOLD,
    write_report: bool = False,
) -> CandidateResult:
    evaluated, skipped, per_well, common_info, current_version = collect_candidates(coverage_threshold=coverage_threshold)
    selected = choose_candidate(evaluated, tie_rmse_tolerance)
    if write_report:
        write_outputs(selected, evaluated, skipped, per_well, common_info, current_version, tie_rmse_tolerance, coverage_threshold)
    return selected


def export_selected_submission(selected: CandidateResult, output_path: Path) -> None:
    sample = load_sample_submission()[["id"]].copy()
    submission = load_submission_like(Path(selected.submission_path), sample=sample)
    output_path.parent.mkdir(exist_ok=True)
    submission.to_csv(output_path, index=False)


def main() -> int:
    parser = argparse.ArgumentParser(description="Select the best validated submission candidate by OOF CV.")
    parser.add_argument("--dry-run", action="store_true", help="Write selection report/json but do not export submission.csv.")
    parser.add_argument("--export-submission", action="store_true", help="Export the selected candidate to --output.")
    parser.add_argument("--output", type=Path, default=ROOT / "submission.csv")
    parser.add_argument("--tie-rmse-tolerance", type=float, default=0.01)
    parser.add_argument("--coverage-threshold", type=float, default=DEFAULT_COVERAGE_THRESHOLD)
    args = parser.parse_args()

    evaluated, skipped, per_well, common_info, current_version = collect_candidates(coverage_threshold=args.coverage_threshold)
    selected = choose_candidate(evaluated, args.tie_rmse_tolerance)
    write_outputs(selected, evaluated, skipped, per_well, common_info, current_version, args.tie_rmse_tolerance, args.coverage_threshold)
    if args.export_submission and not args.dry_run:
        export_selected_submission(selected, args.output)
    print(f"Selected {selected.name}: rmse={selected.rmse}, rows={selected.rows}, wells={selected.wells}, source={selected.submission_path}")
    if args.export_submission and not args.dry_run:
        print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
