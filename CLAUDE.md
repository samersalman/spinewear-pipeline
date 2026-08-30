# CLAUDE.md: project constitution for `v1/`

Read this file first, in full, at the start of every session in this directory. Then read
`SESSION-LOG.md` for state. Everything below is binding on you. Where this file and your own
judgment disagree, this file wins; if you think it is wrong, say so and stop, do not route around it.

---

## 1. What this project is

This is a wearable-linked retrospective cohort study in the All of Us Research Program, working
title "Cumulative ambulatory activity loss after elective cervical and lumbar spine surgery: a
wearable-linked cohort study in the All of Us Research Program." It asks how much baseline-normalized
walking patients actually lose after elective cervical and lumbar decompression and fusion, and
whether that loss differs by anatomic region and fusion status. The primary endpoint is Digital
Recovery Debt accrued over post-discharge days 1 to 35,
`DRD_i = sum over d = 1..35 of max(0, 1 - S_id / B_i)`, where `S_id` is participant i's step count on
post-discharge day d and `B_i` is the median valid daily step count over postoperative days -30 to
-8. The unit is baseline-equivalent activity days lost, bounded at 35: one activity day lost is the
ambulation that patient would normally complete in one day. The secondary result is the protocol's
own feasibility gate, meaning how many EHR-recorded acute-care encounters through day 90 are
observable with a computable proximal step signal, and what that count implies for wearable
early-warning research in this data source. The deliverable is a Methods plus Results draft with 3
figures and 3 tables, in Markdown and Word.

---

## 2. The hard rules

Five rules carried from the project brief. Violating any one of them fails the work, not the style
review.

1. **Disclosure.** No participant-level value may ever reach a printed, returned, or exported
   surface. Counts 1 to 20 are suppressed; larger counts round to the nearest 20, ties away from
   zero. No module in `pipeline/` or `local/` writes its own comparison against a bare floor
   literal, and `local/verify.py` greps the tree for one. A percentage is suppressed whenever its
   numerator count is suppressed, because a percentage times a disclosed denominator recovers the
   hidden count exactly. Percentages are computed from the **rounded numerator over the rounded
   denominator** and printed to **zero decimals**, so that a reader can reproduce every printed
   percentage from the printed counts and from nothing else. **A rate is bound by the same
   arithmetic**, rounded numerator over rounded denominator, and is not produced at all when its
   numerator is not disclosable, because a rate from a true numerator printed beside a rounded
   denominator multiplies back to the hidden count exactly. No `df.head()`, no row prints, no
   per-person values, ever. This is sharper here than in an ordinary project: browser automation
   ships screenshots and DOM to an external model, so "printed" includes anything rendered inside
   the VM where the model can see it.

   **Three predicates, and which one to call is the single most repeated source of error in this
   build.** They are not synonyms and two of them disagree on the number 20 by design. Import them
   from `pipeline/disclosure.py`; never re-derive one from the other.

   | Predicate | The question it answers | Call it |
   |---|---|---|
   | `disclosable(n)` | is this **true** count, before any rounding, allowed to be disclosed at all | on a raw count, **before** `round20`. The arbiter of the floor: true for a real zero and for a whole count strictly greater than 20 |
   | `is_legal_disclosed_count(cell)` | is this **rendered** cell a legal thing to write down | at the export gate and on arrival, on a cell that has **already** been through `round20`. True for a sanctioned suppressed cell, for a zero, and for a whole positive multiple of 20 |
   | `is_bundle_suppressed(cell)` | does this rendered cell say "hidden" in any spelling the bundle sanctions | on a frame headed for `safe_export`, or read back out of an exported CSV. Recognises the sentinel, the figure token `SUPPRESSED`, and the section 7.5 sentences. `is_suppressed()` is the narrow sentinel-only form and is the wrong one to ask of a bundle cell |

   **They disagree on 20 and that is the fix, not the bug.** `disclosable(20)` is false, because a
   true count of 20 is below the floor. `is_legal_disclosed_count(20)` is true, because `round20`
   maps a true 21 through 29 to the numeral 20. Collapsing them cost this build a real defect: the
   export gate asked `disclosable()` of a cell that was already rounded, so a correctly rounded
   ladder was refused by the module that produced it and `07_export.py` could not export the STROBE
   ladder or Table 1. The one residual gap is stated in the module rather than left to be found: a
   raw 20 and a rounded 20 are the same integer at the gate, so the gate accepts a raw 20, and the
   floor on the true count is enforced upstream where the true count still exists.

   **Counts render through `disclosure.render_count`, and only onto a display surface.** It is the
   one place the thousands separator is applied, so `n = 1,240` has a single implementation instead
   of one per module. In **exported bytes** a count stays bare: `safe_export` writes CSV, a
   separator in a numeric cell is a data corruption, and `07_export.py` therefore never calls
   `render_count` at all. Display surface, separator; export surface, bare.

   **Display convention.** One sentence, worded identically here, in `ANALYSIS-PLAN.md` section 8
   rule 2, and in the `pipeline/disclosure.py` module docstring, and it is the sentence the Methods
   footnote carries. Do not paraphrase it. "Counts of 20 or fewer are suppressed; larger counts are
   rounded to the nearest 20, so a disclosed 20 represents a true count of 21 to 29."
2. **Cost.** No BigQuery query executes without a dry-run byte estimate printed first, and every
   query carries a hard `maximum_bytes_billed` cap so an over-budget query **fails rather than
   bills**.
3. **Prespecification precedes counts.** Code implements `prespecification/ANALYSIS-PLAN.md`. It
   never chooses a model, a window, or a cutpoint after seeing a number. One primary estimand per
   aim, no alpha adjustment on those two, everything else labeled explicitly as not
   multiplicity-controlled.
4. **Reproducibility.** Seeded everywhere. BigQuery row and matched-set sampling uses
   `FARM_FINGERPRINT` with a fixed seed, never `RAND()`. The Python and numpy seed is `SEED = 0`.
5. **House prose rules**, asserted at write time on rendered strings, not grepped afterwards:
   no em-dash (U+2014) anywhere; the en-dash (U+2013) is kept and only as a range separator; no
   `snake_case` token in any user-visible string; every table and figure prints its own denominator;
   numeral style is `P < 0.001`, `P = 0.223`, `42.3%`, `n = 1,240`, en-dash ranges, odds ratios to
   two decimals, absolute risks before relative.

Two more rules specific to this deliverable.

6. **Length.** Methods plus Results is **1300 words or fewer**. Roughly 700 Methods and 600
   Results. **This file owns that budget.** It is a delivery constraint on the manuscript, not an
   analysis rule and not an export rule, so it is deliberately absent from
   `prespecification/ANALYSIS-PLAN.md` and from `prespecification/EXPORT-CONTRACT.md`; neither of
   them is the place to look for it, and neither is the place to change it.
   **`local/verify.py` enforces it**, on the same extracted text it already uses for stop condition
   7. It pulls the text back out of the rendered `manuscript/methods_and_results.docx`, keeps the
   Methods and Results bodies, drops the section headings, every figure and table caption, legend
   and footnote, the reference list and every bracketed citation marker, and the contents of table
   cells, then counts whitespace-separated tokens. Above 1300 it exits non-zero.
   `local/manuscript.py` prints the same count as it assembles, so the ceiling is visible while the
   prose is being cut rather than only after it is finished. A hard ceiling, not a target to
   negotiate at assembly time.
7. **Exhibit budget.** Exactly **3 figures and 3 tables**, with an enforced split: **Table 2 carries
   adjusted absolute levels and Figure 3 carries contrasts**, so neither repeats the other.
   Everything else, meaning covariate effects, the daily-trajectory model, and the full sensitivity
   grid, goes to the supplement.

   **The bundle's file count is not the exhibit count, and neither is its key count.**
   `EXPORT-CONTRACT.md` writes one CSV per printed thing rather than one per exhibit: Table 2 has a
   separate footer file and Table 3 is two parts. Counting files is the obvious mistake; counting
   `results.json` keys is the same mistake one level in, because `tables` carries four primary keys
   for three primary tables. The budget is counted over distinct `exhibit` values, which is what
   `MANIFEST.csv` already labels and what contract 3.8 declares per block as `exhibit_set`.
   The bundle also carries two **supplementary** exhibits, the event-centered curve and the collider
   comparison, which are drawn and checked but are not main-text exhibits. `ANALYSIS-PLAN.md`
   section 9 owns the main-text list; where the contract and the plan disagree, the plan wins and the
   contract is amended, never the reverse and never at run time.

---

## 3. Where each thing runs

The compliance boundary is the architecture. There are two sides and code belongs to exactly one.

**Inside the perimeter (BigQuery plus one small VM).** Every operation that touches participant rows:
concept-set construction, episode construction and exclusions, Fitbit feature engineering, baseline
and daily-deficit computation, risk sets, all models, all bootstraps. Derived tables are materialized
into `{GOOGLE_PROJECT}.spinewear_v1`, in the CDR's own location. The perimeter emits only
`results.json`, `tables-csv/*.csv`, the five STROBE companion ledgers in `ledgers-csv/*.csv`, and
the plot-ready aggregate series in `figures-csv/*.csv`, in which **every count cell has already
been cleared by `disclosure.disclosable(n)` on its true value and rounded**, so that what crosses
the boundary satisfies `is_legal_disclosed_count()` and nothing on the local side ever sees a true
count; each row carrying its contributing n, each export stamped with an md5. One artefact sits
outside the bundle by name, `probe/probe_result.json`, under `EXPORT-CONTRACT.md` section 1.2.

**Locally (free, iterate as much as you like).** Figure rendering, table rendering, prose, docx
assembly, the STROBE checklist, and verification. Local code reads the exported aggregates and never
needs row-level data.

**Why figures render locally rather than in the VM.** Three reasons, and the third is the binding one.
It keeps the full house matplotlib style available without installing anything in the VM; it makes
figure iteration cost nothing, since a rendered figure is free locally and costs VM time inside; and
it removes any chance of a plot exposing a small cell, because the VM never draws anything and only
ever exports pre-aggregated, already-suppressed series. No image crosses the boundary. The VM exports
the plotted series, not the plot.

---

## 4. The cohort ladder

**Nineteen rungs.** `prespecification/ANALYSIS-PLAN.md` section 2.6 is the single authoritative rung
list for this study. The table below transcribes it and does not extend it; `pipeline/03_cohort.py`
emits it; `local/verify.py` asserts set equality against `figure1_strobe_ladder.csv`, so a rung
invented here fails verification rather than propagating. Columns emitted per rung:
`step, slug, kind, unit, n_in, n_dropped, n_out, reason`.

Phase 3 fills these counts. Until then every count reads `PENDING` and no downstream number may be
written that implies one. A slug is an identifier and is never printed; every user-visible string
comes from the display label beside it. The `reason` strings, which are the exclusion-box sentences
Figure 1 prints, are deliberately **not** copied into this file: `local/verify.py` holds them to
character equality against the plan, and a second unchecked copy here would be one more place for
those strings to drift. Read them out of plan section 2.6.

| step | slug | kind | unit | n_in | n_dropped | n_out | display label |
|---|---|---|---|---|---|---|---|
| 1 | `program_participants` | exclusion | persons | PENDING | PENDING | PENDING | Participants in the Controlled Tier release |
| 2 | `episode_construction` | conversion | persons to episodes | PENDING | PENDING | PENDING | Spine surgical episodes |
| 3 | `excl_trauma_malignancy_infection` | exclusion | episodes | PENDING | PENDING | PENDING | Episodes after the nonelective-indication exclusions |
| 4 | `excl_ed_encounter_not_elective` | exclusion | episodes | PENDING | PENDING | PENDING | Elective episodes |
| 5 | `excl_prior_operation_90_days` | exclusion | episodes | PENDING | PENDING | PENDING | Episodes with no prior operation within 90 days |
| 6 | `excl_simultaneous_cervical_lumbar` | exclusion | episodes | PENDING | PENDING | PENDING | Episodes at a single anatomic region |
| 7 | `excl_region_unspecified_only` | exclusion | episodes | PENDING | PENDING | PENDING | Episodes with an established anatomic region |
| 8 | `excl_thoracic_only` | exclusion | episodes | PENDING | PENDING | PENDING | Cervical or lumbar episodes |
| 9 | `excl_add_on_code_only` | exclusion | episodes | PENDING | PENDING | PENDING | Episodes defined by a primary procedure code |
| 10 | `excl_missing_discharge_date` | exclusion | episodes | PENDING | PENDING | PENDING | Episodes with a recorded discharge |
| 11 | `excl_no_wearable_data` | exclusion | episodes | PENDING | PENDING | PENDING | Wearable-linked spine episodes |
| 12 | `excl_inadequate_baseline_wear` | exclusion | episodes | PENDING | PENDING | PENDING | Episodes with adequate preoperative baseline wear |
| 13 | `excl_not_first_eligible_episode` | exclusion | episodes | PENDING | PENDING | PENDING | First eligible episode per participant |
| 14 | `excl_no_computable_post_discharge_window` | exclusion | episodes | PENDING | PENDING | PENDING | Episodes with a computable post-discharge day 1 to 35 window |
| 15 | `excl_window_truncated_by_death_or_reoperation` | exclusion | episodes | PENDING | PENDING | PENDING | Analytic cohort |
| 16 | `analytic_cohort` | terminal | episodes | PENDING | n/a | PENDING | Analytic cohort |
| 17 | `events_identified` | conversion | episodes to events | PENDING | n/a | PENDING | Acute-care events through day 90 |
| 18 | `excl_event_without_computable_landmark` | exclusion | events | PENDING | PENDING | PENDING | Analyzable acute-care events |
| 19 | `events_analyzable` | terminal | events | PENDING | n/a | PENDING | Analyzable acute-care events |

An exclusion rung's display label names the box of **survivors** below it, which is why steps 15 and
16 share the label "Analytic cohort".

**The order is fixed and is not an implementation detail.** A ladder counts each episode once, at
the first rung it fails, so reordering changes every rung's `n_dropped` without changing the
analytic n, and that changes what the Figure 1 exclusion boxes say. Reordering is an amendment under
plan section 13.

**Closure asserts. There is no longer one global identity, and treating it as one will fail on the
first real run.** The ladder crosses two unit changes, so the assert is evaluated within unit and
each conversion is recorded as an explicitly labeled re-basing rather than a silent one.

- **Every exclusion rung** asserts `n_in - n_dropped = n_out`, both sides in the same unit.
- **Step 2 cannot assert that**, because its `n_in` is in persons and its `n_out` is in episodes. It
  carries a third count, `n_carried_forward`, in persons, and asserts
  `n_in - n_dropped = n_carried_forward` together with `n_out >= n_carried_forward`, since a carried
  person yields at least one episode. Its `n_dropped` is persons who carry a qualifying concept but
  whose records yield no dated episode.
- **Within the episode unit**, the sum of `n_dropped` over steps 3 to 15 plus the analytic n of step
  16 equals the `n_out` of step 2. Steps 4, 7, 8 and 13 would break this assert if they were left
  implicit, which is the reason they are rungs and not prose.
- **Step 17 carries no `n_dropped`**: every analytic episode is at risk for an event. It asserts only
  that its `n_in` equals the `n_out` of step 16, and its own `n_out` is a count of events, which may
  be zero.
- **Step 19 counts events, not episodes.** It carries no `n_dropped`, and steps 17 and 19 are both
  **excluded** from the global "sum of drops plus the analytic n equals the starting n" assert.
  Steps 17 to 19 close among themselves: `n_out(17) - n_dropped(18) = n_out(19)`.

Asserted in `pipeline/03_cohort.py`, by `assert_ladder()`, and again in the flow-figure builder. If
it does not close, raise. Do not adjust a count to make it close.

**A passing ladder assert is not evidence that the upstream arithmetic was checked, and
`03_cohort.py` says so in its own output.** Every check it runs is labelled **independent** or
**transport**, and the printed census gives the two counts separately rather than one total. The
arithmetic identities above are transport: inside the perimeter they are tautologies of the SQL that
produced the rows, so out here they fail only for a table that was hand-edited, truncated, partially
rebuilt, or left stale by a resumed session. That is a real failure mode and worth checking, but it
is a different claim from "the counts are right". The independent checks are recounts over
`episodes_eligible` and `features`: no episode both eligible and charged, none neither, every charge
landing on a rung in 3 to 15, and the three counts the analytic rung rests on. Read the census, not
just the exit code.

**Trauma, malignancy and infection are one rung, not three, and this file no longer promises
otherwise.** Section 4 used to name seven eligibility exclusions and promise that each would be
"labeled separately in the emitted ladder". **That promise is retired**, deliberately, and the
reason is written down here so that a future session does not helpfully restore it. The three
indications are applied as one composite screen over one 30-day lookback; an episode can trip more
than one of them at once; and a ladder counts each episode once, at the first rung it fails, so
three separate rungs would carry order-dependent counts that a reader would misread as prevalences.
At the cohort size this study expects, three rungs would also very likely produce three suppressed
rows where the composite produces one disclosable one, which loses the information rather than
refining it. The composite is step 3. The breakdown by indication goes to the STROBE
exclusion-reason ledger, where the disclosure floor permits it. Plan section 2.6 carries the same
decision and the same four reasons.

**Rounding footnote rule.** Every box in the flow figure is rounded to the nearest 20, so the boxes
will not reconcile arithmetically. **Publish the footnote saying so. Never adjust the displayed
numbers to make them add up.** The unrounded ladder closes; the rounded picture does not; the
footnote is the honest resolution and it is not optional.

---

## 5. File map

Rebuilt from `find . -path ./.git -prune -o -type f -print`, most recently after the six `local/`
modules landed, not from this file's own previous text, and checked in **both** directions: every
path in the table below was looked for on disk, and every file the `find` returned was looked for
in the table. Re-run the `find` before trusting any row. Sibling tasks write concurrently, and a
row that still says `PENDING` after the file has landed is the failure mode this section keeps
having: it had happened again to all three of `local/manuscript.py`, `local/make_strobe.py` and
`local/verify.py`, each of which was on disk while this table still called it unwritten.

**Four statuses, and the distinction between the last two is the one that goes stale.** An absent
path is not one kind of thing. Collapsing the two kinds is how `results/figures-csv/` sat under a
status that reads as an unfinished task for a directory nobody was ever going to author.

| Status | Meaning |
|---|---|
| `EXISTS` | found on disk by the `find` above. **No size is recorded in this column on purpose.** A line count in a map is a second thing to keep current, and it goes stale faster than a status does; `wc -l` is the authority on how big a file is, and the same rule retires assertion counts, row counts and stage counts of a module's own making |
| `EXISTS (empty)` | the directory is on disk and holds no file yet, at most a `.gitkeep` |
| `PENDING` | **a file this project has to write and has not written.** It is somebody's task, and it is a reason Phase 0 stays open |
| `AT RUNTIME` | **named by a contract, absent by design.** Nobody authors it. It appears when the phase that produces it runs, so it is never a task, never a gap, and never a reason to hold a phase open |

| Path | What it is for | Status |
|---|---|---|
| `.gitignore` | Ignores `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.DS_Store` and `probe/`. Those five are the only paths on disk that this map does not list file by file; the first four are build artifacts and the fifth is the `AT RUNTIME` probe directory, which is deliberately never committed because it is one file per CDR release | EXISTS |
| `CLAUDE.md` | This constitution. Read first, every session | EXISTS |
| `SESSION-LOG.md` | Pinned compliance and cost protocol, environment constants, prespecification lock, phase ledger, carried-forward warnings, handoffs | EXISTS |
| `prespecification/ANALYSIS-PLAN.md` | The locked prespecification. Owns all five slug vocabularies, the 19-rung ladder, and the disclosure rules. Version 1.5, LOCKED, amended five times before any count was seen. `SESSION-LOG.md` section 3 carries the whole chain | EXISTS |
| `prespecification/PLAN-HASH.txt` | The lock record: file, sha256, bytes, timestamp, tool. Written by `lock_plan.py`, never by hand | EXISTS |
| `prespecification/lock_plan.py` | Locks and checks the plan hash and the house prose rules. Stdlib only. `--check`, `--self-test` | EXISTS |
| `prespecification/EXPORT-CONTRACT.md` | The perimeter-to-local bundle contract: paths, keys, columns, labels, suppression representation. Its section 5.6 names the `ledgers-csv/` directory, its section 1.2 names the one artefact it places outside the bundle, and its section 11.4 is the dated register of obligations it has accepted and not discharged. Under active amendment, so read its version header rather than quoting a version from here | EXISTS |
| `prespecification/RUS-DRAFT.md` | The 8-page Research Use Statement for human approval. Never auto-submitted | EXISTS |
| `decisions/` | One locked decision per file, `YYYY-MM-DD-<slug>.md`. Two so far: recovery-debt window, spine region tagging | EXISTS |
| `pipeline/00_config.ipynb` | Ported Workbench config plus `dry_run_gb`, `q_guarded`, and the re-exported disclosure names. Idempotent within a kernel | EXISTS |
| `pipeline/disclosure.py` | Suppression helpers and the three predicates of section 2 rule 1: `disclosable`, `is_legal_disclosed_count`, `is_bundle_suppressed`, plus `round20`, `render_count`, `n_pct`, `safe_export` | EXISTS |
| `pipeline/cs_spine.py` | Region-tagged spine concept set, single source of truth for the 852 concepts | EXISTS |
| `pipeline/tests/` | `__init__.py`, `test_disclosure.py`, `test_cs_spine.py`, `test_drd_export_bridge.py`. Local pytest only; the VM runs the modules' own self-tests. See the note below this table for which pipeline modules that leaves uncovered | EXISTS |
| `pipeline/01_probe.py` | The Phase 2 runtime probes: Fitbit table existence and DDL, the `heart_rate_summary` layout and zone-partition verdict, the locked concept set against the live CDR, the emergency and inpatient visit concept enumeration, `visit_occurrence.visit_source_value`, and the environment facts. Also writes the concept-set registry ledger | EXISTS |
| `pipeline/02_pregate.py` | The cheap pre-gate upper-bound counts and the two concept-set gap measurements. Phase 2 hard stop. Loads `01_probe.py` through `importlib.util.spec_from_file_location`, because a module name beginning with a digit is not importable | EXISTS |
| `pipeline/build_all.sql` | The whole derived-table DAG as four persistent user-defined functions plus one BigQuery stored procedure, `build_all`, in marker-delimited stages. `grep -c '@stage-begin:'` is the authority on how many | EXISTS |
| `pipeline/DAG-SCHEMA.md` | The derived-table contract that `03_cohort.py` and `04_features.py` are written against without reading `build_all.sql`: every column, type, unit and null convention, the per-stage cost model, the disclosure boundary on `{DERIVED}`, and the known-gaps table | EXISTS |
| `pipeline/03_cohort.py` | Episodes, exclusions, the 19-rung attrition ladder, STROBE companion ledgers. Splits `build_all.sql` on its stage markers and prices each stage before the `CALL`. `assert_ladder()` labels every check independent or transport | EXISTS |
| `pipeline/04_features.py` | Validates the derived tables rather than recomputing them: valid wear days, baseline, daily deficit, risk sets, the seeded membership digest. Reads `{DERIVED}` only. `result["features ok"] is False` means the analysis modules must not run | EXISTS |
| `pipeline/05_analysis_drd.py` | Daily-deficit model, g-computation, clustered bootstrap. The two R rungs are an injected `r_runner=`; with none, trigger T0 fires and the ladder lands on the fractional-logit GEE | EXISTS |
| `pipeline/06_analysis_gate.py` | Tier-gated conditional logit and discrete-time risk model. Returns aggregates only; no identifier reaches the kernel | EXISTS |
| `pipeline/07_export.py` | `safe_export` bundle, plot-ready series only, plus the `--fixture` dummy bundle. Calls `disclosure.assert_suppression_vocabulary(LABELS)` at import | EXISTS |
| `local/figures.py` | House style, renders figures 2, 3 and 4 from the exported CSVs. Figure 1 is `make_strobe.py`'s | EXISTS |
| `local/tables.py` | House python-docx tables | EXISTS |
| `local/ledger.py` | Numeral ledger and the only local copy of the label table; refuses any hand-typed numeral in prose | EXISTS |
| `local/manuscript.py` | Methods plus Results at 1300 words | EXISTS |
| `local/make_strobe.py` | STROBE checklist and the Figure 1 flow figure | EXISTS |
| `local/verify.py` | Every prose numeral traces to `results.json`; slug set equality; the word ceiling; the bare-floor-literal grep. Non-zero exit on mismatch. **Under active authorship**, so read the file rather than this row for what it currently checks, exactly as the `EXPORT-CONTRACT.md` row says to read its version header | EXISTS |
| `local/fixtures/results/` | The data-free dummy bundle `07_export.py --fixture` writes, and the thing every local module's `_run_self_test()` runs against. **A real bundle, on disk and in git, not a placeholder:** 18 files, being 3 at its root (`MANIFEST.csv`, `MANIFEST.md5`, `results.json`), 4 in `figures-csv/`, 6 in `tables-csv/` and 5 in `ledgers-csv/`. It pins tier 4, so it cannot exercise the alternate exhibit set | EXISTS |
| `probe/probe_result.json` | The Phase 2 runtime probe result, the one artefact `EXPORT-CONTRACT.md` names **outside** the bundle, in its section 1.2. Written by `01_probe.py` and by nothing else, read by a later session in place of paying to re-run the probe. No `MANIFEST.csv` row, no md5, one file per CDR release, and gitignored for that reason. Created by the Phase 2 probe run | AT RUNTIME |
| `results/` | Where the exported bundle is unpacked byte for byte: `MANIFEST.csv`, `MANIFEST.md5`, `results.json` | EXISTS (empty) |
| `results/tables-csv/` | One CSV per printed table, in print order | EXISTS (empty) |
| `results/figures-csv/` | Plot-ready aggregate series, one CSV per figure. Required by `EXPORT-CONTRACT.md` section 1. Created when the first bundle is unpacked, in Phase 5 | AT RUNTIME |
| `results/ledgers-csv/` | The five STROBE companion ledgers required by `EXPORT-CONTRACT.md` section 5.6. Created in **Phase 2**, before the rest of the bundle exists, because `01_probe.py` writes `ledger_concept_set_registry.csv` into it; `07_export.py` writes the other four in Phase 4 and re-writes the first, with an md5 equality check against the probe's copy | AT RUNTIME |
| `figures/` | `figure_1..4.{png,pdf}` and `figure_legends.md`; `figure_4` is the supplementary event-centered plate | EXISTS (empty) |
| `checklists/` | `strobe.{csv,md}` | EXISTS (empty) |
| `manuscript/` and `manuscript/tables/` | `methods_and_results.{md,docx}` and table docx files | EXISTS (empty) |

**The other direction, which is the half this section never checked.** Set aside `.pytest_cache/`
and `__pycache__/`, whose contents appear and vanish with whoever last ran a module and which the
`.gitignore` row accounts for; **counting them would put a number in this section that changes
every time somebody runs a test**. What is left is what the map is answerable for: the `find`
returns **56 files, and every one of them is covered by a row above**: 3 at the repository root, 5 in
`prespecification/`, 2 in `decisions/`, 12 in `pipeline/` and 4 in `pipeline/tests/`, 6 modules in
`local/`, the 18 of the fixture bundle, and 6 `.gitkeep` placeholders in `checklists/`, `figures/`,
`manuscript/`, `manuscript/tables/`, `results/` and `results/tables-csv/`. Nothing on disk is
missing from this table. Going the other way, every path in this table was found on disk except the
**3 `AT RUNTIME` rows**, which are absent by design and are nobody's task. **No row carries
`PENDING` any more.** The status stays in the legend above because the distinction it draws against
`AT RUNTIME` is the one this section keeps getting wrong, not because a row still needs it.

**`local/` is complete: all six modules are on disk**, which retires both the sentence that called
it an empty untracked directory and the one that said three of the six were written. The fixture
bundle is committed, so a fresh clone gets it without paying for a run. `manuscript.py`,
`make_strobe.py` and `verify.py` all landed after the previous rebuild of this section, which is
what left three stale `PENDING` rows here; `verify.py` was still being appended to while this row
was corrected, and that is what its row records. Existing is not the same as being finished, and
this column has never claimed otherwise: `EXISTS` means the `find` returned the path, and `wc -l`
and the module's own self-test are the authorities on how much is behind it.

**Every module in `pipeline/` now exists, and seven of the eleven have no file in
`pipeline/tests/`.** The three test files cover the other four: `disclosure.py`, `cs_spine.py`, and
the `05_analysis_drd.py` to `07_export.py` seam, which was written after both of those modules
passed their own fixtures and could still not connect to each other.
**There is still no `test_probe.py` and no `test_pregate.py`**, and
`00_config.ipynb`, `03_cohort.py`, `04_features.py`, `06_analysis_gate.py` and `build_all.sql` have
no test file either. Those modules run their own in-module self-tests and are covered by nothing
else, which is a real gap and not a design choice: a self-test that ships inside the module it tests
runs only when somebody remembers to run it, and it cannot fail for a module that was deleted or
never imported. A test file for any module whose filename begins with a digit must load its subject
through `importlib.util.spec_from_file_location`, because such a module is not importable by name.
`02_pregate.py` does this for its own import of `01_probe.py` and `test_drd_export_bridge.py` does
it for both of its subjects; that is the pattern to copy rather than re-invent.

---

## 6. What is decided and closed

Do not reopen these. If a result makes one look wrong, log an amendment in `SESSION-LOG.md` with a
reason and a date, and say so in the Methods. Do not silently switch.

| Decision | Choice |
|---|---|
| Workspace | New, with its own Research Use Statement. The RUS is a public attestation, and wearable early warning after spine surgery is not the pharmacogenomics question already on file |
| Length | 1300 words total, Methods and Results combined. Section 2 rule 6 owns the budget and names the module that counts it |
| Exhibits | 3 figures plus 3 tables in the main text, each non-redundant. Everything beyond them goes to the supplement, which is a destination and not a deletion: the export bundle already carries two supplementary exhibits, the event-centered curve and the collider comparison, declared `exhibit_set: "supplementary"` in `EXPORT-CONTRACT.md` 3.8 |
| Gate fallback | Digital Recovery Debt is primary; the gate counts are reported as a secondary result and drive the STROBE diagram either way |
| Format | Markdown plus `.docx`, Vancouver numbered, spine and neurosurgery house style |
| Recovery-debt window | Discharge-anchored post-discharge day 1 to 35, so every patient contributes 35 comparable ambulatory days regardless of length of stay and the fusion-versus-decompression contrast measures recovery rather than length of stay. The protocol's postoperative day 8 to 42 window is demoted to the first main-text sensitivity row |

---

## 7. Interpretation boundaries

These are carried from the protocol and from the plan's own list of honest limitations, and they
constrain wording, not just claims.

**This section is where those limitations live, and that is deliberate rather than temporary
storage.** The manuscript is Methods and Results only, so there is no Discussion for any of them to
sit in, and the word budget stands at 1,294 of the 1,300 the `word-budget` check enforces. Do not
try to move them into the manuscript to make them feel discharged; a limitation with nowhere to
print is still a limitation somebody owns, and the section that owns it is this one until a
Discussion exists.

- The endpoint is **EHR-recorded acute-care utilization**, never adjudicated complications. All of Us
  misses care delivered outside contributing systems, so it is recorded utilization, not all
  utilization.
- **No causal claim** that reduced walking causes complications.
- **No claim** that a wearable diagnoses anything, or that alerting on it improves outcomes.
- **Fitbit owners in All of Us are not representative; the program uses nonprobability sampling.**
  Nobody was enrolled through a sampling frame, and no analysis in this project reweights the cohort
  to a population. The estimates describe people who bought a consumer device and consented to share
  it, and the paper says that rather than generalizing to spine surgery patients at large.
  `prespecification/RUS-DRAFT.md` states it for the attestation; it is repeated here because the
  paper owes it separately and an attestation is not a limitations paragraph.
- **Consumer daily step count is a noisier correlate of recovery than gait velocity or composite
  indices**, and that noise is the argument for within-patient normalization rather than absolute
  counts: every episode is scored against its own preoperative baseline, so no absolute step count is
  compared between people, and device family sits in the locked covariate block for the same reason.
  State this as a limitation of the measure. It is not a defence of the design. Normalization does
  not remove the noise; it stops the noise from being read as a between-person difference, which is a
  narrower claim and the only one that is true.
- **Requiring preoperative wear cuts both ways, and both directions get stated.** The premise is that
  wearable missingness is informative: lower activity itself predicts higher missingness. Wear
  adherence is then measured **before** surgery, so conditioning on it does not induce collider bias.
  That is the reassuring direction, and it is the half a reader is most likely to be handed alone.
  The other half is a bias and belongs in the same breath: the requirement selects a healthier, more
  active, more adherent subset with higher baselines, and **a higher baseline mechanically produces a
  larger debt**, because debt is measured against that baseline. Running the opposite way at the same
  time, patients in more preoperative pain wear less and carry depressed baselines, which
  **understates debt in exactly the sickest patients**. **Neither half may be stated without the
  other.** Quoting only the collider sentence converts a two-sided selection argument into a
  reassurance, and that is the failure this bullet exists to prevent.
- Fusion and decompression differ by disease severity, not only by operation. Therefore **every
  exhibit title says "differed by", never "attributable to".**
- Baseline-equivalent activity days lost is a novel measure. Report it alongside its correlation with
  published anchors and describe it as a descriptive summary, not a validated outcome.
- Recovery debt summarizes area, not depth or duration. Five catastrophic days plus thirty perfect
  ones give roughly the same number as thirty-five mildly reduced ones. Say so, and put the
  components in the supplement.

**Open obligation: the anchor correlation is a build item and nothing builds it.** The novel-measure
bullet has two halves and only the second one is met. "A descriptive summary, not a validated
outcome" is prose, and `manuscript.py` carries it. "Reported alongside its correlation with published
anchors" is not prose, and it has no key, no exhibit and no code. Checked at this pass rather than
assumed: `grep -rni anchor` over `v1/` returns the `pod_anchored_window` sensitivity slug and the
discharge anchor of section 6, nothing else; `grep -rniE correlat` returns the debt model's residual
correlation, one variance comment in `06_analysis_gate.py`, and three copies of this same unbuilt
sentence, being this bullet, the plan's own limitation list, and
`decisions/2026-08-25-recovery-debt-window.md`. No `results.json` key holds a correlation against
anything outside this study, and `verify.py` cannot check a numeral nobody can source.

What it would take, in order. None of it is this file's to write, which is exactly why it is recorded
here as an obligation with an owner-shaped list rather than left as a sentence three documents repeat
at each other.

1. **Name the anchors in an amendment to `ANALYSIS-PLAN.md`**, with their published values and
   citations. Choosing them after seeing the debt distribution is the thing prespecification exists
   to prevent, so this rung comes first and it costs a re-lock.
2. **A `results.json` key** under `debt.`, carrying the coefficient, its interval, the n it was
   computed on, and which anchor it is against.
3. **A row in `EXPORT-CONTRACT.md`** declaring that key and any column it prints, because the
   contract is what `07_export.py` writes against and what `verify.py` reads back.
4. **A home in an exhibit.** The main text has none: section 6 locks 3 figures and 3 tables, and
   `verify.py`'s `exhibit-budget` check fails a fourth. So it is a supplementary exhibit or a Table 2
   footer row.
5. **A `verify.py` check** that the printed correlation equals the exported one, so that the claim
   joins the numerals the suite can hold rather than the sentences it cannot.

Until those five exist, the bullet above states an obligation the delivery does not meet. The
earliest it can be discharged is the Phase 5 build that renders the supplement, and the fixture
bundle cannot exercise it before then.

---

## 8. Stop conditions

Each of these halts the build. None of them is a number to overwrite, a warning to note, or a check
to relax when it fires late in a session.

1. **Runtime probes fail.** Halt if the Fitbit tables are not present in the Controlled Tier CDR, if
   the CDR's location cannot be resolved and mirrored by the derived dataset, if the workspace
   BigQuery write probe is refused, if the ED and inpatient `visit_concept_id` values are assumed
   rather than enumerated against the CDR's actual distribution, or if `statsmodels` 0.14 or later is
   absent. A failure changes the plan; it never gets worked around.
2. **The concept set moved.** Halt if the locked set does not return exactly 852 concepts with the
   CPT-4 and ICD-10-PCS subtotals matching the locked decision file. A different number means the CDR
   concept table changed and everything downstream is suspect. The SNOMED cross-check must run and its
   discrepancy must be reported. Region assignment and the cervical-decompression CPT gap are reviewed
   with the human before the cohort is built.
3. **The ladder does not close.** Halt if any of the four asserts of section 4 fails: the
   within-unit identity at an exclusion rung, step 2's `n_in - n_dropped = n_carried_forward` with
   `n_out >= n_carried_forward`, the episode-unit total of drops over steps 3 to 15 plus the analytic
   n of step 16 against the `n_out` of step 2, or the event closure `n_out(17) - n_dropped(18) =
   n_out(19)`. There is no longer a single global identity, and steps 17 and 19 are excluded from the
   drops-plus-analytic-n assert. Rounded flow-figure boxes are expected not to reconcile; publish the
   footnote instead of adjusting them.
4. **Prespecification did not precede counts.** Halt if the `ANALYSIS-PLAN.md` SHA-256 is not already
   recorded in `SESSION-LOG.md` before Phase 2 runs, or if the file's current hash does not match the
   recorded one without a dated amendment and a reason. The Methods cite the plan by hash and date.
5. **Disclosure would be breached.** Halt if `safe_export()` is asked to write any count cell that
   `disclosure.is_legal_disclosed_count()` refuses, any identifier-like or date-like column, or any
   table with a near-unique column; if a percentage or a rate survives while its count is
   suppressed; if either is computed from anything other than the rounded numerator over the
   rounded denominator, or a percentage is printed with a decimal; or if an export md5 does not
   match after transcription. Controlled Tier dates are unshifted, so a date column is an
   identifier. **Ask the right predicate**, which is the second one at the gate and the first one
   upstream: `disclosable(n)` is the arbiter of the floor on a **true** count and is asked before
   rounding; `is_legal_disclosed_count(cell)` is the arbiter of a **rendered** cell and is what the
   export gate and `verify.py` ask on arrival, because by then the true counts are gone. The two
   are imported as a pair, and a module that imports one and re-derives the other has re-created
   the defect. A stop condition written against a bare threshold is itself a violation of rule 1.
6. **Cost control was skipped.** Halt if any query is about to run without a dry-run byte estimate
   shown first, or without a hard `maximum_bytes_billed` cap. A session does not end until the compute
   environment is deleted and the Apps tab is verified empty.
7. **A numeral does not trace.** Halt if any number in the prose fails to trace to `results.json`
   through the ledger. `local/verify.py` extracts text back out of the rendered `.docx` and diffs it,
   and exits non-zero on mismatch.
8. **The draft is over length.** Halt if Methods plus Results exceeds 1300 words as
   `local/verify.py` counts them, by the rule written out in section 2 rule 6, which is the owning
   statement of this budget. Cut prose; do not move a Methods paragraph into a caption to pass the
   count.
9. **A house prose rule fired.** Halt if an em-dash reaches `manuscript/`, `figures/`,
   `results/tables-csv/`, `results/figures-csv/`, or `results/ledgers-csv/`; if an en-dash appears
   as anything other than a range separator; if a `snake_case` token appears in user-visible text;
   or if a table or figure does not print its own denominator. These are asserted at write time on
   rendered strings, not grepped afterwards.

   **The list of directories is the check.** A directory absent from that sentence is a directory
   the ban does not reach, so it is checked against `EXPORT-CONTRACT.md` whenever the bundle gains
   a path. **Re-checked against the contract at the batch-3 fix pass and still complete:** those
   five are exactly the five section 11.1 of that contract gives `local/verify.py`, and the bundle
   has gained two exhibits since without gaining a sixth directory. `ledgers-csv/` joined the bundle
   in contract 1.1.0 and is named here from the batch-2 fix pass
   on. `probe/probe_result.json` is deliberately **not** among them: the contract's section 1.2
   gives it no `MANIFEST.csv` row and has `verify.py` assert nothing about it, so its prose is
   guarded where it is written, by `01_probe.py`'s own self-test over every rendered diagnosis
   string and over its module docstring, and not by this stop condition. If that file ever acquires
   a `verify.py` obligation, it belongs in the sentence above and not in a second one beside it.
