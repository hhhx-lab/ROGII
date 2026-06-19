# Engineering Modeling Plan

## Positioning

This project should be treated as a geological prediction engineering problem and a serious leaderboard campaign. The model must be reproducible, interpretable enough for drilling context, and strong enough to compete for first place on hidden wells that are not visible in the public `test/` folder.

The core engineering question is:

> Given a horizontal well trajectory, partial `TVT_input`, gamma ray logs, and a vertical typewell reference, can we predict the missing TVT interval in a way that respects geological continuity and can be validated before submission?

## Engineering Principles

1. Data contracts first: every pipeline step must define required columns, row ordering, well IDs, missing-value rules, and output schema.
2. Geology-aware assumptions: TVT should generally evolve continuously along the lateral, but faults, formation changes, and log mismatches can create local deviations.
3. Validation before modeling ambition: the public test examples are not a reliable leaderboard proxy, so validation must be simulated from training wells.
4. Baselines are controls: a simple extrapolation model is not the final solution; it is the benchmark every complex model must beat.
5. Failure analysis is part of the method: report RMSE by well, by missing-interval length, by GR coverage, and by geological unit where possible.
6. Leaderboard submissions are experiments: every submission should have a hypothesis, a local CV score, and a short result note.

## Current Baseline

The current baseline extrapolates `TVT_input` per well using the median `dTVT/dMD` slope from the last observed segment.

This is useful because:

- it is deterministic and easy to audit;
- it matches the submission schema;
- it gives a lower-bound engineering control;
- it reveals whether hidden intervals are mostly smooth continuation or require stronger geological correction.

This is not enough because:

- it ignores GR signal;
- it ignores vertical typewell correlation;
- it cannot detect structural discontinuities;
- it may fail when the hidden interval crosses a formation transition.

## Validation Plan

The visible `test/` folder contains only three example wells copied from training. Real validation must be built from training data:

1. For each training well, identify observed `TVT_input` and target `TVT`.
2. Mask a continuous trailing segment to imitate the hidden evaluation zone.
3. Run the full prediction pipeline using only the unmasked part.
4. Score RMSE on the masked segment.
5. Repeat across many wells and segment lengths.

Validation reports should include:

- overall RMSE;
- per-well RMSE distribution;
- RMSE by hidden interval length;
- RMSE by GR missing rate;
- RMSE by local TVT slope or curvature;
- top failure cases with plots.

## Method Options

| Option | Method | Engineering value | Main risk | When to use |
|---|---|---|---|---|
| A | Tail-slope extrapolation | Strong control baseline, fully explainable | Weak near faults or formation changes | Always keep as baseline |
| B | Geometry-only residual model | Uses `MD`, `X`, `Y`, `Z`, local slope, curvature | May learn shallow shortcuts | First ML iteration |
| C | GR-aware residual model | Adds rock-response signal from gamma ray | GR has many missing values and may be noisy | After validation masking is stable |
| D | Typewell correlation model | Uses vertical reference log and formation labels | Alignment is nontrivial | Main geology-aware upgrade |
| E | Hybrid system | Baseline extrapolation plus residual corrections | More moving parts | Recommended production path |
| F | Sequence model | Learns full well trajectory patterns | Harder to validate and explain under notebook runtime | Later experiment only |

## Recommended Path

Use a staged hybrid system:

1. Baseline layer: deterministic per-well TVT extrapolation.
2. Feature layer: compute local geometry, slope, curvature, known-distance, GR rolling stats, and typewell summary features.
3. Residual layer: train a model to predict `true TVT - baseline TVT` on simulated masked intervals.
4. Constraint layer: smooth and sanity-check predictions against physically plausible TVT changes.
5. Reporting layer: output submission plus validation diagnostics.

This structure is practical: even if the residual model underperforms, the baseline remains valid and the system degrades gracefully.

## Implementation Milestones

1. Build masking-based cross-validation on all training wells.
2. Add baseline CV metrics and plots.
3. Add feature extraction for horizontal wells.
4. Add typewell feature extraction and GR alignment candidates.
5. Train a first residual model with sklearn histogram gradient boosting.
6. Compare against baseline by well and by failure type.
7. Package a deterministic Kaggle notebook workflow.
8. Track leaderboard submissions with conservative, balanced, and aggressive variants.

## Acceptance Criteria

A model iteration is worth keeping only if it satisfies all of the following:

- produces a valid `id,tvt` submission with no missing values;
- beats the tail-slope baseline on train-derived validation;
- does not improve only on a few easy wells while failing badly on hard wells;
- has clear diagnostics for failure cases;
- can run inside Kaggle notebook limits with internet disabled;
- can be explained as a geological prediction workflow, not just a black-box fit.
