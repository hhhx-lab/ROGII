# Full Inference Artifact Upload Audit

This audit maps `docs/operations/FULL_INFERENCE_GUIDE.md` artifacts to the repository upload decision after the local full inference and gated-pipeline run.

## Submitted In Git

### Code

- `scripts/build_gated_geometry.py`
- `scripts/build_gated_stack.py`
- `scripts/build_leftover_targets.py`
- updates to `scripts/train_residual_model.py`, `scripts/select_submission_candidate.py`, `scripts/make_submission.py`
- updates to `scripts/run_part2_full_server.py`, `docs/operations/FULL_INFERENCE_GUIDE.md`, `reports/final_model_card.md`

### Small artifacts

- final `submission.csv` (`gated_geometry`)
- candidate submissions under `submissions/`
- compact outputs whitelisted in `.gitignore`
- CV reports, candidate-selection reports, feature-importance CSVs, and diagnostic figures
- model configs and feature lists under `models/*.json` and `models/*.txt`

## Local-Only Large Artifacts

The following guide artifacts exist locally but were intentionally not pushed because they exceed normal GitHub file limits or are reproducible from scripts:

| path | local size MB | reason |
|---|---:|---|
| `outputs/baseline_predictions_train_hidden.csv` | 217.50 | larger than 100 MiB |
| `features/baseline_features_train.csv` | 1080.07 | larger than 100 MiB |
| `features/residual_targets.csv` | 289.68 | larger than 100 MiB |
| `features/leftover_targets.csv` | large | reproducible from `build_leftover_targets.py` |
| `features/geometry_features_train.parquet` | 249.30 | larger than 100 MiB |
| `outputs/residual_geometry_oof.csv` | 879.67 | larger than 100 MiB |
| `outputs/gated_geometry_oof.csv` | 496.18 | larger than 100 MiB |
| `outputs/residual_xgb_oof.csv` | 491.80 | larger than 100 MiB |
| `outputs/residual_xgb_leftover_oof.csv` | 696.11 | larger than 100 MiB |
| `outputs/gated_geometry_plus_xgb_leftover_oof.csv` | 593.09 | larger than 100 MiB |
| `outputs/blend_oof.csv` | 664.22 | larger than 100 MiB |
| `features/gr_features_train.csv` | 3830.91 | larger than 100 MiB |
| `features/typewell_features_train.csv` | 1293.66 | larger than 100 MiB |
| `features/alignment_features_train.csv` | 1291.09 | larger than 100 MiB |
| `models/*.pkl` | ~0.83 each | excluded by `.gitignore`; reproducible from training scripts |

## Validation Status

- `scripts/validate_part2_outputs.py`: previously `checks=34 failures=0`
- `scripts/validate_submission.py --submission submission.csv`: `rows=14151, columns=id,tvt`
- `scripts/select_submission_candidate.py --dry-run`: selected `gated_geometry`, OOF RMSE `13.67`
- `gated_geometry_plus_xgb_leftover` stack OOF RMSE `15.03`; kept as tracked candidate but not selected
- Full guide artifacts exist locally under their documented paths.