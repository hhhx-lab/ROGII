#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path


REQUIRED_MEMBERS = [
    "PART2_SERVER_OUTPUT_MANIFEST.json",
    "models/residual_geometry_config.json",
    "models/residual_geometry_feature_list.txt",
    "models/residual_geometry_hgb.pkl",
    "outputs/residual_geometry_cv_by_well.csv",
    "outputs/residual_geometry_multimask_overall.csv",
    "outputs/residual_geometry_oof.csv",
    "outputs/residual_geometry_test_predictions.csv",
    "reports/part2_completion_audit.md",
    "reports/residual_geometry_cv_report.md",
    "reports/residual_geometry_multimask_report.md",
    "submissions/geometry_residual_submission.csv",
]


def safe_extract(tar: tarfile.TarFile, destination: Path) -> None:
    destination = destination.resolve()
    for member in tar.getmembers():
        target = (destination / member.name).resolve()
        if destination not in target.parents and target != destination:
            raise RuntimeError(f"Unsafe archive member path: {member.name}")
    tar.extractall(destination)


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect a returned Part 2 server output package.")
    parser.add_argument("package", type=Path, help="Path to part2_server_outputs_*.tar.gz")
    parser.add_argument("--extract-to", type=Path, default=None, help="Optional directory to extract into after inspection passes.")
    args = parser.parse_args()

    if not args.package.exists():
        print(f"Package does not exist: {args.package}")
        return 1

    archive_hash = sha256_file(args.package)
    with tarfile.open(args.package, "r:gz") as tar:
        members = {member.name: member for member in tar.getmembers()}
        missing = [name for name in REQUIRED_MEMBERS if name not in members]
        if "PART2_SERVER_OUTPUT_MANIFEST.json" in members:
            manifest_file = tar.extractfile("PART2_SERVER_OUTPUT_MANIFEST.json")
            manifest = json.loads(manifest_file.read().decode("utf-8")) if manifest_file else {}
        else:
            manifest = {}

        print(f"archive={args.package}")
        print(f"archive_sha256={archive_hash}")
        print(f"manifest_file_count={manifest.get('file_count', 'unknown')}")
        print(f"manifest_total_bytes={manifest.get('total_bytes', 'unknown')}")
        print(f"missing_required_members={len(missing)}")
        for name in missing:
            print(f"- missing: {name}")

        if missing:
            print("Inspection failed.")
            return 1

        if args.extract_to is not None:
            args.extract_to.mkdir(parents=True, exist_ok=True)
            safe_extract(tar, args.extract_to)
            print(f"Extracted to {args.extract_to}")

    print("Inspection passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
