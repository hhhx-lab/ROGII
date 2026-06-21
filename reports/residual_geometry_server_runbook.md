# Residual Geometry Server Runbook

This is the compact technical companion to `docs/operations/part2_server_full_run_guide.md`.

## Purpose

- Re-run Part 2 on a server from a clean workspace
- Keep the full-row training path reproducible
- Capture the final outputs that will be packaged and brought back locally

## Canonical Commands

```bash
.venv/bin/python scripts/server_part2_preflight.py
.venv/bin/python scripts/run_part2_full_server.py --dry-run
.venv/bin/python scripts/run_part2_full_server.py
.venv/bin/python scripts/validate_part2_outputs.py
.venv/bin/python scripts/package_part2_server_outputs.py
.venv/bin/python scripts/inspect_part2_server_package.py packages/part2_server_outputs_YYYYMMDD_HHMMSS.tar.gz
```

For a smaller smoke run:

```bash
.venv/bin/python scripts/run_part2_full_server.py \
  --train-rows-per-well 1200 \
  --max-iter 300 \
  --multimask-train-rows-per-well 1200 \
  --multimask-max-iter 300
```

## Environment

- Use a project-local `.venv`
- Do not mix in system Python, Homebrew Python, Conda, or `sudo pip`
- Keep raw Kaggle data under `data/raw/`

## Output Contract

Expected final artifacts:

- `models/residual_geometry*`
- `outputs/residual_geometry*`
- `reports/residual_geometry*`
- `reports/part2_completion_audit.md`
- `submissions/geometry_residual_submission.csv`
- `packages/part2_server_outputs_*.tar.gz`
- `packages/part2_server_outputs_*.tar.gz.sha256`

## Readiness Checks

- `checks=34 failures=0` from `scripts/validate_part2_outputs.py`
- server summary markdown/json created
- package inspection passes
- old Part 2 artifacts are not being reused by accident

## Notes

- Part 1 does not need a rerun.
- If Part 2 reports conflict with each other, trust the server rerun that was produced from the clean workspace.
- If the server is memory constrained, lower `--train-rows-per-well` and `--multimask-train-rows-per-well` for a smoke run first, then return to full-row.
