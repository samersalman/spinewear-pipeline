# spinewear-pipeline

Analysis code for a wearable-linked cohort study of ambulatory recovery after elective cervical and
lumbar spine surgery, run inside the *All of Us* Research Program Controlled Tier.

**This repository exists so the code can be cloned into a Controlled Tier analysis VM.** The Controlled
Tier network policy blocks internet access for batch jobs and keeps it for interactive tools, so a
public clone in the notebook terminal is the transfer route, and one 40-character commit SHA is the
integrity check.

## What is not here, and cannot be

No participant data, of any kind, at any level of aggregation. No query results, no counts, no
figures, no manuscript. Everything in this repository is code, a prespecified analysis plan, and an
export contract. Nothing in it has been run against the Controlled Tier at the time of writing, and
nothing that is ever run against it will be committed here: results leave the workspace only as
aggregates that clear the program's dissemination floor, and they leave through a different route.

## Layout

| Path | What it is |
|---|---|
| `pipeline/00_config.ipynb` | Workbench configuration, resource resolution, guarded query helpers |
| `pipeline/disclosure.py` | The suppression rules, unit-tested. Counts round to 20; cells below the floor are refused |
| `pipeline/cs_spine.py` | The locked 852-concept spine procedure set, region-tagged |
| `pipeline/01_probe.py` | Runtime probes: table existence, CDR location, column layout, write permission |
| `pipeline/02_pregate.py` | The cheap upper-bound counts that decide whether the study is feasible |
| `pipeline/build_all.sql` | The derived-table DAG as a BigQuery stored procedure |
| `pipeline/03_cohort.py` | Episodes, exclusions, and the nineteen-rung attrition ladder |
| `pipeline/04_features.py` | Valid wear days, preoperative baseline, daily deficit, risk sets |
| `pipeline/05_analysis_drd.py` | The primary endpoint: daily-deficit model, g-computation, bootstrap |
| `pipeline/06_analysis_gate.py` | The tier-gated conditional logit and discrete-time risk model |
| `pipeline/07_export.py` | The only module that writes an export bundle, and the only one permitted to |
| `prespecification/ANALYSIS-PLAN.md` | The analysis plan. Locked and hashed before any count was seen |
| `prespecification/PLAN-HASH.txt` | The lock record. Written by `lock_plan.py`, never by hand |
| `prespecification/EXPORT-CONTRACT.md` | What an export bundle must contain and what it may never contain |
| `CLAUDE.md` | The project constitution: hard rules and stop conditions |

## The prespecification lock

`ANALYSIS-PLAN.md` is locked at version 1.5. Verify it rather than trusting this sentence:

```
python3 prespecification/lock_plan.py --check
```

Exit 0 means the plan is byte-identical to the record. Exit 1 means it has been edited since the lock,
which is a stop condition and not a discrepancy to explain away. The plan has been amended five times
and every amendment was made before any count, coefficient, curve or P value from this study was
observed; the amendment log is section 13 of the plan itself.

## Disclosure

Every count that leaves the analysis workspace is rounded to a multiple of 20, and any cell whose true
value falls between 1 and 19 is suppressed rather than rounded. Where a set of counts partitions a
disclosed total, one suppressed member forces a second, so that a hidden cell cannot be recovered by
subtraction. `07_export.py` refuses to write a bundle that violates either rule, and `disclosure.py`
carries the tests.
