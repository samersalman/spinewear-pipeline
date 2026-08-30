#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""probe6c_admitting_source.py -- the last read rung 4's route 1 had not had.

`probe6b_elective_routes.py` established that `visit_source_value` carries no elective wording on
either acute-care encounters or inpatient visits, and that BOTH `visit_occurrence` and
`visit_detail` carry an `admitting_source_concept_id`, which is the plan's own wording for route 1
and had never been read.  This reads it, on both tables, and classifies every concept name.

THE ANSWER IT RETURNED, 2026-08-30, and the reason the route retires: 73 distinct concepts on
`visit_occurrence` and 100 on `visit_detail`, ZERO of them reading elective or scheduled.  Both
vocabularies encode POINT OF ORIGIN -- Home, Clinic or physicians office, Emergency Room Hospital,
Transfer from a Hospital, Skilled Nursing Facility -- and not ADMISSION TYPE.  A vocabulary that
does not carry the distinction cannot be made to yield it by a better pattern, which is what makes
this a finding rather than another deferral.

Run from the repository root.  Every count is rounded and floor-tested before printing.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PATTERN = re.compile(r"elect|sched", re.IGNORECASE)
MAX_GB = 6.0


def main() -> int:
    spec = importlib.util.spec_from_file_location("probe01", HERE / "01_probe.py")
    probe = importlib.util.module_from_spec(spec)
    sys.modules["probe01"] = probe
    spec.loader.exec_module(probe)
    ns = probe._bootstrap_config(probe._find_config_notebook())

    q, cdr = ns["q_guarded"], ns["WORKSPACE_CDR"]
    round20, disclosable = ns["round20"], ns["disclosable"]

    reads = [
        ("visit_occurrence.admitting_source_concept_id on inpatient visits", f"""
            SELECT IFNULL(c.concept_name, '(unmapped)') AS nm, COUNT(*) AS n
            FROM `{cdr}.visit_occurrence` v
            LEFT JOIN `{cdr}.concept` c ON c.concept_id = v.admitting_source_concept_id
            WHERE v.visit_concept_id IN (9201, 262, 8717, 38004279)
            GROUP BY nm ORDER BY n DESC LIMIT 100"""),
        ("visit_detail.admitting_source_concept_id, all rows", f"""
            SELECT IFNULL(c.concept_name, '(unmapped)') AS nm, COUNT(*) AS n
            FROM `{cdr}.visit_detail` d
            LEFT JOIN `{cdr}.concept` c ON c.concept_id = d.admitting_source_concept_id
            GROUP BY nm ORDER BY n DESC LIMIT 100"""),
    ]

    for label, sql in reads:
        print("\n" + "=" * 84)
        print(label)
        print("=" * 84)
        frame = q(sql, note=label, max_gb=MAX_GB)
        if frame is None or len(frame) == 0:
            print("  nothing returned")
            continue
        elective_total = 0
        for _, row in frame.iterrows():
            name, n = str(row["nm"]), int(row["n"])
            elective = bool(PATTERN.search(name))
            if elective:
                elective_total += n
            if disclosable(n):
                mark = "ELECTIVE" if elective else ""
                print(f"  {name[:56]:<58}{round20(n):>12}  {mark}")
        shown = round20(elective_total) if disclosable(elective_total) else "at or below the floor"
        print(f"  -> {len(frame)} distinct concept(s); reading elective or scheduled: {shown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
