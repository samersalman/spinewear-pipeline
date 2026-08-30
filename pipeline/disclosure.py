#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""disclosure.py -- the single gate every count passes through before a human sees it.

WHERE THIS RUNS.  Both sides of the boundary, identically.  INSIDE the perimeter it is
imported by `00_config.ipynb` and by every numbered pipeline step, and it is what makes a
printed cell or an exported CSV legal to look at while a model can see the screen.  LOCALLY it
is imported by `local/tables.py`, `local/figures.py` and `local/verify.py`, so one
implementation of the suppression rule is applied on both sides instead of two that can drift.
It holds no data, opens no BigQuery client and touches no network, which is why it is the only
module in `pipeline/` that is fully unit-testable on a laptop with no Workbench session.

WHAT IT ENFORCES (AOS-CS.md section 9; the plan's verification item 5; EXPORT-CONTRACT.md 10).
  * TWO PREDICATES, BECAUSE THERE ARE TWO QUESTIONS.  Collapsing them into one is the defect
    this pair was split apart to fix, so ask the one that matches the number in your hand:

      - `disclosable(n)` asks "may this TRUE count, before any rounding, be disclosed at all?"
        A true zero may.  A count of 1 through 20 inclusive may not.  A count strictly greater
        than 20 may, and is then rounded to the nearest multiple of 20 before anyone sees it.
        This is the ONE arbiter of the floor: `round20`, `mean_sd` and `median_iqr` all ask it
        rather than writing their own comparison.  Ask it BEFORE `round20`, never after.
      - `is_legal_disclosed_count(cell)` asks "is this ALREADY-RENDERED cell a legal disclosed
        output?"  The suppression sentinel is one, a true zero is one, and a whole number that
        is a positive multiple of the rounding base is one.  Nothing else is.  This is what the
        export gate asks, because by the time a frame reaches `safe_export` every count in it
        has been through `round20` and the gate is holding rendered cells, not true counts.
        Ask it AFTER `round20`, never before.

    THE TWO DISAGREE ON 20, and the disagreement is the whole point.  `disclosable(20)` is
    False, because a true count of 20 is below the floor.  `is_legal_disclosed_count(20)` is
    True, because a rendered 20 is what `round20` returns for a true count of 21 to 29.  Asking
    `disclosable` of a rendered cell therefore refuses every correctly rounded 20 in the bundle,
    which is exactly what it did until this split, and which blocked the STROBE ladder and
    Table 1 from exporting at all.
  * TWO SUPPRESSION PREDICATES, FOR THE SAME REASON: a suppressed cell has three sanctioned
    spellings and only one of them is this module's own.

      - `is_suppressed(cell)` asks "is this THIS MODULE'S sentinel?", by containment.  It is
        the right question inside the perimeter, where `round20` put the sentinel there.
      - `is_bundle_suppressed(cell)` asks "is this cell hidden, in ANY representation the
        contract sanctions?": the sentinel, the bare token `SUPPRESSED` that section 4 fixes
        for a figure CSV, or one of the section 7.5 sentences that section 5 fixes for a
        table CSV.  It is the right question at the boundary, and it is what the refusal
        classes that must SEE a hidden count in order to refuse something beside it ask:
        complementary disclosure, and secondary suppression across a partition.

    KEYED ON THE SENTINEL, THOSE TWO CLASSES WERE INERT ON EVERY FRAME THAT CROSSES THE
    BOUNDARY.  No bundle representation contains the sentinel, so a percentage beside a hidden
    count was never refused and a lone suppressed partition member was never refused.  Both
    classes exist to stop a hidden count being recovered by arithmetic; being inert on the real
    bundle was the whole failure.  The recognised set is CLOSED and NAMED in
    `SUPPRESSION_REASONS`, matched by equality, so nothing becomes suppressed by looking like
    prose about suppression, and the empty string means NOT APPLICABLE and never means
    suppressed.
  * THE MANIFEST FIELD IS A THIRD QUESTION AND HAS ITS OWN PREDICATE.  `n_suppressed_cells` is
    not "how many cells are hidden", it is EXPORT-CONTRACT.md 8.3's "cells written as
    `SUPPRESSED`, or as a suppression sentence IN A TABLE CSV", which section 4.4 restates as
    counting "written tokens and not reasons".  A figure CSV writes the 7.5 sentence in a
    display column as prose about a row whose token is already counted, so asking
    `is_bundle_suppressed` there counted one hidden cell twice and Figure 4 stamped 220 where
    the contract states 176.  `_is_manifest_suppressed_cell` is the field's predicate; it keeps
    the token and sentinel clauses on every kind and restricts the sentence clause to
    `table-csv`, and it carries the argument for keying that on `kind`.
  * THE DISPLAY CONVENTION FOR A ROUNDED 20, which the Methods footnote carries verbatim so the
    footnote and this module cannot drift apart:  "Counts of 20 or fewer are suppressed; larger
    counts are rounded to the nearest 20, so a disclosed 20 represents a true count of 21 to
    29."  A displayed 20 stands on a true count of 21 to 29.  It never stands on 20, which is
    suppressed, and never on 30, which rounds up to 40.
  * A percentage is suppressed whenever its numerator is suppressed, and when it is shown it is
    computed from the ROUNDED numerator over the ROUNDED denominator at zero decimals, so a
    reader can reproduce every printed percentage from the printed counts and from nothing else.
  * A continuous summary needs more than 20 contributing observations.  So does a median, for a
    reason the floor does not remove: at odd n the median IS one participant's own value.  What
    the floor buys is the size of the set that value could have come from, and an anonymity set
    of more than 20 is the whole of what makes an individual value publishable.
  * An export refuses a non-tabular extension, small cells, identifier-like columns, date-like
    columns, near-unique columns, a disclosed percentage standing beside a suppressed count, a
    partition with exactly one suppressed member, and the two banned dash characters.  It then
    returns the `MANIFEST.csv` row for the file it wrote, md5 included, so a transcription slip
    is caught at the boundary rather than in a manuscript.
  * THE ONE EXEMPTION, and it is narrow on purpose.  `specification_columns` lets the author
    name a column, ONE COLUMN AT A TIME, whose values come from a public vocabulary or are
    fixed by the protocol rather than derived from participants; a named column is exempt from
    the near-unique and identifier-like classes and from NOTHING else, not even the date class.
    It exists because the concept-set registry of EXPORT-CONTRACT.md 5.6 is one row per locked
    CPT-4 code or ICD-10-PCS stem, so `code` is distinct in every row by construction and the
    near-unique class refuses the whole file for being what the contract asks it to be.  There
    is deliberately no file-level and no `kind`-level form of it.  See `export_violations`.

DISPLAY OR DATA, AND WHICH SIDE THE THOUSANDS SEPARATOR REACHES.  Every count this module
emits lands on exactly one of two surfaces, the separator crosses onto one of them only, and
the distinction is written down here because it is exactly the sort that erodes.

  * A DISPLAY surface is a string rendered FOR A HUMAN TO READ: a printed line, a rendered
    table cell, a sentence of prose.  `render_count` writes onto it, `n_pct` and `prev` write
    onto it through `render_count`, and `safe_show` prints onto it.  A count on a display
    surface carries the house thousands separator -- `n = 1,240`, the numeral style CLAUDE.md
    states -- because four- and five-digit counts are the ORDINARY case here, in the
    exclusion-reason ledger and in the person-day row of the missingness ledger, and the
    analytic cohort itself is four digits.  Not an edge case, so not an edge-case rule.
  * A DATA surface is a VALUE emitted for something else to compute on: the integer `round20`
    returns, the integer or sentinel from `safe_n`, the cells of `safe_counts` and
    `suppress_frame`, and every byte `safe_export` writes.  A count on a data surface is a
    BARE NUMBER and never carries a separator.  A separator in an exported CSV cell is a data
    corruption and not a style improvement: it makes the number unparseable to everything that
    reads the file back, and inside an unquoted field it invents a column.

  THE TWO NEVER MEET, and that is a property of the code rather than a convention.
  `safe_export` renders no count of its own -- it writes the frame it is handed, through
  `_integers_as_integers`, `FLOAT_FORMAT`, `index=False` and a pinned line terminator -- and
  nothing on the display side is reachable from it, so the md5 discipline is untouched and two
  runs still produce byte-identical files.  A frame on its way to the boundary is built from
  `round20` and `suppress_frame`, never from `n_pct` or `prev`.  A `table-csv` frame is
  rendered display strings by the kind rule of `export_violations`, and may carry a separated
  count in a rendered cell; a column DECLARED in `count_cols` stays numeric on either kind,
  because that is the column the floor check parses.

  RENDERED COUNTS ARE ONE-WAY.  Nothing in this bundle reads a string back out of
  `render_count`, `n_pct` or `prev` as a number.  The two predicates that do parse are asked
  of EXPORT CELLS, which are numbers or the sentinel, and neither is weakened by the
  separator: `is_suppressed` matches the sentinel, which carries no digits to separate, and
  `is_legal_disclosed_count` refuses "1,240" outright rather than parsing it -- the correct
  answer, because a rendered string is not a legal export cell whatever number it renders.
  Tests pin both.

  A PERCENTAGE IS NOT SEPARATED, and needs no rule of its own.  It is a part over its own
  whole at zero decimals, so it is three digits at the widest and there is nothing in it to
  separate.  The arithmetic below is untouched by any of this: `_percent` still divides the
  ROUNDED INTEGER numerator by the ROUNDED denominator, never a rendered string.

  A MEAN, AN SD, A MEDIAN AND A QUARTILE ARE NOT COUNTS, so `mean_sd` and `median_iqr` are
  deliberately outside this rule rather than overlooked by it.  They answer "how much", carry
  decimals, and can be negative (a deficit below baseline); the separator is for the integer
  answer to "how many".

PORTED FROM, with two deliberate divergences marked `DIVERGENCE` in the body:
  * `cyp2d6-spine-opioid-analysis/analysis/disclosure.py` -- round20, n_pct, mean_sd.
  * `GWAS/_transfer/pivot_common.py` -- prev, safe_show, safe_n, safe_counts, and the
    complementary-disclosure rule that a suppressed count must suppress its percentage.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import math
import re
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd


__all__ = [
    # policy constants
    "MIN_CELL",
    "ROUND_BASE",
    "SUPPRESSED",
    "NEAR_UNIQUE_RATIO",
    "NEAR_UNIQUE_MIN_ROWS",
    "FLOAT_FORMAT",
    "EM_DASH",
    "MINUS_SIGN",
    "BANNED_CHARACTERS",
    "ALLOWED_EXPORT_SUFFIXES",
    "MANIFEST_COLUMNS",
    "MANIFEST_KINDS",
    # the suppression vocabulary (EXPORT-CONTRACT.md 4, 5 and 7.5)
    "FIGURE_SUPPRESSED_TOKEN",
    "SUPPRESSION_REASONS",
    "SUPPRESSION_SENTENCES",
    "assert_suppression_vocabulary",
    # the arbiter and the error type
    "DisclosureError",
    "disclosable",
    "is_legal_disclosed_count",
    # scalars
    "round20",
    "is_suppressed",
    "is_bundle_suppressed",
    "render_count",
    "n_pct",
    "prev",
    "mean_sd",
    "median_iqr",
    # frames
    "safe_show",
    "safe_n",
    "safe_counts",
    "suppress_frame",
    # the boundary
    "export_violations",
    "md5_of_bytes",
    "safe_export",
]


# --------------------------------------------------------------------------------------
# Policy constants.  Every disclosure FLOOR and every RATIO in this module is one of these
# names, and none of them is written as a literal inside a comparison anywhere in this file,
# which is what `verify.py` greps `pipeline/` and `local/` for.  The `1` in the secondary-
# suppression rule below is not a floor: it is the arity the rule is about, "exactly one
# suppressed member of a partition is recoverable by subtraction".
# --------------------------------------------------------------------------------------

MIN_CELL: int = 20
SUPPRESSED: str = "<=20 (suppressed)"

# The rounding base and the suppression floor coincide at 20 by policy, not by coincidence:
# the Methods sentence is "counts of 20 or fewer are suppressed and larger counts are rounded
# to the nearest 20", and two different numbers there would need two sentences and invite the
# question of why they differ.
ROUND_BASE: int = MIN_CELL

# A column is near-unique when MORE THAN this fraction of its rows carry a distinct value.
# 0.90 rather than 1.00 because it is near-uniqueness, not perfect uniqueness, that enables
# linkage: a column distinct for 95 percent of rows singles out 95 percent of rows, and the
# handful of ties protect nobody.  The comparison is strict, so a column that is distinct in
# exactly 90 percent of its rows clears.
NEAR_UNIQUE_RATIO: float = 0.90

# ... but only on a frame with more than this many rows.  Below the floor the ratio carries no
# information: a 4-row summary table with 4 region labels is 100 percent distinct and obviously
# safe.  The floor is set to MIN_CELL so the Methods has one number in it, not two.
NEAR_UNIQUE_MIN_ROWS: int = MIN_CELL

# Fixed float rendering so the md5 of an export is reproducible across runs, pandas versions
# and platforms.
# DECIDED, deliberately, against the `%.6f` that EXPORT-CONTRACT.md carried: both formats are
# equally deterministic, so the md5 discipline is satisfied by either, but `%.6f` silently
# flattens any value below 1e-6 to `0.000000` and `%.6g` does not.  A plot-ready series carries
# both baseline fractions near 1.0 and tail probabilities near 1e-9, and a P value that prints
# as zero is a correctness failure, not a formatting preference.  The contract is being
# corrected to match this line; this line is not to be changed to match the contract.
FLOAT_FORMAT: str = "%.6g"

# Named, never typed, so the byte never enters this source file.  U+2014 is the em-dash the
# house prose rules ban outright; U+2212 is the Unicode minus, which reads as a dash in every
# proportional font and which EXPORT-CONTRACT.md section 2.2 bans alongside it.
EM_DASH: str = chr(0x2014)
MINUS_SIGN: str = chr(0x2212)
BANNED_CHARACTERS: tuple[str, ...] = (EM_DASH, MINUS_SIGN)

# R2: the perimeter exports the plotted SERIES, never the plot.  Any other extension is a
# binary or an image, and neither can be read by a human at the boundary before it leaves.
ALLOWED_EXPORT_SUFFIXES: tuple[str, ...] = (".csv", ".json", ".md5")

# EXPORT-CONTRACT.md section 8.3, in order.  `safe_export` returns exactly these keys.
MANIFEST_COLUMNS: tuple[str, ...] = (
    "file",
    "kind",
    "exhibit",
    "md5",
    "n_rows",
    "n_columns",
    "min_disclosed_count",
    "n_suppressed_cells",
    "description",
)

# EXPORT-CONTRACT.md section 8.3 again: the three values `kind` may take.
MANIFEST_KINDS: tuple[str, ...] = ("results-json", "figure-csv", "table-csv")


# --------------------------------------------------------------------------------------
# THE SUPPRESSION VOCABULARY.  A suppressed cell does not have one spelling, it has three, and
# only ONE of them is this module's own.  `SUPPRESSED` above is what `round20` returns and what
# a printed frame inside the perimeter carries; the two below are what the same cell is written
# as once it reaches the bundle, and neither of them contains the sentinel:
#
#   * EXPORT-CONTRACT.md section 4, shared rules for `figures-csv/`: "Suppressed cell -- the
#     literal token `SUPPRESSED`.  Never blank, never `0`, never `NA`."
#   * EXPORT-CONTRACT.md section 5, shared rules for `tables-csv/`: "Suppressed cell -- the
#     suppression sentence itself, verbatim from 7.5, never a token."
#
# Naming them here is what makes `is_bundle_suppressed` a CLOSED set rather than a widened
# regex.  A cell is suppressed because it matches a representation this module knows about,
# never because it reads like prose about suppression: "the count was suppressed" written by
# hand into a free-text column is a free-text cell, and treating it as a suppression marker
# would let an author switch off the complementary-disclosure class with a sentence.
# --------------------------------------------------------------------------------------

# EXPORT-CONTRACT.md section 4.  The bare word, upper case, exact.  It is NOT `SUPPRESSED` the
# constant above -- that one is the string `"<=20 (suppressed)"` -- and the collision of names
# is the contract's, not this module's.
FIGURE_SUPPRESSED_TOKEN: str = "SUPPRESSED"

# EXPORT-CONTRACT.md section 7.5, the whole table, slug to display sentence, in the contract's
# own row order.  It is transcribed rather than parsed because this module imports nothing and
# reads nothing at import time -- it runs inside the Workbench VM where the prespecification
# directory is not uploaded -- so the copy has to be checked rather than derived.
#
# WHAT HAPPENS WHEN THE CONTRACT ADDS A SENTENCE, stated here because the failure mode of
# a transcribed table is that it silently stops recognising a cell:
#   * `tests/test_disclosure.py::test_the_suppression_sentences_are_the_contract_s_own` reads
#     section 7.5 out of `prespecification/EXPORT-CONTRACT.md` and asserts this tuple equals it,
#     slug for slug and sentence for sentence.  A row added to the contract turns the suite red
#     on the next run, which is the loud failure.
#   * `assert_suppression_vocabulary()` below is the runtime half of the same check, for a
#     caller that keeps its own copy of 7.5 (`07_export.LABELS` does).  A caller that calls it
#     at import time cannot get out of step with this module without raising.
# Neither is optional politeness.  Without them a new sentence is a suppressed cell that
# `is_bundle_suppressed` returns False for, which is precisely the defect this block fixes.
SUPPRESSION_REASONS: tuple[tuple[str, str], ...] = (
    ("cell_below_threshold", "20 or fewer, suppressed per All of Us dissemination policy"),
    ("numerator_suppressed", "suppressed because the count behind it is suppressed"),
    ("contributing_n_below_threshold", "20 or fewer contributors, suppressed"),
    ("secondary_suppression", "suppressed to protect a suppressed cell in the same total"),
    ("not_estimable_cell_size", "not estimable (cell size)"),
    ("not_estimable_convergence", "not estimable (model did not converge)"),
    ("not_estimable_data_unavailable", "not estimable (data not available)"),
    ("not_permitted_by_tier", "not permitted at the feasibility tier reached"),
    # Ninth as of contract 1.6.0.  It exists because a contrast that never crosses zero out to
    # the extended delta grid is the STRONGER result, and it was previously emitted as
    # `not_estimable_data_unavailable`, which labelled a good finding as a missing one.
    ("no_crossing_within_range", "no crossing within the prespecified range"),
    # TENTH.  `ANALYSIS-PLAN.md` reached version 1.5 and its section 4.9 prespecifies a
    # coefficient ceiling for every logistic fit in Arm A; a fit above it is refused, and the
    # refusal prints this sentence.  The plan names the slug and says in as many words that it
    # "belongs to the suppression-reason vocabulary of EXPORT-CONTRACT.md section 7.5 ... and it
    # is added there in the same commit", so the pair below is TRANSCRIBED and not composed
    # here.  `06_analysis_gate.py` already emits it.
    #
    # NO EXISTING REASON COULD HAVE CARRIED IT, which is why the table grows rather than reuses.
    # A quasi-separated conditional fit CONVERGES: the cell size was fine, the data were
    # available, and the tier permitted the analysis, so `not_estimable_cell_size`,
    # `not_estimable_data_unavailable` and `not_permitted_by_tier` are each simply false of it,
    # and `not_estimable_convergence` -- the near-miss a reader would expect to be reused -- is
    # the falsest of the four, because convergence is exactly the property that makes
    # quasi-separation dangerous instead of visible.
    #
    # ROW POSITION.  The contract owns the order and this module transcribes it.  It is placed
    # last because EXPORT-CONTRACT.md 11.4 calls for "a tenth row in 7.5" and because the ninth
    # was appended the same way.  If 7.5 lands it elsewhere, the ordered-pair checks in
    # `tests/test_disclosure.py` and in `03_cohort.py` fail and name the first divergence; that
    # is the check working, and the fix is to move this row, never to relax the check.
    ("not_estimable_separation", "not estimable (separation)"),
)

# The sentences alone, for the membership test.  A frozenset because the test is EQUALITY on a
# whole cell and never containment: containment on "not estimable (cell size)" would be
# harmless, but containment on the shorter sentences would make any prose that quotes one into
# a suppression marker, and the set has to behave the same way for every member of it.
SUPPRESSION_SENTENCES: frozenset[str] = frozenset(
    sentence for _, sentence in SUPPRESSION_REASONS
)


class DisclosureError(ValueError):
    """Raised when a value or a frame would carry data below the disclosure floor.

    A ValueError subclass so an existing `except ValueError` still catches it, and a distinct
    type so a caller can tell a policy refusal from an ordinary bad argument.
    """


# --------------------------------------------------------------------------------------
# The two predicates.  `disclosable` answers a question about a TRUE count and is the arbiter
# of the floor; `is_legal_disclosed_count` answers a question about an ALREADY-RENDERED cell
# and is what the export gate asks.  They are adjacent so that a reader reaching for one is
# made to see the other, and they disagree on 20 by design.  See the module docstring.
# --------------------------------------------------------------------------------------


def disclosable(n: Any) -> bool:
    """True when a TRUE count, before any rounding, may be disclosed at all.

    THE SINGLE ARBITER OF THE FLOOR (EXPORT-CONTRACT.md lines 27 to 43).  `ANALYSIS-PLAN.md`
    section 8 rule 1 reads "counts 1 to 20 are suppressed", which puts a count of exactly 20
    below the line; `AOS-CS.md` section 9 reads "counts at or above 20", which puts it above.
    The decided reading is the first: suppress 1 through 20 inclusive, disclose only counts
    strictly greater than 20.  This function exists so that reading lives in one place: no
    module in this bundle writes `n >= 20`, `n > 20` or `n < 20`, and `verify.py` greps for a
    bare floor literal in a comparison and fails on a hit.

    A true zero is disclosable and is never suppressed.  Zero is an absence, not a small cell:
    there is no one to re-identify, "<=20" would tell the reader strictly less than "0" does,
    and the attrition ladder stops closing the moment a legitimate zero drop turns into a
    string that cannot be subtracted.

    Everything that is not a finite whole number is NOT disclosable, and that is deliberate
    rather than defensive.  A negative count is a bug upstream.  A fractional cell in a count
    column is a mean or a rate that has been filed under the wrong header, and it carries more
    precision than any rounded count is allowed to.  Both would otherwise slip past a
    comparison written as `1 <= n <= 20`, which is how they slipped past this module before.
    """
    try:
        count = float(n)
    except (TypeError, ValueError, OverflowError):
        # A label, a NaN sentinel, a None, an already-suppressed string.  Not a count, so not a
        # count that may be disclosed.  Callers that must pass such values through unchanged
        # (round20) test for them before asking.
        return False
    if not math.isfinite(count) or count != int(count):
        return False
    whole = int(count)
    return whole == 0 or whole > MIN_CELL


def is_legal_disclosed_count(value: Any, *, allow_zero: bool = True) -> bool:
    """True when an ALREADY-RENDERED cell is a legal disclosed count.

    THE OTHER QUESTION, AND NOT A SYNONYM FOR `disclosable`.  `disclosable(n)` asks whether a
    TRUE count may be disclosed at all and is the arbiter of the floor.  This asks whether a
    cell that has ALREADY been through `round20` is a legal thing to write down.  Two questions,
    two answers, and on the same number they differ:

        disclosable(20)               is False   -- a TRUE count of 20 is below the floor
        is_legal_disclosed_count(20)  is True    -- a RENDERED 20 is round20(21) .. round20(29)

    Collapsing them was a real defect with a real cost.  The export gate asked `disclosable` of
    the cell it was handed, and in an export that cell is already rounded, so a correctly
    rounded 20 -- which ANALYSIS-PLAN.md section 8 rule 2 and the Methods footnote carried in
    this module's docstring both bless as "a disclosed 20 represents a true count of 21 to 29"
    -- was refused by the very module that produced it, and `07_export.py` could not export the
    STROBE ladder or Table 1.

    LEGAL, and nothing else is:
      * a SUPPRESSED CELL IN ANY SANCTIONED REPRESENTATION -- the sentinel, the section 4 token,
        or a section 7.5 sentence -- because a suppressed cell is a legal rendered value and a
        disclosed table is expected to be full of them;
      * a true zero, when `allow_zero`, because a zero is an absence and not a small cell;
      * a whole number that is a positive multiple of ROUND_BASE, which is precisely the set of
        values `round20` is able to return.

    THE 7.5 SENTENCE IN A COUNT COLUMN IS ACCEPTED, DELIBERATELY, and the alternative was
    considered rather than overlooked.  EXPORT-CONTRACT.md section 5 does not merely permit that
    cell, it MANDATES it: "Suppressed cell -- the suppression sentence itself, verbatim from
    7.5, never a token", and Table 1's own worked example in 5.1 writes "20 or fewer, suppressed
    per All of Us dissemination policy" into a count column.  Refusing it would refuse Table 1.
    The narrower reading -- accept only the sentinel, refuse every bundle representation --
    would have this predicate disagree with the gate that calls it about what a suppressed cell
    is, which is the shape of the defect that split `disclosable` off from this function.
    `not_estimable_cell_size` and its three siblings are accepted on the same footing: 7.5 is
    one table, a cell carrying any row of it is a cell with no number in it, and drawing a line
    between "hidden" and "not estimable" here would put the same string on both sides of the
    floor depending on which column it landed in.

    IT DOES NOT WIDEN TO PROSE.  The set is closed and named in `SUPPRESSION_REASONS`, matched
    by equality, so an UNRECOGNISED sentence in a count column -- "not estimable", "suppressed",
    "20 or fewer" -- is not suppressed, is not a number, and is refused.  A test pins that.

    STILL STRICT, WHICH IS THE POINT OF KEEPING IT.  The refusal class this backs exists to
    catch a caller who FORGOT TO ROUND, and it still does, in fact better than the floor test
    did: a count that was never rounded is almost never an exact multiple of 20, so a raw 7 and
    a raw 21 are both refused, and a raw 21 is the common real mistake.  A whole-valued float is
    accepted because a LEFT JOIN turns an INT64 count column into float64, and
    `_integers_as_integers` casts whole-valued floats back to int64 on write.

    THE ONE RESIDUAL GAP, stated here rather than left to be discovered: a RAW count of exactly
    20 is indistinguishable from a ROUNDED 20 at this gate.  Both are the integer 20; the
    information that would separate them is the true count, and by definition the gate no longer
    has it.  So this predicate accepts a raw 20, deliberately.  That is bounded, for three
    reasons.  Every OTHER unrounded value is caught by the multiple-of-ROUND_BASE test.
    `round20` is the only sanctioned way to produce a count for export, and it never emits a raw
    20 -- it emits the sentinel for a true 20.  And the floor on the true count is enforced
    upstream, where the true count still exists: by `round20` itself, and by callers such as
    `02_pregate.render_wide` that ask `disclosable` before rounding.  The alternative, refusing
    every rounded 20 to catch the one raw one, is the cure that was worse than the disease.
    """
    # A suppressed cell is tested first, in every representation.  Each of them is a string, so
    # every numeric test below would refuse it, and a suppressed cell is the single most common
    # legal cell in a disclosed table.
    if is_bundle_suppressed(value):
        return True
    try:
        count = float(value)
    except (TypeError, ValueError, OverflowError):
        # A label, a None, a NaN sentinel, a free-text cell.  Not a count, so not a legal one.
        return False
    if not math.isfinite(count) or count != int(count):
        # A fractional cell in a count column is a mean or a rate filed under the wrong header,
        # and it carries more precision than any rounded count is allowed to.
        return False
    whole = int(count)
    if whole == 0:
        return allow_zero
    # `>= ROUND_BASE` is doing real work here and is NOT implied by the modulo test beside it:
    # Python's `%` follows the sign of the divisor, so `-20 % 20` is 0 and a negative count
    # would otherwise read as a legal multiple.  A negative count is a bug upstream.
    return whole >= ROUND_BASE and whole % ROUND_BASE == 0


# --------------------------------------------------------------------------------------
# Scalars.
# --------------------------------------------------------------------------------------


def round20(n: Any) -> Any:
    """Disclosure-round one count.  Returns int or the SUPPRESSED sentinel; else passes through.

    The floor decision is not made here.  It is made by `disclosable`, which this function
    calls, so that the sentinel and the export gate can never disagree about the same number.
    """
    try:
        count = int(n)
    except (TypeError, ValueError, OverflowError):
        # Not a number: a label, a NaN, a None, an already-suppressed sentinel.  Pass it back
        # untouched so round20 can be mapped blindly over a mixed column.
        return n
    if count < 0:
        # A negative count is a bug upstream, never a disclosure decision.  Assertions are stop
        # conditions in this project, so it raises rather than rounding toward zero in silence.
        # The value itself is NOT interpolated: this exception renders into a notebook
        # traceback, which is the model-visible surface this whole module protects, and a cell
        # value in a traceback is a disclosed cell no matter how it got there.  `suppress_frame`
        # catches this and re-raises it naming the column, which is what a caller needs anyway.
        raise DisclosureError("round20 received a negative count, which is a bug upstream")
    if count == 0:
        return 0
    if not disclosable(count):
        return SUPPRESSED
    # Half-UP, in exact integer arithmetic, deliberately NOT Python's round().  round() is
    # half-to-even, which sends 30 to 40 but 50 to 40 as well, and no Methods sentence that
    # says "rounded to the nearest multiple of 20" can explain why 50 became 40.  Integer
    # arithmetic also means no float ever enters a disclosure decision, so the result is
    # identical on every platform.
    return ((count + ROUND_BASE // 2) // ROUND_BASE) * ROUND_BASE


def is_suppressed(value: Any) -> bool:
    """True when a rendered value carries THIS MODULE'S OWN suppression sentinel.

    Containment rather than equality, so a composed string ("40 of <=20 (suppressed)") is still
    recognised as suppressed by anything downstream that gates on this.

    NARROW ON PURPOSE, AND NOT THE ONE TO ASK OF A BUNDLE CELL.  This is the sentinel test and
    only the sentinel test: it answers "did `round20` produce this cell", which is the question
    inside the perimeter, where `n_pct`, `prev`, `safe_counts` and `suppress_frame` all put the
    sentinel there themselves.  It is deliberately blind to the two representations the same
    cell is written as in the bundle.  `is_bundle_suppressed` below is the one to ask when the
    cell came off a rendered frame on its way to `safe_export`, or was read back out of an
    exported CSV.  The two are adjacent so that a reader reaching for one is made to see the
    other, exactly as `disclosable` and `is_legal_disclosed_count` are.
    """
    return isinstance(value, str) and SUPPRESSED in value


def is_bundle_suppressed(value: Any) -> bool:
    """True when a rendered cell says "hidden" in ANY representation the contract sanctions.

    THE BROAD PREDICATE, AND THE ONE THE EXPORT GATE ASKS.  `is_suppressed` recognises the
    module's own sentinel and nothing else.  That is the right question inside the perimeter
    and the wrong one at the boundary, because EXPORT-CONTRACT.md fixes a DIFFERENT spelling
    for the same cell once it reaches the bundle, and neither spelling contains the sentinel:

        is_suppressed("SUPPRESSED")                                     is False
        is_suppressed("20 or fewer, suppressed per ...")                is False
        is_bundle_suppressed(both, and the sentinel)                    is True

    Which to ask, in one line each:
      * `is_suppressed(cell)` -- the cell was produced by `round20` and has not been rendered
        for the bundle.  Printed frames, `safe_counts` output, `suppress_frame` output.
      * `is_bundle_suppressed(cell)` -- the cell is on a frame headed for `safe_export`, or was
        read back out of an exported CSV.  Every refusal class that has to see a hidden count
        in order to refuse something beside it asks THIS one: complementary disclosure and
        secondary suppression across a partition.

    IT IS NOT THE MANIFEST FIELD'S PREDICATE, and that is the one caller a reader is most
    likely to expect here.  `n_suppressed_cells` counts a NARROWER, KIND-DEPENDENT set --
    EXPORT-CONTRACT.md 8.3's "cells written as `SUPPRESSED`, or as a suppression sentence in a
    table CSV" -- because a figure CSV writes the 7.5 sentence as display prose beside a hidden
    cell rather than as one.  `_is_manifest_suppressed_cell` below is that predicate and holds
    the argument.  The refusal classes above are right to ask the broad question: a percentage
    standing beside a cell that says "not estimable (cell size)" is complementary disclosure
    whatever kind of file it is written into.

    THE RECOGNISED SET IS CLOSED AND NAMED.  Exactly three things are suppressed here, and the
    module can say where each comes from:
      1. `SUPPRESSED`, this module's sentinel, by CONTAINMENT, so `is_bundle_suppressed` never
         disagrees with `is_suppressed` on a cell `is_suppressed` accepts.  It does not appear
         in a well-formed bundle at all; it is recognised so that a sentinel that leaked into
         an export is caught by these classes rather than waved through as an ordinary string.
      2. `FIGURE_SUPPRESSED_TOKEN`, by EQUALITY.  EXPORT-CONTRACT.md section 4.
      3. A sentence in `SUPPRESSION_SENTENCES`, by EQUALITY.  EXPORT-CONTRACT.md section 7.5,
         transcribed into `SUPPRESSION_REASONS` and cross-checked against the contract by a
         test and by `assert_suppression_vocabulary`.

    Equality and not containment for 2 and 3, and no case folding, no stripping, no substring
    search.  The contract writes these cells verbatim and `safe_export` writes bytes, so a cell
    that differs by a space or a capital is a cell some other code path produced, and reading it
    as suppressed would be guessing.  More to the point, a predicate that accepted "the count is
    suppressed" would let any author silence the complementary-disclosure class by writing a
    sentence, which is the failure this whole block exists to avoid.

    THE EMPTY STRING IS NOT SUPPRESSED, ever, and this is load-bearing rather than incidental.
    Both shared-rule tables say so in the same words: section 4, "Not-applicable cell -- the
    empty string.  Distinguished from `SUPPRESSED` on purpose: blank means the concept does not
    apply to this row, `SUPPRESSED` means it applies and is hidden"; section 5, "Empty cell --
    the empty string, meaning the row does not apply to that column".  Reading a blank as hidden
    would make every not-applicable cell a partition member and force a second suppression to
    protect a count that was never there.  It falls out of the three rules above -- `""` is not
    the token, not a sentence, and contains no sentinel -- and a test pins it so it stays a
    decision rather than an accident of the implementation.
    """
    if not isinstance(value, str):
        # A number, a None, a NaN, a bool.  A hidden cell is a WRITTEN cell in every
        # representation the contract has, so nothing that is not a string can be one.
        return False
    if value == FIGURE_SUPPRESSED_TOKEN:
        return True
    if value in SUPPRESSION_SENTENCES:
        return True
    return is_suppressed(value)


def _is_manifest_suppressed_cell(value: Any, kind: str) -> bool:
    """True when a cell is one `MANIFEST.csv`'s `n_suppressed_cells` field is counting.

    NARROWER THAN `is_bundle_suppressed`, AND KIND-DEPENDENT, BECAUSE THE FIELD IS.
    EXPORT-CONTRACT.md 8.3 defines it as "cells written as `SUPPRESSED`, or as a suppression
    sentence IN A TABLE CSV", and section 4.4 says what that qualifier is doing in a sentence
    that leaves no room: the suppressed cells of `figures-csv/figure4_event_centered_activity.csv`
    at tier 4 are counted in "`n_suppressed_cells`, WHICH COUNTS WRITTEN TOKENS AND NOT REASONS".

    `is_bundle_suppressed` asks a different question -- "is this cell hidden, in any sanctioned
    representation" -- and asking it here counted a figure CSV's display prose as hidden cells.
    Figure 4 stamped 220 where the contract states 176: its 44 rows carry the token in four
    columns, which is the 176, and a 7.5 sentence in `not_plotted_display`, which is the extra
    44.  Figure 3 stamped 5 for the same reason, in `not_estimable_display`.  Neither of those
    columns holds a hidden cell.  Section 4.3 and section 4.4 give both of them `never` in their
    own Suppression column and describe both as "printed in place of the marker": they are prose
    ABOUT a row whose number is hidden somewhere else in the same row, and counting them counts
    one hidden cell twice, once as the token and once as the sentence explaining it.

    KIND, AND NOT A `*_display` COLUMN-NAME RULE.  Both fixes make Figure 3 and Figure 4 read
    right, and the choice between them is not a matter of taste:

      * THE CONTRACT'S OWN DEFINITION IS KEYED ON KIND, in the contract's own words, and 8.3
        owns this field.  No section of it states a rule about a column suffix, so a suffix rule
        would be this module inventing the definition of a field it is only implementing.
      * THE SAME STRING MEANS TWO DIFFERENT THINGS IN THE TWO KINDS, WHICH IS WHAT `kind` IS
        FOR.  Section 5 does not merely permit the 7.5 sentence in a table CSV, it MANDATES it
        -- "Suppressed cell -- the suppression sentence itself, verbatim from 7.5, never a
        token" -- so there the sentence IS the hidden cell and there is nothing else to count.
        Section 4 fixes the bare token for a figure CSV, so there the sentence is never the
        hidden cell and is always something else.  One string, two meanings, separated by
        exactly the property the manifest row already carries.
      * NAME MATCHING IS THE WRONG INSTRUMENT AND THIS MODULE ALREADY SAYS SO of the classes
        that use it: "Name matching alone is not enough in either direction."  It is not enough
        here either, in both directions.  A figure CSV that writes a sentence into a column not
        named `*_display` would still be miscounted, and a table CSV column that IS named
        `*_display` and carries a genuinely suppressed cell would be dropped out of a count the
        contract requires.  A suffix rule also silently binds this field to a naming convention
        that `07_export.py` and the contract's column tables are free to change.

    THE TOKEN CLAUSE AND THE SENTINEL CLAUSE ARE NOT RESTRICTED, on either kind, and that is
    decided rather than left over:
      * 8.3's first clause, "cells written as `SUPPRESSED`", carries no qualifier at all.  A
        table CSV may not write the token -- section 5 says "never a token" -- but a token
        written into one is still a written suppression token, and declining to count it would
        understate a file that is already breaking section 5 rather than report it.
      * The module's own sentinel appears in no well-formed bundle cell in either kind; it is
        recognised so that a sentinel which LEAKED into an export is counted rather than waved
        through as an ordinary string.  Restricting it by kind would make a leak invisible on
        exactly the kind where no other clause would see it.

    AN UNDECLARED `kind` DOES NOT COUNT SENTENCES, deliberately and in the same direction
    `export_violations` already takes.  Without a `kind` the module is not told which spelling
    the file uses, so a sentence in it is a string of unknown meaning, and guessing "hidden"
    is the guess that produced the 220.  EXPORT-CONTRACT.md 10.4 requires `07_export.py` to
    pass `kind=` on all sixteen files for the same reason its own string-versus-numeric check
    is keyed on it, so nothing in the bundle reaches this on an empty kind.
    """
    if not isinstance(value, str):
        return False
    if value == FIGURE_SUPPRESSED_TOKEN:
        return True
    if kind == "table-csv" and value in SUPPRESSION_SENTENCES:
        return True
    return is_suppressed(value)


def assert_suppression_vocabulary(reasons: Any) -> None:
    """Raise unless a caller's own copy of EXPORT-CONTRACT.md 7.5 matches this module's.

    THE RUNTIME HALF OF "THE SET IS CLOSED".  `SUPPRESSION_REASONS` is a transcription, and the
    failure mode of a transcription is not that it goes wrong loudly, it is that the contract
    grows a row and this module goes on returning False for a cell that is suppressed.
    Every other module that keeps its own 7.5 table -- `07_export.py` builds its
    `_SUPPRESSION_SENTENCES` out of `LABELS`, and `local/verify.py` needs the same sentences to
    check a bundle on arrival -- can hand it here at import time and get a stop condition
    instead of a silent divergence:

        disclosure.assert_suppression_vocabulary(LABELS)

    `reasons` is anything that maps a slug to its display sentence: a dict of the 7.5 rows, or
    a larger label table that CONTAINS them, which is what `07_export.LABELS` is.  A larger
    table is accepted because the caller's table legitimately carries the other twelve label
    groups of section 7; what is checked is that every slug this module names is present in it
    and spelled identically.  A slug MISSING from the caller's table is the divergence that
    matters and it raises.

    Raises DisclosureError, which is a stop condition and not a warning, and the message names
    the slugs rather than quoting a cell of anybody's data.
    """
    try:
        mapping = dict(reasons)
    except (TypeError, ValueError):
        raise DisclosureError(
            "assert_suppression_vocabulary needs a mapping of suppression slug to sentence"
        ) from None
    missing = [slug for slug, _ in SUPPRESSION_REASONS if slug not in mapping]
    if missing:
        raise DisclosureError(
            f"the caller's suppression vocabulary is missing {len(missing)} slug(s) that "
            f"EXPORT-CONTRACT.md 7.5 names: {sorted(missing)}"
        )
    disagreeing = sorted(
        slug for slug, sentence in SUPPRESSION_REASONS if mapping[slug] != sentence
    )
    if disagreeing:
        raise DisclosureError(
            f"the caller's suppression vocabulary spells {len(disagreeing)} sentence(s) "
            f"differently from EXPORT-CONTRACT.md 7.5: {disagreeing}"
        )


def render_count(value: Any) -> str:
    """Render one ALREADY-ROUNDED count onto a DISPLAY surface, with the thousands separator.

    THE ONE RENDERING RULE, held in one place.  A count a human is going to read is written
    `f"{n:,}"` -- `n = 1,240`, the numeral style CLAUDE.md states -- and a count something else
    is going to compute on is written as a bare number.  This function is the display side of
    that line and the only place in this module the separator is applied, so `n_pct`, `prev`,
    `safe_show` and every caller that renders a count of its own agree on one spelling instead
    of reimplementing it once per module and drifting.

    The SENTINEL PASSES THROUGH UNTOUCHED.  It is a rendered value in its own right, a
    disclosed table is expected to be full of it, and it carries no digits to separate.
    Separating it would also break `is_suppressed`, which is containment on the literal.

    Anything that is not a whole number -- a label, a None, a NaN, a fraction -- passes through
    as its own string rather than raising or truncating.  This renders into printed output, so
    a caller who reaches a label here wants to see the label rather than a traceback carrying
    it, and a fraction rendered as its truncation would be a quieter wrong answer than a
    fraction rendered as itself.  A whole-valued float is a count: a LEFT JOIN turns an INT64
    count column into float64, and `40.0` renders as "40", not "40.0".

    NOT FOR AN EXPORT CELL.  `safe_export` writes bytes and a separator in a numeric CSV cell
    is a data corruption.  A frame on its way to the boundary is built from `round20`, which
    returns the bare integer this function would otherwise decorate.  See the module docstring
    for the display-or-data boundary in full.
    """
    if is_suppressed(value):
        return SUPPRESSED
    if isinstance(value, bool):
        # True is not 1 here.  A flag in a count position is a bug upstream, and rendering it
        # as a numeral would hide that rather than show it.
        return str(value)
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return str(value)
    if not math.isfinite(number) or number != int(number):
        return str(value)
    return f"{int(number):,}"


def _usable_denominator(n: Any) -> float | None:
    """Return a denominator as a positive finite float, or None when it cannot be divided by."""
    if n is None or isinstance(n, str):
        return None
    try:
        value = float(n)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return value


def _rounded_denominator(n: Any) -> float | None:
    """The denominator a printed percentage divides by: the DISCLOSURE-ROUNDED one.

    DECIDED (EXPORT-CONTRACT.md 10.1): rounded numerator over ROUNDED denominator.  The earlier
    code divided the rounded numerator by the RAW denominator, which printed a percentage no
    reader could reproduce from the printed counts, and which put the raw denominator back into
    a published number after the rounding had just taken it out.  Dividing rounded by rounded
    means every percentage in the bundle is checkable with a calculator against the two counts
    printed beside it, which is exactly the check a reviewer performs.

    The raw denominator is screened first, because `round20` raises on a negative and the
    contract for `n_pct(40, -5)` is "(NA)", not a traceback.  A denominator at or below the
    floor rounds to the sentinel, and a percentage over a suppressed denominator is one nobody
    may check, so it too returns None and the caller prints no parenthetical.
    """
    raw = _usable_denominator(n)
    if raw is None:
        return None
    rounded = round20(int(raw))
    if not isinstance(rounded, int) or rounded <= 0:
        return None
    return float(rounded)


def _percent(rounded_count: int, rounded_denominator: float) -> str:
    """Render a percentage from an already-rounded count over an already-rounded denominator."""
    return f"{100.0 * float(rounded_count) / rounded_denominator:.0f}%"


def n_pct(k: int, n: int) -> str:
    """Return "count (pct%)" for k of n, suppressing the percentage with the count.

    DIVERGENCE from the ported `n_pct` (cyp2d6-spine-opioid-analysis/analysis/disclosure.py),
    which rendered `100 * k / n` at one decimal from the RAW numerator over the RAW denominator.
    The plan overrides it and the override is not cosmetic, it closes an exact leak: with the
    denominator disclosed, "40 (3.7%)" of n = 1000 inverts to a raw numerator of 37, so the port
    published the very count the rounding was there to hide.  Computing from the rounded count
    breaks the inversion, and zero decimals keeps the residual precision from re-narrowing the
    interval the rounding opened.

    SECOND DIVERGENCE, from this module's own first version: the denominator is rounded too.
    Rounded over rounded is the only arithmetic a reader can reproduce from the printed table,
    and it removes the raw denominator from the published number entirely.  The cost is a
    percentage coarser than the data, which is the correct trade at the disclosure boundary.

    THE COUNT IS RENDERED, NOT INTERPOLATED.  It goes through `render_count`, so a four-digit
    numerator reads "1,240 (25%)" and not "1240 (25%)".  This is a DISPLAY string and only a
    display string: it is printed, or it becomes a rendered table cell, and it is never put in
    a column declared to `count_cols` and never read back as a number.  See the module
    docstring.  The PERCENTAGE is unchanged and needs no separator: `_percent` is still handed
    the rounded INTEGER numerator, and a part over its own whole at zero decimals is three
    digits at the widest.
    """
    rounded = round20(k)
    if is_suppressed(rounded):
        # Complementary disclosure: a percentage times a disclosed denominator recovers the
        # hidden count exactly, so the percentage dies with the count.
        return SUPPRESSED
    denominator = _rounded_denominator(n)
    if denominator is None:
        return f"{render_count(rounded)} (NA)"
    return f"{render_count(rounded)} ({_percent(rounded, denominator)})"


def prev(k: int, n: int) -> str:
    """Prevalence of k in n.  Same arithmetic as `n_pct`, ported from `pivot_common.prev`.

    The one difference, kept from the port: `prev` never prints a parenthetical it cannot fill.
    A suppressed count returns the bare sentinel; a true zero returns the bare "0", where
    `n_pct` would print "0 (0%)"; an unusable or suppressed denominator returns the bare count,
    where `n_pct` would print "(NA)".  Use `prev` in prose and figure captions where a trailing
    "(NA)" reads as a missing value; use `n_pct` in table cells where a column of percentages
    needs every row to have a parenthetical.

    DIVERGENCE from the port, identical in kind to `n_pct`: the port computed the percentage
    from the raw numerator over the raw denominator, at one decimal.  See `n_pct` for why that
    inverts, and for why the denominator is rounded here too.

    The count goes through `render_count` on every one of the four paths out of here, so `prev`
    and `n_pct` render the same numerator identically and differ only in the parenthetical, as
    they always have.  A test pins that they agree.
    """
    rounded = round20(k)
    if is_suppressed(rounded) or rounded == 0:
        return render_count(rounded)
    denominator = _rounded_denominator(n)
    if denominator is None:
        return render_count(rounded)
    return f"{render_count(rounded)} ({_percent(rounded, denominator)})"


def _numeric(values: Iterable[Any]) -> pd.Series:
    """Coerce anything iterable to a numeric Series with the non-numbers dropped."""
    series = values if isinstance(values, pd.Series) else pd.Series(list(values), dtype="object")
    return pd.to_numeric(series, errors="coerce").dropna()


def _too_few_to_summarise(n_observations: int) -> bool:
    """True when a continuous summary over this many observations may not be shown.

    The floor is `disclosable`, so a change of reading is a change in one place.  The zero case
    is excluded BEFORE the predicate is consulted, and the distinction is not a technicality:
    `disclosable(0)` is True because a count of zero names nobody, whereas a mean over zero
    observations is not a small summary, it is not a summary at all, and it must not render as
    "nan +/- nan".
    """
    return n_observations == 0 or not disclosable(n_observations)


def mean_sd(values: Iterable[Any], decimals: int = 1) -> str:
    """Return "mean +/- SD", or the sentinel when 20 or fewer observations contribute.

    Ported unchanged in behaviour from cyp2d6-spine-opioid-analysis, with `decimals` added so a
    baseline-normalised fraction can be shown to two places without a second function.

    NO THOUSANDS SEPARATOR, and that is decided rather than overlooked.  A mean and an SD are
    measurements, not counts: they answer "how much", they carry decimals, and an SD around a
    deficit sits beside values that can be negative.  The separator rule is for the integer
    answer to "how many", which is what `render_count` renders.  See the module docstring.
    """
    clean = _numeric(values)
    if _too_few_to_summarise(len(clean)):
        return SUPPRESSED
    return f"{clean.mean():.{decimals}f} +/- {clean.std():.{decimals}f}"


def median_iqr(values: Iterable[Any], decimals: int = 1) -> str:
    """Return "median (Q1 to Q3)", or the sentinel when 20 or fewer observations contribute.

    The same floor as `mean_sd`, for a reason worth stating honestly rather than overstating.
    A mean of three people is at least a blend; a median of three is exactly the middle
    person's own value, and the quartiles are two more participants' own values.  The floor
    does NOT make that stop being true: at odd n above the floor the median is still one
    participant's value.  What the floor changes is the size of the set that participant could
    have been drawn from.  Under unshifted Controlled Tier dates an individual value attached
    to a small identifiable group is an identity, and an anonymity set of more than 20 is what
    makes the same arithmetic publishable.  The plan applies this rule to Figure 2 as well: a
    day whose group has 20 or fewer contributors is dropped, not drawn thin.

    The separator is the word "to", never an en-dash: house rules keep the en-dash for numeric
    ranges only, and an interquartile range whose bounds can be negative (a deficit below
    baseline) would read as an arithmetic sign next to a dash.

    No thousands separator either, for the reason given in `mean_sd`: a median and a quartile
    are measurements and not counts.  The word "separator" in the paragraph above is the
    RANGE separator and is a different thing entirely.
    """
    clean = _numeric(values)
    if _too_few_to_summarise(len(clean)):
        return SUPPRESSED
    quantiles = clean.quantile([0.25, 0.50, 0.75])
    q1, median, q3 = (float(quantiles.iloc[i]) for i in range(3))
    return f"{median:.{decimals}f} ({q1:.{decimals}f} to {q3:.{decimals}f})"


# --------------------------------------------------------------------------------------
# Frames: what may be looked at.
# --------------------------------------------------------------------------------------


def safe_show(df: pd.DataFrame, name: str = "df") -> None:
    """Print a frame's shape and column names, and never one row of it.

    DIVERGENCE from the ported `pivot_common.safe_show`, which printed `df.shape[0]` raw.  A
    7-row frame printed "7", which is a disclosed cell of size 7 on the one surface the whole
    policy exists to protect, because a notebook print is exactly what the browser automation
    ships to an external model.  The row count goes through `safe_n` here.

    A print is a DISPLAY surface, so the rounded row count goes through `render_count` and a
    four-digit frame prints "1,500 rows".  It used to inline the format spec, which is how a
    module ends up with two spellings of one rule; now there is one.
    """
    rows = safe_n(df)
    shown = render_count(rows)
    print(f"{name}: {shown} rows x {df.shape[1]} cols  [rows hidden by policy]")
    print(f"columns: {list(df.columns)}")


def safe_n(df: pd.DataFrame) -> int | str:
    """Disclosure-rounded row count of a frame."""
    return round20(len(df))


def safe_counts(series: pd.Series) -> pd.Series:
    """Value counts with every cell disclosure-rounded, missing values included as a category.

    THE LABEL IS SUPPRESSED WITH ITS COUNT.  Rounding only the counts leaves the index intact,
    and an index is data: a category occurring once would have printed its count as the
    sentinel while printing its label in full, so a rare diagnosis string, a rare device model
    or a free-text value would be disclosed by its mere presence in the output.  Every category
    whose count fails the floor is therefore folded into a single row labelled with the
    sentinel, which says that rare categories exist without saying how many there are or what
    any of them was.  The disclosed categories keep their labels and their descending order.
    """
    counts = series.value_counts(dropna=False)
    labels: list[Any] = []
    values: list[Any] = []
    suppressed_any = False
    for label, count in counts.items():
        rounded = round20(count)
        if is_suppressed(rounded):
            suppressed_any = True
            continue
        labels.append(label)
        values.append(rounded)
    if suppressed_any:
        labels.append(SUPPRESSED)
        values.append(SUPPRESSED)
    return pd.Series(values, index=labels, dtype="object", name=counts.name)


def suppress_frame(df: pd.DataFrame, count_cols: Sequence[str]) -> pd.DataFrame:
    """Return a copy with `round20` applied to each named count column, others untouched."""
    missing = [c for c in count_cols if c not in df.columns]
    if missing:
        # A typo here silently disables suppression on the column it was meant to protect, so
        # it raises rather than no-ops.
        raise DisclosureError(f"suppress_frame was given column(s) not in the frame: {missing}")
    out = df.copy()
    for col in count_cols:
        try:
            out[col] = out[col].map(round20)
        except DisclosureError:
            # Name the column and the offence.  Never the value: this renders into a notebook
            # traceback.  `from None` drops the chained frame so the offending cell cannot
            # reappear in a repr further down the traceback either.
            raise DisclosureError(
                f"count column {col!r} holds a negative count, which is a bug upstream "
                f"rather than a disclosure decision"
            ) from None
    return out


# --------------------------------------------------------------------------------------
# Frames: what may leave.
#
# Columns are screened by NAME and by DTYPE and by CONTENT, and any one of the three is enough
# to refuse.  Name matching alone is not enough in either direction.  A column renamed on the
# way out ("v1", "value", "col7") still holds the person id or the unshifted date it held
# before, and the export is exactly where renaming happens; conversely "update flag" contains
# the letters "date" and is not a date at all, which is why the name patterns match whole
# underscore-delimited tokens rather than substrings.
# --------------------------------------------------------------------------------------

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_ALNUM = re.compile(r"[^0-9A-Za-z]+")

# Deliberately narrow: the person-identifying families, not every column ending in "id".  A
# blanket `_id$` would refuse `concept id`, and concept ids are public OMOP vocabulary that the
# concept-set tables must be able to export.  Row-level keys with innocuous names (a visit
# occurrence id) are caught by the near-unique and integer rules below instead, which is the
# division of labour: names catch what is obvious, content catches what is disguised.
_ID_NAME = re.compile(
    r"(?:^|_)(?:person|participant|research|subject|patient|member|record|src|source)_?ids?(?:_|$)"
    r"|^ids?$"
    r"|(?:^|_)(?:pid|rid|mrn|ssn)(?:_|$)"
)

# "time" alone is absent on purpose: "wear time" and "sleep time" are legitimate aggregate
# minutes, while "datetime" and "timestamp" are matched in full.
_DATE_NAME = re.compile(r"(?:^|_)(?:date|dates|dob|birth|birthdate|datetime|timestamp)(?:_|$)")


def _normalize_name(name: Any) -> str:
    """Fold a column name to lowercase underscore tokens so one pattern covers every spelling."""
    text = _CAMEL_BOUNDARY.sub("_", str(name))
    return _NON_ALNUM.sub("_", text).strip("_").lower()


def _is_datetime_like(series: pd.Series) -> bool:
    """True when a column holds dates, by dtype or by the objects actually in it."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if isinstance(series.dtype, pd.PeriodDtype):
        return True
    if series.dtype != object:
        return False
    # A BigQuery DATE column arrives as object-dtype `datetime.date`, which no dtype predicate
    # catches.  One such value is a leak, so this is `any`, not `all`.
    return any(isinstance(v, (dt.date, dt.datetime)) for v in series.dropna())


def _is_integer_like(series: pd.Series) -> bool:
    """True for an integer column, including whole-valued floats.

    A BigQuery INT64 column with a single NULL in it arrives in pandas as float64, so an
    integer key that has been through a LEFT JOIN is float-dtype and would escape a plain
    integer-dtype test.  Booleans are integers to numpy and are excluded.
    """
    if pd.api.types.is_bool_dtype(series):
        return False
    if pd.api.types.is_integer_dtype(series):
        return True
    if pd.api.types.is_float_dtype(series):
        values = series.dropna()
        return len(values) > 0 and bool((values == values.round()).all())
    return False


def _distinct_ratio(series: pd.Series) -> float:
    """Distinct values divided by rows, counting missing as its own value."""
    rows = len(series)
    if rows == 0:
        return 0.0
    try:
        return float(series.nunique(dropna=False)) / float(rows)
    except TypeError:
        # Unhashable contents (a list-valued column).  Uniqueness cannot be cleared, so it
        # fails closed rather than open.
        return 1.0


def _is_number(value: Any) -> bool:
    """True for a real number that is not a bool and not NaN."""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not (isinstance(value, float) and math.isnan(value))
    try:
        import numpy as _np
    except ImportError:  # pragma: no cover - numpy ships with pandas
        return False
    if isinstance(value, _np.bool_):
        return False
    return isinstance(value, (_np.integer, _np.floating)) and not pd.isna(value)


def _is_not_applicable(value: Any) -> bool:
    """True when a cell means "this does not apply here" rather than "this is hidden".

    EXPORT-CONTRACT.md sections 4 and 5 both spend a row of their shared-rule table on this
    distinction, so it gets a named predicate rather than an inline comparison.  The empty
    string is the contract's spelling; None and NaN are what an in-memory frame carries before
    `safe_export` writes them out as the empty string through `na_rep=""`.

    IT IS NOT THE COMPLEMENT OF `is_bundle_suppressed`.  A disclosed `40` is neither hidden nor
    not-applicable.  This answers only "is there nothing here", which is the question the
    partition class has to ask before it can count members.
    """
    if value is None:
        return True
    try:
        if bool(pd.isna(value)):
            return True
    except (TypeError, ValueError):
        pass
    return isinstance(value, str) and value.strip() == ""


def _is_disclosed_value(value: Any) -> bool:
    """True when a cell says something: present, not null, not suppressed in ANY representation.

    `is_bundle_suppressed`, not `is_suppressed`, and the difference is the whole of the
    complementary-disclosure class working on a real bundle frame.  This is the PERCENTAGE side
    of that class: the count side asks whether the count is hidden, and this asks whether the
    percentage beside it is nonetheless shown.  Keying it on the sentinel alone would read a
    percentage cell legitimately written as the 7.5 sentence "suppressed because the count
    behind it is suppressed" -- which is exactly what `ledger_exclusion_and_censoring_reasons`
    writes on a row whose numerator is hidden -- as a DISCLOSED percentage, and the class would
    then refuse the correctly suppressed file it was written to bless.
    """
    if value is None or is_bundle_suppressed(value):
        return False
    try:
        if bool(pd.isna(value)):
            return False
    except (TypeError, ValueError):
        pass
    return str(value).strip() != ""


def export_violations(
    df: pd.DataFrame,
    *,
    count_cols: Sequence[str] = (),
    allow_zero: bool = True,
    percentage_columns: Sequence[str] = (),
    partitions: Sequence[Sequence[str]] = (),
    specification_columns: Sequence[str] = (),
    kind: str = "",
    path: Any = None,
) -> list[str]:
    """Return every reason this frame may not be exported.  Empty list means it may.

    The pure, testable heart of `safe_export`: no file is touched, nothing is printed, and the
    same frame always gives the same list.  EXPORT-CONTRACT.md 10.4 lists the refusal classes
    and they are ALL evaluated, never short-circuited, because a caller fixing violations one
    traceback at a time makes one round trip through the perimeter per violation to learn what
    one report could have told them at once:

      1. a path extension that is not `.csv`, `.json` or `.md5`      (10.4 item 1)
      2. a count cell that is not a legal disclosed count            (10.4 item 3)
      3. a disclosed percentage standing beside a suppressed count   (10.4 item 4)
      4. exactly one suppressed member of a declared partition       (10.4 item 5)
      5. a string cell carrying U+2014 or U+2212                     (10.4 item 6)
      6. a kind-inappropriate column, string or numeric              (10.4 item 7)
      7. an identifier-like, date-like or near-unique column         (10.4 item 2, section 10.2)

    Every parameter after `df` is keyword-only, so the signature the plan pins
    (`export_violations(df, count_cols=...)`) cannot be re-ordered by a later edit, and a
    caller cannot accidentally pass a partition list where a count list was meant.

    `count_cols` keeps that spelling.  EXPORT-CONTRACT.md 10.4 proposes `count_columns`; the
    two must be reconciled to one spelling before `07_export.py` is written.

    Declaring a column and misspelling it is itself a violation, in every class that takes
    column names, `specification_columns` included.  A silent no-op is how a check gets
    switched off on the one column it was written to guard.

    `specification_columns` names columns holding VOCABULARY OR SPECIFICATION VALUES rather
    than participant-derived values, and exempts each named column from the NEAR-UNIQUE and
    IDENTIFIER-LIKE classes and from nothing else.

    WHAT QUALIFIES.  A specification column describes the STUDY, not the people in it.  Its
    values come from a public vocabulary or are fixed by the protocol, they read the same
    whichever cohort the pipeline is pointed at, and no row of the file is about a person.  The
    worked example is `ledgers-csv/ledger_concept_set_registry.csv` (EXPORT-CONTRACT.md 5.6),
    whose producer is `cs_spine.registry_rows()`: one row per locked CPT-4 code or ICD-10-PCS
    stem, so its `code` column carries a distinct value in every row BY CONSTRUCTION.  That
    file is a table of contents for the concept set, it is derived from a vocabulary anyone can
    download, and it identifies nobody -- yet the near-unique class refuses the whole of it for
    having exactly the shape the contract requires of it.  Declaring `code` says so once, in
    the call, on the record.

    WHAT IT IS NOT FOR, which is the abuse this parameter must not be used to commit: silencing
    the near-unique class on a column of PARTICIPANT-DERIVED values because the export was
    inconvenient.  A per-person wear-time total, a per-person deficit, a mean carried to six
    decimals -- each is near-unique for precisely the reason the class exists, and each turns a
    group of rows into one row when joined against any outside list sharing one attribute.  The
    question is never "is this column blocking my export".  It is "would this column read the
    same if the cohort were a different hundred people".  If it would not, it is not a
    specification column and no declaration makes it one.

    Three properties of the declaration, each of them load-bearing:
      * PER COLUMN, NAMED EXPLICITLY.  There is no file-level and no `kind`-level switch, so an
        author declares `code` rather than switching off checking for a file, and an over-broad
        exemption is visible at the call site as a list of column names a reviewer can read.
      * IT EXEMPTS NOTHING ELSE.  A declared column is still refused for a banned dash
        character, still held to the floor if it is also named in `count_cols`, still checked
        for complementary disclosure and for partition membership, and still refused for being
        date-like.  See the comment on the date class in the body for why that last one is a
        deliberate decision rather than an oversight.
      * A DECLARED COLUMN THAT IS NOT IN THE FRAME IS ITSELF A VIOLATION.  Otherwise a typo
        silently grants no exemption at all, or worse, a later column rename silently moves the
        exemption onto nothing while the author goes on believing the file is covered.

    No message ever quotes a cell value, and a test pins that property rather than guessing at
    a substring.  A DisclosureError renders into a notebook traceback, which is precisely the
    model-visible surface this module protects, so "3 cells below the floor" is safe to say and
    "cells 3, 7 and 11" is not.  Row counts inside a message go through `safe_n` for the same
    reason.
    """
    if not isinstance(df, pd.DataFrame):
        return [f"export target is a {type(df).__name__}, not a DataFrame"]

    violations: list[str] = []
    rows = len(df)
    rounded_rows = safe_n(df)

    # -- 1. the path itself ---------------------------------------------------------------
    # R2: the perimeter exports the plotted series, never the plot.  A `.png` is not merely a
    # file this module cannot check, it is a file nobody at the boundary can read before it
    # leaves, and an image of a thin tail discloses what the absence rule removed from the CSV.
    if path is not None:
        suffix = Path(path).suffix.lower()
        if suffix not in ALLOWED_EXPORT_SUFFIXES:
            violations.append(
                f"export path {Path(path).name!r} has an extension that may not leave the "
                f"perimeter; permitted: {', '.join(ALLOWED_EXPORT_SUFFIXES)}"
            )

    # -- 2. count cells that fail the floor -----------------------------------------------
    present_counts = [c for c in count_cols if c in df.columns]
    for col in count_cols:
        if col not in df.columns:
            # A misspelled count column silently switches this check off for the column it was
            # meant to guard, so the misspelling is itself a violation.
            violations.append(f"declared count column {col!r} is not in the frame")
            continue
        values = pd.to_numeric(df[col], errors="coerce").dropna()
        # `is_legal_disclosed_count`, NOT `disclosable`.  The frame this gate is handed has
        # already been through `round20` -- that is what "export" means here -- so the cell in
        # hand is a RENDERED value, and the question the gate is in a position to ask is whether
        # it is a legal one to write down, not whether some true count is above the floor.
        # Asking `disclosable` here refused every correctly rounded 20 in the bundle, because
        # `round20(21)` through `round20(29)` are all exactly 20 and `disclosable(20)` is False.
        # The strictness that class was written for is kept: it exists to catch a caller who
        # forgot to round, and an unrounded count is almost never an exact multiple of 20.  See
        # `is_legal_disclosed_count` for the two questions and for the one residual gap.
        # Already-suppressed cells are strings and are dropped by `to_numeric` before they reach
        # the predicate; the predicate accepts the sentinel in its own right, for callers that
        # map it over a rendered column directly.
        n_bad = int((~values.map(is_legal_disclosed_count).astype(bool)).sum())
        if n_bad:
            # Names the column and the NUMBER of offending cells, never a cell value: this
            # message renders into a notebook traceback.  The rounding base is named in words
            # for the same reason the floor is, so no numeral but the cell count appears.
            violations.append(
                f"count column {col!r} holds {n_bad} cell(s) that are not legal disclosed "
                f"counts; a legal disclosed count is a true zero, the suppression sentinel, "
                f"or a positive whole multiple of the rounding base"
            )
        # Zero is asked separately, with the predicate above left at its permissive default, so
        # that a disallowed zero is reported once under its own specific message rather than
        # twice under two.
        if not allow_zero and bool((values == 0).any()):
            violations.append(f"count column {col!r} holds a zero and zero is not allowed here")

    # -- 3. complementary disclosure ------------------------------------------------------
    # CLAUDE.md rule 1, and the one violation on this list that costs a manuscript rather than
    # a re-export: a disclosed percentage times a disclosed denominator recovers the hidden
    # count exactly, so a percentage may not outlive the count beside it.
    #
    # BOTH SIDES ASK `is_bundle_suppressed`.  Keyed on the sentinel alone -- which is what this
    # class did until the representation fix -- it could not see a suppressed count in the
    # bundle's own spelling, so it returned nothing on EVERY frame `07_export.py` hands to
    # `safe_export`.  A class that is inert on the only frames that cross the boundary is not a
    # weak check, it is an absent one, and this is the class the whole module exists for.
    for pct_col in percentage_columns:
        if pct_col not in df.columns:
            violations.append(f"declared percentage column {pct_col!r} is not in the frame")
            continue
        if not present_counts:
            violations.append(
                f"percentage column {pct_col!r} is declared with no count column to pair it "
                f"against, so complementary disclosure cannot be checked"
            )
            continue
        disclosed = df[pct_col].map(_is_disclosed_value)
        for count_col in present_counts:
            paired = int((disclosed & df[count_col].map(is_bundle_suppressed)).sum())
            if paired:
                violations.append(
                    f"percentage column {pct_col!r} discloses {paired} value(s) on row(s) "
                    f"where count column {count_col!r} is suppressed"
                )

    # -- 4. secondary suppression across a declared partition ------------------------------
    # EXPORT-CONTRACT.md line 50: within a set of counts that partitions a disclosed total, one
    # suppressed member is recoverable by subtraction, so at least two are suppressed or none.
    #
    # `is_bundle_suppressed`, for the reason given on class 3: keyed on the sentinel this class
    # could not see a suppressed member of a bundle frame at all, so it never refused the lone
    # member it was written to refuse.
    #
    # A ROW WITH FEWER THAN TWO MEMBERS PRESENT PARTITIONS NOTHING and is skipped rather than
    # read as a lone suppression.  This is not a loosening, it is what makes the class correct
    # on the frame it now finally sees.  The STROBE ladder declares `(n_dropped, n_out)` as a
    # partition of `n_in`, and its terminal rung carries the not-applicable empty string in
    # `n_dropped` and a hidden `n_out`: one member suppressed, one member ABSENT, and nothing
    # to subtract it from, because there is no disclosed sibling.  Counting that row would
    # refuse the ladder for a suppression that discloses nothing, and the only way to satisfy
    # the refusal would be to suppress a cell the contract requires to be blank.
    for group in partitions:
        members = list(group)
        absent = [c for c in members if c not in df.columns]
        if absent:
            violations.append(f"declared partition names column(s) not in the frame: {absent}")
            continue
        if len(members) < 2:
            violations.append(
                f"declared partition {members!r} has fewer than two members, so it does not "
                f"partition anything"
            )
            continue
        suppressed_per_row = sum(df[c].map(is_bundle_suppressed).astype(int) for c in members)
        present_per_row = sum(
            (~df[c].map(_is_not_applicable).astype(bool)).astype(int) for c in members
        )
        lone = int(((suppressed_per_row == 1) & (present_per_row > 1)).sum())
        if lone:
            violations.append(
                f"partition {members!r} has exactly one suppressed member on {lone} row(s), "
                f"which is recoverable by subtraction from the disclosed total"
            )

    # -- 5. banned characters --------------------------------------------------------------
    # The em-dash and the Unicode minus, named by code point in the constants block so the
    # bytes never enter this source.  A header is a written string too, so it is scanned.
    for position, col in enumerate(df.columns):
        series = df.iloc[:, position]
        if any(ch in str(col) for ch in BANNED_CHARACTERS):
            violations.append(
                f"column header at position {position} carries a banned dash character "
                f"(U+2014 or U+2212)"
            )
        offenders = sum(
            1
            for value in series
            if isinstance(value, str) and any(ch in value for ch in BANNED_CHARACTERS)
        )
        if offenders:
            violations.append(
                f"column {col!r} holds {offenders} string cell(s) carrying a banned dash "
                f"character (U+2014 or U+2212)"
            )

    # -- 6. kind-appropriate content --------------------------------------------------------
    # A table CSV is fully rendered display strings, because a table cell that is still a number
    # is a cell the renderer would format a second time and possibly differently.  A figure CSV
    # is plotted, so a display string in a numeric column is a value matplotlib cannot draw, and
    # a suppressed figure row is ABSENT from the file rather than written as a sentinel.
    if kind:
        if kind not in MANIFEST_KINDS:
            violations.append(
                f"export kind {kind!r} is not one of {', '.join(MANIFEST_KINDS)}"
            )
        elif kind == "table-csv":
            for position, col in enumerate(df.columns):
                non_strings = sum(
                    1 for value in df.iloc[:, position] if not isinstance(value, str)
                )
                if non_strings:
                    violations.append(
                        f"column {col!r} holds {non_strings} cell(s) that are not display "
                        f"strings, and a table CSV carries rendered strings only"
                    )
        elif kind == "figure-csv":
            for position, col in enumerate(df.columns):
                series = df.iloc[:, position]
                numerals = sum(1 for value in series if _is_number(value))
                strings = sum(1 for value in series if isinstance(value, str))
                if numerals and strings:
                    violations.append(
                        f"column {col!r} mixes {strings} display string(s) with numerals, and "
                        f"a figure CSV omits a suppressed row rather than writing a sentinel"
                    )

    # -- 7. one pass per column, so the report reads column by column ---------------------
    # The author's specification declarations are resolved FIRST, before the pass consults
    # them, so that a misspelled name is reported once under its own message instead of
    # disappearing as an exemption that quietly never applied.  See the docstring for what a
    # specification column legitimately is and for the abuse this must not be used for.
    declared_specification: set[Any] = set()
    for col in specification_columns:
        if col not in df.columns:
            violations.append(f"declared specification column {col!r} is not in the frame")
            continue
        declared_specification.add(col)

    for col in df.columns:
        series = df[col]
        name = _normalize_name(col)
        wide_enough = rows > NEAR_UNIQUE_MIN_ROWS
        ratio = _distinct_ratio(series)
        # Declared, one column at a time, by this column's own name.  There is no file-level
        # and no `kind`-level form of this: an author exempts `code`, never a file, so the
        # exemption stays auditable and an over-broad one is visible at the call site.  It
        # reaches the two LINKAGE classes below -- identifier-like and near-unique -- and no
        # other class in this function.
        specified = col in declared_specification

        # identifier-like, by name or by shape.
        if not specified:
            if _ID_NAME.search(name):
                violations.append(f"column {col!r} is named like a participant identifier")
            elif wide_enough and _is_integer_like(series) and ratio > NEAR_UNIQUE_RATIO:
                violations.append(
                    f"column {col!r} is an integer column whose values are near-unique, "
                    f"which is the shape of a key regardless of what it is called"
                )

        # date-like, by name or by dtype.  Controlled Tier dates are UNSHIFTED, so a date is
        # not metadata about a record, it is a direct identifier of the person in it.
        #
        # DELIBERATELY NOT REACHED by `specification_columns`, and this is the one class where
        # a reader is most likely to expect that it would be, so the decision is written down
        # here rather than left to be inferred from the code.  A specification describes the
        # study: a vocabulary code, a match rule, a region label.  A date in such a file is one
        # of exactly two things, and neither of them is a specification value.  Either it is
        # participant-derived and has been filed under the wrong kind of column, which is the
        # leak this class exists to stop; or it is a build fact -- an extract date, a lock date,
        # a vocabulary release -- which belongs in MANIFEST.csv or in the run log, not in a
        # ledger row.  Both readings want the refusal, so a declared date-like column is still
        # refused, and a test pins it.
        if _DATE_NAME.search(name) or _is_datetime_like(series):
            violations.append(
                f"column {col!r} is a date, and Controlled Tier dates are unshifted"
            )

        # near-unique.  A column with a distinct value in almost every row is a quasi-
        # identifier even when nothing about its name says so: joined against any outside list
        # that shares one attribute, a near-unique column turns a group of rows into one row,
        # and a per-person total or a mean carried to six decimals is a fingerprint in exactly
        # the way a name is.
        #
        # The message states the CEILING and not the observed ratio, and its row count goes
        # through `safe_n`.  The earlier wording printed "100% of 21 rows", which is a raw row
        # count on a notebook traceback and, multiplied by the ratio, the exact number of
        # distinct values in the column.
        #
        # This is the class `specification_columns` exists for.  The registry of locked concept
        # codes is one row per code, so its `code` column is distinct in every row and the whole
        # file is refused for being exactly what EXPORT-CONTRACT.md 5.6 asks it to be.  A list
        # of CPT-4 and ICD-10-PCS codes is a SPECIFICATION: it describes the study, it comes
        # from a public vocabulary, and it identifies nobody.
        if wide_enough and ratio > NEAR_UNIQUE_RATIO and not specified:
            violations.append(
                f"column {col!r} is near-unique: more than the {NEAR_UNIQUE_RATIO:.0%} ceiling "
                f"of its {rounded_rows} rows hold a distinct value"
            )

    return violations


def md5_of_bytes(data: bytes) -> str:
    """md5 hex digest of exactly these bytes.

    An integrity check on a hand-carried file, not a security primitive: the threat is a
    truncated copy-paste out of the perimeter, and md5 is chosen because the VM terminal can
    produce one with `md5sum` and no install.
    """
    return hashlib.md5(data).hexdigest()


def _manifest_file_field(target: Path) -> str:
    """The `file` column of MANIFEST.csv: the path relative to `v1/results/`, forward slashes.

    EXPORT-CONTRACT.md 8.3 defines the field relative to the bundle root, and the bundle root
    is the last directory named `results` on the path.  A path written outside a results tree
    (a temporary directory in a test) degrades to the bare file name rather than raising: the
    manifest field is a label, and refusing to write a legal frame because its destination is
    unusually named would be a disclosure gate misfiring on a naming convention.
    """
    parts = list(target.parts)
    if "results" in parts:
        cut = len(parts) - 1 - parts[::-1].index("results")
        return "/".join(parts[cut + 1:])
    return target.name


def _integers_as_integers(df: pd.DataFrame) -> pd.DataFrame:
    """Cast whole-valued float columns to int64 so a count never writes as `340.0`.

    EXPORT-CONTRACT.md 8.2.  A BigQuery INT64 column that has been through a LEFT JOIN arrives
    as float64, and `to_csv` would render its counts with a trailing `.0` that no other run of
    the same pipeline is guaranteed to produce.  Columns holding a null are left alone, because
    int64 cannot carry one and a coerced null is worse than a formatted float.
    """
    out = df
    for position, col in enumerate(df.columns):
        series = df.iloc[:, position]
        if pd.api.types.is_float_dtype(series) and _is_integer_like(series):
            if bool(series.notna().all()):
                if out is df:
                    out = df.copy()
                out[col] = series.astype("int64")
    return out


def safe_export(
    df: pd.DataFrame,
    path: Any,
    *,
    kind: str = "",
    exhibit: str = "",
    description: str = "",
    count_cols: Sequence[str] = (),
    percentage_columns: Sequence[str] = (),
    partitions: Sequence[Sequence[str]] = (),
    specification_columns: Sequence[str] = (),
    allow_zero: bool = True,
) -> dict:
    """Write a frame to CSV only if it is disclosure-clean, and return its MANIFEST.csv row.

    Raises DisclosureError listing EVERY violation found, never only the first.  Nothing is
    opened, created or truncated on the failing path: the check runs first, the CSV is rendered
    to bytes in memory second, and the file is opened only to receive a complete payload, so
    there is no state in which a partial export exists on disk.

    Returns the `MANIFEST.csv` row as a dict, per EXPORT-CONTRACT.md 10.4 item 9 and section
    8.3, with the keys in `MANIFEST_COLUMNS`: `file`, `kind`, `exhibit`, `md5`, `n_rows`,
    `n_columns`, `min_disclosed_count`, `n_suppressed_cells`, `description`.  It returns a row
    rather than a bare md5 because `07_export.py` has to write nine such rows and a manifest
    assembled from nine separate re-derivations of row and column counts is nine chances to
    describe a file the exporter did not write.  `n_rows` is the file's own row count, which is
    a count of aggregated rows and not of people; the contract mandates it in this column.

    `kind` is optional and defaults to no kind-specific check.  `07_export.py` passes it for
    every file in the bundle: without it the string/numeric check of 10.4 item 7 does not run.

    `specification_columns` is passed straight to `export_violations` and is defined in full
    there.  In one sentence: it names, ONE COLUMN AT A TIME, columns whose values are drawn
    from a public vocabulary or fixed by the protocol rather than derived from participants,
    and it exempts each named column from the NEAR-UNIQUE and IDENTIFIER-LIKE classes and from
    nothing else.  The file it was written for is `ledgers-csv/ledger_concept_set_registry.csv`
    (EXPORT-CONTRACT.md 5.6), which is one row per locked CPT-4 code or ICD-10-PCS stem and so
    is refused on `code` for having exactly the shape the contract requires:

        safe_export(registry, path, kind="table-csv", specification_columns=["code"])

    It is not a way to quiet the near-unique class on participant-derived values, and there is
    deliberately no file-level or `kind`-level form of it that would let it become one.
    """
    violations = export_violations(
        df,
        count_cols=count_cols,
        allow_zero=allow_zero,
        percentage_columns=percentage_columns,
        partitions=partitions,
        specification_columns=specification_columns,
        kind=kind,
        path=path,
    )
    if violations:
        listed = "\n".join(f"  {i}. {v}" for i, v in enumerate(violations, 1))
        raise DisclosureError(
            f"refusing to export {Path(path).name}: "
            f"{len(violations)} disclosure violation(s)\n{listed}"
        )

    # index=False and a fixed float format and a pinned line terminator: three ways the same
    # frame could otherwise produce different bytes, and the md5 is only worth stamping if it
    # is a property of the data rather than of the machine.
    payload = _integers_as_integers(df).to_csv(
        index=False, float_format=FLOAT_FORMAT, lineterminator="\n", na_rep=""
    ).encode("utf-8")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)

    # Section 8.1: the md5 is computed over the bytes READ BACK from disk, never over the
    # in-memory frame.  The hash exists to catch a transcription slip in transfer, and a hash
    # of anything other than the transferred bytes cannot do that.
    digest = md5_of_bytes(target.read_bytes())

    # `min_disclosed_count`, and it has NO KIND-DEPENDENT MEANING, unlike the field below it.
    # 8.3 defines it as "the smallest count value written in the file, or empty when the file
    # writes no count", with no qualifier attached -- where the very next row of the same table
    # writes "or as a suppression sentence IN A TABLE CSV" in the contract's own words.  A count
    # is a count in either kind, so this arithmetic is the same on both:
    #   * A table CSV's count column holds NUMERAL STRINGS, which `to_numeric` parses.  It is a
    #     column DECLARED in `count_cols` that stays numeric on either kind, because that is the
    #     column the floor check parses, so no separated `1,240` reaches here from this bundle.
    #     `07_export.py` recomputes the field for the COMPOSED cells it writes elsewhere (`1,240
    #     (33%)`, `n = 340`), which this parser cannot read and which are not count columns.
    #   * A suppressed cell is a string in all three spellings, so `to_numeric` drops it and a
    #     hidden cell can never become the minimum.  A file whose counts are all hidden reports
    #     the empty string, which is what 4.4 states for Figure 4 at tier 4.
    # THE DECLARED COUNT COLUMNS AND NOTHING ELSE.  Widening it to every numeric column would
    # sweep in Figure 4's `series_order` and its `day_relative_to_event`, which reaches -14, and
    # Figure 3's `row_order`; none is a count and the minimum over them is not the smallest
    # count in the file.  The empty pieces are dropped BEFORE the concat -- they contribute no
    # value to the minimum either way, and concatenating an empty frame is a pandas
    # FutureWarning that would render into a notebook, which is the surface this module exists
    # to keep clean.
    pieces = [
        series
        for series in (
            pd.to_numeric(df[c], errors="coerce").dropna()
            for c in count_cols if c in df.columns
        )
        if len(series)
    ]
    counted = pd.concat(pieces) if pieces else pd.Series(dtype="float64")
    # EXPORT-CONTRACT.md 8.3 defines this field as "cells written as SUPPRESSED, or as a
    # suppression sentence in a table CSV", which is neither `is_suppressed` nor
    # `is_bundle_suppressed`.  Counted on the SENTINEL it came back 0 on every file in the
    # bundle, including the one that is 119 suppressed cells deep.  Counted on
    # `is_bundle_suppressed` it went the other way and counted a figure CSV's display prose:
    # Figure 4 stamped 220 where the contract states 176, the 44 extra being the
    # `not_plotted_display` sentences, which are prose about a row whose token is already
    # counted in the same row.  `_is_manifest_suppressed_cell` is the field's own predicate and
    # carries the argument for keying it on `kind` rather than on a column-name convention.
    suppressed_cells = sum(
        int(df.iloc[:, position].map(lambda cell: _is_manifest_suppressed_cell(cell, kind)).sum())
        for position in range(df.shape[1])
    )

    inferred_kind = kind or ("results-json" if target.suffix.lower() == ".json" else "")
    return {
        "file": _manifest_file_field(target),
        "kind": inferred_kind,
        "exhibit": exhibit,
        "md5": digest,
        "n_rows": int(len(df)),
        "n_columns": int(df.shape[1]),
        "min_disclosed_count": int(counted.min()) if len(counted) else "",
        "n_suppressed_cells": int(suppressed_cells),
        "description": description,
    }


# --------------------------------------------------------------------------------------
# Self-test.  The real suite is tests/test_disclosure.py; this is the house pattern that lets
# `python3 disclosure.py` answer "is this module sane" with no pytest and no network.  A pytest
# case invokes `_run_self_test` too, so these assertions are covered by CI rather than only by
# whoever runs the module by hand.
# --------------------------------------------------------------------------------------


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _run_self_test() -> None:
    import tempfile

    n = 0

    _expect(disclosable(0), "a true zero is disclosable")
    _expect(not any(disclosable(k) for k in range(1, MIN_CELL + 1)), "1 to 20 are not")
    _expect(disclosable(MIN_CELL + 1), "21 is")
    _expect(not disclosable(-3) and not disclosable(0.5), "negative and fractional are not")
    n += 4

    _expect(not disclosable(MIN_CELL) and is_legal_disclosed_count(ROUND_BASE),
            "the two predicates disagree on 20, which is the distinction they exist to keep")
    _expect(all(is_legal_disclosed_count(round20(k)) for k in range(0, 200)),
            "every value round20 can return is a legal disclosed cell")
    _expect(not is_legal_disclosed_count(7) and not is_legal_disclosed_count(MIN_CELL + 1),
            "an unrounded count is refused; 21 is the common forgot-to-round mistake")
    _expect(is_legal_disclosed_count(SUPPRESSED) and is_legal_disclosed_count(40.0),
            "the sentinel and a whole-valued float are legal rendered cells")
    _expect(is_legal_disclosed_count(0) and not is_legal_disclosed_count(0, allow_zero=False),
            "a true zero is legal exactly when zero is allowed")
    _expect(not is_legal_disclosed_count(-ROUND_BASE) and not is_legal_disclosed_count(40.5),
            "a negative and a fractional are not legal rendered cells")
    n += 6

    _expect(round20(0) == 0, "a true zero survives")
    _expect(round20(1) == SUPPRESSED and round20(MIN_CELL) == SUPPRESSED, "1 to 20 suppress")
    _expect(round20(21) == ROUND_BASE and round20(30) == 40 and round20(50) == 60, "half-up")
    _expect(round20(90) == 100, "the half at 90 goes up, not to the even 80")
    _expect(round20(None) is None and round20("cervical") == "cervical", "non-numbers pass")
    _expect(is_suppressed(round20(7)) and not is_suppressed(round20(0)), "sentinel detected")
    _expect(is_suppressed(f"40 of {SUPPRESSED}"), "the sentinel is detected inside a composite")
    n += 7

    _expect(n_pct(5, 100) == SUPPRESSED, "a suppressed count suppresses its percentage")
    _expect(n_pct(31, 1000) == "40 (4%)", "percentage from the ROUNDED numerator")
    _expect(n_pct(31, 110) == "40 (33%)", "percentage over the ROUNDED denominator")
    _expect(n_pct(40, 0) == "40 (NA)" and prev(40, 0) == "40", "no division by zero")
    _expect(prev(0, 100) == "0", "prevalence prints a bare zero")
    n += 5

    # The house numeral style is `n = 1,240`, and four- and five-digit counts are the ordinary
    # case in the exclusion-reason ledger, not an edge case.
    _expect(n_pct(1500, 1500) == "1,500 (100%)", "a four-digit count carries the separator")
    _expect(n_pct(340, 1000) == "340 (34%)", "a three-digit count does not gain one")
    _expect(n_pct(1234567, 2000000) == "1,234,560 (62%)", "seven digits take both separators")
    _expect(n_pct(1500, 0) == "1,500 (NA)" and prev(1500, 0) == "1,500",
            "the count is rendered on the paths that print no percentage too")
    _expect(prev(1500, 1500) == n_pct(1500, 1500), "prev and n_pct render the count alike")
    _expect(render_count(SUPPRESSED) == SUPPRESSED and n_pct(8, 1500) == SUPPRESSED,
            "the suppression sentinel is untouched by the separator")
    _expect(not is_legal_disclosed_count("1,240") and not is_suppressed("1,240"),
            "a rendered count is one-way: the parsing predicates refuse it, never bless it")
    _expect(render_count(round20(1500)) == "1,500" and round20(1500) == 1500,
            "the separator is on the DISPLAY of the count, never on the count itself")
    n += 8

    _expect(mean_sd(range(MIN_CELL)) == SUPPRESSED, "20 observations are too few for a mean")
    _expect(median_iqr(range(MIN_CELL)) == SUPPRESSED, "20 observations are too few for a median")
    _expect(mean_sd([]) == SUPPRESSED, "zero observations are not a summary")
    _expect(" to " in median_iqr(range(41)), "the interquartile separator is the word to")
    n += 4

    counts = safe_counts(pd.Series(["common"] * 100 + ["rare-diagnosis-XYZ"] * 3))
    _expect("rare-diagnosis-XYZ" not in list(counts.index), "a suppressed label is suppressed")
    _expect(counts["common"] == 100 and counts[SUPPRESSED] == SUPPRESSED, "the rest survives")
    n += 2

    clean = pd.DataFrame(
        {
            "region": ["cervical"] * 15 + ["lumbar"] * 15,
            "day": list(range(1, 16)) * 2,
            "n contributing": [40, 60, 80] * 10,
        }
    )
    _expect(export_violations(clean, count_cols=["n contributing"]) == [], "a clean frame passes")
    dirty = clean.assign(**{"person id": range(30), "surgery date": ["2020-01-01"] * 30})
    dirty.loc[0, "n contributing"] = 7
    _expect(len(export_violations(dirty, count_cols=["n contributing"])) == 4, "all classes fire")
    rounded_twenty = clean.copy()
    rounded_twenty.loc[0, "n contributing"] = ROUND_BASE
    _expect(export_violations(rounded_twenty, count_cols=["n contributing"]) == [],
            "a correctly rounded 20 exports: it stands on a true count of 21 to 29")
    forgot_to_round = clean.copy()
    forgot_to_round.loc[0, "n contributing"] = MIN_CELL + 1
    _expect(len(export_violations(forgot_to_round, count_cols=["n contributing"])) == 1,
            "a caller who forgot to round is still caught: 21 is not a multiple of the base")
    _expect(len(export_violations(clean, count_cols=["n contributing"], path="figure2.png")) == 1,
            "a non-tabular extension is refused")
    complementary = pd.DataFrame({"n": [SUPPRESSED, "40"], "pct": ["37%", "33%"]})
    _expect(len(export_violations(complementary, count_cols=["n"],
                                  percentage_columns=["pct"])) == 1,
            "a percentage beside a suppressed count is refused")
    partitioned = pd.DataFrame({"a": [SUPPRESSED], "b": ["40"], "c": ["60"]})
    _expect(len(export_violations(partitioned, partitions=[["a", "b", "c"]])) == 1,
            "one suppressed member of a partition is refused")
    _expect(len(export_violations(pd.DataFrame({"label": ["a" + EM_DASH + "b"]}))) == 1,
            "a banned dash character is refused")
    n += 8

    # The 7.5 table itself.  The literals are pinned here so a stripped checkout with no
    # `prespecification/` beside it is still held to the contract's spelling; the whole-table
    # comparison against the contract's own bytes is
    # `tests/test_disclosure.py::test_the_suppression_sentences_are_the_contract_s_own`.
    reasons = dict(SUPPRESSION_REASONS)
    _expect(reasons["not_estimable_separation"] == "not estimable (separation)",
            "the tenth 7.5 sentence is the separation refusal ANALYSIS-PLAN.md 4.9 names")
    _expect(reasons["not_estimable_separation"] != reasons["not_estimable_convergence"],
            "and it is a DIFFERENT sentence from the convergence one, which is the whole reason "
            "it exists: a quasi-separated fit CONVERGES, so that sentence would be false")
    _expect(len(set(reasons.values())) == len(SUPPRESSION_REASONS),
            "no two slugs share a sentence, so a printed cell names exactly one reason")
    n += 3

    # The two classes above, asked again in the BUNDLE's own representations.  Keyed on the
    # sentinel both were inert here, which is the whole of the defect this block pins closed:
    # the frames below are the only ones that ever cross the boundary.
    sentence = SUPPRESSION_REASONS[0][1]
    _expect(is_bundle_suppressed(FIGURE_SUPPRESSED_TOKEN)
            and is_bundle_suppressed(sentence)
            and is_bundle_suppressed(SUPPRESSED),
            "every sanctioned representation of a hidden cell is recognised")
    _expect(not is_suppressed(FIGURE_SUPPRESSED_TOKEN) and not is_suppressed(sentence),
            "is_suppressed keeps its narrow meaning: the module's own sentinel only")
    _expect(not is_bundle_suppressed("") and not is_bundle_suppressed("suppressed"),
            "the empty string is NOT APPLICABLE, and prose about suppression is not a marker")
    token_pct = pd.DataFrame({"n": [FIGURE_SUPPRESSED_TOKEN, "40"], "pct": ["37%", "33%"]})
    _expect(len(export_violations(token_pct, count_cols=["n"],
                                  percentage_columns=["pct"])) == 1,
            "a percentage beside a bundle-token suppressed count is refused")
    sentence_pct = pd.DataFrame({"n": [sentence, "40"], "pct": ["37%", "33%"]})
    _expect(len(export_violations(sentence_pct, count_cols=["n"],
                                  percentage_columns=["pct"])) == 1,
            "a percentage beside a 7.5-sentence suppressed count is refused")
    for hidden in (FIGURE_SUPPRESSED_TOKEN, sentence):
        lone = pd.DataFrame({"a": [hidden], "b": ["40"], "c": ["60"]})
        _expect(len(export_violations(lone, partitions=[["a", "b", "c"]])) == 1,
                "a lone suppressed partition member is refused in every representation")
    ladder = pd.DataFrame({"n_dropped": [""], "n_out": [FIGURE_SUPPRESSED_TOKEN]})
    _expect(export_violations(ladder, partitions=[["n_dropped", "n_out"]]) == [],
            "a row with one member absent partitions nothing and is not a lone suppression")
    n += 8

    # The one exemption, and the three things that keep it narrow.  The frame is the shape of
    # `cs_spine.registry_rows()` -- one row per locked code -- without importing it, because
    # this self-test runs on `disclosure.py` alone.  tests/test_disclosure.py builds the real
    # registry frame and pins the same behaviour on it.
    registry = pd.DataFrame({
        "code": [f"{22600 + i}" for i in range(30)],
        "procedure_class": ["fusion"] * 15 + ["decompression"] * 15,
    })
    _expect(len(export_violations(registry)) == 1, "the registry is refused on its code column")
    _expect(export_violations(registry, specification_columns=["code"]) == [],
            "declaring the code column exempts it from the near-unique class")
    _expect(len(export_violations(registry, specification_columns=["cdoe"])) == 2,
            "a misspelled declaration is itself a violation and grants no exemption")
    dashed = registry.copy()
    dashed.loc[0, "code"] = "22600" + EM_DASH + "22614"
    _expect(len(export_violations(dashed, specification_columns=["code"])) == 1,
            "a declared column is still refused for a banned dash: the exemption is narrow")
    dated = registry.assign(**{"lock date": ["2024-01-01"] * 30})
    _expect(len(export_violations(dated, specification_columns=["code", "lock date"])) == 1,
            "a declared column that is date-like is still refused, and that is deliberate")
    sibling = registry.assign(deficit=[i + 0.5 for i in range(30)],
                              **{"person id": [f"p{i}" for i in range(30)]})
    _expect(len(export_violations(sibling, specification_columns=["code"])) == 3,
            "the exemption is PER COLUMN: declaring code exempts code and nothing beside it")
    n += 6

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "results" / "figures-csv" / "clean.csv"
        row = safe_export(clean, out, kind="figure-csv", exhibit="Figure 2",
                          description="a self-test series", count_cols=["n contributing"])
        _expect(tuple(row) == MANIFEST_COLUMNS, "the manifest row has the contract's columns")
        _expect(row["md5"] == md5_of_bytes(out.read_bytes()), "the digest is of the bytes written")
        _expect(row["file"] == "figures-csv/clean.csv", "the file field is relative to results")
        _expect(row["n_rows"] == 30 and row["n_columns"] == 3, "the shape is the frame's")
        _expect(row["min_disclosed_count"] == 40, "the smallest disclosed count is recorded")
        second = safe_export(clean, out, kind="figure-csv", count_cols=["n contributing"])
        _expect(row["md5"] == second["md5"], "md5 is stable")
        # The data side of the boundary.  A ledger-shaped frame whose counts are four, five
        # and seven digits writes them bare, because a separator in a numeric CSV cell is a
        # data corruption and, unquoted, invents a column.
        ledger = pd.DataFrame({"reason": ["a", "b", "c"],
                               "episodes": [round20(k) for k in (1500, 12480, 1234567)]})
        ledger_path = Path(tmp) / "results" / "ledgers-csv" / "ledger.csv"
        safe_export(ledger, ledger_path, count_cols=["episodes"])
        raw = ledger_path.read_bytes()
        _expect(b"1,500" not in raw and b"1,234,560" not in raw,
                "no thousands separator reaches an exported byte")
        _expect(raw.endswith(b"c,1234560\n"), "an exported count is a bare number")
        # 8.3: "cells written as SUPPRESSED, or as a suppression sentence in a table CSV".
        # Counted on the sentinel this was 0 on every file in the bundle.
        table = pd.DataFrame({"group": ["cervical", "lumbar", "thoracic"],
                              "n": ["60", sentence, sentence],
                              "pct": ["60%", SUPPRESSION_REASONS[1][1],
                                      SUPPRESSION_REASONS[1][1]]})
        table_row = safe_export(table, Path(tmp) / "results" / "tables-csv" / "t1.csv",
                                kind="table-csv", count_cols=["n"],
                                percentage_columns=["pct"])
        _expect(table_row["n_suppressed_cells"] == 4,
                "the manifest counts a suppressed cell in the representation the bundle uses")
        figure = pd.DataFrame({"day": [1, 2], "n": [FIGURE_SUPPRESSED_TOKEN, "40"]})
        figure_row = safe_export(figure, Path(tmp) / "results" / "figures-csv" / "f.csv",
                                 kind="figure-csv", count_cols=["n"])
        _expect(figure_row["n_suppressed_cells"] == 1,
                "and counts the bare token a figure CSV writes")
        n += 4
        # 4.4 again: the field counts "written tokens and not reasons".  This is Figure 4's
        # shape in miniature -- the hidden count written as the token, and the 7.5 sentence
        # written beside it as the prose the renderer prints where the marker would sit --
        # and counting that sentence stamped 220 on a file the contract puts at 176.
        four = pd.DataFrame({"day": ["1", "2"],
                             "n": [FIGURE_SUPPRESSED_TOKEN, "40"],
                             "not_plotted_display": [sentence, ""]})
        _expect(safe_export(four, Path(tmp) / "results" / "figures-csv" / "f4.csv",
                            kind="figure-csv", count_cols=["n"])["n_suppressed_cells"] == 1,
                "a figure CSV counts its token and not the sentence printed beside it")
        _expect(safe_export(four, Path(tmp) / "results" / "tables-csv" / "t4.csv",
                            kind="table-csv", count_cols=["n"])["n_suppressed_cells"] == 2,
                "the SAME frame and the SAME column count the sentence as a table CSV, so the "
                "discriminator is the kind and never the column's name")
        _expect(safe_export(four, Path(tmp) / "results" / "figures-csv" / "f4b.csv",
                            count_cols=["n"])["n_suppressed_cells"] == 1,
                "an undeclared kind does not count a sentence, which is the direction the kind "
                "check of export_violations already takes")
        leaked = pd.DataFrame({"day": ["1"], "n": [SUPPRESSED]})
        _expect(safe_export(leaked, Path(tmp) / "results" / "figures-csv" / "f5.csv",
                            kind="figure-csv", count_cols=["n"])["n_suppressed_cells"] == 1,
                "the sentinel is counted on a figure CSV too: a leak is counted, not waved past")
        n += 4
        blocked = Path(tmp) / "blocked.csv"
        try:
            safe_export(dirty, blocked, count_cols=["n contributing"])
            raise AssertionError("a dirty frame was exported")
        except DisclosureError:
            pass
        _expect(not blocked.exists(), "nothing is written when the export is refused")
        n += 7

    rendered = [SUPPRESSED, n_pct(31, 110), prev(31, 110), mean_sd(range(41)),
                median_iqr(range(41))]
    _expect(all(EM_DASH not in s and MINUS_SIGN not in s for s in rendered),
            "no banned dash reaches a rendered string")
    n += 1

    print("=" * 72)
    print("disclosure.py SELF-TEST: PASS")
    print("=" * 72)
    print(f"  assertions executed        : {n}")
    print(f"  predicate, TRUE count      : disclosable(n), true for 0 and for n above "
          f"{MIN_CELL}")
    print(f"  predicate, RENDERED cell   : is_legal_disclosed_count(cell), true for the "
          f"sentinel, for")
    print(f"                               0, and for positive multiples of {ROUND_BASE}; "
          f"they disagree on {ROUND_BASE}")
    print(f"  suppression floor          : counts 1 to {MIN_CELL} suppress as {SUPPRESSED!r}")
    print( "  predicate, HIDDEN cell     : is_suppressed(cell) is the sentinel only; "
           "is_bundle_suppressed")
    print(f"                               also reads the section 4 token "
          f"{FIGURE_SUPPRESSED_TOKEN!r} and the "
          f"{len(SUPPRESSION_REASONS)} section 7.5")
    print( "                               sentences; the empty string is NOT APPLICABLE "
           "and never hidden")
    print( "  manifest n_suppressed_cells: written TOKENS and not reasons (8.3, 4.4). The "
           "token and the")
    print( "                               sentinel on every kind; a 7.5 sentence on "
           "table-csv only,")
    print( "                               because a figure CSV prints one as prose beside "
           "a hidden cell")
    print(f"  rounding                   : half-UP to multiples of {ROUND_BASE} "
          f"(30 -> {round20(30)}, 50 -> {round20(50)}), integer arithmetic")
    print(f"  a displayed {ROUND_BASE}             : stands on a true count of 21 to 29, never "
          f"{MIN_CELL} and never 30")
    print( "  percentages                : ROUNDED numerator over ROUNDED denominator, zero")
    print( "                               decimals, suppressed with the count")
    print(f"  count rendering, DISPLAY   : render_count, thousands separator "
          f"({render_count(1500)}, {render_count(1234560)}); n_pct,")
    print( "                               prev and safe_show all render through it")
    print( "  count rendering, DATA      : bare, no separator, on every exported byte and")
    print( "                               every value round20 and safe_n return")
    print(f"  near-unique rule           : distinct/rows > {NEAR_UNIQUE_RATIO:.2f} on frames of "
          f"more than {NEAR_UNIQUE_MIN_ROWS} rows")
    print( "  the one exemption          : specification_columns=[...], per column and named,")
    print( "                               clears near-unique and identifier-like and nothing")
    print( "                               else; a date-like column stays refused")
    print(f"  export float format        : {FLOAT_FORMAT}, index dropped, newline pinned")
    print( "  export returns             : the MANIFEST.csv row, md5 included")
    print( "  wrote                      : nothing outside a temporary directory")


if __name__ == "__main__":
    _run_self_test()
