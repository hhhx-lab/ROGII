#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
LOG_DIR = REPORT_DIR / "server_part2_full_run_logs"
SUMMARY_MD = REPORT_DIR / "server_part2_full_run_summary.md"
SUMMARY_JSON = REPORT_DIR / "server_part2_full_run_summary.json"


def command_string(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_step(name: str, command: list[str], env: dict[str, str], log_path: Path, dry_run: bool = False) -> dict[str, object]:
    print(f"\n=== {name} ===")
    print(command_string(command))
    start = time.time()
    if dry_run:
        return {"name": name, "command": command, "log": str(log_path.relative_to(ROOT)), "returncode": 0, "seconds": 0.0, "dry_run": True}

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"# {name}\n")
        log.write(f"$ {command_string(command)}\n\n")
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="")
            log.write(line)
        returncode = process.wait()
    seconds = time.time() - start
    result = {"name": name, "command": command, "log": str(log_path.relative_to(ROOT)), "returncode": returncode, "seconds": seconds, "dry_run": False}
    if returncode != 0:
        print(f"Step failed: {name}, returncode={returncode}")
    return result


def build_steps(args: argparse.Namespace) -> list[tuple[str, list[str], dict[str, str]]]:
    py = sys.executable
    residual_train_cmd = [
        py,
        "scripts/train_residual_model.py",
        "--spec",
        args.residual_spec,
        "--max-rows-per-well",
        str(args.train_rows_per_well),
        "--max-iter",
        str(args.max_iter),
        "--learning-rate",
        str(args.learning_rate),
        "--max-leaf-nodes",
        str(args.max_leaf_nodes),
        "--min-samples-leaf",
        str(args.min_samples_leaf),
        "--l2-regularization",
        str(args.l2),
        "--min-fit-fraction",
        str(args.min_fit_fraction),
    ]
    if args.require_xgboost:
        residual_train_cmd.append("--require-xgboost")

    steps: list[tuple[str, list[str], dict[str, str]]] = [
        ("preflight", [py, "scripts/server_part2_preflight.py"], {}),
        ("data_contract", [py, "scripts/check_data_contract.py"], {}),
    ]
    if not args.skip_part1_baseline:
        steps.append(("part1_baseline_cv", [py, "scripts/evaluate_baseline_cv.py"], {}))
    steps.append(("make_cv_splits", [py, "scripts/make_cv_splits.py"], {}))
    if not args.skip_baseline_multimask:
        steps.append(("baseline_multimask", [py, "scripts/evaluate_baseline_multimask.py"], {}))
    steps.extend(
        [
            ("part2_baseline_features", [py, "scripts/build_baseline_features.py"], {}),
            ("part2_geometry_features", [py, "scripts/build_geometry_features.py"], {}),
            (
                "part2_full_residual_training",
                residual_train_cmd,
                {},
            ),
        ]
    )
    if args.residual_spec == "geometry":
        steps.append(("part2_cv_reports", [py, "scripts/evaluate_model_cv.py"], {}))
    if args.residual_spec == "geometry" and not args.skip_residual_multimask:
        steps.append(
            (
                "part2_full_residual_multimask",
                [py, "scripts/evaluate_residual_multimask.py"],
                {
                    "ROGII_PART2_MULTIMASK_TRAIN_ROWS_PER_WELL": str(args.multimask_train_rows_per_well),
                    "ROGII_PART2_MULTIMASK_MAX_ITER": str(args.multimask_max_iter),
                },
            )
    )
    if args.with_gated_pipeline:
        if args.residual_spec != "geometry":
            geometry_train_cmd = [
                py,
                "scripts/train_residual_model.py",
                "--spec",
                "geometry",
                "--max-rows-per-well",
                str(args.train_rows_per_well),
                "--max-iter",
                str(args.max_iter),
                "--min-fit-fraction",
                str(args.min_fit_fraction),
            ]
            steps.append(("part2_geometry_residual_training", geometry_train_cmd, {}))
        steps.extend(
            [
                ("part2_gated_geometry", [py, "scripts/build_gated_geometry.py"], {}),
                ("part2_leftover_targets", [py, "scripts/build_leftover_targets.py"], {}),
            ]
        )
        if args.with_xgb_leftover:
            leftover_train_cmd = [
                py,
                "scripts/train_residual_model.py",
                "--spec",
                "xgb_leftover",
                "--max-rows-per-well",
                str(args.train_rows_per_well),
                "--max-iter",
                str(args.max_iter),
                "--learning-rate",
                str(args.learning_rate),
                "--max-leaf-nodes",
                str(args.max_leaf_nodes),
                "--min-samples-leaf",
                str(args.min_samples_leaf),
                "--l2-regularization",
                str(args.l2),
                "--min-fit-fraction",
                str(args.min_fit_fraction),
            ]
            if args.require_xgboost:
                leftover_train_cmd.append("--require-xgboost")
            steps.extend(
                [
                    ("part2_xgb_leftover_training", leftover_train_cmd, {}),
                    ("part2_gated_stack", [py, "scripts/build_gated_stack.py"], {}),
                ]
            )
    steps.append(("part2_completion_audit", [py, "scripts/validate_part2_outputs.py", "--primary-spec", args.residual_spec], {}))
    return steps


def build_package_step(args: argparse.Namespace) -> tuple[str, list[str], dict[str, str]]:
    package_cmd = [sys.executable, "scripts/package_part2_server_outputs.py"]
    if args.include_features_in_package:
        package_cmd.append("--include-features")
    return "package_part2_outputs", package_cmd, {}


def write_summary(results: list[dict[str, object]], started_at: str, finished_at: str, failed_step: str | None) -> None:
    SUMMARY_JSON.write_text(
        json.dumps(
            {
                "started_at": started_at,
                "finished_at": finished_at,
                "failed_step": failed_step,
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Server Part 2 Full Run Summary",
        "",
        f"- Started at: `{started_at}`",
        f"- Finished at: `{finished_at}`",
        f"- Result: `{'PASS' if failed_step is None else 'FAIL'}`",
        f"- Failed step: `{failed_step or ''}`",
        "",
        "## Steps",
        "",
        "| Step | Return code | Seconds | Log |",
        "|---|---:|---:|---|",
    ]
    for result in results:
        lines.append(f"| {result['name']} | {result['returncode']} | {float(result['seconds']):.1f} | `{result['log']}` |")
    lines.append("")
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full Part 2 server pipeline from data checks to package creation.")
    parser.add_argument(
        "--residual-spec",
        choices=["geometry", "xgb", "xgb_leftover"],
        default="geometry",
        help="Leaderboard full run defaults to geometry SGD residual; xgb is a direct-residual control; xgb_leftover is the geometry stack layer.",
    )
    parser.add_argument(
        "--with-gated-pipeline",
        action="store_true",
        default=True,
        help="Run gated_geometry and leftover-target generation after geometry residual training.",
    )
    parser.add_argument(
        "--without-gated-pipeline",
        action="store_false",
        dest="with_gated_pipeline",
        help="Skip gater and leftover stack steps.",
    )
    parser.add_argument(
        "--with-xgb-leftover",
        action="store_true",
        default=True,
        help="Train xgb_leftover and build gated_geometry_plus_xgb_leftover when the gated pipeline is enabled.",
    )
    parser.add_argument(
        "--without-xgb-leftover",
        action="store_false",
        dest="with_xgb_leftover",
        help="Skip xgb_leftover training and gated stack build.",
    )
    parser.add_argument("--train-rows-per-well", type=int, default=0, help="0 means use all rows per well for residual training.")
    parser.add_argument("--min-fit-fraction", type=float, default=0.95)
    parser.add_argument("--max-iter", type=int, default=500, help="HistGradientBoosting max_iter for full residual training.")
    parser.add_argument("--max-leaf-nodes", type=int, default=31)
    parser.add_argument("--min-samples-leaf", type=int, default=50)
    parser.add_argument("--l2", type=float, default=0.05)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--require-xgboost", action="store_true", default=True, help="Fail if xgboost is unavailable instead of using the fallback backend.")
    parser.add_argument("--allow-xgboost-fallback", action="store_false", dest="require_xgboost", help="Allow sklearn HistGradientBoosting fallback for experiments.")
    parser.add_argument("--multimask-train-rows-per-well", type=int, default=0, help="0 means use all rows per well for residual multi-mask validation.")
    parser.add_argument("--multimask-max-iter", type=int, default=500)
    parser.add_argument("--skip-part1-baseline", action="store_true", help="Skip evaluate_baseline_cv.py if required Part 1 outputs already exist.")
    parser.add_argument("--skip-baseline-multimask", action="store_true")
    parser.add_argument("--skip-residual-multimask", action="store_true")
    parser.add_argument("--skip-package", action="store_true")
    parser.add_argument("--include-features-in-package", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Print planned steps without running them.")
    args = parser.parse_args()

    REPORT_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    started_at = datetime.now(timezone.utc).isoformat()
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base_env = os.environ.copy()
    results = []
    failed_step = None

    steps = build_steps(args)
    for index, (name, command, extra_env) in enumerate(steps, start=1):
        env = base_env.copy()
        env.update(extra_env)
        log_path = LOG_DIR / f"{run_stamp}_{index:02d}_{name}.log"
        result = run_step(name, command, env, log_path, dry_run=args.dry_run)
        results.append(result)
        if int(result["returncode"]) != 0:
            failed_step = name
            break

    finished_at = datetime.now(timezone.utc).isoformat()
    write_summary(results, started_at, finished_at, failed_step)

    if failed_step is None and not args.skip_package:
        name, command, extra_env = build_package_step(args)
        env = base_env.copy()
        env.update(extra_env)
        log_path = LOG_DIR / f"{run_stamp}_{len(results) + 1:02d}_{name}.log"
        result = run_step(name, command, env, log_path, dry_run=args.dry_run)
        results.append(result)
        if int(result["returncode"]) != 0:
            failed_step = name
        finished_at = datetime.now(timezone.utc).isoformat()
        write_summary(results, started_at, finished_at, failed_step)

    print(f"Wrote {SUMMARY_MD}")
    print(f"Wrote {SUMMARY_JSON}")
    return 1 if failed_step else 0


if __name__ == "__main__":
    raise SystemExit(main())
