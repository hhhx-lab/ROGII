#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

from data_paths import load_sample_submission, resolve_competition_root


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
LOG_DIR = REPORT_DIR / "server_part2_full_run_logs"
SUMMARY_MD = REPORT_DIR / "server_part2_full_run_summary.md"
SUMMARY_JSON = REPORT_DIR / "server_part2_full_run_summary.json"
RUN_CONFIG_MD = REPORT_DIR / "server_part2_full_run_config.md"
RUN_CONFIG_JSON = REPORT_DIR / "server_part2_full_run_config.json"
RUN_CONFIG_DIR = REPORT_DIR / "server_part2_full_run_configs"


def command_string(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def run_text(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def json_safe(value: object) -> object:
    if is_dataclass(value):
        return json_safe(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def path_status(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "file_count": len(list(path.glob("*"))) if path.exists() and path.is_dir() else None,
    }


def load_data_version() -> dict[str, object] | None:
    path = ROOT / "outputs" / "data_version.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"read_error": str(exc)}


def data_snapshot() -> dict[str, object]:
    data_root = resolve_competition_root()
    train_dir = data_root / "train"
    test_dir = data_root / "test"
    try:
        sample_rows: int | None = len(load_sample_submission())
        sample_error = ""
    except Exception as exc:
        sample_rows = None
        sample_error = str(exc)
    return {
        "competition_root": str(data_root),
        "train_dir": path_status(train_dir),
        "test_dir": path_status(test_dir),
        "train_horizontal_files": len(list(train_dir.glob("*__horizontal_well.csv"))) if train_dir.exists() else 0,
        "test_horizontal_files": len(list(test_dir.glob("*__horizontal_well.csv"))) if test_dir.exists() else 0,
        "sample_submission_rows": sample_rows,
        "sample_submission_error": sample_error,
        "data_version": load_data_version(),
    }


def git_snapshot() -> dict[str, object]:
    return {
        "branch": run_text(["git", "branch", "--show-current"]),
        "head": run_text(["git", "rev-parse", "HEAD"]),
        "head_short": run_text(["git", "rev-parse", "--short", "HEAD"]),
        "remote": run_text(["git", "remote", "-v"]).splitlines(),
        "status_short": run_text(["git", "status", "--short", "--branch"]),
    }


def planned_step_rows(steps: list[tuple[str, list[str], dict[str, str]]], run_stamp: str) -> list[dict[str, object]]:
    rows = []
    for index, (name, command, extra_env) in enumerate(steps, start=1):
        rows.append(
            {
                "index": index,
                "name": name,
                "command": command,
                "command_string": command_string(command),
                "extra_env": extra_env,
                "log": str((LOG_DIR / f"{run_stamp}_{index:02d}_{name}.log").relative_to(ROOT)),
            }
        )
    return rows


def build_run_config(
    args: argparse.Namespace,
    started_at: str,
    run_stamp: str,
    steps: list[tuple[str, list[str], dict[str, str]]],
    results: list[dict[str, object]] | None = None,
    finished_at: str | None = None,
    failed_step: str | None = None,
) -> dict[str, object]:
    run_specific_json = RUN_CONFIG_DIR / f"{run_stamp}.json"
    run_specific_md = RUN_CONFIG_DIR / f"{run_stamp}.md"
    return {
        "schema_version": 1,
        "run_id": run_stamp,
        "started_at": started_at,
        "finished_at": finished_at,
        "failed_step": failed_step,
        "dry_run": bool(args.dry_run),
        "root": str(ROOT),
        "argv": sys.argv,
        "python": {
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "platform": platform.platform(),
        },
        "git": git_snapshot(),
        "data": data_snapshot(),
        "args": vars(args),
        "training_policy": {
            "residual_spec": args.residual_spec,
            "full_row_training": args.train_rows_per_well == 0,
            "train_rows_per_well": args.train_rows_per_well,
            "min_fit_fraction": args.min_fit_fraction,
            "require_xgboost": args.require_xgboost,
            "with_gated_pipeline": args.with_gated_pipeline,
            "with_learned_gater": args.with_learned_gater,
            "learned_gater_model": args.learned_gater_model,
            "learned_gater_snap_alpha_grid": args.learned_gater_snap_alpha_grid,
            "with_xgb_leftover": args.with_xgb_leftover,
            "allow_oracle_auto_selection": args.allow_oracle_auto_selection,
            "candidate_eligibility_policy": "oracle/diagnostic candidates are excluded unless --allow-oracle-auto-selection is set",
        },
        "planned_steps": planned_step_rows(steps, run_stamp),
        "results": results or [],
        "artifact_paths": {
            "latest_json": str(RUN_CONFIG_JSON.relative_to(ROOT)),
            "latest_md": str(RUN_CONFIG_MD.relative_to(ROOT)),
            "run_json": str(run_specific_json.relative_to(ROOT)),
            "run_md": str(run_specific_md.relative_to(ROOT)),
            "summary_json": str(SUMMARY_JSON.relative_to(ROOT)),
            "summary_md": str(SUMMARY_MD.relative_to(ROOT)),
            "log_dir": str(LOG_DIR.relative_to(ROOT)),
        },
    }


def write_run_config(config: dict[str, object]) -> None:
    RUN_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    latest_json = RUN_CONFIG_JSON
    latest_md = RUN_CONFIG_MD
    run_json = ROOT / str(config["artifact_paths"]["run_json"])
    run_md = ROOT / str(config["artifact_paths"]["run_md"])
    payload = json.dumps(json_safe(config), indent=2, ensure_ascii=False) + "\n"
    latest_json.write_text(payload, encoding="utf-8")
    run_json.write_text(payload, encoding="utf-8")

    git = config.get("git", {})
    data = config.get("data", {})
    training = config.get("training_policy", {})
    lines = [
        "# Server Part 2 Full Run Config",
        "",
        f"- Run id: `{config['run_id']}`",
        f"- Started at: `{config['started_at']}`",
        f"- Finished at: `{config.get('finished_at') or ''}`",
        f"- Dry run: `{config['dry_run']}`",
        f"- Failed step: `{config.get('failed_step') or ''}`",
        f"- Git branch: `{git.get('branch', '')}`",
        f"- Git HEAD: `{git.get('head_short', '')}`",
        f"- Data root: `{data.get('competition_root', '')}`",
        f"- Train wells/files: `{data.get('train_horizontal_files', '')}`",
        f"- Test wells/files: `{data.get('test_horizontal_files', '')}`",
        f"- Sample rows: `{data.get('sample_submission_rows', '')}`",
        "",
        "## Training Policy",
        "",
        f"- residual_spec: `{training.get('residual_spec')}`",
        f"- full_row_training: `{training.get('full_row_training')}`",
        f"- train_rows_per_well: `{training.get('train_rows_per_well')}`",
        f"- min_fit_fraction: `{training.get('min_fit_fraction')}`",
        f"- require_xgboost: `{training.get('require_xgboost')}`",
        f"- with_gated_pipeline: `{training.get('with_gated_pipeline')}`",
        f"- with_learned_gater: `{training.get('with_learned_gater')}`",
        f"- learned_gater_model: `{training.get('learned_gater_model')}`",
        f"- learned_gater_snap_alpha_grid: `{training.get('learned_gater_snap_alpha_grid')}`",
        f"- with_xgb_leftover: `{training.get('with_xgb_leftover')}`",
        f"- allow_oracle_auto_selection: `{training.get('allow_oracle_auto_selection')}`",
        f"- candidate_eligibility_policy: `{training.get('candidate_eligibility_policy')}`",
        "",
        "## Planned Steps",
        "",
        "| # | Step | Command | Log |",
        "|---:|---|---|---|",
    ]
    for step in config.get("planned_steps", []):
        command = str(step["command_string"]).replace("|", "\\|")
        lines.append(f"| {step['index']} | {step['name']} | `{command}` | `{step['log']}` |")
    if config.get("results"):
        lines.extend(["", "## Results", "", "| Step | Return code | Seconds |", "|---|---:|---:|"])
        for result in config["results"]:
            lines.append(f"| {result['name']} | {result['returncode']} | {float(result['seconds']):.1f} |")
    lines.extend(
        [
            "",
            "## Full JSON",
            "",
            f"- Latest: `{latest_json.relative_to(ROOT)}`",
            f"- This run: `{run_json.relative_to(ROOT)}`",
            "",
        ]
    )
    text = "\n".join(lines)
    latest_md.write_text(text, encoding="utf-8")
    run_md.write_text(text, encoding="utf-8")


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
        steps.append(("part3_diagnostics", [py, "scripts/build_part3_diagnostics.py"], {}))
        steps.extend(
            [
                ("part2_gated_geometry", [py, "scripts/build_gated_geometry.py"], {}),
            ]
        )
        if args.with_learned_gater:
            learned_gater_cmd = [
                py,
                "scripts/train_learned_gater.py",
                "--model",
                args.learned_gater_model,
            ]
            if args.learned_gater_snap_alpha_grid:
                learned_gater_cmd.append("--snap-alpha-grid")
            steps.append(("part2_learned_gater", learned_gater_cmd, {}))
        steps.append(("part2_leftover_targets", [py, "scripts/build_leftover_targets.py"], {}))
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
    if not args.skip_candidate_selection:
        selection_cmd = [py, "scripts/select_submission_candidate.py", "--dry-run"]
        if args.allow_oracle_auto_selection:
            selection_cmd.append("--allow-oracle-candidates")
        steps.append(("candidate_selection", selection_cmd, {}))
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
        help="Full run defaults to geometry residual plus gater; xgb is a direct-residual control; xgb_leftover is the geometry stack layer.",
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
        "--with-learned-gater",
        action="store_true",
        default=True,
        help="Train a fold-safe learned gater after the oracle gated_geometry diagnostic candidate.",
    )
    parser.add_argument(
        "--without-learned-gater",
        action="store_false",
        dest="with_learned_gater",
        help="Skip learned gater training and candidate generation.",
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
    parser.add_argument("--max-iter", type=int, default=500, help="Boosting iteration cap for XGBoost/HGB residual training.")
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
    parser.add_argument(
        "--learned-gater-model",
        choices=["ridge", "elasticnet", "hgb", "random_forest"],
        default="ridge",
        help="Model used for learned gater alpha prediction.",
    )
    parser.add_argument("--learned-gater-snap-alpha-grid", action="store_true")
    parser.add_argument(
        "--allow-oracle-auto-selection",
        action="store_true",
        help="Allow oracle/diagnostic candidates such as gated_geometry in auto selection for experiments.",
    )
    parser.add_argument(
        "--skip-candidate-selection",
        action="store_true",
        help="Skip automatic candidate selection dry-run at the end of the full run.",
    )
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
    planned_steps = list(steps)
    if not args.skip_package:
        planned_steps.append(build_package_step(args))
    run_config = build_run_config(args, started_at, run_stamp, planned_steps)
    write_run_config(run_config)

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
    run_config = build_run_config(args, started_at, run_stamp, planned_steps, results, finished_at, failed_step)
    write_run_config(run_config)

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
        run_config = build_run_config(args, started_at, run_stamp, planned_steps, results, finished_at, failed_step)
        write_run_config(run_config)

    print(f"Wrote {SUMMARY_MD}")
    print(f"Wrote {SUMMARY_JSON}")
    print(f"Wrote {RUN_CONFIG_MD}")
    print(f"Wrote {RUN_CONFIG_JSON}")
    return 1 if failed_step else 0


if __name__ == "__main__":
    raise SystemExit(main())
