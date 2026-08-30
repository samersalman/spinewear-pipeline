#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""01_probe.py -- the first thing that runs inside the perimeter, at the top of Phase 2.

WHERE THIS RUNS.  INSIDE the perimeter only, after `%run 00_config.ipynb`.  It answers, before
any engineering and for as close to nothing as the questions allow, the six things the locked
plan and the build say must not be assumed.  LOCALLY it does nothing useful: every probe needs the CDR.  The
pure logic (column picking, the partition verdict, the visit-id selection, the diagnosis text)
is importable and unit-testable with no cloud, and `python3 01_probe.py --self-test` exercises
exactly that.

WHAT 00_config.ipynb ALREADY DID, AND THIS MODULE DOES NOT REPEAT.  The startup notebook
resolves `GOOGLE_PROJECT`, `WORKSPACE_CDR`, `PREP_CDR` and `CDR_LOCATION`, creates
`{DERIVED}` in the CDR's location if absent, runs and drops a write probe, asserts statsmodels
0.14 or later, records `SOFTWARE_VERSIONS`, `R_KERNEL_VISIBLE` and `WB_RESOURCE_LIST_STATUS`,
and runs the `person` count smoke test.  All of that is imported here, never re-derived.  The
budget is spent on what is genuinely unknown.

THE SIX PROBES (plan Phase 2 item 1, plan section 2.1, CLAUDE.md stop conditions 1 and 2).
  1. Do the Fitbit tables exist in the Controlled Tier CDR at all, and what is their DDL.
     The protocol was written against the Registered Tier.  A sibling project's working Fitbit
     code queried the same CDR and returned real numbers, which is strong evidence and is not
     the same thing as a fact.  Free: INFORMATION_SCHEMA.
  2. The `heart_rate_summary` layout the whole cost design rests on: the exact per-zone minute
     column name, and whether the zones partition the day without double-counting a minute.
     Designed so that "the zones overlap" and "the participant did not wear the device all day"
     cannot be confused, because a naive summary of summed minutes makes them look identical.
  3. The locked 852-concept set against the real CDR.  `cs_spine.assert_concept_frame` has
     never been pointed at a real frame, so drift is presently undetectable.  This is its
     first production caller.
  4. The emergency department and inpatient `visit_concept_id` values, enumerated against the
     CDR's actual distribution rather than trusted.  The selection RULE is prespecified here;
     the distribution is evidence that the rule covers what the CDR holds, never the chooser.
  5. The environment facts a later session should not rediscover: the `wb resource list`
     output shape, and whether `wb resource resolve --name prep_C2025Q4R6` works.
  6. `visit_occurrence.visit_source_value`, which attrition rung 4's ONLY elective rescue and
     the elective-admission exclusion in `events` both key on.  The two failure directions are
     not symmetric: in `events` a flag that is never true excludes nothing, while in rung 4 a
     rescue that never fires excludes every episode with an emergency department encounter in
     the index window and leaves a count in the ladder that reads as a real exclusion.  It
     shares PROBE 4's visit cap rather than adding one.  (DAG-SCHEMA.md section 9 item 6.)

HOW IT BEHAVES.  Every query dry-runs first through `q_guarded`, under a cap sized to the
number this module actually expects, with a note.  Nothing participant-level is printed: every
count goes through `round20`, every printed frame goes through `print_violations` first, and
categorical breakdowns fold their suppressed members into one row the way `safe_counts` does.
Every failure prints a diagnosis saying what was checked, what came back, what it means and
what changes about the plan; none of them prints a traceback.  A check that cannot run reports
"not run" with a reason and is never silently skipped.

THE PROBE RESULT IS RETURNED, PRINTED, AND WRITTEN TO THE PATH THE CONTRACT NAMES.
`EXPORT-CONTRACT.md` section 1 names `v1/probe/probe_result.json` and tells the next session to
read it and to run the probe only when it is absent, so that path is `--write-json`'s DEFAULT
rather than an option: a probe run that wrote nothing made every later session pay to re-learn
facts that do not change between sessions against one CDR release.  `run_probe()` returns the
dict, `main()` prints it as one JSON block for the handoff in `SESSION-LOG.md` section 6 and
writes it, and any path inside a `results` tree is still refused, with the refusal naming the
legal path rather than only the illegal one.  The other file this module writes is
`results/ledgers-csv/ledger_concept_set_registry.csv`, which the contract names in section 5.6
and whose producer it names as `cs_spine.registry_rows()`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
from typing import Any, Callable, Mapping, NamedTuple, Sequence

import pandas as pd


# ======================================================================================
# (1) Locating this repo's own modules, whichever way this file was started.
# ======================================================================================
# Same shape as the locate helper in 00_config.ipynb, and for the same reason: the kernel's
# cwd on a Workbench VM is wherever the human last cd'd to, and importing a DIFFERENT
# disclosure.py than the one this repo ships is how two suppression floors end up in one
# manuscript.  The identity of what actually got imported is checked against the config
# namespace below rather than assumed.


def _repo_paths() -> list[pathlib.Path]:
    """Directories that might hold `disclosure.py`, `cs_spine.py` and `00_config.ipynb`."""
    candidates: list[pathlib.Path] = []
    try:
        candidates.append(pathlib.Path(__file__).resolve().parent)
    except NameError:                      # exec'd without a __file__, for example by %run -i
        pass
    cwd = pathlib.Path.cwd().resolve()
    candidates += [cwd, *cwd.parents]
    out: list[pathlib.Path] = []
    for directory in candidates:
        for cand in (directory, directory / "pipeline"):
            if cand.is_dir() and cand not in out:
                out.append(cand)
    return out


def _find_export_contract() -> pathlib.Path | None:
    """`EXPORT-CONTRACT.md`, if this checkout carries it. READ only, and only by the self-test.

    It exists so `REGISTRY_LEDGER_DESCRIPTION` can be pinned against the contract's own bytes
    rather than against a second transcription of them, which is the thing that drifted.
    """
    for directory in _repo_paths():
        for candidate in (directory / "prespecification" / "EXPORT-CONTRACT.md",
                          directory.parent / "prespecification" / "EXPORT-CONTRACT.md"):
            if candidate.is_file():
                return candidate
    return None


def _add_pipeline_to_path() -> pathlib.Path | None:
    """Put the directory holding `disclosure.py` on sys.path and return it."""
    for directory in _repo_paths():
        if (directory / "disclosure.py").is_file() and (directory / "cs_spine.py").is_file():
            if str(directory) not in sys.path:
                sys.path.insert(0, str(directory))
            return directory
    return None


_PIPELINE_DIR = _add_pipeline_to_path()

try:
    import cs_spine
    import disclosure
except ModuleNotFoundError as _exc:        # pragma: no cover - only fires on a broken checkout
    raise ModuleNotFoundError(
        "01_probe.py could not import disclosure.py and cs_spine.py, which live beside it in "
        "pipeline/. Nothing here may run without them: disclosure.py owns every printed count "
        "and cs_spine.py owns the locked concept set. Run this file from the repo, not from a "
        f"copy. ({_exc})"
    ) from None

# Two predicates, two questions, and the difference is the whole reason this import lists both.
# `disclosable(n)` is the FLOOR: asked of a TRUE count, before `round20`, it decides whether the
# category may be shown at all. `is_legal_disclosed_count(cell)` is the GATE: asked of a cell
# that has ALREADY been through `round20`, it decides whether the rendered value is one this
# project is allowed to write down. They disagree on the numeral 20 and that disagreement is
# correct: `round20` maps a true 21 through 29 to 20, so 20 is an illegal true count and a legal
# rendered one. Asking the floor question of a rendered cell refuses every correctly rounded
# frame; asking the gate question of a raw count lets a true 20 through. Neither is a substitute
# for the other, so both are imported and each is used in exactly one place.
from disclosure import (SUPPRESSED, DisclosureError, disclosable,  # noqa: E402
                        is_legal_disclosed_count, is_suppressed, n_pct,
                        round20, safe_show, suppress_frame)


__all__ = [
    "ProbeStopCondition",
    "ProbeVerdict",
    "STATUS_PASS",
    "STATUS_FAIL",
    "STATUS_INCONCLUSIVE",
    "STATUS_NOT_RUN",
    "MINUTES_PER_DAY",
    "VALID_WEAR_MINUTES",
    "CEILING_BAND_FLOOR",
    "FITBIT_TABLE_PATTERNS",
    "FITBIT_TABLES_REQUIRED",
    "FITBIT_TABLES_EXPECTED",
    "HR_ZONE_MINUTE_COLUMN",
    "ED_VISIT_CONCEPT_IDS",
    "INPATIENT_VISIT_CONCEPT_IDS",
    "ACUTE_CARE_VISIT_CONCEPT_IDS",
    "ELECTIVE_SOURCE_VALUE_PATTERN",
    "VISIT_SOURCE_VALUE_COLUMN",
    "REGISTRY_SPECIFICATION_COLUMNS",
    "REGISTRY_LEDGER_DESCRIPTION",
    "PROBE_RESULT_RELATIVE_PATH",
    "VISIT_CANDIDATE_NAME_PATTERNS",
    "FITBIT_SCHEMA_MAX_GB",
    "ZONE_PARTITION_MAX_GB",
    "CONCEPT_RESOLUTION_MAX_GB",
    "SNOMED_CROSSCHECK_MAX_GB",
    "VISIT_DISTRIBUTION_MAX_GB",
    "fitbit_tables_sql",
    "table_row_counts_sql",
    "columns_sql",
    "zone_partition_sql",
    "visit_concept_distribution_sql",
    "visit_source_value_sql",
    "all_sql_for_audit",
    "pick_zone_columns",
    "zone_partition_verdict",
    "classify_visit_concepts",
    "visit_concept_verdict",
    "classify_visit_source_values",
    "visit_source_value_verdict",
    "matches_elective_pattern",
    "registry_frame",
    "fold_suppressed",
    "print_violations",
    "diagnosis_text",
    "resolve_config",
    "run_probe",
    "main",
]


# ======================================================================================
# (2) Verdicts and the diagnosis format.
# ======================================================================================
# Every check in this module returns one of these instead of raising, so a single run reports
# EVERY problem rather than the first one.  That is the same argument `export_violations` makes
# in disclosure.py: a caller fixing findings one traceback at a time makes one round trip
# through the perimeter, at VM cost and human attention, per finding.  The run still HALTS at
# the end, in `run_probe(halt=True)`; it just halts having said everything it knows.

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_INCONCLUSIVE = "inconclusive"
STATUS_NOT_RUN = "not run"

_HALTING_STATUSES = (STATUS_FAIL, STATUS_INCONCLUSIVE, STATUS_NOT_RUN)


class ProbeStopCondition(RuntimeError):
    """A probe found something that changes the plan. It is never worked around.

    Its own class so a caller can branch on it, and so the notebook traceback carries a name
    that says what happened rather than `RuntimeError`.
    """


class ProbeVerdict(NamedTuple):
    """One check's answer, carrying the four sentences a diagnosis has to say.

    `checked`, `came_back`, `means` and `changes` follow the house style 00_config.ipynb set at
    its write probe: what was checked, what came back, what it means, and what changes about
    the plan. `came_back` is written from ALREADY-ROUNDED numbers; the raw ones decide the
    status and never reach a string.
    """

    key: str
    status: str
    headline: str
    checked: str
    came_back: str
    means: str
    changes: str

    @property
    def halts(self) -> bool:
        return self.status in _HALTING_STATUSES


def diagnosis_text(verdict: ProbeVerdict) -> str:
    """Render a verdict as the printed diagnosis block. No traceback, ever."""
    rule = "-" * 86
    label = {STATUS_PASS: "OK", STATUS_FAIL: "HALTED", STATUS_INCONCLUSIVE: "INCONCLUSIVE",
             STATUS_NOT_RUN: "NOT RUN"}[verdict.status]
    lines = [rule, f"{verdict.key} {label}: {verdict.headline}", rule,
             f"  checked   : {verdict.checked}",
             f"  came back : {verdict.came_back}",
             f"  means     : {verdict.means}",
             f"  changes   : {verdict.changes}", rule]
    return "\n".join(lines)


# ======================================================================================
# (3) Constants. Every threshold this module compares against is a name here.
# ======================================================================================

# The wear arithmetic. 1,440 is the number of minutes in a day and is the ceiling a partition
# of the day cannot exceed; 600 is the plan's primary valid-wear rule (section 2.1); 1,380 is
# 23 hours, the band a full-wear day lands in under a partition scheme. None of these is the
# disclosure floor, which is never written as a literal anywhere in this file: `disclosable`,
# `round20` and `is_suppressed` are the only things that know it.
MINUTES_PER_DAY: int = 1440
VALID_WEAR_MINUTES: int = 600
CEILING_BAND_FLOOR: int = 1380

# INFORMATION_SCHEMA is matched on these, lowercased, so a table named `fitbit_activity_summary`
# and one named `activity_summary` are both found. Kept wide on purpose: the point of the probe
# is to see what is there, not to confirm a guess.
FITBIT_TABLE_PATTERNS: tuple[str, ...] = ("%activity%", "%step%", "%fitbit%", "%heart_rate%",
                                          "%sleep%", "%device%")

# What the locked plan actually needs. `activity_summary` carries the daily step total that is
# S_id; `heart_rate_summary` carries the per-zone minutes that are the valid-wear rule. Absence
# of either ends the project in this tier, which is why it is a stop condition and not a note.
FITBIT_TABLES_REQUIRED: tuple[str, ...] = ("activity_summary", "heart_rate_summary")

# Wanted but not fatal. `heart_rate_minute_level` matters only for the plan's own prespecified
# contingency, the seeded 200-person-day audit of section 2.1; the rest are context.
FITBIT_TABLES_EXPECTED: tuple[str, ...] = ("activity_summary", "heart_rate_summary",
                                           "heart_rate_minute_level", "steps_intraday",
                                           "sleep_daily_summary", "sleep_level")

# ---- The per-zone minute column: ONE name, exported, so three files stop spelling it three
# ---- ways ---------------------------------------------------------------------------------
# The documented All of Us name, the first rung of the `minute` rule chain below, and the value
# `build_all.sql` takes as `hr_minute_column`. It is exported so `02_pregate.py` and the DAG
# import it rather than retyping it: the three files once held `minute_in_zone`, `minute_in_zone`
# and `min_in_zone`, and the odd one out was the spelling interpolated into a query that
# EXECUTES under an 18 GiB cap while the two files that agreed never ran. A column-name mismatch
# discovered there costs a Workbench session.
#
# It is a FIRST GUESS and not an assumption. `pick_zone_columns` resolves the name this CDR
# actually ships, and a run that resolves something else passes THAT name to the build. The
# constant is what the chain tries first and what a caller with no probe result in hand should
# quote; `result["heart rate summary"]["resolved"]["minute"]` is what a caller with one should.
HR_ZONE_MINUTE_COLUMN: str = "minute_in_zone"

# ---- The visit concept selection, PRESPECIFIED, before the distribution is seen -----------
# CLAUDE.md rule 3: code never chooses after seeing a number. So the rule is fixed here and the
# probe measures whether the CDR's actual distribution is covered by it. These are the OMOP
# standard Visit domain concepts. 262 is deliberately in BOTH sets: it is an emergency
# department presentation that became an admission, and plan section 4.1 collapses exactly that
# pair to one event.
ED_VISIT_CONCEPT_IDS: tuple[int, ...] = (9203, 262)
INPATIENT_VISIT_CONCEPT_IDS: tuple[int, ...] = (9201, 262)

# A concept whose NAME says emergency or inpatient but which is not in the sets above is a
# CANDIDATE: the probe reports it so the human can decide, and the cohort build does not use it
# unless the plan is amended. Whole-word-ish patterns rather than substrings, so "nonemergency"
# does not match.
VISIT_CANDIDATE_NAME_PATTERNS: tuple[str, ...] = (
    r"emergency", r"\bed\b", r"inpatient", r"hospital admission", r"admitted",
    r"observation room", r"acute care", r"intensive care",
)

# The union of the two sets, which is the population PROBE 6 measures the elective proxy over,
# because both consumers of that proxy read exactly these encounters. 262 collapses, so the
# union is three ids and not four.
ACUTE_CARE_VISIT_CONCEPT_IDS: tuple[int, ...] = tuple(
    sorted(set(ED_VISIT_CONCEPT_IDS) | set(INPATIENT_VISIT_CONCEPT_IDS)))

# ---- The elective-encounter proxy, quoted from the build rather than written again --------
# `build_all.sql` keys attrition rung 4's ONLY elective rescue and the elective-admission
# exclusion in `events` on this one regular expression over `visit_occurrence.visit_source_value`.
# It is a constant here so PROBE 6 measures the proxy that ships rather than one like it: a
# probe testing a pattern the build does not use answers a question nobody asked.
ELECTIVE_SOURCE_VALUE_PATTERN: str = r"elect|sched"

# The column both consumers read. Named once, checked against INFORMATION_SCHEMA before the
# priced query runs, and never interpolated from anywhere else.
VISIT_SOURCE_VALUE_COLUMN: str = "visit_source_value"

# The manifest description of the concept-set registry ledger, quoted verbatim from
# EXPORT-CONTRACT.md section 8.3. It says CODE OR STEM, not "concept", for the reason the file
# exists: `registry_rows()` yields 51 rows, one per locked code or stem, while the concept set
# RESOLVES to 852 concepts, and `n_rows = 51` is written into MANIFEST.csv beside this sentence.
# "One row per concept" beside a row count of 51 is the 852 claim, printed on the one file whose
# whole point is that the two numbers are different. The self-test pins it against the
# contract's own text so it cannot drift back.
REGISTRY_LEDGER_DESCRIPTION: str = (
    "One row per code or stem in the locked spine concept set with its region and add-on tags")

# Where the probe result goes when nobody names a path. EXPORT-CONTRACT.md section 1 now NAMES
# this artefact and tells the next session to read it and to run the probe only when it is
# absent, so writing it is the default rather than an option: a probe run that wrote nothing
# made every later session pay to re-learn facts that do not change between sessions against one
# CDR release. It is deliberately OUTSIDE `v1/results/`, which the contract declares
# exhaustively, and it is resolved off the repo root exactly the way `--results-dir` is.
PROBE_RESULT_RELATIVE_PATH: str = "probe/probe_result.json"

# ---- Byte caps. Every one is the number this module EXPECTS, with the arithmetic. ---------
# `q_guarded` uses max_gb as both the refusal threshold and `maximum_bytes_billed`, so a cap
# set from a real expectation makes a surprise fail rather than bill. "GB" here is GiB, as in
# 00_config.ipynb.

# INFORMATION_SCHEMA and __TABLES__ are metadata: BigQuery answers them without scanning, and
# the dry run prices them at zero. The cap is not a budget, it is a tripwire that says the
# query is not the metadata query this module thinks it is.
FITBIT_SCHEMA_MAX_GB: float = 1.0

# heart_rate_summary at roughly 4 rows per person-day: order 30 million rows in the Controlled
# Tier, times four columns at about 37 bytes a row, is about 1.2 GB. Capped at eight, which is
# generous headroom on a larger Fitbit cohort and still about five cents.
ZONE_PARTITION_MAX_GB: float = 8.0

# `concept` scanned on four columns, `concept_name` being the wide one: order 1 to 2 GB.
CONCEPT_RESOLUTION_MAX_GB: float = 4.0

# The same `concept` scan plus `concept_relationship` on three columns, order 50 million rows
# at about 36 bytes: about 2 GB more.
SNOMED_CROSSCHECK_MAX_GB: float = 8.0

# `visit_occurrence` on `visit_concept_id` and `person_id`, order 250 million rows at 16 bytes,
# is about 4 GB, plus the `concept` scan for the names.
VISIT_DISTRIBUTION_MAX_GB: float = 10.0


# ======================================================================================
# (4) SQL builders. Text only. `{CDR}` is the only placeholder any of them uses.
# ======================================================================================
# Every builder returns a plain (non-f) string with the braces intact, because `_fill` in
# 00_config.ipynb cannot see a placeholder an f-string already consumed. No RAND(), no
# hardcoded project or dataset, and the identifiers that DO reach SQL as literals (a table or
# column name that came back from INFORMATION_SCHEMA a moment ago) are validated first.

_SAFE_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}")


def _check_identifier(name: Any, what: str) -> str:
    """Refuse anything that is not a bare SQL identifier before it reaches a query string.

    These names come from INFORMATION_SCHEMA rather than from a human, so this is not the
    usual injection story. It is still the only place in this module where a runtime string is
    concatenated into SQL, and an unquoted name arriving with a backtick or a semicolon in it
    would be a query nobody wrote.
    """
    text = str(name)
    if not _SAFE_IDENTIFIER.fullmatch(text):
        raise ProbeStopCondition(
            f"{what} came back as a name that is not a bare SQL identifier, so no query was "
            f"built from it. Read the INFORMATION_SCHEMA output by eye before going further."
        )
    return text


def _like_clause(column: str, patterns: Sequence[str]) -> str:
    """`LOWER(col) LIKE '%a%' OR LOWER(col) LIKE '%b%'`, with the patterns as written."""
    column = _check_identifier(column, "the column named in a LIKE clause")
    joined = "\n     OR ".join(f"LOWER({column}) LIKE '{p}'" for p in patterns)
    return joined


def fitbit_tables_sql() -> str:
    """Fitbit-like table names and their DDL. Free: INFORMATION_SCHEMA is metadata.

    The DDL is what makes partitioning and clustering come along for nothing, which is what
    lets `build_all.sql` prune a date-partitioned Fitbit table instead of scanning it.
    """
    return (
        "SELECT table_name, table_type, ddl\n"
        "FROM `{CDR}`.INFORMATION_SCHEMA.TABLES\n"
        "WHERE " + _like_clause("table_name", FITBIT_TABLE_PATTERNS) + "\n"
        "ORDER BY table_name\n"
    )


def table_row_counts_sql() -> str:
    """Row counts and stored bytes from the dataset's own free metadata table.

    `__TABLES__` is the one place BigQuery hands over a row count without scanning anything.
    It is a legacy metatable and a CDR release could stop exposing it, so the caller treats a
    failure here as missing information rather than as a stop condition.
    """
    return (
        "SELECT table_id AS table_name, row_count, size_bytes\n"
        "FROM `{CDR}.__TABLES__`\n"
        "WHERE " + _like_clause("table_id", FITBIT_TABLE_PATTERNS) + "\n"
        "ORDER BY table_id\n"
    )


def columns_sql(table_name: str) -> str:
    """Column names, types and nullability for one table. Free."""
    table = _check_identifier(table_name, "the table whose columns were asked for")
    return (
        "SELECT column_name, data_type, is_nullable, ordinal_position\n"
        "FROM `{CDR}`.INFORMATION_SCHEMA.COLUMNS\n"
        f"WHERE table_name = '{table}'\n"
        "ORDER BY ordinal_position\n"
    )


def zone_partition_sql(*, table_name: str, person_column: str, date_column: str,
                       zone_column: str, minute_column: str) -> str:
    """The zone-partition check: one scan, three blocks of answers, no person-day printed.

    Everything this returns is a COUNT OF PERSON-DAYS or a count of rows, never a person-day's
    own summed minutes. That matters: a MAX of the summed total is one participant's own value
    on one date, and the question can be answered without it.

    The discriminating band is `summed minutes above 1440`. Non-wear can only push a person-day
    total DOWN, so a total above the number of minutes in a day is impossible under a partition
    and is the signature of zones that overlap. A second, different failure is a REPEATED zone
    label on a person-day, which double-counts by duplication rather than by definition, and is
    counted separately because the two have different fixes.

    Both blocks read the same CTE. BigQuery bills the columns referenced once per query, not
    once per reference, so the zone vocabulary is free once the per-day rollup is being paid
    for.
    """
    table = _check_identifier(table_name, "the heart rate summary table")
    person = _check_identifier(person_column, "the person column")
    day = _check_identifier(date_column, "the date column")
    zone = _check_identifier(zone_column, "the zone column")
    minute = _check_identifier(minute_column, "the per-zone minute column")
    ceiling = MINUTES_PER_DAY
    return (
        "WITH src AS (\n"
        f"  SELECT {person} AS person, {day} AS day, CAST({zone} AS STRING) AS zone,\n"
        f"         {minute} AS minutes\n"
        "  FROM `{CDR}." + table + "`\n"
        "),\n"
        "per_day AS (\n"
        "  SELECT person, day,\n"
        "         SUM(minutes) AS total_minutes,\n"
        "         COUNT(*) AS n_rows,\n"
        "         COUNT(DISTINCT zone) AS n_zones,\n"
        "         COUNTIF(minutes IS NULL) AS n_null_minutes\n"
        "  FROM src\n"
        "  GROUP BY person, day\n"
        ")\n"
        "SELECT 'wear band' AS block, 'person days, all' AS label, COUNT(*) AS n FROM per_day\n"
        "UNION ALL SELECT 'wear band', 'persons contributing', COUNT(DISTINCT person) FROM per_day\n"
        f"UNION ALL SELECT 'wear band', 'summed minutes below {VALID_WEAR_MINUTES}',"
        f" COUNTIF(total_minutes < {VALID_WEAR_MINUTES}) FROM per_day\n"
        f"UNION ALL SELECT 'wear band', 'summed minutes {VALID_WEAR_MINUTES} to {ceiling}',"
        f" COUNTIF(total_minutes >= {VALID_WEAR_MINUTES} AND total_minutes <= {ceiling})"
        " FROM per_day\n"
        f"UNION ALL SELECT 'wear band', 'summed minutes above {ceiling}',"
        f" COUNTIF(total_minutes > {ceiling}) FROM per_day\n"
        f"UNION ALL SELECT 'wear band', 'summed minutes {CEILING_BAND_FLOOR} to {ceiling}',"
        f" COUNTIF(total_minutes >= {CEILING_BAND_FLOOR} AND total_minutes <= {ceiling})"
        " FROM per_day\n"
        "UNION ALL SELECT 'wear band', 'person days with a repeated zone label',"
        " COUNTIF(n_rows > n_zones) FROM per_day\n"
        "UNION ALL SELECT 'wear band', 'person days with a null zone minute cell',"
        " COUNTIF(n_null_minutes > 0) FROM per_day\n"
        "UNION ALL SELECT 'wear band', 'person days with no summed total',"
        " COUNTIF(total_minutes IS NULL) FROM per_day\n"
        "UNION ALL SELECT 'zone label', zone, COUNT(*) FROM src GROUP BY zone\n"
        "ORDER BY block, label\n"
    )


def visit_concept_distribution_sql() -> str:
    """Every `visit_concept_id` present in the CDR, with its name and its two counts.

    Person counts as well as visit counts, because the disclosure floor is about people and
    because "which ids does the cohort build use" is a question about participants. Both are
    rounded before anything is printed.
    """
    return (
        "WITH d AS (\n"
        "  SELECT visit_concept_id,\n"
        "         COUNT(*) AS n_visits,\n"
        "         COUNT(DISTINCT person_id) AS n_persons\n"
        "  FROM `{CDR}.visit_occurrence`\n"
        "  GROUP BY visit_concept_id\n"
        ")\n"
        "SELECT d.visit_concept_id, c.concept_name, c.vocabulary_id, c.concept_code,\n"
        "       d.n_visits, d.n_persons\n"
        "FROM d\n"
        "LEFT JOIN `{CDR}.concept` c ON c.concept_id = d.visit_concept_id\n"
        "ORDER BY d.n_persons DESC, d.visit_concept_id\n"
    )


# The four labels the verdict reads out of the query's own output. Named once so the SQL, the
# classifier and the verdict cannot drift apart by a comma.
SOURCE_VALUE_TOTAL = "visits, all"
SOURCE_VALUE_NULLS = "visits with a null source value"
SOURCE_VALUE_EMPTIES = "visits with an empty source value"
SOURCE_VALUE_DISTINCT = "distinct source values"
SOURCE_VALUE_MATCHED = "visits matching the elective pattern"
SOURCE_VALUE_DISTINCT_MATCHED = "distinct source values matching the elective pattern"


def visit_source_value_sql() -> str:
    """`visit_occurrence.visit_source_value`: is it populated, and does the build's proxy match.

    ONE grouped scan of TWO columns of `visit_occurrence`, `visit_concept_id` and
    `visit_source_value`. BigQuery bills a referenced column once per query rather than once per
    reference, so the restricted block below shares the scan with the unrestricted one and the
    second set of answers is free.

    WHY THIS IS A PROBE AT ALL. `build_all.sql` keys attrition rung 4's only elective rescue and
    the elective-admission exclusion in `events` on one regular expression over this one column,
    and `visit_detail` is deliberately not consulted because its population is itself unverified.
    The two failure directions are not symmetric and only one of them is silent. In `events`, an
    always-false flag excludes nothing, which is the safe direction. In rung 4, an always-false
    `rescue_elective_coded` means the rescue NEVER FIRES, so every episode with an emergency
    department encounter in the index window is excluded with no trace in the ladder, and the
    count reads as a real exclusion rather than as a column nobody populated.

    THREE BLOCKS COME BACK. `coverage` is over every visit in the CDR and answers whether the
    column is populated at all. `acute care coverage` is the same arithmetic restricted to the
    prespecified emergency and inpatient concept ids, which is the population both consumers
    actually read, and it carries the one number that decides the verdict: how many of those
    visits the build's own expression matches. `source value` is the distribution of distinct
    values over those ids, one row per value, folded by the caller before anything is printed.

    Counts here are VISITS and not persons, which is what keeps this to two columns and inside
    the visit cap. That is weaker than a person count in one direction and the caller says so
    where it matters: `fold_suppressed` on a visit count can keep a label whose person count is
    below the floor. The values themselves are the CDR's own visit-type coding rather than a
    participant attribute, and the fold is applied anyway.
    """
    pattern = ELECTIVE_SOURCE_VALUE_PATTERN
    if "'" in pattern or "\\" in pattern:
        raise ProbeStopCondition(
            f"the elective source-value pattern {pattern!r} carries a quote or a backslash and "
            f"would not survive interpolation into SQL intact. Every identifier and literal "
            f"this module puts into a query is checked first; this one is checked here.")
    column = _check_identifier(VISIT_SOURCE_VALUE_COLUMN, "the visit source value column")
    ids = ", ".join(str(int(i)) for i in ACUTE_CARE_VISIT_CONCEPT_IDS)
    return (
        "WITH v AS (\n"
        "  SELECT visit_concept_id AS concept_id,\n"
        f"         CAST({column} AS STRING) AS source_value\n"
        "  FROM `{CDR}.visit_occurrence`\n"
        "),\n"
        "acute AS (\n"
        "  SELECT source_value,\n"
        f"         REGEXP_CONTAINS(LOWER(IFNULL(source_value, '')), r'{pattern}') AS matched\n"
        "  FROM v\n"
        f"  WHERE concept_id IN ({ids})\n"
        ")\n"
        f"SELECT 'coverage' AS block, '{SOURCE_VALUE_TOTAL}' AS label, COUNT(*) AS n FROM v\n"
        f"UNION ALL SELECT 'coverage', '{SOURCE_VALUE_NULLS}',"
        " COUNTIF(source_value IS NULL) FROM v\n"
        f"UNION ALL SELECT 'coverage', '{SOURCE_VALUE_EMPTIES}',"
        " COUNTIF(source_value = '') FROM v\n"
        f"UNION ALL SELECT 'coverage', '{SOURCE_VALUE_DISTINCT}',"
        " COUNT(DISTINCT source_value) FROM v\n"
        f"UNION ALL SELECT 'acute care coverage', '{SOURCE_VALUE_TOTAL}', COUNT(*) FROM acute\n"
        f"UNION ALL SELECT 'acute care coverage', '{SOURCE_VALUE_NULLS}',"
        " COUNTIF(source_value IS NULL) FROM acute\n"
        f"UNION ALL SELECT 'acute care coverage', '{SOURCE_VALUE_EMPTIES}',"
        " COUNTIF(source_value = '') FROM acute\n"
        f"UNION ALL SELECT 'acute care coverage', '{SOURCE_VALUE_DISTINCT}',"
        " COUNT(DISTINCT source_value) FROM acute\n"
        f"UNION ALL SELECT 'acute care coverage', '{SOURCE_VALUE_MATCHED}',"
        " COUNTIF(matched) FROM acute\n"
        f"UNION ALL SELECT 'acute care coverage', '{SOURCE_VALUE_DISTINCT_MATCHED}',"
        " COUNT(DISTINCT IF(matched, source_value, NULL)) FROM acute\n"
        "UNION ALL SELECT 'source value', IFNULL(source_value, '(null)'), COUNT(*)"
        " FROM acute GROUP BY source_value\n"
        "ORDER BY block, label\n"
    )


def all_sql_for_audit() -> dict[str, str]:
    """Every SQL string this module can emit, for the placeholder and hygiene self-test.

    A builder absent from here is a builder the audit does not cover, so this is the list the
    self-test walks rather than a hand-written one beside it.
    """
    return {
        "fitbit tables": fitbit_tables_sql(),
        "table row counts": table_row_counts_sql(),
        "columns": columns_sql("heart_rate_summary"),
        "zone partition": zone_partition_sql(
            table_name="heart_rate_summary", person_column="person_id", date_column="date",
            zone_column="zone_name", minute_column=HR_ZONE_MINUTE_COLUMN),
        "visit concept distribution": visit_concept_distribution_sql(),
        "visit source value": visit_source_value_sql(),
        "concept resolution": cs_spine.concept_resolution_sql(),
        "snomed crosscheck": cs_spine.snomed_crosscheck_sql(),
    }


# ======================================================================================
# (5) Pure logic. No cloud, no printing, fully self-testable.
# ======================================================================================

# Ordered rules, most specific first. The first rule that matches any column decides the role:
# exactly one match takes it, more than one is an ambiguity that stops rather than guesses.
# The canonical All of Us layout is the first rule of each role, so the common case takes the
# exact-name path and never reaches a heuristic.
_ROLE_RULES: dict[str, tuple[tuple[str, Callable[[str, str], bool]], ...]] = {
    "person": (
        ("the exact name person id", lambda name, kind: name == "person_id"),
        ("a name containing person", lambda name, kind: "person" in name),
    ),
    "date": (
        ("the exact name date", lambda name, kind: name == "date"),
        ("a DATE-typed column named like a date",
         lambda name, kind: kind.startswith("DATE") and "date" in name),
        ("any DATE-typed column", lambda name, kind: kind.startswith("DATE")),
    ),
    "zone": (
        ("the exact name zone name", lambda name, kind: name == "zone_name"),
        ("a name containing zone but not minute",
         lambda name, kind: "zone" in name and "minute" not in name),
    ),
    # Rung 3 is the abbreviated spelling, and it is here because the chain could not reach it:
    # rungs 2 and 4 both require the substring "minute", and `min_in_zone` contains neither
    # "minute" nor a numeric-name cue, so a CDR shipping that spelling failed the layout probe,
    # `probe ok` came back false, the pre-gate refused, and Phase 2 ended on a column name. It
    # sits AFTER the exact-name rung and after the "minute and zone" rung, so an exact match
    # always wins and the pair (`minutes_in_zone`, `active_minutes_in_zone`) is still resolved
    # as the ambiguity it is rather than being disambiguated by a narrower rung underneath it.
    "minute": (
        ("the exact name minute in zone", lambda name, kind: name == HR_ZONE_MINUTE_COLUMN),
        ("a name containing both minute and zone",
         lambda name, kind: "minute" in name and "zone" in name),
        ("a name beginning with min and containing zone",
         lambda name, kind: name.startswith("min") and "zone" in name),
        ("a numeric column whose name contains minute",
         lambda name, kind: "minute" in name and kind.split("(")[0] in
         ("INT64", "INTEGER", "NUMERIC", "BIGNUMERIC", "FLOAT64", "FLOAT")),
    ),
}


def pick_zone_columns(columns: Sequence[Mapping[str, Any]]) -> tuple[dict[str, str],
                                                                    ProbeVerdict]:
    """Name the four columns the wear rule needs, from what INFORMATION_SCHEMA actually says.

    Returns (mapping, verdict). The mapping is empty when the verdict does not pass, so a
    caller cannot accidentally build a query from a half-resolved layout.

    `columns` is whatever `columns_sql()` returned, as a sequence of mappings carrying
    `column_name` and `data_type`.
    """
    if not columns:
        return {}, ProbeVerdict(
            key="PROBE 2a", status=STATUS_NOT_RUN,
            headline="the heart rate summary column list came back empty",
            checked="INFORMATION_SCHEMA.COLUMNS for the heart rate summary table",
            came_back="no rows, so the table is invisible to this account or does not exist",
            means="the exact per-zone minute column name cannot be resolved, and plan section "
                  "2.1 says it is a runtime probe rather than an assumption",
            changes="nothing below may run against a guessed column name. Resolve visibility "
                    "of the Fitbit tables first, which is PROBE 1",
        )

    known = [(str(row.get("column_name", "")).strip().lower(),
              str(row.get("data_type", "")).strip().upper()) for row in columns]
    resolved: dict[str, str] = {}
    problems: list[str] = []
    for role, rules in _ROLE_RULES.items():
        for description, rule in rules:
            hits = [name for name, kind in known if name and rule(name, kind)]
            if not hits:
                continue
            if len(hits) > 1:
                problems.append(
                    f"the {role} column is ambiguous: {description} matched {sorted(hits)}")
            else:
                resolved[role] = hits[0]
            break
        else:
            problems.append(f"no column matched any rule for the {role} column")

    if problems:
        return {}, ProbeVerdict(
            key="PROBE 2a", status=STATUS_FAIL,
            headline="the heart rate summary layout is not the one the plan is written against",
            checked="the column list of the heart rate summary table, against an ordered set "
                    "of naming rules for the person, date, zone and per-zone minute columns",
            came_back="; ".join(problems)
                      + f". The columns present are {sorted(name for name, _ in known)}",
            means="the wear rule cannot be built. Plan section 2.1 names the exact zone column "
                  "as a runtime probe precisely so this is found here and not in Phase 3",
            changes="read the column list by eye, then either extend the rules in this module "
                    "to the layout this CDR actually ships or amend plan section 2.1. Do not "
                    "hardcode a column name into the build without doing one of the two",
        )

    return resolved, ProbeVerdict(
        key="PROBE 2a", status=STATUS_PASS,
        headline="the heart rate summary layout resolved",
        checked="the column list of the heart rate summary table",
        came_back=f"person {resolved['person']}, date {resolved['date']}, "
                  f"zone {resolved['zone']}, per-zone minutes {resolved['minute']}",
        means="the wear rule of plan section 2.1 can be built from the summary table rather "
              "than from the minute-level table",
        changes="nothing. The probe result feeds the query, as the plan says it should",
    )


def _band(bands: Mapping[str, int], label: str) -> int | None:
    """One band's raw count, or None when the query did not return it."""
    value = bands.get(label)
    return None if value is None else int(value)


def zone_partition_verdict(bands: Mapping[str, int]) -> ProbeVerdict:
    """Decide whether the zones partition the day, from the raw band counts.

    RAW counts decide; the sentences are written from `round20` output, so no unrounded count
    reaches a printed string. That split is deliberate and is the pattern every probe here
    follows: decide on raw, print rounded.

    The four outcomes and why they are four rather than two:

      overlap        `summed minutes above 1440` is non-zero. A day holds 1,440 minutes. Not
                     wearing the device can only take minutes AWAY from a person-day total, so
                     no amount of non-wear can produce a total above the ceiling and a total
                     above the ceiling can only be a minute counted twice.
      repeated rows  a person-day carries the same zone label more than once. That double
                     counts by duplication rather than by overlapping definitions, and the fix
                     is a de-duplication in the build rather than a change of wear rule, so it
                     is reported as its own failure.
      partition      nothing above the ceiling AND person-days piled up in the top band. The
                     second half is what rules out a NESTED scheme: under nesting a full-wear
                     day would land at roughly twice the ceiling, so full-wear days sitting
                     just below the ceiling are evidence the zones tile the day exactly once.
      inconclusive   nothing above the ceiling and NOTHING in the top band either. This is the
                     case a naive summary gets wrong. A cohort that never wears the device a
                     full day and a nesting scheme under which nobody exceeds half a day look
                     identical in the mean, the median and the maximum, and neither one can be
                     ruled out from summed minutes alone.
    """
    ceiling = MINUTES_PER_DAY
    total = _band(bands, "person days, all")
    above = _band(bands, f"summed minutes above {ceiling}")
    at_ceiling = _band(bands, f"summed minutes {CEILING_BAND_FLOOR} to {ceiling}")
    repeated = _band(bands, "person days with a repeated zone label")
    nulls = _band(bands, "person days with a null zone minute cell")
    valid = _band(bands, f"summed minutes {VALID_WEAR_MINUTES} to {ceiling}")

    missing = [name for name, value in
               (("person days, all", total), (f"summed minutes above {ceiling}", above),
                (f"summed minutes {CEILING_BAND_FLOOR} to {ceiling}", at_ceiling),
                ("person days with a repeated zone label", repeated))
               if value is None]
    if missing:
        return ProbeVerdict(
            key="PROBE 2b", status=STATUS_NOT_RUN,
            headline="the zone-partition query did not return the bands this check needs",
            checked="the band counts returned by the zone-partition query",
            came_back=f"bands absent from the result: {missing}",
            means="the query that ran is not the query this check is written against, so no "
                  "conclusion drawn from it would be safe",
            changes="nothing may assume the summary table gives the wear figure until this "
                    "runs. Fix the query, then re-run the probe",
        )

    if total == 0:
        return ProbeVerdict(
            key="PROBE 2b", status=STATUS_NOT_RUN,
            headline="the heart rate summary table holds no person-days",
            checked="a rollup of summed per-zone minutes over every person-day in the table",
            came_back="zero person-days",
            means="the table exists but is empty for this account, so the wear rule has no "
                  "input and the cost design that rests on it cannot be tested",
            changes="the whole valid-wear-day definition is unbuildable. Treat this exactly "
                    "like the Fitbit tables being absent and bring it to the human",
        )

    shown_total = round20(total)
    if repeated:
        return ProbeVerdict(
            key="PROBE 2b", status=STATUS_FAIL,
            headline="a person-day carries the same zone label more than once",
            checked=f"per person-day, the row count against the count of DISTINCT zone labels, "
                    f"over {shown_total} person-days",
            came_back=f"{round20(repeated)} person-days carry a repeated zone label",
            means="summing the per-zone minute column double counts those days by duplication. "
                  "This is NOT the overlapping-zone failure and it has a different fix: the "
                  "rows are duplicates, not a different definition of a zone",
            changes="the wear query cannot be a bare SUM. Either de-duplicate on person, date "
                    "and zone in the build and re-run this probe, or fall back to wear "
                    "definition S2 of plan section 2.1. Log the choice as an amendment",
        )

    if above:
        return ProbeVerdict(
            key="PROBE 2b", status=STATUS_FAIL,
            headline="summed zone minutes exceed the number of minutes in a day",
            checked=f"the count of person-days whose summed per-zone minutes exceed {ceiling}, "
                    f"over {shown_total} person-days. Non-wear can only reduce a total, so a "
                    f"total above the ceiling can only be a minute counted twice",
            came_back=f"{round20(above)} person-days above {ceiling} summed minutes",
            means="the zones do not partition the day. This is the exact condition plan "
                  "section 2.1 names in its prespecified contingency, and it is not a "
                  "wear-adherence artefact",
            changes="the primary wear definition falls back to sensitivity definition S2, at "
                    "least 10 hours of heart-rate wear and at least 100 steps. Report the "
                    "substitution in the Methods and log it as an amendment. It does NOT fall "
                    "back to minute-level counting for the whole cohort, which is about 300 "
                    "times the bytes and is not in the budget",
        )

    null_note = ("" if not nulls else
                 f" {round20(nulls)} person-days carry a null zone minute cell, which SUM "
                 f"silently skips.")
    if at_ceiling:
        valid_share = "" if valid is None else (
            f" Person-days meeting the plan's {VALID_WEAR_MINUTES}-minute rule: "
            f"{n_pct(valid, total)}.")
        return ProbeVerdict(
            key="PROBE 2b", status=STATUS_PASS,
            headline="the zones partition the day",
            checked=f"the count of person-days above {ceiling} summed minutes, and the count "
                    f"in the top band of {CEILING_BAND_FLOOR} to {ceiling}, over {shown_total} "
                    f"person-days",
            came_back=f"nothing above {ceiling}, and {round20(at_ceiling)} person-days in the "
                      f"top band.{valid_share}{null_note}",
            means="summed per-zone minutes are a wear-minute count and not a double count. A "
                  "nested scheme would have put full-wear days at about twice the ceiling, and "
                  "there are none",
            changes="nothing. The primary wear definition of plan section 2.1 stands, and the "
                    "summary table gives the wear figure at about one three-hundredth of the "
                    "bytes of the minute-level table",
        )

    return ProbeVerdict(
        key="PROBE 2b", status=STATUS_INCONCLUSIVE,
        headline="no person-day reaches the top band, so overlap cannot be ruled out",
        checked=f"the count of person-days above {ceiling} summed minutes, and the count in "
                f"the top band of {CEILING_BAND_FLOOR} to {ceiling}, over {shown_total} "
                f"person-days",
        came_back=f"nothing above {ceiling}, and nothing in the top band either.{null_note}",
        means="this is the case a naive summary reads as success. A cohort that never wears "
              "the device a full day and a nested scheme under which nobody exceeds half a day "
              "produce the same summed distribution, and summed minutes alone cannot tell them "
              "apart",
        changes="run the second half of the plan section 2.1 contingency, the seeded "
                "200-person-day audit against the minute-level table, before the primary wear "
                "definition is trusted. If that audit is not run, the primary definition falls "
                "back to S2 by the same prespecified rule",
    )


def _matches_any(text: str, patterns: Sequence[str]) -> bool:
    lowered = str(text).lower()
    return any(re.search(pattern, lowered) for pattern in patterns)


def classify_visit_concepts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Check the PRESPECIFIED emergency and inpatient id sets against what the CDR holds.

    The rule is fixed in the constants above, before any distribution exists, because
    CLAUDE.md rule 3 forbids choosing after seeing a number. What this measures is whether the
    rule COVERS the CDR: which prespecified ids are actually present, and which ids the CDR
    holds that look like emergency or inpatient encounters by name and are not in the rule.

    Returns raw counts. The caller rounds everything before it prints.
    """
    present: dict[int, dict[str, Any]] = {}
    for row in rows:
        raw_id = row.get("visit_concept_id")
        if raw_id is None or (isinstance(raw_id, float) and pd.isna(raw_id)):
            continue
        present[int(raw_id)] = {
            "concept_name": "" if row.get("concept_name") is None else str(row["concept_name"]),
            "n_visits": int(row.get("n_visits") or 0),
            "n_persons": int(row.get("n_persons") or 0),
        }

    def _block(ids: Sequence[int]) -> list[dict[str, Any]]:
        return [{"visit_concept_id": i,
                 "present": i in present,
                 "concept_name": present.get(i, {}).get("concept_name", ""),
                 "n_visits": present.get(i, {}).get("n_visits", 0),
                 "n_persons": present.get(i, {}).get("n_persons", 0)} for i in ids]

    prespecified = set(ED_VISIT_CONCEPT_IDS) | set(INPATIENT_VISIT_CONCEPT_IDS)
    candidates = [
        {"visit_concept_id": i,
         "concept_name": meta["concept_name"],
         "n_visits": meta["n_visits"],
         "n_persons": meta["n_persons"]}
        for i, meta in sorted(present.items(), key=lambda kv: -kv[1]["n_persons"])
        if i not in prespecified and _matches_any(meta["concept_name"],
                                                  VISIT_CANDIDATE_NAME_PATTERNS)
    ]
    return {
        "emergency": _block(ED_VISIT_CONCEPT_IDS),
        "inpatient": _block(INPATIENT_VISIT_CONCEPT_IDS),
        "candidates not used": candidates,
        "n distinct ids in the CDR": len(present),
        "absent prespecified ids": sorted(i for i in prespecified if i not in present),
    }


def visit_concept_verdict(classification: Mapping[str, Any]) -> ProbeVerdict:
    """Turn the classification into a verdict, with the reason the chosen ids are the chosen ids."""
    absent = list(classification.get("absent prespecified ids") or [])
    candidates = list(classification.get("candidates not used") or [])
    ed_ids = ", ".join(str(i) for i in ED_VISIT_CONCEPT_IDS)
    ip_ids = ", ".join(str(i) for i in INPATIENT_VISIT_CONCEPT_IDS)
    why = (f"The cohort build uses {ed_ids} for an emergency department encounter and {ip_ids} "
           f"for an inpatient admission. 262 is in both because it is an emergency presentation "
           f"that became an admission, which plan section 4.1 collapses to one event.")

    if absent:
        return ProbeVerdict(
            key="PROBE 4", status=STATUS_FAIL,
            headline="a prespecified visit concept id does not occur in this CDR at all",
            checked="every prespecified emergency and inpatient visit concept id against the "
                    "CDR's actual distribution of visit concept ids",
            came_back=f"absent from the distribution: {absent}. The CDR holds "
                      f"{classification.get('n distinct ids in the CDR')} distinct ids",
            means="the outcome definition of plan section 4.1 names an encounter type this CDR "
                  "does not record, so the acute-care count would be silently short",
            changes=f"{why} An absent id has to be resolved with the human before the cohort is "
                    f"built: either the CDR uses a different vocabulary for that encounter type, "
                    f"in which case plan section 4.1 is amended, or the encounter type genuinely "
                    f"does not occur, in which case the gate arithmetic changes",
        )

    if candidates:
        listed = ", ".join(f"{c['visit_concept_id']} ({c['concept_name']})" for c in candidates)
        return ProbeVerdict(
            key="PROBE 4", status=STATUS_INCONCLUSIVE,
            headline="the CDR holds visit concepts that read as acute care and are not in the "
                     "prespecified sets",
            checked="every visit concept id in the CDR's distribution, against the prespecified "
                    "emergency and inpatient sets and against a name pattern for acute care",
            came_back=f"not used by the prespecified rule: {listed}",
            means="the prespecified rule may under-count acute-care encounters in this CDR. It "
                  "is reported rather than silently widened, because widening it after seeing "
                  "the distribution is exactly what CLAUDE.md rule 3 forbids",
            changes=f"{why} Bring the candidate list to the human at the Phase 2 hard stop. "
                    f"Adding an id is an amendment to plan section 4.1, logged and dated, not "
                    f"an edit to this module",
        )

    return ProbeVerdict(
        key="PROBE 4", status=STATUS_PASS,
        headline="the prespecified visit concept ids are present and nothing else reads as "
                 "acute care",
        checked="every visit concept id in the CDR's distribution, against the prespecified "
                "emergency and inpatient sets and against a name pattern for acute care",
        came_back=f"all prespecified ids present; no unused id in the distribution carries an "
                  f"acute-care name. The CDR holds "
                  f"{classification.get('n distinct ids in the CDR')} distinct ids",
        means="the outcome definition of plan section 4.1 is enumerated rather than assumed, "
              "which is CLAUDE.md stop condition 1",
        changes=f"nothing. {why}",
    )


def matches_elective_pattern(value: Any) -> bool:
    """The build's own elective proxy, evaluated in Python on one source value.

    Same expression, same lowercasing, same treatment of a null as an empty string, so a value
    this returns True for is a value `build_all.sql` rescues and no other.
    """
    text = "" if value is None else str(value)
    return bool(re.search(ELECTIVE_SOURCE_VALUE_PATTERN, text.lower()))


def classify_visit_source_values(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Split `visit_source_value_sql()`'s three blocks apart. Raw counts; the caller rounds.

    The distribution is sorted by descending visit count and then by value, so the folded frame
    the caller prints puts what the CDR actually uses at the top rather than in alphabetical
    order, and the `(null)` bucket lands with the rest instead of being special-cased.
    """
    coverage: dict[str, int] = {}
    acute: dict[str, int] = {}
    values: list[dict[str, Any]] = []
    for row in rows:
        block = str(row.get("block", "")).strip()
        label = "" if row.get("label") is None else str(row.get("label"))
        raw = row.get("n")
        count = 0 if raw is None or (isinstance(raw, float) and pd.isna(raw)) else int(raw)
        if block == "coverage":
            coverage[label] = count
        elif block == "acute care coverage":
            acute[label] = count
        elif block == "source value":
            values.append({"source value": label, "visits": count,
                           "matches the elective pattern":
                               "yes" if matches_elective_pattern(label) else "no"})
    values.sort(key=lambda r: (-int(r["visits"]), str(r["source value"])))
    return {"coverage": coverage, "acute care coverage": acute, "source values": values,
            "pattern": ELECTIVE_SOURCE_VALUE_PATTERN,
            "concept ids": list(ACUTE_CARE_VISIT_CONCEPT_IDS)}


def visit_source_value_verdict(classification: Mapping[str, Any]) -> ProbeVerdict:
    """Decide whether attrition rung 4's only rescue can fire in this CDR.

    THE FAIL CONDITION IS ZERO MATCHES, and it is the whole reason this probe exists. A rescue
    that matches nothing does not degrade gracefully: rung 4 then excludes every episode with an
    emergency department encounter in the index window, the ladder shows a plausible-looking
    `n_dropped`, and nothing anywhere says the exclusion was decided by an unpopulated column.
    The sibling consumer in `events` fails the other way and is safe, so the asymmetry is stated
    in the diagnosis rather than left for a reader to work out.

    Counts in the sentences are rounded; the raw ones decide, and the disclosure floor is the
    only threshold this function compares a count against. A match count at or below the floor
    is INCONCLUSIVE rather than a pass: the rescue does fire, and how often cannot be said out
    loud, so it cannot be told apart from a stray free-text value that happens to contain the
    word "scheduled".
    """
    acute = dict(classification.get("acute care coverage") or {})
    coverage = dict(classification.get("coverage") or {})
    pattern = classification.get("pattern", ELECTIVE_SOURCE_VALUE_PATTERN)
    ids = list(classification.get("concept ids") or ACUTE_CARE_VISIT_CONCEPT_IDS)
    checked = (f"{VISIT_SOURCE_VALUE_COLUMN} on every visit carrying one of the prespecified "
               f"emergency or inpatient concept ids {ids}, against the regular expression "
               f"{pattern!r} that build_all.sql itself writes")
    why = ("Attrition rung 4's elective rescue is the ONLY route by which an episode with an "
           "emergency department encounter in the index window survives the ladder, and the "
           "elective-admission exclusion in `events` keys on the same match. The two directions "
           "are not symmetric and only one is silent: in `events` a flag that is never true "
           "excludes nothing, which is the safe direction, while in rung 4 a rescue that never "
           "fires excludes every one of those episodes and the ladder reports a count that "
           "reads as a real exclusion.")

    absent = [label for label in (SOURCE_VALUE_TOTAL, SOURCE_VALUE_MATCHED)
              if label not in acute]
    if absent:
        return ProbeVerdict(
            key="PROBE 6", status=STATUS_NOT_RUN,
            headline="the source-value coverage query did not return the bands the verdict reads",
            checked=checked,
            came_back=f"absent from the result: {absent}. Present: {sorted(acute)}",
            means="whether rung 4's rescue can fire in this CDR is still unknown, and "
                  "DAG-SCHEMA.md section 9 item 6 names it as a runtime probe rather than an "
                  "assumption",
            changes="re-run the probe. Nothing may be built on a rescue whose input was never "
                    "measured")

    total = int(acute[SOURCE_VALUE_TOTAL])
    matched = int(acute[SOURCE_VALUE_MATCHED])
    unpopulated = int(acute.get(SOURCE_VALUE_NULLS, 0)) + int(acute.get(SOURCE_VALUE_EMPTIES, 0))
    distinct = acute.get(SOURCE_VALUE_DISTINCT)
    distinct_all = coverage.get(SOURCE_VALUE_DISTINCT)
    # A distinct-value COUNT is the cardinality of the CDR's visit-type coding, not a count of
    # participants or of their records, so it is reported as metadata the way PROBE 4 reports
    # the number of distinct visit concept ids. Every count of VISITS below goes through n_pct.
    coding = (f"the column holds {distinct} distinct value(s) over those ids and "
              f"{distinct_all} across all visits")

    if total <= 0:
        return ProbeVerdict(
            key="PROBE 6", status=STATUS_NOT_RUN,
            headline="this CDR records no visit at all under the prespecified acute-care ids",
            checked=checked,
            came_back=f"{n_pct(total, total)} visits carry one of {ids}",
            means="there is no population to measure the elective proxy over. That is PROBE 4's "
                  "finding rather than this one's, and the two are the same finding",
            changes="see PROBE 4. Resolve the visit concept ids first; this probe has nothing "
                    "to measure until it has visits")

    if matched <= 0:
        return ProbeVerdict(
            key="PROBE 6", status=STATUS_FAIL,
            headline="the elective pattern matches no visit in this CDR, so attrition rung 4's "
                     "only rescue can never fire",
            checked=checked,
            came_back=f"{n_pct(matched, total)} of the acute-care visits match. "
                      f"{n_pct(unpopulated, total)} carry a null or empty source value, and "
                      f"{coding}",
            means=why,
            changes="rung 4 may not be built on this proxy in this CDR. Either name the column "
                    "that does carry elective wording and amend DAG-SCHEMA.md section 9 item 6 "
                    "and the ladder to it, or amend the plan so rung 4 excludes with no rescue "
                    "and SAYS so in the Methods. Both are plan changes, logged and dated, and "
                    "neither is an edit to this module. What may not happen is the rescue "
                    "shipping as written: an exclusion nobody can see is the failure this probe "
                    "exists to catch")

    if not disclosable(matched):
        return ProbeVerdict(
            key="PROBE 6", status=STATUS_INCONCLUSIVE,
            headline="the elective pattern matches too few visits to disclose, so whether the "
                     "rescue really fires cannot be told from a stray free-text value",
            checked=checked,
            came_back=f"the matching visits are below the disclosure floor and are suppressed. "
                      f"{n_pct(unpopulated, total)} of {n_pct(total, total)} acute-care visits "
                      f"carry a null or empty source value, and {coding}",
            means=f"the rescue fires, and on so few visits that it cannot be distinguished from "
                  f"coincidence. {why}",
            changes="bring the distribution above to the human at the Phase 2 hard stop and "
                    "decide there whether rung 4 keeps the rescue. Do not widen the pattern "
                    "after seeing this distribution: that is what CLAUDE.md rule 3 forbids")

    return ProbeVerdict(
        key="PROBE 6", status=STATUS_PASS,
        headline="the elective pattern matches real visits, so attrition rung 4's rescue has "
                 "something to read",
        checked=checked,
        came_back=f"{n_pct(matched, total)} of the acute-care visits match. "
                  f"{n_pct(unpopulated, total)} carry a null or empty source value, and "
                  f"{coding}",
        means="rung 4's elective rescue and the elective-admission exclusion in `events` are "
              "both keyed on a column this CDR populates, so an episode excluded at rung 4 was "
              "excluded by evidence rather than by an absent column",
        changes="nothing. The rescue stays a PROXY and the Methods say so; what this retires is "
                "the silent-over-exclusion failure of DAG-SCHEMA.md section 9 item 6, not the "
                "proxy's own imprecision")


def fold_suppressed(frame: pd.DataFrame, *, count_col: str,
                    label_cols: Sequence[str]) -> pd.DataFrame:
    """Keep the disclosable rows and fold every other row into one sentinel-labelled row.

    The same semantics as `disclosure.safe_counts`, applied to a frame rather than a Series:
    a category whose count fails the floor loses its LABEL as well as its count, because a
    rare label is data. A rare visit concept name printed beside a suppressed count would
    disclose that the category exists and how few rows it has, which is the whole thing the
    floor protects.

    Input counts are RAW. Output counts are rounded or the sentinel.
    """
    if frame.empty:
        return frame.copy()
    raw = pd.to_numeric(frame[count_col], errors="coerce")
    keep = raw.map(lambda v: bool(disclosable(v)) if pd.notna(v) else False)
    kept = suppress_frame(frame.loc[keep].copy(), [count_col])
    if bool((~keep).any()):
        folded = {column: SUPPRESSED for column in frame.columns}
        for column in label_cols:
            folded[column] = SUPPRESSED
        folded[count_col] = SUPPRESSED
        kept = pd.concat([kept, pd.DataFrame([folded])], ignore_index=True)
    return kept.reset_index(drop=True)


def print_violations(frame: pd.DataFrame, *, count_cols: Sequence[str] = (),
                     metadata_cols: Sequence[str] = ()) -> list[str]:
    """Every reason this aggregate frame may not be PRINTED inside the perimeter.

    Not `export_violations`, deliberately, and the reason is worth writing down because it is
    a real limit of that function rather than a preference. `export_violations` refuses any
    column that is near-unique on a frame of more than twenty rows. A probe frame keyed by a
    public vocabulary id is near-unique BY CONSTRUCTION: a registry of codes has one row per
    code, and a visit-concept distribution has one row per concept id. So does its rounded
    count column, whose values are mostly distinct. Running the export gate over these frames
    refuses every one of them, and a gate that always refuses is a gate nobody runs.

    What this checks instead, and it is the part that carries the disclosure risk:

      1. EVERY column is declared, as a count column or as a metadata column. An undeclared
         column is a violation. This is the strong check: nothing is printed by omission.
      2. A column may not be declared as both.
      3. Every cell of a count column is a LEGAL DISCLOSED COUNT or the suppression sentinel,
         so the frame must already have been through `round20` or `fold_suppressed`. The
         predicate is `is_legal_disclosed_count`, not `disclosable`, and the difference
         matters here rather than being a nicety: this gate is handed a RENDERED cell, and a
         rendered 20 is what `round20` returns for every true count from 21 to 29. Asking
         `disclosable` of it refused exactly the frames this module rounds correctly, while
         letting nothing extra through, because the floor question belongs on the true count
         and is asked there, by `fold_suppressed` and by `suppress_frame`.
      4. No column holds dates. Controlled Tier dates are unshifted, so a date is a direct
         identifier of the person in the row.
      5. No header and no string cell carries a banned dash character.

    Neither the floor nor the rounding base is re-implemented here: `is_legal_disclosed_count`
    and `is_suppressed` are the only things in this function that know either number, and no
    numeral for either appears in this module.
    """
    if not isinstance(frame, pd.DataFrame):
        return [f"print target is a {type(frame).__name__}, not a DataFrame"]

    violations: list[str] = []
    counts = list(count_cols)
    metadata = list(metadata_cols)

    both = sorted(set(counts) & set(metadata))
    if both:
        violations.append(f"column(s) declared as both count and metadata: {both}")

    declared = set(counts) | set(metadata)
    undeclared = [c for c in frame.columns if c not in declared]
    if undeclared:
        violations.append(
            f"column(s) not declared before printing: {undeclared}. Declare every column as a "
            f"count or as metadata; a column printed by omission is a column nobody checked")
    absent = [c for c in declared if c not in frame.columns]
    if absent:
        violations.append(f"declared column(s) not in the frame: {sorted(absent)}")

    for col in counts:
        if col not in frame.columns:
            continue
        numeric = pd.to_numeric(frame[col], errors="coerce")
        bad = 0
        for value, number in zip(frame[col], numeric):
            if is_suppressed(value):
                continue
            # The cell in hand has already been rendered, so the question is whether it is a
            # legal value to write down, not whether some true count cleared the floor.
            if pd.isna(number) or not is_legal_disclosed_count(number):
                bad += 1
        if bad:
            # Names the column and the NUMBER of offending cells, never a cell value: this
            # message is printed to a notebook, which is the surface the policy protects. The
            # rounding base is named in words for the same reason.
            violations.append(
                f"count column {col!r} holds {bad} cell(s) that are not legal disclosed "
                f"counts; a legal disclosed count is a true zero, the suppression sentinel, or "
                f"a positive whole multiple of the rounding base. Put the frame through "
                f"round20 or fold_suppressed before printing it")

    for position, col in enumerate(frame.columns):
        series = frame.iloc[:, position]
        if pd.api.types.is_datetime64_any_dtype(series) or isinstance(series.dtype,
                                                                     pd.PeriodDtype):
            violations.append(f"column {col!r} is a date, and Controlled Tier dates are unshifted")
            continue
        if series.dtype == object and any(
                isinstance(v, (dt.date, dt.datetime)) for v in series.dropna()):
            violations.append(f"column {col!r} is a date, and Controlled Tier dates are unshifted")
        if any(ch in str(col) for ch in disclosure.BANNED_CHARACTERS):
            violations.append(
                f"column header at position {position} carries a banned dash character")
        offenders = sum(1 for v in series if isinstance(v, str)
                        and any(ch in v for ch in disclosure.BANNED_CHARACTERS))
        if offenders:
            violations.append(
                f"column {col!r} holds {offenders} string cell(s) carrying a banned dash character")

    return violations


# The one column of the concept-set registry that is declared a SPECIFICATION column, and the
# whole declaration: `code` holds CPT-4 codes and ICD-10-PCS stems drawn from a published
# vocabulary. A registry of codes has one row per code, so this column is 100% distinct by
# construction and trips the near-unique class on any frame wider than the floor's worth of
# rows. That class is right in general and wrong here: it exists to catch a quasi-identifier
# derived from participants, and a list of procedure codes is derived from a public vocabulary
# and identifies nobody. The exemption lifts the near-unique and identifier-like classes for
# this column only. Every other class still applies to it, and every class still applies to the
# other seven columns, which is why this is a tuple of one name rather than a flag on the file:
# an exemption nobody can point at a column is an exemption nobody can audit.
REGISTRY_SPECIFICATION_COLUMNS: tuple[str, ...] = ("code",)


def registry_frame() -> pd.DataFrame:
    """`cs_spine.registry_rows()` rendered as the ledger EXPORT-CONTRACT.md section 5.6 fixes.

    Eight columns in `cs_spine.REGISTRY_COLUMNS` order, every cell a display string, booleans
    written `true` and `false`, rows sorted by the contract's `sort_keys` of `vocabulary_id`
    then `code`. It carries no counts and therefore never suppresses: it is a list of the codes
    in the locked set, which is a property of the specification and not of any participant.

    Note for whoever writes 07_export.py: this frame has ONE ROW PER LOCKED CODE OR STEM, which
    is 30 CPT-4 codes plus 21 ICD-10-PCS stems. The contract's own manifest example gives 852
    rows for this file, which is the count of resolved CONCEPTS and cannot come out of
    `registry_rows()`, whose eight columns hold no `concept_id`. One of the two has to move.
    """
    rows = []
    for row in cs_spine.registry_rows():
        rendered = {}
        for column in cs_spine.REGISTRY_COLUMNS:
            value = row[column]
            rendered[column] = ("true" if value else "false") if isinstance(value, bool) \
                else str(value)
        rows.append(rendered)
    frame = pd.DataFrame(rows, columns=list(cs_spine.REGISTRY_COLUMNS))
    return frame.sort_values(["vocabulary_id", "code"], kind="mergesort").reset_index(drop=True)


# ======================================================================================
# (6) Getting the 00_config.ipynb namespace, however this file was started.
# ======================================================================================
# Three ways in, tried in order, because the three are genuinely different situations and a
# module that only supports one of them fails in the other two with an unhelpful NameError:
#
#   `%run -i 01_probe.py` after `%run 00_config.ipynb`   -> the names are in OUR globals
#   `import` or `%run 01_probe.py` from a notebook cell  -> the names are in __main__
#   `python3 01_probe.py` in the VM terminal             -> nothing is bound; bootstrap
#
# The bootstrap executes 00_config.ipynb's code cells in this process. It is a full startup:
# four `wb` calls, the dataset metadata read, the write probe and the person count. That is
# announced before it happens rather than done quietly, because it costs about fifteen seconds
# and three guarded queries.

_REQUIRED_CONFIG_NAMES: tuple[str, ...] = (
    "q_guarded", "dry_run_gb", "round20", "disclosable", "is_suppressed", "suppress_frame",
    "safe_show", "safe_counts", "safe_export", "n_pct", "SUPPRESSED",
    "GOOGLE_PROJECT", "WORKSPACE_CDR", "PREP_CDR", "DERIVED", "CDR_LOCATION",
    "SOFTWARE_VERSIONS", "R_KERNEL_VISIBLE", "PERSON_N_ROUNDED", "WRITE_PROBE_RESULT",
    "WB_RESOURCE_LIST_STATUS", "UnresolvedPlaceholder", "QueryCapExceeded",
    "session_cost_report",
)

# Present in a healthy config and used when they are there. `_run_wb` is underscore-private in
# the notebook and its own docstring says 01_probe.py is the caller it exists for: it returns a
# REASON so the `wb` failure modes can be told apart, which an empty list cannot do.
_OPTIONAL_CONFIG_NAMES: tuple[str, ...] = ("_run_wb", "wb_resolve")


def _find_config_notebook() -> pathlib.Path | None:
    for directory in _repo_paths():
        candidate = directory / "00_config.ipynb"
        if candidate.is_file():
            return candidate
    return None


def _bootstrap_config(notebook: pathlib.Path) -> dict[str, Any]:
    """Execute 00_config.ipynb's code cells in this process and return the namespace.

    What `%run` does, done by hand, because a terminal `python3 01_probe.py` has no IPython to
    do it. The cells are plain Python with no line magics, so `exec` is faithful rather than an
    approximation; a magic appearing in a later edit would raise a SyntaxError here, loudly,
    which is the right failure.
    """
    print(f"bootstrapping the configuration from {notebook}")
    print("this is a full 00_config.ipynb startup: the `wb` resolves, the dataset metadata "
          "call, the write probe and the person count. About fifteen seconds and three guarded "
          "queries, all of them free.")
    document = json.loads(notebook.read_text(encoding="utf-8"))
    namespace: dict[str, Any] = {"__name__": "spinewear_config", "__file__": str(notebook)}
    for index, cell in enumerate(document.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if not source.strip():
            continue
        try:
            exec(compile(source, f"{notebook.name}:cell{index}", "exec"), namespace)  # noqa: S102
        except Exception as exc:
            # The notebook's own stop conditions are already good diagnoses: an unresolved
            # GOOGLE_PROJECT, an unattached data collection, a location mismatch, a refused
            # write probe. They are re-raised as a ProbeStopCondition so this module's caller
            # prints ONE diagnosis rather than a traceback through an exec frame, which names
            # this file and tells the reader nothing about what actually failed.
            raise ProbeStopCondition(
                f"00_config.ipynb stopped in code cell {index} and no probe ran. It says:\n"
                f"{exc}\n"
                f"Nothing here may run without a configured session. Fix the configuration in "
                f"a Workbench VM, or start this module from a kernel where "
                f"`%run 00_config.ipynb` has already succeeded. ({type(exc).__name__})"
            ) from None
    return namespace


def resolve_config(namespace: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the names 00_config.ipynb defines, from wherever they already are.

    Raises ProbeStopCondition with a diagnosis, never a NameError, because a NameError on
    `q_guarded` two hundred lines into a probe is the least informative way this can fail.
    """
    searched: list[Mapping[str, Any]] = []
    if namespace is not None:
        searched.append(namespace)
    else:
        searched.append(globals())
        try:
            import __main__
            searched.append(vars(__main__))
        except Exception:                      # pragma: no cover - __main__ always imports
            pass

    for candidate in searched:
        if all(name in candidate for name in _REQUIRED_CONFIG_NAMES):
            resolved = {name: candidate[name] for name in _REQUIRED_CONFIG_NAMES}
            for name in _OPTIONAL_CONFIG_NAMES:
                if name in candidate:
                    resolved[name] = candidate[name]
            _assert_one_disclosure_module(resolved)
            return resolved

    if namespace is not None:
        missing = sorted(n for n in _REQUIRED_CONFIG_NAMES if n not in namespace)
        raise ProbeStopCondition(
            f"the namespace handed to run_probe() is missing {missing}. It has to be the "
            f"namespace `%run 00_config.ipynb` produced; a partial one would let some probes "
            f"run and silently skip others.")

    notebook = _find_config_notebook()
    if notebook is None:
        raise ProbeStopCondition(
            "00_config.ipynb was not found beside this file or anywhere above the working "
            "directory, and none of the names it defines is bound in this session. Nothing "
            "here may run without it: it owns the CDR resolve, the byte cap and the only "
            "query path. Run this from the repo, after `%run 00_config.ipynb`.")
    namespace = _bootstrap_config(notebook)
    missing = sorted(n for n in _REQUIRED_CONFIG_NAMES if n not in namespace)
    if missing:
        raise ProbeStopCondition(
            f"00_config.ipynb ran but did not define {missing}. The notebook and this module "
            f"have come apart. Do not paper over it by defining the names here: the whole "
            f"point of importing them is that there is one definition of each.")
    resolved = {name: namespace[name] for name in _REQUIRED_CONFIG_NAMES}
    for name in _OPTIONAL_CONFIG_NAMES:
        if name in namespace:
            resolved[name] = namespace[name]
    _assert_one_disclosure_module(resolved)
    return resolved


def _assert_one_disclosure_module(config: Mapping[str, Any]) -> None:
    """Refuse to run if the session holds two copies of the suppression rule.

    The notebook makes the same check on import. This makes it again on the OBJECTS, because
    the notebook's check compares file paths at import time and this compares the functions
    actually bound now: a later cell that rebound `round20` to something else would pass the
    first check and fail this one.
    """
    for name, ours in (("round20", round20), ("disclosable", disclosable),
                       ("is_suppressed", is_suppressed)):
        theirs = config.get(name)
        if theirs is not ours:
            raise ProbeStopCondition(
                f"the session's {name} is not the one this module imported from "
                f"{getattr(disclosure, '__file__', 'disclosure')}. Two copies of the "
                f"suppression rule in one session means two floors in one manuscript. Restart "
                f"the kernel and run 00_config.ipynb before anything else imports disclosure.")


# ======================================================================================
# (7) Running one query, with every failure mode told apart rather than collapsed.
# ======================================================================================


class _QueryOutcome(NamedTuple):
    frame: pd.DataFrame | None
    failure: str          # empty on success
    kind: str             # "", "placeholder", "cap", "permission", "other", "priced"


def _run_query(config: Mapping[str, Any], sql: str, *, max_gb: float, note: str,
               price_only: bool = False) -> _QueryOutcome:
    """Dry run, print the estimate, then execute under the cap. Never raises for the caller.

    The failure KINDS are kept apart for the same reason 00_config.ipynb keeps its four write
    probe diagnoses apart: an unresolved placeholder, a cost-cap refusal and a permissions
    error look identical in a traceback and have nothing to do with each other, and offering
    the wrong one of the three costs a session.
    """
    unresolved = config["UnresolvedPlaceholder"]
    over_cap = config["QueryCapExceeded"]
    try:
        if price_only:
            gb = config["dry_run_gb"](sql)
            return _QueryOutcome(None, f"priced only at {gb:,.3f} GB, nothing executed", "priced")
        frame = config["q_guarded"](sql, max_gb=max_gb, note=note)
        return _QueryOutcome(frame, "", "")
    except unresolved as exc:
        return _QueryOutcome(None, str(exc), "placeholder")
    except over_cap as exc:
        return _QueryOutcome(None, str(exc), "cap")
    except Exception as exc:
        text = f"{type(exc).__name__}: {exc}"
        lowered = text.lower()
        kind = "permission" if any(word in lowered for word in
                                   ("permission", "forbidden", "denied", "access")) else "other"
        return _QueryOutcome(None, text, kind)


def _query_failure_verdict(key: str, headline: str, outcome: _QueryOutcome, *,
                           means: str, changes: str) -> ProbeVerdict:
    """One diagnosis per failure kind, so the reader is not offered the wrong explanation."""
    kind_means = {
        "placeholder": "an unresolved placeholder. NOTHING reached BigQuery, so no grant is "
                       "missing and nothing billed",
        "cap": "the cost cap refused the query. NOTHING executed and nothing billed; the "
               "dry-run estimate printed above is the real number",
        "permission": "a permissions error. Both endpoints are inside the perimeter, so this "
                      "is IAM rather than VPC Service Controls",
        "priced": "the run was asked to price only, so this query was estimated and not run",
        "other": "none of the rehearsed explanations. Believe the error above rather than a "
                 "guess",
    }[outcome.kind or "other"]
    status = STATUS_NOT_RUN
    return ProbeVerdict(
        key=key, status=status, headline=headline,
        checked="a guarded query, dry-run first and capped",
        came_back=outcome.failure,
        means=f"{kind_means}. {means}",
        changes=changes,
    )


# ======================================================================================
# (8) Printing. Everything that reaches a screen goes through here.
# ======================================================================================
# CLAUDE.md rule 1 is sharper in this project than in an ordinary one: the browser automation
# ships notebook output, screenshots and DOM to an external model, so "printed" means rendered
# anywhere inside this VM. There is therefore no informal print of a frame in this module.


def _rule(char: str = "=") -> str:
    return char * 86


def _heading(text: str) -> None:
    print("")
    print(_rule())
    print(text)
    print(_rule())


def _count(value: Any) -> Any:
    """A count on its way into the probe result: rounded, or the suppression sentinel."""
    if value is None:
        return None
    try:
        return round20(int(value))
    except (TypeError, ValueError):
        return round20(value)


def _print_frame(frame: pd.DataFrame, *, title: str, count_cols: Sequence[str] = (),
                 metadata_cols: Sequence[str] = ()) -> None:
    """Print an aggregate frame, or refuse it with the reasons. Never prints a raw row."""
    violations = print_violations(frame, count_cols=count_cols, metadata_cols=metadata_cols)
    if violations:
        listed = "\n".join(f"    {i}. {v}" for i, v in enumerate(violations, 1))
        raise ProbeStopCondition(
            f"refusing to print {title}: {len(violations)} disclosure violation(s)\n{listed}")
    print("")
    print(f"{title}  (rows: {disclosure.safe_n(frame)}, columns: {frame.shape[1]})")
    if frame.empty:
        print("  (no rows)")
        return
    for line in frame.to_string(index=False).splitlines():
        print("  " + line)


# ======================================================================================
# (9) PROBE 1. Do the Fitbit tables exist, and what is their DDL.
# ======================================================================================


def _probe_fitbit_tables(config: Mapping[str, Any], result: dict[str, Any], *,
                         price_only: bool) -> list[ProbeVerdict]:
    _heading("PROBE 1: are the Fitbit tables in this Controlled Tier CDR at all")
    print("INFORMATION_SCHEMA is metadata, so BigQuery answers it without scanning and the dry")
    print("run prices it at zero. The DDL comes back in the same call, which is where the")
    print("partitioning and clustering that build_all.sql needs come from for nothing.")

    block: dict[str, Any] = {"tables": [], "required": list(FITBIT_TABLES_REQUIRED),
                             "expected": list(FITBIT_TABLES_EXPECTED), "row counts": {},
                             "ddl": {}}
    result["fitbit tables"] = block

    outcome = _run_query(config, fitbit_tables_sql(), max_gb=FITBIT_SCHEMA_MAX_GB,
                         note="probe 1, Fitbit table existence and DDL")
    if outcome.frame is None:
        return [_query_failure_verdict(
            "PROBE 1", "the Fitbit table probe did not run", outcome,
            means="the binary risk this whole phase exists to retire is still open",
            changes="nothing below may assume a Fitbit table exists. Fix this first; it is the "
                    "cheapest question in the project and the one that can end it")]

    frame = outcome.frame
    safe_show(frame, name="INFORMATION_SCHEMA.TABLES, Fitbit-like")
    names = [str(v) for v in frame.get("table_name", pd.Series(dtype=object)).tolist()]
    block["tables"] = sorted(names)
    block["ddl"] = {str(row["table_name"]): str(row.get("ddl") or "")
                    for _, row in frame.iterrows()}

    listing = pd.DataFrame({
        "table": sorted(names),
        "needed by the plan": ["yes" if t in FITBIT_TABLES_REQUIRED else
                               ("wanted" if t in FITBIT_TABLES_EXPECTED else "no")
                               for t in sorted(names)],
    })
    _print_frame(listing, title="Fitbit-like tables visible in the CDR",
                 metadata_cols=["table", "needed by the plan"])

    counts = _run_query(config, table_row_counts_sql(), max_gb=FITBIT_SCHEMA_MAX_GB,
                        note="probe 1, free row-count metadata")
    if counts.frame is None:
        # Not a stop condition. `__TABLES__` is a legacy metatable and a release could stop
        # exposing it; the tables' existence, which is the question, is already answered.
        print("")
        print("row-count metadata is unavailable from the free metatable, which costs this probe")
        print(f"nothing that matters: {counts.failure[:160]}")
    else:
        rows = counts.frame.copy()
        rows["row_count"] = pd.to_numeric(rows["row_count"], errors="coerce").fillna(0).astype(int)
        block["row counts"] = {str(r["table_name"]): _count(r["row_count"])
                               for _, r in rows.iterrows()}
        shown = suppress_frame(pd.DataFrame({
            "table": rows["table_name"].astype(str),
            "rows": [int(v) for v in rows["row_count"]],
            "stored size, GB": [f"{float(v) / (1024 ** 3):,.2f}"
                                for v in pd.to_numeric(rows["size_bytes"],
                                                       errors="coerce").fillna(0)],
        }), ["rows"])
        _print_frame(shown, title="free row-count metadata",
                     count_cols=["rows"], metadata_cols=["table", "stored size, GB"])

    print("")
    print("DDL, which is where the partitioning and clustering live:")
    for name in sorted(block["ddl"]):
        print("")
        print(f"  -- {name}")
        for line in (block["ddl"][name] or "(no DDL returned)").splitlines():
            print("     " + line)

    missing = [t for t in FITBIT_TABLES_REQUIRED if t not in names]
    absent_wanted = [t for t in FITBIT_TABLES_EXPECTED if t not in names]
    if missing:
        return [ProbeVerdict(
            key="PROBE 1", status=STATUS_FAIL,
            headline="a Fitbit table the plan requires is not in this CDR",
            checked=f"INFORMATION_SCHEMA.TABLES in the resolved CDR for {list(FITBIT_TABLES_REQUIRED)}",
            came_back=f"absent: {missing}. Visible Fitbit-like tables: {sorted(names)}",
            means="the protocol was written against the Registered Tier and this is the "
                  "Controlled Tier. A sibling project's Fitbit code returning real numbers "
                  "against the same CDR was strong evidence and it was not a fact",
            changes="the study cannot be done as written in this tier. This is CLAUDE.md stop "
                    "condition 1: it changes the plan, it does not get worked around. Bring it "
                    "to the human before anything else is spent",
        )]

    note = "" if not absent_wanted else (
        f" Absent but not required: {absent_wanted}."
        + (" heart rate minute level is the input to the plan section 2.1 contingency audit, "
           "so without it the fallback is S2 rather than an audit."
           if "heart_rate_minute_level" in absent_wanted else ""))
    return [ProbeVerdict(
        key="PROBE 1", status=STATUS_PASS,
        headline="the Fitbit tables the plan requires are present",
        checked=f"INFORMATION_SCHEMA.TABLES in the resolved CDR for {list(FITBIT_TABLES_REQUIRED)}",
        came_back=f"present: {list(FITBIT_TABLES_REQUIRED)}.{note}",
        means="the project's binary risk is retired, for nothing, before any engineering",
        changes="nothing. The DDL above is recorded so build_all.sql prunes rather than scans",
    )]


# ======================================================================================
# (10) PROBE 2. The heart_rate_summary layout, which the cost design rests on.
# ======================================================================================


def _probe_heart_rate_summary(config: Mapping[str, Any], result: dict[str, Any], *,
                              price_only: bool, max_gb: float,
                              tables_present: Sequence[str]) -> list[ProbeVerdict]:
    _heading("PROBE 2: the heart rate summary layout, and whether the zones partition the day")
    print("Plan section 2.1 names two facts about this table as runtime probes rather than")
    print("assumptions: the exact per-zone minute column name, and that the zones partition the")
    print("day without double-counting a minute. The whole cost design rests on the second, at")
    print("about one three-hundredth of the bytes of the minute-level table.")

    block: dict[str, Any] = {"columns": [], "resolved": {}, "bands": {}, "zone labels": []}
    result["heart rate summary"] = block
    table = "heart_rate_summary"

    if table not in tables_present:
        verdict = ProbeVerdict(
            key="PROBE 2", status=STATUS_NOT_RUN,
            headline="the heart rate summary table is not visible, so its layout cannot be probed",
            checked="the table list returned by PROBE 1",
            came_back=f"{table} is not among {sorted(tables_present)}",
            means="the wear rule has no input in this CDR",
            changes="see PROBE 1. This is the same finding, not a second one",
        )
        return [verdict]

    columns = _run_query(config, columns_sql(table), max_gb=FITBIT_SCHEMA_MAX_GB,
                         note="probe 2, heart rate summary column list")
    if columns.frame is None:
        return [_query_failure_verdict(
            "PROBE 2", "the heart rate summary column list did not come back", columns,
            means="the exact per-zone minute column name is unresolved",
            changes="the wear query cannot be built against a guessed column name")]

    column_rows = columns.frame.to_dict("records")
    block["columns"] = [{"column": str(r.get("column_name")), "type": str(r.get("data_type")),
                         "nullable": str(r.get("is_nullable"))} for r in column_rows]
    _print_frame(pd.DataFrame(block["columns"]),
                 title=f"{table} columns, as INFORMATION_SCHEMA reports them",
                 metadata_cols=["column", "type", "nullable"])

    resolved, layout_verdict = pick_zone_columns(column_rows)
    block["resolved"] = resolved
    if layout_verdict.status != STATUS_PASS:
        return [layout_verdict]

    sql = zone_partition_sql(table_name=table, person_column=resolved["person"],
                             date_column=resolved["date"], zone_column=resolved["zone"],
                             minute_column=resolved["minute"])
    print("")
    print(f"the zone-partition check is the one query in this probe that is not free. It reads")
    print(f"four columns of {table} and returns counts of person-days only, never a person-day's")
    print(f"own summed minutes. Cap: {max_gb:,.1f} GB.")
    outcome = _run_query(config, sql, max_gb=max_gb, note="probe 2, zone partition check",
                         price_only=price_only)
    if outcome.frame is None:
        return [layout_verdict, _query_failure_verdict(
            "PROBE 2b", "the zone-partition check did not run", outcome,
            means="whether summing the per-zone minute column double counts a minute is still "
                  "unknown, and plan section 2.1 says it may not be assumed",
            changes="either raise the cap deliberately with the printed estimate in hand, or "
                    "apply the plan section 2.1 contingency and fall back to wear definition S2")]

    frame = outcome.frame
    safe_show(frame, name="zone-partition rollup")
    bands = {str(r["label"]): int(r["n"]) for _, r in frame.iterrows()
             if str(r["block"]) == "wear band"}
    zone_rows = frame[frame["block"] == "zone label"][["label", "n"]].copy()
    block["bands"] = {label: _count(value) for label, value in sorted(bands.items())}

    band_frame = suppress_frame(pd.DataFrame({"band": list(bands.keys()),
                                              "person days": list(bands.values())}),
                                ["person days"])
    band_frame = band_frame.sort_values("band", kind="mergesort").reset_index(drop=True)
    _print_frame(band_frame, title="summed per-zone minutes, by band",
                 count_cols=["person days"], metadata_cols=["band"])

    zone_rows = zone_rows.rename(columns={"label": "zone label", "n": "rows"})
    folded = fold_suppressed(zone_rows, count_col="rows", label_cols=["zone label"])
    block["zone labels"] = [{"zone label": str(r["zone label"]), "rows": r["rows"]}
                            for _, r in folded.iterrows()]
    _print_frame(folded, title="the zone vocabulary this CDR actually uses",
                 count_cols=["rows"], metadata_cols=["zone label"])

    total = bands.get("person days, all", 0)
    valid = bands.get(f"summed minutes {VALID_WEAR_MINUTES} to {MINUTES_PER_DAY}")
    if total and valid is not None:
        print("")
        print(f"person-days meeting the plan's {VALID_WEAR_MINUTES}-minute valid-wear rule: "
              f"{n_pct(valid, total)} of all person-days in this table.")

    return [layout_verdict, zone_partition_verdict(bands)]


# ======================================================================================
# (11) PROBE 3. The locked concept set against the real CDR.
# ======================================================================================


def _probe_concept_set(config: Mapping[str, Any], result: dict[str, Any], *,
                       price_only: bool, concept_max_gb: float, snomed_max_gb: float,
                       write_registry: bool, results_dir: pathlib.Path) -> list[ProbeVerdict]:
    _heading("PROBE 3: the locked 852-concept set against this CDR")
    print("cs_spine.assert_concept_frame has never been pointed at a real frame. It and the")
    print("module self-test build their fixtures from the same constants, so until now nothing")
    print("could detect drift between the locked set and the CDR. This is its first production")
    print("caller, and a different count is CLAUDE.md stop condition 2, not a note.")

    block: dict[str, Any] = {"expected": cs_spine.EXPECTED_CONCEPT_COUNT, "resolved": None,
                             "subtotals": {}, "snomed": {}, "registry": {}}
    result["concept set"] = block
    verdicts: list[ProbeVerdict] = []

    outcome = _run_query(config, cs_spine.concept_resolution_sql(), max_gb=concept_max_gb,
                         note="probe 3, locked concept set resolution", price_only=price_only)
    if outcome.frame is None:
        verdicts.append(_query_failure_verdict(
            "PROBE 3a", "the concept-set resolution did not run", outcome,
            means="drift between the locked 852 and the CDR remains undetectable, which is the "
                  "exact gap this probe exists to close",
            changes="nothing downstream may be built. The cohort, the episodes and every count "
                    "derive from this set"))
    else:
        frame = outcome.frame
        safe_show(frame, name="resolved concept frame")
        try:
            cs_spine.assert_concept_frame(frame)          # raises on ANY drift
            block["resolved"] = int(len(frame))
            block["subtotals"] = {
                "CPT-4": int((frame["vocabulary_id"] == "CPT4").sum()),
                "ICD-10-PCS fusion": int(((frame["vocabulary_id"] == "ICD10PCS") &
                                          (frame["procedure_class"] == "fusion")).sum()),
                "ICD-10-PCS decompression": int(((frame["vocabulary_id"] == "ICD10PCS") &
                                                 (frame["procedure_class"] == "decompression")).sum()),
            }
            # Vocabulary metadata, not participant data. cs_spine documents the concept frame as
            # safe to log whole, so these breakdowns are exact rather than rounded.
            for column in ("region", "procedure_class"):
                counts = frame[column].value_counts(dropna=False)
                shown = pd.DataFrame({column.replace("_", " "): [str(i) for i in counts.index],
                                      "concepts": [int(v) for v in counts.values]})
                _print_frame(shown, title=f"locked set by {column.replace('_', ' ')}",
                             metadata_cols=list(shown.columns))
            verdicts.append(ProbeVerdict(
                key="PROBE 3a", status=STATUS_PASS,
                headline="the locked concept set still resolves exactly",
                checked=f"cs_spine.concept_resolution_sql() against this CDR, validated by "
                        f"assert_concept_frame",
                came_back=f"{block['resolved']} source concepts, subtotals {block['subtotals']}",
                means="the CDR concept table has not moved under the locked decision file",
                changes="nothing. The concept-set stop condition now has a production caller, "
                        "so drift is detectable from this run onward"))
        except cs_spine.SpineConceptSetError as exc:
            verdicts.append(ProbeVerdict(
                key="PROBE 3a", status=STATUS_FAIL,
                headline="the locked concept set does not reconcile against this CDR",
                checked="cs_spine.assert_concept_frame on the frame this CDR returned",
                came_back=str(exc),
                means="the CDR concept table changed. Every downstream count is suspect: the "
                      "episode definition, the region tagging and the fusion-versus-"
                      "decompression contrast all read this set",
                changes="CLAUDE.md stop condition 2. Halt. Do not adjust the expected count to "
                        "match; reconcile the locked decision file with the CDR release, with "
                        "the human, and re-lock"))

    snomed = _run_query(config, cs_spine.snomed_crosscheck_sql(), max_gb=snomed_max_gb,
                        note="probe 3, SNOMED cross-check", price_only=price_only)
    if snomed.frame is None:
        verdicts.append(_query_failure_verdict(
            "PROBE 3b", "the SNOMED cross-check did not run", snomed,
            means="the mapping discrepancy CLAUDE.md stop condition 2 requires to be reported "
                  "is unmeasured",
            changes="the source-code path stays primary either way, but the Methods cannot "
                    "report a cross-check that did not happen. Re-run it"))
    else:
        sframe = snomed.frame
        safe_show(sframe, name="SNOMED cross-check frame")
        try:
            cs_spine.assert_snomed_frame(sframe)
            block["snomed"] = {"source concepts": int(sframe["n_source"].sum()),
                               "mapped": int(sframe["n_source_mapped"].sum()),
                               "standard concepts": int(sframe["n_standard"].sum())}
            verdicts.append(ProbeVerdict(
                key="PROBE 3b", status=STATUS_PASS,
                headline="every source concept still maps to a standard concept",
                checked="cs_spine.snomed_crosscheck_sql(), validated by assert_snomed_frame",
                came_back=f"{block['snomed']['mapped']} of "
                          f"{block['snomed']['source concepts']} source concepts carry a "
                          f"'Maps to' relationship",
                means="the CDR's vocabulary has not moved under the locked set",
                changes="nothing. The Methods reports full coverage, as the locked decision "
                        "measured it"))
        except cs_spine.SpineConceptSetError as exc:
            verdicts.append(ProbeVerdict(
                key="PROBE 3b", status=STATUS_FAIL,
                headline="the SNOMED cross-check no longer reconciles",
                checked="cs_spine.assert_snomed_frame on the frame this CDR returned",
                came_back=str(exc),
                means="the CDR's vocabulary changed even if the source-code count did not. The "
                      "source-code path stays primary, so this is not automatically fatal, but "
                      "it is a change nobody has explained",
                changes="report the discrepancy to the human at the Phase 2 hard stop, as "
                        "CLAUDE.md stop condition 2 requires. Do not proceed on the assumption "
                        "that it does not matter"))

    verdicts.append(_write_registry_ledger(config, block, results_dir,
                                           enabled=write_registry))
    return verdicts


def _write_registry_ledger(config: Mapping[str, Any], block: dict[str, Any],
                           results_dir: pathlib.Path, *, enabled: bool) -> ProbeVerdict:
    """Write ledger 1 of EXPORT-CONTRACT.md section 5.6, or say exactly why it was refused."""
    frame = registry_frame()
    target = results_dir / "ledgers-csv" / "ledger_concept_set_registry.csv"
    block["registry"] = {"rows": int(len(frame)), "columns": list(frame.columns),
                         "path": "ledgers-csv/ledger_concept_set_registry.csv",
                         "written": False, "md5": None, "refusals": []}
    # The column contract only. A registry row is vocabulary metadata and would be safe to
    # print, but there are fifty-one of them and the contract is the part a reader needs.
    _print_frame(pd.DataFrame(columns=list(frame.columns)),
                 title="concept-set registry, column contract",
                 metadata_cols=list(frame.columns))
    print(f"  the registry carries {len(frame)} rows, one per locked code or stem: "
          f"{cs_spine.EXPECTED_CPT_CONCEPTS} CPT-4 codes plus {len(cs_spine.ALL_PCS_STEMS)} "
          f"ICD-10-PCS stems. It holds no counts and therefore never suppresses.")

    if not enabled:
        return ProbeVerdict(
            key="PROBE 3c", status=STATUS_NOT_RUN,
            headline="the concept-set registry was not written, by request",
            checked="the --no-registry flag",
            came_back="the ledger was built and not written",
            means="EXPORT-CONTRACT.md section 5.6 requires this file on every run of the "
                  "bundle. This run is a probe, not an export, so skipping it is legal",
            changes="nothing, provided 07_export.py writes it. It is a pure function of the "
                    "locked constants, so the bytes are the same whoever writes them")

    block["registry"]["specification columns"] = list(REGISTRY_SPECIFICATION_COLUMNS)
    print(f"  {list(REGISTRY_SPECIFICATION_COLUMNS)} is declared a specification column, which "
          f"exempts it from")
    print("  the near-unique and identifier-like classes and from nothing else. A list of CPT")
    print("  and ICD-10-PCS codes is drawn from a published vocabulary and identifies nobody.")

    try:
        row = config["safe_export"](
            frame, target, kind="table-csv", exhibit="",
            specification_columns=REGISTRY_SPECIFICATION_COLUMNS,
            description=REGISTRY_LEDGER_DESCRIPTION)
        block["registry"]["written"] = True
        block["registry"]["md5"] = row["md5"]
        return ProbeVerdict(
            key="PROBE 3c", status=STATUS_PASS,
            headline="the concept-set registry was written to its contract path",
            checked="safe_export of cs_spine.registry_rows() to "
                    "results/ledgers-csv/ledger_concept_set_registry.csv, with the code column "
                    "declared a specification column",
            came_back=f"{row['n_rows']} rows, {row['n_columns']} columns, md5 {row['md5']}",
            means="the STROBE supplement's concept-set registry exists and is manifest-stampable",
            changes="07_export.py must write the identical bytes AND must declare the same one "
                    "specification column. registry_rows() is a pure function of the locked "
                    "constants, so a differing md5 means the module moved, not the data")
    except DisclosureError as exc:
        block["registry"]["refusals"] = str(exc).splitlines()
        return ProbeVerdict(
            key="PROBE 3c", status=STATUS_FAIL,
            headline="safe_export refused the concept-set registry",
            checked="safe_export of the eight-column registry that EXPORT-CONTRACT.md section "
                    "5.6 mandates, through the path the contract mandates, with "
                    f"{list(REGISTRY_SPECIFICATION_COLUMNS)} declared a specification column",
            came_back=str(exc),
            means="the one refusal this file used to draw, near-uniqueness of a code column "
                  "that is unique by construction, is now answered by that declaration. A "
                  "refusal standing here is therefore a DIFFERENT refusal, and the exporter "
                  "names which one above",
            changes="read the refusal above rather than widening the declaration. The exemption "
                    "covers the near-unique and identifier-like classes on named columns only; "
                    "a banned character, a count cell or a kind mismatch is a real finding "
                    "about the registry and gets fixed in cs_spine.py, not exempted here")
    except Exception as exc:                    # pragma: no cover - filesystem, not policy
        block["registry"]["refusals"] = [f"{type(exc).__name__}: {exc}"]
        return ProbeVerdict(
            key="PROBE 3c", status=STATUS_NOT_RUN,
            headline="the concept-set registry could not be written",
            checked=f"writing {target}",
            came_back=f"{type(exc).__name__}: {exc}",
            means="the failure is a filesystem or path problem rather than a disclosure one",
            changes="fix the path, or pass --results-dir. Nothing about the concept set itself "
                    "is in question")


# ======================================================================================
# (12) PROBE 4. The visit concept ids, enumerated rather than trusted.
# ======================================================================================


def _probe_visit_concepts(config: Mapping[str, Any], result: dict[str, Any], *,
                          price_only: bool, max_gb: float) -> list[ProbeVerdict]:
    _heading("PROBE 4: the emergency and inpatient visit concept ids")
    print("Plan section 4.1 requires these enumerated against the CDR's actual distribution")
    print("before being trusted, and CLAUDE.md rule 3 forbids choosing after seeing a number.")
    print("So the rule is fixed in this module's constants, and what the distribution measures")
    print("is whether the rule COVERS what this CDR holds.")
    print(f"  emergency department: {list(ED_VISIT_CONCEPT_IDS)}")
    print(f"  inpatient admission : {list(INPATIENT_VISIT_CONCEPT_IDS)}")
    print(f"  cap: {max_gb:,.1f} GB. This query reads two columns of visit occurrence plus the")
    print("  concept names, and is the first of the two queries in this run that scan visit")
    print("  occurrence. PROBE 6 is the other, and the two share this one cap.")

    block: dict[str, Any] = {"prespecified": {"emergency": list(ED_VISIT_CONCEPT_IDS),
                                              "inpatient": list(INPATIENT_VISIT_CONCEPT_IDS)},
                             "distribution": [], "classification": {}}
    result["visit concepts"] = block

    outcome = _run_query(config, visit_concept_distribution_sql(), max_gb=max_gb,
                         note="probe 4, visit concept id distribution", price_only=price_only)
    if outcome.frame is None:
        return [_query_failure_verdict(
            "PROBE 4", "the visit concept distribution did not run", outcome,
            means="the outcome definition of plan section 4.1 would have to be assumed, which "
                  "CLAUDE.md stop condition 1 names as a halting condition in its own right",
            changes="no cohort may be built on assumed visit concept ids. Re-run, or raise the "
                    "cap deliberately with the printed estimate in hand")]

    frame = outcome.frame
    safe_show(frame, name="visit concept distribution")
    rows = frame.to_dict("records")
    classification = classify_visit_concepts(rows)         # decides on RAW counts
    block["classification"] = {
        "emergency": [{**r, "n_visits": _count(r["n_visits"]), "n_persons": _count(r["n_persons"])}
                      for r in classification["emergency"]],
        "inpatient": [{**r, "n_visits": _count(r["n_visits"]), "n_persons": _count(r["n_persons"])}
                      for r in classification["inpatient"]],
        "candidates not used": [{**r, "n_visits": _count(r["n_visits"]),
                                 "n_persons": _count(r["n_persons"])}
                                for r in classification["candidates not used"]],
        "n distinct ids in the CDR": classification["n distinct ids in the CDR"],
        "absent prespecified ids": classification["absent prespecified ids"],
    }

    shown = pd.DataFrame({
        "visit concept id": frame["visit_concept_id"].astype("Int64").astype(str),
        "concept name": frame["concept_name"].fillna("(no concept name)").astype(str),
        "visits": pd.to_numeric(frame["n_visits"], errors="coerce").fillna(0).astype(int),
        "persons": pd.to_numeric(frame["n_persons"], errors="coerce").fillna(0).astype(int),
        "used by the cohort build": [
            _visit_role(int(v)) for v in
            pd.to_numeric(frame["visit_concept_id"], errors="coerce").fillna(-1).astype(int)],
    })
    # Fold on PERSONS, the count the disclosure floor is about. A concept whose person count is
    # below the floor loses its label with its count, exactly as safe_counts does, so a rare
    # encounter type is not disclosed by its mere presence in the output.
    folded = fold_suppressed(shown, count_col="persons",
                             label_cols=["visit concept id", "concept name",
                                         "used by the cohort build"])
    # round20 passes a non-number through unchanged, so the sentinel the fold already wrote
    # into the visits cell survives this without a special case.
    folded = suppress_frame(folded, ["visits"])
    block["distribution"] = folded.to_dict("records")
    _print_frame(folded, title="visit concept id distribution in this CDR",
                 count_cols=["visits", "persons"],
                 metadata_cols=["visit concept id", "concept name",
                                "used by the cohort build"])

    return [visit_concept_verdict(classification)]


def _visit_role(concept_id: int) -> str:
    roles = []
    if concept_id in ED_VISIT_CONCEPT_IDS:
        roles.append("emergency department")
    if concept_id in INPATIENT_VISIT_CONCEPT_IDS:
        roles.append("inpatient admission")
    return " and ".join(roles) if roles else "not used"


# ======================================================================================
# (13) PROBE 5. The environment facts a later session should not rediscover.
# ======================================================================================


def _probe_environment(config: Mapping[str, Any], result: dict[str, Any], *,
                       skip_cli: bool) -> list[ProbeVerdict]:
    _heading("PROBE 5: the environment facts, and the two deferred probes from SESSION-LOG.md")
    block: dict[str, Any] = {
        "google project": config["GOOGLE_PROJECT"],
        "workspace CDR": config["WORKSPACE_CDR"],
        "prep CDR": config["PREP_CDR"],
        "derived dataset": config["DERIVED"],
        "CDR location": config["CDR_LOCATION"],
        "write probe": config["WRITE_PROBE_RESULT"],
        "person rows, rounded": config["PERSON_N_ROUNDED"],
        "software versions": dict(config["SOFTWARE_VERSIONS"]),
        "R kernel visible": bool(config["R_KERNEL_VISIBLE"]),
        "wb resource list status": config["WB_RESOURCE_LIST_STATUS"],
        "wb resource list shape": "not attempted",
        "prep resolve": "not attempted",
    }
    result["environment"] = block

    for label in ("google project", "workspace CDR", "prep CDR", "derived dataset",
                  "CDR location", "write probe", "person rows, rounded",
                  "wb resource list status"):
        print(f"  {label:<26} {block[label]}")
    for name, value in block["software versions"].items():
        print(f"  {name:<26} {value}")

    verdicts: list[ProbeVerdict] = []
    run_wb = config.get("_run_wb")
    if skip_cli or run_wb is None:
        reason = ("the --skip-cli flag" if skip_cli else
                  "00_config.ipynb did not expose _run_wb, which is the helper whose reason "
                  "string tells the `wb` failure modes apart")
        verdicts.append(ProbeVerdict(
            key="PROBE 5", status=STATUS_NOT_RUN,
            headline="the two deferred command-line probes were not run",
            checked=reason,
            came_back=f"the recorded resource-list status is {block['wb resource list status']!r}",
            means="the `wb resource list --format=json` output shape and the "
                  "prep_C2025Q4R6 resolve stay unrecorded, so a later session rediscovers them",
            changes="nothing in the analysis. Run this probe without --skip-cli once, and paste "
                    "the two answers into SESSION-LOG.md so they stop being open"))
        return verdicts

    # ---- deferred probe A: the output SHAPE of `wb resource list --format=json` -----------
    # Key names and resource TYPES only. Those are workspace metadata of the same kind the
    # config already prints, and they are what a later session needs; the resource values are
    # not printed because nothing here needs them.
    code, stdout, reason = run_wb(["wb", "resource", "list", "--format=json"])
    if code != 0:
        block["wb resource list shape"] = f"failed: {reason}"
    else:
        text = (stdout or "").strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except ValueError as exc:
                block["wb resource list shape"] = f"exited 0 but the JSON did not parse ({exc})"
            else:
                keys = sorted({k for row in parsed if isinstance(row, Mapping) for k in row})
                types = sorted({str(row.get("resourceType") or row.get("type") or "")
                                for row in parsed if isinstance(row, Mapping)})
                block["wb resource list shape"] = {
                    "rows": len(parsed), "keys": keys, "resource types": types}
        else:
            block["wb resource list shape"] = ("exited 0 and printed a human-readable table "
                                               "rather than JSON")
    print("")
    print(f"  wb resource list --format=json shape: {block['wb resource list shape']}")

    # ---- deferred probe B: `wb resource resolve --name prep_C2025Q4R6` ---------------------
    # Inferred by symmetry from the documented C2025Q4R6 form and never run. It matters because
    # the {PREP} placeholder raises rather than substituting nothing, so a query that needs the
    # prep dataset fails hard rather than quietly.
    prep_name = f"prep_{cs_spine.CDR_OF_RECORD}"
    code, stdout, reason = run_wb(["wb", "resource", "resolve", "--name", prep_name])
    if code != 0:
        block["prep resolve"] = f"failed: {reason}"
        prep_ok = False
    else:
        lines = [line.strip() for line in (stdout or "").splitlines() if line.strip()]
        block["prep resolve"] = ("exited 0 and returned one id" if len(lines) == 1
                                 else f"exited 0 and printed {len(lines)} lines")
        prep_ok = len(lines) == 1 and lines[0] == config["PREP_CDR"]
        if len(lines) == 1 and not prep_ok:
            block["prep resolve"] += ", which does not match the configured prep dataset"
    print(f"  wb resource resolve --name {prep_name}: {block['prep resolve']}")

    if prep_ok:
        verdicts.append(ProbeVerdict(
            key="PROBE 5", status=STATUS_PASS,
            headline="both deferred command-line probes are now answered",
            checked=f"`wb resource list --format=json` and "
                    f"`wb resource resolve --name {prep_name}`",
            came_back=f"resource list shape {block['wb resource list shape']}; "
                      f"the prep resolve {block['prep resolve']} matching the configured "
                      f"prep dataset",
            means="the symmetric prep name is real rather than inferred, and the resource-list "
                  "output shape is recorded",
            changes="nothing. Paste both into SESSION-LOG.md section 5 and strike the two "
                    "carried-forward probe lines"))
    else:
        verdicts.append(ProbeVerdict(
            key="PROBE 5", status=STATUS_INCONCLUSIVE,
            headline=f"`wb resource resolve --name {prep_name}` did not return the configured "
                     f"prep dataset",
            checked=f"`wb resource resolve --name {prep_name}` against the configured PREP_CDR",
            came_back=f"{block['prep resolve']}; the configured prep dataset is "
                      f"{config['PREP_CDR']!r}",
            means="the prep name was inferred by symmetry from the documented C2025Q4R6 form "
                  "and has never been confirmed. It is fatal only for a query using the {PREP} "
                  "placeholder, and _fill raises there rather than substituting nothing",
            changes="nothing in the locked plan uses {PREP} today. Record the real name in "
                    "SESSION-LOG.md section 2 before anything does"))
    return verdicts


# ======================================================================================
# (14) PROBE 6. visit_source_value, the only evidence attrition rung 4's rescue reads.
# ======================================================================================
# DAG-SCHEMA.md section 9 item 6. Added after the original five because build_all.sql made
# rung 4's elective rescue depend on a column nothing had probed, and because the failure it
# guards against leaves no trace: the ladder prints a count, the count looks like an exclusion,
# and the exclusion was decided by an empty column.


def _probe_visit_source_value(config: Mapping[str, Any], result: dict[str, Any], *,
                              price_only: bool, max_gb: float) -> list[ProbeVerdict]:
    _heading("PROBE 6: visit source value, the column attrition rung 4's only rescue reads")
    print("build_all.sql keys rung 4's elective rescue AND the elective-admission exclusion in")
    print("`events` on one regular expression over one column, and visit_detail is deliberately")
    print("not consulted because its own population is unverified. The two failure directions")
    print("are not symmetric and only one of them is silent: in `events` a flag that is never")
    print("true excludes nothing, while in rung 4 a rescue that never fires excludes every")
    print("episode with an emergency encounter in the index window and the ladder reports a")
    print("count that reads as a real exclusion.")
    print(f"  column     : {VISIT_SOURCE_VALUE_COLUMN}")
    print(f"  pattern    : {ELECTIVE_SOURCE_VALUE_PATTERN!r}, the string build_all.sql writes")
    print(f"  concept ids: {list(ACUTE_CARE_VISIT_CONCEPT_IDS)}")
    print(f"  cap: {max_gb:,.1f} GB. INFORMATION_SCHEMA is free; the distribution is one grouped")
    print("  scan of two visit occurrence columns, and it SHARES the visit cap with PROBE 4")
    print("  rather than adding a cap of its own.")

    block: dict[str, Any] = {
        "column": VISIT_SOURCE_VALUE_COLUMN,
        "pattern": ELECTIVE_SOURCE_VALUE_PATTERN,
        "concept ids": list(ACUTE_CARE_VISIT_CONCEPT_IDS),
        "column present": None,
        "coverage": {}, "acute care coverage": {}, "distinct source values": {},
        "distribution": [],
    }
    result["visit source value"] = block

    # Free, and first: a priced scan of a column that is not there answers nothing and bills.
    columns = _run_query(config, columns_sql("visit_occurrence"), max_gb=FITBIT_SCHEMA_MAX_GB,
                         note="probe 6, visit occurrence column list")
    if columns.frame is None:
        return [_query_failure_verdict(
            "PROBE 6", "the visit occurrence column list did not come back", columns,
            means="whether the column rung 4's rescue reads even exists in this CDR is unknown",
            changes="resolve visibility of visit_occurrence first. It is the same table PROBE 4 "
                    "reads, so this is likely PROBE 4's finding rather than a second one")]

    names = [str(r.get("column_name", "")).strip().lower()
             for r in columns.frame.to_dict("records")]
    block["column present"] = VISIT_SOURCE_VALUE_COLUMN in names
    if not block["column present"]:
        return [ProbeVerdict(
            key="PROBE 6", status=STATUS_FAIL,
            headline="visit occurrence in this CDR has no source value column at all",
            checked=f"INFORMATION_SCHEMA.COLUMNS for visit_occurrence, for "
                    f"{VISIT_SOURCE_VALUE_COLUMN}",
            came_back=f"absent. The columns present are {sorted(name for name in names if name)}",
            means="attrition rung 4's elective rescue and the elective-admission exclusion in "
                  "`events` both reference a column that does not exist, so build_all.sql does "
                  "not compile against this CDR and rung 4 has no rescue to fire",
            changes="the ladder cannot be built as written. Read the column list above, then "
                    "either amend DAG-SCHEMA.md section 9 item 6 to the column this CDR does "
                    "ship or amend the plan so rung 4 excludes with no rescue and says so")]

    outcome = _run_query(config, visit_source_value_sql(), max_gb=max_gb,
                         note="probe 6, visit source value coverage and distribution",
                         price_only=price_only)
    if outcome.frame is None:
        return [_query_failure_verdict(
            "PROBE 6", "the source value coverage query did not run", outcome,
            means="whether rung 4's rescue can fire in this CDR is still unknown, and a rescue "
                  "that never fires excludes silently",
            changes="re-run, or raise the cap deliberately with the printed estimate in hand. "
                    "No ladder may be built on an unmeasured rescue")]

    frame = outcome.frame
    safe_show(frame, name="visit source value coverage")
    classification = classify_visit_source_values(frame.to_dict("records"))   # RAW counts
    coverage = classification["coverage"]
    acute = classification["acute care coverage"]
    block["coverage"] = {label: _count(value) for label, value in sorted(coverage.items())
                         if label != SOURCE_VALUE_DISTINCT}
    block["acute care coverage"] = {
        label: _count(value) for label, value in sorted(acute.items())
        if label not in (SOURCE_VALUE_DISTINCT, SOURCE_VALUE_DISTINCT_MATCHED)}
    # Cardinality of the CDR's own visit-type coding, not a count of participants or of their
    # records, and reported unrounded for the same reason PROBE 4 reports the number of distinct
    # visit concept ids unrounded. Rounding it would suppress the answer rather than protect it:
    # "this CDR uses nine source values" is what the reader needs and identifies nobody.
    block["distinct source values"] = {
        "all visits": coverage.get(SOURCE_VALUE_DISTINCT),
        "emergency and inpatient visits": acute.get(SOURCE_VALUE_DISTINCT),
        "matching the elective pattern": acute.get(SOURCE_VALUE_DISTINCT_MATCHED),
    }

    rows = []
    for population, mapping in (("all visits", coverage),
                                ("emergency and inpatient visits", acute)):
        for label in (SOURCE_VALUE_TOTAL, SOURCE_VALUE_NULLS, SOURCE_VALUE_EMPTIES,
                      SOURCE_VALUE_MATCHED):
            if label in mapping:
                rows.append({"population": population, "measure": label,
                             "visits": int(mapping[label])})
    coverage_frame = suppress_frame(
        pd.DataFrame(rows, columns=["population", "measure", "visits"]), ["visits"])
    _print_frame(coverage_frame, title=f"{VISIT_SOURCE_VALUE_COLUMN} coverage",
                 count_cols=["visits"], metadata_cols=["population", "measure"])
    print("")
    print("  distinct source values:")
    for population, value in block["distinct source values"].items():
        print(f"    {population:<32}: {value}")
    print("  A distinct-value count is the cardinality of this CDR's visit-type coding rather")
    print("  than a count of participants or of their records, so it is reported the way PROBE 4")
    print("  reports the number of distinct visit concept ids.")

    distribution = pd.DataFrame(classification["source values"],
                                columns=["source value", "visits",
                                         "matches the elective pattern"])
    # Folded on VISITS, which is what a two-column scan can offer and is weaker than a person
    # count in one direction: a label kept here could stand on fewer people than the floor. The
    # values are the CDR's own visit-type coding rather than a participant attribute, and the
    # fold is applied to them anyway, so a value the CDR barely uses loses its label with its
    # count exactly as safe_counts would do it.
    folded = fold_suppressed(distribution, count_col="visits",
                             label_cols=["source value", "matches the elective pattern"])
    block["distribution"] = folded.to_dict("records")
    _print_frame(folded,
                 title="visit source values over the emergency and inpatient concept ids",
                 count_cols=["visits"],
                 metadata_cols=["source value", "matches the elective pattern"])

    return [visit_source_value_verdict(classification)]


# ======================================================================================
# (15) The run: every probe, every verdict, one halt at the end.
# ======================================================================================

_JSON_OPEN = "----- BEGIN PROBE RESULT (JSON) -----"
_JSON_CLOSE = "----- END PROBE RESULT (JSON) -----"


def _repo_root() -> pathlib.Path:
    """The one root every default path in this module hangs off."""
    return _PIPELINE_DIR.parent if _PIPELINE_DIR is not None else pathlib.Path.cwd()


def _default_results_dir() -> pathlib.Path:
    return _repo_root() / "results"


def _default_probe_json_path() -> pathlib.Path:
    """`v1/probe/probe_result.json`, resolved the same way `--results-dir` is resolved."""
    return _repo_root() / PROBE_RESULT_RELATIVE_PATH


def run_probe(namespace: Mapping[str, Any] | None = None, *, halt: bool = True,
              price_only: bool = False, skip_cli: bool = False, write_registry: bool = True,
              results_dir: pathlib.Path | str | None = None,
              zone_max_gb: float = ZONE_PARTITION_MAX_GB,
              concept_max_gb: float = CONCEPT_RESOLUTION_MAX_GB,
              snomed_max_gb: float = SNOMED_CROSSCHECK_MAX_GB,
              visit_max_gb: float = VISIT_DISTRIBUTION_MAX_GB) -> dict[str, Any]:
    """Run every probe, print every diagnosis, return the machine-readable result.

    Halts at the END rather than at the first finding, so one VM session reports everything it
    knows. `halt=False` returns the result instead of raising, which is what a notebook cell
    that wants to inspect the dict should pass.
    """
    config = resolve_config(namespace)
    started = dt.datetime.now(dt.timezone.utc)
    results_path = pathlib.Path(results_dir) if results_dir is not None \
        else _default_results_dir()

    result: dict[str, Any] = {
        "meta": {
            "module": "01_probe.py",
            "started": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "google project": config["GOOGLE_PROJECT"],
            "workspace CDR": config["WORKSPACE_CDR"],
            "CDR location": config["CDR_LOCATION"],
            "derived dataset": config["DERIVED"],
            "software versions": dict(config["SOFTWARE_VERSIONS"]),
            "priced only": bool(price_only),
            "byte caps, GB": {
                "zone partition": zone_max_gb,
                "concept resolution": concept_max_gb,
                "SNOMED cross-check": snomed_max_gb,
                "visit distribution": visit_max_gb,
                "visit source value": visit_max_gb,
            },
        },
        "verdicts": [],
    }

    _heading("01_probe.py: the runtime probes, at the top of Phase 2")
    print("Every query below dry-runs first and carries a hard byte cap, so an over-budget")
    print("query fails rather than bills. Every count printed goes through round20; counts of")
    print("20 or fewer are suppressed. Nothing participant-level reaches this screen.")
    if price_only:
        print("")
        print("PRICED ONLY: the metadata queries run, because they are free and because nothing")
        print("below can be priced without the table list. The five priced queries are estimated")
        print("and NOT executed, so this run answers cost and answers nothing else.")

    verdicts: list[ProbeVerdict] = []
    verdicts += _probe_fitbit_tables(config, result, price_only=price_only)
    tables_present = result["fitbit tables"]["tables"]
    verdicts += _probe_heart_rate_summary(config, result, price_only=price_only,
                                          max_gb=zone_max_gb, tables_present=tables_present)
    verdicts += _probe_concept_set(config, result, price_only=price_only,
                                   concept_max_gb=concept_max_gb, snomed_max_gb=snomed_max_gb,
                                   write_registry=write_registry, results_dir=results_path)
    verdicts += _probe_visit_concepts(config, result, price_only=price_only,
                                      max_gb=visit_max_gb)
    verdicts += _probe_environment(config, result, skip_cli=skip_cli)
    verdicts += _probe_visit_source_value(config, result, price_only=price_only,
                                          max_gb=visit_max_gb)

    _heading("Diagnoses")
    for verdict in verdicts:
        if verdict.status != STATUS_PASS:
            print(diagnosis_text(verdict))
    if all(v.status == STATUS_PASS for v in verdicts):
        print("every probe passed. The four sentences of each are in the JSON block below.")

    result["verdicts"] = [dict(v._asdict()) for v in verdicts]
    result["halting"] = sorted({v.key for v in verdicts if v.halts})
    result["probe ok"] = not result["halting"]

    _heading("Summary")
    summary = pd.DataFrame({
        "probe": [v.key for v in verdicts],
        "verdict": [v.status for v in verdicts],
        "finding": [v.headline for v in verdicts],
    })
    _print_frame(summary, title="probe verdicts",
                 metadata_cols=["probe", "verdict", "finding"])

    cost = config["session_cost_report"]()
    result["meta"]["session cost"] = {"queries": cost["queries"],
                                      "GB billed": round(cost["bytes_billed"] / (1024 ** 3), 3),
                                      "USD": round(cost["usd"], 4)}

    if result["halting"] and halt:
        raise ProbeStopCondition(
            "the runtime probes did not all pass: "
            + ", ".join(f"{v.key} {v.status}" for v in verdicts if v.halts)
            + ". Each diagnosis above says what changes about the plan. A probe failure changes "
              "the plan; it does not get worked around.")
    return result


def _emit_json(result: Mapping[str, Any]) -> str:
    """Print the probe result as one JSON block, for the SESSION-LOG.md handoff.

    Printed AS WELL AS written, not instead. The block is what a human pastes into
    SESSION-LOG.md section 6; `v1/probe/probe_result.json` is what the next session reads under
    EXPORT-CONTRACT.md section 1, and `main()` writes it there by default. `--write-json PATH`
    sends the file somewhere else; it still refuses any path inside a `results` tree.
    """
    payload = json.dumps(result, indent=2, sort_keys=True, default=str)
    print("")
    print(_JSON_OPEN)
    print(payload)
    print(_JSON_CLOSE)
    return payload


def _write_json(payload: str, path: pathlib.Path) -> None:
    """Write the probe result where it is named, refusing the export bundle.

    The refusal of a `results` path is unchanged and still right: that tree is the export
    bundle, section 1 declares it exhaustively, and a probe result inside it is exactly the
    straggler `verify.py --bundle` rule 3 fails on. What changed is the last sentence. The
    contract now NAMES the probe artefact, so a refusal saying it names none was false, and a
    refusal that offers no alternative is how the next workaround gets written.
    """
    legal = _default_probe_json_path()
    parts = {part.lower() for part in path.resolve().parts}
    if "results" in parts:
        raise ProbeStopCondition(
            f"refusing to write the probe result to {path}: it is inside a `results` tree, and "
            f"EXPORT-CONTRACT.md section 1 declares that tree exhaustively while section 0 "
            f"forbids a module from writing a file the contract does not name. The legal path "
            f"is {legal}, which the contract names in section 1 and which this module writes to "
            f"by default. Write it there, or anywhere else outside the bundle.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload + "\n", encoding="utf-8")
    print(f"probe result written to {path}")


# ======================================================================================
# (16) Command line.
# ======================================================================================


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="01_probe.py",
        description="Runtime probes for the spine wearable study, run at the top of Phase 2 "
                    "inside the perimeter.")
    parser.add_argument("--self-test", action="store_true",
                        help="exercise the pure logic against synthetic frames and exit. "
                             "No cloud, no configuration, no files written.")
    parser.add_argument("--price-only", action="store_true",
                        help="dry-run every priced query and execute none of them.")
    parser.add_argument("--skip-cli", action="store_true",
                        help="skip the two `wb` command-line probes of PROBE 5.")
    parser.add_argument("--no-registry", action="store_true",
                        help="build the concept-set registry ledger and do not write it.")
    parser.add_argument("--results-dir", default=None,
                        help="the results tree the ledger is written into. Defaults to the "
                             "repo's own results directory.")
    parser.add_argument("--write-json", default=None,
                        help=f"write the probe result somewhere other than the default, which "
                             f"is {PROBE_RESULT_RELATIVE_PATH} under the repo root, the path "
                             f"EXPORT-CONTRACT.md section 1 names. Refused inside a results "
                             f"tree.")
    parser.add_argument("--max-gb-zone", type=float, default=ZONE_PARTITION_MAX_GB,
                        help=f"cap for the zone-partition check (default {ZONE_PARTITION_MAX_GB}).")
    parser.add_argument("--max-gb-concept", type=float, default=CONCEPT_RESOLUTION_MAX_GB,
                        help=f"cap for the concept resolution "
                             f"(default {CONCEPT_RESOLUTION_MAX_GB}).")
    parser.add_argument("--max-gb-snomed", type=float, default=SNOMED_CROSSCHECK_MAX_GB,
                        help=f"cap for the SNOMED cross-check (default {SNOMED_CROSSCHECK_MAX_GB}).")
    parser.add_argument("--max-gb-visits", type=float, default=VISIT_DISTRIBUTION_MAX_GB,
                        help=f"cap for the visit distribution "
                             f"(default {VISIT_DISTRIBUTION_MAX_GB}).")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Exit 0 all probes passed, 1 a stop condition fired, 2 no configuration, 64 usage."""
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return 64 if exc.code not in (0, None) else 0

    if args.self_test:
        _run_self_test()
        return 0

    try:
        result = run_probe(
            halt=False,
            price_only=args.price_only,
            skip_cli=args.skip_cli,
            write_registry=not args.no_registry,
            results_dir=args.results_dir,
            zone_max_gb=args.max_gb_zone,
            concept_max_gb=args.max_gb_concept,
            snomed_max_gb=args.max_gb_snomed,
            visit_max_gb=args.max_gb_visits,
        )
    except ProbeStopCondition as exc:
        # A configuration failure, not a probe finding: run_probe was told not to halt on
        # findings. Printed as a diagnosis rather than a traceback, like everything else here.
        print("")
        print(_rule())
        print("01_probe.py HALTED before any probe ran")
        print(_rule())
        for line in str(exc).splitlines():
            print("  " + line)
        print(_rule())
        return 2

    payload = _emit_json(result)
    named = bool(args.write_json)
    target = pathlib.Path(args.write_json) if named else _default_probe_json_path()
    # WRITTEN BY DEFAULT, because EXPORT-CONTRACT.md section 1 tells the next session to read
    # this file and to run the probe only when it is absent. The one exception is a priced-only
    # run: it executed nothing, every probe comes back not-run, and letting that overwrite a
    # real result would cost the session it exists to save. A human who names a path still gets
    # exactly the path they named.
    written = False
    if named or not args.price_only:
        try:
            _write_json(payload, target)
            written = True
        except ProbeStopCondition as exc:
            print("")
            for line in str(exc).splitlines():
                print("  " + line)
            return 64
    else:
        print("")
        print("priced only, so the probe result was NOT written to")
        print(f"  {target}")
        print("This run executed nothing, so every probe is not-run, and writing that would")
        print("overwrite a real result. Pass --write-json PATH to write it anyway.")

    if not result["probe ok"]:
        print("")
        print(_rule())
        print("01_probe.py HALTED: " + ", ".join(result["halting"]))
        print("Each diagnosis above says what was checked, what came back, what it means and")
        print("what changes about the plan. A probe failure changes the plan; it never gets")
        print("worked around. Report at the Phase 2 hard stop, then delete the environment.")
        print(_rule())
        return 1

    print("")
    if written:
        print("every probe passed, and the result is on disk at the path printed above, which is")
        print("what EXPORT-CONTRACT.md section 1 tells the next session to read instead of")
        print("re-running this.")
    else:
        print("every probe passed, and nothing was written. The JSON block above is the")
        print("only copy of this result.")
    print("Paste the JSON block into SESSION-LOG.md section 6, then run session_cost_report(),")
    print("delete the compute environment, and verify the Apps tab.")
    return 0


# ======================================================================================
# (17) Self-test. Everything checkable without the cloud.
# ======================================================================================
# Same shape as `_run_self_test()` in disclosure.py: `python3 01_probe.py --self-test` answers
# "is the pure logic of this module sane" with no pytest, no configuration and no network. The
# assertion count is MEASURED by the helper rather than tallied by hand, for the reason
# cs_spine.py gives: a hand-kept `n += k` cannot see a loop bound and drifts from the truth.
#
# `_expect` raises rather than using the `assert` statement, because `python -O` strips an
# assert and a stop condition that disappears under an optimization flag is worse than none.

_ASSERTIONS_EXECUTED = 0


def _expect(condition: bool, message: str) -> None:
    global _ASSERTIONS_EXECUTED
    _ASSERTIONS_EXECUTED += 1
    if not condition:
        raise AssertionError(message)


def _bands(**overrides: int) -> dict[str, int]:
    """A band dict shaped like the zone-partition query's own output."""
    ceiling = MINUTES_PER_DAY
    bands = {
        "person days, all": 100000,
        "persons contributing": 12000,
        f"summed minutes below {VALID_WEAR_MINUTES}": 30000,
        f"summed minutes {VALID_WEAR_MINUTES} to {ceiling}": 70000,
        f"summed minutes above {ceiling}": 0,
        f"summed minutes {CEILING_BAND_FLOOR} to {ceiling}": 9000,
        "person days with a repeated zone label": 0,
        "person days with a null zone minute cell": 0,
        "person days with no summed total": 0,
    }
    bands.update(overrides)
    return bands


# The layout 02_pregate.py declared for itself, and the one the rule chain could not resolve
# before the `min...zone` rung existed: `min_in_zone` contains neither "minute" nor a numeric
# name cue, so rungs 1, 2 and 4 all miss it.
_ABBREVIATED_HR_COLUMNS = [
    {"column_name": "person_id", "data_type": "INT64"},
    {"column_name": "date", "data_type": "DATE"},
    {"column_name": "zone_name", "data_type": "STRING"},
    {"column_name": "min_in_zone", "data_type": "INT64"},
    {"column_name": "calorie_count", "data_type": "FLOAT64"},
]


def _source_rows(**overrides) -> list[dict]:
    """Rows shaped exactly like `visit_source_value_sql()`'s own three-block output."""
    coverage = {SOURCE_VALUE_TOTAL: 9000000, SOURCE_VALUE_NULLS: 40000,
                SOURCE_VALUE_EMPTIES: 0, SOURCE_VALUE_DISTINCT: 31}
    acute = {SOURCE_VALUE_TOTAL: 900000, SOURCE_VALUE_NULLS: 4000, SOURCE_VALUE_EMPTIES: 0,
             SOURCE_VALUE_DISTINCT: 9, SOURCE_VALUE_MATCHED: 120000,
             SOURCE_VALUE_DISTINCT_MATCHED: 3}
    values = [("Elective Inpatient Admission", 100000), ("Emergency Admission", 500000),
              ("Scheduled Surgery", 20000), ("(null)", 4000)]
    coverage.update(overrides.pop("coverage", {}))
    acute.update(overrides.pop("acute", {}))
    values = overrides.pop("values", values)
    drop = set(overrides.pop("drop", ()))
    if overrides:
        raise AssertionError(f"unknown fixture override: {sorted(overrides)}")
    rows = [{"block": "coverage", "label": k, "n": v} for k, v in coverage.items()]
    rows += [{"block": "acute care coverage", "label": k, "n": v}
             for k, v in acute.items() if k not in drop]
    rows += [{"block": "source value", "label": k, "n": v} for k, v in values]
    return rows


_CANONICAL_HR_COLUMNS = [
    {"column_name": "person_id", "data_type": "INT64"},
    {"column_name": "date", "data_type": "DATE"},
    {"column_name": "zone_name", "data_type": "STRING"},
    {"column_name": "min_heart_rate", "data_type": "INT64"},
    {"column_name": "max_heart_rate", "data_type": "INT64"},
    {"column_name": "minute_in_zone", "data_type": "INT64"},
    {"column_name": "calorie_count", "data_type": "FLOAT64"},
]


def _run_self_test() -> None:
    ceiling = MINUTES_PER_DAY

    # ---- 1. the layout probe -----------------------------------------------------------
    resolved, verdict = pick_zone_columns(_CANONICAL_HR_COLUMNS)
    _expect(verdict.status == STATUS_PASS, "the canonical layout resolves")
    _expect(resolved == {"person": "person_id", "date": "date", "zone": "zone_name",
                         "minute": "minute_in_zone"}, "and resolves to the four exact names")

    renamed = [{"column_name": "person_id", "data_type": "INT64"},
               {"column_name": "activity_date", "data_type": "DATE"},
               {"column_name": "hr_zone", "data_type": "STRING"},
               {"column_name": "minutes_in_hr_zone", "data_type": "INT64"}]
    resolved2, verdict2 = pick_zone_columns(renamed)
    _expect(verdict2.status == STATUS_PASS, "a renamed but unambiguous layout still resolves")
    _expect(resolved2["minute"] == "minutes_in_hr_zone" and resolved2["zone"] == "hr_zone",
            "by the naming rules rather than by the exact names")

    ambiguous = [{"column_name": "person_id", "data_type": "INT64"},
                 {"column_name": "date", "data_type": "DATE"},
                 {"column_name": "zone_name", "data_type": "STRING"},
                 {"column_name": "minutes_in_zone", "data_type": "INT64"},
                 {"column_name": "active_minutes_in_zone", "data_type": "INT64"}]
    resolved3, verdict3 = pick_zone_columns(ambiguous)
    _expect(verdict3.status == STATUS_FAIL and resolved3 == {},
            "two candidate minute columns is an ambiguity, not a coin toss")
    _expect("ambiguous" in verdict3.came_back, "and the diagnosis says which role was ambiguous")

    missing = [{"column_name": "person_id", "data_type": "INT64"},
               {"column_name": "date", "data_type": "DATE"}]
    _, verdict4 = pick_zone_columns(missing)
    _expect(verdict4.status == STATUS_FAIL, "a layout with no zone column fails")
    _expect("wear rule cannot be built" in verdict4.means, "with the consequence named")
    _expect("The columns present are ['date', 'person_id']" in verdict4.came_back,
            "and a miss still quotes the observed column list, which is what a human reads to "
            "decide whether to extend the rules or amend the plan")
    _, verdict5 = pick_zone_columns([])
    _expect(verdict5.status == STATUS_NOT_RUN, "an empty column list is not run rather than failed")

    # THE ABBREVIATED SPELLING, and the whole reason the chain has a third rung. `min_in_zone`
    # was what 02_pregate.py declared for itself and interpolated into a query that EXECUTES
    # under an 18 GiB cap, while the two files that agreed on `minute_in_zone` never run. Before
    # the rung existed this layout returned mapping {}, status fail, "no column matched any rule
    # for the minute column", which made `probe ok` false and ended Phase 2 on a column name.
    resolved6, verdict6 = pick_zone_columns(_ABBREVIATED_HR_COLUMNS)
    _expect(verdict6.status == STATUS_PASS, "the abbreviated min_in_zone layout now resolves")
    _expect(resolved6 == {"person": "person_id", "date": "date", "zone": "zone_name",
                          "minute": "min_in_zone"},
            "to all four roles, with the minute column read as min_in_zone")
    _expect(HR_ZONE_MINUTE_COLUMN == "minute_in_zone",
            "and the documented All of Us name is still the constant two of the three files use")
    _expect(resolved["minute"] == HR_ZONE_MINUTE_COLUMN,
            "which is what the canonical layout resolves to, so the constant is the first guess "
            "of the chain rather than a fifth opinion beside it")

    # AN EXACT MATCH ALWAYS WINS. The new rung sits below the exact-name rung, so a CDR shipping
    # both spellings resolves to the documented one rather than to whichever sorts first.
    both = _ABBREVIATED_HR_COLUMNS + [{"column_name": HR_ZONE_MINUTE_COLUMN,
                                       "data_type": "INT64"}]
    resolved7, verdict7 = pick_zone_columns(both)
    _expect(verdict7.status == STATUS_PASS and resolved7["minute"] == HR_ZONE_MINUTE_COLUMN,
            "with both spellings present the exact name wins over the broadened rule")

    # AND IT STILL FAILS LOUDLY ON A GENUINE AMBIGUITY. Two columns matching at the SAME rung is
    # a stop, not a first-one-wins: nothing below may be built from a coin toss.
    ambiguous_min = [{"column_name": "person_id", "data_type": "INT64"},
                     {"column_name": "date", "data_type": "DATE"},
                     {"column_name": "zone_name", "data_type": "STRING"},
                     {"column_name": "min_in_zone", "data_type": "INT64"},
                     {"column_name": "mins_in_zone", "data_type": "INT64"}]
    resolved8, verdict8 = pick_zone_columns(ambiguous_min)
    _expect(verdict8.status == STATUS_FAIL and resolved8 == {},
            "two columns matching the broadened rule at the same rung is an ambiguity")
    _expect("ambiguous" in verdict8.came_back
            and "['min_in_zone', 'mins_in_zone']" in verdict8.came_back,
            "and the diagnosis names both candidates rather than silently taking the first")
    _expect("The columns present are" in verdict8.came_back,
            "and quotes the observed column list beside them")
    # The rung ordering is load-bearing in the other direction too: the pre-existing ambiguity
    # of `minutes_in_zone` against `active_minutes_in_zone` is decided at rung 2, ABOVE the new
    # rung, so broadening the chain did not quietly disambiguate a pair that is genuinely
    # ambiguous. verdict3 above is that pair, and it is still a fail.
    _expect(verdict3.status == STATUS_FAIL,
            "and the pre-existing minute-and-zone ambiguity is still decided above the new rung")

    # ---- 2. the partition verdict, on frames that do and do not double-count -------------
    good = zone_partition_verdict(_bands())
    _expect(good.status == STATUS_PASS, "nothing above the ceiling with a populated top band "
                                        "is a partition")
    _expect(str(ceiling) in good.came_back, "and the diagnosis names the ceiling it checked")

    overlapping = zone_partition_verdict(_bands(**{f"summed minutes above {ceiling}": 4200}))
    _expect(overlapping.status == STATUS_FAIL, "person-days above the ceiling are overlap")
    _expect("S2" in overlapping.changes, "and route to the plan's prespecified S2 fallback")
    _expect("300 times the bytes" in overlapping.changes,
            "and say explicitly that they do not route to minute-level counting")

    # The trap this check exists for: a cohort that wears the device half the day looks exactly
    # like a nested scheme in the mean, the median and the maximum. Both frames below have the
    # same low totals; only the tail above the ceiling separates them, and it is the tail that
    # decides here.
    poor_wear = zone_partition_verdict(_bands(**{
        f"summed minutes {CEILING_BAND_FLOOR} to {ceiling}": 0,
        f"summed minutes {VALID_WEAR_MINUTES} to {ceiling}": 20000,
        f"summed minutes below {VALID_WEAR_MINUTES}": 80000}))
    _expect(poor_wear.status == STATUS_INCONCLUSIVE,
            "no full-wear day means overlap cannot be excluded, so the verdict is inconclusive")
    _expect("cannot tell them apart" in poor_wear.means,
            "and the diagnosis names the confound rather than declaring success")
    nested_but_low = zone_partition_verdict(_bands(**{
        f"summed minutes {CEILING_BAND_FLOOR} to {ceiling}": 0,
        f"summed minutes above {ceiling}": 90}))
    _expect(nested_but_low.status == STATUS_FAIL,
            "the same low distribution WITH a tail above the ceiling is overlap, not poor wear")

    duplicated = zone_partition_verdict(_bands(**{"person days with a repeated zone label": 60}))
    _expect(duplicated.status == STATUS_FAIL, "a repeated zone label on a person-day is a failure")
    _expect("duplication" in duplicated.means and "de-duplicate" in duplicated.changes,
            "and it is diagnosed as duplication with a different fix from overlap")
    _expect(duplicated.means != overlapping.means,
            "the two double-counting failures do not share a diagnosis")

    empty = zone_partition_verdict(_bands(**{"person days, all": 0}))
    _expect(empty.status == STATUS_NOT_RUN, "an empty table is not run rather than passed")
    partial = zone_partition_verdict({"person days, all": 10})
    _expect(partial.status == STATUS_NOT_RUN, "a result missing the bands is not run")
    _expect("absent from the result" in partial.came_back, "and says which bands were absent")

    nulls = zone_partition_verdict(_bands(**{"person days with a null zone minute cell": 400}))
    _expect(nulls.status == STATUS_PASS and "null zone minute cell" in nulls.came_back,
            "a null minute cell is reported even when the partition holds, because SUM skips it")

    # ---- 3. the visit-id selection -------------------------------------------------------
    full = [{"visit_concept_id": 9201, "concept_name": "Inpatient Visit",
             "n_visits": 900000, "n_persons": 120000},
            {"visit_concept_id": 9203, "concept_name": "Emergency Room Visit",
             "n_visits": 400000, "n_persons": 90000},
            {"visit_concept_id": 262, "concept_name": "Emergency Room and Inpatient Visit",
             "n_visits": 50000, "n_persons": 20000},
            {"visit_concept_id": 9202, "concept_name": "Outpatient Visit",
             "n_visits": 8000000, "n_persons": 300000}]
    clean = classify_visit_concepts(full)
    _expect(clean["absent prespecified ids"] == [], "every prespecified id is present")
    _expect(clean["candidates not used"] == [], "and nothing unused reads as acute care")
    _expect(all(row["present"] for row in clean["emergency"]),
            "both emergency ids come back present")
    _expect(visit_concept_verdict(clean).status == STATUS_PASS, "so the verdict passes")
    _expect("262 is in both" in visit_concept_verdict(clean).changes,
            "and the verdict says WHY the chosen ids are the chosen ids")

    with_candidate = classify_visit_concepts(full + [
        {"visit_concept_id": 32037, "concept_name": "Intensive Care",
         "n_visits": 20000, "n_persons": 6000}])
    _expect([r["visit_concept_id"] for r in with_candidate["candidates not used"]] == [32037],
            "an unused id whose name reads as acute care is reported as a candidate")
    candidate_verdict = visit_concept_verdict(with_candidate)
    _expect(candidate_verdict.status == STATUS_INCONCLUSIVE,
            "a candidate makes the verdict inconclusive rather than silently widening the rule")
    _expect("rule 3" in candidate_verdict.means,
            "and the diagnosis cites the rule that forbids widening after seeing the number")

    absent = classify_visit_concepts([r for r in full if r["visit_concept_id"] != 262])
    _expect(absent["absent prespecified ids"] == [262], "an absent prespecified id is caught")
    absent_verdict = visit_concept_verdict(absent)
    _expect(absent_verdict.status == STATUS_FAIL, "and it is a failure, not a note")
    _expect("amended" in absent_verdict.changes, "with the amendment named as the fix")
    _expect(classify_visit_concepts([])["n distinct ids in the CDR"] == 0,
            "an empty distribution classifies without raising")
    _expect(_visit_role(262) == "emergency department and inpatient admission",
            "262 is labelled as both, which is what plan section 4.1 collapses")

    # ---- 3b. PROBE 6, the elective proxy attrition rung 4's only rescue reads ------------
    # The FAIL condition is zero matches, and it is the point of the probe: with an always-false
    # rescue, rung 4 excludes every episode with an emergency encounter in the index window and
    # the ladder prints a count that reads as a real exclusion.
    _expect(matches_elective_pattern("Elective Inpatient Admission")
            and matches_elective_pattern("SCHEDULED ADMIT")
            and matches_elective_pattern("pre-scheduled"),
            "the Python proxy matches the same wording build_all.sql's expression matches")
    _expect(not matches_elective_pattern("Emergency Admission")
            and not matches_elective_pattern("") and not matches_elective_pattern(None),
            "and matches neither an emergency admission nor an absent value")
    _expect(ELECTIVE_SOURCE_VALUE_PATTERN in visit_source_value_sql(),
            "the query tests the pattern the build ships rather than one like it")
    _expect(list(ACUTE_CARE_VISIT_CONCEPT_IDS) == sorted(set(ED_VISIT_CONCEPT_IDS)
                                                        | set(INPATIENT_VISIT_CONCEPT_IDS)),
            "measured over the union of the two prespecified sets, which 262 collapses to three")

    populated = classify_visit_source_values(_source_rows())
    _expect(populated["acute care coverage"][SOURCE_VALUE_MATCHED] == 120000,
            "the three blocks are split apart by block name rather than by row order")
    _expect([r["source value"] for r in populated["source values"]][0] == "Emergency Admission",
            "and the distribution is sorted by descending visits, not alphabetically")
    _expect([r["matches the elective pattern"] for r in populated["source values"]]
            == ["no", "yes", "yes", "no"],
            "each value carries whether the build's own expression would rescue it")
    source_ok = visit_source_value_verdict(populated)
    _expect(source_ok.status == STATUS_PASS,
            "a populated source value with real matches passes")
    _expect("9 distinct value(s)" in source_ok.came_back,
            "and the diagnosis reports the distinct-value count of the column")
    _expect("null or empty source value" in source_ok.came_back,
            "and the null rate beside it")

    silent = classify_visit_source_values(_source_rows(acute={SOURCE_VALUE_MATCHED: 0,
                                                             SOURCE_VALUE_DISTINCT_MATCHED: 0}))
    source_fail = visit_source_value_verdict(silent)
    _expect(source_fail.status == STATUS_FAIL,
            "zero matches is a FAIL, because that is the condition under which rung 4 silently "
            "over-excludes")
    _expect("never fire" in source_fail.headline,
            "and the headline says the rescue can never fire rather than reporting a rate")
    _expect("rung 4" in source_fail.means and "excludes nothing" in source_fail.means,
            "and the diagnosis names the asymmetry: `events` fails safe, rung 4 does not")
    _expect("0 (0%)" in source_fail.came_back,
            "with the zero itself in the came-back sentence")

    all_null = classify_visit_source_values(_source_rows(
        acute={SOURCE_VALUE_NULLS: 900000, SOURCE_VALUE_MATCHED: 0,
               SOURCE_VALUE_DISTINCT: 0, SOURCE_VALUE_DISTINCT_MATCHED: 0}, values=[]))
    _expect(visit_source_value_verdict(all_null).status == STATUS_FAIL,
            "a column that is null on every acute-care visit fails by the same rule")

    thin = classify_visit_source_values(_source_rows(
        acute={SOURCE_VALUE_MATCHED: disclosure.MIN_CELL, SOURCE_VALUE_DISTINCT_MATCHED: 1}))
    source_thin = visit_source_value_verdict(thin)
    _expect(source_thin.status == STATUS_INCONCLUSIVE,
            "a match count at or below the disclosure floor is inconclusive, not a pass: the "
            "rescue fires and how often cannot be said out loud")
    _expect(is_suppressed(SUPPRESSED) and SUPPRESSED not in source_thin.came_back,
            "and the suppressed count is described rather than printed as the sentinel")
    _expect("rule 3" in source_thin.changes,
            "and widening the pattern after seeing the distribution is named as forbidden")

    empty_pop = classify_visit_source_values(_source_rows(
        acute={SOURCE_VALUE_TOTAL: 0, SOURCE_VALUE_MATCHED: 0}, values=[]))
    _expect(visit_source_value_verdict(empty_pop).status == STATUS_NOT_RUN,
            "no acute-care visit at all is PROBE 4's finding, so this one is not run")
    truncated = classify_visit_source_values(_source_rows(drop=(SOURCE_VALUE_MATCHED,)))
    source_partial = visit_source_value_verdict(truncated)
    _expect(source_partial.status == STATUS_NOT_RUN
            and SOURCE_VALUE_MATCHED in source_partial.came_back,
            "and a result missing the deciding band is not run, naming the band that was absent")
    _expect(visit_source_value_verdict({}).status == STATUS_NOT_RUN,
            "an empty classification is not run rather than passing by default")

    # ---- 4. every diagnosis is a diagnosis ----------------------------------------------
    all_verdicts = [verdict, verdict2, verdict3, verdict4, verdict5, verdict6, verdict7,
                    verdict8, good, overlapping, poor_wear, nested_but_low, duplicated, empty,
                    partial, nulls, visit_concept_verdict(clean), candidate_verdict,
                    absent_verdict, source_ok, source_fail, source_thin, source_partial]
    for item in all_verdicts:
        _expect(item.status in (STATUS_PASS, STATUS_FAIL, STATUS_INCONCLUSIVE, STATUS_NOT_RUN),
                f"{item.key} carries a known status")
        _expect(all(bool(str(field).strip()) for field in
                    (item.headline, item.checked, item.came_back, item.means, item.changes)),
                f"{item.key} says what was checked, what came back, what it means and what changes")
        rendered = diagnosis_text(item)
        _expect(item.headline in rendered, f"{item.key} renders its headline")
        _expect("Traceback" not in rendered, f"{item.key} renders a diagnosis, not a traceback")
        for character in disclosure.BANNED_CHARACTERS:
            _expect(character not in rendered, f"{item.key} carries no banned dash character")

    # ---- 5. SQL hygiene ------------------------------------------------------------------
    sanctioned = {"{CDR}", "{PREP}", "{DERIVED}"}
    brace = re.compile(r"\{[^}]*\}")
    backticked = re.compile(r"`([^`]*)`")
    for name, sql in all_sql_for_audit().items():
        found = set(brace.findall(sql))
        _expect(found <= sanctioned, f"{name} uses only the sanctioned placeholders, saw {found}")
        _expect("{CDR}" in sql, f"{name} names the CDR through the placeholder")
        _expect("RAND(" not in sql.upper(), f"{name} contains no RAND()")
        _expect(cs_spine.CDR_OF_RECORD not in sql, f"{name} hardcodes no CDR resource name")
        _expect("spinewear_v1" not in sql, f"{name} hardcodes no dataset name")
        _expect("wb-" not in sql, f"{name} hardcodes no project id")
        for span in backticked.findall(sql):
            _expect(span.startswith(("{CDR}", "{PREP}", "{DERIVED}")),
                    f"{name} quotes only placeholder-rooted identifiers, saw `{span}`")
        for character in disclosure.BANNED_CHARACTERS:
            _expect(character not in sql, f"{name} carries no banned dash character")
    zone_sql = all_sql_for_audit()["zone partition"]
    _expect("MAX(" not in zone_sql.upper() and "APPROX_QUANTILES" not in zone_sql.upper(),
            "the zone check returns counts of person-days and no person-day's own value")
    _expect(f"> {ceiling}" in zone_sql, "and it counts the band above the ceiling explicitly")
    try:
        columns_sql("heart_rate_summary; DROP TABLE x")
        raise AssertionError("an identifier that is not an identifier reached SQL")
    except ProbeStopCondition:
        _expect(True, "a table name that is not a bare identifier never reaches a query")

    # ---- 6. the concept-set registry ledger ----------------------------------------------
    registry = registry_frame()
    _expect(tuple(registry.columns) == cs_spine.REGISTRY_COLUMNS,
            "the registry carries the contract's eight columns, in order")
    _expect(len(registry) == cs_spine.EXPECTED_CPT_CONCEPTS + len(cs_spine.ALL_PCS_STEMS),
            "one row per locked code or stem")
    _expect(all(isinstance(v, str) for v in registry.to_numpy().ravel()),
            "every cell is a display string, as section 5.6 requires of a ledger")
    _expect(set(registry["is_add_on"]) <= {"true", "false"},
            "booleans print as true and false")
    _expect(list(registry["vocabulary_id"]) == sorted(registry["vocabulary_id"]),
            "rows are sorted by the contract's sort keys")
    _expect("region" not in registry.columns,
            "there is no bare region column; region primary and region mirrored replaced it")

    # THE MANIFEST DESCRIPTION, pinned against the contract rather than against a second
    # transcription of it. It used to read "One row per concept", which is the 852 claim written
    # into MANIFEST.csv beside `n_rows = 51`, on the one file whose entire point is that those
    # two numbers are different. The literal below is checked unconditionally; when this
    # checkout carries EXPORT-CONTRACT.md the contract's own bytes are checked too, so the two
    # cannot drift apart again without one of these failing.
    _expect(REGISTRY_LEDGER_DESCRIPTION == "One row per code or stem in the locked spine "
                                           "concept set with its region and add-on tags",
            "the registry ledger's manifest description is the contract's sentence verbatim")
    _expect("per code or stem" in REGISTRY_LEDGER_DESCRIPTION
            and "per concept" not in REGISTRY_LEDGER_DESCRIPTION,
            "it says code or stem and not concept, because the file has one row per code")
    _expect(len(REGISTRY_LEDGER_DESCRIPTION) <= 120,
            "and it fits the contract's 120-character manifest description limit")
    _contract = _find_export_contract()
    if _contract is None:                              # pragma: no cover - a partial checkout
        _expect(True, "EXPORT-CONTRACT.md is not on this checkout, so the literal above is the "
                      "only pin available and it has just been checked")
    else:
        _contract_text = _contract.read_text(encoding="utf-8")
        _expect(REGISTRY_LEDGER_DESCRIPTION in _contract_text,
                f"and {_contract.name} carries that exact sentence, so the manifest row this "
                f"module writes matches the row the contract specifies")
        _expect("One row per concept in the locked spine" not in _contract_text,
                "and the contract does not carry the superseded wording anywhere")

    # WHAT THIS PINS, and it used to pin the opposite. The ledger the contract mandates was
    # refused by the exporter the contract mandates: a registry of codes has one row per code,
    # so its `code` column is unique by construction and tripped the near-unique class. The
    # resolution is a DECLARATION, not a removed check. `specification_columns` names the
    # columns whose values come from a published vocabulary rather than from participants, and
    # lifts the near-unique and identifier-like classes on those columns only. So there are
    # three things to hold, and the second and third are what stop the declaration from
    # becoming a blanket exemption.
    undeclared = disclosure.export_violations(registry, kind="table-csv",
                                              path="ledger_concept_set_registry.csv")
    _expect(len(undeclared) > 0 and any("near-unique" in r for r in undeclared),
            "without the declaration the registry is still refused, so the check was not "
            "removed; the near-unique class still sees the code column")

    refusals = disclosure.export_violations(
        registry, kind="table-csv", path="ledger_concept_set_registry.csv",
        specification_columns=REGISTRY_SPECIFICATION_COLUMNS)
    _expect(refusals == [],
            "and with `code` declared a specification column the mandated registry exports")
    _expect(tuple(REGISTRY_SPECIFICATION_COLUMNS) == ("code",),
            "exactly one column is declared, because it is the only one that needs it")
    _expect(all(c in registry.columns for c in REGISTRY_SPECIFICATION_COLUMNS),
            "and the declared column is really in the frame, so the exemption is not a no-op")

    # The exemption is PER COLUMN and is not granted to an undeclared sibling. Same content,
    # different name, not declared: still refused. A column-name typo in 07_export.py therefore
    # fails loudly rather than silently exporting a near-unique column nobody exempted.
    sibling = registry.assign(**{"code note": registry["code"]})
    sibling_refusals = disclosure.export_violations(
        sibling, kind="table-csv", path="ledger_concept_set_registry.csv",
        specification_columns=REGISTRY_SPECIFICATION_COLUMNS)
    _expect(any("'code note'" in r and "near-unique" in r for r in sibling_refusals),
            "an undeclared sibling holding the same values is still refused as near-unique")
    _expect(not any("'code'" in r for r in sibling_refusals),
            "and the declared column is still exempt beside it, so the two do not interfere")

    # ---- 7. folding, the way safe_counts folds -------------------------------------------
    raw = pd.DataFrame({"label": ["common", "rarer", "rarest"], "persons": [4000, 300, 3]})
    folded = fold_suppressed(raw, count_col="persons", label_cols=["label"])
    _expect("rarest" not in list(folded["label"]), "a suppressed label is suppressed with its count")
    _expect(list(folded["persons"])[:2] == [4000, 300], "the disclosable rows keep rounded counts")
    _expect(is_suppressed(list(folded["persons"])[-1]), "and the folded row carries the sentinel")
    _expect(len(fold_suppressed(raw.iloc[:2], count_col="persons", label_cols=["label"])) == 2,
            "a frame with nothing to fold gains no sentinel row")

    # ---- 8. the print gate ---------------------------------------------------------------
    clean_frame = pd.DataFrame({"band": ["a", "b"], "person days": [40, 60]})
    _expect(print_violations(clean_frame, count_cols=["person days"],
                             metadata_cols=["band"]) == [],
            "a fully declared, fully rounded frame may be printed")
    _expect(len(print_violations(clean_frame, count_cols=["person days"])) == 1,
            "an undeclared column is refused: nothing is printed by omission")
    _expect(len(print_violations(pd.DataFrame({"n": [7]}), count_cols=["n"])) == 1,
            "a count below the floor is refused")

    # THE TWO CELLS THAT DECIDE WHICH PREDICATE THIS GATE ASKS. This gate is handed a RENDERED
    # frame, so it asks `is_legal_disclosed_count`, not `disclosable`.
    #   a rendered 20 is round20(21) through round20(29) and MUST be accepted, and asking
    #     `disclosable` here refused it, which refused every correctly rounded frame;
    #   a raw 21 is not a multiple of the rounding base, so it is a caller who forgot to round
    #     and MUST still be refused. That is the strictness the class was written for and it
    #     survives the change.
    # Neither numeral is written as a literal: both come out of `round20`.
    rendered_floor = round20(disclosure.MIN_CELL + 1)
    _expect(print_violations(pd.DataFrame({"n": [rendered_floor]}), count_cols=["n"]) == [],
            "a rounded cell standing on a true count just above the floor may be printed")
    _expect(all(print_violations(pd.DataFrame({"n": [round20(k)]}), count_cols=["n"]) == []
                for k in range(0, 200)),
            "and so may every other cell round20 can produce, across two hundred true counts")
    _expect(len(print_violations(pd.DataFrame({"n": [disclosure.MIN_CELL + 1]}),
                                 count_cols=["n"])) == 1,
            "while an unrounded count just above the floor is still refused, because a caller "
            "who forgot to round is exactly what this class exists to catch")
    # THE ONE RESIDUAL GAP, pinned so nobody later reads it as an oversight. A raw count of
    # exactly the floor is the one unrounded value this gate cannot see, because it is the same
    # integer as a correctly rounded one and the true count is gone by the time the gate runs.
    # It is bounded: `round20` is the only sanctioned way to produce a count for printing and it
    # emits the sentinel for a true count at the floor, never the numeral; and the floor itself
    # is enforced upstream by `fold_suppressed`, where the true count still exists.
    _expect(print_violations(pd.DataFrame({"n": [disclosure.MIN_CELL]}), count_cols=["n"]) == [],
            "a raw count AT the floor is indistinguishable from a rounded one and passes; this "
            "is the documented residual gap, and fold_suppressed is what closes it upstream")
    _expect(is_suppressed(list(fold_suppressed(
                pd.DataFrame({"label": ["thin"], "n": [disclosure.MIN_CELL]}),
                count_col="n", label_cols=["label"])["n"])[-1]),
            "and fold_suppressed does close it: a true count at the floor becomes the sentinel, "
            "so the numeral this gate would accept is never produced in the first place")
    _expect(print_violations(pd.DataFrame({"n": [0]}), count_cols=["n"]) == [],
            "a true zero is an absence rather than a small cell, and prints")
    _expect(print_violations(pd.DataFrame({"n": [SUPPRESSED]}), count_cols=["n"]) == [],
            "and the suppression sentinel is a legal cell in a count column")
    dated = pd.DataFrame({"day": pd.to_datetime(["2020-01-01", "2020-01-02"])})
    _expect(len(print_violations(dated, metadata_cols=["day"])) == 1,
            "a date column is refused, because Controlled Tier dates are unshifted")
    dashed = pd.DataFrame({"label": ["a" + disclosure.EM_DASH + "b"]})
    _expect(len(print_violations(dashed, metadata_cols=["label"])) == 1,
            "a banned dash character is refused")
    _expect(len(print_violations(clean_frame, count_cols=["person days"],
                                 metadata_cols=["band", "person days"])) >= 1,
            "a column declared as both count and metadata is refused")

    # ---- 9. the probe artefact path, and the refusal that now names it -------------------
    # EXPORT-CONTRACT.md section 1 names `v1/probe/probe_result.json` and tells the next session
    # to read it and to run the probe only when it is absent. With no default, a probe run wrote
    # nothing and every later session paid to re-run it; and the refusal asserted the contract
    # named no artefact, which the same commit made false.
    default_json = _default_probe_json_path()
    _expect(PROBE_RESULT_RELATIVE_PATH == "probe/probe_result.json",
            "the probe artefact is the path EXPORT-CONTRACT.md section 1 names")
    _expect(default_json.parts[-2:] == ("probe", "probe_result.json"),
            "and the resolved default really ends at that path")
    _expect(default_json.parent.parent == _default_results_dir().parent,
            "resolved off the same repo root --results-dir is resolved off, by the same helper")
    _expect("results" not in {part.lower() for part in default_json.parts},
            "and it sits OUTSIDE the export bundle, so the default is not a path this module "
            "would refuse")
    try:
        _write_json("{}", _default_results_dir() / "probe_result.json")
        raise AssertionError("a probe result was accepted into the export bundle")
    except ProbeStopCondition as refusal:
        _expect("`results` tree" in str(refusal),
                "a results path is still refused, because that tree is Phase 4's bundle")
        _expect(str(default_json) in str(refusal),
                "and the refusal now NAMES the legal path, because a refusal that offers no "
                "alternative is how the next workaround gets written")
        _expect("names no probe artefact" not in str(refusal),
                "and no longer asserts the contract names none, which it now does")
    _expect("names no probe artefact" not in (__doc__ or ""),
            "and the module docstring does not assert it either")
    _expect(not (_default_results_dir() / "probe_result.json").exists(),
            "and the refusal happened before anything was created on disk")

    # ---- 10. house prose on every rendered string ----------------------------------------
    rendered_strings = [diagnosis_text(v) for v in all_verdicts]
    rendered_strings += list(all_sql_for_audit().values())
    rendered_strings += [_JSON_OPEN, _JSON_CLOSE, __doc__ or ""]
    for text in rendered_strings:
        for character in disclosure.BANNED_CHARACTERS:
            _expect(character not in text, "no banned dash character reaches a rendered string")

    print(_rule())
    print("01_probe.py SELF-TEST: PASS")
    print(_rule())
    print(f"  assertions executed        : {_ASSERTIONS_EXECUTED}")
    print(f"  zone verdicts covered      : {STATUS_PASS}, {STATUS_FAIL} on overlap, "
          f"{STATUS_FAIL} on a repeated zone label,")
    print(f"                               {STATUS_INCONCLUSIVE} when no day reaches the top "
          f"band, {STATUS_NOT_RUN}")
    print(f"  the discriminator          : person-days above {ceiling} summed minutes. Non-wear "
          f"can only")
    print( "                               reduce a total, so a total above the ceiling can only")
    print( "                               be a minute counted twice")
    print(f"  visit ids, prespecified    : emergency {list(ED_VISIT_CONCEPT_IDS)}, "
          f"inpatient {list(INPATIENT_VISIT_CONCEPT_IDS)}")
    print(f"  zone minute column         : {HR_ZONE_MINUTE_COLUMN} is the first guess and the "
          f"exported constant;")
    print( "                               the chain also resolves min_in_zone, and two "
           "candidates at one")
    print( "                               rung is a fail with the observed columns quoted")
    print(f"  PROBE 6, elective proxy    : {ELECTIVE_SOURCE_VALUE_PATTERN!r} over "
          f"{VISIT_SOURCE_VALUE_COLUMN} on visit ids")
    print(f"                               {list(ACUTE_CARE_VISIT_CONCEPT_IDS)}. Zero matches "
          f"is a FAIL, because that is")
    print( "                               when attrition rung 4 silently over-excludes")
    print(f"  SQL builders audited       : {len(all_sql_for_audit())}, placeholders limited to "
          f"{{CDR}}, {{PREP}}, {{DERIVED}}")
    print(f"  registry ledger            : {len(registry)} rows x {len(registry.columns)} "
          f"columns, all display strings")
    print(f"  registry export            : ACCEPTED by export_violations with "
          f"{list(REGISTRY_SPECIFICATION_COLUMNS)} declared a")
    print(f"                               specification column; refused without it "
          f"({len(undeclared)} violation(s)), and the")
    print( "                               exemption is not granted to an undeclared sibling")
    print( "  count-cell predicate       : is_legal_disclosed_count on the RENDERED cell, so a")
    print( "                               rounded floor value prints and an unrounded count "
           "does not")
    print( "  byte caps declared         : "
          f"zone {ZONE_PARTITION_MAX_GB}, concept {CONCEPT_RESOLUTION_MAX_GB}, "
          f"SNOMED {SNOMED_CROSSCHECK_MAX_GB}, visits {VISIT_DISTRIBUTION_MAX_GB} GB")
    print(f"  probe artefact             : {PROBE_RESULT_RELATIVE_PATH} under the repo root, "
          f"by default; a")
    print( "                               `results` path is refused and the refusal names the "
           "legal one")
    print(f"  manifest description       : pinned against "
          f"{'EXPORT-CONTRACT.md' if _contract is not None else 'the literal only'}, "
          f"{len(REGISTRY_LEDGER_DESCRIPTION)} characters")
    print( "  read                       : EXPORT-CONTRACT.md, to pin that description")
    print( "  wrote                      : nothing. No cloud, no configuration, no files")


if __name__ == "__main__":
    raise SystemExit(main())
