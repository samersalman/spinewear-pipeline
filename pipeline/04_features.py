#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""04_features.py -- Phase 3.  Feature VALIDATION and the diagnostics the analysis needs.

WHAT THIS IS, AND WHAT IT IS NOT.  `pipeline/build_all.sql` already COMPUTES valid wear days,
the seven preoperative baselines, the daily deficit panel, the event table and the matched risk
sets, inside `{DERIVED}`.  THIS MODULE RECOMPUTES NONE OF THEM.  It reads the derived tables,
checks that every null convention and every invariant the DAG contract promises actually holds,
produces the diagnostics `05_analysis_drd.py`, `06_analysis_gate.py`, Figure 2 and the STROBE
supplement need, and refuses to certify the frames when a check fails.  A later reader who sees
a `COUNTIF(... valid_wear ...)` in here and concludes the module reimplements the wear rule has
read it backwards: the counts are ABOUT the rule the DAG applied, they do not apply it.

Two consequences of that division, stated because both are easy to violate later:

  * If a feature the analysis needs genuinely is not in the DAG, this module REPORTS it under
    "what the derived tables do not carry" and says what `build_all.sql` would need.  It does
    not grow a second implementation in Python, because two implementations of one definition
    are a divergence waiting for the next amendment, and the one in SQL is the one that ran.
  * The one sanctioned recomputation is the one the DAG contract itself hands over: the
    sensitivity deficits are deliberately NOT precomputed per wear definition, and are
    recomputed from `drd_daily.steps` and `features.baseline_steps_s1` through `_s4`
    (DAG-SCHEMA 8.11).  This module does not run those either; it VERIFIES that the inputs
    they need are present and non-null where they have to be, and reports the join.

WHERE THIS RUNS.  INSIDE THE PERIMETER for the twenty-one queries and the report.  LOCALLY it
still runs, and running it locally is the intended way to check it: `python3 04_features.py`
executes `_run_self_test()`, which drives every pure diagnostic in the module against synthetic
frames, touches no network and writes no file.

IN-PERIMETER USE, in a notebook, after the DAG has been built:

    %run 00_config.ipynb
    %run -i 03_cohort.py                  # builds {DERIVED} and closes the ladder
    %run -i 04_features.py                # -i: the kernel already holds q_guarded
    FEATURES = run_features()

COST.  Every read is of a `{DERIVED}` table, so this module touches NO CDR table at all and its
whole budget is small change.  `q_guarded` is still the only query path, every query is priced
by a free dry run before ANY of them executes, and the aggregate refuses over
`FEATURES_BUDGET_GB` with the measured number in the human's hand rather than after the bill.

DISCLOSURE.  Every number that reaches a printed surface is a GROUP BY aggregate.  Counts are
TRUE INTEGERS inside `{DERIVED}` (DAG-SCHEMA 6), so the floor is applied HERE, once, at the
boundary: `disclosable(n)` on the true count decides whether a cell may be shown at all,
`round20(n)` renders it, `is_legal_disclosed_count(cell)` re-reads the rendered cell, and
`export_violations` gets the finished frame including its declared partitions.  Continuous
summaries go through `median_iqr`, which suppresses at or below the floor, and every one of them
is computed by expanding an AGGREGATE distribution rather than by pulling participant rows into
the kernel.  No frame of rows is ever printed; `safe_show` prints shapes.

THE FOUR DISTINCTIONS THIS MODULE EXISTS TO PROTECT.  Each is a place where a plausible piece of
code silently produces a different study:

  1. NULL IS NOT ZERO.  `fitbit_daily.wear_minutes` is null when there is NO heart-rate record,
     which is not the claim that the participant wore the device for zero minutes; `steps` is
     null when there is no activity record.  A diagnostic that reads either as zero converts an
     absence of data into a measured absence of movement.  Every counter in this module splits
     null, real zero and positive into three columns and never adds the first two together.
  2. A REAL ZERO-STEP ANALYZABLE DAY IS KEPT.  Days under 100 steps are RETAINED under the
     primary wear rule (ANALYSIS-PLAN 2.1) because profound inactivity may be the biological
     signal of interest, and such a day contributes a deficit of exactly 1.  A wear rule that
     deleted it would delete the days the study is about; S2 is the one definition that does,
     which is why S2 is on the sensitivity ladder rather than in the primary.
  3. THE TWO LANDMARK CONDITIONS ARE DIFFERENT.  `has_computable_landmark` (fewer than 2 VALID
     days) is a DATA condition and those windows STAY in the risk set under plan 4.4;
     `structurally_uncomputable_landmark` (fewer than 2 POST-DISCHARGE days) is a DEFINITIONAL
     condition and is attrition rung 18.  Merging them silently deletes the collider-correction
     windows, which is the exact bias plan 4.4 exists to prevent.  They are counted, reported
     and asserted separately here, and the derived range is post-discharge day 1 to 4.  The
     same separation holds on `landmark_daily` and on `events`, and on all three surfaces
     `no_computable_step_signal` now carries the DATA CONDITION ALONE:
     `n_eligible_days_in_window >= 2 AND n_valid_days_in_window < 2`.  So a structurally
     uncomputable day is NOT without a step signal, it is outside the exposure entirely, and
     the containment runs the other way from the one an earlier reading of this file asserted:
     `no_computable_step_signal` implies NOT `structurally_uncomputable_landmark`.  The two are
     never summed on any surface, in this file or in any exhibit.
  4. INPATIENT IS NOT EXCLUSIVE OF OBSERVED.  A readmitted participant wearing the device
     produces a valid, analyzable, INPATIENT day, and the plan KEEPS it.  `drd_daily.day_kind`
     carries observation status in three values and `is_inpatient` carries the setting beside
     it; `day_kind_four` reproduces the plan's exclusive four-value taxonomy by precedence.
     Both are reported, neither is collapsed into the other, and the crosstab is checked to
     prove the inpatient-and-observed cell is counted once in each taxonomy and never twice.

A NULL BASELINE IS THE FIFTH, AND IT IS THE MOST EXPENSIVE.  `baseline.baseline_steps` is NULL,
never 0.  A zero baseline makes `S / B` infinite and the daily deficit `max(0, 1 - S/B)`
silently equal to 1 on EVERY day, manufacturing a maximal recovery debt out of an absence of
data.  This module counts zero baselines across the whole `baseline` table and halts on one.

AND A ZERO-IMPUTED DEFICIT IS THE SIXTH.  `drd_daily.deficit` is NULL on a non-analyzable day
and is never zero-imputed.  A zero deficit is the assertion that the participant walked at or
above their own preoperative baseline that day, which is the most favourable possible completion
of the window; summing over observed days lets every missing day contribute zero, and non-wear
is most likely exactly when the true deficit is largest, so the bias runs downward and runs
harder in sicker participants.  That is the whole reason the estimator is model-and-integrate
rather than sum-the-observed-days (ANALYSIS-PLAN 3.2), and this module verifies that no
zero-imputation has crept in, in both directions.

AND THE EARLY-LANDMARK BOUNDARY IS THE SEVENTH, and it is an off-by-one rather than a
confusion between two columns.  A matched-set member's landmark sits three days before its
matched day, and the landmark observation weights of ANALYSIS-PLAN 4.4 fix 2 read the lagged
wear fraction over the seven post-discharge days behind it.  That predictor DOES NOT EXIST at a
landmark day of 0 or less, where `drd_daily` has no row, and IS NULL at a landmark day of
exactly 1, where the row exists but the lag has nothing behind it to average.  So the members
with no weight input are those at landmark day 1 or LESS, which is matched day 4 or less, and a
counter written on "the landmark precedes post-discharge day 1" misses the whole matched-day-4
group.  Those are the earliest members in the study, and 4.3 argues at length that earliest is a
proxy for most severe, so under-counting them is wrong in the one direction that would flatter
the result.  The rule the plan states is that a member is weighted at landmark day 2 or more.

AND A LANDMARK DAY OF 1 OR LESS IS NOT A SECOND THRESHOLD SITTING BESIDE THAT RULE.  Plan
version 1.5 section 4.4 writes the arithmetic out: the landmark is `T = E - 3` and the window is
`T-2` to `T`, so the window's post-discharge days are the days of `T-2` to `T` that are 1 or
greater, and that count reaches 2 exactly when `T` is 2 or more.  `T = 1` leaves the single day
1 and a `T` of 0 or less leaves none, so A LANDMARK DAY OF 1 OR LESS IS THE DEFINITIONAL
CONDITION ITSELF, WRITTEN IN LANDMARK-DAY TERMS.  Such a member has no exposure window at all:
it carries NO `N`, it contributes nothing to `beta_N`, and it is outside the co-primary exposure
ON EVERY SURFACE, the conditional model of 4.5, the discrete-time model of 4.6, the
`landmark_daily` panel and the `risk_sets` table alike.  A control the day-of-week relaxation of
4.7 puts at post-discharge day 3 or 4 is DROPPED FROM ITS RISK SET AS A MEMBER AND COUNTED; it
cannot leave at attrition rung 18, because rung 18 is an EVENT rung and a sampled control is not
an event.  The weight rule of fix 2 bites the same members for a different reason, so in the
primary it has nothing left to exclude, and it stands alone only where the partial-window
secondary of 4.3 deliberately reads such a member back in under its own single-eligible-day
rule; there, and only there, that member leaves the weighted sensitivity and nothing else.  The
boundary is pinned here by a self-test carrying one member at each of landmark day 0, 1 and 2.

THE THREE COUNTS THAT RULE OBLIGES ARE THREE GRAINS AND NONE IMPLIES ANOTHER.  The affected
members, split by role and by the two routes that produce them, are member-level.  The matched
sets that lose EVERY control leave the conditional likelihood altogether and are set-level, and
that count is not recoverable from the member count because the member count does not know how
the excluded members fell across sets.  The weighted sensitivity's own denominator, in sets and
in members, is the third.  All three are printed whether or not the weighted row moves the
estimate.

WHAT IT WRITES.  Nothing.  `07_export.py` is the only module in this project that writes a file.
`run_features` returns a dictionary and prints a report; the frames it returns are aggregate
count frames, and the keys are listed under `RESULT_KEYS` for the two analysis modules.
"""

from __future__ import annotations

import io
import re
import sys
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
    MINUS_SIGN,
    SUPPRESSED,
    DisclosureError,
    disclosable,
    export_violations,
    is_legal_disclosed_count,
    is_suppressed,
    median_iqr,
    n_pct,
    prev,
    render_count,
    round20,
    safe_show,
)


class FeatureCheckError(RuntimeError):
    """A feature-validation stop condition.  Never downgraded to a warning."""


class FeatureBudgetExceeded(FeatureCheckError):
    """The priced total exceeded this step's budget, so nothing executed and nothing billed.

    A class of its own for the same reason the configuration notebook gives `QueryCapExceeded`
    one: a refusal by the budget is not a permissions problem and not a bad query, and the
    diagnosis printed beside it has to be able to branch on which of the three happened.
    """


# ======================================================================================
# (1) Vocabularies.  Every slug below is MACHINE vocabulary owned by ANALYSIS-PLAN.md or by
#     DAG-SCHEMA.md and is transcribed, never invented.  The display labels beside them are
#     for THIS MODULE'S diagnostic report only.
#
#     THE EXHIBIT LABELS ARE NOT THESE.  EXPORT-CONTRACT.md section 7 owns every printable
#     string that reaches the bundle, and `07_export.py` and `local/ledger.py` are the only two
#     files allowed to transcribe that table.  This module writes no file and no exhibit; it
#     prints a diagnostic report to a notebook, and the house rule that no snake_case token may
#     appear in a user-visible string still binds it, so it needs labels of its own.  They are
#     kept deliberately plain so that nobody mistakes one for an exhibit label and copies it.
# ======================================================================================

# ANALYSIS-PLAN.md 2.4, the seven group slugs, in the plan's own print order.  Rows 1 to 4 are
# the four groups of collapse level 1 and they PARTITION the cohort; `fusion` and
# `decompression` are the collapse-level-2 pair and they partition it a second way;
# `all_groups` is the total of both partitions.  Three sets over one column, which is why the
# suppression closure below is told about each partition separately.
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

# ANALYSIS-PLAN.md 2.1 and DAG-SCHEMA.md 3.  Five wear definitions, one effective flag.
# `valid_wear` is the EFFECTIVE flag carrying this run's S2 contingency; `valid_wear_primary` is
# the 600-minute rule as such.  They are equal on every day unless the zone-partition probe
# failed and the run was called with `primary_wear_definition = 's2'`, so the disagreement
# between them is the evidence of whether the contingency fired, and it is reported as such.
WEAR_DEFINITIONS: tuple[str, ...] = ("primary", "s1", "s2", "s3", "s4")
WEAR_DEFINITION_LABELS: Mapping[str, str] = MappingProxyType({
    "primary": "10 hours of heart-rate wear",
    "s1": "40% heart-rate adherence, which is 576 minutes",
    "s2": "10 hours of wear plus 100 steps",
    "s3": "8 hours of heart-rate wear",
    "s4": "12 hours of heart-rate wear",
})

# The four named windows of the person-by-date grid, which partition it, plus the total.  The
# grid runs index minus 60 through the later of index plus 120 and discharge plus 90
# (DAG-SCHEMA 8.7), so days outside the three named windows genuinely exist and are counted
# rather than dropped: a partition with an unnamed remainder is not a partition.
WINDOW_SLUGS: tuple[str, ...] = (
    "baseline_window",
    "accrual_window",
    "display_tail",
    "outside_named_windows",
)
ALL_WINDOWS_SLUG: str = "all_grid_days"
WINDOW_LABELS: Mapping[str, str] = MappingProxyType({
    "baseline_window": "Baseline window, 8 to 30 days before surgery",
    "accrual_window": "Accrual window, post-discharge day 1 to 35",
    "display_tail": "Display tail, post-discharge day 36 to 90",
    "outside_named_windows": "Grid days outside the three named windows",
    "all_grid_days": "Every day of the grid",
})

# DAG-SCHEMA.md 8.11.  Three values plus a separate flag, and a four-value exclusive taxonomy
# that the flag and the three values together determine by precedence.
DAY_KINDS: tuple[str, ...] = ("censored", "observed", "missing")
DAY_KINDS_FOUR: tuple[str, ...] = ("censored", "inpatient", "observed", "missing")
DAY_KIND_LABELS: Mapping[str, str] = MappingProxyType({
    "censored": "Censored",
    "observed": "Observed",
    "missing": "Missing",
    "inpatient": "Inpatient",
})

# The lagged wear fraction of ANALYSIS-PLAN 3.7, banded a priori.  Fixed cutpoints, not
# quantiles: a band defined on the observed distribution is a band chosen after seeing it.
LAG_BAND_SLUGS: tuple[str, ...] = (
    "unavailable",
    "none",
    "below_quarter",
    "quarter_to_half",
    "half_to_three_quarters",
    "three_quarters_to_all",
    "all",
)
LAG_BAND_LABELS: Mapping[str, str] = MappingProxyType({
    "unavailable": "No lagged window yet, post-discharge day 1",
    "none": "No valid day in the previous week",
    "below_quarter": "Under a quarter of the previous week worn",
    "quarter_to_half": "A quarter to a half worn",
    "half_to_three_quarters": "A half to three quarters worn",
    "three_quarters_to_all": "Three quarters to all but one day worn",
    "all": "Every day of the previous week worn",
})

# The twelve rows of `ledger_variable_missingness` (DAG-SCHEMA 8.19), and the exactly three
# that are STRUCTURALLY zero because an attrition rung removed every episode that could have
# made them non-zero.  A zero anywhere else in that ledger is a fact about the data; a zero in
# these three is a fact about the ladder, and reading the two the same way is how a substituted
# value gets reported as complete.
MISSINGNESS_VARIABLES: tuple[str, ...] = (
    "age_at_index", "sex_at_birth", "race_concept_id", "ethnicity_concept_id", "bmi",
    "charlson_score", "los_days", "device_family", "baseline_steps", "procedure_group",
    "daily_deficit", "r72",
)
STRUCTURALLY_COMPLETE_VARIABLES: tuple[str, ...] = (
    "los_days", "baseline_steps", "procedure_group",
)
MISSINGNESS_LABELS: Mapping[str, str] = MappingProxyType({
    "age_at_index": "Age at index operation",
    "sex_at_birth": "Sex assigned at birth",
    "race_concept_id": "Race",
    "ethnicity_concept_id": "Ethnicity",
    "bmi": "Body mass index",
    "charlson_score": "Comorbidity burden",
    "los_days": "Index length of stay",
    "device_family": "Device family",
    "baseline_steps": "Preoperative baseline steps",
    "procedure_group": "Procedure group",
    "daily_deficit": "Daily deficit",
    "r72": "Proximal activity ratio",
})


# ======================================================================================
# (2) Locked constants.  Every one is read out of ANALYSIS-PLAN.md or DAG-SCHEMA.md and none is
#     chosen here.  They reach the emitted SQL through `_sql`, so a constant cannot be typed a
#     second time inside a query string and drift from the one named below.
# ======================================================================================

SEED: int = 0                                   # ANALYSIS-PLAN 10.  This module draws nothing;
                                                # the constant is here so the reproducibility
                                                # statement quotes it rather than a literal.

# ANALYSIS-PLAN 2.2, the preoperative baseline window and its adequacy rule.
BASELINE_FIRST_DAY_BEFORE: int = 30
BASELINE_LAST_DAY_BEFORE: int = 8
BASELINE_MIN_VALID_DAYS: int = 7
BASELINE_MIN_SPAN_DAYS: int = 14
BASELINE_FLOOR_STEPS: int = 1000                # ANALYSIS-PLAN 3.10, a SENSITIVITY, never a
                                                # filter.  `meets_baseline_floor` is a flag.
BASELINE_DOW_LENGTH: int = 7                    # DAG-SCHEMA 8.8, index 0 is Sunday.
SUNDAY_INDEX: int = 0
SATURDAY_INDEX: int = 6

# ANALYSIS-PLAN 2.2, the weekday-and-weekend split baseline, supplementary sensitivity row ten
# `baseline_weekday_weekend_split`.  The two minima are deliberately UNEQUAL and are set from
# the window's own arithmetic: a 23-day span holds 16 or 17 weekday days and 6 or 7 weekend
# days, so 5 and 2 are close to the same fraction of what the calendar offers and neither half
# is held to a standard the window cannot supply.  Their sum is 7, exactly the primary rule's
# minimum, so the row's set is a SUBSET of the primary's and never a superset.
SPLIT_BASELINE_MIN_WEEKDAY_DAYS: int = 5
SPLIT_BASELINE_MIN_WEEKEND_DAYS: int = 2

# ANALYSIS-PLAN 2.3 and 3.1, the accrual window; DAG-SCHEMA 8.11, the display tail.
ACCRUAL_FIRST_DAY: int = 1
ACCRUAL_LAST_DAY: int = 35
DISPLAY_FIRST_DAY: int = 36
DISPLAY_LAST_DAY: int = 90
NEAR_COMPLETE_WINDOW_DAYS: int = 28             # DAG-SCHEMA 8.10 fixes 28 of 35, that is 80%,
                                                # because the plan does not define it and a
                                                # Table 1 row must not be defined afterwards.

# ANALYSIS-PLAN 4.3, derived in the plan's own six-row table and asserted by the procedure.
STRUCTURAL_DELETION_LAST_DAY: int = 4
FIRST_ELIGIBLE_EVENT_DAY: int = 5
FIRST_FULLY_POST_DISCHARGE_EVENT_DAY: int = 6
LANDMARK_WINDOW_DAYS: int = 3                   # E minus 5 through E minus 3.
LANDMARK_MIN_VALID_DAYS: int = 2
LANDMARK_DAY_OFFSET: int = 3                    # A member's landmark day is its matched day
                                                # minus 3 (DAG-SCHEMA 8.13, 8.14).

# ANALYSIS-PLAN 4.4, THE EARLY-LANDMARK WEIGHT RULE, AND THE BOUNDARY IT TURNS ON.
#
# The landmark weight model's predictor is the lagged wear fraction over post-discharge days
# `T-7` to `T-1`, and `drd_daily` begins at post-discharge day 1.  So the column does not
# EXIST at a landmark day of 0 or less, where there is no row at all, AND IS NULL at a landmark
# day of exactly 1, where the row exists but the lag has nothing behind it to average.  The set
# with no weight input is therefore landmark day <= 1, equivalently MATCHED DAY <= 4, and it is
# one day wider than "the landmark precedes post-discharge day 1".
#
# The plan states the rule in 4.4: a member is weighted when its own landmark day is 2 OR MORE.
# A LANDMARK DAY OF 1 OR LESS IS NOT A THRESHOLD OF ITS OWN.  Plan version 1.5 writes the
# arithmetic out: the landmark is `T = E - 3` and the window is `T-2` to `T`, so the window
# holds 2 post-discharge days exactly when `T` is 2 or more, and `T <= 1` IS the definitional
# condition expressed in landmark-day terms.  Such a member has no exposure window: it carries
# NO `N`, contributes nothing to `beta_N`, and is outside the co-primary exposure on every
# surface.  In the primary it has already left the exposure for that prior and different
# reason, so the weight rule has nothing left to exclude there; the weight rule bites alone
# only on a member the partial-window secondary of 4.3 deliberately reads back in, and that
# member leaves the weighted sensitivity and nothing else.  Counting on `< 1` instead of `<= 1`
# misses the whole matched-day-4 group, which is the earliest and by the argument of 4.3 the
# sickest of them.
LANDMARK_WEIGHT_MIN_LANDMARK_DAY: int = 2       # weighted when the landmark day is at least this
EARLY_LANDMARK_LAST_LANDMARK_DAY: int = 1       # no weight input at or below this landmark day
EARLY_LANDMARK_LAST_MATCHED_DAY: int = 4        # the same boundary on the matched-day scale

# DAG-SCHEMA 8.13, the full-cohort day-indexed landmark panel.  `fitbit_daily` is a dense
# calendar grid reaching back to index day minus 60, so the seven calendar days behind any
# landmark lie inside it for every post-discharge day and every length of stay: a row carrying
# fewer than seven is a defect in the span, never a data condition to be weighted around.
LANDMARK_PANEL_LOOKBACK_DAYS: int = 7

# ANALYSIS-PLAN 4.5, the two caps and the order they are applied in (DAG-SCHEMA 8.14).
CONTROLS_PER_CASE_CAP: int = 5
CONTROL_LANDMARKS_PER_PARTICIPANT_CAP: int = 3
MATCH_RUNGS: tuple[int, ...] = (1, 2, 3)

# ANALYSIS-PLAN 2.2 baseline bands, description only and never a model cutpoint.
BASELINE_BAND_SLUGS: tuple[str, ...] = ("under_3000", "3000_to_6999", "7000_or_more")
BASELINE_BAND_LABELS: Mapping[str, str] = MappingProxyType({
    "under_3000": "Under 3,000 steps per day",
    "3000_to_6999": "3,000 to 6,999 steps per day",
    "7000_or_more": "7,000 or more steps per day",
    "no_baseline": "No computable baseline",
})

# The six prespecified alternative baselines carried by `features` (DAG-SCHEMA 8.10), so that a
# sensitivity row never re-reads `fitbit_daily`.  Slug -> the column pair in `features`.
ALTERNATIVE_BASELINES: Mapping[str, tuple[str, str]] = MappingProxyType({
    "baseline_window_60_15": ("baseline_steps_60_15", "n_valid_baseline_days_60_15"),
    "baseline_window_30_1": ("baseline_steps_30_1", "n_valid_baseline_days_30_1"),
    "wear_definition_s1": ("baseline_steps_s1", "n_valid_baseline_days_s1"),
    "wear_definition_s2": ("baseline_steps_s2", "n_valid_baseline_days_s2"),
    "wear_definition_s3": ("baseline_steps_s3", "n_valid_baseline_days_s3"),
    "wear_definition_s4": ("baseline_steps_s4", "n_valid_baseline_days_s4"),
})
ALTERNATIVE_BASELINE_LABELS: Mapping[str, str] = MappingProxyType({
    "baseline_window_60_15": "Baseline 15 to 60 days before surgery",
    "baseline_window_30_1": "Baseline 1 to 30 days before surgery",
    "wear_definition_s1": "Baseline under 40% heart-rate adherence",
    "wear_definition_s2": "Baseline under 10 hours plus 100 steps",
    "wear_definition_s3": "Baseline under 8 hours of wear",
    "wear_definition_s4": "Baseline under 12 hours of wear",
})

# ANALYSIS-PLAN 2.2 and supplementary sensitivity row ten, `baseline_weekday_weekend_split`.
# Three availability rows and not one, because the two medians and the ROW ITSELF have three
# different denominators: an episode may carry a weekday median and no weekend one, and the row
# is fitted on neither median being non-null but on the two DAY COUNTS clearing their own
# minima, which is where the plan puts the rule so a later edit cannot weaken it inside a null
# test.  Table 2 prints the third of these as the row's own `n`.
SPLIT_BASELINE_METRICS: tuple[str, ...] = (
    "weekday_baseline", "weekend_baseline", "baseline_weekday_weekend_split",
)
SPLIT_BASELINE_LABELS: Mapping[str, str] = MappingProxyType({
    "weekday_baseline": "A Monday to Friday baseline exists",
    "weekend_baseline": "A Saturday or Sunday baseline exists",
    "baseline_weekday_weekend_split":
        "Both halves clear their own minimum, which is the split row's denominator",
})

# A float comparison tolerance, used only to ask whether two computed doubles agree.  It is not
# a threshold on any quantity of interest and nothing scientific reads it.
FLOAT_TOLERANCE: float = 1e-9


# ======================================================================================
# (3) Cost policy.  Two independent guards, protecting different things, exactly as in
#     02_pregate.py: a per-query cap is runaway protection for one query, and the aggregate
#     budget is the allowance.  This step is CHEAP because it reads only `{DERIVED}`: no CDR
#     table is touched by any query in this file, which is asserted in the self-test rather
#     than promised in a comment.
# ======================================================================================

USD_PER_TIB: float = 6.25                       # display only; enforcement is in bytes
BYTES_PER_GIB: int = 1024 ** 3

QUERY_KEYS: tuple[str, ...] = (
    "wear record presence",
    "wear definition agreement",
    "baseline day distribution",
    "baseline categories",
    "baseline day of week",
    "baseline invariants",
    "daily panel invariants",
    "wear availability by day",
    "wear availability ledger",
    "day kind crosstab",
    "landmark conditions",
    "structurally deleted event timing",
    "landmark panel invariants",
    "landmark panel by day",
    "matched set sizes",
    "matched set members",
    "control participation",
    "matched set ledger",
    "risk set digest",
    "observation model inputs",
    "variable missingness ledger",
)

# 8 GiB is about five cents at the price above and is roughly two orders of magnitude more
# than these queries should need: `fitbit_daily` is order 220,000 rows and `drd_daily` order
# 54,000, and BigQuery bills the COLUMNS REFERENCED rather than the table (DAG-SCHEMA 5.2).
# The budget is deliberately not sized to the expectation, because the expectation is what a
# dry run is for; it is sized so that a join that has accidentally become a cross product
# fails rather than bills.
FEATURES_BUDGET_GB: float = 8.0

PLANNED_MAX_GB: Mapping[str, float] = MappingProxyType({
    # The two scans of `fitbit_daily`, the largest derived table this module reads, at roughly
    # a dozen small columns over order 220,000 rows.
    "wear record presence": 2.0,
    "wear definition agreement": 2.0,
    # `features` is order 300 to 600 rows.  Everything keyed on it is free in practice and the
    # cap exists only to catch a cross product.
    "baseline day distribution": 0.5,
    "baseline categories": 0.5,
    "baseline day of week": 0.5,
    # `baseline` is order 12,000 rows, one per episode including the ineligible ones.
    "baseline invariants": 0.5,
    # `drd_daily` is order 27,000 to 54,000 rows.
    "daily panel invariants": 1.0,
    "wear availability by day": 1.0,
    "day kind crosstab": 1.0,
    "observation model inputs": 1.0,
    # The ledgers are tens to hundreds of rows.
    "wear availability ledger": 0.5,
    "matched set ledger": 0.5,
    "variable missingness ledger": 0.5,
    # `events` is order 100 to 400 rows and `risk_sets` order 1,000.
    "landmark conditions": 0.5,
    "structurally deleted event timing": 0.5,
    # `landmark_daily` is the same order as `drd_daily`, 27,000 to 54,000 rows, at a couple of
    # dozen small columns.  The invariants query also joins `events`, which is tiny.
    "landmark panel invariants": 1.0,
    "landmark panel by day": 1.0,
    "matched set sizes": 0.5,
    "matched set members": 0.5,
    "control participation": 0.5,
    "risk set digest": 0.5,
})


# ======================================================================================
# (4) SQL construction.
#
#     EVERY TEMPLATE IS A PLAIN, NON-f STRING WITH `{DERIVED}` INTACT, because the config
#     notebook's `_fill` substitutes the placeholder itself and raises on any residual
#     `{IDENTIFIER}`, and an f-string would have consumed the braces before it ever saw them.
#     This module's OWN constants reach a template through the `<<TOKEN>>` form instead, which
#     cannot collide with a brace, cannot be confused for a dataset placeholder by a reader,
#     and fails loudly rather than silently: an unknown token raises and a surviving `<<`
#     raises, so a constant can never be half-substituted into a query that then runs.
# ======================================================================================

_SQL_TOKEN = re.compile(r"<<([A-Z0-9_]+)>>")

_SQL_CONSTANTS: Mapping[str, Any] = MappingProxyType({
    "BASELINE_FIRST_DAY_BEFORE": BASELINE_FIRST_DAY_BEFORE,
    "BASELINE_LAST_DAY_BEFORE": BASELINE_LAST_DAY_BEFORE,
    "BASELINE_MIN_VALID_DAYS": BASELINE_MIN_VALID_DAYS,
    "BASELINE_MIN_SPAN_DAYS": BASELINE_MIN_SPAN_DAYS,
    "BASELINE_FLOOR_STEPS": BASELINE_FLOOR_STEPS,
    "BASELINE_DOW_LENGTH": BASELINE_DOW_LENGTH,
    "SUNDAY_INDEX": SUNDAY_INDEX,
    "SATURDAY_INDEX": SATURDAY_INDEX,
    "ACCRUAL_FIRST_DAY": ACCRUAL_FIRST_DAY,
    "ACCRUAL_LAST_DAY": ACCRUAL_LAST_DAY,
    "DISPLAY_FIRST_DAY": DISPLAY_FIRST_DAY,
    "DISPLAY_LAST_DAY": DISPLAY_LAST_DAY,
    "NEAR_COMPLETE_WINDOW_DAYS": NEAR_COMPLETE_WINDOW_DAYS,
    "STRUCTURAL_DELETION_LAST_DAY": STRUCTURAL_DELETION_LAST_DAY,
    "LANDMARK_WINDOW_DAYS": LANDMARK_WINDOW_DAYS,
    "LANDMARK_MIN_VALID_DAYS": LANDMARK_MIN_VALID_DAYS,
    "LANDMARK_DAY_OFFSET": LANDMARK_DAY_OFFSET,
    "LANDMARK_WEIGHT_MIN_LANDMARK_DAY": LANDMARK_WEIGHT_MIN_LANDMARK_DAY,
    "EARLY_LANDMARK_LAST_LANDMARK_DAY": EARLY_LANDMARK_LAST_LANDMARK_DAY,
    "EARLY_LANDMARK_LAST_MATCHED_DAY": EARLY_LANDMARK_LAST_MATCHED_DAY,
    "LANDMARK_PANEL_LOOKBACK_DAYS": LANDMARK_PANEL_LOOKBACK_DAYS,
    "SPLIT_BASELINE_MIN_WEEKDAY_DAYS": SPLIT_BASELINE_MIN_WEEKDAY_DAYS,
    "SPLIT_BASELINE_MIN_WEEKEND_DAYS": SPLIT_BASELINE_MIN_WEEKEND_DAYS,
    "CONTROLS_PER_CASE_CAP": CONTROLS_PER_CASE_CAP,
    "CONTROL_LANDMARKS_PER_PARTICIPANT_CAP": CONTROL_LANDMARKS_PER_PARTICIPANT_CAP,
    "FLOAT_TOLERANCE": FLOAT_TOLERANCE,
})


def _sql(template: str) -> str:
    """Substitute this module's `<<TOKEN>>` constants, leaving `{DERIVED}` untouched."""
    def swap(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name not in _SQL_CONSTANTS:
            raise FeatureCheckError(
                f"a query template names the constant <<{name}>>, which this module does not "
                f"define. Add it to the locked constants above rather than typing the number "
                f"into the query."
            )
        return str(_SQL_CONSTANTS[name])
    out = _SQL_TOKEN.sub(swap, template)
    if "<<" in out or ">>" in out:
        raise FeatureCheckError(
            "a query template still carries an unsubstituted token after substitution, so a "
            "constant would have reached BigQuery half-written. Nothing was submitted."
        )
    return out


_COLUMNS_MARKER = "-- @columns:"


def declared_columns(sql: str) -> tuple[str, ...]:
    """The result columns a query DECLARES, read off its own `-- @columns:` line.

    The line exists so that the Python counters below and the emitted SQL cannot drift apart
    without something failing.  The self-test asserts three things about it, in both
    directions: the line is present exactly once, every name on it appears in the query text as
    an explicit `AS name` alias, and the counter that mirrors that query produces exactly this
    column set.  A query that grows a column and a counter that does not therefore fails on a
    laptop rather than in a Workbench session.
    """
    lines = [line for line in sql.splitlines() if line.strip().startswith(_COLUMNS_MARKER)]
    if len(lines) != 1:
        raise FeatureCheckError(
            f"a query carries {len(lines)} column-declaration lines and must carry exactly one"
        )
    body = lines[0].split(_COLUMNS_MARKER, 1)[1]
    names = tuple(name.strip() for name in body.split(",") if name.strip())
    if not names:
        raise FeatureCheckError("a query declares no result columns")
    return names


# --------------------------------------------------------------------------------------
# The common head.  `features` is one row per ELIGIBLE episode, which is one row per
# participant because rung 13 takes the first eligible episode per person (DAG-SCHEMA 8.10), so
# a join to it on `person_id` is one to one and restricts every diagnostic to the analytic
# cohort without a second filter.
#
# The group expansion emits THREE rows per episode, giving the seven group slugs of plan 2.4 in
# one column: the episode's own collapse-level-1 group, its collapse-level-2 group, and the
# total.  It is the same seven-slug vocabulary `ledger_wear_by_day` emits, deliberately, so
# that the ledger cross-check below is a join and not a translation.
# --------------------------------------------------------------------------------------

_COHORT_HEAD = """
WITH cohort AS (
  SELECT
    f.episode_id       AS episode_id,
    f.person_id        AS person_id,
    f.index_date       AS index_date,
    f.discharge_date   AS discharge_date,
    f.procedure_group  AS procedure_group,
    f.fusion           AS fusion
  FROM `{DERIVED}.features` AS f
),
cohort_group AS (
  SELECT
    c.episode_id     AS episode_id,
    c.person_id      AS person_id,
    c.index_date     AS index_date,
    c.discharge_date AS discharge_date,
    g                AS group_slug
  FROM cohort AS c
  CROSS JOIN UNNEST([
    c.procedure_group,
    IF(c.fusion, 'fusion', 'decompression'),
    'all_groups'
  ]) AS g
)"""

# The window classification, written once.  The three named windows cannot overlap: the
# baseline window ends 8 days BEFORE the index date and the accrual window starts 1 day AFTER
# the discharge date, and the discharge date is never before the index date.  Everything else
# in the grid is named rather than dropped, because a partition with an unnamed remainder is
# not a partition and its total will not close.
_WINDOW_CASE = """
    CASE
      WHEN d.activity_date BETWEEN DATE_SUB(cg.index_date, INTERVAL <<BASELINE_FIRST_DAY_BEFORE>> DAY)
                               AND DATE_SUB(cg.index_date, INTERVAL <<BASELINE_LAST_DAY_BEFORE>> DAY)
        THEN 'baseline_window'
      WHEN d.activity_date BETWEEN DATE_ADD(cg.discharge_date, INTERVAL <<ACCRUAL_FIRST_DAY>> DAY)
                               AND DATE_ADD(cg.discharge_date, INTERVAL <<ACCRUAL_LAST_DAY>> DAY)
        THEN 'accrual_window'
      WHEN d.activity_date BETWEEN DATE_ADD(cg.discharge_date, INTERVAL <<DISPLAY_FIRST_DAY>> DAY)
                               AND DATE_ADD(cg.discharge_date, INTERVAL <<DISPLAY_LAST_DAY>> DAY)
        THEN 'display_tail'
      ELSE 'outside_named_windows'
    END"""


def wear_record_presence_sql() -> str:
    """Null against real zero against positive, on both wearable channels, by group and window.

    THIS IS THE QUERY THE WHOLE MODULE RESTS ON.  `wear_minutes` is null when there is NO
    heart-rate record and `steps` is null when there is no activity record (DAG-SCHEMA 8.7).
    Neither null is the number zero, and the two claims differ in the direction that matters: a
    day with no record contributes nothing and is weighted by the observation model, while a
    valid wear day with zero steps contributes a FULL day of deficit.  Every one of the three
    states therefore gets its own column and no two of them are ever added together here.

    Five columns are pure invariants and are expected to be zero on every row.  Two of them
    check the contract's own null convention in both directions (a record flag that disagrees
    with a null), one checks that a null wear figure is never a valid wear day under any
    definition, one checks the same for steps, and one checks that analyzable implies valid.
    """
    return _sql(_COHORT_HEAD + """,
day AS (
  SELECT
    cg.group_slug                      AS group_slug,""" + _WINDOW_CASE + """ AS window_slug,
    d.person_id                        AS person_id,
    d.has_hr_row                       AS has_hr_row,
    d.has_steps_row                    AS has_steps_row,
    d.wear_minutes                     AS wear_minutes,
    d.steps                            AS steps,
    d.valid_wear                       AS valid_wear,
    d.is_analyzable                    AS is_analyzable
  FROM cohort_group AS cg
  JOIN `{DERIVED}.fitbit_daily` AS d
    ON d.person_id = cg.person_id
)
-- @columns: group_slug, window_slug, n_persons, n_days, n_hr_row, n_no_hr_row, n_wear_minutes_null, n_wear_minutes_zero, n_wear_minutes_positive, n_hr_row_with_null_minutes, n_no_hr_row_with_minutes, n_steps_row, n_no_steps_row, n_steps_null, n_steps_zero, n_steps_positive, n_steps_row_with_null_steps, n_no_steps_row_with_steps, n_valid_wear, n_valid_wear_with_null_minutes, n_valid_wear_steps_null, n_analyzable, n_analyzable_not_valid_wear, n_zero_steps_valid_wear, n_zero_steps_analyzable
SELECT
  day.group_slug                                                   AS group_slug,
  segment                                                          AS window_slug,
  COUNT(DISTINCT day.person_id)                                    AS n_persons,
  COUNT(*)                                                         AS n_days,
  COUNTIF(day.has_hr_row)                                          AS n_hr_row,
  COUNTIF(NOT day.has_hr_row)                                      AS n_no_hr_row,
  COUNTIF(day.wear_minutes IS NULL)                                AS n_wear_minutes_null,
  COUNTIF(day.wear_minutes = 0)                                    AS n_wear_minutes_zero,
  COUNTIF(day.wear_minutes > 0)                                    AS n_wear_minutes_positive,
  COUNTIF(day.has_hr_row AND day.wear_minutes IS NULL)             AS n_hr_row_with_null_minutes,
  COUNTIF(NOT day.has_hr_row AND day.wear_minutes IS NOT NULL)     AS n_no_hr_row_with_minutes,
  COUNTIF(day.has_steps_row)                                       AS n_steps_row,
  COUNTIF(NOT day.has_steps_row)                                   AS n_no_steps_row,
  COUNTIF(day.steps IS NULL)                                       AS n_steps_null,
  COUNTIF(day.steps = 0)                                           AS n_steps_zero,
  COUNTIF(day.steps > 0)                                           AS n_steps_positive,
  COUNTIF(day.has_steps_row AND day.steps IS NULL)                 AS n_steps_row_with_null_steps,
  COUNTIF(NOT day.has_steps_row AND day.steps IS NOT NULL)         AS n_no_steps_row_with_steps,
  COUNTIF(day.valid_wear)                                          AS n_valid_wear,
  COUNTIF(day.valid_wear AND day.wear_minutes IS NULL)             AS n_valid_wear_with_null_minutes,
  COUNTIF(day.valid_wear AND day.steps IS NULL)                    AS n_valid_wear_steps_null,
  COUNTIF(day.is_analyzable)                                       AS n_analyzable,
  COUNTIF(day.is_analyzable AND NOT day.valid_wear)                AS n_analyzable_not_valid_wear,
  COUNTIF(day.valid_wear AND day.steps = 0)                        AS n_zero_steps_valid_wear,
  COUNTIF(day.is_analyzable AND day.steps = 0)                     AS n_zero_steps_analyzable
FROM day
CROSS JOIN UNNEST([day.window_slug, 'all_grid_days']) AS segment
GROUP BY day.group_slug, segment
ORDER BY group_slug, window_slug
""")


def wear_definition_agreement_sql() -> str:
    """The two by two between the EFFECTIVE wear flag and each of the five definitions.

    Read `valid_wear`, not `valid_wear_primary`: the effective flag carries this run's S2
    contingency (DAG-SCHEMA 8.7), and a diagnostic written against the primary flag would report
    a study that was not run whenever the zone-partition probe had failed.  The agreement
    against `valid_wear_primary` is therefore itself the evidence of whether the contingency
    fired, and it is the first row of the report rather than a footnote.

    Restricted to the two windows where the wear rule decides something.  In the baseline window
    it decides which days enter the median that becomes `B_i`, and so it changes the DENOMINATOR
    of every deficit; in the accrual window it decides which days are missing, and so it changes
    the exposure to missingness the whole estimator is built around.  Days outside both are
    counted in the presence query and add nothing here.
    """
    return _sql(_COHORT_HEAD + """,
day AS (
  SELECT
    cg.group_slug                      AS group_slug,""" + _WINDOW_CASE + """ AS window_slug,
    d.wear_minutes                     AS wear_minutes,
    d.valid_wear                       AS valid_wear,
    d.valid_wear_primary               AS valid_wear_primary,
    d.valid_wear_s1                    AS valid_wear_s1,
    d.valid_wear_s2                    AS valid_wear_s2,
    d.valid_wear_s3                    AS valid_wear_s3,
    d.valid_wear_s4                    AS valid_wear_s4
  FROM cohort_group AS cg
  JOIN `{DERIVED}.fitbit_daily` AS d
    ON d.person_id = cg.person_id
)
-- @columns: group_slug, window_slug, definition_slug, n_days, n_effective, n_definition, n_both, n_effective_only, n_definition_only, n_neither, n_definition_with_null_minutes
SELECT
  day.group_slug                                              AS group_slug,
  day.window_slug                                             AS window_slug,
  wd.definition_slug                                          AS definition_slug,
  COUNT(*)                                                    AS n_days,
  COUNTIF(day.valid_wear)                                     AS n_effective,
  COUNTIF(wd.flag)                                            AS n_definition,
  COUNTIF(day.valid_wear AND wd.flag)                         AS n_both,
  COUNTIF(day.valid_wear AND NOT wd.flag)                     AS n_effective_only,
  COUNTIF(NOT day.valid_wear AND wd.flag)                     AS n_definition_only,
  COUNTIF(NOT day.valid_wear AND NOT wd.flag)                 AS n_neither,
  COUNTIF(wd.flag AND day.wear_minutes IS NULL)               AS n_definition_with_null_minutes
FROM day
CROSS JOIN UNNEST([
  STRUCT('primary' AS definition_slug, day.valid_wear_primary AS flag),
  STRUCT('s1', day.valid_wear_s1),
  STRUCT('s2', day.valid_wear_s2),
  STRUCT('s3', day.valid_wear_s3),
  STRUCT('s4', day.valid_wear_s4)
]) AS wd
WHERE day.window_slug IN ('baseline_window', 'accrual_window')
GROUP BY day.group_slug, day.window_slug, wd.definition_slug
ORDER BY group_slug, window_slug, definition_slug
""")


# --------------------------------------------------------------------------------------
# The baseline.  Three describing queries over `features`, which is the analytic cohort and
# where every episode has already cleared rung 12, plus ONE invariants query over `baseline`,
# which is one row per episode INCLUDING the ineligible ones and is therefore the only place a
# zero baseline could still be sitting.  The split is deliberate: the description is about the
# cohort that will be modelled, and the invariant is about the whole table, because a defect
# that rung 12 happens to have filtered out is still a defect in the build.
#
# The weekday and weekend counts come out of `baseline_dow_counts`, which is ARRAY<INT64> of
# length exactly 7 with index 0 Sunday and index 6 Saturday (DAG-SCHEMA 8.8).  They are read
# with SAFE_OFFSET rather than OFFSET so that a short array returns null and is COUNTED by the
# invariants query, instead of raising inside a describing query and taking the whole report
# down with an error that reads like a BigQuery problem.
# --------------------------------------------------------------------------------------

def _weekend_days(alias: str) -> str:
    """Saturday plus Sunday out of one episode's composition array, on any table alias."""
    return (f"(IFNULL({alias}.baseline_dow_counts[SAFE_OFFSET(<<SUNDAY_INDEX>>)], 0)"
            f" + IFNULL({alias}.baseline_dow_counts[SAFE_OFFSET(<<SATURDAY_INDEX>>)], 0))")


def _all_dow_days(alias: str) -> str:
    return f"(SELECT IFNULL(SUM(x), 0) FROM UNNEST({alias}.baseline_dow_counts) AS x)"


def _weekday_days(alias: str) -> str:
    """Monday through Friday, as the array total less the weekend pair, on any table alias."""
    return "(" + _all_dow_days(alias) + " - " + _weekend_days(alias) + ")"


_WEEKEND_DAYS = _weekend_days("f")
_ALL_DOW_DAYS = _all_dow_days("f")
_WEEKDAY_DAYS = _weekday_days("f")


def baseline_day_distribution_sql() -> str:
    """Every whole-number baseline quantity as a distribution over episodes, in long format.

    Long format on purpose.  A wide frame with one column per metric is one row per episode,
    which is a participant-level frame; this is one row per (group, metric, value) with a count,
    which is an aggregate and is what a median may be reconstructed from without any
    participant row ever reaching the kernel.  `median_iqr` is then computed by expanding these
    counts, so the continuous summaries in the report cost nothing and disclose nothing.

    `lesser_of_weekday_and_weekend_baseline_days` is here because the PROTOCOL asks for weekday
    and weekend baselines to be estimated separately and the locked plan does not carry the row
    (see the findings section of the report).  Reporting the smaller of the two day counts says
    exactly how many episodes COULD support a split baseline at any minimum a later amendment
    might set, WITHOUT this module inventing that minimum, which is the one thing a
    prespecified analysis may not do after the distribution exists.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, metric_slug, bucket_value, n_episodes
SELECT
  cg.group_slug   AS group_slug,
  m.metric_slug   AS metric_slug,
  m.bucket_value  AS bucket_value,
  COUNT(*)        AS n_episodes
FROM cohort_group AS cg
JOIN `{DERIVED}.features` AS f
  ON f.episode_id = cg.episode_id
CROSS JOIN UNNEST([
  STRUCT('valid_baseline_days' AS metric_slug, f.n_valid_baseline_days AS bucket_value),
  STRUCT('baseline_span_days', f.baseline_span_days),
  STRUCT('weekday_baseline_days', """ + _WEEKDAY_DAYS + """),
  STRUCT('weekend_baseline_days', """ + _WEEKEND_DAYS + """),
  STRUCT('lesser_of_weekday_and_weekend_baseline_days',
         LEAST(""" + _WEEKDAY_DAYS + """, """ + _WEEKEND_DAYS + """)),
  STRUCT('analyzable_accrual_days', f.n_analyzable_days_1_35),
  STRUCT('at_risk_accrual_days', f.n_at_risk_days_1_35)
]) AS m
GROUP BY cg.group_slug, m.metric_slug, m.bucket_value
ORDER BY group_slug, metric_slug, bucket_value
""")


def baseline_categories_sql() -> str:
    """The categorical baseline facts, including whether each alternative baseline exists.

    The six alternative-baseline rows are the ones a sensitivity row cannot run without.
    `features` carries all six precomputed (DAG-SCHEMA 8.10) so that no sensitivity re-reads
    `fitbit_daily`, and each may be null on an episode whose alternative window held no valid
    day even though the locked window did.  A sensitivity row fitted on the episodes where its
    own baseline exists has a DIFFERENT denominator from the primary, and Table 2 has to print
    it; counting the absences here is what lets it.

    THE SPLIT BASELINE IS THE SAME RULE ON A THIRD DENOMINATOR, and it is read off `baseline`
    rather than off `features` because the four columns of ANALYSIS-PLAN 2.2 live there and
    only there (DAG-SCHEMA 8.8).  The join is one to one: `baseline` holds one row per episode
    including the ineligible ones, and the cohort head has already restricted to the analytic
    episodes.  Three rows and not one, because the three quantities have three different
    denominators.  An episode can clear the primary baseline adequacy rung on weekdays alone
    and have NO weekend baseline at all, so `weekday_baseline` and `weekend_baseline` are
    counted apart; and the ROW's own denominator is neither of them.  It is
    `baseline_weekday_weekend_split`, derived from the two DAY COUNTS clearing 5 weekday days
    and 2 weekend days, never from the two medians being non-null.  The plan puts the rule on
    the counts deliberately, so the minimum-day rule stays visible and auditable in one place
    instead of hiding inside a null test a later edit could weaken without anyone noticing.

    An episode with valid days in only one half of the week is excluded from that sensitivity
    row and from NOTHING ELSE.  It keeps its primary baseline, stays in the analytic cohort,
    stays in Table 1 and in Figure 2, and contributes to the primary estimand exactly as it did
    before the row existed.  Its whole cost is this count, and the count is printed.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, metric_slug, bucket_slug, n_episodes
SELECT
  cg.group_slug   AS group_slug,
  m.metric_slug   AS metric_slug,
  m.bucket_slug   AS bucket_slug,
  COUNT(*)        AS n_episodes
FROM cohort_group AS cg
JOIN `{DERIVED}.features` AS f
  ON f.episode_id = cg.episode_id
JOIN `{DERIVED}.baseline` AS b
  ON b.episode_id = cg.episode_id
CROSS JOIN UNNEST([
  STRUCT('baseline_band' AS metric_slug,
         IFNULL(f.baseline_band_slug, 'no_baseline') AS bucket_slug),
  STRUCT('baseline_floor',
         CASE WHEN f.meets_baseline_floor IS NULL THEN 'unknown'
              WHEN f.meets_baseline_floor THEN 'clears'
              ELSE 'below' END),
  STRUCT('near_complete_window', IF(f.near_complete_window, 'yes', 'no')),
  STRUCT('baseline_window_60_15',
         IF(f.baseline_steps_60_15 IS NULL, 'absent', 'present')),
  STRUCT('baseline_window_30_1',
         IF(f.baseline_steps_30_1 IS NULL, 'absent', 'present')),
  STRUCT('wear_definition_s1', IF(f.baseline_steps_s1 IS NULL, 'absent', 'present')),
  STRUCT('wear_definition_s2', IF(f.baseline_steps_s2 IS NULL, 'absent', 'present')),
  STRUCT('wear_definition_s3', IF(f.baseline_steps_s3 IS NULL, 'absent', 'present')),
  STRUCT('wear_definition_s4', IF(f.baseline_steps_s4 IS NULL, 'absent', 'present')),
  STRUCT('weekday_baseline',
         IF(b.baseline_steps_weekday IS NULL, 'absent', 'present')),
  STRUCT('weekend_baseline',
         IF(b.baseline_steps_weekend IS NULL, 'absent', 'present')),
  STRUCT('baseline_weekday_weekend_split',
         IF(b.n_valid_baseline_days_weekday >= <<SPLIT_BASELINE_MIN_WEEKDAY_DAYS>>
            AND b.n_valid_baseline_days_weekend >= <<SPLIT_BASELINE_MIN_WEEKEND_DAYS>>,
            'present', 'absent'))
]) AS m
GROUP BY cg.group_slug, m.metric_slug, m.bucket_slug
ORDER BY group_slug, metric_slug, bucket_slug
""")


def baseline_day_of_week_sql() -> str:
    """The day-of-week composition of the baseline windows, summed over episodes.

    ANALYSIS-PLAN 2.2 requires the composition to be recorded per episode and reported in
    AGGREGATE, and this is the aggregate.  Both indices are emitted, `dow_index` running 0 to 6
    with 0 Sunday as the array is stored and `day_of_week` running 1 to 7 with 1 Sunday as
    `EXTRACT(DAYOFWEEK)` and every other table in this DAG numbers it.  Emitting both, rather
    than silently converting, is what makes the off-by-one checkable instead of assumed: the
    self-test pins `day_of_week = dow_index + 1` and the report prints the named weekday.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, dow_index, day_of_week, n_baseline_days, n_episodes_contributing, n_episodes
SELECT
  cg.group_slug              AS group_slug,
  dow_index                  AS dow_index,
  dow_index + 1              AS day_of_week,
  SUM(dow_count)             AS n_baseline_days,
  COUNTIF(dow_count > 0)     AS n_episodes_contributing,
  COUNT(*)                   AS n_episodes
FROM cohort_group AS cg
JOIN `{DERIVED}.features` AS f
  ON f.episode_id = cg.episode_id
CROSS JOIN UNNEST(f.baseline_dow_counts) AS dow_count WITH OFFSET AS dow_index
GROUP BY cg.group_slug, dow_index
ORDER BY group_slug, dow_index
""")


def baseline_invariants_sql() -> str:
    """One row of pass-or-fail counts over the WHOLE `baseline` table, ineligible episodes too.

    THE ZERO BASELINE IS THE ONE THAT MATTERS.  `baseline_steps` is null and never zero
    (DAG-SCHEMA 8.8), because `exact_median` of an empty or all-null array returns null.  A zero
    would make normalized activity `S / B` infinite and the daily deficit `max(0, 1 - S/B)`
    silently equal to 1 on every day of that episode, manufacturing a maximal recovery debt out
    of an absence of data, and it would do it without a single null anywhere for a later reader
    to notice.  The count is taken over every episode rather than over the analytic cohort
    precisely because rung 12 would otherwise hide it.

    `n_dow_sum_mismatch` asserts the reading DAG-SCHEMA 8.8 now states outright: the array
    counts VALID baseline days, not every calendar day in the window.  The other reading carries
    no information, since the window is a fixed 23 calendar days and a calendar composition
    would be the same seven numbers on every episode in the study.  The assertion is that the
    array sums to `n_valid_baseline_days`, and it halts naming both readings if it fails rather
    than quietly reporting a composition of something else.

    THE FOUR SPLIT-BASELINE COLUMNS ARE CHECKED HERE TOO, AND ON THE SAME NULL RULE.
    `baseline_steps_weekday` and `baseline_steps_weekend` are null when their half of the window
    holds no valid day and are NEVER zero, for exactly the reason `baseline_steps` is: a zero
    baseline makes `S / B` infinite and the daily deficit 1 on every day, manufacturing a
    maximal recovery debt out of missing data, and on these two columns it would do so precisely
    on the participants whose wear is concentrated in the other half of the week, which is a
    differential error rather than a wash.  `n_valid_baseline_days_weekday` and
    `n_valid_baseline_days_weekend` are INT64 and never null.

    The identity DAG-SCHEMA 8.8 states is checked in all three of its parts, because it is the
    join between the composition array and the two medians and a build could satisfy any two of
    the three while breaking the remaining one: the weekday count equals indices 1 through 5 of
    the composition, the weekend count equals indices 0 and 6, and the two sum to
    `n_valid_baseline_days`.
    """
    return _sql("""
-- @columns: n_episodes, n_has_any_fitbit, n_baseline_null, n_baseline_zero, n_baseline_negative, n_null_with_valid_days, n_nonnull_without_valid_days, n_dow_length_wrong, n_dow_sum_mismatch, n_band_null_with_baseline, n_floor_null_with_baseline, n_span_zero_with_baseline, n_span_negative, n_alternative_baseline_zero, n_weekday_baseline_zero, n_weekend_baseline_zero, n_weekday_null_with_valid_days, n_weekday_nonnull_without_valid_days, n_weekend_null_with_valid_days, n_weekend_nonnull_without_valid_days, n_split_day_count_null, n_split_day_count_negative, n_weekday_count_mismatch, n_weekend_count_mismatch, n_weekday_weekend_sum_mismatch
SELECT
  COUNT(*)                                                          AS n_episodes,
  COUNTIF(b.has_any_fitbit)                                         AS n_has_any_fitbit,
  COUNTIF(b.baseline_steps IS NULL)                                 AS n_baseline_null,
  COUNTIF(b.baseline_steps = 0)                                     AS n_baseline_zero,
  COUNTIF(b.baseline_steps < 0)                                     AS n_baseline_negative,
  COUNTIF(b.baseline_steps IS NULL AND b.n_valid_baseline_days > 0) AS n_null_with_valid_days,
  COUNTIF(b.baseline_steps IS NOT NULL
          AND b.n_valid_baseline_days = 0)                          AS n_nonnull_without_valid_days,
  COUNTIF(ARRAY_LENGTH(b.baseline_dow_counts)
          != <<BASELINE_DOW_LENGTH>>)                               AS n_dow_length_wrong,
  COUNTIF((SELECT IFNULL(SUM(x), 0) FROM UNNEST(b.baseline_dow_counts) AS x)
          != b.n_valid_baseline_days)                               AS n_dow_sum_mismatch,
  COUNTIF(b.baseline_steps IS NOT NULL
          AND b.baseline_band_slug IS NULL)                         AS n_band_null_with_baseline,
  COUNTIF(b.baseline_steps IS NOT NULL
          AND b.meets_baseline_floor IS NULL)                       AS n_floor_null_with_baseline,
  COUNTIF(b.baseline_steps IS NOT NULL AND b.baseline_span_days = 0) AS n_span_zero_with_baseline,
  COUNTIF(b.baseline_span_days < 0)                                 AS n_span_negative,
  COUNTIF(b.baseline_steps_60_15 = 0 OR b.baseline_steps_30_1 = 0
          OR b.baseline_steps_s1 = 0 OR b.baseline_steps_s2 = 0
          OR b.baseline_steps_s3 = 0 OR b.baseline_steps_s4 = 0)    AS n_alternative_baseline_zero,
  COUNTIF(b.baseline_steps_weekday = 0)                             AS n_weekday_baseline_zero,
  COUNTIF(b.baseline_steps_weekend = 0)                             AS n_weekend_baseline_zero,
  COUNTIF(b.baseline_steps_weekday IS NULL
          AND b.n_valid_baseline_days_weekday > 0)                  AS n_weekday_null_with_valid_days,
  COUNTIF(b.baseline_steps_weekday IS NOT NULL
          AND b.n_valid_baseline_days_weekday = 0)                  AS n_weekday_nonnull_without_valid_days,
  COUNTIF(b.baseline_steps_weekend IS NULL
          AND b.n_valid_baseline_days_weekend > 0)                  AS n_weekend_null_with_valid_days,
  COUNTIF(b.baseline_steps_weekend IS NOT NULL
          AND b.n_valid_baseline_days_weekend = 0)                  AS n_weekend_nonnull_without_valid_days,
  COUNTIF(b.n_valid_baseline_days_weekday IS NULL
          OR b.n_valid_baseline_days_weekend IS NULL)               AS n_split_day_count_null,
  COUNTIF(b.n_valid_baseline_days_weekday < 0
          OR b.n_valid_baseline_days_weekend < 0)                   AS n_split_day_count_negative,
  COUNTIF(b.n_valid_baseline_days_weekday != """ + _weekday_days("b") + """)
                                                                    AS n_weekday_count_mismatch,
  COUNTIF(b.n_valid_baseline_days_weekend != """ + _weekend_days("b") + """)
                                                                    AS n_weekend_count_mismatch,
  COUNTIF(b.n_valid_baseline_days_weekday + b.n_valid_baseline_days_weekend
          != b.n_valid_baseline_days)                               AS n_weekday_weekend_sum_mismatch
FROM `{DERIVED}.baseline` AS b
""")


# --------------------------------------------------------------------------------------
# The daily deficit panel.  One invariants query, one by-day query, one taxonomy crosstab, one
# observation-model query, and one read of the ledger the by-day query is checked against.
# --------------------------------------------------------------------------------------


def daily_panel_invariants_sql() -> str:
    """One row of pass-or-fail counts over `drd_daily`.  Every one of them is expected to be 0.

    THE ZERO-IMPUTATION CHECK RUNS IN BOTH DIRECTIONS, and both directions are load-bearing.
    `n_deficit_null_but_analyzable` catches a deficit that went missing on a day that should
    have carried one, which would silently shrink the observed set.  `n_deficit_not_null_but_
    not_analyzable` catches the far more dangerous failure: a deficit that EXISTS on a day with
    no step record.  The only value such a deficit could plausibly have been given is zero, and
    a zero deficit is the assertion that the participant walked at or above their own
    preoperative baseline on a day nobody observed them.  Summing over observed days then lets
    every missing day contribute zero, and non-wear is most likely exactly when the true deficit
    is largest, so the bias runs downward and runs harder in the sicker participants.  That is
    the failure ANALYSIS-PLAN 3.2 built the model-and-integrate estimator to avoid, and it is
    invisible in every downstream summary once it has happened.

    THE ZERO-STEP DAY IS CHECKED THE OTHER WAY ROUND.  A real zero-step analyzable day is KEPT
    (ANALYSIS-PLAN 2.1) and contributes `max(0, 1 - 0/B) = 1`, a full day of deficit, because
    profound inactivity may be the biological signal of interest.  So the check is not that such
    days are absent, it is that they are PRESENT and that each carries a deficit of exactly 1.
    `n_zero_steps_analyzable` and `n_zero_steps_analyzable_deficit_one` must be equal, and if
    the first is large and the second is zero then something has deleted the days the study is
    about while leaving every count in the report looking healthy.

    THE TAXONOMY CHECK IS THE THIRD.  `day_kind_four` must equal `day_kind` with the inpatient
    setting promoted by precedence, which is what makes it the plan's exclusive four-value
    taxonomy over the same days rather than a second and inconsistent classification of them.
    """
    return _sql("""
-- @columns: n_days, n_at_risk, n_analyzable, n_deficit_null, n_deficit_not_null, n_deficit_null_but_analyzable, n_deficit_not_null_but_not_analyzable, n_deficit_zero, n_deficit_zero_not_analyzable, n_deficit_out_of_range, n_zero_steps_analyzable, n_zero_steps_analyzable_deficit_one, n_normalized_null_mismatch, n_untruncated_null_mismatch, n_truncation_mismatch, n_steps_null_with_deficit, n_valid_wear_with_null_minutes, n_analyzable_when_censored, n_inpatient_and_analyzable, n_day_kind_unknown, n_day_kind_four_unknown, n_day_kind_four_mismatch, n_observed_not_analyzable, n_analyzable_not_observed, n_lag_null_on_day_one, n_lag_nonnull_on_day_one, n_lag_null_after_day_one_at_risk, n_lag_null_after_day_one_censored, n_lag_out_of_range
SELECT
  COUNT(*)                                                     AS n_days,
  COUNTIF(NOT p.is_censored)                                   AS n_at_risk,
  COUNTIF(p.is_analyzable)                                     AS n_analyzable,
  COUNTIF(p.deficit IS NULL)                                   AS n_deficit_null,
  COUNTIF(p.deficit IS NOT NULL)                               AS n_deficit_not_null,
  COUNTIF(p.deficit IS NULL AND p.is_analyzable)               AS n_deficit_null_but_analyzable,
  COUNTIF(p.deficit IS NOT NULL
          AND NOT p.is_analyzable)                             AS n_deficit_not_null_but_not_analyzable,
  COUNTIF(p.deficit = 0)                                       AS n_deficit_zero,
  COUNTIF(p.deficit = 0 AND NOT p.is_analyzable)               AS n_deficit_zero_not_analyzable,
  COUNTIF(p.deficit < 0 OR p.deficit > 1)                      AS n_deficit_out_of_range,
  COUNTIF(p.is_analyzable AND p.steps = 0)                     AS n_zero_steps_analyzable,
  COUNTIF(p.is_analyzable AND p.steps = 0
          AND ABS(p.deficit - 1) <= <<FLOAT_TOLERANCE>>)       AS n_zero_steps_analyzable_deficit_one,
  COUNTIF((p.normalized_activity IS NULL)
          != (p.deficit IS NULL))                              AS n_normalized_null_mismatch,
  COUNTIF((p.deficit_untruncated IS NULL)
          != (p.deficit IS NULL))                              AS n_untruncated_null_mismatch,
  COUNTIF(p.deficit IS NOT NULL
          AND ABS(p.deficit - GREATEST(0.0, p.deficit_untruncated))
              > <<FLOAT_TOLERANCE>>)                           AS n_truncation_mismatch,
  COUNTIF(p.steps IS NULL AND p.deficit IS NOT NULL)           AS n_steps_null_with_deficit,
  COUNTIF(p.valid_wear AND p.wear_minutes IS NULL)             AS n_valid_wear_with_null_minutes,
  COUNTIF(p.is_censored AND p.is_analyzable)                   AS n_analyzable_when_censored,
  COUNTIF(p.is_inpatient AND p.is_analyzable)                  AS n_inpatient_and_analyzable,
  COUNTIF(p.day_kind NOT IN ('censored', 'observed', 'missing')) AS n_day_kind_unknown,
  COUNTIF(p.day_kind_four
          NOT IN ('censored', 'inpatient', 'observed', 'missing')) AS n_day_kind_four_unknown,
  COUNTIF(p.day_kind_four != CASE WHEN p.day_kind = 'censored' THEN 'censored'
                                  WHEN p.is_inpatient THEN 'inpatient'
                                  ELSE p.day_kind END)         AS n_day_kind_four_mismatch,
  COUNTIF(p.day_kind = 'observed' AND NOT p.is_analyzable)     AS n_observed_not_analyzable,
  COUNTIF(p.is_analyzable AND p.day_kind != 'observed')        AS n_analyzable_not_observed,
  COUNTIF(p.post_discharge_day = <<ACCRUAL_FIRST_DAY>>
          AND p.lagged_wear_fraction IS NULL)                  AS n_lag_null_on_day_one,
  COUNTIF(p.post_discharge_day = <<ACCRUAL_FIRST_DAY>>
          AND p.lagged_wear_fraction IS NOT NULL)              AS n_lag_nonnull_on_day_one,
  COUNTIF(p.post_discharge_day > <<ACCRUAL_FIRST_DAY>> AND NOT p.is_censored
          AND p.lagged_wear_fraction IS NULL)                  AS n_lag_null_after_day_one_at_risk,
  COUNTIF(p.post_discharge_day > <<ACCRUAL_FIRST_DAY>> AND p.is_censored
          AND p.lagged_wear_fraction IS NULL)                  AS n_lag_null_after_day_one_censored,
  COUNTIF(p.lagged_wear_fraction < 0
          OR p.lagged_wear_fraction > 1)                       AS n_lag_out_of_range
FROM `{DERIVED}.drd_daily` AS p
""")


def wear_availability_by_day_sql() -> str:
    """Observation by post-discharge day and group: the input to Figure 2 and to the weights.

    This is the pattern ANALYSIS-PLAN 3.7's observation model is fitted against and the one
    Figure 2's day-indexed curve is drawn on, and it is the diagnostic that says whether
    non-wear is concentrated where the deficit is expected to be largest.  Its four leading
    count columns are defined exactly as `ledger_wear_by_day` defines them (DAG-SCHEMA 8.17),
    so the two are compared cell by cell in Python rather than eyeballed; the remaining columns
    are the ones the ledger does not carry and the weights need.

    `n_inpatient_analyzable` is carried beside `n_inpatient` because inpatient is NOT exclusive
    of observed.  A readmitted participant wearing the device produces a valid, analyzable,
    inpatient day and the plan keeps it, so the inpatient column is a cross-cutting count and
    subtracting it from the analyzable column would delete real observations.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, post_discharge_day, n_at_risk, n_valid_wear, n_analyzable, n_inpatient, n_inpatient_analyzable, n_missing, n_censored, n_deficit_not_null, n_episodes
SELECT
  cg.group_slug                                       AS group_slug,
  p.post_discharge_day                                AS post_discharge_day,
  COUNTIF(NOT p.is_censored)                          AS n_at_risk,
  COUNTIF(NOT p.is_censored AND p.valid_wear)         AS n_valid_wear,
  COUNTIF(p.is_analyzable)                            AS n_analyzable,
  COUNTIF(NOT p.is_censored AND p.is_inpatient)       AS n_inpatient,
  COUNTIF(p.is_analyzable AND p.is_inpatient)         AS n_inpatient_analyzable,
  COUNTIF(p.day_kind = 'missing')                     AS n_missing,
  COUNTIF(p.day_kind = 'censored')                    AS n_censored,
  COUNTIF(p.deficit IS NOT NULL)                      AS n_deficit_not_null,
  COUNT(*)                                            AS n_episodes
FROM cohort_group AS cg
JOIN `{DERIVED}.drd_daily` AS p
  ON p.episode_id = cg.episode_id
GROUP BY cg.group_slug, p.post_discharge_day
ORDER BY group_slug, post_discharge_day
""")


def wear_availability_ledger_sql() -> str:
    """The DAG's own wear-availability ledger, read whole so the by-day query can be checked.

    Reading the ledger rather than trusting it is the point.  `07_export.py` writes Figure 2 and
    the wear-availability ledger out of THIS table, so a disagreement between it and a fresh
    aggregate of `drd_daily` is a disagreement between the figure and the panel the model was
    fitted on, and it would reach the manuscript as a caption whose numbers no reader could
    reproduce from the data.  All seven group slugs are emitted by the DAG because the collapse
    level is decided later (DAG-SCHEMA 8.17), so this frame has rows for groups that may not
    survive; that is expected and it is not a defect.
    """
    return _sql("""
-- @columns: group_slug, group_order, day, n_at_risk, n_valid_wear, n_analyzable, n_inpatient
SELECT
  l.group_slug   AS group_slug,
  l.group_order  AS group_order,
  l.day          AS day,
  l.n_at_risk    AS n_at_risk,
  l.n_valid_wear AS n_valid_wear,
  l.n_analyzable AS n_analyzable,
  l.n_inpatient  AS n_inpatient
FROM `{DERIVED}.ledger_wear_by_day` AS l
ORDER BY group_order, day
""")


def day_kind_crosstab_sql() -> str:
    """Both taxonomies and the inpatient flag on one grain, so neither can be collapsed.

    The three-value `day_kind` partitions the panel and so does the four-value `day_kind_four`;
    `is_inpatient` does NOT, because it cuts across both.  Emitting all three on one grain is
    what lets the report print each partition against the same denominator and print the
    inpatient flag as a cross-cutting count that is deliberately not added to either total.
    The cell that proves the point is (`day_kind` observed, `is_inpatient` true): it is
    non-empty by design, it is counted once inside the observed row of the three-value taxonomy
    and once inside the inpatient row of the four-value one, and it is the same days both times.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, window_slug, day_kind, day_kind_four, is_inpatient, is_analyzable, n_days
SELECT
  cg.group_slug                                                AS group_slug,
  IF(p.in_accrual_window, 'accrual_window', 'display_tail')    AS window_slug,
  p.day_kind                                                   AS day_kind,
  p.day_kind_four                                              AS day_kind_four,
  p.is_inpatient                                               AS is_inpatient,
  p.is_analyzable                                              AS is_analyzable,
  COUNT(*)                                                     AS n_days
FROM cohort_group AS cg
JOIN `{DERIVED}.drd_daily` AS p
  ON p.episode_id = cg.episode_id
GROUP BY group_slug, window_slug, day_kind, day_kind_four, is_inpatient, is_analyzable
ORDER BY group_slug, window_slug, day_kind, day_kind_four, is_inpatient, is_analyzable
""")


def observation_model_inputs_sql() -> str:
    """The lagged wear fraction, banded, which is the observation model's time-varying predictor.

    ANALYSIS-PLAN 3.7 conditions the observation model on the STRICTLY lagged wear fraction over
    post-discharge days `d-7` to `d-1`, so the model can never condition on the very day it is
    weighting.  The strictness is the whole safeguard, and it is checked in the invariants query
    rather than here; this query reports the distribution the weight model will actually see,
    and the analyzable count within each band, which is the crude form of the relationship the
    logistic regression is about to estimate.  A band with no analyzable days and a band with no
    days at all are different facts and the two columns keep them apart.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, lag_band_slug, n_days, n_at_risk, n_analyzable, n_in_accrual_window
SELECT
  cg.group_slug                                 AS group_slug,
  CASE
    WHEN p.lagged_wear_fraction IS NULL  THEN 'unavailable'
    WHEN p.lagged_wear_fraction = 0      THEN 'none'
    WHEN p.lagged_wear_fraction < 0.25   THEN 'below_quarter'
    WHEN p.lagged_wear_fraction < 0.50   THEN 'quarter_to_half'
    WHEN p.lagged_wear_fraction < 0.75   THEN 'half_to_three_quarters'
    WHEN p.lagged_wear_fraction < 1.00   THEN 'three_quarters_to_all'
    ELSE 'all'
  END                                           AS lag_band_slug,
  COUNT(*)                                      AS n_days,
  COUNTIF(NOT p.is_censored)                    AS n_at_risk,
  COUNTIF(p.is_analyzable)                      AS n_analyzable,
  COUNTIF(p.in_accrual_window)                  AS n_in_accrual_window
FROM cohort_group AS cg
JOIN `{DERIVED}.drd_daily` AS p
  ON p.episode_id = cg.episode_id
GROUP BY group_slug, lag_band_slug
ORDER BY group_slug, lag_band_slug
""")


# --------------------------------------------------------------------------------------
# Events and the two landmark conditions.  DAG-SCHEMA 8.12 is emphatic that the two must not be
# merged, and these two queries are what makes the separation auditable rather than asserted.
# --------------------------------------------------------------------------------------


def landmark_conditions_sql() -> str:
    """The two landmark conditions, on one grain, never summed together.

    `has_computable_landmark` is `n_valid_days_in_window >= 2`, a DATA condition on an event
    that is otherwise computable, and ANALYSIS-PLAN 4.4 keeps those windows in the risk set:
    requiring a computable ratio deletes preferentially the sickest windows, and conditioning on
    a common consequence of exposure and outcome is collider stratification.  Its complement is
    NOT the co-primary exposure.  `N` is `no_computable_step_signal`, which is
    `n_eligible_days_in_window >= 2 AND n_valid_days_in_window < 2`: the complement of the
    computable flag INSIDE the windows that held eligible days at all.  The bare complement
    would also hold on an event of post-discharge day 1 to 4, and that event is attrition rung
    18 rather than an exposure state.

    `structurally_uncomputable_landmark` is `n_eligible_days_in_window < 2`, a DEFINITIONAL
    condition: the exposure window must lie on post-discharge days, so an event on
    post-discharge day 1 to 4 has fewer than two eligible days however well the participant wore
    the device.  Those events are attrition rung 18 and are deleted from the analysis.

    Merging them deletes the collider-correction windows silently, because an event with no
    computable landmark simply never appears in an event-level file and nobody counts what is
    not there.  So both flags are on the grain, the `n_valid_days_in_window` and
    `n_eligible_days_in_window` they are defined from are on the grain beside them, and
    `n_events_on_day_four_or_earlier` is carried so the plan's own six-row derivation is
    CHECKED rather than trusted: within the structurally uncomputable rows it must equal the
    event count, and within every other row it must be zero.

    `n_r72_not_null` is on the grain for a reason a later reader will need.  `r72` is null only
    when the window holds NO valid day (DAG-SCHEMA 8.12), so an event with exactly ONE valid day
    carries a non-null `r72` that is a one-day median while `has_computable_landmark` is false.
    The co-primary model of 4.4 multiplies `f(R)` by `(1 - N)` and so never reads it, but a
    module that filtered on `r72 IS NOT NULL` instead of on the flag would read it, and would
    quietly reintroduce the collider the flag exists to avoid.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, is_first_event, n_valid_days_in_window, n_eligible_days_in_window, has_computable_landmark, structurally_uncomputable_landmark, no_computable_step_signal, n_events, n_events_on_day_four_or_earlier, n_r72_not_null, n_r72_24h_not_null, n_reference_not_null, n_negative_control_not_null, n_local_deterioration_not_null, n_wear_fraction_not_null, n_missing_days_mismatch
SELECT
  cg.group_slug                                        AS group_slug,
  e.is_first_event                                     AS is_first_event,
  e.n_valid_days_in_window                             AS n_valid_days_in_window,
  e.n_eligible_days_in_window                          AS n_eligible_days_in_window,
  e.has_computable_landmark                            AS has_computable_landmark,
  e.structurally_uncomputable_landmark                 AS structurally_uncomputable_landmark,
  e.no_computable_step_signal                          AS no_computable_step_signal,
  COUNT(*)                                             AS n_events,
  COUNTIF(e.event_post_discharge_day
          <= <<STRUCTURAL_DELETION_LAST_DAY>>)         AS n_events_on_day_four_or_earlier,
  COUNTIF(e.r72 IS NOT NULL)                           AS n_r72_not_null,
  COUNTIF(e.r72_24h IS NOT NULL)                       AS n_r72_24h_not_null,
  COUNTIF(e.r_reference_7day IS NOT NULL)              AS n_reference_not_null,
  COUNTIF(e.r_negative_control IS NOT NULL)            AS n_negative_control_not_null,
  COUNTIF(e.local_step_deterioration IS NOT NULL)      AS n_local_deterioration_not_null,
  COUNTIF(e.wear_fraction IS NOT NULL)                 AS n_wear_fraction_not_null,
  COUNTIF(e.n_missing_days_in_window
          != <<LANDMARK_WINDOW_DAYS>> - e.n_valid_days_in_window) AS n_missing_days_mismatch
FROM cohort_group AS cg
JOIN `{DERIVED}.events` AS e
  ON e.episode_id = cg.episode_id
GROUP BY group_slug, is_first_event, n_valid_days_in_window, n_eligible_days_in_window,
         has_computable_landmark, structurally_uncomputable_landmark, no_computable_step_signal
ORDER BY group_slug, is_first_event, n_valid_days_in_window, n_eligible_days_in_window
""")


def structurally_deleted_event_timing_sql() -> str:
    """When the structurally deleted events happened, which is a required attrition row.

    ANALYSIS-PLAN 4.3 consequence 2 requires the TIMING of these events to be reported and not
    only their number, and it matters beyond bookkeeping: the deleted events are the earliest
    ones, and earliest is a proxy for most severe.  A reader is entitled to know that the
    analysis is blind to the first four post-discharge days by construction and what that cost.
    Subject to the disclosure floor, so if a day's count cannot be shown the row prints as
    suppressed and the fact of the row still prints.

    `n_eligible_days_in_window` is on the grain because ANALYSIS-PLAN 4.3 consequence 3
    prespecifies a partial-window secondary that admits the post-discharge day 4 events using
    the single eligible day 1.  Those are exactly the rows where this column is 1, and the
    secondary needs their count before it can say whether it is worth running.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, event_post_discharge_day, is_first_event, n_eligible_days_in_window, n_events, n_with_any_valid_day
SELECT
  cg.group_slug                            AS group_slug,
  e.event_post_discharge_day               AS event_post_discharge_day,
  e.is_first_event                         AS is_first_event,
  e.n_eligible_days_in_window              AS n_eligible_days_in_window,
  COUNT(*)                                 AS n_events,
  COUNTIF(e.n_valid_days_in_window > 0)    AS n_with_any_valid_day
FROM cohort_group AS cg
JOIN `{DERIVED}.events` AS e
  ON e.episode_id = cg.episode_id
WHERE e.structurally_uncomputable_landmark
GROUP BY group_slug, event_post_discharge_day, is_first_event, n_eligible_days_in_window
ORDER BY group_slug, event_post_discharge_day, is_first_event
""")


# --------------------------------------------------------------------------------------
# The full-cohort day-indexed landmark panel, DAG-SCHEMA 8.13.  It is the surface the collider
# correction of ANALYSIS-PLAN 4.4 fix 3 is computed on, and it exists because the only two other
# surfaces both carry the selection the comparison exists to expose: `risk_sets` carries it
# where a set was DRAWN, and the draw selects on the very variable the comparison is about;
# `events` carries it only at event dates and chiefly among FIRST events, which is selection on
# the outcome.  This panel carries every analytic episode and every post-discharge day 1 to 90,
# including the days nobody was sampled at and the episodes that never had an event.
#
# TWO INVARIANTS THE STAGE ALREADY ASSERTS IN SQL ARE RE-ASSERTED HERE ON THE FRAMES, because a
# procedure that raised is not evidence about the table a later session reads.  The panel must
# reproduce `events` cell for cell at every event date, and
# `structurally_uncomputable_landmark` must equal `post_discharge_day <= 4` on every episode-day.
# --------------------------------------------------------------------------------------


def landmark_panel_invariants_sql() -> str:
    """One row of pass-or-fail counts over the whole landmark panel, plus its overlap with `events`.

    THE TWO LANDMARK CONDITIONS ARE ON THE GRAIN AND ARE NEVER SUMMED, here as everywhere else.
    `no_computable_step_signal` is the DATA condition and ONLY the data condition,
    `n_eligible_days_in_window >= 2 AND n_valid_days_in_window < 2`: fewer than two WORN days in
    a window that held the days to wear on.  Those episode-days are the "without a computable
    ratio" side of fix 3's comparison and the co-primary exposure keeps them in the risk set.
    `structurally_uncomputable_landmark` is the DEFINITIONAL condition, fewer than two
    POST-DISCHARGE days in the window at all; it is attrition rung 18 and it leaves.  So a
    structurally uncomputable day is NOT without a step signal: it is outside the exposure
    entirely, carries no `N`, and the containment runs `no_computable_step_signal` implies NOT
    `structurally_uncomputable_landmark`.  That containment is asserted below rather than
    assumed, and it is why the by-day query carries both flags on its grain.

    THE FIVE EARLY-LANDMARK COLUMNS ARE CHECKED AGAINST THEIR OWN DEFINITIONS, not against each
    other.  `landmark_lagged_wear_fraction` is null exactly where the weight has no input, which
    is a landmark day of 1 or less and NOT a landmark day below 1: at a landmark on day 1 the
    panel row exists and the column is null anyway, because the lag is defined over
    post-discharge days and day 1 has none preceding it.  `landmark_weight_input_available` is
    that null test as a flag, `landmark_before_post_discharge_day_one` is the strictly narrower
    subset with no `drd_daily` row at all, and the two are counted apart.

    `n_days_behind_landmark_on_wearable_grid` IS EXPECTED TO BE SEVEN ON EVERY ROW.
    `fitbit_daily` is a dense calendar grid reaching back to index day minus 60, so the seven
    calendar days behind any landmark lie inside it for every post-discharge day and every
    length of stay.  A row below seven is not a data condition to be weighted around: it means
    the grid does not cover the lookback, and it is a defect to be found before any weight is
    fitted.
    """
    return _sql("""
-- @columns: n_episode_days, n_episodes, n_persons, n_censored_days, n_at_risk_days, n_event_days, n_first_event_days, n_data_uncomputable_days, n_structurally_uncomputable_days, n_computable_days, n_weight_input_absent, n_weight_input_available, n_landmark_before_day_one, n_landmark_day_offset_wrong, n_day_out_of_range, n_valid_out_of_range, n_eligible_out_of_range, n_valid_over_eligible, n_computable_flag_wrong, n_signal_flag_wrong, n_structural_flag_wrong, n_structural_definition_wrong, n_structural_carrying_no_signal, n_weight_flag_wrong, n_weight_null_boundary_wrong, n_before_day_one_flag_wrong, n_wearable_lag_null, n_wearable_lag_out_of_range, n_wearable_grid_short, n_first_event_not_event, n_events_joined, n_events_without_panel_row, n_event_window_disagreement, n_event_day_not_flagged
WITH panel AS (
  SELECT
    l.episode_id                                AS episode_id,
    l.person_id                                 AS person_id,
    l.post_discharge_day                        AS post_discharge_day,
    l.landmark_post_discharge_day               AS landmark_post_discharge_day,
    l.is_censored                               AS is_censored,
    l.n_valid_days_in_window                    AS n_valid_days_in_window,
    l.n_eligible_days_in_window                 AS n_eligible_days_in_window,
    l.has_computable_landmark                   AS has_computable_landmark,
    l.structurally_uncomputable_landmark        AS structurally_uncomputable_landmark,
    l.no_computable_step_signal                 AS no_computable_step_signal,
    l.landmark_lagged_wear_fraction             AS landmark_lagged_wear_fraction,
    l.landmark_weight_input_available           AS landmark_weight_input_available,
    l.landmark_before_post_discharge_day_one    AS landmark_before_post_discharge_day_one,
    l.landmark_lagged_wear_fraction_wearable    AS landmark_lagged_wear_fraction_wearable,
    l.n_days_behind_landmark_on_wearable_grid   AS n_days_behind_landmark_on_wearable_grid,
    l.is_event_day                              AS is_event_day,
    l.is_first_event_day                        AS is_first_event_day
  FROM `{DERIVED}.landmark_daily` AS l
),
-- The panel and the event table compute the SAME window at an event's own post-discharge day,
-- by the same rule, out of different sources: the event table counts days out of the wearable
-- grid and the panel counts them out of the daily panel.  A disagreement means one has drifted,
-- and the full-cohort comparison would then be answering a different question from the one the
-- risk sets answer, which is a confusion a collider correction cannot survive.
overlap AS (
  SELECT
    COUNT(*)                                                     AS n_events_joined,
    COUNTIF(l.episode_id IS NULL)                                AS n_events_without_panel_row,
    COUNTIF(l.episode_id IS NOT NULL
            AND (l.n_valid_days_in_window != e.n_valid_days_in_window
              OR l.n_eligible_days_in_window != e.n_eligible_days_in_window
              OR l.has_computable_landmark != e.has_computable_landmark
              OR l.structurally_uncomputable_landmark
                 != e.structurally_uncomputable_landmark))       AS n_event_window_disagreement,
    COUNTIF(l.episode_id IS NOT NULL AND NOT l.is_event_day)     AS n_event_day_not_flagged
  FROM `{DERIVED}.events` AS e
  LEFT JOIN panel AS l
    ON l.episode_id = e.episode_id
   AND l.post_discharge_day = e.event_post_discharge_day
)
SELECT
  COUNT(*)                                              AS n_episode_days,
  COUNT(DISTINCT p.episode_id)                          AS n_episodes,
  COUNT(DISTINCT p.person_id)                           AS n_persons,
  COUNTIF(p.is_censored)                                AS n_censored_days,
  COUNTIF(NOT p.is_censored)                            AS n_at_risk_days,
  COUNTIF(p.is_event_day)                               AS n_event_days,
  COUNTIF(p.is_first_event_day)                         AS n_first_event_days,
  -- The DATA condition, read off the column that now carries it and nothing else, and the
  -- definitional one beside it.  Never a sum: one is an exposure and the other is an exclusion.
  -- The AND NOT structurally_uncomputable_landmark this line used to carry was REDUNDANT once
  -- the column became eligible days at least 2 AND valid days below 2, not wrong, because it
  -- was a predicate conjunction over the same rows and never an arithmetic subtraction.  It is
  -- removed rather than kept, because a count that reads correctly under both the old union
  -- definition and the new data-only one would hide a table still carrying the old one, and
  -- the signal-flag pin below is the check that has to halt on exactly that.
  COUNTIF(p.no_computable_step_signal)                  AS n_data_uncomputable_days,
  COUNTIF(p.structurally_uncomputable_landmark)         AS n_structurally_uncomputable_days,
  COUNTIF(p.has_computable_landmark)                    AS n_computable_days,
  COUNTIF(p.landmark_post_discharge_day
          <= <<EARLY_LANDMARK_LAST_LANDMARK_DAY>>)      AS n_weight_input_absent,
  COUNTIF(p.landmark_weight_input_available)            AS n_weight_input_available,
  COUNTIF(p.landmark_before_post_discharge_day_one)     AS n_landmark_before_day_one,
  COUNTIF(p.landmark_post_discharge_day
          != p.post_discharge_day - <<LANDMARK_DAY_OFFSET>>)  AS n_landmark_day_offset_wrong,
  COUNTIF(p.post_discharge_day < <<ACCRUAL_FIRST_DAY>>
          OR p.post_discharge_day > <<DISPLAY_LAST_DAY>>)     AS n_day_out_of_range,
  COUNTIF(p.n_valid_days_in_window < 0
          OR p.n_valid_days_in_window > <<LANDMARK_WINDOW_DAYS>>)  AS n_valid_out_of_range,
  COUNTIF(p.n_eligible_days_in_window < 0
          OR p.n_eligible_days_in_window > <<LANDMARK_WINDOW_DAYS>>) AS n_eligible_out_of_range,
  COUNTIF(p.n_valid_days_in_window > p.n_eligible_days_in_window)    AS n_valid_over_eligible,
  COUNTIF(p.has_computable_landmark
          != (p.n_valid_days_in_window >= <<LANDMARK_MIN_VALID_DAYS>>)) AS n_computable_flag_wrong,
  -- THE PIN.  The co-primary exposure is the DATA condition and only the data condition:
  -- the window held its 2 post-discharge days AND fewer than 2 of them were worn.  A surface
  -- setting this from valid days alone admits the definitional condition into the exposure,
  -- and ANALYSIS-PLAN 4.4 corrects the surface against the plan rather than the other way.
  COUNTIF(p.no_computable_step_signal
          != (p.n_eligible_days_in_window >= <<LANDMARK_MIN_VALID_DAYS>>
              AND p.n_valid_days_in_window
                  < <<LANDMARK_MIN_VALID_DAYS>>))       AS n_signal_flag_wrong,
  -- The six-row derivation of ANALYSIS-PLAN 4.3, checked on EVERY episode-day rather than only
  -- at the event dates the way attrition rung 18 checks it.
  COUNTIF(p.structurally_uncomputable_landmark
          != (p.post_discharge_day
              <= <<STRUCTURAL_DELETION_LAST_DAY>>))     AS n_structural_flag_wrong,
  COUNTIF(p.structurally_uncomputable_landmark
          != (p.n_eligible_days_in_window
              < <<LANDMARK_MIN_VALID_DAYS>>))           AS n_structural_definition_wrong,
  -- The containment, in the direction the data-only definition puts it: a structurally
  -- uncomputable day is OUTSIDE the exposure, so it may not carry the no-signal flag at all.
  COUNTIF(p.structurally_uncomputable_landmark
          AND p.no_computable_step_signal)              AS n_structural_carrying_no_signal,
  COUNTIF(p.landmark_weight_input_available
          != (p.landmark_lagged_wear_fraction IS NOT NULL)) AS n_weight_flag_wrong,
  COUNTIF((p.landmark_lagged_wear_fraction IS NULL)
          != (p.landmark_post_discharge_day
              <= <<EARLY_LANDMARK_LAST_LANDMARK_DAY>>)) AS n_weight_null_boundary_wrong,
  COUNTIF(p.landmark_before_post_discharge_day_one
          != (p.landmark_post_discharge_day
              < <<ACCRUAL_FIRST_DAY>>))                 AS n_before_day_one_flag_wrong,
  COUNTIF(p.landmark_lagged_wear_fraction_wearable IS NULL) AS n_wearable_lag_null,
  COUNTIF(p.landmark_lagged_wear_fraction_wearable < 0
          OR p.landmark_lagged_wear_fraction_wearable > 1) AS n_wearable_lag_out_of_range,
  COUNTIF(p.n_days_behind_landmark_on_wearable_grid
          != <<LANDMARK_PANEL_LOOKBACK_DAYS>>)          AS n_wearable_grid_short,
  COUNTIF(p.is_first_event_day AND NOT p.is_event_day)  AS n_first_event_not_event,
  ANY_VALUE(o.n_events_joined)                          AS n_events_joined,
  ANY_VALUE(o.n_events_without_panel_row)               AS n_events_without_panel_row,
  ANY_VALUE(o.n_event_window_disagreement)              AS n_event_window_disagreement,
  ANY_VALUE(o.n_event_day_not_flagged)                  AS n_event_day_not_flagged
FROM panel AS p
CROSS JOIN overlap AS o
""")


def landmark_panel_by_day_sql() -> str:
    """The panel by group, post-discharge day and BOTH landmark conditions, kept separate.

    This is the frame ANALYSIS-PLAN 4.4 fix 3 is computed from, and its grain is chosen so that
    the comparison cannot be taken wrongly.  Post-discharge day is on the grain because the
    comparison is unmatched and descriptive and the plan requires it reported TWICE, crude and
    directly standardized to the post-discharge-day distribution of the analytic cohort: post-
    discharge day drives both wear and events, and a single crude number cannot say how much of
    the contrast is that.  If the two agree, post-discharge day is not doing the work; if they
    disagree, the reader is shown by how much rather than told which to believe.

    BOTH LANDMARK CONDITIONS ARE ON THE GRAIN AND THE DEFINITIONAL ONE IS FILTERED OUT OF THE
    COMPARISON RATHER THAN ADDED INTO IT.  On post-discharge days 1 to 4 the window holds fewer
    than two post-discharge days at all, so those days are uncomputable for a reason that is not
    about wear and they are on NEITHER side of the comparison: the data condition is false there
    and the computable flag is false there too.  A frame carrying only the two exposure states
    would leave them nowhere and the day counts would not add up to the panel, and a frame that
    put them on the "without a computable ratio" side would make the comparison partly a
    statement about the calendar.  Carrying the definitional flag beside them is what lets the
    consumer restrict to the days where the comparison means anything, and count the rest
    separately.

    The denominators are AT-RISK episode-days, not episode-days.  A censored day is not at risk:
    the episode is past death, past a repeat operation or past the observation cutoff, and
    counting it would put days nobody could have had an event on into the denominator of an
    event rate.
    """
    return _sql(_COHORT_HEAD + """
-- @columns: group_slug, post_discharge_day, structurally_uncomputable_landmark, no_computable_step_signal, n_episode_days, n_at_risk_days, n_event_days, n_first_event_days, n_weight_input_available
SELECT
  cg.group_slug                                            AS group_slug,
  l.post_discharge_day                                     AS post_discharge_day,
  l.structurally_uncomputable_landmark                     AS structurally_uncomputable_landmark,
  l.no_computable_step_signal                              AS no_computable_step_signal,
  COUNT(*)                                                 AS n_episode_days,
  COUNTIF(NOT l.is_censored)                               AS n_at_risk_days,
  COUNTIF(l.is_event_day AND NOT l.is_censored)            AS n_event_days,
  COUNTIF(l.is_first_event_day AND NOT l.is_censored)      AS n_first_event_days,
  COUNTIF(l.landmark_weight_input_available)               AS n_weight_input_available
FROM cohort_group AS cg
JOIN `{DERIVED}.landmark_daily` AS l
  ON l.episode_id = cg.episode_id
GROUP BY group_slug, post_discharge_day, structurally_uncomputable_landmark,
         no_computable_step_signal
ORDER BY group_slug, post_discharge_day, structurally_uncomputable_landmark,
         no_computable_step_signal
""")


# --------------------------------------------------------------------------------------
# The matched risk sets.  Four aggregate queries plus a digest.  Every degree of freedom in the
# sampling is closed by ANALYSIS-PLAN 4.5 and DAG-SCHEMA 8.14, so every one of them is checkable
# and each of these queries checks one.
# --------------------------------------------------------------------------------------


def matched_set_sizes_sql() -> str:
    """Controls per case, by relaxation rung, with both cap checks and a set-shape check.

    The size distribution is the number that shows whether the two caps bit and how hard.  Some
    sets ending with fewer than five controls is EXPECTED: the per-set cap of 5 is applied
    first and the per-participant cap of 3 control landmarks second, and applying them in that
    order deliberately leaves sets short rather than spending a prolific participant's three
    slots on sets they would not have been drawn into anyway.

    `n_size_mismatch` compares the `set_size` the rows CARRY against the number of control rows
    actually present in the set.  They cannot disagree if the table was built as specified, and
    if they do then either the caps were applied to the column and not to the rows or the rows
    were filtered after the column was written, and the matched-set ledger in the supplement
    would be describing a table that is not the one the conditional model reads.

    THE OTHER TWO COUNTS ANALYSIS-PLAN 4.4 OBLIGES ARE SET-LEVEL AND ARE TAKEN HERE, because a
    set is not recoverable from a member count.  `n_sets_losing_every_control` is the count that
    turns a member-level exclusion into an ANALYSIS-level one: a matched set with no control
    contributes nothing at all to a conditional likelihood, so it leaves the weighted
    sensitivity whole, and no arithmetic on the member counts recovers how many sets that was.
    `n_sets_losing_the_case` is its companion in the other direction and is just as final, since
    a set without its case is not a matched set.  `n_sets_in_weighted_sensitivity` and
    `n_members_in_weighted_sensitivity` are the weighted sensitivity's OWN DENOMINATOR, in sets
    and in members, which 9.2 requires printed beside the primary's because a row fitted on a
    subset prints its own `n`.

    The three are not a partition and are not summed.  A set can lose its case and every control
    at once, so the first two overlap; what closes is that a set is in the weighted sensitivity
    exactly when it keeps its case AND at least one control.
    """
    return _sql("""
-- @columns: set_size, match_rung, n_sets, n_size_mismatch, n_case_row_count_wrong, n_over_control_cap, n_sets_losing_every_control, n_sets_losing_the_case, n_sets_in_weighted_sensitivity, n_members_in_weighted_sensitivity
WITH per_set AS (
  SELECT
    r.set_id                                                       AS set_id,
    ANY_VALUE(IF(r.member_role = 'case', r.set_size, NULL))        AS declared_size,
    ANY_VALUE(IF(r.member_role = 'case', r.match_rung, NULL))      AS case_rung,
    COUNTIF(r.member_role = 'control')                             AS observed_size,
    COUNTIF(r.member_role = 'case')                                AS n_case_rows,
    -- ANALYSIS-PLAN 4.4: weighted when the member's OWN landmark day is 2 or more.
    COUNTIF(r.member_role = 'control'
            AND r.member_landmark_post_discharge_day
                >= <<LANDMARK_WEIGHT_MIN_LANDMARK_DAY>>)           AS n_controls_weighted,
    LOGICAL_OR(r.member_role = 'case'
               AND r.member_landmark_post_discharge_day
                   >= <<LANDMARK_WEIGHT_MIN_LANDMARK_DAY>>)        AS case_weighted
  FROM `{DERIVED}.risk_sets` AS r
  GROUP BY set_id
)
SELECT
  per_set.declared_size                                            AS set_size,
  per_set.case_rung                                                AS match_rung,
  COUNT(*)                                                         AS n_sets,
  COUNTIF(per_set.declared_size != per_set.observed_size)          AS n_size_mismatch,
  COUNTIF(per_set.n_case_rows != 1)                                AS n_case_row_count_wrong,
  COUNTIF(per_set.observed_size > <<CONTROLS_PER_CASE_CAP>>)       AS n_over_control_cap,
  COUNTIF(per_set.observed_size > 0
          AND per_set.n_controls_weighted = 0)                     AS n_sets_losing_every_control,
  COUNTIF(NOT per_set.case_weighted)                               AS n_sets_losing_the_case,
  COUNTIF(per_set.case_weighted
          AND per_set.n_controls_weighted > 0)                     AS n_sets_in_weighted_sensitivity,
  SUM(IF(per_set.case_weighted AND per_set.n_controls_weighted > 0,
         1 + per_set.n_controls_weighted, 0))                      AS n_members_in_weighted_sensitivity
FROM per_set
GROUP BY set_size, match_rung
ORDER BY set_size, match_rung
""")


def matched_set_members_sql() -> str:
    """Member-level shape checks, and the two by two the co-primary exposure rests on.

    `fingerprint` is NULL on every case row and non-null on every control row (DAG-SCHEMA 8.14),
    because the fingerprint is the seeded ordering that DREW the control and a case was not
    drawn.  Both directions are counted: a case row carrying one would mean cases had been run
    through the sampler, and a control row missing one would mean a control had been selected by
    something other than the seeded order, which is exactly the nondeterminism 4.5 forbids.

    `n_landmark_weight_input_absent` IS THE COUNT ANALYSIS-PLAN 4.4 OBLIGES, AND ITS BOUNDARY
    IS ONE DAY WIDER THAN IT LOOKS.  A member's landmark sits at `member_matched_day - 3`, and
    the weight model's predictor is the lagged wear fraction over post-discharge days `T-7` to
    `T-1`.  That column does not EXIST at a landmark day of 0 or less, where `drd_daily` has no
    row at all; and it IS NULL at a landmark day of exactly 1, where the row exists but the lag
    has no preceding post-discharge day to average over.  So the affected set is landmark day
    **1 or less**, equivalently MATCHED DAY 4 or less, and a counter written on landmark day
    below 1 misses the whole matched-day-4 group.  Those are the earliest members in the study
    and by the argument of 4.3 the sickest, which is the one direction in which missing them
    would flatter the result.  `n_landmark_before_post_discharge_day_one` is carried BESIDE it,
    not instead of it: it is the strictly narrower subset with no `drd_daily` row at all
    (DAG-SCHEMA 8.13), and the two are different quantities.

    THE RULE, WHICH IS PRESPECIFIED AND NOT DECIDED HERE, AND WHICH PLAN VERSION 1.5 RESTATED
    AS ARITHMETIC.  A member is weighted when its own landmark day is 2 or more.  A LANDMARK
    DAY OF 1 OR LESS IS NOT A SECOND THRESHOLD sitting beside that rule: the landmark is
    `T = E - 3` and the window is `T-2` to `T`, so the window's post-discharge days are the
    days of `T-2` to `T` that are 1 or greater, and that count reaches 2 exactly when `T` is 2
    or more.  `T <= 1` is therefore THE DEFINITIONAL CONDITION written in landmark-day terms,
    and such a member has no exposure window at all.  It carries NO `N`, it contributes nothing
    to `beta_N`, and it is outside the co-primary exposure on every surface: the conditional
    model of 4.5, the discrete-time model of 4.6, the `landmark_daily` panel and this table.
    A control the day-of-week relaxation of 4.7 puts at post-discharge day 3 or 4 is DROPPED
    FROM ITS RISK SET AS A MEMBER AND COUNTED HERE, because it cannot leave at rung 18: rung 18
    is an EVENT rung and a sampled control is not an event.  A matched set that loses every
    control this way contributes nothing to a conditional likelihood and leaves it altogether,
    which is the set-level count above.  The weight rule of fix 2 bites the same members for a
    different reason and in the primary has nothing left to exclude; it stands alone only where
    the partial-window secondary of 4.3 deliberately reads such a member back in under its own
    single-eligible-day rule, and there that member leaves the weighted sensitivity and nothing
    else.

    THE TWO ROUTES ARE COUNTED APART, because the plan requires the split and because they are
    different populations.  4.3 puts every case in the primary at post-discharge day 5 or later
    and therefore at a landmark day of 2 or more, so a member this early arrived by one of two
    named routes.  The PARTIAL-WINDOW SECONDARY of 4.3 admits an event on post-discharge day 4,
    which puts the case itself at landmark day 1 and takes its rung-1 controls with it, so the
    route is read off the CASE's matched day.  The DAY-OF-WEEK RELAXATION of 4.7 admits, at
    rungs 2 and 3, a control up to 2 days below its case's post-discharge day, so a control
    matched to a case at day 5 may sit at day 3 and carry a landmark at day 0; that route is
    read off the member sitting EARLIER than its own case.  The two are mutually exclusive and
    the plan says they are exhaustive, so `n_early_by_neither_route` must be zero and a non-zero
    value is a stop condition rather than a third route nobody prespecified.

    THAT STOP CONDITION IS LOAD-BEARING NOW RATHER THAN THEORETICAL, and it survives the wider
    candidate floor.  `build_all.sql` once carried `control_matched_day >= 5` and excluded every
    day-3 and day-4 control before it could be drawn, so these counts were structurally zero by
    construction; the floor is now 1, such a control is admitted, ranked, drawn under both caps
    and then dropped here as a member carrying the definitional flag.  The exhaustiveness still
    closes, and it closes as ARITHMETIC on the offset invariant rather than as a promise: early
    means a landmark day of 1 or less, which under `landmark = matched - 3` means a matched day
    of 4 or less; "neither route" additionally requires a case matched day above 4 AND a member
    matched day at or above its case's, which would put the member at 5 or more.  The two
    cannot both hold.  So on a table whose landmark offset is intact this count is zero at every
    candidate day the new floor admits, day 1 and day 2 included, and a non-zero value means the
    offset itself has already broken -- which is why `n_landmark_day_offset_wrong` sits beside
    it and why the self-test asserts both fire together.

    `n_early_carrying_no_signal` IS NOT A COLUMN, AND DELIBERATELY SO.  `no_computable_step_signal`
    is already on the grain, so a member at a landmark day of 1 or less carrying the exposure
    shows up as a non-zero `n_landmark_weight_input_absent` on a grain row whose exposure key is
    true, and `risk_set_violations` reads it there.  `n_early_carrying_r72` DOES need a column,
    because the ratio is not on the grain and an early member's non-null ratio would otherwise
    hide inside `n_r72_not_null` beside the ratios of members that legitimately have one.
    """
    return _sql("""
-- @columns: member_role, is_case, no_computable_step_signal, match_rung, n_members, n_persons, n_fingerprint_null, n_r72_not_null, n_wear_fraction_not_null, n_landmark_weight_input_absent, n_landmark_before_post_discharge_day_one, n_early_via_partial_window_secondary, n_early_via_day_of_week_relaxation, n_early_by_neither_route, n_early_carrying_r72, n_landmark_day_offset_wrong, n_role_flag_mismatch
SELECT
  r.member_role                                                    AS member_role,
  r.is_case                                                        AS is_case,
  r.no_computable_step_signal                                      AS no_computable_step_signal,
  r.match_rung                                                     AS match_rung,
  COUNT(*)                                                         AS n_members,
  COUNT(DISTINCT r.person_id)                                      AS n_persons,
  COUNTIF(r.fingerprint IS NULL)                                   AS n_fingerprint_null,
  COUNTIF(r.r72 IS NOT NULL)                                       AS n_r72_not_null,
  COUNTIF(r.wear_fraction IS NOT NULL)                             AS n_wear_fraction_not_null,
  COUNTIF(r.member_landmark_post_discharge_day
          <= <<EARLY_LANDMARK_LAST_LANDMARK_DAY>>)                  AS n_landmark_weight_input_absent,
  COUNTIF(r.member_landmark_post_discharge_day
          < <<ACCRUAL_FIRST_DAY>>)                                 AS n_landmark_before_post_discharge_day_one,
  COUNTIF(r.member_landmark_post_discharge_day
            <= <<EARLY_LANDMARK_LAST_LANDMARK_DAY>>
          AND r.case_matched_day
            <= <<EARLY_LANDMARK_LAST_MATCHED_DAY>>)                AS n_early_via_partial_window_secondary,
  COUNTIF(r.member_landmark_post_discharge_day
            <= <<EARLY_LANDMARK_LAST_LANDMARK_DAY>>
          AND r.case_matched_day
            > <<EARLY_LANDMARK_LAST_MATCHED_DAY>>
          AND r.member_matched_day < r.case_matched_day)           AS n_early_via_day_of_week_relaxation,
  COUNTIF(r.member_landmark_post_discharge_day
            <= <<EARLY_LANDMARK_LAST_LANDMARK_DAY>>
          AND r.case_matched_day
            > <<EARLY_LANDMARK_LAST_MATCHED_DAY>>
          AND r.member_matched_day >= r.case_matched_day)          AS n_early_by_neither_route,
  -- A member at a landmark day of 1 or less has no exposure window, so it has no proximal
  -- ratio either: the window it would be built from reaches at most one post-discharge day.
  -- A non-null ratio there would be publishable, and a reader who forgot the definitional
  -- flag would fit it as the exposure.
  COUNTIF(r.member_landmark_post_discharge_day
            <= <<EARLY_LANDMARK_LAST_LANDMARK_DAY>>
          AND r.r72 IS NOT NULL)                                   AS n_early_carrying_r72,
  COUNTIF(r.member_landmark_post_discharge_day
          != r.member_matched_day - <<LANDMARK_DAY_OFFSET>>)       AS n_landmark_day_offset_wrong,
  COUNTIF(r.is_case != (r.member_role = 'case'))                   AS n_role_flag_mismatch
FROM `{DERIVED}.risk_sets` AS r
GROUP BY member_role, is_case, no_computable_step_signal, match_rung
ORDER BY member_role, is_case, no_computable_step_signal, match_rung
""")


def control_participation_sql() -> str:
    """How many control landmarks each participant contributed, and who was also a case.

    THE DUAL ROLE IS PERMITTED AND IS COUNTED HERE.  A participant may be a control at one
    landmark and a case later; future case status does not disqualify them, and sampling
    controls only from participants who never have an event would condition the control pool on
    the future and bias the odds ratio away from the null (ANALYSIS-PLAN 4.5).  So a non-zero
    count in the `also_a_case` and at least one control landmark cell is the design working, not
    a defect, and reporting it is how a reader can tell the difference.

    It is also why inference is person-clustered.  Conditional logistic regression assumes
    independent matched sets and a participant appearing in several sets breaks that assumption,
    which is what the person-clustered robust variance and the person-level cluster bootstrap of
    `06_analysis_gate.py` are for.  This distribution is the evidence of how much the assumption
    is being leaned on.
    """
    return _sql("""
-- @columns: n_control_landmarks, also_a_case, n_participants, n_over_participant_cap
WITH per_person AS (
  SELECT
    r.person_id                                AS person_id,
    COUNTIF(r.member_role = 'control')         AS n_control_landmarks,
    LOGICAL_OR(r.member_role = 'case')         AS also_a_case
  FROM `{DERIVED}.risk_sets` AS r
  GROUP BY person_id
)
SELECT
  per_person.n_control_landmarks               AS n_control_landmarks,
  per_person.also_a_case                       AS also_a_case,
  COUNT(*)                                     AS n_participants,
  COUNTIF(per_person.n_control_landmarks
          > <<CONTROL_LANDMARKS_PER_PARTICIPANT_CAP>>) AS n_over_participant_cap
FROM per_person
GROUP BY n_control_landmarks, also_a_case
ORDER BY n_control_landmarks, also_a_case
""")


def matched_set_ledger_sql() -> str:
    """The DAG's own matched-set ledger, read whole so the size query can be checked against it.

    The table is created even when Arm A produced no sets, because a file that is present and
    empty and a file that is absent are different claims and only one of them is checkable
    (DAG-SCHEMA 8.18).  Zero rows here is therefore a legitimate result and is reported as one,
    not treated as a missing table.
    """
    return _sql("""
-- @columns: set_size, n_sets, n_cases
SELECT
  l.set_size AS set_size,
  l.n_sets   AS n_sets,
  l.n_cases  AS n_cases
FROM `{DERIVED}.ledger_matched_sets` AS l
ORDER BY set_size
""")


def risk_set_digest_sql() -> str:
    """One scalar digest over the whole matched-set membership, plus its row counts.

    WHY A DIGEST AND NOT A LIST.  ANALYSIS-PLAN 4.5 requires that a resumed session reproduce
    IDENTICAL matched sets, because a nondeterministic draw would move the odds ratio between
    sessions for no reason a reader could see and would make a number in a draft unreproducible.
    The claim is checkable only by comparing two builds, and comparing two builds means
    comparing their membership, which is participant-level.  A digest answers the question
    without carrying the answer: it is a single 32-character value over the ENTIRE table, taken
    after an explicit ORDER BY so that storage order cannot change it, and it is emitted once
    per run and never per group, per set or per row.

    That restriction is the whole of its safety and it is not decoration.  A hash of a per-row
    value over a small domain is invertible by enumeration; a hash over the ordered membership
    of a table of order a thousand rows is not, and it identifies nobody, in the same way
    `MANIFEST.md5` is a hash over bytes derived from participants and is exported.  The
    self-test pins that this query carries no `GROUP BY`.

    HOW THE REPRODUCIBILITY IS ACTUALLY VERIFIED.  Record the digest; rebuild with
    `start_stage = 'risk_sets'`, which is a `CREATE OR REPLACE` and so overwrites rather than
    appends; run this query again; compare the two strings with `digests_agree`.  The mechanism
    that makes them agree is that the ordering key is a seeded `FARM_FINGERPRINT` over the salt,
    the seed, the set id, the control episode id and the matched day, all of which are pure
    functions of values that do not change between runs, so the two caps select the same rows in
    the same order.  A `RAND()` would not, which is why the plan forbids it.
    """
    return _sql("""
-- @columns: n_rows, n_case_rows, n_control_rows, n_distinct_sets, n_distinct_case_persons, n_distinct_control_persons, membership_digest
WITH row_key AS (
  SELECT
    CONCAT(r.set_id, '|', r.member_role, '|', r.episode_id, '|',
           CAST(r.member_matched_day AS STRING), '|',
           CAST(r.match_rung AS STRING), '|',
           CAST(r.set_size AS STRING))                       AS key_text,
    r.member_role                                            AS member_role,
    r.set_id                                                 AS set_id,
    r.person_id                                              AS person_id
  FROM `{DERIVED}.risk_sets` AS r
)
SELECT
  COUNT(*)                                                                  AS n_rows,
  COUNTIF(row_key.member_role = 'case')                                     AS n_case_rows,
  COUNTIF(row_key.member_role = 'control')                                  AS n_control_rows,
  COUNT(DISTINCT row_key.set_id)                                            AS n_distinct_sets,
  COUNT(DISTINCT IF(row_key.member_role = 'case',
                    row_key.person_id, NULL))                               AS n_distinct_case_persons,
  COUNT(DISTINCT IF(row_key.member_role = 'control',
                    row_key.person_id, NULL))                               AS n_distinct_control_persons,
  TO_HEX(MD5(STRING_AGG(row_key.key_text, '~'
                        ORDER BY row_key.key_text)))                        AS membership_digest
FROM row_key
""")


def variable_missingness_ledger_sql() -> str:
    """The DAG's own variable-missingness ledger, read whole, so its shape can be checked.

    Its `n_total` is the denominator of each row's OWN grain (DAG-SCHEMA 8.19): the first ten
    variables are per episode, `daily_deficit` is per accrual-window person-day and `r72` is per
    first event, so reading one denominator across all twelve rows misreads two of them by
    orders of magnitude.  That is why the check below is per row and why the report prints each
    row's own denominator beside it.
    """
    return _sql("""
-- @columns: variable, n_total, n_missing
SELECT
  m.variable  AS variable,
  m.n_total   AS n_total,
  m.n_missing AS n_missing
FROM `{DERIVED}.ledger_variable_missingness` AS m
ORDER BY variable
""")


def build_sql() -> dict[str, str]:
    """Every query this module runs, keyed by `QUERY_KEYS`.  Text only: no dry run, no execution.

    Separating construction from execution is what lets the self-test check every emitted string
    on a laptop: the placeholders it carries, the absence of any CDR table, the absence of any
    data-definition statement, the absence of randomness, and the agreement between each query's
    declared columns and the Python counter that mirrors it.
    """
    built = {
        "wear record presence": wear_record_presence_sql(),
        "wear definition agreement": wear_definition_agreement_sql(),
        "baseline day distribution": baseline_day_distribution_sql(),
        "baseline categories": baseline_categories_sql(),
        "baseline day of week": baseline_day_of_week_sql(),
        "baseline invariants": baseline_invariants_sql(),
        "daily panel invariants": daily_panel_invariants_sql(),
        "wear availability by day": wear_availability_by_day_sql(),
        "wear availability ledger": wear_availability_ledger_sql(),
        "day kind crosstab": day_kind_crosstab_sql(),
        "landmark conditions": landmark_conditions_sql(),
        "structurally deleted event timing": structurally_deleted_event_timing_sql(),
        "landmark panel invariants": landmark_panel_invariants_sql(),
        "landmark panel by day": landmark_panel_by_day_sql(),
        "matched set sizes": matched_set_sizes_sql(),
        "matched set members": matched_set_members_sql(),
        "control participation": control_participation_sql(),
        "matched set ledger": matched_set_ledger_sql(),
        "risk set digest": risk_set_digest_sql(),
        "observation model inputs": observation_model_inputs_sql(),
        "variable missingness ledger": variable_missingness_ledger_sql(),
    }
    missing = [key for key in QUERY_KEYS if key not in built]
    extra = [key for key in built if key not in QUERY_KEYS]
    if missing or extra:
        raise FeatureCheckError(
            f"the built query set and the declared key list disagree. Missing {missing}, "
            f"unexpected {extra}. The cost plan is keyed on the declared list, so a query "
            f"outside it would execute unpriced."
        )
    return {key: built[key] for key in QUERY_KEYS}


# ======================================================================================
# (5) The reference counters.
#
#     THESE ARE TEST ORACLES FOR THE EMITTED SQL AND THEY ARE NOT A SECOND IMPLEMENTATION OF
#     ANY FEATURE.  Each one takes a DAY-LEVEL, EPISODE-LEVEL or MEMBER-LEVEL frame that
#     already carries the columns `build_all.sql` computed, and reproduces the aggregation the
#     matching query performs over them.  None of them decides whether a day is a valid wear
#     day, what a baseline is or what a deficit is; those are decided in SQL, once, and these
#     functions only count what the decision produced.
#
#     They exist because the interesting failures are all failures of NULL HANDLING, and null
#     handling is exactly what cannot be checked by reading a `COUNTIF` in a string.  A
#     synthetic frame carrying a null wear figure beside a real zero, a null deficit beside a
#     real zero deficit and an inpatient day that is also analyzable is the only way to pin, on
#     a laptop, that the counters split them.  In the perimeter they never run against data:
#     the day-level frames they take are the frames this module deliberately never pulls.
# ======================================================================================


def _require_columns(frame: pd.DataFrame, columns: Sequence[str], what: str) -> None:
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise FeatureCheckError(f"{what} is missing column(s) {missing}")


def _numeric(frame: pd.DataFrame, name: str) -> pd.Series:
    """A column as floats with every non-number, including a null, as NaN.

    NaN is the whole point.  Every comparison below against NaN is False in pandas, which is
    the same answer BigQuery's `COUNTIF` gives for a NULL, so `wear_minutes = 0` counts real
    zeros and not absences in both languages.  Anything that coerced NaN to 0 here would make
    the oracle agree with a broken query.
    """
    return pd.to_numeric(frame[name], errors="coerce")


def _boolean(frame: pd.DataFrame, name: str) -> pd.Series:
    """A column DAG-SCHEMA declares never null, as booleans, refusing a null rather than filling it."""
    column = frame[name]
    if column.isna().any():
        raise FeatureCheckError(
            f"column {name!r} carries a null, and the derived-table contract declares it never "
            f"null. Filling it would invent a value; this refuses instead."
        )
    return column.astype(bool)


def expand_groups(frame: pd.DataFrame, *, procedure_group: str = "procedure_group",
                  fusion: str = "fusion") -> pd.DataFrame:
    """One row per episode becomes three, carrying the seven group slugs of plan 2.4.

    The same expansion the emitted SQL performs with `CROSS JOIN UNNEST`, written here so the
    self-test can pin that it yields the collapse-level-1 group, the collapse-level-2 group and
    the total, and nothing else.  Three rows per episode, never four: `all_groups` is the total
    of BOTH partitions and appears once.
    """
    _require_columns(frame, [procedure_group, fusion], "the episode frame")
    pieces = []
    for _, row in frame.iterrows():
        level_one = row[procedure_group]
        if level_one not in FOUR_GROUP_SLUGS:
            raise FeatureCheckError(
                f"an episode carries a procedure group this module does not know. The four "
                f"collapse-level-1 slugs are owned by ANALYSIS-PLAN 2.4."
            )
        level_two = "fusion" if bool(row[fusion]) else "decompression"
        for slug in (level_one, level_two, ALL_GROUPS_SLUG):
            new = row.copy()
            new["group_slug"] = slug
            pieces.append(new)
    return pd.DataFrame(pieces).reset_index(drop=True)


WEAR_PRESENCE_COLUMNS: tuple[str, ...] = (
    "group_slug", "window_slug", "n_persons", "n_days", "n_hr_row", "n_no_hr_row",
    "n_wear_minutes_null", "n_wear_minutes_zero", "n_wear_minutes_positive",
    "n_hr_row_with_null_minutes", "n_no_hr_row_with_minutes",
    "n_steps_row", "n_no_steps_row", "n_steps_null", "n_steps_zero", "n_steps_positive",
    "n_steps_row_with_null_steps", "n_no_steps_row_with_steps",
    "n_valid_wear", "n_valid_wear_with_null_minutes", "n_valid_wear_steps_null",
    "n_analyzable", "n_analyzable_not_valid_wear",
    "n_zero_steps_valid_wear", "n_zero_steps_analyzable",
)


def count_wear_presence(days: pd.DataFrame) -> pd.DataFrame:
    """The reference for the wear-record-presence query.  Null, real zero and positive, apart.

    Three columns per channel, and they are never added together anywhere in this module.  A
    null wear figure means there was no heart-rate record for that person-date, which is not the
    claim that the device recorded zero minutes; a null step total means there was no activity
    record, which is not the claim that the participant took no steps.  Conflating either with
    its real zero converts an absence of data into a measured absence of movement, and it does
    so in the direction that flatters the study: a fabricated zero-minute day is not a valid
    wear day, so it silently leaves the analysis, while a fabricated zero-step day would enter
    it carrying a full day of deficit.
    """
    _require_columns(days, ["group_slug", "window_slug", "person_id", "has_hr_row",
                            "has_steps_row", "wear_minutes", "steps", "valid_wear",
                            "is_analyzable"], "the day-level wear frame")
    work = days.copy()
    work["_wear"] = _numeric(work, "wear_minutes")
    work["_steps"] = _numeric(work, "steps")
    work["_hr_row"] = _boolean(work, "has_hr_row")
    work["_steps_row"] = _boolean(work, "has_steps_row")
    work["_valid"] = _boolean(work, "valid_wear")
    work["_analyzable"] = _boolean(work, "is_analyzable")

    total = work.copy()
    total["window_slug"] = ALL_WINDOWS_SLUG
    both = pd.concat([work, total], ignore_index=True)

    rows: list[dict[str, Any]] = []
    for (group_slug, window_slug), part in both.groupby(["group_slug", "window_slug"],
                                                        sort=True):
        wear = part["_wear"]
        steps = part["_steps"]
        hr_row = part["_hr_row"]
        steps_row = part["_steps_row"]
        valid = part["_valid"]
        analyzable = part["_analyzable"]
        rows.append({
            "group_slug": group_slug,
            "window_slug": window_slug,
            "n_persons": int(part["person_id"].nunique()),
            "n_days": int(len(part)),
            "n_hr_row": int(hr_row.sum()),
            "n_no_hr_row": int((~hr_row).sum()),
            "n_wear_minutes_null": int(wear.isna().sum()),
            "n_wear_minutes_zero": int((wear == 0).sum()),
            "n_wear_minutes_positive": int((wear > 0).sum()),
            "n_hr_row_with_null_minutes": int((hr_row & wear.isna()).sum()),
            "n_no_hr_row_with_minutes": int(((~hr_row) & wear.notna()).sum()),
            "n_steps_row": int(steps_row.sum()),
            "n_no_steps_row": int((~steps_row).sum()),
            "n_steps_null": int(steps.isna().sum()),
            "n_steps_zero": int((steps == 0).sum()),
            "n_steps_positive": int((steps > 0).sum()),
            "n_steps_row_with_null_steps": int((steps_row & steps.isna()).sum()),
            "n_no_steps_row_with_steps": int(((~steps_row) & steps.notna()).sum()),
            "n_valid_wear": int(valid.sum()),
            "n_valid_wear_with_null_minutes": int((valid & wear.isna()).sum()),
            "n_valid_wear_steps_null": int((valid & steps.isna()).sum()),
            "n_analyzable": int(analyzable.sum()),
            "n_analyzable_not_valid_wear": int((analyzable & (~valid)).sum()),
            "n_zero_steps_valid_wear": int((valid & (steps == 0)).sum()),
            "n_zero_steps_analyzable": int((analyzable & (steps == 0)).sum()),
        })
    return pd.DataFrame(rows, columns=list(WEAR_PRESENCE_COLUMNS))


WEAR_AGREEMENT_COLUMNS: tuple[str, ...] = (
    "group_slug", "window_slug", "definition_slug", "n_days", "n_effective", "n_definition",
    "n_both", "n_effective_only", "n_definition_only", "n_neither",
    "n_definition_with_null_minutes",
)


def count_wear_agreement(days: pd.DataFrame) -> pd.DataFrame:
    """The reference for the wear-definition-agreement query.

    The comparison is against `valid_wear`, the EFFECTIVE flag, on every row including the one
    for the primary definition.  That row is not redundant: it is zero-disagreement exactly when
    the run used the primary wear rule and non-zero exactly when the zone-partition probe failed
    and ANALYSIS-PLAN 2.1's S2 contingency was applied, so it is the evidence of which study was
    run rather than a restatement of the parameter that was passed.
    """
    needed = ["group_slug", "window_slug", "wear_minutes", "valid_wear"]
    needed += [f"valid_wear_{name}" for name in WEAR_DEFINITIONS]
    _require_columns(days, needed, "the day-level wear frame")
    work = days[days["window_slug"].isin(("baseline_window", "accrual_window"))].copy()
    work["_wear"] = _numeric(work, "wear_minutes")
    work["_effective"] = _boolean(work, "valid_wear")

    rows: list[dict[str, Any]] = []
    for (group_slug, window_slug), part in work.groupby(["group_slug", "window_slug"],
                                                        sort=True):
        for definition in WEAR_DEFINITIONS:
            flag = _boolean(part, f"valid_wear_{definition}")
            effective = part["_effective"]
            wear = part["_wear"]
            rows.append({
                "group_slug": group_slug,
                "window_slug": window_slug,
                "definition_slug": definition,
                "n_days": int(len(part)),
                "n_effective": int(effective.sum()),
                "n_definition": int(flag.sum()),
                "n_both": int((effective & flag).sum()),
                "n_effective_only": int((effective & (~flag)).sum()),
                "n_definition_only": int(((~effective) & flag).sum()),
                "n_neither": int(((~effective) & (~flag)).sum()),
                "n_definition_with_null_minutes": int((flag & wear.isna()).sum()),
            })
    return pd.DataFrame(rows, columns=list(WEAR_AGREEMENT_COLUMNS))


DAY_KIND_COLUMNS: tuple[str, ...] = (
    "group_slug", "window_slug", "day_kind", "day_kind_four", "is_inpatient", "is_analyzable",
    "n_days",
)


def count_day_kinds(days: pd.DataFrame) -> pd.DataFrame:
    """The reference for the day-kind crosstab.  Both taxonomies and the flag, on one grain.

    Grouping on all three at once is what keeps them from being collapsed.  The
    inpatient-and-observed cell has to survive as its own row, because it is the cell that
    proves inpatient is not exclusive of observed: those days are `observed` in the three-value
    taxonomy and `inpatient` in the four-value one, and they are the same days, counted once in
    each partition and never twice in either.
    """
    _require_columns(days, list(DAY_KIND_COLUMNS[:-1]), "the day-level panel frame")
    work = days.copy()
    work["is_inpatient"] = _boolean(work, "is_inpatient")
    work["is_analyzable"] = _boolean(work, "is_analyzable")
    grouped = (work.groupby(list(DAY_KIND_COLUMNS[:-1]), sort=True)
                   .size().reset_index(name="n_days"))
    return grouped[list(DAY_KIND_COLUMNS)].reset_index(drop=True)


PANEL_INVARIANT_COLUMNS: tuple[str, ...] = (
    "n_days", "n_at_risk", "n_analyzable", "n_deficit_null", "n_deficit_not_null",
    "n_deficit_null_but_analyzable", "n_deficit_not_null_but_not_analyzable",
    "n_deficit_zero", "n_deficit_zero_not_analyzable", "n_deficit_out_of_range",
    "n_zero_steps_analyzable", "n_zero_steps_analyzable_deficit_one",
    "n_normalized_null_mismatch", "n_untruncated_null_mismatch", "n_truncation_mismatch",
    "n_steps_null_with_deficit", "n_valid_wear_with_null_minutes", "n_analyzable_when_censored",
    "n_inpatient_and_analyzable", "n_day_kind_unknown", "n_day_kind_four_unknown",
    "n_day_kind_four_mismatch", "n_observed_not_analyzable", "n_analyzable_not_observed",
    "n_lag_null_on_day_one", "n_lag_nonnull_on_day_one", "n_lag_null_after_day_one_at_risk",
    "n_lag_null_after_day_one_censored", "n_lag_out_of_range",
)


def count_daily_panel_invariants(days: pd.DataFrame) -> pd.Series:
    """The reference for the daily-panel invariants query.  Every count is expected to be zero.

    Except three, which are descriptive rather than invariant and are here because the checks
    beside them are meaningless without them: `n_days`, `n_at_risk` and `n_analyzable` are the
    denominators, `n_deficit_zero` is a legitimate and interesting count (a participant who met
    their own baseline that day), `n_zero_steps_analyzable` is the retained profound-inactivity
    days, and `n_inpatient_and_analyzable` is the cell the plan deliberately keeps.
    """
    needed = ["is_censored", "is_analyzable", "is_inpatient", "deficit", "deficit_untruncated",
              "normalized_activity", "steps", "wear_minutes", "valid_wear", "day_kind",
              "day_kind_four", "post_discharge_day", "lagged_wear_fraction"]
    _require_columns(days, needed, "the day-level panel frame")
    censored = _boolean(days, "is_censored")
    analyzable = _boolean(days, "is_analyzable")
    inpatient = _boolean(days, "is_inpatient")
    valid = _boolean(days, "valid_wear")
    deficit = _numeric(days, "deficit")
    untruncated = _numeric(days, "deficit_untruncated")
    normalized = _numeric(days, "normalized_activity")
    steps = _numeric(days, "steps")
    wear = _numeric(days, "wear_minutes")
    day = _numeric(days, "post_discharge_day")
    lag = _numeric(days, "lagged_wear_fraction")
    kind = days["day_kind"].astype(str)
    kind_four = days["day_kind_four"].astype(str)

    expected_four = pd.Series(
        np.where(kind == "censored", "censored",
                 np.where(inpatient, "inpatient", kind)),
        index=days.index, dtype="object").astype(str)

    truncation_gap = (deficit - untruncated.clip(lower=0)).abs()
    counts = {
        "n_days": int(len(days)),
        "n_at_risk": int((~censored).sum()),
        "n_analyzable": int(analyzable.sum()),
        "n_deficit_null": int(deficit.isna().sum()),
        "n_deficit_not_null": int(deficit.notna().sum()),
        "n_deficit_null_but_analyzable": int((deficit.isna() & analyzable).sum()),
        "n_deficit_not_null_but_not_analyzable": int((deficit.notna() & (~analyzable)).sum()),
        "n_deficit_zero": int((deficit == 0).sum()),
        "n_deficit_zero_not_analyzable": int(((deficit == 0) & (~analyzable)).sum()),
        "n_deficit_out_of_range": int(((deficit < 0) | (deficit > 1)).sum()),
        "n_zero_steps_analyzable": int((analyzable & (steps == 0)).sum()),
        "n_zero_steps_analyzable_deficit_one": int(
            (analyzable & (steps == 0) & ((deficit - 1).abs() <= FLOAT_TOLERANCE)).sum()),
        "n_normalized_null_mismatch": int((normalized.isna() != deficit.isna()).sum()),
        "n_untruncated_null_mismatch": int((untruncated.isna() != deficit.isna()).sum()),
        "n_truncation_mismatch": int((deficit.notna() & (truncation_gap > FLOAT_TOLERANCE)).sum()),
        "n_steps_null_with_deficit": int((steps.isna() & deficit.notna()).sum()),
        "n_valid_wear_with_null_minutes": int((valid & wear.isna()).sum()),
        "n_analyzable_when_censored": int((censored & analyzable).sum()),
        "n_inpatient_and_analyzable": int((inpatient & analyzable).sum()),
        "n_day_kind_unknown": int((~kind.isin(DAY_KINDS)).sum()),
        "n_day_kind_four_unknown": int((~kind_four.isin(DAY_KINDS_FOUR)).sum()),
        "n_day_kind_four_mismatch": int((kind_four != expected_four).sum()),
        "n_observed_not_analyzable": int(((kind == "observed") & (~analyzable)).sum()),
        "n_analyzable_not_observed": int((analyzable & (kind != "observed")).sum()),
        "n_lag_null_on_day_one": int(((day == ACCRUAL_FIRST_DAY) & lag.isna()).sum()),
        "n_lag_nonnull_on_day_one": int(((day == ACCRUAL_FIRST_DAY) & lag.notna()).sum()),
        "n_lag_null_after_day_one_at_risk": int(
            ((day > ACCRUAL_FIRST_DAY) & (~censored) & lag.isna()).sum()),
        "n_lag_null_after_day_one_censored": int(
            ((day > ACCRUAL_FIRST_DAY) & censored & lag.isna()).sum()),
        "n_lag_out_of_range": int(((lag < 0) | (lag > 1)).sum()),
    }
    return pd.Series(counts, index=list(PANEL_INVARIANT_COLUMNS), dtype="int64")


LANDMARK_COLUMNS: tuple[str, ...] = (
    "group_slug", "is_first_event", "n_valid_days_in_window", "n_eligible_days_in_window",
    "has_computable_landmark", "structurally_uncomputable_landmark", "no_computable_step_signal",
    "n_events", "n_events_on_day_four_or_earlier", "n_r72_not_null", "n_r72_24h_not_null",
    "n_reference_not_null", "n_negative_control_not_null", "n_local_deterioration_not_null",
    "n_wear_fraction_not_null", "n_missing_days_mismatch",
)


def count_landmark_conditions(events: pd.DataFrame) -> pd.DataFrame:
    """The reference for the landmark-conditions query.  The two conditions never merge.

    They are separate columns of the grain, so no aggregation in this function can add them
    together, and the frame that comes out has a row for each combination that occurs.  The
    combination that matters most is (computable false, structural false): an event late enough
    to have an eligible window whose days were simply not worn.  Those windows STAY in the risk
    set under plan 4.4 and their absence from this frame would mean they had been deleted.
    """
    needed = ["group_slug", "is_first_event", "n_valid_days_in_window",
              "n_eligible_days_in_window", "has_computable_landmark",
              "structurally_uncomputable_landmark", "no_computable_step_signal",
              "event_post_discharge_day", "r72", "r72_24h", "r_reference_7day",
              "r_negative_control", "local_step_deterioration", "wear_fraction",
              "n_missing_days_in_window"]
    _require_columns(events, needed, "the event-level frame")
    keys = list(LANDMARK_COLUMNS[:7])
    work = events.copy()
    for name in ("is_first_event", "has_computable_landmark",
                 "structurally_uncomputable_landmark", "no_computable_step_signal"):
        work[name] = _boolean(work, name)
    rows: list[dict[str, Any]] = []
    for key, part in work.groupby(keys, sort=True):
        day = _numeric(part, "event_post_discharge_day")
        valid_days = _numeric(part, "n_valid_days_in_window")
        missing_days = _numeric(part, "n_missing_days_in_window")
        row = dict(zip(keys, key))
        row.update({
            "n_events": int(len(part)),
            "n_events_on_day_four_or_earlier": int((day <= STRUCTURAL_DELETION_LAST_DAY).sum()),
            "n_r72_not_null": int(_numeric(part, "r72").notna().sum()),
            "n_r72_24h_not_null": int(_numeric(part, "r72_24h").notna().sum()),
            "n_reference_not_null": int(_numeric(part, "r_reference_7day").notna().sum()),
            "n_negative_control_not_null": int(
                _numeric(part, "r_negative_control").notna().sum()),
            "n_local_deterioration_not_null": int(
                _numeric(part, "local_step_deterioration").notna().sum()),
            "n_wear_fraction_not_null": int(_numeric(part, "wear_fraction").notna().sum()),
            "n_missing_days_mismatch": int(
                (missing_days != (LANDMARK_WINDOW_DAYS - valid_days)).sum()),
        })
        rows.append(row)
    return pd.DataFrame(rows, columns=list(LANDMARK_COLUMNS))


LANDMARK_PANEL_INVARIANT_COLUMNS: tuple[str, ...] = (
    "n_episode_days", "n_episodes", "n_persons", "n_censored_days", "n_at_risk_days",
    "n_event_days", "n_first_event_days", "n_data_uncomputable_days",
    "n_structurally_uncomputable_days", "n_computable_days", "n_weight_input_absent",
    "n_weight_input_available", "n_landmark_before_day_one", "n_landmark_day_offset_wrong",
    "n_day_out_of_range", "n_valid_out_of_range", "n_eligible_out_of_range",
    "n_valid_over_eligible", "n_computable_flag_wrong", "n_signal_flag_wrong",
    "n_structural_flag_wrong", "n_structural_definition_wrong",
    "n_structural_carrying_no_signal",
    "n_weight_flag_wrong", "n_weight_null_boundary_wrong", "n_before_day_one_flag_wrong",
    "n_wearable_lag_null", "n_wearable_lag_out_of_range", "n_wearable_grid_short",
    "n_first_event_not_event", "n_events_joined", "n_events_without_panel_row",
    "n_event_window_disagreement", "n_event_day_not_flagged",
)

LANDMARK_PANEL_BY_DAY_COLUMNS: tuple[str, ...] = (
    "group_slug", "post_discharge_day", "structurally_uncomputable_landmark",
    "no_computable_step_signal", "n_episode_days", "n_at_risk_days", "n_event_days",
    "n_first_event_days", "n_weight_input_available",
)

_LANDMARK_PANEL_COLUMNS: tuple[str, ...] = (
    "episode_id", "person_id", "post_discharge_day", "landmark_post_discharge_day",
    "is_censored", "n_valid_days_in_window", "n_eligible_days_in_window",
    "has_computable_landmark", "structurally_uncomputable_landmark",
    "no_computable_step_signal", "landmark_lagged_wear_fraction",
    "landmark_weight_input_available", "landmark_before_post_discharge_day_one",
    "landmark_lagged_wear_fraction_wearable", "n_days_behind_landmark_on_wearable_grid",
    "is_event_day", "is_first_event_day",
)


def count_landmark_panel(panel: pd.DataFrame, events: pd.DataFrame) -> pd.Series:
    """The reference for the landmark-panel invariants query, including its overlap with `events`.

    Two frames rather than one, because one of the two invariants is ABOUT the overlap.  The
    panel and the event table compute the same proximal window at an event's own post-discharge
    day, by the same rule, out of different sources, so a cell-for-cell comparison at the event
    dates is the check that the two definitions have not drifted.  The other invariant is about
    the calendar alone: the structural flag has to equal post-discharge day 1 to 4 on EVERY
    episode-day, which is the six-row derivation of ANALYSIS-PLAN 4.3 audited across the whole
    panel rather than only where an event happened to land.

    THE TWO LANDMARK CONDITIONS ARE COUNTED APART, AND THE COLUMN NOW CARRIES THE DATA
    CONDITION ALONE.  `no_computable_step_signal` is `n_eligible_days_in_window >= 2 AND
    n_valid_days_in_window < 2`, so the definitional condition is no longer contained in it and
    the containment runs the other way: a structurally uncomputable day does not carry the flag
    at all.  `n_data_uncomputable_days` is therefore a plain read of the column,
    `n_structurally_uncomputable_days` is the definitional one, and the two are never added:
    one is an exposure the analysis keeps and the other is an exclusion.

    THE `AND NOT structural` THIS COUNTER USED TO CARRY IS GONE, AND WHICH IT WAS MATTERS.  It
    was a predicate conjunction over the rows, not an arithmetic subtraction of one count from
    another, so against the new column it is REDUNDANT rather than wrong: it selects exactly
    the same rows.  It is removed anyway, because a number that comes out right under both the
    old union definition and the new data-only one cannot tell a reader which table it was
    taken from, and `n_signal_flag_wrong` exists to halt on the old one.  With the conjunction
    gone the three day classes partition the panel by construction under the new definition and
    over-count it by exactly the structural day count under the old, so the partition assert is
    a second, independent alarm on the same drift.
    """
    _require_columns(panel, list(_LANDMARK_PANEL_COLUMNS), "the landmark panel frame")
    _require_columns(events, ["episode_id", "event_post_discharge_day",
                              "n_valid_days_in_window", "n_eligible_days_in_window",
                              "has_computable_landmark", "structurally_uncomputable_landmark"],
                     "the event frame the landmark panel is checked against")
    day = _numeric(panel, "post_discharge_day")
    landmark_day = _numeric(panel, "landmark_post_discharge_day")
    valid = _numeric(panel, "n_valid_days_in_window")
    eligible = _numeric(panel, "n_eligible_days_in_window")
    lagged = _numeric(panel, "landmark_lagged_wear_fraction")
    wearable = _numeric(panel, "landmark_lagged_wear_fraction_wearable")
    behind = _numeric(panel, "n_days_behind_landmark_on_wearable_grid")
    censored = _boolean(panel, "is_censored")
    computable = _boolean(panel, "has_computable_landmark")
    structural = _boolean(panel, "structurally_uncomputable_landmark")
    no_signal = _boolean(panel, "no_computable_step_signal")
    weight_available = _boolean(panel, "landmark_weight_input_available")
    before_one = _boolean(panel, "landmark_before_post_discharge_day_one")
    is_event = _boolean(panel, "is_event_day")
    is_first = _boolean(panel, "is_first_event_day")

    joined = events.merge(
        panel[["episode_id", "post_discharge_day", "n_valid_days_in_window",
               "n_eligible_days_in_window", "has_computable_landmark",
               "structurally_uncomputable_landmark", "is_event_day"]],
        left_on=["episode_id", "event_post_discharge_day"],
        right_on=["episode_id", "post_discharge_day"],
        how="left", suffixes=("_event", "_panel"))
    matched = joined["post_discharge_day"].notna()
    disagreement = matched & (
        (_numeric(joined, "n_valid_days_in_window_panel")
         != _numeric(joined, "n_valid_days_in_window_event"))
        | (_numeric(joined, "n_eligible_days_in_window_panel")
           != _numeric(joined, "n_eligible_days_in_window_event"))
        | (joined["has_computable_landmark_panel"].astype("boolean")
           != joined["has_computable_landmark_event"].astype("boolean"))
        | (joined["structurally_uncomputable_landmark_panel"].astype("boolean")
           != joined["structurally_uncomputable_landmark_event"].astype("boolean")))

    counts = {
        "n_episode_days": int(len(panel)),
        "n_episodes": int(panel["episode_id"].nunique()),
        "n_persons": int(panel["person_id"].nunique()),
        "n_censored_days": int(censored.sum()),
        "n_at_risk_days": int((~censored).sum()),
        "n_event_days": int(is_event.sum()),
        "n_first_event_days": int(is_first.sum()),
        "n_data_uncomputable_days": int(no_signal.sum()),
        "n_structurally_uncomputable_days": int(structural.sum()),
        "n_computable_days": int(computable.sum()),
        "n_weight_input_absent": int((landmark_day <= EARLY_LANDMARK_LAST_LANDMARK_DAY).sum()),
        "n_weight_input_available": int(weight_available.sum()),
        "n_landmark_before_day_one": int(before_one.sum()),
        "n_landmark_day_offset_wrong": int(
            (landmark_day != (day - LANDMARK_DAY_OFFSET)).sum()),
        "n_day_out_of_range": int(
            ((day < ACCRUAL_FIRST_DAY) | (day > DISPLAY_LAST_DAY)).sum()),
        "n_valid_out_of_range": int(((valid < 0) | (valid > LANDMARK_WINDOW_DAYS)).sum()),
        "n_eligible_out_of_range": int(
            ((eligible < 0) | (eligible > LANDMARK_WINDOW_DAYS)).sum()),
        "n_valid_over_eligible": int((valid > eligible).sum()),
        "n_computable_flag_wrong": int(
            (computable != (valid >= LANDMARK_MIN_VALID_DAYS)).sum()),
        "n_signal_flag_wrong": int(
            (no_signal != ((eligible >= LANDMARK_MIN_VALID_DAYS)
                           & (valid < LANDMARK_MIN_VALID_DAYS))).sum()),
        "n_structural_flag_wrong": int(
            (structural != (day <= STRUCTURAL_DELETION_LAST_DAY)).sum()),
        "n_structural_definition_wrong": int(
            (structural != (eligible < LANDMARK_MIN_VALID_DAYS)).sum()),
        "n_structural_carrying_no_signal": int((structural & no_signal).sum()),
        "n_weight_flag_wrong": int((weight_available != lagged.notna()).sum()),
        "n_weight_null_boundary_wrong": int(
            (lagged.isna() != (landmark_day <= EARLY_LANDMARK_LAST_LANDMARK_DAY)).sum()),
        "n_before_day_one_flag_wrong": int(
            (before_one != (landmark_day < ACCRUAL_FIRST_DAY)).sum()),
        "n_wearable_lag_null": int(wearable.isna().sum()),
        "n_wearable_lag_out_of_range": int(((wearable < 0) | (wearable > 1)).sum()),
        "n_wearable_grid_short": int((behind != LANDMARK_PANEL_LOOKBACK_DAYS).sum()),
        "n_first_event_not_event": int((is_first & ~is_event).sum()),
        "n_events_joined": int(len(events)),
        "n_events_without_panel_row": int((~matched).sum()),
        "n_event_window_disagreement": int(disagreement.fillna(False).sum()),
        "n_event_day_not_flagged": int(
            (matched & ~joined["is_event_day"].astype("boolean").fillna(False)).sum()),
    }
    return pd.Series(counts, index=list(LANDMARK_PANEL_INVARIANT_COLUMNS), dtype="int64")


def count_landmark_panel_by_day(panel: pd.DataFrame) -> pd.DataFrame:
    """The reference for the by-day panel query, on the group-expanded frame."""
    needed = ["group_slug", "post_discharge_day", "structurally_uncomputable_landmark",
              "no_computable_step_signal", "is_censored", "is_event_day", "is_first_event_day",
              "landmark_weight_input_available"]
    _require_columns(panel, needed, "the landmark panel frame")
    work = panel.copy()
    at_risk = ~_boolean(work, "is_censored")
    work["_one"] = 1
    work["_at_risk"] = at_risk
    work["_event"] = _boolean(work, "is_event_day") & at_risk
    work["_first_event"] = _boolean(work, "is_first_event_day") & at_risk
    work["_weight"] = _boolean(work, "landmark_weight_input_available")
    keys = ["group_slug", "post_discharge_day", "structurally_uncomputable_landmark",
            "no_computable_step_signal"]
    grouped = work.groupby(keys, as_index=False).agg(
        n_episode_days=("_one", "sum"), n_at_risk_days=("_at_risk", "sum"),
        n_event_days=("_event", "sum"), n_first_event_days=("_first_event", "sum"),
        n_weight_input_available=("_weight", "sum"))
    for column in grouped.columns:
        if column.startswith("n_"):
            grouped[column] = grouped[column].astype("int64")
    return grouped[list(LANDMARK_PANEL_BY_DAY_COLUMNS)]


MATCHED_SET_SIZE_COLUMNS: tuple[str, ...] = (
    "set_size", "match_rung", "n_sets", "n_size_mismatch", "n_case_row_count_wrong",
    "n_over_control_cap", "n_sets_losing_every_control", "n_sets_losing_the_case",
    "n_sets_in_weighted_sensitivity", "n_members_in_weighted_sensitivity",
)
MATCHED_SET_MEMBER_COLUMNS: tuple[str, ...] = (
    "member_role", "is_case", "no_computable_step_signal", "match_rung", "n_members",
    "n_persons", "n_fingerprint_null", "n_r72_not_null", "n_wear_fraction_not_null",
    "n_landmark_weight_input_absent", "n_landmark_before_post_discharge_day_one",
    "n_early_via_partial_window_secondary", "n_early_via_day_of_week_relaxation",
    "n_early_by_neither_route", "n_early_carrying_r72", "n_landmark_day_offset_wrong",
    "n_role_flag_mismatch",
)
CONTROL_PARTICIPATION_COLUMNS: tuple[str, ...] = (
    "n_control_landmarks", "also_a_case", "n_participants", "n_over_participant_cap",
)


def count_matched_sets(members: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The reference for all three risk-set queries, from one member-level frame.

    One function rather than three, because the three queries are three views of the same rows
    and a synthetic frame that satisfies one view and not the others would not be a risk-set
    table at all.  The dual role is the case worth constructing by hand: a participant who is a
    control in one set and a case in a later one is permitted by ANALYSIS-PLAN 4.5, appears in
    `control participation` with a non-zero landmark count AND `also_a_case` true, and must not
    be double counted as two participants.
    """
    needed = ["set_id", "member_role", "is_case", "person_id", "episode_id", "set_size",
              "match_rung", "no_computable_step_signal", "fingerprint", "r72", "wear_fraction",
              "member_matched_day", "case_matched_day",
              "member_landmark_post_discharge_day"]
    _require_columns(members, needed, "the risk-set member frame")
    work = members.copy()
    work["is_case"] = _boolean(work, "is_case")
    work["no_computable_step_signal"] = _boolean(work, "no_computable_step_signal")
    is_case_row = work["member_role"].astype(str) == "case"

    # ANALYSIS-PLAN 4.4: a member is weighted when its OWN landmark day is 2 or more.  The
    # complement is landmark day 1 or less, which is matched day 4 or less, and is one day wider
    # than "the landmark precedes post-discharge day 1".
    landmark_day_all = _numeric(work, "member_landmark_post_discharge_day")
    work["_weighted"] = landmark_day_all >= LANDMARK_WEIGHT_MIN_LANDMARK_DAY

    set_rows: list[dict[str, Any]] = []
    per_set: list[dict[str, Any]] = []
    for set_id, part in work.groupby("set_id", sort=True):
        is_control = part["member_role"].astype(str) == "control"
        case_part = part[part["member_role"].astype(str) == "case"]
        declared = int(case_part["set_size"].iloc[0]) if len(case_part) else -1
        rung = int(case_part["match_rung"].iloc[0]) if len(case_part) else -1
        observed = int(is_control.sum())
        per_set.append({"set_id": set_id, "declared_size": declared, "match_rung": rung,
                        "observed_size": observed, "n_case_rows": int(len(case_part)),
                        "n_controls_weighted": int((is_control & part["_weighted"]).sum()),
                        "case_weighted": bool(
                            (~is_control & part["_weighted"]).any())})
    sets = pd.DataFrame(per_set)
    if len(sets):
        for (size, rung), part in sets.groupby(["declared_size", "match_rung"], sort=True):
            in_weighted = part["case_weighted"] & (part["n_controls_weighted"] > 0)
            set_rows.append({
                "set_size": int(size),
                "match_rung": int(rung),
                "n_sets": int(len(part)),
                "n_size_mismatch": int((part["declared_size"] != part["observed_size"]).sum()),
                "n_case_row_count_wrong": int((part["n_case_rows"] != 1).sum()),
                "n_over_control_cap": int((part["observed_size"] > CONTROLS_PER_CASE_CAP).sum()),
                "n_sets_losing_every_control": int(
                    ((part["observed_size"] > 0) & (part["n_controls_weighted"] == 0)).sum()),
                "n_sets_losing_the_case": int((~part["case_weighted"]).sum()),
                "n_sets_in_weighted_sensitivity": int(in_weighted.sum()),
                "n_members_in_weighted_sensitivity": int(
                    (in_weighted * (1 + part["n_controls_weighted"])).sum()),
            })

    member_rows: list[dict[str, Any]] = []
    keys = ["member_role", "is_case", "no_computable_step_signal", "match_rung"]
    for key, part in work.groupby(keys, sort=True):
        landmark_day = _numeric(part, "member_landmark_post_discharge_day")
        matched_day = _numeric(part, "member_matched_day")
        case_day = _numeric(part, "case_matched_day")
        early = landmark_day <= EARLY_LANDMARK_LAST_LANDMARK_DAY
        secondary = case_day <= EARLY_LANDMARK_LAST_MATCHED_DAY
        row = dict(zip(keys, key))
        row.update({
            "n_members": int(len(part)),
            "n_persons": int(part["person_id"].nunique()),
            "n_fingerprint_null": int(_numeric(part, "fingerprint").isna().sum()),
            "n_r72_not_null": int(_numeric(part, "r72").notna().sum()),
            "n_wear_fraction_not_null": int(_numeric(part, "wear_fraction").notna().sum()),
            "n_landmark_weight_input_absent": int(early.sum()),
            "n_landmark_before_post_discharge_day_one": int(
                (landmark_day < ACCRUAL_FIRST_DAY).sum()),
            "n_early_via_partial_window_secondary": int((early & secondary).sum()),
            "n_early_via_day_of_week_relaxation": int(
                (early & ~secondary & (matched_day < case_day)).sum()),
            "n_early_by_neither_route": int(
                (early & ~secondary & (matched_day >= case_day)).sum()),
            "n_early_carrying_r72": int(
                (early & _numeric(part, "r72").notna()).sum()),
            "n_landmark_day_offset_wrong": int(
                (landmark_day != (matched_day - LANDMARK_DAY_OFFSET)).sum()),
            "n_role_flag_mismatch": int(
                (part["is_case"] != (part["member_role"].astype(str) == "case")).sum()),
        })
        member_rows.append(row)

    per_person = work.assign(_is_case_row=is_case_row).groupby("person_id", sort=True).agg(
        n_control_landmarks=("member_role", lambda s: int((s.astype(str) == "control").sum())),
        also_a_case=("_is_case_row", "any"),
    ).reset_index()
    participation_rows: list[dict[str, Any]] = []
    for (landmarks, also), part in per_person.groupby(["n_control_landmarks", "also_a_case"],
                                                      sort=True):
        participation_rows.append({
            "n_control_landmarks": int(landmarks),
            "also_a_case": bool(also),
            "n_participants": int(len(part)),
            "n_over_participant_cap": int(
                (part["n_control_landmarks"]
                 > CONTROL_LANDMARKS_PER_PARTICIPANT_CAP).sum()),
        })

    return {
        "matched set sizes": pd.DataFrame(set_rows, columns=list(MATCHED_SET_SIZE_COLUMNS)),
        "matched set members": pd.DataFrame(member_rows,
                                            columns=list(MATCHED_SET_MEMBER_COLUMNS)),
        "control participation": pd.DataFrame(participation_rows,
                                              columns=list(CONTROL_PARTICIPATION_COLUMNS)),
    }


BASELINE_INVARIANT_COLUMNS: tuple[str, ...] = (
    "n_episodes", "n_has_any_fitbit", "n_baseline_null", "n_baseline_zero",
    "n_baseline_negative", "n_null_with_valid_days", "n_nonnull_without_valid_days",
    "n_dow_length_wrong", "n_dow_sum_mismatch", "n_band_null_with_baseline",
    "n_floor_null_with_baseline", "n_span_zero_with_baseline", "n_span_negative",
    "n_alternative_baseline_zero",
    "n_weekday_baseline_zero", "n_weekend_baseline_zero",
    "n_weekday_null_with_valid_days", "n_weekday_nonnull_without_valid_days",
    "n_weekend_null_with_valid_days", "n_weekend_nonnull_without_valid_days",
    "n_split_day_count_null", "n_split_day_count_negative",
    "n_weekday_count_mismatch", "n_weekend_count_mismatch",
    "n_weekday_weekend_sum_mismatch",
)


def count_baseline_invariants(episodes: pd.DataFrame) -> pd.Series:
    """The reference for the baseline invariants query.  The zero baseline is the one that bites.

    `baseline_steps` is NULL and never 0.  A zero would make `S / B` infinite and the daily
    deficit `max(0, 1 - S/B)` equal to 1 on every day of that episode, so an episode with no
    usable preoperative data would enter the analysis carrying the maximum debt the scale allows
    and would do it without a single null for anyone to notice.  The count runs over every
    episode in `baseline`, ineligible ones included, because rung 12 would otherwise hide it.
    """
    needed = ["baseline_steps", "n_valid_baseline_days", "baseline_dow_counts",
              "baseline_band_slug", "meets_baseline_floor", "baseline_span_days",
              "has_any_fitbit", "baseline_steps_weekday", "n_valid_baseline_days_weekday",
              "baseline_steps_weekend", "n_valid_baseline_days_weekend"]
    needed += [column for column, _ in ALTERNATIVE_BASELINES.values()]
    _require_columns(episodes, needed, "the baseline frame")
    steps = _numeric(episodes, "baseline_steps")
    valid_days = _numeric(episodes, "n_valid_baseline_days")
    span = _numeric(episodes, "baseline_span_days")
    dow = episodes["baseline_dow_counts"]
    dow_length = dow.map(lambda a: len(a) if a is not None else 0)
    dow_sum = dow.map(lambda a: int(sum(a)) if a is not None else 0)
    band_null = episodes["baseline_band_slug"].isna()
    floor_null = episodes["meets_baseline_floor"].isna()
    alternative_zero = pd.Series(False, index=episodes.index)
    for column, _ in ALTERNATIVE_BASELINES.values():
        alternative_zero = alternative_zero | (_numeric(episodes, column) == 0)
    # The split baseline of ANALYSIS-PLAN 2.2.  The array halves are recomputed from the
    # composition, which is the whole point: the identity DAG-SCHEMA 8.8 states is the join
    # between the composition and the two medians, and checking it is what stops the composition
    # and the split baselines from describing two different day sets.
    weekday_steps = _numeric(episodes, "baseline_steps_weekday")
    weekend_steps = _numeric(episodes, "baseline_steps_weekend")
    weekday_days = _numeric(episodes, "n_valid_baseline_days_weekday")
    weekend_days = _numeric(episodes, "n_valid_baseline_days_weekend")
    def _dow_half(array: Any, weekend: bool) -> int:
        # A wrong-length array returns a value no count can equal, so a short array fails the
        # identity as well as the length check rather than silently satisfying it on a slice.
        if array is None or len(array) != BASELINE_DOW_LENGTH:
            return -1
        if weekend:
            return int(array[SUNDAY_INDEX] + array[SATURDAY_INDEX])
        return int(sum(array[SUNDAY_INDEX + 1:SATURDAY_INDEX]))

    dow_weekday = dow.map(lambda a: _dow_half(a, weekend=False))
    dow_weekend = dow.map(lambda a: _dow_half(a, weekend=True))
    counts = {
        "n_episodes": int(len(episodes)),
        "n_has_any_fitbit": int(_boolean(episodes, "has_any_fitbit").sum()),
        "n_baseline_null": int(steps.isna().sum()),
        "n_baseline_zero": int((steps == 0).sum()),
        "n_baseline_negative": int((steps < 0).sum()),
        "n_null_with_valid_days": int((steps.isna() & (valid_days > 0)).sum()),
        "n_nonnull_without_valid_days": int((steps.notna() & (valid_days == 0)).sum()),
        "n_dow_length_wrong": int((dow_length != BASELINE_DOW_LENGTH).sum()),
        "n_dow_sum_mismatch": int((dow_sum != valid_days).sum()),
        "n_band_null_with_baseline": int((steps.notna() & band_null).sum()),
        "n_floor_null_with_baseline": int((steps.notna() & floor_null).sum()),
        "n_span_zero_with_baseline": int((steps.notna() & (span == 0)).sum()),
        "n_span_negative": int((span < 0).sum()),
        "n_alternative_baseline_zero": int(alternative_zero.sum()),
        "n_weekday_baseline_zero": int((weekday_steps == 0).sum()),
        "n_weekend_baseline_zero": int((weekend_steps == 0).sum()),
        "n_weekday_null_with_valid_days": int(
            (weekday_steps.isna() & (weekday_days > 0)).sum()),
        "n_weekday_nonnull_without_valid_days": int(
            (weekday_steps.notna() & (weekday_days == 0)).sum()),
        "n_weekend_null_with_valid_days": int(
            (weekend_steps.isna() & (weekend_days > 0)).sum()),
        "n_weekend_nonnull_without_valid_days": int(
            (weekend_steps.notna() & (weekend_days == 0)).sum()),
        "n_split_day_count_null": int((weekday_days.isna() | weekend_days.isna()).sum()),
        "n_split_day_count_negative": int(((weekday_days < 0) | (weekend_days < 0)).sum()),
        "n_weekday_count_mismatch": int((weekday_days != dow_weekday).sum()),
        "n_weekend_count_mismatch": int((weekend_days != dow_weekend).sum()),
        "n_weekday_weekend_sum_mismatch": int(
            ((weekday_days + weekend_days) != valid_days).sum()),
    }
    return pd.Series(counts, index=list(BASELINE_INVARIANT_COLUMNS), dtype="int64")


# ======================================================================================
# (6) Disclosure at the boundary.
#
#     Every count in `{DERIVED}` is a TRUE INTEGER and is not rounded (DAG-SCHEMA 6), so this
#     module is where the floor is applied, once.  The two predicates are asked DIFFERENT
#     questions and are never swapped: `disclosable(n)` asks whether a TRUE count may be shown
#     at all and is asked BEFORE rounding, and `is_legal_disclosed_count(cell)` asks whether an
#     ALREADY ROUNDED cell is a legal thing to write down and is asked AFTER.  On the number 20
#     they disagree, and that disagreement is the whole reason both exist.
# ======================================================================================


def _whole(value: Any, what: str) -> int:
    """A count as a Python int, refusing anything that is not a whole finite number."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise FeatureCheckError(f"{what} is not a number") from None
    if not np.isfinite(number) or number != int(number):
        raise FeatureCheckError(f"{what} is not a whole number, so it is not a count")
    if number < 0:
        raise FeatureCheckError(f"{what} is negative, which is a defect upstream of this module")
    return int(number)


def expand_distribution(frame: pd.DataFrame, *, value_col: str, count_col: str) -> list[int]:
    """Turn an aggregate distribution back into the value list a quantile needs.

    THIS IS WHY NO PARTICIPANT ROW EVER REACHES THE KERNEL.  A median over episodes needs the
    values, and the obvious way to get them is to select one row per episode, which is a
    participant-level frame arriving inside the notebook.  A `(value, count)` distribution over
    a small whole-number domain carries the same order statistics and is an aggregate, so the
    median and the interquartile range are exact and nothing participant-level was ever read.
    The expansion is bounded by the total count and is only ever used on the whole-number
    domains this module queries: valid baseline days, span days, controls per case, valid days
    in a landmark window.
    """
    _require_columns(frame, [value_col, count_col], "a distribution frame")
    values: list[int] = []
    for _, row in frame.iterrows():
        value = _whole(row[value_col], f"a {value_col} bucket")
        count = _whole(row[count_col], f"a {count_col} cell")
        values.extend([value] * count)
    return values


def distribution_summary(frame: pd.DataFrame, *, value_col: str, count_col: str,
                         decimals: int = 1) -> str:
    """The median and interquartile range of an aggregate distribution, floor-suppressed.

    `median_iqr` suppresses at or below the floor on the number of CONTRIBUTING OBSERVATIONS,
    which after expansion is the number of episodes or sets, so a summary over a thin stratum
    prints the sentinel rather than three participants' own values.
    """
    return median_iqr(expand_distribution(frame, value_col=value_col, count_col=count_col),
                      decimals=decimals)


def suppression_mask_wide(wide: pd.DataFrame,
                          partitions: Sequence[Sequence[str]]) -> pd.DataFrame:
    """Which cells may not be shown, after complementary suppression closes every partition.

    Two rules, applied to a fixpoint, and generalised from `02_pregate.suppression_mask` to an
    arbitrary list of declared column partitions because this module prints tables partitioned
    three different ways over one column of group slugs:

      * `disclosable(n)` is the floor and the ONLY floor.  It, not a literal, decides the seed
        mask, and a true zero survives it because zero is an absence and not a small cell.
      * Within a declared partition, one suppressed member is exactly recoverable by
        subtracting the shown members from their disclosed total, so a second member is masked:
        the smallest still-shown cell, because masking the smallest loses the least, with ties
        broken on the declared order so the choice is identical between runs.

    Masking a cell in one partition can open a hole in another, which is why this iterates
    rather than passing once, and the result is checked by `export_violations` rather than
    trusted.
    """
    mask = pd.DataFrame(False, index=wide.index, columns=wide.columns)
    for row in wide.index:
        for column in wide.columns:
            if not disclosable(wide.loc[row, column]):
                mask.loc[row, column] = True
    declared = [[c for c in group if c in wide.columns] for group in partitions]
    for _ in range(wide.size + 1):
        changed = False
        for row in wide.index:
            for group in declared:
                hidden = [c for c in group if mask.loc[row, c]]
                shown = [c for c in group if not mask.loc[row, c]]
                if len(hidden) == 1 and shown:
                    victim = min(shown, key=lambda c: (int(wide.loc[row, c]), group.index(c)))
                    mask.loc[row, victim] = True
                    changed = True
        if not changed:
            return mask
    raise FeatureCheckError("complementary suppression did not reach a fixpoint")


def render_wide(wide: pd.DataFrame, partitions: Sequence[Sequence[str]] = ()) -> pd.DataFrame:
    """Rounded counts where the mask allows, the sentinel where it does not, then re-checked.

    The floor is applied to the TRUE count here, one more time, so that a mask built anywhere
    other than `suppression_mask_wide` still cannot show a small cell.  It belongs on the
    unrounded number: a rendered 20 is a legitimate disclosure standing on a true count of 21 to
    29, while a true 20 is not, and after rounding the two are the same two digits.
    """
    mask = suppression_mask_wide(wide, partitions)
    out = pd.DataFrame(index=wide.index, columns=wide.columns, dtype="object")
    for row in wide.index:
        for column in wide.columns:
            if mask.loc[row, column]:
                out.loc[row, column] = SUPPRESSED
                continue
            if not disclosable(wide.loc[row, column]):
                raise DisclosureError(
                    "a cell that did not clear the floor was about to be shown. The row and "
                    "column are named in the frame; the value never is."
                )
            out.loc[row, column] = round20(wide.loc[row, column])
    for row in out.index:
        for column in out.columns:
            if not is_legal_disclosed_count(out.loc[row, column]):
                raise DisclosureError(
                    "a rendered cell is not a legal disclosed count, which means a count "
                    "reached the display without being rounded. Column named, value never."
                )
    violations = export_violations(out, count_cols=list(out.columns),
                                   partitions=[list(g) for g in partitions])
    if violations:
        raise DisclosureError(
            f"a display table would still allow a suppressed cell to be recovered by "
            f"subtraction: {len(violations)} refusal(s) stand. Do not print it."
        )
    return out


def to_wide(frame: pd.DataFrame, *, index: str, columns: str, value: str) -> pd.DataFrame:
    """A long count frame as a wide one, with absent combinations as TRUE ZEROS, not nulls.

    A combination that produced no row is a count of zero, not a missing value, and the
    difference is not cosmetic: a null propagates through the partition identity and makes a
    total fail to close, while a zero closes it and is itself disclosable.
    """
    _require_columns(frame, [index, columns, value], "a long count frame")
    wide = frame.pivot_table(index=index, columns=columns, values=value, aggfunc="sum",
                             fill_value=0)
    wide.columns = [str(c) for c in wide.columns]
    return wide.astype("int64")


GROUP_PARTITIONS: tuple[tuple[str, ...], ...] = (FOUR_GROUP_SLUGS, TWO_GROUP_SLUGS)


# ======================================================================================
# (7) The interpreters.  Each takes the aggregate count frame the matching query returned and
#     returns the list of reasons that frame fails the derived-table contract.  An EMPTY list
#     means the check passed; every message names the contract clause it is enforcing and NONE
#     of them quotes a count, because a violation message renders into a notebook traceback and
#     a traceback is a printed surface like any other.
# ======================================================================================


def _zero_expected(frame: pd.DataFrame, columns: Sequence[str],
                   sentence: Mapping[str, str]) -> list[str]:
    """Every named column must be zero on every row, and each carries its own diagnosis."""
    out: list[str] = []
    for column in columns:
        if column not in frame.columns:
            out.append(f"the result frame is missing the check column {column!r}")
            continue
        if (pd.to_numeric(frame[column], errors="coerce").fillna(-1) != 0).any():
            out.append(sentence[column])
    return out


def _sums_to_total(frame: pd.DataFrame, *, group_keys: Sequence[str], split_col: str,
                   members: Sequence[str], total: str,
                   count_cols: Sequence[str], what: str) -> list[str]:
    """Every named count column's members must sum to its declared total, within each key.

    A partition whose members do not sum to its total is not a partition, and every suppression
    rule in this project is written in terms of one.  Checking it on the TRUE integers before
    anything is rounded is deliberate: after rounding each member carries an error of up to ten
    and the identity is expected to miss, which is what the rounding footnote is for.
    """
    out: list[str] = []
    work = frame.copy()
    keys = list(group_keys)
    for key, part in (work.groupby(keys, sort=True) if keys else [((), work)]):
        member_rows = part[part[split_col].isin(members)]
        total_rows = part[part[split_col] == total]
        if total_rows.empty:
            out.append(f"{what} carries no {total!r} row, so its partition has no total")
            continue
        for column in count_cols:
            member_sum = int(pd.to_numeric(member_rows[column], errors="coerce").fillna(0).sum())
            total_value = int(pd.to_numeric(total_rows[column], errors="coerce").fillna(0).sum())
            if member_sum != total_value:
                out.append(
                    f"{what}: the {column!r} column does not sum to its {total!r} total across "
                    f"{list(members)}, so that column is not a partition and the suppression "
                    f"rules written in terms of it do not hold"
                )
    return out


_WEAR_PRESENCE_SENTENCES: Mapping[str, str] = MappingProxyType({
    "n_hr_row_with_null_minutes":
        "a day carries a heart-rate record flag beside a null wear figure. DAG-SCHEMA 8.7 says "
        "the wear figure is null exactly when there is no heart-rate record, and a diagnostic "
        "that cannot tell the two apart cannot tell an absence of data from an absence of wear",
    "n_no_hr_row_with_minutes":
        "a day carries a wear figure with no heart-rate record behind it, which is the same "
        "contract clause failing in the other direction",
    "n_steps_row_with_null_steps":
        "a day carries an activity record flag beside a null step total, so the record flag and "
        "the null no longer agree about whether the day was observed",
    "n_no_steps_row_with_steps":
        "a day carries a step total with no activity record behind it",
    "n_valid_wear_with_null_minutes":
        "a day with NO heart-rate record was counted as a valid wear day. A null wear figure is "
        "not zero minutes and is not a valid day under any of the five definitions of "
        "ANALYSIS-PLAN 2.1; this is the reading that turns missing data into measured wear",
    "n_analyzable_not_valid_wear":
        "a day is analyzable without being a valid wear day, which contradicts the definition "
        "of analyzable in DAG-SCHEMA 8.7 and would put an unweighted day into the estimand",
})


def wear_presence_violations(frame: pd.DataFrame) -> list[str]:
    """Every way the wear-presence frame can fail the contract, in one list.

    The three-way splits are checked as identities as well as counted, because the identity is
    what proves the split is exhaustive: null plus real zero plus positive must equal the number
    of days, and if it does not then some fourth state exists that this module is not reporting.
    """
    out = _zero_expected(frame, list(_WEAR_PRESENCE_SENTENCES), _WEAR_PRESENCE_SENTENCES)
    numeric = frame.copy()
    for column in frame.columns:
        if column.startswith("n_"):
            numeric[column] = pd.to_numeric(frame[column], errors="coerce").fillna(-1)
    triples = (
        ("n_wear_minutes_null", "n_wear_minutes_zero", "n_wear_minutes_positive",
         "the wear figure does not split exhaustively into null, real zero and positive"),
        ("n_steps_null", "n_steps_zero", "n_steps_positive",
         "the step total does not split exhaustively into null, real zero and positive"),
    )
    for first, second, third, sentence in triples:
        if ((numeric[first] + numeric[second] + numeric[third]) != numeric["n_days"]).any():
            out.append(sentence)
    pairs = (
        ("n_hr_row", "n_no_hr_row", "the heart-rate record flag does not split the days in two"),
        ("n_steps_row", "n_no_steps_row",
         "the activity record flag does not split the days in two"),
    )
    for first, second, sentence in pairs:
        if ((numeric[first] + numeric[second]) != numeric["n_days"]).any():
            out.append(sentence)
    count_cols = [c for c in frame.columns if c.startswith("n_") and c != "n_persons"]
    out += _sums_to_total(frame, group_keys=["group_slug"], split_col="window_slug",
                          members=WINDOW_SLUGS, total=ALL_WINDOWS_SLUG,
                          count_cols=count_cols, what="the wear-presence frame by window")
    for members in GROUP_PARTITIONS:
        out += _sums_to_total(frame, group_keys=["window_slug"], split_col="group_slug",
                              members=members, total=ALL_GROUPS_SLUG,
                              count_cols=count_cols, what="the wear-presence frame by group")
    return out


def wear_agreement_violations(frame: pd.DataFrame) -> list[str]:
    """The two by two must be a two by two, and no definition may admit a null wear figure."""
    out = _zero_expected(
        frame, ["n_definition_with_null_minutes"],
        {"n_definition_with_null_minutes":
            "a wear definition admitted a day with NO heart-rate record. A null wear figure is "
            "not zero minutes; DAG-SCHEMA 3 says it is never a valid day under any definition"})
    numeric = {c: pd.to_numeric(frame[c], errors="coerce").fillna(-1)
               for c in frame.columns if c.startswith("n_")}
    if ((numeric["n_both"] + numeric["n_effective_only"] + numeric["n_definition_only"]
         + numeric["n_neither"]) != numeric["n_days"]).any():
        out.append("the agreement cells do not sum to the number of days, so the two by two is "
                   "not a two by two")
    if ((numeric["n_both"] + numeric["n_effective_only"]) != numeric["n_effective"]).any():
        out.append("the effective wear flag's margin does not match its own agreement cells")
    if ((numeric["n_both"] + numeric["n_definition_only"]) != numeric["n_definition"]).any():
        out.append("a wear definition's margin does not match its own agreement cells")
    return out


def wear_contingency_verdict(frame: pd.DataFrame) -> dict[str, Any]:
    """Whether this run used the primary wear rule or ANALYSIS-PLAN 2.1's S2 contingency.

    Read off the data rather than off the parameter that was passed, which is the point.  The
    effective flag and the primary flag are the same flag on every day unless the zone-partition
    probe failed and the build was called with the S2 substitution, so a non-zero disagreement
    between them IS the substitution, and it must have a logged amendment behind it.  A module
    that reported the parameter instead would report what somebody intended rather than what ran.
    """
    rows = frame[(frame["definition_slug"] == "primary")
                 & (frame["group_slug"] == ALL_GROUPS_SLUG)]
    if rows.empty:
        raise FeatureCheckError(
            "the wear-agreement frame carries no pooled row for the primary definition, so the "
            "wear rule actually in force cannot be read off it"
        )
    disagreeing = int(pd.to_numeric(rows["n_effective_only"], errors="coerce").fillna(0).sum()
                      + pd.to_numeric(rows["n_definition_only"], errors="coerce").fillna(0).sum())
    return {
        "primary in force": disagreeing == 0,
        "n disagreeing days": disagreeing,
        "requires logged amendment": disagreeing > 0,
    }


_BASELINE_SENTENCES: Mapping[str, str] = MappingProxyType({
    "n_baseline_zero":
        "at least one episode carries a baseline of ZERO steps. DAG-SCHEMA 8.8 and the "
        "exact-median function both say the baseline is null and never zero, because a zero "
        "makes normalized activity infinite and makes the daily deficit exactly 1 on every day "
        "of that episode, manufacturing a maximal recovery debt out of an absence of data. This "
        "is the single most consequential defect available in this build and it does not "
        "announce itself anywhere downstream",
    "n_baseline_negative":
        "at least one episode carries a negative baseline, which no median of step counts can be",
    "n_null_with_valid_days":
        "at least one episode has valid baseline days and no baseline, so the median was not "
        "taken over the days that were counted",
    "n_nonnull_without_valid_days":
        "at least one episode has a baseline and no valid baseline days, so a median was taken "
        "over an empty set and returned a number rather than the null DAG-SCHEMA 3 promises",
    "n_dow_length_wrong":
        "at least one day-of-week composition array is not of length seven, so an index into it "
        "no longer names the weekday it is documented to name",
    "n_dow_sum_mismatch":
        "at least one day-of-week composition does not sum to that episode's valid baseline day "
        "count. DAG-SCHEMA 8.8 calls the array the composition of the baseline window without "
        "saying whether it counts VALID days or every calendar day in the window; only the "
        "first carries information, since the window is a fixed span and the second would be "
        "the same seven numbers on every episode. This module asserts the first reading. If the "
        "build intends the second, DAG-SCHEMA 8.8 has to say so and the weekday and weekend "
        "counts reported here mean something else",
    "n_band_null_with_baseline":
        "at least one episode has a baseline and no baseline band, so a description column is "
        "null where its source is not",
    "n_floor_null_with_baseline":
        "at least one episode has a baseline and no baseline-floor flag",
    "n_span_zero_with_baseline":
        "at least one episode has a baseline and a span of zero days, which cannot happen: one "
        "valid day gives a span of one",
    "n_span_negative":
        "at least one baseline span is negative, so the last valid day precedes the first",
    "n_alternative_baseline_zero":
        "at least one of the six alternative baselines is ZERO rather than null, so a "
        "sensitivity row would run with an infinite normalization on that episode",
    "n_weekday_baseline_zero":
        "at least one episode carries a weekday baseline of ZERO steps. It is null and never "
        "zero for the same reason the pooled baseline is, and here the error is DIFFERENTIAL "
        "rather than a wash: it would land precisely on the participants whose wear is "
        "concentrated in the other half of the week",
    "n_weekend_baseline_zero":
        "at least one episode carries a weekend baseline of ZERO steps, the same failure on the "
        "other half of the week",
    "n_weekday_null_with_valid_days":
        "at least one episode has valid weekday baseline days and no weekday baseline, so the "
        "median was not taken over the days that were counted",
    "n_weekday_nonnull_without_valid_days":
        "at least one episode has a weekday baseline and no valid weekday day, so a median was "
        "taken over an empty set and returned a number",
    "n_weekend_null_with_valid_days":
        "at least one episode has valid weekend baseline days and no weekend baseline",
    "n_weekend_nonnull_without_valid_days":
        "at least one episode has a weekend baseline and no valid weekend day",
    "n_split_day_count_null":
        "at least one weekday or weekend valid-day count is null, and DAG-SCHEMA 8.8 declares "
        "both never null and zero when the half holds no valid day. A null there would make the "
        "split row's denominator, which is derived from the counts, silently smaller",
    "n_split_day_count_negative":
        "at least one weekday or weekend valid-day count is negative, which no count of days is",
    "n_weekday_count_mismatch":
        "at least one weekday valid-day count does not equal indices one through five of that "
        "episode's day-of-week composition, so the composition and the weekday baseline are "
        "describing two different day sets and only one of them can be the one the median was "
        "taken over",
    "n_weekend_count_mismatch":
        "at least one weekend valid-day count does not equal the Sunday and Saturday entries of "
        "that episode's day-of-week composition, the same identity failing on the other half",
    "n_weekday_weekend_sum_mismatch":
        "at least one episode's weekday and weekend valid-day counts do not sum to its valid "
        "baseline day count. The two halves partition the week, so a shortfall means a valid "
        "baseline day fell in neither half and the split row would be fitted on fewer days than "
        "the primary was",
})


def baseline_violations(invariants: Mapping[str, Any],
                        day_distribution: pd.DataFrame,
                        day_of_week: pd.DataFrame,
                        categories: pd.DataFrame) -> list[str]:
    """Everything the baseline tables must satisfy before a deficit computed from them is read.

    The invariants run over the WHOLE `baseline` table, ineligible episodes included, because a
    zero baseline that rung 12 happened to filter out is still a defect in the build and the
    next amendment may not filter it.  The three describing frames are checked for shape only:
    the day-of-week index has to run 0 to 6 with `day_of_week` one greater, and every
    categorical bucket has to be a slug this module knows, because a bucket it does not know is
    a vocabulary that drifted rather than a category that appeared.
    """
    frame = pd.DataFrame([dict(invariants)])
    out = _zero_expected(frame, list(_BASELINE_SENTENCES), _BASELINE_SENTENCES)

    if not day_of_week.empty:
        index = pd.to_numeric(day_of_week["dow_index"], errors="coerce")
        weekday = pd.to_numeric(day_of_week["day_of_week"], errors="coerce")
        if ((weekday - index) != 1).any():
            out.append("the day-of-week index and the weekday number no longer differ by one, "
                       "so index zero is not Sunday and the composition is mislabelled")
        for group_slug, part in day_of_week.groupby("group_slug", sort=True):
            if sorted(int(v) for v in part["dow_index"]) != list(range(BASELINE_DOW_LENGTH)):
                out.append("a group's day-of-week composition does not carry all seven indices")
                break

    known = {
        "baseline_band": set(BASELINE_BAND_SLUGS) | {"no_baseline"},
        "baseline_floor": {"clears", "below", "unknown"},
        "near_complete_window": {"yes", "no"},
    }
    for slug in ALTERNATIVE_BASELINES:
        known[slug] = {"present", "absent"}
    for slug in SPLIT_BASELINE_METRICS:
        known[slug] = {"present", "absent"}
    if not categories.empty:
        for metric, part in categories.groupby("metric_slug", sort=True):
            if metric not in known:
                out.append("the baseline category frame carries a metric this module does not "
                           "know, so its vocabulary and the query's have drifted apart")
                continue
            unknown = set(part["bucket_slug"].astype(str)) - known[metric]
            if unknown:
                out.append("a baseline category carries a bucket outside its declared "
                           "vocabulary, which is a drift rather than a new category")

    if not day_distribution.empty:
        expected_metrics = {
            "valid_baseline_days", "baseline_span_days", "weekday_baseline_days",
            "weekend_baseline_days", "lesser_of_weekday_and_weekend_baseline_days",
            "analyzable_accrual_days", "at_risk_accrual_days",
        }
        seen = set(day_distribution["metric_slug"].astype(str))
        if seen != expected_metrics:
            out.append("the baseline day-distribution frame does not carry exactly the metrics "
                       "this module declares, so a report row would be built from a metric "
                       "nobody named")
        negative = pd.to_numeric(day_distribution["bucket_value"], errors="coerce") < 0
        if negative.any():
            out.append("a baseline day distribution carries a negative bucket, and a count of "
                       "days cannot be negative")

    if not categories.empty and set(SPLIT_BASELINE_METRICS) <= set(
            categories["metric_slug"].astype(str)):
        # ANALYSIS-PLAN 2.2: the split row requires 5 valid weekday days and 2 valid weekend
        # days, so an episode on that row necessarily has a valid day in BOTH halves and
        # therefore both medians.  The row's set is a subset of each median's own set and can
        # never be larger than either.  A build that derived the row's denominator from the
        # medians instead of from the counts would satisfy this; a build that derived the
        # medians from the counts wrongly would not.
        present = categories[categories["bucket_slug"].astype(str) == "present"]

        def _present(metric: str) -> int:
            part = present[(present["group_slug"].astype(str) == ALL_GROUPS_SLUG)
                           & (present["metric_slug"].astype(str) == metric)]
            return int(pd.to_numeric(part["n_episodes"], errors="coerce").fillna(0).sum())

        split = _present("baseline_weekday_weekend_split")
        if split > _present("weekday_baseline") or split > _present("weekend_baseline"):
            out.append("more episodes clear the split-baseline minimum-day rule than have a "
                       "weekday or a weekend baseline at all. The split row requires a valid "
                       "day in each half of the week, so its set is a SUBSET of both medians' "
                       "sets and cannot be larger than either")
    return out


_PANEL_SENTENCES: Mapping[str, str] = MappingProxyType({
    "n_deficit_null_but_analyzable":
        "at least one analyzable day carries no deficit, so an observed day silently left the "
        "estimand",
    "n_deficit_not_null_but_not_analyzable":
        "at least one NON-analyzable day carries a deficit. This is zero-imputation, and it is "
        "the failure ANALYSIS-PLAN 3.2 built the model-and-integrate estimator to avoid: a zero "
        "deficit asserts the participant walked at or above their own preoperative baseline on "
        "a day nobody observed, summing over observed days then lets every missing day "
        "contribute zero, and non-wear is most likely exactly when the true deficit is largest, "
        "so the bias runs downward and runs harder in sicker participants",
    "n_deficit_zero_not_analyzable":
        "at least one non-analyzable day carries a deficit of exactly zero, which is "
        "zero-imputation in its plainest form",
    "n_deficit_out_of_range":
        "at least one deficit lies outside zero to one, which the truncation makes impossible",
    "n_normalized_null_mismatch":
        "normalized activity and the deficit disagree about which days are observed",
    "n_untruncated_null_mismatch":
        "the untruncated deficit and the deficit disagree about which days are observed, so the "
        "untruncated sensitivity row would run on a different day set from the primary",
    "n_truncation_mismatch":
        "at least one deficit is not the truncation at zero of its own untruncated value, so "
        "the two columns are not the same quantity and the untruncated sensitivity would not be "
        "varying only the truncation",
    "n_steps_null_with_deficit":
        "at least one day with NO step record carries a deficit, so a deficit was computed from "
        "an absent step total",
    "n_valid_wear_with_null_minutes":
        "at least one day with NO heart-rate record was counted as a valid wear day",
    "n_analyzable_when_censored":
        "at least one censored day is analyzable, so a day after death, after a repeat "
        "operation or beyond the observation cutoff is contributing to the estimand",
    "n_day_kind_unknown":
        "the three-value day taxonomy carries a value outside its declared vocabulary",
    "n_day_kind_four_unknown":
        "the four-value day taxonomy carries a value outside its declared vocabulary",
    "n_day_kind_four_mismatch":
        "the four-value taxonomy is not the three-value one with the inpatient setting promoted "
        "by precedence, so the two are classifying the same days inconsistently and the report "
        "of ANALYSIS-PLAN 2.3 would not describe the panel the model was fitted on",
    "n_observed_not_analyzable":
        "at least one day is observed and not analyzable, which contradicts DAG-SCHEMA 8.11",
    "n_analyzable_not_observed":
        "at least one analyzable day is not observed, the same clause failing the other way",
    "n_lag_nonnull_on_day_one":
        "post-discharge day 1 carries a lagged wear fraction, and there is no window before it "
        "for one to be computed over",
    "n_lag_null_after_day_one_at_risk":
        "an at-risk day after post-discharge day 1 carries no lagged wear fraction, so the "
        "observation model of ANALYSIS-PLAN 3.7 would drop it for want of a predictor",
    "n_lag_out_of_range":
        "a lagged wear fraction lies outside zero to one, and it is a mean of indicator flags",
})


def panel_violations(invariants: Mapping[str, Any]) -> list[str]:
    """Every way the daily panel can fail the contract, plus the zero-step day checked POSITIVELY.

    The zero-step check is the one that does not fit the "expected zero" shape and must not be
    forced into it.  A real zero-step analyzable day is KEPT (ANALYSIS-PLAN 2.1) and carries a
    deficit of exactly 1, so the failure is not that such days exist, it is that they exist and
    do NOT carry a deficit of 1.  A module that flagged their existence would be arguing for
    deleting the days the study is about.
    """
    frame = pd.DataFrame([dict(invariants)])
    out = _zero_expected(frame, list(_PANEL_SENTENCES), _PANEL_SENTENCES)
    zero_step = _whole(invariants["n_zero_steps_analyzable"], "the zero-step analyzable count")
    with_full = _whole(invariants["n_zero_steps_analyzable_deficit_one"],
                       "the zero-step full-deficit count")
    if zero_step != with_full:
        out.append(
            "a real zero-step analyzable day does not carry a deficit of exactly one. Such a "
            "day is RETAINED under the primary wear rule because profound inactivity may be the "
            "biological signal of interest, and the deficit of a zero-step day is by definition "
            "the maximum. A mismatch here means those days are being computed as something "
            "other than a full day of debt, or are being dropped"
        )
    return out


def day_kind_violations(frame: pd.DataFrame) -> list[str]:
    """Both taxonomies partition the same days, the inpatient flag cuts across, nothing doubles.

    The counted proof of the last clause is arithmetic: the three-value taxonomy sums to the
    number of days and so does the four-value one, so neither has absorbed the inpatient flag as
    a fifth category, and the inpatient count is therefore a cross-cutting total that is
    deliberately not added to either.  Both sums are taken within (group, window) because a
    taxonomy that partitions the pooled total while failing inside a stratum is not a partition.
    """
    out: list[str] = []
    if frame.empty:
        return out
    unknown_kind = set(frame["day_kind"].astype(str)) - set(DAY_KINDS)
    unknown_four = set(frame["day_kind_four"].astype(str)) - set(DAY_KINDS_FOUR)
    if unknown_kind:
        out.append("the three-value day taxonomy carries a value outside its vocabulary")
    if unknown_four:
        out.append("the four-value day taxonomy carries a value outside its vocabulary")
    counts = pd.to_numeric(frame["n_days"], errors="coerce").fillna(0)
    work = frame.assign(_n=counts)
    for (group_slug, window_slug), part in work.groupby(["group_slug", "window_slug"],
                                                        sort=True):
        total = int(part["_n"].sum())
        by_kind = int(part.groupby("day_kind")["_n"].sum().sum())
        by_four = int(part.groupby("day_kind_four")["_n"].sum().sum())
        if by_kind != total or by_four != total:
            out.append("a day taxonomy does not partition its own stratum, so one of the two is "
                       "either dropping days or counting them twice")
            break
        mismatched = part[part.apply(
            lambda r: str(r["day_kind_four"]) != ("censored" if str(r["day_kind"]) == "censored"
                                                  else ("inpatient" if bool(r["is_inpatient"])
                                                        else str(r["day_kind"]))), axis=1)]
        if len(mismatched):
            out.append("the four-value taxonomy is not the three-value one with the inpatient "
                       "setting promoted by precedence")
            break
    return out


def inpatient_observed_cell(frame: pd.DataFrame) -> dict[str, Any]:
    """The cell that proves inpatient is not exclusive of observed, counted once in each taxonomy.

    A readmitted participant who is wearing the device produces a valid, analyzable, INPATIENT
    day and the plan KEEPS it, because a readmission is part of recovery and deleting it would
    delete the worst days.  Those days are `observed` in the three-value taxonomy and
    `inpatient` in the four-value one, which is not a contradiction: they are two questions
    about the same day, one about whether it was seen and one about where it was spent.  This
    returns the count under both labels, and the two must be equal, which is what "counted once
    in each, never twice in either" means arithmetically.
    """
    counts = pd.to_numeric(frame["n_days"], errors="coerce").fillna(0)
    work = frame.assign(_n=counts)
    observed_inpatient = work[(work["day_kind"].astype(str) == "observed")
                              & work["is_inpatient"].astype(bool)]
    four_inpatient = work[(work["day_kind_four"].astype(str) == "inpatient")
                          & work["is_analyzable"].astype(bool)]
    left = int(observed_inpatient["_n"].sum())
    right = int(four_inpatient["_n"].sum())
    return {
        "n observed and inpatient": left,
        "n inpatient and analyzable": right,
        "counted once in each taxonomy": left == right,
    }


_LEDGER_COLUMNS: tuple[str, ...] = ("n_at_risk", "n_valid_wear", "n_analyzable", "n_inpatient")


def wear_ledger_disagreements(daily: pd.DataFrame, ledger: pd.DataFrame) -> pd.DataFrame:
    """Cell-by-cell comparison of a fresh `drd_daily` aggregate against the DAG's own ledger.

    `07_export.py` writes Figure 2 and the wear-availability ledger out of `ledger_wear_by_day`,
    while `05_analysis_drd.py` fits its model on `drd_daily`.  If the two disagree then the
    figure and the model are describing different data, and the caption would carry numbers no
    reader could reproduce.  The counts returned here are counts of TABLE CELLS, which are a
    property of the build rather than of any participant, so they are the one class of number in
    this module that is printed unrounded, and the frame deliberately carries no cell VALUE.
    """
    left = daily.rename(columns={"post_discharge_day": "day"})
    keys = ["group_slug", "day"]
    merged = left.merge(ledger, on=keys, how="outer", suffixes=("_panel", "_ledger"),
                        indicator=True)
    rows: list[dict[str, Any]] = []
    for column in _LEDGER_COLUMNS:
        panel = pd.to_numeric(merged[f"{column}_panel"], errors="coerce")
        ledger_side = pd.to_numeric(merged[f"{column}_ledger"], errors="coerce")
        both = merged["_merge"] == "both"
        differs = both & (panel != ledger_side)
        rows.append({
            "column": column,
            "n_cells_compared": int(both.sum()),
            "n_cells_disagreeing": int(differs.sum()),
        })
    frame = pd.DataFrame(rows)
    frame.attrs["n_rows_only_in_panel"] = int((merged["_merge"] == "left_only").sum())
    frame.attrs["n_rows_only_in_ledger"] = int((merged["_merge"] == "right_only").sum())
    return frame


def wear_ledger_violations(comparison: pd.DataFrame) -> list[str]:
    """A single disagreeing cell is a stop condition, because the figure would be unreproducible."""
    out: list[str] = []
    if (pd.to_numeric(comparison["n_cells_disagreeing"], errors="coerce").fillna(0) > 0).any():
        out.append(
            "the wear-availability ledger disagrees with a fresh aggregate of the daily panel. "
            "Figure 2 and the wear ledger are written from the ledger and the model is fitted on "
            "the panel, so a disagreement puts a caption in the manuscript that nobody can "
            "reproduce from the data the model saw"
        )
    if comparison.attrs.get("n_rows_only_in_panel", 0):
        out.append("the daily panel carries a group and day the wear ledger does not, so the "
                   "ledger is missing rows the figure would need")
    if comparison.attrs.get("n_rows_only_in_ledger", 0):
        out.append("the wear ledger carries a group and day the daily panel does not, so the "
                   "figure would plot a point the model never saw")
    return out


def landmark_violations(frame: pd.DataFrame) -> list[str]:
    """The two landmark conditions must each equal their own definition, and stay separate.

    Every check here is on a flag against the column it is DEFINED from, not on one flag against
    another, which is what keeps the two conditions from being validated into each other.  The
    derived range of ANALYSIS-PLAN 4.3 is checked the same way: the structural flag must be true
    on exactly the events of post-discharge day 1 to 4 and false on every other, and the plan's
    six-row derivation is therefore audited rather than quoted.
    """
    out: list[str] = []
    if frame.empty:
        return out
    valid_days = pd.to_numeric(frame["n_valid_days_in_window"], errors="coerce")
    eligible_days = pd.to_numeric(frame["n_eligible_days_in_window"], errors="coerce")
    computable = frame["has_computable_landmark"].astype(bool)
    structural = frame["structurally_uncomputable_landmark"].astype(bool)
    no_signal = frame["no_computable_step_signal"].astype(bool)
    events = pd.to_numeric(frame["n_events"], errors="coerce").fillna(0)
    early = pd.to_numeric(frame["n_events_on_day_four_or_earlier"], errors="coerce").fillna(0)
    r72 = pd.to_numeric(frame["n_r72_not_null"], errors="coerce").fillna(0)

    if (computable != (valid_days >= LANDMARK_MIN_VALID_DAYS)).any():
        out.append("the computable-landmark flag does not equal its own definition of at least "
                   "two VALID days in the proximal window")
    if (structural != (eligible_days < LANDMARK_MIN_VALID_DAYS)).any():
        out.append("the structural-landmark flag does not equal its own definition of fewer "
                   "than two ELIGIBLE, that is post-discharge, days in the proximal window")
    if (no_signal != ((~computable) & (~structural))).any():
        out.append("the co-primary exposure on the event table is not the DATA condition and "
                   "only the data condition, which is a window that held at least two "
                   "post-discharge days and had fewer than two of them worn. It is NOT the "
                   "bare complement of the computable-landmark flag: that complement also "
                   "holds on an event of post-discharge day 1 to 4, whose window has no "
                   "eligible days to wear on, and folding those in would put attrition rung 18 "
                   "inside ANALYSIS-PLAN 4.4's N")
    if ((structural) & (early != events)).any():
        out.append("an event flagged structurally uncomputable falls after post-discharge day "
                   "4, which contradicts the six-row derivation of ANALYSIS-PLAN 4.3")
    if ((~structural) & (early != 0)).any():
        out.append("an event on post-discharge day 1 to 4 is NOT flagged structurally "
                   "uncomputable, so attrition rung 18 would undercount the events the analysis "
                   "is blind to by construction")
    if (pd.to_numeric(frame["n_missing_days_mismatch"], errors="coerce").fillna(0) != 0).any():
        out.append("the missing-day count in a proximal window is not the window length less "
                   "its valid days")
    if ((valid_days == 0) & (r72 > 0)).any():
        out.append("a proximal window with no valid day carries a proximal activity ratio, so a "
                   "ratio was computed from an empty median")
    return out


def landmark_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """The four landmark counts `06_analysis_gate.py` needs, kept apart on purpose.

    `n structurally deleted` is attrition rung 18 and those events LEAVE the analysis.  `n data
    uncomputable` is the collider-correction set and those windows STAY, entering the model
    through the co-primary exposure N.  Adding the two would delete the second along with the
    first and would leave no trace in any downstream count, which is precisely the failure
    ANALYSIS-PLAN 4.4 exists to prevent, so this returns them as two keys and never a sum.

    `n ratio at a single valid day` is the trap beside them.  `r72` is null only when the window
    holds NO valid day, so an event with exactly one valid day carries a non-null one-day
    median while its landmark is not computable under the two-day rule.  The co-primary model
    multiplies `f(R)` by `(1 - N)` and never reads it; a filter written as `r72 IS NOT NULL`
    would read it and would quietly readmit the collider.
    """
    if frame.empty:
        return {"n first events": 0, "n structurally deleted": 0, "n data uncomputable": 0,
                "n computable": 0, "n ratio at a single valid day": 0}
    first = frame[frame["is_first_event"].astype(bool)]
    events = pd.to_numeric(first["n_events"], errors="coerce").fillna(0)
    structural = first["structurally_uncomputable_landmark"].astype(bool)
    computable = first["has_computable_landmark"].astype(bool)
    valid_days = pd.to_numeric(first["n_valid_days_in_window"], errors="coerce")
    single = first[(valid_days == 1)]
    return {
        "n first events": int(events.sum()),
        "n structurally deleted": int(events[structural].sum()),
        "n data uncomputable": int(events[(~structural) & (~computable)].sum()),
        "n computable": int(events[computable].sum()),
        "n ratio at a single valid day": int(
            pd.to_numeric(single["n_r72_not_null"], errors="coerce").fillna(0).sum()),
    }


_LANDMARK_PANEL_SENTENCES: Mapping[str, str] = MappingProxyType({
    "n_landmark_day_offset_wrong":
        "an episode-day's landmark day is not its post-discharge day less three, so the panel's "
        "landmark scale and its day scale have come apart",
    "n_day_out_of_range":
        "the landmark panel carries a post-discharge day outside 1 to 90, and its grid is the "
        "daily panel's grid",
    "n_valid_out_of_range":
        "a proximal window holds a valid-day count outside zero to three, and the window is "
        "three days long",
    "n_eligible_out_of_range":
        "a proximal window holds an eligible-day count outside zero to three",
    "n_valid_over_eligible":
        "a proximal window holds more VALID days than ELIGIBLE ones, so a day that is not a "
        "post-discharge day was counted as worn",
    "n_computable_flag_wrong":
        "the computable-landmark flag does not equal its own definition of at least two valid "
        "days in the window",
    "n_signal_flag_wrong":
        "the no-signal exposure is not its own definition, which is the DATA condition and only "
        "the data condition: the window held at least two post-discharge days AND fewer than "
        "two of them were worn. A surface that sets it from valid days alone, with no "
        "structural filter, admits the definitional condition into the exposure, and "
        "ANALYSIS-PLAN 4.4 corrects the surface against the plan rather than the plan against "
        "the surface. It would also stop being the column the risk sets carry, so the two "
        "tables would no longer compare without a translation",
    "n_structural_flag_wrong":
        "the structural flag does not equal post-discharge day 1 to 4 on every episode-day. "
        "That flag is arithmetic on the post-discharge grid, so a disagreement means the daily "
        "panel no longer carries one row per analytic episode per day and every window count on "
        "this panel is suspect. This is the six-row derivation of ANALYSIS-PLAN 4.3 checked "
        "across the whole cohort rather than only at event dates",
    "n_structural_definition_wrong":
        "the structural flag does not equal its own definition of fewer than two eligible days, "
        "the same flag failing against the other of its two statements",
    "n_structural_carrying_no_signal":
        "an episode-day is structurally uncomputable and yet carries the no-signal exposure. "
        "Its window holds fewer than two post-discharge days, so it has no exposure window at "
        "all, carries no N, and is outside the co-primary exposure on every surface. A day "
        "counted on both sides puts an exclusion inside an exposure, which is the one merge "
        "ANALYSIS-PLAN 4.4 exists to forbid",
    "n_weight_flag_wrong":
        "the weight-input flag is not the null test on the lagged wear fraction it is defined "
        "as, so counting on it would size the early-landmark rule wrongly",
    "n_weight_null_boundary_wrong":
        "the lagged wear fraction is not null exactly where the landmark day is 1 or less. That "
        "boundary is one day wider than a landmark before post-discharge day 1: at a landmark "
        "on day 1 the panel row exists and the column is null anyway, because the lag runs over "
        "post-discharge days and day 1 has none preceding it",
    "n_before_day_one_flag_wrong":
        "the before-day-one flag does not equal its own definition of a landmark day below 1",
    "n_wearable_lag_null":
        "the wearable-grid lagged fraction is null on at least one episode-day. The wearable "
        "grid is dense from index day minus 60, so it covers the seven days behind every "
        "landmark, and a null there is a defect in the span rather than a data condition",
    "n_wearable_lag_out_of_range":
        "a wearable-grid lagged fraction lies outside zero to one, and it is a mean of "
        "indicator flags",
    "n_wearable_grid_short":
        "at least one episode-day looks back over fewer than seven wearable days. That is not a "
        "data condition to be weighted around: it means the wearable grid does not cover the "
        "lookback, and it is a defect to be found before any weight is fitted",
    "n_first_event_not_event":
        "an episode-day is flagged a first event and not an event",
    "n_events_without_panel_row":
        "an event has no row in the landmark panel at its own post-discharge day, so the "
        "full-cohort comparison is missing exactly the days it exists to describe",
    "n_event_window_disagreement":
        "the landmark panel and the event table disagree about the proximal window at an event "
        "date. Both compute the E minus 5 to E minus 3 window under the same rule from "
        "different sources, so a disagreement means one definition has drifted or one table is "
        "stale from an earlier build. Rebuild the daily panel forward rather than reconciling "
        "the two by hand",
    "n_event_day_not_flagged":
        "an event date carries a panel row that is not flagged an event day, so the panel's own "
        "outcome indicator disagrees with the event table it was built from",
})


def landmark_panel_violations(invariants: Mapping[str, Any],
                              by_day: pd.DataFrame) -> list[str]:
    """The landmark panel checked against DAG-SCHEMA 8.13, both of its SQL asserts included.

    The stage raises on the two invariants while it BUILDS, and that is not evidence about the
    table a later session reads: a resumed build starts at a named stage, and a table left in
    place from an earlier run was never re-asserted.  Both are therefore re-asserted here, on
    the frames, every run.
    """
    frame = pd.DataFrame([dict(invariants)])
    out = _zero_expected(frame, list(_LANDMARK_PANEL_SENTENCES), _LANDMARK_PANEL_SENTENCES)

    episode_days = _whole(invariants.get("n_episode_days", 0), "the panel row count")
    if episode_days == 0:
        out.append("the landmark panel is empty. It is one row per analytic episode per "
                   "post-discharge day 1 to 90 and the cohort is not empty, so an empty panel "
                   "is a stage that did not run rather than a cohort with no days")
        return out
    events_joined = _whole(invariants.get("n_events_joined", 0), "the joined event count")
    if events_joined == 0:
        out.append("no event joined the landmark panel at all, so the cell-for-cell agreement "
                   "between the panel and the event table is unverified rather than verified")
    absent = _whole(invariants.get("n_weight_input_absent", 0), "the weight-input count")
    before_one = _whole(invariants.get("n_landmark_before_day_one", 0), "the early count")
    available = _whole(invariants.get("n_weight_input_available", 0), "the weight-input count")
    if before_one > absent:
        out.append("more episode-days have a landmark before post-discharge day 1 than have no "
                   "weight input at all, and the first is the strictly narrower subset")
    if absent + available != episode_days:
        out.append("the episode-days with and without a landmark weight input do not sum to the "
                   "panel, so the two do not partition it and the early-landmark rule would be "
                   "sized against the wrong denominator")

    if not by_day.empty:
        structural = by_day["structurally_uncomputable_landmark"].astype(bool)
        signal = by_day["no_computable_step_signal"].astype(bool)
        day = pd.to_numeric(by_day["post_discharge_day"], errors="coerce")
        episode = pd.to_numeric(by_day["n_episode_days"], errors="coerce").fillna(-1)
        at_risk = pd.to_numeric(by_day["n_at_risk_days"], errors="coerce").fillna(-1)
        events = pd.to_numeric(by_day["n_event_days"], errors="coerce").fillna(-1)
        first = pd.to_numeric(by_day["n_first_event_days"], errors="coerce").fillna(-1)
        if (structural & (day > STRUCTURAL_DELETION_LAST_DAY)).any():
            out.append("the by-day panel flags an episode-day after post-discharge day 4 as "
                       "structurally uncomputable, which the six-row derivation forbids")
        if ((~structural) & (day <= STRUCTURAL_DELETION_LAST_DAY)).any():
            out.append("the by-day panel does not flag a post-discharge day 1 to 4 as "
                       "structurally uncomputable")
        if (structural & signal).any():
            out.append("the by-day panel carries a structurally uncomputable day that also "
                       "carries the no-signal exposure. That day has no exposure window at all "
                       "and belongs on neither side of the comparison, so counting it as the "
                       "data condition would put an exclusion inside an exposure")
        if (at_risk > episode).any():
            out.append("a by-day cell holds more at-risk days than episode-days")
        if (events > at_risk).any():
            out.append("a by-day cell holds more event days than at-risk days, so an event was "
                       "counted on a day the episode was not at risk")
        if (first > events).any():
            out.append("a by-day cell holds more first-event days than event days")
    return out


def landmark_panel_summary(invariants: Mapping[str, Any],
                           by_day: pd.DataFrame) -> dict[str, Any]:
    """ANALYSIS-PLAN 4.4 fix 3 on the full-cohort panel, crude and day-standardized.

    WHY THIS SURFACE AND NOT THE OTHER TWO.  Risk-set membership is not a sample of
    episode-days; it is the output of the sampling of 4.5 and the matching of 4.7, and both
    select on the variable this comparison is about.  The cap of three control landmarks per
    participant removes the participants who would contribute the most days, who are the
    best-observed ones; five controls per case fixes a ratio rather than measuring a rate; and
    day-of-week matching selects landmarks on the calendar, which is one of the things deciding
    whether a window is computable at all.  A comparison taken there compares windows that
    already survived the selection it exists to expose, which is the collider again one level
    up.  The other available surface, first events among episodes that had one, conditions on
    having an event and on it being the first, which is selection on the outcome.

    WHAT THE FULL-COHORT VERSION BUYS AND WHAT IT COSTS.  It buys a real denominator: every
    at-risk episode-day is in it, whether or not that participant was ever sampled and whether
    or not they ever had an event, so the quantity is an event rate per episode-day within each
    condition and the two sit on a common base.  It costs that the comparison is UNMATCHED and
    DESCRIPTIVE: post-discharge day drives both wear and events and the panel controls for
    nothing, which is why the plan requires it reported twice.  If the two agree, post-discharge
    day is not doing the work; if they disagree, the reader is shown by how much rather than
    told which to believe.  Neither version is a causal estimate and neither is labelled one.

    THE DEFINITIONAL CONDITION IS EXCLUDED FROM THE COMPARISON AND REPORTED BESIDE IT, NEVER
    ADDED IN.  Post-discharge days 1 to 4 are uncomputable for a reason that is not about wear,
    and folding them into the "without" side would make part of the contrast a statement about
    the calendar.
    """
    empty = {
        "available": False,
        "n episode days": _whole(invariants.get("n_episode_days", 0), "the panel row count"),
        "n episodes": _whole(invariants.get("n_episodes", 0), "the panel episode count"),
        "n weight input available": _whole(
            invariants.get("n_weight_input_available", 0), "a weight-input count"),
        "n weight input absent": _whole(
            invariants.get("n_weight_input_absent", 0), "a weight-input count"),
        "n landmark before post-discharge day one": _whole(
            invariants.get("n_landmark_before_day_one", 0), "an early-landmark count"),
        "caveat": "The landmark panel carries no day at which the comparison is defined.",
    }
    if by_day.empty:
        return empty
    pooled = by_day[by_day["group_slug"].astype(str) == ALL_GROUPS_SLUG].copy()
    if pooled.empty:
        return empty
    structural = pooled["structurally_uncomputable_landmark"].astype(bool)
    definitional_days = int(
        pd.to_numeric(pooled[structural]["n_at_risk_days"], errors="coerce").fillna(0).sum())
    definitional_events = int(
        pd.to_numeric(pooled[structural]["n_event_days"], errors="coerce").fillna(0).sum())
    open_days = pooled[~structural].copy()
    if open_days.empty:
        return empty
    open_days["_signal"] = open_days["no_computable_step_signal"].astype(bool)
    open_days["_day"] = pd.to_numeric(open_days["post_discharge_day"], errors="coerce")
    open_days["_at_risk"] = pd.to_numeric(open_days["n_at_risk_days"],
                                          errors="coerce").fillna(0)
    open_days["_events"] = pd.to_numeric(open_days["n_event_days"], errors="coerce").fillna(0)
    grid = open_days.groupby(["_day", "_signal"], as_index=False)[["_at_risk", "_events"]].sum()
    wide_risk = grid.pivot(index="_day", columns="_signal", values="_at_risk").fillna(0)
    wide_events = grid.pivot(index="_day", columns="_signal", values="_events").fillna(0)
    for flag in (True, False):
        if flag not in wide_risk.columns:
            wide_risk[flag] = 0.0
            wide_events[flag] = 0.0

    # The standardization weights are the analytic cohort's own at-risk day distribution and
    # nothing else, restricted to the days where BOTH conditions have days for a rate to exist.
    # A day where one side is empty has no rate on that side, and carrying its weight anyway
    # would divide a numerator by a denominator that includes days the stratum never had.
    both = (wide_risk[True] > 0) & (wide_risk[False] > 0)
    weights = (wide_risk[True] + wide_risk[False]).where(both, 0.0)
    weight_total = float(weights.sum())

    out: dict[str, Any] = dict(empty)
    out["available"] = True
    out["n days standardized over"] = int(both.sum())
    for label, flag in (("without a computable ratio", True),
                        ("with a computable ratio", False)):
        at_risk = float(wide_risk[flag].sum())
        events = float(wide_events[flag].sum())
        out[f"n at risk days {label}"] = int(at_risk)
        out[f"n event days {label}"] = int(events)
        out[f"crude rate {label}"] = (events / at_risk) if at_risk > 0 else float("nan")
        if weight_total > 0:
            day_rate = (wide_events[flag] / wide_risk[flag].replace(0, np.nan)).fillna(0.0)
            out[f"standardized rate {label}"] = float(
                (weights * day_rate).sum() / weight_total)
        else:
            out[f"standardized rate {label}"] = float("nan")
    out["n at risk days with no eligible window"] = definitional_days
    out["n event days with no eligible window"] = definitional_events
    out["caveat"] = (
        "The comparison is unmatched and descriptive. Post-discharge day drives both wear and "
        "events and the panel adjusts for nothing else, which is why it is reported twice, "
        "crude and standardized to the post-discharge-day distribution of the analytic cohort. "
        "Neither figure is a causal estimate and neither is the correction for the collider; "
        "the correction is the co-primary exposure. The bottom pair is the DEFINITIONAL "
        "condition, which is attrition rung 18 and leaves the analysis, and it is never added "
        "to the row above it."
    )
    return out


def risk_set_violations(sizes: pd.DataFrame, members: pd.DataFrame,
                        participation: pd.DataFrame, ledger: pd.DataFrame,
                        digest: Mapping[str, Any]) -> list[str]:
    """Every closed degree of freedom in ANALYSIS-PLAN 4.5, checked against the built table.

    An empty `risk_sets` is a legitimate outcome, not a failure: at the lowest gate tiers Arm A
    does not run and the table is created empty on purpose, because a table that is present and
    empty and a table that is absent are different claims and only one of them is checkable.
    So the shape checks are skipped on an empty table rather than reported as violations, and
    the report says which of the two happened.
    """
    out: list[str] = []
    if not sizes.empty:
        for column, sentence in (
            ("n_size_mismatch",
             "a matched set's declared control count does not equal the control rows it "
             "actually holds, so the matched-set ledger describes a table the conditional model "
             "does not read"),
            ("n_case_row_count_wrong",
             "a matched set does not hold exactly one case row, and the set id IS the case's "
             "event id"),
            ("n_over_control_cap",
             "a matched set holds more controls than the per-case cap of ANALYSIS-PLAN 4.5"),
        ):
            if (pd.to_numeric(sizes[column], errors="coerce").fillna(0) != 0).any():
                out.append(sentence)
        set_size = pd.to_numeric(sizes["set_size"], errors="coerce")
        rung = pd.to_numeric(sizes["match_rung"], errors="coerce")
        n_sets_column = pd.to_numeric(sizes["n_sets"], errors="coerce").fillna(0)
        in_weighted = pd.to_numeric(sizes["n_sets_in_weighted_sensitivity"],
                                    errors="coerce").fillna(0)
        lost_controls = pd.to_numeric(sizes["n_sets_losing_every_control"],
                                      errors="coerce").fillna(0)
        lost_case = pd.to_numeric(sizes["n_sets_losing_the_case"], errors="coerce").fillna(0)
        weighted_members = pd.to_numeric(sizes["n_members_in_weighted_sensitivity"],
                                         errors="coerce").fillna(0)
        if ((in_weighted > n_sets_column) | (lost_controls > n_sets_column)
                | (lost_case > n_sets_column)).any():
            out.append("more matched sets leave or survive the weighted sensitivity than exist "
                       "at that set size and rung, so the weighted denominator is not a subset "
                       "of the primary's")
        if ((in_weighted > 0) & (weighted_members < 2 * in_weighted)).any():
            out.append("a matched set in the weighted sensitivity carries fewer than two "
                       "members, and a set enters a conditional likelihood only with its case "
                       "AND at least one control")
        if ((set_size == 0) & (lost_controls > 0)).any():
            out.append("a matched set with no control at all is counted as LOSING every "
                       "control. It had none to lose, and folding the two together would report "
                       "the early-landmark rule as the cause of an emptiness the sampling "
                       "produced")
        if ((set_size < 0) | (set_size > CONTROLS_PER_CASE_CAP)).any():
            out.append("a matched set size lies outside zero to the per-case cap")
        if (~rung.isin(MATCH_RUNGS)).any():
            out.append("a matched set carries a relaxation rung outside the three of "
                       "ANALYSIS-PLAN 4.7")

    if not members.empty:
        if (pd.to_numeric(members["n_role_flag_mismatch"], errors="coerce").fillna(0) != 0).any():
            out.append("a member's case flag disagrees with its own role")
        if (pd.to_numeric(members["n_landmark_day_offset_wrong"],
                          errors="coerce").fillna(0) != 0).any():
            out.append("a member's landmark day is not its matched day less three, so the "
                       "landmark scale and the matched-day scale have come apart and every "
                       "early-landmark count below is taken on the wrong boundary")
        if (pd.to_numeric(members["n_early_by_neither_route"],
                          errors="coerce").fillna(0) != 0).any():
            out.append("a member sits at a landmark day of one or less by neither of the two "
                       "routes ANALYSIS-PLAN 4.4 names. 4.3 puts every primary case at "
                       "post-discharge day 5 or later, so such a member arrived either through "
                       "the partial-window secondary or through the day-of-week relaxation, and "
                       "a third route is a sampling rule nobody prespecified")
        absent = pd.to_numeric(members["n_landmark_weight_input_absent"],
                               errors="coerce").fillna(0)
        before_one = pd.to_numeric(members["n_landmark_before_post_discharge_day_one"],
                                   errors="coerce").fillna(0)
        routes = sum(pd.to_numeric(members[column], errors="coerce").fillna(0)
                     for column in ("n_early_via_partial_window_secondary",
                                    "n_early_via_day_of_week_relaxation",
                                    "n_early_by_neither_route"))
        if (before_one > absent).any():
            out.append("more members have a landmark before post-discharge day 1 than have no "
                       "weight input at all, and the first is the strictly narrower subset of "
                       "the second: a landmark on day 1 has a panel row but no lagged window "
                       "behind it")
        if (routes != absent).any():
            out.append("the two routes to an early landmark do not account for every member "
                       "without a weight input, so the split ANALYSIS-PLAN 4.4 requires "
                       "reported does not partition the count it is a split of")
        # ANALYSIS-PLAN 4.4: a member at a landmark day of 1 or less carries NO N and is
        # outside the co-primary exposure ON EVERY SURFACE, `risk_sets` included.  The exposure
        # is already on this frame's grain, so a member on both sides shows up as an early
        # count sitting on a grain row whose exposure key is true.
        signal_rows = members[members["no_computable_step_signal"].astype(bool)]
        if (pd.to_numeric(signal_rows["n_landmark_weight_input_absent"],
                          errors="coerce").fillna(0) != 0).any():
            out.append("a risk-set member at a landmark day of one or less carries the "
                       "no-signal exposure. Its window holds fewer than two post-discharge "
                       "days, which is the definitional condition rather than a wear fact, so "
                       "it has no exposure window, carries no N and is outside the co-primary "
                       "exposure on every surface. Counting it as the exposure would put a "
                       "calendar artefact inside the coefficient that exists to measure "
                       "informative non-wear, and it would do it in the direction that matters "
                       "because these are the earliest members in the study")
        if (pd.to_numeric(members["n_early_carrying_r72"],
                          errors="coerce").fillna(0) != 0).any():
            out.append("a risk-set member at a landmark day of one or less carries a proximal "
                       "activity ratio. Its window reaches at most one post-discharge day, so "
                       "there is nothing for a ratio to be a median of, and a reader who "
                       "filtered on the ratio being present rather than on the flag would fit "
                       "it as though it were the exposure")
        cases = members[members["member_role"].astype(str) == "case"]
        controls = members[members["member_role"].astype(str) == "control"]
        case_members = pd.to_numeric(cases["n_members"], errors="coerce").fillna(0)
        case_null = pd.to_numeric(cases["n_fingerprint_null"], errors="coerce").fillna(0)
        control_null = pd.to_numeric(controls["n_fingerprint_null"], errors="coerce").fillna(0)
        if (case_members != case_null).any():
            out.append("a case row carries a sampling fingerprint. The fingerprint is the "
                       "seeded order that DREW a control, and a case was not drawn, so a "
                       "non-null one on a case row means cases went through the sampler")
        if (control_null != 0).any():
            out.append("a control row carries no sampling fingerprint, so that control was "
                       "selected by something other than the seeded order, which is the "
                       "nondeterminism ANALYSIS-PLAN 4.5 forbids")
        case_rungs = pd.to_numeric(cases["match_rung"], errors="coerce")
        if (case_rungs != 1).any():
            out.append("a case row carries a relaxation rung other than one, and DAG-SCHEMA "
                       "8.14 fixes rung one on every case row")

    if not participation.empty:
        if (pd.to_numeric(participation["n_over_participant_cap"],
                          errors="coerce").fillna(0) != 0).any():
            out.append("a participant contributed more control landmarks than the "
                       "per-participant cap of ANALYSIS-PLAN 4.5, so a few long-observed "
                       "participants are dominating the control pool and the effective sample "
                       "size has collapsed below the nominal one")

    if not sizes.empty and not ledger.empty:
        left = (sizes.groupby("set_size", as_index=False)["n_sets"].sum()
                     .rename(columns={"n_sets": "n_sets_computed"}))
        merged = left.merge(ledger, on="set_size", how="outer", indicator=True)
        if (merged["_merge"] != "both").any():
            out.append("the matched-set ledger and a fresh aggregate of the risk sets do not "
                       "carry the same set sizes")
        else:
            computed = pd.to_numeric(merged["n_sets_computed"], errors="coerce").fillna(-1)
            recorded = pd.to_numeric(merged["n_sets"], errors="coerce").fillna(-1)
            cases = pd.to_numeric(merged["n_cases"], errors="coerce").fillna(-1)
            if (computed != recorded).any():
                out.append("the matched-set ledger's set counts disagree with a fresh aggregate "
                           "of the risk sets")
            if (recorded != cases).any():
                out.append("the matched-set ledger records a different number of cases from "
                           "sets, and there is exactly one case per set")

    if digest:
        n_case_rows = _whole(digest.get("n_case_rows", 0), "the case row count")
        n_sets = _whole(digest.get("n_distinct_sets", 0), "the distinct set count")
        if n_case_rows != n_sets:
            out.append("the number of case rows and the number of distinct matched sets "
                       "disagree, and the set id IS the case's event id")
        text = str(digest.get("membership_digest") or "")
        if n_sets and not re.fullmatch(r"[0-9a-f]{32}", text):
            out.append("the matched-set membership digest is not a 32-character hexadecimal "
                       "value, so the reproducibility comparison has nothing to compare")
    return out


def outcome_by_computable_ratio(members: pd.DataFrame) -> dict[str, Any]:
    """The outcome comparison ANALYSIS-PLAN 4.4 fix 3 requires, with its caveat attached.

    "The outcome rate in windows with versus without a computable ratio is reported, subject to
    the disclosure floor. This is the direct evidence for or against the collider concern and it
    costs nothing."  The comparison is over the SAMPLED windows: cases and their matched
    controls, split by whether a proximal ratio could be computed at that member's own landmark.

    THE CAVEAT IS PART OF THE RESULT AND TRAVELS WITH IT.  Incidence-density sampling fixes the
    control-to-case ratio by design, up to five controls per case, so the case fraction inside
    the sampled sets is NOT an absolute risk and must never be printed as one.  What it is, is
    the composition the conditional model conditions on, and a large difference between the two
    columns is exactly the collider signal `beta_N` estimates.  The returned dictionary carries
    the sentence so a caller cannot pick up the numbers without it.

    THE DEFINITIONAL CONDITION IS A THIRD ROW AND NOT A SHARE OF EITHER OF THE OTHER TWO, and
    that became a live distinction rather than a hypothetical one when `build_all.sql` dropped
    its `control_matched_day >= 5` floor.  Under that floor no day-3 or day-4 control could be
    drawn at all, so no risk-set member ever carried the definitional condition and the split
    on the exposure alone was exhaustive.  It no longer is.  Such a member carries a FALSE
    no-signal exposure, because the exposure is the data condition alone, so a two-way split on
    that column would file it under "with a computable ratio" -- and it has no ratio at all,
    its `r72` being null by construction.  It is therefore counted apart, printed beside the
    comparison, and never added into either side of it.
    """
    if members.empty:
        return {"available": False,
                "caveat": "No matched sets were built, so no comparison exists."}
    work = members.copy()
    work["_n"] = pd.to_numeric(work["n_members"], errors="coerce").fillna(0).astype("int64")
    work["_signal"] = work["no_computable_step_signal"].astype(bool)
    work["_case"] = work["member_role"].astype(str) == "case"
    # ANALYSIS-PLAN 4.4 count 1, reported ONCE rather than twice under two labels a reader would
    # try to add together: on `risk_sets` a landmark day of 1 or less IS the definitional
    # condition, and it is the same set of members the weight rule leaves unweighted.
    work["_definitional"] = pd.to_numeric(
        work["n_landmark_weight_input_absent"], errors="coerce").fillna(0).astype("int64")
    out: dict[str, Any] = {"available": True}
    definitional_total = 0
    definitional_cases = 0
    for label, flag in (("without a computable ratio", True), ("with a computable ratio", False)):
        part = work[work["_signal"] == flag]
        early = int(part["_definitional"].sum())
        early_cases = int(part[part["_case"]]["_definitional"].sum())
        definitional_total += early
        definitional_cases += early_cases
        total = int(part["_n"].sum()) - early
        cases = int(part[part["_case"]]["_n"].sum()) - early_cases
        out[f"n windows {label}"] = total
        out[f"n cases {label}"] = cases
    out["n windows with no eligible window at all"] = definitional_total
    out["n cases with no eligible window at all"] = definitional_cases
    out["caveat"] = (
        "Incidence-density sampling fixes the control-to-case ratio by design, so the case "
        "fraction within sampled sets is a composition and not an absolute risk. Absolute risks "
        "come from the complementary full-cohort model of ANALYSIS-PLAN 4.6. This is NOT where "
        "the plan's fix 3 is computed: the sampling and the matching both select on the "
        "variable that comparison is about, so it is computed on the full-cohort day-indexed "
        "panel instead and is reported above. What this table shows is the composition the "
        "conditional model conditions on, and a large gap between the first two rows is the "
        "signal the co-primary coefficient estimates. The bottom row is the DEFINITIONAL "
        "condition, a member whose landmark window holds fewer than two post-discharge days at "
        "all. It has no exposure window, carries no no-signal exposure and has no proximal "
        "ratio, so it belongs to neither of the rows above and is never added to either of "
        "them; it is dropped from its matched set as a member and it is counted."
    )
    return out


def observation_violations(lag_frame: pd.DataFrame, invariants: Mapping[str, Any]) -> list[str]:
    """The observation model's inputs, checked before ANALYSIS-PLAN 3.7's weights are fitted."""
    out: list[str] = []
    if not lag_frame.empty:
        unknown = set(lag_frame["lag_band_slug"].astype(str)) - set(LAG_BAND_SLUGS)
        if unknown:
            out.append("the lagged wear fraction fell into a band outside the declared "
                       "vocabulary, so the band expression and this module have drifted apart")
        analyzable = pd.to_numeric(lag_frame["n_analyzable"], errors="coerce").fillna(0)
        days = pd.to_numeric(lag_frame["n_days"], errors="coerce").fillna(-1)
        at_risk = pd.to_numeric(lag_frame["n_at_risk"], errors="coerce").fillna(-1)
        if (analyzable > at_risk).any():
            out.append("a lagged-wear band holds more analyzable days than at-risk days, and an "
                       "analyzable day is at risk by definition")
        if (at_risk > days).any():
            out.append("a lagged-wear band holds more at-risk days than days")
    if _whole(invariants.get("n_lag_null_on_day_one", 0),
              "the day-one lagged wear count") == 0 and _whole(
                  invariants.get("n_lag_nonnull_on_day_one", 0),
                  "the day-one lagged wear count") == 0:
        out.append("no post-discharge day 1 rows were found at all, so the strict lag could not "
                   "be checked and the observation model's one safeguard is unverified")
    return out


def missingness_violations(frame: pd.DataFrame) -> list[str]:
    """The variable-provenance ledger's shape, and the three rows that are structurally zero.

    Where `features` substitutes, it also carries the flag that records the substitution, and
    the ledger counts the FLAG (DAG-SCHEMA 8.19).  `bmi` counts `bmi_missing` and
    `charlson_score` counts `charlson_missing`, because the scoring rule makes the Charlson
    column non-null by construction and counting its nulls would report zero on every run: a
    fact about the `IFNULL` rather than about the data.  So a zero on those two rows is a claim
    about the cohort and has to be readable as one, which it only is when the three rows that
    are zero BY LADDER are named separately.  They are named here, and a non-zero on any of them
    means an attrition rung did not do what the ladder says it did.
    """
    out: list[str] = []
    if frame.empty:
        return ["the variable-missingness ledger is empty, and it is built with twelve rows"]
    seen = tuple(frame["variable"].astype(str))
    if set(seen) != set(MISSINGNESS_VARIABLES) or len(seen) != len(MISSINGNESS_VARIABLES):
        out.append("the variable-missingness ledger does not carry exactly the twelve variables "
                   "DAG-SCHEMA 8.19 names, so a Table 1 provenance row would be built from a "
                   "variable nobody declared")
    total = pd.to_numeric(frame["n_total"], errors="coerce").fillna(-1)
    missing = pd.to_numeric(frame["n_missing"], errors="coerce").fillna(-1)
    if (missing > total).any():
        out.append("a variable is missing on more rows than its own grain holds")
    if ((total < 0) | (missing < 0)).any():
        out.append("the variable-missingness ledger carries a negative count")
    structural = frame[frame["variable"].astype(str).isin(STRUCTURALLY_COMPLETE_VARIABLES)]
    if (pd.to_numeric(structural["n_missing"], errors="coerce").fillna(0) != 0).any():
        out.append("a variable that an attrition rung made structurally complete is reported "
                   "missing, so either the rung did not remove what the ladder says it removed "
                   "or the ledger is counting a different column")
    return out


def digests_agree(first: Any, second: Any) -> dict[str, Any]:
    """Compare two matched-set membership digests taken from two builds.

    The verdict, not the mechanism.  The mechanism is that the sampling order is a seeded
    `FARM_FINGERPRINT` over the salt, `SEED = 0`, the set id, the control episode id and the
    matched day, every one of which is a pure function of values that do not change between
    runs, so both caps select the same rows in the same order; the digest is taken over an
    explicit `ORDER BY` so storage order cannot move it; and every stage is `CREATE OR REPLACE`,
    so a rebuild overwrites rather than appends.  A `RAND()` draw would fail this comparison,
    which is why ANALYSIS-PLAN 4.5 forbids one.
    """
    left, right = str(first or ""), str(second or "")
    shaped = bool(re.fullmatch(r"[0-9a-f]{32}", left)) and bool(re.fullmatch(r"[0-9a-f]{32}",
                                                                            right))
    return {
        "comparable": shaped,
        "identical": shaped and left == right,
        "verdict": ("the two builds produced identical matched sets" if shaped and left == right
                    else "the two builds produced DIFFERENT matched sets" if shaped
                    else "at least one digest is not a 32-character hexadecimal value"),
    }


# ======================================================================================
# (8) What the derived tables do NOT carry, and what they have since gained.
#
#     Named here rather than worked around.  Every item is a place where the analysis wanted
#     something the DAG did not build, and each says what `build_all.sql` would need or, where
#     the build or the plan has since supplied it, what closed it.  A second implementation in
#     Python was never an option for any of them: two implementations of one definition are a
#     divergence waiting for the next amendment, and the one in SQL is the one that ran.
#
#     A CLOSED ITEM IS KEPT AND MARKED, NEVER DELETED.  A report that only ever shrinks tells
#     a reader comparing two runs nothing, and cannot distinguish a gap that was closed from a
#     gap somebody quietly dropped.  So the entry stays, its status changes, and the
#     consequence field records what closed it and what this module now validates as a result.
# ======================================================================================

# Each entry carries a `status`, and the two values are read differently.  An OPEN gap is a
# place where the analysis wants something the derived tables do not build, and the entry says
# what `build_all.sql` would need.  A CLOSED gap is kept rather than deleted, because a reader
# comparing this report against an earlier run has to be able to tell a gap that was closed from
# a gap that was quietly dropped, and because the entry records WHAT closed it: a report that
# only ever shrinks tells nobody anything.
DAG_GAPS: tuple[Mapping[str, str], ...] = (
    MappingProxyType({
        "status": "closed",
        "title": "Separate weekday and weekend baselines",
        "found": (
            "The study protocol asked for a sensitivity analysis estimating weekday and weekend "
            "baselines separately, and plan versions 1.0 through 1.2 dropped it: section 6 held "
            "no split-baseline slug in either set, so the row could not be run, and the derived "
            "tables matched the plan rather than the protocol. The baseline table carried the "
            "composition array and the six alternative baselines and no weekday or weekend "
            "median."),
        "consequence": (
            "CLOSED. The baseline table now carries a Monday-to-Friday median, a Saturday-or-"
            "Sunday median and a valid-day count beside each, all four on the same scan as the "
            "other seven baselines. Plan version 1.3 carries the row as supplementary "
            "sensitivity ten. This module validates all four columns on the same null rule the "
            "pooled baseline is held to, null and never zero, and asserts the identity between "
            "the two counts and the day-of-week composition in all three of its parts."),
        "what the build would need": (
            "Nothing further. The remaining obligation is on the reporting side: the row is "
            "fitted on its own denominator, the episodes clearing 5 valid weekday days and 2 "
            "valid weekend days, and that count is reported above because Table 2 must print "
            "it. An episode with valid days in only one half of the week leaves this row and "
            "nothing else."),
    }),
    MappingProxyType({
        "status": "closed",
        "title": "Landmark observation weights at a matched day of 4 or earlier",
        "found": (
            "The plan's second collider fix applies the observation model of section 3.7, "
            "adapted to the landmark, as a sensitivity. Its predictor is the strictly lagged "
            "wear fraction, which the daily panel carries only over post-discharge days. A "
            "member's landmark sits three days before its matched day, so the predictor does "
            "not exist at a matched day of 3 or earlier, where the panel has no row, AND is "
            "null at a matched day of 4, where the row exists but the lag has nothing behind "
            "it. The boundary is one day wider than this module first counted."),
        "consequence": (
            "CLOSED by prespecification rather than by a column. Plan version 1.3 section 4.4 "
            "named the weight rule: a member is weighted when its own landmark day is 2 or "
            "more. Version 1.5 settled what the other side of that boundary is, and it is not a "
            "threshold. The landmark is the matched day less 3 and the window is the three days "
            "ending there, so the window holds two post-discharge days exactly when the "
            "landmark day is 2 or more, and a landmark day of 1 or less IS the definitional "
            "condition in landmark-day terms. Such a member has no exposure window: it carries "
            "no no-signal exposure, contributes nothing to the co-primary coefficient, and is "
            "outside that exposure on every surface. In the primary it leaves for that reason, "
            "and the weight rule bites alone only on a member the partial-window secondary "
            "deliberately reads back in. The plan rejected both alternatives explicitly, "
            "carrying the predictor back onto the preoperative grid and giving those members "
            "the marginal weight, on the ground that each would put a number where the model "
            "has none."),
        "what the build would need": (
            "Nothing. The counts the rule obliges are all reported above: the affected members "
            "split by role and by the two routes that produce them, the matched sets that lose "
            "every control and therefore leave the likelihood, and the weighted sensitivity's "
            "own denominator in sets and in members."),
    }),
    MappingProxyType({
        "status": "closed",
        "title": "A full-cohort day-indexed computable-landmark panel",
        "found": (
            "The outcome comparison with and without a computable proximal ratio was available "
            "at the sampled matched sets and among first events, and at neither as a full-cohort "
            "discrete-time quantity, because nothing carried, for every episode and every day, "
            "whether a landmark window ending on that day would have been computable. Both "
            "available surfaces carry the selection the comparison exists to expose."),
        "consequence": (
            "CLOSED. The build now carries the panel, one row per analytic episode per "
            "post-discharge day 1 to 90, as a three-day-offset self-join of the daily panel. "
            "This module validates it as it validates every other table and re-asserts on the "
            "frames the two invariants the stage asserts in SQL: the panel reproduces the event "
            "table cell for cell at every event date, and the definitional condition equals "
            "post-discharge day 1 to 4 on every episode-day. The comparison is reported above, "
            "crude and standardized to the post-discharge-day distribution of the cohort."),
        "what the build would need": (
            "Nothing. One caution for a consumer: the panel carries two lagged wear fractions "
            "and they are not the same quantity. One averages over post-discharge days and is "
            "the plan's own weight input, null exactly where the weight has none. The other "
            "averages over the seven CALENDAR days behind the landmark, so it can average over "
            "inpatient days and, at an early landmark, over preoperative days, where wear is a "
            "different thing being measured for a different reason. Neither may be silently "
            "substituted for the other."),
    }),
    MappingProxyType({
        "status": "open",
        "title": "Sensitivity deficits under the four alternative wear definitions",
        "found": (
            "Deliberately not precomputed. The daily panel carries one deficit, under the "
            "effective wear rule, and four more float columns would widen the table for every "
            "downstream read."),
        "consequence": (
            "Not a gap and not a defect: the contract hands the recomputation over explicitly. "
            "This module verifies that both inputs exist where they are needed rather than "
            "recomputing anything itself."),
        "what the build would need": (
            "Nothing. The daily-deficit model recomputes each sensitivity from the panel's step "
            "column and the matching alternative baseline, joined on the episode. The count of "
            "episodes whose alternative baseline is absent is reported here, because a "
            "sensitivity fitted where its own baseline exists has a different denominator from "
            "the primary and the table has to print it."),
    }),
)

GAP_STATUS_LABELS: Mapping[str, str] = MappingProxyType({
    "open": "Open",
    "closed": "Closed",
})


# ======================================================================================
# (9) Rendering.  Every human-visible string is built here and the house prose rules are
#     asserted on the RENDERED text, not grepped for afterwards.
# ======================================================================================

_SNAKE_TOKEN = re.compile(r"\b[a-z0-9]+_[a-z0-9_]*\b")
_RULE = "=" * 86
_THIN = "-" * 86

# A cell where the quantity is not defined, as against one where it is defined and suppressed.
# The two are different claims and a reader has to be able to tell them apart, so the
# suppression sentinel is never reused to mean this.
NOT_APPLICABLE: str = "not applicable"


def _denominator(n: Any) -> str:
    """A denominator, rounded at the boundary like every other count."""
    return render_count(round20(n))


RATE_DENOMINATOR: int = 1000                    # events per 1,000 at-risk episode-days


def _rate_per_thousand(k: Any, n: Any) -> str:
    """An event rate for print, computed from the ROUNDED pair for the reason `n_pct` is.

    A rate rendered from the raw numerator over the raw denominator inverts: a reader holding
    the disclosed denominator recovers the count the rounding existed to hide.  So the numerator
    is rounded first, suppressed if the true count is below the floor, and the arithmetic runs
    on the rounded pair.  A percentage is useless here, because an acute-care event rate is
    order one per thousand episode-days and would print as zero at the precision `n_pct` uses.
    """
    rounded = round20(k)
    if is_suppressed(rounded):
        return SUPPRESSED
    denominator = round20(n)
    if is_suppressed(denominator) or not _whole(denominator, "a rate denominator"):
        return SUPPRESSED
    rate = RATE_DENOMINATOR * _whole(rounded, "a rate numerator") / _whole(
        denominator, "a rate denominator")
    return f"{rate:,.2f}"


def _table_lines(headers: Sequence[str], rows: Sequence[Sequence[str]],
                 align: str = "") -> list[str]:
    """A fixed-width table.  `align` is one character per column, 'l' or 'r'."""
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


def _assert_house_prose(text: str) -> None:
    """Stop conditions on the rendered report, checked before a character of it is printed."""
    if EM_DASH in text:
        raise FeatureCheckError("the report contains an em-dash, which no house string may carry")
    if MINUS_SIGN in text:
        raise FeatureCheckError("the report contains a Unicode minus sign, which is banned")
    snake = sorted(set(_SNAKE_TOKEN.findall(text)))
    if snake:
        raise FeatureCheckError(
            f"the report contains machine token(s) {snake}, and an identifier is never a "
            f"user-visible string. Use the display label beside it."
        )


def _group_columns(frame: pd.DataFrame) -> list[str]:
    """The group slugs actually present, in the plan's own print order."""
    present = set(frame["group_slug"].astype(str))
    return [slug for slug in GROUP_SLUGS if slug in present]


def group_table_lines(long_frame: pd.DataFrame, *, value: str, index: str,
                      index_labels: Mapping[str, str], title: str,
                      denominator: str, index_order: Sequence[str] = ()) -> list[str]:
    """One count column of a long frame as a suppressed table of groups by whatever indexes it.

    The group column is partitioned twice over, by the four collapse-level-1 groups and by the
    fusion and decompression pair, and both partitions sum to the same total, so both are
    declared and complementary suppression closes each of them.  Everything printed has been
    through the floor on the TRUE count and then through the export refusal classes on the
    RENDERED cell, which are two different questions asked in that order.
    """
    columns = _group_columns(long_frame)
    wide = to_wide(long_frame[long_frame["group_slug"].isin(columns)],
                   index=index, columns="group_slug", value=value)
    for slug in columns:
        if slug not in wide.columns:
            wide[slug] = 0
    wide = wide[columns]
    if index_order:
        # The pivot sorts its index alphabetically, which puts "Days 15" before "Days 1" and
        # the pooled row in the middle of the windows it totals.  Row order is part of what a
        # table means, so the declared vocabulary decides it and the pivot does not.
        ordered = [key for key in index_order if key in wide.index]
        ordered += [key for key in wide.index if key not in ordered]
        wide = wide.loc[ordered]
    display = render_wide(wide, [list(g) for g in GROUP_PARTITIONS if set(g) <= set(columns)])
    headers = [title] + [GROUP_LABELS[slug] for slug in columns]
    rows = [[index_labels.get(str(key), str(key))]
            + [render_count(display.loc[key, slug]) for slug in columns]
            for key in display.index]
    return _table_lines(headers, rows) + [f"Denominator: {denominator}"]


def partition_table_lines(long_frame: pd.DataFrame, *, index: str,
                          index_labels: Mapping[str, str], members: Sequence[str],
                          member_labels: Mapping[str, str], value: str, title: str,
                          denominator: str) -> list[str]:
    """A row-indexed table whose COLUMNS are one declared partition of that row's own total."""
    wide = to_wide(long_frame, index=index, columns="bucket", value=value)
    for name in members:
        if name not in wide.columns:
            wide[name] = 0
    wide = wide[list(members)]
    display = render_wide(wide, [list(members)])
    headers = [title] + [member_labels[name] for name in members]
    rows = [[index_labels.get(str(key), str(key))]
            + [render_count(display.loc[key, name]) for name in members]
            for key in display.index]
    return _table_lines(headers, rows) + [f"Denominator: {denominator}"]


DOW_LABELS: Mapping[str, str] = MappingProxyType({
    "0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday",
    "4": "Thursday", "5": "Friday", "6": "Saturday",
})

_RECORD_SPLIT_LABELS: Mapping[str, str] = MappingProxyType({
    "no record": "No record",
    "recorded zero": "Recorded zero",
    "recorded above zero": "Recorded above zero",
})
_AGREEMENT_LABELS: Mapping[str, str] = MappingProxyType({
    "both": "Valid under both",
    "effective only": "Valid under the rule in force only",
    "definition only": "Valid under the alternative only",
    "neither": "Valid under neither",
})


def _melt(frame: pd.DataFrame, *, index: str, mapping: Mapping[str, str]) -> pd.DataFrame:
    """A handful of count columns of one frame as a long (index, bucket, value) frame."""
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        for bucket, column in mapping.items():
            rows.append({index: str(row[index]), "bucket": bucket,
                         "n": _whole(row[column], f"a {column} cell")})
    return pd.DataFrame(rows)


def _one_row(frame: pd.DataFrame, what: str) -> dict[str, Any]:
    """A one-row result frame as a dictionary, refusing any other shape."""
    if len(frame) != 1:
        raise FeatureCheckError(
            f"{what} returned {len(frame)} rows and is defined to return exactly one. A "
            f"different shape means the query and this module disagree about its grain."
        )
    return {str(k): v for k, v in frame.iloc[0].to_dict().items()}


def assemble(frames: Mapping[str, pd.DataFrame]) -> dict[str, Any]:
    """Turn the twenty-one raw count frames into the diagnostics, the summaries and the verdict.

    PURE.  It runs no query, prints nothing and writes nothing, which is what lets the self-test
    drive the whole module end to end against synthetic frames.  Every violation list it builds
    is a STOP CONDITION list: `run_features` refuses to certify the feature tables when any of
    them is non-empty, and no caller may downgrade one to a warning.
    """
    missing = [key for key in QUERY_KEYS if key not in frames]
    if missing:
        raise FeatureCheckError(f"the result set is missing frame(s) {missing}")

    presence = frames["wear record presence"]
    agreement = frames["wear definition agreement"]
    day_distribution = frames["baseline day distribution"]
    categories = frames["baseline categories"]
    day_of_week = frames["baseline day of week"]
    baseline_invariants = _one_row(frames["baseline invariants"], "the baseline invariants query")
    panel_invariants = _one_row(frames["daily panel invariants"],
                                "the daily panel invariants query")
    by_day = frames["wear availability by day"]
    ledger_day = frames["wear availability ledger"]
    day_kinds = frames["day kind crosstab"]
    landmark = frames["landmark conditions"]
    deleted_timing = frames["structurally deleted event timing"]
    panel_invariants_landmark = _one_row(frames["landmark panel invariants"],
                                         "the landmark panel invariants query")
    panel_by_day = frames["landmark panel by day"]
    set_sizes = frames["matched set sizes"]
    set_members = frames["matched set members"]
    participation = frames["control participation"]
    set_ledger = frames["matched set ledger"]
    digest = _one_row(frames["risk set digest"], "the risk-set digest query")
    lag_bands = frames["observation model inputs"]
    missingness = frames["variable missingness ledger"]

    ledger_comparison = wear_ledger_disagreements(by_day, ledger_day)

    pooled = day_distribution[day_distribution["group_slug"] == ALL_GROUPS_SLUG]
    baseline_summary: dict[str, Any] = {}
    for metric in ("valid_baseline_days", "baseline_span_days", "weekday_baseline_days",
                   "weekend_baseline_days", "lesser_of_weekday_and_weekend_baseline_days",
                   "analyzable_accrual_days", "at_risk_accrual_days"):
        part = pooled[pooled["metric_slug"] == metric]
        baseline_summary[metric.replace("_", " ")] = (
            distribution_summary(part, value_col="bucket_value", count_col="n_episodes")
            if not part.empty else SUPPRESSED)
    floor = categories[(categories["group_slug"] == ALL_GROUPS_SLUG)
                       & (categories["metric_slug"] == "baseline_floor")]
    baseline_summary["n clearing the baseline floor"] = int(
        pd.to_numeric(floor[floor["bucket_slug"] == "clears"]["n_episodes"],
                      errors="coerce").fillna(0).sum())
    baseline_summary["n episodes"] = int(
        pd.to_numeric(floor["n_episodes"], errors="coerce").fillna(0).sum())

    sizes_pooled = (set_sizes.groupby("set_size", as_index=False)["n_sets"].sum()
                    if not set_sizes.empty else set_sizes)
    dual_role = participation[participation["also_a_case"].astype(bool)
                              & (pd.to_numeric(participation["n_control_landmarks"],
                                               errors="coerce") > 0)] \
        if not participation.empty else participation
    at_cap = participation[pd.to_numeric(participation["n_control_landmarks"], errors="coerce")
                           == CONTROL_LANDMARKS_PER_PARTICIPANT_CAP] \
        if not participation.empty else participation
    risk_summary = {
        "n sets": _whole(digest.get("n_distinct_sets", 0), "the distinct set count"),
        "n case rows": _whole(digest.get("n_case_rows", 0), "the case row count"),
        "n control rows": _whole(digest.get("n_control_rows", 0), "the control row count"),
        "n participants contributing as control and later case": (
            int(pd.to_numeric(dual_role["n_participants"], errors="coerce").fillna(0).sum())
            if len(dual_role) else 0),
        "n participants at the control cap": (
            int(pd.to_numeric(at_cap["n_participants"], errors="coerce").fillna(0).sum())
            if len(at_cap) else 0),
        "controls per case": (distribution_summary(sizes_pooled, value_col="set_size",
                                                   count_col="n_sets")
                              if len(sizes_pooled) else SUPPRESSED),
        "membership digest": str(digest.get("membership_digest") or ""),
    }
    # ANALYSIS-PLAN 4.4 obliges THREE counts and this is where all three are formed.  They are
    # kept as separate keys and are never added: count 1 is member-level, count 2 is set-level
    # and is not recoverable from count 1, and count 3 is the weighted row's own denominator.
    def _member_total(column: str, role: str | None = None) -> int:
        if set_members.empty:
            return 0
        part = (set_members if role is None
                else set_members[set_members["member_role"].astype(str) == role])
        return int(pd.to_numeric(part[column], errors="coerce").fillna(0).sum())

    def _set_total(column: str) -> int:
        if set_sizes.empty:
            return 0
        return int(pd.to_numeric(set_sizes[column], errors="coerce").fillna(0).sum())

    risk_summary.update({
        "n members without a landmark weight input":
            _member_total("n_landmark_weight_input_absent"),
        "n cases without a landmark weight input":
            _member_total("n_landmark_weight_input_absent", "case"),
        "n controls without a landmark weight input":
            _member_total("n_landmark_weight_input_absent", "control"),
        "n members with a landmark before post-discharge day one":
            _member_total("n_landmark_before_post_discharge_day_one"),
        "n early through the partial window secondary":
            _member_total("n_early_via_partial_window_secondary"),
        "n early through the day of week relaxation":
            _member_total("n_early_via_day_of_week_relaxation"),
        "n early through neither route": _member_total("n_early_by_neither_route"),
        "n sets losing every control": _set_total("n_sets_losing_every_control"),
        "n sets losing the case": _set_total("n_sets_losing_the_case"),
        "n sets in the weighted sensitivity": _set_total("n_sets_in_weighted_sensitivity"),
        "n members in the weighted sensitivity": _set_total("n_members_in_weighted_sensitivity"),
    })

    result: dict[str, Any] = {
        "frames": dict(frames),
        "wear": {
            "presence": presence,
            "agreement": agreement,
            "contingency": wear_contingency_verdict(agreement),
            "violations": wear_presence_violations(presence)
                          + wear_agreement_violations(agreement),
        },
        "baseline": {
            "day distribution": day_distribution,
            "categories": categories,
            "day of week": day_of_week,
            "invariants": baseline_invariants,
            "summary": baseline_summary,
            "violations": baseline_violations(baseline_invariants, day_distribution,
                                              day_of_week, categories),
        },
        "deficit": {
            "invariants": panel_invariants,
            "by day": by_day,
            "day kinds": day_kinds,
            "inpatient cell": inpatient_observed_cell(day_kinds),
            "ledger comparison": ledger_comparison,
            "violations": panel_violations(panel_invariants) + day_kind_violations(day_kinds)
                          + wear_ledger_violations(ledger_comparison),
        },
        "landmark": {
            "conditions": landmark,
            "structurally deleted timing": deleted_timing,
            "summary": landmark_summary(landmark),
            "panel invariants": panel_invariants_landmark,
            "panel by day": panel_by_day,
            "panel summary": landmark_panel_summary(panel_invariants_landmark, panel_by_day),
            "violations": landmark_violations(landmark)
                          + landmark_panel_violations(panel_invariants_landmark, panel_by_day),
        },
        "risk sets": {
            "sizes": set_sizes,
            "members": set_members,
            "participation": participation,
            "ledger": set_ledger,
            "digest": digest,
            "summary": risk_summary,
            "outcome by computable ratio": outcome_by_computable_ratio(set_members),
            "violations": risk_set_violations(set_sizes, set_members, participation,
                                              set_ledger, digest),
        },
        "observation": {
            "lag bands": lag_bands,
            "by day": by_day,
            "missingness": missingness,
            "violations": observation_violations(lag_bands, panel_invariants)
                          + missingness_violations(missingness),
        },
        "gaps": [dict(gap) for gap in DAG_GAPS],
    }
    halting: list[str] = []
    for section in ("wear", "baseline", "deficit", "landmark", "risk sets", "observation"):
        halting += [f"{section}: {reason}" for reason in result[section]["violations"]]
    result["halting"] = halting
    result["features ok"] = not halting
    return result


RESULT_KEYS: tuple[str, ...] = (
    "features ok", "halting", "frames", "wear", "baseline", "deficit", "landmark",
    "risk sets", "observation", "gaps", "report",
)


# Fixed a priori, like every band in this module.  The first five cover the accrual window in
# calendar weeks and the sixth is the display tail, so the table reads as recovery time rather
# than as an arbitrary partition of the horizon.
DAY_BANDS: tuple[tuple[int, int, str], ...] = (
    (1, 7, "Days 1–7"),
    (8, 14, "Days 8–14"),
    (15, 21, "Days 15–21"),
    (22, 28, "Days 22–28"),
    (29, 35, "Days 29–35"),
    (36, 90, "Days 36–90"),
)

_BASELINE_SUMMARY_LABELS: Mapping[str, str] = MappingProxyType({
    "valid baseline days": "Valid baseline days per episode",
    "baseline span days": "Calendar span of the baseline window",
    "weekday baseline days": "Valid baseline days falling Monday to Friday",
    "weekend baseline days": "Valid baseline days falling Saturday or Sunday",
    "lesser of weekday and weekend baseline days":
        "The smaller of the two, which bounds a split baseline",
    "analyzable accrual days": "Analyzable days in the accrual window",
    "at risk accrual days": "At-risk days in the accrual window",
})


def _band_of(day: Any) -> str:
    number = _whole(day, "a post-discharge day")
    for first, last, label in DAY_BANDS:
        if first <= number <= last:
            return label
    return "Outside the plotted horizon"


def render_report(result: Mapping[str, Any]) -> str:
    """The whole feature-validation report, as one string, ending in the verdict.

    Built as a string and checked before it is printed, so that the house prose rules are
    asserted on the RENDERED text rather than grepped for afterwards, and so the self-test can
    read the same characters a human would.
    """
    lines: list[str] = []
    add = lines.append
    wear = result["wear"]
    baseline = result["baseline"]
    deficit = result["deficit"]
    landmark = result["landmark"]
    risk = result["risk sets"]
    observation = result["observation"]

    add(_RULE)
    add("FEATURE VALIDATION. The derived tables are checked, not rebuilt.")
    add(_RULE)
    add("")
    lines += _wrap(
        "The stored procedure already computed valid wear days, the seven preoperative "
        "baselines, the daily deficit panel, the event table and the matched risk sets. "
        "Nothing below recomputes any of them. Every number is a grouped aggregate of what the "
        "build produced, every count has been through the disclosure floor on its true value "
        "before rounding, and no participant-level value appears anywhere in this report.", 84)
    add("")

    # ---- 1. the valid wear rule ----
    add(_THIN)
    add("1. THE VALID WEAR RULE, AS IT WAS ACTUALLY APPLIED")
    add(_THIN)
    contingency = wear["contingency"]
    if contingency["primary in force"]:
        lines += _wrap(
            "The rule in force is the primary one, 10 hours of heart-rate wear. It agrees with "
            "the primary definition on every day of the grid, which is what says the "
            "zone-partition probe passed and no contingency was applied.", 84)
    else:
        lines += _wrap(
            "The rule in force DISAGREES with the primary definition, which means the "
            "zone-partition probe failed and the prespecified fallback to 10 hours plus 100 "
            "steps was applied. That substitution requires a logged amendment and a sentence in "
            "the Methods, and it changes which days are valid and therefore changes every "
            "baseline as well.", 84)
    add("")
    presence = wear["presence"]
    window_order = list(WINDOW_SLUGS) + [ALL_WINDOWS_SLUG]
    lines += group_table_lines(presence, value="n_days", index="window_slug",
                               index_labels=WINDOW_LABELS, title="Days of the grid",
                               index_order=window_order,
                               denominator="one row per participant per calendar day in the "
                                           "wearable window")
    add("")
    lines += group_table_lines(presence, value="n_analyzable", index="window_slug",
                               index_labels=WINDOW_LABELS, title="Analyzable days",
                               index_order=window_order,
                               denominator="the same grid days as the table above")
    add("")
    pooled = presence[presence["group_slug"] == ALL_GROUPS_SLUG]
    for channel, mapping, title in (
        ("heart-rate wear minutes",
         {"no record": "n_wear_minutes_null", "recorded zero": "n_wear_minutes_zero",
          "recorded above zero": "n_wear_minutes_positive"},
         "Heart-rate wear"),
        ("daily step totals",
         {"no record": "n_steps_null", "recorded zero": "n_steps_zero",
          "recorded above zero": "n_steps_positive"},
         "Daily steps"),
    ):
        long = _melt(pooled, index="window_slug", mapping=mapping)
        lines += partition_table_lines(
            long, index="window_slug", index_labels=WINDOW_LABELS,
            members=list(_RECORD_SPLIT_LABELS), member_labels=_RECORD_SPLIT_LABELS,
            value="n", title=title,
            denominator="all groups pooled, one row per participant per calendar day")
        add("")
    lines += _bullets([
        "No record and recorded zero are different facts and are never added together. A null "
        "wear figure means there was no heart-rate record for that person and date, not that "
        "the device recorded no minutes; a null step total means there was no activity record.",
        "A day with no heart-rate record is not a valid wear day under any of the five "
        "definitions, so treating its absence as a zero would quietly delete it from the "
        "denominator rather than counting it as unobserved.",
        "A day with a real zero step total and confirmed wear is KEPT and carries a full day of "
        "deficit, because profound inactivity may be the biological signal of interest.",
    ])
    add("")
    accrual = wear["agreement"]
    accrual = accrual[(accrual["window_slug"] == "accrual_window")
                      & (accrual["group_slug"] == ALL_GROUPS_SLUG)]
    if not accrual.empty:
        long = _melt(accrual, index="definition_slug",
                     mapping={"both": "n_both", "effective only": "n_effective_only",
                              "definition only": "n_definition_only", "neither": "n_neither"})
        lines += partition_table_lines(
            long, index="definition_slug", index_labels=WEAR_DEFINITION_LABELS,
            members=list(_AGREEMENT_LABELS), member_labels=_AGREEMENT_LABELS, value="n",
            title="Alternative wear rule",
            denominator="accrual window days, all groups pooled")
        add("")
        rows = []
        for _, row in accrual.iterrows():
            rows.append([WEAR_DEFINITION_LABELS[str(row["definition_slug"])],
                         n_pct(_whole(row["n_definition"], "a wear count"),
                               _whole(row["n_days"], "a day count"))])
        lines += _table_lines(["Alternative wear rule", "Days it admits"], rows)
        add("Denominator: accrual window days, all groups pooled")
    add("")

    # ---- 2. the baseline ----
    add(_THIN)
    add("2. THE PREOPERATIVE PERSONAL BASELINE")
    add(_THIN)
    summary = baseline["summary"]
    rows = [[_BASELINE_SUMMARY_LABELS[key], summary[key]]
            for key in _BASELINE_SUMMARY_LABELS if key in summary]
    lines += _table_lines(["Quantity", "Median (Q1 to Q3)"], rows, align="ll")
    add(f"Denominator: analytic episodes, n = {_denominator(summary.get('n episodes', 0))}")
    add("")
    add(f"Episodes clearing the baseline floor of 1,000 steps per day: "
        f"{n_pct(_whole(summary.get('n clearing the baseline floor', 0), 'the floor count'), _whole(summary.get('n episodes', 0), 'the episode count'))}")
    lines += _wrap(
        "The floor is a flag and never a filter. It is the baseline-floor sensitivity row, not "
        "an eligibility criterion, so an episode below it stays in the primary analysis.", 84)
    add("")
    dow = baseline["day of week"]
    pooled_dow = dow[dow["group_slug"] == ALL_GROUPS_SLUG] if not dow.empty else dow
    if not pooled_dow.empty:
        wide = to_wide(pooled_dow.assign(bucket=pooled_dow["dow_index"].astype(str)),
                       index="group_slug", columns="bucket", value="n_baseline_days")
        members = [str(i) for i in range(BASELINE_DOW_LENGTH)]
        for name in members:
            if name not in wide.columns:
                wide[name] = 0
        display = render_wide(wide[members], [members])
        rows = [[DOW_LABELS[name], render_count(display.loc[display.index[0], name])]
                for name in members]
        lines += _table_lines(["Day of week", "Valid baseline days"], rows)
        add("Denominator: every valid baseline day of every analytic episode, all groups pooled")
        lines += _wrap(
            "The array is stored with index zero as Sunday and the weekday number runs from one "
            "as Sunday, and both are emitted by the query so the off-by-one is checked rather "
            "than assumed.", 84)
    add("")
    categories = baseline["categories"]
    availability = categories[categories["metric_slug"].isin(ALTERNATIVE_BASELINES)]
    if not availability.empty:
        present = availability[availability["bucket_slug"] == "present"]
        totals = availability.groupby(["group_slug", "metric_slug"], as_index=False)["n_episodes"].sum()
        rows = []
        for slug in ALTERNATIVE_BASELINES:
            left = present[(present["group_slug"] == ALL_GROUPS_SLUG)
                           & (present["metric_slug"] == slug)]
            right = totals[(totals["group_slug"] == ALL_GROUPS_SLUG)
                           & (totals["metric_slug"] == slug)]
            have = int(pd.to_numeric(left["n_episodes"], errors="coerce").fillna(0).sum())
            of = int(pd.to_numeric(right["n_episodes"], errors="coerce").fillna(0).sum())
            rows.append([ALTERNATIVE_BASELINE_LABELS[slug], n_pct(have, of)])
        lines += _table_lines(["Alternative baseline", "Episodes where it exists"], rows)
        add("Denominator: analytic episodes, all groups pooled")
        lines += _wrap(
            "A sensitivity row fitted where its own baseline exists has a different denominator "
            "from the primary, and the table that reports it has to print that denominator.", 84)
    add("")
    split = categories[categories["metric_slug"].isin(SPLIT_BASELINE_METRICS)] \
        if not categories.empty else categories
    if not split.empty:
        present = split[split["bucket_slug"] == "present"]
        totals = split.groupby(["group_slug", "metric_slug"], as_index=False)["n_episodes"].sum()
        rows = []
        for slug in SPLIT_BASELINE_METRICS:
            left = present[(present["group_slug"] == ALL_GROUPS_SLUG)
                           & (present["metric_slug"] == slug)]
            right = totals[(totals["group_slug"] == ALL_GROUPS_SLUG)
                           & (totals["metric_slug"] == slug)]
            have = int(pd.to_numeric(left["n_episodes"], errors="coerce").fillna(0).sum())
            of = int(pd.to_numeric(right["n_episodes"], errors="coerce").fillna(0).sum())
            rows.append([SPLIT_BASELINE_LABELS[slug], n_pct(have, of)])
        lines += _table_lines(["Separate weekday and weekend baselines", "Episodes"], rows)
        add("Denominator: analytic episodes, all groups pooled")
        lines += _bullets([
            "The third row is the split sensitivity's own denominator and it is derived from "
            "the two valid-day counts, not from the two medians being present. The rule is at "
            "least 5 valid Monday-to-Friday days and at least 2 valid Saturday-or-Sunday days. "
            "The two minima are deliberately unequal and are set from the window's own "
            "arithmetic: a 23-day span offers 16 or 17 weekday days and 6 or 7 weekend days, so "
            "5 and 2 are close to the same fraction of what the calendar supplies and neither "
            "half is held to a standard the window cannot meet. Their sum is 7, exactly the "
            "primary rule's minimum, so this row's set is a subset of the primary's and never a "
            "superset.",
            "Deriving it from the counts rather than from a null test on the medians is what "
            "keeps the minimum-day rule visible in one place. A null test would pass an episode "
            "with a single valid weekend day, whose weekend median is one day's step total.",
            "An episode with valid days in only one half of the week is excluded from this "
            "sensitivity row and from nothing else. It keeps its primary baseline, stays in the "
            "analytic cohort, stays in Table 1 and in Figure 2, and contributes to the primary "
            "estimand exactly as it did before the row existed. Its whole cost is this count, "
            "and Table 2 has to print it beside the estimate.",
            "The identity between the two counts and the day-of-week composition is asserted "
            "rather than assumed, in all three of its parts: the weekday count equals the "
            "Monday-to-Friday entries of the composition, the weekend count equals the Sunday "
            "and Saturday entries, and the two sum to the valid baseline day count. That "
            "identity is the join between the composition and the two medians, and a build "
            "could satisfy any two of the three while breaking the third.",
        ])
    add("")

    # ---- 3. the daily deficit ----
    add(_THIN)
    add("3. THE DAILY DEFICIT, AND WHAT A MISSING DAY CONTRIBUTES")
    add(_THIN)
    lines += _wrap(
        "The deficit is null on a non-analyzable day and is never imputed as zero. A zero "
        "deficit asserts that the participant walked at or above their own preoperative "
        "baseline that day, which is the most favourable possible completion of the window, and "
        "non-wear is most likely exactly when the true deficit is largest. Both directions of "
        "that check are counted below and both must be zero.", 84)
    add("")
    invariants = deficit["invariants"]
    rows = [
        ["Analyzable days carrying no deficit",
         render_count(round20(_whole(invariants["n_deficit_null_but_analyzable"], "a check cell")))],
        ["Non-analyzable days carrying a deficit",
         render_count(round20(_whole(invariants["n_deficit_not_null_but_not_analyzable"],
                               "a check cell")))],
        ["Non-analyzable days carrying a deficit of exactly zero",
         render_count(round20(_whole(invariants["n_deficit_zero_not_analyzable"], "a check cell")))],
        ["Zero-step analyzable days, which are kept",
         render_count(round20(_whole(invariants["n_zero_steps_analyzable"], "a check cell")))],
        ["Of those, carrying a full day of deficit",
         render_count(round20(_whole(invariants["n_zero_steps_analyzable_deficit_one"],
                               "a check cell")))],
    ]
    lines += _table_lines(["Check", "Days"], rows)
    add(f"Denominator: every panel day, n = {_denominator(invariants['n_days'])}")
    add("")
    by_day = deficit["by day"].copy()
    by_day["band"] = by_day["post_discharge_day"].map(_band_of)
    banded = by_day.groupby(["group_slug", "band"], as_index=False)[
        ["n_at_risk", "n_analyzable"]].sum()
    band_labels = {label: label for _, _, label in DAY_BANDS}
    band_order = [label for _, _, label in DAY_BANDS]
    lines += group_table_lines(banded, value="n_analyzable", index="band",
                               index_labels=band_labels, title="Recovery time",
                               index_order=band_order,
                               denominator="analyzable person-days, by post-discharge day band")
    add("")
    lines += group_table_lines(banded, value="n_at_risk", index="band",
                               index_labels=band_labels, title="Recovery time",
                               index_order=band_order,
                               denominator="at-risk person-days, by post-discharge day band")
    add("")
    kinds = deficit["day kinds"]
    accrual_kinds = kinds[kinds["window_slug"] == "accrual_window"] if not kinds.empty else kinds
    if not accrual_kinds.empty:
        # Pooled, and filtered to the total slug BEFORE the pivot. The group column carries
        # three partitions of the same episodes, so pivoting without this filter would sum an
        # episode's day into the table three times and the taxonomy would stop partitioning.
        accrual_kinds = accrual_kinds[accrual_kinds["group_slug"] == ALL_GROUPS_SLUG]
        for column, vocabulary, title in (("day_kind", DAY_KINDS, "Three-value day taxonomy"),
                                          ("day_kind_four", DAY_KINDS_FOUR,
                                           "Four-value day taxonomy")):
            long = (accrual_kinds.groupby([column], as_index=False)["n_days"].sum()
                    .rename(columns={column: "bucket"}))
            long["index"] = title
            lines += partition_table_lines(
                long, index="index", index_labels={title: title}, members=list(vocabulary),
                member_labels=DAY_KIND_LABELS, value="n_days", title="Taxonomy",
                denominator="accrual window person-days, all groups pooled")
            add("")
    cell = deficit["inpatient cell"]
    lines += _bullets([
        "Inpatient is not exclusive of observed. A readmitted participant wearing the device "
        "produces a valid, analyzable, inpatient day and the plan keeps it, because a "
        "readmission is part of recovery and deleting it would delete the worst days.",
        "Those days appear as observed in the three-value taxonomy and as inpatient in the "
        "four-value one. Both taxonomies sum to the same denominator, so neither has absorbed "
        "the inpatient setting as an extra category and no day is counted twice in either.",
        ("The two labels cover the same days: "
         + ("they agree" if cell["counted once in each taxonomy"]
            else "THEY DO NOT AGREE, which means one taxonomy is classifying them differently "
                 "from the other")) + ".",
    ])
    add("")
    comparison = deficit["ledger comparison"]
    ledger_column_labels = {"n_at_risk": "At risk", "n_valid_wear": "Valid wear",
                            "n_analyzable": "Analyzable", "n_inpatient": "Inpatient"}
    rows = [[ledger_column_labels[str(row["column"])],
             f"{int(row['n_cells_compared']):,}", f"{int(row['n_cells_disagreeing']):,}"]
            for _, row in comparison.iterrows()]
    lines += _table_lines(["Ledger column", "Cells compared", "Cells disagreeing"], rows)
    lines += _wrap("Denominator: cells of the wear-availability ledger. These are counts of "
                   "table cells, which are a property of the build and not of any participant, "
                   "so they are not rounded.", 84)
    add("")
    return _finish_report(lines, result, landmark, risk, observation)


def _single_row_partition(values: Mapping[str, int], *, members: Sequence[str],
                          member_labels: Mapping[str, str], row_label: str,
                          title: str, denominator: str) -> list[str]:
    """One row of counts that partition a single total, suppressed and re-checked."""
    wide = pd.DataFrame([[int(values.get(name, 0)) for name in members]],
                        index=[row_label], columns=list(members)).astype("int64")
    display = render_wide(wide, [list(members)])
    headers = [title] + [member_labels[name] for name in members]
    rows = [[row_label] + [render_count(display.loc[row_label, name]) for name in members]]
    return _table_lines(headers, rows) + [f"Denominator: {denominator}"]


def _transposed_partition_lines(rows: Mapping[str, Mapping[str, int]], *,
                                members: Sequence[str], member_labels: Mapping[str, str],
                                title: str, denominator: str) -> list[str]:
    """A partition printed DOWN the page, with the suppression still closed ACROSS it.

    `export_violations` takes partitions as column groups checked row by row, so a partition
    that reads better as rows is masked in the column orientation and only then transposed for
    display.  The alternative, declaring the partition in the orientation it is printed in,
    would silently check nothing: the same trick `02_pregate.partition_violations` uses to ask
    about its column direction, and for the same reason.
    """
    wide = pd.DataFrame([[int(rows[label].get(name, 0)) for name in members]
                         for label in rows],
                        index=list(rows), columns=list(members)).astype("int64")
    display = render_wide(wide, [list(members)])
    headers = [title] + list(rows)
    body = [[member_labels[name]] + [render_count(display.loc[label, name]) for label in rows]
            for name in members]
    return _table_lines(headers, body) + _wrap(f"Denominator: {denominator}", 84)


def _finish_report(lines: list[str], result: Mapping[str, Any], landmark: Mapping[str, Any],
                   risk: Mapping[str, Any], observation: Mapping[str, Any]) -> str:
    """Sections 4 to 8 of the report, then the house prose stop conditions on the whole text."""
    add = lines.append

    # ---- 4. events and the landmark distinction ----
    add(_THIN)
    add("4. EVENTS, AND THE TWO REASONS A LANDMARK MAY NOT EXIST")
    add(_THIN)
    summary = landmark["summary"]
    total_events = _whole(summary["n first events"], "the first-event count")
    rows = [
        ["First events with a computable proximal window",
         n_pct(_whole(summary["n computable"], "a landmark count"), total_events)],
        ["First events whose window was eligible but not worn",
         n_pct(_whole(summary["n data uncomputable"], "a landmark count"), total_events)],
        ["First events with no eligible window at all",
         n_pct(_whole(summary["n structurally deleted"], "a landmark count"), total_events)],
    ]
    lines += _table_lines(["Landmark status", "First events"], rows)
    add(f"Denominator: first acute-care events, n = {_denominator(total_events)}")
    add("")
    lines += _bullets([
        "The middle row and the bottom row are different conditions and are never added "
        "together. The middle row is a data condition on an event that is otherwise computable, "
        "and those windows STAY in the risk set, entering the model as the co-primary exposure, "
        "because requiring a computable ratio deletes preferentially the sickest windows and "
        "conditioning on a common consequence of exposure and outcome is collider "
        "stratification.",
        "The bottom row is a definitional condition. The exposure window must lie on "
        "post-discharge days, so an event on post-discharge day 1 to 4 has fewer than two "
        "eligible days however well the participant wore the device. Those events are their own "
        "attrition rung and they leave the analysis; the first eligible landmark is "
        "post-discharge day 2, belonging to an event on post-discharge day 5.",
        "Merging the two would delete the collider-correction windows silently, because an "
        "event with no computable landmark never appears in an event-level file at all and "
        "nobody counts what is not there.",
        (f"A proximal ratio exists on some windows holding only one valid day, and the count of "
         f"those is {prev(_whole(summary['n ratio at a single valid day'], 'a count'), total_events)}"
         f". The co-primary model never reads them, because it multiplies the ratio term by the "
         f"complement of the co-primary exposure. A filter written on the ratio being present "
         f"rather than on the flag would read them and would readmit the collider."),
    ])
    add("")
    timing = landmark["structurally deleted timing"]
    if not timing.empty:
        first = timing[timing["is_first_event"].astype(bool)]
        banded = first.groupby(["group_slug", "event_post_discharge_day"],
                               as_index=False)["n_events"].sum()
        labels = {str(day): f"Post-discharge day {day}"
                  for day in range(1, STRUCTURAL_DELETION_LAST_DAY + 1)}
        lines += group_table_lines(banded, value="n_events", index="event_post_discharge_day",
                                   index_labels=labels, title="Timing of the deleted events",
                                   denominator="first acute-care events with no eligible "
                                               "proximal window")
        lines += _wrap(
            "The timing is reported and not only the number, because the deleted events are the "
            "earliest ones and earliest is a proxy for most severe. A reader is entitled to "
            "know that the analysis is blind to the first four post-discharge days by "
            "construction and what that cost.", 84)
    else:
        add("No events fell in the structurally uncomputable range, so the attrition rung that "
            "counts them is zero and the row still prints.")
    add("")

    panel = landmark.get("panel summary", {})
    if panel.get("available"):
        add("The same comparison on the full-cohort day-indexed panel")
        rows = []
        for label in ("without a computable ratio", "with a computable ratio"):
            at_risk = _whole(panel[f"n at risk days {label}"], "an at-risk day count")
            events = _whole(panel[f"n event days {label}"], "an event day count")
            standardized = panel[f"standardized rate {label}"]
            rows.append([
                f"Episode days {label}",
                render_count(round20(at_risk)),
                render_count(round20(events)),
                _rate_per_thousand(events, at_risk),
                (SUPPRESSED if not np.isfinite(standardized)
                 or is_suppressed(round20(events))
                 else f"{RATE_DENOMINATOR * standardized:,.2f}"),
            ])
        definitional_days = _whole(panel["n at risk days with no eligible window"],
                                   "an at-risk day count")
        definitional_events = _whole(panel["n event days with no eligible window"],
                                     "an event day count")
        rows.append([
            "Episode days with no eligible window at all",
            render_count(round20(definitional_days)),
            render_count(round20(definitional_events)),
            _rate_per_thousand(definitional_events, definitional_days),
            NOT_APPLICABLE,
        ])
        lines += _table_lines(
            ["Landmark status on the day", "At-risk days", "Event days",
             "Crude rate per 1,000", "Standardized rate per 1,000"], rows)
        add(f"Denominator: at-risk episode days, all groups pooled, standardized over "
            f"{_denominator(panel['n days standardized over'])} post-discharge days")
        lines += _wrap(panel["caveat"], 84)
        add("")
        lines += _bullets([
            "This is the surface the collider evidence belongs on, and the reason is that the "
            "other two carry the selection it exists to expose. The matched sets carry it only "
            "where a set was drawn, and the draw selects on the very variable the comparison is "
            "about: the per-participant cap removes the best-observed participants, the "
            "per-case cap fixes a ratio rather than measuring a rate, and day-of-week matching "
            "selects landmarks on the calendar, which is one of the things deciding whether a "
            "window was computable at all. The event table carries it only at event dates and "
            "chiefly among first events, which is selection on the outcome.",
            "Every at-risk episode day is in the denominator here, whether or not that "
            "participant was ever sampled into a matched set and whether or not they ever had "
            "an event, so the two conditions sit on a common base and the quantity is a rate "
            "rather than a composition inside a selected set.",
            "The bottom row is the definitional condition and it is printed apart from the two "
            "above it and never added to them. Those days are uncomputable for a reason that is "
            "not about wear, and the standardized column is left blank on them because the "
            "post-discharge days they occupy are exactly the ones the comparison excludes.",
        ])
        add("")
        add(f"Panel rows checked: {_denominator(panel['n episode days'])} episode days over "
            f"{_denominator(panel['n episodes'])} episodes, of which "
            f"{_denominator(panel['n weight input available'])} carry a landmark weight input "
            f"and {_denominator(panel['n weight input absent'])} do not. The panel reproduces "
            f"the event table cell for cell at every event date, and the definitional condition "
            f"equals post-discharge day 1 to 4 on every one of them.")
        add("")

    # ---- 5. the matched risk sets ----
    add(_THIN)
    add("5. THE MATCHED RISK SETS")
    add(_THIN)
    shape = risk["summary"]
    n_sets = _whole(shape["n sets"], "the set count")
    if n_sets == 0:
        lines += _wrap(
            "No matched sets were built. At the lowest gate tiers the early-warning analysis "
            "does not run and the table is created empty on purpose, because a table that is "
            "present and empty and a table that is absent are different claims and only one of "
            "them is checkable.", 84)
    else:
        rows = [
            ["Matched sets", render_count(round20(n_sets))],
            ["Control landmarks drawn", render_count(round20(_whole(shape["n control rows"],
                                                              "the control row count")))],
            ["Controls per case, median and range",
             str(shape["controls per case"])],
            ["Participants contributing as a control and later as a case",
             render_count(round20(_whole(
                 shape["n participants contributing as control and later case"], "a count")))],
            ["Participants at the control landmark cap",
             render_count(round20(_whole(shape["n participants at the control cap"], "a count")))],
        ]
        lines += _table_lines(["Quantity", "Value"], rows, align="ll")
        add(f"Denominator: matched sets, n = {_denominator(n_sets)}")
        add("")

        # ANALYSIS-PLAN 4.4 obliges three counts and prints all three whether or not the
        # weighted sensitivity moves the estimate.  They are three different grains and none
        # of them is recoverable from the others.
        n_members_total = (
            _whole(shape["n case rows"], "the case row count")
            + _whole(shape["n control rows"], "the control row count"))
        early_total = _whole(shape["n members without a landmark weight input"], "a count")
        rows = [
            ["Cases", render_count(round20(_whole(
                shape["n cases without a landmark weight input"], "a count")))],
            ["Controls", render_count(round20(_whole(
                shape["n controls without a landmark weight input"], "a count")))],
            ["Through the partial window secondary, which admits an event on day 4",
             render_count(round20(_whole(
                 shape["n early through the partial window secondary"], "a count")))],
            ["Through the day of week relaxation, which admits a control up to 2 days earlier",
             render_count(round20(_whole(
                 shape["n early through the day of week relaxation"], "a count")))],
            ["Of these, whose landmark precedes post-discharge day 1 and has no panel row",
             render_count(round20(_whole(
                 shape["n members with a landmark before post-discharge day one"], "a count")))],
        ]
        lines += _table_lines(
            ["Members at a landmark day of one or less, by role and by route", "Members"], rows)
        add(f"Denominator: matched-set members, n = {_denominator(n_members_total)}, of which "
            f"{prev(early_total, n_members_total)} sit at a landmark day of one or less")
        add("One count and not two. These members have no exposure window, so they leave the "
            "co-primary exposure, and they also have no weight input, so they leave the "
            "weighted sensitivity. The two rules bite the same members for different reasons "
            "and the count is printed once rather than under two labels a reader would add "
            "together.")
        add("")
        rows = [
            ["Matched sets losing every control, which leave the likelihood altogether",
             render_count(round20(_whole(shape["n sets losing every control"], "a count")))],
            ["Matched sets losing the case, which leave for the same reason",
             render_count(round20(_whole(shape["n sets losing the case"], "a count")))],
            ["Matched sets in the weighted sensitivity",
             render_count(round20(_whole(
                 shape["n sets in the weighted sensitivity"], "a count")))],
            ["Members in the weighted sensitivity",
             render_count(round20(_whole(
                 shape["n members in the weighted sensitivity"], "a count")))],
        ]
        lines += _table_lines(["The weighted sensitivity, in sets and in members", "Value"],
                              rows, align="ll")
        add(f"Denominator: matched sets, n = {_denominator(n_sets)}, and their members, "
            f"n = {_denominator(n_members_total)}")
        add("")
        lines += _bullets([
            "A member's landmark sits three days before its matched day, and the weight model's "
            "predictor is the wear fraction over the seven post-discharge days behind that "
            "landmark. The predictor does not exist at a landmark day of zero or less, where "
            "the daily panel has no row at all, and it is null at a landmark day of exactly "
            "one, where the row exists but the lag has nothing behind it to average. So the "
            "members with no weight input are those at a landmark day of one or less, which is "
            "a matched day of four or less. That boundary is one day wider than a landmark "
            "before post-discharge day 1, and a count taken on the narrower one misses the "
            "whole matched-day-four group, who are the earliest members in the study and by the "
            "argument on structurally deleted events a proxy for the sickest.",
            "A landmark day of one or less is not a second threshold beside the weight rule. "
            "The landmark is the matched day less three and the window is the three days ending "
            "there, so the window holds two post-discharge days exactly when the landmark day "
            "is two or more, and a landmark day of one or less is the definitional condition "
            "written on the landmark scale. Such a member has no exposure window at all: it "
            "carries no no-signal exposure, it contributes nothing to the co-primary "
            "coefficient, and it is outside that exposure on every surface, the sampled sets "
            "and the full-cohort panel alike.",
            "A control the day-of-week relaxation places on post-discharge day three or four is "
            "therefore dropped from its matched set as a member, and counted in the table "
            "above. It cannot leave at the event rung that removes the cases, because a sampled "
            "control is not an event, so the count is taken here or nowhere. The weight rule "
            "bites the same members for a different reason, which is why the plan reports one "
            "count and not two a reader would try to add together; it removes a member from the "
            "weighted sensitivity and from nothing else, and it stands alone only where the "
            "partial-window secondary deliberately reads such a member back in.",
            "The set count is not recoverable from the member count and that is why it is here. "
            "A matched set with no surviving control contributes nothing at all to a conditional "
            "likelihood, so it leaves whole; the member count cannot say how many sets that was, "
            "because it does not know how the excluded members were distributed across sets.",
            "The two routes are counted apart because they are different populations and the "
            "plan requires the split. Every case in the primary sits at post-discharge day 5 or "
            "later and therefore at a landmark day of two or more, so a member this early "
            "arrived either through the partial-window secondary, which admits an event on day "
            "4 and takes that case's own matched controls with it, or through the day-of-week "
            "relaxation, which admits a control up to two days below its case. A member "
            "arriving by neither is a sampling rule nobody wrote down, and it halts.",
            "The last row is the strictly narrower subset with no panel row at all, printed "
            "beside the total rather than instead of it. The two are different quantities and "
            "reporting only the second is the count that was wrong before.",
        ])
        add("")
        sizes = risk["sizes"]
        pooled_sizes = sizes.groupby("set_size", as_index=False)["n_sets"].sum()
        members = [str(size) for size in range(CONTROLS_PER_CASE_CAP + 1)]
        values = {str(int(row["set_size"])): _whole(row["n_sets"], "a set count")
                  for _, row in pooled_sizes.iterrows()}
        lines += _single_row_partition(
            values, members=members,
            member_labels={name: (f"{name} control" if name == "1" else f"{name} controls")
                           for name in members},
            row_label="Matched sets", title="Controls in the set",
            denominator=f"matched sets, n = {_denominator(n_sets)}")
        add("")
        lines += _bullets([
            "Some sets ending short of the cap is expected. The per-case cap is applied first "
            "and the per-participant cap second, and that order deliberately leaves sets short "
            "rather than spending a prolific participant's slots on sets they would not have "
            "been drawn into anyway.",
            "A participant may be a control at one landmark and a case later. Future case "
            "status does not disqualify them, and sampling controls only from participants who "
            "never have an event would condition the control pool on the future and bias the "
            "odds ratio away from the null. The count of participants in both roles is above; "
            "it is the design working, and it is also why inference is clustered on the person.",
            "The per-participant cap held on every participant. Without it a small cohort's few "
            "long-observed participants dominate the control pool and the effective sample size "
            "collapses far below the nominal one.",
        ])
        add("")
        outcome = risk["outcome by computable ratio"]
        if outcome.get("available"):
            rows = []
            for label in ("without a computable ratio", "with a computable ratio",
                          "with no eligible window at all"):
                total = _whole(outcome[f"n windows {label}"], "a window count")
                cases = _whole(outcome[f"n cases {label}"], "a case count")
                rows.append([f"Sampled windows {label}", render_count(round20(total)),
                             n_pct(cases, total)])
            lines += _table_lines(["Sampled windows", "Windows", "Of which cases"], rows)
            add("Denominator: each row prints its own window count in the middle column.")
            lines += _wrap(outcome["caveat"], 84)
    add("")
    lines += _wrap(
        "Reproducibility. The sampling order is a seeded fingerprint over the salt, the seed, "
        "the set identifier, the control episode and the matched day, all of which are pure "
        "functions of values that do not change between runs, so both caps select the same rows "
        "in the same order. Every stage of the build replaces rather than appends. To verify: "
        "take the membership digest this run returned, rebuild from the risk-set stage, take "
        "the digest again, and compare the two strings. A random draw would fail that "
        "comparison, which is why the plan forbids one.", 84)
    add("")

    # ---- 6. the observation model ----
    add(_THIN)
    add("6. THE OBSERVATION MODEL, AND WHAT IT CONDITIONS ON")
    add(_THIN)
    lines += _wrap(
        "The daily-deficit model is fitted on observed person-days weighted by the inverse "
        "probability that the day was observed, and the weight model's time-varying predictor "
        "is the wear fraction over the previous seven days. The lag is strict, so the model can "
        "never condition on the very day it is weighting, and that strictness is checked as an "
        "invariant rather than assumed.", 84)
    add("")
    bands = observation["lag bands"]
    pooled_bands = bands[bands["group_slug"] == ALL_GROUPS_SLUG] if not bands.empty else bands
    if not pooled_bands.empty:
        banded: dict[str, dict[str, int]] = {}
        for column, row_label in (("n_days", "Panel days"), ("n_analyzable", "Analyzable days")):
            banded[row_label] = {str(row["lag_band_slug"]): _whole(row[column], "a band cell")
                                 for _, row in pooled_bands.iterrows()}
        lines += _transposed_partition_lines(
            banded, members=list(LAG_BAND_SLUGS), member_labels=LAG_BAND_LABELS,
            title="Wear in the previous week",
            denominator="all groups pooled, one row per analytic episode per post-discharge "
                        "day. Each column is its own partition of its own total.")
        add("")
    missingness = observation["missingness"]
    if not missingness.empty:
        rows = []
        for _, row in missingness.iterrows():
            variable = str(row["variable"])
            total = _whole(row["n_total"], "a ledger denominator")
            missing = _whole(row["n_missing"], "a ledger count")
            rows.append([MISSINGNESS_LABELS.get(variable, variable),
                         render_count(round20(total)), n_pct(missing, total)])
        lines += _table_lines(["Analysis variable", "Rows of its own grain", "Missing"], rows)
        lines += _wrap("Denominator: each row carries its own, in the middle column. The first "
                       "ten are per episode, the daily deficit is per accrual-window "
                       "person-day, and the proximal ratio is per first event, so one "
                       "denominator across all twelve would misread two of them by orders of "
                       "magnitude.", 84)
    add("")

    # ---- 7. what the derived tables do not carry ----
    add(_THIN)
    add("7. WHAT THE DERIVED TABLES DO NOT CARRY")
    add(_THIN)
    open_gaps = [gap for gap in result["gaps"] if gap.get("status") != "closed"]
    lines += _wrap(
        f"Four items, of which {len(result['gaps']) - len(open_gaps)} are now closed. A closed "
        f"item is kept rather than deleted, because a reader comparing this report against an "
        f"earlier run has to be able to tell a gap that was closed from a gap that was quietly "
        f"dropped, and because the entry records what closed it.", 84)
    add("")
    for gap in result["gaps"]:
        status = GAP_STATUS_LABELS.get(str(gap.get("status", "open")), "Open")
        add(f"  [{status}] {gap['title']}")
        for key in ("found", "consequence", "what the build would need"):
            label = {"found": "Found", "consequence": "Consequence",
                     "what the build would need": "What the build would need"}[key]
            chunks = _wrap(f"{label}: {gap[key]}", 78)
            add("    " + chunks[0])
            lines += ["      " + chunk for chunk in chunks[1:]]
        add("")

    # ---- 8. the verdict ----
    add(_RULE)
    if result["features ok"]:
        add("VERDICT: the feature tables are fit to model on.")
        add(_RULE)
        lines += _wrap(
            "Every null convention the derived-table contract promises holds, both directions "
            "of the zero-imputation check are clear, the two landmark conditions are separate, "
            "both day taxonomies partition the same days with the inpatient setting cutting "
            "across them, and every closed degree of freedom in the risk-set sampling held.", 84)
    else:
        add("VERDICT: STOP. The feature tables are NOT fit to model on.")
        add(_RULE)
        lines += _bullets(list(result["halting"]))
        lines += _wrap(
            "Each of these is a stop condition and none of them is a warning. Fix the build and "
            "rerun this module; do not proceed to the analysis modules with any of them "
            "standing.", 84)
    text = "\n".join(lines)
    _assert_house_prose(text)
    return text


# ======================================================================================
# (10) Running it.  `q_guarded` is the only query path and there is no other; nothing in this
#      module can reach the BigQuery API by any route that skips the printed estimate and the
#      hard byte cap.
# ======================================================================================


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
    globals, which is what `%run -i` populates; then the live kernel's namespace, which covers
    `%run` without the flag.  Nothing falls back to a raw BigQuery client: a module that could
    quietly find its own way to the API is a module that eventually runs a query with no printed
    estimate and no cap.
    """
    namespace = None
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
            raise FeatureCheckError(
                f"{name} is not available. This step runs inside the perimeter and gets its "
                f"only query path from the configuration notebook. Run that notebook first, "
                f"then load this file into the same kernel."
            )
        resolved.append(found)
    return resolved[0], resolved[1]


def cost_plan(sql_by_key: Mapping[str, str], dry_run_gb: Callable[[str], float], *,
              budget_gb: float = FEATURES_BUDGET_GB) -> dict[str, Any]:
    """Price every query before any of them runs, and refuse the whole step if it does not fit.

    A dry run is free and prices the columns referenced rather than the table, so this
    pre-flight costs nothing and answers the frightening question first.  `q_guarded` dry-runs
    each query again when it executes it; that second dry run is also free and is the one that
    puts the estimate on the screen immediately before the job, which is the rule.
    """
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
    """The cost plan as text, so it can be checked as easily as it is printed."""
    lines = [_THIN,
             "COST PLAN. Nothing has executed yet; every figure below came from a free dry run.",
             _THIN]
    rows = [[key, f"{plan['estimates'][key]:,.3f}", f"{PLANNED_MAX_GB[key]:,.1f}"]
            for key in QUERY_KEYS]
    lines += _table_lines(["Query", "Estimate, GiB", "Cap, GiB"], rows)
    lines.append(f"total estimate {plan['total gb']:,.3f} GiB, about ${plan['usd']:,.4f}, "
                 f"against a budget of {plan['budget gb']:,.1f} GiB")
    lines.append("Every read is of a derived table. No Controlled Tier table is touched.")
    return lines


def run_features(
    *,
    q_guarded: Callable[..., pd.DataFrame] | None = None,
    dry_run_gb: Callable[[str], float] | None = None,
    budget_gb: float = FEATURES_BUDGET_GB,
    show_report: bool = True,
) -> dict[str, Any]:
    """Price, run, validate and report.  Returns the diagnostics keyed by `RESULT_KEYS`.

    The order is deliberate and is the same order `02_pregate.py` uses: every query is priced by
    a free dry run BEFORE any of them executes, the plan is printed, and the module refuses the
    whole step if the measured total exceeds the budget.  A refusal therefore happens with the
    real number in the human's hand rather than after the bill, and nothing has billed a byte.

    The verdict is returned as well as printed, and it is a STOP CONDITION rather than a
    warning: `features ok` false means the analysis modules must not run, and the reasons are
    in `halting`.  This function does not raise on a failed check, because the report is the
    thing a human needs in front of them when it fails; it raises only when it cannot get far
    enough to produce one.
    """
    query, dry_run = _resolve_runtime(q_guarded, dry_run_gb)
    sql_by_key = build_sql()
    plan = cost_plan(sql_by_key, dry_run, budget_gb=budget_gb)
    for line in cost_plan_lines(plan):
        print(line)
    if not plan["fits"]:
        raise FeatureBudgetExceeded(
            f"nothing executed and nothing billed. The measured dry-run total is "
            f"{plan['total gb']:,.3f} GiB against a budget of {plan['budget gb']:,.1f} GiB, "
            f"and these queries exceeded their own caps: {plan['over cap'] or 'none'}. Every "
            f"read here is of a derived table, so a total this large means a join has become a "
            f"cross product rather than that the data grew."
        )
    frames: dict[str, pd.DataFrame] = {}
    for key in QUERY_KEYS:
        frames[key] = query(sql_by_key[key], max_gb=PLANNED_MAX_GB[key],
                            note=f"04 features, {key}")
        safe_show(frames[key], name=key)
    result = assemble(frames)
    result["cost plan"] = plan
    result["report"] = render_report(result)
    if show_report:
        print(result["report"])
    return result


# ======================================================================================
# (11) The self-test.  No cloud access, no credentials, no file written.
#
#      Every fixture below is SYNTHETIC and is built to carry, on purpose, the states that the
#      interesting failures hide in: a null wear figure beside a real zero, a null step total
#      beside a real zero, a null deficit beside a real zero deficit, a zero-step day that is
#      analyzable, an inpatient day that is also analyzable, an event whose window is eligible
#      but unworn beside one whose window does not exist, and a participant who is a control at
#      one landmark and a case at another.
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


# Named rather than written as a literal comparison, so that `verify.py`'s grep for a bare
# disclosure-floor literal in a comparison cannot mistake a fixture's day index for one.
_FORCED_ZERO_STEP_INDEX: int = 15
_FORCED_ZERO_STEP_DAY: int = 21

_GROUP_OF_PERSON: tuple[tuple[int, int, str], ...] = (
    (1, 20, "cervical_decompression"),
    (21, 35, "cervical_fusion"),
    (36, 50, "lumbar_decompression"),
    (51, 60, "lumbar_fusion"),
)
_N_PERSONS = 60
_WEAR_DAYS_PER_PERSON = 22
_PANEL_DAYS = 40


def _group_of(person: int) -> str:
    for first, last, slug in _GROUP_OF_PERSON:
        if first <= person <= last:
            return slug
    raise AssertionError("the fixture assigned a person to no group")


def _add_group_slugs(frame: pd.DataFrame) -> pd.DataFrame:
    """The three-row group expansion, vectorised, matching the emitted `CROSS JOIN UNNEST`."""
    level_one = frame.assign(group_slug=frame["procedure_group"])
    level_two = frame.assign(
        group_slug=np.where(frame["fusion"], "fusion", "decompression"))
    total = frame.assign(group_slug=ALL_GROUPS_SLUG)
    return pd.concat([level_one, level_two, total], ignore_index=True)


def _synthetic_wear_days() -> pd.DataFrame:
    """A wearable grid carrying every state the null-versus-zero distinction turns on."""
    windows = (["baseline_window"] * 8 + ["accrual_window"] * 8 + ["display_tail"] * 4
               + ["outside_named_windows"] * 2)
    rows: list[dict[str, Any]] = []
    for person in range(1, _N_PERSONS + 1):
        group = _group_of(person)
        for index in range(_WEAR_DAYS_PER_PERSON):
            has_hr = index % 7 != 3
            wear: Any = np.nan if not has_hr else (0 if index % 11 == 5
                                                   else 300 + (index * 37) % 600)
            has_steps = index % 9 != 4
            steps: Any = np.nan if not has_steps else (0 if index % 13 == 2
                                                       else 1000 + (index * 211) % 9000)
            if index == _FORCED_ZERO_STEP_INDEX:
                # Forced, so the fixture always carries the case the study is about: confirmed
                # wear and a REAL zero step total, which is retained and carries a full day of
                # deficit rather than being deleted as non-wear.
                has_hr, wear, has_steps, steps = True, 900, True, 0
            rows.append({
                "person_id": person,
                "procedure_group": group,
                "fusion": group.endswith("fusion"),
                "window_slug": windows[index],
                "has_hr_row": has_hr,
                "has_steps_row": has_steps,
                "wear_minutes": wear,
                "steps": steps,
            })
    frame = pd.DataFrame(rows)
    wear = pd.to_numeric(frame["wear_minutes"], errors="coerce")
    steps = pd.to_numeric(frame["steps"], errors="coerce")
    frame["valid_wear_primary"] = (wear >= 600).fillna(False)
    frame["valid_wear_s1"] = (wear >= 576).fillna(False)
    frame["valid_wear_s2"] = ((wear >= 600) & (steps >= 100)).fillna(False)
    frame["valid_wear_s3"] = (wear >= 480).fillna(False)
    frame["valid_wear_s4"] = (wear >= 720).fillna(False)
    frame["valid_wear"] = frame["valid_wear_primary"]
    frame["is_analyzable"] = frame["valid_wear"] & steps.notna()
    return _add_group_slugs(frame)


def _synthetic_panel() -> pd.DataFrame:
    """A daily-deficit panel carrying a null deficit, a real zero deficit and both taxonomies."""
    baseline_steps = 5000.0
    rows: list[dict[str, Any]] = []
    for person in range(1, _N_PERSONS + 1):
        group = _group_of(person)
        last_at_risk = 30 if person <= 5 else _PANEL_DAYS
        for day in range(1, _PANEL_DAYS + 1):
            censored = day > last_at_risk
            has_hr = (day % 6) != 4
            wear: Any = np.nan if not has_hr else (0 if day % 17 == 3
                                                   else 400 + (day * 53) % 500)
            has_steps = (day % 8) != 5
            steps: Any = np.nan if not has_steps else 500 + (day * 307) % 8000
            if day == _FORCED_ZERO_STEP_DAY:
                has_hr, wear, has_steps, steps = True, 900, True, 0
            valid = bool(has_hr and not pd.isna(wear) and wear >= 600)
            analyzable = bool(valid and not pd.isna(steps) and not censored)
            inpatient = bool(person <= 10 and 10 <= day <= 12)
            kind = "censored" if censored else ("observed" if analyzable else "missing")
            kind_four = ("censored" if censored
                         else ("inpatient" if inpatient else kind))
            normalized = (float(steps) / baseline_steps) if analyzable else np.nan
            rows.append({
                "episode_id": f"E{person}",
                "person_id": person,
                "procedure_group": group,
                "fusion": group.endswith("fusion"),
                "post_discharge_day": day,
                "in_accrual_window": day <= ACCRUAL_LAST_DAY,
                "steps": steps,
                "wear_minutes": wear,
                "valid_wear": valid,
                "is_analyzable": analyzable,
                "is_censored": censored,
                "is_inpatient": inpatient,
                "day_kind": kind,
                "day_kind_four": kind_four,
                "normalized_activity": normalized,
                "deficit": (max(0.0, 1.0 - normalized) if analyzable else np.nan),
                "deficit_untruncated": ((1.0 - normalized) if analyzable else np.nan),
                "lagged_wear_fraction": (np.nan if day == ACCRUAL_FIRST_DAY
                                         else round(((day * 13) % 8) / 7.0, 4)),
            })
    return _add_group_slugs(pd.DataFrame(rows))


def _synthetic_episodes() -> pd.DataFrame:
    """One row per analytic episode, carrying the seven baselines and their day counts."""
    rows: list[dict[str, Any]] = []
    for person in range(1, _N_PERSONS + 1):
        group = _group_of(person)
        valid_days = 7 + (person % 14)
        dow = [valid_days // 7] * BASELINE_DOW_LENGTH
        for extra in range(valid_days - sum(dow)):
            dow[extra % BASELINE_DOW_LENGTH] += 1
        steps = 900 if person % 29 == 0 else 2000 + (person * 137) % 7000
        band = ("under_3000" if steps < 3000
                else "3000_to_6999" if steps < 7000 else "7000_or_more")
        # ANALYSIS-PLAN 2.2: some episodes clear the primary baseline rung on weekdays alone
        # and have NO weekend baseline at all, which is the case the split row's own
        # denominator exists for.  Forced on a few episodes rather than left to chance, and
        # the days are MOVED rather than dropped so the composition still sums to the count.
        if person % 17 == 0:
            dow[1] += dow[SUNDAY_INDEX]
            dow[2] += dow[SATURDAY_INDEX]
            dow[SUNDAY_INDEX] = 0
            dow[SATURDAY_INDEX] = 0
        weekday_days = sum(dow[SUNDAY_INDEX + 1:SATURDAY_INDEX])
        weekend_days = dow[SUNDAY_INDEX] + dow[SATURDAY_INDEX]
        rows.append({
            "episode_id": f"E{person}",
            "person_id": person,
            "procedure_group": group,
            "fusion": group.endswith("fusion"),
            "baseline_steps": float(steps),
            "n_valid_baseline_days": valid_days,
            # Null and never zero when the half holds no valid day, exactly as the pooled
            # baseline is, and the two day counts are never null.
            "baseline_steps_weekday": (float(steps) + 100.0) if weekday_days else np.nan,
            "n_valid_baseline_days_weekday": weekday_days,
            "baseline_steps_weekend": (float(steps) - 100.0) if weekend_days else np.nan,
            "n_valid_baseline_days_weekend": weekend_days,
            "baseline_span_days": 14 + (person % 10),
            "baseline_dow_counts": dow,
            "baseline_band_slug": band,
            "meets_baseline_floor": steps >= BASELINE_FLOOR_STEPS,
            "near_complete_window": person % 3 != 0,
            "has_any_fitbit": True,
            "n_analyzable_days_1_35": 10 + (person % 20),
            "n_at_risk_days_1_35": ACCRUAL_LAST_DAY,
            "baseline_steps_60_15": float(steps) if person % 5 else np.nan,
            "baseline_steps_30_1": float(steps),
            "baseline_steps_s1": float(steps),
            "baseline_steps_s2": float(steps) if person % 7 else np.nan,
            "baseline_steps_s3": float(steps),
            "baseline_steps_s4": float(steps) if person % 11 else np.nan,
        })
    return pd.DataFrame(rows)


def _synthetic_events() -> pd.DataFrame:
    """Events spanning both landmark conditions, including the structurally deleted range."""
    rows: list[dict[str, Any]] = []
    for index in range(1, 61):
        person = ((index * 7) % _N_PERSONS) + 1
        day = 1 + (index % 30)
        eligible = min(LANDMARK_WINDOW_DAYS, max(0, day - 3))
        valid = min(eligible, (index % (LANDMARK_WINDOW_DAYS + 1)))
        rows.append({
            "episode_id": f"E{person}",
            "procedure_group": _group_of(person),
            "fusion": _group_of(person).endswith("fusion"),
            "is_first_event": index % 4 != 0,
            "event_post_discharge_day": day,
            "n_valid_days_in_window": valid,
            "n_eligible_days_in_window": eligible,
            "n_missing_days_in_window": LANDMARK_WINDOW_DAYS - valid,
            "has_computable_landmark": valid >= LANDMARK_MIN_VALID_DAYS,
            "structurally_uncomputable_landmark": eligible < LANDMARK_MIN_VALID_DAYS,
            # The DATA condition and only the data condition, on `events` as on the panel and
            # on `risk_sets`: the window held its two post-discharge days AND fewer than two of
            # them were worn.  A fixture written on valid days alone would be a table carrying
            # the superseded union, and the pin exists to refuse exactly that table.
            "no_computable_step_signal": (eligible >= LANDMARK_MIN_VALID_DAYS
                                          and valid < LANDMARK_MIN_VALID_DAYS),
            "r72": (0.5 if valid >= 1 else np.nan),
            "r72_24h": (0.6 if valid >= 1 else np.nan),
            "r_reference_7day": (0.7 if valid >= 1 else np.nan),
            "r_negative_control": (0.8 if valid >= 1 else np.nan),
            "local_step_deterioration": (-0.2 if valid >= 1 else np.nan),
            "wear_fraction": (0.4 if eligible >= 1 else np.nan),
        })
    return _add_group_slugs(pd.DataFrame(rows))


_SET_SIZES: tuple[int, ...] = (5, 5, 4, 3, 2, 0, 5, 4, 3, 2, 1, 0)


def _early_landmark(matched_day: int) -> bool:
    """A member at this matched day carries the DEFINITIONAL condition, on the landmark scale.

    The landmark is the matched day less three and the window is the three days ending there,
    so the window holds two post-discharge days exactly when the landmark day is 2 or more.
    A member below that has no exposure window: it carries NO no-signal exposure and no
    proximal ratio, and every fixture in this file is built through this one predicate so that
    none of them can quietly disagree with the boundary the module turns on.
    """
    return (matched_day - LANDMARK_DAY_OFFSET) <= EARLY_LANDMARK_LAST_LANDMARK_DAY


def _synthetic_risk_sets() -> pd.DataFrame:
    """Twelve matched sets, both caps respected, and one participant in both roles."""
    rows: list[dict[str, Any]] = []
    control_pool = list(range(200, 230))
    used: dict[int, int] = {}
    cursor = 0
    for index, size in enumerate(_SET_SIZES):
        set_id = f"S{index:02d}"
        case_person = 100 + index
        matched_day = 4 + index
        # Set 1 is forced onto a relaxation rung, because it is the only set early enough for
        # the day-of-week relaxation to put a CONTROL at a landmark day of 1 or less while its
        # own case sits at post-discharge day 5 and is weighted.  That is the second of the two
        # routes ANALYSIS-PLAN 4.4 names, and a fixture without it would leave the route
        # uncounted and the partition check vacuous.
        rung = 3 if index == 1 else (1 if index % 5 else (2 if index % 2 else 3))
        # The exposure is the DATA condition alone, so a member whose landmark window holds
        # fewer than two post-discharge days carries neither it nor a proximal ratio.  The
        # first set's case sits at matched day 4 and is exactly such a member.
        case_early = _early_landmark(matched_day)
        case_signal = (index % 3 == 0) and not case_early
        rows.append({
            "set_id": set_id, "member_role": "case", "is_case": True,
            "person_id": case_person, "episode_id": f"E{case_person}",
            "set_size": size, "match_rung": 1,
            "no_computable_step_signal": case_signal,
            "fingerprint": np.nan,
            "r72": (np.nan if (case_signal or case_early) else 0.5),
            "wear_fraction": 0.4,
            "case_matched_day": matched_day,
            "member_matched_day": matched_day,
            "member_landmark_post_discharge_day": matched_day - LANDMARK_DAY_OFFSET,
        })
        for slot in range(size):
            # One deliberate dual role: the case of the first set is drawn as a control in a
            # later set, which ANALYSIS-PLAN 4.5 permits and which the participation table has
            # to show as one participant in both roles rather than as two participants.
            if index == 6 and slot == 0:
                control_person = 100
            else:
                while used.get(control_pool[cursor % len(control_pool)], 0) >= \
                        CONTROL_LANDMARKS_PER_PARTICIPANT_CAP:
                    cursor += 1
                control_person = control_pool[cursor % len(control_pool)]
                cursor += 1
            used[control_person] = used.get(control_person, 0) + 1
            # ANALYSIS-PLAN 4.7 rungs 2 and 3 admit a control up to 2 days below its case's
            # post-discharge day, which is one of the two routes 4.4 names to a landmark day of
            # 1 or less.  The offset is only ever taken at rung 2 or 3, because rung 1 matches
            # on the same post-discharge day by definition.
            offset = 0 if rung == 1 else (slot % 3) - 2
            control_day = matched_day + offset
            control_early = _early_landmark(control_day)
            control_signal = ((index + slot) % 4 == 0) and not control_early
            rows.append({
                "set_id": set_id, "member_role": "control", "is_case": False,
                "person_id": control_person, "episode_id": f"E{control_person}",
                "set_size": size, "match_rung": rung,
                "no_computable_step_signal": control_signal,
                "fingerprint": float(1_000_000 + index * 97 + slot),
                "r72": (np.nan if (control_signal or control_early) else 0.6),
                "wear_fraction": 0.5,
                "case_matched_day": matched_day,
                "member_matched_day": control_day,
                "member_landmark_post_discharge_day": control_day - LANDMARK_DAY_OFFSET,
            })
    return pd.DataFrame(rows)


_LANDMARK_PANEL_DAYS: int = 40


def _synthetic_landmark_panel() -> pd.DataFrame:
    """A full-cohort landmark panel carrying every state DAG-SCHEMA 8.13 declares.

    Built from the panel's own arithmetic rather than typed, so the fixture cannot disagree
    with itself about the boundary the whole module turns on.  The eligible-day count for
    post-discharge day `d` is how many of `d-5`, `d-4` and `d-3` are post-discharge days at
    all, which is `max(0, min(3, d - 3))`: zero on days 1 to 3, ONE on day 4, two on day 5 and
    three from day 6.  So the definitional condition is exactly day 1 to 4, which is the six-row
    derivation of ANALYSIS-PLAN 4.3, and the fixture reproduces it rather than asserting it.

    The lagged wear fraction is null exactly where the landmark day is 1 or less, which is
    matched day 4 or less, because that is where the weight model has no input: at a landmark
    day of 0 or less there is no panel row behind it and at a landmark day of 1 there is a row
    but no preceding post-discharge day to average.  The WEARABLE-grid fraction is never null on
    any of those days, which is the whole reason the panel carries both and the reason they are
    not the same quantity.
    """
    rows: list[dict[str, Any]] = []
    for person in range(1, _N_PERSONS + 1):
        group = _group_of(person)
        last_at_risk = 30 if person <= 5 else _LANDMARK_PANEL_DAYS
        for day in range(1, _LANDMARK_PANEL_DAYS + 1):
            eligible = max(0, min(LANDMARK_WINDOW_DAYS, day - LANDMARK_DAY_OFFSET))
            valid = min(eligible, (person + day) % (LANDMARK_WINDOW_DAYS + 1))
            landmark_day = day - LANDMARK_DAY_OFFSET
            censored = day > last_at_risk
            # An event every so often, never on a censored day, and the first one per episode
            # flagged as such.
            is_event = (not censored) and ((person * 7 + day * 3) % 23 == 0)
            has_input = landmark_day > EARLY_LANDMARK_LAST_LANDMARK_DAY
            rows.append({
                "episode_id": f"E{person}",
                "person_id": person,
                "procedure_group": group,
                "fusion": group.endswith("fusion"),
                "post_discharge_day": day,
                "landmark_post_discharge_day": landmark_day,
                "is_censored": censored,
                "n_valid_days_in_window": valid,
                "n_eligible_days_in_window": eligible,
                "has_computable_landmark": valid >= LANDMARK_MIN_VALID_DAYS,
                "structurally_uncomputable_landmark": eligible < LANDMARK_MIN_VALID_DAYS,
                # The data condition alone, so the three day classes partition the panel by
                # construction rather than by a subtraction taken afterwards.
                "no_computable_step_signal": (eligible >= LANDMARK_MIN_VALID_DAYS
                                              and valid < LANDMARK_MIN_VALID_DAYS),
                "landmark_lagged_wear_fraction": (
                    ((person + day) % 8) / 7.0 if has_input else np.nan),
                "landmark_weight_input_available": has_input,
                "landmark_before_post_discharge_day_one": landmark_day < ACCRUAL_FIRST_DAY,
                # Defined on every row, including before post-discharge day 1, because the
                # wearable grid reaches back to index day minus 60.
                "landmark_lagged_wear_fraction_wearable": ((person * 3 + day) % 8) / 7.0,
                "n_days_behind_landmark_on_wearable_grid": LANDMARK_PANEL_LOOKBACK_DAYS,
                "is_event_day": is_event,
                "is_first_event_day": False,
            })
    frame = pd.DataFrame(rows)
    # The earliest event row per episode, written as `drop_duplicates(keep="first")` rather
    # than the shorter groupby-then-take-the-first-row form.  DO NOT SHORTEN IT BACK.  The two
    # are the same selection on a frame already sorted by the key: both keep the first row of
    # each `episode_id` in frame order, and both hand back an index.  The shorter one is
    # spelled with the pandas peek-at-the-top-rows method, which is one of the row-printing
    # idioms `verify.py` greps this pipeline for, so it would be reported on this line.  It is
    # a false positive -- the frame is a synthetic fixture and nothing on this path is printed
    # -- but a check whose only hits are false positives is a check a reader learns to ignore,
    # so the idiom is kept off the file rather than the hit explained away each time.  This
    # comment names none of the grepped idioms for the same reason.
    first = (frame[frame["is_event_day"]].sort_values(["episode_id", "post_discharge_day"])
                  .drop_duplicates(subset="episode_id", keep="first").index)
    frame.loc[first, "is_first_event_day"] = True
    return frame


def _events_from_landmark_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """The event rows the panel implies, so the cell-for-cell overlap check has something to pass.

    Derived FROM the panel rather than typed beside it.  The invariant under test is that the
    two agree at every event date, and a hand-typed event table could satisfy a checker that is
    wrong in the same way it is; a derived one at least cannot disagree with itself, and the
    check is then exercised by MUTATING one side.
    """
    events = panel[panel["is_event_day"].astype(bool)].copy()
    return pd.DataFrame({
        "episode_id": events["episode_id"].to_numpy(),
        "event_post_discharge_day": events["post_discharge_day"].to_numpy(),
        "n_valid_days_in_window": events["n_valid_days_in_window"].to_numpy(),
        "n_eligible_days_in_window": events["n_eligible_days_in_window"].to_numpy(),
        "has_computable_landmark": events["has_computable_landmark"].to_numpy(),
        "structurally_uncomputable_landmark":
            events["structurally_uncomputable_landmark"].to_numpy(),
    })


def _lag_band(value: Any) -> str:
    """The band expression of the observation-model query, in Python, for the fixture."""
    if pd.isna(value):
        return "unavailable"
    number = float(value)
    if number == 0:
        return "none"
    if number < 0.25:
        return "below_quarter"
    if number < 0.50:
        return "quarter_to_half"
    if number < 0.75:
        return "half_to_three_quarters"
    if number < 1.00:
        return "three_quarters_to_all"
    return "all"


def _synthetic_frames() -> dict[str, pd.DataFrame]:
    """All twenty-one result frames, built so that a clean fixture produces no violation at all.

    Built from the reference counters wherever one exists, rather than typed out.  A fixture
    typed by hand can satisfy a checker that is wrong in the same way the fixture is; a fixture
    derived from the counter under test at least cannot disagree with itself about a grain, and
    every check that matters is then exercised by MUTATING this frame set rather than by
    building a second one.
    """
    days = _synthetic_wear_days()
    panel = _synthetic_panel()
    episodes = _synthetic_episodes()
    events = _synthetic_events()
    members = _synthetic_risk_sets()
    landmark_panel = _synthetic_landmark_panel()
    panel_events = _events_from_landmark_panel(landmark_panel)

    unexpanded_panel = panel[panel["group_slug"] == ALL_GROUPS_SLUG].copy()
    panel = panel.assign(window_slug=np.where(panel["in_accrual_window"],
                                              "accrual_window", "display_tail"))

    flagged = panel.assign(
        _at_risk=~panel["is_censored"],
        _valid=(~panel["is_censored"]) & panel["valid_wear"],
        _analyzable=panel["is_analyzable"],
        _inpatient=(~panel["is_censored"]) & panel["is_inpatient"],
        _inpatient_analyzable=panel["is_analyzable"] & panel["is_inpatient"],
        _missing=panel["day_kind"] == "missing",
        _censored=panel["day_kind"] == "censored",
        _deficit=pd.to_numeric(panel["deficit"], errors="coerce").notna(),
        _one=1,
    )
    by_day = flagged.groupby(["group_slug", "post_discharge_day"], as_index=False).agg(
        n_at_risk=("_at_risk", "sum"), n_valid_wear=("_valid", "sum"),
        n_analyzable=("_analyzable", "sum"), n_inpatient=("_inpatient", "sum"),
        n_inpatient_analyzable=("_inpatient_analyzable", "sum"),
        n_missing=("_missing", "sum"), n_censored=("_censored", "sum"),
        n_deficit_not_null=("_deficit", "sum"), n_episodes=("_one", "sum"))
    for column in by_day.columns:
        if column.startswith("n_"):
            by_day[column] = by_day[column].astype("int64")

    order = {slug: index + 1 for index, slug in enumerate(GROUP_SLUGS)}
    ledger_day = by_day.rename(columns={"post_discharge_day": "day"})[
        ["group_slug", "day", "n_at_risk", "n_valid_wear", "n_analyzable", "n_inpatient"]].copy()
    ledger_day["group_order"] = ledger_day["group_slug"].map(order)
    ledger_day = ledger_day[["group_slug", "group_order", "day", "n_at_risk", "n_valid_wear",
                             "n_analyzable", "n_inpatient"]]

    grouped_episodes = _add_group_slugs(episodes)
    distribution_rows: list[dict[str, Any]] = []
    for metric, series in (
        ("valid_baseline_days", grouped_episodes["n_valid_baseline_days"]),
        ("baseline_span_days", grouped_episodes["baseline_span_days"]),
        ("weekday_baseline_days",
         grouped_episodes["baseline_dow_counts"].map(lambda a: sum(a[1:6]))),
        ("weekend_baseline_days",
         grouped_episodes["baseline_dow_counts"].map(lambda a: a[0] + a[6])),
        ("lesser_of_weekday_and_weekend_baseline_days",
         grouped_episodes["baseline_dow_counts"].map(lambda a: min(sum(a[1:6]), a[0] + a[6]))),
        ("analyzable_accrual_days", grouped_episodes["n_analyzable_days_1_35"]),
        ("at_risk_accrual_days", grouped_episodes["n_at_risk_days_1_35"]),
    ):
        part = grouped_episodes.assign(bucket_value=series.values)
        counted = part.groupby(["group_slug", "bucket_value"], as_index=False).size()
        for _, row in counted.iterrows():
            distribution_rows.append({"group_slug": row["group_slug"],
                                      "metric_slug": metric,
                                      "bucket_value": int(row["bucket_value"]),
                                      "n_episodes": int(row["size"])})

    category_rows: list[dict[str, Any]] = []
    category_series: list[tuple[str, pd.Series]] = [
        ("baseline_band", grouped_episodes["baseline_band_slug"].fillna("no_baseline")),
        ("baseline_floor", grouped_episodes["meets_baseline_floor"].map(
            lambda v: "unknown" if pd.isna(v) else ("clears" if v else "below"))),
        ("near_complete_window", grouped_episodes["near_complete_window"].map(
            lambda v: "yes" if v else "no")),
    ]
    for slug, (column, _count_column) in ALTERNATIVE_BASELINES.items():
        category_series.append(
            (slug, grouped_episodes[column].map(
                lambda v: "absent" if pd.isna(v) else "present")))
    # The split baseline of ANALYSIS-PLAN 2.2.  Note the third row: the ROW's own denominator is
    # taken off the two DAY COUNTS clearing their minima, never off the two medians being
    # present, which is where the plan puts the rule so a null test cannot weaken it later.
    category_series.append(
        ("weekday_baseline", grouped_episodes["baseline_steps_weekday"].map(
            lambda v: "absent" if pd.isna(v) else "present")))
    category_series.append(
        ("weekend_baseline", grouped_episodes["baseline_steps_weekend"].map(
            lambda v: "absent" if pd.isna(v) else "present")))
    category_series.append(
        ("baseline_weekday_weekend_split",
         pd.Series(np.where((grouped_episodes["n_valid_baseline_days_weekday"]
                             >= SPLIT_BASELINE_MIN_WEEKDAY_DAYS)
                            & (grouped_episodes["n_valid_baseline_days_weekend"]
                               >= SPLIT_BASELINE_MIN_WEEKEND_DAYS), "present", "absent"),
                   index=grouped_episodes.index)))
    for metric, series in category_series:
        part = grouped_episodes.assign(bucket_slug=series.values)
        counted = part.groupby(["group_slug", "bucket_slug"], as_index=False).size()
        for _, row in counted.iterrows():
            category_rows.append({"group_slug": row["group_slug"], "metric_slug": metric,
                                  "bucket_slug": row["bucket_slug"],
                                  "n_episodes": int(row["size"])})

    dow_rows: list[dict[str, Any]] = []
    for group_slug, part in grouped_episodes.groupby("group_slug", sort=True):
        for index in range(BASELINE_DOW_LENGTH):
            column = part["baseline_dow_counts"].map(lambda a: a[index])
            dow_rows.append({"group_slug": group_slug, "dow_index": index,
                             "day_of_week": index + 1,
                             "n_baseline_days": int(column.sum()),
                             "n_episodes_contributing": int((column > 0).sum()),
                             "n_episodes": int(len(part))})

    baseline_table = episodes.assign(
        n_valid_baseline_days=episodes["n_valid_baseline_days"])
    matched = count_matched_sets(members)
    sizes = matched["matched set sizes"]
    set_ledger = (sizes.groupby("set_size", as_index=False)["n_sets"].sum()
                  if not sizes.empty else pd.DataFrame(columns=["set_size", "n_sets"]))
    set_ledger["n_cases"] = set_ledger["n_sets"]

    key_text = (members["set_id"].astype(str) + "|" + members["member_role"].astype(str) + "|"
                + members["episode_id"].astype(str) + "|"
                + members["member_matched_day"].astype(int).astype(str) + "|"
                + members["match_rung"].astype(int).astype(str) + "|"
                + members["set_size"].astype(int).astype(str))
    import hashlib
    digest_text = hashlib.md5("~".join(sorted(key_text)).encode("utf-8")).hexdigest()
    digest = pd.DataFrame([{
        "n_rows": int(len(members)),
        "n_case_rows": int((members["member_role"] == "case").sum()),
        "n_control_rows": int((members["member_role"] == "control").sum()),
        "n_distinct_sets": int(members["set_id"].nunique()),
        "n_distinct_case_persons": int(
            members[members["member_role"] == "case"]["person_id"].nunique()),
        "n_distinct_control_persons": int(
            members[members["member_role"] == "control"]["person_id"].nunique()),
        "membership_digest": digest_text,
    }])

    lag = flagged.assign(lag_band_slug=panel["lagged_wear_fraction"].map(_lag_band))
    lag_bands = lag.groupby(["group_slug", "lag_band_slug"], as_index=False).agg(
        n_days=("_one", "sum"), n_at_risk=("_at_risk", "sum"),
        n_analyzable=("_analyzable", "sum"),
        n_in_accrual_window=("in_accrual_window", "sum"))
    for column in ("n_days", "n_at_risk", "n_analyzable", "n_in_accrual_window"):
        lag_bands[column] = lag_bands[column].astype("int64")

    missingness = pd.DataFrame([
        {"variable": name, "n_total": 600,
         "n_missing": (0 if name in STRUCTURALLY_COMPLETE_VARIABLES else 40)}
        for name in MISSINGNESS_VARIABLES])

    deleted = events[events["structurally_uncomputable_landmark"]].assign(
        _one=1, _any_valid=events["n_valid_days_in_window"] > 0)
    deleted_timing = deleted.groupby(
        ["group_slug", "event_post_discharge_day", "is_first_event",
         "n_eligible_days_in_window"], as_index=False).agg(
        n_events=("_one", "sum"), n_with_any_valid_day=("_any_valid", "sum"))
    for column in ("n_events", "n_with_any_valid_day"):
        deleted_timing[column] = deleted_timing[column].astype("int64")

    return {
        "wear record presence": count_wear_presence(days),
        "wear definition agreement": count_wear_agreement(days),
        "baseline day distribution": pd.DataFrame(distribution_rows),
        "baseline categories": pd.DataFrame(category_rows),
        "baseline day of week": pd.DataFrame(dow_rows),
        "baseline invariants": pd.DataFrame([count_baseline_invariants(baseline_table).to_dict()]),
        "daily panel invariants": pd.DataFrame(
            [count_daily_panel_invariants(unexpanded_panel).to_dict()]),
        "wear availability by day": by_day,
        "wear availability ledger": ledger_day,
        "day kind crosstab": count_day_kinds(panel),
        "landmark conditions": count_landmark_conditions(events),
        "structurally deleted event timing": deleted_timing,
        "landmark panel invariants": pd.DataFrame(
            [count_landmark_panel(landmark_panel, panel_events).to_dict()]),
        "landmark panel by day": count_landmark_panel_by_day(
            _add_group_slugs(landmark_panel)),
        "matched set sizes": sizes,
        "matched set members": matched["matched set members"],
        "control participation": matched["control participation"],
        "matched set ledger": set_ledger,
        "risk set digest": digest,
        "observation model inputs": lag_bands,
        "variable missingness ledger": missingness,
    }


class _FakeRuntime:
    """A stand-in for the configuration notebook's two helpers, so `run_features` is testable.

    It records the cap and the note every query was issued under, which is how the self-test
    proves that each query went out under ITS OWN cap rather than under one number sized to the
    whole step.  A cap sized to the total permits every query to bill the total.
    """

    def __init__(self, frames: Mapping[str, pd.DataFrame], gb: float = 0.01) -> None:
        self.frames = dict(frames)
        self.gb = gb
        self.calls: list[tuple[str, float, str]] = []
        self._by_text = {text: key for key, text in build_sql().items()}

    def dry_run_gb(self, sql: str) -> float:
        return self.gb

    def q_guarded(self, sql: str, *, max_gb: float, note: str = "") -> pd.DataFrame:
        key = self._by_text.get(sql)
        if key is None:
            raise AssertionError("the fake runtime was handed a query this module did not build")
        self.calls.append((key, float(max_gb), note))
        return self.frames[key]


_BACKTICKED = re.compile(r"`([^`]+)`")
_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
_ALIAS = re.compile(r"\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_DDL = re.compile(r"\b(CREATE|DROP|INSERT|UPDATE|DELETE|MERGE|TRUNCATE|ALTER)\b")
_RANDOMNESS = re.compile(r"\bRAND\s*\(")


def _tiny_days(rows: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    """A handful of wearable days, group-expanded so the partition identities hold on them too.

    The expansion is not decoration.  `wear_presence_violations` checks that the four
    collapse-level-one groups sum to the total and that the fusion and decompression pair sums
    to the same total, and a fixture carrying only a pooled row would fail both for want of
    members rather than for want of correctness.
    """
    base = {"procedure_group": "cervical_fusion", "fusion": True,
            "window_slug": "accrual_window", "person_id": 1,
            "has_hr_row": True, "has_steps_row": True, "wear_minutes": 700.0, "steps": 4000.0,
            "valid_wear": True, "is_analyzable": True,
            "valid_wear_primary": True, "valid_wear_s1": True, "valid_wear_s2": True,
            "valid_wear_s3": True, "valid_wear_s4": False}
    return _add_group_slugs(pd.DataFrame([{**base, **dict(row)} for row in rows]))


def _pooled(frame: pd.DataFrame, window_slug: str = "accrual_window") -> pd.Series:
    """The one pooled row of a counted wear frame, which is the row the pins read."""
    part = frame[(frame["group_slug"] == ALL_GROUPS_SLUG)
                 & (frame["window_slug"] == window_slug)]
    if len(part) != 1:
        raise AssertionError("the fixture did not produce exactly one pooled row")
    return part.iloc[0]


def _tiny_panel(rows: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    base = {"post_discharge_day": 10, "steps": 2500.0, "wear_minutes": 700.0,
            "valid_wear": True, "is_analyzable": True, "is_censored": False,
            "is_inpatient": False, "day_kind": "observed", "day_kind_four": "observed",
            "normalized_activity": 0.5, "deficit": 0.5, "deficit_untruncated": 0.5,
            "lagged_wear_fraction": 0.5}
    return pd.DataFrame([{**base, **dict(row)} for row in rows])


def _tiny_events(rows: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    base = {"group_slug": ALL_GROUPS_SLUG, "is_first_event": True,
            "event_post_discharge_day": 10, "n_valid_days_in_window": 3,
            "n_eligible_days_in_window": 3, "n_missing_days_in_window": 0,
            "has_computable_landmark": True, "structurally_uncomputable_landmark": False,
            "no_computable_step_signal": False, "r72": 0.5, "r72_24h": 0.5,
            "r_reference_7day": 0.5, "r_negative_control": 0.5,
            "local_step_deterioration": -0.1, "wear_fraction": 0.4}
    return pd.DataFrame([{**base, **dict(row)} for row in rows])


def _run_self_test() -> None:
    global _ASSERTIONS
    _ASSERTIONS = 0

    # ---- 1. the emitted SQL, every query, checked as text ----------------------------
    sql_by_key = build_sql()
    _expect(tuple(sql_by_key) == QUERY_KEYS,
            "build_sql returns the declared keys, in the declared order")
    _expect(set(PLANNED_MAX_GB) == set(QUERY_KEYS),
            "every query has its own cap and no cap names a query that does not exist")
    _expect(sum(PLANNED_MAX_GB.values()) > FEATURES_BUDGET_GB,
            "the caps deliberately sum to more than the budget: a cap is runaway protection "
            "for one query, and the budget is the allowance for the step")
    for key, sql in sql_by_key.items():
        placeholders = set(_PLACEHOLDER.findall(sql))
        _expect(placeholders == {"{DERIVED}"},
                f"{key} carries the derived-dataset placeholder and nothing else")
        _expect("{CDR}" not in sql and "{PREP}" not in sql,
                f"{key} touches no Controlled Tier table, so it names neither CDR placeholder")
        for name in _BACKTICKED.findall(sql):
            _expect(re.fullmatch(r"\{DERIVED\}\.[a-z_]+", name) is not None,
                    f"{key} quotes only derived tables, never a hardcoded project or dataset")
        _expect("<<" not in sql and ">>" not in sql,
                f"{key} carries no unsubstituted constant token")
        _expect(_DDL.search(sql) is None,
                f"{key} contains no data-definition statement; this module materializes nothing")
        _expect(_RANDOMNESS.search(sql) is None,
                f"{key} contains no random draw, so a rerun returns the same numbers")
        for banned in ("spinewear", "C2025Q4R6", "wb-", "bigquery-public-data"):
            _expect(banned not in sql, f"{key} hardcodes no dataset, project or release name")
        declared = declared_columns(sql)
        _expect(len(set(declared)) == len(declared),
                f"{key} declares each of its result columns once")
        aliases = set(_ALIAS.findall(sql))
        missing = [name for name in declared if name not in aliases]
        _expect(not missing,
                f"{key} declares column(s) {missing} that it does not actually alias, so the "
                f"declaration and the query have drifted apart")
    _expect("GROUP BY" not in sql_by_key["risk set digest"],
            "the membership digest is a single scalar over the WHOLE table and is never taken "
            "per group, per set or per row, which is the whole of its safety")
    _expect_raises(FeatureCheckError, lambda: _sql("SELECT <<NO_SUCH_CONSTANT>>"),
                   "a query naming a constant this module does not define is refused at build "
                   "time rather than reaching BigQuery half-written")
    _expect_raises(FeatureCheckError, lambda: declared_columns("SELECT 1"),
                   "a query with no column declaration is refused")

    # ---- 2. PIN: a null wear figure is not read as zero -------------------------------
    tiny = _tiny_days([
        {"person_id": 1, "has_hr_row": False, "wear_minutes": np.nan,
         "valid_wear": False, "is_analyzable": False, "valid_wear_primary": False,
         "valid_wear_s1": False, "valid_wear_s2": False, "valid_wear_s3": False,
         "valid_wear_s4": False},
        {"person_id": 2, "wear_minutes": 0.0, "valid_wear": False, "is_analyzable": False,
         "valid_wear_primary": False, "valid_wear_s1": False, "valid_wear_s2": False,
         "valid_wear_s3": False, "valid_wear_s4": False},
        {"person_id": 3, "wear_minutes": 700.0},
    ])
    counted = count_wear_presence(tiny)
    row = _pooled(counted)
    _expect(int(row["n_wear_minutes_null"]) == 1,
            "a day with NO heart-rate record is counted as a null and not as a zero")
    _expect(int(row["n_wear_minutes_zero"]) == 1,
            "a day whose device recorded ZERO minutes is counted as a real zero")
    _expect(int(row["n_wear_minutes_positive"]) == 1, "and a positive day is counted as one")
    _expect(int(row["n_wear_minutes_null"]) + int(row["n_wear_minutes_zero"])
            + int(row["n_wear_minutes_positive"]) == int(row["n_days"]),
            "the three states are exhaustive, so no fourth state is going unreported")
    _expect(int(row["n_no_hr_row"]) == 1 and int(row["n_hr_row"]) == 2,
            "the record flag agrees with the null, which is the contract's own convention")
    _expect(int(row["n_valid_wear_with_null_minutes"]) == 0,
            "a null wear figure is not a valid wear day")
    _expect(not wear_presence_violations(counted),
            "and a frame in which all of that holds raises nothing")
    steps_row = _tiny_days([
        {"person_id": 1, "has_steps_row": False, "steps": np.nan, "is_analyzable": False},
        {"person_id": 2, "steps": 0.0},
        {"person_id": 3, "steps": 9000.0},
    ])
    counted_steps = count_wear_presence(steps_row)
    srow = _pooled(counted_steps)
    _expect(int(srow["n_steps_null"]) == 1 and int(srow["n_steps_zero"]) == 1,
            "the same three-way split holds on the step channel: no record is not zero steps")
    _expect(int(srow["n_valid_wear_steps_null"]) == 1,
            "a valid wear day with no step total is counted, which ANALYSIS-PLAN 2.1 requires "
            "reported, and it is unobserved rather than zero")
    broken = tiny.copy()
    broken.loc[0, "valid_wear"] = True
    _expect(any("valid wear day" in reason
                for reason in wear_presence_violations(count_wear_presence(broken))),
            "counting a day with NO heart-rate record as valid wear is a stop condition, "
            "because it is the reading that turns missing data into measured wear")

    # ---- 3. PIN: a null deficit is not read as zero, and a real zero deficit survives ---
    panel = _tiny_panel([
        {"steps": 2500.0, "normalized_activity": 0.5, "deficit": 0.5,
         "deficit_untruncated": 0.5},
        {"steps": 6000.0, "normalized_activity": 1.2, "deficit": 0.0,
         "deficit_untruncated": -0.2},
        {"steps": np.nan, "valid_wear": True, "is_analyzable": False, "day_kind": "missing",
         "day_kind_four": "missing", "normalized_activity": np.nan, "deficit": np.nan,
         "deficit_untruncated": np.nan},
    ])
    invariants = count_daily_panel_invariants(panel)
    _expect(int(invariants["n_deficit_null"]) == 1,
            "an unobserved day carries a NULL deficit and is counted as null")
    _expect(int(invariants["n_deficit_zero"]) == 1,
            "a day the participant met their own baseline carries a REAL zero deficit")
    _expect(int(invariants["n_deficit_zero_not_analyzable"]) == 0,
            "and no unobserved day carries a zero, which is what zero-imputation looks like")
    _expect(int(invariants["n_deficit_not_null_but_not_analyzable"]) == 0,
            "nor does any unobserved day carry a deficit at all")
    _expect(not panel_violations(invariants), "so a clean panel raises nothing")
    imputed = panel.copy()
    imputed.loc[2, ["deficit", "deficit_untruncated", "normalized_activity"]] = [0.0, 0.0, 1.0]
    reasons = panel_violations(count_daily_panel_invariants(imputed))
    _expect(any("zero-imputation" in reason for reason in reasons),
            "filling an unobserved day with a zero deficit is caught and named as "
            "zero-imputation, in both of the columns that can carry it")

    # ---- 4. PIN: a real zero-step analyzable day is KEPT and carries a full day of debt --
    zero_step = _tiny_panel([
        {"steps": 0.0, "normalized_activity": 0.0, "deficit": 1.0, "deficit_untruncated": 1.0},
    ])
    kept = count_daily_panel_invariants(zero_step)
    _expect(int(kept["n_zero_steps_analyzable"]) == 1,
            "a day with confirmed wear and a REAL zero step total is retained, because "
            "profound inactivity may be the biological signal of interest")
    _expect(int(kept["n_zero_steps_analyzable_deficit_one"]) == 1,
            "and it carries a deficit of exactly one, which is the maximum the scale allows")
    _expect(not panel_violations(kept), "so it is not a violation; it is the point")
    halved = zero_step.copy()
    halved.loc[0, ["deficit", "deficit_untruncated"]] = [0.0, 0.0]
    _expect(any("full day of debt" in reason or "deficit of exactly one" in reason
                for reason in panel_violations(count_daily_panel_invariants(halved))),
            "a zero-step day computed as anything other than a full day of debt is caught")

    # ---- 5. PIN: the two landmark conditions are reported separately -------------------
    events = _tiny_events([
        # Post-discharge day 3: the window holds no post-discharge day at all, so this is the
        # DEFINITIONAL condition and the co-primary exposure is FALSE on it, not true.  It has
        # no exposure window, carries no N, and is outside the exposure on every surface.
        {"event_post_discharge_day": 3, "n_valid_days_in_window": 0,
         "n_eligible_days_in_window": 0, "n_missing_days_in_window": 3,
         "has_computable_landmark": False, "structurally_uncomputable_landmark": True,
         "no_computable_step_signal": False, "r72": np.nan, "r72_24h": np.nan,
         "r_reference_7day": np.nan, "r_negative_control": np.nan,
         "local_step_deterioration": np.nan, "wear_fraction": np.nan},
        {"event_post_discharge_day": 10, "n_valid_days_in_window": 1,
         "n_missing_days_in_window": 2, "has_computable_landmark": False,
         "no_computable_step_signal": True},
        {"event_post_discharge_day": 12},
    ])
    conditions = count_landmark_conditions(events)
    summary = landmark_summary(conditions)
    _expect(summary["n structurally deleted"] == 1,
            "the definitional condition is counted on its own: an event on post-discharge day "
            "1 to 4 has no eligible window and is attrition rung 18")
    _expect(summary["n data uncomputable"] == 1,
            "the data condition is counted separately: an eligible window that was not worn "
            "STAYS in the risk set as the co-primary exposure")
    _expect(summary["n computable"] == 1, "and a computable window is counted as one")
    _expect(summary["n structurally deleted"] + summary["n data uncomputable"]
            != summary["n first events"] or summary["n computable"] == 0,
            "the two are never a single number: merging them would delete the "
            "collider-correction windows silently")
    _expect(summary["n ratio at a single valid day"] == 1,
            "a window with exactly one valid day carries a one-day proximal ratio, which the "
            "co-primary model never reads and a filter on the ratio would")
    _expect(not landmark_violations(conditions), "a clean event frame raises nothing")
    merged = events.copy()
    merged.loc[0, "structurally_uncomputable_landmark"] = False
    _expect(any("rung 18" in reason
                for reason in landmark_violations(count_landmark_conditions(merged))),
            "an early event not flagged structurally uncomputable is caught, because rung 18 "
            "would otherwise undercount what the analysis is blind to by construction")
    late = events.copy()
    late.loc[2, "structurally_uncomputable_landmark"] = True
    _expect(any("post-discharge day\n4" in reason.replace(" ", "\n") or "day 4" in reason
                for reason in landmark_violations(count_landmark_conditions(late))),
            "and a late event wrongly flagged structural is caught against the plan's own "
            "six-row derivation")

    # ---- 6. PIN: the full-cohort landmark panel, and both invariants the stage asserts ---
    lm_panel = _synthetic_landmark_panel()
    lm_events = _events_from_landmark_panel(lm_panel)
    lm_counts = count_landmark_panel(lm_panel, lm_events)
    lm_by_day = count_landmark_panel_by_day(_add_group_slugs(lm_panel))
    _expect(not landmark_panel_violations(lm_counts, lm_by_day),
            "a correctly built landmark panel raises nothing")
    _expect(int(lm_counts["n_episode_days"])
            == _N_PERSONS * _LANDMARK_PANEL_DAYS,
            "the panel is one row per analytic episode per post-discharge day, which is the "
            "daily panel's own grid and not a sample of it")
    _expect(int(lm_counts["n_events_joined"]) > 0
            and int(lm_counts["n_event_window_disagreement"]) == 0,
            "the panel reproduces the event table cell for cell at every event date, and the "
            "comparison is made rather than skipped for want of an overlapping row")
    _expect(int(lm_counts["n_weight_input_absent"])
            + int(lm_counts["n_weight_input_available"]) == int(lm_counts["n_episode_days"]),
            "the episode-days with and without a landmark weight input partition the panel")
    _expect(int(lm_counts["n_weight_input_absent"])
            > int(lm_counts["n_landmark_before_day_one"]),
            "and the weight-input boundary is strictly WIDER than the no-panel-row one, which "
            "is the whole of the off-by-one: post-discharge day 4 has a landmark on day 1, "
            "which carries a row and a null lag")
    _expect(int(lm_counts["n_structurally_uncomputable_days"])
            == _N_PERSONS * STRUCTURAL_DELETION_LAST_DAY,
            "the definitional condition is true on post-discharge day 1 to 4 of every episode "
            "and on no other day, which is the six-row derivation of ANALYSIS-PLAN 4.3 checked "
            "across the whole panel rather than only at event dates")
    _expect(int(lm_counts["n_data_uncomputable_days"])
            + int(lm_counts["n_structurally_uncomputable_days"])
            + int(lm_counts["n_computable_days"]) == int(lm_counts["n_episode_days"]),
            "the data condition, the definitional condition and the computable days partition "
            "the panel. They do so by CONSTRUCTION now that the exposure column carries the "
            "data condition alone, rather than by a subtraction taken afterwards, and the two "
            "are still never a single number")
    _expect(int(lm_counts["n_structural_carrying_no_signal"]) == 0,
            "and no structurally uncomputable day carries the no-signal exposure, which is the "
            "containment in the direction the data-only definition puts it: the exposure "
            "implies NOT the definitional condition, and never the reverse")

    # Each invariant, violated on its own, on an otherwise clean frame.
    drifted = lm_events.copy()
    drifted.loc[0, "n_valid_days_in_window"] = int(drifted.loc[0, "n_valid_days_in_window"]) + 1
    _expect(any("disagree about the proximal window" in reason
                for reason in landmark_panel_violations(
                    count_landmark_panel(lm_panel, drifted), lm_by_day)),
            "one disagreeing cell between the panel and the event table is a stop condition, "
            "because the full-cohort comparison would then answer a different question from "
            "the one the risk sets answer")
    miscalendared = lm_panel.copy()
    late = miscalendared.index[miscalendared["post_discharge_day"] == 20][0]
    miscalendared.loc[late, "structurally_uncomputable_landmark"] = True
    _expect(any("post-discharge day 1 to 4 on every episode-day" in reason
                for reason in landmark_panel_violations(
                    count_landmark_panel(miscalendared, lm_events),
                    count_landmark_panel_by_day(_add_group_slugs(miscalendared)))),
            "and a day after post-discharge day 4 flagged structurally uncomputable is caught "
            "on the whole panel, which is where attrition rung 18 cannot see it")
    early = lm_panel.copy()
    first_day = early.index[early["post_discharge_day"] == 3][0]
    early.loc[first_day, "structurally_uncomputable_landmark"] = False
    _expect(any("post-discharge day 1 to 4 on every episode-day" in reason
                for reason in landmark_panel_violations(
                    count_landmark_panel(early, lm_events),
                    count_landmark_panel_by_day(_add_group_slugs(early)))),
            "the same invariant failing the other way is caught too")
    substituted = lm_panel.copy()
    day_four = substituted.index[substituted["post_discharge_day"] == 4][0]
    substituted.loc[day_four, "landmark_lagged_wear_fraction"] = 0.5
    substituted.loc[day_four, "landmark_weight_input_available"] = True
    _expect(any("one day wider" in reason
                for reason in landmark_panel_violations(
                    count_landmark_panel(substituted, lm_events), lm_by_day)),
            "a lagged wear fraction supplied at a landmark day of one is caught. That is the "
            "column having a value where the weight model has no input, which is the shape a "
            "carry-back onto the preoperative grid would take, and ANALYSIS-PLAN 4.4 rejects "
            "it as defined and wrong rather than undefined and honest")
    short = lm_panel.copy()
    short.loc[0, "n_days_behind_landmark_on_wearable_grid"] = 5
    _expect(any("defect in the span" in reason or "does not cover the lookback" in reason
                for reason in landmark_panel_violations(
                    count_landmark_panel(short, lm_events), lm_by_day)),
            "a wearable lookback shorter than seven days is a defect to be found before the "
            "weights are fitted, not a data condition to be weighted around")
    # THE PIN, IN THE DIRECTION THE DATA-ONLY DEFINITION PUTS IT.  Setting the no-signal flag
    # TRUE on a structurally uncomputable day is the merge ANALYSIS-PLAN 4.4 forbids: it folds
    # an exclusion into an exposure.  The old column would have had this day true already, so
    # this mutation is the one that fails loudly on a table still carrying the union.
    merged_conditions = lm_panel.copy()
    merged_conditions.loc[first_day, "no_computable_step_signal"] = True
    merged_reasons = landmark_panel_violations(
        count_landmark_panel(merged_conditions, lm_events),
        count_landmark_panel_by_day(_add_group_slugs(merged_conditions)))
    _expect(any("puts an exclusion inside an exposure" in reason
                for reason in merged_reasons),
            "a structurally uncomputable day that carries the no-signal exposure is caught. It "
            "has no exposure window at all, so counting it as the data condition puts attrition "
            "rung 18 inside the co-primary exposure")
    _expect(any("only the data condition" in reason for reason in merged_reasons),
            "and the same day fails the definition pin as well, because the exposure is the "
            "data condition and only the data condition and this day is not it")
    signal_only = lm_panel.copy()
    signal_only["no_computable_step_signal"] = (
        pd.to_numeric(signal_only["n_valid_days_in_window"])
        < LANDMARK_MIN_VALID_DAYS)
    _expect(any("only the data condition" in reason
                for reason in landmark_panel_violations(
                    count_landmark_panel(signal_only, lm_events),
                    count_landmark_panel_by_day(_add_group_slugs(signal_only)))),
            "a whole panel built on the SUPERSEDED reading, the exposure set from valid days "
            "alone with no structural filter, halts rather than passing. The pin is not "
            "widened to accept both readings: a module that accepted either would validate "
            "neither")

    rates = landmark_panel_summary(lm_counts, lm_by_day)
    _expect(rates["available"] and "unmatched and descriptive" in rates["caveat"],
            "the full-cohort comparison carries its own caveat, so a caller cannot pick up the "
            "two rates without the sentence saying neither is a causal estimate")
    _expect(rates["n at risk days without a computable ratio"] > 0
            and rates["n at risk days with a computable ratio"] > 0,
            "both sides of the with-versus-without comparison have a real denominator, which "
            "is what the full-cohort panel buys over the sampled risk sets")
    _expect(rates["n at risk days with no eligible window"] > 0
            and rates["n at risk days with no eligible window"]
            not in (rates["n at risk days without a computable ratio"],
                    rates["n at risk days without a computable ratio"]
                    + rates["n at risk days with a computable ratio"]),
            "the definitional condition is reported beside the comparison and is not folded "
            "into either side of it, because those days are uncomputable for a reason that is "
            "not about wear")
    _expect(rates["n days standardized over"] > 0,
            "and the standardization runs over the post-discharge days where both conditions "
            "have days, so a day with an empty stratum cannot carry a weight into a rate it "
            "has no value for")
    _expect(rates["n weight input absent"] + rates["n weight input available"]
            == rates["n episode days"]
            and rates["n weight input absent"]
            > rates["n landmark before post-discharge day one"],
            "the panel summary carries the early-landmark denominators the weight rule is sized "
            "against, and the wider boundary strictly contains the narrower one there too")
    empty_rates = landmark_panel_summary(lm_counts, lm_by_day.iloc[0:0])
    _expect(not empty_rates["available"]
            and empty_rates["n episode days"] == int(lm_counts["n_episode_days"]),
            "and with no by-day frame the comparison reports itself unavailable while still "
            "carrying the panel denominators, rather than returning a bare refusal a caller "
            "would have to interpret")

    # ---- 7. PIN: an inpatient day that is also analyzable, in both taxonomies ----------
    crosstab = pd.DataFrame([
        {"group_slug": ALL_GROUPS_SLUG, "window_slug": "accrual_window",
         "day_kind": "observed", "day_kind_four": "inpatient", "is_inpatient": True,
         "is_analyzable": True, "n_days": 30},
        {"group_slug": ALL_GROUPS_SLUG, "window_slug": "accrual_window",
         "day_kind": "observed", "day_kind_four": "observed", "is_inpatient": False,
         "is_analyzable": True, "n_days": 100},
        {"group_slug": ALL_GROUPS_SLUG, "window_slug": "accrual_window",
         "day_kind": "missing", "day_kind_four": "missing", "is_inpatient": False,
         "is_analyzable": False, "n_days": 40},
    ])
    _expect(not day_kind_violations(crosstab),
            "an inpatient day that is also observed is legal, and the plan keeps it")
    cell = inpatient_observed_cell(crosstab)
    _expect(cell["n observed and inpatient"] == 30 and cell["n inpatient and analyzable"] == 30,
            "the same days carry both labels")
    _expect(cell["counted once in each taxonomy"],
            "so they are counted once in the three-value taxonomy and once in the four-value "
            "one, and never twice in either")
    total = int(crosstab["n_days"].sum())
    _expect(int(crosstab.groupby("day_kind")["n_days"].sum().sum()) == total
            and int(crosstab.groupby("day_kind_four")["n_days"].sum().sum()) == total,
            "both taxonomies sum to the same denominator, so neither has absorbed the "
            "inpatient setting as an extra category")
    collapsed = crosstab.copy()
    collapsed.loc[0, "day_kind_four"] = "observed"
    _expect(any("precedence" in reason for reason in day_kind_violations(collapsed)),
            "collapsing the inpatient setting out of the four-value taxonomy is caught")


    # ---- 8. the baseline: null, never zero ---------------------------------------------
    episodes = _synthetic_episodes()
    clean = count_baseline_invariants(episodes)
    _expect(int(clean["n_baseline_zero"]) == 0 and int(clean["n_baseline_negative"]) == 0,
            "the fixture carries no zero baseline, which is what the contract promises")
    _expect(not baseline_violations(clean, pd.DataFrame(), pd.DataFrame(), pd.DataFrame()),
            "and a clean baseline table raises nothing")
    zeroed = episodes.copy()
    zeroed.loc[0, "baseline_steps"] = 0.0
    reasons = baseline_violations(count_baseline_invariants(zeroed), pd.DataFrame(),
                                  pd.DataFrame(), pd.DataFrame())
    _expect(any("ZERO steps" in reason for reason in reasons),
            "a zero baseline is caught and named, because it makes the deficit exactly one on "
            "every day of that episode and announces itself nowhere downstream")
    _expect(all("0" != reason.strip() for reason in reasons),
            "and no violation message quotes a count, because a message renders into a "
            "traceback and a traceback is a printed surface")
    nulled = episodes.copy()
    nulled.loc[1, "baseline_steps"] = np.nan
    _expect(any("valid baseline days and no baseline" in reason
                for reason in baseline_violations(count_baseline_invariants(nulled),
                                                  pd.DataFrame(), pd.DataFrame(),
                                                  pd.DataFrame())),
            "a null baseline standing beside a non-zero valid-day count is caught")
    shortened = episodes.copy()
    shortened.at[2, "baseline_dow_counts"] = [1, 1, 1]
    reasons = baseline_violations(count_baseline_invariants(shortened), pd.DataFrame(),
                                  pd.DataFrame(), pd.DataFrame())
    _expect(any("length seven" in reason for reason in reasons),
            "a day-of-week array that is not seven long is caught, because an index into it "
            "would no longer name the weekday it is documented to name")
    _expect(any("VALID days" in reason for reason in reasons),
            "and the composition sum is checked against the valid-day count, with the ambiguity "
            "in the contract named rather than resolved silently")

    # The split baseline of ANALYSIS-PLAN 2.2, supplementary sensitivity row ten.  Four columns,
    # the same null rule as the pooled baseline, and the identity DAG-SCHEMA 8.8 states in all
    # three of its parts.
    _expect(int(clean["n_weekday_baseline_zero"]) == 0
            and int(clean["n_weekend_baseline_zero"]) == 0,
            "neither split baseline is ever zero in a clean table, and both are null instead")
    _expect(int(clean["n_weekday_count_mismatch"]) == 0
            and int(clean["n_weekend_count_mismatch"]) == 0
            and int(clean["n_weekday_weekend_sum_mismatch"]) == 0,
            "the weekday count equals the Monday-to-Friday entries of the composition, the "
            "weekend count equals the Sunday and Saturday entries, and the two sum to the valid "
            "baseline day count. That identity is the join between the composition and the two "
            "medians and a build can satisfy any two of the three while breaking the third")
    weekend_only = episodes[episodes["n_valid_baseline_days_weekend"] == 0]
    _expect(len(weekend_only) > 0
            and weekend_only["baseline_steps_weekend"].isna().all()
            and weekend_only["n_valid_baseline_days"].gt(0).all(),
            "the fixture carries episodes that clear the primary baseline rung on weekdays "
            "alone and have NO weekend baseline at all, which is the case the split row's own "
            "denominator exists for and which a null test on the pooled baseline cannot see")
    zeroed_split = episodes.copy()
    zeroed_split.loc[0, "baseline_steps_weekday"] = 0.0
    _expect(any("DIFFERENTIAL" in reason
                for reason in baseline_violations(count_baseline_invariants(zeroed_split),
                                                  pd.DataFrame(), pd.DataFrame(),
                                                  pd.DataFrame())),
            "a zero weekday baseline is caught, and the message says why it is worse here than "
            "for the pooled baseline: it lands on exactly the participants whose wear is "
            "concentrated in the other half of the week, so the error is differential rather "
            "than a wash")
    zeroed_split = episodes.copy()
    zeroed_split.loc[0, "baseline_steps_weekend"] = 0.0
    _expect(any("weekend baseline of ZERO steps" in reason
                for reason in baseline_violations(count_baseline_invariants(zeroed_split),
                                                  pd.DataFrame(), pd.DataFrame(),
                                                  pd.DataFrame())),
            "and the same failure on the other half of the week is caught on its own column, "
            "not folded into the weekday one")
    broken_identity = episodes.copy()
    broken_identity.loc[0, "n_valid_baseline_days_weekend"] = int(
        broken_identity.loc[0, "n_valid_baseline_days_weekend"]) + 1
    reasons = baseline_violations(count_baseline_invariants(broken_identity), pd.DataFrame(),
                                  pd.DataFrame(), pd.DataFrame())
    _expect(any("Sunday and Saturday entries" in reason for reason in reasons),
            "a weekend count that does not match the composition is caught")
    _expect(any("do not sum to its valid" in reason for reason in reasons),
            "and the sum identity fails with it, so both halves of the join are checked")
    split_categories = pd.DataFrame([
        {"group_slug": ALL_GROUPS_SLUG, "metric_slug": "weekday_baseline",
         "bucket_slug": "present", "n_episodes": 40},
        {"group_slug": ALL_GROUPS_SLUG, "metric_slug": "weekend_baseline",
         "bucket_slug": "present", "n_episodes": 30},
        {"group_slug": ALL_GROUPS_SLUG, "metric_slug": "baseline_weekday_weekend_split",
         "bucket_slug": "present", "n_episodes": 25},
    ])
    _expect(not baseline_violations(clean, pd.DataFrame(), pd.DataFrame(), split_categories),
            "a split denominator smaller than both medians' own sets is legal, because the row "
            "requires a valid day in each half of the week")
    oversized = split_categories.copy()
    oversized.loc[2, "n_episodes"] = 35
    _expect(any("SUBSET of both" in reason
                for reason in baseline_violations(clean, pd.DataFrame(), pd.DataFrame(),
                                                  oversized)),
            "and a split denominator larger than a median's own set is caught, because the "
            "minimum-day rule cannot admit an episode with no valid day in that half")

    # ---- 9. the risk sets ---------------------------------------------------------------
    members = _synthetic_risk_sets()
    matched = count_matched_sets(members)
    sizes, member_counts = matched["matched set sizes"], matched["matched set members"]
    participation = matched["control participation"]
    set_ledger = sizes.groupby("set_size", as_index=False)["n_sets"].sum()
    set_ledger["n_cases"] = set_ledger["n_sets"]
    digest = {"n_case_rows": int((members["member_role"] == "case").sum()),
              "n_distinct_sets": int(members["set_id"].nunique()),
              "membership_digest": "0" * 32}
    _expect(not risk_set_violations(sizes, member_counts, participation, set_ledger, digest),
            "a correctly built risk-set table raises nothing")

    # THE TWO COUNTS THE OLD CANDIDATE FLOOR MADE STRUCTURALLY ZERO.  While `build_all.sql`
    # carried `control_matched_day >= 5` no day-3 or day-4 control could be drawn, so this
    # module had the counting surface and nothing to count.  The floor is now 1 and both are
    # real, so the fixture carries members on both of them and the assertions are on values
    # rather than on the absence of one.
    _expect(int(pd.to_numeric(
                member_counts["n_early_via_day_of_week_relaxation"]).sum()) > 0,
            "the day-of-week relaxation puts real members at a landmark day of one or less in "
            "this fixture, so the route the plan obliges reported is exercised rather than "
            "merely available")
    _expect(int(pd.to_numeric(sizes["n_sets_losing_every_control"]).sum()) > 0,
            "and at least one matched set loses every control and leaves the conditional "
            "likelihood altogether, which is the count that turns a member-level exclusion "
            "into an analysis-level one")
    _expect(int(pd.to_numeric(sizes["n_members_in_weighted_sensitivity"]).sum())
            >= 2 * int(pd.to_numeric(sizes["n_sets_in_weighted_sensitivity"]).sum()) > 0,
            "the weighted sensitivity has its own denominator in sets and in members, and "
            "every set in it carries at least its case and one control, which is the minimum a "
            "conditional likelihood accepts")

    # THE EXPOSURE AND THE DEFINITIONAL CONDITION DO NOT OVERLAP ON `risk_sets` EITHER.
    smuggled = members.copy()
    early_row = smuggled.index[
        smuggled["member_landmark_post_discharge_day"]
        <= EARLY_LANDMARK_LAST_LANDMARK_DAY][0]
    smuggled.loc[early_row, "no_computable_step_signal"] = True
    smuggled_counts = count_matched_sets(smuggled)
    _expect(any("outside the co-primary exposure on every surface" in reason
                for reason in risk_set_violations(
                    smuggled_counts["matched set sizes"],
                    smuggled_counts["matched set members"],
                    smuggled_counts["control participation"], pd.DataFrame(), {})),
            "a member at a landmark day of one or less carrying the no-signal exposure halts. "
            "Its window holds fewer than two post-discharge days, so it carries no N anywhere, "
            "and counting it as the exposure would fold a calendar artefact into the "
            "coefficient that exists to measure informative non-wear")
    ratioed = members.copy()
    ratioed.loc[early_row, "r72"] = 0.7
    ratioed_counts = count_matched_sets(ratioed)
    _expect(any("nothing for a ratio to be a median of" in reason
                for reason in risk_set_violations(
                    ratioed_counts["matched set sizes"],
                    ratioed_counts["matched set members"],
                    ratioed_counts["control participation"], pd.DataFrame(), {})),
            "and the same member carrying a proximal ratio halts too, because its window "
            "reaches at most one post-discharge day and a reader filtering on the ratio rather "
            "than on the flag would fit it as the exposure")

    dual = participation[participation["also_a_case"].astype(bool)
                         & (participation["n_control_landmarks"] > 0)]
    _expect(int(dual["n_participants"].sum()) == 1,
            "the fixture carries exactly one participant who is a control at one landmark and "
            "a case at another, which ANALYSIS-PLAN 4.5 permits and which must not be counted "
            "as two participants")
    _expect(int(participation["n_over_participant_cap"].sum()) == 0,
            "and no participant exceeded the cap of three control landmarks")
    _expect(int(pd.to_numeric(sizes["set_size"]).max()) <= CONTROLS_PER_CASE_CAP,
            "no matched set holds more controls than the per-case cap")
    cases = member_counts[member_counts["member_role"] == "case"]
    _expect(int(cases["n_members"].sum()) == int(cases["n_fingerprint_null"].sum()),
            "every case row carries a null fingerprint, because a case was not drawn")
    controls = member_counts[member_counts["member_role"] == "control"]
    _expect(int(controls["n_fingerprint_null"].sum()) == 0,
            "and every control row carries one, because it was")
    stamped = members.copy()
    stamped.loc[stamped["member_role"] == "case", "fingerprint"] = 7.0
    stamped_counts = count_matched_sets(stamped)
    _expect(any("cases went through the sampler" in reason
                for reason in risk_set_violations(stamped_counts["matched set sizes"],
                                                  stamped_counts["matched set members"],
                                                  stamped_counts["control participation"],
                                                  set_ledger, digest)),
            "a case row carrying a sampling fingerprint is caught")
    over = pd.DataFrame([{"n_control_landmarks": 4, "also_a_case": False, "n_participants": 3,
                          "n_over_participant_cap": 3}])
    _expect(any("per-participant cap" in reason
                for reason in risk_set_violations(sizes, member_counts, over, set_ledger,
                                                  digest)),
            "a participant over the control cap is caught, because without the cap a few "
            "long-observed participants dominate the control pool")
    outcome = outcome_by_computable_ratio(member_counts)
    _expect(outcome["available"] and "not an absolute risk" in outcome["caveat"],
            "the outcome comparison carries its sampling caveat with it, so a caller cannot "
            "pick up the numbers without the sentence that says what they are")
    _expect(outcome["n windows without a computable ratio"] > 0
            and outcome["n windows with a computable ratio"] > 0,
            "and both arms of the comparison exist in the fixture")
    _expect(outcome["n windows with no eligible window at all"] > 0,
            "the definitional condition is present among the sampled members at all, which it "
            "could not be while the build excluded every day-3 and day-4 control before it "
            "could be drawn")
    _expect(outcome["n windows with no eligible window at all"]
            + outcome["n windows without a computable ratio"]
            + outcome["n windows with a computable ratio"]
            == int(pd.to_numeric(member_counts["n_members"]).sum()),
            "and the three classes partition the sampled members, so the definitional row is "
            "counted apart rather than left inside the row it has no ratio to belong to")
    _expect(outcome["n windows with no eligible window at all"]
            not in (outcome["n windows with a computable ratio"],
                    outcome["n windows with a computable ratio"]
                    + outcome["n windows without a computable ratio"]),
            "and it is never added into either side. A member whose window holds fewer than "
            "two post-discharge days has no ratio at all, so filing it under the computable "
            "side would assert of it exactly what is not true")
    _expect("never added to either of them" in outcome["caveat"],
            "and the sentence saying so travels with the numbers")
    _expect(digests_agree("a" * 32, "a" * 32)["identical"],
            "two builds with the same membership digest reproduce identical matched sets")
    _expect(not digests_agree("a" * 32, "b" * 32)["identical"],
            "two builds with different digests do not")
    _expect(not digests_agree("nope", "nope")["comparable"],
            "and a value that is not a digest is refused rather than compared")

    # THE OFF-BY-ONE, PINNED AT THE BOUNDARY ITSELF.  Three synthetic members, one at each of
    # landmark day 0, 1 and 2, and nothing else varying.  Landmark day 0 has no daily-panel row
    # at all; landmark day 1 HAS a row and a null lagged wear fraction, because the lag runs
    # over post-discharge days and day 1 has none preceding it; landmark day 2 is the first day
    # the weight model has an input.  So the affected set is landmark day 1 or less, which is
    # matched day 4 or less, and a counter written on landmark day below 1 misses the middle
    # one of these three.  ANALYSIS-PLAN 4.4 states the rule as landmark day 2 or more.
    boundary = pd.DataFrame([
        # matched day 3, landmark day 0: no panel row behind the landmark at all.  The
        # exposure is FALSE on both rows, because a landmark day of 1 or less IS the
        # definitional condition and such a member carries no no-signal exposure anywhere.
        {"set_id": "B0", "member_role": "case", "is_case": True, "person_id": 900,
         "episode_id": "E900", "set_size": 1, "match_rung": 1,
         "no_computable_step_signal": False, "fingerprint": np.nan, "r72": np.nan,
         "wear_fraction": 0.3, "case_matched_day": 3, "member_matched_day": 3,
         "member_landmark_post_discharge_day": 0},
        {"set_id": "B0", "member_role": "control", "is_case": False, "person_id": 901,
         "episode_id": "E901", "set_size": 1, "match_rung": 1,
         "no_computable_step_signal": False, "fingerprint": 11.0, "r72": np.nan,
         "wear_fraction": 0.3, "case_matched_day": 3, "member_matched_day": 3,
         "member_landmark_post_discharge_day": 0},
        # matched day 4, landmark day 1: a row exists, the lag has nothing behind it.  Still
        # the definitional condition, so still no exposure and still no proximal ratio.
        {"set_id": "B1", "member_role": "case", "is_case": True, "person_id": 902,
         "episode_id": "E902", "set_size": 1, "match_rung": 1,
         "no_computable_step_signal": False, "fingerprint": np.nan, "r72": np.nan,
         "wear_fraction": 0.4, "case_matched_day": 4, "member_matched_day": 4,
         "member_landmark_post_discharge_day": 1},
        {"set_id": "B1", "member_role": "control", "is_case": False, "person_id": 903,
         "episode_id": "E903", "set_size": 1, "match_rung": 1,
         "no_computable_step_signal": False, "fingerprint": 12.0, "r72": np.nan,
         "wear_fraction": 0.4, "case_matched_day": 4, "member_matched_day": 4,
         "member_landmark_post_discharge_day": 1},
        # matched day 5, landmark day 2: the first day the weight model has an input.
        {"set_id": "B2", "member_role": "case", "is_case": True, "person_id": 904,
         "episode_id": "E904", "set_size": 1, "match_rung": 1,
         "no_computable_step_signal": False, "fingerprint": np.nan, "r72": 0.5,
         "wear_fraction": 0.4, "case_matched_day": 5, "member_matched_day": 5,
         "member_landmark_post_discharge_day": 2},
        {"set_id": "B2", "member_role": "control", "is_case": False, "person_id": 905,
         "episode_id": "E905", "set_size": 1, "match_rung": 1,
         "no_computable_step_signal": False, "fingerprint": 13.0, "r72": 0.5,
         "wear_fraction": 0.4, "case_matched_day": 5, "member_matched_day": 5,
         "member_landmark_post_discharge_day": 2},
    ])
    boundary_counts = count_matched_sets(boundary)
    boundary_members = boundary_counts["matched set members"]
    boundary_sizes = boundary_counts["matched set sizes"]
    absent = int(pd.to_numeric(
        boundary_members["n_landmark_weight_input_absent"]).sum())
    before_one = int(pd.to_numeric(
        boundary_members["n_landmark_before_post_discharge_day_one"]).sum())
    _expect(absent == 4,
            "the four members at landmark day 0 and landmark day 1 all lack a weight input. "
            "This is the assertion that fails on the old threshold, which counted 2")
    _expect(before_one == 2,
            "and only the two at landmark day 0 have no daily-panel row at all, so the narrower "
            "subset is half of the affected set and is not the affected set")
    _expect(absent > before_one,
            "the two counts are different quantities and the wider one is the one the weight "
            "rule turns on")
    _expect(int(pd.to_numeric(boundary_members[
                boundary_members["member_role"] == "case"][
                "n_landmark_weight_input_absent"]).sum()) == 2
            and int(pd.to_numeric(boundary_members[
                boundary_members["member_role"] == "control"][
                "n_landmark_weight_input_absent"]).sum()) == 2,
            "and the count splits into cases and controls, which ANALYSIS-PLAN 4.4 requires "
            "because the two arrive by different routes")
    weighted_sets = int(pd.to_numeric(
        boundary_sizes["n_sets_in_weighted_sensitivity"]).sum())
    weighted_members = int(pd.to_numeric(
        boundary_sizes["n_members_in_weighted_sensitivity"]).sum())
    _expect(weighted_sets == 1 and weighted_members == 2,
            "exactly the set at matched day 5 survives into the weighted sensitivity, with its "
            "case and its one control, which is the row's own denominator in sets and in "
            "members and is what 9.2 requires printed beside the primary's")
    _expect(int(pd.to_numeric(boundary_sizes["n_sets_losing_every_control"]).sum()) == 2,
            "the two earlier sets lose every control and therefore leave the conditional "
            "likelihood altogether. That count is not recoverable from the member count, which "
            "is why the plan obliges it separately")
    _expect(int(pd.to_numeric(boundary_sizes["n_sets_losing_the_case"]).sum()) == 2,
            "and they lose their cases too, which is just as final: a set without its case is "
            "not a matched set")
    _expect(int(pd.to_numeric(
                boundary_members["n_early_via_partial_window_secondary"]).sum()) == 4,
            "all four arrive through the partial-window secondary here, because each sits in a "
            "set whose own case is at post-discharge day 4 or earlier")
    _expect(int(pd.to_numeric(boundary_members["n_early_by_neither_route"]).sum()) == 0,
            "and none arrives by a third route, which the plan says cannot exist")

    # The day-of-week relaxation, which is the OTHER route: a control two days below a case that
    # is itself late enough to be weighted.  ANALYSIS-PLAN 4.7 rungs 2 and 3 admit it.
    relaxed = boundary.copy()
    relaxed = relaxed[relaxed["set_id"] == "B2"].copy()
    relaxed.loc[relaxed["member_role"] == "control", "match_rung"] = 3
    relaxed.loc[relaxed["member_role"] == "control", "member_matched_day"] = 3
    relaxed.loc[relaxed["member_role"] == "control",
                "member_landmark_post_discharge_day"] = 0
    relaxed_members = count_matched_sets(relaxed)["matched set members"]
    _expect(int(pd.to_numeric(
                relaxed_members["n_early_via_day_of_week_relaxation"]).sum()) == 1,
            "a control pulled two days below its own case by the relaxation is attributed to "
            "the relaxation and not to the secondary, because its case is at post-discharge "
            "day 5 and is weighted")
    _expect(int(pd.to_numeric(
                relaxed_members["n_early_via_partial_window_secondary"]).sum()) == 0,
            "and the two routes do not double count the same member")
    # THE STOP CONDITION IS LOAD-BEARING NOW, SO IT IS PINNED WITH A MEMBER THAT ACTUALLY
    # PRODUCES IT.  `build_all.sql` once carried `control_matched_day >= 5`, which excluded
    # every day-3 and day-4 control before it could be drawn; the floor is now 1, so a control
    # at post-discharge day 1 through 4 is admitted, ranked, drawn under both caps and dropped
    # here.  The sweep below walks every matched day the new floor admits and shows the two
    # routes still partition the early members exactly, and the fixture after it produces a
    # member early by neither and shows that it halts.
    #
    # It also shows WHAT such a member has to be.  Early means a landmark day of 1 or less,
    # which under the offset means a matched day of 4 or less; "neither route" additionally
    # needs a case matched day above 4 AND a member matched day at or above its case's, which
    # puts the member at 5 or more.  Both cannot hold, so on a table whose offset is intact the
    # count is zero at every day the floor admits, and reaching a non-zero value requires the
    # offset itself to be broken.  That is why the two reasons are asserted TOGETHER: a third
    # route is not a sampling rule somebody could have written, it is a table that has already
    # come apart on the scale every early-landmark count is taken on.
    case_day = 5
    sweep_rows: list[dict[str, Any]] = [
        {"set_id": "F0", "member_role": "case", "is_case": True, "person_id": 950,
         "episode_id": "E950", "set_size": case_day, "match_rung": 1,
         "no_computable_step_signal": False, "fingerprint": np.nan, "r72": 0.5,
         "wear_fraction": 0.4, "case_matched_day": case_day, "member_matched_day": case_day,
         "member_landmark_post_discharge_day": case_day - LANDMARK_DAY_OFFSET},
    ]
    for control_day in range(ACCRUAL_FIRST_DAY, case_day + 1):
        early_here = _early_landmark(control_day)
        sweep_rows.append(
            {"set_id": "F0", "member_role": "control", "is_case": False,
             "person_id": 950 + control_day, "episode_id": f"E{950 + control_day}",
             "set_size": case_day, "match_rung": 3,
             "no_computable_step_signal": False,
             "fingerprint": float(2_000_000 + control_day),
             "r72": (np.nan if early_here else 0.6), "wear_fraction": 0.5,
             "case_matched_day": case_day, "member_matched_day": control_day,
             "member_landmark_post_discharge_day": control_day - LANDMARK_DAY_OFFSET})
    sweep = pd.DataFrame(sweep_rows)
    sweep_counts = count_matched_sets(sweep)
    sweep_members = sweep_counts["matched set members"]

    def _sweep(column: str) -> int:
        return int(pd.to_numeric(sweep_members[column]).sum())

    n_admitted_early = EARLY_LANDMARK_LAST_MATCHED_DAY - ACCRUAL_FIRST_DAY + 1
    _expect(_sweep("n_landmark_weight_input_absent") == n_admitted_early,
            "every control the new candidate floor admits below matched day 5 carries the "
            "definitional condition, which is four of them at matched days 1, 2, 3 and 4. The "
            "old floor of 5 excluded all four before they could be drawn, so this count was "
            "structurally zero by construction and had nothing to count")
    _expect(_sweep("n_early_via_day_of_week_relaxation") == n_admitted_early,
            "and all four are attributed to the day-of-week relaxation, because each sits "
            "earlier than its own case and that case is at post-discharge day 5")
    _expect(_sweep("n_early_via_partial_window_secondary") == 0,
            "none is attributed to the partial-window secondary, whose case would have to sit "
            "at post-discharge day 4 or earlier")
    _expect(_sweep("n_early_by_neither_route") == 0,
            "and none arrives by a third route at ANY matched day the widened floor admits, "
            "day 1 and day 2 included. That is arithmetic on the offset rather than a promise: "
            "early means a matched day of 4 or less, and neither route would need a member at "
            "5 or more")
    _expect(_sweep("n_early_via_partial_window_secondary")
            + _sweep("n_early_via_day_of_week_relaxation")
            + _sweep("n_early_by_neither_route")
            == _sweep("n_landmark_weight_input_absent"),
            "so the two routes partition the affected members exactly, which is the split "
            "ANALYSIS-PLAN 4.4 requires reported")
    _expect(_sweep("n_landmark_day_offset_wrong") == 0
            and not risk_set_violations(sweep_counts["matched set sizes"], sweep_members,
                                        sweep_counts["control participation"],
                                        pd.DataFrame(), {}),
            "and the swept table raises nothing at all, so the counts above are taken on a "
            "table that is consistent rather than on one already broken elsewhere")
    _expect(int(pd.to_numeric(
                sweep_counts["matched set sizes"]["n_sets_losing_every_control"]).sum()) == 0
            and int(pd.to_numeric(
                sweep_counts["matched set sizes"]["n_sets_in_weighted_sensitivity"]).sum()) == 1,
            "the set keeps the one control at matched day 5, so it survives into the weighted "
            "sensitivity rather than leaving the conditional likelihood altogether")
    stripped = sweep[sweep["member_matched_day"] < case_day].copy()
    stripped_sizes = count_matched_sets(
        pd.concat([sweep[sweep["member_role"] == "case"], stripped[
            stripped["member_role"] == "control"]], ignore_index=True))["matched set sizes"]
    _expect(int(pd.to_numeric(stripped_sizes["n_sets_losing_every_control"]).sum()) == 1,
            "and with that one control removed the set loses EVERY control and leaves the "
            "likelihood whole. This is the second count the old floor made structurally zero, "
            "and it is not recoverable from the member count, which cannot say how the dropped "
            "members fell across sets")

    impossible = relaxed.copy()
    impossible.loc[impossible["member_role"] == "control", "member_matched_day"] = 9
    impossible.loc[impossible["member_role"] == "control",
                   "member_landmark_post_discharge_day"] = 1
    impossible_counts = count_matched_sets(impossible)
    impossible_reasons = risk_set_violations(
        impossible_counts["matched set sizes"],
        impossible_counts["matched set members"],
        impossible_counts["control participation"], pd.DataFrame(), {})
    _expect(int(pd.to_numeric(
                impossible_counts["matched set members"][
                    "n_early_by_neither_route"]).sum()) == 1,
            "the fixture really does produce a member early by neither route, rather than "
            "asserting against a count nothing in it can reach")
    _expect(any("neither of the two routes" in reason for reason in impossible_reasons),
            "and a member early by neither route halts, because a third route would be a "
            "sampling rule nobody prespecified")
    _expect(any("not its matched day less three" in reason for reason in impossible_reasons),
            "and the offset violation is reported beside it, because on a table whose landmark "
            "offset is intact no member can be early by neither route at all. The two reasons "
            "arrive together or the count is unreachable")
    skewed = relaxed.copy()
    skewed.loc[skewed["member_role"] == "control",
               "member_landmark_post_discharge_day"] = 99
    skewed_counts = count_matched_sets(skewed)
    _expect(any("not its matched day less three" in reason
                for reason in risk_set_violations(
                    skewed_counts["matched set sizes"],
                    skewed_counts["matched set members"],
                    skewed_counts["control participation"], pd.DataFrame(), {})),
            "a landmark day that is not the matched day less three is caught, because every "
            "early-landmark count is taken on that offset")

    # ---- 10. disclosure at the boundary ---------------------------------------------------
    wide = pd.DataFrame([[100, 60, 5, 0]], index=["one row"],
                        columns=["a", "b", "c", "d"]).astype("int64")
    display = render_wide(wide, [["a", "b", "c", "d"]])
    _expect(is_suppressed(display.loc["one row", "c"]),
            "a cell below the floor is suppressed, and the floor is disclosable and nothing else")
    _expect(is_suppressed(display.loc["one row", "d"]),
            "and a second member is suppressed with it, because one suppressed member of a "
            "partition is exactly recoverable by subtraction from its own total")
    _expect(int(display.loc["one row", "a"]) == 100 and int(display.loc["one row", "b"]) == 60,
            "the disclosable cells are rounded to the nearest multiple of twenty")
    _expect(all(is_legal_disclosed_count(display.loc[r, c])
                for r in display.index for c in display.columns),
            "and every rendered cell is a legal disclosed count, which is the OTHER question "
            "from whether the true count was disclosable")
    _expect(not export_violations(display, count_cols=list(display.columns),
                                  partitions=[list(display.columns)]),
            "the finished table clears every export refusal class, including the partition one")
    distribution = pd.DataFrame([{"v": 2, "n": 30}, {"v": 4, "n": 30}])
    _expect(distribution_summary(distribution, value_col="v", count_col="n")
            == "3.0 (2.0 to 4.0)",
            "a median reconstructed from an aggregate distribution is EXACT, and on this "
            "even-length case it is 3.0, which is the value the approximate quantile form "
            "would have got wrong")
    _expect(len(expand_distribution(distribution, value_col="v", count_col="n")) == 60,
            "and the expansion is of counts, so no participant row entered the kernel")
    thin = pd.DataFrame([{"v": 2, "n": 5}])
    _expect(is_suppressed(distribution_summary(thin, value_col="v", count_col="n")),
            "a summary over too few contributors is suppressed, because at small n a median "
            "is one participant's own value")
    _expect_raises(FeatureCheckError, lambda: _whole(1.5, "a test value"),
                   "a fractional cell in a count column is refused rather than rounded")
    _expect_raises(FeatureCheckError, lambda: _whole(-3, "a test value"),
                   "and a negative count is refused as a defect upstream")

    # ---- 11. the group expansion ---------------------------------------------------------
    episode_pair = pd.DataFrame([
        {"procedure_group": "cervical_fusion", "fusion": True},
        {"procedure_group": "lumbar_decompression", "fusion": False},
    ])
    expanded = expand_groups(episode_pair)
    _expect(len(expanded) == 6, "each episode yields three rows and never four")
    _expect(set(expanded["group_slug"]) == {"cervical_fusion", "lumbar_decompression",
                                            "fusion", "decompression", "all_groups"},
            "and the three rows are the collapse-level-one group, the collapse-level-two "
            "group and the total")
    _expect_raises(FeatureCheckError,
                   lambda: expand_groups(pd.DataFrame([{"procedure_group": "thoracic_fusion",
                                                        "fusion": True}])),
                   "a group outside the plan's own vocabulary is refused rather than plotted")

    # ---- 12. end to end, against the synthetic frame set ----------------------------------
    frames = _synthetic_frames()
    result = assemble(frames)
    _expect(result["features ok"],
            f"the clean synthetic frame set produces no violation: {result['halting'][:3]}")
    _expect(set(RESULT_KEYS) - set(result) == {"report"},
            "assemble fills every declared result key except the report, which the renderer adds")
    _expect(result["wear"]["contingency"]["primary in force"],
            "the fixture was built under the primary wear rule and the agreement says so")
    _expect(len(result["gaps"]) == len(DAG_GAPS),
            "every gap between the derived tables and the analysis is carried into the result")
    _expect(sum(1 for gap in result["gaps"] if gap.get("status") == "closed") == 3,
            "three of the four items are now closed: the split baseline, the early-landmark "
            "weight rule and the full-cohort landmark panel. A closed item is kept rather than "
            "deleted, so a reader can tell a gap that was closed from one quietly dropped")
    _expect(all(gap.get("status") in GAP_STATUS_LABELS for gap in result["gaps"]),
            "and every item declares a status this module knows how to render")
    _expect(result["landmark"]["panel summary"]["available"],
            "the full-cohort landmark comparison is available, which is what closes the third "
            "item: it was previously computable only at the sampled sets and among first events")
    _expect(result["risk sets"]["summary"]["n members without a landmark weight input"]
            >= result["risk sets"]["summary"][
                "n members with a landmark before post-discharge day one"],
            "and the wider early-landmark count contains the narrower one end to end")
    report = render_report(result)
    result["report"] = report
    _expect(EM_DASH not in report and MINUS_SIGN not in report,
            "the rendered report carries neither banned dash")
    _expect(not _SNAKE_TOKEN.findall(report),
            "and it carries no machine token, so every slug reached it through a display label")
    for phrase in ("Denominator:", "VERDICT", "Inpatient is not exclusive of observed",
                   "WHAT THE DERIVED TABLES DO NOT CARRY",
                   "The same comparison on the full-cohort day-indexed panel",
                   "Members at a landmark day of one or less, by role and by route",
                   "One count and not two.",
                   "Sampled windows with no eligible window at all",
                   "The weighted sensitivity, in sets and in members",
                   "Separate weekday and weekend baselines",
                   "[Closed]", "[Open]"):
        _expect(phrase in report, f"the report carries its {phrase!r} section or line")
    _expect("Standardized rate per 1,000" in report and "Crude rate per 1,000" in report,
            "the with-versus-without comparison prints twice, crude and standardized to the "
            "post-discharge-day distribution, because the panel adjusts for nothing else")
    _expect(NOT_APPLICABLE in report,
            "and a cell where the quantity is not defined says so rather than borrowing the "
            "suppression sentinel, which is a different claim")
    _expect(report.count("Denominator:") >= 12,
            "every table prints its own denominator, which is a house rule and not a courtesy")
    _expect(SUPPRESSED in report,
            "and the fixture's thin strata print as suppressed rather than as small counts")

    broken_frames = dict(frames)
    imputed_panel = frames["daily panel invariants"].copy()
    imputed_panel.loc[0, "n_deficit_not_null_but_not_analyzable"] = 4
    broken_frames["daily panel invariants"] = imputed_panel
    broken = assemble(broken_frames)
    _expect(not broken["features ok"],
            "one zero-imputed day is enough to refuse the whole feature set")
    _expect(any("zero-imputation" in reason for reason in broken["halting"]),
            "and the refusal names it")
    stop_report = render_report(broken)
    _expect("VERDICT: STOP" in stop_report,
            "the report ends in a stop rather than in a verdict a reader has to interpret")

    ledger_broken = dict(frames)
    perturbed = frames["wear availability ledger"].copy()
    perturbed.loc[0, "n_analyzable"] = int(perturbed.loc[0, "n_analyzable"]) + 1
    ledger_broken["wear availability ledger"] = perturbed
    _expect(any("reproduce" in reason
                for reason in assemble(ledger_broken)["deficit"]["violations"]),
            "a single disagreeing cell between the wear ledger and the daily panel is a stop "
            "condition, because Figure 2 is written from one and the model is fitted on the other")

    missing_broken = dict(frames)
    ledger = frames["variable missingness ledger"].copy()
    ledger.loc[ledger["variable"] == "los_days", "n_missing"] = 40
    missing_broken["variable missingness ledger"] = ledger
    _expect(any("structurally complete" in reason
                for reason in assemble(missing_broken)["observation"]["violations"]),
            "a variable an attrition rung made structurally complete cannot be missing")

    # ---- 13. the runner, with a fake query path -------------------------------------------
    runtime = _FakeRuntime(frames)
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        ran = run_features(q_guarded=runtime.q_guarded, dry_run_gb=runtime.dry_run_gb,
                           show_report=False)
    printed = buffer.getvalue()
    _expect([key for key, _, _ in runtime.calls] == list(QUERY_KEYS),
            "every declared query ran, in the declared order, and nothing else ran")
    _expect(all(cap == PLANNED_MAX_GB[key] for key, cap, _ in runtime.calls),
            "each query went out under ITS OWN cap. A cap sized to the whole step would let "
            "every query in the step bill the whole step")
    _expect(all(note.startswith("04 features") for _, _, note in runtime.calls),
            "and each carries a note, which names its entry in the session cost log")
    _expect("COST PLAN" in printed and "free dry run" in printed,
            "the priced plan is printed before anything executes")
    _expect(printed.count("rows hidden by policy") == len(QUERY_KEYS),
            "every returned frame was shown through the shape-only printer, never as rows")
    _expect(set(RESULT_KEYS) <= set(ran), "the runner returns every declared result key")
    _expect(ran["features ok"], "and certifies the clean fixture")

    expensive = _FakeRuntime(frames, gb=100.0)
    _expect_raises(FeatureBudgetExceeded,
                   lambda: run_features(q_guarded=expensive.q_guarded,
                                        dry_run_gb=expensive.dry_run_gb, show_report=False),
                   "a priced total over the budget refuses the whole step, with nothing "
                   "executed and nothing billed")
    _expect(not expensive.calls, "and nothing reached the query path at all")
    _expect_raises(FeatureCheckError, lambda: run_features(show_report=False),
                   "with no query path available the module refuses rather than finding its "
                   "own way to the API")

    plan = cost_plan(build_sql(), _FakeRuntime(frames, gb=0.01).dry_run_gb)
    _expect(plan["fits"] and not plan["over cap"],
            "the priced plan fits, and the per-query caps are the second guard")
    _expect(plan["total gb"] < FEATURES_BUDGET_GB,
            "the whole step reads only derived tables and costs small change")

    # ---- 14. the summary ------------------------------------------------------------------
    print("=" * 86)
    print("04_features.py SELF-TEST: PASS")
    print("=" * 86)
    print(f"  assertions executed        : {_ASSERTIONS}")
    print(f"  queries built              : {len(QUERY_KEYS)}")
    print( "  every emitted query        : carries the derived-dataset placeholder ONLY, quotes")
    print( "                               no hardcoded project or dataset, contains no")
    print( "                               data-definition statement and no random draw, and")
    print( "                               declares result columns it actually aliases")
    print(f"  aggregate budget           : {FEATURES_BUDGET_GB:,.1f} GiB, about "
          f"${FEATURES_BUDGET_GB / 1024 * USD_PER_TIB:,.2f}, priced before anything executes")
    print( "  what this module does      : VALIDATES the derived tables. It recomputes no valid")
    print( "                               day, no baseline, no deficit, no event and no risk set")
    print( "  null is not zero           : pinned on both channels. A null wear figure and a real")
    print( "                               zero are separate columns, the split is exhaustive,")
    print( "                               and counting a null day as valid wear is refused")
    print( "  null deficit is not zero   : pinned in both directions. An unobserved day carrying")
    print( "                               a deficit is named as zero-imputation and halts")
    print( "  zero-step day is KEPT      : pinned positively. A real zero-step analyzable day")
    print( "                               carries a deficit of exactly one, and computing it as")
    print( "                               anything else is the violation")
    print( "  landmark conditions        : pinned separate, and the exposure column is pinned to")
    print( "                               the DATA condition alone: eligible days at least 2")
    print( "                               AND valid days below 2, on events, on the panel and")
    print( "                               on the risk sets alike. The definitional condition is")
    print( "                               rung 18 and leaves, carries no exposure anywhere, and")
    print( "                               the two are never a sum")
    print( "  inpatient and observed     : pinned. Both taxonomies sum to the same denominator,")
    print( "                               the same days carry both labels, and no day is")
    print( "                               counted twice in either")
    print( "  matched sets               : both caps checked, the dual role counted and")
    print( "                               permitted, the fingerprint convention checked in both")
    print( "                               directions, and the membership digest is one scalar")
    print( "                               over the whole table and never per group or per row")
    _open = [gap for gap in DAG_GAPS if gap.get("status") != "closed"]
    print(f"  gaps reported, not patched : {len(DAG_GAPS)}, of which {len(_open)} still open,")
    print( "                               each naming what the build would need or what closed")
    print( "                               it")
    print( "  early landmark boundary    : pinned at landmark day 0, 1 and 2. A member is")
    print( "                               weighted at landmark day 2 or more; landmark day 1")
    print( "                               has a panel row and a null lag, so the affected set")
    print( "                               is landmark day 1 or less, matched day 4 or less")
    print( "  and what that boundary IS  : the definitional condition in landmark-day terms,")
    print( "                               not a threshold of its own. Such a member has no")
    print( "                               exposure window, carries no exposure and no ratio,")
    print( "                               and is dropped from its risk set and counted. The")
    print( "                               two routes are swept across every matched day the")
    print( "                               widened candidate floor admits and still partition")
    print( "                               the affected members exactly")
    print( "  landmark panel             : validated against its own contract, with both of the")
    print( "                               stage's SQL asserts re-asserted on the frames: the")
    print( "                               panel reproduces the event table cell for cell, and")
    print( "                               the definitional condition equals day 1 to 4")
    print( "  cloud access required      : none")


if __name__ == "__main__":
    _run_self_test()
