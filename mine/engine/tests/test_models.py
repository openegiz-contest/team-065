"""
Pure-Python unit tests for the physics/process models and modules -- no network, no MQTT, no
Docker required. Run with:
    python -m pytest tests/test_models.py -v
or, with no pytest installed:
    python tests/test_models.py
Every numeric check here traces to a specific 03_domain.md section (see inline comments and the
individual models/*.py __main__ self-checks, which this file exercises via direct imports).
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random

from models import constants as C
from models import blast, comminution, dust, economics, flotation, reliability, shovel, stockpile, truck, weather
from modules import dispatch as dispatch_mod
from modules import energy as energy_mod
from modules import grade_control as grade_mod
import roster
import scenarios


# --------------------------------------------------------------------------- truck.py
def test_truck_speed_on_grade_785c_matches_doc_example():
    v785 = truck.speed_on_grade_kmh(249.0, 1005.0, 10.0, 2.5, gear_max_kmh=55.0)
    assert abs(v785 - 9.5) < 0.5  # 03_domain.md §2.3 worked example


def test_truck_speed_on_grade_793f_within_table_band():
    v793 = truck.speed_on_grade_kmh(386.0, 1848.0, 10.0, 2.5, gear_max_kmh=60.0)
    assert 10.0 <= v793 <= 14.0  # 03_domain.md §2.3 table band (see truck.py note on the doc's own slip)


def test_truck_passes_per_785c_is_four():
    n = truck.passes_per_truck(136.0, 22.0)
    assert n == 4  # 03_domain.md §2.4


def test_truck_trolley_assist_speeds_up_loaded_ramp():
    v_no = truck.segment_speed_kmh("CAT793F", loaded=True, grade_pct=9.0, rr_pct=3.0, trolley_assist=False)
    v_yes = truck.segment_speed_kmh("CAT793F", loaded=True, grade_pct=9.0, rr_pct=3.0, trolley_assist=True)
    assert v_yes > v_no  # 03_domain.md §11-S12


def test_truck_match_factor_truck_limited_base_case():
    # 03_domain.md §2.6 Bozshakol check: MF = 18*2.3/(4*22) ~ 0.47 (truck-limited)
    mf = truck.match_factor(18, 2.3, 4, 22.0)
    assert 0.3 < mf < 0.6


# --------------------------------------------------------------------------- shovel.py
def test_shovel_finer_fragmentation_speeds_up_dig():
    t_coarse = shovel.swing_time_s(x80_mm=520.0)
    t_fine = shovel.swing_time_s(x80_mm=413.0)
    assert t_fine < t_coarse  # 03_domain.md §4.3: finer blast -> faster dig


def test_shovel_cold_hydraulic_penalty_slows_dig():
    t_normal = shovel.swing_time_s(hydraulic_penalty=0.0)
    t_cold = shovel.swing_time_s(hydraulic_penalty=0.15)
    assert t_cold > t_normal  # 03_domain.md §5.4/§11-S2


# --------------------------------------------------------------------------- blast.py
def test_blast_intensify_reduces_x50():
    base = blast.fragmentation_for_powder_factor(C.POWDER_FACTOR_BASE)
    intensified = blast.fragmentation_for_powder_factor(C.POWDER_FACTOR_INTENSIFIED)
    reduction_pct = 100.0 * (1.0 - intensified["x50_mm"] / base["x50_mm"])
    assert 10.0 < reduction_pct < 35.0  # 03_domain.md §4.2 table: ~21% reduction


# --------------------------------------------------------------------------- comminution.py
def test_bond_work_matches_doc_example():
    w = comminution.bond_work_kwh_t(13.0, 2500.0, 180.0)
    assert abs(w - 7.1) < 0.3  # 03_domain.md §7.3


def test_hard_ore_coarsens_p80_when_holding_tph():
    p80 = comminution.hardness_adjusted_p80(180.0, 13.0, 16.0)
    assert 230.0 < p80 < 255.0  # 03_domain.md §7.3: ~242 um


def test_sag_surrogate_finer_blast_raises_tph():
    base_tph = comminution.sag_tph_surrogate(3425.0, 1.0, 45.0, 45.0, 520.0, 520.0, 0.10, 0.10)
    fine_tph = comminution.sag_tph_surrogate(3425.0, 1.0, 45.0, 45.0, 520.0, 413.0, 0.20, 0.10)
    assert fine_tph > base_tph  # 03_domain.md §4.3/§11-S3: finer feed -> SAG TPH up


# --------------------------------------------------------------------------- flotation.py
def test_flotation_aktogay_check():
    r = flotation.constant_tails_recovery(0.361, 24.3, 0.059)
    assert abs(r - 0.839) < 0.01  # 03_domain.md §7.4


def test_flotation_bozshakol_base_case_recovery():
    r = flotation.constant_tails_recovery(C.HEAD_GRADE_MEAN_CU_PCT, C.CU_CONC_GRADE_PCT, C.CU_TAILS_GRADE_PCT)
    assert abs(r - 0.797) < 0.01  # 03_domain.md §7.4: f=0.51% -> R~79.7%


def test_flotation_recovery_falls_with_lower_head_grade():
    r_low = flotation.constant_tails_recovery(0.45, C.CU_CONC_GRADE_PCT, C.CU_TAILS_GRADE_PCT)
    r_high = flotation.constant_tails_recovery(0.55, C.CU_CONC_GRADE_PCT, C.CU_TAILS_GRADE_PCT)
    assert r_low < r_high  # 03_domain.md §7.4 (and §11-S1 blend-shift causal chain)


def test_flotation_shovel_failure_blend_shift_drops_cu_output():
    # 03_domain.md §11-S1: blend from 0.515% (s1+s2) down to pure s1 0.45% when s2 fails.
    blended_before = stockpile.blend_grade([(1.0, 0.45), (1.0, 0.58)])
    r_before = flotation.cu_recovery(blended_before)
    r_after = flotation.cu_recovery(0.45)
    assert r_after < r_before


# --------------------------------------------------------------------------- stockpile.py
def test_stockpile_mass_balance_and_blend():
    sp = stockpile.Stockpile("x", mass_t=1000.0, grade_pct=0.5, capacity_t=2000.0)
    sp.add(500.0, 0.8)
    assert abs(sp.mass_t - 1500.0) < 1e-6
    assert sp.grade_pct > 0.5
    drawn, g = sp.draw(10_000.0)  # can't draw more than available
    assert drawn == 1500.0


def test_stockpile_buffers_a_mine_side_disruption():
    """The crushed-ore stockpile should keep SAG feed stable for a while even if the crusher
    output drops to zero (03_domain.md §3.2: ~11h/40kt buffer)."""
    sp = stockpile.Stockpile("crushed", mass_t=C.CRUSHED_STOCKPILE_CAPACITY_T, grade_pct=0.5,
                              capacity_t=C.CRUSHED_STOCKPILE_CAPACITY_T)
    drawn, _ = sp.draw(C.SAG_RATED_TPH * 1.0)  # draw 1h of SAG feed with zero crusher input
    assert drawn == C.SAG_RATED_TPH
    assert sp.mass_t > 0  # buffer absorbed it without emptying


# --------------------------------------------------------------------------- reliability.py
def test_reliability_availability_formula():
    a = reliability.inherent_availability(80.0, 6.0)
    assert abs(a - 80.0 / 86.0) < 1e-9


def test_reliability_predictive_avoids_unplanned_failure():
    rng = random.Random(7)
    asset = reliability.AssetReliability("truck", rng)
    asset.time_to_failure_h = 50.0  # force a short, deterministic horizon for the test
    hit_watch = False
    for hour in range(60):
        at_boundary = (hour % 12 == 0 and hour > 0)
        asset.step(dt_h=1.0, predictive=True, at_shift_boundary=at_boundary)
        if asset.work_order_open or asset.down:
            hit_watch = True
    assert hit_watch  # predictive branch raised a work order / planned repair before run-to-failure


# --------------------------------------------------------------------------- dust.py
def test_dust_matches_doc_worked_example():
    e = dust.pm10_kg_per_vkm(8.0, 276.0)
    assert 1.8 < e < 2.8  # 03_domain.md §5.1: ~2.3 kg/vehicle-km


def test_dust_no_watering_below_zero():
    e = dust.pm10_kg_per_vkm(8.0, 276.0)
    c_cold = dust.controlled_pm10_kg_per_vkm(e, 0.65, -10.0)
    assert c_cold == e  # 03_domain.md §5.1: watering impossible below ~0C


# --------------------------------------------------------------------------- weather.py
def test_weather_extreme_cold_caps_speed():
    w = weather.WeatherState(temp_c=-38.0, wind_ms=12.0)
    assert w.road_speed_cap_kmh(ramp=True) == C.COLD_SPEED_CAP_RAMP_KMH


# --------------------------------------------------------------------------- economics.py
def test_economics_base_case_cu_tph():
    cu = economics.cu_tph(3600.0, 0.50, 0.80)
    assert abs(cu - 14.4) < 1e-6  # 03_domain.md §9.3


def test_economics_price_shock_cuts_nsr():
    cu = economics.cu_tph(3600.0, 0.50, 0.80)
    au = economics.au_ozph(3600.0, 0.26, 0.60)
    nsr_base = economics.nsr_usd_h(cu, au, C.CU_PRICE_USD_T_BASE, C.AU_PRICE_USD_OZ, C.TC_RC_USD_PER_T)
    nsr_shock = economics.nsr_usd_h(cu, au, C.CU_PRICE_USD_T_SHOCK, C.AU_PRICE_USD_OZ, C.TC_RC_USD_PER_T_SHOCK)
    assert nsr_shock < nsr_base  # 03_domain.md §11-S10


# --------------------------------------------------------------------------- modules/
def test_dispatch_dynamic_prefers_shortest_queue():
    busy = {"shovel-s1": 1000.0, "shovel-s2": 10.0}
    chosen = dispatch_mod.choose_shovel("dynamic", "truck-01", ["shovel-s1", "shovel-s2"], busy, {},
                                         {}, now_s=0.0)
    assert chosen == "shovel-s2"


def test_dispatch_fixed_ignores_queue_length():
    busy = {"shovel-s1": 1000.0, "shovel-s2": 10.0}
    fixed = {"truck-01": "shovel-s1"}
    chosen = dispatch_mod.choose_shovel("fixed", "truck-01", ["shovel-s1", "shovel-s2"], busy, {},
                                         fixed, now_s=0.0)
    assert chosen == "shovel-s1"  # fixed dispatch does not react to queueing


def test_grade_control_reclaim_restores_target_grade():
    x = grade_mod.high_grade_reclaim_t(1000.0, 0.45, 0.65, 1e6, 0.50, 1e6)
    assert abs((1000.0 * 0.45 + x * 0.65) / (1000.0 + x) - 0.50) < 1e-9  # 03_domain.md §11-S1
    assert grade_mod.high_grade_reclaim_t(1000.0, 0.52, 0.65, 1e6, 0.50, 1e6) == 0.0  # already on grade
    assert grade_mod.high_grade_reclaim_t(1000.0, 0.45, 0.65, 1e6, 0.50, 50.0) == 50.0  # loader-limited


def test_stockpile_conserves_mass():
    sp = stockpile.Stockpile("crushed", mass_t=39000.0, grade_pct=0.5, capacity_t=40000.0)
    sp.add(5000.0, 0.5)
    assert sp.mass_t == 44000.0  # never silently dropped; callers respect headroom()
    assert sp.headroom() == 0.0


def test_energy_trolley_cost_saving_and_carbon_paradox():
    t = energy_mod.trolley_tradeoff(n_trucks_on_ramp=3.0, dt_h=1.0, grid_ef_kg_kwh=0.80)
    assert t["cost_usd_h"] < 0.0  # 03_domain.md §11-S12: net cost falls
    assert t["co2_kg_h"] > 0.0   # but CO2 rises on the 0.80 kg/kWh KZ grid (above 0.64 breakeven)


# --------------------------------------------------------------------------- scenarios.py
def test_all_scenario_ids_resolve_without_error():
    for sid in scenarios.VALID_SCENARIOS:
        fields = scenarios.ScenarioFields(active_scenario=sid)
        eff = scenarios.resolve_effective(fields)
        assert eff.active_scenario == sid


def test_shovel_failure_defaults_to_s2():
    fields = scenarios.ScenarioFields(active_scenario="shovel_failure")
    eff = scenarios.resolve_effective(fields)
    assert eff.shovel_down_id == "shovel-s2"


def test_fleet_minus_2_defaults_truck_delta():
    fields = scenarios.ScenarioFields(active_scenario="fleet_minus_2")
    eff = scenarios.resolve_effective(fields)
    assert eff.truck_count_delta == -2


def test_scenario_event_parser_ignores_echo():
    parser = scenarios.ScenarioEventParser()
    payload = {"path": "/features", "value": {"active_scenario": {"properties": {"value": "none"}}}}
    assert parser.apply_event(payload) is None  # already "none" -- no-op/echo


def test_scenario_event_parser_applies_real_change():
    parser = scenarios.ScenarioEventParser()
    payload = {"path": "/features", "value": {"active_scenario": {"properties": {"value": "shovel_failure"}}}}
    new_fields = parser.apply_event(payload)
    assert new_fields is not None
    assert new_fields.active_scenario == "shovel_failure"


# --------------------------------------------------------------------------- roster.py sanity
def test_roster_shovel_face_grades_match_domain_doc_s1():
    assert roster.SHOVEL_FACE_GRADE_PCT["shovel-s1"] == 0.45
    assert roster.SHOVEL_FACE_GRADE_PCT["shovel-s2"] == 0.58


def test_roster_truck_count_is_fourteen():
    assert len(roster.TRUCK_NAMES) == 14


if __name__ == "__main__":
    # Allow running without pytest installed: execute every test_* function and report.
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
