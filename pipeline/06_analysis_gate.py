#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""06_analysis_gate.py -- Phase 3, Arm A.  The tier-gated early-warning gate analysis.

THIS IS THE ARM THAT MAY NOT RUN AT ALL, AND THAT IS ITS POINT.  The protocol's decision table
(ANALYSIS-PLAN 1.2) binds what may be attempted to a COUNT: at least 100 usable acute-care
events permits a full parsimonious detection model with internal validation; 50 to 99 permits a
step-first model with no broad feature selection and clustered bootstrap validation, labelled
exploratory; 20 to 49 permits event-centered association and visualization only, with no
prediction-tool claim of any kind; fewer than 20 permits no early-warning modeling at all.

THE TIER IS READ FROM THE COUNT AND FROM NOTHING ELSE.  Never from a look at an estimate, never
from a model that has already been fitted, never from a plot.  The module's first job is to
determine the tier; its second is to run only what that tier permits and to REFUSE THE REST BY
NAME, so that a reader can see what was not done rather than having to notice an absence.  The
refusal is a printed ledger with one row per named analysis, and `broad feature selection` sits
in it refused at EVERY tier including the highest, because plan 1.2 forbids it outright.

The two-phase structure is not a convenience.  Phase 1 runs the counting queries and nothing
else.  Phase 2 cannot begin until the count exists and the tier has been decided from it, and
phase 2 submits ONLY the queries the tier permits, so a tier-4 run never prices, never submits
and never bills the model queries at all.  A single-phase module that ran everything and then
decided what to print would have looked at the analysis before deciding whether it was allowed.

THE COINCIDENCE AT THE BOTTOM OF THE TABLE.  The lowest tier's boundary is 20 events.  The All
of Us disclosure floor is also 20, in the exact sense of plan section 8: a count is disclosable
only when it is zero or strictly greater than 20.  The two thresholds are unrelated in origin
and identical in value, so this module carries them as two constants and never aliases one to
the other.  The practical consequence is that THE MODULE MUST BE ABLE TO REPORT A TIER IT
CANNOT PRINT A COUNT FOR: below 20 events the deciding count itself reads "20 or fewer,
suppressed per All of Us dissemination policy", and at exactly 20 events the tier 3 analysis
RUNS while its own denominator stays unprintable.  Both are implemented; neither is an error.

THE FOUR DESIGN PROBLEMS THE PLAN FIXES, IMPLEMENTED HERE RATHER THAN RE-DERIVED:

  1. THE EARLIEST AND MOST SEVERE EVENTS ARE STRUCTURALLY DELETED.  A case needs its exposure
     window entirely on post-discharge days, so an event on post-discharge day 1 TO 4 has no
     computable landmark at all.  That is attrition rung 18, it carries its own ladder row, and
     the timing of the deleted events is reported.  The range is 1 to 4, derived in the plan's
     own six-row table from the two-valid-day rule, and this module asserts it rather than
     transcribing it: any document or comment writing day 1 to 3 is wrong.
  2. REQUIRING WEAR AT THE LANDMARK CONDITIONS ON A COLLIDER.  Wear is plausibly caused both by
     declining activity and by the illness that generates the outcome, so requiring a computable
     ratio deletes preferentially the sickest windows.  The plan promotes "no computable step
     signal" to a CO-PRIMARY EXPOSURE so those windows stay in, adds inverse-probability-of-
     observation weighting as a sensitivity, and reports the outcome rate in windows with versus
     without a computable ratio.  That third comparison runs on the FULL-COHORT DAY-INDEXED
     `landmark_daily` panel, never on the sampled risk sets, because the sampling carries the
     very selection the comparison exists to expose.  It is reported twice, crude and directly
     standardized to post-discharge day, and NEITHER version is labelled causal.
  3. RISK-SET CONTROL SAMPLING.  Controls come from the risk set at the case's post-discharge
     day; a participant may be a control at one landmark and a case later; post-discharge day is
     the single time scale; calendar year is a covariate and not a matching factor; a
     per-participant control cap applies; and INFERENCE IS PERSON-CLUSTERED, because conditional
     logistic regression assumes independent matched sets and a participant appearing in several
     sets breaks that assumption.
  4. DAY-OF-WEEK CONFOUNDING.  A 3-day window covers 3 of 7 weekdays, steps vary by day of week,
     and emergency presentations are not uniform across the week, so landmark day of week is a
     matching factor with a prespecified relaxation order.

THE ONE DISTINCTION THIS MODULE WILL BE BROKEN BY IF IT IS EVER BLURRED.
`has_computable_landmark` is NOT `structurally_uncomputable_landmark`.  The first is a DATA
condition: the window holds at least 2 post-discharge days but fewer than 2 of them were worn.
Those windows STAY in the risk set and are the co-primary exposure.  The second is a
DEFINITIONAL condition: the window holds fewer than 2 post-discharge days at all, which is
exactly an event on post-discharge day 1 to 4.  Those events LEAVE, at rung 18.  THEIR COUNTS
ARE NEVER SUMMED, here or anywhere else.  A single "no computable landmark" number would be the
sum of an exposure and an exclusion, and no reader could take it apart again afterwards.

A SAMPLED CONTROL CAN CARRY THE DEFINITIONAL CONDITION AND CANNOT LEAVE AT RUNG 18, because
rung 18 is an EVENT rung and a sampled control is not an event.  The day-of-week relaxation of
ANALYSIS-PLAN 4.7 admits a control at post-discharge day 3 or 4 under a case at day 5 or 6, and
`risk_sets` draws it, marks it `structurally_uncomputable_landmark`, leaves its
`no_computable_step_signal` FALSE and its `r72` NULL.  `conditional_design` DROPS it before the
fit and returns the count beside the design, the way `discrete_time_design` drops and counts the
structurally uncomputable DAYS of the panel; the matched sets that lose EVERY control that way
are counted separately, because that count turns a member-level exclusion into an
analysis-level one and cannot be recovered from the member count.

WHERE THIS RUNS.  INSIDE THE PERIMETER for the queries, the model fits and the report.  LOCALLY
it still runs, and running it locally is the intended way to check it: `python3
06_analysis_gate.py` executes `_run_self_test()`, which drives every pure function in the module
against synthetic frames, touches no network and writes no file.

IN-PERIMETER USE, in a notebook, after the DAG has been built and validated:

    %run 00_config.ipynb
    %run -i 03_cohort.py                  # builds {DERIVED} and closes the ladder
    %run -i 04_features.py
    FEATURES = run_features()
    %run -i 06_analysis_gate.py
    GATE = run_gate(features_result=FEATURES)

`run_gate` REFUSES to start when `FEATURES["features ok"]` is false.  A feature-validation
failure means a derived table does not hold what its contract promises, and an analysis fitted
on top of that is a number nobody can defend.

DISCLOSURE.  This module is the first in the pipeline that must pull PARTICIPANT-LEVEL rows into
the kernel, because no conditional logistic regression can be fitted on a group-by aggregate.
That is permitted; printing or returning them is not.  Three rules are enforced rather than
promised: the model frames are fitted and then dropped, `run_gate` returns aggregates and
estimate nodes only, and the self-test walks the returned dictionary and fails on any frame
carrying a person identifier, an episode identifier or a date.  Every count reaching a printed
surface has been through `disclosable()` on its TRUE integer value and then `round20()` for
rendering, in that order, because every count in `{DERIVED}` is a true integer and rounding
before the floor test is how a suppressed 21 becomes a printed 20.

WHAT IT WRITES.  Nothing.  `07_export.py` is the only module in this project that writes a file.
`run_gate` returns a dictionary whose `gate` key is exactly the export contract's `gate` block,
and whose other keys carry what this module produces that the contract has no home for yet.
Those are listed under `CONTRACT_GAPS` and printed in the report, so they cannot be lost.
"""

from __future__ import annotations

import io
import math
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
    is_legal_disclosed_count,
    median_iqr,
    round20,
    safe_show,
)


class GateError(RuntimeError):
    """A gate-analysis stop condition.  Never downgraded to a warning."""


class GateRefusal(GateError):
    """The module declined to run at all, and nothing was priced, submitted or billed.

    A class of its own because a refusal is not a failure.  There are exactly three grounds:
    the feature validation did not certify the derived tables, the query path is unavailable,
    or the caller asked for an analysis the tier reached does not permit.  All three are
    correct behaviour and all three have to be distinguishable from a bug by the caller.
    """


class GateBudgetExceeded(GateError):
    """The priced total exceeded this step's budget, so nothing executed and nothing billed."""


class ModelDidNotConverge(GateError):
    """A fit did not converge.  Reported as a not-estimable node, never as a silent zero."""


class ModelSeparated(ModelDidNotConverge):
    """A fit ran away to a boundary: SEPARATION, complete or quasi.  Never a number.

    A SUBCLASS and not a sibling, deliberately.  Under separation the maximum likelihood
    estimate does not exist: the likelihood is still climbing at every finite beta and its
    supremum is approached only at infinity.  "The model did not converge" is therefore
    literally true of a separated fit and not a euphemism for it, so every caller that already
    routes `ModelDidNotConverge` to a not-estimable node routes this correctly WITHOUT being
    edited, and `cluster_bootstrap` already discards and COUNTS it.

    The subclass exists so the two can still be told apart where that matters.  A fit that ran
    out of the iteration budget is a numerical event; a fit that separated is a statement about
    the data, namely that at least one coefficient is identified only by a boundary.  The
    message names which coefficient, its value and the ceiling it broke, so a reader meets a
    named refusal rather than an absence.

    WHY NO SUPPRESSION SLUG OF ITS OWN.  EXPORT-CONTRACT 7.5 owns the suppression-reason
    vocabulary, the set is CLOSED, and `disclosure.py` plus `07_export.py` both cross-check it;
    a ninth slug invented here would be a printed sentence with no home in any of the three.
    The gap is REPORTED instead, in `CONTRACT_GAPS` under `separation_has_no_reason_slug`,
    which is this module's own mechanism for exactly this situation.
    """


# ======================================================================================
# (1) Vocabularies.  Every slug below is MACHINE vocabulary owned by ANALYSIS-PLAN.md or by
#     EXPORT-CONTRACT.md and is transcribed, never invented.  The display strings beside them
#     are transcribed from EXPORT-CONTRACT.md section 7, which is the sole authority for a
#     printed string, so a caption and a report line cannot say two different things.
# ======================================================================================

# ANALYSIS-PLAN.md 2.4, the seven group slugs, in the plan's own print order.  The first four
# partition the cohort; `fusion` and `decompression` partition it a second way; `all groups` is
# the total of both partitions.  The COLLAPSE LEVEL is decided by 03_cohort.py and read here,
# never re-decided and never hardcoded at four.
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

# EXPORT-CONTRACT.md 7.9, the protocol's A-through-F feasibility ledger.  `definition_display`
# is the protocol's own required-count column, verbatim, because Table 3 part A prints it as
# the row definition and the manuscript quotes the protocol.
GATE_STAGE_LETTERS: tuple[str, ...] = ("A", "B", "C", "D", "E", "F")
GATE_STAGE_SLUGS: Mapping[str, str] = MappingProxyType({
    "A": "stage_a_qualifying_episodes",
    "B": "stage_b_baseline_wear",
    "C": "stage_c_computable_window",
    "D": "stage_d_events",
    "E": "stage_e_computable_ratio",
    "F": "stage_f_events_by_stratum",
})
GATE_STAGE_LABELS: Mapping[str, str] = MappingProxyType({
    "A": "Qualifying spine episodes by procedure group",
    "B": "Episodes with at least 7 valid baseline days",
    "C": "Episodes with a computable post-discharge window",
    "D": "First acute-care events through day 90",
    "E": "Events with a computable proximal step ratio",
    "F": "Events by anatomic region and fusion status",
})
GATE_STAGE_DEFINITIONS: Mapping[str, str] = MappingProxyType({
    "A": "Unique qualifying spine episodes by procedure group",
    "B": "Episodes with at least 7 valid baseline days in the 8 to 30 days before surgery",
    "C": "Episodes with at least one computable post-discharge 3-day window",
    "D": "First emergency department visits, inpatient readmissions, and composite events "
         "through 90 days",
    "E": "Events with a computable proximal step ratio",
    "F": "Events by lumbar and cervical, and by fusion and decompression, strata",
})
GATE_STAGE_UNITS: Mapping[str, str] = MappingProxyType({
    "A": "episodes", "B": "episodes", "C": "episodes",
    "D": "events", "E": "events", "F": "events",
})
# Stage D alone is decomposed, into the three counts the protocol's own row names.  The three
# are NOT a partition: an emergency visit that becomes an admission is one composite event and
# is counted in the first two rows as well, which is exactly why the plan collapses it to one
# event and why the composite row is the one the gate reads.
STAGE_D_COMPONENTS: tuple[str, ...] = ("first_ed_visits", "readmissions", "composite")
STAGE_D_COMPONENT_LABELS: Mapping[str, str] = MappingProxyType({
    "first_ed_visits": "First emergency department visits",
    "readmissions": "Readmissions",
    "composite": "Composite events",
})
# The stage the gate is read off.  Named rather than written as a letter in a comparison,
# because "which stage decides the tier" is a scientific fact and not a formatting detail.
GATE_DECIDING_STAGE: str = "E"
GATE_DECIDING_DISPLAY: str = "stage E"

# EXPORT-CONTRACT.md 7.10, the four tiers.  `permitted_analysis_verbatim` and
# `permitted_claim_verbatim` are quoted from ANALYSIS-PLAN.md 1.2 UNALTERED: they are not
# paraphrased, not shortened and not softened, and this module copies them into the `gate`
# block without touching them.  `events_upper` at tier 4 is the largest count that still falls
# below the tier 3 boundary, which is why it reads one below that boundary rather than the
# boundary itself.
TIER_INDICES: tuple[int, ...] = (1, 2, 3, 4)
TIER_SLUGS: Mapping[int, str] = MappingProxyType({
    1: "full_model",
    2: "step_first_exploratory",
    3: "event_centered_only",
    4: "no_early_warning",
})
TIER_LABELS: Mapping[int, str] = MappingProxyType({
    1: "Full detection model",
    2: "Step-first exploratory model",
    3: "Event-centered association only",
    4: "No early-warning modeling",
})
TIER_BAND_DISPLAY: Mapping[int, str] = MappingProxyType({
    1: "100 or more usable events",
    2: "50 to 99 usable events",
    3: "20 to 49 usable events",
    4: "Fewer than 20 usable events",
})
TIER_PERMITTED_ANALYSIS_VERBATIM: Mapping[int, str] = MappingProxyType({
    1: "Full parsimonious detection model with internal validation. Temporal validation if "
       "the later era holds at least 40 events, otherwise optimism-corrected clustered "
       "bootstrap validation",
    2: "Step-first model with no broad feature selection. Clustered bootstrap validation. "
       "Labelled exploratory in the title, the abstract and every exhibit caption",
    3: "Event-centered association and visualization only. No prediction model, no "
       "discrimination metric, no alert-burden calculation",
    4: "No early-warning modeling at all",
})
TIER_PERMITTED_CLAIM_VERBATIM: Mapping[int, str] = MappingProxyType({
    1: "Detection performance may be reported as a performance estimate",
    2: "Association and exploratory performance, explicitly not a prediction tool",
    3: "Association only. No prediction-tool claim of any kind",
    4: "Feasibility statement only, with the count suppressed",
})
# EXPORT-CONTRACT.md 7.10.  Tiers 1 and 2 replace the whole exhibit set with the alternate set
# of ANALYSIS-PLAN 9.5, and `verify.py` asserts the primary set for schema version 1.x, so a
# tier of 1 or 2 REQUIRES a contract amendment before 07_export.py may run.  That is not a
# defect: it is the contract refusing to emit the primary column set with alternate content.
TIER_EXHIBIT_SET: Mapping[int, str] = MappingProxyType({
    1: "alternate", 2: "alternate", 3: "primary", 4: "primary",
})

# EXPORT-CONTRACT.md 7.5.  The reason a number is hidden, and the sentence printed in its
# place.  `not_permitted_by_tier` is the one this module adds to the bundle: it marks a value
# absent because the protocol forbade computing it, which is a different fact from a value
# hidden because its cell is small, and a reader who cannot tell them apart cannot tell a thin
# cohort from a disciplined one.
SUPPRESSION_REASONS: Mapping[str, str] = MappingProxyType({
    "cell_below_threshold": "20 or fewer, suppressed per All of Us dissemination policy",
    "numerator_suppressed": "suppressed because the count behind it is suppressed",
    "contributing_n_below_threshold": "20 or fewer contributors, suppressed",
    "secondary_suppression": "suppressed to protect a suppressed cell in the same total",
    "not_estimable_cell_size": "not estimable (cell size)",
    "not_estimable_convergence": "not estimable (model did not converge)",
    "not_estimable_data_unavailable": "not estimable (data not available)",
    # ANALYSIS-PLAN 4.9 names this reason and says it "belongs to the suppression-reason
    # vocabulary of EXPORT-CONTRACT section 7.5 ... and it is added there in the same commit".
    # It is transcribed here, not invented here.  No existing reason could have carried a
    # separated fit: it did not fail on cell size, no data were unavailable, the tier permitted
    # the analysis, and IT CONVERGED, which is why the convergence sentence would have been a
    # false sentence rather than a near-enough one.
    "not_estimable_separation": "not estimable (separation)",
    "not_permitted_by_tier": "not permitted at the feasibility tier reached",
})

# ANALYSIS-PLAN.md 4.4.  The two landmark conditions, kept apart everywhere.  These two slugs
# are the whole reason this vocabulary exists as a mapping rather than as two booleans in a
# frame: a label table forces the report to name which of the two it is talking about, and a
# reader who meets "no computable landmark" with no qualifier is being shown a sum that must
# never be taken.
LANDMARK_CONDITIONS: tuple[str, ...] = ("data", "definitional")
LANDMARK_CONDITION_LABELS: Mapping[str, str] = MappingProxyType({
    "data": "At least 2 post-discharge days in the window, fewer than 2 of them worn",
    "definitional": "Fewer than 2 post-discharge days in the window at all",
})
LANDMARK_CONDITION_DISPOSITION: Mapping[str, str] = MappingProxyType({
    "data": "Stays in the risk set as the co-primary exposure",
    "definitional": "Leaves at attrition rung 18",
})
# The rung this module reports against, by slug, so that a rename in the ladder breaks here
# rather than producing a report that cites a rung nobody can find.
STRUCTURAL_DELETION_RUNG_SLUG: str = "excl_event_without_computable_landmark"
STRUCTURAL_DELETION_RUNG_STEP: int = 18
STRUCTURAL_DELETION_REASON_DISPLAY: str = (
    "Event on post-discharge day 1 to 4, with no computable proximal window"
)

# ANALYSIS-PLAN.md 4.4, the two routes that put a risk-set member at a landmark day of 1 or
# less.  There are exactly two and the plan names both; a member at such a day by any third
# route is a defect in the sampling, not a case to be weighted around, and this module halts
# on one rather than inventing a third label for it.
EARLY_LANDMARK_ROUTES: tuple[str, ...] = ("day_of_week_relaxation", "partial_window_secondary")
EARLY_LANDMARK_ROUTE_LABELS: Mapping[str, str] = MappingProxyType({
    "day_of_week_relaxation": "Day-of-week relaxation, a control matched below the case's day",
    "partial_window_secondary": "Partial-window secondary, a case on post-discharge day 4",
})
MEMBER_ROLES: tuple[str, ...] = ("case", "control")
MEMBER_ROLE_LABELS: Mapping[str, str] = MappingProxyType({
    "case": "Cases", "control": "Controls",
})

# ANALYSIS-PLAN.md 4.7 and DAG-SCHEMA.md 8.14.  The relaxation ladder, which depends only on
# risk-set SIZE, which is a count, and never on an outcome or an estimate.
MATCH_RUNGS: tuple[int, ...] = (1, 2, 3)
MATCH_RUNG_LABELS: Mapping[int, str] = MappingProxyType({
    1: "Same post-discharge day and same day of week",
    2: "Post-discharge day within 2 days and the same weekday or weekend class",
    3: "Post-discharge day within 2 days, no day-of-week restriction",
})


# ======================================================================================
# (2) THE ANALYSIS CATALOGUE, which is how this module refuses by name.
#
#     Every named analysis Arm A could run appears here exactly once, with the tier indices at
#     which it is permitted written out EXPLICITLY rather than as an inequality.  An explicit
#     tuple cannot be read backwards: tier 1 is the LARGEST event count and tier 4 the
#     smallest, so `tier <= 2` and `tier >= 2` both look plausible and one of them silently
#     runs a detection model on 30 events.  A tuple of the tiers that permit the analysis has
#     no direction to get wrong.
#
#     `broad_feature_selection` is permitted at NO tier, including the highest.  ANALYSIS-PLAN
#     1.2: "There is no stepwise selection, no univariable screening threshold, and no lasso
#     path at any tier."  It is in the catalogue precisely so the refusal is printed rather
#     than being an absence a reader has to notice.
# ======================================================================================

ANALYSIS_CATALOGUE: tuple[tuple[str, str, tuple[int, ...]], ...] = (
    ("gate_ledger",
     "The A through F feasibility ledger",
     (1, 2, 3, 4)),
    ("structurally_deleted_event_timing",
     "Timing of events deleted for having no computable window",
     (1, 2, 3, 4)),
    ("landmark_condition_comparison",
     "Outcome rate with and without a computable step signal, full cohort",
     (1, 2, 3)),
    ("matched_set_size_distribution",
     "Controls per case",
     (1, 2, 3)),
    ("event_centered_description",
     "Event-centered normalized steps and wear fraction, day 14 before to day 7 after",
     (1, 2, 3)),
    ("unadjusted_association",
     "Unadjusted association between the proximal step ratio and the outcome",
     (1, 2, 3)),
    ("adjusted_conditional_logistic_model",
     "Adjusted conditional logistic regression, step-first covariate set",
     (1, 2)),
    ("observation_weighted_sensitivity",
     "Weighted for observation at the landmark",
     (1, 2)),
    ("absolute_risk_translation",
     "Absolute risk from the complementary full-cohort discrete-time model",
     (1, 2)),
    ("negative_control_window",
     "Negative-control window, 14 to 8 days before the event",
     (1, 2)),
    ("clustered_bootstrap_validation",
     "Optimism-corrected clustered bootstrap validation",
     (1, 2)),
    ("secondary_seven_day_horizon",
     "Secondary 7-day outcome horizon",
     (1, 2)),
    ("internal_validation",
     "Internal validation of the detection model",
     (1,)),
    ("temporal_validation",
     "Temporal validation in the later surgical era",
     (1,)),
    ("performance_panel",
     "Discrimination, calibration and predictive-value panel",
     (1,)),
    ("median_lead_time",
     "Median lead time",
     (1,)),
    ("alert_burden",
     "Alerts per 100 patient-days and false alerts per detected encounter",
     (1,)),
    ("multidomain_model",
     "Multidomain model adding nocturnal heart rate and sleep",
     (1,)),
    ("broad_feature_selection",
     "Broad feature selection, stepwise, screening or penalised",
     ()),
)

ANALYSIS_SLUGS: tuple[str, ...] = tuple(slug for slug, _, _ in ANALYSIS_CATALOGUE)
ANALYSIS_LABELS: Mapping[str, str] = MappingProxyType(
    {slug: label for slug, label, _ in ANALYSIS_CATALOGUE})
ANALYSIS_PERMITTED_TIERS: Mapping[str, tuple[int, ...]] = MappingProxyType(
    {slug: tiers for slug, _, tiers in ANALYSIS_CATALOGUE})

# EXPORT-CONTRACT.md 3.7, the THIRTEEN keys of `gate.arm_a.estimates`, in the order 3.7 lists
# them, and the analysis in the catalogue that produces each.  A key whose analysis the tier
# forbids is written as a suppressed node carrying `not_permitted_by_tier`, so the key is
# present and the refusal is printed.  A key absent from the block entirely would be
# indistinguishable from a bug.
#
# EIGHT OF THESE THIRTEEN ARE NEW AND THE LAG THEY CLOSE BLOCKED THE EXPORT AT TIERS 1 TO 3.
# This tuple carried the five keys of contract 1.5.0 while the contract had moved to thirteen,
# and `build_gate_block()` refuses any key 3.7 does not declare, which is the correct direction
# and is why the amendment lands before the module rather than after it.  The consequence of
# the lag was that the six collider keys never reached the block, so `07_export.py` had nothing
# to print in any of Table 4's six rate cells and refused the file at every tier that permits
# the comparison.  Tier 3 is the likeliest tier this study reaches and it is one of the three.
#
# THE TWO ODDS KEYS WERE ALREADY COMPUTED AND HAD NOWHERE TO GO.  Both come off the SAME
# unadjusted conditional fit, which is the one association tier 3 permits: the proximal step
# ratio's own contrast, and the co-primary exposure's own odds, which ANALYSIS-PLAN 4.4 calls
# an estimand of interest in its own right because it answers whether loss of data precedes
# utilization.  They were returned outside the gate block until 3.7 gained a key for each.
#
# THE SIX COLLIDER KEYS ARE ONE PER RATE CELL OF 5.7, WHICH IS THREE ROWS BY TWO RATE COLUMNS.
# Four would leave the standardized rate of each window group tracing to nothing, and
# ANALYSIS-PLAN 4.4 judges the two window groups SEPARATELY -- one may be standardized while
# the other is withheld, and the exhibit shows exactly that -- so two conditions judged
# separately need two cells and therefore two keys.
ESTIMATE_KEYS: tuple[str, ...] = (
    "adjusted_odds_per_lower_step_ratio",
    "unadjusted_odds_per_lower_step_ratio",
    "odds_of_no_computable_step_signal",
    "negative_control_window",
    "median_lead_time",
    "matched_set_size",
    "absolute_risk_translation",
    "collider_rate_with_signal",
    "collider_rate_without_signal",
    "collider_rate_ratio_crude",
    "collider_rate_with_signal_standardized",
    "collider_rate_without_signal_standardized",
    "collider_rate_ratio_standardized",
)
ESTIMATE_KEY_ANALYSIS: Mapping[str, str] = MappingProxyType({
    "adjusted_odds_per_lower_step_ratio": "adjusted_conditional_logistic_model",
    "unadjusted_odds_per_lower_step_ratio": "unadjusted_association",
    "odds_of_no_computable_step_signal": "unadjusted_association",
    "negative_control_window": "negative_control_window",
    "median_lead_time": "median_lead_time",
    "matched_set_size": "matched_set_size_distribution",
    "absolute_risk_translation": "absolute_risk_translation",
    "collider_rate_with_signal": "landmark_condition_comparison",
    "collider_rate_without_signal": "landmark_condition_comparison",
    "collider_rate_ratio_crude": "landmark_condition_comparison",
    "collider_rate_with_signal_standardized": "landmark_condition_comparison",
    "collider_rate_without_signal_standardized": "landmark_condition_comparison",
    "collider_rate_ratio_standardized": "landmark_condition_comparison",
})
# This module's own REPORT labels.  EXPORT-CONTRACT 7.15 owns the strings the bundle prints and
# they are shorter; these are the ones a reader of the printed report meets, where there is room
# to say which contrast a number belongs to.
ESTIMATE_KEY_LABELS: Mapping[str, str] = MappingProxyType({
    "adjusted_odds_per_lower_step_ratio":
        "Adjusted odds per 20-percentage-point lower proximal step ratio",
    "unadjusted_odds_per_lower_step_ratio":
        "Unadjusted odds per 20-percentage-point lower proximal step ratio",
    "odds_of_no_computable_step_signal":
        "Odds of an event with no computable step signal, the co-primary exposure",
    "negative_control_window": "Negative-control window, 14 to 8 days before the event",
    "median_lead_time": "Median lead time",
    "matched_set_size": "Controls per case",
    "absolute_risk_translation": "Absolute 3-day risk at the low proximal ratio",
    "collider_rate_with_signal":
        "Event rate with a computable step signal, crude",
    "collider_rate_without_signal":
        "Event rate without a computable step signal, crude",
    "collider_rate_ratio_crude":
        "Rate ratio, without versus with a computable step signal, crude",
    "collider_rate_with_signal_standardized":
        "Event rate with a computable step signal, standardized to the recovery day bands",
    "collider_rate_without_signal_standardized":
        "Event rate without a computable step signal, standardized to the recovery day bands",
    "collider_rate_ratio_standardized":
        "Rate ratio, without versus with a computable step signal, standardized",
})
# EXPORT-CONTRACT.md 2.2 and 2.4.  Which node shape and which unit each key carries.
# `absolute_risk_translation` is the one this module does NOT emit in the shape the contract
# declares, and the reason is recorded in `CONTRACT_GAPS` rather than being worked around in
# silence.  See that table.
#
# THE SIX COLLIDER KEYS ARE ESTIMATE-SHAPED AND CARRY NO INTERVAL, which is why they are built
# by `bound_node` and not by `estimate_node`.  ANALYSIS-PLAN 4.4 specifies a rate computed from
# the rounded numerator over the rounded denominator and specifies no interval for it; a
# confidence interval invented here would be a statistic the prespecification does not carry,
# printed in the one column a reader would take on trust.  A bound is a bound: the node carries
# the point on all three numeric keys and an EMPTY interval display, so no renderer can print
# it as an interval.
ESTIMATE_KEY_SHAPE: Mapping[str, str] = MappingProxyType({
    "adjusted_odds_per_lower_step_ratio": "estimate",
    "unadjusted_odds_per_lower_step_ratio": "estimate",
    "odds_of_no_computable_step_signal": "estimate",
    "negative_control_window": "estimate",
    "median_lead_time": "quantile",
    "matched_set_size": "quantile",
    "absolute_risk_translation": "estimate",
    "collider_rate_with_signal": "bound",
    "collider_rate_without_signal": "bound",
    "collider_rate_ratio_crude": "bound",
    "collider_rate_with_signal_standardized": "bound",
    "collider_rate_without_signal_standardized": "bound",
    "collider_rate_ratio_standardized": "bound",
})
ESTIMATE_KEY_UNIT: Mapping[str, str] = MappingProxyType({
    "adjusted_odds_per_lower_step_ratio": "odds_ratio",
    "unadjusted_odds_per_lower_step_ratio": "odds_ratio",
    "odds_of_no_computable_step_signal": "odds_ratio",
    "negative_control_window": "odds_ratio",
    "median_lead_time": "hours",
    "matched_set_size": "count",
    "absolute_risk_translation": "percent",
    "collider_rate_with_signal": "rate_per_1000_episode_days",
    "collider_rate_without_signal": "rate_per_1000_episode_days",
    "collider_rate_ratio_crude": "rate_ratio",
    "collider_rate_with_signal_standardized": "rate_per_1000_episode_days",
    "collider_rate_without_signal_standardized": "rate_per_1000_episode_days",
    "collider_rate_ratio_standardized": "rate_ratio",
})
# EXPORT-CONTRACT.md 2.4, the decimals for each unit.  A count and a percent print with none, an
# odds ratio with two.  Rounding a continuous statistic to 20 would be a category error and is
# not done anywhere in this module: `round20` applies to COUNTS only.  The two rate units are
# 2.4's own and print at two decimals, which is what `07_export.py`'s `UNIT_DECIMALS` carries
# for them: an event rate per thousand episode-days on a cohort of this size is a single digit,
# and a rate ratio near one is not readable at fewer.
UNIT_DECIMALS: Mapping[str, int] = MappingProxyType({
    "odds_ratio": 2, "hours": 0, "count": 0, "percent": 0, "days": 0, "dimensionless": 2,
    "rate_per_1000_episode_days": 2, "rate_ratio": 2,
})
# FIXED HERE, BEFORE ANY NUMBER EXISTS.  A 3-day acute-care risk after spine surgery is
# expected well below one percent, and the contract's zero-decimal percent rule would print
# every such value as zero.  Two decimals is chosen a priori and recorded in `CONTRACT_GAPS`;
# a decimals rule chosen after seeing the estimate would be a different kind of object.
ABSOLUTE_RISK_DECIMALS: int = 2


def permitted_at(analysis_slug: str, tier_index: int) -> bool:
    """Is this named analysis permitted at this tier?  The catalogue is the only authority."""
    if analysis_slug not in ANALYSIS_PERMITTED_TIERS:
        raise GateError(
            f"'{analysis_slug}' is not in the analysis catalogue. Every analysis Arm A can run "
            f"is named there, so that the ones the tier forbids can be refused by name rather "
            f"than being absent."
        )
    return int(tier_index) in ANALYSIS_PERMITTED_TIERS[analysis_slug]


# ======================================================================================
# (3) Locked constants.  Every one is read out of ANALYSIS-PLAN.md, DAG-SCHEMA.md or
#     EXPORT-CONTRACT.md and none is chosen here.  The three that the plan leaves open are
#     marked CLOSED HERE and are listed in `CONTRACT_GAPS`, because a constant fixed by this
#     module before any number is seen is prespecification, and the same constant fixed after
#     a look at the curve is not.
# ======================================================================================

SEED: int = 0                                   # ANALYSIS-PLAN 10, everywhere, Python and R.

# ANALYSIS-PLAN.md 1.2, the protocol's tier thresholds.  These are EVENT thresholds and they
# are NOT the disclosure floor.  `TIER_3_MIN_EVENTS` coincides with `disclosure.MIN_CELL` at
# 20 and plan 1.3 names the coincidence rather than tripping over it: the two are unrelated in
# origin and identical in value, so they stay two constants and are never aliased.  Aliasing
# them would let a future edit to the disclosure floor silently move a protocol threshold.
TIER_1_MIN_EVENTS: int = 100
TIER_2_MIN_EVENTS: int = 50
TIER_3_MIN_EVENTS: int = 20
# ANALYSIS-PLAN 1.2 again: temporal validation replaces internal validation at tier 1 only if
# the later surgical era holds at least this many events.
TEMPORAL_VALIDATION_MIN_EVENTS: int = 40

# ANALYSIS-PLAN.md 4.3, derived in the plan's own six-row table from the two-valid-day rule and
# asserted by the stored procedure across the whole panel.  DAY 1 TO 4, NOT DAY 1 TO 3.
STRUCTURAL_DELETION_FIRST_DAY: int = 1
STRUCTURAL_DELETION_LAST_DAY: int = 4
FIRST_ELIGIBLE_EVENT_DAY: int = 5               # the first event with a computable landmark
FIRST_ELIGIBLE_LANDMARK_DAY: int = 2            # its landmark, post-discharge day 2
FIRST_FULLY_POST_DISCHARGE_EVENT_DAY: int = 6

# ANALYSIS-PLAN.md 4.2, the exposure.
LANDMARK_OFFSET_DAYS: int = 3                   # the landmark is the event date minus 3
LANDMARK_WINDOW_FIRST_OFFSET: int = 5           # window is E minus 5 ...
LANDMARK_WINDOW_LAST_OFFSET: int = 3            # ... through E minus 3
LANDMARK_WINDOW_DAYS: int = 3
LANDMARK_MIN_VALID_DAYS: int = 2
# The reference 7-day window of the local step deterioration feature, days E-12 to E-6.
REFERENCE_WINDOW_FIRST_OFFSET: int = 12
REFERENCE_WINDOW_LAST_OFFSET: int = 6
# ANALYSIS-PLAN 4.8, the negative control: window E-14 to E-8, among events after day 15.
NEGATIVE_CONTROL_FIRST_OFFSET: int = 14
NEGATIVE_CONTROL_LAST_OFFSET: int = 8
NEGATIVE_CONTROL_MIN_EVENT_DAY: int = 16        # "occurring after post-discharge day 15"
# The outcome horizon: an encounter within the next 3 calendar days of the landmark.
OUTCOME_HORIZON_DAYS: int = 3

# ANALYSIS-PLAN.md 4.2, the exposure spline.  Three knots FIXED at these ratios, not at data
# quantiles: quantile knots would make the basis depend on the observed distribution, which is
# the one thing a prespecification exists to remove.
STEP_RATIO_KNOTS: tuple[float, ...] = (0.40, 0.70, 1.00)
# ANALYSIS-PLAN.md 3.6, the post-discharge-day spline of the complementary discrete-time model.
DAY_SPLINE_KNOTS: tuple[float, ...] = (2.0, 6.0, 12.0, 21.0, 32.0)
# ANALYSIS-PLAN.md 3.6, age.
AGE_SPLINE_KNOTS: tuple[float, ...] = (45.0, 60.0, 75.0)

# CLOSED HERE.  The plan fixes the DECREMENT at 20 percentage points but not the two ratios the
# contrast is taken between, and a spline effect is not constant so the pair has to be named.
# These are the boundary of the plan's own top display category and one decrement below it, so
# the reported odds ratio compares a participant walking 60% of their own baseline against one
# walking 80%.  Fixed here, before any estimate exists, and printed in the note beside the
# number so no reader has to guess which pair was used.
STEP_RATIO_DECREMENT: float = 0.20
STEP_RATIO_REFERENCE: float = 0.80
STEP_RATIO_CONTRAST: float = STEP_RATIO_REFERENCE - STEP_RATIO_DECREMENT
# The same anchor drives the absolute-risk translation, so the two numbers describe one
# comparison rather than two.
ABSOLUTE_RISK_ANCHOR: float = STEP_RATIO_CONTRAST

# ANALYSIS-PLAN.md 4.2, the display categories.  They MAY be displayed and they NEVER replace
# the continuous analysis, which is why they appear as a description vocabulary and never as a
# model term.
STEP_RATIO_BAND_SLUGS: tuple[str, ...] = (
    "under_40", "40_to_59", "60_to_79", "80_or_more", "no_computable_signal",
)
STEP_RATIO_BAND_LABELS: Mapping[str, str] = MappingProxyType({
    "under_40": "Under 40% of baseline",
    "40_to_59": "40% to 59% of baseline",
    "60_to_79": "60% to 79% of baseline",
    "80_or_more": "80% of baseline or more",
    "no_computable_signal": "No computable step signal",
})

# ANALYSIS-PLAN.md 4.4, the early-landmark weight rule.  A member is weighted when its own
# landmark day is 2 or more; a member at 1 or less leaves the WEIGHTED SENSITIVITY ONLY and
# stays in the primary, stays in its risk set, and still carries the co-primary exposure.
MIN_WEIGHTED_LANDMARK_DAY: int = 2

# ANALYSIS-PLAN.md 4.5, the two caps and the order they are applied in.
CONTROLS_PER_CASE_CAP: int = 5
CONTROL_LANDMARKS_PER_PARTICIPANT_CAP: int = 3

# ANALYSIS-PLAN.md 3.8 and 4.5.  Resample b is seeded `default_rng([SEED, b])`, so any single
# resample regenerates on its own.  The primary contrast takes the full count; a sensitivity
# row is read for direction and overlap rather than for a P value, so it takes half.
BOOTSTRAP_RESAMPLES_PRIMARY: int = 1000
BOOTSTRAP_RESAMPLES_SENSITIVITY: int = 500
CONFIDENCE_LEVEL: float = 0.95
BOOTSTRAP_LOWER_PERCENTILE: float = 2.5
BOOTSTRAP_UPPER_PERCENTILE: float = 97.5
# ANALYSIS-PLAN 3.8: a resample whose model fails to converge is discarded and COUNTED, and
# more than this share failing is descent trigger T4 rather than a footnote.
BOOTSTRAP_MAX_FAILURE_SHARE: float = 0.25

# CLOSED HERE.  The alert threshold of the tier-1 panel targets 80% sensitivity, which the plan
# names; the lead-time definition it implies is not written down anywhere, so it is fixed here.
# An alert at post-discharge day d rests on the window ending at day d minus 3, so the alert
# could not have been raised before that day's data existed, and the lead time is measured from
# there to the event.  The lookback is one week, so a lead time runs from 3 to 9 days.
ALERT_TARGET_SENSITIVITY: float = 0.80
LEAD_TIME_LOOKBACK_DAYS: int = 6
HOURS_PER_DAY: int = 24

# Newton-Raphson controls.  Fixed, so a fit either converges the same way in every session or
# is reported as not estimable; there is no adaptive rule that could make the answer depend on
# the machine it ran on.
MAX_NEWTON_ITERATIONS: int = 100
MAX_STEP_HALVINGS: int = 30                     # a FIXED damping budget, not an
                                                # adaptive rule: a full Newton step
                                                # that would lower the likelihood is
                                                # halved a fixed number of times, so
                                                # a wide design over few matched sets
                                                # converges rather than oscillating
NEWTON_TOLERANCE: float = 1e-9
RIDGE_EPSILON: float = 1e-10                    # a floor on the information matrix, not a prior

# ANALYSIS-PLAN 4.9, "The coefficient ceiling that refuses a separated fit", transcribed under
# the plan's own name for it.  PRESPECIFIED, inside the plan hash, and it can only suppress.
#
# WHAT IT CLOSES.  The convergence rule below accepts a fit whose LIKELIHOOD has flattened even
# though its COEFFICIENT is still growing, and that is right for the ordinary case: without it
# a thin matched design would be called a failure when its maximum is merely further away than
# a step-only rule can see.  It is also the signature of QUASI-SEPARATION, where the maximum
# lies at infinity and the fit reports whatever value the optimizer happened to stop at.
# PERFECT separation was already caught, because that fit does not converge at all.  Quasi
# separation is the common case, and IT CONVERGED, which is exactly what made it dangerous.
#
# WHAT IT BINDS, per 4.9: EVERY logistic fit in Arm A.  The conditional model of 4.5, each of
# that model's bootstrap resamples, and the complementary full-cohort discrete-time model of
# 4.6 from which the absolute risks come.  THE REFUSAL IS AT THE LEVEL OF THE FIT and not of
# the single coefficient that broke it, because a coefficient at the ceiling means the
# information matrix is near-degenerate and no standard error off that fit is trustworthy,
# including the ones on coefficients that look ordinary.
#
# WHY TEN, AND WHY IT WAS NOT TUNED TO THE CASE THAT PROMPTED IT.  Ten on the log-odds scale is
# the conventional separation-detection threshold in the logistic-regression literature and is
# the value implementations use to warn that a fit may be separated.  An absolute coefficient
# of 10 is an odds ratio of about 22,026, which is not a finding this design could produce, and
# nothing on the covariate list of 4.6 can produce one either.  The plan records deliberately
# that the constant was NOT set to the smallest value that would have caught the synthetic fit
# that prompted the rule, whose coefficient sat at 8.961: a threshold chosen to catch the one
# example that prompted it is a threshold fitted to one draw, which is the class of choice the
# prespecification exists to remove.  So a fit below the ceiling with a very wide interval
# STILL PRINTS, and the width of that interval is the reader's own signal.  What the ceiling
# buys is a BOUND ON WHAT CAN BE EXPORTED, not a promise that every wide interval disappears.
#
# IT NEVER PUBLISHES.  Breaking the ceiling raises `ModelSeparated` and returns nothing.  There
# is no clipped estimate, no winsorized coefficient and no ridge-shrunk substitute, and 4.9
# forbids printing the offending value itself, as a bound or in a footnote, because printing it
# is the clipped number arriving by a second route.
MAX_ABS_COEFFICIENT: float = 10.0
# A float comparison tolerance.  It is not a threshold on any quantity of interest.
FLOAT_TOLERANCE: float = 1e-9


# ======================================================================================
# (4) What this module produces that the export contract has no home for, and the one place
#     it deliberately emits a different node shape from the one the contract declares.
#
#     REPORTED, NOT ROUTED AROUND.  Each entry names the quantity, where it currently goes, and
#     the smallest amendment that would give it a home.  They are printed at the end of the
#     report so that they reach the next task rather than being discovered at proof stage.
# ======================================================================================

# FOUR ENTRIES LEFT THIS TABLE AT CONTRACT 1.7.0, and they left because the work landed and
# not because they were softened.  They are named here rather than deleted silently, so that a
# reader of an older report can see where each went:
#
#   the unadjusted association had no key      3.7 declares
#                                              `unadjusted_odds_per_lower_step_ratio`
#   the co-primary exposure's odds had no key  3.7 declares
#                                              `odds_of_no_computable_step_signal`
#   the collider comparison had no exhibit     5.7 is `table4_collider_comparison.csv`, three
#                                              rows by two rate columns, and 3.7 declares one
#                                              key for each of the six rate cells
#   the event-centered curve had no exhibit    4.4 is `figure4_event_centered_activity.csv`,
#                                              two series over twenty-two offsets, in the
#                                              PRIMARY exhibit set because tier 3 permits the
#                                              visualization and tier 3 is the likeliest tier
#
# Everything below is still open.  A gap leaves this tuple when the contract carries the
# quantity, never when the module finds somewhere else to put it.
CONTRACT_GAPS: tuple[Mapping[str, str], ...] = (
    MappingProxyType({
        "slug": "separation_reason_not_yet_transcribed_downstream",
        "what": "The suppression reason a fit refused at the coefficient ceiling of "
                "ANALYSIS-PLAN 4.9 carries",
        "problem": "4.9 names the reason, fixes its sentence as 'not estimable (separation)', "
                   "and says it belongs to EXPORT-CONTRACT section 7.5 'and it is added there "
                   "in the same commit'. This module transcribes it, because the plan is the "
                   "authority and 4.9 states that no existing reason could carry a separated "
                   "fit: it did not fail on cell size, no data were unavailable, the tier "
                   "permitted the analysis, and IT CONVERGED, which is why the convergence "
                   "sentence would be a false sentence rather than a near-enough one. Three "
                   "surfaces downstream have to carry the reason before a refused row can "
                   "travel: EXPORT-CONTRACT 7.5, the disclosure module's transcription of 7.5, "
                   "and the export module's own set of sentences that mean a cell is hidden. "
                   "Until all three carry it, a refused row reaches the bundle with a sentence "
                   "the export module will not recognise as a suppression. THIS ENTRY DOES NOT "
                   "RECORD WHICH OF THE THREE CURRENTLY DO. A snapshot written here goes stale "
                   "the moment one of them lands, and a stale snapshot in a report is worse "
                   "than no snapshot; the arbiter is the disclosure module's own vocabulary "
                   "assert, which is red until the three agree and green afterwards.",
        "emitted": "a suppressed node carrying the separation reason and its plan-fixed "
                   "sentence, with the two counts 4.9 obliges printed in the report",
        "amendment": "EXPORT-CONTRACT 7.5 gains the row the plan already names, and the "
                     "disclosure module and the export module transcribe it in the same pass, "
                     "since all three are checked against each other and a test in the "
                     "disclosure suite turns red until they agree. NOTHING IS ROUTED AROUND "
                     "MEANWHILE: the ceiling already refuses the number, and this amendment "
                     "decides only which true sentence is printed in its place.",
    }),
    MappingProxyType({
        "slug": "absolute_risk_node_shape",
        "what": "The absolute risk from the complementary discrete-time model",
        "problem": "EXPORT-CONTRACT 3.7 declares it a percentage node, whose required keys "
                   "include a numerator and a denominator. A model-predicted absolute risk is "
                   "a fitted probability and has neither. Emitting one would invent a "
                   "numerator that does not exist, which is the same defect already settled "
                   "for the share reaching 80% of baseline.",
        "emitted": "an estimate node with unit percent, carrying a confidence interval, "
                   "printed to two decimals rather than the zero the percent unit fixes",
        "amendment": "EXPORT-CONTRACT 3.7 changes the declared shape of "
                     "absolute risk translation from percentage to estimate on the percent "
                     "scale, exactly as it already does elsewhere, AND section 2.4 gains a "
                     "decimals rule that can render a risk below one percent. At an event "
                     "rate of a few per thousand person-days, zero decimals print every "
                     "absolute risk in this study as zero.",
    }),
    MappingProxyType({
        "slug": "event_centered_curve_denominator_has_no_key",
        "what": "The event-centered curve's own denominator, the risk-set members plotted and "
                "the members the structural filter removed",
        "problem": "EXPORT-CONTRACT 4.4 gives the figure a per-offset contributor count and "
                   "3.8 makes its printed denominator a key of the bundle's own denominator "
                   "block, where the only available key is the composite first-event count. "
                   "That count is not the population the curve is drawn over: the curve is "
                   "drawn over risk-set members, and since it now carries the same structural "
                   "filter the fits carry, the two differ by the members that filter removes. "
                   "The plate note therefore prints a number larger than the curve's own.",
        "emitted": "returned on the curve frame, two columns constant down each role's block, "
                   "and printed in this module's report with its own denominator line",
        "amendment": "EXPORT-CONTRACT 3.2 gains a denominator for the event-centered curve's "
                     "plotted members, and 3.8 points the figure's denominator key at it. A "
                     "figure-level count with no entry in that block cannot be pointed at, "
                     "which is why this is an amendment and not a payload field.",
    }),
    MappingProxyType({
        "slug": "tier_one_or_two_switches_the_exhibit_set",
        "what": "Everything, at tier 1 or 2",
        "problem": "ANALYSIS-PLAN 9.5 replaces Figure 2, Figure 3, Table 1, Table 2 and Table "
                   "3 wholesale at 50 or more events, and verify.py asserts the primary "
                   "exhibit set for schema version 1.x. This is CORRECT behaviour, not a "
                   "defect: the contract is refusing to emit the primary column set with "
                   "alternate content.",
        "emitted": "the exhibit set on the tier record reads alternate, and the report halts "
                   "the export with that sentence",
        "amendment": "a second full pass over EXPORT-CONTRACT sections 4 and 5 before the "
                     "exporter runs. Nothing else unblocks it.",
    }),
    MappingProxyType({
        "slug": "table_3_part_b_example_quotes_the_protocol_not_the_label_table",
        "what": "The tier 4 permitted claim",
        "problem": "EXPORT-CONTRACT 5.5's worked example prints the protocol's phrasing, while "
                   "its own section 7.10 gives a different verbatim claim and section 6 makes "
                   "section 7 the sole authority for a printed string. The two cannot both be "
                   "verbatim.",
        "emitted": "the section 7.10 wording, because section 7 is the declared authority",
        "amendment": "EXPORT-CONTRACT 5.5's example is corrected to the 7.10 wording.",
    }),
)


# ======================================================================================
# (5) Cost policy, and the two-phase query plan that makes the tier gate real.
#
#     PHASE 1 counts.  PHASE 2 models.  Phase 2 is priced and submitted only after the tier has
#     been decided from the phase 1 count, and only for the queries that tier permits.  A tier
#     4 run therefore never prices and never submits a model query at all, which is both the
#     cheapest outcome and the only one that can honestly be called a gate.
#
#     Two independent guards, as everywhere else in this pipeline: a per-query cap is runaway
#     protection for ONE query, and the aggregate budget is the allowance for the step.  They
#     deliberately sum to different numbers.
# ======================================================================================

USD_PER_TIB: float = 6.25                       # display only; enforcement is in bytes
BYTES_PER_GIB: int = 1024 ** 3

PHASE_ONE_QUERY_KEYS: tuple[str, ...] = (
    "gate ladder",
    "structurally deleted event timing",
)
PHASE_TWO_QUERY_KEYS: tuple[str, ...] = (
    "landmark panel",
    "matched set sizes",
    "event centered curve",
    "risk set model frame",
    "negative control frame",
    "discrete time panel",
)
QUERY_KEYS: tuple[str, ...] = PHASE_ONE_QUERY_KEYS + PHASE_TWO_QUERY_KEYS

# Which tiers each query runs at, written out explicitly for the same reason the analysis
# catalogue is: an inequality over a tier index that counts DOWN as the cohort grows is a
# direction anyone can get wrong once.
QUERY_PERMITTED_TIERS: Mapping[str, tuple[int, ...]] = MappingProxyType({
    "gate ladder": (1, 2, 3, 4),
    "structurally deleted event timing": (1, 2, 3, 4),
    "landmark panel": (1, 2, 3),
    "matched set sizes": (1, 2, 3),
    "event centered curve": (1, 2, 3),
    "risk set model frame": (1, 2, 3),
    "negative control frame": (1, 2),
    "discrete time panel": (1, 2),
})
# The analysis in the catalogue each query serves, so that a query cannot outlive the analysis
# that justified it and a refused analysis cannot leave a query running.
QUERY_ANALYSIS: Mapping[str, str] = MappingProxyType({
    "gate ladder": "gate_ledger",
    "structurally deleted event timing": "structurally_deleted_event_timing",
    "landmark panel": "landmark_condition_comparison",
    "matched set sizes": "matched_set_size_distribution",
    "event centered curve": "event_centered_description",
    "risk set model frame": "unadjusted_association",
    "negative control frame": "negative_control_window",
    "discrete time panel": "absolute_risk_translation",
})

# Every read is of a `{DERIVED}` table, so this whole step is small change: `events` is order
# 100 to 400 rows, `risk_sets` order 1,000, `landmark_daily` and `drd_daily` order 27,000 to
# 54,000, `features` order 300 to 600.  The caps are not sized to the expectation, because the
# expectation is what a dry run is for; they are sized so that a join that has accidentally
# become a cross product fails rather than bills.
PLANNED_MAX_GB: Mapping[str, float] = MappingProxyType({
    "gate ladder": 1.0,
    "structurally deleted event timing": 0.5,
    "landmark panel": 1.0,
    "matched set sizes": 0.5,
    "event centered curve": 1.0,
    "risk set model frame": 1.0,
    "negative control frame": 1.0,
    "discrete time panel": 2.0,
})
GATE_BUDGET_GB: float = 6.0                     # about four cents at the price above


# ======================================================================================
# (6) SQL construction.
#
#     EVERY TEMPLATE IS A PLAIN, NON-f STRING WITH `{DERIVED}` INTACT, because the config
#     notebook's `_fill` substitutes the placeholder itself and raises on any residual
#     `{IDENTIFIER}`, and an f-string would have consumed the braces before it ever saw them.
#     This module's own constants reach a template through the `<<TOKEN>>` form instead, which
#     cannot collide with a brace and fails loudly: an unknown token raises and a surviving
#     `<<` raises, so a constant can never be half-substituted into a query that then runs.
#
#     NO IDENTIFIER REACHES THE KERNEL.  The two model frames are the only participant-level
#     frames in this pipeline, and they carry DENSE_RANK surrogates for person, episode and
#     matched set rather than the identifiers themselves.  A person identifier is not needed to
#     cluster on a person; a dense integer is, and it is not an identifier.  The underlying ids
#     are deterministic (DAG-SCHEMA 8.4, 8.12), so the surrogates are stable across a rerun.
# ======================================================================================

# ANALYSIS-PLAN.md 2.2, used only by the stage B query, which counts the protocol's own
# required count rather than reading a ladder rung whose predicate carries the span rule too.
BASELINE_FIRST_DAY_BEFORE: int = 30
BASELINE_LAST_DAY_BEFORE: int = 8
BASELINE_MIN_VALID_DAYS: int = 7
# The event-centered display window of ANALYSIS-PLAN 4.8, relative to the matched day.
EVENT_CENTERED_FIRST_OFFSET: int = 14           # day E minus 14
EVENT_CENTERED_LAST_OFFSET: int = 7             # through day E plus 7
# DAG-SCHEMA.md 8.12, the denominator of the wear fraction: observed heart-rate minutes over
# the minutes in a day.  A null wear figure means NO heart-rate record, which is not the claim
# that the participant wore the device for zero minutes, so it is dropped and never averaged
# in as a zero.
MINUTES_PER_DAY: int = 1440

_SQL_TOKEN = re.compile(r"<<([A-Z0-9_]+)>>")

_SQL_CONSTANTS: Mapping[str, Any] = MappingProxyType({
    "BASELINE_MIN_VALID_DAYS": BASELINE_MIN_VALID_DAYS,
    "BASELINE_FIRST_DAY_BEFORE": BASELINE_FIRST_DAY_BEFORE,
    "BASELINE_LAST_DAY_BEFORE": BASELINE_LAST_DAY_BEFORE,
    "STRUCTURAL_DELETION_FIRST_DAY": STRUCTURAL_DELETION_FIRST_DAY,
    "STRUCTURAL_DELETION_LAST_DAY": STRUCTURAL_DELETION_LAST_DAY,
    "LANDMARK_OFFSET_DAYS": LANDMARK_OFFSET_DAYS,
    "LANDMARK_WINDOW_FIRST_OFFSET": LANDMARK_WINDOW_FIRST_OFFSET,
    "LANDMARK_WINDOW_LAST_OFFSET": LANDMARK_WINDOW_LAST_OFFSET,
    "LANDMARK_MIN_VALID_DAYS": LANDMARK_MIN_VALID_DAYS,
    "REFERENCE_WINDOW_FIRST_OFFSET": REFERENCE_WINDOW_FIRST_OFFSET,
    "REFERENCE_WINDOW_LAST_OFFSET": REFERENCE_WINDOW_LAST_OFFSET,
    "NEGATIVE_CONTROL_FIRST_OFFSET": NEGATIVE_CONTROL_FIRST_OFFSET,
    "NEGATIVE_CONTROL_LAST_OFFSET": NEGATIVE_CONTROL_LAST_OFFSET,
    "NEGATIVE_CONTROL_MIN_EVENT_DAY": NEGATIVE_CONTROL_MIN_EVENT_DAY,
    "EVENT_CENTERED_FIRST_OFFSET": EVENT_CENTERED_FIRST_OFFSET,
    "EVENT_CENTERED_LAST_OFFSET": EVENT_CENTERED_LAST_OFFSET,
    "MINUTES_PER_DAY": MINUTES_PER_DAY,
    "MIN_WEIGHTED_LANDMARK_DAY": MIN_WEIGHTED_LANDMARK_DAY,
    "CONTROLS_PER_CASE_CAP": CONTROLS_PER_CASE_CAP,
    "CONTROL_LANDMARKS_PER_PARTICIPANT_CAP": CONTROL_LANDMARKS_PER_PARTICIPANT_CAP,
})


def _sql(template: str) -> str:
    """Substitute this module's `<<TOKEN>>` constants, leaving `{DERIVED}` untouched."""
    def swap(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name not in _SQL_CONSTANTS:
            raise GateError(
                f"a query template names the constant <<{name}>>, which this module does not "
                f"define. Add it to the locked constants rather than typing the number into "
                f"the query."
            )
        return str(_SQL_CONSTANTS[name])
    out = _SQL_TOKEN.sub(swap, template)
    if "<<" in out or ">>" in out:
        raise GateError(
            "a query template still carries an unsubstituted token after substitution, so a "
            "constant would have reached BigQuery half-written. Nothing was submitted."
        )
    return out


_COLUMNS_MARKER = "-- @columns:"


def declared_columns(sql: str) -> tuple[str, ...]:
    """The result columns a query DECLARES, read off its own `-- @columns:` line.

    The line exists so that the Python side and the emitted SQL cannot drift apart without
    something failing on a laptop: the self-test asserts the line is present exactly once and
    that every name on it appears in the query as an explicit `AS name` alias.
    """
    lines = [line for line in sql.splitlines() if line.strip().startswith(_COLUMNS_MARKER)]
    if len(lines) != 1:
        raise GateError(
            f"a query carries {len(lines)} column-declaration lines and must carry exactly one"
        )
    body = lines[0].split(_COLUMNS_MARKER, 1)[1]
    names = tuple(name.strip() for name in body.split(",") if name.strip())
    if not names:
        raise GateError("a query declares no result columns")
    return names


# --------------------------------------------------------------------------------------
# The covariate head.  ANALYSIS-PLAN 4.6: age, sex assigned at birth, baseline body mass
# index, BASELINE STEPS, comorbidity burden, index length of stay, calendar year and device
# class.  Baseline steps IS a covariate in Arm A, unlike Arm B, because the exposure is a ratio
# whose denominator is the baseline and adjusting for the denominator of an exposure is
# standard rather than circular.  This head is written once and joined by both model queries so
# the two cannot carry different covariate sets.
# --------------------------------------------------------------------------------------

_COVARIATE_HEAD = """
WITH cohort AS (
  SELECT
    f.episode_id       AS episode_id,
    f.person_id        AS person_id,
    f.procedure_group  AS procedure_group,
    f.procedure_class  AS procedure_class,
    f.fusion           AS fusion,
    f.region           AS region,
    f.age_at_index     AS age_at_index,
    f.sex_at_birth     AS sex_at_birth,
    f.bmi_imputed      AS bmi_imputed,
    f.bmi_missing      AS bmi_missing,
    f.charlson_ordinal AS charlson_ordinal,
    f.los_days         AS los_days,
    f.index_year       AS index_year,
    f.covid_era        AS covid_era,
    f.device_family    AS device_family,
    f.baseline_steps   AS baseline_steps,
    f.n_valid_baseline_days AS n_valid_baseline_days
  FROM `{DERIVED}.features` AS f
)"""


def gate_ladder_sql() -> str:
    """The protocol's A-through-F feasibility ledger, as one long frame of exact integers.

    Six stages in one query because they are one exhibit and because a stage that ran in its own
    session could disagree with its neighbour after a partial rebuild.  Stages A and F return
    the four collapse-level-1 groups only; the fusion-and-decompression pair and the total are
    summed from those EXACT integers in Python, never from rounded parts, because summing
    rounded parts puts an error of up to ten per cell into every margin.

    Stage A counts episodes CARRYING a procedure group.  Episodes with no assignable group,
    which are the thoracic-only, unspecified-only and simultaneous two-region ones, leave at
    ladder rungs 6 to 8 and are not "by procedure group" in any sense the protocol's own row
    means; counting them in the total but in no column would make the row fail to close.

    The three stage D components are NOT a partition.  An emergency visit that becomes a
    same-day admission is one composite event and appears in both of the first two counts,
    which is exactly why the plan collapses it to one event and why the gate reads the
    composite row and not a sum of the other two.
    """
    return _sql("""
-- @columns: stage_letter, part_slug, group_slug, n_units
SELECT
  'A'                  AS stage_letter,
  'total'              AS part_slug,
  e.procedure_group    AS group_slug,
  COUNT(*)             AS n_units
FROM `{DERIVED}.episodes` AS e
WHERE e.procedure_group IS NOT NULL
GROUP BY group_slug
UNION ALL
SELECT 'B', 'total', 'all_groups',
       COUNTIF(b.n_valid_baseline_days >= <<BASELINE_MIN_VALID_DAYS>>)
FROM `{DERIVED}.baseline` AS b
UNION ALL
SELECT 'C', 'total', 'all_groups',
       COUNTIF(NOT x.x_no_computable_post_discharge_window)
FROM `{DERIVED}.episodes_eligible` AS x
UNION ALL
SELECT 'D', 'first_ed_visits', 'all_groups',
       COUNTIF(v.event_kind IN ('emergency_department', 'ed_then_inpatient'))
FROM `{DERIVED}.events` AS v
WHERE v.is_first_event
UNION ALL
SELECT 'D', 'readmissions', 'all_groups',
       COUNTIF(v.event_kind IN ('inpatient', 'ed_then_inpatient'))
FROM `{DERIVED}.events` AS v
WHERE v.is_first_event
UNION ALL
SELECT 'D', 'composite', 'all_groups', COUNT(*)
FROM `{DERIVED}.events` AS v
WHERE v.is_first_event
UNION ALL
SELECT 'D', 'total', 'all_groups', COUNT(*)
FROM `{DERIVED}.events` AS v
WHERE v.is_first_event
UNION ALL
SELECT 'E', 'total', 'all_groups', COUNTIF(v.has_computable_landmark)
FROM `{DERIVED}.events` AS v
WHERE v.is_first_event
UNION ALL
SELECT 'F', 'total', f.procedure_group, COUNT(*)
FROM `{DERIVED}.events` AS v
JOIN `{DERIVED}.features` AS f
  ON f.episode_id = v.episode_id
WHERE v.is_first_event AND v.has_computable_landmark
GROUP BY f.procedure_group
ORDER BY stage_letter, part_slug, group_slug
""")


def structurally_deleted_event_timing_sql() -> str:
    """First events by post-discharge day, with the rung 18 subset and its own assertion.

    ANALYSIS-PLAN 4.3 obliges the TIMING of the deleted events to be reported, not merely their
    number, because the deleted events are the earliest ones and earliest is a proxy for most
    severe.  The frame therefore carries the whole first-event day distribution and the
    structurally deleted subset within it, so a reader sees what share of the earliest days went.

    The last column is the plan's six-row derivation checked rather than transcribed: the
    definitional flag must equal `event_post_discharge_day <= 4`, on every first event.  A
    non-zero total there is a stop condition, and it is the check that catches a document
    somewhere still saying day 1 to 3.
    """
    return _sql("""
-- @columns: event_post_discharge_day, n_events, n_structurally_uncomputable, n_data_uncomputable, n_computable, n_flag_disagrees_with_derived_range
SELECT
  v.event_post_discharge_day AS event_post_discharge_day,
  COUNT(*)                   AS n_events,
  COUNTIF(v.structurally_uncomputable_landmark) AS n_structurally_uncomputable,
  COUNTIF(NOT v.structurally_uncomputable_landmark
          AND NOT v.has_computable_landmark)    AS n_data_uncomputable,
  COUNTIF(v.has_computable_landmark)            AS n_computable,
  COUNTIF(v.structurally_uncomputable_landmark
          != (v.event_post_discharge_day <= <<STRUCTURAL_DELETION_LAST_DAY>>))
                                                AS n_flag_disagrees_with_derived_range
FROM `{DERIVED}.events` AS v
WHERE v.is_first_event
GROUP BY event_post_discharge_day
ORDER BY event_post_discharge_day
""")


def landmark_panel_sql() -> str:
    """The full-cohort day-indexed landmark panel, aggregated by post-discharge day.

    ANALYSIS-PLAN 4.4 fix 3.  This is the direct evidence for or against the collider concern,
    and the plan is explicit that it is computed HERE and not at the sampled risk sets: risk-set
    membership is the output of the sampling rules of 4.5 and the matching rules of 4.7, and
    both select on the very variable the comparison is about, so a with-versus-without
    comparison taken there compares windows that already survived the selection the comparison
    exists to expose.  The other available surface, first events among episodes that had one,
    conditions on the outcome.  Neither is fit for the purpose and the panel exists because
    neither is.

    The three day classes below PARTITION the panel and are returned as three columns.  The
    computable and data-uncomputable columns are the two sides of the comparison; the
    definitional column is the exclusion, and it is here so that a reader can see it is not in
    the comparison.  ITS COUNT IS NEVER ADDED TO THE DATA COLUMN.
    """
    return _sql("""
-- @columns: post_discharge_day, n_episode_days, n_computable_days, n_data_uncomputable_days, n_definitional_days, n_event_days, n_event_days_computable, n_event_days_data_uncomputable, n_event_days_definitional, n_weight_input_available, n_landmark_before_day_one, n_wearable_lookback_short
SELECT
  l.post_discharge_day AS post_discharge_day,
  COUNT(*)             AS n_episode_days,
  COUNTIF(l.has_computable_landmark) AS n_computable_days,
  COUNTIF(NOT l.has_computable_landmark
          AND NOT l.structurally_uncomputable_landmark) AS n_data_uncomputable_days,
  COUNTIF(l.structurally_uncomputable_landmark)         AS n_definitional_days,
  COUNTIF(l.is_first_event_day)                         AS n_event_days,
  COUNTIF(l.is_first_event_day AND l.has_computable_landmark) AS n_event_days_computable,
  COUNTIF(l.is_first_event_day AND NOT l.has_computable_landmark
          AND NOT l.structurally_uncomputable_landmark) AS n_event_days_data_uncomputable,
  COUNTIF(l.is_first_event_day
          AND l.structurally_uncomputable_landmark)     AS n_event_days_definitional,
  COUNTIF(l.landmark_weight_input_available)            AS n_weight_input_available,
  COUNTIF(l.landmark_before_post_discharge_day_one)     AS n_landmark_before_day_one,
  COUNTIF(l.n_days_behind_landmark_on_wearable_grid < 7) AS n_wearable_lookback_short
FROM `{DERIVED}.landmark_daily` AS l
WHERE NOT l.is_censored
GROUP BY post_discharge_day
ORDER BY post_discharge_day
""")


def matched_set_sizes_sql() -> str:
    """The distribution of controls per case, straight off the STROBE companion ledger.

    Read from `ledger_matched_sets` rather than recounted from `risk_sets`, because the ledger
    is what the supplement prints and a second count here could disagree with the printed one.
    Zero rows is a legitimate answer: at the lowest tiers Arm A produced no sets and the table
    is created empty on purpose, since a table present and empty and a table absent are
    different claims and only one of them is checkable.
    """
    return _sql("""
-- @columns: set_size, n_sets, n_cases
SELECT
  m.set_size AS set_size,
  m.n_sets   AS n_sets,
  m.n_cases  AS n_cases
FROM `{DERIVED}.ledger_matched_sets` AS m
ORDER BY set_size
""")


def event_centered_curve_sql() -> str:
    """The tier 3 visualization: normalized steps and wear fraction around the matched day.

    ANALYSIS-PLAN 4.8, tier 3: median baseline-normalized steps from day E minus 14 through day
    E plus 7 for cases against post-discharge-day matched controls, with the wear fraction over
    the same window.  Cases and controls are both taken from `risk_sets`, so the controls are
    the ones the matching actually drew and the two curves sit on the same time origin.

    IT CARRIES THE STRUCTURAL FILTER, AND THAT WAS ARGUED RATHER THAN ASSUMED.  ANALYSIS-PLAN
    4.4 says a member whose landmark window holds fewer than 2 post-discharge days is outside
    the co-primary exposure "on every surface", and it enumerates them: the conditional model
    of 4.5, the complementary discrete-time model of 4.6, the `landmark_daily` panel of fix 3,
    and "the `risk_sets` table that `pipeline/build_all.sql` builds and both models read".  A
    reading that treats this query as a display exhibit outside that enumeration is available
    and was taken once: the curve plots activity around a matched day and estimates nothing, so
    a member with no exposure window still has a wear trace worth drawing.  It is rejected
    here.  The plot's whole purpose is to show, in a picture, the deterioration the exposure
    measures, and drawing it over a population the exposure model dropped means the figure and
    the estimate beside it answer questions about two different sets of people.  A reviewer
    asks which population the curve is drawn over, and the honest answer has to be the same
    one as the model's or the paper cannot answer at all.  The controls this admits are also
    exactly the ones 4.4 warns about: the earliest ones, which by the argument of 4.3 are a
    proxy for the sickest, so an unfiltered curve is not merely a different population but a
    differently selected one, in the direction that matters.

    THE FILTER COSTS A COUNT AND THE COUNT IS PRINTED, which is the rule 4.4 applies to its own
    member-level drop: "Its whole cost is a count, and the count is printed."  The query
    returns the members behind each curve and the members the filter removed, per role, on
    every row, so the exhibit carries its own denominator rather than leaving a reader to
    assume it is the risk set.  They are MEMBER counts and not episode counts, because a member
    is the unit 4.4's own obliged counts use and one episode can be a member of several sets.

    The median is the exact-median function, never an approximate two-quantile expression,
    which returns the UPPER value on an even-length array and would bias every thin day upward.

    A relative day whose contributing episode count is not disclosable is dropped by the
    disclosure step downstream, not here: the query returns the true counts so that the floor
    can be applied to a true integer exactly once, at the boundary.
    """
    return _sql("""
-- @columns: member_role, relative_day, n_contributing, n_members_in_curve, n_members_dropped_structural, median_normalized_activity, mean_wear_fraction, n_valid_wear_days, n_analyzable_days
WITH member AS (
  SELECT
    r.set_id             AS set_id,
    r.episode_id         AS episode_id,
    r.member_role        AS member_role,
    r.member_matched_day AS member_matched_day
  FROM `{DERIVED}.risk_sets` AS r
  WHERE NOT r.structurally_uncomputable_landmark
),
curve_denominator AS (
  SELECT
    r.member_role AS denominator_role,
    COUNTIF(NOT r.structurally_uncomputable_landmark) AS n_members_in_curve,
    COUNTIF(r.structurally_uncomputable_landmark)     AS n_members_dropped_structural
  FROM `{DERIVED}.risk_sets` AS r
  GROUP BY denominator_role
)
SELECT
  m.member_role AS member_role,
  d.post_discharge_day - m.member_matched_day AS relative_day,
  COUNT(DISTINCT m.episode_id) AS n_contributing,
  ANY_VALUE(n.n_members_in_curve)           AS n_members_in_curve,
  ANY_VALUE(n.n_members_dropped_structural) AS n_members_dropped_structural,
  `{DERIVED}.exact_median`(ARRAY_AGG(d.normalized_activity IGNORE NULLS))
                               AS median_normalized_activity,
  AVG(d.wear_minutes / <<MINUTES_PER_DAY>>) AS mean_wear_fraction,
  COUNTIF(d.valid_wear)        AS n_valid_wear_days,
  COUNTIF(d.is_analyzable)     AS n_analyzable_days
FROM member AS m
JOIN `{DERIVED}.drd_daily` AS d
  ON d.episode_id = m.episode_id
 AND d.post_discharge_day BETWEEN m.member_matched_day - <<EVENT_CENTERED_FIRST_OFFSET>>
                              AND m.member_matched_day + <<EVENT_CENTERED_LAST_OFFSET>>
JOIN curve_denominator AS n
  ON n.denominator_role = m.member_role
GROUP BY member_role, relative_day
ORDER BY member_role, relative_day
""")


def risk_set_model_frame_sql() -> str:
    """The conditional-logistic model frame: one row per matched-set member, no identifiers.

    THIS IS PARTICIPANT-LEVEL AND IT IS FITTED, NEVER RETURNED AND NEVER PRINTED.  It carries
    dense integer surrogates for person and matched set instead of the identifiers themselves,
    because clustering on a person needs a grouping key and not a person identifier, and an
    episode identifier is a person identifier with a date in it.

    Three quantities are computed here rather than read off `risk_sets`, and each is computed
    for CONTROLS as well as cases, which is why `events` cannot supply them: the 7-day
    reference median behind the local step deterioration feature, the landmark weight input at
    the member's own matched day, and the member's own covariates.  The window rules are the
    plan's own, applied at the member's own landmark rather than at an event date.

    `n_valid_days_in_window` is read from `risk_sets` and the proximal median is read from
    `risk_sets.r72`, so the exposure is not recomputed anywhere in this module.  The reference
    median is new, and the plan defines it only as a ratio to the proximal median, so its own
    valid-day count travels with it and a reference built on fewer than the minimum valid days
    yields a null feature rather than a number resting on one day.

    THE STRUCTURAL FLAG IS SELECTED HERE, NOT DERIVED HERE, AND IT IS NOT OPTIONAL.
    `risk_sets` carries `n_eligible_days_in_window`, `has_computable_landmark` and
    `structurally_uncomputable_landmark` under the same names and the same meanings they carry
    in `events` and `landmark_daily`, and its `no_computable_step_signal` is the DATA condition
    and only the data condition.  The day-of-week relaxation of ANALYSIS-PLAN 4.7 can draw a
    CONTROL at post-discharge day 3 or 4, whose window holds fewer than 2 post-discharge days
    and which therefore has no exposure window at all; such a member cannot leave at rung 18,
    because rung 18 is an EVENT rung, so it is admitted, ranked, drawn under both caps and then
    dropped as a member.  `conditional_design` is where that drop happens and it cannot happen
    without this column, so the column travels into the frame.  `r72` is NULL on exactly those
    members, deliberately: without it a matched-day-4 member would publish a ratio built from
    the single reachable post-discharge day its window touches.
    """
    return _sql(_COVARIATE_HEAD + """,
member AS (
  SELECT
    r.set_id                              AS set_id,
    r.person_id                           AS person_id,
    r.episode_id                          AS episode_id,
    r.member_role                         AS member_role,
    r.is_case                             AS is_case,
    r.case_matched_day                    AS case_matched_day,
    r.member_matched_day                  AS member_matched_day,
    r.member_landmark_post_discharge_day  AS member_landmark_post_discharge_day,
    r.member_landmark_day_of_week         AS member_landmark_day_of_week,
    r.match_rung                          AS match_rung,
    r.set_size                            AS set_size,
    r.n_valid_days_in_window              AS n_valid_days_in_window,
    r.n_eligible_days_in_window           AS n_eligible_days_in_window,
    r.has_computable_landmark             AS has_computable_landmark,
    r.structurally_uncomputable_landmark  AS structurally_uncomputable_landmark,
    r.no_computable_step_signal           AS no_computable_step_signal,
    r.r72                                 AS r72,
    r.wear_fraction                       AS wear_fraction
  FROM `{DERIVED}.risk_sets` AS r
),
reference AS (
  SELECT
    m.set_id     AS set_id,
    m.episode_id AS episode_id,
    `{DERIVED}.exact_median_int`(ARRAY_AGG(d.steps IGNORE NULLS)) AS reference_steps,
    COUNT(*)     AS n_reference_valid_days
  FROM member AS m
  JOIN `{DERIVED}.drd_daily` AS d
    ON d.episode_id = m.episode_id
   AND d.post_discharge_day BETWEEN m.member_matched_day - <<REFERENCE_WINDOW_FIRST_OFFSET>>
                                AND m.member_matched_day - <<REFERENCE_WINDOW_LAST_OFFSET>>
   AND d.valid_wear
   AND d.steps IS NOT NULL
  GROUP BY set_id, episode_id
),
weight_input AS (
  SELECT
    m.set_id     AS set_id,
    m.episode_id AS episode_id,
    l.landmark_lagged_wear_fraction          AS landmark_lagged_wear_fraction,
    l.landmark_weight_input_available        AS landmark_weight_input_available,
    l.landmark_before_post_discharge_day_one AS landmark_before_post_discharge_day_one,
    l.n_valid_days_in_window                 AS panel_valid_days_in_window,
    l.n_days_behind_landmark_on_wearable_grid AS n_days_behind_landmark_on_wearable_grid
  FROM member AS m
  JOIN `{DERIVED}.landmark_daily` AS l
    ON l.episode_id = m.episode_id
   AND l.post_discharge_day = m.member_matched_day
)
-- @columns: set_index, cluster_index, is_case, case_matched_day, member_matched_day, member_landmark_post_discharge_day, member_landmark_day_of_week, is_weekend_landmark, match_rung, set_size, n_valid_days_in_window, n_eligible_days_in_window, has_computable_landmark, structurally_uncomputable_landmark, no_computable_step_signal, r72, wear_fraction, reference_ratio, n_reference_valid_days, landmark_lagged_wear_fraction, landmark_weight_input_available, landmark_before_post_discharge_day_one, panel_valid_days_in_window, n_days_behind_landmark_on_wearable_grid, age_at_index, sex_at_birth, bmi_imputed, bmi_missing, charlson_ordinal, los_days, index_year, covid_era, device_family, baseline_steps, n_valid_baseline_days, procedure_class, region
SELECT
  DENSE_RANK() OVER (ORDER BY m.set_id)    AS set_index,
  DENSE_RANK() OVER (ORDER BY m.person_id) AS cluster_index,
  m.is_case                                AS is_case,
  m.case_matched_day                       AS case_matched_day,
  m.member_matched_day                     AS member_matched_day,
  m.member_landmark_post_discharge_day     AS member_landmark_post_discharge_day,
  m.member_landmark_day_of_week            AS member_landmark_day_of_week,
  m.member_landmark_day_of_week IN (1, 7)  AS is_weekend_landmark,
  m.match_rung                             AS match_rung,
  m.set_size                               AS set_size,
  m.n_valid_days_in_window                 AS n_valid_days_in_window,
  m.n_eligible_days_in_window              AS n_eligible_days_in_window,
  m.has_computable_landmark                AS has_computable_landmark,
  m.structurally_uncomputable_landmark     AS structurally_uncomputable_landmark,
  m.no_computable_step_signal              AS no_computable_step_signal,
  m.r72                                    AS r72,
  m.wear_fraction                          AS wear_fraction,
  IF(rf.n_reference_valid_days >= <<LANDMARK_MIN_VALID_DAYS>>,
     SAFE_DIVIDE(rf.reference_steps, c.baseline_steps), NULL) AS reference_ratio,
  IFNULL(rf.n_reference_valid_days, 0)     AS n_reference_valid_days,
  wi.landmark_lagged_wear_fraction         AS landmark_lagged_wear_fraction,
  wi.landmark_weight_input_available       AS landmark_weight_input_available,
  wi.landmark_before_post_discharge_day_one AS landmark_before_post_discharge_day_one,
  wi.panel_valid_days_in_window            AS panel_valid_days_in_window,
  wi.n_days_behind_landmark_on_wearable_grid AS n_days_behind_landmark_on_wearable_grid,
  c.age_at_index                           AS age_at_index,
  c.sex_at_birth                           AS sex_at_birth,
  c.bmi_imputed                            AS bmi_imputed,
  c.bmi_missing                            AS bmi_missing,
  c.charlson_ordinal                       AS charlson_ordinal,
  c.los_days                               AS los_days,
  c.index_year                             AS index_year,
  c.covid_era                              AS covid_era,
  c.device_family                          AS device_family,
  c.baseline_steps                         AS baseline_steps,
  c.n_valid_baseline_days                  AS n_valid_baseline_days,
  c.procedure_class                        AS procedure_class,
  c.region                                 AS region
FROM member AS m
JOIN cohort AS c
  ON c.episode_id = m.episode_id
LEFT JOIN reference AS rf
  ON rf.set_id = m.set_id AND rf.episode_id = m.episode_id
LEFT JOIN weight_input AS wi
  ON wi.set_id = m.set_id AND wi.episode_id = m.episode_id
ORDER BY set_index, is_case DESC, cluster_index
""")


def negative_control_frame_sql() -> str:
    """The same members, with the exposure read from the remote window instead.

    ANALYSIS-PLAN 4.8: repeat the primary association using the window 14 to 8 days before the
    event, among events occurring after post-discharge day 15.  A signal there, remote from the
    event, argues that the proximal finding reflects a chronic gradient rather than a proximal
    deterioration, which is the whole purpose of a negative control.

    The day restriction is applied to the CASE's matched day, so a whole set enters or does not,
    and the plan's "at least 2 valid days" rule carries over unchanged: a remote window resting
    on one day is not a weaker version of the exposure, it is a different quantity.

    THE STRUCTURAL FLAG TRAVELS HERE TOO, AND IT IS EXPECTED TO BE FALSE ON EVERY ROW.  A
    member carrying it is outside the co-primary exposure "on every surface" (ANALYSIS-PLAN
    4.4), and this fit is one of those surfaces, so `conditional_design` applies the same drop
    to this frame as to the primary.  Here it should never bite: the relaxation of 4.7 moves a
    control at most 2 days below its case, this frame admits only cases past post-discharge day
    15, and a member is structural only at a matched day of 4 or less.  Selecting the column
    anyway is what makes that a checkable no-op instead of an argument, and it is what stops
    the filter from being conditional on which frame it was handed.
    """
    return _sql("""
-- @columns: set_index, cluster_index, is_case, case_matched_day, member_matched_day, structurally_uncomputable_landmark, negative_control_ratio, n_negative_control_valid_days, no_computable_negative_control
WITH member AS (
  SELECT
    r.set_id             AS set_id,
    r.person_id          AS person_id,
    r.episode_id         AS episode_id,
    r.is_case            AS is_case,
    r.case_matched_day   AS case_matched_day,
    r.member_matched_day AS member_matched_day,
    r.structurally_uncomputable_landmark AS structurally_uncomputable_landmark
  FROM `{DERIVED}.risk_sets` AS r
  WHERE r.case_matched_day >= <<NEGATIVE_CONTROL_MIN_EVENT_DAY>>
),
remote AS (
  SELECT
    m.set_id     AS set_id,
    m.episode_id AS episode_id,
    `{DERIVED}.exact_median_int`(ARRAY_AGG(d.steps IGNORE NULLS)) AS remote_steps,
    COUNT(*)     AS n_remote_valid_days
  FROM member AS m
  JOIN `{DERIVED}.drd_daily` AS d
    ON d.episode_id = m.episode_id
   AND d.post_discharge_day BETWEEN m.member_matched_day - <<NEGATIVE_CONTROL_FIRST_OFFSET>>
                                AND m.member_matched_day - <<NEGATIVE_CONTROL_LAST_OFFSET>>
   AND d.valid_wear
   AND d.steps IS NOT NULL
  GROUP BY set_id, episode_id
)
SELECT
  DENSE_RANK() OVER (ORDER BY m.set_id)    AS set_index,
  DENSE_RANK() OVER (ORDER BY m.person_id) AS cluster_index,
  m.is_case                                AS is_case,
  m.case_matched_day                       AS case_matched_day,
  m.member_matched_day                     AS member_matched_day,
  m.structurally_uncomputable_landmark     AS structurally_uncomputable_landmark,
  IF(rm.n_remote_valid_days >= <<LANDMARK_MIN_VALID_DAYS>>,
     SAFE_DIVIDE(rm.remote_steps, f.baseline_steps), NULL) AS negative_control_ratio,
  IFNULL(rm.n_remote_valid_days, 0)        AS n_negative_control_valid_days,
  IFNULL(rm.n_remote_valid_days, 0) < <<LANDMARK_MIN_VALID_DAYS>>
                                           AS no_computable_negative_control
FROM member AS m
JOIN `{DERIVED}.features` AS f
  ON f.episode_id = m.episode_id
LEFT JOIN remote AS rm
  ON rm.set_id = m.set_id AND rm.episode_id = m.episode_id
ORDER BY set_index, is_case DESC, cluster_index
""")


def discrete_time_panel_sql() -> str:
    """The complementary full-cohort discrete-time panel, for ABSOLUTE risks only.

    ANALYSIS-PLAN 4.6: absolute risks at clinically representative ratios come from a
    complementary full-cohort discrete-time model, a pooled logistic regression on person-days
    with the post-discharge-day spline and person-clustered inference, NEVER from the
    conditional model, whose matched-set intercepts are conditioned out and which therefore has
    no intercept to translate into a risk at all.

    It is a proper time-to-first-event panel.  Follow-up ends at the earliest of the first
    acute-care encounter and the episode's own censor day (4.1), so every day after an
    episode's first event is dropped rather than contributing a second outcome.

    STRUCTURALLY UNCOMPUTABLE DAYS ARE EXCLUDED AND COUNTED SEPARATELY.  Post-discharge days 1
    to 4 have no exposure window at all, and putting them in with the no-computable-signal
    indicator set would merge the definitional condition into the data condition, which is the
    one merge ANALYSIS-PLAN 4.4 forbids by name.  Their count is returned in its own column and
    is never added to the data condition's.

    The proximal window median is computed here, on the day grid, because no derived table
    carries a day-indexed step ratio: `events` carries it at event dates and `risk_sets` at
    sampled landmarks.  It is not a second definition.  It applies the plan's own window and
    the DAG's own exact-median function, and the last column proves it: the valid-day count of
    the window built here must equal the panel's own `n_valid_days_in_window`, on every row,
    and a non-zero total there is a stop condition rather than a rounding difference.
    """
    return _sql(_COVARIATE_HEAD + """,
first_event AS (
  SELECT
    l.episode_id                 AS episode_id,
    MIN(l.post_discharge_day)    AS first_event_day
  FROM `{DERIVED}.landmark_daily` AS l
  WHERE l.is_first_event_day
  GROUP BY episode_id
),
window_steps AS (
  SELECT
    l.episode_id          AS episode_id,
    l.post_discharge_day  AS post_discharge_day,
    `{DERIVED}.exact_median_int`(ARRAY_AGG(d.steps IGNORE NULLS)) AS proximal_steps,
    COUNT(*)              AS n_window_valid_days
  FROM `{DERIVED}.landmark_daily` AS l
  JOIN `{DERIVED}.drd_daily` AS d
    ON d.episode_id = l.episode_id
   AND d.post_discharge_day BETWEEN l.post_discharge_day - <<LANDMARK_WINDOW_FIRST_OFFSET>>
                                AND l.post_discharge_day - <<LANDMARK_WINDOW_LAST_OFFSET>>
   AND d.valid_wear
   AND d.steps IS NOT NULL
  WHERE NOT l.is_censored
  GROUP BY episode_id, post_discharge_day
)
-- @columns: cluster_index, episode_index, post_discharge_day, outcome, r72, no_computable_step_signal, structurally_uncomputable_landmark, n_valid_days_in_window, n_window_valid_days_recomputed, window_disagrees, landmark_lagged_wear_fraction, landmark_weight_input_available, age_at_index, sex_at_birth, bmi_imputed, bmi_missing, charlson_ordinal, los_days, index_year, covid_era, device_family, baseline_steps, procedure_class, region
SELECT
  DENSE_RANK() OVER (ORDER BY l.person_id)  AS cluster_index,
  DENSE_RANK() OVER (ORDER BY l.episode_id) AS episode_index,
  l.post_discharge_day                      AS post_discharge_day,
  CAST(l.is_first_event_day AS INT64)       AS outcome,
  SAFE_DIVIDE(ws.proximal_steps, c.baseline_steps) AS r72,
  l.no_computable_step_signal               AS no_computable_step_signal,
  l.structurally_uncomputable_landmark      AS structurally_uncomputable_landmark,
  l.n_valid_days_in_window                  AS n_valid_days_in_window,
  IFNULL(ws.n_window_valid_days, 0)         AS n_window_valid_days_recomputed,
  CAST(IFNULL(ws.n_window_valid_days, 0) != l.n_valid_days_in_window AS INT64)
                                            AS window_disagrees,
  l.landmark_lagged_wear_fraction           AS landmark_lagged_wear_fraction,
  l.landmark_weight_input_available         AS landmark_weight_input_available,
  c.age_at_index                            AS age_at_index,
  c.sex_at_birth                            AS sex_at_birth,
  c.bmi_imputed                             AS bmi_imputed,
  c.bmi_missing                             AS bmi_missing,
  c.charlson_ordinal                        AS charlson_ordinal,
  c.los_days                                AS los_days,
  c.index_year                              AS index_year,
  c.covid_era                               AS covid_era,
  c.device_family                           AS device_family,
  c.baseline_steps                          AS baseline_steps,
  c.procedure_class                         AS procedure_class,
  c.region                                  AS region
FROM `{DERIVED}.landmark_daily` AS l
JOIN cohort AS c
  ON c.episode_id = l.episode_id
LEFT JOIN first_event AS fe
  ON fe.episode_id = l.episode_id
LEFT JOIN window_steps AS ws
  ON ws.episode_id = l.episode_id AND ws.post_discharge_day = l.post_discharge_day
WHERE NOT l.is_censored
  AND (fe.first_event_day IS NULL OR l.post_discharge_day <= fe.first_event_day)
ORDER BY cluster_index, episode_index, post_discharge_day
""")


def build_sql() -> dict[str, str]:
    """Every query this module can run, keyed by `QUERY_KEYS`.  Text only, no execution.

    Construction is separated from execution so that the self-test can check every emitted
    string on a laptop: the placeholders it carries, the absence of any Controlled Tier table,
    the absence of any data-definition statement, the absence of randomness, and the agreement
    between each query's declared columns and the aliases it actually writes.  It builds ALL of
    them, at every tier, because a query that only exists at the tier that runs it cannot be
    checked at the tier that does not.
    """
    built = {
        "gate ladder": gate_ladder_sql(),
        "structurally deleted event timing": structurally_deleted_event_timing_sql(),
        "landmark panel": landmark_panel_sql(),
        "matched set sizes": matched_set_sizes_sql(),
        "event centered curve": event_centered_curve_sql(),
        "risk set model frame": risk_set_model_frame_sql(),
        "negative control frame": negative_control_frame_sql(),
        "discrete time panel": discrete_time_panel_sql(),
    }
    missing = [key for key in QUERY_KEYS if key not in built]
    extra = [key for key in built if key not in QUERY_KEYS]
    if missing or extra:
        raise GateError(
            f"the built query set and the declared key list disagree. Missing {missing}, "
            f"unexpected {extra}. The cost plan is keyed on the declared list, so a query "
            f"outside it would execute unpriced."
        )
    return {key: built[key] for key in QUERY_KEYS}


def queries_for_tier(tier_index: int) -> tuple[str, ...]:
    """The phase 2 queries this tier permits, in declared order.  Phase 1 is not in here.

    A tier that permits nothing gets an empty tuple and nothing is priced, submitted or billed.
    That is the gate doing its job: at tier 4 the model queries are not merely unreported, they
    never run.
    """
    index = int(tier_index)
    if index not in TIER_INDICES:
        raise GateError(f"tier {tier_index!r} is not one of the four tiers")
    return tuple(key for key in PHASE_TWO_QUERY_KEYS
                 if index in QUERY_PERMITTED_TIERS[key])


# ======================================================================================
# (7) THE TIER DECISION.  This is the module's first job and it is the whole gate.
#
#     IT READS A COUNT AND NOTHING ELSE.  There is no argument to any function below that
#     could carry an estimate, a fitted model, a P value or a plot, and there is deliberately
#     no way to pass one: `tier_for_events` takes an integer.  A module that decided a tier
#     from anything else would have chosen a model after seeing a number, which is the one
#     thing the prespecification discipline exists to prevent.
# ======================================================================================


def _whole(value: Any, what: str) -> int:
    """A count as a Python int, refusing anything that is not a whole finite number.

    Every count in `{DERIVED}` is a TRUE INTEGER (DAG-SCHEMA 6), so a fractional value arriving
    here means a division crept into an aggregate somewhere upstream, and rounding it quietly
    would hide that.  Floor-testing and rounding happen at the boundary, on the value this
    returns, and never before.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise GateError(f"{what} is not a number") from None
    if not np.isfinite(number) or number != int(number):
        raise GateError(f"{what} is not a whole number, so it is not a count")
    if number < 0:
        raise GateError(f"{what} is negative, which is a defect upstream of this module")
    return int(number)


# The four bands, written out rather than derived from the thresholds, so that the printed band
# and the branch that selects it cannot drift.  `events_upper` at tier 4 is the largest count
# still below the tier 3 boundary; `events_upper` at the top tier is null because it is open.
TIER_BANDS: Mapping[int, tuple[int | None, int | None]] = MappingProxyType({
    1: (TIER_1_MIN_EVENTS, None),
    2: (TIER_2_MIN_EVENTS, TIER_1_MIN_EVENTS - 1),
    3: (TIER_3_MIN_EVENTS, TIER_2_MIN_EVENTS - 1),
    4: (None, TIER_3_MIN_EVENTS - 1),
})

TIER_DETERMINED_BY: str = (
    "stage E: unique first acute-care events with a computable proximal step ratio"
)


def tier_for_events(n_events: int) -> dict[str, Any]:
    """The protocol's tier for an event count, and everything the export block needs with it.

    ANALYSIS-PLAN 1.2, boundaries inclusive at the bottom of each band: 100 or more is tier 1,
    50 to 99 tier 2, 20 to 49 tier 3, fewer than 20 tier 4.

    `event_count_printable` is `disclosable(n)` and is NOT a synonym for the lowest tier.  A
    gate of exactly 20 events sits in tier 3, where event-centered association is permitted,
    and simultaneously at the top of the suppressed band, where the count may not be printed:
    the analysis runs and its denominator does not appear.  That is the coincidence
    ANALYSIS-PLAN 1.3 names rather than trips over, and this is where it is implemented.

    A MEASURED ZERO IS PRINTABLE, and that is not an oversight.  `disclosable()` is the single
    arbiter of the floor and it admits a true zero, because a zero discloses nobody.
    EXPORT-CONTRACT 3.7's sentence about counts of 20 or fewer is written for the non-zero
    case; deferring to the arbiter here is what keeps a bare 20 out of a comparison anywhere in
    this module.  A gate of zero events prints "0" and still lands in the lowest tier.
    """
    n = _whole(n_events, "the gate event count")
    if n >= TIER_1_MIN_EVENTS:
        index = 1
    elif n >= TIER_2_MIN_EVENTS:
        index = 2
    elif n >= TIER_3_MIN_EVENTS:
        index = 3
    else:
        index = 4
    lower, upper = TIER_BANDS[index]
    return {
        "index": index,
        "slug": TIER_SLUGS[index],
        "display_label": TIER_LABELS[index],
        "band_display": TIER_BAND_DISPLAY[index],
        "events_lower": lower,
        "events_upper": upper,
        "determined_by": TIER_DETERMINED_BY,
        "event_count_printable": bool(disclosable(n)),
        "permitted_analysis_verbatim": TIER_PERMITTED_ANALYSIS_VERBATIM[index],
        "permitted_claim_verbatim": TIER_PERMITTED_CLAIM_VERBATIM[index],
        "exhibit_set": TIER_EXHIBIT_SET[index],
    }


def tier_record_for_export(tier: Mapping[str, Any]) -> dict[str, Any]:
    """The tier record trimmed to exactly the keys EXPORT-CONTRACT 3.7 declares, in its order.

    `band_display` is this module's own and is printed in the report rather than exported, so
    it is dropped here.  Trimming explicitly, rather than letting the whole record through,
    means a key added for a report cannot silently become part of the bundle.
    """
    return {
        "index": tier["index"],
        "slug": tier["slug"],
        "display_label": tier["display_label"],
        "events_lower": tier["events_lower"],
        "events_upper": tier["events_upper"],
        "determined_by": tier["determined_by"],
        "event_count_printable": tier["event_count_printable"],
        "permitted_analysis_verbatim": tier["permitted_analysis_verbatim"],
        "permitted_claim_verbatim": tier["permitted_claim_verbatim"],
        "exhibit_set": tier["exhibit_set"],
    }


# ======================================================================================
# (8) The refusal ledger.  What the tier did NOT permit, named, so that an absence is a
#     printed row rather than something a reader has to notice.
# ======================================================================================


def refusals_for_tier(tier_index: int) -> list[dict[str, str]]:
    """Every catalogue analysis this tier forbids, in catalogue order, with its reason.

    `permitted_at_tiers` is printed beside each refusal so a reader can see what the analysis
    would have needed, which turns "this was not done" into "this needed 50 events and the
    study had fewer".  The analysis that is refused at every tier prints "no tier", and that is
    the honest rendering of a rule that is not about this cohort's size at all.
    """
    index = int(tier_index)
    if index not in TIER_INDICES:
        raise GateError(f"tier {tier_index!r} is not one of the four tiers")
    out: list[dict[str, str]] = []
    for slug, label, tiers in ANALYSIS_CATALOGUE:
        if index in tiers:
            continue
        if tiers:
            needed = ", ".join(TIER_LABELS[t] for t in sorted(tiers))
        else:
            needed = "no tier"
        out.append({
            "slug": slug,
            "display_label": label,
            "reason": "not_permitted_by_tier",
            "reason_display": SUPPRESSION_REASONS["not_permitted_by_tier"],
            "permitted_at_tiers": needed,
        })
    return out


def permitted_for_tier(tier_index: int) -> list[dict[str, str]]:
    """The complement of the refusal ledger, so that the two together are the whole catalogue."""
    index = int(tier_index)
    if index not in TIER_INDICES:
        raise GateError(f"tier {tier_index!r} is not one of the four tiers")
    return [{"slug": slug, "display_label": label}
            for slug, label, tiers in ANALYSIS_CATALOGUE if index in tiers]


def assert_features_certified(features_result: Mapping[str, Any] | None) -> None:
    """Refuse to run unless `04_features.py` certified the derived tables.

    A feature-validation failure means a derived table does not hold what its contract
    promises: a null read as a zero, a deficit where no day was observed, a matched set whose
    declared control count does not match its rows.  An Arm A estimate fitted on top of one of
    those is a number nobody can defend, and it would be defended anyway once it existed.  So
    the refusal happens before the first query is priced.
    """
    if features_result is None:
        raise GateRefusal(
            "the feature-validation result was not supplied. This module refuses to run "
            "without it: 04_features.py is what certifies that the derived tables hold what "
            "their contract promises, and there is no default for that and must never be one."
        )
    if "features ok" not in features_result:
        raise GateRefusal(
            "the object supplied is not a feature-validation result: it carries no "
            "certification key. Pass the dictionary run_features returned."
        )
    if not features_result["features ok"]:
        reasons = list(features_result.get("halting", []))
        raise GateRefusal(
            "the feature validation did not certify the derived tables, so Arm A does not "
            "run. Nothing was priced, submitted or billed. The halting reasons were: "
            + ("; ".join(reasons) if reasons else "none were recorded, which is itself a defect")
        )


# ======================================================================================
# (9) The numeric core.
#
#     WRITTEN OUT RATHER THAN IMPORTED, and the reason is the plan's own inference rule.
#     ANALYSIS-PLAN 4.5 requires a PERSON-CLUSTERED robust variance on a conditional logistic
#     regression, and the reason it requires one is stated there: conditional logistic
#     regression assumes independent matched sets, and a participant appearing in several sets
#     breaks that assumption.  The sandwich that repairs it is five lines of linear algebra
#     over per-observation scores, and writing it here means the self-test can DEMONSTRATE on
#     synthetic data that the clustered standard error and the naive one differ, which is the
#     only way to show the correction is actually being applied rather than merely named.
#
#     The whole core is plain numpy, deterministic, and free of any adaptive rule that could
#     make an answer depend on the machine it ran on.  A fit either converges within the fixed
#     iteration budget or is reported as not estimable; it is never quietly restarted.
# ======================================================================================

# The two-sided normal quantile at the 95% level, written to full double precision rather than
# computed, so the module needs no additional dependency for one constant.
NORMAL_QUANTILE_95: float = 1.959963984540054

# EXPORT-CONTRACT 2.2.  The en-dash is the ONLY dash a display string may carry besides the
# ASCII hyphen-minus, and it separates an observed range and never a confidence interval.
EN_DASH: str = chr(0x2013)


def _expit(z: np.ndarray) -> np.ndarray:
    """The logistic function, evaluated so that a large negative argument does not overflow."""
    z = np.asarray(z, dtype=float)
    out = np.empty_like(z)
    positive = z >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-z[positive]))
    exponential = np.exp(z[~positive])
    out[~positive] = exponential / (1.0 + exponential)
    return out


def rcs_basis(x: Any, knots: Sequence[float]) -> np.ndarray:
    """Restricted cubic spline basis at FIXED knots.  `k` knots give `k - 1` columns.

    ANALYSIS-PLAN 4.2 and 3.6 both fix their knots a priori and both say why: quantile knots
    would make the basis depend on the observed distribution, and then a sensitivity row would
    differ from the primary in the basis as well as in the thing it varies.  This function
    therefore takes the knots and never computes them.
    """
    t = np.asarray(knots, dtype=float)
    if t.ndim != 1 or t.size < 3:
        raise GateError("a restricted cubic spline needs at least three knots")
    if not np.all(np.diff(t) > 0):
        raise GateError("spline knots must be strictly increasing")
    values = np.asarray(x, dtype=float)
    last, penultimate = t[-1], t[-2]
    scale = (last - t[0]) ** 2
    columns = [values]
    for j in range(t.size - 2):
        term = (
            np.maximum(values - t[j], 0.0) ** 3
            - np.maximum(values - penultimate, 0.0) ** 3 * (last - t[j]) / (last - penultimate)
            + np.maximum(values - last, 0.0) ** 3 * (penultimate - t[j]) / (last - penultimate)
        )
        columns.append(term / scale)
    return np.column_stack(columns)


def _solve_spd(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    """Solve a symmetric system, falling back to the pseudo-inverse on a singular one.

    A singular information matrix means a covariate carries no within-set variation at all,
    which happens for real: a matching factor that the design held constant inside every set is
    conditioned out of the likelihood and has no coefficient to estimate.  The pseudo-inverse
    returns a zero coefficient for such a column rather than raising, and the caller reports
    the column as not estimable.  A ridge is added only to keep the solve numerically stable
    and is far too small to act as a prior.
    """
    stabilized = matrix + RIDGE_EPSILON * np.eye(matrix.shape[0])
    try:
        return np.linalg.solve(stabilized, vector)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(stabilized) @ vector


def _invert_spd(matrix: np.ndarray) -> np.ndarray:
    stabilized = matrix + RIDGE_EPSILON * np.eye(matrix.shape[0])
    try:
        return np.linalg.inv(stabilized)
    except np.linalg.LinAlgError:
        return np.linalg.pinv(stabilized)


def conditional_logit_sets(y: np.ndarray, set_code: np.ndarray) -> np.ndarray:
    """Which matched sets carry information: those holding at least one case and one control.

    A set that is all cases or all controls contributes a constant to the conditional
    likelihood and no information at all.  ANALYSIS-PLAN 4.4 makes this a counted quantity
    rather than a silent drop, because the weighted sensitivity's own rule can empty a set of
    every control and that turns a member-level exclusion into an analysis-level one.
    """
    n_sets = int(set_code.max()) + 1 if set_code.size else 0
    cases = np.bincount(set_code, weights=(y > 0).astype(float), minlength=n_sets)
    total = np.bincount(set_code, minlength=n_sets)
    return (cases > 0) & (cases < total)


def fit_conditional_logit(
    design: np.ndarray,
    outcome: np.ndarray,
    set_code: np.ndarray,
    cluster_code: np.ndarray,
    set_weights: Mapping[int, float] | np.ndarray | None = None,
    refuse_above_ceiling: bool = True,
) -> dict[str, Any]:
    """Conditional logistic regression with a PERSON-CLUSTERED robust variance.

    The likelihood is the standard conditional one for matched sets: for set `s`, the
    contribution is the linear predictor of the case minus the log of the sum of exponentiated
    predictors over the set's members.  Matched-set intercepts are conditioned out, which is
    the whole reason ANALYSIS-PLAN 4.6 takes absolute risks from a separate full-cohort model
    rather than from this one: there is no intercept here to turn into a risk.

    The per-observation score is `(y - p) * x`, where `p` is the within-set probability, and it
    sums to the set's score.  That decomposition is what makes person clustering possible: the
    score contributions of the sets a participant appears in are added together first, and the
    outer product is taken of the person's total.  A naive variance adds the sets' outer
    products separately, which is the assumption of independent matched sets, and it is exactly
    the assumption a participant appearing twice violates.

    No finite-sample scaling is applied to the sandwich.  ANALYSIS-PLAN 4.5 reports a
    person-level cluster bootstrap beside it and takes the bootstrap interval where the two
    disagree, so a scaling factor here would change which of two intervals is quoted without
    changing any evidence.

    THE FIT REFUSES A SEPARATED SOLUTION.  ANALYSIS-PLAN 4.9 fixes `MAX_ABS_COEFFICIENT` on the
    absolute value of every coefficient, and a fit that converges past it raises
    `ModelSeparated` instead of returning.  The refusal is of the WHOLE FIT and not of the one
    coefficient that broke it, because a coefficient at the ceiling means a near-degenerate
    information matrix and no trustworthy standard error anywhere in the fit.

    `refuse_above_ceiling` exists for ONE caller and the plan is the reason it exists.  4.9
    rule 2 says a BOOTSTRAP RESAMPLE above the ceiling is "retained in the resample
    distribution and counted. It is not discarded", because discarding the resamples that ran
    furthest from zero would trim exactly the tail the percentile interval of 3.8 is read from
    and would therefore NARROW a published interval, which is the one thing this rule must
    never do.  The resample path passes `False`, keeps the value, and counts it; `above
    ceiling` is returned either way so the counting needs no second threshold.  Every other
    caller takes the default and is refused.

    `set_weights` carries the observation weights of the ANALYSIS-PLAN 4.4 sensitivity, and
    THE WEIGHT IS ON THE SET, not on the member.  The unit of the conditional likelihood is the
    matched set: one set contributes one term, and a weight on a term is well defined while a
    weight on one member of a term is not.  The set takes its case's own stabilized weight,
    which is the member the set is built around.  The plan specifies the weight and does not
    specify how it aggregates to a set, so this is named here and printed beside the result.
    """
    design = np.asarray(design, dtype=float)
    outcome = np.asarray(outcome, dtype=float)
    set_code = np.asarray(set_code, dtype=np.int64)
    cluster_code = np.asarray(cluster_code, dtype=np.int64)
    if design.ndim != 2:
        raise GateError("the design matrix must be two-dimensional")
    if not (design.shape[0] == outcome.size == set_code.size == cluster_code.size):
        raise GateError("the design, the outcome and the two grouping codes disagree in length")

    # Densify first.  A set code that starts at one, or a resampled code with gaps in it, would
    # otherwise index an array of the wrong length, and the failure would be a wrong answer
    # rather than an exception.
    dense = pd.factorize(set_code, sort=True)[0].astype(np.int64)
    informative = conditional_logit_sets(outcome, dense)
    keep = informative[dense] if informative.size else np.zeros(0, dtype=bool)
    n_sets_dropped = int((~informative).sum()) if informative.size else 0
    design, outcome = design[keep], outcome[keep]
    sets = pd.factorize(set_code[keep], sort=True)[0].astype(np.int64)
    clusters = pd.factorize(cluster_code[keep], sort=True)[0].astype(np.int64)
    n_sets = int(sets.max()) + 1 if sets.size else 0
    n_clusters = int(clusters.max()) + 1 if clusters.size else 0
    n_parameters = design.shape[1]
    if n_sets == 0 or n_parameters == 0:
        raise ModelDidNotConverge(
            "no matched set carries both a case and a control, so the conditional likelihood "
            "is empty and there is nothing to estimate"
        )
    if set_weights is None:
        weight_of_set = np.ones(n_sets)
    else:
        weight_of_set = np.asarray(set_weights, dtype=float)
        if weight_of_set.size != n_sets:
            raise GateError(
                "the set weights and the informative matched sets disagree in length. A weight "
                "vector is indexed by the sets that survived, not by the sets that were built."
            )
        if np.any(~np.isfinite(weight_of_set)) or np.any(weight_of_set < 0):
            raise GateError("a set weight is negative or not finite")
    weight_of_row = weight_of_set[sets]
    # A set normally holds exactly one case.  A person-level bootstrap resample can put two
    # copies of one participant into the same set, so a set can hold several case rows, and the
    # likelihood has to be the one that handles that: Breslow's, which subtracts the set's
    # log-sum-exponentiated predictor ONCE PER CASE.  Written without the multiplier the
    # likelihood is not a likelihood at all in a resample, and it climbs without bound.
    cases_per_set = np.bincount(sets, weights=(outcome > 0).astype(float), minlength=n_sets)
    cases_of_row = cases_per_set[sets]

    def _pieces(beta: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
        """The weighted log-likelihood, its gradient and its information, all at one beta."""
        eta = design @ beta
        offset = np.full(n_sets, -np.inf)
        np.maximum.at(offset, sets, eta)
        exponentiated = np.exp(eta - offset[sets])
        denominator = np.bincount(sets, weights=exponentiated, minlength=n_sets)
        probability = exponentiated / denominator[sets]
        log_likelihood = float(
            (weight_of_row * eta)[outcome > 0].sum()
            - (weight_of_set * cases_per_set * (offset + np.log(denominator))).sum())
        residual = (outcome - cases_of_row * probability) * weight_of_row
        gradient = design.T @ residual
        means = np.zeros((n_sets, n_parameters))
        np.add.at(means, sets, design * probability[:, None])
        information = (
            design.T @ (design * (probability * cases_of_row * weight_of_row)[:, None])
            - means.T @ ((weight_of_set * cases_per_set)[:, None] * means))
        return log_likelihood, gradient, information

    beta = np.zeros(n_parameters)
    log_likelihood, gradient, information = _pieces(beta)
    converged = False
    iterations = 0
    for iterations in range(1, MAX_NEWTON_ITERATIONS + 1):
        direction = _solve_spd(information, gradient)
        if not np.all(np.isfinite(direction)):
            break
        # A DAMPED step, halved a fixed number of times until the likelihood stops falling.
        # The budget is fixed, so it cannot make the answer depend on the machine it ran on.
        # Without it a wide design over few matched sets oscillates and is reported as not
        # estimable when the maximum is simply further away than one full Newton step.
        scale = 1.0
        trial, trial_ll = beta, log_likelihood
        trial_gradient, trial_information = gradient, information
        for _ in range(MAX_STEP_HALVINGS + 1):
            trial = beta + scale * direction
            trial_ll, trial_gradient, trial_information = _pieces(trial)
            if np.isfinite(trial_ll) and trial_ll >= log_likelihood - NEWTON_TOLERANCE:
                break
            scale /= 2.0
        improvement = abs(trial_ll - log_likelihood)
        beta, log_likelihood = trial, trial_ll
        gradient, information = trial_gradient, trial_information
        # Two criteria, either sufficient, and both fixed.  The step criterion is the ordinary
        # one.  The relative log-likelihood criterion is what handles a flat likelihood, which
        # is the ordinary case in a resample of a thin matched design: the likelihood flattens
        # while the coefficient keeps growing, and a step-only rule would call an essentially
        # converged fit a failure and discard the resample.
        #
        # THAT SECOND CRITERION CANNOT STAND ALONE, and the ceiling below is why.  A flat
        # likelihood beside a growing coefficient has two causes and this rule sees one shape
        # for both: a maximum further away than a step can reach, and QUASI-SEPARATION, where
        # there is no maximum to reach.  The criterion is kept, because discarding every thin
        # resample would be its own bias, and it is paired with a bound on the coefficient it
        # is allowed to declare converged.  Neither half is sufficient; both together are.
        if (float(np.max(np.abs(scale * direction))) < NEWTON_TOLERANCE
                or improvement <= NEWTON_TOLERANCE * (abs(log_likelihood) + NEWTON_TOLERANCE)):
            converged = True
            break
    if not converged:
        raise ModelDidNotConverge(
            f"the conditional logistic fit did not converge within {MAX_NEWTON_ITERATIONS} "
            f"iterations, and is reported as not estimable rather than restarted with a "
            f"different rule"
        )

    # THE COEFFICIENT CEILING OF ANALYSIS-PLAN 4.9, on the fitted coefficients.  It sits AFTER
    # the convergence test on purpose: not converging and separating are different facts about
    # a fit and each is reported as itself, under its own reason.  A fit that ran out of budget
    # is not estimable for convergence; a fit that CONVERGED onto a boundary is not estimable
    # for separation, and 4.9 says in as many words that the convergence reason "would have
    # been a false sentence rather than a near-enough one" for the second.
    #
    # THE VALUE IS NOT IN THE MESSAGE.  4.9: the value that tripped the ceiling is not printed,
    # "not as a bound and not in a footnote, because printing it is the clipped number arriving
    # by a second route".  The message names the fit, the coefficient's POSITION and the rule.
    # It does not name the number, and neither does anything downstream of it.
    #
    # `np.max` over `np.abs` also catches a non-finite coefficient, because no comparison
    # against `inf` or `nan` can pass the ceiling.
    largest = float(np.max(np.abs(beta))) if beta.size else 0.0
    above_ceiling = not (largest <= MAX_ABS_COEFFICIENT)
    if above_ceiling and refuse_above_ceiling:
        raise ModelSeparated(
            f"the conditional logistic fit is separated: coefficient "
            f"{int(np.argmax(np.abs(beta)))} converged past the prespecified ceiling of "
            f"{MAX_ABS_COEFFICIENT:g} on the log-odds scale, fixed at ANALYSIS-PLAN 4.9. The "
            f"WHOLE FIT is refused, not that one coefficient, because a coefficient at the "
            f"ceiling means a near-degenerate information matrix and no trustworthy standard "
            f"error anywhere in the fit. No estimate is published, clipped or otherwise, and "
            f"the value that tripped the ceiling is deliberately not reported"
        )

    eta = design @ beta
    offset = np.full(n_sets, -np.inf)
    np.maximum.at(offset, sets, eta)
    exponentiated = np.exp(eta - offset[sets])
    denominator = np.bincount(sets, weights=exponentiated, minlength=n_sets)
    probability = exponentiated / denominator[sets]
    bread = _invert_spd(information)
    scores = design * ((outcome - cases_of_row * probability) * weight_of_row)[:, None]
    by_cluster = np.zeros((n_clusters, n_parameters))
    np.add.at(by_cluster, clusters, scores)
    by_set = np.zeros((n_sets, n_parameters))
    np.add.at(by_set, sets, scores)
    covariance_cluster = bread @ (by_cluster.T @ by_cluster) @ bread
    covariance_set = bread @ (by_set.T @ by_set) @ bread

    return {
        "beta": beta,
        "log likelihood": log_likelihood,
        "iterations": iterations,
        "converged": converged,
        # Whether this fit is above the ceiling of ANALYSIS-PLAN 4.9.  A fit that REFUSED never
        # returns, so on a returned point fit this is always False; it is True only on a
        # resample, which 4.9 rule 2 retains rather than discards, and it is how those are
        # counted.  The VALUE is deliberately absent: 4.9 forbids reporting the coefficient
        # that tripped the ceiling, and a key holding it would be that report by another name.
        "above ceiling": bool(above_ceiling),
        "coefficient ceiling": MAX_ABS_COEFFICIENT,
        "information": information,
        "covariance naive": bread,
        "covariance clustered": covariance_cluster,
        "covariance set robust": covariance_set,
        "se naive": np.sqrt(np.clip(np.diag(bread), 0.0, None)),
        "se clustered": np.sqrt(np.clip(np.diag(covariance_cluster), 0.0, None)),
        "n sets": n_sets,
        "n sets without both roles": n_sets_dropped,
        "n members": int(outcome.size),
        "n clusters": n_clusters,
        "n cases": int((outcome > 0).sum()),
        "weighted": set_weights is not None,
    }


def fit_pooled_logit(
    design: np.ndarray,
    outcome: np.ndarray,
    cluster_code: np.ndarray,
    weights: np.ndarray | None = None,
) -> dict[str, Any]:
    """Pooled (discrete-time) logistic regression with a person-clustered robust variance.

    ANALYSIS-PLAN 4.6: this is the COMPLEMENTARY full-cohort model, and it exists because the
    conditional model has no intercept.  It carries the post-discharge-day spline of 3.6 and
    person-clustered inference, and its fitted probability is a daily hazard, which is what
    makes an absolute risk expressible at all.

    THE CEILING OF ANALYSIS-PLAN 4.9 BINDS THIS FIT TOO.  4.9 names it: the ceiling binds "the
    conditional model of 4.5, each of that model's bootstrap resamples, AND the complementary
    full-cohort discrete-time model of 4.6 from which the absolute risks come".  Stop condition
    11 of section 11 makes applying it "to some fits and not others" a halt in its own right,
    so the intercept is checked with everything else rather than exempted for being an
    intercept.  It has room: a daily hazard of a few events per thousand person-days is a
    baseline log-odds near -6, well inside a ceiling of 10, and an intercept that did reach 10
    would mean a fitted daily risk indistinguishable from 0 or 1, which is separation.
    """
    design = np.asarray(design, dtype=float)
    outcome = np.asarray(outcome, dtype=float)
    cluster_code = np.asarray(cluster_code, dtype=np.int64)
    weight = (np.ones(outcome.size) if weights is None
              else np.asarray(weights, dtype=float))
    if not (design.shape[0] == outcome.size == cluster_code.size == weight.size):
        raise GateError("the design, the outcome, the cluster code and the weights disagree "
                        "in length")
    clusters = pd.factorize(cluster_code, sort=True)[0].astype(np.int64)
    n_clusters = int(clusters.max()) + 1 if clusters.size else 0
    n_parameters = design.shape[1]

    def _pieces(beta: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
        mu = _expit(design @ beta)
        safe = np.clip(mu, FLOAT_TOLERANCE, 1.0 - FLOAT_TOLERANCE)
        log_likelihood = float(np.sum(weight * (outcome * np.log(safe)
                                                + (1.0 - outcome) * np.log(1.0 - safe))))
        gradient = design.T @ (weight * (outcome - mu))
        hessian = design.T @ (design * (weight * mu * (1.0 - mu))[:, None])
        return log_likelihood, gradient, hessian

    beta = np.zeros(n_parameters)
    log_likelihood, gradient, hessian = _pieces(beta)
    converged = False
    iterations = 0
    for iterations in range(1, MAX_NEWTON_ITERATIONS + 1):
        direction = _solve_spd(hessian, gradient)
        if not np.all(np.isfinite(direction)):
            break
        scale = 1.0
        trial, trial_ll = beta, log_likelihood
        trial_gradient, trial_hessian = gradient, hessian
        for _ in range(MAX_STEP_HALVINGS + 1):
            trial = beta + scale * direction
            trial_ll, trial_gradient, trial_hessian = _pieces(trial)
            if np.isfinite(trial_ll) and trial_ll >= log_likelihood - NEWTON_TOLERANCE:
                break
            scale /= 2.0
        improvement = abs(trial_ll - log_likelihood)
        beta, log_likelihood = trial, trial_ll
        gradient, hessian = trial_gradient, trial_hessian
        if (float(np.max(np.abs(scale * direction))) < NEWTON_TOLERANCE
                or improvement <= NEWTON_TOLERANCE * (abs(log_likelihood) + NEWTON_TOLERANCE)):
            converged = True
            break
    if not converged:
        raise ModelDidNotConverge(
            f"the pooled logistic fit did not converge within {MAX_NEWTON_ITERATIONS} "
            f"iterations, and is reported as not estimable rather than restarted"
        )
    # The ceiling of ANALYSIS-PLAN 4.9, on the whole fit, with the value withheld for the
    # reason 4.9 gives.  There is no `refuse_above_ceiling` escape here because there is no
    # caller that needs one: 4.9 rule 2's retention applies to the CONDITIONAL model's
    # resamples, and this model's own interval comes from its clustered sandwich.
    if beta.size and not (float(np.max(np.abs(beta))) <= MAX_ABS_COEFFICIENT):
        raise ModelSeparated(
            f"the pooled logistic fit is separated: coefficient "
            f"{int(np.argmax(np.abs(beta)))} converged past the prespecified ceiling of "
            f"{MAX_ABS_COEFFICIENT:g} on the log-odds scale, fixed at ANALYSIS-PLAN 4.9. The "
            f"whole fit is refused, so the absolute risks that would have come off it are "
            f"absent with a named reason rather than translated from a boundary. The value "
            f"that tripped the ceiling is deliberately not reported"
        )
    mu = _expit(design @ beta)
    bread = _invert_spd(hessian)
    scores = design * (weight * (outcome - mu))[:, None]
    by_cluster = np.zeros((n_clusters, n_parameters))
    np.add.at(by_cluster, clusters, scores)
    covariance_cluster = bread @ (by_cluster.T @ by_cluster) @ bread
    return {
        "beta": beta,
        "fitted": mu,
        "log likelihood": log_likelihood,
        "iterations": iterations,
        "converged": converged,
        "covariance naive": bread,
        "covariance clustered": covariance_cluster,
        "se naive": np.sqrt(np.clip(np.diag(bread), 0.0, None)),
        "se clustered": np.sqrt(np.clip(np.diag(covariance_cluster), 0.0, None)),
        "above ceiling": False,          # a fit above it never returns from here
        "coefficient ceiling": MAX_ABS_COEFFICIENT,
        "n rows": int(outcome.size),
        "n clusters": n_clusters,
        "n events": int(outcome.sum()),
    }


def cluster_bootstrap(
    statistic: Callable[[np.ndarray, np.ndarray], float],
    cluster_code: np.ndarray,
    *,
    n_resamples: int = BOOTSTRAP_RESAMPLES_PRIMARY,
    seed: int = SEED,
) -> dict[str, Any]:
    """A person-level cluster bootstrap, seeded exactly as ANALYSIS-PLAN 3.8 requires.

    THE RESAMPLING UNIT IS THE PERSON, and whole participants are drawn with replacement
    carrying all of their rows.  Resample `b` is seeded `default_rng([SEED, b])`, so any single
    resample can be regenerated on its own without replaying the ones before it, which is what
    makes a disagreement between two sessions traceable to a resample rather than to a machine.

    `statistic` receives the ROW INDICES of one resample and the DRAW ORDINAL of each row, and
    returns one number.  The draw ordinal is not decoration: it makes two copies of one drawn
    participant two DISTINCT clusters, so a resample cannot silently fold them together.  The
    MATCHED SETS keep their own identity across a resample, because the conditional likelihood
    is a sum over sets and relabelling a set per draw would split every set into single members
    and leave the likelihood empty.  A set whose case's participant was not drawn simply loses
    its case and drops out, which is counted.  Passing
    indices rather than a frame keeps the resampling here and the model there, so a caller can
    bootstrap a conditional fit, a pooled fit or a standardized risk with the same machinery
    and the same seed convention.  A resample whose model fails to converge returns a
    non-finite value; it is discarded and COUNTED, and the count is reported, because
    ANALYSIS-PLAN 3.8 makes more than a quarter of them failing a descent trigger rather than
    a footnote.
    """
    clusters = pd.factorize(np.asarray(cluster_code), sort=True)[0].astype(np.int64)
    n_clusters = int(clusters.max()) + 1 if clusters.size else 0
    if n_clusters == 0:
        raise GateError("a cluster bootstrap needs at least one cluster")
    rows_by_cluster = [np.flatnonzero(clusters == c) for c in range(n_clusters)]

    values: list[float] = []
    n_failed = 0
    for b in range(1, int(n_resamples) + 1):
        generator = np.random.default_rng([int(seed), b])
        drawn = generator.integers(0, n_clusters, size=n_clusters)
        parts = [rows_by_cluster[c] for c in drawn]
        indices = np.concatenate(parts) if parts else np.zeros(0, dtype=np.int64)
        ordinal = np.repeat(np.arange(len(parts)), [len(part) for part in parts]) \
            if parts else np.zeros(0, dtype=np.int64)
        try:
            value = float(statistic(indices, ordinal))
        except (ModelDidNotConverge, np.linalg.LinAlgError, FloatingPointError, ValueError):
            value = float("nan")
        if np.isfinite(value):
            values.append(value)
        else:
            n_failed += 1
    array = np.asarray(values, dtype=float)
    share_failed = n_failed / float(n_resamples) if n_resamples else 0.0
    if array.size == 0:
        return {"lower": float("nan"), "upper": float("nan"), "n resamples": int(n_resamples),
                "n failed": n_failed, "share failed": share_failed,
                "descent trigger": True, "values": array}
    return {
        "lower": float(np.percentile(array, BOOTSTRAP_LOWER_PERCENTILE)),
        "upper": float(np.percentile(array, BOOTSTRAP_UPPER_PERCENTILE)),
        "n resamples": int(n_resamples),
        "n failed": n_failed,
        "share failed": share_failed,
        "descent trigger": share_failed > BOOTSTRAP_MAX_FAILURE_SHARE,
        "values": array,
    }


def resample_group_codes(codes: np.ndarray, indices: np.ndarray,
                        ordinal: np.ndarray) -> np.ndarray:
    """Relabel a CLUSTER code so that two copies of one drawn cluster stay two distinct groups.

    It is deliberately not applied to the matched set code.  A matched set is the unit of the
    conditional likelihood, and relabelling it per draw would leave every set holding a single
    member and the likelihood with nothing to condition on.
    """
    codes = np.asarray(codes)[np.asarray(indices)]
    ordinal = np.asarray(ordinal)
    span = int(ordinal.max()) + 1 if ordinal.size else 1
    return codes.astype(np.int64) * span + ordinal.astype(np.int64)


# --------------------------------------------------------------------------------------
# The performance panel of ANALYSIS-PLAN 4.8, tier 1 only.  Every metric below is computed from
# a vector of predicted daily risks and the observed outcome, so none of them can be produced
# without the fitted model, and the module refuses to compute any of them at a lower tier by
# never calling this at all.  AUROC is here because the plan requires it to be reported; the
# plan is equally explicit that it is NEVER the headline, and the report prints it last.
# --------------------------------------------------------------------------------------


def _roc_area(predicted: np.ndarray, outcome: np.ndarray) -> float:
    """The area under the receiver operating characteristic, by the rank identity."""
    outcome = np.asarray(outcome, dtype=float)
    positives = outcome > 0
    n_positive, n_negative = int(positives.sum()), int((~positives).sum())
    if n_positive == 0 or n_negative == 0:
        return float("nan")
    ranks = pd.Series(np.asarray(predicted, dtype=float)).rank(method="average").to_numpy()
    return float((ranks[positives].sum() - n_positive * (n_positive + 1) / 2.0)
                 / (n_positive * n_negative))


def _average_precision(predicted: np.ndarray, outcome: np.ndarray) -> float:
    """The area under the precision-recall curve, as the step-wise average precision.

    The plan puts this ahead of the area under the receiver operating characteristic for a
    reason worth keeping in the code: at an event rate of a few per thousand person-days, the
    latter is dominated by the enormous negative class and a useless model still scores well.
    """
    predicted = np.asarray(predicted, dtype=float)
    outcome = np.asarray(outcome, dtype=float) > 0
    if outcome.sum() == 0:
        return float("nan")
    order = np.argsort(-predicted, kind="stable")
    hits = outcome[order].astype(float)
    cumulative_hits = np.cumsum(hits)
    precision = cumulative_hits / np.arange(1, hits.size + 1)
    return float((precision * hits).sum() / hits.sum())


def _threshold_at_sensitivity(predicted: np.ndarray, outcome: np.ndarray,
                              target: float) -> float:
    """The highest threshold whose sensitivity still reaches the target.

    Fixed by the plan at 80% sensitivity, which is a prespecified operating point and not one
    read off the curve after the fact.
    """
    predicted = np.asarray(predicted, dtype=float)
    positives = predicted[np.asarray(outcome, dtype=float) > 0]
    if positives.size == 0:
        return float("nan")
    return float(np.quantile(positives, 1.0 - float(target), method="lower"))


def performance_panel(predicted: np.ndarray, outcome: np.ndarray, *,
                      target_sensitivity: float = ALERT_TARGET_SENSITIVITY) -> dict[str, Any]:
    """Discrimination, calibration, predictive values and alert burden at the fixed threshold."""
    predicted = np.asarray(predicted, dtype=float)
    observed = np.asarray(outcome, dtype=float) > 0
    n_rows = int(observed.size)
    n_events = int(observed.sum())
    threshold = _threshold_at_sensitivity(predicted, observed, target_sensitivity)
    alert = predicted >= threshold if np.isfinite(threshold) else np.zeros(n_rows, dtype=bool)
    true_positive = int((alert & observed).sum())
    false_positive = int((alert & ~observed).sum())
    false_negative = int((~alert & observed).sum())
    true_negative = int((~alert & ~observed).sum())

    def _ratio(numerator: int, denominator: int) -> float:
        return float(numerator) / float(denominator) if denominator else float("nan")

    # Calibration by the standard logistic recalibration of the linear predictor: the intercept
    # is calibration-in-the-large and the slope is the spread of the predictions.
    with np.errstate(divide="ignore", invalid="ignore"):
        clipped = np.clip(predicted, FLOAT_TOLERANCE, 1.0 - FLOAT_TOLERANCE)
        linear_predictor = np.log(clipped / (1.0 - clipped))
    calibration_intercept, calibration_slope = float("nan"), float("nan")
    if n_events > 0 and n_events < n_rows:
        try:
            recalibrated = fit_pooled_logit(
                np.column_stack([np.ones(n_rows), linear_predictor]),
                observed.astype(float),
                np.arange(n_rows),
            )
            calibration_intercept = float(recalibrated["beta"][0])
            calibration_slope = float(recalibrated["beta"][1])
        except ModelDidNotConverge:
            pass
    return {
        "n rows": n_rows,
        "n events": n_events,
        "threshold": threshold,
        "area under the receiver operating characteristic": _roc_area(predicted, observed),
        "area under the precision recall curve": _average_precision(predicted, observed),
        "brier score": float(np.mean((predicted - observed.astype(float)) ** 2))
                       if n_rows else float("nan"),
        "calibration intercept": calibration_intercept,
        "calibration slope": calibration_slope,
        "sensitivity": _ratio(true_positive, true_positive + false_negative),
        "specificity": _ratio(true_negative, true_negative + false_positive),
        "positive predictive value": _ratio(true_positive, true_positive + false_positive),
        "negative predictive value": _ratio(true_negative, true_negative + false_negative),
        "alerts per 100 patient days": _ratio(int(alert.sum()), n_rows) * 100.0
                                       if n_rows else float("nan"),
        "false alerts per detected encounter": _ratio(false_positive, true_positive),
        "number needed to contact": _ratio(true_positive + false_positive, true_positive),
        "n alerts": int(alert.sum()),
        "n true positive": true_positive,
        "n false positive": false_positive,
    }


# ======================================================================================
# (10) The design matrices.
#
#      Written once, in one place, so that the unadjusted fit, the adjusted fit, the weighted
#      sensitivity and the negative control cannot silently carry different exposures.  The
#      exposure basis is CENTERED at the reference ratio, which is what makes the co-primary
#      coefficient interpretable: with the basis centered, the no-computable-signal coefficient
#      is the log odds against a window that WAS computable and sat at the reference ratio,
#      rather than against the mathematical fiction of a window at a ratio of zero.
# ======================================================================================

# The levels each categorical covariate takes, and the level each is contrasted against.  Fixed
# vocabularies from DAG-SCHEMA 8.10, so a level that happens to be absent in one fit does not
# renumber the columns of another.
SEX_LEVELS: tuple[str, ...] = ("male", "female", "other_or_unknown")
SEX_REFERENCE: str = "male"
CHARLSON_LEVELS: tuple[str, ...] = ("0", "1", "2", "3_or_more")
CHARLSON_REFERENCE: str = "0"
DEVICE_FALLBACK_LEVEL: str = "other_or_unknown"
# ANALYSIS-PLAN 3.6 rule 5: any device level whose episode count is not disclosable folds into
# "other or unknown" BEFORE modelling.  The folding runs on a COUNT, never on an estimate, and
# `disclosable` is the arbiter, so no threshold is written here.
BASELINE_STEPS_SCALE: float = 1000.0             # a coefficient per thousand steps reads


def exposure_columns(ratio: Any, no_signal: Any) -> tuple[np.ndarray, list[str]]:
    """The co-primary exposure of ANALYSIS-PLAN 4.4, as a design block and its column names.

    `logit(risk) = alpha + beta_N * N + f(R) * (1 - N) + covariates`, with `f` the restricted
    cubic spline of 4.2 at knots fixed at 0.4, 0.7 and 1.0, centered at the reference ratio.

    A window with no computable signal carries `N = 1` and contributes ZERO through the spline
    block, which is why its missing ratio can be filled with anything finite: it is multiplied
    by `(1 - N)` and never read.  It is filled with the reference ratio rather than with zero
    so that a reader inspecting the matrix sees a neutral value rather than a value that looks
    like profound inactivity.
    """
    signal = np.asarray(pd.to_numeric(pd.Series(no_signal).astype(float),
                                      errors="coerce").fillna(1.0), dtype=float)
    if not np.all(np.isin(signal, (0.0, 1.0))):
        raise GateError("the no-computable-step-signal indicator is not a zero or a one")
    values = pd.to_numeric(pd.Series(ratio), errors="coerce").to_numpy(dtype=float)
    filled = np.where(np.isfinite(values), values, STEP_RATIO_REFERENCE)
    # A computable window with a missing ratio is a contradiction the DAG cannot produce, and
    # letting it through would put the reference ratio into a member that carries the exposure.
    if np.any((signal == 0.0) & ~np.isfinite(values)):
        raise GateError(
            "a member is marked as carrying a computable step signal and has no ratio. The two "
            "come from the same derived row, so a disagreement is a defect upstream, not a "
            "missing value to be filled."
        )
    basis = rcs_basis(filled, STEP_RATIO_KNOTS)
    centre = rcs_basis(np.array([STEP_RATIO_REFERENCE]), STEP_RATIO_KNOTS)[0]
    block = (basis - centre) * (1.0 - signal)[:, None]
    names = ["proximal ratio spline term 1"]
    names += [f"proximal ratio spline term {j + 2}" for j in range(block.shape[1] - 1)]
    return np.column_stack([signal, block]), ["no computable step signal"] + names


def step_ratio_contrast_vector(n_columns: int, offset: int) -> np.ndarray:
    """The contrast that reads "per 20-percentage-point lower proximal step ratio" off a fit.

    A spline effect is not constant, so a per-decrement effect is a CONTRAST BETWEEN TWO
    RATIOS and the pair has to be named.  The pair is fixed in the locked constants: the
    boundary of the plan's own top display category, and one decrement below it.  The vector
    below is zero everywhere except in the spline block, where it is the basis at the lower
    ratio minus the basis at the reference.  Both anchors sit in computable windows, so the
    `(1 - N)` multiplier is one at both and cancels.
    """
    lower = rcs_basis(np.array([STEP_RATIO_CONTRAST]), STEP_RATIO_KNOTS)[0]
    upper = rcs_basis(np.array([STEP_RATIO_REFERENCE]), STEP_RATIO_KNOTS)[0]
    contrast = np.zeros(int(n_columns))
    contrast[offset + 1: offset + 1 + lower.size] = lower - upper
    return contrast


def no_signal_contrast_vector(n_columns: int, offset: int) -> np.ndarray:
    """The contrast for the co-primary exposure: no computable signal against the reference."""
    contrast = np.zeros(int(n_columns))
    contrast[offset] = 1.0
    return contrast


def _indicator_columns(values: Any, levels: Sequence[str], reference: str,
                       label: str) -> tuple[np.ndarray, list[str]]:
    """Dummy columns for a fixed level vocabulary, against a fixed reference level."""
    series = pd.Series(values).astype(str)
    unknown = sorted(set(series) - set(levels))
    if unknown:
        raise GateError(
            f"{label} carries level(s) {unknown} outside its fixed vocabulary. A level that "
            f"appears at run time is a level nobody prespecified."
        )
    columns, names = [], []
    for level in levels:
        if level == reference:
            continue
        columns.append((series == level).to_numpy(dtype=float))
        names.append(f"{label}, {level.replace('_', ' ')}")
    if not columns:
        return np.zeros((len(series), 0)), []
    return np.column_stack(columns), names


def fold_device_levels(values: Any) -> pd.Series:
    """ANALYSIS-PLAN 3.6 rule 5: fold any device level whose episode count is not disclosable.

    The fold runs on a count and the arbiter is `disclosable`, so this function contains no
    threshold of its own.  It happens once, before modelling, and it cannot depend on any
    estimate because no estimate exists when it runs.
    """
    series = pd.Series(values).astype(str)
    counts = series.value_counts()
    keep = {level for level, n in counts.items() if disclosable(int(n))}
    return series.where(series.isin(keep), DEVICE_FALLBACK_LEVEL)


def covariate_columns(frame: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    """The locked Arm A covariate set of ANALYSIS-PLAN 4.6, as a design block.

    Age, sex assigned at birth, baseline body mass index, BASELINE STEPS, comorbidity burden,
    index length of stay, calendar year and device class.  Baseline steps is a covariate here
    and is deliberately not one in Arm B: the exposure is a ratio whose denominator is the
    baseline, and adjusting for the denominator of an exposure is standard rather than
    circular.  The two modules therefore disagree on this covariate on purpose.
    """
    blocks: list[np.ndarray] = []
    names: list[str] = []

    age = pd.to_numeric(frame["age_at_index"], errors="coerce")
    age = age.fillna(age.median() if age.notna().any() else AGE_SPLINE_KNOTS[1])
    age_basis = rcs_basis(age.to_numpy(dtype=float), AGE_SPLINE_KNOTS)
    blocks.append(age_basis)
    names += [f"age spline term {j + 1}" for j in range(age_basis.shape[1])]

    sex_block, sex_names = _indicator_columns(frame["sex_at_birth"], SEX_LEVELS,
                                              SEX_REFERENCE, "sex")
    if sex_block.shape[1]:
        blocks.append(sex_block)
        names += sex_names

    bmi = pd.to_numeric(frame["bmi_imputed"], errors="coerce")
    bmi = bmi.fillna(bmi.median() if bmi.notna().any() else 0.0)
    blocks.append(bmi.to_numpy(dtype=float)[:, None])
    names.append("body mass index")
    blocks.append(pd.Series(frame["bmi_missing"]).astype(float).to_numpy()[:, None])
    names.append("body mass index missing")

    charlson_block, charlson_names = _indicator_columns(
        frame["charlson_ordinal"], CHARLSON_LEVELS, CHARLSON_REFERENCE, "comorbidity burden")
    if charlson_block.shape[1]:
        blocks.append(charlson_block)
        names += charlson_names

    los = pd.to_numeric(frame["los_days"], errors="coerce").fillna(0.0).clip(lower=0.0)
    blocks.append(np.log1p(los.to_numpy(dtype=float))[:, None])
    names.append("log of one plus the index length of stay")

    year = pd.to_numeric(frame["index_year"], errors="coerce")
    year = year.fillna(year.median() if year.notna().any() else 0.0)
    blocks.append((year - year.mean()).to_numpy(dtype=float)[:, None])
    names.append("calendar year, centered")
    blocks.append(pd.Series(frame["covid_era"]).astype(float).to_numpy()[:, None])
    names.append("pandemic disruption era")

    device = fold_device_levels(frame["device_family"])
    device_levels = tuple(sorted(set(device) | {DEVICE_FALLBACK_LEVEL}))
    device_block, device_names = _indicator_columns(device, device_levels,
                                                    DEVICE_FALLBACK_LEVEL, "device family")
    if device_block.shape[1]:
        blocks.append(device_block)
        names += device_names

    baseline = pd.to_numeric(frame["baseline_steps"], errors="coerce")
    baseline = baseline.fillna(baseline.median() if baseline.notna().any() else 0.0)
    blocks.append((baseline / BASELINE_STEPS_SCALE).to_numpy(dtype=float)[:, None])
    names.append("baseline steps, per thousand")

    return np.column_stack(blocks), names


# ANALYSIS-PLAN 3.6 fixes the day-of-week reference at Wednesday, an arbitrary fixed choice
# that cannot affect a standardized estimate.  Day of week is 1 for Sunday (DAG-SCHEMA 8.11).
DAY_OF_WEEK_LEVELS: tuple[int, ...] = (1, 2, 3, 4, 5, 6, 7)
DAY_OF_WEEK_REFERENCE: int = 4                   # Wednesday
DAY_OF_WEEK_LABELS: Mapping[int, str] = MappingProxyType({
    1: "Sunday", 2: "Monday", 3: "Tuesday", 4: "Wednesday",
    5: "Thursday", 6: "Friday", 7: "Saturday",
})
WEEKEND_DAYS: tuple[int, ...] = (1, 7)


def day_of_week_columns(frame: pd.DataFrame) -> tuple[np.ndarray, list[str], str]:
    """ANALYSIS-PLAN 4.7 rung 3: the day-of-week fixed effect, and its reduction rule.

    A single day-of-week term carried in the conditional model IS the plan's "fixed effect for
    that set".  Day of week is constant inside every rung 1 set by construction and inside
    every rung 2 set up to the weekday-or-weekend class, so the conditional likelihood
    conditions it out there and estimates it only where it varies, which is exactly the rung 3
    sets.  One column therefore implements a per-set effect without a per-set parameter.

    "Reduced to the weekend indicator when the set is thin" is a rule on a COUNT, so
    `disclosable` is the arbiter and no threshold is written here: the seven-level form is
    carried when the number of relaxation rung 3 sets is disclosable and the weekend indicator
    otherwise.  A cohort with no rung 3 set at all gets no column, because a column with no
    within-set variation anywhere carries no information and only destabilises the solve.
    """
    rungs = pd.to_numeric(frame["match_rung"], errors="coerce")
    relaxed = frame[rungs == MATCH_RUNGS[-1]]
    n_relaxed_sets = int(pd.Series(relaxed["set_index"]).nunique()) if len(relaxed) else 0
    if n_relaxed_sets == 0:
        return np.zeros((len(frame), 0)), [], "none, no relaxed matched set"
    if disclosable(n_relaxed_sets):
        levels = tuple(str(level) for level in DAY_OF_WEEK_LEVELS)
        block, names = _indicator_columns(
            pd.to_numeric(frame["member_landmark_day_of_week"], errors="coerce")
              .fillna(DAY_OF_WEEK_REFERENCE).astype(int).astype(str),
            levels, str(DAY_OF_WEEK_REFERENCE), "landmark day")
        names = [f"landmark day, {DAY_OF_WEEK_LABELS[int(level)]}"
                 for level in DAY_OF_WEEK_LEVELS if level != DAY_OF_WEEK_REFERENCE]
        return block, names, "seven levels, reference Wednesday"
    weekend = pd.Series(frame["is_weekend_landmark"]).astype(float).to_numpy()[:, None]
    return weekend, ["landmark falls at a weekend"], "weekend indicator, the thin-set reduction"


def structural_member_counts(
    frame: pd.DataFrame,
    *,
    structural_column: str = "structurally_uncomputable_landmark",
    no_signal_column: str = "no_computable_step_signal",
) -> dict[str, Any]:
    """The counts ANALYSIS-PLAN 4.4 obliges for the members that carry no exposure window.

    A member whose landmark window holds fewer than 2 POST-DISCHARGE days is the DEFINITIONAL
    condition.  It carries no `N`, it contributes nothing to `beta_N`, and it sits outside the
    co-primary exposure "on every surface", which by name includes the conditional model this
    frame is fitted with.  Every case here is at post-discharge day 5 or later, because the
    cases are read from `events` under attrition rung 18; the day-of-week relaxation of 4.7 can
    still put a CONTROL at post-discharge day 3 or 4, and a sampled control is not an event and
    cannot leave at rung 18.  Such a member is admitted, ranked, drawn under both caps, and
    then DROPPED FROM ITS RISK SET AS A MEMBER AND COUNTED.  That ordering is deliberate
    upstream: refusing the control at the candidate stage instead would make both of the counts
    below structurally zero while looking like a definition.

    TWO COUNTS, AND THE SECOND IS NOT THE FIRST.  4.4's count 2, matched sets that lose EVERY
    control, "turns a member-level exclusion into an analysis-level one and it cannot be
    recovered from" the member count: one set losing three controls and three sets losing one
    each are the same member count and different analyses, because a set with no control
    contributes nothing to a conditional likelihood and leaves it altogether.  So it is counted
    here rather than inferred downstream.

    THE THREE VIOLATIONS ARE STOP CONDITIONS AND NOT REPAIRS.  A case carrying the flag means
    `events` and `risk_sets` disagree about the same window, which `build_all.sql` raises on in
    its own right.  A member carrying the flag AND the no-computable-signal indicator means the
    data condition has swallowed the definitional one, which is the exact contamination 4.4
    forbids: "their counts are never summed".  And the flag disagreeing with the landmark-day
    arithmetic means the frame is internally inconsistent, since a landmark day of 1 or less is
    not a rule of its own but the same condition written in landmark-day terms.  None of the
    three is repaired here, because a repair would hide a defect the DAG has to be rebuilt for.
    """
    if structural_column not in frame.columns:
        raise GateError(
            f"the model frame carries no {structural_column!r} column, so there is nothing to "
            f"read the definitional condition off. ANALYSIS-PLAN 4.4 puts a member whose "
            f"window holds fewer than 2 post-discharge days outside the co-primary exposure on "
            f"every surface, and a frame that cannot express that condition cannot be fitted "
            f"under it. Select the column rather than defaulting it to false: a default would "
            f"be the silent contamination this rule exists to prevent."
        )
    rows = frame.reset_index(drop=True)
    structural = pd.Series(rows[structural_column]).astype(bool)
    is_case = pd.Series(rows["is_case"]).astype(bool)
    sets = pd.Series(rows["set_index"]).astype("int64")

    violations: list[str] = []
    if bool((structural & is_case).any()):
        violations.append(
            "a case in the matched-set model frame carries the definitional condition. Cases "
            "are read from the events table under attrition rung 18, which is exactly that "
            "condition, so this means the events table and the risk-set table disagree about "
            "the same window or one of the two is stale from an earlier build"
        )
    # Checked only where the frame carries the proximal data condition under its own name.
    # The negative control frame does not, and the remote window's data condition is not this
    # one, so an absent column is a check that does not apply rather than a check that passed.
    if no_signal_column in rows.columns:
        both = structural & pd.Series(rows[no_signal_column]).astype(bool)
        if bool(both.any()):
            violations.append(
                "a member carries the definitional condition and the no-computable-step-signal "
                "indicator at once. That indicator is the DATA condition and only the data "
                "condition, and a member carrying both has had an exclusion folded into an "
                "exposure, which is the contamination ANALYSIS-PLAN 4.4 forbids by name"
            )
    if "member_landmark_post_discharge_day" in rows.columns:
        early = (pd.to_numeric(rows["member_landmark_post_discharge_day"], errors="coerce")
                 < MIN_WEIGHTED_LANDMARK_DAY)
        if bool((structural != early).any()):
            violations.append(
                "the definitional flag disagrees with the landmark day it is arithmetic on. A "
                "landmark day of 1 or less is not a rule of its own: it is the same condition "
                "written in landmark-day terms, so a row where the two differ means the "
                "derived table no longer counts the window it says it counts"
            )

    controls = ~is_case
    controls_per_set = controls.groupby(sets).sum()
    structural_controls_per_set = (controls & structural).groupby(sets).sum()
    lost_every_control = ((controls_per_set > 0)
                          & (structural_controls_per_set == controls_per_set))
    return {
        "n structurally uncomputable members dropped": int(structural.sum()),
        "n structurally uncomputable cases": int((structural & is_case).sum()),
        "n structurally uncomputable controls": int((structural & controls).sum()),
        "n sets losing every control": int(lost_every_control.sum()),
        "n sets losing their case": int((structural & is_case).groupby(sets).any().sum()),
        "n members": int(len(rows)),
        "n sets": int(sets.nunique()),
        "violations": violations,
    }


def conditional_design(frame: pd.DataFrame, *, adjusted: bool,
                       ratio_column: str = "r72",
                       no_signal_column: str = "no_computable_step_signal",
                       structural_column: str = "structurally_uncomputable_landmark",
                       ) -> dict[str, Any]:
    """Assemble the conditional model's design, exposure block first.

    The exposure block always occupies the leading columns, so the two contrast vectors can be
    written against a known offset and cannot silently address a covariate after a design
    change.  `adjusted` is the ONLY difference between the tier 3 fit and the tier 2 fit: the
    exposure, the matching repair and the estimand are identical, which is what makes the two
    comparable and is why the plan writes them as one specification with a tier switch.

    STRUCTURALLY UNCOMPUTABLE MEMBERS ARE DROPPED HERE AND COUNTED, exactly as
    `discrete_time_design` drops and counts the structurally uncomputable DAYS of the panel.
    A member whose window holds fewer than 2 post-discharge days has no exposure window at all,
    so it carries no `N` and it is outside the co-primary exposure on this surface as on every
    other.  Its `r72` is NULL by construction upstream, which is what makes the drop safe to
    check rather than safe to assume: without the drop `exposure_columns` sees a member that is
    NOT marked as having no computable signal and has no ratio, and it halts.  That halt is the
    correct behaviour of a guard and the wrong behaviour of an analysis, and the filter is what
    turns it back into a counted exclusion.  THE FRAME IS RETURNED BESIDE THE DESIGN so that
    the outcome, the set code and the cluster code are read off the SAME rows the design was
    built from; reading them off the unfiltered frame would misalign every one of them.
    """
    # `no_signal_column` is NOT forwarded.  The "never summed" rule of ANALYSIS-PLAN 4.4 is
    # about the PROXIMAL landmark's data condition, which is what `no_computable_step_signal`
    # names on every derived surface.  The negative control of 4.8 hands this function a
    # different no-signal column entirely, the remote window's own data condition, and a member
    # may legitimately carry that one for reasons that have nothing to do with the proximal
    # window.  So the counter checks the proximal column by name where the frame has it, and
    # skips the check where it does not, rather than testing whichever column this fit happens
    # to be using as its exposure indicator.
    counts = structural_member_counts(frame, structural_column=structural_column)
    rows = frame.reset_index(drop=True)
    structural = pd.Series(rows[structural_column]).astype(bool)
    kept = rows[~structural].reset_index(drop=True)
    if kept.empty:
        raise ModelDidNotConverge(
            "every member of every matched set is structurally uncomputable, so no member "
            "carries an exposure window and there is nothing to fit. This is reported as not "
            "estimable rather than fitted on the members the exposure is not defined for"
        )
    exposure, exposure_names = exposure_columns(kept[ratio_column], kept[no_signal_column])
    blocks = [exposure]
    names = list(exposure_names)
    day_block, day_names, day_form = day_of_week_columns(kept)
    if day_block.shape[1]:
        blocks.append(day_block)
        names += day_names
    if adjusted:
        covariates, covariate_names = covariate_columns(kept)
        blocks.append(covariates)
        names += covariate_names
    design = np.column_stack(blocks)
    return {
        "frame": kept,
        "design": design,
        "names": names,
        "exposure offset": 0,
        "day of week form": day_form,
        "adjusted": bool(adjusted),
        # ANALYSIS-PLAN 4.4's obliged counts, carried beside the fit.  The second is NOT
        # recoverable from the first, which is why it is here rather than left to arithmetic.
        "n structurally uncomputable members dropped":
            counts["n structurally uncomputable members dropped"],
        "n sets losing every control": counts["n sets losing every control"],
        "n sets losing their case": counts["n sets losing their case"],
        "structural violations": counts["violations"],
    }


def estimate_contrast(fit: Mapping[str, Any], contrast: np.ndarray) -> dict[str, Any]:
    """One linear contrast of a fit, on the log-odds scale and exponentiated.

    Both variances are returned, and both are printed.  The clustered one is the plan's
    inference; the naive one is printed beside it because a reader who cannot see the two
    cannot see whether the clustering mattered, and "we clustered" is a claim rather than a
    result until the two numbers sit side by side.

    THERE IS NO SECOND CEILING HERE, and that is deliberate.  ANALYSIS-PLAN 4.9 puts the
    ceiling on the COEFFICIENTS and refuses "at the level of the fit and not of the single
    coefficient", which happens in `fit_conditional_logit`, the one place a fit can be refused
    whole.  A contrast is a FIXED linear combination of those coefficients, written before any
    data are seen, so `|c'b|` is at most `||c||_1` times the ceiling and is bounded the moment
    the coefficients are.  A separate bound here would be a second threshold on the same
    quantity chosen at a second place, and two thresholds that could disagree are worse than
    one that cannot.  Everything reaching this function is off a fit that passed the ceiling,
    so the exponential below cannot run away.
    """
    beta = np.asarray(fit["beta"], dtype=float)
    contrast = np.asarray(contrast, dtype=float)
    point = float(contrast @ beta)
    variance_naive = float(contrast @ np.asarray(fit["covariance naive"]) @ contrast)
    variance_cluster = float(contrast @ np.asarray(fit["covariance clustered"]) @ contrast)
    se_naive = math.sqrt(max(variance_naive, 0.0))
    se_cluster = math.sqrt(max(variance_cluster, 0.0))
    return {
        "log odds": point,
        "odds ratio": float(np.exp(point)),
        "standard error naive": se_naive,
        "standard error clustered": se_cluster,
        "wald lower": float(np.exp(point - NORMAL_QUANTILE_95 * se_cluster)),
        "wald upper": float(np.exp(point + NORMAL_QUANTILE_95 * se_cluster)),
        "clustering ratio": (se_cluster / se_naive) if se_naive > 0 else float("nan"),
    }


def conditional_association(
    frame: pd.DataFrame,
    *,
    adjusted: bool,
    ratio_column: str = "r72",
    no_signal_column: str = "no_computable_step_signal",
    set_weights: Mapping[int, float] | None = None,
    n_resamples: int = BOOTSTRAP_RESAMPLES_PRIMARY,
) -> dict[str, Any]:
    """Fit the conditional model and read the two prespecified contrasts off it.

    THE REPORTED INTERVAL IS THE BOOTSTRAP ONE.  ANALYSIS-PLAN 4.5 says the bootstrap interval
    is reported "where the two disagree" and does not define disagreement, so reporting the
    bootstrap unconditionally satisfies the rule without inventing a threshold that would
    itself be a modelling choice made at the keyboard.  The clustered Wald interval is printed
    beside it, so a reader sees whether they disagreed rather than being told they did not.
    """
    built = conditional_design(frame, adjusted=adjusted, ratio_column=ratio_column,
                              no_signal_column=no_signal_column)
    design = built["design"]
    # THE FITTED ROWS, NOT THE HANDED-IN ROWS.  `conditional_design` drops the members that
    # carry no exposure window, so the outcome, the set code and the cluster code come off its
    # returned frame.  Reading them off `frame` would pair a design of one length with vectors
    # of another, and where the lengths happened to survive it would pair each design row with
    # the wrong member.
    fitted_rows = built["frame"]
    outcome = pd.Series(fitted_rows["is_case"]).astype(float).to_numpy()
    sets = pd.to_numeric(fitted_rows["set_index"], errors="coerce").astype("int64").to_numpy()
    clusters = pd.to_numeric(fitted_rows["cluster_index"],
                             errors="coerce").astype("int64").to_numpy()
    weights = None
    if set_weights is not None:
        informative = conditional_logit_sets(outcome,
                                             pd.factorize(sets, sort=True)[0].astype(np.int64))
        surviving = [code for code, keep in
                     zip(sorted(set(int(v) for v in sets)), informative) if keep]
        weights = np.array([float(set_weights.get(code, 1.0)) for code in surviving])
    fit = fit_conditional_logit(design, outcome, sets, clusters, set_weights=weights)

    n_columns = design.shape[1]
    offset = built["exposure offset"]
    ratio_contrast = step_ratio_contrast_vector(n_columns, offset)
    signal_contrast = no_signal_contrast_vector(n_columns, offset)

    # ANALYSIS-PLAN 4.9 rule 2's counter.  One list per contrast, filled by the resample
    # statistic below, so the share can be taken over the resamples that actually produced a
    # value.  It is a COUNT and never an estimate, and 4.9 obliges its reporting whether or not
    # the ceiling ever fires, "because a rule that prints nothing when it does not fire is a
    # rule a reader cannot confirm ran at all".
    # Keyed by the contrast's NAME.  `id()` of a temporary array is not a key: CPython reuses
    # an address as soon as the object behind it is collected, so two contrasts can share one
    # bucket and a count can accumulate across fits.
    above_ceiling: dict[str, list[bool]] = {}

    def _statistic(name: str, contrast: np.ndarray) -> Callable[[np.ndarray, np.ndarray], float]:
        seen = above_ceiling.setdefault(name, [])

        def inner(indices: np.ndarray, ordinal: np.ndarray) -> float:
            # The design is built ONCE and its rows are indexed.  Rebuilding it inside each
            # resample would let a resample that happens to lose a covariate level change the
            # design's width, and the contrast would then address different columns from the
            # ones it was written for.  The device-level folding of ANALYSIS-PLAN 3.6 is a
            # pre-modelling step that runs once on a count, so building it once is also what
            # the plan describes.
            #
            # ANALYSIS-PLAN 4.9 RULE 2: `refuse_above_ceiling=False`.  A resample above the
            # ceiling is RETAINED in the resample distribution and counted, not discarded.
            # Discarding the resamples that ran furthest from zero would trim exactly the tail
            # the percentile interval of 3.8 is read from and would NARROW a published
            # interval, which is the one thing this rule must never do.  A resample that fails
            # to CONVERGE still raises and is still discarded by `cluster_bootstrap`, under
            # 3.8's own rule: it produced no number to keep, while a separated resample
            # produced a number that is too large, and the two are not the same event.
            refit = fit_conditional_logit(
                design[indices],
                outcome[indices],
                np.asarray(sets)[indices],
                resample_group_codes(clusters, indices, ordinal),
                refuse_above_ceiling=False,
            )
            seen.append(bool(refit["above ceiling"]))
            return float(contrast @ np.asarray(refit["beta"]))
        return inner

    result: dict[str, Any] = {
        "fit": fit,
        "design names": built["names"],
        "day of week form": built["day of week form"],
        "adjusted": bool(adjusted),
        "n members": int(fit["n members"]),
        "n sets": int(fit["n sets"]),
        "n clusters": int(fit["n clusters"]),
        "n cases": int(fit["n cases"]),
        "n sets without both roles": int(fit["n sets without both roles"]),
        "weighted": bool(set_weights is not None),
        # ANALYSIS-PLAN 4.4, beside the fit rather than somewhere else: the members this fit
        # dropped for carrying no exposure window, and the sets that lost EVERY control that
        # way and therefore left the conditional likelihood altogether.
        "n structurally uncomputable members dropped":
            int(built["n structurally uncomputable members dropped"]),
        "n sets losing every control": int(built["n sets losing every control"]),
        "n sets losing their case": int(built["n sets losing their case"]),
        "structural violations": list(built["structural violations"]),
    }
    for key, contrast in (("step ratio", ratio_contrast),
                          ("no computable step signal", signal_contrast)):
        estimate = estimate_contrast(fit, contrast)
        boot = cluster_bootstrap(_statistic(key, contrast), clusters,
                                 n_resamples=n_resamples, seed=SEED)
        # ANALYSIS-PLAN 4.9 RULE 3, THE SHARE.  "If more than 25% of the resamples are above
        # the ceiling, the interval AND the point estimate are both refused with the same
        # reason, even where the point fit itself is below it."  An interval read off a
        # resample distribution that separated in a quarter of its draws is not an interval on
        # the quantity the row claims to report, and a point estimate whose only interval is
        # that one is not reportable either.
        #
        # 25% IS NOT A NEW CONSTANT.  4.9 says so explicitly: it is the share 3.8 already uses
        # for resample failure and trigger T4 of 3.5 already uses for bootstrap instability,
        # and reusing it "rather than inventing a second one keeps one number in this document
        # where two would invite a later argument about which of them applies".  So this reads
        # `BOOTSTRAP_MAX_FAILURE_SHARE`, the constant already here, and does not add one.
        #
        # THE DENOMINATOR IS THE RESAMPLES THAT PRODUCED A VALUE.  A resample that did not
        # converge produced no coefficient to compare against the ceiling, so it is neither
        # above it nor below it; it is already counted separately under 3.8 as a failure.
        seen = above_ceiling.get(key, [])
        n_above = int(sum(seen))
        share_above = (n_above / float(len(seen))) if seen else 0.0
        refused = share_above > BOOTSTRAP_MAX_FAILURE_SHARE
        estimate["bootstrap lower"] = float(np.exp(boot["lower"])) \
            if np.isfinite(boot["lower"]) and not refused else float("nan")
        estimate["bootstrap upper"] = float(np.exp(boot["upper"])) \
            if np.isfinite(boot["upper"]) and not refused else float("nan")
        estimate["bootstrap resamples"] = boot["n resamples"]
        estimate["bootstrap failures"] = boot["n failed"]
        estimate["bootstrap descent trigger"] = boot["descent trigger"]
        estimate["resamples above ceiling"] = n_above
        estimate["resamples with a value"] = int(len(seen))
        estimate["share above ceiling"] = float(share_above)
        estimate["refused for separation"] = bool(refused)
        result[key] = estimate
    return result


# ======================================================================================
# (11) The early-landmark weight rule of ANALYSIS-PLAN 4.4, and the three counts it obliges.
#
#      THE RULE.  A member is weighted when its own landmark day is 2 or more.  A member whose
#      landmark day is 1 or less is excluded from the WEIGHTED SENSITIVITY AND FROM NOTHING
#      ELSE: it stays in the primary, it stays in its risk set, and if its window holds fewer
#      than 2 valid days it still carries the co-primary exposure, which is the estimand that
#      exists to keep exactly these members visible.
#
#      The plan rejects the two alternatives explicitly and records why, so that neither is
#      reopened later as a preference.  Carrying the lagged wear fraction back onto the
#      preoperative grid would define the column and define it WRONG, splicing the final
#      preoperative week and the inpatient stay into one predictor.  Giving those members the
#      marginal weight would assert that the earliest members in the study have the observation
#      probability of the average member, unsupported in the one direction that flatters the
#      result, and a weight of 1 that was assumed is indistinguishable in every output from a
#      weight of 1 that was estimated.  The option taken has the opposite property: its whole
#      cost is a count, and the count is printed.
# ======================================================================================


def early_landmark_counts(frame: pd.DataFrame) -> dict[str, Any]:
    """The three counts of ANALYSIS-PLAN 4.4, and the route check that guards them.

    Count 1 is members with a landmark day of 1 or less, split by case and control and split
    again by the route that put them there.  Count 2 is matched sets that lose EVERY control
    and therefore leave the conditional likelihood altogether, which is the count that turns a
    member-level exclusion into an analysis-level one and cannot be recovered from count 1.
    Count 3 is the weighted sensitivity's own denominator, in sets and in members.

    THE ROUTE CHECK IS A STOP CONDITION.  The plan names exactly two routes to a landmark day
    of 1 or less: a control admitted below its case's day by the relaxation ladder, and a case
    admitted by the partial-window secondary at post-discharge day 4.  A member arriving there
    by neither route means the sampling produced something the plan did not specify, and
    labelling it as one of the two would hide that.
    """
    landmark_day = pd.to_numeric(frame["member_landmark_post_discharge_day"], errors="coerce")
    matched_day = pd.to_numeric(frame["member_matched_day"], errors="coerce")
    rung = pd.to_numeric(frame["match_rung"], errors="coerce")
    is_case = pd.Series(frame["is_case"]).astype(bool)
    affected = landmark_day < MIN_WEIGHTED_LANDMARK_DAY

    violations: list[str] = []
    stray_cases = affected & is_case & (matched_day > STRUCTURAL_DELETION_LAST_DAY)
    if bool(stray_cases.any()):
        violations.append(
            "a case sits at a landmark day of 1 or less while its own matched day is past the "
            "structurally deleted range, so it did not arrive by the partial-window secondary "
            "and the plan names no third route"
        )
    stray_controls = affected & (~is_case) & (rung == MATCH_RUNGS[0])
    if bool(stray_controls.any()):
        violations.append(
            "a control sits at a landmark day of 1 or less while its set matched at the "
            "strictest rung, so it did not arrive by the day-of-week relaxation and the plan "
            "names no third route"
        )

    by_route: dict[str, dict[str, int]] = {
        route: {role: 0 for role in MEMBER_ROLES} for route in EARLY_LANDMARK_ROUTES}
    by_route["partial_window_secondary"]["case"] = int((affected & is_case).sum())
    by_route["day_of_week_relaxation"]["control"] = int((affected & ~is_case).sum())

    sets = pd.Series(frame["set_index"]).astype("int64")
    controls = ~is_case
    controls_per_set = controls.groupby(sets).sum()
    affected_controls_per_set = (controls & affected).groupby(sets).sum()
    lost_every_control = ((controls_per_set > 0)
                          & (affected_controls_per_set == controls_per_set))
    case_dropped = (is_case & affected).groupby(sets).any()

    weighted_members = frame[~affected]
    weighted_sets = weighted_members.groupby("set_index")["is_case"].agg(
        lambda column: bool(pd.Series(column).astype(bool).any())
        and bool((~pd.Series(column).astype(bool)).any()))
    return {
        "n affected members": int(affected.sum()),
        "by route": {route: dict(roles) for route, roles in by_route.items()},
        "n affected cases": int((affected & is_case).sum()),
        "n affected controls": int((affected & ~is_case).sum()),
        "n sets losing every control": int(lost_every_control.sum()),
        "n sets losing their case": int(case_dropped.sum()),
        "n weighted members": int(len(weighted_members)),
        "n weighted sets": int(weighted_sets.sum()) if len(weighted_sets) else 0,
        "n members": int(len(frame)),
        "n sets": int(sets.nunique()),
        "violations": violations,
    }


def observation_weights(frame: pd.DataFrame) -> dict[str, Any]:
    """The landmark-adapted observation model of ANALYSIS-PLAN 3.7, and its stabilized weights.

    The outcome is whether the member's own landmark window was computable.  The predictors are
    the model of 3.7 with the member's own landmark day in place of the accrual day: the lagged
    wear fraction over the seven post-discharge days before the landmark, the post-discharge-day
    spline, the day-of-week class, the locked covariate set and the count of valid baseline days.

    The window behind the lagged fraction holds `min(T - 1, 7)` post-discharge days, which is a
    deterministic function of the landmark day and is therefore already absorbed by the
    post-discharge-day spline.  It is NOT entered a second time: a term that is a function of a
    term already in the model is not additional information, and it would destabilise the fit
    at exactly the days holding the fewest members.

    Weights are stabilized by the marginal observation probability and truncated at the 1st and
    99th percentiles, and the truncation points, the mean and the range are all returned so
    that 3.7's reporting requirement is met from the returned object rather than from a memory.
    """
    eligible = frame[
        pd.to_numeric(frame["member_landmark_post_discharge_day"], errors="coerce")
        >= MIN_WEIGHTED_LANDMARK_DAY].reset_index(drop=True)
    if eligible.empty:
        raise ModelDidNotConverge(
            "no risk-set member has a landmark day of 2 or more, so the observation model has "
            "no input at all and the weighted sensitivity has no denominator"
        )
    observed = 1.0 - pd.Series(eligible["no_computable_step_signal"]).astype(float).to_numpy()
    lagged = pd.to_numeric(eligible["landmark_lagged_wear_fraction"], errors="coerce")
    lagged = lagged.fillna(lagged.median() if lagged.notna().any() else 0.0)
    day_basis = rcs_basis(
        pd.to_numeric(eligible["member_matched_day"], errors="coerce").fillna(1.0)
          .to_numpy(dtype=float), DAY_SPLINE_KNOTS)
    covariates, covariate_names = covariate_columns(eligible)
    baseline_days = pd.to_numeric(eligible["n_valid_baseline_days"],
                                  errors="coerce").fillna(0.0).to_numpy(dtype=float)
    weekend = pd.Series(eligible["is_weekend_landmark"]).astype(float).to_numpy()
    design = np.column_stack([
        np.ones(len(eligible)),
        lagged.to_numpy(dtype=float),
        day_basis,
        weekend,
        baseline_days,
        covariates,
    ])
    names = (["intercept", "lagged wear fraction"]
             + [f"post-discharge day spline term {j + 1}" for j in range(day_basis.shape[1])]
             + ["landmark falls at a weekend", "valid baseline days"]
             + covariate_names)
    clusters = pd.to_numeric(eligible["cluster_index"], errors="coerce").astype("int64").to_numpy()
    fit = fit_pooled_logit(design, observed, clusters)
    fitted = np.clip(np.asarray(fit["fitted"], dtype=float), FLOAT_TOLERANCE, 1.0)
    marginal = float(observed.mean())
    raw = marginal / fitted
    lower, upper = float(np.percentile(raw, 1.0)), float(np.percentile(raw, 99.0))
    weights = np.clip(raw, lower, upper)
    eligible = eligible.assign(observation_weight=weights)
    case_rows = eligible[pd.Series(eligible["is_case"]).astype(bool)]
    set_weight = {int(row.set_index): float(row.observation_weight)
                  for row in case_rows.itertuples()}
    return {
        "frame": eligible,
        "design names": names,
        "fit": fit,
        "marginal probability": marginal,
        "weights": weights,
        "truncation lower": lower,
        "truncation upper": upper,
        "weight mean": float(np.mean(weights)),
        "weight minimum": float(np.min(weights)),
        "weight maximum": float(np.max(weights)),
        "set weight": set_weight,
        "n weighted members": int(len(eligible)),
        "n weighted sets": int(pd.Series(eligible["set_index"]).nunique()),
    }


# ======================================================================================
# (12) The collider evidence: the outcome rate with and without a computable step signal, on
#      the FULL-COHORT day-indexed panel.
#
#      Computed twice, crude and directly standardized to the post-discharge-day distribution
#      of the analytic cohort, with the standardization weights fixed by that distribution and
#      by nothing else.  If the two agree, post-discharge day is not doing the work; if they
#      disagree, the reader is shown by how much rather than told which to believe.  NEITHER
#      VERSION IS A CAUSAL ESTIMATE AND NEITHER IS LABELLED ONE: the panel controls for
#      nothing, and this comparison is the EVIDENCE for or against the collider concern, while
#      the CORRECTION for it is the co-primary exposure.
# ======================================================================================

RATE_DENOMINATOR: int = 1000                     # events per thousand episode-days
RATE_DECIMALS: int = 2

# The strata the day-standardization runs over.  FIXED A PRIORI and coarser than a single day,
# and the reason is disclosure rather than statistics.  A rate directly standardized day by day
# is a weighted average of per-day event counts that are individually far below the floor, and
# it can be neither printed nor reproduced from any printed count.  A band-wise rate keeps the
# quantity the plan asks for, reproducible from the numbers beside it, and it is a coarsening
# named in the prespecification rather than a number chosen later.
#
# TRANSCRIBED FROM ANALYSIS-PLAN 4.4, the six-row table headed "The six recovery day bands,
# fixed a priori", at plan version 1.5.  Six bands, their boundaries and their display labels,
# character for character including the en-dash in every label.  This is a TRANSCRIPTION and
# not a derivation: the plan is the authority, the citation is to a section that carries the
# table, and `_run_self_test` pins all six rows so a drift on either side fails loudly rather
# than producing a figure whose strata nobody can check against the prespecification.
DAY_BANDS: tuple[tuple[int, int, str], ...] = (
    (1, 7, "Days 1" + EN_DASH + "7"),
    (8, 14, "Days 8" + EN_DASH + "14"),
    (15, 21, "Days 15" + EN_DASH + "21"),
    (22, 28, "Days 22" + EN_DASH + "28"),
    (29, 35, "Days 29" + EN_DASH + "35"),
    (36, 90, "Days 36" + EN_DASH + "90"),
)


def _band_of(day: int) -> str:
    for first, last, label in DAY_BANDS:
        if first <= int(day) <= last:
            return label
    return "Outside the plotted horizon"


def _rate_from_rounded(events: int, days: int) -> float:
    """One rate, computed from the ROUNDED numerator over the ROUNDED denominator.

    ANALYSIS-PLAN 8 rule 4, applied to a rate for the same reason it is applied to a
    percentage: a rate computed from a true numerator and printed beside a rounded denominator
    lets a reader multiply the two and recover the hidden count to within the rounding error,
    which is exactly the leak the rounding exists to close.  Computing it from the rounded pair
    also makes every printed rate reproducible from the counts printed beside it, which is the
    first thing a careful reader checks.
    """
    if not disclosable(events):
        return float("nan")
    numerator, denominator = round20(events), round20(days)
    if not denominator:
        return float("nan")
    return float(numerator) / float(denominator) * RATE_DENOMINATOR


def landmark_comparison(panel: pd.DataFrame) -> dict[str, Any]:
    """The two-condition comparison, crude and day-standardized, with its own denominators.

    THE DEFINITIONAL CONDITION IS RETURNED BESIDE THE OTHER TWO AND IS NEVER ADDED TO THEM.  It
    is here so that a reader can see it is not in the comparison: post-discharge days 1 to 4
    have no exposure window at all, and folding them into the data condition would put an
    exclusion inside an exposure.  The three columns partition the panel, so the three day
    counts sum to the panel and no pair of them sums to anything a reader should want.

    Every rate below is computed from rounded counts, and the standardized one is suppressed
    unless EVERY contributing band clears the floor.  A standardized rate assembled out of
    stratum counts that may not be printed is a number a reader cannot check and a number that
    carries those counts inside it.
    """
    if panel.empty:
        raise GateError("the landmark panel is empty, so the collider comparison has no base")
    days = pd.to_numeric(panel["post_discharge_day"], errors="coerce").astype("int64")
    bands = days.map(_band_of)
    total_days = pd.to_numeric(panel["n_episode_days"], errors="coerce").fillna(0.0)
    columns = {
        "computable": ("n_computable_days", "n_event_days_computable"),
        "data": ("n_data_uncomputable_days", "n_event_days_data_uncomputable"),
        "definitional": ("n_definitional_days", "n_event_days_definitional"),
    }
    band_total_days = total_days.groupby(bands).sum()
    grand_total = float(band_total_days.sum())

    conditions: dict[str, dict[str, Any]] = {}
    for name, (day_column, event_column) in columns.items():
        day_counts = pd.to_numeric(panel[day_column], errors="coerce").fillna(0.0)
        event_counts = pd.to_numeric(panel[event_column], errors="coerce").fillna(0.0)
        n_days = int(day_counts.sum())
        n_events = int(event_counts.sum())
        by_band_days = day_counts.groupby(bands).sum()
        by_band_events = event_counts.groupby(bands).sum()
        present = [band for band in by_band_days.index if by_band_days[band] > 0]
        printable = all(disclosable(int(by_band_events[band])) for band in present)
        weight_covered = (float(band_total_days[present].sum()) / grand_total
                          if grand_total and present else 0.0)
        if printable and present and weight_covered > 0:
            numerator = sum(
                float(band_total_days[band]) / grand_total
                * _rate_from_rounded(int(by_band_events[band]), int(by_band_days[band]))
                for band in present)
            standardized = numerator / weight_covered
        else:
            standardized = float("nan")
        conditions[name] = {
            "n episode days": n_days,
            "n event days": n_events,
            "crude rate": _rate_from_rounded(n_events, n_days),
            "standardized rate": standardized,
            "weight covered": weight_covered,
            "n bands contributing": len(present),
            "every band printable": bool(printable),
        }
    panel_days = int(total_days.sum())
    parts = sum(conditions[name]["n episode days"] for name in columns)
    if parts != panel_days:
        raise GateError(
            "the three landmark day classes do not sum to the panel, so they are not a "
            "partition and the standardization weights do not describe the base they are "
            "applied to"
        )

    def _ratio(numerator: float, denominator: float) -> float:
        return (numerator / denominator
                if denominator and np.isfinite(denominator) and np.isfinite(numerator)
                else float("nan"))

    return {
        "conditions": conditions,
        "n episode days": panel_days,
        "n days in panel": int(days.nunique()),
        "n bands": len(DAY_BANDS),
        "crude rate ratio": _ratio(conditions["data"]["crude rate"],
                                   conditions["computable"]["crude rate"]),
        "standardized rate ratio": _ratio(conditions["data"]["standardized rate"],
                                          conditions["computable"]["standardized rate"]),
        "rate denominator": RATE_DENOMINATOR,
        "causal": False,
    }


def _collider_rate_node(value: float, *, unit: str, withheld: str) -> dict[str, Any]:
    """One rate cell of 5.7: a bound at its unit's decimals, or the reason it was withheld."""
    if not np.isfinite(value):
        return suppressed_node(withheld)
    return bound_node(float(value), unit=unit)


def collider_estimate_nodes(comparison: Mapping[str, Any]) -> dict[str, Any]:
    """EXPORT-CONTRACT 3.7's six collider keys, one per rate cell of 5.7's three by two.

    SIX AND NOT FOUR.  5.7 gives Table 4 three rows by two rate columns.  Until contract
    1.7.0 only the two crude rates and the two ratios had keys, so the STANDARDIZED RATE OF
    EACH WINDOW GROUP was a printed cell tracing to nothing, and this module could not have
    supplied it even if it wanted to, because `build_gate_block` refuses any key 3.7 does not
    declare.  ANALYSIS-PLAN 4.4 requires the per-group figure and not only the ratio: it
    judges the two conditions SEPARATELY, so "one may be standardized while the other is
    withheld, and the exhibit shows exactly that".

    NOTHING IS COMPUTED HERE.  Every number below is already in `landmark_comparison`'s
    result, computed on the full-cohort day-indexed panel, from the rounded numerator over the
    rounded denominator, and standardized over the six recovery day bands rather than over the
    day grid.  This function gives those numbers the home 3.7 now declares for them and does
    not recompute one of them, because a second computation is a second thing to drift.

    THREE REASONS A CELL CAN BE WITHHELD, AND THEY ARE DIFFERENT SENTENCES.  A crude rate
    whose event count is below the floor is not produced at all, which is
    `contributing_n_below_threshold`.  A standardized rate is produced only when EVERY band
    contributing days to that condition clears the floor, which 5.7 names as the same reason
    because it is the same floor applied to every stratum inside the weighted average.  A
    ratio cannot be formed without both of its rates, so a ratio beside a withheld rate
    carries `numerator_suppressed` rather than a reason about its own size: the number behind
    it is hidden, not small.  The crude column is unaffected by the standardized column's
    fate, because it is one numerator over one denominator and is suppressed on its own terms
    alone.
    """
    conditions = comparison["conditions"]
    with_signal = conditions["computable"]
    without_signal = conditions["data"]

    def _rate(value: float, unit: str) -> dict[str, Any]:
        return _collider_rate_node(value, unit=unit,
                                   withheld="contributing_n_below_threshold")

    nodes = {
        "collider_rate_with_signal":
            _rate(with_signal["crude rate"], "rate_per_1000_episode_days"),
        "collider_rate_without_signal":
            _rate(without_signal["crude rate"], "rate_per_1000_episode_days"),
        "collider_rate_with_signal_standardized":
            _rate(with_signal["standardized rate"], "rate_per_1000_episode_days"),
        "collider_rate_without_signal_standardized":
            _rate(without_signal["standardized rate"], "rate_per_1000_episode_days"),
    }
    for key, ratio, sides in (
        ("collider_rate_ratio_crude", comparison["crude rate ratio"],
         ("collider_rate_with_signal", "collider_rate_without_signal")),
        ("collider_rate_ratio_standardized", comparison["standardized rate ratio"],
         ("collider_rate_with_signal_standardized",
          "collider_rate_without_signal_standardized")),
    ):
        withheld = ("numerator_suppressed"
                    if any(nodes[side]["suppressed"] for side in sides)
                    else "not_estimable_data_unavailable")
        nodes[key] = _collider_rate_node(ratio, unit="rate_ratio", withheld=withheld)
    return nodes


def collider_window_counts(comparison: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    """EXPORT-CONTRACT 5.7's two window-group count pairs, keyed by window group.

    COUNTS, NOT ESTIMATES, AND DELIBERATELY NOT IN A BLOCK NAMED `estimates`.  Columns 3 and 4
    of 5.7 are the episode-days at risk and the acute-care events in each condition.  They are
    floor-tested and rounded to twenty like every other count cell, `gate.arm_a.estimates` is
    the wrong home for a count, and `denominators` carries one cohort-level analytic person-day
    total rather than a split of it.  5.7 therefore supplies them to the exporter BESIDE the
    gate block, keyed by window group, and `07_export.py` refuses Table 4 at a permitting tier
    if they are absent rather than guessing a count into a compliance bundle.
    EXPORT-CONTRACT 11.4 carries the open decision about which block should finally own them;
    this is the input that decision has not yet replaced.

    THE TRUE INTEGERS TRAVEL AND THE ROUNDING HAPPENS ONCE, at the export boundary, which is
    the rule everywhere else in this pipeline.  Rounding here and rounding again there would
    apply the floor to a number that had already been moved off the value it was testing.

    THE DEFINITIONAL CONDITION IS NOT A WINDOW GROUP HERE.  5.7 is three rows and the third is
    the ratio.  The definitional day class is printed beside the comparison in this module's
    own report so a reader can see it is excluded, and it is never added to the row above it.
    """
    conditions = comparison["conditions"]
    return {
        "with_signal": {
            "episode_days": int(conditions["computable"]["n episode days"]),
            "events": int(conditions["computable"]["n event days"]),
        },
        "without_signal": {
            "episode_days": int(conditions["data"]["n episode days"]),
            "events": int(conditions["data"]["n event days"]),
        },
    }


# ======================================================================================
# (13) The complementary full-cohort discrete-time model, and the absolute risk.
#
#      ANALYSIS-PLAN 4.6.  Absolute risks come from HERE and never from the conditional model,
#      whose matched-set intercepts are conditioned out and which therefore has no intercept to
#      translate into a risk at all.  Absolute risks are printed BEFORE relative ones, per the
#      house numeral style, and the report does so.
# ======================================================================================


def discrete_time_design(panel: pd.DataFrame) -> dict[str, Any]:
    """The pooled logistic design: intercept, day spline, exposure block, covariates.

    STRUCTURALLY UNCOMPUTABLE DAYS ARE DROPPED HERE AND COUNTED.  Post-discharge days 1 to 4
    carry no exposure window at all, and admitting them with the no-computable-signal indicator
    set would put the definitional condition inside the data condition.  Their count is
    returned separately and is never added to the data condition's count.
    """
    structural = pd.Series(panel["structurally_uncomputable_landmark"]).astype(bool)
    kept = panel[~structural].reset_index(drop=True)
    if kept.empty:
        raise ModelDidNotConverge(
            "every panel day is structurally uncomputable, so there is no exposure to model"
        )
    day_basis = rcs_basis(
        pd.to_numeric(kept["post_discharge_day"], errors="coerce").fillna(1.0)
          .to_numpy(dtype=float), DAY_SPLINE_KNOTS)
    exposure, exposure_names = exposure_columns(kept["r72"], kept["no_computable_step_signal"])
    covariates, covariate_names = covariate_columns(kept)
    design = np.column_stack([np.ones(len(kept)), day_basis, exposure, covariates])
    names = (["intercept"]
             + [f"post-discharge day spline term {j + 1}" for j in range(day_basis.shape[1])]
             + list(exposure_names) + covariate_names)
    return {
        "frame": kept,
        "design": design,
        "names": names,
        "exposure offset": 1 + day_basis.shape[1],
        "n structurally uncomputable days dropped": int(structural.sum()),
        "day basis width": day_basis.shape[1],
    }


def standardized_risk(fit: Mapping[str, Any], design: np.ndarray, exposure_offset: int,
                      *, ratio: float, horizon_days: int = OUTCOME_HORIZON_DAYS,
                      ) -> dict[str, Any]:
    """The g-computed absolute risk at one proximal ratio, with a delta-method interval.

    Every episode-day in the panel is set to a computable window at the given ratio, its own
    post-discharge day and its own covariates are left alone, and the fitted daily probabilities
    are averaged.  Standardizing to the cohort's own day and covariate distribution is what
    makes the number an absolute risk for THIS cohort rather than for a hypothetical patient
    at the covariate means.

    The horizon conversion assumes the standardized daily probability holds across the horizon.
    That assumption is stated rather than buried: it is the constant-hazard version of the
    discrete-time survival identity, and the report prints the daily probability beside the
    horizon risk so a reader can see both.

    The interval is a delta-method interval on the LOG-ODDS of the horizon risk, back
    transformed, so it cannot fall outside zero and one, which a symmetric interval on a risk
    of a fraction of a percent very easily does.
    """
    beta = np.asarray(fit["beta"], dtype=float)
    covariance = np.asarray(fit["covariance clustered"], dtype=float)
    counterfactual = np.array(design, dtype=float, copy=True)
    block, _ = exposure_columns(np.full(design.shape[0], float(ratio)),
                                np.zeros(design.shape[0]))
    counterfactual[:, exposure_offset: exposure_offset + block.shape[1]] = block
    linear = counterfactual @ beta
    probability = _expit(linear)
    mean_probability = float(np.mean(probability))
    gradient_mean = (probability * (1.0 - probability)) @ counterfactual / design.shape[0]
    horizon = 1.0 - (1.0 - mean_probability) ** int(horizon_days)
    gradient_horizon = (int(horizon_days) * (1.0 - mean_probability) ** (int(horizon_days) - 1)
                        * gradient_mean)
    safe = min(max(horizon, FLOAT_TOLERANCE), 1.0 - FLOAT_TOLERANCE)
    gradient_logit = gradient_horizon / (safe * (1.0 - safe))
    variance = float(gradient_logit @ covariance @ gradient_logit)
    standard_error = math.sqrt(max(variance, 0.0))
    centre = math.log(safe / (1.0 - safe))
    lower = 1.0 / (1.0 + math.exp(-(centre - NORMAL_QUANTILE_95 * standard_error)))
    upper = 1.0 / (1.0 + math.exp(-(centre + NORMAL_QUANTILE_95 * standard_error)))
    return {
        "ratio": float(ratio),
        "daily probability": mean_probability,
        "horizon days": int(horizon_days),
        "risk": horizon,
        "lower": lower,
        "upper": upper,
        "standard error on the log odds": standard_error,
    }


def lead_time_hours(panel: pd.DataFrame, predicted: np.ndarray, threshold: float,
                    ) -> dict[str, Any]:
    """Median lead time at the fixed alert threshold, in hours.

    CLOSED HERE.  ANALYSIS-PLAN 4.8 requires median lead time in the tier 1 panel and fixes the
    threshold at 80% sensitivity, but does not define from WHEN the lead is measured.  An alert
    raised for post-discharge day `d` rests on the window ending at day `d` minus 3, so the
    alert could not have existed before that day's data did, and the lead is measured from
    there to the event.  The lookback is one week, so a lead time runs from 3 to 9 days.

    A case with no alert anywhere in the lookback contributes no lead time and is COUNTED, not
    dropped silently: a median lead time computed only over detected cases is a statement about
    the detected ones and its denominator has to travel with it.
    """
    frame = panel.assign(predicted=np.asarray(predicted, dtype=float))
    outcome = pd.to_numeric(frame["outcome"], errors="coerce").fillna(0)
    events = frame[outcome > 0]
    leads: list[float] = []
    n_without_alert = 0
    if not np.isfinite(threshold):
        return {"hours": [], "n cases": int(len(events)), "n without an alert": int(len(events))}
    for row in events.itertuples():
        episode = frame[frame["episode_index"] == row.episode_index]
        day = int(row.post_discharge_day)
        window = episode[
            (pd.to_numeric(episode["post_discharge_day"], errors="coerce") >= day
             - LEAD_TIME_LOOKBACK_DAYS)
            & (pd.to_numeric(episode["post_discharge_day"], errors="coerce") <= day)
            & (episode["predicted"] >= threshold)]
        if window.empty:
            n_without_alert += 1
            continue
        first_alert_day = int(pd.to_numeric(window["post_discharge_day"],
                                            errors="coerce").min())
        leads.append(float((day - (first_alert_day - LANDMARK_OFFSET_DAYS)) * HOURS_PER_DAY))
    return {
        "hours": leads,
        "n cases": int(len(events)),
        "n with an alert": int(len(leads)),
        "n without an alert": n_without_alert,
    }


# ======================================================================================
# (14) Disclosure at the boundary, and the node grammar of EXPORT-CONTRACT section 2.
#
#      TWO DIFFERENT QUESTIONS, ASKED IN THIS ORDER AND NEVER COLLAPSED.  First: is this TRUE
#      count disclosable?  `disclosable(n)` on the raw integer decides whether the cell may be
#      shown at all.  Second: is this RENDERED cell a legal disclosed output?
#      `is_legal_disclosed_count` re-reads what `round20` produced.  Asking the first question
#      of an already-rounded number is how a suppressed 21 becomes a printed 20, which is the
#      defect the disclosure module was corrected for.
#
#      A suppressed node carries NO numeric key at all.  There is no `"n": null` and no
#      `"est": null`: the number is not in the file.  A consumer doing arithmetic on a
#      suppressed node gets a TypeError at the exact expression that mishandled it, which is
#      the whole reason the contract chose an object over a sentinel.
# ======================================================================================

def assert_display_string(text: str, where: str) -> str:
    """The house prose stop conditions, on one rendered string, before it goes anywhere."""
    if EM_DASH in text:
        raise DisclosureError(f"{where} contains an em-dash, which no house string may carry")
    if MINUS_SIGN in text:
        raise DisclosureError(f"{where} contains a Unicode minus sign, which is banned")
    return text


def suppressed_node(reason: str) -> dict[str, Any]:
    """A suppressed value, in the one shape the contract fixes for every kind of number."""
    if reason not in SUPPRESSION_REASONS:
        raise DisclosureError(f"'{reason}' is not a suppression reason in the label table")
    sentence = SUPPRESSION_REASONS[reason]
    return {
        "suppressed": True,
        "reason": reason,
        "reason_display": sentence,
        "display": sentence,
    }


def count_node(n: Any) -> dict[str, Any]:
    """A count, floor-tested on its TRUE integer and then rendered from the rounded one."""
    value = _whole(n, "a count")
    if not disclosable(value):
        return suppressed_node("cell_below_threshold")
    rendered = round20(value)
    if not is_legal_disclosed_count(rendered):
        raise DisclosureError(
            "a count cleared the floor on its true value and then rendered to a cell that is "
            "not a legal disclosed output, which means the two questions have been crossed"
        )
    return {
        "suppressed": False,
        "n": int(rendered),
        "rounded": value != 0,
        "display": assert_display_string(f"{int(rendered):,}", "a count node"),
    }


def _render_number(value: float, unit: str, decimals: int | None = None) -> str:
    """One number at the decimals its unit fixes, with the house thousands separator."""
    places = UNIT_DECIMALS[unit] if decimals is None else int(decimals)
    if unit in ("count", "steps"):
        return f"{value:,.{places}f}"
    return f"{value:.{places}f}"


def estimate_node(point: float, lower: float, upper: float, *, unit: str,
                  contributing_n: Any, decimals: int | None = None) -> dict[str, Any]:
    """An estimate with a 95% interval, suppressed on its CONTRIBUTING count, not on its value.

    A continuous statistic is never rounded to 20; it is rounded to the decimals its unit fixes
    and it is disclosable only when the count of participants behind it satisfies the floor.
    Confusing the two rules is the single easiest way to leak: a median over three people is
    individual-level data whatever its decimals.

    The interval separator is the word " to " and never a dash, because an interval may cross
    zero and a column that switches separator by sign is worse than one that never switches.
    """
    if unit not in UNIT_DECIMALS:
        raise DisclosureError(f"'{unit}' is not a unit this module knows the decimals for")
    n = _whole(contributing_n, "the contributing count behind an estimate")
    if not disclosable(n):
        return suppressed_node("contributing_n_below_threshold")
    if not all(np.isfinite([point, lower, upper])):
        return suppressed_node("not_estimable_convergence")
    suffix = "%" if unit == "percent" else ""
    point_text = _render_number(point, unit, decimals) + suffix
    lower_text = _render_number(lower, unit, decimals) + suffix
    upper_text = _render_number(upper, unit, decimals) + suffix
    interval = f"95% CI {lower_text} to {upper_text}"
    return {
        "suppressed": False,
        "est": float(round(point, UNIT_DECIMALS[unit] if decimals is None else int(decimals))),
        "lo": float(round(lower, UNIT_DECIMALS[unit] if decimals is None else int(decimals))),
        "hi": float(round(upper, UNIT_DECIMALS[unit] if decimals is None else int(decimals))),
        "level": CONFIDENCE_LEVEL,
        "unit": unit,
        "display": assert_display_string(f"{point_text} ({interval})", "an estimate node"),
        "display_point": point_text,
        "display_ci": interval,
    }


def bound_node(value: float, *, unit: str, decimals: int | None = None) -> dict[str, Any]:
    """A point with NO interval, in the estimate shape EXPORT-CONTRACT 2.2 fixes.

    A BOUND IS A BOUND AND NOT AN INTERVAL.  2.2's estimate shape requires `est`, `lo`, `hi`
    and `level`, and a quantity the prespecification computes without an interval has only the
    point.  Three different numbers would publish an interval nobody estimated; omitting `lo`
    and `hi` would emit a node the three consumer helpers of 2.3 cannot read.  So the point
    sits on all three numeric keys and `display_ci` is EMPTY, which means a renderer printing
    `display` prints one number and a renderer printing `display_ci` prints nothing rather than
    an interval of zero width that a reader would take for a very precise estimate.
    `07_export.py` carries the same shape under the same name, for the same reason.

    IT IS NOT FLOOR-TESTED HERE, and that is deliberate rather than an omission.  The caller
    has already tested the count this value was computed from: `_rate_from_rounded` returns a
    non-finite value when its numerator is below the floor, and a band-standardized rate is
    withheld unless EVERY contributing band clears it, which is a set of counts and not one
    number this function could be handed.  A second floor test here would have to invent a
    contributing count to test, which is the defect it would look like it was preventing.
    """
    if unit not in UNIT_DECIMALS:
        raise DisclosureError(f"'{unit}' is not a unit this module knows the decimals for")
    if not np.isfinite(value):
        raise DisclosureError(
            "a bound node was asked for a value that is not finite. A quantity that was not "
            "computed is a suppressed node carrying the reason it was not, never a point"
        )
    places = UNIT_DECIMALS[unit] if decimals is None else int(decimals)
    printed = _render_number(value, unit, decimals)
    rounded = float(round(value, places))
    return {
        "suppressed": False,
        "est": rounded,
        "lo": rounded,
        "hi": rounded,
        "level": CONFIDENCE_LEVEL,
        "unit": unit,
        "display": assert_display_string(printed, "a bound node"),
        "display_point": printed,
        "display_ci": "",
    }


def quantile_node(values: Sequence[float], *, unit: str, contributing_n: Any,
                  decimals: int | None = None) -> dict[str, Any]:
    """An observed median and interquartile range, suppressed on its contributing count.

    The range separator is the en-dash, because a quantile range of a non-negative quantity
    never carries a sign, which is exactly the case a confidence interval is not.
    """
    if unit not in UNIT_DECIMALS:
        raise DisclosureError(f"'{unit}' is not a unit this module knows the decimals for")
    n = _whole(contributing_n, "the contributing count behind a quantile")
    if not disclosable(n):
        return suppressed_node("contributing_n_below_threshold")
    array = np.asarray([v for v in values if np.isfinite(v)], dtype=float)
    if array.size == 0:
        return suppressed_node("not_estimable_data_unavailable")
    q25, q50, q75 = (float(np.percentile(array, 25.0)), float(np.percentile(array, 50.0)),
                     float(np.percentile(array, 75.0)))
    point_text = _render_number(q50, unit, decimals)
    range_text = (f"{_render_number(q25, unit, decimals)}{EN_DASH}"
                  f"{_render_number(q75, unit, decimals)}")
    places = UNIT_DECIMALS[unit] if decimals is None else int(decimals)
    return {
        "suppressed": False,
        "q50": float(round(q50, places)),
        "q25": float(round(q25, places)),
        "q75": float(round(q75, places)),
        "unit": unit,
        "display": assert_display_string(f"{point_text} ({range_text})", "a quantile node"),
        "display_point": point_text,
        "display_iqr": range_text,
    }


def complementary_suppression(counts: Mapping[str, int]) -> dict[str, dict[str, Any]]:
    """Suppress every cell below the floor, and a second cell where one alone is recoverable.

    ANALYSIS-PLAN 8 rule 5.  If suppressing one cell of a row still allows it to be recovered
    by subtraction from a disclosed total, a second cell is suppressed as well.  The second one
    chosen is the smallest disclosable cell, so the rule costs the least information it can.
    """
    values = {key: _whole(value, f"the count for {key}") for key, value in counts.items()}
    hidden = {key for key, value in values.items() if not disclosable(value)}
    if len(hidden) == 1 and len(values) > 1:
        candidates = sorted((value, key) for key, value in values.items() if key not in hidden)
        if candidates:
            hidden.add(candidates[0][1])
            secondary = candidates[0][1]
        else:
            secondary = None
    else:
        secondary = None
    out: dict[str, dict[str, Any]] = {}
    for key, value in values.items():
        if key == secondary:
            out[key] = suppressed_node("secondary_suppression")
        elif key in hidden:
            out[key] = suppressed_node("cell_below_threshold")
        else:
            out[key] = count_node(value)
    return out


def stage_f_nodes(counts: Mapping[str, int]) -> dict[str, dict[str, Any]]:
    """Stage F, all or nothing, and EXPECTED TO BE NOTHING.

    ANALYSIS-PLAN 9.4: stage F prints as suppressed UNLESS ALL cells are disclosable, because a
    single disclosed cell alongside suppressed ones plus a disclosed total recovers the
    suppressed cells by subtraction.  Plan 1.3 says in advance that this will very likely be
    suppressed in every stratum, so this function treats that as the ORDINARY outcome and not
    as a failure: it returns a full set of suppressed nodes and nothing raises.
    """
    values = {key: _whole(value, f"the stage F count for {key}") for key, value in counts.items()}
    if values and all(disclosable(value) for value in values.values()):
        return {key: count_node(value) for key, value in values.items()}
    return {key: suppressed_node("cell_below_threshold") for key in values}


# ======================================================================================
# (15) The gate block.  Exactly the keys EXPORT-CONTRACT 3.7 declares, and nothing else.
#
#      Anything this module produces that the contract has no key for goes OUTSIDE this block,
#      into the module's own result, and is listed in `CONTRACT_GAPS`.  Adding a key here that
#      the contract does not declare would fail `verify.py` at the far end of the pipeline, in
#      Phase 4, for real money; leaving a produced number out of the returned object entirely
#      would lose it.  So it is returned, and it is returned somewhere a schema check will not
#      mistake for the bundle.
# ======================================================================================


def read_ladder(frame: pd.DataFrame, groups: Sequence[str]) -> dict[str, Any]:
    """Turn the long ladder frame into the six stages, deriving every margin from TRUE integers.

    A margin summed from ROUNDED parts carries an error of up to ten per cell, which is how a
    total ends up disagreeing with its own row by more than the rounding footnote can explain.
    Every sum below is over exact integers and the rounding happens once, at the node.
    """
    if frame.empty:
        raise GateError("the gate ladder query returned nothing, so there is no gate to read")
    counts: dict[tuple[str, str, str], int] = {}
    for row in frame.to_dict("records"):
        key = (str(row["stage_letter"]), str(row["part_slug"]), str(row["group_slug"]))
        counts[key] = counts.get(key, 0) + _whole(row["n_units"], "a ladder count")
    unknown = sorted({letter for letter, _, _ in counts} - set(GATE_STAGE_LETTERS))
    if unknown:
        raise GateError(f"the ladder frame carries stage letter(s) {unknown}, which the "
                        f"protocol's ledger does not name")
    selected = [slug for slug in FOUR_GROUP_SLUGS if slug in set(groups)] or list(groups)

    def _by_group(letter: str) -> dict[str, int]:
        return {slug: counts.get((letter, "total", slug), 0) for slug in selected}

    stage_a = _by_group("A")
    stage_f = _by_group("F")
    stage_e_total = counts.get(("E", "total", ALL_GROUPS_SLUG), 0)
    stage_f_total = sum(stage_f.values())
    if stage_f_total != stage_e_total:
        raise GateError(
            f"stage F stratifies stage E and the two totals disagree ({stage_f_total} against "
            f"{stage_e_total}). A stratification that does not sum to what it stratifies is "
            f"either missing a stratum or double counting one."
        )
    return {
        "A": {"total": sum(stage_a.values()), "by_group": stage_a, "components": None},
        "B": {"total": counts.get(("B", "total", ALL_GROUPS_SLUG), 0),
              "by_group": None, "components": None},
        "C": {"total": counts.get(("C", "total", ALL_GROUPS_SLUG), 0),
              "by_group": None, "components": None},
        "D": {"total": counts.get(("D", "total", ALL_GROUPS_SLUG), 0),
              "by_group": None,
              "components": {part: counts.get(("D", part, ALL_GROUPS_SLUG), 0)
                             for part in STAGE_D_COMPONENTS}},
        "E": {"total": stage_e_total, "by_group": None, "components": None},
        "F": {"total": stage_f_total, "by_group": stage_f, "components": None},
        "groups": selected,
    }


def gate_stages(ladder: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The six stage records of EXPORT-CONTRACT 3.7, in letter order, with their nodes."""
    stages: list[dict[str, Any]] = []
    for letter in GATE_STAGE_LETTERS:
        raw = ladder[letter]
        if letter == "F":
            by_group = stage_f_nodes(raw["by_group"] or {})
        elif raw["by_group"] is not None:
            by_group = complementary_suppression(raw["by_group"])
        else:
            by_group = None
        components = (complementary_suppression(raw["components"])
                      if raw["components"] is not None else None)
        stages.append({
            "letter": letter,
            "slug": GATE_STAGE_SLUGS[letter],
            "display_label": GATE_STAGE_LABELS[letter],
            "definition_display": GATE_STAGE_DEFINITIONS[letter],
            "unit": GATE_STAGE_UNITS[letter],
            "total": count_node(raw["total"]),
            "by_group": by_group,
            "components": components,
        })
    return stages


def arm_a_reason(tier: Mapping[str, Any]) -> str:
    """Why part B carries what it carries, printed instead of a blank table.

    The tier 4 sentence is the contract's own, verbatim, EXCEPT where the deciding count is a
    measured zero.  A zero is disclosable, so the second half of that sentence, which says the
    deciding count is itself below the disclosure floor, would simply be false; a zero-event
    gate is reported as a zero and the tier is still the lowest one.
    """
    index = int(tier["index"])
    if index == 4:
        if not tier["event_count_printable"]:
            return ("The feasibility gate reached the lowest prespecified tier, which permits "
                    "no early-warning estimate. The deciding count is itself below the "
                    "disclosure floor, so the tier boundary and the disclosure floor coincide.")
        return ("The feasibility gate reached the lowest prespecified tier, which permits no "
                "early-warning estimate. The deciding count is a measured zero, which is "
                "disclosable and is printed.")
    if index == 3:
        return ("The feasibility gate reached the event-centered tier, which permits "
                "association and visualization only. No prediction model, no discrimination "
                "metric and no alert-burden calculation was computed, and no prediction-tool "
                "claim of any kind is made.")
    if index == 2:
        return ("The feasibility gate reached the step-first tier, which permits an "
                "exploratory model with no broad feature selection. Every estimate below is "
                "labelled exploratory and none of it is a prediction tool.")
    return ("The feasibility gate reached the highest tier, which permits a detection model "
            "with internal validation. The exhibit set switches to the alternate set, which "
            "the export contract must carry before any of this is written.")


def build_gate_block(stages: Sequence[Mapping[str, Any]], tier: Mapping[str, Any],
                     estimates: Mapping[str, Any]) -> dict[str, Any]:
    """Assemble `results.json`'s `gate` block, and refuse a key the contract does not declare."""
    permitted = int(tier["index"]) != 4
    unknown = sorted(set(estimates) - set(ESTIMATE_KEYS))
    if unknown:
        raise GateError(
            f"the estimates block carries key(s) {unknown}, which EXPORT-CONTRACT 3.7 does "
            f"not declare. A key the contract has no home for goes outside this block and "
            f"into the module's own result, where a schema check will not mistake it for the "
            f"bundle."
        )
    missing = [key for key in ESTIMATE_KEYS if key not in estimates]
    if permitted and missing:
        raise GateError(
            f"the estimates block is missing key(s) {missing}. Every key is present at every "
            f"tier that permits Arm A at all, carrying either a number or a printed refusal, "
            f"because a key absent from the block is indistinguishable from a bug."
        )
    return {
        "stages": [dict(stage) for stage in stages],
        "tier": tier_record_for_export(tier),
        "arm_a": {
            "permitted": permitted,
            "reason_display": arm_a_reason(tier),
            "estimates": ({} if not permitted
                          else {key: estimates[key] for key in ESTIMATE_KEYS}),
        },
    }


def tier_refusal_estimates(tier_index: int) -> dict[str, Any]:
    """Every contract estimate key the tier forbids, as a printed refusal keyed by its name.

    This is the estimates half of refusing by name.  A key present and carrying "not permitted
    at the feasibility tier reached" tells a reader that the quantity exists in the
    specification and was not computed; a key absent tells them nothing at all.
    """
    return {key: suppressed_node("not_permitted_by_tier")
            for key in ESTIMATE_KEYS
            if not permitted_at(ESTIMATE_KEY_ANALYSIS[key], tier_index)}


# ======================================================================================
# (16) The analysis driver.  PURE: it takes the frames and the tier and returns the numbers,
#      so the self-test drives every branch of it without a network.
# ======================================================================================


def landmark_timing_summary(frame: pd.DataFrame) -> dict[str, Any]:
    """The rung 18 report of ANALYSIS-PLAN 4.3, and the six-row derivation checked not trusted.

    THE TWO COUNTS ARE RETURNED AS TWO KEYS AND THERE IS DELIBERATELY NO SUM.  `n structurally
    deleted` is the definitional condition and those events LEAVE at rung 18; `n data
    uncomputable` is the data condition and those windows STAY, entering the model through the
    co-primary exposure.  A single "no computable landmark" number would be the sum of an
    exclusion and an exposure, and no reader could take it apart again afterwards.
    """
    if frame.empty:
        return {"n first events": 0, "n structurally deleted": 0, "n data uncomputable": 0,
                "n computable": 0, "by day": {}, "violations": [],
                "derived range": (STRUCTURAL_DELETION_FIRST_DAY, STRUCTURAL_DELETION_LAST_DAY)}
    day = pd.to_numeric(frame["event_post_discharge_day"], errors="coerce").astype("int64")
    events = pd.to_numeric(frame["n_events"], errors="coerce").fillna(0).astype("int64")
    structural = pd.to_numeric(frame["n_structurally_uncomputable"],
                               errors="coerce").fillna(0).astype("int64")
    data = pd.to_numeric(frame["n_data_uncomputable"], errors="coerce").fillna(0).astype("int64")
    computable = pd.to_numeric(frame["n_computable"], errors="coerce").fillna(0).astype("int64")
    disagreement = int(pd.to_numeric(frame["n_flag_disagrees_with_derived_range"],
                                     errors="coerce").fillna(0).sum())
    violations: list[str] = []
    if disagreement:
        violations.append(
            "the definitional landmark flag disagrees with the derived range on at least one "
            "first event. The plan derives post-discharge day 1 to 4 from its own two-valid-day "
            "rule and any document writing day 1 to 3 is wrong; a disagreement here means the "
            "flag and the derivation have parted company and no count below can be trusted"
        )
    deleted = {int(d): int(n) for d, n in zip(day, structural) if int(n) > 0}
    outside = sorted(d for d in deleted
                     if not (STRUCTURAL_DELETION_FIRST_DAY <= d <= STRUCTURAL_DELETION_LAST_DAY))
    if outside:
        violations.append(
            f"events on post-discharge day(s) {outside} are marked definitionally uncomputable "
            f"and lie outside the derived range"
        )
    return {
        "n first events": int(events.sum()),
        "n structurally deleted": int(structural.sum()),
        "n data uncomputable": int(data.sum()),
        "n computable": int(computable.sum()),
        "by day": deleted,
        "all days": {int(d): int(n) for d, n in zip(day, events)},
        "derived range": (STRUCTURAL_DELETION_FIRST_DAY, STRUCTURAL_DELETION_LAST_DAY),
        "violations": violations,
    }


def matched_set_size_values(frame: pd.DataFrame) -> tuple[list[float], int]:
    """Expand the set-size ledger back into the value list a quantile needs.

    A distribution over a small whole-number domain carries the same order statistics as the
    rows behind it, so the median and the interquartile range are exact and nothing
    participant-level was ever read.
    """
    if frame.empty:
        return [], 0
    values: list[float] = []
    for row in frame.to_dict("records"):
        size = _whole(row["set_size"], "a matched set size")
        n_sets = _whole(row["n_sets"], "a matched set count")
        values.extend([float(size)] * n_sets)
    return values, len(values)


def _record_model_failure(detail: dict[str, Any], key: str, slug: str,
                          failure: ModelDidNotConverge) -> str:
    """File a failed fit, and file a SEPARATED one again in the ledger ANALYSIS-PLAN 4.9 obliges.

    4.9's first obliged count is "fits refused at the ceiling, by analysis slug, so a reader
    can see which rows are absent for this reason rather than for cell size, for convergence,
    or for the tier reached".  This is where that count is accumulated.  Returns the suppression
    reason the caller should attach, so the choice between the separation sentence and the
    convergence sentence is made once here rather than at five call sites.
    """
    detail[key] = str(failure)
    if isinstance(failure, ModelSeparated):
        detail.setdefault("fits refused at the ceiling", []).append(slug)
        return "not_estimable_separation"
    return "not_estimable_convergence"


def _odds_ratio_node(estimate: Mapping[str, Any], *, contributing_n: Any) -> dict[str, Any]:
    """One odds-ratio node, refused under ANALYSIS-PLAN 4.9 rule 3 before it is rendered.

    Rule 3 refuses the INTERVAL AND THE POINT ESTIMATE together when more than the permitted
    share of resamples sat above the ceiling, "even where the point fit itself is below it".
    The refusal has to happen here rather than by handing `estimate_node` a non-finite interval,
    because that route produces the convergence sentence and 4.9 is explicit that the
    convergence sentence is false of a separated fit.
    """
    if estimate.get("refused for separation"):
        return suppressed_node("not_estimable_separation")
    return estimate_node(estimate["odds ratio"], estimate["bootstrap lower"],
                         estimate["bootstrap upper"], unit="odds_ratio",
                         contributing_n=contributing_n)


def analyse(frames: Mapping[str, pd.DataFrame], *, tier: Mapping[str, Any],
            groups: Sequence[str] = FOUR_GROUP_SLUGS,
            n_resamples: int = BOOTSTRAP_RESAMPLES_PRIMARY) -> dict[str, Any]:
    """Everything the tier permits, and a printed refusal for everything it does not.

    The order is the order of the argument: the ladder first, because the gate is read off it;
    then the analyses, each guarded by the catalogue.  Nothing below consults an estimate to
    decide whether to compute another estimate.
    """
    index = int(tier["index"])
    halting: list[str] = []
    ladder = read_ladder(frames["gate ladder"], groups)
    stages = gate_stages(ladder)
    timing = landmark_timing_summary(frames["structurally deleted event timing"])
    halting += timing["violations"]
    if timing["n computable"] != ladder["E"]["total"]:
        halting.append(
            "the event timing frame and the ladder disagree about how many first events carry "
            "a computable proximal ratio, and that count is the gate itself"
        )

    estimates: dict[str, Any] = dict(tier_refusal_estimates(index))
    extra: dict[str, Any] = {}
    # 5.7's two window-group count pairs. They are counts, so `estimates` is the wrong home
    # for them and they travel beside the gate block instead. Empty at a tier that submits no
    # landmark panel query, which is the same tier at which Table 4 is three rows of refusals.
    window_counts: dict[str, dict[str, int]] = {}
    detail: dict[str, Any] = {"ladder": ladder, "timing": timing}

    # ---- the collider evidence, at every tier that permits it ---------------------------
    if permitted_at("landmark_condition_comparison", index):
        comparison = landmark_comparison(frames["landmark panel"])
        detail["landmark comparison"] = comparison
        # EXPORT-CONTRACT 3.7's six collider keys and 5.7's two count pairs, both read off the
        # comparison just computed and neither recomputed. Until contract 1.7.0 declared the
        # keys these numbers were printed in this module's report and reached the bundle
        # nowhere at all, so `07_export.py` refused Table 4 at every tier that permits the
        # comparison, which is tiers 1 to 3.
        estimates.update(collider_estimate_nodes(comparison))
        window_counts = collider_window_counts(comparison)
        short = int(pd.to_numeric(frames["landmark panel"]["n_wearable_lookback_short"],
                                  errors="coerce").fillna(0).sum())
        if short:
            halting.append(
                "the wearable lookback behind at least one landmark is shorter than seven "
                "days. DAG-SCHEMA 8.13 says that is not a data condition to be weighted "
                "around: it means the wearable grid does not cover the lookback, and it is a "
                "defect to be found before the weights are fitted"
            )

    # ---- the matched-set size distribution ----------------------------------------------
    if permitted_at("matched_set_size_distribution", index):
        sizes, n_sets = matched_set_size_values(frames["matched set sizes"])
        detail["matched set sizes"] = {"values": sizes, "n sets": n_sets}
        estimates["matched_set_size"] = quantile_node(sizes, unit="count", contributing_n=n_sets)

    # ---- the event-centered description --------------------------------------------------
    if permitted_at("event_centered_description", index):
        detail["event centered curve"] = frames["event centered curve"]

    # ---- the conditional models -----------------------------------------------------------
    if permitted_at("unadjusted_association", index):
        members = frames["risk set model frame"]
        counts = early_landmark_counts(members)
        detail["early landmark"] = counts
        halting += counts["violations"]
        # ANALYSIS-PLAN 4.4's member-level drop, read off the DERIVED FLAG rather than off the
        # landmark-day arithmetic, and computed HERE rather than only inside the fit.  4.4
        # obliges its counts "whether or not the weighted sensitivity moves the estimate", and
        # a count that exists only when a model converged is not that count.  The two readings
        # are the same condition written two ways, and `structural_member_counts` halts on a
        # row where they differ rather than picking one.
        structural = structural_member_counts(members)
        detail["structural members"] = structural
        halting += structural["violations"]
        try:
            unadjusted = conditional_association(members, adjusted=False,
                                                 n_resamples=n_resamples)
            detail["unadjusted"] = unadjusted
            # THE FIT'S OWN DENOMINATOR, under the rule of ANALYSIS-PLAN 9.2 that a row fitted
            # on a subset prints its own `n`.  This model IS fitted on a subset now: members
            # carrying no exposure window leave before it runs, and a participant who appeared
            # only as one of those is not in the fit at all.  Counting off the handed-in frame
            # would print a denominator larger than the one the number came from.
            contributing = min(int(unadjusted["n cases"]), int(unadjusted["n clusters"]))
            # BOTH OF THESE ARE CONTRACT KEYS AS OF 3.7 AND NO LONGER MODULE EXTRAS. They come
            # off the same unadjusted fit, which is the one association tier 3 permits, and
            # `odds_of_no_computable_step_signal` is `beta_N` of ANALYSIS-PLAN 4.4: the
            # co-primary exposure's own odds, an estimand of interest in its own right because
            # it answers whether loss of data precedes utilization.
            estimates["unadjusted_odds_per_lower_step_ratio"] = _odds_ratio_node(
                unadjusted["step ratio"], contributing_n=contributing)
            estimates["odds_of_no_computable_step_signal"] = _odds_ratio_node(
                unadjusted["no computable step signal"], contributing_n=contributing)
            for _contrast, _slug in (("step ratio", "unadjusted_association"),
                                     ("no computable step signal", "unadjusted_association")):
                if unadjusted[_contrast]["refused for separation"]:
                    detail.setdefault("fits refused at the ceiling", []).append(_slug)
        except ModelDidNotConverge as failure:
            reason = _record_model_failure(detail, "unadjusted failure",
                                           "unadjusted_association", failure)
            estimates["unadjusted_odds_per_lower_step_ratio"] = suppressed_node(reason)
            estimates["odds_of_no_computable_step_signal"] = suppressed_node(reason)

        if permitted_at("adjusted_conditional_logistic_model", index):
            try:
                adjusted = conditional_association(members, adjusted=True,
                                                   n_resamples=n_resamples)
                detail["adjusted"] = adjusted
                estimates["adjusted_odds_per_lower_step_ratio"] = _odds_ratio_node(
                    adjusted["step ratio"],
                    contributing_n=min(int(adjusted["n cases"]),
                                       int(adjusted["n clusters"])))
                if adjusted["step ratio"]["refused for separation"]:
                    detail.setdefault("fits refused at the ceiling", []).append(
                        "adjusted_conditional_logistic_model")
            except ModelDidNotConverge as failure:
                reason = _record_model_failure(
                    detail, "adjusted failure", "adjusted_conditional_logistic_model", failure)
                estimates["adjusted_odds_per_lower_step_ratio"] = suppressed_node(reason)

        if permitted_at("observation_weighted_sensitivity", index):
            try:
                weights = observation_weights(members)
                weighted_frame = weights["frame"]
                weighted_frame = weighted_frame[
                    ~pd.Series(weighted_frame["no_computable_step_signal"]).astype(bool)]
                sensitivity = conditional_association(
                    weighted_frame.reset_index(drop=True), adjusted=True,
                    set_weights=weights["set weight"],
                    n_resamples=BOOTSTRAP_RESAMPLES_SENSITIVITY)
                detail["observation weights"] = {
                    key: weights[key] for key in
                    ("marginal probability", "truncation lower", "truncation upper",
                     "weight mean", "weight minimum", "weight maximum",
                     "n weighted members", "n weighted sets", "design names")}
                detail["weighted sensitivity"] = sensitivity
            except (ModelDidNotConverge, GateError) as failure:
                if isinstance(failure, ModelDidNotConverge):
                    _record_model_failure(detail, "weighted sensitivity failure",
                                          "observation_weighted_sensitivity", failure)
                else:
                    detail["weighted sensitivity failure"] = str(failure)

        if permitted_at("negative_control_window", index):
            control = frames["negative control frame"]
            if control.empty:
                estimates["negative_control_window"] = suppressed_node(
                    "not_estimable_data_unavailable")
            else:
                try:
                    fitted = conditional_association(
                        control, adjusted=False, ratio_column="negative_control_ratio",
                        no_signal_column="no_computable_negative_control",
                        n_resamples=BOOTSTRAP_RESAMPLES_SENSITIVITY)
                    detail["negative control"] = fitted
                    estimates["negative_control_window"] = _odds_ratio_node(
                        fitted["step ratio"],
                        contributing_n=min(int(fitted["n cases"]), int(fitted["n clusters"])))
                    if fitted["step ratio"]["refused for separation"]:
                        detail.setdefault("fits refused at the ceiling", []).append(
                            "negative_control_window")
                except ModelDidNotConverge as failure:
                    reason = _record_model_failure(
                        detail, "negative control failure", "negative_control_window", failure)
                    estimates["negative_control_window"] = suppressed_node(reason)

    # ---- the complementary full-cohort model, which is where absolute risks come from -----
    if permitted_at("absolute_risk_translation", index):
        panel = frames["discrete time panel"]
        disagree = int(pd.to_numeric(panel["window_disagrees"], errors="coerce").fillna(0).sum())
        if disagree:
            halting.append(
                "the proximal window rebuilt on the day grid disagrees with the panel's own "
                "valid-day count on at least one episode-day, so the exposure computed here is "
                "not the exposure the derived tables carry"
            )
        try:
            built = discrete_time_design(panel)
            kept = built["frame"]
            fit = fit_pooled_logit(
                built["design"],
                pd.to_numeric(kept["outcome"], errors="coerce").fillna(0).to_numpy(dtype=float),
                pd.to_numeric(kept["cluster_index"],
                              errors="coerce").astype("int64").to_numpy())
            low = standardized_risk(fit, built["design"], built["exposure offset"],
                                    ratio=ABSOLUTE_RISK_ANCHOR)
            reference = standardized_risk(fit, built["design"], built["exposure offset"],
                                          ratio=STEP_RATIO_REFERENCE)
            detail["discrete time"] = {
                "fit": fit,
                "names": built["names"],
                "n structurally uncomputable days dropped":
                    built["n structurally uncomputable days dropped"],
                "risk at the low ratio": low,
                "risk at the reference ratio": reference,
            }
            contributing = min(int(fit["n events"]), int(fit["n clusters"]))
            estimates["absolute_risk_translation"] = estimate_node(
                low["risk"] * 100.0, low["lower"] * 100.0, low["upper"] * 100.0,
                unit="percent", contributing_n=contributing,
                decimals=ABSOLUTE_RISK_DECIMALS)
            extra["absolute_risk_at_the_reference_ratio"] = estimate_node(
                reference["risk"] * 100.0, reference["lower"] * 100.0,
                reference["upper"] * 100.0, unit="percent", contributing_n=contributing,
                decimals=ABSOLUTE_RISK_DECIMALS)

            if permitted_at("performance_panel", index):
                predicted = np.asarray(fit["fitted"], dtype=float)
                observed = pd.to_numeric(kept["outcome"],
                                         errors="coerce").fillna(0).to_numpy(dtype=float)
                panel_metrics = performance_panel(predicted, observed)
                detail["performance"] = panel_metrics
                lead = lead_time_hours(kept, predicted, panel_metrics["threshold"])
                detail["lead time"] = lead
                estimates["median_lead_time"] = quantile_node(
                    lead["hours"], unit="hours",
                    contributing_n=int(lead["n with an alert"]))
        except ModelDidNotConverge as failure:
            reason = _record_model_failure(detail, "discrete time failure",
                                            "absolute_risk_translation", failure)
            estimates["absolute_risk_translation"] = suppressed_node(reason)
            if permitted_at("median_lead_time", index):
                estimates["median_lead_time"] = suppressed_node(reason)

    # ---- ANALYSIS-PLAN 4.9's two obliged counts, reported whether or not the ceiling fired ---
    # "Both are counts and never estimates, both are subject to the disclosure floor of section
    # 8, and both are reported whether or not the ceiling ever fires, because a rule that
    # prints nothing when it does not fire is a rule a reader cannot confirm ran at all."
    ceiling_ledger: dict[str, Any] = {
        "ceiling": MAX_ABS_COEFFICIENT,
        "share": BOOTSTRAP_MAX_FAILURE_SHARE,
        "refused fits": sorted(set(detail.get("fits refused at the ceiling", []))),
        "by fit": [],
    }
    for label, key in (("Unadjusted association", "unadjusted"),
                       ("Adjusted conditional model", "adjusted"),
                       ("Observation-weighted sensitivity", "weighted sensitivity"),
                       ("Negative control window", "negative control")):
        fitted = detail.get(key)
        if not fitted:
            continue
        # ONE ROW PER FIT, not per contrast.  Whether a resample sat above the ceiling is a
        # property of the REFIT, so both contrasts of one fit read the same resamples and would
        # print the same count twice, which reads as two measurements where there is one.
        row = fitted.get("step ratio")
        if not row or "resamples above ceiling" not in row:
            continue
        ceiling_ledger["by fit"].append({
            "fit": label,
            "n above": int(row["resamples above ceiling"]),
            "n with a value": int(row["resamples with a value"]),
            "share": float(row["share above ceiling"]),
            "refused": bool(fitted["step ratio"]["refused for separation"]
                            or fitted["no computable step signal"]["refused for separation"]),
        })
    detail["coefficient ceiling"] = ceiling_ledger

    # STOP CONDITION 11 of ANALYSIS-PLAN section 11: "a fit above the coefficient ceiling of
    # 4.9 reached an exported surface".  Checked rather than trusted.  A refused point fit
    # never returns from the fitter at all, so the only route to an exported number is rule 3's
    # share, and this asserts that every row rule 3 refused is in fact carrying the separation
    # sentence and not a value.
    _emitted = {**estimates, **extra}
    # Which exported key each refusable contrast feeds.  Written out rather than derived, so a
    # key added later without a row here fails this check by absence rather than passing it by
    # accident.  The weighted sensitivity feeds no exported key and appears in the detail only.
    _FED_BY: Mapping[tuple[str, str], str] = MappingProxyType({
        ("unadjusted", "step ratio"): "unadjusted_odds_per_lower_step_ratio",
        ("unadjusted", "no computable step signal"): "odds_of_no_computable_step_signal",
        ("adjusted", "step ratio"): "adjusted_odds_per_lower_step_ratio",
        ("negative control", "step ratio"): "negative_control_window",
    })
    for _key, _label in (("unadjusted", "Unadjusted association"),
                         ("adjusted", "Adjusted conditional model"),
                         ("negative control", "Negative control window")):
        fitted = detail.get(_key)
        if not fitted:
            continue
        for contrast in ("step ratio", "no computable step signal"):
            row = fitted.get(contrast)
            if not row or not row.get("refused for separation"):
                continue
            name = _FED_BY.get((_key, contrast))
            node = _emitted.get(name) if name else None
            if node is not None and not node.get("suppressed"):
                halting.append(
                    f"the {_label.lower()} was refused under the coefficient ceiling of "
                    f"ANALYSIS-PLAN 4.9 and a number from it still reached an exported "
                    f"surface. That is stop condition 11: a refusal is reported as a refusal "
                    f"with its named reason, and a clipped value is never substituted for one"
                )

    gate = build_gate_block(stages, tier, estimates)
    return {
        "gate": gate,
        "tier": dict(tier),
        "stages": stages,
        "estimates": estimates,
        "estimates extra": extra,
        # BESIDE the gate block, under the name `07_export.py` refuses Table 4 without. It
        # takes these as `window_counts=` on `render_table4_rows`, keyed by window group, each
        # with `episode_days` and `events`, and the key is spelled the way the consumer spells
        # its parameter so the hand-off cannot be got subtly wrong.
        "table4_window_counts": window_counts,
        "detail": detail,
        "refused": refusals_for_tier(index),
        "permitted": permitted_for_tier(index),
        "halting": halting,
        "gate ok": not halting,
    }


# ======================================================================================
# (17) Rendering.  Every human-visible string is built here and the house prose rules are
#      asserted on the RENDERED text, not grepped for afterwards.
#
#      Three rules bind every line below.  No em-dash and no Unicode minus anywhere.  No
#      machine token in a user-visible string, which is why the refusal ledger prints display
#      labels and never slugs.  And every table prints its own denominator, which for a gate
#      whose deciding count may itself be unprintable means the denominator line sometimes
#      reads as the suppression sentence, and that is the correct output rather than a gap.
# ======================================================================================

_SNAKE_TOKEN = re.compile(r"\b[a-z0-9]+_[a-z0-9_]*\b")
_RULE = "=" * 86
_THIN = "-" * 86


def _assert_house_prose(text: str) -> None:
    """Stop conditions on the rendered report, checked before a character of it is printed."""
    if EM_DASH in text:
        raise GateError("the report contains an em-dash, which no house string may carry")
    if MINUS_SIGN in text:
        raise GateError("the report contains a Unicode minus sign, which is banned")
    snake = sorted(set(_SNAKE_TOKEN.findall(text)))
    if snake:
        raise GateError(
            f"the report contains machine token(s) {snake}, and an identifier is never a "
            f"user-visible string. Use the display label beside it."
        )


def _wrap(text: str, width: int = 84) -> list[str]:
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


# The reasons that are a DISCLOSURE decision rather than a design decision.  In a terminal
# table they all render as one short sentinel, both so a wide ledger stays readable and because
# collapsing them hides WHICH cell was primarily suppressed, which is more protective and not
# less.  `results.json` keeps the distinct reason on every node; only this rendering collapses
# them, and the full sentence is printed once under any table that carries one.
_DISCLOSURE_REASONS: tuple[str, ...] = (
    "cell_below_threshold", "secondary_suppression", "contributing_n_below_threshold",
    "numerator_suppressed",
)


def _cell(node: Mapping[str, Any]) -> str:
    """One node rendered for a fixed-width table rather than for prose."""
    if node.get("suppressed") and node.get("reason") in _DISCLOSURE_REASONS:
        return SUPPRESSED
    return shown(node)


def _suppression_footnote(nodes: Sequence[Mapping[str, Any]]) -> list[str]:
    """The full suppression sentence, printed once under a table that hid something."""
    reasons = {node.get("reason") for node in nodes
               if node.get("suppressed") and node.get("reason") in _DISCLOSURE_REASONS}
    if not reasons:
        return []
    out = [f"Hidden cells read {SUPPRESSED} and mean: "
           f"{SUPPRESSION_REASONS['cell_below_threshold']}."]
    if "secondary_suppression" in reasons:
        out.append("At least one cell was hidden a second time, to stop a hidden neighbour "
                   "being recovered by subtraction from a disclosed total.")
    if "contributing_n_below_threshold" in reasons:
        out.append("At least one estimate was hidden because the count of participants behind "
                   "it is below the floor, not because of its own value.")
    return out


def shown(node: Mapping[str, Any]) -> str:
    """The one string that may reach a rendered surface.  Always safe to print.

    A renderer that prints this is correct for a disclosed node and for a suppressed node
    without branching, because a suppressed node's display string IS the suppression sentence.
    """
    return str(node["display"])


def render_report(result: Mapping[str, Any]) -> str:
    """The whole gate report, as one string, ending in the verdict.

    Built as a string and checked before it is printed, so the house rules are asserted on the
    characters a human would read rather than grepped for afterwards.
    """
    lines: list[str] = []
    add = lines.append
    tier = result["tier"]
    gate = result["gate"]
    detail = result["detail"]
    stages = {stage["letter"]: stage for stage in result["stages"]}

    add(_RULE)
    add("ARM A, THE EARLY-WARNING GATE. The tier is read from a count and from nothing else.")
    add(_RULE)
    add("")
    lines += _wrap(
        "The protocol's decision table binds what may be attempted to the number of usable "
        "acute-care events. That number is a count, it is computed before any model is fitted, "
        "and it is the only thing consulted in deciding what runs. Everything the tier forbids "
        "is listed by name at the end of this report, so an absence here is a printed row "
        "rather than something a reader has to notice.")
    add("")

    # ---- 1. the gate, and the count that may or may not be printable ----
    add(_THIN)
    add("1. THE GATE")
    add(_THIN)
    deciding = stages[GATE_DECIDING_STAGE]["total"]
    for label, value in (
        ["Deciding quantity", GATE_STAGE_DEFINITIONS[GATE_DECIDING_STAGE]],
        ["Deciding count", shown(deciding)],
        ["Tier reached", tier["display_label"]],
        ["Tier band", tier["band_display"]],
        ["Exhibit set", tier["exhibit_set"]],
    ):
        lines += _wrap(f"{label}: {value}", 84)
    # The two verbatim rows are printed WHOLE and are never re-flowed.  A quoted claim broken
    # across lines by a wrapper is no longer quotable, and these two are the strings the
    # manuscript copies without alteration.
    add("Permitted analysis, verbatim from the prespecified decision table:")
    add(f"    {tier['permitted_analysis_verbatim']}")
    add("Permitted claim, verbatim from the prespecified decision table:")
    add(f"    {tier['permitted_claim_verbatim']}")
    add("")
    if not tier["event_count_printable"]:
        lines += _wrap(
            "THE DECIDING COUNT IS NOT PRINTABLE, AND THE TIER STILL IS. The lowest tier "
            "boundary and the All of Us disclosure floor are both 20 events. The two are "
            "unrelated in origin and identical in value, so a gate at or below that value "
            "reports its tier and reports its count as suppressed. This is written into the "
            "prespecification rather than discovered at proof stage, and the Methods sentence "
            "for it was drafted before any count existed.")
        add("")
    if int(tier["index"]) == 3 and not tier["event_count_printable"]:
        lines += _wrap(
            "AND THIS IS THE ONE-COUNT CASE THE PLAN NAMES. A gate of exactly 20 events sits "
            "in the third tier, where event-centered association and visualization are "
            "permitted, and simultaneously at the top of the suppressed band, where the count "
            "may not be disclosed. The analysis runs and its denominator does not appear.")
        add("")
    lines += _wrap(f"Why this tier: {gate['arm_a']['reason_display']}", 84)
    add("")

    # ---- 2. the A through F ledger ----
    add(_THIN)
    add("2. THE FEASIBILITY LEDGER, STAGE A THROUGH STAGE F")
    add(_THIN)
    group_slugs = list(detail["ladder"]["groups"])
    headers = ["Stage", "Required count"] + [GROUP_LABELS[slug] for slug in group_slugs] \
        + ["All groups"]
    body: list[list[str]] = []
    printed: list[Mapping[str, Any]] = []
    for letter in GATE_STAGE_LETTERS:
        stage = stages[letter]
        cells = [letter, stage["display_label"]]
        if stage["by_group"]:
            cells += [_cell(stage["by_group"][slug]) for slug in group_slugs]
            printed += [stage["by_group"][slug] for slug in group_slugs]
        else:
            cells += [""] * len(group_slugs)
        cells.append(_cell(stage["total"]))
        printed.append(stage["total"])
        body.append(cells)
        if stage["components"]:
            for part in STAGE_D_COMPONENTS:
                body.append(["", STAGE_D_COMPONENT_LABELS[part]] + [""] * len(group_slugs)
                            + [_cell(stage["components"][part])])
                printed.append(stage["components"][part])
    lines += _table_lines(headers, body, align="ll" + "r" * (len(group_slugs) + 1))
    add(f"Denominator: the analytic cohort, {len(group_slugs)} procedure groups.")
    lines += _suppression_footnote(printed)
    add("")
    # The protocol's own required-count wording, which is what the exported table prints as its
    # row definition, is listed rather than set as a column: at full width it makes the ledger
    # unreadable in a terminal and the exported file is where it belongs.
    add("The protocol's required count for each stage, verbatim:")
    for letter in GATE_STAGE_LETTERS:
        lines += _wrap(f"  {letter}. {GATE_STAGE_DEFINITIONS[letter]}", 84)
    add("")
    lines += _wrap(
        "The three components of the fourth stage are not a partition. An emergency visit that "
        "becomes a same-day admission is one composite event and appears in both of the first "
        "two counts, which is why the plan collapses it to one event and why the gate reads "
        "the composite row rather than a sum.")
    add("")
    if any(stages["F"]["by_group"][slug]["suppressed"] for slug in group_slugs):
        lines += _wrap(
            "Stage F prints as suppressed in every stratum, and that is the ANTICIPATED "
            "outcome rather than a failure. It prints as suppressed unless every cell is "
            "disclosable, because a single disclosed cell alongside suppressed ones plus a "
            "disclosed total recovers the suppressed cells by subtraction. The plan says in "
            "advance that this is what will happen.")
        add("")

    # ---- 3. the two landmark conditions, which are never summed ----
    add(_THIN)
    add("3. THE TWO LANDMARK CONDITIONS, KEPT APART")
    add(_THIN)
    timing = detail["timing"]
    first, last = timing["derived range"]
    # COMPLEMENTARY SUPPRESSION, the same rule the stage tables above already run through.
    # These three counts PARTITION the first events and the partition's own total is printed
    # directly below as the denominator, so one suppressed cell beside two disclosed ones plus
    # that total gives the hidden count back by subtraction.  `round20` bounds what the
    # subtraction recovers and this table is report-only, so nothing here crosses the
    # disclosure boundary; it was still an inconsistency inside one module, applying a rule at
    # one table and not at the next one down the page, and the fix is the function the module
    # already has rather than a second rule written for this table.
    condition_suppressed = complementary_suppression({
        "definitional": timing["n structurally deleted"],
        "data": timing["n data uncomputable"],
        "computable": timing["n computable"],
    })
    condition_nodes = [condition_suppressed["definitional"], condition_suppressed["data"],
                       condition_suppressed["computable"]]
    rows = [
        [LANDMARK_CONDITION_LABELS["definitional"],
         LANDMARK_CONDITION_DISPOSITION["definitional"], _cell(condition_nodes[0])],
        [LANDMARK_CONDITION_LABELS["data"],
         LANDMARK_CONDITION_DISPOSITION["data"], _cell(condition_nodes[1])],
        ["A computable window", "Enters the exposure as a ratio", _cell(condition_nodes[2])],
    ]
    lines += _table_lines(["Condition", "Where it goes", "First events"], rows,
                          align="llr")
    add(f"Denominator: first acute-care events, {shown(count_node(timing['n first events']))}.")
    lines += _suppression_footnote(condition_nodes)
    add("")
    lines += _wrap(
        "THESE COUNTS ARE NEVER SUMMED. The first is definitional and those events leave the "
        "study at the exclusion rung that exists for them; the second is a data condition and "
        "those windows stay, entering the model as the co-primary exposure. A single number "
        "over both would be the sum of an exclusion and an exposure, and no reader could take "
        "it apart again afterwards.")
    add("")
    lines += _wrap(
        f"The definitional range is post-discharge day {first} to {last}, derived from the "
        f"plan's own two-valid-day rule and checked against the derived flag on every first "
        f"event rather than transcribed. The first eligible landmark is post-discharge day "
        f"{FIRST_ELIGIBLE_LANDMARK_DAY}, belonging to an event on post-discharge day "
        f"{FIRST_ELIGIBLE_EVENT_DAY}; the first fully post-discharge window belongs to an "
        f"event on day {FIRST_FULLY_POST_DISCHARGE_EVENT_DAY}. Any document writing day 1 to 3 "
        f"is corrected against that derivation.")
    add("")
    if timing["by day"]:
        day_nodes = [count_node(n) for _, n in sorted(timing["by day"].items())]
        rows = [[str(day), _cell(node)]
                for (day, _), node in zip(sorted(timing["by day"].items()), day_nodes)]
        lines += _table_lines(["Post-discharge day of the deleted event", "Events"], rows)
        add(f"Denominator: events with no computable window, "
            f"{shown(count_node(timing['n structurally deleted']))}.")
        lines += _suppression_footnote(day_nodes)
        add("")
        lines += _wrap(
            "The deleted events are the earliest ones, and earliest is a proxy for most "
            "severe. A reader is told that the analysis is blind to the first days after "
            "discharge by construction, and how many events that cost.")
        add("")
    lines += _render_collider(result)
    lines += _render_matched_sets(result)
    lines += _render_estimates(result)
    lines += _render_refusals(result)
    lines += _render_contract_gaps(result)
    lines += _render_verdict(result)
    text = "\n".join(lines)
    _assert_house_prose(text)
    return text


def _rate(value: float) -> str:
    """One event rate per thousand episode-days, or the suppression sentence."""
    return f"{value:.{RATE_DECIMALS}f}" if np.isfinite(value) else SUPPRESSED


def _render_collider(result: Mapping[str, Any]) -> list[str]:
    """The collider evidence, crude and standardized, and the sentence that is NOT made."""
    detail = result["detail"]
    lines: list[str] = [_THIN, "4. THE OUTCOME RATE WITH AND WITHOUT A COMPUTABLE STEP SIGNAL",
                        _THIN]
    if "landmark comparison" not in detail:
        lines += _wrap(
            "Not computed. The tier reached does not permit it, and it is listed by name in "
            "the refusal ledger below. At the lowest tier every cell of this comparison would "
            "in any case fall below the disclosure floor, because its numerator is the event "
            "count that put the study in that tier.")
        lines.append("")
        return lines
    comparison = detail["landmark comparison"]
    rows: list[list[str]] = []
    hidden: list[Mapping[str, Any]] = []
    for name in ("computable", "data"):
        condition = comparison["conditions"][name]
        events = count_node(condition["n event days"])
        label = ("A computable window" if name == "computable"
                 else LANDMARK_CONDITION_LABELS["data"])
        rows.append([label, _cell(count_node(condition["n episode days"])), _cell(events),
                     _rate(condition["crude rate"]), _rate(condition["standardized rate"])])
        hidden.append(events)
    lines += _table_lines(
        ["Condition", "Episode days", "Event days", "Crude rate", "Standardized rate"],
        rows, align="lrrrr")
    lines += _suppression_footnote(hidden)
    lines.append(f"Denominator: every uncensored episode day in the analytic cohort, "
                 f"{shown(count_node(comparison['n episode days']))}. Rates are events per "
                 f"{comparison['rate denominator']:,} episode days.")
    lines += _suppression_footnote(hidden)
    lines.append("")
    lines += _wrap(
        f"Every rate above is computed from the ROUNDED event count over the ROUNDED day "
        f"count, so each is reproducible from the two numbers beside it and none of them can "
        f"be multiplied back into a hidden count. The standardization runs over the "
        f"{comparison['n bands']} prespecified recovery bands rather than day by day, and it "
        f"is suppressed unless every contributing band clears the floor: a rate standardized "
        f"day by day is a weighted average of per-day event counts that are individually below "
        f"the floor, and it would carry them inside it.")
    lines.append("")
    definitional = comparison["conditions"]["definitional"]
    lines += _wrap(
        f"The definitional condition, which is the earliest days after discharge, holds "
        f"{shown(count_node(definitional['n episode days']))} episode days and is NOT part of "
        f"this comparison. It is printed here so a reader can see it is excluded rather than "
        f"folded in. Its count is never added to the row above it.")
    lines.append("")
    lines += _wrap(
        "NEITHER VERSION IS A CAUSAL ESTIMATE AND NEITHER IS LABELLED ONE. The comparison is "
        "unmatched and descriptive: post-discharge day drives both wear and events, and this "
        "panel controls for nothing. It is reported twice, crude and directly standardized to "
        "the post-discharge-day distribution of the analytic cohort, with the standardization "
        "weights fixed by that distribution and by nothing else. If the two agree, "
        "post-discharge day is not doing the work; if they disagree, the reader is shown by "
        "how much rather than told which to believe. This is the EVIDENCE about the collider "
        "concern. The CORRECTION for it is the co-primary exposure.")
    lines.append("")
    lines += _wrap(
        "It is computed on the full-cohort day-indexed panel and not at the sampled matched "
        "sets, because the sampling caps, the fixed control ratio and the day-of-week matching "
        "all select on the very variable this comparison is about. A comparison taken there "
        "would compare windows that already survived the selection it exists to expose.")
    lines.append("")
    return lines


def _render_matched_sets(result: Mapping[str, Any]) -> list[str]:
    """The matched sets, and the three counts the early-landmark weight rule obliges."""
    detail = result["detail"]
    lines: list[str] = [
        _THIN,
        "5. THE MATCHED SETS, THE EARLY-LANDMARK RULE, AND THE EVENT-CENTERED CURVE",
        _THIN]
    if "matched set sizes" in detail:
        sizes = detail["matched set sizes"]
        node = result["estimates"].get("matched_set_size")
        lines += _wrap(
            f"Controls per case: {shown(node) if node else SUPPRESSED}. Denominator: "
            f"{shown(count_node(sizes['n sets']))} matched sets, one case each.")
        lines.append("")
    if "early landmark" not in detail:
        lines += _wrap(
            "The matched-set model frame was not read at this tier, so the early-landmark "
            "weight rule has nothing to act on and no counts to report.")
        lines.append("")
        return lines
    counts = detail["early landmark"]
    lines += _wrap(
        "THE RULE. A member is weighted when its own landmark day is 2 or more. A member whose "
        "landmark day is 1 or less leaves the WEIGHTED SENSITIVITY and nothing else: it stays "
        "in the primary, it stays in its matched set, and if its window holds fewer than the "
        "minimum valid days it still carries the co-primary exposure, which is the estimand "
        "that exists to keep exactly these members visible. The rule's whole cost is a count, "
        "and here is the count.")
    lines.append("")
    rows = []
    for route in EARLY_LANDMARK_ROUTES:
        for role in MEMBER_ROLES:
            n = counts["by route"][route][role]
            if n == 0:
                continue
            rows.append([EARLY_LANDMARK_ROUTE_LABELS[route], MEMBER_ROLE_LABELS[role],
                         _cell(count_node(n))])
    if not rows:
        rows = [["No member reached a landmark day of 1 or less", "", _cell(count_node(0))]]
    lines += _table_lines(["Route", "Role", "Members"], rows, align="llr")
    lines.append(f"Denominator: every matched-set member, "
                 f"{shown(count_node(counts['n members']))}.")
    lines.append("")
    rows = [
        ["Matched sets that lose every control",
         _cell(count_node(counts["n sets losing every control"]))],
        ["Matched sets that lose their case",
         _cell(count_node(counts["n sets losing their case"]))],
        ["Weighted sensitivity denominator, sets",
         _cell(count_node(counts["n weighted sets"]))],
        ["Weighted sensitivity denominator, members",
         _cell(count_node(counts["n weighted members"]))],
    ]
    lines += _table_lines(["Quantity", "Count"], rows)
    lines.append(f"Denominator: every matched set, {shown(count_node(counts['n sets']))}.")
    lines.append("")
    lines += _wrap(
        "A set that loses every control leaves the conditional likelihood altogether, because "
        "a set with no control contributes nothing to it. That is the count that turns a "
        "member-level exclusion into an analysis-level one, and it cannot be recovered from "
        "the member count above.")
    lines.append("")
    if "structural members" in detail:
        structural = detail["structural members"]
        lines += _wrap(
            "THE SAME MEMBERS, COUNTED ONCE. A landmark day of 1 or less is not a threshold "
            "beside the definitional condition; it is the definitional condition written in "
            "landmark-day terms, so the members above are also the members with no exposure "
            "window at all. They carry no exposure coefficient, and they are dropped from the "
            "conditional model frame before it is fitted rather than admitted with the "
            "no-signal indicator set, which would put an exclusion inside an exposure. The "
            "count is the one already printed above and is deliberately not printed a second "
            "time under a second label, because two labels over one quantity is an invitation "
            "to add them together. The models below therefore print their own denominators.")
        lines.append("")
        if structural["violations"]:
            lines += _wrap("The definitional flag and the landmark day it is arithmetic on "
                           "disagree on at least one member, which is a halting condition and "
                           "is reported with the others.")
            lines.append("")
    if "observation weights" in detail:
        weights = detail["observation weights"]
        rows = [
            ["Marginal observation probability", f"{weights['marginal probability']:.3f}"],
            ["Weight mean", f"{weights['weight mean']:.3f}"],
            ["Weight range", f"{weights['weight minimum']:.3f} to "
                             f"{weights['weight maximum']:.3f}"],
            ["Truncation points", f"{weights['truncation lower']:.3f} to "
                                  f"{weights['truncation upper']:.3f}"],
        ]
        lines += _table_lines(["Observation weight", "Value"], rows)
        lines.append(f"Denominator: weighted members, "
                     f"{shown(count_node(weights['n weighted members']))}.")
        lines.append("")
    elif "weighted sensitivity failure" in detail:
        lines += _wrap("The weighted sensitivity did not fit, and is reported as not "
                       "estimable rather than omitted.")
        lines.append("")
    lines += _render_event_centered_denominator(detail)
    return lines


def _render_event_centered_denominator(detail: Mapping[str, Any]) -> list[str]:
    """Figure 4's own denominator, and the members the structural filter removed.

    THE FIGURE IS DRAWN OVER THE MODEL'S POPULATION AND SAYS SO.  ANALYSIS-PLAN 4.4 puts a
    member whose landmark window holds fewer than 2 post-discharge days outside the co-primary
    exposure "on every surface" and names the risk-set table among them, so the curve carries
    the same filter the fits do.  A figure whose population differs from the model's, without
    saying so, is the first question a reviewer asks and the one the paper would not be able to
    answer; and the members it would have admitted are the earliest ones, which 4.3 argues are
    a proxy for the sickest, so the difference would not even be a neutral one.

    The filter's whole cost is a count, and this is where the count is printed, which is the
    same treatment 4.4 gives its own member-level drop two tables above.  Both counts are
    MEMBERS and not episodes, because a member is the unit those obliged counts use and one
    episode can be a member of several sets.
    """
    curve = detail.get("event centered curve")
    if curve is None or getattr(curve, "empty", True):
        return []
    lines: list[str] = _wrap(
        "THE EVENT-CENTERED CURVE IS DRAWN OVER THE SAME MEMBERS THE MODEL FITS. A member with "
        "no exposure window is outside the co-primary exposure on every surface, which "
        "ANALYSIS-PLAN 4.4 enumerates and which includes the risk-set table this curve reads, "
        "so it is filtered here too rather than kept on the ground that a curve estimates "
        "nothing. The members it would otherwise have admitted are the earliest ones, and a "
        "curve drawn over a population the estimate beside it excluded would answer a "
        "different question from the one it appears to answer.")
    lines.append("")
    rows: list[list[str]] = []
    nodes: list[Mapping[str, Any]] = []
    total = 0
    for role in MEMBER_ROLES:
        block = curve[curve["member_role"] == role]
        if block.empty:
            continue
        in_curve = int(pd.to_numeric(block["n_members_in_curve"], errors="coerce").iloc[0])
        dropped = int(
            pd.to_numeric(block["n_members_dropped_structural"], errors="coerce").iloc[0])
        total += in_curve + dropped
        in_node, dropped_node = count_node(in_curve), count_node(dropped)
        nodes += [in_node, dropped_node]
        rows.append([MEMBER_ROLE_LABELS[role], _cell(in_node), _cell(dropped_node)])
    if not rows:
        return []
    lines += _table_lines(
        ["Role", "Members plotted", "Members with no exposure window, dropped"],
        rows, align="lrr")
    lines += _suppression_footnote(nodes)
    lines.append(f"Denominator: every risk-set member before the filter, "
                 f"{shown(count_node(total))}.")
    lines.append("")
    return lines


def _render_estimates(result: Mapping[str, Any]) -> list[str]:
    """The estimates, ABSOLUTE BEFORE RELATIVE, per the house numeral style."""
    lines: list[str] = [_THIN, "6. WHAT THE TIER PERMITTED, AS NUMBERS", _THIN]
    gate = result["gate"]
    if not gate["arm_a"]["permitted"]:
        lines += _wrap(gate["arm_a"]["reason_display"])
        lines.append("")
        lines += _wrap(
            "Arm A carries no estimate at this tier. That is a decision the protocol made "
            "before this study saw a number, and the gate is still the study's secondary "
            "result: in a nationally recruited, linked, consumer-wearable cohort, the number "
            "of surgical episodes with simultaneous adequate preoperative baseline wear, a "
            "computable post-discharge signal and an observable acute-care event is this "
            "small. That is a reportable finding about the data source.")
        lines.append("")
        return lines
    detail = result["detail"]
    # ALL THIRTEEN OF 3.7's KEYS, ABSOLUTE BEFORE RELATIVE. The six collider rows repeat the
    # comparison section 4 already printed with its own denominators; they are here as well
    # because this table is the estimates BLOCK, and a block that prints twelve of its
    # thirteen rows is a table a reader has to know is incomplete.
    ordered = ["absolute_risk_translation", "median_lead_time",
               "collider_rate_with_signal", "collider_rate_without_signal",
               "collider_rate_with_signal_standardized",
               "collider_rate_without_signal_standardized",
               "collider_rate_ratio_crude", "collider_rate_ratio_standardized",
               "unadjusted_odds_per_lower_step_ratio",
               "odds_of_no_computable_step_signal",
               "adjusted_odds_per_lower_step_ratio", "negative_control_window",
               "matched_set_size"]
    rows = []
    for key in ordered:
        node = gate["arm_a"]["estimates"][key]
        rows.append([ESTIMATE_KEY_LABELS[key], shown(node)])
    for key, node in result["estimates extra"].items():
        label = key.replace("_", " ").replace("odds ", "odds ")
        rows.append([label.capitalize(), shown(node)])
    lines += _table_lines(["Quantity", "Estimate (95% CI)"], rows)
    contributing = detail.get("adjusted", detail.get("unadjusted"))
    if contributing:
        lines.append(f"Denominator: {shown(count_node(int(contributing['n sets'])))} matched "
                     f"sets over {shown(count_node(int(contributing['n clusters'])))} "
                     f"participants.")
    lines.append("")
    # ANALYSIS-PLAN 4.9's two obliged counts, PRINTED WHETHER OR NOT THE CEILING FIRED.
    ledger = detail.get("coefficient ceiling")
    if ledger:
        lines += _wrap(
            f"THE COEFFICIENT CEILING OF ANALYSIS-PLAN 4.9. Every logistic fit in this arm is "
            f"refused whole when any one of its coefficients exceeds "
            f"{ledger['ceiling']:g} on the log-odds scale, an odds ratio of about 22,026, "
            f"which is the conventional separation-detection threshold. The refusal replaces a "
            f"number with a named absence and has no branch that emits, widens, narrows or "
            f"changes an estimate, so it cannot move any published number toward the null or "
            f"away from it. Its whole cost is a count, and here are both counts the plan "
            f"obliges, printed whether or not the ceiling fired.")
        lines.append("")
        # BOTH COUNTS GO THROUGH THE SECTION 8 FLOOR, because 4.9 says they are "subject to the
        # disclosure floor of section 8".  Two consequences follow and both are handled here
        # rather than left to be noticed.  The refused analyses are NOT listed by name beside a
        # suppressed count, because counting the names recovers the count exactly; a reader who
        # wants to know WHICH rows were refused reads the estimates table above, where each
        # refused row already prints the separation sentence in its own place.  And the SHARE
        # is not printed beside a suppressed count either, because the share times the printed
        # denominator recovers the count just as directly.
        refused_nodes = [count_node(len(ledger["refused fits"]))]
        lines += _table_lines(
            ["Fits refused at the ceiling", "Count"],
            [["Every analysis in this arm", _cell(refused_nodes[0])]], align="lr")
        lines += _suppression_footnote(refused_nodes)
        lines += _wrap(
            "Which rows those are is not listed here. Counting a list of names beside a "
            "suppressed count gives the count back, and each refused row already carries the "
            "separation sentence in the estimates table above, which is where a reader meets "
            "it in its own place rather than in a second ledger.")
        lines.append("")
        if ledger["by fit"]:
            rows, nodes = [], []
            for row in ledger["by fit"]:
                above = count_node(row["n above"])
                total = count_node(row["n with a value"])
                nodes += [above, total]
                # ANALYSIS-PLAN 8 rule 4, the same rule `_rate_from_rounded` applies to a rate:
                # the share is computed from the ROUNDED pair, so a reader multiplying it by
                # the printed denominator recovers the printed numerator and not the true one.
                if above["suppressed"] or total["suppressed"] or not total["n"]:
                    share_cell = _cell(above)
                else:
                    share_cell = f"{float(above['n']) / float(total['n']):.1%}"
                rows.append([row["fit"], _cell(above), share_cell,
                             "refused" if row["refused"] else "reported", _cell(total)])
            lines += _table_lines(
                ["Fit", "Above the ceiling", "Share", "Interval", "Resamples with a value"],
                rows, align="lrrlr")
            lines.append("Denominator: each row's own resamples that produced a value, in the "
                         "last column.")
            lines += _suppression_footnote(nodes)
            lines += _wrap(
                "Each share is computed from the two rounded counts printed beside it, never "
                "from the true pair, so multiplying it by the denominator gives the printed "
                "numerator back rather than the hidden one. Where the numerator is below the "
                "floor the share is withheld with it, because a share over a printed "
                "denominator hands back exactly what the floor withheld.")
            lines.append("")
        lines += _wrap(
            f"A resample above the ceiling is RETAINED in the resample distribution and "
            f"counted, never discarded. Discarding the resamples that ran furthest from zero "
            f"would trim exactly the tail the percentile interval is read from and would "
            f"therefore narrow a published interval, which is the one thing this rule must "
            f"never do. Where more than {ledger['share']:.0%} of a fit's resamples sat above "
            f"the ceiling, the interval AND the point estimate are both refused with the "
            f"separation reason, even where the point fit itself was below it: an interval "
            f"read off a resample distribution that separated in a quarter of its draws is "
            f"not an interval on the quantity the row claims to report.")
        lines.append("")
        lines += _wrap(
            "The value that tripped the ceiling is not printed, here or anywhere else, as a "
            "bound or in a footnote. Printing it would put a number this study did not "
            "estimate where a refusal belongs, which is the clipped estimate arriving by a "
            "second route. A fit BELOW the ceiling with a very wide interval still prints, and "
            "the width of that interval is the reader's own signal; the ceiling bounds what "
            "can be exported and does not promise that every wide interval disappears.")
        lines.append("")
    lines += _wrap(
        f"The odds ratio is reported per {int(STEP_RATIO_DECREMENT * 100)}-percentage-point "
        f"lower proximal step ratio, evaluated between a ratio of "
        f"{STEP_RATIO_REFERENCE:.2f} and a ratio of {STEP_RATIO_CONTRAST:.2f}. A spline effect "
        f"is not constant, so the pair the contrast is taken between is part of what the "
        f"number means; it is fixed in this module's locked constants and printed here so "
        f"nobody has to guess it.")
    lines.append("")
    lines += _wrap(
        "Absolute risks come from the complementary full-cohort model and never from the "
        "conditional one, whose matched-set intercepts are conditioned out and which therefore "
        "has no intercept to translate into a risk at all. They are printed before the "
        "relative ones.")
    lines.append("")
    for name, key in (("Unadjusted", "unadjusted"), ("Adjusted", "adjusted")):
        fitted = detail.get(key)
        if not fitted:
            continue
        ratio = fitted["step ratio"]
        lines += _wrap(
            f"{name} fit, person-clustered: the clustered standard error is "
            f"{ratio['standard error clustered']:.4f} against a naive "
            f"{ratio['standard error naive']:.4f}, a ratio of "
            f"{ratio['clustering ratio']:.2f}. The reported interval is the person-level "
            f"cluster bootstrap over {ratio['bootstrap resamples']:,} resamples, of which "
            f"{ratio['bootstrap failures']:,} failed and were discarded and counted. The "
            f"clustered interval is printed beside it so a reader can see whether the two "
            f"disagreed rather than being told that they did not.")
        lines.append("")
        if ratio.get("bootstrap descent trigger"):
            lines += _wrap(
                f"More than {BOOTSTRAP_MAX_FAILURE_SHARE:.0%} of that fit's resamples FAILED "
                f"TO CONVERGE and were discarded and counted, which is trigger T4 of "
                f"ANALYSIS-PLAN 3.8 and stop condition 5 of section 11. That is a different "
                f"event from a resample above the coefficient ceiling, which is retained and "
                f"counted rather than discarded: a resample that did not converge produced no "
                f"number to keep, and one that separated produced a number that is too large.")
            lines.append("")
        lines += _wrap(f"Day-of-week handling in that fit: {fitted['day of week form']}.")
        lines.append("")
    performance = detail.get("performance")
    if performance:
        rows = [
            ["Area under the precision recall curve",
             f"{performance['area under the precision recall curve']:.3f}"],
            ["Brier score", f"{performance['brier score']:.4f}"],
            ["Calibration intercept", f"{performance['calibration intercept']:.3f}"],
            ["Calibration slope", f"{performance['calibration slope']:.3f}"],
            ["Sensitivity", f"{performance['sensitivity']:.3f}"],
            ["Specificity", f"{performance['specificity']:.3f}"],
            ["Positive predictive value",
             f"{performance['positive predictive value']:.3f}"],
            ["Negative predictive value",
             f"{performance['negative predictive value']:.3f}"],
            ["Alerts per 100 patient days",
             f"{performance['alerts per 100 patient days']:.2f}"],
            ["False alerts per detected encounter",
             f"{performance['false alerts per detected encounter']:.2f}"],
            ["Number needed to contact", f"{performance['number needed to contact']:.1f}"],
            ["Area under the receiver operating characteristic",
             f"{performance['area under the receiver operating characteristic']:.3f}"],
        ]
        lines += _table_lines(["Performance", "Value"], rows)
        lines.append(f"Denominator: {shown(count_node(int(performance['n rows'])))} "
                     f"episode days carrying "
                     f"{shown(count_node(int(performance['n events'])))} events.")
        lines.append("")
        lines += _wrap(
            "The area under the receiver operating characteristic is reported last and is "
            "never the headline. At an event rate of a few per thousand episode days it is "
            "dominated by the negative class, and the precision-recall area is the one that "
            "answers the clinical question.")
        lines.append("")
    return lines


def _render_refusals(result: Mapping[str, Any]) -> list[str]:
    """What the tier did not permit, by name.  The whole point of the module."""
    lines: list[str] = [_THIN, "7. WHAT THIS TIER DID NOT PERMIT, BY NAME", _THIN]
    refused = result["refused"]
    if not refused:
        lines += _wrap("Nothing in the analysis catalogue is refused at this tier except what "
                       "no tier permits, and there is none of that here.")
        lines.append("")
        return lines
    rows = [[entry["display_label"], entry["permitted_at_tiers"]] for entry in refused]
    lines += _table_lines(["Analysis not performed", "Permitted at"], rows, align="ll")
    lines.append(f"Denominator: the analysis catalogue, {len(ANALYSIS_CATALOGUE)} named "
                 f"analyses, of which {len(result['permitted'])} were permitted here.")
    lines.append("")
    lines += _wrap(
        "Each row above is an analysis that was specified in full before any count existed and "
        "was not run because the tier forbade it. One of them is forbidden at every tier: "
        "broad feature selection, in any form, is ruled out by the prespecification itself and "
        "not by this cohort's size. Listing it here is the difference between a study that did "
        "not do something and a study that cannot be shown not to have done it.")
    lines.append("")
    return lines


def _render_contract_gaps(result: Mapping[str, Any]) -> list[str]:
    """What this module produced that the export bundle has no home for."""
    lines: list[str] = [_THIN, "8. WHAT THE EXPORT CONTRACT HAS NO HOME FOR YET", _THIN]
    for gap in CONTRACT_GAPS:
        lines += _wrap(f"{gap['what']}: {gap['problem']}")
        lines += _wrap(f"    Emitted as: {gap['emitted']}")
        lines += _wrap(f"    Smallest amendment: {gap['amendment']}")
        lines.append("")
    lines += _wrap(
        "None of the above was worked around. Each is reported so that it reaches the export "
        "step as a decision rather than as a surprise, which is the failure mode a bundle "
        "schema exists to prevent.")
    lines.append("")
    return lines


def _render_verdict(result: Mapping[str, Any]) -> list[str]:
    """The verdict, and the halting reasons if there are any."""
    lines: list[str] = [_RULE]
    if result["gate ok"]:
        lines.append("VERDICT: the gate ran as prespecified and every stop condition held.")
    else:
        lines.append("VERDICT: A STOP CONDITION FIRED. The numbers above are not to be used.")
    lines.append(_RULE)
    if result["halting"]:
        lines += _bullets(result["halting"])
    lines.append("")
    lines += _wrap(
        "Counts of 20 or fewer are suppressed; larger counts are rounded to the nearest 20, so "
        "a disclosed 20 represents a true count of 21 to 29. A percentage is suppressed "
        "whenever the count behind it is suppressed. No participant-level value appears "
        "anywhere in this report, and none is returned by this module.")
    return lines


# ======================================================================================
# (18) Running it.  `q_guarded` is the only query path and there is no other; nothing in this
#      module can reach the BigQuery API by any route that skips the printed estimate and the
#      hard byte cap.
#
#      TWO PHASES, AND THE SECOND CANNOT START EARLY.  Phase 1 prices and runs the counting
#      queries.  The tier is decided from the count they return.  Phase 2 then prices and runs
#      only the queries that tier permits.  At the lowest tier phase 2 is empty and the model
#      queries are not merely unreported: they are never priced and never billed.
# ======================================================================================

# The frames that may be RETURNED.  The three model frames are participant-level, are fitted
# and are dropped; a frame outside this list never reaches the returned object, and the
# self-test walks the returned object to prove it.
RETURNABLE_FRAME_KEYS: tuple[str, ...] = (
    "gate ladder",
    "structurally deleted event timing",
    "landmark panel",
    "matched set sizes",
    "event centered curve",
)
# Column names that would make a returned frame participant-level.  Checked by name AND by
# shape in the self-test, because a rename upstream would defeat a check by name alone.
BANNED_RETURN_COLUMNS: tuple[str, ...] = (
    "person_id", "episode_id", "set_id", "event_id", "cluster_index", "episode_index",
    "set_index", "visit_occurrence_id", "fingerprint",
)

RESULT_KEYS: tuple[str, ...] = (
    "gate ok", "halting", "tier", "gate", "stages", "estimates", "estimates extra",
    "refused", "permitted", "detail", "frames", "cost plan", "contract gaps", "report",
)


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
    globals, which is what a run with the inherit flag populates; then the live kernel's
    namespace.  Nothing falls back to a raw BigQuery client: a module that could quietly find
    its own way to the API is a module that eventually runs a query with no printed estimate
    and no cap.
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
            raise GateRefusal(
                f"{name} is not available. This step runs inside the perimeter and gets its "
                f"only query path from the configuration notebook. Run that notebook first, "
                f"then load this file into the same kernel."
            )
        resolved.append(found)
    return resolved[0], resolved[1]


def cost_plan(sql_by_key: Mapping[str, str], dry_run_gb: Callable[[str], float],
              keys: Sequence[str], *, budget_gb: float, spent_gb: float = 0.0,
              phase: str = "") -> dict[str, Any]:
    """Price a phase before any of its queries runs, and refuse the phase if it does not fit.

    `spent_gb` carries the previous phase's measured total, so the budget is a budget for the
    STEP and not for each phase separately.  A dry run is free and prices the columns
    referenced rather than the table, so this pre-flight costs nothing and answers the
    frightening question first.
    """
    estimates = {key: float(dry_run_gb(sql_by_key[key])) for key in keys}
    total = sum(estimates.values())
    over_cap = sorted(key for key, gb in estimates.items() if gb > PLANNED_MAX_GB[key])
    return {
        "phase": phase,
        "keys": list(keys),
        "estimates": estimates,
        "total gb": total,
        "cumulative gb": total + float(spent_gb),
        "usd": (total + float(spent_gb)) / 1024.0 * USD_PER_TIB,
        "budget gb": float(budget_gb),
        "over cap": over_cap,
        "fits": ((total + float(spent_gb)) <= float(budget_gb)) and not over_cap,
    }


def cost_plan_lines(plan: Mapping[str, Any]) -> list[str]:
    """The cost plan as text, so it can be checked as easily as it is printed."""
    lines = [_THIN,
             f"COST PLAN, {plan['phase']}. Nothing in this phase has executed yet; every "
             f"figure below came from a free dry run.",
             _THIN]
    rows = [[key, f"{plan['estimates'][key]:,.3f}", f"{PLANNED_MAX_GB[key]:,.1f}"]
            for key in plan["keys"]]
    if not rows:
        rows = [["no query runs at this tier", "0.000", "0.0"]]
    lines += _table_lines(["Query", "Estimate, GiB", "Cap, GiB"], rows)
    lines.append(f"phase estimate {plan['total gb']:,.3f} GiB, cumulative "
                 f"{plan['cumulative gb']:,.3f} GiB, about ${plan['usd']:,.4f}, against a "
                 f"budget of {plan['budget gb']:,.1f} GiB")
    lines.append("Every read is of a derived table. No Controlled Tier table is touched.")
    return lines


def run_gate(
    *,
    features_result: Mapping[str, Any] | None = None,
    q_guarded: Callable[..., pd.DataFrame] | None = None,
    dry_run_gb: Callable[[str], float] | None = None,
    groups: Sequence[str] | None = None,
    budget_gb: float = GATE_BUDGET_GB,
    n_resamples: int = BOOTSTRAP_RESAMPLES_PRIMARY,
    show_report: bool = True,
) -> dict[str, Any]:
    """Price, count, decide the tier, run only what it permits, and report what it refused.

    The verdict is returned as well as printed and it is a STOP CONDITION rather than a
    warning: a false certification means the numbers above it are not to be used.  This
    function does not raise on a failed check, because the report is the thing a human needs in
    front of them when it fails; it raises only when it cannot get far enough to produce one,
    or when it is refusing to run at all.
    """
    assert_features_certified(features_result)
    query, dry_run = _resolve_runtime(q_guarded, dry_run_gb)
    sql_by_key = build_sql()

    first = cost_plan(sql_by_key, dry_run, PHASE_ONE_QUERY_KEYS, budget_gb=budget_gb,
                      phase="phase one, the counting queries")
    for line in cost_plan_lines(first):
        print(line)
    if not first["fits"]:
        raise GateBudgetExceeded(
            f"nothing executed and nothing billed. The measured dry-run total for the counting "
            f"queries is {first['total gb']:,.3f} GiB against a budget of "
            f"{first['budget gb']:,.1f} GiB, and these exceeded their own caps: "
            f"{first['over cap'] or 'none'}."
        )
    frames: dict[str, pd.DataFrame] = {}
    for key in PHASE_ONE_QUERY_KEYS:
        frames[key] = query(sql_by_key[key], max_gb=PLANNED_MAX_GB[key],
                            note=f"06 gate, {key}")
        safe_show(frames[key], name=key)

    ladder = read_ladder(frames["gate ladder"],
                         groups if groups is not None else FOUR_GROUP_SLUGS)
    tier = tier_for_events(ladder[GATE_DECIDING_STAGE]["total"])
    print(_THIN)
    print("THE TIER, READ FROM THE COUNT AND FROM NOTHING ELSE")
    print(_THIN)
    print(f"  deciding quantity : {TIER_DETERMINED_BY}")
    print(f"  deciding count    : {shown(count_node(ladder[GATE_DECIDING_STAGE]['total']))}")
    print(f"  tier reached      : {tier['display_label']}, {tier['band_display']}")
    print(f"  permitted claim   : {tier['permitted_claim_verbatim']}")
    print(f"  queries that run  : {list(queries_for_tier(tier['index'])) or 'none'}")

    second = cost_plan(sql_by_key, dry_run, queries_for_tier(tier["index"]),
                       budget_gb=budget_gb, spent_gb=first["total gb"],
                       phase="phase two, only what the tier permits")
    for line in cost_plan_lines(second):
        print(line)
    if not second["fits"]:
        raise GateBudgetExceeded(
            f"the counting queries ran; nothing further executed and nothing further billed. "
            f"The measured cumulative total is {second['cumulative gb']:,.3f} GiB against a "
            f"budget of {second['budget gb']:,.1f} GiB, and these exceeded their own caps: "
            f"{second['over cap'] or 'none'}."
        )
    for key in queries_for_tier(tier["index"]):
        frames[key] = query(sql_by_key[key], max_gb=PLANNED_MAX_GB[key],
                            note=f"06 gate, {key}")
        safe_show(frames[key], name=key)

    result = analyse(frames, tier=tier,
                     groups=groups if groups is not None else FOUR_GROUP_SLUGS,
                     n_resamples=n_resamples)
    result["frames"] = {key: frames[key] for key in RETURNABLE_FRAME_KEYS if key in frames}
    result["cost plan"] = {"phase one": first, "phase two": second}
    result["contract gaps"] = [dict(gap) for gap in CONTRACT_GAPS]
    result["report"] = render_report(result)
    if show_report:
        print(result["report"])
    return result


# ======================================================================================
# (19) The self-test.  No cloud access, no credentials, no file written.
#
#      Every fixture below is SYNTHETIC and is built to carry, on purpose, the states the
#      interesting failures hide in: a gate exactly at each tier boundary, a gate below the
#      disclosure floor so the tier is printable and the count is not, a stage F suppressed in
#      every stratum, an event whose window is eligible but unworn beside one whose window does
#      not exist, a participant who is a control at one landmark and a case at another, and a
#      matched design in which the naive and the person-clustered standard errors DIFFER, which
#      is the only way to show that the clustering is applied rather than merely named.
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


_BACKTICKED = re.compile(r"`([^`]+)`")
_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}")
_ALIAS = re.compile(r"\bAS\s+([A-Za-z_][A-Za-z0-9_]*)\b")
_DDL = re.compile(r"\b(CREATE|DROP|INSERT|UPDATE|DELETE|MERGE|TRUNCATE|ALTER)\b")
_RANDOMNESS = re.compile(r"\bRAND\s*\(")

# Fixture sizes.  Named rather than written as literals in a comparison, so a grep for a bare
# disclosure floor in a comparison cannot mistake a fixture's size for one.
_FIXTURE_GROUPS: tuple[str, ...] = FOUR_GROUP_SLUGS
_FIXTURE_EPISODES: int = 240
_FIXTURE_PANEL_DAYS: int = 30


def _ladder_frame(*, n_gate_events: int, n_first_events: int | None = None,
                  by_group: Sequence[int] | None = None) -> pd.DataFrame:
    """A synthetic A-through-F ladder whose deciding count is exactly what the caller asked for."""
    events = n_gate_events if n_first_events is None else n_first_events
    if by_group is None:
        share = [n_gate_events // 4] * 4
        share[0] += n_gate_events - sum(share)
        by_group = share
    rows = [{"stage_letter": "A", "part_slug": "total", "group_slug": slug,
             "n_units": 60 + 20 * index}
            for index, slug in enumerate(_FIXTURE_GROUPS)]
    rows += [
        {"stage_letter": "B", "part_slug": "total", "group_slug": ALL_GROUPS_SLUG,
         "n_units": 420},
        {"stage_letter": "C", "part_slug": "total", "group_slug": ALL_GROUPS_SLUG,
         "n_units": 340},
        {"stage_letter": "D", "part_slug": "total", "group_slug": ALL_GROUPS_SLUG,
         "n_units": events},
        {"stage_letter": "D", "part_slug": "first_ed_visits", "group_slug": ALL_GROUPS_SLUG,
         "n_units": max(events - 5, 0)},
        {"stage_letter": "D", "part_slug": "readmissions", "group_slug": ALL_GROUPS_SLUG,
         "n_units": 5},
        {"stage_letter": "D", "part_slug": "composite", "group_slug": ALL_GROUPS_SLUG,
         "n_units": events},
        {"stage_letter": "E", "part_slug": "total", "group_slug": ALL_GROUPS_SLUG,
         "n_units": n_gate_events},
    ]
    rows += [{"stage_letter": "F", "part_slug": "total", "group_slug": slug,
              "n_units": int(count)}
             for slug, count in zip(_FIXTURE_GROUPS, by_group)]
    return pd.DataFrame(rows)


def _timing_frame(*, n_gate_events: int, n_deleted: int, n_data: int) -> pd.DataFrame:
    """First events by post-discharge day, with the deleted ones inside the derived range."""
    rows = []
    remaining = n_deleted
    for day in range(STRUCTURAL_DELETION_FIRST_DAY, STRUCTURAL_DELETION_LAST_DAY + 1):
        share = remaining if day == STRUCTURAL_DELETION_LAST_DAY else remaining // 4
        remaining -= share
        rows.append({"event_post_discharge_day": day, "n_events": share,
                     "n_structurally_uncomputable": share, "n_data_uncomputable": 0,
                     "n_computable": 0, "n_flag_disagrees_with_derived_range": 0})
    rows.append({"event_post_discharge_day": FIRST_ELIGIBLE_EVENT_DAY,
                 "n_events": n_gate_events + n_data,
                 "n_structurally_uncomputable": 0, "n_data_uncomputable": n_data,
                 "n_computable": n_gate_events, "n_flag_disagrees_with_derived_range": 0})
    return pd.DataFrame(rows)


def _landmark_panel_frame(*, n_event_days: int) -> pd.DataFrame:
    """The full-cohort day-indexed panel, three day classes that partition it."""
    rows = []
    per_day = max(n_event_days // _FIXTURE_PANEL_DAYS, 0)
    leftover = n_event_days - per_day * _FIXTURE_PANEL_DAYS
    for day in range(1, _FIXTURE_PANEL_DAYS + 1):
        definitional = _FIXTURE_EPISODES if day <= STRUCTURAL_DELETION_LAST_DAY else 0
        computable = 0 if definitional else int(_FIXTURE_EPISODES * 0.7)
        data = 0 if definitional else _FIXTURE_EPISODES - computable
        events = per_day + (1 if day <= leftover else 0)
        events_data = (events // 4) if computable else 0
        events_computable = (events - events_data) if computable else 0
        rows.append({
            "post_discharge_day": day,
            "n_episode_days": _FIXTURE_EPISODES,
            "n_computable_days": computable,
            "n_data_uncomputable_days": data,
            "n_definitional_days": definitional,
            "n_event_days": events if not definitional else 0,
            "n_event_days_computable": events_computable if not definitional else 0,
            "n_event_days_data_uncomputable": events_data if not definitional else 0,
            "n_event_days_definitional": 0,
            "n_weight_input_available": computable,
            "n_landmark_before_day_one": definitional,
            "n_wearable_lookback_short": 0,
        })
    return pd.DataFrame(rows)


def _matched_set_size_frame(*, n_sets: int) -> pd.DataFrame:
    sizes = [max(CONTROLS_PER_CASE_CAP - (index % 3), 1) for index in range(n_sets)]
    counts = pd.Series(sizes).value_counts().sort_index()
    return pd.DataFrame([{"set_size": int(size), "n_sets": int(n), "n_cases": int(n)}
                         for size, n in counts.items()])


def _event_centered_frame() -> pd.DataFrame:
    """The curve, with its own denominator and the members the structural filter removed.

    The two denominator columns are constant down each role's block, because they describe the
    population the curve is drawn over and not the offset.  A control at post-discharge day 3
    or 4 is the case the filter exists for, and the fixture carries a non-zero drop so the
    printed denominator is exercised rather than merely present.
    """
    rows = []
    for role in MEMBER_ROLES:
        dropped = 0 if role == "case" else 6
        for day in range(-EVENT_CENTERED_FIRST_OFFSET, EVENT_CENTERED_LAST_OFFSET + 1):
            rows.append({
                "member_role": role, "relative_day": day, "n_contributing": 40,
                "n_members_in_curve": 90 if role == "case" else 274,
                "n_members_dropped_structural": dropped,
                "median_normalized_activity": 0.7 - (0.2 if role == "case" and day > -4 else 0),
                "mean_wear_fraction": 0.6, "n_valid_wear_days": 30, "n_analyzable_days": 28,
            })
    return pd.DataFrame(rows)


def _member_covariates(index: int) -> dict[str, Any]:
    """Covariates that vary between participants, so a conditional fit has something to use."""
    return {
        "age_at_index": 45.0 + (index % 35),
        "sex_at_birth": SEX_LEVELS[index % len(SEX_LEVELS)],
        "bmi_imputed": 24.0 + (index % 15),
        "bmi_missing": bool(index % 11 == 0),
        "charlson_ordinal": CHARLSON_LEVELS[index % len(CHARLSON_LEVELS)],
        "los_days": 1 + (index % 5),
        "index_year": 2016 + (index % 8),
        "covid_era": bool(index % 7 == 0),
        "device_family": ("charge", "versa", "sense")[index % 3],
        "baseline_steps": 4000.0 + 200.0 * (index % 20),
        "n_valid_baseline_days": 10 + (index % 12),
        "procedure_class": "fusion" if index % 2 else "decompression",
        "region": "cervical" if index % 3 else "lumbar",
    }


def _risk_set_frame(*, n_sets: int, n_persons: int, seed: int = SEED,
                    early_control_sets: int = 4, no_signal_share: float = 0.25,
                    relaxed_sets: int = 16, lost_control_sets: int = 1) -> pd.DataFrame:
    """A matched design in which PARTICIPANTS REAPPEAR ACROSS SETS, which is the whole point.

    A participant who is a control at one landmark and a case later is exactly what
    ANALYSIS-PLAN 4.5 permits and requires, and it is also exactly what breaks the independent
    matched sets assumption.  The fixture draws members at random so that reappearance is
    common and so that no covariate is a deterministic function of case status: a fixture in
    which the case is picked by an arithmetic rule over the person index separates perfectly
    once the covariates are added, and a fit that cannot converge demonstrates nothing.

    IT ALSO CARRIES THE MEMBERS THAT HAVE NO EXPOSURE WINDOW, AND CARRIES THEM THE WAY
    `build_all.sql` PRODUCES THEM.  The relaxation ladder of ANALYSIS-PLAN 4.7 moves a control
    at most 2 days below its case and a member is structurally uncomputable at a matched day of
    4 or less, so post-discharge day 5 and 6 are the ONLY case days that can draw one: the
    structural sets are put there rather than anywhere convenient, because a fixture the DAG
    cannot produce proves nothing about the DAG.  On such a member the derived table sets
    `structurally_uncomputable_landmark`, leaves `no_computable_step_signal` FALSE because that
    column is the data condition and only the data condition, and leaves `r72` NULL so that no
    ratio built from a single reachable post-discharge day can be fitted.  That combination is
    exactly what makes an unfiltered model frame halt, which is what this fixture exists to
    catch.  `lost_control_sets` sets lose EVERY control that way, which is ANALYSIS-PLAN 4.4's
    count 2 and is not recoverable from the member count.

    WHY `relaxed_sets` IS NOT A SMALL NUMBER, WRITTEN DOWN SO IT IS NOT TRIMMED BACK LATER.
    The day-of-week term of 4.7 is identified ONLY inside relaxation rung 3 sets: rung 1 and
    rung 2 hold it constant within the set and the conditional likelihood conditions it out
    there, so a fixture with a handful of rung 3 sets identifies a whole coefficient off a
    handful of within-set comparisons.  Such a fixture is quasi-separated on the day-of-week
    column at the slightest perturbation, and it was: removing the members that carry no
    exposure window is a perturbation, and it tipped a six-rung-3-set fixture past the
    coefficient ceiling.  A fixture that separates on an artefact of its own size demonstrates
    nothing about the module, so the rung 3 stratum is made large enough to carry the term the
    model puts on it.  It stays BELOW the disclosure floor on purpose, so the thin-set weekend
    reduction is still the branch under test rather than the seven-level form.
    """
    generator = np.random.default_rng([int(seed), 7])
    rows: list[dict[str, Any]] = []
    for set_index in range(1, n_sets + 1):
        # The draws stay in the same order and the same number whatever the set is for, so a
        # fixture knob never reshuffles the stream behind an unrelated assertion.
        matched_day = int(generator.integers(FIRST_ELIGIBLE_EVENT_DAY, 45))
        loses_every_control = set_index <= lost_control_sets
        loses_one_control = (not loses_every_control) and set_index <= early_control_sets
        if loses_every_control or loses_one_control:
            matched_day = FIRST_ELIGIBLE_EVENT_DAY + (set_index % 2)   # day 5 or day 6
        rung = (MATCH_RUNGS[-1]
                if (set_index <= relaxed_sets or loses_every_control or loses_one_control)
                else MATCH_RUNGS[0])
        drawn = generator.choice(n_persons, size=CONTROLS_PER_CASE_CAP + 1, replace=False)
        members = [(int(person) + 1, position == 0) for position, person in enumerate(drawn)]
        for position, (person, is_case) in enumerate(members):
            member_day = matched_day
            if rung == MATCH_RUNGS[-1] and not is_case:
                member_day = max(matched_day - int(generator.integers(0, 3)), 1)
            if not is_case and (loses_every_control
                                or (loses_one_control and position == 1)):
                member_day = matched_day - 2           # matched day 3 or 4: no exposure window
            landmark_day = member_day - LANDMARK_OFFSET_DAYS
            # The count of the window's days that are post-discharge days at all.  The window
            # is the three days ending at the landmark, so this is arithmetic on the landmark
            # day and on nothing else, which is how `build_all.sql` computes it off the dense
            # calendar grid.  It reaches 2 exactly when the landmark day is 2 or more.
            eligible_days = max(0, landmark_day
                                - max(landmark_day - (LANDMARK_WINDOW_DAYS - 1), 1) + 1)
            structural = eligible_days < LANDMARK_MIN_VALID_DAYS
            # `no_computable_step_signal` is the DATA condition and only the data condition, so
            # it is FALSE on a structural member.  The draw is taken either way, so the knobs
            # above cannot move the random stream.
            no_signal = bool(generator.random() < no_signal_share) and not structural
            # The exposure carries a real effect, so there is a coefficient to put an interval
            # on, and it OVERLAPS between cases and controls, so the likelihood has a maximum.
            centre = 0.60 if is_case else 0.75
            ratio = float(np.clip(generator.normal(centre, 0.20), 0.05, 1.4))
            row = {
                "set_index": set_index,
                "cluster_index": person,
                "is_case": is_case,
                "case_matched_day": matched_day,
                "member_matched_day": member_day,
                "member_landmark_post_discharge_day": landmark_day,
                "member_landmark_day_of_week": int(1 + ((member_day + set_index) % 7)),
                "is_weekend_landmark": bool((1 + ((member_day + set_index) % 7))
                                            in WEEKEND_DAYS),
                "match_rung": rung,
                "set_size": CONTROLS_PER_CASE_CAP,
                "n_valid_days_in_window": (0 if (no_signal or structural)
                                           else LANDMARK_WINDOW_DAYS),
                "n_eligible_days_in_window": eligible_days,
                "has_computable_landmark": not (no_signal or structural),
                "structurally_uncomputable_landmark": structural,
                "no_computable_step_signal": no_signal,
                # NULL on every structural member, deliberately: without it a matched-day-4
                # member would publish a ratio built from its single reachable post-discharge
                # day, and a reader who forgot the flag would fit it as though it were the
                # exposure.
                "r72": np.nan if (no_signal or structural) else ratio,
                "wear_fraction": 0.55,
                "reference_ratio": float(np.clip(ratio + 0.05, 0.05, 1.5)),
                "n_reference_valid_days": 5,
                "landmark_lagged_wear_fraction": (
                    np.nan if landmark_day < MIN_WEIGHTED_LANDMARK_DAY
                    else float(np.clip(generator.normal(0.6, 0.2), 0.0, 1.0))),
                "landmark_weight_input_available": landmark_day >= MIN_WEIGHTED_LANDMARK_DAY,
                "landmark_before_post_discharge_day_one": landmark_day < 1,
                "panel_valid_days_in_window": (0 if (no_signal or structural)
                                               else LANDMARK_WINDOW_DAYS),
                "n_days_behind_landmark_on_wearable_grid": 7,
            }
            row.update(_member_covariates(person))
            rows.append(row)
    return pd.DataFrame(rows)


def _negative_control_frame(members: pd.DataFrame) -> pd.DataFrame:
    """The same members with the remote window, restricted to late cases as the plan requires."""
    late = members[pd.to_numeric(members["case_matched_day"], errors="coerce")
                   >= NEGATIVE_CONTROL_MIN_EVENT_DAY].copy()
    generator = np.random.default_rng([SEED, 11])
    n = len(late)
    remote = np.clip(generator.normal(0.75, 0.15, size=n), 0.05, 1.4)
    missing = generator.random(n) < 0.2
    late["negative_control_ratio"] = np.where(missing, np.nan, remote)
    late["n_negative_control_valid_days"] = np.where(missing, 1, 5)
    late["no_computable_negative_control"] = missing
    return late.reset_index(drop=True)


def _discrete_time_frame(*, n_persons: int, n_days: int, seed: int = SEED) -> pd.DataFrame:
    """A person-day panel with a real event rate, the earliest days flagged definitional."""
    generator = np.random.default_rng([int(seed), 13])
    rows: list[dict[str, Any]] = []
    for person in range(1, n_persons + 1):
        covariates = _member_covariates(person)
        event_day = int(generator.integers(FIRST_ELIGIBLE_EVENT_DAY, n_days + 1)) \
            if generator.random() < 0.25 else None
        for day in range(1, n_days + 1):
            if event_day is not None and day > event_day:
                break
            structural = day <= STRUCTURAL_DELETION_LAST_DAY
            no_signal = bool(generator.random() < 0.2) and not structural
            ratio = float(np.clip(generator.normal(0.75, 0.18), 0.05, 1.4))
            row = {
                "cluster_index": person,
                "episode_index": person,
                "post_discharge_day": day,
                "outcome": int(event_day is not None and day == event_day),
                "r72": np.nan if (structural or no_signal) else ratio,
                # THE DATA CONDITION ONLY, WHICH IS THE UNION THIS COLUMN CANNOT CARRY.  This
                # read `bool(structural or no_signal)`, and `landmark_daily` cannot emit that
                # combination: ANALYSIS-PLAN 4.4 keeps the two landmark conditions distinct and
                # says their counts are never summed, on the panel or anywhere else, and a
                # structurally uncomputable window carries NO no-signal indicator at all
                # because it has no exposure window to be uncomputable in.  No result moves,
                # because `discrete_time_design` drops the structural rows before it builds the
                # exposure block and the two expressions agree on every row that survives; what
                # moves is that a fixture which builds an impossible state stops testing the
                # real one, and the next reader of it stops being able to tell which is which.
                "no_computable_step_signal": bool(no_signal),
                "structurally_uncomputable_landmark": structural,
                "n_valid_days_in_window": 0 if (structural or no_signal)
                                          else LANDMARK_WINDOW_DAYS,
                "n_window_valid_days_recomputed": 0 if (structural or no_signal)
                                                  else LANDMARK_WINDOW_DAYS,
                "window_disagrees": 0,
                "landmark_lagged_wear_fraction": np.nan if day <= LANDMARK_OFFSET_DAYS else 0.6,
                "landmark_weight_input_available": day > LANDMARK_OFFSET_DAYS,
            }
            row.update(covariates)
            rows.append(row)
    return pd.DataFrame(rows)


def _fixture_frames(*, n_gate_events: int, n_deleted: int = 9, n_data: int = 6,
                    n_sets: int = 90, n_persons: int = 120) -> dict[str, pd.DataFrame]:
    members = _risk_set_frame(n_sets=n_sets, n_persons=n_persons)
    return {
        "gate ladder": _ladder_frame(n_gate_events=n_gate_events,
                                     n_first_events=n_gate_events + n_deleted + n_data),
        "structurally deleted event timing": _timing_frame(
            n_gate_events=n_gate_events, n_deleted=n_deleted, n_data=n_data),
        "landmark panel": _landmark_panel_frame(n_event_days=n_gate_events),
        "matched set sizes": _matched_set_size_frame(n_sets=n_sets),
        "event centered curve": _event_centered_frame(),
        "risk set model frame": members,
        "negative control frame": _negative_control_frame(members),
        "discrete time panel": _discrete_time_frame(n_persons=n_persons, n_days=40),
    }


class _FakeRuntime:
    """A stand-in for the configuration notebook's two helpers, recording every call."""

    def __init__(self, frames: Mapping[str, pd.DataFrame], gb: float = 0.02) -> None:
        self._frames = dict(frames)
        self._by_sql = {}
        self.gb = float(gb)
        self.calls: list[tuple[str, float, str]] = []
        self.dry_runs = 0
        for key, sql in build_sql().items():
            self._by_sql[sql] = key

    def dry_run_gb(self, sql: str) -> float:
        self.dry_runs += 1
        return self.gb

    def q_guarded(self, sql: str, *, max_gb: float, note: str = "") -> pd.DataFrame:
        key = self._by_sql[sql]
        self.calls.append((key, float(max_gb), note))
        return self._frames[key].copy()


def _clustered_demonstration(n_persons: int = 12, n_sets: int = 60, seed: int = SEED,
                             true_beta: float = 0.9, members_per_set: int = 4,
                             ) -> dict[str, Any]:
    """A synthetic matched design where the naive and clustered standard errors MUST differ.

    Each participant contributes to many sets and carries a participant-level shift in the
    exposure, so the score contributions of the sets they appear in are correlated.  That
    correlation is exactly what a naive variance assumes away and exactly what the person
    cluster sums restore, so the two standard errors cannot come out equal here unless the
    clustering is not being applied at all.

    The case within each set is drawn from the CONDITIONAL model itself, with probability
    proportional to the exponentiated linear predictor.  Picking the largest exposure instead
    would give perfect separation, and a fit that diverges demonstrates nothing about a
    variance.
    """
    generator = np.random.default_rng([int(seed), 101])
    person_shift = generator.normal(0.0, 1.2, size=n_persons)
    rows_x, rows_y, rows_set, rows_cluster = [], [], [], []
    for set_index in range(n_sets):
        members = [(set_index * 2 + offset) % n_persons for offset in range(members_per_set)]
        exposures = np.array([person_shift[p] + generator.normal(0.0, 0.8) for p in members])
        weights = np.exp(true_beta * exposures)
        weights = weights / weights.sum()
        case = int(generator.choice(len(members), p=weights))
        for position, person in enumerate(members):
            rows_x.append(float(exposures[position]))
            rows_y.append(1.0 if position == case else 0.0)
            rows_set.append(set_index)
            rows_cluster.append(person)
    design = np.asarray(rows_x, dtype=float)[:, None]
    return {
        "fit": fit_conditional_logit(design, np.asarray(rows_y), np.asarray(rows_set),
                                     np.asarray(rows_cluster)),
        "design": design,
        "outcome": np.asarray(rows_y, dtype=float),
        "sets": np.asarray(rows_set, dtype=np.int64),
        "clusters": np.asarray(rows_cluster, dtype=np.int64),
        "true beta": float(true_beta),
    }


def _near_separated_design(n_break: int, n_sets: int = 40, members_per_set: int = 4,
                           seed: int = SEED) -> tuple[np.ndarray, ...]:
    """A matched design at a controllable DEGREE of separation, which the suite had none of.

    `n_sets` sets of `members_per_set`, and the case is the member at MAXIMUM exposure in every
    set but `n_break` of them, where it is the member at the second highest instead.  At
    `n_break = 0` the separation is PERFECT: no finite coefficient maximises the likelihood and
    the Newton iteration walks off, which the fit already caught before the ceiling existed.
    At `n_break` of 1 or more it is QUASI-separated, which is the case the ceiling exists for
    and the case a real study meets: the likelihood flattens, the old rule declared convergence,
    and the coefficient it declared converged was 8.961, an odds ratio of 7,792.

    `_clustered_demonstration` draws its case from the conditional model itself and says in its
    own docstring that it does so to AVOID separation, which is right for a test about a
    variance.  The consequence was that no test in this module exercised separation at all, so
    no assertion in it could fire on a runaway fit.  This is that test's missing complement.
    """
    generator = np.random.default_rng(seed)
    rows_x, rows_y, rows_set, rows_cluster = [], [], [], []
    for set_index in range(n_sets):
        exposures = generator.normal(0.0, 1.0, size=members_per_set)
        ordered = np.argsort(exposures)
        case = int(ordered[-2]) if set_index < n_break else int(ordered[-1])
        for position in range(members_per_set):
            rows_x.append(float(exposures[position]))
            rows_y.append(1.0 if position == case else 0.0)
            rows_set.append(set_index)
            rows_cluster.append(set_index)
    return (np.asarray(rows_x, dtype=float)[:, None], np.asarray(rows_y, dtype=float),
            np.asarray(rows_set, dtype=np.int64), np.asarray(rows_cluster, dtype=np.int64))


def _strong_but_legitimate_design(true_beta: float = 2.0, n_sets: int = 80,
                                  members_per_set: int = 4, seed: int = SEED,
                                  ) -> tuple[np.ndarray, ...]:
    """A LARGE real effect, drawn from the conditional model, which the ceiling must not refuse.

    A ceiling that only ever fires is indistinguishable from one that fires too often, so the
    refusal above is worth nothing on its own.  `true_beta` here is 2.0, an odds ratio of about
    7.4 per unit of exposure, which is far larger than anything this study expects to see from
    a step ratio and is still two full log-odds units clear of nothing being refused.
    """
    generator = np.random.default_rng([int(seed), 4241])
    rows_x, rows_y, rows_set, rows_cluster = [], [], [], []
    for set_index in range(n_sets):
        exposures = generator.normal(0.0, 1.0, size=members_per_set)
        weights = np.exp(true_beta * exposures)
        case = int(generator.choice(members_per_set, p=weights / weights.sum()))
        for position in range(members_per_set):
            rows_x.append(float(exposures[position]))
            rows_y.append(1.0 if position == case else 0.0)
            rows_set.append(set_index)
            rows_cluster.append(set_index)
    return (np.asarray(rows_x, dtype=float)[:, None], np.asarray(rows_y, dtype=float),
            np.asarray(rows_set, dtype=np.int64), np.asarray(rows_cluster, dtype=np.int64))


def _run_self_test() -> None:
    global _ASSERTIONS
    _ASSERTIONS = 0

    # ---- 1. the emitted SQL, every query, checked as text ----------------------------------
    sql_by_key = build_sql()
    _expect(tuple(sql_by_key) == QUERY_KEYS,
            "build_sql returns the declared keys, in the declared order")
    _expect(set(PLANNED_MAX_GB) == set(QUERY_KEYS),
            "every query has its own cap and no cap names a query that does not exist")
    _expect(set(QUERY_PERMITTED_TIERS) == set(QUERY_KEYS),
            "every query declares the tiers it runs at")
    _expect(sum(PLANNED_MAX_GB.values()) > GATE_BUDGET_GB,
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
                    f"{key} quotes only derived tables and functions, never a hardcoded "
                    f"project or dataset")
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
                f"{key} declares column(s) {missing} that it does not actually alias")
    for key in ("risk set model frame", "negative control frame", "discrete time panel"):
        _expect("DENSE_RANK" in sql_by_key[key],
                f"{key} emits dense surrogates, so no person, episode or set identifier ever "
                f"reaches the kernel")
        for identifier in ("person_id AS person_id", "episode_id AS episode_id",
                           "set_id AS set_id"):
            _expect(f"  {identifier}" not in sql_by_key[key].split("-- @columns:")[1],
                    f"{key} does not select an identifier into its result columns")
    _expect_raises(GateError, lambda: _sql("SELECT <<NO_SUCH_CONSTANT>>"),
                   "a query naming a constant this module does not define is refused at build "
                   "time rather than reaching BigQuery half-written")
    _expect_raises(GateError, lambda: declared_columns("SELECT 1"),
                   "a query with no column declaration is refused")

    # EVERY SURFACE THE DEFINITIONAL CONDITION LEAVES, CHECKED AS TEXT.  ANALYSIS-PLAN 4.4
    # enumerates them and names `risk_sets` among them, and the event-centered curve is the one
    # that read that table without the filter: it was left unfiltered on the reading that a
    # display exhibit is outside the enumeration, and it is filtered now, because a figure
    # whose population differs from the model's without saying so is a question the paper could
    # not answer.
    for key in ("event centered curve", "risk set model frame", "negative control frame",
                "discrete time panel"):
        _expect("structurally_uncomputable_landmark" in sql_by_key[key],
                f"{key} names the definitional flag, because it is the one thing that decides "
                f"whether a member carries an exposure window at all")
    _expect("WHERE NOT r.structurally_uncomputable_landmark"
            in sql_by_key["event centered curve"],
            "the event-centered curve FILTERS on it rather than merely selecting it: a control "
            "the exposure model dropped for having a window that straddles discharge is not in "
            "the figure either")
    for column in ("n_members_in_curve", "n_members_dropped_structural"):
        _expect(column in declared_columns(sql_by_key["event centered curve"]),
                f"and the curve returns '{column}', so the exhibit carries its own denominator "
                f"and the filter's cost is a printed count rather than a silent one")

    # ---- 2. THE TIER DECISION, AT EVERY BOUNDARY -------------------------------------------
    boundaries = [
        (0, 4), (1, 4), (TIER_3_MIN_EVENTS - 1, 4),
        (TIER_3_MIN_EVENTS, 3), (TIER_3_MIN_EVENTS + 1, 3), (TIER_2_MIN_EVENTS - 1, 3),
        (TIER_2_MIN_EVENTS, 2), (TIER_2_MIN_EVENTS + 1, 2), (TIER_1_MIN_EVENTS - 1, 2),
        (TIER_1_MIN_EVENTS, 1), (TIER_1_MIN_EVENTS + 1, 1), (10_000, 1),
    ]
    for count, expected in boundaries:
        _expect(tier_for_events(count)["index"] == expected,
                f"a gate of {count} events is tier {expected}, on the plan's own inclusive "
                f"lower bounds")
    _expect(tier_for_events(TIER_3_MIN_EVENTS)["index"] == 3,
            "EXACTLY 20 events is tier 3, not tier 4: the tier band and the disclosure band "
            "are not the same band")
    _expect(tier_for_events(TIER_2_MIN_EVENTS)["index"] == 2,
            "EXACTLY 50 events is tier 2")
    _expect(tier_for_events(TIER_1_MIN_EVENTS)["index"] == 1,
            "EXACTLY 100 events is tier 1")
    _expect_raises(GateError, lambda: tier_for_events(3.5),
                   "the tier is read from a whole count and a fractional one is refused rather "
                   "than rounded into a band")
    _expect_raises(GateError, lambda: tier_for_events(-1),
                   "a negative count is a defect upstream, not a tier 4")
    for index in TIER_INDICES:
        record = tier_for_events(
            TIER_BANDS[index][0] if TIER_BANDS[index][0] is not None else 0)
        _expect(record["permitted_claim_verbatim"] == TIER_PERMITTED_CLAIM_VERBATIM[index],
                f"tier {index} carries the verbatim permitted claim, unaltered")
        _expect(record["exhibit_set"] == TIER_EXHIBIT_SET[index],
                f"tier {index} carries the exhibit set the contract fixes for it")
    _expect(TIER_EXHIBIT_SET[1] == TIER_EXHIBIT_SET[2] == "alternate",
            "the two highest tiers switch the whole exhibit set, which the contract must be "
            "amended for before any export runs")

    # ---- 3. A TIER IT CANNOT PRINT A COUNT FOR ---------------------------------------------
    below = tier_for_events(TIER_3_MIN_EVENTS - 1)
    _expect(below["index"] == 4 and not below["event_count_printable"],
            "below the lowest boundary the module reports a tier and refuses to print the "
            "count that produced it")
    _expect(below["display_label"] and below["band_display"],
            "and the tier itself is fully printable, which is the whole point: a tier that "
            "could not be reported would leave a reader unable to see that a gate ran at all")
    at_boundary = tier_for_events(TIER_3_MIN_EVENTS)
    _expect(at_boundary["index"] == 3 and not at_boundary["event_count_printable"],
            "THE ONE-COUNT CASE: exactly 20 events runs the tier 3 analysis and may not print "
            "its own denominator")
    _expect(tier_for_events(TIER_3_MIN_EVENTS + 1)["event_count_printable"],
            "21 events is disclosable and prints, rounded")
    _expect(tier_for_events(0)["event_count_printable"] and tier_for_events(0)["index"] == 4,
            "a measured zero is disclosable and is printed, and it is still the lowest tier. "
            "The floor arbiter admits a true zero and this module defers to it rather than "
            "writing a bare comparison of its own")
    node = count_node(TIER_3_MIN_EVENTS)
    _expect(node["suppressed"] and node["reason"] == "cell_below_threshold",
            "and the deciding count at exactly the boundary renders as the suppression "
            "sentence rather than as a number")
    _expect(shown(node) == SUPPRESSION_REASONS["cell_below_threshold"],
            "which reads '20 or fewer', because a count of exactly 20 IS suppressed and a "
            "sentence saying 'fewer than 20' over a suppressed 20 is simply false")

    # ---- 4. EACH TIER REFUSES THE ANALYSES ABOVE IT, BY NAME -------------------------------
    for index in TIER_INDICES:
        refused = refusals_for_tier(index)
        permitted = permitted_for_tier(index)
        slugs_refused = {entry["slug"] for entry in refused}
        slugs_permitted = {entry["slug"] for entry in permitted}
        _expect(slugs_refused | slugs_permitted == set(ANALYSIS_SLUGS),
                f"at tier {index} the refusal ledger and the permitted list together are the "
                f"whole catalogue, so nothing can be silently absent from both")
        _expect(not (slugs_refused & slugs_permitted),
                f"at tier {index} nothing is both refused and permitted")
        _expect(all(entry["display_label"] and "_" not in entry["display_label"]
                    for entry in refused),
                f"at tier {index} every refusal prints a display label and never a slug")
        _expect(all(entry["reason"] == "not_permitted_by_tier" for entry in refused),
                f"at tier {index} every refusal carries the tier reason, which is a different "
                f"fact from a cell being small")
    _expect({e["slug"] for e in refusals_for_tier(4)} > {e["slug"] for e in refusals_for_tier(3)},
            "tier 4 refuses strictly more than tier 3")
    _expect({e["slug"] for e in refusals_for_tier(3)} > {e["slug"] for e in refusals_for_tier(2)},
            "tier 3 refuses strictly more than tier 2")
    _expect({e["slug"] for e in refusals_for_tier(2)} > {e["slug"] for e in refusals_for_tier(1)},
            "tier 2 refuses strictly more than tier 1")
    for named in ("adjusted_conditional_logistic_model", "negative_control_window",
                  "median_lead_time", "performance_panel", "alert_burden",
                  "internal_validation", "temporal_validation", "multidomain_model"):
        _expect(named in {e["slug"] for e in refusals_for_tier(3)},
                f"tier 3 refuses '{named}' BY NAME, which is what turns an absence into a "
                f"printed row")
    _expect("broad_feature_selection" in {e["slug"] for e in refusals_for_tier(1)},
            "broad feature selection is refused even at the HIGHEST tier, because the "
            "prespecification forbids it outright and not because the cohort is thin")
    _expect(refusals_for_tier(1)[[e["slug"] for e in refusals_for_tier(1)]
                                 .index("broad_feature_selection")]["permitted_at_tiers"]
            == "no tier",
            "and it prints 'no tier', which is the honest rendering of a rule that is not "
            "about this cohort's size at all")
    _expect(not permitted_at("adjusted_conditional_logistic_model", 3),
            "no adjusted model at tier 3: the plan permits the UNADJUSTED association there "
            "and the adjusted one is the step-first model that tier 2 adds")
    _expect(permitted_at("unadjusted_association", 3),
            "and the unadjusted association is what tier 3 does permit")
    _expect_raises(GateError, lambda: permitted_at("no_such_analysis", 3),
                   "an analysis outside the catalogue cannot be asked about, because the "
                   "catalogue is what makes a refusal nameable")
    for index in TIER_INDICES:
        refusal_nodes = tier_refusal_estimates(index)
        for key, node in refusal_nodes.items():
            _expect(node["suppressed"] and node["reason"] == "not_permitted_by_tier",
                    f"at tier {index} the contract key '{key}' is present and carries a "
                    f"printed refusal, because a key absent from the block is "
                    f"indistinguishable from a bug")
            _expect("n" not in node and "est" not in node,
                    "a refused node carries no numeric key at all: the number is not in the file")
    # THE FIVE TABLES THAT DESCRIBE A KEY MOVE TOGETHER OR NOT AT ALL.  A key added to the
    # tuple without a row in each of the other four is the shape the 1.5.0 lag had: the tuple
    # was the authority, the rest described something else, and nothing failed until an export
    # refused a file at a tier nobody had run yet.
    _expect(len(ESTIMATE_KEYS) == 13 and len(set(ESTIMATE_KEYS)) == 13,
            "EXPORT-CONTRACT 3.7 declares thirteen keys for the gate block and each once")
    for table, name in ((ESTIMATE_KEY_ANALYSIS, "analysis"), (ESTIMATE_KEY_LABELS, "label"),
                        (ESTIMATE_KEY_SHAPE, "shape"), (ESTIMATE_KEY_UNIT, "unit")):
        _expect(set(table) == set(ESTIMATE_KEYS),
                f"the {name} table and the key tuple name the same thirteen keys")
    for key in ESTIMATE_KEYS:
        _expect(ESTIMATE_KEY_ANALYSIS[key] in ANALYSIS_SLUGS,
                f"'{key}' names an analysis the catalogue carries, so the tier that forbids it "
                f"can refuse it BY NAME rather than leaving it absent")
        _expect(ESTIMATE_KEY_UNIT[key] in UNIT_DECIMALS,
                f"'{key}' carries a unit this module knows the decimals for")
        _expect(ESTIMATE_KEY_SHAPE[key] in ("estimate", "quantile", "bound"),
                f"'{key}' carries one of the node shapes EXPORT-CONTRACT 2.2 fixes")
    # 3.7's TIER TABLE, ROW BY ROW, off the catalogue rather than off a run.
    _expect(set(tier_refusal_estimates(3)) == {
        "adjusted_odds_per_lower_step_ratio", "negative_control_window",
        "median_lead_time", "absolute_risk_translation"},
        "3.7's tier 3 row refuses exactly four keys and produces the other nine, which are "
        "the set-size distribution, the two odds contrasts and the six collider cells")
    _expect(set(tier_refusal_estimates(2)) == {"median_lead_time"},
            "3.7's tier 2 row produces all but median lead time")
    _expect(set(tier_refusal_estimates(4)) == set(ESTIMATE_KEYS),
            "at tier 4 every contract estimate key is refused")
    _expect(set(tier_refusal_estimates(1)) == set(),
            "at tier 1 none of them is")
    _expect(set(queries_for_tier(4)) == set(),
            "at tier 4 no phase two query runs at all, so the model queries are not merely "
            "unreported: they are never priced and never billed")
    _expect(set(queries_for_tier(3)) < set(queries_for_tier(2)) <= set(queries_for_tier(1)),
            "the query set grows with the tier and never shrinks")

    # ---- 5. THE TWO LANDMARK CONDITIONS ARE NEVER SUMMED -----------------------------------
    timing = landmark_timing_summary(_timing_frame(n_gate_events=30, n_deleted=9, n_data=6))
    _expect(timing["n structurally deleted"] == 9 and timing["n data uncomputable"] == 6,
            "the definitional and the data conditions are counted separately")
    _expect("n no computable landmark" not in timing and "n uncomputable" not in timing,
            "AND THERE IS NO SUM. A single number over both would be the sum of an exclusion "
            "and an exposure, and no reader could take it apart again afterwards")
    _expect(timing["derived range"] == (STRUCTURAL_DELETION_FIRST_DAY,
                                        STRUCTURAL_DELETION_LAST_DAY)
            and STRUCTURAL_DELETION_LAST_DAY == 4,
            "the definitional range is post-discharge day 1 to 4, derived from the plan's own "
            "two-valid-day rule. Day 1 to 3 is the wrong range and is what this pins")
    _expect(set(timing["by day"]) <= set(range(STRUCTURAL_DELETION_FIRST_DAY,
                                               STRUCTURAL_DELETION_LAST_DAY + 1)),
            "and every deleted event lies inside it")
    stray = _timing_frame(n_gate_events=30, n_deleted=9, n_data=6)
    stray.loc[stray.index[0], "n_flag_disagrees_with_derived_range"] = 1
    _expect(landmark_timing_summary(stray)["violations"],
            "a derived flag that disagrees with the derivation is a stop condition, not a "
            "rounding difference: it is how a document still saying day 1 to 3 is caught")
    panel = _landmark_panel_frame(n_event_days=40)
    comparison = landmark_comparison(panel)
    conditions = comparison["conditions"]
    _expect(set(conditions) == {"computable", "data", "definitional"},
            "the panel carries three day classes and the definitional one is reported beside "
            "the comparison rather than inside it")
    _expect(conditions["computable"]["n episode days"] + conditions["data"]["n episode days"]
            + conditions["definitional"]["n episode days"] == comparison["n episode days"],
            "the three partition the panel, which is what makes the standardization weights "
            "describe the base they are applied to")
    _expect(comparison["causal"] is False,
            "and neither version is labelled causal, because the panel controls for nothing")
    rich = landmark_comparison(_landmark_panel_frame(n_event_days=2400))
    _expect(np.isfinite(rich["crude rate ratio"])
            and np.isfinite(rich["standardized rate ratio"]),
            "where the counts allow it BOTH the crude and the band-standardized comparison are "
            "produced, so a reader is shown how much post-discharge day was doing rather than "
            "told which to believe")
    thin = landmark_comparison(_landmark_panel_frame(n_event_days=8))
    _expect(not np.isfinite(thin["conditions"]["computable"]["standardized rate"]),
            "and where a contributing band is below the floor the standardized rate is "
            "suppressed rather than published, because it would otherwise carry per-band "
            "counts that may not be printed inside it")
    _expect(not thin["conditions"]["computable"]["every band printable"],
            "which the comparison records rather than leaving a reader to infer from a gap")
    _expect(abs(_rate_from_rounded(31, 1000) - round20(31) / round20(1000)
                * RATE_DENOMINATOR) < FLOAT_TOLERANCE,
            "every rate is computed from the ROUNDED numerator over the ROUNDED denominator, "
            "so it is reproducible from the counts beside it and cannot be multiplied back "
            "into a hidden count")
    _expect(not np.isfinite(_rate_from_rounded(TIER_3_MIN_EVENTS, 1000)),
            "and a rate whose numerator is below the floor is not produced at all")
    broken = panel.copy()
    broken.loc[broken.index[0], "n_definitional_days"] = 999
    _expect_raises(GateError, lambda: landmark_comparison(broken),
                   "a panel whose three classes do not sum to it is refused")

    # EXPORT-CONTRACT 3.7's SIX COLLIDER KEYS, ONE PER RATE CELL OF 5.7's THREE BY TWO.
    collider_keys = tuple(k for k in ESTIMATE_KEYS if k.startswith("collider_"))
    _expect(len(collider_keys) == 6,
            "six rate cells and six keys. Four would leave the standardized rate of each "
            "window group tracing to nothing, and ANALYSIS-PLAN 4.4 judges the two conditions "
            "SEPARATELY, so two conditions need two cells and therefore two keys")
    nodes = collider_estimate_nodes(rich)
    _expect(set(nodes) == set(collider_keys),
            "and the builder emits exactly those six, never a key 3.7 does not declare")
    for key, node in nodes.items():
        _expect(node["suppressed"] is False and node["display_ci"] == ""
                and node["lo"] == node["est"] == node["hi"]
                and node["unit"] == ESTIMATE_KEY_UNIT[key],
                f"'{key}' is a BOUND: the point on all three keys, an empty interval display, "
                f"and the unit 2.4 fixes, because ANALYSIS-PLAN 4.4 specifies a rate from "
                f"rounded counts and specifies no interval for it")
    # The band-level floor bites here and the cohort-level one does not, which is the case
    # 5.7 and ANALYSIS-PLAN 4.4 are both written for: a crude rate over one numerator that
    # clears the floor, and a standardized rate that is a weighted average of band counts that
    # do not.
    withheld = collider_estimate_nodes(comparison)
    _expect(withheld["collider_rate_with_signal_standardized"]["reason"]
            == "contributing_n_below_threshold",
            "a standardized rate whose contributing band is below the floor is withheld under "
            "the reason 5.7 names, and not under a reason about its own size")
    _expect(withheld["collider_rate_ratio_standardized"]["reason"] == "numerator_suppressed",
            "and the standardized ratio goes with it, because it cannot be formed without "
            "both rates. The number behind it is hidden, not small")
    _expect(withheld["collider_rate_with_signal"]["suppressed"] is False,
            "while the CRUDE rate beside it is unaffected: it is one numerator over one "
            "denominator and is suppressed on its own terms alone")
    counts = collider_window_counts(rich)
    _expect(set(counts) == {"with_signal", "without_signal"}
            and all(set(pair) == {"episode_days", "events"} for pair in counts.values()),
            "5.7's two window-group count pairs are keyed by window group and carry the "
            "episode-days at risk and the acute-care events, which are COUNTS and therefore "
            "travel beside a block named for estimates rather than inside it")
    _expect(all(key not in counts for key in ("definitional", "n definitional")),
            "and the definitional condition is not a window group of the comparison: it is "
            "printed beside it so a reader can see it is excluded, never folded in")
    _expect(counts["with_signal"]["events"]
            == rich["conditions"]["computable"]["n event days"],
            "the TRUE integers travel, so the floor is applied once and at the export "
            "boundary rather than twice on a number already moved")

    # AND THE SYNTHETIC PANEL BUILDS A STATE `landmark_daily` CAN EMIT.  Its no-signal column
    # was the UNION of the two landmark conditions, which the source cannot produce: 4.4 keeps
    # them distinct and their counts are never summed, and a window with fewer than 2
    # post-discharge days carries no no-signal indicator at all because it has no exposure
    # window to be uncomputable in.  No result moved when this was corrected, because the fit
    # drops the structural rows before it builds the exposure block; what changed is that the
    # fixture tests the real state rather than an impossible one.
    synthetic = _discrete_time_frame(n_persons=40, n_days=30)
    both = synthetic[synthetic["structurally_uncomputable_landmark"].astype(bool)
                     & synthetic["no_computable_step_signal"].astype(bool)]
    _expect(both.empty,
            "no synthetic panel row carries both landmark conditions at once, because no real "
            "one can")
    _expect(synthetic["structurally_uncomputable_landmark"].astype(bool).any()
            and synthetic["no_computable_step_signal"].astype(bool).any(),
            "and both conditions are present separately, so dropping the union did not drop "
            "the coverage the fixture existed to give")

    # ---- 6. A SUPPRESSED STAGE F IS THE ORDINARY CASE, NOT AN ERROR ------------------------
    thin = {slug: 5 for slug in _FIXTURE_GROUPS}
    nodes = stage_f_nodes(thin)
    _expect(all(node["suppressed"] for node in nodes.values()),
            "stage F suppressed in EVERY stratum is handled and returns a full set of nodes")
    _expect(all(node["reason"] == "cell_below_threshold" for node in nodes.values()),
            "each carrying the cell-size sentence, which is the reason it is hidden")
    mixed = {"cervical_decompression": 400, "cervical_fusion": 5,
             "lumbar_decompression": 400, "lumbar_fusion": 400}
    _expect(all(node["suppressed"] for node in stage_f_nodes(mixed).values()),
            "ALL OR NOTHING: one thin cell suppresses every cell, because a single disclosed "
            "cell beside suppressed ones plus a disclosed total recovers the hidden ones by "
            "subtraction")
    fat = {slug: 400 for slug in _FIXTURE_GROUPS}
    _expect(not any(node["suppressed"] for node in stage_f_nodes(fat).values()),
            "and a stage F whose every cell clears the floor prints in full")
    _expect(stage_f_nodes({}) == {},
            "an empty stratification returns an empty mapping rather than raising")

    # ---- 7. PERSON-CLUSTERED INFERENCE IS ACTUALLY CLUSTERED -------------------------------
    demonstration = _clustered_demonstration()
    fit = demonstration["fit"]
    naive = float(fit["se naive"][0])
    clustered = float(fit["se clustered"][0])
    _expect(fit["n clusters"] < fit["n sets"],
            "the demonstration has participants appearing in several matched sets, which is "
            "what ANALYSIS-PLAN 4.5 permits and what breaks independent matched sets")
    _expect(naive > 0 and clustered > 0, "both standard errors are finite and positive")
    _expect(abs(clustered - naive) / naive > 0.05,
            f"AND THEY DIFFER: clustered {clustered:.5f} against naive {naive:.5f}, a ratio "
            f"of {clustered / naive:.3f}. Equal standard errors here would mean the person "
            f"cluster sums were never taken")
    _expect(abs(fit["beta"][0] - demonstration["true beta"]) < 0.6,
            "and the fit recovered the coefficient the data were generated with, so the "
            "likelihood being differentiated is the conditional one and not something else "
            "that happens to converge")
    covariance = np.asarray(fit["covariance clustered"])
    _expect(covariance.shape == (1, 1) and np.all(np.isfinite(covariance)),
            "the clustered covariance is a finite matrix of the right shape")

    # The identity that proves the cluster code, and not something else, drives the answer:
    # summing the scores by SET must reproduce the set-robust sandwich exactly.
    by_set = fit_conditional_logit(demonstration["design"], demonstration["outcome"],
                                   demonstration["sets"], demonstration["sets"])
    _expect(np.allclose(np.asarray(by_set["covariance clustered"]),
                        np.asarray(by_set["covariance set robust"]), atol=1e-12),
            "clustering ON THE SET reproduces the set-robust sandwich exactly, which is what "
            "says the cluster sums are taken over the code that was passed in")
    _expect(abs(float(by_set["se clustered"][0]) - clustered) > 1e-6,
            "and clustering on the person gives a DIFFERENT answer from clustering on the "
            "set, on the same fit, which is the whole content of the correction")
    _expect(np.allclose(np.asarray(by_set["beta"]), np.asarray(fit["beta"])),
            "while the point estimate is untouched by the choice of cluster, as it must be: "
            "clustering changes the variance and never the coefficient")

    sparse = _clustered_demonstration(n_persons=480, n_sets=60)
    sparse_ratio = (float(sparse["fit"]["se clustered"][0])
                    / float(sparse["fit"]["se naive"][0]))
    _expect(abs(sparse_ratio - 1.0) < abs(clustered / naive - 1.0),
            f"and where participants barely repeat the two standard errors move back towards "
            f"each other, ratio {sparse_ratio:.3f} against {clustered / naive:.3f}, which is "
            f"the sanity check that the difference above is the clustering and not an "
            f"arithmetic slip")

    # ---- 7b. SEPARATION: THE BLIND SPOT THE SUITE HAD --------------------------------------
    # `_clustered_demonstration` above draws its case from the conditional model on purpose so
    # that it never separates, and says so in its own docstring.  That is right for a test
    # about a variance and it left this module with 451 assertions none of which could fire on
    # a runaway fit.  These are that test's missing complement, at four degrees of separation,
    # with a legitimately strong design beside them so the ceiling is shown not to refuse a
    # real effect.  Every rule below is ANALYSIS-PLAN 4.9's, not this module's.
    _expect(MAX_ABS_COEFFICIENT == 10.0,
            "the coefficient ceiling is the plan's own prespecified 10 on the log-odds scale, "
            "an odds ratio of about 22,026, carried as a named constant rather than a literal")
    _expect(SUPPRESSION_REASONS["not_estimable_separation"] == "not estimable (separation)",
            "and the reason a refusal carries is the sentence ANALYSIS-PLAN 4.9 names, not the "
            "convergence sentence, which 4.9 calls false of a fit that converged")
    _expect(issubclass(ModelSeparated, ModelDidNotConverge),
            "a separated fit is a kind of fit that produced no usable answer, so the bootstrap "
            "and every existing guard still catch it, while callers that must tell the two "
            "apart can")

    # RULE 1, THE POINT FIT.  Perfect separation was already caught before the ceiling existed.
    _expect_raises(ModelDidNotConverge,
                   lambda: fit_conditional_logit(*_near_separated_design(0)),
                   "PERFECT separation, the case at maximum exposure in every set, is refused "
                   "because that fit does not converge at all")
    for _seed in (1, 7):
        _expect_raises(ModelSeparated,
                       lambda seed=_seed: fit_conditional_logit(
                           *_near_separated_design(1, seed=seed)),
                       f"and a QUASI-separated fit whose coefficient converges past the "
                       f"ceiling is refused as a SEPARATED fit, at draw {_seed}, which is the "
                       f"case that used to return converged and export an odds ratio")
    _runaway = fit_conditional_logit(*_near_separated_design(1, seed=7),
                                     refuse_above_ceiling=False)
    _runaway_beta = float(_runaway["beta"][0])
    try:
        fit_conditional_logit(*_near_separated_design(1, seed=7))
        _separation_message = ""
    except ModelSeparated as _refusal:
        _separation_message = str(_refusal)
    _expect(bool(_separation_message)
            and f"{_runaway_beta:.4g}" not in _separation_message
            and f"{_runaway_beta:.3f}" not in _separation_message
            and str(int(np.exp(_runaway_beta))) not in _separation_message
            and "22,026" not in _separation_message,
            "AND THE REFUSAL DOES NOT NAME THE VALUE THAT TRIPPED IT. ANALYSIS-PLAN 4.9: the "
            "offending value is not printed, not as a bound and not in a footnote, because "
            "printing it is the clipped number arriving by a second route. The message carries "
            "the ceiling, the plan section and the coefficient's position, and no more")
    _expect(str(int(MAX_ABS_COEFFICIENT)) in _separation_message
            and "4.9" in _separation_message,
            "while it DOES name the rule it applied and the section that fixes it, so the "
            "refusal is auditable against the prespecification rather than merely asserted")
    _expect(bool(_runaway["above ceiling"]) and "coefficient" not in _runaway,
            "and the same fit run without the refusal reports itself as ABOVE THE CEILING and "
            "nothing more: a boolean is the only thing that crosses out of a fit that broke "
            "the ceiling, because a key holding the offending value would be 4.9's forbidden "
            "report under another name")

    # RULE 2, A BOOTSTRAP RESAMPLE.  Retained and counted, never discarded.
    quasi: dict[int, dict[str, Any]] = {}
    for n_break in (1, 2, 3, 4):
        design, outcome, sets, clusters = _near_separated_design(n_break)
        fitted = fit_conditional_logit(design, outcome, sets, clusters)
        seen: list[bool] = []

        def _statistic(indices, ordinal, d=design, y=outcome, st=sets, cl=clusters,
                       log=seen):
            refit = fit_conditional_logit(d[indices], y[indices], st[indices],
                                          resample_group_codes(cl, indices, ordinal),
                                          refuse_above_ceiling=False)
            log.append(bool(refit["above ceiling"]))
            return float(refit["beta"][0])

        boot = cluster_bootstrap(_statistic, clusters, n_resamples=200)
        share = sum(seen) / len(seen) if seen else 0.0
        quasi[n_break] = {"fit": fitted, "boot": boot, "n above": sum(seen),
                          "share": share, "refused": share > BOOTSTRAP_MAX_FAILURE_SHARE}
    _expect(quasi[1]["n above"] > 0 and quasi[1]["boot"]["n failed"] == 0,
            f"a resample above the ceiling is RETAINED and counted, not discarded: "
            f"{quasi[1]['n above']} of 200 sat above it while "
            f"{quasi[1]['boot']['n failed']} were discarded for non-convergence, which are "
            f"different events and are counted separately")
    _expect(np.isfinite(quasi[1]["boot"]["lower"]) and np.isfinite(quasi[1]["boot"]["upper"]),
            "and the resample distribution still HAS its tail, because trimming the resamples "
            "that ran furthest from zero would narrow a published interval, which is the one "
            "thing this rule must never do")

    # RULE 3, THE SHARE.  Both the interval and the point estimate go, even where the point fit
    # is below the ceiling.  This is the rule that catches the fit that prompted the review.
    _expect(quasi[1]["refused"] and quasi[2]["refused"],
            f"MORE THAN {BOOTSTRAP_MAX_FAILURE_SHARE:.0%} OF THE RESAMPLES ABOVE THE CEILING "
            f"REFUSES THE ROW: at one broken set {quasi[1]['share']:.1%} of resamples sat "
            f"above it and at two {quasi[2]['share']:.1%} did, so both rows go, interval and "
            f"point estimate together")
    _expect(not quasi[1]["fit"]["above ceiling"] and not quasi[2]["fit"]["above ceiling"],
            "EVEN THOUGH BOTH POINT FITS ARE THEMSELVES BELOW THE CEILING, which is exactly "
            "what 4.9 rule 3 says: an interval read off a resample distribution that separated "
            "in a quarter of its draws is not an interval on the quantity the row reports")
    _expect(not quasi[3]["refused"] and not quasi[4]["refused"],
            f"while at three and four broken sets the share falls to {quasi[3]['share']:.1%} "
            f"and {quasi[4]['share']:.1%} and the rows still print. A fit below the ceiling "
            f"with a wide interval PRINTS, and the width is the reader's own signal: 4.9 "
            f"bounds what can be exported and does not promise every wide interval disappears")
    _expect(BOOTSTRAP_MAX_FAILURE_SHARE == 0.25,
            "and the share is not a second constant: it is the one ANALYSIS-PLAN 3.8 already "
            "uses for resample failure, reused rather than duplicated")

    # THE REFUSAL, END TO END, AS THE NODE THAT WOULD HAVE BEEN EXPORTED.
    for n_break in (1, 2):
        point = float(np.exp(float(quasi[n_break]["fit"]["beta"][0])))
        node = _odds_ratio_node({"odds ratio": point, "bootstrap lower": float("nan"),
                                 "bootstrap upper": float("nan"),
                                 "refused for separation": quasi[n_break]["refused"]},
                                contributing_n=340)
        _expect(node["suppressed"] and node["reason"] == "not_estimable_separation",
                f"THE REFUSAL, END TO END: the near-separated design at {n_break} broken "
                f"set(s), whose point odds ratio is {point:,.0f}, exports the SEPARATION "
                f"sentence and not a number, and not the convergence sentence either")
        _expect(not any(character.isdigit() for character in node["display"]),
                "and NO DIGIT survives into the rendered string, which is what says the number "
                "was refused rather than clipped, bounded, rounded or reformatted")

    # A LEGITIMATELY STRONG EFFECT IS STILL ACCEPTED.  A ceiling that only ever fires is
    # indistinguishable from one that fires too often, so the refusals above are worth nothing
    # without this.
    design, outcome, sets, clusters = _strong_but_legitimate_design(true_beta=2.0)
    strong = fit_conditional_logit(design, outcome, sets, clusters)
    strong_or = float(np.exp(float(strong["beta"][0])))
    strong_seen: list[bool] = []

    def _strong_statistic(indices, ordinal):
        refit = fit_conditional_logit(design[indices], outcome[indices], sets[indices],
                                      resample_group_codes(clusters, indices, ordinal),
                                      refuse_above_ceiling=False)
        strong_seen.append(bool(refit["above ceiling"]))
        return float(refit["beta"][0])

    strong_boot = cluster_bootstrap(_strong_statistic, clusters, n_resamples=200)
    strong_share = sum(strong_seen) / len(strong_seen)
    _expect(strong["converged"] and not strong["above ceiling"] and strong_or > 5.0,
            f"a large but REAL effect, an odds ratio of {strong_or:.2f} per unit of exposure, "
            f"is fitted and not refused, so the ceiling is not simply refusing everything with "
            f"a big coefficient")
    _expect(strong_share <= BOOTSTRAP_MAX_FAILURE_SHARE,
            f"and {strong_share:.1%} of its resamples sat above the ceiling, inside the "
            f"permitted {BOOTSTRAP_MAX_FAILURE_SHARE:.0%}, so rule 3 does not take it either")
    strong_node = _odds_ratio_node(
        {"odds ratio": strong_or, "bootstrap lower": float(np.exp(strong_boot["lower"])),
         "bootstrap upper": float(np.exp(strong_boot["upper"])),
         "refused for separation": strong_share > BOOTSTRAP_MAX_FAILURE_SHARE},
        contributing_n=340)
    _expect(not strong_node["suppressed"] and strong_node["est"] > 5.0,
            f"SO A REAL EFFECT STILL RETURNS A NUMBER: {strong_node['display']}")

    # THE CEILING BINDS THE COMPLEMENTARY FULL-COHORT MODEL TOO, which 4.9 names and which stop
    # condition 11 makes a halt to apply "to some fits and not others".
    _separated_rows = 200
    _pooled_design = np.column_stack([np.ones(_separated_rows),
                                      np.repeat([0.0, 1.0], _separated_rows // 2)])
    _pooled_outcome = np.repeat([0.0, 1.0], _separated_rows // 2)
    _expect_raises(ModelSeparated,
                   lambda: fit_pooled_logit(_pooled_design, _pooled_outcome,
                                            np.arange(_separated_rows)),
                   "a perfectly separated POOLED fit, where the covariate predicts the outcome "
                   "exactly, is refused at the same ceiling, because 4.9 binds the "
                   "complementary full-cohort model the absolute risks come from as well")

    # ---- 7c. the six recovery day bands, pinned to ANALYSIS-PLAN 4.4 -----------------------
    # The comment above DAY_BANDS used to assert that the plan carried these bands at a time
    # when it did not.  It does now, at version 1.5 section 4.4, in a six-row table headed
    # "The six recovery day bands, fixed a priori".  This pins the transcription so that a
    # drift on either side is a failure here rather than a figure whose strata cannot be
    # checked against the prespecification.
    _expect(DAY_BANDS == ((1, 7, "Days 1" + EN_DASH + "7"),
                          (8, 14, "Days 8" + EN_DASH + "14"),
                          (15, 21, "Days 15" + EN_DASH + "21"),
                          (22, 28, "Days 22" + EN_DASH + "28"),
                          (29, 35, "Days 29" + EN_DASH + "35"),
                          (36, 90, "Days 36" + EN_DASH + "90")),
            "the six day bands are ANALYSIS-PLAN 4.4's own, character for character, including "
            "the en-dash in every display label")
    _expect(len(DAY_BANDS) == 6 and DAY_BANDS[4][1] == 35 and DAY_BANDS[5][0] == 36,
            "the first five bands are the accrual window of post-discharge days 1 to 35 in "
            "calendar weeks and the sixth carries the remainder of the 90-day horizon")
    _expect(all(DAY_BANDS[i][1] + 1 == DAY_BANDS[i + 1][0] for i in range(5)),
            "and the bands abut with no gap and no overlap, so a day falls in exactly one")
    _expect(_band_of(1) == DAY_BANDS[0][2] and _band_of(35) == DAY_BANDS[4][2]
            and _band_of(90) == DAY_BANDS[5][2],
            "and the band lookup agrees with the table at all three boundaries that matter")

    # ---- 7d. the landmark-condition partition is complementarily suppressed ----------------
    # The three conditions partition the first events and the report prints that partition's
    # own total directly below as the denominator, so one hidden cell beside two disclosed ones
    # is recoverable by subtraction.  This is the rule the stage tables already run through,
    # applied at the table one page further down where it was missing.
    partition = complementary_suppression({"definitional": 4, "data": 300, "computable": 900})
    _expect(partition["definitional"]["suppressed"],
            "a landmark condition below the floor is hidden")
    _expect(partition["data"]["suppressed"]
            and partition["data"]["reason"] == "secondary_suppression",
            "AND ITS SMALLEST DISCLOSABLE NEIGHBOUR IS HIDDEN WITH IT, because the partition's "
            "total is printed as the denominator directly below it and one hidden cell out of "
            "three comes straight back by subtraction")
    _expect(not partition["computable"]["suppressed"],
            "while the rule costs the least information it can: only one neighbour goes")
    _expect(not any(node["suppressed"] for node in complementary_suppression(
                {"definitional": 40, "data": 300, "computable": 900}).values()),
            "and a partition with every cell above the floor prints in full")

    # ---- 8. the numeric core, checked against facts that do not depend on the fixture -------
    knots = (0.0, 1.0, 2.0)
    basis = rcs_basis(np.array([0.0, 0.5, 1.0, 2.0]), knots)
    _expect(basis.shape == (4, len(knots) - 1),
            "a restricted cubic spline with k knots gives k minus 1 columns")
    _expect(abs(basis[0, 0]) < FLOAT_TOLERANCE and abs(basis[2, 0] - 1.0) < FLOAT_TOLERANCE,
            "and its first column is the variable itself")
    _expect_raises(GateError, lambda: rcs_basis([0.0], (1.0, 0.0, 2.0)),
                   "knots out of order are refused rather than silently sorted")
    _expect_raises(GateError, lambda: rcs_basis([0.0], (0.0, 1.0)),
                   "two knots are not a restricted cubic spline")
    generator = np.random.default_rng(SEED)
    design = np.column_stack([np.ones(400), generator.normal(size=400)])
    truth = np.array([-1.0, 0.8])
    outcome = (generator.random(400) < _expit(design @ truth)).astype(float)
    fitted = fit_pooled_logit(design, outcome, np.arange(400))
    _expect(fitted["converged"] and np.all(np.abs(fitted["beta"] - truth) < 0.4),
            "the pooled logistic fit recovers a known coefficient on synthetic data")
    try:
        from statsmodels.api import GLM, families      # type: ignore[import-not-found]
        reference = GLM(outcome, design, family=families.Binomial()).fit()
        _expect(np.all(np.abs(np.asarray(reference.params) - fitted["beta"]) < 1e-6),
                "and agrees with the reference implementation to six decimals, which is what "
                "says the hand-written core is the standard estimator and not a variant")
    except ImportError:                              # pragma: no cover - environment dependent
        _expect(True, "the reference implementation was unavailable and was skipped")
    _expect(_roc_area(np.array([0.9, 0.8, 0.2, 0.1]), np.array([1, 1, 0, 0])) == 1.0,
            "a perfectly ordered predictor scores one under the receiver operating "
            "characteristic")
    _expect(abs(_average_precision(np.array([0.9, 0.8, 0.2, 0.1]),
                                   np.array([1, 1, 0, 0])) - 1.0) < FLOAT_TOLERANCE,
            "and one under the precision recall curve")
    boot = cluster_bootstrap(lambda indices, ordinal: float(indices.size),
                             np.repeat(np.arange(10), 3), n_resamples=8)
    _expect(boot["n resamples"] == 8 and boot["n failed"] == 0,
            "the cluster bootstrap draws whole clusters and counts its own failures")
    first = cluster_bootstrap(lambda i, o: float(i.sum()), np.repeat(np.arange(10), 3),
                              n_resamples=5)
    second = cluster_bootstrap(lambda i, o: float(i.sum()), np.repeat(np.arange(10), 3),
                               n_resamples=5)
    _expect(np.array_equal(first["values"], second["values"]),
            "and it is seeded, so two runs in the same session draw the same resamples")
    codes = resample_group_codes(np.array([0, 0, 1, 1]), np.array([0, 1, 0, 1]),
                                 np.array([0, 0, 1, 1]))
    _expect(len(set(codes.tolist())) == 2,
            "two copies of one cluster become two distinct matched sets in a resample, which "
            "is what stops the variance being understated")

    # ---- 9. the node grammar and the disclosure boundary ------------------------------------
    _expect(count_node(0) == {"suppressed": False, "n": 0, "rounded": False, "display": "0"},
            "a true zero is disclosable, prints as zero, and is not marked as rounded")
    _expect(count_node(TIER_3_MIN_EVENTS + 1)["n"] == round20(TIER_3_MIN_EVENTS + 1),
            "a disclosed count is rendered from the rounded value and floor-tested on the true "
            "one, in that order")
    _expect(count_node(1)["suppressed"] and count_node(TIER_3_MIN_EVENTS)["suppressed"],
            "everything from one to the floor inclusive is suppressed")
    _expect_raises(GateError, lambda: count_node(2.5),
                   "a fractional count is refused rather than rounded, because every count in "
                   "the derived dataset is a true integer")
    _expect_raises(DisclosureError, lambda: suppressed_node("no_such_reason"),
                   "a suppression reason outside the label table is refused")
    estimate = estimate_node(1.384, 1.02, 1.88, unit="odds_ratio", contributing_n=340)
    _expect(estimate["display"] == "1.38 (95% CI 1.02 to 1.88)",
            "an odds ratio prints to two decimals and its interval uses the word 'to', never "
            "a dash, because an interval may cross zero")
    _expect(estimate_node(1.4, 1.0, 2.0, unit="odds_ratio",
                          contributing_n=TIER_3_MIN_EVENTS)["reason"]
            == "contributing_n_below_threshold",
            "an estimate is suppressed on the count of participants behind it, not on its own "
            "value: a median over three people is individual-level data whatever its decimals")
    _expect(estimate_node(float("nan"), 1.0, 2.0, unit="odds_ratio",
                          contributing_n=340)["reason"] == "not_estimable_convergence",
            "and a fit that did not produce a number is not estimable rather than absent")
    risk = estimate_node(0.41, 0.22, 0.77, unit="percent", contributing_n=340,
                         decimals=ABSOLUTE_RISK_DECIMALS)
    _expect(risk["display"] == "0.41% (95% CI 0.22% to 0.77%)",
            "an absolute risk carries the percent sign on all three numbers and prints to the "
            "decimals fixed a priori, because zero decimals would print every risk in this "
            "study as zero")
    quantile = quantile_node([1, 2, 3, 4, 5], unit="count", contributing_n=340)
    _expect(EN_DASH in quantile["display_iqr"] and " to " not in quantile["display_iqr"],
            "an observed quantile range uses the en-dash, which is exactly the case a "
            "confidence interval is not")
    _expect(quantile_node([], unit="count", contributing_n=340)["reason"]
            == "not_estimable_data_unavailable",
            "and an empty value list is not estimable rather than zero")
    _expect_raises(DisclosureError, lambda: assert_display_string(f"a{EM_DASH}b", "a test"),
                   "an em-dash in a display string is refused at the boundary")
    _expect_raises(DisclosureError, lambda: assert_display_string(f"a{MINUS_SIGN}b", "a test"),
                   "and so is a Unicode minus sign")
    partition = complementary_suppression({"a": 400, "b": 5, "c": 380, "d": 360})
    _expect(partition["b"]["reason"] == "cell_below_threshold",
            "the thin cell is suppressed on its own account")
    _expect(sum(1 for node in partition.values() if node["suppressed"]) == 2,
            "and a SECOND cell goes with it, because one hidden cell beside a disclosed total "
            "is recoverable by subtraction")
    _expect(partition["d"]["reason"] == "secondary_suppression",
            "and the second is the smallest disclosable one, so the rule costs the least "
            "information it can")
    _expect(sum(1 for node in complementary_suppression({"a": 400, "b": 5, "c": 3}).values()
                if node["suppressed"]) == 2,
            "two already-hidden cells need no third")

    # ---- 10. the early-landmark weight rule, and its three obliged counts -------------------
    # The SAME fixture the end-to-end run reads, rather than a smaller one: the counts below
    # and the counts the report prints should be the same object, and a 40-set frame carrying
    # 30 participants is thin enough that a bootstrap on it measures the fixture.
    members = _risk_set_frame(n_sets=90, n_persons=120)
    counts = early_landmark_counts(members)
    _expect(not counts["violations"],
            "the fixture reaches an early landmark only by the two routes the plan names")
    _expect(counts["n affected members"] ==
            counts["n affected cases"] + counts["n affected controls"],
            "count one splits by role and the two halves are the whole")
    _expect(set(counts["by route"]) == set(EARLY_LANDMARK_ROUTES),
            "and it splits again by the two routes, which is what the plan obliges")
    _expect(counts["n affected controls"] > 0,
            "the fixture actually exercises the rule rather than reporting an empty one")
    _expect("n sets losing every control" in counts and "n weighted sets" in counts
            and "n weighted members" in counts,
            "counts two and three are present: the sets that leave the conditional likelihood "
            "altogether, and the weighted sensitivity's own denominator in sets and members")
    _expect(counts["n weighted members"] + counts["n affected members"] == counts["n members"],
            "and the weighted denominator plus the affected members is every member, so the "
            "rule touches exactly what the count says it touches")
    # THE WIRING, END TO END, THROUGH THE FUNCTION THAT ASSEMBLES THE ESTIMATE.  The assertions
    # in part 7b run the fit and the bootstrap directly; this one proves that the association
    # function itself withholds the interval when the plan's failure share is broken, because
    # that is the object the analysis actually reads.
    ordinary = conditional_association(members, adjusted=False, n_resamples=60)
    _expect(np.isfinite(ordinary["step ratio"]["bootstrap lower"])
            and not ordinary["step ratio"]["bootstrap descent trigger"],
            "on a fixture whose exposure overlaps between cases and controls the bootstrap "
            "returns an interval and the trigger stays down, so the new refusal is not simply "
            "refusing everything")
    separated_members = members.copy()
    # Force the near-separated case at the frame level: give every case the strongest exposure
    # its scale allows and every control the weakest, in the sets that carry a signal.
    _signal = ~pd.Series(separated_members["no_computable_step_signal"]).astype(bool)
    _case = pd.Series(separated_members["is_case"]).astype(bool)
    separated_members.loc[_signal & _case, "r72"] = 0.05
    separated_members.loc[_signal & ~_case, "r72"] = 1.30
    _expect_raises(ModelSeparated,
                   lambda: conditional_association(separated_members, adjusted=False,
                                                   n_resamples=20),
                   "AND A SEPARATED POINT FIT PROPAGATES OUT OF THE ASSOCIATION FUNCTION as a "
                   "named separation, so the analysis reaches its existing not-estimable "
                   "branch and never reaches a number to publish")

    stray = members.copy()
    stray.loc[stray.index[0], "member_landmark_post_discharge_day"] = 0
    stray.loc[stray.index[0], "is_case"] = True
    stray.loc[stray.index[0], "member_matched_day"] = 30
    _expect(early_landmark_counts(stray)["violations"],
            "a member reaching an early landmark by neither named route is a stop condition, "
            "because labelling it as one of the two would hide that the sampling produced "
            "something nobody specified")

    # ---- 10b. THE MEMBERS THAT CARRY NO EXPOSURE WINDOW, AT THE CONDITIONAL MODEL -----------
    # ANALYSIS-PLAN 4.4: a landmark day of 1 or less IS the definitional condition, a member
    # carrying it carries no `N`, and it sits outside the co-primary exposure ON EVERY SURFACE,
    # which the plan spells out to include the conditional model of 4.5.  `risk_sets` marks
    # such a member, leaves the no-computable-signal indicator FALSE on it because that
    # indicator is the data condition and only the data condition, and leaves `r72` NULL.  It
    # is the day-of-week relaxation of 4.7 that puts one there, by admitting a control at
    # post-discharge day 3 or 4, and rung 18 cannot remove it because rung 18 is an event rung.
    _expect("structurally_uncomputable_landmark"
            in declared_columns(sql_by_key["risk set model frame"]),
            "the model frame SELECTS the definitional flag rather than deriving a second copy "
            "of the rule, so the condition the fit drops on is the one the derived table "
            "asserts and the two cannot drift apart")
    _expect("structurally_uncomputable_landmark"
            in declared_columns(sql_by_key["negative control frame"]),
            "and so does the negative control frame, so the drop applies wherever the "
            "conditional model is fitted rather than only where the column happened to travel")
    n_structural = int(pd.Series(
        members["structurally_uncomputable_landmark"]).astype(bool).sum())
    _expect(n_structural > 0,
            "the fixture carries members with no exposure window at all, drawn the only way "
            "the relaxation can draw one: a control at post-discharge day 3 or 4 under a case "
            "at day 5 or 6")
    _expect(not bool((pd.Series(members["structurally_uncomputable_landmark"]).astype(bool)
                      & pd.Series(members["no_computable_step_signal"]).astype(bool)).any()),
            "and it carries them the way the derived table does: the definitional condition "
            "and the data condition are never both set on one member, because one is an "
            "exclusion and the other is the exposure")
    _expect(not pd.Series(members.loc[pd.Series(
                members["structurally_uncomputable_landmark"]).astype(bool), "r72"]).notna().any(),
            "and `r72` is null on every one of them, which is what stops a matched-day-4 "
            "member publishing a ratio built from its single reachable post-discharge day")

    # THE FIT RUNS, THE MEMBERS LEAVE, AND THE COUNT COMES BACK BESIDE THE FIT.
    built = conditional_design(members, adjusted=False)
    _expect(built["n structurally uncomputable members dropped"] == n_structural,
            "A FRAME CARRYING SUCH A MEMBER NOW BUILDS ITS DESIGN WITHOUT RAISING. They are "
            "dropped before the exposure block is assembled and their count is returned beside "
            "it, exactly as the discrete-time design returns the structurally uncomputable "
            "DAYS it drops")
    _expect(len(built["frame"]) == len(members) - n_structural
            and built["design"].shape[0] == len(built["frame"]),
            "the returned frame IS the fitted frame, one design row per kept member, so the "
            "outcome, the set code and the cluster code cannot be read off rows the design was "
            "never built from")
    _expect(not pd.Series(
                built["frame"]["structurally_uncomputable_landmark"]).astype(bool).any(),
            "and not one of them survives into the design")
    _expect(ordinary["n structurally uncomputable members dropped"] == n_structural
            and ordinary["n sets losing every control"]
                == built["n sets losing every control"],
            "and the association function carries both counts out beside the fit, which is "
            "where the analysis reads them")
    _expect(ordinary["n members"] < len(members),
            "so the fit's own denominator is smaller than the frame it was handed, which is "
            "why the report prints the fit's `n` and not the frame's")
    _expect(built["n structurally uncomputable members dropped"] == counts["n affected members"]
            and built["n sets losing every control"] == counts["n sets losing every control"],
            "THE TWO READINGS ARE ONE QUANTITY. The flag the derived table carries and the "
            "landmark-day arithmetic the weight rule reads agree member for member and set for "
            "set, which is what lets the report print the count ONCE rather than twice under "
            "two labels a reader would try to add together")

    # A FRAME WITH NO SUCH MEMBER IS UNCHANGED, WHICH IS THE OTHER HALF OF THE CLAIM.
    plain = members[~pd.Series(members["structurally_uncomputable_landmark"]).astype(bool)] \
        .reset_index(drop=True)
    plain_built = conditional_design(plain, adjusted=False)
    _expect(plain_built["n structurally uncomputable members dropped"] == 0
            and plain_built["n sets losing every control"] == 0
            and len(plain_built["frame"]) == len(plain),
            "a frame with no member carrying the definitional condition drops nothing and "
            "counts zero")
    _expect(plain_built["design"].shape == built["design"].shape
            and np.allclose(plain_built["design"], built["design"])
            and plain_built["names"] == built["names"],
            "AND ITS DESIGN IS UNCHANGED, to the last cell: filtering and then building gives "
            "the same matrix as building on a frame that never held one, so the filter adds no "
            "behaviour to the case it does not apply to")

    # COUNT 2 IS NOT COUNT 1 ARITHMETIC, DEMONSTRATED RATHER THAN ASSERTED.  ANALYSIS-PLAN 4.4:
    # matched sets that lose EVERY control "cannot be recovered from" the member count.  Two
    # frames dropping the SAME NUMBER of members leave different numbers of sets in the
    # conditional likelihood, and here are the two frames.
    def _mark_structural(frame: pd.DataFrame, rows: Any) -> pd.DataFrame:
        marked = frame.copy()
        marked.loc[rows, "structurally_uncomputable_landmark"] = True
        marked.loc[rows, "no_computable_step_signal"] = False
        marked.loc[rows, "r72"] = np.nan
        marked.loc[rows, "member_matched_day"] = LANDMARK_OFFSET_DAYS
        marked.loc[rows, "member_landmark_post_discharge_day"] = 0
        marked.loc[rows, "match_rung"] = MATCH_RUNGS[-1]
        return marked

    _is_control = ~pd.Series(plain["is_case"]).astype(bool)
    _sets = pd.Series(plain["set_index"]).astype("int64")
    _victim = int(_sets[_is_control].iloc[0])
    _whole_set = plain.index[_is_control & (_sets == _victim)]
    _spread = [plain.index[_is_control & (_sets == code)][0]
               for code in list(dict.fromkeys(_sets[_is_control].tolist()))[:len(_whole_set)]]
    emptied = _mark_structural(plain, _whole_set)
    spread = _mark_structural(plain, _spread)
    emptied_counts = structural_member_counts(emptied)
    spread_counts = structural_member_counts(spread)
    _expect(len(_whole_set) > 1
            and emptied_counts["n structurally uncomputable members dropped"]
                == spread_counts["n structurally uncomputable members dropped"],
            "two frames that lose exactly the same number of members")
    _expect(emptied_counts["n sets losing every control"] == 1
            and spread_counts["n sets losing every control"] == 0,
            "AND ONE OF THEM LOSES A WHOLE SET FROM THE LIKELIHOOD WHILE THE OTHER LOSES NONE. "
            "That is why the second count is taken separately: a set with no control "
            "contributes nothing to a conditional likelihood and leaves it altogether, and no "
            "reader could recover which of these two frames they were looking at from the "
            "member count alone")
    _expect(conditional_design(emptied, adjusted=False)["n sets losing every control"] == 1,
            "and the design reports it from the same place the fit is built, so the count "
            "printed beside an estimate is the count that estimate was subject to")

    # THE HALT THIS REPLACED, PINNED SO IT CANNOT COME BACK QUIETLY.
    contaminated = members.copy()
    contaminated["structurally_uncomputable_landmark"] = False
    _expect_raises(GateError, lambda: conditional_design(contaminated, adjusted=False),
                   "A FRAME WHOSE FLAG HAS BEEN WIPED FALSE STILL HALTS, and it halts in the "
                   "exposure block, because such a member reads as carrying a computable step "
                   "signal while holding no ratio. That halt is a guard working and an "
                   "analysis failing, and the filter above is what turns it back into a "
                   "counted exclusion rather than into a silent contamination")
    _expect_raises(GateError,
                   lambda: conditional_design(
                       members.drop(columns=["structurally_uncomputable_landmark"]),
                       adjusted=False),
                   "and a frame that cannot express the condition at all is REFUSED rather "
                   "than defaulted to false, because a default would be exactly the silent "
                   "admission of the definitional condition into the data condition that "
                   "ANALYSIS-PLAN 4.4 corrects a surface against")
    _expect_raises(ModelDidNotConverge,
                   lambda: conditional_design(
                       members.assign(structurally_uncomputable_landmark=True), adjusted=False),
                   "and a frame in which no member has an exposure window at all is reported "
                   "as not estimable rather than fitted on members the exposure is undefined "
                   "for")

    # THE THREE VIOLATIONS, EACH ON ITS OWN.
    case_flagged = _mark_structural(plain, plain.index[pd.Series(plain["is_case"]).astype(bool)][:1])
    _expect(structural_member_counts(case_flagged)["violations"],
            "a CASE carrying the definitional condition is a stop condition: cases are read "
            "from the events table under attrition rung 18, which is that condition, so the "
            "two tables disagree about the same window or one of them is stale")
    summed = members.copy()
    _summed_row = summed.index[pd.Series(
        summed["structurally_uncomputable_landmark"]).astype(bool)][0]
    summed.loc[_summed_row, "no_computable_step_signal"] = True
    _expect(structural_member_counts(summed)["violations"],
            "a member carrying the definitional condition AND the no-computable-signal "
            "indicator is a stop condition, because that is an exclusion folded into an "
            "exposure and the plan forbids the two being summed anywhere")
    mismatched = plain.copy()
    mismatched.loc[mismatched.index[0], "structurally_uncomputable_landmark"] = True
    _expect(structural_member_counts(mismatched)["violations"],
            "and a flag disagreeing with the landmark day it is arithmetic on is a stop "
            "condition, because a landmark day of 1 or less is not a rule of its own but the "
            "same condition written in landmark-day terms")
    _expect(not structural_member_counts(members)["violations"],
            "while the frame the DAG actually produces trips none of the three")

    # ---- 11. the whole module, end to end, at three tiers ----------------------------------
    certified = {"features ok": True, "halting": []}
    _expect_raises(GateRefusal,
                   lambda: run_gate(features_result={"features ok": False,
                                                     "halting": ["a wear count is wrong"]},
                                    show_report=False),
                   "a feature validation that did not certify the derived tables stops the "
                   "whole arm before the first query is priced")
    _expect_raises(GateRefusal, lambda: run_gate(show_report=False),
                   "and so does a missing feature-validation result: there is no default for "
                   "that and there must never be one")

    outcomes: dict[int, dict[str, Any]] = {}
    for label, n_events, expected_tier in (("tier four", TIER_3_MIN_EVENTS - 5, 4),
                                           ("tier three", TIER_3_MIN_EVENTS + 15, 3),
                                           ("tier two", TIER_2_MIN_EVENTS + 12, 2)):
        frames = _fixture_frames(n_gate_events=n_events)
        runtime = _FakeRuntime(frames)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            ran = run_gate(features_result=certified, q_guarded=runtime.q_guarded,
                           dry_run_gb=runtime.dry_run_gb, n_resamples=12, show_report=True)
        printed = buffer.getvalue()
        outcomes[expected_tier] = ran
        _expect(ran["tier"]["index"] == expected_tier,
                f"{label}: the fixture's deciding count lands in the tier it was built for")
        ran_keys = [key for key, _, _ in runtime.calls]
        _expect(ran_keys[:len(PHASE_ONE_QUERY_KEYS)] == list(PHASE_ONE_QUERY_KEYS),
                f"{label}: the counting queries run first and nothing else runs before them")
        _expect(ran_keys[len(PHASE_ONE_QUERY_KEYS):]
                == list(queries_for_tier(expected_tier)),
                f"{label}: and then EXACTLY the queries this tier permits, in declared order")
        _expect(all(cap == PLANNED_MAX_GB[key] for key, cap, _ in runtime.calls),
                f"{label}: each query goes out under its own cap")
        _expect(all(note.startswith("06 gate") for _, _, note in runtime.calls),
                f"{label}: and carries a note naming its entry in the session cost log")
        _expect("COST PLAN" in printed and "free dry run" in printed,
                f"{label}: every phase is priced before any of its queries executes")
        _expect(printed.count("rows hidden by policy") == len(runtime.calls),
                f"{label}: every returned frame went through the shape-only printer")
        _expect(set(RESULT_KEYS) <= set(ran),
                f"{label}: the runner returns every declared result key")
        _expect(set(ran["gate"]) == {"stages", "tier", "arm_a"},
                f"{label}: the gate block carries exactly the three keys the contract declares")
        _expect(set(ran["gate"]["tier"]) == {
            "index", "slug", "display_label", "events_lower", "events_upper", "determined_by",
            "event_count_printable", "permitted_analysis_verbatim",
            "permitted_claim_verbatim", "exhibit_set"},
            f"{label}: and the tier record carries exactly the contract's ten keys")
        _expect([stage["letter"] for stage in ran["gate"]["stages"]]
                == list(GATE_STAGE_LETTERS),
                f"{label}: six stages, letters A to F, in that order")
        _expect(all(set(stage) == {"letter", "slug", "display_label", "definition_display",
                                   "unit", "total", "by_group", "components"}
                    for stage in ran["gate"]["stages"]),
                f"{label}: every stage carries exactly the contract's eight keys")
        _expect(ran["gate ok"], f"{label}: and every stop condition held")
        for frame in ran["frames"].values():
            offending = [column for column in frame.columns
                         if column in BANNED_RETURN_COLUMNS]
            _expect(not offending,
                    f"{label}: no returned frame carries a participant-level key, and this "
                    f"one carried {offending}")
        _expect(set(ran["frames"]) <= set(RETURNABLE_FRAME_KEYS),
                f"{label}: the three model frames were fitted and dropped, never returned")

    # ---- 12. what each tier actually produced ----------------------------------------------
    lowest = outcomes[4]
    _expect(lowest["gate"]["arm_a"]["permitted"] is False,
            "at the lowest tier Arm A is not permitted")
    _expect(lowest["gate"]["arm_a"]["estimates"] == {},
            "and its estimates block is empty, which the contract requires and which is a "
            "different fact from every key being suppressed")
    _expect(lowest["gate"]["arm_a"]["reason_display"],
            "with a printed reason, because a blank table reads as a build error")
    _expect(not lowest["gate"]["tier"]["event_count_printable"],
            "the deciding count is below the floor and is not printable")
    _expect(lowest["gate"]["stages"][4]["total"]["suppressed"],
            "so the deciding stage prints the suppression sentence")
    _expect(lowest["gate"]["tier"]["display_label"] == TIER_LABELS[4],
            "AND THE TIER IS STILL REPORTED. That is the whole coincidence: a tier this module "
            "can name over a count it may not print")
    _expect("landmark comparison" not in lowest["detail"],
            "no collider comparison at the lowest tier, and it is refused by name instead")

    middle = outcomes[3]
    _expect(middle["gate"]["arm_a"]["permitted"] is True,
            "at the event-centered tier Arm A is permitted")
    _expect(middle["gate"]["arm_a"]["estimates"]["matched_set_size"]["suppressed"] is False,
            "and the matched-set size distribution, which is a count, is produced")
    _expect(middle["gate"]["arm_a"]["estimates"]["adjusted_odds_per_lower_step_ratio"]["reason"]
            == "not_permitted_by_tier",
            "while the adjusted model is present as a PRINTED REFUSAL rather than as an "
            "absence")
    _expect(middle["gate"]["arm_a"]["estimates"]["median_lead_time"]["reason"]
            == "not_permitted_by_tier",
            "and so is median lead time, which belongs to the highest tier")
    # EXPORT-CONTRACT 3.7's TIER 3 ROW, PINNED KEY BY KEY. It names four keys the tier
    # refuses and nine it produces, and tier 3 is the likeliest tier this study reaches. Before
    # the module adopted 3.7's other eight keys this block carried the set-size distribution
    # and five refusals, which reads as a failed analysis rather than as the analysis the plan
    # prescribes at that tier.
    middle_estimates = middle["gate"]["arm_a"]["estimates"]
    _expect(set(middle_estimates) == set(ESTIMATE_KEYS) and len(ESTIMATE_KEYS) == 13,
            "the block carries all thirteen of 3.7's keys at a permitting tier")
    for refused in ("adjusted_odds_per_lower_step_ratio", "negative_control_window",
                    "median_lead_time", "absolute_risk_translation"):
        _expect(middle_estimates[refused]["reason"] == "not_permitted_by_tier",
                f"3.7's tier 3 row refuses '{refused}' by name")
    for produced in ("matched_set_size", "unadjusted_odds_per_lower_step_ratio",
                     "odds_of_no_computable_step_signal", "collider_rate_with_signal",
                     "collider_rate_without_signal", "collider_rate_ratio_crude",
                     "collider_rate_with_signal_standardized",
                     "collider_rate_without_signal_standardized",
                     "collider_rate_ratio_standardized"):
        _expect(middle_estimates[produced].get("reason") != "not_permitted_by_tier",
                f"and it PRODUCES '{produced}', which is what turns tier 3 from five refusals "
                f"into the association the plan permits there")
    _expect("landmark comparison" in middle["detail"],
            "and the collider evidence is computed on the full-cohort panel")
    # THE SIX RATE CELLS ARE ESTIMATE-SHAPED AND CARRY NO INTERVAL, because ANALYSIS-PLAN 4.4
    # specifies a rate from the rounded numerator over the rounded denominator and specifies no
    # interval for it. A bound prints one number; an interval of zero width would read as a
    # very precise estimate of something nobody estimated.
    for key in ESTIMATE_KEYS:
        node = middle_estimates[key]
        if ESTIMATE_KEY_SHAPE[key] != "bound" or node["suppressed"]:
            continue
        _expect(node["display_ci"] == "" and node["lo"] == node["est"] == node["hi"],
                f"'{key}' is a bound and prints no interval")
        _expect(node["unit"] == ESTIMATE_KEY_UNIT[key],
                f"'{key}' carries the unit 2.4 fixes for it")
    # 5.7's TWO COUNT COLUMNS COME FROM BESIDE THE BLOCK AND NOT FROM INSIDE IT. They are
    # counts, so a block named `estimates` is the wrong home; `07_export.py` takes them as
    # `window_counts=` and refuses at a permitting tier if they are absent.
    _expect(set(middle["table4_window_counts"]) == {"with_signal", "without_signal"},
            "the two window-group count pairs travel beside the gate block, keyed by window "
            "group, because a count does not belong in a block named for estimates")
    _expect(all(set(pair) == {"episode_days", "events"}
                and all(isinstance(v, int) for v in pair.values())
                for pair in middle["table4_window_counts"].values()),
            "each pair is the episode-days at risk and the acute-care events, as TRUE "
            "integers, so the floor is applied once and at the export boundary")
    _expect(not any(key.startswith("collider_") or key.endswith("_step_ratio")
                    or key == "odds_of_no_computable_step_signal"
                    for key in middle["estimates extra"]),
            "and nothing 3.7 now declares is still being returned outside the block, because "
            "two routes to one cell is a second thing to drift")

    top = outcomes[2]
    _expect(top["gate"]["tier"]["exhibit_set"] == "alternate",
            "at the step-first tier the whole exhibit set switches, which the export contract "
            "must be amended for before anything is written")
    _expect(top["gate"]["arm_a"]["estimates"]["adjusted_odds_per_lower_step_ratio"]
            .get("reason") != "not_permitted_by_tier",
            "the adjusted model is permitted here and is no longer a tier refusal")
    _expect(top["gate"]["arm_a"]["estimates"]["absolute_risk_translation"]
            .get("reason") != "not_permitted_by_tier",
            "and so is the absolute risk from the complementary full-cohort model")
    _expect(top["gate"]["arm_a"]["estimates"]["absolute_risk_translation"].get("unit")
            in (None, "percent"),
            "which is emitted as an estimate node on the percent scale, not as a percentage "
            "node with a numerator that does not exist")
    _expect("early landmark" in top["detail"] and "unadjusted" in top["detail"],
            "the matched-set frame was read and both conditional fits were attempted")
    _expect(top["detail"]["adjusted"]["step ratio"]["standard error clustered"] > 0,
            "the adjusted fit carries a person-clustered standard error")
    _expect(top["detail"]["discrete time"]["n structurally uncomputable days dropped"] > 0,
            "and the discrete-time panel dropped the structurally uncomputable days, counted "
            "separately, rather than folding them into the data condition")

    # ---- 13. the report, and the budget ------------------------------------------------------
    for index, ran in outcomes.items():
        text = ran["report"]
        _expect(EM_DASH not in text and MINUS_SIGN not in text,
                f"tier {index}: the report carries neither banned dash")
        _expect(not _SNAKE_TOKEN.findall(text),
                f"tier {index}: and no machine token, so no identifier reaches a printed "
                f"surface")
        if index != 4:
            _expect("MEMBERS THE MODEL FITS" in text,
                    f"tier {index}: the event-centered curve says which population it is drawn "
                    f"over, because a figure whose population differs from the model's without "
                    f"saying so is a question a reviewer asks and the paper cannot answer")
            _expect("Members plotted" in text and "dropped" in text,
                    f"tier {index}: and it prints its own denominator and the filter's cost, "
                    f"which is the treatment 4.4 gives every member-level drop in this arm")
        _expect("Denominator:" in text,
                f"tier {index}: every table prints its own denominator")
        _expect("BY NAME" in text and "not perform" in text.lower(),
                f"tier {index}: the report names what the tier did not permit")
        _expect(ran["tier"]["permitted_claim_verbatim"] in text,
                f"tier {index}: and prints the verbatim permitted claim unaltered")
        _expect("NEVER SUMMED" in text,
                f"tier {index}: and says in as many words that the two landmark conditions are "
                f"never added together")
    _expect(SUPPRESSION_REASONS["cell_below_threshold"] in outcomes[4]["report"],
            "at the lowest tier the report prints the suppression sentence where the deciding "
            "count would otherwise be")
    _expect("Absolute risks come from" in outcomes[2]["report"],
            "and at a tier that produces one, absolute risks are printed before relative ones")
    for gap in CONTRACT_GAPS:
        for field in ("what", "problem", "emitted", "amendment"):
            _expect(not _SNAKE_TOKEN.findall(gap[field]),
                    f"the contract gap '{gap['slug']}' prints prose in its {field} field")
            _expect(EM_DASH not in gap[field] and MINUS_SIGN not in gap[field],
                    f"and carries neither banned dash in its {field} field")

    frames = _fixture_frames(n_gate_events=TIER_3_MIN_EVENTS + 15)
    expensive = _FakeRuntime(frames, gb=100.0)
    _expect_raises(GateBudgetExceeded,
                   lambda: run_gate(features_result=certified,
                                    q_guarded=expensive.q_guarded,
                                    dry_run_gb=expensive.dry_run_gb, show_report=False),
                   "a priced total over the budget refuses, with nothing executed and nothing "
                   "billed")
    _expect(not expensive.calls, "and nothing reached the query path at all")
    _expect_raises(GateRefusal,
                   lambda: run_gate(features_result=certified, show_report=False),
                   "with no query path available the module refuses rather than finding its "
                   "own way to the API")
    plan = cost_plan(build_sql(), _FakeRuntime(frames, gb=0.01).dry_run_gb,
                     PHASE_ONE_QUERY_KEYS, budget_gb=GATE_BUDGET_GB, phase="test")
    _expect(plan["fits"] and not plan["over cap"],
            "the priced counting phase fits and the per-query caps are the second guard")

    # ---- 14. the ladder's own arithmetic -----------------------------------------------------
    ladder = read_ladder(_ladder_frame(n_gate_events=40), _FIXTURE_GROUPS)
    _expect(ladder["F"]["total"] == ladder["E"]["total"],
            "stage F stratifies stage E and the two totals agree")
    _expect(sum(ladder["A"]["by_group"].values()) == ladder["A"]["total"],
            "and every margin is summed from TRUE integers, never from rounded parts")
    broken = _ladder_frame(n_gate_events=40)
    broken.loc[broken.index[-1], "n_units"] = 999
    _expect_raises(GateError, lambda: read_ladder(broken, _FIXTURE_GROUPS),
                   "a stratification that does not sum to what it stratifies is refused")
    _expect_raises(GateError, lambda: read_ladder(pd.DataFrame(), _FIXTURE_GROUPS),
                   "and an empty ladder is refused, because there would be no gate to read")
    _expect_raises(GateError,
                   lambda: build_gate_block([], tier_for_events(TIER_2_MIN_EVENTS),
                                            {"not_a_contract_key": count_node(40)}),
                   "a key the export contract does not declare is refused out of the gate "
                   "block, because it would fail the bundle schema in Phase 4 for real money")

    # ---- 15. the summary ---------------------------------------------------------------------
    print("=" * 86)
    print("06_analysis_gate.py SELF-TEST: PASS")
    print("=" * 86)
    print(f"  assertions executed        : {_ASSERTIONS}")
    print(f"  queries built              : {len(QUERY_KEYS)}, of which "
          f"{len(PHASE_ONE_QUERY_KEYS)} count and {len(PHASE_TWO_QUERY_KEYS)} model")
    print( "  every emitted query        : carries the derived-dataset placeholder ONLY, quotes")
    print( "                               no hardcoded project or dataset, contains no")
    print( "                               data-definition statement and no random draw, and")
    print( "                               declares result columns it actually aliases")
    print( "  the three model queries    : emit dense surrogates, so no person, episode or set")
    print( "                               identifier ever reaches the kernel at all")
    print(f"  aggregate budget           : {GATE_BUDGET_GB:,.1f} GiB, about "
          f"${GATE_BUDGET_GB / 1024 * USD_PER_TIB:,.2f}, priced per phase before either runs")
    print( "  the tier decision          : pinned at EVERY boundary, including exactly 20,")
    print(f"                               exactly {TIER_2_MIN_EVENTS} and exactly "
          f"{TIER_1_MIN_EVENTS}. It reads a count and nothing else")
    print( "  a tier with no printable   : pinned. Below the floor the module reports the tier")
    print( "  count                        and prints the suppression sentence for the count.")
    print( "                               At exactly 20 the tier 3 analysis RUNS and its own")
    print( "                               denominator stays unprintable")
    print(f"  refusal by name            : pinned at all four tiers over {len(ANALYSIS_CATALOGUE)}")
    print( "                               named analyses, one of which is refused at EVERY")
    print( "                               tier because the plan forbids it outright")
    print( "  the two landmark conditions: pinned separate, with NO sum available anywhere. The")
    print(f"                               definitional range is post-discharge day "
          f"{STRUCTURAL_DELETION_FIRST_DAY} to {STRUCTURAL_DELETION_LAST_DAY},")
    print( "                               checked against the derived flag, not transcribed")
    print( "  no exposure window         : a member whose window holds fewer than 2")
    print( "                               post-discharge days is DROPPED from the conditional")
    print( "                               model and COUNTED, and the matched sets that lose")
    print( "                               every control that way are counted separately")
    print( "                               because that count cannot be recovered from the")
    print( "                               member one. A frame holding no such member builds")
    print( "                               the identical design, to the last cell")
    print( "  stage F suppressed         : handled as the ORDINARY case, all or nothing, and")
    print( "                               never as an error")
    print( "  person-clustered inference : DEMONSTRATED, not asserted. On synthetic data where")
    print(f"                               participants repeat across sets the clustered "
          f"standard")
    print(f"                               error is {clustered:.5f} against a naive "
          f"{naive:.5f}, a ratio of")
    print(f"                               {clustered / naive:.3f}. Where they barely repeat "
          f"the ratio falls to")
    print(f"                               {sparse_ratio:.3f}. Clustering on the SET reproduces "
          f"the set-robust")
    print( "                               sandwich exactly, and the point estimate is")
    print( "                               untouched by the choice of cluster")
    print(f"  the coefficient ceiling    : PINNED at {MAX_ABS_COEFFICIENT:g} on the log-odds "
          f"scale, an odds ratio of about")
    print( "                               22,026, on EVERY logistic fit in this arm: the")
    print( "                               conditional model, each of its bootstrap resamples,")
    print( "                               and the complementary full-cohort model. A separated")
    print( "                               POINT fit publishes nothing. A separated RESAMPLE is")
    print( "                               RETAINED and counted, never discarded, because")
    print( "                               trimming the tail would narrow a published interval;")
    print(f"                               past {BOOTSTRAP_MAX_FAILURE_SHARE:.0%} of resamples "
          f"above it the interval AND")
    print( "                               the point estimate are both refused. The value that")
    print( "                               tripped it is never printed, as a bound or in a")
    print( "                               footnote. Demonstrated at four degrees of")
    print( "                               separation, with a legitimately strong effect beside")
    print( "                               them that is still fitted and still returns a number")
    print( "  the six day bands          : pinned character for character against the plan's")
    print( "                               own table, boundaries and display labels alike")
    print( "  the collider comparison    : runs on the FULL-COHORT day-indexed panel, crude and")
    print( "                               day-standardized, and neither is labelled causal")
    print( "  nothing participant-level  : no returned frame carries a person, episode or set")
    print( "                               key, checked by walking the returned object")
    print(f"  contract gaps reported     : {len(CONTRACT_GAPS)}, each naming the smallest")
    print( "                               amendment that would give the number a home")
    print( "  cloud access required      : none")


if __name__ == "__main__":
    _run_self_test()
