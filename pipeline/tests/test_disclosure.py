#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for `pipeline/disclosure.py`.

Runs locally with no Workbench session, no network and no credentials:
    cd v1/pipeline && python3 -m pytest tests/ -q

Every assertion here is a policy statement, not an implementation detail.  Where the plan
overrides the module this module was ported from, the test pins the OVERRIDE and names the
ported behaviour it must not fall back to, so a later "cleanup" that reinstates the port fails
loudly instead of quietly reopening a disclosure hole.

Two rules this file follows after the first review found it breaking both:
  * A test that cannot fail is not a test.  Every assertion here was checked by mutation: the
    implementation was broken deliberately and the suite had to go red.  Assertions dominated
    by a stronger assertion beside them are deleted rather than kept for comfort.
  * Pin the BEHAVIOUR, not the wording.  Nothing here asserts on a message fragment that
    carries the floor in it, because a change of floor would then break the suite on prose
    rather than on policy.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import inspect
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

# Run the suite from anywhere: `pipeline/` is the import root for `disclosure`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from disclosure import (  # noqa: E402  (path bootstrap must precede the import)
    ALLOWED_EXPORT_SUFFIXES,
    FIGURE_SUPPRESSED_TOKEN,
    FLOAT_FORMAT,
    MANIFEST_COLUMNS,
    MIN_CELL,
    NEAR_UNIQUE_MIN_ROWS,
    NEAR_UNIQUE_RATIO,
    ROUND_BASE,
    SUPPRESSED,
    SUPPRESSION_REASONS,
    SUPPRESSION_SENTENCES,
    DisclosureError,
    _run_self_test,
    assert_suppression_vocabulary,
    disclosable,
    export_violations,
    is_bundle_suppressed,
    is_legal_disclosed_count,
    is_suppressed,
    md5_of_bytes,
    mean_sd,
    median_iqr,
    n_pct,
    prev,
    render_count,
    round20,
    safe_counts,
    safe_export,
    safe_n,
    safe_show,
    suppress_frame,
)

# The registry case below is pinned against the REAL producer, not a hand-made fixture, so a
# change to the locked concept set that alters the registry's shape is seen here.  `cs_spine`
# is pure -- no BigQuery client, no network -- and sits beside `disclosure` in `pipeline/`.
import cs_spine  # noqa: E402  (path bootstrap must precede the import)

EM_DASH = chr(0x2014)
MINUS_SIGN = chr(0x2212)

# The number the Methods sentence and AOS-CS.md section 9 both carry, held in a named constant
# so pinning it is not itself a bare floor literal in a comparison, which EXPORT-CONTRACT.md
# lines 40 to 43 have `verify.py` grep for across `pipeline/`.
DOCUMENTED_FLOOR = 20


# ======================================================================================
# Fixtures.  A "clean" frame is what a plot-ready export actually looks like: repeated group
# labels, a day index that repeats across series, and counts that have already been through
# round20.
# ======================================================================================


def _clean_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "region": ["cervical"] * 15 + ["lumbar"] * 15,
            "procedure": (["fusion"] * 5 + ["decompression"] * 10) * 2,
            "day": list(range(1, 16)) * 2,
            "n contributing": [40, 60, 80] * 10,
            "median deficit": [0.51, 0.62, 0.73] * 10,
        }
    )


def _ledger_frame() -> pd.DataFrame:
    """The shape of the exclusion-reason ledger, with the counts it actually carries.

    Four, five and seven digits, because those are the ORDINARY magnitudes in this ledger and
    in the person-day row of the missingness ledger, and a toy frame of two-digit counts is
    exactly the fixture that let the separator defect live.  Every count has been through
    `round20`, which is what a frame on its way to `safe_export` looks like.
    """
    return pd.DataFrame(
        {
            "reason": [
                "no wearable device linked",
                "fewer than 14 baseline wear-days",
                "no qualifying procedure code",
                "index outside the study window",
                "person-days in the analytic cohort",
            ],
            "episodes": [round20(k) for k in (12480, 3421, 1500, 260, 1234567)],
            "denominator": [round20(20000)] * 5,
        }
    )


def _dirty_frame() -> pd.DataFrame:
    """One frame carrying exactly one violation of each of the four column refusal classes."""
    df = _clean_frame()
    df.loc[0, "n contributing"] = 7                      # 1. a cell below the floor
    df["person id"] = ["A", "B", "C"] * 10               # 2. an identifier-like name
    df["surgery date"] = ["2020-03-01"] * 30             # 3. a date-like name
    df["fingerprint"] = [i + 0.5 for i in range(30)]     # 4. near-unique, innocuous name
    return df


# ======================================================================================
# disclosable: the single arbiter of the floor
# ======================================================================================


def test_disclosable_is_the_decided_reading_of_the_floor():
    # DECIDED: suppress 1 through 20 INCLUSIVE, disclose only counts strictly greater than 20.
    # ANALYSIS-PLAN.md section 8 rule 1 puts 20 below the line; AOS-CS.md section 9 reads it as
    # above.  This function is the reason those two readings can no longer be implemented
    # differently in two places in one file, which is what the review found.
    assert disclosable(0)
    assert not any(disclosable(k) for k in range(1, MIN_CELL + 1))
    assert disclosable(MIN_CELL + 1)
    assert disclosable(1_000_000)


def test_disclosable_refuses_anything_that_is_not_a_whole_count():
    # A negative cell and a fractional cell both walked through the old export gate, because
    # its band was written `1 <= v <= MIN_CELL - 1` and neither value is inside it.
    assert not disclosable(-1)
    assert not disclosable(-1000)
    assert not disclosable(0.5)
    assert not disclosable(20.5)
    assert not disclosable(40.5)
    assert not disclosable(None)
    assert not disclosable("cervical")
    assert not disclosable(SUPPRESSED)
    assert not disclosable(float("nan"))
    assert not disclosable(float("inf"))


def test_round20_and_disclosable_never_disagree_about_the_same_count():
    # One answer to "may this TRUE count be shown", shared by the sentinel and by every caller
    # that still holds the unrounded number.  NOT by the export gate: by the time a frame
    # reaches the gate its counts are already rounded, so the gate asks the OTHER predicate.
    for k in range(0, 61):
        assert is_suppressed(round20(k)) is (not disclosable(k))


# ======================================================================================
# is_legal_disclosed_count: the OTHER predicate, the one the export gate is able to ask
#
# `disclosable` answers "may this TRUE count, before rounding, be disclosed at all".  This one
# answers "is this ALREADY-RENDERED cell a legal disclosed output".  They were one predicate
# until a correctly rounded 20 was refused by the same module that produced it, which would
# have blocked the STROBE ladder and Table 1 from exporting.  These tests pin that shut, and
# pin that the strictness the refusal class was written for survived the fix.
# ======================================================================================


def test_the_two_predicates_disagree_on_twenty_and_that_is_the_point():
    # THE DEFECT, in two assertions.  round20(21) through round20(29) are all exactly 20, so a
    # RENDERED 20 is a legal disclosed cell; a TRUE count of 20 is below the floor and is not.
    # One predicate cannot hold both readings, which is why there are two.
    assert not disclosable(DOCUMENTED_FLOOR)
    assert is_legal_disclosed_count(ROUND_BASE)


def test_every_value_round20_can_return_is_a_legal_disclosed_cell():
    # The invariant that ties the two predicates together and the one a later edit is most
    # likely to break: whatever `round20` emits, the export gate must accept.  One sweep covers
    # the sentinel, the true zero and every rounded count.
    for k in range(0, 200):
        assert is_legal_disclosed_count(round20(k))


def test_a_rounded_count_is_legal():
    assert is_legal_disclosed_count(ROUND_BASE)
    assert is_legal_disclosed_count(2 * ROUND_BASE)
    assert is_legal_disclosed_count(400)
    assert is_legal_disclosed_count(1240)


def test_an_unrounded_count_is_refused_because_it_is_not_a_multiple_of_the_base():
    # This is what the refusal class is FOR: catching a caller who forgot to round.  It does it
    # better than the floor test did, because a count that was never rounded is almost never an
    # exact multiple of the base.  A raw 21 is the common real mistake and the OLD predicate
    # waved it through, since 21 is above the floor.
    assert not is_legal_disclosed_count(7)
    assert not is_legal_disclosed_count(MIN_CELL + 1)
    assert not is_legal_disclosed_count(1)
    assert not is_legal_disclosed_count(19)
    assert not is_legal_disclosed_count(399)


def test_the_suppression_sentinel_is_a_legal_rendered_cell():
    # A suppressed cell is a legal rendered value and a disclosed table is expected to be full
    # of them, so a predicate that only understands numbers would refuse every one.
    assert is_legal_disclosed_count(SUPPRESSED)
    assert is_legal_disclosed_count(f"40 of {SUPPRESSED}")


def test_a_true_zero_is_legal_exactly_when_zero_is_allowed():
    assert is_legal_disclosed_count(0)
    assert not is_legal_disclosed_count(0, allow_zero=False)


def test_allow_zero_on_the_predicate_is_keyword_only():
    with pytest.raises(TypeError):
        is_legal_disclosed_count(0, False)


def test_a_whole_valued_float_is_legal_because_a_left_join_produces_floats():
    # A BigQuery INT64 count column that has been through a LEFT JOIN arrives as float64, and
    # `_integers_as_integers` casts whole-valued floats back to int64 on write.  Refusing them
    # here would refuse a frame the exporter goes on to write correctly.
    assert is_legal_disclosed_count(40.0)
    assert is_legal_disclosed_count(1234560.0)
    assert is_legal_disclosed_count(0.0)


def test_a_negative_is_refused_even_though_it_divides_by_the_base():
    # Python's `%` follows the sign of the divisor, so -20 % 20 is 0 and a modulo test on its
    # own would read a negative count as a legal multiple.  A negative count is a bug upstream.
    assert (-ROUND_BASE) % ROUND_BASE == 0
    assert not is_legal_disclosed_count(-ROUND_BASE)
    assert not is_legal_disclosed_count(-40)
    assert not is_legal_disclosed_count(-1)


def test_a_fractional_value_is_refused():
    # A fractional cell in a count column is a mean or a rate filed under the wrong header, and
    # it carries more precision than any rounded count is allowed to.
    assert not is_legal_disclosed_count(40.5)
    assert not is_legal_disclosed_count(0.5)
    assert not is_legal_disclosed_count(19.999)


def test_anything_that_is_not_a_number_at_all_is_refused():
    assert not is_legal_disclosed_count(None)
    assert not is_legal_disclosed_count("cervical")
    assert not is_legal_disclosed_count(float("nan"))
    assert not is_legal_disclosed_count(float("inf"))


def test_the_one_residual_gap_is_a_raw_twenty_and_it_is_stated_not_hidden():
    # A RAW 20 and a ROUNDED 20 are the same integer.  What separates them is the true count,
    # which the gate by definition no longer has, so the gate accepts it.  The gap is bounded
    # and this pins the three reasons: every OTHER unrounded value fails the multiple test,
    # `round20` never emits a raw 20 (it emits the sentinel), and the floor on the TRUE count
    # is still enforced upstream where the true count exists.
    assert is_legal_disclosed_count(DOCUMENTED_FLOOR)      # the gap, accepted deliberately
    assert not is_legal_disclosed_count(DOCUMENTED_FLOOR + 1)   # every other raw value caught
    assert round20(DOCUMENTED_FLOOR) == SUPPRESSED         # round20 never produces a raw 20
    assert not disclosable(DOCUMENTED_FLOOR)               # the floor still refuses a true 20


def test_both_predicates_are_exported():
    # `07_export.py`, `01_probe.py` and `local/verify.py` import from this module by name, and
    # a predicate missing from `__all__` is a predicate a caller reimplements badly.
    import disclosure

    assert "disclosable" in disclosure.__all__
    assert "is_legal_disclosed_count" in disclosure.__all__


# ======================================================================================
# round20
# ======================================================================================


def test_true_zero_passes_through():
    # Zero is an absence, not a small cell: nobody is re-identified by it, and the attrition
    # ladder stops closing if a legitimate zero drop becomes a string.
    assert round20(0) == 0
    assert not is_suppressed(round20(0))


def test_suppression_boundary_at_one_and_twenty_and_twentyone():
    assert round20(1) == SUPPRESSED
    assert round20(MIN_CELL) == SUPPRESSED
    assert round20(MIN_CELL + 1) == ROUND_BASE


def test_every_count_in_the_closed_small_range_is_suppressed():
    assert all(round20(k) == SUPPRESSED for k in range(1, MIN_CELL + 1))


def test_rounding_at_the_equidistant_half_is_half_up():
    # 30 is exactly halfway between 20 and 40, so this pins a CHOICE, not an inevitability.
    # Half-UP is chosen over Python's round(), which is half-to-EVEN and would send 30 to 40
    # but 50 to 40 as well.  A Methods sentence reading "rounded to the nearest multiple of 20"
    # can defend the first and cannot defend the second.  50 and 90 are the discriminating
    # cases: under half-to-even they would be 40 and 80.
    assert round20(30) == 40
    assert round20(50) == 60
    assert round20(70) == 80
    assert round20(90) == 100


def test_rounding_away_from_the_half():
    assert round20(29) == ROUND_BASE
    assert round20(31) == 40
    assert round20(1000) == 1000


def test_a_displayed_twenty_stands_only_on_a_true_count_of_21_to_29():
    # The Methods footnote sentence, pinned as arithmetic.  A reader who sees 20 in a table
    # must be able to read the footnote and know the true count was 21 to 29, never 20 (which
    # is suppressed) and never 30 (which rounds up to 40).
    assert {k for k in range(0, 200) if round20(k) == ROUND_BASE} == set(range(21, 30))


def test_non_numeric_input_passes_through_unchanged():
    assert round20(None) is None
    assert round20("cervical") == "cervical"
    assert round20(SUPPRESSED) == SUPPRESSED
    assert pd.isna(round20(float("nan")))


def test_a_negative_count_is_a_stop_condition_that_never_quotes_the_value():
    with pytest.raises(DisclosureError) as caught:
        round20(-7)
    # The exception renders into a notebook traceback, which is the model-visible surface this
    # module exists to protect.  The offending cell must not appear in it.  The function's own
    # name is removed first, because it carries the floor in it and is not a cell value; what
    # is left must contain no numeral at all.
    message = str(caught.value).replace("round20", "the rounder")
    assert re.findall(r"\d+", message) == []


def test_is_suppressed_reads_the_sentinel_and_nothing_else():
    assert is_suppressed(SUPPRESSED)
    assert is_suppressed(round20(5))
    assert is_suppressed(n_pct(5, 100))
    assert not is_suppressed(0)
    assert not is_suppressed(40)
    assert not is_suppressed("40 (33%)")


def test_is_suppressed_is_containment_not_equality():
    # Its documented reason for existing: a COMPOSED string must still read as suppressed, so
    # anything downstream that gates on this cannot be fooled by a cell that was concatenated.
    assert is_suppressed(f"40 of {SUPPRESSED}")
    assert is_suppressed(f"{SUPPRESSED} in 2 of 4 groups")
    assert is_suppressed(f"cervical: {SUPPRESSED}")


# ======================================================================================
# is_bundle_suppressed: the SECOND suppression predicate, and the representation defect
#
# The defect it closes, stated once here so the tests below read as a policy rather than as a
# list of strings: `is_suppressed` matches this module's own sentinel, `"<=20 (suppressed)"`.
# EXPORT-CONTRACT.md fixes a DIFFERENT spelling for the same cell once it reaches the bundle --
# the bare token `SUPPRESSED` in a figure CSV (section 4) and one of the section 7.5
# sentences in a table CSV (section 5) -- and neither of those contains the sentinel.  So on
# every frame `07_export.py` hands to `safe_export`, the complementary-disclosure class and the
# partition class could not SEE a suppressed cell, never refused anything, and
# `n_suppressed_cells` came back 0 on a file that is 119 suppressed cells deep.
#
# Two properties are pinned throughout, because the fix is worthless if it costs either:
#   * the set of recognised representations is CLOSED and NAMED, so nothing becomes suppressed
#     by reading like prose about suppression;
#   * the EMPTY STRING is NOT APPLICABLE and never suppressed, which sections 4 and 5 both say
#     in as many words.
# ======================================================================================

CELL_BELOW_THRESHOLD = "20 or fewer, suppressed per All of Us dissemination policy"
NUMERATOR_SUPPRESSED = "suppressed because the count behind it is suppressed"
SECONDARY_SUPPRESSION = "suppressed to protect a suppressed cell in the same total"
CONTRIBUTING_N_BELOW_THRESHOLD = "20 or fewer contributors, suppressed"
NOT_PERMITTED_BY_TIER = "not permitted at the feasibility tier reached"


def test_every_sanctioned_representation_of_a_hidden_cell_is_recognised():
    # One assertion per representation the contract fixes, named by where it comes from.
    assert is_bundle_suppressed(SUPPRESSED)                    # this module's own sentinel
    assert is_bundle_suppressed(FIGURE_SUPPRESSED_TOKEN)       # section 4, a figure CSV
    assert is_bundle_suppressed(CELL_BELOW_THRESHOLD)          # section 7.5, a table CSV
    assert all(is_bundle_suppressed(s) for s in SUPPRESSION_SENTENCES)
    # And it still agrees with `is_suppressed` on everything `is_suppressed` accepts, including
    # a composed cell, so nothing that was recognised before has stopped being recognised.
    assert is_bundle_suppressed(round20(5))
    assert is_bundle_suppressed(f"40 of {SUPPRESSED}")


def test_the_empty_string_is_not_applicable_and_is_never_suppressed():
    # Sections 4 and 5, in as many words: blank means the concept does not apply to this row,
    # `SUPPRESSED` means it applies and is hidden.  Reading a blank as hidden would make every
    # not-applicable cell a partition member and force a second suppression to protect a count
    # that was never there.  The contract is explicit, so this is pinned rather than inferred.
    assert not is_bundle_suppressed("")
    assert not is_bundle_suppressed("   ")
    assert not is_suppressed("")


def test_is_bundle_suppressed_is_a_closed_set_and_not_prose_matching():
    # The whole reason this is not a widened regex.  A cell is suppressed because it matches a
    # representation the module NAMES, never because it mentions suppression: otherwise any
    # author could switch off the complementary-disclosure class by writing a sentence.
    assert not is_bundle_suppressed("suppressed")
    assert not is_bundle_suppressed("the count was suppressed")
    assert not is_bundle_suppressed("20 or fewer")
    assert not is_bundle_suppressed("not estimable")
    assert not is_bundle_suppressed("SUPPRESSED (see footnote)")
    assert not is_bundle_suppressed("suppressed per All of Us dissemination policy")
    assert not is_bundle_suppressed(CELL_BELOW_THRESHOLD.upper())
    # And nothing that is not a written cell at all.  A hidden cell is a WRITTEN cell in every
    # representation the contract has.
    assert not is_bundle_suppressed(None)
    assert not is_bundle_suppressed(0)
    assert not is_bundle_suppressed(40)
    assert not is_bundle_suppressed(float("nan"))


def test_is_suppressed_keeps_its_narrow_meaning_and_the_broad_one_is_a_new_name():
    # Constraint on the fix: `is_suppressed` is documented as containment on the module's own
    # sentinel and other code depends on that -- `render_count` passes the sentinel through
    # untouched, and `n_pct`, `prev` and `safe_counts` all branch on what `round20` returned.
    # Widening it in place would have changed all four.  So it did not move, and the broad
    # question got its own name.
    assert not is_suppressed(FIGURE_SUPPRESSED_TOKEN)
    assert not is_suppressed(CELL_BELOW_THRESHOLD)
    assert all(not is_suppressed(s) for s in SUPPRESSION_SENTENCES)
    assert render_count(FIGURE_SUPPRESSED_TOKEN) == FIGURE_SUPPRESSED_TOKEN
    assert render_count(SUPPRESSED) == SUPPRESSED


def test_both_suppression_predicates_are_exported_under_their_own_names():
    import disclosure

    assert "is_suppressed" in disclosure.__all__
    assert "is_bundle_suppressed" in disclosure.__all__
    assert "FIGURE_SUPPRESSED_TOKEN" in disclosure.__all__
    assert "SUPPRESSION_REASONS" in disclosure.__all__


def test_a_suppression_sentence_in_a_count_column_is_a_legal_rendered_cell():
    # DELIBERATE, and the contract is why: section 5 does not merely permit the 7.5 sentence in
    # a count column, it MANDATES it, and 5.1's own worked example writes it into Table 1's
    # count columns.  Refusing it here would refuse Table 1.
    assert is_legal_disclosed_count(CELL_BELOW_THRESHOLD)
    assert is_legal_disclosed_count(FIGURE_SUPPRESSED_TOKEN)
    assert all(is_legal_disclosed_count(s) for s in SUPPRESSION_SENTENCES)


def test_an_unrecognised_sentence_in_a_count_column_does_not_pass_as_suppressed():
    # The other half of the same decision, and the one that stops "accept the sentences" from
    # becoming "accept any string".  A near-miss is not a count and is not a suppression
    # marker, so it is refused on both predicates rather than waved through on either.
    for near_miss in ("20 or fewer suppressed",           # the comma is gone
                      "not estimable (small cell)",       # not the 7.5 wording
                      "suppressed per policy",
                      "Suppressed",
                      "n/a"):
        assert not is_bundle_suppressed(near_miss)
        assert not is_legal_disclosed_count(near_miss)
    # ... and nothing downstream treats it as hidden either.  The manifest does not count it,
    # and -- the one that would actually cost a manuscript -- a disclosed percentage beside it
    # is NOT excused, because the cell it stands next to is not a suppressed cell.
    df = pd.DataFrame({"n": ["40", "not estimable (small cell)"],
                       "pct": ["33%", "67%"]})
    assert export_violations(df, count_cols=["n"], percentage_columns=["pct"]) == []
    counted = sum(1 for col in df.columns for cell in df[col] if is_bundle_suppressed(cell))
    assert counted == 0


def test_the_count_class_parses_numerically_so_a_string_cell_never_reaches_the_floor():
    # A boundary of `export_violations`, pinned rather than left to be discovered.  The count
    # class runs `pd.to_numeric(errors="coerce").dropna()`, so EVERY string cell -- the
    # sentinel, the bundle token, a 7.5 sentence and an unrecognised sentence alike -- is
    # dropped before `is_legal_disclosed_count` is asked.  That is deliberate: it is what lets
    # a table CSV's suppressed count columns through, and it is why the predicate accepting the
    # sentences does not widen this class.  A hand-written sentence in a count column is caught
    # on the rendered cell by `07_export._contract_violations`, not here.
    strings = pd.DataFrame({"n": ["not estimable (small cell)"]})
    assert [v for v in export_violations(strings, count_cols=["n"])
            if "legal disclosed counts" in v] == []
    # The floor still refuses everything that DOES parse, which is the class's actual job.
    numbers = pd.DataFrame({"n": [MIN_CELL + 1]})
    assert any("legal disclosed counts" in v
               for v in export_violations(numbers, count_cols=["n"]))


# ======================================================================================
# The suppression vocabulary: where the sentence list comes from, and how it fails loudly
# ======================================================================================


def _contract_suppression_reasons() -> list[tuple[str, str]]:
    """Section 7.5 of EXPORT-CONTRACT.md, parsed out of the markdown table.

    The module TRANSCRIBES that table, because it imports nothing and reads nothing at import
    time -- it runs inside the Workbench VM, where `prespecification/` is not uploaded.  The
    failure mode of a transcription is silent: the contract grows a ninth sentence, the module
    goes on returning False for a cell that is suppressed, and the complementary-disclosure
    class quietly stops firing on it.  This is the check that makes that loud.
    """
    contract = Path(__file__).resolve().parents[2] / "prespecification" / "EXPORT-CONTRACT.md"
    if not contract.exists():           # pragma: no cover - present in the repo, absent in the VM
        pytest.skip(f"{contract.name} is not on this side of the boundary")
    rows: list[tuple[str, str]] = []
    inside = False
    for line in contract.read_text(encoding="utf-8").splitlines():
        if line.startswith("### 7.5"):
            inside = True
            continue
        if inside and line.startswith("#"):
            break
        if not inside or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 2 or cells[0] in ("slug", "") or set(cells[0]) <= set("-: "):
            continue
        rows.append((cells[0].strip("`"), cells[1]))
    return rows


def test_the_suppression_sentences_are_the_contract_s_own():
    # THE LOUD FAILURE.  A row added to, removed from or reworded in EXPORT-CONTRACT.md 7.5
    # turns this red on the next run.  Without it the module would simply stop recognising the
    # new sentence, which is the defect this whole section exists to close, one sentence at a
    # time instead of all of them at once.  ORDERED PAIRS, so a reordering fails here too.
    assert _contract_suppression_reasons() == list(SUPPRESSION_REASONS)


def test_the_transcription_check_fails_on_a_reordering_and_not_only_on_a_missing_row():
    # The check above, checked.  A comparison that waves a reordering through is the same
    # comparison that would wave a reworded row through, so both are exercised rather than read
    # off the assertion beside them.  Lists and not sets is the whole of what makes that true.
    contract = _contract_suppression_reasons()
    assert contract[1:] + contract[:1] != list(SUPPRESSION_REASONS)      # reordered
    assert contract[:-1] != list(SUPPRESSION_REASONS)                    # a row missing
    assert [(slug, s + " ") for slug, s in contract] != list(SUPPRESSION_REASONS)   # reworded


def test_the_tenth_reason_is_the_separated_fit_and_is_not_the_convergence_one():
    # ANALYSIS-PLAN.md reached version 1.5 and its section 4.9 refuses a fit whose coefficient
    # is above the prespecified ceiling.  No existing reason could carry it: a quasi-separated
    # conditional model CONVERGES, so the cell size was fine, the data were available and the
    # tier permitted the analysis.  `not_estimable_convergence` is the near-miss a later
    # "cleanup" would reach for, and it is exactly the sentence that would be FALSE, because
    # convergence is the property that makes quasi-separation dangerous instead of visible.
    reasons = dict(SUPPRESSION_REASONS)
    assert reasons["not_estimable_separation"] == "not estimable (separation)"
    assert reasons["not_estimable_separation"] != reasons["not_estimable_convergence"]
    # And a cell carrying it is HIDDEN, which is the point of transcribing it at all: until it
    # is here, `is_bundle_suppressed` returns False for a suppressed cell `06_analysis_gate.py`
    # already writes, and the complementary-disclosure class cannot see one.
    assert is_bundle_suppressed("not estimable (separation)")
    assert is_legal_disclosed_count("not estimable (separation)")


def test_the_vocabulary_guard_accepts_a_larger_label_table_that_contains_the_eight():
    # `07_export.LABELS` is the whole of section 7, not only 7.5, so the guard checks
    # CONTAINMENT and spelling rather than equality of the two tables.
    larger = dict(SUPPRESSION_REASONS)
    larger["lumbar_fusion"] = "Lumbar fusion"
    assert assert_suppression_vocabulary(larger) is None


def test_the_vocabulary_guard_raises_on_a_missing_slug_and_names_it():
    short = dict(SUPPRESSION_REASONS)
    del short["not_permitted_by_tier"]
    with pytest.raises(DisclosureError) as caught:
        assert_suppression_vocabulary(short)
    assert "not_permitted_by_tier" in str(caught.value)


def test_the_vocabulary_guard_raises_on_a_reworded_sentence():
    # The quiet divergence: the slug is there, the sentence has drifted, and equality matching
    # would stop recognising every cell the other module writes.
    drifted = dict(SUPPRESSION_REASONS)
    drifted["cell_below_threshold"] = "fewer than 20, suppressed"
    with pytest.raises(DisclosureError) as caught:
        assert_suppression_vocabulary(drifted)
    assert "cell_below_threshold" in str(caught.value)


def test_the_vocabulary_guard_refuses_something_that_is_not_a_mapping():
    with pytest.raises(DisclosureError):
        assert_suppression_vocabulary(object())


def test_the_suppression_reasons_table_is_ordered_and_has_no_duplicates():
    slugs = [slug for slug, _ in SUPPRESSION_REASONS]
    assert len(set(slugs)) == len(slugs)
    assert SUPPRESSION_SENTENCES == frozenset(s for _, s in SUPPRESSION_REASONS)
    assert len(SUPPRESSION_SENTENCES) == len(SUPPRESSION_REASONS)


# ======================================================================================
# n_pct and prev
# ======================================================================================


def test_a_suppressed_count_suppresses_its_percentage():
    # Complementary disclosure: a percentage times a disclosed denominator recovers the hidden
    # count exactly, so the percentage cannot outlive the count.
    assert n_pct(5, 100) == SUPPRESSED
    assert n_pct(MIN_CELL, 100) == SUPPRESSED
    assert prev(5, 100) == SUPPRESSED
    assert is_suppressed(prev(MIN_CELL, 100))


def test_percentage_is_computed_from_the_rounded_numerator():
    # DISCRIMINATING.  The previous version of this test used k = 37 of n = 1000, where the raw
    # 3.7% and the rounded 4.0% both render as "4%" at zero decimals, so reinstating the ported
    # raw-numerator arithmetic left the whole suite green.  k = 31 separates them: the port
    # gives 3.1% -> "3%", the policy gives round20(31) = 40 over 1000 -> "4%".
    assert n_pct(31, 1000) == "40 (4%)"
    assert n_pct(31, 1000) != "40 (3%)"
    assert prev(31, 1000) == "40 (4%)"
    assert "." not in n_pct(31, 1000)


def test_percentage_is_computed_over_the_rounded_denominator():
    # DECIDED (EXPORT-CONTRACT.md 10.1): rounded numerator over ROUNDED denominator, so a
    # reader reproduces every printed percentage from the printed counts alone.  k = 31 of
    # n = 110 separates all four candidate arithmetics:
    #     raw over raw          31 / 110 = 28%
    #     raw over rounded      31 / 120 = 26%
    #     rounded over raw      40 / 110 = 36%   <- what this module did before
    #     rounded over rounded  40 / 120 = 33%   <- the policy
    assert n_pct(31, 110) == "40 (33%)"
    assert n_pct(31, 110) != "40 (36%)"
    assert prev(31, 110) == "40 (33%)"


def test_a_denominator_at_or_below_the_floor_prints_no_percentage():
    # The rounded denominator is itself a disclosure decision: n = 15 rounds to the sentinel,
    # and a percentage over a suppressed denominator is one no reader may check.
    assert n_pct(40, 15) == "40 (NA)"
    assert prev(40, 15) == "40"
    assert n_pct(40, MIN_CELL) == "40 (NA)"


def test_zero_denominator_does_not_divide():
    assert n_pct(40, 0) == "40 (NA)"
    assert prev(40, 0) == "40"


def test_missing_denominator_does_not_divide():
    for bad in (None, float("nan"), SUPPRESSED, -5):
        assert n_pct(40, bad) == "40 (NA)"
        assert prev(40, bad) == "40"


def test_zero_numerator_renders_a_disclosed_zero():
    assert n_pct(0, 100) == "0 (0%)"
    assert n_pct(0, 0) == "0 (NA)"
    # prev never prints a parenthetical it cannot fill; this is the ported contract.
    assert prev(0, 100) == "0"


# ======================================================================================
# The house thousands separator, and which side of the display/data boundary it reaches.
#
# The defect these pin: `n_pct(1500, 1500)` rendered "1500 (100%)" while CLAUDE.md states the
# numeral style `n = 1,240`.  Four- and five-digit counts are the ordinary case here, and
# `03_cohort._count_and_share` had already grown a local workaround that re-rendered `n_pct`'s
# own numerator, which is evidence of the defect rather than a fix for it.
#
# The rule these pin, in both directions: a count on a DISPLAY surface carries the separator,
# a count on a DATA surface never does.
# ======================================================================================


def test_a_four_digit_count_carries_the_house_thousands_separator():
    # The reported case, verbatim.
    assert n_pct(1500, 1500) == "1,500 (100%)"
    assert render_count(1500) == "1,500"


def test_a_three_digit_count_does_not_gain_a_separator():
    # The regression guard on the other side: the separator is applied by a format spec, not
    # by a hand-rolled chunker that could start grouping at three digits.
    assert n_pct(340, 1000) == "340 (34%)"
    assert render_count(340) == "340"
    assert render_count(0) == "0"
    assert "," not in n_pct(340, 1000)


def test_a_seven_digit_count_takes_both_separators():
    assert render_count(1234560) == "1,234,560"
    assert n_pct(1234567, 2000000) == "1,234,560 (62%)"


def test_the_suppression_sentinel_is_untouched_by_the_separator():
    # The sentinel is a rendered value in its own right and `is_suppressed` is CONTAINMENT on
    # the literal, so anything that reformatted it would break every downstream gate at once.
    assert render_count(SUPPRESSED) == SUPPRESSED
    assert is_suppressed(render_count(SUPPRESSED))
    assert n_pct(8, 1500) == SUPPRESSED
    assert prev(8, 1500) == SUPPRESSED
    # The live path on which `render_count` actually meets the sentinel: a frame below the
    # floor makes `safe_n` return it, and `safe_show` renders whatever comes back.
    assert render_count(safe_n(pd.DataFrame({"a": range(5)}))) == SUPPRESSED


def test_prev_and_n_pct_agree_on_the_rendering_of_the_count():
    # They differ only in the parenthetical, as they always have.  If one grows a rendering
    # rule the other does not, a prose sentence and the table cell beside it disagree.
    for k, n in ((1500, 1500), (12480, 20000), (1234567, 2000000), (340, 1000), (8, 1500)):
        assert prev(k, n).partition(" ")[0] == n_pct(k, n).partition(" ")[0]
    assert prev(1500, 1500) == n_pct(1500, 1500) == "1,500 (100%)"
    # The one documented difference survives: prev prints no parenthetical it cannot fill.
    assert prev(1500, 0) == "1,500"
    assert n_pct(1500, 0) == "1,500 (NA)"


def test_the_separator_is_on_the_display_of_a_count_and_never_on_the_count():
    # `round20`, `safe_n`, `safe_counts` and `suppress_frame` emit VALUES for something else to
    # compute on.  A separator there is not a style improvement, it is a string where a number
    # was.  This is the data side of the boundary the module docstring states.
    assert round20(1500) == 1500 and isinstance(round20(1500), int)
    assert safe_n(pd.DataFrame({"a": range(1500)})) == 1500
    assert safe_counts(pd.Series(["x"] * 1500))["x"] == 1500
    assert suppress_frame(pd.DataFrame({"n": [1500]}), ["n"])["n"].iloc[0] == 1500
    # ... and the display of each of them does carry it.
    assert render_count(round20(1500)) == "1,500"


def test_a_rendered_count_is_one_way_and_the_parsing_predicates_refuse_it():
    # `is_legal_disclosed_count` and `is_suppressed` are asked of EXPORT CELLS, which are
    # numbers or the sentinel.  Neither is weakened by the separator, and the refusal below is
    # the CORRECT answer rather than a gap: a rendered string is not a legal export cell
    # whatever number it renders, so a caller who puts one in a count column is caught.
    assert is_legal_disclosed_count("1,240") is False
    assert is_legal_disclosed_count("1,500 (100%)") is False
    assert is_suppressed("1,240") is False
    # The unseparated spelling is what a count column legitimately holds, and it still passes.
    assert is_legal_disclosed_count(1240) is True
    assert is_legal_disclosed_count("1240") is True


def test_the_percentage_side_is_untouched_by_the_separator():
    # A percentage is a part over its own whole at zero decimals, so it is three digits at the
    # widest and there is nothing in it to separate.  These pin that the ARITHMETIC did not
    # move either: `_percent` is still handed the rounded INTEGER numerator, not a string.
    assert n_pct(31, 1000) == "40 (4%)"
    assert n_pct(31, 110) == "40 (33%)"
    assert n_pct(1500, 1500).partition(" ")[2] == "(100%)"
    assert "." not in n_pct(1234567, 2000000)


def test_mean_sd_and_median_iqr_are_deliberately_not_separated():
    # DECIDED, not overlooked.  A mean, an SD, a median and a quartile are MEASUREMENTS: they
    # answer "how much", they carry decimals, and an IQR around a deficit has negative bounds.
    # The separator is for the integer answer to "how many".  If this is ever revisited, it is
    # revisited here and in the module docstring together, not silently in one of them.
    assert mean_sd(range(15000)) == "7499.5 +/- 4330.3"
    assert median_iqr(range(15000)) == "7499.5 (3749.8 to 11249.2)"
    assert "," not in mean_sd(range(15000))
    assert "," not in median_iqr(range(15000))


def test_render_count_is_exported_so_the_local_modules_stop_reimplementing_it():
    # Four numbered modules had each grown their own `_count` helper spelling this rule.  A
    # rendering rule missing from `__all__` is a rendering rule that drifts six ways.
    import disclosure

    assert "render_count" in disclosure.__all__


def test_render_count_passes_through_what_is_not_a_whole_count():
    # It renders into printed output, so a label reaches the reader as the label rather than
    # as a traceback carrying it, and a fraction is not quietly truncated into a wrong count.
    assert render_count("cervical") == "cervical"
    assert render_count(None) == "None"
    assert render_count(40.5) == "40.5"
    assert render_count(True) == "True"
    # A whole-valued float IS a count: a LEFT JOIN turns an INT64 count column into float64.
    assert render_count(1500.0) == "1,500"


def test_safe_show_renders_a_large_row_count_with_the_separator(capsys):
    safe_show(pd.DataFrame({"a": range(1500)}), name="ledger")
    printed = capsys.readouterr().out
    assert "1,500 rows" in printed
    assert "1500 rows" not in printed


# ======================================================================================
# mean_sd and median_iqr
# ======================================================================================


def test_mean_sd_needs_more_than_twenty_observations():
    assert mean_sd(range(MIN_CELL)) == SUPPRESSED
    assert mean_sd(range(MIN_CELL + 1)).startswith("10.0 +/-")


def test_a_summary_over_no_observations_is_not_a_summary():
    # `disclosable(0)` is True, because a COUNT of zero names nobody.  A MEAN over zero
    # observations is a different thing entirely and must not render as "nan +/- nan".
    assert mean_sd([]) == SUPPRESSED
    assert median_iqr([]) == SUPPRESSED
    assert mean_sd(["missing", None]) == SUPPRESSED


def test_mean_sd_honours_decimals_and_drops_non_numbers():
    assert mean_sd(range(21), decimals=2).startswith("10.00 +/-")
    assert mean_sd(list(range(21)) + ["missing", None]).startswith("10.0 +/-")


def test_median_iqr_suppresses_at_exactly_twenty():
    # A median of a small set is dominated by one participant's own value, and at odd n it IS
    # that value.  The floor does not change the arithmetic; it changes the size of the set the
    # value could have come from, which is what makes the same number publishable.
    assert median_iqr(range(MIN_CELL)) == SUPPRESSED
    assert is_suppressed(median_iqr([1.5] * MIN_CELL))


def test_median_iqr_is_shown_at_twentyone():
    assert median_iqr(range(MIN_CELL + 1)) == "10.0 (5.0 to 15.0)"


def test_median_iqr_uses_the_word_to_and_no_dash():
    # The equality below is the whole assertion: it pins the separator, both dashes and every
    # decimal at once, so the three weaker checks that used to sit under it are gone.
    assert median_iqr(range(41), decimals=2) == "20.00 (10.00 to 30.00)"


def test_no_rendered_string_carries_a_banned_dash():
    rendered = [
        SUPPRESSED,
        round20(5),
        n_pct(31, 110),
        prev(31, 110),
        mean_sd(range(41)),
        median_iqr(range(41)),
    ]
    assert all(EM_DASH not in str(s) and MINUS_SIGN not in str(s) for s in rendered)


# ======================================================================================
# Frame helpers
# ======================================================================================


def test_safe_n_rounds_the_row_count():
    assert safe_n(pd.DataFrame({"a": range(5)})) == SUPPRESSED
    assert safe_n(pd.DataFrame({"a": range(100)})) == 100
    assert safe_n(pd.DataFrame({"a": []})) == 0


def test_safe_counts_suppresses_the_label_along_with_the_count():
    # The label IS data.  Rounding only the counts left a rare diagnosis string, a rare device
    # model or a free-text value disclosed by its mere presence in the index while its count
    # printed as the sentinel beside it.
    counts = safe_counts(pd.Series(["a"] * 100 + ["rare-diagnosis-XYZ"] * 3 + ["b"] * 2))
    assert counts["a"] == 100
    assert "rare-diagnosis-XYZ" not in list(counts.index)
    assert "b" not in list(counts.index)
    assert counts[SUPPRESSED] == SUPPRESSED
    # One folded row, not one row per rare category, so the NUMBER of rare categories is not
    # disclosed either; and the index stays unique so a caller can still index into it.
    assert list(counts.index).count(SUPPRESSED) == 1
    assert counts.index.is_unique


def test_safe_counts_keeps_the_disclosed_categories_and_rounds_them():
    counts = safe_counts(pd.Series(["a"] * 101 + ["b"] * 61))
    assert list(counts.index) == ["a", "b"]
    assert list(counts) == [100, 60]


def test_safe_show_prints_no_rows_and_rounds_a_small_row_count(capsys):
    df = pd.DataFrame({"steps": [1234, 5678, 91011], "region": ["c", "l", "c"]})
    safe_show(df, name="episodes")
    printed = capsys.readouterr().out
    assert SUPPRESSED in printed          # 3 rows is itself a small cell and is not printed
    assert "3 rows" not in printed
    assert "1234" not in printed          # no cell value reaches the screen
    assert "steps" in printed             # column names do


def test_safe_show_rounds_a_large_row_count_too(capsys):
    # The suppression path was the only one exercised, so a mutant that printed the raw count
    # whenever it was above the floor survived.
    safe_show(pd.DataFrame({"a": range(105)}), name="episodes")
    printed = capsys.readouterr().out
    assert "105" not in printed
    assert "100 rows" in printed


def test_suppress_frame_touches_only_the_named_columns():
    df = pd.DataFrame({"region": ["cervical", "lumbar"], "events": [7, 100]})
    out = suppress_frame(df, ["events"])
    assert list(out["events"]) == [SUPPRESSED, 100]
    assert list(out["region"]) == ["cervical", "lumbar"]
    assert list(df["events"]) == [7, 100]  # the input is not mutated


def test_suppress_frame_refuses_a_column_it_cannot_find():
    with pytest.raises(DisclosureError):
        suppress_frame(pd.DataFrame({"events": [100]}), ["evnets"])


def test_suppress_frame_names_the_column_on_a_negative_count_and_not_the_value():
    df = pd.DataFrame({"region": ["cervical"], "events": [-7]})
    with pytest.raises(DisclosureError) as caught:
        suppress_frame(df, ["events"])
    message = str(caught.value)
    assert "events" in message                       # what the caller needs
    assert re.findall(r"\d+", message) == []         # and nothing the caller may not see


# ======================================================================================
# export_violations: the refusal classes, one at a time
# ======================================================================================


def test_a_clean_frame_has_no_violations():
    assert export_violations(_clean_frame(), count_cols=["n contributing"]) == []


def test_every_parameter_after_the_frame_is_keyword_only():
    # The plan pins `export_violations(df, count_cols=...)`.  Keyword-only means a later edit
    # cannot re-order the parameters, and a caller cannot pass a partition list where a count
    # list was meant.
    with pytest.raises(TypeError):
        export_violations(_clean_frame(), ["n contributing"])


def test_class_count_cells_below_the_floor():
    df = _clean_frame()
    df.loc[0, "n contributing"] = 7
    violations = export_violations(df, count_cols=["n contributing"])
    assert len(violations) == 1
    assert "n contributing" in violations[0]


def test_a_class_count_message_counts_the_cells_and_never_quotes_one():
    df = _clean_frame()
    df.loc[0, "n contributing"] = 7
    df.loc[1, "n contributing"] = 13
    violations = export_violations(df, count_cols=["n contributing"])
    assert len(violations) == 1
    # THE PROPERTY, not a substring guess.  The check this replaces was `" 7" not in message`,
    # which passed against a message rendering the offending cells as "[7.0]".  The only
    # numeral a refusal message may carry is the NUMBER OF offending cells.
    assert re.findall(r"\d+", violations[0]) == ["2"]


def test_class_count_accepts_a_correctly_rounded_twenty():
    # THE DEFECT THIS CLASS WAS FIXED FOR.  The gate asked `disclosable` of the cell it was
    # handed, and in an export that cell has already been through `round20`, so `disclosable(20)`
    # being False refused a frame the module had just produced correctly.  ANALYSIS-PLAN.md
    # section 8 rule 2 and the module docstring both say a disclosed 20 stands on a true count
    # of 21 to 29, and almost every table in the study carries a rounded 20 somewhere.
    df = _clean_frame()
    df.loc[0, "n contributing"] = ROUND_BASE
    assert export_violations(df, count_cols=["n contributing"]) == []


def test_class_count_still_refuses_a_caller_who_forgot_to_round():
    # The strictness the class was written for, and it survives the fix.  A raw 21 is the common
    # real mistake, and the OLD floor test waved it through because 21 is above the floor.
    df = _clean_frame()
    df.loc[0, "n contributing"] = MIN_CELL + 1
    violations = export_violations(df, count_cols=["n contributing"])
    assert len(violations) == 1
    assert "n contributing" in violations[0]
    assert disclosable(MIN_CELL + 1)      # what the predicate this replaced would have said


def test_class_count_cannot_see_a_raw_twenty_and_the_gap_is_bounded():
    # THE ONE RESIDUAL GAP, pinned so it is a known property rather than a surprise found later.
    # A raw 20 is indistinguishable from a rounded 20 at the gate.  It is bounded because
    # `round20` is the only sanctioned way to produce a count for export and it suppresses a
    # true 20 rather than emitting it, and because the floor on the TRUE count is enforced
    # upstream by callers such as `02_pregate.render_wide` that ask `disclosable` first.
    df = _clean_frame()
    df.loc[0, "n contributing"] = DOCUMENTED_FLOOR
    assert export_violations(df, count_cols=["n contributing"]) == []
    assert round20(DOCUMENTED_FLOOR) == SUPPRESSED


def test_class_count_accepts_a_count_column_of_whole_valued_floats():
    # A LEFT JOIN turns an INT64 count column into float64.  The gate must accept it: the file
    # `safe_export` goes on to write casts it back to int64 and is correct.
    df = _clean_frame().astype({"n contributing": "float64"})
    assert export_violations(df, count_cols=["n contributing"]) == []


def test_the_class_count_message_names_the_right_predicate():
    # The old message said the cells "are not disclosable counts", which sends a reader to
    # `disclosable` -- the predicate that is NOT asked here and that gives the opposite answer
    # on 20.  A refusal message that misnames the rule costs the next reader the same hour.
    df = _clean_frame()
    df.loc[0, "n contributing"] = 7
    message = export_violations(df, count_cols=["n contributing"])[0]
    assert "disclosable" not in message
    assert "n contributing" in message
    # and the discipline holds on the new wording: the only numeral is the count of bad cells,
    # so the rounding base is named in words and no cell value is quoted.
    assert re.findall(r"\d+", message) == ["1"]


def test_class_count_refuses_a_negative_cell():
    df = _clean_frame()
    df.loc[0, "n contributing"] = -3
    assert len(export_violations(df, count_cols=["n contributing"])) == 1


def test_class_count_refuses_a_fractional_cell():
    # `values >= 1` used to exclude 0.5 from the band entirely, so a rate filed under a count
    # header exported clean, carrying more precision than any rounded count is allowed to.
    df = _clean_frame().astype({"n contributing": "float64"})
    df.loc[0, "n contributing"] = 0.5
    assert len(export_violations(df, count_cols=["n contributing"])) == 1
    df.loc[0, "n contributing"] = 40.5
    assert len(export_violations(df, count_cols=["n contributing"])) == 1


def test_class_count_allows_a_zero_by_default_and_refuses_it_on_request():
    df = _clean_frame()
    df.loc[0, "n contributing"] = 0
    assert export_violations(df, count_cols=["n contributing"]) == []
    strict = export_violations(df, count_cols=["n contributing"], allow_zero=False)
    assert len(strict) == 1 and "zero" in strict[0]


def test_allow_zero_is_keyword_only():
    with pytest.raises(TypeError):
        export_violations(_clean_frame(), ["n contributing"], False)


def test_class_count_ignores_already_suppressed_cells():
    df = _clean_frame()
    df["n contributing"] = df["n contributing"].astype(object)
    df.loc[0, "n contributing"] = SUPPRESSED
    assert export_violations(df, count_cols=["n contributing"]) == []


def test_a_misspelled_count_column_is_itself_a_violation():
    # Otherwise a typo silently switches off the check on the column it was meant to guard.
    violations = export_violations(_clean_frame(), count_cols=["n contributng"])
    assert len(violations) == 1
    assert "not in the frame" in violations[0]


def test_class_extension_refuses_a_non_tabular_path():
    # R2: the perimeter exports the plotted SERIES, never the plot.  `safe_export(df, "x.png")`
    # used to write the file and return an md5 for it.
    violations = export_violations(_clean_frame(), count_cols=["n contributing"],
                                   path="figure2.png")
    assert len(violations) == 1
    assert "png" in violations[0]


@pytest.mark.parametrize("suffix", ALLOWED_EXPORT_SUFFIXES)
def test_class_extension_permits_the_three_bundle_extensions(suffix):
    assert export_violations(_clean_frame(), count_cols=["n contributing"],
                             path=f"bundle{suffix}") == []


@pytest.mark.parametrize("name", ["figure2.PNG", "notes.txt", "series.parquet", "model.pkl",
                                  "table1.xlsx", "archive.csv.gz", "series"])
def test_class_extension_refuses_every_other_extension(name):
    assert len(export_violations(_clean_frame(), count_cols=["n contributing"],
                                 path=name)) == 1


def test_class_complementary_refuses_a_percentage_beside_a_suppressed_count():
    # CLAUDE.md rule 1, and the violation on this list that costs a manuscript rather than a
    # re-export.  Verified absent before this fix: this exact frame returned [].
    df = pd.DataFrame({"group": ["cervical", "lumbar"],
                       "n": [SUPPRESSED, "40"],
                       "pct": ["37%", "33%"]})
    violations = export_violations(df, count_cols=["n"], percentage_columns=["pct"])
    assert len(violations) == 1
    assert "pct" in violations[0] and "'n'" in violations[0]


def test_class_complementary_passes_when_the_percentage_dies_with_the_count():
    df = pd.DataFrame({"group": ["cervical", "lumbar"],
                       "n": [SUPPRESSED, "40"],
                       "pct": [SUPPRESSED, "33%"]})
    assert export_violations(df, count_cols=["n"], percentage_columns=["pct"]) == []


def test_class_complementary_refuses_a_percentage_it_cannot_pair():
    # Declaring a percentage column with no count column would otherwise switch the check off
    # silently, which is how the check would come to be reported as passing on a frame nobody
    # checked.
    df = pd.DataFrame({"group": ["cervical"], "pct": ["33%"]})
    assert len(export_violations(df, percentage_columns=["pct"])) == 1
    assert len(export_violations(df, percentage_columns=["pctt"])) == 1


def test_class_partition_refuses_exactly_one_suppressed_member():
    # One suppressed member of a partition of a disclosed total is recoverable by subtraction.
    df = pd.DataFrame({"group": ["all"], "a": [SUPPRESSED], "b": ["40"], "c": ["60"]})
    violations = export_violations(df, partitions=[["a", "b", "c"]])
    assert len(violations) == 1
    assert "subtraction" in violations[0]


def test_class_partition_allows_two_suppressed_members_or_none():
    two = pd.DataFrame({"a": [SUPPRESSED], "b": [SUPPRESSED], "c": ["60"]})
    assert export_violations(two, partitions=[["a", "b", "c"]]) == []
    none = pd.DataFrame({"a": ["40"], "b": ["60"], "c": ["80"]})
    assert export_violations(none, partitions=[["a", "b", "c"]]) == []


def test_class_partition_refuses_a_partition_it_cannot_evaluate():
    df = pd.DataFrame({"a": [SUPPRESSED], "b": ["40"]})
    assert len(export_violations(df, partitions=[["a", "bb"]])) == 1
    assert len(export_violations(df, partitions=[["a"]])) == 1


# ======================================================================================
# The same two classes, in the BUNDLE's representations.  These are the tests that would have
# caught the original defect: every frame above spells a suppressed cell with the module's own
# sentinel, which is the ONE spelling that never reaches an exported file, so all of them
# passed while both classes were inert on everything `07_export.py` actually writes.
#
# The frames below are the real shapes, column for column:
#   `_strobe_frame`   -- figures-csv/figure1_strobe_ladder.csv, thirteen columns, the numeral
#                        columns rendered as strings and a hidden cell written as the bare
#                        section 4 token.  `build_figure1_frame` declares exactly the
#                        `count_cols` and `partitions` used here.
#   `_exclusion_ledger_frame` -- ledgers-csv/ledger_exclusion_and_censoring_reasons.csv, seven
#                        columns, a hidden count written as the 7.5 sentence and its percentage
#                        written as the `numerator_suppressed` sentence.
#                        `build_ledger_exclusion_frame` declares exactly what is used here.
# ======================================================================================


def _strobe_frame(n_dropped: str, n_out: str, n_in: str = "40") -> pd.DataFrame:
    """One rung of the STROBE ladder, in the thirteen columns section 4.1 fixes."""
    return pd.DataFrame([{
        "step": 18,
        "slug": "excl_event_without_computable_landmark",
        "display_label": "Analyzable acute-care events",
        "kind": "exclusion",
        "unit": "events",
        "n_in": n_in,
        "n_dropped": n_dropped,
        "n_out": n_out,
        "n_carried_forward": "",
        "reason": "excl_event_without_computable_landmark",
        "reason_display": "Event on post-discharge day 1 to 4 with no computable window",
        "closes_exact": "true",
        "box_side": "exclusion",
    }])


STROBE_DECLARATIONS = {
    "kind": "figure-csv",
    "count_cols": ("n_in", "n_dropped", "n_out", "n_carried_forward"),
    "partitions": (("n_dropped", "n_out"),),
}


def _exclusion_ledger_frame(n_episodes: str, share: str) -> pd.DataFrame:
    """Two rows of the exclusion-reason ledger, in the seven columns section 5.6 fixes."""
    return pd.DataFrame([
        {"step": "15", "slug": "excl_window_truncated",
         "display_label": "Analytic cohort",
         "reason_detail": "Accrual window truncated by death",
         "n_episodes": n_episodes, "n_denominator": "60",
         "share_of_step_dropped": share},
        {"step": "15", "slug": "excl_window_truncated",
         "display_label": "Analytic cohort",
         "reason_detail": "Accrual window truncated by a repeat operation",
         "n_episodes": "40", "n_denominator": "60",
         "share_of_step_dropped": "67%"},
    ])


LEDGER_DECLARATIONS = {
    "kind": "table-csv",
    "count_cols": ("n_episodes", "n_denominator"),
    "percentage_columns": ("share_of_step_dropped",),
    "specification_columns": ("reason_detail",),
}


@pytest.mark.parametrize("hidden", [FIGURE_SUPPRESSED_TOKEN, CELL_BELOW_THRESHOLD,
                                    SECONDARY_SUPPRESSION, SUPPRESSED])
def test_class_complementary_fires_on_a_bundle_representation(hidden):
    # The class that costs a manuscript rather than a re-export.  67% of a disclosed 60 is 40,
    # so the hidden count is recovered exactly by multiplication, and until the representation
    # fix this frame -- the ledger's real shape, with the ledger's real declarations -- came
    # back clean because no bundle spelling of "hidden" contains the module's sentinel.
    df = _exclusion_ledger_frame(n_episodes=hidden, share="33%")
    violations = export_violations(df, **LEDGER_DECLARATIONS)
    assert len(violations) == 1
    assert "share_of_step_dropped" in violations[0] and "n_episodes" in violations[0]


def test_class_complementary_still_passes_when_the_percentage_dies_with_the_count():
    # The other side of the same fix, and the reason `_is_disclosed_value` had to move too.
    # A suppressed percentage is written as the 7.5 `numerator_suppressed` sentence, which is
    # what this ledger actually carries on a hidden row.  Read as a DISCLOSED percentage -- the
    # sentinel-only reading -- the class would refuse the file for suppressing correctly.
    df = _exclusion_ledger_frame(n_episodes=CELL_BELOW_THRESHOLD, share=NUMERATOR_SUPPRESSED)
    assert export_violations(df, **LEDGER_DECLARATIONS) == []


@pytest.mark.parametrize("hidden", [FIGURE_SUPPRESSED_TOKEN, CELL_BELOW_THRESHOLD,
                                    SECONDARY_SUPPRESSION, SUPPRESSED])
def test_class_partition_fires_on_a_bundle_representation(hidden):
    # `n_dropped` and `n_out` partition `n_in` on an exclusion rung, so one hidden member is
    # `n_in` minus the other: subtraction recovers it exactly.  This is the real declaration
    # `build_figure1_frame` emits, on the real thirteen-column frame.
    df = _strobe_frame(n_dropped=hidden, n_out="20")
    violations = export_violations(df, **STROBE_DECLARATIONS)
    assert len(violations) == 1
    assert "subtraction" in violations[0]


@pytest.mark.parametrize("hidden", [FIGURE_SUPPRESSED_TOKEN, CELL_BELOW_THRESHOLD])
def test_class_partition_allows_two_suppressed_members_in_a_bundle_representation(hidden):
    assert export_violations(_strobe_frame(n_dropped=hidden, n_out=hidden),
                             **STROBE_DECLARATIONS) == []


@pytest.mark.parametrize("hidden", [FIGURE_SUPPRESSED_TOKEN, CELL_BELOW_THRESHOLD])
def test_class_partition_skips_a_row_where_the_other_member_is_not_applicable(hidden):
    # THE FALSE POSITIVE THE FIX MUST NOT CREATE.  Figure 1's terminal rung carries the
    # not-applicable empty string in `n_dropped` and a hidden `n_out`: one member suppressed,
    # one member ABSENT, and no disclosed sibling to subtract it from.  Counting that row would
    # refuse the STROBE ladder for a suppression that discloses nothing, and the only way to
    # satisfy the refusal would be to suppress a cell the contract requires to be blank.
    df = _strobe_frame(n_dropped="", n_out=hidden, n_in=hidden)
    assert export_violations(df, **STROBE_DECLARATIONS) == []
    # It is the ABSENCE that skips the row, not the representation: give the row a disclosed
    # sibling and the same hidden cell is refused again.
    assert len(export_violations(_strobe_frame(n_dropped="20", n_out=hidden),
                                 **STROBE_DECLARATIONS)) == 1


def test_the_empty_string_does_not_make_a_partition_member_suppressed():
    # Constraint 4 at the class, not only at the predicate.  A row of blanks partitions
    # nothing; a blank beside a disclosed count is not a lone suppression.
    blanks = pd.DataFrame({"a": ["", ""], "b": ["", "40"], "c": ["60", "60"]})
    assert export_violations(blanks, partitions=[["a", "b", "c"]]) == []


@pytest.mark.parametrize("banned", [chr(0x2014), chr(0x2212)])
def test_class_banned_characters_in_a_string_cell(banned):
    df = pd.DataFrame({"label": ["cervical", f"1{banned}2"]})
    violations = export_violations(df)
    assert len(violations) == 1
    assert "U+2014" in violations[0] or "U+2212" in violations[0]


def test_class_banned_characters_in_a_column_header():
    # A header is a written string too, and it lands in the file above every row.
    df = pd.DataFrame({f"day{chr(0x2014)}range": ["cervical"]})
    assert len(export_violations(df)) == 1


def test_class_banned_characters_permits_the_en_dash_and_the_hyphen():
    df = pd.DataFrame({"label": [f"2020{chr(0x2013)}2021", "before-2020"]})
    assert export_violations(df) == []


def test_class_kind_table_csv_refuses_a_cell_that_is_not_a_display_string():
    # A table CSV carries rendered strings; a number still in it is a number the renderer would
    # format a second time, and possibly differently from the first.
    df = pd.DataFrame({"group": ["cervical"], "n": [40]})
    assert len(export_violations(df, kind="table-csv", count_cols=["n"])) == 1
    rendered = pd.DataFrame({"group": ["cervical"], "n": ["40"]})
    assert export_violations(rendered, kind="table-csv", count_cols=["n"]) == []


def test_class_kind_figure_csv_refuses_a_display_string_in_a_numeric_column():
    # A suppressed figure row is ABSENT from the file, never written as a sentinel, because
    # matplotlib cannot plot a sentinel and a reader cannot see one.
    df = pd.DataFrame({"day": [1, 2], "n contributing": [40, SUPPRESSED]})
    assert len(export_violations(df, kind="figure-csv")) == 1
    dropped = pd.DataFrame({"day": [1], "n contributing": [40]})
    assert export_violations(dropped, kind="figure-csv") == []


def test_class_kind_refuses_a_kind_it_does_not_know():
    assert len(export_violations(_clean_frame(), kind="figures-csv")) == 1


def test_class_identifier_like_name():
    df = _clean_frame().assign(**{"person id": ["A", "B", "C"] * 10})
    violations = export_violations(df, count_cols=["n contributing"])
    assert len(violations) == 1
    assert "participant identifier" in violations[0]


@pytest.mark.parametrize(
    "name", ["person_id", "participant_id", "research_id", "subject_id", "personId", "PERSON ID"]
)
def test_class_identifier_catches_every_spelling(name):
    df = _clean_frame().assign(**{name: ["A", "B", "C"] * 10})
    assert any("participant identifier" in v for v in export_violations(df))


def test_class_identifier_does_not_refuse_a_public_concept_id():
    # Concept ids are public OMOP vocabulary and the concept-set table must be exportable, so
    # the name patterns are deliberately narrow rather than a blanket match on "id".
    df = _clean_frame().assign(**{"concept id": [4030520, 4288546, 40480160] * 10})
    assert export_violations(df, count_cols=["n contributing"]) == []


def test_class_identifier_integer_column_that_is_near_unique_is_a_key():
    # An integer key with an innocuous name fires on its SHAPE.  It necessarily also fires the
    # near-unique class, because near-unique is the superset; both messages are expected, and
    # that is the point of screening by name AND dtype AND content rather than by name alone.
    df = _clean_frame().assign(code=range(1000, 1030))
    violations = export_violations(df, count_cols=["n contributing"])
    assert len(violations) == 2
    assert any("shape of a key" in v for v in violations)
    assert any("near-unique" in v for v in violations)


def test_class_date_like_name():
    df = pd.DataFrame({"region": ["cervical"] * 5, "surgery date": ["2020-03-01"] * 5})
    violations = export_violations(df)
    assert len(violations) == 1
    assert "unshifted" in violations[0]


@pytest.mark.parametrize("name", ["date", "index_date", "dob", "birth_datetime", "event timestamp"])
def test_class_date_catches_every_spelling(name):
    df = pd.DataFrame({name: ["2020-03-01"] * 5})
    assert any("unshifted" in v for v in export_violations(df))


def test_class_date_name_matching_is_token_wise_not_substring():
    # "update flag" contains the letters "date" and is not a date.
    assert export_violations(pd.DataFrame({"update flag": [True, False]})) == []


def test_class_date_datetime_dtype_under_an_innocuous_name():
    # The renamed-column case: name matching alone would pass this straight through.
    df = pd.DataFrame({"when": pd.to_datetime(["2020-03-01"] * 5)})
    violations = export_violations(df)
    assert len(violations) == 1
    assert "unshifted" in violations[0]


def test_class_date_object_column_of_python_dates():
    # A BigQuery DATE column arrives as object-dtype datetime.date, which no dtype predicate
    # catches and which no name betrays.
    df = pd.DataFrame({"value": [dt.date(2020, 3, 1)] * 5})
    violations = export_violations(df)
    assert len(violations) == 1
    assert "unshifted" in violations[0]


def test_class_near_unique_column():
    df = _clean_frame().assign(fingerprint=[i + 0.5 for i in range(30)])
    violations = export_violations(df, count_cols=["n contributing"])
    assert len(violations) == 1
    assert "near-unique" in violations[0]


def test_the_near_unique_message_rounds_its_row_count_and_states_no_ratio():
    # The message used to read "100% of 21 rows", on a notebook traceback, which is a raw row
    # count disclosed on the surface `safe_show` exists to protect; and the ratio times the row
    # count is the exact number of distinct values in the column.
    df = pd.DataFrame({"score": [i + 0.5 for i in range(21)]})
    violations = [v for v in export_violations(df) if "near-unique" in v]
    assert len(violations) == 1
    assert "21" not in violations[0]        # the raw row count
    assert "100%" not in violations[0]      # the observed ratio
    assert "20 rows" in violations[0]       # the rounded row count, via safe_n
    assert f"{NEAR_UNIQUE_RATIO:.0%}" in violations[0]   # the ceiling, which is policy


def test_class_near_unique_respects_the_row_floor():
    # Below the floor the ratio carries no information: a 4-row table with 4 region labels is
    # 100 percent distinct and obviously safe.
    at_floor = pd.DataFrame({"score": [i + 0.5 for i in range(NEAR_UNIQUE_MIN_ROWS)]})
    assert export_violations(at_floor) == []
    over_floor = pd.DataFrame({"score": [i + 0.5 for i in range(NEAR_UNIQUE_MIN_ROWS + 1)]})
    assert any("near-unique" in v for v in export_violations(over_floor))


def test_class_near_unique_ratio_boundary_is_strict():
    # Exactly at the ceiling clears; one distinct value more does not.  The docstring used to
    # read "this fraction or more" while the code compared with `>`, and nothing pinned which
    # was right.
    ties = [0.5, 1.5, 2.5]
    at_ceiling = [float(i) + 0.5 for i in range(27)] + ties          # 27 distinct in 30 rows
    over_ceiling = [float(i) + 0.5 for i in range(28)] + ties[:2]    # 28 distinct in 30 rows
    # These two tie the fixtures to the module constant rather than to test-local arithmetic:
    # if the ceiling moves, they fail here, which is the signal that the fixtures no longer sit
    # on the boundary they were built to straddle.
    assert len(set(at_ceiling)) / len(at_ceiling) == NEAR_UNIQUE_RATIO
    assert len(set(over_ceiling)) / len(over_ceiling) > NEAR_UNIQUE_RATIO
    assert export_violations(pd.DataFrame({"score": at_ceiling})) == []
    assert any("near-unique" in v for v in export_violations(pd.DataFrame({"score": over_ceiling})))


def test_all_four_column_classes_at_once_are_all_reported():
    violations = export_violations(_dirty_frame(), count_cols=["n contributing"])
    assert len(violations) == 4
    assert any("n contributing" in v for v in violations)
    assert any("participant identifier" in v for v in violations)
    assert any("unshifted" in v for v in violations)
    assert any("near-unique" in v for v in violations)


# ======================================================================================
# specification_columns: the one exemption, and the four things that keep it narrow
#
# A specification column holds VOCABULARY OR PROTOCOL values rather than participant-derived
# values, and is exempt from the NEAR-UNIQUE and IDENTIFIER-LIKE classes and from nothing else.
# The tests below pin, in order: that the real registry needs it, that it works, that it
# reaches exactly two classes and no others, that it is per column, and that a declaration
# which names nothing is caught rather than ignored.
# ======================================================================================


def _registry_frame() -> pd.DataFrame:
    """The real `ledger_concept_set_registry.csv` producer, rendered as a table CSV.

    EXPORT-CONTRACT.md 5.6.  Built from `cs_spine.registry_rows()` rather than from a fixture,
    because a fixture would pin the shape this test WANTS the registry to have instead of the
    shape it HAS, and the whole point of the case is that the real file is refused.  `.astype`
    is the table-CSV rendering step, not part of the case: a table CSV carries display strings.
    """
    return pd.DataFrame(cs_spine.registry_rows()).astype(str)


def test_the_real_registry_is_the_shape_the_near_unique_class_fires_on():
    # Guards the case itself.  If a later edit to the locked concept set drops the registry
    # below the row floor or introduces a duplicate code, the tests below would start passing
    # for the wrong reason and this one goes red first to say so.
    df = _registry_frame()
    assert len(df) > NEAR_UNIQUE_MIN_ROWS
    assert df["code"].nunique() == len(df)      # one row per locked code, so 100% distinct


def test_the_real_registry_is_refused_on_its_code_column_when_it_is_not_declared():
    violations = export_violations(_registry_frame(), kind="table-csv")
    assert len(violations) == 1
    assert "near-unique" in violations[0]
    assert "code" in violations[0]


def test_the_real_registry_exports_cleanly_when_code_is_declared():
    # The defect: a list of CPT-4 and ICD-10-PCS codes is a SPECIFICATION.  It describes the
    # study, it is derived from a public vocabulary, and it identifies nobody.
    assert export_violations(
        _registry_frame(), kind="table-csv", specification_columns=["code"]
    ) == []


def test_safe_export_writes_the_registry_when_code_is_declared(tmp_path):
    df = _registry_frame()
    out = tmp_path / "results" / "ledgers-csv" / "ledger_concept_set_registry.csv"
    row = safe_export(
        df, out, kind="table-csv", exhibit="Supplement S1",
        description="locked concept set registry", specification_columns=["code"],
    )
    assert out.exists()
    assert row["file"] == "ledgers-csv/ledger_concept_set_registry.csv"
    assert row["n_rows"] == len(df)
    with pytest.raises(DisclosureError):
        safe_export(df, tmp_path / "undeclared.csv", kind="table-csv")


@pytest.mark.parametrize("banned", [EM_DASH, MINUS_SIGN])
def test_a_declared_column_is_still_refused_for_a_banned_character(banned):
    # The exemption reaches two LINKAGE classes.  A banned dash is a rendering fault, not a
    # linkage risk, and a declaration says nothing about it either way.
    df = _registry_frame()
    df.loc[0, "code"] = "22600" + banned + "22614"
    violations = export_violations(df, kind="table-csv", specification_columns=["code"])
    assert len(violations) == 1
    assert "banned dash" in violations[0]


def test_a_declared_column_that_is_date_like_is_still_refused():
    # DELIBERATE, and the one exemption a reader is most likely to expect and not get.  A date
    # in a specification file is either participant-derived and mislabelled, or a build fact
    # that belongs in MANIFEST.csv.  Both readings want the refusal.
    df = _registry_frame().assign(**{"lock date": ["2024-01-01"] * len(_registry_frame())})
    violations = export_violations(
        df, kind="table-csv", specification_columns=["code", "lock date"]
    )
    assert len(violations) == 1
    assert "unshifted" in violations[0]


def test_a_declared_column_that_is_a_datetime_dtype_is_still_refused():
    # The same decision reached by dtype rather than by name, so a rename cannot slip a real
    # date column past the gate under a declaration.
    df = pd.DataFrame({"code": [f"{22600 + i}" for i in range(30)],
                       "when": pd.to_datetime(["2020-03-01"] * 30)})
    violations = export_violations(df, specification_columns=["code", "when"])
    assert len(violations) == 1
    assert "unshifted" in violations[0]


def test_a_declared_column_is_still_held_to_the_count_and_partition_classes():
    # Declaring a column says what its values ARE, not that it may skip the floor.  Here the
    # same column is declared and named as a count, and the floor still refuses its cells.
    df = pd.DataFrame({"code": [7] * 30})
    violations = export_violations(df, count_cols=["code"], specification_columns=["code"])
    assert len(violations) == 1
    assert "legal disclosed counts" in violations[0]

    partitioned = pd.DataFrame({"code": [f"{22600 + i}" for i in range(30)],
                                "a": [SUPPRESSED] * 30, "b": ["40"] * 30})
    lone = export_violations(
        partitioned, partitions=[["a", "b"]], specification_columns=["code", "a", "b"]
    )
    assert len(lone) == 1
    assert "recoverable by subtraction" in lone[0]


def test_a_declared_column_is_still_held_to_the_percentage_class():
    df = pd.DataFrame({"code": [f"{22600 + i}" for i in range(30)],
                       "n": [SUPPRESSED] * 30, "pct": ["37%"] * 30})
    violations = export_violations(
        df, count_cols=["n"], percentage_columns=["pct"],
        specification_columns=["code", "n", "pct"],
    )
    assert len(violations) == 1
    assert "suppressed" in violations[0]


def test_the_exemption_covers_the_identifier_like_shape_branch():
    # OMOP concept ids are public vocabulary, and a registry of them is near-unique integers,
    # which is the SHAPE of a key.  Undeclared it fires both linkage classes; declared, neither.
    df = pd.DataFrame({"concept id": list(range(4030520, 4030550))})
    undeclared = export_violations(df)
    assert len(undeclared) == 2
    assert any("shape of a key" in v for v in undeclared)
    assert any("near-unique" in v for v in undeclared)
    assert export_violations(df, specification_columns=["concept id"]) == []


def test_the_exemption_covers_the_identifier_like_name_branch():
    # The mechanism is uniform across both branches of the class.  What stops this from being
    # abused is not that the gate refuses the declaration, it is that the declaration is
    # explicit, per column, and sits in the diff where a reviewer reads it.
    df = pd.DataFrame({"person id": ["A", "B", "C"] * 10})
    assert any("participant identifier" in v for v in export_violations(df))
    assert export_violations(df, specification_columns=["person id"]) == []


def test_the_exemption_does_not_leak_to_an_undeclared_sibling_column():
    # PER COLUMN, never file-level.  A per-person fingerprint riding along in the same frame as
    # a legitimately declared vocabulary column is still refused, which is the whole reason
    # there is no file-level or `kind`-level form of this parameter.
    df = _registry_frame()
    df["deficit"] = [i + 0.5 for i in range(len(df))]
    violations = export_violations(df, specification_columns=["code"])
    assert len(violations) == 1
    assert "near-unique" in violations[0]
    assert "deficit" in violations[0]
    assert "code" not in violations[0]


def test_the_exemption_does_not_leak_to_an_undeclared_identifier_column():
    # The second half of "per column": the identifier-like class does not leak either.  A
    # file-level or `kind`-level form of this parameter would walk a participant identifier out
    # of the perimeter on the strength of a legitimate declaration on an unrelated column.
    df = _registry_frame()
    df["person id"] = [f"p{i}" for i in range(len(df))]
    violations = export_violations(df, specification_columns=["code"])
    assert any("participant identifier" in v and "person id" in v for v in violations)
    assert not any("code" in v for v in violations)


def test_declaring_a_column_that_is_not_in_the_frame_is_a_violation_naming_it():
    # Otherwise a typo silently grants no exemption, or a later column rename silently grants
    # one to nothing while the author believes the file is covered.  Both violations are
    # reported: the misspelling, and the near-unique column the misspelling failed to cover.
    violations = export_violations(_registry_frame(), specification_columns=["cdoe"])
    assert len(violations) == 2
    assert any("cdoe" in v and "not in the frame" in v for v in violations)
    assert any("near-unique" in v and "code" in v for v in violations)


def test_a_misspelled_declaration_is_reported_even_when_nothing_else_is_wrong():
    # The frame below has no near-unique column at all, so the misspelling is the only thing
    # wrong with it.  A silent no-op would export this file and report nothing.
    df = pd.DataFrame({"region": ["cervical", "lumbar"] * 15})
    violations = export_violations(df, specification_columns=["code"])
    assert len(violations) == 1
    assert "code" in violations[0] and "not in the frame" in violations[0]


def test_declaring_nothing_leaves_every_class_exactly_as_it_was():
    # The default is the pre-existing behaviour, so no caller that does not pass the parameter
    # can have its checking changed by it.
    assert export_violations(_dirty_frame(), count_cols=["n contributing"]) == export_violations(
        _dirty_frame(), count_cols=["n contributing"], specification_columns=[]
    )


def test_specification_columns_is_keyword_only_on_both_functions():
    for fn in (export_violations, safe_export):
        parameter = inspect.signature(fn).parameters["specification_columns"]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, fn.__name__
        assert parameter.default == ()
    # And positionally it is simply not reachable, on either function.
    with pytest.raises(TypeError):
        export_violations(_registry_frame(), ["code"])
    with pytest.raises(TypeError):
        safe_export(_registry_frame(), "a.csv", ["code"])


def test_export_violations_does_not_mutate_the_frame():
    df = _dirty_frame()
    before = df.copy()
    export_violations(df, count_cols=["n contributing"])
    pd.testing.assert_frame_equal(df, before)


def test_an_empty_frame_is_exportable():
    assert export_violations(pd.DataFrame({"region": [], "n": []}), count_cols=["n"]) == []


# ======================================================================================
# md5_of_bytes and safe_export
# ======================================================================================


def test_md5_of_bytes_matches_the_reference_digest():
    assert md5_of_bytes(b"") == "d41d8cd98f00b204e9800998ecf8427e"
    assert md5_of_bytes(b"abc") == "900150983cd24fb0d6963f7d28e17f72"


def test_safe_export_returns_the_manifest_row(tmp_path):
    # EXPORT-CONTRACT.md 10.4 item 9 and section 8.3.  `07_export.py` writes nine of these
    # rows; a manifest assembled from nine separate re-derivations of the row and column counts
    # is nine chances to describe a file the exporter did not write.
    out = tmp_path / "results" / "figures-csv" / "figure2.csv"
    row = safe_export(
        _clean_frame(),
        out,
        kind="figure-csv",
        exhibit="Figure 2",
        description="Baseline-normalized daily activity by post-discharge day",
        count_cols=["n contributing"],
    )
    assert tuple(row) == MANIFEST_COLUMNS
    assert out.exists()
    # The independent check: hash the file on disk, not the object that was passed in.
    assert row["md5"] == hashlib.md5(out.read_bytes()).hexdigest()
    assert row["file"] == "figures-csv/figure2.csv"        # relative to the bundle root
    assert row["kind"] == "figure-csv"
    assert row["exhibit"] == "Figure 2"
    assert row["n_rows"] == 30
    assert row["n_columns"] == 5
    assert row["min_disclosed_count"] == 40
    assert row["n_suppressed_cells"] == 0
    assert row["description"].startswith("Baseline-normalized")


def test_the_manifest_row_counts_suppressed_cells_and_the_smallest_disclosed_count(tmp_path):
    df = pd.DataFrame(
        {
            "group": ["cervical", "lumbar", "thoracic"],
            "n": ["60", "40", SUPPRESSED],
            "pct": ["60%", "40%", SUPPRESSED],
        }
    )
    row = safe_export(df, tmp_path / "table1.csv", kind="table-csv", exhibit="Table 1",
                      count_cols=["n"], percentage_columns=["pct"])
    assert row["n_suppressed_cells"] == 2
    assert row["min_disclosed_count"] == 40
    assert row["file"] == "table1.csv"     # no results/ on the path: the bare name


def test_the_manifest_row_leaves_the_smallest_count_empty_when_there_is_none(tmp_path):
    df = pd.DataFrame({"group": ["cervical"], "label": ["fusion"]})
    row = safe_export(df, tmp_path / "labels.csv", kind="table-csv")
    assert row["min_disclosed_count"] == ""


def test_the_manifest_counts_a_suppressed_cell_in_the_bundle_representation(tmp_path):
    # EXPORT-CONTRACT.md 8.3 defines this field as "cells written as SUPPRESSED, or as a
    # suppression sentence in a table CSV", which is neither of them the module's own sentinel.
    # Counted on the sentinel it returned 0 on every file in the bundle, and the manifest
    # understated every suppressed file it stamps.
    table = _exclusion_ledger_frame(n_episodes=CELL_BELOW_THRESHOLD, share=NUMERATOR_SUPPRESSED)
    row = safe_export(table, tmp_path / "results" / "ledgers-csv" / "ledger.csv",
                      **LEDGER_DECLARATIONS)
    assert row["n_suppressed_cells"] == 2

    figure = _strobe_frame(n_dropped=FIGURE_SUPPRESSED_TOKEN, n_out=FIGURE_SUPPRESSED_TOKEN)
    row = safe_export(figure, tmp_path / "results" / "figures-csv" / "figure1.csv",
                      **STROBE_DECLARATIONS)
    assert row["n_suppressed_cells"] == 2


def test_the_manifest_does_not_count_a_not_applicable_cell_as_suppressed(tmp_path):
    # A file whose only non-numeric cells are the not-applicable empty string has none hidden.
    # Reading a blank as hidden would inflate this field on every figure CSV in the bundle,
    # `figure1_strobe_ladder.csv` most of all: eighteen of its nineteen rows carry a blank
    # `n_carried_forward`.
    df = _strobe_frame(n_dropped="20", n_out="20")
    row = safe_export(df, tmp_path / "results" / "figures-csv" / "figure1.csv",
                      **STROBE_DECLARATIONS)
    assert row["n_suppressed_cells"] == 0


def test_the_manifest_does_not_count_prose_about_suppression(tmp_path):
    # The closed set, at the manifest.  A free-text column that discusses suppression is not a
    # column of suppressed cells, and inflating the count would misreport the file.
    df = pd.DataFrame({"note": ["the count was suppressed", "suppressed", "not estimable"],
                       "n": ["40", "60", "80"]})
    row = safe_export(df, tmp_path / "results" / "tables-csv" / "notes.csv",
                      kind="table-csv", count_cols=["n"])
    assert row["n_suppressed_cells"] == 0


# ---- n_suppressed_cells counts written TOKENS and not reasons ------------------------
# EXPORT-CONTRACT.md 8.3: "cells written as `SUPPRESSED`, or as a suppression sentence IN A
# TABLE CSV".  Section 4.4 restates the qualifier without room for a second reading: the
# suppressed cells of Figure 4 at tier 4 are counted in "`n_suppressed_cells`, which counts
# written tokens and not reasons".  Asking `is_bundle_suppressed` over every column ignored the
# qualifier and counted a figure CSV's display prose, which stamped Figure 4 at 220 against the
# contract's 176 and Figure 3 at 5 against 4.


def _figure4_tier_four_frame() -> pd.DataFrame:
    """`figures-csv/figure4_event_centered_activity.csv` at tier 4, in its ten columns.

    EXPORT-CONTRACT.md 4.4: the file keeps its 44 rows -- two series across the fixed `-14` to
    `+7` window -- and suppresses its cells, so `n_contributing`, `observed_median`,
    `observed_p25` and `observed_p75` all carry the bare token, `plotted` is `false`, and
    `not_plotted_display` carries the `not_permitted_by_tier` sentence.  That is 176 written
    tokens beside 44 printed reasons, and 4.4 states the 176 as the number the manifest carries.
    """
    offsets = list(range(-14, 8))
    rows = []
    for order, slug, label in ((1, "event_case", "Cases"), (2, "matched_control", "Matched controls")):
        for offset in offsets:
            rows.append({
                "series_slug": slug,
                "display_label": label,
                "series_order": str(order),
                "day_relative_to_event": str(offset),
                "n_contributing": FIGURE_SUPPRESSED_TOKEN,
                "observed_median": FIGURE_SUPPRESSED_TOKEN,
                "observed_p25": FIGURE_SUPPRESSED_TOKEN,
                "observed_p75": FIGURE_SUPPRESSED_TOKEN,
                "plotted": "false",
                "not_plotted_display": NOT_PERMITTED_BY_TIER,
            })
    return pd.DataFrame(rows)


def test_the_manifest_counts_figure_four_at_the_number_the_contract_states(tmp_path):
    # The defect, at its own scale and in its own file.  44 rows x 4 token columns is 176; the
    # 44 `not_plotted_display` sentences are the 44 that made it 220.
    frame = _figure4_tier_four_frame()
    assert len(frame) == 44
    row = safe_export(frame, tmp_path / "results" / "figures-csv" / "figure4.csv",
                      kind="figure-csv", exhibit="Figure 4", count_cols=["n_contributing"])
    assert row["n_suppressed_cells"] == 176
    # And the file discloses no count, which 4.4 states in the same paragraph.
    assert row["min_disclosed_count"] == ""


def test_the_manifest_does_not_count_a_figure_csv_s_printed_reason(tmp_path):
    # Figure 3's shape: the hidden estimate is the token, and `not_estimable_display` prints
    # the reason for it beside it.  One hidden cell, not two.
    df = pd.DataFrame({"slug": ["debt_overall", "debt_cervical"],
                       "estimate": [FIGURE_SUPPRESSED_TOKEN, "40"],
                       "estimable": ["false", "true"],
                       "not_estimable_display": [CELL_BELOW_THRESHOLD, ""]})
    row = safe_export(df, tmp_path / "results" / "figures-csv" / "figure3.csv",
                      kind="figure-csv", count_cols=["estimate"])
    assert row["n_suppressed_cells"] == 1


def test_the_manifest_sentence_clause_is_keyed_on_the_kind_and_not_on_the_column_name(tmp_path):
    # The two fixes that both make Figure 4 read right are told apart here.  A `*_display`
    # column-name rule would agree with the kind rule on the frame above and disagree on both
    # of these, and on both of them the contract is with the kind rule.
    #
    # One frame, one column, two kinds.  Section 5 MANDATES the 7.5 sentence as a table CSV's
    # spelling of a hidden cell, so the same string that is prose in a figure CSV is the hidden
    # cell itself in a table CSV.
    same = pd.DataFrame({"group": ["cervical", "lumbar"],
                         "n": [CELL_BELOW_THRESHOLD, "40"]})
    as_figure = safe_export(same, tmp_path / "results" / "figures-csv" / "f.csv",
                            kind="figure-csv", count_cols=["n"])
    as_table = safe_export(same, tmp_path / "results" / "tables-csv" / "t.csv",
                           kind="table-csv", count_cols=["n"])
    assert (as_figure["n_suppressed_cells"], as_table["n_suppressed_cells"]) == (0, 1)

    # A table CSV whose hidden cell happens to sit in a column named `*_display` is still
    # counted: the name is not the rule, and a suffix rule would drop this one.
    named = pd.DataFrame({"row_label": ["Cervical decompression"],
                          "n_display": [CELL_BELOW_THRESHOLD]})
    row = safe_export(named, tmp_path / "results" / "tables-csv" / "named.csv",
                      kind="table-csv")
    assert row["n_suppressed_cells"] == 1

    # And a figure CSV that prints its reason into a column NOT named `*_display` is still not
    # counted, which a suffix rule would miss in the other direction.
    unnamed = pd.DataFrame({"slug": ["debt_overall"],
                            "n": [FIGURE_SUPPRESSED_TOKEN],
                            "reason": [CELL_BELOW_THRESHOLD]})
    row = safe_export(unnamed, tmp_path / "results" / "figures-csv" / "unnamed.csv",
                      kind="figure-csv", count_cols=["n"])
    assert row["n_suppressed_cells"] == 1


def test_the_manifest_counts_the_token_and_the_sentinel_on_every_kind(tmp_path):
    # 8.3's first clause carries no kind qualifier, so the token counts wherever it is written,
    # including in a table CSV where section 5 forbids it -- a file already breaking section 5
    # should be reported, not understated.
    token_in_a_table = pd.DataFrame({"group": ["cervical"], "n": [FIGURE_SUPPRESSED_TOKEN]})
    row = safe_export(token_in_a_table, tmp_path / "results" / "tables-csv" / "t.csv",
                      kind="table-csv", count_cols=["n"])
    assert row["n_suppressed_cells"] == 1

    # The module's own sentinel is in no well-formed bundle cell of either kind.  It is counted
    # so that a sentinel which LEAKED into an export is reported rather than waved past, and
    # restricting it by kind would hide a leak on the kind where nothing else would see it.
    leaked = pd.DataFrame({"group": ["cervical"], "n": [SUPPRESSED]})
    row = safe_export(leaked, tmp_path / "results" / "figures-csv" / "f.csv",
                      kind="figure-csv", count_cols=["n"])
    assert row["n_suppressed_cells"] == 1


def test_the_manifest_does_not_count_a_sentence_when_no_kind_is_declared(tmp_path):
    # Without a `kind` the module has not been told which spelling the file uses, so a sentence
    # in it is a string of unknown meaning and reading it as hidden is the guess that produced
    # the 220.  This is the direction `export_violations`'s own kind clause already takes: no
    # declaration, no kind-specific behaviour.  10.4 requires `07_export.py` to declare `kind`
    # on all sixteen files, so nothing in the bundle arrives here undeclared.
    df = pd.DataFrame({"group": ["cervical", "lumbar"],
                       "n": [FIGURE_SUPPRESSED_TOKEN, CELL_BELOW_THRESHOLD]})
    row = safe_export(df, tmp_path / "results" / "figures-csv" / "undeclared.csv",
                      count_cols=["n"])
    assert row["n_suppressed_cells"] == 1


# ---- min_disclosed_count has no kind-dependent meaning -------------------------------
# 8.3 defines it as "the smallest count value written in the file, or empty when the file
# writes no count", with NO kind qualifier beside it -- unlike `n_suppressed_cells` one row
# below, whose sentence clause carries "in a table CSV" in the contract's own words.  A count
# is a count in either kind, so the arithmetic is kind-invariant and the field is taken from
# the DECLARED count columns and from nothing else.


def test_the_smallest_disclosed_count_does_not_depend_on_the_kind(tmp_path):
    # The same counts under both kinds give the same answer.  A table CSV's count column holds
    # numeral strings, which `to_numeric` parses; a figure CSV's holds integers.
    strings = pd.DataFrame({"group": ["cervical", "lumbar"], "n": ["60", "40"]})
    numbers = pd.DataFrame({"group": ["cervical", "lumbar"], "n": [60, 40]})
    as_table = safe_export(strings, tmp_path / "results" / "tables-csv" / "t.csv",
                           kind="table-csv", count_cols=["n"])
    as_figure = safe_export(numbers, tmp_path / "results" / "figures-csv" / "f.csv",
                            kind="figure-csv", count_cols=["n"])
    assert as_table["min_disclosed_count"] == as_figure["min_disclosed_count"] == 40


def test_the_smallest_disclosed_count_reads_the_declared_count_columns_only(tmp_path):
    # Widening it to every numeric column would sweep in Figure 4's `series_order` and its
    # `day_relative_to_event`, which reaches -14, and Figure 3's `row_order`.  None of the
    # three is a count, and the minimum over them is not the smallest count in the file.
    df = pd.DataFrame({"series_order": [1, 1, 2],
                       "day_relative_to_event": [-14, 0, 7],
                       "n_contributing": [60, 40, 80]})
    row = safe_export(df, tmp_path / "results" / "figures-csv" / "f4.csv",
                      kind="figure-csv", count_cols=["n_contributing"])
    assert row["min_disclosed_count"] == 40


def test_the_smallest_disclosed_count_ignores_a_suppressed_cell_in_every_representation(tmp_path):
    # A hidden cell is not a disclosed count, in any of the three spellings, so none of them
    # may become the minimum and a file that discloses nothing reports the empty string.
    for kind, hidden in (("figure-csv", FIGURE_SUPPRESSED_TOKEN),
                         ("table-csv", CELL_BELOW_THRESHOLD),
                         ("table-csv", SUPPRESSED)):
        df = pd.DataFrame({"group": ["cervical", "lumbar"], "n": [hidden, "40"]})
        row = safe_export(df, tmp_path / "results" / kind / f"{abs(hash(hidden))}.csv",
                          kind=kind, count_cols=["n"])
        assert row["min_disclosed_count"] == 40
        only_hidden = pd.DataFrame({"group": ["cervical"], "n": [hidden]})
        row = safe_export(only_hidden, tmp_path / "results" / kind / f"o{abs(hash(hidden))}.csv",
                          kind=kind, count_cols=["n"])
        assert row["min_disclosed_count"] == ""


def test_safe_export_parameters_after_the_path_are_keyword_only(tmp_path):
    with pytest.raises(TypeError):
        safe_export(_clean_frame(), tmp_path / "a.csv", ["n contributing"])


def test_safe_export_is_byte_stable_across_runs(tmp_path):
    first = safe_export(_clean_frame(), tmp_path / "a.csv", count_cols=["n contributing"])
    second = safe_export(_clean_frame(), tmp_path / "b.csv", count_cols=["n contributing"])
    assert first["md5"] == second["md5"]
    assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()


# ---- the data side of the separator boundary -----------------------------------------
# `safe_export` writes bytes.  A separator in a numeric CSV cell is a data corruption, not a
# style improvement: it makes the number unparseable to everything that reads the file back,
# and inside an unquoted field it invents a column.  These pin that the display-side fix did
# not reach the boundary, on the two frames that actually go over it.

# The md5 of each frame under the implementation BEFORE the thousands separator was added to
# `n_pct`, `prev` and `safe_show`.  Pinned as literals rather than as a same-run comparison,
# because a same-run comparison cannot see a change that moved a byte in BOTH runs.  If either
# of these goes red, an export byte moved, and the md5 discipline of EXPORT-CONTRACT.md 8.1 is
# what moved with it: the digest of a hand-carried file no longer matches the one recorded
# beside it in MANIFEST.csv.
LEDGER_MD5_BEFORE_THE_SEPARATOR = "9e73e6413f98eba3bd81bb812d9c63d7"
REGISTRY_MD5_BEFORE_THE_SEPARATOR = "86da18da08c92e224add3d47017dbfb4"


def test_an_exported_count_carries_no_thousands_separator(tmp_path):
    # A realistic ledger, not a toy: four, five and seven digit counts, which is where a
    # separator would appear at all.
    out = tmp_path / "results" / "ledgers-csv" / "ledger_exclusion_reasons.csv"
    safe_export(_ledger_frame(), out, count_cols=["episodes", "denominator"])
    raw = out.read_bytes()
    assert b"1,500" not in raw
    assert b"12,480" not in raw
    assert b"1,234,560" not in raw
    assert b"1500" in raw and b"12480" in raw and b"1234560" in raw
    # Every field is unquoted, which is only true while no cell holds a comma.
    assert b'"' not in raw
    # And the file still has exactly one comma per column boundary on every row.
    lines = raw.decode().strip().split("\n")
    assert {line.count(",") for line in lines} == {2}


def test_an_exported_count_reads_back_as_a_number(tmp_path):
    # The consequence a separator would take away.  `verify.py` parses the bundle back.
    out = tmp_path / "ledger.csv"
    safe_export(_ledger_frame(), out, count_cols=["episodes", "denominator"])
    back = pd.read_csv(out)
    assert back["episodes"].tolist() == _ledger_frame()["episodes"].tolist()
    assert pd.api.types.is_integer_dtype(back["episodes"])
    # And every cell read back is still a legal disclosed count, which it would not be if it
    # had been written with a separator: the predicate refuses "1,234,560".
    assert all(is_legal_disclosed_count(v) for v in back["episodes"])


def test_the_md5_of_an_exported_ledger_is_unchanged_by_the_separator_fix(tmp_path):
    out = tmp_path / "results" / "ledgers-csv" / "ledger_exclusion_reasons.csv"
    row = safe_export(_ledger_frame(), out, count_cols=["episodes", "denominator"])
    assert row["md5"] == LEDGER_MD5_BEFORE_THE_SEPARATOR
    assert md5_of_bytes(out.read_bytes()) == LEDGER_MD5_BEFORE_THE_SEPARATOR


def test_the_md5_of_the_real_registry_export_is_unchanged_by_the_separator_fix(tmp_path):
    # The real `cs_spine.registry_rows()` producer, exported the way EXPORT-CONTRACT.md 5.6
    # has `07_export.py` export it.
    out = tmp_path / "results" / "ledgers-csv" / "ledger_concept_set_registry.csv"
    row = safe_export(
        _registry_frame(), out, kind="table-csv", specification_columns=["code"]
    )
    assert row["md5"] == REGISTRY_MD5_BEFORE_THE_SEPARATOR


def test_safe_export_renders_no_count_of_its_own(tmp_path):
    # WHY the two md5 pins above can hold at all, stated as a property rather than left to be
    # inferred from two hashes: nothing on the display side of the boundary is reachable from
    # the export path.  `safe_export` writes the frame it is handed.
    import disclosure

    source = inspect.getsource(safe_export) + inspect.getsource(disclosure._integers_as_integers)
    assert "render_count" not in source
    assert "n_pct" not in source
    assert "prev(" not in source
    # What the export path DOES pin, and the three reasons two runs agree byte for byte.
    assert "float_format=FLOAT_FORMAT" in source
    assert "index=False" in source
    assert "lineterminator" in source


def test_safe_export_drops_the_index_and_pins_the_line_ending(tmp_path):
    out = tmp_path / "c.csv"
    safe_export(_clean_frame(), out, count_cols=["n contributing"])
    raw = out.read_bytes()
    assert raw.startswith(b"region,procedure,day,n contributing,median deficit\n")
    assert b"\r\n" not in raw


def test_safe_export_applies_the_float_format_and_it_is_the_decided_one(tmp_path):
    # DECIDED: %.6g, not the %.6f the contract carried.  Both are deterministic, so the md5
    # discipline is satisfied by either; %.6f flattens anything below 1e-6 to "0.000000", and a
    # tail probability that prints as zero is a correctness failure.  The two columns
    # discriminate all three candidates: `precise` separates %.6g from pandas' default repr,
    # `tail` separates %.6g from %.6f.
    df = pd.DataFrame(
        {
            "region": ["cervical"] * 5,
            "precise": [0.12345678901234] * 5,
            "tail": [1.5e-09] * 5,
        }
    )
    out = tmp_path / "floats.csv"
    safe_export(df, out)
    raw = out.read_bytes()
    assert FLOAT_FORMAT == "%.6g"
    assert b"0.123457" in raw                 # %.6g applied
    assert b"0.12345678901234" not in raw     # not the pandas default
    assert b"1.5e-09" in raw                  # %.6g on a tail value
    assert b"0.000000" not in raw             # which is what %.6f would have written


def test_safe_export_writes_whole_valued_floats_as_integers(tmp_path):
    # EXPORT-CONTRACT.md 8.2.  An INT64 column that has been through a LEFT JOIN arrives as
    # float64, and a count must not reach the manuscript as "340.0".
    # THE DISCRIMINATING VALUE IS A LARGE ONE.  A small whole float is already written as an
    # integer by %.6g, so a test on 40.0 alone cannot see whether the cast happened; %.6g keeps
    # six significant digits, so a count of 1,234,560 still carried as a float would be written
    # "1.23456e+06" and lose its last digit.  The cast is what keeps a count a count.
    df = pd.DataFrame({"region": ["cervical", "lumbar"], "n contributing": [40.0, 1234560.0]})
    out = tmp_path / "counts.csv"
    safe_export(df, out, count_cols=["n contributing"])
    raw = out.read_bytes()
    assert b"1234560" in raw
    assert b"1.23456e+06" not in raw
    assert b"40.0" not in raw
    assert raw.endswith(b"lumbar,1234560\n")


def test_safe_export_round_trips_to_the_same_values(tmp_path):
    out = tmp_path / "d.csv"
    safe_export(_clean_frame(), out, count_cols=["n contributing"])
    back = pd.read_csv(out)
    assert list(back.columns) == list(_clean_frame().columns)
    assert back["n contributing"].tolist() == _clean_frame()["n contributing"].tolist()


def test_safe_export_raises_on_a_dirty_frame_and_lists_every_violation(tmp_path):
    out = tmp_path / "blocked.csv"
    with pytest.raises(DisclosureError) as caught:
        safe_export(_dirty_frame(), out, count_cols=["n contributing"])
    message = str(caught.value)
    assert "4 disclosure violation(s)" in message
    for marker in ("n contributing", "participant identifier", "unshifted", "near-unique"):
        assert marker in message


def test_safe_export_refuses_a_non_tabular_extension(tmp_path):
    # Verified before this fix: this call wrote figure2.png and returned an md5 for it.
    out = tmp_path / "figure2.png"
    with pytest.raises(DisclosureError):
        safe_export(_clean_frame(), out, count_cols=["n contributing"])
    assert not out.exists()


def test_safe_export_writes_nothing_when_it_refuses(tmp_path):
    out = tmp_path / "nested" / "blocked.csv"
    with pytest.raises(DisclosureError):
        safe_export(_dirty_frame(), out, count_cols=["n contributing"])
    assert not out.exists()
    assert not out.parent.exists()   # not even the directory, so no half-made export tree
    assert list(tmp_path.iterdir()) == []


def test_safe_export_does_not_overwrite_an_existing_file_when_it_refuses(tmp_path):
    out = tmp_path / "existing.csv"
    good = safe_export(_clean_frame(), out, count_cols=["n contributing"])
    with pytest.raises(DisclosureError):
        safe_export(_dirty_frame(), out, count_cols=["n contributing"])
    assert hashlib.md5(out.read_bytes()).hexdigest() == good["md5"]


def test_safe_export_refuses_a_zero_cell_when_zero_is_not_allowed(tmp_path):
    df = _clean_frame()
    df.loc[0, "n contributing"] = 0
    out = tmp_path / "zero.csv"
    row = safe_export(df, out, count_cols=["n contributing"], allow_zero=True)
    assert row["md5"] == hashlib.md5(out.read_bytes()).hexdigest()
    out.unlink()
    with pytest.raises(DisclosureError):
        safe_export(df, out, count_cols=["n contributing"], allow_zero=False)
    assert not out.exists()


def test_safe_export_refuses_a_percentage_beside_a_suppressed_count(tmp_path):
    df = pd.DataFrame({"group": ["cervical"], "n": [SUPPRESSED], "pct": ["37%"]})
    out = tmp_path / "table2.csv"
    with pytest.raises(DisclosureError):
        safe_export(df, out, kind="table-csv", count_cols=["n"], percentage_columns=["pct"])
    assert not out.exists()


# ======================================================================================
# Constants and the module self-test
# ======================================================================================


def test_the_disclosure_constants_are_the_documented_ones():
    # T7 (00_config.ipynb) and T16 (07_export.py) both import these; pin them so a later edit
    # to the module is a deliberate change to the contract rather than a silent one.
    assert MIN_CELL == DOCUMENTED_FLOOR
    assert ROUND_BASE == MIN_CELL
    assert NEAR_UNIQUE_MIN_ROWS == MIN_CELL
    assert NEAR_UNIQUE_RATIO == 0.90
    assert SUPPRESSED == "<=20 (suppressed)"
    assert ALLOWED_EXPORT_SUFFIXES == (".csv", ".json", ".md5")
    assert MANIFEST_COLUMNS == (
        "file", "kind", "exhibit", "md5", "n_rows", "n_columns",
        "min_disclosed_count", "n_suppressed_cells", "description",
    )


def test_the_module_self_test_runs_and_passes(capsys):
    # `python3 disclosure.py` is the house pattern and its assertions were unprotected by CI:
    # nothing under pytest invoked them, so a mutant that broke one of them stayed green here.
    _run_self_test()
    printed = capsys.readouterr().out
    assert "SELF-TEST: PASS" in printed
    assert "assertions executed" in printed
