#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_RAW = ROOT / "data" / "raw"
TRAIN_DIR = DATA_RAW / "train"
TEST_DIR = DATA_RAW / "test"
REPORT_PATH = ROOT / "reports" / "server_part2_preflight_report.md"

REQUIRED_PACKAGES = {
    "joblib": "joblib",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "pandas": "pandas",
    "pyarrow": "pyarrow",
    "sklearn": "scikit-learn",
    "tabulate": "tabulate",
}

MIN_FREE_GB = 25
RECOMMENDED_FREE_GB = 80
RECOMMENDED_RAM_GB = 64


def check(condition: bool, name: str, evidence: str = "", critical: bool = True) -> dict[str, object]:
    return {
        "name": name,
        "status": "PASS" if condition else ("FAIL" if critical else "WARN"),
        "critical": critical,
        "evidence": evidence,
    }


def count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("rb") as handle:
        return max(0, sum(chunk.count(b"\n") for chunk in iter(lambda: handle.read(1024 * 1024), b"")) - 1)


def run_text(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def total_ram_gb() -> float | None:
    if Path("/proc/meminfo").exists():
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) / 1024 / 1024
    if platform.system() == "Darwin":
        value = run_text(["sysctl", "-n", "hw.memsize"])
        return int(value) / 1024**3 if value.isdigit() else None
    if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names and "SC_PAGE_SIZE" in os.sysconf_names:
        try:
            return os.sysconf("SC_PHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") / 1024**3
        except Exception:
            return None
    return None


def package_status() -> list[dict[str, object]]:
    rows = []
    for module_name, display_name in REQUIRED_PACKAGES.items():
        rows.append(
            check(
                importlib.util.find_spec(module_name) is not None,
                f"python package available: {display_name}",
                critical=True,
            )
        )
    return rows


def data_status() -> list[dict[str, object]]:
    train_horizontal = sorted(TRAIN_DIR.glob("*__horizontal_well.csv")) if TRAIN_DIR.exists() else []
    test_horizontal = sorted(TEST_DIR.glob("*__horizontal_well.csv")) if TEST_DIR.exists() else []
    sample_rows = count_lines(DATA_RAW / "sample_submission.csv")
    return [
        check(DATA_RAW.exists(), "data/raw directory exists", str(DATA_RAW), critical=True),
        check(TRAIN_DIR.exists(), "data/raw/train directory exists", str(TRAIN_DIR), critical=True),
        check(TEST_DIR.exists(), "data/raw/test directory exists", str(TEST_DIR), critical=True),
        check((DATA_RAW / "sample_submission.csv").exists(), "sample_submission.csv exists", critical=True),
        check((DATA_RAW / "AI_wellbore_geology_prediction_task_en.pptx").exists(), "task PPTX exists", critical=False),
        check(len(train_horizontal) == 773, "train horizontal well file count is 773", str(len(train_horizontal)), critical=True),
        check(len(test_horizontal) == 3, "test horizontal well file count is 3", str(len(test_horizontal)), critical=True),
        check(sample_rows == 14151, "sample_submission row count is 14151", str(sample_rows), critical=True),
    ]


def system_status() -> list[dict[str, object]]:
    usage = shutil.disk_usage(ROOT)
    free_gb = usage.free / 1024**3
    ram_gb = total_ram_gb()
    python_in_venv = sys.prefix != sys.base_prefix or Path(sys.prefix).name in {".venv", "venv"}
    rows = [
        check(free_gb >= MIN_FREE_GB, "free disk is at least 25 GB", f"{free_gb:.1f} GB", critical=True),
        check(free_gb >= RECOMMENDED_FREE_GB, "free disk recommended at least 80 GB", f"{free_gb:.1f} GB", critical=False),
        check(python_in_venv, "running inside a project or conda environment", sys.prefix, critical=False),
    ]
    if ram_gb is None:
        rows.append(check(False, "RAM amount can be detected", "unknown", critical=False))
    else:
        rows.append(check(ram_gb >= RECOMMENDED_RAM_GB, "RAM recommended at least 64 GB", f"{ram_gb:.1f} GB", critical=False))
    return rows


def git_status() -> list[dict[str, object]]:
    branch = run_text(["git", "branch", "--show-current"])
    head = run_text(["git", "rev-parse", "--short", "HEAD"])
    remote = run_text(["git", "remote", "-v"]).replace("\n", " | ")
    dirty = run_text(["git", "status", "--short"])
    return [
        check(bool(branch), "git branch is detectable", branch or "unknown", critical=False),
        check(bool(head), "git commit is detectable", head or "unknown", critical=False),
        check("git@github.com" in remote or "github.com" in remote, "github remote is configured", remote or "unknown", critical=False),
        check(dirty == "", "worktree has no uncommitted tracked changes", "clean" if dirty == "" else dirty, critical=False),
    ]


def write_report(rows: list[dict[str, object]]) -> None:
    REPORT_PATH.parent.mkdir(exist_ok=True)
    failed = [row for row in rows if row["status"] == "FAIL"]
    warned = [row for row in rows if row["status"] == "WARN"]
    lines = [
        "# Server Part 2 Preflight Report",
        "",
        f"- Created at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Python: `{sys.version.split()[0]}`",
        f"- Platform: `{platform.platform()}`",
        f"- Checks: {len(rows)}",
        f"- Failures: {len(failed)}",
        f"- Warnings: {len(warned)}",
        "",
        "## Checks",
        "",
        "| Status | Check | Evidence | Critical |",
        "|---|---|---|---|",
    ]
    for row in rows:
        evidence = str(row.get("evidence", "")).replace("|", "\\|")
        lines.append(f"| {row['status']} | {row['name']} | {evidence} | {row['critical']} |")
    lines.extend(["", "## Result", "", "PASS" if not failed else "FAIL", ""])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check whether a server is ready to run ROGII Part 2 full training.")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = parser.parse_args()

    rows = []
    rows.extend(system_status())
    rows.extend(package_status())
    rows.extend(data_status())
    rows.extend(git_status())
    write_report(rows)

    failures = [row for row in rows if row["status"] == "FAIL"]
    warnings = [row for row in rows if row["status"] == "WARN"]
    print(f"Wrote {REPORT_PATH}")
    print(f"checks={len(rows)} failures={len(failures)} warnings={len(warnings)}")
    if failures or (args.strict and warnings):
        print("Preflight did not pass. Inspect reports/server_part2_preflight_report.md.")
        return 1
    print("Preflight passed. Warnings are allowed unless --strict is used.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
