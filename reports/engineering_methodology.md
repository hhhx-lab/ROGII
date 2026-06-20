# Geological Prediction Engineering Methodology

## What We Are Building

We are building a real, testable workflow for predicting TVT along horizontal wellbores. The competition format is Kaggle, and the competitive target is first place, but the engineering target is broader: a pipeline that can ingest well trajectory data, partial TVT observations, gamma ray logs, and typewell references, then produce a defensible geological-position prediction.

The project should answer three questions:

1. Can the pipeline produce correct submissions every time?
2. Can the validation setup estimate hidden-well performance honestly?
3. Can the model behavior be explained in geological and operational terms?

## System View

```text
Raw well files
  |
  v
Schema and integrity checks
  |
  v
Per-well baseline prediction
  |
  v
Geometric, log, and typewell features
  |
  v
Residual model and constraints
  |
  v
Validation report + Kaggle submission
```

## Data Contracts

Horizontal well files must provide:

- `MD`, measured depth;
- `X`, `Y`, `Z`, trajectory coordinates;
- `GR`, gamma ray log, possibly missing;
- `TVT_input`, observed target proxy with hidden interval set to missing;
- `TVT`, training-only ground truth;
- formation-surface columns in training data.

Typewell files must provide:

- `TVT`, vertical depth index;
- `GR`, vertical reference gamma ray;
- `Geology`, formation label in training typewell files; optional or absent on visible test typewell files.

Submission files must provide:

- `id`, formatted as `{well}_{row_index}`;
- `tvt`, predicted true vertical thickness.

## Validation Design

The hidden test set is not directly visible. The correct engineering substitute is a train-derived validation task:

1. Select a training well.
2. Hide the last interval of `TVT_input`.
3. Predict the hidden interval.
4. Score against the original `TVT`.
5. Repeat across wells and interval lengths.

This makes the validation problem structurally similar to the Kaggle rerun environment.

## Model Design Choices

### Baseline

Use local TVT continuation from the last observed segment. This is the operational control model.

### Residual Model

Learn corrections to the baseline instead of predicting absolute TVT from scratch. This makes the model easier to stabilize and easier to diagnose.

Useful residual features:

- distance from last known TVT point;
- local `dTVT/dMD` slope and slope stability;
- `Z`, `MD`, and trajectory curvature;
- GR rolling mean, standard deviation, and missingness flags;
- typewell GR statistics near candidate TVT;
- optional formation-label indicators from typewell alignment, only when the target test schema provides labels.

### Geological Constraint Checks

After prediction, run checks for:

- impossible jumps;
- unstable oscillation;
- monotonicity breaks where not justified;
- extreme departure from the baseline;
- high-risk wells with missing GR or long hidden intervals.

## Method Options

| Choice | Description | Why it is credible |
|---|---|---|
| Baseline only | Continue TVT from known interval | Matches continuity assumption and is auditable |
| Geometry residual | Correct baseline with trajectory features | Captures well path effects |
| GR residual | Add gamma ray response features | Uses petrophysical signal |
| Typewell alignment | Match horizontal GR against vertical reference | Uses the provided geological reference directly |
| Hybrid ensemble | Combine baseline, residual, and constraint checks | Practical, robust, and explainable |

## Practical Recommendation

Start with the hybrid residual approach, not a deep sequence model. The deep model may be useful later, but it is harder to validate, harder to explain, and more likely to become a leaderboard trick. A residual system gives us a clearer engineering story:

- baseline explains the main trend;
- features explain local deviations;
- validation proves robustness;
- diagnostics show where geology is hard.

## Next Engineering Deliverables

1. `scripts/make_cv_splits.py`: generate simulated hidden intervals.
2. `scripts/evaluate_baseline_cv.py`: score the current baseline across training wells.
3. `scripts/build_features.py`: produce per-row geometric and GR features.
4. `scripts/train_residual_model.py`: train and evaluate the residual model.
5. `reports/failure_cases.md`: summarize the worst wells and likely geological causes.
