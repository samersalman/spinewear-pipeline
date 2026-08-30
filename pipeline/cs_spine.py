#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cs_spine.py -- the region-tagged spine concept set, single source of truth.

Owner: T3.  Every downstream query (`episodes`, `episodes_eligible`, the pre-gate counts,
Table 1's four procedure groups) builds from the code sets and the SQL fragments here.
Nothing downstream may enumerate a spine code of its own.

Runs LOCALLY, with no cloud access
----------------------------------
Everything in this file is either data or string assembly.  Importing it, calling any
builder, and running `_run_self_test()` all work on a laptop with the standard library
alone.  There is no BigQuery client here and no `pandas` import: the assertion helpers
duck-type the concept frame so a caller may hand them a DataFrame or a list of dicts.

Runs INSIDE the perimeter
-------------------------
The five SQL builders return TEXT ONLY.  The caller resolves `{CDR}` at runtime (never
hardcode a dataset: `wb resource resolve --name C2025Q4R6`), prints a dry-run byte estimate
before executing, and passes a hard `maximum_bytes_billed` cap so an over-budget query fails
rather than bills.  Then the caller runs `assert_concept_frame()` on what comes back, before
any downstream query is allowed to run.

Disclosure
----------
`concept_id` / `concept_code` / `concept_name` are vocabulary METADATA, not participant data,
so the resolved concept frame is safe to log in full, and so is `registry_rows()`.  The person
counts returned by the two gap builders, `cervical_decompression_split_sql()` and
`cervical_fusion_split_sql()`, are NOT: the caller rounds them to 20 and suppresses 1 to 20
before anything is printed or exported.

Provenance
----------
Code sets are frozen from the locked decision
`Projects/Pharmacogenomic-Prediction/decisions/2026-07-06-spine-phenotype.md`
(852 source concept ids: 30 CPT-4 + 704 ICD-10-PCS fusion + 118 ICD-10-PCS decompression).
The region tagging, the mirrored junction map, the add-on flags and the three open items are
this project's own additions, locked in `v1/decisions/2026-08-25-spine-region-tagging.md`.
Read that file before changing a single code below.

House rule on prose: no em-dash anywhere.  Enforced on the emitted SQL by the self-test.
Column names in the emitted SQL are deliberately snake case; the house ban on snake case
applies to rendered manuscript strings, not to SQL identifiers or developer diagnostics.
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence


class SpineConceptSetError(ValueError):
    """Raised when the concept set does not reconcile.  Never downgraded to a warning."""


# ============================================================================
# (0) The in-list helper, same semantics as `GWAS/_transfer/pivot_common.py`.
# ============================================================================
def il(xs: Iterable[Any]) -> str:
    """Render an iterable as a SQL in-list body: ``'a','b'``.

    Identical to the sibling projects' `il` lambda so a reader moving between them does not
    have to re-check quoting.  Call sites sort their input, which keeps the emitted SQL
    byte-stable across runs and makes a diff of two builds meaningful.
    """
    return ",".join("'" + str(x) + "'" for x in xs)


# ============================================================================
# (1) The locked counts.
#     A DIFFERENT NUMBER AT RUNTIME MEANS THE CDR CONCEPT TABLE CHANGED, and every count,
#     cohort and estimate built on top of this set is suspect until the change is explained.
#     These are stop conditions: `assert_concept_frame()` raises, it does not warn.
# ============================================================================
EXPECTED_CONCEPT_COUNT: int = 852
EXPECTED_CPT_CONCEPTS: int = 30
EXPECTED_PCS_FUSION_CONCEPTS: int = 704
EXPECTED_PCS_DECOMPRESSION_CONCEPTS: int = 118

CDR_OF_RECORD: str = "C2025Q4R6"  # the CDR the 852 was measured against; resolve, never hardcode

REGIONS: tuple[str, ...] = ("cervical", "thoracic", "lumbar", "unspecified")
PROCEDURE_CLASSES: tuple[str, ...] = ("fusion", "decompression")

# The plan's Table 1 has four columns and none of them is thoracic.  A `thoracic` tag is a
# real tag, not an analysis group.
#
# The call is now made and locked (decision file, Judgment call 3): a THORACIC-ONLY episode is
# EXCLUDED, on its own counted rung of the attrition ladder.  The protocol's target population
# is "elective surgery for degenerative cervical or lumbar disease" and the study title says
# cervical and lumbar; a retained thoracic group would contradict both.  This tuple is the
# episode builder's inclusion filter, not a display convenience: an episode whose regional
# evidence resolves to nothing in ANALYSIS_REGIONS does not enter the analytic cohort.
ANALYSIS_REGIONS: tuple[str, ...] = ("cervical", "lumbar")


# ============================================================================
# (2) CPT-4, frozen from the locked decision.
# ============================================================================
# Fusion, 21 codes.  Arthrodesis primaries, then the additional-level add-ons, then
# instrumentation, then interbody devices.
CPT_FUSION: tuple[str, ...] = (
    "22551", "22558", "22600", "22610", "22612", "22630", "22633",   # arthrodesis primaries
    "22614", "22632", "22634",                                       # additional-level add-ons
    "22840", "22841", "22842", "22843", "22844",                     # posterior instrumentation, wiring
    "22845", "22846", "22847", "22848",                              # anterior instrumentation, pelvic fixation
    "22853", "22854",                                                # interbody biomechanical device
)

# Decompression, 9 codes.
CPT_DECOMPRESSION: tuple[str, ...] = (
    "63005", "63012", "63017",   # laminectomy, lumbar
    "63020",                     # laminotomy / hemilaminectomy, cervical
    "63030",                     # laminotomy, lumbar
    "63047",                     # laminectomy / facetectomy / foraminotomy, lumbar
    "63075",                     # discectomy, anterior, cervical
    "63035", "63048",            # additional-interspace / additional-segment add-ons
)

ALL_CPT: tuple[str, ...] = tuple(sorted(set(CPT_FUSION) | set(CPT_DECOMPRESSION)))

# Add-on and instrumentation codes.  The protocol is explicit: "Additional-level and
# instrumentation codes cannot define an operation without a primary procedure code."  The
# episode builder MUST require at least one code with `is_add_on = FALSE` before it will call
# a same-day bundle an operation.
#
# The locked decision file annotates 22840-22848 and 22853/22854 as instrumentation and marks
# 63035 and 63048 as add-ons ("+ add-on" in its own text).  It does NOT annotate 22614, 22632
# or 22634, which are all AMA add-on codes ("each additional vertebral segment" /
# "each additional interspace").  They are flagged here.  See the decision file, section
# "What the locked file's own annotations missed".
CPT_ADD_ON: frozenset[str] = frozenset({
    "22614", "22632", "22634",
    "22840", "22841", "22842", "22843", "22844", "22845", "22846", "22847", "22848",
    "22853", "22854",
    "63035", "63048",
})

# Region implied by the CPT descriptor.  Every add-on is 'unspecified' by rule, not by
# accident: an add-on's region comes from the primary code it is billed against, and several
# of them ("cervical or lumbar" for 63035, "cervical, thoracic, or lumbar" for 63048) name no
# single region at all.  22632 and 22634 are lumbar in practice because their only parents are
# lumbar, but the uniform rule is applied so that no add-on can ever contribute a region.
#
# Read-only: a "locked" map that a caller can mutate is not locked.  Every map in this module
# is a MappingProxyType for the same reason `REGIONS` and `CPT_ADD_ON` are a tuple and a
# frozenset.  `dict(CPT_REGION)` still gives a working copy to anyone who needs one.
CPT_REGION: Mapping[str, str] = MappingProxyType({
    # fusion primaries
    "22551": "cervical",     # ACDF, anterior interbody, cervical below C2
    "22600": "cervical",     # posterior / posterolateral arthrodesis, cervical below C2
    "22610": "thoracic",     # posterior / posterolateral arthrodesis, thoracic
    "22558": "lumbar",       # anterior interbody arthrodesis, lumbar
    "22612": "lumbar",       # posterior / posterolateral arthrodesis, lumbar
    "22630": "lumbar",       # posterior interbody arthrodesis, lumbar
    "22633": "lumbar",       # combined posterolateral and interbody arthrodesis, lumbar
    # decompression primaries
    "63020": "cervical",     # laminotomy, cervical, single interspace
    "63075": "cervical",     # anterior discectomy, cervical, single interspace
    "63005": "lumbar",       # laminectomy, lumbar
    "63012": "lumbar",       # Gill-type laminectomy, lumbar
    "63017": "lumbar",       # laminectomy, more than 2 segments, lumbar
    "63030": "lumbar",       # laminotomy, lumbar, single interspace
    "63047": "lumbar",       # laminectomy / facetectomy / foraminotomy, lumbar, single segment
    # add-on and instrumentation, region-free by rule
    "22614": "unspecified", "22632": "unspecified", "22634": "unspecified",
    "22840": "unspecified", "22841": "unspecified", "22842": "unspecified",
    "22843": "unspecified", "22844": "unspecified", "22845": "unspecified",
    "22846": "unspecified", "22847": "unspecified", "22848": "unspecified",
    "22853": "unspecified", "22854": "unspecified",
    "63035": "unspecified", "63048": "unspecified",
})

# NOT part of the locked set.  MEASURED by `cervical_decompression_split_sql()`, which is how
# Phase 2 quantifies the gap so the human can amend the set or prespecify the omission as a
# sensitivity.  Measuring a code is not adding it: nothing here reaches `ALL_CPT`, the region
# maps or the 852.
# The protocol's own cervical decompression row is 63001, 63015, 63020, 63040, 63045, 63048;
# the locked set carries only 63020 and 63075.
CERVICAL_DECOMPRESSION_CANDIDATE_CPT: tuple[str, ...] = ("63001", "63015", "63040", "63045")

# Same shape of gap on the cervical FUSION side, and the more consequential of the two.  22554
# is the legacy anterior cervical arthrodesis the protocol pairs with 63075; 22590 and 22595
# are occiput-C2 and C1-C2 arthrodesis.  None is in the locked set, and 63075 IS, so a
# legacy-coded ACDF (22554 with 63075) currently classifies as cervical DECOMPRESSION.  That is
# not a missing case, it is a case counted on the wrong arm of the primary estimand, which
# biases the fusion versus decompression contrast toward the null.
# MEASURED by `cervical_fusion_split_sql()`, the symmetric builder, so both gap numbers reach
# the human at the same Phase 2 stop.  Also not added to the set; see the decision file.
CERVICAL_FUSION_CANDIDATE_CPT: tuple[str, ...] = ("22554", "22590", "22595")


# ============================================================================
# (3) ICD-10-PCS, frozen from the locked decision.  Matched on SUBSTR(concept_code, 1, 4).
# ============================================================================
# Fusion, root operation G, vertebral body parts only.  704 concept_ids.
PCS_FUSION_STEMS: tuple[str, ...] = (
    "0RG0", "0RG1", "0RG2", "0RG4", "0RG6", "0RG7", "0RG8", "0RGA",  # upper joints
    "0SG0", "0SG1", "0SG3",                                          # lower joints
)

# Decompression: spinal cord / meninges release plus disc excision.  118 concept_ids.
PCS_DECOMPRESSION_STEMS: tuple[str, ...] = (
    "00NT", "00NW", "00NX", "00NY",           # release of spinal meninges / cord
    "0RB3", "0RB5", "0RB9", "0RBB",           # excision, cervical to thoracolumbar disc
    "0SB2", "0SB4",                           # excision, lumbar / lumbosacral disc
)

ALL_PCS_STEMS: tuple[str, ...] = tuple(sorted(set(PCS_FUSION_STEMS) | set(PCS_DECOMPRESSION_STEMS)))

# The junction stems.  ICD-10-PCS character 4 names a two-region joint or disc, so the region
# is a tie-break and not a fact.  The primary rule is "assign the junction to the CRANIAL
# member of the pair", which reproduces the plan's own thoracolumbar choice; the mirror is
# "assign to the CAUDAL member".  Both are named so the mirror runs as a prespecified
# sensitivity rather than as an afterthought.
CERVICOTHORACIC_STEMS: frozenset[str] = frozenset({"0RG4", "0RB5"})
THORACOLUMBAR_STEMS: frozenset[str] = frozenset({"0RGA", "0RBB"})
JUNCTION_STEMS: frozenset[str] = CERVICOTHORACIC_STEMS | THORACOLUMBAR_STEMS

# Character 4 = T is "Spinal Meninges", which names no vertebral level at all.  This is not a
# tie-break, it is an absence: the code cannot carry a region and none is invented for it.
# Protocol exclusion 3 removes an episode whose coding "cannot establish an anatomic region",
# so an episode whose only evidence is 00NT is not classifiable and must be dropped upstream
# of analysis.  Where 00NT sits beside a level-bearing code on the same date it still
# contributes procedure_class = 'decompression' and takes its region from that code.
LEVEL_AGNOSTIC_PCS_STEMS: frozenset[str] = frozenset({"00NT"})

# PRIMARY region map.  Junctions to the cranial member.  Built as a private dict because the
# mirrored map is derived from it, then published read-only.
_PCS_REGION_PRIMARY: dict[str, str] = {
    "0RG0": "cervical",   # fusion, occipital-cervical joint
    "0RG1": "cervical",   # fusion, cervical vertebral joint
    "0RG2": "cervical",   # fusion, cervical vertebral joints, 2 or more
    "0RB3": "cervical",   # excision, cervical vertebral disc
    "00NW": "cervical",   # release, cervical spinal cord
    "0RG4": "cervical",   # fusion, CERVICOTHORACIC vertebral joint          (junction tie-break)
    "0RB5": "cervical",   # excision, CERVICOTHORACIC vertebral disc         (junction tie-break)
    "0RG6": "thoracic",   # fusion, thoracic vertebral joint
    "0RG7": "thoracic",   # fusion, thoracic vertebral joints, 2 to 7
    "0RG8": "thoracic",   # fusion, thoracic vertebral joints, 8 or more
    "0RB9": "thoracic",   # excision, thoracic vertebral disc
    "00NX": "thoracic",   # release, thoracic spinal cord
    "0RGA": "thoracic",   # fusion, THORACOLUMBAR vertebral joint            (junction tie-break)
    "0RBB": "thoracic",   # excision, THORACOLUMBAR vertebral disc           (junction tie-break)
    "0SG0": "lumbar",     # fusion, lumbar vertebral joint
    "0SG1": "lumbar",     # fusion, lumbar vertebral joints, 2 or more
    "0SG3": "lumbar",     # fusion, lumbosacral joint
    "0SB2": "lumbar",     # excision, lumbar vertebral disc
    "0SB4": "lumbar",     # excision, lumbosacral disc
    "00NY": "lumbar",     # release, lumbar spinal cord
    "00NT": "unspecified",  # release, spinal meninges: no level in the code
}
PCS_REGION_PRIMARY: Mapping[str, str] = MappingProxyType(_PCS_REGION_PRIMARY)

# MIRRORED region map.  Identical except that every junction goes to the caudal member.
# This is the prespecified sensitivity, not an alternative anyone gets to pick after seeing
# a number.
_PCS_REGION_MIRRORED: dict[str, str] = dict(_PCS_REGION_PRIMARY)
_PCS_REGION_MIRRORED.update({
    "0RG4": "thoracic",   # cervicothoracic joint, mirrored to the caudal member
    "0RB5": "thoracic",   # cervicothoracic disc,  mirrored to the caudal member
    "0RGA": "lumbar",     # thoracolumbar joint,   mirrored to the caudal member
    "0RBB": "lumbar",     # thoracolumbar disc,    mirrored to the caudal member
})
PCS_REGION_MIRRORED: Mapping[str, str] = MappingProxyType(_PCS_REGION_MIRRORED)

# The default alias, so a caller that does not care about the sensitivity still gets the
# locked primary map by name rather than by accident.  It aliases the read-only PROXY, not the
# dict behind it, so the two names cannot be made to disagree and neither can be mutated.
PCS_REGION: Mapping[str, str] = PCS_REGION_PRIMARY


# ============================================================================
# (4) Reconciliation against the plan's own assignment.
#     Encoded as data so "nothing silently dropped, nothing silently invented" is a TESTED
#     claim and not a sentence in a report.  The self-test asserts both directions.
# ============================================================================
# Plan, Phase 2 item 2, read literally.  "0RG6 through 0RGA" is expanded character by
# character, which is why 0RG9 appears: it is what the range says, and it is NOT in the
# locked set.  0RG9 would be "thoracic vertebral DISC", which is not a valid body part for
# root operation G (a disc is excised, not fused), so no such fusion code exists to add.
# Nineteen stems, which is what the range says once it is expanded; eighteen of them are in
# the locked set and 0RG9 is not.
PLAN_REGION_ASSIGNMENT: Mapping[str, str] = MappingProxyType({
    "0RG0": "cervical", "0RG1": "cervical", "0RG2": "cervical",
    "0RB3": "cervical", "00NW": "cervical",
    "0SG0": "lumbar", "0SG1": "lumbar", "0SG3": "lumbar",
    "0SB2": "lumbar", "0SB4": "lumbar", "00NY": "lumbar",
    "0RG6": "thoracic", "0RG7": "thoracic", "0RG8": "thoracic", "0RG9": "thoracic",
    "0RGA": "thoracic", "0RB9": "thoracic", "0RBB": "thoracic", "00NX": "thoracic",
})

# In the locked set, given no region by the plan.  Resolved here, each on the anatomy the
# code actually denotes, and each named in the decision file.
STEMS_LOCKED_NOT_ASSIGNED_BY_PLAN: frozenset[str] = (
    frozenset(ALL_PCS_STEMS) - frozenset(PLAN_REGION_ASSIGNMENT)
)

# Assigned a region by the plan, absent from the locked set.  Not added.
STEMS_ASSIGNED_BY_PLAN_NOT_LOCKED: frozenset[str] = (
    frozenset(PLAN_REGION_ASSIGNMENT) - frozenset(ALL_PCS_STEMS)
)


# ============================================================================
# (5) Pure-python lookups.  The SQL CASE expressions are GENERATED from these, so the SQL and
#     the python can never drift apart: there is one map, not two.
# ============================================================================
def procedure_class_of(vocabulary_id: str, concept_code: str) -> str:
    """Return 'fusion' or 'decompression'.  Raises on anything not in the locked set."""
    if vocabulary_id == "CPT4":
        if concept_code in CPT_FUSION:
            return "fusion"
        if concept_code in CPT_DECOMPRESSION:
            return "decompression"
        raise SpineConceptSetError(f"CPT-4 code {concept_code!r} is not in the locked set")
    if vocabulary_id == "ICD10PCS":
        stem = concept_code[:4]
        if stem in PCS_FUSION_STEMS:
            return "fusion"
        if stem in PCS_DECOMPRESSION_STEMS:
            return "decompression"
        raise SpineConceptSetError(f"ICD-10-PCS stem {stem!r} is not in the locked set")
    raise SpineConceptSetError(f"vocabulary {vocabulary_id!r} is not part of the spine set")


def region_of(vocabulary_id: str, concept_code: str, *, mirror_junctions: bool = False) -> str:
    """Return the anatomic region tag.  Raises on anything not in the locked set."""
    if vocabulary_id == "CPT4":
        try:
            return CPT_REGION[concept_code]
        except KeyError:
            raise SpineConceptSetError(
                f"CPT-4 code {concept_code!r} has no region in the locked set") from None
    if vocabulary_id == "ICD10PCS":
        stem = concept_code[:4]
        table = PCS_REGION_MIRRORED if mirror_junctions else PCS_REGION_PRIMARY
        try:
            return table[stem]
        except KeyError:
            raise SpineConceptSetError(
                f"ICD-10-PCS stem {stem!r} has no region in the locked set") from None
    raise SpineConceptSetError(f"vocabulary {vocabulary_id!r} is not part of the spine set")


def is_add_on_code(vocabulary_id: str, concept_code: str) -> bool:
    """True for an add-on or instrumentation-only code, which cannot define an operation.

    ICD-10-PCS has no add-on construct: every PCS code is a complete procedure statement, so
    the flag is always False there.  That is a fact about the vocabulary, not a default.
    """
    return vocabulary_id == "CPT4" and concept_code in CPT_ADD_ON


REGISTRY_COLUMNS: tuple[str, ...] = (
    "vocabulary_id", "match", "code", "procedure_class",
    "region_primary", "region_mirrored", "is_add_on", "is_junction",
)


def registry_rows(*, mirror_junctions: bool = False) -> list[dict[str, Any]]:
    """The concept-set registry the STROBE supplement needs, as metadata-only rows.

    One row per locked code or stem, carrying BOTH region assignments so a reader can see the
    junction tie-break without re-running anything.

    `region_primary` and `region_mirrored` are read from `PCS_REGION_PRIMARY` and
    `PCS_REGION_MIRRORED` UNCONDITIONALLY, so this registry is byte-identical whichever way it
    is called.  An earlier version drove `region` off `mirror_junctions`, which made the two
    columns identical under `mirror_junctions=True` and so erased the primary assignment in
    exactly the run where the tie-break is the thing the reader came for.

    `mirror_junctions` is accepted and deliberately IGNORED, so a caller threading the flag
    through every builder does not have to special-case this one.  It cannot change the output:
    both assignments are always present.

    On the 30 CPT-4 rows the two region columns are equal, and that is a fact rather than a
    copy: the mirror is a tie-break between the two members of an ICD-10-PCS junction body
    part, and CPT-4 has no junction construct to break.
    """
    del mirror_junctions  # see the docstring: both assignments ship on every call
    rows: list[dict[str, Any]] = []
    for code in ALL_CPT:
        rows.append({
            "vocabulary_id": "CPT4",
            "match": "exact code",
            "code": code,
            "procedure_class": procedure_class_of("CPT4", code),
            "region_primary": CPT_REGION[code],
            "region_mirrored": CPT_REGION[code],
            "is_add_on": is_add_on_code("CPT4", code),
            "is_junction": False,
        })
    for stem in ALL_PCS_STEMS:
        rows.append({
            "vocabulary_id": "ICD10PCS",
            "match": "first four characters",
            "code": stem,
            "procedure_class": procedure_class_of("ICD10PCS", stem),
            "region_primary": PCS_REGION_PRIMARY[stem],
            "region_mirrored": PCS_REGION_MIRRORED[stem],
            "is_add_on": False,
            "is_junction": stem in JUNCTION_STEMS,
        })
    return rows


# ============================================================================
# (6) SQL builders.  Text only; `{CDR}` is resolved by the caller at runtime.
#     Shape follows `GWAS/notebooks/s2_part_a.py`: a source-code CTE, then an audit on top.
# ============================================================================
_CTE_NAME = "spine_src"


def _in_clause(vocabulary_id: str, codes: Sequence[str]) -> str:
    if vocabulary_id == "CPT4":
        return "vocabulary_id = 'CPT4' AND concept_code IN (" + il(sorted(codes)) + ")"
    return ("vocabulary_id = 'ICD10PCS' AND SUBSTR(concept_code, 1, 4) IN ("
            + il(sorted(codes)) + ")")


def _labelled_case_sql(labels: Sequence[str], label_of, alias: str) -> str:
    """Build a CASE over the locked set, bucketing by whatever `label_of` returns.

    ELSE is NULL, and today it is UNREACHABLE: `source_concept_cte()` generates its WHERE and
    these WHENs from the same two sets, so no surviving row can miss a WHEN.  It is kept as
    defence in depth against one specific future edit, the one that widens the WHERE without
    widening the CASE.  Under that edit the extra rows arrive as NULLs that
    `assert_concept_frame()` raises on, instead of arriving under a quiet default label that
    would carry a wrong region or class all the way into Table 1.  The cost of keeping it is
    one line of SQL; the cost of dropping it is a silent mislabel.
    """
    buckets: dict[str, dict[str, list[str]]] = {}
    for code in ALL_CPT:
        buckets.setdefault(label_of("CPT4", code), {}).setdefault("CPT4", []).append(code)
    for stem in ALL_PCS_STEMS:
        buckets.setdefault(label_of("ICD10PCS", stem), {}).setdefault("ICD10PCS", []).append(stem)
    lines: list[str] = []
    for label in labels:                              # fixed order keeps the SQL byte-stable
        for vocabulary_id in ("CPT4", "ICD10PCS"):
            codes = buckets.get(label, {}).get(vocabulary_id, [])
            if codes:
                lines.append("      WHEN " + _in_clause(vocabulary_id, codes)
                             + " THEN '" + label + "'")
    return ("    CASE\n" + "\n".join(lines)
            + "\n      ELSE NULL   -- unreachable today; a NULL here is a stop condition\n"
            + "    END AS " + alias)


def source_concept_cte(*, mirror_junctions: bool = False) -> str:
    """The source-code CTE: the locked codes resolved to concept_ids and tagged.

    Matches `procedure_source_concept_id` the way the locked phenotype does: CPT-4 on the
    exact code, ICD-10-PCS on the first four characters.  No domain, validity or standard
    filter is applied, because the locked 852 was measured without one and adding a filter
    here would change the number without changing the phenotype.

    The CTE name is the module constant `_CTE_NAME` and is not a parameter.  It used to be one,
    and no downstream builder honoured it: all three composed their SQL against the hardcoded
    `spine_src`, so passing a name emitted a CTE that nothing could consume.  A knob that only
    breaks things is worse than no knob.
    """
    return (
        "WITH " + _CTE_NAME + " AS (\n"
        "  SELECT\n"
        "    concept_id, vocabulary_id, concept_code, concept_name,\n"
        + _labelled_case_sql(REGIONS, lambda v, c: region_of(
            v, c, mirror_junctions=mirror_junctions), "region") + ",\n"
        + _labelled_case_sql(PROCEDURE_CLASSES, procedure_class_of, "procedure_class") + ",\n"
        "    CASE WHEN vocabulary_id = 'CPT4'\n"
        "              AND concept_code IN (" + il(sorted(CPT_ADD_ON)) + ")\n"
        "         THEN TRUE ELSE FALSE END AS is_add_on\n"
        "  FROM `{CDR}.concept`\n"
        "  WHERE (" + _in_clause("CPT4", ALL_CPT) + ")\n"
        "     OR (" + _in_clause("ICD10PCS", ALL_PCS_STEMS) + ")\n"
        ")\n"
    )


def concept_resolution_sql(*, mirror_junctions: bool = False) -> str:
    """Resolve the locked set to concept_ids.  Feed the result to `assert_concept_frame()`.

    Vocabulary metadata only, so the whole frame is safe to log as the concept-set registry.
    """
    return (
        source_concept_cte(mirror_junctions=mirror_junctions)
        + "SELECT concept_id, vocabulary_id, concept_code, concept_name,\n"
          "       region, procedure_class, is_add_on\n"
          "FROM " + _CTE_NAME + "\n"
          "ORDER BY procedure_class, region, vocabulary_id, concept_code\n"
    )


def snomed_crosscheck_sql(*, mirror_junctions: bool = False) -> str:
    """The SNOMED reconciliation audit.  The source-code path stays primary.

    COUNT(DISTINCT concept_id) rather than COUNT(*): a source concept with two 'Maps to' rows
    would otherwise be counted twice and the total would not reconcile against 852.  The
    locked decision reports 852 of 852 mapped, so anything short of full coverage in a column
    is a change in the CDR's vocabulary, not a change in this code set.
    """
    return (
        source_concept_cte(mirror_junctions=mirror_junctions)
        + ", mapped AS (\n"
          "  SELECT s.vocabulary_id, s.procedure_class, s.region, s.concept_id,\n"
          "         cr.concept_id_2 AS standard_concept_id\n"
          "  FROM " + _CTE_NAME + " s\n"
          "  LEFT JOIN `{CDR}.concept_relationship` cr\n"
          "    ON cr.concept_id_1 = s.concept_id AND cr.relationship_id = 'Maps to'\n"
          ")\n"
          "SELECT vocabulary_id, procedure_class, region,\n"
          "       COUNT(DISTINCT concept_id) AS n_source,\n"
          "       COUNT(DISTINCT IF(standard_concept_id IS NULL, NULL, concept_id))"
          " AS n_source_mapped,\n"
          "       COUNT(DISTINCT standard_concept_id) AS n_standard\n"
          "FROM mapped\n"
          "GROUP BY vocabulary_id, procedure_class, region\n"
          "ORDER BY vocabulary_id, procedure_class, region\n"
    )


def cervical_decompression_split_sql(*, mirror_junctions: bool = False) -> str:
    """Measure the CPT versus ICD-10-PCS split for cervical decompression.

    This exists to put a number in front of the human in Phase 2, not to change the set.  The
    locked set carries two cervical decompression CPT codes (63020, 63075) where the protocol
    names six, so cervical decompression-only episodes should arrive mostly through
    ICD-10-PCS.  The decision-critical row is 'candidate CPT only, invisible to the locked
    set': the incremental yield of amending the set, persons the locked set cannot see at all.
    `ORDER BY evidence_path` sorts it FIRST of the four, because 'candidate' precedes 'locked'
    alphabetically.  Do not describe it by position without checking the sort.

    Read this beside `cervical_fusion_split_sql()`.  Both gap numbers, decompression and
    fusion, belong in front of the human at the SAME stop: amending one side and not the other
    would move the fusion versus decompression contrast on its own.

    Person-level, matching how the locked decision counted.  Add-on codes are excluded from
    the CPT arm because an add-on cannot define an operation.  Note that 00NT (release of
    spinal meninges) carries no region and so appears in NEITHER arm: a cervical decompression
    coded only as 00NT is invisible to any region filter, which is the point of open item 3.

    Returns person counts.  The caller rounds to 20 and suppresses 1 to 20 before printing.
    """
    return (
        source_concept_cte(mirror_junctions=mirror_junctions)
        + ", cervical_decompression AS (\n"
          "  SELECT concept_id, 'cpt locked' AS evidence FROM " + _CTE_NAME + "\n"
          "  WHERE region = 'cervical' AND procedure_class = 'decompression'\n"
          # `is_add_on = FALSE` is redundant TODAY: every add-on is tagged 'unspecified', so
          # `region = 'cervical'` has already removed all sixteen of them.  Kept because it
          # states the protocol rule the arm depends on, and because it is the one line that
          # still holds if a later edit ever gives an add-on a region.
          "    AND vocabulary_id = 'CPT4' AND is_add_on = FALSE\n"
          "  UNION ALL\n"
          "  SELECT concept_id, 'pcs locked' FROM " + _CTE_NAME + "\n"
          "  WHERE region = 'cervical' AND procedure_class = 'decompression'\n"
          "    AND vocabulary_id = 'ICD10PCS'\n"
          "  UNION ALL\n"
          "  SELECT concept_id, 'cpt candidate' FROM `{CDR}.concept`\n"
          "  WHERE vocabulary_id = 'CPT4'\n"
          "    AND concept_code IN (" + il(CERVICAL_DECOMPRESSION_CANDIDATE_CPT) + ")\n"
          ")\n"
          ", per_person AS (\n"
          "  SELECT p.person_id,\n"
          "         MAX(IF(c.evidence = 'cpt locked', 1, 0))    AS has_cpt_locked,\n"
          "         MAX(IF(c.evidence = 'pcs locked', 1, 0))    AS has_pcs_locked,\n"
          "         MAX(IF(c.evidence = 'cpt candidate', 1, 0)) AS has_cpt_candidate\n"
          "  FROM `{CDR}.procedure_occurrence` p\n"
          "  JOIN cervical_decompression c\n"
          "    ON c.concept_id = p.procedure_source_concept_id\n"
          "  GROUP BY p.person_id\n"
          ")\n"
          "SELECT\n"
          "  CASE\n"
          "    WHEN has_cpt_locked = 1 AND has_pcs_locked = 1"
          " THEN 'locked set: CPT and ICD-10-PCS'\n"
          "    WHEN has_cpt_locked = 1"
          "                        THEN 'locked set: CPT only'\n"
          "    WHEN has_pcs_locked = 1"
          "                        THEN 'locked set: ICD-10-PCS only'\n"
          "    ELSE 'candidate CPT only, invisible to the locked set'\n"
          "  END AS evidence_path,\n"
          "  COUNT(*) AS n_persons,\n"
          "  SUM(has_cpt_candidate) AS n_also_carrying_candidate_cpt\n"
          "FROM per_person\n"
          "GROUP BY evidence_path\n"
          "ORDER BY evidence_path\n"
    )


def cervical_fusion_split_sql(*, mirror_junctions: bool = False) -> str:
    """Measure the cervical FUSION gap: the prevalence of 22554, 22590 and 22595.

    The symmetric partner of `cervical_decompression_split_sql()`, and the more consequential
    of the two.  The decompression gap costs cases; this one MISFILES them.  22554 is the
    legacy anterior cervical arthrodesis and it is absent from the locked set, while 63075
    (anterior cervical discectomy) is present and tagged cervical decompression.  So a
    legacy-coded ACDF billed as 22554 with 63075 arrives today as cervical DECOMPRESSION.  A
    case on the wrong arm of the primary contrast is worse than a case missing from both:
    it biases fusion versus decompression toward the null in a way no attrition count reveals.

    Same four mutually exclusive evidence paths, same `ORDER BY evidence_path`, so 'candidate
    CPT only, invisible to the locked set' sorts FIRST here too.

    Three counts per path:
      n_persons                                     persons on that path
      n_also_carrying_candidate_cpt                 of those, how many carry 22554, 22590 or
                                                    22595, so the locked-set rows answer "how
                                                    many candidate carriers the set ALREADY
                                                    sees as cervical fusion"
      n_also_carrying_locked_cervical_decompression of those, how many carry a locked cervical
                                                    decompression code.  On the three locked
                                                    rows this is ordinary fusion with
                                                    decompression, which plan section 2.4
                                                    classifies as fusion.  On the FIRST row it
                                                    is the misroute itself: persons the locked
                                                    set books as cervical decompression whose
                                                    fusion code it cannot see.

    This measures; it does not amend.  Amending the locked set would break the 852 assertion
    and everything calibrated to it.  Both gap numbers go to the human at the same Phase 2
    stop, because amending one side alone would move the primary contrast on its own.

    Person-level.  Add-on codes are excluded from the locked CPT arm because an add-on cannot
    define an operation.  Returns person counts: the caller rounds to 20 and suppresses 1 to 20
    before anything is printed or exported.
    """
    return (
        source_concept_cte(mirror_junctions=mirror_junctions)
        + ", cervical_fusion AS (\n"
          "  SELECT concept_id, 'cpt locked' AS evidence FROM " + _CTE_NAME + "\n"
          "  WHERE region = 'cervical' AND procedure_class = 'fusion'\n"
          # Redundant today for the same reason as in the decompression builder: every add-on
          # is tagged 'unspecified', so the region filter has already dropped all sixteen.
          # Kept because it states the protocol rule the arm rests on.
          "    AND vocabulary_id = 'CPT4' AND is_add_on = FALSE\n"
          "  UNION ALL\n"
          "  SELECT concept_id, 'pcs locked' FROM " + _CTE_NAME + "\n"
          "  WHERE region = 'cervical' AND procedure_class = 'fusion'\n"
          "    AND vocabulary_id = 'ICD10PCS'\n"
          "  UNION ALL\n"
          "  SELECT concept_id, 'cpt candidate' FROM `{CDR}.concept`\n"
          "  WHERE vocabulary_id = 'CPT4'\n"
          "    AND concept_code IN (" + il(sorted(CERVICAL_FUSION_CANDIDATE_CPT)) + ")\n"
          "  UNION ALL\n"
          # The misroute arm.  Not an evidence path of its own: it never sets has_cpt_locked or
          # has_pcs_locked, so it cannot move a person between the four rows.  It only reports
          # where the locked set is currently filing these operations.
          "  SELECT concept_id, 'cervical decompression' FROM " + _CTE_NAME + "\n"
          "  WHERE region = 'cervical' AND procedure_class = 'decompression'\n"
          "    AND is_add_on = FALSE\n"
          ")\n"
          ", per_person AS (\n"
          "  SELECT p.person_id,\n"
          "         MAX(IF(c.evidence = 'cpt locked', 1, 0))    AS has_cpt_locked,\n"
          "         MAX(IF(c.evidence = 'pcs locked', 1, 0))    AS has_pcs_locked,\n"
          "         MAX(IF(c.evidence = 'cpt candidate', 1, 0)) AS has_cpt_candidate,\n"
          "         MAX(IF(c.evidence = 'cervical decompression', 1, 0))"
          " AS has_locked_cervical_decompression\n"
          "  FROM `{CDR}.procedure_occurrence` p\n"
          "  JOIN cervical_fusion c\n"
          "    ON c.concept_id = p.procedure_source_concept_id\n"
          "  GROUP BY p.person_id\n"
          ")\n"
          "SELECT\n"
          "  CASE\n"
          "    WHEN has_cpt_locked = 1 AND has_pcs_locked = 1"
          " THEN 'locked set: CPT and ICD-10-PCS'\n"
          "    WHEN has_cpt_locked = 1"
          "                        THEN 'locked set: CPT only'\n"
          "    WHEN has_pcs_locked = 1"
          "                        THEN 'locked set: ICD-10-PCS only'\n"
          "    ELSE 'candidate CPT only, invisible to the locked set'\n"
          "  END AS evidence_path,\n"
          "  COUNT(*) AS n_persons,\n"
          "  SUM(has_cpt_candidate) AS n_also_carrying_candidate_cpt,\n"
          "  SUM(has_locked_cervical_decompression)"
          " AS n_also_carrying_locked_cervical_decompression\n"
          "FROM per_person\n"
          # The misroute arm joins persons who have cervical DECOMPRESSION and no cervical
          # fusion evidence of any kind.  Without this filter every such person would fall
          # through the CASE into 'candidate CPT only', which would be a lie: they carry no
          # candidate code.  Every arm in the decompression builder sets one of its three
          # flags, so that builder needs no equivalent line.
          "WHERE has_cpt_locked = 1 OR has_pcs_locked = 1 OR has_cpt_candidate = 1\n"
          "GROUP BY evidence_path\n"
          "ORDER BY evidence_path\n"
    )


ALL_SQL_BUILDERS = (
    source_concept_cte,
    concept_resolution_sql,
    snomed_crosscheck_sql,
    cervical_decompression_split_sql,
    cervical_fusion_split_sql,
)


# ============================================================================
# (7) Assertion helpers.  These RAISE.  A caller runs them on the frame that comes back from
#     `concept_resolution_sql()` before any downstream query is allowed to run.
# ============================================================================
# The full column contract of `concept_resolution_sql()`, `concept_name` included.  It is in
# the SELECT and in the declared CTE contract, so a frame without it is not the frame this
# module asked for, whether or not any assertion below reads it.
_REQUIRED_COLUMNS = ("concept_id", "vocabulary_id", "concept_code", "concept_name",
                     "region", "procedure_class", "is_add_on")

# The full column contract of `snomed_crosscheck_sql()`.
_REQUIRED_SNOMED_COLUMNS = ("vocabulary_id", "procedure_class", "region",
                            "n_source", "n_source_mapped", "n_standard")


def _rows(frame: Any) -> list[Mapping[str, Any]]:
    """Accept a pandas DataFrame or any iterable of mappings, so this module needs no pandas."""
    to_dict = getattr(frame, "to_dict", None)
    if callable(to_dict):
        return list(to_dict("records"))
    return [dict(row) for row in frame]


def _assert_columns(rows: Sequence[Mapping[str, Any]], required: Sequence[str], what: str) -> None:
    """Raise unless EVERY row carries every required column.

    Row 0 is not the frame.  A DataFrame is rectangular so row 0 would do, but these helpers
    duck-type deliberately and a list of dicts is not: checking only row 0 let a frame with
    `region` deleted from row 500 through the column gate and then raise a bare `KeyError` deep
    inside the loop below.  A caller that catches `SpineConceptSetError` as its stop condition
    would miss that entirely, which is the whole failure mode this gate exists to prevent.
    """
    for index, row in enumerate(rows):
        missing = [c for c in required if c not in row]
        if missing:
            where = "" if index == 0 else f" (first seen at row {index})"
            raise SpineConceptSetError(f"{what} is missing columns: {missing}{where}")


def assert_concept_frame(frame: Any, *, mirror_junctions: bool = False) -> None:
    """Raise unless the resolved concept frame reconciles against the locked decision.

    Checks, in order: every row carries every column; CPT-4 resolves one concept_id per code;
    the total is 852; the CPT-4 and the two ICD-10-PCS subtotals match; every locked code and
    stem actually resolved; every row carries a region and a class from the closed
    vocabularies; every row's region, class and add-on flag match this module's maps exactly;
    and no concept_id carries two regions or two classes.
    """
    rows = _rows(frame)
    if not rows:
        raise SpineConceptSetError("the concept frame is empty; the resolution query returned nothing")
    _assert_columns(rows, _REQUIRED_COLUMNS, "the concept frame")

    # BEFORE the total, so the failure is legible.  `EXPECTED_CPT_CONCEPTS = 30` counts CPT-4
    # CODES; the frame counts CONCEPT IDS.  The two agree only while CPT-4 is 1:1 in this CDR,
    # which it is today and which nothing here guarantees.  If one code ever resolved to two
    # concept_ids the total check would fire first with "expected 852, got 853" and no pointer
    # at all to the cause, so this runs ahead of it and names the code.
    cpt_ids_by_code: dict[str, set[Any]] = {}
    for row in rows:
        if row["vocabulary_id"] == "CPT4":
            cpt_ids_by_code.setdefault(str(row["concept_code"]), set()).add(row["concept_id"])
    multi_id_cpt = sorted(c for c, ids in cpt_ids_by_code.items() if len(ids) > 1)
    if multi_id_cpt:
        raise SpineConceptSetError(
            f"CPT-4 codes resolving to more than one concept_id: {multi_id_cpt}. "
            f"The locked subtotal of {EXPECTED_CPT_CONCEPTS} counts CODES and this frame counts "
            "concept ids; they agree only while CPT-4 is one to one in the CDR. The CDR "
            "vocabulary changed. Do not proceed.")

    if len(rows) != EXPECTED_CONCEPT_COUNT:
        raise SpineConceptSetError(
            f"expected {EXPECTED_CONCEPT_COUNT} source concepts, got {len(rows)}. "
            "The CDR concept table changed; every downstream count is suspect until this is "
            "explained. Do not proceed.")

    n_cpt = sum(1 for r in rows if r["vocabulary_id"] == "CPT4")
    n_pcs_fusion = sum(1 for r in rows
                       if r["vocabulary_id"] == "ICD10PCS" and r["procedure_class"] == "fusion")
    n_pcs_dec = sum(1 for r in rows
                    if r["vocabulary_id"] == "ICD10PCS" and r["procedure_class"] == "decompression")
    for got, want, what in ((n_cpt, EXPECTED_CPT_CONCEPTS, "CPT-4"),
                            (n_pcs_fusion, EXPECTED_PCS_FUSION_CONCEPTS, "ICD-10-PCS fusion"),
                            (n_pcs_dec, EXPECTED_PCS_DECOMPRESSION_CONCEPTS,
                             "ICD-10-PCS decompression")):
        if got != want:
            raise SpineConceptSetError(f"expected {want} {what} concepts, got {got}")

    resolved_cpt = {r["concept_code"] for r in rows if r["vocabulary_id"] == "CPT4"}
    missing_cpt = sorted(set(ALL_CPT) - resolved_cpt)
    if missing_cpt:
        raise SpineConceptSetError(f"CPT-4 codes did not resolve against the CDR: {missing_cpt}")
    resolved_stems = {str(r["concept_code"])[:4] for r in rows if r["vocabulary_id"] == "ICD10PCS"}
    missing_stems = sorted(set(ALL_PCS_STEMS) - resolved_stems)
    if missing_stems:
        raise SpineConceptSetError(f"ICD-10-PCS stems did not resolve against the CDR: {missing_stems}")

    regions_by_concept: dict[Any, set[str]] = {}
    classes_by_concept: dict[Any, set[str]] = {}
    for row in rows:
        code = str(row["concept_code"])
        vocabulary_id = str(row["vocabulary_id"])
        region = row["region"]
        procedure_class = row["procedure_class"]
        if region is None or region not in REGIONS:
            raise SpineConceptSetError(
                f"{vocabulary_id} {code} carries region {region!r}, which is not one of {REGIONS}")
        if procedure_class is None or procedure_class not in PROCEDURE_CLASSES:
            raise SpineConceptSetError(
                f"{vocabulary_id} {code} carries class {procedure_class!r}, "
                f"which is not one of {PROCEDURE_CLASSES}")
        want_region = region_of(vocabulary_id, code, mirror_junctions=mirror_junctions)
        if region != want_region:
            raise SpineConceptSetError(
                f"{vocabulary_id} {code} came back as {region!r}, the locked map says {want_region!r}")
        want_class = procedure_class_of(vocabulary_id, code)
        if procedure_class != want_class:
            raise SpineConceptSetError(
                f"{vocabulary_id} {code} came back as {procedure_class!r}, "
                f"the locked map says {want_class!r}")
        add_on = row["is_add_on"]
        # A NULL flag must raise, not be read as False.  `bool(None)` is False, so before this
        # line a NULL on any of the fourteen non-add-on codes matched what the map wanted and
        # validated silently: a hole in exactly the raise-on-NULL posture the region and class
        # checks above enforce.  This module's own SQL cannot produce one (`CASE ... ELSE
        # FALSE`), but this helper validates whatever a caller hands it.
        if add_on is None:
            raise SpineConceptSetError(
                f"{vocabulary_id} {code} carries a NULL add-on flag; the flag decides whether a "
                "code may define an operation and it has no safe default")
        want_add_on = is_add_on_code(vocabulary_id, code)
        if bool(add_on) != want_add_on:
            raise SpineConceptSetError(
                f"{vocabulary_id} {code} add-on flag is {add_on!r}, expected {want_add_on!r}")
        regions_by_concept.setdefault(row["concept_id"], set()).add(region)
        classes_by_concept.setdefault(row["concept_id"], set()).add(procedure_class)

    two_regions = sorted(str(k) for k, v in regions_by_concept.items() if len(v) > 1)
    if two_regions:
        raise SpineConceptSetError(f"concept_ids carrying two regions: {two_regions}")
    two_classes = sorted(str(k) for k, v in classes_by_concept.items() if len(v) > 1)
    if two_classes:
        raise SpineConceptSetError(f"concept_ids carrying two classes: {two_classes}")


def assert_snomed_frame(frame: Any) -> None:
    """Raise unless the SNOMED audit still shows every source concept mapping to a standard one.

    The locked decision measured 852 of 852.  A shortfall means the CDR's vocabulary changed,
    which is worth knowing even though the source-code path stays primary.
    """
    rows = _rows(frame)
    if not rows:
        raise SpineConceptSetError("the SNOMED audit frame is empty")
    _assert_columns(rows, _REQUIRED_SNOMED_COLUMNS, "the SNOMED audit frame")
    total_source = sum(int(r["n_source"]) for r in rows)
    total_mapped = sum(int(r["n_source_mapped"]) for r in rows)
    if total_source != EXPECTED_CONCEPT_COUNT:
        raise SpineConceptSetError(
            f"the SNOMED audit covers {total_source} source concepts, expected "
            f"{EXPECTED_CONCEPT_COUNT}")
    # An EXCESS is checked before a shortfall, and separately.  `n_source_mapped` is built as a
    # COUNT(DISTINCT ...) over the same concept_ids as `n_source`, so it cannot exceed it: if
    # it does, the query is not the one this helper is written against and no conclusion drawn
    # from either number is safe.  Falling through to the shortfall branch instead printed
    # "only 900 of 852 source concepts have a 'Maps to' standard concept", which is nonsense in
    # the one place a reader most needs a message they can act on.
    if total_mapped > total_source:
        raise SpineConceptSetError(
            f"the SNOMED audit reports {total_mapped} mapped source concepts out of "
            f"{total_source}; a mapped count cannot exceed the source count, so this frame did "
            "not come from snomed_crosscheck_sql()")
    if total_mapped != total_source:
        raise SpineConceptSetError(
            f"only {total_mapped} of {total_source} source concepts have a 'Maps to' standard "
            "concept; the locked decision measured full coverage")


# ============================================================================
# (8) Self-test.  Everything checkable without the cloud.
# ============================================================================
# The banner's assertion count is MEASURED, not tallied.  A hand-maintained `n += k` beside
# each block drifted from the truth (it printed 316 against a real 319) because a `k` cannot
# see a loop bound that changes, and the wrong number was then republished as fact in the
# locked decision file.  Every check below goes through one of the three helpers and every
# helper increments this, so the count cannot be wrong about the code it sits in.
_ASSERTIONS_EXECUTED = 0


def _expect(condition: bool, message: str) -> None:
    global _ASSERTIONS_EXECUTED
    _ASSERTIONS_EXECUTED += 1
    if not condition:
        raise AssertionError(message)


def _expect_raises(exc: type, fn, message: str) -> BaseException:
    global _ASSERTIONS_EXECUTED
    _ASSERTIONS_EXECUTED += 1
    try:
        fn()
    except exc as caught:
        return caught
    except BaseException as wrong:  # noqa: BLE001 - the wrong exception is still a failure
        raise AssertionError(f"{message}: raised {type(wrong).__name__} instead") from None
    raise AssertionError(f"{message}: nothing raised")


def _expect_ok(fn, message: str) -> Any:
    """The positive path: a helper that is supposed to accept this input and say nothing.

    It exists so a passing `assert_concept_frame()` call is COUNTED like every other check.
    The old tally credited these calls without routing them through a helper, which is half of
    why the printed number was wrong.
    """
    global _ASSERTIONS_EXECUTED
    _ASSERTIONS_EXECUTED += 1
    try:
        return fn()
    except BaseException as caught:  # noqa: BLE001 - any raise here is the failure
        raise AssertionError(f"{message}: raised {type(caught).__name__}: {caught}") from None


def _synthetic_concept_frame(*, mirror_junctions: bool = False) -> list[dict[str, Any]]:
    """A fake 852-row frame built from the constants, so the assertions are exercised locally.

    The per-stem distribution of the 704 and the 118 is unknown offline and does not matter:
    the assertions test totals and per-row validity, never a per-stem count.
    """
    rows: list[dict[str, Any]] = []
    concept_id = 2_000_000
    for code in ALL_CPT:
        concept_id += 1
        rows.append({
            "concept_id": concept_id, "vocabulary_id": "CPT4", "concept_code": code,
            "concept_name": "synthetic " + code,
            "region": region_of("CPT4", code, mirror_junctions=mirror_junctions),
            "procedure_class": procedure_class_of("CPT4", code),
            "is_add_on": is_add_on_code("CPT4", code),
        })
    for stems, total in ((PCS_FUSION_STEMS, EXPECTED_PCS_FUSION_CONCEPTS),
                         (PCS_DECOMPRESSION_STEMS, EXPECTED_PCS_DECOMPRESSION_CONCEPTS)):
        base, extra = divmod(total, len(stems))
        for i, stem in enumerate(sorted(stems)):
            for j in range(base + (1 if i < extra else 0)):
                concept_id += 1
                code = f"{stem}{j:03d}"
                rows.append({
                    "concept_id": concept_id, "vocabulary_id": "ICD10PCS", "concept_code": code,
                    "concept_name": "synthetic " + code,
                    "region": region_of("ICD10PCS", code, mirror_junctions=mirror_junctions),
                    "procedure_class": procedure_class_of("ICD10PCS", code),
                    "is_add_on": False,
                })
    return rows


def _run_self_test() -> None:
    global _ASSERTIONS_EXECUTED
    _ASSERTIONS_EXECUTED = 0        # so a second call reports its own run

    # -- (a) the two classes never overlap --------------------------------
    _expect(not (set(CPT_FUSION) & set(CPT_DECOMPRESSION)),
            "no CPT-4 code is in both the fusion and the decompression list")
    _expect(not (set(PCS_FUSION_STEMS) & set(PCS_DECOMPRESSION_STEMS)),
            "no ICD-10-PCS stem is in both the fusion and the decompression list")

    # -- (b) list lengths match the locked subtotals -----------------------
    _expect(len(CPT_FUSION) == 21, f"21 CPT-4 fusion codes, got {len(CPT_FUSION)}")
    _expect(len(CPT_DECOMPRESSION) == 9, f"9 CPT-4 decompression codes, got {len(CPT_DECOMPRESSION)}")
    # 30 CODES, and EXPECTED_CPT_CONCEPTS counts CONCEPT IDS.  The two are the same number only
    # while CPT-4 is one to one in this CDR, which it is today.  `assert_concept_frame()` tests
    # that premise on the real frame and names the offending code if it ever stops holding.
    _expect(len(ALL_CPT) == EXPECTED_CPT_CONCEPTS, f"30 CPT-4 codes, got {len(ALL_CPT)}")
    _expect(len(PCS_FUSION_STEMS) == 11, f"11 fusion stems, got {len(PCS_FUSION_STEMS)}")
    _expect(len(PCS_DECOMPRESSION_STEMS) == 10, f"10 decompression stems, got {len(PCS_DECOMPRESSION_STEMS)}")
    _expect(len(ALL_PCS_STEMS) == 21, f"21 stems in total, got {len(ALL_PCS_STEMS)}")
    _expect(EXPECTED_CPT_CONCEPTS + EXPECTED_PCS_FUSION_CONCEPTS
            + EXPECTED_PCS_DECOMPRESSION_CONCEPTS == EXPECTED_CONCEPT_COUNT,
            "the three subtotals add to 852")

    # -- (c) the region map covers exactly the locked stem set -------------
    _expect(set(PCS_REGION_PRIMARY) == set(ALL_PCS_STEMS),
            "the primary region map covers exactly the locked stems")
    _expect(set(PCS_REGION_MIRRORED) == set(ALL_PCS_STEMS),
            "the mirrored region map covers exactly the locked stems")
    _expect(set(CPT_REGION) == set(ALL_CPT), "the CPT-4 region map covers exactly the locked codes")
    for stem in ALL_PCS_STEMS:
        _expect(PCS_REGION_PRIMARY[stem] in REGIONS, f"{stem} has a valid primary region")
        _expect(PCS_REGION_MIRRORED[stem] in REGIONS, f"{stem} has a valid mirrored region")

    # -- (d) the mirror flips the junctions and nothing else ---------------
    flipped = {s for s in ALL_PCS_STEMS if PCS_REGION_PRIMARY[s] != PCS_REGION_MIRRORED[s]}
    _expect(flipped == set(JUNCTION_STEMS),
            f"the mirror flips exactly the junction stems, it flipped {sorted(flipped)}")
    for stem in CERVICOTHORACIC_STEMS:
        _expect((PCS_REGION_PRIMARY[stem], PCS_REGION_MIRRORED[stem]) == ("cervical", "thoracic"),
                f"{stem} runs cranial then caudal")
    for stem in THORACOLUMBAR_STEMS:
        _expect((PCS_REGION_PRIMARY[stem], PCS_REGION_MIRRORED[stem]) == ("thoracic", "lumbar"),
                f"{stem} runs cranial then caudal")

    # -- (e) only the declared stems and codes may be region-free ----------
    for stem in ALL_PCS_STEMS:
        unspecified = PCS_REGION_PRIMARY[stem] == "unspecified"
        _expect(unspecified == (stem in LEVEL_AGNOSTIC_PCS_STEMS),
                f"{stem} is region-free only if it was declared region-free")
    for code in ALL_CPT:
        unspecified = CPT_REGION[code] == "unspecified"
        _expect(unspecified == (code in CPT_ADD_ON),
                f"CPT-4 {code} is region-free exactly when it is an add-on")

    # -- (f) the add-on flags -----------------------------------------------
    _expect(CPT_ADD_ON <= set(ALL_CPT), "every add-on code is in the locked set")
    _expect(len(CPT_ADD_ON) == 16, f"16 add-on and instrumentation codes, got {len(CPT_ADD_ON)}")
    _expect({"22840", "22841", "22842", "22843", "22844", "22845", "22846", "22847",
             "22848", "22853", "22854"} <= CPT_ADD_ON, "the locked file's instrumentation codes are flagged")
    _expect({"63035", "63048"} <= CPT_ADD_ON, "the locked file's add-on codes are flagged")
    _expect({"22614", "22632", "22634"} <= CPT_ADD_ON,
            "the additional-level codes the locked file left unannotated are flagged")
    _expect(sum(1 for c in ALL_CPT if c not in CPT_ADD_ON) == 14,
            "14 CPT-4 codes can define an operation")
    # This used to read `not any(is_add_on_code("ICD10PCS", s) for s in ALL_PCS_STEMS)`, which
    # could not fail: `is_add_on_code` short-circuits on `vocabulary_id == "CPT4"` and so
    # returns False for a PCS stem whatever the data says.  The claim worth asserting is about
    # the DATA behind that short-circuit, and it can fail: nothing stops an editor putting a
    # four-character stem into CPT_ADD_ON.  Asserting disjointness means the vocabulary guard
    # restates the constants rather than being the only thing holding the claim up.
    _expect(not (CPT_ADD_ON & set(ALL_PCS_STEMS)),
            f"no ICD-10-PCS stem appears in the add-on set, it carries "
            f"{sorted(CPT_ADD_ON & set(ALL_PCS_STEMS))}")

    # -- (g) reconciliation against the plan's own assignment ---------------
    _expect(STEMS_LOCKED_NOT_ASSIGNED_BY_PLAN == frozenset({"0RG4", "0RB5", "00NT"}),
            f"the plan leaves exactly 0RG4, 0RB5 and 00NT unassigned, it left "
            f"{sorted(STEMS_LOCKED_NOT_ASSIGNED_BY_PLAN)}")
    _expect(STEMS_ASSIGNED_BY_PLAN_NOT_LOCKED == frozenset({"0RG9"}),
            f"the plan's range implies exactly one stem outside the locked set, it implied "
            f"{sorted(STEMS_ASSIGNED_BY_PLAN_NOT_LOCKED)}")
    for stem, planned in PLAN_REGION_ASSIGNMENT.items():
        if stem in PCS_REGION_PRIMARY:
            _expect(PCS_REGION_PRIMARY[stem] == planned,
                    f"{stem}: this module says {PCS_REGION_PRIMARY[stem]}, the plan says {planned}")

    # -- (h) the lookups refuse anything outside the locked set -------------
    _expect_raises(SpineConceptSetError, lambda: region_of("CPT4", "99999"),
                   "an unknown CPT-4 code has no region")
    _expect_raises(SpineConceptSetError, lambda: region_of("ICD10PCS", "0SG9000"),
                   "an excluded stem has no region")
    _expect_raises(SpineConceptSetError, lambda: procedure_class_of("ICD9Proc", "81.08"),
                   "a vocabulary outside the set has no class")

    # -- (i) every emitted SQL string is placeholder-only and house-clean ----
    for mirror in (False, True):
        for builder in ALL_SQL_BUILDERS:
            sql = builder(mirror_junctions=mirror)
            label = f"{builder.__name__}(mirror_junctions={mirror})"
            _expect("{CDR}" in sql, f"{label} carries the CDR placeholder")
            backticked = re.findall(r"`([^`]+)`", sql)
            _expect(backticked, f"{label} references at least one table")
            for name in backticked:
                _expect(name.startswith("{CDR}."),
                        f"{label} references {name!r}, which is not behind the placeholder")
            _expect(CDR_OF_RECORD not in sql, f"{label} does not hardcode the CDR name")
            _expect(not re.search(r"\bwb-[a-z0-9-]+\b", sql),
                    f"{label} does not hardcode a workbench project id")
            _expect("RAND(" not in sql.upper(), f"{label} uses no unseeded randomness")
            _expect("\u2014" not in sql, f"{label} contains no em-dash")  # U+2014, escaped so
            # this file itself contains no em-dash character anywhere

    # -- (j) the SQL and the python maps cannot drift -----------------------
    for mirror in (False, True):
        case_sql = _labelled_case_sql(
            REGIONS, lambda v, c: region_of(v, c, mirror_junctions=mirror), "region")
        for code in ALL_CPT:
            _expect(case_sql.count("'" + code + "'") == 1,
                    f"CPT-4 {code} appears exactly once in the region CASE")
        for stem in ALL_PCS_STEMS:
            _expect(case_sql.count("'" + stem + "'") == 1,
                    f"stem {stem} appears exactly once in the region CASE")

    # -- (k) the assertion helpers, on a synthetic frame --------------------
    # NOTE, and it is the reason `pipeline/tests/test_cs_spine.py` exists: this frame is built
    # from the same constants the helper checks against, so its 852 is true BY CONSTRUCTION and
    # the count assert here is satisfied tautologically.  What is exercised below is the
    # helper's ability to REFUSE, which is not tautological.  Only a caller running it on a
    # real CDR frame can detect drift between these constants and the CDR.
    frame = _synthetic_concept_frame()
    _expect_ok(lambda: assert_concept_frame(frame), "a synthetic 852-row frame validates")
    _expect_ok(lambda: assert_concept_frame(_synthetic_concept_frame(mirror_junctions=True),
                                            mirror_junctions=True),
               "a mirrored synthetic frame validates against the mirrored map")
    _expect_raises(SpineConceptSetError,
                   lambda: assert_concept_frame(_synthetic_concept_frame(mirror_junctions=True)),
                   "a mirrored frame does not validate against the primary map")
    _expect_raises(SpineConceptSetError, lambda: assert_concept_frame(frame[:-1]),
                   "a frame short of 852 rows is refused")
    _expect_raises(SpineConceptSetError, lambda: assert_concept_frame([]),
                   "an empty frame is refused")

    for mutation, why in (
        ({"region": None}, "a NULL region is refused"),
        ({"region": "sacral"}, "a region outside the closed vocabulary is refused"),
        ({"region": "lumbar"}, "a region that contradicts the locked map is refused"),
        ({"procedure_class": "decompression"}, "a class that contradicts the locked map is refused"),
        ({"is_add_on": True}, "an add-on flag that contradicts the locked map is refused"),
        ({"is_add_on": None}, "a NULL add-on flag is refused, not read as False"),
        ({"procedure_class": None}, "a NULL class is refused"),
    ):
        broken = [dict(r) for r in frame]
        broken[0].update(mutation)            # row 0 is CPT-4 22551: cervical, fusion, not add-on
        _expect_raises(SpineConceptSetError, lambda b=broken: assert_concept_frame(b), why)

    # row 0 is CPT-4 22551 (cervical) and row 1 is 22558 (lumbar); giving them one concept_id
    # makes a single concept carry two regions and two classes at once
    dupe = [dict(r) for r in frame]
    dupe[1]["concept_id"] = dupe[0]["concept_id"]
    _expect(len(dupe) == EXPECTED_CONCEPT_COUNT, "the duplicate frame is still 852 rows")
    _expect_raises(SpineConceptSetError, lambda: assert_concept_frame(dupe),
                   "one concept_id carrying two regions is refused")

    missing_column = [{k: v for k, v in r.items() if k != "region"} for r in frame]
    _expect_raises(SpineConceptSetError, lambda: assert_concept_frame(missing_column),
                   "a frame without a region column is refused")

    # A column missing from a LATE row, which is the case a row-0-only gate walked straight
    # past and then hit as a bare KeyError deep in the loop, invisible to a caller catching
    # SpineConceptSetError.
    late_gap = [dict(r) for r in frame]
    del late_gap[500]["region"]
    _expect_raises(SpineConceptSetError, lambda: assert_concept_frame(late_gap),
                   "a column missing from row 500 is refused as a concept-set error")

    # A CPT-4 code resolving to two concept_ids: the count still says 852 in every subtotal, so
    # only the dedicated check can name the cause.
    two_ids = [dict(r) for r in frame]
    two_ids.insert(1, dict(frame[0], concept_id=9_999_002))   # 22551 again, a second id
    del two_ids[-1]                                           # hold the frame at 852 rows
    caught = _expect_raises(SpineConceptSetError, lambda: assert_concept_frame(two_ids),
                            "a CPT-4 code resolving to two concept_ids is refused")
    _expect("more than one concept_id" in str(caught),
            f"and the message names the cause rather than the total, it said {str(caught)[:60]!r}")

    # -- (l) the SNOMED audit helper ---------------------------------------
    good_audit = [{"vocabulary_id": "CPT4", "procedure_class": "fusion", "region": "cervical",
                   "n_source": EXPECTED_CONCEPT_COUNT, "n_source_mapped": EXPECTED_CONCEPT_COUNT,
                   "n_standard": 400}]
    _expect_ok(lambda: assert_snomed_frame(good_audit), "a fully mapped audit frame validates")
    short_audit = [dict(good_audit[0], n_source_mapped=EXPECTED_CONCEPT_COUNT - 1)]
    _expect_raises(SpineConceptSetError, lambda: assert_snomed_frame(short_audit),
                   "an incomplete 'Maps to' mapping is refused")
    _expect_raises(SpineConceptSetError,
                   lambda: assert_snomed_frame([dict(good_audit[0], n_source=851,
                                                     n_source_mapped=851)]),
                   "an audit that does not cover 852 concepts is refused")
    _expect_raises(SpineConceptSetError,
                   lambda: assert_snomed_frame([dict(good_audit[0], n_source_mapped=900)]),
                   "more mapped concepts than source concepts is refused, not reported as a "
                   "shortfall")
    _expect_raises(SpineConceptSetError,
                   lambda: assert_snomed_frame([{k: v for k, v in good_audit[0].items()
                                                 if k != "n_source_mapped"}]),
                   "an audit frame missing a column is refused, not a bare KeyError")

    # -- (m) the registry ---------------------------------------------------
    registry = registry_rows()
    _expect(len(registry) == len(ALL_CPT) + len(ALL_PCS_STEMS),
            "the registry has one row per code or stem")
    _expect(sum(1 for r in registry if r["is_junction"]) == len(JUNCTION_STEMS),
            "the registry marks every junction stem")
    # The registry exists to make the junction tie-break readable without a re-run, so BOTH
    # assignments ship on every call and the flag cannot suppress either one.
    _expect(registry == registry_rows(mirror_junctions=True),
            "the registry is identical whichever way mirror_junctions is passed")
    _expect(all(tuple(r) == REGISTRY_COLUMNS for r in registry),
            "every registry row carries exactly the declared columns in order")
    junction_rows = [r for r in registry if r["is_junction"]]
    _expect(all(r["region_primary"] != r["region_mirrored"] for r in junction_rows),
            "every junction row shows two different regions, which is the tie-break itself")
    _expect(all(r["region_primary"] == r["region_mirrored"]
                for r in registry if not r["is_junction"]),
            "no non-junction row moves under the mirror")

    # -- (n) the locked maps are locked -------------------------------------
    def _try_to_mutate(mapping: Any) -> None:
        mapping["ZZZZ"] = "cervical"

    for name, locked_map in (("CPT_REGION", CPT_REGION),
                             ("PCS_REGION_PRIMARY", PCS_REGION_PRIMARY),
                             ("PCS_REGION_MIRRORED", PCS_REGION_MIRRORED),
                             ("PCS_REGION", PCS_REGION),
                             ("PLAN_REGION_ASSIGNMENT", PLAN_REGION_ASSIGNMENT)):
        _expect_raises(TypeError, lambda m=locked_map: _try_to_mutate(m),
                       f"{name} is read-only; a locked map a caller can mutate is not locked")
    _expect(dict(PCS_REGION) == dict(PCS_REGION_PRIMARY),
            "the PCS_REGION alias and the primary map agree, and neither can be moved")

    bar = "=" * 78
    print(bar)
    print("cs_spine.py SELF-TEST: PASS")
    print(bar)
    print(f"  assertions executed          : {_ASSERTIONS_EXECUTED}")
    print(f"  locked concept total         : {EXPECTED_CONCEPT_COUNT} "
          f"({EXPECTED_CPT_CONCEPTS} CPT-4 + {EXPECTED_PCS_FUSION_CONCEPTS} PCS fusion "
          f"+ {EXPECTED_PCS_DECOMPRESSION_CONCEPTS} PCS decompression)")
    print(f"  CPT-4                        : {len(CPT_FUSION)} fusion, "
          f"{len(CPT_DECOMPRESSION)} decompression, {len(CPT_ADD_ON)} of {len(ALL_CPT)} add-on "
          f"or instrumentation, {len(ALL_CPT) - len(CPT_ADD_ON)} able to define an operation")
    print(f"  ICD-10-PCS stems             : {len(PCS_FUSION_STEMS)} fusion, "
          f"{len(PCS_DECOMPRESSION_STEMS)} decompression, {len(ALL_PCS_STEMS)} total")
    counts = {r: sum(1 for s in ALL_PCS_STEMS if PCS_REGION_PRIMARY[s] == r) for r in REGIONS}
    print( "  region tags, primary map     : "
          + ", ".join(f"{k} {v}" for k, v in counts.items()))
    print(f"  junction tie-breaks          : cervicothoracic "
          f"{sorted(CERVICOTHORACIC_STEMS)} cervical, thoracolumbar "
          f"{sorted(THORACOLUMBAR_STEMS)} thoracic; mirror sends each to the caudal member")
    print(f"  region-free by design        : {sorted(LEVEL_AGNOSTIC_PCS_STEMS)} "
          f"(spinal meninges, no level in the code) plus every add-on code")
    print(f"  in the locked set, unassigned by the plan : "
          f"{sorted(STEMS_LOCKED_NOT_ASSIGNED_BY_PLAN)}")
    print(f"  assigned by the plan, not in the locked set : "
          f"{sorted(STEMS_ASSIGNED_BY_PLAN_NOT_LOCKED)}")
    print(f"  cervical decompression gap   : locked carries "
          f"{sorted(c for c in CPT_DECOMPRESSION if CPT_REGION[c] == 'cervical')}, "
          f"protocol also names {list(CERVICAL_DECOMPRESSION_CANDIDATE_CPT)} "
          f"(measured, not amended)")
    print(f"  cervical fusion gap          : locked carries "
          f"{sorted(c for c in CPT_FUSION if CPT_REGION[c] == 'cervical')}, "
          f"protocol also names {list(CERVICAL_FUSION_CANDIDATE_CPT)} "
          f"(measured, not amended)")
    print( "  wrong-arm risk               : 22554 absent and 63075 present, so a legacy-coded")
    print( "                                 ACDF books as cervical decompression today")
    print(f"  SQL builders checked         : "
          f"{', '.join(b.__name__ for b in ALL_SQL_BUILDERS)}")
    print( "  every emitted query          : carries {CDR}, no hardcoded project or dataset,")
    print( "                                 no unseeded randomness, no em-dash")
    print( "  cloud access required        : none")


if __name__ == "__main__":
    _run_self_test()
