"""07_export.py - the only module that writes across the compliance boundary.

INSIDE THE PERIMETER (Verily Workbench, Controlled Tier).  This module runs last in Phase 4,
after `06_analysis_gate.py`.  It reads the analysis results already held in memory, renders
them into the sixteen files `prespecification/EXPORT-CONTRACT.md` section 1 declares, and
writes nothing else.  Everything the local side will ever see comes through here.

IT REFUSES TO START UNTIL EVERY UPSTREAM MODULE HAS CERTIFIED ITS OWN OUTPUT.  `04_features.py`
returns `features ok`, `05_analysis_drd.py` returns `drd ok` and `06_analysis_gate.py` returns
`gate ok`, each beside a `halting` list of the reasons.  A module whose declared posture is
refuse by default cannot be the one module in the pipeline with no channel for an upstream
refusal to arrive through: 06's reconciliation failure sets `gate ok` false and says the event
timing frame and the ladder disagree about the count that IS the gate, and 04's author wrote
that a false `features ok` means the analysis modules must not run.  `render_bundle` asks for
all three before it renders anything at all, so a refusal halts before a frame is built rather
than after a bundle is written.

LOCALLY (outside the perimeter).  Nothing in this module runs locally except `--fixture`,
which writes a complete DUMMY bundle at the values of EXPORT-CONTRACT.md section 9.1 and
touches no cloud resource, reads no CDR and needs no credentials.  That fixture is what
`local/figures.py`, `local/tables.py`, `local/ledger.py`, `local/manuscript.py`,
`local/make_strobe.py` and `local/verify.py` run their self-tests against, so all six can be
written and debugged in Phase 0 before a single real count exists.

THE POSTURE IS REFUSE BY DEFAULT.  A defect here is not a bug, it is a disclosure event, so
every frame is proved safe before it is written rather than assembled and hoped over:

  * `disclosure.safe_export()` is the gate.  It is the only function permitted to write into
    the export directory, `kind=` is passed on all sixteen files (without it the
    string-versus-numeric check of 10.4 item 7 silently does not run), and it returns the
    `MANIFEST.csv` row as a dict rather than a bare md5.
  * ROUND AND FLOOR-TEST AT THE BOUNDARY, NEVER BEFORE.  Every count in `{DERIVED}` is a TRUE
    integer.  `disclosable(n)` is asked of the true count, before `round20`;
    `is_legal_disclosed_count(cell)` is asked of the rendered cell, after.  They disagree on 20
    by design, because `round20` maps a true 21 through 29 to the numeral 20, so a displayed 20
    stands on a true count of 21 to 29, never on 20 and never on 30.
  * EXPORTED STATISTICS ARE ROUNDED TO THEIR UNIT'S DECIMALS BEFORE THE GATE SEES THEM.
    Distinctness is computed on the in-memory floats, so a frame of unrounded medians is
    near-unique and is refused even though the printed CSV would look fine.
  * FIGURE 2 IS LONG FORMAT, one row per group per day.  A single-series day-indexed frame is
    100% distinct and trips the near-unique class; four series over ninety days is not.
  * NO IMAGE CROSSES THE BOUNDARY.  The perimeter exports the plotted series, never the plot.

WHY THIS MODULE CARRIES CHECKS OF ITS OWN, WHICH IS NOT A ROUTE AROUND THE GATE.  The
amendment this paragraph used to ask for has landed.  `disclosure.py` now carries
`is_bundle_suppressed()`, which recognises the module's own sentinel by containment and, by
equality, both of the representations the contract fixes for a bundle cell: the bare token
`SUPPRESSED` in a figure CSV (section 4) and the suppression SENTENCE of 7.5 in a table CSV
(section 5).  Its complementary-disclosure class, its partition class and its
`n_suppressed_cells` field all route through it, so the three checks that used to be inert on
every frame that crossed the boundary now fire in the module that owns them, and the copies
this file kept as a workaround are DELETED rather than left to drift.

What remains here is what `safe_export()` has no argument for and 10.4 now specifies as this
module's own three declarations, plus two classes that are about the bundle's representation
rather than about disclosure arithmetic:

  * `composite_count_columns` (10.4 decl. 1), because a table CSV's counts live inside
    composed tokens -- `1,240 (33%)`, `n = 340` -- that `pd.to_numeric` cannot parse and that
    sit in columns which are not count columns at all.
  * `row_partitions` (10.4 decl. 2), because `export_violations`' `partitions` is a sequence
    of COLUMN groups checked across one row, and several of this bundle's partitions run DOWN
    a column across several rows.  A DECLARATION PER COLUMN IS WHERE THE DEFECTS CAME FROM:
    four of them, each a count column somebody did not remember to name, the last being
    Table 2's own `Episodes` and `Complete windows`.  Where a partition is a property of a
    BLOCK rather than of one column -- `debt.by_group`, whose group entries partition the
    pooled one in every count it carries -- the declaration is now derived from the block's
    shape and applied to all of them at once, so a new column inherits the protection instead
    of having to opt into it.  `DEBT_BY_GROUP_COUNT_COLUMNS` and `by_group_member_rows` are
    that seam, and `build_ledger_matched_sets_frame` names both of its count columns for the
    same reason.
  * `UNIT_DECIMALS` and `_round_to_unit` (10.4 decl. 3), applied as each frame is built.
  * the suppression-representation check, which asks whether a hidden cell is spelled the way
    its file kind spells it, a question about the contract's two representations that no
    disclosure predicate answers.
  * the numeral-string check, which replaces the module's string-versus-numeric class on the
    figure CSVs whose schema REQUIRES a column to carry both a numeral and the token.
  * the 10.2 register, checked at the call site here rather than left for `verify.py` to find
    after the bundle has already left the perimeter, together with exception 5's stated
    precondition.

`_contract_violations()` runs over the rendered frame FIRST and `safe_export()` sees the same
frame second.  Both must pass; the small remaining overlap on banned characters and the count
floor is deliberate and cheap.

STOP CONDITIONS, all of which halt and none of which repair:
  * Table 1's `row_order` must be the contiguous ordinal 1 to N (10.2).  The `row_order`
    exemption is what stops the gate noticing a gap, and a gap would disclose which
    prespecified row was dropped.
  * The concept-set registry md5 must equal the one `01_probe.py` wrote in Phase 2 (5.6).
    Both writers call the same pure function, so identical bytes are expected; identical by
    construction is not the same as checked.
  * `attrition.closes` must be true, asserted on the TRUE integers before rounding.
  * A `specification_columns=` declaration outside the 10.2 register is refused here, not left
    for `verify.py` to find after the export has already left the perimeter.  The register is
    keyed by (file, column) and names which of the three registers authorised each grant,
    because at contract 1.6.0 one file draws on two of them.
  * Every upstream module must have certified its own output.  All three certifications are
    required and a missing one is a refusal, not a default.
  * `debt.model_fit.residual_correlation` is READ FROM THE FIT and validated against the
    three-rung residual descent of ANALYSIS-PLAN.md 3.4.  The descent is data-dependent, so a
    hardcoded rung 1 asserts a structure that may not have been fitted and prints that
    assertion into the Table 2 footer.
  * A suppression reason with no sentence in 7.5 halts by name.  `not_estimable_separation`,
    which 06 has emitted since it was written, was that halt until contract 1.7.0 gave 7.5 a
    tenth row; the stop condition stays for the eleventh.
  * THE A-THROUGH-F GATE LEDGER IS MONOTONE NON-INCREASING (7.9).  Each stage is a subset of
    the one above it by its own definition, so a ledger that grows is two different cohorts
    written in one column and there is no reading of it that makes Table 3 part A true.  The
    unit changes once, at D, and the check still holds across it: the events D counts are
    FIRST events, at most one per episode, which is what the attrition ladder's rung 17 says
    when it converts 340 episodes into 40 events.  Asserted on both render paths, because a
    real run's ledger arrives already rendered from 06.
  * A DELTA-SHIFT TIPPING POINT IS A GRID COORDINATE, and both halves of that are now
    refusals rather than sentences.  The grid must be the one ANALYSIS-PLAN.md 3.11 locked --
    seven coordinates extending in 0.5 increments to 4.0 and no further, which 3.11 says is
    what "stops it from being an extension invented later" -- and each reported coordinate
    must be a delta that grid actually walked.  `05_analysis_drd.py` can only ever return
    one, so a value between two of them is a payload defect, and printing it would put a
    Methods sentence on a shift the analysis never evaluated.
  * THE PLAN'S HASH, ITS LOCK DATE AND ITS AMENDMENT LOG COME OFF THE WORKING TREE TOGETHER.
    A hash says WHICH DOCUMENT and only the date says WHICH LOCK of it; reading one live and
    remembering the other is how the bundle came to cite plan v1.5's hash beside v1.3's lock
    timestamp and print both into the Methods.  A `PLAN-HASH.txt` that answers the first and
    not the second is a refusal, not a fall back to a remembered date.
  * THE PRIMARY EXHIBIT SET IS THREE FIGURES AND THREE TABLES, and a fourth of either halts.
    `CLAUDE.md` section 2 rule 7 owns that budget and `ANALYSIS-PLAN.md` section 9 owns the
    main-text list; this module counts it over DISTINCT EXHIBIT NAMES among the blocks
    declaring `exhibit_set = "primary"`, never over the sixteen bundle files and never over
    the nine block keys.  Both counts are wrong for the same reason: this bundle writes one
    CSV per printed thing, so Table 2 has a footer file, Table 3 is two files AND two keys,
    and neither is a second exhibit.  `figure4` and `table4` are SUPPLEMENTARY and are still
    written on every run, still stamped in `MANIFEST.csv` and still carry a full block in
    `results.json`; the supplement is where an exhibit is PRINTED and not a place a file goes
    to be deleted.
  * `debt.unadjusted_contrasts` and `debt.unadjusted_model` are REQUIRED, not optional.
    They are contract 1.9.0's answer to STROBE item 16(a), and nothing breaks by their
    absence, which is the whole reason they are asserted: this module reads the `debt` block
    by named key, so an `05_analysis_drd.py` that had not picked up the contract would have
    its two new keys silently dropped and the bundle would come out one reporting item short
    with nothing red anywhere.  A partial adoption must fail loudly.  `unadjusted_model`
    carries `prespecified: false` and it is DECLARED rather than inferred: the locked plan
    prespecifies an unadjusted association for the other arm and an unadjusted level for
    this one, and neither is an unadjusted contrast, so a Methods section that called this
    quantity planned would have misreported the prespecification.
  * Every mandatory denominator of 3.2 must be in the payload, in a unit 3.2 declares, and
    `figures.figure4` names `event_centered_members` rather than the composite first-event
    count: the curve carries the structural filter the fits carry, so the two differ by the
    members that filter removes and the composite count is somebody else's denominator.

USAGE
    python3 pipeline/07_export.py --fixture v1/local/fixtures/results
    python3 pipeline/07_export.py --self-test
    # in the perimeter, from 06_analysis_gate.py:
    #   from importlib import util; ... export_bundle(results_root, bundle)
"""

from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

# `disclosure` sits beside this file.  The notebook path (`%run 00_config.ipynb`) has already
# put pipeline/ on sys.path; a plain `python3 pipeline/07_export.py` has not, so the fallback
# is not decoration.
try:  # pragma: no cover - exercised by whichever path the caller took
    import disclosure
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import disclosure

from disclosure import (  # noqa: E402  - after the path fix, deliberately
    FIGURE_SUPPRESSED_TOKEN,
    FLOAT_FORMAT,
    MANIFEST_COLUMNS,
    MIN_CELL,
    SUPPRESSION_SENTENCES,
    DisclosureError,
    disclosable,
    is_bundle_suppressed,
    is_legal_disclosed_count,
    md5_of_bytes,
    round20,
    safe_export,
)


class ExportError(RuntimeError):
    """A stop condition in the export path.  Every one of them halts; none warns."""


class ContractViolation(ExportError):
    """The bundle-representation gate refused a frame before `safe_export` saw it."""


# ======================================================================================
# SECTION 7.  THE LABEL TABLE, transcribed from EXPORT-CONTRACT.md.
#
# Section 6 makes section 7 the sole authority for every printed string, and this module
# emits every `display_label`, `column_header`, `block_label` and `reason_display` BY
# LOOKUP.  The only permitted composition is f"{LABELS[slug]} (n = {n:,})".  A slug with no
# entry here has nothing to print, and that is the intended failure.
# ======================================================================================

# 7.1 procedure groups, 7.3 contrasts, 7.4 arms, 7.5 suppression reasons, 7.7 estimator
# rungs, 7.8 sensitivity rows (plotted and supplementary), 7.9 gate stages, 7.10 tiers and
# 7.11 block labels and subgroups, in one flat slug -> display map.
LABELS: dict[str, str] = {
    # 7.1 procedure groups
    "cervical_decompression": "Cervical decompression",
    "cervical_fusion": "Cervical fusion",
    "lumbar_decompression": "Lumbar decompression",
    "lumbar_fusion": "Lumbar fusion",
    "all_groups": "All groups",
    "fusion": "Fusion",
    "decompression": "Decompression",
    # 7.2 attrition rungs, ladder-box labels.  The exclusion-box sentence is the second
    # string on the same rung and lives in RUNG_REASON_DISPLAY: one slug, two printed
    # strings, so one flat dict cannot hold both.
    "program_participants": "Participants in the Controlled Tier release",
    "episode_construction": "Spine surgical episodes",
    "excl_trauma_malignancy_infection": "Episodes after the nonelective-indication exclusions",
    "excl_ed_encounter_not_elective": "Elective episodes",
    "excl_prior_operation_90_days": "Episodes with no prior operation within 90 days",
    "excl_simultaneous_cervical_lumbar": "Episodes at a single anatomic region",
    "excl_region_unspecified_only": "Episodes with an established anatomic region",
    "excl_thoracic_only": "Cervical or lumbar episodes",
    "excl_add_on_code_only": "Episodes defined by a primary procedure code",
    "excl_missing_discharge_date": "Episodes with a recorded discharge",
    "excl_no_wearable_data": "Wearable-linked spine episodes",
    "excl_inadequate_baseline_wear": "Episodes with adequate preoperative baseline wear",
    "excl_not_first_eligible_episode": "First eligible episode per participant",
    "excl_no_computable_post_discharge_window":
        "Episodes with a computable post-discharge day 1 to 35 window",
    "excl_window_truncated_by_death_or_reoperation": "Analytic cohort",
    "analytic_cohort": "Analytic cohort",
    "events_identified": "Acute-care events through day 90",
    "excl_event_without_computable_landmark": "Analyzable acute-care events",
    "events_analyzable": "Analyzable acute-care events",
    # 7.3 contrasts
    "fusion_vs_decompression": "Fusion versus decompression",
    "lumbar_vs_cervical": "Lumbar versus cervical",
    "region_by_fusion_interaction": "Region by fusion interaction",
    "fusion_vs_decompression_cervical": "Fusion versus decompression, cervical",
    "fusion_vs_decompression_lumbar": "Fusion versus decompression, lumbar",
    # 7.4 arms
    "recovery_debt": "Recovery debt",
    "early_warning": "Early warning",
    # 7.5 suppression reasons
    "cell_below_threshold": "20 or fewer, suppressed per All of Us dissemination policy",
    "numerator_suppressed": "suppressed because the count behind it is suppressed",
    "contributing_n_below_threshold": "20 or fewer contributors, suppressed",
    "secondary_suppression": "suppressed to protect a suppressed cell in the same total",
    "not_estimable_cell_size": "not estimable (cell size)",
    "not_estimable_convergence": "not estimable (model did not converge)",
    "not_estimable_data_unavailable": "not estimable (data not available)",
    "not_permitted_by_tier": "not permitted at the feasibility tier reached",
    # The ninth, added at contract 1.6.0.  It is a suppression reason in the MECHANICAL
    # sense only: the node shape is how a value-free result is carried in this bundle, and
    # a contrast that never crosses zero out to the extended grid is the STRONGER finding,
    # not a missing one.  It never enters `suppressed.by_reason` under an R1 rule; it is
    # filed with `"rule": "no crossing"` so `n_entries` still ties out.
    "no_crossing_within_range": "no crossing within the prespecified range",
    # THE TENTH, added at contract 1.7.0, transcribed character-exact from 7.5 and placed
    # LAST because 7.5 places it last.  It is the fourth `not_estimable_*` reason and the
    # tenth ROW, and 7.5 says in terms that those are two different facts: `disclosure.py`
    # holds the vocabulary as an ordered tuple and its test asserts ordered equality
    # against the table, so grouping it with its three siblings would turn that test red
    # for a grouping the contract's prose already states.
    #
    # A QUASI-SEPARATED FIT CONVERGES, which is why the table grew rather than reusing a
    # row.  ANALYSIS-PLAN.md 4.9 refuses any Arm A logistic fit carrying a coefficient
    # whose absolute value exceeds its prespecified ceiling: the cell size was fine, the
    # data were available and the tier permitted the analysis, so three of the near
    # neighbours are simply false of it, and `not_estimable_convergence` is the falsest,
    # because the relative-log-likelihood criterion declared convergence while the
    # coefficient ran off toward infinity.  `06_analysis_gate.py` has emitted this slug
    # since it was written and this module halted by name on it until 7.5 gave it a
    # sentence, which was the correct behaviour for a reason with nothing to print.
    "not_estimable_separation": "not estimable (separation)",
    # 7.7 estimator rungs (the display column of the 3.1.1 table)
    "r_ordered_beta_glmm": "Ordered beta mixed model in R",
    "r_zero_one_inflated_beta_glmm": "Zero-one-inflated beta mixed model in R",
    "py_fractional_logit_gee": "Fractional-response quasi-binomial estimating equations",
    "py_linear_mixed_truncated":
        "Linear mixed model with fitted values truncated to the unit interval",
    "py_nonparametric_day_group_means": "Nonparametric day and group means",
    # 7.8 sensitivity rows, the fourteen plotted
    "pod_anchored_window": "Postoperative day 8–42 window",
    "inpatient_days_censored": "Inpatient days censored",
    "complete_window_direct_regression": "Complete windows, direct regression",
    "observation_weighted": "Weighted for observation",
    "delta_shift_tipping_point": "Delta-shift tipping point",
    "wear_definition_s1": "Wear day at 40% heart-rate adherence",
    "wear_definition_s2": "Wear day at 10 hours plus 100 steps",
    "wear_definition_s3": "Wear day at 8 hours",
    "wear_definition_s4": "Wear day at 12 hours",
    "baseline_window_60_15": "Baseline 15–60 days before surgery",
    "baseline_window_30_1": "Baseline 1–30 days before surgery",
    "device_change_excluded": "Device change excluded",
    "baseline_floor": "Baseline floor at 1,000 steps per day",
    "debt_untruncated": "Debt not truncated at zero",
    # 7.8 sensitivity rows, the ten supplementary.  They carry printed labels because
    # section 6 makes this table the sole authority, and they have no key in this bundle.
    "baseline_steps_adjusted": "Baseline steps adjusted",
    "bmi_multiply_imputed": "Body mass index multiply imputed",
    "weights_without_lagged_wear": "Observation weights without lagged wear",
    "junctions_mirrored": "Junction codes mirrored",
    "cervical_fusion_gap_reclassified": "Cervical fusion gap reclassified",
    "cervical_decompression_gap_stated": "Cervical decompression gap",
    "four_group_model": "Four-group model",
    "truncated_assigned_max_debt": "Truncated windows at maximal debt",
    "fusion_status_non_add_on_only": "Fusion status without add-on codes",
    "baseline_weekday_weekend_split": "Separate weekday and weekend baselines",
    # 7.9 gate stages
    "stage_a_qualifying_episodes": "Qualifying spine episodes by procedure group",
    "stage_b_baseline_wear": "Episodes with at least 7 valid baseline days",
    "stage_c_computable_window": "Episodes with a computable post-discharge window",
    "stage_d_events": "First acute-care events through day 90",
    "stage_e_computable_ratio": "Events with a computable proximal step ratio",
    "stage_f_events_by_stratum": "Events by anatomic region and fusion status",
    # 7.10 tiers
    "full_model": "Full detection model",
    "step_first_exploratory": "Step-first exploratory model",
    "event_centered_only": "Event-centered association only",
    "no_early_warning": "No early-warning modeling",
    # 7.11 block labels and other printed strings
    "block_contrasts": "Primary and key secondary contrasts",
    "block_robustness": "Robustness of the primary contrast",
    "block_subgroups": "Subgroups",
    "subgroup_age_lt_65": "Younger than 65 years",
    "subgroup_age_ge_65": "65 years or older",
    "subgroup_female": "Female sex assigned at birth",
    "subgroup_male": "Male sex assigned at birth",
    "subgroup_bmi_lt_30": "Body mass index under 30",
    "subgroup_bmi_ge_30": "Body mass index 30 or above",
    "subgroup_device_byod": "Participant-owned device",
    "subgroup_device_wear": "Program-provided device",
    # 7.15, the gate exhibits' printed strings.  TWENTY at contract 1.7.0: the fifteen
    # `Quantity` values of table3_gate_part_b.csv, the two Figure 4 series and the three
    # Table 4 window groups.  There is one row of 7.15 for every key of
    # `gate.arm_a.estimates`, so the two keys 3.7 gained arrive with their labels in the
    # same edit: a key added without one is an unowned printed string.
    # Before 1.6.0 this module composed the five estimate-key strings itself and the
    # contract owned none of them, so `verify.py`'s label assertion had nothing to compare
    # them against.  They are looked up here like every other printed string.
    "gate_tier_reached": "Feasibility tier reached",
    "gate_permitted_claim": "Permitted claim",
    "adjusted_odds_per_lower_step_ratio": "Adjusted odds per lower step ratio",
    "unadjusted_odds_per_lower_step_ratio": "Unadjusted odds per lower step ratio",
    "odds_of_no_computable_step_signal": "Odds with no computable step signal",
    "negative_control_window": "Negative control window",
    "median_lead_time": "Median lead time",
    "matched_set_size": "Controls per case",
    "absolute_risk_translation": "Absolute risk at the reference step ratio",
    "collider_rate_with_signal": "Event rate with a computable step signal",
    "collider_rate_without_signal": "Event rate without a computable step signal",
    "collider_rate_with_signal_standardized":
        "Event rate with a computable step signal, standardized",
    "collider_rate_without_signal_standardized":
        "Event rate without a computable step signal, standardized",
    "collider_rate_ratio_crude": "Rate ratio, crude",
    "collider_rate_ratio_standardized": "Rate ratio, standardized to recovery day bands",
    "event_case": "Cases",
    "matched_control": "Matched controls",
    "collider_with_signal": "With a computable step signal",
    "collider_without_signal": "Without a computable step signal",
    "collider_rate_ratio_row": "Rate ratio, without versus with",
}

# THE RUNTIME HALF OF "THE 7.5 SET IS CLOSED", run at import so a divergence is a stop
# condition rather than a suppressed cell nobody recognises.  `disclosure.py` transcribes
# 7.5 as well, and the failure mode of a transcription is not that it goes wrong loudly:
# it is that the contract grows a row and one of the two copies goes on returning False for
# a cell that is suppressed.  This module no longer keeps its own membership test at all --
# `is_bundle_suppressed` is imported -- so what has to be checked is that the table this
# module PRINTS from and the table that module RECOGNISES from are the same table.
disclosure.assert_suppression_vocabulary(LABELS)

# The 7.5 sentences this module carries that `disclosure.is_bundle_suppressed` does not
# recognise.  IT IS EMPTY AT CONTRACT 1.7.0 and it is computed rather than listed, so it
# stays empty by construction and can never become a second transcription of 7.5.
#
# It exists because the failure mode of two transcriptions of one table is not a loud one.
# `assert_suppression_vocabulary` above checks one direction, that this module's table
# contains every slug the module names.  This checks the other: that every 7.5 sentence
# this module PRINTS is one the module RECOGNISES.  The two directions are different
# questions and only the second one matters for a cell that reaches a frame, because a
# sentence the module does not recognise is a hidden cell no refusal class can see.  The
# ninth reason, `no_crossing_within_range`, was exactly that case for the length of one
# contract version, and the tenth, `not_estimable_separation`, would have been the next;
# `--self-test` reports a non-empty set so neither can be silent.
_SENTENCES_DISCLOSURE_CANNOT_SEE: frozenset[str] = frozenset(
    LABELS[slug] for slug in (
        "cell_below_threshold", "numerator_suppressed", "contributing_n_below_threshold",
        "secondary_suppression", "not_estimable_cell_size", "not_estimable_convergence",
        "not_estimable_data_unavailable", "not_permitted_by_tier",
        "no_crossing_within_range", "not_estimable_separation",
    )
    if not is_bundle_suppressed(LABELS[slug])
)

# 7.2, the exclusion-box sentence.  Empty on the three conversion and terminal rungs, where
# empty means the concept does not apply and never means suppressed.
RUNG_REASON_DISPLAY: dict[str, str] = {
    "program_participants":
        "No qualifying spine procedure concept in the electronic health record",
    "episode_construction":
        "Same-day qualifying procedure records collapsed into one episode; operations on "
        "different dates stay separate episodes until step 13",
    "excl_trauma_malignancy_infection":
        "Trauma, spinal cord injury, malignancy, metastatic disease or spinal infection "
        "recorded in the 30 days before or on the index date",
    "excl_ed_encounter_not_elective":
        "Emergency department encounter immediately before the index operation, with no "
        "coding evidence of an elective episode",
    "excl_prior_operation_90_days":
        "Prior qualifying spine operation within 90 days of the index episode",
    "excl_simultaneous_cervical_lumbar": "Simultaneous cervical and lumbar procedure",
    "excl_region_unspecified_only":
        "Procedure coding that cannot establish an anatomic region",
    "excl_thoracic_only": "Thoracic-only operation, outside the target population",
    "excl_add_on_code_only":
        "Add-on and instrumentation codes only, with no primary procedure code",
    "excl_missing_discharge_date": "No recorded discharge date for the index admission",
    "excl_no_wearable_data": "No Fitbit activity record linked to the participant",
    "excl_inadequate_baseline_wear":
        "Fewer than 7 valid wear days in postoperative days -30 to -8, or a span under 14 "
        "calendar days",
    "excl_not_first_eligible_episode":
        "A later operation by a participant whose first eligible episode is already in the "
        "cohort",
    "excl_no_computable_post_discharge_window":
        "No analyzable day inside post-discharge days 1 to 35 before censoring",
    "excl_window_truncated_by_death_or_reoperation":
        "Accrual window truncated by death or by a repeat spine operation",
    "analytic_cohort": "",
    "events_identified": "",
    "excl_event_without_computable_landmark":
        "Event on post-discharge day 1 to 4, with no computable proximal window",
    "events_analyzable": "",
}

# 7.6 units, display form.  The slug is machine-read; these are what a header prints.
UNIT_HEADER_DISPLAY: dict[str, str] = {
    "activity_days": "Activity days",
    "thousand_steps": "Thousand steps",
    "normalized_activity": "Normalized activity",
    "steps": "Steps per day",
    "days": "Days",
    "percent": "Percent",
    "absolute_risk_percent": "Absolute risk, percent",
    "odds_ratio": "Odds ratio",
    "rate_ratio": "Rate ratio",
    "rate_per_1000_episode_days": "Events per 1,000 episode-days",
    "hours": "Hours",
    "minutes": "Minutes",
    "count": "Episodes",
    "dimensionless": "",
    "information_criterion": "Akaike information criterion",
}

# 2.4 decimals per unit slug.  A continuous statistic is NEVER round20-ed; it is rounded to
# the decimals here, and that rounding is what keeps a 286-row frame of medians off the
# near-unique class.  `steps` and `count` carry a thousands separator on a DISPLAY surface
# only; the exported numeral stays bare.
UNIT_DECIMALS: dict[str, int] = {
    "activity_days": 1,
    "thousand_steps": 1,
    "normalized_activity": 2,
    "steps": 0,
    "days": 1,
    "percent": 0,
    # `absolute_risk_percent` is NOT `percent` with two decimals, and the split is a
    # disclosure decision rather than a rendering one.  A `percent` value in this bundle is
    # a rounded numerator over a rounded denominator at ZERO decimals, and both halves of
    # that rule protect a small numerator from being back-calculated.  A model-predicted
    # absolute risk has no numerator for any rule to protect, and at zero decimals the
    # number this study expects, a 90-day acute-care risk of a few percent, prints as `0%`.
    "absolute_risk_percent": 2,
    "odds_ratio": 2,
    "rate_ratio": 2,
    "rate_per_1000_episode_days": 2,
    "hours": 0,
    "minutes": 0,
    "count": 0,
    "dimensionless": 2,
    "information_criterion": 0,
}

# 7.12 exclusion and censoring reason details.  Keyed by the (step, reason_detail) PAIR the
# `ledger_exclusion_reasons` stage of build_all.sql emits.  Twenty pairs, which is every
# pair the producer emits; a slug the producer adds without an amendment to 7.12 has
# nothing to print, and that is the intended failure.
REASON_DETAIL_LABELS: dict[tuple[int, str], str] = {
    (3, "malignancy"): "Malignancy recorded in the 30 days before or on the index date",
    (3, "metastatic_disease"):
        "Metastatic disease recorded in the 30 days before or on the index date",
    (3, "spinal_cord_injury"):
        "Spinal cord injury recorded in the 30 days before or on the index date",
    (3, "spinal_infection"):
        "Spinal infection recorded in the 30 days before or on the index date",
    (3, "trauma"): "Trauma diagnosis recorded in the 30 days before or on the index date",
    (4, "ed_encounter_present"):
        "Emergency department encounter ending on the index date or within the 2 days "
        "before it",
    (4, "rescue_degenerative_index"):
        "Rescued by a degenerative index diagnosis despite the emergency department "
        "encounter",
    (4, "rescue_degenerative_outpatient_90d"):
        "Rescued by an outpatient degenerative spine diagnosis in the 90 days before the "
        "index date",
    (4, "rescue_elective_coded"):
        "Rescued by elective or scheduled wording on the index admission",
    (12, "baseline_span_under_14_days"):
        "Seven or more valid wear days, spanning under 14 calendar days",
    (12, "fewer_than_seven_valid_days"):
        "Between 1 and 6 valid wear days in the baseline window",
    (12, "no_valid_baseline_day"): "No valid wear day anywhere in the baseline window",
    (14, "no_analyzable_day_in_window"):
        "No analyzable day inside post-discharge days 1 to 35",
    (14, "not_at_risk_in_window"): "Not at risk on any day of post-discharge days 1 to 35",
    (15, "death"): "Accrual window truncated by death",
    (15, "repeat_spine_operation"):
        "Accrual window truncated by a repeat spine operation",
    (16, "censoring_cdr_observation_cutoff"):
        "Censored at the end of the release observation period",
    (16, "censoring_death"): "Censored at death",
    (16, "censoring_none"):
        "Followed to the end of the accrual window with no censoring",
    (16, "censoring_repeat_spine_operation"): "Censored at a repeat spine operation",
}

# 7.13 analysis variables, for the provenance ledger.  Twelve variables, which is every
# variable the `ledger_variable_missingness` stage emits, in that stage's own ORDER BY.
VARIABLE_LABELS: dict[str, str] = {
    "age_at_index": "Age at the index operation",
    "baseline_steps": "Preoperative baseline steps per day",
    "bmi": "Body mass index",
    "charlson_score": "Charlson comorbidity score",
    "daily_deficit": "Daily activity deficit",
    "device_family": "Device family",
    "ethnicity_concept_id": "Ethnicity",
    "los_days": "Length of stay",
    "procedure_group": "Procedure group",
    "r72": "Proximal activity ratio at 72 hours",
    "race_concept_id": "Race",
    "sex_at_birth": "Sex assigned at birth",
}

VARIABLE_DERIVATION: dict[str, str] = {
    "age_at_index":
        "Days from the recorded date of birth to the index operation date, divided by "
        "365.25",
    "baseline_steps":
        "Median steps per day over the valid wear days of the baseline window",
    "bmi":
        "The nearest recorded body mass index in the 365 days before the index date, "
        "inside a plausibility window of 10 to 80 kg per square metre",
    "charlson_score":
        "Quan's ICD-10 Charlson categories over the 365 days before the index date, "
        "weighted and summed under the three hierarchy rules",
    "daily_deficit":
        "One less the normalized activity of an analyzable day inside the accrual window",
    "device_family":
        "The modal Fitbit device family over the 30 days before the index date, ties "
        "broken by the most recent record and then by family name",
    "ethnicity_concept_id":
        "The person table's ethnicity concept, taken as recorded",
    "los_days": "Days from the start to the end of the index admission visit",
    "procedure_group":
        "Anatomic region crossed with fusion status, one of the four groups of section 2.4 "
        "of the analysis plan",
    "r72":
        "Median steps of the proximal window over the participant's own baseline steps",
    "race_concept_id": "The person table's race concept, taken as recorded",
    "sex_at_birth":
        "The person table's sex-at-birth concept, mapped to female, male, or other or "
        "unknown",
}

# --------------------------------------------------------------------------------------
# ledger_variable_provenance.csv declares TEN columns and this module writes all ten.  Who
# owns each of them, now that contract 1.6.0's section 7.14 and its 10.2 ownership register
# have landed and the gap this block used to record is closed:
#
#   variable, n_total, n_missing   the `ledger_variable_missingness` stage of build_all.sql
#   display_label, derivation      section 7.13, transcribed above
#   unit, missing_handling         SECTION 7.14, transcribed below.  Both are printed
#                                  verbatim into a cell, so section 6 requires section 7 to
#                                  be their authority; before 1.6.0 neither had one and
#                                  `verify.py`'s character-equality assertion passed
#                                  vacuously on twenty-four strings.  That is the same
#                                  defect 7.12 and 7.13 closed at 1.5.0, in the same file,
#                                  one column pair later.  Three of the twenty-four are
#                                  also pinned by 5.6's worked example and are
#                                  character-identical to it: baseline_steps, daily_deficit
#                                  and r72.
#   role, source_table,            no section 7 table, and none is owed one: the 10.2
#   source_concept_set             ownership register classes all three MACHINE TOKEN, so
#                                  section 6's rule about printed strings does not reach
#                                  them and `verify.py` skips them in its snake_case
#                                  assertion.  Their values are derived from something that
#                                  exists rather than invented here:
#
#   role                  the six-value vocabulary of EXPORT-CONTRACT.md 5.6, assigned per
#                         variable from the model specification of ANALYSIS-PLAN.md 3.
#   source_table          the DERIVED table stage 19 actually reads the variable out of:
#                         `features` for the ten episode-level rows, `drd_daily` for
#                         `daily_deficit`, `events` for `r72`.  Read off the stage body, not
#                         chosen.  This is what makes `n_total`'s grain agree with the
#                         column beside it, which 5.6 requires; 5.6's own worked example
#                         used to break it by writing `fitbit_daily` for `baseline_steps`
#                         against an `n_total` of 340 EPISODES, and contract 1.6.0 corrects
#                         that example to `features`, which is what this module already
#                         wrote.  The divergence is closed.
#   source_concept_set    the module owning the concept set the variable is built from:
#                         `cs_spine` for `procedure_group`, `cs_condition` for
#                         `charlson_score`, empty (not applicable) for the other ten, which
#                         is what 5.6's worked example shows on all three of its rows.
#
# Every string below obeys the house prose rules: no em-dash, no Unicode minus, and no
# snake_case token in a sentence.
# --------------------------------------------------------------------------------------

# 7.14, the printed unit of each analysis variable.  It is deliberately NOT a slug from 2.4:
# 2.4 fixes the unit of a value NODE in results.json, and this column names the unit of the
# VARIABLE as a reader of the supplement meets it.  Five of the twelve are categorical and
# carry the empty string, which is the not-applicable convention of section 4 and never
# means suppressed.
VARIABLE_UNIT: dict[str, str] = {
    "age_at_index": "Years",
    "baseline_steps": "Steps per day",
    "bmi": "Kilograms per square metre",
    "charlson_score": "Weighted score",
    "daily_deficit": "Normalized activity",
    "device_family": "",
    "ethnicity_concept_id": "",
    "los_days": "Days",
    "procedure_group": "",
    "r72": "Normalized activity",
    "race_concept_id": "",
    "sex_at_birth": "",
}

# 7.14, one prespecified sentence per variable saying what the analysis does with a missing
# value.  A methods commitment fixed before any count exists, and the column a reviewer
# reads this ledger for.  The three variables expected to report ZERO missing each name the
# rung that removed the episodes which would otherwise have been missing: `baseline_steps`
# at step 12, `los_days` at step 10 and `procedure_group` at steps 6, 7 and 8.  A zero in
# `n_missing` on any other row is a finding.
VARIABLE_MISSING_HANDLING: dict[str, str] = {
    "age_at_index":
        "Complete case; the release records a date of birth for every participant",
    "baseline_steps":
        "Complete case; an episode without an adequate baseline is excluded at step 12",
    "bmi":
        "A missing indicator is carried beside the substituted value, so the model never "
        "reads a substitution as an observation; multiple imputation is a supplementary "
        "sensitivity row",
    "charlson_score":
        "An absent category scores zero and a missing indicator records that no qualifying "
        "condition record was found at all",
    "daily_deficit":
        "Not imputed; a missing day is never read as a zero deficit and the observation "
        "weights of 3.7 do the work",
    "device_family":
        "An unclassifiable or absent device model takes the other or unknown level, which "
        "is counted rather than dropped",
    "ethnicity_concept_id": "Reported as its own level; no ethnicity is imputed",
    "los_days":
        "Complete case; an episode with no recorded discharge date is excluded at step 10",
    "procedure_group":
        "Complete case; steps 6, 7 and 8 remove every episode whose anatomic region or "
        "fusion status cannot be established",
    "r72":
        "Not imputed; an event with no computable proximal window is excluded at step 18",
    "race_concept_id": "Reported as its own level; no race is imputed",
    "sex_at_birth":
        "Reported as its own level, including other or unknown; no sex is imputed",
}

# The three machine-token columns, classed as such by the 10.2 ownership register.
VARIABLE_PROVENANCE: dict[str, dict[str, str]] = {
    "age_at_index": {
        "role": "covariate", "source_table": "features", "source_concept_set": ""},
    "baseline_steps": {
        "role": "covariate", "source_table": "features", "source_concept_set": ""},
    "bmi": {
        "role": "covariate", "source_table": "features", "source_concept_set": ""},
    "charlson_score": {
        "role": "covariate", "source_table": "features",
        "source_concept_set": "cs_condition"},
    "daily_deficit": {
        "role": "outcome", "source_table": "drd_daily", "source_concept_set": ""},
    "device_family": {
        "role": "stratifier", "source_table": "features", "source_concept_set": ""},
    "ethnicity_concept_id": {
        "role": "covariate", "source_table": "features", "source_concept_set": ""},
    "los_days": {
        "role": "covariate", "source_table": "features", "source_concept_set": ""},
    "procedure_group": {
        "role": "exposure", "source_table": "features", "source_concept_set": "cs_spine"},
    "r72": {
        "role": "outcome", "source_table": "events", "source_concept_set": ""},
    "race_concept_id": {
        "role": "covariate", "source_table": "features", "source_concept_set": ""},
    "sex_at_birth": {
        "role": "covariate", "source_table": "features", "source_concept_set": ""},
}

# ======================================================================================
# The vocabularies the contract transcribes from ANALYSIS-PLAN.md.  Set equality against
# the plan is verify.py's job; carrying them here is what lets this module build a frame
# in the plan's fixed order rather than in whatever order a dict happened to have.
# ======================================================================================

# 3.3 / 7.2.  (step, slug, kind, unit).  The order is fixed and is not an implementation
# detail: a ladder counts each episode once, at the first rung it fails.
ATTRITION_RUNGS: tuple[tuple[int, str, str, str], ...] = (
    (1, "program_participants", "exclusion", "persons"),
    (2, "episode_construction", "conversion", "persons to episodes"),
    (3, "excl_trauma_malignancy_infection", "exclusion", "episodes"),
    (4, "excl_ed_encounter_not_elective", "exclusion", "episodes"),
    (5, "excl_prior_operation_90_days", "exclusion", "episodes"),
    (6, "excl_simultaneous_cervical_lumbar", "exclusion", "episodes"),
    (7, "excl_region_unspecified_only", "exclusion", "episodes"),
    (8, "excl_thoracic_only", "exclusion", "episodes"),
    (9, "excl_add_on_code_only", "exclusion", "episodes"),
    (10, "excl_missing_discharge_date", "exclusion", "episodes"),
    (11, "excl_no_wearable_data", "exclusion", "episodes"),
    (12, "excl_inadequate_baseline_wear", "exclusion", "episodes"),
    (13, "excl_not_first_eligible_episode", "exclusion", "episodes"),
    (14, "excl_no_computable_post_discharge_window", "exclusion", "episodes"),
    (15, "excl_window_truncated_by_death_or_reoperation", "exclusion", "episodes"),
    (16, "analytic_cohort", "terminal", "episodes"),
    (17, "events_identified", "conversion", "episodes to events"),
    (18, "excl_event_without_computable_landmark", "exclusion", "events"),
    (19, "events_analyzable", "terminal", "events"),
)

# 3.6 / 7.8.  (order, sub_order, slug, axis, render).  Fourteen plotted rows from ten
# ladder rows: row 6 expands to four wear definitions and row 7 to two baseline windows.
SENSITIVITY_ROWS: tuple[tuple[int, int, str, str, str], ...] = (
    (1, 1, "pod_anchored_window", "primary", "marker"),
    (2, 1, "inpatient_days_censored", "primary", "marker"),
    (3, 1, "complete_window_direct_regression", "primary", "marker"),
    (4, 1, "observation_weighted", "primary", "marker"),
    (5, 1, "delta_shift_tipping_point", "latent_logit_shift", "panel"),
    (6, 1, "wear_definition_s1", "primary", "marker"),
    (6, 2, "wear_definition_s2", "primary", "marker"),
    (6, 3, "wear_definition_s3", "primary", "marker"),
    (6, 4, "wear_definition_s4", "primary", "marker"),
    (7, 1, "baseline_window_60_15", "primary", "marker"),
    (7, 2, "baseline_window_30_1", "primary", "marker"),
    (8, 1, "device_change_excluded", "primary", "marker"),
    (9, 1, "baseline_floor", "primary", "marker"),
    (10, 1, "debt_untruncated", "primary", "marker"),
)

# 3.6.  Reported in the supplement, plotted nowhere, no key in this bundle.  Carried so
# that a slug meeting a reader in the supplement is one this module can name, and so the
# set-equality assertion has an explicit exclusion list rather than an inferred one.
SUPPLEMENTARY_SENSITIVITY_ROWS: tuple[str, ...] = (
    "baseline_steps_adjusted",
    "bmi_multiply_imputed",
    "weights_without_lagged_wear",
    "junctions_mirrored",
    "cervical_fusion_gap_reclassified",
    "cervical_decompression_gap_stated",
    "four_group_model",
    "truncated_assigned_max_debt",
    "fusion_status_non_add_on_only",
    "baseline_weekday_weekend_split",
)

CONTRAST_SLUGS: tuple[str, ...] = (
    "fusion_vs_decompression",
    "lumbar_vs_cervical",
    "region_by_fusion_interaction",
    "fusion_vs_decompression_cervical",
    "fusion_vs_decompression_lumbar",
)

SUBGROUP_SLUGS: tuple[str, ...] = (
    "subgroup_age_lt_65",
    "subgroup_age_ge_65",
    "subgroup_female",
    "subgroup_male",
    "subgroup_bmi_lt_30",
    "subgroup_bmi_ge_30",
    "subgroup_device_byod",
    "subgroup_device_wear",
)

# ANALYSIS-PLAN.md 3.4.  The residual descent, which runs INSIDE an estimator rung and is
# not a family descent.  Three rungs, walked top down, each step triggered by a
# COMPUTATIONAL property of the fit and never by the estimate it produces:
#
#   1. continuous-time AR(1) residual, plus a person random intercept and a random linear
#      slope in post-discharge day;
#   2. on non-convergence or `rho_hat` at a boundary of 0 or 1, the residual correlation
#      structure is dropped and the intercept and slope are kept;
#   3. on a singular random-effect covariance or a random-effect correlation past 0.99,
#      the person random intercept only.
#
# `debt.model_fit.residual_correlation` is the DISPLAY of the rung actually reached.  This
# module used to write `"continuous-time AR(1)"` unconditionally, which asserts rung 1 of a
# prespecified descent that is decided by the data: when the descent lands lower the bundle
# claimed a structure that was not fitted, and `table2_adjusted_debt_footer.csv` printed
# that claim in the row a methods reviewer reads it out of.  The value is read from the fit
# and validated against this vocabulary, so a rung slug or display 05 invents has nothing to
# print and that is the intended failure.  The plan owns the ladder; this transcribes it, in
# the plan's order, exactly as ESTIMATOR_RUNGS transcribes 3.5's.
RESIDUAL_STRUCTURE_RUNGS: tuple[tuple[int, str, str], ...] = (
    (1, "continuous_time_ar1_intercept_slope",
     "Continuous-time first-order autoregressive"),
    (2, "intercept_slope_no_residual_correlation",
     "Person random intercept and slope in day"),
    (3, "intercept_only", "Person random intercept only"),
)

RESIDUAL_STRUCTURE_DISPLAY: dict[str, str] = {
    slug: display for _index, slug, display in RESIDUAL_STRUCTURE_RUNGS
}


def residual_correlation_display(fit: Mapping[str, Any]) -> str:
    """The display of the residual rung the fit ACTUALLY reached, validated, never assumed.

    Accepts either spelling 05 may hand over: `residual_structure`, the rung slug, or an
    already-resolved `residual_correlation` display string.  Both are checked against the
    3.4 vocabulary and an unknown value halts, because a residual structure this module
    cannot name is one the Methods cannot describe and one the footer would print raw.
    """
    slug = fit.get("residual_structure")
    if slug is not None:
        if slug not in RESIDUAL_STRUCTURE_DISPLAY:
            raise ExportError(
                f"debt.model_fit.residual_structure is {slug!r}, which is not one of the "
                f"three residual rungs of ANALYSIS-PLAN.md 3.4: "
                f"{sorted(RESIDUAL_STRUCTURE_DISPLAY)}"
            )
        return RESIDUAL_STRUCTURE_DISPLAY[slug]
    display = fit.get("residual_correlation")
    if display in set(RESIDUAL_STRUCTURE_DISPLAY.values()):
        return str(display)
    raise ExportError(
        "debt.model_fit carries no residual structure this module can name. The residual "
        "descent of ANALYSIS-PLAN.md 3.4 is data-dependent, so the rung reached is read "
        "from the fit and never assumed; supply `residual_structure` as one of "
        f"{sorted(RESIDUAL_STRUCTURE_DISPLAY)} or `residual_correlation` as its display."
    )


# 3.1.1, transcribed from ANALYSIS-PLAN.md 3.5.
ESTIMATOR_RUNGS: tuple[tuple[int, str], ...] = (
    (1, "r_ordered_beta_glmm"),
    (2, "r_zero_one_inflated_beta_glmm"),
    (3, "py_fractional_logit_gee"),
    (4, "py_linear_mixed_truncated"),
    (5, "py_nonparametric_day_group_means"),
)

# The slug the POOLED entry of a by-group block carries.  It is the TOTAL, and a total is
# never a member of the partition it totals.  Named once rather than spelled at each of the
# four call sites that ask the question, because "which entry is the total" is the whole of
# the by-group partition and a fifth call site spelling it differently is a hole.
ALL_GROUPS_SLUG = "all_groups"

# ======================================================================================
# 3.5 / 5.2.  `debt.by_group`, and the partition every count column in it shares.
#
# THE PARTITION IS A PROPERTY OF THE BLOCK, NOT OF A COLUMN.  The per-group entries
# partition the pooled one, so one suppressed member of ANY count in the block is
# recoverable by subtracting the disclosed members from the pooled figure standing beside
# them in the same column.  That is one fact about the block's shape and it holds of every
# count in it at once, including counts added to it later.
#
# It used to be written out by hand in exactly one place, beside `share_zero_debt` in
# `_render_debt`, while `n` and `n_complete_windows` -- the two counts Table 2 actually
# PRINTS -- were declared nowhere at all, so a bundle with one suppressed group exported the
# other three and the pooled total clean and the hidden count came back by subtraction.  The
# whole thirteen-check delivery chain passed over it.  Declaring the two columns would have
# closed that instance and left the seam; this tuple closes the seam.
#
# `_render_debt` BUILDS the block's count nodes from this tuple and `build_table2_frame`
# builds Table 2's columns and its row partitions from it, so a count cannot reach the page
# without a row here, and a row here is a declared partition by construction.  A new count
# column inherits the protection instead of having to remember to opt into it.
#
# (node key in `debt.by_group[i]`, key in the payload entry, Table 2 column header).
DEBT_BY_GROUP_COUNT_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("n", "true_n", "Episodes"),
    # A STRICT SUBSET of the group's own `n`: the episodes whose 35-day window is complete.
    # The collapse ladder of ANALYSIS-PLAN.md 2.5 does not read it, so nothing bounds it
    # below the way the ladder bounds `n`, and the plan expects heavy non-wear.  A stratum
    # of sixty episodes with fewer than twenty complete windows is the case this study is
    # likely to produce rather than the corner it might.
    ("n_complete_windows", "true_complete_windows", "Complete windows"),
)

# 7.9.  (letter, slug, definition_display, unit).  The definition is verbatim from the
# protocol's required-count column.
GATE_STAGES: tuple[tuple[str, str, str, str], ...] = (
    ("A", "stage_a_qualifying_episodes",
     "Unique qualifying spine episodes by procedure group", "episodes"),
    ("B", "stage_b_baseline_wear",
     "Episodes with at least 7 valid baseline days in the 8 to 30 days before surgery",
     "episodes"),
    ("C", "stage_c_computable_window",
     "Episodes with at least one computable post-discharge 3-day window", "episodes"),
    ("D", "stage_d_events",
     "First emergency department visits, inpatient readmissions, and composite events "
     "through 90 days", "events"),
    ("E", "stage_e_computable_ratio", "Events with a computable proximal step ratio",
     "events"),
    ("F", "stage_f_events_by_stratum",
     "Events by lumbar and cervical, and by fusion and decompression, strata", "events"),
)

GATE_STAGE_D_COMPONENT_LABELS: tuple[tuple[str, str], ...] = (
    ("first_ed_visits", "First emergency department visits"),
    ("readmissions", "Readmissions"),
    ("composite", "Composite events"),
)

# 7.10.  (index, slug, events_lower, events_upper, permitted_analysis, permitted_claim).
# Both verbatim columns are quoted unaltered from ANALYSIS-PLAN.md 1.2.
TIERS: tuple[tuple[int, str, Any, Any, str, str], ...] = (
    (1, "full_model", 100, None, "Full detection model with held-out performance",
     "Detection performance may be reported as a performance estimate"),
    (2, "step_first_exploratory", 50, 99, "Step-first exploratory model",
     "Association and exploratory performance, explicitly not a prediction tool"),
    (3, "event_centered_only", MIN_CELL, 49, "Event-centered association only",
     "Association only. No prediction-tool claim of any kind"),
    (4, "no_early_warning", None, 19, "No early-warning modeling at all",
     "Feasibility statement only, with the count suppressed"),
)

# 3.7, the THIRTEEN `gate.arm_a.estimates` keys IN THE ORDER THAT SECTION LISTS THEM, which
# is the order 5.5 requires Table 3 part B's rows to be written in.  Alphabetical order was
# wrong the moment there were more than five: it puts the crude collider ratio above the
# adjusted odds and separates the two rate rows from the two ratio rows they belong beside.
# Every key is present at every tier that permits Arm A at all, carrying either a number or
# the `not_permitted_by_tier` sentence, because a key absent from the block is
# indistinguishable from a bug.
#
# SIX COLLIDER KEYS AND NOT FOUR, one per rate cell of Table 4, adopted at contract 1.7.0.
# 5.7 gives that file three rows by two rate columns, which is six rate cells, and 3.7
# declared four keys: the two crude rates and the two ratios.  The STANDARDIZED RATE OF
# EACH WINDOW GROUP had no key, so two printed cells traced to nothing and this module had
# to take them beside the payload or refuse.  ANALYSIS-PLAN.md 4.4 judges the two window
# groups separately -- one may be standardized while the other is withheld -- so two
# conditions judged separately need two cells and therefore two keys.
GATE_ESTIMATE_KEYS: tuple[str, ...] = (
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

# 4.4.  The event-centered window, fixed by ANALYSIS-PLAN.md 9.5 and pinned here so a
# renderer can set its axis before it reads a row.  TWO SERIES, 22 OFFSETS, 44 ROWS, ON
# EVERY RUN AND AT EVERY TIER.  This file keeps its rows and suppresses its cells, which is
# Figure 3's convention and not Figure 2's, and the difference is the axis rather than a
# change of mind: a Figure 2 day is a point on a curve running forward from discharge, so an
# absent day reads as "the series ended", which is true; an event-centered offset is a
# coordinate in a fixed, two-sided window this study published in advance, and a curve that
# silently shortened to the offsets clearing the floor would misstate the window it was
# drawn over.  Two consequences make the choice cheap: the row count is exactly 44 on every
# run, so MANIFEST.csv and the fixture pin an exact number rather than a data-dependent one,
# and `day_relative_to_event` holds 22 distinct values across 44 rows at every tier, so the
# axis never approaches the near-unique ceiling and this file needs no part of exception 3.
FIGURE4_FIRST_OFFSET = -14
FIGURE4_LAST_OFFSET = 7
FIGURE4_OFFSETS: tuple[int, ...] = tuple(
    range(FIGURE4_FIRST_OFFSET, FIGURE4_LAST_OFFSET + 1)
)

# 7.15.  (slug, order).  One series for the cases and one for their post-discharge-day
# matched controls.
FIGURE4_SERIES: tuple[tuple[str, int], ...] = (
    ("event_case", 1),
    ("matched_control", 2),
)

# 5.7.  (window-group slug, crude rate key, standardized rate key, window-group counts key
# or None).  THREE ROWS ON EVERY RUN AND AT EVERY TIER, for the reason 4.4 keeps its 44:
# the three window groups are prespecified here, not discovered in the data, so a file that
# shrank to one row would say the comparison was defined differently rather than that the
# tier forbade it.
#
# COLUMNS 5 AND 6 ARE ESTIMATES AND COLUMNS 3 AND 4 ARE NOT, which is why a row names both
# an estimate key and a counts key.  At contract 1.7.0 all six rate cells trace to a
# `gate.arm_a.estimates` key of 3.7; the two window-group count pairs are counts, are
# floor-tested and `round20`-rounded like every other count cell, and a block named
# `estimates` is the wrong home for them, so they arrive beside the gate block keyed by
# window group.  11.4 carries the open decision about which `results.json` block should own
# them.  The ratio row takes no counts at all: 5.7 leaves both cells empty there, which is
# the not-applicable convention and never a suppression.
TABLE4_ROWS: tuple[tuple[str, str, str, str | None], ...] = (
    ("collider_with_signal", "collider_rate_with_signal",
     "collider_rate_with_signal_standardized", "with_signal"),
    ("collider_without_signal", "collider_rate_without_signal",
     "collider_rate_without_signal_standardized", "without_signal"),
    ("collider_rate_ratio_row", "collider_rate_ratio_crude",
     "collider_rate_ratio_standardized", None),
)

TABLE4_COLUMNS: tuple[str, ...] = (
    "row_order",
    "Window group",
    "Episode-days at risk",
    "Acute-care events",
    "Crude rate per 1,000 episode-days",
    "Standardized rate per 1,000 episode-days",
)

COLLAPSE_LEVELS: dict[str, int] = {
    "four_group": 1,
    "two_group": 2,
    "single_group": 3,
    "no_estimand": 0,
}

# 3.10.  Thirteen mandatory check slugs; a run reporting fewer has skipped one.
CHECK_SLUGS: tuple[str, ...] = (
    "ladder_closes",
    "no_cell_below_floor",
    "no_hardcoded_floor",
    "no_identifier_column",
    "no_date_column",
    "no_near_unique_column",
    "percentages_from_rounded_counts",
    "percentage_suppressed_with_count",
    "secondary_suppression_applied",
    "no_em_dash",
    "labels_match_contract",
    "csv_bytes_stable_across_two_runs",
    "manifest_md5_matches",
)

CHECK_DISPLAY: dict[str, str] = {
    "ladder_closes":
        "The unrounded attrition ladder closes at every rung and in every segment.",
    "no_cell_below_floor":
        "No exported count is between 1 and the disclosure floor.",
    "no_hardcoded_floor":
        "No comparison in the export path writes the disclosure floor as a literal.",
    "no_identifier_column":
        "No exported frame carries a column shaped or named like a participant identifier.",
    "no_date_column": "No exported frame carries a participant-derived date column.",
    "no_near_unique_column":
        "No exported frame carries a near-unique column outside the declared register.",
    "percentages_from_rounded_counts":
        "Every percentage was computed from the rounded numerator over the rounded "
        "denominator and printed to zero decimals.",
    "percentage_suppressed_with_count":
        "No percentage is disclosed beside a suppressed count.",
    "secondary_suppression_applied":
        "No declared partition has exactly one suppressed member.",
    "no_em_dash": "No written string carries an em-dash or a Unicode minus.",
    "labels_match_contract":
        "Every printed label is a verbatim copy of its entry in the contract's label table.",
    "csv_bytes_stable_across_two_runs":
        "Two runs of the exporter wrote byte-identical comma-separated files.",
    "manifest_md5_matches":
        "Every manifest md5 equals the md5 of the bytes read back from disk.",
}

CHECKS_LOCAL_REASSERT: frozenset[str] = frozenset({
    "ladder_closes",
    "no_cell_below_floor",
    "percentage_suppressed_with_count",
    "secondary_suppression_applied",
    "no_em_dash",
    "labels_match_contract",
    "manifest_md5_matches",
})

# 1.  The bundle, path by path, in MANIFEST.csv row order.  No consumer globs, and neither
# does the producer: the tree is a literal here so a seventeenth file cannot appear by
# accident and a sixteenth cannot go missing without the count moving.  3.8 derives the
# sixteen as `1 + 4 + 6 + 5` and every one of those four terms is named below.
BUNDLE_FILES: tuple[str, ...] = (
    "results.json",
    "figures-csv/figure1_strobe_ladder.csv",
    "figures-csv/figure2_daily_activity.csv",
    "figures-csv/figure3_forest.csv",
    "figures-csv/figure4_event_centered_activity.csv",
    "tables-csv/table1_cohort_characteristics.csv",
    "tables-csv/table2_adjusted_debt.csv",
    "tables-csv/table2_adjusted_debt_footer.csv",
    "tables-csv/table3_gate_part_a.csv",
    "tables-csv/table3_gate_part_b.csv",
    "tables-csv/table4_collider_comparison.csv",
    "ledgers-csv/ledger_concept_set_registry.csv",
    "ledgers-csv/ledger_variable_provenance.csv",
    "ledgers-csv/ledger_exclusion_and_censoring_reasons.csv",
    "ledgers-csv/ledger_wear_availability_by_day.csv",
    "ledgers-csv/ledger_matched_set_sizes.csv",
)

BUNDLE_DIRECTORIES: tuple[str, ...] = ("figures-csv", "tables-csv", "ledgers-csv")

# 3.8.  THE EXHIBIT REGISTER: which printed exhibit each `figures`/`tables` key IS, and
# which exhibit set that exhibit belongs to.
#
# THE BUDGET IS COUNTED OVER EXHIBITS, NEVER OVER FILES AND NEVER OVER KEYS.  CLAUDE.md
# section 2 rule 7 fixes the primary set at exactly three figures and three tables and
# sends everything beyond it to the supplement, and it already says that counting bundle
# FILES is not how that budget is checked: this bundle writes one CSV per printed thing,
# so Table 2 has a footer file and Table 3 is two parts.  Counting KEYS is the same
# mistake one level in.  `tables` carries FOUR primary keys for THREE primary tables,
# because 5.4 and 5.5 give each part of Table 3 its own file and 3.8 therefore gives each
# its own key.  So this register names the exhibit each key belongs to, and the budget is
# the count of DISTINCT exhibit names among the primary blocks: computed, not typed.
#
# `figure4` and `table4` are SUPPLEMENTARY, and that is the locked plan's own placement
# rather than a demotion invented here.  ANALYSIS-PLAN.md section 9 owns the main-text
# exhibit list and reads "exactly 3 figures and 3 tables"; 9.5 specifies the
# event-centered curve as the ALTERNATE Figure 2 at 50 or more events, not as a fourth
# primary figure.  Contract 1.6.0 put both in the primary set to close two real gaps --
# the collider comparison had no exhibit anywhere and the event-centered curve had none at
# the 20-to-49 tier -- and the gaps were real; the placement was not.
#
# NOTHING IS DELETED AND THAT IS THE POINT.  Both files keep their contract sections,
# their schemas, their builders, their renderers and their manifest rows, and both are
# still written on every run.  A supplementary exhibit that no longer exists is a worse
# outcome than a primary exhibit that should not have been one, because the collider
# comparison has nowhere else to go.  What moves is the declaration, and only that.
PRIMARY_FIGURE_BUDGET = 3
PRIMARY_TABLE_BUDGET = 3
EXHIBIT_SETS: frozenset[str] = frozenset({"primary", "supplementary"})

FIGURE_EXHIBITS: dict[str, tuple[str, str]] = {
    "figure1": ("Figure 1", "primary"),
    "figure2": ("Figure 2", "primary"),
    "figure3": ("Figure 3", "primary"),
    "figure4": ("Figure 4", "supplementary"),
}

TABLE_EXHIBITS: dict[str, tuple[str, str]] = {
    "table1": ("Table 1", "primary"),
    "table2": ("Table 2", "primary"),
    # Two keys, two files, ONE exhibit.  This pair is the whole reason the budget is
    # counted over distinct exhibit names rather than over `len(results["tables"])`.
    "table3a": ("Table 3", "primary"),
    "table3b": ("Table 3", "primary"),
    "table4": ("Table 4", "supplementary"),
}

# 3.2.  The eight required denominator keys and the unit vocabulary they draw on.  Both
# are checked here rather than assumed, because `_render_denominators` renders whatever
# the payload hands it: without this register a caller that omitted a mandatory
# denominator would produce a bundle that validates locally and has an exhibit pointing at
# a key that is not there.  `event_centered_members` is the ninth, added at contract 1.8.0
# for Figure 4, whose printed denominator had no key of its own to name.
REQUIRED_DENOMINATORS: tuple[str, ...] = (
    "program_participants",
    "episodes_identified",
    "episodes_eligible",
    "episodes_wearable_linked",
    "episodes_baseline_adequate",
    "analytic",
    "analytic_person_days",
    "events_composite",
    "event_centered_members",
)

DENOMINATOR_UNITS: frozenset[str] = frozenset({
    "persons", "episodes", "events", "person-days", "risk-set members",
})

# 10.2.  The whitelist, exception 3 and exception 5, as one register keyed by (file,
# column) so the AUTHORITY is per column and not per file.  Per file was wrong from
# contract 1.6.0 on: `figure2_daily_activity.csv` now declares `day` under exception 3 and
# six statistic columns under exception 5, and a file-level authority string would report
# one of the two registers for a column the other one authorises.  verify.py checks call
# sites against the same union of three registers on arrival and reports which of the three
# authorised each column; checking it here as well means an unauthorised declaration halts
# BEFORE the file is written rather than after it has already left the perimeter.
#
# The three registers are kept apart because their criteria are different and 10.2 says so.
# The whitelist's criterion is "would this column read exactly the same if the cohort were a
# different hundred people".  `day` does not meet it, because which days survive depends on
# the data; a fitted median plainly does not meet it either.  Filing either in the whitelist
# would corrupt that criterion for every future entry.
SPECIFICATION_COLUMN_AUTHORITY: dict[tuple[str, str], str] = {
    # -- the 10.2 whitelist, thirteen grants.  Five of them are Figure 1's, added at
    # contract 1.6.1 to close a margin of one row.  The ladder is nineteen rungs, the
    # module's row floor is `NEAR_UNIQUE_MIN_ROWS` and its test is strictly greater, so the
    # near-unique class has never armed on that file at all: it cleared the gate by one row
    # and by accident, while `step`, `slug` and `reason_display` are 100% distinct and
    # would be refused the moment a twentieth rung landed.  The ladder has already moved
    # twice in this project, from fifteen rungs to nineteen.  Each of the five was tested
    # against the whitelist's own criterion on its own rather than the file being granted
    # whole: all five are the rung vocabulary of ANALYSIS-PLAN.md 2.6 and every one of them
    # reads exactly the same if the cohort is a different hundred people.  The four count
    # columns are NOT granted and are not eligible under any reading, and `closes_exact` is
    # not granted because whether a rung's arithmetic closed is a fact about the data.
    ("figures-csv/figure1_strobe_ladder.csv", "step"): "10.2 whitelist",
    ("figures-csv/figure1_strobe_ladder.csv", "slug"): "10.2 whitelist",
    ("figures-csv/figure1_strobe_ladder.csv", "display_label"): "10.2 whitelist",
    ("figures-csv/figure1_strobe_ladder.csv", "reason"): "10.2 whitelist",
    ("figures-csv/figure1_strobe_ladder.csv", "reason_display"): "10.2 whitelist",
    ("ledgers-csv/ledger_concept_set_registry.csv", "code"): "10.2 whitelist",
    ("ledgers-csv/ledger_variable_provenance.csv", "variable"): "10.2 whitelist",
    ("ledgers-csv/ledger_variable_provenance.csv", "display_label"): "10.2 whitelist",
    ("ledgers-csv/ledger_variable_provenance.csv", "derivation"): "10.2 whitelist",
    ("ledgers-csv/ledger_exclusion_and_censoring_reasons.csv", "reason_detail"):
        "10.2 whitelist",
    ("figures-csv/figure3_forest.csv", "slug"): "10.2 whitelist",
    ("figures-csv/figure3_forest.csv", "display_label"): "10.2 whitelist",
    ("tables-csv/table1_cohort_characteristics.csv", "row_order"): "10.2 whitelist",
    # -- exception 3, a day axis on a curve file.  Two grants.
    ("figures-csv/figure2_daily_activity.csv", "day"): "10.2 exception 3",
    ("ledgers-csv/ledger_wear_availability_by_day.csv", "day"): "10.2 exception 3",
    # -- exception 5, a rounded aggregate statistic on a frame of prespecified strata.
    # Twelve grants across three files, exempt from the near-unique CARDINALITY class and
    # from nothing else.  The exception states a precondition rather than merely a reason:
    # the value is rounded to its unit's decimals before the frame is built, and the row
    # carries a floor-tested contributing count.  `assert_exception_5_preconditions` below
    # asserts both on the frame, because an exemption whose precondition is assumed is an
    # exemption without a precondition.
    ("figures-csv/figure2_daily_activity.csv", "observed_median"): "10.2 exception 5",
    ("figures-csv/figure2_daily_activity.csv", "observed_p25"): "10.2 exception 5",
    ("figures-csv/figure2_daily_activity.csv", "observed_p75"): "10.2 exception 5",
    ("figures-csv/figure2_daily_activity.csv", "fitted_marginal"): "10.2 exception 5",
    ("figures-csv/figure2_daily_activity.csv", "fitted_lo"): "10.2 exception 5",
    ("figures-csv/figure2_daily_activity.csv", "fitted_hi"): "10.2 exception 5",
    ("figures-csv/figure3_forest.csv", "estimate"): "10.2 exception 5",
    ("figures-csv/figure3_forest.csv", "ci_lo"): "10.2 exception 5",
    ("figures-csv/figure3_forest.csv", "ci_hi"): "10.2 exception 5",
    ("figures-csv/figure4_event_centered_activity.csv", "observed_median"):
        "10.2 exception 5",
    ("figures-csv/figure4_event_centered_activity.csv", "observed_p25"):
        "10.2 exception 5",
    ("figures-csv/figure4_event_centered_activity.csv", "observed_p75"):
        "10.2 exception 5",
}

# The twelve exception 5 columns, by file, and the count column whose floor test is the
# other half of the exception's precondition.  A statistic column may be declared only
# beside a count that was floor-tested on its TRUE value, which is what makes "a summary
# over more than twenty people by construction" true whatever the cardinality is.
EXCEPTION_5_COLUMNS: dict[str, tuple[tuple[str, ...], str, str]] = {
    "figures-csv/figure2_daily_activity.csv": (
        ("observed_median", "observed_p25", "observed_p75",
         "fitted_marginal", "fitted_lo", "fitted_hi"),
        "n_contributing", "normalized_activity"),
    "figures-csv/figure3_forest.csv": (
        ("estimate", "ci_lo", "ci_hi"), "n", ""),
    "figures-csv/figure4_event_centered_activity.csv": (
        ("observed_median", "observed_p25", "observed_p75"),
        "n_contributing", "normalized_activity"),
}


def specification_column_authority(relative_path: str, column: str) -> str | None:
    """Which of the three 10.2 registers authorises this column on this file, or None."""
    return SPECIFICATION_COLUMN_AUTHORITY.get((relative_path, column))

# 4.  The figure-CSV suppression token is `disclosure.FIGURE_SUPPRESSED_TOKEN`, imported
# at the top of this file and no longer defined here.  It is the bare word, NOT
# `disclosure.SUPPRESSED`, and 2.5 keeps it out of the approved display vocabulary because
# it never reaches a rendered surface: the renderer maps it to the sentence.  The module
# owns it now because `is_bundle_suppressed` recognises it, and a constant defined in two
# places is a constant that can differ in one of them.

ROUNDING_FOOTNOTE = (
    "Counts are rounded to the nearest 20 in accordance with the All of Us dissemination "
    "policy, so the boxes may not sum exactly. The unrounded ladder was asserted to close "
    "before rounding."
)

CONTRACT_VERSION = "2.0.0"
CONTRACT_RELATIVE_PATH = "prespecification/EXPORT-CONTRACT.md"
PLAN_RELATIVE_PATH = "prespecification/ANALYSIS-PLAN.md"
PLAN_HASH_RELATIVE_PATH = "prespecification/PLAN-HASH.txt"
# `build_all.sql` sits beside this file, in `pipeline/`, in the perimeter and in the
# repository alike.  It is READ and never transcribed: the sampling salt is a DAG constant
# and the one thing this module must not do with it is keep a second copy.  See
# `dag_sampling_salt` for why the file and not the `build_params` table is the cross-check.
BUILD_SQL_NAME = "build_all.sql"
# `DECLARE sampling_salt STRING DEFAULT '<salt>';` at the head of the stored procedure.
# Anchored on the DECLARE and not on the `build_params` SELECT, because the SELECT is
# `sampling_salt AS sampling_salt` and carries no value at all.
BUILD_SQL_SALT_DECLARE = re.compile(
    r"DECLARE\s+sampling_salt\s+STRING\s+DEFAULT\s+'([^'\n]*)'\s*;")
# The heading of ANALYSIS-PLAN.md section 13.  Its table is the authority on how many times
# the locked plan has moved and on which hash each move superseded, and 13's own opening
# paragraph is why the log records the SUPERSEDED hash rather than the resulting one: a
# file cannot contain its own hash.
PLAN_AMENDMENT_HEADING = "## 13. Amendment log"
# The stamp `lock_plan.py` writes on the `locked:` line of PLAN-HASH.txt.
PLAN_LOCK_STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# ======================================================================================
# THE UPSTREAM CERTIFICATIONS.
#
# Every module that runs before this one ends by certifying its own output, as a boolean
# beside the list of reasons it would refuse:
#
#   04_features.py   `features ok`  its author's own words for a false value are "the
#                                   analysis modules must not run".  It is false when a
#                                   deficit is present on a day the panel calls unobserved,
#                                   which is a zero-imputation by another name, or on any of
#                                   the five other structural violations it checks.
#   05_analysis_drd.py `drd ok`     false when the analytic cohort is below the disclosure
#                                   floor, so there is no estimand, and on every guard
#                                   sentence its own ladder raises.
#   06_analysis_gate.py `gate ok`   false when the event timing frame and the ladder
#                                   disagree about how many first events carry a computable
#                                   proximal ratio.  That count IS the gate: it decides the
#                                   tier, the tier decides the exhibit set, and a bundle
#                                   built on a reconciliation failure would print a tier
#                                   nobody can defend.
#
# UNTIL NOW THIS MODULE READ NONE OF THEM.  A payload arrived and was rendered, so a
# refusal three modules upstream was invisible to the one module that writes across the
# compliance boundary and whose declared posture is refuse by default.  The three are read
# here, together, BEFORE anything is rendered: not before the write, which would already be
# too late to be cheap, and not per block, which would let a bundle be half built.
#
# All three are REQUIRED rather than optional.  A missing key is a refusal and not a
# default, because the failure mode of an optional certification is a caller that forgot to
# pass it getting exactly the same result as a caller whose upstream module passed.
# ======================================================================================

UPSTREAM_CERTIFICATIONS: tuple[tuple[str, str, str], ...] = (
    ("features", "features ok", "pipeline/04_features.py"),
    ("drd", "drd ok", "pipeline/05_analysis_drd.py"),
    ("gate", "gate ok", "pipeline/06_analysis_gate.py"),
)


def assert_upstream_certifications(certifications: Any) -> dict[str, Any]:
    """Halt unless `features ok`, `drd ok` and `gate ok` are all true.  Read, never inferred.

    `certifications` maps each of the three names above to that module's own result dict,
    or to any mapping carrying its certification key and its `halting` list.  The whole
    result may be passed: only the two keys are read, and nothing participant-derived is in
    either.

    Every reason from every module is collected before raising, because a caller fixing
    them one traceback at a time makes one round trip through the perimeter per module.
    The `halting` strings are the upstream modules' own prose, written for a reader, so
    they are quoted rather than summarised; none of them carries a count.
    """
    if not isinstance(certifications, Mapping):
        raise ExportError(
            "the export payload carries no `certifications` block. 07_export.py reads "
            "`features ok`, `drd ok` and `gate ok` before it renders anything, and a "
            "missing block is a refusal rather than a default: a caller that forgot to "
            "pass one must not get the same result as a caller whose upstream modules "
            "passed."
        )
    refusing: list[str] = []
    missing: list[str] = []
    read: dict[str, Any] = {}
    for name, key, module in UPSTREAM_CERTIFICATIONS:
        result = certifications.get(name)
        if not isinstance(result, Mapping) or key not in result:
            missing.append(f"{key!r} from {module}")
            continue
        certified = bool(result[key])
        read[key] = certified
        if certified:
            continue
        reasons = [str(r) for r in (result.get("halting") or [])]
        listed = "; ".join(reasons) if reasons else "no reason was returned"
        refusing.append(f"{module} did not certify its output ({key} is false): {listed}")
    if missing:
        raise ExportError(
            "the export payload does not carry every upstream certification. Missing: "
            + ", ".join(missing)
            + ". Each is required and none defaults to true."
        )
    if refusing:
        listed = "\n".join(f"  {i}. {r}" for i, r in enumerate(refusing, 1))
        raise ExportError(
            f"refusing to render the bundle: {len(refusing)} upstream module(s) refused "
            f"their own output.\n{listed}\nNothing has been rendered and nothing has been "
            f"written. An upstream refusal is a stop condition here, not a warning: the "
            f"module that writes across the compliance boundary does not get to be the one "
            f"that ignores it."
        )
    return read


# ======================================================================================
# SECTION 2.  The value node grammar, and the two moments the two predicates are asked at.
# ======================================================================================


class SuppressionLog:
    """The explicit ledger of everything hidden (`results.json.suppressed`, section 3.9).

    A suppressed value is NEVER silently omitted, because silent omission is itself a
    disclosure: it tells the reader which cells were small.  Every node builder that
    suppresses appends here, so `n_entries` cannot drift from the object it describes.
    """

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []
        self.series_points_by_file: dict[str, int] = {}

    def add(
        self,
        *,
        locus: str,
        kind: str,
        reason: str,
        rule: str,
        path: str = "",
        file_row_key: str | None = None,
        column: str | None = None,
    ) -> None:
        self.entries.append({
            "locus": locus,
            "path": path,
            "file_row_key": file_row_key,
            "column": column,
            "kind": kind,
            "reason": reason,
            "reason_display": _suppression_sentence(reason),
            "rule": rule,
        })

    def as_block(self) -> dict[str, Any]:
        by_reason: dict[str, int] = {}
        for entry in self.entries:
            by_reason[entry["reason"]] = by_reason.get(entry["reason"], 0) + 1
        return {
            "entries": list(self.entries),
            "n_entries": len(self.entries),
            "by_reason": by_reason,
            "series_points_by_file": dict(self.series_points_by_file),
        }


def _suppression_sentence(reason: str) -> str:
    """The 7.5 sentence for a suppression reason, or a stop condition naming the slug.

    A bare `KeyError` in a notebook traceback is a poor stop condition for a real one: an
    upstream module emitting a reason section 7.5 does not own is a contract gap, and the
    message should say which slug and which table rather than leaving a reader to work out
    that `LABELS` is the label table.  This was not hypothetical.
    `06_analysis_gate.py` emits `not_estimable_separation` for the case where the
    conditional model separates; 7.5 carried nine reasons and that was not one of them, so
    this function halted by name on it, which was the correct behaviour for a reason with
    nothing to print.  Contract 1.7.0 landed the tenth row and the halt is now unreachable
    for that slug.  It stays for the eleventh.
    """
    try:
        return LABELS[reason]
    except KeyError:
        raise ExportError(
            f"suppression reason {reason!r} has no sentence in EXPORT-CONTRACT.md 7.5, so "
            f"there is nothing to print for it. A reason an upstream module emits and this "
            f"contract does not own is an amendment to 7.5 under the first row of 11.2, "
            f"never a string composed here."
        ) from None


def suppressed_node(reason: str) -> dict[str, Any]:
    """A suppressed value, as the four-key object of section 2.1 and NO numeric key.

    Not a sentinel string, which type-punches a numeric field, and not a null with a
    companion flag, which `value or 0` reads as a real zero and prints.  Arithmetic on a
    dict raises TypeError at the exact expression that mishandled it.
    """
    sentence = _suppression_sentence(reason)
    return {
        "suppressed": True,
        "reason": reason,
        "reason_display": sentence,
        "display": sentence,
    }


def count_node(
    true_n: Any,
    *,
    log: SuppressionLog | None = None,
    path: str = "",
    reason: str = "cell_below_threshold",
    rule: str = "R1 cell below floor",
    force_suppress: bool = False,
) -> dict[str, Any]:
    """Build a count node from a TRUE integer, asking `disclosable` before `round20`.

    THE ORDER IS THE WHOLE POINT.  `true_n` is the count as it came back from BigQuery,
    where every count in `{DERIVED}` is a true integer.  `disclosable(true_n)` decides
    whether it may be disclosed at all; only then does `round20` produce the numeral.
    Asking the other predicate here would have no floor at all, and asking this one of an
    already-rounded cell refuses a legitimate 20.

    `force_suppress` is secondary suppression: the count is disclosable on its own size and
    is hidden anyway, to protect a suppressed sibling in the same total.  It carries the
    `secondary_suppression` sentence rather than the `cell_below_threshold` one, so a
    reader can tell a cell hidden for its own size from a cell hidden for a sibling's.
    """
    if force_suppress or not disclosable(true_n):
        chosen = reason if not force_suppress else "secondary_suppression"
        chosen_rule = rule if not force_suppress else "R1 secondary suppression"
        if log is not None:
            log.add(locus="results.json", path=path, kind="count",
                    reason=chosen, rule=chosen_rule)
        return suppressed_node(chosen)
    rounded = round20(int(true_n))
    return {
        "suppressed": False,
        "n": int(rounded),
        # `rounded` is false ONLY for an exact zero: zero is an absence, never rounded and
        # never suppressed, and suppressing it would make "the share with zero debt"
        # unreportable.
        "rounded": int(true_n) != 0,
        "display": f"{int(rounded):,}",
    }


def percentage_node(
    true_num: Any,
    true_den: Any,
    *,
    log: SuppressionLog | None = None,
    path: str = "",
    force_suppress: bool = False,
) -> dict[str, Any]:
    """A percentage node: rounded numerator over rounded denominator, zero decimals.

    ANALYSIS-PLAN.md section 8 rule 4.  Both halves matter.  A one-decimal percentage
    against a rounded denominator lets a reader back-calculate an exact small numerator,
    and a percentage computed from the TRUE numerator over a rounded denominator does the
    same.  A percentage dies with its count without exception (rule 3), because a disclosed
    percentage times a disclosed denominator recovers the hidden count exactly.
    """
    if force_suppress:
        if log is not None:
            log.add(locus="results.json", path=path, kind="percentage",
                    reason="secondary_suppression", rule="R1 secondary suppression")
        return suppressed_node("secondary_suppression")
    if not disclosable(true_num):
        if log is not None:
            log.add(locus="results.json", path=path, kind="percentage",
                    reason="cell_below_threshold", rule="R1 cell below floor")
        return suppressed_node("cell_below_threshold")
    if not disclosable(true_den):
        if log is not None:
            log.add(locus="results.json", path=path, kind="percentage",
                    reason="numerator_suppressed", rule="R1 cell below floor")
        return suppressed_node("numerator_suppressed")
    num = int(round20(int(true_num)))
    den = int(round20(int(true_den)))
    pct = _percent_integer(num, den)
    return {
        "suppressed": False,
        "pct": pct,
        "num": num,
        "den": den,
        "display": f"{pct}%",
        "display_count": f"{num:,}",
        "display_denominator": f"{den:,}",
    }


def _percent_integer(rounded_num: int, rounded_den: int) -> int:
    """The integer percent `disclosure._percent` renders, as a number rather than a string.

    Same arithmetic and same rounding, deliberately: `f"{x:.0f}"` is round-half-to-even on
    the float, so 37.5 prints 38 and 3.50877 prints 4, and a second implementation that
    rounded differently would put two different percentages in one bundle.
    """
    return int(f"{100.0 * float(rounded_num) / float(rounded_den):.0f}")


def _round_to_unit(value: float, unit: str) -> float:
    """Round a continuous statistic to its unit's decimals (section 2.4), before export.

    `round20` applies to COUNTS ONLY.  A median step count, an adjusted debt or a mean
    normalized activity is never rounded to 20; it is rounded here, and it is disclosable
    only when the count of participants contributing to it satisfies `disclosable`.

    This rounding is also what keeps a long-format curve frame off the near-unique class.
    Distinctness is computed on the IN-MEMORY floats, not on the rendered bytes, so a
    286-row frame of unrounded medians is effectively 100% distinct and is refused even
    though `FLOAT_FORMAT` would have printed something that looked fine.
    """
    return round(float(value), UNIT_DECIMALS[unit])


def _fmt(value: float, unit: str) -> str:
    """Render one number at its unit's decimals, with a thousands separator where 2.4 says."""
    decimals = UNIT_DECIMALS[unit]
    if unit in ("steps", "count", "information_criterion"):
        return f"{int(round(float(value))):,}"
    return f"{float(value):.{decimals}f}"


def estimate_node(
    est: float,
    lo: float,
    hi: float,
    unit: str,
    *,
    level: float = 0.95,
    percent_sign: bool = False,
) -> dict[str, Any]:
    """An estimate node.  A confidence interval ALWAYS uses the word " to ".

    2.2's separator table is not a preference.  A confidence interval may cross zero, so
    "-1.8", en-dash, "3.6" is unreadable, and a column that switches separator by sign is
    worse than one that never switches.
    """
    est_r, lo_r, hi_r = (_round_to_unit(v, unit) for v in (est, lo, hi))
    suffix = "%" if percent_sign else ""
    point = f"{_fmt(est_r, unit)}{suffix}"
    ci = f"95% CI {_fmt(lo_r, unit)}{suffix} to {_fmt(hi_r, unit)}{suffix}"
    return {
        "suppressed": False,
        "est": est_r,
        "lo": lo_r,
        "hi": hi_r,
        "level": level,
        "unit": unit,
        "display": f"{point} ({ci})",
        "display_point": point,
        "display_ci": ci,
    }


def bound_node(est: float, unit: str, *, percent_sign: bool = False) -> dict[str, Any]:
    """A bound: an estimate node with lo == hi == est and an EMPTY `display_ci`.

    A bound is a bound, not an interval.  Giving it interval keys with different numbers
    would invite a renderer to print it as a confidence interval, which is a different and
    much stronger claim.  `percent_sign` carries 2.4's rule that a percent-scale estimate
    node prints the sign on all three numbers, which for a bound is all one number.
    """
    est_r = _round_to_unit(est, unit)
    printed = f"{_fmt(est_r, unit)}{'%' if percent_sign else ''}"
    return {
        "suppressed": False,
        "est": est_r,
        "lo": est_r,
        "hi": est_r,
        "level": 0.95,
        "unit": unit,
        "display": printed,
        "display_point": printed,
        "display_ci": "",
    }


# ======================================================================================
# NON-FINITE VALUES ARRIVE HERE AND ARE SUPPRESSED HERE, WHICH IS THE UPSTREAM MODULE'S
# STATED EXPECTATION AND NOT AN INFERENCE.  `05_analysis_drd.py`'s `_triple()` says it in
# terms: "NON-FINITE MEMBERS PASS THROUGH RATHER THAN BEING REPAIRED. A NaN here means the
# estimate or its interval was not computed, and both renderers that meet it ... and
# 07_export.py at the boundary, suppress on exactly that. Substituting a number would hide
# the one thing the triple is carrying."
#
# Two different facts arrive as two different shapes and are rendered as two different
# nodes, because collapsing them would lose the distinction the triple exists to carry:
#
#   the POINT is not finite      the quantity was not computed at all.  A suppressed node,
#                                with no numeric key, so arithmetic on it raises at the
#                                expression that mishandled it rather than printing a NaN.
#   the point is finite and an   the estimate exists and its uncertainty does not.  A BOUND
#   INTERVAL BOUND is not        node, so the number is reported and no renderer can draw a
#                                confidence band that was never computed.  This is the
#                                bootstrap-failed case and it is the reason the two are not
#                                one rule.
#
# Every estimate node in `debt` and in `sensitivity` is built through these, so the rule is
# in one place rather than at fifteen call sites.
# ======================================================================================


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def estimate_from_triple(
    triple: Any, unit: str, *, percent_sign: bool = False,
    reason: str = "not_estimable_data_unavailable",
) -> dict[str, Any]:
    """An estimate node from an upstream `(est, lo, hi)`, suppressing what was not computed."""
    if triple is None:
        return suppressed_node(reason)
    est, lo, hi = (triple[0], triple[1], triple[2])
    if not _finite(est):
        return suppressed_node(reason)
    if not (_finite(lo) and _finite(hi)):
        return bound_node(float(est), unit, percent_sign=percent_sign)
    return estimate_node(float(est), float(lo), float(hi), unit,
                         percent_sign=percent_sign)


def quantile_from_triple(
    triple: Any, unit: str, *, reason: str = "not_estimable_data_unavailable",
) -> dict[str, Any]:
    """A quantile node from an upstream `(q50, q25, q75)`, suppressing what was not computed.

    A quantile range has no bound form: a median with no quartiles is not a narrower claim,
    it is a different one, so a non-finite member suppresses the whole node.
    """
    if triple is None or not all(_finite(v) for v in triple[:3]):
        return suppressed_node(reason)
    return quantile_node(float(triple[0]), float(triple[1]), float(triple[2]), unit)


def scalar_or_suppressed(
    value: Any, display: str | None = None,
    *, reason: str = "not_estimable_data_unavailable",
) -> dict[str, Any]:
    """A scalar node, or a suppressed node where the constant was not computed.

    `model_fit.aic` is the live case and it is not hypothetical: the fractional-response
    rung of the estimator ladder reports no information criterion at all, so a run that
    descends to it hands over a NaN, and 3.5 declares the key a scalar node with no shape
    for a missing one.  A scalar node carries no `suppressed` key by design, so the only
    node shape that can say "this constant is not available" is the suppressed one.
    """
    if not _finite(value):
        return suppressed_node(reason)
    return scalar_node(value, display)


def pvalue_or_none(p: Any) -> dict[str, Any] | None:
    """A P value node, or `null` where the row has no P value defined."""
    if p is None or not _finite(p):
        return None
    return pvalue_node(float(p))


def quantile_node(q50: float, q25: float, q75: float, unit: str) -> dict[str, Any]:
    """A quantile node.  An observed range uses the EN-DASH, never the word " to ".

    A quantile range of a non-negative quantity never carries a sign, so the en-dash is
    unambiguous there and the word is reserved for the interval that can cross zero.
    """
    q50_r, q25_r, q75_r = (_round_to_unit(v, unit) for v in (q50, q25, q75))
    iqr = f"{_fmt(q25_r, unit)}–{_fmt(q75_r, unit)}"
    return {
        "suppressed": False,
        "q50": q50_r,
        "q25": q25_r,
        "q75": q75_r,
        "unit": unit,
        "display": f"{_fmt(q50_r, unit)} ({iqr})",
        "display_point": _fmt(q50_r, unit),
        "display_iqr": iqr,
    }


def pvalue_node(p: float) -> dict[str, Any]:
    """A P value node.  `P < 0.001` when floored, `P = 0.223` otherwise: house numeral style."""
    floored = float(p) < 0.001
    return {
        "suppressed": False,
        "p": float(p),
        "floored": floored,
        "display": "P < 0.001" if floored else f"P = {float(p):.3f}",
    }


def scalar_node(value: Any, display: str | None = None) -> dict[str, Any]:
    """A constant that is not a result: a window boundary, a threshold, a seed.

    Never suppressed, so it carries no `suppressed` key at all: a consumer that meets one
    and branches on `suppressed` has reached for a node shape that does not apply.
    """
    if display is None:
        display = f"{value:,}" if isinstance(value, int) else str(value)
    return {"value": value, "display": display}


def is_node_suppressed(node: Any) -> bool:
    """True when a results.json node is the suppressed object of 2.1."""
    return isinstance(node, Mapping) and bool(node.get("suppressed", False))


def node_display(node: Any) -> str:
    """The one string that may reach a rendered surface.  Always safe to print.

    Correct for a disclosed node and for a suppressed node without branching, because a
    suppressed node's `display` IS the suppression sentence.
    """
    if node is None:
        return ""
    return str(node["display"])


# ======================================================================================
# THE GATE.
#
# `disclosure.safe_export()` is the gate the contract names, and it is called for all
# fifteen CSVs with `kind=` passed on every one; `results.json` is the sixteenth file and
# 10.4 sends it down a different path, because `safe_export` would accept the `.json` suffix
# and write comma-separated bytes into it with no error at all.  `_contract_violations` runs
# FIRST, over the same rendered frame, and covers the classes `safe_export` has no argument
# for.  The division, class by class, so neither is mistaken for the other:
#
#   class                          safe_export      here
#   ---------------------------------------------------------------------------------
#   path extension                 yes              no
#   near-unique / identifier-like  yes              no      (the module owns cardinality)
#   date-like name and dtype       yes              no
#   banned dash characters         yes              yes     (cheap, and header-inclusive)
#   count floor on a rendered cell yes*             yes     (*only cells to_numeric parses;
#                                                            a display string carrying a
#                                                            thousands separator does not
#                                                            parse, so a table CSV's count
#                                                            columns reach it as NaN and
#                                                            are dropped before the test)
#   kind string-versus-numeric     yes              yes     (a figure CSV column that must
#                                                            carry both a numeral and the
#                                                            SUPPRESSED token is rendered
#                                                            here as an all-string column,
#                                                            which the module then reads as
#                                                            string-only; the numeral-shape
#                                                            check below is what replaces it)
#   complementary disclosure       yes              no      (the module reads a bundle-
#   partition, by column           yes              no       representation hidden cell now,
#                                                            so both classes finally fire
#                                                            where they were written to)
#   partition, by ROW              no               yes     (the module's `partitions` is a
#                                                            sequence of COLUMN groups; the
#                                                            contract's Table 1 blocks and
#                                                            exclusion-ledger partitions are
#                                                            groups of ROWS within a column,
#                                                            and 10.4 specifies the
#                                                            declaration this module holds)
#   composite embedded count       no               yes     (10.4 declaration 1: a count
#                                                            rendered as `1,240 (33%)` or
#                                                            `n = 340` is unparseable to
#                                                            `pd.to_numeric` and lives in a
#                                                            column that is not a count
#                                                            column)
#   suppression representation     no               yes
#   exception 5 preconditions      no               yes     (10.2: a statistic column may be
#                                                            declared only when it is rounded
#                                                            to its unit's decimals and its
#                                                            row carries a floor-tested count)
#
# This is not a route around the gate.  Both must pass and the overlap is deliberate.
# ======================================================================================

_NUMERAL = re.compile(r"^-?(?:\d+)(?:\.\d+)?$")
_DISPLAY_COUNT = re.compile(r"^-?\d{1,3}(?:,\d{3})*$|^-?\d+$")


def _parse_display_count(cell: Any) -> int | None:
    """The integer behind a rendered count cell, or None when the cell is not a count.

    `1,240` is the house numeral style and is what a table CSV writes, so the separator has
    to come back out before the rendered cell can be gate-tested.  A suppression sentence,
    an empty cell and a free-text cell all return None and are handled by their own class.
    """
    if isinstance(cell, bool):
        return None
    if isinstance(cell, (int,)):
        return int(cell)
    if isinstance(cell, float):
        return int(cell) if float(cell).is_integer() else None
    if not isinstance(cell, str):
        return None
    text = cell.strip()
    if text == "" or _cell_is_hidden(text):
        return None
    if not _DISPLAY_COUNT.match(text):
        return None
    return int(text.replace(",", ""))


_COMPOSITE_COUNT = re.compile(
    r"^(?:n\s*=\s*)?(-?\d{1,3}(?:,\d{3})*|-?\d+)(?:\s*\(\d+%\))?$"
)


def _embedded_counts(cell: Any) -> list[int]:
    """The counts a rendered TABLE cell carries, in the two shapes this bundle writes.

    A table CSV's counts do not live in count columns.  They live inside composed display
    tokens -- `1,240 (33%)` in a Table 1 body cell and `n = 340` in a Table 2 episodes
    cell -- beside cells that are medians, estimates and sentences in the same column.  So
    the gate cannot read the column as a count column, and without this it would not test
    those counts at all, which is the one failure mode that leaves no mark in the file it
    damages.

    Deliberately narrow.  `62 (54–70)` is a median with an interquartile range and matches
    nothing here, because its parenthetical is a range and not a percent.  `0.62 (95% CI
    0.55 to 0.69)` matches nothing for the same reason.  A cell that matches neither shape
    carries no count and is left to its own class.
    """
    if not isinstance(cell, str):
        return []
    text = cell.strip()
    if text == "" or _cell_is_hidden(text):
        return []
    match = _COMPOSITE_COUNT.match(text)
    if not match:
        return []
    return [int(match.group(1).replace(",", ""))]


# Which spelling of "hidden" each file kind is allowed to write.  Section 4 fixes the bare
# token for a figure CSV and section 5 fixes the 7.5 sentence for a table CSV, and an empty
# cell means NOT APPLICABLE in both and never means suppressed.
_HIDDEN_SPELLINGS_BY_KIND: dict[str, frozenset[str]] = {
    "figure-csv": frozenset({FIGURE_SUPPRESSED_TOKEN}),
    "table-csv": SUPPRESSION_SENTENCES | _SENTENCES_DISCLOSURE_CANNOT_SEE,
}


def _cell_is_hidden(cell: Any) -> bool:
    """`disclosure.is_bundle_suppressed`, plus any 7.5 sentence it does not yet carry.

    The predicate is the module's and is not re-implemented here.  The second term is a
    COMPUTED set, empty in a healthy tree, that exists only while this module prints a 7.5
    sentence `disclosure.py` has not transcribed: at contract 1.6.0 that is
    `no_crossing_within_range`, the ninth, which `07_export.py` writes into two Table 2
    footer rows and which `is_bundle_suppressed` therefore returns False for.  A cell that
    is hidden and unrecognised is not a small gap in a representation check: it is the one
    class that would let the ninth sentence be written into a FIGURE CSV, where the
    contract requires the bare token, with nothing refusing it.  The set closes itself the
    moment `disclosure.SUPPRESSION_REASONS` grows the row, and `--self-test` reports it
    while it is not empty.
    """
    return is_bundle_suppressed(cell) or (
        isinstance(cell, str) and cell in _SENTENCES_DISCLOSURE_CANNOT_SEE
    )


def _contract_violations(
    df: pd.DataFrame,
    *,
    relative_path: str,
    kind: str,
    count_cols: Sequence[str] = (),
    composite_count_columns: Sequence[str] = (),
    row_partitions: Sequence[tuple[str, Sequence[int]]] = (),
    numeric_string_columns: Sequence[str] = (),
    specification_columns: Sequence[str] = (),
) -> list[str]:
    """Every reason this RENDERED frame may not be written that `safe_export` cannot see.

    Returns every reason, never only the first: a caller fixing violations one traceback at
    a time makes one round trip through the perimeter per violation.  No message quotes a
    cell value, only a column name and a cell count, because a refusal renders into a
    notebook traceback and a cell value in a traceback is a disclosed cell.

    WHAT IS NO LONGER HERE, and why that is a deletion rather than a relaxation.  The
    complementary-disclosure class and the column-partition class used to be duplicated in
    this function because `disclosure.is_suppressed` recognised only the module's own
    sentinel, which is neither of the two spellings a bundle cell uses, so both classes
    came back empty on every frame that crossed the boundary.  `disclosure.py` now routes
    both through `is_bundle_suppressed`, which recognises the figure token and the 7.5
    sentences by equality and the sentinel by containment, so both classes fire in the
    module where they belong.  A second copy here would be a second implementation of the
    same rule and a second place for it to drift.  `gated_export` still runs `safe_export`
    on every frame, so both classes still run on every frame; what changed is which module
    owns them.
    """
    problems: list[str] = []

    # -- the 10.2 register, by (file, column).  Checked HERE, before the write, rather than
    # left for verify.py, which sees the file only after it has left the perimeter.
    for col in specification_columns:
        if specification_column_authority(relative_path, col) is None:
            problems.append(
                f"specification column {col!r} on {relative_path} is authorised by none of "
                f"the three 10.2 registers: the whitelist, exception 3 or exception 5"
            )

    # -- 10.2 exception 5's PRECONDITION, asserted on the frame rather than assumed.  The
    # exception exempts twelve statistic columns from the near-unique class on the argument
    # that a row is a prespecified stratum and that the statistic is a summary over more
    # than twenty people by construction.  Both halves of that argument are properties of
    # the values: the value is rounded to its unit's decimals before the frame is built,
    # and the row carries a contributing count that was floor-tested on its TRUE value.  An
    # exemption whose precondition is assumed is an exemption without a precondition.
    problems.extend(_exception_5_precondition_violations(
        df, relative_path=relative_path, specification_columns=specification_columns))

    # -- suppression representation (sections 4 and 5).  A figure CSV writes the bare token;
    # a table CSV writes the 7.5 sentence.  An empty string means NOT APPLICABLE and never
    # means suppressed, so a sentinel of the wrong shape is a violation rather than a
    # stylistic slip: the local side branches on it.
    permitted_spellings = _HIDDEN_SPELLINGS_BY_KIND.get(kind)
    if permitted_spellings is not None:
        for col in df.columns:
            # A `*_display` column is not a value cell: its whole job is to carry the
            # printed sentence in place of the marker, so `figure3_forest.csv` legitimately
            # holds "not estimable (cell size)" beside a `SUPPRESSED` estimate, and
            # `figure4_event_centered_activity.csv` holds the same in `not_plotted_display`.
            if str(col).endswith("_display"):
                continue
            wrong = sum(
                1 for cell in df[col]
                if isinstance(cell, str) and _cell_is_hidden(cell)
                and cell not in permitted_spellings
            )
            if wrong:
                problems.append(
                    f"column {col!r} holds {wrong} suppressed cell(s) written in a "
                    f"representation this file kind does not use"
                )

    # -- the count floor, on the rendered cell (10.4 item 3).  `is_legal_disclosed_count`,
    # never `disclosable`: these cells have already been through `round20`, so the question
    # is whether the value is a legal one to write down, and asking the floor predicate here
    # refuses every correctly rounded 20 in the bundle.  `safe_export` runs the same class
    # over the cells `pd.to_numeric` parses; this reaches the ones it does not, which is
    # every four-figure count a table CSV writes with a thousands separator.
    for col in count_cols:
        if col not in df.columns:
            problems.append(f"declared count column {col!r} is not in the frame")
            continue
        bad = 0
        for cell in df[col]:
            if isinstance(cell, str) and (cell.strip() == "" or _cell_is_hidden(cell)):
                continue
            parsed = _parse_display_count(cell)
            if parsed is None or not is_legal_disclosed_count(parsed):
                bad += 1
        if bad:
            problems.append(
                f"count column {col!r} holds {bad} cell(s) that are not legal disclosed "
                f"counts; a legal disclosed count is a true zero, a suppression "
                f"representation, or a positive whole multiple of the rounding base"
            )

    # -- the same floor, on a count embedded in a composed display token (10.4 decl. 1).
    for col in composite_count_columns:
        if col not in df.columns:
            problems.append(f"declared composite count column {col!r} is not in the frame")
            continue
        bad = sum(
            1 for cell in df[col]
            for number in _embedded_counts(cell)
            if not is_legal_disclosed_count(number)
        )
        if bad:
            problems.append(
                f"column {col!r} holds {bad} composed cell(s) whose embedded count is not "
                f"a legal disclosed count"
            )

    # -- partitions by ROW (10.4 declaration 2).  `disclosure.export_violations`' own
    # `partitions` argument is a sequence of COLUMN-name groups, checked across the cells of
    # one row; four partitions in this bundle are the other shape, several ROWS of one
    # column summing to a disclosed total, and there is no way to say that in a sequence of
    # column names.  One suppressed member of such a set is recoverable by subtraction.
    for column, row_indices in row_partitions:
        if column not in df.columns:
            problems.append(f"declared row partition names column {column!r}, not in the frame")
            continue
        cells = [df[column].iloc[i] for i in row_indices]
        hidden = sum(1 for cell in cells if _cell_is_hidden(cell))
        if hidden == 1:
            problems.append(
                f"column {column!r} has exactly one suppressed member across a declared "
                f"row partition of {len(cells)} rows, which is recoverable by subtraction"
            )

    # -- banned characters.  A header is a written string too, so it is scanned.  This one
    # overlaps `safe_export` deliberately: it is cheap, and a refusal here names the column
    # before any file is opened.
    for col in df.columns:
        if any(ch in str(col) for ch in disclosure.BANNED_CHARACTERS):
            problems.append(
                f"column header {col!r} carries a banned dash character (U+2014 or U+2212)"
            )
        offenders = sum(
            1 for cell in df[col]
            if isinstance(cell, str)
            and any(ch in cell for ch in disclosure.BANNED_CHARACTERS)
        )
        if offenders:
            problems.append(
                f"column {col!r} holds {offenders} string cell(s) carrying a banned dash "
                f"character (U+2014 or U+2212)"
            )

    # -- a numeral column rendered as strings.  This is what replaces the module's
    # string-versus-numeric check on the figure CSVs whose schema REQUIRES a column to carry
    # both a numeral and the suppression token: every cell must be a plain numeral, the bare
    # token, or the empty string, and nothing else.  Without it, rendering the column as
    # strings to get past the module's check would switch that check off.
    for col in numeric_string_columns:
        if col not in df.columns:
            problems.append(f"declared numeral column {col!r} is not in the frame")
            continue
        bad = 0
        for cell in df[col]:
            if not isinstance(cell, str):
                bad += 1
            elif cell == "" or cell == FIGURE_SUPPRESSED_TOKEN:
                continue
            elif not _NUMERAL.match(cell):
                bad += 1
        if bad:
            problems.append(
                f"numeral column {col!r} holds {bad} cell(s) that are neither a plain "
                f"numeral nor the suppression token nor the not-applicable empty string"
            )

    return problems


def _exception_5_precondition_violations(
    df: pd.DataFrame,
    *,
    relative_path: str,
    specification_columns: Sequence[str] = (),
) -> list[str]:
    """10.2 exception 5's stated precondition, asserted on the values it is claimed over.

    Two halves, both properties of the values rather than of the column name:

      1. **The statistic is rounded to its unit's decimals (2.4) before the frame is
         built.** That is what bounds the value space the exception then argues about: at
         `normalized_activity`'s two decimals a Figure 2 column of 286 rows holds about
         seventy distinct values, and at three decimals it would hold 286.  Rounding is a
         precondition of the exemption and not an alternative to it.
      2. **The row carries a contributing count**, floor-tested on its true value upstream,
         so the statistic is a summary over more than twenty people by construction
         whatever its cardinality.  A declared statistic column on a frame with no such
         count column is an exemption resting on an argument the frame cannot make.

    `figure3_forest.csv` carries a per-row `unit` column rather than one unit for the file,
    so its decimals are checked per row against that column.
    """
    spec = EXCEPTION_5_COLUMNS.get(relative_path)
    if spec is None:
        return []
    columns, count_column, unit = spec
    declared = [c for c in specification_columns if c in columns]
    if not declared:
        return []
    problems: list[str] = []
    if count_column not in df.columns:
        problems.append(
            f"10.2 exception 5 is declared on {relative_path} for {len(declared)} "
            f"column(s), but the frame carries no {count_column!r} column, so the "
            f"floor-tested contributing count the exception rests on is not there"
        )
        return problems
    units = (
        [str(u) for u in df["unit"]] if not unit and "unit" in df.columns
        else [unit] * len(df)
    )
    for col in declared:
        coarser = 0
        for cell, row_unit in zip(df[col], units):
            if isinstance(cell, str):
                if cell.strip() == "" or _cell_is_hidden(cell):
                    continue
                try:
                    value = float(cell)
                except ValueError:
                    coarser += 1
                    continue
            elif isinstance(cell, (int, float)) and not isinstance(cell, bool):
                value = float(cell)
            else:
                coarser += 1
                continue
            decimals = UNIT_DECIMALS.get(row_unit)
            if decimals is None or round(value, decimals) != value:
                coarser += 1
        if coarser:
            problems.append(
                f"10.2 exception 5 column {col!r} on {relative_path} holds {coarser} "
                f"value(s) that are not at their unit's decimals from 2.4, which is the "
                f"exception's stated precondition and not an alternative to it"
            )
    return problems


def gated_export(
    df: pd.DataFrame,
    root: Path,
    relative_path: str,
    *,
    kind: str,
    exhibit: str = "",
    description: str = "",
    count_cols: Sequence[str] = (),
    composite_count_columns: Sequence[str] = (),
    percentage_columns: Sequence[str] = (),
    partitions: Sequence[Sequence[str]] = (),
    row_partitions: Sequence[tuple[str, Sequence[int]]] = (),
    numeric_string_columns: Sequence[str] = (),
    specification_columns: Sequence[str] = (),
) -> dict[str, Any]:
    """Run both gates, write through `safe_export`, and return the MANIFEST.csv row.

    ONE field of the returned row is recomputed here, and the reason is a parser rather
    than a disagreement about what it means:

      `min_disclosed_count` -- 8.3 defines it as "the smallest count value written in the
        file".  `safe_export` takes it from `pd.to_numeric`, which cannot parse `9,860`, so
        a table CSV's four-figure counts drop out of the minimum silently, and the counts
        this bundle composes into `1,240 (33%)` and `n = 340` never reach it at all.

    `n_suppressed_cells` is NO LONGER recomputed here.  8.3 defines it as "cells written as
    `SUPPRESSED`, or as a suppression sentence in a table CSV", and `safe_export` now counts
    exactly that, through `is_bundle_suppressed` over every column of the frame.  It used to
    count the module's own sentinel, which appears in no bundle cell, and came back zero on
    a file full of hidden cells; recomputing it here was the workaround for that and is now
    a second implementation of a field the module computes correctly.

    Everything else in the row is `safe_export`'s, including the md5, which is computed over
    the bytes read back from disk and is the only number in the row this module must not
    touch.
    """
    problems = _contract_violations(
        df,
        relative_path=relative_path,
        kind=kind,
        count_cols=count_cols,
        composite_count_columns=composite_count_columns,
        row_partitions=row_partitions,
        numeric_string_columns=numeric_string_columns,
        specification_columns=specification_columns,
    )
    if problems:
        listed = "\n".join(f"  {i}. {p}" for i, p in enumerate(problems, 1))
        raise ContractViolation(
            f"refusing to export {relative_path}: {len(problems)} contract violation(s)\n"
            f"{listed}"
        )

    row = safe_export(
        df,
        root / relative_path,
        kind=kind,
        exhibit=exhibit,
        description=description,
        count_cols=count_cols,
        percentage_columns=percentage_columns,
        partitions=partitions,
        specification_columns=specification_columns,
    )
    row["file"] = relative_path
    disclosed: list[int] = []
    for col in count_cols:
        if col not in df.columns:
            continue
        for cell in df[col]:
            parsed = _parse_display_count(cell)
            if parsed is not None:
                disclosed.append(parsed)
    for col in composite_count_columns:
        if col not in df.columns:
            continue
        for cell in df[col]:
            disclosed.extend(_embedded_counts(cell))
    row["min_disclosed_count"] = min(disclosed) if disclosed else ""
    return row



# ======================================================================================
# SECTION 8.  results.json, MANIFEST.csv, MANIFEST.md5.
# ======================================================================================


def _round_floats(obj: Any, decimals: int = 6) -> Any:
    """Round every float in the object before dumping, so R and Python serialize alike.

    A value produced by glmmTMB and the same value produced by statsmodels differ in the
    last bits of their repr, and `results.json`'s md5 is stamped over the bytes.  Six
    decimals is well beyond every display precision in 2.4.
    """
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ExportError("results.json carries a non-finite float, which has no display")
        return round(obj, decimals)
    if isinstance(obj, dict):
        return {k: _round_floats(v, decimals) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_round_floats(v, decimals) for v in obj]
    return obj


def count_value_nodes(obj: Any) -> int:
    """`n_rows` for results.json (8.3): objects carrying a `display` key, at any depth."""
    total = 0
    if isinstance(obj, Mapping):
        if "display" in obj:
            total += 1
        for value in obj.values():
            total += count_value_nodes(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            total += count_value_nodes(value)
    return total


def _walk_nodes(obj: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(obj, Mapping):
        if "display" in obj:
            yield obj
        for value in obj.values():
            yield from _walk_nodes(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from _walk_nodes(value)


def _json_disclosure_violations(obj: Any) -> list[str]:
    """The checks `safe_export` would have run over a frame, run over the OBJECT instead.

    10.4: `safe_export` writes CSV even into a `.json` path, so `results.json` is
    serialized by this module.  That is a different caller, not a hole in the enforcement,
    and this function is what makes the two equivalent: every count node's `n` is
    gate-tested with `is_legal_disclosed_count`, every disclosed percentage node is checked
    for a real numerator, and every written string is scanned for a banned dash.
    """
    problems: list[str] = []
    n_illegal = 0
    n_percent_bad = 0
    for node in _walk_nodes(obj):
        if node.get("suppressed") is True:
            if any(key in node for key in ("n", "pct", "est", "q50", "p")):
                problems.append(
                    "a suppressed node carries a numeric key; the number must not be in the file"
                )
            continue
        if "n" in node and not is_legal_disclosed_count(node["n"]):
            n_illegal += 1
        if "pct" in node:
            if not is_legal_disclosed_count(node.get("num")):
                n_percent_bad += 1
            elif not is_legal_disclosed_count(node.get("den")):
                n_percent_bad += 1
            elif node["pct"] != _percent_integer(int(node["num"]), int(node["den"])):
                n_percent_bad += 1
    if n_illegal:
        problems.append(
            f"{n_illegal} count node(s) carry a value that is not a legal disclosed count"
        )
    if n_percent_bad:
        problems.append(
            f"{n_percent_bad} percentage node(s) are not the rounded numerator over the "
            f"rounded denominator at zero decimals"
        )
    banned = _banned_character_strings(obj)
    if banned:
        problems.append(
            f"{banned} string(s) in results.json carry a banned dash character "
            f"(U+2014 or U+2212)"
        )
    return problems


def _banned_character_strings(obj: Any) -> int:
    total = 0
    if isinstance(obj, str):
        if any(ch in obj for ch in disclosure.BANNED_CHARACTERS):
            total += 1
    elif isinstance(obj, Mapping):
        for key, value in obj.items():
            total += _banned_character_strings(key) + _banned_character_strings(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            total += _banned_character_strings(value)
    return total


def write_results_json(obj: Mapping[str, Any], root: Path, log: SuppressionLog) -> dict[str, Any]:
    """Serialize results.json, hash the bytes read back, and assemble its manifest row by hand.

    This one file does not go through `safe_export`, and 10.4 says why: `safe_export` would
    accept the `.json` path and write comma-separated bytes into it with no error at all.
    """
    problems = _json_disclosure_violations(obj)
    if problems:
        listed = "\n".join(f"  {i}. {p}" for i, p in enumerate(problems, 1))
        raise ContractViolation(
            f"refusing to export results.json: {len(problems)} contract violation(s)\n"
            f"{listed}"
        )
    target = root / "results.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(_round_floats(obj, 6), handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write("\n")
    digest = md5_of_bytes(target.read_bytes())

    disclosed = [
        int(node["n"]) for node in _walk_nodes(obj)
        if not node.get("suppressed", False) and "n" in node
    ]
    return {
        "file": "results.json",
        "kind": "results-json",
        "exhibit": "",
        "md5": digest,
        "n_rows": count_value_nodes(obj),
        "n_columns": 0,
        "min_disclosed_count": min(disclosed) if disclosed else "",
        "n_suppressed_cells": len(log.entries),
        "description": (
            "Every scalar the manuscript cites, with its display string and its "
            "suppression state"
        ),
    }


def write_manifest(root: Path, rows: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    """Write MANIFEST.csv in the fixed order of 8.3, then MANIFEST.md5 over its bytes.

    The manifest is assembled from the sixteen rows the writers RETURNED.  No row is built
    by hand here beyond `results.json`'s, because a manifest assembled from sixteen
    separate re-derivations of a row and column count is sixteen chances to describe a file
    the exporter did not write.
    """
    by_file = {row["file"]: row for row in rows}
    missing = [name for name in BUNDLE_FILES if name not in by_file]
    if missing:
        raise ExportError(f"the manifest is short of {len(missing)} file(s): {missing}")
    extra = [name for name in by_file if name not in BUNDLE_FILES]
    if extra:
        raise ExportError(
            f"the manifest names {len(extra)} file(s) section 1 does not declare: {extra}"
        )
    frame = pd.DataFrame(
        [{col: by_file[name][col] for col in MANIFEST_COLUMNS} for name in BUNDLE_FILES],
        columns=list(MANIFEST_COLUMNS),
    )
    payload = frame.to_csv(
        index=False, float_format=FLOAT_FORMAT, lineterminator="\n", na_rep=""
    ).encode("utf-8")
    manifest_path = root / "MANIFEST.csv"
    manifest_path.write_bytes(payload)
    manifest_md5 = md5_of_bytes(manifest_path.read_bytes())
    # MANIFEST.csv carries no row for itself: a manifest that hashed itself would be
    # circular, which is the whole reason this is two files.
    (root / "MANIFEST.md5").write_text(manifest_md5 + "\n", encoding="utf-8", newline="\n")
    return manifest_md5, str(manifest_path)


# ======================================================================================
# SECTIONS 4 AND 5.  The frame builders.  Each returns the frame and the declarations
# `gated_export` needs, so the declaration lives beside the schema it describes rather
# than at a call site three hundred lines away.
# ======================================================================================


def _bool_cell(value: bool) -> str:
    """`true` / `false`, lower case, never `TRUE` and never `1` (section 4 shared rules)."""
    return "true" if value else "false"


def figure_cell(node: Any) -> str:
    """A figure-CSV cell from a node: the bare numeral, the bare token, or the empty string."""
    if node is None:
        return ""
    if is_node_suppressed(node):
        return FIGURE_SUPPRESSED_TOKEN
    if "n" in node:
        return str(int(node["n"]))
    raise ExportError("figure_cell was handed a node with no count")


def table_cell(node: Any) -> str:
    """A table-CSV cell from a node: the display string, or the 7.5 sentence, verbatim.

    Counts stay BARE in exported bytes and carry the separator only on a display surface;
    a table CSV is a display surface, which is why `display` is right here and
    `disclosure.render_count` is never called by this module at all -- `safe_export` renders
    no count of its own, so the separator cannot reach a figure CSV's numeric cell.
    """
    if node is None:
        return ""
    return node_display(node)


def build_figure1_frame(results: Mapping[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """figures-csv/figure1_strobe_ladder.csv.  Nineteen rows, thirteen columns, sorted by step."""
    rungs = results["attrition"]["rungs"]
    records = []
    for rung in rungs:
        records.append({
            "step": int(rung["step"]),
            "slug": rung["slug"],
            "display_label": rung["display_label"],
            "kind": rung["kind"],
            "unit": rung["unit"],
            "n_in": figure_cell(rung["n_in"]),
            "n_dropped": figure_cell(rung["n_dropped"]),
            "n_out": figure_cell(rung["n_out"]),
            "n_carried_forward": figure_cell(rung["n_carried_forward"]),
            "reason": rung["reason"],
            "reason_display": rung["reason_display"],
            "closes_exact": _bool_cell(bool(rung["closes_exact"])),
            # The ladder spine on the left, the exclusion box on the right.  A rung earns a
            # right-hand box exactly when it has a sentence to put in it, which is the same
            # fact as a non-empty reason display: a terminal rung has none, and neither
            # does step 17, which converts episodes into events without excluding anything.
            # Keying on the sentence rather than on `kind` is what keeps a renderer from
            # drawing an empty box beside the unit change.
            "box_side": "exclusion" if rung["reason_display"] else "main",
        })
    frame = pd.DataFrame(records).sort_values("step", kind="stable").reset_index(drop=True)
    declarations = {
        "kind": "figure-csv",
        "exhibit": "Figure 1",
        "description": "Participant flow through the nineteen prespecified attrition rungs",
        "count_cols": ("n_in", "n_dropped", "n_out", "n_carried_forward"),
        # `n_dropped` and `n_out` partition `n_in` on every exclusion rung.  On a conversion
        # or terminal rung `n_dropped` is the empty not-applicable cell, so the row carries
        # one present member and is skipped rather than read as a lone suppression.
        "partitions": (("n_dropped", "n_out"),),
        "numeric_string_columns": ("n_in", "n_dropped", "n_out", "n_carried_forward"),
        # The five rung-vocabulary columns, under the 10.2 whitelist as of contract 1.6.1.
        # THE GRANT DOES NOT ON ITS OWN MAKE A GROWN LADDER EXPORTABLE, and 11.4 says so:
        # measured at twenty-one rungs, `n_in` and `n_out` cross the ceiling too and carry
        # the integer-key shape with them, they are counts, and a count column is exempted
        # by nothing in that document.  That residue is a dated obligation, not a widened
        # exemption, and it is not this call site's to clear.
        "specification_columns": (
            "step", "slug", "display_label", "reason", "reason_display"),
    }
    return frame, declarations


def build_figure2_frame(series_rows: Sequence[Mapping[str, Any]]) -> tuple[pd.DataFrame, dict]:
    """figures-csv/figure2_daily_activity.csv.  LONG FORMAT, one row per group per day.

    Long format is a disclosure decision, not a convenience.  A single-series day-indexed
    frame has a distinct `day` in every row, so it is 100% distinct and trips the
    near-unique class; four series over ninety days repeat every day four times and the
    ratio falls to about a quarter.  10.2 exception 3 covers the `single_group` case, where
    the collapse leaves one series and the ratio goes back to one, and that exception is
    why `specification_columns=["day"]` is declared here at every collapse level.

    The absence rule: a day whose TRUE contributing count fails `disclosable` is not
    written at all.  No row, no token, no null.  The `n_contributing` that survives is the
    ROUNDED value, so a row reading 20 stands on a true count of 21 to 29.
    """
    frame = pd.DataFrame(list(series_rows), columns=[
        "group_slug", "display_label", "group_order", "day", "n_contributing",
        "observed_median", "observed_p25", "observed_p75",
        "fitted_marginal", "fitted_lo", "fitted_hi",
        "in_accrual_window", "series_segment",
    ])
    frame = frame.sort_values(["group_order", "day"], kind="stable").reset_index(drop=True)
    declarations = {
        "kind": "figure-csv",
        "exhibit": "Figure 2",
        "description": (
            "Baseline-normalized daily activity by post-discharge day for each procedure "
            "group"
        ),
        "count_cols": ("n_contributing",),
        # `day` under 10.2 exception 3 and the six statistic columns under exception 5.
        # The exception grants an exemption from the near-unique CARDINALITY class only;
        # `specification_columns` is the module's one lever and it also lifts the
        # identifier-like class, which these six do not trip in either form -- they are
        # floats, so the integer-key shape does not apply, and none of the six names
        # matches the identifier pattern -- so the wider lever is inert on them.  Both
        # halves of exception 5's precondition are asserted on the frame by
        # `_exception_5_precondition_violations`, not assumed.
        "specification_columns": (
            "day",
            "observed_median", "observed_p25", "observed_p75",
            "fitted_marginal", "fitted_lo", "fitted_hi",
        ),
    }
    return frame, declarations


def build_figure3_frame(forest_rows: Sequence[Mapping[str, Any]]) -> tuple[pd.DataFrame, dict]:
    """figures-csv/figure3_forest.csv.  Twenty-seven rows in three blocks.

    A below-threshold row is PRESENT, not absent, which is the opposite of the Figure 2
    rule and deliberately so: a Figure 3 row is a named, prespecified analysis, and its
    absence would read as "this analysis was never planned", which is false and which leaks
    by omission to any reader holding the prespecified list.
    """
    frame = pd.DataFrame(list(forest_rows), columns=[
        "block", "block_label", "row_order", "slug", "display_label",
        "estimate", "ci_lo", "ci_hi", "unit", "axis", "render", "n",
        "estimable", "not_estimable_display", "is_primary", "reference_value",
    ])
    frame = frame.sort_values(["block", "row_order"], kind="stable").reset_index(drop=True)
    declarations = {
        "kind": "figure-csv",
        "exhibit": "Figure 3",
        "description": (
            "Recovery debt contrasts, robustness rows and subgroups on the primary scale"
        ),
        "count_cols": ("n",),
        "numeric_string_columns": ("estimate", "ci_lo", "ci_hi", "n"),
        # `slug` and `display_label` under the 10.2 whitelist: one row per prespecified
        # analysis makes both unique by construction over 27 rows, and what is unique is the
        # list of analyses this study planned, which the contract publishes in full in 7.3,
        # 7.8 and 7.11.  `estimate`, `ci_lo` and `ci_hi` under exception 5: twenty-seven
        # prespecified analyses over one cohort produce twenty-seven well-separated numbers,
        # and three columns of them at `activity_days`' one decimal are near-certain to
        # exceed the ninety percent ceiling.  The fixture passes without the grant only by
        # accident, at a ratio of 0.59, because eleven of its dummy values were typed rather
        # than fitted; a real forest would halt the export in Phase 4, inside the perimeter,
        # after every query had been billed.
        "specification_columns": ("slug", "display_label", "estimate", "ci_lo", "ci_hi"),
    }
    return frame, declarations


def build_figure4_frame(rows: Sequence[Mapping[str, Any]]) -> tuple[pd.DataFrame, dict]:
    """figures-csv/figure4_event_centered_activity.csv.  Forty-four rows, ten columns.

    Two series over the 22 offsets -14 to +7, on every run and at every tier.  The row count
    is not data-dependent, which is what lets `MANIFEST.csv`, `figures.figure4.rows` and the
    fixture all pin an exact number, and what makes the file's tier-4 shape checkable: 44
    rows of `SUPPRESSED` with a printed reason in every one, which is section 1's rule for a
    file whose content is entirely suppressed met in this file's own representation.
    """
    frame = pd.DataFrame(list(rows), columns=list(FIGURE_COLUMNS["figure4"]))
    frame = frame.assign(
        _order=frame["series_order"].astype(int),
        _day=frame["day_relative_to_event"].astype(int),
    ).sort_values(["_order", "_day"], kind="stable").drop(
        columns=["_order", "_day"]).reset_index(drop=True)
    if len(frame) != len(FIGURE4_SERIES) * len(FIGURE4_OFFSETS):
        raise ExportError(
            f"figure4_event_centered_activity.csv is {len(frame)} rows. 4.4 fixes it at "
            f"{len(FIGURE4_SERIES)} series over {len(FIGURE4_OFFSETS)} offsets on every "
            f"run and at every tier, so a different number is a dropped row and not a "
            f"suppression."
        )
    declarations = {
        "kind": "figure-csv",
        "exhibit": "Figure 4",
        "description": (
            "Normalized activity centred on the acute-care event for cases and matched "
            "controls"
        ),
        "count_cols": ("n_contributing",),
        "numeric_string_columns": (
            "n_contributing", "observed_median", "observed_p25", "observed_p75",
        ),
        # The three quantile columns under 10.2 exception 5.  Twenty-two offsets on two
        # series at `normalized_activity`'s two decimals is the same shape the exception was
        # written for on Figure 3.  `day_relative_to_event` is NOT declared and needs no
        # part of exception 3: 22 distinct values across 44 rows is a ratio of one half.
        "specification_columns": ("observed_median", "observed_p25", "observed_p75"),
    }
    return frame, declarations


def assert_row_order_contiguous(frame: pd.DataFrame, where: str) -> None:
    """`row_order` is 1 to N with no gaps.  HALT on a gap, never repair (10.2, 5.1).

    The `row_order` grant exempts the column from the near-unique class and from the
    integer-key shape, which is the whole of what the gate would otherwise notice about it.
    A contiguous ordinal carries nothing beyond the print order the contract already
    publishes; a GAP would carry something else -- that a prespecified row of the 5.1
    row-order table was not written, and which one -- and the exemption is precisely what
    stops the gate noticing.  So the safety is a property of the values, not of the column,
    and it is checked on the values.

    Renumbering to close the gap would hide the dropped row, and the dropped row is the
    finding.  5.1 already requires that a row whose every cell is suppressed is still
    written, so this cannot fire on a suppression.
    """
    if list(frame["row_order"]) != list(range(1, len(frame) + 1)):
        raise ExportError(
            f"{where}: row_order is not the contiguous ordinal 1 to {len(frame)}. A gap "
            f"says a prespecified row was not written, and which one. Halting rather than "
            f"renumbering, because renumbering would hide it."
        )


def build_table1_frame(
    results: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """tables-csv/table1_cohort_characteristics.csv.  Every cell is a display string.

    The number of group columns follows the collapse level, so the header list is built
    from `cohort.groups[i].column_header` and never from a literal four.
    """
    headers = [group["column_header"] for group in results["cohort"]["groups"]]
    columns = ["row_order", "Characteristic", "Level"] + headers + ["Statistic"]
    records = []
    for index, row in enumerate(rows, start=1):
        record: dict[str, Any] = {
            "row_order": index,
            "Characteristic": row["characteristic"],
            "Level": row["level"],
            "Statistic": row["statistic"],
        }
        for header, cell in zip(headers, row["cells"]):
            record[header] = cell
        records.append(record)
    frame = pd.DataFrame(records, columns=columns)

    # The contiguity assertion runs on the INTEGER column, exactly as 10.2 writes it, and
    # before the cast that section 5 requires of every table cell.  Doing it the other way
    # round would compare strings to integers and pass vacuously.
    assert_row_order_contiguous(frame, "tables-csv/table1_cohort_characteristics.csv")
    frame["row_order"] = frame["row_order"].map(str)

    # Each characteristic block is a partition of its group total, by ROW rather than by
    # column, so one suppressed level inside a block forces a second.  The blocks are
    # declared from the rows themselves rather than hardcoded, because the row list is what
    # 5.1 owns.
    row_partitions: list[tuple[str, tuple[int, ...]]] = []
    for header in headers:
        for indices in _characteristic_blocks(rows):
            row_partitions.append((header, indices))
    # ALONG a row, the procedure-group columns partition the pooled `All groups` cell, so
    # one suppressed group cell is recoverable by subtracting the others from the pooled
    # one.  That is a COLUMN partition and is a different rule from the row partition
    # above; Table 1 is the one file in the bundle that carries both, and missing either
    # leaves a recoverable cell.
    member_headers = tuple(
        group["column_header"] for group in results["cohort"]["groups"]
        if group["slug"] != "all_groups"
    )
    declarations = {
        "kind": "table-csv",
        "exhibit": "Table 1",
        "description": (
            "Cohort characteristics and wearable data availability by procedure group"
        ),
        "row_partitions": tuple(row_partitions),
        "partitions": (member_headers,) if len(member_headers) > 1 else (),
        # Table 1's counts live inside composed `n (%)` tokens beside medians and
        # sentences in the same column, so they are declared here rather than as count
        # columns, and the gate tests the embedded numerator.
        "composite_count_columns": tuple(headers),
        "specification_columns": ("row_order",),
    }
    return frame, declarations


def _characteristic_blocks(rows: Sequence[Mapping[str, Any]]) -> list[tuple[int, ...]]:
    """The row index groups that partition a group total: the multi-level count blocks.

    A single-line median row partitions nothing, and neither does a two-row block whose
    levels overlap, so only blocks explicitly marked as a partition are returned.
    """
    blocks: dict[str, list[int]] = {}
    for index, row in enumerate(rows):
        if not row.get("partition", False):
            continue
        blocks.setdefault(row["characteristic"], []).append(index)
    return [tuple(indices) for indices in blocks.values() if len(indices) > 1]


def by_group_member_rows(
    entries: Sequence[Mapping[str, Any]], *, where: str
) -> tuple[int, ...]:
    """The rows of a by-group block that PARTITION its pooled row, from the block's shape.

    The members are the entries whose slug is not `all_groups`; the total is the one that
    is, and it is never a member of itself.  Derived here once rather than declared per
    column, because the partition is a fact about the BLOCK: it is true of `n`, of
    `n_complete_windows`, of `share_zero_debt` and of any count the block grows later, and a
    rule restated at each column is a rule that will one day be restated at all but one.

    RETURNS THE EMPTY TUPLE WHEN THERE ARE FEWER THAN TWO MEMBERS, which is a real state and
    not an error.  The collapse ladder of ANALYSIS-PLAN.md 2.5 can land on `single_group`,
    where the one member and the pooled total are the same number: there is no second
    disclosed member to subtract, so nothing is recoverable and nothing is declared.
    `disclosure.export_violations` refuses a one-member partition outright, and it is right
    to; the empty tuple is how this says "no partition" rather than "a bad one".

    A block with no pooled entry, or with two, is refused.  The derivation has no total to
    name, and a partition with the total inside it would force a second suppression to
    protect a cell that nothing can recover.
    """
    members = tuple(i for i, e in enumerate(entries) if e["slug"] != ALL_GROUPS_SLUG)
    totals = tuple(i for i, e in enumerate(entries) if e["slug"] == ALL_GROUPS_SLUG)
    if len(totals) != 1:
        raise ExportError(
            f"{where} carries {len(totals)} pooled {ALL_GROUPS_SLUG!r} entries and must "
            f"carry exactly one. The by-group partition is derived from the block's own "
            f"shape, so a block with no total, or with two, has no partition to derive and "
            f"every count column in it would export unprotected."
        )
    return members if len(members) > 1 else ()


def build_table2_frame(results: Mapping[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """tables-csv/table2_adjusted_debt.csv.  Absolute adjusted levels live here and only here.

    Contrasts live in Figure 3 and only there.  The naive unadjusted column carries its own
    denominator, because it is computed on complete windows only and printing it against
    the analytic n would put a median over 180 episodes under a header saying 340.

    THE COUNT COLUMNS AND THEIR PARTITIONS BOTH COME FROM `DEBT_BY_GROUP_COUNT_COLUMNS`.
    Every count this table prints is a column of `debt.by_group`, the four group rows of
    each partition the `All groups` row beneath them, and one suppressed member of any of
    them is recoverable by subtraction.  Naming the columns and deriving the partitions from
    the one declaration is what makes that structural: a column cannot appear in this frame
    without arriving through the tuple, and arriving through the tuple is what declares it.
    """
    count_columns = [column for _key, _source, column in DEBT_BY_GROUP_COUNT_COLUMNS]
    columns = (
        ["row_order", "Procedure group"]
        + count_columns
        + ["Unadjusted debt, median (IQR)", "Adjusted debt, activity days (95% CI)",
           "Thousand steps lost (95% CI)", "Adjusted mean normalized activity (95% CI)",
           "Reached 80% of baseline (95% CI)"]
    )
    groups = {g["slug"]: g for g in results["cohort"]["groups"]}
    entries = results["debt"]["by_group"]
    records = []
    for index, entry in enumerate(entries, start=1):
        slug = entry["slug"]
        record: dict[str, Any] = {
            "row_order": index,
            "Procedure group": groups[slug]["display_label"],
            "Unadjusted debt, median (IQR)": table_cell(entry["unadjusted_debt"]),
            "Adjusted debt, activity days (95% CI)": table_cell(entry["adjusted_debt"]),
            "Thousand steps lost (95% CI)": table_cell(entry["thousand_steps_lost"]),
            "Adjusted mean normalized activity (95% CI)":
                table_cell(entry["adjusted_mean_normalized_activity"]),
            "Reached 80% of baseline (95% CI)":
                table_cell(entry["share_reaching_80pct_baseline"]),
        }
        for key, _source, column in DEBT_BY_GROUP_COUNT_COLUMNS:
            record[column] = _n_equals(entry[key])
        records.append(record)
    frame = pd.DataFrame(records, columns=columns)
    assert_row_order_contiguous(frame, "tables-csv/table2_adjusted_debt.csv")
    frame["row_order"] = frame["row_order"].map(str)
    # The group rows partition the pooled row DOWN each count column, so the declaration is
    # a row partition rather than the column partition Table 1 also carries, and it is made
    # for every count column of the block at once rather than for the two that happen to
    # exist today.
    member_rows = by_group_member_rows(entries, where="debt.by_group")
    declarations = {
        "kind": "table-csv",
        "exhibit": "Table 2",
        "description": (
            "Adjusted digital recovery debt by procedure group, in activity days lost"
        ),
        "composite_count_columns": tuple(count_columns),
        "row_partitions": tuple(
            (column, member_rows) for column in count_columns
        ) if member_rows else (),
    }
    return frame, declarations


def _n_equals(node: Mapping[str, Any]) -> str:
    """The `n = 340` token a column header or an episodes cell prints."""
    if is_node_suppressed(node):
        return node_display(node)
    return f"n = {int(node['n']):,}"


TABLE2_FOOTER_ROWS: tuple[tuple[str, str], ...] = (
    ("Model family", "debt.model_fit.family"),
    ("Model rung reached", "meta.estimator.rung_display"),
    ("Residual correlation", "debt.model_fit.residual_correlation"),
    ("Intraclass correlation", "debt.model_fit.icc"),
    ("Marginal R squared", "debt.model_fit.marginal_r2"),
    ("Conditional R squared", "debt.model_fit.conditional_r2"),
    ("Contributing person-days", "debt.model_fit.n_person_days"),
    ("Share with zero debt", "debt.by_group[4].share_zero_debt"),
    ("Manski bounds on the primary contrast", "debt.manski.display"),
    ("Delta-shift tipping point, point estimate",
     "debt.delta_shift.tipping_point_point_estimate"),
    # 5.3 row 11.  The label says what the row reads off the grid: the first delta at which
    # the CONTRAST's interval includes zero, which is a different question from row 10's and
    # not an interval around row 10's answer.
    ("Delta-shift tipping point, first delta whose interval includes zero",
     "debt.delta_shift.tipping_point_interval"),
    ("Denominator", "denominators.analytic.display_n_equals"),
    # 5.3 ROWS 13, 14 AND 15, THE STROBE ITEM 16(a) PAIR, ADDED AT CONTRACT 1.9.0 AND
    # APPENDED RATHER THAN INSERTED.  Rows 1 to 12 keep the `row_order` they had at 1.8.0,
    # which is 5.3's own instruction and the reason the three rows are here and not beside
    # row 9's Manski bounds: a renumbering is a change every assertion in this module, in
    # the fixture and in `local/tables.py` would have to absorb for no gain.
    #
    # THEY ARE IN THE FOOTER AND NOT IN TABLE 2'S BODY OR IN FIGURE 3, and 3.5 argues each
    # absence.  The body is held to adjusted absolute LEVELS by the split `verify.py`
    # enforces on `table2_adjusted_debt.csv`, and an unadjusted contrast is a contrast.
    # Figure 3 block 2 is a set `verify.py` asserts equality on against the locked plan's
    # section 6, so a fifteenth row there is an amendment to a prespecification.  Block 1
    # would need five new slugs and five new 7.3 labels for what are not new contrasts, and
    # would have to decide whether the unadjusted primary row carries `is_primary`, where
    # 4.3 permits exactly one `true` in the file and either answer is wrong.  This file's
    # shape is `Footer item`, `Value` and `Source key` with no `slug`, no `axis` and no
    # `is_primary` column, so nothing printed here can trip that split, and row 9 already
    # carries a contrast-scale fact about the primary estimate.
    ("Unadjusted primary contrast",
     "debt.unadjusted_contrasts.fusion_vs_decompression.estimate"),
    # Row 14 without row 13 would leave "unadjusted" a word the reader fills in from habit
    # and fills in wrongly, because this table's own unadjusted COLUMN is a different
    # quantity: a median by direct summation on complete windows, not a contrast.
    ("Unadjusted contrast, what it removes", "debt.unadjusted_model.definition_display"),
    # Printed beside row 2's rung for the adjusted fit.  A covariate-free design is a
    # different optimization problem and may land on a different rung of the 3.1.1 ladder;
    # when it does, the gap between the two contrasts carries a change of model family as
    # well as a change of covariate set, and that has to be visible on the page.
    ("Unadjusted contrast, model rung reached", "debt.unadjusted_model.rung_display"),
)

# The two footer rows whose source key is allowed to be ABSENT or NULL, and the only two.
# 3.5 lets a wholly failed unadjusted fit leave `debt.unadjusted_contrasts` empty and
# `debt.unadjusted_model.rung_display` null, and 5.3 says what the two rows print then: the
# 7.5 sentence for `debt.unadjusted_model.not_estimable_reason`.  That is the ordinary
# suppression behaviour of every other footer row and not a special case, so it is spelled
# as a rule over named rows rather than as a `try` around the whole loop, which would also
# swallow a genuine typo in one of the other thirteen keys.
TABLE2_FOOTER_NOT_ESTIMABLE_ROWS: frozenset[str] = frozenset({
    "debt.unadjusted_contrasts.fusion_vs_decompression.estimate",
    "debt.unadjusted_model.rung_display",
})


def _source_key_node(results: Mapping[str, Any], key: str) -> Any:
    """Walk one dotted path into results.json and return the raw value it names."""
    node: Any = results
    for part in key.split("."):
        match = re.match(r"^([A-Za-z_0-9]+)\[(\d+)\]$", part)
        if match:
            node = node[match.group(1)][int(match.group(2))]
        else:
            node = node[part]
    return node


def _resolve_source_key(results: Mapping[str, Any], key: str) -> str:
    """Read one dotted path out of results.json and render it as its display string.

    The footer prints values, and every value it prints traces to a key.  A path that does
    not resolve raises rather than printing an empty cell, because an empty footer cell
    reads as "not applicable" and this file has no such rows.
    """
    node = _source_key_node(results, key)
    if isinstance(node, Mapping):
        return node_display(node)
    return str(node)


def _unadjusted_footer_value(results: Mapping[str, Any], key: str) -> str:
    """Rows 13 and 15 of 5.3: the value, or the 7.5 sentence naming why there is none.

    A wholly failed unadjusted fit is REPORTED, never omitted.  3.5 puts the reason on
    `debt.unadjusted_model.not_estimable_reason` precisely so the exporter has a sentence to
    print where the estimate would sit, and a reason that is null while the value is missing
    is a contradiction rather than a blank cell: the fit either returned something or named
    why it did not.  `str(None)` is not a footer value and neither is the empty string.
    """
    try:
        node = _source_key_node(results, key)
    except (KeyError, IndexError):
        node = None
    if node is not None:
        return _resolve_source_key(results, key)
    reason = results["debt"]["unadjusted_model"].get("not_estimable_reason")
    if not reason:
        raise ExportError(
            f"the Table 2 footer has nothing to print for {key!r}: the unadjusted fit "
            f"returned no value and `debt.unadjusted_model.not_estimable_reason` is null. "
            f"EXPORT-CONTRACT.md 3.5 requires a slug of 7.5 whenever the fit did not come "
            f"back, and 5.3 prints its sentence in rows 13 and 15."
        )
    return _suppression_sentence(str(reason))


def build_table2_footer_frame(results: Mapping[str, Any]) -> tuple[pd.DataFrame, dict]:
    """tables-csv/table2_adjusted_debt_footer.csv.  The footer as rows, so each value traces."""
    records = []
    for index, (item, key) in enumerate(TABLE2_FOOTER_ROWS, start=1):
        value = (
            _unadjusted_footer_value(results, key)
            if key in TABLE2_FOOTER_NOT_ESTIMABLE_ROWS
            else _resolve_source_key(results, key)
        )
        records.append({
            "row_order": index,
            "Footer item": item,
            "Value": value,
            "Source key": key,
        })
    frame = pd.DataFrame(records, columns=["row_order", "Footer item", "Value", "Source key"])
    assert_row_order_contiguous(frame, "tables-csv/table2_adjusted_debt_footer.csv")
    frame["row_order"] = frame["row_order"].map(str)
    declarations = {
        "kind": "table-csv",
        "exhibit": "",
        "description": "The Table 2 footer as rows, each tracing to its key in results.json",
        "composite_count_columns": ("Value",),
    }
    return frame, declarations


def build_table3a_frame(results: Mapping[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """tables-csv/table3_gate_part_a.csv.  Eight rows: A, B, C, D split into three, E, F."""
    group_slugs = [g["slug"] for g in results["cohort"]["groups"] if g["slug"] != "all_groups"]
    group_headers = [LABELS[slug] for slug in group_slugs]
    columns = ["row_order", "Stage", "Definition"] + group_headers + ["All groups"]
    records: list[dict[str, Any]] = []
    order = 0
    for stage in results["gate"]["stages"]:
        if stage["components"] is not None:
            for key, label in GATE_STAGE_D_COMPONENT_LABELS:
                order += 1
                record = {
                    "row_order": order,
                    "Stage": stage["letter"],
                    "Definition": label,
                    "All groups": table_cell(stage["components"][key]),
                }
                for header in group_headers:
                    record[header] = ""
                records.append(record)
            continue
        order += 1
        record = {
            "row_order": order,
            "Stage": stage["letter"],
            "Definition": stage["definition_display"],
            "All groups": table_cell(stage["total"]),
        }
        for slug, header in zip(group_slugs, group_headers):
            record[header] = (
                table_cell(stage["by_group"][slug]) if stage["by_group"] is not None else ""
            )
        records.append(record)
    frame = pd.DataFrame(records, columns=columns)
    assert_row_order_contiguous(frame, "tables-csv/table3_gate_part_a.csv")
    frame["row_order"] = frame["row_order"].map(str)

    # Stage D's three components are a partition of the composite, so one suppressed
    # component forces a second.  Stage F's four strata partition its own total, across the
    # group columns of one row.
    component_rows = tuple(
        i for i, r in enumerate(records)
        if r["Stage"] == "D" and r["Definition"] != "Composite events"
    )
    stage_f_rows = tuple(i for i, r in enumerate(records) if r["Stage"] == "F")
    declarations = {
        "kind": "table-csv",
        "exhibit": "Table 3",
        "description": "The feasibility gate ledger, stages A to F, by procedure group",
        "count_cols": tuple(group_headers) + ("All groups",),
        "row_partitions": (("All groups", component_rows),),
        "partitions": (tuple(group_headers),) if stage_f_rows else (),
    }
    return frame, declarations


def build_table3b_frame(results: Mapping[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    """tables-csv/table3_gate_part_b.csv.  Whatever the tier allows.  Never header-only.

    When the tier permits no Arm A estimate the file carries exactly two rows, the tier
    reached and the verbatim permitted claim, because a header-only table in a manuscript
    reads as a build error rather than as a finding.
    """
    tier = results["gate"]["tier"]
    records: list[dict[str, Any]] = [
        {
            "row_order": 1,
            # 7.15 owns these two strings too.  They were literals here and the contract
            # owned neither, so `verify.py`'s label assertion had nothing to compare them
            # against; they are looked up now like every other printed string.
            "Quantity": LABELS["gate_tier_reached"],
            "Estimate (95% CI)": tier["display_label"],
            "Note": "Determined by stage E",
        },
        {
            "row_order": 2,
            "Quantity": LABELS["gate_permitted_claim"],
            "Estimate (95% CI)": tier["permitted_claim_verbatim"],
            "Note": "Verbatim from the prespecified decision table",
        },
    ]
    if results["gate"]["arm_a"]["permitted"]:
        estimates = results["gate"]["arm_a"]["estimates"]
        # 5.5: one row per key of `arm_a.estimates`, IN THE ORDER 3.7 LISTS THEM.  A key the
        # tier does not produce is present carrying the `not_permitted_by_tier` sentence,
        # never absent, so a reader can tell a quantity that was not computed from one the
        # specification never had.  A key 3.7 does not declare has no row and no label, and
        # that is the intended failure rather than a `Quantity` composed from a slug.
        unknown = sorted(set(estimates) - set(GATE_ESTIMATE_KEYS))
        if unknown:
            raise ExportError(
                f"gate.arm_a.estimates carries key(s) {unknown}, which EXPORT-CONTRACT.md "
                f"3.7 does not declare and section 7.15 therefore has no printed label for"
            )
        missing = [key for key in GATE_ESTIMATE_KEYS if key not in estimates]
        if missing:
            raise ExportError(
                f"gate.arm_a.estimates is missing key(s) {missing}. Every key is present at "
                f"every tier that permits Arm A at all, carrying either a number or a "
                f"printed refusal, because a key absent from the block is indistinguishable "
                f"from a bug."
            )
        for order, key in enumerate(GATE_ESTIMATE_KEYS, start=3):
            records.append({
                "row_order": order,
                "Quantity": LABELS[key],
                "Estimate (95% CI)": table_cell(estimates[key]),
                "Note": tier["permitted_claim_verbatim"],
            })
    frame = pd.DataFrame(
        records, columns=["row_order", "Quantity", "Estimate (95% CI)", "Note"]
    )
    assert_row_order_contiguous(frame, "tables-csv/table3_gate_part_b.csv")
    frame["row_order"] = frame["row_order"].map(str)
    declarations = {
        "kind": "table-csv",
        "exhibit": "Table 3",
        "description": "The analysis the feasibility tier permits, or the reason it permits none",
    }
    return frame, declarations


def build_table4_frame(rows: Sequence[Mapping[str, Any]]) -> tuple[pd.DataFrame, dict]:
    """tables-csv/table4_collider_comparison.csv.  Three rows, six columns, on every run."""
    frame = pd.DataFrame(list(rows), columns=list(TABLE4_COLUMNS))
    if len(frame) != len(TABLE4_ROWS):
        raise ExportError(
            f"table4_collider_comparison.csv is {len(frame)} rows. 5.7 fixes it at "
            f"{len(TABLE4_ROWS)} on every run and at every tier."
        )
    assert_row_order_contiguous(frame, "tables-csv/table4_collider_comparison.csv")
    frame["row_order"] = frame["row_order"].map(str)
    declarations = {
        "kind": "table-csv",
        "exhibit": "Table 4",
        "description": (
            "Acute-care event rate with and without a computable step signal, crude and "
            "standardized"
        ),
        # Both count columns carry the house thousands separator, so `pd.to_numeric` drops
        # them and the floor reaches them through this module's own recompute instead.
        "count_cols": ("Episode-days at risk", "Acute-care events"),
    }
    return frame, declarations


# ======================================================================================
# SECTION 5.6.  The five STROBE companion ledgers.
# ======================================================================================


def build_ledger_registry_frame() -> tuple[pd.DataFrame, dict[str, Any]]:
    """ledgers-csv/ledger_concept_set_registry.csv.  Fifty-one rows, eight columns.

    Fifty-one, not 852: `registry_rows()` yields one row per CODE OR STEM, the 30 CPT-4
    codes plus the 21 four-character ICD-10-PCS stems.  852 is the CONCEPT count, which is
    what those 51 resolve to in the CDR, and it lives in `meta.concept_set.n_concepts`.
    `REGISTRY_COLUMNS` carries no `concept_id`, so 852 rows would be 852 copies of 51
    distinct ones.

    This ledger carries no counts and therefore never suppresses: it is a property of the
    specification, not of any participant.
    """
    import cs_spine  # local to the call: the fixture and the real run both need it, and
                     # nothing else in this module does.

    columns = list(cs_spine.REGISTRY_COLUMNS)
    frame = pd.DataFrame(cs_spine.registry_rows(), columns=columns)
    for column in columns:
        # Booleans print as `true` and `false`, and every cell in a table CSV is a display
        # string, so the cast is the schema rather than a convenience.
        frame[column] = frame[column].map(
            lambda v: _bool_cell(v) if isinstance(v, bool) else str(v)
        )
    frame = frame.sort_values(["vocabulary_id", "code"], kind="stable").reset_index(drop=True)
    declarations = {
        "kind": "table-csv",
        "exhibit": "",
        "description": (
            "One row per code or stem in the locked spine concept set with its region and "
            "add-on tags"
        ),
        # One row per code makes `code` unique by construction over 51 rows, which trips
        # the near-unique class on a frame wider than the floor.  The rule is right in
        # general and wrong here: a published list of CPT-4 and ICD-10-PCS codes is a
        # property of the specification and identifies nobody.  The other six columns are
        # low-cardinality closed vocabularies and are checked normally.
        "specification_columns": ("code",),
    }
    return frame, declarations


def build_ledger_provenance_frame(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """ledgers-csv/ledger_variable_provenance.csv.  Twelve rows, ten columns, sorted by variable.

    `n_total` is on the file because the denominator is not the same on every row: ten
    rows are episode-grain, `daily_deficit` is person-day grain and `r72` is event grain,
    and those populations differ by orders of magnitude.  Without it a reader divides all
    twelve numerators by the cohort size and misreads two of them by a factor of tens.

    `n_missing` is tested against its COMPLEMENT as well as against itself, and the caller
    does that before it builds the row: `n_total` and `n_missing` are a two-member
    partition of a disclosed total whose other member, the observed count, is never written
    and is therefore recoverable by subtraction.  On an almost-complete variable the
    recovered number is large and harmless; on an almost-entirely-missing one it is exactly
    the cell the floor exists to protect.
    """
    columns = [
        "variable", "display_label", "role", "source_table", "source_concept_set",
        "derivation", "unit", "n_total", "n_missing", "missing_handling",
    ]
    frame = pd.DataFrame(list(rows), columns=columns)
    frame = frame.sort_values("variable", kind="stable").reset_index(drop=True)
    declarations = {
        "kind": "table-csv",
        "exhibit": "",
        "description": (
            "Provenance and missingness for every analysis variable beside the denominator "
            "each one is measured over"
        ),
        "count_cols": ("n_total", "n_missing"),
        # One row per variable makes all three unique by construction.  All three are
        # written by the analyst in the contract's own vocabulary; none is measured.
        # `n_total` and `n_missing` on the same row are counts and are NOT exempt.
        "specification_columns": ("variable", "display_label", "derivation"),
    }
    return frame, declarations


def build_ledger_exclusion_frame(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """ledgers-csv/ledger_exclusion_and_censoring_reasons.csv.  Twenty rows, seven columns.

    THREE SETS OF ROWS ARE PARTITIONS AND THE REST ARE NOT, and the difference is a
    property of the rows rather than of the sentences.  Steps 12, 15 and 16 partition their
    denominators, so one suppressed member forces a second.  The five step 3 indication
    rows overlap by construction, since an episode may carry trauma and malignancy and is
    counted under both, and the step 4 rows are an emergency department population plus
    three rescue routes that overlap and do not exhaust it.  Declaring either as a
    partition would be a false claim that the gate would then enforce.

    Sorted by `step` then the reason-detail SLUG, which is the order 7.12's own table is
    written in and the only reading under which that table is the file's row order.
    """
    columns = [
        "step", "slug", "display_label", "reason_detail",
        "n_episodes", "n_denominator", "share_of_step_dropped",
    ]
    ordered = sorted(rows, key=lambda r: (int(r["step"]), r["_detail_slug"]))
    frame = pd.DataFrame(
        [{c: r[c] for c in columns} for r in ordered], columns=columns
    ).reset_index(drop=True)
    row_partitions: list[tuple[str, tuple[int, ...]]] = []
    for step in (12, 15, 16):
        indices = tuple(i for i, r in enumerate(ordered) if int(r["step"]) == step)
        if len(indices) > 1:
            row_partitions.append(("n_episodes", indices))
    declarations = {
        "kind": "table-csv",
        "exhibit": "",
        "description": (
            "Exclusion and censoring reasons within a rung beside the denominator each "
            "share is taken over"
        ),
        "count_cols": ("n_episodes", "n_denominator"),
        "percentage_columns": ("share_of_step_dropped",),
        "row_partitions": tuple(row_partitions),
        "specification_columns": ("reason_detail",),
    }
    return frame, declarations


def build_ledger_wear_frame(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """ledgers-csv/ledger_wear_availability_by_day.csv.  Seven columns, group by day.

    Seven columns and not nine.  The producer also computes `n_analyzable` and
    `n_inpatient`, and both are deliberately dropped: `n_valid_wear` less `n_analyzable` is
    the count of at-risk days with enough wear and no step record, a two-member partition
    of a total this file already discloses with one member written and the other not, which
    is the shape section 0 refuses.  `n_inpatient` counts readmitted days and would be a
    suppression sentence on most of its rows.

    The absence rule of 4.2 applies here too: a day whose `n_at_risk` fails `disclosable`
    is absent rather than written as a suppressed row.
    """
    columns = [
        "group_slug", "display_label", "group_order", "day",
        "n_at_risk", "n_valid_wear", "share_valid_wear",
    ]
    frame = pd.DataFrame(list(rows), columns=columns)
    # Sorted on the NUMERIC value of the two sort keys, not on their rendered strings.
    # Every cell in a table CSV is a display string, so `day` reaches this frame as text,
    # and a lexicographic sort puts day 10 between day 1 and day 2.  That is a curve drawn
    # in the wrong order, and it would have been byte-stable and therefore invisible to the
    # two-run check.
    frame = frame.assign(
        _order=frame["group_order"].astype(int), _day=frame["day"].astype(int)
    ).sort_values(["_order", "_day"], kind="stable").drop(
        columns=["_order", "_day"]).reset_index(drop=True)
    declarations = {
        "kind": "table-csv",
        "exhibit": "",
        "description": (
            "Days at risk and days of valid wear by procedure group and post-discharge day"
        ),
        "count_cols": ("n_at_risk", "n_valid_wear"),
        "percentage_columns": ("share_valid_wear",),
        "specification_columns": ("day",),
    }
    return frame, declarations


def build_ledger_matched_sets_frame(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """ledgers-csv/ledger_matched_set_sizes.csv.  Four columns, one row per matched-set size.

    Written on every run.  When the tier permits no Arm A analysis it carries one row
    saying so, because a file that is present and empty and a file that is absent are
    different claims and only one of them is checkable.  On that row `set_size` is the
    empty not-applicable cell -- there is no set size to name -- and the three measured
    quantities each carry the `not_permitted_by_tier` sentence of 7.5.  5.6 does not fix
    the shape of that row; this is the reading that keeps the empty-versus-suppressed
    distinction of section 4 intact, and it is reported.
    """
    columns = ["set_size", "n_sets", "n_cases", "share_of_sets"]
    frame = pd.DataFrame(list(rows), columns=columns)
    frame = frame.sort_values("set_size", kind="stable").reset_index(drop=True)
    count_columns = ("n_sets", "n_cases")
    row_partitions: list[tuple[str, tuple[int, ...]]] = []
    if len(frame) > 1:
        # The set-size rows partition a disclosed total, so the secondary-suppression rule
        # of section 0 applies down them -- IN BOTH COUNT COLUMNS AND NOT ONLY IN `n_sets`.
        # A matched set has one size, and a case belongs to one matched set, so the rows
        # partition the total number of sets and the total number of cases alike; the second
        # total is the analyzable event count the attrition ladder's rung 19 already
        # discloses.  Only `n_sets` was declared here, which is the same omission
        # `debt.by_group` carried in `n` and `n_complete_windows`, so the columns are named
        # once and the partition is derived for all of them.
        row_partitions = [(column, tuple(range(len(frame)))) for column in count_columns]
    declarations = {
        "kind": "table-csv",
        "exhibit": "",
        "description": "Distribution of controls per case from the risk-set sampling",
        "count_cols": count_columns,
        "percentage_columns": ("share_of_sets",),
        "row_partitions": tuple(row_partitions),
    }
    return frame, declarations


def matched_sets_not_permitted_row() -> dict[str, str]:
    """The one row 5.6 requires when the tier permits no Arm A analysis."""
    sentence = LABELS["not_permitted_by_tier"]
    return {
        "set_size": "",
        "n_sets": sentence,
        "n_cases": sentence,
        "share_of_sets": sentence,
    }


# ======================================================================================
# Writing the bundle.  One pass, sixteen files, three directories, nothing else.
# ======================================================================================


def _write_frames(
    root: Path,
    specs: Sequence[tuple[str, pd.DataFrame, Mapping[str, Any]]],
) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for relative_path, frame, declarations in specs:
        rows[relative_path] = gated_export(frame, root, relative_path, **declarations)
    return rows


def _assert_registry_matches_probe(previous: str | None, written_md5: str) -> None:
    """5.6: compare this module's registry bytes against the ones `01_probe.py` wrote.

    Both writers call the same pure function, `cs_spine.registry_rows()`, so the bytes are
    identical BY CONSTRUCTION.  Identical by construction is not the same as checked, and
    the difference is the whole point of the comparison: a mismatch cannot be a data
    finding, because `registry_rows()` reads no data, so it means `cs_spine.py` moved
    between Phase 2 and Phase 4, which invalidates every episode built in between.

    `previous` is the md5 of the bytes already at the contract path when this export
    started, or None where the probe has not written there.  It is held in memory rather
    than stashed beside the bundle, because a sidecar file inside `v1/results/` is exactly
    the straggler `verify.py --bundle` rule 3 refuses.
    """
    if previous and previous != written_md5:
        raise ExportError(
            "the concept-set registry this export wrote does not match the one "
            "01_probe.py wrote in Phase 2. Both writers call the same pure function, so "
            "the bytes cannot differ for a data reason: cs_spine.py moved between the two "
            "phases, which invalidates every episode built in between. Halting."
        )


def _swap_bundle_into_place(staging: Path, destination: Path) -> None:
    """Move a finished bundle onto the contract path, atomically or not at all.

    TWO RENAMES AND A ROLLBACK.  A rename within one directory is atomic, so `destination`
    holds the whole previous bundle right up to the instant it holds the whole new one and
    never holds a half-written one.  The previous bundle is moved aside rather than deleted
    first, and it is removed only after the new one is in place.

    A SWAP THAT FAILS HALFWAY IS THE SAME HAZARD ONE LEVEL UP, so it is handled rather than
    assumed away.  If the second rename fails after the first succeeded -- a permissions
    change, a full disk, a directory a viewer has open -- `destination` would be MISSING,
    which is exactly the empty-directory failure this whole path exists to close.  The
    first rename is therefore undone before the failure is re-raised.  If the rollback
    itself fails, nothing is silently lost either: the refusal names the directory the
    previous bundle is sitting in so it can be moved back by hand.
    """
    staging = Path(staging)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    retired: Path | None = None
    if destination.exists():
        # `mkdtemp` reserves a name nothing else holds; the directory itself is removed
        # again immediately, because `os.rename` needs the name free and not merely empty.
        holder = Path(tempfile.mkdtemp(prefix=f".{destination.name}.retired-",
                                       dir=destination.parent))
        holder.rmdir()
        os.rename(destination, holder)
        retired = holder

    try:
        os.rename(staging, destination)
    except BaseException as failure:
        if retired is not None:
            try:
                os.rename(retired, destination)
            except OSError as rollback_failure:
                raise ExportError(
                    f"the bundle swap failed and the rollback failed after it. The PREVIOUS "
                    f"bundle is intact at {retired} and must be moved back to {destination} "
                    f"by hand; the new one is at {staging}. Swap failure: {failure}. "
                    f"Rollback failure: {rollback_failure}"
                ) from failure
        raise
    if retired is not None:
        shutil.rmtree(retired, ignore_errors=True)


def export_bundle(
    root: Path,
    payload: Mapping[str, Any],
    *,
    verify_stability: bool = True,
    compare_registry_to_previous: bool = True,
) -> dict[str, Any]:
    """Render, gate and write the whole bundle.  The only entry point that writes anything.

    The order is fixed by a dependency and not by taste: the fifteen CSVs are written
    first, because `results.json` duplicates each one's md5 and row count into its
    `figures` and `tables` blocks so a consumer can check a file without parsing the
    manifest; `results.json` is written next; `MANIFEST.csv` is assembled last from the
    sixteen rows the writers returned; and `MANIFEST.md5` is written over the manifest's
    own bytes, which is why the manifest carries no row for itself.

    NOTHING IS WRITTEN AT THE CONTRACT PATH UNTIL ALL SIXTEEN FILES EXIST.  Every write
    below lands in a staging directory beside the destination, and the finished bundle is
    swapped in at the end.  A render that raises part way -- a gate refusal, a failed
    check, an editing mistake in a caller -- therefore leaves the bundle already at
    `root` byte-identical, which is the only property that makes a rebuild safe to attempt.
    Delete-then-rebuild is what this replaces, and it has a real failure: a half-landed
    edit raised `ValueError: too many values to unpack` mid-rebuild and left the directory
    empty, which cost the six local modules the only bundle they can be developed against
    and would have cost a Phase 4 run its actual results.

    The staging directory is a SIBLING of the destination rather than a system temporary
    directory, so the swap is a rename inside one filesystem and cannot degrade into a
    copy that can itself fail halfway.

    `compare_registry_to_previous` is the one thing the staging changes.  The registry
    check of 5.6 compares the bytes this export writes against the ones `01_probe.py`
    wrote at the contract path, so the PREVIOUS bytes are read from the destination before
    the staging directory exists.  A caller rebuilding a bundle that has no probe-written
    predecessor -- `write_fixture` is the only one -- passes `False`, because there the
    only bytes at the destination are an earlier copy of its own output.
    """
    destination = Path(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    registry_relative = "ledgers-csv/ledger_concept_set_registry.csv"
    previous_registry = destination / registry_relative
    previous_registry_md5 = (
        md5_of_bytes(previous_registry.read_bytes())
        if compare_registry_to_previous and previous_registry.exists() else None
    )
    root = Path(tempfile.mkdtemp(prefix=f".{destination.name}.staging-",
                                 dir=destination.parent))
    try:
        written = _render_gate_and_write(root, payload, previous_registry_md5,
                                         verify_stability)
        _swap_bundle_into_place(root, destination)
    except BaseException:
        shutil.rmtree(root, ignore_errors=True)
        raise
    written["root"] = str(destination)
    return written


def _render_gate_and_write(
    root: Path,
    payload: Mapping[str, Any],
    previous_registry_md5: str | None,
    verify_stability: bool,
) -> dict[str, Any]:
    """Everything `export_bundle` does inside the staging directory, and nothing outside it."""
    registry_relative = "ledgers-csv/ledger_concept_set_registry.csv"
    results, specs, log = render_bundle(payload)

    stable = True
    if verify_stability:
        # 8.2 and check `csv_bytes_stable_across_two_runs`: the exporter writes the bundle
        # twice and diffs the bytes.  A timestamp inside any CSV, a dict-ordering change or
        # an unsorted groupby would all show up here and nowhere else.
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "results"
            _write_frames(first, specs)
            second_rows = _write_frames(root, specs)
            stable = all(
                filecmp.cmp(first / name, root / name, shallow=False)
                for name, _, _ in specs
            )
    else:
        second_rows = _write_frames(root, specs)

    _assert_registry_matches_probe(
        previous_registry_md5, second_rows[registry_relative]["md5"])

    for key, relative_path in (
        ("figure1", "figures-csv/figure1_strobe_ladder.csv"),
        ("figure2", "figures-csv/figure2_daily_activity.csv"),
        ("figure3", "figures-csv/figure3_forest.csv"),
        ("figure4", "figures-csv/figure4_event_centered_activity.csv"),
    ):
        results["figures"][key]["md5"] = second_rows[relative_path]["md5"]
        results["figures"][key]["rows"] = second_rows[relative_path]["n_rows"]
    for key, relative_path in (
        ("table1", "tables-csv/table1_cohort_characteristics.csv"),
        ("table2", "tables-csv/table2_adjusted_debt.csv"),
        ("table3a", "tables-csv/table3_gate_part_a.csv"),
        ("table3b", "tables-csv/table3_gate_part_b.csv"),
        ("table4", "tables-csv/table4_collider_comparison.csv"),
    ):
        results["tables"][key]["md5"] = second_rows[relative_path]["md5"]
        results["tables"][key]["rows"] = second_rows[relative_path]["n_rows"]

    for entry in results["checks"]["entries"]:
        if entry["slug"] == "csv_bytes_stable_across_two_runs":
            entry["passed"] = bool(stable)
            entry["detail"] = "" if stable else "two runs wrote different bytes"
    results["checks"]["n_passed"] = sum(
        1 for e in results["checks"]["entries"] if e["passed"]
    )
    results["checks"]["n_failed"] = (
        results["checks"]["n_checks"] - results["checks"]["n_passed"]
    )
    if results["checks"]["n_failed"]:
        failed = [e["slug"] for e in results["checks"]["entries"] if not e["passed"]]
        raise ExportError(
            f"refusing to complete the export: {len(failed)} check(s) failed: {failed}. "
            f"Any failed check is a stop condition, not a warning."
        )

    json_row = write_results_json(results, root, log)
    manifest_md5, _ = write_manifest(root, [json_row, *second_rows.values()])
    # `root` here is the staging directory and is about to stop existing under that name.
    # `export_bundle` overwrites this field with the contract path it swapped the bundle
    # onto, so no caller ever reads a directory that was renamed out from under it.
    return {
        "root": str(root),
        "manifest_md5": manifest_md5,
        "rows": [json_row, *second_rows.values()],
        "results": results,
    }


# ======================================================================================
# Validating a written bundle.  Everything `verify.py --bundle` will re-assert on arrival,
# run here first, because a bundle that passed inside the perimeter and a bundle that
# arrived intact are different claims and this is the half the perimeter can make.
# ======================================================================================


def validate_bundle(root: Path) -> list[str]:
    """Return every way the written bundle fails the contract.  Empty list means it passes."""
    root = Path(root)
    problems: list[str] = []

    for name in BUNDLE_FILES + ("MANIFEST.csv", "MANIFEST.md5"):
        if not (root / name).exists():
            problems.append(f"missing file: {name}")
    declared = set(BUNDLE_FILES) | {"MANIFEST.csv", "MANIFEST.md5"}
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            if path.name not in BUNDLE_DIRECTORIES:
                problems.append(f"unexpected directory: {path.relative_to(root)}")
            continue
        relative = path.relative_to(root).as_posix()
        if relative not in declared:
            problems.append(f"straggler file nobody stamped: {relative}")
    if not problems:
        subdirectories = sorted(p.name for p in root.iterdir() if p.is_dir())
        if tuple(subdirectories) != tuple(sorted(BUNDLE_DIRECTORIES)):
            problems.append(f"expected three subdirectories, found {subdirectories}")

    if (root / "MANIFEST.csv").exists():
        manifest = pd.read_csv(root / "MANIFEST.csv", dtype=str, keep_default_na=False)
        if list(manifest.columns) != list(MANIFEST_COLUMNS):
            problems.append(f"MANIFEST.csv columns are {list(manifest.columns)}")
        if len(manifest) != len(BUNDLE_FILES):
            problems.append(
                f"MANIFEST.csv has {len(manifest)} data rows, not {len(BUNDLE_FILES)}"
            )
        if list(manifest["file"]) != list(BUNDLE_FILES):
            problems.append("MANIFEST.csv rows are not in the fixed order of section 8.3")
        for _, row in manifest.iterrows():
            target = root / row["file"]
            if not target.exists():
                problems.append(f"manifest names a file that does not exist: {row['file']}")
                continue
            actual = md5_of_bytes(target.read_bytes())
            if actual != row["md5"]:
                problems.append(f"md5 mismatch on {row['file']}")
            if row["kind"] not in disclosure.MANIFEST_KINDS:
                problems.append(f"manifest kind {row['kind']!r} on {row['file']}")
            if target.suffix == ".csv":
                frame = pd.read_csv(target, dtype=str, keep_default_na=False)
                if len(frame) != int(row["n_rows"]):
                    problems.append(
                        f"{row['file']}: {len(frame)} data rows, manifest says {row['n_rows']}"
                    )
                if frame.shape[1] != int(row["n_columns"]):
                    problems.append(
                        f"{row['file']}: {frame.shape[1]} columns, manifest says "
                        f"{row['n_columns']}"
                    )
        if (root / "MANIFEST.md5").exists():
            stated = (root / "MANIFEST.md5").read_text(encoding="utf-8")
            if not re.fullmatch(r"[0-9a-f]{32}\n", stated):
                problems.append("MANIFEST.md5 is not 32 hex characters plus a newline")
            elif stated.strip() != md5_of_bytes((root / "MANIFEST.csv").read_bytes()):
                problems.append("MANIFEST.md5 does not match the bytes of MANIFEST.csv")

    if not (root / "results.json").exists():
        return problems
    raw = (root / "results.json").read_bytes()
    if not raw.endswith(b"\n"):
        problems.append("results.json does not end with a newline")
    results = json.loads(raw.decode("utf-8"))

    for block in ("meta", "denominators", "attrition", "cohort", "debt", "sensitivity",
                  "gate", "figures", "tables", "suppressed", "checks"):
        if block not in results:
            problems.append(f"results.json is missing the mandatory block {block!r}")
    if results.get("meta", {}).get("schema_version") != CONTRACT_VERSION:
        problems.append("meta.schema_version does not equal this contract's version")
    if results.get("meta", {}).get("manifest_rows") != len(BUNDLE_FILES):
        problems.append("meta.manifest_rows does not equal the manifest data-row count")
    problems.extend(_validate_json_types(results))

    for key, block in results.get("figures", {}).items():
        problems.extend(_validate_exhibit_block(root, key, block, figure=True))
    for key, block in results.get("tables", {}).items():
        problems.extend(_validate_exhibit_block(root, key, block, figure=False))
    problems.extend(
        exhibit_budget_problems(results.get("figures", {}), results.get("tables", {}))
    )

    # Every count cell in every arriving file is a legal disclosed count.  This is the
    # arrival-side form of R1: the true counts are gone by now, so the only question left
    # is whether each rendered cell is a legal one.
    for relative_path, count_columns in COUNT_COLUMNS_BY_FILE.items():
        target = root / relative_path
        if not target.exists():
            continue
        frame = pd.read_csv(target, dtype=str, keep_default_na=False)
        for column in count_columns:
            if column not in frame.columns:
                problems.append(f"{relative_path}: declared count column {column} is absent")
                continue
            for cell in frame[column]:
                if cell == "" or _cell_is_hidden(cell):
                    continue
                parsed = _parse_display_count(cell)
                if parsed is None or not is_legal_disclosed_count(parsed):
                    problems.append(
                        f"{relative_path}: column {column} holds a cell that is not a "
                        f"legal disclosed count"
                    )
                    break
    return problems


COUNT_COLUMNS_BY_FILE: dict[str, tuple[str, ...]] = {
    "figures-csv/figure1_strobe_ladder.csv":
        ("n_in", "n_dropped", "n_out", "n_carried_forward"),
    "figures-csv/figure2_daily_activity.csv": ("n_contributing",),
    "figures-csv/figure3_forest.csv": ("n",),
    "figures-csv/figure4_event_centered_activity.csv": ("n_contributing",),
    "tables-csv/table4_collider_comparison.csv":
        ("Episode-days at risk", "Acute-care events"),
    "ledgers-csv/ledger_variable_provenance.csv": ("n_total", "n_missing"),
    "ledgers-csv/ledger_exclusion_and_censoring_reasons.csv":
        ("n_episodes", "n_denominator"),
    "ledgers-csv/ledger_wear_availability_by_day.csv": ("n_at_risk", "n_valid_wear"),
    "ledgers-csv/ledger_matched_set_sizes.csv": ("n_sets", "n_cases"),
}


def _validate_exhibit_block(
    root: Path, key: str, block: Mapping[str, Any], *, figure: bool
) -> list[str]:
    problems: list[str] = []
    required = ["file", "columns", "rows", "md5", "denominator", "n", "legend",
                "exhibit", "exhibit_set"]
    required += ["sort_keys", "plate_note"] if figure else ["key_columns", "footer_file"]
    for field in required:
        if field not in block:
            problems.append(f"{'figures' if figure else 'tables'}.{key} lacks {field!r}")
    target = root / block["file"]
    if not target.exists():
        problems.append(f"{block['file']} named in results.json does not exist")
        return problems
    frame = pd.read_csv(target, dtype=str, keep_default_na=False)
    if list(frame.columns) != list(block["columns"]):
        problems.append(f"{block['file']}: header does not equal its declared column list")
    if len(frame) != int(block["rows"]):
        problems.append(f"{block['file']}: row count does not equal its declared rows")
    if md5_of_bytes(target.read_bytes()) != block["md5"]:
        problems.append(f"{block['file']}: md5 in results.json does not match the bytes")
    return problems


def exhibit_budget_problems(
    figures: Mapping[str, Any], tables: Mapping[str, Any]
) -> list[str]:
    """Every way the rendered exhibit blocks break the locked three-and-three budget.

    ONE IMPLEMENTATION, TWO CALL SITES.  `render_bundle` raises on it before a frame is
    written, and `validate_bundle` reports it on a bundle read back off disk, so the
    budget is checked on the way out and again on the way in.  A second copy of the
    arithmetic is a second place for it to be wrong, and this is the arithmetic a reader
    gets wrong by counting the files or the keys instead of the exhibits.
    """
    problems: list[str] = []
    for block_name, blocks, register, budget in (
        ("figures", figures, FIGURE_EXHIBITS, PRIMARY_FIGURE_BUDGET),
        ("tables", tables, TABLE_EXHIBITS, PRIMARY_TABLE_BUDGET),
    ):
        if set(blocks) != set(register):
            problems.append(
                f"results.json[{block_name!r}] carries {sorted(blocks)} and 3.8's exhibit "
                f"register declares {sorted(register)}"
            )
        primary: set[str] = set()
        for key in sorted(blocks):
            block = blocks[key]
            exhibit = block.get("exhibit")
            exhibit_set = block.get("exhibit_set")
            if exhibit_set not in EXHIBIT_SETS:
                problems.append(
                    f"{block_name}.{key}.exhibit_set is {exhibit_set!r}; 3.8 allows only "
                    f"{sorted(EXHIBIT_SETS)}"
                )
            declared = register.get(key)
            if declared is not None and (exhibit, exhibit_set) != declared:
                problems.append(
                    f"{block_name}.{key} declares exhibit {exhibit!r} in the "
                    f"{exhibit_set!r} set and 3.8's register says {declared}"
                )
            if exhibit_set == "primary" and isinstance(exhibit, str):
                primary.add(exhibit)
        if len(primary) != budget:
            problems.append(
                f"the primary exhibit set carries {len(primary)} {block_name}, "
                f"{sorted(primary)}. CLAUDE.md section 2 rule 7 fixes it at {budget} and "
                f"sends everything beyond it to the supplement. Counting bundle files or "
                f"block keys is not how this budget is checked: it is counted over "
                f"distinct exhibit names among the primary blocks"
            )
    return problems


def assert_exhibit_budget(
    figures: Mapping[str, Any], tables: Mapping[str, Any]
) -> None:
    """HALT on a bundle whose primary exhibit set is not three figures and three tables."""
    problems = exhibit_budget_problems(figures, tables)
    if problems:
        listed = "\n".join(f"  {i}. {p}" for i, p in enumerate(problems, 1))
        raise ExportError(
            f"refusing to export: the exhibit set does not match the locked budget\n"
            f"{listed}"
        )


_JSON_TYPES: tuple[tuple[str, type | tuple[type, ...]], ...] = (
    ("meta.schema_version", str),
    ("meta.contract_sha256", str),
    ("meta.study", str),
    ("meta.generated_utc", str),
    ("meta.run_id", str),
    ("meta.manifest_rows", int),
    ("meta.seeds.python", int),
    # A STRING, because the salt is a string: `build_all.sql` declares
    # `sampling_salt STRING` and `build_params` publishes the column at that type.  It was
    # declared an integer for as long as it was a fabricated integer, which is how a type
    # error and a value error travelled together.
    ("meta.sampling_salt", str),
    ("meta.estimator.rung_index", int),
    ("meta.estimator.r_used", bool),
    ("meta.analysis_plan.locked_before_first_count", bool),
    ("meta.cdr.dates_shifted", bool),
    ("attrition.closes", bool),
    ("attrition.rounding_footnote", str),
    ("cohort.collapse_level", str),
    ("cohort.collapse_level_index", int),
    ("debt.estimand.unit", str),
    # The one boolean a Methods section cannot afford to lose.  It is type-checked on
    # arrival as well as asserted on the way out, because a `prespecified` that has become a
    # string, or gone missing, is a bundle whose consumer would have to decide for itself
    # whether the guideline-mandated contrast beside the prespecified one was planned.
    ("debt.unadjusted_model.prespecified", bool),
    ("gate.tier.index", int),
    ("gate.tier.exhibit_set", str),
    ("gate.arm_a.permitted", bool),
    ("suppressed.n_entries", int),
    ("checks.n_checks", int),
    ("checks.n_passed", int),
    ("checks.n_failed", int),
    ("checks.policy", str),
)


def _validate_json_types(results: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    for path, expected in _JSON_TYPES:
        node: Any = results
        try:
            for part in path.split("."):
                node = node[part]
        except (KeyError, TypeError):
            problems.append(f"results.json is missing {path}")
            continue
        # bool is a subclass of int in Python, so an int field would accept True.
        if expected is int and isinstance(node, bool):
            problems.append(f"results.json {path} is a boolean where an integer is declared")
        elif not isinstance(node, expected):
            problems.append(
                f"results.json {path} is {type(node).__name__}, not "
                f"{getattr(expected, '__name__', expected)}"
            )
    # THE SALT, ON ARRIVAL AS WELL AS ON THE WAY OUT.  `_render_meta` refuses to build a
    # bundle whose salt is not the DAG's; this asks the same question of a bundle that has
    # already been written, which is the only form of the question a `--validate` run on a
    # directory can ask.  Both exist for the reason section 0 gives for every paired check
    # here: a value asserted once, at the moment it is constructed, is a value nothing
    # re-reads.
    meta = results.get("meta", {})
    if "farm_fingerprint" in meta.get("seeds", {}):
        problems.append(
            "meta.seeds.farm_fingerprint is the sampling salt filed as a seed; the salt is "
            "meta.sampling_salt and seeds holds seeds"
        )
    for name, value in sorted(meta.get("seeds", {}).items()):
        if isinstance(value, bool) or not isinstance(value, int):
            problems.append(f"meta.seeds.{name} is {value!r}, which is not an integer seed")
    try:
        declared_salt = dag_sampling_salt_from_tree()
    except ExportError as exc:                       # the DAG is not beside this module
        problems.append(str(exc))
    else:
        if meta.get("sampling_salt") != declared_salt:
            problems.append(
                f"meta.sampling_salt is {meta.get('sampling_salt')!r} and {BUILD_SQL_NAME} "
                f"declares {declared_salt!r}; the bundle records a salt the DAG in this tree "
                f"does not use, so its matched sets cannot be reproduced from it"
            )
    if len(results.get("attrition", {}).get("rungs", [])) != len(ATTRITION_RUNGS):
        problems.append("attrition.rungs is not the nineteen-rung ladder")
    if len(results.get("sensitivity", {})) != len(SENSITIVITY_ROWS):
        problems.append("sensitivity does not carry the fourteen plotted rows")
    if set(results.get("sensitivity", {})) & set(SUPPLEMENTARY_SENSITIVITY_ROWS):
        problems.append("a supplementary sensitivity row has a key in results.json")
    if len(results.get("gate", {}).get("stages", [])) != len(GATE_STAGES):
        problems.append("gate.stages is not the six-stage ledger")
    if results.get("checks", {}).get("n_checks") != len(CHECK_SLUGS):
        problems.append("checks.n_checks is not thirteen")
    if len(results.get("figures", {})) != 4 or len(results.get("tables", {})) != 5:
        # 3.8: four figure keys and five table keys, six table FILES, sixteen manifest rows.
        # The Table 2 footer is a file and not an exhibit, so it has no `tables` key.
        problems.append("figures must have four keys and tables five")
    if results.get("suppressed", {}).get("n_entries") != len(
        results.get("suppressed", {}).get("entries", [])
    ):
        problems.append("suppressed.n_entries does not equal len(entries)")
    return problems


# ======================================================================================
# SECTION 3.  Rendering results.json from TRUE counts.
#
# Everything below receives true integers and asks `disclosable` of them.  Nothing below
# receives a rounded count: `round20` is called here and nowhere upstream, which is what
# makes "round and floor-test at the boundary, never before" a property of the code rather
# than a convention.
# ======================================================================================


class _Union:
    """Tiny union-find over (step, field) pairs that carry the SAME true count.

    Consecutive rungs share a number: `n_out` of one rung and `n_in` of the next are one
    integer written twice, and a terminal rung's `n_in` and `n_out` are the same again.  So
    suppressing one and disclosing the other would publish the very count that was hidden,
    one row down.  The classes are what make that impossible.
    """

    def __init__(self) -> None:
        self.parent: dict[Any, Any] = {}

    def find(self, item: Any) -> Any:
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: Any, right: Any) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[a] = b


_LADDER_FIELDS = ("n_in", "n_dropped", "n_out", "n_carried_forward")


def _render_attrition(payload: Mapping[str, Any], log: SuppressionLog) -> dict[str, Any]:
    """The nineteen-rung ladder, closure asserted on the TRUE integers before rounding.

    Exact closure is asserted here, inside the perimeter, where the unrounded counts still
    exist.  The local side cannot do that: each exported count is independently rounded and
    carries an error of at most 10, so an identity over k rounded terms carries an error of
    at most 10k, and demanding exact closure on rounded boxes would force this module to
    adjust a published number to make the arithmetic work.  That is falsification.  The
    published resolution is the footnote every exhibit prints verbatim, and `closes_exact`
    is what carries the guarantee across.
    """
    rungs_in = {int(r["step"]): r for r in payload["ladder"]}
    if len(rungs_in) != len(ATTRITION_RUNGS):
        raise ExportError("the ladder handed to the exporter is not the nineteen rungs")

    truth: dict[tuple[int, str], int] = {}
    for step, slug, kind, unit in ATTRITION_RUNGS:
        source = rungs_in[step]
        if source["slug"] != slug or source["kind"] != kind or source["unit"] != unit:
            raise ExportError(f"rung {step} does not match the contract's ladder")
        for field in _LADDER_FIELDS:
            value = source.get(field)
            if value is not None:
                truth[(step, field)] = int(value)

    # -- exact closure on the true integers.  A stop condition, not a warning.
    closes: dict[int, bool] = {}
    for step, _slug, kind, _unit in ATTRITION_RUNGS:
        if kind == "exclusion":
            ok = truth[(step, "n_in")] - truth[(step, "n_dropped")] == truth[(step, "n_out")]
        elif kind == "terminal":
            ok = truth[(step, "n_in")] == truth[(step, "n_out")]
        else:
            ok = (truth[(step, "n_in")] - truth.get((step, "n_dropped"), 0)
                  == truth[(step, "n_carried_forward")]) if (step, "n_carried_forward") in truth \
                else True
        closes[step] = bool(ok)
    for index in range(len(ATTRITION_RUNGS) - 1):
        here = ATTRITION_RUNGS[index][0]
        after = ATTRITION_RUNGS[index + 1][0]
        if truth[(here, "n_out")] != truth[(after, "n_in")]:
            closes[here] = False
            closes[after] = False
    broken = sorted(step for step, ok in closes.items() if not ok)
    if broken:
        raise ExportError(
            f"the attrition ladder does not close on the unrounded integers at step(s) "
            f"{broken}. Halting: a ladder that does not close inside the perimeter makes "
            f"nothing downstream trustworthy."
        )

    # -- which cells are hidden, and why.  Own size first, then partitions, then the chain,
    # iterated to a fixed point because forcing one member can leave another alone.
    classes = _Union()
    for index in range(len(ATTRITION_RUNGS) - 1):
        classes.union((ATTRITION_RUNGS[index][0], "n_out"),
                      (ATTRITION_RUNGS[index + 1][0], "n_in"))
    for step, _slug, kind, _unit in ATTRITION_RUNGS:
        if kind == "terminal":
            classes.union((step, "n_in"), (step, "n_out"))

    state: dict[tuple[int, str], str] = {}
    for key, value in truth.items():
        state[key] = "show" if disclosable(value) else "own"

    partitions: list[tuple[tuple[int, str], ...]] = []
    for step, _slug, kind, _unit in ATTRITION_RUNGS:
        if kind == "exclusion":
            partitions.append(((step, "n_dropped"), (step, "n_out")))
        elif (step, "n_carried_forward") in truth:
            partitions.append(((step, "n_dropped"), (step, "n_carried_forward")))

    for _ in range(len(ATTRITION_RUNGS) + 2):
        changed = False
        hidden_classes = {
            classes.find(key) for key, value in state.items() if value != "show"
        }
        for key, value in list(state.items()):
            if value == "show" and classes.find(key) in hidden_classes:
                state[key] = "secondary"
                changed = True
        for members in partitions:
            present = [m for m in members if m in state]
            hidden = [m for m in present if state[m] != "show"]
            if len(hidden) == 1 and len(present) > 1:
                for member in present:
                    if state[member] == "show":
                        state[member] = "secondary"
                        changed = True
                        break
        if not changed:
            break

    def node_for(step: int, field: str, index: int) -> Any:
        """A rung's node, or None where the field does not apply to this rung.

        Three states, two of which are suppression: "show" discloses, "own" lets
        `count_node` suppress on the true count's own size, and "secondary" forces the
        suppression to protect a sibling and carries the other sentence for it.
        """
        key = (step, field)
        if key not in truth:
            return None
        return count_node(
            truth[key],
            log=log,
            path=f"attrition.rungs[{index}].{field}",
            force_suppress=state[key] == "secondary",
        )

    rungs: list[dict[str, Any]] = []
    for index, (step, slug, kind, unit) in enumerate(ATTRITION_RUNGS):
        rungs.append({
            "step": step,
            "slug": slug,
            "display_label": LABELS[slug],
            "kind": kind,
            "unit": unit,
            "n_in": node_for(step, "n_in", index),
            "n_dropped": node_for(step, "n_dropped", index),
            "n_out": node_for(step, "n_out", index),
            "n_carried_forward": node_for(step, "n_carried_forward", index),
            # `reason` carries no vocabulary of its own: it is the rung's own slug on an
            # exclusion rung, the literal `unit_change` on a conversion rung and the empty
            # string on a terminal one.  A naive LABELS[reason] therefore raises by design.
            "reason": slug if kind == "exclusion" else ("unit_change" if kind == "conversion" else ""),
            "reason_display": RUNG_REASON_DISPLAY[slug],
            "closes_exact": closes[step],
        })

    segments = _render_segments(truth, state, closes, log)
    return {
        "rungs": rungs,
        "segments": segments,
        "closes": all(closes.values()) and all(s["closes_exact"] for s in segments),
        "rounding_footnote": ROUNDING_FOOTNOTE,
    }


_SEGMENT_SPEC: tuple[tuple[str, int, int, tuple[int, ...]], ...] = (
    ("persons", 1, 2, (1, 2)),
    ("episodes", 2, 16, tuple(range(3, 16))),
    ("events", 17, 19, (18,)),
)


def _render_segments(
    truth: Mapping[tuple[int, str], int],
    state: Mapping[tuple[int, str], str],
    closes: Mapping[int, bool],
    log: SuppressionLog,
) -> list[dict[str, Any]]:
    """The three unit regimes.  Asserting one global closure over them asserts an identity
    that does not exist: persons, episodes and events do not share a denominator."""
    kinds = {step: kind for step, _slug, kind, _unit in ATTRITION_RUNGS}
    segments: list[dict[str, Any]] = []
    for index, (unit, first, last, drop_steps) in enumerate(_SEGMENT_SPEC):
        start_key = (first, "n_out") if kinds[first] == "conversion" else (first, "n_in")
        end_key = (last, "n_carried_forward") if unit == "persons" else (last, "n_out")
        sum_true = sum(truth[(s, "n_dropped")] for s in drop_steps)
        exact = truth[start_key] - sum_true == truth[end_key]
        if not exact:
            raise ExportError(
                f"the {unit} segment of the attrition ladder does not close on the "
                f"unrounded integers. Halting."
            )
        any_drop_hidden = any(state[(s, "n_dropped")] != "show" for s in drop_steps)
        path = f"attrition.segments[{index}]"
        n_start = count_node(truth[start_key], log=log, path=f"{path}.n_start",
                             force_suppress=state[start_key] == "secondary")
        n_end = count_node(truth[end_key], log=log, path=f"{path}.n_end",
                           force_suppress=state[end_key] == "secondary")
        if any_drop_hidden:
            log.add(locus="results.json", path=f"{path}.sum_dropped", kind="count",
                    reason="cell_below_threshold", rule="R1 cell below floor")
            sum_dropped: dict[str, Any] = suppressed_node("cell_below_threshold")
        else:
            sum_dropped = count_node(sum_true, log=log, path=f"{path}.sum_dropped")
        n_rounded_terms = 2 + len(drop_steps)
        residual = None
        if not any(is_node_suppressed(n) for n in (n_start, n_end, sum_dropped)):
            residual = int(n_start["n"]) - int(sum_dropped["n"]) - int(n_end["n"])
        segments.append({
            "unit": unit,
            "first_step": first,
            "last_step": last,
            "n_start": n_start,
            "n_end": n_end,
            "sum_dropped": sum_dropped,
            "n_rounded_terms": n_rounded_terms,
            # 10 per independently rounded term.  Exported so the local side compares
            # rather than recomputes, and so a change of base moves one number here.
            "tolerance": (disclosure.ROUND_BASE // 2) * n_rounded_terms,
            "closes_exact": bool(exact and all(closes[s] for s in drop_steps)),
            "rounded_residual": residual,
        })
    return segments


def _checked_seeds(seeds: Any) -> dict[str, int]:
    """`meta.seeds`, holding SEEDS and nothing else.

    ANALYSIS-PLAN.md section 10 fixes `SEED = 0` "everywhere, in Python and in R" and 4.5
    repeats it for the FARM_FINGERPRINT sampling by name, so every member of this block is
    an integer and `verify.py` compares every member against that one value.  The block was
    also carrying the sampling SALT, which is a string, which is not 0, and which is not a
    seed; the consequence was that the one block whose members are all governed by a single
    plan sentence had a member that sentence does not govern, and the comparison that should
    have caught it read as a document disagreement instead of as a misfiling.

    A salt filed here is refused BY NAME as well as by type, because the name is how it got
    here: `farm_fingerprint` is what the salt was called when it was a seed, and a caller
    reaching for the old key is reaching for a field that has moved rather than one that is
    gone.
    """
    if not isinstance(seeds, Mapping) or not seeds:
        raise ExportError(
            "meta.seeds is absent or empty. ANALYSIS-PLAN.md section 10 fixes SEED = 0 "
            "everywhere and the bundle is what records that the run honoured it."
        )
    if "farm_fingerprint" in seeds:
        raise ExportError(
            "meta.seeds.farm_fingerprint is the sampling SALT filed as a seed. The salt is a "
            "string, it is published as `build_params.sampling_salt`, and it is now carried "
            "as `meta.sampling_salt`, a sibling of this block. `seeds` holds seeds."
        )
    out: dict[str, int] = {}
    for name in sorted(seeds):
        value = seeds[name]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ExportError(
                f"meta.seeds.{name} is {value!r}, which is not an integer. Every member of "
                f"this block is the seed ANALYSIS-PLAN.md section 10 fixes at 0; a "
                f"reproducibility input that is not a seed goes beside the block and not "
                f"inside it, the way `meta.sampling_salt` does."
            )
        out[name] = int(value)
    return out


def _checked_sampling_salt(salt: Any) -> str:
    """`meta.sampling_salt`, held to what the DAG declares rather than to what was typed.

    THE ASSERTION THAT WOULD HAVE CAUGHT THE FABRICATED VALUE, and it is the only reason
    this field can be trusted at all.  The payload's salt comes from
    `build_params.sampling_salt`, which is what the run actually sampled with; the DAG on
    disk is what the run was supposed to sample with.  Equality of the two is the claim the
    bundle is making when it records a salt, so it is checked and not assumed.  An integer
    that no `DECLARE` in `build_all.sql` produces fails this on the first character.
    """
    declared = dag_sampling_salt_from_tree()
    if not isinstance(salt, str) or not salt:
        raise ExportError(
            f"meta.sampling_salt is {salt!r}. It is the STRING the DAG publishes as "
            f"`build_params.sampling_salt` and that `build_all.sql` feeds to "
            f"FARM_FINGERPRINT beside the seed; {BUILD_SQL_NAME} declares it as "
            f"{declared!r}. A session reproducing the matched sets uses this value, so a "
            f"missing or mistyped one is a reproducibility claim the bundle cannot support."
        )
    if salt != declared:
        raise ExportError(
            f"meta.sampling_salt is {salt!r} and {BUILD_SQL_NAME} declares {declared!r}. "
            f"The salt orders the control risk set through "
            f"FARM_FINGERPRINT(FORMAT('%s|%d|...', sampling_salt, seed, ...)), so the two "
            f"disagreeing means the bundle was produced by a different DAG than the one in "
            f"this tree and the matched sets cannot be reproduced from what it records. The "
            f"value is READ from `build_params.sampling_salt` and cross-checked here; it is "
            f"never transcribed into this module."
        )
    return salt


def _render_meta(payload: Mapping[str, Any]) -> dict[str, Any]:
    """The provenance block.  It carries NO participant-derived value.

    `generated_utc`, `resolved_utc` and `locked_utc` are run timestamps, not participant
    dates, and the date ban of section 10 is about participant-derived columns.  The
    distinction is written down rather than assumed because the two look identical.
    """
    meta = dict(payload["meta"])
    estimator = dict(meta["estimator"])
    index = int(estimator["rung_index"])
    slug = dict(ESTIMATOR_RUNGS)[index]
    if estimator.get("rung_slug", slug) != slug:
        raise ExportError("meta.estimator.rung_slug does not match its rung index")
    estimator["rung_slug"] = slug
    estimator["rung_display"] = LABELS[slug]
    estimator["r_used"] = index <= 2
    meta["estimator"] = estimator
    meta["schema_version"] = CONTRACT_VERSION
    meta["manifest_rows"] = len(BUNDLE_FILES)
    meta["seeds"] = _checked_seeds(meta.get("seeds"))
    meta["sampling_salt"] = _checked_sampling_salt(meta.get("sampling_salt"))
    meta["arm"] = {
        "slug": meta["arm"]["slug"],
        "display": LABELS[meta["arm"]["slug"]],
        "selected_by": meta["arm"]["selected_by"],
        "tier_slug": meta["arm"]["tier_slug"],
    }
    return meta


def _render_denominators(payload: Mapping[str, Any], log: SuppressionLog) -> dict[str, Any]:
    """Every denominator any exhibit prints, by name, each already `round20`-rounded.

    `denominators[key]` is an object and NOT a count node: it carries provenance the node
    shape has no room for, and the house `denom_n()` reads `["n"]` off it unmodified.
    """
    supplied = payload["denominators"]
    # 3.2 calls its key list "required, all mandatory", and until this check existed the
    # word was decoration: this function rendered whatever the payload handed it, so a
    # caller that omitted one produced a bundle carrying an exhibit that names a
    # denominator key nobody wrote.  An exhibit's `denominator` field is a POINTER, and a
    # pointer whose target is optional is not a pointer.
    missing = [key for key in REQUIRED_DENOMINATORS if key not in supplied]
    if missing:
        raise ExportError(
            f"the payload is missing {len(missing)} mandatory denominator(s): {missing}. "
            f"3.2 requires all {len(REQUIRED_DENOMINATORS)} on every run and every "
            f"exhibit's `denominator` names one of them."
        )
    unknown_units = sorted({
        str(entry["unit"]) for entry in supplied.values()
        if entry["unit"] not in DENOMINATOR_UNITS
    })
    if unknown_units:
        raise ExportError(
            f"denominator unit(s) {unknown_units} are not in 3.2's vocabulary "
            f"{sorted(DENOMINATOR_UNITS)}. A unit this contract does not declare is a "
            f"unit no consumer can render."
        )
    out: dict[str, Any] = {}
    for key, entry in supplied.items():
        true_n = int(entry["true_n"])
        if not disclosable(true_n):
            raise ExportError(
                f"denominator {key!r} is below the disclosure floor. A bundle whose "
                f"default denominator cannot be printed is a no_estimand run, which "
                f"section 3.4 handles by exporting the ladder alone."
            )
        rounded = int(round20(true_n))
        out[key] = {
            "n": rounded,
            "unit": entry["unit"],
            "display": f"{rounded:,}",
            "display_n_equals": f"n = {rounded:,}",
            "definition": entry["definition"],
            "used_for": entry["used_for"],
        }
    return out


def _render_cohort(payload: Mapping[str, Any], log: SuppressionLog) -> dict[str, Any]:
    """Group sizes, window constants and the collapse level the data reached.

    The number of groups is DATA-DEPENDENT and every consumer must treat it that way, so
    the list is built from the payload and never padded to four.
    """
    level = payload["collapse_level"]
    groups = []
    for index, entry in enumerate(payload["groups"]):
        slug = entry["slug"]
        node = count_node(entry["true_n"], log=log, path=f"cohort.groups[{index}].n")
        if is_node_suppressed(node):
            raise ExportError(
                f"group {slug!r} is below the disclosure floor at collapse level {level!r}. "
                f"The collapse ladder of ANALYSIS-PLAN.md 2.5 is decided BEFORE the export, "
                f"on the exact within-perimeter counts, so a suppressed group here means "
                f"the wrong level was selected."
            )
        # The only permitted composition in this module: a label by lookup, an n by format.
        header = f"{LABELS[slug]} (n = {int(node['n']):,})"
        groups.append({
            "slug": slug,
            "display_label": LABELS[slug],
            "order": int(entry["order"]),
            "n": node,
            "column_header": header,
        })
    window = payload["window"]
    return {
        "groups": groups,
        "collapse_level": level,
        "collapse_level_index": COLLAPSE_LEVELS[level],
        "collapse_reason": payload["collapse_reason"],
        "collapse_footnote": payload.get("collapse_footnote"),
        "denominator_index": list(payload["denominator_index"]),
        "window": {
            "accrual_first_day": scalar_node(window["accrual_first_day"]),
            "accrual_last_day": scalar_node(window["accrual_last_day"]),
            "follow_up_last_day": scalar_node(window["follow_up_last_day"]),
            "baseline_first_day": scalar_node(window["baseline_first_day"]),
            "baseline_last_day": scalar_node(window["baseline_last_day"]),
            "baseline_min_valid_days": scalar_node(window["baseline_min_valid_days"]),
            "baseline_min_span_days": scalar_node(window["baseline_min_span_days"]),
            "valid_day_min_minutes": scalar_node(window["valid_day_min_minutes"]),
            "display_accrual": window["display_accrual"],
            "display_baseline": window["display_baseline"],
        },
        # Recorded so the local side can print the floor without retyping it.  This is a
        # scalar node, not a comparison, which is why the ast.Compare walk does not see it.
        "min_cell": scalar_node(MIN_CELL),
    }


# The one sensitivity row whose estimate is a BOUND rather than an interval.  It carries
# the same number as `debt.delta_shift.tipping_point_point_estimate` and 9.1's worked
# example writes both with `lo == hi == est` and an empty `display_ci`; 4.3 gives the row
# `render = panel` for the same reason, that a tipping curve is not a point estimate with an
# interval.  Rendering one of the two as a bound and the other as an interval would put two
# shapes on one number in one bundle.  Contract 1.7.0 settled this: 3.5 now counts FIVE
# bound nodes and names this one as the fifth, and 3.6 no longer calls it an estimate node,
# so the shape this module took from 9.1's worked example is the shape 3.5 declares.
BOUND_SENSITIVITY_ROWS: frozenset[str] = frozenset({"delta_shift_tipping_point"})

# ANALYSIS-PLAN.md 3.11, transcribed the way every other locked vocabulary in this module is
# transcribed: the delta grid, and its prespecified extension in 0.5 increments to 4.0 and
# no further.  It is the SET OF VALUES a tipping point may take, and this module said so
# twice in prose -- "A tipping point is a GRID COORDINATE", "a grid coordinate read off
# delta_shift.grid" -- while asserting it nowhere, so a fixture shipped a tipping point of
# 1.25, which the locked grid cannot produce, beside a two-point grid array that did not
# contain it either.  `05_analysis_drd.py` returns a coordinate it read off this grid, so
# a value outside it is a payload this module must not print.
DELTA_SHIFT_GRID: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
DELTA_SHIFT_EXTENSION_STEP = 0.5
DELTA_SHIFT_EXTENSION_LAST = 4.0
DELTA_SHIFT_GRID_EXTENDED: tuple[float, ...] = DELTA_SHIFT_GRID + tuple(
    round(DELTA_SHIFT_GRID[-1] + DELTA_SHIFT_EXTENSION_STEP * (i + 1), 10)
    for i in range(int(round(
        (DELTA_SHIFT_EXTENSION_LAST - DELTA_SHIFT_GRID[-1]) / DELTA_SHIFT_EXTENSION_STEP)))
)


def _assert_delta_shift_grid(shift: Mapping[str, Any]) -> tuple[float, ...]:
    """Every delta the payload walked is one of 3.11's, and returns the ones it walked.

    THE GRID IS PRESPECIFIED AND THIS IS WHERE THAT BECOMES A REFUSAL.  3.11 fixes seven
    coordinates and one extension rule, and its last paragraph says why in terms: "Writing
    the extension rule down now is what stops it from being an extension invented later."
    A delta outside the locked set is exactly such an invention, whether it arrived as a
    finer grid somebody found more informative or as a value typed into a fixture.
    """
    permitted = (DELTA_SHIFT_GRID_EXTENDED if shift.get("grid_extended")
                 else DELTA_SHIFT_GRID)
    walked = tuple(sorted({float(point["delta"]) for point in shift.get("grid", ())}))
    stray = [d for d in walked
             if not any(math.isclose(d, p, abs_tol=1e-9) for p in permitted)]
    if stray:
        raise ExportError(
            f"debt.delta_shift.grid walks {stray}, which ANALYSIS-PLAN.md 3.11 does not "
            f"prespecify. The locked grid is {list(DELTA_SHIFT_GRID)} log-odds, extending "
            f"in {DELTA_SHIFT_EXTENSION_STEP} increments to {DELTA_SHIFT_EXTENSION_LAST} "
            f"and no further, and a delta outside it is an extension invented after the "
            f"lock rather than the one written down before it."
        )
    return walked


def _tipping_point_node(
    shift: Mapping[str, Any], key: str, log: SuppressionLog, path: str
) -> dict[str, Any]:
    """One delta-shift tipping point: a bound node, or the no-crossing node with no number.

    `crossed_within_grid` is false whenever the primary contrast holds its sign out to the
    end of the prespecified extension at delta 4.0, and that is the STRONGER result: no
    amount of unmeasured-day pessimism inside the prespecified range overturns the finding.
    It carries `no_crossing_within_range` (7.5's ninth) and not
    `not_estimable_data_unavailable`, which says the data were not there, and the data were
    there: the grid was walked, the extension was used, and the analysis returned an answer
    the vocabulary had no word for until contract 1.6.0.

    It is filed in `suppressed.entries` with `"rule": "no crossing"` so a consumer walking
    that block to find every node it cannot call `value()` on finds this one too, and so
    `n_entries` still ties out.  It is NOT a disclosure event and enters no R1 tally.
    """
    # EACH NODE IS DECIDED BY ITS OWN FLAG, not by one shared one, and 05 is why.
    # `05_analysis_drd.py` returns `crossed_within_grid` for the point estimate and
    # `interval_crossed_within_grid` for the interval, and says in terms that the second
    # "can fail to cross when the first one crossed".  The reverse also happens and does on
    # real data: a contrast whose point estimate never crosses inside the range can still
    # have its confidence band first include zero at some delta, which is a computed grid
    # coordinate and a reportable one.  3.5 used to suppress both nodes off the single flag,
    # which would have discarded that coordinate; contract 1.7.0 DECLARES
    # `debt.delta_shift.interval_crossed_within_grid` and says each node reads its own flag
    # alone, so the key is read outright rather than defaulted.  Falling back to
    # `crossed_within_grid` when it is absent would silently restore exactly the conflation
    # 1.7.0 removed, so an absent declared key is a refusal.
    flag_key = ("interval_crossed_within_grid" if key == "tipping_point_interval"
                else "crossed_within_grid")
    if flag_key not in shift:
        raise ExportError(
            f"debt.delta_shift is missing {flag_key!r}, which EXPORT-CONTRACT.md 3.5 "
            f"declares and which is the only flag this node may be decided on. Reading "
            f"the other node's flag instead is the conflation contract 1.7.0 removed."
        )
    crossed = bool(shift[flag_key])
    value = shift[key]
    if value is None or not crossed:
        if value is not None:
            raise ExportError(
                f"debt.delta_shift.{key} carries a coordinate while {flag_key} says the "
                f"curve did not cross. One of the two is wrong and this module will not "
                f"print a tipping point the analysis says does not exist."
            )
        log.add(locus="results.json", path=path, kind="estimate",
                reason="no_crossing_within_range", rule="no crossing")
        return suppressed_node("no_crossing_within_range")
    # A bound is one number.  A three-tuple here is the pre-1.6.0 estimate-node shape and
    # its `lo` and `hi` are a confidence interval that a grid coordinate does not have, so
    # only the point is read and the interval is refused rather than silently dropped.
    if isinstance(value, (list, tuple)):
        raise ExportError(
            f"debt.delta_shift.{key} arrived as a {len(value)}-tuple. Contract 1.6.0 makes "
            f"it a BOUND node: a tipping point is a grid coordinate read off "
            f"delta_shift.grid, so it has a point and no interval, and supplying an "
            f"interval would have a renderer draw a confidence band that does not exist."
        )
    # AND IT IS A COORDINATE THE GRID ACTUALLY HOLDS.  This module has said twice, in this
    # function and in `_render_debt`, that a tipping point is a grid coordinate and nothing
    # between the grid's values; until now it said so and checked neither half.  05 walks
    # the grid and reports the smallest delta at which a stated condition first holds, so it
    # can only ever return a value that is in `grid` and in 3.11's locked set -- which is
    # what makes a value outside them a payload defect rather than a finding, and what makes
    # printing it a Methods sentence about a shift the analysis never evaluated.
    coordinate = float(value)
    walked = _assert_delta_shift_grid(shift)
    if not any(math.isclose(coordinate, d, abs_tol=1e-9) for d in walked):
        raise ExportError(
            f"debt.delta_shift.{key} is {coordinate} and debt.delta_shift.grid walks "
            f"{list(walked)}. A tipping point is a GRID COORDINATE: the smallest delta at "
            f"which a stated condition first holds, so it is one of the deltas the curve "
            f"was evaluated at and never a value between two of them. This one names a "
            f"shift the analysis did not evaluate."
        )
    return bound_node(coordinate, "dimensionless")


MANSKI_COMPUTED_ON = "every eligible episode"


def _assert_manski_computed_on(supplied: Any) -> str:
    """Halt unless 05 computed the bounds on every eligible episode, as 3.5 requires.

    The bounds exist to say what the unobserved days could have been.  Computed on the
    complete windows only they answer a different question, and a much more reassuring one,
    while carrying a name that promises the first.  The string is the one thing that would
    say so, so it is compared rather than transcribed: an exporter that writes "every
    eligible episode" over a computation that was not is worse than no string at all.
    """
    if supplied is None:
        return MANSKI_COMPUTED_ON
    if str(supplied) != MANSKI_COMPUTED_ON:
        raise ExportError(
            f"debt.manski.computed_on is {supplied!r} and EXPORT-CONTRACT.md 3.5 requires "
            f"{MANSKI_COMPUTED_ON!r}. Bounds computed on the complete windows alone answer "
            f"a different and more reassuring question than the one this key names."
        )
    return MANSKI_COMPUTED_ON


# ======================================================================================
# STROBE ITEM 16(a), CONTRACT 1.9.0.  `debt.unadjusted_contrasts` and
# `debt.unadjusted_model`, rendered from the raw true values 05 hands over.
#
# NOTHING BREAKS BY ABSENCE, WHICH IS EXACTLY WHY BOTH KEYS ARE REQUIRED HERE.  This module
# reads the `debt` block by named key, so an 05 that has not been updated would have its two
# new keys silently dropped and the bundle would come out one reporting item short with
# nothing red anywhere: a partial adoption failing quietly is a worse failure mode than one
# failing loudly, and 11.4 registered this obligation precisely so it could not happen by
# omission.  Both keys are therefore asserted present rather than defaulted, and a missing
# one halts naming the section and the module that owes it.
#
# THE VALUES CROSS RAW AND ARE FLOOR-TESTED AND ROUNDED HERE, at the boundary, exactly as
# the adjusted contrasts are.  05's own words for the triple apply unchanged: non-finite
# members pass through rather than being repaired, and this is where they become a
# suppression rather than a NaN in the bundle.
# ======================================================================================

UNADJUSTED_REQUIRED_KEYS: tuple[str, ...] = ("unadjusted_contrasts", "unadjusted_model")

UNADJUSTED_MODEL_REQUIRED_KEYS: tuple[str, ...] = (
    "definition_display", "mandate_display", "prespecified", "rung_slug", "rung_display",
    "rung_index", "rung_matches_adjusted", "rung_note_display", "true_bootstrap_attempted",
    "true_bootstrap_failed", "not_estimable_reason",
)


def _assert_unadjusted_keys_present(debt: Mapping[str, Any]) -> None:
    """Halt on a `debt` block that predates contract 1.9.0, rather than dropping it."""
    missing = [key for key in UNADJUSTED_REQUIRED_KEYS if key not in debt]
    if missing:
        raise ExportError(
            f"the debt payload is missing {missing}, which EXPORT-CONTRACT.md 3.5 has "
            f"required since 1.9.0 for STROBE item 16(a). `05_analysis_drd.py` returns both "
            f"keys beside `contrasts`; a payload without them is an upstream module that has "
            f"not picked up the contract, and this module refuses rather than exporting a "
            f"bundle that is one reporting item short with nothing to show for it."
        )
    absent = [key for key in UNADJUSTED_MODEL_REQUIRED_KEYS
              if key not in debt["unadjusted_model"]]
    if absent:
        raise ExportError(
            f"debt.unadjusted_model is missing {absent}. EXPORT-CONTRACT.md 3.5 declares "
            f"every one of them, and `prespecified` above all: a Methods section that reads "
            f"a guideline-mandated estimand as a planned one has misreported the "
            f"prespecification, and the boolean beside the number is the only form of that "
            f"statement a consumer cannot lose in transcription."
        )


def _render_unadjusted_contrasts(
    debt: Mapping[str, Any],
    contrasts: Mapping[str, Any],
    log: SuppressionLog,
) -> dict[str, Any]:
    """`debt.unadjusted_contrasts`: the same five slugs, the same node builder, its own n.

    THE LABEL IS THE ADJUSTED CONTRAST'S OWN.  An unadjusted contrast is the same contrast,
    so it reuses the same 7.3 entry and 7.3 does not grow; five new slugs for what are not
    new contrasts is the mistake 3.5 argues Figure 3 block 1 out of.

    THE FAILURE NEVER PROPAGATES.  A guideline-mandated companion that could suppress or
    unseat the prespecified estimand beside it would be a worse defect than the gap it
    closes, so nothing here reaches `contrasts`: this function reads the adjusted block only
    to check that the two agree about which slugs exist and which one is primary.
    """
    _assert_unadjusted_keys_present(debt)
    supplied = debt["unadjusted_contrasts"]
    # An empty object is the legal shape for a fit that failed entirely (3.5), and the
    # footer's rows 13 and 15 then print `unadjusted_model.not_estimable_reason`'s sentence.
    # Anything else must be keyed exactly as `contrasts` is, because 3.5 fixes the slugs so a
    # consumer holding one can reach both estimates without a second vocabulary.
    if supplied and set(supplied) != set(contrasts):
        raise ExportError(
            f"debt.unadjusted_contrasts is keyed {sorted(supplied)} and debt.contrasts is "
            f"keyed {sorted(contrasts)}. EXPORT-CONTRACT.md 3.5 requires the same slugs and "
            f"no others: an unadjusted contrast is the same contrast, not a new one."
        )
    out: dict[str, Any] = {}
    for slug, spec in supplied.items():
        path = f"debt.unadjusted_contrasts.{slug}.estimate"
        true_n = spec["true_n_compared"]
        if not disclosable(true_n):
            # Its OWN n against the floor, never the adjusted contrast's: the unadjusted fit
            # runs on its own rows and 3.5 says nothing about this quantity is exempt.
            log.add(locus="results.json", path=path, kind="estimate",
                    reason="contributing_n_below_threshold",
                    rule="R1 contributing n below floor")
            estimate: dict[str, Any] = suppressed_node("contributing_n_below_threshold")
        else:
            # ITS OWN INTERVAL, from its own person-clustered bootstrap, never the adjusted
            # contrast's.  A refused interval beside a computed point estimate is a BOUND and
            # not a suppression, which is this module's rule for every estimate node and the
            # reason the pair can be read side by side: reporting the point as missing would
            # hide a number that exists.  A point that is not finite is the fit itself not
            # coming back, and 3.5 names `not_estimable_convergence` for it.
            estimate = estimate_from_triple(
                spec["estimate"], "activity_days", reason="not_estimable_convergence")
            if is_node_suppressed(estimate):
                # 3.9 fixes the five `rule` strings and none of them is a convergence
                # failure, which fires no disclosure rule at all.  The same mapping
                # `_log_if_suppressed` already applies to a node that arrived suppressed for
                # a reason outside the R1 ladder is applied here, so one bundle carries one
                # mapping rather than two that can differ.
                log.add(locus="results.json", path=path, kind="estimate",
                        reason=estimate["reason"], rule="R1 cell below floor")
        out[slug] = {
            "display_label": LABELS[slug],
            "estimate": estimate,
            "pvalue": pvalue_or_none(spec.get("p")),
            "is_primary": bool(spec["is_primary"]),
            "n_compared": count_node(
                true_n, log=log, path=f"debt.unadjusted_contrasts.{slug}.n_compared"),
        }
    if out:
        primary = [slug for slug, entry in out.items() if entry["is_primary"]]
        adjusted_primary = [slug for slug, entry in contrasts.items() if entry["is_primary"]]
        if primary != adjusted_primary:
            raise ExportError(
                f"debt.unadjusted_contrasts carries is_primary on {primary} and "
                f"debt.contrasts on {adjusted_primary}. 3.5 requires exactly one, and the "
                f"same slug in both: the two are one contrast estimated two ways."
            )
    return out


def _render_unadjusted_model(
    payload: Mapping[str, Any],
    debt: Mapping[str, Any],
    log: SuppressionLog,
) -> dict[str, Any]:
    """`debt.unadjusted_model`: what was removed, which rung it reached, what it lost.

    `prespecified` IS FALSE AND IS DECLARED, NEVER INFERRED.  `ANALYSIS-PLAN.md` is locked at
    1.5 and carries no unadjusted contrast for this arm anywhere: 4.8 prespecifies an
    unadjusted ASSOCIATION for the other arm, 9.2 an unadjusted LEVEL for this one, and
    section 6's `complete_window_direct_regression` row is a different estimator that is
    itself regressed on the covariate set.  Adding an estimand to a locked plan is an
    amendment and a re-lock under that file's section 13, so the quantity ships with the
    boolean beside it and 11.1 obliges `manuscript.py` to READ it rather than decide.  This
    module transcribes neither answer: it carries the boolean across unchanged.
    """
    _assert_unadjusted_keys_present(debt)
    model = debt["unadjusted_model"]
    index = model["rung_index"]
    slug = model["rung_slug"]
    if (index is None) != (slug is None):
        raise ExportError(
            f"debt.unadjusted_model carries rung_index {index!r} beside rung_slug {slug!r}. "
            f"3.5 makes both null together, when the fit returned no estimate, and both "
            f"present together otherwise."
        )
    if index is None:
        rung_display: Any = None
        matches: Any = None
        if model["rung_matches_adjusted"] is not None:
            raise ExportError(
                "debt.unadjusted_model.rung_matches_adjusted must be null when the "
                "unadjusted fit reached no rung; 3.5 declares it null in exactly that case."
            )
        if not model["not_estimable_reason"]:
            raise ExportError(
                "debt.unadjusted_model reached no rung and names no reason. 3.5 requires a "
                "slug of 7.5 whenever the fit did not come back, because the exporter prints "
                "that sentence where the estimate would sit."
            )
    else:
        expected = dict(ESTIMATOR_RUNGS).get(int(index))
        if expected is None or str(slug) != expected:
            raise ExportError(
                f"debt.unadjusted_model.rung_slug is {slug!r} at rung index {index!r}, which "
                f"3.1.1's ladder does not pair. The unadjusted fit walks the same ladder as "
                f"the adjusted one and reports where it landed."
            )
        # 7.7 sends the printed string to the label table, so the display is looked up rather
        # than transcribed from the payload, exactly as `meta.estimator.rung_display` is.
        rung_display = LABELS[expected]
        # `rung_matches_adjusted` is a REPORTABLE FACT and `false` is not a failure, so it is
        # checked against the adjusted rung rather than carried on trust.  This module is the
        # only one that sees `meta.estimator` and the debt block together, and two blocks
        # disagreeing about which rung the primary fit reached is not something either half
        # could catch alone.
        adjusted_index = int(payload["meta"]["estimator"]["rung_index"])
        matches = int(index) == adjusted_index
        if bool(model["rung_matches_adjusted"]) != matches:
            raise ExportError(
                f"debt.unadjusted_model.rung_matches_adjusted is "
                f"{model['rung_matches_adjusted']!r}, but the unadjusted fit reached rung "
                f"{int(index)} and meta.estimator.rung_index is {adjusted_index}. When the "
                f"two rungs differ the gap between the contrasts carries a change of model "
                f"family as well as of covariate set, so the flag is checked, not copied."
            )
    reason = model["not_estimable_reason"]
    if reason is not None:
        # A reason 7.5 does not own has nothing to print, and `_suppression_sentence` halts
        # by name on it.  Asked here so the halt names the key rather than the label table.
        _suppression_sentence(str(reason))
    return {
        "definition_display": model["definition_display"],
        "mandate_display": model["mandate_display"],
        # Carried across unchanged.  3.5: declared, never inferred.
        "prespecified": bool(model["prespecified"]),
        "rung_slug": None if slug is None else str(slug),
        "rung_display": rung_display,
        "rung_index": None if index is None else int(index),
        "rung_matches_adjusted": matches,
        "rung_note_display": model["rung_note_display"],
        # A PERCENTAGE NODE, built here from the two raw resample counts, the way
        # `meta.estimator.bootstrap_failure_rate` is already built and for the same reason
        # 3.5 gives: these are resample counts, not participant counts, so the shape is a
        # numerator over a denominator and never an estimate.  05's `instability_trigger`
        # travels beside them in the payload and is deliberately NOT emitted: 3.5 declares no
        # key for it, and the failure rate is the fact this block exports.
        "bootstrap_failure_rate": percentage_node(
            model["true_bootstrap_failed"], model["true_bootstrap_attempted"],
            log=log, path="debt.unadjusted_model.bootstrap_failure_rate"),
        "not_estimable_reason": None if reason is None else str(reason),
    }


def _render_debt(payload: Mapping[str, Any], log: SuppressionLog) -> dict[str, Any]:
    """The whole of Table 2 and Figure 3 block 1.

    `share_reaching_80pct_baseline` is an ESTIMATE node, not a percentage node: it is a
    fitted probability from a logistic g-computation, so it has a confidence interval and
    no numerator at all.  Treating it as n over N would invent a numerator that does not
    exist.  `share_zero_debt` beside it IS a percentage node, because it is an observed
    count over a denominator.  The two sit in the same row and are different shapes.

    EVERY COUNT COLUMN OF `by_group` IS BUILT FROM `DEBT_BY_GROUP_COUNT_COLUMNS`, which is
    also what `build_table2_frame` derives Table 2's row partitions from.  The two are one
    declaration on purpose: the group rows partition the pooled row in every count column at
    once, and a column that reaches the block by any other route would reach the page with
    no partition declared for it.  That is what happened to `n` and `n_complete_windows`.
    """
    debt = payload["debt"]
    entries = debt["by_group"]
    by_group: list[dict[str, Any]] = []
    zero_debt_true = [int(g["zero_debt_true_n"]) for g in entries]
    group_denominators = [int(g["true_n"]) for g in entries]
    # The per-group zero-debt counts partition the pooled one, so one suppressed member
    # forces a second.  THE MEMBERS COME FROM THE SAME DERIVATION Table 2's row partitions
    # do, rather than from a second hand-written copy of the rule sitting here: this used to
    # be the only place in the module that knew `debt.by_group` was a partition at all.
    # `share_zero_debt` is a PERCENTAGE and is protected by forcing a second suppression,
    # because a percentage this module can hide costs the reader one cell; the two count
    # columns are the study's own denominators and are protected by refusing the export
    # instead, because hiding a second group's episode count silently to protect the first
    # would leave the bundle's denominators disagreeing with themselves.
    member_indices = by_group_member_rows(entries, where="debt.by_group")
    hidden = [i for i in member_indices if not disclosable(zero_debt_true[i])]
    forced: set[int] = set()
    if len(hidden) == 1:
        candidates = sorted(
            (i for i in member_indices if i not in hidden), key=lambda i: zero_debt_true[i]
        )
        forced.add(candidates[0])

    for index, entry in enumerate(entries):
        path = f"debt.by_group[{index}]"
        record: dict[str, Any] = {"slug": entry["slug"]}
        for key, source, _column in DEBT_BY_GROUP_COUNT_COLUMNS:
            record[key] = count_node(entry[source], log=log, path=f"{path}.{key}")
        record.update({
            "unadjusted_debt": quantile_from_triple(
                entry["unadjusted_debt"], "activity_days"),
            "adjusted_debt": estimate_from_triple(
                entry["adjusted_debt"], "activity_days"),
            "thousand_steps_lost": estimate_from_triple(
                entry["thousand_steps_lost"], "thousand_steps"),
            "adjusted_mean_normalized_activity": estimate_from_triple(
                entry["adjusted_mean_normalized_activity"], "normalized_activity"),
            # An ESTIMATE node and not a percentage node: it is a fitted probability from a
            # logistic g-computation, so it has a confidence interval and no numerator at
            # all, and treating it as n over N would invent a numerator that does not exist.
            "share_reaching_80pct_baseline": estimate_from_triple(
                entry["share_reaching_80pct_baseline"], "percent", percent_sign=True),
            "share_zero_debt": percentage_node(
                zero_debt_true[index], group_denominators[index],
                log=log, path=f"{path}.share_zero_debt",
                force_suppress=index in forced),
        })
        by_group.append(record)

    contrasts: dict[str, Any] = {}
    for slug, spec in debt["contrasts"].items():
        contrasts[slug] = {
            "display_label": LABELS[slug],
            "estimate": estimate_from_triple(spec["estimate"], "activity_days"),
            "pvalue": pvalue_or_none(spec.get("p")),
            "is_primary": bool(spec["is_primary"]),
            "n_compared": count_node(
                spec["true_n_compared"], log=log, path=f"debt.contrasts.{slug}.n_compared"),
        }
    if sum(1 for c in contrasts.values() if c["is_primary"]) != 1:
        raise ExportError("exactly one contrast must carry is_primary")

    unadjusted = _render_unadjusted_contrasts(debt, contrasts, log)

    absolute: dict[str, Any] = {}
    for slug, spec in debt["absolute_scale"].items():
        absolute[slug] = {
            "display_label": LABELS[slug],
            "estimate": estimate_from_triple(spec["estimate"], "thousand_steps"),
            "pvalue": pvalue_or_none(spec.get("p")),
            "is_primary": False,
            "n_compared": count_node(
                spec["true_n_compared"], log=log,
                path=f"debt.absolute_scale.{slug}.n_compared"),
        }

    manski = debt["manski"]

    def _bound(value: Any) -> dict[str, Any]:
        if not _finite(value):
            return suppressed_node("not_estimable_data_unavailable")
        return bound_node(float(value), "activity_days")

    primary_bounds_known = (
        _finite(manski["primary_lower"]) and _finite(manski["primary_upper"]))
    manski_block = {
        "by_group": {
            slug: {"lower": _bound(lo), "upper": _bound(hi)}
            for slug, (lo, hi) in manski["by_group"].items()
        },
        "primary_contrast_lower": _bound(manski["primary_lower"]),
        "primary_contrast_upper": _bound(manski["primary_upper"]),
        # The footer sentence, or the 7.5 sentence where the bounds were not computed.  It
        # is a printed string either way, because 5.3 row 9 has no not-applicable form: an
        # empty footer cell reads as "does not apply" and this file has no such row.
        "display": (
            f"{_fmt(_round_to_unit(manski['primary_lower'], 'activity_days'), 'activity_days')}"
            f" to "
            f"{_fmt(_round_to_unit(manski['primary_upper'], 'activity_days'), 'activity_days')}"
            f" activity days"
        ) if primary_bounds_known else LABELS["not_estimable_data_unavailable"],
        "crosses_zero": bool(
            primary_bounds_known
            and manski["primary_lower"] <= 0 <= manski["primary_upper"]),
        # Never "complete windows only": the bounds exist precisely to say what the
        # missing days could have been, so computing them on the complete windows would
        # answer a different question and a reassuring one.  05 returns the same string and
        # says why the two exist: "The exporter asserts the same string independently, and
        # the two exist so they can be compared."  So they are compared, here, rather than
        # this module transcribing a claim about how an upstream computation was done.
        "computed_on": _assert_manski_computed_on(manski.get("computed_on")),
    }

    shift = debt["delta_shift"]
    fit = debt["model_fit"]
    return {
        "estimand": {
            "display": debt["estimand_display"],
            "unit": "activity_days",
            "max_possible": scalar_node(debt["max_possible"]),
            "estimator": "model and integrate",
        },
        "by_group": by_group,
        "contrasts": contrasts,
        # STROBE ITEM 16(a), added at contract 1.9.0.  The same five slugs as `contrasts`,
        # so a consumer holding a contrast slug reaches both estimates without a second
        # vocabulary, and `absolute_scale` deliberately has NO unadjusted twin: 3.5 says why,
        # and it is the definition rather than the effort.  The absolute-scale companion's
        # model is required by ANALYSIS-PLAN.md 3.9 to carry a spline in log baseline steps,
        # so a covariate-free version of it would still have to carry a covariate and would
        # not be "the same estimator with the covariate set removed" but a third thing with
        # no clean description.  Item 16(a) is answered on the scale the estimand is defined
        # on, which is `activity_days`.  The absence is a decision and not an oversight.
        "unadjusted_contrasts": unadjusted,
        "unadjusted_model": _render_unadjusted_model(payload, debt, log),
        "absolute_scale": absolute,
        "manski": manski_block,
        "delta_shift": {
            # The shift is on the model's own LATENT LOGIT scale, in log-odds, not on the
            # normalized-activity scale.  A renderer that plots it beside an activity-day
            # contrast asserts a comparison that does not exist, which is why 4.3 gives the
            # row `render = panel` and its own axis.
            "scale": "latent logit",
            "applied_to": shift["applied_to"],
            # BOUND NODES, not estimate nodes.  A tipping point is a GRID COORDINATE: the
            # smallest `delta` in `delta_shift.grid` at which a stated condition first
            # holds, so it takes one of the prespecified grid values and nothing between
            # them and nothing around them.  Giving it `lo` and `hi` that differ from `est`
            # invites a renderer to draw a confidence interval that does not exist, and the
            # second node's name says `interval` because the condition it reads off the
            # grid is about the CONTRAST's interval, not its own.  The two sit one row
            # apart in the Table 2 footer, which is where a reader is most likely to
            # conflate them.
            "tipping_point_point_estimate": _tipping_point_node(
                shift, "tipping_point_point_estimate", log,
                "debt.delta_shift.tipping_point_point_estimate"),
            "tipping_point_interval": _tipping_point_node(
                shift, "tipping_point_interval", log,
                "debt.delta_shift.tipping_point_interval"),
            "definition_display": shift["definition_display"],
            "applications": list(shift["applications"]),
            "grid": [dict(point) for point in shift["grid"]],
            "reference_deficit": scalar_node(
                shift["reference_deficit"],
                _fmt(shift["reference_deficit"], "normalized_activity")),
            "grid_extended": bool(shift["grid_extended"]),
            # TWO FLAGS, ONE PER NODE, both declared by 3.5 as of contract 1.7.0.  The
            # first is the point estimate's and its alone; the second is the interval's and
            # its alone, and either may be false while the other is true.  Writing only the
            # first would leave a consumer to infer the interval node's suppression from a
            # flag that does not answer for it.
            "crossed_within_grid": bool(shift["crossed_within_grid"]),
            "interval_crossed_within_grid": bool(shift["interval_crossed_within_grid"]),
            "no_crossing_display": shift["no_crossing_display"],
        },
        "model_fit": {
            "family": fit["family"],
            "link": fit["link"],
            "spline_basis": fit["spline_basis"],
            "spline_df": scalar_node(fit["spline_df"]),
            # THE RUNG THE DESCENT ACTUALLY REACHED, read from the fit and validated
            # against ANALYSIS-PLAN.md 3.4's three-rung vocabulary.  An index-lagged AR(1)
            # is wrong with irregular missing days and missing days are the whole subject
            # of this study, which is why rung 1 is the continuous-time analogue; but rung
            # 1 is where the descent STARTS, not where it necessarily lands, and a bundle
            # that names a structure the fit did not use is a Methods claim nobody made.
            "residual_correlation": residual_correlation_display(fit),
            "rho": estimate_from_triple(fit["rho"], "dimensionless"),
            "icc": estimate_from_triple(fit["icc"], "dimensionless"),
            "marginal_r2": estimate_from_triple(fit["marginal_r2"], "dimensionless"),
            "conditional_r2": estimate_from_triple(fit["conditional_r2"], "dimensionless"),
            # The fractional-response rung reports no information criterion at all, so a run
            # that descends to it hands over a non-finite value and this is where that
            # becomes a printed sentence rather than a NaN in the bundle.
            "aic": scalar_or_suppressed(
                fit["aic"],
                f"{int(fit['aic']):,}" if _finite(fit["aic"]) else None),
            "n_person_days": count_node(
                fit["true_n_person_days"], log=log, path="debt.model_fit.n_person_days"),
            "n_persons": count_node(
                fit["true_n_persons"], log=log, path="debt.model_fit.n_persons"),
            "converged": bool(fit["converged"]),
            # Random effects are marginalized by Monte Carlo, never set to zero, because
            # the deficit function is convex and a zero random effect is not the average.
            "monte_carlo_draws": scalar_node(fit["monte_carlo_draws"]),
        },
    }


def _render_sensitivity(payload: Mapping[str, Any], log: SuppressionLog) -> dict[str, Any]:
    """One entry per prespecified robustness row.  Fourteen plotted rows from ten ladder rows.

    Key order in the file is alphabetical because of `sort_keys`; LADDER ORDER is carried by
    `order` and `sub_order`, so the plan's fixed order survives the expansion of row 6 into
    four wear definitions and row 7 into two baseline windows and cannot be rearranged to
    put a reassuring row at the top.
    """
    out: dict[str, Any] = {}
    supplied = payload["sensitivity"]
    for order, sub_order, slug, axis, render in SENSITIVITY_ROWS:
        spec = supplied[slug]
        unit = spec.get("unit", "activity_days")
        estimable = bool(spec["estimable"])
        out[slug] = {
            "order": order,
            "sub_order": sub_order,
            "display_label": LABELS[slug],
            "estimate": (
                _sensitivity_estimate_node(slug, spec["estimate"], unit) if estimable
                else suppressed_node(spec["not_estimable_reason"])
            ),
            "pvalue": pvalue_or_none(spec.get("p")),
            "n": count_node(spec["true_n"], log=log, path=f"sensitivity.{slug}.n"),
            "estimable": estimable,
            "not_estimable_reason": None if estimable else spec["not_estimable_reason"],
            "axis": axis,
            "render": render,
            "varies": spec["varies"],
            "direction_matches_primary": bool(spec["direction_matches_primary"]),
        }
    return out


def _sensitivity_estimate_node(slug: str, estimate: Any, unit: str) -> dict[str, Any]:
    """A sensitivity row's estimate: an interval, or a bound where the row carries a bound."""
    if slug in BOUND_SENSITIVITY_ROWS:
        point = estimate[0] if isinstance(estimate, (list, tuple)) else estimate
        if not _finite(point):
            return suppressed_node("not_estimable_data_unavailable")
        return bound_node(float(point), unit)
    return estimate_from_triple(estimate, unit)


def _assert_gate_ledger_monotone(stages: Sequence[Mapping[str, Any]]) -> None:
    """The A-through-F ledger is monotone non-increasing, asserted rather than assumed.

    EACH STAGE IS A SUBSET OF THE ONE ABOVE IT, by the definitions 7.9 transcribes.  B is
    the episodes of A that also clear the baseline-wear rule, C is the episodes of B that
    also have a computable post-discharge window, E is the events of D that also have a
    computable proximal ratio, and F is those events again by stratum.  A ledger whose
    stage B stands above its stage A is not a tight ledger, it is a ledger that cannot be
    read: the reader has no way to know which of the two numbers the study actually had,
    and the gate tier is decided off stage E at the bottom of the chain.

    THE UNIT CHANGES ONCE, AT D, AND THE LEDGER STILL DOES NOT RISE.  A through C count
    episodes and D through F count events, but the events D counts are FIRST events, at
    most one per episode -- which is the same fact the attrition ladder states at rung 17,
    where 340 episodes convert to 40 events.  So the comparison across the conversion is
    meaningful in the one direction this check tests, and a D above C would say some
    episode contributed two first events.

    A suppressed total is skipped and the comparison is carried across it to the next
    disclosed stage, which is still bounded by the last disclosed one.  Rounding cannot
    manufacture a violation: `round20` is monotone, so a true ledger that does not rise
    cannot round into one that does.
    """
    previous_letter = ""
    previous: int | None = None
    for stage in stages:
        node = stage["total"]
        if is_node_suppressed(node):
            continue
        current = int(node["n"])
        if previous is not None and current > previous:
            raise ExportError(
                f"the feasibility gate ledger rises: stage {stage['letter']} is "
                f"{current:,} and stage {previous_letter} above it is {previous:,}. Each "
                f"stage of 7.9 is a subset of the one above it, so a ledger that grows is "
                f"two different cohorts written in one column and there is no reading of "
                f"it that makes Table 3 part A true. Halting rather than reordering."
            )
        previous, previous_letter = current, stage["letter"]


def _render_gate(payload: Mapping[str, Any], log: SuppressionLog) -> dict[str, Any]:
    """The A-through-F ledger, the tier, and the verbatim permitted claim.

    NOT PERMITTED IS NOT THE SAME AS SUPPRESSED.  A key absent because the tier forbids the
    analysis is recorded in `arm_a.permitted: false` with a printed reason; a key present
    but hidden for cell size is recorded in `suppressed`.  Both print.  Neither vanishes.
    """
    gate = payload["gate"]
    if not isinstance(gate["stages"], Mapping):
        # `06_analysis_gate.py` already builds this block in the contract's own shape:
        # `gate_stages()` returns the six stage records with `total` as a count node, and
        # `build_gate_block()` adds the tier and `arm_a`.  It applies the floor to the true
        # counts where the true counts still exist, which is the correct moment, so
        # re-deriving them here would need 06 to hand back raw counts it has already and
        # correctly consumed.  This branch adopts that block, VALIDATES it against the
        # contract's own vocabularies, and folds its suppressed nodes into the suppression
        # ledger, which is the one thing 06 cannot do because the ledger spans blocks.
        adopted = _adopt_rendered_gate(gate, log)
        # Asserted on BOTH paths.  A ledger arriving already rendered from 06 is exactly the
        # one this module has no other view of, so a check that ran only on the raw-count
        # path would be off for every real Phase 4 run and on only for the fixture.
        _assert_gate_ledger_monotone(adopted["stages"])
        return adopted
    stages: list[dict[str, Any]] = []
    for index, (letter, slug, definition, unit) in enumerate(GATE_STAGES):
        spec = gate["stages"][letter]
        path = f"gate.stages[{index}]"
        by_group = None
        if spec.get("by_group") is not None:
            by_group = {
                group_slug: count_node(
                    true_n, log=log, path=f"{path}.by_group.{group_slug}")
                for group_slug, true_n in spec["by_group"].items()
            }
        components = None
        if spec.get("components") is not None:
            true_components = spec["components"]
            parts = [key for key, _label in GATE_STAGE_D_COMPONENT_LABELS
                     if key != "composite"]
            hidden = [k for k in parts if not disclosable(true_components[k])]
            forced = set()
            if len(hidden) == 1:
                forced = {k for k in parts if k not in hidden}
            components = {
                key: count_node(
                    true_components[key], log=log, path=f"{path}.components.{key}",
                    force_suppress=key in forced)
                for key, _label in GATE_STAGE_D_COMPONENT_LABELS
            }
        stages.append({
            "letter": letter,
            "slug": slug,
            "display_label": LABELS[slug],
            "definition_display": definition,
            "unit": unit,
            "total": count_node(spec["total"], log=log, path=f"{path}.total"),
            "by_group": by_group,
            "components": components,
        })
    _assert_gate_ledger_monotone(stages)

    deciding = int(gate["stages"]["E"]["total"])
    index, slug, lower, upper, analysis, claim = _tier_for(deciding)
    tier = {
        "index": index,
        "slug": slug,
        "display_label": LABELS[slug],
        "events_lower": lower,
        "events_upper": upper,
        "determined_by": "stage E",
        # The lowest tier's boundary and the disclosure floor are the same NUMBER from
        # unrelated origins, so this is false whenever the deciding count is not
        # disclosable, and it is NOT a synonym for the lowest tier.
        "event_count_printable": bool(disclosable(deciding)),
        "permitted_analysis_verbatim": analysis,
        "permitted_claim_verbatim": claim,
        "exhibit_set": "primary" if index >= 3 else "alternate",
    }
    if tier["exhibit_set"] != "primary":
        raise ExportError(
            "the feasibility gate reached a tier that replaces the whole exhibit set "
            "(ANALYSIS-PLAN.md 9.5). This contract specifies the primary set only, so the "
            "contract is amended before the export runs. Refusing to emit the primary "
            "column set with alternate content."
        )
    permitted = bool(gate["arm_a"]["permitted"])
    return {
        "stages": stages,
        "tier": tier,
        "arm_a": {
            "permitted": permitted,
            "reason_display": gate["arm_a"]["reason_display"],
            "estimates": gate["arm_a"]["estimates"] if permitted else {},
        },
    }


def _adopt_rendered_gate(gate: Mapping[str, Any], log: SuppressionLog) -> dict[str, Any]:
    """Adopt the finished gate block from `06_analysis_gate.py`, checked rather than trusted."""
    stages = [dict(stage) for stage in gate["stages"]]
    if len(stages) != len(GATE_STAGES):
        raise ExportError("the gate block does not carry the six A-through-F stages")
    for stage, (letter, slug, definition, unit) in zip(stages, GATE_STAGES):
        if (stage["letter"], stage["slug"], stage["unit"]) != (letter, slug, unit):
            raise ExportError(f"gate stage {stage.get('letter')!r} does not match 7.9")
        if stage["display_label"] != LABELS[slug] or stage["definition_display"] != definition:
            raise ExportError(
                f"gate stage {letter} carries a printed string that is not the contract's"
            )
    tier = dict(gate["tier"])
    known = {index: slug for index, slug, *_rest in TIERS}
    if known.get(int(tier["index"])) != tier["slug"]:
        raise ExportError("gate.tier.index and gate.tier.slug disagree with 7.10")
    if tier["display_label"] != LABELS[tier["slug"]]:
        raise ExportError("gate.tier.display_label is not the contract's label")
    if tier["exhibit_set"] != "primary":
        raise ExportError(
            "the feasibility gate reached a tier that replaces the whole exhibit set "
            "(ANALYSIS-PLAN.md 9.5). This contract specifies the primary set only, so the "
            "contract is amended before the export runs. Refusing to emit the primary "
            "column set with alternate content."
        )
    for index, stage in enumerate(stages):
        path = f"gate.stages[{index}]"
        for label, node in [("total", stage["total"])]:
            _log_if_suppressed(log, node, f"{path}.{label}")
        for group_slug, node in (stage["by_group"] or {}).items():
            _log_if_suppressed(log, node, f"{path}.by_group.{group_slug}")
        for key, node in (stage["components"] or {}).items():
            _log_if_suppressed(log, node, f"{path}.components.{key}")
    for key, node in (gate["arm_a"].get("estimates") or {}).items():
        _log_if_suppressed(log, node, f"gate.arm_a.estimates.{key}")
    return {
        "stages": stages,
        "tier": tier,
        "arm_a": {
            "permitted": bool(gate["arm_a"]["permitted"]),
            "reason_display": gate["arm_a"]["reason_display"],
            "estimates": dict(gate["arm_a"].get("estimates") or {}),
        },
    }


def _log_if_suppressed(log: SuppressionLog, node: Any, path: str) -> None:
    """Record an already-rendered suppressed node in the ledger of section 3.9.

    A suppressed value is never silently omitted, and a node that arrived already
    suppressed from another module is exactly the one at risk of being: the module that
    hid it has no view of the ledger, and the module that owns the ledger did not hide it.
    """
    if not is_node_suppressed(node):
        return
    reason = node["reason"]
    rule = ("R1 secondary suppression" if reason == "secondary_suppression"
            else "tier" if reason == "not_permitted_by_tier"
            else "R1 cell below floor")
    kind = "estimate" if "estimates." in path else "count"
    log.add(locus="results.json", path=path, kind=kind, reason=reason, rule=rule)


def _tier_for(n_events: int) -> tuple[int, str, Any, Any, str, str]:
    """The tier the deciding count lands in, read off 7.10's bands rather than compared to a
    literal.  The bands are inclusive and are searched from the top."""
    for index, slug, lower, upper, analysis, claim in TIERS:
        low_ok = lower is None or n_events >= lower
        high_ok = upper is None or n_events <= upper
        if low_ok and high_ok:
            return index, slug, lower, upper, analysis, claim
    raise ExportError("no feasibility tier covers the deciding event count")


FIGURE_COLUMNS: dict[str, tuple[str, ...]] = {
    "figure1": (
        "step", "slug", "display_label", "kind", "unit", "n_in", "n_dropped", "n_out",
        "n_carried_forward", "reason", "reason_display", "closes_exact", "box_side",
    ),
    "figure2": (
        "group_slug", "display_label", "group_order", "day", "n_contributing",
        "observed_median", "observed_p25", "observed_p75",
        "fitted_marginal", "fitted_lo", "fitted_hi", "in_accrual_window", "series_segment",
    ),
    "figure3": (
        "block", "block_label", "row_order", "slug", "display_label", "estimate",
        "ci_lo", "ci_hi", "unit", "axis", "render", "n", "estimable",
        "not_estimable_display", "is_primary", "reference_value",
    ),
    "figure4": (
        "series_slug", "display_label", "series_order", "day_relative_to_event",
        "n_contributing", "observed_median", "observed_p25", "observed_p75",
        "plotted", "not_plotted_display",
    ),
}

FIGURE_SORT_KEYS: dict[str, tuple[str, ...]] = {
    "figure1": ("step",),
    "figure2": ("group_order", "day"),
    "figure3": ("block", "row_order"),
    "figure4": ("series_order", "day_relative_to_event"),
}


def _render_figures(
    payload: Mapping[str, Any],
    results: Mapping[str, Any],
    frames: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    """One manifest entry per plot-ready CSV.  md5 and rows are filled in after the write."""
    analytic = results["denominators"]["analytic"]["n"]
    curve_members = results["denominators"]["event_centered_members"]["n"]
    figure2 = payload["figure2_summary"]
    figure4 = payload["figure4_summary"]
    blocks = payload["figure3_blocks"]
    tier_permits_plot = bool(figure4["tier_permits_plot"])
    # The tier decides whether an event-centered query was submitted at all, so a Figure 4
    # that says it plotted something while `arm_a.permitted` is false is two modules
    # disagreeing about which analysis ran.  Checked rather than trusted, because the file
    # is written either way and the disagreement would be invisible in either half alone.
    if tier_permits_plot != bool(results["gate"]["arm_a"]["permitted"]):
        raise ExportError(
            f"figures.figure4.tier_permits_plot is {tier_permits_plot} and "
            f"gate.arm_a.permitted is {results['gate']['arm_a']['permitted']}. The tier "
            f"decides whether any event-centered query was submitted, so the two are one "
            f"fact and cannot disagree."
        )
    # The curve's own denominator and the tier are one fact too.  At a tier that permits no
    # early-warning analysis no event-centered query is submitted, so no risk-set member is
    # drawn and the honest count is a true zero; at a permitting tier the curve is drawn
    # over somebody.  Without this the denominator is the one field that could go stale
    # while every row of the file said the right thing.
    if tier_permits_plot == (curve_members == 0):
        raise ExportError(
            f"figures.figure4.tier_permits_plot is {tier_permits_plot} and the "
            f"event-centered curve's denominator is {curve_members} risk-set members. A "
            f"tier that permits no early-warning analysis submits no event-centered query "
            f"and draws nobody; a permitting tier draws somebody."
        )
    return {
        "figure1": {
            "file": "figures-csv/figure1_strobe_ladder.csv",
            "exhibit": "Figure 1",
            "exhibit_set": "primary",
            "columns": list(FIGURE_COLUMNS["figure1"]),
            "sort_keys": list(FIGURE_SORT_KEYS["figure1"]),
            "rows": 0,
            "md5": "",
            "denominator": "analytic",
            "n": analytic,
            "legend": (
                "Figure 1. Participant flow. Counts are rounded to the nearest 20 in "
                "accordance with the All of Us dissemination policy, so the boxes may not "
                "sum exactly."
            ),
            "plate_note": f"Analytic cohort n = {analytic:,} episodes.",
        },
        "figure2": {
            "file": "figures-csv/figure2_daily_activity.csv",
            "exhibit": "Figure 2",
            "exhibit_set": "primary",
            "columns": list(FIGURE_COLUMNS["figure2"]),
            "sort_keys": list(FIGURE_SORT_KEYS["figure2"]),
            "rows": 0,
            "md5": "",
            "denominator": "analytic",
            "n": analytic,
            "legend": (
                "Figure 2. Baseline-normalized daily activity by post-discharge day. Days "
                "on which a group had 20 or fewer contributors are not plotted, so a line "
                "and its ribbon end where the data end."
            ),
            # The plate note states the truncation RULE and the fact that days are missing.
            # It does not list the dropped days one at a time, and the reason is length
            # rather than disclosure: up to ninety integers per series is not caption
            # content, and the surviving set is the file's own `day` column anyway.
            "plate_note": (
                f"Analytic cohort n = {analytic:,} episodes. Days with 20 or fewer "
                f"contributors are not plotted."
            ),
            "days_dropped_by_group": dict(figure2["days_dropped_by_group"]),
            "last_day_by_group": dict(figure2["last_day_by_group"]),
            "n_gaps_by_group": dict(figure2["n_gaps_by_group"]),
            "n_series": int(figure2["n_series"]),
        },
        "figure3": {
            "file": "figures-csv/figure3_forest.csv",
            "exhibit": "Figure 3",
            "exhibit_set": "primary",
            "columns": list(FIGURE_COLUMNS["figure3"]),
            "sort_keys": list(FIGURE_SORT_KEYS["figure3"]),
            "rows": 0,
            "md5": "",
            "denominator": "analytic",
            "n": analytic,
            "legend": (
                "Figure 3. Recovery debt contrasts and robustness. A subgroup below the "
                "disclosure floor prints as not estimable rather than being omitted."
            ),
            "plate_note": f"Analytic cohort n = {analytic:,} episodes.",
            "blocks": [dict(block) for block in blocks],
        },
        "figure4": {
            "file": "figures-csv/figure4_event_centered_activity.csv",
            "exhibit": "Figure 4",
            "exhibit_set": "supplementary",
            "columns": list(FIGURE_COLUMNS["figure4"]),
            "sort_keys": list(FIGURE_SORT_KEYS["figure4"]),
            "rows": 0,
            "md5": "",
            # 3.2's `event_centered_members`, NOT `events_composite`.  The composite
            # first-event count is not the population this curve is drawn over: the curve
            # is drawn over risk-set members and carries the same structural filter the
            # fits carry, so the two differ by exactly the members that filter removes,
            # and pointing the plate note at the composite count printed a number larger
            # than the curve's own.  Being supplementary does not excuse it from carrying
            # a denominator.  A supplementary exhibit is still a PRINTED exhibit, and
            # CLAUDE.md section 2 rule 5 makes every printed figure carry its own; the
            # supplement changes where an exhibit is printed, not whether it prints one.
            "denominator": "event_centered_members",
            "n": curve_members,
            "legend": (
                "Figure 4. Normalized daily activity centred on the acute-care event, for "
                "cases and their post-discharge-day matched controls."
                + ("" if tier_permits_plot else
                   " The feasibility tier reached permits no early-warning analysis, so no "
                   "offset is plotted.")
            ),
            "plate_note": (
                f"Event-centered curve n = {curve_members:,} risk-set members."
                + ("" if tier_permits_plot else
                   " No offset is plotted at the feasibility tier reached.")
            ),
            "n_series": len(FIGURE4_SERIES),
            # Carried so a renderer fixes its axis before it reads a row.  It is a pair of
            # OFFSETS from the event date, not a pair of days from an anchor in anybody's
            # calendar, which is why it is a constant of the specification and not data.
            "day_range": [FIGURE4_FIRST_OFFSET, FIGURE4_LAST_OFFSET],
            "n_days_plotted_by_series": dict(figure4["n_days_plotted_by_series"]),
            # NOT PERMITTED IS NOT SUPPRESSED.  3.7 and 3.9 keep them apart: a tier-driven
            # absence is recorded where the tier is recorded, with a printed reason, and
            # never as an entry in `results.json.suppressed`.  MANIFEST.csv still counts the
            # written tokens in `n_suppressed_cells`, which counts tokens and not reasons.
            "tier_permits_plot": tier_permits_plot,
        },
    }


def _render_tables(
    results: Mapping[str, Any],
    frames: Mapping[str, pd.DataFrame],
) -> dict[str, Any]:
    """Five keys, six files.  The Table 2 footer is a file, not an exhibit, so it has no key
    here and is reached through `tables.table2.footer_file`; it still gets its own manifest
    row and its own md5."""
    analytic = results["denominators"]["analytic"]["n"]
    events = results["denominators"]["events_composite"]["n"]
    person_days = results["denominators"]["analytic_person_days"]["n"]
    return {
        "table1": {
            "file": "tables-csv/table1_cohort_characteristics.csv",
            "exhibit": "Table 1",
            "exhibit_set": "primary",
            "columns": list(frames["tables-csv/table1_cohort_characteristics.csv"].columns),
            "key_columns": ["Characteristic", "Level"],
            "rows": 0,
            "denominator": "analytic",
            "n": analytic,
            "md5": "",
            "legend": (
                "Table 1. Cohort characteristics and wearable data availability by "
                "procedure group. Percentages are computed from the rounded numerator over "
                "the rounded denominator and printed to zero decimals."
            ),
            "footer_file": None,
        },
        "table2": {
            "file": "tables-csv/table2_adjusted_debt.csv",
            "exhibit": "Table 2",
            "exhibit_set": "primary",
            "columns": list(frames["tables-csv/table2_adjusted_debt.csv"].columns),
            "key_columns": ["Procedure group"],
            "rows": 0,
            "denominator": "analytic",
            "n": analytic,
            "md5": "",
            "legend": (
                "Table 2. Adjusted digital recovery debt by procedure group, in "
                "baseline-equivalent activity days lost across post-discharge day 1–35."
            ),
            "footer_file": "tables-csv/table2_adjusted_debt_footer.csv",
        },
        "table3a": {
            "file": "tables-csv/table3_gate_part_a.csv",
            "exhibit": "Table 3",
            "exhibit_set": "primary",
            "columns": list(frames["tables-csv/table3_gate_part_a.csv"].columns),
            "key_columns": ["Stage"],
            "rows": 0,
            "denominator": "events_composite",
            "n": events,
            "md5": "",
            "legend": (
                "Table 3, part A. Feasibility gate ledger. The deciding count at stage E "
                "is below the disclosure floor and is therefore not printable."
            ),
            "footer_file": None,
        },
        "table3b": {
            "file": "tables-csv/table3_gate_part_b.csv",
            "exhibit": "Table 3",
            "exhibit_set": "primary",
            "columns": list(frames["tables-csv/table3_gate_part_b.csv"].columns),
            "key_columns": ["Quantity"],
            "rows": 0,
            "denominator": "events_composite",
            "n": events,
            "md5": "",
            "legend": "Table 3, part B. The analysis the feasibility tier permits.",
            "footer_file": None,
        },
        "table4": {
            "file": "tables-csv/table4_collider_comparison.csv",
            "exhibit": "Table 4",
            "exhibit_set": "supplementary",
            "columns": list(frames["tables-csv/table4_collider_comparison.csv"].columns),
            "key_columns": ["Window group"],
            "rows": 0,
            "denominator": "analytic_person_days",
            "n": person_days,
            "md5": "",
            # The legend is where the wording obligation of ANALYSIS-PLAN.md 4.4 lives,
            # because the legend is a printed string the contract owns.  Neither rate is a
            # causal estimate and the table says so rather than leaving a reader to infer it.
            "legend": (
                "Table 4. Acute-care event rate on episode-days with and without a "
                "computable step signal, crude and standardized to the recovery day bands. "
                "The comparison is unmatched and descriptive: post-discharge day drives "
                "both wear and events, and the two versions are reported so that a reader "
                "who finds them different is shown by how much rather than told which to "
                "believe. Neither version is a causal estimate."
            ),
            "footer_file": None,
        },
    }


def _render_checks() -> dict[str, Any]:
    """Thirteen checks.  A run that reports fewer has skipped one, and `n_checks` says so.

    Every entry starts passed, because every one of them is enforced by a stop condition
    earlier in this module: a failure raises there rather than being written here as a
    false.  The one exception is the two-run byte comparison, which cannot be known until
    both writes have happened and is filled in by `export_bundle`.
    """
    entries = [
        {
            "slug": slug,
            "display": CHECK_DISPLAY[slug],
            "passed": True,
            "detail": "",
            "local_reassert": slug in CHECKS_LOCAL_REASSERT,
        }
        for slug in CHECK_SLUGS
    ]
    return {
        "entries": entries,
        "n_checks": len(entries),
        "n_passed": len(entries),
        "n_failed": 0,
        "policy": "any failed check is a stop condition, not a warning",
    }


def render_bundle(
    payload: Mapping[str, Any],
) -> tuple[dict[str, Any], list[tuple[str, pd.DataFrame, dict[str, Any]]], SuppressionLog]:
    """Turn true counts into the results object and the fifteen frames.  Writes nothing.

    THE FIRST THING IT DOES IS ASK THE THREE UPSTREAM MODULES WHETHER THEY CERTIFIED THEIR
    OWN OUTPUT, and it does that before a single node is built.  A refusal from 04, 05 or 06
    is a refusal here: 06's reconciliation failure sets `gate ok` false over the very count
    that decides the tier, and 04's `features ok` means, in its author's words, that the
    analysis modules must not run.  Rendering first and checking later would put a bundle in
    memory that must not exist, and the only reason it would not be written is that
    somebody remembered to look.
    """
    # The return value is deliberately dropped.  The certification is a GATE and not a
    # bundle field: 3.1 fixes the keys of `meta` and this module does not get to add one to
    # it, because a key `verify.py` has no entry for is a key the contract has to grow
    # before it can be checked.  What the bundle carries is the consequence, which is that
    # it exists at all.
    assert_upstream_certifications(payload.get("certifications"))
    log = SuppressionLog()
    results: dict[str, Any] = {}
    results["meta"] = _render_meta(payload)
    results["denominators"] = _render_denominators(payload, log)
    results["attrition"] = _render_attrition(payload, log)
    results["cohort"] = _render_cohort(payload, log)
    results["debt"] = _render_debt(payload, log)
    results["sensitivity"] = _render_sensitivity(payload, log)
    results["gate"] = _render_gate(payload, log)
    results["checks"] = _render_checks()

    # A denominator and the ladder box carrying the same quantity must carry the same
    # number.  Checked here rather than trusted, because the two are computed by different
    # queries and a drift between them is invisible in either one alone.
    rung_by_step = {r["step"]: r for r in results["attrition"]["rungs"]}
    for key, spec in payload["denominators"].items():
        rung = spec.get("rung")
        if rung is None:
            continue
        step, field = rung
        node = rung_by_step[step][field]
        if is_node_suppressed(node) or int(node["n"]) != results["denominators"][key]["n"]:
            raise ExportError(
                f"denominator {key!r} and ladder step {step} {field} disagree after "
                f"rounding, and they are the same quantity"
            )

    frames: dict[str, pd.DataFrame] = {}
    declarations: dict[str, dict[str, Any]] = {}

    def stage(relative_path: str, built: tuple[pd.DataFrame, Mapping[str, Any]]) -> None:
        frame, decl = built
        frames[relative_path] = frame
        declarations[relative_path] = dict(decl)

    stage("figures-csv/figure1_strobe_ladder.csv", build_figure1_frame(results))
    stage("figures-csv/figure2_daily_activity.csv",
          build_figure2_frame(payload["figure2_rows"]))
    stage("figures-csv/figure3_forest.csv", build_figure3_frame(payload["forest_rows"]))
    stage("figures-csv/figure4_event_centered_activity.csv",
          build_figure4_frame(payload["figure4_rows"]))
    stage("tables-csv/table1_cohort_characteristics.csv",
          build_table1_frame(results, payload["table1_rows"]))
    stage("tables-csv/table2_adjusted_debt.csv", build_table2_frame(results))
    stage("tables-csv/table2_adjusted_debt_footer.csv", build_table2_footer_frame(results))
    stage("tables-csv/table3_gate_part_a.csv", build_table3a_frame(results))
    stage("tables-csv/table3_gate_part_b.csv", build_table3b_frame(results))
    stage("tables-csv/table4_collider_comparison.csv",
          build_table4_frame(payload["table4_rows"]))
    stage("ledgers-csv/ledger_concept_set_registry.csv", build_ledger_registry_frame())
    stage("ledgers-csv/ledger_variable_provenance.csv",
          build_ledger_provenance_frame(payload["provenance_rows"]))
    stage("ledgers-csv/ledger_exclusion_and_censoring_reasons.csv",
          build_ledger_exclusion_frame(payload["exclusion_ledger_rows"]))
    stage("ledgers-csv/ledger_wear_availability_by_day.csv",
          build_ledger_wear_frame(payload["wear_ledger_rows"]))
    stage("ledgers-csv/ledger_matched_set_sizes.csv",
          build_ledger_matched_sets_frame(payload["matched_set_rows"]))

    results["figures"] = _render_figures(payload, results, frames)
    results["tables"] = _render_tables(results, frames)
    # The locked exhibit budget, asserted before a single frame is written.  It is checked
    # again on arrival by `validate_bundle`, because a budget enforced only inside the
    # perimeter is a budget nobody can re-derive from the bundle.
    assert_exhibit_budget(results["figures"], results["tables"])
    # The `exhibit` a block declares and the `exhibit` its file's MANIFEST.csv row carries
    # are one fact written twice, and this is where they are made to agree.  8.3's column
    # is what a reader of the manifest alone sees; 3.8's field is what a consumer of
    # `results.json` alone sees, and a bundle in which they disagree tells two stories.
    for block in (*results["figures"].values(), *results["tables"].values()):
        stated = declarations[block["file"]].get("exhibit")
        if stated != block["exhibit"]:
            raise ExportError(
                f"{block['file']}: results.json calls it {block['exhibit']!r} and its "
                f"MANIFEST.csv row calls it {stated!r}. 3.8 and 8.3 name the same exhibit."
            )

    for key, block in results["figures"].items():
        if list(frames[block["file"]].columns) != block["columns"]:
            raise ExportError(f"{block['file']}: header does not match figures.{key}.columns")
    # A below-threshold FOREST ROW is present in its file rather than absent, so it is not
    # a silent omission, but 3.9 records it anyway and the worked example of 9.1 shows the
    # entry: the row is a named, prespecified analysis whose value is hidden, and a reader
    # of `suppressed` should meet it beside the hidden `results.json` nodes rather than
    # having to notice `estimable = false` in a CSV.
    forest = frames["figures-csv/figure3_forest.csv"]
    for _, row in forest.iterrows():
        if row["estimable"] != "false":
            continue
        log.add(locus="figures-csv/figure3_forest.csv", kind="row",
                file_row_key=f"{row['block']} / {row['row_order']}", column="estimate",
                reason="not_estimable_cell_size", rule="R1 contributing n below floor")

    # A suppressed TABLE cell is not recorded here one cell at a time, and that is a
    # decision rather than an omission: it carries the 7.5 sentence in the file itself, so
    # it is already its own record, `MANIFEST.csv` counts them per file in
    # `n_suppressed_cells`, and 3.9's `kind` vocabulary has no member for a table cell.
    # What this block exists to make impossible is a value hidden with NO mark anywhere,
    # which is a `results.json` node with no number and a Figure 2 day with no row.
    for file_path, absent in payload.get("series_points_by_file", {}).items():
        log.series_points_by_file[file_path] = int(absent)
    for locus, count in log.series_points_by_file.items():
        # A Figure 2 day that is absent is recorded as an AGGREGATE per file, never as a
        # list of individual days with their counts: a list of exactly which days fell
        # below the floor is itself a per-day count pattern.
        log.add(locus=locus, kind="series-point",
                reason="contributing_n_below_threshold",
                rule="R1 contributing n below floor")
    results["suppressed"] = log.as_block()

    specs = [
        (name, frames[name], declarations[name])
        for name in BUNDLE_FILES if name != "results.json"
    ]
    return results, specs, log


# ======================================================================================
# Row renderers.  These take TRUE integers and produce rendered rows, so the floor is
# applied in one place per file rather than once per call site.  A real Phase 4 run and
# the fixture both go through them.
# ======================================================================================


def _count_cell_from_true(true_n: int, *, forced: bool = False) -> str:
    """A table-CSV count cell: the display string, or the 7.5 sentence, from a TRUE count."""
    if forced:
        return LABELS["secondary_suppression"]
    if not disclosable(true_n):
        return LABELS["cell_below_threshold"]
    return f"{int(round20(true_n)):,}"


def _share_cell_from_true(true_num: int, true_den: int, *, forced: bool = False) -> str:
    """A percentage cell, rounded numerator over rounded denominator, zero decimals.

    A percentage dies with its count without exception, and it also dies with a denominator
    that cannot be disclosed: a percentage nobody may check against a printed denominator is
    a number a reader can only invert.
    """
    if forced or not disclosable(true_num) or not disclosable(true_den):
        return LABELS["numerator_suppressed"]
    return f"{_percent_integer(int(round20(true_num)), int(round20(true_den)))}%"


def render_provenance_rows(
    measurements: Sequence[tuple[str, int, int]],
) -> list[dict[str, Any]]:
    """The twelve rows of ledger 2, from (variable, true n_total, true n_missing).

    `n_missing` is tested against its COMPLEMENT as well as against itself.  `n_total` and
    `n_missing` are a two-member partition of a disclosed total whose other member, the
    observed count, is never written and is therefore recoverable by subtraction.  On an
    almost-complete variable that recovered number is large and harmless; on an almost
    entirely missing one it is small, and it is exactly the cell the floor protects.
    """
    rows: list[dict[str, Any]] = []
    for variable, true_total, true_missing in measurements:
        if variable not in VARIABLE_LABELS:
            raise ExportError(
                f"variable {variable!r} has no entry in section 7.13 and therefore has no "
                f"display label to print"
            )
        provenance = VARIABLE_PROVENANCE[variable]
        complement = int(true_total) - int(true_missing)
        if not disclosable(true_missing):
            missing_cell = LABELS["cell_below_threshold"]
        elif not disclosable(complement):
            missing_cell = LABELS["secondary_suppression"]
        else:
            missing_cell = f"{int(round20(true_missing)):,}"
        rows.append({
            "variable": variable,
            "display_label": VARIABLE_LABELS[variable],
            "role": provenance["role"],
            "source_table": provenance["source_table"],
            "source_concept_set": provenance["source_concept_set"],
            "derivation": VARIABLE_DERIVATION[variable],
            "unit": VARIABLE_UNIT[variable],
            "n_total": _count_cell_from_true(int(true_total)),
            "n_missing": missing_cell,
            "missing_handling": VARIABLE_MISSING_HANDLING[variable],
        })
    return rows


def render_exclusion_ledger_rows(
    measurements: Sequence[tuple[int, str, int, int]],
    partition_steps: Sequence[int] = (12, 15, 16),
) -> list[dict[str, Any]]:
    """The twenty rows of ledger 3, from (step, reason_detail slug, true n, true denominator).

    Steps 12, 15 and 16 are partitions and the rest are not, and the difference is a
    property of the rows.  Where a partition has exactly one member below the floor, the
    smallest disclosable sibling is suppressed beside it and carries the
    `secondary_suppression` sentence, not the `cell_below_threshold` one, so a reader can
    tell a cell hidden for its own size from a cell hidden to protect a sibling.
    """
    slug_by_step = {step: slug for step, slug, _kind, _unit in ATTRITION_RUNGS}
    forced: set[int] = set()
    for step in partition_steps:
        members = [i for i, m in enumerate(measurements) if m[0] == step]
        hidden = [i for i in members if not disclosable(measurements[i][2])]
        if len(hidden) == 1 and len(members) > 1:
            candidates = sorted(
                (i for i in members if i not in hidden), key=lambda i: measurements[i][2]
            )
            forced.add(candidates[0])

    rows: list[dict[str, Any]] = []
    for index, (step, detail, true_n, true_den) in enumerate(measurements):
        key = (int(step), detail)
        if key not in REASON_DETAIL_LABELS:
            raise ExportError(
                f"reason detail {key!r} has no sentence in section 7.12, so there is "
                f"nothing to print for it"
            )
        rung_slug = slug_by_step[int(step)]
        is_forced = index in forced
        rows.append({
            "step": str(int(step)),
            "slug": rung_slug,
            "display_label": LABELS[rung_slug],
            "reason_detail": REASON_DETAIL_LABELS[key],
            "n_episodes": _count_cell_from_true(int(true_n), forced=is_forced),
            "n_denominator": _count_cell_from_true(int(true_den)),
            "share_of_step_dropped": _share_cell_from_true(
                int(true_n), int(true_den), forced=is_forced),
            "_detail_slug": detail,
        })
    return rows


def render_wear_ledger_rows(
    groups: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """The rows of ledger 4, plus how many group-days the absence rule removed.

    A day whose `n_at_risk` fails `disclosable` is ABSENT from the file rather than written
    as a suppressed row, exactly as in Figure 2: a row with no value is not a point on a
    curve, and both the renderer and the reader want the series to stop where the data did.
    """
    rows: list[dict[str, Any]] = []
    absent = 0
    for group in groups:
        for day, true_at_risk, true_valid in group["days"]:
            if not disclosable(true_at_risk):
                absent += 1
                continue
            rows.append({
                "group_slug": group["slug"],
                "display_label": LABELS[group["slug"]],
                "group_order": str(int(group["order"])),
                "day": str(int(day)),
                "n_at_risk": _count_cell_from_true(int(true_at_risk)),
                "n_valid_wear": _count_cell_from_true(int(true_valid)),
                "share_valid_wear": _share_cell_from_true(int(true_valid), int(true_at_risk)),
            })
    return rows, absent


def render_figure2_rows(
    groups: Sequence[Mapping[str, Any]],
    accrual_last_day: int,
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    """Figure 2's long-format rows, its summary block, and how many day-points went absent.

    `series_segment` increments after every gap in a group's day sequence, so the renderer
    draws one plot() and one fill_between() per group AND SEGMENT and never bridges a gap.
    A visible break is the correct rendering: it says data ran out, which is true.
    """
    rows: list[dict[str, Any]] = []
    dropped: dict[str, int] = {}
    last_day: dict[str, int] = {}
    gaps: dict[str, int] = {}
    total_absent = 0
    for group in groups:
        slug = group["slug"]
        present = [d for d in group["days"] if disclosable(d["true_contributing"])]
        dropped[slug] = len(group["days"]) - len(present)
        total_absent += dropped[slug]
        segment = 1
        previous_day: int | None = None
        for day_spec in present:
            day = int(day_spec["day"])
            if previous_day is not None and day != previous_day + 1:
                segment += 1
            previous_day = day
            rows.append({
                "group_slug": slug,
                "display_label": LABELS[slug],
                "group_order": int(group["order"]),
                "day": day,
                "n_contributing": int(round20(day_spec["true_contributing"])),
                "observed_median": _round_to_unit(
                    day_spec["observed_median"], "normalized_activity"),
                "observed_p25": _round_to_unit(
                    day_spec["observed_p25"], "normalized_activity"),
                "observed_p75": _round_to_unit(
                    day_spec["observed_p75"], "normalized_activity"),
                "fitted_marginal": _round_to_unit(
                    day_spec["fitted_marginal"], "normalized_activity"),
                "fitted_lo": _round_to_unit(day_spec["fitted_lo"], "normalized_activity"),
                "fitted_hi": _round_to_unit(day_spec["fitted_hi"], "normalized_activity"),
                "in_accrual_window": _bool_cell(day <= accrual_last_day),
                "series_segment": segment,
            })
        last_day[slug] = present[-1]["day"] if present else 0
        gaps[slug] = segment - 1
    summary = {
        "days_dropped_by_group": dropped,
        "last_day_by_group": last_day,
        "n_gaps_by_group": gaps,
        "n_series": len(groups),
    }
    return rows, summary, total_absent


def render_figure4_rows(
    series: Sequence[Mapping[str, Any]],
    *,
    tier_permits_plot: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Figure 4's forty-four rows and its summary block, from TRUE contributing counts.

    Every one of the 22 offsets is written for every one of the 2 series, whatever the data
    do and whatever the tier permits.  A row whose true contributing count fails the floor
    carries the bare token in `n_contributing` and in all three quantiles, `plotted` is
    `false`, and `not_plotted_display` carries the 7.5 sentence the renderer prints where
    the marker would have sat.

    THE TWO REASONS ARE DIFFERENT SENTENCES AND THE DIFFERENCE IS NOT COSMETIC.  At a tier
    that permits no early-warning analysis no event-centered query is submitted at all, so
    the cell is empty because the tier forbade the question, and it carries
    `not_permitted_by_tier`; at a permitting tier a cell is empty because the offset had 20
    or fewer contributors, and it carries `contributing_n_below_threshold`.  3.7 keeps not
    permitted and suppressed apart everywhere else in this bundle and this file is where a
    reader meets both.
    """
    labelled = {slug: order for slug, order in FIGURE4_SERIES}
    supplied = {spec["slug"]: spec for spec in series}
    unknown = sorted(set(supplied) - set(labelled))
    if unknown:
        raise ExportError(
            f"figure 4 was handed series {unknown}, which section 7.15 has no label for. "
            f"The two series are fixed by 4.4 and are not data-dependent."
        )
    rows: list[dict[str, Any]] = []
    plotted_by_series: dict[str, int] = {}
    for slug, order in FIGURE4_SERIES:
        spec = supplied.get(slug, {})
        by_offset = {
            int(point["day_relative_to_event"]): point for point in spec.get("offsets", ())
        }
        plotted = 0
        for offset in FIGURE4_OFFSETS:
            point = by_offset.get(offset)
            if not tier_permits_plot:
                reason: str | None = "not_permitted_by_tier"
            elif point is None or not disclosable(point["true_contributing"]):
                reason = "contributing_n_below_threshold"
            else:
                reason = None
            if reason is None:
                plotted += 1
                cells = {
                    "n_contributing": str(int(round20(point["true_contributing"]))),
                    "observed_median": _figure_numeral(
                        point["observed_median"], "normalized_activity"),
                    "observed_p25": _figure_numeral(
                        point["observed_p25"], "normalized_activity"),
                    "observed_p75": _figure_numeral(
                        point["observed_p75"], "normalized_activity"),
                    "plotted": _bool_cell(True),
                    "not_plotted_display": "",
                }
            else:
                cells = {
                    "n_contributing": FIGURE_SUPPRESSED_TOKEN,
                    "observed_median": FIGURE_SUPPRESSED_TOKEN,
                    "observed_p25": FIGURE_SUPPRESSED_TOKEN,
                    "observed_p75": FIGURE_SUPPRESSED_TOKEN,
                    "plotted": _bool_cell(False),
                    "not_plotted_display": LABELS[reason],
                }
            rows.append({
                "series_slug": slug,
                "display_label": LABELS[slug],
                "series_order": order,
                "day_relative_to_event": offset,
                **cells,
            })
        plotted_by_series[slug] = plotted
    summary = {
        "n_days_plotted_by_series": plotted_by_series,
        "tier_permits_plot": bool(tier_permits_plot),
    }
    return rows, summary


def _figure_numeral(value: Any, unit: str) -> str:
    """A figure-CSV numeral, rounded to its unit's decimals BEFORE it reaches the frame.

    10.4 declaration 3.  Distinctness is computed on the in-memory value, so rounding on
    the way to the renderer would not keep a frame off the near-unique class, and it is
    also the stated precondition of 10.2 exception 5.
    """
    return FLOAT_FORMAT % _round_to_unit(float(value), unit)


def render_table4_rows(
    estimates: Mapping[str, Any],
    *,
    permitted: bool,
    window_counts: Mapping[str, Mapping[str, int]] | None = None,
) -> list[dict[str, Any]]:
    """Table 4's three rows, from the six collider keys of 3.7 and the two window totals.

    At a tier that permits no Arm A analysis no landmark panel query is submitted, so all
    three rows carry empty count cells and the `not_permitted_by_tier` sentence in both rate
    columns.  Keeping the rows is the same choice 4.4 makes for the event-centered curve and
    for the same reason: the three window groups are prespecified, not discovered, so a file
    that shrank to one row would say the comparison was defined differently rather than that
    the tier forbade it.

    ALL SIX RATE CELLS NOW TRACE TO A KEY.  5.7 gives the file three rows by two rate
    columns and 3.7 declares one `gate.arm_a.estimates` key for each of the six: column 5
    to `collider_rate_with_signal`, `collider_rate_without_signal` and
    `collider_rate_ratio_crude` in row order, column 6 to
    `collider_rate_with_signal_standardized`, `collider_rate_without_signal_standardized`
    and `collider_rate_ratio_standardized`.  Until contract 1.7.0 the two per-group
    standardized cells had no key at all and this module took them beside the payload; that
    supplement is gone rather than kept as a fallback, because a second route to a cell is a
    second thing to drift.

    THE TWO COUNT COLUMNS ARE STILL TAKEN BESIDE THE BLOCK, AND REFUSED RATHER THAN
    GUESSED.  Columns 3 and 4 are counts, not estimates: they are floor-tested and
    `round20`-rounded like every other count cell, so a block named `estimates` is the wrong
    home for them, and `denominators` carries one cohort-level `analytic_person_days` rather
    than a split of it.  They therefore arrive keyed by window group, and a permitting tier
    that arrives without them halts naming both sections.  11.4 carries the open decision
    about which `results.json` block should own them; a guessed count in a compliance bundle
    is worse than a halt that says what to amend.
    """
    if not permitted:
        sentence = LABELS["not_permitted_by_tier"]
        return [
            {
                "row_order": order,
                "Window group": LABELS[slug],
                "Episode-days at risk": "",
                "Acute-care events": "",
                "Crude rate per 1,000 episode-days": sentence,
                "Standardized rate per 1,000 episode-days": sentence,
            }
            for order, (slug, _crude, _std, _counts) in enumerate(TABLE4_ROWS, start=1)
        ]
    missing = [key for _slug, crude, std, _counts in TABLE4_ROWS
               for key in (crude, std) if key not in estimates]
    if missing:
        raise ExportError(
            f"table 4 needs gate.arm_a.estimates key(s) {sorted(set(missing))}, which are "
            f"not in the block. 5.7 traces every one of the file's six rate cells to a key "
            f"3.7 declares, and a rate cell with no key has nothing to print. "
            f"EXPORT-CONTRACT.md 11.4 dates the lag: `06_analysis_gate.py` declares five of "
            f"3.7's thirteen keys and must adopt the other eight."
        )
    counts_keys = [key for _s, _c, _std, key in TABLE4_ROWS if key is not None]
    if window_counts is None or any(key not in window_counts for key in counts_keys):
        absent = ([key for key in counts_keys if key not in (window_counts or {})])
        raise ExportError(
            f"table 4 at a permitting tier needs the window-group count pair(s) "
            f"{sorted(absent)}, the episode-days at risk and the acute-care events in each "
            f"condition, and no block of results.json declares them: 5.7 gives the file "
            f"those two columns and says they are counts rather than estimates, so 3.7's "
            f"`gate.arm_a.estimates` is the wrong home and `denominators` carries one "
            f"cohort-level `analytic_person_days` rather than a split of it. Supply them "
            f"beside the gate block as `table4_window_counts`, keyed by window group, each "
            f"with `episode_days` and `events`. EXPORT-CONTRACT.md 11.4 carries the open "
            f"decision about which block should own them. Refusing to guess a count in a "
            f"compliance bundle."
        )
    rows: list[dict[str, Any]] = []
    for order, (slug, crude_key, std_key, counts_key) in enumerate(TABLE4_ROWS, start=1):
        counts = {} if counts_key is None else dict(window_counts[counts_key])
        rows.append({
            "row_order": order,
            "Window group": LABELS[slug],
            "Episode-days at risk": (
                "" if counts.get("episode_days") is None
                else _count_cell_from_true(int(counts["episode_days"]))),
            "Acute-care events": (
                "" if counts.get("events") is None
                else _count_cell_from_true(int(counts["events"]))),
            "Crude rate per 1,000 episode-days": table_cell(estimates[crude_key]),
            "Standardized rate per 1,000 episode-days": table_cell(estimates[std_key]),
        })
    return rows


def render_table1_rows(
    row_specs: Sequence[Mapping[str, Any]],
    group_true_n: Sequence[tuple[str, int]],
) -> list[dict[str, Any]]:
    """Table 1's rows, with BOTH of its partitions enforced to a fixed point.

    Table 1 carries two different partitions and missing either leaves a recoverable cell:

      DOWN a column, the levels of one characteristic partition that group's total, so one
      suppressed level inside a block is recoverable by subtracting the others from the
      column header's n.
      ALONG a row, the procedure-group columns partition the pooled `All groups` cell, so
      one suppressed group cell is recoverable by subtracting the others from the pooled
      one.

    Forcing one can leave the other alone, which is why this iterates rather than making
    one pass.  The suppressed sibling chosen is always the SMALLEST disclosable one, so the
    cell that is lost is the one that tells a reader least.
    """
    slugs = [slug for slug, _n in group_true_n]
    totals = dict(group_true_n)
    truth: list[dict[str, int]] = []
    kinds: list[str] = []
    for spec in row_specs:
        if spec["statistic"] != "n (%)":
            truth.append({})
            kinds.append("display")
            continue
        truth.append({slug: int(round(totals[slug] * spec["weight"])) for slug in slugs})
        kinds.append("count")

    hidden: list[dict[str, str]] = [
        {slug: ("own" if not disclosable(values[slug]) else "show") for slug in values}
        for values in truth
    ]
    blocks: dict[str, list[int]] = {}
    for index, spec in enumerate(row_specs):
        if kinds[index] == "count" and spec.get("partition", False):
            blocks.setdefault(spec["characteristic"], []).append(index)
    member_slugs = [slug for slug in slugs if slug != "all_groups"]

    for _ in range(len(row_specs) + len(slugs) + 2):
        changed = False
        for indices in blocks.values():
            if len(indices) < 2:
                continue
            for slug in slugs:
                shown = [i for i in indices if hidden[i][slug] == "show"]
                if len(indices) - len(shown) == 1 and shown:
                    pick = min(shown, key=lambda i: truth[i][slug])
                    hidden[pick][slug] = "secondary"
                    changed = True
        for index, kind in enumerate(kinds):
            if kind != "count" or len(member_slugs) < 2:
                continue
            shown = [s for s in member_slugs if hidden[index][s] == "show"]
            if len(member_slugs) - len(shown) == 1 and shown:
                pick = min(shown, key=lambda s: truth[index][s])
                hidden[index][pick] = "secondary"
                changed = True
        if not changed:
            break

    rows: list[dict[str, Any]] = []
    for index, spec in enumerate(row_specs):
        if kinds[index] == "display":
            cells = list(spec["cells"])
        else:
            cells = []
            for slug in slugs:
                state = hidden[index][slug]
                if state == "secondary":
                    cells.append(LABELS["secondary_suppression"])
                elif state == "own":
                    cells.append(LABELS["cell_below_threshold"])
                else:
                    rounded = int(round20(truth[index][slug]))
                    pct = _percent_integer(rounded, int(round20(totals[slug])))
                    cells.append(f"{rounded:,} ({pct}%)")
        rows.append({
            "characteristic": spec["characteristic"],
            "level": spec["level"],
            "statistic": spec["statistic"],
            "partition": bool(spec.get("partition", False)),
            "cells": cells,
        })
    return rows


# ======================================================================================
# SECTION 9.  The fixture.
#
# An excerpt cannot be imported, so this is the complete bundle at the dummy values of
# 9.1.  It touches no cloud resource, reads no CDR and needs no credentials, so it runs in
# Phase 0 and costs nothing, and every local module's `_run_self_test()` runs against it.
#
# WHERE THE COUNTS COME FROM, recounted from the contract's own tables rather than copied:
#   19 attrition rungs   the rung table of 3.3 and 7.2, which is ANALYSIS-PLAN.md 2.6
#    5 by_group entries  4 procedure groups plus `all_groups`, at `four_group` (3.4)
#   14 sensitivity rows  10 ladder rows of 3.6 with row 6 expanded to four wear
#                        definitions and row 7 to two baseline windows: 10 - 2 + 4 + 2 = 14
#   27 forest rows       block 1's 5 contrasts (7.3) + block 2's 14 sensitivity rows (7.8)
#                        + block 3's 8 subgroups (7.11)
#  286 Figure 2 rows     4 series over 90 days is 360, less the 74 days the absence rule
#                        removes: 34 + 21 + 8 + 11 = 74, and 360 - 74 = 286
#   44 Figure 4 rows     2 series over the 22 offsets -14 to +7, and NOT data-dependent:
#                        4.4 keeps every row and suppresses the cells, so 2 x 22 = 44 on
#                        every run and at every tier
#    3 Table 4 rows      the three prespecified window groups of 5.7, on every run
#   16 manifest rows     1 + 4 + 6 + 5, per 3.8
#   41 Table 1 rows      the row-order table of 5.1, with six self-reported race levels
#   51 registry rows     30 CPT-4 codes + 21 ICD-10-PCS stems, from cs_spine.registry_rows()
#   12 provenance rows   the twelve variables of 7.13
#   20 exclusion rows    the twenty (step, reason_detail) pairs of 7.12
#  318 wear ledger rows  4 groups over 90 days less the 42 days whose at-risk count is not
#                        disclosable: 17 + 15 + 4 + 6 = 42, and 360 - 42 = 318.  The
#                        surviving day set is a SUPERSET of Figure 2's, per group, because
#                        a day's at-risk count is never below its contributing count.
#    1 matched-set row   the tier permits no Arm A analysis, so 5.6's one row saying so
#
# The timestamps are FIXED rather than taken from the clock, which is what makes the whole
# fixture byte-identical across runs, `results.json` included.  A real run takes the real
# clock and only its CSVs are byte-stable, which is what 8.2 says.
# ======================================================================================

FIXTURE_GENERATED_UTC = "2026-09-14T18:02:11Z"
FIXTURE_RUN_ID = "2026-09-14T18:02:11Z-a3f9c1"
FIXTURE_COMMIT = "4b1f9d2c8a7e0135ab62d4f80c9e73516a2d8b4f"
FIXTURE_CONTRACT_SHA = (
    "9f2c74b1a0d38e5f6c1b904e77aa2318cd54fe0b6a9137d24e8c05b3f1a6d2e0"
)
# THE THREE PLAN FACTS TRAVEL TOGETHER, and they are dummies together.  Whenever the
# fixture runs inside the repository all three are replaced by one read of the working tree
# -- `PLAN-HASH.txt`'s `sha256:` and `locked:` lines and ANALYSIS-PLAN.md's section 13 --
# and these values are never written.  They are here for the one case the tree is not,
# which is also the only case in which the plan hash itself is a dummy: a bundle carrying a
# made-up hash beside a made-up date at least says the same untrue thing twice, where a
# real hash beside a stale date says two different true-looking things and passed thirteen
# of thirteen checks doing it.  Adjacent so that a reader adding one cannot miss the others.
FIXTURE_PLAN_SHA = (
    "c41d8f2b6e07a95315cd4b8e2f70a6d19b3c5e8047af12d6903b7c4e5a1f9b77"
)
FIXTURE_PLAN_LOCKED_UTC = "2026-01-01T00:00:00Z"
FIXTURE_PLAN_AMENDMENTS: tuple[dict[str, Any], ...] = ()

# The ladder, as TRUE integers.  Every one is a multiple of the rounding base except the
# two that are meant to be suppressed, so the rounded ladder reproduces 9.1 exactly and the
# unrounded closure assert and the rounded residuals agree.
FIXTURE_LADDER: tuple[tuple[int, int, Any, int, Any], ...] = (
    # step, n_in, n_dropped, n_out, n_carried_forward
    (1, 413460, 403740, 9720, None),
    (2, 9720, 180, 10240, 9540),
    (3, 10240, 460, 9780, None),
    (4, 9780, 200, 9580, None),
    (5, 9580, 620, 8960, None),
    (6, 8960, 80, 8880, None),
    (7, 8880, 240, 8640, None),
    (8, 8640, 340, 8300, None),
    (9, 8300, 720, 7580, None),
    (10, 7580, 700, 6880, None),
    (11, 6880, 5720, 1160, None),
    (12, 1160, 520, 640, None),
    (13, 640, 60, 580, None),
    (14, 580, 180, 400, None),
    (15, 400, 60, 340, None),
    (16, 340, None, 340, None),
    (17, 340, None, 40, None),
    (18, 40, 12, 28, None),
    (19, 28, None, 28, None),
)

FIXTURE_GROUPS: tuple[tuple[str, int, int], ...] = (
    ("cervical_decompression", 1, 60),
    ("cervical_fusion", 2, 80),
    ("lumbar_decompression", 3, 120),
    ("lumbar_fusion", 4, 80),
    ("all_groups", 5, 340),
)

# (characteristic, level, statistic, partition, weight or the five display cells).
_MEDIAN = "median (IQR)"
_NPCT = "n (%)"


def _median_row(characteristic: str, triples: Sequence[tuple[Any, Any, Any]],
                decimals: int = 0, thousands: bool = False) -> dict[str, Any]:
    def one(value: Any) -> str:
        if thousands:
            return f"{int(value):,}"
        return f"{value:.{decimals}f}" if decimals else f"{int(value)}"
    return {
        "characteristic": characteristic,
        "level": "",
        "statistic": _MEDIAN,
        "partition": False,
        # The IQR uses the EN-DASH, never the word " to ": an observed range of a
        # non-negative quantity never carries a sign, and the word is reserved for the
        # interval that can.
        "cells": [f"{one(m)} ({one(lo)}–{one(hi)})" for m, lo, hi in triples],
    }


def _count_rows(characteristic: str, levels: Sequence[tuple[str, float]]) -> list[dict]:
    return [
        {"characteristic": characteristic, "level": level, "statistic": _NPCT,
         "partition": True, "weight": weight}
        for level, weight in levels
    ]


def fixture_table1_specs() -> list[dict[str, Any]]:
    """The forty-one rows of 5.1, in the fixed print order that section publishes."""
    specs: list[dict[str, Any]] = []
    specs.append(_median_row("Age, years", [
        (62, 54, 70), (59, 51, 67), (64, 56, 71), (61, 53, 69), (62, 54, 70)]))
    specs += _count_rows("Age band", [
        ("under 50", 0.18), ("50–64", 0.34), ("65–74", 0.30), ("75 or older", 0.18)])
    specs += _count_rows("Sex assigned at birth", [
        ("Female", 0.54), ("Male", 0.39), ("Other or not reported", 0.07)])
    specs += _count_rows("Self-reported race", [
        ("American Indian or Alaska Native", 0.02), ("Asian", 0.04),
        ("Black or African American", 0.18),
        ("Native Hawaiian or Other Pacific Islander", 0.01),
        ("White", 0.66), ("Not reported", 0.09)])
    specs += _count_rows("Self-reported ethnicity", [
        ("Hispanic or Latino", 0.14), ("Not Hispanic or Latino", 0.80),
        ("Not reported", 0.06)])
    specs.append(_median_row("Body mass index", [
        (29.4, 25.8, 33.9), (28.6, 25.1, 32.8), (30.2, 26.4, 34.7),
        (30.8, 26.9, 35.1), (29.7, 26.0, 34.1)], decimals=1))
    specs += _count_rows("Body mass index band", [
        ("under 25", 0.19), ("25–29", 0.31), ("30 or above", 0.38),
        ("Not recorded", 0.12)])
    specs.append(_median_row("Comorbidity burden", [
        (1, 0, 3), (1, 0, 3), (2, 0, 4), (2, 1, 4), (1, 0, 3)]))
    specs += _count_rows("Comorbidity burden", [
        ("0", 0.42), ("1", 0.26), ("2", 0.18), ("3 or more", 0.14)])
    specs.append(_median_row("Length of stay, days", [
        (1, 1, 2), (2, 1, 3), (2, 1, 3), (3, 2, 5), (2, 1, 4)]))
    specs += _count_rows("Length of stay band", [
        ("0–1", 0.46), ("2–3", 0.36), ("4 or more", 0.18)])
    specs += _count_rows("Index era", [
        ("before 2020", 0.38), ("2020–2021", 0.29), ("2022 or later", 0.33)])
    specs += _count_rows("Device class", [
        ("program provided", 0.24), ("participant owned", 0.68), ("Not recorded", 0.08)])
    specs.append(_median_row("Preoperative baseline steps per day", [
        (6420, 4180, 9260), (6810, 4390, 9640), (5980, 3820, 8710),
        (5640, 3510, 8320), (6180, 3960, 9040)], thousands=True))
    specs.append(_median_row("Valid baseline days", [
        (18, 13, 22), (17, 12, 21), (18, 14, 22), (16, 12, 21), (18, 13, 22)]))
    specs.append(_median_row("Valid wear days inside the accrual window", [
        (26, 17, 32), (24, 15, 31), (25, 16, 32), (22, 13, 29), (24, 15, 31)]))
    specs.append({
        "characteristic": "Near-complete accrual window, defined as 28 or more valid days",
        "level": "", "statistic": _NPCT, "partition": False, "weight": 0.52,
    })
    return specs


def _fixture_curve(n_group: int, day: int, floor_share: float) -> dict[str, Any]:
    """One Figure 2 day for one group: a declining contributing count and a recovery curve.

    The statistics are rounded to `normalized_activity`'s two decimals HERE, before they
    reach any frame, and that is not cosmetic: distinctness is computed on the in-memory
    floats, so 286 unrounded medians would be near-unique and the frame would be refused
    even though `FLOAT_FORMAT` prints something that looks fine.
    """
    contributing = int(n_group * (1.0 - 0.55 * (day - 1) / 89.0))
    recovery = floor_share + (1.0 - floor_share) * ((day / 90.0) ** 0.6)
    median = min(1.0, max(0.0, recovery))
    return {
        "day": day,
        "true_contributing": contributing,
        "observed_median": median,
        "observed_p25": max(0.0, median - 0.18),
        "observed_p75": min(1.0, median + 0.19),
        "fitted_marginal": median,
        "fitted_lo": max(0.0, median - 0.04),
        "fitted_hi": min(1.0, median + 0.04),
    }


# Which post-discharge days survive in Figure 2, per group.  Written out rather than
# derived from the curve, because the absence pattern is the thing the local renderer is
# being smoke-tested against: one group must have a MID-SERIES GAP so that a renderer
# which bridges gaps fails against the fixture instead of against the real bundle.
FIXTURE_FIGURE2_PRESENCE: dict[str, tuple[int, ...]] = {
    "cervical_decompression": tuple(range(1, 41)) + tuple(range(58, 74)),
    "cervical_fusion": tuple(range(1, 70)),
    "lumbar_decompression": tuple(range(1, 83)),
    "lumbar_fusion": tuple(range(1, 80)),
}

# The wear ledger's surviving days, a per-group PREFIX and a superset of Figure 2's set:
# a day's at-risk count is never below its contributing count, so a day Figure 2 keeps
# cannot be a day this ledger drops.
FIXTURE_WEAR_LAST_DAY: dict[str, int] = {
    "cervical_decompression": 73,
    "cervical_fusion": 75,
    "lumbar_decompression": 86,
    "lumbar_fusion": 84,
}

FIXTURE_FLOOR_SHARE: dict[str, float] = {
    "cervical_decompression": 0.34,
    "cervical_fusion": 0.24,
    "lumbar_decompression": 0.30,
    "lumbar_fusion": 0.16,
}


def render_forest_rows(
    contrasts: Mapping[str, Mapping[str, Any]],
    sensitivity: Mapping[str, Mapping[str, Any]],
    subgroups: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Figure 3's twenty-seven rows and its three block descriptors.

    `render` is what stops a renderer asserting a comparison that does not exist: a row
    whose value lives on a different axis draws no marker and no whisker, and the
    delta-shift row draws an inset panel, because a tipping curve is not a point estimate
    with an interval.
    """

    def numeral(value: Any) -> str:
        return FLOAT_FORMAT % float(value)

    def row(block: int, block_slug: str, order: int, slug: str, spec: Mapping[str, Any],
            *, axis: str, render: str, is_primary: bool) -> dict[str, Any]:
        estimable = bool(spec["estimable"])
        unit = spec.get("unit", "activity_days")
        if estimable:
            est, lo, hi = (_round_to_unit(v, unit) for v in spec["estimate"])
            if slug in BOUND_SENSITIVITY_ROWS:
                # A BOUND, so the file agrees with the node it is drawn from.  The
                # delta-shift row's estimate is a grid coordinate: `results.json` writes it
                # with `lo == hi == est` and an empty `display_ci`, and writing an interval
                # here would put two shapes on one number in one bundle.  The row renders as
                # `panel` and draws no whisker either way, but a consumer comparing the CSV
                # against the node would find them disagreeing, which is the drift the two
                # files exist to make impossible.
                lo = hi = est
            estimate, ci_lo, ci_hi = numeral(est), numeral(lo), numeral(hi)
            not_estimable_display = ""
        else:
            estimate = ci_lo = ci_hi = FIGURE_SUPPRESSED_TOKEN
            not_estimable_display = LABELS[spec["not_estimable_reason"]]
        true_n = int(spec["true_n"])
        n_cell = (
            str(int(round20(true_n))) if disclosable(true_n) else FIGURE_SUPPRESSED_TOKEN
        )
        return {
            "block": block,
            "block_label": LABELS[block_slug],
            "row_order": order,
            "slug": slug,
            "display_label": LABELS[slug],
            "estimate": estimate,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
            "unit": unit,
            "axis": axis,
            "render": render,
            "n": n_cell,
            "estimable": _bool_cell(estimable),
            "not_estimable_display": not_estimable_display,
            "is_primary": _bool_cell(is_primary),
            # The null line for this row's scale: 0 on a difference scale, 1 on a ratio one.
            "reference_value": 0,
        }

    rows: list[dict[str, Any]] = []
    for order, slug in enumerate(CONTRAST_SLUGS, start=1):
        spec = contrasts[slug]
        rows.append(row(1, "block_contrasts", order, slug, spec,
                        axis="primary", render="marker",
                        is_primary=bool(spec.get("is_primary", False))))
    for order, (_o, _s, slug, axis, render) in enumerate(SENSITIVITY_ROWS, start=1):
        rows.append(row(2, "block_robustness", order, slug, sensitivity[slug],
                        axis=axis, render=render, is_primary=False))
    for order, slug in enumerate(SUBGROUP_SLUGS, start=1):
        rows.append(row(3, "block_subgroups", order, slug, subgroups[slug],
                        axis="primary", render="marker", is_primary=False))

    if sum(1 for r in rows if r["is_primary"] == "true") != 1:
        raise ExportError("figure3_forest.csv must carry exactly one primary row")
    blocks = [
        {"index": 1, "display_label": LABELS["block_contrasts"], "rows": len(CONTRAST_SLUGS)},
        {"index": 2, "display_label": LABELS["block_robustness"],
         "rows": len(SENSITIVITY_ROWS)},
        {"index": 3, "display_label": LABELS["block_subgroups"], "rows": len(SUBGROUP_SLUGS)},
    ]
    return rows, blocks


FIXTURE_CONTRASTS: dict[str, dict[str, Any]] = {
    "fusion_vs_decompression": {
        "estimate": (4.4, 2.6, 6.2), "p": 0.0004, "is_primary": True,
        "true_n_compared": 340, "estimable": True, "true_n": 340},
    "lumbar_vs_cervical": {
        "estimate": (1.6, -0.3, 3.5), "p": 0.098, "is_primary": False,
        "true_n_compared": 340, "estimable": True, "true_n": 340},
    "region_by_fusion_interaction": {
        "estimate": (2.1, -0.4, 4.6), "p": 0.102, "is_primary": False,
        "true_n_compared": 340, "estimable": True, "true_n": 340},
    "fusion_vs_decompression_cervical": {
        "estimate": (3.9, 1.2, 6.6), "p": 0.005, "is_primary": False,
        "true_n_compared": 140, "estimable": True, "true_n": 140},
    "fusion_vs_decompression_lumbar": {
        "estimate": (4.8, 2.4, 7.2), "p": 0.0002, "is_primary": False,
        "true_n_compared": 200, "estimable": True, "true_n": 200},
}

# STROBE item 16(a), contract 1.9.0.  THE SAME FIVE SLUGS AS `FIXTURE_CONTRASTS` AND NO
# OTHERS, each on its own n and with its own interval, which is what makes the fixture
# exercise the pair a consumer has to print side by side.  The values are the worked
# example's of 9.1: every one sits further from zero than its adjusted twin, so a consumer
# that quietly read one where it meant the other would produce a visibly different number
# rather than a plausible one.  The primary pair, 5.8 unadjusted against 4.4 adjusted, is the
# gap the covariate block moved.
FIXTURE_UNADJUSTED_CONTRASTS: dict[str, dict[str, Any]] = {
    "fusion_vs_decompression": {
        "estimate": (5.8, 3.9, 7.7), "p": 0.0002, "is_primary": True,
        "true_n_compared": 340, "estimable": True, "true_n": 340},
    "lumbar_vs_cervical": {
        "estimate": (2.4, 0.3, 4.5), "p": 0.026, "is_primary": False,
        "true_n_compared": 340, "estimable": True, "true_n": 340},
    "region_by_fusion_interaction": {
        "estimate": (2.6, -0.1, 5.3), "p": 0.061, "is_primary": False,
        "true_n_compared": 340, "estimable": True, "true_n": 340},
    "fusion_vs_decompression_cervical": {
        "estimate": (5.2, 2.4, 8.0), "p": 0.0003, "is_primary": False,
        "true_n_compared": 140, "estimable": True, "true_n": 140},
    "fusion_vs_decompression_lumbar": {
        "estimate": (6.1, 3.6, 8.6), "p": 0.0001, "is_primary": False,
        "true_n_compared": 200, "estimable": True, "true_n": 200},
}

# The raw members `05_analysis_drd.py`'s `_assemble_unadjusted_model()` hands over, at the
# fixture's own rung.  The two display sentences are 05's `UNADJUSTED_CONTRAST_DISPLAY` and
# `UNADJUSTED_MANDATE_DISPLAY` verbatim, so the fixture exercises the strings a real run
# emits rather than a paraphrase of them.  The fixture converges at rung 1, so the unadjusted
# fit reaching rung 1 too is `rung_matches_adjusted = True` and the note is the matching one.
FIXTURE_UNADJUSTED_MODEL: dict[str, Any] = {
    "definition_display": (
        "The unadjusted contrast is the same model-and-integrate estimator refitted with the "
        "locked covariate set removed: age, sex assigned at birth, body mass index, "
        "comorbidity burden, length of stay, index year, the COVID-19 era indicator and "
        "device family are all absent from its mean structure. Everything the estimand is "
        "defined on is kept and is not an adjustment: the post-discharge-day spline, the "
        "procedure groups and their day curves, the region terms the collapse level admits, "
        "and day of week. The observation weights are the primary analysis's own and are not "
        "refitted, so the one difference between the two contrasts is the covariate block "
        "and the reader may read the gap between them as what the covariates moved."
    ),
    "mandate_display": (
        "This contrast is required by STROBE item 16(a), which asks for unadjusted estimates "
        "beside confounder-adjusted ones. It is not prespecified: the locked analysis plan "
        "carries an unadjusted association for the other arm at its section 4.8 and an "
        "unadjusted absolute level for this one at its section 9.2, and neither is an "
        "unadjusted contrast. It is reported as guideline-mandated and never as prespecified."
    ),
    # FALSE, and the fixture pins it false because that is what a run against plan version
    # 1.5 returns.  A fixture carrying `true` here would let a consumer that decided the
    # answer for itself pass its own self-test.
    "prespecified": False,
    "rung_slug": "r_ordered_beta_glmm",
    # Supplied because 05 supplies it, and IGNORED because 7.7 sends the printed string to
    # the label table: the exporter looks the display up from the slug rather than trusting
    # a string that travelled beside it.
    "rung_display": "Ordered beta mixed model in R",
    "rung_index": 1,
    "rung_matches_adjusted": True,
    "rung_note_display": (
        "The unadjusted fit reached the same rung of the model family ladder as the adjusted "
        "fit, so the two contrasts differ in the covariate set and in nothing else."
    ),
    # RAW RESAMPLE COUNTS, not a rendered node: the exporter builds the percentage node from
    # these two, the way it does for `meta.estimator.bootstrap_failure_rate`.  The denominator
    # is the PRIMARY resample count, `BOOTSTRAP_PRIMARY` in 05_analysis_drd.py, which is 1,000.
    "true_bootstrap_attempted": 1000,
    "true_bootstrap_failed": 24,
    "instability_trigger": False,
    "not_estimable_reason": None,
}

FIXTURE_SENSITIVITY: dict[str, dict[str, Any]] = {
    "pod_anchored_window": {
        "estimate": (5.1, 3.1, 7.1), "p": 0.0006, "true_n": 340, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Accrual over postoperative days 8 to 42 instead of post-discharge "
                  "days 1 to 35"},
    "inpatient_days_censored": {
        "estimate": (4.9, 3.0, 6.8), "p": 0.0007, "true_n": 340, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Days spent as an inpatient are censored rather than counted"},
    "complete_window_direct_regression": {
        "estimate": (4.2, 1.9, 6.5), "p": 0.0004, "true_n": 180, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Direct regression on the complete windows, with no integration step"},
    "observation_weighted": {
        "estimate": (4.7, 2.7, 6.7), "p": 0.0005, "true_n": 340, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Each observed day is weighted by its inverse probability of observation"},
    # THE SAME NUMBER AS `debt.delta_shift.tipping_point_point_estimate`, which is a
    # coordinate of 3.11's locked grid.  The `lo` and `hi` are deliberately not equal to it:
    # the row is a BOUND, so `_sensitivity_estimate_node` reads the point and drops the pair,
    # and a fixture whose pair is already collapsed would not exercise that.
    "delta_shift_tipping_point": {
        "estimate": (1.0, 0.75, 1.5), "p": None, "true_n": 340, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "unit": "dimensionless",
        "varies": "The delta grid, applied to the fusion group, the decompression group "
                  "and both"},
    "wear_definition_s1": {
        "estimate": (4.3, 2.4, 6.2), "p": 0.0009, "true_n": 380, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Valid wear day at 40% daily heart-rate adherence"},
    "wear_definition_s2": {
        "estimate": (4.6, 2.7, 6.5), "p": 0.0008, "true_n": 320, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Valid wear day at 10 hours of wear plus at least 100 steps"},
    "wear_definition_s3": {
        "estimate": (4.6, 2.7, 6.5), "p": 0.0008, "true_n": 360, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Valid wear day requires at least 8 hours of heart-rate wear"},
    "wear_definition_s4": {
        "estimate": (4.5, 2.6, 6.4), "p": 0.0008, "true_n": 300, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Valid wear day requires at least 12 hours of heart-rate wear"},
    "baseline_window_60_15": {
        "estimate": (4.1, 2.2, 6.0), "p": 0.0011, "true_n": 340, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Baseline taken over 15 to 60 days before surgery"},
    "baseline_window_30_1": {
        "estimate": (4.9, 3.0, 6.8), "p": 0.0006, "true_n": 340, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Baseline taken over 1 to 30 days before surgery"},
    "device_change_excluded": {
        "estimate": (4.4, 2.4, 6.4), "p": 0.0007, "true_n": 280, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Episodes whose device family changed across the window are excluded"},
    "baseline_floor": {
        "estimate": (4.2, 2.3, 6.1), "p": 0.0009, "true_n": 320, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Baseline floored at 1,000 steps per day"},
    "debt_untruncated": {
        "estimate": (5.1, 3.1, 7.1), "p": 0.0005, "true_n": 340, "estimable": True,
        "not_estimable_reason": None, "direction_matches_primary": True,
        "varies": "Daily deficit is not truncated at zero, so a day above baseline "
                  "offsets a day below"},
}

FIXTURE_SUBGROUPS: dict[str, dict[str, Any]] = {
    "subgroup_age_lt_65": {"estimate": (4.0, 1.8, 6.2), "true_n": 180, "estimable": True,
                           "not_estimable_reason": None},
    "subgroup_age_ge_65": {"estimate": (4.8, 2.4, 7.2), "true_n": 160, "estimable": True,
                           "not_estimable_reason": None},
    "subgroup_female": {"estimate": (4.6, 2.3, 6.9), "true_n": 180, "estimable": True,
                        "not_estimable_reason": None},
    "subgroup_male": {"estimate": (4.2, 1.9, 6.5), "true_n": 140, "estimable": True,
                      "not_estimable_reason": None},
    "subgroup_bmi_lt_30": {"estimate": (4.4, 2.1, 6.7), "true_n": 180, "estimable": True,
                           "not_estimable_reason": None},
    "subgroup_bmi_ge_30": {"estimate": (4.5, 2.2, 6.8), "true_n": 140, "estimable": True,
                           "not_estimable_reason": None},
    "subgroup_device_byod": {"estimate": (3.9, 1.7, 6.1), "true_n": 240, "estimable": True,
                             "not_estimable_reason": None},
    # The suppressed forest row.  It is PRESENT with `estimable = false`, not absent: a
    # Figure 3 row is a named, prespecified analysis, and omitting it would read as "this
    # analysis was never planned" and would leak by omission to anyone holding the list.
    "subgroup_device_wear": {"estimate": None, "true_n": 14, "estimable": False,
                             "not_estimable_reason": "not_estimable_cell_size"},
}

FIXTURE_PROVENANCE: tuple[tuple[str, int, int], ...] = (
    ("age_at_index", 340, 22),
    ("baseline_steps", 340, 0),
    ("bmi", 340, 84),
    ("charlson_score", 340, 46),
    ("daily_deficit", 9860, 1720),
    ("device_family", 340, 66),
    ("ethnicity_concept_id", 340, 38),
    ("los_days", 340, 0),
    ("procedure_group", 340, 0),
    ("r72", 40, 12),
    ("race_concept_id", 340, 44),
    ("sex_at_birth", 340, 26),
)

FIXTURE_EXCLUSION_LEDGER: tuple[tuple[int, str, int, int], ...] = (
    (3, "malignancy", 120, 460),
    (3, "metastatic_disease", 60, 460),
    (3, "spinal_cord_injury", 40, 460),
    (3, "spinal_infection", 80, 460),
    (3, "trauma", 180, 460),
    # Step 4's denominator is the count of episodes with an emergency department
    # encounter, deliberately NOT the rung's own drop count, which is why 5.6 gave this
    # file an `n_denominator` column at all.
    (4, "ed_encounter_present", 320, 320),
    (4, "rescue_degenerative_index", 120, 320),
    (4, "rescue_degenerative_outpatient_90d", 60, 320),
    (4, "rescue_elective_coded", 40, 320),
    (12, "baseline_span_under_14_days", 60, 520),
    (12, "fewer_than_seven_valid_days", 160, 520),
    (12, "no_valid_baseline_day", 300, 520),
    (14, "no_analyzable_day_in_window", 120, 180),
    (14, "not_at_risk_in_window", 60, 180),
    # Step 15 is the two-member partition doing its work: the true death count is below
    # the floor, so the repeat-operation count is suppressed beside it even though its own
    # true count is disclosable.
    (15, "death", 12, 60),
    (15, "repeat_spine_operation", 48, 60),
    (16, "censoring_cdr_observation_cutoff", 30, 340),
    (16, "censoring_death", 40, 340),
    (16, "censoring_none", 240, 340),
    (16, "censoring_repeat_spine_operation", 30, 340),
)


FIXTURE_BY_GROUP: tuple[dict[str, Any], ...] = (
    {"slug": "cervical_decompression", "true_n": 60, "true_complete_windows": 40,
     "unadjusted_debt": (5.4, 2.1, 11.8), "adjusted_debt": (6.1, 4.2, 8.0),
     "thousand_steps_lost": (28.4, 19.1, 37.7),
     "adjusted_mean_normalized_activity": (0.79, 0.74, 0.84),
     "share_reaching_80pct_baseline": (67, 54, 78), "zero_debt_true_n": 8},
    {"slug": "cervical_fusion", "true_n": 80, "true_complete_windows": 40,
     "unadjusted_debt": (9.8, 4.6, 17.2), "adjusted_debt": (9.4, 7.2, 11.6),
     "thousand_steps_lost": (46.1, 35.2, 57.0),
     "adjusted_mean_normalized_activity": (0.68, 0.63, 0.73),
     "share_reaching_80pct_baseline": (44, 33, 56), "zero_debt_true_n": 9},
    {"slug": "lumbar_decompression", "true_n": 120, "true_complete_windows": 60,
     "unadjusted_debt": (6.3, 2.6, 13.1), "adjusted_debt": (7.2, 5.4, 9.0),
     "thousand_steps_lost": (34.6, 25.9, 43.3),
     "adjusted_mean_normalized_activity": (0.75, 0.71, 0.79),
     "share_reaching_80pct_baseline": (58, 48, 68), "zero_debt_true_n": 12},
    {"slug": "lumbar_fusion", "true_n": 80, "true_complete_windows": 40,
     "unadjusted_debt": (14.2, 7.6, 22.9), "adjusted_debt": (12.4, 10.1, 14.7),
     "thousand_steps_lost": (61.8, 49.2, 74.4),
     "adjusted_mean_normalized_activity": (0.58, 0.53, 0.63),
     "share_reaching_80pct_baseline": (31, 21, 43), "zero_debt_true_n": 12},
    {"slug": "all_groups", "true_n": 340, "true_complete_windows": 180,
     "unadjusted_debt": (8.6, 3.4, 17.1), "adjusted_debt": (9.0, 7.6, 10.4),
     "thousand_steps_lost": (44.2, 36.1, 52.3),
     "adjusted_mean_normalized_activity": (0.68, 0.64, 0.72),
     "share_reaching_80pct_baseline": (47, 41, 53), "zero_debt_true_n": 41},
)


def utc_stamp(now: dt.datetime | None = None) -> str:
    """`meta.generated_utc`: ISO 8601 with a `Z` suffix, second precision.

    A run timestamp, not a participant date.  The date ban of section 10 is about
    participant-derived columns, and `meta` carries no participant-derived value at all;
    the distinction is written down rather than assumed because the two look identical.
    """
    moment = now or dt.datetime.now(dt.timezone.utc)
    return moment.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_run_id(generated_utc: str, code_commit_sha: str) -> str:
    """`meta.run_id`: the stamp, a hyphen, and six hex, unique per export.

    Derived from the stamp and the commit rather than drawn at random, so a re-export from
    the same code at the same second is the same run and a re-export from moved code is
    not.  Nothing about a participant reaches it.
    """
    digest = hashlib.sha256(f"{generated_utc}|{code_commit_sha}".encode("utf-8")).hexdigest()
    return f"{generated_utc}-{digest[:6]}"


def _repo_root() -> Path | None:
    """The v1/ directory, if this file is sitting inside the repository it belongs to."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / CONTRACT_RELATIVE_PATH).exists():
            return parent
    return None


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dag_sampling_salt(sql_text: str) -> str:
    """The sampling salt, READ from the DAG that uses it.  Never a literal in this module.

    WHY THIS FUNCTION EXISTS.  `meta` records how the run was configured, and the salt is
    half of what makes the matched sets reproducible: `build_all.sql` orders the control
    risk set by

        FARM_FINGERPRINT(FORMAT('%s|%d|%s|%s|%d',
          (SELECT sampling_salt FROM p), (SELECT seed FROM p), ...))

    so a session holding the seed and not the salt reproduces a DIFFERENT set of controls
    and has no way to know it.  Until this landed the bundle carried `seeds.farm_fingerprint
    = 20260825`, an integer that appears in no other file of this project: not in the DAG
    that samples, not in `build_params` which publishes the parameters, not in
    `DAG-SCHEMA.md` which documents the column, and not in `03_cohort.py` which passes it.
    It was wrong three ways at once -- wrong value, wrong type, and filed under `seeds`
    where a salt is not a seed -- and every one of the three came from the same cause, which
    is that the value was TYPED rather than read.  Reading it is the fix; the rest follows.

    WHY THE FILE AND NOT THE `build_params` TABLE.  A real run's authority is the row the
    DAG wrote, and that row is what the payload carries: `06_analysis_gate.py` hands this
    module `meta.sampling_salt` out of `build_params.sampling_salt`.  This function is the
    CROSS-CHECK on it, and it reads the one artefact that is present on both sides of the
    boundary and under version control -- the procedure's own DECLARE.  The two agreeing
    says the bundle was built by the code in this tree.  The two disagreeing says it was
    not, which is a stop condition and not a preference, and `_render_meta` treats it as one.

    Exactly one DECLARE, or a refusal.  Zero means the constant has moved and this module
    would otherwise fall back to something; two means the procedure declares it twice and
    no reader can say which one the FARM_FINGERPRINT saw.  Neither has a safe default.
    """
    found = BUILD_SQL_SALT_DECLARE.findall(sql_text)
    if len(found) != 1:
        raise ExportError(
            f"{BUILD_SQL_NAME} declares the sampling salt {len(found)} time(s) in the form "
            f"`DECLARE sampling_salt STRING DEFAULT '<salt>';` and this module reads exactly "
            f"one. The salt is half of what reproduces the matched sets and there is no "
            f"value to fall back to: a literal here is the defect this reader replaced."
        )
    salt = found[0]
    if not salt.strip():
        raise ExportError(
            f"{BUILD_SQL_NAME} declares an empty sampling salt. An empty salt makes the "
            f"FARM_FINGERPRINT ordering depend on the seed alone, which is a reproducibility "
            f"claim the bundle would be recording as true."
        )
    return salt


def dag_sampling_salt_from_tree() -> str:
    """`dag_sampling_salt` over the `build_all.sql` sitting beside this file.

    Beside this file rather than under `_repo_root()`, because the DAG travels with the
    pipeline and the prespecification does not have to: inside the perimeter this module is
    loaded out of `pipeline/` by `06_analysis_gate.py` and its sibling is right there.  A
    missing sibling is a refusal for the reason the reader above states -- there is no
    literal to fall back to, by design.
    """
    path = Path(__file__).resolve().parent / BUILD_SQL_NAME
    if not path.exists():
        raise ExportError(
            f"{BUILD_SQL_NAME} is not beside this module, so the sampling salt the bundle "
            f"records cannot be checked against the DAG that uses it. `meta.sampling_salt` "
            f"is read from the DAG and never transcribed here, so this halts rather than "
            f"emitting an unverified value."
        )
    return dag_sampling_salt(path.read_text(encoding="utf-8"))


def plan_hash_fields(text: str) -> dict[str, str]:
    """Every `key: value` line of `PLAN-HASH.txt`, read as ONE RECORD.

    AS A RECORD, WHICH IS THE WHOLE POINT OF THE HELPER.  `lock_plan.py` writes five lines
    and two of them are load-bearing: `sha256` says WHICH DOCUMENT and `locked` says WHICH
    LOCK OF IT.  They are separately falsifiable, they are written by one tool in one pass,
    and they are only ever true of each other.  Reading one of them live from this file and
    typing the other into the fixture by hand is how the bundle came to carry plan v1.5's
    hash beside v1.3's lock timestamp and print the mismatched pair into the Methods.  One
    read, both fields, and a missing half is a refusal rather than a fallback.

    The split is on the FIRST colon, because the value of `locked` carries two more.
    """
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields


def _markdown_table_rows(text: str, heading: str) -> list[list[str]]:
    """The first pipe table under `heading`, as rows of stripped cells, header dropped.

    Deliberately small and deliberately not a markdown parser: the one table this module
    reads is the amendment log of ANALYSIS-PLAN.md section 13, whose shape that section
    fixes.  A table that is not there returns no rows, and the caller decides what that
    means, because "the log is empty" and "the heading moved" are different findings.
    """
    start = text.find(heading)
    if start < 0:
        return []
    rows: list[list[str]] = []
    seen_header = False
    for line in text[start:].splitlines()[1:]:
        stripped = line.strip()
        if not stripped.startswith("|"):
            if seen_header:
                break
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(c and set(c) <= set("-: ") for c in cells):
            continue                              # the alignment rule under the header
        if not seen_header:
            seen_header = True
            continue                              # the header row itself
        rows.append(cells)
    return rows


def plan_amendment_entries(plan_text: str) -> list[dict[str, Any]]:
    """`meta.analysis_plan.amendments`, read from ANALYSIS-PLAN.md section 13's own table.

    ONE ENTRY PER ROW OF THE LOG, IN THE LOG'S OWN ORDER, carrying what the row carries and
    nothing this module invented.  Section 13 is the authority on how many times the plan
    has moved; the plan's own verification requirement and the log's opening paragraph both
    have the Methods cite the plan by hash and date AND cite any amendment, so an empty
    array beside a five-row log is a bundle reporting a document that has never moved.

    THE SHAPE CARRIES `superseded_sha256` AND NOT `sha256_after`, and the divergence from
    EXPORT-CONTRACT.md 3.1's proposed `{n, utc, reason, sha256_after}` is argued rather than
    drifted into.  Section 13 records the SUPERSEDED hash by design, and states the reason
    in its first paragraph: a file cannot contain its own hash, so the hash a row could
    carry is the one it replaced.  `sha256_after` is therefore not a fact the log holds.
    Deriving it by chaining each row onto the next would assume the table is in
    chronological order, which this module cannot check and which the log's own prose does
    not obviously satisfy; and the hash AFTER the last amendment is already in the bundle,
    as `meta.analysis_plan.sha256`.  Inventing the field would put a number in the Methods
    that no document states.  The contract row is the half that needs the amendment.

    `utc` carries the row's Date column verbatim.  The table records a DATE and not a lock
    stamp -- the stamps live in the log's prose, in an order this module has no way to pair
    with the table's rows -- so the date is what is carried, and nothing is upgraded into a
    precision the source does not have.
    """
    entries: list[dict[str, Any]] = []
    for index, row in enumerate(
            _markdown_table_rows(plan_text, PLAN_AMENDMENT_HEADING), start=1):
        if len(row) < 6:
            continue
        entries.append({
            "n": index,
            "utc": row[0],
            "sections": row[1],
            "change": row[2],
            "reason": row[3],
            "approved_by": row[4],
            "superseded_sha256": row[5].strip("`"),
        })
    return entries


def _plan_lock_from_tree(root: Path) -> tuple[str, str, list[dict[str, Any]]]:
    """The hash, the lock stamp and the amendment log, all read from the working tree.

    ONE FUNCTION, BECAUSE THEY ARE ONE FACT.  The Methods cites the plan by hash and by
    date, and a hash from one lock beside a date from another states no claim at all.  The
    three are returned together so that a caller cannot take one of them live and leave
    another behind, which is the defect this replaces.
    """
    hash_file = root / PLAN_HASH_RELATIVE_PATH
    fields = plan_hash_fields(hash_file.read_text(encoding="utf-8"))
    sha = fields.get("sha256", "")
    locked = fields.get("locked", "")
    if not re.fullmatch(r"[0-9a-f]{64}", sha):
        raise ExportError(
            f"{PLAN_HASH_RELATIVE_PATH} carries no `sha256:` line this module can read, so "
            f"the bundle would cite no prespecification at all."
        )
    if not PLAN_LOCK_STAMP.fullmatch(locked):
        raise ExportError(
            f"{PLAN_HASH_RELATIVE_PATH} records the plan hash but no `locked:` stamp this "
            f"module can read ({locked!r}). A hash says WHICH DOCUMENT and only the date "
            f"says WHICH LOCK of it, and a bundle carrying one live and the other from "
            f"memory is how this file came to print v1.5's hash beside v1.3's date. Both "
            f"come from this one read or neither does."
        )
    plan_file = root / PLAN_RELATIVE_PATH
    amendments = (
        plan_amendment_entries(plan_file.read_text(encoding="utf-8"))
        if plan_file.exists() else []
    )
    return sha, locked, amendments


def fixture_payload() -> dict[str, Any]:
    """The complete dummy payload of section 9.1, as TRUE counts.

    Nothing here is rounded or suppressed: every count is the true integer, and the whole
    of the disclosure work happens downstream in `render_bundle`, which is the same code
    path a real Phase 4 run takes.  That is the point of the fixture: if the floor, the
    partitions or the representations were applied by the fixture rather than by the
    exporter, the fixture would prove nothing about the exporter.
    """
    root = _repo_root()
    contract_sha = FIXTURE_CONTRACT_SHA
    plan_sha = FIXTURE_PLAN_SHA
    plan_locked_utc = FIXTURE_PLAN_LOCKED_UTC
    plan_amendments: list[dict[str, Any]] = list(FIXTURE_PLAN_AMENDMENTS)
    if root is not None:
        # Taken from the working tree when this is running inside the repository, so
        # `verify.py --bundle` checks 6 and 7 pass against the fixture as they will
        # against the real bundle.  A dummy is used only when the tree is not there.
        #
        # THE HASH, THE LOCK STAMP AND THE AMENDMENT LOG COME OFF THE TREE TOGETHER.  Until
        # this landed the hash was read live from `PLAN-HASH.txt` and the date beside it was
        # a literal in this function, so the pair drifted apart the moment the plan was
        # re-locked: the bundle carried plan v1.5's hash beside v1.3's lock timestamp and
        # the rendered Methods printed both.  The three now travel through one call, so a
        # re-lock moves all of them or none, and the pair cannot separate again.
        contract_sha = _sha256_of(root / CONTRACT_RELATIVE_PATH)
        if (root / PLAN_HASH_RELATIVE_PATH).exists():
            plan_sha, plan_locked_utc, plan_amendments = _plan_lock_from_tree(root)

    ladder = [
        {"step": step, "slug": slug, "kind": kind, "unit": unit,
         "n_in": n_in, "n_dropped": n_dropped, "n_out": n_out,
         "n_carried_forward": carried}
        for (step, slug, kind, unit), (_s, n_in, n_dropped, n_out, carried)
        in zip(ATTRITION_RUNGS, FIXTURE_LADDER)
    ]

    figure2_groups = []
    wear_groups = []
    for slug, order, n_group in FIXTURE_GROUPS:
        if slug == "all_groups":
            continue
        present = set(FIXTURE_FIGURE2_PRESENCE[slug])
        days = []
        for day in range(1, 91):
            spec = _fixture_curve(n_group, day, FIXTURE_FLOOR_SHARE[slug])
            if day not in present:
                # Below the floor on the TRUE count, which is what makes the absence rule
                # do the removing rather than the fixture.
                spec["true_contributing"] = 14
            days.append(spec)
        figure2_groups.append({"slug": slug, "order": order, "days": days})

        last = FIXTURE_WEAR_LAST_DAY[slug]
        wear_days = []
        for day in range(1, 91):
            at_risk = int(n_group * (1.0 - 0.45 * (day - 1) / 89.0)) if day <= last else 16
            wear_days.append((day, at_risk, int(0.75 * at_risk)))
        wear_groups.append({"slug": slug, "order": order, "days": wear_days})

    figure2_rows, figure2_summary, figure2_absent = render_figure2_rows(figure2_groups, 35)
    # The fixture pins tier 4, where `gate.arm_a.permitted` is false, no event-centered
    # query and no landmark panel query is submitted, and both new exhibits are written at
    # their full prespecified shape with a printed reason in every measured cell.  That is
    # section 1's rule for a file whose content is entirely suppressed, met in each file's
    # own representation, and it is what makes "44 rows" and "3 rows" true on every run.
    figure4_rows, figure4_summary = render_figure4_rows((), tier_permits_plot=False)
    table4_rows = render_table4_rows({}, permitted=False)
    wear_rows, wear_absent = render_wear_ledger_rows(wear_groups)
    forest_rows, forest_blocks = render_forest_rows(
        FIXTURE_CONTRASTS, FIXTURE_SENSITIVITY, FIXTURE_SUBGROUPS)
    table1_rows = render_table1_rows(
        fixture_table1_specs(), [(slug, n) for slug, _o, n in FIXTURE_GROUPS])

    return {
        "meta": {
            "contract_sha256": contract_sha,
            "study": (
                "Cumulative ambulatory activity loss after elective cervical and lumbar "
                "spine surgery"
            ),
            "generated_utc": FIXTURE_GENERATED_UTC,
            "run_id": FIXTURE_RUN_ID,
            "code_commit_sha": FIXTURE_COMMIT,
            "cdr": {
                "resource_name": "C2025Q4R6",
                "resolved_dataset": "wb-silky-artichoke-2408.C2025Q4R6",
                "resolved_by": "wb resource resolve --name C2025Q4R6",
                "resolved_utc": "2026-09-14T16:41:02Z",
                "bq_location": "US",
                "tier": "Controlled",
                "version_label": "cdrv9",
                # Controlled Tier dates are UNSHIFTED, which is why the date ban is a
                # column ban and not a formatting preference.
                "dates_shifted": False,
            },
            "workspace": {
                "google_project": "wb-spinewear-4471",
                "derived_dataset": "wb-spinewear-4471.spinewear_v1",
                "derived_location": "US",
            },
            "analysis_plan": {
                "path": PLAN_RELATIVE_PATH,
                # ALL THREE FROM THE SAME READ OF THE SAME LOCK.  The hash says which
                # document, the stamp says which lock of it, and the log says how many times
                # it has moved since; a Methods that cites two of the three from one lock and
                # the third from another cites no lock at all.
                "sha256": plan_sha,
                "locked_utc": plan_locked_utc,
                "locked_before_first_count": True,
                "amendments": plan_amendments,
            },
            "arm": {"slug": "recovery_debt",
                    "selected_by": "feasibility gate tier reached",
                    "tier_slug": "no_early_warning"},
            # SEEDS, AND ONLY SEEDS.  Four integers, each the 0 ANALYSIS-PLAN.md section 10
            # fixes "everywhere, in Python and in R".  The fifth member used to be
            # `farm_fingerprint: 20260825`, which was the sampling salt: a string, filed
            # under a name no document uses, at a value no document states.  It moved out
            # to `sampling_salt` below, where it is read rather than typed.
            "seeds": {"python": 0, "numpy": 0, "bootstrap": 0, "monte_carlo": 0},
            # READ FROM THE DAG, WHICH IS THE WHOLE OF THE FIX.  There is deliberately no
            # fixture literal to fall back to: the fixture is what proves the exporter emits
            # the DAG's salt, and a fixture carrying its own copy would prove only that two
            # copies agree.  `_checked_sampling_salt` compares this against the same DECLARE
            # on the way out, so reverting this line to a literal fails the render.
            "sampling_salt": dag_sampling_salt_from_tree(),
            "software": {
                "python": "3.11.9",
                "packages": {"numpy": "1.26.4", "pandas": "2.2.2",
                             "statsmodels": "0.14.2"},
                "r": "4.3.2",
                "r_packages": {"glmmTMB": "1.1.9", "ordbetareg": "0.7.2"},
            },
            "estimator": {
                "rung_index": 1,
                "descent_triggers_fired": [],
                "fallback_reason": None,
                "rungs_attempted": [
                    {"index": 1, "slug": "r_ordered_beta_glmm", "outcome": "converged"},
                    {"index": 2, "slug": "r_zero_one_inflated_beta_glmm",
                     "outcome": "not attempted"},
                ],
                # The denominator is the PRIMARY resample count, `BOOTSTRAP_PRIMARY` in
                # 05_analysis_drd.py, which is 1,000.  It read 500, which is
                # `BOOTSTRAP_SENSITIVITY`, the count a robustness row is run at; a local
                # module sanity-checking the primary denominator against the locked
                # constant would have failed against the fixture and passed against the
                # bundle, which is the worst way round for a fixture to be wrong.
                "bootstrap_failure_rate": percentage_node(38, 1000),
            },
            "concept_set": {
                "n_concepts": scalar_node(852, "852"),
                "source_module": "pipeline/cs_spine.py",
                "registry_file": "ledgers-csv/ledger_concept_set_registry.csv",
                "gaps": {
                    "cervical_decompression": {
                        "builder": "cs_spine.cervical_decompression_split_sql",
                        "evidence_path_first":
                            "candidate CPT only, invisible to the locked set",
                        "n_candidate_only": count_node(60),
                        "n_locked_set": count_node(1140),
                        "share": percentage_node(60, 1200),
                        "response_display": (
                            "Stated omission: the four absent codes and the measured share "
                            "go in the Methods and in the limitations. The set is not "
                            "amended"
                        ),
                        "set_amended": False,
                    },
                    "cervical_fusion": {
                        "builder": "cs_spine.cervical_fusion_split_sql",
                        "evidence_path_first":
                            "candidate CPT only, invisible to the locked set",
                        "n_candidate_only": count_node(80),
                        "n_also_carrying_candidate_cpt": count_node(80),
                        "n_locked_set": count_node(1140),
                        "n_misfiled": count_node(40),
                        "share": percentage_node(40, 1140),
                        "response_display": (
                            "A supplementary row moves the misfiled episodes to cervical "
                            "fusion and re-estimates the primary contrast; the locked set "
                            "is not amended"
                        ),
                        "set_amended": False,
                    },
                },
            },
        },
        "denominators": {
            "program_participants": {
                "true_n": 413460, "unit": "persons", "rung": (1, "n_in"),
                "definition": "All participants in the Controlled Tier release",
                "used_for": "The first box of the participant flow figure."},
            "episodes_identified": {
                "true_n": 10240, "unit": "episodes", "rung": (2, "n_out"),
                "definition": (
                    "Qualifying spine surgical episodes after same-day collapse"),
                "used_for": "The participant flow figure and the Methods."},
            "episodes_eligible": {
                "true_n": 6880, "unit": "episodes", "rung": (10, "n_out"),
                "definition": (
                    "Identified episodes surviving every protocol exclusion"),
                "used_for": "The participant flow figure and the Manski bounds."},
            "episodes_wearable_linked": {
                "true_n": 1160, "unit": "episodes", "rung": (11, "n_out"),
                "definition": "Eligible episodes with any Fitbit activity record",
                "used_for": "The participant flow figure and the wearable linkage sentence."},
            "episodes_baseline_adequate": {
                "true_n": 640, "unit": "episodes", "rung": (12, "n_out"),
                "definition": (
                    "Wearable-linked episodes with adequate preoperative baseline wear"),
                "used_for": "The participant flow figure and the feasibility gate stage B."},
            "analytic": {
                "true_n": 340, "unit": "episodes", "rung": (16, "n_out"),
                "definition": (
                    "Eligible spine episodes with adequate preoperative baseline wear and "
                    "a computable post-discharge activity window"),
                "used_for": (
                    "The default denominator. Table 1, Table 2, Figure 2 and Figure 3 "
                    "unless a row names another.")},
            "analytic_person_days": {
                "true_n": 9860, "unit": "person-days", "rung": None,
                "definition": (
                    "Contributing person-days inside the accrual window"),
                "used_for": "The Table 2 footer and the model fit statement in Methods."},
            "events_composite": {
                "true_n": 40, "unit": "events", "rung": (17, "n_out"),
                "definition": (
                    "First emergency department visits and readmissions through "
                    "post-discharge day 90, whichever came first"),
                "used_for": (
                    "Table 3 part A stage D and the feasibility statement in Results.")},
            # The fixture pins tier 4, where no event-centered query is submitted at all,
            # so no risk-set member is drawn and the true count is a real zero.  A real
            # zero is disclosable and `is_legal_disclosed_count(0)` is true, so this is
            # the tier-4 number and not a placeholder standing in for one.
            "event_centered_members": {
                "true_n": 0, "unit": "risk-set members", "rung": None,
                "definition": (
                    "Risk-set members drawn on the event-centered curve, after the "
                    "structural filter the conditional and discrete-time fits apply"),
                "used_for": (
                    "The plate note and legend of the supplementary event-centered "
                    "figure.")},
        },
        "ladder": ladder,
        "collapse_level": "four_group",
        "collapse_level_index": 1,
        "collapse_reason": "every procedure group at or above the disclosure floor",
        "collapse_footnote": None,
        "denominator_index": ["analytic", "events_composite"],
        "groups": [
            {"slug": slug, "order": order, "true_n": n}
            for slug, order, n in FIXTURE_GROUPS
        ],
        "window": {
            "accrual_first_day": 1, "accrual_last_day": 35, "follow_up_last_day": 90,
            "baseline_first_day": -30, "baseline_last_day": -8,
            "baseline_min_valid_days": 7, "baseline_min_span_days": 14,
            "valid_day_min_minutes": 600,
            "display_accrual": "post-discharge day 1–35",
            "display_baseline": "8–30 days before surgery",
        },
        "debt": {
            "estimand_display": (
                "Digital recovery debt is the sum across post-discharge day 1 to 35 of "
                "the shortfall between a participant's daily step count and that "
                "participant's own preoperative baseline, in baseline-equivalent activity "
                "days lost."
            ),
            "max_possible": 35,
            "by_group": [dict(entry) for entry in FIXTURE_BY_GROUP],
            "contrasts": FIXTURE_CONTRASTS,
            # STROBE item 16(a), contract 1.9.0.  `absolute_scale` below has NO unadjusted
            # twin and that is 3.5's decision rather than an omission in this fixture: the
            # absolute-scale model must carry the log-baseline spline, so a covariate-free
            # version of it would still carry a covariate.
            "unadjusted_contrasts": FIXTURE_UNADJUSTED_CONTRASTS,
            "unadjusted_model": dict(FIXTURE_UNADJUSTED_MODEL),
            "absolute_scale": {
                "fusion_vs_decompression": {
                    "estimate": (24.9, 13.8, 36.0), "p": 0.0009, "is_primary": False,
                    "true_n_compared": 340},
            },
            "manski": {
                "by_group": {"all_groups": (3.1, 21.4)},
                "primary_lower": -0.4,
                "primary_upper": 9.6,
            },
            # THE WHOLE PRESPECIFIED GRID, AND TWO TIPPING POINTS THAT ARE COORDINATES ON IT.
            # The fixture used to report a point estimate of 1.25 and an interval crossing at
            # 0.75 against a two-point `grid` holding 0.0 and 1.25.  1.25 is not a value
            # ANALYSIS-PLAN.md 3.11's grid can produce -- it fixes 0, 0.25, 0.5, 0.75, 1.0,
            # 1.5, 2.0 -- and 0.75 was reported as a crossing on a grid that never evaluated
            # it, so both numbers named shifts the analysis had not walked.  05 can only ever
            # return a delta it walked, so this is the shape a real run produces: the seven
            # locked coordinates, a contrast curve monotone in the shift, the interval first
            # including zero at 0.75, and the point estimate first at or below zero at 1.0.
            "delta_shift": {
                "applied_to": "decompression only",
                # Bound nodes at contract 1.6.0: a tipping point is a grid coordinate, so
                # it is one number and not an interval.
                "tipping_point_point_estimate": 1.0,
                "tipping_point_interval": 0.75,
                "definition_display": (
                    "The primary contrast crosses zero once the daily deficit on "
                    "unobserved days in the decompression groups is shifted upward by 1.0 "
                    "log-odds on the model's own latent scale, which turns a reference day "
                    "with a 30% deficit into a day with a 54% deficit."
                ),
                "applications": ["fusion only", "decompression only", "both groups"],
                # `implied_deficit_at_reference` is expit(logit(0.30) + delta) at the two
                # decimals 2.4 gives `normalized_activity`, which is what 3.11 means by "the
                # translation is computed, never hand-typed".
                "grid": [
                    {"delta": 0.0, "applied_to": "decompression only", "contrast_est": 4.4,
                     "contrast_lo": 2.6, "contrast_hi": 6.2,
                     "implied_deficit_at_reference": 0.3},
                    {"delta": 0.25, "applied_to": "decompression only", "contrast_est": 3.5,
                     "contrast_lo": 1.7, "contrast_hi": 5.3,
                     "implied_deficit_at_reference": 0.35},
                    {"delta": 0.5, "applied_to": "decompression only", "contrast_est": 2.5,
                     "contrast_lo": 0.7, "contrast_hi": 4.3,
                     "implied_deficit_at_reference": 0.41},
                    {"delta": 0.75, "applied_to": "decompression only", "contrast_est": 1.6,
                     "contrast_lo": -0.2, "contrast_hi": 3.4,
                     "implied_deficit_at_reference": 0.48},
                    {"delta": 1.0, "applied_to": "decompression only", "contrast_est": 0.0,
                     "contrast_lo": -1.8, "contrast_hi": 1.8,
                     "implied_deficit_at_reference": 0.54},
                    {"delta": 1.5, "applied_to": "decompression only", "contrast_est": -1.9,
                     "contrast_lo": -3.7, "contrast_hi": -0.1,
                     "implied_deficit_at_reference": 0.66},
                    {"delta": 2.0, "applied_to": "decompression only", "contrast_est": -3.6,
                     "contrast_lo": -5.4, "contrast_hi": -1.8,
                     "implied_deficit_at_reference": 0.76},
                ],
                "reference_deficit": 0.3,
                "grid_extended": False,
                "crossed_within_grid": True,
                "interval_crossed_within_grid": True,
                "no_crossing_display": None,
            },
            "model_fit": {
                "family": "ordered beta", "link": "logit",
                # 3.5, corrected at contract 1.7.0 and verbatim from ANALYSIS-PLAN.md 3.6:
                # RESTRICTED, not natural, and in POST-DISCHARGE day, not postoperative day.
                # The two differ by the length of stay, which is the confounded quantity of
                # the plan's 5.1, and this is the string 05 emits.
                "spline_basis": "restricted cubic on post-discharge day", "spline_df": 5,
                "rho": (0.41, 0.36, 0.46), "icc": (0.62, 0.55, 0.69),
                "marginal_r2": (0.18, 0.13, 0.23), "conditional_r2": (0.69, 0.64, 0.74),
                "aic": 18420, "true_n_person_days": 9860, "true_n_persons": 340,
                "converged": True, "monte_carlo_draws": 2000,
                # The rung the residual descent of ANALYSIS-PLAN.md 3.4 reached.  Rung 1 is
                # where the descent starts; the fixture converges there, and the exporter
                # reads the rung rather than assuming it.
                "residual_structure": "continuous_time_ar1_intercept_slope",
            },
        },
        "sensitivity": FIXTURE_SENSITIVITY,
        "gate": {
            # THE LEDGER IS MONOTONE NON-INCREASING AND IT IS NOT THE ANALYTIC COHORT.  Stage
            # A is the QUALIFYING episodes the gate starts from, which is the ladder's rung
            # 11 output at 1,160 -- the spine episodes with wearable data, before the
            # baseline-wear rule.  It used to be the analytic 340 with stage B at 420
            # beneath it, so the fixture shipped a ledger whose second row was larger than
            # its first while B is a subset of A by definition, and 340 was the wrong number
            # for stage A in the first place.  Stage B is rung 12's output and stage C is
            # Arm A's own 3-day-window count, which is laxer than Arm B's 35-day window and
            # is therefore above the analytic cohort rather than equal to it.  The four group
            # cells of stage A sum to its total, and stage F's four sum to its own.
            "stages": {
                "A": {"total": 1160, "by_group": {
                    "cervical_decompression": 200, "cervical_fusion": 280,
                    "lumbar_decompression": 400, "lumbar_fusion": 280}},
                "B": {"total": 640},
                "C": {"total": 420},
                "D": {"total": 40, "components": {
                    "first_ed_visits": 18, "readmissions": 22, "composite": 40}},
                "E": {"total": 15},
                "F": {"total": 15, "by_group": {
                    "cervical_decompression": 4, "cervical_fusion": 4,
                    "lumbar_decompression": 4, "lumbar_fusion": 3}},
            },
            "arm_a": {
                "permitted": False,
                "reason_display": (
                    "The feasibility gate reached the lowest prespecified tier, which "
                    "permits no early-warning estimate. The deciding count is itself below "
                    "the disclosure floor, so the tier boundary and the disclosure floor "
                    "coincide."
                ),
                "estimates": {},
            },
        },
        # 04, 05 and 06 each certify their own output and this module refuses to render
        # until all three have.  The fixture carries them as the three modules return them,
        # so the certification path is exercised by every `--fixture` run rather than only
        # by the self-test's refusal cases.
        "certifications": {
            "features": {"features ok": True, "halting": []},
            "drd": {"drd ok": True, "halting": []},
            "gate": {"gate ok": True, "halting": []},
        },
        "figure2_rows": figure2_rows,
        "figure2_summary": figure2_summary,
        "figure4_rows": figure4_rows,
        "figure4_summary": figure4_summary,
        "table4_rows": table4_rows,
        "figure3_blocks": forest_blocks,
        "forest_rows": forest_rows,
        "table1_rows": table1_rows,
        "provenance_rows": render_provenance_rows(FIXTURE_PROVENANCE),
        "exclusion_ledger_rows": render_exclusion_ledger_rows(FIXTURE_EXCLUSION_LEDGER),
        "wear_ledger_rows": wear_rows,
        "matched_set_rows": [matched_sets_not_permitted_row()],
        "series_points_by_file": {
            "figures-csv/figure2_daily_activity.csv": figure2_absent,
            "ledgers-csv/ledger_wear_availability_by_day.csv": wear_absent,
        },
    }


DEFAULT_FIXTURE_DIRECTORY = "local/fixtures/results"


def write_fixture(directory: Path | str) -> dict[str, Any]:
    """Write the complete dummy bundle of 9.1 into `directory`.  Data-free and free.

    THE PREVIOUS BUNDLE IS NEVER DELETED BEFORE THE NEW ONE EXISTS.  This function used to
    unlink all sixteen files and both manifests and then rebuild, so a rebuild that raised
    part way through left the directory EMPTY.  That is not hypothetical: a half-landed
    edit raised `ValueError: too many values to unpack` mid-rebuild and destroyed the
    fixture, and it was recovered only because another session regenerated it minutes
    later.  The bundle is the only thing the six local modules can be developed against and
    the same writer puts a real Phase 4 run's actual results at the contract path, so
    delete-then-fail is not an acceptable failure mode for either.

    `export_bundle` now renders into a staging directory beside the destination and swaps
    the finished bundle in, so a rebuild that raises leaves the previous bundle intact and
    byte-identical, and a swap that fails between its two renames rolls back to it.  The
    swap also does what the unlink was for, and does it unconditionally rather than for the
    sixteen names this module happens to know: the destination is REPLACED, so a straggler
    from a previous bundle shape cannot survive into the new one and be refused by
    `verify.py --bundle` rule 3.

    A FIXTURE REBUILD HAS NO PROBE-WRITTEN PREDECESSOR, which is why the registry
    comparison of 5.6 is off here.  The only concept-set registry at a fixture destination
    is the one an earlier fixture run wrote; comparing the two would report an ordinary
    edit to `cs_spine.py` as `01_probe.py` and this module disagreeing across two phases,
    which is a sentence about a run that never happened.
    """
    return export_bundle(Path(directory), fixture_payload(),
                         compare_registry_to_previous=False)


def describe_tree(root: Path) -> str:
    """The bundle as a sorted listing with byte sizes, for a report or a log."""
    root = Path(root)
    lines = [f"{root}"]
    for name in ("MANIFEST.csv", "MANIFEST.md5", "results.json"):
        path = root / name
        lines.append(f"  {name:<52} {path.stat().st_size:>9,} bytes")
    for directory in BUNDLE_DIRECTORIES:
        lines.append(f"  {directory}/")
        for name in BUNDLE_FILES:
            if not name.startswith(directory + "/"):
                continue
            path = root / name
            leaf = name.split("/", 1)[1]
            lines.append(f"    {leaf:<50} {path.stat().st_size:>9,} bytes")
    return "\n".join(lines)


# ======================================================================================
# Self-test.  Every refusal this module exists to make is pinned here, so a later "fix"
# that quietly removes one fails rather than lands.  `python3 07_export.py` runs it with
# no cloud, no credentials and no pytest.
# ======================================================================================


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _extended_delta_grid_rows(base: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The fixture's grid carried out to 3.11's extension, for the self-test cases that use it.

    The contrast keeps falling and the implied deficit keeps rising, both computed rather
    than typed, so a case that claims a crossing beyond delta 2.0 has a grid that reaches it.
    """
    rows = [dict(point) for point in base]
    last = dict(rows[-1])
    for delta in DELTA_SHIFT_GRID_EXTENDED[len(DELTA_SHIFT_GRID):]:
        step = float(delta) - float(last["delta"])
        rows.append({
            "delta": float(delta),
            "applied_to": last["applied_to"],
            "contrast_est": round(float(last["contrast_est"]) - 3.2 * step, 1),
            "contrast_lo": round(float(last["contrast_lo"]) - 3.2 * step, 1),
            "contrast_hi": round(float(last["contrast_hi"]) - 3.2 * step, 1),
            "implied_deficit_at_reference": round(
                1.0 / (1.0 + math.exp(-(math.log(0.3 / 0.7) + float(delta)))), 2),
        })
        last = rows[-1]
    return rows


def _expect_refusal(fn, fragment: str, message: str) -> None:
    """Assert that `fn()` refuses, and that the refusal says the right thing."""
    try:
        fn()
    except (DisclosureError, ContractViolation, ExportError) as error:
        _expect(fragment in str(error),
                f"{message}: refused, but for the wrong reason: {error}")
        return
    raise AssertionError(f"{message}: the frame was NOT refused")


def _run_self_test() -> None:
    checks = 0

    # ---------------------------------------------------------------- label table shape
    for _step, slug, _kind, _unit in ATTRITION_RUNGS:
        _expect(slug in LABELS, f"rung {slug} has no ladder-box label")
        _expect(slug in RUNG_REASON_DISPLAY, f"rung {slug} has no reason display")
        checks += 2
    _expect(len(ATTRITION_RUNGS) == 19, "the ladder is not nineteen rungs")
    _expect(len(SENSITIVITY_ROWS) == 14, "the plotted sensitivity set is not fourteen")
    _expect(len(SUPPLEMENTARY_SENSITIVITY_ROWS) == 10,
            "the supplementary sensitivity set is not ten")
    _expect(len(REASON_DETAIL_LABELS) == 20, "7.12 is not twenty pairs")
    _expect(len(VARIABLE_LABELS) == 12 and len(VARIABLE_DERIVATION) == 12,
            "7.13 is not twelve variables")
    _expect(set(VARIABLE_PROVENANCE) == set(VARIABLE_LABELS),
            "the provenance block and 7.13 name different variables")
    _expect(len(BUNDLE_FILES) == 16, "the bundle is not sixteen files")
    _expect(len(BUNDLE_FILES) == 1 + 4 + 6 + 5,
            "3.8 derives sixteen manifest rows as 1 + 4 + 6 + 5 and every term is named")
    _expect(len(GATE_ESTIMATE_KEYS) == 13, "3.7 is not thirteen estimate keys")
    _expect(all(key in LABELS for key in GATE_ESTIMATE_KEYS),
            "an estimate key has no printed label in 7.15")
    _expect(len(FIGURE4_OFFSETS) == 22 and len(FIGURE4_SERIES) == 2,
            "4.4 fixes two series over twenty-two offsets")
    _expect(len(TABLE4_ROWS) == 3
            and all(slug in LABELS for slug, _c, _s, _k in TABLE4_ROWS),
            "5.7 is three window groups, each with a label in 7.15")
    # Six rate cells, six keys, and every one of them declared by 3.7.  This is the count
    # that was wrong until contract 1.7.0: two printed cells traced to nothing.
    _expect(sorted({key for _s, crude, std, _k in TABLE4_ROWS for key in (crude, std)})
            == sorted(k for k in GATE_ESTIMATE_KEYS if k.startswith("collider_")),
            "5.7's six rate cells and 3.7's six collider keys are not the same six")
    _expect(len(RESIDUAL_STRUCTURE_RUNGS) == 3,
            "ANALYSIS-PLAN.md 3.4's residual descent is three rungs")
    for unit in ("absolute_risk_percent", "rate_ratio", "rate_per_1000_episode_days"):
        _expect(UNIT_DECIMALS[unit] == 2 and unit in UNIT_HEADER_DISPLAY,
                f"2.4's unit {unit} is missing or not at two decimals")
        checks += 1
    checks += 7
    _expect(len(CHECK_SLUGS) == 13, "3.10 is not thirteen checks")
    _expect(not (set(SENSITIVITY_ROWS_SLUGS := {r[2] for r in SENSITIVITY_ROWS})
                 & set(SUPPLEMENTARY_SENSITIVITY_ROWS)),
            "a supplementary slug is in the plotted set")
    checks += 9
    for value in list(LABELS.values()) + list(RUNG_REASON_DISPLAY.values()) \
            + list(REASON_DETAIL_LABELS.values()) + list(VARIABLE_DERIVATION.values()):
        _expect(not any(ch in value for ch in disclosure.BANNED_CHARACTERS),
                "a label carries a banned dash character")
        checks += 1
    for table, name in ((VARIABLE_UNIT, "unit"), (VARIABLE_MISSING_HANDLING,
                                                  "missing_handling")):
        _expect(set(table) == set(VARIABLE_LABELS),
                f"7.14's {name} table and 7.13 name different variables")
        checks += 1
        for value in table.values():
            _expect(not re.search(r"\b[a-z0-9]+_[a-z0-9_]+\b", value),
                    f"a printed 7.14 string carries a snake case token: {name}")
            _expect(not any(ch in value for ch in disclosure.BANNED_CHARACTERS),
                    f"a printed 7.14 string carries a banned dash character: {name}")
            checks += 2

    # ---------------------------------------------------- the two predicates, two moments
    _expect(utc_stamp(dt.datetime(2026, 9, 14, 18, 2, 11, tzinfo=dt.timezone.utc))
            == FIXTURE_GENERATED_UTC, "utc_stamp does not render ISO 8601 with a Z suffix")
    _expect(make_run_id(FIXTURE_GENERATED_UTC, FIXTURE_COMMIT)
            == make_run_id(FIXTURE_GENERATED_UTC, FIXTURE_COMMIT),
            "make_run_id is not deterministic")
    _expect(disclosable(20) is False, "a TRUE count of 20 is below the floor")
    _expect(is_legal_disclosed_count(20) is True,
            "a RENDERED 20 is the ordinary output of round20 on a true 21 to 29")
    # Written against MIN_CELL rather than the numerals, so the ast.Compare walk of 10.4
    # does not report this line.  It says the same thing: one above the floor, and nine
    # above it, both round DOWN onto the floor's own numeral, which is why a displayed 20
    # stands on a true 21 to 29 and never on 20.
    _expect(round20(MIN_CELL + 1) == MIN_CELL and round20(MIN_CELL + 9) == MIN_CELL,
            "a displayed 20 must stand on a true 21 to 29")
    _expect(round20(MIN_CELL + 10) == MIN_CELL * 2,
            "a true 30 rounds up, so it never displays as 20")
    _expect(disclosure.is_suppressed(round20(MIN_CELL)),
            "round20 emits the sentinel for a true 20, never the numeral")
    checks += 7

    # ------------------------------------------------------------- REFUSAL: unrounded count
    _expect_refusal(
        lambda: _gate_probe(
            pd.DataFrame({"slug": [f"r{i}" for i in range(24)],
                          "n": [21] * 24}),
            relative_path="figures-csv/figure1_strobe_ladder.csv",
            kind="figure-csv", count_cols=("n",)),
        "not legal disclosed counts",
        "an unrounded count column")
    # The same floor, on a count embedded in a composed Table 1 cell.  Without this the
    # gate reads the column as free text and tests nothing at all, which is the failure
    # mode that leaves no mark in the file it damages.
    _expect_refusal(
        lambda: _gate_probe(
            pd.DataFrame({"Cervical decompression (n = 60)": ["21 (35%)", "40 (67%)"]}),
            relative_path="tables-csv/table1_cohort_characteristics.csv",
            kind="table-csv",
            composite_count_columns=("Cervical decompression (n = 60)",)),
        "whose embedded count is not a legal disclosed count",
        "an unrounded count inside a composed table cell")
    _expect(_embedded_counts("62 (54–70)") == [],
            "a median with an interquartile range is not a count cell")
    _expect(_embedded_counts("0.62 (95% CI 0.55 to 0.69)") == [],
            "an estimate with a confidence interval is not a count cell")
    _expect(_embedded_counts("1,240 (33%)") == [1240], "a composed n (%) cell carries a count")
    _expect(_embedded_counts("n = 340") == [340], "an n = token carries a count")
    checks += 5

    # ------------------------------------- REFUSAL: a percentage beside a suppressed count
    sentence = LABELS["cell_below_threshold"]
    _expect_refusal(
        lambda: _gate_probe(
            pd.DataFrame({"n_episodes": ["40", sentence],
                          "n_denominator": ["60", "60"],
                          "share_of_step_dropped": ["67%", "80%"]}),
            relative_path="ledgers-csv/ledger_exclusion_and_censoring_reasons.csv",
            kind="table-csv",
            count_cols=("n_episodes", "n_denominator"),
            percentage_columns=("share_of_step_dropped",)),
        "discloses 1 value(s) on row(s) where count column",
        "a percentage beside a suppressed count")
    checks += 1

    # ------------------------------------------- REFUSAL: a lone suppressed partition member
    _expect_refusal(
        lambda: _gate_probe(
            pd.DataFrame({"n_in": ["40"], "n_dropped": [sentence], "n_out": ["20"]}),
            relative_path="figures-csv/figure1_strobe_ladder.csv",
            kind="table-csv",
            count_cols=("n_in", "n_dropped", "n_out"),
            column_partitions=(("n_dropped", "n_out"),)),
        "exactly one suppressed member",
        "a lone suppressed member of a column partition")
    _expect_refusal(
        lambda: _gate_probe(
            pd.DataFrame({"n_episodes": [sentence, "40", "60"]}),
            relative_path="ledgers-csv/ledger_exclusion_and_censoring_reasons.csv",
            kind="table-csv",
            count_cols=("n_episodes",),
            row_partitions=(("n_episodes", (0, 1, 2)),)),
        "exactly one suppressed member across a declared row partition",
        "a lone suppressed member of a row partition")
    checks += 2

    # ----------------------------------------------------- REFUSAL: a non-contiguous row_order
    gapped = pd.DataFrame({"row_order": [1, 2, 4], "Characteristic": ["a", "b", "c"]})
    _expect_refusal(
        lambda: assert_row_order_contiguous(gapped, "Table 1"),
        "row_order is not the contiguous ordinal",
        "a gap in Table 1's row_order")
    assert_row_order_contiguous(
        pd.DataFrame({"row_order": [1, 2, 3]}), "Table 1")
    checks += 2

    # ---------------------------------------------------------- REFUSAL: a registry md5 drift
    _expect_refusal(
        lambda: _assert_registry_matches_probe("0" * 32, "1" * 32),
        "cs_spine.py moved between the two phases",
        "a concept-set registry md5 that differs from the probe's")
    _assert_registry_matches_probe(None, "1" * 32)
    _assert_registry_matches_probe("1" * 32, "1" * 32)
    checks += 3

    # ----------------------------------------------- REFUSAL: a single-series Figure 2 frame
    single = pd.DataFrame({
        "group_slug": ["all_groups"] * 90,
        "day": list(range(1, 91)),
        "n_contributing": [40] * 90,
        "observed_median": [round(0.3 + 0.006 * d, 2) for d in range(90)],
    })
    _expect_refusal(
        lambda: safe_export(single, Path(tempfile.mkdtemp()) / "results" /
                            "figures-csv" / "figure2_daily_activity.csv",
                            kind="figure-csv", count_cols=("n_contributing",)),
        "near-unique",
        "a single-series day-indexed Figure 2 frame")
    # The same frame passes once `day` is declared under 10.2 exception 3, which is the
    # whole reason that exception exists: at `single_group` the axis is distinct in every
    # row, and a gate that refuses at one collapse level what it passes at another is
    # measuring cardinality and not disclosure.
    row = safe_export(single, Path(tempfile.mkdtemp()) / "results" / "figures-csv" /
                      "figure2_daily_activity.csv",
                      kind="figure-csv", count_cols=("n_contributing",),
                      specification_columns=["day"])
    _expect(len(row["md5"]) == 32, "safe_export must return a manifest row with an md5")
    _expect(tuple(row) == tuple(MANIFEST_COLUMNS),
            "safe_export must return the MANIFEST.csv row, keyed as MANIFEST_COLUMNS")
    checks += 3

    # ------------------------ REFUSAL: a specification_columns declaration off the register
    # `n_contributing` is a COUNT.  10.2 says in terms that no exception in the document
    # reaches a count, a percentage or a share column on these files or on any other, so it
    # is authorised by no register and declaring it would switch the near-unique class off
    # on the one column of this file where a small cell could live.
    _expect_refusal(
        lambda: _gate_probe(
            pd.DataFrame({"n_contributing": [40, 60]}),
            relative_path="figures-csv/figure2_daily_activity.csv",
            kind="figure-csv", specification_columns=("n_contributing",)),
        "authorised by none of the three 10.2 registers",
        "a count column declared as a specification column")
    _expect_refusal(
        lambda: _gate_probe(
            pd.DataFrame({"code": ["22551"]}),
            relative_path="ledgers-csv/ledger_variable_provenance.csv",
            kind="table-csv", specification_columns=("code",)),
        "authorised by none of the three",
        "a whitelisted column declared on the wrong file")
    _expect(specification_column_authority(
        "figures-csv/figure2_daily_activity.csv", "day") == "10.2 exception 3",
        "the day axis is authorised by exception 3 and not by the whitelist")
    _expect(specification_column_authority(
        "figures-csv/figure2_daily_activity.csv", "observed_median") == "10.2 exception 5",
        "a statistic column on the same file is authorised by exception 5")
    _expect(specification_column_authority(
        "figures-csv/figure3_forest.csv", "slug") == "10.2 whitelist",
        "a forest slug is authorised by the whitelist")
    # Figure 1 entered the whitelist at contract 1.6.1, for its five rung-vocabulary
    # columns and for those only.  Its four COUNT columns are held by no register and are
    # eligible under no reading, which is the residue 11.4 carries as a dated obligation:
    # at twenty-one rungs `n_in` and `n_out` cross the ceiling too.
    _expect(specification_column_authority(
        "figures-csv/figure1_strobe_ladder.csv", "slug") == "10.2 whitelist",
        "figure 1's rung vocabulary is whitelisted as of contract 1.6.1")
    for count_column in ("n_in", "n_dropped", "n_out", "n_carried_forward", "closes_exact"):
        _expect(specification_column_authority(
            "figures-csv/figure1_strobe_ladder.csv", count_column) is None,
            f"figure 1's {count_column} is granted by nothing, anywhere")
        checks += 1
    _expect(set(
        c for (f, c) in SPECIFICATION_COLUMN_AUTHORITY if f.endswith("figure1_strobe_ladder.csv")
    ) == {"step", "slug", "display_label", "reason", "reason_display"},
        "figure 1's grant is five columns and not the file")
    # THE FIGURE 1 NEAR MISS, MEASURED RATHER THAN ARGUED.  At nineteen rungs the ladder
    # clears the near-unique class by one row and by accident: the module's row floor is
    # `NEAR_UNIQUE_MIN_ROWS`, the test is strictly greater, and the class therefore never
    # arms.  Padded past the floor the same frame is refused, and this pins both halves of
    # the 1.6.1 grant: that it clears the five rung-vocabulary columns, and that `n_in` and
    # `n_out` survive it, which is the residue 11.4 carries as a dated obligation.
    grown = pd.DataFrame({
        "step": list(range(1, 22)),
        "slug": [f"rung_{i}" for i in range(1, 22)],
        "display_label": [f"Rung {i}" for i in range(1, 22)],
        "reason": [f"reason_{i}" for i in range(1, 22)],
        "reason_display": [f"Sentence {i}" for i in range(1, 22)],
        # Deliberately distinct per row, which is what a real ladder's survivor counts are.
        "n_in": [str(20 * (60 - i)) for i in range(1, 22)],
        "n_out": [str(20 * (59 - i)) for i in range(1, 22)],
    })
    ungranted = disclosure.export_violations(grown, kind="figure-csv",
                                             count_cols=("n_in", "n_out"))
    _expect(sum(1 for v in ungranted if "near-unique" in v) >= 5,
            "at twenty-one rungs the ladder's vocabulary columns are near-unique, which is "
            "the refusal the nineteenth rung was hiding by one row")
    granted = disclosure.export_violations(
        grown, kind="figure-csv", count_cols=("n_in", "n_out"),
        specification_columns=["step", "slug", "display_label", "reason",
                               "reason_display"])
    cleared = {"step", "slug", "display_label", "reason", "reason_display"}
    _expect(not any(f"{c!r}" in v for v in granted if "near-unique" in v for c in cleared),
            "the 1.6.1 whitelist grant clears all five rung-vocabulary columns")
    _expect(any("near-unique" in v and ("n_in" in v or "n_out" in v) for v in granted),
            "AND THE TWO COUNT COLUMNS SURVIVE IT. They are counts, a count column is "
            "exempted by nothing in 10.2, and this is the residue 11.4 dates rather than "
            "a gap this module may close at a call site")
    checks += 3

    # 10.2 exception 5's PRECONDITION, refused rather than assumed: an unrounded statistic
    # is not eligible under the exception or any other, because rounding is what bounds the
    # value space the exception then argues about.
    _expect_refusal(
        lambda: _gate_probe(
            pd.DataFrame({"n_contributing": [40, 40],
                          "observed_median": [0.412, 0.221],
                          "observed_p25": [0.2, 0.1], "observed_p75": [0.6, 0.5],
                          "fitted_marginal": [0.4, 0.2], "fitted_lo": [0.3, 0.1],
                          "fitted_hi": [0.5, 0.3]}),
            relative_path="figures-csv/figure2_daily_activity.csv",
            kind="figure-csv", count_cols=("n_contributing",),
            specification_columns=("observed_median",)),
        "not at their unit's decimals",
        "an exception 5 column that was not rounded before the frame was built")
    checks += 7

    # ------------------------------- the gate block may arrive already rendered from 06
    # `06_analysis_gate.py` builds the whole block in the contract's shape, so 07 adopts it
    # rather than asking 06 to hand back raw counts it has already correctly consumed.  The
    # round trip must be exact, and the suppression ledger must come out the same length
    # either way, or the adoption path is quietly losing a hidden cell.
    base = fixture_payload()
    rendered_results, _specs, rendered_log = render_bundle(base)
    adopted = fixture_payload()
    adopted["gate"] = rendered_results["gate"]
    adopted_results, _s2, adopted_log = render_bundle(adopted)
    _expect(adopted_results["gate"] == rendered_results["gate"],
            "adopting a pre-rendered gate block changes the block")
    _expect(len(adopted_log.entries) == len(rendered_log.entries),
            "adopting a pre-rendered gate block loses a suppression-ledger entry")
    _expect(adopted_results["suppressed"]["by_reason"]
            == rendered_results["suppressed"]["by_reason"],
            "adopting a pre-rendered gate block changes the suppression ledger")
    broken_tier = fixture_payload()
    broken_tier["gate"] = json.loads(json.dumps(rendered_results["gate"]))
    broken_tier["gate"]["tier"]["exhibit_set"] = "alternate"
    _expect_refusal(lambda: render_bundle(broken_tier),
                    "replaces the whole exhibit set",
                    "a tier that switches the exhibit set")
    broken_label = fixture_payload()
    broken_label["gate"] = json.loads(json.dumps(rendered_results["gate"]))
    broken_label["gate"]["stages"][0]["display_label"] = "Qualifying episodes"
    _expect_refusal(lambda: render_bundle(broken_label),
                    "printed string that is not the contract's",
                    "a gate stage label that is not the contract's")
    # 3.2's key list says "required, all mandatory", and the word now costs something.
    # An exhibit's `denominator` is a POINTER, so a mandatory target that the renderer
    # would happily leave out is not a pointer at all.
    no_denominator = fixture_payload()
    del no_denominator["denominators"]["event_centered_members"]
    _expect_refusal(lambda: render_bundle(no_denominator),
                    "mandatory denominator(s): ['event_centered_members']",
                    "a payload missing a mandatory denominator")
    bad_unit = fixture_payload()
    bad_unit["denominators"]["event_centered_members"]["unit"] = "members"
    _expect_refusal(lambda: render_bundle(bad_unit),
                    "not in 3.2's vocabulary",
                    "a denominator carrying a unit 3.2 does not declare")
    # The tier and the curve's denominator are one fact.  A permitting tier that drew
    # nobody, and a forbidding tier that drew somebody, are both refused, so the
    # denominator cannot go stale while every row of the file still says the right thing.
    stale_denominator = fixture_payload()
    stale_denominator["denominators"]["event_centered_members"]["true_n"] = 340
    _expect_refusal(lambda: render_bundle(stale_denominator),
                    "draws nobody; a permitting tier draws somebody",
                    "a tier-4 run whose event-centered curve claims 340 members")
    checks += 8

    # -------------------------------- REFUSAL: an upstream module that did not certify
    # The module whose declared posture is refuse by default must have a channel through
    # which an upstream refusal can arrive, and it must be read BEFORE anything is
    # rendered.  All three are required; a missing block is a refusal and not a default.
    for name, key, fragment in (
        ("features", "features ok", "04_features.py did not certify"),
        ("drd", "drd ok", "05_analysis_drd.py did not certify"),
        ("gate", "gate ok", "06_analysis_gate.py did not certify"),
    ):
        refusing = fixture_payload()
        refusing["certifications"] = json.loads(
            json.dumps(refusing["certifications"]))
        refusing["certifications"][name][key] = False
        refusing["certifications"][name]["halting"] = ["a reason the module returned"]
        _expect_refusal(lambda p=refusing: render_bundle(p),
                        fragment, f"{key} is false")
        _expect_refusal(lambda p=refusing: render_bundle(p),
                        "a reason the module returned",
                        f"{key} is false and the upstream reason is quoted")
        dropped = fixture_payload()
        dropped["certifications"] = {
            k: v for k, v in dropped["certifications"].items() if k != name
        }
        _expect_refusal(lambda p=dropped: render_bundle(p),
                        "does not carry every upstream certification",
                        f"{key} is absent")
        checks += 3
    no_block = fixture_payload()
    del no_block["certifications"]
    _expect_refusal(lambda: render_bundle(no_block),
                    "carries no `certifications` block",
                    "a payload with no certifications block at all")
    # Nothing is rendered and nothing is written when a certification refuses, which is the
    # whole point of reading them first: a bundle that must not exist must not be built.
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "results"
        refusing = fixture_payload()
        refusing["certifications"]["gate"] = {
            "gate ok": False,
            "halting": ["the event timing frame and the ladder disagree about how many "
                        "first events carry a computable proximal ratio"],
        }
        _expect_refusal(lambda: export_bundle(target, refusing),
                        "did not certify its output",
                        "export_bundle with a refusing upstream module")
        _expect(not target.exists() or not any(target.rglob("*.csv")),
                "a refused export must write no file at all")
    checks += 3

    # ------------------------ REFUSAL: a residual structure the plan's 3.4 does not name
    unknown_residual = fixture_payload()
    unknown_residual["debt"]["model_fit"] = dict(
        unknown_residual["debt"]["model_fit"], residual_structure="ar1_on_the_row_index")
    _expect_refusal(lambda: render_bundle(unknown_residual),
                    "not one of the three residual rungs",
                    "a residual structure outside ANALYSIS-PLAN.md 3.4")
    no_residual = fixture_payload()
    no_residual["debt"]["model_fit"] = {
        k: v for k, v in no_residual["debt"]["model_fit"].items()
        if k != "residual_structure"
    }
    _expect_refusal(lambda: render_bundle(no_residual),
                    "carries no residual structure this module can name",
                    "a fit that names no residual structure at all")
    # The descent is data-dependent, so a lower rung renders as ITS OWN display and the
    # Table 2 footer prints what was fitted rather than what rung 1 would have been.
    for _index, slug, display in RESIDUAL_STRUCTURE_RUNGS:
        descended = fixture_payload()
        descended["debt"]["model_fit"] = dict(
            descended["debt"]["model_fit"], residual_structure=slug)
        rendered, specs_d, _log_d = render_bundle(descended)
        _expect(rendered["debt"]["model_fit"]["residual_correlation"] == display,
                f"the bundle must name the residual rung actually reached: {slug}")
        footer = next(f for name, f, _d in specs_d
                      if name == "tables-csv/table2_adjusted_debt_footer.csv")
        _expect(display in list(footer["Value"]),
                f"the Table 2 footer must print the rung actually reached: {slug}")
        checks += 2
    checks += 2

    # ===== THE REPRODUCIBILITY INPUTS: FOUR SEEDS FROM THE PLAN, ONE SALT FROM THE DAG =====
    # THIS IS THE ASSERTION THAT WAS MISSING.  The bundle carried
    # `meta.seeds.farm_fingerprint = 20260825` and nothing anywhere compared it to anything,
    # because there was nothing to compare it to: the integer appears in no other file of
    # this project.  The salt the DAG actually samples with is a STRING, it is declared once
    # in `build_all.sql`, published as `build_params.sampling_salt`, documented in
    # `DAG-SCHEMA.md` and passed by `03_cohort.py`, and the exporter consulted none of them.
    # Every check below exists to make that impossible rather than merely fixed: the value is
    # read from the DAG, it is compared to the DAG on the way out, and it may not appear as a
    # literal in this module's own source at all.
    declared_salt = dag_sampling_salt_from_tree()
    _expect(isinstance(declared_salt, str) and bool(declared_salt.strip()),
            f"build_all.sql declares a non-empty sampling salt, read as {declared_salt!r}")
    _expect(rendered_results["meta"]["sampling_salt"] == declared_salt,
            f"meta.sampling_salt is {rendered_results['meta']['sampling_salt']!r} and "
            f"build_all.sql declares {declared_salt!r}. The bundle records the salt the DAG "
            f"uses, or it records a number a reproducing session would sample against and "
            f"get a different risk set from.")
    # NO COPY HERE, ENFORCED.  A transcription is how the fabricated value survived four
    # documents, so the salt is not permitted to occur in this file's bytes: `--fixture`,
    # `_render_meta` and `validate_bundle` all reach it through `dag_sampling_salt`.
    _expect(declared_salt not in Path(__file__).read_text(encoding="utf-8"),
            "the sampling salt appears as a literal in this module's source. It is READ from "
            "build_all.sql at every one of the three sites that needs it; a copy here is the "
            "defect `20260825` was, one edit away from drifting again.")
    seeds = rendered_results["meta"]["seeds"]
    _expect(set(seeds) == {"python", "numpy", "bootstrap", "monte_carlo"},
            f"meta.seeds carries the four seeds and nothing else, got {sorted(seeds)}. A salt "
            f"is not a seed and the block whose every member ANALYSIS-PLAN.md section 10 "
            f"fixes at 0 cannot hold a member that sentence does not govern.")
    _expect(all(isinstance(v, int) and not isinstance(v, bool) and v == 0
                for v in seeds.values()),
            f"every member of meta.seeds is the integer 0 section 10 fixes 'everywhere, in "
            f"Python and in R', got {seeds}")
    # The DECLARE this module reads is the value `build_params` publishes and the value the
    # FARM_FINGERPRINT consumes.  Asserted against the DAG's own text, because reading the
    # right constant out of the wrong statement would pass every check above.
    build_sql = (Path(__file__).resolve().parent / BUILD_SQL_NAME).read_text(encoding="utf-8")
    _expect(re.search(r"sampling_salt\s+AS sampling_salt", build_sql) is not None,
            "build_all.sql's build_params stage publishes `sampling_salt AS sampling_salt`, "
            "which is the column DAG-SCHEMA.md documents and this module's value stands for")
    _expect("(SELECT sampling_salt FROM p)" in build_sql,
            "build_all.sql's risk-set ordering reads the salt out of build_params inside its "
            "FARM_FINGERPRINT, which is what makes the salt a reproducibility input at all")
    checks += 7

    # ---- and the four refusals, one per way the defect could come back.
    def _with_meta(**changes: Any) -> dict[str, Any]:
        payload = fixture_payload()
        meta = dict(payload["meta"])
        meta.update(changes)
        payload["meta"] = meta
        return payload

    _expect_refusal(lambda: render_bundle(_with_meta(sampling_salt=20260825)),
                    "It is the STRING the DAG publishes",
                    "the fabricated integer this field used to carry")
    _expect_refusal(lambda: render_bundle(_with_meta(sampling_salt=declared_salt + "x")),
                    "a different DAG than the one in",
                    "a salt that is a string and is not the DAG's")
    _expect_refusal(
        lambda: render_bundle(_with_meta(
            seeds={"python": 0, "numpy": 0, "bootstrap": 0, "monte_carlo": 0,
                   "farm_fingerprint": 20260825})),
        "the sampling SALT filed as a seed",
        "the salt filed back under seeds, which is where it was")
    _expect_refusal(lambda: render_bundle(_with_meta(seeds={"python": "0"})),
                    "which is not an integer",
                    "a member of meta.seeds that is not a seed")
    checks += 4

    # ---- the reader itself, over synthetic SQL, so a DECLARE that stops matching is a
    #      refusal and never a silent fallback to a remembered value.
    _expect(dag_sampling_salt("DECLARE sampling_salt STRING DEFAULT 'a-salt';") == "a-salt",
            "the DECLARE reader reads the value out of the statement")
    _expect_refusal(lambda: dag_sampling_salt("DECLARE seed INT64 DEFAULT 0;"),
                    "declares the sampling salt 0 time(s)",
                    "a DAG that no longer declares the salt in the form this module reads")
    _expect_refusal(lambda: dag_sampling_salt(
        "DECLARE sampling_salt STRING DEFAULT 'a';\n"
        "DECLARE sampling_salt STRING DEFAULT 'b';"),
        "declares the sampling salt 2 time(s)",
        "a DAG declaring the salt twice, where no reader can say which one sampled")
    _expect_refusal(lambda: dag_sampling_salt("DECLARE sampling_salt STRING DEFAULT '';"),
                    "empty sampling salt",
                    "a DAG declaring an empty salt")
    checks += 4

    # ============ THE PLAN LOCK: ONE HASH, ONE DATE, ONE LOG, ALL FROM ONE READ ============
    # The hash was read live from `PLAN-HASH.txt` and the date beside it was a literal in
    # `fixture_payload`, so the two drifted apart at the next re-lock: the bundle carried
    # plan v1.5's hash beside v1.3's lock timestamp and the rendered Methods printed the
    # mismatched pair verbatim.  A hash says WHICH DOCUMENT and only the date says WHICH
    # LOCK of it, so the pair is only ever true of itself and is now read as one record.
    _expect(plan_hash_fields("sha256: abc\nlocked: 2026-08-28T00:39:48Z\n")
            == {"sha256": "abc", "locked": "2026-08-28T00:39:48Z"},
            "PLAN-HASH.txt is read as a record, and `locked` keeps its own two colons")
    root_for_plan = _repo_root()
    if root_for_plan is not None:
        stamped = plan_hash_fields(
            (root_for_plan / PLAN_HASH_RELATIVE_PATH).read_text(encoding="utf-8"))
        plan_block = rendered_results["meta"]["analysis_plan"]
        _expect(plan_block["sha256"] == stamped["sha256"]
                and plan_block["locked_utc"] == stamped["locked"],
                "the bundle cites the hash AND the date of the same lock of the same file")
        _expect(PLAN_LOCK_STAMP.fullmatch(plan_block["locked_utc"]) is not None,
                "the cited lock date is the stamp lock_plan.py writes")
        # The log is the authority on how many times the plan has moved, and the Methods
        # cite any amendment, so an empty array beside a populated log reports a document
        # that has never been amended.
        logged = plan_amendment_entries(
            (root_for_plan / PLAN_RELATIVE_PATH).read_text(encoding="utf-8"))
        _expect(len(plan_block["amendments"]) == len(logged) >= 1,
                "meta.analysis_plan.amendments carries one entry per row of section 13")
        _expect(all(re.fullmatch(r"[0-9a-f]{64}", a["superseded_sha256"])
                    and a["n"] == i and a["utc"] and a["reason"]
                    for i, a in enumerate(plan_block["amendments"], start=1)),
                "every amendment carries its ordinal, its date, its reason and the "
                "SUPERSEDED hash section 13 records")
        checks += 4
    # A `PLAN-HASH.txt` that answers which document and not which lock is a refusal, not a
    # fallback to a remembered date: falling back is precisely how the pair separated.
    with tempfile.TemporaryDirectory() as tmp:
        half = Path(tmp)
        (half / "prespecification").mkdir()
        (half / PLAN_HASH_RELATIVE_PATH).write_text(f"sha256: {'a' * 64}\n", "utf-8")
        _expect_refusal(lambda: _plan_lock_from_tree(half),
                        "no `locked:` stamp this module can read",
                        "a plan hash with no lock stamp beside it")
        (half / PLAN_HASH_RELATIVE_PATH).write_text(
            f"sha256: {'a' * 64}\nlocked: yesterday\n", "utf-8")
        _expect_refusal(lambda: _plan_lock_from_tree(half),
                        "no `locked:` stamp this module can read",
                        "a lock stamp that is not the form lock_plan.py writes")
        checks += 2

    # ========== THE `debt.by_group` PARTITION, IN EVERY COUNT COLUMN OF THE BLOCK ==========
    # The four group rows sum to the `All groups` row in every count column Table 2 prints,
    # so one suppressed member is recoverable by subtracting the other three from the total.
    # Only `share_zero_debt` knew that, in a hand-written copy of the rule inside
    # `_render_debt`; `n` and `n_complete_windows` were declared nowhere and a lone
    # suppressed member exported clean through all thirteen checks.  The partition is now a
    # property of the block, derived from its own shape and applied to every count column,
    # so these cases are about the SEAM and not about the two columns that exist today.
    _expect(by_group_member_rows(base["debt"]["by_group"], where="t") == (0, 1, 2, 3),
            "the members are the entries whose slug is not all_groups")
    _expect(by_group_member_rows(
        [{"slug": "lumbar_fusion"}, {"slug": ALL_GROUPS_SLUG}], where="t") == (),
        "one member and its own total partition nothing, so nothing is declared")
    # AND THE `single_group` COLLAPSE RENDERS, which the hand-written copy of this rule did
    # not: with one member below the floor it took `candidates[0]` off an empty list and
    # raised IndexError, so the one collapse level the ladder reaches when the strata are
    # thinnest would have taken the export down with a traceback instead of a refusal.
    collapsed = fixture_payload()
    collapsed["debt"]["by_group"] = [
        dict(collapsed["debt"]["by_group"][3], zero_debt_true_n=18),
        collapsed["debt"]["by_group"][4],
    ]
    single = _render_debt(collapsed, SuppressionLog())
    _expect(is_node_suppressed(single["by_group"][0]["share_zero_debt"])
            and not is_node_suppressed(single["by_group"][1]["share_zero_debt"]),
            "at single_group the lone member is hidden on its own size and forces nothing")
    checks += 1
    _expect_refusal(
        lambda: by_group_member_rows([{"slug": "a"}, {"slug": "b"}], where="debt.by_group"),
        "has no partition to derive",
        "a by-group block with no pooled total")
    _expect_refusal(
        lambda: by_group_member_rows(
            [{"slug": ALL_GROUPS_SLUG}, {"slug": ALL_GROUPS_SLUG}], where="debt.by_group"),
        "has no partition to derive",
        "a by-group block with two pooled totals")
    table2_declarations = build_table2_frame(rendered_results)[1]
    _expect(set(dict(table2_declarations["row_partitions"]))
            == {column for _k, _s, column in DEBT_BY_GROUP_COUNT_COLUMNS}
            == set(table2_declarations["composite_count_columns"]),
            "every count column of the block is declared as a row partition, not some of them")
    checks += 5
    # EVERY count column refuses, and the refusal NAMES the column, so a column added to
    # `DEBT_BY_GROUP_COUNT_COLUMNS` is covered here without this loop being edited.
    for _key, source, column in DEBT_BY_GROUP_COUNT_COLUMNS:
        lone = fixture_payload()
        lone["debt"]["by_group"][0] = dict(lone["debt"]["by_group"][0], **{source: 18})
        with tempfile.TemporaryDirectory() as tmp:
            _expect_refusal(
                lambda p=lone, t=tmp: export_bundle(
                    Path(t) / "results", p, compare_registry_to_previous=False),
                "recoverable by subtraction",
                f"one group below the floor in {column!r}")
            _expect_refusal(
                lambda p=lone, t=tmp: export_bundle(
                    Path(t) / "results", p, compare_registry_to_previous=False),
                repr(column),
                f"the refusal for {column!r} names the column it is about")
        checks += 2
    # And a payload with NO suppressed member still exports, so the declaration refuses the
    # recoverable case and not the ordinary one.
    with tempfile.TemporaryDirectory() as tmp:
        clean = export_bundle(Path(tmp) / "results", fixture_payload(),
                              compare_registry_to_previous=False)
        _expect(len(clean["rows"]) == len(BUNDLE_FILES),
                "a by-group block with no suppressed member exports all sixteen files")
        checks += 1
    # TWO suppressed members are not recoverable and are not refused, which is the other half
    # of the rule: the class is "exactly one", never "any".
    with tempfile.TemporaryDirectory() as tmp:
        pair = fixture_payload()
        for row in (0, 1):
            pair["debt"]["by_group"][row] = dict(
                pair["debt"]["by_group"][row], true_complete_windows=18)
        two_hidden = export_bundle(Path(tmp) / "results", pair,
                                   compare_registry_to_previous=False)
        column = next(c for k, _s, c in DEBT_BY_GROUP_COUNT_COLUMNS
                      if k == "n_complete_windows")
        cells = list(pd.read_csv(
            Path(two_hidden["root"]) / "tables-csv/table2_adjusted_debt.csv",
            dtype=str)[column])
        _expect(sum(1 for cell in cells if _cell_is_hidden(cell)) == 2,
                "two suppressed members are not recoverable and are written as they are")
        checks += 1

    # THE SAME OMISSION, FOUND IN THE ONE OTHER BLOCK THAT HAD IT.  The matched-set-size
    # rows partition a total in BOTH count columns -- a matched set has one size and a case
    # belongs to one set -- and only `n_sets` was declared, so a lone suppressed `n_cases`
    # was recoverable by subtraction from the analyzable event count rung 19 discloses.
    sized_rows = [
        {"set_size": "1", "n_sets": "40", "n_cases": "40", "share_of_sets": "40%"},
        {"set_size": "2", "n_sets": "40", "n_cases": _suppression_sentence(
            "cell_below_threshold"), "share_of_sets": "40%"},
        {"set_size": "3", "n_sets": "20", "n_cases": "20", "share_of_sets": "20%"},
    ]
    sized_frame, sized_declarations = build_ledger_matched_sets_frame(sized_rows)
    _expect(set(dict(sized_declarations["row_partitions"])) == {"n_sets", "n_cases"},
            "both count columns of the matched-set ledger are declared as row partitions")
    _expect_refusal(
        lambda: _gate_probe(
            sized_frame, relative_path="ledgers-csv/ledger_matched_set_sizes.csv",
            kind="table-csv", count_cols=sized_declarations["count_cols"],
            percentage_columns=sized_declarations["percentage_columns"],
            row_partitions=sized_declarations["row_partitions"]),
        "recoverable by subtraction",
        "one suppressed n_cases across the matched-set sizes")
    checks += 2

    # ------------------------------- a tipping point that never crosses is a FINDING
    no_crossing = fixture_payload()
    # 05 returns `None` for a coordinate that does not exist, beside the flag that says so.
    no_crossing["debt"]["delta_shift"] = dict(
        no_crossing["debt"]["delta_shift"], crossed_within_grid=False,
        interval_crossed_within_grid=False, grid_extended=True,
        tipping_point_point_estimate=None, tipping_point_interval=None,
        no_crossing_display=LABELS["no_crossing_within_range"])
    crossed_results, _s3, crossed_log = render_bundle(no_crossing)
    shift = crossed_results["debt"]["delta_shift"]
    for key in ("tipping_point_point_estimate", "tipping_point_interval"):
        node = shift[key]
        _expect(is_node_suppressed(node)
                and node["reason"] == "no_crossing_within_range",
                f"{key} must carry the no-crossing reason and no number")
        _expect(not any(k in node for k in ("est", "lo", "hi")),
                f"{key} must carry no numeric key when it did not cross")
        checks += 2
    _expect(any(e["rule"] == "no crossing" for e in crossed_log.entries),
            "a no-crossing node is filed in suppressed.entries under its own rule")
    _expect(crossed_results["suppressed"]["n_entries"]
            == len(crossed_results["suppressed"]["entries"]),
            "n_entries still ties out when a value-free node is filed")
    # A three-tuple is the pre-1.6.0 estimate shape and its interval does not exist.
    interval_shaped = fixture_payload()
    interval_shaped["debt"]["delta_shift"] = dict(
        interval_shaped["debt"]["delta_shift"],
        tipping_point_point_estimate=(1.25, 0.9, 1.75))
    _expect_refusal(lambda: render_bundle(interval_shaped),
                    "arrived as a 3-tuple",
                    "a tipping point supplied as an interval")
    # THE TWO COORDINATES ARE DECIDED SEPARATELY.  05 returns a flag for each and says the
    # second can fail to cross when the first one crossed; the reverse happens too, and a
    # real synthetic run produces exactly it: no point crossing inside the range, and a
    # confidence band that first includes zero at delta 3.5.  Suppressing both off one flag
    # would discard a computed coordinate.
    #
    # THE GRID IS EXTENDED TOO, and it has to be.  `grid_extended` says 3.11's extension rule
    # fired, and 05 emits a row for every delta it walked, so a payload claiming a crossing
    # at 3.5 over a grid that stops at 2.0 is one no run can produce.  This case used to
    # claim exactly that and nothing noticed, because the coordinate was never checked
    # against the grid it is supposed to be read off.
    split = fixture_payload()
    split["debt"]["delta_shift"] = dict(
        split["debt"]["delta_shift"], crossed_within_grid=False,
        interval_crossed_within_grid=True, grid_extended=True,
        tipping_point_point_estimate=None, tipping_point_interval=3.5,
        grid=_extended_delta_grid_rows(split["debt"]["delta_shift"]["grid"]))
    split_results, _s4, _log4 = render_bundle(split)
    split_shift = split_results["debt"]["delta_shift"]
    _expect(is_node_suppressed(split_shift["tipping_point_point_estimate"])
            and split_shift["tipping_point_point_estimate"]["reason"]
            == "no_crossing_within_range",
            "the point estimate is suppressed when it did not cross")
    _expect(not is_node_suppressed(split_shift["tipping_point_interval"])
            and split_shift["tipping_point_interval"]["est"] == 3.5
            and split_shift["tipping_point_interval"]["display_ci"] == "",
            "and the interval coordinate is reported as a bound, because it did cross")
    # A coordinate beside a flag that denies it is a contradiction, not a preference.
    contradiction = fixture_payload()
    contradiction["debt"]["delta_shift"] = dict(
        contradiction["debt"]["delta_shift"], crossed_within_grid=False)
    _expect_refusal(lambda: render_bundle(contradiction),
                    "will not print a tipping point the analysis says does not exist",
                    "a coordinate beside a flag that denies it")
    checks += 6

    # ------------- A TIPPING POINT IS A GRID COORDINATE, and now that is a refusal
    # This module said so twice in prose and asserted it nowhere, so a tipping point of 1.25
    # -- a value 3.11's grid cannot produce -- travelled the whole delivery chain in the
    # fixture beside a `grid` array that did not contain it either.  05 walks the grid and
    # returns the smallest delta at which a condition first holds, so it cannot return
    # anything else; a value between two coordinates is a payload defect, and printing it
    # would put a Methods sentence on a shift the analysis never evaluated.
    _expect(1.25 not in DELTA_SHIFT_GRID_EXTENDED,
            "1.25 is not a coordinate ANALYSIS-PLAN.md 3.11's grid can produce")
    _expect(DELTA_SHIFT_GRID_EXTENDED[-1] == DELTA_SHIFT_EXTENSION_LAST
            and len(DELTA_SHIFT_GRID_EXTENDED) == len(DELTA_SHIFT_GRID) + 4,
            "3.11 extends the grid in 0.5 increments to 4.0 and no further")
    for key in ("tipping_point_point_estimate", "tipping_point_interval"):
        off_grid = fixture_payload()
        off_grid["debt"]["delta_shift"] = dict(
            off_grid["debt"]["delta_shift"], **{key: 1.25})
        _expect_refusal(lambda p=off_grid: render_bundle(p),
                        "A tipping point is a GRID COORDINATE",
                        f"{key} between two grid coordinates")
        # And a coordinate the LOCKED grid holds but this run did not walk is refused too:
        # 3.11's extension rule fires or it does not, and a crossing at 3.0 reported over a
        # grid that stops at 2.0 is a crossing nothing computed.
        unwalked = fixture_payload()
        unwalked["debt"]["delta_shift"] = dict(
            unwalked["debt"]["delta_shift"], **{key: 3.0})
        _expect_refusal(lambda p=unwalked: render_bundle(p),
                        "A tipping point is a GRID COORDINATE",
                        f"{key} at a locked coordinate this run did not walk")
        checks += 2
    # The grid itself is held to 3.11 as well, so a finer grid somebody found more
    # informative is refused before either coordinate is read off it.
    finer = fixture_payload()
    finer["debt"]["delta_shift"] = dict(
        finer["debt"]["delta_shift"],
        grid=[dict(point, delta=0.6) if point["delta"] == 0.5 else dict(point)
              for point in finer["debt"]["delta_shift"]["grid"]])
    _expect_refusal(lambda: render_bundle(finer),
                    "does not prespecify",
                    "a delta grid finer than the one the plan locked")
    # THE FIXTURE'S OWN COORDINATES ARE ON THE GRID, which is the assertion the fixture
    # failed before this landed.
    fixture_shift = rendered_results["debt"]["delta_shift"]
    for key in ("tipping_point_point_estimate", "tipping_point_interval"):
        node = fixture_shift[key]
        _expect(not is_node_suppressed(node)
                and any(math.isclose(float(node["est"]), d, abs_tol=1e-9)
                        for d in DELTA_SHIFT_GRID),
                f"the fixture's {key} must be a coordinate of 3.11's locked grid")
        checks += 1
    _expect([float(p["delta"]) for p in fixture_shift["grid"]] == list(DELTA_SHIFT_GRID),
            "the fixture walks the whole locked grid, in order, as 05 does")
    checks += 4

    # ---------------- THE A-THROUGH-F GATE LEDGER IS MONOTONE NON-INCREASING
    # Each stage of 7.9 is a subset of the one above it, and the fixture shipped a stage B of
    # 420 beneath a stage A of 340 with all thirteen checks passing over it.  Asserted on
    # both render paths, because a real run's ledger arrives already rendered from 06 and a
    # check that ran only on the raw-count path would be on for the fixture alone.
    rising = fixture_payload()
    rising["gate"]["stages"]["B"] = {"total": rising["gate"]["stages"]["A"]["total"] + 80}
    _expect_refusal(lambda: render_bundle(rising),
                    "the feasibility gate ledger rises",
                    "a gate ledger whose stage B exceeds its stage A")
    rising_adopted = fixture_payload()
    rising_adopted["gate"] = json.loads(json.dumps(rendered_results["gate"]))
    rising_adopted["gate"]["stages"][2]["total"] = count_node(9999)
    _expect_refusal(lambda: render_bundle(rising_adopted),
                    "the feasibility gate ledger rises",
                    "a pre-rendered gate ledger that rises at stage C")
    # A suppressed total is carried ACROSS rather than read as a break in the chain: the
    # fixture's stage E is below the floor and stage F beneath it still has to be bounded by
    # the last disclosed stage above.
    ledger_stages = rendered_results["gate"]["stages"]
    disclosed = [int(s["total"]["n"]) for s in ledger_stages
                 if not is_node_suppressed(s["total"])]
    _expect(any(is_node_suppressed(s["total"]) for s in ledger_stages),
            "the fixture exercises the ledger check across a suppressed stage")
    _expect(disclosed == sorted(disclosed, reverse=True),
            "the fixture's own disclosed ledger does not rise")
    checks += 4

    # ============================ STROBE ITEM 16(a), CONTRACT 1.9.0 ======================
    # The unadjusted contrast beside the adjusted one, its model, and the three footer rows.
    plain_contrasts = rendered_results["debt"]["unadjusted_contrasts"]
    plain_model = rendered_results["debt"]["unadjusted_model"]
    adjusted_contrasts = rendered_results["debt"]["contrasts"]

    # THE SAME FIVE SLUGS AND NO OTHERS, so a consumer holding a contrast slug reaches both
    # estimates without a second vocabulary.
    _expect(set(plain_contrasts) == set(adjusted_contrasts) == set(CONTRAST_SLUGS),
            "debt.unadjusted_contrasts must carry 3.5's five contrast slugs and no others")
    # 7.3 DOES NOT GROW.  An unadjusted contrast is the same contrast, so it reuses the
    # adjusted contrast's own label rather than inventing five more.
    _expect(all(plain_contrasts[slug]["display_label"]
                == adjusted_contrasts[slug]["display_label"] == LABELS[slug]
                for slug in CONTRAST_SLUGS),
            "an unadjusted contrast reuses the adjusted contrast's 7.3 label")
    _expect(all(plain_contrasts[slug]["estimate"]["unit"] == "activity_days"
                for slug in CONTRAST_SLUGS),
            "every unadjusted contrast is on the scale the estimand is defined on")
    # ONE PRIMARY, AND THE SAME SLUG IN BOTH.  4.3 permits exactly one `true` in the forest
    # file for the same reason: two primaries is two studies.
    # 3.5 names `fusion_vs_decompression` the primary contrast and 5.3 row 13 names it again
    # in its source key, so it is the slug both blocks must agree on.
    primary_slug = "fusion_vs_decompression"
    _expect([s for s, e in plain_contrasts.items() if e["is_primary"]]
            == [s for s, e in adjusted_contrasts.items() if e["is_primary"]]
            == [primary_slug],
            "the unadjusted primary is the slug that is primary in debt.contrasts")
    # IT CARRIES ITS OWN INTERVAL AND ITS OWN N, never the adjusted contrast's.  The fixture
    # separates them on purpose, so a renderer that reached for the wrong one is visible.
    _expect(plain_contrasts[primary_slug]["estimate"]["display"]
            != adjusted_contrasts[primary_slug]["estimate"]["display"],
            "the unadjusted contrast carries its own interval, not the adjusted one's")
    # `absolute_scale` HAS NO UNADJUSTED TWIN AND THE ABSENCE IS A DECISION.  3.5: the
    # absolute-scale model must carry a spline in log baseline steps, so a covariate-free
    # version of it would still have to carry a covariate and would not be the same
    # estimator with the covariate set removed.
    _expect("unadjusted_absolute_scale" not in rendered_results["debt"]
            and all("unadjusted" not in key
                    for key in rendered_results["debt"]["absolute_scale"]),
            "absolute_scale has no unadjusted twin and 3.5 says why")
    checks += 6

    # THE BOOLEAN, WHICH IS THE ONE FIELD A METHODS SECTION CANNOT AFFORD TO LOSE.  It is
    # carried across, never decided here, and it is a real bool rather than a truthy string.
    _expect(plain_model["prespecified"] is False,
            "debt.unadjusted_model.prespecified is false at plan version 1.5, and declared")
    _expect(plain_model["mandate_display"] and "16(a)" in plain_model["mandate_display"],
            "the mandate sentence names the reporting item that requires the quantity")
    _expect(plain_model["definition_display"]
            and "removed" in plain_model["definition_display"],
            "the definition sentence says which terms were removed")
    # A PERCENTAGE NODE FROM THE TWO RAW COUNTS, the way meta.estimator's is built.
    rate = plain_model["bootstrap_failure_rate"]
    _expect(rate["num"] == int(round20(FIXTURE_UNADJUSTED_MODEL["true_bootstrap_failed"]))
            and rate["den"] == FIXTURE_UNADJUSTED_MODEL["true_bootstrap_attempted"]
            and rate["pct"] == _percent_integer(rate["num"], rate["den"]),
            "bootstrap_failure_rate is the rounded numerator over the rounded denominator")
    # THE RUNG DISPLAY IS LOOKED UP, NOT TRANSCRIBED.  7.7 sends the printed string to the
    # label table, so a payload carrying a stale display does not put it in the bundle.
    stale_display = fixture_payload()
    stale_display["debt"]["unadjusted_model"] = dict(
        stale_display["debt"]["unadjusted_model"], rung_display="Whatever 05 last called it")
    stale_results, _s6, _log6 = render_bundle(stale_display)
    _expect(stale_results["debt"]["unadjusted_model"]["rung_display"]
            == LABELS["r_ordered_beta_glmm"],
            "the unadjusted rung's display comes from the label table, not from the payload")
    checks += 5

    # NOTHING BREAKS BY ABSENCE, WHICH IS WHY BOTH KEYS ARE ASSERTED RATHER THAN DEFAULTED.
    # This module reads the debt block by named key, so an 05 that had not picked up 1.9.0
    # would have both keys silently dropped and the bundle would come out one reporting item
    # short with nothing red anywhere.  A partial adoption must halt.
    for absent_key in ("unadjusted_contrasts", "unadjusted_model"):
        stale = fixture_payload()
        stale["debt"] = {k: v for k, v in stale["debt"].items() if k != absent_key}
        _expect_refusal(lambda p=stale: render_bundle(p),
                        "required since 1.9.0 for STROBE item 16(a)",
                        f"a debt payload with no {absent_key}")
        checks += 1
    for absent_field in ("prespecified", "rung_note_display", "true_bootstrap_attempted"):
        stale = fixture_payload()
        stale["debt"]["unadjusted_model"] = {
            k: v for k, v in stale["debt"]["unadjusted_model"].items() if k != absent_field}
        _expect_refusal(lambda p=stale: render_bundle(p),
                        "debt.unadjusted_model is missing",
                        f"an unadjusted model with no {absent_field}")
        checks += 1

    # ITS OWN N AGAINST THE FLOOR.  Nothing about a guideline-mandated quantity is exempt
    # from the ordinary suppression, and the entry is filed under the path 3.5 names.
    small = fixture_payload()
    small["debt"]["unadjusted_contrasts"] = {
        slug: (dict(spec, true_n_compared=14, true_n=14)
               if slug == "fusion_vs_decompression_cervical" else dict(spec))
        for slug, spec in FIXTURE_UNADJUSTED_CONTRASTS.items()
    }
    small_results, _s7, small_log = render_bundle(small)
    hidden_node = (small_results["debt"]["unadjusted_contrasts"]
                   ["fusion_vs_decompression_cervical"]["estimate"])
    _expect(is_node_suppressed(hidden_node)
            and hidden_node["reason"] == "contributing_n_below_threshold",
            "an unadjusted contrast below the floor is suppressed on its own n")
    _expect(any(e["path"] == ("debt.unadjusted_contrasts."
                              "fusion_vs_decompression_cervical.estimate")
                and e["kind"] == "estimate" for e in small_log.entries),
            "and the suppression is filed under the path 3.5 names")
    # THE FAILURE NEVER PROPAGATES.  The prespecified contrast beside it is untouched: a
    # guideline-mandated companion that could unseat the prespecified estimand would be a
    # worse defect than the gap it closes.
    _expect(not is_node_suppressed(small_results["debt"]["contrasts"]
                                   ["fusion_vs_decompression_cervical"]["estimate"]),
            "a suppressed unadjusted contrast does not suppress the adjusted one beside it")
    # A REFUSED INTERVAL IS A BOUND, NOT A SUPPRESSION, exactly as it is for the adjusted
    # contrast.  The bootstrap failed; the estimate did not.
    no_interval = fixture_payload()
    no_interval["debt"]["unadjusted_contrasts"] = dict(
        FIXTURE_UNADJUSTED_CONTRASTS,
        fusion_vs_decompression=dict(FIXTURE_UNADJUSTED_CONTRASTS["fusion_vs_decompression"],
                                     estimate=(5.8, float("nan"), float("nan"))))
    bound_results, _s8, _log8 = render_bundle(no_interval)
    bound_estimate = (bound_results["debt"]["unadjusted_contrasts"]
                      ["fusion_vs_decompression"]["estimate"])
    _expect(not is_node_suppressed(bound_estimate)
            and bound_estimate["display_ci"] == ""
            and bound_estimate["est"] == bound_estimate["lo"] == bound_estimate["hi"] == 5.8,
            "an unadjusted contrast whose interval was refused is a bound, not a suppression")
    checks += 4

    # A FIT THAT FAILED ENTIRELY.  3.5's legal shape: an empty object, a null rung, and a
    # reason of 7.5.  5.3 then has rows 13 and 15 print that sentence where the value would
    # sit, which is the ordinary suppression behaviour of every other footer row.
    failed = fixture_payload()
    failed["debt"]["unadjusted_contrasts"] = {}
    failed["debt"]["unadjusted_model"] = dict(
        FIXTURE_UNADJUSTED_MODEL, rung_slug=None, rung_display=None, rung_index=None,
        rung_matches_adjusted=None, not_estimable_reason="not_estimable_convergence",
        rung_note_display=("The unadjusted fit did not return an estimate, so the contrast "
                           "beside the adjusted one is not estimable and the reason is "
                           "printed in its place."))
    failed_results, failed_specs, _log9 = render_bundle(failed)
    _expect(failed_results["debt"]["unadjusted_contrasts"] == {}
            and failed_results["debt"]["unadjusted_model"]["rung_display"] is None,
            "a wholly failed unadjusted fit renders as an empty object and a null rung")
    failed_footer = next(f for name, f, _d in failed_specs
                         if name == "tables-csv/table2_adjusted_debt_footer.csv")
    sentence = LABELS["not_estimable_convergence"]
    _expect(list(failed_footer["Value"])[12] == sentence
            and list(failed_footer["Value"])[14] == sentence,
            "footer rows 13 and 15 print the 7.5 sentence when the fit returned nothing")
    _expect(len(failed_footer) == len(TABLE2_FOOTER_ROWS),
            "and the footer is still its full row list, with nothing omitted")
    # The prespecified estimand beside it is untouched, at every one of the first twelve rows.
    base_footer = next(f for name, f, _d in _specs
                       if name == "tables-csv/table2_adjusted_debt_footer.csv")
    _expect(list(failed_footer["Value"])[:12] == list(base_footer["Value"])[:12],
            "a failed unadjusted fit changes nothing above row 13")
    # A fit that returned nothing and names no reason has nothing to print, and an empty
    # footer cell reads as "not applicable", which this file has no row for.
    silent = fixture_payload()
    silent["debt"]["unadjusted_contrasts"] = {}
    silent["debt"]["unadjusted_model"] = dict(
        FIXTURE_UNADJUSTED_MODEL, rung_slug=None, rung_display=None, rung_index=None,
        rung_matches_adjusted=None, not_estimable_reason=None)
    _expect_refusal(lambda: render_bundle(silent),
                    "reached no rung and names no reason",
                    "a failed unadjusted fit that names no 7.5 reason")
    checks += 5

    # THE RUNG IS CHECKED, NOT COPIED.  `rung_matches_adjusted` is a reportable fact and
    # `false` is not a failure, so a flag disagreeing with the two rung indices is a
    # contradiction between two blocks only this module sees together.
    wrong_pair = fixture_payload()
    wrong_pair["debt"]["unadjusted_model"] = dict(
        FIXTURE_UNADJUSTED_MODEL, rung_slug="py_fractional_logit_gee", rung_index=1)
    _expect_refusal(lambda: render_bundle(wrong_pair),
                    "3.1.1's ladder does not pair",
                    "a rung slug that is not its index's")
    wrong_flag = fixture_payload()
    wrong_flag["debt"]["unadjusted_model"] = dict(
        FIXTURE_UNADJUSTED_MODEL, rung_slug="py_fractional_logit_gee", rung_index=3,
        rung_matches_adjusted=True)
    _expect_refusal(lambda: render_bundle(wrong_flag),
                    "so the flag is checked, not copied",
                    "a rung_matches_adjusted that the two indices contradict")
    # AND A DIFFERING RUNG IS REPORTED RATHER THAN SMOOTHED AWAY.  `false` is a reportable
    # fact: the gap between the two contrasts then carries a change of model family as well.
    differing = fixture_payload()
    differing["debt"]["unadjusted_model"] = dict(
        FIXTURE_UNADJUSTED_MODEL, rung_slug="py_fractional_logit_gee", rung_index=3,
        rung_matches_adjusted=False,
        rung_note_display=("The unadjusted fit reached a different rung of the model family "
                           "ladder from the adjusted fit, so the gap between the two "
                           "contrasts carries a change of model family as well as the "
                           "covariate set, and is read accordingly."))
    differing_results, differing_specs, _log10 = render_bundle(differing)
    differing_model = differing_results["debt"]["unadjusted_model"]
    _expect(differing_model["rung_matches_adjusted"] is False
            and differing_model["rung_display"] == LABELS["py_fractional_logit_gee"],
            "a differing rung is reported with its own display, not forced to match")
    differing_footer = next(f for name, f, _d in differing_specs
                            if name == "tables-csv/table2_adjusted_debt_footer.csv")
    _expect(list(differing_footer["Value"])[14] != list(differing_footer["Value"])[1],
            "footer row 15 prints the unadjusted rung beside row 2's adjusted one, so two "
            "fits landing on two rungs is visible on the page instead of buried")
    checks += 4

    # THE FOOTER IS FIFTEEN ROWS AND ROWS 1 TO 12 DID NOT MOVE.  5.3 appends 13, 14 and 15
    # rather than inserting them beside row 9, because a renumbering is a change every
    # assertion in this module, in the fixture and in `local/tables.py` would have to absorb.
    _expect(len(TABLE2_FOOTER_ROWS) == 15 and len(base_footer) == 15,
            "the Table 2 footer is 5.3's fifteen rows as of contract 1.9.0")
    _expect([item for item, _key in TABLE2_FOOTER_ROWS][12:]
            == ["Unadjusted primary contrast", "Unadjusted contrast, what it removes",
                "Unadjusted contrast, model rung reached"],
            "rows 13 to 15 are 5.3's three STROBE item 16(a) rows, appended")
    _expect([key for _item, key in TABLE2_FOOTER_ROWS][12:]
            == ["debt.unadjusted_contrasts.fusion_vs_decompression.estimate",
                "debt.unadjusted_model.definition_display",
                "debt.unadjusted_model.rung_display"],
            "and each traces to the source key 5.3 names")
    _expect(list(base_footer["row_order"]) == [str(i) for i in range(1, 16)]
            and list(base_footer["Source key"])[11]
            == "denominators.analytic.display_n_equals",
            "row_order is the contiguous 1 to 15 and row 12 is where it was at 1.8.0")
    # THE NEAR-UNIQUE MARGIN, MEASURED RATHER THAN ASSUMED.  Three more rows narrow 10.2's
    # margin on this file from eight to five, and it is now the second-smallest in the
    # bundle.  The test is strictly greater than the floor, so a file AT the floor is one row
    # from arming; this one is five rows under it and every column would trip together.
    _expect(len(TABLE2_FOOTER_ROWS) <= disclosure.NEAR_UNIQUE_MIN_ROWS,
            f"the Table 2 footer is {len(TABLE2_FOOTER_ROWS)} rows against a near-unique "
            f"floor of {disclosure.NEAR_UNIQUE_MIN_ROWS}: 5.3's list has grown past it and "
            f"`Footer item`, `Value`, `Source key` and `row_order` would all trip together")
    _expect(disclosure.NEAR_UNIQUE_MIN_ROWS - len(TABLE2_FOOTER_ROWS) == 5,
            "10.2 records the margin as five at 1.9.0, down from eight at 1.8.0")
    checks += 6

    # ---- non-finite values arrive from 05 and are SUPPRESSED here, which is 05's own
    # stated expectation: "NON-FINITE MEMBERS PASS THROUGH RATHER THAN BEING REPAIRED ...
    # 07_export.py at the boundary suppresses on exactly that".
    nan = float("nan")
    _expect(is_node_suppressed(estimate_from_triple((nan, 1.0, 2.0), "activity_days")),
            "an estimate whose point was not computed is suppressed, not printed as NaN")
    partial = estimate_from_triple((4.4, nan, nan), "activity_days")
    _expect(not is_node_suppressed(partial) and partial["display_ci"] == ""
            and partial["lo"] == partial["hi"] == partial["est"],
            "AN ESTIMATE WITH NO INTERVAL IS A BOUND, not a suppression: the bootstrap "
            "failed, the estimate did not, and reporting it as missing would hide a number "
            "that exists")
    _expect(is_node_suppressed(quantile_from_triple((1.0, nan, 3.0), "activity_days")),
            "a quantile range with a missing quartile has no bound form and is suppressed")
    _expect(is_node_suppressed(scalar_or_suppressed(nan)),
            "a constant that was not computed is suppressed; 3.5 gives a scalar node no "
            "shape for a missing one and the fractional-response rung reports no AIC")
    _expect(scalar_or_suppressed(18420, "18,420")["display"] == "18,420",
            "and a finite one is the ordinary scalar node")
    _expect(pvalue_or_none(None) is None and pvalue_or_none(nan) is None
            and pvalue_or_none(0.5)["display"] == "P = 0.500",
            "a P value that is not defined is null and never a rendered NaN")
    no_aic = fixture_payload()
    no_aic["debt"]["model_fit"] = dict(no_aic["debt"]["model_fit"], aic=nan)
    aic_results, _s5, _log5 = render_bundle(no_aic)
    _expect(is_node_suppressed(aic_results["debt"]["model_fit"]["aic"]),
            "a bundle rendered from a rung with no information criterion still serializes")
    checks += 7

    # ------------------------------------- Table 3 part B follows 3.7's order, not the alphabet
    permitting = fixture_payload()
    permitting["gate"] = json.loads(json.dumps(rendered_results["gate"]))
    permitting["gate"]["tier"] = dict(permitting["gate"]["tier"], index=3,
                                      slug="event_centered_only",
                                      display_label=LABELS["event_centered_only"])
    permitting["gate"]["arm_a"] = {
        "permitted": True,
        "reason_display": rendered_results["gate"]["arm_a"]["reason_display"],
        "estimates": {key: suppressed_node("not_permitted_by_tier")
                      for key in GATE_ESTIMATE_KEYS},
    }
    part_b, _decl = build_table3b_frame(permitting["gate"] and
                                        {"gate": permitting["gate"]})
    _expect(list(part_b["Quantity"])[2:]
            == [LABELS[key] for key in GATE_ESTIMATE_KEYS],
            "Table 3 part B must print the estimate rows in 3.7's order")
    _expect(len(part_b) == 2 + len(GATE_ESTIMATE_KEYS),
            "Table 3 part B must carry one row per declared estimate key")
    short = {"gate": {"tier": permitting["gate"]["tier"],
                      "arm_a": {"permitted": True, "reason_display": "",
                                "estimates": {GATE_ESTIMATE_KEYS[0]:
                                              suppressed_node("not_permitted_by_tier")}}}}
    _expect_refusal(lambda: build_table3b_frame(short),
                    "is missing key(s)",
                    "an estimates block short of a declared key")
    checks += 3

    # ------------------------------------------ Figure 4 and Table 4 at a permitting tier
    plotted_rows, plotted_summary = render_figure4_rows(
        [{"slug": "event_case", "offsets": [
            {"day_relative_to_event": d, "true_contributing": 40 if d < 0 else 14,
             "observed_median": 0.6234, "observed_p25": 0.4412, "observed_p75": 0.8156}
            for d in FIGURE4_OFFSETS]}],
        tier_permits_plot=True)
    _expect(len(plotted_rows) == 44, "figure 4 is 44 rows at every tier")
    _expect(plotted_summary["n_days_plotted_by_series"]
            == {"event_case": 14, "matched_control": 0},
            "only the offsets clearing the floor are plotted, and the count is per series")
    plotted_frame, plotted_decl = build_figure4_frame(plotted_rows)
    _expect(set(plotted_frame["observed_median"]) == {"0.62", FIGURE_SUPPRESSED_TOKEN},
            "a plotted quantile is rounded to two decimals before the frame is built")
    _expect(set(plotted_frame["not_plotted_display"])
            == {"", LABELS["contributing_n_below_threshold"]},
            "at a permitting tier a hidden offset says the contributors were too few, not "
            "that the tier forbade the question")
    # And the same frame passes both gates, which is what exception 5 is for.
    _gate_probe(plotted_frame,
                relative_path="figures-csv/figure4_event_centered_activity.csv",
                **{k: v for k, v in plotted_decl.items()
                   if k in ("kind", "count_cols", "numeric_string_columns",
                            "specification_columns")})
    # TABLE 4 AT A PERMITTING TIER, rendered from the keys 3.7 declares.  The fixture pins
    # tier 4, where Arm A is not permitted and the file is fully determined, so this is the
    # only place the six-key path is exercised at all: every rate cell is read from
    # `gate.arm_a.estimates` and the two count pairs are taken beside the block, because
    # counts are not estimates and 5.7 says so.
    collider_rates = {
        "collider_rate_with_signal": (5.24, 3.91, 6.57),
        "collider_rate_without_signal": (9.12, 7.05, 11.19),
        "collider_rate_ratio_crude": (1.74, 1.28, 2.20),
        "collider_rate_with_signal_standardized": (5.41, 4.02, 6.80),
        "collider_rate_without_signal_standardized": (8.77, 6.71, 10.83),
        "collider_rate_ratio_standardized": (1.62, 1.19, 2.05),
    }
    permitted_estimates = {
        key: suppressed_node("not_permitted_by_tier") for key in GATE_ESTIMATE_KEYS
    } | {
        key: estimate_from_triple(
            triple,
            "rate_ratio" if "ratio" in key else "rate_per_1000_episode_days")
        for key, triple in collider_rates.items()
    }
    permitted_counts = {
        "with_signal": {"episode_days": 7640, "events": 40},
        "without_signal": {"episode_days": 2180, "events": 34},
    }
    table4_permitted = render_table4_rows(
        permitted_estimates, permitted=True, window_counts=permitted_counts)
    _expect(len(table4_permitted) == 3
            and [row["Window group"] for row in table4_permitted]
            == [LABELS[slug] for slug, _c, _s, _k in TABLE4_ROWS],
            "Table 4 at a permitting tier is still 5.7's three prespecified window groups")
    _expect([row["Crude rate per 1,000 episode-days"] for row in table4_permitted]
            == ["5.24 (95% CI 3.91 to 6.57)", "9.12 (95% CI 7.05 to 11.19)",
                "1.74 (95% CI 1.28 to 2.20)"]
            and [row["Standardized rate per 1,000 episode-days"]
                 for row in table4_permitted]
            == ["5.41 (95% CI 4.02 to 6.80)", "8.77 (95% CI 6.71 to 10.83)",
                "1.62 (95% CI 1.19 to 2.05)"],
            "each of the six rate cells reads its own 3.7 key, in 5.7's row order")
    _expect([row["Episode-days at risk"] for row in table4_permitted]
            == ["7,640", "2,180", ""]
            and [row["Acute-care events"] for row in table4_permitted] == ["40", "40", ""],
            "the two count columns are round20-rounded from the payload and empty on the "
            "ratio row, which is the not-applicable convention and not a suppression")
    # A block short of a key refuses BY NAME.  This is 11.4's dated lag made concrete:
    # `06_analysis_gate.py` declares five of 3.7's thirteen keys, so the six collider keys
    # never reach the block and every rate cell of this file has nothing to print.
    _expect_refusal(
        lambda: render_table4_rows(
            {key: suppressed_node("not_permitted_by_tier")
             for key in GATE_ESTIMATE_KEYS[:7]},
            permitted=True, window_counts=permitted_counts),
        "'collider_rate_with_signal_standardized'",
        "Table 4 at a permitting tier with the collider keys absent from the block")
    # And the two count pairs, which 3.7 is the wrong home for and 11.4 has not yet housed.
    _expect_refusal(
        lambda: render_table4_rows(permitted_estimates, permitted=True),
        "Refusing to guess a count in a compliance bundle",
        "Table 4 at a permitting tier with no window-group counts")
    checks += 8

    # ------------------------------------------------- the ladder must close on true integers
    broken = fixture_payload()
    broken["ladder"][10]["n_dropped"] = broken["ladder"][10]["n_dropped"] + 20
    _expect_refusal(lambda: render_bundle(broken),
                    "does not close on the unrounded integers",
                    "an attrition ladder that does not close")
    checks += 1

    # ------------------- A REBUILD THAT RAISES LEAVES THE PREVIOUS BUNDLE BYTE-IDENTICAL
    # The hazard this pins is not hypothetical.  `write_fixture` used to unlink all sixteen
    # files and both manifests and THEN rebuild, so a rebuild that raised part way left the
    # directory EMPTY: a half-landed edit raised `ValueError: too many values to unpack`
    # mid-rebuild and destroyed the fixture, which is the only bundle six local modules can
    # be developed against, and the same writer puts a real Phase 4 run's actual results at
    # the contract path.  So the test does what the accident did -- raises deliberately in
    # the middle of a rebuild -- and asserts that every md5 in the previous bundle is
    # unchanged afterwards.  Asserting the FILES still exist would not catch a rebuild that
    # got half way and left a mixture of two bundles behind, which is why this compares the
    # bytes rather than the listing.
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "results"
        write_fixture(target)
        stamped = tuple(BUNDLE_FILES) + ("MANIFEST.csv", "MANIFEST.md5")
        before = {name: md5_of_bytes((target / name).read_bytes()) for name in stamped}

        def _raises_mid_rebuild(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            """The real failure, at the real point: fifteen CSVs written, `results.json` not."""
            raise ValueError("too many values to unpack (expected 2)")

        restore = globals()["write_results_json"]
        globals()["write_results_json"] = _raises_mid_rebuild
        try:
            write_fixture(target)
        except ValueError:
            pass
        else:
            raise AssertionError("the deliberate mid-rebuild failure did not propagate")
        finally:
            globals()["write_results_json"] = restore
        _expect({name: md5_of_bytes((target / name).read_bytes())
                 for name in stamped} == before,
                "a rebuild that raised part way did not leave the previous bundle "
                "byte-identical")
        _expect(not validate_bundle(target),
                "the bundle a failed rebuild left behind no longer validates")
        _expect([p.name for p in Path(tmp).iterdir()] == ["results"],
                "a failed rebuild left a staging directory beside the bundle")
        checks += 3

        # A SWAP THAT FAILS HALFWAY IS THE SAME HAZARD ONE LEVEL UP.  The first rename moves
        # the previous bundle aside, so a second rename that fails would leave the contract
        # path MISSING, which is the empty directory again by another route.  The swap undoes
        # the first rename instead, and this drives exactly that branch.
        real_rename = os.rename
        renames = {"n": 0}

        def _fail_the_second_rename(source: Any, destination: Any) -> None:
            renames["n"] += 1
            if renames["n"] == 2:
                raise OSError("the swap failed between its two renames")
            return real_rename(source, destination)

        os.rename = _fail_the_second_rename
        try:
            write_fixture(target)
        except OSError:
            pass
        else:
            raise AssertionError("the deliberate swap failure did not propagate")
        finally:
            os.rename = real_rename
        _expect(renames["n"] == 3,
                "the swap did not roll its first rename back after the second one failed")
        _expect({name: md5_of_bytes((target / name).read_bytes())
                 for name in stamped} == before,
                "a swap that failed halfway did not roll the previous bundle back")
        _expect(not validate_bundle(target),
                "the rolled-back bundle no longer validates")
        _expect([p.name for p in Path(tmp).iterdir()] == ["results"],
                "a rolled-back swap left a staging or retired directory behind")
        checks += 4

    # ------------------------------------------------------------------ the fixture, end to end
    with tempfile.TemporaryDirectory() as tmp:
        first = Path(tmp) / "a" / "results"
        second = Path(tmp) / "b" / "results"
        write_fixture(first)
        write_fixture(second)
        problems = validate_bundle(first)
        _expect(not problems, f"the fixture bundle does not validate: {problems}")
        checks += 1
        for name in BUNDLE_FILES:
            if name == "results.json":
                continue
            _expect(filecmp.cmp(first / name, second / name, shallow=False),
                    f"{name} is not byte-identical across two fixture runs")
            checks += 1
        _expect((first / "results.json").read_bytes()
                == (second / "results.json").read_bytes(),
                "the fixture's results.json is not byte-identical across runs")
        _expect((first / "MANIFEST.md5").read_bytes()
                == (second / "MANIFEST.md5").read_bytes(),
                "the fixture's MANIFEST.md5 is not byte-identical across runs")
        checks += 2

        results = json.loads((first / "results.json").read_text(encoding="utf-8"))
        _expect(results["meta"]["manifest_rows"] == 16, "manifest_rows is not 16")
        _expect(len(results["figures"]) == 4 and len(results["tables"]) == 5,
                "3.8 declares four figure keys and five table keys")

        # ------------------------------------------------- the locked exhibit budget
        # THE BUDGET IS THREE FIGURES AND THREE TABLES AND IT IS COUNTED OVER EXHIBITS.
        # Not over the sixteen bundle files, which CLAUDE.md section 2 rule 7 already
        # warns against, and not over the nine block keys either: `tables` carries four
        # primary keys for three primary tables because Table 3 is printed in two parts.
        # These four assertions are the ones a future session will be tempted to relax
        # when a real gap wants a fourth exhibit, which is exactly how this drifted the
        # first time.  The gap goes to the supplement; the budget does not move.
        primary_figures = sorted({
            b["exhibit"] for b in results["figures"].values()
            if b["exhibit_set"] == "primary"})
        primary_tables = sorted({
            b["exhibit"] for b in results["tables"].values()
            if b["exhibit_set"] == "primary"})
        _expect(primary_figures == ["Figure 1", "Figure 2", "Figure 3"],
                f"the primary figure set is {primary_figures}, not three figures")
        _expect(primary_tables == ["Table 1", "Table 2", "Table 3"],
                f"the primary table set is {primary_tables}, not three tables")
        _expect(len(primary_figures) == PRIMARY_FIGURE_BUDGET
                and len(primary_tables) == PRIMARY_TABLE_BUDGET,
                "the primary exhibit set is not exactly 3 figures and 3 tables")
        _expect(sorted(b["exhibit"] for b in results["figures"].values()
                       if b["exhibit_set"] == "supplementary") == ["Figure 4"]
                and sorted(b["exhibit"] for b in results["tables"].values()
                           if b["exhibit_set"] == "supplementary") == ["Table 4"],
                "the two supplementary exhibits are not Figure 4 and Table 4")
        # SUPPLEMENTARY IS A DECLARATION, NOT A DELETION.  Both files are still in the
        # bundle, still at their contract row counts, still stamped in the manifest and
        # still reachable through their own `results.json` block.  If this assertion ever
        # fails because a file is gone, the fix that removed it was the wrong fix.
        _expect((first / "figures-csv/figure4_event_centered_activity.csv").exists()
                and (first / "tables-csv/table4_collider_comparison.csv").exists()
                and results["figures"]["figure4"]["rows"] == 44
                and results["tables"]["table4"]["rows"] == 3,
                "a supplementary exhibit stopped being written into the bundle")
        _expect(not exhibit_budget_problems(results["figures"], results["tables"]),
                "the fixture bundle does not satisfy its own exhibit budget")
        checks += 6

        # ...AND IT BITES.  A fourth primary figure is refused, by name and by count.
        # Proved by adding one rather than by reading the code: the check is worth having
        # only if it fires, and a budget nobody has watched fire is a comment.
        fourth = {k: dict(v) for k, v in results["figures"].items()}
        fourth["figure4"]["exhibit_set"] = "primary"
        bitten = exhibit_budget_problems(fourth, results["tables"])
        _expect(any("carries 4 figures" in p for p in bitten),
                f"a fourth primary figure was not refused on the count: {bitten}")
        _expect(any("3.8's register says ('Figure 4', 'supplementary')" in p
                    for p in bitten),
                f"a fourth primary figure was not refused on the register: {bitten}")
        _expect_refusal(
            lambda: assert_exhibit_budget(fourth, results["tables"]),
            "CLAUDE.md section 2 rule 7 fixes it at 3",
            "assert_exhibit_budget accepted four primary figures")
        # A fifth block key is refused too, so the register is what pins the set and not
        # merely the arithmetic over whatever keys happen to be present.
        fifth = {**{k: dict(v) for k, v in results["tables"].items()},
                 "table5": {"exhibit": "Table 5", "exhibit_set": "primary"}}
        _expect(any("3.8's exhibit register declares" in p
                    for p in exhibit_budget_problems(results["figures"], fifth)),
                "a table key 3.8 does not declare was not refused")
        checks += 4

        # ------------------------------------- the event-centered curve's own denominator
        # 3.8 makes an exhibit's `denominator` a key of `denominators`, and until 1.8.0 the
        # only candidate for this figure was `events_composite`, which is not the
        # population the curve is drawn over: the curve carries the same structural filter
        # the fits carry, so the plate note printed a number larger than the curve's own.
        _expect(results["figures"]["figure4"]["denominator"] == "event_centered_members",
                "Figure 4 still names a denominator that is not its own population")
        _expect(all(block["denominator"] in results["denominators"]
                    for block in (*results["figures"].values(),
                                  *results["tables"].values())),
                "an exhibit names a denominator key that results.json does not carry")
        _expect(sorted(results["denominators"]) == sorted(REQUIRED_DENOMINATORS),
                "results.json does not carry exactly 3.2's required denominator keys")
        _expect(results["denominators"]["event_centered_members"]["unit"]
                == "risk-set members",
                "the curve's denominator is not in risk-set members, which is the unit "
                "the producing query counts in")
        # The fixture pins tier 4, where no event-centered query is submitted at all, so
        # the curve is drawn over a true zero and the plate note says so.
        _expect(results["figures"]["figure4"]["n"] == 0
                and results["figures"]["figure4"]["plate_note"].startswith(
                    "Event-centered curve n = 0 risk-set members."),
                "at tier 4 the curve's plate note does not print its own empty denominator")
        checks += 5
        _expect(len(results["attrition"]["rungs"]) == 19, "the ladder is not 19 rungs")
        _expect(len(results["debt"]["by_group"]) == 5, "by_group is not 5 entries")
        _expect(len(results["sensitivity"]) == 14, "sensitivity is not 14 rows")
        _expect(results["attrition"]["closes"] is True, "the ladder does not close")
        checks += 5

        figure2 = pd.read_csv(first / "figures-csv/figure2_daily_activity.csv",
                              dtype=str, keep_default_na=False)
        _expect(len(figure2) == 286, f"figure 2 is {len(figure2)} rows, not 286")
        _expect(figure2["series_segment"].astype(int).max() == 2,
                "the fixture must carry a mid-series gap, or a renderer that bridges gaps "
                "passes against it")
        forest = pd.read_csv(first / "figures-csv/figure3_forest.csv",
                             dtype=str, keep_default_na=False)
        _expect(len(forest) == 27, f"figure 3 is {len(forest)} rows, not 27")
        _expect((forest["estimate"] == FIGURE_SUPPRESSED_TOKEN).sum() == 1,
                "the fixture must carry exactly one suppressed forest row")
        table1 = pd.read_csv(first / "tables-csv/table1_cohort_characteristics.csv",
                             dtype=str, keep_default_na=False)
        _expect(list(table1["row_order"].astype(int)) == list(range(1, len(table1) + 1)),
                "Table 1's row_order is not contiguous on arrival")
        # Figure 4 keeps its rows and suppresses its cells, which is Figure 3's convention
        # and not Figure 2's: an event-centered offset is a coordinate in a fixed, two-sided
        # window this study published in advance, and a curve that silently shortened to the
        # offsets clearing the floor would misstate the window it was drawn over.
        figure4 = pd.read_csv(first / "figures-csv/figure4_event_centered_activity.csv",
                              dtype=str, keep_default_na=False)
        _expect(len(figure4) == 44, f"figure 4 is {len(figure4)} rows, not 44")
        _expect(sorted(set(figure4["day_relative_to_event"].astype(int)))
                == list(FIGURE4_OFFSETS),
                "figure 4 must carry every offset from -14 to +7 on every run")
        _expect(figure4["day_relative_to_event"].nunique() * 2 == len(figure4),
                "22 distinct offsets across 44 rows is what keeps the axis off the "
                "near-unique class without any part of 10.2 exception 3")
        # The fixture pins tier 4, so every measured cell is the token and every reason is
        # the TIER's sentence rather than the contributor one.  Those cells are not entries
        # in results.json.suppressed: 3.7 records a tier-driven absence where the tier is
        # recorded, and 3.9 says so in terms.
        _expect(set(figure4["n_contributing"]) == {FIGURE_SUPPRESSED_TOKEN}
                and set(figure4["plotted"]) == {"false"},
                "at tier 4 figure 4 is 44 rows of SUPPRESSED with nothing plotted")
        _expect(set(figure4["not_plotted_display"]) == {LABELS["not_permitted_by_tier"]},
                "at tier 4 every figure 4 row says the tier forbade the question")
        table4 = pd.read_csv(first / "tables-csv/table4_collider_comparison.csv",
                             dtype=str, keep_default_na=False)
        _expect(len(table4) == 3, f"table 4 is {len(table4)} rows, not 3")
        _expect(list(table4.columns) == list(TABLE4_COLUMNS),
                "table 4's header is not the six columns of 5.7")
        _expect(list(table4["Window group"])
                == [LABELS[slug] for slug, _c, _s, _k in TABLE4_ROWS],
                "table 4's three window groups are not 7.15's, in 5.7's order")
        _expect(set(table4["Episode-days at risk"]) == {""},
                "at tier 4 no landmark panel query is submitted, so the count cells are "
                "the not-applicable empty string and never a suppression sentence")
        manifest = pd.read_csv(first / "MANIFEST.csv", dtype=str, keep_default_na=False)
        _expect(len(manifest) == 16, f"the manifest is {len(manifest)} rows, not 16")
        _expect(list(manifest["file"]) == list(BUNDLE_FILES),
                "the manifest is not in the fixed row order of 8.3")
        checks += 11

        registry = pd.read_csv(first / "ledgers-csv/ledger_concept_set_registry.csv",
                               dtype=str, keep_default_na=False)
        _expect(len(registry) == 51, f"the registry ledger is {len(registry)} rows, not 51")
        # Every file is sorted on the NUMERIC value of its declared sort keys.  A table CSV
        # renders its cells as strings before this point, so a lexicographic sort would put
        # day 10 between day 1 and day 2 and would be byte-stable while it did it.
        wear = pd.read_csv(first / "ledgers-csv/ledger_wear_availability_by_day.csv",
                           dtype=str, keep_default_na=False)
        _expect(len(wear) == 318, f"the wear ledger is {len(wear)} rows, not 318")
        for _slug, block in wear.groupby("group_slug", sort=False):
            days = list(block["day"].astype(int))
            _expect(days == sorted(days), "the wear ledger is not in ascending day order")
            _expect(all(int(v) <= int(a) for v, a in
                        zip(block["n_valid_wear"], block["n_at_risk"])),
                    "a rounded valid-wear count exceeds its rounded at-risk denominator")
        for _slug, block in figure2.groupby("group_slug", sort=False):
            days = list(block["day"].astype(int))
            _expect(days == sorted(days), "Figure 2 is not in ascending day order")
        checks += 9

        # No image, ever.  The perimeter exports the plotted series, never the plot.
        for path in first.rglob("*"):
            _expect(path.is_dir() or path.suffix in disclosure.ALLOWED_EXPORT_SUFFIXES,
                    f"a file with a forbidden extension is in the bundle: {path.name}")
            checks += 1

    if _SENTENCES_DISCLOSURE_CANNOT_SEE:
        # Not an assertion.  `pipeline/tests/test_disclosure.py` already carries the hard
        # failure for this exact divergence, and a second stop condition here would block
        # this module for a gap in another one.  It is printed so that no run of this
        # self-test can pass while quietly relying on the local supplement.
        unseen = sorted(
            slug for slug, sentence in LABELS.items()
            if sentence in _SENTENCES_DISCLOSURE_CANNOT_SEE
        )
        print(
            f"07_export.py NOTE: disclosure.SUPPRESSION_REASONS has not adopted "
            f"{len(unseen)} of EXPORT-CONTRACT.md 7.5's sentences: {unseen}. "
            f"is_bundle_suppressed() returns False for them, so MANIFEST.csv understates "
            f"n_suppressed_cells wherever one is written and the complementary-disclosure "
            f"class cannot see one. This module carries a computed supplement for the "
            f"representation check only; it empties itself when the module adopts them."
        )
    print(f"07_export.py self-test passed: {checks} assertions.")


def _gate_probe(
    frame: pd.DataFrame,
    *,
    relative_path: str,
    kind: str,
    count_cols: Sequence[str] = (),
    percentage_columns: Sequence[str] = (),
    column_partitions: Sequence[Sequence[str]] = (),
    row_partitions: Sequence[tuple[str, Sequence[int]]] = (),
    composite_count_columns: Sequence[str] = (),
    numeric_string_columns: Sequence[str] = (),
    specification_columns: Sequence[str] = (),
) -> None:
    """Raise if EITHER gate finds anything.  The self-test's way in, without a write.

    Both gates, because both run on every frame `gated_export` writes and the split between
    them moved at contract 1.6.0: the complementary-disclosure and column-partition classes
    now live in `disclosure.export_violations`, where they can finally see a
    bundle-representation hidden cell, and this module keeps the classes the module has no
    argument for.  A probe that asked only one of the two would stop pinning the refusals
    that moved, which is exactly how a check gets quietly dropped in a refactor.
    """
    problems = _contract_violations(
        frame, relative_path=relative_path, kind=kind, count_cols=count_cols,
        composite_count_columns=composite_count_columns,
        row_partitions=row_partitions, numeric_string_columns=numeric_string_columns,
        specification_columns=specification_columns,
    )
    problems += disclosure.export_violations(
        frame, kind=kind, count_cols=count_cols,
        percentage_columns=percentage_columns, partitions=column_partitions,
        specification_columns=specification_columns,
    )
    if problems:
        raise ContractViolation("; ".join(problems))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Write the export bundle EXPORT-CONTRACT.md declares. --fixture writes the "
            "data-free dummy bundle of section 9.1 and touches no cloud resource."
        )
    )
    parser.add_argument(
        "--fixture", metavar="DIR", nargs="?", const=DEFAULT_FIXTURE_DIRECTORY,
        help=(
            "write the dummy bundle into DIR (default: "
            f"{DEFAULT_FIXTURE_DIRECTORY} under the repository root)"
        ),
    )
    parser.add_argument("--self-test", action="store_true",
                        help="run the self-test and exit")
    parser.add_argument("--validate", metavar="DIR",
                        help="validate an already-written bundle and exit")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.self_test:
        _run_self_test()
        return 0

    if args.validate:
        problems = validate_bundle(Path(args.validate))
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"{len(problems)} problem(s)")
        return 1 if problems else 0

    if args.fixture:
        target = Path(args.fixture)
        if not target.is_absolute():
            root = _repo_root()
            target = (root / target) if root is not None else target
        written = write_fixture(target)
        print(describe_tree(target))
        print(f"\nMANIFEST.md5 {written['manifest_md5']}")
        problems = validate_bundle(target)
        for problem in problems:
            print(f"FAIL {problem}")
        print(f"bundle validation: {len(problems)} problem(s)")
        return 1 if problems else 0

    _run_self_test()
    return 0


if __name__ == "__main__":
    sys.exit(main())
