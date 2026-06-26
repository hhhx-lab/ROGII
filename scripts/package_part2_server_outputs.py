#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "packages"

REQUIRED_FILES = [
    "models/residual_geometry_config.json",
    "models/residual_geometry_feature_list.txt",
    "models/residual_geometry_hgb.pkl",
    "outputs/data_version.json",
    "outputs/data_contract_summary.csv",
    "outputs/cv_splits.csv",
    "outputs/residual_geometry_alpha_search.csv",
    "outputs/residual_geometry_cv_by_well.csv",
    "outputs/residual_geometry_multimask_by_split.csv",
    "outputs/residual_geometry_multimask_overall.csv",
    "outputs/residual_geometry_oof.csv",
    "outputs/residual_geometry_test_predictions.csv",
    "reports/part2_completion_audit.md",
    "reports/residual_geometry_cv_report.md",
    "reports/residual_geometry_failure_analysis.md",
    "reports/residual_geometry_feature_importance.md",
    "reports/residual_geometry_multimask_report.md",
    "reports/residual_geometry_server_runbook.md",
    "reports/residual_target_report.md",
    "submissions/geometry_residual_submission.csv",
    "docs/plans/02_residual_modeling_progress.md",
]

OPTIONAL_GLOBS = [
    "reports/figures/residual_geometry_best_improved/*.png",
    "reports/figures/residual_geometry_worst_degraded/*.png",
    "reports/server_part2_preflight_report.md",
    "reports/server_part2_full_run_config.md",
    "reports/server_part2_full_run_config.json",
    "reports/server_part2_full_run_configs/*.md",
    "reports/server_part2_full_run_configs/*.json",
    "reports/server_part2_full_run_summary.md",
    "reports/server_part2_full_run_summary.json",
    "reports/server_part2_full_run_logs/*.log",
    "models/learned_gated_geometry_config.json",
    "models/learned_gater_model.pkl",
    "outputs/learned_gated_alpha_by_well.csv",
    "outputs/learned_gated_geometry_cv_by_well.csv",
    "outputs/learned_gated_geometry_test_predictions.csv",
    "reports/learned_gated_geometry_cv_report.md",
    "submissions/learned_gated_geometry_submission.csv",
]

FEATURE_FILES = [
    "features/baseline_features_train.parquet",
    "features/baseline_features_test.parquet",
    "features/geometry_features_train.parquet",
    "features/geometry_features_test.parquet",
    "features/residual_targets.parquet",
]

PART1_LARGE_FILES = [
    "outputs/baseline_predictions_train_hidden.csv",
    "outputs/baseline_cv_by_well.csv",
    "outputs/baseline_multimask_by_split.csv",
    "outputs/baseline_multimask_overall.csv",
]


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_paths(include_features: bool, include_part1_large: bool) -> tuple[list[Path], list[str]]:
    requested = list(REQUIRED_FILES)
    if include_features:
        requested.extend(FEATURE_FILES)
    if include_part1_large:
        requested.extend(PART1_LARGE_FILES)

    paths: list[Path] = []
    missing: list[str] = []
    seen: set[Path] = set()

    for rel in requested:
        path = ROOT / rel
        if path.exists():
            if path not in seen:
                paths.append(path)
                seen.add(path)
        else:
            missing.append(rel)

    for pattern in OPTIONAL_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file() and path not in seen:
                paths.append(path)
                seen.add(path)
    return paths, missing


def package_readme(manifest: dict[str, object]) -> str:
    return "\n".join(
        [
            "# Part 2 Server Output Package",
            "",
            "This archive was produced by `scripts/package_part2_server_outputs.py`.",
            "",
            "## Contents",
            "",
            "- Part 2 model artifacts under `models/`",
            "- Part 2 residual outputs under `outputs/`",
            "- Reports and diagnostic figures under `reports/`",
            "- Submission CSV under `submissions/`",
            "- Progress document under `docs/plans/`",
            "",
            "## Verification",
            "",
            "After copying this archive back, run:",
            "",
            "```bash",
            "python scripts/inspect_part2_server_package.py packages/<this_archive>.tar.gz",
            "```",
            "",
            f"- Package created at: `{manifest['created_at']}`",
            f"- File count: `{manifest['file_count']}`",
            f"- Total bytes before compression: `{manifest['total_bytes']}`",
            "",
        ]
    )


def add_bytes(tar: tarfile.TarFile, arcname: str, data: bytes) -> None:
    info = tarfile.TarInfo(arcname)
    info.size = len(data)
    tar.addfile(info, io.BytesIO(data))


def main() -> int:
    parser = argparse.ArgumentParser(description="Package Part 2 server outputs for transfer back to a workstation.")
    parser.add_argument("--output", type=Path, default=None, help="Output tar.gz path. Defaults to packages/part2_server_outputs_<timestamp>.tar.gz")
    parser.add_argument("--include-features", action="store_true", help="Include generated features/*.parquet files. This makes the archive much larger.")
    parser.add_argument("--include-part1-large", action="store_true", help="Include large Part 1 output files such as baseline_predictions_train_hidden.csv.")
    parser.add_argument("--allow-missing", action="store_true", help="Create the package even when required files are missing.")
    args = parser.parse_args()

    PACKAGE_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = args.output or (PACKAGE_DIR / f"part2_server_outputs_{timestamp}.tar.gz")
    paths, missing = collect_paths(args.include_features, args.include_part1_large)
    if missing and not args.allow_missing:
        print("Missing required files:")
        for rel in missing:
            print(f"- {rel}")
        print("Run Part 2 first, or use --allow-missing for a diagnostic-only package.")
        return 1

    files = []
    total_bytes = 0
    for path in paths:
        rel = path.relative_to(ROOT).as_posix()
        size = path.stat().st_size
        total_bytes += size
        files.append({"path": rel, "size_bytes": size, "sha256": sha256_file(path)})

    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "include_features": args.include_features,
        "include_part1_large": args.include_part1_large,
        "missing_required_files": missing,
        "files": files,
    }

    with tarfile.open(output, "w:gz") as tar:
        for path in paths:
            tar.add(path, arcname=path.relative_to(ROOT).as_posix())
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        add_bytes(tar, "PART2_SERVER_OUTPUT_MANIFEST.json", manifest_bytes)
        add_bytes(tar, "README_SERVER_OUTPUTS.md", package_readme(manifest).encode("utf-8"))

    output_hash = sha256_file(output)
    hash_path = output.with_suffix(output.suffix + ".sha256")
    hash_path.write_text(f"{output_hash}  {output.name}\n", encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Wrote {hash_path}")
    print(f"package_sha256={output_hash}")
    print(f"files={len(files)} total_uncompressed_bytes={total_bytes}")
    if missing:
        print(f"missing_required_files={len(missing)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
