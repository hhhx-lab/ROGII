# Leaderboard Strategy

## Objective

The target is first place, but the route is not random model stacking. We need a disciplined competition system:

1. a trusted local validation score;
2. a strong baseline control;
3. aggressive but explainable feature development;
4. multiple model families only after validation is stable;
5. submission tracking and failure analysis after every leaderboard result.

## Core Principle

Engineering rigor and leaderboard ambition should reinforce each other. The validation system tells us which ideas are real; the leaderboard tells us where our validation is misaligned with Kaggle's hidden rerun set.

## Sprint Tracks

| Track | Purpose | Deliverable |
|---|---|---|
| Validation | Avoid chasing noise | Full-train hidden-interval CV and group splits |
| Baseline | Establish control score | Tail-slope CV report across 773 wells |
| Features | Add real geological signal | Geometry, GR rolling, typewell alignment |
| Models | Push score | Residual boosting, calibrated blends, sequence experiments |
| Submission Ops | Learn from leaderboard | Versioned submissions, notes, public/private gap tracking |

## Model Escalation Ladder

1. Tail-slope baseline.
2. Geometry residual model.
3. GR-aware residual model.
4. Typewell alignment residual model.
5. Blend several validated residual models.
6. Test sequence or dynamic-time-warping ideas only if they win in validation.

## High-Value Leaderboard Ideas

- Predict residuals instead of absolute TVT.
- Use multiple simulated mask lengths to match hidden wells of different lateral lengths.
- Build well-level difficulty features and use them for model routing.
- Align horizontal GR against typewell GR to detect formation drift.
- Use robust post-processing: smooth residuals, cap impossible jumps, and preserve baseline continuity.
- Keep separate submissions for conservative, balanced, and aggressive blends.

## What We Will Not Do

- Trust the three visible public test wells as a score estimate.
- Add deep models before the residual baseline is beaten.
- Optimize only one aggregate RMSE while ignoring catastrophic wells.
- Submit unlabeled experiments without a clear hypothesis.

## Immediate Next Moves

1. Run full-train tail-slope CV.
2. Build feature extraction and residual targets.
3. Train first sklearn histogram gradient boosting residual model.
4. Compare overall RMSE and worst-well tail against baseline.
5. Prepare Kaggle notebook submission variants.
