# Full Inference Artifact Upload Audit

This audit maps `docs/operations/FULL_INFERENCE_GUIDE.md` artifacts to the repository upload decision after the local full inference run.

## Submitted In Git

Small artifacts from the guide were submitted in-place under their expected paths, including final submissions, reports, test-side feature artifacts, compact parquet feature dependencies, and Part 2 audit outputs.

## Local-Only Large Artifacts

The following guide artifacts exist locally but were intentionally not pushed because the user requested not to upload oversized files and they exceed normal GitHub file limits:

| path | local size MB | reason |
|---|---:|---|
| `outputs/baseline_predictions_train_hidden.csv` | 217.50 | larger than 100 MiB |
| `features/baseline_features_train.csv` | 1080.07 | larger than 100 MiB |
| `features/residual_targets.csv` | 289.68 | larger than 100 MiB |
| `features/geometry_features_train.parquet` | 249.30 | larger than 100 MiB |
| `outputs/residual_geometry_oof.csv` | 879.67 | larger than 100 MiB |
| `features/gr_features_train.csv` | 3830.91 | larger than 100 MiB and above this repository's GitHub LFS single-object limit |
| `features/typewell_features_train.csv` | 1293.66 | larger than 100 MiB |
| `features/alignment_features_train.csv` | 1291.09 | larger than 100 MiB |

## Validation Status

- `scripts/validate_part2_outputs.py`: `checks=34 failures=0`
- `scripts/validate_submission.py --submission submission.csv`: `rows=14151, columns=id,tvt`
- Full guide artifacts exist locally under their documented paths.
