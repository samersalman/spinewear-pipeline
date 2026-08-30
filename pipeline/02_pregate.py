#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02_pregate.py -- Phase 2.  The cheap upper-bound counts, and the hard stop they feed.

WHERE THIS RUNS.  INSIDE THE PERIMETER, and only there, for the four queries and the report.
It is the highest-value cheap step in the plan: roughly twenty minutes of VM time and about
fifteen cents of BigQuery, spent before a single derived table exists, to answer the one
question that decides how the rest of the study is built.  LOCALLY it still runs, and running
it locally is the intended way to check it: `python3 02_pregate.py` executes `_run_self_test()`,
which exercises every pure decision in the module against synthetic frames, touches no network
and writes no file.

IN-PERIMETER USE, in a notebook, AFTER the probe has run and passed:

    %run 00_config.ipynb
    %run -i 01_probe.py                   # writes PROBE, or halts with a diagnosis
    %run -i 02_pregate.py                 # -i: run in the kernel that already holds q_guarded
    PREGATE = run_pregate(probe_result=PROBE)

THE VISIT CONCEPT IDS ARE NOT AN ARGUMENT.  They are PRESPECIFIED in 01_probe.py as
`ED_VISIT_CONCEPT_IDS` and `INPATIENT_VISIT_CONCEPT_IDS`, VERIFIED by that module against the
CDR's own visit distribution, and IMPORTED here as their union,
`ED_AND_INPATIENT_VISIT_CONCEPT_IDS`.  Prespecify then verify is the discipline this project
runs on; choosing ids after seeing a distribution is the post-hoc choice the prespecification
exists to prevent.  And there is still no silent default, which is the other half of the same
requirement: `run_pregate` REFUSES TO RUN unless it is handed a probe result whose `probe ok`
is true, so CLAUDE.md stop condition 1 -- which halts the build when these concepts "are
assumed rather than enumerated against the CDR's actual distribution" -- is satisfied by
evidence rather than by a constant.  `PreGateError` fires when the probe result is absent, is
not what `run_probe()` returns, or carries a false verdict.

WHAT IT COMPUTES, in the plan's own order (locked plan, Phase 2 item 4):

  1. Spine surgical episodes with any Fitbit activity data.
  2. Of those, episodes with at least 7 valid wear days spanning at least 14 calendar days in
     postoperative days -30 to -8.
  3. Of those, episodes with an emergency-department or inpatient encounter in postoperative
     days 1 to 90.
  4. All of the above stratified by anatomic region and fusion status, so the thinnest cell is
     visible at the stop rather than three phases later.

FUSION STATUS READS ALL QUALIFYING EVIDENCE, ADD-ON CODES INCLUDED.  `has_fusion` is
`LOGICAL_OR(procedure_class = 'fusion')` over every record in the same-day bundle, with no
add-on filter, which is the reading `build_all.sql` has always used for the DAG's own episode
table.  This module used to filter add-ons out of that predicate and record the filter as a
deliberate choice; the human decided in favour of the DAG's reading and the choice recorded
here is now the opposite one.  The reasoning, rather than the assertion: fourteen of the
sixteen add-on and instrumentation codes in the locked set carry `procedure_class = 'fusion'`,
instrumentation without arthrodesis is essentially never performed in degenerative spine
surgery, and the filtered and unfiltered readings differ ONLY on an episode whose primary
arthrodesis code is absent from the record.  That absence is a CODING-CAPTURE GAP, not a
clinical fact, and on such an episode the add-on is the only evidence the fusion happened.
Filtering it out puts a fusion patient on the decompression arm.

THIS DOES NOT WEAKEN THE ADD-ON RULE.  An add-on still cannot establish that AN OPERATION
HAPPENED.  The requirement of at least one `is_add_on = FALSE` record before a same-day bundle
counts as an operation is unchanged, and a bundle of instrumentation alone is still not an
episode and is still not counted.  The decision is only about which ARM an already-established
episode belongs to.  The two predicates are emitted by two SEPARATE FUNCTIONS, `_fusion_flag`
and `_operation_exists_having`, so that a later reader cannot merge them back into one
expression and lose the distinction.  The REGION half keeps its add-on filter and needed no
change: every add-on in the locked set is tagged 'unspecified' in both region columns, which is
asserted at import, so an add-on can never override a cervical, lumbar or thoracic assignment.

EVERY ONE OF THEM IS AN UPPER BOUND.  They are computed BEFORE the nineteen-rung eligibility
ladder of ANALYSIS-PLAN.md section 2.6, so each can only fall once Phase 3 runs.  The report
says so in words, in every place a number appears, because a reader comparing these numbers
against the later ladder will otherwise read the difference as attrition when most of it is
definition.

IT ALSO MEASURES THE TWO CONCEPT-SET GAPS and applies the response prespecified for each in
ANALYSIS-PLAN.md section 2.7.  It does NOT amend the locked concept set.  Amending it would
break the 852 assertion and everything calibrated to it; measuring a code is not adding it.
The measurement goes in front of the human at this stop, with the prespecified consequence of
each threshold already written down, so the branch cannot be chosen after the number is seen.

WHAT THIS MODULE DELIBERATELY DOES NOT DO.  It materializes nothing into {DERIVED}, builds no
part of the DAG, and applies no exclusion beyond the two the concept set itself requires (see
`APPLIED_HERE` below).  That is Phase 3's job, it costs twenty times as much, and doing it here
would spend the budget this hard stop exists to protect.  A self-test assertion holds the
emitted SQL to it: no data-definition statement, and no {DERIVED} placeholder, in any query.

COST.  `q_guarded` is the only query path, every call is dry-run first, and every call carries
a `maximum_bytes_billed` cap sized against the scan it expects.  On top of the per-query caps
there is an aggregate guard: the four queries are ALL priced before ANY of them executes, the
plan is printed, and the module refuses to run at all if the measured total exceeds
`PREGATE_BUDGET_GB`.  A dry run is free, so the pre-flight costs nothing and the refusal
happens with the real number in the human's hand rather than after the bill.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

# `pipeline/` is not a package and this file's name is not an importable identifier, so it is
# always a script: `%run` inside the perimeter, `python3` on a laptop.  Both need the module's
# own directory on the path before `import cs_spine` can resolve, and neither guarantees it
# (a notebook's cwd is the repo root as often as it is `pipeline/`).
try:
    _HERE = str(Path(__file__).resolve().parent)
except NameError:                                  # exec'd without a file, e.g. a paste
    _HERE = str(Path.cwd())
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import pandas as pd

import cs_spine
from disclosure import (
    EM_DASH,
    MINUS_SIGN,
    SUPPRESSED,
    DisclosureError,
    disclosable,
    export_violations,
    is_suppressed,
    n_pct,
    round20,
    safe_show,
    suppress_frame,
)


class PreGateError(RuntimeError):
    """A pre-gate stop condition.  Never downgraded to a warning."""


class PreGateBudgetExceeded(PreGateError):
    """The priced total exceeded the step's budget, so nothing executed and nothing billed.

    A class of its own for the same reason the config notebook gives `QueryCapExceeded` one: a
    refusal by the budget is not a permissions problem and not a bad query, and the diagnosis
    printed beside it has to be able to branch on which of the three happened.
    """


# ======================================================================================
# (1) The vocabularies this module owns, and the three it borrows.
#
# Borrowed vocabularies are ASSERTED at import rather than retyped.  cs_spine owns the region
# and class names; if either set is ever edited there, this module's CASE expressions would
# quietly stop matching and every stratum would collapse into "Region unspecified only".  A
# stop condition at import is cheaper than a table of zeros at the stop.
#
# 01_probe.py owns the visit concept ids, and that borrowing is the one worth explaining,
# because this module used to demand them as an argument with no default.  Two positions had to
# be reconciled and both were right about something.
#
#   The PROBE's position, on the substance: the ids are PRESPECIFIED here and the probe VERIFIES
#   them against the CDR's actual distribution, flagging any acute-care-named id that sits
#   outside the prespecified sets.  Prespecify then verify is the discipline the whole project
#   runs on, and picking ids after seeing a distribution is precisely the post-hoc choice the
#   prespecification exists to prevent.
#
#   THIS module's position, on the mechanism: a SILENT DEFAULT must remain impossible.
#   CLAUDE.md stop condition 1 halts the build when these are "assumed rather than enumerated
#   against the CDR's actual distribution", and a constant nobody checked is an assumption.
#
# Both hold together: the constants are IMPORTED from the probe, so they are prespecified in one
# place and never retyped, and `run_pregate` REFUSES TO RUN unless it is handed a probe result
# whose `probe ok` is true, so they have also been verified against this CDR before a single
# byte is billed.  `PreGateError` still fires when the probe result is absent or its verdict is
# false, which are the two ways a default could otherwise creep back in.
# ======================================================================================

# 01_probe.py's filename begins with a digit, so `import 01_probe` is a syntax error and no
# amount of sys.path work will make it one.  It is loaded by PATH, explicitly, which is the
# same mechanism a test module needs to load THIS file.  The loader is a function rather than
# four lines at module scope so the self-test can call it and check what it returns.
_PROBE_FILENAME = "01_probe.py"
_PROBE_MODULE_NAME = "_pregate_probe_01"

# A bare SQL identifier and nothing else.  It lives here rather than beside `_validated_schema`,
# its other caller, because the borrowed table and column names below are checked against it AT
# IMPORT, before that function exists.  Everything that reaches a query from outside this file
# passes through it: a probe constant, a probe result, and a caller's `schema=`.
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _load_probe_module() -> Any:
    """Load `01_probe.py` from beside this file and return it as a module object.

    Executing the probe's module body is cheap and has no side effects worth naming: it is
    imports, constants and function definitions, and its `main()` is behind the usual
    `__name__ == "__main__"` guard, which a `spec_from_file_location` load does not satisfy.
    It costs no query and touches no network.

    The module is registered in `sys.modules` under its own name so a second call returns the
    same object rather than a second copy of the same constants, and so `dataclasses`-style
    machinery inside it can find itself.  The name is deliberately not `01_probe`: nothing may
    be able to reach this module by a name that looks like a normal import, because a name that
    looks importable invites someone to type `import 01_probe` and be told something unhelpful.
    """
    if _PROBE_MODULE_NAME in sys.modules:
        return sys.modules[_PROBE_MODULE_NAME]
    # `_HERE` first, and then beside the `cs_spine` this process actually resolved.  The second
    # is not belt and braces: `_HERE` falls back to the cwd when there is no `__file__` (a
    # pasted cell), and the cwd on a Workbench VM is wherever the human last cd'd to.  Whatever
    # directory `cs_spine` came from is by definition this repo's `pipeline/`, and taking the
    # probe from anywhere else is the same mistake as importing a second disclosure module.
    searched: list[Path] = [Path(_HERE)]
    cs_spine_file = getattr(cs_spine, "__file__", None)
    if cs_spine_file:
        beside = Path(cs_spine_file).resolve().parent
        if beside not in searched:
            searched.append(beside)
    for directory in searched:
        path = directory / _PROBE_FILENAME
        if path.is_file():
            break
    else:
        raise PreGateError(
            f"{_PROBE_FILENAME} was not found in {[str(d) for d in searched]}. It owns the "
            f"prespecified emergency-department and inpatient visit concept ids, and this "
            f"module has no default for them and never will: CLAUDE.md stop condition 1 halts "
            f"the build when they are assumed rather than enumerated against the CDR's own "
            f"distribution. Run this file from the repo, not from a copy."
        )
    spec = importlib.util.spec_from_file_location(_PROBE_MODULE_NAME, path)
    if spec is None or spec.loader is None:            # pragma: no cover - a broken checkout
        raise PreGateError(f"{path} could not be loaded as a module.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_PROBE_MODULE_NAME] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        del sys.modules[_PROBE_MODULE_NAME]
        raise
    return module


def _borrowed_concept_ids(module: Any, name: str) -> tuple[int, ...]:
    """One prespecified id tuple from the probe, shape-checked before anything interpolates it.

    A missing or empty tuple here would otherwise become an empty SQL in-list, which matches
    nothing and returns a table of zeros that reads exactly like a real finding.  So the shape
    is a stop condition at import, not a surprise at the stop.
    """
    values = getattr(module, name, None)
    if not isinstance(values, (tuple, list)) or not values:
        raise PreGateError(
            f"{_PROBE_FILENAME} does not define {name} as a non-empty sequence. This module "
            f"reads the visit concept ids from there rather than retyping them, and an empty "
            f"one would build an in-list that matches nothing."
        )
    if any(isinstance(v, bool) or not isinstance(v, int) for v in values):
        raise PreGateError(
            f"{_PROBE_FILENAME}'s {name} holds a value that is not a whole number. Visit "
            f"concept ids are integers enumerated against the CDR's own distribution, never "
            f"names."
        )
    return tuple(int(v) for v in values)


def _borrowed_int(module: Any, name: str) -> int:
    """One prespecified whole-number threshold from the probe, shape-checked at import.

    The same guard `_borrowed_concept_ids` applies to the visit ids, for the same reason: a
    threshold that arrives as None or as a string would be interpolated into a comparison and
    would return a table of zeros that reads exactly like a real finding.
    """
    value = getattr(module, name, None)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PreGateError(
            f"{_PROBE_FILENAME} does not define {name} as a positive whole number, and this "
            f"module reads it from there rather than retyping it."
        )
    return int(value)


def _borrowed_name(module: Any, name: str) -> str:
    """One prespecified table or column name from the probe, checked to be a bare identifier.

    The check is not politeness.  A borrowed name is interpolated straight into SQL, and this
    is the same restriction `_validated_schema` puts on a name arriving from a caller: the
    emitted string is provably table and column names and nothing else.
    """
    value = getattr(module, name, None)
    if not isinstance(value, str) or not _IDENTIFIER.match(value):
        raise PreGateError(
            f"{_PROBE_FILENAME}'s {name} is not a bare SQL identifier. This module interpolates "
            f"it into a query and it may name a table or a column, nothing else."
        )
    return value


def _borrowed_fitbit_tables(module: Any) -> tuple[str, str]:
    """The activity and heart-rate table names, taken from the probe's required-tables tuple.

    The probe checks INFORMATION_SCHEMA for exactly these two names and STOPS THE BUILD when
    either is missing; this module then interpolates them into the query that reads them.  One
    list has to serve both, or the probe verifies one pair of tables and the pre-gate scans
    another.

    Matched on CONTENT rather than position, so a reordering over there cannot silently swap
    the activity table for the heart-rate table here.
    """
    names = getattr(module, "FITBIT_TABLES_REQUIRED", None)
    if not isinstance(names, (tuple, list)) or len(names) != 2:
        raise PreGateError(
            f"{_PROBE_FILENAME} does not define FITBIT_TABLES_REQUIRED as a pair of names. This "
            f"module reads the activity and heart rate table names from there rather than "
            f"retyping them, and it needs exactly the two the plan requires."
        )
    bad = [n for n in names if not isinstance(n, str) or not _IDENTIFIER.match(n)]
    if bad:
        raise PreGateError(
            f"{_PROBE_FILENAME}'s FITBIT_TABLES_REQUIRED holds {bad}, which is not a bare SQL "
            f"identifier. These names are interpolated into a query."
        )
    activity = [n for n in names if "activity" in n]
    heart = [n for n in names if "heart" in n]
    if len(activity) != 1 or len(heart) != 1:
        raise PreGateError(
            f"{_PROBE_FILENAME}'s FITBIT_TABLES_REQUIRED is {list(names)}, and this module "
            f"cannot tell which is the activity table and which the heart rate table. It reads "
            f"a daily step total from the first and per-zone minutes from the second, so it "
            f"may not guess."
        )
    return activity[0], heart[0]


_PROBE = _load_probe_module()

# PRESPECIFIED IN 01_probe.py, VERIFIED BY IT AGAINST THIS CDR, IMPORTED HERE.  Not retyped:
# one edit in one place moves both modules, and a divergence is impossible rather than merely
# unlikely.
ED_VISIT_CONCEPT_IDS: tuple[int, ...] = _borrowed_concept_ids(_PROBE, "ED_VISIT_CONCEPT_IDS")
INPATIENT_VISIT_CONCEPT_IDS: tuple[int, ...] = _borrowed_concept_ids(
    _PROBE, "INPATIENT_VISIT_CONCEPT_IDS")

# The pre-gate counts ONE outcome, "an emergency-department or inpatient encounter", so what it
# needs is the union.  262 is deliberately a member of BOTH borrowed sets and appears once here:
# it is an emergency department presentation that became an admission, and plan section 4.1
# collapses exactly that pair into ONE event.  Counting it twice would inflate the acute-care
# ceiling that the tier decision is read off, so the union is taken as a set, sorted for a
# byte-stable in-list.
ED_AND_INPATIENT_VISIT_CONCEPT_IDS: tuple[int, ...] = tuple(
    sorted(set(ED_VISIT_CONCEPT_IDS) | set(INPATIENT_VISIT_CONCEPT_IDS)))

# The concept CTE's name, pinned by the concept-set decision.  It is a module-private constant
# over there, so it is restated here and then CHECKED against the emitted text, which is a real
# guard rather than a copy: a rename in that module fails this import instead of producing a
# query that references a CTE nobody declared.
SOURCE_CTE_NAME = "spine_src"
if not cs_spine.source_concept_cte().startswith("WITH " + SOURCE_CTE_NAME + " AS ("):
    raise PreGateError(
        f"the concept set's CTE is no longer named {SOURCE_CTE_NAME!r}, and every query in this "
        f"module joins against that name."
    )

_REQUIRED_REGIONS = ("cervical", "thoracic", "lumbar", "unspecified")
if tuple(cs_spine.REGIONS) != _REQUIRED_REGIONS:
    raise PreGateError(
        f"the concept set's region vocabulary is {tuple(cs_spine.REGIONS)}, and this module's "
        f"stratification is written against {_REQUIRED_REGIONS}. One of the two moved; "
        f"reconcile them before running anything."
    )
_REQUIRED_CLASSES = ("fusion", "decompression")
if tuple(cs_spine.PROCEDURE_CLASSES) != _REQUIRED_CLASSES:
    raise PreGateError(
        f"the concept set's class vocabulary is {tuple(cs_spine.PROCEDURE_CLASSES)}, and this "
        f"module reads {_REQUIRED_CLASSES}."
    )

# WHAT THE ADD-ONS ACTUALLY CARRY.  The fusion decision below rests on two facts about the
# locked set, so both are measured here rather than asserted in a comment that ages badly.
#
#   Every add-on is tagged 'unspecified' in BOTH region columns.  This is what lets the REGION
#   half keep its add-on filter: dropping it there would change nothing, because an add-on
#   never carries a region that could override a cervical, lumbar or thoracic assignment.
#
#   Most add-ons carry the FUSION class.  This is what makes dropping the filter in the FUSION
#   half a real change rather than a rounding error, and it is the evidence behind reading an
#   add-on arthrodesis code as evidence that the fusion happened.
#
# If a later concept-set edit gives an add-on a region, the region half's filter stops being
# redundant and starts being load-bearing, and this import fails so somebody looks at it.
_ADD_ON_ROWS = tuple(row for row in cs_spine.registry_rows() if row["is_add_on"])
_regioned_add_ons = sorted(
    row["code"] for row in _ADD_ON_ROWS
    if row["region_primary"] != "unspecified" or row["region_mirrored"] != "unspecified")
if _regioned_add_ons:
    raise PreGateError(
        f"add-on code(s) {_regioned_add_ons} now carry an anatomic region. The region flags in "
        f"this module filter add-ons out on the grounds that the filter is redundant today, and "
        f"it has just stopped being redundant. Read `_region_flag` and decide deliberately "
        f"before running anything."
    )
ADD_ON_FUSION_CODES: int = sum(1 for row in _ADD_ON_ROWS
                               if row["procedure_class"] == "fusion")
if ADD_ON_FUSION_CODES == 0:
    raise PreGateError(
        "no add-on in the locked set carries the fusion class any more. The fusion flag reads "
        "add-on rows precisely because most of them do; if none does, the reading that was "
        "chosen has lost the evidence it was chosen on. Reconcile before running anything."
    )

# The pre-gate region strata.  FIVE, not the study's two, and that is the point of the table:
# every stratum that a later rung will remove is shown here on its own row rather than folded
# into a neighbour, so the reader can subtract the rows the ladder will delete instead of
# guessing which of them are inside the headline number.  Left value is the SQL literal, right
# value is the only string that reaches a human.
REGION_STRATA: tuple[tuple[str, str], ...] = (
    ("cervical", "Cervical"),
    ("lumbar", "Lumbar"),
    ("cervical and lumbar", "Cervical and lumbar"),
    ("thoracic only", "Thoracic only"),
    ("unspecified only", "Region unspecified only"),
)
PROCEDURE_GROUPS: tuple[tuple[str, str], ...] = (
    ("fusion", "Fusion"),
    ("decompression", "Decompression"),
)
ALL_GROUPS_LABEL = "All groups"
ALL_REGIONS_LABEL = "All regions"

REGION_LABELS: tuple[str, ...] = tuple(display for _, display in REGION_STRATA)
GROUP_LABELS: tuple[str, ...] = tuple(display for _, display in PROCEDURE_GROUPS)
WIDE_COLUMNS: tuple[str, ...] = GROUP_LABELS + (ALL_GROUPS_LABEL,)
WIDE_ROWS: tuple[str, ...] = REGION_LABELS + (ALL_REGIONS_LABEL,)

# The four nested stages, in the plan's order.  Left value is the returned column, right value
# is the display label.
STAGES: tuple[tuple[str, str], ...] = (
    ("n_episodes", "Spine surgical episodes"),
    ("n_wearable_linked", "With any Fitbit activity data"),
    ("n_baseline_adequate", "With adequate baseline wear"),
    ("n_acute_care", "With acute care, days 1 to 90"),
)
STAGE_COLUMNS: tuple[str, ...] = tuple(column for column, _ in STAGES)

# The four queries, named once.  The name is the cost-log entry, the cost-plan row and the
# refusal message, so there is one vocabulary rather than three.
QUERY_KEYS: tuple[str, ...] = (
    "concept set resolution",
    "cervical decompression gap",
    "cervical fusion gap",
    "pre-gate upper-bound counts",
)


# ======================================================================================
# (2) Cost policy.
#
# TWO INDEPENDENT GUARDS, and they protect different things.
#
#   PLANNED_MAX_GB is per query.  Each cap is sized against the scan that query actually
#   makes, and it is passed to q_guarded as BOTH the refusal threshold and the job's
#   maximum_bytes_billed, so a stale statistic or a partition pruned differently at run time
#   fails the job instead of billing past the cap.  The caps SUM to more than the budget on
#   purpose: a cap is runaway protection for one query, not an allowance.
#
#   PREGATE_BUDGET_GB is the aggregate.  All four queries are priced by dry run before any of
#   them executes, and the module refuses to execute anything if the MEASURED total exceeds it.
#   This is the guard that implements "about $0.15, and a query that would blow it must fail
#   rather than bill", because four queries each inside its own cap can still add up to a bill
#   nobody approved.
# ======================================================================================

# Display only.  Enforcement is in bytes, everywhere.  Mirrors the config notebook's constant;
# nothing in this project computes a decision from a price.
USD_PER_TIB: float = 6.25
BYTES_PER_GIB: int = 1024 ** 3

# 24 GiB is about $0.15 at the price above, which is the whole budget the locked plan gives
# this step.  Raising it is a deliberate act with the priced total already on the screen: pass
# `budget_gb=` to run_pregate, having read the number the cost plan printed.
PREGATE_BUDGET_GB: float = 24.0

PLANNED_MAX_GB: Mapping[str, float] = MappingProxyType({
    # `{CDR}.concept` is order ten million rows and this reads four columns of it, one of them
    # the name string.  Two gibibytes is generous for that and tight enough to catch a join
    # that has accidentally become a cross product.
    "concept set resolution": 2.0,
    # `{CDR}.procedure_occurrence` on two INT64 columns (the person and the source concept),
    # plus one pass over `concept` for the candidate arm.  Sized against an order
    # five-hundred-million-row procedure table: two columns at eight bytes is about eight
    # gibibytes, and twelve leaves room for a larger release without leaving room for a
    # different query.
    "cervical decompression gap": 12.0,
    # The same shape, one extra flag, same sizing.
    "cervical fusion gap": 12.0,
    # `procedure_occurrence` on three columns (the date is the third), `activity_summary` on
    # one, `heart_rate_summary` on three, `visit_occurrence` on three.  The procedure table
    # dominates; the wear table is small because zone-summary rows are roughly four per
    # person-day rather than 1,440.
    "pre-gate upper-bound counts": 18.0,
})


# ======================================================================================
# (3) Definitions, all of them read out of the locked plan rather than chosen here.
# ======================================================================================

# ANALYSIS-PLAN.md 2.1, primary wear definition.  IMPORTED from 01_probe.py, which owns it as
# `VALID_WEAR_MINUTES` and reports every wear band against it, rather than retyped here.  The
# two files held the same 600 twice, and two copies of a threshold are a divergence waiting for
# the next plan amendment: the probe would go on reporting the share of person-days clearing one
# number while the pre-gate counted valid wear days against another.  The local name is kept
# because it reads correctly where it is used; only the VALUE is borrowed.
VALID_WEAR_DAY_MINUTES: int = _borrowed_int(_PROBE, "VALID_WEAR_MINUTES")
# ANALYSIS-PLAN.md 2.2, the preoperative baseline window and its adequacy rule.
BASELINE_WINDOW_FIRST_DAY_BEFORE: int = 30
BASELINE_WINDOW_LAST_DAY_BEFORE: int = 8
BASELINE_MIN_VALID_DAYS: int = 7
# "spanning at least 14 calendar days" (plan 2.2; rung 12 reads "a span under 14 calendar
# days").  Read INCLUSIVELY here: the closed interval from the first valid day to the last must
# contain at least fourteen calendar dates, so the SQL is DATE_DIFF(last, first) + 1 >= 14.
# The exclusive reading (DATE_DIFF >= 14) is one day stricter and the plan does not settle
# which is meant.  The inclusive reading is chosen BECAUSE it is the more permissive of the
# two, and every number this module prints is an upper bound.  03_cohort.py must adopt the
# same reading or the pre-gate ceiling and rung 12 will disagree by a whole day of eligibility.
BASELINE_MIN_SPAN_CALENDAR_DAYS: int = 14
# Locked plan, Phase 2 item 4: postoperative days 1 to 90, anchored on the operation date.
ACUTE_CARE_FIRST_DAY: int = 1
ACUTE_CARE_LAST_DAY: int = 90

# ANALYSIS-PLAN.md 1.2, the protocol's tier table.  These are EVENT thresholds and they are not
# the disclosure floor.  TIER_3_MIN_EVENTS coincides with `disclosure.MIN_CELL` at 20 and plan
# section 1.3 names that coincidence rather than tripping over it: the two are unrelated in
# origin and identical in value, so they are kept as two constants and never aliased.  Aliasing
# them would make a future edit to the disclosure floor silently move a protocol threshold.
TIER_1_MIN_EVENTS: int = 100
TIER_2_MIN_EVENTS: int = 50
TIER_3_MIN_EVENTS: int = 20
# Locked plan, Phase 2: "If the acute-care count is already under 50 before any exclusion, Aim
# A is dead and we skip building the matched-sampling branch entirely."  That is the tier 2
# boundary, named separately because it is a different decision made on the same number.
AIM_A_MIN_EVENTS: int = TIER_2_MIN_EVENTS

TIER_TABLE: tuple[tuple[int, str, str], ...] = (
    (1, "100 or more usable events",
     "Full detection model with internal validation. Performance may be reported"),
    (2, "50 to 99 usable events",
     "Step-first model, no broad feature selection. Exploratory in every caption"),
    (3, "20 to 49 usable events",
     "Event-centered association and visualization only. No prediction claim"),
    (4, "Fewer than 20 usable events",
     "No early-warning modeling. Feasibility statement only, count suppressed"),
)

# ANALYSIS-PLAN.md 2.7.  Exact rationals, not floats, so "5% or less" and "10% or less" mean
# exactly that at the boundary: Fraction(1, 20) > Fraction(5, 100) is False, where the same
# comparison on binary floats depends on which side of 0.05 the nearest double falls.
FUSION_GAP_THRESHOLD: Fraction = Fraction(5, 100)
DECOMPRESSION_GAP_THRESHOLD: Fraction = Fraction(10, 100)

# The one row of each split builder that carries the decision, spelled as the builders emit it.
# Both builders sort by this column, so it arrives FIRST of the four rather than fourth, and
# nothing here reads it by position.
CANDIDATE_ONLY_PATH = "candidate CPT only, invisible to the locked set"
LOCKED_PATH_PREFIX = "locked set: "

# The two rules this module DOES apply, because the concept set hands both to whatever builds
# an episode and both change a count.  They are NOT the same rule and they do not point the same
# way: the first is an EXCLUSION and decides whether an episode exists at all, the second is a
# LABEL and decides which arm an episode that already exists belongs to.  Stated in the report,
# not only here, because the reader is comparing these numbers against a later ladder that
# applies far more.
APPLIED_HERE: tuple[str, ...] = (
    "A same-day bundle is an operation only when it carries at least one code that is not an "
    "add-on or an instrumentation code. A bundle of instrumentation alone is not an operation "
    "and is not counted.",
    "Fusion status is then read from every qualifying code on that date, add-on and "
    "instrumentation codes included. An episode whose only arthrodesis evidence is an add-on "
    "code is counted as a fusion, because a missing primary arthrodesis code is a "
    "coding-capture gap rather than a clinical fact and the add-on is the only evidence the "
    "fusion happened. This chooses the arm and nothing else. It never makes an operation out "
    "of a bundle the rule above has already rejected.",
)

# Everything the ladder will apply and this step will not.  Each line lowers a count later, so
# each is named in the output rather than in a comment: the reader is holding these numbers up
# against the Phase 3 ladder, and the difference between the two is mostly this list.
NOT_APPLIED_HERE: tuple[str, ...] = (
    "Trauma, malignancy and infection screening.",
    "The elective-admission screen, and the prior-operation-within-90-days screen.",
    "Episodes at both cervical and lumbar regions on one date. Retained, and shown on their "
    "own row so they can be subtracted rather than guessed at.",
    "Episodes whose only regional evidence carries no anatomic level. Retained, and shown on "
    "their own row as Region unspecified only, never folded into a neighbouring region.",
    "Thoracic-only episodes, which are outside the target population. Retained, and shown on "
    "their own row.",
    "One eligible episode per participant. A participant with two qualifying procedure dates "
    "contributes two episodes here.",
    "The discharge anchor. Acute-care days are counted from the operation date, not from the "
    "discharge date, so the window is wider here than the study's own and the count is higher.",
    "Truncation by death or by repeat operation, and the requirement of a computable "
    "post-discharge day 1 to 35 window.",
)


# ======================================================================================
# (4) Table and column names that are RUNTIME PROBES, not assumptions.
#
# The exact per-zone minute column of `heart_rate_summary` is named as a probe by the project
# brief and by plan 2.1, and the Fitbit tables' presence in a Controlled Tier CDR is stop
# condition 1.  So every physical name this module puts in a query is a parameter with a
# documented default, and 01_probe.py's finding is passed in rather than pasted here.  Keys are
# spaced words rather than identifiers so that printing one cannot leak a snake-case token into
# a human-visible string.
# ======================================================================================

# The two Fitbit tables the plan requires, IMPORTED from 01_probe.py's FITBIT_TABLES_REQUIRED.
# The probe treats the absence of either as stop condition 1 and checks INFORMATION_SCHEMA for
# exactly these names; this module then scans them.  Retyping them would let the probe verify
# one pair and the pre-gate read another.
FITBIT_ACTIVITY_TABLE, FITBIT_HEART_RATE_TABLE = _borrowed_fitbit_tables(_PROBE)

# The per-zone minute column, IMPORTED, and never typed here in either spelling.  This file used
# to declare `min_in_zone` while 01_probe.py and build_all.sql both used `minute_in_zone`, and
# the odd one out was the one interpolated into a query that EXECUTES under an 18 GiB cap, while
# the two files that agreed never ran.  A column-name mismatch discovered there costs a Workbench
# session.  The constant is a FIRST GUESS and not an assumption: the probe's own resolver chain
# accepts both spellings against this CDR's INFORMATION_SCHEMA (rung 1 is the exact name, rung 3
# is "begins with min and contains zone"), and a run that resolves something else hands THAT
# name back through `schema=`.
HR_ZONE_MINUTE_COLUMN: str = _borrowed_name(_PROBE, "HR_ZONE_MINUTE_COLUMN")

DEFAULT_SCHEMA: Mapping[str, str] = MappingProxyType({
    "procedure table": "procedure_occurrence",
    "procedure date column": "procedure_date",
    "procedure source concept column": "procedure_source_concept_id",
    "activity table": FITBIT_ACTIVITY_TABLE,
    "heart rate table": FITBIT_HEART_RATE_TABLE,
    "heart rate date column": "date",
    "heart rate zone minutes column": HR_ZONE_MINUTE_COLUMN,
    "visit table": "visit_occurrence",
    "visit start date column": "visit_start_date",
    "visit concept column": "visit_concept_id",
})


def _validated_schema(schema: Mapping[str, str]) -> Mapping[str, str]:
    """Return the schema names, refusing anything that is not a bare SQL identifier.

    A probe result is data arriving from outside this file, and it is interpolated straight
    into SQL.  Restricting it to `[A-Za-z_][A-Za-z0-9_]*` is not defensive politeness: it is
    what makes the emitted string provably free of anything but table and column names, which
    is the property the self-test asserts about every query this module builds.
    """
    missing = [k for k in DEFAULT_SCHEMA if k not in schema]
    if missing:
        raise PreGateError(f"the schema is missing name(s) this module needs: {missing}")
    unexpected = [k for k in schema if k not in DEFAULT_SCHEMA]
    if unexpected:
        raise PreGateError(f"the schema carries name(s) no query reads: {unexpected}")
    bad = sorted(k for k, v in schema.items() if not _IDENTIFIER.match(str(v)))
    if bad:
        raise PreGateError(
            f"schema entr(ies) {bad} are not bare SQL identifiers. A probe result is "
            f"interpolated into a query and may name a table or a column, nothing else."
        )
    return MappingProxyType(dict(schema))


def _require_passing_probe(probe_result: Any) -> Mapping[str, Any]:
    """Refuse to run unless 01_probe.py verified this CDR and said so.

    THE MECHANISM HALF OF THE RECONCILIATION.  Importing the prespecified ids removes the
    retyping and the missing default; it does not on its own establish that anyone ever looked
    at what THIS CDR holds.  That is what the probe's verdict is for, and it is why the pre-gate
    takes the probe RESULT rather than a list of numbers: a caller cannot satisfy this gate by
    typing ids in, only by having run the probe and having it pass.

    The three refusals are separate because the fixes are different.  No result at all means the
    probe has not been run.  A result with no verdict in it means something other than
    `run_probe()` produced it.  A false verdict means the probe ran and FOUND SOMETHING, and the
    named probes carry their own four-sentence diagnosis, which is the thing to read.
    """
    if probe_result is None:
        raise PreGateError(
            "no probe result was given, so nothing has verified that this CDR holds what the "
            "prespecified visit concept ids assume. CLAUDE.md stop condition 1 halts the build "
            "when they are assumed rather than enumerated against the CDR's actual "
            "distribution. Run 01_probe.py first and pass what run_probe() returned."
        )
    if not isinstance(probe_result, Mapping) or "probe ok" not in probe_result:
        raise PreGateError(
            "the probe result is not the mapping run_probe() returns: it carries no verdict. "
            "Pass the object run_probe() returned, or the parsed JSON block 01_probe.py prints "
            "for the session log, and nothing assembled by hand."
        )
    if not probe_result["probe ok"]:
        halting = list(probe_result.get("halting") or [])
        named = ", ".join(str(k) for k in halting) if halting else "at least one probe"
        raise PreGateError(
            f"the runtime probes did not all pass: {named}. A probe failure changes the plan; "
            f"it does not get worked around, and it is not made truer by spending fifteen cents "
            f"on the counts underneath it. Read the four-sentence diagnosis 01_probe.py printed "
            f"for each, take it to the Phase 2 hard stop, and re-run the probe after."
        )
    return probe_result


def _int_list(values: Sequence[Any]) -> str:
    """Render integer concept ids as a SQL in-list body, sorted and de-duplicated.

    Sorted and de-duplicated so the emitted SQL is byte-stable across two calls with the same
    set in a different order, which is what makes a diff of two builds mean something.  Every
    value must be a whole number: an accidental string here would be quoted by the caller's
    formatting and silently match nothing.
    """
    if values is None:
        raise PreGateError("no visit concept ids were given")
    cleaned: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int,)):
            try:
                as_int = int(str(value).strip())
            except (TypeError, ValueError):
                raise PreGateError(
                    "visit concept ids must be whole numbers enumerated against the CDR's own "
                    "visit distribution by the runtime probe, never names or strings"
                ) from None
        else:
            as_int = int(value)
        cleaned.append(as_int)
    if not cleaned:
        raise PreGateError(
            "the emergency-department and inpatient visit concept ids are empty. CLAUDE.md "
            "stop condition 1 halts the build when these are assumed rather than enumerated "
            "against the CDR's actual distribution, so this module has no default for them. "
            "Run the visit-concept enumeration probe and pass its result in."
        )
    return ",".join(str(v) for v in sorted(set(cleaned)))


# ======================================================================================
# (5) SQL.  Text only, `{CDR}` is the only placeholder, and the caller dry-runs and caps.
#
# Built from cs_spine, never from a retyped code list.  `source_concept_cte()` returns text
# ending in ")\n", so the episode layer is appended as ", episodes AS (...)".  The join key is
# `procedure_source_concept_id`, which is how the locked phenotype counted its 9,720.
# ======================================================================================


def _region_flag(region: str, alias: str) -> str:
    """A LOGICAL_OR over non-add-on rows only, because an add-on cannot carry a region.

    Every add-on in the locked set is tagged 'unspecified' in BOTH region columns, which is
    asserted at import above rather than trusted here, so this filter changes nothing today for
    cervical, thoracic or lumbar: an add-on cannot override a cervical, lumbar or thoracic
    assignment because it never carries one to override it with.  It is written anyway because
    it states the protocol rule the stratification rests on, and because it is the line that
    still holds if a later edit ever gives an add-on code a region.

    THE REGION HALF THEREFORE DOES NOT FOLLOW THE FUSION HALF, and the asymmetry is not an
    oversight.  `_fusion_flag` drops its add-on filter because most add-ons carry the fusion
    class and dropping it moves episodes between arms; this one keeps its filter because every
    add-on is 'unspecified' and dropping it would move nothing at all.  Two different facts
    about the same sixteen codes, both measured at import, giving two different answers.
    """
    return ("    LOGICAL_OR(s.region = '" + region + "' AND NOT s.is_add_on) AS " + alias)


def _fusion_flag(alias: str = "has_fusion") -> str:
    """A LOGICAL_OR over ALL qualifying rows, add-ons included.  The ARM predicate.

    `LOGICAL_OR(s.procedure_class = 'fusion')`, with no add-on filter, which is exactly what
    `build_all.sql` computes for the DAG's own episode table.  The two files read fusion status
    the same way because they now emit the same predicate.

    WHY THE ADD-ON FILTER IS ABSENT.  Fourteen of the sixteen add-on and instrumentation codes
    in the locked set carry `procedure_class = 'fusion'` (`ADD_ON_FUSION_CODES`, counted at
    import), and instrumentation without arthrodesis is essentially never performed in
    degenerative spine surgery.  The filtered and unfiltered readings therefore differ ONLY on
    an episode whose primary arthrodesis code is absent from the record.  That absence is a
    CODING-CAPTURE GAP rather than a clinical fact, and on such an episode the add-on is the
    only evidence the fusion happened, so filtering it out puts a fusion patient on the
    decompression arm.

    THIS IS NOT THE OPERATION-EXISTS PREDICATE, and the two must never be merged.  That one is
    `_operation_exists_having` and it is unchanged: an add-on still cannot establish that an
    operation happened.  Two functions rather than one expression so the distinction has
    somewhere to live.  This one picks an ARM for an episode that already exists; that one
    decides WHETHER the episode exists at all, and it runs first.
    """
    return ("    LOGICAL_OR(s.procedure_class = 'fusion') AS " + alias)


def _operation_exists_having() -> str:
    """The EXCLUSION predicate: a bundle is an operation only if a primary code is on it.

    `HAVING LOGICAL_OR(NOT s.is_add_on)`.  Sixteen of the thirty CPT-4 codes in the locked set
    are add-on or instrumentation codes, so a bundle carrying nothing else is not a rare case,
    and admitting one would inflate the ceiling with episodes no rung would ever have counted.

    UNCHANGED BY THE FUSION DECISION, and deliberately its own function so it cannot be folded
    back into `_fusion_flag`.  Reading fusion status from add-on rows chooses which ARM an
    episode belongs to and says nothing whatever about whether AN OPERATION HAPPENED.  This
    line is still the only thing in the module that answers that question, and it still
    requires at least one `is_add_on = FALSE` record.
    """
    # Repeated rather than referenced by alias: BigQuery would accept the alias, and a query
    # that only works on one engine is a query that gets edited on another.
    return "  HAVING LOGICAL_OR(NOT s.is_add_on)\n"


def episodes_cte_sql(*, mirror_junctions: bool = False) -> str:
    """The concept CTE plus a same-day episode collapse and its region and fusion labels.

    This is a COLLAPSE, not the cohort.  One row per participant and procedure date, with no
    exclusion applied beyond the two the concept set requires, so the count it feeds is a
    ceiling.  It is deliberately not materialized: Phase 3 owns the DAG, and building any part
    of it here would spend the budget the stop exists to protect.

    Two obligations `cs_spine` hands to whatever builds an episode, and both are here because
    both change a number:

      (1) `HAVING LOGICAL_OR(NOT s.is_add_on)`, emitted by `_operation_exists_having`.  A
          same-day bundle of instrumentation alone is not an operation.  Sixteen of the thirty
          CPT-4 codes are add-on or instrumentation, so this is not a rare case and dropping it
          would inflate the ceiling with bundles that no rung would ever have admitted.

      (2) The region label treats 'unspecified' as evidence of nothing rather than as a region.
          An episode reaches the 'unspecified only' stratum exactly when it has a code that can
          define an operation and no code that carries an anatomic level, which is what
          protocol exclusion 3 and rung 7 act on.  It is RETAINED here and shown on its own
          row: this is a pre-gate ceiling, so the exclusion is reported rather than applied,
          and a reader who wants the post-rung number subtracts the row.

    Fusion status does NOT take rule (1)'s filter, and the asymmetry is the decision rather than
    an oversight.  `_fusion_flag` emits `LOGICAL_OR(s.procedure_class = 'fusion')` over EVERY
    qualifying record on the date, add-ons included, which is what `build_all.sql` has always
    computed for the DAG's own episode table; the two files now read fusion status the same way.
    An interbody device code beside a decompression primary DOES make the episode a fusion,
    because fourteen of the sixteen add-ons carry the fusion class, because instrumentation
    without arthrodesis is essentially never performed in degenerative spine surgery, and
    because the only episodes on which the two readings differ are those whose primary
    arthrodesis code never reached the record.  That is a coding-capture gap, not a clinical
    fact, and there the add-on is the only evidence the fusion happened.

    RULE (1) IS UNTOUCHED BY THAT.  An add-on still cannot establish that an OPERATION HAPPENED,
    a bundle of instrumentation alone is still not counted at all, and the arm decision only
    ever runs on an episode rule (1) has already admitted.  The two predicates live in two
    separate functions so a later reader cannot merge them.  Plan section 2.4 fixes the other
    direction, that fusion with decompression is fusion, and LOGICAL_OR gives that for free.
    """
    schema = DEFAULT_SCHEMA
    return (
        cs_spine.source_concept_cte(mirror_junctions=mirror_junctions)
        + ", episodes AS (\n"
          "  SELECT\n"
          "    p.person_id,\n"
          "    p." + schema["procedure date column"] + " AS index_date,\n"
        + _region_flag("cervical", "has_cervical") + ",\n"
        + _region_flag("thoracic", "has_thoracic") + ",\n"
        + _region_flag("lumbar", "has_lumbar") + ",\n"
        + _fusion_flag("has_fusion") + "\n"
        + "  FROM `{CDR}." + schema["procedure table"] + "` p\n"
          "  JOIN " + SOURCE_CTE_NAME + " s\n"
          "    ON s.concept_id = p." + schema["procedure source concept column"] + "\n"
          "  WHERE p." + schema["procedure date column"] + " IS NOT NULL\n"
          "  GROUP BY p.person_id, p." + schema["procedure date column"] + "\n"
        + _operation_exists_having()
        + ")\n"
          ", labelled AS (\n"
          "  SELECT\n"
          "    person_id,\n"
          "    index_date,\n"
          "    CASE\n"
          # Order matters and is the junction rule already applied inside the concept CTE:
          # a cervicothoracic bundle arrives tagged cervical, so it lands in 'cervical' and
          # never in 'thoracic only'.  'thoracic only' means what it says.
          "      WHEN has_cervical AND has_lumbar THEN 'cervical and lumbar'\n"
          "      WHEN has_cervical               THEN 'cervical'\n"
          "      WHEN has_lumbar                 THEN 'lumbar'\n"
          "      WHEN has_thoracic               THEN 'thoracic only'\n"
          "      ELSE                                 'unspecified only'\n"
          "    END AS region_stratum,\n"
          "    IF(has_fusion, 'fusion', 'decompression') AS procedure_group\n"
          "  FROM episodes\n"
          ")\n"
    )


def pregate_counts_sql(
    *,
    visit_concept_ids: Sequence[Any] = ED_AND_INPATIENT_VISIT_CONCEPT_IDS,
    mirror_junctions: bool = False,
    schema: Mapping[str, str] = DEFAULT_SCHEMA,
) -> str:
    """The four nested upper-bound counts, stratified by region and fusion status.

    `visit_concept_ids` defaults to the union imported from 01_probe.py.  That is not a silent
    default: it is the PRESPECIFIED value, defined in one place and read from there, and the
    verification that it covers this CDR is enforced one level up by `run_pregate`, which will
    not call this builder at all without a passing probe.  The parameter stays so that a caller
    can build the text for an audit or a diff against an explicit list, and so `_int_list` can
    be shown refusing an empty one.

    One query rather than four, because each of the four counts is a subset of the one above it
    and because `procedure_occurrence` is the cost driver: scanning it once for four counts is
    the difference between this step costing fifteen cents and costing fifty.

    Returns at most ten rows, each a pair of stratum labels and four counts.  Every count is an
    EPISODE count and every one is an upper bound.  The totals are formed in pandas from these
    exact integers and only then rounded, never summed from rounded parts.

    The acute-care arm counts a visit whose start date is STRICTLY AFTER the index date, so the
    index admission itself is never counted as its own outcome.  A same-stay transfer recorded
    as a fresh visit on postoperative day 1 or later still is, which overcounts, which is the
    correct direction for a ceiling and is stated in the report rather than left to be found.
    """
    s = _validated_schema(schema)
    ids = _int_list(visit_concept_ids)
    return (
        episodes_cte_sql(mirror_junctions=mirror_junctions)
        + ", wearable_persons AS (\n"
          # "Any Fitbit activity data", the loosest possible reading and therefore the right one
          # for a ceiling: any activity row at any date, with no window and no adequacy rule.
          # It matches rung 11's own wording, "No Fitbit activity record linked to the
          # participant", so the ceiling and the rung are asking the same question.
          "  SELECT DISTINCT person_id FROM `{CDR}." + s["activity table"] + "`\n"
          ")\n"
          ", wear_days AS (\n"
          # Plan 2.1: a valid wear day is at least `VALID_WEAR_DAY_MINUTES` heart-rate
          # minutes, borrowed from the probe rather than restated here, obtained by SUMMING
          # the per-zone minute counts for the person-date.  The zone column name is a runtime
          # probe and arrives through the schema; that the zones partition the day without
          # double-counting a minute is the OTHER half of the probe, and if it fails the plan's
          # prespecified contingency substitutes wear definition S2 for the whole study rather
          # than patching it here.
          "  SELECT\n"
          "    h.person_id,\n"
          "    h." + s["heart rate date column"] + " AS wear_date\n"
          "  FROM `{CDR}." + s["heart rate table"] + "` h\n"
          "  GROUP BY h.person_id, h." + s["heart rate date column"] + "\n"
          "  HAVING SUM(h." + s["heart rate zone minutes column"] + ") >= "
        + str(VALID_WEAR_DAY_MINUTES) + "\n"
          ")\n"
          ", baseline AS (\n"
          "  SELECT\n"
          "    l.person_id,\n"
          "    l.index_date,\n"
          "    COUNT(*) AS n_valid_days,\n"
          # Inclusive span: the closed interval from the first valid day to the last contains
          # this many calendar dates.  See BASELINE_MIN_SPAN_CALENDAR_DAYS for why the
          # inclusive reading is the one a ceiling takes.
          "    DATE_DIFF(MAX(w.wear_date), MIN(w.wear_date), DAY) + 1 AS span_days\n"
          "  FROM labelled l\n"
          "  JOIN wear_days w\n"
          "    ON w.person_id = l.person_id\n"
          "   AND w.wear_date BETWEEN DATE_SUB(l.index_date, INTERVAL "
        + str(BASELINE_WINDOW_FIRST_DAY_BEFORE) + " DAY)\n"
          "                       AND DATE_SUB(l.index_date, INTERVAL "
        + str(BASELINE_WINDOW_LAST_DAY_BEFORE) + " DAY)\n"
          "  GROUP BY l.person_id, l.index_date\n"
          ")\n"
          ", acute_care AS (\n"
          "  SELECT DISTINCT\n"
          "    l.person_id,\n"
          "    l.index_date\n"
          "  FROM labelled l\n"
          "  JOIN `{CDR}." + s["visit table"] + "` v\n"
          "    ON v.person_id = l.person_id\n"
          "   AND v." + s["visit start date column"] + " BETWEEN DATE_ADD(l.index_date, INTERVAL "
        + str(ACUTE_CARE_FIRST_DAY) + " DAY)\n"
          "                       AND DATE_ADD(l.index_date, INTERVAL "
        + str(ACUTE_CARE_LAST_DAY) + " DAY)\n"
          "  WHERE v." + s["visit concept column"] + " IN (" + ids + ")\n"
          ")\n"
          "SELECT\n"
          "  l.region_stratum,\n"
          "  l.procedure_group,\n"
          "  COUNT(*) AS n_episodes,\n"
          "  COUNTIF(w.person_id IS NOT NULL) AS n_wearable_linked,\n"
          # Each stage repeats the stage above it rather than assuming it.  The nesting the
          # plan asks for is "of those", and an episode can have heart-rate wear without an
          # activity row, so the conjunction is written out instead of inferred from a join.
          "  COUNTIF(w.person_id IS NOT NULL\n"
          "          AND b.n_valid_days >= " + str(BASELINE_MIN_VALID_DAYS) + "\n"
          "          AND b.span_days >= " + str(BASELINE_MIN_SPAN_CALENDAR_DAYS) + ")\n"
          "    AS n_baseline_adequate,\n"
          "  COUNTIF(w.person_id IS NOT NULL\n"
          "          AND b.n_valid_days >= " + str(BASELINE_MIN_VALID_DAYS) + "\n"
          "          AND b.span_days >= " + str(BASELINE_MIN_SPAN_CALENDAR_DAYS) + "\n"
          "          AND a.person_id IS NOT NULL)\n"
          "    AS n_acute_care\n"
          "FROM labelled l\n"
          # ON rather than USING: after a USING join the right side's key column cannot be
          # named, and every COUNTIF above tests exactly that column for NULL.
          "LEFT JOIN wearable_persons w ON w.person_id = l.person_id\n"
          "LEFT JOIN baseline b ON b.person_id = l.person_id AND b.index_date = l.index_date\n"
          "LEFT JOIN acute_care a ON a.person_id = l.person_id AND a.index_date = l.index_date\n"
          "GROUP BY l.region_stratum, l.procedure_group\n"
          "ORDER BY l.region_stratum, l.procedure_group\n"
    )


def build_sql(
    *,
    visit_concept_ids: Sequence[Any] = ED_AND_INPATIENT_VISIT_CONCEPT_IDS,
    mirror_junctions: bool = False,
    schema: Mapping[str, str] = DEFAULT_SCHEMA,
) -> dict[str, str]:
    """Every query this step will send, keyed by `QUERY_KEYS`, in execution order.

    `visit_concept_ids` defaults to the tuple imported from 01_probe.py; see
    `pregate_counts_sql` for why that is a prespecification rather than a default.
    """
    return {
        "concept set resolution":
            cs_spine.concept_resolution_sql(mirror_junctions=mirror_junctions),
        "cervical decompression gap":
            cs_spine.cervical_decompression_split_sql(mirror_junctions=mirror_junctions),
        "cervical fusion gap":
            cs_spine.cervical_fusion_split_sql(mirror_junctions=mirror_junctions),
        "pre-gate upper-bound counts":
            pregate_counts_sql(visit_concept_ids=visit_concept_ids,
                               mirror_junctions=mirror_junctions, schema=schema),
    }


# ======================================================================================
# (6) The two concept-set gap measurements, and the response prespecified for each.
#     ANALYSIS-PLAN.md section 2.7, implemented exactly, thresholds included.
# ======================================================================================


def _column(frame: pd.DataFrame, name: str) -> pd.Series:
    if name not in frame.columns:
        raise PreGateError(
            f"the split query returned no {name!r} column, so the gap cannot be measured. The "
            f"concept-set module's builder changed shape; reconcile before proceeding."
        )
    return frame[name]


def _whole(value: Any, what: str) -> int:
    """Coerce a returned count to a whole number, refusing anything that is not one."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise PreGateError(f"{what} came back as something that is not a number") from None
    if number != int(number) or number < 0:
        raise PreGateError(f"{what} came back as something that is not a whole count")
    return int(number)


def _candidate_only_row(frame: pd.DataFrame, what: str) -> pd.Series:
    paths = _column(frame, "evidence_path")
    hits = frame[paths == CANDIDATE_ONLY_PATH]
    if len(hits) > 1:
        raise PreGateError(f"the {what} split returned the candidate-only path more than once")
    if len(hits) == 0:
        # A legitimate outcome: nobody carries a candidate code and nobody is invisible.  The
        # measurement is a zero and the plan has a branch for a measured zero, so this returns
        # an all-zero row rather than raising.
        return pd.Series({"n_persons": 0, "n_also_carrying_candidate_cpt": 0,
                          "n_also_carrying_locked_cervical_decompression": 0})
    return hits.iloc[0]


def gap_measurements(
    decompression_frame: pd.DataFrame,
    fusion_frame: pd.DataFrame,
) -> dict[str, Any]:
    """Extract D, C and M from the two split frames, exactly as plan 2.7 defines them.

    D  persons the locked set classifies as cervical decompression: the three `locked set: ...`
       rows of the DECOMPRESSION builder.
    C  the `n_persons` on the candidate-only row of the DECOMPRESSION builder: persons the
       locked set cannot see at all.
    M  the `n_also_carrying_locked_cervical_decompression` value on the candidate-only row of
       the FUSION builder: persons carrying a candidate cervical fusion code, no locked
       cervical fusion evidence, and locked cervical decompression evidence.  The misfiled
       anterior cervical fusions.

    Rows are selected BY LABEL, never by position.  Both builders sort by `evidence_path`, so
    the candidate-only row arrives first today, and a builder that ever changed its sort would
    silently swap D for C in a positional reading.

    `M <= D` is a structural identity rather than an expectation: every person counted in M
    carries locked cervical decompression evidence, so every one of them is also inside D.  It
    is asserted, because a violation means the two builders disagree about the same locked
    codes and no threshold computed from them would mean anything.
    """
    dec_paths = _column(decompression_frame, "evidence_path")
    locked_rows = decompression_frame[dec_paths.astype(str).str.startswith(LOCKED_PATH_PREFIX)]
    d = sum(_whole(v, "a locked cervical decompression count")
            for v in _column(locked_rows, "n_persons"))
    c = _whole(_candidate_only_row(decompression_frame, "cervical decompression")["n_persons"],
               "the invisible cervical decompression count")
    m = _whole(
        _candidate_only_row(fusion_frame, "cervical fusion")[
            "n_also_carrying_locked_cervical_decompression"],
        "the misfiled cervical fusion count",
    )
    if m > d:
        raise PreGateError(
            "the misfiled cervical fusion count exceeds the locked cervical decompression "
            "count, which is impossible: every misfiled person carries locked cervical "
            "decompression evidence and is therefore already inside that count. The two split "
            "builders disagree about the same locked codes. Do not proceed."
        )
    if c + d == 0:
        raise PreGateError(
            "the cervical decompression split returned nobody at all, neither locked nor "
            "candidate. Either the concept join is broken or the procedure table is not what "
            "this query thinks it is. Do not proceed on a zero that has no explanation."
        )
    return {
        "locked cervical decompression persons": d,
        "invisible cervical decompression persons": c,
        "misfiled cervical fusion persons": m,
    }


def fusion_gap_response(misfiled: int, locked_decompression: int) -> dict[str, Any]:
    """The prespecified response to the fusion gap.  Plan 2.7, fixed before the number existed.

    A misfiled fraction f of one arm attenuates a two-arm contrast by roughly 2f, because each
    misfiled episode is subtracted from one arm's mean and added to the other's.  That is why
    this threshold is half the decompression one: a misfiled case sits on the wrong arm, a
    missing case sits on neither.
    """
    if misfiled == 0:
        return {
            "share": Fraction(0),
            "amend": False,
            "branch": "measured zero",
            "response": ("Record the measured zero in the Methods and the supplement. No "
                         "amendment, and no supplementary row."),
        }
    if locked_decompression == 0:
        # Unreachable while M <= D is asserted above, and kept so that a future edit which
        # relaxes that assertion cannot reach a division by zero instead of a stop condition.
        raise PreGateError("a misfiled count above zero against a locked count of zero")
    share = Fraction(misfiled, locked_decompression)
    if share > FUSION_GAP_THRESHOLD:
        return {
            "share": share,
            "amend": True,
            "branch": "above the threshold",
            "response": ("Attenuation is comparable to a plausible effect. AMEND the concept "
                         "set to carry the three candidate cervical fusion codes, write the "
                         "amendment into plan section 13 with the measured share and the date, "
                         "re-hash the plan BEFORE any outcome is computed, and make the "
                         "pre-amendment classification the supplementary row instead."),
        }
    return {
        "share": share,
        "amend": False,
        "branch": "at or below the threshold",
        "response": ("Attenuation is comfortably inside the interval this study will produce. "
                     "The locked set is NOT amended. A supplementary row moves the misfiled "
                     "episodes to cervical fusion and re-estimates the primary contrast; it is "
                     "reported whatever it shows."),
    }


def decompression_gap_response(invisible: int, locked_decompression: int) -> dict[str, Any]:
    """The prespecified response to the decompression gap.  Plan 2.7.

    Deliberately weaker than the fusion response, and the asymmetry is the point: a missing
    case costs n and may select, but it moves no case between arms, so it cannot bias the
    primary contrast in the way a misfiled case does.
    """
    if invisible == 0:
        return {
            "share": Fraction(0),
            "amend": False,
            "branch": "measured zero",
            "response": "Record the measured zero. No amendment.",
        }
    share = Fraction(invisible, invisible + locked_decompression)
    if share > DECOMPRESSION_GAP_THRESHOLD:
        return {
            "share": share,
            "amend": True,
            "branch": "above the threshold",
            "response": ("The cervical decompression arm is materially incomplete. AMEND the "
                         "concept set to carry the four candidate cervical decompression "
                         "codes, under the same plan section 13 and re-hash discipline."),
        }
    return {
        "share": share,
        "amend": False,
        "branch": "at or below the threshold",
        "response": ("Stated omission: the four absent codes and the measured share go in the "
                     "Methods and in the limitations. The set is not amended."),
    }


# ======================================================================================
# (7) The tier decision and the arm decision.
# ======================================================================================


def tier_for_events(n_events: int) -> dict[str, Any]:
    """The protocol's tier for an event count.  Plan 1.2, boundaries inclusive at the bottom."""
    n = _whole(n_events, "the event count")
    if n >= TIER_1_MIN_EVENTS:
        tier = 1
    elif n >= TIER_2_MIN_EVENTS:
        tier = 2
    elif n >= TIER_3_MIN_EVENTS:
        tier = 3
    else:
        tier = 4
    band, permitted = next((b, p) for t, b, p in TIER_TABLE if t == tier)
    return {"tier": tier, "band": band, "permitted": permitted}


def arm_decision(acute_care_upper_bound: int) -> dict[str, Any]:
    """What this ceiling already settles about Arm A, and what it cannot settle.

    A ceiling licenses exactly one direction of inference and the report has to say which.  The
    true gate count is at most this number, so a LOW ceiling is conclusive: it forecloses every
    tier above the one it lands in, before a single exclusion has run.  A HIGH ceiling settles
    nothing at all, because the entire eligibility ladder, the discharge anchor and the
    computable-landmark rule all sit between this number and the gate.
    """
    bound = _whole(acute_care_upper_bound, "the acute-care upper bound")
    best = tier_for_events(bound)
    dead = bound < AIM_A_MIN_EVENTS
    return {
        "upper bound": bound,
        "best attainable tier": best["tier"],
        "best attainable band": best["band"],
        "permitted at best": best["permitted"],
        "aim A foreclosed": dead,
        "build matched sampling": not dead,
    }


# ======================================================================================
# (8) The stratified table, its suppression, and the partition guard.
#
# THIS TABLE WILL CONTAIN SUPPRESSED CELLS AND THAT IS THE EXPECTED OUTCOME.  It is the table
# the arm decision is read off, it is deliberately cut fine enough to show the thinnest cell,
# and a stratification fine enough to be useful is a stratification thin enough to suppress.
# The job here is not to avoid suppression, it is to make sure a suppressed cell cannot be
# recovered by subtraction from a disclosed total, in EITHER direction of the table.
# ======================================================================================


def wide_counts(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    """One stage's counts as rows of regions by columns of groups, with exact margins.

    Margins are summed from the EXACT integers and rounded afterwards.  Summing rounded parts
    would put an error of up to ten per cell into every total, which is how a total ends up
    disagreeing with its own rows by more than the rounding footnote can explain.
    """
    counts = {(region, group): 0 for region in REGION_LABELS for group in GROUP_LABELS}
    region_of = {sql: display for sql, display in REGION_STRATA}
    group_of = {sql: display for sql, display in PROCEDURE_GROUPS}
    for row in frame.to_dict("records"):
        region = region_of.get(str(row.get("region_stratum")))
        group = group_of.get(str(row.get("procedure_group")))
        if region is None or group is None:
            raise PreGateError(
                "the counts query returned a stratum this module does not know. Its CASE "
                "expression and this module's stratum vocabulary have drifted apart."
            )
        counts[(region, group)] += _whole(row.get(column), f"a {column!r} cell")
    wide = pd.DataFrame(0, index=list(WIDE_ROWS), columns=list(WIDE_COLUMNS), dtype="int64")
    for (region, group), value in counts.items():
        wide.loc[region, group] = value
    wide[ALL_GROUPS_LABEL] = wide[list(GROUP_LABELS)].sum(axis=1)
    wide.loc[ALL_REGIONS_LABEL] = wide.loc[list(REGION_LABELS)].sum(axis=0)
    return wide


def suppression_mask(wide: pd.DataFrame) -> pd.DataFrame:
    """Which cells may not be shown, after complementary suppression closes both directions.

    Three rules, applied to fixpoint:

      * `disclosable(n)` is the floor and the only floor.  It, not a literal, decides the seed
        mask.  A true zero survives it: zero is an absence, not a small cell.
      * A row's fusion and decompression cells partition that row's total.  Two members means
        one suppressed member is exactly recoverable, so the rule masks BOTH or neither.
      * A column's five region cells partition that column's all-regions total.  With one
        member suppressed, the rule masks a second: the smallest still-shown cell, because
        masking the smallest loses the least and ties break on stratum order so the choice is
        deterministic across runs.

    Masking a cell can open a hole in the other direction, so this iterates.  The bound is the
    number of cells, since every pass either masks at least one more cell or stops, and the
    final state is checked against `export_violations` rather than trusted.
    """
    mask = pd.DataFrame(False, index=wide.index, columns=wide.columns)
    for row in wide.index:
        for column in wide.columns:
            if not disclosable(wide.loc[row, column]):
                mask.loc[row, column] = True

    members = list(GROUP_LABELS)
    for _ in range(wide.size + 1):
        changed = False
        for row in wide.index:
            hidden = [c for c in members if mask.loc[row, c]]
            if len(hidden) == 1:
                for column in members:
                    if not mask.loc[row, column]:
                        mask.loc[row, column] = True
                        changed = True
        for column in wide.columns:
            hidden = [r for r in REGION_LABELS if mask.loc[r, column]]
            if len(hidden) == 1:
                shown = [r for r in REGION_LABELS if not mask.loc[r, column]]
                if shown:
                    victim = min(shown, key=lambda r: (int(wide.loc[r, column]),
                                                       REGION_LABELS.index(r)))
                    mask.loc[victim, column] = True
                    changed = True
        if not changed:
            return mask
    raise PreGateError("complementary suppression did not reach a fixpoint")


def render_wide(wide: pd.DataFrame, mask: pd.DataFrame) -> pd.DataFrame:
    """Rounded counts where the mask allows, the suppression sentinel where it does not.

    The floor is checked here on the TRUE count, one more time and against `disclosable`, so
    that a mask built anywhere other than `suppression_mask` still cannot show a small cell.
    This is the check that matters, and it belongs on the unrounded number: a rounded 20 is a
    legitimate disclosure standing on a true count of 21 to 29, while a true 20 is not, and
    after rounding the two are the same digits.
    """
    out = pd.DataFrame(index=wide.index, columns=wide.columns, dtype="object")
    for row in wide.index:
        for column in wide.columns:
            if mask.loc[row, column]:
                out.loc[row, column] = SUPPRESSED
                continue
            if not disclosable(wide.loc[row, column]):
                raise DisclosureError(
                    "a stratum cell that did not clear the floor was about to be shown. The "
                    "column and row are named, the value never is."
                )
            out.loc[row, column] = round20(wide.loc[row, column])
    return out


def partition_violations(display: pd.DataFrame) -> list[str]:
    """Ask `export_violations` whether either direction of this table can be subtracted open.

    The check is not reimplemented here.  `export_violations` owns the refusal class for
    "exactly one suppressed member of a declared partition", and it takes partitions as column
    groups checked row by row, so the column direction is asked by handing it the TRANSPOSE:
    the five region strata become columns and the one declared partition is the five of them.

    `count_cols` IS declared, and used to be withheld.  The count-cell class asked `disclosable`
    of the cell as written; `disclosable(20)` is False while `round20` of every true count from
    21 to 29 is exactly 20, so declaring it refused this table's own correctly rounded cells.
    That class now asks `is_legal_disclosed_count`, which is the question a rendered cell is in
    a position to answer, so the check is safe to ask and every column here is a count column.
    The division of labour did not move: the floor still belongs on the TRUE count and is still
    applied there, by `suppression_mask` and again by `render_wide`.  What is gained is a second
    and independent reader of the one frame this module leaves as numerals.
    """
    violations = list(export_violations(display, count_cols=list(display.columns),
                                        partitions=[list(GROUP_LABELS)]))
    transposed = display.loc[list(REGION_LABELS)].T
    violations += list(export_violations(transposed, count_cols=list(transposed.columns),
                                         partitions=[list(REGION_LABELS)]))
    return violations


def stratified_tables(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """One suppressed display table per stage, each checked in both directions before returning."""
    tables: dict[str, pd.DataFrame] = {}
    for column, _label in STAGES:
        wide = wide_counts(frame, column)
        display = render_wide(wide, suppression_mask(wide))
        violations = partition_violations(display)
        if violations:
            raise DisclosureError(
                "the stratified table would still allow a suppressed cell to be recovered by "
                f"subtraction after complementary suppression: {len(violations)} refusal(s) "
                "stand. Do not print it."
            )
        tables[column] = display
    return tables


def headline_counts(frame: pd.DataFrame) -> dict[str, int]:
    """The three plan-ordered headline numbers, as exact integers, taken from the same margins."""
    return {column: int(wide_counts(frame, column).loc[ALL_REGIONS_LABEL, ALL_GROUPS_LABEL])
            for column, _ in STAGES}


# ======================================================================================
# (9) Rendering.  Every human-visible string is built here and the house prose rules are
#     asserted on the RENDERED text, not grepped for afterwards.
# ======================================================================================

# The two banned dash characters are `disclosure`'s constants, imported rather than redefined:
# a second definition is a second place for the code point to be typed slightly wrong.
_SNAKE_TOKEN = re.compile(r"\b[a-z0-9]+_[a-z0-9_]*\b")
_RULE = "=" * 86
_THIN = "-" * 86


def _count(value: Any) -> str:
    """Render one already-rounded count for print, with the house thousands separator."""
    if is_suppressed(value):
        return SUPPRESSED
    return f"{int(value):,}"


def _table_lines(headers: Sequence[str], rows: Sequence[Sequence[str]],
                 align: str = "") -> list[str]:
    """A fixed-width table.  `align` is one character per column, 'l' or 'r'.

    Default is the shape a count table wants: a left-hand label and numbers right-aligned on
    their last digit, which is the only alignment in which a reader can compare magnitudes down
    a column at a glance.  A column of sentences takes 'l' explicitly.
    """
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


def _bullets(items: Sequence[str], width: int = 82) -> list[str]:
    """Wrapped bullet points.  A bullet that runs past the terminal is a bullet nobody reads."""
    out: list[str] = []
    for item in items:
        chunks = _wrap(item, width - 4)
        out.append("  * " + chunks[0])
        out += ["    " + chunk for chunk in chunks[1:]]
    return out


def _assert_house_prose(text: str) -> None:
    """Stop conditions on the rendered report, checked before a character of it is printed."""
    if EM_DASH in text:
        raise PreGateError("the report contains an em-dash, which no house string may carry")
    if MINUS_SIGN in text:
        raise PreGateError("the report contains a Unicode minus sign, which is banned")
    snake = sorted(set(_SNAKE_TOKEN.findall(text)))
    if snake:
        raise PreGateError(
            f"the report contains snake-case token(s) {snake}, and an identifier is never a "
            f"user-visible string. Use the display label beside it."
        )


def render_report(result: Mapping[str, Any]) -> str:
    """The whole pre-gate report, as one string, ending in the hard stop."""
    lines: list[str] = []
    add = lines.append

    headline = result["headline"]
    tables = result["tables"]
    gaps = result["gaps"]
    fusion = result["fusion response"]
    decompression = result["decompression response"]
    decision = result["decision"]
    total_episodes = headline["n_episodes"]

    add(_RULE)
    add("PHASE 2 PRE-GATE: UPPER-BOUND COUNTS, COMPUTED BEFORE THE ELIGIBILITY EXCLUSIONS")
    add(_RULE)
    add("")
    add("Every count below is an UPPER BOUND. None of the nineteen eligibility rungs has run,")
    add("so each of these numbers can only fall once Phase 3 applies them. Read each one as a")
    add("ceiling on what the study can have, never as a cohort size, and do not carry any of")
    add("them into a manuscript sentence: the ladder, not this report, owns the cohort.")
    add("")
    add("Applied here, because the concept set requires it and it changes a count:")
    lines += _bullets(APPLIED_HERE)
    add("")
    add("NOT applied here. Every line below lowers a count later, and the gap between this")
    add("report and the Phase 3 ladder is mostly this list rather than attrition:")
    lines += _bullets(NOT_APPLIED_HERE)
    add("")
    add("The acute-care arm counts a visit starting strictly after the operation date, so the")
    add("index admission is never its own outcome. A same-stay transfer recorded as a fresh")
    add("visit on postoperative day 1 or later is still counted, which overcounts, which is the")
    add("correct direction for a ceiling.")
    add("")

    add(_THIN)
    add("CONCEPT SET")
    add(_THIN)
    add(result["concept summary"])
    add("These are vocabulary counts, not person counts, so the disclosure floor does not")
    add("apply to them and they are printed in full.")
    add("")

    add(_THIN)
    add("THE THREE HEADLINE UPPER BOUNDS, in the locked plan's own order")
    add(_THIN)
    rows = []
    for column, label in STAGES:
        rows.append([label, _count(round20(headline[column]))])
    add("\n".join(_table_lines(["Stage (upper bound, before exclusions)", "Episodes"], rows)))
    add("")
    add(f"Denominator: all spine surgical episodes found, n = "
        f"{_count(round20(total_episodes))}.")
    add("Each stage is nested inside the one above it.")
    add("")

    add(_THIN)
    add("BY REGION AND FUSION STATUS. This is the table the arm decision is read off.")
    add(_THIN)
    add("What this table is NOT: it is not the analytic cohort, not a Table 1, and not a")
    add("prevalence. Its four region strata beyond cervical and lumbar exist so that every")
    add("episode a later rung will remove is visible on its own row instead of hidden inside a")
    add("neighbouring one. Suppressed cells below are the expected outcome of stratifying this")
    add("finely, not a failure: where one cell of a row or column is too small to show, a")
    add("second is suppressed with it, because otherwise subtraction from the disclosed total")
    add("would recover the first exactly.")
    add("")
    header = ["Region stratum", "Group"] + [label for _, label in STAGES]
    rows = []
    for region in WIDE_ROWS:
        for group in WIDE_COLUMNS:
            cells = [_count(tables[column].loc[region, group]) for column, _ in STAGES]
            rows.append([region if group == WIDE_COLUMNS[0] else "", group] + cells)
    add("\n".join(_table_lines(header, rows, align="ll" + "r" * len(STAGES))))
    add("")
    add(f"Denominator: all spine surgical episodes found, n = "
        f"{_count(round20(total_episodes))}.")
    add("Every count is rounded to the nearest 20 independently, so the rows and columns of")
    add("this table do not add up. That is expected and the numbers are not adjusted to make")
    add("them add up. Counts of 20 or fewer are suppressed; larger counts are rounded to the")
    add("nearest 20, so a disclosed 20 represents a true count of 21 to 29.")
    add("")

    add(_THIN)
    add("THE TWO CONCEPT-SET GAPS. Measured, not amended.")
    add(_THIN)
    add("The locked set was NOT changed by this step and must not be changed by anyone reading")
    add("this report on their own authority: amending it breaks the 852 assertion and every")
    add("count calibrated to it. Measuring a code is not adding it. Both responses below were")
    add("written into plan section 2.7 before either number existed, and both thresholds are")
    add("evaluated on the exact counts inside the perimeter while only rounded counts print.")
    add("")
    locked = gaps["locked cervical decompression persons"]
    invisible = gaps["invisible cervical decompression persons"]
    misfiled = gaps["misfiled cervical fusion persons"]
    add("Fusion gap. Persons carrying a candidate cervical fusion code, no locked cervical")
    add("fusion evidence, and locked cervical decompression evidence. These sit on the WRONG")
    add("ARM of the primary contrast today, because the anterior cervical discectomy code is in")
    add("the set and tagged decompression while the arthrodesis code beside it is absent.")
    add(f"  Misfiled persons, of locked cervical decompression : "
        f"{n_pct(misfiled, locked)}")
    add(f"  Prespecified threshold                             : "
        f"above {float(FUSION_GAP_THRESHOLD):.0%} amends the set")
    add(f"  Measured branch                                    : {fusion['branch']}")
    add("  Response, fixed in advance:")
    for chunk in _wrap(fusion["response"], 80):
        add("    " + chunk)
    add("")
    add("Decompression gap. Persons the locked set cannot see at all, because the four absent")
    add("cervical decompression codes are their only evidence. These cost n and may select, but")
    add("they move no case between arms.")
    add(f"  Invisible persons, of all cervical decompression   : "
        f"{n_pct(invisible, invisible + locked)}")
    add(f"  Prespecified threshold                             : "
        f"above {float(DECOMPRESSION_GAP_THRESHOLD):.0%} amends the set")
    add(f"  Measured branch                                    : {decompression['branch']}")
    add("  Response, fixed in advance:")
    for chunk in _wrap(decompression["response"], 80):
        add("    " + chunk)
    add("")
    add("A misfiled case sits on the wrong arm; a missing case sits on neither. That is why the")
    add("two thresholds differ, and neither may be moved after a measurement without an")
    add("amendment recording the old value, the new value and the reason.")
    add("")

    add(_RULE)
    add("HARD STOP. PHASE 2 ENDS HERE. A HUMAN READS THESE NUMBERS AND DECIDES.")
    add(_RULE)
    add("")
    add("THE DECISION: which arm is this study in?")
    add("")
    add(f"  Acute-care ceiling, before any exclusion : "
        f"{_count(round20(decision['upper bound']))} episodes")
    add(f"  Best tier still attainable               : tier {decision['best attainable tier']}"
        f" ({decision['best attainable band']})")
    add(f"  Permitted there                          : {decision['permitted at best']}")
    add("")
    add("  The protocol's tier table, on usable events:")
    tier_rows = [[f"Tier {tier}", band, permitted] for tier, band, permitted in TIER_TABLE]
    for chunk in _table_lines(["", "Usable events", "Permitted analysis"], tier_rows,
                              align="lll"):
        add("    " + chunk)
    add("")
    if decision["aim A foreclosed"]:
        add("  AIM A IS DEAD, and this ceiling settles it before a single exclusion has run.")
        for chunk in _wrap(
                f"The true gate count is at most the ceiling above, which is under the "
                f"{AIM_A_MIN_EVENTS} events the early-warning arm needs, so no eligibility "
                f"rung, no discharge anchor and no landmark rule can raise it.", 78):
            add("  " + chunk)
        add("  DO NOT BUILD THE MATCHED-SAMPLING BRANCH. Arm A is reported as the feasibility")
        add("  gate itself, which is a real and useful result about this data source, and the")
        add("  manuscript is Arm B.")
    else:
        add("  Aim A is not foreclosed by this ceiling, and a ceiling settles nothing on its")
        add("  own in this direction. The eligibility ladder, the discharge anchor and the")
        add("  computable-landmark rule all sit between this number and the gate, and each of")
        add("  them only subtracts. Build the matched-sampling branch only if you accept that")
        add("  the true count may still land two tiers below this ceiling.")
    add("")
    add("  Arm B, Digital Recovery Debt, is primary either way and requires no events at all.")
    add("  It cannot be extinguished by a thin event count, which is why it was chosen as")
    add("  primary before any of these numbers existed.")
    add("")
    add("  What each gap already obliges, whatever is decided about the arm:")
    add(f"    Fusion gap        : {'AMEND the locked set' if fusion['amend'] else 'no amendment'}")
    add(f"    Decompression gap : "
        f"{'AMEND the locked set' if decompression['amend'] else 'no amendment'}")
    if fusion["amend"] or decompression["amend"]:
        add("    An amendment is written into plan section 13 with the measured share and the")
        add("    date, and the plan is re-hashed BEFORE any outcome is computed. Nothing about")
        add("    the study's answer exists yet, so taking this branch cannot have been chosen")
        add("    in response to a result.")
    add("")
    add("  DO NOT, on the strength of this report: amend the locked concept set without the")
    add("  section 13 record, build any derived table, run the eligibility ladder, or quote a")
    add("  number above as a cohort size.")
    add("")
    add("  Before leaving this session: print the running query cost and paste it into the")
    add("  handoff block, then DELETE the compute environment. Deleted, not paused, and the")
    add("  applications tab verified empty.")
    add(_RULE)
    return "\n".join(lines)


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    out: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > width:
            out.append(current)
            current = word
        else:
            current = f"{current} {word}".strip()
    if current:
        out.append(current)
    return out


# ======================================================================================
# (10) The run.  q_guarded is the only query path, and nothing executes until everything is
#      priced and the aggregate fits the budget.
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
    """Find the two config-notebook helpers, in the order a caller would expect them found.

    Explicit argument first (which is how the self-test injects a fake), then this module's own
    globals (which is what `%run -i` populates), then the live kernel's namespace (which covers
    `%run` without `-i`).  Nothing falls back to a raw BigQuery client: `q_guarded` is the only
    query path, and a module that could quietly find its own way to the API is a module that
    eventually runs a query with no printed estimate and no cap.
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
            raise PreGateError(
                f"{name} is not available. This step runs inside the perimeter and gets its "
                f"only query path from the configuration notebook. Run that notebook first, "
                f"then load this file into the same kernel."
            )
        resolved.append(found)
    return resolved[0], resolved[1]


def cost_plan(
    sql_by_key: Mapping[str, str],
    dry_run_gb: Callable[[str], float],
    *,
    budget_gb: float = PREGATE_BUDGET_GB,
) -> dict[str, Any]:
    """Price every query before any of them runs, and refuse the whole step if it does not fit.

    A dry run is free and prices the columns referenced rather than the table, so this pre-flight
    costs nothing and answers the frightening question first.  `q_guarded` will dry-run each
    query again when it executes it; that second dry run is also free and is the one that puts
    the estimate on the screen immediately before the job, which is the rule.
    """
    estimates: dict[str, float] = {}
    for key in QUERY_KEYS:
        estimates[key] = float(dry_run_gb(sql_by_key[key]))
    total = sum(estimates.values())
    over_cap = sorted(k for k, gb in estimates.items() if gb > PLANNED_MAX_GB[k])
    plan = {
        "estimates": estimates,
        "total gb": total,
        "usd": total / 1024.0 * USD_PER_TIB,
        "budget gb": float(budget_gb),
        "over cap": over_cap,
        "fits": (total <= float(budget_gb)) and not over_cap,
    }
    return plan


def cost_plan_lines(plan: Mapping[str, Any]) -> list[str]:
    """The cost plan as text, so it can be checked as easily as it is printed."""
    lines = [_THIN,
             "COST PLAN. Nothing has executed yet; every figure below came from a free dry run.",
             _THIN]
    rows = []
    for key in QUERY_KEYS:
        gb = plan["estimates"][key]
        rows.append([key, f"{gb:,.3f}", f"{PLANNED_MAX_GB[key]:,.1f}",
                     f"{gb / 1024.0 * USD_PER_TIB:,.4f}"])
    lines += _table_lines(["Query", "Estimate, GiB", "Cap, GiB", "Estimate, USD"], rows)
    lines.append(f"total estimate {plan['total gb']:,.3f} GiB, about ${plan['usd']:,.4f}, "
                 f"against a budget of {plan['budget gb']:,.1f} GiB")
    return lines


def run_pregate(
    *,
    probe_result: Mapping[str, Any] | None = None,
    q_guarded: Callable[..., pd.DataFrame] | None = None,
    dry_run_gb: Callable[[str], float] | None = None,
    mirror_junctions: bool = False,
    schema: Mapping[str, str] = DEFAULT_SCHEMA,
    budget_gb: float = PREGATE_BUDGET_GB,
    show_report: bool = True,
) -> dict[str, Any]:
    """Run the four queries, print the report, and stop.

    `probe_result` is what `01_probe.py`'s `run_probe()` returned, and it is REQUIRED: the
    keyword defaults to None only so that omitting it produces this module's own diagnosis
    rather than a TypeError naming an argument.  There is no path through this function that
    reaches a query without a probe result whose `probe ok` is true.  The visit concept ids
    themselves are not a parameter at all any more; they are prespecified in 01_probe.py and
    imported, and the probe verdict is the evidence that they cover this CDR.  See section (1)
    for why those are two separate obligations and why both are enforced.

    Returns the assembled result so a caller can re-render it or paste a number into the
    session log.  It returns ROUNDED display tables and exact scalars, and the exact scalars
    are the ones the prespecified thresholds are evaluated on, never printed.

    `show_report=False` silences every print, including the cost plan and the frame shapes.
    It exists so the self-test can drive the whole path without flooding the output, and it is
    never what an in-perimeter run passes: the printed cost plan is the estimate that rule 2
    requires to appear before anything executes.
    """
    # FIRST, before the runtime is even resolved: a probe that did not pass costs nothing to
    # refuse here and about fifteen cents to refuse four queries later.
    _require_passing_probe(probe_result)
    visit_concept_ids = ED_AND_INPATIENT_VISIT_CONCEPT_IDS
    query, price = _resolve_runtime(q_guarded, dry_run_gb)
    def say(*text: str) -> None:
        if show_report:
            for line in text:
                print(line)
    # Printed before the cost plan, because the ids are the one input to these queries that a
    # reader of the report cannot see in the numbers.  Held to the same prose rule as the
    # report itself, which is why it names the probe rather than the probe's filename.
    banner = "\n".join([
        f"VISIT CONCEPT IDS {list(visit_concept_ids)}. Prespecified by the runtime probe and "
        f"verified by it",
        f"against this CDR's own visit distribution. Emergency {list(ED_VISIT_CONCEPT_IDS)}, "
        f"inpatient {list(INPATIENT_VISIT_CONCEPT_IDS)}.",
        f"{sorted(set(ED_VISIT_CONCEPT_IDS) & set(INPATIENT_VISIT_CONCEPT_IDS))[0]} is in both "
        f"sets and counted once here: an emergency department",
        "presentation that became an admission is ONE event, per plan section 4.1.",
    ])
    _assert_house_prose(banner)
    say(_THIN, banner, _THIN)
    sql_by_key = build_sql(visit_concept_ids=visit_concept_ids,
                           mirror_junctions=mirror_junctions, schema=schema)

    plan = cost_plan(sql_by_key, price, budget_gb=budget_gb)
    say(*cost_plan_lines(plan))
    if plan["over cap"]:
        raise PreGateBudgetExceeded(
            f"nothing executed and nothing billed: {plan['over cap']} priced above the cap "
            f"sized for it. A query that costs more than its cap is not the query this module "
            f"thinks it is; read the estimate before raising anything."
        )
    if not plan["fits"]:
        raise PreGateBudgetExceeded(
            f"nothing executed and nothing billed: the four queries price at "
            f"{plan['total gb']:,.3f} GiB, about ${plan['usd']:,.4f}, against a budget of "
            f"{plan['budget gb']:,.1f} GiB. Raise it deliberately with this number in hand by "
            f"passing a larger budget, or narrow the columns referenced."
        )

    concept_frame = query(sql_by_key["concept set resolution"],
                          max_gb=PLANNED_MAX_GB["concept set resolution"],
                          note="pre-gate, concept set resolution")
    if show_report:
        safe_show(concept_frame, "concept set")
    # The batch-2 requirement carried forward from the concept-set module: this assertion had
    # no production caller, so neither it nor its own self-test could ever detect drift between
    # the module's maps and the real CDR.  This is that caller.  It RAISES.
    cs_spine.assert_concept_frame(concept_frame, mirror_junctions=mirror_junctions)
    concept_summary = (
        f"Resolved {cs_spine.EXPECTED_CONCEPT_COUNT} source concepts as locked: "
        f"{cs_spine.EXPECTED_CPT_CONCEPTS} CPT-4, "
        f"{cs_spine.EXPECTED_PCS_FUSION_CONCEPTS} fusion and "
        f"{cs_spine.EXPECTED_PCS_DECOMPRESSION_CONCEPTS} decompression ICD-10-PCS."
    )

    decompression_frame = query(sql_by_key["cervical decompression gap"],
                                max_gb=PLANNED_MAX_GB["cervical decompression gap"],
                                note="pre-gate, cervical decompression gap")
    if show_report:
        safe_show(decompression_frame, "cervical decompression split")
    fusion_frame = query(sql_by_key["cervical fusion gap"],
                         max_gb=PLANNED_MAX_GB["cervical fusion gap"],
                         note="pre-gate, cervical fusion gap")
    if show_report:
        safe_show(fusion_frame, "cervical fusion split")

    counts_frame = query(sql_by_key["pre-gate upper-bound counts"],
                         max_gb=PLANNED_MAX_GB["pre-gate upper-bound counts"],
                         note="pre-gate, upper-bound counts by region and fusion status")
    if show_report:
        safe_show(counts_frame, "pre-gate counts")

    result = assemble(concept_summary, decompression_frame, fusion_frame, counts_frame)
    # The split frames carry PERSON counts.  They are rounded and suppressed here so that a
    # caller who prints the returned object cannot print a raw one.
    result["decompression split"] = suppress_frame(
        decompression_frame, ["n_persons", "n_also_carrying_candidate_cpt"])
    result["fusion split"] = suppress_frame(
        fusion_frame, ["n_persons", "n_also_carrying_candidate_cpt",
                       "n_also_carrying_locked_cervical_decompression"])
    result["cost plan"] = dict(plan)
    say(result["report"])
    return result


def assemble(
    concept_summary: str,
    decompression_frame: pd.DataFrame,
    fusion_frame: pd.DataFrame,
    counts_frame: pd.DataFrame,
) -> dict[str, Any]:
    """Turn four returned frames into the decided, suppressed, rendered result.

    Pure: no query, no print, no file.  This is the whole of the module's judgment, which is
    what makes the judgment testable on a laptop against synthetic frames.
    """
    gaps = gap_measurements(decompression_frame, fusion_frame)
    locked = gaps["locked cervical decompression persons"]
    fusion = fusion_gap_response(gaps["misfiled cervical fusion persons"], locked)
    decompression = decompression_gap_response(
        gaps["invisible cervical decompression persons"], locked)
    headline = headline_counts(counts_frame)
    result: dict[str, Any] = {
        "concept summary": concept_summary,
        "gaps": gaps,
        "fusion response": fusion,
        "decompression response": decompression,
        "headline": headline,
        "tables": stratified_tables(counts_frame),
        "decision": arm_decision(headline["n_acute_care"]),
    }
    report = render_report(result)
    _assert_house_prose(report)
    result["report"] = report
    return result


# ======================================================================================
# (11) Self-test.  No cloud, no file, no network.  The house pattern from disclosure.py.
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


_EMITTED_TERM = re.compile(
    r"^(?P<negated>NOT\s+)?s\.(?P<column>[a-z_]+)(?:\s*=\s*'(?P<literal>[a-z ]+)')?$")


def _emitted_line(sql: str, marker: str) -> str:
    """The one emitted line carrying `marker`, or a failure naming how many there were."""
    hits = [line for line in sql.splitlines() if marker in line]
    if len(hits) != 1:
        raise AssertionError(
            f"expected exactly one emitted line carrying {marker!r} and found {len(hits)}")
    return hits[0]


def _evaluate_row_predicate(body: str, record: Mapping[str, Any]) -> bool:
    """Evaluate one emitted row predicate against one synthetic procedure record.

    Understands exactly the shape this module emits: AND-joined terms, each optionally negated,
    each either a bare boolean column or a column compared against a quoted literal.  It REFUSES
    anything else rather than guessing, so a predicate rewritten into a shape this evaluator has
    never seen fails the self-test loudly instead of passing it quietly.
    """
    value = True
    for part in body.split(" AND "):
        match = _EMITTED_TERM.match(part.strip())
        if match is None:
            raise AssertionError(
                f"the self-test cannot evaluate the emitted predicate {part.strip()!r}. It was "
                f"written against AND-joined column tests; reconcile the two rather than "
                f"trusting either."
            )
        column = match.group("column")
        if column not in record:
            raise AssertionError(
                f"the emitted predicate reads a column {column!r} that the synthetic record "
                f"does not carry")
        literal = match.group("literal")
        term = (record[column] == literal) if literal is not None else bool(record[column])
        if match.group("negated"):
            term = not term
        value = value and term
    return value


def _logical_or(emitted_line: str, records: Sequence[Mapping[str, Any]]) -> bool:
    """Apply one emitted `LOGICAL_OR(...)` aggregate to a synthetic same-day bundle.

    The point of parsing the EMITTED TEXT rather than asserting against a retyped copy of the
    predicate is that a revert has to go red.  Put the add-on filter back into the fusion flag
    and this function sees it, applies it, and the episode whose only arthrodesis evidence is an
    add-on stops being a fusion.  A retyped copy would agree with whatever it was retyped from.
    """
    body = emitted_line[emitted_line.index("LOGICAL_OR(") + len("LOGICAL_OR("):]
    body = body[:body.rindex(")")]
    return any(_evaluate_row_predicate(body, record) for record in records)


def _record(region: str, procedure_class: str, add_on: bool) -> dict[str, Any]:
    """One synthetic `spine_src` row as the emitted predicates see it."""
    return {"region": region, "procedure_class": procedure_class, "is_add_on": add_on}


def _split_frame(*, candidate: int, cpt: int, pcs: int, both: int,
                  misfiled: int = 0, fusion_shape: bool = False) -> pd.DataFrame:
    """A synthetic split frame with the builders' exact columns and their exact sort order."""
    rows = [
        {"evidence_path": CANDIDATE_ONLY_PATH,
         "n_persons": candidate, "n_also_carrying_candidate_cpt": candidate,
         "n_also_carrying_locked_cervical_decompression": misfiled},
        {"evidence_path": "locked set: CPT and ICD-10-PCS",
         "n_persons": both, "n_also_carrying_candidate_cpt": 0,
         "n_also_carrying_locked_cervical_decompression": 0},
        {"evidence_path": "locked set: CPT only",
         "n_persons": cpt, "n_also_carrying_candidate_cpt": 0,
         "n_also_carrying_locked_cervical_decompression": 0},
        {"evidence_path": "locked set: ICD-10-PCS only",
         "n_persons": pcs, "n_also_carrying_candidate_cpt": 0,
         "n_also_carrying_locked_cervical_decompression": 0},
    ]
    frame = pd.DataFrame(rows)
    if not fusion_shape:
        frame = frame.drop(columns=["n_also_carrying_locked_cervical_decompression"])
    return frame


def _counts_frame(cells: Mapping[tuple[str, str], tuple[int, int, int, int]]) -> pd.DataFrame:
    rows = []
    for (region, group), values in cells.items():
        row = {"region_stratum": region, "procedure_group": group}
        row.update(dict(zip(STAGE_COLUMNS, values)))
        rows.append(row)
    return pd.DataFrame(rows)


def _uniform_counts_frame(values: tuple[int, int, int, int]) -> pd.DataFrame:
    return _counts_frame({(region, group): values
                          for region, _ in REGION_STRATA for group, _ in PROCEDURE_GROUPS})


def _run_self_test() -> None:
    global _ASSERTIONS
    _ASSERTIONS = 0

    # ---- 0. the visit concept ids: prespecified there, verified there, imported here ----
    # The import mechanism is TESTED, not assumed, because 01_probe.py's filename is not an
    # importable identifier and a path-based load is the kind of thing that works on the laptop
    # it was written on and not on the VM.
    probe_module = _load_probe_module()
    _expect(probe_module is sys.modules.get(_PROBE_MODULE_NAME),
            "the probe module loads by path and is cached, so a second call is the same object")
    _expect(_load_probe_module() is probe_module,
            "and calling the loader twice does not build a second copy of the constants")
    _expect(getattr(probe_module, "__file__", "").endswith(_PROBE_FILENAME),
            "and what was loaded is the file beside this one, not something off sys.path")
    _expect(ED_VISIT_CONCEPT_IDS == tuple(probe_module.ED_VISIT_CONCEPT_IDS)
            and INPATIENT_VISIT_CONCEPT_IDS == tuple(probe_module.INPATIENT_VISIT_CONCEPT_IDS),
            "both id tuples are the probe's own, not retyped, so they cannot diverge")
    _expect(ED_AND_INPATIENT_VISIT_CONCEPT_IDS
            == tuple(sorted(set(ED_VISIT_CONCEPT_IDS) | set(INPATIENT_VISIT_CONCEPT_IDS))),
            "the pre-gate reads their union, sorted for a byte-stable in-list")
    shared = set(ED_VISIT_CONCEPT_IDS) & set(INPATIENT_VISIT_CONCEPT_IDS)
    _expect(len(shared) == 1,
            "exactly one id is in both sets: an emergency presentation that became an "
            "admission, which plan section 4.1 collapses into one event")
    _expect(sum(1 for v in ED_AND_INPATIENT_VISIT_CONCEPT_IDS if v in shared) == 1,
            "and the union carries it once, so the acute-care ceiling is not inflated by it")
    _expect_raises(PreGateError,
                   lambda: _borrowed_concept_ids(probe_module, "NO_SUCH_CONSTANT"),
                   "a missing id tuple is a stop condition, never an empty in-list")
    _expect_raises(PreGateError,
                   lambda: _borrowed_concept_ids(probe_module, "FITBIT_TABLES_REQUIRED"),
                   "and a tuple of names where integers belong is refused")

    # The mechanism half: no probe verdict, no run. Checked BEFORE the runtime is resolved, so
    # these refusals do not depend on a query path existing.
    _expect_raises(PreGateError, lambda: run_pregate(show_report=False),
                   "with no probe result at all the pre-gate refuses to run")
    _expect_raises(PreGateError, lambda: run_pregate(probe_result={}, show_report=False),
                   "and a mapping carrying no verdict is refused as not a probe result")
    _expect_raises(PreGateError,
                   lambda: run_pregate(probe_result={"probe ok": False,
                                                     "halting": ["PROBE 1"]},
                                       show_report=False),
                   "and a false verdict is refused, naming the probe that halted")
    _expect_raises(PreGateError,
                   lambda: run_pregate(probe_result=[("probe ok", True)], show_report=False),
                   "and something that is not a mapping is refused rather than duck-typed")
    passing_probe: dict[str, Any] = {"probe ok": True, "halting": []}
    _expect(_require_passing_probe(passing_probe) is passing_probe,
            "a passing probe result is returned unchanged, so the gate has no other effect")

    # ---- 0b. the constants this module used to retype, now borrowed from the probe ------
    # The same guard SOURCE_CTE_NAME already gets: a divergence fails HERE, at import or at
    # `python3 02_pregate.py`, and not in a Workbench session under an 18 GiB cap.
    _expect(VALID_WEAR_DAY_MINUTES == probe_module.VALID_WEAR_MINUTES,
            "the valid-wear threshold is the probe's own, not a second copy of the same number")
    _expect(HR_ZONE_MINUTE_COLUMN == probe_module.HR_ZONE_MINUTE_COLUMN,
            "the per-zone minute column is the probe's own, not a second spelling of it")
    _expect(DEFAULT_SCHEMA["heart rate zone minutes column"] == probe_module.HR_ZONE_MINUTE_COLUMN,
            "and it is that name that reaches the schema, and therefore the emitted query")
    _expect({FITBIT_ACTIVITY_TABLE, FITBIT_HEART_RATE_TABLE}
            == set(probe_module.FITBIT_TABLES_REQUIRED),
            "the two Fitbit table names are the probe's required pair, matched on content")
    _expect(DEFAULT_SCHEMA["activity table"] == FITBIT_ACTIVITY_TABLE
            and DEFAULT_SCHEMA["heart rate table"] == FITBIT_HEART_RATE_TABLE,
            "and both reach the schema, so the probe verifies the tables the pre-gate scans")
    _expect_raises(PreGateError, lambda: _borrowed_int(probe_module, "HR_ZONE_MINUTE_COLUMN"),
                   "a column name where a whole number is expected is refused at import")
    _expect_raises(PreGateError, lambda: _borrowed_name(probe_module, "VALID_WEAR_MINUTES"),
                   "and a number where a bare identifier is expected is refused too")
    _expect_raises(PreGateError,
                   lambda: _borrowed_name(probe_module, "PROBE_RESULT_RELATIVE_PATH"),
                   "a probe string that is not a bare identifier never reaches a query")
    _expect_raises(PreGateError, lambda: _borrowed_int(probe_module, "NO_SUCH_CONSTANT"),
                   "and a constant the probe has stopped exporting is a stop condition, not a "
                   "silent fallback to a literal")

    # ---- 1. the emitted SQL -----------------------------------------------------------
    ids = [9203, 9201, 262, 9201]
    sql_a = build_sql(visit_concept_ids=ids)
    sql_b = build_sql(visit_concept_ids=list(reversed(ids)))
    _expect(sql_a == sql_b, "the emitted SQL is byte-stable across two calls")
    _expect(sorted(sql_a) == sorted(QUERY_KEYS), "every named query is built")
    placeholders = set()
    for text in sql_a.values():
        placeholders |= set(re.findall(r"\{[A-Za-z_][A-Za-z0-9_]*\}", text))
    _expect(placeholders == {"{CDR}"}, "the only placeholder emitted is the CDR")
    _expect("{GOOGLE_PROJECT}" not in "".join(sql_a.values()), "the banned spelling is absent")
    _expect("{DERIVED}" not in "".join(sql_a.values()),
            "nothing is written to the derived dataset, so its placeholder never appears")
    joined = "".join(sql_a.values()).upper()
    for forbidden in ("RAND(", "CREATE ", "INSERT ", "MERGE ", "DROP ", "UPDATE ", "DELETE "):
        _expect(forbidden not in joined, f"no emitted query contains {forbidden.strip()!r}")
    _expect("APPROX_QUANTILES" not in joined, "no approximate quantile stands in for a median")
    _expect("wb-" not in "".join(sql_a.values()) and "C2025Q4R6" not in "".join(sql_a.values()),
            "no project or dataset is hardcoded")
    _expect(EM_DASH not in "".join(sql_a.values()), "no emitted query carries an em-dash")
    _expect(SOURCE_CTE_NAME in sql_a["pre-gate upper-bound counts"],
            "the counts query is built on the concept set's own CTE")
    _expect(sql_a["pre-gate upper-bound counts"].count("262,9201,9203") == 1,
            "visit concept ids are sorted, de-duplicated and rendered once")
    _expect(build_sql() == sql_a,
            "and the imported prespecified union builds byte-identical SQL to that same list "
            "passed by hand, so the default is the prespecification and not a second opinion")
    _expect(_int_list(ED_AND_INPATIENT_VISIT_CONCEPT_IDS) in
            sql_a["pre-gate upper-bound counts"],
            "the in-list in the emitted query is exactly the imported union")
    _expect_raises(PreGateError, lambda: build_sql(visit_concept_ids=[]),
                   "an empty visit concept list is refused rather than defaulted")
    _expect_raises(PreGateError, lambda: build_sql(visit_concept_ids=["emergency"]),
                   "a visit concept name is refused")
    _expect_raises(
        PreGateError,
        lambda: pregate_counts_sql(visit_concept_ids=[9203],
                                   schema=dict(DEFAULT_SCHEMA,
                                               **{"activity table": "x`; DROP TABLE y; --"})),
        "a schema name that is not a bare identifier is refused",
    )
    _expect("SUM(h." + probe_module.HR_ZONE_MINUTE_COLUMN + ")"
            in sql_a["pre-gate upper-bound counts"],
            "the wear rule sums the column the probe names, in the probe's own spelling")
    _expect(">= " + str(probe_module.VALID_WEAR_MINUTES) in sql_a["pre-gate upper-bound counts"],
            "and compares the sum against the probe's own valid-wear threshold")
    _expect("`{CDR}." + FITBIT_HEART_RATE_TABLE + "`" in sql_a["pre-gate upper-bound counts"]
            and "`{CDR}." + FITBIT_ACTIVITY_TABLE + "`" in sql_a["pre-gate upper-bound counts"],
            "and both Fitbit tables named in the query are the two the probe verified")

    # ---- 1b. the fusion ARM reads all qualifying evidence, add-on codes included -------
    # This section evaluates the EMITTED predicate text against synthetic same-day bundles, so
    # a revert of the fusion flag goes red here rather than passing against a retyped copy of
    # whatever the flag currently says.
    episodes_sql = episodes_cte_sql()
    fusion_line = _emitted_line(episodes_sql, "AS has_fusion")
    having_line = _emitted_line(episodes_sql, "HAVING LOGICAL_OR")
    _expect("NOT s.is_add_on" not in fusion_line,
            "the fusion flag carries no add-on filter, which is the DAG's reading and now this "
            "module's: build_all.sql computes LOGICAL_OR(procedure_class = 'fusion') over all "
            "qualifying records and so does this")
    _expect("NOT s.is_add_on" in having_line,
            "and the operation-exists rule still requires a record that is not an add-on, so "
            "reading the arm from add-ons did not weaken the rule that admits the episode")
    _expect(ADD_ON_FUSION_CODES == 14 and len(_ADD_ON_ROWS) == 16,
            "fourteen of the sixteen add-on and instrumentation codes carry the fusion class, "
            "which is the evidence the arm decision rests on rather than a rounding error")

    # A decompression primary plus one add-on arthrodesis code, and NO primary arthrodesis code
    # on the record: the coding-capture gap, and the only episode shape on which the filtered
    # and unfiltered readings disagree.
    add_on_only_fusion = (_record("lumbar", "decompression", False),
                          _record("unspecified", "fusion", True))
    _expect(_logical_or(having_line, add_on_only_fusion),
            "the bundle is an operation, on the strength of its non-add-on decompression "
            "primary, so the arm decision is reached at all")
    _expect(_logical_or(fusion_line, add_on_only_fusion),
            "and the episode is a FUSION on the strength of the add-on alone, because the "
            "missing primary arthrodesis code is a coding-capture gap and the add-on is the "
            "only evidence the fusion happened. This is the assertion a revert fails")

    # The add-on rule itself, unchanged and tested in both directions.
    instrumentation_only = (_record("unspecified", "fusion", True),)
    _expect(not _logical_or(having_line, instrumentation_only),
            "a bundle of instrumentation alone is still not an operation, so it is not counted "
            "at all and no arm is ever chosen for it")
    _expect(_logical_or(fusion_line, instrumentation_only),
            "even though the fusion flag would call it a fusion: the two predicates answer "
            "different questions and the operation rule runs first")
    decompression_only = (_record("lumbar", "decompression", False),)
    _expect(not _logical_or(fusion_line, decompression_only),
            "an episode with no fusion evidence of any kind is still a decompression")
    fusion_primary = (_record("lumbar", "fusion", False),
                      _record("lumbar", "decompression", False))
    _expect(_logical_or(fusion_line, fusion_primary),
            "and fusion with decompression is fusion, which is plan section 2.4 and which "
            "LOGICAL_OR gives for free")

    # The REGION half keeps its add-on filter, and here is why it needs no change.
    for region in ("cervical", "thoracic", "lumbar"):
        region_line = _emitted_line(episodes_sql, "AS has_" + region)
        _expect(not _logical_or(region_line, instrumentation_only),
                f"an add-on carries no {region} evidence, so it cannot create that stratum")
    cervical_line = _emitted_line(episodes_sql, "AS has_cervical")
    _expect(_logical_or(cervical_line, (_record("cervical", "decompression", False),
                                        _record("unspecified", "fusion", True))),
            "and an add-on beside a cervical primary cannot override the cervical assignment, "
            "because every add-on in the locked set is tagged unspecified")
    _expect(all(row["region_primary"] == "unspecified"
                and row["region_mirrored"] == "unspecified" for row in _ADD_ON_ROWS),
            "which is a measured fact about the locked set and not an assumption: it is "
            "asserted at import, and it is why the region half did not follow the fusion half")

    # ---- 2. the tier decision, at every protocol boundary ------------------------------
    for events, tier in ((0, 4), (19, 4), (20, 3), (21, 3), (49, 3),
                         (50, 2), (51, 2), (99, 2), (100, 1), (101, 1), (5000, 1)):
        _expect(tier_for_events(events)["tier"] == tier,
                f"{events} events sit in tier {tier}")
    _expect(arm_decision(49)["aim A foreclosed"], "49 forecloses the early-warning arm")
    _expect(not arm_decision(50)["aim A foreclosed"], "exactly 50 does not")
    _expect(arm_decision(50)["build matched sampling"], "50 permits the matched branch")
    _expect(not arm_decision(49)["build matched sampling"], "49 does not")
    _expect(arm_decision(19)["best attainable tier"] == 4, "19 can reach no better than tier 4")
    _expect(arm_decision(20)["best attainable tier"] == 3, "exactly 20 reaches tier 3")

    # ---- 3. the section 2.7 gap responses, at and across every threshold ---------------
    _expect(fusion_gap_response(0, 400)["branch"] == "measured zero", "a measured zero is named")
    _expect(not fusion_gap_response(0, 400)["amend"], "a measured zero amends nothing")
    _expect(not fusion_gap_response(20, 400)["amend"], "exactly 5% does not amend")
    _expect(fusion_gap_response(21, 400)["amend"], "just above 5% amends")
    _expect(not fusion_gap_response(1, 400)["amend"], "well below 5% does not amend")
    _expect(fusion_gap_response(400, 400)["amend"], "a wholly misfiled arm amends")
    _expect(fusion_gap_response(20, 400)["share"] == FUSION_GAP_THRESHOLD,
            "the boundary share is exactly the threshold, in exact arithmetic")
    _expect(decompression_gap_response(0, 400)["branch"] == "measured zero", "the zero branch")
    _expect(not decompression_gap_response(0, 400)["amend"], "a measured zero amends nothing")
    # C / (C + D) = 10% exactly at C = 40, D = 360.
    _expect(decompression_gap_response(40, 360)["share"] == DECOMPRESSION_GAP_THRESHOLD,
            "the boundary share is exactly one tenth")
    _expect(not decompression_gap_response(40, 360)["amend"], "exactly 10% does not amend")
    _expect(decompression_gap_response(41, 360)["amend"], "just above 10% amends")
    _expect(not decompression_gap_response(1, 360)["amend"], "well below 10% does not amend")

    decompression_frame = _split_frame(candidate=40, cpt=120, pcs=200, both=40)
    fusion_frame = _split_frame(candidate=60, cpt=140, pcs=180, both=40,
                                misfiled=21, fusion_shape=True)
    gaps = gap_measurements(decompression_frame, fusion_frame)
    _expect(gaps["locked cervical decompression persons"] == 360, "D sums the three locked rows")
    _expect(gaps["invisible cervical decompression persons"] == 40, "C is the candidate row")
    _expect(gaps["misfiled cervical fusion persons"] == 21, "M is the misroute column")
    _expect(decompression_frame["evidence_path"].iloc[0] == CANDIDATE_ONLY_PATH,
            "the decision-critical row arrives first, and nothing reads it by position")
    shuffled = decompression_frame.iloc[[2, 0, 3, 1]].reset_index(drop=True)
    _expect(gap_measurements(shuffled, fusion_frame) == gaps,
            "the measurement is unchanged by row order, because rows are found by label")
    _expect_raises(
        PreGateError,
        lambda: gap_measurements(decompression_frame,
                                 _split_frame(candidate=60, cpt=1, pcs=1, both=1,
                                              misfiled=9999, fusion_shape=True)),
        "a misfiled count larger than the locked count is a stop condition",
    )
    _expect_raises(
        PreGateError,
        lambda: gap_measurements(_split_frame(candidate=0, cpt=0, pcs=0, both=0), fusion_frame),
        "a cervical decompression split that found nobody at all is a stop condition",
    )
    empty_candidate = decompression_frame[
        decompression_frame["evidence_path"] != CANDIDATE_ONLY_PATH]
    _expect(gap_measurements(empty_candidate, fusion_frame)[
        "invisible cervical decompression persons"] == 0,
        "an absent candidate row is a measured zero, not a failure")

    # ---- 4. the stratified table, its suppression and its partition guard --------------
    wide = wide_counts(_uniform_counts_frame((100, 80, 60, 40)), "n_episodes")
    _expect(int(wide.loc[ALL_REGIONS_LABEL, ALL_GROUPS_LABEL]) == 100 * len(REGION_LABELS) * 2,
            "the grand margin is summed from exact integers")
    _expect(int(wide.loc["Cervical", ALL_GROUPS_LABEL]) == 200, "a row margin is exact")

    thin = _uniform_counts_frame((100, 80, 60, 40))
    thin.loc[(thin["region_stratum"] == "cervical")
             & (thin["procedure_group"] == "fusion"), "n_episodes"] = 3
    wide_thin = wide_counts(thin, "n_episodes")
    mask = suppression_mask(wide_thin)
    _expect(bool(mask.loc["Cervical", "Fusion"]), "a thin stratum is suppressed")
    _expect(bool(mask.loc["Cervical", "Decompression"]),
            "its partner is suppressed with it, or the row total would recover it")
    _expect(not bool(mask.loc["Cervical", ALL_GROUPS_LABEL]),
            "the row's own total survives; it is not a member of the partition")
    _expect(not bool(mask.loc[ALL_REGIONS_LABEL, "Fusion"]),
            "a healthy margin is not suppressed by a thin cell beneath it")
    display_thin = render_wide(wide_thin, mask)
    _expect(is_suppressed(display_thin.loc["Cervical", "Fusion"]), "the sentinel is written")
    _expect(partition_violations(display_thin) == [],
            "the partition guard clears the suppressed table in both directions")

    # The vertical direction on its own: one region column thin, everything else healthy.
    vertical = _uniform_counts_frame((100, 80, 60, 40))
    vertical.loc[(vertical["region_stratum"] == "thoracic only"), "n_episodes"] = 2
    wide_vertical = wide_counts(vertical, "n_episodes")
    mask_vertical = suppression_mask(wide_vertical)
    hidden_fusion = [r for r in REGION_LABELS if bool(mask_vertical.loc[r, "Fusion"])]
    _expect(len(hidden_fusion) >= 2,
            "one suppressed region alone would be recoverable, so a second goes with it")
    _expect(partition_violations(render_wide(wide_vertical, mask_vertical)) == [],
            "the column direction clears too")

    # And the guard itself must be able to fail: a hand-built table with exactly one hole.
    broken = render_wide(wide, suppression_mask(wide))
    broken.loc["Cervical", "Fusion"] = SUPPRESSED
    _expect(len(partition_violations(broken)) > 0,
            "one suppressed member beside a disclosed total is refused, not tolerated")

    zeros = wide_counts(_uniform_counts_frame((0, 0, 0, 0)), "n_acute_care")
    _expect(not suppression_mask(zeros).to_numpy().any(),
            "a true zero is an absence, not a small cell, and is never suppressed")

    _expect_raises(
        PreGateError,
        lambda: wide_counts(_counts_frame({("sacral", "fusion"): (1, 1, 1, 1)}), "n_episodes"),
        "a stratum this module does not know is a stop condition",
    )

    # ---- 5. the whole run, against a fake runtime --------------------------------------
    counts_frame = _counts_frame({
        ("cervical", "fusion"): (900, 300, 120, 60),
        ("cervical", "decompression"): (700, 240, 100, 44),
        ("lumbar", "fusion"): (1500, 500, 220, 90),
        ("lumbar", "decompression"): (1300, 420, 180, 70),
        ("cervical and lumbar", "fusion"): (120, 44, 30, 4),
        ("cervical and lumbar", "decompression"): (90, 40, 26, 3),
        ("thoracic only", "fusion"): (200, 60, 30, 5),
        ("thoracic only", "decompression"): (60, 24, 22, 2),
        ("unspecified only", "fusion"): (40, 24, 22, 0),
        ("unspecified only", "decompression"): (80, 30, 24, 1),
    })
    calls: list[tuple[str, float, str]] = []

    def fake_price(sql: str) -> float:
        return {"concept set resolution": 0.4, "cervical decompression gap": 7.1,
                "cervical fusion gap": 7.2, "pre-gate upper-bound counts": 8.0}[
            _key_of(sql, ids)]

    def fake_query(sql: str, *, max_gb: float, note: str = "") -> pd.DataFrame:
        key = _key_of(sql, ids)
        calls.append((key, max_gb, note))
        return {"concept set resolution": _concept_frame(),
                "cervical decompression gap": decompression_frame,
                "cervical fusion gap": fusion_frame,
                "pre-gate upper-bound counts": counts_frame}[key]

    result = run_pregate(probe_result=passing_probe, q_guarded=fake_query, dry_run_gb=fake_price,
                         show_report=False)
    _expect([c[0] for c in calls] == list(QUERY_KEYS), "all four queries ran, in plan order")
    _expect(all(c[1] == PLANNED_MAX_GB[c[0]] for c in calls),
            "every call carried the cap sized for it")
    _expect(all(c[2] for c in calls), "every call named its cost-log entry")
    _expect(result["headline"]["n_acute_care"] == 279, "the acute-care ceiling is the margin")
    _expect(result["decision"]["best attainable tier"] == 1, "279 leaves tier 1 attainable")
    _expect(not result["decision"]["aim A foreclosed"], "and does not foreclose the arm")
    _expect(str(result["decompression split"]["n_persons"].iloc[0]) == "40",
            "a person count is rounded before it can be printed")
    report = result["report"]
    _expect("UPPER BOUND" in report and "HARD STOP" in report, "the report says both")
    _expect("DO NOT BUILD THE MATCHED-SAMPLING BRANCH" not in report,
            "the arm is not declared dead on a ceiling that does not foreclose it")
    _expect(SUPPRESSED in report, "the thin strata print as suppressed rather than as numbers")
    flat_report = " ".join(report.split())
    _expect("add-on and instrumentation codes included" in flat_report,
            "the report tells the human that fusion status reads all qualifying evidence, "
            "because a reader comparing these strata against the DAG's must know they agree")
    _expect("A bundle of instrumentation alone is not an operation" in flat_report,
            "and that the add-on rule that admits an episode is unchanged")
    _assert_house_prose(report)

    thin_events = _counts_frame({
        ("cervical", "fusion"): (900, 300, 120, 10),
        ("cervical", "decompression"): (700, 240, 100, 8),
        ("lumbar", "fusion"): (1500, 500, 220, 9),
        ("lumbar", "decompression"): (1300, 420, 180, 6),
        ("cervical and lumbar", "fusion"): (120, 44, 30, 0),
        ("cervical and lumbar", "decompression"): (90, 40, 26, 0),
        ("thoracic only", "fusion"): (200, 60, 30, 0),
        ("thoracic only", "decompression"): (60, 24, 22, 0),
        ("unspecified only", "fusion"): (40, 24, 22, 0),
        ("unspecified only", "decompression"): (80, 30, 24, 0),
    })
    dead = assemble("resolved", decompression_frame, fusion_frame, thin_events)
    _expect(dead["headline"]["n_acute_care"] == 33, "the thin ceiling is 33 events")
    _expect(dead["decision"]["aim A foreclosed"], "33 is below the early-warning floor")
    _expect("AIM A IS DEAD" in dead["report"], "and the report says so plainly")
    _expect("DO NOT BUILD THE MATCHED-SAMPLING BRANCH" in dead["report"],
            "and says what not to build")
    _assert_house_prose(dead["report"])

    # ---- 6. the budget guard ------------------------------------------------------------
    # Every one of these is UNDER its own cap, so what refuses the run is the aggregate budget
    # and not a per-query cap.  The two guards are tested separately on purpose.
    def expensive(sql: str) -> float:
        return {"concept set resolution": 1.9, "cervical decompression gap": 11.0,
                "cervical fusion gap": 11.0, "pre-gate upper-bound counts": 11.0}[
            _key_of(sql, ids)]

    _expect_raises(
        PreGateBudgetExceeded,
        lambda: run_pregate(probe_result=passing_probe, q_guarded=fake_query, dry_run_gb=expensive,
                            show_report=False),
        "four queries at 9 GiB each exceed the budget and nothing executes",
    )
    before = len(calls)
    try:
        run_pregate(probe_result=passing_probe, q_guarded=fake_query, dry_run_gb=expensive,
                    show_report=False)
    except PreGateBudgetExceeded:
        pass
    _expect(len(calls) == before, "a refused budget executes nothing at all")
    _expect_raises(
        PreGateBudgetExceeded,
        lambda: run_pregate(probe_result=passing_probe, q_guarded=fake_query,
                            dry_run_gb=lambda sql: 100.0, show_report=False,
                            budget_gb=10_000.0),
        "a single query above its own cap is refused even when the budget would allow it",
    )
    _expect_raises(
        PreGateError,
        lambda: run_pregate(probe_result=passing_probe, q_guarded=None, dry_run_gb=None,
                            show_report=False),
        "with no configured query path the step refuses rather than finding its own",
    )

    # ---- 7. the house prose guard is able to fail ---------------------------------------
    _expect_raises(PreGateError, lambda: _assert_house_prose("a" + EM_DASH + "b"),
                   "an em-dash in a rendered string is a stop condition")
    _expect_raises(PreGateError, lambda: _assert_house_prose("see region_stratum"),
                   "a snake-case token in a rendered string is a stop condition")

    print("=" * 86)
    print("02_pregate.py SELF-TEST: PASS")
    print("=" * 86)
    print(f"  assertions executed        : {_ASSERTIONS}")
    print(f"  queries built              : {', '.join(QUERY_KEYS)}")
    print( "  every emitted query        : carries {CDR} only, no hardcoded project or dataset,")
    print( "                               no randomness, no data-definition statement, and no")
    print( "                               {DERIVED}, because this step materializes nothing")
    print(f"  per-query caps, GiB        : "
          f"{', '.join(f'{k} {v:,.1f}' for k, v in PLANNED_MAX_GB.items())}")
    print(f"  aggregate budget           : {PREGATE_BUDGET_GB:,.1f} GiB, about "
          f"${PREGATE_BUDGET_GB / 1024 * USD_PER_TIB:,.2f}, priced before anything executes")
    print(f"  tier boundaries tested     : {TIER_3_MIN_EVENTS}, {TIER_2_MIN_EVENTS} and "
          f"{TIER_1_MIN_EVENTS} events, each exactly and on both sides")
    print(f"  gap thresholds tested      : {float(FUSION_GAP_THRESHOLD):.0%} misfiled and "
          f"{float(DECOMPRESSION_GAP_THRESHOLD):.0%} missing, each exactly and on both sides")
    print( "  the locked concept set     : measured, never amended; the assertion now has a")
    print( "                               production caller for the first time")
    print(f"  fusion arm predicate       : LOGICAL_OR(procedure class = fusion) over ALL "
          f"qualifying")
    print(f"                               records, add-ons included, which is what "
          f"build_all.sql")
    print(f"                               reads. {ADD_ON_FUSION_CODES} of the "
          f"{len(_ADD_ON_ROWS)} add-on and instrumentation codes")
    print( "                               carry the fusion class, and the two readings differ")
    print( "                               only when the primary arthrodesis code is missing")
    print( "                               from the record, which is a coding-capture gap")
    print( "  operation-exists predicate : UNCHANGED and separate. A same-day bundle is still")
    print( "                               an operation only with a non-add-on record on it,")
    print( "                               and a bundle of instrumentation alone is still not")
    print( "                               counted. Tested on an episode whose only fusion")
    print( "                               evidence is an add-on code, against the EMITTED text")
    print( "  region predicates          : add-on filter KEPT, and it changes nothing: every")
    print( "                               add-on is tagged unspecified in both region columns,")
    print( "                               asserted at import, so none can override a region")
    print(f"  borrowed from the probe    : valid wear minutes {VALID_WEAR_DAY_MINUTES}, zone "
          f"minute column {HR_ZONE_MINUTE_COLUMN},")
    print(f"                               Fitbit tables "
          f"{list(probe_module.FITBIT_TABLES_REQUIRED)}, all from")
    print(f"                               {_PROBE_FILENAME} and none of them retyped here.")
    print( "                               Each checked against the probe's own value, so a")
    print( "                               divergence fails here and not in a session")
    print( "  stratified table           : suppressed cells are the expected outcome, and both")
    print( "                               directions clear the partition refusal class, now")
    print( "                               with every column declared as a count column")
    print(f"  visit concept ids          : {list(ED_AND_INPATIENT_VISIT_CONCEPT_IDS)}, imported "
          f"from {_PROBE_FILENAME}, never")
    print(f"                               retyped. Emergency {list(ED_VISIT_CONCEPT_IDS)}, "
          f"inpatient {list(INPATIENT_VISIT_CONCEPT_IDS)};")
    print( "                               262 is in both sets and once in the union, because")
    print( "                               an emergency presentation that became an admission")
    print( "                               is one event")
    print( "  probe verdict              : required. run_pregate refuses an absent result, a")
    print( "                               result carrying no verdict, and a false verdict")
    print( "  cloud access required      : none")


def _concept_frame() -> pd.DataFrame:
    """The 852-row concept frame, rebuilt from the concept-set module's own registry.

    Built from `registry_rows()` rather than typed out, so the self-test cannot pass against a
    frame this module invented.  The ICD-10-PCS stems are expanded to their locked concept
    counts by repeating each stem, which is what the real resolution returns.
    """
    rows: list[dict[str, Any]] = []
    registry = cs_spine.registry_rows()
    pcs_fusion = [r for r in registry if r["vocabulary_id"] == "ICD10PCS"
                  and r["procedure_class"] == "fusion"]
    pcs_dec = [r for r in registry if r["vocabulary_id"] == "ICD10PCS"
               and r["procedure_class"] == "decompression"]
    concept_id = 1
    def emit(entry: Mapping[str, Any], code: str) -> None:
        nonlocal concept_id
        rows.append({
            "concept_id": concept_id,
            "vocabulary_id": entry["vocabulary_id"],
            "concept_code": code,
            "concept_name": "synthetic",
            "region": entry["region_primary"],
            "procedure_class": entry["procedure_class"],
            "is_add_on": entry["is_add_on"],
        })
        concept_id += 1
    for entry in registry:
        if entry["vocabulary_id"] == "CPT4":
            emit(entry, entry["code"])
    for group, target in ((pcs_fusion, cs_spine.EXPECTED_PCS_FUSION_CONCEPTS),
                          (pcs_dec, cs_spine.EXPECTED_PCS_DECOMPRESSION_CONCEPTS)):
        for index in range(target):
            entry = group[index % len(group)]
            emit(entry, entry["code"] + str(index).zfill(3))
    return pd.DataFrame(rows)


def _key_of(sql: str, visit_concept_ids: Sequence[Any]) -> str:
    """Which of the four queries this text is, for the self-test's fake runtime."""
    for key, text in build_sql(visit_concept_ids=visit_concept_ids).items():
        if text == sql:
            return key
    raise AssertionError("the fake runtime was handed a query this module did not build")


if __name__ == "__main__":
    _run_self_test()
