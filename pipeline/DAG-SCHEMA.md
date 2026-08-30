# DAG-SCHEMA.md: the derived-table contract

**This document is the contract.** `pipeline/03_cohort.py` and `pipeline/04_features.py` are written
against it without reading `build_all.sql`, so every column name, type, unit and null convention a
downstream module needs is written down here. If a module needs something this document does not
name, that is a defect in this document, not a licence to guess.

- **Producer:** `pipeline/build_all.sql`, four persistent user-defined functions plus one stored
  procedure, `build_all`.
- **Consumers:** `pipeline/03_cohort.py` (the attrition ladder, the collapse-level decision, the
  gate), `pipeline/04_features.py` (the analysis frames), `pipeline/05_analysis_drd.py`,
  `pipeline/06_analysis_gate.py`, `pipeline/07_export.py` (the only module that writes a file).
- **Nothing in this DAG prints, returns or exports a row.** Everything it writes lives in
  `{DERIVED}` and, apart from two vocabulary tables, is participant-level. See section 6.

---

## 1. Placeholders and names

| Placeholder | Resolves to | Used here |
|---|---|---|
| `{CDR}` | the Controlled Tier CDR dataset, `project.dataset` | yes |
| `{PREP}` | the prep CDR dataset, `project.dataset` | **no** |
| `{DERIVED}` | the workspace project's own spinewear derived dataset | yes |

`{PREP}` is deliberately unused. Its table inventory is an unconfirmed runtime probe, and a DAG that
depends on a dataset nobody has looked at is a DAG that fails on the first real run for a reason that
reads like a permissions error. If a later phase needs it, it is added then and this row changes.

There is no hardcoded project, dataset or bucket anywhere in `build_all.sql`. The workspace project
name is never written in braces, **not even inside a comment**, because `00_config.ipynb`'s `_fill`
raises on any residual `{IDENTIFIER}` after substitution and does not exempt comments.

Placeholders are substituted by `_fill` before submission, so the SQL must be sent as a plain
(non-f) Python string with the braces intact.

---

## 2. The stored procedure

```sql
CALL `{DERIVED}.build_all`(
  junction_map,                 -- STRING
  hr_minute_column,             -- STRING
  device_model_column,          -- STRING
  ed_visit_concept_ids,         -- ARRAY<INT64>
  inpatient_visit_concept_ids,  -- ARRAY<INT64>
  primary_wear_definition,      -- STRING
  start_stage                   -- STRING
);
```

BigQuery `CALL` takes arguments **positionally**, in the order above.

### 2.1 The seven parameters

| # | Parameter | Domain | Where the value comes from |
|---|---|---|---|
| 1 | `junction_map` | `'primary'` or `'mirrored'` | Prespecified. `'primary'` for the main run; `'mirrored'` is the `junctions_mirrored` supplementary sensitivity |
| 2 | `hr_minute_column` | a bare SQL identifier | **RUNTIME PROBE.** `01_probe.py` reads the per-zone minute column name off `heart_rate_summary` |
| 3 | `device_model_column` | a bare SQL identifier, or `''` | **RUNTIME PROBE.** The model string column of the `device` table. `''` means unavailable and makes every episode take device family `other_or_unknown` |
| 4 | `ed_visit_concept_ids` | non-empty `ARRAY<INT64>` | **RUNTIME PROBE.** `01_probe.py` enumerates emergency department `visit_concept_id` values against the CDR's actual distribution |
| 5 | `inpatient_visit_concept_ids` | non-empty `ARRAY<INT64>` | **RUNTIME PROBE.** Same, for inpatient admissions |
| 6 | `primary_wear_definition` | `'primary'` or `'s2'` | `'primary'` unless the zone-partition probe fails, in which case `ANALYSIS-PLAN` 2.1's prespecified contingency applies and the substitution is logged as an amendment |
| 7 | `start_stage` | `''` or a stage name | `''` builds everything. Any of the nineteen table names in section 4 rebuilds from there |

### 2.2 What is NOT a parameter, and why

`SEED = 0` and the sampling salt `'spinewear-v1-risk-set'` are `DECLARE` constants inside the
procedure. `ANALYSIS-PLAN` 4.5 and 10 pin the seed, and a knob that can only break reproducibility is
worse than no knob. Every locked threshold is likewise internal: the 600-minute wear rule and its
four sensitivity variants, the baseline window of days minus 30 to minus 8, the 7-valid-day and
14-calendar-day baseline minimums, the accrual window of post-discharge days 1 to 35, the 90-day Arm
A horizon, the 5-controls-per-case cap, the 3-control-landmarks-per-participant cap, the Charlson
weights, and the fourteen device family names.

### 2.3 What the procedure refuses to do

Every one of these raises rather than producing a table:

1. `junction_map` or `primary_wear_definition` outside its domain.
2. `hr_minute_column` or `device_model_column` that is not a bare identifier. They are interpolated
   into dynamic SQL, and the identifier regex is the whole defence.
3. `heart_rate_summary` missing any of `person_id`, `date` or the probed minute column. **This is the
   check that stops a wrong probe from producing a study in which every wear minute is zero**, which
   reads as total non-wear rather than as a broken probe. The check is against
   `INFORMATION_SCHEMA.COLUMNS` and bills nothing.
4. A named `device_model_column` that does not exist on `device`.
5. Either visit-concept array empty. An empty array would silently make every acute-care event and
   every emergency-department exclusion count zero.
6. `person` missing `sex_at_birth_concept_id`.
7. The exact-median UDF returning the wrong value on an even-length array, an odd-length array or an
   empty array. See section 3.
8. The locked spine concept set not resolving to exactly 852 concepts.
9. The Quan Charlson mapping not resolving all seventeen categories.
10. Summed heart-rate zone minutes exceeding 1,440 on any person-date, unless
    `primary_wear_definition = 's2'`. The zones must partition the day for the sum to be a wear
    figure at all.
11. The attrition ladder failing to close, at any rung or either segment.
12. The ladder not having exactly nineteen rungs.
13. The structurally-uncomputable-landmark flag disagreeing with post-discharge day 1 to 4.
14. `ledger_exclusion_reasons` carrying a step and slug pair that is not a rung.
15. `start_stage` naming something that is not a stage.

---

## 3. The four user-defined functions

They are created as **top-level statements before the procedure**, so they persist in `{DERIVED}` and
are callable from `04_features.py` and from any ad hoc query. Call them rather than reimplementing
them.

| Function | Signature | Returns |
|---|---|---|
| `{DERIVED}.exact_median` | `(xs ARRAY<FLOAT64>) -> FLOAT64` | The exact median. Odd length: the middle element. Even length: the mean of the two middle elements. **Empty array or all-NULL array: NULL, never zero.** NULLs inside the array are dropped before the median is taken |
| `{DERIVED}.exact_median_int` | `(xs ARRAY<INT64>) -> FLOAT64` | The same, over an integer array, so a caller aggregating step counts never has to cast |
| `{DERIVED}.is_valid_wear` | `(wear_minutes INT64, steps INT64, definition STRING) -> BOOL` | The five valid-wear-day rules of `ANALYSIS-PLAN` 2.1. `definition` is `'primary'`, `'s1'`, `'s2'`, `'s3'` or `'s4'`; anything else returns NULL |
| `{DERIVED}.device_family` | `(model STRING) -> STRING` | The fourteen-family device rule of 3.6, as a lowercase slug, or `'other_or_unknown'` |

### Why the median is a function

BigQuery's approximate-quantile function, asked for two quantiles and indexed at offset one, returns
the **upper** of the two middle values on an even-length array. The preoperative baseline `B_i` is
defined as a median, and the proximal exposure `R_72` is a median over a window that carries as few
as **two** valid days, so on `R_72` the even-length case is the ordinary case rather than the edge
case. Using the approximate form would bias every baseline and every two-day proximal window upward,
in the same direction, invisibly. Writing it once as a UDF means no downstream query can reintroduce
it, and the procedure **asserts** the behaviour at the top of every run:

```
exact_median([1.0, 2.0, 4.0, 8.0]) = 3.0     approximate form would give 4.0
exact_median([1.0, 2.0, 4.0])      = 2.0
exact_median([])                   IS NULL   never zero
```

The empty-array convention carries real weight. A zero baseline would make normalized activity
`S / B` infinite and the daily deficit `max(0, 1 - S/B)` silently equal to 1 on every day,
manufacturing a maximal recovery debt out of an absence of data. NULL propagates instead and is
caught and counted at attrition rung 12.

### The five wear thresholds, in one place

| `definition` | Rule | Slug in the sensitivity ladder |
|---|---|---|
| `'primary'` | `wear_minutes >= 600` | (the primary) |
| `'s1'` | `wear_minutes >= 576`, which is 40% of 1,440 | `wear_definition_s1` |
| `'s2'` | `wear_minutes >= 600` **and** `steps >= 100` | `wear_definition_s2` |
| `'s3'` | `wear_minutes >= 480` | `wear_definition_s3` |
| `'s4'` | `wear_minutes >= 720` | `wear_definition_s4` |

A NULL `wear_minutes` means **no `heart_rate_summary` row for that person-date**, which is not the
same claim as zero minutes, and it is never a valid day under any definition.

---

## 4. DAG order, and what a resumed session runs

| # | Table | Reads |
|---|---|---|
| 1 | `build_params` | `{CDR}.observation_period`, the procedure's own arguments |
| 2 | `cs_spine` | `{CDR}.concept`, `build_params` |
| 3 | `cs_condition` | `{CDR}.concept` |
| 4 | `episodes` | `{CDR}.procedure_occurrence`, `{CDR}.visit_occurrence`, `cs_spine`, `build_params` |
| 5 | `hr_daily` | `{CDR}.heart_rate_summary`, `episodes` |
| 6 | `device_daily` | `{CDR}.device`, `episodes` |
| 7 | `fitbit_daily` | `{CDR}.activity_summary`, `hr_daily`, `episodes`, `build_params` |
| 8 | `baseline` | `fitbit_daily`, `episodes`, `build_params` |
| 9 | `episodes_eligible` | `episodes`, `baseline`, `fitbit_daily`, `cs_condition`, `{CDR}.visit_occurrence`, `{CDR}.condition_occurrence`, `{CDR}.observation_period`, `{CDR}.death` |
| 10 | `features` | `episodes_eligible`, `episodes`, `baseline`, `device_daily`, `cs_condition`, `{CDR}.person`, `{CDR}.condition_occurrence`, `{CDR}.measurement` |
| 11 | `drd_daily` | `features`, `fitbit_daily`, `{CDR}.visit_occurrence` |
| 12 | `events` | `features`, `fitbit_daily`, `{CDR}.visit_occurrence` |
| 13 | `landmark_daily` | `drd_daily`, `events`, `fitbit_daily` |
| 14 | `risk_sets` | `events`, `features`, `fitbit_daily` |
| 15 | `attrition` | `episodes`, `episodes_eligible`, `events`, `cs_spine`, `{CDR}.person`, `{CDR}.procedure_occurrence` |
| 16 | `ledger_exclusion_reasons` | `episodes_eligible`, `baseline`, `attrition` |
| 17 | `ledger_wear_by_day` | `drd_daily`, `features` |
| 18 | `ledger_matched_sets` | `risk_sets` |
| 19 | `ledger_variable_missingness` | `features`, `drd_daily`, `events` |

The number in column one is the number the stage guard compares `start_ix` against inside the
procedure. `start_stage = 'features'` rebuilds stages 10 through 19. `build_params` is **always**
rewritten, whatever `start_stage` says, because it is the record of what this run was called with.

### A resumed session

```
%run 00_config.ipynb            resolves {CDR}, {PREP}, {DERIVED} and the CDR location
python3 03_cohort.py --call     dry-runs every stage, prints the bytes, then CALLs
```

Nothing above needs the previous session's compute disk, its `/tmp`, or any parquet. The tables live
in the CDR's own project and outlive the environment. That is the entire reason this file is a stored
procedure rather than a notebook cell: every prior All of Us session in this repo re-materialized
parquets from SQL because the workspace had no writable home, and wrote scratch to the one location
guaranteed to vanish with the compute disk.

Every statement is `CREATE OR REPLACE`, so a re-run overwrites rather than appends. The DAG is
idempotent under a fixed parameter set.

---

## 5. Cost, and how each table is priced before it runs

### 5.1 Dry-running the body, not the CALL

A dry run of `CALL` does **not** price the procedure body. Two design decisions make each stage
priceable anyway:

1. Every stage body is delimited by a marker pair, `@stage-begin:` and `@stage-end:` followed by the
   table name.
2. Every stage body reads its run parameters from `{DERIVED}.build_params` rather than from procedure
   variables. A body lifted out between its markers is therefore **standalone-valid SQL** and
   dry-runs on its own.

`03_cohort.py` splits on the markers and dry-runs each body through `dry_run_gb()`, which prints that
stage's own byte estimate and its dollars.

**`maximum_bytes_billed` on a BigQuery script is enforced per CHILD JOB, not across the script.** The
`CALL` is a script job, and each of the 19 stages inside it is a child job that the cap is applied to
**individually**. A cap sized to the 19-stage total therefore does not bound the run: it permits each
of the 19 stages to bill up to that total, which is **up to nineteen times** the number the human
approved. The whole point of the cap is that an over-budget query fails rather than bills, and sized
against the DAG total it would not fail on any stage a per-stage cap would have caught.

**So size `max_gb` per stage, against that stage's own dry-run estimate, never against the DAG
total.** Issue each stage under its own cap at its own estimate plus a stated margin. The DAG total
is still worth computing and showing to the human, but it is an approval figure checked before
anything is submitted, not a cap: nothing enforces it at run time.

**The stage that actually binds is expected to be `hr_daily`.** It is the only scan of
`heart_rate_summary` (5.4), the largest table this DAG touches, and by 5.2 it bills three whole
columns of it. Nothing narrows that: its join to `span` is on `person_id` and a date range derived
from a column, which is exactly the predicate 5.3 says BigQuery cannot prune, so restricting the
OUTPUT to cohort persons and the window does not restrict the BYTES. The one stage that could rival
it is `features`, the only stage that scans two large CDR tables in a single job,
`condition_occurrence` and `measurement`. Which of the two is larger is settled by the dry run and
not by this paragraph, which is exactly why the cap is sized from the estimate rather than from an
expectation.

**The two exceptions are `hr_daily` and `device_daily`.** Both bodies are `FORMAT` templates, because
a column name cannot be a query parameter. `03_cohort.py` must substitute `hr_minute_column` into
`hr_daily`'s two `%s` positions and `device_model_column` into `device_daily`'s one **before** the
dry run. Skip the substitution and the dry run prices a query that is not the one that will execute:
the estimate is meaningless, and the per-stage cap above is then sized against the wrong number.
`device_daily` is the one that gets missed, because its template sits on the `ELSE` branch of the
empty-column-name test rather than at the top of the body. Neither template contains a literal
percent sign other than those substitutions; adding one without doubling it would corrupt the
statement.

**That requirement is mechanically checkable, not only documented.** Each of the two bodies carries a
line reading `-- @stage-format-args:` followed by the `FORMAT` arguments in order, placed inside its
own `@stage-begin:` / `@stage-end:` pair so that the marker splitter is unchanged and the line
travels with the body it governs. `03_cohort.py` asserts in both directions: a body containing
`EXECUTE IMMEDIATE FORMAT(` must carry the line, a body without it must not, the number of names on
the line must equal the number of `%s` in the template, and no `%s` may survive substitution. A stage
that becomes a template later fails that assert instead of being priced wrong. The `%s` in
`episodes`, `events` and `risk_sets` are ordinary `FORMAT` calls in static SQL and are not templates,
which is why the test keys on `EXECUTE IMMEDIATE FORMAT(` and not on the percent sign.

### 5.2 BigQuery bills the sum of the COLUMNS REFERENCED, not the table

This is the single most useful fact for reading the cost of this DAG. A query touching four columns
of a hundred-column table bills four columns. It is why every stage below names the columns it reads
rather than selecting a star from a CDR table, and it is why the wide derived tables are cheap to
join against: a downstream query that needs `person_id`, `activity_date` and `steps` bills three
columns of `fitbit_daily`, not all seventeen.

### 5.3 What partitioning and clustering actually buy here

| Table | Partition | Cluster | What it buys, honestly |
|---|---|---|---|
| `fitbit_daily` | `activity_date`, daily | `person_id` | Partition **pruning only applies to a literal date predicate**. Most downstream reads join `fitbit_daily` to an episode table on `person_id` and a date range derived from a column, and BigQuery cannot prune partitions on a join predicate. So the partitioning pays for era-restricted rebuilds and for the wear-availability ledger's date filters, and not for the ordinary join. What pays for the ordinary join is the clustering on `person_id`, which puts a participant's rows in adjacent blocks and lets a `person_id` filter skip blocks, plus column pruning, which is the dominant saving. Roughly 4,000 daily partitions over a decade, against BigQuery's 10,000-partition limit |
| `hr_daily` | `activity_date`, daily | `person_id` | Same. Its real purpose is to be a **cache**: it isolates the one scan of `heart_rate_summary` so that rebuilding `fitbit_daily` under a different wear rule does not re-read it |
| `drd_daily`, `landmark_daily` | `RANGE_BUCKET(post_discharge_day, 0..100 by 5)` | `person_id, episode_id` | **The only partitioning in this DAG that prunes on a literal predicate.** `WHERE post_discharge_day BETWEEN 1 AND 35` is the dominant downstream filter, and it prunes 19 partitions down to 7. `landmark_daily` shares the grid and the key, so a day-restricted read of the two together prunes identically on both |
| `episodes`, `baseline`, `episodes_eligible`, `features`, `events`, `risk_sets` | none | `person_id` | Small tables. Clustering keeps the person-keyed joins cheap; partitioning them would buy nothing |
| everything else | none | none | Tens to hundreds of rows |

### 5.4 The three expensive scans, and where they are

The whole project's BigQuery budget is under two dollars. Three CDR tables are large enough to
matter, and each is read exactly once:

1. **`heart_rate_summary`**, read only by `hr_daily`, three columns, restricted to cohort persons and
   the window. This table is person by date by heart-rate **zone** with a per-zone minute count,
   roughly four rows per person-day against 1,440 for `heart_rate_minute_level`. Summing zone minutes
   gives the wear figure at about one three-hundredth of the bytes. **This is the fact the budget
   rests on.** The minute-level table is not in the critical path and is gated behind explicit human
   approval of a dry-run estimate.
2. **`condition_occurrence`**, read by `episodes_eligible` (four columns) and by `features` (three).
3. **`measurement`**, read once by `features`, four columns, for body mass index.

`visit_occurrence` is read by four stages at five or six columns each; it is large but not in the
same class. `procedure_occurrence` is read twice at three columns.

**`landmark_daily` adds no CDR scan at all.** It is a three-day-offset self-join of `drd_daily` plus
a seven-day lookback on `fitbit_daily`, both already in `{DERIVED}`, at a handful of columns each. It
is the cheapest stage in the DAG after the two vocabulary tables.

---

## 6. The disclosure boundary: what may never leave `{DERIVED}`

**Two tables carry no participant-level column and are safe to read whole:**

- `cs_spine` (852 rows of vocabulary metadata)
- `cs_condition` (the ICD-10-CM condition concept sets)

Concept ids, vocabulary ids, concept codes and concept names are properties of the specification, not
of any participant. `disclosure.export_violations` deliberately does not refuse a column by the name
`concept id`.

**`build_params` carries no participant data either**, but it does carry the CDR observation cutoff
date, which is a property of the release.

**Every other table in `{DERIVED}` is participant-level in its entirety.** Under Controlled Tier,
dates are **unshifted**, so any date column and any near-unique numeric column is an identifier risk
on its own. The following column classes may never be selected into an export, in any table:

| Class | Columns |
|---|---|
| Identifiers | `person_id`, `episode_id`, `event_id`, `set_id`, `visit_occurrence_id`, `index_visit_occurrence_id`, `case_episode_id`, `case_person_id`, `fingerprint` |
| Unshifted dates | `index_date`, `discharge_date`, `visit_start_date`, `activity_date`, `calendar_date`, `event_date`, `case_event_date`, `landmark_date`, `member_landmark_date`, `censor_date`, `death_date`, `repeat_operation_date`, `observation_end_date`, `device_date`, `cdr_observation_cutoff` |
| Per-person measurements | `steps`, `wear_minutes`, `max_zone_minutes`, `baseline_steps` and all eight of its variants, `bmi`, `bmi_imputed`, `age_at_index`, `los_days`, `charlson_score`, `deficit`, `deficit_untruncated`, `normalized_activity`, `lagged_wear_fraction`, `landmark_lagged_wear_fraction`, `landmark_lagged_wear_fraction_wearable`, `r72`, `r72_24h`, `r_reference_7day`, `r_negative_control`, `local_step_deterioration`, `wear_fraction`, `baseline_dow_counts` |

**What leaves is a `GROUP BY` aggregate that has passed `disclosure.safe_export`.** Counts are
suppressed at 1 through 20 inclusive and larger counts round to the nearest 20;
`disclosure.disclosable(n)` is the one arbiter and no module compares against a bare literal.

**Every count in this DAG is a TRUE INTEGER and is not rounded.** `attrition.n_in`, `n_dropped`,
`n_out`, `n_carried_forward`, every `n_episodes` and `n_denominator` in the ledgers, every
`n_at_risk` and `n_valid_wear`: all exact. Rounding and floor-testing happen in `07_export.py`, once,
at the boundary. A module that reads a count out of `{DERIVED}` and prints it has committed a
disclosure violation.

**No display string is ever written by SQL.** `attrition.reason` is a **slug**; the printable
sentence is `LABELS[slug]` in `07_export.py`, keyed by the rung's **`slug`** and never by `reason`.
`EXPORT-CONTRACT.md` section 7.2 keys that table on the nineteen rung slugs, so `reason` is not a
key into it: two of the three values `reason` may take, the literal `"unit_change"` and the empty
string, have no entry there and never will. Group slugs, region slugs, censor reasons, day kinds,
device families and baseline bands are all machine vocabulary. This is what keeps a reason from being
paraphrased at render time and what keeps a `snake_case` token out of user-visible prose.

---

## 7. Safe to drop and rebuild, versus expensive to lose

| Tier | Tables | If lost |
|---|---|---|
| **Expensive** | `hr_daily` | The only scan of `heart_rate_summary`. Rebuilding it is the single largest byte cost in the project. Never drop it to save storage; storage on a few hundred thousand rows is free by comparison |
| **Moderate** | `episodes`, `episodes_eligible`, `features` | Each re-reads a large CDR table (`procedure_occurrence`, `condition_occurrence`, `measurement`, `visit_occurrence`). Rebuilding all three is minutes and cents, not dollars |
| **Cheap** | `build_params`, `cs_spine`, `cs_condition`, `device_daily`, `fitbit_daily`, `baseline`, `drd_daily`, `events`, `landmark_daily`, `risk_sets`, `attrition`, all four ledgers | Derived from tables already in `{DERIVED}`, or from a small CDR table. Drop and rebuild freely |

The practical resume rule: if you are unsure what changed, `start_stage = 'fitbit_daily'` rebuilds
everything downstream of the expensive scan for a few cents.

---

## 8. The tables

Column tables read `column | type | unit | null convention | provenance`. "unit" is a dash where the
value is a category, a flag or an identifier. Row counts are order-of-magnitude estimates against a
9,720-person base cohort with roughly 1,200 Fitbit-overlapping members, which is what a sibling
project in this repo observed; they are expectations, not targets.

---

### 8.1 `{DERIVED}.build_params`

**Purpose.** The run's parameters, materialized so that every later stage body reads them from a
table instead of from a procedure variable. That is what makes each stage body standalone-valid and
therefore dry-runnable. It is also the provenance record: any table carrying `junction_map` traces
back to the map and the probes that produced it.

**Grain.** Exactly one row. **Derives from:** the procedure's arguments and
`{CDR}.observation_period`. **Partition/cluster:** none.

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `junction_map` | STRING | - | never null | parameter 1, `'primary'` or `'mirrored'` |
| `hr_minute_column` | STRING | - | never null | parameter 2, the probed zone-minute column |
| `device_model_column` | STRING | - | never null; `''` means unavailable | parameter 3 |
| `ed_visit_concept_ids` | ARRAY&lt;INT64&gt; | - | never empty | parameter 4, enumerated by `01_probe.py` |
| `inpatient_visit_concept_ids` | ARRAY&lt;INT64&gt; | - | never empty | parameter 5, enumerated by `01_probe.py` |
| `primary_wear_definition` | STRING | - | never null | parameter 6, `'primary'` or `'s2'` |
| `seed` | INT64 | - | never null | internal constant, `0` |
| `sampling_salt` | STRING | - | never null | internal constant, `'spinewear-v1-risk-set'` |
| `built_at` | TIMESTAMP | UTC | never null | `CURRENT_TIMESTAMP()` at build time |
| `cdr_observation_cutoff` | DATE | - | never null | `MAX(observation_period_end_date)` over the CDR |

---

### 8.2 `{DERIVED}.cs_spine`

**Purpose.** The locked 852-concept spine set, region-tagged, transcribed from `pipeline/cs_spine.py`.
**Both** region assignments are carried on every row unconditionally, so a row where they differ IS a
junction code and the mirrored sensitivity needs no second table. The effective region for this run
is resolved once, here.

**Grain.** One row per `concept_id`. **Rows:** exactly 852; the procedure raises otherwise.
**Derives from:** `{CDR}.concept`, `build_params`. **Partition/cluster:** none.
**Vocabulary metadata: no participant-level column.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `concept_id` | INT64 | - | never null | `{CDR}.concept` |
| `vocabulary_id` | STRING | - | never null | `'CPT4'` or `'ICD10PCS'` |
| `concept_code` | STRING | - | never null | `{CDR}.concept` |
| `concept_name` | STRING | - | never null | `{CDR}.concept` |
| `match_kind` | STRING | - | never null | `'exact'` for CPT-4, `'stem4'` for the four-character ICD-10-PCS stem |
| `region_primary` | STRING | - | never null | locked junction map: junction stems go to the CRANIAL member |
| `region_mirrored` | STRING | - | never null | mirrored map: junction stems go to the CAUDAL member |
| `region` | STRING | - | never null | `region_mirrored` when `junction_map = 'mirrored'`, else `region_primary` |
| `procedure_class` | STRING | - | never null | `'fusion'` or `'decompression'` |
| `is_add_on` | BOOL | - | never null | true for the sixteen CPT-4 add-on and instrumentation codes |
| `is_junction` | BOOL | - | never null | `region_primary != region_mirrored`; true for `0RG4`, `0RB5`, `0RGA`, `0RBB` |
| `junction_map` | STRING | - | never null | copied from `build_params` |

`region` takes one of `'cervical'`, `'thoracic'`, `'lumbar'`, `'unspecified'`. `00NT`, release of
spinal meninges, is `'unspecified'` under **both** maps: its fourth character names a tissue rather
than a level, and no sensitivity can recover a level that was never coded.

**The mirrored map changes the ladder, legitimately.** `0RG4` and `0RB5` become thoracic, so an
episode whose only evidence is a cervicothoracic code moves from cervical to thoracic-only, that is
from included to excluded at rung 8. The primary and mirrored runs therefore have **different
ladders**. `attrition.junction_map` records which. Nothing compares one run's rung counts to the
other's.

---

### 8.3 `{DERIVED}.cs_condition`

**Purpose.** Every condition concept set the DAG needs, in one auditable table: the composite
nonelective-indication screen of rung 3, the degenerative-spine set that rescues an episode at rung
4, and the Quan ICD-10 mapping for the Charlson index.

**Grain.** One row per concept per category. A concept may appear under more than one category, which
is intended: malignancy is both a nonelective indication and a Charlson category, and different
consumers count them. **Rows:** roughly 40,000. **Derives from:** `{CDR}.concept`.
**Vocabulary metadata: no participant-level column.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `concept_id` | INT64 | - | never null | `{CDR}.concept` |
| `vocabulary_id` | STRING | - | never null | always `'ICD10CM'` |
| `concept_code` | STRING | - | never null | `{CDR}.concept`, dotted form |
| `concept_name` | STRING | - | never null | `{CDR}.concept` |
| `category_kind` | STRING | - | never null | `'nonelective_indication'`, `'degenerative_spine'` or `'charlson'` |
| `category` | STRING | - | never null | the slug within the kind |
| `weight` | INT64 | Charlson points | **null except when `category_kind = 'charlson'`** | Charlson weights |

`category` under `'nonelective_indication'`: `trauma`, `spinal_cord_injury`, `malignancy`,
`metastatic_disease`, `spinal_infection`. Under `'charlson'`: the seventeen Quan categories.

**Known and accepted gap.** Matching is **ICD-10-CM only**, joined downstream on
`condition_source_concept_id`, which is the same source-code path the locked spine concept set uses.
ICD-9-CM coded conditions are not screened. The study window is the Fitbit era, so pre-2015 records
are a small and shrinking share, and adding ICD-9 would double the vocabulary for episodes whose
wearable data does not exist. **The Charlson hierarchy is NOT applied here**, because it is a scoring
rule and not a vocabulary fact; it is applied in `features`.

---

### 8.4 `{DERIVED}.episodes`

**Purpose.** Attrition rung 2, the persons-to-episodes conversion. Qualifying procedure records on
the **same date** for the same person collapse into one episode; operations on different dates stay
separate episodes until rung 13.

**Grain.** One row per person per index date. **Rows:** roughly 12,000. **Derives from:**
`{CDR}.procedure_occurrence` joined to `cs_spine` on `procedure_source_concept_id`, plus
`{CDR}.visit_occurrence`. **Cluster:** `person_id`. **PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `episode_id` | STRING | - | never null | `FORMAT('%d-%s', person_id, yyyymmdd(index_date))`. **Deterministic**, so a rebuild reproduces it. Contains a person id and a date: an identifier |
| `person_id` | INT64 | - | never null | `{CDR}.procedure_occurrence` |
| `index_date` | DATE | - | never null | `procedure_date` of the same-day bundle |
| `n_procedure_records` | INT64 | records | never null | count of qualifying records in the bundle |
| `n_primary_records` | INT64 | records | never null | count with `is_add_on = FALSE`. Rung 9 fires when this is zero |
| `has_fusion` | BOOL | - | never null | any qualifying record with `procedure_class = 'fusion'` |
| `has_decompression` | BOOL | - | never null | any with `'decompression'` |
| `has_cervical` | BOOL | - | never null | any record with `region = 'cervical'` |
| `has_thoracic` | BOOL | - | never null | any with `'thoracic'` |
| `has_lumbar` | BOOL | - | never null | any with `'lumbar'` |
| `has_unspecified` | BOOL | - | never null | any with `'unspecified'` |
| `procedure_class` | STRING | - | never null | `'fusion'` if `has_fusion`, else `'decompression'` |
| `region` | STRING | - | never null | `'cervical_and_lumbar'`, `'cervical'`, `'lumbar'`, `'thoracic'`, `'unspecified'`, in that precedence |
| `procedure_group` | STRING | - | **null when `region` is not cervical or lumbar** | one of the four group slugs of `ANALYSIS-PLAN` 2.4 |
| `index_visit_occurrence_id` | INT64 | - | null when no visit contains the index date | see below |
| `index_visit_concept_id` | INT64 | - | null with the above | `{CDR}.visit_occurrence` |
| `visit_start_date` | DATE | - | null with the above | admission date |
| `discharge_date` | DATE | - | **null when the index visit has no end date, or no index visit was found.** Rung 10 fires on this | `visit_end_date` |
| `los_days` | INT64 | days | null when `discharge_date` is null | `DATE_DIFF(discharge_date, visit_start_date, DAY)` |
| `episode_seq` | INT64 | - | never null | rank of `index_date` within person, 1 is earliest |
| `junction_map` | STRING | - | never null | copied from `build_params` |

**Index visit selection, deterministic.** Among visits containing the index date: a visit named on
one of the qualifying procedure records wins; among the rest an inpatient visit wins; ties break on
the earliest start and then on the id.

**Two classification choices, the first now decided and prespecified rather than made here.**

1. `procedure_class` uses **all** qualifying evidence including add-on codes. An add-on arthrodesis
   code beside a primary laminectomy still evidences a fusion, and 2.4 classifies decompression plus
   fusion on the same date and region as fusion. What add-on codes cannot do is bring an episode into
   existence on their own, and that is enforced separately by `n_primary_records` at rung 9.
   **This is no longer an undocumented choice.** The reading implemented in `build_all.sql` was put
   to the human and decided in its favour: fusion status reads all qualifying evidence for the
   bundle, add-on codes included. `ANALYSIS-PLAN` **section 2.4** is the section that carries it, and
   `02_pregate.py` is matched to the same rule. Changing it is an amendment under plan section 13.
2. A bundle carrying both cervical and lumbar evidence takes `region = 'cervical_and_lumbar'` rather
   than either one, so that rung 6 can exclude it as a simultaneous two-region operation instead of a
   rule here silently picking a side.

---

### 8.5 `{DERIVED}.hr_daily`

**Purpose.** The **only** scan of `heart_rate_summary` in the project, isolated in its own table so
that rebuilding anything downstream does not re-read it. Built by the first of the two dynamic
statements, because the per-zone minute column name is a runtime probe and a column name cannot be a
query parameter.

**Grain.** One row per person per date with any heart-rate record, over the window of section 8.7.
**Rows:** on the order of 10^5. **Partition:** `activity_date`. **Cluster:** `person_id`.
**PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `person_id` | INT64 | - | never null | `{CDR}.heart_rate_summary` |
| `activity_date` | DATE | - | never null | the `date` column of `heart_rate_summary` |
| `wear_minutes` | INT64 | minutes | never null on a row that exists; **absence of a row means no heart-rate record**, which is not the same as zero | `SUM` of the probed per-zone minute column over the day's zone rows, rounded to a whole minute |
| `n_hr_zone_rows` | INT64 | rows | never null | zone rows for that person-date, typically about 4 |
| `max_zone_minutes` | INT64 | minutes | never null | the largest single zone, kept for auditing the partition assumption |

**The zone-partition stop condition.** The summed zone minutes are a wear figure only if the zones
partition the day without double-counting a minute. The procedure counts person-dates with
`wear_minutes > 1440` and **raises** if any exist, naming `ANALYSIS-PLAN` 2.1's prespecified
response: adopt sensitivity definition S2 as the primary wear rule, log the substitution as an
amendment, and re-run with `primary_wear_definition = 's2'`. It does not fall back to minute-level
counting, which is roughly 300 times the bytes and is not in the budget.

---

### 8.6 `{DERIVED}.device_daily`

**Purpose.** Fitbit model records reduced to the fourteen-family vocabulary of `ANALYSIS-PLAN` 3.6.
The second and last dynamic statement.

**Grain.** One row per person per device date per family. **Rows:** on the order of 10^4.
**Cluster:** `person_id`. **PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `person_id` | INT64 | - | never null | `{CDR}.device` |
| `device_date` | DATE | - | never null | `{CDR}.device` |
| `device_family` | STRING | - | never null; `'other_or_unknown'` for an unrecognised or absent model string | `{DERIVED}.device_family(<probed model column>)` |
| `n_records` | INT64 | rows | never null | device rows for that person, date and family |

**When `device_model_column = ''` this table is created EMPTY with its schema intact.** Every episode
then takes device family `other_or_unknown`, which is a level and not a missing value, and
`features.device_family_source` records that it happened.

---

### 8.7 `{DERIVED}.fitbit_daily`

**Purpose.** Person by date, as a **complete grid**, for every Fitbit-linked participant in the
episode set. The grid is complete on purpose: 2.3 requires every day in the window to be exactly one
of observed, missing, censored or inpatient, and a day that is missing because no row exists is
indistinguishable from a day that was never in the window unless the row is there carrying nulls.
`has_steps_row` and `has_hr_row` keep "no record" apart from "recorded zero", which matters because a
valid wear day with zero steps contributes a full day of deficit while a day with no record
contributes nothing and is weighted instead.

**The window.** Index date minus 60 through index date plus 120, **extended to discharge plus 90
where the length of stay requires it**. Post-discharge day 90 falls on index plus length of stay plus
90, so a stay longer than 30 days pushes the Arm A horizon past index plus 120; without the extension
the recovery curve of exactly the sickest episodes would be silently truncated, and the plan
explicitly retains long stays because the estimand is defined in post-discharge time.

**Restricted to participants with at least one Fitbit record anywhere.** A participant absent from
this table is exactly attrition rung 11.

**Grain.** One row per Fitbit-linked person per date in the window, roughly 181 rows per participant.
**Rows:** order of 220,000 at the observed Fitbit overlap; under 2,000,000 even if every base-cohort
person were linked. **Partition:** `activity_date`. **Cluster:** `person_id`. **PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `person_id` | INT64 | - | never null | grid |
| `activity_date` | DATE | - | never null | grid. **This is the partition key. It is `activity_date`, not `date`** |
| `steps` | INT64 | steps per day | **null when there is no `activity_summary` row for that person-date** | `{CDR}.activity_summary.steps` |
| `wear_minutes` | INT64 | minutes | **null when there is no heart-rate record**, which is not zero | `hr_daily` |
| `n_hr_zone_rows` | INT64 | rows | null with the above | `hr_daily` |
| `has_steps_row` | BOOL | - | never null | an `activity_summary` row existed |
| `has_hr_row` | BOOL | - | never null | an `hr_daily` row existed |
| `valid_wear_primary` | BOOL | - | never null | `is_valid_wear(wear_minutes, steps, 'primary')` |
| `valid_wear_s1` | BOOL | - | never null | sensitivity S1, 576 minutes |
| `valid_wear_s2` | BOOL | - | never null | sensitivity S2, 600 minutes and 100 steps |
| `valid_wear_s3` | BOOL | - | never null | sensitivity S3, 480 minutes |
| `valid_wear_s4` | BOOL | - | never null | sensitivity S4, 720 minutes |
| `valid_wear` | BOOL | - | never null | **the EFFECTIVE flag under this run's `primary_wear_definition`.** Read this one, not `valid_wear_primary`, so the S2 contingency propagates without a second edit |
| `is_analyzable` | BOOL | - | never null | `valid_wear AND steps IS NOT NULL`. A valid wear day with a null step total is **unobserved**, not zero, and is the target of the observation weights |
| `day_of_week` | INT64 | 1 is Sunday, 7 is Saturday | never null | `EXTRACT(DAYOFWEEK FROM activity_date)` |
| `is_weekend` | BOOL | - | never null | `day_of_week IN (1, 7)` |
| `junction_map` | STRING | - | never null | `build_params` |

**Days with fewer than 100 steps are RETAINED** under the primary rule when heart-rate coverage
confirms wear, because profound inactivity may be the biological signal of interest and a steps-based
wear rule would delete exactly the days the study is about. S2 is the one definition that deletes
them, which is why it is on the sensitivity ladder.

---

### 8.8 `{DERIVED}.baseline`

**Purpose.** The preoperative personal baseline `B_i` of `ANALYSIS-PLAN` 2.2 and its eight
prespecified alternatives. All nine are computed here rather than downstream, because each is a
different median over the **same** scan and recomputing them later would mean re-reading
`fitbit_daily` once per sensitivity row.

**Grain.** One row per episode, **including episodes with no wearable data**, so the ladder can count
them. **Rows:** roughly 12,000. **Derives from:** `episodes`, `fitbit_daily`. **Cluster:**
`person_id`. **PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `episode_id` | STRING | - | never null | `episodes` |
| `person_id` | INT64 | - | never null | `episodes` |
| `index_date` | DATE | - | never null | `episodes` |
| `baseline_steps` | FLOAT64 | steps per day | **null when no valid day in the window. NEVER zero** | `exact_median` of `steps` over `valid_wear` days with non-null steps, index day minus 30 to minus 8 |
| `n_valid_baseline_days` | INT64 | days | never null, zero when none | count over the same window |
| `baseline_dow_counts` | ARRAY&lt;INT64&gt; | days | never null, length exactly 7 | **valid baseline days** by day of week, index 0 is Sunday through index 6 is Saturday. `SUM(baseline_dow_counts) = n_valid_baseline_days` |
| `baseline_steps_weekday` | FLOAT64 | steps per day | **null when no valid weekday in the window. NEVER zero** | `exact_median_int` of `steps` over `valid_wear` days with non-null steps, index day minus 30 to minus 8, `day_of_week` 2 through 6 |
| `n_valid_baseline_days_weekday` | INT64 | days | never null, zero when none | count over the same days. **The denominator of any weekday-baseline sensitivity** |
| `baseline_steps_weekend` | FLOAT64 | steps per day | **null when no valid weekend day in the window. NEVER zero** | the same over `day_of_week` 1 and 7, that is Sunday and Saturday |
| `n_valid_baseline_days_weekend` | INT64 | days | never null, zero when none | count over the same days. **The denominator of any weekend-baseline sensitivity** |
| `baseline_steps_60_15` | FLOAT64 | steps per day | null as above | sensitivity `baseline_window_60_15`, days minus 60 to minus 15 |
| `n_valid_baseline_days_60_15` | INT64 | days | never null | same window |
| `baseline_steps_30_1` | FLOAT64 | steps per day | null as above | sensitivity `baseline_window_30_1`, days minus 30 to minus 1 |
| `n_valid_baseline_days_30_1` | INT64 | days | never null | same window |
| `baseline_steps_s1` | FLOAT64 | steps per day | null as above | the locked window under wear definition S1 |
| `n_valid_baseline_days_s1` | INT64 | days | never null | the same |
| `baseline_steps_s2` | FLOAT64 | steps per day | null as above | the locked window under wear definition S2 |
| `n_valid_baseline_days_s2` | INT64 | days | never null | the same |
| `baseline_steps_s3` | FLOAT64 | steps per day | null as above | the locked window under wear definition S3 |
| `n_valid_baseline_days_s3` | INT64 | days | never null | the same |
| `baseline_steps_s4` | FLOAT64 | steps per day | null as above | the locked window under wear definition S4 |
| `n_valid_baseline_days_s4` | INT64 | days | never null | the same |
| `baseline_span_days` | INT64 | calendar days | never null, **zero when no valid day** | last valid baseline date minus first, plus 1 |
| `baseline_band_slug` | STRING | - | **null when `baseline_steps` is null** | `'under_3000'`, `'3000_to_6999'`, `'7000_or_more'`. Description only, never a model cutpoint |
| `meets_baseline_floor` | BOOL | - | null when `baseline_steps` is null | `baseline_steps >= 1000`. A **flag**, never a filter: the floor is sensitivity `baseline_floor`, not an eligibility criterion |
| `has_any_fitbit` | BOOL | - | never null | the person appears in `fitbit_daily` at all. Rung 11 fires on its negation |
| `junction_map` | STRING | - | never null | `build_params` |

**Changing the wear rule changes `B_i` itself**, because it changes which days are valid. That is why
a wear sensitivity cannot be run by swapping a flag at model time, and why the four `_s1` to `_s4`
baselines exist.

**`baseline_dow_counts` counts VALID BASELINE DAYS, not calendar days.** Each element is the number
of days in index day minus 30 to minus 8 that fall on that weekday **and** are valid wear days with a
non-null step count, which is the identical predicate `baseline_steps` and `n_valid_baseline_days`
are taken over. So the array sums to `n_valid_baseline_days`, and `04_features.py` asserts exactly
that. The other reading carries no information at all: the baseline window is a fixed 23-day span, so
a calendar-day composition would be the same seven numbers on every episode in the study, and every
weekday and weekend figure computed from it would be a property of the calendar rather than of the
participant. The array is the **evidence of imbalance** that `ANALYSIS-PLAN` 5.5 rests on: day of
week balances by construction only when the window is complete, and it fails differentially, because
a participant who wears the device on weekdays and abandons it at weekends contributes an unbalanced
window and the imbalance correlates with the amount of missingness.

**Weekday and weekend baselines, and why each has its own denominator.** The protocol asks for two
things about day of week, that the composition be recorded and that a sensitivity analysis estimate
weekday and weekend baselines separately. `baseline_dow_counts` is the first;
`baseline_steps_weekday` and `baseline_steps_weekend` are the second, and the composition cannot
stand in for them, because it says how many Sundays are in the window and not what the participant
walked on them. Both are medians over the locked minus 30 to minus 8 window under the effective wear
rule, so only the half of the week varies. Weekend is Saturday and Sunday, the split
`ANALYSIS-PLAN` 5.5 already uses for the Arm A landmark relaxation.

By construction `n_valid_baseline_days_weekday` equals `SUM(baseline_dow_counts[1..5])`,
`n_valid_baseline_days_weekend` equals `baseline_dow_counts[0] + baseline_dow_counts[6]`, and the two
sum to `n_valid_baseline_days`. A consumer may check that identity; it must not recompute the medians
from it, because a count of days does not carry the steps walked on them.

**A sensitivity fitted on either median runs on its own denominator, and Table 2 must print it.**
Not every episode has a valid day in both halves of the week: a participant who charges the device at
weekends can clear the baseline-adequacy rung on weekdays alone and still have **no** weekend
baseline. The set `baseline_weekday_weekend_split` is fitted on is therefore a different, strictly
smaller set than the primary's, and `ANALYSIS-PLAN` 2.2 defines it as the analytic episodes with
`n_valid_baseline_days_weekday >= 5 AND n_valid_baseline_days_weekend >= 2`. **The denominator is
derived from the two counts and never from the two medians being non-null.** The two are not the
same test: the count form carries the minimum-day rule the plan set from the window's own arithmetic,
where a null test would silently accept an episode with a single valid weekend day. This is the same
own-denominator rule that already governs the `_s1` to `_s4` rows, which is why `04_features.py`
reports how many episodes lack each alternative baseline. The four columns are carried onto
`features` as well, and 8.10 repeats this note there, because `features` is the table a sensitivity
author reads.

**A median over no valid day is NULL, never 0**, here as everywhere else in this table. A zero
baseline makes `S/B` infinite and the daily deficit silently equal to 1 on every day, manufacturing a
maximal recovery debt out of an absence of data, and on these two columns it would do so precisely
on the participants whose wear is concentrated in the other half of the week, which is a
differential error and not a wash.

---

### 8.9 `{DERIVED}.episodes_eligible`

**Purpose.** **THE EXCLUSIONS TABLE. It is not the filtered survivor set.** It carries one row per
episode from `episodes`, every exclusion predicate, and the **first** rung the episode fails. Filter
on `is_eligible` to get survivors.

It is built this way because the ladder counts an episode **once, at the first rung it fails**, and
that is what makes the ladder close. A cascade of filtered tables would make the attribution implicit
and would make the per-reason breakdown, where an episode may be counted under more than one reason,
impossible to produce afterwards. Both come out of this one table: `first_fail_step` drives
`attrition` and the individual flags drive `ledger_exclusion_reasons`.

**Grain.** One row per episode. **Rows:** roughly 12,000. **Derives from:** `episodes`, `baseline`,
`fitbit_daily`, `cs_condition`, `{CDR}.visit_occurrence`, `{CDR}.condition_occurrence`,
`{CDR}.observation_period`, `{CDR}.death`. **Cluster:** `person_id`. **PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `episode_id` | STRING | - | never null | `episodes` |
| `person_id` | INT64 | - | never null | `episodes` |
| `index_date` | DATE | - | never null | `episodes` |
| `discharge_date` | DATE | - | null when rung 10 fires | `episodes` |
| `death_date` | DATE | - | null when the person has no death record | `{CDR}.death` |
| `repeat_operation_date` | DATE | - | null when no later episode after discharge | `MIN(index_date)` of the person's later episodes |
| `observation_end_date` | DATE | - | never null | `MAX(observation_period_end_date)`, falling back to the CDR cutoff |
| `censor_date` | DATE | - | null only when all three sources are null | the earliest of the three above |
| `censor_reason` | STRING | - | never null | `'none'`, `'death'`, `'repeat_spine_operation'`, `'cdr_observation_cutoff'`, in that precedence on a tie |
| `n_analyzable_days_1_35` | INT64 | days | never null, zero when none | analyzable days in post-discharge days 1 to 35, before the censor date |
| `n_at_risk_days_1_35` | INT64 | days | never null, zero when none | grid days in that window before the censor date |
| `ind_trauma` | BOOL | - | never null | a trauma concept in the 30 days before or on the index date |
| `ind_spinal_cord_injury` | BOOL | - | never null | same |
| `ind_malignancy` | BOOL | - | never null | same |
| `ind_metastatic_disease` | BOOL | - | never null | same |
| `ind_spinal_infection` | BOOL | - | never null | same |
| `ed_encounter_present` | BOOL | - | never null | an emergency visit ending on the index date or either of the 2 days before |
| `rescue_elective_coded` | BOOL | - | never null | rescue route 1, the elective proxy |
| `rescue_degenerative_index` | BOOL | - | never null | rescue route 2, a degenerative diagnosis on the index encounter AND nothing from the rung 3 sets on the emergency encounter |
| `rescue_degenerative_outpatient_90d` | BOOL | - | never null | rescue route 3 |
| `x_trauma_malignancy_infection` | BOOL | - | never null | rung 3 predicate, the OR of the five `ind_` flags |
| `x_ed_encounter_not_elective` | BOOL | - | never null | rung 4 predicate |
| `x_prior_operation_90_days` | BOOL | - | never null | rung 5 predicate |
| `x_simultaneous_cervical_lumbar` | BOOL | - | never null | rung 6 predicate |
| `x_region_unspecified_only` | BOOL | - | never null | rung 7 predicate |
| `x_thoracic_only` | BOOL | - | never null | rung 8 predicate |
| `x_add_on_code_only` | BOOL | - | never null | rung 9 predicate, `n_primary_records = 0` |
| `x_missing_discharge_date` | BOOL | - | never null | rung 10 predicate |
| `x_no_wearable_data` | BOOL | - | never null | rung 11 predicate |
| `x_inadequate_baseline_wear` | BOOL | - | never null | rung 12 predicate |
| `x_no_computable_post_discharge_window` | BOOL | - | never null | rung 14 predicate |
| `x_window_truncated_by_death_or_reoperation` | BOOL | - | never null | rung 15 predicate |
| `x_not_first_eligible_episode` | BOOL | - | never null | rung 13 predicate. **Listed last in column order but evaluated at rung 13** |
| `first_fail_step` | INT64 | - | **null exactly when the episode is eligible** | the first rung, 3 to 15, whose predicate is true |
| `first_fail_slug` | STRING | - | null with the above | the matching rung slug |
| `is_eligible` | BOOL | - | never null | `first_fail_step IS NULL` |
| `junction_map` | STRING | - | never null | `build_params` |

**Every predicate is evaluated for every episode.** Which one gets the count is decided by
`first_fail_step`, never by a filter. That is deliberate: the flags support the exclusion-reason
ledger, where rows overlap and are explicitly not a partition.

**Rung 4, the elective proxy, operationally.** "Immediately preceding" is an emergency department
visit whose **end** date falls on the index date or on either of the 2 calendar days before it. Two
days rather than one, because an emergency presentation late on a Friday leading to a Monday
operation is exactly the case the criterion is about. Three rescues, any one sufficient. Rescue route
1 reads `visit_occurrence.visit_source_value` for elective or scheduled wording; **`visit_detail` is
deliberately not consulted**, because whether the CDR populates it is an unconfirmed runtime probe
and a rescue that silently never fires is worse than one that is narrow and named. Rescue route 3's
"outpatient" is defined by exclusion from the two enumerated visit sets, because no outpatient
concept id was probed.

**Rung 12 subsumes protocol exclusion criterion 6.** A participant whose device first appears after
the operation has no preoperative wear at all, so no such participant can clear rung 12. A separate
rung would count zero by construction and would invite a reader to believe it was measuring
something. The **device-change** exclusion is a different criterion and lives on the sensitivity
ladder as `device_change_excluded`, driven by `features.device_changed`.

**Rung 13 makes person and episode coincide in the primary**, which is what makes the person random
effects and the person-clustered bootstrap coherent: the resampling unit and the outcome unit are the
same object. The rank is a running count of episodes passing rungs 3 through 12, within person,
ordered by index date. A tie inside a participant cannot occur, because same-date records were
collapsed at rung 2.

---

### 8.10 `{DERIVED}.features`

**Purpose.** The analysis-ready covariate frame. Everything the locked covariate table of 3.6 names,
plus the quantities Table 1 reports, plus **all eight** alternative baselines carried forward so that
no sensitivity row has to re-read `fitbit_daily` and none has to reach back to `baseline` for a
column this table was supposed to carry.

**Grain.** One row per **eligible** episode, which is one row per participant, because rung 13 takes
the first eligible episode per person. **Rows:** order of 300 to 600. **Derives from:**
`episodes_eligible` filtered to `is_eligible`, `episodes`, `baseline`, `device_daily`,
`cs_condition`, `{CDR}.person`, `{CDR}.condition_occurrence`, `{CDR}.measurement`. **Cluster:**
`person_id`. **PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `episode_id` | STRING | - | never null | `episodes_eligible` |
| `person_id` | INT64 | - | never null | same |
| `index_date` | DATE | - | never null | same |
| `discharge_date` | DATE | - | never null in this table, rung 10 removed the nulls | `episodes` |
| `los_days` | INT64 | days | never null | `episodes` |
| `region` | STRING | - | never null; always `'cervical'` or `'lumbar'` here, rungs 6 to 8 removed the rest | `episodes` |
| `procedure_class` | STRING | - | never null | `'fusion'` or `'decompression'` |
| `procedure_group` | STRING | - | never null in this table | one of the four group slugs |
| `fusion` | BOOL | - | never null | `procedure_class = 'fusion'`. **The primary contrast is on this** |
| `age_at_index` | FLOAT64 | years | null when `birth_datetime` is null | `DATE_DIFF(index_date, birth_datetime) / 365.25` |
| `sex_at_birth` | STRING | - | never null | `'male'`, `'female'`, `'other_or_unknown'`, from `person.sex_at_birth_concept_id` |
| `race_concept_id` | INT64 | - | may be null or 0 | `{CDR}.person`. A concept id, mapped to a label by `07_export.py` |
| `ethnicity_concept_id` | INT64 | - | may be null or 0 | same |
| `bmi` | FLOAT64 | kg/m2 | **null when no plausible measurement in the 365 days before index** | nearest `measurement_concept_id = 3038553` in that window, plausibility window 10 to 80 |
| `bmi_missing` | BOOL | - | never null | `bmi IS NULL`. The **missing indicator** of 3.6 |
| `bmi_imputed` | FLOAT64 | kg/m2 | never null when at least one episode has a BMI | `bmi`, or the cohort's `exact_median` BMI. Computed inside the perimeter and never printed |
| `charlson_score` | INT64 | Charlson points | never null, zero when no qualifying condition | Quan ICD-10 over the 365 days before index, with the three hierarchy rules applied |
| `charlson_missing` | BOOL | - | never null | true when the Charlson CTE produced no row for the episode, that is when the zero above is a **substituted** zero rather than a scored one. The **missing indicator** for `charlson_score`, exactly as `bmi_missing` is for `bmi` |
| `charlson_ordinal` | STRING | - | never null | `'0'`, `'1'`, `'2'`, `'3_or_more'`. The modelled form |
| `index_year` | INT64 | calendar year | never null | `EXTRACT(YEAR FROM index_date)` |
| `covid_era` | BOOL | - | never null | index date from 2020-03-01 through 2021-06-30 |
| `device_family` | STRING | - | never null; `'other_or_unknown'` is a level | modal family in the 30 days before index |
| `device_family_source` | STRING | - | never null | `'device_table'` or `'unavailable'` |
| `device_changed` | BOOL | - | never null | more than one distinct family between index minus 30 and discharge plus 90. Drives sensitivity `device_change_excluded` |
| `baseline_steps` | FLOAT64 | steps per day | never null in this table, rung 12 removed the nulls | `baseline` |
| `n_valid_baseline_days` | INT64 | days | never null | `baseline` |
| `baseline_steps_weekday` | FLOAT64 | steps per day | **null when the window holds no valid weekday. NEVER zero** | `baseline`, carried unchanged |
| `n_valid_baseline_days_weekday` | INT64 | days | never null, zero when none | `baseline`, carried unchanged. **Half of the denominator rule for `baseline_weekday_weekend_split`** |
| `baseline_steps_weekend` | FLOAT64 | steps per day | **null when the window holds no valid weekend day. NEVER zero** | `baseline`, carried unchanged |
| `n_valid_baseline_days_weekend` | INT64 | days | never null, zero when none | `baseline`, carried unchanged. **The other half of that rule** |
| `baseline_steps_60_15` | FLOAT64 | steps per day | may be null | `baseline` |
| `n_valid_baseline_days_60_15` | INT64 | days | never null | `baseline` |
| `baseline_steps_30_1` | FLOAT64 | steps per day | may be null | `baseline` |
| `n_valid_baseline_days_30_1` | INT64 | days | never null | `baseline` |
| `baseline_steps_s1` | FLOAT64 | steps per day | may be null | `baseline` |
| `n_valid_baseline_days_s1` | INT64 | days | never null | `baseline` |
| `baseline_steps_s2` | FLOAT64 | steps per day | may be null | `baseline` |
| `n_valid_baseline_days_s2` | INT64 | days | never null | `baseline` |
| `baseline_steps_s3` | FLOAT64 | steps per day | may be null | `baseline` |
| `n_valid_baseline_days_s3` | INT64 | days | never null | `baseline` |
| `baseline_steps_s4` | FLOAT64 | steps per day | may be null | `baseline` |
| `n_valid_baseline_days_s4` | INT64 | days | never null | `baseline` |
| `baseline_span_days` | INT64 | calendar days | never null | `baseline` |
| `baseline_dow_counts` | ARRAY&lt;INT64&gt; | days | never null, length 7 | `baseline` |
| `baseline_band_slug` | STRING | - | never null in this table | `baseline` |
| `meets_baseline_floor` | BOOL | - | never null | `baseline` |
| `n_analyzable_days_1_35` | INT64 | days | never null, at least 1 in this table | `episodes_eligible` |
| `n_at_risk_days_1_35` | INT64 | days | never null | same |
| `share_window_observed` | FLOAT64 | proportion 0 to 1 | never null | `n_analyzable_days_1_35 / 35` |
| `near_complete_window` | BOOL | - | never null | at least 28 of the 35 accrual days analyzable. **The plan does not define "near complete"; 28 of 35, that is 80%, is fixed here so a Table 1 row cannot be defined after the distribution is seen** |
| `censor_date` | DATE | - | null when never censored | `episodes_eligible` |
| `censor_reason` | STRING | - | never null | `episodes_eligible` |
| `at_risk_last_day` | INT64 | post-discharge days | never null | `LEAST(90, DATE_DIFF(censor_date, discharge_date))`, floored at 0, defaulting to 90 |
| `junction_map` | STRING | - | never null | `build_params` |

**All eight alternative baselines are here, and the two week-half ones are here for the same reason
as the other six.** The two window variants (`_60_15`, `_30_1`), the four wear variants (`_s1`
through `_s4`) and the two week-half variants (`_weekday`, `_weekend`) are all carried from
`baseline`, so a sensitivity row reads its baseline off this table and nothing else. The four
week-half columns were added last and are the reason the sentence above says eight rather than six;
before they were carried, `05_analysis_drd.py` had to join `{DERIVED}.baseline` for exactly the
columns this section said it would not have to.

**The four week-half columns are carried with their null conventions intact, and nothing here
coalesces them.** `baseline_steps_weekday` and `baseline_steps_weekend` are **NULL, never zero**,
when their half of the window holds no valid day, on the same reasoning that makes `baseline_steps`
null rather than zero: a zero baseline makes `S/B` infinite and the daily deficit silently equal to 1
on every day, which manufactures a maximal recovery debt out of missing data, and on these two
columns it would do so precisely on the participants whose wear is concentrated in the other half of
the week, which is a differential error and not a wash. `n_valid_baseline_days_weekday` and
`n_valid_baseline_days_weekend` are INT64, **never null**, and zero when the half holds no valid day.
Unlike `baseline_steps`, which rung 12 has already made non-null in this table, **either median can
be null here on a fully eligible episode.**

**A sensitivity fitted on either median runs on its OWN denominator, and the denominator comes from
the two COUNTS.** Not every episode has a valid day in both halves of the week: a participant who
charges the device at weekends can clear the baseline-adequacy rung on weekdays alone and have **no**
weekend baseline at all. So the set `baseline_weekday_weekend_split` is fitted on is a **different,
strictly smaller** set than the primary's, and Table 2 prints that set's own `n` beside the row under
the rule of `ANALYSIS-PLAN` 9.2. That set is defined by `ANALYSIS-PLAN` 2.2 as the analytic episodes
with `n_valid_baseline_days_weekday >= 5 AND n_valid_baseline_days_weekend >= 2`, and it is
**derived from the two counts and never from the two medians being non-null**. The two are not the
same test: the count form carries the minimum-day rule the plan set from the window's own arithmetic,
where a null test would silently accept an episode with a single valid weekend day. Both counts are
carried here so the rule can be applied against this table alone. This note is repeated from 8.8
because this is the table a sensitivity author reads.

**`baseline_steps` is deliberately NOT a covariate in the primary model.** The outcome is already
normalized by it, and conditioning on the denominator of the outcome changes what is being estimated.
It enters in three prespecified places only: the companion endpoint model, the baseline-floor
sensitivity, and a supplementary baseline-adjusted row. In **Arm A** it **is** a covariate, because
the exposure is a ratio whose denominator is the baseline.

**The Charlson hierarchy rules, applied here.** Metastatic solid tumour (6) supersedes any malignancy
(2); moderate or severe liver disease (3) supersedes mild (1); diabetes with complication (2)
supersedes diabetes without (1).

**Why `charlson_missing` exists.** `charlson_score` is `IFNULL(..., 0)`, which is a **scoring** rule
and not an imputation: an episode with no qualifying condition in the lookback genuinely scores zero.
But the `IFNULL` also destroys the evidence that the Charlson CTE produced no row at all, and
`ledger_variable_missingness` could then only ever report zero missing Charlson, which would be a
fact about the `IFNULL` rather than about the data. The flag carries that evidence forward and the
ledger row counts **it**. Same rule as `bmi_missing`: **where this table substitutes, it also carries
the flag that records the substitution, and the missingness ledger counts the flag.**

---

### 8.11 `{DERIVED}.drd_daily`

**Purpose.** The daily deficit panel. The estimand accrues over post-discharge days 1 to 35; days 36
to 90 are carried because Figure 2 plots the recovery curve out to day 90 and the display model has
its own knots there.

**Post-discharge day 1 is the first COMPLETE calendar day after the index discharge.** The discharge
day itself is day 0 and is excluded from every wearable window, because it is a partial inpatient day
whose step count mixes two settings.

**Grain.** One row per analytic episode per post-discharge day 1 to 90. **Rows:** order of 27,000 to
54,000. **Derives from:** `features`, `fitbit_daily`, `{CDR}.visit_occurrence`. **Partition:**
`RANGE_BUCKET(post_discharge_day, GENERATE_ARRAY(0, 100, 5))`. **Cluster:** `person_id, episode_id`.
**PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `episode_id` | STRING | - | never null | `features` |
| `person_id` | INT64 | - | never null | `features` |
| `post_discharge_day` | INT64 | days, 1 to 90 | never null | the grid. **The partition key** |
| `postoperative_day` | INT64 | days | never null | `los_days + post_discharge_day` |
| `calendar_date` | DATE | - | never null | `discharge_date + post_discharge_day` |
| `day_of_week` | INT64 | 1 is Sunday | never null | `EXTRACT(DAYOFWEEK FROM calendar_date)` |
| `is_weekend` | BOOL | - | never null | `day_of_week IN (1, 7)` |
| `steps` | INT64 | steps per day | **null when no step record** | `fitbit_daily` |
| `wear_minutes` | INT64 | minutes | **null when no heart-rate record** | `fitbit_daily` |
| `valid_wear` | BOOL | - | never null | `fitbit_daily`, effective definition |
| `valid_wear_s1` | BOOL | - | never null | `fitbit_daily` |
| `valid_wear_s2` | BOOL | - | never null | `fitbit_daily` |
| `valid_wear_s3` | BOOL | - | never null | `fitbit_daily` |
| `valid_wear_s4` | BOOL | - | never null | `fitbit_daily` |
| `is_analyzable` | BOOL | - | never null | `fitbit_daily.is_analyzable` **and** the day is at risk |
| `is_censored` | BOOL | - | never null | `post_discharge_day > at_risk_last_day` |
| `is_inpatient` | BOOL | - | never null | the calendar date falls inside a readmission stay beginning after discharge |
| `in_accrual_window` | BOOL | - | never null | day 1 to 35. **The estimand's window** |
| `in_pod_anchored_window` | BOOL | - | never null | postoperative day 8 to 42. Sensitivity `pod_anchored_window` |
| `day_kind` | STRING | - | never null | `'censored'`, `'observed'`, `'missing'`, in that precedence |
| `day_kind_four` | STRING | - | never null | the plan's exclusive taxonomy: `'censored'`, `'inpatient'`, `'observed'`, `'missing'`, in that precedence |
| `normalized_activity` | FLOAT64 | proportion of baseline | **null on a non-analyzable day** | `steps / baseline_steps` |
| `deficit` | FLOAT64 | proportion, 0 to 1 | **null on a non-analyzable day. NEVER zero-imputed** | `GREATEST(0, 1 - steps / baseline_steps)` |
| `deficit_untruncated` | FLOAT64 | proportion, may be negative | null as above | `1 - steps / baseline_steps`. Sensitivity `debt_untruncated` |
| `lagged_wear_fraction` | FLOAT64 | proportion 0 to 1 | **null on post-discharge day 1, partial through day 7** | mean of `valid_wear` over days d minus 7 to d minus 1. **Strictly lagged**, so the observation model can never condition on the day it is weighting. The lag runs over post-discharge days, so it does not exist at a landmark on day 1 or earlier; 8.13 carries that case |
| `junction_map` | STRING | - | never null | `build_params` |

**Why the taxonomy needs two columns.** Inpatient is not exclusive of observed: a readmitted patient
who is wearing the device produces a valid, analyzable, inpatient day, and the plan **keeps** those
days in the primary because a readmission is part of recovery and deleting it would delete the worst
days. `day_kind` therefore carries observation status in three values and `is_inpatient` carries the
setting alongside it, so the "inpatient days censored" sensitivity is a filter on a flag rather than a
rebuild. `day_kind_four` reproduces the plan's exclusive four-value taxonomy for the report of 2.3.

**A missing day is never imputed as zero deficit.** A zero deficit is the assertion that the patient
walked at or above their own preoperative baseline that day, which is the most favourable possible
completion of the window and is biased downward exactly where the deficit is largest.

**Sensitivity deficits are NOT precomputed per wear definition.** Recompute them from `steps` and
`features.baseline_steps_s1` through `_s4`. Four more float columns here would widen the table for
every downstream read, and BigQuery bills columns.

---

### 8.12 `{DERIVED}.events`

**Purpose.** Arm A's outcome: an EHR-recorded post-discharge acute-care encounter within 90 days,
meaning an emergency department visit or a new inpatient admission beginning after discharge from the
index surgical encounter. An emergency visit followed by same-day admission collapses to **one**
event. The manuscript says "acute-care encounter", never "unplanned readmission" and never
"complication".

**Every event is kept, with `event_rank`.** `is_first_event` marks the one the ladder counts; the
later ones exist so that the prespecified secondary admitting repeat events needs no second build.

**Grain.** One row per acute-care encounter date per analytic episode. **Rows:** order of 100 to 400.
**Derives from:** `features`, `fitbit_daily`, `{CDR}.visit_occurrence`. **Cluster:** `person_id`.
**PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `event_id` | STRING | - | never null | `FORMAT('%s-%s', episode_id, yyyymmdd(event_date))`. Deterministic |
| `episode_id` | STRING | - | never null | `features` |
| `person_id` | INT64 | - | never null | `features` |
| `event_date` | DATE | - | never null | `visit_start_date` |
| `event_post_discharge_day` | INT64 | days | never null | `DATE_DIFF(event_date, discharge_date, DAY)` |
| `event_kind` | STRING | - | never null | `'emergency_department'`, `'inpatient'`, `'ed_then_inpatient'` |
| `visit_occurrence_id` | INT64 | - | never null | the smallest id on that date |
| `event_rank` | INT64 | - | never null | 1 is the first event for the episode |
| `is_first_event` | BOOL | - | never null | `event_rank = 1`. **The ladder and the gate count this** |
| `landmark_date` | DATE | - | never null | `event_date - 3` |
| `landmark_post_discharge_day` | INT64 | days | never null | `event_post_discharge_day - 3`. May be zero or negative |
| `landmark_day_of_week` | INT64 | 1 is Sunday | never null | of the landmark date |
| `n_valid_days_in_window` | INT64 | days, 0 to 3 | never null | valid wear days with non-null steps among the eligible days of E minus 5 to E minus 3 |
| `n_eligible_days_in_window` | INT64 | days, 0 to 3 | never null | days of that window that are **post-discharge days**, whether worn or not |
| `has_computable_landmark` | BOOL | - | never null | `n_valid_days_in_window >= 2` |
| `structurally_uncomputable_landmark` | BOOL | - | never null | `n_eligible_days_in_window < 2`. **Attrition rung 18 counts on THIS, not on `has_computable_landmark`** |
| `no_computable_step_signal` | BOOL | - | never null | `n_eligible_days_in_window >= 2 AND n_valid_days_in_window < 2`. **The data condition and only the data condition.** This is `N` in the co-primary model of 4.4, and it is **false**, never true, on a structurally uncomputable event. Same name, same meaning and same expression shape as 8.13 and 8.14 |
| `n_missing_days_in_window` | INT64 | days | never null | `3 - n_valid_days_in_window` |
| `r72` | FLOAT64 | proportion of baseline | **null when no valid day in the window** | `exact_median_int(steps over E-5..E-3) / baseline_steps` |
| `r72_24h` | FLOAT64 | proportion | null as above | secondary 24-hour landmark, days E minus 3 to E minus 1 |
| `r_reference_7day` | FLOAT64 | proportion | null as above | reference window, days E minus 12 to E minus 6 |
| `r_negative_control` | FLOAT64 | proportion | null as above | negative-control window, days E minus 14 to E minus 8 |
| `local_step_deterioration` | FLOAT64 | natural log ratio | null when either median is null or the reference is zero | `LN(proximal median / reference median)` |
| `wear_fraction` | FLOAT64 | proportion 0 to 1 | null when the window has no eligible day | mean of `wear_minutes / 1440` over the eligible proximal days |
| `junction_map` | STRING | - | never null | `build_params` |

**The two "cannot compute" conditions are different and must not be merged.**

- `structurally_uncomputable_landmark` is a **definitional** problem. The exposure window must lie on
  post-discharge days, and post-discharge day 1 is the first complete day after discharge, so an
  event on post-discharge days 1 to 4 has fewer than two eligible days no matter how well the patient
  wore the device. The first eligible landmark is post-discharge day 2, belonging to an event on
  post-discharge day 5. **Day 1 to 4, not day 1 to 3**; the six-row derivation is in `ANALYSIS-PLAN`
  4.3 and the procedure **asserts** that this flag equals `event_post_discharge_day <= 4`. These
  events are rung 18 and are never folded into a generic insufficient-wearable-data row. Their timing
  is reported, and a prespecified partial-window secondary admits day-4 events using day 1 alone.
- `no_computable_step_signal` is a **data** condition on an event that is otherwise computable: the
  window held its two post-discharge days and fewer than two of them were worn. Those windows **stay
  in the risk set**, because requiring a computable ratio deletes preferentially the sickest windows,
  and conditioning on a common consequence of exposure and outcome is collider stratification. `N` is
  promoted to a co-primary exposure instead. The flag carries the data condition **and nothing else**:
  it is false on a structurally uncomputable event, so **the two counts are never summed** and no
  reader can add an exposure to an exclusion. `NOT has_computable_landmark` is the **union** of the
  two and is not the data condition; the data condition is this column and only this column.

**The three surfaces that carry this column now agree, and the agreement is the point.** `events`
(8.12), `landmark_daily` (8.13) and `risk_sets` (8.14) each set `no_computable_step_signal` from the
same expression, allowing only for each stage's own null guard on a left-joined window:

| table | expression | column beside it |
|---|---|---|
| `events` | `IFNULL(n_eligible_days_in_window, 0) >= 2 AND IFNULL(n_valid_days_in_window, 0) < 2` | `structurally_uncomputable_landmark` |
| `landmark_daily` | `n_eligible_days_in_window >= 2 AND n_valid_days_in_window < 2` | `structurally_uncomputable_landmark` |
| `risk_sets` | `IFNULL(n_eligible_days_in_window, 0) >= 2 AND IFNULL(n_valid_days_in_window, 0) < 2` | `structurally_uncomputable_landmark` |

A column whose meaning differed by which table a reader opened would be a defect in this contract
rather than a disagreement to be settled at run time, and `ANALYSIS-PLAN` 4.4 puts the definitional
condition outside the co-primary exposure on **every** surface it names: the conditional model of
4.5, the discrete-time model of 4.6, the `landmark_daily` panel of fix 3 and `risk_sets`. **The
definitional condition loses nothing by this**, because all three tables carry
`structurally_uncomputable_landmark` beside it and it keeps its own column. **On all three the two
conditions are distinct and their counts are never summed**, here, in `04_features.py`, in
`06_analysis_gate.py` or in any exhibit.

**The truth table, by post-discharge day, and it now reads the same on all three tables.** The window
for post-discharge day `D` is days `D` minus 5, `D` minus 4 and `D` minus 3, and only those of them
that are 1 or greater are eligible, so `n_eligible` is arithmetic on `D` alone and no amount of wear
moves it. The landmark day is `D` minus 3.

| post-discharge day `D` | landmark day | `n_eligible` | `structurally_uncomputable_landmark` | `no_computable_step_signal` | `has_computable_landmark` |
|---|---|---|---|---|---|
| 1 | -2 | 0 | **true** | **false**, at any wear | false |
| 2 | -1 | 0 | **true** | **false**, at any wear | false |
| 3 | 0 | 0 | **true** | **false**, at any wear | false |
| 4 | 1 | 1 | **true** | **false**, at any wear | false |
| 5 | 2 | 2 | false | true when `n_valid < 2` | true when `n_valid = 2` |
| 6 | 3 | 3 | false | true when `n_valid < 2` | true when `n_valid >= 2` |
| 7 | 4 | 3 | false | true when `n_valid < 2` | true when `n_valid >= 2` |
| 8 | 5 | 3 | false | true when `n_valid < 2` | true when `n_valid >= 2` |

Days 1 to 4 are the definitional condition and carry **no** `N`; day 5 is the first day that can carry
one, which is the first eligible landmark of `ANALYSIS-PLAN` 4.3 restated. Exactly one of the last
three columns is true on every row, on every one of the three tables. In `events` read `D` as
`event_post_discharge_day`, in `landmark_daily` as `post_discharge_day`, and in `risk_sets` as
`member_matched_day`; no case row ever sits at `D` of 4 or less, because rung 18 removed those events
before `cases` read them, while the day-of-week relaxation of 4.7 can still put a **control** at `D`
of 3 or 4, and that control is dropped from its risk set and counted.

**Admissions carrying scheduled or elective wording on the admission date are excluded**, by the same
proxy as rung 4 and labelled as one for the same reason.

**At least 30 postoperative Fitbit days are NOT required.** That restriction would create selection
and immortal-time bias by excluding early events and patients whose adherence declined during
deterioration.

**This table holds the landmark comparison only at event dates and chiefly at first events.** The
full-cohort, day-indexed version, which is what the collider correction of `ANALYSIS-PLAN` 4.4
actually needs, is 8.13. The two agree cell for cell at every event date and the procedure raises if
they do not.

---

### 8.13 `{DERIVED}.landmark_daily`

**Purpose.** The **full-cohort, day-indexed landmark panel**, and it exists to serve the collider
correction of `ANALYSIS-PLAN` 4.4. The plan promotes "no computable step signal" to a **co-primary
exposure** and specifies inverse-probability-of-observation weighting alongside it, on the reasoning
that wear is plausibly caused both by declining activity and by the illness that generates the
outcome. If that is right, requiring a computable landmark deletes exactly the sickest windows, and
conditioning on a common consequence of exposure and outcome is collider stratification.

**Testing that reasoning needs a day-indexed panel over the whole cohort.** The same comparison is
available in two other places and neither answers the question. `risk_sets` carries it only where a
set was drawn, which is a **sampled** comparison and carries a sampling caveat. `events` carries it
only at event dates and reports chiefly on **first** events. Neither says how often a landmark was
computable on an **ordinary** episode-day, nor whether an event followed. This table says both, on
every analytic episode and every post-discharge day, including days nobody was sampled at and
episodes that never had an event.

**It is a three-day-offset self-join of `drd_daily`,** so it is cheap. The window for post-discharge
day d is days d minus 5, d minus 4 and d minus 3, which is the plan's E minus 5 to E minus 3 window
read at a landmark rather than at an event.

**Grain.** One row per analytic episode per post-discharge day 1 to 90, the same grid as `drd_daily`.
**Rows:** order of 27,000 to 54,000. **Derives from:** `drd_daily`, `events`, `fitbit_daily`.
**Partition:** `RANGE_BUCKET(post_discharge_day, GENERATE_ARRAY(0, 100, 5))`. **Cluster:**
`person_id, episode_id`. **PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `episode_id` | STRING | - | never null | `drd_daily` |
| `person_id` | INT64 | - | never null | `drd_daily` |
| `post_discharge_day` | INT64 | days, 1 to 90 | never null | the `drd_daily` grid. **The partition key.** The day a risk set would be matched at |
| `landmark_post_discharge_day` | INT64 | days | never null | `post_discharge_day - 3`. **May be zero or negative**, exactly as in `events` |
| `is_censored` | BOOL | - | never null | `drd_daily.is_censored`. Restrict the panel to the risk set with its negation |
| `n_valid_days_in_window` | INT64 | days, 0 to 3 | never null | days d minus 5 to d minus 3 that are `valid_wear` with a non-null step count |
| `n_eligible_days_in_window` | INT64 | days, 0 to 3 | never null | days d minus 5 to d minus 3 that are **post-discharge days**, worn or not. Structural: `drd_daily`'s grid starts at day 1, so an earlier day has no row to match |
| `has_computable_landmark` | BOOL | - | never null | `n_valid_days_in_window >= 2`. **A computable window.** Its negation is the union of the two rows below and is not, on its own, the data condition |
| `structurally_uncomputable_landmark` | BOOL | - | never null | `n_eligible_days_in_window < 2`. **A definitional condition, and attrition rung 18.** Never merge it with the row below |
| `no_computable_step_signal` | BOOL | - | never null | `n_eligible_days_in_window >= 2 AND n_valid_days_in_window < 2`. **The data condition and only the data condition.** This is `N`, the co-primary exposure of `ANALYSIS-PLAN` 4.4, and it is **false**, never true, on a structurally uncomputable episode-day, so it needs no prior structural drop to read correctly. Same name, same meaning and same expression shape as 8.12 and 8.14. **The two counts are never summed** |
| `landmark_lagged_wear_fraction` | FLOAT64 | proportion 0 to 1 | **null when `landmark_post_discharge_day` is 1 or less** | `drd_daily.lagged_wear_fraction` read at the landmark day. **The plan's own observation-weight input** |
| `landmark_weight_input_available` | BOOL | - | never null | `landmark_lagged_wear_fraction IS NOT NULL`. Count on this column to size the early-landmark rule |
| `landmark_before_post_discharge_day_one` | BOOL | - | never null | `landmark_post_discharge_day < 1`, that is a matched day of 3 or earlier. The subset with **no `drd_daily` row at all** at the landmark |
| `landmark_lagged_wear_fraction_wearable` | FLOAT64 | proportion 0 to 1 | **never null in a correct build**, see below | mean of `fitbit_daily.valid_wear` over the seven **calendar** days before the landmark date. **Defined before post-discharge day 1** |
| `n_days_behind_landmark_on_wearable_grid` | INT64 | days, 0 to 7 | never null | its denominator. **Expected to be 7 on every row** |
| `is_event_day` | BOOL | - | never null | an `events` row falls on this episode and day |
| `is_first_event_day` | BOOL | - | never null | that row is the episode's first event |
| `junction_map` | STRING | - | never null | `build_params` |

**The two "cannot compute" conditions are separate here for the same reason they are separate in
8.12, and merging them would defeat the table.** `no_computable_step_signal` is true when the window
held its two post-discharge days and fewer than two of them were **worn**: a data condition, and
precisely the state the co-primary exposure was introduced to keep in the analysis.
`structurally_uncomputable_landmark` is true when fewer than two days of the window are
**post-discharge days**: a definitional condition that no amount of wear could fix, true on
post-discharge days 1 to 4 and on no other day. A panel that folded the second into the first would
put an exclusion inside an exposure and delete the windows it was built to preserve.

**The three day classes partition the panel, which is what the standardization weights rest on.**
Every episode-day is in exactly one of `has_computable_landmark`, `no_computable_step_signal` and
`structurally_uncomputable_landmark`, because valid days are a subset of eligible days: two or more
worn days force two or more eligible ones, and fewer than two eligible days force fewer than two worn
ones. `06_analysis_gate.py` asserts that the three day counts sum to the panel's own day count before
it standardizes anything. **That assert is a check on the partition and is not a licence to add the
classes together in an exhibit.** It is the one place in this contract where the three are
arithmetically related, it produces no published number, and outside it **the counts are never
summed**: a single "no computable landmark" number would be the sum of a data condition that is an
exposure and a definitional condition that is an exclusion, and no reader could take it apart again
afterwards.

**Watch `NOT has_computable_landmark`, which is the union and is not the data condition.** It is true
on both of the other two classes. The column that carries the data condition alone is
`no_computable_step_signal`, and it is the only one of the three that may be read as `N`.

**The panel reproduces `events` where the two overlap, and the procedure raises if it does not.** At
an event's own post-discharge day both compute the same window under the same rule from different
sources, `events` out of `fitbit_daily` and this table out of `drd_daily`. The check compares
`n_valid_days_in_window`, `n_eligible_days_in_window`, `has_computable_landmark` and
`structurally_uncomputable_landmark` row by row. It does not need a fifth comparison for
`no_computable_step_signal`: both tables derive that column from the same two counts by the same
expression, so equal counts force an equal flag and the four columns already listed decide it. A
second check asserts `structurally_uncomputable_landmark = (post_discharge_day <= 4)` on **every**
episode-day, which is the six-row derivation of `ANALYSIS-PLAN` 4.3 verified across the whole panel
rather than only at event dates the way rung 18 verifies it.

**Adding this table did not change the attrition ladder.** It is a nineteenth **stage**, not a
twentieth **rung**. Rung 18 still counts `events.structurally_uncomputable_landmark` over first
events, and nothing in `attrition` reads this table.

### The early-landmark weight problem, and what this table supplies

A risk set matched at post-discharge day d has its landmark at day d minus 3. So:

| matched day | landmark day | is there a `drd_daily` row? | is `lagged_wear_fraction` defined? |
|---|---|---|---|
| 1, 2, 3 | -2, -1, 0 | **no** | no |
| 4 | 1 | yes | **no**, the lag is over post-discharge days and day 1 has none preceding it |
| 5 to 10 | 2 to 7 | yes | yes, but **partial**: the lag has fewer than seven preceding post-discharge days to average over |
| 11 or later | 8 or later | yes | yes, over the full seven |

**The observation weights of 3.7 therefore have no input at any matched day of 4 or earlier**, which
is one day wider than "the landmark is before post-discharge day 1". This table does not decide the
rule, because the rule is a prespecification question. It supplies both of the things a rule could
need:

- **`landmark_weight_input_available`** and **`landmark_before_post_discharge_day_one`** make the
  affected members **countable**, so the rule can be applied and its denominator reported;
- **`landmark_lagged_wear_fraction_wearable`** is the fraction taken over the **wearable** grid,
  which exists before post-discharge day 1 because `fitbit_daily` reaches back to index day minus 60.

`fitbit_daily` is a **dense** calendar grid per Fitbit-linked person, running from `MIN(index_date)`
minus 60 days to at least `MAX(discharge_date)` plus 90 (8.7). The seven days before a landmark on
post-discharge day d minus 3 are the calendar days from discharge plus d minus 10 through discharge
plus d minus 4, which lie inside that span for every d from 1 to 90 and every length of stay. So
`n_days_behind_landmark_on_wearable_grid` is **7 on every row of a correct build**, and
`landmark_lagged_wear_fraction_wearable` is never null. A row below 7 is not a data condition to be
weighted around: it means the span does not cover the lookback, and it is a defect to be found
before the weights are fitted.

**The two lagged fractions are not the same quantity and neither may be silently substituted for the
other.** `landmark_lagged_wear_fraction` averages over post-discharge days only.
`landmark_lagged_wear_fraction_wearable` averages over calendar days, so it can include inpatient
days and, at an early landmark, **preoperative** days, where wear behaviour is a different thing
being measured for a different reason. `ANALYSIS-PLAN` 4.4 names which one the weight model uses, or
whether an early landmark instead takes a marginal weight; whichever it names, the count of affected
members is reported alongside the estimate.

---

### 8.14 `{DERIVED}.risk_sets`

**Purpose.** Incidence-density sampled matched sets for Arm A. Under-specified risk-set sampling
biases away from the null, chiefly by drawing controls only from participants who never have an
event, which conditions the control pool on the future. Every degree of freedom is closed.

**Grain.** One row per matched set per member, **cases included**. **Rows:** order of 10^3.
**Derives from:** `events`, `features`, `fitbit_daily`. **Cluster:** `person_id`.
**PARTICIPANT-LEVEL.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `set_id` | STRING | - | never null | the case's `event_id` |
| `case_episode_id` | STRING | - | never null | `events` |
| `case_person_id` | INT64 | - | never null | `events` |
| `case_event_date` | DATE | - | never null | `events` |
| `case_matched_day` | INT64 | post-discharge days | never null | the case's event day. **The single time scale** |
| `member_role` | STRING | - | never null | `'case'` or `'control'` |
| `episode_id` | STRING | - | never null | this member's episode |
| `person_id` | INT64 | - | never null | this member's person |
| `member_matched_day` | INT64 | post-discharge days | never null | equals `case_matched_day` at rung 1, within 2 at rungs 2 and 3 |
| `member_landmark_date` | DATE | - | never null | `discharge_date + member_matched_day - 3` |
| `member_landmark_post_discharge_day` | INT64 | days | never null | `member_matched_day - 3` |
| `member_landmark_day_of_week` | INT64 | 1 is Sunday | never null | of the landmark date |
| `match_rung` | INT64 | - | never null | 1, 2 or 3, the relaxation rung the set used. **1 on every case row** |
| `set_size` | INT64 | controls | never null | number of **control rows** in the set, 0 to 5. It counts every control the sampling drew, **including one later dropped for the definitional condition below**, so it equals `COUNTIF(member_role = 'control')` over this table and `04_features.py` checks exactly that. The count that enters the conditional likelihood is the control rows with `structurally_uncomputable_landmark` false |
| `fingerprint` | INT64 | - | **null on every case row** | the seeded `FARM_FINGERPRINT` that ordered the draw |
| `n_valid_days_in_window` | INT64 | days, 0 to 3 | never null | valid wear days with a non-null step count among the eligible days of the window ending at this member's own landmark |
| `n_eligible_days_in_window` | INT64 | days, 0 to 3 | never null | days of that window that are **post-discharge days**, whether worn or not. **Same name, same rule and same meaning as 8.12 and 8.13**; `fitbit_daily` is a dense calendar grid per linked person, so this is a calendar count and not a second wear rule |
| `has_computable_landmark` | BOOL | - | never null | `n_valid_days_in_window >= 2` |
| `structurally_uncomputable_landmark` | BOOL | - | never null | `n_eligible_days_in_window < 2`, equivalently `member_landmark_post_discharge_day <= 1`, equivalently `member_matched_day <= 4`. **A definitional condition.** The member carries no `N` and is **dropped from its risk set**. False on every case row, because rung 18 removed those events before `cases` read them |
| `no_computable_step_signal` | BOOL | - | never null | `n_eligible_days_in_window >= 2 AND n_valid_days_in_window < 2`. **The data condition and only the data condition.** This is `N`, the co-primary exposure of `ANALYSIS-PLAN` 4.4. It is **false**, never true, on a structurally uncomputable member. Same name, same meaning and same expression shape as 8.12 and 8.13 |
| `r72` | FLOAT64 | proportion of baseline | **null when the window holds no valid day, and null on every structurally uncomputable member** | `exact_median_int(steps) / baseline_steps` at this member's own landmark. A member with no exposure window publishes no ratio, so a reader who forgot the structural flag cannot fit a one-day ratio as though it were the exposure |
| `wear_fraction` | FLOAT64 | proportion | null when the window has no eligible day | mean `wear_minutes / 1440` |
| `is_case` | BOOL | - | never null | `member_role = 'case'` |
| `junction_map` | STRING | - | never null | `build_params` |

**The two landmark conditions are distinct here, they carry the names and meanings they carry in
8.12 and 8.13, and their counts are never summed.** `no_computable_step_signal` is a **data**
condition: the window holds at least two post-discharge days but fewer than two of them were worn.
That member **stays** in the risk set, carries `N = 1` and is the co-primary exposure that
`ANALYSIS-PLAN` 4.4 introduced precisely so those windows do not vanish.
`structurally_uncomputable_landmark` is a **definitional** condition: the window holds fewer than two
post-discharge days at all. That member has no exposure window, carries **no** `N`, and leaves. **A
single "no computable landmark" number would be the sum of an exposure and an exclusion, and no
reader could take it apart again afterwards**, so the two are never added together here, in
`04_features.py`, in `06_analysis_gate.py` or in any exhibit.

**Why the definitional condition may not sit inside the data condition.** `N` exists to capture one
thing: sick people who stopped wearing the device. A window that is uncomputable because it
**straddles discharge** is uncomputable for **calendar** reasons that have nothing to do with the
participant's illness or behaviour, and it is a deterministic function of post-discharge day, which
is already this design's single time scale, already matched on and already conditioned on. Folding it
into `N` would put a calendar artefact inside the coefficient that exists to measure informative
non-wear, and it would do so in the direction that matters, because the members it adds are the
earliest ones. `T = E - 3` and the window is `T-2` to `T`, so the window reaches two post-discharge
days exactly when `T` is 2 or more: **a landmark day of 1 or less is not a threshold, it is the
definitional condition written in landmark-day terms.**

**The one member this bites, and why it is dropped and counted rather than filtered out.** Every case
here sits at post-discharge day 5 or later, because `cases` reads only events that survived rung 18.
The **day-of-week relaxation** of `ANALYSIS-PLAN` 4.7 can still put a **control** at post-discharge
day 3 or 4, therefore at a landmark day of 0 or 1, and such a control has no exposure window to
contribute. **It cannot leave at ladder rung 18: rung 18 is an event rung and a sampled control is
not an event.** So it is admitted by the relaxation, drawn under both caps, and then **dropped from
its risk set as a member and counted**, carrying `structurally_uncomputable_landmark` and a null
`r72` so that the drop is visible in the table rather than implied by its absence. The candidate
filter is post-discharge day **1**, not 5, for exactly this reason: a floor of 5 would look like a
definition while making every count below structurally zero, which is the silent exclusion the plan
exists to prevent.

`04_features.py` reads those counts off `member_landmark_post_discharge_day` and reports them:
members at a landmark day of 1 or less, split into cases and controls and split again by the two
routes of 4.4; and the **matched sets that lose every control** that way, which leave the conditional
likelihood altogether and which no arithmetic on the member counts recovers.

**Two assertions guard the flag, and both sit beside the stage rather than inside it.** The first
asserts `structurally_uncomputable_landmark = (member_matched_day <= 4)` on every row, which is the
same calendar identity 8.13 asserts on the panel, checked here against a count taken out of
`fitbit_daily` instead of `drd_daily`. The second asserts that **no case row** carries the flag,
since every case came through rung 18. Either failing is a stop condition and names the stage to
rebuild from.

**The sampling, in full.**

- Eligible controls are participants **still at risk** at the case's post-discharge day and
  **encounter-free** through it. A participant may be a control at one landmark and a **case** later:
  future case status does not disqualify them, and excluding never-event participants only would
  break the design.
- Post-discharge day is the single time scale. Not calendar time, not time since enrollment.
- Calendar year is a **covariate**, not a matching factor.
- Ordering is a seeded `FARM_FINGERPRINT` over the salt, the seed, the set id, the control episode id
  and the matched day. A nondeterministic random draw would give a different matched set every time
  the procedure ran, so the odds ratio would move between sessions for no reason a reader could see,
  and a resumed session could not reproduce the number in a draft.
- A control episode can be a candidate at up to five matched days, one per offset in the relaxation
  window. **One candidacy per (set, control) survives**, chosen by the strictest rung the pair can
  satisfy, then the closest post-discharge day, then the fingerprint. Ordering by closeness first
  would silently discard a pair that matched on weekday class at an offset of one while failing it at
  an offset of zero, and would push the whole set down a relaxation rung for no reason.

**The two caps, and the order they are applied in.** First the per-set cap of **5**, ranking by
fingerprint within the set; then the per-participant cap of **3 control landmarks across the whole
study**, ranking that participant's surviving selections by fingerprint. Applying the participant cap
first would spend a prolific participant's three slots on sets where they would not have been drawn
anyway. **This is not a sequential greedy assignment**, which one pass of SQL cannot express; it is a
fully determined two-pass rule, and its consequence is that some sets end with fewer than 5 controls.
That is expected and it is exactly what `ledger_matched_sets` reports.

**The relaxation ladder of 4.7**, applied per set, depending only on risk-set **size**, which is a
count, never on an outcome or an estimate. The three rungs are nested, so the counts are taken once:

| `match_rung` | Rule | Chosen when |
|---|---|---|
| 1 | same post-discharge day **and** same day of week | at least 2 eligible controls at rung 1 |
| 2 | post-discharge day within 2 **and** same weekday-versus-weekend class | otherwise, if at least 2 at rung 2 |
| 3 | post-discharge day within 2, no day-of-week restriction | otherwise. **Carry a day-of-week fixed effect in the conditional model for that set**, reduced to a weekend indicator when the set is thin |

**Inference is person-clustered.** Conditional logistic regression assumes independent matched sets,
and a participant appearing in several sets breaks that assumption. `06_analysis_gate.py` carries a
person-clustered robust variance and a person-level cluster bootstrap of `B = 1,000`; where the two
disagree, the bootstrap interval is the one reported.

---

### 8.15 `{DERIVED}.attrition`

**Purpose.** The **nineteen-rung ladder of `ANALYSIS-PLAN` 2.6, exactly.** That table is the single
authoritative rung list; `CLAUDE.md` section 4 and `EXPORT-CONTRACT.md` sections 3.3 and 7.2
transcribe it and do not extend it, and `local/verify.py` asserts **set equality** of the slug column
against the plan.

**Grain.** Exactly 19 rows; the procedure raises otherwise. **Derives from:** `episodes`,
`episodes_eligible`, `events`, `cs_spine`, `{CDR}.person`, `{CDR}.procedure_occurrence`.
**Partition/cluster:** none. **Counts are participant-derived and are TRUE INTEGERS.**

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `step` | INT64 | - | never null | 1 through 19, the plan's fixed order |
| `slug` | STRING | - | never null | the plan's rung slug |
| `kind` | STRING | - | never null | `'exclusion'`, `'conversion'`, `'terminal'` |
| `unit` | STRING | - | never null | `'persons'`, `'persons to episodes'`, `'episodes'`, `'episodes to events'`, `'events'` |
| `n_in` | INT64 | the rung's unit | never null | exact count entering the rung |
| `n_dropped` | INT64 | the rung's unit | **null on steps 16, 17 and 19** | exact count removed |
| `n_out` | INT64 | the rung's unit | never null | exact count leaving |
| `n_carried_forward` | INT64 | **persons** | **null on all eighteen rungs but step 2** | persons carried out of the conversion |
| `reason` | STRING | - | **never null** | keyed off `kind`, per `EXPORT-CONTRACT.md` 3.3: the rung's own **`slug`** on an `exclusion` rung, the literal `'unit_change'` on a `conversion` rung, the **empty string** on a `terminal` rung. The printable sentence is `LABELS[slug]` in `07_export.py`, keyed by `slug` and not by this column |
| `closes_exact` | BOOL | - | never null | asserted on the true integers, before any rounding. **True by construction on eighteen of the nineteen rungs**; see the map below before reading it as evidence |
| `junction_map` | STRING | - | never null | **which map produced this ladder** |
| `built_at` | TIMESTAMP | UTC | never null | `build_params` |

#### The nineteen rungs

| step | slug | kind | unit |
|---|---|---|---|
| 1 | `program_participants` | exclusion | persons |
| 2 | `episode_construction` | conversion | persons to episodes |
| 3 | `excl_trauma_malignancy_infection` | exclusion | episodes |
| 4 | `excl_ed_encounter_not_elective` | exclusion | episodes |
| 5 | `excl_prior_operation_90_days` | exclusion | episodes |
| 6 | `excl_simultaneous_cervical_lumbar` | exclusion | episodes |
| 7 | `excl_region_unspecified_only` | exclusion | episodes |
| 8 | `excl_thoracic_only` | exclusion | episodes |
| 9 | `excl_add_on_code_only` | exclusion | episodes |
| 10 | `excl_missing_discharge_date` | exclusion | episodes |
| 11 | `excl_no_wearable_data` | exclusion | episodes |
| 12 | `excl_inadequate_baseline_wear` | exclusion | episodes |
| 13 | `excl_not_first_eligible_episode` | exclusion | episodes |
| 14 | `excl_no_computable_post_discharge_window` | exclusion | episodes |
| 15 | `excl_window_truncated_by_death_or_reoperation` | exclusion | episodes |
| 16 | `analytic_cohort` | terminal | episodes |
| 17 | `events_identified` | conversion | episodes to events |
| 18 | `excl_event_without_computable_landmark` | exclusion | events |
| 19 | `events_analyzable` | terminal | events |

#### How each count is formed

| step | `n_in` | `n_dropped` | `n_out` |
|---|---|---|---|
| 1 | persons in `{CDR}.person` | persons with no qualifying spine concept | persons carrying one |
| 2 | `n_out(1)` | persons carrying a concept whose records yield no dated episode | **episodes** |
| 3 to 15 | `n_out` of the previous rung | episodes whose `first_fail_step` equals this step | `n_in - n_dropped` |
| 16 | `n_out(15)` | null | the analytic n |
| 17 | `n_out(16)`, episodes | null | **events**, first events among analytic episodes; may be zero |
| 18 | `n_out(17)` | first events with `structurally_uncomputable_landmark` | `n_in - n_dropped` |
| 19 | `n_out(18)` | null | `n_in` |

#### The closure mechanics, implemented rather than approximated

1. **Every exclusion rung** asserts `n_in - n_dropped = n_out`, both sides in one unit.
2. **Step 2 cannot**, because `n_in` is persons and `n_out` is episodes. It carries
   `n_carried_forward` in persons and asserts `n_in - n_dropped = n_carried_forward` **together
   with** `n_out >= n_carried_forward`, since a carried person yields at least one episode. An
   explicitly labelled re-basing, never a silent one.
3. **Steps 17 and 19 count events**, carry no `n_dropped`, and are **excluded** from the global "sum
   of drops plus the analytic n equals the starting n" assert. Steps 17 to 19 close among themselves:
   `n_out(17) - n_dropped(18) = n_out(19)`.
4. A fourth, uniform check runs over all nineteen: `n_in(k) = n_out(k - 1)`. It holds across **both**
   conversions, because a conversion re-bases the unit but not the count.
5. The episode segment: the sum of `n_dropped` over steps 3 to 15, plus `n_out(16)`, equals
   `n_out(2)`. This is the assert that steps 4, 7, 8 and 13 would break if they were left implicit,
   which is the reason they are rungs and not prose.

**If it does not close, the procedure raises. Do not adjust a count to make it close.**

#### What `closes_exact` actually tests, and where it is empty

The five mechanics above state the identities. They are **not all tested**, because the `counts` CTE
computes one side of most of them **from** the other side, and an expression compared against itself
cannot fail. This is the map. Read it before treating the column as evidence.

| rungs | why `closes_exact` cannot go false there | verdict |
|---|---|---|
| 1 | `n_dropped` is **defined** as `n_persons_total - n_persons_with_concept` | tautology |
| 2 | `n_dropped` is **defined** as `n_persons_with_concept - n_persons_with_episode`, so the `n_carried_forward` identity is arithmetic; and `n_out >= n_carried_forward` is `COUNT(*) >= COUNT(DISTINCT person_id)` over one table | tautology |
| 3 to 15 | `n_out` is **defined** as `n_in - n_dropped`, and `n_in` is the running-sum window over those same drops, so `n_in(k) = n_out(k - 1)` is that same algebra again. Both conjuncts | tautology |
| 17 | `n_in` is `n_analytic`, the same `tot` expression as `n_out(16)`, and the rung's own test is `n_dropped IS NULL AND n_out >= 0`, which a count cannot fail | tautology |
| 18 | `n_out` is **defined** as `n_in - n_dropped` | tautology |
| 19 | `n_in` and `n_out` are both the same `tot` expression as `n_out(18)` | tautology |
| **16** | `n_in = n_out(15)` reconciles `COUNTIF(is_eligible)` against `COUNT(*) FROM episodes` less the `first_fail_step` histogram: **two different aggregations of `episodes_eligible` that a real defect can separate** | **the one real identity** |

The **episode-segment** check is that same step-16 identity rearranged, so it is a second test of the
one thing rather than a nineteenth test of a nineteenth thing. The **event-segment** check is a
tautology: `n_out(19)` is written as the same expression as `n_out(17) - n_dropped(18)`.

**Eighteen of the nineteen `closes_exact` values are therefore true by construction, and the closure
column's whole empirical content is step 16.** It is not small. It is exactly the failure that can
happen here, an episode that is neither eligible nor charged to a rung, and the ladder does catch it.
But **nothing downstream may read `closes_exact` as nineteen independent checks**, and `make_strobe.py`
must not re-derive confidence from the column being uniformly true; `attrition.closes` in
`EXPORT-CONTRACT.md` 3.3 is the conjunction of these, so it carries step 16's guarantee and no more.

This was left as computed rather than rebuilt on independently counted `n_out` values because steps
1, 2, 17, 18 and 19 have no second source that is not a second scan of a large `{CDR}` table, so a
partial rebuild would still need this table and would buy a false uniformity across the rungs it did
not reach. `build_all.sql` carries the same map in place.

`ladder_breaks` counts `closes_exact IS NOT TRUE` rather than `NOT closes_exact`, because `COUNTIF`
does not count a null and a null `closes_exact` would otherwise pass the stop condition in silence.
No path produces one; the clause is there so that none can.

**An episode is counted once, at the first rung it fails.** That is why trauma, malignancy and
infection are **one** composite rung rather than three: an episode can trip more than one at a time,
so three rungs would carry order-dependent counts a reader would misread as prevalences, and at this
cohort size three rungs would very likely produce three suppressed rows where the composite produces
one disclosable one. The per-indication breakdown goes to `ledger_exclusion_reasons`.

**The order is fixed and is not an implementation detail.** Reordering changes every rung's
`n_dropped` without changing the analytic n, which changes what the Figure 1 exclusion boxes say.
Reordering is an amendment under `ANALYSIS-PLAN` section 13.

**Only rounded counts are ever printed**, so the printed boxes will not reconcile arithmetically. The
rounding footnote is published and the displayed numbers are never adjusted to make them add up. The
local side asserts `|n_in - n_dropped - n_out| <= 30`, because each of three independently rounded
counts carries an error of at most 10; the exporter asserts **exact** closure on the unrounded
integers and exports `closes_exact` per rung.

---

### 8.16 `{DERIVED}.ledger_exclusion_reasons`

**Purpose.** STROBE companion ledger 3 of 5. The breakdowns that **cannot** be rungs, because rows
here may overlap and are explicitly **not a partition**: an episode excluded at rung 3 may carry
trauma **and** malignancy and is counted under both.

**Grain.** One row per reason detail within a rung. **Rows:** about 20. **Derives from:**
`episodes_eligible`, `baseline`, `attrition`.

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `step` | INT64 | - | never null | a rung step. The procedure raises if the pair is not a rung |
| `slug` | STRING | - | never null | that rung's slug |
| `reason_detail` | STRING | - | never null | the detail slug within the rung |
| `n_episodes` | INT64 | episodes | never null | exact count. **Round and floor-test before export** |
| `n_denominator` | INT64 | episodes | never null | the honest denominator for the printed share |
| `junction_map` | STRING | - | never null | `build_params` |

`07_export.py` computes `share_of_step_dropped = n_episodes / n_denominator` and applies the
disclosure floor to both before either is printed. **`n_denominator` is not always the rung's
`n_dropped`**: for the rung 4 rescue routes the population at risk of being rescued is the set of
episodes with an emergency department encounter, not the set that failed the rung.

| step | `reason_detail` values | denominator |
|---|---|---|
| 3 | `trauma`, `spinal_cord_injury`, `malignancy`, `metastatic_disease`, `spinal_infection` | episodes dropped at rung 3 |
| 4 | `ed_encounter_present`, `rescue_elective_coded`, `rescue_degenerative_index`, `rescue_degenerative_outpatient_90d` | episodes with an emergency encounter |
| 12 | `no_valid_baseline_day`, `fewer_than_seven_valid_days`, `baseline_span_under_14_days` | episodes dropped at rung 12 |
| 14 | `no_analyzable_day_in_window`, `not_at_risk_in_window` | episodes dropped at rung 14 |
| 15 | `death`, `repeat_spine_operation` | episodes dropped at rung 15 |
| 16 | `censoring_none`, `censoring_death`, `censoring_repeat_spine_operation`, `censoring_cdr_observation_cutoff` | the analytic cohort |

The step 16 rows are the **censoring reasons of 2.3** over the analytic cohort. A censored day is not
a missing day: the episode is not at risk on it and the window is shortened.

---

### 8.17 `{DERIVED}.ledger_wear_by_day`

**Purpose.** STROBE companion ledger 4 of 5. Wear availability by group and post-discharge day.

**Grain.** One row per group slug per post-discharge day 1 to 90. **Rows:** up to 7 by 90, so 630.
**Derives from:** `drd_daily`, `features`.

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `group_slug` | STRING | - | never null | one of the seven group slugs of 2.4 |
| `group_order` | INT64 | - | never null | 1 to 4 the four groups, 5 `all_groups`, 6 `fusion`, 7 `decompression` |
| `day` | INT64 | post-discharge days | never null | 1 to 90 |
| `n_at_risk` | INT64 | episodes | never null | episodes in the group not censored on that day |
| `n_valid_wear` | INT64 | episodes | never null | of those, valid wear days |
| `n_analyzable` | INT64 | episodes | never null | of those, analyzable days |
| `n_inpatient` | INT64 | episodes | never null | of those, days inside a readmission stay |
| `junction_map` | STRING | - | never null | `build_params` |

**All seven group slugs are emitted**, because the group set that survives is decided by the collapse
level of 2.5, which is decided on the attrition ladder **after** this table exists. No consumer may
hardcode four groups, four Table 1 columns or four Figure 2 series; read `cohort.groups` and
`tables[key].columns` at run time. The plan writes the two collapse-level-2 groups as `2a` and `2b`;
this is an integer column, so they are 6 and 7 here, and `07_export.py` owns the print order.

**The absence rule of Figure 2 is an EXPORT-TIME rule, not a build-time one.** A day whose `n_at_risk`
fails the disclosure floor is dropped from the **file** by `07_export.py` rather than written as a
suppressed row, because a list of which days were hidden recovers the pattern it was hiding. This
table carries every day.

---

### 8.18 `{DERIVED}.ledger_matched_sets`

**Purpose.** STROBE companion ledger 5 of 5. The distribution of controls per case, which is the
number that shows whether the two caps bit and how hard.

**Grain.** One row per distinct set size. **Rows:** a handful, and **zero when Arm A produced no
sets**. **Derives from:** `risk_sets`.

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `set_size` | INT64 | controls per case | never null | 0 to 5 |
| `n_sets` | INT64 | sets | never null | exact count |
| `n_cases` | INT64 | cases | never null | one case per set, so equal to `n_sets` |
| `junction_map` | STRING | - | never null | `build_params` |

The table is created even when empty, because a file that is present and empty and a file that is
absent are different claims and only one of them is checkable. `07_export.py` writes the one-row
"no Arm A analysis at this tier" statement when it reads zero rows here. The secondary-suppression
rule applies across `n_sets` rows, which partition a disclosed total.

---

### 8.19 `{DERIVED}.ledger_variable_missingness`

**Purpose.** The **count half** of STROBE companion ledger 2 of 5, variable provenance. Every other
column of that ledger (`display_label`, `role`, `source_table`, `source_concept_set`, `derivation`,
`unit`, `missing_handling`) is a **specification fact** owned by `07_export.py`, which is also where
the display strings live. Only `n_missing` is a fact about the data.

**Grain.** One row per analysis variable. **Rows:** twelve. **Derives from:** `features`,
`drd_daily`, `events`.

| column | type | unit | null convention | provenance |
|---|---|---|---|---|
| `variable` | STRING | - | never null | the analysis variable's machine name |
| `n_total` | INT64 | rows | never null | the denominator for that variable's grain |
| `n_missing` | INT64 | rows | never null | exact count. Round and floor-test before export |
| `junction_map` | STRING | - | never null | `build_params` |

Variables emitted: `age_at_index`, `sex_at_birth`, `race_concept_id`, `ethnicity_concept_id`, `bmi`,
`charlson_score`, `los_days`, `device_family`, `baseline_steps`, `procedure_group`, `daily_deficit`,
`r72`. The first ten are per episode; `daily_deficit` is per accrual-window person-day; `r72` is per
first event. **`n_total` is the denominator of that row's own grain**, which is why it is a column
rather than one number for the table: reading a single denominator across all twelve rows misreads
`daily_deficit` and `r72` by orders of magnitude.

**A row here counts the evidence of absence, never the substituted value.** Where `features`
substitutes, it also carries the flag that records the substitution, and the row counts the flag:
`bmi` counts `bmi_missing`, `charlson_score` counts `charlson_missing`. Counting
`charlson_score IS NULL` instead is unsatisfiable, because the `IFNULL` scoring rule makes that column
non-null by construction, and the row would report zero on every run. `sex_at_birth` and
`device_family` count their own `'other_or_unknown'` level, which **is** the evidence rather than a
substitution over it.

**Three rows are expected to be structurally zero, and only these three:** `los_days`, because rung 10
removed every episode with no discharge date; `baseline_steps`, because rung 12 removed every episode
with no baseline; and `procedure_group`, because it is null only for the simultaneous, thoracic-only
and unspecified-region episodes that rungs 6, 7 and 8 removed. A zero there is a true statement about
the cohort. A zero produced by a substitution is not.

**The fifth ledger, the concept-set registry, is not built by SQL.** It comes from
`cs_spine.registry_rows()` in Python and its columns are `cs_spine.REGISTRY_COLUMNS`. It carries no
counts and therefore never suppresses.

---

## 9. Known gaps and open runtime probes

Stated here so a downstream module does not rediscover them as bugs.

| # | Item | Status |
|---|---|---|
| 1 | The per-zone minute column of `heart_rate_summary` | **Probe.** Parameter 2. Existence checked; the build raises if absent |
| 2 | That heart-rate zones partition the day without double-counting | **Probe.** Enforced: any person-date over 1,440 summed zone minutes raises and names the S2 contingency |
| 3 | The `device` table's model column | **Probe.** Parameter 3. `''` builds without a device covariate |
| 4 | Emergency department and inpatient `visit_concept_id` values | **Probe.** Parameters 4 and 5, enumerated by `01_probe.py`. Empty arrays raise |
| 5 | `person.sex_at_birth_concept_id` exists | **Checked at run time.** Raises if absent |
| 6 | `visit_occurrence.visit_source_value` carries elective or scheduled wording | **Unverified.** The elective proxy at rung 4 and the elective-admission exclusion in `events` both depend on it. If the CDR does not populate it, both rescues silently never fire and rung 4 over-excludes. `01_probe.py` should sample its distinct values |
| 7 | `visit_detail` population | **Not used.** Deliberately, see 8.9 |
| 8 | ICD-9-CM indications are not screened | **Accepted gap**, see 8.3 |
| 9 | Body mass index concept id 3038553 with a 10 to 80 plausibility window | **Choice made here**, stated so it is auditable |
| 10 | "Near-complete window" at 28 of 35 days | **Choice made here**, because the plan does not define it and a Table 1 row must not be defined after the distribution is seen |
| 11 | `{PREP}` is unused | **Deliberate**, see section 1 |
| 12 | The observation weight at a landmark on post-discharge day 1 or earlier | **Open, and it is a prespecification question, not a build one.** The weights of `ANALYSIS-PLAN` 3.7 have no input at any matched day of 4 or earlier. 8.13 supplies both a countable flag and a wearable-grid alternative; the plan names which rule applies and the count is reported with the estimate |
| 13 | Weekday and weekend baselines exist in `baseline` and are not yet a named sensitivity row | **Open in `ANALYSIS-PLAN` section 6.** The protocol asks for the split; the columns and their two denominators are in 8.8. Until the plan carries a slug, nothing fits on them |

---

## 10. Cross-references

| Question | Authority |
|---|---|
| The nineteen rungs, their order and their display labels | `prespecification/ANALYSIS-PLAN.md` section 2.6 |
| The seven procedure-group slugs and the four collapse levels | `ANALYSIS-PLAN.md` sections 2.4 and 2.5 |
| The plotted sensitivity rows and the supplementary ones, and how many of each | `ANALYSIS-PLAN.md` section 6, which is the authority on the count. This file deliberately does not carry a number that would go stale on the next amendment |
| Whether a weekday or weekend baseline sensitivity is fitted, and on which denominator | `ANALYSIS-PLAN.md` sections 2.2 and 6; the columns and the two denominators are in 8.8 |
| The observation-weight rule at a landmark before post-discharge day 1 | `ANALYSIS-PLAN.md` section 4.4; the inputs a rule can use are in 8.13 |
| The five valid-wear-day definitions | `ANALYSIS-PLAN.md` section 2.1 |
| The bundle paths, the suppression representation and the five ledgers | `prespecification/EXPORT-CONTRACT.md` sections 1, 5 and 5.6 |
| Every printable string | `EXPORT-CONTRACT.md` section 7, transcribed into `LABELS` |
| The disclosure floor and `disclosable(n)` | `pipeline/disclosure.py` |
| The concept set and its region tagging | `pipeline/cs_spine.py` |
| The only query path, the byte cap and the placeholders | `pipeline/00_config.ipynb` |
