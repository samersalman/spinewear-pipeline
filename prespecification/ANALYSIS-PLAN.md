# ANALYSIS-PLAN.md: the locked prespecification

**Study.** Cumulative ambulatory activity loss after elective cervical and lumbar spine surgery: a
wearable-linked cohort study in the All of Us Research Program.

**Version.** 1.5. **Status.** LOCKED. **Date of lock.** 2026-08-27. Versions 1.1 through 1.5
correct the unpublished provisional lock of 1.0 before any count from this study was seen; the
itemised lists and the superseded hashes are in section 13.

**What "locked" means here.** This file is frozen and hashed by
`prespecification/lock_plan.py` before Phase 2 runs, which is before any count from this study
exists. The SHA-256, the byte length and the lock timestamp are written to
`prespecification/PLAN-HASH.txt` and recorded in `SESSION-LOG.md`. The Methods cite this plan by
hash and date. `lock_plan.py --check` recomputes the hash and exits non-zero if the file has moved,
so a silent post-lock edit is caught rather than argued about. Any deliberate change after the lock
is an amendment: it goes in section 13 with a date and a reason, the file is re-hashed, and both
hashes are kept.

**The claim this file exists to support.** At the moment of the lock, no author and no agent had
seen a cohort count, an event count, a coefficient, a curve, or a P value from this study. Every
branch below is therefore resolved by a rule written in advance, not by a look at the data. Where a
rule depends on a number, the number that resolves it is a *count* (cohort size, event count, cell
size, risk-set size, convergence status), never an *estimate* (a contrast, a direction, a
significance level). That distinction is the spine of the document and it is worth checking as you
read: a reader looking for a place where a choice could have been made after seeing the answer
should find every branch keyed to something that cannot encode the answer.

**Implemented by.** `pipeline/04_features.py`, `pipeline/05_analysis_drd.py`,
`pipeline/06_analysis_gate.py`, `pipeline/07_export.py`, `local/figures.py`, `local/tables.py`.
Where code and this file disagree, this file wins and the code is fixed, or an amendment is written.

**Five vocabularies are owned here, and every row of each carries a stable slug.**
`prespecification/EXPORT-CONTRACT.md` section 11.3 assigns ownership of the attrition rungs, the
sensitivity ladder, the estimator ladder, the procedure-group names and the prespecified subgroup
list to this file, and `local/verify.py` asserts **set equality** against the lists below. A slug is
an identifier and is never printed; every user-visible string comes from the display label beside
it. The five vocabularies live in sections 2.4 (procedure groups), 2.6 (attrition rungs), 3.5
(estimator rungs), 6 (sensitivity rows) and 9.1 (subgroups). Where a list here and a list in the
export contract disagree, this file wins and the contract is amended in the same commit. The
disagreement is never resolved by a module choosing one at runtime.

---

## Where each required element lives

| Required element | Section |
|---|---|
| Both arms, and the rule that selects between them | 1 |
| The disclosure-floor coincidence at the lowest gate tier | 1.3 |
| The primary estimand | 3.1 |
| Model-and-integrate, and why not sum-the-observed-days | 3.2 |
| Jensen's inequality, and Monte Carlo marginalization with draws and seed | 3.3 |
| Continuous-time AR(1), and what happens if it will not converge | 3.4 |
| Model family and the complete fallback ladder with descent triggers | 3.5 |
| Splines, knots, interactions, random effects, covariates | 3.6 |
| Weighting for observation | 3.7 |
| Marginal estimate and confidence interval, g-computation and bootstrap | 3.8 |
| Day of week as a fixed effect | 3.6, 5.5 |
| The five protocol problems, each with a handling | 5 |
| Baseline floor | 3.10 |
| Absolute-scale companion endpoint | 3.9 |
| Delta-shift tipping point | 3.11 |
| Manski bounds | 3.12 |
| The full prespecified sensitivity ladder in plot order | 6 |
| Valid wear day definitions | 2.1 |
| Multiplicity | 7 |
| Collapse ladder for thin strata | 2.5 |
| The attrition ladder, every rung slug, and the closure assert | 2.6 |
| Protocol inclusion criterion 5, reconciled against the locked window | 2.6 |
| The fusion-status evidence rule, and the add-on rung it does not weaken | 2.4, 2.6 |
| The two concept-set gap measurements and the response to each | 2.7 |
| The prespecified subgroups and the rule that makes one not estimable | 9.1 |
| Locked exhibit list, alternate set, suppression rules | 9 |
| Separate weekday and weekend baselines, as the protocol asks | 2.2, 6 |
| The landmark observation weight, where lagged wear has no input | 4.4 |
| The full-cohort day-indexed landmark panel, and what it changes | 4.4 |
| The strata the collider comparison is standardized over, and why not the day grid | 4.4 |
| The suppression rule on that standardization, and what is reported when it fires | 4.4, 8 |
| The definitional condition, and why it sits outside the co-primary exposure | 4.4 |
| The coefficient ceiling that refuses a separated fit, and the counts it obliges | 4.9 |
| Denominators for sensitivities fitted on a subset of the cohort | 9.2 |
| Amendment log | 13 |

---

## 1. The two arms, and the rule that selects between them

The protocol contains two studies. This section states, before any count is seen, which one is the
manuscript and what the other is allowed to become.

### 1.1 Arm B is primary and is a guaranteed deliverable

**Arm B, Digital Recovery Debt**, is the primary manuscript. It answers: how much cumulative
baseline-normalized walking is lost after elective cervical and lumbar decompression and fusion, and
does that loss differ by anatomic region and fusion status. It is primary for a structural reason
rather than an expected one: **Arm B requires no events**. Every eligible episode contributes an
outcome, so Arm B cannot be extinguished by a thin event count, and its selection therefore cannot
have been made in response to one.

**Arm A, the early-warning gate analysis**, asks whether a proximal 3-day baseline-normalized step
decline precedes an EHR-recorded acute-care encounter within the next 3 calendar days. It requires
events. It runs only at the tier the protocol's decision table permits, and it is reported as a
secondary result whose headline is the feasibility gate itself.

### 1.2 The gate, and the tier it permits

The gate quantity is **the number of unique first EHR-recorded acute-care events through
post-discharge day 90 that have a computable proximal step ratio**, that is stage E of the
protocol's A through F ledger. It counts unique first events, never repeated person-days. It is
computed once, in Phase 3, and reviewed before any model is fit.

| Usable events | Tier | Permitted analysis | Permitted claim |
|---|---|---|---|
| 100 or more | 1 | Full parsimonious detection model with internal validation. Temporal validation if the later era holds at least 40 events, otherwise optimism-corrected clustered bootstrap validation | Detection performance may be reported as a performance estimate |
| 50–99 | 2 | Step-first model with **no broad feature selection**. Clustered bootstrap validation. Labelled exploratory in the title, the abstract and every exhibit caption | Association and exploratory performance, explicitly not a prediction tool |
| 20–49 | 3 | Event-centered association and visualization only. No prediction model, no discrimination metric, no alert-burden calculation | Association only. **No prediction-tool claim of any kind** |
| Fewer than 20 | 4 | No early-warning modeling at all | Feasibility statement only, with the count suppressed. See 1.3 |

"Step-first model with no broad feature selection" means: the covariate set is fixed at the
clinical-time set plus the three prespecified step features named in 4.8, and no variable is added,
dropped, screened, or penalised into or out of the model on the basis of its performance. There is
no stepwise selection, no univariable screening threshold, and no lasso path at any tier.

At tier 1 or 2 the exhibit set switches to the alternate set in section 9.5. That switch is keyed to
the event count, which is a count and not an estimate, and it is the only thing in this plan that
changes which exhibits are printed.

### 1.3 The coincidence at the bottom of the table, named rather than tripped over

The lowest tier's boundary is 20 events. The All of Us disclosure floor is also 20, in the exact
sense fixed in section 8: a count is disclosable only when it is zero or **strictly greater than
20**, so 1 through 20 inclusive are suppressed. The two thresholds are unrelated in origin and
identical in value, and the collision has two practical consequences that will otherwise be
discovered at proof stage.

> **If the gate lands at 20 events or fewer, the event count itself is unprintable.** It is reported
> as "20 or fewer, suppressed per All of Us dissemination policy" in the text, in Table 3, and in
> the terminal box of Figure 1. The sentence that reports the gate is the same sentence that
> suppresses it.

> **A gate of exactly 20 is permitted an analysis whose denominator it may not print.** Twenty
> events sits in tier 3, where event-centered association and visualization are permitted, and
> simultaneously at the top of the suppressed band, where the count may not be disclosed. The
> analysis runs and the count does not appear. That is not a contradiction to be resolved at proof
> stage; it is written down here so the Methods sentence and the exhibit are drafted for it in
> advance.

This is named in the Methods as a feature of the design rather than tripped over later. The Methods
sentence is drafted now, so it is not composed under deadline:

> The feasibility gate's lowest tier boundary and the All of Us disclosure floor are both 20 events.
> Where the observable event count fell at or below that value, the count is reported as "20 or
> fewer" in accordance with the All of Us Data and Statistics Dissemination Policy. Below 20 events
> the early-warning analysis was not attempted; at exactly 20 events the tier 3 analysis was
> performed and its denominator is reported in that same suppressed form.

Two consequences follow and are accepted in advance. First, a reader cannot distinguish 3 events
from 20; the manuscript says so. Second, stage F of the ledger, events by region and fusion stratum,
will very likely be suppressed in every cell, and prints as suppressed unless **all four** cells are
disclosable, because a single disclosed cell alongside three suppressed ones plus a disclosed total
recovers the suppressed cells by subtraction.

### 1.4 What Arm A contributes even at tier 4

At tier 4 the gate is still the study's secondary result and still drives Figure 1 and Table 3
Part A. The finding is: in a nationally recruited, EHR-linked, consumer-wearable cohort, the number
of surgical episodes with simultaneous adequate preoperative baseline wear, a computable
post-discharge signal, and an observable acute-care event is *this small*. That is a reportable and
useful result about the data source, and it is the honest reason the manuscript is Arm B.

---

## 2. Definitions on which everything downstream rests

Three of the five owned vocabularies are in this section: the procedure groups (2.4), the collapse
levels (2.5) and the attrition rungs (2.6). The valid-wear-day definitions of 2.1 carry the slugs
that the sensitivity ladder of section 6 uses for them, so the wear rule and the row that varies it
cannot drift apart.

### 2.1 Valid wear day

**Primary definition.** A person-date is a valid wear day when it carries **at least 600 heart-rate
minutes**, obtained by summing the per-zone minute counts for that person-date in
`heart_rate_summary`. Days with fewer than 100 steps are **retained** when heart-rate coverage
confirms wear, because profound inactivity may be the biological signal of interest and a
steps-based wear rule would delete exactly the days the study is about.

Two facts about `heart_rate_summary` are runtime probes, not assumptions: the exact per-zone minute
column name, and that the zones partition the day without double-counting a minute. The probe result
feeds the query. **Prespecified contingency:** if the probe shows the zones do not partition the day
(any person-date whose summed zone minutes exceed 1,440, or a summed distribution implausible
against `heart_rate_minute_level` on a seeded 200-person-day audit sample), the primary wear
definition falls back to sensitivity definition S2 below, and the substitution is reported in the
Methods and logged as an amendment. It does not fall back to minute-level counting for the whole
cohort, which is roughly 300 times the bytes and is not in the budget.

**Sensitivity definitions**, carried from the protocol and run as rows of the ladder in section 6:

- **S1**, slug `wear_definition_s1`, display label "Wear day at 40% heart-rate adherence". At least
  40% daily heart-rate adherence. Note for the reader that 40% of 1,440 minutes is 576 minutes, so
  S1 is only marginally more permissive than the primary rule; it is retained because it is the All
  of Us exploratory convention and its near-equivalence is itself worth showing.
- **S2**, slug `wear_definition_s2`, display label "Wear day at 10 hours plus 100 steps". At least 10
  hours of heart-rate wear **and** at least 100 steps. This is the commonly used All of Us
  physical-activity rule and it is the one rule that deletes profoundly inactive days.
- **S3**, slug `wear_definition_s3`, display label "Wear day at 8 hours". At least 8 hours of
  heart-rate wear.
- **S4**, slug `wear_definition_s4`, display label "Wear day at 12 hours". At least 12 hours of
  heart-rate wear.

**Analyzable day.** A day is analyzable for the daily deficit only if it is a valid wear day **and**
carries a non-null daily step total. A valid wear day with a null step total is treated as
unobserved and enters the observation model of section 3.7. The frequency of this case is reported.

### 2.2 Preoperative personal baseline

`B_i` is the **median** valid daily step count over postoperative days -30 through -8. The final 7
preoperative days are excluded because pain flares, preoperative testing, travel and preoperative
instructions alter activity. The median rather than the mean limits the influence of isolated
high-activity days. Eligibility requires at least 7 valid days in that window spanning at least 14
calendar days.

The median is computed with an **exact-median user-defined function**, never with
`APPROX_QUANTILES(x, 2)[OFFSET(1)]`, which returns the upper value on an even-length array and is
therefore not a median. Day-of-week composition of the baseline window is recorded per episode and
reported in aggregate.

**`baseline_dow_counts` counts valid baseline days, not calendar days.** The reading is fixed here
because the split below depends on it and because the derived table's own documentation does not say
which it is. On the calendar reading the array would hold nearly the same seven numbers on every
episode, since the window is a fixed 23-day span, and would carry no information at all. Two
identities follow and `pipeline/04_features.py` asserts both, halting rather than reporting if
either fails: `SUM(baseline_dow_counts)` equals `n_valid_baseline_days`; and, with index 0 as
Sunday, indices 1 through 5 sum to the weekday count and indices 0 and 6 sum to the weekend count
defined below.

**Separate weekday and weekend baselines, which the protocol asks for and versions 1.0 through 1.2
of this file dropped.** The protocol's baseline section asks for two things and not one: that
day-of-week composition be recorded, and that "a sensitivity analysis will estimate weekday and
weekend baselines separately". The paragraph above delivers the first. The second is specified in
full here and is carried as a supplementary sensitivity row in section 6, slug
`baseline_weekday_weekend_split`, display label **Separate weekday and weekend baselines**.

**The two baselines.** `B_i^weekday` is the median valid daily step count over the Monday through
Friday days of postoperative days -30 through -8. `B_i^weekend` is the same median over the Saturday
and Sunday days of that same window. Weekend is Saturday and Sunday, which is the same pair section
4.7 uses for the Arm A weekday-versus-weekend matching class, so one definition of the weekend
serves both arms and neither can drift. Both medians use the exact-median function and the primary
valid-wear rule of 2.1. Nothing about the window moves: the only thing that changes between the two
is which days enter which median.

**The minimum valid days required in each half of the week.** A 23-day span holds 6 or 7 weekend
days and 16 or 17 weekday days, depending on where it falls in the calendar. The split baseline
requires **at least 5 valid weekday days and at least 2 valid weekend days**. The two minima are
deliberately unequal, and they are set from the window's own arithmetic rather than from a
preference: 5 of the 16 or 17 weekday days available and 2 of the 6 or 7 weekend days available are
close to the same fraction of what the calendar offers, so neither half is held to a standard the
window cannot supply. Their sum is 7, exactly the primary rule's minimum, and the split is computed
only on episodes already in the analytic cohort, which cleared rung 12 of 2.6 and therefore already
satisfy both the 7-day minimum and the 14-calendar-day span. The set this row is fitted on is
consequently a **subset** of the primary's, never a superset: an episode with 7 valid days that all
fall on weekdays clears the primary baseline and fails this one. The span requirement is not applied
a second time within each half.

**An episode with valid days in only one half of the week.** It is **excluded from this sensitivity
row and from nothing else**. It keeps its primary `B_i`, stays in the analytic cohort, stays in
Table 1, stays in Figure 2, and contributes to the primary estimand exactly as it did before this
row existed. There is no fallback that substitutes the surviving half's median for the missing one,
and none that substitutes the pooled `B_i`. Either substitution would convert the row from "the
debt measured against a day-type-matched reference" into "the debt measured against a reference that
is day-type-matched on some episodes and not on others", which is not what the protocol asked for
and is not a quantity a reader could interpret. The excluded episodes are counted and the count is
printed, under the rule of 9.2 that a sensitivity fitted on a subset prints its own denominator.

**How the deficit is formed on this row, and how the contrast is reported.** The daily deficit
becomes

```
D_id = max(0, 1 - S_id / B_i^type(d))
```

where `type(d)` is weekday or weekend for the calendar day on which post-discharge day `d` falls.
Every other element of the estimator is identical to the primary: the same rung of the ladder of
3.5, the same covariate set including the 7-level day-of-week fixed effect of 3.6, the same
observation weights of 3.7, the same seeds, and `B = 500` bootstrap resamples under the convention
of 3.8. The row reports the **primary contrast**, fusion versus decompression pooled across region,
in baseline-equivalent activity days lost with a 95% CI, printed beside the primary's own value and
against the row's own `n`. Two descriptive numbers are reported with it, because they are what tell
a reader whether the split was worth making at all: the median `B_i^weekday` and the median
`B_i^weekend` by procedure group, and the median within-episode ratio `B_i^weekend / B_i^weekday`,
each subject to the disclosure floor of section 8. A ratio at 1 says the two baselines are one
measurement taken twice and the contrast should not move; a ratio away from 1 says how much the
denominator's calendar composition mattered, which is the question the protocol was asking.

**The four columns this rests on**, named here so that the derived table and this file cannot drift
apart. `baseline.baseline_steps_weekday` and `baseline.baseline_steps_weekend` are FLOAT64 and are
**null when their half of the window holds no valid day, never zero**, on the same reasoning that
makes `baseline_steps` null rather than zero: a zero baseline makes the ratio infinite and the
deficit silently 1 on every day, manufacturing maximal debt out of missing data.
`baseline.n_valid_baseline_days_weekday` and `baseline.n_valid_baseline_days_weekend` are INT64,
never null, and zero when the half holds no valid day. **The row's denominator is derived from the
two counts and never from the two medians being non-null**: it is the count of analytic episodes
with `n_valid_baseline_days_weekday >= 5 AND n_valid_baseline_days_weekend >= 2`. Deriving it from
the counts keeps the minimum-day rule visible and auditable in one place instead of hiding it inside
a null test that a later edit could weaken without anyone noticing.

### 2.3 Post-discharge day, and the taxonomy of an absent day

**Post-discharge day 1** is the first complete calendar day after the index discharge date. The
discharge day itself is day 0 and is excluded from every wearable window, because it is a partial
inpatient day whose step count mixes two settings.

Every day in the accrual window is exactly one of four kinds, and the distinction drives everything
in section 3:

| Kind | Definition | Handling |
|---|---|---|
| **Observed** | Valid wear day with a non-null step total | Contributes `D_id = max(0, 1 - S_id / B_i)` |
| **Missing** | Inside the window, inside the observation period, not a valid wear day, or valid with a null step total | Target of the observation weights (3.7) and of the delta-shift (3.11). **Never imputed as zero deficit** |
| **Censored** | Beyond the CDR observation cutoff, or after death, or after a repeat spine operation | Not at risk. The episode contributes a shortened window and this is recorded. Not "missing" |
| **Inpatient** | Inside the window and inside a readmission stay | **Kept in the primary.** A readmission is part of recovery, and deleting it would delete the worst days. Removed in the "inpatient days censored" sensitivity row |

Episodes whose window is truncated by death or by a repeat spine operation are excluded from the
primary estimand on their own attrition rung, `excl_window_truncated_by_death_or_reoperation` (2.6,
rung 15), and are expected to be too few to disclose. A supplementary row,
`truncated_assigned_max_debt`, assigns them the maximal debt of 35 days lost, which is the extreme
composite interpretation; it is a supplementary row and not a member of the Figure 3 block 2 ladder
(section 6), and it is reported whatever the count.

### 2.4 Procedure groups, and the slug for each

Four groups: cervical decompression, cervical fusion, lumbar decompression, lumbar fusion. An
episode with decompression and fusion on the same date and region is classified **fusion with
decompression**, that is, fusion. Additional-level and instrumentation codes cannot define an
operation without a primary procedure code; what they can do once an operation is established is
settled below. Region comes from the region-tagged concept set in `pipeline/cs_spine.py`.

**The group vocabulary, owned here.** Print order is the order of this table. No consumer hardcodes
four groups, four Table 1 columns or four Figure 2 series; the set present at run time is whichever
the collapse level of 2.5 selected.

| order | slug | display label | exists at |
|---|---|---|---|
| 1 | `cervical_decompression` | Cervical decompression | collapse level 1 |
| 2 | `cervical_fusion` | Cervical fusion | collapse level 1 |
| 3 | `lumbar_decompression` | Lumbar decompression | collapse level 1 |
| 4 | `lumbar_fusion` | Lumbar fusion | collapse level 1 |
| 5 | `all_groups` | All groups | collapse levels 1, 2 and 3 |
| 2a | `fusion` | Fusion | collapse level 2 only |
| 2b | `decompression` | Decompression | collapse level 2 only |

Two group-level factors are used in models: `fusion` (fusion versus decompression) and `region`
(cervical versus lumbar). The primary contrast is on `fusion`.

**Fusion status reads all qualifying evidence, including add-on and instrumentation codes.** An
episode whose existence a primary procedure code has already established is classified `fusion` when
**any** qualifying code in its same-day bundle carries `procedure_class = 'fusion'`, whether or not
that code is an add-on. The rule is written here because the two readings of it disagree on a real
set of episodes, and the disagreement is settled before a count exists rather than at the keyboard
afterwards.

- **Fourteen of the sixteen add-on and instrumentation codes in the locked set carry
  `procedure_class = 'fusion'`**: `22614`, `22632` and `22634`, the additional-level arthrodesis
  codes; `22840` through `22848`, the instrumentation codes; and `22853` and `22854`, the interbody
  devices. The other two, `63035` and `63048`, are decompression add-ons and carry
  `procedure_class = 'decompression'`, so no add-on in the set can move an episode across the
  contrast in the other direction.
- **Instrumentation without arthrodesis is essentially never performed in degenerative spine
  surgery.** The presence of one of these codes is therefore strong evidence that a fusion occurred,
  and treating it as no evidence at all discards the clearest signal the bundle carries.
- **The two readings differ only when the primary arthrodesis code is absent from the record**,
  which is a coding-capture gap and not a clinical fact. In exactly that situation the add-on is the
  only evidence of the fusion, and ignoring it would place a fusion patient on the decompression
  arm. That is not a lost episode, it is a misclassified one, sitting on the wrong side of the
  primary contrast and biasing it.
- **The false-positive risk in the other direction is low**, because these codes are specific. A
  decompression-only episode would have to carry a spurious arthrodesis or instrumentation code to
  be misassigned, which is a rarer failure than the capture gap the rule repairs.

**This does not weaken the add-on rule, and the two rules answer different questions.** The add-on
rule, enforced at rung 9 of 2.6, says that an add-on cannot establish that an **operation
happened**: a same-day bundle carrying add-on and instrumentation codes only, with no primary
procedure code beside them, is not an operation, and it is excluded and counted at that rung. That
rule stands unchanged, and nothing here re-admits an episode it removed. The rule stated above is
about which **arm** an episode already established by a primary code belongs to. Existence first,
then classification: an add-on is mute on the first question and probative on the second. The two
are easy to conflate, and a reader will try, so the distinction is written out rather than left to
be inferred from the fact that both sentences mention add-on codes.

**The region half of the same question is settled, and it is settled by the concept set rather than
by a rule of this section.** Every add-on in the locked set carries `region = 'unspecified'` in
`pipeline/cs_spine.py`, by rule and not by accident, so an add-on can neither supply a region nor
override a cervical, lumbar or thoracic assignment. Reading all qualifying evidence for fusion
status therefore changes nothing about region: a bundle's region still comes from its region-bearing
codes, and a bundle with none survives no further than rung 7 of 2.6. This is stated so that it is
not reopened alongside the fusion question, which is the question that actually needed deciding.

**One rule, used by both tables that report a group.** The stratified ceiling table of
`pipeline/02_pregate.py`, which reports counts by region and fusion status, and the procedure groups
carried into rung 16 of the attrition ladder, the analytic cohort, are built under the rule above and
not under two readings of it. Comparability between those two tables is the entire purpose of the
pre-gate: the ceiling is an upper bound on what the ladder can deliver, and an upper bound computed
under a different classification rule bounds nothing. `pipeline/02_pregate.py` read fusion status
from non-add-on records only when this paragraph was written, and is corrected against it under the
header rule that where code and this file disagree, this file wins.

**The reading this section declines is reported rather than argued about.** Fusion status from
non-add-on records only is a prespecified supplementary sensitivity,
`fusion_status_non_add_on_only`, in section 6.

**Thoracic is a tag, and it is not a group.** The locked concept set tags thoracic codes, because a
cervicothoracic or thoracolumbar bundle has to be classified before it can be judged. The protocol's
target population is elective surgery for degenerative **cervical or lumbar** disease, and the study
title says cervical and lumbar, so an episode whose regional evidence resolves entirely to thoracic
is **outside the target population and is excluded**, on its own counted rung (2.6, rung 8). It is
not folded into the nearest region: folding would place an operation in a group whose recovery curve
it does not belong to, and would do it silently. An episode carrying thoracic evidence **beside**
cervical or lumbar evidence is a junction case, assigned by the junction rule of
`decisions/2026-08-25-spine-region-tagging.md`, and it is not touched by that rung.

### 2.5 The collapse ladder for thin strata

Prespecified so that it is not a judgment call made after seeing counts. The level is decided
**once**, on the Phase 3 attrition ladder, before any model is fit, on the exact within-perimeter
counts; only the rounded counts are ever printed. The chosen level is written to `results.json` and
named in the Methods.

| Level | slug | Trigger | What is estimated |
|---|---|---|---|
| **1. Four groups** | `four_group` | All four of cervical decompression, cervical fusion, lumbar decompression and lumbar fusion have a **disclosable** episode count | Full model with `fusion`, `region`, their interaction, and region-specific day curves. Figure 2 shows four series. Table 1 has four columns |
| **2. Two groups** | `two_group` | Any one of the four is **not** disclosable, and both fusion and decompression are | Fusion versus decompression, region-adjusted, with no region interaction. Figure 2 shows two series. Table 1 collapses to two columns with a footnote naming the collapse |
| **3. One group** | `single_group` | Either fusion or decompression is **not** disclosable | Pooled descriptive only. One recovery curve, one debt estimate, **no between-group contrast**, and an explicit sentence that no contrast was estimable at the prespecified floor |
| **0. Nothing** | `no_estimand` | The analytic cohort itself is **not** disclosable | Attrition ladder only, with the terminal count suppressed. No estimand is reported |

**"Disclosable" has exactly one definition in this document**, and it is the predicate
`disclosure.disclosable(n)`, true when `n` is zero or strictly greater than 20 (section 8). Every
threshold in this file reads through that predicate. No section states a second floor, and a
sentence anywhere in this project that appears to state one is an error to be corrected against this
paragraph rather than a rule to be followed.

**The disclosure floor doubles as the analysis floor.** A cell that cannot be printed is a cell that
will not be modelled. This removes the class of decision where an analyst fits a four-group model,
sees an unstable cell, and collapses afterwards.

### 2.6 The attrition ladder, and the slug for every rung

This table is the single authoritative rung list for the study. `CLAUDE.md` section 4 and
`prespecification/EXPORT-CONTRACT.md` sections 3.3 and 7.2 transcribe it and do not extend it;
`pipeline/03_cohort.py` emits it; `local/verify.py` asserts set equality against
`figure1_strobe_ladder.csv`. **Nineteen rungs.** Columns emitted per rung:
`step, slug, kind, unit, n_in, n_dropped, n_out, reason`.

| step | slug | kind | unit | display label (ladder box) | reason display (exclusion box) |
|---|---|---|---|---|---|
| 1 | `program_participants` | exclusion | persons | Participants in the Controlled Tier release | No qualifying spine procedure concept in the electronic health record |
| 2 | `episode_construction` | conversion | persons to episodes | Spine surgical episodes | Same-day qualifying procedure records collapsed into one episode; operations on different dates stay separate episodes until step 13 |
| 3 | `excl_trauma_malignancy_infection` | exclusion | episodes | Episodes after the nonelective-indication exclusions | Trauma, spinal cord injury, malignancy, metastatic disease or spinal infection recorded in the 30 days before or on the index date |
| 4 | `excl_ed_encounter_not_elective` | exclusion | episodes | Elective episodes | Emergency department encounter immediately before the index operation, with no coding evidence of an elective episode |
| 5 | `excl_prior_operation_90_days` | exclusion | episodes | Episodes with no prior operation within 90 days | Prior qualifying spine operation within 90 days of the index episode |
| 6 | `excl_simultaneous_cervical_lumbar` | exclusion | episodes | Episodes at a single anatomic region | Simultaneous cervical and lumbar procedure |
| 7 | `excl_region_unspecified_only` | exclusion | episodes | Episodes with an established anatomic region | Procedure coding that cannot establish an anatomic region |
| 8 | `excl_thoracic_only` | exclusion | episodes | Cervical or lumbar episodes | Thoracic-only operation, outside the target population |
| 9 | `excl_add_on_code_only` | exclusion | episodes | Episodes defined by a primary procedure code | Add-on and instrumentation codes only, with no primary procedure code |
| 10 | `excl_missing_discharge_date` | exclusion | episodes | Episodes with a recorded discharge | No recorded discharge date for the index admission |
| 11 | `excl_no_wearable_data` | exclusion | episodes | Wearable-linked spine episodes | No Fitbit activity record linked to the participant |
| 12 | `excl_inadequate_baseline_wear` | exclusion | episodes | Episodes with adequate preoperative baseline wear | Fewer than 7 valid wear days in postoperative days -30 to -8, or a span under 14 calendar days |
| 13 | `excl_not_first_eligible_episode` | exclusion | episodes | First eligible episode per participant | A later operation by a participant whose first eligible episode is already in the cohort |
| 14 | `excl_no_computable_post_discharge_window` | exclusion | episodes | Episodes with a computable post-discharge day 1 to 35 window | No analyzable day inside post-discharge days 1 to 35 before censoring |
| 15 | `excl_window_truncated_by_death_or_reoperation` | exclusion | episodes | Analytic cohort | Accrual window truncated by death or by a repeat spine operation |
| 16 | `analytic_cohort` | terminal | episodes | Analytic cohort | |
| 17 | `events_identified` | conversion | episodes to events | Acute-care events through day 90 | |
| 18 | `excl_event_without_computable_landmark` | exclusion | events | Analyzable acute-care events | Event on post-discharge day 1 to 4, with no computable proximal window |
| 19 | `events_analyzable` | terminal | events | Analyzable acute-care events | |

An exclusion rung's display label names the box of **survivors** below it, which is why steps 15 and
16 share the label "Analytic cohort". Reason displays are printed strings governed by character
equality in `local/verify.py`; they are not paraphrased at render time.

**The order is fixed and is not an implementation detail.** A ladder counts each episode once, at
the first rung it fails, so reordering changes every rung's `n_dropped` without changing the
analytic n. That changes what the Figure 1 exclusion boxes say. Reordering is an amendment under
section 13.

**Two conversions, and what the closure assert means at each.** Step 2 converts persons to episodes
and step 17 converts episodes to events. The closure assert is evaluated **within unit**, and each
conversion is recorded as an explicitly labelled re-basing rather than a silent one.

- **Every exclusion rung** asserts `n_in - n_dropped = n_out`, both sides in the same unit.
- **Step 2** cannot assert that identity, because `n_in` is in persons and `n_out` is in episodes.
  It carries a third count, `n_carried_forward`, in persons, and asserts
  `n_in - n_dropped = n_carried_forward` together with `n_out >= n_carried_forward`, since a carried
  person yields at least one episode. Its `n_dropped` is persons who carry a qualifying concept but
  whose records yield no dated episode.
- **Within the episode unit**, the sum of `n_dropped` over steps 3 to 15 plus the analytic n of step
  16 equals the `n_out` of step 2. This is the assert that steps 4, 7, 8 and 13 would break if they
  were left implicit, which is the reason they are rungs and not prose.
- **Step 17 carries no `n_dropped`**: every analytic episode is at risk for an event. It asserts only
  that its `n_in` equals the `n_out` of step 16, and its own `n_out` is a count of events, which may
  be zero.
- **Step 19 counts events, not episodes.** It carries no `n_dropped` and is **excluded** from the
  "sum of drops plus the analytic n equals the starting n" assert, as is step 17. Steps 17 to 19
  close among themselves: `n_out(17) - n_dropped(18) = n_out(19)`.

Asserted in `pipeline/03_cohort.py` and again in the flow-figure builder. If it does not close,
raise. Do not adjust a count to make it close. Only the rounded counts are ever printed, so the
printed boxes will not reconcile arithmetically; the rounding footnote is published and the
displayed numbers are never adjusted to make them add up (9.1).

**Step 4, the elective proxy, operationally defined.** Protocol exclusion criterion 2 excludes "an
ED encounter immediately preceding the index operation, unless chart coding clearly supports an
elective episode". Neither "immediately preceding" nor "clearly supports" is computable as written,
so both are fixed here, before any count exists.

- **Immediately preceding** means an emergency department `visit_occurrence` whose end date falls on
  the index operation date or on either of the 2 calendar days before it. Two days rather than one,
  because an ED presentation late on a Friday that leads to a Monday operation is exactly the case
  the criterion is about and a same-day rule would miss it. The ED `visit_concept_id` values are
  enumerated against the CDR's actual distribution before use (4.1), never assumed.
- **Coding evidence that rescues the episode**, any one of the three being sufficient: the index
  admission is coded elective or scheduled in `visit_detail` or in the admitting-source concept;
  **or** a degenerative index diagnosis (spondylosis, spinal stenosis, disc degeneration or
  displacement, spondylolisthesis, or radiculopathy or myelopathy of degenerative origin) is
  recorded on the index encounter **and** nothing from the trauma, malignancy or infection sets of
  step 3 is recorded on the ED encounter; **or** an outpatient visit carrying a degenerative spine
  diagnosis is recorded in the 90 days before the index date.
- An episode with a qualifying ED encounter and none of the three rescues is excluded and counted
  here. The count, and the share rescued by each of the three routes, go to the STROBE supplement.

This rung is a **proxy** and is labelled as one in the Methods, because it cannot read a chart. Its
failure mode is a genuinely elective operation preceded by an unrelated ED visit with no degenerative
diagnosis coded anywhere, which is lost. The selection that produces runs toward the nonelective end
of the spectrum, which is the direction the criterion intends, and the number removed is reported so
a reader can size it.

**Step 7, unspecified region only.** Protocol exclusion criterion 3 excludes "procedure coding that
cannot establish an anatomic region". An episode is excluded here when **every** qualifying code in
its same-day bundle carries `region = 'unspecified'` in `pipeline/cs_spine.py`. That is the case for
the add-on and instrumentation codes, and for the level-agnostic ICD-10-PCS stem exposed as
`LEVEL_AGNOSTIC_PCS_STEMS = {"00NT"}`, release of spinal meninges, whose fourth character names a
tissue rather than a level. Where an unspecified code sits **beside** a region-bearing code on the
same date, the region comes from the region-bearing code and the episode survives this rung. No
sensitivity can recover an absent level, so unlike the junction codes this rung has no mirrored
counterpart on the supplementary list of section 6.

**Step 8, thoracic only.** Defined in 2.4. An episode whose regional evidence resolves entirely to
thoracic is outside the target population and is excluded and counted here.

**Step 9, add-on codes only, and the question this rung does not answer.** An episode is excluded
here when **every** qualifying code in its same-day bundle is an add-on: instrumentation, an
interbody device, or an additional-level code, with no primary procedure code beside it. Such a
bundle is a billing fragment rather than an operation, and nothing downstream could date it,
region it or classify it. This rung asks only whether an **operation happened**. It does not decide
which arm an operation belongs to, and it is not weakened by the rule of 2.4 under which fusion
status reads all qualifying evidence, add-on codes included: that rule applies only after a primary
code has established the episode, and it never re-admits an episode this rung removed. Read together
the two are one sentence: an add-on cannot make an operation, and once a primary code has, an add-on
can say what kind it was.

**Step 13, the first eligible episode.** The protocol's episode-construction rule is: "If multiple
eligible episodes remain, use the first episode with adequate baseline Fitbit data." It is a rung
rather than prose because it is a real reduction between step 12 and the analytic cohort, and an
uncounted reduction breaks the closure assert on the first real run. The rule: among a participant's
episodes surviving step 12, keep the one with the earliest index date. A tie inside a participant
cannot occur, because same-date records were collapsed at step 2. Every later episode is dropped
here and counted.

**Person and episode therefore coincide in the primary**, which is what makes the person random
effects of 3.6 and the person-clustered bootstrap of 3.8 coherent: the resampling unit and the
outcome unit are the same object. The secondary analysis admitting later operations reads the
episodes dropped at step 13 back in, nests episode within person, and keeps person-clustered
inference. Any statement anywhere in this project that a participant may contribute more than one
episode **to the primary** is wrong and is corrected against this rung.

**Protocol exclusion criterion 6 is subsumed, and the subsumption is stated so a reviewer does not
read a gap.** Criterion 6 excludes "a device first appearing during the immediate postoperative
period, because measurement reactivity and absent baseline data prevent individualized comparison".
A participant whose device first appears after the operation has **no** preoperative wear at all, so
no such participant can clear step 12, which requires at least 7 valid wear days in postoperative
days -30 to -8. The criterion is therefore enforced with certainty by step 12 and carries no rung of
its own. A separate rung would count zero by construction and would invite a reader to believe it
was measuring something. The **device-change** exclusion is a different criterion, is not subsumed,
and remains sensitivity row 8 of section 6, `device_change_excluded`.

**Protocol inclusion criterion 5, reconciled against the locked window.** Criterion 5 requires "at
least one eligible post-discharge risk window before postoperative day 90"; the locked primary
endpoint requires a computable post-discharge day 1 to 35 accrual window. These are not two versions
of one criterion, and neither is drift from the other.

- Criterion 5 is a **minimum of one** window, phrased in postoperative time. It is implemented once
  per arm: step 14 for Arm B, at the discharge anchor, and step 18 for Arm A, at the proximal
  landmark.
- Post-discharge day 1 is postoperative day `LOS + 1`. For any episode discharged before
  postoperative day 89, post-discharge day 1 falls before postoperative day 90, so an episode that
  clears step 14 satisfies criterion 5 by construction and step 14 is the **stronger** of the two
  requirements. An episode discharged on postoperative day 89 or later has no post-discharge day
  inside the protocol's 90-day horizon and fails both.
- The whole 35-day accrual window lies inside postoperative day 90 whenever the index length of stay
  is 55 days or fewer. Episodes with a longer stay are **retained**, because the estimand is defined
  in post-discharge time and an ambulatory-exposure quantity does not stop being defined at a
  postoperative-time boundary. Their count is reported.

The single departure from the protocol remains the change of anchor recorded in 5.1 and in
`decisions/2026-08-25-recovery-debt-window.md`. Criterion 5 is not part of it, and a reviewer
comparing protocol to Methods should read this paragraph rather than infer drift.

**Step 14, a computable accrual window, operationally defined.** An episode clears step 14 when it
is at risk (2.3) on at least one day of post-discharge days 1 to 35 **and** contributes at least one
**analyzable** day (2.1) inside that window. The second condition is the binding one: an episode
with zero analyzable days contributes nothing to the fit, and integrating a 35-day debt for it would
be extrapolation from covariates with no observation of its own to anchor it. The number excluded
here, and the covariate distribution of those episodes, go to the STROBE supplement, because this is
the one rung whose selection the observation weighting of 3.7 cannot repair: it never sees the
episodes it removed.

**Trauma, malignancy and infection are one rung, not three.** `CLAUDE.md` previously promised that
each of the seven eligibility exclusions would be "labeled separately in the emitted ladder". That
promise is retired here, deliberately. The three indications are applied as one composite screen over
one 30-day lookback; an episode can trip more than one of them at once; and a ladder counts each
episode once, at the first rung it fails. Three separate rungs would therefore carry order-dependent
counts that a reader would misread as prevalences. They would also, at the cohort size this study
expects, very likely produce three suppressed rows where the composite produces one disclosable one,
which loses the information rather than refining it. The composite is one rung, step 3; the
breakdown by indication goes to the STROBE exclusion-reason ledger, where the disclosure floor
permits it. `CLAUDE.md` is corrected against this table.

### 2.7 The two concept-set gap measurements, and the response to each

The locked 852-concept set has two known gaps on the cervical side. Both are **measured** in Phase 2
and both are **stop-and-report** items: the two numbers go in front of the human at one stop, before
any outcome is computed, and the response to each is prespecified here so that it is not chosen
after the number is seen. Neither measurement adds a code to the locked set. Measuring a code is not
adding it.

| Gap | What is absent | What it costs | Measured by |
|---|---|---|---|
| **Decompression** | The protocol names six cervical decompression CPT codes; the locked set carries 63020 and 63075. Absent: 63001, 63015, 63040, 63045 | **Missing cases.** Operations the locked set cannot see at all. Costs n and may select, but moves no case between arms | `cs_spine.cervical_decompression_split_sql()` |
| **Fusion** | 22554, the legacy anterior cervical arthrodesis the protocol pairs with 63075, plus 22590 and 22595 | **Misfiled cases.** 63075 is in the set and is tagged cervical **decompression**, so a legacy-coded ACDF arrives on the wrong arm of the primary contrast and biases it toward the null | `cs_spine.cervical_fusion_split_sql()` |

**The two numbers, defined before they exist.**

- `D`, the persons the locked set classifies as cervical decompression: the three `locked set: ...`
  rows of the decompression builder.
- `C`, the `n_persons` on the `candidate CPT only, invisible to the locked set` row of the
  decompression builder: persons the locked set cannot see at all.
- `M`, the `n_also_carrying_locked_cervical_decompression` value on the `candidate CPT only,
  invisible to the locked set` row of the fusion builder: persons carrying a candidate cervical
  fusion code, no locked cervical fusion evidence, and locked cervical decompression evidence. These
  are the misfiled anterior cervical fusions.
- The two reported shares are `f_missing = C / (C + D)` and `f_misfiled = M / D`.

Both are shares of **counts**. No contrast, direction or P value exists at the Phase 2 stop, so
nothing about the study's answer can leak into the branch that is taken.

**The prespecified response to the fusion gap.** A misfiled fraction `f` of one arm attenuates a
two-arm contrast by roughly `2f` when the arms are of similar size, because each misfiled episode is
subtracted from one arm's mean and added to the other's.

| `f_misfiled` | Response, fixed in advance |
|---|---|
| `M` is zero | Record the measured zero in the Methods and the supplement. No amendment, no extra row |
| Above zero, **5% or less** | Attenuation of roughly 10% or less, comfortably inside the interval this study will produce. The locked set is **not** amended. A supplementary row, `cervical_fusion_gap_reclassified`, moves the `M` episodes to cervical fusion and re-estimates the primary contrast; it is reported whatever it shows |
| **Above 5%** | Attenuation becomes comparable to a plausible effect. The concept set **is** amended to carry 22554, 22590 and 22595 as cervical fusion; the amendment is written in section 13 with the measured share and the date; this file is re-hashed **before any outcome is computed**; and the pre-amendment classification becomes the supplementary row instead |

**The prespecified response to the decompression gap.** Missing cases cannot move the contrast, so
the response is deliberately weaker.

| `f_missing` | Response, fixed in advance |
|---|---|
| `C` is zero | Record the measured zero. No amendment |
| Above zero, **10% or less** | Stated omission: the four absent codes and the measured share go in the Methods and in the limitations. The set is not amended |
| **Above 10%** | The cervical decompression arm is materially incomplete. The set is amended to carry 63001, 63015, 63040 and 63045, under the same section 13 and re-hash discipline |

The 5% and 10% thresholds are fixed here, before the numbers exist, and they differ because the two
gaps do different damage: a misfiled case sits on the wrong arm, a missing case sits on neither.
Neither threshold is tuned. Neither may be moved after a measurement without an amendment recording
the old value, the new value and the reason.

**What happens under every outcome is therefore written down.** Both measurements are reported in
the Methods whatever they show, including a measured zero, because "we checked and it was zero" and
"we did not check" are different claims and only one of them is defensible.

---

## 3. Arm B, Digital Recovery Debt: the primary analysis

### 3.1 The primary estimand

Let `S_id` be the daily step total on post-discharge day `d` for episode `i`, `B_i` the preoperative
baseline of 2.2, `A_id = S_id / B_i` the normalized activity, and

```
D_id  = max(0, 1 - A_id)                     the daily deficit, bounded in [0, 1]
DRD_i = sum over d = 1..35 of D_id
```

**Digital Recovery Debt is accrued over post-discharge days 1 to 35.** The unit is
**baseline-equivalent activity days lost**, bounded at 35: one activity day lost is the ambulation
that patient would normally complete in one day. A day at or above baseline contributes zero. A day
with zero recorded steps on a valid wear day contributes one.

The window is **discharge-anchored**, which is the one place this plan departs from the protocol's
postoperative day 8 to 42. The reasoning, the cost, and the sensitivity that recovers the protocol's
window are in section 5.1 and in `decisions/2026-08-25-recovery-debt-window.md`. Both windows are 35
days long, so the estimand's scale and its bound at 35 are identical under either, and the two rows
of Figure 3 are on the same unit.

**The primary contrast** is fusion versus decompression, pooled across region:

```
Delta = psi(fusion) - psi(decompression),     in baseline-equivalent activity days lost
```

where `psi(g)` is the covariate-standardized marginal mean debt when every episode in the analytic
cohort is set to procedure group `g`, defined formally in 3.8. A positive `Delta` means fusion loses
more. The prespecified direction of the hypothesis is that fusion shows the greater debt; the test
is two-sided regardless, at 5%, and no equivalence claim will be made from a confidence interval
that includes zero. If the interval includes zero, the result is reported as inconclusive with the
interval width stated in activity days lost.

**Pooling with an interaction present.** The model in 3.6 contains a fusion-by-region interaction.
"Pooled across region" therefore means standardization, not omission: `Delta` is the difference
between two whole-cohort predictions made at the cohort's own region and covariate distribution. It
is not a coefficient and it is not a weighted average chosen at analysis time.

### 3.2 The estimator is model-and-integrate, not sum-the-observed-days

This is the most consequential choice in the plan, and it is a choice about bias, not about
elegance. It is set out at length because a reviewer who does not follow the argument will read the
modelled estimate as an unnecessary complication of a sum.

**The naive estimator and why it fails.** The obvious estimator sums the observed daily deficits:
`DRD_naive_i = sum over observed d of D_id`. Under this estimator every missing day contributes
exactly zero deficit, which is the assertion that on each unobserved day the patient walked at or
above their own preoperative baseline. That assertion is not conservative and it is not neutral. It
is the most favourable possible completion of the window.

**The bias has a direction, and the direction is the worst one available.** Non-wear is most likely
precisely when the true deficit is largest: a patient in pain, readmitted, deconditioned or unwell
is the patient who stops charging and wearing the device. So the days deleted are disproportionately
the high-deficit days, and `DRD_naive` is biased **downward**. Worse, the amount of non-wear is
itself greater in sicker patients and in the more invasive group, so the downward bias is **larger
in the group expected to have the larger debt**. The naive estimator therefore attenuates exactly
the between-group contrast this paper is about, and it does so in a direction that manufactures a
null. A reviewer would be right to reject a null result built on it.

**Scaling by the observed fraction does not fix it.** Multiplying the observed-day sum by
`35 / (number of observed days)` replaces "missing days had zero deficit" with "missing days looked
like this patient's observed days", which is missing-completely-at-random within person. It removes
the crudest part of the bias and leaves the informative part untouched, because the whole objection
is that missing days do *not* look like observed days.

**What is specified instead.**

1. Model the **daily deficit** `D_id` directly, as a function of a post-discharge-day spline
   interacted with procedure group, plus region, day of week, and the covariate set (3.6).
2. Fit on **observed person-days only**, weighted by the inverse probability of observation (3.7),
   so that observed days stand in for comparable missing days rather than for nothing.
3. **Integrate the fitted daily deficit over the whole 35-day window** for every episode, including
   the days that episode did not contribute, and average over the cohort under each procedure group
   (3.8). The integral over a 35-day grid of daily values is a sum over `d = 1..35`; it is called an
   integration here because the fitted object is a continuous curve in post-discharge day and the
   sum is its discretisation on the day grid the estimand is defined on.
4. Report the marginal estimate and its confidence interval.

**Direct summation on complete windows is the sensitivity, not the primary.** It appears as row 3 of
the ladder in section 6 and as the unadjusted median and interquartile range column of Table 2,
where it is labelled as the naive estimator restricted to the most complete windows, with its own
denominator printed. Reporting it is not a concession; it is the anchor that lets a reader see how
far the modelled estimate moved and in which direction.

### 3.3 Trap one: the deficit function is convex, so a mean activity may not be plugged into it

`D = max(0, 1 - A)` is a convex function of `A`. By Jensen's inequality, for any non-degenerate
distribution of `A`,

```
E[max(0, 1 - A)]  >=  max(0, 1 - E[A])
```

with equality only when `A` is degenerate or lies entirely at or below baseline. So an analysis that
models mean normalized activity and then applies the deficit function to the fitted mean
**underestimates the debt**, and underestimates it most in the groups and on the days where activity
is most variable. Two rules follow, and both are binding.

**Rule 1. Model `D`, never `A`.** The response variable of the primary model is the daily deficit
itself. No quantity in Table 2 or Figure 3 is produced by pushing a fitted activity through
`max(0, 1 - .)`. Where mean normalized activity is reported (Table 2), it is reported as
`1 - D_bar`, that is, mean normalized activity **capped at baseline**, which is exactly the
complement of the modelled deficit and requires no second model and no inequality.

**Rule 2. Marginalize the random effects by Monte Carlo, never by setting them to zero.** In a
generalized linear mixed model with a non-identity link, the prediction at `b = 0` is the
**conditional** mean for a median-random-effect episode, not the **marginal** mean of the
population. The two differ whenever the link is nonlinear, and the marginal mean is the estimand.
The marginal fitted deficit is therefore obtained by integrating the conditional mean over the
estimated random-effect distribution:

```
E[D | X, day, group] = integral over b of  g_inverse( eta(X, day, group) + z'b )  dN(0, Sigma_hat)(b)
```

approximated by Monte Carlo:

- **Number of draws: `M = 2,000`** random-effect vectors from `N(0, Sigma_hat)`.
- **Seed:** the project master seed `SEED = 0`. For the point estimate the generator is
  `numpy.random.default_rng(SEED)`; inside clustered bootstrap resample `b` it is
  `numpy.random.default_rng([SEED, b])`, so any single resample reproduces independently. If the fit
  is in R, the equivalent is `set.seed(0)` with the RNG kind pinned to `"Mersenne-Twister"` and
  `sample.kind = "Rejection"`, and both the seed and the RNG kind are written to `results.json`.
- **Common random numbers.** The same `M` draws are reused across days, across procedure groups, and
  across covariate profiles within a resample. The contrast is a difference of two integrals
  computed on the same draws, so most Monte Carlo noise cancels in `Delta` rather than accumulating
  over 35 days.
- **Convergence check, prespecified.** The whole marginalization is recomputed once at `M = 4,000`
  on a different stream, `default_rng([SEED, 999])`. If the primary contrast moves by more than
  **0.05 activity days lost**, which is about one seven-hundredth of the 35-day scale, `M` is raised
  to 10,000 and the check repeated. The final `M` and the observed movement are reported.

### 3.4 Trap two: an AR(1) residual lags in the index, not in time

A standard AR(1) residual correlation is defined on the *observation index*: it assigns correlation
`rho` to consecutive rows of a person's data. With complete daily data those two things coincide.
With irregular missing days they do not, and the model then treats a pair of days 6 days apart as
though they were 1 day apart, because they happen to be adjacent rows. That is not a small
distortion in a study whose entire subject is irregular non-wear.

**Specified: the continuous-time analogue.** The residual correlation is

```
Corr(e_it, e_it') = rho ^ |t - t'|,     with |t - t'| measured in DAYS
```

which is the continuous-time AR(1), equivalently the exponential or Ornstein-Uhlenbeck correlation.
In R this is `glmmTMB`'s `ou(times + 0 | person)` structure, or `nlme::corCAR1`. It reduces to the
familiar AR(1) exactly when no day is missing.

**If it will not converge.** The descent is prespecified and ordered, and each step is triggered by
a computational property of the fit, never by the estimate it produces:

1. Continuous-time AR(1) residual, plus a person random intercept and a random linear slope in
   post-discharge day.
2. **On non-convergence, or `rho_hat` at a boundary of 0 or 1:** drop the residual correlation
   structure and keep the person random intercept plus random linear slope. A random slope in real
   post-discharge day already induces a within-person correlation that is a function of elapsed
   time, not of row order, so the essential property is preserved.
3. **On a singular random-effect covariance, or a random-effect correlation with `|r| > 0.99`:**
   keep the person random intercept only.
4. In every case, **all reported uncertainty comes from the person-level cluster bootstrap of 3.8**,
   which resamples whole participants and is therefore valid under an arbitrarily misspecified
   within-person correlation. The residual structure affects the point estimate's efficiency and,
   very mildly, its value; it is not what the confidence interval rests on. This is stated in the
   Methods, because it is the reason the descent is not a threat to the inference.

The rung reached is recorded in `results.json` and named in the Methods.

### 3.5 The model family, and the complete fallback ladder

The response is a daily deficit bounded in `[0, 1]` with genuine mass at **both** ends: mass at 0
because a patient at or above baseline is common, especially late in the window, and mass at 1
because a day with zero recorded steps on a worn device is real and is exactly the signal of
interest. A family that cannot represent both boundary masses will misplace the estimand.

The ladder is walked **top down** and stops at the first rung that fits cleanly. A rung is never
revisited after the estimate it produces has been seen. Every descent trigger below is a
computational property of the fit or of the environment. **No trigger references the direction,
magnitude, or significance of any contrast.**

| Rung | slug | Family | Where it runs | Descent trigger |
|---|---|---|---|---|
| **1** | `r_ordered_beta_glmm` | **Ordered beta GLMM.** A single latent index with two cutpoints generates Pr(D = 0), Pr(D = 1) and the continuous beta part, so one coefficient governs both the chance of a boundary and the magnitude in between. `glmmTMB` with `family = ordbeta()` | R Analysis Environment, on the Controlled Tier app allow-list | T0, T1, T2 or T3 |
| **2** | `r_zero_one_inflated_beta_glmm` | **Zero-one-inflated beta GLMM**, three parts: logistic for Pr(D = 0), logistic for Pr(D = 1 given D > 0), beta with logit link for the interior. Marginal mean assembled as `pi_1 + (1 - pi_0 - pi_1) * mu_beta` | R, `glmmTMB` | T1, T2 or T3 |
| **3** | `py_fractional_logit_gee` | **Fractional-response quasi-binomial GEE.** `statsmodels.GEE` with `family = Binomial()`, logit link, clustered on person, exchangeable working correlation, autoregressive with real time gaps where the implementation supports it. The Papke and Wooldridge quasi-MLE is consistent for the conditional mean with a `[0, 1]` response including both boundaries, with no transformation and no boundary handling. Being a marginal model, it needs no random-effect marginalization at all | **Python**, standard VM image | T1 or T2 |
| **4** | `py_linear_mixed_truncated` | **Linear mixed model on `D`** with a person random intercept, fitted values truncated to `[0, 1]` before integration, inference from the clustered bootstrap only. The truncation is reported | Python, `statsmodels.MixedLM` | T1 or T2 |
| **5** | `py_nonparametric_day_group_means` | **Nonparametric day-and-group means.** Weighted mean of `D` within procedure group and post-discharge day, using the observation weights of 3.7, summed over `d = 1..35`. No distributional assumption at all | Python, always available | None. This rung cannot fail, and it is the guaranteed floor of the ladder |

**Display labels for the five rungs**, printed wherever the rung reached is named: "Ordered beta
mixed model in R", "Zero-one-inflated beta mixed model in R", "Fractional-response quasi-binomial
estimating equations", "Linear mixed model with fitted values truncated to the unit interval",
"Nonparametric day and group means". `estimator.rung_slug` in `results.json` is a member of this
set and `estimator.rung_index` is its position in this table.

Two spellings are settled here because two documents drafted them differently. Rung 2 is
`r_zero_one_inflated_beta_glmm`, with the `glmm` suffix, in parallel with rung 1 and because the
rung genuinely carries random effects that a fixed-effect zero-one-inflated beta would not. Rung 3
is `py_fractional_logit_gee`, naming the **link**, because "fractional GEE" is ambiguous between a
logit and an identity link and an earlier draft of the export contract placed an identity-link GEE
at this rung. Naming the link closes that ambiguity permanently.

**Descent triggers, stated exactly.**

- **T0. Environment unavailable.** The R Analysis Environment cannot be created in the workspace, or
  `glmmTMB` of the required version cannot be installed in it. Controlled Tier blocks internet for
  batch jobs while keeping it for interactive tools, so package installation is an interactive
  operation that can fail. T0 skips rungs 1 and 2 together and lands on rung 3.
- **T1. Non-convergence.** The optimizer returns a non-zero convergence code, or the maximum
  absolute gradient exceeds `1e-3`, or the Hessian is not positive definite.
- **T2. Boundary estimate.** An estimated variance component is within `1e-4` of zero, or a fitted
  cutpoint, dispersion or correlation parameter sits at a boundary of its admissible range.
- **T3. Singular covariance.** The random-effect covariance matrix is singular, or carries an
  estimated correlation with `|r| > 0.99`.
- **T4. Bootstrap instability.** More than 25% of the clustered bootstrap resamples fail to
  converge. This is a property of the fitting process across resamples, not of any estimate, and it
  descends one rung. The failure rate is reported whatever it is.

**Because Phase 4 may therefore run R rather than Python**, the pipeline is written so that the R
leg consumes exactly the same person-day feature table emitted by `pipeline/04_features.py` and
writes exactly the same `results.json` schema. The language used is recorded in `results.json` and
named in the Methods. The choice between R and Python is settled by T0, which is an environment fact
established in Phase 1, before any count is seen.

### 3.6 Specification: splines, interactions, random effects, covariates

**Time basis.** A restricted cubic spline in post-discharge day with **five knots at days 2, 6, 12,
21 and 32**. The knots are fixed a priori, on a roughly logarithmic spacing, because postoperative
recovery curvature is concentrated in the first two weeks. They are **not** placed at data
quantiles. Quantile knots would make the basis depend on the observed day distribution, and although
that distribution is near-uniform by construction here, fixed knots remove even that dependence and
guarantee that every sensitivity row differs from the primary only in the thing it varies. For the
Figure 2 display window of post-discharge day 1 to 90, a separate display model uses **seven knots
at days 2, 6, 12, 21, 35, 55 and 80**.

**Mean structure of the primary model.**

```
D_id  ~  rcs(day_d) * fusion_i
       + region_i + rcs(day_d):region_i
       + fusion_i:region_i
       + dow(d)
       + age_i + sex_i + bmi_i + charlson_i + log1p(los_i) + year_i + covid_i + device_i
```

- `rcs(day) * fusion` gives each procedure class its own recovery shape.
- `rcs(day):region` lets cervical and lumbar recover on different shapes without forcing the fusion
  effect to differ by region.
- `fusion:region` is a constant interaction, present at collapse level 1 only. Its presence is
  exactly why the pooled contrast is defined by standardization (3.1, 3.8).
- `dow(d)` is a **7-level fixed effect for the calendar day of week** of post-discharge day `d`. See
  section 5.5 for why it is a fixed effect and not an assumption. The reference level is Wednesday,
  an arbitrary fixed choice that cannot affect the standardized marginal estimate.

**Covariate set, locked.**

| Covariate | Form |
|---|---|
| Age at index | Restricted cubic spline, 3 knots fixed at 45, 60 and 75 years |
| Sex assigned at birth | Factor: male, female, other or unknown |
| BMI | Nearest measurement within 365 days before index. Restricted cubic spline, 3 knots fixed at 22, 28 and 35 kg/m2. Missing handled by a missing indicator plus median substitution, the median computed inside the perimeter and never printed |
| Comorbidity burden | Charlson comorbidity index from ICD-10-CM condition records in the 365 days before index, Quan mapping, modelled as ordinal 0, 1, 2, 3 or more |
| Index length of stay | `log(1 + LOS)` in days |
| Calendar year | Index year, linear, plus a COVID-19 disruption indicator for index dates from 2020-03-01 through 2021-06-30 |
| Device class | Fitbit model family from the `device` table, assigned by the fixed rule below; unknown is its own level; any level whose episode count is not disclosable is folded into "other or unknown" before modelling |
| Day of week | 7-level factor, described above |

**Device class, and the model-family rule that closes the last free choice in this table.** "Model
family" was the one cell here an analyst could still decide after seeing the data, so the rule is
written down rather than left to runtime. The family is derived from the `device` table's model
string mechanically, with a fixed vocabulary and a determinate fallback:

1. Uppercase the model string, replace every character that is not a letter with a space, and take
   the **first token**.
2. If that token is one of the fourteen fixed family names below, the family is that name. Otherwise
   the family is **other or unknown**, as is a null or empty model string.
3. The fixed family vocabulary, in full: CHARGE, VERSA, SENSE, INSPIRE, LUXE, ALTA, IONIC, BLAZE,
   SURGE, FLEX, ONE, ZIP, ACE, ULTRA.
4. Generation is deliberately **not** distinguished: Charge 5 and Charge 6 are one level, as are
   Versa 2 and Versa 4. Generation is largely a proxy for calendar year, which is already in the
   model, and splitting on it would manufacture thin levels that rule 5 would immediately re-merge
   on the basis of observed counts, which is precisely the data-dependent choice this rule removes.
5. Only then does the folding rule apply: any level whose episode count is not disclosable folds
   into "other or unknown". Folding runs on a **count**, never on an estimate, and it happens once,
   on the Phase 3 attrition ladder, alongside the collapse-level decision of 2.5.

The rule is independent of the observed distribution by construction: it yields the same fourteen
candidate levels on a cohort of any size. Its failure mode is a model string this vocabulary does not
name, which lands in "other or unknown" and is reported as a share.

**Baseline steps `B_i` is deliberately not a covariate in the primary model.** The outcome is
already normalized by `B_i`, and conditioning on the denominator of the outcome changes what is
being estimated. Baseline steps enters in three prespecified places only: the companion endpoint
model (3.9), the baseline-floor sensitivity (3.10), and a supplementary baseline-adjusted row
(section 6). Fixed baseline bands, used for description and never as a model cutpoint, are under
3,000, 3,000 to 6,999, and 7,000 or more steps per day.

**Random effects.** Person random intercept plus random linear slope in post-discharge day,
unstructured 2 by 2 covariance, plus the continuous-time AR(1) residual of 3.4. The protocol takes
the first eligible episode per person, enforced and counted at rung 13 of the attrition ladder
(2.6), so person and episode coincide in the primary; the secondary analysis admitting later
operations reads the episodes dropped at that rung back in, nests episode within person, and keeps
person-clustered inference.

### 3.7 Weighting for observation

The daily-deficit model is fitted on observed person-days, weighted by the inverse probability that
the day was observed.

**The observation model.** A pooled logistic regression for `Pr(day d of episode i is analyzable)`,
with predictors: the post-discharge-day spline of 3.6, procedure group, region, day of week, the
full covariate set of 3.6, device class, the count of valid baseline days, and the **lagged** wear
fraction over post-discharge days `d-7` to `d-1`. The lag is strict: the observation model never
uses same-day or future information, so it cannot condition on the very day it is weighting.

**The weights.** `w_id = p_marginal / p_hat_id`, stabilized by the marginal observation probability,
and truncated at the 1st and 99th percentiles of the weight distribution. The truncation points, the
weight mean, and the weight range are reported.

**The assumption, stated plainly.** These weights make the primary estimator valid under
missing-at-random *given the observation model's conditioning set*. They do not make it valid under
arbitrary informative non-wear, and nothing can. That gap is what the delta-shift tipping point of
3.11 measures and reports as a number.

**One honesty note.** Lagged wear is a time-varying predictor of observation that is plausibly
affected by earlier deficit, which is the standard marginal-structural-model situation. Including it
is the right call because it is strongly predictive of observation, and a supplementary fit that
omits lagged wear from the weight model is reported so a reader can see how much the weights depend
on it.

**Where this model has no input at all.** The lagged wear fraction is defined only on the
post-discharge grid, so the Arm A adaptation of this model in 4.4 has a case where the predictor
does not exist rather than being missing. That case is closed in 4.4, with the rule, the two
rejected alternatives and the counts it obliges. It is not decided here and it is not left to the
keyboard.

### 3.8 The marginal estimate and its confidence interval

**g-computation.** For procedure group `g`:

```
psi_hat(g) = (1/n) * sum over episodes i of
                 sum over d = 1..35 of  E_hat[ D_id | G = g, X = X_i, day = d, dow_i(d) ]
```

where the inner conditional expectation is the Monte Carlo marginalized fitted deficit of 3.3, and
`X_i` holds each episode's own covariates and its own region and calendar day-of-week alignment. The
whole cohort is set to `g`; nobody is dropped; the region and covariate distribution standardized to
is the analytic cohort's own. The primary contrast is
`Delta_hat = psi_hat(fusion) - psi_hat(decompression)`.

**Inference: person-clustered nonparametric bootstrap.**

- **Resampling unit:** the person. Whole participants are drawn with replacement, carrying all of
  their person-days.
- **What is refit inside each resample:** everything downstream of the resample, including the
  observation model of 3.7, the deficit model, the Monte Carlo marginalization, and the
  g-computation. Refitting the weight model inside the bootstrap is what makes the interval account
  for the weights being estimated rather than known.
- **Resamples:** `B = 1,000` for the primary contrast, `B = 500` for each sensitivity row.
  `B = 1,000` places 25 resamples beyond each 95% percentile endpoint, which is the conventional
  minimum for a percentile interval; sensitivity rows are read for direction and overlap rather than
  for a reported P value, so 500 is adequate and the reduction is stated.
- **Seed:** resample `b` uses `numpy.random.default_rng([SEED, b])` with `SEED = 0`, so any single
  resample can be regenerated on its own. In R, `set.seed(0)` with the RNG kind pinned.
- **Interval:** the 2.5th and 97.5th percentiles of the resampled `Delta`. A resample whose model
  fails to converge is discarded and counted; the count is reported; trigger T4 of 3.5 applies if
  more than 25% fail.
- **P value, if one is printed at all:** twice the smaller resample tail proportion beyond zero,
  printed in house style as `P < 0.001` or `P = 0.223`. No P value in this plan selects a model, a
  window, a covariate, or a cutpoint.

**Reporting format.** Adjusted debt is printed in baseline-equivalent activity days lost to one
decimal with a 95% CI; the contrast likewise; absolute levels precede relative statements.

### 3.9 The companion endpoint on the absolute scale, in thousand steps lost

The normalized endpoint divides by `B_i` and is therefore sensitive to the baseline floor problem of
3.10. The companion endpoint is not.

```
TSL_i = sum over d = 1..35 of max(0, B_i - S_id) / 1000        thousand steps lost over the window
```

**No second model is needed for the arithmetic**, because `B_i * D_id = max(0, B_i - S_id)`
identically: the absolute shortfall is exactly the deficit multiplied by that episode's own
baseline. The absolute-scale marginal estimate is the same fitted daily deficit re-weighted by each
episode's own baseline **inside** the g-computation, before averaging, never after.

**One model change is required, and it is not optional.** Multiplying a baseline-independent fitted
deficit by an episode's baseline would impose the assumption that the deficit does not depend on the
baseline. The data can test that, so for the companion endpoint the daily-deficit model is refit
with a **restricted cubic spline in log baseline steps, 3 knots fixed at 3,000, 6,000 and 10,000
steps per day**, added to the mean structure. The fusion contrast on the absolute scale is then
obtained by the identical g-computation and clustered bootstrap. The companion endpoint is a
prespecified secondary and is not multiplicity-controlled.

### 3.10 The baseline floor

The normalized endpoint has a structural asymmetry that a reviewer will find immediately. A patient
whose baseline is 800 steps per day exceeds it on any day they leave the bedroom, so `D` floors at
zero and their debt is near zero almost by construction. A patient whose baseline is 14,000 steps
per day is nearly guaranteed a large debt for weeks after any operation. The measure is a ratio, and
a ratio with a tiny denominator is dominated by noise: at `B = 1,000`, one 250-step trip along a
hallway and back moves the day's ratio by 25 percentage points.

**Specified floor value: `B_i` at least 1,000 steps per day.**

**Justification.** 1,000 steps per day sits far below every published sedentary threshold, which
begin around 5,000 steps per day, so the floor does **not** exclude sedentary patients, who are a
population of interest and whose debt is a real quantity. It excludes only baselines so small that
the ratio is dominated by measurement granularity rather than by behaviour. The value is chosen for
that reason and is not tuned.

**Where it is applied.** The **primary applies no floor**, so that no patient is excluded on the
basis of how sedentary they were before surgery, and the direction of the resulting bias is stated
in the limitations. The floor is **sensitivity row 9** of section 6, restricting to `B_i` at least
1,000 steps per day. In addition, the correlation between `B_i` and `DRD_i` is reported, and
description by the fixed baseline bands of 3.6 goes to the supplement.

### 3.11 The delta-shift tipping point

This is the single best preemption of "your missingness is informative", because it converts an
unanswerable complaint into a reported number.

**Parameterisation.** On observed person-days the fitted model stands. On **missing** person-days,
as defined in 2.3, the counterfactual daily deficit is shifted on the model's own latent logit
scale:

```
logit( E[D_id | missing] )  =  logit( E_hat[D_id | X, day, group] )  +  delta
```

`delta = 0` is missing at random given the model and the weights, that is, the primary. `delta > 0`
means a missing day was worse than the comparable observed day the model would predict for it. The
whole g-computation is then rerun at each `delta` on the grid.

**Grid: `delta` in {0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0} log-odds**, applied three ways:

1. to the fusion group only,
2. to the decompression group only,
3. to both groups equally.

Applying it to **both** groups equally moves both arms and mostly cancels in the contrast, which is
itself informative and is plotted. The reported tipping point is driven by application 2,
**decompression only**, because that is the direction that works *against* the study hypothesis: it
makes the comparison group's unobserved days worse, shrinking the fusion-minus-decompression
difference toward and past zero.

**Two numbers are reported**, and they are the point of the exercise:

- the smallest `delta` at which the primary contrast's **point estimate** crosses zero;
- the smallest `delta` at which the **95% CI first includes** zero.

**Interpretability.** Each `delta` on the grid is printed beside the deficit it implies for a
reference day whose observed-equivalent deficit is 30%, so a reader can judge for themselves whether
the tipping `delta` describes a plausible world or an absurd one. The translation is computed, never
hand-typed.

**Prespecified extension rule.** If the contrast has not crossed zero at `delta = 2.0`, the grid
extends in 0.5 increments to `delta = 4.0` and **no further**. A shift of `delta = 4.0` is an odds
ratio of about 55 between a missing day and its observed twin, which is beyond any defensible
informative-missingness scenario. If the contrast has still not crossed, the reported answer is "no
tipping point within the prespecified range, which extends to delta = 4.0". Writing the extension
rule down now is what stops it from being an extension invented later.

### 3.12 Assumption-free Manski bounds

Reported in the **footer of Table 2**, for the primary contrast and for each group's level.

- **Lower bound.** Every missing day contributes zero deficit: the patient walked at or above
  baseline on every unobserved day. This is `DRD_naive` of 3.2.
- **Upper bound.** Every missing day contributes a full deficit of 1: the patient took no steps at
  all on every unobserved day.
- **Bounds on the contrast**, by interval arithmetic on a difference:
  `[ mean_fusion_low - mean_decomp_high , mean_fusion_high - mean_decomp_low ]`.
- Censored days, as distinct from missing days (2.3), are outside the window and are not bounded
  over. The bounds are computed on every eligible episode, not only on complete windows.

**These bounds will be wide, and they are reported anyway.** They will very likely span zero. They
are the only statement in the paper that survives with no assumption about missingness whatsoever,
and the honest structure of the argument is: the bounds say what is certain, the tipping point of
3.11 says how far the model would have to be wrong, and the point estimate says what the model
implies. A paper that prints only the third of those is a paper that has hidden the first two.

---

## 4. Arm A, the early-warning gate analysis: specified in full, run only at the permitted tier

Arm A is specified completely here so that the tier decision changes only **how far up the ladder
the analysis goes**, never **what the analysis is**.

### 4.1 Outcome

First **EHR-recorded post-discharge acute-care encounter** within 90 days: an emergency department
visit, or a new inpatient admission beginning after discharge from the index surgical encounter. An
ED visit followed by same-day admission collapses to one event. Admissions accompanied by a clearly
scheduled elective procedure on the admission date are excluded. The manuscript says "acute-care
encounter", never "unplanned readmission" and never "complication". The `visit_concept_id` values
for ED and inpatient are **enumerated against the CDR's actual distribution** before use, never
assumed.

Risk begins on the first complete calendar day after index discharge. Follow-up ends at the earliest
of: first acute-care encounter, repeat spine operation, death where reliably available, CDR
observation cutoff, or post-discharge day 90. **At least 30 postoperative Fitbit days are not
required**, because that restriction would create selection and immortal-time bias by excluding
early events and patients whose adherence declined during deterioration.

### 4.2 Exposure

For an encounter on date `E`, the primary landmark is `T = E - 3`, and the proximal step ratio is

```
R_72 = median( steps on E-5, E-4, E-3 ) / B_i
```

requiring **at least 2 valid wear days** among the eligible days of that 3-day window. The median is
the exact-median UDF, never `APPROX_QUANTILES(x, 2)[OFFSET(1)]`, which returns the upper value on an
even-length array and would bias every two-day proximal window upward.

`R_72` enters as a **restricted cubic spline with 3 knots fixed at `R` = 0.4, 0.7 and 1.0**, and the
interpretable effect is reported per **20-percentage-point lower ratio**. Categories of less than
40%, 40% to 59%, 60% to 79%, and at least 80% of baseline may be displayed but never replace the
continuous analysis. A secondary 24-hour landmark uses days `E-3` through `E-1`; a secondary 7-day
horizon is prespecified and reported only at tier 1 or 2.

### 4.3 The first eligible landmark, named explicitly

The exposure window must lie on post-discharge days, and post-discharge day 1 is the first complete
day after discharge (2.3). That single requirement structurally deletes the earliest and most severe
events, and it deletes them **silently** unless the deletion is named, because an event with no
computable landmark simply never appears in an event-level analysis file.

| Event on post-discharge day `E` | Window `E-5` to `E-3` | Days in the window that are post-discharge | Computable under the 2-valid-day rule |
|---|---|---|---|
| 1 | -4 to -2 | none | no |
| 2 | -3 to -1 | none | no |
| 3 | -2 to 0 | none | no |
| 4 | -1 to 1 | day 1 only | no, one eligible day |
| **5** | **0 to 2** | **days 1 and 2** | **yes, if both are valid wear days** |
| 6 | 1 to 3 | days 1, 2 and 3 | yes, and the first fully post-discharge window |

**The first eligible landmark is post-discharge day 2, belonging to an event on post-discharge day
5.** The first *fully* post-discharge exposure window belongs to an event on post-discharge day 6.
**Events on post-discharge days 1 to 4 are structurally uncomputable.** They are not a missing-data
problem; they are a definitional one.

Three consequences are written into the analysis:

1. **They get their own attrition rung**, `excl_event_without_computable_landmark`, rung 18 of the
   ladder in 2.6, whose printed reason display is "Event on post-discharge day 1 to 4, with no
   computable proximal window". It appears in the ladder and in Figure 1 and is never folded into a
   generic "insufficient wearable data" row. **Day 1 to 4 is the derived range, not day 1 to 3**;
   the six-row derivation is the table above and any document writing day 1 to 3 is corrected
   against it.
2. **Their timing is reported**, as the distribution of event day among deleted events, subject to
   the disclosure floor: if the count is not disclosable the row prints as suppressed, and the fact
   of the row still prints.
3. **A prespecified partial-window secondary** admits events on post-discharge day 4 using the
   single eligible day 1, labelled separately and never pooled with the primary.

This matters beyond bookkeeping: the deleted events are the earliest ones, and earliest is a proxy
for most severe. A reader is told that the analysis is blind to the first 4 days by construction,
and how many events that cost.

### 4.4 Requiring wear at the landmark conditions on a collider

Wear is plausibly caused both by declining activity and by the illness that generates the outcome.
Requiring a computable ratio at the landmark therefore deletes preferentially the sickest windows,
and conditioning on a common consequence of exposure and outcome is collider stratification. Three
fixes, all prespecified:

1. **"No computable step signal" is promoted to a co-primary exposure**, so those windows stay in
   the risk set instead of vanishing. `N` is defined **only on a landmark window that holds at
   least 2 post-discharge days**, and on such a window `N = 1` when fewer than 2 of those days are
   valid wear days. A window holding fewer than 2 post-discharge days carries **no** `N` at all:
   that is the **definitional** condition, it sits outside this exposure, and the rule for it is
   below. The model is

   ```
   logit(risk) = alpha + beta_N * N + f(R) * (1 - N) + covariates
   ```

   where `f` is the spline of 4.2. `beta_N` is itself an estimand of interest and answers the
   protocol's own question, whether loss of data precedes utilization.
2. **Inverse-probability-of-observation weighting**, using the observation model of 3.7 adapted to
   the landmark, as a sensitivity. That adaptation has one case where its main predictor has no
   input at all, and the rule for it is prespecified below rather than discovered at the keyboard.
3. **The outcome rate in windows with versus without a computable ratio is reported**, subject to
   the disclosure floor. This is the direct evidence for or against the collider concern and it
   costs nothing. It is computed on the **full-cohort day-indexed landmark panel** specified below,
   not at the sampled risk sets and not among first events.

**The landmark weight model, and the one place it has no input.** Fix 2 reweights each risk-set
member by the inverse probability that its own landmark window was computable, using the model of
3.7 with the member's own landmark day in place of the accrual day. One predictor in that model is
the **lagged wear fraction over days `T-7` to `T-1`**, and it is the predictor carrying most of the
model's information. It exists only on the post-discharge grid: `drd_daily` begins at post-discharge
day 1, so the column is null at `T = 1`, where no prior post-discharge day exists to average, and
does not exist at all at a `T` of 0 or less. A member's landmark day is its own post-discharge day
minus 3. Although 4.3 puts every **case** in the primary at post-discharge day 5 or later and
therefore at `T` of 2 or more, two routes put members at `T` of 1 or less:

- **the day-of-week relaxation of 4.7**, whose rungs 2 and 3 admit a control at a post-discharge day
  up to 2 days below the case's, so a control matched to a case at post-discharge day 5 may sit at
  day 3 and carry a landmark at day 0; and
- **the partial-window secondary of 4.3**, which admits events on post-discharge day 4 and therefore
  cases at `T = 1`.

The rule is undefined for exactly those members, and they are the earliest ones, which by the
argument of 4.3 makes them a proxy for the sickest.

**The rule.** A member is weighted when its own landmark day `T` is **2 or more**, and the lagged
wear fraction is read from `drd_daily` at day `T` as it stands, partial or complete. The window
behind it holds `min(T - 1, 7)` post-discharge days, which is a deterministic function of `T` and is
therefore already absorbed by the post-discharge-day spline the weight model carries. It is **not**
entered a second time as a covariate: a term that is a function of a term already in the model is
not additional information, and it would destabilise the fit at exactly the days holding the fewest
members. A member whose landmark day is **1 or less** has no weight at all, because the predictor
the weight model runs on does not exist there. Under the rule below such a member has already left
the exposure model for a prior and different reason, so in the primary the weight rule has nothing
left to exclude; where a member at such a landmark is deliberately read back in, which is route (b)
below, the weight rule stands and that member is **excluded from the weighted sensitivity and from
nothing else**.

**A landmark day of 1 or less is the definitional condition itself, and that is arithmetic rather
than a threshold.** The landmark is `T = E - 3` and the window is `T-2` to `T`, so the window's
post-discharge days are the days of `T-2` to `T` that are 1 or greater, and that count reaches 2
exactly when `T` is 2 or more. `T = 1` leaves the single day 1; a `T` of 0 or less leaves none. **A
landmark day of 1 or less is therefore not a rule of its own. It is the definitional condition of
the table below, written in landmark-day terms.** Such a member has no exposure window at all, so it
carries **no** `N`, it contributes nothing to `beta_N`, and it is outside the co-primary exposure
**on every surface**: the conditional model of 4.5, the complementary discrete-time model of 4.6,
the `landmark_daily` panel of fix 3, and the `risk_sets` table that `pipeline/build_all.sql` builds
and both models read. A surface that sets its no-computable-signal indicator from valid days alone,
with no structural filter, admits the definitional condition into the data condition, and under the
header rule that surface is corrected against this paragraph rather than this paragraph against it.

**Why it has to be outside, in the terms of the collider argument this section is about.** `N`
exists to capture one thing: **sick people who stopped wearing the device**. A window that is
uncomputable because it straddles discharge is uncomputable for **calendar** reasons that have
nothing to do with the participant's illness or with anything the participant did, and it is a
deterministic function of post-discharge day, which is already the single time scale of this design
and is already conditioned on by the risk-set sampling of 4.5 and the matching of 4.7. Folding it
into `N` would contaminate the exposure with a quantity the design has already handled, and it would
do so in the direction that matters, because the members it adds are the earliest ones: `beta_N`
would carry a calendar artefact inside the coefficient that exists to measure informative non-wear.
A fix to a collider that reintroduces the collider through its own exposure is worse than no fix,
because it looks like a correction.

**The two routes, and which of them the earlier wording got wrong.** Route (b), the partial-window
secondary of 4.3, is **self-consistent and is unaffected**. It admits events at a landmark day of 1
deliberately, reads them back in under its own single-eligible-day rule, labels them separately and
never pools them with the primary, so nothing there is being smuggled into `N`. Route (a) is the one
at issue. The day-of-week relaxation of 4.7 can put a **control** in the **primary** at
post-discharge day 3 or 4, therefore at a landmark day of 0 or 1, and such a control has no exposure
window to contribute. **It is dropped from its risk set as a member, and counted.** It does not
leave at rung 18: rung 18 is an **event** rung and a sampled control is not an event, so this is a
member-level drop inside Arm A, counted here because the ladder cannot count it. A matched set that
loses every control this way contributes nothing to a conditional likelihood and leaves it
altogether, which is count 2 below.

**Why not the other two options, recorded so that the choice is not reopened later as a preference.**

- *Carry the lagged wear fraction back onto the preoperative grid, so that it is defined
  everywhere.* **Rejected.** The days it would be carried back onto are not the same process. For a
  landmark at `T` of 0 or less the window `T-7` to `T-1` lies inside the index admission, inside the
  final preoperative week, or across both. The final preoperative week is the window this plan
  already excludes from the baseline, in 2.2, on the stated grounds that pain flares, preoperative
  testing, travel and preoperative instructions alter activity; and wear during an inpatient stay is
  a property of the ward and of who fastened the device, not of the participant's adherence.
  Splicing three regimes into one predictor gives the weight model a number where it currently has
  none. That reads as closing the gap and is in fact fabricating an input: the column would be
  defined and wrong, which is worse than undefined and honest.
- *Give those members the marginal weight.* **Rejected**, and it is the closer call of the two.
  Setting the stabilized weight to its marginal value where the model has no input asserts that a
  member whose landmark precedes the first post-discharge day has the observation probability of the
  average member. Those are the earliest members in the study, and 4.3 argues at length that
  earliest is a proxy for most severe, so the assertion is not merely unsupported, it is unsupported
  in the one direction that would flatter the result. Its second defect is worse than its first: a
  weight of 1 is indistinguishable in every output from a weight of 1 that was estimated, so the
  assumption would be invisible to every reader of every exhibit. The option this plan takes has the
  opposite property. Its whole cost is a count, and the count is printed.

**The counts these two rules oblige, because a count is what tells a reader how much of the
analysis they touched.** All three are counts and never estimates, all are subject to the disclosure
floor of section 8, and all are reported whether or not the weighted sensitivity moves the estimate:

1. **Members with a landmark day of 1 or less**, split into cases and controls, and split again by
   which of the two routes above put them there. This one count serves the member-level drop and the
   weight rule alike, because the two bite the same members for two different reasons, and it is
   reported once rather than twice under two labels a reader would try to add together.
2. **Matched sets that lose every control** and therefore leave the conditional likelihood
   altogether, since a set with no control contributes nothing to a conditional logistic fit. This
   is the count that turns a member-level exclusion into an analysis-level one, and it cannot be
   recovered from count 1.
3. **The weighted sensitivity's own denominator**, in sets and in members, printed beside the
   primary's, under the rule of 9.2 that a row fitted on a subset prints its own `n`.

**Fix 3 is computed on the full-cohort day-indexed panel, and that changes what it means.** The
panel is `landmark_daily`: **one row per analytic episode per post-discharge day**, carrying, for
the window ending three days earlier, the count of valid wear days inside it, the two landmark
conditions below as separate flags, and an indicator for whether an acute-care event occurred on
that day. It is a three-day-offset self-join of `drd_daily` over the same episodes and the same
days, so it introduces no eligibility rule of its own and cannot disagree with the cohort.

**Why not at the risk sets, which is the only other place the comparison is available.** Risk-set
membership is not a sample of episode-days; it is the output of the sampling rules of 4.5 and the
matching rules of 4.7, and both of them select on the variable the comparison is about. The cap of 3
control landmarks per participant removes the participants who would contribute the most days, who
are the best-observed ones; up to 5 controls per case fixes a ratio rather than measuring a rate;
and the day-of-week matching of 4.7, with its relaxation rungs, selects landmarks on the calendar,
which is one of the things determining whether a window is computable at all. A with-versus-without
comparison computed there compares windows that already survived the selection the comparison exists
to expose, which is the collider again, one level up. The other available surface, first events
among episodes that had one, conditions on having an event and on it being the first, which is
selection on the outcome. Neither surface is fit for this purpose, and the panel exists because
neither is.

**What the full-cohort version buys, and what it costs.** It buys a real denominator. Every episode
day at risk is in it, whether or not that participant was ever sampled into a risk set and whether
or not they ever had an event, so the quantity becomes an **event rate per episode day** within each
of the two conditions rather than a ratio inside a selected set, and the two conditions sit on a
common base. What it costs is that the comparison is **unmatched and descriptive**: post-discharge
day drives both wear and events, and the panel controls for nothing. The comparison is therefore
reported **twice**, crude and directly standardized to the post-discharge-day distribution of the
analytic cohort, with the standardization weights fixed by that distribution and by nothing else. If
the two agree, post-discharge day is not doing the work; if they disagree, the reader is shown by
how much rather than told which to believe. Neither version is a causal estimate and neither is
labelled one. This is the evidence for or against the collider concern; the correction for it is fix
1.

**The strata that standardization runs over, and why a single day cannot be one of them.** The
strata are the six recovery day bands below. They are **not** single days, and the reason is
disclosure rather than statistics. Direct standardization over the day grid is a weighted average of
**per-day event counts**, and on a cohort of this size every one of those per-day counts sits at or
below the floor of rule 1 of section 8. A figure assembled out of them carries them inside it. It is
a number no reader can reproduce from anything printed beside it, and it is a number that discloses
in aggregate exactly the cells the floor exists to withhold, which makes it either unpublishable or
publishable only by giving up the rule. The day grid is therefore not an admissible stratification
for this quantity at any cohort size this study can reach, and no run-time check rescues it, because
the defect is in how the quantity is built rather than in what a particular run happens to return. A
reader who asks why this comparison is standardized coarsely is owed that answer and not an appeal
to smoothing, to stability, or to the width of an interval, so it is written here in those terms.

**The six recovery day bands, fixed a priori.** The standardization runs over these six strata and
over no others. The first five are the accrual window of post-discharge days 1 to 35 in calendar
weeks and the sixth is the display tail of Figure 2, so the partition reads as recovery time rather
than as a cut chosen to make cells clear the floor. They are fixed before any count from this study
exists, they are the same six bands `pipeline/04_features.py` already reports its person-day tables
over, and they do not move in response to what a run returns. A partition that could still be
widened after a suppression was seen would be a choice made after seeing counts, which is the class
of decision this document exists to remove.

| Band | Post-discharge days | Display label |
|---|---|---|
| 1 | 1 to 7 | Days 1–7 |
| 2 | 8 to 14 | Days 8–14 |
| 3 | 15 to 21 | Days 15–21 |
| 4 | 22 to 28 | Days 22–28 |
| 5 | 29 to 35 | Days 29–35 |
| 6 | 36 to 90 | Days 36–90 |

**This table is not a sixth owned vocabulary.** The bands carry a display label and **no slug**.
Nothing keys on them, no exported row is identified by them, and the set-equality assertion in
`local/verify.py` runs against the five vocabularies named in the header and not against this table.
The display labels above are printed strings governed by character equality, like every other
display label in this file.

**The suppression rule, and what survives it.** The standardized rate for a condition is produced
only when **every band contributing days to that condition** carries a disclosable event count under
section 8. If any contributing band falls below the floor, the standardized rate for that condition
is **withheld**, and the standardized rate ratio is withheld with it, since it cannot be formed
without both. The two conditions are judged **separately**: one may be standardized while the other
is withheld, and the exhibit shows exactly that rather than suppressing both so that the row looks
uniform. A band contributing **no** days to a condition is not a suppression event. It is dropped,
the remaining band weights are renormalized over the bands that do contribute, and the share of the
cohort's episode days those bands cover is reported beside the rate, so that the renormalization is
visible rather than silent.

**What is reported when the standardized figure is withheld.** The **crude comparison is reported
alone**, with its own two denominators, and the exhibit states in words that the standardization was
withheld and why. It is not replaced by a finer stratification, it is not replaced by a model-based
adjustment, and the row is not dropped: a with-versus-without comparison that vanished when it
became inconvenient would be worse evidence than a crude one, and this comparison exists to be
checked rather than to be believed. What changes is the sentence the exhibit is allowed to make. The
crude rates and their ratio are reported, and **no claim is made about how much of the difference
post-discharge day explains**, because the quantity that would support such a claim was not
published.

**Every rate in this comparison is computed from the rounded numerator over the rounded
denominator**, which is rule 4 of section 8 applied to a rate for the same reason it is applied to a
percentage, and a rate is not produced at all when its numerator is not disclosable. A rate computed
from a true numerator and printed beside a rounded denominator lets a reader multiply the two and
recover the hidden count, which is the leak the rounding exists to close. Computing from the rounded
pair also makes every printed rate reproducible from the two counts printed beside it, which is the
first thing a careful reader checks.

**The two landmark conditions stay distinct on the panel, as they are everywhere else in this plan.**
They are different objects, and merging them would silently delete the windows the collider
correction exists to keep:

| Condition | Definition | Where it goes |
|---|---|---|
| **Data** | The window holds at least 2 post-discharge days, but fewer than 2 of them are valid wear days | **Stays in the risk set.** It is `N = 1`, the co-primary exposure of fix 1, and it is the "without a computable ratio" side of this comparison |
| **Definitional** | The window holds fewer than 2 post-discharge days at all, equivalently a landmark day of 1 or less, which for an event is exactly post-discharge day 1 to 4 (4.3) and for a sampled control is post-discharge day 3 or 4 | **Leaves, and carries no `N` anywhere.** An event leaves at rung 18 of the ladder of 2.6, `excl_event_without_computable_landmark`. A sampled control is not an event and cannot leave at rung 18, so it is dropped from its risk set as a member and counted above |

The panel carries the two as separate columns and **their counts are never summed**, on the panel,
in `pipeline/build_all.sql`, in `pipeline/04_features.py`, in `pipeline/06_analysis_gate.py`, or in
any exhibit. The same holds of the `risk_sets` table, whose no-computable-signal column carries the
data condition and the data condition only. A single "no computable landmark" number would be the
sum of a data condition that is an exposure and a definitional condition that is an exclusion, and
no reader could take it apart again afterwards.

**The panel's three day classes partition it, and the partition is what the standardization weights
rest on.** Every episode day on the panel is in exactly one of three classes: a computable window,
the data condition, or the definitional condition. `pipeline/06_analysis_gate.py` asserts that the
three day counts sum to the panel's own day count before it standardizes anything, and halts if they
do not, because band weights taken from the panel's day distribution describe a base the three
classes have to cover exactly. That assert is a check on the partition and is **not** a licence to
add the classes together in an exhibit; it is the one place in this plan where the three are
arithmetically related, and it is an internal consistency check that produces no published number.

**The comparison is drawn between the computable condition and the data condition, and between those
two only.** The definitional count is printed beside the comparison rather than inside it, so that a
reader can see it is excluded rather than folded in, and it is never added to the row above it.
Folding it in would put an exclusion inside an exposure: those are events on post-discharge day 1 to
4, which have no exposure window at all and leave at rung 18, while the data condition is the
co-primary exposure of fix 1 and stays. The same separation holds for the counts, for the rates and
for the denominators, and there is no number anywhere in this plan that is the two of them together.

### 4.5 Risk-set control sampling, fully specified

Under-specified risk-set sampling biases away from the null, chiefly by sampling controls only from
participants who never have an event, which conditions the control pool on the future. Every degree
of freedom is closed here:

- **Sample from the risk set at the case's post-discharge day.** Eligible controls are participants
  still at risk and encounter-free through the corresponding 3-calendar-day horizon at that
  post-discharge day.
- **A participant may be a control at one landmark and a case later.** Future case status does not
  disqualify a participant from being sampled as a control before their event. Excluding
  never-event participants only would break the design and is forbidden.
- **Post-discharge day is the single time scale.** Not calendar time, not time since enrollment.
- **Calendar year is a covariate, not a matching factor.** Matching on it would shrink risk sets for
  no confounding gain, since post-discharge day already carries the recovery-stage confounding that
  risk-set sampling exists to handle.
- **Up to 5 controls per case.**
- **Cap on any one participant's control contributions: 3 control landmarks across the whole
  study.** Without a cap, a small cohort's few long-observed participants dominate the control pool
  and the effective sample size collapses far below the nominal one.
- **Sampling is seeded `FARM_FINGERPRINT`, never `RAND()`**, with `SEED = 0`, so a resumed session
  reproduces identical matched sets.
- **Inference is person-clustered.** Conditional logistic regression assumes independent matched
  sets, and a participant appearing in several sets breaks that assumption. The primary odds ratio
  carries a person-clustered robust variance, and a person-level cluster bootstrap of `B = 1,000`
  resamples with the seed convention of 3.8 is reported alongside it. Where the two disagree, the
  bootstrap interval is the one reported.

### 4.6 Adjustment and absolute risks

Adjust for age, sex assigned at birth, baseline BMI, **baseline steps**, comorbidity burden, index
length of stay, calendar year, and device class. Baseline steps **is** a covariate here, unlike Arm B
(3.6), because the exposure is a ratio whose denominator is the baseline, and adjusting for the
denominator of an exposure is standard rather than circular.

Absolute risks at clinically representative ratios come from a **complementary full-cohort
discrete-time model**, a pooled logistic regression on person-days with the post-discharge-day
spline of 3.6 and person-clustered inference, never from the conditional model, whose matched-set
intercepts are conditioned out. Absolute risks are printed before relative ones.

### 4.7 Day of week enters Arm A as a matching factor

See 5.5 for the reasoning. The matching rule is hierarchical with a **prespecified relaxation
order**, because matching on both post-discharge day within 2 days and exact day of week is
over-constrained: day of week repeats every 7 days, so both can hold simultaneously only at an
offset of exactly 0.

1. **Same post-discharge day and same day of week.**
2. If that yields fewer than 2 eligible controls, relax to **post-discharge day within 2 days and
   the same weekday-versus-weekend class**, where weekend is Saturday and Sunday.
3. If that still yields fewer than 2 eligible controls, relax to **post-discharge day within 2 days
   with no day-of-week restriction**, and carry a day-of-week fixed effect in the conditional model
   for that set, reduced to the weekend indicator when the set is thin.

The rung used by each matched set is recorded and the distribution across rungs is reported. This
relaxation depends only on **risk-set size**, which is a count, never on any outcome or estimate.

### 4.8 What each tier runs

- **Tier 3, 20 to 49 events.** Event-centered description and visualization only: median
  baseline-normalized steps from day `E-14` through `E+7` for cases against post-discharge-day
  matched controls, with the wear fraction over the same window, plus the unadjusted association
  between `R_72` and the outcome. No model is presented as a prediction tool, no discrimination
  metric is computed, no alert burden is computed.
- **Tier 2, 50 to 99 events.** The above plus the **step-first model**: the clinical-time covariate
  set (post-discharge day spline, procedure class, age, sex, comorbidity burden, baseline steps,
  index length of stay) plus exactly three prespecified step features and nothing else: `R_72`;
  **local step deterioration**, the log ratio of the proximal 3-day median to the reference 7-day
  median over days `E-12` to `E-6`; and **wear fraction**, observed heart-rate minutes divided by
  1,440 together with the count of missing days. Validation is optimism-corrected clustered
  bootstrap with participant-grouped resampling, so no participant appears in both a training and a
  validation fold. Labelled exploratory throughout.
- **Tier 1, 100 or more events.** The above plus internal validation, with temporal validation
  substituted when the later surgical era holds at least 40 events, plus the full performance panel:
  area under the precision-recall curve, Brier score, calibration intercept and slope, sensitivity,
  specificity, positive and negative predictive value, alerts per 100 patient-days, false alerts per
  detected encounter, number needed to contact at a threshold targeting 80% sensitivity, and median
  lead time. AUROC is reported but is never the headline. The multidomain model adding nocturnal
  heart rate and sleep runs **only** at tier 1 **and** only with explicit human approval of the
  dry-run byte estimate for the minute-level query.
- **Tier 4, fewer than 20 events.** Nothing above runs. The gate is reported with the count
  suppressed. Note that the tier band and the disclosure band are not the same band: an event count
  of exactly 20 is **tier 3**, so the tier 3 analysis runs, and is simultaneously unprintable under
  section 8. See 1.3, where the collision and its Methods sentence are set out.

**Negative control, at tier 2 or 1.** Repeat the primary association using the window `E-14` to
`E-8`, among events occurring after post-discharge day 15. A signal there, remote from the event,
argues that the proximal finding reflects a chronic gradient rather than a proximal deterioration.

### 4.9 The coefficient ceiling that refuses a separated fit

**What this closes.** Conditional logistic regression on a thin matched design with a strong exposure
can **separate**: the likelihood becomes monotone in a coefficient, the maximum lies at infinity, and
the fit reports whatever value the optimizer happened to stop at. **Perfect** separation is already
caught, because the fit does not converge and the row is reported as not estimable. **Quasi-separation
is not caught, and quasi-separation is the common case.** The likelihood flattens while the
coefficient keeps growing, the relative-log-likelihood criterion declares the fit converged, and an
odds ratio in the thousands is exported beside an interval whose upper end is a property of the
stopping rule rather than a bound on anything. Tier 3, 20 to 49 events, is the tier this design most
plausibly reaches (1.3, 1.4, 9.4), and a thin matched design with a strong exposure is precisely
where this lives.

**The constant, and what it binds.** `MAX_ABS_COEFFICIENT = 10`. **A fit is refused when any one of
its coefficients has an absolute value greater than 10**, which on the odds-ratio scale is about
22,000. It binds every logistic fit in Arm A: the conditional model of 4.5, each of that model's
bootstrap resamples, and the complementary full-cohort discrete-time model of 4.6 from which the
absolute risks come. The refusal is at the level of the **fit** and not of the single coefficient,
because a coefficient at the ceiling means the information matrix is near-degenerate and no standard
error from that fit is trustworthy, including the ones on coefficients that look ordinary.

**Why ten, and why it was not tuned to the case that prompted it.** Ten on the log-odds scale is the
conventional separation-detection threshold in the logistic-regression literature and is the value
implementations use to warn that a fit may be separated. It is generous enough not to refuse a
plausible real effect: an odds ratio of 22,000 for a 20-percentage-point lower step ratio is not a
finding this design could produce, and nothing on the covariate list of 4.6 can produce one either.
It is tight enough that a runaway fit cannot reach an exported surface. **The constant was
deliberately not set to the smallest value that would have caught the fit that prompted it.** The
review that prompted this rule demonstrated the failure on a **synthetic** near-separated matched
design, built for the demonstration and carrying no data from this study, whose coefficient sat at
8.961, below this ceiling; a fit like that one still prints. A threshold chosen to catch the single
example that prompted it would be a threshold fitted to one draw, which is the class of choice this
document exists to remove. What the ceiling buys is a **bound on what can be exported**, not a
promise that every wide interval disappears: a fit below the ceiling with a very wide interval still
prints, and the width of that interval is the reader's signal.

**What a refusal returns.** Not a clipped number. The row prints **"not estimable (separation)"**,
slug `not_estimable_separation`, and the point estimate, the interval, and every quantity derived
from that fit are absent with that reason attached. **Clipping is forbidden.** Printing the odds
ratio at the ceiling, or printing it as "greater than 22,000", would put a number this study did not
estimate where a refusal belongs, and no reader could tell it apart from a fit that really landed
there. For the same reason **the value that tripped the ceiling is not printed**, not as a bound and
not in a footnote, because printing it is the clipped number arriving by a second route.

**This rule can only suppress, and it can never publish.** The ceiling has exactly one action, which
is to replace a number with a refusal. It has no branch that emits an estimate, no branch that
changes an estimate's value, and no branch that widens or narrows an interval, so it cannot move any
published number toward the null or away from it. A reviewer asking whether a prespecified constant
could have manufactured a result can check that property directly rather than take it on trust: the
rule's only output is an absence carrying a named reason, and an absence is not a finding. Its whole
cost is a count, and the count is printed.

**The point fit and the bootstrap resamples are both checked, and the consequence differs.** A
resample that separates while the point fit does not is a different situation from a separated point
fit, so it is decided here rather than left to the module to decide later.

1. **The point fit.** If any coefficient of the point fit is above the ceiling, the fit is refused as
   above. No interval is formed, because there is no point estimate to put one around.
2. **A bootstrap resample.** A resample above the ceiling is **retained in the resample distribution
   and counted. It is not discarded.** Discarding the resamples that ran furthest from zero would
   trim exactly the tail the percentile interval of 3.8 is read from, and would therefore **narrow a
   published interval**, which is the one thing this rule must never do. This is a deliberate
   departure from the resample rule of 3.8, where a resample whose model fails to converge is
   discarded and counted, and the departure is written down rather than left to be noticed: a
   non-converged resample produced no number to keep, a separated resample produced a number that is
   too large, and the two are not the same event.
3. **The share.** If **more than 25%** of the resamples are above the ceiling, the interval **and**
   the point estimate are both refused with the same reason, even where the point fit itself is
   below it. An interval read off a resample distribution that separated in a quarter of its draws
   is not an interval on the quantity the row claims to report. **25% is not a new constant.** It is
   the share 3.8 already uses for resample failure and trigger T4 of 3.5 already uses for bootstrap
   instability, and reusing it rather than inventing a second one keeps one number in this document
   where two would invite a later argument about which of them applies.

**The counts this obliges.** Both are counts and never estimates, both are subject to the disclosure
floor of section 8, and both are reported whether or not the ceiling ever fires, because a rule that
prints nothing when it does not fire is a rule a reader cannot confirm ran at all:

1. **Fits refused at the ceiling**, by analysis slug, so a reader can see which rows are absent for
   this reason rather than for cell size, for convergence, or for the tier reached.
2. **Resamples above the ceiling**, out of `B`, for every fit that produced an interval, so a reader
   can see how close an interval that did print came to the share that would have withheld it.

**The slug is not this file's to own.** `not_estimable_separation` belongs to the suppression-reason
vocabulary of `prespecification/EXPORT-CONTRACT.md` section 7.5, beside `not_estimable_cell_size`,
`not_estimable_convergence` and `not_estimable_data_unavailable`, and it is added there in the same
commit. It is **not** a member of any of the five vocabularies this file owns, so the set-equality
assertions of the header and of stop condition 8 are untouched by it. No existing reason could have
carried a separated fit: it did not fail on cell size, no data were unavailable, the tier permitted
the analysis, and **it converged**, which is exactly the property that makes quasi-separation
dangerous and is why `not_estimable_convergence` would have been a false sentence rather than a
near-enough one.

---

## 5. The five protocol problems, and the handling of each

### 5.1 The accrual window collides with length of stay, and the collision is confounded with the primary contrast

**The problem.** The protocol accrues recovery debt over postoperative days 8 to 42. That window is
fixed; length of stay is not. A decompression patient discharged on postoperative day 1 spends all
35 of those days at home. A fusion patient with a 12-day stay spends postoperative days 8 through 12
**as an inpatient**, at near-zero steps, and contributes only 30 ambulatory days. Inpatient days
score close to the maximum daily deficit for a reason that has nothing to do with recovery: the
patient is in a hospital bed. Debt is therefore mechanically inflated in the longer-stay group, and
the longer-stay group **is** the fusion group. The bias runs in the same direction as the
hypothesis, which is the worst possible arrangement.

**The resolution, decided by the human before the lock.** The window is **discharge-anchored,
post-discharge day 1 to 35**. Every patient contributes 35 comparable ambulatory days regardless of
length of stay, and the fusion-versus-decompression contrast measures recovery rather than length of
stay. The protocol's postoperative day 8 to 42 window becomes the **first main-text sensitivity
row** (section 6, row 1), computed with the identical estimator so the two are directly comparable.
Recorded in `decisions/2026-08-25-recovery-debt-window.md`.

**Why adjusting for length of stay does not repair this.** Three reasons, each sufficient on its
own.

1. **It is not a confounding problem, it is a definitional one.** Length of stay does not merely
   associate with the outcome; it changes **which days each patient contributes to the outcome**.
   Under a fixed postoperative-day window, the outcome variable is literally computed over different
   settings of care for different patients. A covariate cannot repair a term that appears inside the
   definition of the dependent variable. Regression adjustment removes the part of an association
   that is *explained by* a covariate; it does not restore days that were never ambulatory.
2. **Length of stay is post-treatment.** It is a downstream consequence of the operation, so
   conditioning on it blocks part of the very effect being estimated. The adjusted estimate answers
   a question nobody asked: the fusion-versus-decompression difference *among patients with the same
   length of stay*, in a comparison where length of stay is one of the main things the operation
   changes.
3. **The residual mismatch survives adjustment anyway.** Even at a fixed length of stay, the number
   and the position of inpatient days inside the window differ across patients, so the window
   mismatch is not a scalar that a single coefficient can absorb.

**What the resolution costs**, stated in the paper: the two groups are then compared at different
postoperative ages. A fusion patient with a 12-day stay contributes postoperative days 13 to 47,
while a decompression patient discharged on day 1 contributes postoperative days 2 to 36. The
discharge-anchored window trades **postoperative-time comparability** for **ambulatory-exposure
comparability**. This study chooses the second, because the question is how much home recovery is
lost, and the sensitivity row recovers the first for any reader who prefers it.

### 5.2 The earliest and most severe acute-care events are structurally deleted

Handled in full in 4.3: the first eligible landmark is post-discharge day 2 for an event on
post-discharge day 5, events on post-discharge days 1 to 4 are structurally uncomputable, they carry
their own attrition row rather than a generic wearable-data row, their timing is reported subject to
the disclosure floor, and a prespecified partial-window secondary admits day 4 events separately.

### 5.3 Requiring wear at the landmark conditions on a collider

Handled in full in 4.4: "no computable step signal" is promoted to a co-primary exposure with its
own coefficient, inverse-probability-of-observation weighting is added as a sensitivity, and the
outcome rate in windows with versus without a computable ratio is reported. Three details of that
handling are prespecified in 4.4 rather than left to the analysis, because each is a place where the
fix could have quietly reintroduced the bias it exists to remove. The **definitional** condition, a
landmark day of 1 or less, sits **outside** the co-primary exposure on every surface: such a window
is uncomputable by the calendar rather than because anyone stopped wearing a device, so admitting it
would put a deterministic function of post-discharge day, which the design already conditions on,
inside the exposure that exists to measure informative non-wear. The weight of the second fix is
undefined for a member whose landmark precedes the first post-discharge day, and those members are
the earliest ones: the rule excludes them from the weighted sensitivity and from nothing else, and
three counts are reported. The comparison of the third fix is computed on the **full-cohort
day-indexed landmark panel** rather than at the sampled risk sets, because
risk-set membership is itself selected on wear and on the calendar, which is the collider a second
time.

### 5.4 Risk-set control sampling is under-specified in a way that biases away from the null

Handled in full in 4.5: sample from the risk set at the case's post-discharge day; a participant may
be a control at one landmark and a case later; post-discharge day is the single time scale; calendar
year is a covariate and not a matching factor; up to 5 controls per case with a cap of 3 control
contributions per participant; seeded `FARM_FINGERPRINT` sampling; and person-clustered inference,
because conditional logistic regression assumes independent matched sets.

### 5.5 Day of week is a fixed effect, not an assumption

For a **complete** five-week window, day of week balances by construction: 35 consecutive days
contain exactly five of each weekday, so any day-of-week effect cancels in the sum and needs no
model term. That argument is true only when the window is complete. **With missing days it is
false**, and it fails differentially: a patient who wears the device on weekdays and abandons it at
weekends contributes a window whose day-of-week composition is not balanced, and the imbalance
correlates with the amount of missingness, which correlates with the group.

**Specified for Arm B:** day of week enters the daily-deficit model as a **7-level fixed effect**
(3.6). The g-computation then integrates over each episode's own calendar alignment, so the marginal
estimate is not conditional on any particular weekday and the reference level is irrelevant to it.
The day-of-week composition of each episode's baseline window and accrual window is recorded and
reported in aggregate.

**Specified for Arm A:** matching on **landmark day of week**, under the hierarchical relaxation
rule of 4.7. The reasoning is arithmetic rather than speculative: a 3-day window covers 3 of 7
weekdays, steps vary systematically by day of week, and emergency department presentations are not
uniform across the week. An unmatched design lets a case whose landmark fell on a Sunday be compared
against controls whose landmarks fell on Tuesdays, and the resulting step difference is partly a
calendar artefact.

---

## 6. The prespecified sensitivity ladder

**Figure 3 block 2 plots these rows in exactly this order.** The order is fixed here so that it
cannot be rearranged later to put a reassuring row at the top. Each row varies exactly one thing
from the primary, uses the identical estimator, and carries `B = 500` bootstrap resamples with the
seed convention of 3.8.

| # | slug or slugs | Row | What it varies | Why it is on the ladder |
|---|---|---|---|---|
| 1 | `pod_anchored_window` | **Postoperative-day-anchored window** | Accrual over postoperative days 8 to 42 instead of post-discharge days 1 to 35 | The protocol's own window. First row because it is the one departure from the protocol (5.1) |
| 2 | `inpatient_days_censored` | **Inpatient days censored** | Days inside a readmission stay removed from the window | Isolates the mechanism of 5.1: how much of the debt is a hospital bed |
| 3 | `complete_window_direct_regression` | **Complete-window direct regression** | Direct summation of `DRD` on episodes with all 35 days observed, regressed on the covariate set | The naive estimator of 3.2, shown rather than hidden. Reveals how far model-and-integrate moved the answer |
| 4 | `observation_weighted` | **Weighted for observation** | Observation weights of 3.7 removed, or applied where the primary rung did not use them | Isolates the contribution of the weights |
| 5 | `delta_shift_tipping_point` | **Delta-shift tipping point** | The `delta` grid of 3.11, three application patterns | Converts "your missingness is informative" into two reported numbers |
| 6 | `wear_definition_s1` to `wear_definition_s4` | **Wear thresholds** | Valid wear day definitions S1, S2, S3, S4 of 2.1, one row each | The wear rule determines what counts as a missing day, so it determines the primary's exposure to missingness |
| 7 | `baseline_window_60_15`, `baseline_window_30_1` | **Baseline windows** | Postoperative days -60 to -15, and days -30 to -1, instead of -30 to -8 | Tests whether excluding the final preoperative week matters, and whether a longer baseline stabilises `B_i` |
| 8 | `device_change_excluded` | **Device-change exclusion** | Exclude any participant changing Fitbit device model between baseline and post-discharge day 90 | A device change can shift step counts by more than the effect being measured |
| 9 | `baseline_floor` | **Baseline floor** | Restrict to `B_i` at least 1,000 steps per day (3.10) | The ratio's denominator problem |
| 10 | `debt_untruncated` | **Untruncated debt** | Remove the `max(0, .)` truncation, so days above baseline offset days below | Shows how much of the debt is one-sided accounting rather than net activity loss |

**Ten ladder rows expand to fourteen plotted rows**, because row 6 carries four wear definitions and
row 7 carries two baseline windows. The expansion is the reason `order` and `sub` are both exported:
the plan's fixed order survives it. Anyone counting "ten rows" in Figure 3 block 2 is off by four.

**The plotted vocabulary, owned here.** This is the set `local/verify.py` asserts equality against,
and it has exactly fourteen members.

| order | sub | slug | display label | axis | render |
|---|---|---|---|---|---|
| 1 | 1 | `pod_anchored_window` | Postoperative day 8–42 window | primary | marker |
| 2 | 1 | `inpatient_days_censored` | Inpatient days censored | primary | marker |
| 3 | 1 | `complete_window_direct_regression` | Complete windows, direct regression | primary | marker |
| 4 | 1 | `observation_weighted` | Weighted for observation | primary | marker |
| 5 | 1 | `delta_shift_tipping_point` | Delta-shift tipping point | `latent_logit_shift` | panel |
| 6 | 1 | `wear_definition_s1` | Wear day at 40% heart-rate adherence | primary | marker |
| 6 | 2 | `wear_definition_s2` | Wear day at 10 hours plus 100 steps | primary | marker |
| 6 | 3 | `wear_definition_s3` | Wear day at 8 hours | primary | marker |
| 6 | 4 | `wear_definition_s4` | Wear day at 12 hours | primary | marker |
| 7 | 1 | `baseline_window_60_15` | Baseline 15–60 days before surgery | primary | marker |
| 7 | 2 | `baseline_window_30_1` | Baseline 1–30 days before surgery | primary | marker |
| 8 | 1 | `device_change_excluded` | Device change excluded | primary | marker |
| 9 | 1 | `baseline_floor` | Baseline floor at 1,000 steps per day | primary | marker |
| 10 | 1 | `debt_untruncated` | Debt not truncated at zero | primary | marker |

The display label of `observation_weighted` is **"Weighted for observation"**, exactly those three
words, in the label table and in the plotted row alike. Every display label above is a printed string
governed by character equality; a second phrasing of any of them anywhere in this project is an error
to be corrected against this table.

**Row 5 renders as its own small panel** inside block 2, because a tipping curve is not a point
estimate with an interval and plotting it as one would misrepresent it. It is the only row whose
`axis` is not `primary`: its scale is latent log-odds, not activity days, so a renderer that plotted
it as a marker on the shared axis would assert a comparison that does not exist.

**Protocol sensitivity analyses carried over where they still apply**, reported in the supplement
and not plotted in Figure 3: lumbar-only cohort; cervical-only cohort; fusion-only and
decompression-only cohorts; alternate wear thresholds of 8, 10 and 12 hours (row 6 above, repeated
here for the trace); official-style valid day requiring at least 100 steps; restriction to BYOD and
WEAR participants separately; restriction to participants with dense EHR observation; and exclusion
of the COVID-19 disruption period as an alternative to adjusting for calendar era. For Arm A only,
and only at a permitted tier: index events from postoperative days 8 to 30; index events from
postoperative days 31 to 90; local deterioration in steps as the exposure instead of preoperative
baseline normalization; and the negative-control window of 4.8.

**Supplementary Arm B rows**, which are **not** members of the fourteen-row set above and are not
plotted on the Figure 3 ladder. They carry slugs so that a supplementary exhibit can name them
without inventing one, and the separation is stated explicitly so the set-equality assertion is
unambiguous about what it is asserting over.

| slug | display label | What it is |
|---|---|---|
| `baseline_steps_adjusted` | Baseline steps adjusted | The primary model with `B_i` added to the mean structure |
| `bmi_multiply_imputed` | Body mass index multiply imputed | `m = 20` imputations with `SEED = 0`, in place of the missing indicator |
| `weights_without_lagged_wear` | Observation weights without lagged wear | The weight model of 3.7 refitted with the lagged wear fraction removed |
| `junctions_mirrored` | Junction codes mirrored | Cervicothoracic and thoracolumbar stems assigned to the caudal rather than the cranial member |
| `cervical_fusion_gap_reclassified` | Cervical fusion gap reclassified | The misfiled anterior cervical fusions of 2.7 moved to cervical fusion |
| `cervical_decompression_gap_stated` | Cervical decompression gap | The absent cervical decompression codes of 2.7, reported as a measured omission |
| `four_group_model` | Four-group model | The four-group specification where the collapse ladder of 2.5 permits it |
| `truncated_assigned_max_debt` | Truncated windows at maximal debt | Episodes truncated by death or reoperation (2.3) assigned the maximal 35 days lost |
| `fusion_status_non_add_on_only` | Fusion status without add-on codes | The primary contrast re-estimated with fusion status read from non-add-on records only, the reading 2.4 declines |
| `baseline_weekday_weekend_split` | Separate weekday and weekend baselines | The primary contrast re-estimated with each day's deficit taken against the baseline of its own day type, weekday or weekend (2.2) |

The two concept-set rows are governed by 2.7, which fixes what each measurement triggers before the
measurement exists.

**The ninth supplementary row is new in version 1.2.**
`fusion_status_non_add_on_only` is the reading of the fusion-status rule that 2.4 declines: fusion
status read from non-add-on records only, so that an episode whose only fusion evidence is an add-on
or instrumentation code is classified decompression instead. Like the eight rows above it, it is
**not** a member of the fourteen plotted rows that `local/verify.py` asserts set equality against,
and it is not plotted on the Figure 3 ladder. Its purpose is to **bound how much of the primary
contrast rests on episodes whose fusion status comes only from an add-on code**. If the two readings
give the same contrast, the classification rule is not load-bearing and a reader can stop weighing
it; if they diverge, the size of the divergence is on the page rather than in an argument. That is
the same move this plan makes with the delta-shift tipping point of 3.11 and the Manski bounds of
3.12: a judgment call is converted into a reported number, and the reader is handed the number
rather than the judgment.

**Ten supplementary rows. The tenth is new in version 1.3, and it is supplementary rather than a
fifteenth plotted row by a decision recorded below rather than by default.**
`baseline_weekday_weekend_split` carries the weekday-and-weekend baseline sensitivity the protocol's
own baseline section asks for and versions 1.0 through 1.2 of this file dropped: section 6 held no
split-baseline slug in either set, so the sensitivity could not be run, and a reviewer comparing the
protocol against the Methods would have found a silent omission. Section 2.2 now specifies it in
full, the two medians, the minimum valid days in each half of the week, what happens to an episode
with valid days in only one half, and how the contrast is reported.

**Why it is supplementary and not plotted, argued rather than assumed.** The obvious home for it is
row 7, beside the two alternative baseline windows, and the structural resemblance is real: all
three vary the preoperative reference. The decision goes the other way, for a reason about what the
two sets are for. Every one of the fourteen plotted rows tests a choice the primary makes with no
other protection: the wear rule, the window anchor, the truncation, the estimator, the weights,
the baseline window. Day of week is not such a choice. It is already handled twice inside the
primary, as a 7-level fixed effect in the mean structure (3.6) and by g-computation over each
episode's own calendar alignment (3.8, 5.5), and 5.5 sets out at length why both handlings are
there. The split baseline asks the narrower remaining question, whether the **denominator** needs
the same protection the numerator already has. A row that corroborates a handling the primary
already carries belongs in the supplement; a row that tests an unhedged choice belongs on the
plotted ladder. That is the line the two sets are drawn along, and it is the line this row falls on.

A second reason points the same way and is worth separating from the first, because it is the weaker
of the two and should not be mistaken for the argument. The fourteen plotted rows share one axis,
baseline-equivalent activity days lost against a single personal reference. This row's reference
**moves within an episode**, day by day, with the calendar. Its estimate therefore lives in a unit
close to the shared unit but not identical to it, and a reader comparing markers along one axis
would read part of any gap as instability in the primary when some of it is a change in what a day
is measured against. That is the same argument this plan already makes for rendering the delta-shift
row as its own panel instead of a marker: an axis is an assertion that the things on it are
comparable, and the assertion has to be true.

**What follows, stated prominently because it crosses a file this plan does not own.** The fourteen
plotted rows are **untouched**. Same members, same slugs, same display labels, same `order` and
`sub` values, in the same order, in a table that is byte-identical to version 1.2's.
`local/verify.py`'s set-equality assertion against the fourteen is therefore unaffected, and no
transcription of the fourteen anywhere needs to change. What changes is the supplementary count,
from nine to ten. `prespecification/EXPORT-CONTRACT.md` section 11.3 must gain the row
`baseline_weekday_weekend_split` with the display label **Separate weekday and weekend baselines**;
the sentence excluding the supplementary rows from the assertion by name must read **ten** where it
now reads nine; and the ownership row must read "the 14 plotted rows and the 10 supplementary rows"
as of plan version 1.3. Under the header rule, where a list here and a list in that contract
disagree, this file wins and the contract is amended in the same commit. That contract's own checker
asserts set equality against this section, so until the row is transcribed the checker will report a
**failure**. That is the check working as designed. It is closed by adding the row, never by
loosening the check.

---

## 7. Multiplicity

**One primary estimand per aim, and only two aims.**

| Aim | Primary estimand | Test |
|---|---|---|
| Arm B | Adjusted difference in Digital Recovery Debt over post-discharge days 1 to 35, fusion minus decompression, pooled across region by standardization | Two-sided, 5%, no adjustment |
| Arm A | Adjusted odds ratio for an acute-care encounter per 20-percentage-point lower proximal step ratio, at the permitted tier | Two-sided, 5%, no adjustment |

**No alpha adjustment is applied to those two.** They are prespecified, they address distinct aims,
and adjusting two prespecified primary tests trades power for a correction that no reporting
guideline requires.

**Everything else is labelled explicitly as not multiplicity-controlled**, in the text, in each
table footer, and in each figure caption. That set is: the region contrast; the fusion-by-region
interaction; the within-region contrasts; every subgroup; every row of the sensitivity ladder of
section 6; the absolute-scale companion endpoint; the mean normalized activity and the share
reaching 80% of baseline; every secondary outcome and every secondary horizon; and every gate count.
Those are reported with confidence intervals and read as descriptive.

**No P value in this plan selects anything.** No model, window, covariate, cutpoint, subgroup, or
exhibit is chosen on the basis of a P value, at any point.

---

## 8. Disclosure rules that bind every number in this plan

These are not stylistic. They constrain what the estimator is permitted to emit.

1. **Counts 1 to 20 inclusive are suppressed. A count is disclosable only when it is zero or
   strictly greater than 20.** The single arbiter is the predicate `disclosure.disclosable(n)`; no
   module in `pipeline/` or `local/` writes a bare 20 into a comparison of its own. Larger counts
   are rounded to the nearest 20, ties away from zero, so 50 rounds to 60 and not to 40: a Methods
   sentence saying "rounded to the nearest multiple of 20" cannot defend 50 becoming 40.
2. **A rounded and disclosed 20 stands on a true count of 21 to 29**, never on 20 and never on 30.
   Rounding sends 21 through 29 to 20 and sends 30 to 40, while a true 20 is suppressed by rule 1
   rather than printed. The Methods footnote and the `disclosure.py` module docstring carry the same
   sentence, so the two cannot drift: "Counts of 20 or fewer are suppressed; larger counts are
   rounded to the nearest 20, so a disclosed 20 represents a true count of 21 to 29."
3. A percentage is suppressed whenever its numerator count is suppressed, because a percentage
   multiplied by a disclosed denominator recovers the hidden count exactly.
4. Percentages are computed from the **rounded numerator over the rounded denominator** and printed
   to **zero decimals**. Both halves matter. Zero decimals, because a one-decimal percentage against
   a rounded denominator lets a reader back-calculate an exact small numerator. A rounded
   denominator, because it makes every printed percentage reproducible from the printed counts,
   which is the first thing a careful reader checks, and it removes the raw denominator from the
   computation entirely. **The same arithmetic binds a rate.** An event rate is computed from the
   rounded numerator over the rounded denominator, for the same two reasons, and is not produced at
   all when its numerator is not disclosable. A rate computed from a true numerator and printed
   beside a rounded denominator lets a reader multiply the two and recover the hidden count exactly,
   which is the leak the rounding exists to close.
5. Complementary suppression is enforced: if suppressing one cell of a row still allows it to be
   recovered by subtraction from a disclosed total, a second cell is suppressed as well.
6. Controlled Tier dates are **unshifted**, so a date column is an identifier. No date, no
   near-unique column, and no participant-level value reaches any exported surface.
7. Every exported table carries its contributing `n` per row and an md5 checked after transcription.
8. Every figure and every table prints its own denominator.

---

## 9. The locked exhibit list

Exactly **3 figures and 3 tables**. The split between Table 2 and Figure 3 is enforced, not
stylistic: **Table 2 holds adjusted absolute levels, Figure 3 holds contrasts only**, so neither
repeats the other and the exhibit budget buys three distinct things rather than two things twice.
Covariate effects, the daily-trajectory model, and the full sensitivity grid go to the supplement,
because a surgeon audience wants the group contrasts and the absolute levels, not a coefficient
table.

### 9.1 Figures

**Figure 1. Participant flow (STROBE).** The **nineteen rungs of 2.6**, in that order, from the
program cohort through qualifying spine episodes, the eligibility exclusions, Fitbit linkage,
baseline-wear eligibility, the first-eligible-episode reduction, and the analytic cohort, with a
right-hand exclusion box carrying that rung's reason display at each step, terminating in the
analyzable acute-care event count. Drawn with the ladder-closure assert of 2.6, evaluated within
unit, or the build fails. Every box is rounded to the nearest 20, so the boxes will not reconcile arithmetically;
the rounding footnote is published and the displayed numbers are never adjusted to make them add up.
*Unique because:* nothing else in the paper shows cohort construction, and this is exactly what
STROBE requires.

**Figure 2. Baseline-normalized daily activity by post-discharge day.** The x axis runs
post-discharge day 1 to 90; the y axis is activity as a fraction of the patient's own preoperative
baseline; a bold reference line sits at 1.0 and the day 1 to 35 accrual window is shaded. Series are
the procedure groups at whatever collapse level 2.5 selected. Observed median with interquartile
ribbon, plus the model-fitted marginal curve as a dashed overlay, where the fitted curve is the
g-computed marginal `1 - D_hat` of 3.8, so **the shaded area between the fitted curve and the
reference line literally is the estimand**. *Unique because:* this is the shape of recovery, and no
table shows it.

**Figure 3. Recovery debt: contrasts and robustness.** A horizontal forest plot in three blocks.
*Block 1*, the primary and key secondary contrasts: fusion versus decompression pooled across region
(the primary estimand), lumbar versus cervical, the interaction, and the within-region contrasts.
*Block 2*, robustness of the primary contrast across the ten ladder rows of section 6 **in that
order**, which expand to fourteen plotted rows, with the delta-shift row rendered as its own panel.
*Block 3*, the eight prespecified subgroups named below, every one of which prints whether or not it
is estimable. *Unique because:* contrasts live here and only here. Block 1's five contrast slugs are
`fusion_vs_decompression`, `lumbar_vs_cervical`, `region_by_fusion_interaction`,
`fusion_vs_decompression_cervical` and `fusion_vs_decompression_lumbar`; that vocabulary is owned by
`prespecification/EXPORT-CONTRACT.md` section 7.3, not by this file.

**The prespecified subgroups, owned here.** Eight rows, fixed before any count exists. This list is
in the hash. A subgroup list that could still be chosen would be a choice made after seeing data,
which is the one thing this document exists to prevent, so the list is written out rather than
described by a rule that selects it later.

| order | slug | display label | Defining variable and cut |
|---|---|---|---|
| 1 | `subgroup_age_lt_65` | Younger than 65 years | Age at index under 65 years |
| 2 | `subgroup_age_ge_65` | 65 years or older | Age at index 65 years or older |
| 3 | `subgroup_female` | Female sex assigned at birth | Sex assigned at birth recorded female |
| 4 | `subgroup_male` | Male sex assigned at birth | Sex assigned at birth recorded male |
| 5 | `subgroup_bmi_lt_30` | Body mass index under 30 | Body mass index under 30 kg/m2, on the nearest measurement within 365 days before index (3.6) |
| 6 | `subgroup_bmi_ge_30` | Body mass index 30 or above | Body mass index 30 kg/m2 or above, same measurement rule |
| 7 | `subgroup_device_byod` | Participant-owned device | Device provenance recorded as participant-owned |
| 8 | `subgroup_device_wear` | Program-provided device | Device provenance recorded as program-provided |

**The cuts are fixed a priori and are not tuned.** 65 years is the conventional older-adult
boundary and the one a surgical readership expects; 30 kg/m2 is the World Health Organization
obesity threshold. Neither is a data quantile, and neither may be moved without an amendment.

**How a subgroup row is estimated.** Each row is the **primary contrast re-estimated within the
subgroup**, using the identical estimator rung, covariate set, observation weights, seeds and
`B = 500` bootstrap resamples of 3.8. Two mechanical consequences are prespecified so they are not
decided at the keyboard: the subgrouping variable is dropped from the covariate set inside its own
row, where it is constant or nearly so; and where the primary carries that variable as a restricted
cubic spline (age, body mass index), the spline is replaced by a **linear** term inside the row,
because a 3-knot spline on a truncated range is not identified.

**The rule that makes a subgroup not estimable**, applied in this order and never revisited after an
estimate has been seen:

1. **Cell size.** A row is estimated only if **every** cell it needs is disclosable, that is, zero
   or strictly greater than 20 (section 8). The cells it needs are the subgroup's episode count in
   each arm of the contrast being drawn at the collapse level reached: fusion and decompression at
   levels 1 and 2. If any one of them is not disclosable, the row prints
   **"not estimable (cell size)"**, slug `not_estimable_cell_size`.
2. **Convergence.** If the within-subgroup fit fails at the primary rung and at every rung below it
   on the ladder of 3.5, which cannot happen at rung 5 and is therefore reported rather than
   expected, the row prints **"not estimable (model did not converge)"**, slug
   `not_estimable_convergence`.
3. **No contrast exists.** At collapse level 3 or 0 there is no between-group contrast to subgroup,
   so block 3 is replaced in full by one sentence saying so, and no row is printed. This is one
   sentence and not eight suppressed rows, because eight identically suppressed rows would suggest
   eight separate small cells rather than one absent estimand.

**No subgroup ever vanishes.** A row that is not estimable prints its label and its reason, because
silent omission itself leaks which cells were small: a reader who counts the rows learns exactly
which subgroups fell short. This is rule 3 of 9.3, stated here in the vocabulary that owns it.

**Two absences are deliberate and are stated in the caption rather than left to inference.** Sex
assigned at birth recorded as other or unknown is not a subgroup row: it is a heterogeneous residual
category rather than a clinical stratum, and those episodes contribute to the primary and to every
subgroup for which they qualify. Episodes with no body mass index measurement contribute to the
primary through the missing indicator of 3.6 but belong to neither body-mass-index row, so those two
rows print a denominator that does not sum to the analytic n, and the caption says so. If the
release does not distinguish participant-owned from program-provided devices, rows 7 and 8 both
print "not estimable (data not available)" rather than being dropped.

**Subgroups are not multiplicity-controlled** and are read as descriptive, per section 7.

### 9.2 Tables

**Table 1. Cohort characteristics and wearable data availability by procedure group.** Columns are
the procedure groups at the selected collapse level, each header carrying its own `n`. Rows: age,
sex assigned at birth, self-reported race and ethnicity, BMI, comorbidity burden, index length of
stay, index era, device class; then preoperative baseline steps, valid baseline days, valid wear
days inside the accrual window, and the share with a near-complete window. Percentages are computed
from the rounded numerator over the rounded denominator and printed to zero decimals (section 8).

**Table 2. Adjusted digital recovery debt by procedure group.** The primary estimand's **absolute
level**: `n`; unadjusted debt as median and interquartile range, computed by direct summation on
complete windows only, labelled as the naive estimator with its own denominator printed; adjusted
debt in baseline-equivalent activity days lost with a 95% CI; the absolute-scale companion in
thousand steps lost (3.9); adjusted mean normalized activity across the window, defined as
`1 - D_bar`, that is, mean normalized activity capped at baseline (3.3); and the adjusted share
reaching 80% of baseline, defined as the fitted probability that an episode's median daily capped
normalized activity over post-discharge days 29 to 35 is at least 0.8, estimated by a logistic
g-computation on the same covariate set with person-clustered bootstrap inference. Footer carries
model fit, the model rung reached on the ladder of 3.5, the share with zero debt, and the
**assumption-free Manski bounds** of 3.12. *Unique because:* absolute adjusted levels live here and
only here.

**Every sensitivity fitted on its own subset prints its own denominator, and Table 2's footer is
where that happens.** Several rows of this plan cannot be fitted on the whole analytic cohort,
because the quantity they vary is itself sometimes absent. `baseline_weekday_weekend_split` needs at
least 5 valid weekday days and at least 2 valid weekend days in the baseline window (2.2), and an
episode whose valid days all fall in one half of the week has no second baseline to fit against.
`baseline_window_60_15` and `baseline_window_30_1` need a baseline in a window that rung 12 of the
eligibility ladder never tested, so either may be absent on an episode that is fully eligible.
`wear_definition_s1` through `wear_definition_s4` each need a baseline recomputed under their own
wear rule, and a stricter rule can leave an episode with no valid baseline day at all.
`baseline_floor` and `device_change_excluded` restrict by construction, and
`complete_window_direct_regression` is defined only on complete windows.

**A contrast printed against the analytic `n` when it was fitted on fewer episodes is a mislabelled
number, and nothing about the estimate reveals it.** Table 2's footer therefore carries, for **every
row whose fitted set is smaller than the analytic cohort**, that row's own `n` and the count of
episodes it could not use, both rounded and suppressed under section 8. Where a row's fitted set
equals the analytic cohort the footer says so explicitly rather than omitting the row, because an
omission cannot be told apart from an oversight by anyone reading the table. The unadjusted column
already has its own denominator for exactly this reason, printed as `Complete windows`; this rule
generalises that treatment to every row rather than inventing a new one for the split baseline.

**Table 3. Feasibility gate and the analysis it permits.** *Part A* is the protocol's A through F
ledger: qualifying episodes by group; episodes with adequate baseline wear; episodes with a
computable post-discharge window; first ED visits, readmissions, and the composite through day 90;
events with a computable proximal step ratio; and events by stratum, ending with the tier reached
and the **verbatim permitted claim** from the table in 1.2. *Part B* is whatever that tier allows,
from nothing at all up to the adjusted odds per lower step ratio with its negative-control window
and median lead time. *Unique because:* this is the only exhibit containing Arm A, the acute-care
endpoint, or the gate.

### 9.3 Suppression rules that bind the figures

These are prespecified because each of them is a place where a plot could otherwise leak a small
cell or, worse, leak *which* cells were small.

1. **Any day at which a group's contributing episode count is not disclosable is dropped entirely**,
   that is, any day whose count is between 1 and 20 inclusive. The line and the ribbon are
   **truncated** at that day. They are never plotted thin, faded, dashed, or
   annotated, because a visibly degraded segment communicates the same information as the suppressed
   count. The truncation day is stated in the legend.
2. **Medians and quartiles are suppressed on the same rule.** A median of three people under
   unshifted dates is effectively an individual-level value.
3. **Any subgroup with a cell that is not disclosable prints "not estimable (cell size)"** rather
   than vanishing from the forest plot, because silent omission itself leaks which cells were small:
   a reader who counts the rows learns exactly which subgroups fell short. The eight subgroups and
   the full not-estimable rule are in 9.1.
4. **Every figure prints its own denominator**, and every exported plot series carries its
   contributing `n` per row.
5. No image crosses the perimeter. The VM exports the plotted series; figures render locally.

### 9.4 Table 3 stage F, anticipated rather than discovered

Stage F, events by region and fusion stratum, will very likely fall at or below 20 in every cell. It
prints as suppressed **unless all four cells are disclosable**, for the complementary suppression
reason of section 8.

### 9.5 The alternate exhibit set, if the gate returns 50 or more events

At tier 1 or 2, Arm A becomes primary and the exhibits switch as a set. This is triggered by the
event count, a count and not an estimate, and it is the only exhibit-level branch in the plan.

| Exhibit | Alternate content |
|---|---|
| Figure 1 | Unchanged |
| Figure 2 | Event-centered normalized steps for cases against post-discharge-day matched controls, day `E-14` to `E+7` |
| Figure 3 | Adjusted spline dose-response for `R_72`, with an alert-burden panel |
| Table 1 | Split by event status instead of by procedure group |
| Table 2 | The conditional logistic regression with absolute-risk translation |
| Table 3 | Clinical-time versus step-augmented model comparison |

Under the alternate set, Arm B moves to the supplement in full, and the recovery-debt primary
estimand is still reported in the main text as a single sentence with its contrast and interval, so
the guaranteed deliverable is never lost.

---

## 10. Seeds, software, and reproducibility

- **Master seed `SEED = 0`**, everywhere, in Python and in R.
- **BigQuery row sampling and matched-set sampling use `FARM_FINGERPRINT` with the fixed seed, never
  `RAND()`.**
- **Monte Carlo marginalization:** `M = 2,000` draws, `numpy.random.default_rng(SEED)` for the point
  estimate, `default_rng([SEED, b])` inside bootstrap resample `b`, common random numbers across
  days and groups, convergence check at `M = 4,000` on `default_rng([SEED, 999])` with a 0.05
  activity-day tolerance (3.3).
- **Clustered bootstrap:** `B = 1,000` for primary contrasts, `B = 500` for sensitivity rows,
  resample `b` seeded `default_rng([SEED, b])` (3.8).
- **Medians in SQL** come from an exact-median UDF, never `APPROX_QUANTILES(x, 2)[OFFSET(1)]`, which
  returns the upper value on an even-length array.
- **Software and versions** are recorded in `results.json`: language, package versions, the model
  rung reached, the descent triggers that fired, the RNG kind, and the resolved CDR dataset and
  location.
- **Environment facts are probed, never assumed:** Fitbit table existence in the Controlled Tier
  CDR, the CDR location, the `heart_rate_summary` zone column name and its partition property, the
  ED and inpatient `visit_concept_id` values, and the presence of `statsmodels` 0.14 or later.

---

## 11. Stop conditions specific to this plan

Each halts the analysis. None is a number to overwrite or a check to relax late in a session.

1. **The plan hash does not match.** `lock_plan.py --check` exits non-zero and no analysis proceeds
   until either the file is restored or an amendment is written in section 13 and the file
   re-hashed.
2. **The plan hash was not recorded before Phase 2 ran.** The prespecification did not precede the
   counts, and the claim this document exists to support is void.
3. **A ladder rung was selected on anything other than a trigger in 3.5.** Halt and revert.
4. **The collapse level was decided after a model was fit.** Halt and revert. The level is decided
   on the Phase 3 attrition ladder.
5. **More than 25% of bootstrap resamples fail to converge** and the ladder was not descended
   (trigger T4).
6. **A sensitivity row was added, dropped, or reordered** relative to section 6 without an
   amendment.
7. **A suppression rule of section 8 or 9.3 was relaxed** to make an exhibit look complete.
8. **A slug reached an exported surface that is not in one of the five vocabularies of this file**,
   or one of those vocabularies lost a member without an amendment. `local/verify.py` asserts set
   equality against sections 2.4, 2.6, 3.5, 6 and 9.1; a mismatch halts the export rather than
   being reconciled at run time.
9. **A subgroup was added to, or removed from, the eight of 9.1**, or a subgroup cut was moved.
   The list and the cuts are inside the hash, and a subgroup chosen after a count has been seen is
   the failure this document exists to prevent.
10. **The attrition ladder did not close within unit**, or a count was adjusted to make it close.
11. **A fit above the coefficient ceiling of 4.9 reached an exported surface**, or the ceiling was
    raised, lowered, or applied to some fits and not others once a run had produced a number. The
    constant is inside the hash, a refusal is reported as a refusal with its named reason, and a
    clipped value is never substituted for one.

---

## 12. Objections a hostile reviewer will raise, and where each is already answered

| Objection | Answer | Section |
|---|---|---|
| "You picked the recovery-debt arm because the event count was too small." | Arm B needs no events and was designated primary before any count existed, in a file hashed and timestamped before Phase 2 | 1.1, header |
| "Your window is not the protocol's window." | Correct, and the reason, the cost, and the sensitivity row that recovers the protocol's window are all prespecified | 5.1, row 1 of 6 |
| "Then just adjust for length of stay." | A covariate cannot repair a term inside the definition of the outcome window, and length of stay is post-treatment | 5.1 |
| "Your missingness is informative." | Agreed. The tipping point reports how bad it must be before the contrast crosses zero, and Manski bounds report what holds with no assumption at all | 3.11, 3.12 |
| "You summed observed days and called it a total." | The primary does not sum observed days. Direct summation is a sensitivity row, printed alongside | 3.2, row 3 of 6 |
| "Your mixed model's predictions are conditional, not marginal." | Marginalized by Monte Carlo over the fitted random-effect distribution, with draws, seed, and a convergence check specified | 3.3 |
| "You plugged a mean into a nonlinear function." | The deficit is the modelled response. Nothing is pushed through `max(0, 1 - .)` after fitting | 3.3 |
| "Your AR(1) is wrong with missing days." | Continuous-time AR(1) on the day scale, with an ordered descent if it will not converge, and inference from a person-level bootstrap either way | 3.4 |
| "You chose the model that gave you the answer." | Every descent trigger is a computational property of the fit or the environment. None references an estimate | 3.5 |
| "Five weeks balances day of week." | Only for a complete window. With missing days it does not, so day of week is a fixed effect and a matching factor | 5.5 |
| "Your controls were participants who never had an event." | Forbidden. Controls come from the risk set at the case's post-discharge day, and a control may be a case later | 4.5 |
| "Conditional logistic assumes independent matched sets." | Agreed, which is why inference is person-clustered and a cap limits control reuse | 4.5 |
| "Where are the early events?" | Structurally uncomputable, named, counted in their own attrition row, and their timing reported | 4.3 |
| "You dropped the sickest windows by requiring wear." | No computable step signal is a co-primary exposure with its own coefficient | 4.4 |
| "Sedentary patients cannot accrue debt." | Named, with a floor value, a sensitivity row, and an absolute-scale companion endpoint immune to it | 3.9, 3.10 |
| "Subgroup X is missing from your forest plot." | It prints "not estimable (cell size)". Nothing vanishes silently | 9.1, 9.3 |
| "You chose those subgroups after seeing the forest plot." | Eight subgroups, each with a slug and a fixed cut, written into a file that was hashed before any count existed. The rule that makes one not estimable is prespecified too | 9.1 |
| "Where did the thoracic operations go?" | Excluded, on a counted rung, because the target population is cervical and lumbar. Named before the concept set was ever run | 2.4, 2.6 |
| "How do you know these were elective?" | A prespecified proxy with a stated definition of "immediately preceding" and three stated rescues, labelled a proxy in the Methods, with the number removed reported | 2.6 |
| "Your concept set misses the legacy ACDF code." | Measured, with the response to every possible value of the measurement fixed before the measurement ran | 2.7 |
| "An instrumentation code with no arthrodesis code made your patient a fusion." | Fourteen of the sixteen add-on codes in the locked set are fusion codes, instrumentation without arthrodesis is essentially never performed in degenerative disease, and the two readings differ only where the primary code was never captured. The reading you prefer is a reported supplementary row, not an argument | 2.4, 6 |
| "Then an add-on code on its own can conjure an operation." | It cannot. An add-on-only bundle is excluded and counted at rung 9. Whether an operation happened and which arm it belongs to are separate questions, decided by separate rules | 2.6 |
| "The protocol asked for weekday and weekend baselines and your Methods has none." | It has one. Two medians, a minimum valid-day count in each half of the week, a stated rule for an episode with only one half, and a supplementary row with its own denominator | 2.2, 6 |
| "You reweighted for observation and quietly dropped the earliest windows to do it." | The weight rule drops them from the weighted sensitivity and from nothing else. Separately, a window holding fewer than 2 post-discharge days has no exposure to weight or to model at all; that is the definitional condition, it sits outside the co-primary exposure everywhere, and it is counted rather than folded in. Three counts are printed, including the matched sets that lose every control | 4.4 |
| "Your no-computable-signal exposure includes windows that could never have been computed." | It does not. A landmark day of 1 or less is the definitional condition and carries no `N` on any surface. That exposure measures participants who stopped wearing the device; a window that straddles discharge is uncomputable by the calendar, and the calendar is already the design's time scale | 4.4 |
| "Your conditional model exported an odds ratio in the thousands." | It cannot. A fit carrying any coefficient whose absolute value exceeds the prespecified ceiling of 10 is refused and prints "not estimable (separation)", and the count of refusals is printed | 4.9 |
| "That ceiling is how you buried a result you did not like." | The ceiling can only ever remove a number. It has no branch that emits an estimate, changes one, or moves one toward or away from the null, and it was fixed before any count existed at the conventional literature value rather than at the value that would have caught the fit that prompted it | 4.9 |
| "Your weight model just assumed an average weight where it had no data." | It does not. The two options that would have, carrying the predictor back onto the preoperative grid and assigning the marginal weight, are named and rejected in writing, with the reason for each | 4.4 |
| "You measured the collider inside the sets the collider selected." | No. The with-versus-without comparison runs on a full-cohort day-indexed panel, so its denominator is every episode day at risk, and it is reported crude and standardized over the six prespecified recovery day bands | 4.4 |
| "You standardized over week-wide bands because narrower strata gave you the wrong answer." | The strata were fixed before any count existed and the reason they are bands is disclosure, not fit. Standardizing day by day is a weighted average of per-day event counts that are all below the floor, so the figure would carry them inside it. The rule is stated in the plan and not only in the code, and the standardized figure is withheld outright unless every contributing band clears the floor | 4.4, 8 |
| "How many tests did you run?" | Two primary estimands, no alpha adjustment on those two, everything else labelled not multiplicity-controlled | 7 |

---

## 13. Amendment log

**Any change to this file after a lock is recorded here** with a date, the section amended, the
change, the reason, who approved it, and the **superseded** SHA-256. The superseded hash rather than
the new one, because a file cannot contain its own hash: the new hash is written by `lock_plan.py`
into `prespecification/PLAN-HASH.txt` and pasted into `SESSION-LOG.md`, where **both** are kept. The
Methods cite the plan by hash and date, and cite any amendment. A change made without an entry here
is stop condition 1 of section 11.

**Entry 1 is a correction to an unpublished document, not a post-hoc amendment**, and the
distinction is the whole point of the log, so it is stated plainly rather than implied. The
provisional lock of 2026-08-26T03:43:40Z was a working checkpoint at the end of a build session. It
was never published, never cited, and never used to gate an analysis. **No count, coefficient,
curve or P value from this study had been observed at the time of that lock, and none had been
observed at the time of this correction.** No BigQuery query had been run against the Controlled
Tier. Every change in entry 1 is therefore a repair to a document whose claim to precede the data is
untouched by it. Recording it as an amendment is the conservative choice: an unrecorded correction
and a concealed amendment are indistinguishable to a reader, and only one of them is honest.

**Entry 2 is a correction to an unpublished document as well, and not a post-hoc amendment.** The
same facts hold of it as held of entry 1, and they are stated rather than implied. **No count,
coefficient, curve or P value from this study had been observed at the time of the lock it
supersedes, and none had been observed at the time of this correction.** No BigQuery query had been
run against the Controlled Tier. The lock of 2026-08-26T04:49:02Z was never published, never cited,
and never used to gate an analysis. The change was made at the human's direction after a review
found two modules disagreeing about fusion status, one reading add-on and instrumentation codes and
one not, with this file fixing no rule either way. It therefore adds a rule where the plan was
silent rather than replacing one the plan had stated, and it adds a supplementary sensitivity row
that reports the reading it declines. The plan's claim to precede the data is untouched by it.

**Entry 3 is a correction to an unpublished document, and not a post-hoc amendment.** The same
facts hold of it as held of entries 1 and 2, and they are stated in those terms rather than left to
inference. **No count, coefficient, curve or P value from this study has been observed**, not at the
time of the lock this entry supersedes and not at the time of this correction. **No BigQuery query
has been run against the Controlled Tier.** The lock of 2026-08-26T12:31:20Z was never published,
never cited, and never used to gate an analysis. Every change in this entry is therefore a repair to
a document whose claim to precede the data is untouched by it.

**What prompted it.** A downstream module found the gap rather than a reader of the plan. While
specifying `pipeline/04_features.py`, which validates the derived tables the analysis modules read,
the work found that the derived `baseline` table carries no weekday or weekend median and that
section 6 of this file held no split-baseline slug in either the plotted set or the supplementary
set, so a sensitivity the protocol asks for in plain words could not have been run and nobody
reading this file alone would have noticed. The same module found two rules this file had left
undefined at the point where code has to act: the observation weight of 4.4 has no input at a
landmark that precedes the first post-discharge day, and the with-versus-without computable-ratio
comparison of 4.4 had no surface to be computed on that was not already selected on the variable it
measures. A protocol-to-plan gap that only a build finds is exactly the gap this log exists to make
visible, so the origin is recorded here rather than smoothed over.

**Entry 4 is a correction to an unpublished document, and not a post-hoc amendment.** The same
facts hold of it as held of entries 1, 2 and 3, and they are stated in those terms rather than left
to inference. **No count, coefficient, curve or P value from this study has been observed**, not at
the time of the lock this entry supersedes and not at the time of this correction. **No BigQuery
query has been run against the Controlled Tier.** The lock of 2026-08-26T13:56:10Z was never
published, never cited, and never used to gate an analysis. Every change in this entry is therefore
a repair to a document whose claim to precede the data is untouched by it, and nothing in it could
have been informed by a result, because there is no result.

**What prompted entry 4.** A module author found it, not a reader of this file. While building
`pipeline/06_analysis_gate.py`, which implements Arm A, the work found that the specification in 4.4
could not be published under this project's own disclosure rule. 4.4 required the with-versus-without
computable-ratio comparison to be reported crude and directly standardized to post-discharge day.
Direct standardization over the day grid is a weighted average of per-day event counts; in a cohort
of this size those per-day counts are individually below the floor of rule 1 of section 8, and the
standardized figure carries them inside it. The number as specified was therefore either
unpublishable or publishable only by disclosing what the floor exists to withhold. The module did
not quietly substitute a coarser quantity and leave this file saying something else. It named the
substitution as a coarsening and referred the specification back here, which is the behaviour this
log exists to reward: a specification that a build cannot execute honestly is a defect in the
specification, and the fix belongs in the hashed document rather than in a comment in a module
nobody reviewing the Methods will read.

**Entry 5 is a correction to an unpublished document, and not a post-hoc amendment.** The same
facts hold of it as held of entries 1 through 4, and they are stated in those terms rather than left
to inference. **No count, coefficient, curve or P value from this study has been observed**, not at
the time of the lock this entry supersedes and not at the time of this correction. **No BigQuery
query has been run against the Controlled Tier.** The lock of 2026-08-26T15:29:49Z was never
published, never cited, and never used to gate an analysis. Every change in this entry is therefore
a repair to a document whose claim to precede the data is untouched by it, and nothing in it could
have been informed by a result, because there is no result. The coefficient in the demonstration
that prompted item 1 came from a **synthetic** matched design built to exhibit the failure; it is
not a number from this study and no number from this study exists.

**What prompted entry 5, item by item, because the two items were found in two different ways.**
Item 1 was found by a **review** of `pipeline/06_analysis_gate.py`, which demonstrated that the
conditional logistic fit accepts a quasi-separated maximum and exports an unbounded odds ratio with
an interval whose upper end is a property of the stopping rule. Perfect separation was already
caught, because it does not converge; quasi-separation, which is the common case in a thin matched
design with a strong exposure, was not caught at all, and the tier this study most plausibly reaches
is exactly the thin one. **The ceiling and its value were decided by the human**, not by the module
and not by this file's author, and the decision is recorded here rather than in a module comment
because a constant that governs whether a result is published is prespecification and belongs inside
the hash. Item 2 was found by **two modules implementing the same definition differently**:
`pipeline/build_all.sql` sets `risk_sets.no_computable_step_signal` from valid days alone with no
structural filter, so a member whose window holds fewer than 2 post-discharge days carries the
co-primary exposure, while `pipeline/06_analysis_gate.py` drops structurally uncomputable rows from
the discrete-time exposure model on the ground that admitting them would put the definitional
condition inside the data condition. Only one of the two can be right, this file had wording that
supported the wrong one, and a column whose meaning differs by surface is a defect in the
specification rather than a disagreement to be settled at run time.

| Date | Section | Change | Reason | Approved by | Superseded SHA-256 |
|---|---|---|---|---|---|
| 2026-08-25 | Header, 1.3, 2.1, 2.3, 2.4, 2.5, 2.6, 2.7, 3.5, 3.6, 4.3, 4.8, 6, 8, 9.1, 9.3, 9.4, 11, 12, 13 | See the itemised list below | Spec-compliance review of the batch-1 build found the plan asserting ownership of five slug vocabularies while containing no slugs, an attrition ladder that existed in three mutually inconsistent forms in other files and in none here, three mandated rungs present nowhere, a disclosure floor stated two ways inside one document, and one covariate cell an analyst could still choose after seeing data | Samer, at the batch-1 fix pass, before any count was seen | `405f04f9218ca4197e5db766de26fadb1ed52030dae1f9c4d9da9efff1d0826e` |
| 2026-08-26 | Header, the element-location table, 2.4, 2.6, 6, 12, 13 | See the itemised list below | A review found `pipeline/02_pregate.py` reading fusion status from non-add-on records only while this file fixed no rule either way, so the pre-gate's stratified ceiling table and the ladder's rung-16 procedure groups could have been built under two different classifications, and a ceiling computed under a different rule from the ladder it bounds is not a ceiling on it | Samer, at his direction, before any count was seen | `b42a6b1fc4d159788af6617e9ab378cb6d02dccca18cae18fdb8f782beab820f` |
| 2026-08-26 | Header, the element-location table, 4.4, 8, 12, 13 | See the itemised list below | The author of `pipeline/06_analysis_gate.py` found 4.4's day-level direct standardization unpublishable under this project's own disclosure rule: it is a weighted average of per-day event counts that are individually below the floor and it carries them inside it, so the figure was either unpublishable or publishable only by giving up the floor. The module named the coarsening it used rather than substituting it silently, and referred the specification back to this file | Samer, at the module-author fix pass, before any count was seen | `a30a7156a851fc7f5f61e36bb35db9d5a7d09905f44ac7e8a1cb34b0da716a29` |
| 2026-08-26 | Header, the element-location table, 2.2, 3.7, 4.4, 5.3, 6, 9.2, 12, 13 | See the itemised list below | A downstream module specifying `pipeline/04_features.py` found that a sensitivity the protocol asks for in its own baseline section, separate weekday and weekend baselines, had been dropped from this file and carried no slug in either sensitivity set, so it could not be run and the omission was silent; and that two weighting and comparison rules this file relies on were undefined at exactly the earliest windows, which are the ones its own collider correction is about | Samer, at the downstream fix pass, before any count was seen | `d507e09c2417c5c2115eb8735139205d86ab5fa321ea056ca58af032cef1aec7` |
| 2026-08-27 | Header, the element-location table, 4.4, 4.9, 5.3, 11, 12, 13 | See the itemised list below | A review of `pipeline/06_analysis_gate.py` demonstrated that the conditional logistic fit accepts quasi-separation and exports an unbounded odds ratio, with no prespecified constant governing whether such a fit may be published at all; and two modules were found implementing the same landmark definition differently, `pipeline/build_all.sql` admitting a structurally uncomputable window into the co-primary exposure while `pipeline/06_analysis_gate.py` drops it, with this file's own wording supporting the reading that puts the definitional condition inside the exposure | Samer, who fixed the ceiling constant himself, before any count was seen | `26285afa5ea279428fea8a07d448860216b2321f554bc6b5216ede4491197b66` |

**What entry 1 changed, itemised.**

1. **Five slug vocabularies added, where there were none.** Procedure groups (2.4), attrition rungs
   (2.6), estimator rungs (3.5), sensitivity rows (6) and subgroups (9.1) each gained a stable slug
   per row as a real column, plus display labels. `local/verify.py` asserts set equality against
   these lists; before this entry every one of those assertions had no left-hand side.
2. **The prespecified subgroup list was written out.** The file previously said only "subgroups
   where every cell clears 20", which is not a list: it is a rule that would have selected the list
   after the counts were seen. Eight subgroups, with slugs, fixed cuts and an explicit
   not-estimable rule, are now in the hash (9.1). This is the most consequential item in the entry.
3. **One authoritative attrition ladder, nineteen rungs (2.6).** Three lists existed and none was
   authoritative. Four rungs that appeared in no list were added: `excl_ed_encounter_not_elective`
   (protocol exclusion criterion 2), `excl_region_unspecified_only` (criterion 3),
   `excl_thoracic_only` (target population) and `excl_not_first_eligible_episode` (the protocol's
   episode-construction rule, which is a real reduction that nothing counted, so the ladder could
   not have closed on the first real run). Protocol exclusion criterion 6 is stated as subsumed by
   the baseline-wear rung. The unit changes and the terminal event count are pinned against the
   closure assert. Trauma, malignancy and infection are settled as one rung, with the reason.
4. **The disclosure floor was made single-valued.** Suppress 1 through 20 inclusive; disclose only
   counts strictly greater than 20, through the single predicate `disclosure.disclosable(n)`. Nine
   superseded thresholds were corrected: the four collapse-ladder triggers (2.5), the four figure
   rules (9.1, 9.3, 9.4) and the device-level folding rule (3.6). The display sentence became "20
   or fewer, suppressed per All of Us dissemination policy", which is factually right for a count of
   exactly 20 where the previous wording was wrong. The tier 3 collision at exactly 20 events is
   named (1.3, 4.8), and the convention that a disclosed 20 stands on a true count of 21 to 29 is
   recorded (section 8, rule 2).
5. **Percentages** are computed from the rounded numerator over the rounded **denominator** (8, rule
   4), so every printed percentage is reproducible from the printed counts.
6. **Protocol inclusion criterion 5 reconciled** against the discharge-anchored window (2.6), so a
   reviewer comparing protocol to Methods does not read it as a second departure.
7. **The device model-family rule was named** (3.6), closing the last cell of the covariate table an
   analyst could still decide after seeing the data.
8. **The two concept-set gap measurements** were made prespecified stop-and-report items with the
   response to every possible value fixed in advance (2.7).
9. **Three stop conditions added** (11, items 8 to 10) covering slug-set equality, subgroup-list
   integrity and ladder closure.

**What entry 2 changed, itemised.**

1. **The fusion-status evidence rule was written down** (2.4). Fusion status reads all qualifying
   evidence in the same-day bundle, add-on and instrumentation codes included. Fourteen of the
   sixteen add-on codes in the locked set carry `procedure_class = 'fusion'`; the two readings of
   the rule differ only where the primary arthrodesis code was never captured; and under the
   reading this entry rejects, an episode whose only fusion evidence is an add-on code would have
   been analysed on the decompression arm. Before this entry the plan fixed no rule either way,
   which is why two modules could disagree without either of them being wrong against the plan.
2. **The add-on rung was given its scope in prose** (2.6, step 9), so that the two rules cannot be
   read as contradicting each other. An add-on cannot establish that an operation happened, and an
   add-on-only bundle is still excluded and counted at rung 9. Whether an operation happened and
   which arm it belongs to are separate questions, and only the second one changed.
3. **One supplementary sensitivity row was added**, `fusion_status_non_add_on_only` (6), carrying
   the reading 2.4 declines. It is **not** a member of the fourteen plotted rows that
   `local/verify.py` asserts set equality against, and the section says so explicitly. Its purpose
   is to bound how much of the primary contrast rests on episodes whose fusion status comes only
   from an add-on code. This is the only slug added anywhere by this entry, and no slug was
   removed or renamed, so all five asserted vocabularies are unchanged.
4. **The region half of the question was recorded as settled** (2.4). Every add-on in the locked
   set carries `region = 'unspecified'`, so an add-on can neither supply a region nor override a
   cervical, lumbar or thoracic assignment. Nothing about region changes, and the paragraph exists
   so that it is not reopened alongside the fusion question.
5. **The pre-gate and the ladder were pinned to one rule** (2.4). The stratified ceiling table of
   `pipeline/02_pregate.py` and the procedure groups at rung 16 of 2.6 use the rule stated here,
   because comparability between those two tables is the entire purpose of the pre-gate.
   `pipeline/02_pregate.py` is corrected against this file rather than the reverse.
6. **Two reviewer objections were recorded** (12), one for each direction of the conflation this
   entry anticipates.

`prespecification/EXPORT-CONTRACT.md` section 11.3 transcribes the supplementary rows and counts
them as eight. It is amended to nine in the same commit, under the header rule that where a list
here and a list in the contract disagree, this file wins. The set `local/verify.py` asserts equality
against is untouched: it is still the fourteen plotted rows, and the supplementary rows are still
excluded from it by name.

**What entry 3 changed, itemised.**

1. **The weekday and weekend baseline sensitivity was written down** (2.2), where the protocol asks
   for it and this file had kept only the day-of-week composition. Two medians over the same 23-day
   window, minima of 5 valid weekday days and 2 valid weekend days set from what the window can
   supply, a day-type-matched deficit, an explicit rule that an episode with valid days in only one
   half of the week leaves this row and nothing else, and four named columns on the derived
   `baseline` table with the null-never-zero discipline the rest of the baseline already carries.
   The reading of `baseline_dow_counts` was fixed at the same time, as valid baseline days rather
   than calendar days, with two identities that `pipeline/04_features.py` asserts, because the
   split's counts have to agree with the composition array or one of the two is wrong.
2. **One supplementary sensitivity row was added**, `baseline_weekday_weekend_split`, display label
   **Separate weekday and weekend baselines** (6). **It is supplementary and not a fifteenth plotted
   row**, and the choice is argued in 6 rather than taken by default: day of week is already handled
   twice inside the primary, as a fixed effect and by standardization over each episode's calendar
   alignment, so this row corroborates an existing handling instead of testing an unhedged choice,
   and its reference moves within an episode, which puts its estimate in a unit close to but not
   identical with the shared forest axis. **The fourteen plotted rows are byte-identical and in
   identical order**, so `local/verify.py`'s set-equality assertion is unaffected. The supplementary
   count moves from nine to ten, which `prespecification/EXPORT-CONTRACT.md` section 11.3 must
   follow in the same commit; its checker will report a failure until it does, and that failure is
   the check working. This is the only slug added anywhere by this entry, no slug was removed or
   renamed, and the plotted vocabulary is untouched.
3. **The landmark observation weight was made defined everywhere it is claimed** (4.4, with a
   pointer from 3.7). The weight's main predictor, the lagged wear fraction, exists only on the
   post-discharge grid, so it has no input for a member whose own landmark day is 1 or less, which
   the day-of-week relaxation of 4.7 and the partial-window secondary of 4.3 both produce. Those
   members are excluded from the weighted sensitivity and from nothing else, keeping their place in
   the primary and in `beta_N`. The two alternatives were named and rejected in writing, carrying
   the predictor back onto a preoperative and inpatient grid that is a different process, and
   assigning the marginal weight, which would have made an unsupported assumption invisible in every
   output. Three counts are obliged, including the matched sets that lose every control, which is
   the one that cannot be recovered from the member count.
4. **The computable-ratio comparison was moved onto a full-cohort day-indexed panel** (4.4), because
   the sampled risk sets and the first-event surface are both selected on wear and on the calendar,
   which is the collider the comparison exists to expose, one level up. The panel gives it a real
   denominator and turns it into an event rate per episode day; the price is that it is unmatched,
   so it is reported crude and standardized to post-discharge day, and neither version is labelled
   causal. The **data** and **definitional** landmark conditions stay distinct on the panel and
   their counts are never summed, because one is an exposure and the other is an exclusion.
5. **Sensitivities fitted on a subset now print their own denominator** (9.2). A contrast printed
   against the analytic `n` when it was fitted on fewer episodes is a mislabelled number and the
   estimate does not reveal it. Table 2's footer carries the row's own `n` and the count of episodes
   it could not use, for every such row, and says so explicitly where a row's set is the full
   cohort. The split baseline forced the rule to be written; it applies to the alternative baseline
   windows, the four wear definitions, the baseline floor, the device-change row and the
   complete-window row alike.
6. **Four reviewer objections were recorded** (12), one for the dropped protocol sensitivity and
   three for the places where a fix to a bias could have quietly reintroduced it.

**What entry 4 changed, itemised.**

1. **The strata the collider comparison is standardized over were named, and the day grid was ruled
   out in this file rather than only in a module** (4.4). The standardization runs over six recovery
   day bands, written out with their boundaries and their display labels: the accrual window of
   post-discharge days 1 to 35 in calendar weeks, plus the display tail of Figure 2 as a sixth band.
   They are the same six bands `pipeline/04_features.py` already reports its person-day tables over,
   they were fixed before any count existed, and they do not move in response to what a run returns.
   The reason the day grid is inadmissible is given as a **disclosure** reason and not a statistical
   one, because a reviewer asking why the comparison is standardized coarsely is owed the real
   answer rather than an appeal to smoothing or to stability. This is the substantive item in the
   entry: before it, the plan specified a number that could not be printed.
2. **The suppression rule was specified, and so was what is reported when it fires** (4.4). The
   standardized rate for a condition is produced only when every band contributing days to that
   condition clears the floor; otherwise that condition's standardized rate is withheld and the
   standardized rate ratio is withheld with it. The two conditions are judged separately. A band
   contributing no days is dropped rather than treated as a suppression, the remaining weights are
   renormalized, and the covered share is printed so the renormalization is visible. When the
   standardization is withheld the **crude comparison is reported alone**, with both denominators
   and a sentence saying what was withheld and why; the row is not dropped, is not replaced by a
   finer stratification, and is not replaced by a model-based adjustment. What narrows is the claim:
   no statement is made about how much of the difference post-discharge day explains.
3. **Rule 4 of section 8 was extended to rates** (8). A rate is computed from the rounded numerator
   over the rounded denominator and is not produced when its numerator is not disclosable, for the
   same two reasons the rule already gave for a percentage. This is a **presentation** rule and it
   changes no estimand. The rule numbers in section 8 are unchanged, because other files cite them
   by number.
4. **The panel's three day classes were written down as a partition, and the never-summed rule was
   restated across all three** (4.4). Computable, data and definitional are the three classes; they
   partition the panel, and `pipeline/06_analysis_gate.py` asserts that they do before it
   standardizes anything, because band weights taken from the panel's day distribution describe a
   base the three classes have to cover exactly. That assert is an internal consistency check that
   produces no published number, and the file now says so, so it cannot be read as licence to add
   the classes together. The comparison itself is drawn between the computable and data conditions
   and between those two only; the definitional count is printed beside it so a reader can see it is
   excluded rather than folded in, and it is never added to the row above it.
5. **Two reviewer objections were recorded** (12), one edited to match the coarsening and one added
   for the obvious hostile reading of it, that week-wide bands were chosen because narrower strata
   gave an unwelcome answer.
6. **No slug was added, removed or renamed anywhere by this entry.** All five vocabularies owned by
   this file are byte-identical to the version this entry supersedes, so the set-equality assertions
   in `local/verify.py` and in `prespecification/EXPORT-CONTRACT.md` are unaffected. The six
   recovery day bands are **not** a sixth vocabulary: they carry display labels and no slugs,
   nothing keys on them, and no set-equality assertion runs against them.
7. **The rest of the file was swept for the same failure mode and it is not present elsewhere.** The
   defect is specific to a directly standardized or weighted quantity whose weights are per-day,
   per-stratum or per-cell **counts**, because only those carry suppressed counts inside a published
   number. The other aggregates in this plan are not of that kind and each was checked by name: the
   covariate-standardized marginal debt of 3.1 and 3.8 and the standardized absolute risk of 4.6 are
   g-computations that average a fitted value over individual episode or person-day records, so
   their weights are per-record and the quantity averaged is a model prediction rather than a count;
   rung 5 of 3.5 averages a continuous deficit under observation weights, not counts; the unadjusted
   column of Table 2 in 9.2 is a median, already bound by rule 2 of 9.3; the per-day medians and
   quartiles of Figure 2 are bound by rules 1 and 2 of 9.3, which drop the day outright rather than
   degrade it; and the stratum cells of 9.4 are bound by the complementary suppression of rule 5 of
   section 8. Recording the sweep rather than only its one hit is deliberate: a reader checking this
   class of defect should be able to see it was looked for everywhere, not just where it was found.

**What entry 5 changed, itemised.**

1. **A coefficient ceiling was prespecified for every logistic fit in Arm A** (4.9, new). A fit is
   refused when any one of its coefficients has an absolute value greater than 10, the constant
   named `MAX_ABS_COEFFICIENT`, which on the odds-ratio scale is about 22,000. Ten is the
   conventional separation-detection threshold in the logistic-regression literature: generous
   enough that no plausible real effect in this design is refused, tight enough that a runaway fit
   cannot reach an exported surface. The refusal is at the level of the fit rather than of the one
   coefficient, because a coefficient at the ceiling means a near-degenerate information matrix and
   no standard error from that fit is trustworthy. **This is the substantive item in the entry:
   before it, whether an unbounded odds ratio could be published was decided by whichever stopping
   rule the optimizer happened to use, which is not a prespecified rule at all.**
2. **A refusal returns a named reason and never a clipped number** (4.9). The row prints "not
   estimable (separation)", slug `not_estimable_separation`, and the value that tripped the ceiling
   is not printed, not as a bound and not in a footnote, because printing it is the clipped number
   arriving by a second route. Two counts are obliged: fits refused at the ceiling by analysis slug,
   and resamples above the ceiling out of `B` for every fit that produced an interval.
3. **The ceiling is stated to be one-directional, so a reviewer can check that it cannot manufacture
   a result** (4.9). It has exactly one action, replacing a number with a refusal. It has no branch
   that emits an estimate, changes one, or widens or narrows an interval, so it cannot move a
   published number toward the null or away from it. The constant was **not** tuned to the case that
   prompted it: the demonstration sat at 8.961, below the ceiling, and a fit like it still prints. A
   threshold chosen to catch the one example that prompted it would be a threshold fitted to one
   draw.
4. **The point fit and the bootstrap resamples were decided rather than deferred** (4.9). A
   separated point fit refuses the fit. A separated resample is **retained and counted, never
   discarded**, because discarding the resamples that ran furthest from zero would trim the tail the
   percentile interval is read from and would narrow a published interval, which is the one thing a
   suppression rule must never do; this is a stated departure from the discard-and-count rule of
   3.8, which applies to a resample that produced no number rather than one that produced too large
   a number. Above a 25% share the interval and the point estimate are both refused, and 25% is the
   share 3.8 and trigger T4 of 3.5 already use rather than a second constant.
5. **The definitional condition was put outside the co-primary exposure on every surface** (4.4,
   with 5.3 and 12 following it). The landmark is `T = E - 3` over the window `T-2` to `T`, so a
   landmark day of 1 or less holds fewer than 2 post-discharge days and **is** the definitional
   condition rather than a threshold near it. Such a member carries no `N`, contributes nothing to
   `beta_N`, and leaves the exposure model on the conditional fit of 4.5, the discrete-time model of
   4.6, the `landmark_daily` panel and the `risk_sets` table alike. `N` exists to capture
   participants who stopped wearing the device; a window uncomputable because it straddles discharge
   is uncomputable by the calendar, and the calendar is already this design's single time scale, so
   folding it in would contaminate the exposure with a quantity the design already conditions on.
6. **The wording this file previously carried was wrong for exactly one route, and the entry says
   which** (4.4). Route (b), the partial-window secondary of 4.3, is self-consistent and unaffected:
   it reads day 4 events back in deliberately, under its own single-eligible-day rule, labelled
   separately and never pooled with the primary. Route (a) is the one the old wording got wrong: a
   day-of-week-relaxed **control** in the **primary** at post-discharge day 3 or 4 sits at a
   landmark day of 0 or 1 and has no exposure window. It is dropped from its risk set as a member
   and counted. It does not leave at rung 18, because rung 18 is an event rung and a sampled control
   is not an event, so the drop is counted in 4.4 where the ladder cannot count it.
7. **The weight rule of entry 3 was re-scoped rather than reversed** (4.4, 5.3, 12). Its content is
   unchanged: a member whose landmark day is 1 or less has no weight, because the predictor the
   weight model runs on does not exist there, and the two rejected alternatives stand as written.
   What changed is that such a member has now already left the exposure model for a prior and
   different reason, so in the primary the weight rule has nothing left to exclude, and it does its
   work where such a member is deliberately read back in. Item 3 of entry 3 is superseded on this
   point and is left standing as written, because an amendment log that edits its own history is
   worth nothing.
8. **A stop condition was added** (11, new condition 11). Publishing a fit above the ceiling, or
   raising, lowering or selectively applying the ceiling once a run has produced a number, halts the
   analysis. The existing ten conditions are unchanged and unrenumbered, because other files cite
   them by number.
9. **One new slug was created and it is not this file's to own.** `not_estimable_separation`, display
   sentence "not estimable (separation)", belongs to the suppression-reason vocabulary of
   `prespecification/EXPORT-CONTRACT.md` section 7.5 and must be added there in the same commit;
   its checker will report a failure until it is, and that failure is the check working. **All five
   vocabularies owned by this file are byte-identical to the version this entry supersedes**, so the
   set-equality assertions in `local/verify.py` and in the export contract are unaffected, and stop
   condition 8 is not engaged. No existing reason could have carried a separated fit: the cell size
   was fine, the data were available, the tier permitted the analysis, and the fit **converged**,
   which is the property that makes quasi-separation dangerous in the first place.
10. **`pipeline/build_all.sql` must change to match, and the obligation is recorded here rather than
    left to a module author to infer.** Its `risk_sets` stage sets `no_computable_step_signal` from
    valid days alone, with no structural filter, so a member at a landmark day of 1 or less is
    currently given the co-primary exposure. Under the header rule that code is corrected against
    this file. `pipeline/06_analysis_gate.py` already drops structurally uncomputable rows from the
    discrete-time model and its reasoning is the reading prespecified here, so that module needs no
    change on item 2; it does need the ceiling of 4.9, which is being implemented in the same pass.
11. **Four reviewer objections were touched** (12), one edited so that it no longer claims these
    members stay in the co-primary exposure, and three added: one for the definitional condition,
    and two for the ceiling, including the hostile reading that a ceiling is how an unwelcome result
    gets buried.
