"""
publish.py -- builds the Ditto feature dicts for every twin category from the live Simulation
state. Pure(ish) functions: each takes the simulation (and sometimes the resolved scenario
params) and returns {"feature_name": {"properties": {"value": v, "unit": u}}, ...}, ready for
ditto_io.RateLimitedPublisher.enqueue(name, features).

The baseline-vs-current delta readout lives on the kpi twin (build_kpi_features).
"""
from __future__ import annotations

import roster
import os

from ditto_io import feature as feat
from models import constants as C
from simulation import Simulation
from scenarios import EffectiveParams

TRUCK_STATE_LABEL = {
    "init": "queued", "queue_shovel": "queued_at_shovel", "spot_load": "spotting",
    "loading": "loading", "haul_loaded": "hauling", "queue_dump": "queued_at_dump",
    "dumping": "dumping", "haul_empty": "returning", "down": "down",
}


def build_truck_features(t) -> dict:
    progress = 0.0
    if t.phase_total_s > 0:
        progress = max(0.0, min(100.0, 100.0 * (1.0 - t.phase_remaining_s / t.phase_total_s)))
    return {
        "state": feat(TRUCK_STATE_LABEL.get(t.phase, t.phase), ""),
        "payload_t": feat(round(t.payload_t, 1), "t"),
        "speed_kmh": feat(round(t.speed_kmh, 1), "km/h"),
        "assigned_shovel": feat(t.assigned_shovel or "", ""),
        "route": feat(t.route, ""),
        "fuel_lph": feat(round(t.fuel_lph, 1), "L/h"),
        "trips_total": feat(t.trips_total, ""),
        "route_progress_pct": feat(round(progress, 1), "%"),
        "parked": feat(1 if t.parked else 0, ""),
        # Road segment the truck is on (thingId), "" at a shovel or the dump.
        "road_segment": feat(_road_segment(t, progress), ""),
    }


def _road_segment(t, progress_pct: float) -> str:
    if t.phase not in ("haul_loaded", "haul_empty") or not t.leg:
        return ""
    frac = progress_pct / 100.0
    for name, end in t.leg:
        if frac <= end + 1e-9:
            return f"{roster.NAMESPACE}:{name}"
    return f"{roster.NAMESPACE}:{t.leg[-1][0]}"


def build_truck_health_features(sim: Simulation, name: str) -> dict:
    asset = sim.maint.assets[name]
    return {
        # Health and time to wear-out as estimated from the condition signals, not the hidden truth.
        "health_pct": feat(round(asset.estimated_health_pct, 1), "%"),
        "next_pm_due_h": feat(round(asset.next_pm_due_h, 1), "h"),
        "coolant_temp_c": feat(round(asset.coolant_temp_c, 1), "C"),
        "oil_fe_ppm": feat(round(asset.oil_fe_ppm, 1), "ppm"),
        "work_order_open": feat(1 if asset.work_order_open else 0, ""),
    }


def build_shovel_features(sim: Simulation, name: str) -> dict:
    asset = sim.maint.assets[name]
    down = asset.down
    gas_blocked = sim.gas_block_until_h.get(name, -1.0) > sim.sim_time_h
    queue_len = sum(1 for t in sim.trucks.values() if not t.parked and t.assigned_shovel == name
                     and t.phase in ("queue_shovel", "spot_load"))
    state = "down" if down else ("blocked" if gas_blocked else ("loading" if queue_len == 0 else "queued"))
    return {
        "state": feat(state, ""),
        "face_grade_pct": feat(roster.SHOVEL_FACE_GRADE_PCT.get(name, 0.0), "%"),
        "queue_length": feat(queue_len, ""),
        "health_pct": feat(round(asset.health_pct, 1), "%"),
        "dig_rate_tph": feat(round(0.0 if (down or gas_blocked) else
                                    _shovel_dig_rate_tph(sim), 1), "t/h"),
    }


def _shovel_dig_rate_tph(sim: Simulation) -> float:
    from models import shovel as shovel_model
    swing_s = shovel_model.swing_time_s(x80_mm=sim.last_x80_mm, hydraulic_penalty=sim.weather.hydraulic_penalty())
    return shovel_model.dig_rate_tph(C.SHOVEL_BUCKET_M3["ore"], swing_s)


def build_drill_features(sim: Simulation, name: str, blast_powder_factor: float) -> dict:
    asset = sim.maint.assets[name]
    holes_factor = blast_powder_factor  # tighter burden/spacing -> proportionally more holes/hours
    return {
        "state": feat("down" if asset.down else "drilling", ""),
        # [A] 32 m/h (mid of the 25-40 m/h band, §4.1) at the base Bond Wi, slower in harder rock;
        # zero while the drill is down
        "penetration_rate_mh": feat(0.0 if asset.down else
                                    round(32.0 * (C.BWI_BASE_KWHT / sim.last_ore_wi) ** 0.6, 1), "m/h"),
        "drill_hours_factor": feat(round(holes_factor, 2), ""),
        "health_pct": feat(round(asset.health_pct, 1), "%"),
    }


def build_crusher_features(sim: Simulation, eff: EffectiveParams) -> dict:
    asset = sim.maint.assets[roster.CRUSHER_NAME]
    return {
        "state": feat("down" if asset.down else ("starved" if sim.last_crusher_tph < 1.0 else "crushing"), ""),
        "throughput_tph": feat(round(sim.last_crusher_tph, 0), "t/h"),
        "feed_grade_pct": feat(round(sim.stockpile_rom.grade_pct, 3), "%"),
        "availability": feat(round(eff.crusher_availability, 2), ""),
        "health_pct": feat(round(asset.health_pct, 1), "%"),
    }


def build_conveyor_features(sim: Simulation, index: int) -> dict:
    # conveyor-01: overland conveyor from the crushed-ore stockpile to the SAG mill;
    # conveyor-02: from the primary crusher to the crushed-ore stockpile.
    tph = sim.last_sag_tph if index == 0 else sim.last_crusher_tph
    return {
        "state": feat("running" if tph > 1.0 else "idle", ""),
        "throughput_tph": feat(round(tph, 0), "t/h"),
    }


def build_mill_features(sim: Simulation, is_sag: bool, name: str = "") -> dict:
    asset_name = roster.MILL_SAG_NAME if is_sag else name
    asset = sim.maint.assets[asset_name]
    tph = sim.last_sag_tph if is_sag else sim.last_ball_tph.get(name, 0.0)
    power_kw = sim.last_mill_power_kw.get(asset_name, 0.0)
    out = {
        "state": feat("down" if asset.down else ("starved" if tph < 1.0 else "grinding"), ""),
        "throughput_tph": feat(round(tph, 0), "t/h"),
        "power_kw": feat(round(power_kw, 0), "kW"),
        "health_pct": feat(round(asset.health_pct, 1), "%"),
    }
    if is_sag:
        out["p80_um"] = feat(round(sim.last_p80_um, 1), "um")
        out["x80_feed_mm"] = feat(round(sim.last_x80_mm, 1), "mm")
    return out


def build_flotation_features(sim: Simulation) -> dict:
    return {
        "state": feat("running" if sim.last_sag_tph > 1.0 else "idle", ""),
        "feed_tph": feat(round(sim.last_sag_tph, 0), "t/h"),
        "feed_grade_pct": feat(round(sim.last_mill_feed_grade, 3), "%"),
        "cu_recovery_pct": feat(round(sim.last_cu_recovery * 100.0, 1), "%"),
        "au_recovery_pct": feat(round(sim.last_au_recovery * 100.0, 1), "%"),
        # [A] concentrate grade follows head grade around the 22 % design value
        "conc_grade_pct": feat(round(min(26.0, max(18.0, C.CU_CONC_GRADE_PCT
                                                   + 8.0 * (sim.last_mill_feed_grade - C.HEAD_GRADE_MEAN_CU_PCT))), 2), "%"),
    }


def build_tailings_features(sim: Simulation) -> dict:
    mass_pull_pct = 0.0
    from models.flotation import mass_pull_to_conc_pct
    if sim.last_mill_feed_grade > 0:
        mass_pull_pct = mass_pull_to_conc_pct(sim.last_mill_feed_grade, sim.last_cu_recovery)
    tails_tph = sim.last_sag_tph * (1.0 - mass_pull_pct / 100.0)
    return {
        "state": feat("flowing" if sim.last_sag_tph > 1.0 else "idle", ""),
        "throughput_tph": feat(round(tails_tph, 0), "t/h"),
        "tails_grade_pct": feat(C.CU_TAILS_GRADE_PCT, "%"),
    }


def build_stockpile_features(sp) -> dict:
    return {
        "mass_t": feat(round(sp.mass_t, 0), "t"),
        "grade_pct": feat(round(sp.grade_pct, 3), "%"),
        "fill_pct": feat(round(sp.fill_fraction * 100.0, 1), "%"),
    }


def build_fan_features(eff: EffectiveParams, sim: Simulation | None = None) -> dict:
    out = {
        "state": feat("running" if eff.fan_speed_factor > 0.05 else "stopped", ""),
        "speed_factor": feat(round(eff.fan_speed_factor, 2), ""),
    }
    if sim is not None:
        # Pit dust station: haul-road PM10 emission (AP-42) and whether watering is possible.
        out["road_pm10_kg_h"] = feat(round(sim.last_pm10_kg_h, 1), "kg/h")
        out["watering_on"] = feat(1 if sim.watering_on else 0, "")
    return out


def build_substation_features(sim: Simulation) -> dict:
    load_kw = sim.last_kpi.get("energy_kwh_h", 0.0)
    return {
        "load_kw": feat(round(load_kw, 0), "kW"),
        "capacity_kw": feat(214000.0, "kW"),  # [R] S3 Bozshakol project power requirement
        "grid_co2_factor": feat(C.GRID_CO2_KG_PER_KWH, "kg/kWh"),
    }


def build_weather_features(sim: Simulation) -> dict:
    return {
        "temp_c": feat(round(sim.weather.temp_c, 1), "C"),
        "wind_ms": feat(round(sim.weather.wind_ms, 1), "m/s"),
        "condition": feat(sim.weather.condition, ""),
        "visibility_m": feat(round(sim.weather.visibility_m, 0), "m"),
    }


_TARP = [(5.0, "green"), (30.0, "amber"), (1e9, "red")]


def _tarp_level(velocity_mmday: float) -> str:
    for threshold, label in _TARP:
        if velocity_mmday < threshold:
            return label
    return "red"


def build_radar_features(eff: EffectiveParams, is_primary: bool, sim: Simulation | None = None,
                         name: str = "") -> dict:
    creep = sim.radar_creep.get(name, 1.0) if sim is not None else 1.0
    velocity = max(eff.slope_velocity_mmday, creep) if is_primary else creep
    return {
        "velocity_mmday": feat(round(velocity, 1), "mm/day"),
        "tarp_level": feat(_tarp_level(velocity), ""),
    }


def build_bench_features(name: str) -> dict:
    role = roster.BENCH_ROLE[name]
    # Face grade where a shovel is digging; otherwise the mean head grade for ore benches.
    grade = C.HEAD_GRADE_MEAN_CU_PCT if role == "ore" else 0.0
    for shovel, bench in roster.SHOVEL_BENCH.items():
        if bench == name:
            grade = roster.SHOVEL_FACE_GRADE_PCT.get(shovel, 0.0)
    return {
        "role": feat(role, ""),
        "grade_pct": feat(grade, "%"),
    }


def build_road_features(sim: Simulation, eff: EffectiveParams, name: str) -> dict:
    seg = roster.ROAD_SEGMENTS[name]
    closed = eff.close_main_ore_ramp and name in ("road-ramp-ore-up", "road-ramp-ore-down")
    n_ore_loaded = sum(1 for t in sim.trucks.values() if not t.parked and t.route == "ore"
                        and t.phase == "haul_loaded")
    n_waste_loaded = sum(1 for t in sim.trucks.values() if not t.parked and t.route == "waste"
                          and t.phase == "haul_loaded")
    traffic = 0
    if name.startswith("road-ramp-ore") and not closed:
        traffic = round(n_ore_loaded * 0.5)
    elif name.startswith("road-haul-crusher"):
        traffic = round(n_ore_loaded * 0.5)
    elif name.startswith("road-ramp-waste"):
        traffic = round(n_waste_loaded * 0.5)
    elif name.startswith("road-haul-dump"):
        traffic = round(n_waste_loaded * 0.5)
    rr_pct = C.RR_TYPICAL + eff.road_rr_bonus_pct
    return {
        "closed": feat(1 if closed else 0, ""),
        "traffic_count": feat(int(traffic), ""),
        "rolling_resistance_pct": feat(round(rr_pct, 1), "%"),
    }


def build_group_dispatch_features(sim: Simulation, eff: EffectiveParams) -> dict:
    from models.truck import match_factor
    ore_trucks = sum(1 for t in sim.trucks.values() if not t.parked and t.route == "ore")
    mf = match_factor(ore_trucks, C.LOAD_SWING_MEAN_MIN * 4.0, len(roster.ORE_SHOVELS), 22.0)
    queued = sum(1 for t in sim.trucks.values() if not t.parked and t.phase in ("queue_shovel", "queue_dump"))
    return {
        "dispatch_policy_active": feat(eff.dispatch_policy, ""),
        "match_factor_ore": feat(round(mf, 2), ""),
        "trucks_queued_total": feat(queued, ""),
    }


def build_group_pit_features(sim: Simulation) -> dict:
    sr = sim.last_kpi.get("strip_ratio", C.STRIP_RATIO_BASE)
    return {
        "strip_ratio": feat(round(sr, 2), ""),
        "ore_delivered_tph": feat(round(sim.last_crusher_tph, 0), "t/h"),
    }


def build_group_plant_features(sim: Simulation) -> dict:
    return {
        "plant_tph": feat(round(sim.last_sag_tph, 0), "t/h"),
        # Share of the main plant units (crusher, SAG, two ball mills) in service right now.
        "plant_availability": feat(round(sum(0.0 if sim.maint.is_down(n) else 1.0 for n in
                                             [roster.CRUSHER_NAME, roster.MILL_SAG_NAME] + list(roster.MILL_BALL_NAMES)) / 4.0, 2), ""),
    }


def build_group_mine_features(sim: Simulation) -> dict:
    return {
        "tonnes_ore_total": feat(round(sim.ore_total_t, 0), "t"),
        "tonnes_waste_total": feat(round(sim.waste_total_t, 0), "t"),
        "cu_output_total_t": feat(round(sim.cu_output_total_t, 2), "t"),
    }


def _pct_delta(current: float, baseline: float) -> float:
    if abs(baseline) < 1e-9:
        return 0.0
    return 100.0 * (current - baseline) / baseline


def build_kpi_features(sim_real: Simulation, sim_base: Simulation, eff: EffectiveParams) -> dict:
    cur = sim_real.last_kpi
    base = sim_base.last_kpi
    out = {
        "active_scenario": feat(eff.active_scenario, ""),
        "run_id": feat(eff.run_id, ""),
        "idSimulationRun": feat(eff.run_id, ""),
    }
    for key, unit in (("tph", "t/h"), ("cu_tph", "t/h"), ("au_ozph", "oz/h"), ("nsr_usd_h", "$/h"),
                       ("margin_usd_h", "$/h"), ("energy_kwh_h", "kWh/h"), ("fuel_l_h", "L/h"),
                       ("co2_t_h", "t/h"), ("ore_mined_tph", "t/h"), ("moved_tph", "t/h"),
                       ("mined_grade_pct", "%"), ("cu_mined_tph", "t/h"), ("haul_cycle_min", "min"),
                       ("fleet_avail_pct", "%"), ("buffer_h", "h"), ("mill_kwh_t", "kWh/t")):
        cv = float(cur.get(key, 0.0))
        bv = float(base.get(key, 0.0))
        out[f"current_{key}"] = feat(round(cv, 2), unit)
        out[f"baseline_{key}"] = feat(round(bv, 2), unit)
        out[f"delta_{key}_pct"] = feat(round(_pct_delta(cv, bv), 2), "%")
    # Latest causal event from the real (not baseline) simulation; event_seq lets
    # the UI tell a new event from a repeat of the same text.
    last = sim_real.events[-1] if sim_real.events else ""
    out["last_event"] = feat(last, "")
    out["event_seq"] = feat(sim_real.event_seq, "")
    # Simulation clock, so the interface can say how much mine time has passed.
    out["gc_reclaim_tph"] = feat(round(sim_real.gc_reclaim_tph, 0), "t/h")
    out["road_pm10_kg_h"] = feat(round(sim_real.last_pm10_kg_h, 1), "kg/h")
    out["sim_time_h"] = feat(round(sim_real.sim_time_h, 3), "h")
    out["speedup"] = feat(float(os.environ.get("SPEEDUP", "60")), "x")
    out["trucks_operating"] = feat(sum(1 for n in sim_real.active_fleet_names
                                       if not sim_real.maint.is_down(n)), "trucks")
    for key, sim_ in (("current", sim_real), ("baseline", sim_base)):
        out[f"{key}_unplanned_failures"] = feat(sim_.unplanned_failures_total, "")
        out[f"{key}_planned_repairs"] = feat(sim_.planned_repairs_total, "")
    out["cu_output_total_t"] = feat(round(sim_real.cu_output_total_t, 2), "t")
    out["co2_total_t"] = feat(round(sim_real.co2_total_kg / 1000.0, 2), "t")
    return out
