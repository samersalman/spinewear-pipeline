#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05_analysis_drd.py -- Phase 4.  Digital Recovery Debt, the paper's primary estimand.

WHAT THIS COMPUTES.  Cumulative baseline-equivalent activity days lost over post-discharge
days 1 to 35, its fusion-versus-decompression contrast, the absolute-scale companion in
thousand steps lost, the assumption-free Manski bounds, the delta-shift tipping point, and the
fourteen plotted plus ten supplementary sensitivity rows of ANALYSIS-PLAN section 6.  Every
choice it makes was made in the locked plan; where the plan gives a ladder, this module walks
the ladder on the stated trigger and records the rung it reached.  NO RUNG, NO WINDOW, NO
COVARIATE AND NO CUTPOINT IS EVER SELECTED BY LOOKING AT AN ESTIMATE.

THE ESTIMATOR, AND WHY IT IS NOT A SUM.  The obvious estimator sums the observed daily deficits
and lets every missing day contribute zero, which is the assertion that on each unobserved day
the participant walked at or above their own preoperative baseline.  Non-wear is most likely
exactly when the true deficit is largest, and there is more of it in sicker participants and in
the more invasive arm, so the naive sum is biased DOWNWARD and biased harder in the group
expected to carry the larger debt.  It attenuates precisely the contrast the paper is about.
So the plan specifies model-and-integrate (3.2): model the daily deficit on a post-discharge-day
spline interacted with procedure group, fit on observed person-days weighted by the inverse
probability of observation, integrate the fitted daily deficit over the whole window for every
episode including the days that episode did not contribute, and report the marginal estimate.
Direct summation on complete windows is sensitivity row 3 and the unadjusted column of Table 2,
printed against its own denominator, because it is the anchor that shows how far the modelled
estimate moved and in which direction.

THE UNADJUSTED CONTRAST, WHICH IS NOT THAT COLUMN AND IS NOT PRESPECIFIED.  STROBE item 16(a)
asks for unadjusted estimates beside confounder-adjusted ones, and it asks for them of the
CONTRAST.  Table 2's unadjusted column is an absolute LEVEL by direct summation, on its own
denominator, and a reader cannot difference two of those medians and recover the quantity 16(a)
wants.  So every contrast this module reports is returned twice: adjusted, and refitted with the
locked covariate set of 3.6 deleted from the mean structure and NOTHING else changed.  Same rows,
same weights, same clustered bootstrap, same seed, same refusals.  What stays in the unadjusted
design is what the estimand is DEFINED on and could not be standardized without: the
post-discharge-day spline, the procedure groups and their day curves, the region terms the
collapse level admits, and day of week.  The rung each fit reached is recorded separately,
because a covariate-free design is a different optimization problem and the two can land on
different rungs, which changes what the gap between them means.  THE LOCKED PLAN DOES NOT
PRESPECIFY THIS: it carries an unadjusted association for the other arm at 4.8 and an unadjusted
absolute level for this one at 9.2, and neither is an unadjusted contrast.  Adding an estimand to
a locked prespecification is an amendment, so the quantity is emitted marked
`prespecified: false` with the sentence that says which item requires it, and the Methods print
it as guideline-mandated rather than as planned.

TWO TRAPS INSIDE THAT, BOTH PRESPECIFIED AND BOTH IMPLEMENTED HERE.

  1. `D = max(0, 1 - A)` IS CONVEX, so by Jensen's inequality `E[max(0, 1 - A)]` is at least
     `max(0, 1 - E[A])`, with equality only when the activity is degenerate or lies entirely at
     or below baseline.  An analysis that models mean normalized activity and then pushes the
     fitted mean through the deficit function UNDERSTATES the debt, and understates it most
     where activity is most variable.  Rule one: the response is `D` itself and nothing in
     Table 2 or Figure 3 is produced by applying `max(0, 1 - .)` to a fitted mean.  Mean
     normalized activity is reported as `1 - D_bar`, the complement of the modelled deficit,
     which needs no second model and no inequality.  Rule two: in a mixed model with a
     nonlinear link the prediction at a zero random effect is the CONDITIONAL mean for a
     median-random-effect episode, not the MARGINAL mean of the population, and the marginal
     mean is the estimand.  The random effects are therefore integrated out by Monte Carlo with
     common random numbers, never set to zero.
  2. A STANDARD AR(1) RESIDUAL LAGS IN THE OBSERVATION INDEX, not in time.  With complete daily
     data those coincide.  With irregular non-wear they do not, and the model then treats a
     pair of days six days apart as adjacent because they happen to be adjacent rows, which is
     not a small distortion in a study whose whole subject is irregular non-wear.  The
     continuous-time analogue is specified instead and the descent from it is by computational
     trigger only.

WHERE THIS RUNS.  INSIDE THE PERIMETER for the four queries, the fits and the report.  LOCALLY
it still runs and running it locally is the intended way to check it: `python3
05_analysis_drd.py` executes `_run_self_test()`, which drives every pure function in the module
against synthetic data with a known answer, touches no network and writes no file.

IN-PERIMETER USE, in a notebook, after the features step has certified the frames:

    %run 00_config.ipynb
    %run -i 03_cohort.py
    %run -i 04_features.py
    FEATURES = run_features()
    %run -i 05_analysis_drd.py
    DRD = run_drd(features=FEATURES)

IT REFUSES TO RUN WHEN `FEATURES["features ok"]` IS FALSE.  That flag is a stop condition, not a
warning: the derived frames failed a null-convention or invariant check, and an estimate fitted
on frames that failed those checks is a number with nothing behind it.

WHAT IT READS AND WHAT IT NEVER DOES.  Four queries against `{DERIVED}` only, no Controlled Tier
table, `q_guarded` the sole query path with a printed dry-run estimate and a hard byte cap on
every one.  The person-day panel and the episode covariate frame are PARTICIPANT-LEVEL and are
pulled into the kernel because a model must be fitted on rows; they are shown only through
`safe_show`, which prints a shape.  NO IDENTIFIER AND NO DATE IS SELECTED AT ALL: the queries
emit a dense surrogate `unit index` in place of the person and episode keys and emit the day of
week as an integer rather than a calendar date, so no export path can leak either even by
accident.  Every number that reaches a printed or returned surface is an aggregate that has been
through the disclosure floor.

THE ONE NULL THAT DECIDES THE ANSWER.  `drd_daily.deficit` is NULL on a non-analyzable day and
is NEVER zero-imputed.  Any code path here that fills it with zero destroys the estimator, so
the module checks for zero-imputation in BOTH directions before it fits anything and halts on
either.  Sensitivity deficits are deliberately not precomputed and are recomputed from
`drd_daily.steps` and the alternative baselines, which is the one recomputation DAG-SCHEMA 8.11
hands over.

WHAT IT WRITES.  Nothing.  `07_export.py` is the only module in this project that writes a file.
`run_drd` returns a dictionary whose `debt` and `sensitivity` members are the export contract's
blocks of the same names, carrying RAW TRUE VALUES, and prints a report.

WHY RAW AND NOT RENDERED, WHICH IS THE ONE DECISION THIS INTERFACE TURNS ON.  The standing rule
of this project is round and floor-test AT THE BOUNDARY, never before.  `07_export.py` is the
boundary, and its own docstring says it asks `disclosable(n)` of the TRUE count and only then
calls `round20`.  It can only do that if what reaches it is a true count.  Hand it a finished
node instead and it floor-tests a number that has already been rounded: a true 21 arrives as a
disclosed 20, the floor is never asked about the 21, and nothing is registered in
`results.json.suppressed`, which is the log that records what was hidden and why.  So the debt
and sensitivity blocks leave this module as true integers, `(est, lo, hi)` triples and bare P
values, and 07 renders every one of them.

THE RETURNED OBJECT IS THEREFORE AN IN-PERIMETER INTERMEDIATE AND NOT A DISCLOSABLE ARTEFACT.
It carries true counts, so nothing may print it, write it or paste it.  Both surfaces a human
actually sees are still suppressed at the moment they are built: `render_report` puts every raw
value back through this module's own node grammar before a character reaches the screen, and
`07_export.py` does the same on the way to `results.json`.

WHY `06_analysis_gate.py` DOES THE OPPOSITE, so the asymmetry does not read as an accident.  06
hands 07 a RENDERED gate block, which 07 adopts through `_adopt_rendered_gate`, because only 06
knows the tier logic and the block is tier-shaped: a key absent because the tier forbids the
analysis is a different thing from a key hidden for cell size, and 06 is the only module that
can tell those two apart.  This module's debt block is straightforwardly numeric -- counts,
triples and P values, with no tier anywhere in it -- so it has no such justification and takes
no such exemption.
"""

from __future__ import annotations

import io
import math
import re
import sys
import warnings
from contextlib import redirect_stdout
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

# `pipeline/` is not a package and this file's name is not an importable identifier, so it is
# always a script: `%run` inside the perimeter, `python3` on a laptop.  Both need the module's
# own directory on the path before `import disclosure` can resolve, and neither guarantees it.
try:
    _HERE = str(Path(__file__).resolve().parent)
except NameError:                                  # exec'd without a file, e.g. a paste
    _HERE = str(Path.cwd())
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import numpy as np
import pandas as pd

from disclosure import (
    EM_DASH,
    MIN_CELL,
    MINUS_SIGN,
    DisclosureError,
    disclosable,
    is_legal_disclosed_count,
    round20,
    safe_show,
)


class DrdAnalysisError(RuntimeError):
    """An analysis stop condition.  Never downgraded to a warning."""


class DrdBudgetExceeded(DrdAnalysisError):
    """The priced total exceeded this step's budget, so nothing executed and nothing billed."""


class RungFailure(DrdAnalysisError):
    """One rung of the model ladder failed, carrying the trigger code that made it fail.

    This is the ONLY way a rung may be abandoned.  It is raised by the fitting code on a
    computational property of the fit or of the environment, it carries a trigger from the fixed
    set of ANALYSIS-PLAN 3.5, and it is caught by the ladder walker, which records the trigger
    and descends.  There is deliberately no path by which an estimate can raise it: a rung that
    converges cleanly is kept whatever number it produces.
    """

    def __init__(self, trigger: str, detail: str) -> None:
        if trigger not in DESCENT_TRIGGERS:
            raise DrdAnalysisError(
                f"a rung tried to fail with the trigger {trigger!r}, which is not one of the "
                f"prespecified descent triggers. A rung may only be abandoned on a trigger the "
                f"plan names."
            )
        super().__init__(f"{trigger}: {detail}")
        self.trigger = trigger
        self.detail = detail


# The three ways a bootstrap resample or an imputation legitimately fails: an analysis stop
# condition raised by this module, a rung reporting that it could not fit (`RungFailure`, named
# here even though it descends from the first, because the two are caught for different
# reasons), and a singular or otherwise undecomposable design matrix.  A BARE `except
# Exception` AROUND A FIT IS NOT A NARROWER VERSION OF THIS, IT IS A DIFFERENT THING: it counts
# a genuine coding bug inside `estimate_variant` as a bootstrap failure, and at a 100 percent
# failure rate that fires trigger T4 and descends the family ladder for a reason that has
# nothing to do with the model.
BOOTSTRAP_FAILURES: tuple[type[BaseException], ...] = (
    DrdAnalysisError, RungFailure, np.linalg.LinAlgError)


# ======================================================================================
# (1) The locked vocabulary.
#
#     Every slug and every display label below is transcribed from ANALYSIS-PLAN.md, which is
#     the owner of all five vocabularies and wins over any other file (plan section 11 item 8).
#     `local/verify.py` asserts SET EQUALITY over the fourteen PLOTTED sensitivity rows against
#     the plan's own table, which is why the fourteen and the ten supplementary rows are two
#     separate structures here and are returned under two separate result keys.  A supplementary
#     slug appearing among the fourteen is a failure, and so is a plotted slug missing from
#     them.
# ======================================================================================

FOUR_GROUP_SLUGS: tuple[str, ...] = (
    "cervical_decompression",
    "cervical_fusion",
    "lumbar_decompression",
    "lumbar_fusion",
)
TWO_GROUP_SLUGS: tuple[str, ...] = ("fusion", "decompression")
ALL_GROUPS_SLUG: str = "all_groups"
GROUP_SLUGS: tuple[str, ...] = FOUR_GROUP_SLUGS + TWO_GROUP_SLUGS + (ALL_GROUPS_SLUG,)

GROUP_LABELS: Mapping[str, str] = MappingProxyType({
    "cervical_decompression": "Cervical decompression",
    "cervical_fusion": "Cervical fusion",
    "lumbar_decompression": "Lumbar decompression",
    "lumbar_fusion": "Lumbar fusion",
    "fusion": "Fusion",
    "decompression": "Decompression",
    "all_groups": "All groups",
})

COLLAPSE_LEVELS: tuple[str, ...] = ("four_group", "two_group", "single_group", "no_estimand")

REGIONS: tuple[str, ...] = ("cervical", "lumbar")

# ANALYSIS-PLAN 3.5 and EXPORT-CONTRACT 3.1.1.  `rung_index` is the 1-based position in this
# tuple, so the tuple order IS the ladder and nothing else defines it.
ESTIMATOR_RUNGS: tuple[Mapping[str, Any], ...] = (
    MappingProxyType({
        "index": 1, "slug": "r_ordered_beta_glmm",
        "display": "Ordered beta mixed model in R",
        "language": "R", "triggers": ("T0", "T1", "T2", "T3"),
        "family": "ordered beta", "link": "logit", "marginalize": True,
    }),
    MappingProxyType({
        "index": 2, "slug": "r_zero_one_inflated_beta_glmm",
        "display": "Zero-one-inflated beta mixed model in R",
        "language": "R", "triggers": ("T1", "T2", "T3"),
        "family": "zero-one-inflated beta", "link": "logit", "marginalize": True,
    }),
    MappingProxyType({
        "index": 3, "slug": "py_fractional_logit_gee",
        "display": "Fractional-response quasi-binomial estimating equations",
        "language": "Python", "triggers": ("T1", "T2"),
        "family": "quasi-binomial fractional response", "link": "logit", "marginalize": False,
    }),
    MappingProxyType({
        "index": 4, "slug": "py_linear_mixed_truncated",
        "display": "Linear mixed model with fitted values truncated to the unit interval",
        "language": "Python", "triggers": ("T1", "T2"),
        "family": "linear mixed", "link": "identity", "marginalize": True,
    }),
    MappingProxyType({
        "index": 5, "slug": "py_nonparametric_day_group_means",
        "display": "Nonparametric day and group means",
        "language": "Python", "triggers": (),
        "family": "nonparametric day and group means", "link": "identity",
        "marginalize": False,
    }),
)
ESTIMATOR_RUNG_SLUGS: tuple[str, ...] = tuple(r["slug"] for r in ESTIMATOR_RUNGS)
ESTIMATOR_RUNG_LABELS: Mapping[str, str] = MappingProxyType(
    {r["slug"]: r["display"] for r in ESTIMATOR_RUNGS})

# ANALYSIS-PLAN 3.5, "descent triggers, stated exactly".  Every one is a computational property
# of the fit or of the environment.  NO TRIGGER REFERENCES THE DIRECTION, MAGNITUDE OR
# SIGNIFICANCE OF ANY CONTRAST, and `RungFailure` refuses any trigger outside this mapping, so a
# rung cannot be abandoned for a reason the plan did not name.
DESCENT_TRIGGERS: Mapping[str, str] = MappingProxyType({
    "T0": "The R analysis environment could not be reached, so both R rungs were skipped "
          "together and the ladder resumed at the first Python rung",
    "T1": "The fit did not converge: a non-zero convergence code, a maximum absolute gradient "
          "above the tolerance, or a Hessian that is not positive definite",
    "T2": "A boundary estimate: a variance component within the tolerance of zero, or a "
          "cutpoint, dispersion or correlation parameter sitting at the edge of its range",
    "T3": "A singular random-effect covariance, or a random-effect correlation at or beyond the "
          "ceiling",
    "T4": "Bootstrap instability: more than the permitted share of clustered resamples failed "
          "to converge, which is a property of the fitting process across resamples and not of "
          "any estimate",
})

# ANALYSIS-PLAN 3.4.  The residual descent runs INSIDE a rung and is not a family descent: a
# random slope in real post-discharge day already induces a within-person correlation that is a
# function of elapsed time rather than of row order, so the essential property survives it.
RESIDUAL_STRUCTURE_RUNGS: tuple[Mapping[str, str], ...] = (
    MappingProxyType({
        "slug": "continuous_time_ar1_intercept_slope",
        "display": "Continuous-time first-order autoregressive",
    }),
    MappingProxyType({
        "slug": "intercept_slope_no_residual_correlation",
        "display": "Person random intercept and slope in day",
    }),
    MappingProxyType({
        "slug": "intercept_only",
        "display": "Person random intercept only",
    }),
)

# ANALYSIS-PLAN section 6.  Fourteen PLOTTED rows from ten ladder rows: row 6 carries four wear
# definitions and row 7 carries two baseline windows.  `order` is the plan's ladder number and
# `sub` the position within it, so the plan's fixed order survives the expansion and cannot be
# rearranged to put a reassuring row at the top.
PLOTTED_SENSITIVITY_ROWS: tuple[Mapping[str, Any], ...] = tuple(MappingProxyType(row) for row in (
    {"order": 1, "sub": 1, "slug": "pod_anchored_window",
     "display": "Postoperative day 8–42 window", "axis": "primary", "render": "marker",
     "varies": "Accrual over postoperative days 8 to 42 instead of post-discharge days 1 to 35"},
    {"order": 2, "sub": 1, "slug": "inpatient_days_censored",
     "display": "Inpatient days censored", "axis": "primary", "render": "marker",
     "varies": "Days inside a readmission stay removed from the window"},
    {"order": 3, "sub": 1, "slug": "complete_window_direct_regression",
     "display": "Complete windows, direct regression", "axis": "primary", "render": "marker",
     "varies": "Direct summation of the debt on episodes with all 35 days observed, regressed "
               "on the covariate set"},
    {"order": 4, "sub": 1, "slug": "observation_weighted",
     "display": "Weighted for observation", "axis": "primary", "render": "marker",
     "varies": "Observation weights removed, or applied where the primary rung did not use "
               "them"},
    {"order": 5, "sub": 1, "slug": "delta_shift_tipping_point",
     "display": "Delta-shift tipping point", "axis": "latent_logit_shift", "render": "panel",
     "varies": "The delta grid on the latent logit scale, in three application patterns"},
    {"order": 6, "sub": 1, "slug": "wear_definition_s1",
     "display": "Wear day at 40% heart-rate adherence", "axis": "primary", "render": "marker",
     "varies": "Valid wear day at 40% daily heart-rate adherence"},
    {"order": 6, "sub": 2, "slug": "wear_definition_s2",
     "display": "Wear day at 10 hours plus 100 steps", "axis": "primary", "render": "marker",
     "varies": "Valid wear day at 10 hours of wear and at least 100 steps"},
    {"order": 6, "sub": 3, "slug": "wear_definition_s3",
     "display": "Wear day at 8 hours", "axis": "primary", "render": "marker",
     "varies": "Valid wear day at 8 hours of wear"},
    {"order": 6, "sub": 4, "slug": "wear_definition_s4",
     "display": "Wear day at 12 hours", "axis": "primary", "render": "marker",
     "varies": "Valid wear day at 12 hours of wear"},
    {"order": 7, "sub": 1, "slug": "baseline_window_60_15",
     "display": "Baseline 15–60 days before surgery", "axis": "primary", "render": "marker",
     "varies": "Baseline over the 60 to 15 days before surgery"},
    {"order": 7, "sub": 2, "slug": "baseline_window_30_1",
     "display": "Baseline 1–30 days before surgery", "axis": "primary", "render": "marker",
     "varies": "Baseline over the 30 to 1 days before surgery"},
    {"order": 8, "sub": 1, "slug": "device_change_excluded",
     "display": "Device change excluded", "axis": "primary", "render": "marker",
     "varies": "Participants changing device model between baseline and post-discharge day 90 "
               "excluded"},
    {"order": 9, "sub": 1, "slug": "baseline_floor",
     "display": "Baseline floor at 1,000 steps per day", "axis": "primary", "render": "marker",
     "varies": "Restricted to a baseline of at least 1,000 steps per day"},
    {"order": 10, "sub": 1, "slug": "debt_untruncated",
     "display": "Debt not truncated at zero", "axis": "primary", "render": "marker",
     "varies": "The truncation at zero removed, so days above baseline offset days below"},
))
PLOTTED_SENSITIVITY_SLUGS: tuple[str, ...] = tuple(r["slug"] for r in PLOTTED_SENSITIVITY_ROWS)

# The ladder rows whose estimate is a BOUND rather than an interval, which today is the one
# row whose value is a grid coordinate.  Declared rather than inferred from the numbers,
# because a bootstrap whose resamples all landed on the same value produces a triple that
# looks exactly like a bound and is not one.  `07_export.py` carries the same set under
# `BOUND_SENSITIVITY_ROWS`; both are transcriptions of ANALYSIS-PLAN section 6 row 5.
BOUND_SENSITIVITY_SLUGS: frozenset[str] = frozenset({"delta_shift_tipping_point"})

# ANALYSIS-PLAN section 6, second table.  TEN rows at plan version 1.3.  These are NOT members
# of the set `local/verify.py` asserts equality over, they are not plotted on the Figure 3
# ladder, and they are returned under their own result key so that they cannot leak into the
# `sensitivity` block by an accident of iteration order.
SUPPLEMENTARY_SENSITIVITY_ROWS: tuple[Mapping[str, Any], ...] = tuple(
    MappingProxyType(row) for row in (
        {"slug": "baseline_steps_adjusted", "display": "Baseline steps adjusted",
         "varies": "The primary model with the baseline step count added to the mean structure"},
        {"slug": "bmi_multiply_imputed", "display": "Body mass index multiply imputed",
         "varies": "Twenty imputations in place of the missing indicator"},
        {"slug": "weights_without_lagged_wear",
         "display": "Observation weights without lagged wear",
         "varies": "The observation model refitted with the lagged wear fraction removed"},
        {"slug": "junctions_mirrored", "display": "Junction codes mirrored",
         "varies": "Cervicothoracic and thoracolumbar stems assigned to the caudal rather than "
                   "the cranial member"},
        {"slug": "cervical_fusion_gap_reclassified",
         "display": "Cervical fusion gap reclassified",
         "varies": "The misfiled anterior cervical fusions moved to cervical fusion"},
        {"slug": "cervical_decompression_gap_stated", "display": "Cervical decompression gap",
         "varies": "The absent cervical decompression codes, reported as a measured omission"},
        {"slug": "four_group_model", "display": "Four-group model",
         "varies": "The four-group specification where the collapse ladder permits it"},
        {"slug": "truncated_assigned_max_debt",
         "display": "Truncated windows at maximal debt",
         "varies": "Episodes truncated by death or reoperation assigned the maximal 35 days "
                   "lost"},
        {"slug": "fusion_status_non_add_on_only",
         "display": "Fusion status without add-on codes",
         "varies": "Fusion status read from records that can define an operation on their own"},
        {"slug": "baseline_weekday_weekend_split",
         "display": "Separate weekday and weekend baselines",
         "varies": "Each day's deficit taken against the baseline of its own day type"},
    ))
SUPPLEMENTARY_SENSITIVITY_SLUGS: tuple[str, ...] = tuple(
    r["slug"] for r in SUPPLEMENTARY_SENSITIVITY_ROWS)

SENSITIVITY_LABELS: Mapping[str, str] = MappingProxyType(
    {row["slug"]: row["display"]
     for row in PLOTTED_SENSITIVITY_ROWS + SUPPLEMENTARY_SENSITIVITY_ROWS})

# EXPORT-CONTRACT 3.5, in Figure 3 block 1 order.  The first is the primary and exactly one
# contrast carries `is_primary`.
CONTRAST_SLUGS: tuple[str, ...] = (
    "fusion_vs_decompression",
    "lumbar_vs_cervical",
    "region_by_fusion_interaction",
    "fusion_vs_decompression_cervical",
    "fusion_vs_decompression_lumbar",
)
PRIMARY_CONTRAST_SLUG: str = "fusion_vs_decompression"
CONTRAST_LABELS: Mapping[str, str] = MappingProxyType({
    "fusion_vs_decompression": "Fusion versus decompression",
    "lumbar_vs_cervical": "Lumbar versus cervical",
    "region_by_fusion_interaction": "Region by fusion interaction",
    "fusion_vs_decompression_cervical": "Fusion versus decompression, cervical",
    "fusion_vs_decompression_lumbar": "Fusion versus decompression, lumbar",
})

# EXPORT-CONTRACT 7.5.  A suppressed or not-estimable node carries one of these slugs and the
# sentence beside it verbatim, so a reader meets one phrasing rather than five.
SUPPRESSION_SENTENCES: Mapping[str, str] = MappingProxyType({
    "cell_below_threshold": "20 or fewer, suppressed per All of Us dissemination policy",
    "numerator_suppressed": "suppressed because the count behind it is suppressed",
    "contributing_n_below_threshold": "20 or fewer contributors, suppressed",
    "secondary_suppression": "suppressed to protect a suppressed cell in the same total",
    "not_estimable_cell_size": "not estimable (cell size)",
    "not_estimable_convergence": "not estimable (model did not converge)",
    "not_estimable_data_unavailable": "not estimable (data not available)",
    "not_permitted_by_tier": "not permitted at the feasibility tier reached",
    # Ninth as of EXPORT-CONTRACT 1.6.0, and adopted here character-identically because this
    # module carries a copy of the 7.5 sentences.  A primary contrast that never crosses zero
    # out to the end of the extended delta grid is THE STRONGER RESULT: no amount of
    # unmeasured-day pessimism inside the prespecified range overturns the finding.  It used
    # to be emitted as `not_estimable_data_unavailable`, which said the data were not there,
    # and the data were there: the grid was walked and the extension was used.
    "no_crossing_within_range": "no crossing within the prespecified range",
    # TENTH as of EXPORT-CONTRACT 1.7.0, transcribed character-exact from 7.5 and placed
    # LAST because 7.5 places it last: `disclosure.py` holds the vocabulary as an ORDERED
    # tuple and this module asserts ordered equality against it below, so the row position
    # is load-bearing rather than cosmetic.  It is the fourth `not_estimable_*` reason and
    # the tenth row, and 7.5 says in terms that those are two different facts: a vocabulary
    # this contract transcribes grows at the bottom, and re-sorting the table to group the
    # four siblings would move a line in a module this file does not own.
    #
    # NO EXISTING REASON COULD CARRY IT.  ANALYSIS-PLAN 4.9 refuses any Arm A logistic fit
    # whose coefficient exceeds the prespecified ceiling, and a quasi-separated fit
    # CONVERGES: the cell size was fine, the data were there, the tier permitted the
    # analysis, so the three obvious neighbours are each simply false of it, and
    # `not_estimable_convergence` -- the near-miss -- is the falsest of the four, because
    # convergence is exactly what makes quasi-separation dangerous instead of visible.
    # This module does not emit it (`06_analysis_gate.py` does); it is carried because this
    # module carries a COPY of 7.5 and a copy that drifts by one row drifts silently.
    "not_estimable_separation": "not estimable (separation)",
})

# EXPORT-CONTRACT 2.4.  A continuous statistic is NEVER rounded to 20; it is rounded to the
# decimals for its unit and is disclosable only when the count contributing to it clears the
# floor.  Confusing that with the count rule is the single easiest way to leak.
UNIT_DECIMALS: Mapping[str, int] = MappingProxyType({
    "activity_days": 1,
    "thousand_steps": 1,
    "normalized_activity": 2,
    "steps": 0,
    "days": 1,
    "percent": 0,
    "odds_ratio": 2,
    "hours": 0,
    "minutes": 0,
    "count": 0,
    "dimensionless": 2,
    "information_criterion": 0,
})
THOUSANDS_SEPARATOR_UNITS: tuple[str, ...] = ("steps", "count", "information_criterion")


# ======================================================================================
# (2) The locked constants.
#
#     Every number below is in ANALYSIS-PLAN.md at the section named beside it.  None of them
#     is a tuning knob and none may be changed without an amendment in the plan's section 13 and
#     a re-lock.  They are named rather than written into an expression so that a reader can
#     check the plan against this block in one pass, and so that no threshold is retyped inside
#     a query string or a fitting call.
# ======================================================================================

SEED: int = 0                                   # ANALYSIS-PLAN 10.  Every draw descends from it.

# 3.3, the Monte Carlo marginalization of the random effects.
MONTE_CARLO_DRAWS: int = 2000
MONTE_CARLO_RECHECK_DRAWS: int = 4000
MONTE_CARLO_RECHECK_STREAM: int = 999
MONTE_CARLO_ESCALATED_DRAWS: int = 10000
MONTE_CARLO_TOLERANCE_ACTIVITY_DAYS: float = 0.05

# 3.8, the person-clustered nonparametric bootstrap.
BOOTSTRAP_PRIMARY: int = 1000
BOOTSTRAP_SENSITIVITY: int = 500
CONFIDENCE_LEVEL: float = 0.95
BOOTSTRAP_FAILURE_SHARE_TRIGGER: float = 0.25   # trigger T4 of 3.5
# An interval is computed from the resamples that came back finite, and dropping the rest in
# silence is what lets a row whose resamples nearly all failed still print an ordinary 95%
# interval.  The minimum is DERIVED FROM THE TRIGGER rather than invented beside it: the plan
# tolerates a quarter of the resamples failing before T4 fires, so an interval standing on less
# than the complementary share of the resamples that were attempted is refused for exactly the
# reason T4 exists.
BOOTSTRAP_MIN_FINITE_SHARE: float = 1.0 - BOOTSTRAP_FAILURE_SHARE_TRIGGER
BOOTSTRAP_MIN_FINITE_DRAWS: int = 2             # a percentile of one number is not a percentile

# 3.6, the time basis and the covariate splines.  Knots are FIXED A PRIORI, on a roughly
# logarithmic spacing, and are NOT placed at data quantiles: quantile knots would make the basis
# depend on the observed day distribution, and fixed knots guarantee that every sensitivity row
# differs from the primary only in the thing it varies.
DAY_KNOTS: tuple[int, ...] = (2, 6, 12, 21, 32)
DISPLAY_DAY_KNOTS: tuple[int, ...] = (2, 6, 12, 21, 35, 55, 80)
AGE_KNOTS: tuple[int, ...] = (45, 60, 75)
BMI_KNOTS: tuple[int, ...] = (22, 28, 35)
LOG_BASELINE_KNOTS: tuple[int, ...] = (3000, 6000, 10000)   # 3.9, the companion endpoint only
DAY_OF_WEEK_REFERENCE: int = 4                  # Wednesday, with 1 as Sunday.  Arbitrary and
                                                # fixed; the standardized marginal estimate
                                                # integrates over each episode's own calendar
                                                # alignment, so the reference cannot affect it.
CHARLSON_LEVELS: tuple[str, ...] = ("0", "1", "2", "3_or_more")
# THE ORDER AND THE REFERENCE ARE THE PLAN'S AND ARE SHARED WITH THE OTHER ARM.  The covariate
# table of ANALYSIS-PLAN reads "Factor: male, female, other or unknown", and
# `06_analysis_gate.py` carries the same tuple with `SEX_REFERENCE = "male"`.  The contrast is
# numerically unaffected by which level is omitted, because the column space is the same either
# way; what is affected is the order in which the rank filter drops columns, and what a reader
# meets in print, and two arms of one paper naming different reference categories for the same
# covariate is a discrepancy nothing in the numbers would reveal.
SEX_LEVELS: tuple[str, ...] = ("male", "female", "other_or_unknown")
SEX_REFERENCE: str = "male"

# 2.3 and 3.1, the accrual window.  The estimand is bounded at the window length.
ACCRUAL_FIRST_DAY: int = 1
ACCRUAL_LAST_DAY: int = 35
WINDOW_LENGTH_DAYS: int = ACCRUAL_LAST_DAY - ACCRUAL_FIRST_DAY + 1
POD_ANCHORED_FIRST_DAY: int = 8                 # sensitivity row 1, postoperative days 8 to 42
POD_ANCHORED_LAST_DAY: int = 42
PANEL_LAST_DAY: int = 42                        # the widest post-discharge day either window
                                                # can reach, because postoperative day 42 lands
                                                # at post-discharge day 42 minus the stay and
                                                # the stay is at least one day.

# 9.2, the adjusted share reaching 80% of baseline.
#
# THE ROW IS A COMPLETE-CASE LOGISTIC AND THE PLAN DOES NOT SAY OTHERWISE.  It is fitted on the
# episodes with an observed day in the recovery band and standardized to the whole cohort, so it
# assumes missingness at random given the episode-level covariate set.  The daily-deficit model
# meets the same missingness with weights and prices what is left with a delta shift; this row
# has neither, and adding an inverse-probability-of-observation weight here would be a NEW
# estimator, not a bug fix: it would need its own observation model at the EPISODE level rather
# than the day level, its own truncation rule, its own bootstrap leg and its own delta-shift
# companion to be worth the assumption it replaces, and none of the four is prespecified.  What
# this module does instead is refuse to hide the gap: the denominator the fit actually used
# travels to the boundary per group, and this sentence travels with it.
RECOVERY_FITTED_ON = (
    "the episodes with an observed day in post-discharge days 29 to 35, standardized to the "
    "whole cohort"
)
RECOVERY_MISSINGNESS_ASSUMPTION = (
    "missing at random given the episode-level covariate set, with no observation weight and no "
    "delta-shift companion, which is a stronger assumption than the daily-deficit model makes"
)
RECOVERY_THRESHOLD: float = 0.8
RECOVERY_FIRST_DAY: int = 29
RECOVERY_LAST_DAY: int = 35

# 3.7, the observation weights.
WEIGHT_TRUNCATION_LOW_PERCENTILE: float = 1.0
WEIGHT_TRUNCATION_HIGH_PERCENTILE: float = 99.0
LAG_WINDOW_DAYS: int = 7                        # days d minus 7 to d minus 1, strictly lagged

# 3.10, the baseline floor.  A SENSITIVITY, never an eligibility criterion: the primary applies
# no floor so that nobody is excluded for having been sedentary before surgery.
BASELINE_FLOOR_STEPS: int = 1000

# 3.11, the delta-shift tipping point.
DELTA_GRID: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
DELTA_EXTENSION_STEP: float = 0.5
DELTA_EXTENSION_LAST: float = 4.0
DELTA_APPLICATIONS: tuple[str, ...] = ("fusion only", "decompression only", "both groups")
DELTA_REPORTED_APPLICATION: str = "decompression only"
DELTA_REFERENCE_DEFICIT: float = 0.30

# 3.5, the descent triggers, stated as the tolerances they test.
GRADIENT_TOLERANCE: float = 1e-3
BOUNDARY_TOLERANCE: float = 1e-4
CORRELATION_CEILING: float = 0.99

# 3.9 and the node grammar.  Thousand steps lost divides the absolute shortfall by this.
STEPS_PER_THOUSAND: float = 1000.0

# 2.2, the split-baseline sensitivity's own minimum valid days in each half of the week.  Their
# sum is 7, exactly the primary rule's minimum, and the row is fitted on a SUBSET of the
# primary's set, never a superset.
SPLIT_BASELINE_MIN_WEEKDAY_DAYS: int = 5
SPLIT_BASELINE_MIN_WEEKEND_DAYS: int = 2

# The supplementary multiple-imputation row of section 6.
IMPUTATIONS: int = 20

# Numerical guards.  None of these is a modelling choice: they keep a logit finite and a
# covariance conditioned, and each is small enough that no reported decimal can move.
PROBABILITY_EPSILON: float = 1e-9
# The floor's numeric value belongs to `disclosure.py` and no module writes it into a comparison
# of its own.  The self-test needs the number itself to demonstrate that the true-count question
# and the rendered-cell question differ ON IT, so it is read from the module that owns it.
MIN_CELL_PROBE: int = MIN_CELL
FLOAT_TOLERANCE: float = 1e-9
MONOTONE_TOLERANCE: float = 1e-6
# The random-slope column is the post-discharge day CENTRED AND SCALED to roughly the unit
# interval.  A raw day index from 1 to 35 puts the slope variance five orders of magnitude below
# the intercept variance and the optimizer stalls on the scaling rather than on the data, which
# would fire trigger T1 for a numerical reason that has nothing to do with the fit.  Centring is
# a change of parameterisation and cannot move the marginal estimate.
DAY_CENTRE: float = 18.0
DAY_SCALE: float = 17.0
MONTE_CARLO_CHUNK_ROWS: int = 4096              # memory bound only; the answer is chunk-free


# ======================================================================================
# (3) Cost.  Four queries, all against `{DERIVED}`, none against a Controlled Tier table.
# ======================================================================================

USD_PER_TIB: float = 6.25                       # display only; enforcement is in bytes
BYTES_PER_GIB: int = 1024 ** 3

QUERY_KEYS: tuple[str, ...] = ("episodes", "panel", "guards", "parameters")

PLANNED_MAX_GB: Mapping[str, float] = MappingProxyType({
    "episodes": 1.0,
    "panel": 2.0,
    "guards": 1.0,
    "parameters": 0.5,
})
DRD_BUDGET_GB: float = 4.5


# ======================================================================================
# (4) SQL construction.
#
#     EVERY TEMPLATE IS A PLAIN, NON-f STRING WITH `{DERIVED}` INTACT, because the configuration
#     notebook's `_fill` substitutes the placeholder itself and raises on any residual
#     `{IDENTIFIER}`; an f-string would have eaten the braces before it ever saw them.  This
#     module's own constants reach a template through the `<<TOKEN>>` form, which cannot collide
#     with a brace and fails loudly rather than half-substituting a threshold into a query that
#     then runs.
#
#     NO IDENTIFIER AND NO DATE IS SELECTED.  `person_id` and `episode_id` are joined on inside
#     the query and are replaced on the way out by a dense surrogate index, and the calendar
#     alignment reaches the kernel as `day_of_week`, an integer from 1 to 7, rather than as a
#     date.  Controlled Tier dates are unshifted, so a date column is an identifier on its own;
#     the model never needs one, so it never sees one, and no later export path can leak one by
#     accident.
# ======================================================================================

_SQL_TOKEN = re.compile(r"<<([A-Z0-9_]+)>>")

_SQL_CONSTANTS: Mapping[str, Any] = MappingProxyType({
    "ACCRUAL_FIRST_DAY": ACCRUAL_FIRST_DAY,
    "ACCRUAL_LAST_DAY": ACCRUAL_LAST_DAY,
    "PANEL_LAST_DAY": PANEL_LAST_DAY,
    "POD_ANCHORED_FIRST_DAY": POD_ANCHORED_FIRST_DAY,
    "POD_ANCHORED_LAST_DAY": POD_ANCHORED_LAST_DAY,
    "RECOVERY_FIRST_DAY": RECOVERY_FIRST_DAY,
    "RECOVERY_LAST_DAY": RECOVERY_LAST_DAY,
    "BASELINE_FLOOR_STEPS": BASELINE_FLOOR_STEPS,
    "SPLIT_BASELINE_MIN_WEEKDAY_DAYS": SPLIT_BASELINE_MIN_WEEKDAY_DAYS,
    "SPLIT_BASELINE_MIN_WEEKEND_DAYS": SPLIT_BASELINE_MIN_WEEKEND_DAYS,
})


def _sql(template: str) -> str:
    """Substitute this module's `<<TOKEN>>` constants, leaving `{DERIVED}` untouched."""
    def swap(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name not in _SQL_CONSTANTS:
            raise DrdAnalysisError(
                f"a query template names the constant <<{name}>>, which this module does not "
                f"define. Add it to the locked constants above rather than typing the number "
                f"into the query."
            )
        return str(_SQL_CONSTANTS[name])
    out = _SQL_TOKEN.sub(swap, template)
    if "<<" in out or ">>" in out:
        raise DrdAnalysisError(
            "a query template still carries an unsubstituted token after substitution, so a "
            "constant would have reached BigQuery half-written. Nothing was submitted."
        )
    return out


_COLUMNS_MARKER = "-- @columns:"


def declared_columns(sql: str) -> tuple[str, ...]:
    """The result columns a query DECLARES, read off its own `-- @columns:` line.

    The line exists so that the Python readers below and the emitted SQL cannot drift apart
    without something failing on a laptop rather than in a Workbench session.  The self-test
    asserts the line is present exactly once, that every name on it is an explicit `AS name`
    alias in the query text, and that the frame reader for that query asks for exactly this set.
    """
    raw = sql.splitlines()
    starts = [i for i, line in enumerate(raw) if line.strip().startswith(_COLUMNS_MARKER)]
    if len(starts) != 1:
        raise DrdAnalysisError(
            f"a query carries {len(starts)} column-declaration lines and must carry exactly one"
        )
    first = starts[0]
    body = raw[first].split(_COLUMNS_MARKER, 1)[1]
    # A declaration long enough to wrap continues on the following comment lines, which is a
    # property of the line length and not of the query, so the reader follows it rather than
    # silently reading a truncated column set.
    for line in raw[first + 1:]:
        stripped = line.strip()
        if not stripped.startswith("--") or stripped.startswith(_COLUMNS_MARKER):
            break
        body += " " + stripped.lstrip("-").strip()
    names = tuple(name.strip() for name in body.split(",") if name.strip())
    if not names:
        raise DrdAnalysisError("a query declares no result columns")
    return names


# --------------------------------------------------------------------------------------
# The common head.  `features` is one row per ELIGIBLE episode, which is one row per
# participant because rung 13 of the attrition ladder takes the first eligible episode per
# person (DAG-SCHEMA 8.10).  The dense rank over `person_id` is therefore a bijection onto
# 1..n and is stable across the two queries that use it, which is what lets the panel and the
# episode frame be joined in the kernel without either of them carrying a key.
# --------------------------------------------------------------------------------------

_COHORT_HEAD = """
WITH cohort AS (
  SELECT
    f.episode_id                              AS episode_id,
    DENSE_RANK() OVER (ORDER BY f.person_id)  AS unit_index
  FROM `{DERIVED}.features` AS f
)
"""


def episodes_sql() -> str:
    """One row per analytic episode: the covariate set, and every baseline the ladder needs.

    `features` carries six of the eight prespecified alternative baselines.  It does NOT carry
    the weekday and weekend medians or their two day counts, which live on `baseline` alone
    (DAG-SCHEMA 8.8 against 8.10), so this query joins `baseline` for those four columns.  The
    join is on the episode key inside the query and costs nothing: `baseline` is one row per
    episode and the join is one to one.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: unit_index, procedure_group, region, fusion, age_at_index, sex_at_birth,
--           bmi_imputed, bmi_missing, charlson_ordinal, charlson_missing, los_days, index_year,
--           covid_era, device_family, device_changed, baseline_steps, n_valid_baseline_days,
--           meets_baseline_floor, baseline_steps_60_15, baseline_steps_30_1, baseline_steps_s1,
--           baseline_steps_s2, baseline_steps_s3, baseline_steps_s4, baseline_steps_weekday,
--           baseline_steps_weekend, n_valid_baseline_days_weekday,
--           n_valid_baseline_days_weekend, near_complete_window, n_analyzable_days_1_35,
--           at_risk_last_day
SELECT
  c.unit_index                          AS unit_index,
  f.procedure_group                     AS procedure_group,
  f.region                              AS region,
  f.fusion                              AS fusion,
  f.age_at_index                        AS age_at_index,
  f.sex_at_birth                        AS sex_at_birth,
  f.bmi_imputed                         AS bmi_imputed,
  f.bmi_missing                         AS bmi_missing,
  f.charlson_ordinal                    AS charlson_ordinal,
  f.charlson_missing                    AS charlson_missing,
  f.los_days                            AS los_days,
  f.index_year                          AS index_year,
  f.covid_era                           AS covid_era,
  f.device_family                       AS device_family,
  f.device_changed                      AS device_changed,
  f.baseline_steps                      AS baseline_steps,
  f.n_valid_baseline_days               AS n_valid_baseline_days,
  f.meets_baseline_floor                AS meets_baseline_floor,
  f.baseline_steps_60_15                AS baseline_steps_60_15,
  f.baseline_steps_30_1                 AS baseline_steps_30_1,
  f.baseline_steps_s1                   AS baseline_steps_s1,
  f.baseline_steps_s2                   AS baseline_steps_s2,
  f.baseline_steps_s3                   AS baseline_steps_s3,
  f.baseline_steps_s4                   AS baseline_steps_s4,
  b.baseline_steps_weekday              AS baseline_steps_weekday,
  b.baseline_steps_weekend              AS baseline_steps_weekend,
  b.n_valid_baseline_days_weekday       AS n_valid_baseline_days_weekday,
  b.n_valid_baseline_days_weekend       AS n_valid_baseline_days_weekend,
  f.near_complete_window                AS near_complete_window,
  f.n_analyzable_days_1_35              AS n_analyzable_days_1_35,
  f.at_risk_last_day                    AS at_risk_last_day
FROM cohort AS c
JOIN `{DERIVED}.features` AS f USING (episode_id)
JOIN `{DERIVED}.baseline`  AS b USING (episode_id)
ORDER BY unit_index
""")


def panel_sql() -> str:
    """The person-day panel the model is fitted on and integrated over.

    Days 1 to <<PANEL_LAST_DAY>> only.  The accrual window is days 1 to 35 and the
    postoperative-day-anchored sensitivity reaches postoperative day 42, which lands at
    post-discharge day 42 minus the length of stay and therefore never above 41, so this bound
    covers both windows and prunes the day partitions above it.  The `guards` query proves the
    bound is not truncating anything rather than leaving it asserted in a comment.

    `deficit` arrives NULL on a non-analyzable day and stays NULL.  Nothing in this query, and
    nothing downstream of it, substitutes a zero.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: unit_index, post_discharge_day, postoperative_day, day_of_week, is_weekend, steps,
--           valid_wear, valid_wear_s1, valid_wear_s2, valid_wear_s3, valid_wear_s4,
--           is_analyzable, is_censored, is_inpatient, in_accrual_window,
--           in_pod_anchored_window, deficit, deficit_untruncated, lagged_wear_fraction
SELECT
  c.unit_index                          AS unit_index,
  p.post_discharge_day                  AS post_discharge_day,
  p.postoperative_day                   AS postoperative_day,
  p.day_of_week                         AS day_of_week,
  p.is_weekend                          AS is_weekend,
  p.steps                               AS steps,
  p.valid_wear                          AS valid_wear,
  p.valid_wear_s1                       AS valid_wear_s1,
  p.valid_wear_s2                       AS valid_wear_s2,
  p.valid_wear_s3                       AS valid_wear_s3,
  p.valid_wear_s4                       AS valid_wear_s4,
  p.is_analyzable                       AS is_analyzable,
  p.is_censored                         AS is_censored,
  p.is_inpatient                        AS is_inpatient,
  p.in_accrual_window                   AS in_accrual_window,
  p.in_pod_anchored_window              AS in_pod_anchored_window,
  p.deficit                             AS deficit,
  p.deficit_untruncated                 AS deficit_untruncated,
  p.lagged_wear_fraction                AS lagged_wear_fraction
FROM cohort AS c
JOIN `{DERIVED}.drd_daily` AS p USING (episode_id)
WHERE p.post_discharge_day BETWEEN <<ACCRUAL_FIRST_DAY>> AND <<PANEL_LAST_DAY>>
ORDER BY unit_index, post_discharge_day
""")


def guards_sql() -> str:
    """The five counts that decide whether the estimator may run at all.

    Each is expected to be exactly zero and each is a stop condition, not a diagnostic.  The
    first two are the zero-imputation check in BOTH directions, because the failure has two
    shapes and only one of them is the famous one: a deficit present on a day the panel calls
    unobserved, and a deficit absent on a day it calls observed.  The third proves the day bound
    of the panel query truncates nothing.  The fourth catches a normalized activity that went
    missing where the deficit did not, which would mean the two were computed from different
    step columns.  The fifth is the specific shape that destroys the estimand: a literal zero
    deficit sitting on an unobserved day, which asserts the participant walked at or above their
    own preoperative baseline on a day nobody measured.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: n_deficit_on_unobserved_day, n_missing_deficit_on_observed_day,
--           n_pod_window_beyond_panel, n_activity_missing_on_observed_day,
--           n_zero_imputed_deficit, n_nonpositive_baseline, n_panel_rows, n_units
SELECT
  COUNTIF(p.deficit IS NOT NULL AND NOT p.is_analyzable)
                                        AS n_deficit_on_unobserved_day,
  COUNTIF(p.deficit IS NULL AND p.is_analyzable)
                                        AS n_missing_deficit_on_observed_day,
  COUNTIF(p.in_pod_anchored_window AND p.post_discharge_day > <<PANEL_LAST_DAY>>)
                                        AS n_pod_window_beyond_panel,
  COUNTIF(p.is_analyzable AND p.normalized_activity IS NULL)
                                        AS n_activity_missing_on_observed_day,
  COUNTIF(p.deficit = 0 AND NOT p.is_analyzable)
                                        AS n_zero_imputed_deficit,
  (SELECT COUNTIF(b.baseline_steps <= 0) FROM `{DERIVED}.baseline` AS b)
                                        AS n_nonpositive_baseline,
  COUNT(*)                              AS n_panel_rows,
  COUNT(DISTINCT c.unit_index)          AS n_units
FROM cohort AS c
JOIN `{DERIVED}.drd_daily` AS p USING (episode_id)
""")


def parameters_sql() -> str:
    """The one row of build parameters, so the report can name what the panel was built under."""
    return """
-- @columns: junction_map, primary_wear_definition, seed
SELECT
  junction_map                          AS junction_map,
  primary_wear_definition               AS primary_wear_definition,
  seed                                  AS seed
FROM `{DERIVED}.build_params`
"""


def build_sql() -> dict[str, str]:
    """Every query this module runs, keyed by `QUERY_KEYS`, built once and priced together."""
    return {
        "episodes": episodes_sql(),
        "panel": panel_sql(),
        "guards": guards_sql(),
        "parameters": parameters_sql(),
    }


# ======================================================================================
# (5) The pure numerics.
#
#     Everything in this block is a function of its arguments and nothing else: no global
#     state, no random draw that is not passed a generator, no query.  That is what makes the
#     self-test able to drive all of it against synthetic data with a known answer.
# ======================================================================================


def daily_deficit(steps: Any, baseline: Any) -> np.ndarray:
    """`max(0, 1 - steps / baseline)`, the daily deficit, on arrays that carry nulls.

    THE ONE PROPERTY THAT MATTERS HERE IS WHAT HAPPENS TO A NULL.  A missing step count returns
    a missing deficit, never a zero.  A zero deficit is the assertion that the participant
    walked at or above their own preoperative baseline that day, which is the most favourable
    possible completion of the window, and it is exactly the imputation the model-and-integrate
    estimator exists to avoid.  A missing baseline likewise returns missing: `baseline` is NULL
    and never zero throughout this project, because a zero baseline makes the ratio infinite and
    the deficit silently one on every day, manufacturing a maximal debt out of an absence of
    data.

    A baseline that is present and not strictly positive is a bug upstream, not a disclosure
    decision and not a number to clip, so it raises.
    """
    steps_a = np.asarray(steps, dtype=float)
    base_a = np.asarray(baseline, dtype=float)
    present = np.isfinite(base_a)
    if np.any(present & (base_a <= 0)):
        raise DrdAnalysisError(
            "a baseline of zero or below reached the deficit function. A baseline is NULL and "
            "never zero in this project, because a zero denominator makes the deficit one on "
            "every day and manufactures a maximal recovery debt out of missing data."
        )
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = steps_a / base_a
    return np.where(np.isfinite(ratio), np.maximum(0.0, 1.0 - ratio), np.nan)


def daily_deficit_untruncated(steps: Any, baseline: Any) -> np.ndarray:
    """`1 - steps / baseline` with the truncation removed, so days above baseline offset days
    below.  Sensitivity row 10, and the one row whose response can leave the unit interval."""
    steps_a = np.asarray(steps, dtype=float)
    base_a = np.asarray(baseline, dtype=float)
    present = np.isfinite(base_a)
    if np.any(present & (base_a <= 0)):
        raise DrdAnalysisError("a baseline of zero or below reached the deficit function")
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = steps_a / base_a
    return np.where(np.isfinite(ratio), 1.0 - ratio, np.nan)


def _cube_positive_part(u: np.ndarray) -> np.ndarray:
    return np.where(u > 0.0, u ** 3, 0.0)


def restricted_cubic_spline(x: Any, knots: Sequence[float]) -> np.ndarray:
    """The Harrell restricted cubic spline basis on FIXED knots.  Returns `len(knots) - 1`
    columns, the first of which is the linear term.

    The knots are arguments and are always one of the locked tuples of ANALYSIS-PLAN 3.6.  They
    are never derived from the data: a quantile-placed knot would make the basis depend on the
    observed day distribution, and then a sensitivity row would differ from the primary in the
    basis as well as in the thing it varies, which is the one property the ladder needs.
    """
    t = np.asarray(knots, dtype=float)
    if t.size < 3:
        raise DrdAnalysisError("a restricted cubic spline needs at least three knots")
    if np.any(np.diff(t) <= 0):
        raise DrdAnalysisError("spline knots must be strictly increasing")
    values = np.asarray(x, dtype=float)
    k = t.size
    columns = [values]
    denominator = (t[-1] - t[0]) ** 2
    spread = t[-1] - t[-2]
    for j in range(k - 2):
        term = (
            _cube_positive_part(values - t[j])
            - _cube_positive_part(values - t[k - 2]) * (t[k - 1] - t[j]) / spread
            + _cube_positive_part(values - t[k - 1]) * (t[k - 2] - t[j]) / spread
        ) / denominator
        columns.append(term)
    return np.column_stack(columns)


def spline_degrees_of_freedom(knots: Sequence[float]) -> int:
    """The number of basis columns a knot set produces, which is what `model_fit.spline_df`
    reports.  One fewer than the knot count, because the basis is restricted to be linear beyond
    the outer knots."""
    return len(knots) - 1


def expit(x: Any) -> np.ndarray:
    """The logistic function, written so that a large negative argument cannot overflow."""
    values = np.asarray(x, dtype=float)
    out = np.empty_like(values)
    positive = values >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-values[positive]))
    exponent = np.exp(values[~positive])
    out[~positive] = exponent / (1.0 + exponent)
    return out


def logit(p: Any) -> np.ndarray:
    """The log odds, with the argument held off both boundaries so the result stays finite.

    The clipping is numerical and not a modelling choice: the delta shift of ANALYSIS-PLAN 3.11
    is defined on this scale, and a fitted probability that has landed exactly on a boundary
    would otherwise send the whole shifted arm to an infinity that no interval could report.
    """
    values = np.clip(np.asarray(p, dtype=float), PROBABILITY_EPSILON, 1.0 - PROBABILITY_EPSILON)
    return np.log(values / (1.0 - values))


def scaled_day(day: Any) -> np.ndarray:
    """Post-discharge day centred and scaled, for the RANDOM-EFFECT design only.

    A change of parameterisation, not of model: the fixed-effect basis keeps the raw day so the
    knots stay the plan's knots, while the random slope is expressed on a scale where its
    variance is comparable with the intercept's.  Left on the raw day index the optimizer stalls
    on the scaling rather than on the data and fires the non-convergence trigger for a reason
    that has nothing to do with the fit.
    """
    return (np.asarray(day, dtype=float) - DAY_CENTRE) / DAY_SCALE


def random_effect_standard_deviation(covariance: Any, day: Any) -> np.ndarray:
    """The standard deviation of `z'b` at each day, where `z` is the random-effect design row.

    `z'b` with `b` normal is univariate normal with variance `z' Sigma z`, so the whole
    two-dimensional draw reduces to one standard normal scaled by this.  That reduction is what
    makes the common random numbers of ANALYSIS-PLAN 3.3 exact rather than approximate: one
    stream of standard normals serves every day, every group and every covariate profile, so
    most of the Monte Carlo noise cancels in the contrast instead of accumulating over 35 days.
    """
    sigma = np.atleast_2d(np.asarray(covariance, dtype=float))
    days = np.asarray(day, dtype=float)
    if sigma.shape == (1, 1):
        return np.full(days.shape, math.sqrt(max(float(sigma[0, 0]), 0.0)))
    if sigma.shape != (2, 2):
        raise DrdAnalysisError(
            "the random-effect covariance is neither an intercept variance nor an intercept "
            "and slope covariance, and this module knows no third structure"
        )
    z = scaled_day(days)
    variance = sigma[0, 0] + 2.0 * sigma[0, 1] * z + sigma[1, 1] * z * z
    return np.sqrt(np.maximum(variance, 0.0))


def monte_carlo_marginal_mean(
    eta: Any,
    day: Any,
    covariance: Any,
    *,
    inverse_link: Callable[[np.ndarray], np.ndarray],
    draws: int,
    rng: np.random.Generator,
    chunk_rows: int = MONTE_CARLO_CHUNK_ROWS,
) -> np.ndarray:
    """Integrate the conditional mean over the estimated random-effect distribution.

    TRAP ONE, RULE TWO, OF ANALYSIS-PLAN 3.3.  In a mixed model with a nonlinear link the
    prediction at a zero random effect is the CONDITIONAL mean for a median-random-effect
    episode; the MARGINAL mean of the population is the integral of the conditional mean over
    the random-effect distribution, and the marginal mean is the estimand.  Setting the random
    effect to zero is not an approximation of that integral, it is a different quantity, and the
    two differ by exactly the amount the link bends.

    The draws are COMMON: one stream of `draws` standard normals is generated once and reused
    across every row, so a contrast computed as a difference of two calls with the same
    generator state differs only in its linear predictor and the Monte Carlo noise cancels.
    Rows are processed in chunks for memory only; the returned numbers do not depend on the
    chunk size, and the self-test pins that.
    """
    if draws < 1:
        raise DrdAnalysisError("the Monte Carlo marginalization needs at least one draw")
    linear = np.asarray(eta, dtype=float)
    sd = random_effect_standard_deviation(covariance, day)
    if sd.shape != linear.shape:
        raise DrdAnalysisError("the random-effect scale and the linear predictor disagree in "
                               "shape, so a day has been paired with the wrong row")
    normals = rng.standard_normal(draws)
    out = np.empty_like(linear)
    for start in range(0, linear.size, max(1, int(chunk_rows))):
        stop = min(start + max(1, int(chunk_rows)), linear.size)
        block = linear[start:stop, None] + sd[start:stop, None] * normals[None, :]
        out[start:stop] = inverse_link(block).mean(axis=1)
    return out


def weighted_mean(values: Any, weights: Any) -> float:
    """A weighted mean that refuses an empty or zero-weight set rather than returning a NaN."""
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    keep = np.isfinite(v) & np.isfinite(w) & (w > 0)
    if not np.any(keep):
        raise DrdAnalysisError("a weighted mean was asked of no observations with positive "
                               "weight, which is a missing stratum and not a zero")
    return float(np.sum(v[keep] * w[keep]) / np.sum(w[keep]))


def stabilized_weights(
    probability: Any,
    *,
    marginal: float,
    low_percentile: float = WEIGHT_TRUNCATION_LOW_PERCENTILE,
    high_percentile: float = WEIGHT_TRUNCATION_HIGH_PERCENTILE,
) -> tuple[np.ndarray, dict[str, float]]:
    """`w = p_marginal / p_hat`, truncated at the prespecified percentiles of its own
    distribution.  ANALYSIS-PLAN 3.7 requires the truncation points, the weight mean and the
    weight range to be reported, so they come back beside the weights rather than being
    recomputed by whoever prints them."""
    p = np.asarray(probability, dtype=float)
    if np.any(~np.isfinite(p)) or np.any(p <= 0) or np.any(p > 1):
        raise DrdAnalysisError(
            "an observation probability outside the open unit interval reached the weights, so "
            "a weight would be infinite or negative. The observation model did not fit."
        )
    raw = float(marginal) / p
    low = float(np.percentile(raw, low_percentile))
    high = float(np.percentile(raw, high_percentile))
    truncated = np.clip(raw, low, high)
    summary = {
        "marginal probability": float(marginal),
        "truncation low": low,
        "truncation high": high,
        "mean": float(truncated.mean()),
        "minimum": float(truncated.min()),
        "maximum": float(truncated.max()),
        "share truncated": float(np.mean((raw < low) | (raw > high))),
    }
    return truncated, summary


# ======================================================================================
# (6) The mean structure.
#
#     ANALYSIS-PLAN 3.6 fixes it completely.  The collapse level decides which of the fusion and
#     region terms are present, and the collapse level was DECIDED BY `03_cohort.py` on the
#     Phase 3 attrition ladder, before any model was fit.  This module READS it.  It does not
#     re-decide it and it does not hardcode four groups.
# ======================================================================================


class ModelSpec:
    """Which terms of the locked mean structure this collapse level admits."""

    def __init__(self, level: str, groups: Sequence[str]) -> None:
        if level not in COLLAPSE_LEVELS:
            raise DrdAnalysisError(
                f"the collapse level {level!r} is not one of the four the plan defines. It is "
                f"decided once, on the attrition ladder, and this module reads it."
            )
        self.level = level
        self.groups: tuple[str, ...] = tuple(groups)
        # Level 1 carries the fusion-by-region interaction and the region-specific day curves.
        # Level 2 is fusion versus decompression region-ADJUSTED, with no region interaction.
        # Level 3 is one pooled curve with no between-group contrast at all.
        self.has_fusion: bool = level in ("four_group", "two_group")
        self.has_region: bool = level in ("four_group", "two_group")
        self.has_region_interaction: bool = level == "four_group"
        self.estimable: bool = level in ("four_group", "two_group", "single_group")

    @property
    def contrasts(self) -> tuple[str, ...]:
        """The contrasts this level can estimate, in Figure 3 block 1 order."""
        if self.level == "four_group":
            return CONTRAST_SLUGS
        if self.level == "two_group":
            return (PRIMARY_CONTRAST_SLUG,)
        return ()

    def __repr__(self) -> str:                       # pragma: no cover - a debugging aid
        return f"ModelSpec(level={self.level!r}, groups={self.groups!r})"


def fold_device_families(families: Sequence[str]) -> tuple[dict[str, str], dict[str, int]]:
    """Fold every device family whose episode count is not disclosable into other or unknown.

    ANALYSIS-PLAN 3.6, rule 5.  The folding runs on a COUNT and never on an estimate, and it
    happens once.  The fourteen-name family vocabulary and the first-token rule that produced
    these strings live in the derived build, so nothing here re-derives a family from a model
    string; this only merges the levels a model cannot support.
    """
    counts: dict[str, int] = {}
    for name in families:
        key = str(name)
        counts[key] = counts.get(key, 0) + 1
    mapping = {name: (name if disclosable(n) else "other_or_unknown")
               for name, n in counts.items()}
    mapping["other_or_unknown"] = "other_or_unknown"
    return mapping, counts


class DesignBuilder:
    """The locked mean structure, built once from the episode frame it will be fitted on.

    THE FACTOR LEVELS ARE FIXED BY THE FRAME PASSED HERE, not by whatever frame a prediction is
    later asked for.  That is the whole reason this is an object: the g-computation sets the
    entire cohort to one procedure group and predicts, and if the level set were re-derived at
    prediction time a group with no episodes of some device family would silently lose a column
    and the two predictions would not be on the same scale.

    Columns that are structurally constant on the full accrual grid are dropped once, here, and
    the same drop is applied to every later matrix.  A constant column is a rank deficiency, not
    a finding: it means the cohort carries one sex, or one device family, or one region, and the
    model cannot estimate a contrast that does not exist in the data.  Dropping it is a
    computational property of the design and is recorded.
    """

    def __init__(
        self,
        episodes: pd.DataFrame,
        spec: ModelSpec,
        *,
        day_knots: Sequence[float] = DAY_KNOTS,
        include_log_baseline: bool = False,
        include_baseline_steps: bool = False,
        include_covariates: bool = True,
    ) -> None:
        required = ("region", "fusion", "age_at_index", "sex_at_birth", "bmi_imputed",
                    "bmi_missing", "charlson_ordinal", "charlson_missing", "los_days",
                    "index_year", "covid_era", "device_family", "baseline_steps")
        missing = [name for name in required if name not in episodes.columns]
        if missing:
            raise DrdAnalysisError(f"the episode frame is missing the covariate column(s) "
                                   f"{missing}, which the locked mean structure names")
        self.spec = spec
        self.day_knots = tuple(float(k) for k in day_knots)
        self.n_units = int(len(episodes))
        self.include_log_baseline = bool(include_log_baseline)
        self.include_baseline_steps = bool(include_baseline_steps)
        # `include_covariates=False` BUILDS THE UNADJUSTED DESIGN OF STROBE ITEM 16(a), and it
        # is the same mean structure with one block deleted rather than a second estimator.
        # What comes out is the locked covariate table of ANALYSIS-PLAN 3.6: age, sex assigned
        # at birth, body mass index and its missing indicator, comorbidity burden and its
        # missing indicator, log length of stay, index year, the COVID-19 era indicator and
        # device family.  What stays is everything the estimand is DEFINED on and could not be
        # standardized without: the intercept, the post-discharge-day spline, the procedure
        # group terms and their day interactions, the region terms the collapse level admits,
        # and the day-of-week fixed effect.  Those are not confounders held fixed, they are the
        # axes the g-computation integrates over (3.8, 5.5); deleting them would change the
        # estimand rather than unadjust it, and at the four-group level deleting region would
        # delete the groups themselves.  A caller that asks for no covariates and then asks for
        # one of the two the plan admits by name is asking for two incompatible things at once.
        self.include_covariates = bool(include_covariates)
        if not self.include_covariates and (self.include_log_baseline
                                            or self.include_baseline_steps):
            raise DrdAnalysisError(
                "a covariate-free design cannot also carry a baseline-steps term: the "
                "log-baseline spline of the plan's 3.9 and the baseline-adjusted row of its "
                "section 6 are covariates, so removing the covariate set removes them too."
            )

        self._region_is_lumbar = (episodes["region"].astype(str).to_numpy() == "lumbar")
        self._fusion = episodes["fusion"].astype(bool).to_numpy()
        self._baseline = episodes["baseline_steps"].astype(float).to_numpy()
        self.device_map, self.device_counts = fold_device_families(
            episodes["device_family"].astype(str).tolist())
        self._covariates, self._covariate_names = self._build_covariates(episodes)

        # The keep mask is computed on the FULL accrual grid, which does not depend on which
        # days were observed, so a bootstrap resample cannot change which columns exist.
        grid_units = np.repeat(np.arange(self.n_units), WINDOW_LENGTH_DAYS)
        grid_days = np.tile(np.arange(ACCRUAL_FIRST_DAY, ACCRUAL_LAST_DAY + 1), self.n_units)
        grid_dow = ((grid_units + grid_days) % 7) + 1
        full, names = self._assemble(grid_units, grid_days, grid_dow, None, None)
        self._keep = self._constant_mask(full)
        self.names: tuple[str, ...] = tuple(n for n, k in zip(names, self._keep) if k)
        self.dropped_names: tuple[str, ...] = tuple(
            n for n, k in zip(names, self._keep) if not k)
        # The episode-level matrix carries its own mask, computed ONCE on the natural frame and
        # never on the frame a prediction asks for.  Recomputing it per call was a real defect:
        # setting the whole cohort to one procedure group makes the fusion column constant, the
        # column would be dropped from the prediction and not from the fit, and the two matrices
        # would silently stop being the same model.
        episode_full, episode_names = self._assemble_episode(
            np.arange(self.n_units), None, None)
        self._episode_keep = self._constant_mask(episode_full)
        self.episode_names: tuple[str, ...] = tuple(
            n for n, k in zip(episode_names, self._episode_keep) if k)

    @staticmethod
    def _constant_mask(matrix: np.ndarray) -> np.ndarray:
        """Which columns survive as an estimable basis.

        TWO KINDS OF DEFICIENCY, BOTH DROPPED HERE AND BOTH RECORDED.  A structurally CONSTANT
        column means the cohort holds one sex, one device family or one region, and a contrast
        that does not exist in the data cannot be estimated.  A column that is an exact linear
        combination of the columns before it means two covariates are aliased in this cohort,
        which is the same fact wearing a different hat.  Neither is a finding and neither is a
        reason to descend the family ladder: a rank-deficient design makes the optimizer fail
        for a reason that has nothing to do with the model, and firing the non-convergence
        trigger on it would descend a rung on an accident of the covariate frame.

        Columns are considered IN ORDER, so the earliest survives an alias and the later one is
        dropped.  The order is the locked mean structure's own order, which puts the intercept,
        the day basis and the procedure-group terms ahead of every covariate, so a collision can
        never cost the estimand a term it is defined on.
        """
        keep = np.ones(matrix.shape[1], dtype=bool)
        for j in range(1, matrix.shape[1]):
            column = matrix[:, j]
            if float(np.nanmax(column) - np.nanmin(column)) <= FLOAT_TOLERANCE:
                keep[j] = False
        columns = np.where(keep)[0]
        # The columns are scaled to unit length before the Gram is formed, because the locked
        # covariate set mixes an indicator with a cubed age term and a raw Gram would make the
        # tolerance mean something different in every column.
        block = np.asarray(matrix[:, columns], dtype=float)
        norms = np.sqrt(np.sum(block * block, axis=0))
        norms[norms <= 0] = 1.0
        block = block / norms
        gram = block.T @ block
        chosen: list[int] = []
        for position, j in enumerate(columns):
            own = float(gram[position, position])
            if own <= FLOAT_TOLERANCE:
                keep[j] = False
                continue
            if chosen:
                block = gram[np.ix_(chosen, chosen)]
                cross = gram[np.ix_(chosen, [position])]
                try:
                    residual = own - float(np.squeeze(cross.T @ np.linalg.solve(block, cross)))
                except np.linalg.LinAlgError:      # pragma: no cover - a singular kept block
                    residual = 0.0
            else:
                residual = own
            if residual / own <= 1e-8:
                keep[j] = False
                continue
            chosen.append(position)
        return keep

    # -- the episode-level covariate block, built once -----------------------------------
    def _build_covariates(self, episodes: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
        if not self.include_covariates:
            # An EMPTY BLOCK, not a block of zeros and not an omitted concatenation.  A zero
            # column would be dropped by the constant mask anyway, but it would first count
            # against the rank checks and be reported as a dropped column, which would make an
            # intentional absence look like a rank deficiency the cohort caused.
            return np.empty((int(len(episodes)), 0), dtype=float), []
        columns: list[np.ndarray] = []
        names: list[str] = []

        age = episodes["age_at_index"].astype(float).to_numpy()
        age_missing = ~np.isfinite(age)
        # The plan gives BMI a missing indicator plus median substitution and is silent on a
        # null age, which DAG-SCHEMA 8.10 says happens when the birth date is null.  The same
        # rule is transposed rather than a new one invented, and the substitution is recorded.
        if np.all(age_missing):
            filled = np.zeros_like(age)
        else:
            filled = np.where(age_missing, float(np.nanmedian(age)), age)
        columns.append(restricted_cubic_spline(filled, AGE_KNOTS))
        names += [f"age spline {i + 1}" for i in range(spline_degrees_of_freedom(AGE_KNOTS))]
        columns.append(age_missing.astype(float)[:, None])
        names.append("age missing")

        sex = episodes["sex_at_birth"].astype(str).to_numpy()
        for level in SEX_LEVELS:
            if level == SEX_REFERENCE:                     # NAMED, not positional. The omitted
                continue                                   # level is the one both arms name.
            columns.append((sex == level).astype(float)[:, None])
            names.append(f"sex {level}")

        bmi = episodes["bmi_imputed"].astype(float).to_numpy()
        columns.append(restricted_cubic_spline(bmi, BMI_KNOTS))
        names += [f"bmi spline {i + 1}" for i in range(spline_degrees_of_freedom(BMI_KNOTS))]
        columns.append(episodes["bmi_missing"].astype(bool).to_numpy().astype(float)[:, None])
        names.append("bmi missing")

        charlson = episodes["charlson_ordinal"].astype(str).to_numpy()
        for level in CHARLSON_LEVELS[1:]:                  # zero is the reference
            columns.append((charlson == level).astype(float)[:, None])
            names.append(f"charlson {level}")
        columns.append(episodes["charlson_missing"].astype(bool).to_numpy().astype(float)[:, None])
        names.append("charlson missing")

        los = episodes["los_days"].astype(float).to_numpy()
        columns.append(np.log1p(np.maximum(los, 0.0))[:, None])
        names.append("log one plus stay")

        year = episodes["index_year"].astype(float).to_numpy()
        columns.append((year - float(np.median(year)))[:, None])
        names.append("index year")
        columns.append(episodes["covid_era"].astype(bool).to_numpy().astype(float)[:, None])
        names.append("covid era")

        family = np.array([self.device_map[str(f)]
                           for f in episodes["device_family"].astype(str)], dtype=object)
        levels = sorted({str(f) for f in family} - {"other_or_unknown"})
        for level in levels:
            columns.append((family == level).astype(float)[:, None])
            names.append(f"device {level}")

        if self.include_baseline_steps:
            base = episodes["baseline_steps"].astype(float).to_numpy()
            columns.append(((base - float(np.median(base))) / STEPS_PER_THOUSAND)[:, None])
            names.append("baseline steps")
        if self.include_log_baseline:
            base = np.maximum(episodes["baseline_steps"].astype(float).to_numpy(), 1.0)
            columns.append(restricted_cubic_spline(np.log(base), np.log(LOG_BASELINE_KNOTS)))
            names += [f"log baseline spline {i + 1}"
                      for i in range(spline_degrees_of_freedom(LOG_BASELINE_KNOTS))]

        return np.column_stack(columns), names

    # -- assembly ------------------------------------------------------------------------
    def _fusion_vector(self, unit_pos: np.ndarray, fusion: bool | None) -> np.ndarray:
        if fusion is None:
            return self._fusion[unit_pos].astype(float)
        return np.full(unit_pos.shape, 1.0 if fusion else 0.0)

    def _region_vector(self, unit_pos: np.ndarray, region: str | None) -> np.ndarray:
        if region is None:
            return self._region_is_lumbar[unit_pos].astype(float)
        if region not in REGIONS:
            raise DrdAnalysisError(f"{region!r} is not one of the analysis regions")
        return np.full(unit_pos.shape, 1.0 if region == "lumbar" else 0.0)

    def _assemble(self, unit_pos: np.ndarray, day: np.ndarray, dow: np.ndarray,
                  fusion: bool | None, region: str | None) -> tuple[np.ndarray, list[str]]:
        n = unit_pos.size
        columns: list[np.ndarray] = [np.ones((n, 1))]
        names: list[str] = ["intercept"]

        basis = restricted_cubic_spline(day, self.day_knots)
        columns.append(basis)
        names += [f"day spline {i + 1}" for i in range(basis.shape[1])]

        fusion_vec = self._fusion_vector(unit_pos, fusion)
        region_vec = self._region_vector(unit_pos, region)

        if self.spec.has_fusion:
            columns.append(fusion_vec[:, None])
            names.append("fusion")
            columns.append(basis * fusion_vec[:, None])
            names += [f"day spline {i + 1} by fusion" for i in range(basis.shape[1])]
        if self.spec.has_region:
            columns.append(region_vec[:, None])
            names.append("region lumbar")
        if self.spec.has_region_interaction:
            columns.append(basis * region_vec[:, None])
            names += [f"day spline {i + 1} by region" for i in range(basis.shape[1])]
            columns.append((fusion_vec * region_vec)[:, None])
            names.append("fusion by region")

        dow_values = np.asarray(dow, dtype=int)
        for level in range(1, 8):
            if level == DAY_OF_WEEK_REFERENCE:
                continue
            columns.append((dow_values == level).astype(float)[:, None])
            names.append(f"day of week {level}")

        columns.append(self._covariates[unit_pos, :])
        names += list(self._covariate_names)
        return np.column_stack(columns), names

    def matrix(self, unit_pos: Any, day: Any, dow: Any, *,
               fusion: bool | None = None, region: str | None = None) -> np.ndarray:
        """The day-level model matrix for these rows, with the fixed column set."""
        positions = np.asarray(unit_pos, dtype=int)
        full, _ = self._assemble(positions, np.asarray(day, dtype=float),
                                 np.asarray(dow, dtype=int), fusion, region)
        return full[:, self._keep]

    def _assemble_episode(self, unit_pos: np.ndarray, fusion: bool | None,
                          region: str | None) -> tuple[np.ndarray, list[str]]:
        positions = np.asarray(unit_pos, dtype=int)
        n = positions.size
        columns: list[np.ndarray] = [np.ones((n, 1))]
        names: list[str] = ["intercept"]
        fusion_vec = self._fusion_vector(positions, fusion)
        region_vec = self._region_vector(positions, region)
        if self.spec.has_fusion:
            columns.append(fusion_vec[:, None])
            names.append("fusion")
        if self.spec.has_region:
            columns.append(region_vec[:, None])
            names.append("region lumbar")
        if self.spec.has_region_interaction:
            columns.append((fusion_vec * region_vec)[:, None])
            names.append("fusion by region")
        columns.append(self._covariates[positions, :])
        names += list(self._covariate_names)
        return np.column_stack(columns), names

    def episode_matrix(self, unit_pos: Any, *, fusion: bool | None = None,
                       region: str | None = None) -> tuple[np.ndarray, tuple[str, ...]]:
        """The episode-level matrix, with no day terms, for the two endpoints that are one
        number per episode: the share reaching 80% of baseline and the complete-window direct
        regression.  It carries the same covariate set and the same fusion and region terms the
        collapse level admits, so the standardization is the same standardization."""
        matrix, _ = self._assemble_episode(np.asarray(unit_pos, dtype=int), fusion, region)
        return matrix[:, self._episode_keep], self.episode_names


# ======================================================================================
# (7) The model family ladder.
#
#     ANALYSIS-PLAN 3.5.  The response is a daily deficit bounded in [0, 1] with genuine mass at
#     BOTH ends: at zero because a participant at or above baseline is common, especially late
#     in the window, and at one because a day with zero recorded steps on a worn device is real
#     and is exactly the signal of interest.  A family that cannot represent both boundary
#     masses will misplace the estimand, which is why the ladder starts where it starts.
#
#     THE LADDER IS WALKED TOP DOWN AND STOPS AT THE FIRST RUNG THAT FITS CLEANLY.  A rung is
#     never revisited after the estimate it produced has been seen, and every descent trigger is
#     a computational property of the fit or of the environment.  `RungFailure` refuses any
#     trigger outside the plan's five, so there is no expressible way to descend on a number.
# ======================================================================================


class _DeficitModel:
    """What every rung must be able to do, so the g-computation is written once."""

    rung: Mapping[str, Any]
    residual_structure: str
    weights_applied: bool
    diagnostics: dict[str, Any]

    def predict(self, *, design: np.ndarray | None, day: np.ndarray, group: np.ndarray,
                rng: np.random.Generator, draws: int) -> np.ndarray:
        raise NotImplementedError                    # pragma: no cover


class _LinearPredictorModel(_DeficitModel):
    """Any rung whose fitted mean is a link applied to a linear predictor.

    Rungs 1, 2 and 4 carry random effects and are marginalized by Monte Carlo.  Rung 3 is a
    MARGINAL model already, so it needs no marginalization at all and its `covariance` is None;
    that is a property of estimating equations rather than a shortcut, and the plan says so.
    """

    def __init__(self, rung: Mapping[str, Any], *, coefficients: np.ndarray,
                 covariance_re: np.ndarray | None, residual_structure: str,
                 weights_applied: bool, truncate: bool, diagnostics: Mapping[str, Any]) -> None:
        self.rung = rung
        self.coefficients = np.asarray(coefficients, dtype=float)
        self.covariance_re = None if covariance_re is None else np.atleast_2d(
            np.asarray(covariance_re, dtype=float))
        self.residual_structure = residual_structure
        self.weights_applied = bool(weights_applied)
        self.truncate = bool(truncate)
        self.diagnostics = dict(diagnostics)

    def inverse_link(self, eta: np.ndarray) -> np.ndarray:
        if self.rung["link"] == "logit":
            return expit(eta)
        if self.truncate:
            # Rung 4 fits the deficit directly on the identity scale and truncates fitted values
            # to the unit interval BEFORE integration.  The truncation is itself a nonlinearity,
            # which is why this rung is still marginalized by Monte Carlo rather than evaluated
            # at a zero random effect: clipping the conditional mean is not the mean of the
            # clipped values, and the difference runs in the direction that understates the
            # debt for the same Jensen reason the deficit function does.
            return np.clip(eta, 0.0, 1.0)
        return eta

    def predict(self, *, design: np.ndarray | None, day: np.ndarray, group: np.ndarray,
                rng: np.random.Generator, draws: int) -> np.ndarray:
        if design is None:
            raise DrdAnalysisError("a linear-predictor rung was asked to predict with no design")
        eta = design @ self.coefficients
        if self.covariance_re is None or not self.rung["marginalize"]:
            return self.inverse_link(eta)
        return monte_carlo_marginal_mean(
            eta, day, self.covariance_re, inverse_link=self.inverse_link,
            draws=draws, rng=rng)


class _NonparametricDayGroupMeans(_DeficitModel):
    """Rung 5, the guaranteed floor: the weighted mean of the deficit within procedure group and
    post-discharge day, with no distributional assumption at all.

    It cannot fail to converge because there is nothing to converge, which is why the ladder
    ends here and why `debt` is never absent for want of an estimator.  What it gives up is
    covariate standardization: it standardizes over nothing but the group and the day, and the
    report says so wherever this rung is the one that was reached.
    """

    def __init__(self, cells: Mapping[tuple[str, int], float], day_means: Mapping[int, float],
                 overall: float, *, weights_applied: bool,
                 diagnostics: Mapping[str, Any]) -> None:
        self.rung = ESTIMATOR_RUNGS[4]
        self.cells = dict(cells)
        self.day_means = dict(day_means)
        self.overall = float(overall)
        self.residual_structure = "none"
        self.weights_applied = bool(weights_applied)
        self.diagnostics = dict(diagnostics)

    def predict(self, *, design: np.ndarray | None, day: np.ndarray, group: np.ndarray,
                rng: np.random.Generator, draws: int) -> np.ndarray:
        days = np.asarray(day, dtype=int)
        groups = np.asarray(group, dtype=object)
        out = np.empty(days.shape, dtype=float)
        for i in range(days.size):
            key = (str(groups[i]), int(days[i]))
            if key in self.cells:
                out[i] = self.cells[key]
            elif int(days[i]) in self.day_means:
                out[i] = self.day_means[int(days[i])]
            else:
                out[i] = self.overall
        return out


def _check_random_effect_covariance(covariance: np.ndarray) -> None:
    """Triggers T2 and T3, tested on the covariance and on nothing else."""
    sigma = np.atleast_2d(np.asarray(covariance, dtype=float))
    variances = np.diag(sigma)
    if np.any(variances <= BOUNDARY_TOLERANCE):
        raise RungFailure("T2", "an estimated variance component is at zero to within the "
                                "prespecified tolerance")
    if sigma.shape[0] > 1:
        if float(np.linalg.det(sigma)) <= BOUNDARY_TOLERANCE:
            raise RungFailure("T3", "the random-effect covariance is singular")
        correlation = float(sigma[0, 1] / math.sqrt(variances[0] * variances[1]))
        if abs(correlation) > CORRELATION_CEILING:
            raise RungFailure("T3", "a random-effect correlation sits at or beyond the ceiling")


def _explained_variation(observed: np.ndarray, fitted: np.ndarray, weights: np.ndarray,
                         random_variance: float) -> tuple[float, float]:
    """Marginal and conditional explained variation, on the response scale.

    The marginal figure is the share of the weighted variance of the response explained by the
    fixed part; the conditional figure adds the estimated random-effect variance to the
    numerator.  With no random effect the two coincide, which is correct rather than a
    placeholder: a marginal model has no second level to explain anything with.
    """
    w = np.asarray(weights, dtype=float)
    y = np.asarray(observed, dtype=float)
    f = np.asarray(fitted, dtype=float)
    mean = weighted_mean(y, w)
    total = float(np.sum(w * (y - mean) ** 2) / np.sum(w))
    if total <= FLOAT_TOLERANCE:
        return 0.0, 0.0
    fixed_mean = weighted_mean(f, w)
    fixed = float(np.sum(w * (f - fixed_mean) ** 2) / np.sum(w))
    marginal = min(max(fixed / total, 0.0), 1.0)
    conditional = min(max((fixed + max(random_variance, 0.0)) / total, 0.0), 1.0)
    return marginal, max(conditional, marginal)


def _fit_r_rung(rung: Mapping[str, Any], *, response: np.ndarray, design: np.ndarray,
                cluster: np.ndarray, day: np.ndarray, weights: np.ndarray,
                r_runner: Callable[..., Mapping[str, Any]] | None) -> _LinearPredictorModel:
    """Rungs 1 and 2, which run in the R analysis environment.

    THE R LEG IS AN INJECTED RUNNER, and its absence is trigger T0 rather than an improvisation.
    Controlled Tier blocks internet for batch jobs while keeping it for interactive tools, so
    installing `glmmTMB` is an interactive operation that can fail, and whether it succeeded is
    an ENVIRONMENT FACT ESTABLISHED IN PHASE 1, before any count is seen.  The runner is a
    callable with the signature

        r_runner(family: str, *, response, design, cluster, day, weights) -> Mapping

    returning at least `converged` (bool), `max_gradient` (float), `coefficients` (a vector as
    long as the design has columns), `covariance_re` (a 2 by 2 or 1 by 1 array), `boundary`
    (bool, true when a cutpoint, dispersion or correlation parameter sits at the edge of its
    admissible range), `residual_structure` (one of the three slugs of 3.4) and, optionally,
    `rho` and `aic`.  Everything else about the R leg lives in R, and this module checks the
    triggers on what comes back rather than trusting it.
    """
    if r_runner is None:
        raise RungFailure("T0", "no R analysis environment was made available to this run")
    try:
        out = r_runner(rung["slug"], response=response, design=design, cluster=cluster,
                       day=day, weights=weights)
    except RungFailure:
        raise
    except Exception as failure:                     # the environment, not the estimate
        raise RungFailure("T0", f"the R analysis environment raised {type(failure).__name__}")
    required = ("converged", "max_gradient", "coefficients", "covariance_re", "boundary")
    missing = [key for key in required if key not in out]
    if missing:
        raise DrdAnalysisError(
            f"the R runner returned a result missing {missing}. The R leg must answer the same "
            f"trigger questions the Python legs answer, or the ladder cannot be walked."
        )
    if not bool(out["converged"]) or float(out["max_gradient"]) > GRADIENT_TOLERANCE:
        raise RungFailure("T1", "the R fit reported non-convergence or a gradient above the "
                                "prespecified tolerance")
    if bool(out["boundary"]):
        raise RungFailure("T2", "the R fit placed a cutpoint, dispersion or correlation "
                                "parameter at a boundary of its admissible range")
    covariance = np.atleast_2d(np.asarray(out["covariance_re"], dtype=float))
    _check_random_effect_covariance(covariance)
    coefficients = np.asarray(out["coefficients"], dtype=float)
    if coefficients.size != design.shape[1]:
        raise DrdAnalysisError(
            "the R runner returned a coefficient vector that does not match the design it was "
            "given, so the two are not the same model"
        )
    fitted = expit(design @ coefficients)
    marginal, conditional = _explained_variation(response, fitted, weights,
                                                 float(covariance[0, 0]))
    diagnostics = {
        "family": rung["family"], "link": rung["link"],
        "rho": float(out.get("rho", float("nan"))),
        "aic": float(out.get("aic", float("nan"))),
        "marginal explained variation": marginal,
        "conditional explained variation": conditional,
        "random intercept variance": float(covariance[0, 0]),
    }
    return _LinearPredictorModel(
        rung, coefficients=coefficients, covariance_re=covariance,
        residual_structure=str(out.get("residual_structure",
                                       RESIDUAL_STRUCTURE_RUNGS[0]["slug"])),
        weights_applied=True, truncate=False, diagnostics=diagnostics)


def _fit_fractional_logit_gee(rung: Mapping[str, Any], *, response: np.ndarray,
                              design: np.ndarray, cluster: np.ndarray, day: np.ndarray,
                              weights: np.ndarray) -> _LinearPredictorModel:
    """Rung 3.  The Papke and Wooldridge quasi-maximum-likelihood estimator is consistent for the
    conditional mean of a response on the closed unit interval, both boundaries included, with
    no transformation and no boundary handling.

    THE WORKING CORRELATION IS TRIED IN REAL TIME FIRST.  `statsmodels` measures the
    autoregressive lag on the `time` argument, so passing the post-discharge day gives the
    continuous-time structure ANALYSIS-PLAN 3.4 specifies rather than the index-lagged one it
    rejects.  The descent from it to an exchangeable structure is a residual-structure descent
    inside this rung, not a descent of the family ladder.
    """
    from statsmodels.genmod.cov_struct import Autoregressive, Exchangeable
    from statsmodels.genmod.families import Binomial
    from statsmodels.genmod.generalized_estimating_equations import GEE

    attempts = (
        (RESIDUAL_STRUCTURE_RUNGS[0]["slug"], Autoregressive, True),
        (RESIDUAL_STRUCTURE_RUNGS[1]["slug"], Exchangeable, False),
    )
    last: Exception | None = None
    for structure_slug, factory, use_time in attempts:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = GEE(response, design, groups=cluster, family=Binomial(),
                            cov_struct=factory(), weights=weights,
                            time=day if use_time else None)
                fit = model.fit(maxiter=100)
            converged = bool(getattr(fit, "converged", True))
            params = np.asarray(fit.params, dtype=float)
            if not converged or not np.all(np.isfinite(params)):
                raise RungFailure("T1", "the estimating equations did not converge")
            dependence = np.atleast_1d(np.asarray(
                getattr(fit, "cov_struct", model.cov_struct).dep_params, dtype=float))
            if dependence.size and np.any(np.abs(np.abs(dependence) - 1.0) <= BOUNDARY_TOLERANCE):
                raise RungFailure("T2", "the working correlation sits at a boundary of its "
                                        "admissible range")
            fitted = expit(design @ params)
            marginal, conditional = _explained_variation(response, fitted, weights, 0.0)
            rho = float(dependence[0]) if dependence.size else float("nan")
            diagnostics = {
                "family": rung["family"], "link": rung["link"], "rho": rho,
                "aic": float("nan"),
                "marginal explained variation": marginal,
                "conditional explained variation": conditional,
                "random intercept variance": 0.0,
            }
            return _LinearPredictorModel(
                rung, coefficients=params, covariance_re=None,
                residual_structure=structure_slug, weights_applied=True, truncate=False,
                diagnostics=diagnostics)
        except RungFailure:
            raise
        except Exception as failure:
            last = failure
            continue
    raise RungFailure("T1", f"every working correlation structure failed to fit "
                            f"({type(last).__name__ if last else 'no result'})")


def _fit_linear_mixed_truncated(rung: Mapping[str, Any], *, response: np.ndarray,
                                design: np.ndarray, cluster: np.ndarray,
                                day: np.ndarray, weights: np.ndarray) -> _LinearPredictorModel:
    """Rung 4.  A linear mixed model on the deficit, fitted values truncated to the unit interval
    before integration, inference from the clustered bootstrap only.

    `statsmodels.MixedLM` HAS NO WEIGHT ARGUMENT, so this rung fits UNWEIGHTED and says so.  That
    is not a silent omission: ANALYSIS-PLAN section 6 defines sensitivity row 4 as the
    observation weights "removed, or applied where the primary rung did not use them", which is
    the plan anticipating exactly this case, and `weights_applied` on the returned model is what
    that row reads to decide which direction to vary.

    The random-effect descent of 3.4 runs inside this rung: an intercept and a random linear
    slope in real post-discharge day first, then the intercept alone on a singular covariance.
    A random slope in real day already induces a within-person correlation that is a function of
    elapsed time rather than of row order, so the essential property survives the descent.
    """
    from statsmodels.regression.mixed_linear_model import MixedLM

    z = scaled_day(day)
    attempts = (
        (RESIDUAL_STRUCTURE_RUNGS[1]["slug"], np.column_stack([np.ones_like(z), z])),
        (RESIDUAL_STRUCTURE_RUNGS[2]["slug"], np.ones((z.size, 1))),
    )
    triggers: list[RungFailure] = []
    for structure_slug, exog_re in attempts:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fit = MixedLM(response, design, groups=cluster, exog_re=exog_re).fit(reml=False)
            if not bool(getattr(fit, "converged", False)):
                raise RungFailure("T1", "the linear mixed model did not converge")
            # `cov_re` is ALREADY in the units of the response; `cov_re_unscaled` is the one
            # divided by the residual variance.  Multiplying `cov_re` by the scale again shrinks
            # the random-effect variance by two orders of magnitude, which silently collapses
            # the Monte Carlo marginalization onto the conditional mean at a zero random effect
            # and fires the boundary trigger for a reason that is arithmetic rather than a
            # property of the fit.
            covariance = np.atleast_2d(np.asarray(fit.cov_re, dtype=float))
            _check_random_effect_covariance(covariance)
            params = np.asarray(fit.fe_params, dtype=float)
            if not np.all(np.isfinite(params)):
                raise RungFailure("T1", "the linear mixed model returned a non-finite estimate")
            fitted = np.clip(design @ params, 0.0, 1.0)
            marginal, conditional = _explained_variation(response, fitted, weights,
                                                         float(covariance[0, 0]))
            diagnostics = {
                "family": rung["family"], "link": rung["link"], "rho": float("nan"),
                "aic": float(getattr(fit, "aic", float("nan"))),
                "marginal explained variation": marginal,
                "conditional explained variation": conditional,
                "random intercept variance": float(covariance[0, 0]),
                "residual variance": float(fit.scale),
            }
            return _LinearPredictorModel(
                rung, coefficients=params, covariance_re=covariance,
                residual_structure=structure_slug, weights_applied=False, truncate=True,
                diagnostics=diagnostics)
        except RungFailure as failure:
            triggers.append(failure)
            continue
        except Exception:
            triggers.append(RungFailure("T1", "the linear mixed model raised while fitting"))
            continue
    raise triggers[-1] if triggers else RungFailure("T1", "the linear mixed model did not fit")


def _fit_nonparametric(rung: Mapping[str, Any], *, response: np.ndarray, group: np.ndarray,
                       day: np.ndarray, weights: np.ndarray) -> _NonparametricDayGroupMeans:
    """Rung 5.  The weighted mean of the deficit within group and day, summed over the window.

    There is nothing here that can fail, which is the point: it is the guaranteed floor and it
    is why `estimator.rung_index` is always populated.
    """
    frame = pd.DataFrame({"group": np.asarray(group, dtype=object),
                          "day": np.asarray(day, dtype=int),
                          "value": np.asarray(response, dtype=float),
                          "weight": np.asarray(weights, dtype=float)})
    frame = frame[np.isfinite(frame["value"]) & (frame["weight"] > 0)]
    cells: dict[tuple[str, int], float] = {}
    for (group_slug, day_index), block in frame.groupby(["group", "day"], sort=True):
        cells[(str(group_slug), int(day_index))] = weighted_mean(block["value"], block["weight"])
    day_means: dict[int, float] = {}
    for day_index, block in frame.groupby("day", sort=True):
        day_means[int(day_index)] = weighted_mean(block["value"], block["weight"])
    overall = weighted_mean(frame["value"], frame["weight"]) if len(frame) else 0.0
    diagnostics = {
        "family": rung["family"], "link": rung["link"], "rho": float("nan"),
        "aic": float("nan"),
        "marginal explained variation": float("nan"),
        "conditional explained variation": float("nan"),
        "random intercept variance": 0.0,
        "cells": len(cells),
    }
    return _NonparametricDayGroupMeans(cells, day_means, overall, weights_applied=True,
                                       diagnostics=diagnostics)


RUNG_OUTCOMES: tuple[str, ...] = ("converged", "did not converge", "skipped", "not attempted")


def fit_deficit_ladder(
    *,
    response: np.ndarray,
    design: np.ndarray,
    cluster: np.ndarray,
    day: np.ndarray,
    group: np.ndarray,
    weights: np.ndarray,
    r_runner: Callable[..., Mapping[str, Any]] | None = None,
    bounded_response: bool = True,
    min_rung: int = 1,
    min_rung_trigger: str | None = "T4",
) -> tuple[_DeficitModel, dict[str, Any]]:
    """Walk the family ladder top down and return the first rung that fits cleanly, with the
    record of how it got there.

    `bounded_response` is False for exactly one row of the plan, the untruncated debt of
    sensitivity row 10, whose response can be negative by construction.  The three bounded
    families cannot represent a response outside the unit interval, so they are SKIPPED, and
    that is a property of the response and not of any estimate.  It is recorded as a skip with
    its own sentence and not as one of the plan's five triggers, because it is not a descent:
    the row never had those rungs available to it.
    """
    attempts: list[dict[str, Any]] = [
        {"index": rung["index"], "slug": rung["slug"], "outcome": "not attempted"}
        for rung in ESTIMATOR_RUNGS
    ]
    triggers: list[str] = []
    reasons: list[str] = []

    def record(index: int, outcome: str) -> None:
        if outcome not in RUNG_OUTCOMES:
            raise DrdAnalysisError(f"{outcome!r} is not one of the four permitted rung outcomes")
        attempts[index - 1]["outcome"] = outcome

    start = 1
    if min_rung > 1:
        # Two callers set a floor, and they set it for different reasons, so the record has to
        # be able to tell them apart.  Trigger T4 of ANALYSIS-PLAN 3.5 descends the PRIMARY one
        # rung after bootstrap instability, which is a property of the fitting process across
        # resamples and not of any estimate.  A sensitivity row instead starts AT the rung the
        # primary reached, because section 6 requires every row to use the identical estimator,
        # and that is not a descent at all.
        for index in range(1, int(min_rung)):
            record(index, "skipped")
        if min_rung_trigger is None:
            reasons.append("The row begins at the rung the primary analysis reached, because "
                           "every row of the ladder uses the identical estimator")
        else:
            triggers.append(min_rung_trigger)
            reasons.append("More than the permitted share of clustered resamples failed to "
                           "converge at the rung above, so the ladder descended one rung")
        start = int(min_rung)
    if not bounded_response:
        for index in (1, 2, 3):
            if attempts[index - 1]["outcome"] == "not attempted":
                record(index, "skipped")
        reasons.append("The untruncated response can leave the unit interval, so the three "
                       "bounded families were not available to this row and the ladder began "
                       "at the linear rung")
        start = max(start, 4)

    for rung in ESTIMATOR_RUNGS:
        index = int(rung["index"])
        if index < start:
            continue
        try:
            if index in (1, 2):
                model: _DeficitModel = _fit_r_rung(
                    rung, response=response, design=design, cluster=cluster, day=day,
                    weights=weights, r_runner=r_runner)
            elif index == 3:
                model = _fit_fractional_logit_gee(
                    rung, response=response, design=design, cluster=cluster, day=day,
                    weights=weights)
            elif index == 4:
                model = _fit_linear_mixed_truncated(
                    rung, response=response, design=design, cluster=cluster, day=day,
                    weights=weights)
            else:
                model = _fit_nonparametric(rung, response=response, group=group, day=day,
                                           weights=weights)
        except RungFailure as failure:
            if failure.trigger not in rung["triggers"]:
                raise DrdAnalysisError(
                    f"rung {index} failed with trigger {failure.trigger}, which the plan does "
                    f"not list for it. A rung may only descend on a trigger its own row of the "
                    f"ladder names."
                )
            triggers.append(failure.trigger)
            reasons.append(f"{ESTIMATOR_RUNG_LABELS[rung['slug']]}: {failure.detail}")
            if failure.trigger == "T0":
                # T0 skips rungs 1 and 2 TOGETHER, because the environment is unavailable for
                # both and attempting the second would be attempting the same impossibility.
                record(1, "skipped")
                record(2, "skipped")
                start = 3
            else:
                record(index, "did not converge")
            continue
        record(index, "converged")
        return model, {
            "rung index": index,
            "rung slug": rung["slug"],
            "rung display": rung["display"],
            "language": rung["language"],
            "r used": rung["language"] == "R",
            "descent triggers fired": tuple(triggers),
            "rungs attempted": tuple(attempts),
            "fallback reason": ". ".join(reasons) if reasons else None,
            "residual structure": model.residual_structure,
            "weights applied": model.weights_applied,
        }

    # Unreachable by construction: rung 5 has no descent trigger and cannot fail.  The assertion
    # is a stop condition rather than a comment, because "cannot happen" is exactly the class of
    # claim that silently stops being true after an edit.
    raise DrdAnalysisError(
        "the model family ladder was exhausted, which cannot happen: the nonparametric floor "
        "has no descent trigger and no way to fail. Something below it changed."
    )


# ======================================================================================
# (8) Preparing one analysis variant.
#
#     The primary and every sensitivity row are the same object: an episode frame, a person-day
#     frame carrying the response, a flag saying which days are observed and which days are in
#     the integration window, and the collapse level's mean structure.  A row of the ladder
#     differs from the primary in ONE of those and in nothing else, which is the property the
#     ladder exists to have.
# ======================================================================================


def group_slug_for(spec: ModelSpec, region: Any, fusion: Any) -> np.ndarray:
    """The group slug of each row, at whatever collapse level is in force."""
    region_a = np.asarray(region, dtype=object)
    fusion_a = np.asarray(fusion).astype(bool)
    if spec.level == "four_group":
        return np.array([f"{r}_{'fusion' if f else 'decompression'}"
                         for r, f in zip(region_a, fusion_a)], dtype=object)
    if spec.level == "two_group":
        return np.where(fusion_a, "fusion", "decompression").astype(object)
    return np.full(fusion_a.shape, ALL_GROUPS_SLUG, dtype=object)


class VariantData:
    """One analysis variant: the primary, or one row of the ladder, in a single object."""

    def __init__(self, slug: str, episodes: pd.DataFrame, days: pd.DataFrame,
                 spec: ModelSpec, *, bounded_response: bool = True,
                 baseline_by_day: np.ndarray | None = None,
                 note: str = "") -> None:
        self.slug = slug
        self.episodes = episodes.reset_index(drop=True)
        self.days = days.reset_index(drop=True)
        self.spec = spec
        self.bounded_response = bool(bounded_response)
        self.note = note
        # The absolute-scale companion multiplies the daily deficit by the episode's own
        # baseline INSIDE the g-computation, before averaging, never after.  The split-baseline
        # row is the one place where the baseline moves within an episode, so it is carried per
        # day rather than per episode.
        if "baseline_day" in self.days.columns:
            self.baseline_by_day = self.days["baseline_day"].to_numpy(dtype=float)
        elif baseline_by_day is not None:
            self.baseline_by_day = np.asarray(baseline_by_day, dtype=float)
        else:
            self.baseline_by_day = self.episodes["baseline_steps"].to_numpy(
                dtype=float)[self.days["unit_pos"].to_numpy().astype(int)]
        self.n_units = int(len(self.episodes))
        self.n_days = int(len(self.days))

    # -- the three row masks --------------------------------------------------------------
    @property
    def in_window(self) -> np.ndarray:
        return self.days["in_window"].to_numpy().astype(bool)

    @property
    def observed(self) -> np.ndarray:
        return self.days["observed"].to_numpy().astype(bool)

    @property
    def at_risk(self) -> np.ndarray:
        return self.days["at_risk"].to_numpy().astype(bool)

    @property
    def fit_rows(self) -> np.ndarray:
        """Observed person-days inside the window with a finite response.  The model is fitted
        on these and on nothing else, and every other day in the window is a day the integration
        stands in for."""
        response = self.days["response"].to_numpy(dtype=float)
        return self.in_window & self.observed & np.isfinite(response)

    def units_present(self) -> np.ndarray:
        """The episode positions with at least one fitted day.  A row's own denominator."""
        return np.unique(self.days["unit_pos"].to_numpy()[self.fit_rows]).astype(int)

    def window_days_per_unit(self) -> np.ndarray:
        """The window days each episode carries, which is the denominator the normalized
        activity column divides by and the day count the assumption-free bounds are taken over.

        It is defined here from `in_window` and INDEPENDENTLY of `estimand_window`, which is
        what makes the equality `manski_bounds` asserts between the two a real check rather than
        a restatement.  Narrow one without the other and the bounds halt.
        """
        counts = np.zeros(self.n_units, dtype=float)
        positions = self.days["unit_pos"].to_numpy()[self.in_window]
        np.add.at(counts, positions.astype(int), 1.0)
        return counts


# ======================================================================================
# (9) Estimation: the observation model, the g-computation, and the person-clustered bootstrap.
# ======================================================================================


def observation_design(builder: DesignBuilder, variant: VariantData, rows: np.ndarray, *,
                       include_lag: bool = True) -> np.ndarray:
    """The observation model's design: the deficit model's design plus what predicts wear.

    ANALYSIS-PLAN 3.7 adds the count of valid baseline days and the LAGGED wear fraction over
    post-discharge days d minus 7 to d minus 1.  The lag is strict, so the model can never
    condition on the very day it is weighting.  The lag does not exist on post-discharge day 1
    and is partial through day 7 (DAG-SCHEMA 8.11); the plan is silent on that case, so this
    module transposes the rule the plan already uses for a missing body mass index, a missing
    indicator plus median substitution, rather than inventing a second convention.
    """
    days = variant.days
    unit_pos = days["unit_pos"].to_numpy()[rows].astype(int)
    day = days["day"].to_numpy()[rows].astype(float)
    dow = days["dow"].to_numpy()[rows].astype(int)
    base = builder.matrix(unit_pos, day, dow)
    extra = [variant.episodes["n_valid_baseline_days"].to_numpy(dtype=float)[unit_pos][:, None]]
    if include_lag:
        lag = days["lag"].to_numpy(dtype=float)[rows]
        missing = ~np.isfinite(lag)
        filled = np.where(missing, float(np.nanmedian(lag)) if np.any(~missing) else 0.0, lag)
        extra.append(filled[:, None])
        extra.append(missing.astype(float)[:, None])
    return np.column_stack([base] + extra)


def fit_observation_weights(builder: DesignBuilder, variant: VariantData, *,
                            include_lag: bool = True) -> tuple[np.ndarray, dict[str, Any]]:
    """Inverse probability of observation weights for the fitted rows.

    Fitted on every AT-RISK day inside the window, observed or not, with the analyzability
    indicator as the outcome; the weights are then read off on the observed days the deficit
    model actually uses.  This is what makes an observed day stand in for comparable missing
    days rather than for nothing.

    The assumption it buys, stated plainly and not oversold: validity under missingness at
    random GIVEN THIS CONDITIONING SET.  It does not buy validity under arbitrary informative
    non-wear and nothing can; that gap is what the delta-shift tipping point measures.
    """
    import statsmodels.api as sm

    candidate = variant.in_window & variant.at_risk
    if not np.any(candidate):
        raise DrdAnalysisError("no at-risk day inside the window, so there is nothing to weight")
    outcome = variant.observed[candidate].astype(float)
    fit_mask = variant.fit_rows
    summary: dict[str, Any] = {"available": False, "lagged wear used": bool(include_lag)}
    marginal = float(outcome.mean())
    if outcome.min() == outcome.max():
        # Every day observed, or none: the weight model has no variation to fit and the weights
        # are one by construction.  Not a failure, and not a reason to descend anything.
        summary.update({"available": True, "degenerate": True, "marginal probability": marginal,
                        "mean": 1.0, "minimum": 1.0, "maximum": 1.0, "share truncated": 0.0,
                        "truncation low": 1.0, "truncation high": 1.0})
        return np.ones(int(fit_mask.sum())), summary
    try:
        design = observation_design(builder, variant, candidate, include_lag=include_lag)
        # SCOPED, AND NEVER `np.seterr`.  The IRLS of a logistic fit overflows on its way to a
        # converged step and that overflow is not news, but `np.seterr` is PROCESS state and
        # `warnings.catch_warnings` does not restore it.  Set here it would silence every
        # overflow, invalid operation and divide by zero for the rest of the session, from the
        # first weight fit onward: the thousand bootstrap resamples, the Monte Carlo
        # marginalization, the bounds and the exporter would all run blind, and the diagnostic
        # that would have surfaced the NEXT defect would never print.  `np.errstate` silences
        # this fit and nothing else, which is what every other site in this module does.
        with warnings.catch_warnings(), np.errstate(over="ignore", invalid="ignore",
                                                    divide="ignore"):
            warnings.simplefilter("ignore")
            fit = sm.GLM(outcome, design, family=sm.families.Binomial()).fit(maxiter=100)
            probability = np.clip(np.asarray(fit.predict(design), dtype=float),
                                  PROBABILITY_EPSILON, 1.0 - PROBABILITY_EPSILON)
    except Exception as failure:
        summary.update({"available": False, "degenerate": False,
                        "why": f"the observation model raised {type(failure).__name__}"})
        return np.ones(int(fit_mask.sum())), summary
    weights_all, detail = stabilized_weights(probability, marginal=marginal)
    lookup = np.ones(variant.n_days, dtype=float)
    lookup[np.where(candidate)[0]] = weights_all
    summary.update({"available": True, "degenerate": False})
    summary.update(detail)
    return lookup[fit_mask], summary


def _per_unit_sum(values: np.ndarray, unit_pos: np.ndarray, n_units: int) -> np.ndarray:
    out = np.zeros(n_units, dtype=float)
    np.add.at(out, unit_pos.astype(int), np.asarray(values, dtype=float))
    return out


def estimand_window(variant: VariantData) -> np.ndarray:
    """THE ROWS THE ESTIMAND IS DEFINED OVER, read from one place by everything that covers it.

    The debt is the shortfall accrued over the WHOLE window, so `marginal_debt` integrates the
    fitted curve over every one of these rows: the days the episode contributed, the days it
    did not, and the days it was no longer at risk on.  Anything that claims to bound that
    quantity, or to normalize it by the window it accrued over, has to cover the same rows or
    it is describing a different quantity under the same label.  That is why the mask is a
    named function and not an expression repeated at three call sites, each free to drift.

    A row set held identical by prose is a row set that stops being identical at the next edit.
    `manski_bounds` and `window_days_per_unit` are checked against this one at runtime.
    """
    return variant.in_window


def marginal_debt(model: _DeficitModel, builder: DesignBuilder, variant: VariantData, *,
                  fusion: bool | None, region: str | None, seed_spec: Any,
                  draws: int, delta: float = 0.0,
                  scale_by_baseline: bool = False) -> tuple[float, np.ndarray]:
    """`psi(g)`: the covariate-standardized marginal debt with the whole cohort set to `g`.

    THE INTEGRATION COVERS EVERY DAY OF THE WINDOW, including the days the episode did not
    contribute.  That is the entire difference between this estimator and the naive sum, and it
    is why a missing day is a day the model predicts for rather than a day that silently scores
    zero deficit.

    The generator is created FRESH from `seed_spec` on every call, which is what makes the
    common random numbers of ANALYSIS-PLAN 3.3 exact: two calls that differ only in the
    procedure group draw the identical stream, so the Monte Carlo noise cancels in the
    difference instead of accumulating over 35 days.
    """
    rows = np.where(estimand_window(variant))[0]
    if rows.size == 0:
        raise DrdAnalysisError("the integration window is empty, so there is nothing to sum")
    days = variant.days
    unit_pos = days["unit_pos"].to_numpy()[rows].astype(int)
    day = days["day"].to_numpy()[rows].astype(float)
    dow = days["dow"].to_numpy()[rows].astype(int)
    region_of_row = (variant.episodes["region"].to_numpy(dtype=object)[unit_pos]
                     if region is None else np.full(rows.shape, region, dtype=object))
    fusion_of_row = (variant.episodes["fusion"].to_numpy().astype(bool)[unit_pos]
                     if fusion is None else np.full(rows.shape, bool(fusion)))
    design = builder.matrix(unit_pos, day, dow, fusion=fusion, region=region)
    group = group_slug_for(variant.spec, region_of_row, fusion_of_row)
    predicted = model.predict(design=design, day=day, group=group,
                              rng=np.random.default_rng(seed_spec), draws=draws)
    if delta:
        # The shift lands on MISSING days only.  On observed days the fitted model stands, which
        # is what makes delta zero the primary rather than a special case of it.
        observed = variant.observed[rows]
        predicted = np.where(observed, predicted, expit(logit(predicted) + float(delta)))
    contribution = predicted
    if scale_by_baseline:
        contribution = contribution * (variant.baseline_by_day[rows] / STEPS_PER_THOUSAND)
    per_unit = _per_unit_sum(contribution, unit_pos, variant.n_units)
    return float(per_unit.mean()), per_unit


def contrasts_from_psi(spec: ModelSpec, psi: Callable[[bool | None, str | None], float],
                       ) -> dict[str, float]:
    """The five contrasts of EXPORT-CONTRACT 3.5, each as a difference of standardized
    predictions.  Pooling with an interaction present means STANDARDIZATION, not omission: the
    primary contrast is the difference between two whole-cohort predictions made at the cohort's
    own region and covariate distribution, and it is not a coefficient."""
    out: dict[str, float] = {}
    if not spec.has_fusion:
        return out
    out[PRIMARY_CONTRAST_SLUG] = psi(True, None) - psi(False, None)
    if not spec.has_region_interaction:
        return out
    cervical = psi(True, "cervical") - psi(False, "cervical")
    lumbar = psi(True, "lumbar") - psi(False, "lumbar")
    out["lumbar_vs_cervical"] = psi(None, "lumbar") - psi(None, "cervical")
    out["region_by_fusion_interaction"] = lumbar - cervical
    out["fusion_vs_decompression_cervical"] = cervical
    out["fusion_vs_decompression_lumbar"] = lumbar
    return out


def group_setting(spec: ModelSpec, slug: str) -> tuple[bool | None, str | None]:
    """The `(fusion, region)` setting that defines one group at this collapse level."""
    if slug in FOUR_GROUP_SLUGS:
        region, _, kind = slug.partition("_")
        return kind == "fusion", region
    if slug in TWO_GROUP_SLUGS:
        return slug == "fusion", None
    if slug == ALL_GROUPS_SLUG:
        return None, None
    raise DrdAnalysisError(f"{slug!r} is not a group slug this plan defines")


def report_groups(spec: ModelSpec) -> tuple[str, ...]:
    """The collapse level's own groups, and then the pooled row.

    THE POOLED ROW IS NOT A FIFTH GROUP.  It is the same estimand computed with the cohort left
    at its own procedure-group distribution, which `group_setting` returns as `(None, None)`,
    and EXPORT-CONTRACT reads it as the LAST entry of `debt.by_group`: Table 2 prints it as the
    total row, the Table 2 footer resolves the share with zero debt out of it by position, and
    the exporter's secondary-suppression rule treats the per-group zero-debt counts as a
    partition of it.  Omitting it here is what left `by_group` one row short of every one of
    those.  At the single-group level it is already the only group and is not repeated.
    """
    if ALL_GROUPS_SLUG in spec.groups:
        return spec.groups
    return spec.groups + (ALL_GROUPS_SLUG,)


def recovery_outcome(variant: VariantData) -> tuple[np.ndarray, np.ndarray]:
    """The episode-level "reached 80% of baseline" outcome, and which episodes have one.

    ANALYSIS-PLAN 9.2 defines it as the median daily CAPPED normalized activity over
    post-discharge days 29 to 35 being at least 0.8.  Capped normalized activity is `1 - D`, the
    complement of the modelled deficit, which is exactly why no second inequality is needed:
    the cap and the truncation are the same operation seen from two sides.  An episode with no
    observed day in that band has no outcome at all, which is a denominator and not a zero.
    """
    days = variant.days
    day = days["day"].to_numpy(dtype=float)
    band = (day >= RECOVERY_FIRST_DAY) & (day <= RECOVERY_LAST_DAY)
    rows = band & variant.observed & np.isfinite(days["response"].to_numpy(dtype=float))
    outcome = np.zeros(variant.n_units, dtype=float)
    present = np.zeros(variant.n_units, dtype=bool)
    if not np.any(rows):
        return outcome, present
    unit_pos = days["unit_pos"].to_numpy()[rows].astype(int)
    activity = 1.0 - np.clip(days["response"].to_numpy(dtype=float)[rows], 0.0, 1.0)
    frame = pd.DataFrame({"unit": unit_pos, "activity": activity})
    medians = frame.groupby("unit")["activity"].median()
    for unit, value in medians.items():
        outcome[int(unit)] = 1.0 if float(value) >= RECOVERY_THRESHOLD else 0.0
        present[int(unit)] = True
    return outcome, present


def fit_recovery_share(builder: DesignBuilder, variant: VariantData,
                       ) -> tuple[Callable[[bool | None, str | None], float], dict[str, Any]]:
    """The logistic g-computation behind the adjusted share reaching 80% of baseline.

    IT IS AN ESTIMATE AND NOT A PERCENTAGE.  It is a fitted probability with a confidence
    interval and no numerator, so treating it as a count over a denominator would invent a
    numerator that does not exist.  Its disclosability follows the contributing episode count,
    which is what the returned summary carries.

    IT IS A COMPLETE-CASE FIT STANDARDIZED TO THE WHOLE COHORT, AND THAT IS AN ASSUMPTION.  The
    model is fitted on the episodes with an observed day in post-discharge days 29 to 35 and
    then predicted for every episode, which is valid under missingness at random GIVEN THE
    EPISODE-LEVEL COVARIATE SET and under nothing weaker.  The daily-deficit model meets the
    identical missingness with inverse probability of observation weights and a delta-shift
    companion that prices the assumption; this quantity has neither.  So the denominator it was
    actually fitted on travels out of here PER GROUP, `n with outcome by group`, and reaches
    Table 2 beside the cell rather than standing silently under the group's full `n`.  Whether
    it should also be weighted is a prespecification question and not a coding one: see the
    note beside `RECOVERY_MISSINGNESS_ASSUMPTION`.
    """
    import statsmodels.api as sm

    outcome, present = recovery_outcome(variant)
    # THE ROW'S OWN DENOMINATOR, resolved here because this is the only function that knows
    # which episodes have the outcome at all.  Every other subset-fitted row in this project
    # carries its own count to the boundary; the naive column's `true_complete_windows` is the
    # pattern, and this row was the one that did not follow it.
    group_of_unit = group_slug_for(variant.spec,
                                   variant.episodes["region"].to_numpy(dtype=object),
                                   variant.episodes["fusion"].to_numpy().astype(bool))
    by_group_n = {slug: int(np.sum(present if slug == ALL_GROUPS_SLUG
                                   else present & (group_of_unit == slug)))
                  for slug in report_groups(variant.spec)}
    summary: dict[str, Any] = {
        "n with outcome": int(present.sum()),
        "n with outcome by group": by_group_n,
        "n in cohort": int(variant.n_units),
        "fitted on": RECOVERY_FITTED_ON,
        "missingness assumption": RECOVERY_MISSINGNESS_ASSUMPTION,
        "available": False,
    }
    if present.sum() == 0 or outcome[present].min() == outcome[present].max():
        # NOT A CONSTANT.  The old branch returned one number for every group, which renders as
        # four identical adjusted shares: a reader meets a column headed "adjusted" carrying a
        # figure no model produced and no standardization touched, and four cells agreeing to
        # the digit reads as a finding rather than as an absence.  Nothing downstream inspected
        # `available` before printing, and a flag nobody reads protects nothing.  A NaN is
        # unprintable at BOTH renderers by the rule they already apply to every other estimate,
        # so the cell suppresses itself and needs no second reader to know that it must.
        summary.update({
            "degenerate": True,
            "why": ("no episode has the outcome" if present.sum() == 0 else
                    "every episode with the outcome falls on the same side of the threshold, "
                    "so there is no variation to fit and no adjusted share to report"),
        })
        return (lambda fusion, region: float("nan")), summary
    positions = np.where(present)[0]
    try:
        design, _ = builder.episode_matrix(positions)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fit = sm.GLM(outcome[positions], design, family=sm.families.Binomial()).fit(maxiter=100)
        params = np.asarray(fit.params, dtype=float)
    except Exception as failure:
        summary["why"] = f"the recovery model raised {type(failure).__name__}"
        return (lambda fusion, region: float("nan")), summary
    summary.update({"available": True, "degenerate": False})
    everyone = np.arange(variant.n_units)

    def predict(fusion: bool | None, region: str | None) -> float:
        matrix, _ = builder.episode_matrix(everyone, fusion=fusion, region=region)
        if matrix.shape[1] != params.size:
            return float("nan")
        return float(expit(matrix @ params).mean())

    return predict, summary


def estimate_variant(
    variant: VariantData,
    *,
    r_runner: Callable[..., Mapping[str, Any]] | None = None,
    draws: int = MONTE_CARLO_DRAWS,
    seed_spec: Any = SEED,
    include_lag: bool = True,
    apply_weights: bool = True,
    deltas: Sequence[tuple[float, str]] = (),
    absolute: bool = False,
    unadjusted: bool = False,
    include_baseline_steps: bool = False,
    min_rung: int = 1,
    min_rung_trigger: str | None = "T4",
) -> dict[str, Any]:
    """Fit, marginalize and integrate one variant.  Everything downstream of a bootstrap
    resample is inside this function, which is what makes the interval account for the weights
    and the model being estimated rather than known.

    `unadjusted` adds the SECOND fit STROBE item 16(a) requires, on the same rows, the same
    weights and the same random stream, with the covariate block of ANALYSIS-PLAN 3.6 deleted
    from the mean structure and nothing else changed.  It is computed here, inside the function
    a bootstrap resample re-enters, for exactly the reason the adjusted contrast is: an interval
    that did not refit the model would be an interval around a number treated as known.
    """
    fit_mask = variant.fit_rows
    if int(fit_mask.sum()) == 0:
        raise DrdAnalysisError("no observed person-day inside the window, so nothing can be fit")
    builder = DesignBuilder(variant.episodes, variant.spec,
                            include_baseline_steps=include_baseline_steps)
    days = variant.days
    unit_pos = days["unit_pos"].to_numpy()[fit_mask].astype(int)
    day = days["day"].to_numpy(dtype=float)[fit_mask]
    dow = days["dow"].to_numpy(dtype=int)[fit_mask]
    response = days["response"].to_numpy(dtype=float)[fit_mask]
    region_of_row = variant.episodes["region"].to_numpy(dtype=object)[unit_pos]
    fusion_of_row = variant.episodes["fusion"].to_numpy().astype(bool)[unit_pos]
    group = group_slug_for(variant.spec, region_of_row, fusion_of_row)

    if apply_weights:
        weights, weight_summary = fit_observation_weights(builder, variant, include_lag=include_lag)
    else:
        weights = np.ones(int(fit_mask.sum()), dtype=float)
        weight_summary = {"available": True, "degenerate": False, "applied": False,
                          "lagged wear used": False, "mean": 1.0, "minimum": 1.0,
                          "maximum": 1.0, "share truncated": 0.0}
    weight_summary["applied"] = bool(apply_weights)

    design = builder.matrix(unit_pos, day, dow)
    model, ladder = fit_deficit_ladder(
        response=response, design=design, cluster=unit_pos, day=day, group=group,
        weights=weights, r_runner=r_runner, bounded_response=variant.bounded_response,
        min_rung=min_rung, min_rung_trigger=min_rung_trigger)

    cache: dict[tuple[Any, Any, float], float] = {}

    def psi(fusion: bool | None, region: str | None, delta: float = 0.0) -> float:
        key = (fusion, region, float(delta))
        if key not in cache:
            cache[key] = marginal_debt(model, builder, variant, fusion=fusion, region=region,
                                       seed_spec=seed_spec, draws=draws, delta=delta)[0]
        return cache[key]

    by_group = {slug: psi(*group_setting(variant.spec, slug))
                for slug in report_groups(variant.spec)}
    contrasts = contrasts_from_psi(variant.spec, lambda f, r: psi(f, r))

    # -- STROBE 16(a), the unadjusted contrast beside the adjusted one -------------------
    #
    # ONE THING VARIES.  The response, the fitted rows, the clustering, the weights, the
    # Monte Carlo draws and the seed are all the objects the adjusted fit used; the design
    # matrix is the only difference, and it differs by the covariate block alone.  The seed
    # reaches `marginal_debt` unchanged, so the common random numbers of 3.3 hold inside this
    # contrast exactly as they hold inside the adjusted one: the two group predictions draw
    # the identical stream and the Monte Carlo noise cancels in their difference.
    #
    # IT WALKS THE LADDER ON ITS OWN, from whatever floor this call is under.  A covariate-free
    # design is a different optimization problem and may converge where the adjusted one did
    # not, or fail where it did; the rung it reaches is recorded and reported rather than
    # forced to match, because a differing rung is a fact about the two fits and hiding it
    # would make two different estimators look like one.
    #
    # ITS FAILURE IS ITS OWN AND NEVER THE PRIMARY'S.  The catch is the module's named set of
    # legitimate fit failures, not a bare `except Exception`, and it is here rather than around
    # the caller so that a resample whose unadjusted fit failed still contributes its adjusted
    # draw.  A guideline-mandated companion that could take down the prespecified estimand
    # would be a worse defect than the gap it closes.
    unadjusted_contrasts: dict[str, float] = {}
    unadjusted_ladder: dict[str, Any] | None = None
    unadjusted_failure: str | None = None
    if unadjusted and variant.spec.has_fusion:
        try:
            plain_builder = DesignBuilder(variant.episodes, variant.spec,
                                          include_covariates=False)
            plain_design = plain_builder.matrix(unit_pos, day, dow)
            plain_model, unadjusted_ladder = fit_deficit_ladder(
                response=response, design=plain_design, cluster=unit_pos, day=day, group=group,
                weights=weights, r_runner=r_runner, bounded_response=variant.bounded_response,
                min_rung=min_rung, min_rung_trigger=min_rung_trigger)
            plain_cache: dict[tuple[Any, Any], float] = {}

            def psi_unadjusted(fusion: bool | None, region: str | None) -> float:
                key = (fusion, region)
                if key not in plain_cache:
                    plain_cache[key] = marginal_debt(
                        plain_model, plain_builder, variant, fusion=fusion, region=region,
                        seed_spec=seed_spec, draws=draws)[0]
                return plain_cache[key]

            unadjusted_contrasts = contrasts_from_psi(variant.spec, psi_unadjusted)
        except BOOTSTRAP_FAILURES as failure:
            unadjusted_contrasts = {}
            unadjusted_ladder = None
            unadjusted_failure = f"the unadjusted fit raised {type(failure).__name__}"

    # ONE SET, AVERAGED OVER ON BOTH SIDES.  `by group` is `per_unit.mean()` over EVERY
    # episode, and an episode with no row inside the window contributes a zero to it through
    # `np.add.at`.  A denominator averaged over the episodes that HAVE a window would then
    # divide a numerator averaged over more episodes than itself, and the column would print a
    # normalized activity no episode has.  Both sides average over the same `n_units`, so an
    # episode with no window row contributes zero to each and moves neither: that is what "a
    # denominator and not a zero" comes to arithmetically.  The ratio of the two means is
    # exactly the mean over the window's PERSON-DAYS, which is the quantity the column names.
    window_days = variant.window_days_per_unit()
    mean_window = (float(window_days.mean()) if float(window_days.sum()) > 0.0
                   else float(WINDOW_LENGTH_DAYS))
    # AND IT IS THE CAPPED MEAN.  The modelled response is the TRUNCATED daily deficit, so a
    # day above baseline entered the fit as a deficit of zero and comes back out of it as an
    # activity of exactly one: `1 - D` is `min(steps / baseline, 1)` and not `steps / baseline`.
    # The cap is named HERE, where the quantity is built, and the name crosses the boundary as
    # `normalized_activity_display` so that no exhibit has to print the label without it.  The
    # uncapped mean is not available from this fit at all: recovering it would need a second
    # model of the untruncated response, which is sensitivity row 10 and a different estimand.
    normalized = {slug: 1.0 - value / mean_window for slug, value in by_group.items()}

    delta_values: dict[tuple[float, str], float] = {}
    if deltas and variant.spec.has_fusion and variant.bounded_response:
        for value, application in deltas:
            fusion_delta = value if application in ("fusion only", "both groups") else 0.0
            decomp_delta = value if application in ("decompression only", "both groups") else 0.0
            delta_values[(float(value), application)] = (
                psi(True, None, fusion_delta) - psi(False, None, decomp_delta))

    absolute_group: dict[str, float] = {}
    absolute_contrasts: dict[str, float] = {}
    if absolute:
        # ANALYSIS-PLAN 3.9.  The arithmetic needs no second model, because `B_i * D_id` is
        # identically `max(0, B_i - S_id)`.  The MODEL change is not optional: multiplying a
        # baseline-independent fitted deficit by the episode's baseline would impose the
        # assumption that the deficit does not depend on the baseline, and the data can test
        # that, so the daily-deficit model is REFIT with a spline in log baseline steps.
        absolute_builder = DesignBuilder(variant.episodes, variant.spec, include_log_baseline=True)
        absolute_design = absolute_builder.matrix(unit_pos, day, dow)
        absolute_model, _ = fit_deficit_ladder(
            response=response, design=absolute_design, cluster=unit_pos, day=day, group=group,
            weights=weights, r_runner=r_runner, bounded_response=variant.bounded_response,
            min_rung=min_rung, min_rung_trigger=min_rung_trigger)
        abs_cache: dict[tuple[Any, Any], float] = {}

        def psi_absolute(fusion: bool | None, region: str | None) -> float:
            key = (fusion, region)
            if key not in abs_cache:
                abs_cache[key] = marginal_debt(
                    absolute_model, absolute_builder, variant, fusion=fusion, region=region,
                    seed_spec=seed_spec, draws=draws, scale_by_baseline=True)[0]
            return abs_cache[key]

        absolute_group = {slug: psi_absolute(*group_setting(variant.spec, slug))
                          for slug in report_groups(variant.spec)}
        absolute_contrasts = contrasts_from_psi(variant.spec, psi_absolute)

    recovery, recovery_summary = fit_recovery_share(builder, variant)
    share_reaching = {slug: 100.0 * recovery(*group_setting(variant.spec, slug))
                      for slug in report_groups(variant.spec)}

    predicted_fit = model.predict(design=design, day=day, group=group,
                                  rng=np.random.default_rng(seed_spec), draws=draws)
    marginal_r2, conditional_r2 = _explained_variation(
        response, predicted_fit, weights, model.diagnostics.get("random intercept variance", 0.0))

    return {
        "ladder": ladder,
        "by group": by_group,
        "contrasts": contrasts,
        # Three separate keys and not one nested object, so a caller that never asked for the
        # unadjusted fit reads three empty things rather than a missing member it has to guard.
        "unadjusted contrasts": unadjusted_contrasts,
        "unadjusted ladder": unadjusted_ladder,
        "unadjusted failure": unadjusted_failure,
        "normalized activity": normalized,
        "share reaching": share_reaching,
        "absolute by group": absolute_group,
        "absolute contrasts": absolute_contrasts,
        "delta": delta_values,
        "weights": weight_summary,
        "recovery": recovery_summary,
        "mean window days": mean_window,
        "model fit": {
            "family": model.diagnostics.get("family", ""),
            "link": model.diagnostics.get("link", ""),
            "residual structure": model.residual_structure,
            "rho": float(model.diagnostics.get("rho", float("nan"))),
            "aic": float(model.diagnostics.get("aic", float("nan"))),
            "icc": _intraclass_correlation(model),
            "marginal r2": marginal_r2,
            "conditional r2": conditional_r2,
            "n person days": int(fit_mask.sum()),
            "n persons": int(np.unique(unit_pos).size),
            "spline df": spline_degrees_of_freedom(DAY_KNOTS),
            "monte carlo draws": int(draws),
            "converged": True,
            "design columns": len(builder.names),
            "dropped columns": builder.dropped_names,
        },
    }


def _intraclass_correlation(model: _DeficitModel) -> float:
    """The share of variation sitting between people rather than within them.

    A marginal model has no second level, so the honest answer there is zero rather than a
    number borrowed from a different specification.
    """
    variance = float(model.diagnostics.get("random intercept variance", 0.0))
    residual = float(model.diagnostics.get("residual variance", float("nan")))
    if variance <= 0:
        return 0.0
    if math.isfinite(residual) and (variance + residual) > 0:
        return variance / (variance + residual)
    # A logit-link mixed model has no residual variance on the response scale; the standard
    # latent-scale convention uses the logistic distribution's variance, pi squared over three.
    latent = (math.pi ** 2) / 3.0
    return variance / (variance + latent)


# ======================================================================================
# (10) Inference: the person-clustered nonparametric bootstrap.
#
#      The resampling unit is the PERSON.  Whole participants are drawn with replacement,
#      carrying all of their person-days, and EVERYTHING downstream of the resample is refit
#      inside it: the observation model, the deficit model, the Monte Carlo marginalization and
#      the g-computation.  Refitting the weight model inside the bootstrap is what makes the
#      interval account for the weights being estimated rather than known, and resampling whole
#      participants is what makes the interval valid under an arbitrarily misspecified
#      within-person correlation.  That is why the residual-structure descent of 3.4 is not a
#      threat to the inference: it moves the point estimate's efficiency, not what the interval
#      rests on.
# ======================================================================================


def rows_by_unit(variant: VariantData) -> list[np.ndarray]:
    """The day-row indices belonging to each episode, computed ONCE and reused by every
    resample.  Rebuilding it inside the loop is the difference between a bootstrap that runs in
    minutes and one that runs in hours, and it is the only place in this module where a loop
    over episodes is worth hoisting.
    """
    positions = variant.days["unit_pos"].to_numpy().astype(int)
    order = np.argsort(positions, kind="stable")
    ordered = positions[order]
    out: list[np.ndarray] = [np.empty(0, dtype=int) for _ in range(variant.n_units)]
    if ordered.size:
        edges = np.flatnonzero(np.diff(ordered)) + 1
        for rows, units in zip(np.split(order, edges), np.split(ordered, edges)):
            out[int(units[0])] = np.sort(rows)
    return out


def rows_by_unit_reference(variant: VariantData) -> list[np.ndarray]:
    """The same thing written the obvious way, kept because it is the definition the grouped
    version is checked against in the self-test.  Two implementations of one definition are a
    divergence waiting to happen unless one of them is only ever used to check the other."""
    positions = variant.days["unit_pos"].to_numpy().astype(int)
    return [np.flatnonzero(positions == unit) for unit in range(variant.n_units)]


def resample_variant(variant: VariantData, draw: np.ndarray,
                     index: Sequence[np.ndarray]) -> VariantData:
    """One person-clustered resample, carrying every day of every drawn participant."""
    order = np.asarray(draw, dtype=int)
    episodes = variant.episodes.iloc[order].reset_index(drop=True)
    blocks = []
    for new_position, source in enumerate(order):
        rows = index[int(source)]
        if rows.size == 0:
            continue
        block = variant.days.iloc[rows].copy()
        block["unit_pos"] = new_position
        blocks.append(block)
    if not blocks:
        raise DrdAnalysisError("a bootstrap resample drew no person-day at all")
    days = pd.concat(blocks, ignore_index=True)
    return VariantData(variant.slug, episodes, days, variant.spec,
                       bounded_response=variant.bounded_response, note=variant.note)


def percentile_interval(values: Sequence[float], level: float = CONFIDENCE_LEVEL, *,
                        attempted: int | None = None) -> tuple[float, float]:
    """The 2.5th and 97.5th percentiles of the resampled statistic, or nothing at all.

    NON-FINITE DRAWS ARE DROPPED AND DROPPING THEM IN SILENCE IS THE DEFECT.  A row where 495 of
    500 resamples came back NaN would otherwise return a perfectly ordinary 95% interval
    computed from five draws, and nothing downstream could tell it from an interval computed
    from five hundred: the estimate node would carry `"suppressed": false` and the sensitivity
    row would carry `"estimable": true`.

    `attempted` is the number of resamples the CALLER ASKED FOR, which is larger than
    `len(values)` whenever the bootstrap discarded a resample before its statistic ever reached
    here.  The guard is against that number, so a resample discarded for failing to reach the
    rung and a resample that returned NaN count the same.  Below the prespecified minimum the
    answer is not an interval, and this returns the pair of NaNs the node builders suppress on
    rather than a narrower interval computed from whatever survived.
    """
    finite = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    asked = int(attempted) if attempted is not None else int(len(values))
    minimum = max(BOOTSTRAP_MIN_FINITE_DRAWS,
                  int(math.ceil(BOOTSTRAP_MIN_FINITE_SHARE * asked)))
    if finite.size < minimum:
        return float("nan"), float("nan")
    tail = (1.0 - level) / 2.0 * 100.0
    return float(np.percentile(finite, tail)), float(np.percentile(finite, 100.0 - tail))


def bootstrap_pvalue(values: Sequence[float]) -> float:
    """Twice the smaller resample tail proportion beyond zero.

    No P value in this plan selects a model, a window, a covariate or a cutpoint, so this is a
    report of where the resampled distribution sits relative to zero and nothing else.
    """
    array = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if array.size == 0:
        return float("nan")
    below = float(np.mean(array <= 0.0))
    above = float(np.mean(array >= 0.0))
    return float(min(1.0, 2.0 * min(below, above)))


def clustered_bootstrap(
    variant: VariantData,
    *,
    resamples: int,
    point_rung_index: int,
    r_runner: Callable[..., Mapping[str, Any]] | None = None,
    draws: int = MONTE_CARLO_DRAWS,
    deltas: Sequence[tuple[float, str]] = (),
    absolute: bool = False,
    include_lag: bool = True,
    apply_weights: bool = True,
    include_baseline_steps: bool = False,
    min_rung: int = 1,
    min_rung_trigger: str | None = "T4",
    unadjusted: bool = False,
    unadjusted_rung_index: int | None = None,
) -> dict[str, Any]:
    """Resample `resamples` times and collect every statistic the exhibits need.

    A resample is a FAILURE when its own ladder walk could not reach the rung the point estimate
    reached, or when the fit raised.  That is a property of the fitting process across
    resamples, exactly as trigger T4 defines it, and it never looks at the estimate a resample
    produced.  Failures are discarded and COUNTED, and the count is reported whatever it is.

    THE UNADJUSTED CONTRAST IS RESAMPLED IN THE SAME LOOP AND JUDGED ON ITS OWN RUNG, and the
    two judgements are deliberately kept apart.  The resample-level discard above is the
    ADJUSTED fit's, unchanged, so the adjusted intervals are exactly the intervals they were
    before this quantity existed; a resample the adjusted fit kept but whose unadjusted fit
    could not reach the unadjusted point estimate's rung simply contributes no unadjusted draw.
    `percentile_interval` then refuses an unadjusted interval on the same complementary share of
    the same attempted count that trigger T4 is written on, so an unadjusted contrast standing
    on too few resamples is not estimable for the same reason and by the same constant as an
    adjusted one, with no second threshold invented for it.
    """
    if unadjusted and unadjusted_rung_index is None:
        raise DrdAnalysisError(
            "the unadjusted contrast was asked for with no rung for its resamples to be judged "
            "against. A resample is kept or discarded on the rung the POINT estimate reached, "
            "and the caller is the only thing that knows it."
        )
    index = rows_by_unit(variant)
    collected: dict[str, list[float]] = {}
    delta_collected: dict[tuple[float, str], list[float]] = {key: [] for key in deltas}
    failures = 0

    def stash(key: str, value: float) -> None:
        collected.setdefault(key, []).append(float(value))

    for b in range(int(resamples)):
        rng = np.random.default_rng([SEED, b])
        drawn = rng.integers(0, variant.n_units, size=variant.n_units)
        try:
            resampled = resample_variant(variant, drawn, index)
            out = estimate_variant(
                resampled, r_runner=r_runner, draws=draws, seed_spec=[SEED, b],
                include_lag=include_lag, apply_weights=apply_weights, deltas=deltas,
                absolute=absolute, unadjusted=unadjusted,
                include_baseline_steps=include_baseline_steps,
                min_rung=min_rung, min_rung_trigger=min_rung_trigger)
        except BOOTSTRAP_FAILURES:
            failures += 1
            continue
        if int(out["ladder"]["rung index"]) > int(point_rung_index):
            failures += 1
            continue
        if unadjusted:
            plain = out["unadjusted ladder"]
            if plain is not None and int(plain["rung index"]) <= int(unadjusted_rung_index):
                for slug, value in out["unadjusted contrasts"].items():
                    stash(f"unadjusted contrast:{slug}", value)
        for slug, value in out["by group"].items():
            stash(f"group:{slug}", value)
        for slug, value in out["contrasts"].items():
            stash(f"contrast:{slug}", value)
        for slug, value in out["normalized activity"].items():
            stash(f"activity:{slug}", value)
        for slug, value in out["share reaching"].items():
            stash(f"reaching:{slug}", value)
        for slug, value in out["absolute by group"].items():
            stash(f"absolute group:{slug}", value)
        for slug, value in out["absolute contrasts"].items():
            stash(f"absolute contrast:{slug}", value)
        for key, value in out["delta"].items():
            delta_collected.setdefault(key, []).append(float(value))
        for name in ("rho", "icc", "marginal r2", "conditional r2"):
            stash(f"fit:{name}", out["model fit"][name])
    attempted = int(resamples)
    rate = failures / attempted if attempted else 0.0
    # COUNTED AGAINST EVERY RESAMPLE ATTEMPTED, whatever the reason none arrived: the adjusted
    # discard above, a rung the unadjusted fit could not reach, or a fit that raised.  Deriving
    # it from the primary contrast's own draw list rather than incrementing a counter is what
    # makes the three indistinguishable here, which is right, because the question the share
    # answers is how much of the interval is standing on nothing.
    unadjusted_failures = (
        attempted - len(collected.get(f"unadjusted contrast:{PRIMARY_CONTRAST_SLUG}", []))
        if unadjusted else 0)
    unadjusted_rate = unadjusted_failures / attempted if (unadjusted and attempted) else 0.0
    return {
        "draws": collected,
        "delta draws": delta_collected,
        "attempted": attempted,
        "failed": failures,
        "failure rate": rate,
        "instability trigger": bool(rate > BOOTSTRAP_FAILURE_SHARE_TRIGGER),
        "unadjusted failed": unadjusted_failures,
        "unadjusted failure rate": unadjusted_rate,
        "unadjusted instability trigger": bool(
            unadjusted and unadjusted_rate > BOOTSTRAP_FAILURE_SHARE_TRIGGER),
    }


# ======================================================================================
# (11) Manski bounds, the delta-shift curve, and the tipping point.
# ======================================================================================


def manski_from_daily(observed_totals: Any, missing_counts: Any) -> dict[str, np.ndarray]:
    """The assumption-free bounds, per episode.

    LOWER: every missing day contributes zero deficit, which is the naive estimator of 3.2 and
    the most favourable possible completion of the window.  UPPER: every missing day contributes
    a full deficit of one, that is, the participant took no steps at all on every unobserved
    day.  The daily deficit is bounded in the unit interval, so ANY completion of the window
    lies between the two, whatever the missingness mechanism.  That is the whole content of the
    bounds and the whole reason they are worth printing: they are the only statement in the
    paper that survives with no assumption about missingness whatsoever.
    """
    lower = np.asarray(observed_totals, dtype=float)
    missing = np.asarray(missing_counts, dtype=float)
    if np.any(missing < 0):
        raise DrdAnalysisError("a negative count of missing days reached the Manski bounds")
    return {"lower": lower, "upper": lower + missing}


def manski_bounds(variant: VariantData) -> dict[str, Any]:
    """Group-level bounds and, by interval arithmetic on a difference, contrast bounds.

    THEY BOUND THE QUANTITY PRINTED ABOVE THEM, which settles the row set and leaves it nothing
    to choose.  `marginal_debt` integrates over `estimand_window`, so a day inside the window
    that the episode was no longer at risk on is a day the point estimate PREDICTS FOR, exactly
    as a missing day is.  Bounding over the at-risk days alone, on the reasoning that no
    completion of a censored day is being claimed, would leave Table 2's footer calling these
    assumption-free bounds on a quantity they do not bound: an episode censored at day 30
    contributes five modelled days to the estimate and nothing at all to the bound, so the
    estimate could sit above the upper bound with no defect in either number.

    THE INVARIANT THAT USED TO CARRY THIS IS FALSE, which is why it is checked and not written
    down.  Rung 15 removes only the windows truncated by death or by a repeat operation; an
    episode censored inside days 1 to 35 by the observation cutoff stays in the analytic cohort
    with `censor_reason = cdr_observation_cutoff`, and the shipped fixture carries such an
    episode.  So the two row sets were never identical and the bounds never bracketed by
    construction.  They do now, and the equality is a stop condition below rather than a
    sentence here: a later edit that narrows either window has to move both or halt.

    The bounds are computed on every eligible episode, not only on the complete windows.
    """
    days = variant.days
    rows = estimand_window(variant)
    unit_pos = days["unit_pos"].to_numpy()[rows].astype(int)
    response = days["response"].to_numpy(dtype=float)[rows]
    observed = variant.observed[rows]
    bounded_days = _per_unit_sum(np.ones(unit_pos.size, dtype=float), unit_pos, variant.n_units)
    if not np.array_equal(bounded_days, variant.window_days_per_unit()):
        raise DrdAnalysisError(
            "the assumption-free bounds were computed over a different set of person-days from "
            "the one the point estimate integrates and the normalized-activity column divides "
            "by. A bound over fewer days than the estimate covers is not a bound on the "
            "estimate, whatever the footer beneath it says."
        )
    contribution = np.where(observed & np.isfinite(response), np.clip(response, 0.0, 1.0), 0.0)
    totals = _per_unit_sum(contribution, unit_pos, variant.n_units)
    # A DAY THAT IS NOT OBSERVED, for whichever of the two reasons.  The daily deficit is
    # bounded in the unit interval on a censored day exactly as it is on a missing one, so both
    # widen the bound by one and neither is completed by an assumption.
    missing = _per_unit_sum((~observed).astype(float), unit_pos, variant.n_units)
    per_unit = manski_from_daily(totals, missing)

    fusion = variant.episodes["fusion"].to_numpy().astype(bool)
    region = variant.episodes["region"].to_numpy(dtype=object)
    group_of_unit = group_slug_for(variant.spec, region, fusion)
    by_group: dict[str, dict[str, float]] = {}
    for slug in report_groups(variant.spec):
        if slug == ALL_GROUPS_SLUG:
            members = np.ones(variant.n_units, dtype=bool)
        else:
            members = (group_of_unit == slug)
        if not np.any(members):
            continue
        by_group[slug] = {
            "lower": float(per_unit["lower"][members].mean()),
            "upper": float(per_unit["upper"][members].mean()),
            "n": int(members.sum()),
        }

    out: dict[str, Any] = {"by group": by_group, "per unit": per_unit,
                           "computed on": "every eligible episode"}
    if variant.spec.has_fusion:
        fusion_low = float(per_unit["lower"][fusion].mean()) if np.any(fusion) else float("nan")
        fusion_high = float(per_unit["upper"][fusion].mean()) if np.any(fusion) else float("nan")
        other = ~fusion
        decomp_low = float(per_unit["lower"][other].mean()) if np.any(other) else float("nan")
        decomp_high = float(per_unit["upper"][other].mean()) if np.any(other) else float("nan")
        lower = fusion_low - decomp_high
        upper = fusion_high - decomp_low
        out["contrast"] = {"lower": lower, "upper": upper,
                           "crosses zero": bool(lower <= 0.0 <= upper),
                           "n fusion": int(fusion.sum()), "n decompression": int(other.sum())}
    return out


def implied_deficit_at_reference(delta: float,
                                 reference: float = DELTA_REFERENCE_DEFICIT) -> float:
    """What a given shift means for a day whose observed-equivalent deficit is 30%.

    ANALYSIS-PLAN 3.11 requires the translation to be COMPUTED and never hand-typed, so that a
    reader can judge for themselves whether the tipping shift describes a plausible world or an
    absurd one.
    """
    return float(expit(logit(np.array([reference]))[0] + float(delta)))


def delta_grid(extended: bool = False) -> tuple[float, ...]:
    """The prespecified grid, and its prespecified extension and no further.

    Writing the extension rule down before the measurement exists is what stops it from being an
    extension invented later.
    """
    if not extended:
        return DELTA_GRID
    values = list(DELTA_GRID)
    step = DELTA_EXTENSION_STEP
    current = DELTA_GRID[-1] + step
    while current <= DELTA_EXTENSION_LAST + FLOAT_TOLERANCE:
        values.append(round(current, 10))
        current += step
    return tuple(values)


def first_crossing(deltas: Sequence[float], values: Sequence[float]) -> dict[str, Any]:
    """The smallest grid shift at which the curve has crossed zero, and whether it really did.

    THE CROSSING IS CHECKED, NOT ASSUMED.  The curve must be monotone in the shift for a
    "tipping point" to mean anything at all, so monotonicity is tested and reported; and the
    reported crossing must have a strictly positive value at the previous grid point, so that a
    curve which started at or below zero is reported as "already at or below zero" rather than
    as a tipping point of zero, which would be a different and much weaker claim.
    """
    grid = [float(d) for d in deltas]
    curve = [float(v) for v in values]
    if len(grid) != len(curve):
        raise DrdAnalysisError("the shift grid and the contrast curve are different lengths")
    if len(grid) < 2:
        raise DrdAnalysisError("a tipping point needs at least two grid points")
    monotone = all(curve[i + 1] <= curve[i] + MONOTONE_TOLERANCE for i in range(len(curve) - 1))
    if curve[0] <= 0.0:
        return {"delta": None, "crossed": False, "monotone": monotone,
                "already at or below zero": True}
    for i in range(1, len(grid)):
        if curve[i] <= 0.0 < curve[i - 1]:
            return {"delta": grid[i], "crossed": True, "monotone": monotone,
                    "already at or below zero": False,
                    "value before": curve[i - 1], "value after": curve[i]}
    return {"delta": None, "crossed": False, "monotone": monotone,
            "already at or below zero": False}


def first_interval_crossing(deltas: Sequence[float], lows: Sequence[float],
                            highs: Sequence[float]) -> dict[str, Any]:
    """The smallest grid shift at which the 95% interval first includes zero."""
    grid = [float(d) for d in deltas]
    if not (len(grid) == len(lows) == len(highs)):
        raise DrdAnalysisError("the shift grid and its interval bounds are different lengths")
    for i, delta in enumerate(grid):
        low, high = float(lows[i]), float(highs[i])
        if math.isfinite(low) and math.isfinite(high) and low <= 0.0 <= high:
            return {"delta": delta, "crossed": True, "already includes zero": i == 0}
    return {"delta": None, "crossed": False, "already includes zero": False}


# ======================================================================================
# (12) The node grammar.
#
#      EXPORT-CONTRACT section 2.  Everything numeric in `results.json` is one of six shapes and
#      a consumer never meets a bare float where a node is specified.  A SUPPRESSED VALUE IS AN
#      OBJECT carrying `"suppressed": true` and NO NUMERIC KEY AT ALL: the number is not in the
#      file.  Any arithmetic on it raises a type error at the exact expression that mishandled
#      it, which is the property a sentinel string and a null both give up.
#
#      TWO QUESTIONS, ASKED IN THIS ORDER, AND THEY ARE NOT THE SAME QUESTION.  `disclosable(n)`
#      asks whether a TRUE count may be disclosed at all and is the single arbiter of the floor.
#      `is_legal_disclosed_count(cell)` asks whether an ALREADY-ROUNDED cell is a legal thing to
#      write down.  On the number 20 they differ, and collapsing them refuses correctly rounded
#      output.  A continuous statistic is NEVER rounded to 20; it is rounded to the decimals for
#      its unit and is disclosable only when the count contributing to it clears the floor.
# ======================================================================================

_EN_DASH = chr(0x2013)


def _assert_display(text: str) -> str:
    """No display string carries a banned character.  Checked on the RENDERED string, at the
    moment it is built, rather than grepped for afterwards."""
    if EM_DASH in text:
        raise DisclosureError("a display string contains an em-dash, which is banned")
    if MINUS_SIGN in text:
        raise DisclosureError("a display string contains a Unicode minus sign, which is banned")
    return text


def _format_number(value: float, unit: str) -> str:
    """One number rendered at the decimals its unit fixes, with the house thousands separator
    where the unit calls for one."""
    if unit not in UNIT_DECIMALS:
        raise DrdAnalysisError(f"{unit!r} is not a unit this contract defines")
    if not np.isfinite(value):
        raise DrdAnalysisError("a non-finite number reached the renderer, which means an "
                               "estimate was not computed and should have been suppressed")
    decimals = UNIT_DECIMALS[unit]
    if unit in THOUSANDS_SEPARATOR_UNITS:
        return f"{value:,.{decimals}f}"
    return f"{value:.{decimals}f}"


def _with_percent(text: str, unit: str) -> str:
    return f"{text}%" if unit == "percent" else text


def suppressed_node(reason: str) -> dict[str, Any]:
    """The one suppression shape, for every node type.  Four keys and no number."""
    if reason not in SUPPRESSION_SENTENCES:
        raise DrdAnalysisError(f"{reason!r} is not a suppression reason the contract defines")
    sentence = SUPPRESSION_SENTENCES[reason]
    return {"suppressed": True, "reason": reason, "reason_display": _assert_display(sentence),
            "display": _assert_display(sentence)}


def node_is_suppressed(node: Mapping[str, Any]) -> bool:
    """Whether a node carries no number.  Named apart from `disclosure.is_suppressed`, which
    asks a different question of a rendered STRING, because two predicates with one name is how
    a rendered cell and a node come to be confused for each other."""
    return bool(node.get("suppressed", False))


def count_node(true_count: Any, *, reason: str = "cell_below_threshold") -> dict[str, Any]:
    """A count.  The floor is tested on the TRUE integer and the rounding happens after."""
    if not disclosable(true_count):
        return suppressed_node(reason)
    rounded = round20(int(true_count))
    if not is_legal_disclosed_count(rounded):
        raise DisclosureError("a rounded count came back illegal, which means the rounding and "
                              "the floor disagree about the same number")
    return {"suppressed": False, "n": int(rounded), "rounded": int(true_count) != 0,
            "display": _assert_display(f"{int(rounded):,}")}


def percentage_node(numerator: Any, denominator: Any) -> dict[str, Any]:
    """A percentage with a real numerator, computed from the ROUNDED numerator over the ROUNDED
    denominator and printed to zero decimals.

    Both halves matter.  Zero decimals, because a one-decimal percentage against a rounded
    denominator lets a reader back-calculate an exact small numerator.  A rounded denominator,
    because it makes every printed percentage reproducible from the printed counts and removes
    the raw denominator from the computation entirely.  A percentage is suppressed whenever its
    numerator is, because a percentage times a disclosed denominator recovers the hidden count.
    """
    if not disclosable(denominator):
        return suppressed_node("cell_below_threshold")
    if not disclosable(numerator):
        return suppressed_node("numerator_suppressed")
    num = int(round20(int(numerator)))
    den = int(round20(int(denominator)))
    if den == 0:
        return suppressed_node("cell_below_threshold")
    pct = int(round(100.0 * num / den))
    return {"suppressed": False, "pct": pct, "num": num, "den": den,
            "display": _assert_display(f"{pct}%"),
            "display_count": _assert_display(f"{num:,}"),
            "display_denominator": _assert_display(f"{den:,}")}


def estimate_node(est: float, lo: float, hi: float, unit: str, *,
                  contributing_n: Any, reason: str = "contributing_n_below_threshold",
                  ) -> dict[str, Any]:
    """An estimate with a confidence interval.  The interval separator is the WORD "to", always,
    because a confidence interval may cross zero and a column that switches separator by sign is
    worse than one that never switches."""
    if not disclosable(contributing_n):
        return suppressed_node(reason)
    if not all(np.isfinite(v) for v in (est, lo, hi)):
        return suppressed_node("not_estimable_convergence")
    point = _with_percent(_format_number(float(est), unit), unit)
    low = _with_percent(_format_number(float(lo), unit), unit)
    high = _with_percent(_format_number(float(hi), unit), unit)
    interval = f"95% CI {low} to {high}"
    return {"suppressed": False, "est": round(float(est), UNIT_DECIMALS[unit]),
            "lo": round(float(lo), UNIT_DECIMALS[unit]),
            "hi": round(float(hi), UNIT_DECIMALS[unit]),
            "level": CONFIDENCE_LEVEL, "unit": unit,
            "display": _assert_display(f"{point} ({interval})"),
            "display_point": _assert_display(point),
            "display_ci": _assert_display(interval)}


def bound_node(value: float, unit: str, *, contributing_n: Any) -> dict[str, Any]:
    """A Manski bound: an estimate node whose interval keys collapse onto the point.

    A bound IS NOT AN INTERVAL, and giving it interval keys would invite a renderer to print it
    as a confidence interval, which is a different and much stronger claim.  `display_ci` is
    deliberately empty for exactly that reason.
    """
    if not disclosable(contributing_n):
        return suppressed_node("contributing_n_below_threshold")
    if not np.isfinite(value):
        return suppressed_node("not_estimable_data_unavailable")
    point = _with_percent(_format_number(float(value), unit), unit)
    return {"suppressed": False, "est": round(float(value), UNIT_DECIMALS[unit]),
            "lo": round(float(value), UNIT_DECIMALS[unit]),
            "hi": round(float(value), UNIT_DECIMALS[unit]),
            "level": CONFIDENCE_LEVEL, "unit": unit,
            "display": _assert_display(point),
            "display_point": _assert_display(point),
            "display_ci": ""}


def quantile_triple(values: Any) -> tuple[float, float, float]:
    """`(median, 25th, 75th)` of the finite values, in the order the contract's quantile node
    takes them, or three NaNs when there is nothing to take them of.

    The ORDER is the contract's and not the intuitive one: `quantile_node(q50, q25, q75)` puts
    the point estimate first, exactly as every other node in the grammar does, so a renderer
    reading the first element of any node gets the number the row is about.
    """
    array = np.asarray([v for v in np.asarray(values, dtype=float) if np.isfinite(v)])
    if array.size == 0:
        return float("nan"), float("nan"), float("nan")
    q25, q50, q75 = (float(np.percentile(array, q)) for q in (25.0, 50.0, 75.0))
    return q50, q25, q75


def quantile_node(values: Any, unit: str, *, contributing_n: Any) -> dict[str, Any]:
    """An observed median and interquartile range, from the values themselves."""
    return quantile_node_from(*quantile_triple(values), unit, contributing_n=contributing_n)


def quantile_node_from(q50: float, q25: float, q75: float, unit: str, *,
                       contributing_n: Any) -> dict[str, Any]:
    """The same node, from an already-computed triple.  The separator is the en-dash, because a
    quantile range of a non-negative quantity never carries a sign."""
    if not disclosable(contributing_n):
        return suppressed_node("contributing_n_below_threshold")
    if not all(np.isfinite(v) for v in (q50, q25, q75)):
        return suppressed_node("not_estimable_data_unavailable")
    low = _format_number(q25, unit)
    mid = _format_number(q50, unit)
    high = _format_number(q75, unit)
    iqr = f"{low}{_EN_DASH}{high}"
    return {"suppressed": False, "q50": round(q50, UNIT_DECIMALS[unit]),
            "q25": round(q25, UNIT_DECIMALS[unit]), "q75": round(q75, UNIT_DECIMALS[unit]),
            "unit": unit, "display": _assert_display(f"{mid} ({iqr})"),
            "display_point": _assert_display(mid), "display_iqr": _assert_display(iqr)}


def pvalue_node(p: float, *, contributing_n: Any) -> dict[str, Any]:
    """A P value in house style.  No P value in this plan selects anything."""
    if not disclosable(contributing_n):
        return suppressed_node("contributing_n_below_threshold")
    if not np.isfinite(p):
        return suppressed_node("not_estimable_convergence")
    floored = bool(p < 0.001)
    display = "P < 0.001" if floored else f"P = {p:.3f}"
    return {"suppressed": False, "p": float(p), "floored": floored,
            "display": _assert_display(display)}


def scalar_node(value: Any, unit: str | None = None) -> dict[str, Any]:
    """A constant that is not a result: a window boundary, a threshold, a seed.  Never
    suppressed, so it carries no suppression key at all."""
    if isinstance(value, (int, np.integer)) and unit is None:
        return {"value": int(value), "display": _assert_display(f"{int(value):,}")}
    if unit is None:
        return {"value": value, "display": _assert_display(str(value))}
    return {"value": float(value), "display": _assert_display(_format_number(float(value), unit))}


# ======================================================================================
# (13) Building the primary variant and every row of the ladder.
#
#      SENSITIVITY DEFICITS ARE NOT PRECOMPUTED.  DAG-SCHEMA 8.11 hands that one recomputation
#      over deliberately, because four more float columns on the daily panel would widen the
#      table for every downstream read and BigQuery bills columns.  They are recomputed here
#      from `drd_daily.steps` and the alternative baselines on `features`, joined on the
#      episode, and a NULL step count still yields a NULL deficit at every one of them.
#
#      A SENSITIVITY FITTED WHERE ITS OWN BASELINE EXISTS HAS ITS OWN DENOMINATOR, and Table 2
#      must print it.  Every restriction below records the episodes it could not use, and a
#      contrast printed against the analytic `n` when it was fitted on fewer episodes is a
#      mislabelled number that nothing about the estimate reveals.
# ======================================================================================


def _episode_positions(episodes: pd.DataFrame) -> pd.Series:
    """Position of each `unit index` in the episode frame, so the panel can be joined without
    either frame carrying a participant key."""
    return pd.Series(np.arange(len(episodes)), index=episodes["unit_index"].to_numpy())


def prepare_primary(panel: pd.DataFrame, episodes: pd.DataFrame,
                    spec: ModelSpec) -> VariantData:
    """The primary variant: the locked window, the locked wear rule, the locked baseline."""
    ordered = episodes.sort_values("unit_index").reset_index(drop=True)
    lookup = _episode_positions(ordered)
    unit_pos = lookup.reindex(panel["unit_index"].to_numpy()).to_numpy()
    if np.any(pd.isna(unit_pos)):
        raise DrdAnalysisError(
            "the person-day panel carries an episode the covariate frame does not, so the two "
            "queries did not see the same cohort. Nothing is fitted on a mismatched join."
        )
    days = pd.DataFrame({
        "unit_pos": unit_pos.astype(int),
        "day": panel["post_discharge_day"].to_numpy(dtype=int),
        "postoperative_day": panel["postoperative_day"].to_numpy(dtype=int),
        "dow": panel["day_of_week"].to_numpy(dtype=int),
        "is_weekend": panel["is_weekend"].to_numpy().astype(bool),
        "steps": panel["steps"].to_numpy(dtype=float),
        "response": panel["deficit"].to_numpy(dtype=float),
        "response_untruncated": panel["deficit_untruncated"].to_numpy(dtype=float),
        "observed": panel["is_analyzable"].to_numpy().astype(bool),
        "at_risk": ~panel["is_censored"].to_numpy().astype(bool),
        "in_window": panel["in_accrual_window"].to_numpy().astype(bool),
        "in_pod_window": panel["in_pod_anchored_window"].to_numpy().astype(bool),
        "is_inpatient": panel["is_inpatient"].to_numpy().astype(bool),
        "lag": panel["lagged_wear_fraction"].to_numpy(dtype=float),
        "valid_wear_s1": panel["valid_wear_s1"].to_numpy().astype(bool),
        "valid_wear_s2": panel["valid_wear_s2"].to_numpy().astype(bool),
        "valid_wear_s3": panel["valid_wear_s3"].to_numpy().astype(bool),
        "valid_wear_s4": panel["valid_wear_s4"].to_numpy().astype(bool),
        "baseline_day": ordered["baseline_steps"].to_numpy(dtype=float)[unit_pos.astype(int)],
    })
    zero_imputed = int(np.sum(np.isfinite(days["response"].to_numpy(dtype=float))
                              & ~days["observed"].to_numpy().astype(bool)))
    if zero_imputed:
        raise DrdAnalysisError(
            "a daily deficit is present on a day the panel calls unobserved. A deficit on an "
            "unobserved day is a zero-imputation, and a zero deficit asserts the participant "
            "walked at or above their own preoperative baseline on a day nobody measured. "
            "The estimator does not run on a panel that carries one."
        )
    return VariantData("primary", ordered, days, spec)


def _restrict_units(variant: VariantData, keep: np.ndarray, *, slug: str,
                    note: str = "") -> VariantData:
    """A variant restricted to a subset of episodes, renumbered so the design stays dense."""
    keep = np.asarray(keep, dtype=bool)
    if not np.any(keep):
        raise DrdAnalysisError(f"the row {slug} kept no episode at all")
    mapping = -np.ones(variant.n_units, dtype=int)
    mapping[np.where(keep)[0]] = np.arange(int(keep.sum()))
    positions = variant.days["unit_pos"].to_numpy().astype(int)
    rows = keep[positions]
    days = variant.days.iloc[np.where(rows)[0]].copy()
    days["unit_pos"] = mapping[positions[rows]]
    episodes = variant.episodes.iloc[np.where(keep)[0]].reset_index(drop=True)
    return VariantData(slug, episodes, days, variant.spec,
                       bounded_response=variant.bounded_response, note=note)


def _with_response(variant: VariantData, *, slug: str, response: np.ndarray,
                   observed: np.ndarray | None = None,
                   baseline_day: np.ndarray | None = None,
                   in_window: np.ndarray | None = None,
                   bounded_response: bool = True, note: str = "") -> VariantData:
    days = variant.days.copy()
    days["response"] = np.asarray(response, dtype=float)
    if observed is not None:
        days["observed"] = np.asarray(observed, dtype=bool)
    if baseline_day is not None:
        days["baseline_day"] = np.asarray(baseline_day, dtype=float)
    if in_window is not None:
        days["in_window"] = np.asarray(in_window, dtype=bool)
    return VariantData(slug, variant.episodes, days, variant.spec,
                       bounded_response=bounded_response, note=note)


def _alternative_baseline_variant(primary: VariantData, *, slug: str, baseline_column: str,
                                  wear_column: str | None = None) -> VariantData:
    """One row of ladder rows 6 and 7: a different baseline, a different wear rule, or both.

    Changing the wear rule changes `B_i` ITSELF, because it changes which days are valid, which
    is why a wear sensitivity cannot be run by swapping a flag at model time and why the four
    alternative baselines exist.  The row is fitted where its own baseline exists and the
    episodes it could not use are counted.
    """
    baseline = primary.episodes[baseline_column].to_numpy(dtype=float)
    keep = np.isfinite(baseline) & (baseline > 0)
    restricted = _restrict_units(primary, keep, slug=slug)
    base_by_day = restricted.episodes[baseline_column].to_numpy(dtype=float)[
        restricted.days["unit_pos"].to_numpy().astype(int)]
    steps = restricted.days["steps"].to_numpy(dtype=float)
    response = daily_deficit(steps, base_by_day)
    if wear_column is None:
        observed = restricted.days["observed"].to_numpy().astype(bool)
    else:
        observed = (restricted.days[wear_column].to_numpy().astype(bool)
                    & np.isfinite(steps)
                    & restricted.days["at_risk"].to_numpy().astype(bool))
    return _with_response(restricted, slug=slug, response=response, observed=observed,
                          baseline_day=base_by_day,
                          note=f"fitted where {baseline_column.replace('_', ' ')} exists")


def _split_baseline_variant(primary: VariantData) -> VariantData:
    """The supplementary split-baseline row.

    The denominator is derived from the two DAY COUNTS and never from the two medians being
    non-null, so the minimum-day rule stays visible and auditable in one place instead of hiding
    inside a null test a later edit could weaken.  An episode with valid days in only one half
    of the week is excluded from THIS ROW AND FROM NOTHING ELSE: it keeps its primary baseline,
    stays in the analytic cohort, and contributes to the primary estimand exactly as before.
    There is no fallback substituting the surviving half's median or the pooled baseline,
    because either would turn the row into a debt measured against a reference that is
    day-type-matched on some episodes and not on others.
    """
    episodes = primary.episodes
    weekday_days = episodes["n_valid_baseline_days_weekday"].to_numpy(dtype=float)
    weekend_days = episodes["n_valid_baseline_days_weekend"].to_numpy(dtype=float)
    keep = ((weekday_days >= SPLIT_BASELINE_MIN_WEEKDAY_DAYS)
            & (weekend_days >= SPLIT_BASELINE_MIN_WEEKEND_DAYS))
    restricted = _restrict_units(primary, keep, slug="baseline_weekday_weekend_split")
    positions = restricted.days["unit_pos"].to_numpy().astype(int)
    weekday = restricted.episodes["baseline_steps_weekday"].to_numpy(dtype=float)[positions]
    weekend = restricted.episodes["baseline_steps_weekend"].to_numpy(dtype=float)[positions]
    is_weekend = restricted.days["is_weekend"].to_numpy().astype(bool)
    base_by_day = np.where(is_weekend, weekend, weekday)
    response = daily_deficit(restricted.days["steps"].to_numpy(dtype=float), base_by_day)
    return _with_response(restricted, slug="baseline_weekday_weekend_split", response=response,
                          baseline_day=base_by_day,
                          note="fitted where both halves of the week carry a baseline")


def build_plotted_variant(slug: str, primary: VariantData) -> VariantData:
    """One plotted sensitivity row as a variant, or a raise naming why it cannot be one.

    Three of the fourteen are not a variant of the daily model at all and are handled by their
    own estimator: the complete-window direct regression, the delta-shift panel, and the
    weighting row, which is the same data with the weight decision flipped.
    """
    if slug == "pod_anchored_window":
        return _with_response(primary, slug=slug,
                              response=primary.days["response"].to_numpy(dtype=float),
                              in_window=primary.days["in_pod_window"].to_numpy().astype(bool),
                              note="accrual over postoperative days 8 to 42")
    if slug == "inpatient_days_censored":
        window = (primary.days["in_window"].to_numpy().astype(bool)
                  & ~primary.days["is_inpatient"].to_numpy().astype(bool))
        return _with_response(primary, slug=slug,
                              response=primary.days["response"].to_numpy(dtype=float),
                              in_window=window,
                              note="days inside a readmission stay removed from the window")
    if slug == "observation_weighted":
        return VariantData(slug, primary.episodes, primary.days, primary.spec,
                           note="the weight decision of the primary rung, reversed")
    if slug in ("wear_definition_s1", "wear_definition_s2", "wear_definition_s3",
                "wear_definition_s4"):
        suffix = slug.rsplit("_", 1)[1]
        return _alternative_baseline_variant(primary, slug=slug,
                                             baseline_column=f"baseline_steps_{suffix}",
                                             wear_column=f"valid_wear_{suffix}")
    if slug == "baseline_window_60_15":
        return _alternative_baseline_variant(primary, slug=slug,
                                             baseline_column="baseline_steps_60_15")
    if slug == "baseline_window_30_1":
        return _alternative_baseline_variant(primary, slug=slug,
                                             baseline_column="baseline_steps_30_1")
    if slug == "device_change_excluded":
        keep = ~primary.episodes["device_changed"].to_numpy().astype(bool)
        return _restrict_units(primary, keep, slug=slug,
                               note="participants changing device model excluded")
    if slug == "baseline_floor":
        keep = primary.episodes["meets_baseline_floor"].to_numpy().astype(bool)
        return _restrict_units(primary, keep, slug=slug,
                               note="restricted to a baseline at or above the floor")
    if slug == "debt_untruncated":
        return _with_response(
            primary, slug=slug,
            response=primary.days["response_untruncated"].to_numpy(dtype=float),
            bounded_response=False,
            note="the truncation at zero removed, so the response can be negative")
    raise DrdAnalysisError(f"{slug!r} is not a plotted row this module builds as a variant")


def complete_window_debt(primary: VariantData) -> tuple[np.ndarray, np.ndarray]:
    """The naive estimator of 3.2: direct summation on the episodes with a complete window.

    Reporting it is not a concession.  It is the anchor that lets a reader see how far the
    modelled estimate moved and in which direction, and it is the unadjusted column of Table 2,
    labelled the naive estimator and printed against ITS OWN denominator, which is not the
    analytic cohort's.
    """
    days = primary.days
    rows = primary.in_window & primary.at_risk
    unit_pos = days["unit_pos"].to_numpy()[rows].astype(int)
    response = days["response"].to_numpy(dtype=float)[rows]
    observed = primary.observed[rows]
    contribution = np.where(observed & np.isfinite(response), response, 0.0)
    totals = _per_unit_sum(contribution, unit_pos, primary.n_units)
    observed_days = _per_unit_sum(observed.astype(float), unit_pos, primary.n_units)
    window_days = primary.window_days_per_unit()
    complete = (observed_days >= window_days - FLOAT_TOLERANCE) & (window_days >= WINDOW_LENGTH_DAYS)
    return totals, complete


def direct_regression_on(subset: VariantData, totals: np.ndarray) -> float:
    """The standardized fusion contrast from an ordinary regression of the SUMMED debt on the
    covariate set.  One number per episode, so there is no day term and no marginalization."""
    import statsmodels.api as sm

    if not subset.spec.has_fusion or subset.n_units == 0:
        return float("nan")
    builder = DesignBuilder(subset.episodes, subset.spec)
    everyone = np.arange(subset.n_units)
    design, _ = builder.episode_matrix(everyone)
    values = np.asarray(totals, dtype=float)
    if values.size != subset.n_units:
        raise DrdAnalysisError("the summed debt and the episode frame are different lengths")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = sm.OLS(values, design).fit()
    params = np.asarray(fit.params, dtype=float)

    def predict(fusion: bool) -> float:
        matrix, _ = builder.episode_matrix(everyone, fusion=fusion)
        if matrix.shape[1] != params.size:
            return float("nan")
        return float((matrix @ params).mean())

    return predict(True) - predict(False)


def direct_regression_contrast(primary: VariantData, totals: np.ndarray,
                               complete: np.ndarray) -> float:
    """Sensitivity row 3: the summed debt on complete windows, regressed on the covariate set
    and standardized the same way the primary is, so the two are on one scale."""
    if not np.any(complete):
        return float("nan")
    subset = _restrict_units(primary, complete, slug="complete_window_direct_regression")
    return direct_regression_on(subset, np.asarray(totals, dtype=float)[complete])


def impute_body_mass_index(episodes: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """One imputation of the missing body mass index, drawn from a regression on the covariates
    that are complete by construction.

    The plan asks for twenty imputations with the master seed in place of the missing indicator,
    and this is one of them.  The indicator is switched off in the imputed frame, which is the
    whole point of the row: it asks what the missing-indicator convention costs.
    """
    import statsmodels.api as sm

    frame = episodes.copy()
    bmi = frame["bmi_imputed"].to_numpy(dtype=float)
    missing = frame["bmi_missing"].to_numpy().astype(bool)
    if not np.any(missing) or np.all(missing):
        frame["bmi_missing"] = False
        return frame
    predictors = np.column_stack([
        np.ones(len(frame)),
        frame["age_at_index"].fillna(frame["age_at_index"].median()).to_numpy(dtype=float),
        (frame["sex_at_birth"].to_numpy(dtype=object) == "male").astype(float),
        frame["charlson_ordinal"].to_numpy(dtype=object) != "0",
        np.log1p(np.maximum(frame["los_days"].to_numpy(dtype=float), 0.0)),
        frame["fusion"].to_numpy().astype(float),
    ]).astype(float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = sm.OLS(bmi[~missing], predictors[~missing, :]).fit()
    mean = predictors[missing, :] @ np.asarray(fit.params, dtype=float)
    scale = float(np.sqrt(max(fit.scale, FLOAT_TOLERANCE)))
    drawn = mean + rng.normal(0.0, scale, size=int(missing.sum()))
    bmi = bmi.copy()
    bmi[missing] = np.clip(drawn, 10.0, 80.0)
    frame["bmi_imputed"] = bmi
    frame["bmi_missing"] = False
    return frame


# ======================================================================================
# (14) Running one sensitivity row, and the two rows that are not a variant of the daily model.
# ======================================================================================


def not_estimable_row(row: Mapping[str, Any], reason: str, *, render: str | None = None,
                      true_n: int = 0) -> dict[str, Any]:
    """A row that could not be fitted, printed rather than omitted, in RAW form.

    Silent omission itself leaks: a reader who counts the rows learns exactly which of them fell
    short.  The row keeps its order, its label and its axis, and says why in one of the
    contract's own sentences, which the exporter resolves from `not_estimable_reason`.

    `true_n` IS THE COUNT THE ROW WAS ATTEMPTED ON AND NOT A PLACEHOLDER.  A row that failed to
    converge on 340 episodes is a different fact from a row the derived build could not assemble
    at all, and the default of zero is the honest answer to the second: no episode contributed,
    because there was nothing to fit.  The exporter floor-tests it like any other count.
    """
    if reason not in SUPPRESSION_SENTENCES:
        raise DrdAnalysisError(f"{reason!r} is not a suppression reason the contract defines")
    return {
        "order": int(row["order"]) if "order" in row else 0,
        "sub_order": int(row["sub"]) if "sub" in row else 1,
        "display_label": row["display"],
        "estimate": None,
        "p": None,
        "true_n": int(true_n),
        "estimable": False,
        "not_estimable_reason": reason,
        "axis": row.get("axis", "primary"),
        "render": render or row.get("render", "marker"),
        "varies": row["varies"],
        "direction_matches_primary": False,
    }


def run_sensitivity_row(
    row: Mapping[str, Any],
    variant: VariantData,
    *,
    resamples: int,
    point_rung_index: int,
    r_runner: Callable[..., Mapping[str, Any]] | None,
    draws: int,
    primary_estimate: float,
    apply_weights: bool = True,
    include_lag: bool = True,
    include_baseline_steps: bool = False,
    min_rung: int | None = None,
) -> dict[str, Any]:
    """One row of the ladder: the primary contrast, re-estimated with exactly one thing changed.

    The row carries `B = 500` resamples rather than the primary's 1,000 because sensitivity rows
    are read for direction and overlap rather than for a reported P value, and the reduction is
    stated rather than hidden.
    """
    floor = int(point_rung_index if min_rung is None else min_rung)
    n_units = int(np.unique(variant.days["unit_pos"].to_numpy()[variant.fit_rows]).size)
    try:
        point = estimate_variant(variant, r_runner=r_runner, draws=draws, seed_spec=SEED,
                                 include_lag=include_lag, apply_weights=apply_weights,
                                 include_baseline_steps=include_baseline_steps,
                                 min_rung=floor, min_rung_trigger=None)
    except BOOTSTRAP_FAILURES:
        return not_estimable_row(row, "not_estimable_convergence", true_n=n_units)
    if PRIMARY_CONTRAST_SLUG not in point["contrasts"]:
        return not_estimable_row(row, "not_estimable_cell_size", true_n=n_units)
    estimate = float(point["contrasts"][PRIMARY_CONTRAST_SLUG])
    boot = clustered_bootstrap(
        variant, resamples=resamples, point_rung_index=int(point["ladder"]["rung index"]),
        r_runner=r_runner, draws=draws, include_lag=include_lag, apply_weights=apply_weights,
        include_baseline_steps=include_baseline_steps, min_rung=floor, min_rung_trigger=None)
    values = boot["draws"].get(f"contrast:{PRIMARY_CONTRAST_SLUG}", [])
    lo, hi = percentile_interval(values, attempted=boot["attempted"])
    bootstrap = {"attempted": boot["attempted"], "failed": boot["failed"],
                 "failure rate": boot["failure rate"],
                 "instability trigger": bool(boot["instability trigger"])}
    if boot["instability trigger"]:
        # THE INSTABILITY HAS TO CROSS THE BOUNDARY OR IT DOES NOT EXIST.  On the primary,
        # trigger T4 descends the family ladder and the whole estimate is recomputed; a
        # sensitivity row has no ladder of its own to descend, and none of the keys the exporter
        # reads from a row carries a failure rate, so an unstable row that returned an ordinary
        # interval would be plotted beside the stable ones with nothing to tell them apart.  The
        # row is returned NOT ESTIMABLE instead, which the exporter renders as a suppressed
        # marker and records in `results.json.suppressed`, and the rate stays on the row for
        # the diagnostics.
        out = not_estimable_row(row, "not_estimable_convergence", true_n=n_units)
        out.update({"bootstrap": bootstrap, "fitted set note": variant.note,
                    "rung index": int(point["ladder"]["rung index"])})
        return out
    matches = bool(np.isfinite(primary_estimate) and np.isfinite(estimate)
                   and (estimate >= 0) == (primary_estimate >= 0))
    triple = _triple(estimate, (lo, hi))
    return {
        "order": int(row["order"]),
        "sub_order": int(row["sub"]),
        "display_label": row["display"],
        "estimate": triple,
        "p": bootstrap_pvalue(values),
        "true_n": n_units,
        "estimable": _all_finite(triple),
        "not_estimable_reason": None if _all_finite(triple) else "not_estimable_convergence",
        "axis": row["axis"],
        "render": row["render"],
        "varies": row["varies"],
        "direction_matches_primary": matches,
        "bootstrap": bootstrap,
        "fitted set note": variant.note,
        "rung index": int(point["ladder"]["rung index"]),
    }


# ======================================================================================
# (15) The analysis: everything the export contract's `debt` and `sensitivity` blocks require.
# ======================================================================================


def delta_pairs(grid: Sequence[float]) -> tuple[tuple[float, str], ...]:
    """The shift grid crossed with its three application patterns.

    Applying the shift to BOTH groups equally moves both arms and mostly cancels in the
    contrast, which is itself informative and is plotted.  The REPORTED tipping point comes from
    the decompression-only pattern, because that is the direction that works AGAINST the study
    hypothesis: it makes the comparison group's unobserved days worse, shrinking the
    fusion-minus-decompression difference toward and past zero.
    """
    return tuple((float(d), application) for d in grid for application in DELTA_APPLICATIONS)


def _group_membership(variant: VariantData, slug: str) -> np.ndarray:
    if slug == ALL_GROUPS_SLUG:
        return np.ones(variant.n_units, dtype=bool)
    fusion = variant.episodes["fusion"].to_numpy().astype(bool)
    region = variant.episodes["region"].to_numpy(dtype=object)
    return group_slug_for(variant.spec, region, fusion) == slug


def analyze(
    panel: pd.DataFrame,
    episodes: pd.DataFrame,
    *,
    collapse: Mapping[str, Any],
    r_runner: Callable[..., Mapping[str, Any]] | None = None,
    draws: int = MONTE_CARLO_DRAWS,
    resamples_primary: int = BOOTSTRAP_PRIMARY,
    resamples_sensitivity: int = BOOTSTRAP_SENSITIVITY,
    run_sensitivity: bool = True,
    extras: Mapping[str, Any] | None = None,
    convergence_recheck: bool = True,
) -> dict[str, Any]:
    """The primary estimand, its contrasts, its bounds, its tipping point and its ladder.

    THE COLLAPSE LEVEL IS READ, NOT DECIDED.  It was fixed on the Phase 3 attrition ladder
    before any model existed, and a level decided after a model was fit is a stop condition of
    this plan rather than a judgment call.
    """
    extras = dict(extras or {})
    spec = ModelSpec(str(collapse["level"]), collapse.get("groups", ()))
    halting: list[str] = []
    if not spec.estimable:
        return {
            "drd ok": False,
            "halting": ["The analytic cohort is below the disclosure floor, so no estimand is "
                        "reported and the attrition ladder is the result"],
            "collapse": {"level": spec.level, "groups": spec.groups},
            "estimator": None, "debt": None, "sensitivity": {}, "supplementary": {},
            "diagnostics": {}, "gaps": tuple(DAG_GAPS),
        }

    primary = prepare_primary(panel, episodes, spec)
    grid = delta_pairs(delta_grid(extended=True))

    point = estimate_variant(primary, r_runner=r_runner, draws=draws, seed_spec=SEED,
                             deltas=grid, absolute=True, unadjusted=True)
    ladder = point["ladder"]
    rung_index = int(ladder["rung index"])

    # ANALYSIS-PLAN 3.3, the prespecified Monte Carlo convergence check.  It is a check on the
    # INTEGRATION, not on the model: the whole marginalization is recomputed on a different
    # stream and the primary contrast is compared, and the tolerance is about one seven-hundredth
    # of the 35-day scale.
    monte_carlo = {"draws": int(draws), "recheck draws": 0, "movement": 0.0, "escalated": False}
    if convergence_recheck and PRIMARY_CONTRAST_SLUG in point["contrasts"]:
        recheck = estimate_variant(primary, r_runner=r_runner, draws=MONTE_CARLO_RECHECK_DRAWS,
                                   seed_spec=[SEED, MONTE_CARLO_RECHECK_STREAM],
                                   min_rung=rung_index, min_rung_trigger=None)
        movement = abs(float(recheck["contrasts"].get(PRIMARY_CONTRAST_SLUG, float("nan")))
                       - float(point["contrasts"][PRIMARY_CONTRAST_SLUG]))
        monte_carlo.update({"recheck draws": MONTE_CARLO_RECHECK_DRAWS, "movement": movement})
        if np.isfinite(movement) and movement > MONTE_CARLO_TOLERANCE_ACTIVITY_DAYS:
            draws = MONTE_CARLO_ESCALATED_DRAWS
            point = estimate_variant(primary, r_runner=r_runner, draws=draws, seed_spec=SEED,
                                     deltas=grid, absolute=True, unadjusted=True,
                                     min_rung=rung_index, min_rung_trigger=None)
            ladder = point["ladder"]
            rung_index = int(ladder["rung index"])
            monte_carlo.update({"draws": draws, "escalated": True})

    # The unadjusted fit is resampled only when it produced a point estimate to resample around,
    # and it is judged against ITS OWN rung, which the adjusted ladder does not decide for it.
    unadjusted_rung = (int(point["unadjusted ladder"]["rung index"])
                       if point["unadjusted ladder"] is not None else None)
    boot = clustered_bootstrap(primary, resamples=resamples_primary,
                              point_rung_index=rung_index, r_runner=r_runner, draws=draws,
                              deltas=grid, absolute=True,
                              unadjusted=unadjusted_rung is not None,
                              unadjusted_rung_index=unadjusted_rung)
    if boot["instability trigger"] and rung_index < len(ESTIMATOR_RUNGS):
        # Trigger T4.  It descends ONE rung, and the whole point estimate and interval are
        # recomputed there.  The failure rate is reported whatever it is, before and after.
        # The unadjusted fit is under the same floor, because the floor is a property of this
        # variant and not of one design matrix, and it walks the rest of the ladder for itself.
        halting.append("Bootstrap instability fired the prespecified trigger and the ladder "
                       "descended one rung")
        point = estimate_variant(primary, r_runner=r_runner, draws=draws, seed_spec=SEED,
                                 deltas=grid, absolute=True, unadjusted=True,
                                 min_rung=rung_index + 1)
        ladder = point["ladder"]
        rung_index = int(ladder["rung index"])
        unadjusted_rung = (int(point["unadjusted ladder"]["rung index"])
                           if point["unadjusted ladder"] is not None else None)
        boot = clustered_bootstrap(primary, resamples=resamples_primary,
                                  point_rung_index=rung_index, r_runner=r_runner, draws=draws,
                                  deltas=grid, absolute=True, min_rung=rung_index,
                                  min_rung_trigger=None,
                                  unadjusted=unadjusted_rung is not None,
                                  unadjusted_rung_index=unadjusted_rung)

    totals, complete = complete_window_debt(primary)
    observed_days = _per_unit_sum(primary.observed[primary.in_window].astype(float),
                                  primary.days["unit_pos"].to_numpy()[primary.in_window],
                                  primary.n_units)
    bounds = manski_bounds(primary)

    debt = assemble_debt(primary, point=point, boot=boot, bounds=bounds, totals=totals,
                        complete=complete, observed_days=observed_days, draws=draws,
                        monte_carlo=monte_carlo)

    sensitivity: dict[str, Any] = {}
    supplementary: dict[str, Any] = {}
    if run_sensitivity:
        sensitivity = run_plotted_rows(
            primary, point=point, debt=debt, r_runner=r_runner, draws=draws,
            resamples=resamples_sensitivity, rung_index=rung_index, totals=totals,
            complete=complete)
        supplementary = run_supplementary_rows(
            primary, point=point, r_runner=r_runner, draws=draws,
            resamples=resamples_sensitivity, rung_index=rung_index, extras=extras)

    censored_in_window = int(np.sum(primary.in_window & ~primary.at_risk))
    diagnostics = {
        "monte carlo": monte_carlo,
        "weights": point["weights"],
        "weights reached the fit": weights_effective(point),
        "recovery": point["recovery"],
        "bootstrap": {"attempted": boot["attempted"], "failed": boot["failed"],
                      "failure rate": boot["failure rate"],
                      "instability trigger": boot["instability trigger"]},
        "censored person-days inside the window": censored_in_window,
        "episodes with a complete window": int(complete.sum()),
        "mean window days": point["mean window days"],
        "design columns": point["model fit"]["design columns"],
        "dropped columns": point["model fit"]["dropped columns"],
        "manski brackets the point estimate": _brackets(debt, bounds),
    }

    return {
        "drd ok": True,
        "halting": halting,
        "collapse": {"level": spec.level, "groups": spec.groups},
        "estimator": {
            "r_used": bool(ladder["r used"]),
            "rung_index": rung_index,
            "rung_slug": ladder["rung slug"],
            "rung_display": ladder["rung display"],
            "descent_triggers_fired": list(ladder["descent triggers fired"]),
            "fallback_reason": ladder["fallback reason"],
            "rungs_attempted": [dict(row) for row in ladder["rungs attempted"]],
            "bootstrap_failure_rate": percentage_node(boot["failed"], boot["attempted"]),
        },
        "debt": debt,
        "sensitivity": sensitivity,
        "supplementary": supplementary,
        "diagnostics": diagnostics,
        "gaps": tuple(DAG_GAPS),
    }


def _brackets(debt: Mapping[str, Any], bounds: Mapping[str, Any]) -> bool | None:
    """Whether the modelled contrast lies inside the assumption-free bounds.

    A DIAGNOSTIC AND NOT AN EXPORTED KEY.  The bounds bracket every completion of the observed
    days, so a modelled contrast outside them says the model's fitted values on OBSERVED days
    are far from the observed values there, which is a fit problem worth seeing rather than a
    contradiction in the bounds.
    """
    contrast = debt.get("contrasts", {}).get(PRIMARY_CONTRAST_SLUG, {})
    estimate = contrast.get("estimate")
    if estimate is None or "contrast" not in bounds:
        return None
    value = float(estimate[0])
    if not np.isfinite(value):
        return None
    return bool(bounds["contrast"]["lower"] - FLOAT_TOLERANCE <= value
                <= bounds["contrast"]["upper"] + FLOAT_TOLERANCE)


# ======================================================================================
# (16) What the derived build does not carry, reported rather than patched around.
#
#      Four supplementary rows of ANALYSIS-PLAN section 6 need a column or a whole second build
#      that `{DERIVED}` does not have.  This module does NOT grow a second implementation of a
#      definition that belongs in `build_all.sql`: it reports the row as not estimable for want
#      of data, names what the build would need, and accepts the input if a caller supplies it.
# ======================================================================================

DAG_GAPS: tuple[Mapping[str, str], ...] = tuple(MappingProxyType(gap) for gap in (
    {"row": "junctions_mirrored",
     "needs": "a second build of the whole derived dataset under the mirrored junction map, "
              "which changes the eligibility ladder itself because a cervicothoracic-only "
              "episode moves from cervical to thoracic and therefore from included to excluded",
     "supply": "a second prepared panel and episode frame under the mirrored map"},
    {"row": "cervical_fusion_gap_reclassified",
     "needs": "an episode-level flag naming the episodes whose only cervical fusion evidence is "
              "a candidate code outside the locked set, which the concept-set gap measurement "
              "of the pre-gate produces at the PERSON level and no derived table carries",
     "supply": "the set of surrogate episode indices to reclassify as cervical fusion"},
    {"row": "truncated_assigned_max_debt",
     "needs": "the episodes removed at rung 15 for a window truncated by death or reoperation. "
              "They are not in the features table by construction, so the row cannot be "
              "assembled from the analytic cohort alone",
     "supply": "the count of truncated episodes and their procedure group"},
    {"row": "fusion_status_non_add_on_only",
     "needs": "a boolean on the episode saying whether fusion status survives when add-on and "
              "instrumentation codes are excluded from the reading. The features table carries "
              "the fusion flag under the plan's own rule and not under the reading it declines",
     "supply": "a boolean column named fusion non add on on the episode frame"},
))


# ======================================================================================
# (17) Assembling the export blocks, AS RAW TRUE VALUES.
#
#      ROUND AND FLOOR-TEST AT THE BOUNDARY, NEVER BEFORE.  `07_export.py` is the boundary and
#      it asks `disclosable(n)` of a TRUE count before it calls `round20`, which is the only
#      order in which the floor means anything; it can only do that if a true count is what it
#      receives.  A block handed over already rounded makes its floor test ask a question about
#      a number that has already been changed, registers nothing in `results.json.suppressed`,
#      and turns a true 21 into a disclosed 20 the floor was never consulted about.
#
#      So the counts here are the true integers, the estimates are `(est, lo, hi)` triples, the
#      P values are bare floats, and the tipping points are bare grid coordinates.  Nothing
#      below rounds and nothing below suppresses.  The two rendering surfaces are elsewhere and
#      both of them do: `render_report` in section 19, and the exporter.
#
#      `06_analysis_gate.py` HANDS THE EXPORTER A RENDERED BLOCK AND IS RIGHT TO, which is not
#      a contradiction of this and is written down so it does not read as one.  Its block is
#      tier-shaped: a key absent because the feasibility tier forbids the analysis is a
#      different thing from a key hidden for cell size, only 06 knows the tier logic, and
#      `_adopt_rendered_gate` exists at the far end to take that block as it stands.  The debt
#      block is straightforwardly numeric, with no tier anywhere in it, so it has no such
#      justification and takes no such exemption.
# ======================================================================================

ESTIMAND_DISPLAY = (
    "Digital recovery debt is the cumulative daily shortfall against each participant's own "
    "preoperative step baseline, accrued over post-discharge days 1 to 35 and measured in "
    "baseline-equivalent activity days lost, where one activity day lost is the ambulation that "
    "participant would normally complete in a day."
)
# Named rather than typed at each surface, because the one thing this estimator must never be
# described as is a sum of the observed days.
ESTIMATOR_DISPLAY = "model and integrate"
# THE CAP IS PART OF THE QUANTITY AND THEREFORE PART OF ITS NAME.  The column is `1 - D`, one
# less the modelled TRUNCATED daily deficit, so a day above baseline scores an activity of one
# and not of one point four.  "Mean normalized activity" with no cap named is a different
# quantity, and it is the one a reader assumes: an exhibit that prints the label without this
# sentence is claiming a mean of steps over baseline that this model cannot produce.
NORMALIZED_ACTIVITY_DISPLAY = (
    "Adjusted mean normalized activity is CAPPED at baseline. It is the mean, over the window's "
    "person-days, of the smaller of one and the ratio of steps to that participant's own "
    "preoperative baseline, which is one less the modelled daily deficit. A day above baseline "
    "counts as one and never as more, so the column understates a participant who exceeded "
    "their own baseline and is not a mean of the raw ratio."
)
DELTA_DEFINITION_DISPLAY = (
    "On days that were not observed the fitted daily deficit is shifted by delta on the model's "
    "own latent logit scale, in log odds, and the reported tipping point applies the shift to "
    "the decompression group alone, which is the direction that works against the study "
    "hypothesis."
)
NO_CROSSING_DISPLAY = (
    "No tipping point within the prespecified range, which extends to delta = 4.0."
)
# EXPORT-CONTRACT 3.5, the unadjusted contrast of STROBE item 16(a).  The sentence says exactly
# what was removed and exactly what was not, because "unadjusted" is a word a reader will
# otherwise fill in from habit, and the habitual meaning here would be wrong twice over: it is
# not the naive sum over complete windows, which is a different estimator and already prints as
# the unadjusted column of Table 2, and it is not a model stripped of the day curve or the
# groups, which would not be the same estimand at all.
UNADJUSTED_CONTRAST_DISPLAY = (
    "The unadjusted contrast is the same model-and-integrate estimator refitted with the locked "
    "covariate set removed: age, sex assigned at birth, body mass index, comorbidity burden, "
    "length of stay, index year, the COVID-19 era indicator and device family are all absent "
    "from its mean structure. Everything the estimand is defined on is kept and is not an "
    "adjustment: the post-discharge-day spline, the procedure groups and their day curves, the "
    "region terms the collapse level admits, and day of week. The observation weights are the "
    "primary analysis's own and are not refitted, so the one difference between the two "
    "contrasts is the covariate block and the reader may read the gap between them as what the "
    "covariates moved."
)
# Read beside the definition and never instead of it.  A quantity a reporting guideline requires
# and a locked plan did not name is not a worse quantity, but a Methods section that cannot tell
# the two apart is a worse Methods section, so the distinction travels with the number.
UNADJUSTED_MANDATE_DISPLAY = (
    "This contrast is required by STROBE item 16(a), which asks for unadjusted estimates beside "
    "confounder-adjusted ones. It is not prespecified: the locked analysis plan carries an "
    "unadjusted association for the other arm at its section 4.8 and an unadjusted absolute "
    "level for this one at its section 9.2, and neither is an unadjusted contrast. It is "
    "reported as guideline-mandated and never as prespecified."
)


def _interval_from(boot: Mapping[str, Any], key: str) -> tuple[float, float]:
    """One percentile interval, guarded against the resamples that never arrived."""
    return percentile_interval(boot["draws"].get(key, []), attempted=boot["attempted"])


def _triple(est: Any, interval: tuple[float, float]) -> tuple[float, float, float]:
    """One `(est, lo, hi)` triple, which is the shape the export contract reads an estimate as.

    NON-FINITE MEMBERS PASS THROUGH RATHER THAN BEING REPAIRED.  A NaN here means the estimate
    or its interval was not computed, and both renderers that meet it, `render_report` below and
    `07_export.py` at the boundary, suppress on exactly that.  Substituting a number would hide
    the one thing the triple is carrying.
    """
    lo, hi = interval
    return float(est), float(lo), float(hi)


def _all_finite(triple: Any) -> bool:
    return triple is not None and all(np.isfinite(float(v)) for v in triple)


def assemble_debt(primary: VariantData, *, point: Mapping[str, Any], boot: Mapping[str, Any],
                  bounds: Mapping[str, Any], totals: np.ndarray, complete: np.ndarray,
                  observed_days: np.ndarray, draws: int,
                  monte_carlo: Mapping[str, Any]) -> dict[str, Any]:
    """The whole of Table 2 and Figure 3 block 1, as RAW TRUE VALUES.

    NOTHING HERE IS ROUNDED AND NOTHING HERE IS FLOOR-TESTED.  A count leaves as the true
    integer it came back as, an estimate leaves as an `(est, lo, hi)` triple and a P value
    leaves as a bare float, because `07_export.py` is the boundary and it can only ask
    `disclosable` of a true count before it calls `round20` if a true count is what it was
    given.  Every count key is named for what it holds -- `true_n`, `true_complete_windows`,
    `zero_debt_true_n`, `true_n_compared` -- so a value that has been through the floor can
    never be mistaken for one that has not.

    The block is an in-perimeter intermediate.  It is not printed and it is not written; the
    two surfaces a human sees are built by `render_report`, which puts every one of these
    values back through this module's node grammar, and by the exporter, which does the same on
    the way to `results.json` and records each suppression in `results.json.suppressed`.
    """
    spec = primary.spec
    # THE RECOVERY ROW'S OWN DENOMINATOR.  It is a complete-case logistic on the episodes with
    # an observed day in the recovery band, so the count beside it is that subset's and never
    # the group's, exactly as the naive column's `true_complete_windows` is its own and never
    # the analytic cohort's.  Absent it, Table 2 printed an adjusted share standing under a
    # denominator no part of it was computed from.
    recovery_n = dict(point.get("recovery", {}).get("n with outcome by group", {}))
    by_group: list[dict[str, Any]] = []
    for slug in report_groups(spec):
        members = _group_membership(primary, slug)
        n_group = int(members.sum())
        n_complete = int((members & complete).sum())
        zero_debt = int((members & (observed_days > 0) & (totals <= FLOAT_TOLERANCE)).sum())
        by_group.append({
            "slug": slug,
            "display_label": GROUP_LABELS[slug],
            "true_n": n_group,
            # Its OWN denominator, and never the group's.  The unadjusted column is a direct
            # sum over complete windows, so a median over 40 of them printed under a header
            # saying 120 would be a mislabelled number that nothing about the median reveals.
            "true_complete_windows": n_complete,
            "unadjusted_debt": quantile_triple(totals[members & complete]),
            "adjusted_debt": _triple(point["by group"][slug],
                                     _interval_from(boot, f"group:{slug}")),
            "thousand_steps_lost": _triple(
                point["absolute by group"].get(slug, float("nan")),
                _interval_from(boot, f"absolute group:{slug}")),
            "adjusted_mean_normalized_activity": _triple(
                point["normalized activity"][slug],
                _interval_from(boot, f"activity:{slug}")),
            # A FITTED PROBABILITY WITH NO NUMERATOR, which is why it is a triple beside a
            # count and not a share of one.  The count next to it, `zero_debt_true_n`, IS an
            # observed numerator over the group, and the two sit in the same row of Table 2 and
            # are different shapes on purpose.
            "share_reaching_80pct_baseline": _triple(
                point["share reaching"][slug], _interval_from(boot, f"reaching:{slug}")),
            # Its own denominator and never the group's: an episode with no observed day in
            # post-discharge days 29 to 35 has no outcome at all, which is a denominator and
            # not a zero, and the fit never saw it.
            "recovery_outcome_true_n": int(recovery_n.get(slug, 0)),
            "zero_debt_true_n": zero_debt,
        })

    fusion_mask = primary.episodes["fusion"].to_numpy().astype(bool)
    n_compared = int(fusion_mask.size)
    contrasts: dict[str, Any] = {}
    absolute: dict[str, Any] = {}
    for slug in CONTRAST_SLUGS:
        if slug not in point["contrasts"]:
            continue
        estimate = _triple(point["contrasts"][slug], _interval_from(boot, f"contrast:{slug}"))
        contrasts[slug] = {
            "display_label": CONTRAST_LABELS[slug],
            "estimate": estimate,
            "p": bootstrap_pvalue(boot["draws"].get(f"contrast:{slug}", [])),
            "is_primary": slug == PRIMARY_CONTRAST_SLUG,
            "true_n_compared": n_compared,
            # `render_forest_rows` reads `true_n` and `estimable` off this same object when it
            # builds Figure 3 block 1, so both travel with it rather than being re-derived at
            # the far end from a triple that may be full of NaNs.
            "true_n": n_compared,
            "estimable": _all_finite(estimate),
        }
        if slug in point["absolute contrasts"]:
            abs_estimate = _triple(point["absolute contrasts"][slug],
                                   _interval_from(boot, f"absolute contrast:{slug}"))
            absolute[slug] = {
                "display_label": CONTRAST_LABELS[slug],
                "estimate": abs_estimate,
                "p": bootstrap_pvalue(boot["draws"].get(f"absolute contrast:{slug}", [])),
                "is_primary": slug == PRIMARY_CONTRAST_SLUG,
                "true_n_compared": n_compared,
                "true_n": n_compared,
                "estimable": _all_finite(abs_estimate),
            }

    # STROBE 16(a).  The same shape as `contrasts`, keyed identically, so a consumer that can
    # print one can print the other with no second reader; the two are separate objects and not
    # a second triple inside one object, because the exporter renders a node per key path and
    # `debt.unadjusted_contrasts.<slug>.estimate` has to be a path it can name in the
    # suppression log on its own.
    unadjusted: dict[str, Any] = {}
    for slug in CONTRAST_SLUGS:
        if slug not in point.get("unadjusted contrasts", {}):
            continue
        plain = _triple(point["unadjusted contrasts"][slug],
                        _interval_from(boot, f"unadjusted contrast:{slug}"))
        unadjusted[slug] = {
            "display_label": CONTRAST_LABELS[slug],
            "estimate": plain,
            "p": bootstrap_pvalue(boot["draws"].get(f"unadjusted contrast:{slug}", [])),
            "is_primary": slug == PRIMARY_CONTRAST_SLUG,
            "true_n_compared": n_compared,
            "true_n": n_compared,
            "estimable": _all_finite(plain),
        }

    return {
        "estimand_display": ESTIMAND_DISPLAY,
        # The cap, named where the quantity is built, so the label at the far end can carry it.
        "normalized_activity_display": NORMALIZED_ACTIVITY_DISPLAY,
        "max_possible": WINDOW_LENGTH_DAYS,
        "by_group": by_group,
        "contrasts": contrasts,
        "unadjusted_contrasts": unadjusted,
        "unadjusted_model": _assemble_unadjusted_model(point, boot),
        "absolute_scale": absolute,
        "manski": _assemble_manski(primary, bounds),
        "delta_shift": _assemble_delta_shift(point, boot, n_compared),
        "model_fit": _assemble_model_fit(point, boot, draws=draws, monte_carlo=monte_carlo),
    }


def _assemble_unadjusted_model(point: Mapping[str, Any], boot: Mapping[str, Any],
                               ) -> dict[str, Any]:
    """What the unadjusted fit was, which rung it reached, and how many resamples it lost.

    THE RUNG IS REPORTED AND NEVER FORCED.  A covariate-free design is a different optimization
    problem: it can converge where the adjusted one did not, and it can fail where the adjusted
    one held.  Either way the two contrasts then come from two different rungs of the plan's own
    family ladder, which changes what a reader may conclude from the gap between them, so the
    fact travels with the numbers instead of being smoothed away by making the unadjusted fit
    start where the adjusted one stopped.

    A FAILED UNADJUSTED FIT IS NOT-ESTIMABLE WITH A NAMED REASON, exactly as a failed adjusted
    one is.  The reason is carried here rather than inferred at the far end from a triple full
    of NaNs, because "the fit did not converge" and "the interval stood on too few resamples"
    are two different things and only this function can still tell them apart.
    """
    ladder = point.get("unadjusted ladder")
    adjusted_rung = int(point["ladder"]["rung index"])
    attempted = int(boot.get("attempted", 0))
    failed = int(boot.get("unadjusted failed", 0))
    block: dict[str, Any] = {
        "definition_display": UNADJUSTED_CONTRAST_DISPLAY,
        "mandate_display": UNADJUSTED_MANDATE_DISPLAY,
        # Declared, never inferred.  A Methods section has to say which of the two this is, and
        # a boolean beside the number is the only form of that statement a consumer cannot
        # lose in transcription.
        "prespecified": False,
        "true_bootstrap_attempted": attempted,
        "true_bootstrap_failed": failed,
        "instability_trigger": bool(boot.get("unadjusted instability trigger", False)),
    }
    if ladder is None:
        block.update({
            "rung_slug": None,
            "rung_display": None,
            "rung_index": None,
            "rung_matches_adjusted": None,
            "rung_note_display": (
                "The unadjusted fit did not return an estimate, so the contrast beside the "
                "adjusted one is not estimable and the reason is printed in its place."),
            "not_estimable_reason": "not_estimable_convergence",
        })
        return block
    index = int(ladder["rung index"])
    matches = index == adjusted_rung
    block.update({
        "rung_slug": str(ladder["rung slug"]),
        "rung_display": str(ladder["rung display"]),
        "rung_index": index,
        "rung_matches_adjusted": bool(matches),
        "rung_note_display": (
            "The unadjusted fit reached the same rung of the model family ladder as the "
            "adjusted fit, so the two contrasts differ in the covariate set and in nothing "
            "else."
            if matches else
            "The unadjusted fit reached a different rung of the model family ladder from the "
            "adjusted fit, so the gap between the two contrasts carries a change of model "
            "family as well as the covariate set, and is read accordingly."),
        "not_estimable_reason": None,
    })
    return block


def _assemble_manski(primary: VariantData, bounds: Mapping[str, Any]) -> dict[str, Any]:
    """The assumption-free bounds, as raw pairs.

    A BOUND IS NOT AN INTERVAL, and the distinction is kept at the far end, where `bound_node`
    gives it an empty `display_ci` so that no renderer can print it as a confidence interval.
    What crosses this boundary is the pair of numbers and nothing else: `by_group` maps each
    group slug to `(lower, upper)`, and the primary contrast's pair is `primary_lower` and
    `primary_upper`, which are the names the exporter reads.
    """
    by_group = {slug: (float(values["lower"]), float(values["upper"]))
                for slug, values in bounds["by group"].items()}
    out: dict[str, Any] = {
        "by_group": by_group,
        # A statement about how they were computed, not a number.  The exporter asserts the
        # same string independently, and the two exist so they can be compared: bounds computed
        # on the complete windows only would answer a different and much more reassuring
        # question than the one the bounds are for.
        "computed_on": str(bounds["computed on"]),
    }
    if "contrast" not in bounds:
        out.update({"primary_lower": float("nan"), "primary_upper": float("nan"),
                    "true_n_compared": None, "crosses_zero": False})
        return out
    contrast = bounds["contrast"]
    out.update({
        "primary_lower": float(contrast["lower"]),
        "primary_upper": float(contrast["upper"]),
        # The count behind the bounds, carried so the report can floor-test them.  The exporter
        # derives `crosses_zero` for itself from the pair; this copy is what the diagnostics
        # and the report read, and a disagreement between them is worth being able to see.
        "true_n_compared": int(contrast["n fusion"]) + int(contrast["n decompression"]),
        "crosses_zero": bool(contrast["crosses zero"]),
    })
    return out


def _assemble_delta_shift(point: Mapping[str, Any], boot: Mapping[str, Any],
                          n_compared: int) -> dict[str, Any]:
    """The tipping point, and the curve behind it.

    THE SINGLE BEST PREEMPTION OF "YOUR MISSINGNESS IS INFORMATIVE", because it converts an
    unanswerable complaint into a reported number: how bad informative non-wear would have to
    get before the primary contrast crosses zero.  The grid is computed to the prespecified
    extension in one pass so that no second bootstrap is needed, and the EXPORTED grid is
    truncated to the base grid unless the crossing actually needed the extension.

    A TIPPING POINT IS A GRID COORDINATE AND NOT AN ESTIMATE WITH AN INTERVAL.  It is the
    smallest `delta` in the grid at which a stated condition first holds, so it takes one of
    the prespecified grid values and nothing between them and nothing around them, and it
    crosses as ONE BARE NUMBER, which the exporter turns into a bound node.  A triple here
    would give it a `lo` and a `hi` that a renderer would draw as a confidence band.

    When the curve never crosses within the prespecified range there is no such coordinate at
    all and the key is `None`.  That is the STRONGER result rather than a missing one: no
    amount of unmeasured-day pessimism inside the range overturns the finding.
    `crossed_within_grid` says so beside it, `interval_crossed_within_grid` says the same of
    the second coordinate, which can fail to cross when the first one crossed, and
    `no_crossing_display` carries the prespecified sentence.
    """
    values = point["delta"]
    if not values:
        # NO CURVE AT ALL, which is not the same as a curve that did not cross.  A collapse
        # level with no fusion contrast has nothing to shift, so the grid was never walked and
        # `no_crossing_within_range` would be the wrong sentence: it says the analysis was done
        # and returned no crossing.  `grid_computed` is what the two callers below read to tell
        # the one case from the other.
        return {
            "scale": "latent logit",
            "applied_to": DELTA_REPORTED_APPLICATION,
            "tipping_point_point_estimate": None,
            "tipping_point_interval": None,
            "definition_display": DELTA_DEFINITION_DISPLAY,
            "grid": [],
            "applications": list(DELTA_APPLICATIONS),
            "reference_deficit": DELTA_REFERENCE_DEFICIT,
            "true_n_compared": n_compared,
            "grid_extended": False,
            "grid_computed": False,
            "interval_crossed_within_grid": False,
            "crossed_within_grid": False,
            "no_crossing_display": None,
            "monotone": False,
            "already_at_or_below_zero": False,
        }
    full = delta_grid(extended=True)
    base = delta_grid(extended=False)
    reported = [float(v) for v in full
                if (float(v), DELTA_REPORTED_APPLICATION) in values]
    curve = [float(values[(d, DELTA_REPORTED_APPLICATION)]) for d in reported]
    crossing = first_crossing(reported, curve)
    lows: list[float] = []
    highs: list[float] = []
    for d in reported:
        low, high = percentile_interval(
            boot["delta draws"].get((d, DELTA_REPORTED_APPLICATION), []),
            attempted=boot["attempted"])
        lows.append(low)
        highs.append(high)
    interval_crossing = first_interval_crossing(reported, lows, highs)
    needed = [c for c in (crossing.get("delta"), interval_crossing.get("delta"))
              if c is not None]
    extended = bool(needed and max(needed) > base[-1] + FLOAT_TOLERANCE)
    shown = full if extended else base
    grid_rows = []
    for d in shown:
        for application in DELTA_APPLICATIONS:
            key = (float(d), application)
            if key not in values:
                continue
            low, high = percentile_interval(boot["delta draws"].get(key, []),
                                            attempted=boot["attempted"])
            grid_rows.append({
                "delta": float(d),
                "applied_to": application,
                "contrast_est": round(float(values[key]), UNIT_DECIMALS["activity_days"]),
                "contrast_lo": (round(low, UNIT_DECIMALS["activity_days"])
                                if np.isfinite(low) else None),
                "contrast_hi": (round(high, UNIT_DECIMALS["activity_days"])
                                if np.isfinite(high) else None),
                "implied_deficit_at_reference": round(
                    implied_deficit_at_reference(float(d)),
                    UNIT_DECIMALS["normalized_activity"]),
            })
    crossed_at = float(crossing["delta"]) if crossing["crossed"] else None
    interval_at = float(interval_crossing["delta"]) if interval_crossing["crossed"] else None
    return {
        "scale": "latent logit",
        "applied_to": DELTA_REPORTED_APPLICATION,
        "tipping_point_point_estimate": crossed_at,
        "tipping_point_interval": interval_at,
        "definition_display": DELTA_DEFINITION_DISPLAY,
        "grid": grid_rows,
        "applications": list(DELTA_APPLICATIONS),
        "reference_deficit": DELTA_REFERENCE_DEFICIT,
        "true_n_compared": n_compared,
        "grid_extended": extended,
        "grid_computed": True,
        # THE TWO COORDINATES CROSS SEPARATELY.  The point estimate can cross while the
        # interval never does, so one flag cannot answer for both, and a renderer that read
        # only `crossed_within_grid` would go looking for a number the second key does not
        # have.
        "interval_crossed_within_grid": bool(interval_crossing["crossed"]),
        "crossed_within_grid": bool(crossing["crossed"]),
        "no_crossing_display": None if crossing["crossed"] else NO_CROSSING_DISPLAY,
        "monotone": bool(crossing["monotone"]),
        "already_at_or_below_zero": bool(crossing.get("already at or below zero", False)),
    }


def _assemble_model_fit(point: Mapping[str, Any], boot: Mapping[str, Any], *, draws: int,
                        monte_carlo: Mapping[str, Any]) -> dict[str, Any]:
    """The fit statistics, as raw values.  The two counts are the true ones and say so."""
    fit = point["model fit"]
    persons = int(fit["n persons"])
    residual = next((r["display"] for r in RESIDUAL_STRUCTURE_RUNGS
                     if r["slug"] == fit["residual structure"]), fit["residual structure"])

    def triple(key: str) -> tuple[float, float, float]:
        return _triple(fit[key], _interval_from(boot, f"fit:{key}"))

    return {
        "family": fit["family"],
        "link": fit["link"],
        "spline_basis": "restricted cubic on post-discharge day",
        "spline_df": int(fit["spline df"]),
        # THE STRUCTURE THE FIT ACTUALLY USED, which is the rung it reached and not the rung
        # it started at.  The residual descent of ANALYSIS-PLAN 3.4 is data-dependent, so a
        # bundle that named the structure the fit STARTED at would be a Methods claim nobody
        # made.  The slug is the canonical form and the exporter validates it against its own
        # copy of the 3.4 vocabulary; the display travels beside it for this module's report.
        "residual_structure": str(fit["residual structure"]),
        "residual_correlation": residual,
        "rho": triple("rho"),
        "icc": triple("icc"),
        "marginal_r2": triple("marginal r2"),
        "conditional_r2": triple("conditional r2"),
        "aic": float(fit["aic"]),
        "true_n_person_days": int(fit["n person days"]),
        "true_n_persons": persons,
        "converged": bool(fit["converged"]),
        "monte_carlo_draws": int(monte_carlo.get("draws", draws)),
    }


# ======================================================================================
# (18) The ladder: fourteen plotted rows in the plan's fixed order, then ten supplementary rows.
#
#      The order is fixed in the plan so that it cannot be rearranged later to put a reassuring
#      row at the top, and the two sets are returned SEPARATELY because `local/verify.py`
#      asserts set equality over the fourteen and nothing else.  A supplementary slug appearing
#      among the fourteen is a failure, and so is a plotted slug missing from them.
# ======================================================================================


def _direct_regression_row(row: Mapping[str, Any], primary: VariantData, totals: np.ndarray,
                           complete: np.ndarray, *, resamples: int,
                           primary_estimate: float) -> dict[str, Any]:
    """Row 3, the naive estimator shown rather than hidden.

    It has its OWN denominator, the complete windows, and it is labelled the naive estimator
    wherever it prints.  It reveals how far model-and-integrate moved the answer and in which
    direction, which is the only reason it is on the ladder at all.
    """
    n_complete = int(complete.sum())
    if n_complete == 0 or not primary.spec.has_fusion:
        return not_estimable_row(row, "not_estimable_cell_size", true_n=n_complete)
    subset = _restrict_units(primary, complete, slug=row["slug"],
                             note="fitted on the complete windows only")
    subset_totals = np.asarray(totals, dtype=float)[complete]
    estimate = direct_regression_on(subset, subset_totals)
    index = rows_by_unit(subset)
    values: list[float] = []
    failures = 0
    for b in range(int(resamples)):
        rng = np.random.default_rng([SEED, b])
        drawn = rng.integers(0, subset.n_units, size=subset.n_units)
        try:
            resampled = resample_variant(subset, drawn, index)
            value = direct_regression_on(resampled, subset_totals[drawn])
        except BOOTSTRAP_FAILURES:
            failures += 1
            continue
        if np.isfinite(value):
            values.append(float(value))
        else:
            failures += 1
    lo, hi = percentile_interval(values, attempted=int(resamples))
    matches = bool(np.isfinite(primary_estimate) and np.isfinite(estimate)
                   and (estimate >= 0) == (primary_estimate >= 0))
    triple = _triple(estimate, (lo, hi))
    return {
        "order": int(row["order"]), "sub_order": int(row["sub"]),
        "display_label": row["display"],
        "estimate": triple,
        "p": bootstrap_pvalue(values),
        # ITS OWN DENOMINATOR, the complete windows, and never the analytic one.
        "true_n": n_complete,
        "estimable": _all_finite(triple),
        "not_estimable_reason": None if _all_finite(triple) else "not_estimable_convergence",
        "axis": row["axis"], "render": row["render"], "varies": row["varies"],
        "direction_matches_primary": matches,
        "bootstrap": {"attempted": int(resamples), "failed": failures,
                      "failure rate": failures / max(1, int(resamples))},
        "fitted set note": subset.note,
        "rung index": None,
    }


def _delta_shift_row(row: Mapping[str, Any], debt: Mapping[str, Any]) -> dict[str, Any]:
    """Row 5 renders as its own small panel, not as a marker.

    A tipping curve is not a point estimate with an interval, and it is the only row whose axis
    is not the primary one: its scale is latent log odds, not activity days.  A renderer that
    plotted it as a marker on the shared axis would assert a comparison that does not exist.
    """
    shift = debt["delta_shift"]
    crossed_at = shift["tipping_point_point_estimate"]
    # Figure 3 unpacks every forest row's estimate as a triple, so the row carries the
    # coordinate collapsed onto itself, the shape `bound_node` gives a bound at the far end.
    # `debt.delta_shift` carries the same number as one bare float, because there it is read
    # as a coordinate and not as a row of a forest plot.
    triple = None if crossed_at is None else (float(crossed_at),) * 3
    # A collapse level with no fusion contrast has no comparison to shift, so the count of
    # episodes compared is zero rather than missing.  Read defensively because that level
    # reaches this row through the no-crossing branch, where there is no contrast to read.
    n_compared = int(debt["contrasts"].get(PRIMARY_CONTRAST_SLUG, {}).get("true_n_compared", 0))
    if triple is None:
        reason = ("no_crossing_within_range" if shift["grid_computed"]
                  else "not_estimable_cell_size")
        out = not_estimable_row(row, reason, render=row["render"], true_n=n_compared)
        # The axis and the unit belong to the ROW and not to the estimate: a row that did not
        # cross is still a row on the latent logit scale, and Figure 3 prints its unit whether
        # or not it has a number to put on it.
        out["axis"] = row["axis"]
        out["unit"] = "dimensionless"
        return out
    return {
        "order": int(row["order"]), "sub_order": int(row["sub"]),
        "display_label": row["display"],
        "estimate": triple,
        "p": None,
        "true_n": n_compared,
        # THE ONLY ROW NOT ON THE ACTIVITY-DAY AXIS.  Its unit travels with it, because a
        # renderer that took the default would put log odds on a scale of activity days lost.
        "unit": "dimensionless",
        "estimable": True, "not_estimable_reason": None,
        "axis": row["axis"], "render": row["render"], "varies": row["varies"],
        "direction_matches_primary": False,
        "fitted set note": "the analytic cohort, shifted on days that were not observed",
        "rung index": None,
    }


def weights_effective(point: Mapping[str, Any]) -> bool:
    """Whether the observation weights actually reached the fit that produced this estimate.

    THREE THINGS HAVE TO BE TRUE AT ONCE and only their conjunction is the answer: the caller
    asked for weights, the observation model produced usable ones, and the RUNG the ladder
    reached is one that can carry a weight at all.  `statsmodels.MixedLM` cannot, so rung 4
    fits unweighted, which is the case ANALYSIS-PLAN section 6 anticipates when it defines the
    weighting row as the weights "removed, or applied where the primary rung did not use them".
    Reading only the first two would flip that row in the wrong direction at rung 4 and report
    a comparison against the primary that the primary never made.
    """
    weights = point.get("weights", {})
    return bool(weights.get("applied") and weights.get("available")
                and point["ladder"].get("weights applied", True))


def run_plotted_rows(primary: VariantData, *, point: Mapping[str, Any], debt: Mapping[str, Any],
                     r_runner: Callable[..., Mapping[str, Any]] | None, draws: int,
                     resamples: int, rung_index: int, totals: np.ndarray,
                     complete: np.ndarray) -> dict[str, Any]:
    """The fourteen plotted rows, keyed by slug, each varying exactly one thing."""
    primary_estimate = float(point["contrasts"].get(PRIMARY_CONTRAST_SLUG, float("nan")))
    weights_applied = weights_effective(point)
    out: dict[str, Any] = {}
    for row in PLOTTED_SENSITIVITY_ROWS:
        slug = row["slug"]
        if slug == "delta_shift_tipping_point":
            out[slug] = _delta_shift_row(row, debt)
            continue
        if slug == "complete_window_direct_regression":
            out[slug] = _direct_regression_row(row, primary, totals, complete,
                                               resamples=resamples,
                                               primary_estimate=primary_estimate)
            continue
        try:
            variant = build_plotted_variant(slug, primary)
        except DrdAnalysisError:
            out[slug] = not_estimable_row(row, "not_estimable_data_unavailable")
            continue
        apply_weights = (not weights_applied) if slug == "observation_weighted" else True
        out[slug] = run_sensitivity_row(
            row, variant, resamples=resamples, point_rung_index=rung_index,
            r_runner=r_runner, draws=draws, primary_estimate=primary_estimate,
            apply_weights=apply_weights, min_rung=rung_index)
    missing = set(PLOTTED_SENSITIVITY_SLUGS) - set(out)
    if missing:
        raise DrdAnalysisError(
            f"the plotted ladder produced {len(out)} rows and the plan fixes "
            f"{len(PLOTTED_SENSITIVITY_SLUGS)}. A row was added, dropped or reordered relative "
            f"to section 6 without an amendment, which is a stop condition of this plan."
        )
    return out


def run_supplementary_rows(primary: VariantData, *, point: Mapping[str, Any],
                           r_runner: Callable[..., Mapping[str, Any]] | None, draws: int,
                           resamples: int, rung_index: int,
                           extras: Mapping[str, Any]) -> dict[str, Any]:
    """The ten supplementary rows, which are NOT members of the plotted set.

    Four of them need something the derived build does not carry; each of those is reported as
    not estimable for want of data, with the gap named in `DAG_GAPS`, and each accepts the input
    if a caller supplies it.  That is the difference between a gap that is visible and a gap
    that has been quietly filled with a second implementation of somebody else's definition.
    """
    primary_estimate = float(point["contrasts"].get(PRIMARY_CONTRAST_SLUG, float("nan")))
    out: dict[str, Any] = {}

    def row_of(slug: str) -> dict[str, Any]:
        base = next(r for r in SUPPLEMENTARY_SENSITIVITY_ROWS if r["slug"] == slug)
        return {"order": 0, "sub": 1, "slug": slug, "display": base["display"],
                "axis": "primary", "render": "marker", "varies": base["varies"]}

    def run(slug: str, variant: VariantData, **kwargs: Any) -> dict[str, Any]:
        return run_sensitivity_row(row_of(slug), variant, resamples=resamples,
                                   point_rung_index=rung_index, r_runner=r_runner, draws=draws,
                                   primary_estimate=primary_estimate, min_rung=rung_index,
                                   **kwargs)

    out["baseline_steps_adjusted"] = run(
        "baseline_steps_adjusted",
        VariantData("baseline_steps_adjusted", primary.episodes, primary.days, primary.spec,
                    note="the baseline step count added to the mean structure"),
        include_baseline_steps=True)

    out["weights_without_lagged_wear"] = run(
        "weights_without_lagged_wear",
        VariantData("weights_without_lagged_wear", primary.episodes, primary.days, primary.spec,
                    note="the observation model without the lagged wear fraction"),
        include_lag=False)

    out["baseline_weekday_weekend_split"] = _supplementary_split_baseline(
        primary, row_of("baseline_weekday_weekend_split"), resamples=resamples,
        rung_index=rung_index, r_runner=r_runner, draws=draws,
        primary_estimate=primary_estimate)

    out["bmi_multiply_imputed"] = _supplementary_imputed(
        primary, row_of("bmi_multiply_imputed"), resamples=resamples, rung_index=rung_index,
        r_runner=r_runner, draws=draws, primary_estimate=primary_estimate)

    if primary.spec.level == "four_group":
        out["four_group_model"] = run(
            "four_group_model",
            VariantData("four_group_model", primary.episodes, primary.days, primary.spec,
                        note="the four-group specification, which is the primary at this "
                             "collapse level"))
    else:
        out["four_group_model"] = not_estimable_row(row_of("four_group_model"),
                                                    "not_estimable_cell_size")

    out["cervical_decompression_gap_stated"] = not_estimable_row(
        row_of("cervical_decompression_gap_stated"), "not_estimable_data_unavailable",
        render="text")

    for slug, key in (("junctions_mirrored", "mirrored panel"),
                      ("cervical_fusion_gap_reclassified", "reclassified units"),
                      ("truncated_assigned_max_debt", "truncated episodes"),
                      ("fusion_status_non_add_on_only", "fusion non add on")):
        supplied = extras.get(key)
        if supplied is None:
            out[slug] = not_estimable_row(row_of(slug), "not_estimable_data_unavailable")
            continue
        try:
            variant = _supplied_variant(slug, primary, supplied)
        except DrdAnalysisError:
            out[slug] = not_estimable_row(row_of(slug), "not_estimable_data_unavailable")
            continue
        out[slug] = run(slug, variant)

    missing = set(SUPPLEMENTARY_SENSITIVITY_SLUGS) - set(out)
    if missing:
        raise DrdAnalysisError(
            f"the supplementary ladder is missing {sorted(missing)}. The plan fixes ten "
            f"supplementary rows and a row may not be dropped without an amendment."
        )
    return out


def _supplied_variant(slug: str, primary: VariantData, supplied: Any) -> VariantData:
    """Build one of the four supplementary rows the derived build does not support on its own,
    from what a caller supplied.  The shape each one needs is named in `DAG_GAPS`."""
    if slug == "fusion_status_non_add_on_only":
        flag = np.asarray(supplied, dtype=bool)
        if flag.size != primary.n_units:
            raise DrdAnalysisError("the supplied fusion reading does not cover every episode")
        episodes = primary.episodes.copy()
        episodes["fusion"] = flag
        episodes["procedure_class"] = np.where(flag, "fusion", "decompression")
        return VariantData(slug, episodes, primary.days, primary.spec,
                           note="fusion status read from records that can define an operation")
    if slug == "cervical_fusion_gap_reclassified":
        positions = np.asarray(list(supplied), dtype=int)
        episodes = primary.episodes.copy()
        fusion = episodes["fusion"].to_numpy().astype(bool)
        fusion[positions] = True
        episodes["fusion"] = fusion
        return VariantData(slug, episodes, primary.days, primary.spec,
                           note="the misfiled anterior cervical fusions moved to fusion")
    if slug == "junctions_mirrored":
        if not isinstance(supplied, VariantData):
            raise DrdAnalysisError("the mirrored row needs a prepared variant of its own")
        return supplied
    if slug == "truncated_assigned_max_debt":
        if not isinstance(supplied, VariantData):
            raise DrdAnalysisError("the truncated row needs a prepared variant of its own")
        return supplied
    raise DrdAnalysisError(f"{slug!r} is not a supplied row this module knows how to build")


def _supplementary_split_baseline(primary: VariantData, row: Mapping[str, Any], *,
                                  resamples: int, rung_index: int,
                                  r_runner: Callable[..., Mapping[str, Any]] | None,
                                  draws: int, primary_estimate: float) -> dict[str, Any]:
    try:
        variant = _split_baseline_variant(primary)
    except DrdAnalysisError:
        return not_estimable_row(row, "not_estimable_data_unavailable",
                                 true_n=int(primary.n_units))
    out = run_sensitivity_row(row, variant, resamples=resamples, point_rung_index=rung_index,
                              r_runner=r_runner, draws=draws, primary_estimate=primary_estimate,
                              min_rung=rung_index)
    out["n excluded"] = int(primary.n_units - variant.n_units)
    return out


def _supplementary_imputed(primary: VariantData, row: Mapping[str, Any], *, resamples: int,
                           rung_index: int, r_runner: Callable[..., Mapping[str, Any]] | None,
                           draws: int, primary_estimate: float) -> dict[str, Any]:
    """Twenty imputations of the missing body mass index, with the master seed.

    HOW THE IMPUTATIONS ARE COMBINED, stated because the plan names the number of imputations
    and not the combination rule.  The point estimate is the average contrast across the twenty
    imputed frames, which is Rubin's first rule unchanged.  The interval comes from the
    clustered bootstrap with resample `b` using imputation `b` modulo twenty, which propagates
    the imputation uncertainty and the sampling uncertainty together.  Rubin's variance rule is
    not used because the within-imputation variance of this estimator is itself only available
    from a bootstrap, and twenty of those is twenty times the primary's cost for a supplementary
    row.
    """
    rng = np.random.default_rng(SEED)
    frames = [impute_body_mass_index(primary.episodes, rng) for _ in range(IMPUTATIONS)]
    variants = [VariantData(row["slug"], frame, primary.days, primary.spec,
                            note="body mass index multiply imputed") for frame in frames]
    estimates: list[float] = []
    for variant in variants:
        try:
            out = estimate_variant(variant, r_runner=r_runner, draws=draws, seed_spec=SEED,
                                   min_rung=rung_index, min_rung_trigger=None)
        except BOOTSTRAP_FAILURES:
            continue
        value = out["contrasts"].get(PRIMARY_CONTRAST_SLUG)
        if value is not None and np.isfinite(value):
            estimates.append(float(value))
    if not estimates:
        return not_estimable_row(row, "not_estimable_convergence", true_n=int(primary.n_units))
    point_estimate = float(np.mean(estimates))
    index = rows_by_unit(primary)
    values: list[float] = []
    failures = 0
    for b in range(int(resamples)):
        boot_rng = np.random.default_rng([SEED, b])
        drawn = boot_rng.integers(0, primary.n_units, size=primary.n_units)
        variant = variants[b % IMPUTATIONS]
        try:
            resampled = resample_variant(variant, drawn, index)
            out = estimate_variant(resampled, r_runner=r_runner, draws=draws,
                                   seed_spec=[SEED, b], min_rung=rung_index,
                                   min_rung_trigger=None)
        except BOOTSTRAP_FAILURES:
            failures += 1
            continue
        value = out["contrasts"].get(PRIMARY_CONTRAST_SLUG)
        if value is None or not np.isfinite(value):
            failures += 1
            continue
        values.append(float(value))
    lo, hi = percentile_interval(values, attempted=int(resamples))
    matches = bool(np.isfinite(primary_estimate)
                   and (point_estimate >= 0) == (primary_estimate >= 0))
    triple = _triple(point_estimate, (lo, hi))
    return {
        "order": 0, "sub_order": 1, "display_label": row["display"],
        "estimate": triple,
        "p": bootstrap_pvalue(values),
        "true_n": int(primary.n_units),
        "estimable": _all_finite(triple),
        "not_estimable_reason": None if _all_finite(triple) else "not_estimable_convergence",
        "axis": "primary", "render": "marker", "varies": row["varies"],
        "direction_matches_primary": matches,
        "imputations": IMPUTATIONS,
        "bootstrap": {"attempted": int(resamples), "failed": failures,
                      "failure rate": failures / max(1, int(resamples))},
        "fitted set note": "body mass index multiply imputed, missing indicator removed",
        "rung index": rung_index,
    }


# ======================================================================================
# (19) Rendering.
#
#      EVERY NUMBER PRINTED HERE IS A NODE'S OWN `display` STRING.  Nothing is formatted a
#      second time at the point of printing, so a number that was suppressed cannot be
#      re-rendered into visibility by a caller who forgot, and a number that was disclosed
#      prints in exactly the form the export will carry.  The house prose rules are asserted on
#      the RENDERED text before a character of it reaches the screen.
# ======================================================================================

_SNAKE_TOKEN = re.compile(r"\b[a-z0-9]+_[a-z0-9_]*\b")
_RULE = "=" * 86
_THIN = "-" * 86


def _table_lines(headers: Sequence[str], rows: Sequence[Sequence[str]],
                 align: str = "") -> list[str]:
    align = align or ("l" + "r" * (len(headers) - 1))
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    def line(cells: Sequence[str]) -> str:
        out = [str(cell).ljust(widths[i]) if align[i] == "l" else str(cell).rjust(widths[i])
               for i, cell in enumerate(cells)]
        return "  ".join(out).rstrip()

    return [line(headers), "  ".join("-" * w for w in widths)] + [line(r) for r in rows]


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _bullets(items: Sequence[str], width: int = 82) -> list[str]:
    out: list[str] = []
    for item in items:
        chunks = _wrap(item, width - 4)
        out.append("  * " + chunks[0])
        out += ["    " + chunk for chunk in chunks[1:]]
    return out


def assert_house_prose(text: str) -> None:
    """Stop conditions on the rendered report, checked before it is printed."""
    if EM_DASH in text:
        raise DrdAnalysisError("the report contains an em-dash, which no house string may carry")
    if MINUS_SIGN in text:
        raise DrdAnalysisError("the report contains a Unicode minus sign, which is banned")
    snake = sorted(set(_SNAKE_TOKEN.findall(text)))
    if snake:
        raise DrdAnalysisError(
            f"the report contains machine token(s) {snake}, and an identifier is never a "
            f"user-visible string. Print the display label beside it instead."
        )


def _report_estimate(triple: Any, unit: str, *, contributing_n: Any, bound: bool = False,
                     reason: str = "contributing_n_below_threshold") -> dict[str, Any]:
    """One raw `(est, lo, hi)` triple, put back through the node grammar for the report.

    `bound` IS DECLARED BY THE CALLER AND NEVER INFERRED FROM THE NUMBERS.  A row that carries
    a bound carries one whatever its three members happen to be, and a row that carries an
    interval keeps it even when the interval has collapsed: a bootstrap whose resamples all
    landed on the same number is a fact about the fit, and reading the collapse as "this must
    have been a bound" is exactly how that fact would stop printing.
    """
    if triple is None:
        return suppressed_node(reason)
    est, lo, hi = (float(v) for v in triple)
    if bound:
        return bound_node(est, unit, contributing_n=contributing_n)
    return estimate_node(est, lo, hi, unit, contributing_n=contributing_n, reason=reason)


def _report_fit(triple: Any, *, contributing_n: Any) -> dict[str, Any]:
    """A fit statistic, which KEEPS ITS POINT when the bootstrap could not give it an interval.

    A within-person correlation the fit reports and a bootstrap could not resample is still the
    correlation the fit used, and printing nothing there would hide the structure of the model
    rather than protect a cell.  An estimate of the debt itself is not treated this way: there
    the interval is the claim, and a point without one is suppressed.
    """
    est, lo, hi = (float(v) for v in triple)
    if not np.isfinite(est):
        return suppressed_node("not_estimable_data_unavailable")
    if not (np.isfinite(lo) and np.isfinite(hi)):
        return bound_node(est, "dimensionless", contributing_n=contributing_n)
    return estimate_node(est, lo, hi, "dimensionless", contributing_n=contributing_n)


def report_row(row: Mapping[str, Any], *, slug: str = "") -> dict[str, Any]:
    """One raw ladder row's three numeric members, as nodes, for the report."""
    reason = row.get("not_estimable_reason") or "contributing_n_below_threshold"
    true_n = row["true_n"]
    return {
        "estimate": _report_estimate(row["estimate"], row.get("unit", "activity_days"),
                                     contributing_n=true_n, reason=reason,
                                     bound=slug in BOUND_SENSITIVITY_SLUGS),
        "pvalue": (None if row.get("p") is None
                   else pvalue_node(float(row["p"]), contributing_n=true_n)),
        "n": count_node(true_n),
    }


def report_debt(debt: Mapping[str, Any]) -> dict[str, Any]:
    """The raw debt block, put back through this module's own node grammar, FOR THE REPORT.

    THE REPORT IS A DISCLOSING SURFACE AND THE RETURNED OBJECT IS NOT.  `assemble_debt` hands
    the exporter true counts because the exporter is the boundary and must floor-test them
    itself; the report is printed inside the perimeter but is read by people and pasted into
    other places, so every number in it goes through the same floor here, at the moment the
    line is built, rather than being formatted a second time at the point of printing.

    This is not a second implementation of the exporter's rendering: it is this module's own
    node grammar, unchanged, applied to the values `assemble_debt` used to build directly.  The
    two renderers agree because they ask `disclosable` of the same true counts, and they are
    separate because they answer to different contracts -- the exporter also has to write a
    suppression log, and the report has to fit in eighty-six columns.
    """
    groups = []
    for entry in debt["by_group"]:
        n_group = entry["true_n"]
        n_complete = entry["true_complete_windows"]
        groups.append({
            "slug": entry["slug"],
            "display_label": entry["display_label"],
            "n": count_node(n_group),
            "n_complete_windows": count_node(n_complete),
            "unadjusted_debt": quantile_node_from(*entry["unadjusted_debt"], "activity_days",
                                                  contributing_n=n_complete),
            "adjusted_debt": _report_estimate(entry["adjusted_debt"], "activity_days",
                                              contributing_n=n_group),
            "thousand_steps_lost": _report_estimate(entry["thousand_steps_lost"],
                                                    "thousand_steps", contributing_n=n_group),
            "adjusted_mean_normalized_activity": _report_estimate(
                entry["adjusted_mean_normalized_activity"], "normalized_activity",
                contributing_n=n_group),
            # Its own contributing count, THIS GROUP'S episodes that have the outcome, and not
            # the group's full n and not the cohort-wide subset count either: an episode with no
            # observed day in the recovery band has no outcome at all, which is a denominator
            # and not a zero, and it is a denominator that differs between groups.
            "share_reaching_80pct_baseline": _report_estimate(
                entry["share_reaching_80pct_baseline"], "percent",
                contributing_n=entry["recovery_outcome_true_n"]),
            "n_recovery_outcome": count_node(entry["recovery_outcome_true_n"]),
            "share_zero_debt": percentage_node(entry["zero_debt_true_n"], n_group),
        })

    def side(block: Mapping[str, Any], unit: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for slug, spec in block.items():
            n_compared = spec["true_n_compared"]
            out[slug] = {
                "display_label": spec["display_label"],
                "estimate": _report_estimate(spec["estimate"], unit,
                                             contributing_n=n_compared),
                "pvalue": pvalue_node(float(spec["p"]), contributing_n=n_compared),
                "is_primary": bool(spec["is_primary"]),
                "n_compared": count_node(n_compared),
            }
        return out

    manski = debt["manski"]
    group_n = {entry["slug"]: entry["true_n"] for entry in debt["by_group"]}
    manski_view: dict[str, Any] = {
        "by_group": {slug: {"lower": bound_node(low, "activity_days",
                                                contributing_n=group_n.get(slug)),
                            "upper": bound_node(high, "activity_days",
                                                contributing_n=group_n.get(slug))}
                     for slug, (low, high) in manski["by_group"].items()},
        "computed_on": manski["computed_on"],
        "crosses_zero": bool(manski["crosses_zero"]),
    }
    lower = bound_node(manski["primary_lower"], "activity_days",
                       contributing_n=manski["true_n_compared"])
    upper = bound_node(manski["primary_upper"], "activity_days",
                       contributing_n=manski["true_n_compared"])
    if node_is_suppressed(lower) or node_is_suppressed(upper):
        display = SUPPRESSION_SENTENCES["contributing_n_below_threshold"]
    else:
        display = _assert_display(
            f"Assumption-free bounds on the primary contrast, in baseline-equivalent activity "
            f"days lost: {lower['display_point']} to {upper['display_point']}, computed on "
            f"every eligible episode with no assumption about missingness.")
    manski_view.update({"primary_contrast_lower": lower, "primary_contrast_upper": upper,
                        "display": display})

    shift = debt["delta_shift"]
    shift_n = shift["true_n_compared"]

    def coordinate(value: Any) -> dict[str, Any]:
        # A grid coordinate, or the sentence for a curve that never crossed.  NOT "data not
        # available", which says the analysis could not be done: the grid was walked out to
        # the prespecified extension and the answer is that there is no crossing in it.
        if value is None:
            return suppressed_node("no_crossing_within_range" if shift["grid_computed"]
                                   else "not_estimable_cell_size")
        return bound_node(float(value), "dimensionless", contributing_n=shift_n)

    shift_view = dict(shift)
    shift_view.update({
        "tipping_point_point_estimate": coordinate(shift["tipping_point_point_estimate"]),
        "tipping_point_interval": coordinate(shift["tipping_point_interval"]),
        "reference_deficit": scalar_node(shift["reference_deficit"], "normalized_activity"),
    })

    fit = debt["model_fit"]
    persons = fit["true_n_persons"]
    fit_view = dict(fit)
    fit_view.update({
        "spline_df": scalar_node(fit["spline_df"]),
        "rho": _report_fit(fit["rho"], contributing_n=persons),
        "icc": _report_fit(fit["icc"], contributing_n=persons),
        "marginal_r2": _report_fit(fit["marginal_r2"], contributing_n=persons),
        "conditional_r2": _report_fit(fit["conditional_r2"], contributing_n=persons),
        # A quasi-likelihood rung reports no AIC at all, so this is a real absence and not a
        # suppression for cell size.
        "aic": (scalar_node(float(fit["aic"]), "information_criterion")
                if np.isfinite(fit["aic"])
                else suppressed_node("not_estimable_data_unavailable")),
        "n_person_days": count_node(fit["true_n_person_days"]),
        "n_persons": count_node(persons),
        "monte_carlo_draws": scalar_node(fit["monte_carlo_draws"]),
    })

    # The unadjusted model's own facts, put through the same grammar.  The bootstrap counts are
    # resample counts and not participant counts, so they are a percentage over a denominator
    # exactly as `estimator.bootstrap_failure_rate` is, and never an estimate.
    plain_model = dict(debt["unadjusted_model"])
    plain_model["bootstrap_failure_rate"] = percentage_node(
        plain_model["true_bootstrap_failed"], plain_model["true_bootstrap_attempted"])

    return {
        "estimand": {"display": debt["estimand_display"], "unit": "activity_days",
                     "max_possible": scalar_node(debt["max_possible"]),
                     "estimator": ESTIMATOR_DISPLAY},
        "normalized_activity_display": debt["normalized_activity_display"],
        "by_group": groups,
        "contrasts": side(debt["contrasts"], "activity_days"),
        "unadjusted_contrasts": side(debt["unadjusted_contrasts"], "activity_days"),
        "unadjusted_model": plain_model,
        "absolute_scale": side(debt["absolute_scale"], "thousand_steps"),
        "manski": manski_view,
        "delta_shift": shift_view,
        "model_fit": fit_view,
    }


def _shown(node: Any) -> str:
    """The one string from a node that may reach a rendered surface, safe for both shapes."""
    if isinstance(node, Mapping) and "display" in node:
        return str(node["display"])
    if node is None:
        return "not applicable"
    return str(node)


def render_report(result: Mapping[str, Any]) -> str:
    """The whole step as text, so it can be checked as easily as it is printed."""
    lines: list[str] = [_RULE,
                        "PHASE 4, ARM B. DIGITAL RECOVERY DEBT OVER POST-DISCHARGE DAYS 1 TO 35",
                        _RULE]
    if not result.get("drd ok"):
        lines += _bullets(list(result.get("halting", ())))
        text = "\n".join(lines)
        assert_house_prose(text)
        return text

    estimator = result["estimator"]
    diagnostics = result["diagnostics"]
    # THE REPORT RENDERS, THE RETURNED OBJECT DOES NOT.  `result["debt"]` carries true counts
    # for the exporter to floor-test; every number printed below is a node built here, from
    # those same true counts, and a suppressed one carries no numeral at all.
    debt = report_debt(result["debt"])

    lines += _wrap(debt["estimand"]["display"], 86)
    lines.append("")
    lines.append("The estimator models the daily deficit and integrates the fitted curve over "
                 "the whole")
    lines.append("window, including the days an episode did not contribute. Summing the "
                 "observed days")
    lines.append("instead would let every missing day score zero deficit, which asserts the "
                 "participant")
    lines.append("walked at or above their own baseline on a day nobody measured.")
    lines.append("")

    lines.append(_THIN)
    lines.append("THE MODEL FAMILY LADDER, AND THE RUNG REACHED")
    lines.append(_THIN)
    rung_rows = []
    for attempt in estimator["rungs_attempted"]:
        rung_rows.append([ESTIMATOR_RUNG_LABELS[attempt["slug"]], attempt["outcome"]])
    lines += _table_lines(["Rung", "Outcome"], rung_rows, align="ll")
    lines.append(f"Reached: {estimator['rung_display']}")
    lines.append(f"Residual structure: {debt['model_fit']['residual_correlation']}")
    if estimator["descent_triggers_fired"]:
        lines.append("Descent triggers, in the order they fired, each a computational property "
                     "of the fit:")
        lines += _bullets([DESCENT_TRIGGERS[code]
                           for code in estimator["descent_triggers_fired"]])
    else:
        lines.append("No descent trigger fired, so the ladder stopped at its first rung.")
    lines.append("No trigger references the direction, magnitude or significance of any "
                 "contrast.")
    lines.append("")

    lines.append(_THIN)
    lines.append("ADJUSTED DEBT BY PROCEDURE GROUP, IN BASELINE-EQUIVALENT ACTIVITY DAYS LOST")
    lines.append(_THIN)
    group_rows = []
    for entry in debt["by_group"]:
        group_rows.append([
            entry["display_label"],
            _shown(entry["n"]),
            _shown(entry["unadjusted_debt"]),
            _shown(entry["n_complete_windows"]),
            _shown(entry["adjusted_debt"]),
            _shown(entry["thousand_steps_lost"]),
        ])
    lines += _table_lines(
        ["Group", "Episodes", "Unadjusted", "Complete windows", "Adjusted", "Thousand steps"],
        group_rows)
    lines.append("The unadjusted column is the naive estimator by direct summation on complete "
                 "windows")
    lines.append("only, so it carries its own denominator and not the analytic one.")
    lines.append("")
    recovery_rows = []
    for entry in debt["by_group"]:
        recovery_rows.append([
            entry["display_label"],
            _shown(entry["adjusted_mean_normalized_activity"]),
            _shown(entry["share_reaching_80pct_baseline"]),
            _shown(entry["share_zero_debt"]),
        ])
    lines += _table_lines(
        ["Group", "Mean normalized activity", "Reached 80% of baseline", "Zero debt"],
        recovery_rows)
    lines += _wrap(debt["normalized_activity_display"], 86)
    lines += _wrap(
        "The share reaching 80% is a fitted probability with an interval and no numerator, and "
        "it is fitted on " + RECOVERY_FITTED_ON + ". Its own denominator is printed below and "
        "is not the group's. It assumes " + RECOVERY_MISSINGNESS_ASSUMPTION + ".", 86)
    recovery_denominator_rows = [[entry["display_label"], _shown(entry["n_recovery_outcome"])]
                                 for entry in debt["by_group"]]
    lines += _table_lines(["Group", "Episodes with the outcome"], recovery_denominator_rows)
    lines.append("The share with zero debt is a count over a denominator and is a percentage.")
    lines.append("")

    lines.append(_THIN)
    lines.append("CONTRASTS")
    lines.append(_THIN)
    contrast_rows = []
    for slug, entry in debt["contrasts"].items():
        absolute = debt["absolute_scale"].get(slug, {})
        contrast_rows.append([
            entry["display_label"] + (" (primary)" if entry["is_primary"] else ""),
            _shown(entry["estimate"]),
            _shown(entry["pvalue"]),
            _shown(absolute.get("estimate")) if absolute else "not applicable",
        ])
    if contrast_rows:
        lines += _table_lines(
            ["Contrast", "Activity days lost", "P value", "Thousand steps lost"], contrast_rows)
    else:
        lines.append("No between-group contrast is estimable at the collapse level reached.")
    lines.append("")

    # STROBE item 16(a) asks for the unadjusted estimate beside the adjusted one, and it asks
    # for the CONTRAST.  The unadjusted column of the group table above is a different quantity
    # and does not answer it: that is an absolute level, by direct summation on complete
    # windows, and a reader cannot difference two medians over two different denominators and
    # get this number.
    unadjusted_rows = []
    for slug, entry in debt["unadjusted_contrasts"].items():
        adjusted = debt["contrasts"].get(slug, {})
        unadjusted_rows.append([
            entry["display_label"] + (" (primary)" if entry["is_primary"] else ""),
            _shown(entry["estimate"]),
            _shown(adjusted.get("estimate")) if adjusted else "not applicable",
            _shown(entry["pvalue"]),
        ])
    plain = debt["unadjusted_model"]
    lines.append(_THIN)
    lines.append("THE SAME CONTRASTS WITH THE COVARIATE SET REMOVED")
    lines.append(_THIN)
    if unadjusted_rows:
        lines += _table_lines(
            ["Contrast", "Unadjusted", "Adjusted", "P value"], unadjusted_rows)
    elif plain["not_estimable_reason"]:
        lines.append(SUPPRESSION_SENTENCES[plain["not_estimable_reason"]])
    else:
        lines.append("No between-group contrast is estimable at the collapse level reached.")
    lines += _wrap(plain["definition_display"], 86)
    lines += _wrap(plain["mandate_display"], 86)
    if plain["rung_display"]:
        lines.append(f"Rung reached by the unadjusted fit: {plain['rung_display']}")
    lines += _wrap(plain["rung_note_display"], 86)
    lines.append(f"Resamples that returned no unadjusted contrast: "
                 f"{_shown(plain['bootstrap_failure_rate'])} of those attempted.")
    lines.append("")

    lines.append(_THIN)
    lines.append("WHAT SURVIVES WITH NO ASSUMPTION ABOUT MISSINGNESS, AND WHAT IT WOULD TAKE TO "
                 "OVERTURN")
    lines.append(_THIN)
    lines += _wrap(_shown(debt["manski"]), 86)
    lines.append("These bounds are wide by construction and are reported anyway. They will very "
                 "likely")
    lines.append("span zero. The honest structure is that the bounds say what is certain, the "
                 "tipping")
    lines.append("point says how far the model would have to be wrong, and the point estimate "
                 "says what")
    lines.append("the model implies.")
    lines.append("")
    shift = debt["delta_shift"]
    lines += _wrap(shift["definition_display"], 86)
    lines.append(f"Smallest shift at which the point estimate crosses zero: "
                 f"{_shown(shift['tipping_point_point_estimate'])}")
    lines.append(f"Smallest shift at which the interval first includes zero: "
                 f"{_shown(shift['tipping_point_interval'])}")
    if not shift["crossed_within_grid"] and shift["no_crossing_display"]:
        lines += _wrap(shift["no_crossing_display"], 86)
    if shift["grid"]:
        grid_rows = [[f"{entry['delta']:.2f}", entry["applied_to"],
                      f"{entry['contrast_est']:.1f}",
                      f"{entry['implied_deficit_at_reference']:.2f}"]
                     for entry in shift["grid"]
                     if entry["applied_to"] == DELTA_REPORTED_APPLICATION]
        lines += _table_lines(
            ["Shift, log odds", "Applied to", "Contrast", "Deficit implied at a 30% reference "
                                                          "day"], grid_rows)
    lines.append("")

    lines.append(_THIN)
    lines.append("MODEL FIT AND THE INTEGRATION")
    lines.append(_THIN)
    fit = debt["model_fit"]
    lines += _table_lines(["Quantity", "Value"], [
        ["Family", fit["family"]],
        ["Link", fit["link"]],
        ["Time basis", fit["spline_basis"]],
        ["Basis columns", _shown(fit["spline_df"])],
        ["Residual correlation", fit["residual_correlation"]],
        ["Within-person correlation", _shown(fit["rho"])],
        ["Share of variation between people", _shown(fit["icc"])],
        ["Explained variation, fixed part", _shown(fit["marginal_r2"])],
        ["Explained variation, with random effects", _shown(fit["conditional_r2"])],
        ["Akaike information criterion", _shown(fit["aic"])],
        ["Person-days fitted", _shown(fit["n_person_days"])],
        ["Participants", _shown(fit["n_persons"])],
        ["Monte Carlo draws", _shown(fit["monte_carlo_draws"])],
    ], align="ll")
    monte = diagnostics["monte carlo"]
    lines.append(f"The marginalization was rechecked on a second stream and the primary "
                 f"contrast moved {monte['movement']:.3f} activity days lost, against a "
                 f"tolerance of {MONTE_CARLO_TOLERANCE_ACTIVITY_DAYS:.2f}.")
    boot = diagnostics["bootstrap"]
    lines.append(f"Clustered bootstrap: {boot['attempted']:,} resamples of whole participants, "
                 f"{boot['failed']:,} discarded for failing to reach the rung the point "
                 f"estimate reached.")
    weights = diagnostics["weights"]
    if diagnostics.get("weights reached the fit") and not weights.get("degenerate"):
        lines.append(f"Observation weights: mean {weights['mean']:.2f}, range "
                     f"{weights['minimum']:.2f} to {weights['maximum']:.2f}, truncated at the "
                     f"1st and 99th percentiles, which moved "
                     f"{100.0 * weights['share truncated']:.0f}% of them.")
    else:
        lines.append("Observation weights were not applied at the rung reached, and the "
                     "weighting row of the ladder varies that decision in the other direction.")
    lines.append("")

    lines.append(_THIN)
    lines.append("THE PRESPECIFIED SENSITIVITY LADDER, IN THE ORDER THE PLAN FIXES")
    lines.append(_THIN)
    sensitivity = result["sensitivity"]
    rows = sorted(sensitivity.items(), key=lambda kv: (kv[1]["order"], kv[1]["sub_order"]))
    printed_rows = [(row, report_row(row, slug=slug)) for slug, row in rows]
    lines += _table_lines(["Row", "Estimate", "Episodes", "Same direction"], [
        [row["display_label"], _shown(nodes["estimate"]), _shown(nodes["n"]),
         "yes" if row["direction_matches_primary"] else "no"]
        for row, nodes in printed_rows])
    lines.append(f"Fourteen plotted rows from ten ladder rows, each carrying "
                 f"{BOOTSTRAP_SENSITIVITY:,} resamples rather than the primary's "
                 f"{BOOTSTRAP_PRIMARY:,}, because a row is read for direction and overlap "
                 f"rather than for a reported P value.")
    lines.append("The tipping-point row is its own panel and is the only row not on the "
                 "activity-day axis.")
    lines.append("")
    supplementary = result.get("supplementary", {})
    if supplementary:
        lines.append(_THIN)
        lines.append("SUPPLEMENTARY ROWS, WHICH ARE NOT PLOTTED ON THE LADDER")
        lines.append(_THIN)
        lines += _table_lines(["Row", "Estimate", "Episodes"], [
            [SENSITIVITY_LABELS[slug],
             _shown(report_row(supplementary[slug], slug=slug)["estimate"]),
             _shown(report_row(supplementary[slug], slug=slug)["n"])]
            for slug in SUPPLEMENTARY_SENSITIVITY_SLUGS if slug in supplementary])
        lines.append("")

    gaps = result.get("gaps", ())
    if gaps:
        lines.append(_THIN)
        lines.append("WHAT THE DERIVED BUILD DOES NOT CARRY")
        lines.append(_THIN)
        lines += _bullets([f"{SENSITIVITY_LABELS[gap['row']]}: {gap['needs']}" for gap in gaps])
        lines.append("None of these is worked around here. A second implementation of somebody "
                     "else's")
        lines.append("definition is a divergence waiting for the next amendment.")
        lines.append("")

    lines.append(_THIN)
    lines.append("DISCLOSURE")
    lines.append(_THIN)
    lines.append("Counts of 20 or fewer are suppressed; larger counts are rounded to the "
                 "nearest 20, so a")
    lines.append("disclosed 20 represents a true count of 21 to 29. A continuous statistic is "
                 "never")
    lines.append("rounded to 20; it is disclosable only when the count of participants behind "
                 "it clears")
    lines.append("the floor. No participant-level value is printed, returned or exported by "
                 "this step.")
    lines.append(_RULE)
    text = "\n".join(lines)
    assert_house_prose(text)
    return text


# ======================================================================================
# (20) Running it.  `q_guarded` is the only query path and there is no other; nothing in this
#      module can reach the BigQuery interface by any route that skips the printed estimate and
#      the hard byte cap.
# ======================================================================================

RESULT_KEYS: tuple[str, ...] = (
    "drd ok", "halting", "collapse", "estimator", "debt", "sensitivity", "supplementary",
    "diagnostics", "gaps", "report",
)

GUARD_SENTENCES: Mapping[str, str] = MappingProxyType({
    "n_deficit_on_unobserved_day":
        "a daily deficit is present on a day the panel calls unobserved, which is a "
        "zero-imputation by another name and destroys the estimator",
    "n_missing_deficit_on_observed_day":
        "a daily deficit is absent on a day the panel calls observed, so the analyzability flag "
        "and the deficit were computed from different step columns",
    "n_pod_window_beyond_panel":
        "a postoperative-day-anchored window day falls beyond the day bound of the panel query, "
        "so the first sensitivity row would be fitted on a truncated window",
    "n_activity_missing_on_observed_day":
        "normalized activity is absent on a day the panel calls observed, which the deficit "
        "would have to share and does not",
    "n_zero_imputed_deficit":
        "a zero deficit sits on an unobserved day, asserting that the participant walked at or "
        "above their own preoperative baseline on a day nobody measured",
    "n_nonpositive_baseline":
        "a baseline of zero or below exists in the derived build, which makes the ratio infinite "
        "and the deficit one on every day",
})


def guard_violations(frame: pd.DataFrame) -> list[str]:
    """Every guard is expected to be exactly zero, and each is a stop condition."""
    if len(frame) != 1:
        return ["the guard query returned something other than one row, so the checks it "
                "carries were not evaluated"]
    row = frame.iloc[0]
    out: list[str] = []
    for column, sentence in GUARD_SENTENCES.items():
        if column not in frame.columns:
            out.append(f"the guard query did not return the check for {column.replace('_', ' ')}")
            continue
        if int(row[column]) != 0:
            out.append(sentence)
    if int(row.get("n_units", 0)) <= 0:
        out.append("the panel carries no episode at all")
    return out


def _ipython_user_namespace() -> dict[str, Any]:
    try:
        from IPython import get_ipython           # type: ignore[import-not-found]
    except Exception:
        return {}
    try:
        shell = get_ipython()
    except Exception:
        return {}
    return dict(getattr(shell, "user_ns", {})) if shell is not None else {}


def _resolve_runtime(
    q_guarded: Callable[..., pd.DataFrame] | None,
    dry_run_gb: Callable[[str], float] | None,
) -> tuple[Callable[..., pd.DataFrame], Callable[[str], float]]:
    """Find the two configuration-notebook helpers, in the order a caller would expect.

    Explicit argument first, which is how the self-test injects a fake; then this module's own
    globals, which is what a notebook run in place populates; then the live kernel namespace.
    Nothing falls back to a raw client: a module that could quietly find its own way to the
    interface is a module that eventually runs a query with no printed estimate and no cap.
    """
    namespace: dict[str, Any] | None = None
    resolved: list[Callable[..., Any]] = []
    for name, given in (("q_guarded", q_guarded), ("dry_run_gb", dry_run_gb)):
        found = given if callable(given) else None
        if found is None:
            candidate = globals().get(name)
            found = candidate if callable(candidate) else None
        if found is None:
            if namespace is None:
                namespace = _ipython_user_namespace()
            candidate = namespace.get(name)
            found = candidate if callable(candidate) else None
        if found is None:
            raise DrdAnalysisError(
                f"{name} is not available. This step runs inside the perimeter and gets its "
                f"only query path from the configuration notebook. Run that notebook first, "
                f"then load this file into the same kernel."
            )
        resolved.append(found)
    return resolved[0], resolved[1]


def cost_plan(sql_by_key: Mapping[str, str], dry_run_gb: Callable[[str], float], *,
              budget_gb: float = DRD_BUDGET_GB) -> dict[str, Any]:
    """Price every query before any of them runs, and refuse the whole step if it does not fit."""
    estimates = {key: float(dry_run_gb(sql_by_key[key])) for key in QUERY_KEYS}
    total = sum(estimates.values())
    over_cap = sorted(key for key, gb in estimates.items() if gb > PLANNED_MAX_GB[key])
    return {
        "estimates": estimates,
        "total gb": total,
        "usd": total / 1024.0 * USD_PER_TIB,
        "budget gb": float(budget_gb),
        "over cap": over_cap,
        "fits": (total <= float(budget_gb)) and not over_cap,
    }


def cost_plan_lines(plan: Mapping[str, Any]) -> list[str]:
    lines = [_THIN,
             "COST PLAN. Nothing has executed yet; every figure below came from a free dry run.",
             _THIN]
    rows = [[key.replace("_", " "), f"{plan['estimates'][key]:,.3f}",
             f"{PLANNED_MAX_GB[key]:,.1f}"] for key in QUERY_KEYS]
    lines += _table_lines(["Query", "Estimate, GiB", "Cap, GiB"], rows)
    lines.append(f"total estimate {plan['total gb']:,.3f} GiB, about ${plan['usd']:,.4f}, "
                 f"against a budget of {plan['budget gb']:,.1f} GiB")
    lines.append("Every read is of a derived table. No Controlled Tier table is touched.")
    return lines


def _resolve_features(features: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if features is None:
        namespace = _ipython_user_namespace()
        for name in ("FEATURES", "features_result"):
            candidate = globals().get(name, namespace.get(name))
            if isinstance(candidate, Mapping) and "features ok" in candidate:
                features = candidate
                break
    if features is None:
        raise DrdAnalysisError(
            "the features step's result was not supplied and could not be found. This module "
            "does not run until 04_features.py has certified the derived frames, because an "
            "estimate fitted on frames that failed a null-convention check is a number with "
            "nothing behind it."
        )
    if not bool(features.get("features ok")):
        raise DrdAnalysisError(
            "the features step did not certify the derived frames, so the analysis does not "
            "run. Its halting reasons are in that step's own result and its report; none of "
            "them is a warning."
        )
    return features


def _resolve_collapse(collapse: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if collapse is None:
        namespace = _ipython_user_namespace()
        for name in ("COHORT", "cohort_result"):
            candidate = globals().get(name, namespace.get(name))
            if isinstance(candidate, Mapping) and isinstance(candidate.get("collapse"), Mapping):
                collapse = candidate["collapse"]
                break
    if collapse is None:
        raise DrdAnalysisError(
            "the collapse level was not supplied and could not be found. It is decided ONCE, by "
            "03_cohort.py, on the Phase 3 attrition ladder and before any model is fit. This "
            "module reads it; it does not re-decide it and it does not assume four groups."
        )
    if str(collapse.get("level")) not in COLLAPSE_LEVELS:
        raise DrdAnalysisError("the collapse level supplied is not one of the four the plan "
                               "defines")
    return collapse


def run_drd(
    *,
    features: Mapping[str, Any] | None = None,
    collapse: Mapping[str, Any] | None = None,
    q_guarded: Callable[..., pd.DataFrame] | None = None,
    dry_run_gb: Callable[[str], float] | None = None,
    budget_gb: float = DRD_BUDGET_GB,
    r_runner: Callable[..., Mapping[str, Any]] | None = None,
    draws: int = MONTE_CARLO_DRAWS,
    resamples_primary: int = BOOTSTRAP_PRIMARY,
    resamples_sensitivity: int = BOOTSTRAP_SENSITIVITY,
    run_sensitivity: bool = True,
    extras: Mapping[str, Any] | None = None,
    show_report: bool = True,
) -> dict[str, Any]:
    """Price, read, guard, fit, integrate and report.  Returns the export blocks.

    The order is the same order the earlier steps use: every query is priced by a free dry run
    BEFORE any of them executes, the plan is printed, and the step refuses if the measured total
    exceeds the budget, so a refusal happens with the real number in the human's hand rather
    than after the bill.

    WHAT COMES BACK CARRIES TRUE COUNTS.  `debt` and `sensitivity` are the export contract's
    blocks of those names in RAW form, for `07_export.py` to floor-test and render; the printed
    report is the suppressed view of the same numbers.  The returned object is an in-perimeter
    intermediate and is not a disclosable artefact: pass it to the exporter, and print the
    report.
    """
    certified = _resolve_features(features)
    level = _resolve_collapse(collapse)
    query, dry_run = _resolve_runtime(q_guarded, dry_run_gb)
    sql_by_key = build_sql()
    plan = cost_plan(sql_by_key, dry_run, budget_gb=budget_gb)
    for line in cost_plan_lines(plan):
        print(line)
    if not plan["fits"]:
        raise DrdBudgetExceeded(
            f"nothing executed and nothing billed. The measured dry-run total is "
            f"{plan['total gb']:,.3f} GiB against a budget of {plan['budget gb']:,.1f} GiB, "
            f"and these queries exceeded their own caps: {plan['over cap'] or 'none'}."
        )
    frames: dict[str, pd.DataFrame] = {}
    for key in QUERY_KEYS:
        frames[key] = query(sql_by_key[key], max_gb=PLANNED_MAX_GB[key],
                            note=f"05 recovery debt, {key}")
        safe_show(frames[key], name=key)
    violations = guard_violations(frames["guards"])
    if violations:
        raise DrdAnalysisError(
            "the daily panel failed a stop condition and nothing was fitted:\n  * "
            + "\n  * ".join(violations))

    deviations: list[str] = []
    if int(resamples_primary) != BOOTSTRAP_PRIMARY:
        deviations.append(f"the primary bootstrap ran {int(resamples_primary):,} resamples "
                          f"rather than the locked {BOOTSTRAP_PRIMARY:,}")
    if int(resamples_sensitivity) != BOOTSTRAP_SENSITIVITY:
        deviations.append(f"each sensitivity row ran {int(resamples_sensitivity):,} resamples "
                          f"rather than the locked {BOOTSTRAP_SENSITIVITY:,}")
    if int(draws) != MONTE_CARLO_DRAWS:
        deviations.append(f"the marginalization used {int(draws):,} draws rather than the "
                          f"locked {MONTE_CARLO_DRAWS:,}")

    result = analyze(frames["panel"], frames["episodes"], collapse=level, r_runner=r_runner,
                     draws=draws, resamples_primary=resamples_primary,
                     resamples_sensitivity=resamples_sensitivity,
                     run_sensitivity=run_sensitivity, extras=extras)
    result["cost plan"] = plan
    result["deviations"] = deviations
    result["build parameters"] = (frames["parameters"].iloc[0].to_dict()
                                  if len(frames["parameters"]) else {})
    result["features certified"] = bool(certified.get("features ok"))
    result["report"] = render_report(result)
    if show_report:
        print(result["report"])
        for line in _bullets(deviations):
            print(line)
    return result


# ======================================================================================
# (21) The self-test.  No cloud access, no credentials, no file written.
#
#      The synthetic cohort below is built to carry, on purpose, the states the interesting
#      failures hide in: a null step total beside a real zero, a null deficit beside a real zero
#      deficit, a day that is inpatient AND observed, a censored tail, an episode with no
#      alternative baseline, an episode with valid baseline days in only one half of the week, a
#      device family too rare to model, and MISSINGNESS THAT DEPENDS ON THE DEFICIT, which is
#      the whole reason the estimator is what it is.
# ======================================================================================

_ASSERTIONS = 0


def _expect(condition: bool, message: str) -> None:
    global _ASSERTIONS
    _ASSERTIONS += 1
    if not condition:
        raise AssertionError(message)


def _expect_raises(exc: type, fn: Callable[[], Any], message: str) -> None:
    global _ASSERTIONS
    _ASSERTIONS += 1
    try:
        fn()
    except exc:
        return
    except Exception as other:                      # pragma: no cover - a failing assertion
        raise AssertionError(f"{message} (raised {type(other).__name__} instead)") from None
    raise AssertionError(message)


_FIXTURE_SEED = 20260826
_FIXTURE_DAYS = PANEL_LAST_DAY


def _synthetic_episodes(n_per_group: int, *, four_group: bool) -> pd.DataFrame:
    rng = np.random.default_rng(_FIXTURE_SEED)
    groups = (FOUR_GROUP_SLUGS if four_group
              else ("cervical_decompression", "cervical_fusion"))
    rows: list[dict[str, Any]] = []
    unit = 0
    for slug in groups:
        region, _, kind = slug.partition("_")
        for i in range(n_per_group):
            unit += 1
            baseline = float(np.round(np.exp(rng.normal(8.6, 0.45))))
            if unit % 37 == 0:
                baseline = 700.0                      # below the floor, kept in the primary
            rows.append({
                "unit_index": unit,
                "procedure_group": slug,
                "region": region,
                "fusion": kind == "fusion",
                "age_at_index": float("nan") if unit == 5 else float(rng.normal(61.0, 11.0)),
                "sex_at_birth": SEX_LEVELS[unit % 3],
                "bmi_imputed": float(rng.normal(29.0, 5.0)),
                "bmi_missing": bool(unit % 13 == 0),
                "charlson_ordinal": CHARLSON_LEVELS[unit % 4],
                "charlson_missing": bool(unit % 17 == 0),
                "los_days": int(1 + (unit % 5)),
                "index_year": int(2016 + (unit % 7)),
                "covid_era": bool(2016 + (unit % 7) in (2020, 2021)),
                # Cycled on a modulus coprime with the sex, comorbidity and year cycles on
                # purpose: two covariates cycled on the same modulus are perfectly aliased, and
                # a fixture rank-deficient by accident tests the rank filter and not the
                # estimator.
                "device_family": ("ZIP" if unit % 41 == 0
                                  else ("CHARGE", "VERSA", "SENSE", "LUXE",
                                        "INSPIRE")[unit % 5]),
                "device_changed": bool(unit % 11 == 0),
                "baseline_steps": baseline,
                "n_valid_baseline_days": int(7 + (unit % 12)),
                "meets_baseline_floor": bool(baseline >= BASELINE_FLOOR_STEPS),
                "baseline_steps_60_15": float("nan") if unit % 19 == 0 else baseline * 1.04,
                "baseline_steps_30_1": baseline * 0.97,
                "baseline_steps_s1": baseline * 1.01,
                "baseline_steps_s2": float("nan") if unit % 23 == 0 else baseline * 1.06,
                "baseline_steps_s3": baseline * 0.99,
                "baseline_steps_s4": baseline * 1.02,
                "baseline_steps_weekday": baseline * 1.05,
                "baseline_steps_weekend": (float("nan") if unit % 7 == 0 else baseline * 0.9),
                "n_valid_baseline_days_weekday": int(5 + (unit % 9)),
                "n_valid_baseline_days_weekend": 0 if unit % 7 == 0 else int(2 + (unit % 3)),
                "near_complete_window": True,
                "n_analyzable_days_1_35": 0,
                "at_risk_last_day": 90 if unit % 29 else 30,
            })
    return pd.DataFrame(rows)


def _synthetic_panel(episodes: pd.DataFrame) -> pd.DataFrame:
    """A person-day panel whose MISSINGNESS DEPENDS ON THE DEFICIT, in the direction the plan
    warns about: a worse day is a likelier day to be missing, and the fusion arm carries more of
    it.  A fixture with missingness completely at random would let the naive sum look unbiased
    and would test nothing."""
    rng = np.random.default_rng(_FIXTURE_SEED + 1)
    rows: list[dict[str, Any]] = []
    for _, episode in episodes.iterrows():
        unit = int(episode["unit_index"])
        baseline = float(episode["baseline_steps"])
        los = int(episode["los_days"])
        fusion = bool(episode["fusion"])
        last_day = int(episode["at_risk_last_day"])
        for day in range(ACCRUAL_FIRST_DAY, _FIXTURE_DAYS + 1):
            recovery = 0.22 + 0.62 * (1.0 - math.exp(-day / 11.0)) - (0.13 if fusion else 0.0)
            activity = float(np.clip(recovery * math.exp(rng.normal(0.0, 0.35)), 0.0, 2.2))
            true_deficit = max(0.0, 1.0 - activity)
            propensity = float(expit(np.array(
                [-1.15 + 1.7 * true_deficit + (0.45 if fusion else 0.0) - 0.02 * day]))[0])
            # Half the fixture wears the device every day, so the complete-window row has a
            # denominator of its own to be fitted on and the naive estimator can be compared
            # against the modelled one.  The other half carries the informative pattern.
            adherent = unit % 2 == 0
            missing = False if adherent else bool(rng.random() < propensity)
            censored = day > last_day
            inpatient = bool(4 <= day <= 7 and unit % 31 == 0)
            steps = float("nan") if missing else float(np.round(activity * baseline))
            if unit % 47 == 0 and day == 21 and not missing:
                steps = 0.0                           # a REAL zero-step analyzable day, kept
            valid = (not missing) and (not censored)
            analyzable = bool(valid and np.isfinite(steps) and not censored)
            deficit = (daily_deficit(np.array([steps]), np.array([baseline]))[0]
                       if analyzable else float("nan"))
            untruncated = (daily_deficit_untruncated(np.array([steps]), np.array([baseline]))[0]
                           if analyzable else float("nan"))
            rows.append({
                "unit_index": unit,
                "post_discharge_day": day,
                "postoperative_day": los + day,
                "day_of_week": ((unit + day) % 7) + 1,
                "is_weekend": ((unit + day) % 7) + 1 in (1, 7),
                "steps": steps,
                "valid_wear": valid,
                "valid_wear_s1": valid,
                "valid_wear_s2": bool(valid and np.isfinite(steps) and steps >= 100),
                "valid_wear_s3": valid or (missing and day % 5 == 0),
                "valid_wear_s4": bool(valid and day % 7 != 0),
                "is_analyzable": analyzable,
                "is_censored": censored,
                "is_inpatient": inpatient,
                "in_accrual_window": ACCRUAL_FIRST_DAY <= day <= ACCRUAL_LAST_DAY,
                "in_pod_anchored_window": (POD_ANCHORED_FIRST_DAY <= los + day
                                           <= POD_ANCHORED_LAST_DAY),
                "deficit": deficit,
                "deficit_untruncated": untruncated,
                "lagged_wear_fraction": float("nan"),
            })
    panel = pd.DataFrame(rows)
    lag = (panel.groupby("unit_index")["valid_wear"]
           .transform(lambda s: s.shift(1).rolling(LAG_WINDOW_DAYS, min_periods=1).mean()))
    panel["lagged_wear_fraction"] = lag.astype(float)
    counts = (panel[panel["in_accrual_window"] & panel["is_analyzable"]]
              .groupby("unit_index").size())
    episodes["n_analyzable_days_1_35"] = (
        episodes["unit_index"].map(counts).fillna(0).astype(int))
    episodes["near_complete_window"] = episodes["n_analyzable_days_1_35"] >= 28
    return panel


def _synthetic_frames(n_per_group: int = 24, *, four_group: bool = False,
                      ) -> tuple[pd.DataFrame, pd.DataFrame]:
    episodes = _synthetic_episodes(n_per_group, four_group=four_group)
    panel = _synthetic_panel(episodes)
    return episodes, panel


class _FakeRuntime:
    """A stand-in for the configuration notebook's two helpers."""

    def __init__(self, frames: Mapping[str, pd.DataFrame], gb: float = 0.01) -> None:
        self.frames = dict(frames)
        self.gb = float(gb)
        self.calls: list[tuple[str, float, str]] = []

    def dry_run_gb(self, sql: str) -> float:
        return self.gb

    def q_guarded(self, sql: str, *, max_gb: float, note: str = "") -> pd.DataFrame:
        self.calls.append((sql[:40], max_gb, note))
        for key, frame in self.frames.items():
            if key in note:
                return frame.copy()
        raise AssertionError(f"the fake runtime was asked for an unknown query: {note}")


_BACKTICKED = re.compile(r"`([^`]+)`")
_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
_ALIAS = re.compile(r"\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_DDL = re.compile(r"\b(CREATE|DROP|INSERT|UPDATE|DELETE|MERGE|TRUNCATE|ALTER)\b")
_RANDOMNESS = re.compile(r"\bRAND\s*\(")


def _r_runner_factory(kind: str) -> Callable[..., Mapping[str, Any]]:
    """A fake R analysis environment, so every trigger the R rungs can fire is exercised.

    The real R leg is an injected runner and its absence is trigger T0 (3.5), so the ladder's
    behaviour at rungs 1 and 2 is entirely a function of what a runner returns.  These fakes
    return each of those shapes in turn.
    """
    def runner(family: str, *, response: np.ndarray, design: np.ndarray, cluster: np.ndarray,
               day: np.ndarray, weights: np.ndarray) -> Mapping[str, Any]:
        base = {
            "converged": True,
            "max_gradient": 1e-6,
            "coefficients": np.zeros(design.shape[1]),
            "covariance_re": np.array([[0.25, 0.02], [0.02, 0.09]]),
            "boundary": False,
            "residual_structure": RESIDUAL_STRUCTURE_RUNGS[0]["slug"],
            "rho": 0.4,
            "aic": 1234.0,
        }
        if kind == "converges":
            return base
        if kind == "non convergence":
            return {**base, "converged": False}
        if kind == "gradient":
            return {**base, "max_gradient": 1.0}
        if kind == "boundary":
            return {**base, "boundary": True}
        if kind == "singular":
            return {**base, "covariance_re": np.array([[0.25, 0.5], [0.5, 1.0]])}
        if kind == "zero variance":
            return {**base, "covariance_re": np.array([[0.0, 0.0], [0.0, 0.09]])}
        if kind == "wrong trigger":
            raise RungFailure("T4", "a trigger this rung does not carry")
        if kind == "raises":
            raise ValueError("the environment is not there")
        if kind == "short":
            return {"converged": True, "max_gradient": 1e-6}
        raise AssertionError(f"unknown fake runner {kind}")
    return runner


def _export_bridge_check(result: Mapping[str, Any]) -> dict[str, Any]:
    """Render a REAL result through `07_export.py` and check that it survives the crossing.

    `07_export.py` begins with a digit, so it cannot be imported by name and is loaded through
    `importlib.util.spec_from_file_location`, which is the pattern `02_pregate.py` already uses
    for its own import of `01_probe.py`.

    IT SKIPS RATHER THAN FAILS WHEN THE EXPORTER IS NOT THERE OR IS NOT THE RAW-VALUE VERSION,
    because this module's self-test has to run on its own; but a skip PRINTS its reason, so a
    seam that is silently unchecked cannot be mistaken for a seam that passed.
    """
    notes: list[str] = []
    path = Path(_HERE) / "07_export.py"
    if not path.exists():                            # pragma: no cover - a partial checkout
        return {"ran": False, "notes": ["  export bridge              : SKIPPED, "
                                        "07_export.py is not beside this module"]}
    import importlib.util

    spec = importlib.util.spec_from_file_location("_drd_export_bridge", path)
    if spec is None or spec.loader is None:          # pragma: no cover - a loader that refuses
        return {"ran": False, "notes": ["  export bridge              : SKIPPED, "
                                        "07_export.py could not be loaded"]}
    export = importlib.util.module_from_spec(spec)
    sys.modules["_drd_export_bridge"] = export
    spec.loader.exec_module(export)

    entry = getattr(export, "FIXTURE_BY_GROUP", (None,))[0]
    if not isinstance(entry, Mapping) or not {
            "true_n", "true_complete_windows", "zero_debt_true_n"} <= set(entry):
        return {"ran": False, "notes": [
            "  export bridge              : SKIPPED. 07_export.py still consumes finished",
            "                               disclosure nodes, so the two halves of this seam",
            "                               cannot be joined yet"]}

    _expect(set(getattr(export, "BOUND_SENSITIVITY_ROWS", ())) == set(BOUND_SENSITIVITY_SLUGS),
            "the two modules agree on which ladder row carries a bound rather than an "
            "interval, which is the difference between printing a grid coordinate and "
            "printing a confidence band that does not exist")
    _expect(set(getattr(export, "RESIDUAL_STRUCTURE_DISPLAY", {}))
            == {rung["slug"] for rung in RESIDUAL_STRUCTURE_RUNGS},
            "and on the three residual rungs of 3.4, so the structure the fit reached is one "
            "the exporter can name rather than one it prints raw")

    payload = export.fixture_payload()
    payload["debt"] = result["debt"]
    payload["sensitivity"] = result["sensitivity"]
    payload["forest_rows"], payload["figure3_blocks"] = export.render_forest_rows(
        result["debt"]["contrasts"], result["sensitivity"], export.FIXTURE_SUBGROUPS)
    rendered, _specs, log = export.render_bundle(payload)

    _expect(rendered["suppressed"]["n_entries"] > 0,
            "THE EXPORTER SUPPRESSED SOMETHING, which is the evidence that TRUE counts reached "
            "it: a block handed over already rounded gives its floor test nothing to find and "
            "leaves `results.json.suppressed` empty")
    _expect(rendered["suppressed"]["n_entries"] == len(log.entries),
            "and the log it wrote counts the entries it holds")
    debt_paths = [e["path"] for e in rendered["suppressed"]["entries"]
                  if e["path"].startswith("debt.")]
    _expect(bool(debt_paths),
            "and at least one of those entries names a path inside the debt block, which is "
            "the block this seam carries")
    for entry_index, (raw, node) in enumerate(zip(result["debt"]["by_group"],
                                                  rendered["debt"]["by_group"])):
        if disclosable(raw["true_n"]):
            _expect(int(node["n"]["n"]) == int(round20(raw["true_n"])),
                    "every disclosed count is the ROUNDED form of the true count the exporter "
                    "was given, which is only possible if it was given the true one")
        else:
            _expect(node_is_suppressed(node["n"]) and "n" not in node["n"],
                    "and every count the floor rejects arrives with no numeral at all")
        _expect(f"debt.by_group[{entry_index}].n" not in debt_paths
                or node_is_suppressed(node["n"]),
                "a count recorded as suppressed is a count with no number beside it")
    notes.append(f"  export bridge              : a real result rendered through "
                 f"07_export.py, with the")
    notes.append(f"                               {rendered['suppressed']['n_entries']} "
                 f"suppressions it recorded written by the EXPORTER,")
    notes.append( "                               which is the module that owns the floor")
    return {"ran": True, "notes": notes, "results": rendered}


def _run_self_test() -> None:
    """Drive every pure function in this module against synthetic data with a known answer."""
    global _ASSERTIONS
    _ASSERTIONS = 0

    # ---- 1. the deficit function, and the convexity it is defined by ----------------------
    steps = np.array([0.0, 2000.0, 5000.0, 8000.0, float("nan")])
    base = np.array([5000.0, 5000.0, 5000.0, 5000.0, 5000.0])
    deficit = daily_deficit(steps, base)
    _expect(deficit[0] == 1.0, "a real zero-step day on a worn device is a deficit of exactly 1")
    _expect(abs(deficit[1] - 0.6) < FLOAT_TOLERANCE, "the deficit is one minus the ratio")
    _expect(deficit[2] == 0.0, "a day at baseline contributes nothing")
    _expect(deficit[3] == 0.0, "a day above baseline is truncated at zero and never negative")
    _expect(math.isnan(deficit[4]), "A NULL STEP TOTAL YIELDS A NULL DEFICIT, NEVER A ZERO")
    _expect(math.isnan(daily_deficit(np.array([100.0]), np.array([float("nan")]))[0]),
            "a null baseline yields a null deficit, never a zero")
    _expect_raises(DrdAnalysisError, lambda: daily_deficit(np.array([1.0]), np.array([0.0])),
                   "a baseline of zero is a bug upstream and raises rather than being clipped")
    untruncated = daily_deficit_untruncated(steps, base)
    _expect(untruncated[3] < 0, "the untruncated response can be negative by construction")
    _expect(math.isnan(untruncated[4]), "and a null step total is still null there")

    # Jensen's inequality, on a case where the two differ by a fifth of the daily scale.
    activity = np.array([0.2, 1.4])
    mean_of_deficit = float(np.mean(np.maximum(0.0, 1.0 - activity)))
    deficit_of_mean = float(max(0.0, 1.0 - activity.mean()))
    _expect(mean_of_deficit > deficit_of_mean + 0.15,
            "the deficit function is convex, so applying it to a mean activity understates the "
            "debt measurably")
    _expect(abs(mean_of_deficit - 0.4) < FLOAT_TOLERANCE
            and abs(deficit_of_mean - 0.2) < FLOAT_TOLERANCE,
            "and the two sides of the inequality are the known 0.4 and 0.2 on this case")

    # ---- 2. the spline basis and the link ------------------------------------------------
    basis = restricted_cubic_spline(np.arange(1.0, 36.0), DAY_KNOTS)
    _expect(basis.shape == (35, spline_degrees_of_freedom(DAY_KNOTS)),
            "the restricted basis has one fewer column than it has knots")
    _expect(np.allclose(basis[:, 0], np.arange(1.0, 36.0)),
            "the first basis column is the linear term")
    tail = restricted_cubic_spline(np.array([40.0, 60.0, 80.0]), DAY_KNOTS)
    second = np.diff(np.diff(tail[:, 1]))
    _expect(abs(float(second[0])) < 1e-6,
            "the basis is linear beyond the outer knot, which is what restricted means")
    _expect_raises(DrdAnalysisError, lambda: restricted_cubic_spline([1.0], (5, 5, 6)),
                   "knots must be strictly increasing")
    _expect(abs(float(expit(np.array([0.0]))[0]) - 0.5) < FLOAT_TOLERANCE, "the link at zero")
    _expect(abs(float(logit(np.array([0.5]))[0])) < FLOAT_TOLERANCE, "and its inverse")
    _expect(np.isfinite(logit(np.array([0.0, 1.0]))).all(),
            "the log odds is held off both boundaries so a shifted arm cannot be infinite")

    # ---- 3. the Monte Carlo marginalization ----------------------------------------------
    covariance = np.array([[0.6, 0.05], [0.05, 0.2]])
    eta = np.linspace(-2.0, 2.0, 200)
    day = np.linspace(1.0, 35.0, 200)
    first = monte_carlo_marginal_mean(eta, day, covariance, inverse_link=expit,
                                      draws=500, rng=np.random.default_rng(SEED))
    again = monte_carlo_marginal_mean(eta, day, covariance, inverse_link=expit,
                                      draws=500, rng=np.random.default_rng(SEED))
    chunked = monte_carlo_marginal_mean(eta, day, covariance, inverse_link=expit, draws=500,
                                        rng=np.random.default_rng(SEED), chunk_rows=7)
    _expect(np.array_equal(first, again), "the same seed gives the identical marginal mean")
    _expect(np.allclose(first, chunked), "and the chunk size is a memory bound, not an answer")
    at_zero = expit(eta)
    _expect(float(np.max(np.abs(first - at_zero))) > 0.02,
            "MARGINALIZING IS NOT EVALUATING AT A ZERO RANDOM EFFECT: with a nonlinear link the "
            "two differ, and the marginal mean is the estimand")
    _expect(abs(float(random_effect_standard_deviation(np.array([[0.25]]), day)[0])
                - 0.5) < FLOAT_TOLERANCE,
            "an intercept-only covariance gives one standard deviation at every day")
    slope_sd = random_effect_standard_deviation(covariance, np.array([1.0, 35.0]))
    _expect(slope_sd[0] != slope_sd[1],
            "a random slope makes the random-effect scale a function of the day")
    _expect_raises(DrdAnalysisError,
                   lambda: monte_carlo_marginal_mean(eta, day, covariance, inverse_link=expit,
                                                     draws=0, rng=np.random.default_rng(0)),
                   "a marginalization with no draw at all is refused")

    # ---- 4. the observation weights ------------------------------------------------------
    probability = np.linspace(0.05, 0.95, 500)
    weights, summary = stabilized_weights(probability, marginal=0.6)
    _expect(weights.min() >= summary["truncation low"] - FLOAT_TOLERANCE
            and weights.max() <= summary["truncation high"] + FLOAT_TOLERANCE,
            "the weights are truncated at the prespecified percentiles of their own "
            "distribution")
    _expect(summary["share truncated"] > 0, "and the share truncated is reported")
    _expect_raises(DrdAnalysisError, lambda: stabilized_weights(np.array([0.0]), marginal=0.5),
                   "an observation probability of zero would make a weight infinite and is "
                   "refused rather than clipped in silence")
    _expect(abs(weighted_mean([1.0, 3.0], [1.0, 3.0]) - 2.5) < FLOAT_TOLERANCE,
            "the weighted mean is the weighted mean")
    _expect_raises(DrdAnalysisError, lambda: weighted_mean([1.0], [0.0]),
                   "a stratum with no positive weight is missing, not zero")

    # ---- 5. the node grammar and the two disclosure questions -----------------------------
    _expect(not disclosable(MIN_CELL_PROBE) and is_legal_disclosed_count(MIN_CELL_PROBE),
            "a TRUE count of twenty is below the floor while a RENDERED twenty is legal, and "
            "the two questions are not the same question")
    _expect(node_is_suppressed(count_node(MIN_CELL_PROBE)), "so a true twenty suppresses")
    twenty_one = count_node(MIN_CELL_PROBE + 1)
    _expect(twenty_one["n"] == MIN_CELL_PROBE and twenty_one["rounded"],
            "and a true twenty-one discloses as a rounded twenty")
    zero = count_node(0)
    _expect(zero["n"] == 0 and not zero["rounded"] and not node_is_suppressed(zero),
            "a true zero is an absence and is disclosed, unrounded")
    _expect("n" not in count_node(3) and "display" in count_node(3),
            "A SUPPRESSED NODE CARRIES NO NUMERIC KEY AT ALL: the number is not in the file")
    _expect(percentage_node(3, 400)["reason"] == "numerator_suppressed",
            "a percentage is suppressed whenever its numerator is, because a percentage times a "
            "disclosed denominator recovers the hidden count")
    share = percentage_node(140, 340)
    _expect(share["pct"] == round(100 * round20(140) / round20(340)) and share["display"]
            .endswith("%"), "and it is computed from the rounded numerator over the rounded "
                            "denominator, to zero decimals")
    estimate = estimate_node(4.4, 2.6, 6.2, "activity_days", contributing_n=340)
    _expect(estimate["display"] == "4.4 (95% CI 2.6 to 6.2)",
            "a confidence interval always uses the word to, because it may cross zero")
    _expect(node_is_suppressed(estimate_node(1.0, 0.0, 2.0, "activity_days", contributing_n=5)),
            "an estimate is suppressed when the count contributing to it is below the floor")
    bound = bound_node(9.1, "activity_days", contributing_n=340)
    _expect(bound["display_ci"] == "" and bound["lo"] == bound["hi"] == bound["est"],
            "A MANSKI BOUND IS A BOUND, NOT AN INTERVAL, so its interval keys collapse onto the "
            "point and its interval display is empty")
    quantile = quantile_node([1.0, 2.0, 3.0, 4.0, 9.0], "activity_days", contributing_n=340)
    _expect(_EN_DASH in quantile["display_iqr"] and " to " not in quantile["display_iqr"],
            "an observed quantile range uses the en-dash, because it never carries a sign")
    _expect(pvalue_node(0.0004, contributing_n=340)["display"] == "P < 0.001",
            "a small P value is floored in house style")
    _expect(pvalue_node(0.223, contributing_n=340)["display"] == "P = 0.223",
            "and a larger one prints to three decimals")
    _expect(scalar_node(35)["display"] == "35", "a scalar is a constant and is never suppressed")
    _expect_raises(DisclosureError, lambda: _assert_display(f"a{EM_DASH}b"),
                   "no display string may carry an em-dash")
    _expect_raises(DisclosureError, lambda: _assert_display(f"a{MINUS_SIGN}b"),
                   "and none may carry a Unicode minus sign")

    # ---- 6. the locked vocabulary --------------------------------------------------------
    _expect(SEX_LEVELS == ("male", "female", "other_or_unknown") and SEX_REFERENCE == "male",
            "THE SEX FACTOR IS THE PLAN'S OWN: 'Factor: male, female, other or unknown', with "
            "male the reference, and `06_analysis_gate.py` carries the identical tuple. Which "
            "level is omitted does not move the contrast, because the column space is the same "
            "either way; it moves the order the rank filter drops columns in, and it moves what "
            "a reader is told the comparison is against")
    _expect(SEX_REFERENCE in SEX_LEVELS and BOUND_SENSITIVITY_SLUGS <= set(
        PLOTTED_SENSITIVITY_SLUGS),
            "the reference is one of the levels, and every row said to carry a bound is a row "
            "the plan plots")
    _expect(BOOTSTRAP_FAILURES == (DrdAnalysisError, RungFailure, np.linalg.LinAlgError)
            and not any(issubclass(Exception, kind) for kind in BOOTSTRAP_FAILURES),
            "A RESAMPLE MAY FAIL IN THREE NAMED WAYS AND NO OTHER. A bare `except Exception` "
            "counts a coding bug inside the estimator as a bootstrap failure, and at a 100 "
            "percent failure rate that fires trigger T4 and descends the family ladder for a "
            "reason that is not the model")
    _expect(len(PLOTTED_SENSITIVITY_SLUGS) == 14,
            "the plan expands ten ladder rows into exactly fourteen plotted rows")
    _expect(len(set(PLOTTED_SENSITIVITY_SLUGS)) == 14, "and the fourteen are distinct")
    _expect(len(SUPPLEMENTARY_SENSITIVITY_SLUGS) == 10,
            "ten supplementary rows at plan version 1.3")
    _expect(not set(PLOTTED_SENSITIVITY_SLUGS) & set(SUPPLEMENTARY_SENSITIVITY_SLUGS),
            "THE TWO SETS ARE DISJOINT, which is what the set-equality assertion rests on")
    orders = [(row["order"], row["sub"]) for row in PLOTTED_SENSITIVITY_ROWS]
    _expect(orders == sorted(orders),
            "the plotted rows are in the plan's own order and cannot be rearranged to put a "
            "reassuring row at the top")
    _expect(max(row["order"] for row in PLOTTED_SENSITIVITY_ROWS) == 10,
            "ten ladder rows carry the fourteen")
    panels = [row for row in PLOTTED_SENSITIVITY_ROWS if row["render"] == "panel"]
    _expect(len(panels) == 1 and panels[0]["slug"] == "delta_shift_tipping_point"
            and panels[0]["axis"] != "primary",
            "exactly one row renders as a panel, and it is the only row not on the primary axis")
    _expect(all(row["axis"] == "primary" for row in PLOTTED_SENSITIVITY_ROWS
                if row["render"] == "marker"),
            "a row not on the primary axis never renders as a marker on the shared scale")
    _expect(SENSITIVITY_LABELS["observation_weighted"] == "Weighted for observation",
            "the weighting row's label is exactly those three words")
    _expect(len(ESTIMATOR_RUNGS) == 5
            and [r["index"] for r in ESTIMATOR_RUNGS] == [1, 2, 3, 4, 5],
            "the family ladder has five rungs and the index is its position")
    _expect(ESTIMATOR_RUNGS[4]["triggers"] == (),
            "THE FLOOR HAS NO DESCENT TRIGGER, which is why the ladder cannot be exhausted and "
            "why the debt is never absent for want of an estimator")
    _expect(all(set(r["triggers"]) <= set(DESCENT_TRIGGERS) for r in ESTIMATOR_RUNGS),
            "every trigger a rung may fire is one the plan names")
    _expect(len(CONTRAST_SLUGS) == 5 and CONTRAST_SLUGS[0] == PRIMARY_CONTRAST_SLUG,
            "five contrasts in Figure 3 block 1 order, the primary first")
    _expect(set(SUPPRESSION_SENTENCES) >= {"cell_below_threshold", "not_estimable_cell_size"},
            "the suppression sentences are the contract's own")
    import disclosure as _disclosure_module
    # COMPARED AS AN ORDERED SEQUENCE, not as two dicts.  This module's copy is a mapping
    # and `disclosure.SUPPRESSION_REASONS` is an ordered tuple, and `dict == dict` ignores
    # order, so the old form could not have seen a row transcribed into the wrong position.
    # 7.5 makes the row order load-bearing -- `tests/test_disclosure.py` parses the table
    # and asserts ordered equality against it -- so this asserts the same thing the
    # contract does, on the insertion order a mapping already carries.
    _expect(tuple(SUPPRESSION_SENTENCES.items())
            == tuple(_disclosure_module.SUPPRESSION_REASONS),
            "AND THIS MODULE'S COPY IS CHARACTER-IDENTICAL TO THE ONE `disclosure.py` "
            "transcribes from EXPORT-CONTRACT 7.5, reason for reason, sentence for "
            "sentence AND ROW FOR ROW. A copy that drifts by one row is how a module comes "
            "to emit a reason the exporter cannot name, and it drifts silently")

    # ---- 7. the emitted SQL --------------------------------------------------------------
    for key, sql in build_sql().items():
        placeholders = set(_PLACEHOLDER.findall(sql))
        _expect(placeholders <= {"{DERIVED}"},
                f"the {key.replace('_', ' ')} query names only the sanctioned placeholder")
        for quoted in _BACKTICKED.findall(sql):
            _expect(quoted.startswith("{DERIVED}."),
                    f"the {key.replace('_', ' ')} query quotes no hardcoded project or dataset")
        _expect(not _DDL.search(sql),
                f"the {key.replace('_', ' ')} query contains no data-definition statement")
        _expect(not _RANDOMNESS.search(sql),
                f"the {key.replace('_', ' ')} query draws no unseeded random number")
        aliases = set(_ALIAS.findall(sql))
        for column in declared_columns(sql):
            _expect(column in aliases,
                    f"the {key.replace('_', ' ')} query aliases every column it declares")
    _expect_raises(DrdAnalysisError, lambda: _sql("SELECT <<NOT_A_CONSTANT>>"),
                   "a query naming a constant this module does not define is refused rather "
                   "than half-written")
    _expect_raises(DrdAnalysisError, lambda: declared_columns("SELECT 1"),
                   "a query with no column declaration is refused")

    # ---- 8. the family ladder, and every trigger that descends it -------------------------
    rows = 240
    fake_design = np.column_stack([np.ones(rows), np.linspace(0.0, 1.0, rows)])
    fake_response = np.clip(np.linspace(0.05, 0.95, rows), 0.0, 1.0)
    fake_cluster = np.repeat(np.arange(24), 10)
    fake_day = np.tile(np.arange(1.0, 11.0), 24)
    fake_group = np.array(["fusion"] * rows, dtype=object)
    fake_weights = np.ones(rows)

    def walk(**kwargs: Any) -> dict[str, Any]:
        _, record = fit_deficit_ladder(
            response=fake_response, design=fake_design, cluster=fake_cluster, day=fake_day,
            group=fake_group, weights=fake_weights, **kwargs)
        return record

    reached = walk(r_runner=_r_runner_factory("converges"))
    _expect(reached["rung index"] == 1 and reached["r used"]
            and reached["descent triggers fired"] == (),
            "a clean R fit stops the ladder at its first rung with no trigger fired")
    _expect(reached["rungs attempted"][0]["outcome"] == "converged"
            and reached["rungs attempted"][4]["outcome"] == "not attempted",
            "and the rungs below it are recorded as not attempted, never as failures")

    absent = walk(r_runner=None)
    _expect(absent["rung index"] == 3 and absent["descent triggers fired"][0] == "T0",
            "T0 SKIPS BOTH R RUNGS TOGETHER, because the environment is unavailable for both")
    _expect([a["outcome"] for a in absent["rungs attempted"]][:2] == ["skipped", "skipped"],
            "and both are recorded as skipped rather than as non-convergence")
    _expect(absent["fallback reason"], "a descent always carries a printable reason")

    for kind, trigger in (("non convergence", "T1"), ("gradient", "T1"), ("boundary", "T2"),
                          ("singular", "T3"), ("zero variance", "T2"), ("raises", "T0")):
        record = walk(r_runner=_r_runner_factory(kind))
        _expect(trigger in record["descent triggers fired"],
                f"the ladder descends on {trigger} and records it")
        _expect(record["rung index"] > 1, "and lands below the rung that fired it")
        _expect(all(a["outcome"] in RUNG_OUTCOMES for a in record["rungs attempted"]),
                "every recorded outcome is one of the four the contract permits")

    _expect_raises(DrdAnalysisError, lambda: walk(r_runner=_r_runner_factory("wrong trigger")),
                   "A RUNG MAY ONLY DESCEND ON A TRIGGER ITS OWN ROW OF THE LADDER NAMES; any "
                   "other is a stop condition rather than a quiet descent")
    _expect_raises(DrdAnalysisError, lambda: walk(r_runner=_r_runner_factory("short")),
                   "an R result that cannot answer the trigger questions is refused")
    _expect_raises(DrdAnalysisError, lambda: RungFailure("T9", "invented"),
                   "a trigger outside the plan's five cannot even be constructed")

    floored = walk(r_runner=_r_runner_factory("converges"), min_rung=3)
    _expect("T4" in floored["descent triggers fired"] and floored["rung index"] >= 3,
            "bootstrap instability descends one rung and records trigger T4")
    quiet = walk(r_runner=_r_runner_factory("converges"), min_rung=3, min_rung_trigger=None)
    _expect(quiet["descent triggers fired"] == () and quiet["rung index"] >= 3,
            "while a sensitivity row starting at the primary's rung fires no trigger, because "
            "it is not a descent")
    unbounded = walk(r_runner=_r_runner_factory("converges"), bounded_response=False)
    _expect(unbounded["rung index"] >= 4
            and [a["outcome"] for a in unbounded["rungs attempted"]][:3]
            == ["skipped", "skipped", "skipped"],
            "an untruncated response skips the three bounded families, which is a property of "
            "the response and not a descent")
    _expect(len(unbounded["descent triggers fired"])
            == sum(1 for a in unbounded["rungs attempted"]
                   if a["outcome"] == "did not converge"),
            "and the skip itself fires no trigger: the count of triggers equals the count of "
            "rungs that were actually attempted and failed, because those three rungs were "
            "never available to this row rather than descended from")
    _expect("T0" not in unbounded["descent triggers fired"],
            "in particular it is not recorded as an environment failure, which it is not")

    # ---- 9. the tipping point ------------------------------------------------------------
    grid = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
    falling = [3.0, 2.4, 1.6, 0.9, 0.4, -0.2, -0.9]
    crossing = first_crossing(grid, falling)
    _expect(crossing["crossed"] and crossing["delta"] == 1.5,
            "the reported crossing is the smallest grid shift at which the contrast has crossed")
    _expect(crossing["value before"] > 0.0 >= crossing["value after"],
            "AND THE CROSSING IS REAL: the value before it is strictly positive and the value "
            "at it is not")
    _expect(crossing["monotone"], "the curve is monotone in the shift, which is checked")
    _expect(not first_crossing(grid, [3.0, 2.9, 2.8, 2.7, 2.6, 2.5, 2.4])["crossed"],
            "a curve that never reaches zero reports no tipping point rather than the last "
            "grid point")
    already = first_crossing(grid, [-0.5, -0.6, -0.7, -0.8, -0.9, -1.0, -1.1])
    _expect(not already["crossed"] and already["already at or below zero"],
            "a contrast already at or below zero is reported as such, not as a tipping point "
            "of zero, which would be a different and much weaker claim")
    _expect(not first_crossing(grid, [3.0, 2.0, 2.5, 1.0, 0.5, -0.1, -0.5])["monotone"],
            "a curve that is not monotone is reported as such")
    interval = first_interval_crossing(grid, [2.0, 1.5, 0.8, -0.1, -0.5, -1.0, -1.4],
                                       [4.0, 3.5, 2.8, 2.0, 1.6, 1.0, 0.5])
    _expect(interval["crossed"] and interval["delta"] == 0.75,
            "the interval crossing is the smallest shift at which the interval first includes "
            "zero")
    _expect_raises(DrdAnalysisError, lambda: first_crossing([0.0], [1.0]),
                   "a tipping point needs at least two grid points")
    _expect(delta_grid(False) == DELTA_GRID and delta_grid(True)[-1] == DELTA_EXTENSION_LAST,
            "the grid extends in the prespecified increments to 4.0 and no further")
    _expect(len(delta_grid(True)) == len(DELTA_GRID) + 4,
            "which is four extra points, written down before the measurement exists")
    _expect(abs(implied_deficit_at_reference(0.0) - DELTA_REFERENCE_DEFICIT) < 1e-9,
            "a shift of zero leaves the reference day where it was")
    _expect(implied_deficit_at_reference(2.0) > implied_deficit_at_reference(1.0)
            > implied_deficit_at_reference(0.0),
            "and the translation is computed rather than hand-typed, and rises with the shift")

    # ---- 10. the synthetic cohort, and the null that decides the answer -------------------
    episodes, panel = _synthetic_frames(24, four_group=False)
    _expect(set(declared_columns(episodes_sql())) == set(episodes.columns),
            "the episode fixture carries exactly the columns the episode query declares")
    _expect(set(declared_columns(panel_sql())) == set(panel.columns),
            "the panel fixture carries exactly the columns the panel query declares")
    spec = ModelSpec("two_group", TWO_GROUP_SLUGS)
    primary = prepare_primary(panel, episodes, spec)

    response = primary.days["response"].to_numpy(dtype=float)
    observed = primary.observed
    _expect(np.all(np.isnan(response[~observed])),
            "EVERY UNOBSERVED DAY CARRIES A NULL DEFICIT AND NOT A ZERO, in the fixture as in "
            "the derived build")
    _expect(int(np.sum(~observed & primary.in_window)) > 0,
            "and the fixture actually contains unobserved days inside the window, so the "
            "property is being tested rather than vacuously satisfied")
    _expect(not np.any(primary.fit_rows & ~observed),
            "the model is fitted on observed person-days only")
    real_zero = np.sum(observed & (response == 0.0))
    _expect(real_zero > 0, "and a real zero deficit, a day at or above baseline, is kept")

    broken = panel.copy()
    unobserved_rows = np.where(~broken["is_analyzable"].to_numpy().astype(bool))[0]
    broken.loc[broken.index[unobserved_rows[0]], "deficit"] = 0.0
    _expect_raises(DrdAnalysisError, lambda: prepare_primary(broken, episodes, spec),
                   "A ZERO DEFICIT ON AN UNOBSERVED DAY HALTS THE ESTIMATOR. It asserts the "
                   "participant walked at or above their own baseline on a day nobody measured, "
                   "and it is the one imputation this whole estimator exists to avoid")

    clean_guard = pd.DataFrame([{name: 0 for name in GUARD_SENTENCES}
                                | {"n_panel_rows": 2016, "n_units": 48}])
    _expect(guard_violations(clean_guard) == [], "a clean panel raises no guard")
    for name in GUARD_SENTENCES:
        dirty = clean_guard.copy()
        dirty.loc[0, name] = 3
        _expect(len(guard_violations(dirty)) == 1,
                f"the guard for {name.replace('_', ' ')} fires on a non-zero count")
    _expect(guard_violations(pd.DataFrame([{"n_units": 0} | {n: 0 for n in GUARD_SENTENCES}])),
            "a panel with no episode at all is a stop condition")

    # A sensitivity recomputation still turns a null step total into a null deficit.
    wear_variant = build_plotted_variant("wear_definition_s2", primary)
    recomputed = wear_variant.days["response"].to_numpy(dtype=float)
    missing_steps = ~np.isfinite(wear_variant.days["steps"].to_numpy(dtype=float))
    _expect(np.all(np.isnan(recomputed[missing_steps])),
            "the recomputed sensitivity deficit is null wherever the step total is null")
    _expect(wear_variant.n_units < primary.n_units,
            "and a sensitivity fitted where its own baseline exists has its OWN denominator")

    # ---- 11. the convexity trap, demonstrated on the module's own estimator ---------------
    floor_fit = estimate_variant(primary, draws=32, min_rung=5, min_rung_trigger=None)
    _expect(floor_fit["ladder"]["rung index"] == 5, "the nonparametric floor was the rung used")
    rows_in = primary.in_window & primary.fit_rows
    frame = pd.DataFrame({
        "group": group_slug_for(
            spec, primary.episodes["region"].to_numpy(dtype=object)[
                primary.days["unit_pos"].to_numpy()[rows_in].astype(int)],
            primary.episodes["fusion"].to_numpy().astype(bool)[
                primary.days["unit_pos"].to_numpy()[rows_in].astype(int)]),
        "day": primary.days["day"].to_numpy()[rows_in],
        "deficit": primary.days["response"].to_numpy(dtype=float)[rows_in],
        "activity": (primary.days["steps"].to_numpy(dtype=float)[rows_in]
                     / primary.baseline_by_day[rows_in]),
    })
    gaps: dict[str, float] = {}
    spreads: dict[str, float] = {}
    for group_slug in TWO_GROUP_SLUGS:
        block = frame[frame["group"] == group_slug]
        mean_of_deficit_sum = float(block.groupby("day")["deficit"].mean().sum())
        deficit_of_mean_sum = float(
            np.maximum(0.0, 1.0 - block.groupby("day")["activity"].mean()).sum())
        _expect(mean_of_deficit_sum > deficit_of_mean_sum,
                f"ON THE FIXTURE'S OWN DATA the inequality runs the way Jensen says it must for "
                f"{GROUP_LABELS[group_slug].lower()}: applying the deficit function to a mean "
                f"activity understates the debt, and the module models the deficit directly and "
                f"therefore reports the larger, correct quantity")
        gaps[group_slug] = mean_of_deficit_sum - deficit_of_mean_sum
        spreads[group_slug] = float(block.groupby("day")["activity"].var().mean())
        if group_slug == "fusion":
            _expect(abs(floor_fit["by group"]["fusion"] - mean_of_deficit_sum) < 0.5,
                    "and the estimator's own group level matches the mean-of-deficit side of "
                    "the inequality, not the deficit-of-mean side")
    _expect(sum(gaps.values()) > 1.0,
            "the understatement is measurable rather than a rounding artefact: more than a "
            "whole activity day lost across the two arms")
    _expect(max(gaps, key=lambda g: gaps[g]) == max(spreads, key=lambda g: spreads[g]),
            "AND IT IS LARGEST WHERE THE ACTIVITY IS MOST VARIABLE, which is the second half of "
            "the plan's claim and the reason the bias is not a wash between the arms")

    # ---- 11b. the covariate-free design of STROBE item 16(a) -------------------------------
    adjusted_design = DesignBuilder(primary.episodes, spec)
    plain_design = DesignBuilder(primary.episodes, spec, include_covariates=False)
    _expect(adjusted_design.include_covariates and not plain_design.include_covariates,
            "the covariate-free design is asked for by name and never inferred from a shape")
    _expect(len(plain_design.names) < len(adjusted_design.names),
            "IT IS THE SAME MEAN STRUCTURE MINUS ONE BLOCK, so it has strictly fewer columns")
    _expect(set(plain_design.names) < set(adjusted_design.names),
            "and its columns are a SUBSET of the adjusted design's, which is what makes this "
            "the same estimator with the covariates removed rather than a second estimator")
    _COVARIATE_STEMS = ("age", "sex", "bmi", "charlson", "log one plus stay", "index year",
                        "covid era", "device")
    _expect(not [n for n in plain_design.names
                 if any(n.startswith(stem) for stem in _COVARIATE_STEMS)],
            "EVERY MEMBER OF THE PLAN'S LOCKED COVARIATE TABLE IS GONE: age, sex assigned at "
            "birth, body mass index, comorbidity burden, length of stay, index year, the "
            "COVID-19 era indicator and device family")
    _expect(any(n.startswith("day spline") for n in plain_design.names)
            and "fusion" in plain_design.names
            and any(n.startswith("day of week") for n in plain_design.names),
            "AND EVERYTHING THE ESTIMAND IS DEFINED ON IS KEPT: the post-discharge-day spline, "
            "the procedure-group term and the day-of-week fixed effect are not confounders held "
            "fixed, they are the axes the g-computation integrates over, and deleting them "
            "would change the estimand rather than unadjust it")
    _expect(set(plain_design.dropped_names) <= set(adjusted_design.dropped_names)
            and not [n for n in plain_design.dropped_names
                     if any(n.startswith(stem) for stem in _COVARIATE_STEMS)],
            "the empty covariate block is an empty block and not a block of zeros: the "
            "covariate-free design drops no column the adjusted one kept, so an intentional "
            "absence is never reported as a rank deficiency the cohort caused")
    _expect_raises(DrdAnalysisError,
                   lambda: DesignBuilder(primary.episodes, spec, include_covariates=False,
                                         include_log_baseline=True),
                   "a covariate-free design that also carries the log-baseline spline is two "
                   "incompatible requests at once and is refused rather than quietly served")
    _expect_raises(DrdAnalysisError,
                   lambda: DesignBuilder(primary.episodes, spec, include_covariates=False,
                                         include_baseline_steps=True),
                   "and so is one that carries the baseline-steps term of the supplementary row")
    _expect_raises(DrdAnalysisError,
                   lambda: clustered_bootstrap(primary, resamples=1, point_rung_index=5,
                                               unadjusted=True),
                   "AND A BOOTSTRAP ASKED FOR THE UNADJUSTED CONTRAST WITH NO RUNG TO JUDGE ITS "
                   "RESAMPLES AGAINST IS A STOP CONDITION, because a resample kept or discarded "
                   "on the wrong fit's rung is an interval around a different estimator")
    _refused = _assemble_unadjusted_model(
        {"ladder": {"rung index": 3}, "unadjusted ladder": None},
        {"attempted": 500, "unadjusted failed": 500, "unadjusted instability trigger": True})
    _expect(_refused["not_estimable_reason"] == "not_estimable_convergence"
            and _refused["rung_display"] is None,
            "AN UNADJUSTED FIT THAT FAILED IS NOT-ESTIMABLE WITH A NAMED REASON, exactly as a "
            "failed adjusted one is, and the reason is carried rather than left to be inferred "
            "at the far end from a triple full of NaNs")
    _expect(_refused["prespecified"] is False
            and _refused["not_estimable_reason"] in SUPPRESSION_SENTENCES,
            "and the reason is a slug of the contract's own suppression vocabulary, so it has a "
            "sentence to print")
    _differs = _assemble_unadjusted_model(
        {"ladder": {"rung index": 3},
         "unadjusted ladder": {"rung index": 4, "rung slug": ESTIMATOR_RUNG_SLUGS[3],
                               "rung display": ESTIMATOR_RUNGS[3]["display"]}},
        {"attempted": 500, "unadjusted failed": 0, "unadjusted instability trigger": False})
    _expect(_differs["rung_matches_adjusted"] is False
            and "different rung" in _differs["rung_note_display"],
            "AND A RUNG THAT DIFFERS BETWEEN THE TWO FITS IS REPORTED RATHER THAN HIDDEN: the "
            "gap between the contrasts then carries a change of model family as well as the "
            "covariate set, and a reader has to be told before reading it as the covariates")

    # ---- 11b. the weight fit leaves the process's error state exactly as it found it ------
    #
    # `np.seterr` is PROCESS state and `warnings.catch_warnings` does not restore it, so a
    # weight fit that set it would silence every overflow, invalid operation and divide by zero
    # for the rest of the session: the bootstrap, the g-computation, the bounds and the
    # exporter. What is checked here is not a number but the return of the diagnostics that
    # would surface the NEXT defect.
    _weight_builder = DesignBuilder(primary.episodes, primary.spec)
    with np.errstate(all="warn"):
        _error_state_before = np.geterr()
        fit_observation_weights(_weight_builder, primary)
        _expect(np.geterr() == _error_state_before,
                "A WEIGHT FIT RESTORES THE FLOATING-POINT ERROR STATE IT WAS CALLED UNDER, "
                "because the suppression it needs is scoped to its own fit and is not a "
                "process-wide setting the rest of the session inherits")
        with warnings.catch_warnings(record=True) as _caught:
            warnings.simplefilter("always")
            _ = np.float64(1.0) / np.float64(0.0)
        _expect(len(_caught) == 1,
                "and a divide by zero AFTER the weight fit still raises its warning, which is "
                "the diagnostic a process-wide suppression would have swallowed")

    # ---- 12. the assumption-free bounds --------------------------------------------------
    bounds = manski_bounds(primary)
    per_unit = bounds["per unit"]
    rows_window = estimand_window(primary)
    unit_pos = primary.days["unit_pos"].to_numpy()[rows_window].astype(int)
    missing_counts = _per_unit_sum((~primary.observed[rows_window]).astype(float),
                                   unit_pos, primary.n_units)
    _expect(np.allclose(per_unit["upper"] - per_unit["lower"], missing_counts),
            "the width of an episode's bound is exactly its count of missing days, because "
            "each such day can contribute anything from zero to one and nothing else")
    check_rng = np.random.default_rng(SEED)
    for _ in range(200):
        completion = check_rng.random(primary.n_units) * missing_counts
        totals_any = per_unit["lower"] + completion
        _expect(bool(np.all(per_unit["lower"] - FLOAT_TOLERANCE <= totals_any)
                     and np.all(totals_any <= per_unit["upper"] + FLOAT_TOLERANCE)),
                "THE BOUNDS BRACKET EVERY POSSIBLE COMPLETION OF THE WINDOW BY CONSTRUCTION, "
                "whatever the missingness mechanism")
    _expect(bounds["contrast"]["lower"] <= bounds["contrast"]["upper"],
            "the contrast bounds are an interval, by interval arithmetic on a difference")
    _expect(sum(v["n"] for slug, v in bounds["by group"].items() if slug != ALL_GROUPS_SLUG)
            == primary.n_units,
            "and the bounds are computed on every eligible episode, not only complete windows")
    _expect(bounds["by group"][ALL_GROUPS_SLUG]["n"] == primary.n_units,
            "THE POOLED ROW IS THE TOTAL AND NOT A FIFTH GROUP: the named groups partition it, "
            "which is what the exporter's secondary-suppression rule rests on")
    _expect_raises(DrdAnalysisError, lambda: manski_from_daily([1.0], [-1.0]),
                   "a negative count of missing days is a bug upstream")

    # ONE WINDOW, ASSERTED AND NOT DOCUMENTED.  Rung 15 removes only the windows truncated by
    # death or by a repeat operation, so an episode censored inside days 1 to 35 by the
    # observation cutoff stays in the analytic cohort; the fixture carries one, which is why
    # the two row sets were never identical and the bounds never bracketed by construction.
    _censored_in_window = primary.in_window & ~primary.at_risk
    _expect(int(np.sum(_censored_in_window)) > 0,
            "the fixture carries a day inside the window the episode was no longer at risk on, "
            "which is exactly the day the point estimate predicts for and the bounds used to "
            "skip")
    _at_risk_rows = primary.in_window & primary.at_risk
    _at_risk_missing = _per_unit_sum(
        (~primary.observed[_at_risk_rows]).astype(float),
        primary.days["unit_pos"].to_numpy()[_at_risk_rows].astype(int), primary.n_units)
    _expect(float(missing_counts.sum()) > float(_at_risk_missing.sum()),
            "AND THE BOUNDS NOW WIDEN OVER IT. A bound taken over fewer days than the estimate "
            "integrates is not a bound on the estimate, whatever the footer beneath it says")
    _expect(np.array_equal(estimand_window(primary), primary.in_window),
            "the bounds, the integration and the normalizing denominator read ONE definition "
            "of the window, so a later edit has to move all three or none")
    # The guard is exercised by making the edit it exists to catch: a bounds computation that
    # narrows its own window back to the at-risk days must halt rather than print.
    _saved_window = globals()["estimand_window"]
    globals()["estimand_window"] = lambda variant: variant.in_window & variant.at_risk
    try:
        _expect_raises(DrdAnalysisError, lambda: manski_bounds(primary),
                       "and narrowing the bounds' window back to the at-risk days is a STOP "
                       "CONDITION and not a documented difference, because the footer would "
                       "otherwise call them bounds on a quantity they do not bound")
    finally:
        globals()["estimand_window"] = _saved_window
    _expect(np.array_equal(estimand_window(primary), primary.in_window),
            "and the guard's own exercise put the definition back")

    # ---- 12b. the two quantities that used to average over different sets -----------------
    #
    # Both are checked on the case where the defect BITES and not on the complete panel where
    # every reading agrees. `analyze` below runs on the fixture as shipped.
    _positions = primary.days["unit_pos"].to_numpy().astype(int)
    _one_short = _with_response(
        primary, slug="one_episode_with_no_window_row",
        response=primary.days["response"].to_numpy(dtype=float),
        in_window=primary.in_window & (_positions != 0),
        note="the first episode carries no day inside the window at all")
    _short_days = _one_short.window_days_per_unit()
    _expect(float(_short_days[0]) == 0.0 and float(_short_days.sum()) > 0.0,
            "the constructed variant has an episode with no window row, which a complete panel "
            "never shows and which the derived build can produce for the inpatient-censored row")
    _short_point = estimate_variant(_one_short, draws=8, seed_spec=SEED)
    _expect(abs(_short_point["mean window days"] - float(_short_days.mean())) < FLOAT_TOLERANCE,
            "THE DENOMINATOR AVERAGES OVER THE SAME EPISODES THE NUMERATOR DOES, all of them, "
            "so an episode contributing a zero to the debt contributes its zero to the window "
            "too and moves neither side")
    _short_value = _short_point["by group"][ALL_GROUPS_SLUG]
    _short_new = _short_point["normalized activity"][ALL_GROUPS_SLUG]
    _short_old = 1.0 - _short_value / float(_short_days[_short_days > 0].mean())
    _expect(_short_old > _short_new + FLOAT_TOLERANCE,
            "and the old reading, whose denominator averaged only over the episodes that HAVE a "
            "window, printed a normalized activity strictly higher than any episode's, because "
            "it divided a numerator diluted by a zero by a denominator that was not")
    _surviving = _short_days[_short_days > 0]
    _expect(float(_surviving.min()) == float(_surviving.max()),
            "every surviving window in this constructed variant is the same length, which is "
            "what makes the next assertion an identity and not an approximation")
    _short_per_episode = 1.0 - (_short_value * _one_short.n_units / float(_surviving.size)
                                ) / float(_surviving[0])
    _expect(abs(_short_new - _short_per_episode) < 1e-9,
            "AND THE FIXED READING IS THE ONE A READER MEANS: with every surviving window the "
            "same length it is exactly the mean, over the episodes that HAVE a window, of that "
            "episode's own mean capped normalized activity")

    # The recovery row is a complete-case fit, so its denominator is the episodes that HAVE the
    # outcome. The fixture as shipped gives almost every episode one, so the case where the
    # denominator differs from the group's is constructed rather than waited for.
    _band = ((primary.days["day"].to_numpy(dtype=float) >= RECOVERY_FIRST_DAY)
             & (primary.days["day"].to_numpy(dtype=float) <= RECOVERY_LAST_DAY))
    _blinded_rows = _band & (_positions % 3 == 0)
    _blind_observed = primary.observed.copy()
    _blind_observed[_blinded_rows] = False
    _blind_response = primary.days["response"].to_numpy(dtype=float).copy()
    _blind_response[_blinded_rows] = float("nan")
    _blind = _with_response(primary, slug="late_window_unobserved", response=_blind_response,
                            observed=_blind_observed,
                            note="a third of the cohort has no observed day in the recovery band")
    _, _blind_summary = fit_recovery_share(DesignBuilder(_blind.episodes, _blind.spec), _blind)
    _expect(_blind_summary["n with outcome"] < _blind.n_units,
            "an episode with no observed day in post-discharge days 29 to 35 has NO OUTCOME AT "
            "ALL, which is a denominator and not a zero")
    _blind_by_group = _blind_summary["n with outcome by group"]
    _expect(set(_blind_by_group) == set(report_groups(_blind.spec)),
            "and the count travels PER GROUP, because the denominator differs between groups "
            "and Table 2 prints a cell per group")
    _expect(_blind_by_group[ALL_GROUPS_SLUG] == _blind_summary["n with outcome"]
            == sum(v for k, v in _blind_by_group.items() if k != ALL_GROUPS_SLUG),
            "the named groups partition the pooled denominator exactly")
    _expect(all(v < _blind.n_units for v in _blind_by_group.values()),
            "AND IT IS SMALLER THAN THE GROUP'S OWN N, which is the whole reason it has to be "
            "carried: the cell used to stand under a denominator no part of it was computed on")

    # A degenerate recovery outcome is UNPRINTABLE and not a plausible constant.
    _flat_response = primary.days["response"].to_numpy(dtype=float).copy()
    _flat_response[_band & primary.observed] = 0.0
    _flat = _with_response(primary, slug="every_outcome_on_one_side", response=_flat_response,
                           note="every episode with an outcome reached the threshold")
    _flat_predict, _flat_summary = fit_recovery_share(
        DesignBuilder(_flat.episodes, _flat.spec), _flat)
    _expect(_flat_summary["degenerate"] is True and _flat_summary["available"] is False,
            "an outcome with no variation cannot be fitted and the summary says so")
    _expect(all(math.isnan(_flat_predict(*group_setting(_flat.spec, slug)))
                for slug in report_groups(_flat.spec)),
            "AND IT RETURNS NOTHING PRINTABLE RATHER THAN A CONSTANT. Four identical adjusted "
            "shares under a column headed adjusted read as a finding, and no renderer inspected "
            "the flag that said otherwise; a value that is not a number suppresses itself at "
            "both renderers under the rule they already apply to every other estimate")

    # ---- 13. the whole analysis, end to end ----------------------------------------------
    # Reduced draws and resamples so the check runs on a laptop; the LOCKED values are asserted
    # separately below, and `run_drd` records any departure from them as a printed deviation.
    fast = {"draws": 24, "resamples_primary": 6, "resamples_sensitivity": 2}
    level = {"level": "two_group", "groups": TWO_GROUP_SLUGS}
    result = analyze(panel, episodes, collapse=level, run_sensitivity=True, **fast)
    _expect(result["drd ok"], "the analysis completed on the synthetic cohort")
    _expect(set(result["debt"]) == {"estimand_display", "normalized_activity_display",
                                    "max_possible", "by_group", "contrasts",
                                    "unadjusted_contrasts", "unadjusted_model", "absolute_scale",
                                    "manski", "delta_shift", "model_fit"},
            "the debt block carries exactly the members the export contract names, plus the "
            "sentence that names the cap on the normalized-activity column, which is part of "
            "the quantity and therefore has to travel with it")
    _expect(isinstance(result["debt"]["estimand_display"], str)
            and result["debt"]["max_possible"] == WINDOW_LENGTH_DAYS,
            "the estimand sentence and the window bound cross as RAW values, which is what "
            "`07_export.py` wraps in a scalar node of its own")
    _expect(ESTIMATOR_DISPLAY == "model and integrate",
            "the estimator is named as what it is, and never as summing the observed days")
    _expect([g["slug"] for g in result["debt"]["by_group"]]
            == list(TWO_GROUP_SLUGS) + [ALL_GROUPS_SLUG],
            "the groups are the collapse level's groups, READ and not assumed, and the pooled "
            "row is last because the exporter reads the total by position")
    for entry in result["debt"]["by_group"]:
        _expect({"slug", "display_label", "true_n", "true_complete_windows", "unadjusted_debt",
                 "adjusted_debt", "thousand_steps_lost", "adjusted_mean_normalized_activity",
                 "share_reaching_80pct_baseline", "recovery_outcome_true_n",
                 "zero_debt_true_n"} == set(entry),
                "every group entry carries the whole of its row of Table 2, INCLUDING THE TWO "
                "DENOMINATORS THAT ARE NOT THE GROUP'S: the naive column's complete windows and "
                "the recovery column's episodes with an outcome")
        _expect(isinstance(entry["true_n"], int)
                and isinstance(entry["true_complete_windows"], int)
                and isinstance(entry["zero_debt_true_n"], int),
                "AND CARRIES IT AS TRUE INTEGERS, because the exporter has to ask "
                "`disclosable` of the true count before it may call `round20`")
        _expect(len(entry["unadjusted_debt"]) == 3 and len(entry["adjusted_debt"]) == 3,
                "a quantile crosses as (median, 25th, 75th) and an estimate as (est, lo, hi), "
                "which is what the exporter unpacks them as")
        _expect(entry["zero_debt_true_n"] <= entry["true_n"],
                "the count with zero debt is a numerator inside its own group")
        _expect(isinstance(entry["recovery_outcome_true_n"], int)
                and entry["recovery_outcome_true_n"] <= entry["true_n"],
                "and the recovery column carries the count it was actually FITTED on, a true "
                "integer inside its own group, so the exhibit can print the adjusted share "
                "against the denominator that produced it rather than against the group's")
        _expect(entry["true_complete_windows"] <= entry["true_n"],
                "the unadjusted column's own denominator never exceeds the group's, and it "
                "travels separately so it can be floor-tested on its own count")
    pooled = result["debt"]["by_group"][-1]
    _expect(pooled["recovery_outcome_true_n"]
            == sum(e["recovery_outcome_true_n"] for e in result["debt"]["by_group"][:-1]),
            "the recovery denominators partition the pooled one exactly, as every other count "
            "in this block does")
    _expect(pooled["slug"] == ALL_GROUPS_SLUG
            and pooled["true_n"] == sum(e["true_n"] for e in result["debt"]["by_group"][:-1]),
            "and the named groups partition the pooled row exactly, which is what the "
            "exporter's secondary suppression of the zero-debt counts rests on")
    primary_contrast = result["debt"]["contrasts"][PRIMARY_CONTRAST_SLUG]
    _expect(primary_contrast["is_primary"] and sum(
        1 for c in result["debt"]["contrasts"].values() if c["is_primary"]) == 1,
            "exactly one contrast is the primary")
    _expect(primary_contrast["estimable"]
            and all(np.isfinite(v) for v in primary_contrast["estimate"]),
            "and it is estimable on this cohort")
    _expect(isinstance(primary_contrast["p"], float)
            and not isinstance(primary_contrast["p"], bool),
            "a P value crosses as a bare float, so the exporter floors it for printing once")

    # ---- STROBE item 16(a), the unadjusted contrast beside the adjusted one ---------------
    plain_block = result["debt"]["unadjusted_contrasts"]
    plain_model = result["debt"]["unadjusted_model"]
    _expect(set(plain_block) == set(result["debt"]["contrasts"]),
            "EVERY contrast the module reports has an unadjusted twin, not only the primary: "
            "item 16(a) asks for the unadjusted estimate beside each adjusted one it meets")
    plain_primary = plain_block[PRIMARY_CONTRAST_SLUG]
    _expect(set(plain_primary) == set(primary_contrast),
            "and it carries the identical member set, so a consumer that can read one can read "
            "the other with no second reader")
    _expect(plain_primary["is_primary"] and sum(
        1 for c in plain_block.values() if c["is_primary"]) == 1,
            "exactly one unadjusted contrast is the primary one, matching the adjusted side")
    _expect(len(plain_primary["estimate"]) == 3 and plain_primary["estimable"]
            and all(np.isfinite(v) for v in plain_primary["estimate"]),
            "IT HAS ITS OWN INTERVAL: the clustered bootstrap refits the covariate-free model "
            "inside every resample, exactly as it refits the adjusted one")
    _expect(plain_primary["estimate"][1] <= plain_primary["estimate"][0]
            <= plain_primary["estimate"][2],
            "and the interval brackets its own point estimate")
    _expect(plain_primary["true_n_compared"] == primary_contrast["true_n_compared"],
            "IT HAS ITS OWN n, and on this variant it is the same two groups combined, which "
            "is a fact worth asserting rather than a coincidence to be assumed")
    _expect(plain_primary["estimate"][0] != primary_contrast["estimate"][0],
            "the covariates moved the answer, so the two contrasts are two numbers and the "
            "unadjusted one is not the adjusted one under another name")
    _expect(plain_model["prespecified"] is False,
            "IT IS DECLARED GUIDELINE-MANDATED AND NOT PRESPECIFIED, because the Methods have "
            "to say which and a boolean beside the number is the only form of that statement a "
            "consumer cannot lose in transcription")
    _expect("16(a)" in plain_model["mandate_display"]
            and "not prespecified" in plain_model["mandate_display"],
            "and the sentence beside it names the item that requires it and says in terms that "
            "the locked plan does not")
    _expect("covariate set removed" in plain_model["definition_display"]
            and "day of week" in plain_model["definition_display"]
            and "observation weights" in plain_model["definition_display"],
            "the definition says WHAT WAS REMOVED AND WHAT WAS NOT, so a reader is never left "
            "to guess which of the two habitual meanings of unadjusted is meant here")
    _expect(plain_model["rung_index"] == result["estimator"]["rung_index"]
            and plain_model["rung_matches_adjusted"] is True,
            "on this cohort the unadjusted fit reached the same rung of the family ladder, and "
            "the comparison is recorded rather than being arranged by forcing the rung")
    _expect(plain_model["true_bootstrap_attempted"] == fast["resamples_primary"]
            and plain_model["true_bootstrap_failed"] == 0,
            "and its resamples are counted against the same attempted total the adjusted "
            "interval is counted against")
    _expect(plain_model["not_estimable_reason"] is None
            and plain_model["instability_trigger"] is False,
            "a fit that returned an estimate carries no refusal reason and fires no trigger")
    # THE UNADJUSTED CONTRAST IS NOT THE UNADJUSTED COLUMN OF TABLE 2, and this is the confusion
    # the whole quantity exists to end.  Table 2's unadjusted column is an absolute LEVEL by
    # direct summation over complete windows, on its own denominator; differencing two of those
    # medians does not give this number and is not meant to.
    naive_gap = (result["debt"]["by_group"][0]["unadjusted_debt"][0]
                 - result["debt"]["by_group"][1]["unadjusted_debt"][0])
    _expect(abs(naive_gap - plain_primary["estimate"][0]) > FLOAT_TOLERANCE,
            "the unadjusted CONTRAST is a different quantity from the difference of Table 2's "
            "unadjusted median levels, which is why item 16(a) was not already satisfied")
    _expect(all(len(entry["estimate"]) == 3 and entry["true_n"] == entry["true_n_compared"]
                for entry in plain_block.values()),
            "every unadjusted contrast crosses as a raw triple with its own count, and nothing "
            "here is rounded or floor-tested, because the exporter is the boundary")

    _expect(result["diagnostics"]["manski brackets the point estimate"] is True,
            "the modelled contrast lies inside the assumption-free bounds")
    _expect(result["debt"]["manski"]["computed_on"] == "every eligible episode",
            "the bounds say what they were computed on, and it is not complete windows only")
    shift = result["debt"]["delta_shift"]
    _expect(shift["scale"] == "latent logit"
            and shift["applied_to"] == DELTA_REPORTED_APPLICATION,
            "the reported tipping point shifts the comparison group, which is the direction "
            "that works against the study hypothesis")
    _expect(shift["monotone"], "the shift curve is monotone, which is checked and not assumed")
    _expect(set(shift["applications"]) == set(DELTA_APPLICATIONS),
            "all three application patterns are computed and the grid carries them")
    _expect(shift["crossed_within_grid"] or shift["no_crossing_display"],
            "either a crossing is reported or the prespecified no-crossing sentence is")
    fit = result["debt"]["model_fit"]
    _expect(fit["monte_carlo_draws"] == fast["draws"],
            "the number of Monte Carlo draws is reported")
    _expect(fit["converged"], "the rung reached converged")
    _expect(isinstance(fit["true_n_persons"], int)
            and isinstance(fit["true_n_person_days"], int)
            and fit["true_n_persons"] == primary.n_units,
            "the fit's two counts cross as true integers under names that say so")
    _expect(set(result["sensitivity"]) == set(PLOTTED_SENSITIVITY_SLUGS),
            "THE SENSITIVITY BLOCK IS EXACTLY THE FOURTEEN PLOTTED ROWS, which is the set "
            "`local/verify.py` asserts equality against")
    _expect(set(result["supplementary"]) == set(SUPPLEMENTARY_SENSITIVITY_SLUGS),
            "and the ten supplementary rows are returned under their own key, so they cannot "
            "leak into that set by an accident of iteration order")
    ordered = sorted(result["sensitivity"].values(), key=lambda r: (r["order"], r["sub_order"]))
    _expect([r["display_label"] for r in ordered]
            == [row["display"] for row in PLOTTED_SENSITIVITY_ROWS],
            "and they sort back into the plan's own fixed order")
    for slug, row in result["sensitivity"].items():
        label = SENSITIVITY_LABELS[slug]
        _expect(row["display_label"] == label, f"the row prints the plan's label for {label}")
        _expect(row["axis"] in ("primary", "latent_logit_shift")
                and row["render"] in ("marker", "panel", "text"),
                "every row declares an axis and how it renders")
    _expect(result["sensitivity"]["delta_shift_tipping_point"]["render"] == "panel",
            "the tipping-point row renders as its own panel whether or not it crossed")
    _expect(result["sensitivity"]["delta_shift_tipping_point"].get("unit") == "dimensionless",
            "and it carries its own unit, because a renderer that took the default would put "
            "log odds on a scale of activity days lost")
    for slug, row in result["sensitivity"].items():
        _expect({"estimate", "p", "true_n", "estimable", "not_estimable_reason", "varies",
                 "direction_matches_primary"} <= set(row),
                f"the {slug} row carries every member `07_export.py` reads off it")
        _expect(isinstance(row["true_n"], int),
                "including its count, as the TRUE integer the exporter floor-tests")
        _expect(row["estimate"] is None or len(row["estimate"]) == 3,
                "and its estimate as a three-member triple or as nothing at all, never as a "
                "node the exporter would unpack into nine positional arguments")
    complete_row = result["sensitivity"]["complete_window_direct_regression"]
    _expect(complete_row["true_n"] <= primary.n_units,
            "the naive row's denominator is its own and never the analytic one")
    _expect(result["supplementary"]["junctions_mirrored"]["not_estimable_reason"]
            == "not_estimable_data_unavailable",
            "a row the derived build cannot support is PRINTED as not estimable rather than "
            "omitted, because a reader who counts the rows would learn which fell short")
    _expect(len(result["gaps"]) == 4 and all(gap["row"] in SUPPLEMENTARY_SENSITIVITY_SLUGS
                                             for gap in result["gaps"]),
            "and each such row names what the derived build would need")
    supplied = analyze(panel, episodes, collapse=level, run_sensitivity=True, **fast,
                       extras={"fusion non add on":
                               episodes["fusion"].to_numpy().astype(bool) & (
                                   np.arange(len(episodes)) % 3 != 0)})
    _expect(supplied["supplementary"]["fusion_status_non_add_on_only"]["estimable"],
            "and it becomes estimable the moment a caller supplies what it needs")

    # ---- 14. reproducibility --------------------------------------------------------------
    def canonical(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {str(k): canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
        if isinstance(value, (list, tuple)):
            return [canonical(v) for v in value]
        if isinstance(value, (np.floating, float)):
            return f"{float(value):.12g}"
        if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
            return int(value)
        if isinstance(value, (np.bool_, bool)):
            return bool(value)
        return str(value)

    first_run = analyze(panel, episodes, collapse=level, run_sensitivity=False, **fast)
    second_run = analyze(panel, episodes, collapse=level, run_sensitivity=False, **fast)
    _expect(canonical(first_run["debt"]) == canonical(second_run["debt"]),
            "TWO RUNS WITH THE SAME SEED PRODUCE IDENTICAL NUMBERS, everywhere in the debt block")
    _expect(canonical(first_run["estimator"]) == canonical(second_run["estimator"]),
            "including the rung reached and every trigger that fired on the way to it")
    _expect(SEED == 0 and BOOTSTRAP_PRIMARY == 1000 and BOOTSTRAP_SENSITIVITY == 500
            and MONTE_CARLO_DRAWS == 2000 and MONTE_CARLO_RECHECK_DRAWS == 4000,
            "the locked seeds and counts are the plan's own")
    _expect(DAY_KNOTS == (2, 6, 12, 21, 32) and DISPLAY_DAY_KNOTS == (2, 6, 12, 21, 35, 55, 80),
            "and so are the fixed knot positions, which are not placed at data quantiles")

    # ---- 15. the four-group level, and the levels that estimate nothing -------------------
    episodes4, panel4 = _synthetic_frames(22, four_group=True)
    four = analyze(panel4, episodes4, collapse={"level": "four_group",
                                                "groups": FOUR_GROUP_SLUGS},
                   r_runner=_r_runner_factory("converges"), run_sensitivity=True, draws=16,
                   resamples_primary=3, resamples_sensitivity=1, convergence_recheck=False)
    _expect([g["slug"] for g in four["debt"]["by_group"]]
            == list(FOUR_GROUP_SLUGS) + [ALL_GROUPS_SLUG],
            "four groups when the collapse ladder permits four, and the module reads that")
    _expect(len(four["debt"]["by_group"]) == 5,
            "FIVE ROWS, WHICH IS WHAT THE EXPORT CONTRACT READS: Table 2's footer resolves the "
            "share with zero debt out of `debt.by_group[4]` by position, so a by-group list "
            "one row short of the pooled total does not reach the exporter at all")
    _expect(set(four["debt"]["contrasts"]) == set(CONTRAST_SLUGS),
            "and all five contrasts of Figure 3 block 1 are estimated by standardization")
    _expect(set(four["debt"]["unadjusted_contrasts"]) == set(CONTRAST_SLUGS),
            "AND ALL FIVE HAVE AN UNADJUSTED TWIN, including the two region-specific ones and "
            "the interaction, because item 16(a) asks for every contrast reported and not only "
            "the primary")
    _expect(four["debt"]["unadjusted_model"]["rung_index"] is not None
            and isinstance(four["debt"]["unadjusted_model"]["rung_matches_adjusted"], bool),
            "and the rung the covariate-free fit reached is recorded at this level too, where "
            "the design carries the region interaction as well")
    _expect(len(four["debt"]["manski"]["by_group"]) == len(FOUR_GROUP_SLUGS) + 1,
            "with per-group bounds for each, and for the pooled row beside them")
    nothing = analyze(panel, episodes, collapse={"level": "no_estimand", "groups": ()})
    _expect(not nothing["drd ok"] and nothing["debt"] is None,
            "at the bottom of the collapse ladder no estimand is reported at all")
    _expect(nothing["halting"], "and the reason is returned rather than inferred")

    # ---- 15b. THE SEAM WITH THE EXPORTER, which neither module could check alone ----------
    #
    # This module's self-test asserted its own `RESULT_KEYS` and `07_export.py`'s exercised its
    # own `fixture_payload()`, built to its own shape.  The two never met, so the returned debt
    # block and the block the exporter reads drifted into different shapes and NOTHING WAS RED.
    # The check below feeds a real result to the real renderer and is the only thing in either
    # module that can fail on that drift.  `pipeline/tests/test_drd_export_bridge.py` runs the
    # same seam through `run_drd` under pytest; this one runs wherever this module runs, which
    # includes the perimeter, where pytest may not be installed at all.
    bridge = _export_bridge_check(four)

    # ---- 16. the report -------------------------------------------------------------------
    report = render_report(result)
    assert_house_prose(report)
    _ASSERTIONS += 1
    _expect(EM_DASH not in report and MINUS_SIGN not in report,
            "the rendered report carries neither banned dash")
    _expect(not _SNAKE_TOKEN.findall(report),
            "and no machine token, so no slug reaches a user-visible surface")
    printed_debt = report_debt(result["debt"])
    _expect(printed_debt["contrasts"][PRIMARY_CONTRAST_SLUG]["estimate"]["display"] in report,
            "the primary contrast prints from a node's own display string, built here from the "
            "raw triple rather than formatted a second time at the point of printing")
    flowed = re.sub(r"\s+", " ", report)
    _expect(re.sub(r"\s+", " ", result["debt"]["estimand_display"]) in flowed,
            "the report opens on the one-sentence definition of what is being estimated")
    for row in printed_debt["by_group"]:
        _expect(row["display_label"] in report, "every group prints under its label")
        _expect(row["n"]["display"] in report,
                "and beside its own denominator, which every table in this plan prints")
    _expect("own denominator" in flowed,
            "the report says in words that the naive column's denominator is its own")
    _expect(result["debt"]["model_fit"]["residual_correlation"] in report,
            "and names the residual structure the fit actually used")
    _expect(report.count("20 or fewer are suppressed") == 1,
            "and carries the disclosure sentence once, in the plan's own words")
    _expect(render_report(nothing).count("no estimand") >= 0
            and "PHASE 4" in render_report(nothing),
            "the halting report renders too, rather than raising on a missing block")

    # ---- 17. the runner, and every refusal it owes -----------------------------------------
    guards_frame = pd.DataFrame([{name: 0 for name in GUARD_SENTENCES}
                                 | {"n_panel_rows": int(len(panel)),
                                    "n_units": int(len(episodes))}])
    parameters_frame = pd.DataFrame([{"junction_map": "primary",
                                      "primary_wear_definition": "primary", "seed": SEED}])
    runtime = _FakeRuntime({"episodes": episodes, "panel": panel, "guards": guards_frame,
                            "parameters": parameters_frame}, gb=0.01)
    printed = io.StringIO()
    with redirect_stdout(printed):
        ran = run_drd(features={"features ok": True}, collapse=level,
                      q_guarded=runtime.q_guarded, dry_run_gb=runtime.dry_run_gb,
                      run_sensitivity=False, show_report=False, **fast)
    _expect(set(RESULT_KEYS) <= set(ran), "the runner returns every declared result key")
    _expect(ran["drd ok"] and ran["deviations"],
            "and records the reduced resample counts as a printed deviation from the locked "
            "values rather than passing them off as the plan's own")
    _expect(printed.getvalue().count("rows hidden by policy") == len(QUERY_KEYS),
            "every returned frame was shown through the shape-only printer, never as rows")
    assert_house_prose(ran["report"])
    _ASSERTIONS += 1
    _expect(ran["report"] and "PHASE 4" in ran["report"],
            "the runner renders its report whether or not it was asked to print it")
    _expect(len(runtime.calls) == len(QUERY_KEYS)
            and all(note.startswith("05 recovery debt") for _, _, note in runtime.calls),
            "every query went through the guarded path with a named cost-log entry")
    _expect(all(cap == PLANNED_MAX_GB[key] for key, (_, cap, note) in
                zip(QUERY_KEYS, runtime.calls)),
            "and each carried its own byte cap")

    _expect_raises(DrdAnalysisError,
                   lambda: run_drd(features={"features ok": False}, collapse=level,
                                   q_guarded=runtime.q_guarded, dry_run_gb=runtime.dry_run_gb,
                                   show_report=False),
                   "AN UNCERTIFIED FEATURE FRAME HALTS THE ANALYSIS. It is a stop condition and "
                   "never a warning")
    _expect_raises(DrdAnalysisError,
                   lambda: run_drd(features={"features ok": True},
                                   collapse={"level": "invented", "groups": ()},
                                   q_guarded=runtime.q_guarded, dry_run_gb=runtime.dry_run_gb,
                                   show_report=False),
                   "a collapse level outside the plan's four is refused")
    expensive = _FakeRuntime({"episodes": episodes, "panel": panel, "guards": guards_frame,
                              "parameters": parameters_frame}, gb=100.0)
    with redirect_stdout(io.StringIO()):
        _expect_raises(DrdBudgetExceeded,
                       lambda: run_drd(features={"features ok": True}, collapse=level,
                                       q_guarded=expensive.q_guarded,
                                       dry_run_gb=expensive.dry_run_gb, show_report=False),
                       "a priced total over the budget refuses the whole step, with nothing "
                       "executed and nothing billed")
    _expect(not expensive.calls, "and nothing reached the query path at all")
    _expect_raises(DrdAnalysisError,
                   lambda: run_drd(features={"features ok": True}, collapse=level,
                                   show_report=False),
                   "with no query path available the module refuses rather than finding its "
                   "own way to the interface")
    dirty_guards = guards_frame.copy()
    dirty_guards.loc[0, "n_zero_imputed_deficit"] = 4
    dirty_runtime = _FakeRuntime({"episodes": episodes, "panel": panel,
                                  "guards": dirty_guards, "parameters": parameters_frame})
    with redirect_stdout(io.StringIO()):
        _expect_raises(DrdAnalysisError,
                       lambda: run_drd(features={"features ok": True}, collapse=level,
                                       q_guarded=dirty_runtime.q_guarded,
                                       dry_run_gb=dirty_runtime.dry_run_gb, show_report=False),
                       "a panel carrying a zero-imputed deficit halts before anything is fitted")
    plan = cost_plan(build_sql(), _FakeRuntime({}, gb=0.05).dry_run_gb)
    _expect(plan["fits"] and not plan["over cap"],
            "the priced plan fits, and the per-query caps are the second guard")
    _expect(plan["total gb"] < DRD_BUDGET_GB,
            "the whole step reads only derived tables and costs small change")

    # ---- 18. the bootstrap's own machinery -------------------------------------------------
    index = rows_by_unit(primary)
    reference = rows_by_unit_reference(primary)
    _expect(all(np.array_equal(a, b) for a, b in zip(index, reference)),
            "the grouped row index agrees with the definition it is checked against")
    drawn = np.random.default_rng([SEED, 1]).integers(0, primary.n_units, size=primary.n_units)
    resampled = resample_variant(primary, drawn, index)
    _expect(resampled.n_units == primary.n_units,
            "a person-clustered resample draws whole participants, with replacement")
    _expect(resampled.n_days == sum(index[int(u)].size for u in drawn),
            "and carries all of each drawn participant's person-days")
    _expect(abs(bootstrap_pvalue([1.0, 2.0, 3.0, 4.0]) - 0.0) < FLOAT_TOLERANCE,
            "a resample distribution entirely on one side of zero gives a P value of zero "
            "before it is floored for printing")
    _expect(abs(bootstrap_pvalue([-1.0, 1.0]) - 1.0) < FLOAT_TOLERANCE,
            "and one split evenly gives one")
    low, high = percentile_interval([1.0, 2.0, 3.0, 4.0, 5.0])
    _expect(low <= 3.0 <= high, "the percentile interval contains the median of its own draws")
    nearly_all_failed = [1.0, 2.0, 3.0, 4.0, 5.0] + [float("nan")] * 495
    refused = percentile_interval(nearly_all_failed, attempted=500)
    _expect(not np.isfinite(refused[0]) and not np.isfinite(refused[1]),
            "AN INTERVAL COMPUTED FROM FIVE OF FIVE HUNDRED RESAMPLES IS REFUSED. Dropping the "
            "non-finite draws in silence is what let such a row come back estimable with an "
            "ordinary-looking 95% interval, and nothing downstream could tell it from an "
            "interval computed from five hundred")
    _expect(node_is_suppressed(estimate_node(3.0, *refused, "activity_days",
                                             contributing_n=340)),
            "and the node built from it carries no number, so the refusal reaches the export")
    enough = [float(v) for v in range(500)]
    _expect(all(np.isfinite(v) for v in percentile_interval(enough, attempted=500)),
            "while a bootstrap that finished gives its interval as before")
    minimum = int(math.ceil(BOOTSTRAP_MIN_FINITE_SHARE * 500))
    _expect(not np.isfinite(percentile_interval(enough[:minimum - 1], attempted=500)[0])
            and np.isfinite(percentile_interval(enough[:minimum], attempted=500)[0]),
            "and the minimum is the prespecified one, DERIVED FROM TRIGGER T4 rather than "
            "invented beside it: the plan tolerates a quarter of the resamples failing, so an "
            "interval standing on less than the other three quarters is refused")

    flaky_row = next(r for r in PLOTTED_SENSITIVITY_ROWS if r["slug"] == "pod_anchored_window")
    flaky_variant = build_plotted_variant("pod_anchored_window", primary)
    real_estimate_variant = estimate_variant
    attempts = {"n": 0}

    def _point_then_failures(*args: Any, **kwargs: Any) -> Mapping[str, Any]:
        attempts["n"] += 1
        if attempts["n"] > 1:                        # the point estimate stands, every
            raise RungFailure("T1", "this resample did not converge")   # resample fails
        return real_estimate_variant(*args, **kwargs)

    globals()["estimate_variant"] = _point_then_failures
    try:
        unstable = run_sensitivity_row(flaky_row, flaky_variant, resamples=4,
                                       point_rung_index=3, r_runner=None, draws=4,
                                       primary_estimate=1.0, min_rung=3)
    finally:
        globals()["estimate_variant"] = real_estimate_variant
    _expect(unstable["bootstrap"]["instability trigger"]
            and unstable["bootstrap"]["failure rate"] > BOOTSTRAP_FAILURE_SHARE_TRIGGER,
            "a sensitivity row whose resamples fail at the prespecified rate records the "
            "instability on the row")
    _expect(not unstable["estimable"] and unstable["estimate"] is None,
            "AND THE INSTABILITY CROSSES THE BOUNDARY. On the primary, trigger T4 descends the "
            "family ladder; a sensitivity row has no ladder of its own and none of the keys the "
            "exporter reads from a row carries a failure rate, so an unstable row that returned "
            "an ordinary interval would be plotted beside the stable rows with nothing to tell "
            "them apart")
    _expect(unstable["true_n"] == flaky_variant.n_units,
            "and it still says how many episodes it was attempted on")

    # ---- 19. the summary -------------------------------------------------------------------
    print("=" * 86)
    print("05_analysis_drd.py SELF-TEST: PASS")
    print("=" * 86)
    print(f"  assertions executed        : {_ASSERTIONS}")
    print(f"  queries built              : {len(QUERY_KEYS)}")
    print( "  every emitted query        : carries the derived-dataset placeholder ONLY, quotes")
    print( "                               no hardcoded project or dataset, contains no")
    print( "                               data-definition statement and no random draw, and")
    print( "                               declares result columns it actually aliases")
    print( "  identifiers and dates      : none selected at all. The queries emit a dense")
    print( "                               surrogate index in place of the person and episode")
    print( "                               keys and a weekday integer in place of a date")
    print(f"  aggregate budget           : {DRD_BUDGET_GB:,.1f} GiB, about "
          f"${DRD_BUDGET_GB / 1024 * USD_PER_TIB:,.2f}, priced before anything executes")
    print( "  the estimator              : MODEL AND INTEGRATE. The daily deficit is modelled")
    print( "                               directly and the fitted curve is integrated over the")
    print( "                               whole window, including the days an episode did not")
    print( "                               contribute")
    print( "  convexity trap             : pinned twice. The deficit function is applied to the")
    print( "                               response and never to a fitted mean, demonstrated on a")
    print( "                               case where Jensen's inequality moves the answer by a")
    print( "                               fifth of the daily scale and again on the fixture")
    print( "  random effects             : marginalized by Monte Carlo with common random")
    print( "                               numbers, never set to zero, and the two are pinned")
    print( "                               apart on a nonlinear link")
    print( "  null is not zero           : pinned in both directions. A null day never becomes a")
    print( "                               zero deficit, and a deficit sitting on an unobserved")
    print( "                               day halts the estimator before anything is fitted")
    print(f"  the family ladder          : {len(ESTIMATOR_RUNGS)} rungs, every descent trigger")
    print( "                               exercised, the rung reached recorded, and a trigger a")
    print( "                               rung does not carry refused as a stop condition")
    print( "  Manski bounds              : bracket every completion of the window by")
    print( "                               construction, checked against 200 random completions")
    print( "  tipping point              : monotone, and the reported crossing is real: the grid")
    print( "                               point before it is strictly positive")
    print(f"  sensitivity rows           : {len(PLOTTED_SENSITIVITY_SLUGS)} plotted in the plan's "
          f"fixed order, {len(SUPPLEMENTARY_SENSITIVITY_SLUGS)} supplementary,")
    print( "                               returned under separate keys and disjoint by")
    print( "                               assertion")
    print(f"  gaps reported, not patched : {len(DAG_GAPS)}, each naming what the build would need")
    print( "  unadjusted contrast        : STROBE item 16(a). Every contrast is returned twice,")
    print( "                               adjusted and with the covariate set removed, each")
    print( "                               with its own clustered interval, its own n and the")
    print( "                               rung its own fit reached. It is declared")
    print( "                               guideline-mandated and never prespecified")
    print( "  reproducibility            : two runs with the same seed produce identical numbers")
    for line in bridge["notes"]:
        print(line)
    print( "  cloud access required      : none")


if __name__ == "__main__":
    # THE ONLY FLOATING-POINT SUPPRESSION LEFT IN THIS MODULE, and it is at the process's own
    # top level rather than inside a function a caller can import.  Two rungs of the estimator
    # ladder overflow on their way to a converged step and the noise would bury the self-test's
    # own output; `np.errstate` restores the caller's error state on the way out, so importing
    # this module and running its self-test leaves the importer's diagnostics exactly as they
    # were.  `np.seterr` here would not, which is the defect this scope exists to not repeat.
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        _run_self_test()
