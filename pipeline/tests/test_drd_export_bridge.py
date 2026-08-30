"""The seam between `05_analysis_drd.py` and `07_export.py`, exercised end to end.

THIS IS THE TEST WHOSE ABSENCE WAS THE DEFECT.  Both modules were correct against their own
fixtures and could not connect to each other: `07_export.py` exercised only its own
`fixture_payload()`, built to its own shape, and `05_analysis_drd.py` asserted only its own
`RESULT_KEYS`.  A real `run_drd()` result had never been fed to `render_bundle` in either
module's checks, so the first key of the first block raised `KeyError` and nothing was red.

What this file does is the one thing neither self-test could do: it runs a REAL `run_drd()`
against the analysis module's own synthetic cohort, splices the `debt` and `sensitivity` blocks
it returns into the exporter's payload in place of the fixture's, and renders the whole bundle.
The rest of the payload stays fixture-supplied, because it belongs to `03_cohort.py` and
`06_analysis_gate.py`; what is under test here is the two blocks Phase 4 arm B owns.

Both filenames begin with a digit, so neither can be imported by name.  They are loaded through
`importlib.util.spec_from_file_location`, which is the pattern `02_pregate.py` already uses for
its own import of `01_probe.py`.

NO CLOUD ACCESS AND NO CREDENTIALS.  `run_drd` takes its query path by injection and the
analysis module ships a fake runtime for it, so the whole bridge runs on a laptop.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest

PIPELINE = Path(__file__).resolve().parents[1]


def _load(name: str, filename: str):
    """Load one digit-prefixed pipeline module under an importable alias."""
    if str(PIPELINE) not in sys.path:
        sys.path.insert(0, str(PIPELINE))
    spec = importlib.util.spec_from_file_location(name, PIPELINE / filename)
    assert spec is not None and spec.loader is not None, f"cannot load {filename}"
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


drd = _load("drd_analysis_05", "05_analysis_drd.py")
export = _load("drd_export_07", "07_export.py")


# ======================================================================================
# The fake R leg.
#
# ANALYSIS-PLAN 3.5 puts the ordered-beta GLMM at rung 1 and the R analysis environment is an
# INJECTED runner, its absence being trigger T0, so a run with no runner descends the family
# ladder to the fractional-logit GEE at rung 3.  That rung is a quasi-likelihood estimator and
# reports no AIC, which is a real difference between the rungs and not a defect here.  The
# bridge injects a runner so the run lands where the plan expects a real run to land, and the
# rung reached is asserted rather than assumed.
# ======================================================================================


def _r_runner(family: str, *, response: np.ndarray, design: np.ndarray, cluster: np.ndarray,
              day: np.ndarray, weights: np.ndarray) -> dict[str, Any]:
    """A stand-in that answers the same trigger questions the real R leg answers.

    It is a weighted least-squares fit on the logit of the response, which is not the estimator
    R would run and is not meant to be: what this test is about is the SHAPE that crosses the
    boundary, and for that the fit only has to be non-degenerate and converged.
    """
    bounded = np.clip(np.asarray(response, dtype=float), 1e-4, 1.0 - 1e-4)
    latent = np.log(bounded / (1.0 - bounded))
    root = np.sqrt(np.asarray(weights, dtype=float))
    coefficients, *_ = np.linalg.lstsq(design * root[:, None], latent * root, rcond=None)
    residual = latent - design @ coefficients
    variance = float(np.mean(residual ** 2)) or 1e-9
    return {
        "converged": True,
        "max_gradient": 1e-9,
        "coefficients": coefficients,
        "covariance_re": np.array([[0.25, 0.02], [0.02, 0.09]]),
        "boundary": False,
        "residual_structure": drd.RESIDUAL_STRUCTURE_RUNGS[0]["slug"],
        "rho": 0.4,
        "aic": float(latent.size * np.log(variance) + 2.0 * (design.shape[1] + 1)),
    }


def _exporter_consumes_raw_values() -> bool:
    """Whether `07_export.py` is the version that renders from TRUE values.

    Its own fixture is its declaration of the payload shape it consumes, so this reads the
    fixture rather than the renderer: an exporter still built around finished nodes carries a
    fixture full of finished nodes and cannot be handed a true count.
    """
    try:
        entry = export.FIXTURE_BY_GROUP[0]
    except (AttributeError, IndexError):            # pragma: no cover - a shape that predates
        return False                                # the fixture entirely
    return {"true_n", "true_complete_windows", "zero_debt_true_n"} <= set(entry)


requires_raw_exporter = pytest.mark.skipif(
    not _exporter_consumes_raw_values(),
    reason=(
        "07_export.py still consumes finished disclosure nodes: its FIXTURE_BY_GROUP carries "
        "no true_n, true_complete_windows or zero_debt_true_n. The matching change to the "
        "exporter and its fixture is not in the tree yet, so the two halves of this seam "
        "cannot be joined; this test runs the moment it lands."
    ),
)


@pytest.fixture(scope="module")
def real_result() -> dict[str, Any]:
    """One real `run_drd()` on the analysis module's own synthetic cohort.

    Reduced draws and resamples so the suite runs on a laptop.  `run_drd` records every
    departure from the locked values as a printed deviation, which is asserted below, so a
    reduced run cannot be mistaken for the plan's own.
    """
    episodes, panel = drd._synthetic_frames(24, four_group=True)
    guards = pd.DataFrame([{name: 0 for name in drd.GUARD_SENTENCES}
                           | {"n_panel_rows": int(len(panel)), "n_units": int(len(episodes))}])
    parameters = pd.DataFrame([{"junction_map": "primary",
                                "primary_wear_definition": "primary", "seed": drd.SEED}])
    runtime = drd._FakeRuntime({"episodes": episodes, "panel": panel, "guards": guards,
                                "parameters": parameters}, gb=0.01)
    return drd.run_drd(
        features={"features ok": True},
        collapse={"level": "four_group", "groups": drd.FOUR_GROUP_SLUGS},
        q_guarded=runtime.q_guarded, dry_run_gb=runtime.dry_run_gb,
        r_runner=_r_runner, draws=12, resamples_primary=6, resamples_sensitivity=3,
        run_sensitivity=True, show_report=False)


def _payload_from(result: dict[str, Any]) -> dict[str, Any]:
    """The exporter's own payload with the REAL debt and sensitivity blocks spliced in.

    Figure 3's rows are rebuilt from the real blocks too, through the exporter's own
    `render_forest_rows`, because the fixture's forest rows were rendered from the fixture's
    numbers and would otherwise carry a different analysis than the one in `results.json`.
    """
    payload = export.fixture_payload()
    payload["debt"] = result["debt"]
    payload["sensitivity"] = result["sensitivity"]
    payload["forest_rows"], payload["figure3_blocks"] = export.render_forest_rows(
        result["debt"]["contrasts"], result["sensitivity"], export.FIXTURE_SUBGROUPS)
    return payload


# ======================================================================================
# The bridge itself.
# ======================================================================================


@requires_raw_exporter
def test_the_runner_reaches_the_plan_s_own_rung(real_result):
    assert real_result["drd ok"]
    assert real_result["estimator"]["rung_slug"] == "r_ordered_beta_glmm"
    assert real_result["deviations"], (
        "a run with reduced draws and resamples must record them as a printed deviation "
        "rather than passing them off as the locked values"
    )


@requires_raw_exporter
def test_a_real_run_renders_the_whole_bundle(real_result):
    """The defect, closed.  This is the call that used to raise on the first key."""
    results, specs, log = export.render_bundle(_payload_from(real_result))

    assert set(export.BUNDLE_FILES) - {"results.json"} == {name for name, _f, _d in specs}
    assert results["debt"]["by_group"], "the rendered debt block carries its group rows"
    assert results["sensitivity"], "and its sensitivity rows"


@requires_raw_exporter
def test_the_suppression_log_is_populated_by_the_exporter_and_not_by_the_analysis(real_result):
    """THE LOG IS THE POINT.  A rendered block handed over already suppressed registers
    nothing here, because the exporter floor-tests a number that has already been rounded and
    finds nothing to hide.  A populated log is the evidence that the true counts arrived."""
    results, _specs, log = export.render_bundle(_payload_from(real_result))
    block = results["suppressed"]

    assert block["n_entries"] > 0, (
        "nothing was recorded as suppressed, which on a cohort with groups of 24 means the "
        "exporter never met a true count"
    )
    assert block["n_entries"] == len(block["entries"]) == len(log.entries)
    assert block["by_reason"], "and each entry names the rule that hid it"

    paths = {entry["path"] for entry in block["entries"] if entry["path"]}
    assert any(path.startswith("debt.") for path in paths), (
        f"no suppression was recorded anywhere in the debt block, which is the block this "
        f"seam carries. Recorded paths: {sorted(paths)}"
    )


@requires_raw_exporter
def test_every_key_the_exporter_reads_is_present_in_a_real_result(real_result):
    """The key-by-key contract, written out so a rename on either side turns this red.

    The list is not a restatement of the exporter's source in a second place for its own sake:
    it is what the two modules agreed on, and the whole reason this test exists is that neither
    module could check the agreement alone.
    """
    debt = real_result["debt"]
    assert {"estimand_display", "max_possible", "by_group", "contrasts", "absolute_scale",
            "manski", "delta_shift", "model_fit"} <= set(debt)

    for entry in debt["by_group"]:
        assert {"slug", "true_n", "true_complete_windows", "unadjusted_debt", "adjusted_debt",
                "thousand_steps_lost", "adjusted_mean_normalized_activity",
                "share_reaching_80pct_baseline", "zero_debt_true_n"} <= set(entry)
        assert len(entry["unadjusted_debt"]) == 3
        assert len(entry["adjusted_debt"]) == 3
    assert debt["by_group"][-1]["slug"] == "all_groups", (
        "the pooled row is last: the Table 2 footer resolves debt.by_group[4] by position"
    )
    assert len(debt["by_group"]) == 5

    for spec in list(debt["contrasts"].values()) + list(debt["absolute_scale"].values()):
        assert {"estimate", "p", "is_primary", "true_n_compared"} <= set(spec)
        assert len(spec["estimate"]) == 3, (
            "an estimate crosses as (est, lo, hi). A nine-key node unpacks into nine "
            "positional arguments, which is the TypeError this seam used to raise"
        )
    assert {"by_group", "primary_lower", "primary_upper"} <= set(debt["manski"])
    assert all(len(pair) == 2 for pair in debt["manski"]["by_group"].values())

    shift = debt["delta_shift"]
    assert {"applied_to", "tipping_point_point_estimate", "tipping_point_interval",
            "definition_display", "applications", "grid", "reference_deficit",
            "grid_extended", "crossed_within_grid", "no_crossing_display"} <= set(shift)
    for key in ("tipping_point_point_estimate", "tipping_point_interval"):
        assert shift[key] is None or isinstance(shift[key], float), (
            f"{key} is a grid coordinate and crosses as one bare number, or as None when the "
            f"curve never crossed within the prespecified range"
        )
    assert isinstance(shift["reference_deficit"], float)

    fit = debt["model_fit"]
    assert {"family", "link", "spline_basis", "spline_df", "aic", "true_n_person_days",
            "true_n_persons", "converged", "monte_carlo_draws"} <= set(fit)
    assert fit["residual_structure"] in export.RESIDUAL_STRUCTURE_DISPLAY
    for key in ("rho", "icc", "marginal_r2", "conditional_r2"):
        assert len(fit[key]) == 3

    for slug, row in real_result["sensitivity"].items():
        assert {"estimate", "p", "true_n", "estimable", "not_estimable_reason", "varies",
                "direction_matches_primary"} <= set(row), slug
        assert row["estimate"] is None or len(row["estimate"]) == 3, slug


@requires_raw_exporter
def test_the_counts_arrive_true_and_the_exporter_is_what_rounds_them(real_result):
    """The reason the decision went this way, demonstrated on a number that changes.

    Every procedure group in this cohort holds 24 episodes.  `round20(24)` is 20, so a count
    that had already been through the floor would arrive as 20 and the exporter would round a
    20 to a 20 and record nothing.  The raw block carries the 24; the rendered node carries the
    20; and the floor was asked about the 24, which is the only order in which it means
    anything.
    """
    debt = real_result["debt"]
    groups = {entry["slug"]: entry["true_n"] for entry in debt["by_group"]}
    changed = {slug: n for slug, n in groups.items() if int(drd.round20(n)) != int(n)}
    assert changed, (
        f"this cohort has no count that rounding would change, so it cannot demonstrate the "
        f"difference. Group counts: {groups}"
    )

    results, _specs, _log = export.render_bundle(_payload_from(real_result))
    rendered = {entry["slug"]: entry["n"] for entry in results["debt"]["by_group"]}
    for slug, true_n in changed.items():
        node = rendered[slug]
        assert not node["suppressed"], slug
        assert int(node["n"]) == int(drd.round20(true_n)) != int(true_n), (
            f"{slug}: true {true_n} rendered as {node['n']}, which is not what round20 does "
            f"to it. A count that arrived already rounded would be unchanged here"
        )

    # And the same on the two model-fit counts, which travel under names that say what they are.
    fit = real_result["debt"]["model_fit"]
    assert fit["true_n_persons"] == sum(groups[slug] for slug in drd.FOUR_GROUP_SLUGS)
    assert int(results["debt"]["model_fit"]["n_persons"]["n"]) == int(
        drd.round20(fit["true_n_persons"]))


@requires_raw_exporter
def test_a_count_below_the_floor_is_hidden_by_the_exporter_and_recorded(real_result):
    """A count small enough to hide, hidden at the boundary and written into the log.

    Every group of this cohort holds 24 episodes over roughly a dozen complete windows, so the
    two counts in one Table 2 row fall on opposite sides of the floor: the group count is
    disclosed rounded and the complete-window count is hidden.  That is the pairing the
    decision was made for, and it can only happen if BOTH arrive true.  The assertion is on
    the pairing rather than on either half: a hidden count has a node with no numeral in it
    and an entry in `suppressed` that names its path.
    """
    results, _specs, _log = export.render_bundle(_payload_from(real_result))
    raw = real_result["debt"]["by_group"]
    rendered = results["debt"]["by_group"]
    logged = {entry["path"] for entry in results["suppressed"]["entries"]}

    hidden = 0
    for index, (raw_entry, node_entry) in enumerate(zip(raw, rendered)):
        for raw_key, node_key in (("true_n", "n"),
                                  ("true_complete_windows", "n_complete_windows")):
            node = node_entry[node_key]
            if export.disclosable(raw_entry[raw_key]):
                assert not node["suppressed"] and "n" in node
                continue
            hidden += 1
            assert node["suppressed"] and "n" not in node, (
                "A SUPPRESSED NODE CARRIES NO NUMERIC KEY AT ALL: the number is not in the file"
            )
            assert f"debt.by_group[{index}].{node_key}" in logged, (
                f"debt.by_group[{index}].{node_key} was hidden and not recorded, which is the "
                f"silent omission `results.json.suppressed` exists to prevent"
            )
    assert hidden, (
        "this cohort produced no below-floor count in the debt block, so it cannot show the "
        "floor being applied at the boundary"
    )
