# EXPORT-CONTRACT.md

**Contract version:** 2.0.0
**Status:** normative. This is the only interface across the compliance boundary.
**Changed in 2.0.0, a MAJOR bump under the SECOND row of 11.2, because a declared key is
removed: `seeds.farm_fingerprint` is gone and `sampling_salt` takes its place.** `verify.py`'s
`plan-constants` check had one known-open finding and it was right to. This document declared
`seeds.farm_fingerprint`, an `integer`, "the fixed salt for BigQuery sampling", at `20260825`.
**That number has no referent anywhere in this project.** The salt the DAG actually samples with is
a STRING: `build_all.sql` declares `sampling_salt STRING DEFAULT '<salt>'`, its `build_params` stage
publishes it as the column `sampling_salt`, `DAG-SCHEMA.md` documents that column, `03_cohort.py`
passes it as a DAG parameter, and `build_all.sql` feeds it to
`FARM_FINGERPRINT(FORMAT('%s|%d|...', sampling_salt, seed, ...))` beside the seed. The exporter
consulted none of the four and typed a literal instead. Three defects, one cause: **the value was
wrong**, so a session reproducing the matched sets from `meta` would have salted differently and got
different sets; **the type was wrong**, an integer declared for a string; and **it was filed under
`seeds`**, where `ANALYSIS-PLAN.md` section 10 fixes every member at `SEED = 0` and 4.5 repeats it
for the `FARM_FINGERPRINT` sampling by name. The plan and the DAG never disagreed -- the seed
genuinely is 0 and is passed separately in the same `FORMAT` -- so nothing here is a plan amendment.
This document invented a field, misfiled it, and gave it a value. 3.1.4 is the replacement row's
reasoning, in full, including why the salt is a **sibling** of `seeds` and not a member of it. The
fix is at the source: `07_export.py` now READS the salt from the DAG (`dag_sampling_salt()` over the
`build_all.sql` beside it), refuses to render a bundle whose salt is not the one the DAG declares,
refuses a `meta.seeds` carrying a `farm_fingerprint` key or a non-integer member, and asserts in its
own self-test that the salt does not appear as a literal in its source. **It is a major bump and not
a minor one on the second row's own test**: a key this document declared is removed, which is
precisely the row, and the fact that no consumer happens to READ that key does not change which row
the change trips -- `ledger.py`'s own major-version guard quotes the row to say so. The consumer
updates the row obliges are registered in 11.4, and they are three one-line changes and one
deletion. **2.0.0 also amends the `analysis_plan.amendments` row** to the shape `07_export.py`
emits, `{n, utc, sections, change, reason, approved_by, superseded_sha256}`, and records why
`sha256_after` is not a field the section 13 log can supply; 3.1.3 carries that argument. That half
is the first row of 11.2 on its own -- keys added to a declared shape -- and a major bump carries it.
**Changed in 1.9.1, a patch bump under the LAST row of 11.2: no key, column, file, path,
label or row count moves, and every 1.9.0 consumer keeps working.** `verify.py` reported one
column of one file whose cells carry machine tokens and which no register in this document
classifies: `series_slug` in `figures-csv/figure4_event_centered_activity.csv`, holding
`event_case` and `matched_control`. Section 6's list of the machine-token columns of a figure CSV
was written for Figures 1 to 3 and never revisited when 1.6.0 added Figure 4, so that column was
skipped by the snake_case assertion **by silence rather than by rule**, which is the one
distinction the 10.2 ownership register exists to remove. **This document has now recorded that
defect at 1.5.0, at 1.6.0 and here, which makes the row the wrong fix and the sweep the right
one.** So 10.2 gains the row, section 6 gains the name, and beside them 10.2 gains **the
machine-token column sweep**: every string column of every bundle file that is not a display
string, put to both registers, with the answer recorded for each. It found four more columns
carrying tokens today with no register row -- `group_slug` on Figure 2 and on the wear-availability
ledger, `unit` and `axis` on Figure 3 -- and four more that are machine-token columns whose present
values happen to carry no underscore, `render` on Figure 3 and `kind`, `unit` and `box_side` on
Figure 1. **`box_side` is the third instance the sweep was run to find**: like `series_slug` it is
named by no row of section 6 and by no row of the register, and only its two underscore-free values
have kept it quiet. All nine are now register rows classed **machine token**, all nine read `not
exempt`, and not one of them changes a check: they say what a column holds so a rule about printed
strings knows to skip it. **The register now classifies by (file, column) pair what section 6
classifies by name**, which is the stronger of the two, and 11.4 records the two places this
landing leaves open, one of them found by the landing itself: the pin `verify.py` set on
`column-register` is a subset assertion and so did not fire when the finding closed. The other is
that the two still disagree on one name: `unit` is a machine token on a figure CSV and a display
label on
`ledgers-csv/ledger_variable_provenance.csv`, and a consumer reading section 6's names without
their surfaces skips a printed column. Nothing is renamed, removed or added to the export: no
bundle file gains or loses a column, `07_export.py` transcribes no new string and runs no new
check, and the exemption registers are untouched. `meta.schema_version` and `meta.contract_sha256`
both move, as they do on any edit, so the bundle is restamped under 11.4's existing obligation and
for no other reason.
**Changed in 1.9.0, additive, so the major version does not move: a minor bump under the FIRST
row of 11.2, for two keys in 3.5 and three rows in 5.3's fixed footer list, and every 1.8.0
consumer keeps working.** A STROBE checklist built against the bundle found that item **16(a)**,
"give unadjusted estimates and, if applicable, confounder-adjusted estimates and their
precision", could not be satisfied: `debt.contrasts` carried the adjusted contrast alone, and
nothing in the bundle carried a crude one to print beside it. **The near miss is the reason this
was not caught earlier.** Table 2 already prints an unadjusted column, so the gap looks closed
from the outside; but `by_group[i].unadjusted_debt` is an absolute **level**, a median and
interquartile range by direct summation on complete windows against its own denominator, and item
16(a) asks for the unadjusted **contrast**. Two of those medians cannot be differenced into it:
they rest on two different subsets, direct summation is a different estimator from
model-and-integrate, and a difference of group medians is not the standardized difference the
estimand is defined as. **3.5 gains `debt.unadjusted_contrasts`**, the same five contrast slugs
carrying the same estimator refitted with the locked covariate table of `ANALYSIS-PLAN.md` 3.6
deleted and nothing else changed, each with its own person-clustered interval and its own n; and
**`debt.unadjusted_model`**, which says in one sentence what was removed and what was kept, which
rung of the 3.1.1 ladder the covariate-free fit reached, whether that rung matched the adjusted
fit's, and how many resamples returned nothing. 7.3 does **not** grow: an unadjusted contrast is
the same contrast and reuses the same label. **5.3 gains three footer rows**, 13 to 15, appended
so that every existing `row_order` is unchanged, and 3.5 argues why the footer rather than Table
2's body or Figure 3's forest: the body is held to adjusted absolute levels by the split
`verify.py` enforces, Figure 3 block 2 is a set `verify.py` asserts equality on against a locked
plan section, Figure 3 block 1 would need five new slugs and a second `is_primary` for what are
not new contrasts, and the footer already carries a contrast-scale fact in row 9's Manski bounds.
**It is not prespecified and the bundle says so.** `ANALYSIS-PLAN.md` is locked at 1.5 and
carries an unadjusted *association* for the other arm at 4.8 and an unadjusted *level* for this
one at 9.2, neither of which is an unadjusted contrast; adding an estimand to a locked plan is an
amendment and a re-lock, which is not this document's to take. So the quantity ships with
`prespecified: false`, 11.1 obliges `manuscript.py` to read that boolean rather than decide, and
11.4 registers what `07_export.py`, its fixture and the three local consumers must pick up. Two
10.2 cells move from 12 rows to 15 with the footer. A re-export is required:
`meta.schema_version` and `meta.contract_sha256` both move, and the exporter transcribes two of
the strings above. Nothing is renamed or removed, so every 1.8.0 consumer keeps working; a
consumer that hardcoded a 12-row Table 2 footer is what this bump breaks.
**Changed in 1.8.0, additive, so the major version does not move: a minor bump under the FIRST
row of 11.2, for two keys on every exhibit block, one denominator, one unit and one row of a
vocabulary this document transcribes.** 1.6.0 put
`figures-csv/figure4_event_centered_activity.csv` and `tables-csv/table4_collider_comparison.csv`
in the **primary** exhibit set. **Both are supplementary exhibits and this version says so.**
The gaps 1.6.0 closed were real and stay closed: the collider comparison had no exhibit anywhere,
and the event-centered curve had none at the 20-to-49 tier. The placement was the error, and it
was made here because the budget that forbids it lives in a document this contract's author was
not reading: `CLAUDE.md` section 2 rule 7 and section 6 fix the deliverable at **exactly 3
figures and 3 tables** and send everything beyond that to a supplement, and `ANALYSIS-PLAN.md`
section 9.5 specifies the event-centered curve as the **alternate Figure 2 at 50 or more
events**, not as a fourth primary figure. Under 11.3 the plan wins and this document is amended.
**Nothing is deleted.** Both files keep their sections, their schemas, their columns, their row
counts, their `MANIFEST.csv` rows, their `results.json` blocks and their builders, and both are
still written on every run; `local/figures.py` still renders Figure 4 and is still what serves
the alternate exhibit set at tiers 1 and 2. **3.8 gains `exhibit` and `exhibit_set` on every
block of `figures` and `tables`** and states the budget in one place: it is counted over
**distinct `exhibit` values among the primary blocks**, never over bundle files and never over
block keys. Both of those counts are wrong and wrong differently: this bundle writes one CSV per
printed thing, so Table 2 has a footer file, and Table 3 is two files **and** two keys while
being one exhibit. `figures` still carries four blocks and `tables` still five. **3.2 gains
`event_centered_members`** and the unit `risk-set members`, and **3.8 points
`figures.figure4.denominator` at it**, closing the gap `06_analysis_gate.py` raised: 3.8 makes an
exhibit's denominator a key of `denominators`, the only candidate was the composite first-event
count, and the curve carries the same structural filter the fits carry, so the plate note printed
a number larger than the curve's own. A supplementary exhibit still needs one, because it is
still a printed exhibit and `CLAUDE.md` section 2 rule 5 makes every printed figure carry its
own denominator. **11.1 gives `verify.py` the budget check** and **11.4 restates the
`absolute_risk_node_shape` obligation**, which was half stale: the shape 3.7 declares has been
right since 1.6.0, and what is still live is that `06_analysis_gate.py` emits `unit="percent"`
with a decimals override where 2.4 now carries `absolute_risk_percent`. A re-export is required:
`meta.schema_version` and `meta.contract_sha256` both move, and Figure 4's plate note is a string
the exporter transcribes and its required content moved. Nothing is renamed or removed, so every
1.7.0 consumer keeps working; a consumer that read `len(results["figures"])` as the figure budget,
or that took Figure 4's `n` for the composite event count, is what this bump breaks.
**Changed in 1.7.0, additive, so the major version does not move: a minor bump under the FIRST
row of 11.2, for one row in a vocabulary this contract transcribes and three keys, and every
1.6.1 consumer keeps working.** Six places where this document disagreed with itself or with a
module written against it, all six reported by the module authors rather than found here.
**7.5 gains a tenth suppression reason**, `not_estimable_separation`, sentence "not estimable
(separation)", transcribed character-exact from `ANALYSIS-PLAN.md` section 4.9, which reached
version 1.5. `06_analysis_gate.py` has emitted it since it was written and `07_export.py` halted
by name on it, correctly, because a reason with no sentence has nothing to print. It could not
reuse an existing reason: a quasi-separated conditional fit **converges**, so the cell size was
fine, the data were there, the tier permitted the analysis, and `not_estimable_convergence` would
have been a false sentence rather than a near-enough one. **3.5 gains
`delta_shift.interval_crossed_within_grid`.** `05_analysis_drd.py` returns a crossing flag per
node, and a real run produced `crossed_within_grid = false` beside
`interval_crossed_within_grid = true` with a genuine coordinate at `delta = 3.5`; 3.5 suppressed
both nodes off the single flag, which would have discarded a computed result, and each node now
reads its own flag. **3.7 gains the two per-group standardized rate keys** of the collider
comparison, because 5.7 gives Table 4 six rate cells and 3.7 declared four, so two printed cells
traced to nothing and `06_analysis_gate.py`'s `build_gate_block()`, which refuses any key this
document does not declare, could not supply them; `ANALYSIS-PLAN.md` 4.4 judges the two window
groups separately and therefore requires the per-group figure and not only the ratio. 7.15 gains
their two labels in the same edit. **The bound-node count was wrong.** 3.5 said four nodes are
bound nodes "and they are the only ones" while 9.1 wrote `sensitivity.delta_shift_tipping_point.estimate` as a fifth, carrying the same coordinate as
`debt.delta_shift.tipping_point_point_estimate`; the modules followed 9.1, the count is now five,
and 3.6 no longer declares that node an estimate node. **`model_fit.spline_basis` was the wrong
string**: the plan specifies a **restricted** cubic spline in **post-discharge** day and
`05_analysis_drd.py` emits the plan's wording; this document said "natural cubic on postoperative
day", which is two words wrong in a string a reader meets in the Table 2 footer, and under 11.3
the plan wins. **8.3 and 4.4 now state the `n_suppressed_cells` rule by file kind** and show its
arithmetic: `44 x 4 = 176` for Figure 4 at tier 4, with the 44 `not_plotted_display` sentences
outside the count, because in a figure CSV the sentence sits beside a cell already written as
`SUPPRESSED` rather than in place of it. A re-export is required: `meta.schema_version` and
`meta.contract_sha256` both move, and the exporter transcribes three of the strings above.
**Changed in 1.6.1, a patch bump under the last row of 11.2: no key, column, file, path, label
or row count moves, and every 1.6.0 consumer keeps working.**
`figures-csv/figure1_strobe_ladder.csv` was clearing the near-unique refusal class by one row and
by accident. The ladder is nineteen rungs, the module's row floor is `NEAR_UNIQUE_MIN_ROWS` and its
test is strictly greater, so the class never armed on that file; the ladder has already moved twice
in this project, fifteen rungs and then nineteen, and two more rungs arm it inside the perimeter on
a paid Workbench run. **10.2's whitelist gains `figures-csv/figure1_strobe_ladder.csv` and five of
its thirteen columns**, `step`, `slug`, `display_label`, `reason` and `reason_display`. Each was
tested against the whitelist's own criterion on its own rather than the file being granted whole:
all five are the rung vocabulary of `ANALYSIS-PLAN.md` section 2.6, transcribed into 3.3 and 7.2,
and every one of them reads exactly the same if the cohort is a different hundred people. **The
whitelist and not exception 3, and the difference is the criterion rather than the convenience.**
Figure 2's `day` fails that criterion, because which days are present is the output of the absence
rule and therefore depends on the data, and it is granted under exception 3 for that reason; a
rung's step number, slug and printed sentence do not depend on the data at all. **The grant does
not on its own make a grown ladder exportable, and 10.2 and 11.4 now say so** rather than leaving it
to be found in the perimeter: measured on the shipped module at twenty-one rungs, `n_in` and `n_out`
cross the ceiling too and carry the integer-key shape with them, they are counts, and a count column
is exempted by nothing in this document. That residue is a dated obligation in 11.4 and not a
widened exemption. **10.2 also gains the row-floor sweep**, every bundle file's row count against
the floor computed from the grain this document declares for it, because the ladder's margin of one
row was not a thing anybody had measured. It found one other file at the boundary:
`ledgers-csv/ledger_exclusion_and_censoring_reasons.csv` is at twenty rows, a margin of zero, and
crosses safely only because `reason_detail` is its one column above the ceiling and was whitelisted
at 1.2.0 for a reason of its own. A re-export is required: `07_export.py` must pass the new
declaration on the Figure 1 frame, and `meta.schema_version` and `meta.contract_sha256` both move.
**Changed in 1.6.0, additive, so the major version does not move:** two exhibits, six
`gate.arm_a.estimates` keys, three units, one suppression reason, two label tables, one exception
and one dated-obligation register, closing sixteen defects three downstream modules found while
being written against version 1.5.0. **Two node shapes were wrong.**
`gate.arm_a.estimates.absolute_risk_translation` was declared a percentage node, which requires a
numerator and a denominator, and a model-predicted absolute risk has neither; it becomes an
estimate node on the percent scale, which is the same defect and the same resolution as
`debt.by_group[i].share_reaching_80pct_baseline`. It also gets its own unit,
`absolute_risk_percent`, at two decimals, because the `percent` unit's zero decimals print a 90-day
acute-care risk of a few percent as `0%`. And the two delta-shift tipping points become **bound
nodes**: a tipping point read off a grid has no interval, and giving it `lo` and `hi` that differ
from `est` invites a renderer to draw a confidence interval that does not exist. **Five keys were
missing.** 7.5 gains `no_crossing_within_range`, so a primary contrast that never crosses zero out
to the extended delta grid stops being reported as `not_estimable_data_unavailable`, which labels
the stronger result as a missing one. `gate.arm_a.estimates` gains the unadjusted association,
which is the one estimate the 20-to-49 tier permits and the likeliest tier this study reaches, the
co-primary exposure's own odds, and the four keys of the collider comparison. **Two exhibits were
missing**, and both are reachable at the 20-to-49 tier where the alternate exhibit set is not:
`figures-csv/figure4_event_centered_activity.csv` (section 4.4) and
`tables-csv/table4_collider_comparison.csv` (section 5.7). `MANIFEST.csv` therefore carries
**sixteen** data rows, `results.json["figures"]` four keys and `results.json["tables"]` five.
**Section 7.14** is new: the twelve `unit` and twelve `missing_handling` strings of
`ledgers-csv/ledger_variable_provenance.csv`, which are printed cells that section 7 did not own,
the same defect 7.12 and 7.13 closed at 1.5.0. **Section 7.15** owns the printed strings of the two
new exhibits. **Section 6 no longer claims that every `tables-csv` cell is a printed display
string**: five columns across three files hold machine tokens, and the 10.2 ownership register
now classes them rather than leaving `verify.py`'s snake_case check to fail on arrival. **10.2
gains exception 5**, which exempts a rounded aggregate statistic on a frame of prespecified strata
from the near-unique cardinality class only, because twenty-seven forest rows at one decimal are
near-certain to exceed the ninety percent ceiling and would halt the export mid-session on a paid
Workbench run. **10.4 gains the three declarations `07_export.py` already holds** and this document
did not carry: the composite-count columns that let the floor reach a count rendered as `1,240
(33%)` or `n = 340`, the row-partition declaration for the four partitions that run down a column
rather than across a row, and the rule that every exported statistic is rounded to its unit's
decimals before the gate sees it. Its `no_hardcoded_floor` walk also stops reporting the six
comparisons this project's in-module `_run_self_test()` bodies legitimately carry. **11.4 is new**
and records, dated, that tiers 1 and 2 block the export until sections 4 and 5 get a second full
pass for the alternate exhibit set. Four worked examples that contradicted their own rules are
corrected: 5.5's tier-4 claim, 5.6's `baseline_steps` source table and missing count, 8.3's
arithmetically impossible wear-ledger row count, and 4.2's three-decimal normalized activity. The
bump is minor rather than patch because keys, columns, files and vocabulary rows all move, which is
the first row of 11.2. Nothing is renamed or removed, so every 1.5.0 consumer keeps working; a
consumer that hardcoded fourteen manifest rows, three figures or four tables, or that reads
`absolute_risk_translation` as a percentage node, is what this bump breaks.
**Changed in 1.5.0, additive, so the major version does not move:** three tables, two of them
tables this contract already required and did not carry. **Section 7.12** is new: the twenty
`(step, reason_detail)` sentences of `ledgers-csv/ledger_exclusion_and_censoring_reasons.csv`. 5.6
requires that column to hold one prespecified sentence per row and 10.2 exempts it from the
near-unique class on exactly that ground, but section 7 held no table for the twenty detail slugs the
`ledger_exclusion_reasons` stage of `pipeline/build_all.sql` emits, so the exemption rested on a table
that did not exist and `pipeline/03_cohort.py` had to define a local `REASON_DETAIL_LABELS` to have
anything to print. **Section 7.13** is new for the same reason: the twelve display labels and
derivation sentences of `ledgers-csv/ledger_variable_provenance.csv`, the one `display_label` column
in the bundle whose strings section 7 did not own, which `verify.py`'s character-equality assertion
would have failed on arrival. **10.2 gains an ownership register** naming what each exempted column
holds and who owns its values, so that the next exemption resting on an absent table fails a check
rather than a re-export. And the supplementary Arm B sensitivity rows go from nine to ten, following
the version 1.3 amendment to `ANALYSIS-PLAN.md` section 6. The new row is
`baseline_weekday_weekend_split`, display label **Separate weekday and weekend baselines**, which
re-estimates the primary contrast against a baseline split by day type. It is supplementary rather
than a fifteenth plotted row because day of week is already handled twice inside the primary, as a
7-level fixed effect and by g-computation over each episode's own calendar alignment, and a row that
corroborates an existing handling is not a row that tests an unprotected choice. The fourteen plotted
rows did not move in the version 1.3 amendment either, in membership, order, labels or bytes, so the
set-equality assertion is untouched. The bump is minor rather than patch because a row count moves
and two tables are added, which the last row of 11.2 excludes itself over. No key, column, file or
path changes and nothing is renamed or removed, so every 1.4.0 consumer keeps working; a consumer
that hardcoded the previous nine supplementary slugs instead of reading 3.6, or that carried its own
copy of either new label table, is what this bump breaks.
**Changed in 1.4.0, additive, so the major version does not move:** the supplementary Arm B
sensitivity rows go from eight to nine, following the version 1.2 amendment to
`ANALYSIS-PLAN.md` section 6. The new row is `fusion_status_non_add_on_only`, display label
**Fusion status without add-on codes**, which re-estimates the primary contrast with fusion status
read from non-add-on records only. The plan's fusion-status rule reads all qualifying evidence
including add-on and instrumentation codes, and this row bounds how much of the primary contrast
rests on episodes whose fusion status comes from an add-on code alone, in the same way the
delta-shift tipping point of `ANALYSIS-PLAN.md` 3.11 and the Manski bounds of 3.12 convert a
judgment call into a reported number. It is transcribed into 3.6 and, with the other eight, into the
label table of 7.8, where section 6 of this contract says a printed string must live. It is a
supplementary row and is **not** a member of the fourteen-row set `local/verify.py` asserts equality
over: the fourteen plotted rows are byte-identical and in identical order across the plan amendment,
so that assertion does not move. The bump is minor rather than patch because a row count moves,
which the last row of 11.2 excludes itself over. No key, column, file or path changes and nothing is
renamed or removed, so every 1.3.1 consumer keeps working; a consumer that hardcoded the previous
eight slugs instead of reading 3.6 is the one thing this bump breaks.
**Changed in 1.3.1, a patch bump under the last row of 11.2: no key, column, file, path, label
or row count moves, and every 1.3.0 consumer keeps working.** The plate-note rule of 4.2 and the CSV
schema directly above it said incompatible things about the surviving-day set, and the rule was the
half that was wrong. Three edits follow from that. **10.2 gains a third named exception**, a day axis
on a curve file is an axis rather than a value column, covering `day` in
`figures-csv/figure2_daily_activity.csv` and in `ledgers-csv/ledger_wear_availability_by_day.csv`;
without it a `single_group` run halts mid-export on the near-unique refusal class, on a paid
Workbench session, at the one collapse level a small cohort is most likely to reach. `day` is
**not** added to the `specification_columns` whitelist and the two registers keep separate criteria,
for the reason 10.2 now states. **4.2 item 5 stops promising** that the identity of the dropped days
is withheld, because the file publishes its complement, and says what the plate note prints instead.
And the **`row_order` grant on Table 1 gains the contiguity assertion** that is the condition of its
own safety, in 10.2 and in 5.1. A re-export is required, because `figures.figure2.plate_note` is a
printed string the exporter transcribes and its required content moved.
**Changed in 1.3.0, all additive, so the major version does not move:** two ledger CSVs gain the
denominator their producer already computes, because `ANALYSIS-PLAN.md` section 8 rule 8 says every
table prints its own denominator and these two did not. `ledger_variable_provenance.csv` gains
`n_total`, because `ledger_variable_missingness` in `build_all.sql` measures a different denominator
on different rows, so a reader given only `n_missing` divides all twelve rows by one number and
misreads the person-day row and the event row by orders of magnitude.
`ledger_exclusion_and_censoring_reasons.csv` gains `n_denominator`, because the rung 4 rescue routes
are counted over the episodes with an emergency department encounter and not over the rung's drops,
so the printed share has a denominator no reader can infer. 5.6 names the three sets of rows that
`n_denominator` now puts in the same frame as their total, and records why
`ledger_wear_availability_by_day.csv` does **not** take the `n_analyzable` and `n_inpatient` columns
its producer also emits. No key, file, label or row count changes and no column is renamed or
removed, so every 1.2.0 consumer keeps working; a consumer that reads either of those two files by
position rather than by column name is the one thing this bump breaks.
**Changed in 1.2.0, all additive, so the major version does not move:** section 0 states the two
disclosure predicates and the two moments they are asked at, because `disclosure.py` now exports
`is_legal_disclosed_count` beside `disclosable` and asking the floor predicate of an
already-rounded cell refused a correctly rounded frame; `specification_columns` is transcribed into
the 10.4 signatures and given a per-column whitelist in 10.2; the concept-set registry ledger is
**51 rows**, not 852, and 5.6 says which number lives where; `pipeline/01_probe.py` is named as the
registry's second writer, with an md5 equality check in `07_export.py`; and section 1.2 names
`v1/probe/probe_result.json`, the first artefact this contract names outside the bundle. No bundle
path, column, key, label or row count changes, so every 1.1.0 consumer keeps working.
**Changed in 1.1.0, all additive, so the major version does not move:** the attrition ladder is the
nineteen rungs of `ANALYSIS-PLAN.md` section 2.6; `figure1_strobe_ladder.csv` gains an
`n_carried_forward` column; a third subdirectory `ledgers-csv/` carries the five STROBE companion
ledgers, taking `MANIFEST.csv` from 9 data rows to 14; `meta.concept_set` carries the two
concept-set gap measurements; the comma-separated float format is `%.6g`; the `cell_below_threshold`
sentence reads "20 or fewer"; and the estimator rung-3 slug is `py_fractional_logit_gee`.
**Producer (inside the perimeter):** `pipeline/07_export.py`, through `safe_export()` in `pipeline/disclosure.py`.
**Consumers (local, outside the perimeter):** `local/figures.py`, `local/tables.py`, `local/ledger.py`,
`local/manuscript.py`, `local/make_strobe.py`, `local/verify.py`.
**Authority order when documents disagree:** `AOS-CS.md` section 9, then `v1/CLAUDE.md`, then
`prespecification/ANALYSIS-PLAN.md`, then this file, then any module.

A module MUST NOT read a key, a column or a file that this document does not name, and MUST NOT
write one either. If a module needs a value that is absent here, the fix is an amendment to this
document plus a re-export, never an ad hoc key.

---

## 0. The five rules this contract exists to enforce

| # | Rule | Where enforced |
|---|---|---|
| R1 | No participant-level value crosses the boundary. Two predicates, asked at two different moments: `disclosable(n)` of the **true** count, before `round20`, decides whether it may be disclosed at all; `is_legal_disclosed_count(cell)` of the **rendered** cell, after `round20`, decides whether that value may be written down. Anything either one refuses is suppressed. | `safe_export()`, re-checked by `verify.py` |
| R2 | No image crosses the boundary. The perimeter exports the **plotted series**, never the plot. There is no `.png`, `.pdf`, `.svg`, `.jpg`, `.parquet` or `.pkl` anywhere in the bundle. | `safe_export()` refuses a non-CSV, non-JSON extension |
| R3 | Every exported file carries an md5 in `MANIFEST.csv`, computed over the bytes actually written. | section 8 |
| R4 | Every numeral that reaches prose exists as a `display` string in `results.json`. Nothing is hand-typed. | `local/ledger.py`, audited by `verify.py` |
| R5 | Every user-visible string in the bundle is a verbatim copy of an entry in the label table in section 7. | `verify.py` string equality check |

**The floor is a number this document refuses to write down.** `ANALYSIS-PLAN.md` section 8 rule 1
says "counts 1 to 20 inclusive are suppressed", which puts a count of exactly 20 below the line;
`AOS-CS.md` section 9 says "counts at or above 20" are disclosable, which puts it above. Rather than
pick a reading and have `07_export.py` and `verify.py` pick differently, both import the predicates
themselves:

```python
from disclosure import MIN_CELL, disclosable, is_legal_disclosed_count, round20

disclosable(n)                  # n is the TRUE count, BEFORE round20.  THE FLOOR.
round20(n)                      # nearest 20, applied only after disclosable(n) is True
is_legal_disclosed_count(cell)  # cell has ALREADY been through round20.  THE GATE.
```

**There are two questions here, and one predicate cannot answer both.** Six modules read this
document to decide which to call, so the division is written down rather than left to be inferred
from a call site:

| Ask | Of what | When | Because it decides |
|---|---|---|---|
| `disclosable(n)` | the **true** count, as it came back from BigQuery | **before** `round20` | whether this count may be disclosed at all, which is to say whether to suppress it |
| `is_legal_disclosed_count(cell)` | a **rendered** cell, or a whole column of them | **after** `round20` | whether a value already produced for export is one that may legally be written down |

**They disagree on 20, by design, and that is the point rather than a wrinkle.**
`disclosable(20)` is `False`, because a true count of 20 sits below the floor.
`is_legal_disclosed_count(20)` is `True`, because `round20` maps a true 21 through 29 to the numeral
20, so a rendered 20 is the ordinary output of a correctly suppressed and correctly rounded pipeline.
Collapsing the two was a real defect with a real cost: the export gate asked `disclosable()` of a
cell that had already been rounded, so a correctly rounded frame was refused by the same module that
produced it, and the STROBE ladder and Table 1 could not be exported at all.

The rule that follows, and it governs every later sentence in this document: **wherever this
document says a count is tested before it is rounded or suppressed, the predicate is `disclosable`;
wherever it says a cell is tested before it is written, the predicate is `is_legal_disclosed_count`.**
A module reaching for `disclosable()` on a frame it is about to hand to `safe_export()` has picked
the wrong one, and a module reaching for `is_legal_disclosed_count()` on a raw count out of a query
has picked the wrong one in the other direction and has no floor at all.

`is_legal_disclosed_count` accepts exactly three things and nothing else: the suppression sentinel,
an exact `0` when `allow_zero`, which is its default and this bundle's setting, and a whole number
that is a positive multiple of `ROUND_BASE`. So it still catches the mistake the gate exists to
catch, a caller who forgot to round, and catches it better than the floor test did: an unrounded 21
is refused because it is not a multiple of 20, where the floor test would have waved it through. The
one pair it cannot separate is a raw 20 from a rounded 20, because by then the true count no longer
exists to be asked; that gap is closed upstream instead, by `round20` itself, which emits the
sentinel for a true 20 and never the numeral.

`pipeline/disclosure.py` owns the number and both comparisons. No module in this bundle writes
`n >= 20`, `n > 20` or `n < 20` anywhere, and `verify.py` greps the pipeline and the local modules
for a bare `20` in a comparison and fails on a hit. Everything below is written against these two
predicates, so a change of reading is a one-line change in one file rather than a hunt.

**The display convention that follows from the floor** is `ANALYSIS-PLAN.md` section 8 **rule 2**,
and it is quoted rather than paraphrased because the Methods footnote and the `disclosure.py`
docstring both carry the same sentence: *"Counts of 20 or fewer are suppressed; larger counts are
rounded to the nearest 20, so a disclosed 20 represents a true count of 21 to 29."* A printed `20`
therefore never stands on a true 20, which is suppressed, and never on a true 30, which rounds to
40. Two citation notes, because the plan's section 8 was renumbered when rule 2 was inserted: rule 1
is still the `disclosable(n)` floor and did not move, and the rules this document cites elsewhere
are rule 2 (the 21-to-29 convention), rule 3 (a percentage is suppressed whenever its numerator is),
rule 4 (rounded numerator over rounded denominator, zero decimals) and rule 5 (complementary
suppression). Old rules 2 through 7 are now 3 through 8; a citation of "section 8 rule N" written
before the insertion is off by one for every N above 1.

An exact zero is disclosable and is exported as `0`, never rounded and never suppressed: a zero cell
names nobody, and suppressing it would make "the share with zero debt" unreportable. Because every
row and column total in the bundle is itself rounded, a zero cell cannot be differenced against a
total to recover a small cell.

**Secondary suppression.** Within any set of counts that partitions a disclosed total, if one member
is suppressed then at least two must be suppressed. One suppressed member of a partition is
recoverable by subtraction. `safe_export()` applies this before writing, and `verify.py` re-asserts
it on the arrival side for every partition this contract names.

---

## 1. Bundle layout

The perimeter writes this tree. The local side unpacks it, byte for byte, at `v1/results/`.
Paths in `MANIFEST.csv` and in `results.json` are relative to `v1/results/` and use forward slashes.

```
v1/results/
├── MANIFEST.csv                            one row per exported file (section 8)
├── MANIFEST.md5                            one line: the md5 of MANIFEST.csv, then a newline
├── results.json                            every scalar the prose will cite (section 3)
├── figures-csv/                            plot-ready aggregate series, one file per figure
│   ├── figure1_strobe_ladder.csv
│   ├── figure2_daily_activity.csv
│   ├── figure3_forest.csv
│   └── figure4_event_centered_activity.csv
├── tables-csv/                             one file per printed table, in print order
│   ├── table1_cohort_characteristics.csv
│   ├── table2_adjusted_debt.csv
│   ├── table2_adjusted_debt_footer.csv
│   ├── table3_gate_part_a.csv
│   ├── table3_gate_part_b.csv
│   └── table4_collider_comparison.csv
└── ledgers-csv/                            the five STROBE companion ledgers (section 5.6)
    ├── ledger_concept_set_registry.csv
    ├── ledger_variable_provenance.csv
    ├── ledger_exclusion_and_censoring_reasons.csv
    ├── ledger_wear_availability_by_day.csv
    └── ledger_matched_set_sizes.csv
```

**Every file in this tree is mandatory on every run.** A file whose content is entirely suppressed
still exists, still carries its header row, and still carries a row saying why it is empty. A missing
file is a build failure, not a signal. Silent omission is itself a disclosure: it tells the reader
which cells were small.

**This tree is a file list and not an exhibit list, and the two are counted differently.**
Sixteen files carry nine exhibit blocks carrying six exhibits, three of which are primary figures
and three of which are primary tables; `figure4_event_centered_activity.csv` and
`table4_collider_comparison.csv` are **supplementary** exhibits, written on every run like every
other file here. 3.8 declares that classification and states the arithmetic. Counting the files in
this tree is not how the exhibit budget of `CLAUDE.md` section 2 rule 7 is checked, and neither is
counting the keys of `results.json["figures"]` and `["tables"]`.

The two files the feasibility tier can empty are written under that rule rather than around it.
`tables-csv/table3_gate_part_b.csv` carries its two tier rows (5.5),
`tables-csv/table4_collider_comparison.csv` keeps its three window-group rows with the tier sentence
in every rate cell (5.7), and `figures-csv/figure4_event_centered_activity.csv` keeps its full grid
of 44 rows with every measured cell written as `SUPPRESSED` (4.4), which is why that one file
departs from the absence rule of 4.2 and says so in its own section.

| Property | Rule |
|---|---|
| Encoding | UTF-8, no BOM |
| Line ending | LF (`\n`) only, on every file, including the final line |
| Extensions permitted | `.csv`, `.json`, `.md5`. Nothing else. |
| Directory count | Exactly three subdirectories, named above. No nesting below them. |
| Total bundle size | Under 2 MB. A bundle above that is evidence that something row-level got in. |
| Transfer | The whole tree is zipped into `spinewear_v1_export.zip` for transfer. The zip is a courier, not an artifact: it is not md5-stamped and is deleted after unpacking. The per-file md5s are what carry across. |

### 1.1 Which consumer reads which file

| File | figures.py | tables.py | ledger.py | manuscript.py | make_strobe.py | verify.py |
|---|---|---|---|---|---|---|
| `results.json` | read | read | read | via ledger | read | read |
| `figures-csv/figure1_strobe_ladder.csv` | read | no | no | no | read | read |
| `figures-csv/figure2_daily_activity.csv` | read | no | no | no | no | read |
| `figures-csv/figure3_forest.csv` | read | no | no | no | no | read |
| `figures-csv/figure4_event_centered_activity.csv` | read | no | no | no | no | read |
| `tables-csv/table1_*.csv` | no | read | no | no | no | read |
| `tables-csv/table2_*.csv` | no | read | no | no | no | read |
| `tables-csv/table3_*.csv` | no | read | no | no | read | read |
| `tables-csv/table4_collider_comparison.csv` | no | read | no | no | no | read |
| `ledgers-csv/*.csv` | no | no | no | no | read | read |
| `MANIFEST.csv`, `MANIFEST.md5` | no | no | no | no | no | read |

No consumer globs. Every path is a literal, assembled from the `file` field the manifest declares.
The five `ledgers-csv/` files are the only files in the bundle with no `results.json` block of their
own: they are reached by the literal paths named above, and their integrity rides on `MANIFEST.csv`
like every other file's. Section 5.6 fixes their columns, their suppression rule and their manifest
entries.

---

### 1.2 The probe result, and why it sits beside the bundle rather than in it

`pipeline/01_probe.py` runs the five runtime probes at the top of Phase 2 and produces one JSON
object: the Fitbit table inventory and DDL, the resolved `heart_rate_summary` layout with the
zone-partition verdict, the locked concept set resolved against the live CDR, the emergency and
inpatient visit concept distribution, and the environment facts. Section 0 forbids a module from
writing a file this document does not name, and until this subsection existed this document named
none, so the probe result was returned, printed as a bracketed JSON block for a human to paste into
`SESSION-LOG.md` section 6, and written to a file only where a human typed a path. That was correct
behaviour under the rules as they stood and a workaround under any reading. It has a name now.

| Property | Value |
|---|---|
| Path | `v1/probe/probe_result.json`. One file, one directory, no nesting |
| Written by | `pipeline/01_probe.py`, and nothing else |
| Read by | any later session, in place of re-running the probe; `pipeline/02_pregate.py` when it does not already hold the returned dict; `local/verify.py` may read it and asserts nothing about it |
| Serialization | `json.dump(obj, fh, indent=2, sort_keys=True, default=str)` and a trailing newline, which is the byte-stability setting of 8.2, so a re-run that found the same facts writes the same bytes |
| Lifetime | one per CDR release. A probe run overwrites it and the previous one is recovered from git history, which is the reason this is a repo path and not a bucket object |
| `MANIFEST.csv` row | none. It is not in the bundle, and section 8's md5 discipline does not reach it |
| Suppression | every count in it is `disclosable()`-tested on its true value and then `round20`-rounded before it is written, exactly as if it were a bundle file. The file crosses the compliance boundary by copy-paste, and a JSON block on a notebook screen is a disclosure whatever it is later saved as |

```
v1/probe/
└── probe_result.json                       the Phase 2 runtime probe result
```

**Beside the bundle, and the phase ordering is what decides it.** The probe runs in Phase 2. The
bundle is written in Phase 4, by `07_export.py`, in one pass, and `v1/results/` does not exist when
the probe runs. Three consequences follow, and the first alone settles it:

1. **A Phase-2 file cannot wait inside a Phase-4 artefact.** `CLAUDE.md` stop condition 6 requires
   the compute environment to be deleted before a session ends, and Phase 2 ends in a hard stop for
   a human decision, so Phase 2 and Phase 4 are different sessions on different machines. A probe
   result parked in a bundle tree that does not exist yet would be deleted with the environment that
   wrote it. It has to leave the perimeter at the end of Phase 2, on its own, which is what
   "beside" means here.
2. **The manifest arithmetic is exact and four places assert it.** `MANIFEST.csv` carries sixteen
   data rows, `meta.manifest_rows` restates the number, 3.8 derives it as `1 + 4 + 6 + 5`, and 9.2
   pins it in the fixture. A probe result inside `v1/results/` is either a straggler that fails
   `verify.py --bundle` rule 3, which refuses any file the manifest does not name, or a seventeenth
   manifest row that moves a number in four places for a file that is not an exhibit and that no
   consumer plots, tabulates or quotes.
3. **The two have different lifetimes.** The bundle is rewritten whole on every export and is
   invalid if one file is missing. The probe result is written once per CDR release and is expected
   to sit unchanged across many exports. Two lifetimes in one tree is how a stale file gets shipped
   as a fresh one.

**What it carries, and which keys are counts.** Nine top-level keys, and the distinction section 10
turns on is between keys that are **metadata**, exported as measured, and keys that are **counts of
participants or of participant-days**, which meet the floor like every other count in this project:

| Key | What it holds | Disclosure |
|---|---|---|
| `meta` | module name, UTC start, the resolved project, CDR, CDR location and derived dataset, software versions, the four byte caps, and the session cost as queries, GB billed and USD | **metadata.** A byte count and a dollar figure are properties of a query, not of a person |
| `probe ok` | boolean: no probe returned a halting status | **metadata** |
| `halting` | the sorted probe keys that halted; empty when `probe ok` | **metadata** |
| `verdicts` | one object per check, with `key`, `status`, `headline`, `checked`, `came_back`, `means` and `changes` | **metadata**, with one rule that is not optional: `came_back` is composed from already-rounded numbers. The raw counts decide the status and never reach a string |
| `fitbit tables` | `tables`, `required`, `expected` and `ddl` | **metadata**, except **`row counts`, which is a count**: a Fitbit table row is a person-day |
| `heart rate summary` | `columns`, `resolved`, and the `zone label` names | **metadata**, except **`bands` and `zone labels[].rows`, which are counts** of person-days |
| `concept set` | `expected`, `resolved`, `subtotals`, `snomed`, `registry` | **metadata throughout, and deliberately unrounded.** See below |
| `visit concepts` | `prespecified`, the two locked id tuples | **metadata**, except **`distribution` and `classification`, which carry `n_visits` and `n_persons`**. Both are counts, and both are folded on persons so a rare encounter type loses its label together with its count |
| `environment` | project, workspace CDR, prep CDR, derived dataset, location, write probe result, R kernel visibility, `wb resource list` status, software versions | **metadata**, except **`person rows, rounded`, which is a count** and which arrives already rounded, as its key says |

**A concept count is not a participant count**, and the `concept set` block is the one row a reader
is most likely to get wrong, so it is stated rather than implied. `resolved`, the CPT-4 and
ICD-10-PCS `subtotals`, the SNOMED mapping totals and `registry.rows` are counts of entries in a
vocabulary. Rounding them would destroy the exact-match test `CLAUDE.md` stop condition 2 depends
on, which halts unless the locked set returns exactly 852 concepts with its locked subtotals, and it
would round a specification rather than a measurement. `cs_spine` documents the concept frame as
safe to log whole and this file records it exactly. Every count in the other four blocks is a count
of people or of person-days and is rounded before it is written.

**How a later session reads it instead of paying to re-run the probe.** The four priced probe
queries cost 13 to 18 GiB, about $0.08 to $0.11, and they answer questions whose answers do not
change between sessions against one CDR release: whether the Fitbit tables exist, what the per-zone
minute column is called, whether the zones partition the day, what the locked concept set resolves
to, and which visit concept ids this CDR actually carries. A session holding this file reads those
facts out of it:

1. Read `v1/probe/probe_result.json`. If it is absent, run the probe. There is no default for
   anything in it, and `02_pregate.py` refuses to run on assumed visit concept ids.
2. Compare `meta` against what `00_config.ipynb` resolved this session. If `workspace CDR` or
   `CDR location` differs, the file describes a different release: discard it and re-earn it. A
   probe result is valid for the CDR it was measured against and for no other.
3. If `probe ok` is `false`, stop. A stale pass is a fact; a stale failure is a plan change that was
   never made.
4. Otherwise take the facts and skip the queries. `--price-only` still runs the free metadata
   queries, so a session that wants to re-confirm the table inventory without spending can.

**`01_probe.py --write-json PATH`.** The path above is now the default, so the flag exists to send
the result somewhere else rather than to make writing possible at all. It still refuses any path
inside `v1/results/`, for the reason in point 2: that tree is the bundle, section 1 declares it
exhaustively, and a probe result in it is exactly the straggler `verify.py --bundle` rule 3 fails
on. The refusal now names the legal path rather than only the illegal one, because a refusal that
offers no alternative is how the next workaround gets written.

---

## 2. The value node grammar

Everything numeric in `results.json` is one of six node shapes. A consumer never sees a bare float
where a node is specified, and never sees a node where a bare scalar is specified.

### 2.1 Why a suppressed value is an object

**Decision: a suppressed value is a JSON object carrying `"suppressed": true`. It is never a
sentinel string, and never a `null` with a companion flag.**

| Candidate | Failure mode |
|---|---|
| Sentinel string (`"<20"`, `"suppressed"`) | Type-punches a numeric field. `float(x)` raises deep inside a renderer, far from the cause, and `sum()` on a column of mixed types either concatenates or raises with a message naming the wrong line. |
| `null` plus a companion flag | Two lookups where one will be forgotten. `value or 0` reads a suppressed cell as zero and prints it, which is worse than crashing: a suppressed count silently becomes a real number in a table. |
| **Object** (chosen) | Any arithmetic on a `dict` raises `TypeError` at the exact expression that mishandled it. The node carries its own reason and its own display string, so a renderer that handles it correctly needs no second lookup, and a renderer that handles it incorrectly cannot fail quietly. |

The object also gives suppression a single shape across counts, percentages, estimates and P values,
so one helper handles all four.

```json
{
  "suppressed": true,
  "reason": "cell_below_threshold",
  "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
  "display": "20 or fewer, suppressed per All of Us dissemination policy"
}
```

`reason` is a slug from the suppression-reason table in section 7.5. `reason_display` and `display`
are verbatim copies of that table's display column. A suppressed node carries **no** numeric key at
all: there is no `"n": null`, no `"est": null`. The number is not in the file.

### 2.2 The six node shapes

Every node carries `"suppressed": false` when it is disclosed, so a consumer can branch on one key
without a `.get()`. Every node carries `display`.

| Shape | Required keys | Types and units | Disclosed example |
|---|---|---|---|
| **count** | `suppressed`, `n`, `rounded`, `display` | `n` integer, already rounded by `round20` (or exactly `0`); `rounded` boolean, `false` only for an exact zero; `display` string with a thousands separator, zero decimals | `{"suppressed": false, "n": 1240, "rounded": true, "display": "1,240"}` |
| **percentage** | `suppressed`, `pct`, `num`, `den`, `display`, `display_count`, `display_denominator` | `pct` **integer**, zero decimals, computed from the ROUNDED `num` and the ROUNDED `den`; `num` and `den` integers; `display` ends in `%`. Used only where a real numerator exists. | `{"suppressed": false, "pct": 41, "num": 140, "den": 340, "display": "41%", "display_count": "140", "display_denominator": "340"}` |
| **estimate** | `suppressed`, `est`, `lo`, `hi`, `level`, `unit`, `display`, `display_point`, `display_ci` | `est`/`lo`/`hi` floats at the decimals for that unit (section 2.4); `level` float, always `0.95`; `unit` a slug from section 2.4 | `{"suppressed": false, "est": 4.4, "lo": 2.6, "hi": 6.2, "level": 0.95, "unit": "activity_days", "display": "4.4 (95% CI 2.6 to 6.2)", "display_point": "4.4", "display_ci": "95% CI 2.6 to 6.2"}` |
| **quantile** | `suppressed`, `q50`, `q25`, `q75`, `unit`, `display`, `display_point`, `display_iqr` | three floats at the unit decimals; the observed median and interquartile bounds | `{"suppressed": false, "q50": 9.1, "q25": 3.8, "q75": 17.2, "unit": "activity_days", "display": "9.1 (3.8–17.2)", "display_point": "9.1", "display_iqr": "3.8–17.2"}` |
| **pvalue** | `suppressed`, `p`, `floored`, `display` | `p` float, the raw value; `floored` boolean, `true` when `p < 0.001`; `display` is `P = 0.223` or `P < 0.001` | `{"suppressed": false, "p": 0.0004, "floored": true, "display": "P < 0.001"}` |
| **scalar** | `value`, `display` | a constant that is not a result: a window boundary, a threshold, a seed. Never suppressed, so it carries no `suppressed` key. | `{"value": 35, "display": "35"}` |

**Interval separator, fixed and non-negotiable:**

| Interval kind | Separator | Reason |
|---|---|---|
| Confidence interval | the word ` to ` | A confidence interval may cross zero; `-1.8`, en-dash, `3.6` is unreadable, and a column that switches separator by sign is worse than one that never switches. |
| Observed quantile range (IQR) | en-dash `–` | A quantile range of a non-negative quantity never carries a sign. |
| Day range, era band, threshold range | en-dash `–` | Ranges of ordered constants. |

The en-dash (U+2013) is the **only** dash permitted in a display string other than the ASCII
hyphen-minus (U+002D), which is the only sign character permitted on a negative number. The em-dash
(U+2014) and the Unicode minus (U+2212) appear nowhere in the bundle. `safe_export()` scans every
written string for both and refuses the write.

### 2.3 Reading a node: the three helpers every consumer copies

These three functions are the whole consuming API for `results.json`. All six local modules define
them identically; `verify.py` asserts the source text of the three is character-identical across the
modules that define them, so a private variant cannot drift.

```python
class Suppressed(ValueError):
    """Raised when a consumer asks for the number behind a suppressed node."""

def is_suppressed(node: dict) -> bool:
    return bool(node.get("suppressed", False))

def value(node: dict, key: str) -> float | int:
    """The raw number, or a loud failure. Never returns a default."""
    if is_suppressed(node):
        raise Suppressed(node["reason_display"])
    return node[key]                       # KeyError if the node is the wrong shape

def shown(node: dict) -> str:
    """The one string that may reach a rendered surface. Always safe to print."""
    return node["display"]
```

A renderer that prints `shown(node)` is correct for a disclosed node and for a suppressed node
without branching, because a suppressed node's `display` is the suppression sentence. A renderer that
needs the number calls `value()` and must catch `Suppressed` or let it propagate.

### 2.4 Units and decimals

`unit` is a machine slug. Its display form comes from section 7.6, never from the slug.

| `unit` slug | Meaning | Decimals | Example `display_point` |
|---|---|---|---|
| `activity_days` | Baseline-equivalent activity days lost, bounded at the window length | 1 | `12.4` |
| `thousand_steps` | Thousands of steps lost across the window | 1 | `42.6` |
| `normalized_activity` | Daily steps divided by the participant's own baseline, dimensionless | 2 | `0.68` |
| `steps` | Raw daily step count | 0, thousands separator | `6,420` |
| `days` | A count of calendar or postoperative days | 1 for a mean, 0 for a count | `24.3` |
| `percent` | A percentage computed from a rounded numerator over a rounded denominator. On an estimate node the percent sign is carried on all three numbers. | 0 | `41` |
| `absolute_risk_percent` | A model-predicted absolute risk, on the percent scale, with no numerator | 2 | `2.85` |
| `odds_ratio` | Odds ratio | 2 | `1.38` |
| `rate_ratio` | Ratio of two event rates on a common denominator | 2 | `1.74` |
| `rate_per_1000_episode_days` | Events per 1,000 episode-days at risk | 2 | `5.95` |
| `hours` | Hours | 0 | `36` |
| `minutes` | Minutes of wear | 0 | `600` |
| `count` | A count of persons, episodes, events or person-days | 0, thousands separator | `1,240` |
| `dimensionless` | ICC, R squared, rho, a delta shift on the normalized scale | 2 | `0.28` |
| `information_criterion` | AIC or BIC | 0, thousands separator | `18,420` |

`round20` applies to **counts only**. A continuous statistic (a median step count, an adjusted debt,
a mean normalized activity) is never rounded to 20; it is rounded to the decimals in this table, and
it is disclosable only when the count of participants contributing to it satisfies `disclosable()`.
Confusing these two rules is the single easiest way to leak: a median over three people is
individual-level data whatever its decimals, and unshifted Controlled Tier dates make it worse.

**Why `absolute_risk_percent` exists rather than two decimals on `percent`.** The two are different
quantities that happen to share a scale, and one rule cannot serve both. A `percent` value in this
bundle is a count over a count: `ANALYSIS-PLAN.md` section 8 rule 4 fixes it at a rounded numerator
over a rounded denominator printed to **zero** decimals, and both halves of that rule are
disclosure requirements rather than style, because a one-decimal percentage against a rounded
denominator lets a reader back-calculate an exact small numerator. Giving `percent` two decimals to
carry the absolute risk would weaken that rule on every count-derived percentage in the bundle,
which is roughly two hundred Table 1 cells, three ledger share columns and `share_zero_debt`. A
model-predicted absolute risk has no numerator to protect, so no rule of section 8 reaches it, and
at zero decimals the number this study actually expects, a 90-day acute-care risk of a few percent,
prints as `0%` in every row of Table 3 part B. Two rules, two units. `share_reaching_80pct_baseline`
stays on `percent` because it is a share in the tens of percent, where zero decimals carries the
number.

**Every exported statistic is rounded to its unit's decimals before the export gate sees it**, and
that is a disclosure rule and not a rendering one. Distinctness is computed on the in-memory float,
not on the rendered token, so a frame of unrounded medians is near-unique and is refused by 10.2
even though the printed CSV would look fine. `07_export.py` holds the decimals of this table as
`UNIT_DECIMALS` and applies them in `_round_to_unit()` before it builds any frame; 10.4 states the
obligation and 10.2 exception 5 states what remains after it.


### 2.5 The approved display vocabulary

Three rules elsewhere in this document ("every table cell is approved", "every prose numeral is
approved", "no hand-typed string") all refer to one set. It is defined once here:

> **The approved display vocabulary** is the set of string values of every key named `display` or
> beginning with `display_`, at any depth in `results.json`, together with every entry in the label
> table of section 7 and the literal empty string.

That set is what `verify.py` builds by walking the parsed `results.json` once. It contains
`display_point`, `display_ci`, `display_iqr`, `display_count`, `display_denominator` and
`display_n_equals` as well as the composed `display`, which is why a footer cell may print `0.62`
where the composed token is `0.62 (95% CI 0.55 to 0.69)`: both are approved, and neither was typed.

The figure-CSV token `SUPPRESSED` is **not** in the vocabulary. It never reaches a rendered surface;
the renderer maps it to the suppression sentence, which is in the vocabulary by way of the label
table.

---

## 3. `results.json`

Top-level keys, in the order `07_export.py` builds them. All eleven are mandatory on every run.
The file is written with `sort_keys=True`, so the on-disk order is alphabetical; the order below is
the order to read the specification in.

| Block | Purpose | Absent ever? |
|---|---|---|
| `meta` | Provenance: what ran, against what, seeded how, under which locked plan | no |
| `denominators` | Every denominator any exhibit prints, by name | no |
| `attrition` | The machine-readable cohort ladder | no |
| `cohort` | Group sizes, window constants, the collapse level reached | no |
| `debt` | The primary estimand and everything Table 2 prints | no |
| `sensitivity` | One entry per prespecified robustness row | no |
| `gate` | The A-through-F ledger, the tier, the verbatim permitted claim, Arm A if allowed | no |
| `figures` | One manifest entry per plot-ready CSV | no |
| `tables` | One manifest entry per printed table CSV | no |
| `suppressed` | Every key and row that exists but is hidden, with its reason | no, may be empty |
| `checks` | The exporter's own assertions and their results, for local re-assertion | no |

### 3.1 `meta`

| Key | Type | Unit / format | Example |
|---|---|---|---|
| `schema_version` | string | semver of THIS contract | `"2.0.0"` |
| `contract_sha256` | string | 64 hex, sha256 of `EXPORT-CONTRACT.md` as committed | `"9f2c...e10a"` |
| `study` | string | display title, house prose rules apply | `"Cumulative ambulatory activity loss after elective cervical and lumbar spine surgery"` |
| `generated_utc` | string | ISO 8601, `Z` suffix, second precision | `"2026-09-14T18:02:11Z"` |
| `run_id` | string | `<generated_utc>-<6 hex>`, unique per export | `"2026-09-14T18:02:11Z-a3f9c1"` |
| `code_commit_sha` | string | 40 hex, the commit the VM cloned | `"4b1f9d2c8a7e0135..."` |
| `cdr.resource_name` | string | the Verily resource, never a hardcoded dataset | `"C2025Q4R6"` |
| `cdr.resolved_dataset` | string | `project.dataset`, resolved at runtime | `"wb-silky-artichoke-2408.C2025Q4R6"` |
| `cdr.resolved_by` | string | the command that resolved it | `"wb resource resolve --name C2025Q4R6"` |
| `cdr.resolved_utc` | string | ISO 8601 Z | `"2026-09-14T16:41:02Z"` |
| `cdr.bq_location` | string | BigQuery location, mirrored by the derived dataset | `"US"` |
| `cdr.tier` | string | `"Controlled"` | `"Controlled"` |
| `cdr.version_label` | string | display label for the CDR release | `"cdrv9"` |
| `cdr.dates_shifted` | boolean | `false` on Controlled Tier. Drives the date-column ban. | `false` |
| `workspace.google_project` | string | the project that pays | `"wb-spinewear-4471"` |
| `workspace.derived_dataset` | string | `project.dataset` for the DAG | `"wb-spinewear-4471.spinewear_v1"` |
| `workspace.derived_location` | string | must equal `cdr.bq_location` | `"US"` |
| `analysis_plan.path` | string | repo-relative | `"prespecification/ANALYSIS-PLAN.md"` |
| `analysis_plan.sha256` | string | 64 hex of the locked bytes | `"c41d...9b77"` |
| `analysis_plan.locked_utc` | string | ISO 8601 Z, the lock timestamp | `"2026-08-25T22:41:07Z"` |
| `analysis_plan.locked_before_first_count` | boolean | `true` or the export is invalid | `true` |
| `analysis_plan.amendments` | array of object | `{n, utc, sections, change, reason, approved_by, superseded_sha256}`, one per row of `ANALYSIS-PLAN.md` section 13's log, in the log's own order, empty only when the log is. **`superseded_sha256` and not `sha256_after`; 3.1.3 says why.** | see 3.1.3 |
| `arm.slug` | string | `"recovery_debt"` or `"early_warning"` | `"recovery_debt"` |
| `arm.display` | string | label table 7.4 | `"Recovery debt"` |
| `arm.selected_by` | string | the rule, not a narrative | `"feasibility gate tier reached"` |
| `arm.tier_slug` | string | must equal `gate.tier.slug` | `"no_early_warning"` |
| `seeds.python` | integer | `0` | `0` |
| `seeds.numpy` | integer | `0` | `0` |
| `seeds.bootstrap` | integer | seed for the clustered bootstrap | `0` |
| `seeds.monte_carlo` | integer | seed for random-effect marginalization | `0` |
| `sampling_salt` | string | the salt `build_all.sql` declares and `build_params` publishes as `sampling_salt`; a **sibling of `seeds`, not a member of it**. Read from the DAG, never transcribed. 3.1.4 says why it sits here and what it is for | `"spinewear-v1-risk-set"` |
| `software.python` | string | | `"3.11.9"` |
| `software.packages` | object | name to version, sorted | `{"numpy": "1.26.4", "pandas": "2.2.2", "statsmodels": "0.14.2"}` |
| `software.r` | string or null | `null` when R was not used | `"4.3.2"` |
| `software.r_packages` | object | empty when R was not used | `{"glmmTMB": "1.1.9", "ordbetareg": "0.7.2"}` |
| `estimator.r_used` | boolean | `true` at rungs 1 and 2, `false` at rungs 3 to 5 | `true` |
| `estimator.rung_index` | integer | `1` to `5`, 1-based to match `ANALYSIS-PLAN.md` section 3.5 | `1` |
| `estimator.rung_slug` | string | from the ladder in `ANALYSIS-PLAN.md` section 3.5 | `"r_ordered_beta_glmm"` |
| `estimator.rung_display` | string | label table 7.7 | `"Ordered beta mixed model in R"` |
| `estimator.descent_triggers_fired` | array of string | trigger codes `T0` to `T4` that caused a descent, in the order they fired; empty at rung 1 | `[]` |
| `estimator.fallback_reason` | string or null | `null` at rung 1; otherwise the printed sentence naming the trigger | `null` |
| `estimator.rungs_attempted` | array of object | `{index, slug, outcome}` where `outcome` is `"converged"`, `"did not converge"`, `"skipped"` or `"not attempted"` | see 3.1.1 |
| `estimator.bootstrap_failure_rate` | percentage node | share of clustered bootstrap resamples that failed to converge; reported whatever it is (trigger T4). Its `num` is `round20`-rounded like every other percentage numerator, so a failure count of 20 or fewer suppresses the node rather than printing a small integer | |
| `concept_set.n_concepts` | scalar node | size of the locked spine concept set, in **concepts**: what the 51 codes and stems of the registry ledger resolve to in this CDR. A concept count, not a person count, and never rounded | `{"value": 852, "display": "852"}` |
| `concept_set.source_module` | string | the module that owns the set | `"pipeline/cs_spine.py"` |
| `concept_set.registry_file` | string | the ledger carrying one row per code or stem, 51 rows; **not** one row per concept, and 5.6 says why | `"ledgers-csv/ledger_concept_set_registry.csv"` |
| `concept_set.gaps` | object | the two prespecified gap measurements of `ANALYSIS-PLAN.md` section 2.7, keyed `cervical_decompression` and `cervical_fusion` | see 3.1.2 |
| `manifest_rows` | integer | number of data rows in `MANIFEST.csv`; a cheap cross-check | `16` |

`meta` carries **no participant-derived value**. `generated_utc`, `resolved_utc` and `locked_utc` are
run timestamps, not participant dates; the date ban in section 10 applies to participant-derived
columns only, and this is why the distinction is written down rather than assumed.

#### 3.1.1 The estimator ladder

The rung enumeration is owned by `ANALYSIS-PLAN.md` section 3.5. This contract fixes the shape and
the keys. `verify.py` asserts `estimator.rung_slug` is a member of the plan's ladder and that
`estimator.rung_index` equals its position there. The ladder, transcribed from the plan:

| index | slug | display | runs in |
|---|---|---|---|
| 1 | `r_ordered_beta_glmm` | Ordered beta mixed model in R | R Analysis Environment |
| 2 | `r_zero_one_inflated_beta_glmm` | Zero-one-inflated beta mixed model in R | R Analysis Environment |
| 3 | `py_fractional_logit_gee` | Fractional-response quasi-binomial estimating equations | Python, standard image |
| 4 | `py_linear_mixed_truncated` | Linear mixed model with fitted values truncated to the unit interval | Python |
| 5 | `py_nonparametric_day_group_means` | Nonparametric day and group means | Python |

Descent trigger codes, also from the plan, recorded verbatim in `estimator.descent_triggers_fired`:
`T0` environment unavailable (skips rungs 1 and 2 together), `T1` non-convergence, `T2` boundary
estimate, `T3` singular covariance, `T4` bootstrap instability. Every trigger is a computational
property of the fit or of the environment. **No trigger references the direction, magnitude or
significance of any contrast**, and `07_export.py` therefore records the trigger without recording
any estimate from the rung that failed.

Rung 5 cannot fail and is the guaranteed floor, so `estimator.rung_index` is always populated and
`debt` is never absent for want of an estimator.

If `ANALYSIS-PLAN.md` locks a different ladder, the plan wins and this table is amended.

#### 3.1.2 `meta.concept_set.gaps`, the two concept-set measurements

`ANALYSIS-PLAN.md` section 2.7 measures two known gaps on the cervical side and fixes the response
to each **before** the number exists. Both numbers are quoted in the Methods whatever they show,
including a measured zero, so both need a `display` string in `results.json` or R4 has nothing to
check the prose against. The builders live in `pipeline/cs_spine.py`; this block is where their
output crosses the boundary.

| Key, under `concept_set.gaps.<gap>` | Type | Notes |
|---|---|---|
| `builder` | string | the `cs_spine` function that produced the row, e.g. `"cs_spine.cervical_fusion_split_sql"` |
| `evidence_path_first` | string | the `evidence_path` value of the first row the builder returns, always `"candidate CPT only, invisible to the locked set"` |
| `n_candidate_only` | count node | persons on that first row: `C` for the decompression gap, the candidate-fusion carriers for the fusion gap |
| `n_locked_set` | count node | `D`, the persons the locked set classifies into the arm this gap threatens |
| `n_misfiled` | count node | fusion gap only: `M`, the `n_also_carrying_locked_cervical_decompression` value on the first row |
| `n_also_carrying_candidate_cpt` | count node | fusion gap only, carried through from the builder |
| `share` | percentage node | `f_missing = C / (C + D)` for the decompression gap, `f_misfiled = M / D` for the fusion gap |
| `response_display` | string | the prespecified response the measured share selected, verbatim from the plan's response table |
| `set_amended` | boolean | `true` only where the plan's threshold was crossed and section 13 carries the amendment |

**All of these are person counts.** Every one is tested with `disclosable()` on its true value and
then `round20`-rounded before it reaches this block, in that order, and `share` is computed from the rounded numerator over the rounded
denominator like every other percentage in the bundle (section 8 rule 4). A gap builder's raw output
never crosses the boundary.

**Row order is fixed by the builder, and the first row is the one that matters.** Both
`cervical_decompression_split_sql()` and `cervical_fusion_split_sql()` sort by `evidence_path`, so
`candidate CPT only, invisible to the locked set` arrives **first**, not fourth. `07_export.py` reads
row 0 for `n_candidate_only` and, in the fusion case, for `n_misfiled`; it must not index the last
row, and it must not re-sort. The builders return four rows each and carry the columns
`evidence_path`, `n_persons`, `n_also_carrying_candidate_cpt` and, for the fusion builder,
`n_also_carrying_locked_cervical_decompression`.

Two of the supplementary sensitivity rows of 3.6 are attached to these measurements,
`cervical_fusion_gap_reclassified` and `cervical_decompression_gap_stated`, and neither is plotted
in Figure 3.

#### 3.1.3 `meta.analysis_plan.amendments`, and why the hash it carries is the SUPERSEDED one

One object per row of `ANALYSIS-PLAN.md` section 13's amendment log, in the log's own order,
carrying what the row carries and nothing derived:

| Key | Type | Notes |
|---|---|---|
| `n` | integer | 1-based position in the log, which is the row's ordinal and not a row id the plan states |
| `utc` | string | the log row's **Date** column, verbatim. Section 13's table records a DATE; the lock STAMPS live in the log's prose in an order no reader can pair with the rows, so the date is carried and nothing is upgraded into a precision the source does not have |
| `sections` | string | the sections the amendment touched, verbatim |
| `change` | string | what changed, verbatim |
| `reason` | string | why, verbatim |
| `approved_by` | string | verbatim |
| `superseded_sha256` | string | 64 hex: the hash of the plan the amendment **replaced** |

**`sha256_after` is not available and this contract no longer asks for it.** Until 2.0.0 the row
above proposed `{n, utc, reason, sha256_after}`, and the resulting-hash half of that shape is a fact
section 13 does not hold. Section 13 records the superseded hash **by design**, and its opening
paragraph states the reason: a file cannot contain its own hash, so the only hash a row of the log
can carry is the one it replaced. Three consequences, each of which is why the field is absent
rather than computed:

1. **Chaining is not available either.** `sha256_after` of row *i* would be `superseded_sha256` of
   row *i+1*, which assumes the table is in chronological order. `07_export.py` cannot check that
   the table is chronological, the log's prose does not obviously guarantee it, and an exporter that
   assumed it would put a hash in the Methods that is right only if an unverified property holds.
2. **The last one is already in the bundle.** The hash after the final amendment is the hash of the
   plan as locked, which is `meta.analysis_plan.sha256`, read from `PLAN-HASH.txt` in the same call
   that reads the log. A second copy of it under another name adds no fact.
3. **Inventing it would state a number no document states**, which is the failure this whole block
   exists to prevent: the Methods cites the plan by hash and by date **and** cites any amendment,
   so every one of those citations has to be traceable to a document that says it.

`07_export.py` reads the log with `plan_amendment_entries()`, off the same tree read that produces
`sha256` and `locked_utc`, so the hash, the date and the log move together or not at all. Its
self-test asserts one entry per row of section 13, an ordinal per entry, and 64 hex on every
`superseded_sha256`.

#### 3.1.4 `meta.sampling_salt`, a sibling of `seeds` and not a member of it

**What it is.** `build_all.sql` orders the control risk set with

```
FARM_FINGERPRINT(FORMAT('%s|%d|%s|%s|%d',
  (SELECT sampling_salt FROM p), (SELECT seed FROM p),
  cr.set_id, cr.control_episode_id, cr.control_matched_day))
```

so the matched sets are a function of the seed **and** the salt. A session holding one and not the
other reproduces a different set of controls and has nothing to tell it so. The salt is therefore a
reproducibility input of exactly the same standing as the seeds, and the bundle records it for
exactly the same reason.

**Where it comes from, in one line each.** `build_all.sql` declares it,
`DECLARE sampling_salt STRING DEFAULT '<salt>';`; the `build_params` stage publishes it as the
column `sampling_salt`; `DAG-SCHEMA.md` documents that column as a `STRING`, never null, an
internal constant; `03_cohort.py` passes it as `sampling_salt` in `dag_parameters()`. Four
documents, one name, one type.

**Why it is a sibling of `seeds` rather than a member.** `seeds` is not a bag of reproducibility
inputs; it is the block whose every member is governed by one sentence. `ANALYSIS-PLAN.md` section
10 fixes `SEED = 0` "everywhere, in Python and in R" and 4.5 repeats it for the `FARM_FINGERPRINT`
sampling by name, and `verify.py` reads that as licence to compare **every** member of `seeds`
against `0`. That reading is correct and must stay correct: it is what makes a wrong seed a finding
rather than a value somebody has to notice. A string member breaks it in the worst available way,
by turning a comparison that should fail into a disagreement between two governing documents. The
salt sits beside the block, at the DAG's own name and the DAG's own type, so `seeds` keeps meaning
"the members section 10 fixes at 0" and the salt keeps meaning "the string the DAG salts with".

It is a bare `string` and not a one-member `salts` object because the DAG publishes exactly one
salt under exactly that name; a plural block would invent a family the DAG does not have, which is
the same species of error as the field it replaces. Its provenance is stated here, in this
document, rather than carried as sibling keys in the bundle, which is how `analysis_plan.path` and
`cdr.resolved_by` already work.

**How `07_export.py` obtains it, and the assertion that holds it there.** The payload carries the
salt out of `build_params.sampling_salt`, which is what the run actually sampled with.
`dag_sampling_salt()` reads the `DECLARE` out of the `build_all.sql` sitting beside the module, and
`_render_meta` **refuses to render a bundle whose salt is not the one the DAG in the tree
declares**; `validate_bundle()` asks the same question of a bundle already written. The module
carries no literal copy of the salt at all, and its self-test asserts that the salt does not occur
in its own source. `meta.seeds` is refused if it carries a `farm_fingerprint` key or any member
that is not an integer.

**What this row replaces.** From the version that introduced it until 2.0.0 this contract declared
`seeds.farm_fingerprint`, an `integer`, "the fixed salt for BigQuery sampling", at `20260825`. That
number appears in no other file of this project: not in the DAG that samples, not in `build_params`
that publishes, not in `DAG-SCHEMA.md` that documents the column, not in `03_cohort.py` that passes
it, and not in `ANALYSIS-PLAN.md`. It was wrong in three compounding ways -- a value with no
referent, a string declared as an integer, and a salt filed as a seed -- and all three had one
cause, which is that the value was typed here instead of read from the DAG. `verify.py`'s
`plan-constants` check reported it as a document disagreement and pinned it as its single
known-open finding, which is the mechanism working: it could not tell a fabricated constant from a
plan that had moved, because on the evidence in the bundle those look identical.

### 3.2 `denominators`

Shape and access path are the house shape, so `denom_n()` from
`NSQIP/projects/opioid-shoulder-arthroscopy/v2/pipeline/03_figures.py` works unmodified:

```python
def denom_n(results: dict, key: str) -> int:
    return int(results["denominators"][key]["n"])
```

`denominators[key]` is an object, **not** a count node, because it carries provenance the node shape
has no room for. Its `n` is already `round20`-rounded.

| Key of the entry | Sub-key | Type | Meaning |
|---|---|---|---|
| any | `n` | integer | the rounded denominator |
| any | `unit` | string | `"persons"`, `"episodes"`, `"events"`, `"person-days"` or `"risk-set members"` |
| any | `display` | string | `"340"`, thousands separator, zero decimals |
| any | `display_n_equals` | string | `"n = 340"`, the exact token an exhibit prints |
| any | `definition` | string | one sentence, house prose rules apply |
| any | `used_for` | string | which exhibits print it. Prose, not a list of module names. |

Required denominator keys, all mandatory:

| Key | Unit | Definition | Ladder rung it reads off |
|---|---|---|---|
| `program_participants` | persons | All participants in the Controlled Tier release | `n_in` of step 1 |
| `episodes_identified` | episodes | Qualifying spine surgical episodes after same-day collapse | `n_out` of step 2 |
| `episodes_eligible` | episodes | Identified episodes surviving every protocol exclusion | `n_out` of step 10 |
| `episodes_wearable_linked` | episodes | Eligible episodes with any Fitbit activity record | `n_out` of step 11 |
| `episodes_baseline_adequate` | episodes | Wearable-linked episodes with adequate preoperative baseline wear | `n_out` of step 12 |
| `analytic` | episodes | The analytic cohort. The default denominator for every exhibit that does not name another. | `n_out` of step 16 |
| `analytic_person_days` | person-days | Contributing person-days inside the accrual window | not a rung |
| `events_composite` | events | First acute-care events through post-discharge day 90 | `n_out` of step 17 |
| `event_centered_members` | risk-set members | Risk-set members drawn on the event-centered curve, after the structural filter | not a rung |

The fourth column exists so that a denominator and a ladder box carrying the same quantity carry the
same number. Where a denominator names a rung, `verify.py` asserts the two are equal after rounding.
`episodes_eligible` is the survivors of the eligibility exclusions, steps 3 through 10, and
deliberately does **not** include the first-eligible-episode reduction of step 13, which is an
episode-selection rule rather than an eligibility criterion.

**Every key above is required on every run**, and `07_export.py` refuses a payload missing one
rather than rendering the block it was handed. An exhibit's `denominator` field is a **pointer**,
and a pointer whose target is optional is not a pointer: until the exporter checked, a caller that
omitted a mandatory entry produced a bundle that validated locally and carried an exhibit naming a
key nobody wrote.

**`event_centered_members` is new at 1.8.0 and it exists because 4.4's exhibit had no denominator
of its own to name.** 3.8 makes an exhibit's printed denominator a key of this block, and until
this version the only candidate for the event-centered curve was `events_composite`. That is not
the population the curve is drawn over. The curve is drawn over **risk-set members**, and it
carries the same structural filter the conditional and discrete-time fits carry, on
`ANALYSIS-PLAN.md` 4.4's rule that a member whose landmark window holds fewer than two
post-discharge days is outside the co-primary exposure "on every surface"; the two counts
therefore differ by exactly the members that filter removes, and the plate note printed a number
larger than the curve's own. The producing query in `06_analysis_gate.py` already returns the
members behind each curve and the members the filter removed, per role, on every row, so this
entry names a count that is measured rather than one that has to be invented.

**Why the unit is `risk-set members` and not `episodes` or `events`.** One episode can be a member
of several risk sets, so a member count is not an episode count, and the producing query says so
in terms; the curve's two series are cases **and** their matched controls, so it is not an event
count either. A fifth unit is cheaper than a fourth that is wrong, and 4.4's own obliged counts
are member counts for the same reason.

**It is 0 at tier 4, and 0 is the honest number rather than a placeholder.** At
`no_early_warning` no event-centered query is submitted at all, so no member is drawn; a real zero
is `disclosable()` and satisfies `is_legal_disclosed_count()`, and 4.4 already writes that file as
44 rows of `SUPPRESSED`. `07_export.py` asserts the two agree in both directions: a tier that
permits no plot may not carry a non-zero curve denominator, and a permitting tier may not carry a
zero one, so the denominator cannot go stale while every row of the file still says the right
thing.

### 3.3 `attrition`

The machine-readable cohort ladder. `attrition.rungs` is an array in ladder order; index 0 is the
program cohort.

| Key | Type | Meaning |
|---|---|---|
| `rungs[i].step` | integer | 1-based position; equals `i + 1` |
| `rungs[i].slug` | string | stable identifier, owned by `03_cohort.py` and `ANALYSIS-PLAN.md` |
| `rungs[i].display_label` | string | label table 7.2, printed in the flow figure box |
| `rungs[i].kind` | string | `"exclusion"`, `"conversion"` or `"terminal"` |
| `rungs[i].unit` | string | `"persons"`, `"episodes"` or `"events"` on an `exclusion` or `terminal` rung; on a `conversion` rung it names both sides, so it is `"persons to episodes"` at step 2 and `"episodes to events"` at step 17. Five permitted values in all, transcribed from the plan's own column. `segments[j].unit` uses only the three simple ones |
| `rungs[i].n_in` | count node | rounded |
| `rungs[i].n_dropped` | count node, or `null` when `kind` is not `"exclusion"` | rounded, may be suppressed |
| `rungs[i].n_out` | count node | rounded, may be suppressed |
| `rungs[i].n_carried_forward` | count node, or `null` on every rung but step 2 | rounded; persons carried out of `episode_construction` into the episode unit |
| `rungs[i].reason` | string | for an `exclusion` rung, the rung's own `slug`; the literal `"unit_change"` on a `conversion` rung; the empty string on a `terminal` rung |
| `rungs[i].reason_display` | string | the sentence printed in the right-hand exclusion box, verbatim from label table 7.2 |
| `rungs[i].closes_exact` | boolean | asserted inside the perimeter on the TRUE integers, before rounding |
| `attrition.segments` | array of object | three entries, one per unit regime; see below |
| `attrition.closes` | boolean | the AND of every rung's and every segment's `closes_exact`. The local side re-asserts. |
| `attrition.rounding_footnote` | string | the sentence every exhibit prints below the ladder |

**`reason` carries no vocabulary of its own.** It is derived, not chosen: on an exclusion rung it is
that rung's `slug`, so the set of `reason` values is a subset of the set of rung slugs and needs no
separate table for `verify.py` to assert against. Earlier drafts of this contract invented per-rung
reason slugs (`no_spine_procedure`, `no_wearable_record`); those are retired, because a sixth slug
vocabulary that no document owns is exactly how six modules diverge.

**`kind` and why the ladder needs three of them.** An `exclusion` rung removes rows in a fixed unit:
`n_in - n_dropped = n_out`. A `conversion` rung changes the unit (persons to episodes at step 2,
episodes to events at step 17) and is excluded from every within-unit closure sum. A `terminal` rung
is a labelled endpoint carrying only `n_out`. Without this distinction the ladder either fails to
close at the unit change or has to fake a drop, and both are worse than naming it.

**Step 2 is a conversion that also drops, which is why it needs a third count.** `n_in` is persons,
`n_out` is episodes, and the two cannot be differenced. `n_carried_forward` is the count of persons
who survive the rung, in persons, so the persons-unit identity closes on it and the episode-unit
identity starts from `n_out`. The re-basing is labelled, never silent. `n_dropped` at step 2 is
persons who carry a qualifying concept but whose records yield no dated episode.
`n_carried_forward` is `null` on all eighteen other rungs.

**`segments`** partitions the ladder into its three unit regimes, because the three do not share one
identity and asserting a single global closure over them is asserting an identity that does not
exist:

| Key | Type | Meaning |
|---|---|---|
| `segments[j].unit` | string | the unit throughout this segment |
| `segments[j].first_step` | integer | |
| `segments[j].last_step` | integer | |
| `segments[j].n_start` | count node | the first count in this unit: `rungs[first_step - 1].n_in` where the segment opens on an exclusion rung, and `rungs[first_step - 1].n_out` where it opens on a conversion rung |
| `segments[j].n_end` | count node | the last count in this unit: `rungs[last_step - 1].n_out`, except in the persons segment where it is `rungs[1].n_carried_forward` |
| `segments[j].sum_dropped` | count node | the sum of every `exclusion` rung's rounded `n_dropped` in the segment, plus step 2's `n_dropped` in the persons segment |
| `segments[j].n_rounded_terms` | integer | how many independently rounded counts the segment's identity contains: `2 + (number of dropped terms summed)` |
| `segments[j].tolerance` | integer | `10 * n_rounded_terms`, exported so the local side compares rather than recomputes |
| `segments[j].closes_exact` | boolean | asserted on true integers inside the perimeter |
| `segments[j].rounded_residual` | integer or `null` | `n_start - sum_dropped - n_end`, computed on the ROUNDED values as exported; `null` when any of the three is suppressed, in which case the segment check is skipped and `closes_exact` carries the guarantee |

The three segments, fixed:

| j | unit | steps | identity asserted | rounded terms | tolerance |
|---|---|---|---|---|---|
| 0 | persons | 1 to 2 | `n_in(1) - n_dropped(1) - n_dropped(2) = n_carried_forward(2)` | 4 | 40 |
| 1 | episodes | 2 to 16 | `n_out(2) - sum(n_dropped, steps 3 to 15) - n_out(16) = 0`, thirteen dropped terms | 15 | 150 |
| 2 | events | 17 to 19 | `n_out(17) - n_dropped(18) - n_out(19) = 0` | 3 | 30 |

**Steps 17 and 19 are outside the global drops-plus-analytic-n assert.** Steps 17 to 19 close among
themselves and against nothing else. A consumer that adds step 18's `n_dropped` into the episode-unit
sum is adding events to episodes and will get a residual it cannot interpret.

**The closure check the local side runs**, in `make_strobe.py` and again in `figures.py`:

1. `attrition.closes` is `true`. If it is `false`, raise. The ladder failed inside the perimeter and
   nothing downstream is trustworthy.
2. **Chaining, tolerance 0.** For consecutive rungs in the same unit, `rungs[i].n_out.n` equals
   `rungs[i + 1].n_in.n` exactly. They are `round20` applied to one true integer, so rounding cannot
   separate them, and a difference of even 20 is a real defect rather than rounding. The same
   applies across step 17: `rungs[16].n_in.n == rungs[15].n_out.n`.
3. **Exclusion rung, tolerance 30.** For every `exclusion` rung whose `n_dropped` and `n_out` are
   both disclosed: `abs(n_in.n - n_dropped.n - n_out.n) <= 30`.
4. **Step 2, tolerance 30 and one inequality.**
   `abs(n_in.n - n_dropped.n - n_carried_forward.n) <= 30`, and
   `n_out.n >= n_carried_forward.n - 20`, since a carried person yields at least one episode and the
   two counts are rounded independently.
5. **Step 17, tolerance 0 and no drop.** It carries `n_dropped: null`, asserts only
   `n_in.n == rungs[15].n_out.n`, and its own `n_out` is a count of events, which may be exactly `0`.
   A zero here is disclosable and is printed as `0`; it is not suppressed.
6. **Segments, tolerance `segments[j].tolerance`.**
   `abs(segments[j].rounded_residual) <= segments[j].tolerance`.

**Why the tolerance is per segment and not a global 30.** Each exported count is independently
rounded to the nearest 20, so each carries an error of at most 10, and an identity over `k` rounded
terms carries an error of at most `10k`. A three-term rung identity therefore tolerates 30, and the
episode segment, which sums thirteen dropped terms between two endpoints, tolerates 150. A single
global 30 would either fail on a correct ladder or, applied only to the rung identities, leave the
segment identity unchecked. Demanding exact closure on rounded boxes would force the exporter to
adjust a published number to make the arithmetic work, which is falsification. The published
resolution is the footnote, which every exhibit carrying the ladder must print verbatim:

> `attrition.rounding_footnote` = "Counts are rounded to the nearest 20 in accordance with the
> All of Us dissemination policy, so the boxes may not sum exactly. The unrounded ladder was
> asserted to close before rounding."

**When a rung's `n_dropped` is suppressed**, checks 3 and 4 are skipped for that rung, that rung's
contribution drops out of its segment's `sum_dropped`, the segment check is skipped too, and
`closes_exact` carries the guarantee instead. `verify.py` asserts that every skipped rung and every
skipped segment has `closes_exact: true`, so a skip can never hide a broken ladder.

**Nineteen rungs, transcribed from `ANALYSIS-PLAN.md` section 2.6**, which owns them. The plan emits
`step, slug, kind, unit, n_in, n_dropped, n_out, reason`; this contract carries that set plus the
rendering columns `display_label`, `reason_display`, `closes_exact`, `box_side` and, at step 2,
`n_carried_forward`. `verify.py` asserts set equality of the slug column against the plan and against
`figure1_strobe_ladder.csv`. Display labels and reason displays are in label table 7.2 and are
governed by character equality; they are not restated here.

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

**The order is fixed and is not an implementation detail.** A ladder counts each episode once, at the
first rung it fails, so reordering changes every rung's `n_dropped` without changing the analytic n,
and it changes what the Figure 1 exclusion boxes say. Reordering is an amendment under the plan's
section 13, not a change to this file.

Four rungs deserve a note, because a consumer will otherwise mis-read what they count:

- **Step 8, thoracic only** (`ANALYSIS-PLAN.md` sections 2.4 and 2.6). Under the mirrored junction
  map of the `junctions_mirrored` supplementary row, a cervicothoracic bundle moves from cervical to
  thoracic-only, that is from included to excluded, so the primary run and the mirrored run have
  **different ladders**. This is expected. The closure assert tolerates it because each run exports
  its own ladder and its own `closes_exact`; nothing compares one run's rung counts to the other's.
- **Step 13, not the first eligible episode.** This is the rung that makes the ladder close under the
  plan's first-eligible-episode rule. Person and episode coincide in the primary, which is what makes
  the person random effects and the person-clustered bootstrap coherent. Any statement anywhere that
  a participant may contribute more than one episode **to the primary** is wrong and is corrected
  against this rung.
- **Step 15** removes episodes whose window is truncated by death or by a repeat spine operation
  (`ANALYSIS-PLAN.md` section 2.3). These are expected to be too few to disclose, so this rung's
  `n_dropped` will very likely be a suppressed node. The supplementary row
  `truncated_assigned_max_debt` assigns them the maximal debt of 35 days lost and is reported
  whatever the count.
- **Step 18** removes acute-care events on post-discharge day 1 to 4, which have no computable
  proximal window. Day 1 to 4 rather than day 1 to 3: the protocol's proximal window needs two valid
  days, the first eligible landmark is post-discharge day 2, and the earliest event it can serve sits
  on post-discharge day 5, so days 1 through 4 are structurally uncomputable
  (`ANALYSIS-PLAN.md` sections 2.3 and 5.2). Their timing is reported rather than left implicit.

### 3.4 `cohort`

| Key | Type | Unit | Example |
|---|---|---|---|
| `groups` | array of object | the procedure groups at the selected collapse level in print order, then the pooled entry `all_groups`. Five entries at `four_group`, three at `two_group`, one at `single_group`, none at `no_estimand`. **Never assume five.** | see below |
| `groups[i].slug` | string | | `"lumbar_fusion"` |
| `groups[i].display_label` | string | label table 7.1 | `"Lumbar fusion"` |
| `groups[i].order` | integer | 1-based print order, stable across every exhibit; `5` is the pooled entry | `4` |
| `groups[i].n` | count node | episodes | `{"suppressed": false, "n": 80, ...}` |
| `groups[i].column_header` | string | the exact Table 1 column header, carrying its own n | `"Lumbar fusion (n = 80)"` |
| `collapse_level` | string | `"four_group"`, `"two_group"`, `"single_group"` or `"no_estimand"` | `"four_group"` |
| `collapse_level_index` | integer | `1`, `2`, `3` or `0`, matching `ANALYSIS-PLAN.md` section 2.5 | `1` |
| `collapse_reason` | string | the prespecified trigger that selected the level | `"every procedure group at or above the disclosure floor"` |
| `collapse_footnote` | string or `null` | the sentence Table 1 prints when the level is not `four_group`; `null` at `four_group` | `null` |
| `denominator_index` | array of string | the `denominators` keys any exhibit prints, in the order they first appear | `["analytic", "episodes_identified", ...]` |
| `window.accrual_first_day` | scalar node | post-discharge day | `{"value": 1, "display": "1"}` |
| `window.accrual_last_day` | scalar node | post-discharge day | `{"value": 35, "display": "35"}` |
| `window.follow_up_last_day` | scalar node | post-discharge day | `{"value": 90, "display": "90"}` |
| `window.baseline_first_day` | scalar node | postoperative day, negative | `{"value": -30, "display": "-30"}` |
| `window.baseline_last_day` | scalar node | postoperative day, negative | `{"value": -8, "display": "-8"}` |
| `window.baseline_min_valid_days` | scalar node | days | `{"value": 7, "display": "7"}` |
| `window.baseline_min_span_days` | scalar node | days | `{"value": 14, "display": "14"}` |
| `window.valid_day_min_minutes` | scalar node | minutes of wear | `{"value": 600, "display": "600"}` |
| `window.display_accrual` | string | the printed range, en-dash | `"post-discharge day 1–35"` |
| `window.display_baseline` | string | the printed range | `"8–30 days before surgery"` |
| `min_cell` | scalar node | `disclosure.MIN_CELL`, recorded so the local side can print the floor without retyping it | `{"value": 20, "display": "20"}` |

**The number of groups is data-dependent, and every consumer must treat it that way.** The collapse
ladder of `ANALYSIS-PLAN.md` section 2.5 is decided once, on the exact within-perimeter counts,
before any model is fit:

| `collapse_level` | index | Groups in `cohort.groups` | Consequence |
|---|---|---|---|
| `four_group` | 1 | 4 procedure groups plus `all_groups` | Figure 2 shows four series; Table 1 has four group columns |
| `two_group` | 2 | `fusion` and `decompression` plus `all_groups` | Figure 2 shows two series; Table 1 collapses to two group columns and prints `collapse_footnote` |
| `single_group` | 3 | `all_groups` only | One curve, one level, **no contrast**. Figure 3 block 1 is empty and prints the sentence in `collapse_footnote`. |
| `no_estimand` | 0 | none | The analytic cohort is itself below the floor. Only the attrition ladder is exported; `debt` and `sensitivity` carry a single suppressed entry each and every exhibit but Figure 1 prints its reason. |

No consumer hardcodes four groups, four Table 1 columns or four Figure 2 series. The group list comes
from `cohort.groups` and the column list from `tables[key].columns`, both read at run time. This is
why `load_table` checks the manifest's columns against the file rather than against a literal.

At `two_group` the group slugs are `fusion` and `decompression`, with display labels `Fusion` and
`Decompression`; those two entries are part of label table 7.1.

### 3.5 `debt`

The whole of Table 2 and Figure 3 block 1.

| Key | Type | Unit | Notes |
|---|---|---|---|
| `estimand.display` | string | | The one-sentence definition Methods prints |
| `estimand.unit` | string | `activity_days` | |
| `estimand.max_possible` | scalar node | activity days | equals the window length, 35 |
| `estimand.estimator` | string | | `"model and integrate"`, never `"sum the observed days"` |
| `by_group` | array of object | one per `cohort.groups`, same `order` | see below |
| `by_group[i].slug` | string | | matches `cohort.groups[i].slug` |
| `by_group[i].n` | count node | episodes | the group denominator |
| `by_group[i].n_complete_windows` | count node | episodes | the denominator of the UNADJUSTED column only, which is computed on complete windows and therefore has its own n |
| `by_group[i].unadjusted_debt` | quantile node | `activity_days` | observed median and IQR by direct summation on complete windows. Labelled the naive estimator wherever it prints. |
| `by_group[i].adjusted_debt` | estimate node | `activity_days` | the marginal integrated fitted deficit of the plan's section 3.8 |
| `by_group[i].thousand_steps_lost` | estimate node | `thousand_steps` | the absolute-scale companion, immune to the baseline floor |
| `by_group[i].adjusted_mean_normalized_activity` | estimate node | `normalized_activity` | mean normalized activity capped at baseline, that is `1 - D_bar`, across the accrual window |
| `by_group[i].share_reaching_80pct_baseline` | estimate node | `percent` | **an estimate node, not a percentage node.** It is a fitted probability from a logistic g-computation, so it has a confidence interval and no numerator. Its disclosability follows the group's contributing n, not a count. |
| `by_group[i].share_zero_debt` | percentage node | `percent` | observed share whose integrated deficit is zero. A count over a denominator, so it is a percentage node. |
| `contrasts` | object | keyed by contrast slug | see below |
| `contrasts[slug].display_label` | string | label table 7.3 | |
| `contrasts[slug].estimate` | estimate node | `activity_days` | difference scale, so it may be negative |
| `contrasts[slug].pvalue` | pvalue node | | |
| `contrasts[slug].is_primary` | boolean | exactly one contrast carries `true` | |
| `contrasts[slug].n_compared` | count node | episodes | the two groups combined |
| `unadjusted_contrasts` | object | keyed by contrast slug, **the same slugs as `contrasts`** | the unadjusted twin of every contrast above, for STROBE item 16(a). **Reporting-guideline-mandated, not prespecified**; see below |
| `unadjusted_contrasts[slug].display_label` | string | label table 7.3 | the **same** label as the adjusted contrast, because it is the same contrast. No new label slug is created and 7.3 does not grow |
| `unadjusted_contrasts[slug].estimate` | estimate node | `activity_days` | difference scale, so it may be negative. Its **own** interval, from its own person-clustered bootstrap, never the adjusted contrast's |
| `unadjusted_contrasts[slug].pvalue` | pvalue node | | |
| `unadjusted_contrasts[slug].is_primary` | boolean | exactly one carries `true`, and it is the same slug that carries it in `contrasts` | |
| `unadjusted_contrasts[slug].n_compared` | count node | episodes | its **own** n, the two groups combined on the rows the unadjusted fit used |
| `unadjusted_model.definition_display` | string | | one sentence naming exactly which terms were removed and which were kept. Printed wherever the pair is |
| `unadjusted_model.mandate_display` | string | | one sentence naming the reporting item that requires the quantity and saying in terms that `ANALYSIS-PLAN.md` does not prespecify it |
| `unadjusted_model.prespecified` | boolean | | `false` at plan version 1.5. **Declared, never inferred**: Methods must say which, and a boolean beside the number is the only form of that statement a consumer cannot lose in transcription |
| `unadjusted_model.rung_slug` | string or `null` | a slug of 3.1.1 | the estimator rung the **unadjusted** fit reached, which need not be the adjusted fit's. `null` when the fit returned no estimate |
| `unadjusted_model.rung_display` | string or `null` | label table 7.7 | |
| `unadjusted_model.rung_index` | integer or `null` | | its position in the 3.1.1 ladder |
| `unadjusted_model.rung_matches_adjusted` | boolean or `null` | | `false` is a **reportable fact and not a failure**; `null` when the fit returned no estimate |
| `unadjusted_model.rung_note_display` | string | | the sentence printed beside the pair. It differs by whether the two rungs matched, because what a reader may conclude from the gap differs |
| `unadjusted_model.bootstrap_failure_rate` | percentage node | `percent` | resamples that returned no unadjusted contrast, over resamples attempted. The same shape as `meta.estimator.bootstrap_failure_rate` and for the same reason: these are resample counts, not participant counts |
| `unadjusted_model.not_estimable_reason` | string or `null` | a slug of 7.5 | `null` when the fit returned an estimate. `not_estimable_convergence` when it did not |
| `absolute_scale` | object | | the same contrasts on `thousand_steps`, keyed identically |
| `manski.by_group` | object | keyed by group slug; each an object with `lower` and `upper`, both `activity_days` bound nodes | per-group level bounds |
| `manski.primary_contrast_lower` | bound node | `activity_days` | lower bound: every missing day contributes zero deficit |
| `manski.primary_contrast_upper` | bound node | `activity_days` | upper bound: every missing day contributes a full deficit of 1 |
| `manski.display` | string | | the footer sentence, both contrast bounds in one string |
| `manski.crosses_zero` | boolean | | reported whether or not it is convenient. It will very likely be `true`. |
| `manski.computed_on` | string | | `"every eligible episode"`, never `"complete windows only"` |
| `delta_shift.scale` | string | | `"latent logit"`. The shift is on the model's own logit scale, in log-odds, not on the normalized-activity scale. |
| `delta_shift.applied_to` | string | | `"decompression only"` for the reported tipping point, which is the direction working against the study hypothesis |
| `delta_shift.tipping_point_point_estimate` | **bound node** | `dimensionless` | smallest `delta` at which the primary contrast's POINT ESTIMATE crosses zero. Read off the grid, so it has no interval |
| `delta_shift.tipping_point_interval` | **bound node** | `dimensionless` | smallest `delta` at which the 95% CI FIRST INCLUDES zero. Also read off the grid, and the interval in its name is the contrast's, not its own |
| `delta_shift.definition_display` | string | | one sentence naming what is shifted, on what scale, and to which group |
| `delta_shift.grid` | array of object | `{delta, applied_to, contrast_est, contrast_lo, contrast_hi, implied_deficit_at_reference}` | the shift curve, one entry per `delta` and application pattern |
| `delta_shift.applications` | array of string | `["fusion only", "decompression only", "both groups"]` |
| `delta_shift.reference_deficit` | scalar node | `normalized_activity` | the observed-equivalent deficit against which each `delta` is translated, fixed at `0.30` |
| `delta_shift.grid_extended` | boolean | | `true` when the prespecified extension past `delta = 2.0` was used |
| `delta_shift.crossed_within_grid` | boolean | | the **point estimate's** flag, and its alone. `false` means the primary contrast's point estimate reaches no tipping point within the prespecified range, which extends to `delta = 4.0`. That is a stronger result, not a failure. |
| `delta_shift.interval_crossed_within_grid` | boolean | | the **interval's** flag, and its alone: `false` means the 95% band never first includes zero within the same range. The two are computed and reported separately, per node, and either may be `false` while the other is `true` |
| `delta_shift.no_crossing_display` | string or `null` | | the sentence printed when either flag is `false`; `null` only when both crossed |

A **bound node** is an estimate node with `lo` and `hi` equal to `est` and `display_ci` empty: a
Manski bound is a bound, not an interval, and giving it interval keys would invite a renderer to
print it as a confidence interval.

**Five nodes are bound nodes and they are the only ones**: `manski.primary_contrast_lower`,
`manski.primary_contrast_upper`, `delta_shift.tipping_point_point_estimate`,
`delta_shift.tipping_point_interval` and `sensitivity.delta_shift_tipping_point.estimate`. The
fifth is the fourth pair's own number arriving in the ladder: 3.6's tipping-point row carries the
**same** coordinate as `delta_shift.tipping_point_point_estimate`, so a document that called it a
bound in one block and an estimate in the other would be declaring two shapes for one value, and
9.1 writes it as a bound in both. This count said four for one version while the worked example
already wrote five; the example was right, and the modules followed the example. The two tipping
points join the two Manski bounds for the same reason and it is worth stating rather than
inferring, because an earlier draft of this document declared them estimate nodes and a renderer
reading that draft would have drawn a confidence interval around each.

**A tipping point is a grid coordinate.** It is the smallest
`delta` in `delta_shift.grid` at which a stated condition first holds, so it takes one of the seven
prespecified grid values of `ANALYSIS-PLAN.md` section 3.11, or one of the extended values, and
nothing between them and nothing around them. Repeating the point estimate in `lo` and `hi` is
therefore not a loss of information; it is the whole of the information, and `display_ci` is empty
because there is no interval to print. The second node's name says `interval` because the condition
it reads off the grid is about the **contrast's** interval, the first `delta` at which the 95%
confidence band includes zero. That is a different question from the first node's, not an interval
around the first node's answer, and the two are one row apart in the Table 2 footer where a reader
is most likely to conflate them.

**When a coordinate never crosses, its own node is suppressed with a reason of its own, and the
other node is untouched.** Each tipping point has a flag of its own, `crossed_within_grid` for
the point estimate and `interval_crossed_within_grid` for the interval, and a node is suppressed
on its own flag alone. A `false` flag means the condition its own node reads off the grid never
holds out to the end of the prespecified extension at `delta = 4.0`: the point estimate never
crosses zero, or the 95% band never comes to include it. Either way that is the **stronger**
result, because no amount of unmeasured-day pessimism inside the prespecified range overturns the
finding. That node is then a suppressed node carrying `"reason": "no_crossing_within_range"` and
the sentence 7.5 gives it, and `no_crossing_display` carries the same sentence so a footer row has
a string to print. Before that reason existed both nodes carried `not_estimable_data_unavailable`,
which says the data were not there, and the data were there: the analysis ran, over the full
grid, and returned an answer that the vocabulary had no word for. A reason slug that reports a
good result as a missing one is a reporting defect and not a formatting one.

**One flag cannot answer for both, and a real run is the proof.** `05_analysis_drd.py` returns
the two flags separately and says in terms that the second "can fail to cross when the first one
crossed"; the reverse happens too, and a run of this study produced `crossed_within_grid = false`
beside `interval_crossed_within_grid = true` with a genuine grid coordinate at `delta = 3.5`. A
contrast whose point estimate holds its sign across the whole range can still have its confidence
band first include zero somewhere in it, and that delta is a computed, reportable coordinate.
Until this version 3.5 suppressed both nodes off `crossed_within_grid` alone, which would have
thrown that coordinate away and printed a no-crossing sentence over a number the analysis had.
The exporter already decides per node and cross-checks the flag against the value, halting when
a node carries a coordinate its own flag says does not exist; this section now declares the key
that decision reads.
| `model_fit.family` | string | | `"ordered beta"` |
| `model_fit.link` | string | | `"logit"` |
| `model_fit.spline_basis` | string | | `"restricted cubic on post-discharge day"`, verbatim from `ANALYSIS-PLAN.md` section 3.6. **Restricted**, not natural, and in **post-discharge** day, not postoperative day: the two differ by the length of stay, which is the confounded quantity of the plan's section 5.1 |
| `model_fit.spline_df` | scalar node | | |
| `model_fit.residual_correlation` | string | | `"continuous-time AR(1)"`, because an index-lagged AR(1) is wrong with irregular missing days |
| `model_fit.rho` | estimate node | `dimensionless` | |
| `model_fit.icc` | estimate node | `dimensionless` | |
| `model_fit.marginal_r2` | estimate node | `dimensionless` | |
| `model_fit.conditional_r2` | estimate node | `dimensionless` | |
| `model_fit.aic` | scalar node | `information_criterion` | |
| `model_fit.n_person_days` | count node | person-days | |
| `model_fit.n_persons` | count node | episodes | |
| `model_fit.converged` | boolean | | `false` invalidates every estimate above and forces a fallback rung |
| `model_fit.monte_carlo_draws` | scalar node | | random effects are marginalized by Monte Carlo, never set to zero, because the deficit function is convex |

Contrast slugs, in Figure 3 block 1 order: `fusion_vs_decompression` (primary), `lumbar_vs_cervical`,
`region_by_fusion_interaction`, `fusion_vs_decompression_cervical`, `fusion_vs_decompression_lumbar`.
`unadjusted_contrasts` is keyed by **the same five slugs and no others**, so a consumer holding a
contrast slug can reach both estimates without a second vocabulary.

**`unadjusted_contrasts` exists because STROBE item 16(a) asks for a quantity nothing else in this
bundle carried.** Item 16(a) requires unadjusted estimates beside confounder-adjusted ones, and it
requires them of the **contrast**. Before 1.9.0 the only unadjusted number here was
`by_group[i].unadjusted_debt`, which is an absolute **level** by direct summation over complete
windows against its own denominator. Differencing two of those medians does not give the unadjusted
contrast and is not meant to: the two medians rest on two different subsets, the direct sum is a
different estimator from model-and-integrate, and the difference of two group medians is not the
standardized difference the estimand is defined as. A checklist built against the bundle found this
and was right that it needed a re-export rather than a rewrite.

**"Unadjusted" here means one thing and the document says which, because the word has two habitual
meanings and both of the wrong ones are available.** The unadjusted contrast is the **same
model-and-integrate estimator of `ANALYSIS-PLAN.md` 3.2 and 3.8, refitted with the locked covariate
table of that plan's 3.6 deleted from the mean structure and nothing else changed**. Removed: age,
sex assigned at birth, body mass index and its missing indicator, comorbidity burden and its missing
indicator, `log(1 + LOS)`, index year, the COVID-19 disruption indicator, and device family. **Kept,
and kept deliberately**: the restricted cubic spline in post-discharge day, the procedure-group terms
and their day interactions, the region terms the collapse level admits, and the day-of-week fixed
effect. Those are not confounders held fixed. They are the axes the g-computation of 3.8 integrates
over, day of week is there twice over by 3.6 and 5.5, and at the four-group collapse level deleting
region would delete the groups the contrast is between. Removing them would produce a different
estimand rather than an unadjusted version of this one. **The observation weights of 3.7 are the
primary analysis's own and are not refitted**, so exactly one thing differs between the two contrasts
and a reader may read the gap between them as what the covariates moved.

**`absolute_scale` has no unadjusted twin, and the reason is the definition rather than the effort.** The absolute-scale companion is the same contrast re-expressed in thousand steps lost, and `ANALYSIS-PLAN.md` 3.9 requires its model to carry a spline in log baseline steps: multiplying a baseline-independent fitted deficit by the episode's own baseline would impose the assumption that the deficit does not depend on the baseline, which the data can test and the plan refuses to assume. A covariate-free version of that model would therefore have to keep a covariate, and would not be "the same estimator with the covariate set removed" but a third thing with no clean description. Item 16(a) is answered on the scale the estimand is defined on, `activity_days`, and this document says so here rather than leaving the absence to look like an oversight.

**It carries its own interval, its own n and its own rung.** The person-clustered bootstrap of 3.8
refits the covariate-free model inside every resample under the same seed convention, so the interval
accounts for the unadjusted model being estimated rather than known, exactly as the adjusted one
does. A resample is kept for the unadjusted contrast only when its own unadjusted ladder walk reached
the rung the unadjusted **point estimate** reached; a resample that did not contributes nothing, and
`percentile_interval` then refuses the interval on the same complementary share of the same attempted
count that trigger T4 of 3.5 is written on. No second threshold is invented for it. A covariate-free
design is a different optimization problem and may reach a different rung of the 3.1.1 ladder from
the adjusted fit; `rung_matches_adjusted` reports that rather than hiding it, because when the rungs
differ the gap between the two contrasts carries a change of model family as well as a change of
covariate set, and a reader has to be told before reading it as the covariates.

**Suppression is the ordinary suppression and nothing about this quantity is exempt.** Each
`unadjusted_contrasts[slug].estimate` is an estimate node whose disclosability follows its own
`n_compared` against the floor of section 2.4 and 10.1, so it is suppressed with
`contributing_n_below_threshold` when the count behind it does not clear the floor, and with
`not_estimable_convergence` when the fit or its interval did not come back. A fit that failed
entirely leaves `unadjusted_contrasts` empty, `unadjusted_model.rung_slug` `null` and
`unadjusted_model.not_estimable_reason` set to a slug of 7.5, and the exporter prints that sentence
where the estimate would sit. The failure never propagates: a guideline-mandated companion that could
suppress or unseat the prespecified estimand beside it would be a worse defect than the gap it
closes.

**Where it prints, and why not in the two obvious places.** It prints in
`tables-csv/table2_adjusted_debt_footer.csv` (5.3), as three new footer rows, and in Methods and
Results prose. It does **not** print in `tables-csv/table2_adjusted_debt.csv` and it does **not**
print in `figures-csv/figure3_forest.csv`, and both absences are decisions rather than omissions.
`ANALYSIS-PLAN.md` 9.2 puts **adjusted absolute levels** in Table 2's body and contrasts in Figure 3,
5.2 has `verify.py` enforce that split on this file by asserting that no contrast slug appears in it,
and an unadjusted contrast is a contrast. Figure 3 is where a contrast belongs, and it is closed to
this one at both blocks: block 2's row set is the fourteen plotted sensitivity rows that `verify.py`
asserts **set equality** against `ANALYSIS-PLAN.md` section 6, so a fifteenth row there is an
amendment to a locked prespecification and not this contract's to make; and block 1 would need five
new contrast slugs and five new 7.3 labels for what are not new contrasts, and would have to decide
whether the unadjusted primary row carries `is_primary`, where 4.3 permits exactly one `true` in the
whole file and either answer is wrong. **The Table 2 footer is neither a body row nor a forest row
and it already carries a contrast-scale quantity**: row 9 is `debt.manski.display`, the
assumption-free bounds on this same primary contrast. The footer's shape is `Footer item`, `Value`
and `Source key` with no `slug`, no `axis` and no `is_primary` column, so nothing printed there can
trip the split the body and the forest are held to, and the footer is already where facts *about* the
primary estimate live rather than where levels are tabulated. The three rows are **appended** at 13,
14 and 15 rather than inserted beside row 9, so that every existing `row_order` is unchanged for a
module and a fixture this document does not own.

**It is not prespecified and this document will not let that be forgotten.**
`ANALYSIS-PLAN.md` is locked at version 1.5 and carries no unadjusted contrast for Arm B anywhere: it
prespecifies an **unadjusted association** for the other arm at 4.8, an unadjusted absolute **level**
for this one at 9.2, and a `complete_window_direct_regression` sensitivity row at section 6 that is a
different estimator and is itself regressed **on the covariate set**. Adding an estimand to a locked
prespecification is an amendment under that file's own section 13 and a re-lock, which is not a
decision a downstream module or this contract may take. So the quantity is emitted with
`prespecified: false` and a sentence naming the item that requires it, `11.1` obliges
`manuscript.py` to print it as guideline-mandated rather than as planned, and if the plan is ever
amended to prespecify it, that boolean is the one edit that has to move.

### 3.6 `sensitivity`

An object keyed by slug. Key order in the file is alphabetical because of `sort_keys`; **ladder order
is carried by the `order` integer**, which matches the ten-row ladder in `ANALYSIS-PLAN.md` section 6
and, after flattening, the `row_order` in Figure 3 block 2. A consumer sorts by
`(order, sub_order)`, never by key.

Two of the plan's ten ladder rows expand into several plotted rows: row 6, wear thresholds, becomes
one row per valid-wear-day definition S1 to S4, and row 7, baseline windows, becomes one row per
alternate window. `order` carries the plan's ladder number and `sub_order` carries the position
within it, so the plan's fixed order survives the expansion and cannot be rearranged to put a
reassuring row at the top.

| Key | Type | Notes |
|---|---|---|
| `sensitivity[slug].order` | integer | the plan's ladder row, `1` to `10` |
| `sensitivity[slug].sub_order` | integer | position within an expanded ladder row; `1` where the row does not expand |
| `sensitivity[slug].display_label` | string | label table 7.8 |
| `sensitivity[slug].estimate` | estimate node, except one | usually `activity_days`. **`delta_shift_tipping_point` is the exception: it is a `dimensionless` bound node**, the fifth and last of 3.5's five, because it carries the same grid coordinate as `debt.delta_shift.tipping_point_point_estimate` and a coordinate has no interval. It is the only row of this block whose `display_ci` is empty by rule rather than by outcome |
| `sensitivity[slug].pvalue` | pvalue node or `null` | `null` where a P value is not defined for the row |
| `sensitivity[slug].n` | count node | episodes contributing to the row |
| `sensitivity[slug].estimable` | boolean | `false` when the row could not be fitted |
| `sensitivity[slug].not_estimable_reason` | string or `null` | suppression-reason slug from 7.5 |
| `sensitivity[slug].axis` | string | `"primary"` when the row is on the primary contrast scale; otherwise a named alternative axis |
| `sensitivity[slug].render` | string | `"marker"`, `"panel"` or `"text"`. A row not on the primary axis never renders as a marker on the shared scale. The delta-shift row renders as `"panel"`, because a tipping curve is not a point estimate with an interval and plotting it as one would misrepresent it. |
| `sensitivity[slug].varies` | string | the one thing this row changes from the primary, printed in the supplement table |
| `sensitivity[slug].direction_matches_primary` | boolean | convenience for the Results sentence that says how many rows agreed |

Slugs, transcribed from `ANALYSIS-PLAN.md` section 6. The plan owns the list; `verify.py` asserts
set equality between the plan, this block and Figure 3 block 2. Fourteen plotted rows from ten
ladder rows.

| order | sub | slug | axis | render |
|---|---|---|---|---|
| 1 | 1 | `pod_anchored_window` | primary | marker |
| 2 | 1 | `inpatient_days_censored` | primary | marker |
| 3 | 1 | `complete_window_direct_regression` | primary | marker |
| 4 | 1 | `observation_weighted` | primary | marker |
| 5 | 1 | `delta_shift_tipping_point` | `latent_logit_shift` | panel |
| 6 | 1 | `wear_definition_s1` | primary | marker |
| 6 | 2 | `wear_definition_s2` | primary | marker |
| 6 | 3 | `wear_definition_s3` | primary | marker |
| 6 | 4 | `wear_definition_s4` | primary | marker |
| 7 | 1 | `baseline_window_60_15` | primary | marker |
| 7 | 2 | `baseline_window_30_1` | primary | marker |
| 8 | 1 | `device_change_excluded` | primary | marker |
| 9 | 1 | `baseline_floor` | primary | marker |
| 10 | 1 | `debt_untruncated` | primary | marker |

The primary valid-wear-day rule is 600 heart-rate minutes, so no ladder row restates it. S1 is 40%
daily heart-rate adherence, S2 is 10 hours of wear plus at least 100 steps, S3 is 8 hours, S4 is 12
hours; the definitions live in `ANALYSIS-PLAN.md` section 2.1 and their display labels in section
7.8 below.

**The ten supplementary rows, and what they are excluded from.** `ANALYSIS-PLAN.md` section 6
carries a second table of Arm B rows that are reported in the supplement and are **not** plotted on
the Figure 3 ladder. They carry slugs so a supplementary exhibit can name one without inventing one.
They are transcribed here so that `verify.py` can be written against an explicit list rather than
inferring one, and so that a reader of this contract does not meet a slug in the supplement that
appears nowhere in the interface:

| slug | display label |
|---|---|
| `baseline_steps_adjusted` | Baseline steps adjusted |
| `bmi_multiply_imputed` | Body mass index multiply imputed |
| `weights_without_lagged_wear` | Observation weights without lagged wear |
| `junctions_mirrored` | Junction codes mirrored |
| `cervical_fusion_gap_reclassified` | Cervical fusion gap reclassified |
| `cervical_decompression_gap_stated` | Cervical decompression gap |
| `four_group_model` | Four-group model |
| `truncated_assigned_max_debt` | Truncated windows at maximal debt |
| `fusion_status_non_add_on_only` | Fusion status without add-on codes |
| `baseline_weekday_weekend_split` | Separate weekday and weekend baselines |

**These ten supplementary rows are NOT members of the set `verify.py` asserts equality over.** The set-equality
assertion runs over the **fourteen plotted rows** above and nothing else: the keys of
`results.json.sensitivity`, the slug column of Figure 3 block 2, and the fourteen-row table in
`ANALYSIS-PLAN.md` section 6 must be the same set of fourteen. A supplementary slug appearing among
those fourteen is a failure, and so is a plotted slug missing from them. The ten supplementary rows
have no entry in `results.json.sensitivity`, no row in `figure3_forest.csv`, and no home in this
bundle at all; they live in the supplement, which is outside this contract's exhibit set. Among
them, `truncated_assigned_max_debt` is the row step 15 of the attrition ladder refers to; it had
no slug before the plan gave it one, which is why an earlier draft of this contract described it in
prose and left a printed string with nothing to look up.

**The ninth row, `fusion_status_non_add_on_only`, arrives with version 1.2 of the plan and is
transcribed here at contract version 1.4.0.** It reports fusion status computed from non-add-on
records only, which is the reading of the fusion-status rule that `ANALYSIS-PLAN.md` section 2.4
declines: the plan's fusion status reads all qualifying evidence, add-on and instrumentation codes
included, so an episode whose only fusion evidence is an add-on code is classified fusion in the
primary and decompression in this row. The row exists to bound how much of the primary contrast
rests on those episodes. If the two readings give the same contrast the classification rule is not
load-bearing and a reader can stop weighing it; if they diverge, the size of the divergence is a
printed number rather than an argument. That is the move the plan already makes with the delta-shift
tipping point of its 3.11 and the Manski bounds of its 3.12: a judgment call is converted into a
reported number, and the reader is handed the number. Like the eight rows above it, this row is
**not** a member of the fourteen-row set the set-equality assertion runs over, it is not plotted on
the Figure 3 ladder, and it has no key anywhere in this bundle. The fourteen plotted rows did not
move in the amendment, in membership or in order, so the assertion itself is untouched by it.

**The tenth row, `baseline_weekday_weekend_split`, arrives with version 1.3 of the plan and is
transcribed here at contract version 1.5.0.** It re-estimates the primary contrast with each day's
deficit taken against the baseline of its own day type, weekday or weekend, which is the
split-baseline sensitivity the protocol's own baseline section asks for and plan versions 1.0 through
1.2 held no slug for in either set. The plan's section 2.2 now specifies it in full and its section 6
argues, rather than assumes, why it is supplementary and not a fifteenth plotted row. That argument
is worth transcribing, because it is the line the two sets are drawn along and this contract's
set-equality assertion is what enforces it: **every one of the fourteen plotted rows tests a choice
the primary makes with no other protection**, the wear rule, the window anchor, the truncation, the
estimator, the weights, the baseline window. Day of week is not such a choice. It is already handled
twice inside the primary, as a 7-level fixed effect in the mean structure and by g-computation over
each episode's own calendar alignment. The split baseline asks the narrower question of whether the
**denominator** needs the protection the numerator already has, and a row that corroborates an
existing handling belongs in the supplement while a row that tests an unhedged choice belongs on the
plotted ladder. Like the nine rows above it, this row is **not** a member of the fourteen-row set the
set-equality assertion runs over, it is not plotted on the Figure 3 ladder, and it has no key anywhere
in this bundle. The fourteen plotted rows are byte-identical across the version 1.3 amendment, in
membership, order and display label alike, so the assertion itself is untouched by it.

### 3.7 `gate`

| Key | Type | Notes |
|---|---|---|
| `stages` | array of object | six entries, letters A to F, in that order |
| `stages[i].letter` | string | `"A"` to `"F"` |
| `stages[i].slug` | string | e.g. `"stage_a_qualifying_episodes"` |
| `stages[i].display_label` | string | label table 7.9, printed in Table 3 part A |
| `stages[i].definition_display` | string | the required count, verbatim from the protocol table |
| `stages[i].unit` | string | `"episodes"` or `"events"` |
| `stages[i].total` | count node | may be suppressed |
| `stages[i].by_group` | object or `null` | keyed by group slug, each a count node; `null` where the stage is not stratified |
| `stages[i].components` | object or `null` | for stage D only: `first_ed_visits`, `readmissions`, `composite`, each a count node |
| `tier.index` | integer | `1` to `4`, matching `ANALYSIS-PLAN.md` section 1.2. Tier 1 is the largest event count. |
| `tier.slug` | string | `"full_model"`, `"step_first_exploratory"`, `"event_centered_only"` or `"no_early_warning"` |
| `tier.display_label` | string | label table 7.10 |
| `tier.events_lower` | integer or `null` | lower bound of the tier band |
| `tier.events_upper` | integer or `null` | upper bound, `null` for the open top tier |
| `tier.determined_by` | string | always stage E: unique first acute-care events with a computable proximal step ratio |
| `tier.event_count_printable` | boolean | `false` when the deciding count is itself below the floor |
| `tier.permitted_analysis_verbatim` | string | quoted, unaltered, from the plan's decision table |
| `tier.permitted_claim_verbatim` | string | quoted, unaltered, from the plan's decision table |
| `tier.exhibit_set` | string | `"primary"` at tiers 3 and 4; `"alternate"` at tiers 1 and 2, where the plan switches the whole exhibit set. `verify.py` refuses `"alternate"` for schema 1.x and that refusal is a **stated, dated obligation**: see 11.4 |
| `arm_a.permitted` | boolean | `false` at `no_early_warning` |
| `arm_a.reason_display` | string | why part B carries no estimate, printed instead of a blank table |
| `arm_a.estimates` | object | `{}` when `permitted` is `false`; otherwise the keys below, each present or suppressed but never absent |
| `arm_a.estimates.adjusted_odds_per_lower_step_ratio` | estimate node, `odds_ratio` | per prespecified decrement in the proximal step ratio |
| `arm_a.estimates.unadjusted_odds_per_lower_step_ratio` | estimate node, `odds_ratio` | the same contrast with no covariates, which is the one association the 20-to-49 tier permits |
| `arm_a.estimates.odds_of_no_computable_step_signal` | estimate node, `odds_ratio` | the co-primary exposure's own odds, `beta_N` of `ANALYSIS-PLAN.md` 4.4 |
| `arm_a.estimates.negative_control_window` | estimate node, `odds_ratio` | the day 14 to 8 pre-event control window |
| `arm_a.estimates.median_lead_time` | quantile node, `hours` | |
| `arm_a.estimates.matched_set_size` | quantile node, `count` | distribution of controls per case |
| `arm_a.estimates.absolute_risk_translation` | **estimate node**, `absolute_risk_percent` | absolute risk before relative, per house numeral style. Not a percentage node: see below |
| `arm_a.estimates.collider_rate_with_signal` | estimate node, `rate_per_1000_episode_days` | crude event rate on episode-days whose landmark window is computable |
| `arm_a.estimates.collider_rate_without_signal` | estimate node, `rate_per_1000_episode_days` | crude event rate on episode-days whose landmark window is not |
| `arm_a.estimates.collider_rate_ratio_crude` | estimate node, `rate_ratio` | without over with, crude |
| `arm_a.estimates.collider_rate_with_signal_standardized` | estimate node, `rate_per_1000_episode_days` | the same rate, directly standardized to the recovery day bands of `ANALYSIS-PLAN.md` 4.4 |
| `arm_a.estimates.collider_rate_without_signal_standardized` | estimate node, `rate_per_1000_episode_days` | the same, for the windows whose landmark is not computable |
| `arm_a.estimates.collider_rate_ratio_standardized` | estimate node, `rate_ratio` | the same ratio, directly standardized to the recovery day bands of `ANALYSIS-PLAN.md` 4.4 |

**Six collider keys and not four, one per rate cell of Table 4.** 5.7 gives that file three rows
by two rate columns, which is six rate cells, and until this version 3.7 declared four keys: the
two crude rates and the two ratios. The **standardized rate of each window group** had no key,
so two printed cells traced to nothing, and `06_analysis_gate.py`'s `build_gate_block()` refuses
any key this section does not declare, which meant the gate could not supply them either and the
exporter halted at any tier that permits the comparison. `ANALYSIS-PLAN.md` 4.4 requires the
per-group figure and not only the ratio: it judges the two conditions **separately**, so "one may
be standardized while the other is withheld, and the exhibit shows exactly that". Two conditions
judged separately need two cells and therefore two keys. The two window-group **count** cells of
5.7 are counts and not estimates, do not belong in a block named `estimates`, and are supplied to
the exporter beside the gate block; 11.4 carries the decision about which block should own them.

**`absolute_risk_translation` is an estimate node and not a percentage node, and the fix is the one
`share_reaching_80pct_baseline` already had.** A percentage node requires `num` and `den`, because
its whole contract is that a reader can reproduce the percentage from the two rounded counts
printed beside it. A model-predicted absolute risk is a fitted probability out of a conditional
logistic model evaluated at a prespecified step ratio. There is no numerator: no set of people was
counted to produce it, and inventing a `num` and a `den` for it would publish two numbers that
describe nothing and that a careful reader would then divide. It is an estimate with a confidence
interval, on the percent scale, and its disclosability follows the count of events contributing to
the fit rather than a count of its own. That is exactly the shape 3.5 gives
`share_reaching_80pct_baseline`, for exactly the same reason, and the two are the only two nodes in
this bundle on the percent scale that carry an interval. **No percentage node in this bundle holds
a fitted value.** The remaining percentage nodes are `debt.by_group[i].share_zero_debt`,
`meta.estimator.bootstrap_failure_rate`, the `share_of_step_dropped`, `share_valid_wear` and
`share_of_sets` columns of 5.6, and the `n (%)` cells of Table 1, and every one of them is a
counted numerator over a counted denominator.

**Which keys the tier produces, so a consumer knows what an absent estimate means.** The tier does
not merely gate `arm_a.permitted`; inside a permitted arm it decides which queries are submitted at
all, and a key the tier does not permit carries the `not_permitted_by_tier` sentence of 7.5 rather
than vanishing.

| Tier | `arm_a.permitted` | Estimate keys produced | Keys carrying `not_permitted_by_tier` |
|---|---|---|---|
| 4, fewer than 20 | `false` | none. `estimates` is `{}` | the whole arm, through `arm_a.reason_display` |
| 3, 20 to 49 | `true` | `matched_set_size`, `unadjusted_odds_per_lower_step_ratio`, `odds_of_no_computable_step_signal`, and the six collider keys | `adjusted_odds_per_lower_step_ratio`, `negative_control_window`, `median_lead_time`, `absolute_risk_translation` |
| 2, 50 to 99 | `true` | all but `median_lead_time` | `median_lead_time` |
| 1, 100 or more | `true` | all | none |

**Tier 3 is the likeliest tier this study reaches and it used to carry no number at all.** Before
this version the block at tier 3 produced `matched_set_size` and five refusals, so Table 3 part B
printed a set-size distribution and four sentences saying what could not be estimated, which reads
as a failed analysis rather than as the analysis the plan prescribes at that tier. The plan's own
tier 3 row permits "event-centered association and visualization", and the three keys added here
are that association: the unadjusted contrast, the co-primary exposure's own odds, and the collider
comparison, none of which needs an adjusted model. The event-centered visualization is section
4.4's exhibit, which for the same reason exists at this tier and is not reachable only through
the alternate set; 1.8.0 prints it in the supplement rather than as a fourth main-text figure,
which changes the page it appears on and not whether the tier can produce it.

**`event_count_printable` is the coincidence worth naming.** The lowest tier's boundary is 20 usable
events and the disclosure floor is also 20, in the exact sense of `ANALYSIS-PLAN.md` section 1.3: the
two thresholds are unrelated in origin and identical in value. They do not coincide exactly, and the
one-count gap is the interesting case. A gate of 20 events sits in **tier 3**, where event-centered
association is permitted, and simultaneously at the top of the suppressed band, where the count may
not be disclosed: the analysis runs and its denominator does not appear. Below 20 events the tier is
4 and no early-warning analysis is attempted. `event_count_printable` is `false` in both cases, so it
is `false` whenever `stages[E].total.n` would be 20 or fewer, and it is not a synonym for
`tier.slug == "no_early_warning"`. When it is `false`, `stages[E].total` is a suppressed node whose
`display` reads "20 or fewer, suppressed per All of Us dissemination policy", and Methods states that
the tier boundary and the disclosure floor share a value rather than letting a reader wonder why the
number is missing.

**Not permitted is not the same as suppressed.** A key absent because the tier forbids the analysis
is recorded in `arm_a.permitted: false` with a printed reason. A key present but hidden for cell size
is recorded in `suppressed`. Both print. Neither vanishes.

### 3.8 `figures` and `tables`

`tables` matches the house shape exactly, so `load_table()` from
`NSQIP/projects/opioid-shoulder-arthroscopy/v2/pipeline/03_figures.py` works unmodified.

| Key | Type | Notes |
|---|---|---|
| `tables[key].file` | string | path relative to `v1/results/` |
| `tables[key].columns` | array of string | exact header strings, in file order |
| `tables[key].key_columns` | array of string | the columns `load_table` sets as the index |
| `tables[key].rows` | integer | data rows, excluding the header |
| `tables[key].exhibit` | string | the printed exhibit this block IS, `"Table 1"` to `"Table 4"`, character-identical to the `exhibit` column of this file's `MANIFEST.csv` row (8.3). Two blocks may name the same exhibit and two do |
| `tables[key].exhibit_set` | string | `"primary"` or `"supplementary"`. See the exhibit budget below |
| `tables[key].denominator` | string | a key in `denominators` |
| `tables[key].n` | integer | that denominator's `n`, duplicated so a caption needs one lookup |
| `tables[key].md5` | string | duplicated from `MANIFEST.csv`, so a consumer can check without parsing the manifest |
| `tables[key].legend` | string | the full printed legend, house prose rules apply |
| `tables[key].footer_file` | string or `null` | the companion footer CSV, where one exists |

`tables` keys: `table1`, `table2`, `table3a`, `table3b`, `table4`. **Five keys, six files.** The
Table 2 footer is not its own exhibit, so it has no `tables` key; it is reached through
`tables.table2.footer_file` and it still gets its own `MANIFEST.csv` row and its own md5. The
arithmetic that follows from this is worth writing down because it is the kind of off-by-one a
consumer will otherwise assert wrongly:

```
MANIFEST.csv data rows = 1 (results.json) + 4 (figure files) + 6 (table files)
                                          + 5 (ledger files, section 5.6)      = 16
len(results.json["figures"]) = 4      # BLOCKS, not exhibits: 3 primary + 1 supplementary
len(results.json["tables"])  = 5      # BLOCKS, not exhibits: Table 3 is two of them
# there is no results.json["ledgers"]: the ledgers are manifest-stamped and path-addressed

# the exhibit budget, counted over DISTINCT `exhibit` values among the PRIMARY blocks
primary figures = |{"Figure 1", "Figure 2", "Figure 3"}|                       = 3
primary tables  = |{"Table 1", "Table 2", "Table 3"}|                          = 3
supplementary   = figures.figure4 ("Figure 4"), tables.table4 ("Table 4")
```

`meta.manifest_rows` carries the 16, and `verify.py` checks it against the file rather than deriving
it from the block sizes. The five ledger files deliberately have no `results.json` block: nothing in
the main text cites a number out of them, so giving them one would create a second place for a
ledger's row count to drift from the file.

`figures` uses the same shape plus figure-specific fields:

| Key | Type | Notes |
|---|---|---|
| `figures[key].file` | string | |
| `figures[key].exhibit` | string | the printed exhibit this block IS, `"Figure 1"` to `"Figure 4"`, character-identical to the `exhibit` column of this file's `MANIFEST.csv` row (8.3) |
| `figures[key].exhibit_set` | string | `"primary"` or `"supplementary"`. See the exhibit budget below |
| `figures[key].columns` | array of string | machine column names, in file order |
| `figures[key].sort_keys` | array of string | the columns the file is sorted by, ascending, in order |
| `figures[key].rows` | integer | |
| `figures[key].md5` | string | |
| `figures[key].denominator` | string | a key in `denominators` |
| `figures[key].n` | integer | |
| `figures[key].legend` | string | the full printed legend |
| `figures[key].plate_note` | string | the short denominator statement rendered onto the artwork itself |
| `figures.figure2.days_dropped_by_group` | object | group slug to integer: how many of the 90 days fell below the floor and are absent |
| `figures.figure2.last_day_by_group` | object | group slug to integer: the truncation day, the last day the series is plotted. Printed in the legend. |
| `figures.figure2.n_gaps_by_group` | object | group slug to integer: how many mid-series gaps the group has, which is the number of segments minus one |
| `figures.figure2.n_series` | integer | equals the number of procedure groups at the selected collapse level |
| `figures.figure3.blocks` | array of object | `{index, display_label, rows}` |
| `figures.figure4.n_series` | integer | always `2`: cases and matched controls |
| `figures.figure4.day_range` | array of two integer | `[-14, 7]`, the prespecified event-centered window of `ANALYSIS-PLAN.md` section 9.5, carried so a renderer fixes its axis before it reads a row |
| `figures.figure4.n_days_plotted_by_series` | object | series slug to integer: how many of the 22 offsets cleared the floor and carry a value |
| `figures.figure4.tier_permits_plot` | boolean | `false` at tier 4, where every measured cell in the file is `SUPPRESSED` |

`figures` keys: `figure1`, `figure2`, `figure3`, `figure4`.

**The exhibit budget, and this is the section that declares it.** `CLAUDE.md` section 2 rule 7
and section 6 fix the deliverable at **exactly 3 figures and 3 tables**, with everything beyond
them in a supplement, and `ANALYSIS-PLAN.md` section 9 owns the main-text exhibit list. This
document does not get to grow that set, and 11.3's last rule applies with no exception: where a
list here and a list in the plan disagree, the plan wins and this document is amended, never the
reverse and never at run time. `exhibit_set` is how the bundle carries that decision, so a
consumer can read the classification instead of inferring it from a count.

| `exhibit_set` | Blocks | Printed where |
|---|---|---|
| `"primary"` | `figures.figure1`, `figures.figure2`, `figures.figure3`, `tables.table1`, `tables.table2`, `tables.table3a`, `tables.table3b` | the main text: Figures 1 to 3, Tables 1 to 3 |
| `"supplementary"` | `figures.figure4`, `tables.table4` | the supplement |

**Count the exhibits, not the files and not the keys, and the two wrong counts are wrong
differently.** Counting bundle **files** gives 4 figure files and 6 table files, because this
bundle writes one CSV per printed thing: Table 2 has a separate footer file and Table 3 is two
parts. `CLAUDE.md` rule 7 already warns against that count. Counting **block keys** is the same
mistake one level in and it survives the first warning, which is why it is written out here:
`tables` carries **four** primary keys for **three** primary tables, because `table3a` and
`table3b` are the two parts of one exhibit and both name `"Table 3"`. So the budget is the count
of **distinct `exhibit` values among the blocks whose `exhibit_set` is `"primary"`**, which is 3
and 3, and it is computed rather than typed. 8.3's `exhibit` column already counts Table 3 once
for the same reason, and `figures[key].exhibit` and `tables[key].exhibit` are that column's
`results.json` twin: the exporter asserts the two agree, because a bundle whose manifest and
whose `results.json` name an exhibit differently tells two stories.

**A supplementary exhibit keeps its `results.json` block, and that is a decision rather than an
oversight.** The five `ledgers-csv/` files have no block, on the stated ground that nothing in the
main text cites a number out of them; that ground does not reach Figure 4 and Table 4, which
are **rendered**: they have legends, plate notes, denominators, declared column lists and row
counts that `verify.py` checks on arrival, and `figures.figure4` additionally carries
`day_range`, `n_series`, `n_days_plotted_by_series` and `tier_permits_plot`, which a renderer
needs before it reads a row. Moving them out of `figures` and `tables` would delete those checks
and that metadata for two files that are still drawn, and it would be a **rename** under 11.2,
which is a major bump and updates every consumer in the same commit. The blocks stay; they gain a
field saying which set they belong to. 5.6's phrase for the ledgers is the one that fits here
too, with the halves swapped: Figure 4 and Table 4 are **supplement-only in destination and
primary-grade in discipline**.

**The alternate exhibit set at tiers 1 and 2 is untouched by this.** `gate.tier.exhibit_set`
(3.7) is a different field answering a different question: it records which of the plan's two
exhibit **sets** the event count selected, and `verify.py` still refuses `"alternate"` for schema
1.x under 11.4's first open obligation. `exhibit_set` on an exhibit block records where a
**particular exhibit** is printed within the set in force. Under the alternate set 9.5 promotes
this curve to Figure 2 wholesale, and Figure 4's renderer in `local/figures.py` is still what
serves it; that promotion is 11.4's obligation to specify and is not what this field does.

### 3.9 `suppressed`

The explicit ledger of everything hidden. An empty array is legal and means nothing was suppressed.
Silent omission is the failure mode this block exists to make impossible.

| Key | Type | Notes |
|---|---|---|
| `entries[i].locus` | string | `"results.json"` or a CSV path |
| `entries[i].path` | string | dotted path into `results.json`, or empty for a CSV entry |
| `entries[i].file_row_key` | string or `null` | for a CSV entry, the value of the file's key columns, joined by `" / "` |
| `entries[i].column` | string or `null` | for a CSV entry, the suppressed column |
| `entries[i].kind` | string | `"count"`, `"percentage"`, `"estimate"`, `"quantile"`, `"row"` or `"series-point"` |
| `entries[i].reason` | string | slug from 7.5 |
| `entries[i].reason_display` | string | the printed sentence |
| `entries[i].rule` | string | which rule fired: `"R1 cell below floor"`, `"R1 secondary suppression"`, `"R1 contributing n below floor"`, `"tier"`, `"no crossing"` |
| `n_entries` | integer | equals `len(entries)` |
| `by_reason` | object | reason slug to integer count |
| `series_points_by_file` | object | file path to integer: how many series points are absent from the file entirely |

**`"no crossing"` is the one rule in that list that is not a disclosure event**, and it is here
because this block's job is to make a value-free node impossible to miss rather than to list
disclosure events specifically. A tipping point that never crosses (7.5,
`no_crossing_within_range`) produces a node with no number in it, exactly as a suppressed cell does,
and a consumer walking `suppressed.entries` to find every node it cannot call `value()` on has to
find that one too. It does not enter any `R1` tally and `verify.py` does not count it against the
floor. **A tier-driven absence is different again and is deliberately not here**, per 3.7: a key or
an exhibit the tier forbids is recorded in `gate.arm_a.permitted` and in
`figures.figure4.tier_permits_plot`, with a printed reason, and not as a suppression. The
`MANIFEST.csv` `n_suppressed_cells` column counts written tokens rather than reasons, so it still
counts those cells; the two are different questions and 8.3 answers the mechanical one.

A `series-point` entry is a Figure 2 day that is **absent from the file**. It is recorded here as an
aggregate count per group and per file, never as a list of individual days with their counts, because
a list of exactly which days fell below 20 is itself a per-day count pattern.

### 3.10 `checks`

The exporter's assertions, re-run locally. Each entry:

| Key | Type | Notes |
|---|---|---|
| `entries[i].slug` | string | |
| `entries[i].display` | string | one sentence stating what was asserted |
| `entries[i].passed` | boolean | |
| `entries[i].detail` | string | empty when passed |
| `entries[i].local_reassert` | boolean | `true` when the local side must run the same check |
| `n_checks`, `n_passed`, `n_failed` | integer | |
| `policy` | string | `"any failed check is a stop condition, not a warning"` |

Mandatory check slugs: `ladder_closes`, `no_cell_below_floor`, `no_hardcoded_floor`,
`no_identifier_column`, `no_date_column`, `no_near_unique_column`,
`percentages_from_rounded_counts`, `percentage_suppressed_with_count`,
`secondary_suppression_applied`, `no_em_dash`, `labels_match_contract`,
`csv_bytes_stable_across_two_runs`, `manifest_md5_matches`. Thirteen checks, and
`checks.n_checks` must equal thirteen; a run that reports fewer has skipped one.

---

## 4. The plot-ready aggregate CSVs

One file per figure. **Every row carries its own contributing n**, because the local side re-checks
suppression rather than trusting the exporter: `figures.py` refuses to plot any row whose
`n_contributing` is below `min_cell`, even though `safe_export()` already refused to write one.

Shared rules for every file under `figures-csv/`:

| Rule | Value |
|---|---|
| Column names | machine tokens, lower snake case. **Never printed.** See section 6. |
| Numeric cells | raw numbers, not display strings. Floats written with `float_format="%.6g"`, the value `disclosure.FLOAT_FORMAT` pins. Integers written without a decimal point. **Every statistic is rounded to its unit's decimals (2.4) before the frame is built**, not on the way to the renderer: the near-unique class of 10.2 is computed on the in-memory float, so an unrounded column is refused whatever `%.6g` would have printed. |
| Suppressed cell | the literal token `SUPPRESSED`. Never blank, never `0`, never `NA`. |
| Not-applicable cell | the empty string. Distinguished from `SUPPRESSED` on purpose: blank means the concept does not apply to this row, `SUPPRESSED` means it applies and is hidden. |
| Missing value | does not occur. A row with an unknown value is not written. |
| Row order | fixed by the `sort_keys` in `figures[key].sort_keys`, ascending, so bytes are stable |
| Boolean cells | the strings `true` and `false`, lower case, never `TRUE` or `1` |

### 4.1 `figures-csv/figure1_strobe_ladder.csv`

**Nineteen rows, one per attrition rung**, in the order of `ANALYSIS-PLAN.md` section 2.6. Must
reconcile row for row with `results.json.attrition.rungs`: `verify.py` asserts equality of `slug`,
`step`, and every disclosed count, and asserts set equality of the `slug` column against the plan.

| Column | Type | Unit | Suppression | Example |
|---|---|---|---|---|
| `step` | integer | ordinal, 1 to 19 | never | `11` |
| `slug` | string | | never | `excl_no_wearable_data` |
| `display_label` | string | | never | `Wearable-linked spine episodes` |
| `kind` | string | | never | `exclusion` |
| `unit` | string | | never | `episodes` |
| `n_in` | integer | count | `SUPPRESSED` if below floor | `6880` |
| `n_dropped` | integer | count | `SUPPRESSED` if below floor; empty when `kind` is not `exclusion` | `5720` |
| `n_out` | integer | count | `SUPPRESSED` if below floor | `1160` |
| `n_carried_forward` | integer | count, persons | `SUPPRESSED` if below floor; **empty on every row but step 2** | `` |
| `reason` | string | | never; empty on a `terminal` rung | `excl_no_wearable_data` |
| `reason_display` | string | | never; empty on a `terminal` rung | `No Fitbit activity record linked to the participant` |
| `closes_exact` | boolean | | never | `true` |
| `box_side` | string | | never | `main` for the ladder spine, `exclusion` for the right-hand box |

Sort keys: `step`. Thirteen columns.

**Five of the thirteen are declared to `safe_export()` as specification columns, and four of them
never can be.** At nineteen rows this file is under the near-unique row floor and no column of it is
tested for cardinality at all. At twenty-one rows every one of `step`, `slug`, `display_label`,
`reason` and `reason_display` crosses the ninety percent ceiling, and `step` carries the
integer-key shape besides. All five are the rung vocabulary of `ANALYSIS-PLAN.md` section 2.6 and
are granted in the 10.2 whitelist, so `07_export.py` passes
`specification_columns=["step", "slug", "display_label", "reason", "reason_display"]` on this frame
and on no other figure. `kind`, `unit` and `box_side` meet the same criterion and are deliberately
**not** granted: each is a closed vocabulary of three, five and two values, so no ladder length
brings it near the ceiling, and an exemption a column cannot need is an over-broad grant.
`closes_exact` is not granted because whether a rung's arithmetic closed is a fact about the data
and fails the criterion outright. And `n_in`, `n_dropped`, `n_out` and `n_carried_forward` are
counts: they are floor-tested on their true values and gate-tested as rendered cells, no register in
this document reaches them, and at twenty-one rungs `n_in` and `n_out` refuse this file on their
own. 11.4 carries that as an obligation, because it is the thing a twentieth rung would set off.

`n_carried_forward` exists for one row and is empty on the other eighteen, which is the
not-applicable convention of the shared rules above and not a suppression. It is a column rather than
a footnote because the persons-unit closure assert of 3.3 cannot be evaluated from this file without
it, and `make_strobe.py` re-asserts closure from this file.

```csv
step,slug,display_label,kind,unit,n_in,n_dropped,n_out,n_carried_forward,reason,reason_display,closes_exact,box_side
2,episode_construction,Spine surgical episodes,conversion,persons to episodes,9720,180,10240,9540,unit_change,Same-day qualifying procedure records collapsed into one episode; operations on different dates stay separate episodes until step 13,true,exclusion
11,excl_no_wearable_data,Wearable-linked spine episodes,exclusion,episodes,6880,5720,1160,,excl_no_wearable_data,No Fitbit activity record linked to the participant,true,exclusion
18,excl_event_without_computable_landmark,Analyzable acute-care events,exclusion,events,40,SUPPRESSED,SUPPRESSED,,excl_event_without_computable_landmark,Event on post-discharge day 1 to 4 with no computable proximal window,true,exclusion
```

### 4.2 `figures-csv/figure2_daily_activity.csv`

Baseline-normalized daily activity by post-discharge day, day 1 to 90, one series per group at the
selected collapse level. **The series count is data-dependent**: four at `four_group`, two at
`two_group`, one at `single_group`. Read `figures.figure2.n_series` and `cohort.groups`; never
assume four.

| Column | Type | Unit | Suppression | Example |
|---|---|---|---|---|
| `group_slug` | string | | never | `lumbar_fusion` |
| `display_label` | string | | never | `Lumbar fusion` |
| `group_order` | integer | 1-based, the legend and colour order; the maximum is the number of series at the selected collapse level, which is 4 only at `four_group` | never | `4` |
| `day` | integer | post-discharge day, 1 to 90 | never | `12` |
| `n_contributing` | integer | episodes contributing that day, `round20`-rounded | never present below the floor: the ROW IS ABSENT | `80` |
| `observed_median` | float | `normalized_activity`, **two decimals** | never blank when the row exists | `0.41` |
| `observed_p25` | float | `normalized_activity` | | `0.22` |
| `observed_p75` | float | `normalized_activity` | | `0.64` |
| `fitted_marginal` | float | `normalized_activity` | | `0.43` |
| `fitted_lo` | float | `normalized_activity` | 95% marginal band, lower | `0.39` |
| `fitted_hi` | float | `normalized_activity` | 95% marginal band, upper | `0.47` |
| `in_accrual_window` | boolean | `true` for day 1 to 35 | never | `true` |
| `series_segment` | integer | 1-based, increments after every gap in that group's day sequence | never | `1` |

Sort keys: `group_order`, `day`.

**The absence rule, and it is absence, not a null.** A day whose true contributing count fails
`disclosable()` is **not written to the file at all**. There is no row, no `SUPPRESSED` token
and no null. The threshold is applied to the true count inside the perimeter; the `n_contributing`
that survives to the file is the rounded value, so a row reading `n_contributing = 20` stands on a
true count of **21 to 29**, never on 20 and never on 30: `round20(20)` suppresses and `round20(30)`
is 40 (`ANALYSIS-PLAN.md` section 8 rule 2).

Consequence for the renderer, which is the whole point of the rule: the line and the ribbon are drawn
only where data exists, so a thin tail truncates instead of wandering. Nothing is plotted thin, and
the median of three people never reaches the artwork. Medians and quartiles fall under the same rule
as counts, because under unshifted Controlled Tier dates a median over a handful of people is
individual-level data.

**A gap in the middle of a series.** The renderer MUST NOT bridge it. `series_segment` exists so this
is mechanical rather than a judgment call:

1. Group the rows by `(group_slug, series_segment)`.
2. Draw one `plot()` call and one `fill_between()` call per group and segment. Never one call per group.
3. Never interpolate, forward-fill, or connect the last point of segment `k` to the first point of
   segment `k + 1`. A visible break is the correct rendering: it says data ran out, which is true.
4. A segment of length 1 draws a marker, not a line, so a single surviving day is visible.
5. The plate note and the legend both state the truncation rule and the number of days affected,
   read from `figures.figure2.days_dropped_by_group`. The legend also states **the truncation day**
   for each series, read from `figures.figure2.last_day_by_group`, because a reader needs to know
   where a line stops and why. Between them those two numbers say everything a reader of the
   artwork needs: this series was truncated, this many days went, and it stops here. Neither prints
   the dropped days one at a time, and the reason is length and not disclosure. A plate is a
   caption, and up to 90 integers per series is not caption content.

   **The identity of the surviving days is not withheld, and this item used to say that it was.**
   The surviving set is the `day` column of this file, at every collapse level, so the dropped set
   is its complement and any reader who wants it reads the CSV. An earlier draft of this item said
   the opposite, that a full list of which days fell below the floor is itself a per-day count
   pattern and is therefore not printed, which was a promise the schema above it broke in the same
   breath. The schema is right and the promise was wrong. What the surviving set reveals is exactly
   what the suppression rule is built to publish: these days had more than 20 contributors, those
   had 20 or fewer. It pins no exact small count, because every withheld day is bounded only as at
   or below the floor and every count printed beside a surviving day is already rounded. Section
   10.2 exception 3 carries the argument in full and names this file.

**All six statistic columns are rounded to two decimals before the frame is built**, which is the
unit's decimals from 2.4 and is what keeps a 286-row frame of medians off the near-unique class:
two decimals bound the value space at about a hundred, three do not, and an earlier draft of the
example below printed three. 10.2 exception 5 covers what rounding alone does not, which is the
`single_group` case where one series leaves at most ninety rows and a smooth fitted curve can still
approach one distinct value per row.

```csv
group_slug,display_label,group_order,day,n_contributing,observed_median,observed_p25,observed_p75,fitted_marginal,fitted_lo,fitted_hi,in_accrual_window,series_segment
lumbar_fusion,Lumbar fusion,4,1,80,0.22,0.04,0.41,0.22,0.18,0.26,true,1
lumbar_fusion,Lumbar fusion,4,2,80,0.25,0.07,0.44,0.25,0.21,0.29,true,1
```

### 4.3 `figures-csv/figure3_forest.csv`

One row per contrast, robustness row or subgroup, in three blocks.

| Column | Type | Unit | Suppression | Example |
|---|---|---|---|---|
| `block` | integer | 1, 2 or 3 | never | `2` |
| `block_label` | string | printed as the block heading | never | `Robustness of the primary contrast` |
| `row_order` | integer | 1-based within the block, contiguous | never | `5` |
| `slug` | string | stable across runs and across every exhibit | never | `observation_weighted` |
| `display_label` | string | verbatim from the label table | never | `Weighted for observation` |
| `estimate` | float | see `unit` | `SUPPRESSED` when `estimable` is `false` | `4.7` |
| `ci_lo` | float | | `SUPPRESSED` when `estimable` is `false` | `2.7` |
| `ci_hi` | float | | `SUPPRESSED` when `estimable` is `false` | `6.7` |
| `unit` | string | a slug from section 2.4 | never | `activity_days` |
| `axis` | string | `primary` or a named alternative | never | `primary` |
| `render` | string | `marker`, `panel` or `text` | never | `marker` |
| `n` | integer | episodes contributing | `SUPPRESSED` when below floor | `340` |
| `estimable` | boolean | | never | `true` |
| `not_estimable_display` | string | printed in place of the marker; empty when `estimable` is `true` | never | `not estimable (cell size)` |
| `is_primary` | boolean | exactly one `true` in the whole file | never | `false` |
| `reference_value` | float | the null line for this row's scale: `0` on a difference scale, `1` on a ratio scale | never | `0` |

Sort keys: `block`, `row_order`.

**A below-threshold row is present, not absent.** This is the opposite of the Figure 2 rule, and the
difference is deliberate. A Figure 2 day is one point in a continuous series, and its absence reads
as "the series ended". A Figure 3 row is a named, prespecified analysis, and its absence reads as
"this analysis was never planned", which is false and which leaks by omission: a reader who knows the
prespecified subgroup list can infer exactly which cells were small. So the row is written with
`estimable = false`, `estimate`, `ci_lo`, `ci_hi` and often `n` set to `SUPPRESSED`, and the renderer
prints `not_estimable_display` where the marker would sit.

Rows whose `render` is not `marker` carry a value on a different axis, and the renderer draws **no
marker and no whisker** for them, because a marker on a shared axis asserts a comparison that does
not exist.

| `render` | What the renderer draws |
|---|---|
| `marker` | a point at `estimate` with a whisker from `ci_lo` to `ci_hi`, against `reference_value` |
| `panel` | a small inset panel at the row position, plotted from `debt.delta_shift.grid` in `results.json`. The delta-shift row is the only `panel` row, because a tipping curve is not a point estimate with an interval. |
| `text` | the `display_label` and the value as text at the row position |

```csv
block,block_label,row_order,slug,display_label,estimate,ci_lo,ci_hi,unit,axis,render,n,estimable,not_estimable_display,is_primary,reference_value
1,Primary and key secondary contrasts,1,fusion_vs_decompression,Fusion versus decompression,4.4,2.6,6.2,activity_days,primary,marker,340,true,,true,0
3,Subgroups,8,subgroup_device_wear,Program-provided device,SUPPRESSED,SUPPRESSED,SUPPRESSED,activity_days,primary,marker,SUPPRESSED,false,not estimable (cell size),false,0
```

### 4.4 `figures-csv/figure4_event_centered_activity.csv`

Normalized daily activity centred on the acute-care event rather than on discharge: one series for
the cases and one for their post-discharge-day matched controls, over the fixed offsets `-14` to
`+7` that `ANALYSIS-PLAN.md` section 9.5 names. **Two series, 22 offsets, 44 rows, on every run.**

**Why it exists, and why it is a SUPPLEMENTARY exhibit.** The plan puts an event-centered curve in
the alternate exhibit set of 9.5, which is reached only at tiers 1 and 2, and permits
"event-centered association and **visualization**" at tier 3, which is the likeliest tier this
cohort reaches. Before 1.6.0 there was no exhibit for it at all, so the one visualization the plan
explicitly permits at tier 3 had no file to be written into and would have had to be drawn from a
number the bundle does not carry. That gap was real and this file closes it. **What 1.6.0 got
wrong was the placement.** It put this file in the **primary** exhibit set, which took the main
text to four figures; `CLAUDE.md` section 2 rule 7 and section 6 fix the deliverable at exactly 3
figures and 3 tables and send everything beyond them to a supplement, and 9.5 specifies this curve
as the **alternate Figure 2 at 50 or more events**, not as a fourth primary figure. The plan wins
under 11.3. At 1.8.0 this is a supplementary exhibit: `figures.figure4.exhibit_set` reads
`"supplementary"`, and the curve is printed in the supplement.

**Nothing about the file changes, and that is deliberate.** It keeps this section, its ten
columns, its 44 rows, its sort keys, its suppression rule, its `MANIFEST.csv` row and its full
`results.json` block; `07_export.py` still builds it on every run and `local/figures.py` still
renders it. Supplementary names where the picture is **printed**, not whether it is drawn. The
alternate set's version of this curve, where Figure 2 is replaced by it wholesale, is a different
exhibit at a different figure number, is still outside this contract until 11.4's obligation is
discharged, and is served by this same renderer when it lands.

**Its denominator is `denominators.event_centered_members` and not `events_composite`**, per 3.2.
The curve is drawn over risk-set members carrying the structural filter the fits carry, so the
composite first-event count is somebody else's population and the plate note used to print a
number larger than the curve's own. Being supplementary does not excuse the figure from carrying
its own denominator: `CLAUDE.md` section 2 rule 5 makes every printed figure print one, and this
figure is printed.

| Column | Type | Unit | Suppression | Example |
|---|---|---|---|---|
| `series_slug` | string | | never | `event_case` |
| `display_label` | string | verbatim from 7.15 | never | `Cases` |
| `series_order` | integer | 1-based, the legend and colour order | never | `1` |
| `day_relative_to_event` | integer | offset from the event date, `-14` to `7`; `0` is the event day | never | `-3` |
| `n_contributing` | integer | episodes contributing that offset, `round20`-rounded | `SUPPRESSED` when below the floor | `40` |
| `observed_median` | float | `normalized_activity`, two decimals | `SUPPRESSED` with `n_contributing` | `0.62` |
| `observed_p25` | float | `normalized_activity` | `SUPPRESSED` with `n_contributing` | `0.44` |
| `observed_p75` | float | `normalized_activity` | `SUPPRESSED` with `n_contributing` | `0.81` |
| `plotted` | boolean | `false` on a suppressed offset, so the renderer branches on one column | never | `true` |
| `not_plotted_display` | string | printed where the marker would sit; empty when `plotted` is `true` | never | `20 or fewer contributors, suppressed` |

Sort keys: `series_order`, `day_relative_to_event`.

**This file keeps its rows and suppresses its cells, which is Figure 3's convention and not Figure
2's, and the difference is the axis rather than a change of mind.** A Figure 2 day is a point on a
curve that runs forward from discharge until the data run out, so an absent day reads as "the
series ended", which is true and is what the reader should see. An event-centered offset is a
coordinate in a **fixed, two-sided window** that this document and the plan both publish in
advance: it is bounded at `-14` and at `+7` whatever the data do, the interesting content is the
shape either side of offset `0`, and a curve that silently shortened to the offsets that cleared
the floor would misstate the window it was drawn over. So the row is written, `n_contributing`,
`observed_median`, `observed_p25` and `observed_p75` carry the literal `SUPPRESSED` token, `plotted`
is `false`, and `not_plotted_display` carries the 7.5 sentence the renderer prints in place of the
marker. Two consequences worth stating because they are what makes the choice cheap: the row count
is exactly 44 on every run, so `MANIFEST.csv` and the fixture pin an exact number rather than a
data-dependent one, and `day_relative_to_event` holds 22 distinct values across 44 rows at every
tier, so the axis never approaches the near-unique ceiling and this file needs no part of 10.2
exception 3.

**At tier 4 the file is 44 rows of `SUPPRESSED`.** `gate.arm_a.permitted` is `false`, no
event-centered query is submitted at all, `figures.figure4.tier_permits_plot` is `false`, and every
`not_plotted_display` carries the `not_permitted_by_tier` sentence of 7.5 rather than the
contributor sentence. Those 176 cells are **not** entries in `results.json.suppressed`, because 3.7
distinguishes not permitted from suppressed and a tier-driven absence is recorded where the tier is
recorded; `MANIFEST.csv` still counts them in `n_suppressed_cells`, which counts written tokens and
not reasons, and `min_disclosed_count` is empty because the file discloses no count.

**176 is `44 x 4`, and the `not_plotted_display` column is not in it.** The four cells a row can
write as the literal `SUPPRESSED` token are `n_contributing`, `observed_median`, `observed_p25`
and `observed_p75`, so a wholly suppressed file is `44 x 4 = 176` and nothing else. The
`not_plotted_display` column also carries 44 strings at tier 4, and every one of them is a 7.5
sentence, but this is a **figure** CSV and 8.3 counts a suppression sentence only in a table CSV.
The reason is the column's job: in a table CSV the sentence **is** the cell, printed where the
number would have gone, so counting it counts a hidden value; here it is a declared companion
column that exists to be printed **beside** an already-counted `SUPPRESSED`, so counting it counts
the same hidden value twice and reports 220 for a file with 176 hidden numbers in it. Figure 3's
`not_estimable_display` is the same shape and is excluded for the same reason. This is a rule
about what a column is for and not about which file it is in, and it is stated here because this
is the file where the two conventions meet. That is
section 1's rule for a file whose content is entirely suppressed, met in this file's own
representation: the file exists, carries its header, and every row says why it is empty.

```csv
series_slug,display_label,series_order,day_relative_to_event,n_contributing,observed_median,observed_p25,observed_p75,plotted,not_plotted_display
event_case,Cases,1,-14,40,0.62,0.44,0.81,true,
event_case,Cases,1,0,SUPPRESSED,SUPPRESSED,SUPPRESSED,SUPPRESSED,false,"20 or fewer contributors, suppressed"
```

---

## 5. The `tables-csv/*.csv` files

**Every cell in a table CSV is a string, and every cell a reader sees is a display string.** No
table CSV contains a raw float or a raw integer. This is what the house reader already expects
(`load_table` reads with `dtype=str` and `keep_default_na=False`), and it puts the formatting
decision in one place: the exporter renders each number through the decimals table in section 2.4
and writes the resulting token, so `tables.py` copies strings into a Word table and never formats
anything.

**Seven columns in this bundle are strings that are not display strings, and they are enumerated
rather than excused.** `slug` in `ledgers-csv/ledger_exclusion_and_censoring_reasons.csv`,
`variable`, `role`, `source_table` and `source_concept_set` in
`ledgers-csv/ledger_variable_provenance.csv`, `group_slug` in
`ledgers-csv/ledger_wear_availability_by_day.csv`, and
`Source key` in `tables-csv/table2_adjusted_debt_footer.csv` hold **machine tokens**: a rung slug,
an analysis-variable token, a role from a closed vocabulary, a derived table name, a concept-set
module name, a procedure-group token, and the dotted
`results.json` path 5.3 requires. None of the seven is printed into a manuscript surface, all seven
are snake_case or dotted, and a rule saying every cell is a display string would put every one of
them in front of `verify.py`'s snake_case check and fail the bundle on arrival. Section 6 carries
the corrected rule and the 10.2 ownership register classes all seven. **This sentence said five
until 1.9.1**, having missed `source_concept_set`, which section 6 already named, and `group_slug`,
which section 6 did not name either; both were found by the machine-token column sweep 10.2 now
carries, and the number here is checked against that register rather than counted by hand.

| Rule | Value |
|---|---|
| Column headers | display strings in sentence case, printed verbatim. Group headers carry their own n. |
| Cell content | display strings only, taken from a `display` field in `results.json` or from the label table |
| Suppressed cell | the suppression sentence itself, verbatim from 7.5, never a token |
| Empty cell | the empty string, meaning the row does not apply to that column |
| Row order | the exact print order. `row_order` is column 1 and runs 1 to N with no gaps. |
| Percentages | zero decimals, computed from the ROUNDED numerator and the ROUNDED denominator |
| A percentage whose count is suppressed | suppressed, with no exception, because a percentage times a disclosed denominator recovers the hidden count exactly |

Two different integrity checks apply, and conflating them would make one of them vacuous:

| Surface | Check | Why this one |
|---|---|---|
| A table cell | the cell in the rendered `.docx` equals the cell in the table CSV, character for character | The CSV is itself an md5-stamped export. Requiring every one of roughly two hundred table cells to also exist in `results.json` would duplicate the CSV inside the JSON for no gain. What can go wrong is `tables.py` reformatting or reordering a cell on the way into Word, and a round-trip diff catches exactly that. |
| A prose numeral, a caption, a legend, a plate note | the token is a member of the approved display vocabulary of section 2.5 | Prose is composed, so a numeral in it could have been typed. Nothing else in the bundle has that failure mode. |

A hand-typed string in a table cell is therefore caught upstream, at `safe_export()`, which is the
only writer of a table CSV.

### 5.1 `tables-csv/table1_cohort_characteristics.csv`

Cohort characteristics and wearable data availability by procedure group.

Columns, in file order:

| # | Column header | Content |
|---|---|---|
| 1 | `row_order` | `1` to N, contiguous. `07_export.py` asserts the contiguity before export and halts on a gap; 10.2 says why the exemption on this column makes that assertion load-bearing |
| 2 | `Characteristic` | the row group, e.g. `Age, years` |
| 3 | `Level` | the level within the characteristic, e.g. `65 or older`; empty for a single-line row |
| 4 to k | one column per entry in `cohort.groups`, header taken verbatim from `groups[i].column_header` | `Cervical decompression (n = 60)`, and so on. **The number of these columns follows the collapse level**, so a consumer reads `tables.table1.columns` rather than assuming four. |
| k+1 | `Statistic` | what the cells are: `n (%)`, `median (IQR)` or `mean (SD)` |

`key_columns`: `["Characteristic", "Level"]`.

Row order, fixed. A row whose every cell is suppressed is still written.

| Block | Rows |
|---|---|
| Demography | Age (median, IQR); Age band (under 50, 50–64, 65–74, 75 or older); Sex assigned at birth (Female, Male, Other or not reported); Self-reported race (each category plus Not reported); Self-reported ethnicity (Hispanic or Latino, Not Hispanic or Latino, Not reported) |
| Clinical | Body mass index (median, IQR); Body mass index band (under 25, 25–29, 30 or above, Not recorded); Comorbidity burden (median, IQR); Comorbidity burden band (0, 1, 2, 3 or more) |
| Index operation | Length of stay, days (median, IQR); Length of stay band (0–1, 2–3, 4 or more); Index era (before 2020, 2020–2021, 2022 or later) |
| Wearable | Device class (program provided, participant owned, Not recorded); Preoperative baseline steps per day (median, IQR); Valid baseline days (median, IQR); Valid wear days inside the accrual window (median, IQR); Near-complete accrual window, defined as 28 or more valid days (n, %) |

Index era is a banded calendar year over a group of at least 20 episodes. It is an aggregate, not a
date column, and it is the only calendar-derived row in the bundle. Section 10 records why that
distinction has to be stated rather than assumed.

```csv
row_order,Characteristic,Level,Cervical decompression (n = 60),Cervical fusion (n = 80),Lumbar decompression (n = 120),Lumbar fusion (n = 80),All groups (n = 340),Statistic
1,"Age, years",,"62 (54–70)","59 (51–67)","64 (56–71)","61 (53–69)","62 (54–70)",median (IQR)
2,Age band,75 or older,"20 or fewer, suppressed per All of Us dissemination policy","20 or fewer, suppressed per All of Us dissemination policy","40 (33%)","20 or fewer, suppressed per All of Us dissemination policy","60 (18%)",n (%)
```

### 5.2 `tables-csv/table2_adjusted_debt.csv`

Adjusted digital recovery debt by procedure group. Absolute adjusted levels live here and only here;
contrasts live in Figure 3 and only there. The split is enforced: `verify.py` asserts that no
contrast slug appears in this file and that no group-level adjusted level appears in
`figure3_forest.csv`.

| # | Column header | Content |
|---|---|---|
| 1 | `row_order` | |
| 2 | `Procedure group` | `cohort.groups[i].display_label` |
| 3 | `Episodes` | `n = 120` style token from `by_group[i].n.display_n_equals` |
| 4 | `Complete windows` | `n = 40` style token from `by_group[i].n_complete_windows`. The naive column has its own denominator and prints it. |
| 5 | `Unadjusted debt, median (IQR)` | `activity_days`, one decimal, en-dash IQR. The naive estimator. |
| 6 | `Adjusted debt, activity days (95% CI)` | one decimal, `to` separator |
| 7 | `Thousand steps lost (95% CI)` | one decimal |
| 8 | `Adjusted mean normalized activity (95% CI)` | two decimals |
| 9 | `Reached 80% of baseline (95% CI)` | percent with a confidence interval, zero decimals, percent sign on all three numbers |

`key_columns`: `["Procedure group"]`. Rows: the groups in `cohort.groups` order, so the row count
follows the collapse level; the final row is `All groups`.

```csv
row_order,Procedure group,Episodes,Complete windows,"Unadjusted debt, median (IQR)","Adjusted debt, activity days (95% CI)",Thousand steps lost (95% CI),Adjusted mean normalized activity (95% CI),Reached 80% of baseline (95% CI)
1,Cervical decompression,n = 60,n = 40,"5.4 (2.1–11.8)",6.1 (4.2 to 8.0),28.4 (19.1 to 37.7),0.79 (0.74 to 0.84),67% (95% CI 54% to 78%)
4,Lumbar fusion,n = 80,n = 40,"14.2 (7.6–22.9)",12.4 (10.1 to 14.7),61.8 (49.2 to 74.4),0.58 (0.53 to 0.63),31% (95% CI 21% to 43%)
```

### 5.3 `tables-csv/table2_adjusted_debt_footer.csv`

The Table 2 footer, as rows rather than as a blob, so each footer value traces to a key.

| # | Column header | Content |
|---|---|---|
| 1 | `row_order` | |
| 2 | `Footer item` | display label |
| 3 | `Value` | display string, or the suppression sentence |
| 4 | `Source key` | the dotted path into `results.json` this value came from |

`key_columns`: `["Footer item"]`. Required rows, in order:

| row | Footer item | Source key |
|---|---|---|
| 1 | Model family | `debt.model_fit.family` |
| 2 | Model rung reached | `meta.estimator.rung_display` |
| 3 | Residual correlation | `debt.model_fit.residual_correlation` |
| 4 | Intraclass correlation | `debt.model_fit.icc` |
| 5 | Marginal R squared | `debt.model_fit.marginal_r2` |
| 6 | Conditional R squared | `debt.model_fit.conditional_r2` |
| 7 | Contributing person-days | `debt.model_fit.n_person_days` |
| 8 | Share with zero debt | `debt.by_group[4].share_zero_debt` |
| 9 | Manski bounds on the primary contrast | `debt.manski.display` |
| 10 | Delta-shift tipping point, point estimate | `debt.delta_shift.tipping_point_point_estimate` |
| 11 | Delta-shift tipping point, first delta whose interval includes zero | `debt.delta_shift.tipping_point_interval` |
| 12 | Denominator | `denominators.analytic.display_n_equals` |
| 13 | Unadjusted primary contrast | `debt.unadjusted_contrasts.fusion_vs_decompression.estimate` |
| 14 | Unadjusted contrast, what it removes | `debt.unadjusted_model.definition_display` |
| 15 | Unadjusted contrast, model rung reached | `debt.unadjusted_model.rung_display` |

```csv
row_order,Footer item,Value,Source key
4,Intraclass correlation,0.62,debt.model_fit.icc
9,Manski bounds on the primary contrast,-0.4 to 9.6 activity days,debt.manski.display
13,Unadjusted primary contrast,4.9 (95% CI 3.1 to 6.8),debt.unadjusted_contrasts.fusion_vs_decompression.estimate
```

**Rows 13 to 15 are the STROBE item 16(a) pair, and they are here rather than in Table 2's body or
in Figure 3 for the reasons 3.5 sets out.** Row 13 is the unadjusted primary contrast with its own
interval, which a reader reads against the adjusted contrast in Figure 3 block 1. Row 14 is the
sentence saying which terms were removed and which were kept, without which "unadjusted" is a word a
reader fills in from habit and fills in wrongly, because this table's own column 5 already uses it
for a different quantity. Row 15 is the rung the **unadjusted** fit reached, printed beside row 2's
rung for the adjusted fit, so that two fits landing on two rungs of the 3.1.1 ladder is visible on
the page instead of buried: when the two differ, the gap between the contrasts carries a change of
model family as well as a change of covariate set. When the unadjusted fit returned no estimate, row
13 prints the 7.5 sentence for `debt.unadjusted_model.not_estimable_reason` and row 15 prints the
same sentence, which is the ordinary suppression behaviour of every other footer row and not a
special case. **The three rows are appended and nothing is renumbered**: rows 1 to 12 keep the
`row_order` they had at 1.8.0, because `07_export.py` and its fixture are owned elsewhere and a
renumbering is a change every one of their assertions would have to absorb for no gain.

### 5.4 `tables-csv/table3_gate_part_a.csv`

The protocol's A-through-F ledger.

| # | Column header | Content |
|---|---|---|
| 1 | `row_order` | |
| 2 | `Stage` | `A` to `F` |
| 3 | `Definition` | verbatim from the protocol's required-count column |
| 4 | `Cervical decompression` | count or suppression sentence; empty where the stage is not stratified |
| 5 | `Cervical fusion` | |
| 6 | `Lumbar decompression` | |
| 7 | `Lumbar fusion` | |
| 8 | `All groups` | |

`key_columns`: `["Stage"]`. Eight rows: A, B, C, then D split into three component rows
(first emergency department visits, readmissions, composite), then E, then F. Row F carries the
stratified counts and is written even when all four are suppressed.

```csv
row_order,Stage,Definition,Cervical decompression,Cervical fusion,Lumbar decompression,Lumbar fusion,All groups
1,A,Unique qualifying spine episodes by procedure group,60,80,120,80,340
7,E,Events with a computable proximal step ratio,,,,,"20 or fewer, suppressed per All of Us dissemination policy"
```

### 5.5 `tables-csv/table3_gate_part_b.csv`

Whatever the tier allows. This file always exists.

| # | Column header | Content |
|---|---|---|
| 1 | `row_order` | |
| 2 | `Quantity` | display label |
| 3 | `Estimate (95% CI)` | display string, or the suppression sentence, or empty when the tier permits nothing |
| 4 | `Note` | the tier constraint on the claim |

`key_columns`: `["Quantity"]`.

When `gate.arm_a.permitted` is `false` the file carries exactly two rows: the tier reached and the
verbatim permitted claim. It is never an empty file and never a file with only a header, because a
header-only table in a manuscript reads as a build error rather than as a finding.

When `gate.arm_a.permitted` is `true` the file carries one row per key of `arm_a.estimates`, in the
order 3.7 lists them, with the tier constraint of 7.10 in the `Note` column and the
`not_permitted_by_tier` sentence of 7.5 in `Estimate (95% CI)` on every key the tier does not
produce. At tier 3 that is eight rows carrying a number and four carrying the sentence.

```csv
row_order,Quantity,Estimate (95% CI),Note
1,Feasibility tier reached,No early-warning modeling,Determined by stage E
2,Permitted claim,"Feasibility statement only, with the count suppressed",Verbatim from the prespecified decision table
```

**The permitted claim in that second row is 7.10's string and not the protocol's.** An earlier draft
of this example printed "Do not pursue early-warning modeling; pivot to the continuous recovery-debt
study", which is the protocol's own tier-4 wording and is a different sentence from the one 7.10
carries. Section 6 makes section 7 the sole authority for a printed string and 11.3 records that
7.10 is quoted from `ANALYSIS-PLAN.md` section 1.2, so the label table wins and the example is
corrected to it. The two say the same thing and that is exactly why the divergence would have
survived review: `verify.py` compares by character equality, so it would not have survived the
export.

### 5.6 The five STROBE companion ledgers, in `ledgers-csv/`

**Why they are in the bundle rather than outside it.** `ANALYSIS-PLAN.md` Phase 3 requires five
companion ledgers: a concept-set registry, variable provenance, exclusion and censoring reasons,
wear availability by day and group, and the matched-set size distribution. Section 0 of this
document forbids a module from writing a file this contract does not name, and section 1 declares
the bundle exhaustively, so before contract 1.1.0 the plan required five artefacts that had no legal
export path: `cs_spine.registry_rows()` exists, is tested and is documented as "the concept-set
registry the STROBE supplement needs", and there was nowhere for it to go.

The alternative was to declare them supplement-only and let some module write them outside the
bundle. That was rejected, and the reason is R3: a file that leaves the perimeter without a
`MANIFEST.csv` row carries no md5, so a transcription slip in transfer is undetectable, and a ledger
that reports why episodes were excluded is exactly the kind of file a reviewer will quote. Naming
them here costs one directory and five manifest rows and keeps every boundary rule intact. They are
supplement-only in **destination** and in-bundle in **discipline**.

**Rules that bind all five.**

| Rule | Value |
|---|---|
| Directory | `ledgers-csv/`, no nesting |
| `kind` in `MANIFEST.csv` | `table-csv`. `disclosure.MANIFEST_KINDS` has exactly three members and is not going to grow for these; a ledger is a table of display strings, so `table-csv` is the honest label and it is the label that turns on the all-strings check |
| `exhibit` in `MANIFEST.csv` | the empty string. A ledger is not a numbered exhibit |
| Cell content | display strings only, as in section 5. Booleans print as `true` and `false` |
| Every count cell | `disclosable()`-tested on its true value, then `round20`-rounded, then written as its display string, or the suppression sentence of 7.5 verbatim. The cell `safe_export()` then sees is tested with `is_legal_disclosed_count()`, which is the other predicate and the other moment (section 0) |
| Suppression | identical to a table CSV: the sentence, never a token, never a blank |
| `safe_export()` declarations | every count column is named in `count_cols`, every percentage column in `percentage_columns`, every set of **columns** that partitions a disclosed row total in `partitions`, and every set of **rows** that partitions a disclosed column total in `row_partitions`, which is `07_export.py`'s own declaration and not the module's: see 10.4. A count column left out of `count_cols` is not floor-tested at all, which is the one failure mode that leaves no mark in the file it damages |
| Row order | fixed by the `sort_keys` named per file below, so the bytes are stable |
| `results.json` block | none. Reached by literal path; integrity rides on `MANIFEST.csv` |
| Written by | `pipeline/07_export.py`, through `safe_export()` like every other file. Ledger 1 has a **second writer**, `pipeline/01_probe.py`, and an md5 equality check that closes the drift surface; see below |
| Read by | `local/make_strobe.py` and `local/verify.py` only |

**The concept-set registry carries no counts and therefore never suppresses.** It is a list of the
codes in the locked set, which is a property of the specification and not of any participant. The
other four carry counts, and every one of those counts passes `disclosable()` before it is rounded
and `is_legal_disclosed_count()` as it is written.

| # | File | One row per | `sort_keys` |
|---|---|---|---|
| 1 | `ledger_concept_set_registry.csv` | code or stem in the locked set, so **51 rows** | `vocabulary_id`, `code` |
| 2 | `ledger_variable_provenance.csv` | analysis variable | `variable` |
| 3 | `ledger_exclusion_and_censoring_reasons.csv` | reason within a rung | `step`, `reason_detail` |
| 4 | `ledger_wear_availability_by_day.csv` | group and post-discharge day | `group_order`, `day` |
| 5 | `ledger_matched_set_sizes.csv` | matched-set size | `set_size` |

**1. `ledger_concept_set_registry.csv`.** The columns are `cs_spine.REGISTRY_COLUMNS`, copied
exactly and in order, because `registry_rows()` is the producer and a renamed column here would be a
silent mismatch:

`vocabulary_id`, `match`, `code`, `procedure_class`, `region_primary`, `region_mirrored`,
`is_add_on`, `is_junction`

Eight columns, all strings. **There is no bare `region` column**: `region_primary` carries the
locked assignment and `region_mirrored` carries the assignment under the mirrored junction map of
the `junctions_mirrored` supplementary row, and both are populated on every row unconditionally, so
a row where the two differ is exactly a junction code and needs no flag beyond `is_junction`.
`registry_rows(mirror_junctions=...)` accepts the flag and ignores it, so this file is byte-identical
whichever way it is called. Any code written against an older `region` column is broken and must be
updated to name which of the two it wants.

**Fifty-one rows, not 852.** `registry_rows()` yields one row per **code or stem**: the 30 CPT-4
codes plus the 21 ICD-10-PCS four-character stems of the locked set, and `30 + 21 = 51`. 852 is the
**concept** count, which is what those 51 codes and stems resolve to in the CDR's concept table, and
it is not a shape this producer can return at all: `REGISTRY_COLUMNS` carries no `concept_id`, so
this file has no column that could differ across the 704 fusion and 118 decompression PCS concepts
sharing a stem, and 852 rows would be 852 copies of 51 distinct rows. An earlier draft of the
manifest example in 8.3 said 852 rows, which was the concept count filed under the registry's row
count; it is corrected to 51 there and here.

Both numbers are wanted and they live in different places, which is why neither substitutes for the
other. The **specification** is this ledger, because 51 codes and stems is what a reader needs in
order to reproduce the phenotype: it is what goes into a query. The **resolution** is
`meta.concept_set.n_concepts` in `results.json`, with the CPT-4 and ICD-10-PCS subtotals of 3.1,
because 852 is what the locked set was measured to return against this CDR and is the number
`CLAUDE.md` stop condition 2 halts on. The ledger is deliberately not expanded to one row per
concept: it would add no specification and would restate a resolution the JSON already carries.

**Two writers, and `07_export.py` checks itself against the first one.** `pipeline/01_probe.py`
also writes this file, and legitimately: the probe is where the locked concept set is validated
against the live CDR by `cs_spine.assert_concept_frame()`, and the registry falls out of that
validation, so making the probe hold it in memory across a session boundary in order to let a later
module write it would be ceremony rather than control. Both writers call the same pure function, so
the bytes are identical by construction. Identical by construction is not the same as checked:

- `01_probe.py` writes it through `safe_export()` at the contract path in Phase 2 and records the
  returned md5 in its probe result, under `concept set.registry.md5` (section 1.2).
- `07_export.py` writes it through `safe_export()` at the contract path in Phase 4 as one of the
  sixteen manifest rows. **If the file is already on disk, `07_export.py` reads the existing bytes,
  hashes them with `disclosure.md5_of_bytes`, and compares that md5 against the one `safe_export()`
  returns for its own write. A difference halts the export.** It cannot be a data finding, because
  `registry_rows()` reads no data; it means `cs_spine.py` moved between Phase 2 and Phase 4, which
  invalidates every episode built in between.

The manifest row is `07_export.py`'s in every case, so the bundle still has sixteen rows and the
probe's earlier write never becomes a seventeenth. The comparison is the whole point: without it the
two writers are an argument that they agree rather than a check that they do.

**This ledger declares `specification_columns`, and declares exactly one column, `code`.** One row
per code makes `code` unique by construction, which trips the near-unique refusal class on any frame
wider than the floor, and that rule is right in general and wrong here: a published list of CPT-4
and ICD-10-PCS codes is a property of the specification and identifies nobody. The exemption is
per-column, reaches the near-unique and identifier-like classes only, and is defined with the rest
of the whitelist in section 10.2. It is not a blanket over the file: `vocabulary_id`,
`procedure_class`, `region_primary`, `region_mirrored`, `is_add_on` and `is_junction` are checked
normally, and all six are low-cardinality closed vocabularies with no need of it.

**2. `ledger_variable_provenance.csv`.** Columns: `variable`, `display_label`, `role`, `source_table`,
`source_concept_set`, `derivation`, `unit`, `n_total`, `n_missing`, `missing_handling`. Ten columns.
`role` is one of `outcome`, `exposure`, `covariate`, `weight`, `stratifier`, `identifier_free_key`.
`n_total` and `n_missing` are counts, so both are rounded, suppression-tested and named in
`count_cols`; every other column is a specification fact. One row per variable makes `variable`,
`display_label` and `derivation` unique by construction, so those three
are declared in `specification_columns` per section 10.2 and no others are. **`display_label` and
`derivation` are printed strings and are owned by section 7.13**, which carries one row per variable
and is the authority section 6 requires a printed string to have; `variable` itself is the token the
producer emits and is never printed. The 10.2 register records all three and which class each is
in.

**`unit` and `missing_handling` are printed strings too, and section 7.14 owns them.** Ten columns
is enough for one file to carry all three kinds of string this bundle writes, and this is the file
that carries all three: four machine tokens that are never printed, four printed strings, and two
counts. Two of the printed four had an owner before this version and two did not. `unit` is a
printed unit name, one per variable, and it is deliberately **not** a slug from 2.4: the unit of
`bmi` is `Kilograms per square metre`, which is a property of the variable and not of any node in
`results.json`, and five of the twelve variables are categorical and carry the empty string.
`missing_handling` is one prespecified sentence per variable saying what the analysis does with a
missing value, which is a methods commitment fixed before any count exists and is the column a
reviewer reads this ledger for. Both are printed verbatim into a cell, section 6 makes section 7 the
sole authority for a printed string, and until 7.14 existed neither had one: `verify.py`'s
character-equality assertion had nothing to compare them against and would have passed vacuously on
twenty-four strings. That is the same defect 7.12 and 7.13 closed for the two `display_label`
columns at contract 1.5.0, found in the same file, one column pair later.

**Where the file's other four strings come from, so no column in it is unowned.** `variable` is the
`ledger_variable_missingness` stage's own token; `role` is one of the six values named above, a
closed vocabulary this section owns; `source_table` is the derived table the variable is measured
on, owned by `pipeline/build_all.sql` and named in `DAG-SCHEMA.md`; and `source_concept_set` names
the concept-set module a variable resolves through, or is empty. All four are machine tokens, none
of them is printed into a manuscript surface, and the 10.2 register classes all four so section 6's
rule for a `tables-csv` cell does not reach them.

**`n_total` is on the file because the denominator is not the same on every row.** The producer,
`ledger_variable_missingness` in `pipeline/build_all.sql`, measures each variable over the population
that variable is defined on, and those populations differ by orders of magnitude: the ten
episode-level covariates over the analytic episodes, `daily_deficit` over the person-days inside the
accrual window, and `r72` over the first events. Without the column the file carries twelve
numerators and no denominator at all, a reader divides all twelve by the cohort size, and two of the
twelve come out wrong by a factor of tens. With it, the file obeys `ANALYSIS-PLAN.md` section 8
rule 8, the rule that made the other four ledgers carry their own denominators.

The file's own `unit` column carries the unit of the **variable**, not of these two counts. Both
counts are `count` in the sense of 2.4, zero decimals with a thousands separator, and their grain is
the grain of the population named on the row:

| Column | Type | Grain of the value | Null convention | Suppression |
|---|---|---|---|---|
| `n_total` | integer, written as its display string | episodes, person-days or events, being the rows of the population `source_table` and `derivation` name on that row | never null, never blank, never empty. Every row carries one | `disclosable()` on the true count, then `round20`, then the display string; the `cell_below_threshold` sentence of 7.5 if refused |
| `n_missing` | integer, written as its display string | the same grain as `n_total` on that row | never null, never blank. An exact `0` is disclosable and prints as `0` | `disclosable()` on the true count **and** on the true `n_total` less the true `n_missing`, then `round20`; the `secondary_suppression` sentence of 7.5 when it is the complement that failed |

**Why `n_missing` is now tested against its complement as well as against itself.** `n_total` and
`n_missing` on one row are a two-member partition of a disclosed total whose other member, the
observed count, is never written and is therefore recoverable by subtraction. On a variable that is
almost complete the recovered number is large and harmless. On a variable that is almost entirely
missing it is small, and it is exactly the cell the floor exists to protect. That is
`ANALYSIS-PLAN.md` section 8 rule 5, complementary suppression, written out in this file's own two
columns so `07_export.py` has a rule to implement rather than a principle to remember. The rule is
new with the column: before `n_total` existed this file carried no total to subtract from.

**What `n_total` discloses that the bundle did not already carry, checked rather than assumed.** Ten
of the twelve rows carry the analytic episode count, since `features` is `episodes_eligible` filtered
to `is_eligible`. That number is already published twice, as `denominators.analytic` and as the
`n_out` of ladder step 16, at the same rounding, and ten identical rounded numerals cannot be
differenced against one another. The remaining two, the in-window person-day count and the
first-event count, are new numerals in this file and are floor-tested and rounded like every other
count in it. The twelve rows are not a partition of anything, because the same episodes are counted
in all ten episode-grain rows, so no row is the residual of the others and no new subtraction is
available across rows.

```csv
variable,display_label,role,source_table,source_concept_set,derivation,unit,n_total,n_missing,missing_handling
baseline_steps,Preoperative baseline steps per day,covariate,features,,Median steps per day over the valid wear days of the baseline window,Steps per day,340,0,Complete case; an episode without an adequate baseline is excluded at step 12
daily_deficit,Daily activity deficit,outcome,drd_daily,,One less the normalized activity of an analyzable day inside the accrual window,Normalized activity,"9,860","1,720",Not imputed; a missing day is never read as a zero deficit and the observation weights of 3.7 do the work
r72,Proximal activity ratio at 72 hours,outcome,events,,Median steps of the proximal window over the participant's own baseline steps,Normalized activity,40,"20 or fewer, suppressed per All of Us dissemination policy",Not imputed; an event with no computable proximal window is excluded at step 18
```

**Two cells in that example used to contradict this section's own rules and are corrected here.**
The `baseline_steps` row named `fitbit_daily` as its source table while its `n_total` counted 340
episodes, and `fitbit_daily` is one row per person-day: a row cannot take its denominator from one
population and its provenance from another, which is precisely the confusion `n_total` was added at
1.3.0 to end. The measured population is `features`, one row per analytic episode, which is what
the producer reads and what the 340 counts. And its `n_missing` read 40 while 7.13 states that
`baseline_steps` is one of exactly three variables expected to report **zero** missing, because
rung 12 removed every episode without an adequate baseline before `features` was built. Forty
missing baselines in a cohort whose twelfth rung exists to exclude them is not a small example
value; it is a claim that a rung did not run. Both cells now agree with 7.13, with the ladder and
with the fixture.

**3. `ledger_exclusion_and_censoring_reasons.csv`.** Columns: `step`, `slug`, `display_label`,
`reason_detail`, `n_episodes`, `n_denominator`, `share_of_step_dropped`. Seven columns. This is the
file the plan sends the trauma-malignancy-infection breakdown to: section 2.6 keeps those three
indications as **one** rung,
step 3, because a ladder counts each episode once at the first rung it fails, so three rungs would
carry order-dependent counts a reader would misread as prevalences, and at this cohort size three
rungs would very likely produce three suppressed rows where the composite produces one disclosable
one. The breakdown belongs here, where an episode may be counted under more than one detail and the
those rows are explicitly not a partition. It also carries the censoring reasons of section 2.3 and the
three rescue routes of the elective proxy at step 4. `step` and `slug` are members of the
nineteen-rung vocabulary; a `slug` here that is not a rung slug is a failure.
`display_label` is the rung's ladder-box label, from 7.2.
`share_of_step_dropped` is a percentage and follows section 8 rule 4. `reason_detail` is one prespecified
sentence per row and is therefore unique by construction, so it is declared in `specification_columns`
per section 10.2; the two counts and the share beside it are not and are checked normally. **The twenty
sentences themselves are owned by section 7.12**, one per `(step, reason_detail)` pair the producer
emits, because section 6 makes section 7 the authority for a printed string and an exemption granted on
the ground that a column holds prespecified sentences has to have somewhere for those sentences to
live.

**`n_denominator` is on the file because the share's denominator is not always the rung's
`n_dropped`, and the rung where it is not is the one a reader is most likely to get wrong.**
`build_all.sql` says so in terms at the head of the producer: for the rung 4 rescue routes the
population at risk of being rescued is the set of episodes with an emergency department encounter,
not the set of episodes the rung dropped. `07_export.py` computes `share_of_step_dropped` as
`n_episodes` over `n_denominator` and applies the floor to both before either is printed, so the file
has to carry the denominator it divided by. The column name `share_of_step_dropped` is kept rather
than renamed, and `n_denominator` is what makes keeping it honest: the share is over the denominator
printed beside it, which is the rung's drop count on most rows and is something else on the rest.

| Column | Type | Grain of the value | Null convention | Suppression |
|---|---|---|---|---|
| `n_episodes` | integer, written as its display string | episodes | never null, never blank. An exact `0` is disclosable and prints as `0` | `disclosable()` on the true count, then `round20`; the `cell_below_threshold` sentence of 7.5 if refused, or the `secondary_suppression` sentence when a declared partition below is what suppressed it |
| `n_denominator` | integer, written as its display string | episodes | never null, never blank. Every row carries one, including the rows where it equals `n_episodes` | `disclosable()` on the true count, then `round20`; the `cell_below_threshold` sentence of 7.5 if refused |
| `share_of_step_dropped` | percentage | percent, zero decimals, rounded numerator over rounded denominator | never blank | the `numerator_suppressed` sentence of 7.5 whenever either count beside it is suppressed, per section 8 rule 3 |

**Which denominator a row carries, so the column is checkable and not merely present.** On steps 3,
12, 14 and 15 it is the count of episodes whose first failing rung is that rung, which is the
ladder's own `n_dropped` for the rung, and `verify.py` asserts the two are equal after rounding. On
step 4 it is the count of episodes with an emergency department encounter, which is deliberately
**not** the rung's `n_dropped` and is the reason this column exists. On step 16 it is the analytic
cohort, the same number as `denominators.analytic`, because the censoring reasons of 2.3 are counted
over the episodes that were kept rather than over any rung's drops.

**Three sets of rows in this file are partitions, and adding `n_denominator` is what makes declaring
them necessary.** Before the column, the file carried parts and no total, and nothing inside it could
be differenced. It now carries both, so the secondary-suppression rule of section 0 applies and the
partitions are named here rather than left for a reader to notice:

| Partition | Members, by `reason_detail` | Total |
|---|---|---|
| Step 12, which of the two baseline conditions bound | no valid baseline day; fewer than seven valid days; baseline span under 14 days | the step 12 `n_denominator`. The three are mutually exclusive and, by the rung's definition, exhaustive |
| Step 15, which truncation removed the episode | death; repeat spine operation | the step 15 `n_denominator`. A censor reason is single valued and the rung admits only these two |
| Step 16, the censoring reasons of 2.3 | none; death; repeat spine operation; CDR observation cutoff | the step 16 `n_denominator`, which is the analytic cohort. A censor reason is single valued and these are its four levels |

Each is declared in `row_partitions`, so one suppressed member forces a second. **They are row
partitions and not column ones**, and the distinction is a real one rather than bookkeeping:
`disclosure.export_violations`' `partitions` argument is a sequence of **column-name groups**,
checked across the cells of one row, and these three run **down** the `n_episodes` column across
several rows of one `step`. Declaring them in `partitions` would name three columns that do not
exist and refuse the file; leaving them undeclared would leave one suppressed member of a
three-member total recoverable by subtraction. `07_export.py` therefore carries the row-partition
declaration itself and 10.4 specifies it. Step 15 has two members, so suppressing one suppresses
that rung's whole breakdown; that is the rule working and not a defect in it. The forced cell carries the `secondary_suppression` sentence of 7.5 and not
the `cell_below_threshold` one, so a reader can tell a cell hidden for its own size from a cell
hidden to protect a sibling.

**The rows that are not partitions, stated so the distinction is not rediscovered as an argument.**
The five step 3 indication rows overlap by construction, since an episode may carry trauma and
malignancy and is counted under both, which is the whole reason the plan keeps those indications as
one rung and sends the breakdown here. The step 4 rows are the emergency department population itself
and three rescue routes that also overlap, and the routes do not exhaust it, because an episode with
an emergency department encounter and no rescue is exactly what the rung drops. Neither set sums to
its `n_denominator`, so neither is declared in `row_partitions`; declaring one would be a false claim
that the gate would then enforce.

```csv
step,slug,display_label,reason_detail,n_episodes,n_denominator,share_of_step_dropped
3,excl_trauma_malignancy_infection,Episodes after the nonelective-indication exclusions,Trauma diagnosis recorded in the 30 days before or on the index date,180,460,39%
4,excl_ed_encounter_not_elective,Elective episodes,Rescued by a degenerative index diagnosis despite the emergency department encounter,120,320,38%
15,excl_window_truncated_by_death_or_reoperation,Analytic cohort,Accrual window truncated by death,"20 or fewer, suppressed per All of Us dissemination policy",60,suppressed because the count behind it is suppressed
15,excl_window_truncated_by_death_or_reoperation,Analytic cohort,Accrual window truncated by a repeat spine operation,suppressed to protect a suppressed cell in the same total,60,suppressed because the count behind it is suppressed
```

The last two rows are the step 15 partition doing its work: the true `death` count is below the
floor, so the `repeat_spine_operation` count is suppressed beside it even though its own true count
is disclosable. Disclosing it would have handed a reader the denominator and one of that
denominator's two members, and the difference between them is the member that was hidden.

**4. `ledger_wear_availability_by_day.csv`.** Columns: `group_slug`, `display_label`, `group_order`,
`day`, `n_at_risk`, `n_valid_wear`, `share_valid_wear`. Seven columns. One row per group and
post-discharge day 1 to 90. `display_label` is the procedure group's label, from 7.1. **The absence rule of Figure 2 applies here too**: a day whose
`n_at_risk` fails `disclosable()` is absent from the file rather than written as a suppressed row,
for the reason 4.2 gives, which is that a row with no value is not a point on a curve and both the
renderer and the reader want the series to stop where the data stopped. The days that remain are
**disclosed**, and that is the published output of the suppression rule rather than a leak around
it: 10.2 exception 3 carries the argument and names this file's `day` column, so a `single_group`
run, where one series leaves `day` distinct in every row, exports instead of halting. The group set
is data-dependent and follows the collapse level.

**Its producer emits two more count columns and this file deliberately does not take them, which is a
decision on the record and not an omission.** `ledger_wear_by_day` in `build_all.sql` also computes
`n_analyzable` and `n_inpatient`. `07_export.py` drops both, the column count above is seven, and the
manifest row in 8.3 carries seven, so a pass-through widens the file past a number `verify.py`
already checks on arrival rather than slipping through unnoticed. The reasons, in the order that
decided it:

- **This file already prints its own denominator.** `n_at_risk` is the denominator of
  `share_valid_wear`, so section 8 rule 8, the rule that sent `n_total` into ledger 2 and
  `n_denominator` into ledger 3, is already satisfied here. `n_analyzable` and `n_inpatient` would be
  further numerators, not the missing denominator, so the argument that carries those two columns
  does not reach these.
- **`n_analyzable` would make an unwritten complement recoverable by subtraction.** An analyzable day
  is an at-risk day with enough wear minutes **and** a step count, while a valid-wear day needs only
  the wear minutes, so `n_valid_wear` less `n_analyzable` is the count of at-risk days with enough
  wear and no step record. That is a two-member partition of `n_valid_wear`, which this file already
  discloses, with one member written and the other not, which is the shape section 0 refuses.
  Publishing it safely would mean floor-testing a difference the producer never computes.
- **`n_analyzable` is already published where it is read.** Per group and post-discharge day it is
  the same quantity as `n_contributing` in `figure2_daily_activity.csv`, for every group that
  survives the collapse level, which is every group the figure plots. Carrying it here would restate
  at the same grain a number the bundle already has, which is the reasoning that kept the concept
  count out of ledger 1.
- **`n_inpatient` counts readmitted days, so it is small on most days by its nature.** The absence
  rule keys on `n_at_risk` and tests no second count, so most `n_inpatient` cells would arrive at
  `safe_export()` below the floor and would each have to be written as the 7.5 suppression sentence.
  A column that is a suppression sentence on most of its rows costs a width `verify.py` checks and
  reports almost nothing. That is a value argument and not a disclosure one, and the distinction is
  worth keeping straight: what a printed cell beside a suppressed one would say is what the
  suppression rule says everywhere else in this bundle, which is the same point 10.2 exception 3
  makes about the axis these rows sit on.

Both columns therefore stay inside the perimeter, where the modelling reads `is_analyzable` and
`is_inpatient` from `drd_daily` directly and neither is a wear-availability fact the supplement is
short of. If a reviewer asks for either, the fix is an amendment here and a re-export, with the
subtraction above resolved first, and never a column added at a call site.

**5. `ledger_matched_set_sizes.csv`.** Columns: `set_size`, `n_sets`, `n_cases`, `share_of_sets`. The
distribution of controls per case from the risk-set sampling of `ANALYSIS-PLAN.md` section 4.5. It is
written on every run and carries one row saying so when the tier permits no Arm A analysis, because
a file that is present and empty and a file that is absent are different claims and only one of them
is checkable. Every count is rounded and suppression-tested, and the secondary-suppression rule of
section 0 applies across `n_sets` rows, which partition a disclosed total: that is the fourth **row**
partition in the bundle and it is declared in `row_partitions` on the `n_sets` column, for the reason
the exclusion ledger's three are.

### 5.7 `tables-csv/table4_collider_comparison.csv`

The outcome rate in windows with and without a computable step signal, crude and standardized, from
fix 3 of `ANALYSIS-PLAN.md` section 4.4. **Three rows, on every run.**

| # | Column header | Content |
|---|---|---|
| 1 | `row_order` | `1` to `3`, contiguous |
| 2 | `Window group` | display label from 7.15 |
| 3 | `Episode-days at risk` | count token, or the suppression sentence; empty on the ratio row |
| 4 | `Acute-care events` | count token, or the suppression sentence; empty on the ratio row |
| 5 | `Crude rate per 1,000 episode-days` | `rate_per_1000_episode_days`, two decimals, or the suppression sentence |
| 6 | `Standardized rate per 1,000 episode-days` | the same, standardized to the recovery day bands, or the suppression sentence |

`key_columns`: `["Window group"]`. Rows, in order: `With a computable step signal`,
`Without a computable step signal`, `Rate ratio, without versus with`. The denominator is
`denominators.analytic_person_days`.

**Three rows by two rate columns is six rate cells, and 3.7 declares one key for each.** Column
5 traces to `gate.arm_a.estimates.collider_rate_with_signal`, `collider_rate_without_signal`
and `collider_rate_ratio_crude`, in row order; column 6 traces to
`collider_rate_with_signal_standardized`, `collider_rate_without_signal_standardized` and
`collider_rate_ratio_standardized`. Until 1.7.0 this sentence said "the four rate cells" and
named four keys, so the standardized rate of each window group was a printed cell tracing to
nothing; 3.7 now carries all six and says why the plan requires the per-group figure and not
only the ratio.

**Columns 3 and 4 are counts and do not come from that block.** The two window-group totals, the
episode-days at risk and the acute-care events in each condition, are counts rather than
estimates: they are floor-tested and `round20`-rounded like every other count cell, and a block
named `estimates` is the wrong home for them. They are supplied to the exporter beside the gate
block, keyed by window group, and 11.4 carries the open decision about which `results.json`
block should own them so that a consumer reading the bundle alone can reach them. The ratio row
leaves both cells empty, which is the not-applicable convention and not a suppression.

**Why this comparison gets an exhibit of its own, and why that exhibit is SUPPLEMENTARY.**
`ANALYSIS-PLAN.md` 4.4 states that requiring a computable ratio at the landmark conditions on a
collider, and it prescribes three fixes. Fix 1 is the co-primary exposure, which is now
`odds_of_no_computable_step_signal` in 3.7. Fix 2 is a weighted sensitivity, which is
`weights_without_lagged_wear` in the supplementary set of 3.6. Fix 3 is this comparison, and the
plan calls it "the direct evidence for or against the collider concern", computed on the
full-cohort day-indexed landmark panel and reported **twice**, crude and directly standardized.
Two versions of a rate in two window groups is four numbers and a ratio each way, and before 1.6.0
the bundle had nowhere to put any of them: the reader would have been told a collider was checked
and shown nothing. A three-row table is the cheapest honest home for it and it sits beside Table 3
because it is a property of the gate's own panel.

**It is printed in the supplement, and 1.6.0's placement in the primary set is corrected at
1.8.0.** `CLAUDE.md` section 2 rule 7 fixes the main text at exactly 3 figures and 3 tables and
sends everything beyond them to a supplement, and this table is a fourth. `tables.table4.exhibit_set`
reads `"supplementary"`. **The file is not deleted and must not be**: fix 3 is a prespecified
obligation of the plan, this table is the only place its six rate cells and two count pairs can
go, and a comparison the Methods says was run with no exhibit anywhere is the exact failure this
section was written to prevent. It keeps its three rows, its six columns, its `MANIFEST.csv` row,
its `results.json` block and its builder, on every run and at every tier. What moves is the page
it is printed on.

**The standardized column is suppressed unless every contributing band clears the floor**, and it
carries `contributing_n_below_threshold` when it does not. A directly standardized rate is a
weighted average of within-stratum rates, so it carries every stratum's numerator inside it, and a
day-level standardization over ninety post-discharge days is a weighted average of ninety event
counts that are individually far below the floor. Standardization therefore runs over the recovery
day bands of `ANALYSIS-PLAN.md` 4.4 rather than over the day grid, and the cell is written only when
every band contributing to it is itself disclosable. The crude column beside it is unaffected: it is
one numerator over one denominator, both rounded, and it is suppressed on its own terms alone.

**Neither rate is a causal estimate and the table says so.** `tables.table4.legend` states that the
comparison is unmatched and descriptive, that post-discharge day drives both wear and events, and
that the two versions are reported so that a reader who finds them different is shown by how much
rather than told which to believe. That is the plan's own wording obligation and it lives in the
legend because the legend is a printed string this document owns.

```csv
row_order,Window group,Episode-days at risk,Acute-care events,"Crude rate per 1,000 episode-days","Standardized rate per 1,000 episode-days"
1,With a computable step signal,"7,640",40,5.24,5.41
3,"Rate ratio, without versus with",,,1.74,1.62
```

**At tier 4 the file is still three rows.** `gate.arm_a.permitted` is `false` and no landmark panel
query is submitted, so all three rows carry empty count cells and the `not_permitted_by_tier`
sentence of 7.5 in both rate columns. Keeping the rows is the same choice 4.4 makes for the
event-centered curve and for the same reason: the three window groups are prespecified here, not
discovered in the data, so a file that shrank to one row would say the comparison was defined
differently rather than that the tier forbade it. It also makes "three rows" true on every run,
which is a number `MANIFEST.csv`, `tables.table4.rows` and the fixture can all pin exactly. It is a
weaker version of the same rule 5.6 applies to `ledger_matched_set_sizes.csv`, where the row set
**is** data-dependent and one row is therefore the only honest tier-4 shape.

---

## 6. Column-name discipline, and where display labels live

The export is machine-read locally and then rendered into user-visible strings. No `snake_case` token
may appear in user-visible text, so the two vocabularies must be kept apart by rule rather than by
care.

| Surface | Vocabulary | Printed? |
|---|---|---|
| `results.json` keys | machine tokens | no |
| `figures-csv/*.csv` column headers | machine tokens | no |
| `figures-csv/*.csv` machine-token columns, which are its slug columns and its small closed vocabularies (`slug`, `series_slug`, `group_slug`, `axis`, `render`, `kind`, `unit`, `reason`, `box_side`) | machine tokens | no |
| `figures-csv/*.csv` `display_label`, `block_label`, `reason_display`, `not_estimable_display` | display strings | yes |
| `tables-csv/*.csv` column headers | display strings | yes |
| `tables-csv/*.csv` every cell, except the seven machine-token columns below | display strings | yes |
| `tables-csv/*.csv` machine-token columns: `slug` and `variable`, `role`, `source_table`, `source_concept_set` in `ledgers-csv/`, `group_slug` in `ledgers-csv/ledger_wear_availability_by_day.csv`, and `Source key` in the Table 2 footer | machine tokens | no |
| `figures-csv/figure4_event_centered_activity.csv` `not_plotted_display` | display string | yes |
| `MANIFEST.csv` `description` | display string | audit only, but house prose rules still apply |

**`series_slug` and `box_side` were added to that row at 1.9.1, and the row is named for what
it holds rather than for how the names are spelled.** Until 1.9.1 it read "slug columns" and
listed the seven of Figures 1 to 3. Four of the seven were never slugs -- `axis`, `render`, `kind`
and `unit` are small closed vocabularies -- and the list was not revisited when 1.6.0 added Figure
4, so `series_slug` was outside it, `verify.py` skipped that column by silence rather than by rule,
and the ownership register said nothing about it either. That is the third time this document has
recorded a column with machine tokens and no owner, so 10.2 now carries the **machine-token column
sweep** that put every string column of every bundle file to both registers at once, and `box_side`
is what it found: a machine column on the ladder named by neither, quiet only because both its
values happen to carry no underscore.

**Every row of the table above is scoped by SURFACE, and the scope is load-bearing on exactly one
name.** `unit` is a machine token on a figure CSV, where it is a slug from 2.4 that no reader
meets, and a **display label** on `ledgers-csv/ledger_variable_provenance.csv`, where 7.14 owns the
printed string and the 10.2 register classes it that way. A consumer that reads the names out of
this table without the surfaces they are listed under skips a column that prints. The 10.2
ownership register is the way out of that, because it classifies a **(file, column) pair** rather
than a name and so cannot be ambiguous, and 11.1 already makes the register the thing `verify.py`
reads. 11.4 records the one consumer that still flattens these rows to a set of bare names.

**Decision: the display labels live in THIS CONTRACT, in the label table of section 7.**

Neither of the other two homes survives contact with six modules:

| Rejected home | Why |
|---|---|
| In the CSV alone | The perimeter would own the wording of every printed string. Fixing a label would cost a VM session and a re-export, so labels would be fixed in the renderer instead and drift from the export. |
| In the renderer alone | Six modules each build their own label map. A group named `Lumbar fusion` in Table 1 becomes `Fusion, lumbar` in Figure 3, and nothing detects it. |

The mechanism that makes one home work in two places:

1. Section 7 is the authority. A label exists there or it does not exist.
2. `07_export.py` holds a transcribed copy as `LABELS: dict[str, str]` and emits every
   `display_label`, `column_header`, `block_label` and `reason_display` **by lookup**, never by
   f-string. A column header carrying an n is `f"{LABELS[slug]} (n = {n:,})"`, which is the only
   permitted composition and is itself specified here.
3. `local/ledger.py` holds the same transcribed copy as `LABELS: dict[str, str]`, and is the only
   local module allowed to define one. `figures.py`, `tables.py`, `manuscript.py` and `make_strobe.py`
   import it.
4. `verify.py` asserts three things and exits non-zero on any of them:
   - every `slug` appearing anywhere in the bundle has an entry in `LABELS`;
   - every `display_label` in the bundle is **character-identical** to `LABELS[slug]`;
   - no printed string in the bundle matches `\b[a-z0-9]+_[a-z0-9_]+\b` or contains U+2014 or U+2212.

The third assertion is what catches a slug that leaked into a caption, which is the failure this rule
exists to prevent.

**And it is why the row above had to be corrected rather than left as a simplification.** Until this
version this table said, without qualification, that every cell of every `tables-csv` file is a
display string, and that is false for seven columns across four files. Three of them are
`ledgers-csv/` files, which are `table-csv` by `kind` because a ledger is a table of strings, and
the fourth is the Table 2 footer, whose `Source key` column 5.3 **requires** to be a dotted
`results.json` path. Run against the bundle as it stands, the snake_case assertion above would have fired on
`excl_trauma_malignancy_infection` in the exclusion ledger's `slug` column, on `baseline_steps`,
`covariate` and `features` in the provenance ledger, on `cervical_decompression` in the
wear-availability ledger's `group_slug` column, and on `debt.model_fit.icc` in the footer, and
it would have fired on arrival, after the export, with the bundle already out of the perimeter. The
seven are enumerated in the row above, they are classed **machine token** in the 10.2 ownership
register together with the exempted columns, and the register is what `verify.py` reads to decide
which columns the third assertion skips. The general rule is unchanged: a string a reader sees is a
display string, and a string a machine reads is declared as one, by name, in one place.

**The count read five until 1.9.1 and it was wrong twice, in the two different ways a hand count
goes wrong.** It omitted `source_concept_set`, which the row above already named, so the prose
undercounted its own table; and it omitted `group_slug` on
`ledgers-csv/ledger_wear_availability_by_day.csv`, which no row of this section named at all, so
the table undercounted the bundle. The second is the `series_slug` defect on a ledger instead of a
figure and it was found the same way, by the 10.2 machine-token column sweep rather than by a
reader. Neither number is counted by hand again: 10.2's ownership register classifies a **(file,
column) pair**, this sentence is checked against the register's own count of the pairs it classes
machine token on a `tables-csv/` or `ledgers-csv/` file, and the row above is checked against the
same set. A count in prose that no register can be compared with is the shape of both errors.

---

## 7. The label table

Every string below is printed verbatim. Sentence case. No terminal period unless the entry is a
sentence.

### 7.1 Procedure groups

| order | slug | display label |
|---|---|---|
| 1 | `cervical_decompression` | Cervical decompression |
| 2 | `cervical_fusion` | Cervical fusion |
| 3 | `lumbar_decompression` | Lumbar decompression |
| 4 | `lumbar_fusion` | Lumbar fusion |
| 5 | `all_groups` | All groups |
| collapse level 2 only | `fusion` | Fusion |
| collapse level 2 only | `decompression` | Decompression |

### 7.2 Attrition rungs

Nineteen rungs, transcribed character for character from `ANALYSIS-PLAN.md` section 2.6. Every
string in the second and third columns is printed: the display label names the box of survivors on
the ladder spine, the reason display is the sentence in the right-hand exclusion box. `verify.py`
compares both by character equality, so neither is paraphrased, re-cased or re-punctuated at render
time.

| step | slug | display label (ladder box) | reason display (exclusion box) |
|---|---|---|---|
| 1 | `program_participants` | Participants in the Controlled Tier release | No qualifying spine procedure concept in the electronic health record |
| 2 | `episode_construction` | Spine surgical episodes | Same-day qualifying procedure records collapsed into one episode; operations on different dates stay separate episodes until step 13 |
| 3 | `excl_trauma_malignancy_infection` | Episodes after the nonelective-indication exclusions | Trauma, spinal cord injury, malignancy, metastatic disease or spinal infection recorded in the 30 days before or on the index date |
| 4 | `excl_ed_encounter_not_elective` | Elective episodes | Emergency department encounter immediately before the index operation, with no coding evidence of an elective episode |
| 5 | `excl_prior_operation_90_days` | Episodes with no prior operation within 90 days | Prior qualifying spine operation within 90 days of the index episode |
| 6 | `excl_simultaneous_cervical_lumbar` | Episodes at a single anatomic region | Simultaneous cervical and lumbar procedure |
| 7 | `excl_region_unspecified_only` | Episodes with an established anatomic region | Procedure coding that cannot establish an anatomic region |
| 8 | `excl_thoracic_only` | Cervical or lumbar episodes | Thoracic-only operation, outside the target population |
| 9 | `excl_add_on_code_only` | Episodes defined by a primary procedure code | Add-on and instrumentation codes only, with no primary procedure code |
| 10 | `excl_missing_discharge_date` | Episodes with a recorded discharge | No recorded discharge date for the index admission |
| 11 | `excl_no_wearable_data` | Wearable-linked spine episodes | No Fitbit activity record linked to the participant |
| 12 | `excl_inadequate_baseline_wear` | Episodes with adequate preoperative baseline wear | Fewer than 7 valid wear days in postoperative days -30 to -8, or a span under 14 calendar days |
| 13 | `excl_not_first_eligible_episode` | First eligible episode per participant | A later operation by a participant whose first eligible episode is already in the cohort |
| 14 | `excl_no_computable_post_discharge_window` | Episodes with a computable post-discharge day 1 to 35 window | No analyzable day inside post-discharge days 1 to 35 before censoring |
| 15 | `excl_window_truncated_by_death_or_reoperation` | Analytic cohort | Accrual window truncated by death or by a repeat spine operation |
| 16 | `analytic_cohort` | Analytic cohort | |
| 17 | `events_identified` | Acute-care events through day 90 | |
| 18 | `excl_event_without_computable_landmark` | Analyzable acute-care events | Event on post-discharge day 1 to 4, with no computable proximal window |
| 19 | `events_analyzable` | Analyzable acute-care events | |

Steps 15 and 16 share the label "Analytic cohort", and steps 18 and 19 share "Analyzable acute-care
events", because an exclusion rung's display label names the box of survivors below it. That is not a
transcription slip and a renderer must not de-duplicate it.

The three terminal and conversion rungs carry an empty reason display. Empty means the concept does
not apply, per the not-applicable convention of section 4; it never means suppressed.

### 7.3 Contrasts

| slug | display label |
|---|---|
| `fusion_vs_decompression` | Fusion versus decompression |
| `lumbar_vs_cervical` | Lumbar versus cervical |
| `region_by_fusion_interaction` | Region by fusion interaction |
| `fusion_vs_decompression_cervical` | Fusion versus decompression, cervical |
| `fusion_vs_decompression_lumbar` | Fusion versus decompression, lumbar |

### 7.4 Arms

| slug | display label |
|---|---|
| `recovery_debt` | Recovery debt |
| `early_warning` | Early warning |

### 7.5 Suppression reasons

| slug | display sentence |
|---|---|
| `cell_below_threshold` | 20 or fewer, suppressed per All of Us dissemination policy |
| `numerator_suppressed` | suppressed because the count behind it is suppressed |
| `contributing_n_below_threshold` | 20 or fewer contributors, suppressed |
| `secondary_suppression` | suppressed to protect a suppressed cell in the same total |
| `not_estimable_cell_size` | not estimable (cell size) |
| `not_estimable_convergence` | not estimable (model did not converge) |
| `not_estimable_data_unavailable` | not estimable (data not available) |
| `not_permitted_by_tier` | not permitted at the feasibility tier reached |
| `no_crossing_within_range` | no crossing within the prespecified range |
| `not_estimable_separation` | not estimable (separation) |

The first sentence is the one the plan names for the unprintable gate count, and it is used verbatim
wherever a count is hidden, so a reader meets one sentence rather than five phrasings. It reads "20
or fewer", not "fewer than 20", because a count of exactly 20 is suppressed
(`ANALYSIS-PLAN.md` section 8 rules 1 and 2) and a sentence that says "fewer than 20" over a
suppressed 20 is simply false.

`not_estimable_data_unavailable` exists for one prespecified case: `ANALYSIS-PLAN.md` section 9.1
requires the two device-provenance subgroup rows to print "not estimable (data not available)" if
the release does not distinguish participant-owned from program-provided devices. That is a printed
string, so under R5 it needs an entry here or the bundle fails the label check on arrival.

**`not_estimable_separation` exists because a quasi-separated fit converges.** `ANALYSIS-PLAN.md`
section 4.9 refuses any Arm A logistic fit carrying a coefficient whose absolute value exceeds
`MAX_ABS_COEFFICIENT = 10`, and prescribes the printed sentence and the slug: the row prints "not
estimable (separation)". The reason exists because **no existing one could carry that fit without
saying something false**. It did not fail on cell size, the data were available, the tier
permitted the analysis, and it **converged**: the relative-log-likelihood criterion declared it
converged while the coefficient ran off toward infinity, which is exactly what makes
quasi-separation dangerous and exactly why `not_estimable_convergence` would have been a false
sentence rather than a near-enough one. The plan owns the rule and the ceiling; this section owns
the slug and the sentence, and 4.9 says so in terms: the slug "is not this file's to own" and
"belongs to the suppression-reason vocabulary of `prespecification/EXPORT-CONTRACT.md` section
7.5". It is not a member of any of the five vocabularies the plan owns, so the plan's own
set-equality assertions are untouched by it. `06_analysis_gate.py` has emitted it since it was
written, and until this version `07_export.py` halted by name on it, which was the correct
behaviour for a reason with nothing to print and is why the gap was dated in 11.4 rather than
worked around.

**It is the fourth `not_estimable_*` reason and the tenth row, and those are two different
facts.** 4.9 places it "beside `not_estimable_cell_size`, `not_estimable_convergence` and
`not_estimable_data_unavailable`", which is a claim about what kind of reason it is, and that
claim is made here in words. The **row** is appended at the bottom, which is where the ninth
went and where `disclosure.py` has already transcribed this one. That module owns
`SUPPRESSION_REASONS` as an **ordered** tuple under 11.3 and
`tests/test_disclosure.py::test_the_suppression_sentences_are_the_contract_s_own` parses this
table and asserts ordered equality against it, so the row order here is load-bearing rather
than cosmetic: re-sorting this table to group the four `not_estimable_*` sentences would turn
that test red and move a line in a module this document does not own, for a grouping the prose
already states. A vocabulary this document transcribes grows at the bottom.

**`no_crossing_within_range` exists because the absence of a number is sometimes the result.** It is
the reason on `debt.delta_shift.tipping_point_point_estimate` and
`debt.delta_shift.tipping_point_interval` when `crossed_within_grid` is `false`, which is when the
primary contrast holds its sign at every `delta` out to the end of the prespecified extension at
4.0. Nothing failed there. The grid was walked, the extension was used, and the contrast did not
cross, which is the **stronger** finding and the one a reader should meet as a finding. Before this
slug existed the only sentence available was `not_estimable_data_unavailable`, which says the data
were not there; a footer row reading "not estimable (data not available)" beside a Manski bound and
an intraclass correlation reads as a gap in the analysis rather than as its result, and a reader
comparing two studies would score the robust one as the incomplete one. This is a **suppression
reason** in the mechanical sense only, because the node shape is how a value-free result is carried
in this bundle; it is not a disclosure event and it never enters `suppressed.by_reason` under an
`R1` rule. `07_export.py` files it in `suppressed.entries` with `"rule": "no crossing"`, so the
count in `suppressed.n_entries` still ties out and nothing is silently absent.

### 7.6 Units, display form

| unit slug | display, singular | display, in a column header |
|---|---|---|
| `activity_days` | activity day | Activity days |
| `thousand_steps` | thousand steps | Thousand steps |
| `normalized_activity` | normalized activity | Normalized activity |
| `steps` | step | Steps per day |
| `days` | day | Days |
| `percent` | percent | Percent |
| `absolute_risk_percent` | percent | Absolute risk, percent |
| `odds_ratio` | odds ratio | Odds ratio |
| `rate_ratio` | rate ratio | Rate ratio |
| `rate_per_1000_episode_days` | per 1,000 episode-days | Events per 1,000 episode-days |
| `hours` | hour | Hours |
| `minutes` | minute | Minutes |
| `count` | | Episodes |
| `dimensionless` | | |
| `information_criterion` | | Akaike information criterion |

### 7.7 Estimator rungs

See the table in section 3.1.1. Those display strings are label-table entries.

### 7.8 Sensitivity rows

| slug | display label |
|---|---|
| `pod_anchored_window` | Postoperative day 8–42 window |
| `inpatient_days_censored` | Inpatient days censored |
| `complete_window_direct_regression` | Complete windows, direct regression |
| `observation_weighted` | Weighted for observation |
| `delta_shift_tipping_point` | Delta-shift tipping point |
| `wear_definition_s1` | Wear day at 40% heart-rate adherence |
| `wear_definition_s2` | Wear day at 10 hours plus 100 steps |
| `wear_definition_s3` | Wear day at 8 hours |
| `wear_definition_s4` | Wear day at 12 hours |
| `baseline_window_60_15` | Baseline 15–60 days before surgery |
| `baseline_window_30_1` | Baseline 1–30 days before surgery |
| `device_change_excluded` | Device change excluded |
| `baseline_floor` | Baseline floor at 1,000 steps per day |
| `debt_untruncated` | Debt not truncated at zero |

**The ten supplementary rows of 3.6 carry printed labels too.** Section 6 makes section 7 the sole
authority for a printed string, so they are listed here rather than only in 3.6, and a supplementary
exhibit that names one of them prints the string below. They are a **separate** table on purpose:
the set-equality assertion reads the fourteen-row table above and nothing else, and none of these
ten supplementary rows has a key in `results.json.sensitivity` or a row in `figure3_forest.csv`.

| slug | display label |
|---|---|
| `baseline_steps_adjusted` | Baseline steps adjusted |
| `bmi_multiply_imputed` | Body mass index multiply imputed |
| `weights_without_lagged_wear` | Observation weights without lagged wear |
| `junctions_mirrored` | Junction codes mirrored |
| `cervical_fusion_gap_reclassified` | Cervical fusion gap reclassified |
| `cervical_decompression_gap_stated` | Cervical decompression gap |
| `four_group_model` | Four-group model |
| `truncated_assigned_max_debt` | Truncated windows at maximal debt |
| `fusion_status_non_add_on_only` | Fusion status without add-on codes |
| `baseline_weekday_weekend_split` | Separate weekday and weekend baselines |

### 7.9 Gate stages

| letter | slug | display label |
|---|---|---|
| A | `stage_a_qualifying_episodes` | Qualifying spine episodes by procedure group |
| B | `stage_b_baseline_wear` | Episodes with at least 7 valid baseline days |
| C | `stage_c_computable_window` | Episodes with a computable post-discharge window |
| D | `stage_d_events` | First acute-care events through day 90 |
| E | `stage_e_computable_ratio` | Events with a computable proximal step ratio |
| F | `stage_f_events_by_stratum` | Events by anatomic region and fusion status |

Stage D component labels: `First emergency department visits`, `Readmissions`, `Composite events`.

### 7.10 Tiers

| index | slug | display label | band | verbatim permitted claim |
|---|---|---|---|---|
| 1 | `full_model` | Full detection model | 100 or more | Detection performance may be reported as a performance estimate |
| 2 | `step_first_exploratory` | Step-first exploratory model | 50–99 | Association and exploratory performance, explicitly not a prediction tool |
| 3 | `event_centered_only` | Event-centered association only | 20–49 | Association only. No prediction-tool claim of any kind |
| 4 | `no_early_warning` | No early-warning modeling | fewer than 20 | Feasibility statement only, with the count suppressed |

The permitted-claim column is quoted from `ANALYSIS-PLAN.md` section 1.2 and copied into
`gate.tier.permitted_claim_verbatim` unaltered. It is not paraphrased, shortened or softened. The
plan's separate "Permitted analysis" column is copied into `gate.tier.permitted_analysis_verbatim`
by the same rule.

**Tiers 1 and 2 switch the exhibit set.** `ANALYSIS-PLAN.md` section 9.5 replaces Figure 2, Figure 3,
Table 1, Table 2 and Table 3 wholesale when the event count reaches 50. This contract specifies the
primary exhibit set, which is what tiers 3 and 4 print. If `gate.tier.exhibit_set` is `"alternate"`,
the contract is amended before the export runs; the exporter must not silently emit the primary
column set with alternate content. `verify.py` asserts `tier.exhibit_set == "primary"` for schema
version 1.x.

### 7.11 Block labels and other printed strings

| slug | display |
|---|---|
| `block_contrasts` | Primary and key secondary contrasts |
| `block_robustness` | Robustness of the primary contrast |
| `block_subgroups` | Subgroups |
| `subgroup_age_lt_65` | Younger than 65 years |
| `subgroup_age_ge_65` | 65 years or older |
| `subgroup_female` | Female sex assigned at birth |
| `subgroup_male` | Male sex assigned at birth |
| `subgroup_bmi_lt_30` | Body mass index under 30 |
| `subgroup_bmi_ge_30` | Body mass index 30 or above |
| `subgroup_device_byod` | Participant-owned device |
| `subgroup_device_wear` | Program-provided device |

### 7.12 Exclusion and censoring reason details

`ledgers-csv/ledger_exclusion_and_censoring_reasons.csv` carries **one prespecified sentence per row**
in its `reason_detail` column, which is the ground 5.6 states it on and the ground 10.2 exempts it
from the near-unique class on. The sentences are here, because section 6 makes this section the sole
authority for a printed string, and an exemption whose justification points at a table that does not
exist is not an exemption: before contract 1.5.0 this table was absent and `pipeline/03_cohort.py`
carried a second copy of it, unowned, to have anything to print.

The `reason_detail` slug is the value the `ledger_exclusion_reasons` stage of
`pipeline/build_all.sql` emits, read out of that stage rather than invented here. **Twenty pairs,
which is every pair the producer emits.** The rung slug beside each is the rung the row is counted
under, so a pair that is not a rung of 7.2 is visible in this table rather than only at run time, and
the order is the file's own `sort_keys`, `step` then `reason_detail`. `07_export.py` writes the
sentence by lookup on the pair `(step, reason_detail)` and never by f-string; a slug the producer adds
without an amendment here has nothing to print, and that is the intended failure.

| step | rung slug | `reason_detail` | display sentence |
|---|---|---|---|
| 3 | `excl_trauma_malignancy_infection` | `malignancy` | Malignancy recorded in the 30 days before or on the index date |
| 3 | `excl_trauma_malignancy_infection` | `metastatic_disease` | Metastatic disease recorded in the 30 days before or on the index date |
| 3 | `excl_trauma_malignancy_infection` | `spinal_cord_injury` | Spinal cord injury recorded in the 30 days before or on the index date |
| 3 | `excl_trauma_malignancy_infection` | `spinal_infection` | Spinal infection recorded in the 30 days before or on the index date |
| 3 | `excl_trauma_malignancy_infection` | `trauma` | Trauma diagnosis recorded in the 30 days before or on the index date |
| 4 | `excl_ed_encounter_not_elective` | `ed_encounter_present` | Emergency department encounter ending on the index date or within the 2 days before it |
| 4 | `excl_ed_encounter_not_elective` | `rescue_degenerative_index` | Rescued by a degenerative index diagnosis despite the emergency department encounter |
| 4 | `excl_ed_encounter_not_elective` | `rescue_degenerative_outpatient_90d` | Rescued by an outpatient degenerative spine diagnosis in the 90 days before the index date |
| 4 | `excl_ed_encounter_not_elective` | `rescue_elective_coded` | Rescued by elective or scheduled wording on the index admission |
| 12 | `excl_inadequate_baseline_wear` | `baseline_span_under_14_days` | Seven or more valid wear days, spanning under 14 calendar days |
| 12 | `excl_inadequate_baseline_wear` | `fewer_than_seven_valid_days` | Between 1 and 6 valid wear days in the baseline window |
| 12 | `excl_inadequate_baseline_wear` | `no_valid_baseline_day` | No valid wear day anywhere in the baseline window |
| 14 | `excl_no_computable_post_discharge_window` | `no_analyzable_day_in_window` | No analyzable day inside post-discharge days 1 to 35 |
| 14 | `excl_no_computable_post_discharge_window` | `not_at_risk_in_window` | Not at risk on any day of post-discharge days 1 to 35 |
| 15 | `excl_window_truncated_by_death_or_reoperation` | `death` | Accrual window truncated by death |
| 15 | `excl_window_truncated_by_death_or_reoperation` | `repeat_spine_operation` | Accrual window truncated by a repeat spine operation |
| 16 | `analytic_cohort` | `censoring_cdr_observation_cutoff` | Censored at the end of the release observation period |
| 16 | `analytic_cohort` | `censoring_death` | Censored at death |
| 16 | `analytic_cohort` | `censoring_none` | Followed to the end of the accrual window with no censoring |
| 16 | `analytic_cohort` | `censoring_repeat_spine_operation` | Censored at a repeat spine operation |

**Four of these twenty are already fixed by the worked example of 5.6 and are character-identical to
it**, deliberately: `(3, trauma)`, `(4, rescue_degenerative_index)`, `(15, death)` and
`(15, repeat_spine_operation)` are the four sentences that section's example CSV prints, and this
table does not restate them in a second phrasing. A second phrasing of any sentence above, anywhere
in this project, is an error to be corrected against this table.

**The step 3 and step 4 rows overlap and the step 12, 15 and 16 rows do not**, which is a property of
the rows and not of the sentences, and 5.6 is where it is declared, in `partitions`. Nothing in this
table changes it. What this table adds is that every one of the twenty sentences is fixed before any
count exists, so a reason cannot be reworded after its count is seen.

### 7.13 Analysis variables, for the provenance ledger

`ledgers-csv/ledger_variable_provenance.csv` carries a `display_label` column, and it is the one
`display_label` in the bundle whose strings section 7 did not own before contract 1.5.0. Section 6
makes this section the authority for a printed string and `verify.py` asserts every `display_label` in
the bundle is character-identical to its entry here, so an unowned one fails on arrival. The
`derivation` column is exempted by 10.2 on the same specification-value ground and is owned here for
the same reason.

The `variable` token is the value the `ledger_variable_missingness` stage of `pipeline/build_all.sql`
emits, read out of that stage rather than invented here. **Twelve variables, which is every variable
the producer emits**, in the file's own `sort_keys` order, `variable`. The token itself is machine-read
and never printed; the two strings beside it are printed verbatim.

| `variable` | display label | derivation |
|---|---|---|
| `age_at_index` | Age at the index operation | Days from the recorded date of birth to the index operation date, divided by 365.25 |
| `baseline_steps` | Preoperative baseline steps per day | Median steps per day over the valid wear days of the baseline window |
| `bmi` | Body mass index | The nearest recorded body mass index in the 365 days before the index date, inside a plausibility window of 10 to 80 kg per square metre |
| `charlson_score` | Charlson comorbidity score | Quan's ICD-10 Charlson categories over the 365 days before the index date, weighted and summed under the three hierarchy rules |
| `daily_deficit` | Daily activity deficit | One less the normalized activity of an analyzable day inside the accrual window |
| `device_family` | Device family | The modal Fitbit device family over the 30 days before the index date, ties broken by the most recent record and then by family name |
| `ethnicity_concept_id` | Ethnicity | The person table's ethnicity concept, taken as recorded |
| `los_days` | Length of stay | Days from the start to the end of the index admission visit |
| `procedure_group` | Procedure group | Anatomic region crossed with fusion status, one of the four groups of section 2.4 of the analysis plan |
| `r72` | Proximal activity ratio at 72 hours | Median steps of the proximal window over the participant's own baseline steps |
| `race_concept_id` | Race | The person table's race concept, taken as recorded |
| `sex_at_birth` | Sex assigned at birth | The person table's sex-at-birth concept, mapped to female, male, or other or unknown |

**Three of these twelve are already fixed by the worked example of 5.6 and are character-identical to
it**: `baseline_steps`, `daily_deficit` and `r72` are the three rows that section's example CSV
prints, label and derivation alike.

**Three of the twelve are expected to report zero missing, and only these three**: `los_days`, because
rung 10 removed every episode with no discharge date; `baseline_steps`, because rung 12 removed every
episode with no baseline; and `procedure_group`, because it is null only for the episodes rungs 6, 7
and 8 removed. A zero there is a true statement about the cohort. A zero anywhere else in the column
is a finding, not a formatting question.

### 7.14 Analysis-variable units and missing handling

`ledgers-csv/ledger_variable_provenance.csv` carries two more printed columns beside the
`display_label` and `derivation` that 7.13 owns, and until contract 1.6.0 section 7 owned neither.
`unit` is the printed unit of the variable and `missing_handling` is one prespecified sentence per
variable saying what the analysis does with a missing value. Both are written verbatim into a cell,
so section 6 requires this section to be their authority and `verify.py`'s character-equality
assertion needs a table to compare them against; without one it passes vacuously on twenty-four
strings, which is the same defect 7.12 and 7.13 closed in the same file at 1.5.0.

**Twelve variables, which is every variable the producer emits**, in the file's own `sort_keys`
order, `variable`. The `unit` column is **not** a slug from 2.4 and does not need to be: 2.4 fixes
the unit of a value node in `results.json`, while this column names the unit of the **variable** as
a reader of the supplement meets it, and five of the twelve are categorical and carry the empty
string, which is the not-applicable convention of section 4 and never means suppressed.

| `variable` | unit | missing handling |
|---|---|---|
| `age_at_index` | Years | Complete case; the release records a date of birth for every participant |
| `baseline_steps` | Steps per day | Complete case; an episode without an adequate baseline is excluded at step 12 |
| `bmi` | Kilograms per square metre | A missing indicator is carried beside the substituted value, so the model never reads a substitution as an observation; multiple imputation is a supplementary sensitivity row |
| `charlson_score` | Weighted score | An absent category scores zero and a missing indicator records that no qualifying condition record was found at all |
| `daily_deficit` | Normalized activity | Not imputed; a missing day is never read as a zero deficit and the observation weights of 3.7 do the work |
| `device_family` | | An unclassifiable or absent device model takes the other or unknown level, which is counted rather than dropped |
| `ethnicity_concept_id` | | Reported as its own level; no ethnicity is imputed |
| `los_days` | Days | Complete case; an episode with no recorded discharge date is excluded at step 10 |
| `procedure_group` | | Complete case; steps 6, 7 and 8 remove every episode whose anatomic region or fusion status cannot be established |
| `r72` | Normalized activity | Not imputed; an event with no computable proximal window is excluded at step 18 |
| `race_concept_id` | | Reported as its own level; no race is imputed |
| `sex_at_birth` | | Reported as its own level, including other or unknown; no sex is imputed |

**Three of the twelve sentences are already fixed by the worked example of 5.6 and are
character-identical to it**: `baseline_steps`, `daily_deficit` and `r72`, whose `unit` and
`missing_handling` cells that example prints. A second phrasing of any sentence above, anywhere in
this project, is an error to be corrected against this table, which is the rule 7.12 states for its
own twenty.

**The three variables expected to report zero missing are the three 7.13 names**, and this table is
where the reason is written as a sentence rather than as a note: `baseline_steps`, `los_days` and
`procedure_group` each say which rung removed the episodes that would otherwise have been missing.
A zero in `n_missing` on any other row is a finding.

### 7.15 The gate exhibits' printed strings

The two exhibits added at contract 1.6.0 print strings of their own, and so do the rows of Table 3
part B, which 5.5 now fills one row per `gate.arm_a.estimates` key rather than leaving to the
exporter to phrase. Section 6 makes this section the authority for all of them.

**Twenty strings.** The first fifteen print in the `Quantity` column of
`tables-csv/table3_gate_part_b.csv`, the next two are the two series of
`figures-csv/figure4_event_centered_activity.csv`, and the last three are the `Window group` rows of
`tables-csv/table4_collider_comparison.csv`.

| slug | display label | where it prints |
|---|---|---|
| `gate_tier_reached` | Feasibility tier reached | Table 3 part B |
| `gate_permitted_claim` | Permitted claim | Table 3 part B |
| `adjusted_odds_per_lower_step_ratio` | Adjusted odds per lower step ratio | Table 3 part B |
| `unadjusted_odds_per_lower_step_ratio` | Unadjusted odds per lower step ratio | Table 3 part B |
| `odds_of_no_computable_step_signal` | Odds with no computable step signal | Table 3 part B |
| `negative_control_window` | Negative control window | Table 3 part B |
| `median_lead_time` | Median lead time | Table 3 part B |
| `matched_set_size` | Controls per case | Table 3 part B |
| `absolute_risk_translation` | Absolute risk at the reference step ratio | Table 3 part B |
| `collider_rate_with_signal` | Event rate with a computable step signal | Table 3 part B |
| `collider_rate_without_signal` | Event rate without a computable step signal | Table 3 part B |
| `collider_rate_with_signal_standardized` | Event rate with a computable step signal, standardized | Table 3 part B |
| `collider_rate_without_signal_standardized` | Event rate without a computable step signal, standardized | Table 3 part B |
| `collider_rate_ratio_crude` | Rate ratio, crude | Table 3 part B |
| `collider_rate_ratio_standardized` | Rate ratio, standardized to recovery day bands | Table 3 part B |
| `event_case` | Cases | Figure 4 |
| `matched_control` | Matched controls | Figure 4 |
| `collider_with_signal` | With a computable step signal | Table 4 |
| `collider_without_signal` | Without a computable step signal | Table 4 |
| `collider_rate_ratio_row` | Rate ratio, without versus with | Table 4 |

The thirteen estimate-key labels are new to this section and not new to the bundle: Table 3 part B
printed a `Quantity` for each of the five keys 3.7 already carried, and this document owned none of
those five strings, so the exporter composed them and `verify.py`'s label assertion had nothing to
compare them against. Adding six keys without adding a label table would have widened an unowned
surface rather than closing it. The two 1.7.0 keys arrive with their labels in the same
edit, for the same reason: **there is one row of this table for every key of
`gate.arm_a.estimates`, and a key added without one is an unowned printed string.**

---

## 8. The md5 discipline

### 8.1 What the md5 is computed over

The **bytes of the written file**, read back from disk in binary after the write completes:

```python
md5 = hashlib.md5(path.read_bytes()).hexdigest()      # 32 lower-case hex characters
```

Never over an in-memory frame, never over a re-serialization, never over a normalized copy. The bytes
that cross the boundary are the bytes that get hashed, because the md5 exists to catch a transcription
slip in transfer, and a hash of anything other than the transferred bytes cannot do that.

### 8.2 What makes the bytes stable

Two runs of the same code against the same data must produce byte-identical CSVs. `07_export.py`
self-tests this by writing the bundle twice into two temporary directories and diffing the bytes.

For every CSV:

```python
from disclosure import FLOAT_FORMAT            # "%.6g". The module owns it; nobody retypes it.

df.to_csv(
    path,
    index=False,                 # a pandas index would emit an unnamed first column
    lineterminator="\n",         # CRLF on any platform would change every md5
    float_format=FLOAT_FORMAT,   # "%.6g", imported from disclosure.py, never retyped
    encoding="utf-8",
    na_rep="",                   # a NaN must never print as "nan"
    quoting=csv.QUOTE_MINIMAL,
    quotechar='"',
)
```

| Requirement | Reason |
|---|---|
| `index=False` | An index column is an unnamed column, and `load_table` would fail its column check on it |
| Explicit column order, taken from this contract | A dict-ordering change would silently reorder columns and change every md5 |
| Explicit row sort, on the declared `sort_keys` | A groupby-ordering change would reorder rows |
| `float_format="%.6g"` | Six significant figures is well beyond every display precision in section 2.4, so it never loses a printed digit, and an explicit format removes shortest-repr and platform differences. `%.6g` rather than `%.6f` because both are equally deterministic and therefore equally safe for md5 stability, while `%.6f` flattens anything below 1e-6 to `0` and silently turns a small value into a zero |
| Integer columns written as integers | `astype("int64")` before writing, so a count never appears as `340.0` |
| No timestamp inside any CSV | A timestamp makes the bytes differ every run and destroys the two-run check |

For `results.json`:

```python
json.dump(_round_floats(obj, 6), fh, indent=2, sort_keys=True, ensure_ascii=False)
fh.write("\n")
```

`_round_floats` walks the object and rounds every float to 6 decimals before dumping, so a value
produced in R and a value produced in Python serialize identically. `sort_keys=True` fixes key order.
`ensure_ascii=False` keeps the en-dash a single character rather than an escape, which matters because
the display strings are compared character by character against the label table.

`results.json` carries `meta.generated_utc` and therefore differs between runs by design. Its md5
checks transcription, not determinism. Every CSV in the bundle is byte-identical across two runs, and
`checks.csv_bytes_stable_across_two_runs` records that the exporter verified it.

### 8.3 `MANIFEST.csv`

One row per exported file. **Sixteen data rows.** Fixed row order: `results.json`, then the four
figure CSVs in figure order, then the six table CSVs in table order, then the five ledger CSVs in
the order of section 5.6. No timestamp column, so `MANIFEST.csv` is itself byte-stable.

The columns are `disclosure.MANIFEST_COLUMNS`, in that order, and they are the keys of the dict
`safe_export()` returns for each file. `07_export.py` assembles the manifest by collecting sixteen
returned rows and writing them in the fixed order above; it does not build a row by hand.

| Column | Type | Meaning |
|---|---|---|
| `file` | string | path relative to the `results` directory, forward slashes |
| `kind` | string | `results-json`, `figure-csv` or `table-csv`. These are `disclosure.MANIFEST_KINDS` and the set does not grow; a ledger CSV is `table-csv` |
| `exhibit` | string | `Figure 2`, `Table 1`, or empty for `results.json` and for every ledger CSV |
| `md5` | string | 32 lower-case hex |
| `n_rows` | integer | data rows, excluding the header. For `results.json`, the number of value nodes: objects carrying a `display` key. |
| `n_columns` | integer | columns. For `results.json`, `0`. |
| `min_disclosed_count` | integer | the smallest count value written in the file, or empty when the file writes no count |
| `n_suppressed_cells` | integer | cells written as `SUPPRESSED`, or, **in a table CSV only**, as a suppression sentence of 7.5. The kind decides: in a table CSV the sentence is the cell and stands where the number would have gone, so it is a hidden value; in a figure CSV a sentence lives in a declared companion column (`not_plotted_display`, `not_estimable_display`) beside a cell already written as `SUPPRESSED`, so counting it would count one hidden value twice |
| `description` | string | one line, at most 120 characters, house prose rules apply |

`MANIFEST.csv` does not contain a row for itself. Its own md5 is written to `MANIFEST.md5` as a
single line of 32 hex characters followed by a newline and nothing else. The two-file arrangement
exists because a manifest that hashed itself would be circular.

```csv
file,kind,exhibit,md5,n_rows,n_columns,min_disclosed_count,n_suppressed_cells,description
results.json,results-json,,6f1a9c4e2b7d08153a6c9f4b2e8d0714,412,0,40,12,"Every scalar the manuscript cites, with its display string and its suppression state"
figures-csv/figure1_strobe_ladder.csv,figure-csv,Figure 1,0c8d1e5f7a2b34960d1e8c7f5a3b2049,19,13,40,2,Participant flow through the nineteen prespecified attrition rungs
figures-csv/figure2_daily_activity.csv,figure-csv,Figure 2,a1b2c3d4e5f60718293a4b5c6d7e8f90,286,13,40,0,Baseline-normalized daily activity by post-discharge day for four procedure groups
figures-csv/figure4_event_centered_activity.csv,figure-csv,Figure 4,4c7e1a9b3d5f60728194a3b5c6d7e8f0,44,10,,176,Normalized activity centred on the acute-care event for cases and matched controls
tables-csv/table4_collider_comparison.csv,table-csv,Table 4,6d8f0a2b4c6e80917a3b5c7d9e1f2a34,3,6,,6,"Acute-care event rate with and without a computable step signal, crude and standardized"
ledgers-csv/ledger_concept_set_registry.csv,table-csv,,3d5e7f9a1b2c4d6e8f0a1b3c5d7e9f01,51,8,,0,One row per code or stem in the locked spine concept set with its region and add-on tags
ledgers-csv/ledger_variable_provenance.csv,table-csv,,7b3c9d1e5f2a48607c1d9e3f5a7b2c04,12,10,0,1,Provenance and missingness for every analysis variable beside the denominator each one is measured over
ledgers-csv/ledger_exclusion_and_censoring_reasons.csv,table-csv,,2e6f0a4b8c1d35729e4f6a8b0c2d1e53,20,7,20,2,Exclusion and censoring reasons within a rung beside the denominator each share is taken over
ledgers-csv/ledger_wear_availability_by_day.csv,table-csv,,8a4b2c6d0e1f39572b8c4d6e0f1a3b25,318,7,20,0,Days at risk and days of valid wear by procedure group and post-discharge day
```

Figure 4's `176` is that rule's arithmetic and the number most likely to be recomputed wrongly:
at tier 4 the file is 44 rows and four token columns, `44 x 4 = 176`. Its `not_plotted_display`
column holds 44 more 7.5 sentences and Figure 3's `not_estimable_display` holds one per
not-estimable row, and neither column enters this count, because a figure CSV writes its sentence
beside the suppressed cell rather than in it. A counter that took the sentence clause to reach
every kind reports 220 for Figure 4, which is 176 hidden numbers plus the 44 strings printed to
announce them.

The example is written at the worked example's own dummy values, which land in tier 4, so
`table4_collider_comparison.csv` carries its three rows with no count in any of them and its
`min_disclosed_count` is empty; at a tier that permits the comparison the same three rows carry the
two episode-day totals and the smaller of them is what that column reports.

**Three numbers in that example were wrong and the wear-ledger row count was arithmetically
impossible.** The file is one row per procedure group and post-discharge day 1 to 90 (5.6), so at
`four_group`, which is the widest collapse level there is, the file cannot hold more than
`4 x 90 = 360` rows, and the example said 556. It is 318 in the fixture, which is 360 less the 42
group-days whose `n_at_risk` failed the floor and were dropped by the absence rule, and 9.2 now pins
that number with its derivation so the example and the fixture cannot drift again. The count is
bounded below as well as above and both bounds are worth stating, because they are what makes it
checkable: it is at least `figure2_daily_activity.csv`'s row count, because `n_at_risk` on a group
and day is at least that day's `n_contributing` and the two files apply the same absence rule to
those two counts, and it is at most 360. The provenance ledger's `min_disclosed_count` moved from 20
to 0 in the same pass, because 5.6's own worked example now reports `baseline_steps` at zero missing
as 7.13 requires, and an exact zero is disclosable and is written as `0`.

### 8.4 The local check, and when it runs

`verify.py --bundle` runs **immediately after transcription and before any figure is rendered**. It is
the first thing that touches `v1/results/`. A transcription slip caught here costs a re-download; the
same slip caught after the manuscript is assembled has already been read as a finding.

```
verify.py --bundle
  1. MANIFEST.md5 exists, is 32 hex characters plus a newline, and equals md5(MANIFEST.csv bytes).
  2. Every row in MANIFEST.csv names a file that exists.
  3. Every file under v1/results/ appears in MANIFEST.csv, except MANIFEST.csv and MANIFEST.md5.
     A straggler file is a failure: it is a file nobody stamped.
  4. For every row: md5(file bytes) equals the declared md5.
  5. For every CSV row: the parsed row count equals n_rows and the parsed column count equals
     n_columns.
  6. results.json parses, and meta.schema_version equals this contract's version.
  7. meta.contract_sha256 equals sha256(prespecification/EXPORT-CONTRACT.md bytes) as committed.
  8. meta.manifest_rows equals the data-row count of MANIFEST.csv.
  9. Every md5 duplicated into results.json.tables[*].md5 and results.json.figures[*].md5 equals the
     manifest's md5 for the same file.
 10. Exit 0 on all clear. Exit 1 on the first failure, naming the file and both hashes.
```

`verify.py` with no flag runs the full audit: the bundle check above, then the disclosure re-check
(section 10), then the label check (section 6), then the numeral audit that extracts text back out of
the rendered `.docx` and asserts every numeral token is a member of the approved display vocabulary
of section 2.5.

---

## 9. Worked example

Dummy values, realistic in magnitude for this cohort: an analytic cohort of 340 episodes, 20
composite acute-care events, and a gate that lands in the lowest tier so the deciding count is itself
unprintable. The example deliberately exercises a suppressed scalar (`gate.stages[E].total`), a
suppressed ladder rung (`excl_event_without_computable_landmark`), a suppressed forest row
(`subgroup_device_wear`), and absent Figure 2 series points including a mid-series gap.

### 9.1 `results.json`, excerpt

Arrays are shown with representative members: `attrition.rungs` shows 5 of its 19 rungs,
`attrition.segments` shows all 3, `denominators` shows 3 of its 8, `debt.by_group` shows 3 of its 5,
and `sensitivity` shows 3 of its 14. `cohort.groups`, `gate.stages`, `figures` and `tables` are
complete. Every block is present, and every node shape appears at least once, including the bound
node and the suppressed node.

`suppressed.entries` and `checks.entries` are excerpts too, and their counters are the one place this
excerpt cannot be internally consistent with a real run: `n_entries` and `by_reason` here count only
the entries shown, while `checks.n_checks` carries the true 13 against 3 shown entries. In a real
file `n_entries` equals `len(entries)`, `by_reason` totals to it, and `n_checks` equals
`len(checks.entries)`. The fixture of 9.2, not this excerpt, is what a module asserts against.

```json
{
  "meta": {
    "schema_version": "2.0.0",
    "contract_sha256": "9f2c74b1a0d38e5f6c1b904e77aa2318cd54fe0b6a9137d24e8c05b3f1a6d2e0",
    "study": "Cumulative ambulatory activity loss after elective cervical and lumbar spine surgery",
    "generated_utc": "2026-09-14T18:02:11Z",
    "run_id": "2026-09-14T18:02:11Z-a3f9c1",
    "code_commit_sha": "4b1f9d2c8a7e0135ab62d4f80c9e73516a2d8b4f",
    "cdr": {
      "resource_name": "C2025Q4R6",
      "resolved_dataset": "wb-silky-artichoke-2408.C2025Q4R6",
      "resolved_by": "wb resource resolve --name C2025Q4R6",
      "resolved_utc": "2026-09-14T16:41:02Z",
      "bq_location": "US",
      "tier": "Controlled",
      "version_label": "cdrv9",
      "dates_shifted": false
    },
    "workspace": {"google_project": "wb-spinewear-4471", "derived_dataset": "wb-spinewear-4471.spinewear_v1", "derived_location": "US"},
    "analysis_plan": {
      "path": "prespecification/ANALYSIS-PLAN.md",
      "sha256": "c41d8f2b6e07a95315cd4b8e2f70a6d19b3c5e8047af12d6903b7c4e5a1f9b77",
      "locked_utc": "2026-08-25T22:41:07Z",
      "locked_before_first_count": true,
      "amendments": [
        {"n": 1, "utc": "2026-08-25", "sections": "Header, 1.3, 2.1, ...", "change": "See the itemised list below", "reason": "Spec-compliance review of the batch-1 build found ...", "approved_by": "Samer, at the batch-1 fix pass, before any count was seen", "superseded_sha256": "405f04f9218ca4197e5db766de26fadb1ed52030dae1f9c4d9da9efff1d0826e"}
      ]
    },
    "arm": {"slug": "recovery_debt", "display": "Recovery debt", "selected_by": "feasibility gate tier reached", "tier_slug": "no_early_warning"},
    "seeds": {"python": 0, "numpy": 0, "bootstrap": 0, "monte_carlo": 0},
    "sampling_salt": "spinewear-v1-risk-set",
    "software": {
      "python": "3.11.9",
      "packages": {"numpy": "1.26.4", "pandas": "2.2.2", "statsmodels": "0.14.2"},
      "r": "4.3.2",
      "r_packages": {"glmmTMB": "1.1.9", "ordbetareg": "0.7.2"}
    },
    "estimator": {
      "r_used": true,
      "rung_index": 1,
      "rung_slug": "r_ordered_beta_glmm",
      "rung_display": "Ordered beta mixed model in R",
      "descent_triggers_fired": [],
      "fallback_reason": null,
      "rungs_attempted": [
        {"index": 1, "slug": "r_ordered_beta_glmm", "outcome": "converged"},
        {"index": 2, "slug": "r_zero_one_inflated_beta_glmm", "outcome": "not attempted"}
      ],
      "bootstrap_failure_rate": {"suppressed": false, "pct": 8, "num": 40, "den": 500, "display": "8%", "display_count": "40", "display_denominator": "500"}
    },
    "concept_set": {
      "n_concepts": {"value": 852, "display": "852"},
      "source_module": "pipeline/cs_spine.py",
      "registry_file": "ledgers-csv/ledger_concept_set_registry.csv",
      "gaps": {
        "cervical_decompression": {
          "builder": "cs_spine.cervical_decompression_split_sql",
          "evidence_path_first": "candidate CPT only, invisible to the locked set",
          "n_candidate_only": {"suppressed": false, "n": 60, "rounded": true, "display": "60"},
          "n_locked_set": {"suppressed": false, "n": 1140, "rounded": true, "display": "1,140"},
          "share": {"suppressed": false, "pct": 5, "num": 60, "den": 1200, "display": "5%", "display_count": "60", "display_denominator": "1,200"},
          "response_display": "Stated omission: the four absent codes and the measured share go in the Methods and in the limitations. The set is not amended",
          "set_amended": false
        },
        "cervical_fusion": {
          "builder": "cs_spine.cervical_fusion_split_sql",
          "evidence_path_first": "candidate CPT only, invisible to the locked set",
          "n_candidate_only": {"suppressed": false, "n": 80, "rounded": true, "display": "80"},
          "n_also_carrying_candidate_cpt": {"suppressed": false, "n": 80, "rounded": true, "display": "80"},
          "n_locked_set": {"suppressed": false, "n": 1140, "rounded": true, "display": "1,140"},
          "n_misfiled": {"suppressed": false, "n": 40, "rounded": true, "display": "40"},
          "share": {"suppressed": false, "pct": 4, "num": 40, "den": 1140, "display": "4%", "display_count": "40", "display_denominator": "1,140"},
          "response_display": "A supplementary row moves the misfiled episodes to cervical fusion and re-estimates the primary contrast; the locked set is not amended",
          "set_amended": false
        }
      }
    },
    "manifest_rows": 16
  },
  "denominators": {
    "analytic": {
      "n": 340,
      "unit": "episodes",
      "display": "340",
      "display_n_equals": "n = 340",
      "definition": "Eligible spine episodes with adequate preoperative baseline wear and a computable post-discharge activity window",
      "used_for": "The default denominator. Table 1, Table 2, Figure 2 and Figure 3 unless a row names another."
    },
    "events_composite": {
      "n": 40,
      "unit": "events",
      "display": "40",
      "display_n_equals": "n = 40",
      "definition": "First emergency department visits and readmissions through post-discharge day 90, whichever came first",
      "used_for": "Table 3 part A stage D and the feasibility statement in Results."
    },
    "analytic_person_days": {
      "n": 9860,
      "unit": "person-days",
      "display": "9,860",
      "display_n_equals": "n = 9,860",
      "definition": "Analyzable episode-days inside the accrual window, over the analytic cohort",
      "used_for": "Table 4 and the model fit line of the Table 2 footer."
    }
  },
  "attrition": {
    "rungs": [
      {
        "step": 1,
        "slug": "program_participants",
        "display_label": "Participants in the Controlled Tier release",
        "kind": "exclusion",
        "unit": "persons",
        "n_in": {"suppressed": false, "n": 413460, "rounded": true, "display": "413,460"},
        "n_dropped": {"suppressed": false, "n": 403740, "rounded": true, "display": "403,740"},
        "n_out": {"suppressed": false, "n": 9720, "rounded": true, "display": "9,720"},
        "n_carried_forward": null,
        "reason": "program_participants",
        "reason_display": "No qualifying spine procedure concept in the electronic health record",
        "closes_exact": true
      },
      {
        "step": 2,
        "slug": "episode_construction",
        "display_label": "Spine surgical episodes",
        "kind": "conversion",
        "unit": "persons to episodes",
        "n_in": {"suppressed": false, "n": 9720, "rounded": true, "display": "9,720"},
        "n_dropped": {"suppressed": false, "n": 180, "rounded": true, "display": "180"},
        "n_out": {"suppressed": false, "n": 10240, "rounded": true, "display": "10,240"},
        "n_carried_forward": {"suppressed": false, "n": 9540, "rounded": true, "display": "9,540"},
        "reason": "unit_change",
        "reason_display": "Same-day qualifying procedure records collapsed into one episode; operations on different dates stay separate episodes until step 13",
        "closes_exact": true
      },
      {
        "step": 11,
        "slug": "excl_no_wearable_data",
        "display_label": "Wearable-linked spine episodes",
        "kind": "exclusion",
        "unit": "episodes",
        "n_in": {"suppressed": false, "n": 6880, "rounded": true, "display": "6,880"},
        "n_dropped": {"suppressed": false, "n": 5720, "rounded": true, "display": "5,720"},
        "n_out": {"suppressed": false, "n": 1160, "rounded": true, "display": "1,160"},
        "n_carried_forward": null,
        "reason": "excl_no_wearable_data",
        "reason_display": "No Fitbit activity record linked to the participant",
        "closes_exact": true
      },
      {
        "step": 13,
        "slug": "excl_not_first_eligible_episode",
        "display_label": "First eligible episode per participant",
        "kind": "exclusion",
        "unit": "episodes",
        "n_in": {"suppressed": false, "n": 640, "rounded": true, "display": "640"},
        "n_dropped": {"suppressed": false, "n": 60, "rounded": true, "display": "60"},
        "n_out": {"suppressed": false, "n": 580, "rounded": true, "display": "580"},
        "n_carried_forward": null,
        "reason": "excl_not_first_eligible_episode",
        "reason_display": "A later operation by a participant whose first eligible episode is already in the cohort",
        "closes_exact": true
      },
      {
        "step": 18,
        "slug": "excl_event_without_computable_landmark",
        "display_label": "Analyzable acute-care events",
        "kind": "exclusion",
        "unit": "events",
        "n_in": {"suppressed": false, "n": 40, "rounded": true, "display": "40"},
        "n_dropped": {
          "suppressed": true,
          "reason": "cell_below_threshold",
          "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
          "display": "20 or fewer, suppressed per All of Us dissemination policy"
        },
        "n_out": {
          "suppressed": true,
          "reason": "secondary_suppression",
          "reason_display": "suppressed to protect a suppressed cell in the same total",
          "display": "suppressed to protect a suppressed cell in the same total"
        },
        "n_carried_forward": null,
        "reason": "excl_event_without_computable_landmark",
        "reason_display": "Event on post-discharge day 1 to 4, with no computable proximal window",
        "closes_exact": true
      }
    ],
    "segments": [
      {
        "unit": "persons",
        "first_step": 1,
        "last_step": 2,
        "n_start": {"suppressed": false, "n": 413460, "rounded": true, "display": "413,460"},
        "n_end": {"suppressed": false, "n": 9540, "rounded": true, "display": "9,540"},
        "sum_dropped": {"suppressed": false, "n": 403920, "rounded": true, "display": "403,920"},
        "n_rounded_terms": 4,
        "tolerance": 40,
        "closes_exact": true,
        "rounded_residual": 0
      },
      {
        "unit": "episodes",
        "first_step": 2,
        "last_step": 16,
        "n_start": {"suppressed": false, "n": 10240, "rounded": true, "display": "10,240"},
        "n_end": {"suppressed": false, "n": 340, "rounded": true, "display": "340"},
        "sum_dropped": {"suppressed": false, "n": 9900, "rounded": true, "display": "9,900"},
        "n_rounded_terms": 15,
        "tolerance": 150,
        "closes_exact": true,
        "rounded_residual": 0
      },
      {
        "unit": "events",
        "first_step": 17,
        "last_step": 19,
        "n_start": {"suppressed": false, "n": 40, "rounded": true, "display": "40"},
        "n_end": {
          "suppressed": true,
          "reason": "secondary_suppression",
          "reason_display": "suppressed to protect a suppressed cell in the same total",
          "display": "suppressed to protect a suppressed cell in the same total"
        },
        "sum_dropped": {
          "suppressed": true,
          "reason": "cell_below_threshold",
          "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
          "display": "20 or fewer, suppressed per All of Us dissemination policy"
        },
        "n_rounded_terms": 3,
        "tolerance": 30,
        "closes_exact": true,
        "rounded_residual": null
      }
    ],
    "closes": true,
    "rounding_footnote": "Counts are rounded to the nearest 20 in accordance with the All of Us dissemination policy, so the boxes may not sum exactly. The unrounded ladder was asserted to close before rounding."
  },
  "cohort": {
    "groups": [
      {
        "slug": "cervical_decompression",
        "display_label": "Cervical decompression",
        "order": 1,
        "n": {"suppressed": false, "n": 60, "rounded": true, "display": "60"},
        "column_header": "Cervical decompression (n = 60)"
      },
      {
        "slug": "cervical_fusion",
        "display_label": "Cervical fusion",
        "order": 2,
        "n": {"suppressed": false, "n": 80, "rounded": true, "display": "80"},
        "column_header": "Cervical fusion (n = 80)"
      },
      {
        "slug": "lumbar_decompression",
        "display_label": "Lumbar decompression",
        "order": 3,
        "n": {"suppressed": false, "n": 120, "rounded": true, "display": "120"},
        "column_header": "Lumbar decompression (n = 120)"
      },
      {
        "slug": "lumbar_fusion",
        "display_label": "Lumbar fusion",
        "order": 4,
        "n": {"suppressed": false, "n": 80, "rounded": true, "display": "80"},
        "column_header": "Lumbar fusion (n = 80)"
      },
      {
        "slug": "all_groups",
        "display_label": "All groups",
        "order": 5,
        "n": {"suppressed": false, "n": 340, "rounded": true, "display": "340"},
        "column_header": "All groups (n = 340)"
      }
    ],
    "collapse_level": "four_group",
    "collapse_reason": "every procedure group at or above the disclosure floor",
    "denominator_index": ["analytic", "events_composite"],
    "window": {
      "accrual_first_day": {"value": 1, "display": "1"},
      "accrual_last_day": {"value": 35, "display": "35"},
      "follow_up_last_day": {"value": 90, "display": "90"},
      "baseline_first_day": {"value": -30, "display": "-30"},
      "baseline_last_day": {"value": -8, "display": "-8"},
      "baseline_min_valid_days": {"value": 7, "display": "7"},
      "baseline_min_span_days": {"value": 14, "display": "14"},
      "valid_day_min_minutes": {"value": 600, "display": "600"},
      "display_accrual": "post-discharge day 1–35",
      "display_baseline": "8–30 days before surgery"
    },
    "min_cell": {"value": 20, "display": "20"},
    "collapse_level_index": 1,
    "collapse_footnote": null
  },
  "debt": {
    "estimand": {
      "display": "Digital recovery debt is the sum across post-discharge day 1 to 35 of the shortfall between a participant's daily step count and that participant's own preoperative baseline, in baseline-equivalent activity days lost.",
      "unit": "activity_days",
      "max_possible": {"value": 35, "display": "35"},
      "estimator": "model and integrate"
    },
    "by_group": [
      {
        "slug": "cervical_decompression",
        "n": {"suppressed": false, "n": 60, "rounded": true, "display": "60"},
        "unadjusted_debt": {"suppressed": false, "q50": 5.4, "q25": 2.1, "q75": 11.8, "unit": "activity_days", "display": "5.4 (2.1–11.8)", "display_point": "5.4", "display_iqr": "2.1–11.8"},
        "adjusted_debt": {"suppressed": false, "est": 6.1, "lo": 4.2, "hi": 8.0, "level": 0.95, "unit": "activity_days", "display": "6.1 (95% CI 4.2 to 8.0)", "display_point": "6.1", "display_ci": "95% CI 4.2 to 8.0"},
        "thousand_steps_lost": {
          "suppressed": false,
          "est": 28.4,
          "lo": 19.1,
          "hi": 37.7,
          "level": 0.95,
          "unit": "thousand_steps",
          "display": "28.4 (95% CI 19.1 to 37.7)",
          "display_point": "28.4",
          "display_ci": "95% CI 19.1 to 37.7"
        },
        "adjusted_mean_normalized_activity": {
          "suppressed": false,
          "est": 0.79,
          "lo": 0.74,
          "hi": 0.84,
          "level": 0.95,
          "unit": "normalized_activity",
          "display": "0.79 (95% CI 0.74 to 0.84)",
          "display_point": "0.79",
          "display_ci": "95% CI 0.74 to 0.84"
        },
        "share_reaching_80pct_baseline": {"suppressed": false, "est": 67, "lo": 54, "hi": 78, "level": 0.95, "unit": "percent", "display": "67% (95% CI 54% to 78%)", "display_point": "67%", "display_ci": "95% CI 54% to 78%"},
        "share_zero_debt": {
          "suppressed": true,
          "reason": "cell_below_threshold",
          "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
          "display": "20 or fewer, suppressed per All of Us dissemination policy"
        },
        "n_complete_windows": {"suppressed": false, "n": 40, "rounded": true, "display": "40"}
      },
      {
        "slug": "lumbar_fusion",
        "n": {"suppressed": false, "n": 80, "rounded": true, "display": "80"},
        "unadjusted_debt": {"suppressed": false, "q50": 14.2, "q25": 7.6, "q75": 22.9, "unit": "activity_days", "display": "14.2 (7.6–22.9)", "display_point": "14.2", "display_iqr": "7.6–22.9"},
        "adjusted_debt": {
          "suppressed": false,
          "est": 12.4,
          "lo": 10.1,
          "hi": 14.7,
          "level": 0.95,
          "unit": "activity_days",
          "display": "12.4 (95% CI 10.1 to 14.7)",
          "display_point": "12.4",
          "display_ci": "95% CI 10.1 to 14.7"
        },
        "thousand_steps_lost": {
          "suppressed": false,
          "est": 61.8,
          "lo": 49.2,
          "hi": 74.4,
          "level": 0.95,
          "unit": "thousand_steps",
          "display": "61.8 (95% CI 49.2 to 74.4)",
          "display_point": "61.8",
          "display_ci": "95% CI 49.2 to 74.4"
        },
        "adjusted_mean_normalized_activity": {
          "suppressed": false,
          "est": 0.58,
          "lo": 0.53,
          "hi": 0.63,
          "level": 0.95,
          "unit": "normalized_activity",
          "display": "0.58 (95% CI 0.53 to 0.63)",
          "display_point": "0.58",
          "display_ci": "95% CI 0.53 to 0.63"
        },
        "share_reaching_80pct_baseline": {"suppressed": false, "est": 31, "lo": 21, "hi": 43, "level": 0.95, "unit": "percent", "display": "31% (95% CI 21% to 43%)", "display_point": "31%", "display_ci": "95% CI 21% to 43%"},
        "share_zero_debt": {
          "suppressed": true,
          "reason": "secondary_suppression",
          "reason_display": "suppressed to protect a suppressed cell in the same total",
          "display": "suppressed to protect a suppressed cell in the same total"
        },
        "n_complete_windows": {"suppressed": false, "n": 40, "rounded": true, "display": "40"}
      },
      {
        "slug": "all_groups",
        "n": {"suppressed": false, "n": 340, "rounded": true, "display": "340"},
        "n_complete_windows": {"suppressed": false, "n": 180, "rounded": true, "display": "180"},
        "unadjusted_debt": {"suppressed": false, "q50": 8.6, "q25": 3.4, "q75": 17.1, "unit": "activity_days", "display": "8.6 (3.4–17.1)", "display_point": "8.6", "display_iqr": "3.4–17.1"},
        "adjusted_debt": {"suppressed": false, "est": 9.0, "lo": 7.6, "hi": 10.4, "level": 0.95, "unit": "activity_days", "display": "9.0 (95% CI 7.6 to 10.4)", "display_point": "9.0", "display_ci": "95% CI 7.6 to 10.4"},
        "thousand_steps_lost": {
          "suppressed": false,
          "est": 44.2,
          "lo": 36.1,
          "hi": 52.3,
          "level": 0.95,
          "unit": "thousand_steps",
          "display": "44.2 (95% CI 36.1 to 52.3)",
          "display_point": "44.2",
          "display_ci": "95% CI 36.1 to 52.3"
        },
        "adjusted_mean_normalized_activity": {
          "suppressed": false,
          "est": 0.68,
          "lo": 0.64,
          "hi": 0.72,
          "level": 0.95,
          "unit": "normalized_activity",
          "display": "0.68 (95% CI 0.64 to 0.72)",
          "display_point": "0.68",
          "display_ci": "95% CI 0.64 to 0.72"
        },
        "share_reaching_80pct_baseline": {"suppressed": false, "est": 47, "lo": 41, "hi": 53, "level": 0.95, "unit": "percent", "display": "47% (95% CI 41% to 53%)", "display_point": "47%", "display_ci": "95% CI 41% to 53%"},
        "share_zero_debt": {"suppressed": false, "pct": 12, "num": 40, "den": 340, "display": "12%", "display_count": "40", "display_denominator": "340"}
      }
    ],
    "contrasts": {
      "fusion_vs_decompression": {
        "display_label": "Fusion versus decompression",
        "estimate": {"suppressed": false, "est": 4.4, "lo": 2.6, "hi": 6.2, "level": 0.95, "unit": "activity_days", "display": "4.4 (95% CI 2.6 to 6.2)", "display_point": "4.4", "display_ci": "95% CI 2.6 to 6.2"},
        "pvalue": {"suppressed": false, "p": 0.0004, "floored": true, "display": "P < 0.001"},
        "is_primary": true,
        "n_compared": {"suppressed": false, "n": 340, "rounded": true, "display": "340"}
      },
      "lumbar_vs_cervical": {
        "display_label": "Lumbar versus cervical",
        "estimate": {"suppressed": false, "est": 1.6, "lo": -0.3, "hi": 3.5, "level": 0.95, "unit": "activity_days", "display": "1.6 (95% CI -0.3 to 3.5)", "display_point": "1.6", "display_ci": "95% CI -0.3 to 3.5"},
        "pvalue": {"suppressed": false, "p": 0.098, "floored": false, "display": "P = 0.098"},
        "is_primary": false,
        "n_compared": {"suppressed": false, "n": 340, "rounded": true, "display": "340"}
      }
    },
    "unadjusted_contrasts": {
      "fusion_vs_decompression": {
        "display_label": "Fusion versus decompression",
        "estimate": {"suppressed": false, "est": 5.8, "lo": 3.9, "hi": 7.7, "level": 0.95, "unit": "activity_days", "display": "5.8 (95% CI 3.9 to 7.7)", "display_point": "5.8", "display_ci": "95% CI 3.9 to 7.7"},
        "pvalue": {"suppressed": false, "p": 0.0002, "floored": true, "display": "P < 0.001"},
        "is_primary": true,
        "n_compared": {"suppressed": false, "n": 340, "rounded": true, "display": "340"}
      },
      "lumbar_vs_cervical": {
        "display_label": "Lumbar versus cervical",
        "estimate": {"suppressed": false, "est": 2.4, "lo": 0.3, "hi": 4.5, "level": 0.95, "unit": "activity_days", "display": "2.4 (95% CI 0.3 to 4.5)", "display_point": "2.4", "display_ci": "95% CI 0.3 to 4.5"},
        "pvalue": {"suppressed": false, "p": 0.026, "floored": false, "display": "P = 0.026"},
        "is_primary": false,
        "n_compared": {"suppressed": false, "n": 340, "rounded": true, "display": "340"}
      }
    },
    "unadjusted_model": {
      "definition_display": "The unadjusted contrast is the same model-and-integrate estimator refitted with the locked covariate set removed: age, sex assigned at birth, body mass index, comorbidity burden, length of stay, index year, the COVID-19 era indicator and device family are all absent from its mean structure. Everything the estimand is defined on is kept and is not an adjustment: the post-discharge-day spline, the procedure groups and their day curves, the region terms the collapse level admits, and day of week. The observation weights are the primary analysis's own and are not refitted, so the one difference between the two contrasts is the covariate block and the reader may read the gap between them as what the covariates moved.",
      "mandate_display": "This contrast is required by STROBE item 16(a), which asks for unadjusted estimates beside confounder-adjusted ones. It is not prespecified: the locked analysis plan carries an unadjusted association for the other arm at its section 4.8 and an unadjusted absolute level for this one at its section 9.2, and neither is an unadjusted contrast. It is reported as guideline-mandated and never as prespecified.",
      "prespecified": false,
      "rung_slug": "py_fractional_logit_gee",
      "rung_display": "Fractional-response quasi-binomial estimating equations",
      "rung_index": 3,
      "rung_matches_adjusted": true,
      "rung_note_display": "The unadjusted fit reached the same rung of the model family ladder as the adjusted fit, so the two contrasts differ in the covariate set and in nothing else.",
      "bootstrap_failure_rate": {"suppressed": false, "pct": 2, "num": 20, "den": 1000, "display": "2%", "display_count": "20", "display_denominator": "1,000"},
      "not_estimable_reason": null
    },
    "absolute_scale": {
      "fusion_vs_decompression": {
        "display_label": "Fusion versus decompression",
        "estimate": {
          "suppressed": false,
          "est": 24.9,
          "lo": 13.8,
          "hi": 36.0,
          "level": 0.95,
          "unit": "thousand_steps",
          "display": "24.9 (95% CI 13.8 to 36.0)",
          "display_point": "24.9",
          "display_ci": "95% CI 13.8 to 36.0"
        },
        "pvalue": {"suppressed": false, "p": 0.0009, "floored": true, "display": "P < 0.001"},
        "is_primary": false,
        "n_compared": {"suppressed": false, "n": 340, "rounded": true, "display": "340"}
      }
    },
    "manski": {
      "by_group": {
        "all_groups": {
          "lower": {"suppressed": false, "est": 3.1, "lo": 3.1, "hi": 3.1, "level": 0.95, "unit": "activity_days", "display": "3.1", "display_point": "3.1", "display_ci": ""},
          "upper": {"suppressed": false, "est": 21.4, "lo": 21.4, "hi": 21.4, "level": 0.95, "unit": "activity_days", "display": "21.4", "display_point": "21.4", "display_ci": ""}
        }
      },
      "primary_contrast_lower": {"suppressed": false, "est": -0.4, "lo": -0.4, "hi": -0.4, "level": 0.95, "unit": "activity_days", "display": "-0.4", "display_point": "-0.4", "display_ci": ""},
      "primary_contrast_upper": {"suppressed": false, "est": 9.6, "lo": 9.6, "hi": 9.6, "level": 0.95, "unit": "activity_days", "display": "9.6", "display_point": "9.6", "display_ci": ""},
      "display": "-0.4 to 9.6 activity days",
      "crosses_zero": true,
      "computed_on": "every eligible episode"
    },
    "delta_shift": {
      "scale": "latent logit",
      "applied_to": "decompression only",
      "tipping_point_point_estimate": {
        "suppressed": false,
        "est": 1.25,
        "lo": 1.25,
        "hi": 1.25,
        "level": 0.95,
        "unit": "dimensionless",
        "display": "1.25",
        "display_point": "1.25",
        "display_ci": ""
      },
      "tipping_point_interval": {"suppressed": false, "est": 0.75, "lo": 0.75, "hi": 0.75, "level": 0.95, "unit": "dimensionless", "display": "0.75", "display_point": "0.75", "display_ci": ""},
      "definition_display": "The primary contrast crosses zero once the daily deficit on unobserved days in the decompression groups is shifted upward by 1.25 log-odds on the model's own latent scale, which turns a reference day with a 30% deficit into a day with a 60% deficit.",
      "applications": ["fusion only", "decompression only", "both groups"],
      "grid": [
        {"delta": 0.0, "applied_to": "decompression only", "contrast_est": 4.4, "contrast_lo": 2.6, "contrast_hi": 6.2, "implied_deficit_at_reference": 0.3},
        {"delta": 1.25, "applied_to": "decompression only", "contrast_est": 0.0, "contrast_lo": -1.8, "contrast_hi": 1.8, "implied_deficit_at_reference": 0.6}
      ],
      "reference_deficit": {"value": 0.3, "display": "0.30"},
      "grid_extended": false,
      "crossed_within_grid": true,
      "interval_crossed_within_grid": true,
      "no_crossing_display": null
    },
    "model_fit": {
      "family": "ordered beta",
      "link": "logit",
      "spline_basis": "restricted cubic on post-discharge day",
      "spline_df": {"value": 5, "display": "5"},
      "residual_correlation": "continuous-time AR(1)",
      "rho": {
        "suppressed": false,
        "est": 0.41,
        "lo": 0.36,
        "hi": 0.46,
        "level": 0.95,
        "unit": "dimensionless",
        "display": "0.41 (95% CI 0.36 to 0.46)",
        "display_point": "0.41",
        "display_ci": "95% CI 0.36 to 0.46"
      },
      "icc": {
        "suppressed": false,
        "est": 0.62,
        "lo": 0.55,
        "hi": 0.69,
        "level": 0.95,
        "unit": "dimensionless",
        "display": "0.62 (95% CI 0.55 to 0.69)",
        "display_point": "0.62",
        "display_ci": "95% CI 0.55 to 0.69"
      },
      "marginal_r2": {
        "suppressed": false,
        "est": 0.18,
        "lo": 0.13,
        "hi": 0.23,
        "level": 0.95,
        "unit": "dimensionless",
        "display": "0.18 (95% CI 0.13 to 0.23)",
        "display_point": "0.18",
        "display_ci": "95% CI 0.13 to 0.23"
      },
      "conditional_r2": {
        "suppressed": false,
        "est": 0.69,
        "lo": 0.64,
        "hi": 0.74,
        "level": 0.95,
        "unit": "dimensionless",
        "display": "0.69 (95% CI 0.64 to 0.74)",
        "display_point": "0.69",
        "display_ci": "95% CI 0.64 to 0.74"
      },
      "aic": {"value": 18420, "display": "18,420"},
      "n_person_days": {"suppressed": false, "n": 9860, "rounded": true, "display": "9,860"},
      "n_persons": {"suppressed": false, "n": 340, "rounded": true, "display": "340"},
      "converged": true,
      "monte_carlo_draws": {"value": 2000, "display": "2,000"}
    }
  },
  "sensitivity": {
    "pod_anchored_window": {
      "order": 1,
      "display_label": "Postoperative day 8–42 window",
      "estimate": {"suppressed": false, "est": 5.1, "lo": 3.1, "hi": 7.1, "level": 0.95, "unit": "activity_days", "display": "5.1 (95% CI 3.1 to 7.1)", "display_point": "5.1", "display_ci": "95% CI 3.1 to 7.1"},
      "pvalue": {"suppressed": false, "p": 0.0006, "floored": true, "display": "P < 0.001"},
      "n": {"suppressed": false, "n": 340, "rounded": true, "display": "340"},
      "estimable": true,
      "not_estimable_reason": null,
      "axis": "primary",
      "render": "marker",
      "direction_matches_primary": true,
      "sub_order": 1,
      "varies": "Accrual over postoperative days 8 to 42 instead of post-discharge days 1 to 35"
    },
    "delta_shift_tipping_point": {
      "order": 5,
      "display_label": "Delta-shift tipping point",
      "estimate": {
        "suppressed": false,
        "est": 1.25,
        "lo": 1.25,
        "hi": 1.25,
        "level": 0.95,
        "unit": "dimensionless",
        "display": "1.25",
        "display_point": "1.25",
        "display_ci": ""
      },
      "pvalue": null,
      "n": {"suppressed": false, "n": 340, "rounded": true, "display": "340"},
      "estimable": true,
      "not_estimable_reason": null,
      "axis": "latent_logit_shift",
      "render": "panel",
      "direction_matches_primary": true,
      "sub_order": 1,
      "varies": "The delta grid, applied to the fusion group, the decompression group and both"
    },
    "wear_definition_s3": {
      "order": 6,
      "sub_order": 3,
      "display_label": "Wear day at 8 hours",
      "estimate": {"suppressed": false, "est": 4.6, "lo": 2.7, "hi": 6.5, "level": 0.95, "unit": "activity_days", "display": "4.6 (95% CI 2.7 to 6.5)", "display_point": "4.6", "display_ci": "95% CI 2.7 to 6.5"},
      "pvalue": {"suppressed": false, "p": 0.0008, "floored": true, "display": "P < 0.001"},
      "n": {"suppressed": false, "n": 360, "rounded": true, "display": "360"},
      "estimable": true,
      "not_estimable_reason": null,
      "axis": "primary",
      "render": "marker",
      "varies": "Valid wear day requires at least 8 hours of heart-rate wear",
      "direction_matches_primary": true
    }
  },
  "gate": {
    "stages": [
      {
        "letter": "A",
        "slug": "stage_a_qualifying_episodes",
        "display_label": "Qualifying spine episodes by procedure group",
        "definition_display": "Unique qualifying spine episodes by procedure group",
        "unit": "episodes",
        "total": {"suppressed": false, "n": 340, "rounded": true, "display": "340"},
        "by_group": {
          "cervical_decompression": {"suppressed": false, "n": 60, "rounded": true, "display": "60"},
          "cervical_fusion": {"suppressed": false, "n": 80, "rounded": true, "display": "80"},
          "lumbar_decompression": {"suppressed": false, "n": 120, "rounded": true, "display": "120"},
          "lumbar_fusion": {"suppressed": false, "n": 80, "rounded": true, "display": "80"}
        },
        "components": null
      },
      {
        "letter": "B",
        "slug": "stage_b_baseline_wear",
        "display_label": "Episodes with at least 7 valid baseline days",
        "definition_display": "Episodes with at least 7 valid baseline days in the 8 to 30 days before surgery",
        "unit": "episodes",
        "total": {"suppressed": false, "n": 420, "rounded": true, "display": "420"},
        "by_group": null,
        "components": null
      },
      {
        "letter": "C",
        "slug": "stage_c_computable_window",
        "display_label": "Episodes with a computable post-discharge window",
        "definition_display": "Episodes with at least one computable post-discharge 3-day window",
        "unit": "episodes",
        "total": {"suppressed": false, "n": 340, "rounded": true, "display": "340"},
        "by_group": null,
        "components": null
      },
      {
        "letter": "D",
        "slug": "stage_d_events",
        "display_label": "First acute-care events through day 90",
        "definition_display": "First emergency department visits, inpatient readmissions, and composite events through 90 days",
        "unit": "events",
        "total": {"suppressed": false, "n": 40, "rounded": true, "display": "40"},
        "by_group": null,
        "components": {
          "first_ed_visits": {
            "suppressed": true,
            "reason": "cell_below_threshold",
            "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
            "display": "20 or fewer, suppressed per All of Us dissemination policy"
          },
          "readmissions": {
            "suppressed": true,
            "reason": "secondary_suppression",
            "reason_display": "suppressed to protect a suppressed cell in the same total",
            "display": "suppressed to protect a suppressed cell in the same total"
          },
          "composite": {"suppressed": false, "n": 40, "rounded": true, "display": "40"}
        }
      },
      {
        "letter": "E",
        "slug": "stage_e_computable_ratio",
        "display_label": "Events with a computable proximal step ratio",
        "definition_display": "Events with a computable proximal step ratio",
        "unit": "events",
        "total": {
          "suppressed": true,
          "reason": "cell_below_threshold",
          "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
          "display": "20 or fewer, suppressed per All of Us dissemination policy"
        },
        "by_group": null,
        "components": null
      },
      {
        "letter": "F",
        "slug": "stage_f_events_by_stratum",
        "display_label": "Events by anatomic region and fusion status",
        "definition_display": "Events by lumbar and cervical, and by fusion and decompression, strata",
        "unit": "events",
        "total": {
          "suppressed": true,
          "reason": "cell_below_threshold",
          "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
          "display": "20 or fewer, suppressed per All of Us dissemination policy"
        },
        "by_group": {
          "cervical_decompression": {
            "suppressed": true,
            "reason": "cell_below_threshold",
            "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
            "display": "20 or fewer, suppressed per All of Us dissemination policy"
          },
          "cervical_fusion": {
            "suppressed": true,
            "reason": "cell_below_threshold",
            "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
            "display": "20 or fewer, suppressed per All of Us dissemination policy"
          },
          "lumbar_decompression": {
            "suppressed": true,
            "reason": "cell_below_threshold",
            "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
            "display": "20 or fewer, suppressed per All of Us dissemination policy"
          },
          "lumbar_fusion": {
            "suppressed": true,
            "reason": "cell_below_threshold",
            "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
            "display": "20 or fewer, suppressed per All of Us dissemination policy"
          }
        },
        "components": null
      }
    ],
    "tier": {
      "index": 4,
      "slug": "no_early_warning",
      "display_label": "No early-warning modeling",
      "events_lower": null,
      "events_upper": 19,
      "determined_by": "stage E",
      "event_count_printable": false,
      "permitted_analysis_verbatim": "No early-warning modeling at all",
      "permitted_claim_verbatim": "Feasibility statement only, with the count suppressed",
      "exhibit_set": "primary"
    },
    "arm_a": {
      "permitted": false,
      "reason_display": "The feasibility gate reached the lowest prespecified tier, which permits no early-warning estimate. The deciding count is itself below the disclosure floor, so the tier boundary and the disclosure floor coincide.",
      "estimates": {}
    }
  },
  "figures": {
    "figure1": {
      "file": "figures-csv/figure1_strobe_ladder.csv",
      "columns": ["step", "slug", "display_label", "kind", "unit", "n_in", "n_dropped", "n_out", "n_carried_forward", "reason", "reason_display", "closes_exact", "box_side"],
      "sort_keys": ["step"],
      "rows": 19,
      "md5": "0c8d1e5f7a2b34960d1e8c7f5a3b2049",
      "denominator": "analytic",
      "n": 340,
      "legend": "Figure 1. Participant flow. Counts are rounded to the nearest 20 in accordance with the All of Us dissemination policy, so the boxes may not sum exactly.",
      "plate_note": "Analytic cohort n = 340 episodes."
    },
    "figure2": {
      "file": "figures-csv/figure2_daily_activity.csv",
      "columns": [
        "group_slug",
        "display_label",
        "group_order",
        "day",
        "n_contributing",
        "observed_median",
        "observed_p25",
        "observed_p75",
        "fitted_marginal",
        "fitted_lo",
        "fitted_hi",
        "in_accrual_window",
        "series_segment"
      ],
      "sort_keys": ["group_order", "day"],
      "rows": 286,
      "md5": "a1b2c3d4e5f60718293a4b5c6d7e8f90",
      "denominator": "analytic",
      "n": 340,
      "legend": "Figure 2. Baseline-normalized daily activity by post-discharge day. Days on which a group had 20 or fewer contributors are not plotted, so a line and its ribbon end where the data end.",
      "plate_note": "Analytic cohort n = 340 episodes. Days with 20 or fewer contributors are not plotted.",
      "days_dropped_by_group": {"cervical_decompression": 34, "cervical_fusion": 21, "lumbar_decompression": 8, "lumbar_fusion": 11},
      "last_day_by_group": {"cervical_decompression": 73, "cervical_fusion": 69, "lumbar_decompression": 82, "lumbar_fusion": 79},
      "n_gaps_by_group": {"cervical_decompression": 1, "cervical_fusion": 0, "lumbar_decompression": 0, "lumbar_fusion": 0},
      "n_series": 4
    },
    "figure3": {
      "file": "figures-csv/figure3_forest.csv",
      "columns": ["block", "block_label", "row_order", "slug", "display_label", "estimate", "ci_lo", "ci_hi", "unit", "axis", "render", "n", "estimable", "not_estimable_display", "is_primary", "reference_value"],
      "sort_keys": ["block", "row_order"],
      "rows": 27,
      "md5": "5e9f0a1b2c3d4e5f60718293a4b5c6d7",
      "denominator": "analytic",
      "n": 340,
      "legend": "Figure 3. Recovery debt contrasts and robustness. A subgroup below the disclosure floor prints as not estimable rather than being omitted.",
      "plate_note": "Analytic cohort n = 340 episodes.",
      "blocks": [
        {"index": 1, "display_label": "Primary and key secondary contrasts", "rows": 5},
        {"index": 2, "display_label": "Robustness of the primary contrast", "rows": 14},
        {"index": 3, "display_label": "Subgroups", "rows": 8}
      ]
    },
    "figure4": {
      "file": "figures-csv/figure4_event_centered_activity.csv",
      "columns": ["series_slug", "display_label", "series_order", "day_relative_to_event", "n_contributing", "observed_median", "observed_p25", "observed_p75", "plotted", "not_plotted_display"],
      "sort_keys": ["series_order", "day_relative_to_event"],
      "rows": 44,
      "md5": "4c7e1a9b3d5f60728194a3b5c6d7e8f0",
      "denominator": "events_composite",
      "n": 40,
      "legend": "Figure 4. Normalized daily activity centred on the acute-care event, for cases and their post-discharge-day matched controls. The feasibility tier reached permits no early-warning analysis, so no offset is plotted.",
      "plate_note": "First acute-care events n = 40. No offset is plotted at the feasibility tier reached.",
      "n_series": 2,
      "day_range": [-14, 7],
      "n_days_plotted_by_series": {"event_case": 0, "matched_control": 0},
      "tier_permits_plot": false
    }
  },
  "tables": {
    "table1": {
      "file": "tables-csv/table1_cohort_characteristics.csv",
      "columns": [
        "row_order",
        "Characteristic",
        "Level",
        "Cervical decompression (n = 60)",
        "Cervical fusion (n = 80)",
        "Lumbar decompression (n = 120)",
        "Lumbar fusion (n = 80)",
        "All groups (n = 340)",
        "Statistic"
      ],
      "key_columns": ["Characteristic", "Level"],
      "rows": 41,
      "denominator": "analytic",
      "n": 340,
      "md5": "7b3c9d0e1f2a3b4c5d6e7f8091a2b3c4",
      "legend": "Table 1. Cohort characteristics and wearable data availability by procedure group. Percentages are computed from the rounded numerator over the rounded denominator and printed to zero decimals.",
      "footer_file": null
    },
    "table2": {
      "file": "tables-csv/table2_adjusted_debt.csv",
      "columns": [
        "row_order",
        "Procedure group",
        "Episodes",
        "Complete windows",
        "Unadjusted debt, median (IQR)",
        "Adjusted debt, activity days (95% CI)",
        "Thousand steps lost (95% CI)",
        "Adjusted mean normalized activity (95% CI)",
        "Reached 80% of baseline (95% CI)"
      ],
      "key_columns": ["Procedure group"],
      "rows": 5,
      "denominator": "analytic",
      "n": 340,
      "md5": "2f4a6b8c0d1e3f5a7b9c0d2e4f6a8b0c",
      "legend": "Table 2. Adjusted digital recovery debt by procedure group, in baseline-equivalent activity days lost across post-discharge day 1–35.",
      "footer_file": "tables-csv/table2_adjusted_debt_footer.csv"
    },
    "table3a": {
      "file": "tables-csv/table3_gate_part_a.csv",
      "columns": ["row_order", "Stage", "Definition", "Cervical decompression", "Cervical fusion", "Lumbar decompression", "Lumbar fusion", "All groups"],
      "key_columns": ["Stage"],
      "rows": 8,
      "denominator": "events_composite",
      "n": 40,
      "md5": "9a0b1c2d3e4f5061728394a5b6c7d8e9",
      "legend": "Table 3, part A. Feasibility gate ledger. The deciding count at stage E is below the disclosure floor and is therefore not printable.",
      "footer_file": null
    },
    "table3b": {
      "file": "tables-csv/table3_gate_part_b.csv",
      "columns": ["row_order", "Quantity", "Estimate (95% CI)", "Note"],
      "key_columns": ["Quantity"],
      "rows": 2,
      "denominator": "events_composite",
      "n": 40,
      "md5": "c3d4e5f60718293a4b5c6d7e8f901a2b",
      "legend": "Table 3, part B. The analysis the feasibility tier permits.",
      "footer_file": null
    },
    "table4": {
      "file": "tables-csv/table4_collider_comparison.csv",
      "columns": ["row_order", "Window group", "Episode-days at risk", "Acute-care events", "Crude rate per 1,000 episode-days", "Standardized rate per 1,000 episode-days"],
      "key_columns": ["Window group"],
      "rows": 3,
      "denominator": "analytic_person_days",
      "n": 9860,
      "md5": "6d8f0a2b4c6e80917a3b5c7d9e1f2a34",
      "legend": "Table 4. Acute-care event rate on episode-days with and without a computable step signal, crude and standardized to the recovery day bands. The comparison is unmatched and descriptive: post-discharge day drives both wear and events, and the two versions are reported so that a reader who finds them different is shown by how much rather than told which to believe. Neither version is a causal estimate.",
      "footer_file": null
    }
  },
  "suppressed": {
    "entries": [
      {
        "locus": "results.json",
        "path": "gate.stages[4].total",
        "file_row_key": null,
        "column": null,
        "kind": "count",
        "reason": "cell_below_threshold",
        "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
        "rule": "R1 cell below floor"
      },
      {
        "locus": "results.json",
        "path": "attrition.rungs[17].n_dropped",
        "file_row_key": null,
        "column": null,
        "kind": "count",
        "reason": "cell_below_threshold",
        "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
        "rule": "R1 cell below floor"
      },
      {
        "locus": "results.json",
        "path": "debt.by_group[0].share_zero_debt",
        "file_row_key": null,
        "column": null,
        "kind": "percentage",
        "reason": "cell_below_threshold",
        "reason_display": "20 or fewer, suppressed per All of Us dissemination policy",
        "rule": "R1 cell below floor"
      },
      {
        "locus": "results.json",
        "path": "debt.by_group[1].share_zero_debt",
        "file_row_key": null,
        "column": null,
        "kind": "percentage",
        "reason": "secondary_suppression",
        "reason_display": "suppressed to protect a suppressed cell in the same total",
        "rule": "R1 secondary suppression"
      },
      {
        "locus": "figures-csv/figure3_forest.csv",
        "path": "",
        "file_row_key": "3 / 8",
        "column": "estimate",
        "kind": "row",
        "reason": "not_estimable_cell_size",
        "reason_display": "not estimable (cell size)",
        "rule": "R1 contributing n below floor"
      },
      {
        "locus": "figures-csv/figure2_daily_activity.csv",
        "path": "",
        "file_row_key": null,
        "column": null,
        "kind": "series-point",
        "reason": "contributing_n_below_threshold",
        "reason_display": "20 or fewer contributors, suppressed",
        "rule": "R1 contributing n below floor"
      }
    ],
    "n_entries": 6,
    "by_reason": {"cell_below_threshold": 3, "secondary_suppression": 1, "not_estimable_cell_size": 1, "contributing_n_below_threshold": 1},
    "series_points_by_file": {"figures-csv/figure2_daily_activity.csv": 74}
  },
  "checks": {
    "entries": [
      {"slug": "ladder_closes", "display": "The unrounded attrition ladder closes at every rung and in every segment.", "passed": true, "detail": "", "local_reassert": true},
      {"slug": "no_cell_below_floor", "display": "No exported count is between 1 and the disclosure floor.", "passed": true, "detail": "", "local_reassert": true},
      {"slug": "csv_bytes_stable_across_two_runs", "display": "Two runs of the exporter wrote byte-identical comma-separated files.", "passed": true, "detail": "", "local_reassert": false}
    ],
    "n_checks": 13,
    "n_passed": 13,
    "n_failed": 0,
    "policy": "any failed check is a stop condition, not a warning"
  }
}
```

### 9.2 The fixture, and why the excerpt is not enough

An excerpt cannot be imported. `07_export.py` therefore carries a data-free mode:

```
python3 pipeline/07_export.py --fixture v1/local/fixtures/results
```

It writes a **complete** bundle at those dummy values: all **19** attrition rungs, all **5**
`by_group` entries, all **14** sensitivity rows, all **27** forest rows, all **286** Figure 2 rows,
all **44** Figure 4 rows, all six table CSVs, all five ledger CSVs, a real `MANIFEST.csv` with its
**16** data rows, and a real `MANIFEST.md5`. It touches no cloud resource, reads no CDR and needs no
credentials, so it runs locally in Phase 0 and costs nothing.

Where each number comes from, so a module asserting on one can check it rather than trust it:

| Count | Derivation |
|---|---|
| 19 attrition rungs | the rung table of `ANALYSIS-PLAN.md` section 2.6, transcribed in 3.3 and 7.2 |
| 5 `by_group` entries | 4 procedure groups plus `all_groups`, at `four_group`. **Data-dependent in a real run**: 3 at `two_group`, 1 at `single_group`. The fixture pins `four_group` so this count is 5 |
| 14 sensitivity rows | the ten ladder rows of `ANALYSIS-PLAN.md` section 6, with row 6 expanded to four wear definitions and row 7 to two baseline windows: `10 - 2 + 4 + 2 = 14`. The ten supplementary rows are excluded |
| 27 forest rows | block 1's 5 contrasts (7.3) + block 2's 14 sensitivity rows (7.8) + block 3's 8 subgroups (7.11) |
| 286 Figure 2 rows | 4 series over 90 days is 360 possible rows, less the 74 days below the floor that the absence rule removes: `360 - 74 = 286`, and 74 is `figures.figure2.days_dropped_by_group` summed, `34 + 21 + 8 + 11` |
| 44 Figure 4 rows | 2 series over the 22 offsets `-14` to `+7`, and **not** data-dependent: 4.4 keeps every row and suppresses the cells, so `2 x 22 = 44` on every run and at every tier |
| 16 manifest rows | `1 + 4 + 6 + 5`, per 3.8 |

The five ledger row counts the fixture pins, which the manifest example of 8.3 carries and which
`verify.py` re-derives on arrival:

| Ledger | Rows | Derivation |
|---|---|---|
| `ledger_concept_set_registry.csv` | 51 | 30 CPT-4 codes plus 21 ICD-10-PCS stems, from `cs_spine.registry_rows()` (5.6) |
| `ledger_variable_provenance.csv` | 12 | one row per analysis variable the `ledger_variable_missingness` stage emits (7.13, 7.14) |
| `ledger_exclusion_and_censoring_reasons.csv` | 20 | one row per `(step, reason_detail)` pair the `ledger_exclusion_reasons` stage emits (7.12) |
| `ledger_wear_availability_by_day.csv` | 318 | 4 groups over 90 days is 360 possible rows, less the 42 group-days whose `n_at_risk` failed the floor: `360 - 42 = 318`. **Bounded on both sides**: at most 360, and never fewer than `figure2_daily_activity.csv`'s 286, because `n_at_risk` on a group and day is at least that day's `n_contributing` and both files drop a row on the same test applied to their own count |
| `ledger_matched_set_sizes.csv` | 1 | the fixture pins tier 4, where 5.6 requires the single row saying the tier permits no Arm A analysis |

`tables-csv/table4_collider_comparison.csv` is 3 rows on every run and at every tier, per 5.7, so
the fixture pins 3.

**No count above moves at 1.8.0, and that is the check on the correction rather than a note about
it.** Reclassifying two exhibits as supplementary is a change to a **declaration**, not to a file
set: both files are still written, so the bundle is still 18 files, `MANIFEST.csv` still carries
16 data rows, `figures-csv/` still holds 4 files and `tables-csv/` still 6, Figure 4 is still 44
rows and Table 4 still 3. If any number in this section had moved, something had been deleted, and
deleting a supplementary exhibit is a worse outcome than mis-filing a primary one. What the
fixture gains is the classification itself: its `results.json` carries `exhibit` and `exhibit_set`
on all nine exhibit blocks, so `verify.py`'s budget assertion and any consumer that branches on
`exhibit_set` are exercised in Phase 0, against a bundle whose primary set is 3 and 3 and whose
supplementary set is Figure 4 and Table 4, before a single real count exists. It also carries
`denominators.event_centered_members` at the tier-4 value of 0, which is what lets a consumer
meet the `risk-set members` unit and an empty curve denominator without a paid run.

Every local module's `_run_self_test()` runs against the fixture. That is what lets `figures.py`,
`tables.py`, `manuscript.py`, `make_strobe.py` and `verify.py` be written, run and debugged before a
single real count exists, which is the whole point of locking this contract in Phase 0.

---

## 10. Compliance restatement

This section restates the boundary rules in the form `safe_export()` enforces them. It is a
restatement, not a new policy: the policy is `AOS-CS.md` section 9 and the All of Us Data Use and
Registration Agreement.

### 10.1 The cell rule

Every exported cell is `0`, or at or above the disclosure floor, or suppressed. There is no fourth
case. This holds for counts, for percentages, for medians and quartiles, for model estimates and for
the contributing n on every plot-ready row.

| Quantity | Disclosable when | Exported as |
|---|---|---|
| A count | `disclosable(n)`, asked of the **true** count | `round20(n)`, or exactly `0`; the cell that results then satisfies `is_legal_disclosed_count()` on the way out |
| A percentage | its numerator count is disclosable | integer percent, computed from the **rounded** numerator over the **rounded** denominator, zero decimals |
| A median, a quartile, a mean | the count of participants contributing to it is disclosable | the statistic at its unit's decimals, unrounded to 20 |
| A model estimate or interval | the count of participants contributing to the fit is disclosable | the estimate at its unit's decimals |
| A plot-ready series point | that day's contributing count is disclosable | the row, otherwise the row is absent |

**The two predicates, restated at the gate.** The `Disclosable when` column is asked of the true
count, before rounding, and it is what decides whether to suppress. The `Exported as` column is
what `round20` then produces, and every cell in it is tested again with `is_legal_disclosed_count()`
on the way out, because by that point the true count is gone and the only remaining question is
whether the rendered value is a legal one. Section 0 sets out why the two disagree on 20 and why
that disagreement is correct rather than a defect to reconcile.

**Percentages are computed from the rounded numerator over the rounded denominator and printed to
zero decimals.** Both halves matter and neither is optional. A one-decimal percentage against a
rounded denominator lets a reader back-calculate an exact small numerator, and a percentage computed
from the true numerator over a rounded denominator does the same. A **rounded** denominator makes
every printed percentage reproducible from the printed counts, which is the first thing a careful
reader checks, and it removes the raw denominator from the computation entirely. This is
`ANALYSIS-PLAN.md` section 8 rule 4, and `disclosure.n_pct` and `disclosure.prev` implement it.

It changes printed numbers, so it is pinned by example rather than by description:

```python
n_pct(31, 110)     # "40 (33%)".  round20(31) = 40, round20(110) = 120, 40/120 = 33%.
                   # NOT "40 (36%)", which is the rounded numerator over the RAW denominator.
n_pct(37, 1000)    # "40 (4%)".   Unchanged: 1000 is already a multiple of 20.
n_pct(31, 20)      # "40 (NA)".   A denominator of 20 or fewer is not disclosable, so no
                   # percentage is printed; `prev` prints the bare count in the same case.
```

**A percentage is suppressed whenever its count is suppressed**, without exception, because a
disclosed percentage times a disclosed denominator recovers the hidden count exactly. That holds for
a percentage whose numerator is a count of anything, including the bootstrap failure rate of
`meta.estimator`: its numerator is rounded and tested like every other.

Secondary suppression, restated: within any partition of a disclosed total, one suppressed member is
recoverable by subtraction, so at least two members are suppressed or none is.

### 10.2 The column rule

No identifier-like, date-like or near-unique column appears in any export.

| Refused | Test |
|---|---|
| Identifier-like column shape | an integer column that is also near-unique, which is the shape of a key regardless of what it is called |
| Identifier-like column name | the column name matches, case-insensitively, `person_?id`, `participant_?id`, `research_?id`, `\bpid\b`, `\bmrn\b`, `observation_id`, `visit_occurrence_id`, `procedure_occurrence_id`, `condition_occurrence_id`, `measurement_id`, `device_id`, `src_id`, `\buuid\b` |
| Date-like column name | the column name matches `date`, `datetime`, `dob`, `birth`, `_dt$`, `admit`, `discharge_d`, `start_d`, `end_d`, `calendar` |
| Date-like column content | any column whose dtype is a datetime, or whose string values parse as an ISO date for more than half the rows |
| Geographic or site column | the column name matches `zip`, `postal`, `address`, `\bstate\b`, `county`, `\bsite\b`, `ehr_site`, `location` |
| Near-unique value column | **any** column, numeric or string, on a frame of more than `NEAR_UNIQUE_MIN_ROWS` rows, more than `NEAR_UNIQUE_RATIO` of whose rows hold a distinct value. The test is pure cardinality and knows nothing about which lists this document publishes, which is why a `code` or `slug` column unique per row trips it and why `specification_columns` exists |
| Free text | any string column whose values are not drawn from the closed vocabulary this contract enumerates |
| Non-tabular payload | any file extension other than `.csv`, `.json` or `.md5` |

**Three permitted exceptions, all stated so they are not rediscovered as arguments later:**

1. **Relative day offsets are not dates.** `day` in Figure 2 is a post-discharge day from 1 to 90,
   and `baseline_first_day` is a postoperative day offset. An integer offset from a per-participant
   anchor carries no calendar information and is permitted. An absolute calendar date is refused. The
   name-based test above is deliberately narrow enough to let `day` through and wide enough to catch
   `discharge_date`.
2. **A banded calendar era over an aggregate is not a date.** The Table 1 row `Index era`, with
   levels `before 2020`, `2020–2021` and `2022 or later`, is a count over a disclosable
   number of episodes. It is the only calendar-derived content in the bundle.
3. **A day axis on a curve file is an axis, not a value column.** `day` in
   `figures-csv/figure2_daily_activity.csv` and in `ledgers-csv/ledger_wear_availability_by_day.csv`
   is the axis each of those two files is drawn along. It measures nothing about anybody. The
   disclosure content of a curve file lives in its count and estimate columns, which are
   `n_contributing`, the observed quantiles and the fitted band in the first file and `n_at_risk`,
   `n_valid_wear` and `share_valid_wear` in the second. **Every count and every share among those
   stays fully checked and always will**: floor-tested on its true value before rounding,
   gate-tested as a rendered cell before writing, with no exemption of any kind and none available.
   That is `n_contributing` in the first file and `n_at_risk`, `n_valid_wear` and
   `share_valid_wear` in the second, which is where a small cell could live. The six quantile and
   band columns of the first file are **not** counts, and exception 5 below exempts them, and only
   them, from the near-unique **cardinality** class, on an argument of its own; an earlier draft of
   this paragraph said no exemption was available to any column of either file, which was a promise
   this document could not keep at `single_group` and is corrected there rather than here. The axis
   itself is exempt from the near-unique refusal class and from the integer-shape form of the
   identifier-like class, which are the two classes it trips, and from nothing else.

   **Why it is granted.** The set of days present in the file is the published output of the
   suppression rule rather than a leak around it. The absence rule of 4.2 omits a day whose
   contributing count is not disclosable, so the days present are the days with more than 20
   contributors and the days absent are the days with 20 or fewer, which is the statement
   `ANALYSIS-PLAN.md` section 8 rule 2 exists to make in public. No exact small count is pinned by
   it: every withheld day is bounded only as at or below the floor. And the same set already
   crosses the boundary at `four_group` and at `two_group` without tripping anything, because four
   series repeat every day four times and the cardinality falls under the ceiling. A gate that
   refuses at `single_group` what it passes at `four_group`, with the disclosure content identical
   in both, is measuring cardinality and not disclosure. Left ungranted it would halt
   `07_export.py` mid-session on a paid Workbench run, at the one collapse level a small cohort is
   most likely to land on, and both affected files land there together.

   **What it does not reach.** Any column whose values are participant-derived. This exception is a
   statement about an axis, an index this study fixed in advance and printed in this document as
   post-discharge day 1 to 90, and it does not travel to a count, a percentage, a median, a
   quartile, an estimate or any other measured quantity, on these two files or on any other. A
   third file that believes it needs the exception gets an amendment here, with its own argument,
   and never a call-site argument added to make an error go away.

   **How it reaches the call site, given that the module has one lever and is final.**
   `export_violations()` takes exactly one exemption argument, `specification_columns`, and 11.3
   makes `pipeline/disclosure.py` authoritative over its own signature, so `07_export.py` passes
   `specification_columns=["day"]` on these two files and on no others. That is the **mechanism**;
   the **authorization** is this exception and not the whitelist below, and the two are deliberately
   kept apart. The whitelist's entire value is that every entry meets one criterion, would this
   column read exactly the same if the cohort were a different hundred people, and `day` does not
   meet it, because which days are present depends on the data. Filing `day` there would corrupt
   that criterion for every future entry. `verify.py` therefore tests a `specification_columns=`
   call site against the **union of three registers**, the whitelist below, the two files named in
   this exception and the twelve columns of exception 5, and reports which of the three authorized
   the column.

**A fourth exception, declared per column rather than inferred: `specification_columns`.** A registry
of the codes in the locked concept set has one row per code, so its `code` column is 100% distinct by
construction and trips the near-unique test on any frame wider than the floor. The rule is right in
general and wrong here: a published list of CPT-4 and ICD-10-PCS codes is a property of the
specification and identifies nobody. `export_violations()` and `safe_export()` therefore take
`specification_columns`, a sequence of column names the author **declares** hold vocabulary or
specification values rather than participant-derived ones.

What it does, and more importantly what it does not do:

| | |
|---|---|
| Exempts from | the **near-unique** refusal class, and the **identifier-like** refusal class in both its forms, by column name and by integer shape |
| Exempts from nothing else | the date-like name and dtype tests still run, the banned-character test still runs, the count tests still run, the percentage and partition tests still run, and the `kind` string-versus-numeric test still runs |
| Granularity | per column, by name. There is no file-level, no `kind`-level and no directory-level blanket, and none is going to be added: a blanket is invisible both at the call site that needs it and in review, which is the pair of properties that makes an exemption dangerous |
| A declared column absent from the frame | is itself a violation, in this class as in every class that takes column names. Declaring an exemption on a column that is not there is how a check gets quietly switched off on the one column it was written to guard, one rename later |
| Who may declare it | only the files and columns in the table below, plus the `day` axis on the two files exception 3 names and the twelve statistic columns exception 5 names. `verify.py` reads every `specification_columns=` call site in `pipeline/` and fails on a column that no register authorizes, and names the register that did authorize the ones it passes |

**A fifth exception, for a rounded aggregate statistic on a frame of prespecified strata.** The
numbering runs 1, 2 and 3 for the named exceptions above, 4 for `specification_columns` and its
whitelist, and 5 for this one. The numbers are cited by number in this document, in `07_export.py`
and in `verify.py`, so they are not renumbered when one is inserted.

**The problem, measured rather than predicted.** `figures-csv/figure3_forest.csv` has 27 rows and
carries `estimate`, `ci_lo` and `ci_hi` at the decimals of `activity_days`, which is one.
Twenty-seven prespecified analyses over one cohort produce twenty-seven well-separated
numbers, and three columns of them at one decimal are near-certain to exceed the ninety percent
ceiling of the near-unique class. The whitelist above grants that file `slug` and `display_label`
and nothing else, so nothing catches this until `safe_export()` refuses the frame, and
`07_export.py` refuses it in Phase 4, inside the perimeter, on a paid Workbench session, after every
query has been billed. The `--fixture` bundle passes only by accident: sixteen of its twenty-seven
`estimate` values happen to be distinct, for a ratio of 0.59 against a ceiling of 0.90, and the
eleven that repeat do so because the dummy values were typed rather than fitted. The same
shape reaches `figures-csv/figure4_event_centered_activity.csv`, whose three quantile columns run
over 44 rows, and `figures-csv/figure2_daily_activity.csv` at `single_group`, where one series
leaves at most ninety rows and a smooth fitted band can approach one distinct value per row.

**Why it is granted.** The near-unique rule is a cardinality proxy for a **row-level key**: its own
entry in the table above says so, and the sentence that follows the whitelist says why a per-person
total carried to six decimals is a fingerprint. Neither describes these columns. On all three files
a row is a **prespecified stratum**, not a person: a named analysis in 7.3, 7.8 and 7.11, a group
and post-discharge day, a series and an event offset. This document publishes the full list of
strata in advance, so the number of rows is decided by how many strata were prespecified and not by
how many people are in the cohort. And the protection that matters is already carried and is not
touched: **every row of all three files carries its own contributing count, floor-tested on its true
value before it is rounded**, and a row whose count fails the floor carries `SUPPRESSED` in every
statistic column or is absent from the file entirely. So a statistic in these columns is a summary
over more than twenty people by construction, whatever its cardinality, and cardinality is
measuring the value space of a rounded statistic rather than the identifiability of a row. What
makes that value space small enough to be worth measuring at all is the rounding rule of 2.4, which
is a precondition of this exception and not an alternative to it: at `normalized_activity`'s two
decimals a Figure 2 column of 286 rows holds about seventy distinct values, and at three decimals it
would hold 286.

| | |
|---|---|
| Exempts from | the **near-unique** refusal class, and nothing else |
| Exempts from nothing else | the identifier-like tests still run in both forms, the date-like tests still run, the banned-character test still runs, the count tests still run on every count column beside these, the percentage and partition tests still run, and the `kind` string-versus-numeric test still runs |
| Granularity | per column, by name, on the three files named below and no others |
| Precondition | the value is rounded to its unit's decimals (2.4) before the frame is built, and the row carries a floor-tested contributing count. A column meeting neither is not eligible under this exception or any other |
| What it does not reach | a **count**, a **percentage** or a **share** column, on these three files or on any other. Those are the columns the near-unique rule exists for and no exception in this document reaches them |

| File | Columns exempted from the near-unique class |
|---|---|
| `figures-csv/figure2_daily_activity.csv` | `observed_median`, `observed_p25`, `observed_p75`, `fitted_marginal`, `fitted_lo`, `fitted_hi` |
| `figures-csv/figure3_forest.csv` | `estimate`, `ci_lo`, `ci_hi` |
| `figures-csv/figure4_event_centered_activity.csv` | `observed_median`, `observed_p25`, `observed_p75` |

Like exception 3, this is a register of its own and not a row in the whitelist below, because the
whitelist's criterion is "would this column read exactly the same if the cohort were a different
hundred people" and a fitted median plainly would not. Filing these twelve columns there would
corrupt that criterion for every future entry, in exactly the way 10.2 already records that filing
`day` there would have. `verify.py` therefore tests a `specification_columns=` call site against the
**union of three registers**, the whitelist, exception 3 and this exception, and reports which one
authorized each column.

**The whitelist. Every grant is a file, a column and a reason, so an over-broad one is visible here
rather than buried in a call site:**

| File | Columns | Why these are specification values and not participant-derived ones |
|---|---|---|
| `ledgers-csv/ledger_concept_set_registry.csv` | `code` | one row per code or stem, so unique by construction over 51 rows. The CPT-4 code and the four-character ICD-10-PCS stem are published vocabulary, straight out of `cs_spine.registry_rows()`, which reads no data |
| `ledgers-csv/ledger_variable_provenance.csv` | `variable`, `display_label`, `derivation` | one row per analysis variable, so all three are unique by construction. All three are written by the analyst, in this document's own vocabulary; none is measured. `n_total` and `n_missing` on the same row are counts and are **not** exempt |
| `ledgers-csv/ledger_exclusion_and_censoring_reasons.csv` | `reason_detail` | one prespecified sentence per row, so unique by construction. `n_episodes`, `n_denominator` and `share_of_step_dropped` on the same row are **not** exempt |
| `figures-csv/figure3_forest.csv` | `slug`, `display_label` | 27 rows, one per prespecified analysis, both drawn verbatim from the label table of section 7. What is unique here is the list of analyses this study planned, which this document publishes in full |
| `tables-csv/table1_cohort_characteristics.csv` | `row_order` | a contiguous 1 to N print ordinal, fixed by the row-order table of 5.1. It carries no information beyond the print order this document already publishes, and Table 1 is the one table CSV whose row count exceeds the floor |
| `figures-csv/figure1_strobe_ladder.csv` | `step`, `slug`, `display_label`, `reason`, `reason_display` | one row per attrition rung, and all five columns are the rung vocabulary of `ANALYSIS-PLAN.md` section 2.6, transcribed into 3.3 and 7.2 and printed from there by lookup. `step` is the plan's own ordinal, `slug` and `reason` are its tokens, `display_label` and `reason_display` are its two printed sentences, and not one of the five would read differently for a different hundred people. The four count columns `n_in`, `n_dropped`, `n_out` and `n_carried_forward` are **not** granted and are not eligible under any reading, and `closes_exact` is not granted because whether a rung's arithmetic closed is a fact about the data |



**The row floor, swept across the whole bundle, so the next near miss is not found by accident.**
The Figure 1 grant above was added at 1.6.1 to close a margin of one row that nobody had measured.
Every bundle file's row count is fixed by a grain this document declares, so the margin is
computable rather than a matter of opinion, and it is computed here for every file that is not
already over the floor. `NEAR_UNIQUE_MIN_ROWS` is the floor, the test is strictly greater than it,
and a file at the floor exactly is one row from arming.

| File | The grain that fixes its row count | Rows | Can that grain cross the floor | What would trip, and which register holds it |
|---|---|---|---|---|
| `figures-csv/figure1_strobe_ladder.csv` | one row per attrition rung, `ANALYSIS-PLAN.md` 2.6 | 19, a margin of one | **yes, and it has already moved twice** | `step`, `slug`, `display_label`, `reason`, `reason_display`, all granted in the whitelist above as of 1.6.1; `n_in` and `n_out`, held by no register, see 11.4 |
| `ledgers-csv/ledger_exclusion_and_censoring_reasons.csv` | one row per reason within a rung, 7.12, so it grows with the ladder | 20, a margin of zero | **yes, and it is at the floor now** | `reason_detail` alone, already granted in the whitelist above. `step`, `slug` and `display_label` repeat within a rung and sit at 0.30, 0.30 and 0.25 against a ceiling of 0.90 |
| `ledgers-csv/ledger_variable_provenance.csv` | one row per analysis variable, the `ledger_variable_missingness` stage of `pipeline/build_all.sql` | 12, a margin of eight | only if the analysis gains nine variables | `variable`, `display_label` and `derivation` are granted; `missing_handling` is **not**, and is the one row this table would need |
| `tables-csv/table2_adjusted_debt_footer.csv` | one row per footer item, 5.3 | 15, a margin of five | no, 5.3 fixes the list | `Footer item`, `Value`, `Source key` and `row_order` would all trip together. **The margin was eight at 1.8.0 and is five at 1.9.0**, because 5.3's list grew by the three STROBE item 16(a) rows. The list is fixed by this document, so the count moves only when this document moves it, but the margin is recorded here rather than recomputed later because it is now the second-smallest in the bundle |
| `tables-csv/table3_gate_part_a.csv` | one row per gate stage, `A` to `F` with `D` split three ways, 5.4 | 8, a margin of twelve | no, 5.4 fixes eight | `Definition` and `row_order` |
| `tables-csv/table3_gate_part_b.csv` | one row per key of `gate.arm_a.estimates` (3.7), or the two tier rows | 2, at most 11 | no, 3.7 fixes the keys | `Quantity`, `Estimate (95% CI)`, `Note` and `row_order` |
| `ledgers-csv/ledger_matched_set_sizes.csv` | one row per matched-set size | 1, at most 6 | no: `ANALYSIS-PLAN.md` 4.5 caps sampling at five controls per case | `set_size`, and it would need an exception of its own rather than a row here, because which sizes occur depends on the data |
| `tables-csv/table2_adjusted_debt.csv` | one row per procedure group plus the pooled row, 2.4 | 5, a margin of fifteen | no, 2.4 fixes the groups | every string column, all five of them |
| `tables-csv/table4_collider_comparison.csv` | three window groups, 5.7 | 3, a margin of seventeen | no, 5.7 fixes three | `Window group` and `row_order` |

The six files already over the floor are not in the sweep's scope because their exposure is not
hypothetical and each is already answered: `figures-csv/figure2_daily_activity.csv` at 286 rows and
`ledgers-csv/ledger_wear_availability_by_day.csv` at 318 by exception 3 and exception 5,
`figures-csv/figure3_forest.csv` at 27 and `ledgers-csv/ledger_concept_set_registry.csv` at 51 by
this whitelist and exception 5, `figures-csv/figure4_event_centered_activity.csv` at the 44 rows
4.4's window fixes by exception 5, and `tables-csv/table1_cohort_characteristics.csv` at 41 by the
`row_order` grant above.

**Two of the nine are worth saying out loud.** The exclusion and censoring ledger is **at** the
floor and not under it. Its twenty rows are one row per reason within a rung, so it grows whenever
the ladder does, and the only thing between it and the refusal is that `reason_detail` happens to be
its one column above the ceiling and was granted at 1.2.0 on its own argument. It is safe, and it is
safe for a reason unconnected to the reason it is close, which is the shape of a near miss rather
than of a margin. And the provenance ledger has one column, `missing_handling`, that this table does
not reach although both its neighbours `display_label` and `derivation` do; it holds one prespecified
sentence per variable, 7.14 owns it, and it would meet this table's criterion on the day it were
needed. 11.4 records the trigger for both rather than leaving either to be rediscovered.

**The ownership register: what each column actually holds, and who owns its values.** A grant above
says a column is a specification value rather than a participant-derived one. It does not say where
the value comes from, and an exemption whose justification points at a table that does not exist is
not an exemption: it is an unowned string with an argument attached. The register below closes that.
A grant classed **display label** or **prespecified sentence** must name a section 7 subsection that
exists and carries the stated number of entries. That is a checkable property and it is checked.
Before contract 1.5.0 it did not hold: 5.6 classed `reason_detail` a prespecified sentence, this
section exempted it on that ground, section 7 carried no table for it, and `pipeline/03_cohort.py`
therefore defined a second copy of the table locally in order to have anything to print. Two copies
of a label table, one of them unowned, is the drift this document exists to prevent.

**What the register covers, and it is wider than the grants at contract 1.6.1.** It carries three
kinds of row, and the `Exempt under` column says which kind each is, so the register can be complete
without any row in it quietly becoming an exemption:

1. **Every exempted column**, once: the thirteen whitelist grants, the two `day` grants of
   exception 3 and the twelve statistic grants of exception 5. Each names the register that authorizes it. The
   register invents no exemption and omits none, and that is an equality rather than an inclusion.
2. **Every column in the bundle whose cells are strings that are not display strings**, which is the
   set section 6's rule used to describe wrongly. Five columns across three files hold machine
   tokens and would otherwise reach `verify.py`'s snake_case assertion on arrival, after the export.
   These rows read `not exempt`, and they change no check: they say what a column holds so a rule
   about printed strings knows to skip it.
3. **Every column of `ledgers-csv/ledger_variable_provenance.csv`**, all ten. That one file mixes
   machine tokens, display labels, prespecified sentences and counts in ten columns, and it is the
   file both the 1.5.0 and the 1.6.0 ownership defects came out of, one column pair apart. Carrying
   it whole makes "which section owns this cell" answerable for every column of it by reading one
   table, and makes a new column with no owner a failing check rather than a passing export.

A row classed **count** is on the register to record the opposite of an exemption: those two columns
are floor-tested, gate-tested and named in `count_cols`, and nothing here reaches them.

| Column | What the values are | Class | Owner of the values | Entries | Exempt under |
|---|---|---|---|---|---|
| `ledgers-csv/ledger_concept_set_registry.csv` `code` | CPT-4 codes and four-character ICD-10-PCS stems of the locked set | vocabulary code | `pipeline/cs_spine.py`, through `registry_rows()` | 51 | 10.2 whitelist |
| `ledgers-csv/ledger_variable_provenance.csv` `variable` | the analysis-variable token, machine-read and never printed | machine token | the `ledger_variable_missingness` stage of `pipeline/build_all.sql` | 12 | 10.2 whitelist |
| `ledgers-csv/ledger_variable_provenance.csv` `display_label` | the printed name of the variable | display label | section 7.13 | 12 | 10.2 whitelist |
| `ledgers-csv/ledger_variable_provenance.csv` `derivation` | one prespecified sentence per variable, saying how it is computed | prespecified sentence | section 7.13 | 12 | 10.2 whitelist |
| `ledgers-csv/ledger_variable_provenance.csv` `role` | the variable's role in the model, one of the six values 5.6 fixes | machine token | section 5.6 | 6 | not exempt |
| `ledgers-csv/ledger_variable_provenance.csv` `source_table` | the derived table the variable is measured on | machine token | `pipeline/build_all.sql`, described in `DAG-SCHEMA.md` | 12 | not exempt |
| `ledgers-csv/ledger_variable_provenance.csv` `source_concept_set` | the concept-set module a variable resolves through, or empty | machine token | `pipeline/cs_spine.py` and the condition concept sets of `pipeline/build_all.sql` | 12 | not exempt |
| `ledgers-csv/ledger_variable_provenance.csv` `unit` | the printed unit of the variable, or empty where it is categorical | display label | section 7.14 | 12 | not exempt |
| `ledgers-csv/ledger_variable_provenance.csv` `n_total` | the size of the population the variable is measured on | count | section 5.6, floor-tested and named in `count_cols` | 12 | not exempt |
| `ledgers-csv/ledger_variable_provenance.csv` `n_missing` | how many of them are missing | count | section 5.6, floor-tested against its own value and its complement | 12 | not exempt |
| `ledgers-csv/ledger_variable_provenance.csv` `missing_handling` | one prespecified sentence per variable, saying what the analysis does with a missing value | prespecified sentence | section 7.14 | 12 | not exempt |
| `ledgers-csv/ledger_exclusion_and_censoring_reasons.csv` `reason_detail` | one prespecified sentence per reason within a rung | prespecified sentence | section 7.12 | 20 | 10.2 whitelist |
| `ledgers-csv/ledger_exclusion_and_censoring_reasons.csv` `slug` | the rung slug the row is counted under, machine-read and never printed | machine token | section 7.2, emitted by `pipeline/03_cohort.py` | 19 | not exempt |
| `tables-csv/table2_adjusted_debt_footer.csv` `Source key` | the dotted `results.json` path the footer value came from | machine token | section 5.3 | 15 | not exempt |
| `figures-csv/figure3_forest.csv` `slug` | the slug of a prespecified analysis, machine-read | machine token | sections 7.3, 7.8 and 7.11 | 27 | 10.2 whitelist |
| `figures-csv/figure3_forest.csv` `display_label` | the printed label of that analysis | display label | sections 7.3, 7.8 and 7.11 | 27 | 10.2 whitelist |
| `figures-csv/figure1_strobe_ladder.csv` `step` | the rung's ordinal position on the ladder | print ordinal | `ANALYSIS-PLAN.md` section 2.6, transcribed in 3.3 and 7.2 | 19 | 10.2 whitelist |
| `figures-csv/figure1_strobe_ladder.csv` `slug` | the rung slug, machine-read and never printed | machine token | section 7.2, emitted by `pipeline/03_cohort.py` | 19 | 10.2 whitelist |
| `figures-csv/figure1_strobe_ladder.csv` `display_label` | the printed name of the box of survivors on the ladder spine | display label | section 7.2 | 19 | 10.2 whitelist |
| `figures-csv/figure1_strobe_ladder.csv` `reason` | the rung's reason token, derived from `kind` and `slug` by the rule of 3.3 and never printed | machine token | section 3.3 | 19 | 10.2 whitelist |
| `figures-csv/figure1_strobe_ladder.csv` `reason_display` | the printed sentence in the right-hand exclusion box | prespecified sentence | section 7.2 | 19 | 10.2 whitelist |
| `tables-csv/table1_cohort_characteristics.csv` `row_order` | the contiguous print ordinal 1 to N | print ordinal | the row-order table of section 5.1 | the rows of that table | 10.2 whitelist |
| `figures-csv/figure2_daily_activity.csv` `day` | post-discharge day, the axis the file is drawn along | print ordinal | exception 3 above | 90 | 10.2 exception 3 |
| `ledgers-csv/ledger_wear_availability_by_day.csv` `day` | post-discharge day, the axis the file is drawn along | print ordinal | exception 3 above | 90 | 10.2 exception 3 |
| `figures-csv/figure2_daily_activity.csv` `observed_median` | the observed median normalized activity of a group and day, rounded to two decimals | aggregate statistic | section 4.2, emitted by `pipeline/05_analysis_drd.py` | 1 per row | 10.2 exception 5 |
| `figures-csv/figure2_daily_activity.csv` `observed_p25` | the same at the lower quartile | aggregate statistic | section 4.2 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure2_daily_activity.csv` `observed_p75` | the same at the upper quartile | aggregate statistic | section 4.2 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure2_daily_activity.csv` `fitted_marginal` | the marginal fitted value of a group and day | aggregate statistic | section 4.2 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure2_daily_activity.csv` `fitted_lo` | the lower edge of its 95% marginal band | aggregate statistic | section 4.2 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure2_daily_activity.csv` `fitted_hi` | the upper edge of its 95% marginal band | aggregate statistic | section 4.2 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure3_forest.csv` `estimate` | the point estimate of a prespecified analysis, rounded to its unit's decimals | aggregate statistic | sections 3.5 and 3.6, emitted by `pipeline/05_analysis_drd.py` | 1 per row | 10.2 exception 5 |
| `figures-csv/figure3_forest.csv` `ci_lo` | the lower confidence bound of that analysis | aggregate statistic | sections 3.5 and 3.6 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure3_forest.csv` `ci_hi` | the upper confidence bound of that analysis | aggregate statistic | sections 3.5 and 3.6 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure4_event_centered_activity.csv` `observed_median` | the observed median normalized activity of a series and event offset | aggregate statistic | section 4.4, emitted by `pipeline/06_analysis_gate.py` | 1 per row | 10.2 exception 5 |
| `figures-csv/figure4_event_centered_activity.csv` `observed_p25` | the same at the lower quartile | aggregate statistic | section 4.4 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure4_event_centered_activity.csv` `observed_p75` | the same at the upper quartile | aggregate statistic | section 4.4 | 1 per row | 10.2 exception 5 |
| `figures-csv/figure1_strobe_ladder.csv` `kind` | the rung's kind, one of the three 3.3 fixes: `exclusion`, `conversion`, `terminal` | machine token | section 3.3 | 3 | not exempt |
| `figures-csv/figure1_strobe_ladder.csv` `unit` | the unit the rung's counts are in, one of the five the three segments of 3.3 span | machine token | sections 3.3 and 4.1 | 5 | not exempt |
| `figures-csv/figure1_strobe_ladder.csv` `box_side` | which side of the ladder the row is drawn on, `main` or `exclusion` | machine token | section 4.1 | 2 | not exempt |
| `figures-csv/figure2_daily_activity.csv` `group_slug` | the procedure-group token of the series, at the collapse level `cohort.collapse_level` records | machine token | section 7.1 | 7 | not exempt |
| `figures-csv/figure3_forest.csv` `unit` | the unit slug the row's estimate is on, machine-read and never printed | machine token | section 2.4 | 15 | not exempt |
| `figures-csv/figure3_forest.csv` `axis` | the axis the row is drawn against, `primary` or a named alternative | machine token | sections 3.6 and 4.3 | 2 | not exempt |
| `figures-csv/figure3_forest.csv` `render` | how the row is drawn, `marker`, `panel` or `text` | machine token | sections 3.6 and 4.3 | 3 | not exempt |
| `figures-csv/figure4_event_centered_activity.csv` `series_slug` | the series token, `event_case` or `matched_control`, machine-read and never printed | machine token | section 7.15 | 2 | not exempt |
| `ledgers-csv/ledger_wear_availability_by_day.csv` `group_slug` | the procedure-group token of the row, the same vocabulary Figure 2 draws | machine token | section 7.1 | 7 | not exempt |

**The machine-token column sweep, run across the whole bundle at 1.9.1, so the next unowned
column is not found by `verify.py` on arrival.** The register's second clause has always claimed
**every** column in the bundle whose cells are strings that are not display strings, and until
1.9.1 it carried only the five that section 6's blanket rule had described wrongly. `verify.py`
then found a sixth on arrival, `series_slug` on Figure 4, and this document has now recorded that
same defect three times: at 1.5.0 for `reason_detail`, at 1.6.0 for the provenance ledger's column
pair, and here. **A third instance is evidence that the row is the wrong unit of work.** So the
question was asked of every column of every bundle file at once, and the answer is written down for
each rather than left to be rediscovered.

The sweep's scope is the register's own second clause: a column whose cells are **strings** that
are not display strings. It therefore reaches no count, no ordinal and no boolean -- `row_order`,
`step`, `group_order`, `series_order`, `series_segment`, `block`, `day`, `day_relative_to_event`,
`closes_exact`, `estimable`, `is_primary`, `plotted`, `in_accrual_window`, `is_add_on` and
`is_junction` hold no strings for a prose rule to fire on -- and it excludes `MANIFEST.csv`, whose
nine columns 8.3 owns one by one and which `verify.py` audits there. Two tests were applied to each
column in scope, deliberately both: **does a row of this register classify the (file, column)
pair**, and **does section 6 name the column**. A column needs both, and the two failure modes are
different: a column section 6 names but the register does not is an unowned string with a rule
attached, and a column the register classifies but section 6 does not name is a rule a reader of
section 6 cannot apply.

| Column | Carries a token today | In the register before 1.9.1 | Named in section 6 before 1.9.1 | What the sweep did |
|---|---|---|---|---|
| `figures-csv/figure1_strobe_ladder.csv` `slug` | yes | yes | yes | nothing; it was already whole |
| `figures-csv/figure1_strobe_ladder.csv` `reason` | yes | yes | yes | nothing |
| `figures-csv/figure1_strobe_ladder.csv` `kind` | no, `exclusion` and its two siblings carry no underscore | **no** | yes | register row added |
| `figures-csv/figure1_strobe_ladder.csv` `unit` | no, `episodes to events` is spaced rather than underscored | **no** | yes | register row added |
| `figures-csv/figure1_strobe_ladder.csv` `box_side` | no, `main` and `exclusion` carry no underscore | **no** | **no** | **the third instance**: register row added and the name added to section 6 |
| `figures-csv/figure2_daily_activity.csv` `group_slug` | yes, `cervical_decompression` | **no** | yes | register row added |
| `figures-csv/figure3_forest.csv` `slug` | yes | yes | yes | nothing |
| `figures-csv/figure3_forest.csv` `unit` | yes, `activity_days` | **no** | yes | register row added |
| `figures-csv/figure3_forest.csv` `axis` | yes, `latent_logit_shift` | **no** | yes | register row added |
| `figures-csv/figure3_forest.csv` `render` | no, `marker` and `panel` carry no underscore | **no** | yes | register row added |
| `figures-csv/figure4_event_centered_activity.csv` `series_slug` | yes, `event_case` | **no** | **no** | **the reported finding**: register row added and the name added to section 6 |
| `ledgers-csv/ledger_exclusion_and_censoring_reasons.csv` `slug` | yes | yes | yes | nothing |
| `ledgers-csv/ledger_variable_provenance.csv` `variable` | yes | yes | yes | nothing |
| `ledgers-csv/ledger_variable_provenance.csv` `role` | no, `covariate` and `exposure` carry no underscore | yes | yes | nothing; the register already reached it |
| `ledgers-csv/ledger_variable_provenance.csv` `source_table` | yes, `drd_daily` | yes | yes | nothing |
| `ledgers-csv/ledger_variable_provenance.csv` `source_concept_set` | yes, `cs_spine` | yes | yes | nothing |
| `ledgers-csv/ledger_wear_availability_by_day.csv` `group_slug` | yes, `cervical_decompression` | **no** | **no**: only under the `figures-csv` row, and this is a ledger | register row added, and the name added to section 6's `tables-csv` row |
| `tables-csv/table2_adjusted_debt_footer.csv` `Source key` | yes, a dotted path | yes | yes | nothing |

**Two things the sweep says that a sixth register row would not have.** The first is that four of
the nine columns it added carry **no** machine token today: `kind`, `unit` and `box_side` on the
ladder and `render` on the forest are machine columns whose present vocabularies happen to spell
without an underscore. A sweep driven by what `verify.py` reports would never have reached them,
because nothing has fired on them and nothing will until one value gains an underscore, at which
point it fires **on arrival, after the export**, which is the failure mode this whole section
exists to move earlier. The second is `group_slug` on the wear-availability ledger: section 6 names
`group_slug` under its `figures-csv` row, and that file is a ledger, so the name was right and the
surface it was listed under was wrong. Reading names without their surfaces is the same mistake in
the other direction from `unit`, which is a machine token on a figure and a printed label on the
provenance ledger.

**What the register now guarantees, and it is a set equality rather than an inclusion.** Every
column of the bundle whose cells are strings that are not display strings has a row here, and every
row here names a column of a file this document declares. That is checkable in both directions, and
both directions are checked: `verify.py` sweeps the arriving bundle for a column carrying a token
that no register classifies, and the contract checker reads this table against the column lists of
sections 4 and 5. A tenth machine-token column arriving with no row is a failing check rather than
a passing export, which is what clause 2 promised and what, for four versions, it only partly did.

The register does not widen any exemption and does not create one: it says, for columns whose values
section 6's blanket rule does not describe, where those values live. The classes that carry a hard
obligation are the two that print. A **display label** and a **prespecified sentence** are both
printed verbatim into a cell, so both must exist in section 7 before the file can be written, and the
count in the last column is checked against the producer rather than against this document: the 20
against the `ledger_exclusion_reasons` stage of `pipeline/build_all.sql`, the 12 against the
`ledger_variable_missingness` stage, the 51 against `cs_spine.registry_rows()`, and the 27 against
7.3 plus 7.8's plotted table plus 7.11. A **machine token**, a **vocabulary code**, a **print
ordinal**, an **aggregate statistic** and a **count** are not printed as prose and carry no section 7
obligation, which is why `code` and `row_order` have no label table and are not going to grow one.
An `Entries` cell reading `1 per row` says the column holds one measured value per row rather than a
vocabulary of a fixed size, which is what an aggregate statistic is and is why no section 7 table
could own it.

**The `row_order` grant is conditional on contiguity, and the condition is asserted rather than
assumed.** That grant exempts `tables-csv/table1_cohort_characteristics.csv` from the near-unique
class and from the integer-key shape, which is the whole of what the gate would otherwise notice
about that column. A contiguous `1` to N ordinal carries nothing beyond the print order this
document already publishes, and that is what makes the grant safe. A **gap** in it would carry
something else. It would say that a prespecified row of the 5.1 row-order table was not written,
and which one, and the exemption is precisely what stops the gate noticing. So the safety is a
property of the values and not of the column, and it has to be checked on the values.
**`07_export.py` MUST assert `list(df["row_order"]) == list(range(1, len(df) + 1))` on the Table 1
frame before it calls `safe_export()`, and halt on a mismatch.** It is an assert and never a repair:
renumbering to close the gap would hide the dropped row, and the dropped row is the finding. 5.1
already requires that a row whose every cell is suppressed is still written, so this assertion
cannot fire on a suppression; it fires when a row went missing for some other reason, which is a bug
in the exporter and not a disclosure event. `verify.py` re-asserts it on arrival, like every other
rule in 11.1.

**Nothing else may enter this whitelist beyond the classes stated, and the near-misses are
recorded so they are not rediscovered as arguments.** No column holding a count, a percentage, a median, a quartile or a
model estimate is eligible for **this table** under any reading, and the criterion is the one stated
above it: a count and a fitted median both change when the cohort changes, so neither is a
specification value. The twelve statistic columns of exception 5 are exempted from one class on a
different criterion, in a different register, and are named there; a count column is exempted by
nothing, anywhere, and a per-person total carried to six decimals is a fingerprint in exactly the
way a name is.

`figure1_strobe_ladder.csv` **is in the table as of 1.6.1, and until 1.6.1 it needed nothing.**
Nineteen rows is not more than the floor, so the near-unique class never armed on it and no column
of it was ever tested for cardinality. That is a margin of one row, on a ladder that has already
moved twice in this project, from fifteen rungs to nineteen, and a twenty-first rung arms the class
on five of its columns at once. The five are the rung vocabulary, each was put to this table's
criterion on its own, and each passes it: a step number, a slug, a printed box label, a reason token
and a printed reason sentence all read exactly the same for a different hundred people, because all
five are transcribed from `ANALYSIS-PLAN.md` section 2.6 and none is measured. That is what makes
this table the right register for them, and not exception 3.

**What the grant does not do is make a grown ladder exportable, and that is stated here rather than
discovered inside the perimeter.** Measured on the shipped module, a twenty-first rung also carries
`n_in` and `n_out` over the ceiling, with the integer-key shape besides, and those are counts: they
are exempted by nothing in this document, as the paragraph above says and as this one does not
weaken. So a twenty-first rung still halts the export, on two columns rather than seven, and that
residue is a dated obligation in 11.4 with the decision it would take written out. A grant that
closed five sevenths of a refusal and let the file read as safe would be worse than no grant, which
is why the arithmetic is in 11.4 and in the checker rather than in a reassurance here.

And the `day` axis of
`figure2_daily_activity.csv` and of `ledger_wear_availability_by_day.csv` is **deliberately absent
from this table**: at `single_group` each file is one series, so `day` holds one distinct value per
row and trips the same rule, but a day axis is not a specification value under this table's
criterion, because which days are present depends on the data. It is authorized by **exception 3**
above instead, which is a different criterion kept in a different register. An earlier draft of this
paragraph left that collision unresolved and said the fix would be an amendment to this table; the
amendment landed as the exception rather than as a row here, and until it landed a `single_group`
run would have halted mid-export. Nothing else is authorized by either route: a third file that
needs one gets an amendment to this table or to exception 3, and it is never a
`specification_columns=` argument added at the call site to make an error go away.

**The closed-vocabulary rule for string columns.** Every string cell in every CSV is drawn from a
vocabulary this contract enumerates: the approved display vocabulary of section 2.5, the fixed token
`SUPPRESSED`, or the booleans `true` and `false`. **This is a rule `verify.py` checks on arrival, and
it is not something `safe_export()` infers.** An earlier draft of this section said `safe_export()`
checks membership rather than cardinality for such columns, and that a `slug` column unique per row
therefore does not trip the near-unique test. It does trip it: the module's test is pure cardinality
and knows nothing about which lists this document publishes, which is why `specification_columns`
exists and why the whitelist above names the two `slug`-like columns that need it. A phantom
automatic exemption is worse than a buried call site, because nobody declares anything and nobody
reviews anything. Prose fields inside `results.json` (`legend`, `definition`, `used_for`,
`reason_display`) are author-written sentences, not participant-derived strings, and are exempt from
the vocabulary test and subject to the house prose rules instead.

### 10.3 Why a date is an identifier here and not merely metadata

**Controlled Tier dates are unshifted.** `meta.cdr.dates_shifted` records this as `false` on every
run. In a date-shifted release, a surgical date is a coarse temporal attribute. In this release it is
the real date of a real operation on a real person, and combined with an anatomic region, an age band
and a length of stay it is close to unique. That is why the date ban is a column ban rather than a
formatting preference, and why a median over three people is treated as individual-level data: under
unshifted dates, a small-cell summary is a re-identification vector rather than a rounding concern.

The same reasoning is why `07_export.py` never exports a per-participant row under any aggregation
that could isolate one, and why the local side never receives a file with one row per person.

### 10.4 What `safe_export()` must do

`safe_export()` in `pipeline/disclosure.py` is the only function permitted to write into the export
directory. Nothing else in `pipeline/` opens a file for writing under it.

Required behavior, in order:

1. Refuse a path whose extension is not `.csv`, `.json` or `.md5`.
2. Refuse a frame containing any column matching the name or content tests in 10.2, except a column
   the caller named in `specification_columns`, which is exempt from the near-unique and
   identifier-like classes and from nothing else.
3. Refuse a frame containing any count cell for which `is_legal_disclosed_count()` is `False`.
   The cells reaching `safe_export()` have already been through `round20`, so the predicate here is
   the rendered-cell gate and not the floor; `disclosable()` was asked upstream, of the true count,
   by whoever rounded it. Section 0 sets out why asking the floor predicate at this point refuses a
   correctly rounded 20 and refused the STROBE ladder and Table 1.
4. Refuse a frame in which a percentage is disclosed while its count is suppressed.
5. Refuse a frame in which exactly one member of a declared partition is suppressed.
6. Refuse any string cell containing U+2014 or U+2212.
7. Refuse a `tables-csv` frame containing a non-string cell, and a `figures-csv` frame containing a
   display string in a numeric column.
8. Write the file with the byte-stability settings in section 8.2.
9. Read the bytes back, compute the md5, and return the `MANIFEST.csv` row for the file.

Every refusal raises. None warns. A warning in a disclosure path is a warning nobody reads.

**The signature, transcribed from `pipeline/disclosure.py` rather than proposed to it.** The module
is final and this document matches it; where an earlier draft of this section proposed a different
spelling, the module won and the draft is corrected:

```python
def safe_export(
    df: pd.DataFrame,
    path: Path,
    *,
    kind: str = "",                  # "figure-csv", "table-csv" or "results-json"
    exhibit: str = "",               # "Figure 2", "Table 1", or ""
    description: str = "",           # the MANIFEST description line
    count_cols: Sequence[str] = (),
    percentage_columns: Sequence[str] = (),
    partitions: Sequence[Sequence[str]] = (),
    specification_columns: Sequence[str] = (),
    allow_zero: bool = True,
) -> dict:                           # the MANIFEST.csv row, keys == MANIFEST_COLUMNS

def export_violations(                # the pure, testable heart of the above
    df: pd.DataFrame,
    *,
    count_cols: Sequence[str] = (),
    allow_zero: bool = True,
    percentage_columns: Sequence[str] = (),
    partitions: Sequence[Sequence[str]] = (),
    specification_columns: Sequence[str] = (),
    kind: str = "",
    path: Any = None,
) -> list[str]:                       # every reason, never only the first
```

Six things about it that a caller will otherwise get wrong:

- **The parameter is `count_cols`, not `count_columns`.** The module keeps that spelling because
  `00_config.ipynb` and `ANALYSIS-PLAN.md` both pin it and `suppress_frame(df, count_cols)` shares
  it. An earlier draft of this section wrote `count_columns`; that spelling is retired here.
- **It returns a dict, not a string.** The dict is the `MANIFEST.csv` row and its keys are
  `disclosure.MANIFEST_COLUMNS` in order: `file`, `kind`, `exhibit`, `md5`, `n_rows`, `n_columns`,
  `min_disclosed_count`, `n_suppressed_cells`, `description`. Call sites read `row["md5"]`, never
  the return value itself.
- **`kind`, `exhibit` and `description` are optional in the module and mandatory here.**
  `07_export.py` MUST pass `kind=` on all sixteen files, because item 7 above, the string-versus-
  numeric check, is keyed on `kind` and silently does not run when `kind` is empty. `exhibit` is the
  empty string for `results.json` and for the five ledgers, which is a value, not an omission.
- **`allow_zero` exists and defaults to `True`**, which is what makes an exact zero exportable as
  `0` per section 0. Pass `allow_zero=False` only for a column where a zero would itself be a
  finding no one is entitled to, and nothing in this bundle is such a column.
- **The count cells are tested with `is_legal_disclosed_count`, not with `disclosable`.** They have
  already been rounded by the time they arrive, so the floor predicate would refuse a correctly
  rounded 20, which is what it did. `disclosable()` belongs upstream, on the true count, in the code
  that rounds. Section 0 has the full division and the table that goes with it.
- **`specification_columns` is a per-column exemption, not a file-level one.** It names columns that
  hold vocabulary or specification values rather than participant-derived ones, and it exempts them
  from the near-unique and identifier-like refusal classes and from nothing else. A declared column
  that is not in the frame is itself a violation. The complete list of which files may declare it
  and for which columns is the whitelist in 10.2; a call site passing a column that whitelist does
  not name is a `verify.py` failure, not a judgement call.

**`safe_export` writes CSV. It will accept a `.json` path and write CSV into it.** The extension
allow-list is `disclosure.ALLOWED_EXPORT_SUFFIXES`, which contains `.json` so that the module can
stamp a JSON file's manifest row, but the writer itself is `DataFrame.to_csv`. Handing it
`results.json` and a frame would produce a comma-separated file with a `.json` name and no error.

**So `results.json` is written by `07_export.py`, not by `safe_export`.** Nobody owned this before;
it is owned here. `07_export.py` serializes the object itself with the settings of section 8.2
(`json.dump(_round_floats(obj, 6), fh, indent=2, sort_keys=True, ensure_ascii=False)` then a
trailing newline), reads the bytes back from disk, hashes them with `disclosure.md5_of_bytes`, and
assembles that one manifest row by hand with `kind="results-json"`, `exhibit=""`, `n_rows` equal to
the number of value nodes (objects carrying a `display` key), `n_columns` equal to `0`, and the
`min_disclosed_count` and `n_suppressed_cells` it computed while building the object. That row is
the first of the sixteen. Every other file goes through `safe_export` and contributes the row it
returns. The disclosure checks that `safe_export` would have run over a frame are run over the object
before it is serialized, so `results.json` is not a hole in the enforcement; it is enforced by a
different caller.

**The three declarations `07_export.py` holds and `safe_export()` does not.** `pipeline/disclosure.py`
is final and 11.3 makes it authoritative over its own signature, so where a bundle rule needs a
declaration the module has no argument for, `07_export.py` carries it and runs the check itself, in
`_contract_violations()`, over the same rendered frame and **before** it calls `safe_export()`. That
is not a route around the gate and the division is stated class by class in the module's own
docstring: `safe_export()` keeps the path, cardinality, identifier, date and extension classes, and
`_contract_violations()` covers the classes the module cannot see in the bundle's representation,
because `disclosure.is_suppressed()` recognises one sentinel and this bundle writes two different
things, the bare token `SUPPRESSED` in a figure CSV and the 7.5 sentence in a table CSV. Three
declarations follow from that, and this document specifies all three rather than leaving them to a
call site:

**1. `composite_count_columns`, so the floor reaches a count that is rendered rather than numeric.**
`safe_export()`'s count test parses each cell with `pd.to_numeric`, which cannot read `9,860`, so a
table CSV's four-figure counts arrive as `NaN` and are dropped from the check without a word. And a
table CSV's counts do not live in count columns at all: they live inside composed display tokens,
`1,240 (33%)` in a Table 1 body cell and `n = 340` in a Table 2 episodes cell, beside medians,
estimates and suppression sentences in the same column, so the column cannot be declared in
`count_cols` either. `07_export.py` therefore declares those columns in `composite_count_columns`,
extracts the leading count from each cell and tests it with `is_legal_disclosed_count()`. The
grammar is deliberately narrow and its refusals matter as much as its matches:

| Cell | Read as | Why |
|---|---|---|
| `340`, `9,860` | the count `340`, `9860` | a bare count, with or without thousands separators |
| `1,240 (33%)` | the count `1240` | `n_pct`, whose parenthetical is a percent |
| `n = 340` | the count `340` | the `display_n_equals` token of 3.2 |
| the suppression sentences of 7.5, and the empty string | no count | already suppressed, or not applicable |
| `62 (54 to 70)` | **no count, and this is deliberate** | a confidence interval. Its parenthetical is a range, not a percent, so it matches nothing and is left to its own class. Reading `62` out of it would floor-test the integer part of an estimate |
| `62 (54–70)` | **no count** | a median with an interquartile range, refused for the same reason |

The pattern is a single anchored expression, `^(?:n\s*=\s*)?(-?\d{1,3}(?:,\d{3})*|-?\d+)(?:\s*\(\d+%\))?$`,
and a cell matching neither shape carries no count. A declared column absent from the frame is a
violation, as in every class that takes column names.

**2. `row_partitions`, because four of this bundle's partitions run down a column and not across a
row.** `disclosure.export_violations`' `partitions` argument is a sequence of **column-name groups**,
checked row by row: it answers "these cells of one row sum to a disclosed total". Four partitions in
this bundle are the other shape, several **rows** of one column summing to a disclosed total, and
there is no way to say that in a sequence of column names. `07_export.py` declares each as a
`(column, row indices)` pair and applies the secondary-suppression rule of section 0 to it: if
exactly one member of a declared row partition is suppressed, the frame is refused, because that
member is recoverable by subtraction.

| File | Column | Rows | Total |
|---|---|---|---|
| `tables-csv/table1_cohort_characteristics.csv` | each procedure-group column and `All groups` | the levels of one banded `Characteristic`, taken from the 5.1 row-order table rather than hardcoded | that group's column-header n. Table 1 is the one file in the bundle that carries **both** a row partition and a column partition, the column one being the group cells of one row summing to the pooled cell, and missing either leaves a recoverable cell |
| `ledgers-csv/ledger_exclusion_and_censoring_reasons.csv` | `n_episodes` | the rows of step 12, of step 15 and of step 16 | that step's `n_denominator` (5.6) |
| `tables-csv/table3_gate_part_a.csv` | `All groups` | the two stage D component rows other than the composite | the stage D composite row |
| `ledgers-csv/ledger_matched_set_sizes.csv` | `n_sets` | every row | the total number of matched sets, which `share_of_sets` divides by |

**Stage D's three components are declared a partition although they are not strictly one**, and that
is a deliberate over-suppression rather than an oversight. An emergency department presentation that
becomes a same-day admission is counted under both of the first two components, so the composite is
at most their sum and not equal to it, and a suppressed component is therefore **bounded** by
subtraction rather than recovered exactly. Handing a reader a tight bound on a hidden cell is not a
thing this bundle does, the alternative would need the overlap count published to be checkable, and
declaring the partition costs one extra suppressed cell in the one case where it binds. The gate
reads the composite row wherever it needs stage D as a number, which is why nothing downstream
depends on the components summing.

**3. Every exported statistic is rounded to its unit's decimals before the gate sees it.**
`07_export.py` holds the decimals of 2.4 as `UNIT_DECIMALS` and applies them in `_round_to_unit()`
as it builds each frame, never on the way to the renderer. The reason is the near-unique class of
10.2: distinctness is computed on the in-memory float, and `FLOAT_FORMAT = "%.6g"` affects only what
is written, so a 286-row frame of unrounded medians is 100% distinct and is refused even though the
printed CSV would have looked fine. It is what keeps Figure 2 off the near-unique class at
`normalized_activity`'s two decimals and would not keep it there at three. It is a precondition of
exception 5 and not a substitute for it: rounding bounds the value space, and exception 5 covers the
files where a bounded value space is still one distinct value per row.

None of the three needs a new check slug in 3.10. The composite-count test is part of
`no_cell_below_floor`, the row-partition test is part of `secondary_suppression_applied`, and the
rounding rule is a precondition of `no_near_unique_column`; adding slugs would move
`checks.n_checks` for three rules that are already inside a check that reports.

**The bare-`20` grep `verify.py` runs, specified so it does not fire on the two lines that are not
comparisons.** Section 0 requires that no module writes the floor as a literal in a comparison, and
the naive grep for `20` hits `disclosure.py`'s own `MIN_CELL: int = 20`, which is the one line in the
project that is *supposed* to carry the number, and the sentinel string `"<=20 (suppressed)"`, which
is a display value and not a comparison. The check is therefore defined on comparison syntax rather
than on the digits:

```
verify.py --no-hardcoded-floor
  Scan every *.py and every notebook code cell under pipeline/ and local/, excluding
  pipeline/tests/ and local/tests/: the rule constrains the export path, and a test is
  entitled to name the number it is testing.
  Parse each file with `ast`.  Walk it recursively, carrying the chain of enclosing
  ast.FunctionDef and ast.AsyncFunctionDef names.  For every ast.Compare node:
    if no operand is an ast.Constant int in {19, 20, 21}, skip;
    if every OTHER operand is a cardinality expression -- an ast.Call to the builtin
      `len`, or an attribute access ending `.size` or `.shape` -- skip: that is an
      assertion about how many codes are in a locked list, not about a cell;
    if ANY name in the enclosing chain matches
        ^_run_self_test$ | ^_{0,2}tests?_ | ^_synthetic_ | ^_fixture | ^_make_fixture
      skip: the comparison is inside a self-test or a fixture builder, which is the
      directory exclusion above applied to this project's actual file layout;
    otherwise report the file, the line and the source of that line.
  Exit 1 on any hit.
```

**The self-test carve-out is the directory exclusion, applied to where the tests actually are.** The
rule as first written excluded `pipeline/tests/` and `local/tests/` on the stated ground that a test
is entitled to name the number it is testing. This project's house pattern does not put its tests
there: every module in `pipeline/` carries a module-level `_run_self_test()` and runs it under
`python3 <module>.py`, which is what makes a module testable inside the perimeter where no test
runner is installed. So the exclusion reached two directories, one of which holds a single ported
module's tests, and reached none of the six modules that carry their own. Run as first specified,
the walk reports **seven comparisons across five modules**, and every one of them is inside a
self-test or a fixture builder: `_run_self_test` in `02_pregate.py` asserting a fixture's misroute
column is 21, three in `03_cohort.py` naming the ladder's nineteenth rung, one in `04_features.py`
indexing a synthetic day 20, one in `_synthetic_panel` in `05_analysis_drd.py` seeding a
missing day at 21, and one in `_run_self_test` in `local/figures.py` asserting a constructed
delta-shift grid holds 21 points, which is seven locked coordinates crossed with three application
patterns and not a floor at all. **None is on an export path and none is a disclosure floor.** The house pattern
is the pattern, so the exclusion widens to it rather than six modules being rewritten to satisfy a
check about where their tests live.

**How a checker identifies such a body, which has to be mechanical or the carve-out is a licence.**
`ast` nodes carry no parent pointer, so the walk is a recursive descent that carries the list of
enclosing function names and extends it at every `FunctionDef` and `AsyncFunctionDef`. A `Compare`
is skipped when **any** name in that chain matches the pattern above, which is what reaches a nested
helper: `break_events`, defined inside `_run_self_test` in `03_cohort.py`, has the chain
`("_run_self_test", "break_events")` and is skipped on its first element. The chain is lexical and
not dynamic, so a comparison in an export-path function stays reported however it is called, and a
self-test that calls an export-path function does not launder that function's comparisons. Three
properties make this narrow rather than a hole: the name must be the exact `_run_self_test` or start
with one of four reserved prefixes, none of which any export-path function in `pipeline/` or
`local/` uses; a module-level comparison, outside every function, is never skipped; and the
`if __name__ == "__main__":` guard needs no carve-out at all, because its own `Compare` has a string
operand and no integer one. **Run against the shipped modules with the carve-out, this check reports
nothing**, which is the state it is meant to hold, and it reported six before it, which is the state
that made a reader learn to ignore it.

An `ast.Compare` walk rather than a regular expression is the whole point, and it is what makes the
two lines the review flagged non-issues rather than exemptions: `MIN_CELL: int = 20` is an
`ast.AnnAssign` and `"<=20 (suppressed)"` is an `ast.Constant` of type `str`, so neither is reachable
from a `Compare` node at all. A grep for a bare `20` would have hit both, reported the one line in
the project that is supposed to carry the number, and trained a reader to ignore the check. The
`len()` carve-out is what keeps `cs_spine.py`'s locked-cardinality assertions (`len(CPT_FUSION) == 21`
and its siblings) out of the report; those are counts of concepts in a specification, not counts of
people. The corresponding check slug is `no_hardcoded_floor` in `results.json.checks`.

---

## 11. Consumer obligations, change control, and what this contract does not own

### 11.1 What each consumer must re-assert

The local side never trusts the exporter. Every rule below is checked again on arrival, because a
bundle that passed inside the perimeter and a bundle that arrived intact are different claims.

| Module | Must re-assert |
|---|---|
| `verify.py --bundle` | every md5, every row and column count, the manifest completeness, the contract hash |
| `verify.py` (full) | every count cell in every arriving file satisfies `is_legal_disclosed_count()`, which is the arrival-side form of R1: the true counts are gone by then, so the question is whether each rendered cell is a legal one; no percentage disclosed while its count is suppressed; no partition with exactly one suppressed member; every label character-identical to section 7; no U+2014 or U+2212 anywhere in `manuscript/`, `figures/`, `tables-csv/`, `figures-csv/` or `ledgers-csv/`; every prose numeral a member of the approved display vocabulary of section 2.5; every rendered table cell equal to its CSV cell; no bare disclosure-floor literal in any comparison in `pipeline/` or `local/`, by the `ast.Compare` walk of 10.4; `row_order` in Table 1 is the contiguous ordinal `1` to N, which is the condition its 10.2 grant depends on; every `specification_columns=` call site in `pipeline/` names a column authorized by the 10.2 whitelist, by 10.2 exception 3 or by 10.2 exception 5, and no other, and names which of the three; every column in the 10.2 ownership register classed **machine token** is skipped by the snake_case assertion of section 6 and no other column is; every column classed **display label** or **prespecified sentence** matches its section 7 entry character for character, which for `ledgers-csv/ledger_variable_provenance.csv` now reaches `unit` and `missing_handling` against 7.14; every declared row partition of 10.4 has none or at least two suppressed members; every count embedded in a `composite_count_columns` cell satisfies `is_legal_disclosed_count()`; every statistic column is at its unit's decimals from 2.4 and no finer; no percentage node anywhere in `results.json` holds a fitted value, which is the arrival-side form of 3.7's rule and is checked by asserting every percentage node carries `num` and `den`; **`debt.unadjusted_contrasts` is keyed by exactly the slugs `debt.contrasts` is keyed by**, carries the same `display_label` on each, and carries `is_primary` `true` on the same one slug, so the STROBE 16(a) pair cannot go out of step with the estimates it is printed against; **`debt.unadjusted_model.prespecified` is `false` for as long as `ANALYSIS-PLAN.md` prespecifies no unadjusted contrast**, which is a set-equality-style assertion against the plan and not a remembered fact, and if the plan is amended to prespecify it this is the assertion that has to be changed in the same commit; every suppression reason any module emits is a slug of 7.5; **the primary exhibit set is exactly three figures and three tables**, counted as the number of DISTINCT `exhibit` values among the blocks of `figures` and of `tables` whose `exhibit_set` is `"primary"`, never as a count of bundle files and never as a count of block keys, with every block carrying an `exhibit_set` of `"primary"` or `"supplementary"`, every block's `exhibit` equal to the `exhibit` column of its own `MANIFEST.csv` row, and the supplementary set being exactly `figures.figure4` and `tables.table4`; **set equality of all five plan-owned slug vocabularies** against `ANALYSIS-PLAN.md`: the 7 procedure groups of 2.4, the 4 collapse levels of 2.5, the 19 attrition rungs of 2.6, the 5 estimator rungs of 3.5 and the 14 plotted sensitivity rows of section 6, plus the 8 subgroups of 9.1. The 10 supplementary sensitivity rows are excluded from the sensitivity set by name |
| `figures.py` | `attrition.closes`; that it renders a plate for every block of `figures`, supplementary included, since `exhibit_set` decides where a plate is printed and never whether it is drawn; the per-segment rounded-residual tolerance of 3.3, read from `segments[j].tolerance` rather than assumed; `is_legal_disclosed_count(n_contributing)` on every plotted row, which is the predicate for an arriving cell because `n_contributing` was rounded inside the perimeter and a legitimately rounded 20 must not be refused on the way in either; one line and one ribbon per group and segment; the series count read from `cohort.groups`, never assumed to be four; every plate carries its own denominator |
| `tables.py` | every cell is a member of the approved vocabulary; every column header carries its n where this contract says it does; the column list read from `tables[key].columns`, never assumed to be four groups; percentages at zero decimals; the Table 2 footer is **15** rows as of 1.9.0 and its `row_order` is the contiguous `1` to `15` of 5.3 |
| `make_strobe.py` | the ladder closes at all three segments; `figure1_strobe_ladder.csv` has 19 rows and reconciles row for row with `attrition.rungs`; `n_carried_forward` is present at step 2 and empty elsewhere; the rounding footnote is printed; the five `ledgers-csv/` files parse and their `slug` values are members of the vocabularies of 5.6 |
| `ledger.py` | every numeral it emits came from a `display` field by key path, never from a computation; no hand-typed numeral survives `S()` |
| `manuscript.py` | Methods states the analysis plan hash and lock date; Methods states that the tier boundary and the disclosure floor coincide when `gate.tier.event_count_printable` is `false`; Results reports the delta-shift tipping point as a bound and never as an interval, and prints the `no_crossing_within_range` sentence as a finding rather than as a gap when `debt.delta_shift.crossed_within_grid` is `false`; **Methods reports the unadjusted contrast of 3.5 as required by the reporting guideline and never as prespecified**, reading `debt.unadjusted_model.prespecified` rather than deciding for itself, and prints `debt.unadjusted_model.definition_display` so that what was and was not held fixed is on the page beside the number |

### 11.2 Change control

| Change | Consequence |
|---|---|
| Adding a key, a column or a file, or a row to a vocabulary this contract transcribes | minor version bump; `meta.schema_version` and `meta.contract_sha256` change; consumers keep working. This is the row 1.4.0 was bumped under, for the ninth supplementary sensitivity row of 3.6 and 7.8; the row 1.5.0 was bumped under, for the tenth such row and for the two label tables 7.12 and 7.13; **the row 1.6.0 was bumped under**, for two exhibits, six `gate.arm_a.estimates` keys, three units, one suppression reason and the two label tables 7.14 and 7.15; **the row 1.7.0 was bumped under**, for the tenth suppression reason of 7.5, the two per-group standardized rate keys of 3.7 with their two 7.15 labels, and `debt.delta_shift.interval_crossed_within_grid`; and **the row 1.8.0 was bumped under**, for `exhibit` and `exhibit_set` on every block of `figures` and `tables`, `denominators.event_centered_members`, and the `risk-set members` unit in 3.2's unit vocabulary. **The row 1.9.0 was bumped under is this same first row**, for `debt.unadjusted_contrasts` and `debt.unadjusted_model` in 3.5 and three rows in 5.3's fixed footer list. It is the adding row and not the renaming one on the same test 1.8.0 was measured against: no key, column, file or path is renamed or removed, the footer keeps every `row_order` it had and gains three at the end, 7.3 does not grow because the unadjusted contrasts reuse the adjusted contrasts' own five labels, and `figures` still carries four blocks and `tables` five. It is minor and not a patch for the reason this row already states: three rows added to a list this document fixes are three rows the exporter and its fixture must adopt, which is a consumer obligation and not a rewording. The two 10.2 sweep cells that move from 12 rows to 15 are a patch-row change on their own, and a minor bump carries them. **1.8.0 is a minor bump and not a major one, and the test is renaming rather than reclassifying**: no key, column, file or path is renamed or removed, `figures` still carries four blocks and `tables` five, both reclassified exhibits keep their sections and their bytes, and what changes is two added fields plus the exhibit-set each block declares. Moving `figure4` out of `figures` into a block of its own WOULD have been the renaming row, and a major bump updating six consumers in the same commit, which is one of the two reasons 3.8 does not do it. It is a minor bump and not a patch one for the reason this row states and 11.4's discharged eighth row demonstrates: a row added to a transcribed vocabulary is a row every module that copies that vocabulary must adopt, which is a consumer obligation and not a rewording. The bound-node count, the `spline_basis` string, the per-node crossing sentence and the `n_suppressed_cells` restatement in that same version are each a patch-row change on their own, and a minor bump carries them. The node-shape corrections, the exception, the three `07_export.py` declarations and the four corrected worked examples in that same version are each a patch-row change on their own, and a minor bump carries them |
| Renaming or removing a key, a column or a file | major version bump; every consumer is updated in the same commit. **This is the row 2.0.0 was bumped under**, for the removal of `seeds.farm_fingerprint` and the addition of `sampling_salt` beside `seeds`. It is this row and not the first one on this row's own test: a key this document declared is **removed**, and a removal is not made minor by the removed key having been a fabrication -- the value `20260825` had no referent in any other file of this project, but the KEY was declared here and could have been read. Nor is it made minor by the fact that no consumer read it: `local/ledger.py`'s `_assert_schema_major` cites this row verbatim to explain why it refuses a bundle whose major version it was not written against, and that refusal firing is the row working, not the row misapplied. The salt's arrival is the first row on its own and the reshaped `analysis_plan.amendments` row is the first row on its own; a major bump carries both. The three consumer updates this row obliges -- `ledger.py`'s `SCHEMA_MAJOR_SUPPORTED`, `tables.py`'s `1.` prefix assertion and `verify.py`'s pin on the finding this bump closes -- are registered in 11.4 rather than assumed, because they are owned outside the two files that changed |
| Changing a display label | patch version bump; the label table is the only edit; a re-export is required because the exporter transcribes it |
| Changing a decimals rule or a separator | patch version bump; a re-export is required |
| Changing a rule, an exception or an exporter obligation, with no key, column, file, path, label or row count moving | patch version bump; consumers keep working; a re-export is required whenever the change moves a string the exporter transcribes or a check the exporter runs. This is the row 1.3.1 was bumped under, and the row this one was added under. It is also **the row 1.6.1 was bumped under**, for the Figure 1 grant in the 10.2 whitelist and the row-floor sweep beside it: no key, column, file, path, label or row count moves, and what changes is one exemption register, one dated obligation and the `specification_columns=` declaration `07_export.py` passes at one call site, which is a check the exporter runs and so requires the re-export. And it is **the row 1.9.1 was bumped under**, for `series_slug` and `box_side` in section 6's machine-token row, nine rows in the 10.2 ownership register and the machine-token column sweep beside them. It is this row and not the first one on the first row's own test: nothing is **added** to the export. No bundle file gains or loses a column, no vocabulary this document transcribes gains a row, and every one of the nine register rows classes a column that has been in the bundle since the file that carries it was specified. What moves is a rule and a register, which is what this row is for. It is also the one bump of the four patch bumps so far that requires **no** re-export on this row's own test: no string the exporter transcribes moves and no check the exporter runs moves, and the bundle is restamped only because `meta.contract_sha256` moves on any edit at all |

`verify.py` refuses a bundle whose `meta.schema_version` major version differs from the contract in
the working tree, and warns on a minor mismatch. A hash mismatch on `meta.contract_sha256` is a hard
failure: it means the bundle was produced against a different specification than the one the local
modules were written to, which is exactly the condition this document exists to prevent.

### 11.3 What this contract does not own

| Owned elsewhere | Owner | Coupling |
|---|---|---|
| `MIN_CELL`, `round20`, `disclosable`, `is_legal_disclosed_count`, `FLOAT_FORMAT`, `MANIFEST_COLUMNS`, `MANIFEST_KINDS`, `ALLOWED_EXPORT_SUFFIXES` | `pipeline/disclosure.py` | imported, never hardcoded here or in `07_export.py`. The two predicates are imported **as a pair**: a module that imports one and re-derives the other has re-created the defect section 0 records |
| `safe_export()`'s exact signature | `pipeline/disclosure.py` | section 10.4 **transcribes** it; the module is final and this document matches it, not the other way round |
| `results.json`'s bytes | `pipeline/07_export.py` | `safe_export` writes CSV even into a `.json` path, so `07_export.py` serializes, hashes and manifests this one file itself (10.4) |
| The attrition rung slugs | `ANALYSIS-PLAN.md` section 2.6, emitted by `pipeline/03_cohort.py` | sections 3.3 and 7.2 transcribe the 19 as of 1.1.0; `verify.py` asserts set equality |
| The sensitivity ladder and its order | `ANALYSIS-PLAN.md` section 6, version 1.3 | section 3.6 transcribes the 14 plotted rows as of 1.1.0 and the 10 supplementary rows as of 1.5.0, and 7.8 carries the labels of both; `verify.py` asserts set equality over the 14 only |
| The estimator fallback ladder | `ANALYSIS-PLAN.md` section 3.5 | section 3.1.1 lists the set as of 1.1.0 |
| The prespecified subgroup list | `ANALYSIS-PLAN.md` section 9.1 | section 7.11 lists the labels as of 1.1.0 |
| The procedure-group and collapse-level slugs | `ANALYSIS-PLAN.md` sections 2.4 and 2.5 | sections 7.1 and 3.4 transcribe them as of 1.1.0 |
| The concept set, its registry columns and its two gap builders | `pipeline/cs_spine.py` | `REGISTRY_COLUMNS` is copied into 5.6 verbatim; the builders' row order and column names are quoted in 3.1.2. There is no bare `region` column |
| The exclusion and censoring reason-detail slugs | `pipeline/build_all.sql`, stage `ledger_exclusion_reasons` | section 7.12 transcribes the 20 `(step, reason_detail)` pairs as of 1.5.0 and owns the sentence beside each; a detail slug the producer adds without an amendment here has nothing to print, and `verify.py` asserts set equality against the stage |
| The analysis-variable tokens | `pipeline/build_all.sql`, stage `ledger_variable_missingness` | section 7.13 transcribes the 12 as of 1.5.0 and owns the display label and derivation sentence beside each; `verify.py` asserts set equality against the stage |
| The collapse ladder | `ANALYSIS-PLAN.md` | `cohort.collapse_level` records which rung was reached |
| The tier bands and permitted claims | `background/All_of_Us_Spine_Wearable_Protocol.md` | quoted verbatim in section 7.10 |
| The recovery day bands the collider comparison is standardized over | `ANALYSIS-PLAN.md` section 4.4 | sections 3.7 and 5.7 carry the six keys and the three rows; the band boundaries stay inside the perimeter, and the standardized cell is suppressed unless every band contributing to it clears the floor |
| The event-centered window `-14` to `+7` | `ANALYSIS-PLAN.md` section 9.5 | section 4.4 fixes it as `figures.figure4.day_range` and pins the file at 44 rows |
| `composite_count_columns`, `row_partitions` and `UNIT_DECIMALS` | `pipeline/07_export.py` | section 10.4 **transcribes** all three, as it transcribes `safe_export()`'s signature from `disclosure.py`. They exist in the exporter and not in the module because 11.3's first row makes `disclosure.py` final over its own signature |
| Figure rendering, palette, legibility | `local/figures.py` and the house style | this contract stops at the series |

Where a list in this document and a list in `ANALYSIS-PLAN.md` disagree, the plan wins and this
document is amended in the same commit. The disagreement is never resolved by the exporter choosing
one at runtime.

### 11.4 Stated obligations, dated

A known gap that is written down with a date, a trigger and a cost is a decision. The same gap
discovered when it fires is a surprise, and this one would fire inside the perimeter, on a paid
session, after the analysis had run. Each row below is an obligation this contract accepts and has
not discharged. A row leaves this table when the work is done and the version that did it is named,
never by being softened.

| Raised | Obligation | Trigger | What it would take | Owner |
|---|---|---|---|---|
| 2026-08-26 | **Sections 4 and 5 need a second full pass for the alternate exhibit set before an export can run at tier 1 or 2.** | `gate.tier.index` is 1 or 2, which is 50 or more usable events at stage E | see the itemised cost below | this document, amended before `07_export.py` runs |
| 2026-08-26 | **`06_analysis_gate.py` declares five of 3.7's thirteen `arm_a.estimates` keys and must adopt the other eight**, along with the two exhibits 4.4 and 5.7 added. Measured on the shipped module: its `ESTIMATE_KEYS` is the five of contract 1.5.0 and its own comment still calls them "the five keys". Its `build_gate_block()` raises on any estimate key this contract does not declare, which is the correct direction and means the amendment lands before the module does; the consequence of the lag is that the six collider keys never reach the block, so `07_export.py` refuses Table 4 at any tier that permits the comparison. **This one blocks the export at tiers 1 to 3** | the next run of `06_analysis_gate.py`, or any `--fixture` run at a permitting tier | eight keys in `ESTIMATE_KEYS`, their rows in `ESTIMATE_KEY_ANALYSIS`, `ESTIMATE_KEY_LABELS` and `ESTIMATE_KEY_SHAPE`, two frames, and the tier table of 3.7 | `pipeline/06_analysis_gate.py` |
| 2026-08-27 | **A twentieth attrition rung halts the export and no register in this document can clear it.** At twenty-one rungs `figures-csv/figure1_strobe_ladder.csv` crosses the near-unique row floor. The 10.2 whitelist grant added at 1.6.1 clears `step`, `slug`, `display_label`, `reason` and `reason_display`, and `n_in` and `n_out` survive it: they are counts, they carry the integer-key shape as well as the cardinality class, and 10.2 says in two places that a count column is exempted by nothing. The decision is not made here because it is not this fix's to make | `ANALYSIS-PLAN.md` section 2.6 carries more than `disclosure.NEAR_UNIQUE_MIN_ROWS` rungs. The checker fails on the plan's own rung count, locally, before any session is paid for | one of three, argued and chosen rather than assumed: a sixth exception for a count column that is a **cohort-level** total rather than a per-row measurement, which is a genuinely new argument and the first exemption this document would grant a count; or a change to the ladder's own shape so the two columns are not near-unique, for instance dropping `n_in` on the ground that it is `n_out` of the rung above and is recoverable; or raising `NEAR_UNIQUE_MIN_ROWS`, which is `pipeline/disclosure.py`'s to own under 11.3 and reaches every file in the bundle. The first is the likeliest and the third is the most dangerous | this document, amended before `07_export.py` runs on a twentieth rung |
| 2026-08-27 | **`ledgers-csv/ledger_variable_provenance.csv` needs a sixth whitelist row if it ever passes the floor.** Its `missing_handling` column holds one prespecified sentence per variable and is 100% distinct over twelve rows; 7.14 owns it and it would meet the whitelist criterion, but it is not granted today because the file is eight rows under the floor and an exemption a column does not need is an over-broad grant. The sweep in 10.2 records the margin | the `ledger_variable_missingness` stage of `pipeline/build_all.sql` emits more than `disclosure.NEAR_UNIQUE_MIN_ROWS` analysis variables | one row in the 10.2 whitelist, one row in the ownership register, and `missing_handling` added to the `specification_columns=` list `07_export.py` passes on that frame | this document |
| 2026-08-27 | **Table 4's two window-group count pairs have no `results.json` home.** 5.7 gives the file an `Episode-days at risk` and an `Acute-care events` column, non-empty on the two window-group rows, and no block of `results.json` declares them: they are counts, so `gate.arm_a.estimates` is the wrong home, and `denominators` carries one cohort-level `analytic_person_days` rather than a split of it. `07_export.py` takes them beside the gate block and refuses at a permitting tier if they are absent, which is the correct direction. The decision is not made here because it is a block-ownership question and this fix's mandate was the rate cells | a run at any tier that permits the comparison, which is tiers 1 to 3. The exporter's own refusal names both sections | one of three, argued rather than assumed: two more `denominators` entries, which reads oddly because a denominator there is cohort-level and these are strata of one; a `gate.arm_a.collider` sibling block holding four count nodes, which is the shape 3.7 already gives `stages[i].components`; or leaving them a payload-only input to the exporter and saying so in 5.7, which is what 5.7 says today and which means a consumer reading `results.json` alone cannot reproduce the printed cell. The second is the likeliest | this document |
| 2026-08-27 | **`06_analysis_gate.py` emits the absolute risk on the wrong unit.** Its shape is right and has been since 1.6.0: 3.7 declares `arm_a.estimates.absolute_risk_translation` an **estimate** node, not a percentage node, and the module builds an estimate node. What is still wrong is the unit. The module passes `unit="percent"` with a per-call `decimals=ABSOLUTE_RISK_DECIMALS` override, on both `absolute_risk_translation` and `absolute_risk_at_the_reference_ratio`, because zero decimals on `percent` print a 90-day acute-care risk of a few percent as `0%`. 2.4 has carried `absolute_risk_percent` at two decimals since 1.6.0 for exactly that quantity, so the override is now a workaround for a unit that exists. It is not merely cosmetic: 11.1 has `verify.py` assert that **every statistic column is at its unit's decimals from 2.4 and no finer**, and a two-decimal value declaring `unit: "percent"` is a value one decimal finer than its declared unit permits, which is the arrival-side form of a disclosure rule. **The module's own `CONTRACT_GAPS` entry for this is half stale** and its first sentence, that 3.7 declares a percentage node, has been false since 1.6.0; the live half is the unit | the next run of `06_analysis_gate.py` at a tier that permits `absolute_risk_translation`, which is tiers 1 and 2, or `verify.py`'s decimals assertion on arrival | two rows in `ESTIMATE_KEY_UNIT` changed from `percent` to `absolute_risk_percent`, both `decimals=` overrides dropped at the two call sites, `ABSOLUTE_RISK_DECIMALS` retired or reduced to a reference to 2.4, and the `absolute_risk_node_shape` entry in `CONTRACT_GAPS` restated so its first sentence names the unit rather than the shape | `pipeline/06_analysis_gate.py` |
| 2026-08-27 | **`06_analysis_gate.py` must hand the exporter `denominators.event_centered_members`.** 3.2 makes it a required denominator and 3.8 points `figures.figure4.denominator` at it, so the document half of the gap the module raised as `event_centered_curve_denominator_has_no_key` is closed at 1.8.0. The remaining half is plumbing: `07_export.py` renders the `denominators` block from the payload it is handed and now **refuses** a payload missing any required key, which is the correct direction, so the export halts until the count arrives. The count is already measured. `event_centered_curve_sql()` returns `n_members_in_curve` and `n_members_dropped_structural` per role, constant down each role's block, precisely so the exhibit carries its own denominator; what is missing is the step that sums the per-role TRUE integers and puts one entry in the export payload. Summing happens on the true integers and the floor is met once, at the boundary, which is this project's rule everywhere | the next run of `07_export.py` on a real payload. The exporter's refusal names the key and section 3.2 | one payload entry: the true total across both roles, `unit: "risk-set members"`, no rung, and 3.2's definition and `used_for` strings. It is 0 at tier 4, where no event-centered query is submitted | `pipeline/06_analysis_gate.py` |
| 2026-08-27 | **`07_export.py` and its fixture must pick up 1.9.0's STROBE item 16(a) keys.** `05_analysis_drd.py` now returns `debt.unadjusted_contrasts`, keyed by the five contrast slugs with the same raw shape as `debt.contrasts` (`display_label`, an `(est, lo, hi)` triple, a bare `p`, `is_primary`, `true_n_compared`, `true_n`, `estimable`), and `debt.unadjusted_model`, whose raw members are `definition_display`, `mandate_display`, `prespecified`, `rung_slug`, `rung_display`, `rung_index`, `rung_matches_adjusted`, `rung_note_display`, `true_bootstrap_attempted`, `true_bootstrap_failed`, `instability_trigger` and `not_estimable_reason`. Both cross as **raw true values**, so the exporter floor-tests and renders them exactly as it does the adjusted contrasts. Nothing breaks by absence today: the exporter reads the `debt` block by named key and ignores what it has not been told about, so the two keys are silently dropped until it is updated, which is why this is a dated obligation and not a halt | the next run of `07_export.py` on a real payload, or the next fixture regeneration | render `unadjusted_contrasts` through the same node builder `contrasts` uses, with `unit="activity_days"`; render `unadjusted_model.bootstrap_failure_rate` as a percentage node from `true_bootstrap_failed` over `true_bootstrap_attempted`, the way `meta.estimator.bootstrap_failure_rate` is already built; add rows 13, 14 and 15 of 5.3 to `TABLE2_FOOTER_ROWS` with the source keys 5.3 names, keeping rows 1 to 12 at the `row_order` they have; log every suppression under the paths `debt.unadjusted_contrasts.<slug>.estimate` and `debt.unadjusted_model.*`; restamp the fixture's Table 2 footer row count from 12 to 15 and its `meta.schema_version` to `1.9.1`, which is the version in the tree after 1.9.1's register sweep and the version `CONTRACT_VERSION` must read; 1.9.1 adds nothing to the exporter, so the stamp is the whole of what it costs | `pipeline/07_export.py` |
| 2026-08-27 | **`local/verify.py`'s known-open pin on `column-register` is a SUBSET assertion, so it does not fire when the finding it pins is closed.** Its self-test reads `expected_open = {"column-register"}` and asserts `_failed(baseline) <= expected_open`, and the comment above it says why the pin exists: "the day that amendment lands, this line fails and somebody deletes it, rather than the gap quietly becoming permanent". The amendment landed at 1.9.1, `column-register` passes on the reference bundle and on the fixture, and the assertion held anyway, because the empty set is a subset of every set. **Measured, not predicted**: `python3 local/verify.py --self-test` reports 14 of 14 checks passing and 21 self-test checks passing with the pin still in the source. So the pin now records a finding that does not exist, which is the state its own comment was written to prevent, and the next reader of that module is told one check is expected to fail when none is | already fired, in the sense that matters: the condition the pin describes is false as of 1.9.1 and the pin still passes. It will stay silently wrong until somebody reads it | delete the three lines, which is what closing the finding was always going to cost. If a pin of this shape is wanted again, it is `_failed(baseline) == expected_open`: equality fails both when a new check breaks and when a pinned one is fixed, and only equality gives the property the comment claims | `local/verify.py` |
| 2026-08-27 | **`local/verify.py` reads section 6's machine-token rows as a set of bare column NAMES, and those rows are scoped by surface.** Its `SECTION_SIX_MACHINE_NAMES` is a hardcoded set holding `slug`, `group_slug`, `axis`, `render`, `kind`, `unit`, `reason`, `row_order` and `step`, applied to every file of the bundle. Section 6 lists `unit` under `figures-csv/*.csv`, where it is a slug from 2.4; on `ledgers-csv/ledger_variable_provenance.csv` the same name is a **display label** that 7.14 owns and that the 10.2 register classes as printing. The flattening therefore exempts a printed column from the snake_case and house-prose sweeps on that one file, which is a check switched off on a column it was written to guard. **It is a false negative and not a false alarm, so nothing fires and nothing will**; the module's own comment says the register decides a pair and this set decides a name, and the defect is that a name is not enough. Two consumers of the constant differ in how much this matters: `check_column_register` short-circuits on the register pair first, so it is unaffected as of 1.9.1 now that every machine-token column has a row; `printed_columns` reads the name set after the register and is where the printed column is lost | any run of `verify.py` against a bundle whose provenance-ledger `unit` cell carries a machine token, a house-prose violation or an en-dash, none of which would be reported | the constant is scoped to `(file, column)` pairs or, more simply, deleted in favour of the 10.2 register, which classifies pairs and, as of 1.9.1, reaches every machine-token column in the bundle. The register is already what 11.1 tells the module to read | `local/verify.py` |
| 2026-08-27 | **The local consumers must pick up 1.9.0.** `verify.py` gains the two 11.1 assertions on the 16(a) pair, `tables.py` reads a 15-row Table 2 footer instead of a 12-row one, and `manuscript.py` prints the unadjusted contrast as reporting-guideline-mandated rather than as prespecified, reading `debt.unadjusted_model.prespecified` instead of deciding. The third is the one that matters and the reason this is registered rather than assumed: a Methods section that describes a guideline-mandated estimand as a planned one has misreported the prespecification, which is the single failure this whole project's lock discipline exists to prevent, and no consumer can infer which it is from the number | the next local self-test run against the regenerated fixture | two assertions in `verify.py`, one row count in `tables.py`, and one Methods sentence in `manuscript.py` that reads the boolean | `local/verify.py`, `local/tables.py` and `local/manuscript.py` |
| 2026-08-27 | **The local consumers must pick up 1.8.0.** `figures[key]` and `tables[key]` each gain `exhibit` and `exhibit_set`, `denominators` gains `event_centered_members` on the new `risk-set members` unit, and `figures.figure4.n` is now the curve's own member count rather than the composite first-event count. Additive, so nothing breaks by absence, and the reason this is registered rather than assumed is that two of the three obligations are **new assertions** rather than new reads: `verify.py` must assert the three-and-three budget over distinct `exhibit` values, and `figures.py` must render Figure 4's plate note from the new denominator instead of the old one. A consumer that took `len(results["figures"])` for the figure budget, or that hardcoded `First acute-care events n =` as the curve's plate note, is what this bump breaks | the next local self-test run against the regenerated fixture, which already carries all three | one assertion in `verify.py`, one plate-note read in `figures.py`, and a `meta.schema_version` minor-mismatch warning cleared | `local/verify.py` and `local/figures.py` |
| 2026-08-28 | **The local consumers must pick up 2.0.0, which is a MAJOR bump and so is the one kind of bump that breaks them by construction.** Three of them, each measured against the tree rather than predicted. (1) `local/ledger.py` sets `SCHEMA_MAJOR_SUPPORTED = 1` and `_assert_schema_major()` raises `LedgerError` on any bundle whose major version differs, so it refuses the 2.0.0 fixture and every module built on it -- `manuscript.py`, `make_strobe.py` -- refuses with it. (2) `local/tables.py`'s self-test asserts `bundle.results["meta"]["schema_version"].startswith("1.")`. (3) `local/verify.py` pins `plan-constants` as its single known-open finding with the needle `meta.seeds.farm_fingerprint is 20260825`; that finding is CLOSED by this bump, the pin is an equality assertion in both directions, and its own comment says what to do when the amendment lands: "on the day it lands this pin fires as over-strict and is deleted rather than widened". None of the three is a read of the removed key -- no consumer ever read `seeds.farm_fingerprint` -- so nothing has to be rewritten, only re-pointed. **A fourth item is an addition rather than a repair, and it is the one that closes the class of defect rather than this instance of it:** `verify.py` should re-assert `meta.sampling_salt` against the `DECLARE` in `pipeline/build_all.sql` on arrival, the way `bundle-integrity` already re-asserts the contract hash. `07_export.py` asks that question on both sides of its own boundary, in `_render_meta` and in `validate_bundle`, but the arriving bundle is a separate claim and the DAG is in the local tree too. Until it lands, a bundle that arrives carrying any salt at all passes every arrival check, which is the exact silence that let `20260825` stand | already fired, at the moment 2.0.0 landed: `ledger.py` and `tables.py` refuse the regenerated fixture and `verify.py --self-test` fails on the pin, while `verify.py --arrival` on the bundle passes 11 of 11 | `SCHEMA_MAJOR_SUPPORTED = 2` in `ledger.py`; `startswith("2.")` in `tables.py`; delete the `plan-constants` entry from `verify.py`'s `pinned` dict and the `farm-fingerprint-repaired` mutation beside it, which asserted the pinned value could be repaired and now has no pinned value to repair. Four lines, three files, no logic | `local/ledger.py`, `local/tables.py`, `local/verify.py` |

**Discharged, with the version that did it, so the register shrinks as well as grows.**
Each row below left the table above because the work landed, not because it was softened, and each
was checked against the tree rather than remembered.

| Raised | Obligation | Discharged | Evidence |
|---|---|---|---|
| 2026-08-26 | `07_export.py` must write two more files, carry two more manifest rows and extend `--fixture` to 16 manifest rows, 44 Figure 4 rows and a three-row Table 4 | before 1.7.0 | the fixture bundle carries `figures-csv/figure4_event_centered_activity.csv` at 44 rows, `tables-csv/table4_collider_comparison.csv` at 3, and `MANIFEST.csv` at 16 data rows |
| 2026-08-26 | Every module carrying a copy of the 7.5 sentences must adopt the ninth, `no_crossing_within_range` | before 1.7.0 | `03_cohort.py`'s `SUPPRESSION_SENTENCES` and `07_export.py`'s `LABELS` each carry it, character-identical to 7.5 |
| 2026-08-26 | `07_export.py`'s `UNIT_DECIMALS` must gain `absolute_risk_percent`, `rate_ratio` and `rate_per_1000_episode_days`, and its `LABELS` the entries of 7.14 and 7.15 | before 1.7.0 | all three units are in `UNIT_DECIMALS` at two decimals, and 2.4's unit vocabulary and the module's now agree exactly |
| 2026-08-27 | `06_analysis_gate.py` emits a suppression reason 7.5 does not own, `not_estimable_separation` | 1.7.0 | 7.5 carries it as its tenth row with the sentence `ANALYSIS-PLAN.md` 4.9 fixes, and `disclosure.py` and `06_analysis_gate.py` both match it character for character |
| 2026-08-27 | The fixture and `07_export.py` must pick up 1.6.1 | before 1.7.0, and reopened above for 1.7.0 | `07_export.py`'s `CONTRACT_VERSION` read `1.6.1`, the fixture's `meta.schema_version` read `1.6.1`, and the Figure 1 frame carried the `specification_columns=` declaration 10.2 grants |
| 2026-08-27 | **The fixture and `07_export.py` must pick up 1.7.0.** `LABELS` gains 7.5's tenth sentence and 7.15's two new labels, `GATE_ESTIMATE_KEYS` gains 3.7's two new keys, `TABLE4_ROWS` reads each window group's standardized rate from `estimates` under its new key, `_tipping_point_node`'s `REPORTED` comment cites 3.5's new key, the Table 2 footer's `spline_basis` string is the plan's wording, and the fixture restamps two `n_suppressed_cells` values, Figure 4 from 220 to 176 and Figure 3 from 5 to 4 | 1.8.0 | measured in the tree rather than remembered: `07_export.py`'s `LABELS` carries all twenty of 7.15's strings and 7.5's tenth sentence, its `GATE_ESTIMATE_KEYS` carries all thirteen keys of 3.7 including the two standardized ones, and the regenerated fixture's `MANIFEST.csv` reads `176` on Figure 4 and `4` on Figure 3. `CONTRACT_VERSION` is now `1.8.0`, which is past `1.7.0` and carries it |

**What the alternate exhibit set would take, itemised, so the cost is a number and not a worry.**
`ANALYSIS-PLAN.md` section 9.5 replaces Figure 2, Figure 3, Table 1, Table 2 and Table 3 wholesale
when the event count reaches 50, and `06_analysis_gate.py` correctly sets
`gate.tier.exhibit_set = "alternate"` at tiers 1 and 2. `verify.py` refuses that value for schema
1.x (7.10), so the export halts, and **that refusal is correct behaviour and must not be relaxed**:
this document specifies the primary exhibit set only, and an exporter that emitted the primary
column set with alternate content would produce a bundle whose columns say one thing and whose
numbers say another. Discharging it means:

1. **Five new file schemas in sections 4 and 5**, one per replaced exhibit, each with its column
   list, its suppression rule, its sort keys and its worked example. Figure 2 becomes the
   event-centered curve of section 4.4 promoted to a primary exhibit with matched controls; Figure 3
   becomes an adjusted spline dose-response for the proximal step ratio with an alert-burden panel;
   Table 1 splits by event status rather than by procedure group; Table 2 becomes the conditional
   logistic regression with the absolute-risk translation; Table 3 becomes the clinical-time versus
   step-augmented model comparison.
2. **A second `results.json` shape for `debt` and `gate`**, because under the alternate set Arm A is
   primary and Arm B moves to the supplement in full, while the recovery-debt primary estimand is
   still reported in the main text as one sentence with its contrast and interval. The `debt` block
   does not shrink; what changes is which block the exhibits are drawn from.
3. **A manifest arithmetic decision.** The alternate set replaces exhibits rather than adding them,
   so the row count need not move, but 3.8 derives 16 from `1 + 4 + 6 + 5` and every one of those
   terms is named. Whichever way it lands, four places assert the number and all four move together.
4. **A major or minor version decision under 11.2.** Replacing a file's columns wholesale is the
   renaming row, which is a major bump and updates every consumer in the same commit. Carrying both
   sets side by side, keyed on `exhibit_set`, is the adding row and is minor. The second is more
   work in this document and less work in six consumers, and the choice is not made here because it
   is not made until the count is seen.
5. **`verify.py`'s schema guard relaxed by one line**, and only after 1 through 4 land. It reads
   `tier.exhibit_set == "primary"` today and would read a version test instead.

**Why this is not being written now.** The exhibit set is chosen by a count nobody has seen, and
`ANALYSIS-PLAN.md` section 1.2 makes that count the only exhibit-level branch in the study. Writing
five speculative schemas before the gate runs would put five unexercised file specifications in a
document whose whole value is that every line in it is checked, and the fixture cannot exercise them
because the fixture pins tier 4. The honest position is that the primary set is specified, checked
and locked, that the alternate set is a known and dated obligation with a costed path, and that the
gate's own refusal is what makes it impossible to ship the second as the first.
