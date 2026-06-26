# Full Inference Artifact Upload Audit

This audit maps `docs/operations/FULL_INFERENCE_GUIDE.md` artifacts to the repository upload decision after the local full inference run on `2026-06-26`.

Data source: parent-folder `data/raw` linked into `ROGII/data/raw` via junction. Training used full-row geometry residual (`--max-rows-per-well 0`), learned gater (`ridge`), and optional `xgb_leftover` stack.

## Submitted In Git

### Code

No script or doc changes in this run. Existing tracked code already covers:

- `scripts/build_gated_geometry.py`
- `scripts/build_gated_stack.py`
- `scripts/build_leftover_targets.py`
- `scripts/train_learned_gater.py`
- updates to `scripts/train_residual_model.py`, `scripts/select_submission_candidate.py`, `scripts/make_submission.py`
- `scripts/run_part2_full_server.py`, `docs/operations/FULL_INFERENCE_GUIDE.md`, `reports/final_model_card.md`

### Small artifacts

- final `submission.csv` (`geometry`, auto-selected)
- candidate submissions under `submissions/`, including new `learned_gated_geometry_submission.csv`
- compact outputs whitelisted in `.gitignore`, including new `learned_gated_alpha_by_well.csv` and `learned_gated_geometry_cv_by_well.csv`
- CV reports, candidate-selection reports, feature-importance CSVs, and diagnostic figures
- model configs and feature lists under `models/*.json` and `models/*.txt`, including new `learned_gated_geometry_config.json`

### Removed from Git in this refresh

These direct `xgb` control artifacts were not regenerated in this run and should be deleted from the repo:

- `models/residual_xgb_config.json`
- `models/residual_xgb_feature_list.txt`
- `reports/residual_xgb_cv_report.md`
- `reports/residual_xgb_feature_importance.csv`
- `submissions/xgb_residual_submission.csv`

## Local-Only Large Artifacts

The following guide artifacts exist locally but were intentionally not pushed because they exceed normal GitHub file limits or are reproducible from scripts:

| path | local size MB | reason |
|---|---:|---|
| `outputs/baseline_predictions_train_hidden.csv` | 217.50 | larger than 100 MiB |
| `features/baseline_features_train.csv` | 1080.07 | larger than 100 MiB |
| `features/residual_targets.csv` | 289.68 | larger than 100 MiB |
| `features/leftover_targets.csv` | 626.13 | larger than 100 MiB; reproducible from `build_leftover_targets.py` |
| `features/geometry_features_train.parquet` | 249.30 | larger than 100 MiB |
| `outputs/residual_geometry_oof.csv` | 879.62 | larger than 100 MiB |
| `outputs/gated_geometry_oof.csv` | 496.21 | larger than 100 MiB |
| `outputs/learned_gated_geometry_oof.csv` | 572.76 | larger than 100 MiB |
| `outputs/residual_xgb_leftover_oof.csv` | 696.28 | larger than 100 MiB |
| `outputs/gated_geometry_plus_xgb_leftover_oof.csv` | 593.26 | larger than 100 MiB |
| `outputs/blend_oof.csv` | 664.57 | larger than 100 MiB |
| `features/gr_features_train.csv` | 3830.91 | larger than 100 MiB |
| `features/typewell_features_train.csv` | 1293.66 | larger than 100 MiB |
| `features/alignment_features_train.csv` | 1291.09 | larger than 100 MiB |
| `models/*.pkl` | ~0.83 each | excluded by `.gitignore`; reproducible from training scripts |
| `archive/runs/` | varies | local cleanup archive only |
| `reports/full_inference_logs/` | varies | run logs only |
| `.venv/` | varies | local environment only |

## Validation Status

- `scripts/check_data_contract.py`: `critical_errors=0`
- `scripts/validate_part2_outputs.py`: `checks=25 failures=0`
- `scripts/validate_submission.py --submission submission.csv`: `rows=14151, columns=id,tvt`
- `scripts/select_submission_candidate.py --dry-run`: selected `geometry`, OOF RMSE `15.6288`
- oracle `gated_geometry` OOF RMSE `13.3807`; excluded from auto submission by policy
- `learned_gated_geometry` OOF RMSE `19.8180`; tracked candidate, not selected
- `xgb_leftover` OOF RMSE `16.8652`; tracked candidate, not selected
- `gated_geometry_plus_xgb_leftover` OOF RMSE `14.3469`; oracle stack diagnostic only, not selected
- Full guide artifacts exist locally under their documented paths.