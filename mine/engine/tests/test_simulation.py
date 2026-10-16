"""
End-to-end (but still pure-Python, no network) checks on simulation.py: run the Simulation class
for a batch of ticks under different scenarios and check the documented causal direction actually
comes out the other end of the full truck-cycle / plant / KPI pipeline -- not just the isolated
model functions (those are covered in test_models.py).

Run with: python -m pytest tests/test_simulation.py -v   (or run this file directly)
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scenarios import ScenarioFields, resolve_effective
from simulation import Simulation

DT_S = 5.0          # one sim tick = 5 simulated seconds
N_TICKS = 2000       # ~2.8 simulated hours -- enough for several full truck cycles


def _run(scenario_id: str, seed: int = 42) -> Simulation:
    sim = Simulation(seed=seed, label=scenario_id)
    eff = resolve_effective(ScenarioFields(active_scenario=scenario_id))
    for _ in range(N_TICKS):
        sim.step(DT_S, eff)
    return sim


def test_baseline_runs_without_crashing_and_moves_material():
    sim = _run("none")
    assert sim.ore_total_t > 0.0
    assert sim.waste_total_t > 0.0
    assert sim.cu_output_total_t > 0.0


def test_all_scenarios_run_without_crashing():
    from scenarios import VALID_SCENARIOS
    for sid in VALID_SCENARIOS:
        sim = _run(sid, seed=7)
        assert sim.sim_time_h > 0.0


def test_shovel_failure_drops_blend_grade_and_cu_output_vs_baseline():
    base = _run("none")
    failure = _run("shovel_failure")
    # 03_domain.md §11-S1: with shovel-s2 down, remaining ore comes from shovel-s1 (0.45%) only,
    # so the realised mill feed grade should end up lower than the baseline blend.
    assert failure.last_mill_feed_grade <= base.last_mill_feed_grade + 1e-6
    assert failure.cu_output_total_t < base.cu_output_total_t


def test_dispatch_fixed_moves_less_material_than_dynamic_baseline():
    dynamic = _run("none")           # default dispatch_policy = "dynamic"
    fixed = _run("dispatch_fixed")
    # 03_domain.md §11-S11: fixed/locked dispatch should move less material than dynamic LP/MTCT
    # dispatch over the same elapsed time (because an imbalanced shovel can't be relieved).
    assert fixed.ore_total_t + fixed.waste_total_t <= dynamic.ore_total_t + dynamic.waste_total_t


def test_fleet_minus_2_moves_less_material():
    full = _run("none")
    reduced = _run("fleet_minus_2")
    assert reduced.ore_total_t + reduced.waste_total_t < full.ore_total_t + full.waste_total_t


def test_price_drop_cuts_margin():
    base = _run("none")
    shock = _run("price_drop")
    assert shock.last_kpi["nsr_usd_h"] < base.last_kpi["nsr_usd_h"]


def test_trolley_assist_reduces_diesel_rate():
    base = _run("none")
    trolley = _run("trolley_assist")
    assert trolley.last_kpi["fuel_l_h"] <= base.last_kpi["fuel_l_h"] + 1e-6


def test_weather_cold_snap_raises_idle_fuel_multiplier():
    sim = _run("weather_cold_snap")
    assert sim.weather.is_extreme_cold
    assert sim.weather.idle_fuel_multiplier() > 1.0


def test_slope_alarm_closes_main_ramp():
    eff = resolve_effective(ScenarioFields(active_scenario="slope_alarm"))
    assert eff.close_main_ore_ramp is True


def test_shovel_down_id_accepts_full_thing_id():
    eff = resolve_effective(ScenarioFields(active_scenario="shovel_failure",
                                           shovel_down_id="kz.kyzyltas.mine:shovel-s2"))
    assert eff.shovel_down_id == "shovel-s2"


def test_undo_ends_scenario_imposed_outages():
    import dataclasses
    from scenarios import BASELINE_EFFECTIVE
    for sid, shovel in (("shovel_failure", "shovel-s2"), ("blast_delay", "shovel-s1")):
        eff = resolve_effective(dataclasses.replace(ScenarioFields(), active_scenario=sid, run_id="r1"))
        sim = Simulation(seed=42, label="undo")
        for _ in range(300):
            sim.step(12, eff)
        assert sim.maint.is_down(shovel) or sim.gas_block_until_h.get(shovel, -1) > sim.sim_time_h, sid
        for _ in range(3):
            sim.step(12, BASELINE_EFFECTIVE)
        assert not sim.maint.is_down(shovel), sid
        assert sim.gas_block_until_h.get(shovel, -1) <= sim.sim_time_h, sid


def test_baseline_clone_measures_only_the_new_scenario():
    import dataclasses
    from scenarios import BASELINE_EFFECTIVE
    real = Simulation(seed=42, label="real")
    earlier = resolve_effective(dataclasses.replace(ScenarioFields(), active_scenario="blast_intensify", run_id="a"))
    for _ in range(600):
        real.step(12, earlier)
    base = real.clone_as_baseline()
    assert base.last_kpi == real.last_kpi  # identical at the moment of the switch
    eff = resolve_effective(dataclasses.replace(ScenarioFields(), active_scenario="shovel_failure", run_id="b"))
    for _ in range(300):
        real.step(12, eff)
        base.step(12, BASELINE_EFFECTIVE)
    assert real.last_kpi["cu_mined_tph"] < base.last_kpi["cu_mined_tph"]
    # Same scenario on both sides -> identical futures (random streams were copied too).
    twin = real.clone_as_baseline()
    for _ in range(300):
        real.step(12, eff)
        twin.step(12, eff)
    assert abs(real.last_kpi["ore_mined_tph"] - twin.last_kpi["ore_mined_tph"]) < 1e-6


def test_ore_mass_balance_closes():
    import dataclasses
    sim = Simulation(seed=42, label="mass")
    eff = resolve_effective(dataclasses.replace(ScenarioFields(), active_scenario="hard_ore_domain", run_id="m"))
    piles = lambda: sim.stockpile_rom.mass_t + sim.stockpile_crushed.mass_t + sim.stockpile_hg.mass_t
    start, milled = piles(), 0.0
    for _ in range(12 * 300):
        sim.step(12, eff)
        milled += sim.last_sag_tph * 12 / 3600
    assert abs(start + sim.ore_total_t - milled - piles()) < 1.0


def test_ball_mill_outage_halves_sag_throughput():
    from scenarios import BASELINE_EFFECTIVE
    sim = Simulation(seed=42, label="ball")
    for _ in range(300):
        sim.step(12, BASELINE_EFFECTIVE)
    a = sim.maint.assets["mill-ball-01"]
    a.down, a.down_remaining_h, a.down_mode = True, 5.0, "other"
    for _ in range(10):
        sim.step(12, BASELINE_EFFECTIVE)
    assert sim.last_sag_tph <= 1706.0 * 1.2 + 1e-6
    assert sim.last_mill_power_kw["mill-ball-01"] == 0.0


def test_fixed_dispatch_waits_for_radio_reassignment():
    import dataclasses
    from scenarios import BASELINE_EFFECTIVE
    sim = Simulation(seed=42, label="fixed")
    for _ in range(300):
        sim.step(12, BASELINE_EFFECTIVE)
    eff = resolve_effective(dataclasses.replace(ScenarioFields(), active_scenario="shovel_failure",
                                                run_id="f", dispatch_policy="fixed"))
    for _ in range(600):
        sim.step(12, eff)
    assert any("reassigned by radio" in e for e in sim.events)


def test_custom_scenario_applies_twin_fields():
    eff = resolve_effective(ScenarioFields(active_scenario="custom", run_id="c", truck_count_delta=-3.0,
                                           crusher_availability=0.5, blast_powder_factor=1.2,
                                           shovel_down_id="kz.kyzyltas.mine:shovel-s3", dispatch_policy="fixed"))
    assert eff.truck_count_delta == -3.0 and eff.crusher_availability == 0.5
    assert eff.blast_powder_factor == 1.2 and eff.shovel_down_id == "shovel-s3" and eff.dispatch_policy == "fixed"


def test_shovel_failure_on_an_already_broken_shovel_still_differs_from_baseline():
    import dataclasses
    from scenarios import BASELINE_EFFECTIVE
    real = Simulation(seed=42, label="real")
    for _ in range(300):
        real.step(12, BASELINE_EFFECTIVE)
    a = real.maint.assets["shovel-s2"]
    a.down, a.down_remaining_h, a.down_mode = True, 0.5, "other"  # a short random fault in progress
    base = real.clone_as_baseline()
    eff = resolve_effective(dataclasses.replace(ScenarioFields(), active_scenario="shovel_failure", run_id="x"))
    for _ in range(600):  # two mine hours
        real.step(12, eff)
        base.step(12, BASELINE_EFFECTIVE)
    assert real.maint.is_down("shovel-s2") and not base.maint.is_down("shovel-s2")


def test_numeric_scenario_fields_override_presets():
    from models import constants as C
    eff = resolve_effective(ScenarioFields(active_scenario="custom", run_id="n", ambient_temp_c=-25.0,
                                           ore_bwi_kwht=15.0, mill_power_factor=0.9, road_rr_bonus_pct=1.5,
                                           cu_price_usd_t=12000.0))
    assert eff.ambient_temp_c == -25.0 and eff.ore_wi_kwht == 15.0 and eff.sag_power_fraction == 0.9
    assert eff.road_rr_bonus_pct == 1.5 and eff.cu_price_usd_t == 12000.0
    assert C.AXB_BASE > eff.axb > 32.0  # harder ore -> lower Axb
    # At baseline values the preset stays in charge.
    eff2 = resolve_effective(ScenarioFields(active_scenario="weather_cold_snap", run_id="c"))
    assert eff2.ambient_temp_c == C.TEMP_WINTER_EXTREME_C


if __name__ == "__main__":
    import traceback

    glb = dict(globals())
    tests = [(name, fn) for name, fn in glb.items() if name.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)
