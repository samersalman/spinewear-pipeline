#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""03_cohort.py -- Phase 3.  The cohort driver, the attrition ladder, and the second hard stop.

WHERE THIS RUNS.  INSIDE THE PERIMETER for everything that touches a byte: pricing the
nineteen stage bodies of `build_all.sql`, calling the stored procedure, reading the ladder and
the four SQL-side ledgers back out of `{DERIVED}`.  LOCALLY it still runs end to end with no
cloud and no credentials: `python3 03_cohort.py --self-test` exercises the stage splitter
against the real `build_all.sql` on disk, and drives every ladder assertion against synthetic
ladders that are correct and against ladders broken in each specific way.

IN-PERIMETER USE, in a notebook, after the probe and the pre-gate have both passed:

    %run 00_config.ipynb
    %run -i 01_probe.py
    %run -i 03_cohort.py
    COHORT = run_cohort(hr_minute_column=..., device_model_column=...)

or from the VM terminal, which is the resumed-session path:

    python3 03_cohort.py --price-only          prices all 19 stages, executes nothing
    python3 03_cohort.py --call                prices, then CALLs, then asserts, then stops
    python3 03_cohort.py --call --resume features    rebuilds stages 10 through 19

WHAT IT DOES, in order, and it stops at the fifth.

  1. PRICES THE DAG STAGE BY STAGE BEFORE RUNNING ANY OF IT.  `build_all.sql` is delimited into
     nineteen stages by `@stage-begin:` / `@stage-end:` markers.  Each body is lifted, made
     standalone, dry-run through the configuration notebook's free `dry_run_gb`, and printed
     with its own byte estimate and its own dollars, with a total, before a single job is
     submitted.
  2. RUNS THE PROCEDURE, or resumes it from a named stage.  One `CALL`, seven positional
     arguments, `start_stage` last.
  3. EMITS THE NINETEEN-RUNG LADDER of ANALYSIS-PLAN 2.6 and ASSERTS IT CLOSES, by four
     different rules, plus an independent reconciliation against `episodes_eligible` that is
     not a re-reading of anything the ladder computed for itself.
  4. EMITS THE FOUR SQL-SIDE STROBE LEDGERS at the exported column set of
     EXPORT-CONTRACT 5.6, which is NARROWER than what the producer writes, deliberately.
  5. STOPS.  The protocol's own rule is that no modelling begins until the attrition table is
     reviewed.  Nothing downstream runs until a human has read the table this module prints.

THE ONE FACT THAT COSTS MONEY IF IT IS MISSED.  `maximum_bytes_billed` on a BigQuery script is
enforced PER CHILD JOB, not across the script.  `CALL` is a script job and each of the nineteen
stages inside it is a child job the cap is applied to individually.  A cap sized to the
nineteen-stage TOTAL therefore does not bound the run at all: it permits EACH of the nineteen
stages to bill up to that total, which is up to nineteen times the number the human approved.
So the cap this module hands `q_guarded` is sized from the LARGEST PER-STAGE ESTIMATE, never
from the sum.  The sum is still computed and shown, because it is the approval figure a human
signs off on before anything is submitted; it is simply not a thing BigQuery enforces.
DAG-SCHEMA.md section 5.1 carries the same reasoning in full.

TWO STAGES ARE `FORMAT` TEMPLATES and both must be substituted BEFORE the dry run, or the
estimate prices a query that is not the one that will execute and the per-stage cap is sized
against the wrong number.  `hr_daily` takes the probed heart-rate zone-minute column twice;
`device_daily` takes the probed device model column once, on the ELSE branch of its
empty-column test, which is why it is the one that gets missed.  Both carry a
`-- @stage-format-args:` line inside their own marker pair, and this module asserts in BOTH
directions: a body containing `EXECUTE IMMEDIATE FORMAT(` must carry the line, a body carrying
the line must have as many names on it as the template has `%s`, and no `%s` may survive.
THE TEST KEYS ON `EXECUTE IMMEDIATE FORMAT(`, NOT ON THE PERCENT SIGN, because `episodes`,
`events` and `risk_sets` each carry a literal `%s` inside an ordinary static `FORMAT` call and
would every one of them false-positive.

WHAT `closes_exact` DOES AND DOES NOT PROVE, because this is the trap in the ladder.  The
column is TRUE BY CONSTRUCTION on eighteen of the nineteen rungs: `n_out` is computed AS
`n_in - n_dropped`, so the rung's own test compares an expression against itself and cannot
fail.  Exactly one identity is independently tested inside the perimeter, at step 16, which
reconciles `COUNTIF(is_eligible)` against the `first_fail_step` histogram.  This module
therefore does NOT treat the column as nineteen checks.  It recomputes every identity on the
true integers it was handed, and it runs ONE FURTHER QUERY that counts the exclusions table a
second way and holds the ladder to it, because that is the only check on this side of the
boundary that can separate the three quantities the analytic rung rests on.  Reading the
finished nineteen rows, the arithmetic identities are implied by one another and are transport
checks; what can fail out here on a correct build is the STRUCTURE, meaning the rungs, their
order, their kinds, their units, their null discipline and their reason column against this
module's transcription of the plan, and the RECOUNT.  Which of these is which is written out
beside each one and printed in the report, because an assertion nobody can describe the failure
of is decoration.

WHAT THIS MODULE DELIBERATELY DOES NOT DO.  No model, no estimate, no bootstrap, no export
bundle, no file written anywhere.  `04_features.py` builds the analysis frames,
`05_analysis_drd.py` and `06_analysis_gate.py` fit, and `07_export.py` is the only module in
this project that writes a file.  This one prints a table and stops.

DISCLOSURE.  Every count in `{DERIVED}` is a TRUE INTEGER and is not rounded, so this module
rounds and floor-tests AT THE BOUNDARY, once, where the number becomes a printed cell.
`disclosable(n)` is asked of a true count before rounding; `is_legal_disclosed_count(cell)` is
asked of a cell already rounded; the two disagree on 20 by design and are never substituted for
one another.  No frame is ever shown with rows: `safe_show` prints a shape and nothing else.
Percentages go through `n_pct`, which divides by the ROUNDED denominator, so a reader can
reproduce every printed percentage from the printed counts and from nothing else.

DISPLAY OR DATA, AND THIS MODULE RENDERS NOTHING OF ITS OWN.  A count is DISPLAY when it is a
string a human reads and it carries the house thousands separator; it is DATA when something
else computes on it and it is a bare number.  Every display count here goes through
`disclosure.render_count`, directly or through `n_pct`, so the separator has one implementation
in this project rather than one per module.  This module writes no separator itself.

NO DISPLAY STRING IS WRITTEN BY SQL.  `attrition.reason` is a SLUG and takes exactly three
values, the rung's own slug, the literal `unit_change` and the empty string.  The label table of
EXPORT-CONTRACT 7.2 is keyed by the rung's `slug`, and has no entry for either of the other two,
so `LABELS[reason]` raises on any conversion or terminal rung.  Every lookup in this module is
keyed by `slug` and the function that does it refuses a `reason`.

SEED = 0, everywhere, and nothing in this module samples.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

# `pipeline/` is not a package and this file's name is not an importable identifier, so it is
# always a script: `%run` inside the perimeter, `python3` on a laptop.  Both need this file's
# own directory on the path before `import disclosure` resolves, and neither guarantees it.
try:
    _HERE = Path(__file__).resolve().parent
except NameError:                                   # exec'd without a file, e.g. a paste
    _HERE = Path.cwd()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import pandas as pd

from disclosure import (
    EM_DASH,
    MIN_CELL,
    MINUS_SIGN,
    disclosable,
    is_legal_disclosed_count,
    is_suppressed,
    n_pct,
    render_count,
    round20,
    safe_show,
)

SEED = 0

# BigQuery on-demand list price, US, and the byte unit.  Repeated from the configuration
# notebook rather than imported, because this module must be able to print a cost table on a
# laptop with no notebook in the namespace.  Display only: enforcement is always in bytes.
USD_PER_TIB = 6.25
BYTES_PER_GIB = 1024 ** 3


class CohortError(RuntimeError):
    """A Phase 3 stop condition.  Never downgraded to a warning."""


class StageMarkerError(CohortError):
    """`build_all.sql` does not split into the nineteen stages this module prices.

    A class of its own because it is a defect in the SQL file, not in the data and not in the
    environment: nothing has been submitted, nothing has billed, and the fix is an edit to
    `build_all.sql` rather than a re-run.
    """


class LadderClosureError(CohortError):
    """The attrition ladder does not close.  CLAUDE.md stop condition 3.

    Distinct from every other failure here because it is the one that invalidates work already
    paid for: the tables exist, they cost money, and they are wrong.  Do not adjust a count to
    make it close.
    """


class CohortBudgetExceeded(CohortError):
    """The priced DAG total exceeded the approval figure, so nothing executed and nothing billed.

    A class of its own for the same reason the configuration notebook gives `QueryCapExceeded`
    one: a refusal by the budget is not a permissions problem and not a bad query, and the
    diagnosis printed beside it has to be able to branch on which of the three happened.
    """


# ======================================================================================
# (1) The nineteen rungs.  THIS MODULE OWNS THE LIST.
#
# ANALYSIS-PLAN.md section 2.6 is the authority; CLAUDE.md section 4, DAG-SCHEMA.md 8.15 and
# EXPORT-CONTRACT.md sections 3.3 and 7.2 transcribe it and do not extend it.  `local/verify.py`
# asserts SET EQUALITY of the slug column, so a rung invented anywhere fails verification rather
# than propagating.  The tuple below is the transcription this project's code reads, and it is
# the one `07_export.py` should IMPORT rather than retype: a fourth hand-typed copy of nineteen
# slugs is a fourth place for them to drift.
#
# Order is fixed and is not an implementation detail.  A ladder counts each episode once, at the
# first rung it fails, so reordering changes every rung's drop count without changing the
# analytic n, and that changes what the Figure 1 exclusion boxes say.  Reordering is an
# amendment under plan section 13.
# ======================================================================================

_KINDS = ("exclusion", "conversion", "terminal")
_UNITS = ("persons", "persons to episodes", "episodes", "episodes to events", "events")

# step, slug, kind, unit.  Read down the file next to ANALYSIS-PLAN 2.6 and they match line for
# line, which is how a transcription is checked.
ATTRITION_RUNGS: tuple[Mapping[str, Any], ...] = tuple(
    MappingProxyType({"step": step, "slug": slug, "kind": kind, "unit": unit})
    for step, slug, kind, unit in (
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
)

LADDER_SLUGS: tuple[str, ...] = tuple(rung["slug"] for rung in ATTRITION_RUNGS)
LADDER_STEPS: tuple[int, ...] = tuple(rung["step"] for rung in ATTRITION_RUNGS)

# The step numbers each closure rule reaches.  Named rather than written as a literal range at
# the call site, because "steps 3 to 15" appears in four different asserts and an off-by-one in
# one of them is exactly the kind of thing that closes anyway on the first run and stops closing
# on the second.
CONVERSION_STEPS: tuple[int, ...] = (2, 17)
TERMINAL_STEPS: tuple[int, ...] = (16, 19)
NO_DROP_STEPS: tuple[int, ...] = (16, 17, 19)          # n_dropped is null exactly here
CARRIED_FORWARD_STEP: int = 2                          # n_carried_forward is non-null only here
EPISODE_DROP_STEPS: tuple[int, ...] = tuple(range(3, 16))
EPISODE_SEGMENT_TERMINAL_STEP: int = 16
EVENT_SEGMENT_STEPS: tuple[int, ...] = (17, 18, 19)

# The three values `attrition.reason` may take, keyed off `kind` and NOT off whether `n_dropped`
# happens to be null, which is a different question: step 2 is a conversion that also drops and
# step 17 is a conversion that does not.
REASON_UNIT_CHANGE = "unit_change"
REASON_NOT_APPLICABLE = ""


# --------------------------------------------------------------------------------------
# The label table, transcribed character for character from EXPORT-CONTRACT.md section 7.2,
# which transcribes ANALYSIS-PLAN.md section 2.6.  KEYED BY SLUG.
#
# THIS IS THE TRAP THE CONTRACT WARNS ABOUT.  `attrition.reason` is a slug, but it is not a key
# into this table: on a conversion rung it is the literal `unit_change` and on a terminal rung it
# is the empty string, and neither has an entry here or ever will.  A naive `LABELS[reason]`
# therefore raises on steps 2, 16, 17 and 19.  `rung_label()` and `rung_reason_display()` below
# take the RUNG SLUG and refuse anything else, so the mistake is not available at a call site.
#
# Steps 15 and 16 share "Analytic cohort" and steps 18 and 19 share "Analyzable acute-care
# events", because an exclusion rung's display label names the box of SURVIVORS below it.  That
# is not a transcription slip and a renderer must not de-duplicate it.
# --------------------------------------------------------------------------------------

RUNG_LABELS: Mapping[str, str] = MappingProxyType({
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
})

RUNG_REASON_DISPLAY: Mapping[str, str] = MappingProxyType({
    "program_participants":
        "No qualifying spine procedure concept in the electronic health record",
    "episode_construction":
        "Same-day qualifying procedure records collapsed into one episode; operations on "
        "different dates stay separate episodes until step 13",
    "excl_trauma_malignancy_infection":
        "Trauma, spinal cord injury, malignancy, metastatic disease or spinal infection "
        "recorded in the 30 days before or on the index date",
    "excl_ed_encounter_not_elective":
        "Emergency department encounter immediately before the index operation, with no coding "
        "evidence of an elective episode",
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
})

# EXPORT-CONTRACT.md 7.1.  Seven group slugs, because the group set that survives is decided by
# the collapse level AFTER the ledger exists, so the producer emits all seven and no consumer
# may hardcode four.
GROUP_LABELS: Mapping[str, str] = MappingProxyType({
    "cervical_decompression": "Cervical decompression",
    "cervical_fusion": "Cervical fusion",
    "lumbar_decompression": "Lumbar decompression",
    "lumbar_fusion": "Lumbar fusion",
    "all_groups": "All groups",
    "fusion": "Fusion",
    "decompression": "Decompression",
})

# EXPORT-CONTRACT.md 7.5, transcribed character for character and in the contract's own row
# order.  The first sentence is used verbatim wherever a count is hidden, so a reader meets one
# sentence rather than five phrasings.  It reads "20 or fewer", not "fewer than 20", because a
# true count of exactly 20 IS suppressed and a sentence saying "fewer than 20" over a suppressed
# 20 is simply false.
#
# The ninth entry is a suppression reason in the MECHANICAL sense only.  The node shape is how a
# value-free result is carried in this bundle, so `no_crossing_within_range` borrows it; it is
# not a disclosure event and it never enters `suppressed.by_reason` under an R1 rule.  It exists
# because a primary contrast that holds its sign at every `delta` out to the end of the
# prespecified extension is the STRONGER finding, and the only sentence available for it before
# the contract reached 1.6.0 was `not_estimable_data_unavailable`, which says the data were not
# there and reads to a comparing reader as a gap in the analysis rather than as its result.
#
# The tenth entry is a real refusal and not a mechanical one.  `ANALYSIS-PLAN.md` reached
# version 1.5 and its section 4.9 prespecifies a coefficient ceiling for every logistic fit in
# Arm A: a fit carrying any coefficient above the ceiling is refused and prints this sentence,
# and the value that tripped it is never printed, not as a bound and not in a footnote.  The
# plan names the slug and says the vocabulary is not its to own, so the pair below is
# transcribed from 7.5 and not composed here; `06_analysis_gate.py` already emits it.  No
# existing reason could have carried a separated fit: a quasi-separated conditional model
# CONVERGES, so the cell size was fine, the data were available, the tier permitted the
# analysis, and `not_estimable_convergence` -- the near-miss -- would have been a false
# sentence rather than a near-enough one.
#
# A transcription drifts silently, so `_run_self_test()` reparses section 7.5 out of
# EXPORT-CONTRACT.md and asserts this whole table against it, slug by slug and character by
# character and IN THE CONTRACT'S OWN ROW ORDER, rather than only checking that a newly added
# row is present.
SUPPRESSION_SENTENCES: Mapping[str, str] = MappingProxyType({
    "cell_below_threshold": "20 or fewer, suppressed per All of Us dissemination policy",
    "numerator_suppressed": "suppressed because the count behind it is suppressed",
    "contributing_n_below_threshold": "20 or fewer contributors, suppressed",
    "secondary_suppression": "suppressed to protect a suppressed cell in the same total",
    "not_estimable_cell_size": "not estimable (cell size)",
    "not_estimable_convergence": "not estimable (model did not converge)",
    "not_estimable_data_unavailable": "not estimable (data not available)",
    "not_permitted_by_tier": "not permitted at the feasibility tier reached",
    "no_crossing_within_range": "no crossing within the prespecified range",
    "not_estimable_separation": "not estimable (separation)",
})

# ANALYSIS-PLAN.md 2.5, the collapse ladder.  Prespecified, so the level is a consequence of the
# counts and not a judgment made after seeing them.
COLLAPSE_LEVELS: tuple[str, ...] = ("four_group", "two_group", "single_group", "no_estimand")
FOUR_GROUP_SLUGS: tuple[str, ...] = (
    "cervical_decompression", "cervical_fusion", "lumbar_decompression", "lumbar_fusion")


def rung_label(slug: str) -> str:
    """The ladder-box sentence for a rung, keyed by its SLUG and by nothing else.

    Refuses `unit_change` and the empty string by name rather than by KeyError, because those
    are exactly the two values `attrition.reason` takes on the four non-exclusion rungs and a
    caller reaching this function with one of them has made the substitution EXPORT-CONTRACT 7.2
    warns about.  The message says which mistake it was.
    """
    if slug in (REASON_UNIT_CHANGE, REASON_NOT_APPLICABLE):
        raise CohortError(
            "the label table is keyed by the rung slug, never by the reason column: the reason "
            "carries a unit-change marker on a conversion rung and an empty string on a "
            "terminal rung, and neither is a key here. Pass the rung's own slug."
        )
    try:
        return RUNG_LABELS[slug]
    except KeyError:
        raise CohortError(f"{slug!r} is not one of the nineteen rung slugs") from None


def rung_reason_display(slug: str) -> str:
    """The exclusion-box sentence for a rung, keyed by its SLUG.  Empty on the four that carry none."""
    if slug in (REASON_UNIT_CHANGE, REASON_NOT_APPLICABLE):
        raise CohortError(
            "the reason-display table is keyed by the rung slug, never by the reason column"
        )
    try:
        return RUNG_REASON_DISPLAY[slug]
    except KeyError:
        raise CohortError(f"{slug!r} is not one of the nineteen rung slugs") from None


# ======================================================================================
# (2) The four SQL-side STROBE ledgers, and the columns the contract does NOT export.
#
# The fifth ledger, the concept-set registry, is already written by 01_probe.py from
# `cs_spine.registry_rows()` and is not touched here.
#
# EXPORT-CONTRACT.md 5.6 fixes each file's exported column set, and for the wear ledger that set
# is NARROWER than what `build_all.sql` produces.  The producer emits `n_analyzable` and
# `n_inpatient`; the contract exports neither, and THAT REFUSAL IS LOAD BEARING rather than an
# oversight, so this module reproduces it rather than showing the human two columns that will
# not be in the file they are approving.
#
#   n_analyzable would make an unwritten complement recoverable by subtraction.  An analyzable
#   day is an at-risk day with enough wear minutes AND a step count; a valid-wear day needs only
#   the minutes.  So `n_valid_wear` less `n_analyzable` is the count of at-risk days with wear
#   and no step record: a two-member partition of a number this file already discloses, with one
#   member written and the other not, which is precisely the shape the disclosure rules refuse.
#   It is also already published where it is read, as `n_contributing` in the Figure 2 series.
#
#   n_inpatient counts readmitted days, so it is small on most days by its nature, and the
#   absence rule keys on `n_at_risk` alone.  Most of its cells would arrive at the boundary
#   below the floor and would each be written as the suppression sentence.  That is a value
#   argument rather than a disclosure one and the distinction is worth keeping straight.
#
# DO NOT WIDEN EITHER.  The fix, if a reviewer asks, is an amendment to the contract with the
# subtraction above resolved first, never a column added at a call site.
# ======================================================================================

# Producer table in {DERIVED} -> the contract's file name.  Names are kept side by side because
# they differ, and a module that silently prints one while the manifest carries the other is a
# module a reviewer cannot reconcile.
LEDGER_TABLES: Mapping[str, str] = MappingProxyType({
    "ledger_exclusion_reasons": "ledger_exclusion_and_censoring_reasons.csv",
    "ledger_wear_by_day": "ledger_wear_availability_by_day.csv",
    "ledger_matched_sets": "ledger_matched_set_sizes.csv",
    "ledger_variable_missingness": "ledger_variable_provenance.csv",
})

# The columns this module READS off each producer table.
LEDGER_SOURCE_COLUMNS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "ledger_exclusion_reasons": ("step", "slug", "reason_detail", "n_episodes", "n_denominator"),
    "ledger_wear_by_day": ("group_slug", "group_order", "day", "n_at_risk", "n_valid_wear"),
    "ledger_matched_sets": ("set_size", "n_sets", "n_cases"),
    "ledger_variable_missingness": ("variable", "n_total", "n_missing"),
})

# The columns the producer writes that the contract deliberately does not export.  Named so the
# refusal is visible in the code and in the printed report, rather than being an absence.
LEDGER_WITHHELD_COLUMNS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "ledger_exclusion_reasons": (),
    "ledger_wear_by_day": ("n_analyzable", "n_inpatient"),
    "ledger_matched_sets": (),
    "ledger_variable_missingness": (),
})

# The row order EXPORT-CONTRACT.md 5.6 fixes for each file, so the bytes are stable.  Read in
# that order here too, rather than in whatever order the columns happen to sit in, so what a
# reviewer approves at this stop is the order the exported file will carry.
LEDGER_SORT_KEYS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "ledger_exclusion_reasons": ("step", "reason_detail"),
    "ledger_wear_by_day": ("group_order", "day"),
    "ledger_matched_sets": ("set_size",),
    "ledger_variable_missingness": ("variable",),
})

# The count columns on each ledger, which is what decides where the floor is applied.  A count
# column left out of this map is not floor-tested at all, which is the one failure mode that
# leaves no mark in the file it damages.
LEDGER_COUNT_COLUMNS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "ledger_exclusion_reasons": ("n_episodes", "n_denominator"),
    "ledger_wear_by_day": ("n_at_risk", "n_valid_wear"),
    "ledger_matched_sets": ("n_sets", "n_cases"),
    "ledger_variable_missingness": ("n_total", "n_missing"),
})

# The three sets of rows in the exclusion ledger that ARE partitions of a disclosed total, so
# the secondary-suppression rule applies across their members.  The step 3 indication rows and
# the step 4 rescue routes are NOT partitions: they overlap, and they do not sum to their
# denominator, so declaring them would be a false claim.
LEDGER_EXCLUSION_PARTITIONS: Mapping[int, tuple[str, ...]] = MappingProxyType({
    12: ("no_valid_baseline_day", "fewer_than_seven_valid_days", "baseline_span_under_14_days"),
    15: ("death", "repeat_spine_operation"),
    16: ("censoring_none", "censoring_death", "censoring_repeat_spine_operation",
         "censoring_cdr_observation_cutoff"),
})

# --------------------------------------------------------------------------------------
# `reason_detail` sentences.
#
# THE CONTRACT REQUIRES A SENTENCE HERE AND DOES NOT SUPPLY THE TABLE.  EXPORT-CONTRACT.md 5.6
# says `reason_detail` is "one prespecified sentence per row", and section 10.2 exempts the
# column from the near-unique class on exactly that ground, but section 7 carries no table for
# the twenty detail slugs `build_all.sql` emits.  Printing the slugs instead is not an option:
# an identifier is never a user-visible string.  So the table lives here, in the module that
# owns the rung vocabulary, and the four sentences the contract's own worked example already
# fixes are transcribed from it character for character rather than rewritten.  This needs to
# become a section 7.12 of the contract before 07_export.py writes the file, or the two copies
# drift; it is called out in this module's handoff for that reason.
# --------------------------------------------------------------------------------------
REASON_DETAIL_LABELS: Mapping[tuple[int, str], str] = MappingProxyType({
    (3, "trauma"): "Trauma diagnosis recorded in the 30 days before or on the index date",
    (3, "spinal_cord_injury"):
        "Spinal cord injury recorded in the 30 days before or on the index date",
    (3, "malignancy"): "Malignancy recorded in the 30 days before or on the index date",
    (3, "metastatic_disease"):
        "Metastatic disease recorded in the 30 days before or on the index date",
    (3, "spinal_infection"):
        "Spinal infection recorded in the 30 days before or on the index date",
    (4, "ed_encounter_present"):
        "Emergency department encounter ending on the index date or within the 2 days before it",
    (4, "rescue_elective_coded"):
        "Rescued by elective or scheduled wording on the index admission",
    (4, "rescue_degenerative_index"):
        "Rescued by a degenerative index diagnosis despite the emergency department encounter",
    (4, "rescue_degenerative_outpatient_90d"):
        "Rescued by an outpatient degenerative spine diagnosis in the 90 days before the index "
        "date",
    (12, "no_valid_baseline_day"): "No valid wear day anywhere in the baseline window",
    (12, "fewer_than_seven_valid_days"):
        "Between 1 and 6 valid wear days in the baseline window",
    (12, "baseline_span_under_14_days"):
        "Seven or more valid wear days, spanning under 14 calendar days",
    (14, "no_analyzable_day_in_window"):
        "No analyzable day inside post-discharge days 1 to 35",
    (14, "not_at_risk_in_window"): "Not at risk on any day of post-discharge days 1 to 35",
    (15, "death"): "Accrual window truncated by death",
    (15, "repeat_spine_operation"): "Accrual window truncated by a repeat spine operation",
    (16, "censoring_none"): "Followed to the end of the accrual window with no censoring",
    (16, "censoring_death"): "Censored at death",
    (16, "censoring_repeat_spine_operation"): "Censored at a repeat spine operation",
    (16, "censoring_cdr_observation_cutoff"):
        "Censored at the end of the release observation period",
})

# The twelve analysis variables of `ledger_variable_missingness`, with the printable name each
# gets.  Three of the twelve are expected to be STRUCTURALLY ZERO and only these three: length
# of stay, because rung 10 removed every episode with no discharge date; baseline steps, because
# rung 12 removed every episode with no baseline; and procedure group, because it is null only
# for the episodes rungs 6, 7 and 8 removed.  A zero there is a true statement about the cohort.
# A zero produced by a substitution would not be, which is why the ledger counts the SUBSTITUTION
# FLAG on the two variables that substitute rather than counting the column itself.
VARIABLE_LABELS: Mapping[str, str] = MappingProxyType({
    "age_at_index": "Age at the index operation",
    "sex_at_birth": "Sex assigned at birth",
    "race_concept_id": "Race",
    "ethnicity_concept_id": "Ethnicity",
    "bmi": "Body mass index",
    "charlson_score": "Charlson comorbidity score",
    "los_days": "Length of stay",
    "device_family": "Device family",
    "baseline_steps": "Preoperative baseline steps per day",
    "procedure_group": "Procedure group",
    "daily_deficit": "Daily activity deficit",
    "r72": "Proximal activity ratio at 72 hours",
})
STRUCTURALLY_COMPLETE_VARIABLES: tuple[str, ...] = (
    "los_days", "baseline_steps", "procedure_group")


# ======================================================================================
# (3) The stage splitter.
#
# `build_all.sql` is delimited into nineteen stages by a marker pair, and every stage body reads
# its run parameters from `{DERIVED}.build_params` rather than from procedure variables, which
# is what makes a lifted body standalone-valid SQL and therefore dry-runnable on its own.  A dry
# run of `CALL` does not price the procedure body at all: the script job reports zero.
# ======================================================================================

DEFAULT_BUILD_SQL_NAME = "build_all.sql"

# DAG order, and the number beside each is the `start_stage` index the procedure compares
# against.  Asserted against the splitter's output rather than trusted, so a stage added to the
# SQL without being added here fails at the splitter instead of being silently unpriced.
#
# WHY THIS TUPLE IS NOT DERIVED FROM THE MARKERS, WHICH IS THE OBVIOUS THING TO DO.  Reading
# the order off the `@stage-begin:` lines would make the splitter's "names match" check compare
# the file against itself, and that check would then pass on any file at all.  What this tuple
# actually duplicates is not the markers but the procedure's own `DECLARE stages ARRAY<STRING>`
# and its `IF start_ix <= N THEN` guards, which is what decides what a resume rebuilds.  So the
# tuple stays hand-typed, and `_assert_procedure_stage_declaration` below reads BOTH of those
# declarations out of the SQL and holds all three to each other.  A stage inserted mid-DAG has
# to renumber every guard below it, and that is the failure worth a check.
STAGE_ORDER: tuple[str, ...] = (
    "build_params",                 # 1
    "cs_spine",                     # 2
    "cs_condition",                 # 3
    "episodes",                     # 4
    "hr_daily",                     # 5
    "device_daily",                 # 6
    "fitbit_daily",                 # 7
    "baseline",                     # 8
    "episodes_eligible",            # 9
    "features",                     # 10
    "drd_daily",                    # 11
    "events",                       # 12
    # Reads `drd_daily`, `events` and `fitbit_daily` and NO CDR TABLE, so it prices at the
    # floor and cannot become the binding stage.  It is the full-cohort day-indexed landmark
    # panel the collider correction of ANALYSIS-PLAN 4.4 needs, because the with-versus-without
    # comparison was previously available only at the SAMPLED risk sets, which carry the very
    # selection the comparison exists to expose.  Its two landmark conditions stay separate and
    # their counts are never summed: `has_computable_landmark` is a DATA condition and stays in
    # the risk set as the co-primary exposure, while `structurally_uncomputable_landmark` is
    # DEFINITIONAL and is ladder rung 18.
    "landmark_daily",               # 13
    "risk_sets",                    # 14
    "attrition",                    # 15
    "ledger_exclusion_reasons",     # 16
    "ledger_wear_by_day",           # 17
    "ledger_matched_sets",          # 18
    "ledger_variable_missingness",  # 19
)
N_STAGES = len(STAGE_ORDER)
ATTRITION_STAGE_INDEX = STAGE_ORDER.index("attrition") + 1

# The two stages that are `FORMAT` templates, and the parameter each substitutes.
FORMAT_TEMPLATE_STAGES: Mapping[str, str] = MappingProxyType({
    "hr_daily": "hr_minute_column",
    "device_daily": "device_model_column",
})

_STAGE_BEGIN_RE = re.compile(r"^\s*--\s*@stage-begin:\s*(?P<name>\S+)\s*$")
_STAGE_END_RE = re.compile(r"^\s*--\s*@stage-end:\s*(?P<name>\S+)\s*$")
_STAGE_FORMAT_ARGS_RE = re.compile(r"^\s*--\s*@stage-format-args:\s*(?P<args>.+?)\s*$")
_LINE_COMMENT_RE = re.compile(r"^\s*--")

# The procedure's OWN two declarations of the DAG order: the array a `start_stage` name is
# resolved against, and the guard each body sits inside.  See
# `_assert_procedure_stage_declaration` for why these and not the markers are what `STAGE_ORDER`
# is checked against.
_STAGES_DECLARATION_RE = re.compile(
    r"DECLARE\s+stages\s+ARRAY<STRING>\s+DEFAULT\s*\[(?P<body>.*?)\]\s*;", re.DOTALL)
_STAGE_GUARD_RE = re.compile(r"^\s*IF\s+start_ix\s*<=\s*(?P<index>\d+)\s+THEN\s*$")

# The marker that says a body is a template.  THE TEST KEYS ON THIS AND NOT ON THE PERCENT SIGN.
# `episodes`, `events` and `risk_sets` each carry a literal `%s` inside an ordinary static
# `FORMAT` call building an identifier string, and all three would false-positive on a percent
# test while none of them is a template and none of them needs substituting.
_EXECUTE_IMMEDIATE = "EXECUTE IMMEDIATE FORMAT("

# The payload of `EXECUTE IMMEDIATE FORMAT("""...""", arg, arg);`.  The argument list is matched
# as "no closing parenthesis", which is exact here because both templates take bare identifiers
# and nothing else; a future argument carrying a parenthesis would fail this match rather than
# being silently truncated, and failing is the right outcome for a template nobody has priced.
_EXECUTE_IMMEDIATE_RE = re.compile(
    r'EXECUTE\s+IMMEDIATE\s+FORMAT\(\s*"""(?P<template>.*?)"""\s*,(?P<args>[^)]*)\)\s*;',
    re.DOTALL,
)

# The `IF <cond> THEN ... ELSE ... END IF;` wrapper `device_daily` sits inside.  Its THEN branch
# creates the table empty with its schema intact, which is the zero-byte case, and its ELSE
# branch is the template.  Which one executes depends on a runtime parameter, so which one gets
# priced does too.
_IF_ELSE_RE = re.compile(
    r"^\s*IF\s+(?P<condition>.+?)\s+THEN\s*\n(?P<then_branch>.*?)\n\s*ELSE\s*\n"
    r"(?P<else_branch>.*?)\n\s*END IF;\s*$",
    re.DOTALL,
)

# `build_params` is the ONE stage whose body cannot be lifted as it stands, because it is the
# stage that turns procedure variables INTO the table every other body reads.  Its expressions
# are the bare parameter names, each aliased to itself.  The pattern below matches exactly that
# shape, `<name> AS <same name>`, so `CURRENT_TIMESTAMP() AS built_at` and the observation-period
# subquery are left alone, and a parameter renamed on one side of the `AS` stops matching rather
# than being substituted into the wrong column.
_SELF_ALIASED_RE = re.compile(
    r"^(?P<indent>\s*)(?P<name>[a-z_][a-z0-9_]*)(?P<gap>\s+AS\s+)(?P=name)(?P<tail>,?)\s*$")


def read_build_sql(path: str | Path | None = None) -> str:
    """Read `build_all.sql` off disk.  Defaults to the copy beside this file."""
    target = Path(path) if path is not None else _HERE / DEFAULT_BUILD_SQL_NAME
    if not target.is_file():
        raise StageMarkerError(
            f"the DAG file was not found at {target}. This module prices and calls "
            f"{DEFAULT_BUILD_SQL_NAME}; pass its path if it does not sit beside this file."
        )
    return target.read_text(encoding="utf-8")


def strip_line_comments(body: str) -> str:
    """Drop whole-line SQL comments.  Whole-line only, and that restraint is deliberate.

    Two reasons, and the second is the one that matters.  A comment costs nothing at a dry run,
    so removing it changes no estimate.  But the `%s` COUNT is meaningless unless comments are
    gone first: `hr_daily`'s body carries three `%s`, one of which sits in the comment explaining
    what the other two are for, and `device_daily`'s carries two for the same reason.  Counting
    the raw body would say three arguments where the template takes two, and substituting into
    the raw body would consume the comment's marker as a substitution position.

    Only lines whose stripped form BEGINS with the comment marker are dropped, never a trailing
    comment on a code line, because this function cannot tell a comment marker from two hyphens
    inside a string literal and a wrong removal there would corrupt a statement silently.
    """
    return "\n".join(line for line in body.splitlines() if not _LINE_COMMENT_RE.match(line))


def split_stages(sql_text: str) -> tuple[Mapping[str, Any], ...]:
    """Split `build_all.sql` on its stage markers.  Returns one mapping per stage, in DAG order.

    Every failure here is a defect in the SQL file rather than in the data, so each raises with
    the marker it was reading when it gave up.  Nothing has been submitted at this point and
    nothing has billed.
    """
    stages: list[dict[str, Any]] = []
    current: str | None = None
    buffer: list[str] = []
    begin_line = 0

    for number, line in enumerate(sql_text.splitlines(), start=1):
        begin = _STAGE_BEGIN_RE.match(line)
        end = _STAGE_END_RE.match(line)
        if begin:
            if current is not None:
                raise StageMarkerError(
                    f"a stage begin marker for {begin.group('name')!r} at line {number} opened "
                    f"while {current!r} was still open at line {begin_line}. The markers do not "
                    f"nest and every begin must be closed before the next one opens."
                )
            current, buffer, begin_line = begin.group("name"), [], number
            continue
        if end:
            name = end.group("name")
            if current is None:
                raise StageMarkerError(
                    f"a stage end marker for {name!r} at line {number} closes a stage that was "
                    f"never opened."
                )
            if name != current:
                raise StageMarkerError(
                    f"the stage opened as {current!r} at line {begin_line} is closed as {name!r} "
                    f"at line {number}. The two names must match exactly."
                )
            stages.append({
                "name": name,
                "body": "\n".join(buffer),
                "first_line": begin_line + 1,
                "last_line": number - 1,
            })
            current, buffer = None, []
            continue
        if current is not None:
            buffer.append(line)

    if current is not None:
        raise StageMarkerError(
            f"the stage opened as {current!r} at line {begin_line} is never closed.")

    names = tuple(stage["name"] for stage in stages)
    if names != STAGE_ORDER:
        # Both directions, because the two failures need different fixes: a stage present in the
        # SQL and absent here is unpriced, and a stage present here and absent there is a stale
        # transcription.  The message says which happened rather than "they differ".
        missing = [name for name in STAGE_ORDER if name not in names]
        extra = [name for name in names if name not in STAGE_ORDER]
        raise StageMarkerError(
            f"the DAG file splits into {len(names)} stage(s) and this module prices "
            f"{N_STAGES} in a fixed order. Not found in the file: {missing or 'none'}. Found in "
            f"the file and unknown here: {extra or 'none'}. Order as read: {list(names)}."
        )

    _assert_procedure_stage_declaration(sql_text)

    for stage in stages:
        stripped = strip_line_comments(stage["body"])
        args_lines = [_STAGE_FORMAT_ARGS_RE.match(line).group("args")
                      for line in stage["body"].splitlines()
                      if _STAGE_FORMAT_ARGS_RE.match(line)]
        if len(args_lines) > 1:
            raise StageMarkerError(
                f"stage {stage['name']!r} carries {len(args_lines)} format-argument marker "
                f"lines. One body, one marker.")
        stage["is_template"] = _EXECUTE_IMMEDIATE in stripped
        stage["format_args"] = (
            tuple(name.strip() for name in args_lines[0].split(",")) if args_lines else ())
        stage["n_placeholders"] = stripped.count("%s")
        stage["stripped"] = stripped
        stage["index"] = STAGE_ORDER.index(stage["name"]) + 1

    _assert_template_markers(stages)
    return tuple(MappingProxyType(stage) for stage in stages)


def _assert_procedure_stage_declaration(sql_text: str) -> None:
    """Hold `STAGE_ORDER` to the procedure's OWN two declarations of the same order.

    THE MARKERS ARE NOT THE AUTHORITY ON DAG ORDER AND CHECKING AGAINST THEM CHECKS NOTHING.
    `@stage-begin:` is a lexical delimiter that says where a body starts.  What decides what a
    resume actually rebuilds is the procedure's `DECLARE stages ARRAY<STRING>`, which turns a
    `start_stage` NAME into a `start_ix` NUMBER, and the `IF start_ix <= N THEN` guard wrapping
    each body, which compares that number.  Those two are a separate transcription of the same
    order, hand-maintained, and inserting a stage mid-DAG forces every guard below it to be
    renumbered by hand.  A guard left one too low silently rebuilds a stage the resume point was
    supposed to skip; one too high silently skips the stage the human asked for.  Neither shows
    up in the marker names, in the priced set, or in any count.

    So all THREE are held to each other here: this module's tuple, the procedure's array, and
    the guards.  `build_params` is the one stage with no guard, because it is always rewritten
    whatever the resume point says, and its absence is asserted rather than tolerated.
    """
    declaration = _STAGES_DECLARATION_RE.search(sql_text)
    if declaration is None:
        raise StageMarkerError(
            "the DAG file carries no `DECLARE stages ARRAY<STRING>` block. That array is what "
            "the procedure resolves a start_stage name against, so without it the resume flag "
            "means nothing and this module cannot check the order it prices."
        )
    declared = tuple(re.findall(r"'([A-Za-z_][A-Za-z0-9_]*)'", declaration.group("body")))
    if declared != STAGE_ORDER:
        raise StageMarkerError(
            f"the procedure declares its stages as {list(declared)} and this module prices "
            f"{list(STAGE_ORDER)}. The index of a name in that array IS the start_ix its guard "
            f"compares against, so a disagreement here misdirects every resume."
        )

    # The guard governing a body is the last one opened before its begin marker, not the line
    # immediately above it: `features` carries ten lines of comment between the two.
    guards: dict[str, int | None] = {}
    pending: int | None = None
    for line in sql_text.splitlines():
        guard = _STAGE_GUARD_RE.match(line)
        if guard:
            pending = int(guard.group("index"))
            continue
        begin = _STAGE_BEGIN_RE.match(line)
        if begin:
            guards[begin.group("name")] = pending
            pending = None

    for position, name in enumerate(STAGE_ORDER, start=1):
        found = guards.get(name)
        if name == STAGE_ORDER[0]:
            if found is not None:
                raise StageMarkerError(
                    f"stage {name!r} sits inside an `IF start_ix <= {found} THEN` guard. It is "
                    f"the parameter table and is ALWAYS rewritten, whatever the resume point "
                    f"says, because it is the record of what the run was called with."
                )
            continue
        if found is None:
            raise StageMarkerError(
                f"stage {name!r} sits inside no `IF start_ix <= N THEN` guard, so a resume past "
                f"it would rebuild it anyway and a resume at it would price a stage the "
                f"procedure runs unconditionally."
            )
        if found != position:
            raise StageMarkerError(
                f"stage {name!r} is number {position} in the DAG and its guard reads "
                f"`IF start_ix <= {found} THEN`. A guard below its own index silently rebuilds "
                f"a stage the resume point excluded; one above it silently skips the stage the "
                f"resume point named. Renumber the guards under the inserted stage."
            )


def _assert_template_markers(stages: Sequence[Mapping[str, Any]]) -> None:
    """Assert the format-argument contract IN BOTH DIRECTIONS.

    A body containing the dynamic-statement marker MUST carry a format-argument line, a body
    carrying the line MUST contain the marker, and the number of names on the line MUST equal
    the number of substitution positions in the template.  A stage that becomes a template later
    fails this rather than being priced against a query that is not the one that will execute.
    """
    templated = tuple(stage["name"] for stage in stages if stage["is_template"])
    declared = tuple(stage["name"] for stage in stages if stage["format_args"])
    expected = tuple(FORMAT_TEMPLATE_STAGES)

    if templated != expected:
        raise StageMarkerError(
            f"the stages built with a dynamic statement are {list(templated)}; this module "
            f"prices {list(expected)}. A stage that has become a template must be substituted "
            f"before its dry run, or the estimate prices a query that will not execute and its "
            f"cap is sized against the wrong number."
        )
    if declared != expected:
        raise StageMarkerError(
            f"the stages carrying a format-argument marker are {list(declared)}; the stages "
            f"built with a dynamic statement are {list(templated)}. Every template declares its "
            f"arguments and nothing else declares any."
        )
    for stage in stages:
        if not stage["format_args"]:
            continue
        if len(stage["format_args"]) != stage["n_placeholders"]:
            raise StageMarkerError(
                f"stage {stage['name']!r} declares {len(stage['format_args'])} format "
                f"argument(s) {list(stage['format_args'])} and its template carries "
                f"{stage['n_placeholders']} substitution position(s). They must match."
            )
        parameter = FORMAT_TEMPLATE_STAGES[stage["name"]]
        if set(stage["format_args"]) != {parameter}:
            raise StageMarkerError(
                f"stage {stage['name']!r} declares {list(stage['format_args'])} and this module "
                f"substitutes {parameter!r} into it. A template taking a different parameter "
                f"needs a decision here, not a guess."
            )
        # No percent sign other than the substitution positions.  Both templates are documented
        # as carrying none, and one added without being doubled would corrupt the statement.
        if stage["stripped"].count("%") != stage["n_placeholders"]:
            raise StageMarkerError(
                f"stage {stage['name']!r} carries a percent sign that is not a substitution "
                f"position. A literal percent in a format template must be doubled."
            )


# ======================================================================================
# (4) Run parameters, and making each stage body standalone.
# ======================================================================================

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
JUNCTION_MAPS: tuple[str, ...] = ("primary", "mirrored")
WEAR_DEFINITIONS: tuple[str, ...] = ("primary", "s2")

# Internal constants of the procedure, not parameters, repeated here only so `build_params` can
# be made standalone for its dry run.  ANALYSIS-PLAN 4.5 and 10 pin the seed and a knob that can
# only break reproducibility is worse than no knob.
SAMPLING_SALT = "spinewear-v1-risk-set"


def _sql_string(value: str) -> str:
    """One SQL string literal, refusing anything that could close it.

    Every value reaching here has already been checked against a closed vocabulary or an
    identifier pattern, so this cannot fire in normal use. It is the second lock on the door
    the identifier regex is the first lock on, and it costs one comparison.
    """
    if "'" in value or "\\" in value or "\n" in value:
        raise CohortError(
            "a run parameter carries a quote, a backslash or a newline and is refused rather "
            "than escaped. These values are column names and closed-vocabulary slugs; one that "
            "needs escaping is one that is wrong."
        )
    return f"'{value}'"


def _sql_int_array(values: Sequence[int]) -> str:
    """One SQL array literal of integers.  Refuses an empty array and anything not an integer."""
    if not values:
        raise CohortError(
            "a visit concept array is empty. The procedure refuses both arrays empty for the "
            "same reason this does: an empty array would silently make every acute-care event "
            "and every emergency-department exclusion count zero, which reads as a finding."
        )
    out: list[str] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise CohortError(
                "a visit concept id is not an integer. They are enumerated against the CDR's "
                "own distribution by the probe and are never strings."
            )
        out.append(str(value))
    return "[" + ", ".join(out) + "]"


def dag_parameters(
    *,
    hr_minute_column: str,
    device_model_column: str = "",
    ed_visit_concept_ids: Sequence[int],
    inpatient_visit_concept_ids: Sequence[int],
    junction_map: str = "primary",
    primary_wear_definition: str = "primary",
) -> Mapping[str, Any]:
    """Validate the six run parameters and return them frozen.

    The same checks the procedure runs, run here so a bad value costs nothing instead of costing
    a submitted job.  The two column names are interpolated into dynamic SQL, so the identifier
    pattern is the whole defence and it is applied on both sides of the boundary.
    """
    if junction_map not in JUNCTION_MAPS:
        raise CohortError(
            f"the junction map must be one of {list(JUNCTION_MAPS)}. Under the mirrored map an "
            f"episode whose only evidence is cervicothoracic moves from cervical to "
            f"thoracic-only, that is from included to excluded, so the two runs legitimately "
            f"produce different ladders and each carries its own map on every row."
        )
    if primary_wear_definition not in WEAR_DEFINITIONS:
        raise CohortError(
            f"the primary wear definition must be one of {list(WEAR_DEFINITIONS)}. The second "
            f"is the prespecified contingency of ANALYSIS-PLAN 2.1, invoked only when the "
            f"zone-partition probe fails and the substitution is logged as an amendment."
        )
    if not _IDENTIFIER_RE.match(str(hr_minute_column or "")):
        raise CohortError(
            "the heart-rate zone-minute column is not a bare SQL identifier. It is a runtime "
            "probe result and it is interpolated into a dynamic statement; run 01_probe.py and "
            "pass the name it reports."
        )
    if device_model_column and not _IDENTIFIER_RE.match(device_model_column):
        raise CohortError(
            "the device model column is not a bare SQL identifier. Pass the empty string when "
            "the device table carries no usable model column, in which case every episode takes "
            "the unknown device family and the feature table records that it did."
        )
    return MappingProxyType({
        "junction_map": junction_map,
        "hr_minute_column": str(hr_minute_column),
        "device_model_column": str(device_model_column or ""),
        "ed_visit_concept_ids": tuple(int(v) for v in ed_visit_concept_ids),
        "inpatient_visit_concept_ids": tuple(int(v) for v in inpatient_visit_concept_ids),
        "primary_wear_definition": primary_wear_definition,
        "seed": SEED,
        "sampling_salt": SAMPLING_SALT,
    })


def _parameter_literals(params: Mapping[str, Any]) -> Mapping[str, str]:
    """Each run parameter as the SQL literal that stands in for it in a lifted stage body."""
    return MappingProxyType({
        "junction_map": _sql_string(params["junction_map"]),
        "hr_minute_column": _sql_string(params["hr_minute_column"]),
        "device_model_column": _sql_string(params["device_model_column"]),
        "ed_visit_concept_ids": _sql_int_array(params["ed_visit_concept_ids"]),
        "inpatient_visit_concept_ids": _sql_int_array(params["inpatient_visit_concept_ids"]),
        "primary_wear_definition": _sql_string(params["primary_wear_definition"]),
        "seed": str(int(params["seed"])),
        "sampling_salt": _sql_string(params["sampling_salt"]),
    })


def _substitute_self_aliased(body: str, literals: Mapping[str, str]) -> str:
    """Replace `<parameter> AS <parameter>` with `<literal> AS <parameter>`, line by line.

    This is what makes `build_params` dry-runnable.  It is the one stage whose body reads
    procedure variables rather than the parameter table, because it is the stage that CREATES
    the parameter table, so lifting it without this leaves eight unresolved names and the dry run
    fails on a syntax error that reads like a placeholder problem.

    Sequential and shape-restricted on purpose.  It matches only an expression that is a bare
    name aliased to that same name, so nothing that is a real expression is touched, and a
    parameter renamed on one side of the alias stops matching rather than being substituted into
    the wrong column.
    """
    out: list[str] = []
    for line in body.splitlines():
        match = _SELF_ALIASED_RE.match(line)
        if match and match.group("name") in literals:
            out.append(f"{match.group('indent')}{literals[match.group('name')]}"
                       f"{match.group('gap')}{match.group('name')}{match.group('tail')}")
        else:
            out.append(line)
    return "\n".join(out)


def _substitute_format_args(template: str, arguments: Sequence[str]) -> str:
    """Fill a `FORMAT` template's substitution positions, left to right.

    Written as a sequential walk rather than Python's own percent operator, because the operator
    would also consume any other percent sign in the text and would fail on a doubled one with a
    message about format strings rather than about SQL.  Here a count mismatch is named for what
    it is, and a surviving position is a stop condition.
    """
    out = template
    for argument in arguments:
        if "%s" not in out:
            raise StageMarkerError(
                "a format template ran out of substitution positions before it ran out of "
                "arguments, so the estimate would price a query that will not execute."
            )
        out = out.replace("%s", argument, 1)
    if "%s" in out:
        raise StageMarkerError(
            "a substitution position survived the format arguments, so the dry run would price "
            "a query that will not execute and this stage's cap would be sized against the "
            "wrong number."
        )
    return out


def stage_priceable_sql(stage: Mapping[str, Any], *, params: Mapping[str, Any]) -> str:
    """The standalone SQL this module dry-runs to price one stage.

    Three shapes, and which one a stage takes is read off the body rather than off its name:

      * the ordinary stage, whose body is already standalone because it reads its run parameters
        out of the parameter table;
      * `build_params`, whose body is the one that WRITES that table, so its parameter names are
        substituted for literals first;
      * a `FORMAT` template, whose executed statement is the string inside the dynamic call and
        not the call itself.  A dry run of the call would report zero bytes, because a dynamic
        statement is a script, so the template is unwrapped and substituted and the priced text
        is the statement that will actually run.

    `device_daily` is the shape that gets missed, and it is handled explicitly: when the device
    model column is unavailable the procedure takes the branch that creates the table empty, so
    that branch is what gets priced, and the template beside it is never submitted.
    """
    literals = _parameter_literals(params)
    body = strip_line_comments(stage["body"])

    if stage["name"] == "build_params":
        return _substitute_self_aliased(body, literals).strip()

    if not stage["is_template"]:
        return body.strip()

    parameter = FORMAT_TEMPLATE_STAGES[stage["name"]]
    value = params[parameter]

    branch = _IF_ELSE_RE.match(body.strip())
    if branch and not value:
        # The empty-column case.  The THEN branch creates the table with its schema and no rows
        # and reads nothing, so it is priced at whatever a schema-only statement costs, which is
        # nothing, and the template is correctly left unpriced because it will not run.
        return branch.group("then_branch").strip()

    if not value:
        raise StageMarkerError(
            f"stage {stage['name']!r} is a format template, its parameter is empty, and the body "
            f"carries no branch for the empty case. There is nothing to price and nothing safe "
            f"to guess."
        )

    dynamic = _EXECUTE_IMMEDIATE_RE.search(body)
    if dynamic is None:
        raise StageMarkerError(
            f"stage {stage['name']!r} is marked as a format template and its dynamic statement "
            f"could not be read out of the body. The estimate would price the wrapper rather "
            f"than the statement, which reports zero bytes and would leave this stage uncapped "
            f"in practice."
        )
    declared = tuple(name.strip() for name in dynamic.group("args").split(","))
    if declared != tuple(stage["format_args"]):
        raise StageMarkerError(
            f"stage {stage['name']!r} declares format arguments {list(stage['format_args'])} on "
            f"its marker line and passes {list(declared)} to the dynamic statement. The marker "
            f"is the checkable half and it must match what is passed."
        )
    return _substitute_format_args(dynamic.group("template"),
                                   [value] * len(declared)).strip()


# ======================================================================================
# (5) THE COST MODEL, AND THE ONE FACT THAT COSTS MONEY IF IT IS MISSED.
#
# `maximum_bytes_billed` on a BigQuery script is enforced PER CHILD JOB, not across the script.
# `CALL` is a script job.  Each of the nineteen stages inside it is a child job the cap is
# applied to individually.  So:
#
#   A cap sized to the nineteen-stage TOTAL does not bound the run.  It permits EACH of the
#   nineteen stages to bill up to that total, which is up to nineteen times the number the human
#   approved, and it would not fail on any stage a per-stage cap would have caught.  The whole
#   point of the cap is that an over-budget query fails rather than bills.
#
# The cap this module hands the query path is therefore derived from the LARGEST PER-STAGE
# ESTIMATE, plus a stated margin, never from the sum.  The largest is the largest a single legal
# child job may bill, so it is the tightest cap that does not kill the run, and it is what
# "size the cap per stage" reduces to when the nineteen stages are submitted as one script.
#
# The SUM is still computed and shown.  It is the approval figure a human signs off on before
# anything is submitted, and the refusal above `DAG_BUDGET_GB` is checked against it.  It is not
# a thing BigQuery enforces and this module never presents it as one.  The worst case the cap
# permits is printed beside it, in the same units, so nobody has to work it out.
# ======================================================================================

# Headroom over a stage's own estimate.  A dry-run estimate is a plan against current table
# statistics; the executed job can read slightly more when a statistic is stale or a partition
# prunes differently at run time, and a cap set exactly at the estimate turns that into a
# failure rather than a few extra megabytes.
STAGE_CAP_MARGIN = 0.25

# The floor under a per-stage cap.  BigQuery bills a ten-megabyte minimum per table scanned, and
# several stages here are estimated at or near zero because they read only derived tables, so a
# cap computed as "estimate plus a quarter" would land under the minimum and refuse a free
# query.  One gibibyte is about six tenths of a cent.
STAGE_CAP_FLOOR_GB = 1.0

# The approval figure for one full DAG build, checked against the priced SUM before anything is
# submitted.  DAG-SCHEMA.md 5.4 puts the whole project's BigQuery budget under two dollars, of
# which Phase 2's probe and pre-gate have already spent a share, so this leaves room for a
# re-run rather than consuming the lot on the first one.  Raise it deliberately, with the
# measured number in hand, never to get past a refusal.
DAG_BUDGET_GB = 200.0


def gb_to_usd(gb: float) -> float:
    """Dollars for a byte count, at the list price.  Display only; enforcement is in bytes."""
    return float(gb) / 1024.0 * USD_PER_TIB


def stage_cap_gb(estimate_gb: float) -> float:
    """The `maximum_bytes_billed` cap for ONE stage, from THAT stage's own estimate."""
    if estimate_gb < 0:
        raise CohortError("a dry-run estimate came back negative, which is not a byte count")
    return max(float(estimate_gb) * (1.0 + STAGE_CAP_MARGIN), STAGE_CAP_FLOOR_GB)


def _stages_to_run(stages: Sequence[Mapping[str, Any]], start_stage: str) -> tuple[Mapping[str, Any], ...]:
    """The stages a `CALL` with this resume point will actually build.

    `build_params` is ALWAYS rewritten, whatever the resume point says, because it is the record
    of what this run was called with, so it is always in the priced set even when the resume
    point sits past it.
    """
    if not start_stage:
        return tuple(stages)
    if start_stage not in STAGE_ORDER:
        raise CohortError(
            f"{start_stage!r} is not a stage. Pass the empty string to build everything, or one "
            f"of {list(STAGE_ORDER)}, in DAG order."
        )
    start_index = STAGE_ORDER.index(start_stage) + 1
    return tuple(stage for stage in stages
                 if stage["index"] == 1 or stage["index"] >= start_index)


def price_dag(
    *,
    params: Mapping[str, Any],
    dry_run_gb: Callable[[str], float],
    stages: Sequence[Mapping[str, Any]] | None = None,
    start_stage: str = "",
    budget_gb: float = DAG_BUDGET_GB,
) -> Mapping[str, Any]:
    """Dry-run every stage that this run will build, and price it, before any of it executes.

    A dry run is free and prices the COLUMNS REFERENCED rather than the table, so the whole
    pre-flight costs nothing and the frightening question is answered for nothing first.  The
    refusal, if it comes, arrives with the measured total in the human's hand rather than after
    the bill.
    """
    if stages is None:
        stages = split_stages(read_build_sql())
    selected = _stages_to_run(stages, start_stage)

    priced: list[dict[str, Any]] = []
    for stage in selected:
        sql = stage_priceable_sql(stage, params=params)
        estimate = float(dry_run_gb(sql))
        priced.append({
            "name": stage["name"],
            "index": stage["index"],
            "gb": estimate,
            "usd": gb_to_usd(estimate),
            "cap_gb": stage_cap_gb(estimate),
            "is_template": bool(stage["is_template"]),
            "sql": sql,
        })

    total_gb = sum(row["gb"] for row in priced)
    binding = max(priced, key=lambda row: row["gb"]) if priced else None
    call_cap = max((row["cap_gb"] for row in priced), default=STAGE_CAP_FLOOR_GB)

    plan: dict[str, Any] = {
        "stages": tuple(MappingProxyType(row) for row in priced),
        "start stage": start_stage,
        "total gb": total_gb,
        "total usd": gb_to_usd(total_gb),
        "binding stage": binding["name"] if binding else "",
        "binding gb": binding["gb"] if binding else 0.0,
        "call cap gb": call_cap,
        "worst case gb": call_cap * len(priced),
        "budget gb": float(budget_gb),
        "within budget": total_gb <= float(budget_gb),
    }
    if not plan["within budget"]:
        raise CohortBudgetExceeded(
            f"the DAG prices at {total_gb:,.3f} GB, about ${gb_to_usd(total_gb):,.2f}, against "
            f"an approval figure of {float(budget_gb):,.1f} GB, about "
            f"${gb_to_usd(budget_gb):,.2f}. Nothing was submitted and nothing billed. The "
            f"binding stage is {plan['binding stage']!r} at {plan['binding gb']:,.3f} GB. "
            f"Either narrow that stage or raise the figure deliberately, with this number in "
            f"hand."
        )
    return MappingProxyType(plan)


# ======================================================================================
# (6) The CALL, and the resumed session.
# ======================================================================================

def build_call_sql(*, params: Mapping[str, Any], start_stage: str = "") -> str:
    """The one statement that builds the DAG.  Seven arguments, positional, `start_stage` last.

    BigQuery `CALL` takes its arguments positionally, so the order below is the contract and a
    reordered argument list is a silently different run rather than an error.  It is written out
    one argument per line, with the parameter it fills named in a trailing comment, so the two
    can be read against DAG-SCHEMA.md section 2 side by side.
    """
    if start_stage and start_stage not in STAGE_ORDER:
        raise CohortError(
            f"{start_stage!r} is not a stage. Pass the empty string to build everything, or one "
            f"of {list(STAGE_ORDER)}, in DAG order."
        )
    literals = _parameter_literals(params)
    return (
        "CALL `{DERIVED}.build_all`(\n"
        f"  {literals['junction_map']},\n"
        f"  {literals['hr_minute_column']},\n"
        f"  {literals['device_model_column']},\n"
        f"  {literals['ed_visit_concept_ids']},\n"
        f"  {literals['inpatient_visit_concept_ids']},\n"
        f"  {literals['primary_wear_definition']},\n"
        f"  {_sql_string(start_stage)}\n"
        ")"
    )


def run_dag(
    *,
    params: Mapping[str, Any],
    plan: Mapping[str, Any],
    q_guarded: Callable[..., pd.DataFrame],
    start_stage: str = "",
    announce: bool = True,
) -> Mapping[str, Any]:
    """Submit the `CALL` under the per-stage cap, and return what was run.

    The cap comes off the plan's binding stage and NOT off its total, for the reason written out
    at the head of section 5: BigQuery applies it to each of the nineteen child jobs
    individually, so a total-sized cap bounds nothing.
    """
    sql = build_call_sql(params=params, start_stage=start_stage)
    cap = float(plan["call cap gb"])
    note = (f"build_all, {len(plan['stages'])} stage(s), per-child-job cap {cap:,.3f} GB sized "
            f"on {plan['binding stage']}")
    # The query path dry-runs everything it submits, which is the rule and is why it is the only
    # path. On a script that dry run reports ZERO BYTES, because it prices the CALL and not the
    # nineteen child jobs inside it, and a reader who takes that zero at face value has read the
    # one number on the screen that is not an estimate of anything. Said out loud immediately
    # before it appears, rather than left for somebody to work out afterwards.
    if announce:
        print(f"The dry run below prices the call itself and will report nothing, because a "
              f"script job does not price its children. The estimate for this run is the "
              f"{plan['total gb']:,.3f} GB in the table above.")
    q_guarded(sql, max_gb=cap, note=note)
    return MappingProxyType({
        "called": True,
        "start stage": start_stage,
        "stages built": tuple(row["name"] for row in plan["stages"]),
        "cap gb": cap,
        "note": note,
    })


# ======================================================================================
# (7) Reading the ladder, and the assertions that can actually fail.
#
# WHAT `closes_exact` PROVES, AND WHERE IT IS EMPTY.  DAG-SCHEMA.md 8.15 and `build_all.sql`
# carry the same map, and it has to be read before the column is treated as evidence.  The
# procedure computes `n_out` AS `n_in - n_dropped` on steps 3 to 15 and 18, computes `n_dropped`
# AS a difference on steps 1 and 2, and writes steps 16, 17 and 19 from the same expressions
# their neighbours use.  So on EIGHTEEN of the nineteen rungs the rung's own test compares an
# expression against itself and cannot go false.  ONE identity is independently tested, at step
# 16, which reconciles the eligible count against the first-failing-rung histogram: two
# different aggregations of the exclusions table that a real defect can separate.
#
# THIS MODULE THEREFORE DOES NOT READ THE COLUMN AS NINETEEN CHECKS, and it does not re-derive
# confidence from the column being uniformly true.  It asks a different question at each rung,
# and it labels every answer as one of two kinds, which is what the report prints:
#
#   INDEPENDENT.  The check compares the table against something the table did not compute for
#   itself: this module's transcription of the plan, the run parameters it was called with, or a
#   second count taken off `episodes_eligible` in its own query.  These can fail on a correct
#   build and are the reason this module exists.
#
#   TRANSPORT.  The check recomputes an identity that was a tautology in SQL.  It can still
#   fail, but only for a table that was hand-edited, truncated, partially rebuilt, or read from
#   an older build than the one just priced, which is a real and recurring situation in a
#   resumed session and is exactly what a resume flag makes easy.  It is not evidence that the
#   arithmetic upstream was checked.
#
# An assertion nobody can describe the failure of is decoration, so every check below carries
# its kind and the report prints the census.
# ======================================================================================

LADDER_COLUMNS: tuple[str, ...] = (
    "step", "slug", "kind", "unit", "n_in", "n_dropped", "n_out", "n_carried_forward",
    "reason", "closes_exact", "junction_map", "built_at",
)

LADDER_SQL = """
SELECT
  step, slug, kind, unit,
  n_in, n_dropped, n_out, n_carried_forward,
  reason, closes_exact, junction_map, built_at
FROM `{DERIVED}.attrition`
ORDER BY step
"""

# The independent reconciliation.  Seven aggregates over two derived tables, two columns of one
# and one of the other, so it is cents at most and it is the only check in this module that
# asks the data a question the ladder did not already answer for itself.
#
# It tests four things the ladder cannot test alone:
#   the eligibility flag and the first-failing rung are a PARTITION of the exclusions table,
#     with no episode both eligible and charged and none neither;
#   every charged episode is charged to a rung that exists;
#   the exclusions table is one row per EPISODE and not the filtered survivor set, which is the
#     single most common misreading of that table;
#   and the three counts the ladder's own step 16 identity rests on, recomputed here.
RECONCILIATION_SQL = """
SELECT
  (SELECT COUNT(*) FROM `{DERIVED}.episodes`)                              AS n_episodes,
  (SELECT COUNT(*) FROM `{DERIVED}.episodes_eligible`)                     AS n_exclusion_rows,
  (SELECT COUNTIF(is_eligible) FROM `{DERIVED}.episodes_eligible`)         AS n_eligible,
  (SELECT COUNTIF(first_fail_step IS NOT NULL)
     FROM `{DERIVED}.episodes_eligible`)                                   AS n_charged,
  (SELECT COUNTIF(is_eligible AND first_fail_step IS NOT NULL)
     FROM `{DERIVED}.episodes_eligible`)                                   AS n_eligible_and_charged,
  (SELECT COUNTIF(NOT is_eligible AND first_fail_step IS NULL)
     FROM `{DERIVED}.episodes_eligible`)                                   AS n_neither,
  (SELECT COUNTIF(first_fail_step IS NOT NULL
                  AND first_fail_step NOT BETWEEN 3 AND 15)
     FROM `{DERIVED}.episodes_eligible`)                                   AS n_charged_off_ladder
"""

LADDER_MAX_GB = 1.0
RECONCILIATION_MAX_GB = 4.0
LEDGER_MAX_GB = 1.0
GROUP_COUNT_MAX_GB = 1.0


def _disclosed(true_count: Any) -> str:
    """Round one TRUE count and render it.  The boundary, and the only place rounding happens.

    `disclosable()` is asked of the true integer, inside `round20`, before rounding.
    `is_legal_disclosed_count()` is asked of what comes back, which is the other predicate and
    the other moment: the two disagree on 20 by design, because a TRUE 20 is below the floor
    while a RENDERED 20 is what a true count of 21 to 29 rounds to.

    The RENDERING is `disclosure.render_count`'s and is not reimplemented here.  This function
    owns the rounding and the legality test, which are the disclosure decisions; the thousands
    separator is a house style held in one place for the whole project.
    """
    rendered = round20(true_count)
    if not is_legal_disclosed_count(rendered):
        raise CohortError(
            "a rounded count is not a legal disclosed cell, which means it reached this point "
            "unrounded or was rounded to something the policy does not produce."
        )
    return render_count(rendered)


def _as_int(value: Any, *, where: str) -> int | None:
    """One count out of a frame, as an exact integer or None.  Nothing else is a count.

    Every count in the derived dataset is a TRUE INTEGER.  A float arriving here is a real
    defect and not a dtype inconvenience: it means an aggregate was averaged somewhere, or a
    left join widened an integer column into a nullable float and lost precision on the way.
    The value is never quoted in the message, because this renders into a notebook traceback,
    which is the model-visible surface the whole disclosure policy protects.
    """
    if value is None or value is pd.NA:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        raise LadderClosureError(f"{where} holds a boolean where a count belongs")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise LadderClosureError(f"{where} holds a value that is not a count") from None
    if number != int(number):
        raise LadderClosureError(
            f"{where} is not a whole number. Every count in the derived dataset is a true "
            f"integer, so a fraction here is an aggregate that was averaged rather than counted."
        )
    return int(number)


class _Checks:
    """A running census of assertions, each labelled independent or transport.

    Every check raises on failure, which is what a stop condition means in this project.  The
    census exists so the printed report can say how many of each kind ran, rather than offering
    a bare count of assertions that hides the fact that most of them are transport.
    """

    def __init__(self) -> None:
        self.independent = 0
        self.transport = 0
        self.log: list[tuple[str, str]] = []

    def require(self, condition: bool, kind: str, name: str, message: str) -> None:
        if kind == "independent":
            self.independent += 1
        elif kind == "transport":
            self.transport += 1
        else:                                        # pragma: no cover - a programming error
            raise CohortError(f"a check declared an unknown kind {kind!r}")
        self.log.append((kind, name))
        if not condition:
            raise LadderClosureError(f"{name}: {message}")

    @property
    def total(self) -> int:
        return self.independent + self.transport


def assert_ladder(
    frame: pd.DataFrame,
    *,
    junction_map: str | None = None,
) -> Mapping[str, Any]:
    """The nineteen-rung closure assert.  Raises `LadderClosureError` on the first failure.

    CLAUDE.md stop condition 3.  There is no longer a single global identity and treating it as
    one fails on the first real run, because the ladder crosses TWO unit changes.  Four rules,
    and a fifth uniform one:

      1. Every EXCLUSION rung: entering less removed equals leaving, both sides in one unit.
      2. Step 2 CANNOT assert that, because it enters in persons and leaves in episodes.  It
         carries a third count in PERSONS and asserts entering less removed equals carried
         forward, together with leaving at least carried forward, since a carried person yields
         at least one episode.  An explicitly labelled re-basing, never a silent one.
      3. Within the EPISODE unit, the removals of steps 3 to 15 plus the analytic count of step
         16 equal what left step 2.  This is the assert steps 4, 7, 8 and 13 would break if they
         were left implicit, which is the reason they are rungs and not prose.
      4. Steps 17 and 19 count EVENTS, carry no removal, are EXCLUDED from rule 3, and close
         among themselves.
      5. Uniform over all nineteen: what enters a rung is what left the one before it.  It holds
         across both conversions, because a conversion re-bases the unit but not the count.

    If it does not close, raise.  Do not adjust a count to make it close.
    """
    checks = _Checks()

    missing = [column for column in LADDER_COLUMNS if column not in frame.columns]
    checks.require(
        not missing, "independent", "ladder columns",
        f"the ladder is missing column(s) {missing}. DAG-SCHEMA.md 8.15 fixes the column set "
        f"and a ladder without them is not the ladder this module asserts on.")

    checks.require(
        len(frame) == len(ATTRITION_RUNGS), "independent", "nineteen rungs",
        f"the ladder has {len(frame)} row(s) and ANALYSIS-PLAN.md section 2.6 fixes "
        f"{len(ATTRITION_RUNGS)}. A missing rung is an uncounted reduction and it breaks the "
        f"episode-unit identity on the first real run.")

    rows = frame.sort_values("step").reset_index(drop=True) if "step" in frame else frame
    steps = tuple(_as_int(value, where=f"the step column at row {position}")
                  for position, value in enumerate(rows["step"], start=1))
    checks.require(
        steps == LADDER_STEPS, "independent", "rung order",
        f"the ladder's steps read {list(steps)} and the plan fixes {list(LADDER_STEPS)}. The "
        f"order is not an implementation detail: a ladder counts each episode once at the first "
        f"rung it fails, so reordering changes every rung's removal count without changing the "
        f"analytic count, and that changes what the flow-figure boxes say.")

    slugs = tuple(str(value) for value in rows["slug"])
    checks.require(
        slugs == LADDER_SLUGS, "independent", "rung slugs",
        f"the ladder's slugs do not match the plan's, in order. Present in the ladder and not "
        f"in the plan: {[s for s in slugs if s not in LADDER_SLUGS]}. In the plan and not in "
        f"the ladder: {[s for s in LADDER_SLUGS if s not in slugs]}.")

    for rung, (_, row) in zip(ATTRITION_RUNGS, rows.iterrows()):
        step = rung["step"]
        checks.require(
            str(row["kind"]) == rung["kind"], "independent", f"kind at step {step}",
            f"step {step} is recorded as {row['kind']!r} and the plan fixes {rung['kind']!r}. "
            f"The three kinds are not decoration: an exclusion rung removes rows in a fixed "
            f"unit, a conversion changes the unit and is excluded from every within-unit sum, "
            f"and a terminal rung is a labelled endpoint.")
        checks.require(
            str(row["unit"]) == rung["unit"], "independent", f"unit at step {step}",
            f"step {step} is recorded in {row['unit']!r} and the plan fixes {rung['unit']!r}.")
        checks.require(
            str(row["kind"]) in _KINDS and str(row["unit"]) in _UNITS,
            "independent", f"vocabulary at step {step}",
            f"step {step} carries a kind or a unit outside the closed vocabularies.")

    # ---- the counts, as exact integers -------------------------------------------------
    n_in = {step: _as_int(rows.loc[i, "n_in"], where=f"the entering count at step {step}")
            for i, step in enumerate(steps)}
    n_out = {step: _as_int(rows.loc[i, "n_out"], where=f"the leaving count at step {step}")
             for i, step in enumerate(steps)}
    n_dropped = {step: _as_int(rows.loc[i, "n_dropped"], where=f"the removed count at step {step}")
                 for i, step in enumerate(steps)}
    carried = {step: _as_int(rows.loc[i, "n_carried_forward"],
                             where=f"the carried-forward count at step {step}")
               for i, step in enumerate(steps)}

    for step in LADDER_STEPS:
        checks.require(
            n_in[step] is not None and n_out[step] is not None,
            "independent", f"counts present at step {step}",
            f"step {step} carries a null entering or leaving count. Both are never null on any "
            f"rung of this ladder.")
        checks.require(
            n_in[step] >= 0 and n_out[step] >= 0, "independent", f"counts sane at step {step}",
            f"step {step} carries a negative count, which is a defect upstream and never a "
            f"disclosure decision.")

    # ---- null discipline, which is a vocabulary check and not arithmetic ---------------
    for step in LADDER_STEPS:
        should_drop = step not in NO_DROP_STEPS
        checks.require(
            (n_dropped[step] is not None) == should_drop,
            "independent", f"removal null discipline at step {step}",
            f"step {step} {'carries no' if n_dropped[step] is None else 'carries a'} removal "
            f"count and the plan says it should {'carry one' if should_drop else 'carry none'}. "
            f"Steps {list(NO_DROP_STEPS)} carry none: the two terminal rungs are endpoints and "
            f"step 17 is a conversion where every analytic episode is at risk for an event.")
        if should_drop:
            checks.require(
                n_dropped[step] >= 0, "independent", f"removal sane at step {step}",
                f"step {step} removes a negative number of rows.")
        checks.require(
            (carried[step] is not None) == (step == CARRIED_FORWARD_STEP),
            "independent", f"carried-forward null discipline at step {step}",
            f"the carried-forward count is non-null on exactly one rung, step "
            f"{CARRIED_FORWARD_STEP}, and step {step} disagrees. It is the count in PERSONS that "
            f"lets the persons identity close across the unit change.")

    # ---- the reason column, keyed off KIND and not off nullness ------------------------
    for rung, (_, row) in zip(ATTRITION_RUNGS, rows.iterrows()):
        expected = (REASON_UNIT_CHANGE if rung["kind"] == "conversion"
                    else REASON_NOT_APPLICABLE if rung["kind"] == "terminal"
                    else rung["slug"])
        actual = row["reason"]
        checks.require(
            actual is not None and not pd.isna(actual), "independent",
            f"reason present at step {rung['step']}",
            f"step {rung['step']} carries a null reason. It is never null, so no consumer can "
            f"be handed a null to key a lookup with.")
        checks.require(
            str(actual) == expected, "independent", f"reason at step {rung['step']}",
            f"step {rung['step']} carries a reason of {str(actual)!r} and its kind fixes "
            f"{expected!r}. The reason is keyed off the kind, not off whether the rung happens "
            f"to remove rows: step 2 is a conversion that also removes and step 17 is a "
            f"conversion that does not.")

    # ---- the run this ladder belongs to ------------------------------------------------
    maps = sorted({str(value) for value in rows["junction_map"]})
    checks.require(
        len(maps) == 1, "independent", "one junction map",
        f"the ladder carries {maps} across its rungs. One ladder belongs to one map: the "
        f"primary and the mirrored runs legitimately produce DIFFERENT ladders, so a mixture is "
        f"two runs stitched together and neither of them closes.")
    if junction_map is not None:
        checks.require(
            maps[0] == junction_map, "independent", "junction map matches the run",
            f"the ladder was built under the {maps[0]!r} map and this run was called with "
            f"{junction_map!r}. Reading one map's ladder while calling another is a stale "
            f"table, not a finding.")

    # ---- rule 5, the uniform chain -----------------------------------------------------
    # TRANSPORT.  In SQL the entering count is a running-sum window over the same removals the
    # leaving count is computed from, so this is that algebra again.  It still catches a table
    # assembled from two different builds, which a resume flag makes easy to produce.
    for previous, step in zip(LADDER_STEPS, LADDER_STEPS[1:]):
        checks.require(
            n_in[step] == n_out[previous], "transport", f"chain into step {step}",
            f"what enters step {step} is not what left step {previous}. It holds across both "
            f"unit changes, because a conversion re-bases the unit but not the count.")

    # ---- rule 1, every exclusion rung --------------------------------------------------
    # TRANSPORT, for the same reason: the leaving count is DEFINED as entering less removed.
    for rung in ATTRITION_RUNGS:
        if rung["kind"] != "exclusion":
            continue
        step = rung["step"]
        checks.require(
            n_in[step] - n_dropped[step] == n_out[step], "transport", f"closure at step {step}",
            f"step {step} does not close: entering less removed is not what left, in "
            f"{rung['unit']}. Do not adjust a count to make it close.")

    # ---- rule 1 for the terminal rungs, which carry no removal -------------------------
    for step in TERMINAL_STEPS:
        checks.require(
            n_in[step] == n_out[step], "transport", f"terminal rung at step {step}",
            f"step {step} is a terminal rung, so what enters it is what leaves it.")

    # ---- rule 2, the persons-to-episodes conversion -------------------------------------
    step = CARRIED_FORWARD_STEP
    checks.require(
        n_in[step] - n_dropped[step] == carried[step], "transport",
        "persons identity at the first conversion",
        f"the persons identity does not close at step {step}: persons entering less persons "
        f"removed is not persons carried forward. The removal here is persons who carry a "
        f"qualifying concept but whose records yield no dated episode.")
    checks.require(
        n_out[step] >= carried[step], "transport", "episodes at least persons carried forward",
        f"step {step} carries more persons forward than it produces episodes, and a carried "
        f"person yields at least one episode.")

    # ---- rule 3, the episode segment ----------------------------------------------------
    # TRANSPORT ON THIS SIDE OF THE BOUNDARY, and the distinction is worth stating exactly
    # because it is easy to overclaim.  INSIDE THE PERIMETER this identity has real empirical
    # content: it is the step 16 identity rearranged, and its three terms are three DIFFERENT
    # aggregations, COUNT(*) over the episode table against COUNTIF(is_eligible) and the
    # first-failing-rung histogram over the exclusions table, which an episode that is neither
    # eligible nor charged to a rung separates.  OUT HERE, reading the finished nineteen rows,
    # it is implied by the rung identities and the chain above and cannot fail on its own.
    # The independent version of this check on the Python side is `reconcile_ladder`, which
    # recounts the exclusions table in its own query rather than re-reading these integers, and
    # that is the function that would catch the failure this rule describes.
    episode_drops = sum(n_dropped[step] for step in EPISODE_DROP_STEPS)
    analytic = n_out[EPISODE_SEGMENT_TERMINAL_STEP]
    episodes_in = n_out[CARRIED_FORWARD_STEP]
    checks.require(
        episode_drops + analytic == episodes_in, "transport", "episode segment",
        f"the episode segment does not close. The removals of steps "
        f"{EPISODE_DROP_STEPS[0]} to {EPISODE_DROP_STEPS[-1]} plus the analytic count of step "
        f"{EPISODE_SEGMENT_TERMINAL_STEP} came to "
        f"{_disclosed(episode_drops + analytic)} against "
        f"{_disclosed(episodes_in)} leaving step {CARRIED_FORWARD_STEP}. An episode that is "
        f"neither eligible nor charged to a rung is what separates them. Do not adjust a count "
        f"to make it close.")

    # ---- rule 4, the event segment ------------------------------------------------------
    # TRANSPORT.  In SQL the leaving count of step 19 is written as the same expression as step
    # 17's leaving count less step 18's removal, so it cannot go false there.
    first, middle, last = EVENT_SEGMENT_STEPS
    checks.require(
        n_out[first] - n_dropped[middle] == n_out[last], "transport", "event segment",
        f"the event segment does not close: events identified at step {first} less those "
        f"removed at step {middle} is not what leaves step {last}. Steps {first} and {last} "
        f"count events, carry no removal, and are excluded from the episode segment; a consumer "
        f"that adds step {middle}'s removal into the episode sum is adding events to episodes.")

    # ---- the closure column, asserted and immediately qualified -------------------------
    # TRANSPORT, and the report says so.  A false value here means a ladder built by a version
    # of the procedure that did not raise on its own stop condition, which is worth catching.
    # It is NOT nineteen independent checks and nothing downstream may read it as such.
    closes = [row["closes_exact"] for _, row in rows.iterrows()]
    checks.require(
        all(value is True or value is bool(value) and value for value in closes),
        "transport", "closure column",
        "the ladder carries a rung whose closure flag is not true. The procedure raises on this "
        "inside the perimeter, so a false value here is a table built by something that did not.")

    return MappingProxyType({
        "checks": checks,
        "n_rungs": len(rows),
        "junction map": maps[0],
        "n_in": MappingProxyType(dict(n_in)),
        "n_out": MappingProxyType(dict(n_out)),
        "n_dropped": MappingProxyType(dict(n_dropped)),
        "n_carried_forward": MappingProxyType(dict(carried)),
        "episode drops": episode_drops,
        "analytic": analytic,
        "episodes": episodes_in,
        "events identified": n_out[first],
        "events analyzable": n_out[last],
        "program participants": n_in[1],
    })


def reconcile_ladder(
    ladder: Mapping[str, Any],
    totals: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Recount the exclusions table a second way and hold the ladder to it.

    EVERY CHECK HERE IS INDEPENDENT.  The counts come from a query this module wrote, against a
    table the ladder read separately, so nothing below compares an expression against itself.
    These are the assertions that would catch the failure the ladder's own closure column cannot
    describe: an episode that is neither eligible nor charged to a rung.
    """
    checks = _Checks()

    def total(name: str) -> int:
        value = _as_int(totals[name], where=f"the reconciliation count {name!r}")
        if value is None:
            raise LadderClosureError(f"the reconciliation returned no value for {name!r}")
        return value

    n_episodes = total("n_episodes")
    n_rows = total("n_exclusion_rows")
    n_eligible = total("n_eligible")
    n_charged = total("n_charged")

    checks.require(
        total("n_eligible_and_charged") == 0, "independent", "no episode both kept and charged",
        "an episode is marked eligible and is also charged to a failing rung. The first "
        "failing rung is null exactly when the episode is eligible, and the two together are "
        "what make the ladder close.")
    checks.require(
        total("n_neither") == 0, "independent", "no episode neither kept nor charged",
        "an episode is neither eligible nor charged to a rung. This is the one failure the "
        "ladder's own closure column exists to catch and the one identity the procedure tests "
        "independently, and it is the reason this reconciliation is here.")
    checks.require(
        total("n_charged_off_ladder") == 0, "independent", "every charge lands on a rung",
        f"an episode is charged to a rung outside steps {EPISODE_DROP_STEPS[0]} to "
        f"{EPISODE_DROP_STEPS[-1]}, which are the only rungs the exclusions table can charge.")
    checks.require(
        n_rows == n_episodes, "independent", "the exclusions table is one row per episode",
        f"the exclusions table holds {_disclosed(n_rows)} row(s) against "
        f"{_disclosed(n_episodes)} episode(s). IT IS NOT THE FILTERED SURVIVOR SET: it carries "
        f"one row per episode with every predicate and the first rung each episode fails, and "
        f"reading it as the survivors is the single most common misreading of that table.")
    checks.require(
        n_episodes == ladder["episodes"], "independent", "episodes match the ladder",
        f"the episode table holds {_disclosed(n_episodes)} row(s) and the ladder says "
        f"{_disclosed(ladder['episodes'])} left the first conversion.")
    checks.require(
        n_eligible == ladder["analytic"], "independent", "analytic count matches the ladder",
        f"the exclusions table marks {_disclosed(n_eligible)} episode(s) eligible and the "
        f"ladder's analytic rung says {_disclosed(ladder['analytic'])}.")
    checks.require(
        n_charged == ladder["episode drops"], "independent", "removals match the ladder",
        f"the exclusions table charges {_disclosed(n_charged)} episode(s) to a rung and the "
        f"ladder's removals over the episode unit sum to "
        f"{_disclosed(ladder['episode drops'])}.")
    checks.require(
        n_eligible + n_charged == n_rows, "independent", "eligibility partitions the table",
        "the eligible and the charged episodes do not partition the exclusions table.")

    return MappingProxyType({"checks": checks, "totals": MappingProxyType(dict(totals))})


# ======================================================================================
# (8) The collapse level, which is prespecified and is decided HERE.
#
# ANALYSIS-PLAN.md 2.5: "The level is decided ONCE, on the Phase 3 attrition ladder, before any
# model is fit, on the exact within-perimeter counts; only the rounded counts are ever printed."
# It is a predicate over four counts and not a judgment, which is the whole point of writing it
# down before the counts exist: it removes the class of decision where an analyst fits a
# four-group model, sees an unstable cell, and collapses afterwards.
#
# "Disclosable" has exactly one definition in this project and it is `disclosure.disclosable`.
# No threshold is written as a literal anywhere below.
# ======================================================================================

GROUP_COUNT_SQL = """
SELECT procedure_group AS group_slug, COUNT(*) AS n_episodes
FROM `{DERIVED}.features`
GROUP BY group_slug
ORDER BY group_slug
"""


def collapse_level(group_counts: Mapping[str, int], *, analytic: int) -> Mapping[str, Any]:
    """The prespecified collapse level for these counts.  Pure, and it sees no model.

    The disclosure floor doubles as the analysis floor: a cell that cannot be printed is a cell
    that will not be modelled.
    """
    four = {slug: int(group_counts.get(slug, 0)) for slug in FOUR_GROUP_SLUGS}
    fusion = four["cervical_fusion"] + four["lumbar_fusion"]
    decompression = four["cervical_decompression"] + four["lumbar_decompression"]

    if not disclosable(analytic):
        level, why = "no_estimand", ("the analytic cohort itself is below the disclosure floor, "
                                     "so no estimand is reported and the ladder is the result")
    elif not (disclosable(fusion) and disclosable(decompression)):
        level, why = "single_group", ("either the fusion or the decompression arm is below the "
                                      "floor, so one pooled curve is reported and no "
                                      "between-group contrast is estimable")
    elif all(disclosable(value) for value in four.values()):
        level, why = "four_group", ("all four region and fusion cells clear the floor, so the "
                                    "full model with the interaction is fit")
    else:
        level, why = "two_group", ("at least one of the four region and fusion cells is below "
                                   "the floor while both arms clear it, so fusion versus "
                                   "decompression is estimated region-adjusted, with no "
                                   "interaction")

    return MappingProxyType({
        "level": level,
        "why": why,
        "groups": tuple(slug for slug in FOUR_GROUP_SLUGS) if level == "four_group"
                  else ("fusion", "decompression") if level == "two_group"
                  else ("all_groups",) if level == "single_group" else (),
        "four group counts": MappingProxyType(four),
        "fusion": fusion,
        "decompression": decompression,
        "analytic": int(analytic),
    })


# ======================================================================================
# (9) Reading the derived tables back out.
#
# NOTHING HERE PRINTS A ROW.  Every frame that comes back is participant-derived, and the only
# thing a frame is ever shown by is `safe_show`, which prints a shape and a column list and
# hides the rows.  Counts stay TRUE INTEGERS all the way to the render, where they are rounded
# once, at the boundary.
# ======================================================================================

def _resolve_runtime(
    q_guarded: Callable[..., pd.DataFrame] | None,
    dry_run_gb: Callable[[str], float] | None,
) -> tuple[Callable[..., pd.DataFrame], Callable[[str], float]]:
    """Find the two configuration-notebook helpers, in the order a caller would expect.

    Explicit argument first, which is how the self-test injects a fake; then this module's own
    globals, which is what a notebook run in place populates; then the live kernel namespace.
    Nothing falls back to a raw BigQuery client: `q_guarded` is the only query path, and a
    module that could quietly find its own way to the interface is a module that eventually runs
    a query with no printed estimate and no cap.
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
            raise CohortError(
                f"{name} is not available. This step runs inside the perimeter and gets its "
                f"only query path from the configuration notebook. Run that notebook first, "
                f"then load this file into the same kernel."
            )
        resolved.append(found)
    return resolved[0], resolved[1]


def _ipython_user_namespace() -> dict[str, Any]:
    """The live kernel's namespace, or an empty one outside a kernel."""
    try:
        from IPython import get_ipython           # type: ignore[import-not-found]
        shell = get_ipython()
    except Exception:
        return {}
    return dict(getattr(shell, "user_ns", {})) if shell is not None else {}


def read_ladder(*, q_guarded: Callable[..., pd.DataFrame],
                max_gb: float = LADDER_MAX_GB) -> pd.DataFrame:
    """The nineteen rungs, as true integers.  Nineteen rows and twelve columns; nothing printed."""
    return q_guarded(LADDER_SQL, max_gb=max_gb, note="attrition ladder, 19 rungs")


def read_reconciliation(*, q_guarded: Callable[..., pd.DataFrame],
                        max_gb: float = RECONCILIATION_MAX_GB) -> Mapping[str, Any]:
    """The independent recount of the exclusions table.  One row of seven aggregates."""
    frame = q_guarded(RECONCILIATION_SQL, max_gb=max_gb,
                      note="ladder reconciliation against the exclusions table")
    if len(frame) != 1:
        raise LadderClosureError(
            "the reconciliation query returned something other than one row of aggregates.")
    return MappingProxyType({column: frame.iloc[0][column] for column in frame.columns})


def read_ledgers(*, q_guarded: Callable[..., pd.DataFrame],
                 max_gb: float = LEDGER_MAX_GB) -> Mapping[str, pd.DataFrame]:
    """The four SQL-side ledgers, at the columns the contract exports and no others.

    The projection is done in the SELECT rather than after the fact, so the two columns the
    contract refuses never enter this process at all.  That is not theatre: a column read into
    memory is a column somebody adds to a render later "since it is already here", and the
    refusal of the analyzable-day count is load bearing, because it is a recoverable member of
    a partition this file already discloses.
    """
    out: dict[str, pd.DataFrame] = {}
    for table, columns in LEDGER_SOURCE_COLUMNS.items():
        sql = (f"SELECT {', '.join(columns)}\nFROM `{{DERIVED}}.{table}`\n"
               f"ORDER BY {', '.join(LEDGER_SORT_KEYS[table])}")
        out[table] = q_guarded(sql, max_gb=max_gb, note=f"ledger {table}")
    return MappingProxyType(out)


def read_group_counts(*, q_guarded: Callable[..., pd.DataFrame],
                      max_gb: float = GROUP_COUNT_MAX_GB) -> Mapping[str, int]:
    """The four procedure-group counts the collapse level is decided on.  True integers."""
    frame = q_guarded(GROUP_COUNT_SQL, max_gb=max_gb, note="procedure group counts")
    counts: dict[str, int] = {}
    for _, row in frame.iterrows():
        slug = row["group_slug"]
        if slug is None or (isinstance(slug, float) and pd.isna(slug)):
            # The feature table's group is never null, because rungs 6, 7 and 8 removed every
            # episode it could be null for.  A null here is those rungs not having run.
            raise CohortError(
                "an analytic episode carries no procedure group. It is null only for the "
                "simultaneous, thoracic-only and unspecified-region episodes that rungs 6, 7 "
                "and 8 remove, so a null here means those rungs did not run.")
        counts[str(slug)] = int(_as_int(row["n_episodes"], where="a procedure group count") or 0)
    return MappingProxyType(counts)


# ======================================================================================
# (10) Rendering.  Every printed count is rounded here and nowhere earlier.
# ======================================================================================

_SNAKE_TOKEN = re.compile(r"\b[a-z0-9]+_[a-z0-9_]*\b")
_RULE = "=" * 86
_THIN = "-" * 86


def assert_house_prose(text: str, *, allow: Sequence[str] = ()) -> None:
    """Stop conditions on a rendered string, checked before a character of it is printed.

    `allow` names MACHINE TOKENS a particular surface is permitted to print verbatim, and it
    exists for exactly one surface: the stage cost table, whose rows are the nineteen table
    names a human types back at the resume flag.  Rendering "Heart rate daily" there would make
    the flag unusable, and the alternative of exempting the whole table from the check is how
    an exemption widens.  The list is explicit, per token, and is asserted to be a subset of the
    stage names, so nothing else can be smuggled through it.

    The exhibit-facing surfaces, the ladder and the four ledgers, pass an empty list and print
    display labels for everything.
    """
    for token in allow:
        if token not in STAGE_ORDER:
            raise CohortError(
                f"the house-prose guard was asked to allow {token!r}, which is not one of the "
                f"stage names. The exemption covers the resume vocabulary and nothing else."
            )
    if EM_DASH in text:
        raise CohortError("a rendered string contains an em-dash, which no house string carries")
    if MINUS_SIGN in text:
        raise CohortError("a rendered string contains a Unicode minus sign, which is banned")
    scanned = text
    for token in allow:
        scanned = scanned.replace(token, " ")
    snake = sorted(set(_SNAKE_TOKEN.findall(scanned)))
    if snake:
        raise CohortError(
            f"a rendered string contains identifier token(s) {snake}, and an identifier is "
            f"never a user-visible string. Use the display label beside it."
        )


def _table_lines(headers: Sequence[str], rows: Sequence[Sequence[Any]],
                 align: str = "") -> list[str]:
    """A fixed-width table.  `align` is one character per column, 'l' or 'r'."""
    align = align or ("l" + "r" * (len(headers) - 1))
    widths = [len(str(head)) for head in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(str(cell)))

    def line(cells: Sequence[Any]) -> str:
        return "  ".join(
            str(cell).ljust(widths[index]) if align[index] == "l" else str(cell).rjust(widths[index])
            for index, cell in enumerate(cells)).rstrip()

    return [line(headers), "  ".join("-" * width for width in widths)] + [line(r) for r in rows]


def _wrap(text: str, width: int) -> list[str]:
    """Greedy wrap.  A line that runs past the terminal is a line nobody reads."""
    words, out, current = text.split(), [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width and current:
            out.append(current)
            current = word
        else:
            current = candidate
    if current:
        out.append(current)
    return out or [""]


def render_cost_plan(plan: Mapping[str, Any]) -> str:
    """The per-stage cost table, the total, and the cap that will actually be enforced.

    THIS IS THE ONE SURFACE THAT PRINTS MACHINE NAMES, because its rows are the vocabulary of
    the resume flag.  It is rendered under an explicit, per-token exemption rather than outside
    the house-prose guard.
    """
    lines: list[str] = [_RULE, "PHASE 3 COST PLAN: EVERY STAGE PRICED BEFORE ANY OF IT RUNS", _RULE, ""]
    lines += _wrap(
        "A dry run is free and prices the columns referenced rather than the table, so the "
        "whole of the table below cost nothing. Read it before approving the call.", 86)
    lines.append("")
    rows = [(f"{row['index']:>2d}", row["name"],
             "yes" if row["is_template"] else "",
             f"{row['gb']:,.3f}", f"${row['usd']:,.4f}", f"{row['cap_gb']:,.3f}")
            for row in plan["stages"]]
    lines += _table_lines(
        ("#", "Stage", "Template", "Estimate, GB", "Estimate", "Cap, GB"),
        rows, align="rlrrrr")
    lines.append("")
    lines.append(f"  Stages priced           : {len(plan['stages'])} of {N_STAGES}"
                 + (f", resuming from {plan['start stage']}" if plan["start stage"] else ""))
    lines.append(f"  Total, the approval figure: {plan['total gb']:,.3f} GB, about "
                 f"${plan['total usd']:,.2f}")
    lines.append(f"  Approval ceiling        : {plan['budget gb']:,.1f} GB, about "
                 f"${gb_to_usd(plan['budget gb']):,.2f}")
    lines.append(f"  Binding stage           : {plan['binding stage']} at "
                 f"{plan['binding gb']:,.3f} GB")
    lines.append(f"  Cap sent with the call  : {plan['call cap gb']:,.3f} GB, PER CHILD JOB")
    lines.append(f"  Worst case that cap allows: {plan['worst case gb']:,.3f} GB, about "
                 f"${gb_to_usd(plan['worst case gb']):,.2f}")
    naive = plan["total gb"] * len(plan["stages"])
    lines.append(f"  Worst case a total-sized cap would allow: {naive:,.3f} GB, about "
                 f"${gb_to_usd(naive):,.2f}")
    lines.append("")
    lines += _wrap(
        "The cap is sized on the binding stage and never on the total. A BigQuery script "
        "applies it to each child job individually, so a cap set at the total would permit "
        "every one of these stages to bill the total, which is up to "
        f"{len(plan['stages'])} times the approval figure above. The total is what a human "
        "approves; it is not a thing BigQuery enforces, and the worst case beside it is what "
        "the cap actually bounds.", 86)
    lines.append("")
    return "\n".join(lines)


def _suppressed_or(count: Any, sentence_slug: str = "cell_below_threshold") -> str:
    """A true count rendered, or the contract's suppression sentence, verbatim."""
    if not disclosable(count):
        return SUPPRESSION_SENTENCES[sentence_slug]
    return _disclosed(count)


def _complement_guarded(part: int, whole: int) -> str:
    """A part of a disclosed whole, suppressed when EITHER it or its complement is too small.

    A part and its total are a two-member partition whose other member is never written and is
    therefore recoverable by subtraction.  On a nearly complete variable the recovered number is
    large and harmless; on a nearly empty one it is small, and it is exactly the cell the floor
    exists to protect.  So both sides are tested and the sentence says which rule fired.
    """
    if not disclosable(whole):
        return SUPPRESSION_SENTENCES["cell_below_threshold"]
    if not disclosable(part):
        return SUPPRESSION_SENTENCES["cell_below_threshold"]
    if not disclosable(whole - part):
        return SUPPRESSION_SENTENCES["secondary_suppression"]
    return n_pct(part, whole)


def _apply_secondary_suppression(counts: Sequence[int]) -> tuple[bool, ...]:
    """Which members of a declared partition must be hidden, given their true counts.

    A partition of a disclosed total with EXACTLY ONE hidden member hands the reader that
    member by subtraction, so a second is hidden beside it.  The second one chosen is the
    smallest disclosable member, because hiding the smallest costs the reader the least
    information while closing the same hole.  With no hidden member nothing happens; with two
    or more, nothing further is needed.
    """
    hidden = [not disclosable(value) for value in counts]
    if sum(hidden) != 1:
        return tuple(hidden)
    candidates = [(value, index) for index, value in enumerate(counts) if not hidden[index]]
    if not candidates:
        return tuple(hidden)
    hidden[min(candidates)[1]] = True
    return tuple(hidden)


ROUNDING_FOOTNOTE = (
    "Counts are rounded to the nearest 20 in accordance with the All of Us dissemination "
    "policy, so the boxes may not sum exactly. The unrounded ladder was asserted to close "
    "before rounding.")

DISCLOSURE_SENTENCE = (
    "Counts of 20 or fewer are suppressed; larger counts are rounded to the nearest 20, so a "
    "disclosed 20 represents a true count of 21 to 29.")


def render_ladder(frame: pd.DataFrame, ladder: Mapping[str, Any]) -> str:
    """The nineteen rungs, as a printed table, with every count rounded at this boundary.

    The ladder box names the SURVIVORS below the rung, which is why steps 15 and 16 share a
    label and steps 18 and 19 share one. That is not a transcription slip and it is not
    de-duplicated here.
    """
    rows: list[tuple[Any, ...]] = []
    for rung, (_, row) in zip(ATTRITION_RUNGS, frame.sort_values("step").iterrows()):
        slug = rung["slug"]
        dropped = _as_int(row["n_dropped"], where=f"the removed count at step {rung['step']}")
        carried = _as_int(row["n_carried_forward"],
                          where=f"the carried-forward count at step {rung['step']}")
        rows.append((
            rung["step"],
            rung_label(slug),
            rung["unit"].replace(" to ", " into "),
            _suppressed_or(_as_int(row["n_in"], where="an entering count")),
            "" if dropped is None else _suppressed_or(dropped),
            _suppressed_or(_as_int(row["n_out"], where="a leaving count")),
            "" if carried is None else _suppressed_or(carried),
        ))

    lines: list[str] = [_RULE, "PHASE 3 ATTRITION LADDER", _RULE, ""]
    lines += _table_lines(
        ("Step", "Ladder box", "Unit", "Entering", "Removed", "Leaving", "Carried"),
        rows, align="rllrrrr")
    lines.append("")
    lines.append("Denominator for this table: "
                 f"{_suppressed_or(ladder['program participants'])} participants in the "
                 f"Controlled Tier release; the analytic cohort is "
                 f"{_suppressed_or(ladder['analytic'])} episodes.")
    lines.append("")
    lines += _wrap(ROUNDING_FOOTNOTE, 86)
    lines.append("")

    reasons = [(rung["step"], rung_reason_display(rung["slug"]))
               for rung in ATTRITION_RUNGS if rung_reason_display(rung["slug"])]
    lines.append("Why each rung removed what it removed, in the sentence the exclusion box prints:")
    lines.append("")
    for step, sentence in reasons:
        wrapped = _wrap(sentence, 78)
        lines.append(f"  {step:>2d}. {wrapped[0]}")
        lines += [f"      {chunk}" for chunk in wrapped[1:]]
    lines.append("")
    return "\n".join(lines)


def render_closure(ladder: Mapping[str, Any],
                   reconciliation: Mapping[str, Any] | None) -> str:
    """What was asserted, which of it can fail, and what the closure column does not prove."""
    ladder_checks: _Checks = ladder["checks"]
    lines: list[str] = [_THIN, "CLOSURE", _THIN, ""]
    lines += _wrap(
        "The ladder crosses two unit changes, so there is no single global identity and "
        "treating it as one fails on the first real run. Four rules were asserted, plus a "
        "uniform fifth, and all of them held or this text would not have been reached.", 86)
    lines.append("")
    lines += _bullets([
        "Every exclusion rung: entering less removed equals leaving, both sides in one unit.",
        "The persons into episodes conversion cannot assert that, so it carries a third count "
        "in persons and asserts entering less removed equals carried forward, together with "
        "leaving at least carried forward.",
        "Within the episode unit, the removals of steps 3 to 15 plus the analytic count equal "
        "what left the first conversion.",
        "Steps 17 and 19 count events, carry no removal, are excluded from that sum, and close "
        "among themselves.",
        "Uniform over all nineteen: what enters a rung is what left the one before it.",
    ])
    lines.append("")
    lines += _wrap(
        "WHAT THE CLOSURE COLUMN DOES NOT PROVE. Inside the perimeter that column is true by "
        "construction on eighteen of the nineteen rungs, because the leaving count is computed "
        "AS entering less removed and an expression compared against itself cannot fail. "
        "Exactly one identity is independently tested there, at the analytic rung, which "
        "reconciles the eligible count against the first-failing-rung histogram. Nothing here "
        "reads that column as nineteen checks.", 86)
    lines.append("")
    lines.append(f"  Checks that can fail on a correct build : {ladder_checks.independent}")
    lines.append(f"  Checks of transport only                : {ladder_checks.transport}")
    if reconciliation is not None:
        recon_checks: _Checks = reconciliation["checks"]
        lines.append(f"  Independent recount of the exclusions   : "
                     f"{recon_checks.independent} check(s), all independent")
        lines.append("")
        lines += _wrap(
            "The recount is the strongest check in this module. It counts the exclusions table "
            "a second way, in its own query, and holds the ladder to it: that eligibility and "
            "the first failing rung partition the table with no episode in both and none in "
            "neither, that every charge lands on a rung that exists, that the table is one row "
            "per episode rather than the filtered survivor set, and that the three counts the "
            "analytic identity rests on agree. An episode that is neither eligible nor charged "
            "is exactly the failure that can happen here, and this is what catches it.", 86)
    else:
        lines.append("")
        lines += _wrap(
            "The independent recount did not run, so the only checks that can fail on a correct "
            "build are the structural ones and the episode segment. Run it before treating the "
            "ladder as reviewed.", 86)
    lines.append("")
    return "\n".join(lines)


def _bullets(items: Sequence[str], width: int = 86) -> list[str]:
    """Wrapped bullet points."""
    out: list[str] = []
    for item in items:
        chunks = _wrap(item, width - 4)
        out.append("  * " + chunks[0])
        out += ["    " + chunk for chunk in chunks[1:]]
    return out


def render_exclusion_ledger(frame: pd.DataFrame) -> str:
    """STROBE companion ledger 3, at the contract's seven exported columns.

    THE ROWS HERE ARE NOT A PARTITION and that is the whole reason this ledger exists rather
    than more rungs: an episode excluded for a nonelective indication may carry trauma AND
    malignancy and is counted under both.  Three sets of rows ARE partitions of a disclosed
    total, and only those three carry the secondary-suppression rule, because declaring a
    partition that does not hold would be a false claim enforced downstream.

    The denominator is NOT always the rung's removal count, and the rung where it is not is the
    one a reader is most likely to get wrong: for the elective-proxy rescue routes the
    population at risk of being rescued is the set of episodes with an emergency encounter, not
    the set the rung dropped.  It is printed beside every share for that reason.
    """
    rows: list[tuple[Any, ...]] = []
    for step in sorted({int(value) for value in frame["step"]}):
        block = frame[frame["step"] == step].sort_values("reason_detail")
        details = [str(value) for value in block["reason_detail"]]
        episodes = [int(_as_int(value, where="a ledger episode count") or 0)
                    for value in block["n_episodes"]]
        denominators = [int(_as_int(value, where="a ledger denominator") or 0)
                        for value in block["n_denominator"]]

        declared = LEDGER_EXCLUSION_PARTITIONS.get(step)
        if declared is not None:
            if sorted(details) != sorted(declared):
                raise CohortError(
                    f"step {step} is declared a partition of {len(declared)} members and the "
                    f"ledger carries {len(details)}. A declared partition that does not hold is "
                    f"a false claim, and the suppression rule would then enforce it.")
            hidden = _apply_secondary_suppression(episodes)
        else:
            hidden = tuple(not disclosable(value) for value in episodes)

        for detail, count, denominator, is_hidden in zip(details, episodes, denominators, hidden):
            try:
                sentence = REASON_DETAIL_LABELS[(step, detail)]
            except KeyError:
                raise CohortError(
                    f"the ledger carries a reason detail at step {step} with no printable "
                    f"sentence. An identifier is never a user-visible string, so a new detail "
                    f"needs a sentence here before it can be printed or exported."
                ) from None
            # n_pct divides the ROUNDED count by the ROUNDED denominator and prints to zero
            # decimals, so a reader reproduces the share from the two numbers printed beside
            # it and from nothing else. The count and its share travel in one cell for that
            # reason; splitting them invites a reader to divide the wrong pair.
            if is_hidden:
                cell = (SUPPRESSION_SENTENCES["secondary_suppression"]
                        if disclosable(count)
                        else SUPPRESSION_SENTENCES["cell_below_threshold"])
            else:
                cell = n_pct(count, denominator)
            rows.append((step, rung_label(str(block.iloc[0]["slug"])), sentence, cell,
                         _suppressed_or(denominator)))

    lines = [_THIN, "STROBE LEDGER: EXCLUSION AND CENSORING REASONS", _THIN, ""]
    lines += _table_lines(("Step", "Ladder box", "Reason", "Episodes (share)", "Denominator"),
                          rows, align="rlllr")
    lines.append("")
    lines += _wrap(
        "These rows overlap and are not a partition of anything, except at the three rungs "
        "where the members are mutually exclusive and exhaustive, where one hidden member "
        "forces a second beside it so the first cannot be recovered by subtraction. Each share "
        "is over the denominator printed beside it, which is the rung's own removal count on "
        "most rows and the population at risk of rescue on the elective-proxy rows.", 86)
    lines.append("")
    return "\n".join(lines)


def render_wear_ledger(frame: pd.DataFrame) -> str:
    """STROBE companion ledger 4, at the contract's SEVEN exported columns and no more.

    THE PRODUCER EMITS TWO MORE COUNT COLUMNS AND THIS DOES NOT TAKE THEM.  The analyzable-day
    count would make an unwritten complement recoverable by subtraction, since a valid-wear day
    needs only the minutes while an analyzable day needs the minutes and a step count, so the
    difference between two disclosed numbers would be a member nobody floor-tested.  The
    inpatient-day count is small on most days by its nature and would be a suppression sentence
    on most of its rows.  Neither is widened here.

    THE ABSENCE RULE.  A day whose at-risk count fails the floor is DROPPED FROM THIS TABLE
    rather than written as a hidden row, because a list of which days were hidden recovers the
    pattern it was hiding, and because a row with no value is not a point on a curve.  The days
    that remain are disclosed, which is the published output of the rule and not a leak around
    it.  The producer carries every day; this is where the rule is applied.
    """
    kept: list[tuple[Any, ...]] = []
    dropped_days = 0
    for _, row in frame.sort_values(["group_order", "day"]).iterrows():
        at_risk = int(_as_int(row["n_at_risk"], where="an at-risk day count") or 0)
        valid = int(_as_int(row["n_valid_wear"], where="a valid-wear day count") or 0)
        if not disclosable(at_risk):
            dropped_days += 1
            continue
        slug = str(row["group_slug"])
        if slug not in GROUP_LABELS:
            raise CohortError(
                f"the wear ledger carries a group with no printable label. The seven group "
                f"slugs are fixed and no consumer may hardcode four of them.")
        kept.append((GROUP_LABELS[slug], int(row["group_order"]), int(row["day"]),
                     _disclosed(at_risk), _complement_guarded(valid, at_risk)))

    # Only the endpoints of each group's series are printed. The full grid is up to 630 rows and
    # nobody reads 630 rows at a stop; what a reviewer needs here is where each series starts,
    # where it stops, and how far the adherence fell between.
    summary: list[tuple[Any, ...]] = []
    for order in sorted({row[1] for row in kept}):
        series = [row for row in kept if row[1] == order]
        first, last = series[0], series[-1]
        summary.append((first[0], f"{first[2]} to {last[2]}", len(series),
                        first[3], first[4], last[3], last[4]))

    lines = [_THIN, "STROBE LEDGER: WEAR AVAILABILITY BY GROUP AND POST-DISCHARGE DAY", _THIN, ""]
    if summary:
        lines += _table_lines(
            ("Group", "Days retained", "Rows", "At risk, first", "Valid wear, first",
             "At risk, last", "Valid wear, last"),
            summary, align="llrrlrl")
    else:
        lines.append("  No group and day cell clears the disclosure floor, so this ledger is "
                     "empty.")
    lines.append("")
    lines.append(f"  Days carried by the producer and dropped here by the absence rule: "
                 f"{dropped_days}")
    lines.append(f"  Columns the producer emits and the contract refuses: "
                 f"{len(LEDGER_WITHHELD_COLUMNS['ledger_wear_by_day'])}, being the analyzable "
                 f"and the inpatient day counts")
    lines.append("")
    lines += _wrap(
        "A day below the floor is absent from this table rather than hidden in it, because a "
        "list of which days were hidden recovers the pattern it was hiding. The two refused "
        "columns stay inside the perimeter: the analyzable count is a recoverable member of a "
        "total this table already discloses, and it is already published where it is read, as "
        "the contributing count on the daily activity series.", 86)
    lines.append("")
    return "\n".join(lines)


def render_matched_set_ledger(frame: pd.DataFrame) -> str:
    """STROBE companion ledger 5.  Written on every run, including the run that has no sets.

    A file that is present and empty and a file that is absent are different claims and only one
    of them is checkable, which is why the producer creates the table either way.  The set-size
    rows partition a disclosed total, so the secondary-suppression rule applies across them.
    """
    lines = [_THIN, "STROBE LEDGER: CONTROLS PER MATCHED SET", _THIN, ""]
    if len(frame) == 0:
        lines.append("  No matched sets were produced, so no early-warning analysis is "
                     "available at the feasibility tier this cohort reached.")
        lines.append("")
        return "\n".join(lines)

    sizes = [int(_as_int(value, where="a matched set size") or 0) for value in frame["set_size"]]
    sets = [int(_as_int(value, where="a matched set count") or 0) for value in frame["n_sets"]]
    cases = [int(_as_int(value, where="a matched case count") or 0) for value in frame["n_cases"]]
    total_sets = sum(sets)
    hidden = _apply_secondary_suppression(sets)

    rows = [(size,
             (SUPPRESSION_SENTENCES["secondary_suppression"] if is_hidden and disclosable(count)
              else SUPPRESSION_SENTENCES["cell_below_threshold"] if is_hidden
              else _disclosed(count)),
             (SUPPRESSION_SENTENCES["numerator_suppressed"] if is_hidden
              else _suppressed_or(case_count)))
            for size, count, case_count, is_hidden in zip(sizes, sets, cases, hidden)]

    lines += _table_lines(("Controls in the set", "Sets", "Cases"), rows, align="lll")
    lines.append("")
    lines.append(f"  Denominator for this table: {_suppressed_or(total_sets)} matched sets, one "
                 f"case each.")
    lines.append("")
    lines += _wrap(
        "Some sets end with fewer than five controls and that is expected: the per-set cap is "
        "applied first and the per-participant cap second, and the second one bites on "
        "participants who are eligible controls at many landmarks. This table is where the two "
        "caps become visible.", 86)
    lines.append("")
    return "\n".join(lines)


def render_missingness_ledger(frame: pd.DataFrame) -> str:
    """The COUNT HALF of STROBE companion ledger 2.  The other eight columns are specification.

    Every other column of that ledger, the display label, the role, the source table, the source
    concept set, the derivation, the unit and the missing-value handling, is a fact about the
    specification rather than about the data, and it is owned by the exporter.  Only the missing
    count is a fact about the data, and that is all this prints.

    The total is on the file because the denominator is NOT the same on every row: ten of the
    twelve variables are measured over the analytic episodes, one over the person-days inside
    the accrual window and one over the first events, and those populations differ by orders of
    magnitude.  Reading a single denominator across all twelve misreads two of them by a factor
    of tens.
    """
    rows: list[tuple[Any, ...]] = []
    unexpected_zero: list[str] = []
    for _, row in frame.iterrows():
        variable = str(row["variable"])
        if variable not in VARIABLE_LABELS:
            raise CohortError(
                f"the missingness ledger carries a variable with no printable label. An "
                f"identifier is never a user-visible string.")
        total = int(_as_int(row["n_total"], where="a variable total") or 0)
        missing = int(_as_int(row["n_missing"], where="a variable missing count") or 0)
        rows.append((VARIABLE_LABELS[variable], _suppressed_or(total),
                     _complement_guarded(missing, total)))
        if missing == 0 and variable not in STRUCTURALLY_COMPLETE_VARIABLES:
            unexpected_zero.append(VARIABLE_LABELS[variable])

    lines = [_THIN, "STROBE LEDGER: VARIABLE MISSINGNESS, THE COUNT HALF", _THIN, ""]
    lines += _table_lines(("Variable", "Rows in its own population", "Missing"),
                          rows, align="lrl")
    lines.append("")
    lines += _wrap(
        "Each row prints the denominator of its own population, because the twelve are not "
        "measured over the same rows: ten are per episode, one is per person-day inside the "
        "accrual window and one is per first event. A missing cell counts the evidence of "
        "absence and never the substituted value, so the two variables that substitute count "
        "their substitution flag instead of their column.", 86)
    lines.append("")
    lines.append("  Expected to be structurally complete, and only these three: "
                 + ", ".join(VARIABLE_LABELS[name] for name in STRUCTURALLY_COMPLETE_VARIABLES))
    if unexpected_zero:
        lines.append("  Complete and not expected to be, which is worth a look before the "
                     "models run: " + ", ".join(unexpected_zero))
    lines.append("")
    return "\n".join(lines)


def render_hard_stop(ladder: Mapping[str, Any],
                     collapse: Mapping[str, Any] | None) -> str:
    """The second hard stop, and the decision the human has to make at it.

    The protocol's own rule is that no modelling begins until the attrition table is reviewed.
    That is not a courtesy pause: the collapse level is decided here, on these counts, before any
    model is fit, which is what removes the class of decision where an analyst fits a four-group
    model, sees an unstable cell, and collapses afterwards.
    """
    lines = [_RULE, "PHASE 3 HARD STOP: NOTHING RUNS UNTIL THIS TABLE IS REVIEWED", _RULE, ""]
    lines += _wrap(
        "The derived tables exist. No model has been fit, no estimate computed, no bundle "
        "written. The ladder above closed on the true integers before any of it was rounded, "
        "and the counts printed are the rounded ones, which is the only form any of them may "
        "ever take on a page.", 86)
    lines.append("")
    lines.append("What the reviewer is being asked to decide:")
    lines.append("")
    lines += _bullets([
        "Whether the ladder is accepted as it stands. If a rung removed more than it should "
        "have, that is a definition to fix in the exclusions stage and rebuild from there, "
        "never a count to adjust.",
        "Whether the elective proxy behaved. It reads admission wording that this release is "
        "not confirmed to populate, and if it does not, that rung over-excludes silently and "
        "the reason ledger's rescue rows are the place it shows.",
        "Whether the analytic cohort supports the estimand at the level the collapse ladder "
        "selects, below.",
        "Whether the wearable rung removed what was expected. It is the largest single "
        "reduction in this ladder by construction, because most participants with a spine "
        "operation contributed no device data at all.",
    ])
    lines.append("")

    if collapse is not None:
        lines.append(_THIN)
        lines.append("THE COLLAPSE LEVEL, PRESPECIFIED AND DECIDED ON THESE COUNTS")
        lines.append(_THIN)
        lines.append("")
        rows = [(GROUP_LABELS[slug], _suppressed_or(count))
                for slug, count in collapse["four group counts"].items()]
        rows.append((GROUP_LABELS["fusion"], _suppressed_or(collapse["fusion"])))
        rows.append((GROUP_LABELS["decompression"], _suppressed_or(collapse["decompression"])))
        rows.append((GROUP_LABELS["all_groups"], _suppressed_or(collapse["analytic"])))
        lines += _table_lines(("Group", "Episodes"), rows, align="lr")
        lines.append("")
        selected = {"four_group": "Four groups", "two_group": "Two groups",
                    "single_group": "One group", "no_estimand": "No estimand"}[collapse["level"]]
        lines.append(f"  Selected: {selected}")
        lines += [f"  {chunk}" for chunk in _wrap("Because " + collapse["why"], 84)]
        lines.append("")
        lines += _wrap(
            "The disclosure floor doubles as the analysis floor, which is the point of deciding "
            "here rather than later: a cell that cannot be printed is a cell that will not be "
            "modelled, and the level is a consequence of the counts rather than a judgment made "
            "after seeing them.", 86)
        lines.append("")

    lines.append(_THIN)
    lines.append("BEFORE ANYTHING ELSE RUNS")
    lines.append(_THIN)
    lines.append("")
    lines += _bullets([
        "Paste this table into the session log, with the run cost report beside it.",
        "Record the collapse level in the session log, because the Methods names it and the "
        "exported result carries it.",
        "Only then load the feature builder. It reads the eligible episodes and the daily "
        "grids; it does not rebuild any of this.",
        "Delete the compute environment when the session ends and verify the applications tab "
        "is empty. The derived tables outlive the environment, which is why the next session "
        "is one call and not a rebuild.",
    ])
    lines.append("")
    lines.append(DISCLOSURE_SENTENCE)
    lines.append("")
    lines.append(_RULE)
    return "\n".join(lines)


# ======================================================================================
# (11) The driver.
# ======================================================================================

def run_cohort(
    *,
    hr_minute_column: str,
    device_model_column: str = "",
    ed_visit_concept_ids: Sequence[int],
    inpatient_visit_concept_ids: Sequence[int],
    junction_map: str = "primary",
    primary_wear_definition: str = "primary",
    start_stage: str = "",
    call: bool = True,
    build_sql_path: str | Path | None = None,
    budget_gb: float = DAG_BUDGET_GB,
    q_guarded: Callable[..., pd.DataFrame] | None = None,
    dry_run_gb: Callable[[str], float] | None = None,
    show_report: bool = True,
) -> Mapping[str, Any]:
    """Price the DAG, optionally call it, assert the ladder, emit the ledgers, and stop.

    `call=False` is the priced-only path: every stage is dry-run, the cost table is printed, and
    nothing executes.  It is how the first run of a session answers "what will this cost" for
    nothing, and it is the flag to reach for when the last run's tables are still in place.
    """
    query, price = _resolve_runtime(q_guarded, dry_run_gb)
    params = dag_parameters(
        hr_minute_column=hr_minute_column,
        device_model_column=device_model_column,
        ed_visit_concept_ids=ed_visit_concept_ids,
        inpatient_visit_concept_ids=inpatient_visit_concept_ids,
        junction_map=junction_map,
        primary_wear_definition=primary_wear_definition,
    )
    stages = split_stages(read_build_sql(build_sql_path))
    plan = price_dag(params=params, dry_run_gb=price, stages=stages,
                     start_stage=start_stage, budget_gb=budget_gb)

    if show_report:
        cost_text = render_cost_plan(plan)
        assert_house_prose(cost_text, allow=STAGE_ORDER)
        print(cost_text)

    result: dict[str, Any] = {
        "parameters": params,
        "plan": plan,
        "called": False,
        "ladder": None,
        "collapse": None,
        "report": "",
    }
    if not call:
        if show_report:
            print("Priced only. Nothing was submitted and nothing billed. Pass the call flag "
                  "when the number above is approved.")
        return MappingProxyType(result)

    result["run"] = run_dag(params=params, plan=plan, q_guarded=query, start_stage=start_stage,
                            announce=show_report)
    result["called"] = True

    frame = read_ladder(q_guarded=query)
    if show_report:
        safe_show(frame, name="attrition ladder")
    ladder = assert_ladder(frame, junction_map=params["junction_map"])
    totals = read_reconciliation(q_guarded=query)
    reconciliation = reconcile_ladder(ladder, totals)

    ledgers = read_ledgers(q_guarded=query)
    group_counts = read_group_counts(q_guarded=query)
    collapse = collapse_level(group_counts, analytic=ladder["analytic"])

    sections = [
        render_ladder(frame, ladder),
        render_closure(ladder, reconciliation),
        render_exclusion_ledger(ledgers["ledger_exclusion_reasons"]),
        render_wear_ledger(ledgers["ledger_wear_by_day"]),
        render_matched_set_ledger(ledgers["ledger_matched_sets"]),
        render_missingness_ledger(ledgers["ledger_variable_missingness"]),
        render_hard_stop(ladder, collapse),
    ]
    report = "\n".join(sections)
    assert_house_prose(report)

    result.update({
        "ladder": ladder,
        "ladder frame": frame,
        "reconciliation": reconciliation,
        "ledgers": ledgers,
        "collapse": collapse,
        "report": report,
    })
    if show_report:
        print(report)
    return MappingProxyType(result)


# ======================================================================================
# (12) Command line.
#
# The visit concept ids are NOT typed at the command line and there is no default for them.
# They are prespecified in `01_probe.py` and verified there against the CDR's own distribution,
# and this module imports them from that file by path, because a module name beginning with a
# digit is not an importable identifier.  A constant nobody checked is an assumption, and
# CLAUDE.md stop condition 1 halts the build on exactly that.
# ======================================================================================

_PROBE_FILENAME = "01_probe.py"
_PROBE_MODULE_NAME = "_cohort_probe_01"


def load_probe_module() -> Any:
    """Load `01_probe.py` from beside this file and return it as a module object.

    Executing its body costs no query and touches no network: imports, constants and function
    definitions, with its own entry point behind the usual guard, which a path-based load does
    not satisfy.  Registered under a name that deliberately does not look importable, so nobody
    is invited to type an import that cannot work.
    """
    if _PROBE_MODULE_NAME in sys.modules:
        return sys.modules[_PROBE_MODULE_NAME]
    import importlib.util

    path = _HERE / _PROBE_FILENAME
    if not path.is_file():
        raise CohortError(
            f"{_PROBE_FILENAME} was not found beside this file. The emergency and inpatient "
            f"visit concept ids are prespecified there and verified there against the CDR's "
            f"own distribution; there is no default for them here and there must never be one."
        )
    spec = importlib.util.spec_from_file_location(_PROBE_MODULE_NAME, path)
    if spec is None or spec.loader is None:            # pragma: no cover - importlib contract
        raise CohortError(f"{_PROBE_FILENAME} could not be loaded by path")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_PROBE_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="03_cohort.py",
        description="Price the derived-table DAG stage by stage, build it, and emit the "
                    "nineteen-rung attrition ladder and the STROBE ledgers. Ends at the "
                    "project's second hard stop.")
    parser.add_argument("--self-test", action="store_true",
                        help="exercise the splitter and every ladder assertion against "
                             "synthetic ladders and exit. No cloud, no configuration.")
    parser.add_argument("--price-only", action="store_true",
                        help="dry-run every stage, print the cost table, execute nothing. "
                             "This is the default.")
    parser.add_argument("--call", action="store_true",
                        help="price, then call the procedure, then assert and report.")
    parser.add_argument("--resume", default="",
                        help="rebuild from this stage onward. One of the nineteen table names, "
                             "in DAG order. The parameter table is always rewritten.")
    parser.add_argument("--junction-map", default="primary", choices=list(JUNCTION_MAPS),
                        help="the region map for junction codes (default primary).")
    parser.add_argument("--wear-definition", default="primary", choices=list(WEAR_DEFINITIONS),
                        help="the primary valid-wear rule. The second is the prespecified "
                             "contingency and needs a logged amendment.")
    parser.add_argument("--hr-minute-column", default=None,
                        help="the per-zone minute column of the heart-rate table. Defaults to "
                             "the name the probe prespecifies and verifies.")
    parser.add_argument("--device-model-column", default="",
                        help="the model column of the device table, or empty when the release "
                             "carries none.")
    parser.add_argument("--budget-gb", type=float, default=DAG_BUDGET_GB,
                        help=f"the approval ceiling for the priced DAG total (default "
                             f"{DAG_BUDGET_GB}). Raise it deliberately, with the measured "
                             f"number in hand.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Exit 0 reviewed and stopped, 1 a stop condition fired, 2 no configuration, 64 usage."""
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return 64 if exc.code not in (0, None) else 0

    if args.self_test:
        _run_self_test()
        return 0

    try:
        probe = load_probe_module()
        result = run_cohort(
            hr_minute_column=args.hr_minute_column or probe.HR_ZONE_MINUTE_COLUMN,
            device_model_column=args.device_model_column,
            ed_visit_concept_ids=tuple(probe.ED_VISIT_CONCEPT_IDS),
            inpatient_visit_concept_ids=tuple(probe.INPATIENT_VISIT_CONCEPT_IDS),
            junction_map=args.junction_map,
            primary_wear_definition=args.wear_definition,
            start_stage=args.resume,
            call=bool(args.call) and not args.price_only,
            budget_gb=args.budget_gb,
        )
    except LadderClosureError as exc:
        print("")
        print(_RULE)
        print("03_cohort.py HALTED: the attrition ladder does not close")
        print(_RULE)
        for line in str(exc).splitlines():
            print("  " + line)
        print("")
        print("This is stop condition 3. The derived tables exist and they are wrong. Fix the")
        print("definition that produced the disagreement and rebuild from that stage; do not")
        print("adjust a count to make it close.")
        print(_RULE)
        return 1
    except CohortBudgetExceeded as exc:
        print("")
        print(_RULE)
        print("03_cohort.py HALTED: the priced DAG exceeds its approval figure")
        print(_RULE)
        for line in str(exc).splitlines():
            print("  " + line)
        print(_RULE)
        return 1
    except CohortError as exc:
        print("")
        print(_RULE)
        print("03_cohort.py HALTED before anything was submitted")
        print(_RULE)
        for line in str(exc).splitlines():
            print("  " + line)
        print(_RULE)
        return 2

    if not result["called"]:
        return 0
    print("")
    print("Run the session cost report, paste it into the session log beside the table above,")
    print("then delete the compute environment and verify the applications tab is empty.")
    return 0


# ======================================================================================
# (13) Self-test.  Everything checkable without the cloud.
#
# Same shape as `_run_self_test()` in `disclosure.py` and `02_pregate.py`:
# `python3 03_cohort.py --self-test` answers "is the pure logic of this module sane" with no
# pytest, no configuration and no network.  It runs the REAL stage splitter against the REAL
# `build_all.sql` on disk, and it drives the ladder assertions against a synthetic ladder that
# is correct and against ladders broken in each specific way.  EVERY BROKEN LADDER MUST RAISE:
# an assertion that cannot be shown to fail is decoration.
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
    except Exception as other:                       # pragma: no cover - a failing assertion
        raise AssertionError(f"{message} (raised {type(other).__name__} instead)") from None
    raise AssertionError(message)


# ---- the contract's own bytes, when this side of the boundary carries them ---------------
#
# READ ONLY, and only by the self-test.  This module runs inside the Workbench VM, where
# `prespecification/` is not uploaded, so nothing here may read the contract at import time and
# the label tables in section (1) have to be TRANSCRIPTIONS.  A transcription's failure mode is
# silent: the contract grows a row or rewords one, this module goes on emitting the old
# sentence, and the divergence is found by a reader of the manuscript rather than by a check.
# These two functions are what make it loud on any checkout that carries the file.


def _find_export_contract() -> Path | None:
    """`prespecification/EXPORT-CONTRACT.md`, if this checkout carries it, else None.

    Searched rather than computed from `_HERE` alone, because `_HERE` falls back to the cwd
    when there is no `__file__` (a paste, or `%run -i`) and the cwd on a Workbench VM is
    wherever the human last cd'd to.
    """
    cwd = Path.cwd().resolve()
    seen: set[Path] = set()
    for directory in (_HERE, _HERE.parent, cwd, *cwd.parents):
        candidate = directory / "prespecification" / "EXPORT-CONTRACT.md"
        if candidate in seen:
            continue
        seen.add(candidate)
        if candidate.is_file():
            return candidate
    return None


def _contract_suppression_sentences(text: str) -> list[tuple[str, str]]:
    """Section 7.5's markdown table, parsed into (slug, sentence) pairs in the contract's order.

    Pairs and not a dict, so ORDER is checkable too.  A table holding the right ten rows in a
    different order is a table somebody reordered by hand, and the check that would wave that
    through is the check that would also wave through a reworded row.
    """
    rows: list[tuple[str, str]] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("### 7.5"):
            inside = True
            continue
        if inside and line.startswith("#"):
            break
        if not inside or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] == "slug" or set(cells[0]) <= set("-: "):
            continue
        rows.append((cells[0].strip("`"), cells[1]))
    return rows


def _first_suppression_divergence(
    contract_rows: Sequence[tuple[str, str]],
    module_rows: Sequence[tuple[str, str]],
) -> str:
    """Where a transcribed 7.5 table and the contract's own part company, or "" when they agree.

    ORDERED PAIRS, POSITION BY POSITION, so this fails on a REORDERING and not only on a row
    that is missing or reworded.  Held in a named function rather than inline in the self-test
    so that the CHECK ITSELF can be checked: a comparison that waves a reordering through is
    the same comparison that would wave a reworded row through, and asserting that it fails on
    both is the only way to know it is an ordered-pair check rather than a set comparison that
    happens to be written over lists.

    The row count is reported first and on its own, because a length mismatch makes every
    position after the divergence meaningless and "row 10 is missing" is the useful sentence
    when the contract has grown a row this module has not adopted.
    """
    if len(contract_rows) != len(module_rows):
        return (f"the contract carries {len(contract_rows)} row(s) and this module "
                f"transcribes {len(module_rows)}")
    return next(
        (f"row {i + 1}, contract {theirs!r} against module {mine!r}"
         for i, (theirs, mine) in enumerate(zip(contract_rows, module_rows)) if theirs != mine),
        "",
    )


# The drops that make the synthetic ladder close.  Chosen so every rung is disclosable except
# the two the plan expects to be small, which is what makes the suppression paths reachable.
_FIXTURE_DROPS: Mapping[int, int] = MappingProxyType({
    3: 900, 4: 600, 5: 400, 6: 120, 7: 300, 8: 250, 9: 180,
    10: 140, 11: 7332, 12: 220, 13: 60, 14: 50, 15: 188,
})
_FIXTURE_PERSONS = 400_000
_FIXTURE_WITH_CONCEPT = 9_720
_FIXTURE_WITH_EPISODE = 9_000
_FIXTURE_EPISODES = 11_000
_FIXTURE_EVENTS = 120
_FIXTURE_EVENTS_DROPPED = 25


def _fixture_ladder(junction_map: str = "primary") -> pd.DataFrame:
    """A synthetic nineteen-rung ladder that closes by all four rules.  Every count an integer."""
    drops = dict(_FIXTURE_DROPS)
    running = _FIXTURE_EPISODES
    episode_in: dict[int, int] = {}
    episode_out: dict[int, int] = {}
    for step in EPISODE_DROP_STEPS:
        episode_in[step] = running
        running -= drops[step]
        episode_out[step] = running
    analytic = running
    events_out = _FIXTURE_EVENTS - _FIXTURE_EVENTS_DROPPED

    counts: dict[int, tuple[int, int | None, int, int | None]] = {
        1: (_FIXTURE_PERSONS, _FIXTURE_PERSONS - _FIXTURE_WITH_CONCEPT, _FIXTURE_WITH_CONCEPT, None),
        2: (_FIXTURE_WITH_CONCEPT, _FIXTURE_WITH_CONCEPT - _FIXTURE_WITH_EPISODE,
            _FIXTURE_EPISODES, _FIXTURE_WITH_EPISODE),
        16: (analytic, None, analytic, None),
        17: (analytic, None, _FIXTURE_EVENTS, None),
        18: (_FIXTURE_EVENTS, _FIXTURE_EVENTS_DROPPED, events_out, None),
        19: (events_out, None, events_out, None),
    }
    for step in EPISODE_DROP_STEPS:
        counts[step] = (episode_in[step], drops[step], episode_out[step], None)

    rows = []
    for rung in ATTRITION_RUNGS:
        step = rung["step"]
        n_in, dropped, n_out, carried = counts[step]
        reason = (REASON_UNIT_CHANGE if rung["kind"] == "conversion"
                  else REASON_NOT_APPLICABLE if rung["kind"] == "terminal" else rung["slug"])
        rows.append({
            "step": step, "slug": rung["slug"], "kind": rung["kind"], "unit": rung["unit"],
            "n_in": n_in, "n_dropped": dropped, "n_out": n_out, "n_carried_forward": carried,
            "reason": reason, "closes_exact": True, "junction_map": junction_map,
            "built_at": "2026-08-26T00:00:00Z",
        })
    return pd.DataFrame(rows)


def _fixture_totals(frame: pd.DataFrame) -> dict[str, int]:
    """The reconciliation counts that agree with a fixture ladder."""
    by_step = {int(row["step"]): row for _, row in frame.iterrows()}
    charged = sum(int(by_step[step]["n_dropped"]) for step in EPISODE_DROP_STEPS)
    return {
        "n_episodes": int(by_step[2]["n_out"]),
        "n_exclusion_rows": int(by_step[2]["n_out"]),
        "n_eligible": int(by_step[16]["n_out"]),
        "n_charged": charged,
        "n_eligible_and_charged": 0,
        "n_neither": 0,
        "n_charged_off_ladder": 0,
    }


def _broken(mutate: Callable[[pd.DataFrame], None]) -> pd.DataFrame:
    """A fixture ladder with one specific defect introduced."""
    frame = _fixture_ladder()
    mutate(frame)
    return frame


def _fixture_exclusion_ledger() -> pd.DataFrame:
    """One row per reason detail, with the three declared partitions closing on their totals."""
    rows: list[dict[str, Any]] = []
    slug_of = {rung["step"]: rung["slug"] for rung in ATTRITION_RUNGS}
    payload = {
        (3, "trauma"): (420, 900), (3, "spinal_cord_injury"): (60, 900),
        (3, "malignancy"): (300, 900), (3, "metastatic_disease"): (80, 900),
        (3, "spinal_infection"): (140, 900),
        (4, "ed_encounter_present"): (1500, 1500),
        (4, "rescue_elective_coded"): (300, 1500),
        (4, "rescue_degenerative_index"): (420, 1500),
        (4, "rescue_degenerative_outpatient_90d"): (180, 1500),
        (12, "no_valid_baseline_day"): (100, 220),
        (12, "fewer_than_seven_valid_days"): (80, 220),
        (12, "baseline_span_under_14_days"): (40, 220),
        (14, "no_analyzable_day_in_window"): (30, 50),
        (14, "not_at_risk_in_window"): (20, 50),
        # The step 15 partition: EXACTLY ONE member below the floor, which must force the
        # other one beside it. Two members, so suppressing one suppresses the whole breakdown;
        # that is the rule working rather than a defect in it.
        (15, "death"): (8, 188), (15, "repeat_spine_operation"): (180, 188),
        (16, "censoring_none"): (180, 260), (16, "censoring_death"): (24, 260),
        (16, "censoring_repeat_spine_operation"): (28, 260),
        (16, "censoring_cdr_observation_cutoff"): (28, 260),
    }
    for (step, detail), (episodes, denominator) in payload.items():
        rows.append({"step": step, "slug": slug_of[step], "reason_detail": detail,
                     "n_episodes": episodes, "n_denominator": denominator})
    return pd.DataFrame(rows)


def _fixture_wear_ledger() -> pd.DataFrame:
    """Two groups over ninety days, with the tail falling below the floor as the cohort thins."""
    rows: list[dict[str, Any]] = []
    for order, slug in ((1, "cervical_fusion"), (3, "lumbar_decompression")):
        for day in range(1, 91):
            at_risk = max(0, 260 - order * 20 - day * 2)
            rows.append({"group_slug": slug, "group_order": order, "day": day,
                         "n_at_risk": at_risk, "n_valid_wear": int(at_risk * 0.7)})
    return pd.DataFrame(rows)


def _fixture_matched_sets() -> pd.DataFrame:
    return pd.DataFrame([
        {"set_size": 0, "n_sets": 8, "n_cases": 8},
        {"set_size": 3, "n_sets": 40, "n_cases": 40},
        {"set_size": 5, "n_sets": 60, "n_cases": 60},
    ])


def _fixture_missingness() -> pd.DataFrame:
    payload = {
        "age_at_index": (260, 0), "sex_at_birth": (260, 24), "race_concept_id": (260, 40),
        "ethnicity_concept_id": (260, 40), "bmi": (260, 60), "charlson_score": (260, 30),
        "los_days": (260, 0), "device_family": (260, 80), "baseline_steps": (260, 0),
        "procedure_group": (260, 0), "daily_deficit": (9100, 1720), "r72": (120, 40),
    }
    return pd.DataFrame([{"variable": name, "n_total": total, "n_missing": missing}
                         for name, (total, missing) in payload.items()])


def _run_self_test() -> None:
    global _ASSERTIONS
    _ASSERTIONS = 0

    # ---- 1. the rung list, against ANALYSIS-PLAN.md section 2.6 ------------------------
    _expect(len(ATTRITION_RUNGS) == 19, "the ladder has nineteen rungs")
    _expect(LADDER_STEPS == tuple(range(1, 20)), "the steps run 1 through 19 with no gap")
    _expect(len(set(LADDER_SLUGS)) == 19, "the nineteen slugs are distinct")
    _expect(set(LADDER_SLUGS) == set(RUNG_LABELS), "every rung has a ladder-box label")
    _expect(set(LADDER_SLUGS) == set(RUNG_REASON_DISPLAY), "every rung has a reason entry")
    _expect(tuple(rung["kind"] for rung in ATTRITION_RUNGS
                  if rung["kind"] == "conversion") == ("conversion",) * 2,
            "exactly two rungs are conversions")
    _expect(tuple(rung["step"] for rung in ATTRITION_RUNGS
                  if rung["kind"] == "conversion") == CONVERSION_STEPS,
            "and they are the two the plan names")
    _expect(tuple(rung["step"] for rung in ATTRITION_RUNGS
                  if rung["kind"] == "terminal") == TERMINAL_STEPS,
            "the two terminal rungs are the two the plan names")
    _expect(all(rung["unit"] in _UNITS for rung in ATTRITION_RUNGS),
            "every unit is one of the five the contract permits")
    _expect(RUNG_LABELS["excl_window_truncated_by_death_or_reoperation"]
            == RUNG_LABELS["analytic_cohort"] == "Analytic cohort",
            "steps 15 and 16 share a label, because a rung names the box of survivors below it")
    _expect(RUNG_LABELS["excl_event_without_computable_landmark"]
            == RUNG_LABELS["events_analyzable"] == "Analyzable acute-care events",
            "and so do steps 18 and 19")
    _expect(sum(1 for slug in LADDER_SLUGS if not RUNG_REASON_DISPLAY[slug]) == 3,
            "exactly three rungs carry an empty reason, which means not applicable")

    # THE TRAP: the label table is keyed by SLUG, and the reason column is not a key into it.
    _expect_raises(CohortError, lambda: rung_label(REASON_UNIT_CHANGE),
                   "keying the label table with a conversion rung's reason raises")
    _expect_raises(CohortError, lambda: rung_label(REASON_NOT_APPLICABLE),
                   "keying it with a terminal rung's reason raises")
    _expect_raises(CohortError, lambda: rung_reason_display(REASON_UNIT_CHANGE),
                   "the same holds for the reason-display table")
    _expect_raises(CohortError, lambda: rung_label("no_such_rung"),
                   "and an invented slug raises rather than returning something plausible")
    _expect(REASON_UNIT_CHANGE not in RUNG_LABELS and REASON_NOT_APPLICABLE not in RUNG_LABELS,
            "neither reason value is a key in the label table and neither ever will be")

    # ---- 1b. the label tables, against EXPORT-CONTRACT.md's OWN BYTES ------------------
    # Section (1)'s tables are transcriptions, and a transcribed table with no check is how the
    # other nine sentences would drift one at a time.  The literals below are checked
    # unconditionally, so a stripped checkout is still pinned; when the contract is on this side
    # of the boundary the whole of 7.5 is checked against it, slug for slug, character for
    # character and in the contract's own row order, so the two cannot part company without one
    # of these failing.
    _expect(len(SUPPRESSION_SENTENCES) == 10,
            "section 7.5 carries ten suppression reasons; the tenth moves a row count in a "
            "vocabulary the contract transcribes, which is a minor bump under 11.2's first row")
    _expect(SUPPRESSION_SENTENCES["no_crossing_within_range"]
            == "no crossing within the prespecified range",
            "the ninth sentence is the contract's own and not a paraphrase of it")
    _expect(SUPPRESSION_SENTENCES["no_crossing_within_range"]
            != SUPPRESSION_SENTENCES["not_estimable_data_unavailable"],
            "and it is a DIFFERENT sentence from the one it replaced, which is the whole "
            "reason it exists: a contrast that never crosses is a finding, not a missing datum")
    _expect(SUPPRESSION_SENTENCES["not_estimable_separation"] == "not estimable (separation)",
            "the tenth sentence is the contract's own and not a paraphrase of it")
    _expect(SUPPRESSION_SENTENCES["not_estimable_separation"]
            != SUPPRESSION_SENTENCES["not_estimable_convergence"],
            "and it is a DIFFERENT sentence from the convergence one, which is the whole "
            "reason it exists: a quasi-separated fit CONVERGES, so the convergence sentence "
            "would be a false sentence rather than a near-enough one")
    _expect(len(set(SUPPRESSION_SENTENCES.values())) == len(SUPPRESSION_SENTENCES),
            "no two slugs share a sentence, so a printed cell names exactly one reason")
    _expect(not any(EM_DASH in sentence for sentence in SUPPRESSION_SENTENCES.values()),
            "and no sentence carries an em dash, which the bundle refuses")
    contract_path = _find_export_contract()
    if contract_path is None:                        # pragma: no cover - a partial checkout
        _expect(True, "EXPORT-CONTRACT.md is not on this side of the boundary, so the literals "
                      "above are the only pin available and they have just been checked")
    else:
        contract_rows = _contract_suppression_sentences(
            contract_path.read_text(encoding="utf-8"))
        module_rows = list(SUPPRESSION_SENTENCES.items())
        first_divergence = _first_suppression_divergence(contract_rows, module_rows)
        _expect(not first_divergence,
                f"every row of section 7.5 is transcribed here character for character and in "
                f"the contract's own order; the first divergence is {first_divergence}")
        # THE CHECK ITSELF, CHECKED, on synthetic tables.  A comparison that waves a reordering
        # through is the same comparison that would wave a reworded row through, so both of the
        # two ways a transcription goes wrong are exercised rather than read off the code.
        _expect(_first_suppression_divergence(module_rows[1:] + module_rows[:1], module_rows),
                "the transcription check fails on a REORDERING, which is what makes it an "
                "ordered-pair check and not a set comparison written over lists")
        _expect(_first_suppression_divergence(module_rows[:-1], module_rows),
                "and on a MISSING row, which is how the tenth suppression reason would have "
                "arrived if the contract had grown it and this module had not")
        _expect(_first_suppression_divergence(module_rows, module_rows) == "",
                "and returns the empty string on two tables that agree, so it is the "
                "divergence that fails the assertion and never the check's own shape")
        _expect(_contract_suppression_sentences("### 7.5 x\n| slug | display sentence |\n"
                                                "|---|---|\n| `a_slug` | a sentence |\n"
                                                "\n### 7.6 y\n| `b_slug` | b sentence |\n")
                == [("a_slug", "a sentence")],
                "and the parser stops at the next heading rather than swallowing 7.6, which is "
                "what would make the check above pass on a table it never read")

    # ---- 2. the stage splitter, against the REAL build_all.sql -------------------------
    sql_text = read_build_sql()
    stages = split_stages(sql_text)
    _expect(len(stages) == 19, "the splitter finds exactly nineteen stages")
    _expect(tuple(stage["name"] for stage in stages) == STAGE_ORDER,
            "and finds them in DAG order")
    _expect(tuple(stage["index"] for stage in stages) == tuple(range(1, 20)),
            "and every stage index matches its position, which is what the resume flag compares")

    templated = tuple(stage["name"] for stage in stages if stage["is_template"])
    declared = tuple(stage["name"] for stage in stages if stage["format_args"])
    _expect(templated == ("hr_daily", "device_daily"),
            "exactly two stages are dynamic-statement templates")
    _expect(declared == templated,
            "and exactly those two carry a format-argument marker, in both directions")
    _expect({stage["name"]: len(stage["format_args"]) for stage in stages if stage["format_args"]}
            == {"hr_daily": 2, "device_daily": 1},
            "each template declares as many arguments as it has substitution positions")

    # THE FALSE POSITIVE THE TEST IS KEYED AWAY FROM.  Three stages carry a literal percent-s
    # inside an ordinary static format call and none of them is a template.  A test keyed on the
    # percent sign would flag all three and demand a marker none of them needs.
    static_percent = tuple(stage["name"] for stage in stages
                           if stage["n_placeholders"] and not stage["is_template"])
    _expect(static_percent == ("episodes", "events", "risk_sets"),
            "three stages carry a substitution marker in static SQL and are not templates")
    _expect(all(not stage["format_args"] for stage in stages
                if stage["name"] in static_percent),
            "and none of the three declares format arguments, which is correct")

    # Comment stripping is what makes the count meaningful: the raw bodies carry a marker inside
    # the comment that explains the markers.
    raw = {stage["name"]: stage["body"].count("%s") for stage in stages if stage["is_template"]}
    _expect(raw == {"hr_daily": 3, "device_daily": 2},
            "the raw template bodies each carry one extra marker, inside their own comment")
    _expect({stage["name"]: stage["n_placeholders"] for stage in stages if stage["is_template"]}
            == {"hr_daily": 2, "device_daily": 1},
            "and stripping whole-line comments leaves exactly the real substitution positions")

    # ---- 3. making each body standalone and priceable ----------------------------------
    params = dag_parameters(hr_minute_column="minute_in_zone", device_model_column="model_name",
                            ed_visit_concept_ids=(9203, 262),
                            inpatient_visit_concept_ids=(9201, 262))
    priced = {stage["name"]: stage_priceable_sql(stage, params=params) for stage in stages}
    _expect(len(priced) == 19, "every stage yields a priceable statement")
    template_names = {stage["name"] for stage in stages if stage["is_template"]}
    for name, text in priced.items():
        # The "nothing survives" rule reaches the TEMPLATES only. The three static-SQL stages
        # legitimately keep their marker, because it is an argument to an ordinary format call
        # that BigQuery evaluates at run time and not a position this module fills.
        if name in template_names:
            _expect("%s" not in text, f"no substitution position survives in {name}")
        _expect(_EXECUTE_IMMEDIATE not in text,
                f"{name} is priced as the statement that will run, not as its dynamic wrapper")
        _expect(text.lstrip().upper().startswith(("CREATE", "INSERT", "SELECT")),
                f"{name} prices a statement rather than a fragment")
        found = set(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", text))
        _expect(found <= {"{CDR}", "{DERIVED}"},
                f"{name} carries only sanctioned placeholders, and it carries {sorted(found)}")
        _expect("{GOOGLE_PROJECT}" not in text, f"{name} does not use the spelling that raises")
        _expect("wb-" not in text and "C2025Q4R6" not in text,
                f"{name} hardcodes no project and no dataset")
        _expect(EM_DASH not in text and MINUS_SIGN not in text,
                f"{name} carries no banned character")

    _expect("'minute_in_zone'" in priced["build_params"],
            "the parameter stage is made standalone by substituting its parameters as literals")
    _expect("[9203, 262]" in priced["build_params"] and "[9201, 262]" in priced["build_params"],
            "including both visit concept arrays")
    _expect(f"'{SAMPLING_SALT}'" in priced["build_params"] and "0 " in priced["build_params"],
            "and the seed and salt, which are internal constants rather than parameters")
    _expect("CURRENT_TIMESTAMP() " in priced["build_params"],
            "an expression that is not a bare self-aliased name is left alone")
    _expect(not re.search(r"^\s+junction_map\s+AS\s+junction_map", priced["build_params"], re.M),
            "and no bare parameter name survives on the expression side")
    _expect("h.minute_in_zone" in priced["hr_daily"],
            "the heart-rate template takes the probed column")
    _expect(priced["hr_daily"].count("minute_in_zone") == 2,
            "in both of its substitution positions")
    _expect("d.model_name" in priced["device_daily"],
            "and the device template takes the probed model column")

    # The empty-model case takes the other branch, which reads nothing.
    params_no_device = dag_parameters(hr_minute_column="minute_in_zone", device_model_column="",
                                      ed_visit_concept_ids=(9203,),
                                      inpatient_visit_concept_ids=(9201,))
    empty = stage_priceable_sql(
        next(s for s in stages if s["name"] == "device_daily"), params=params_no_device)
    _expect("device_family STRING" in empty and "{CDR}" not in empty,
            "with no model column the priced statement is the one that creates the table empty")
    _expect("%s" not in empty, "and it carries no unsubstituted position")

    # ---- 4. the marker contract, in both directions -----------------------------------
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace("  -- @stage-format-args: device_model_column\n", "")),
        "a template whose format-argument marker is missing is refused")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace(
            "  -- @stage-begin: attrition",
            "  -- @stage-begin: attrition\n  -- @stage-format-args: junction_map")),
        "a non-template that declares format arguments is refused")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace(
            "  -- @stage-format-args: hr_minute_column, hr_minute_column",
            "  -- @stage-format-args: hr_minute_column")),
        "a template declaring fewer arguments than it has positions is refused")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace("  -- @stage-end: baseline\n", "")),
        "an unclosed stage is refused")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace("  -- @stage-end: features", "  -- @stage-end: feature")),
        "a stage closed under a different name is refused")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace("  -- @stage-begin: events\n", "")
                             .replace("  -- @stage-end: events\n", "")),
        "a stage that disappears from the file is refused, because it would go unpriced")
    _expect_raises(StageMarkerError, lambda: read_build_sql("/no/such/file.sql"),
                   "a missing DAG file is refused rather than defaulted")
    _expect_raises(StageMarkerError,
                   lambda: _substitute_format_args("SELECT %s, %s", ["a"]),
                   "a surviving substitution position is a stop condition")

    # ---- 4b. the procedure's OWN declarations of the same order ------------------------
    # The failures a marker check cannot see.  A stage inserted mid-DAG renumbers every guard
    # below it, and a guard left wrong misdirects the resume flag while every marker, every
    # name and every count stays correct.
    _expect(_STAGES_DECLARATION_RE.search(sql_text) is not None,
            "the procedure declares its stage order in an array this module can read")
    _expect(tuple(re.findall(r"'([a-z_][a-z0-9_]*)'",
                             _STAGES_DECLARATION_RE.search(sql_text).group("body")))
            == STAGE_ORDER,
            "and that array is this module's tuple, name for name and in order")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace("  IF start_ix <= 14 THEN",
                                              "  IF start_ix <= 13 THEN")),
        "a guard renumbered one too low is refused, because it rebuilds an excluded stage")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace("  IF start_ix <= 15 THEN\n", "")),
        "a stage that has lost its guard is refused, because a resume cannot skip it")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace("    'landmark_daily',                 -- 13\n",
                                              "")),
        "a stage missing from the procedure's array is refused, because the resume flag cannot "
        "resolve its name")
    _expect_raises(
        StageMarkerError,
        lambda: split_stages(sql_text.replace(
            "  DECLARE stages ARRAY<STRING> DEFAULT [", "  DECLARE stages_x ARRAY<STRING> [")),
        "and a file with no such array at all is refused rather than priced unchecked")

    # ---- 5. the cost model, and the per-child-job cap ----------------------------------
    estimates = {"hr_daily": 60.0, "features": 25.0, "episodes": 8.0, "episodes_eligible": 6.0,
                 "events": 4.0, "risk_sets": 1.0, "build_params": 0.01}
    priced_calls: list[str] = []

    def fake_price(sql: str) -> float:
        priced_calls.append(sql)
        for name, text in priced.items():
            if text == sql:
                return estimates.get(name, 0.1)
        # The empty-device branch and any resume subset still price through the same table.
        return 0.1

    plan = price_dag(params=params, dry_run_gb=fake_price, stages=stages)
    _expect(len(priced_calls) == 19, "every stage is dry-run before anything executes")
    _expect(len(plan["stages"]) == 19, "and every stage appears in the plan")
    _expect(abs(plan["total gb"] - (60.0 + 25.0 + 8.0 + 6.0 + 4.0 + 1.0 + 0.01 + 12 * 0.1)) < 1e-9,
            "the total is the sum of the per-stage estimates")
    _expect(plan["binding stage"] == "hr_daily", "the binding stage is the one that scans most")
    _expect(abs(plan["call cap gb"] - 60.0 * (1 + STAGE_CAP_MARGIN)) < 1e-9,
            "THE CAP IS SIZED ON THE BINDING STAGE, not on the total")
    _expect(plan["call cap gb"] < plan["total gb"],
            "and on this DAG that cap is strictly tighter than a total-sized one would be")
    _expect(abs(plan["worst case gb"] - plan["call cap gb"] * 19) < 1e-6,
            "the worst case the cap permits is nineteen child jobs at that cap, and it is shown")
    _expect(stage_cap_gb(0.0) == STAGE_CAP_FLOOR_GB,
            "a stage estimated at nothing still gets a floor, because BigQuery bills a minimum")
    _expect(stage_cap_gb(100.0) == 125.0, "and a priced stage gets its own estimate plus margin")
    _expect_raises(CohortError, lambda: stage_cap_gb(-1.0),
                   "a negative estimate is not a byte count")

    # The refusal fires on the TOTAL, which is the approval figure, and it fires before
    # anything is submitted.
    _expect_raises(CohortBudgetExceeded,
                   lambda: price_dag(params=params, dry_run_gb=fake_price, stages=stages,
                                     budget_gb=1.0),
                   "a DAG priced above its approval figure is refused and nothing executes")

    resumed = price_dag(params=params, dry_run_gb=fake_price, stages=stages,
                        start_stage="features")
    _expect(tuple(row["name"] for row in resumed["stages"])[0] == "build_params",
            "a resumed run still rewrites the parameter table, whatever the resume point says")
    _expect(len(resumed["stages"]) == 11,
            "and rebuilds the ten stages from the resume point onward")
    _expect(resumed["binding stage"] == "features",
            "the binding stage of a resumed run is the largest of the stages it will build")
    _expect_raises(CohortError,
                   lambda: price_dag(params=params, dry_run_gb=fake_price, stages=stages,
                                     start_stage="no_such_stage"),
                   "an unknown resume point is refused")

    # ---- 6. the call itself -------------------------------------------------------------
    call_sql = build_call_sql(params=params, start_stage="")
    argument_lines = [line.strip() for line in call_sql.splitlines()[1:-1] if line.strip()]
    # Counted as LINES rather than as commas, because two of the seven arguments are array
    # literals carrying commas of their own and a comma count says nine.
    _expect(len(argument_lines) == 7 and call_sql.startswith("CALL `{DERIVED}.build_all`("),
            "the call passes seven positional arguments to the procedure")
    _expect(call_sql.strip().endswith(")"), "and is one statement")
    _expect("'minute_in_zone'" in call_sql and "[9203, 262]" in call_sql,
            "carrying both probe results")
    _expect(argument_lines[-1] == "''",
            "with the resume point last, and empty for a full build it is still a literal "
            "rather than an omitted argument")
    _expect("'attrition'" in build_call_sql(params=params, start_stage="attrition"),
            "a named resume point reaches the seventh argument")
    _expect_raises(CohortError, lambda: build_call_sql(params=params, start_stage="nope"),
                   "and an unknown one is refused before the call is built")
    _expect_raises(CohortError, lambda: _sql_string("it's"),
                   "a run parameter that would close its own literal is refused, never escaped")
    _expect_raises(CohortError, lambda: _sql_int_array(()),
                   "an empty visit concept array is refused, because it silently zeroes a rung")
    _expect_raises(CohortError, lambda: _sql_int_array(("9203",)),
                   "and a string in that array is refused")

    # ---- 7. parameter validation --------------------------------------------------------
    _expect_raises(CohortError,
                   lambda: dag_parameters(hr_minute_column="minute in zone",
                                          ed_visit_concept_ids=(1,),
                                          inpatient_visit_concept_ids=(2,)),
                   "a heart-rate column that is not a bare identifier is refused")
    _expect_raises(CohortError,
                   lambda: dag_parameters(hr_minute_column="m", device_model_column="a-b",
                                          ed_visit_concept_ids=(1,),
                                          inpatient_visit_concept_ids=(2,)),
                   "and so is a device column that is not")
    _expect_raises(CohortError,
                   lambda: dag_parameters(hr_minute_column="m", junction_map="both",
                                          ed_visit_concept_ids=(1,),
                                          inpatient_visit_concept_ids=(2,)),
                   "a junction map outside its domain is refused")
    _expect_raises(CohortError,
                   lambda: dag_parameters(hr_minute_column="m", primary_wear_definition="s4",
                                          ed_visit_concept_ids=(1,),
                                          inpatient_visit_concept_ids=(2,)),
                   "and a wear definition outside the two the procedure accepts")
    _expect(dag_parameters(hr_minute_column="m", ed_visit_concept_ids=(1,),
                           inpatient_visit_concept_ids=(2,))["seed"] == SEED,
            "the seed is fixed and is not a parameter")

    # ---- 8. THE LADDER ASSERTIONS.  A correct ladder passes ------------------------------
    good = _fixture_ladder()
    ladder = assert_ladder(good, junction_map="primary")
    checks: _Checks = ladder["checks"]
    _expect(ladder["n_rungs"] == 19, "the fixture ladder has nineteen rungs")
    _expect(ladder["analytic"] == _FIXTURE_EPISODES - sum(_FIXTURE_DROPS.values()),
            "and its analytic count is what the removals leave")
    _expect(checks.independent > 0 and checks.transport > 0,
            "the census records both kinds of check")
    _expect(checks.total > 100, "and there are enough of them to be worth counting")

    totals = _fixture_totals(good)
    reconciliation = reconcile_ladder(ladder, totals)
    _expect(reconciliation["checks"].transport == 0,
            "EVERY check in the reconciliation is independent, which is why it is here")
    _expect(reconciliation["checks"].independent == 8,
            "and there are eight of them")

    # ---- 9. AND EVERY BROKEN LADDER RAISES ----------------------------------------------
    # A rung that does not close.
    def break_rung(frame: pd.DataFrame) -> None:
        frame.loc[frame["step"] == 5, "n_out"] = int(frame.loc[frame["step"] == 5, "n_out"].iloc[0]) + 20
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_rung)),
                   "a rung whose entering less removed is not its leaving raises")

    # A conversion rung whose carried-forward count is wrong.
    def break_carried(frame: pd.DataFrame) -> None:
        frame.loc[frame["step"] == 2, "n_carried_forward"] = _FIXTURE_WITH_EPISODE + 1
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_carried)),
                   "a conversion rung whose carried-forward count is wrong raises")

    def break_carried_inequality(frame: pd.DataFrame) -> None:
        # Persons carried forward exceed the episodes produced, which cannot happen: a carried
        # person yields at least one episode.
        frame.loc[frame["step"] == 2, "n_in"] = _FIXTURE_EPISODES + 100
        frame.loc[frame["step"] == 2, "n_dropped"] = 0
        frame.loc[frame["step"] == 2, "n_carried_forward"] = _FIXTURE_EPISODES + 100
        frame.loc[frame["step"] == 1, "n_out"] = _FIXTURE_EPISODES + 100
        frame.loc[frame["step"] == 1, "n_dropped"] = _FIXTURE_PERSONS - (_FIXTURE_EPISODES + 100)
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_carried_inequality)),
                   "carrying more persons forward than the episodes produced raises")

    # An event segment that does not close.
    def break_events(frame: pd.DataFrame) -> None:
        frame.loc[frame["step"] == 19, "n_out"] = int(
            frame.loc[frame["step"] == 19, "n_out"].iloc[0]) - 5
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_events)),
                   "an event segment that does not close raises")

    # A missing rung.
    _expect_raises(LadderClosureError,
                   lambda: assert_ladder(good[good["step"] != 7].reset_index(drop=True)),
                   "a ladder with a rung missing raises")

    # A rung out of order.
    def break_order(frame: pd.DataFrame) -> None:
        six = frame.index[frame["step"] == 6][0]
        seven = frame.index[frame["step"] == 7][0]
        frame.loc[[six, seven], "slug"] = list(frame.loc[[seven, six], "slug"])
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_order)),
                   "two rungs swapped out of the plan's order raise")

    def break_steps(frame: pd.DataFrame) -> None:
        frame.loc[frame["step"] == 9, "step"] = len(ATTRITION_RUNGS) + 1
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_steps)),
                   "a step outside 1 to 19 raises")

    # The episode segment, which is the one arithmetic check with empirical content.  The
    # break below leaves every rung's own identity intact and the chain intact, and separates
    # ONLY the analytic count from the removals, which is exactly the defect the segment exists
    # to catch: an episode that is neither eligible nor charged to a rung.
    def break_segment(frame: pd.DataFrame) -> None:
        # The analytic count moves and nothing else does, which is the shape of the defect the
        # segment describes: episodes that were removed by no rung and kept by no flag. It
        # trips the segment, the terminal identity and the chain together, because on the
        # finished table those three are the same algebra. The version of this defect that only
        # the recount can see is exercised immediately below.
        frame.loc[frame["step"] == 16, "n_out"] -= 40
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_segment)),
                   "an analytic count that does not agree with the removals raises")

    # And the same defect seen from the other side, by the independent recount.
    bad_totals = dict(_fixture_totals(good))
    bad_totals["n_neither"] = 40
    _expect_raises(LadderClosureError, lambda: reconcile_ladder(ladder, bad_totals),
                   "an episode neither eligible nor charged is caught by the recount")
    for key, value in (("n_eligible_and_charged", 3), ("n_charged_off_ladder", 2),
                       ("n_exclusion_rows", _FIXTURE_EPISODES - 20),
                       ("n_eligible", ladder["analytic"] + 20),
                       ("n_charged", ladder["episode drops"] - 20)):
        broken_totals = dict(_fixture_totals(good))
        broken_totals[key] = value
        _expect_raises(LadderClosureError,
                       lambda t=broken_totals: reconcile_ladder(ladder, t),
                       f"a recount disagreeing on one count raises")

    # Vocabulary, null discipline and the reason column.
    for column, step, value, why in (
        ("kind", 4, "terminal", "a rung recorded under the wrong kind raises"),
        ("unit", 4, "events", "a rung recorded in the wrong unit raises"),
        ("slug", 11, "excl_no_fitbit", "a renamed rung raises"),
        ("reason", 4, "excl_prior_operation_90_days",
         "a reason that is not the rung's own slug raises"),
        ("reason", 2, "episode_construction",
         "a conversion rung carrying a slug instead of the unit-change marker raises"),
        ("reason", 16, "analytic_cohort",
         "a terminal rung carrying a slug instead of the empty string raises"),
        ("junction_map", 8, "mirrored", "a ladder mixing two junction maps raises"),
    ):
        _expect_raises(
            LadderClosureError,
            lambda c=column, s=step, v=value: assert_ladder(
                _broken(lambda f: f.__setitem__(
                    c, [v if int(row) == s else old
                        for row, old in zip(f["step"], f[c])]))),
            why)

    def break_null_drop(frame: pd.DataFrame) -> None:
        frame.loc[frame["step"] == 17, "n_dropped"] = 0
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_null_drop)),
                   "a rung that should carry no removal but carries a zero raises, because a "
                   "zero and an absent removal are different claims")

    def break_null_carried(frame: pd.DataFrame) -> None:
        frame.loc[frame["step"] == 5, "n_carried_forward"] = 10
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_null_carried)),
                   "a carried-forward count on a rung that is not the first conversion raises")

    def break_negative(frame: pd.DataFrame) -> None:
        frame.loc[frame["step"] == 6, "n_dropped"] = -20
        frame.loc[frame["step"] == 6, "n_out"] = int(frame.loc[frame["step"] == 6, "n_in"].iloc[0]) + 20
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_negative)),
                   "a negative removal raises, because it is a defect upstream")

    def break_fraction(frame: pd.DataFrame) -> None:
        frame["n_out"] = frame["n_out"].astype(float)
        frame.loc[frame["step"] == 6, "n_out"] = 120.5
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_fraction)),
                   "a fractional count raises: every count in the derived dataset is exact")

    def break_closure_flag(frame: pd.DataFrame) -> None:
        frame.loc[frame["step"] == 12, "closes_exact"] = False
    _expect_raises(LadderClosureError, lambda: assert_ladder(_broken(break_closure_flag)),
                   "a false closure flag raises, because the procedure raises on it first")

    _expect_raises(LadderClosureError,
                   lambda: assert_ladder(good.drop(columns=["n_carried_forward"])),
                   "a ladder missing a contract column raises")
    _expect_raises(LadderClosureError,
                   lambda: assert_ladder(good, junction_map="mirrored"),
                   "reading one map's ladder while calling another raises")

    # ---- 10. the collapse ladder, which is prespecified ---------------------------------
    four = {"cervical_decompression": 80, "cervical_fusion": 60,
            "lumbar_decompression": 200, "lumbar_fusion": 180}
    _expect(collapse_level(four, analytic=520)["level"] == "four_group",
            "four disclosable cells select the four-group level")
    thin = dict(four, cervical_fusion=18)
    _expect(collapse_level(thin, analytic=478)["level"] == "two_group",
            "one cell below the floor collapses to two groups while both arms clear it")
    _expect(collapse_level(thin, analytic=478)["groups"] == ("fusion", "decompression"),
            "and the two-group level names the two arm slugs")
    one_arm = {"cervical_decompression": 200, "cervical_fusion": 8,
               "lumbar_decompression": 300, "lumbar_fusion": 10}
    _expect(collapse_level(one_arm, analytic=518)["level"] == "single_group",
            "an arm below the floor collapses to one pooled curve with no contrast")
    # The boundary is written through the module that owns it rather than as a literal, which
    # is the same rule that keeps a bare floor out of every comparison in this project.
    _expect(collapse_level(four, analytic=MIN_CELL)["level"] == "no_estimand",
            "an analytic cohort at exactly the floor reports no estimand, because a true count "
            "at the floor is suppressed")
    _expect(collapse_level(four, analytic=MIN_CELL + 1)["level"] == "four_group",
            "and one just above it is not, which is the boundary the one arbiter draws")
    _expect({collapse_level(four, analytic=520)["level"],
             collapse_level(thin, analytic=478)["level"],
             collapse_level(one_arm, analytic=518)["level"],
             collapse_level(four, analytic=MIN_CELL)["level"]} == set(COLLAPSE_LEVELS),
            "the four triggers select the four levels the plan names, one each")

    # ---- 11. the ledgers, at the contract's exported columns ----------------------------
    _expect(LEDGER_WITHHELD_COLUMNS["ledger_wear_by_day"] == ("n_analyzable", "n_inpatient"),
            "the wear ledger's two refused columns are named rather than merely absent")
    for table, columns in LEDGER_SOURCE_COLUMNS.items():
        withheld = set(LEDGER_WITHHELD_COLUMNS[table])
        _expect(not (set(columns) & withheld),
                f"{table} reads none of the columns the contract refuses")
        _expect(set(LEDGER_COUNT_COLUMNS[table]) <= set(columns),
                f"every count column of {table} is a column it reads, so none goes untested")
        _expect(set(LEDGER_SORT_KEYS[table]) <= set(columns),
                f"{table} is read in the row order the contract fixes for its file, so what is "
                f"reviewed here is the order the export will carry")

    exclusion_text = render_exclusion_ledger(_fixture_exclusion_ledger())
    _expect(SUPPRESSION_SENTENCES["cell_below_threshold"] in exclusion_text,
            "a reason detail below the floor prints the policy sentence verbatim")
    _expect(SUPPRESSION_SENTENCES["secondary_suppression"] in exclusion_text,
            "and its partner in a two-member partition is suppressed beside it, so the first "
            "cannot be recovered by subtraction")
    _expect("Accrual window truncated by death" in exclusion_text,
            "every reason prints a sentence and never its identifier")
    _expect_raises(
        CohortError,
        lambda: render_exclusion_ledger(pd.DataFrame([
            {"step": 3, "slug": "excl_trauma_malignancy_infection",
             "reason_detail": "invented", "n_episodes": 40, "n_denominator": 100}])),
        "a reason detail with no printable sentence raises rather than printing an identifier")
    _expect_raises(
        CohortError,
        lambda: render_exclusion_ledger(_fixture_exclusion_ledger().iloc[
            lambda f: [i for i, s in enumerate(f["reason_detail"]) if s != "death"]]),
        "a declared partition that has lost a member raises, because declaring one that does "
        "not hold is a false claim")

    _expect(_apply_secondary_suppression([8, 12]) == (True, True),
            "one hidden member of a two-member partition forces the other")
    _expect(_apply_secondary_suppression([8, 12, 400]) == (True, True, False),
            "and the smallest disclosable member is the one that goes, not the largest")
    _expect(_apply_secondary_suppression([100, 200, 400]) == (False, False, False),
            "a partition with nothing to hide hides nothing")
    _expect(_apply_secondary_suppression([2, 4, 400]) == (True, True, False),
            "two already-hidden members need no third")

    wear_text = render_wear_ledger(_fixture_wear_ledger())
    _expect("analyzable" in wear_text and "inpatient" in wear_text,
            "the wear ledger states which two columns it refuses and why")
    _expect("Cervical fusion" in wear_text and "Lumbar decompression" in wear_text,
            "and prints group labels rather than group identifiers")
    _expect("dropped here by the absence rule" in wear_text,
            "a day below the floor is absent from the table and the count of them is reported")

    matched_text = render_matched_set_ledger(_fixture_matched_sets())
    _expect("Controls in the set" in matched_text, "the matched-set ledger prints its rows")
    _expect("matched sets, one case each" in matched_text,
            "and prints its own denominator")
    _expect("no early-warning analysis" in render_matched_set_ledger(
        pd.DataFrame(columns=["set_size", "n_sets", "n_cases"])),
        "an empty matched-set ledger says so, because present and empty is a claim")

    missing_text = render_missingness_ledger(_fixture_missingness())
    _expect("Preoperative baseline steps per day" in missing_text,
            "the missingness ledger prints variable labels rather than identifiers")
    _expect("Rows in its own population" in missing_text,
            "and prints the denominator of each row's own population")
    _expect(_complement_guarded(4, 260) == SUPPRESSION_SENTENCES["cell_below_threshold"],
            "a missing count below the floor is suppressed for its own size")
    _expect(_complement_guarded(256, 260) == SUPPRESSION_SENTENCES["secondary_suppression"],
            "and one whose COMPLEMENT is below the floor is suppressed to protect it")
    _expect(_complement_guarded(60, 260) == n_pct(60, 260) == "60 (23%)",
            "an ordinary cell prints its count and its share of the rounded denominator")
    # THE LOCAL WRAPPER IS GONE.  `_count_and_share` existed only because `n_pct` used to write
    # its numerator with no thousands separator, so this module re-rendered it.  `n_pct` now
    # goes through `disclosure.render_count` and the wrapper was an identity function; the cell
    # is `n_pct`'s directly, and these three assertions hold `n_pct` to what the wrapper used to
    # promise rather than deleting the promise along with the code.
    _expect(_complement_guarded(1500, 1500) == "1,500 (100%)",
            "a four-digit count carries the house thousands separator, from n_pct itself")
    _expect(n_pct(1500, 1500) == f"{render_count(round20(1500))} (100%)",
            "which is render_count's separator and not a second implementation of it")
    _expect(is_suppressed(n_pct(8, 1500)),
            "and a numerator below the floor takes the percentage down with it")
    _expect(_disclosed(1500) == render_count(1500) == "1,500",
            "and the one place this module rounds renders through render_count too")

    # ---- 12. disclosure at the boundary, and the two predicates -------------------------
    _expect(disclosable(0) and not disclosable(20) and disclosable(21),
            "the arbiter suppresses a true 20 and discloses a true 21")
    _expect(is_legal_disclosed_count(20),
            "and a RENDERED 20 is legal, because it is what a true 21 to 29 rounds to. The two "
            "predicates disagree on 20 by design and are never substituted for one another")
    _expect(_disclosed(0) == "0", "a true zero is an absence and prints as itself")
    _expect(_disclosed(25) == "20", "a true 25 rounds down to the nearest 20")
    _expect(_disclosed(30) == "40" and _disclosed(50) == "60",
            "and a tie rounds away from zero, which is the rule the Methods can defend")
    _expect(_suppressed_or(8) == SUPPRESSION_SENTENCES["cell_below_threshold"],
            "a count below the floor prints the policy sentence and never a number")
    _expect(_suppressed_or(_FIXTURE_EPISODES) == "11,000",
            "and a disclosable one prints with the house thousands separator")

    # ---- 13. the rendered report, and the house prose rules ------------------------------
    ladder_text = render_ladder(good, ladder)
    closure_text = render_closure(ladder, reconciliation)
    collapse = collapse_level(four, analytic=ladder["analytic"])
    stop_text = render_hard_stop(ladder, collapse)
    report = "\n".join([ladder_text, closure_text, exclusion_text, wear_text, matched_text,
                        missing_text, stop_text])
    assert_house_prose(report)
    _expect(EM_DASH not in report and MINUS_SIGN not in report,
            "the rendered report carries no banned character")
    _expect(not _SNAKE_TOKEN.findall(report),
            "and no identifier reaches a user-visible string anywhere in it")
    # Compared on normalized whitespace, because both sentences are wrapped to the terminal
    # width when they are printed and a line break is not a paraphrase.
    def _flat(text: str) -> str:
        return " ".join(text.split())

    _expect(_flat(ROUNDING_FOOTNOTE) in _flat(ladder_text),
            "the ladder publishes the rounding footnote verbatim rather than adjusting a box")
    _expect(_flat(DISCLOSURE_SENTENCE) in _flat(stop_text),
            "and the hard stop carries the disclosure sentence, worded as the Methods words it")
    _expect("400,000" in ladder_text and "11,000" in ladder_text,
            "the ladder prints rounded counts")
    _expect("Analytic cohort" in ladder_text,
            "and prints the ladder box that names the survivors")
    _expect("nineteen" in closure_text,
            "the closure section says how many rungs were asserted")
    _expect("true by construction on eighteen of the nineteen rungs" in _flat(closure_text),
            "and says plainly what the closure column does not prove")
    _expect("Checks that can fail on a correct build" in closure_text
            and "Checks of transport only" in closure_text,
            "and reports the two kinds separately rather than as one assertion count")
    _expect("Four groups" in stop_text,
            "the hard stop names the collapse level in words")

    # The cost table is the ONE surface that prints machine names, under a per-token exemption
    # rather than outside the guard.  Both halves of that are tested.
    cost_text = render_cost_plan(plan)
    assert_house_prose(cost_text, allow=STAGE_ORDER)
    _expect("hr_daily" in cost_text,
            "the cost table prints stage names, because they are the resume vocabulary")
    _expect_raises(CohortError, lambda: assert_house_prose(cost_text),
                   "and the same text fails the guard without the explicit exemption")
    _expect_raises(CohortError, lambda: assert_house_prose("a", allow=("not_a_stage",)),
                   "the exemption refuses anything that is not a stage name")
    _expect_raises(CohortError, lambda: assert_house_prose("a" + EM_DASH + "b"),
                   "an em-dash in a rendered string is a stop condition")
    _expect_raises(CohortError, lambda: assert_house_prose("see first_fail_step"),
                   "and so is an identifier")
    _expect("PER CHILD JOB" in cost_text,
            "the cost table says where the cap is enforced, in the one place it matters")
    _expect("Worst case that cap allows" in cost_text
            and "Worst case a total-sized cap would allow" in cost_text,
            "and prints both worst cases, so the saving from sizing on the binding stage is a "
            "number rather than an argument")

    # ---- 14. the driver, end to end, against a fake runtime ------------------------------
    executed: list[tuple[str, float]] = []
    frames = {
        "attrition ladder, 19 rungs": good,
        "ladder reconciliation against the exclusions table": pd.DataFrame([_fixture_totals(good)]),
        "ledger ledger_exclusion_reasons": _fixture_exclusion_ledger(),
        "ledger ledger_wear_by_day": _fixture_wear_ledger(),
        "ledger ledger_matched_sets": _fixture_matched_sets(),
        "ledger ledger_variable_missingness": _fixture_missingness(),
        "procedure group counts": pd.DataFrame(
            [{"group_slug": slug, "n_episodes": count} for slug, count in four.items()]),
    }

    def fake_query(sql: str, *, max_gb: float, note: str = "") -> pd.DataFrame:
        executed.append((note, max_gb))
        if note in frames:
            return frames[note]
        if note.startswith("build_all"):
            return pd.DataFrame()
        raise AssertionError(f"the fake runtime was handed a query it does not know: {note!r}")

    result = run_cohort(hr_minute_column="minute_in_zone", device_model_column="model_name",
                        ed_visit_concept_ids=(9203, 262),
                        inpatient_visit_concept_ids=(9201, 262),
                        q_guarded=fake_query, dry_run_gb=fake_price, show_report=False)
    _expect(result["called"], "the driver calls the procedure when it is told to")
    _expect(executed[0][0].startswith("build_all"), "and the call is the first thing executed")
    _expect(abs(executed[0][1] - plan["call cap gb"]) < 1e-9,
            "under the cap sized on the binding stage, not on the DAG total")
    _expect(result["collapse"]["level"] == "four_group",
            "and it reports the prespecified collapse level for these counts")
    _expect(result["ladder"]["analytic"] == ladder["analytic"],
            "and returns the asserted ladder")
    assert_house_prose(result["report"])

    before = len(executed)
    priced_only = run_cohort(hr_minute_column="minute_in_zone",
                             ed_visit_concept_ids=(9203,), inpatient_visit_concept_ids=(9201,),
                             call=False, q_guarded=fake_query, dry_run_gb=fake_price,
                             show_report=False)
    _expect(len(executed) == before,
            "PRICED ONLY EXECUTES NOTHING AT ALL, which is what makes it safe to run first")
    _expect(not priced_only["called"] and priced_only["ladder"] is None,
            "and it returns no ladder, because there is nothing to assert")

    _expect_raises(CohortError,
                   lambda: run_cohort(hr_minute_column="minute_in_zone",
                                      ed_visit_concept_ids=(9203,),
                                      inpatient_visit_concept_ids=(9201,),
                                      q_guarded=None, dry_run_gb=None, show_report=False),
                   "with no configured query path the step refuses rather than finding its own")

    # A broken ladder reaches the driver as a halt, not as a report.
    frames["attrition ladder, 19 rungs"] = _broken(break_segment)
    _expect_raises(LadderClosureError,
                   lambda: run_cohort(hr_minute_column="minute_in_zone",
                                      ed_visit_concept_ids=(9203,),
                                      inpatient_visit_concept_ids=(9201,),
                                      q_guarded=fake_query, dry_run_gb=fake_price,
                                      show_report=False),
                   "a ladder that does not close halts the driver rather than being reported")
    frames["attrition ladder, 19 rungs"] = good

    print(_RULE)
    print("03_cohort.py SELF-TEST: PASS")
    print(_RULE)
    print(f"  assertions executed        : {_ASSERTIONS}")
    print(f"  stages found in the DAG    : {len(stages)}, in DAG order, matching the "
          f"{N_STAGES} this module prices")
    print(f"  format templates           : {list(templated)}, each declaring its arguments and "
          f"each substituted before its dry run")
    print(f"  false positives avoided    : {list(static_percent)} carry a substitution marker "
          f"in static SQL")
    print( "                               and declare nothing, which is why the test keys on")
    print( "                               the dynamic-statement marker and not on the percent")
    print(f"  ladder rungs asserted      : {len(ATTRITION_RUNGS)}, slugs set-equal to the plan "
          f"and in order")
    print(f"  ladder checks that can fail on a correct build : {checks.independent}")
    print(f"  ladder checks of transport only               : {checks.transport}")
    print(f"  independent recount checks : {reconciliation['checks'].independent}, all of them "
          f"independent")
    print( "  closure column             : asserted AND qualified. It is true by construction")
    print( "                               on eighteen of nineteen rungs, so nothing here reads")
    print( "                               it as nineteen checks")
    print(f"  cap sent with the call     : sized on the binding stage "
          f"({plan['binding stage']}), never on the DAG total,")
    print( "                               because a script applies it to each child job")
    print(f"  ledger columns refused     : "
          f"{list(LEDGER_WITHHELD_COLUMNS['ledger_wear_by_day'])}, and the refusal is load")
    print( "                               bearing rather than an omission")
    print( "  cloud access required      : none")


# The entry point is the command line, because this module HAS one and its exit codes are the
# contract a shell script reads: 0 reviewed and stopped, 1 a stop condition fired, 2 no
# configuration, 64 usage. Dispatching straight to the self-test here instead would make
# `--call` unreachable and would make an unconfigured run look like a pass. On a laptop the
# self-test is one flag away and needs nothing: `python3 03_cohort.py --self-test`.
if __name__ == "__main__":
    sys.exit(main())
