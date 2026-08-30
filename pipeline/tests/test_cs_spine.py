#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for `pipeline/cs_spine.py`.

Runs locally with no Workbench session, no network and no credentials:
    cd v1/pipeline && python3 -m pytest tests/ -q

Why this file exists
--------------------
`assert_concept_frame()` shipped with NO CALLER anywhere in the repo, and the only frame it had
ever seen was `cs_spine._synthetic_concept_frame()`, built from the same constants it validates
against.  Its count check was therefore satisfied by construction: it could not have failed, so
it proved nothing.  Everything below drives the helpers with frames that are wrong in one
specific, named way, because a validator is only worth what its REFUSALS are worth.

The 852-row fixture here is built independently of the module's own synthetic frame, from the
public lookups rather than by importing the private one.  The duplication is deliberate: a test
that reuses the fixture under test shares its blind spots.

`assert_concept_frame()` now has two production callers, `01_probe.py` (PROBE 3a) and
`02_pregate.py`, both of which run it on the frame the CDR actually returns.  One residue of the
original gap survives and is worth naming: neither those callers nor these tests have yet been
pointed at a real CDR, so drift between the locked 852-concept set and the live concept table
stays undetected until Phase 2 runs inside the perimeter.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

# Run the suite from anywhere: `pipeline/` is the import root for `cs_spine`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cs_spine  # noqa: E402  (path bootstrap must precede the import)
from cs_spine import (  # noqa: E402
    ALL_CPT,
    ALL_PCS_STEMS,
    ALL_SQL_BUILDERS,
    ANALYSIS_REGIONS,
    CDR_OF_RECORD,
    CERVICAL_DECOMPRESSION_CANDIDATE_CPT,
    CERVICAL_FUSION_CANDIDATE_CPT,
    CPT_ADD_ON,
    CPT_REGION,
    EXPECTED_CONCEPT_COUNT,
    EXPECTED_CPT_CONCEPTS,
    EXPECTED_PCS_DECOMPRESSION_CONCEPTS,
    EXPECTED_PCS_FUSION_CONCEPTS,
    JUNCTION_STEMS,
    PCS_DECOMPRESSION_STEMS,
    PCS_FUSION_STEMS,
    PCS_REGION,
    PCS_REGION_MIRRORED,
    PCS_REGION_PRIMARY,
    PLAN_REGION_ASSIGNMENT,
    REGIONS,
    REGISTRY_COLUMNS,
    SpineConceptSetError,
    assert_concept_frame,
    assert_snomed_frame,
    cervical_decompression_split_sql,
    cervical_fusion_split_sql,
    concept_resolution_sql,
    il,
    is_add_on_code,
    procedure_class_of,
    region_of,
    registry_rows,
    snomed_crosscheck_sql,
    source_concept_cte,
)

EM_DASH = chr(0x2014)


# ======================================================================================
# Fixtures.  A concept frame is what `concept_resolution_sql()` returns: one row per resolved
# source concept_id, carrying the seven declared columns.
# ======================================================================================


def _frame(*, mirror_junctions: bool = False) -> list[dict[str, Any]]:
    """An 852-row concept frame shaped like the real one.

    Built stem by stem rather than by the module's divmod split, so the two constructions can
    disagree.  The per-stem distribution of the 704 and the 118 is unknown offline and no
    assertion under test looks at it: what has to be right is the totals and each row's tags.
    """
    rows: list[dict[str, Any]] = []
    concept_id = 3_000_000
    for code in ALL_CPT:
        concept_id += 1
        rows.append({
            "concept_id": concept_id,
            "vocabulary_id": "CPT4",
            "concept_code": code,
            "concept_name": "CPT-4 " + code,
            "region": region_of("CPT4", code, mirror_junctions=mirror_junctions),
            "procedure_class": procedure_class_of("CPT4", code),
            "is_add_on": is_add_on_code("CPT4", code),
        })
    for stems, total in ((PCS_FUSION_STEMS, EXPECTED_PCS_FUSION_CONCEPTS),
                         (PCS_DECOMPRESSION_STEMS, EXPECTED_PCS_DECOMPRESSION_CONCEPTS)):
        ordered = sorted(stems)
        remaining = total
        for position, stem in enumerate(ordered):
            # Fill one code per stem, then give the whole remainder to the last stem.  A
            # deliberately lopsided split: if any assertion ever starts depending on an even
            # per-stem distribution, this fixture is what catches it.
            take = remaining - (len(ordered) - position - 1) if position == len(ordered) - 1 else 1
            for j in range(take):
                concept_id += 1
                code = f"{stem}{j:03d}"
                rows.append({
                    "concept_id": concept_id,
                    "vocabulary_id": "ICD10PCS",
                    "concept_code": code,
                    "concept_name": "ICD-10-PCS " + code,
                    "region": region_of("ICD10PCS", code, mirror_junctions=mirror_junctions),
                    "procedure_class": procedure_class_of("ICD10PCS", code),
                    "is_add_on": False,
                })
                remaining -= 1
    return rows


def _index_of(frame: list[dict[str, Any]], concept_code: str) -> int:
    for i, row in enumerate(frame):
        if row["concept_code"] == concept_code:
            return i
    raise LookupError(concept_code)


def _snomed_frame() -> list[dict[str, Any]]:
    """One row of what `snomed_crosscheck_sql()` returns, at full coverage."""
    return [{
        "vocabulary_id": "CPT4",
        "procedure_class": "fusion",
        "region": "cervical",
        "n_source": EXPECTED_CONCEPT_COUNT,
        "n_source_mapped": EXPECTED_CONCEPT_COUNT,
        "n_standard": 400,
    }]


# ======================================================================================
# The fixture itself has to be right, or every refusal test below is testing the fixture.
# ======================================================================================


def test_the_fixture_is_the_frame_the_module_expects():
    frame = _frame()
    assert len(frame) == EXPECTED_CONCEPT_COUNT
    assert sum(1 for r in frame if r["vocabulary_id"] == "CPT4") == EXPECTED_CPT_CONCEPTS
    assert sum(1 for r in frame if r["vocabulary_id"] == "ICD10PCS"
               and r["procedure_class"] == "fusion") == EXPECTED_PCS_FUSION_CONCEPTS
    assert sum(1 for r in frame if r["vocabulary_id"] == "ICD10PCS"
               and r["procedure_class"] == "decompression") == EXPECTED_PCS_DECOMPRESSION_CONCEPTS
    assert len({r["concept_id"] for r in frame}) == EXPECTED_CONCEPT_COUNT
    assert_concept_frame(frame)


def test_a_pandas_frame_validates_too():
    # Phase 2 hands this helper a BigQuery result, which arrives as a DataFrame.  The module
    # imports no pandas and duck-types instead, so the DataFrame path needs its own test.
    assert_concept_frame(pd.DataFrame(_frame()))


# ======================================================================================
# assert_concept_frame: the refusals.  One test per way a frame can be wrong.
# ======================================================================================


def test_an_empty_frame_is_refused():
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame([])
    assert "empty" in str(caught.value)


def test_a_short_count_is_refused_and_the_message_names_both_numbers():
    frame = _frame()[:-1]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    message = str(caught.value)
    assert str(EXPECTED_CONCEPT_COUNT) in message
    assert str(EXPECTED_CONCEPT_COUNT - 1) in message
    # It is a stop condition, not a note.  Pin the sentence that says so.
    assert "Do not proceed" in message


def test_a_long_count_is_refused():
    frame = _frame()
    frame.append(dict(frame[-1], concept_id=8_000_001, concept_code="0SB4999"))
    with pytest.raises(SpineConceptSetError):
        assert_concept_frame(frame)


def test_a_wrong_cpt_subtotal_is_refused_even_when_the_total_is_right():
    # The discriminating case: 852 rows, but 31 of them CPT-4.  A frame that fails only the
    # subtotal proves the subtotal check is reachable and is not shadowed by the total check.
    # 22554 is the real-world version of this: the CDR starting to return the legacy ACDF code.
    frame = _frame()
    frame.insert(0, dict(frame[0], concept_id=8_000_002, concept_code="22554",
                         concept_name="CPT-4 22554", region="cervical",
                         procedure_class="fusion", is_add_on=False))
    del frame[-1]
    assert len(frame) == EXPECTED_CONCEPT_COUNT
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "CPT-4" in str(caught.value)
    assert str(EXPECTED_CPT_CONCEPTS) in str(caught.value)


def test_a_missing_column_in_row_zero_is_refused():
    frame = [{k: v for k, v in r.items() if k != "region"} for r in _frame()]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "region" in str(caught.value)


def test_a_missing_column_in_a_LATE_row_is_refused_as_a_concept_set_error():
    # The bug this pins: the gate inspected `rows[0]` only, so deleting a column from row 500
    # sailed past it and surfaced as a bare KeyError from deep inside the validation loop.  A
    # caller whose stop condition is `except SpineConceptSetError` never sees a KeyError, so
    # the frame would have been treated as valid.  A DataFrame is rectangular and cannot
    # express this; a list of dicts, which these helpers accept by design, can.
    frame = _frame()
    del frame[500]["region"]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "region" in str(caught.value)
    assert "500" in str(caught.value)


def test_concept_name_is_part_of_the_column_contract():
    # `concept_resolution_sql()` selects it and the CTE contract declares it, so a frame
    # without it is not the frame this module asked for, whether or not an assertion reads it.
    assert "concept_name" in cs_spine._REQUIRED_COLUMNS
    frame = [{k: v for k, v in r.items() if k != "concept_name"} for r in _frame()]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "concept_name" in str(caught.value)


def test_a_null_region_is_refused():
    frame = _frame()
    frame[_index_of(frame, "22551")]["region"] = None
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "region" in str(caught.value)


def test_a_region_outside_the_closed_vocabulary_is_refused():
    frame = _frame()
    frame[_index_of(frame, "22551")]["region"] = "sacral"
    with pytest.raises(SpineConceptSetError):
        assert_concept_frame(frame)


def test_a_region_that_contradicts_the_locked_map_is_refused():
    frame = _frame()
    frame[_index_of(frame, "22551")]["region"] = "lumbar"   # 22551 is cervical
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "lumbar" in str(caught.value) and "cervical" in str(caught.value)


def test_a_null_procedure_class_is_refused():
    frame = _frame()
    frame[_index_of(frame, "22551")]["procedure_class"] = None
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "class" in str(caught.value)


def test_a_class_that_contradicts_the_locked_map_is_refused():
    frame = _frame()
    frame[_index_of(frame, "22551")]["procedure_class"] = "decompression"   # 22551 is fusion
    with pytest.raises(SpineConceptSetError):
        assert_concept_frame(frame)


def test_a_null_is_add_on_is_refused_and_is_not_read_as_false():
    # `bool(None)` is False, so before the fix a NULL flag on any of the fourteen non-add-on
    # codes matched what the map wanted and validated silently.  That was a hole in the
    # raise-on-NULL posture the region and class checks enforce one line above it.  22551 is
    # not an add-on, so this is exactly the row where a NULL used to pass.
    assert not is_add_on_code("CPT4", "22551")
    frame = _frame()
    frame[_index_of(frame, "22551")]["is_add_on"] = None
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "NULL add-on flag" in str(caught.value)


def test_a_null_is_add_on_on_an_add_on_code_is_also_refused():
    frame = _frame()
    frame[_index_of(frame, "22840")]["is_add_on"] = None    # 22840 IS an add-on
    with pytest.raises(SpineConceptSetError):
        assert_concept_frame(frame)


def test_an_add_on_flag_that_contradicts_the_locked_map_is_refused():
    frame = _frame()
    frame[_index_of(frame, "22551")]["is_add_on"] = True
    with pytest.raises(SpineConceptSetError):
        assert_concept_frame(frame)


def test_one_concept_id_carrying_two_regions_is_refused():
    frame = _frame()
    cervical = _index_of(frame, "22551")     # cervical
    lumbar = _index_of(frame, "22558")       # lumbar
    frame[lumbar]["concept_id"] = frame[cervical]["concept_id"]
    assert len(frame) == EXPECTED_CONCEPT_COUNT
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "two regions" in str(caught.value)


def test_one_concept_id_carrying_two_classes_is_refused():
    frame = _frame()
    fusion = _index_of(frame, "22600")          # cervical fusion
    decompression = _index_of(frame, "63020")   # cervical decompression, same region
    frame[decompression]["concept_id"] = frame[fusion]["concept_id"]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "two classes" in str(caught.value)


def test_a_cpt_code_resolving_to_two_concept_ids_is_named_rather_than_showing_as_a_bad_total():
    # The locked subtotal counts CODES; the frame counts CONCEPT IDS.  They agree only while
    # CPT-4 is one to one in this CDR.  Without a dedicated check this surfaces as "expected
    # 852, got 853" with no pointer at all to the cause.
    frame = _frame()
    frame.insert(1, dict(frame[_index_of(frame, "22551")], concept_id=8_000_003))
    del frame[-1]
    assert len(frame) == EXPECTED_CONCEPT_COUNT
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    message = str(caught.value)
    assert "more than one concept_id" in message
    assert "22551" in message


def test_a_code_that_did_not_resolve_is_refused_by_name():
    # Swap 22551 for a CPT-4 code outside the locked set, so the total is still 852 and the CPT
    # subtotal is still 30.  Only the "did every locked code resolve" check can fire, and it
    # has to name the code that went missing rather than report an arithmetic mismatch.
    frame = _frame()
    frame[_index_of(frame, "22551")]["concept_code"] = "22554"
    assert len(frame) == EXPECTED_CONCEPT_COUNT
    with pytest.raises(SpineConceptSetError) as caught:
        assert_concept_frame(frame)
    assert "22551" in str(caught.value)
    assert "did not resolve" in str(caught.value)


# ======================================================================================
# The mirror, both directions.  The sensitivity is prespecified, so it has to be impossible to
# validate a frame under the wrong map.
# ======================================================================================


def test_a_primary_frame_validates_under_the_primary_map_and_is_refused_under_the_mirror():
    frame = _frame()
    assert_concept_frame(frame)
    with pytest.raises(SpineConceptSetError):
        assert_concept_frame(frame, mirror_junctions=True)


def test_a_mirrored_frame_validates_under_the_mirror_and_is_refused_under_the_primary_map():
    frame = _frame(mirror_junctions=True)
    assert_concept_frame(frame, mirror_junctions=True)
    with pytest.raises(SpineConceptSetError):
        assert_concept_frame(frame)


def test_the_round_trip_is_not_vacuous_because_junction_stems_carry_real_rows():
    # If no junction stem had a row, the two directions above would pass for the empty reason.
    frame = _frame()
    junction_rows = sum(1 for r in frame
                        if r["vocabulary_id"] == "ICD10PCS"
                        and str(r["concept_code"])[:4] in JUNCTION_STEMS)
    assert junction_rows > 0


def test_the_mirror_moves_exactly_the_junction_stems():
    moved = {s for s in ALL_PCS_STEMS if PCS_REGION_PRIMARY[s] != PCS_REGION_MIRRORED[s]}
    assert moved == set(JUNCTION_STEMS)
    for stem in ALL_PCS_STEMS:
        assert region_of("ICD10PCS", stem) == PCS_REGION_PRIMARY[stem]
        assert region_of("ICD10PCS", stem, mirror_junctions=True) == PCS_REGION_MIRRORED[stem]


def test_cpt_codes_do_not_move_under_the_mirror():
    # CPT-4 has no junction construct, so the mirror is a no-op there.  A fact, not an
    # oversight, and the registry's two equal CPT columns depend on it.
    for code in ALL_CPT:
        assert region_of("CPT4", code) == region_of("CPT4", code, mirror_junctions=True)


# ======================================================================================
# assert_snomed_frame
# ======================================================================================


def test_a_fully_mapped_audit_frame_validates():
    assert_snomed_frame(_snomed_frame())


def test_an_audit_frame_missing_a_column_is_refused_rather_than_raising_a_key_error():
    frame = [{k: v for k, v in _snomed_frame()[0].items() if k != "n_source_mapped"}]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_snomed_frame(frame)
    assert "n_source_mapped" in str(caught.value)


def test_an_audit_that_does_not_cover_852_concepts_is_refused():
    frame = [dict(_snomed_frame()[0], n_source=851, n_source_mapped=851)]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_snomed_frame(frame)
    assert str(EXPECTED_CONCEPT_COUNT) in str(caught.value)


def test_an_incomplete_maps_to_mapping_is_refused():
    frame = [dict(_snomed_frame()[0], n_source_mapped=EXPECTED_CONCEPT_COUNT - 1)]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_snomed_frame(frame)
    assert "full coverage" in str(caught.value)


def test_more_mapped_than_source_is_refused_and_the_message_is_not_nonsense():
    # There was no upper bound, so n_source_mapped=900 against n_source=852 passed the total
    # check and then raised "only 900 of 852 source concepts have a 'Maps to' standard
    # concept".  A validator whose message is nonsense in the one case a reader has to act on
    # is worse than no message.
    frame = [dict(_snomed_frame()[0], n_source_mapped=900)]
    with pytest.raises(SpineConceptSetError) as caught:
        assert_snomed_frame(frame)
    message = str(caught.value)
    assert "cannot exceed" in message
    assert "only 900 of" not in message


def test_an_empty_audit_frame_is_refused():
    with pytest.raises(SpineConceptSetError):
        assert_snomed_frame([])


def test_the_audit_totals_are_summed_across_rows_not_read_from_one():
    # The real query groups by vocabulary, class and region, so it returns many rows.
    half = EXPECTED_CONCEPT_COUNT // 2
    frame = [dict(_snomed_frame()[0], n_source=half, n_source_mapped=half),
             dict(_snomed_frame()[0], region="lumbar",
                  n_source=EXPECTED_CONCEPT_COUNT - half,
                  n_source_mapped=EXPECTED_CONCEPT_COUNT - half)]
    assert_snomed_frame(frame)


# ======================================================================================
# The SQL builders.  Text only: what is testable offline is the contract, not the result.
# ======================================================================================


@pytest.mark.parametrize("builder", ALL_SQL_BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize("mirror", [False, True])
def test_every_builder_carries_the_cdr_placeholder(builder, mirror):
    assert "{CDR}" in builder(mirror_junctions=mirror)


@pytest.mark.parametrize("builder", ALL_SQL_BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize("mirror", [False, True])
def test_every_backticked_name_sits_behind_the_placeholder(builder, mirror):
    import re
    sql = builder(mirror_junctions=mirror)
    names = re.findall(r"`([^`]+)`", sql)
    assert names, "a builder that references no table cannot be checked for hardcoding"
    for name in names:
        assert name.startswith("{CDR}."), name


@pytest.mark.parametrize("builder", ALL_SQL_BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize("mirror", [False, True])
def test_no_builder_hardcodes_a_project_or_a_dataset(builder, mirror):
    import re
    sql = builder(mirror_junctions=mirror)
    # The CDR resource name is resolved at runtime with `wb resource resolve`, never typed.
    assert CDR_OF_RECORD not in sql
    # `wb-silky-artichoke-2408` and every other workbench project id share this shape.
    assert not re.search(r"\bwb-[a-z0-9-]+\b", sql)


@pytest.mark.parametrize("builder", ALL_SQL_BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize("mirror", [False, True])
def test_every_builder_is_byte_stable_across_two_calls(builder, mirror):
    # A diff of two builds is only meaningful if the same inputs give the same bytes.  Set
    # iteration order is the usual way this breaks, which is why every call site sorts.
    first = builder(mirror_junctions=mirror)
    second = builder(mirror_junctions=mirror)
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


@pytest.mark.parametrize("builder", ALL_SQL_BUILDERS, ids=lambda b: b.__name__)
def test_the_mirror_flag_actually_changes_the_emitted_sql(builder):
    # Otherwise the prespecified sensitivity would be a keyword that does nothing.
    assert builder(mirror_junctions=False) != builder(mirror_junctions=True)


@pytest.mark.parametrize("builder", ALL_SQL_BUILDERS, ids=lambda b: b.__name__)
@pytest.mark.parametrize("mirror", [False, True])
def test_no_builder_emits_unseeded_randomness_or_an_em_dash(builder, mirror):
    sql = builder(mirror_junctions=mirror)
    assert "RAND(" not in sql.upper()
    assert EM_DASH not in sql


def test_the_cte_name_is_not_a_parameter():
    # It used to be, and no downstream builder honoured it: all three composed against the
    # hardcoded name, so passing one emitted a CTE that nothing could consume.  Dropped rather
    # than threaded.  This pins the removal so it is not helpfully reinstated.
    import inspect
    assert list(inspect.signature(source_concept_cte).parameters) == ["mirror_junctions"]


def test_the_source_cte_name_is_the_one_every_downstream_builder_composes_against():
    for builder in (concept_resolution_sql, snomed_crosscheck_sql,
                    cervical_decompression_split_sql, cervical_fusion_split_sql):
        sql = builder()
        assert "WITH " + cs_spine._CTE_NAME + " AS (" in sql
        assert sql.count(cs_spine._CTE_NAME) >= 2   # declared, then consumed


def test_every_locked_code_and_stem_reaches_the_source_cte_the_exact_number_of_times():
    # Three CASE expressions and one WHERE are generated from the same maps, so each code has a
    # fixed, checkable multiplicity: region CASE, class CASE, WHERE, plus the add-on CASE for
    # the sixteen add-ons.  A code that appears more or fewer times than this is a code that
    # got into one generated clause and not another, which is how the SQL and the python maps
    # would start to drift.
    sql = source_concept_cte()
    for code in ALL_CPT:
        expected = 4 if code in CPT_ADD_ON else 3
        assert sql.count("'" + code + "'") == expected, code
    for stem in ALL_PCS_STEMS:
        assert sql.count("'" + stem + "'") == 3, stem


def test_il_quotes_and_joins_without_spaces():
    assert il(["a", "b"]) == "'a','b'"
    assert il([]) == ""


# ======================================================================================
# The two gap builders.  Neither amends the locked set; both put a number in front of a human.
# ======================================================================================


def test_the_fusion_gap_builder_measures_the_candidate_codes():
    sql = cervical_fusion_split_sql()
    for code in CERVICAL_FUSION_CANDIDATE_CPT:
        assert "'" + code + "'" in sql
    assert "22554" in sql


def test_the_decompression_gap_builder_measures_its_candidate_codes():
    sql = cervical_decompression_split_sql()
    for code in CERVICAL_DECOMPRESSION_CANDIDATE_CPT:
        assert "'" + code + "'" in sql


def test_neither_gap_builder_adds_a_candidate_code_to_the_locked_set():
    # Measuring a code is not adding it.  Amending the set would break the 852 assertion and
    # everything calibrated to it, so the candidates must stay outside every locked constant.
    for code in CERVICAL_FUSION_CANDIDATE_CPT + CERVICAL_DECOMPRESSION_CANDIDATE_CPT:
        assert code not in ALL_CPT
        assert code not in CPT_REGION
        assert code not in CPT_ADD_ON
    assert len(ALL_CPT) == EXPECTED_CPT_CONCEPTS


def test_the_wrong_arm_premise_is_real_and_stays_measured():
    # This is the whole reason the fusion builder exists: 63075 is IN the set and tagged
    # cervical decompression, while 22554 is NOT in the set.  So a legacy ACDF billed as 22554
    # with 63075 books as cervical DECOMPRESSION, on the wrong side of the primary contrast.
    # If either half of this ever stops being true the builder's docstring is wrong.
    assert "63075" in ALL_CPT
    assert region_of("CPT4", "63075") == "cervical"
    assert procedure_class_of("CPT4", "63075") == "decompression"
    assert "22554" not in ALL_CPT


def test_the_fusion_builder_reports_the_misroute_it_exists_to_size():
    sql = cervical_fusion_split_sql()
    assert "n_also_carrying_locked_cervical_decompression" in sql


def test_the_fusion_builder_counts_only_persons_with_fusion_or_candidate_evidence():
    # The misroute arm joins persons whose only cervical evidence is decompression.  Without
    # the guard they would fall through the CASE into 'candidate CPT only', which would be a
    # lie: they carry no candidate code, and the decision-critical row would be inflated.
    sql = cervical_fusion_split_sql()
    assert ("WHERE has_cpt_locked = 1 OR has_pcs_locked = 1 OR has_cpt_candidate = 1" in sql)


def test_both_gap_builders_return_the_same_four_evidence_paths():
    for sql in (cervical_decompression_split_sql(), cervical_fusion_split_sql()):
        for path in ("locked set: CPT and ICD-10-PCS", "locked set: CPT only",
                     "locked set: ICD-10-PCS only",
                     "candidate CPT only, invisible to the locked set"):
            assert "'" + path + "'" in sql


def test_the_decision_critical_row_sorts_FIRST_under_order_by_evidence_path():
    # The docstrings used to call it "the fourth row of the result" and the decision file's
    # table listed it fourth.  Both builders sort by the label, and 'candidate' precedes
    # 'locked'.  Anyone describing this result by position has to get the direction right.
    paths = ["locked set: CPT and ICD-10-PCS", "locked set: CPT only",
             "locked set: ICD-10-PCS only", "candidate CPT only, invisible to the locked set"]
    assert sorted(paths)[0] == "candidate CPT only, invisible to the locked set"
    for sql in (cervical_decompression_split_sql(), cervical_fusion_split_sql()):
        assert "ORDER BY evidence_path" in sql


def test_the_gap_builders_are_registered_so_the_self_test_checks_them():
    assert cervical_fusion_split_sql in ALL_SQL_BUILDERS
    assert cervical_decompression_split_sql in ALL_SQL_BUILDERS


# ======================================================================================
# The registry.  The STROBE supplement consumes these columns by name.
# ======================================================================================


def test_the_registry_has_one_row_per_locked_code_or_stem():
    registry = registry_rows()
    assert len(registry) == len(ALL_CPT) + len(ALL_PCS_STEMS)
    assert {r["code"] for r in registry} == set(ALL_CPT) | set(ALL_PCS_STEMS)


def test_the_registry_columns_are_the_declared_ones_in_order():
    for row in registry_rows():
        assert tuple(row) == REGISTRY_COLUMNS


def test_the_registry_has_no_bare_region_column_any_more():
    # The rename from `region` to `region_primary` is the point: a column called `region` gave
    # no clue which of the two assignments it held, which is how the tie-break got lost.
    assert "region" not in REGISTRY_COLUMNS
    assert "region_primary" in REGISTRY_COLUMNS and "region_mirrored" in REGISTRY_COLUMNS
    assert all("region" not in row for row in registry_rows())


def test_the_registry_is_identical_whichever_way_mirror_junctions_is_passed():
    # It used to drive `region` off the flag, which made the two columns identical under
    # mirror_junctions=True and erased the primary assignment in exactly the run where the
    # tie-break is what the reader came for.  Both assignments now ship on every call.
    assert registry_rows() == registry_rows(mirror_junctions=True)
    assert registry_rows(mirror_junctions=False) == registry_rows(mirror_junctions=True)


def test_every_junction_row_shows_two_different_regions():
    junctions = [r for r in registry_rows() if r["is_junction"]]
    assert len(junctions) == len(JUNCTION_STEMS)
    for row in junctions:
        assert row["region_primary"] != row["region_mirrored"]
        assert row["region_primary"] == PCS_REGION_PRIMARY[row["code"]]
        assert row["region_mirrored"] == PCS_REGION_MIRRORED[row["code"]]


def test_no_non_junction_row_moves_under_the_mirror():
    for row in registry_rows():
        if not row["is_junction"]:
            assert row["region_primary"] == row["region_mirrored"]


def test_the_registry_marks_add_ons_only_on_cpt_rows():
    for row in registry_rows():
        if row["vocabulary_id"] == "ICD10PCS":
            assert row["is_add_on"] is False
        else:
            assert row["is_add_on"] == (row["code"] in CPT_ADD_ON)


def test_the_registry_is_metadata_only():
    # It goes into the STROBE supplement verbatim, so nothing person-level may be in it.
    for row in registry_rows():
        assert set(row) == set(REGISTRY_COLUMNS)


# ======================================================================================
# The locked constants.  A "locked" map a caller can mutate is not locked.
# ======================================================================================


@pytest.mark.parametrize("name", ["CPT_REGION", "PCS_REGION_PRIMARY", "PCS_REGION_MIRRORED",
                                  "PCS_REGION", "PLAN_REGION_ASSIGNMENT"])
def test_every_locked_map_is_read_only(name):
    mapping = getattr(cs_spine, name)
    with pytest.raises(TypeError):
        mapping["ZZZZ"] = "cervical"
    with pytest.raises((TypeError, AttributeError)):
        mapping.update({"ZZZZ": "cervical"})


def test_the_pcs_region_alias_cannot_drift_from_the_primary_map():
    assert dict(PCS_REGION) == dict(PCS_REGION_PRIMARY)


def test_the_maps_cover_exactly_the_locked_sets():
    assert set(PCS_REGION_PRIMARY) == set(ALL_PCS_STEMS)
    assert set(PCS_REGION_MIRRORED) == set(ALL_PCS_STEMS)
    assert set(CPT_REGION) == set(ALL_CPT)
    assert all(r in REGIONS for r in PCS_REGION_PRIMARY.values())
    assert all(r in REGIONS for r in CPT_REGION.values())


def test_the_plan_assignment_expands_to_nineteen_stems_eighteen_of_them_locked():
    # The plan writes "0RG6 through 0RGA", which read character by character includes 0RG9.
    # The literal expansion is 19, not the 18 the prose used to claim.
    assert len(PLAN_REGION_ASSIGNMENT) == 19
    assert len(set(PLAN_REGION_ASSIGNMENT) & set(ALL_PCS_STEMS)) == 18
    assert set(PLAN_REGION_ASSIGNMENT) - set(ALL_PCS_STEMS) == {"0RG9"}


def test_no_icd10pcs_stem_is_in_the_add_on_set():
    # `is_add_on_code` short-circuits on vocabulary, so calling it on a stem proves nothing.
    # The claim worth testing is about the data behind the short-circuit, and nothing stops an
    # editor putting a four-character stem into the add-on set.
    assert not (CPT_ADD_ON & set(ALL_PCS_STEMS))
    assert CPT_ADD_ON <= set(ALL_CPT)


def test_thoracic_is_tagged_but_is_not_an_analysis_region():
    # Locked: a thoracic-only episode is excluded, on its own counted attrition rung.  The tag
    # still exists because the codes do.
    assert "thoracic" in REGIONS
    assert ANALYSIS_REGIONS == ("cervical", "lumbar")
    assert any(r == "thoracic" for r in PCS_REGION_PRIMARY.values())


# ======================================================================================
# The self-test's own banner.  316 was printed for years against a real 319 and was republished
# as fact in the locked decision file.
# ======================================================================================


def test_the_banner_assertion_count_is_measured_not_tallied(capsys):
    cs_spine._run_self_test()
    printed = capsys.readouterr().out
    measured = cs_spine._ASSERTIONS_EXECUTED
    assert f"assertions executed          : {measured}" in printed
    assert measured > 0


def test_the_assertion_count_is_reset_so_two_runs_agree(capsys):
    cs_spine._run_self_test()
    first = cs_spine._ASSERTIONS_EXECUTED
    cs_spine._run_self_test()
    second = cs_spine._ASSERTIONS_EXECUTED
    capsys.readouterr()
    assert first == second


def test_the_self_test_passes():
    cs_spine._run_self_test()   # raises AssertionError on any failure
