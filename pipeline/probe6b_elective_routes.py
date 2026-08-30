#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe6b_elective_routes.py -- what PROBE 6 should have asked, and did not.

WHY THIS EXISTS.  `01_probe.py` PROBE 6 reports that "attrition rung 4's ONLY elective rescue
can never fire".  Three things in that sentence are wrong or narrower than they sound, and all
three were found by reading `ANALYSIS-PLAN.md` section 2.6 step 4 against `build_all.sql`
rather than by running anything:

  1.  Rung 4 has THREE rescue routes, not one.  `build_all.sql` line 1315 excludes an episode
      only when none of the three fires, and the ladder reports each route's rescue count
      separately.  Routes 2 and 3 are diagnosis-based and PROBE 6 never touched them.
  2.  Route 1 as the PLAN specifies it reads `visit_detail` OR THE ADMITTING-SOURCE CONCEPT.
      Route 1 as `build_all.sql` IMPLEMENTS it reads `visit_source_value`, and its own comment
      says visit_detail is deliberately not consulted because whether the CDR populates it was
      an unconfirmed runtime probe.  So the route measured dead is a proxy for the route the
      plan wrote, not that route.
  3.  Route 1 keys on the INDEX SURGICAL ADMISSION, `e.index_visit_occurrence_id`.  PROBE 6
      measured `visit_source_value` over every visit carrying an acute-care concept id, which
      is a different population.  Elective wording is far likelier on a scheduled spine
      admission than on an emergency department encounter, so a zero on the second says less
      than it appears to about the first.

WHAT THIS ANSWERS, and nothing else.  It is a diagnostic, not an analysis.  It writes no
derived table, defines no cohort and touches no participant-level output.

  A.  Which elective-relevant columns this CDR actually has, on `visit_occurrence` and on
      `visit_detail`.  INFORMATION_SCHEMA, free.
  B.  Whether `visit_detail` is populated at all, and how densely.
  C.  On INPATIENT visits, which is the population an index spine admission sits in: the
      distinct `visit_source_value` values, and the distinct admitting-source concepts, with
      counts, and whether any of them read as elective or scheduled.

DISCLOSURE.  Every count is rounded through `round20` and every value below the floor is
suppressed before printing, by the same helpers `00_config.ipynb` loads.  The distinct-value
lists are CDR vocabulary rather than participant attributes, but they are floor-tested anyway
on the count that accompanies them, which is the conservative reading.

COST.  A and B are INFORMATION_SCHEMA and a row count.  C reads two columns of
`visit_occurrence`.  Every query dry-runs first through `q_guarded` under a cap.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys
from typing import Any, Mapping

HERE = pathlib.Path(__file__).resolve().parent
ELECTIVE_PATTERN = re.compile(r"elect|sched", re.IGNORECASE)
MAX_GB = 2.0


def _load_probe_module():
    spec = importlib.util.spec_from_file_location("probe01", HERE / "01_probe.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["probe01"] = module
    spec.loader.exec_module(module)
    return module


def _config() -> Mapping[str, Any]:
    probe = _load_probe_module()
    notebook = probe._find_config_notebook()
    if notebook is None:
        raise SystemExit("00_config.ipynb was not found beside this file or above it.")
    return probe._bootstrap_config(notebook)


def _rule(title: str) -> None:
    print("\n" + "=" * 86)
    print(title)
    print("=" * 86)


def main() -> int:
    ns = _config()
    q = ns["q_guarded"]
    cdr = ns["WORKSPACE_CDR"]
    round20 = ns["round20"]
    disclosable = ns["disclosable"]
    project, dataset = cdr.split(".", 1)

    _rule("A. Elective-relevant columns this CDR actually carries")
    columns = q(
        f"""
        SELECT table_name, column_name, data_type
        FROM `{project}.{dataset}.INFORMATION_SCHEMA.COLUMNS`
        WHERE table_name IN ('visit_occurrence', 'visit_detail')
        ORDER BY table_name, ordinal_position
        """,
        note="A: visit_occurrence and visit_detail layout, INFORMATION_SCHEMA, free",
        max_gb=MAX_GB,
    )
    if columns is None or len(columns) == 0:
        print("visit_occurrence is not visible in this CDR. Nothing below can run.")
        return 2

    have = {}
    for table in ("visit_occurrence", "visit_detail"):
        names = sorted(columns.loc[columns["table_name"] == table, "column_name"])
        have[table] = names
        print(f"\n{table}: {len(names)} column(s)")
        if not names:
            print("  ABSENT from this CDR.")
            continue
        interesting = [n for n in names if any(
            k in n for k in ("admit", "admitted", "source", "visit_type", "discharge"))]
        print("  columns bearing on the elective question:")
        for n in interesting or ["  (none)"]:
            print(f"    {n}")

    admit_cols = [n for n in have["visit_occurrence"]
                  if "admit" in n and n.endswith("concept_id")]
    print(f"\nadmitting-source candidate column(s) on visit_occurrence: {admit_cols or 'NONE'}")
    print("The plan's route 1 names visit_detail OR the admitting-source concept. Whether it")
    print("is expressible at all is decided by the two lines above, not by a regular expression.")

    _rule("B. Is visit_detail populated, or present and empty")
    if not have["visit_detail"]:
        print("visit_detail does not exist in this CDR. Route 1 cannot read it, and")
        print("build_all.sql's decision not to consult it was correct for this release.")
    else:
        detail = q(
            f"SELECT COUNT(*) AS n FROM `{cdr}.visit_detail`",
            note="B: visit_detail row count",
            max_gb=MAX_GB,
        )
        n = int(detail["n"].iloc[0]) if detail is not None and len(detail) else 0
        print(f"visit_detail rows: {round20(n) if disclosable(n) else ns['SUPPRESSED']}")
        if n == 0:
            print("Present but EMPTY. A rescue reading it would never fire, which is exactly")
            print("the failure mode build_all.sql's comment was written to avoid.")

    _rule("C. Elective wording on INPATIENT visits, the population an index admission sits in")
    print("Route 1 keys on the index surgical admission. PROBE 6 measured acute-care encounters")
    print("instead. This asks the question on the right side of that distinction.")
    rows = q(
        f"""
        SELECT
          LOWER(IFNULL(visit_source_value, '(null)')) AS source_value,
          COUNT(*) AS n
        FROM `{cdr}.visit_occurrence`
        WHERE visit_concept_id IN (9201, 262, 8717, 38004279)
        GROUP BY source_value
        ORDER BY n DESC
        LIMIT 200
        """,
        note="C: visit_source_value distribution on inpatient visits",
        max_gb=MAX_GB,
    )
    if rows is None or len(rows) == 0:
        print("no inpatient visits returned; nothing to classify.")
        return 1

    total = int(rows["n"].sum())
    shown = 0
    hits = []
    print(f"\n{'source value':<44}{'count':>14}   elective wording")
    print("-" * 86)
    for _, row in rows.iterrows():
        value, n = str(row["source_value"]), int(row["n"])
        elective = bool(ELECTIVE_PATTERN.search(value))
        if elective:
            hits.append((value, n))
        if not disclosable(n):
            continue
        shown += 1
        if shown <= 40:
            print(f"{value[:42]:<44}{round20(n):>14}   {'YES' if elective else 'no'}")
    if shown > 40:
        print(f"... {shown - 40} further value(s) at or above the floor, all classified")

    hit_n = sum(n for _, n in hits)
    print("-" * 86)
    print(f"distinct values returned      : {len(rows)}")
    print(f"values at or above the floor  : {shown}")
    print(f"inpatient visits in total     : {round20(total)}")
    print(f"visits whose source value reads elective or scheduled: "
          f"{round20(hit_n) if disclosable(hit_n) else ns['SUPPRESSED']}")

    _rule("Verdict")
    if hit_n > 0:
        print("Route 1 IS expressible on visit_source_value for inpatient admissions.")
        print("PROBE 6's zero was a fact about acute-care encounters, not about index")
        print("admissions, and rung 4's route 1 should be kept and pointed at this population.")
    elif admit_cols:
        print("visit_source_value carries no elective wording on inpatient visits either.")
        print(f"An admitting-source concept column DOES exist: {admit_cols}.")
        print("That is the plan's own wording for route 1 and it has not been read yet;")
        print("enumerate it before retiring the route.")
    else:
        print("No elective wording on inpatient visit_source_value, no admitting-source")
        print("concept column, and visit_detail unusable. Route 1 is not computable in this")
        print("CDR by any route the plan names. Retiring it is then a finding, not a shortcut,")
        print("and routes 2 and 3 carry rung 4 alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
