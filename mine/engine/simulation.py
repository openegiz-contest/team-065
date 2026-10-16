"""
simulation.py -- the Simulation class: one running instance of the whole mine (truck cycles,
shovel/dispatch resource contention, blast fragmentation, crusher->SAG->ball->flotation mass/grade
flow, maintenance, energy/CO2, KPIs). engine.py runs TWO instances: one with the live scenario
applied, one "shadow baseline" always at scenarios.BASELINE_EFFECTIVE, so the UI can show
delta-vs-baseline (published on the kpi twin).

This is a tick-based (not full discrete-event) simulation: each entity's current phase has a
duration computed when the phase is entered (using the params live at that instant), and ticks
down by dt_s every step. Resource contention (one truck at a time per shovel; a 2-bay crusher
dump queue) is modelled with simple busy_until timestamps, which is what produces real,
emergent queueing/match-factor behaviour rather than a scripted number.
"""
from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field

import roster
from models import constants as C
from models import blast as blast_model
from models import comminution as comm_model
from models import economics as econ_model
from models import flotation as flot_model
from models import shovel as shovel_model
from models import stockpile as stock_model
from models import truck as truck_model
from models import weather as weather_model
from models import dust as dust_model
from modules import dispatch as dispatch_mod
from modules import energy as energy_mod
from modules import grade_control as grade_mod
from modules.maintenance import MaintenanceManager
from scenarios import EffectiveParams, BASELINE_EFFECTIVE


SHOVEL_ASSET_CLASS = "shovel"
DRILL_ASSET_CLASS = "drill"
CRUSHER_ASSET_CLASS = "crusher"
MILL_ASSET_CLASS = "mill"
TRUCK_ASSET_CLASS = "truck"


@dataclass
class TruckState:
    name: str
    cls: str
    route: str
    fixed_shovel: str
    phase: str = "init"
    phase_remaining_s: float = 0.0
    phase_total_s: float = 1.0
    assigned_shovel: str = ""
    dump_bay: int = -1
    payload_t: float = 0.0
    grade_at_load_pct: float = 0.0
    speed_kmh: float = 0.0
    trips_total: int = 0
    odometer_km: float = 0.0
    fuel_lph: float = 0.0
    parked: bool = False
    just_dumped_ore_t: float = 0.0
    just_dumped_ore_grade: float = 0.0
    just_dumped_waste_t: float = 0.0
    last_dump_h: float = -1.0
    trolley_share: float = 0.0  # fraction of the current loaded haul spent on the trolley ramp
    leg: tuple = ()  # (road segment name, cumulative fraction of the leg's travel time) for the current haul
    manual_shovel: str = ""     # fixed dispatch: shovel a supervisor reassigned this truck to (until shift end)
    reassign_wait_since_h: float = -1.0


def _tri(rng: random.Random, lo: float, mode: float, hi: float) -> float:
    return rng.triangular(lo, hi, mode)


class Simulation:
    def __init__(self, seed: int, label: str):
        self.label = label
        self.rng = random.Random(seed)
        self.sim_time_h = 0.0
        self._last_shift_idx = -1
        self.maint = MaintenanceManager(rng=self.rng, seed=seed)

        self.trucks: dict[str, TruckState] = {}
        for name in roster.TRUCK_NAMES:
            cls = roster.truck_class(name)
            route = roster.TRUCK_ROUTE[name]
            fixed = roster.FIXED_SHOVEL_ASSIGNMENT[name]
            self.trucks[name] = TruckState(name=name, cls=cls, route=route, fixed_shovel=fixed)
            self.maint.register(name, TRUCK_ASSET_CLASS)
        for name in roster.SHOVEL_NAMES:
            self.maint.register(name, SHOVEL_ASSET_CLASS)
        for name in roster.DRILL_NAMES:
            self.maint.register(name, DRILL_ASSET_CLASS)
        self.maint.register(roster.CRUSHER_NAME, CRUSHER_ASSET_CLASS)
        self.maint.register(roster.MILL_SAG_NAME, MILL_ASSET_CLASS)
        for name in roster.MILL_BALL_NAMES:
            self.maint.register(name, MILL_ASSET_CLASS)

        self.shovel_busy_until_s: dict[str, float] = {s: 0.0 for s in roster.SHOVEL_NAMES}
        self.dump_bay_busy_until_s = [0.0, 0.0]
        self.gas_block_until_h: dict[str, float] = {}

        self.weather = weather_model.WeatherState()
        self.stockpile_rom = stock_model.Stockpile("stockpile-rom", mass_t=5000.0,
                                                     grade_pct=C.HEAD_GRADE_MEAN_CU_PCT,
                                                     capacity_t=C.ROM_PAD_CAPACITY_T)
        self.rom_full_alert = False
        self.last_ball_tph: dict[str, float] = {}
        self.last_mill_power_kw: dict[str, float] = {}
        self.stockpile_crushed = stock_model.Stockpile("stockpile-crushed",
                                                         mass_t=C.CRUSHED_STOCKPILE_START_FRACTION * C.CRUSHED_STOCKPILE_CAPACITY_T,
                                                         grade_pct=C.HEAD_GRADE_MEAN_CU_PCT,
                                                         capacity_t=C.CRUSHED_STOCKPILE_CAPACITY_T)
        self.stockpile_hg = stock_model.Stockpile("stockpile-hg", mass_t=C.HG_STOCKPILE_T,
                                                    grade_pct=C.HG_STOCKPILE_GRADE_PCT,
                                                    capacity_t=C.HG_STOCKPILE_T)
        self.gc_reclaim_tph = 0.0
        self.gc_active = False
        self.gc_last_reclaim_h = -99.0
        # Slope radar background creep (mm/day), mean-reverting; own random stream so it does not
        # shift any other draw.
        self.radar_rng = random.Random(f"{seed}:radar")
        self.radar_creep = {n: 1.0 + 0.5 * i for i, n in enumerate(roster.RADAR_NAMES)}
        self.last_ore_wi = C.BWI_BASE_KWHT
        self.last_pm10_kg_h = 0.0
        self.watering_on = True
        self.stockpile_waste = stock_model.Stockpile("stockpile-waste", mass_t=0.0, grade_pct=0.0,
                                                       capacity_t=1.0e9)

        self.sim_time_h0 = 0.0
        self.last_crusher_tph = 0.0
        self.last_sag_tph = 0.0
        self.last_mill_feed_grade = C.HEAD_GRADE_MEAN_CU_PCT
        self.last_x80_mm = 520.0
        self.last_p80_um = C.BOND_P80_UM_BASE
        self.last_sag_power_fraction = 1.0
        self.last_cu_recovery = 0.80
        self.last_au_recovery = C.AU_RECOVERY_BASE
        self.cu_output_total_t = 0.0
        self.au_output_total_oz = 0.0
        self.ore_total_t = 0.0
        self.waste_total_t = 0.0
        self.diesel_total_l = 0.0
        self.grid_total_kwh = 0.0
        self.co2_total_kg = 0.0
        self.last_kpi: dict = {}
        self.events: list[str] = []  # recent human-readable events, newest last
        self.event_seq = 0  # increments per event; published so the UI can spot new ones
        self.last_scenario_run = "baseline"
        self.gas_blast_run = ""  # run_id whose post-blast exclusion was already applied
        self.shovel_forced_run = ""  # run_id whose forced shovel outage was already applied
        # Pit-side rates: exponential moving averages over KPI_EMA_TAU_H of sim time. They react
        # to haulage changes at once, while plant KPIs lag behind the crushed-ore buffer.
        self.ema_ore_tph = 0.0
        self.ema_waste_tph = 0.0
        self.ema_ore_cu_tph = 0.0  # tonnes of contained Cu mined per hour
        self.ema_cycle_min = 0.0
        self.ema_diesel_lph = 0.0
        self.ema_trolley_kwh_h = 0.0
        self.ema_plant_kw = 0.0
        self.unplanned_failures_total = 0
        self.planned_repairs_total = 0
        self.buffer_alert = ""  # "", "low", "starved"
        self.active_fleet_names: list[str] = list(roster.TRUCK_NAMES)

        self.last_dump_bay_grade_sum = 0.0
        self.last_dump_bay_mass_sum = 0.0

    # -------------------------------------------------------------------- utils
    def _eligible_shovels(self, route: str) -> list[str]:
        names = roster.ORE_SHOVELS if route == "ore" else roster.WASTE_SHOVELS
        out = []
        for n in names:
            if self.maint.is_down(n):
                continue
            if self.gas_block_until_h.get(n, -1.0) > self.sim_time_h:
                continue
            out.append(n)
        return out

    def _shovel_grade(self, name: str) -> float:
        return roster.SHOVEL_FACE_GRADE_PCT.get(name, 0.0)

    def _apply_fleet_size(self, eff: EffectiveParams) -> None:
        active_n = dispatch_mod.fleet_size(len(roster.TRUCK_NAMES), eff.truck_count_delta, min_fleet=4)
        self.active_fleet_names = list(roster.TRUCK_NAMES)[:active_n]
        for name, t in self.trucks.items():
            t.parked = name not in self.active_fleet_names
            if t.parked:
                t.last_dump_h = -1.0

    def clone_as_baseline(self) -> "Simulation":
        """Counterfactual baseline from this exact moment: a deep copy of the live mine, including
        every random-number stream. Stepped without the scenario, it differs from the live mine
        only because of what the scenario changes from now on."""
        twin = copy.deepcopy(self)
        twin.label = "baseline"
        return twin

    def trucks_available(self) -> int:
        return sum(1 for n in roster.TRUCK_NAMES if not self.maint.is_down(n))

    def buffer_hours(self) -> float:
        """Hours of mill feed in the crushed-ore stockpile at the SAG mill's rated throughput."""
        return self.stockpile_crushed.mass_t / C.SAG_RATED_TPH

    def _check_buffer(self) -> None:
        h = self.stockpile_crushed.mass_t / max(self.last_sag_tph, C.SAG_RATED_TPH * 0.5)
        if self.stockpile_crushed.mass_t < 1.0:
            state = "starved"
        elif h < C.BUFFER_LOW_H:
            state = "low"
        else:
            state = ""
        if state == self.buffer_alert:
            return
        if state == "low":
            self._log(f"stockpile-crushed: below {C.BUFFER_LOW_H:.0f} h of mill feed "
                      f"({self.stockpile_crushed.mass_t:,.0f} t) -> SAG mill at risk")
        elif state == "starved":
            self._log("stockpile-crushed: empty -> SAG mill starved, throughput limited to crusher output")
        else:
            self._log(f"stockpile-crushed: recovered to {h:.1f} h of mill feed")
        self.buffer_alert = state

    def _log(self, text: str) -> None:
        self.events.append(f"[t={self.sim_time_h:6.2f}h] {text}")
        self.event_seq += 1
        if len(self.events) > 50:
            self.events = self.events[-50:]

    # -------------------------------------------------------------------- main step
    def step(self, dt_s: float, eff: EffectiveParams) -> None:
        dt_h = dt_s / 3600.0
        self.sim_time_h += dt_h
        self.last_ore_wi = eff.ore_wi_kwht
        for n in self.radar_creep:
            # [A] green-level creep, mean-reverting around 1.5 mm/day (TARP green < 5 mm/day, §5.3)
            v = self.radar_creep[n]
            v += 0.5 * (1.5 - v) * dt_h + 0.4 * (dt_h ** 0.5) * self.radar_rng.gauss(0.0, 1.0)
            self.radar_creep[n] = min(4.0, max(0.2, v))
        if eff.run_id != self.last_scenario_run:
            self.last_scenario_run = eff.run_id
            self._log(f"Scenario '{eff.active_scenario}': {eff.narrative}")
        shift_idx = int(self.sim_time_h // C.SHIFT_LENGTH_H)
        at_shift_boundary = shift_idx != self._last_shift_idx
        self._last_shift_idx = shift_idx
        if at_shift_boundary:
            for tr in self.trucks.values():
                tr.manual_shovel = ""  # new shift plan
        if self.rom_full_alert and self.stockpile_rom.headroom() > 20000.0:
            self.rom_full_alert = False
            self._log("stockpile-rom: room on the pad again -> ore trucks dump normally")

        # weather: smooth toward the scenario's target so transitions aren't an instant snap
        self._step_weather(dt_h, eff)

        self._apply_fleet_size(eff)

        # scenario-forced shovel outage (e.g. shovel_failure) -- deterministic MTTR window
        forced_down_name = eff.shovel_down_id
        for name in roster.SHOVEL_NAMES:
            # Undo: an outage imposed by a scenario ends when that scenario is cleared.
            asset = self.maint.assets[name]
            if asset.down and asset.down_mode == "forced" and name != forced_down_name:
                asset.down_remaining_h = 0.0
                self.shovel_forced_run = ""
            # One outage per scenario run: after its repair the shovel stays in service.
            forced_h = 0.0
            if name == forced_down_name and self.shovel_forced_run != eff.run_id:
                self.shovel_forced_run = eff.run_id
                forced_h = C.SHOVEL_FAILURE_MTTR_H
                if self.maint.is_down(name):
                    # Already down from an ordinary fault: the scenario turns it into its own
                    # outage (so Undo ends it) and makes it last the scenario's full repair time.
                    asset = self.maint.assets[name]
                    asset.down_mode = "forced"
                    asset.down_remaining_h = max(asset.down_remaining_h, forced_h)
                    self._log(f"{name}: already down; scenario extends the outage to {forced_h:.0f} h")
                    forced_h = 0.0
            res = self.maint.step(name, dt_h, predictive=False, at_shift_boundary=at_shift_boundary,
                                   forced_down_h=forced_h)
            if res["event"]:
                self._log(f"{name}: {res['event']}")

        for name in roster.DRILL_NAMES:
            self.maint.step(name, dt_h, predictive=False, at_shift_boundary=at_shift_boundary)
        self.maint.step(roster.CRUSHER_NAME, dt_h, predictive=False, at_shift_boundary=at_shift_boundary)
        self.maint.step(roster.MILL_SAG_NAME, dt_h, predictive=False, at_shift_boundary=at_shift_boundary)
        for name in roster.MILL_BALL_NAMES:
            self.maint.step(name, dt_h, predictive=False, at_shift_boundary=at_shift_boundary)

        # blast_delay gas exclusion: block affected shovels for the scenario's clearance window
        if eff.gas_extra_delay_min <= 0.0 and self.gas_blast_run:
            # Scenario undone: lift the exclusion at once.
            for name, until in self.gas_block_until_h.items():
                if until > self.sim_time_h:
                    self.gas_block_until_h[name] = self.sim_time_h
                    self._log(f"{name}: fume exclusion lifted (scenario cleared)")
            self.gas_blast_run = ""
        if eff.gas_extra_delay_min > 0.0 and eff.gas_block_shovels:
            clearance_h = (C.BLAST_REENTRY_MIN_MIN + eff.gas_extra_delay_min) / eff.fan_speed_factor / 60.0
            # One exclusion window per scenario run (not re-extended every tick).
            if self.gas_blast_run != eff.run_id:
                self.gas_blast_run = eff.run_id
                for name in eff.gas_block_shovels:
                    self._log(f"{name} idled by post-blast fume exclusion for {clearance_h*60:.0f} min")
                    self.gas_block_until_h[name] = self.sim_time_h + clearance_h

        self.last_dump_bay_grade_sum = 0.0
        self.last_dump_bay_mass_sum = 0.0

        for name in self.active_fleet_names:
            res = self.maint.step(name, dt_h, predictive=eff.predictive_maintenance_on,
                                   at_shift_boundary=at_shift_boundary)
            if res["event"]:
                self._log(f"{name}: {res['event']}")
                if res["event"].startswith("unplanned failure"):
                    self.unplanned_failures_total += 1
                elif res["event"].startswith("planned repair"):
                    self.planned_repairs_total += 1

        ore_t = waste_t = ore_cu_t = 0.0
        for name in self.active_fleet_names:
            t = self.trucks[name]
            self._step_truck(t, dt_s, dt_h, eff)
            if t.just_dumped_ore_t > 0.0 or t.just_dumped_waste_t > 0.0:
                if t.last_dump_h >= 0.0:
                    cyc_min = (self.sim_time_h - t.last_dump_h) * 60.0
                    if self.ema_cycle_min <= 0.0:
                        self.ema_cycle_min = cyc_min
                    else:
                        self.ema_cycle_min += (cyc_min - self.ema_cycle_min) * C.KPI_CYCLE_EMA_WEIGHT
                t.last_dump_h = self.sim_time_h
            ore_t += t.just_dumped_ore_t
            ore_cu_t += t.just_dumped_ore_t * t.just_dumped_ore_grade / 100.0
            waste_t += t.just_dumped_waste_t
            if t.just_dumped_ore_t > 0.0:
                self.stockpile_rom.add(t.just_dumped_ore_t, t.just_dumped_ore_grade)
                self.ore_total_t += t.just_dumped_ore_t
                t.just_dumped_ore_t = 0.0
            if t.just_dumped_waste_t > 0.0:
                self.stockpile_waste.add(t.just_dumped_waste_t, 0.0)
                self.waste_total_t += t.just_dumped_waste_t
                t.just_dumped_waste_t = 0.0

        truck_fuel_l = sum(t.fuel_lph * dt_h for t in self.trucks.values() if not t.parked)

        # Haul-road PM10 (AP-42 §13.2.2): vehicle-km travelled this tick x emission factor at
        # each truck's mean (empty/loaded) weight; watering control is lost below 0 C.
        pm10_kg = 0.0
        self.watering_on = self.weather.temp_c >= 0.0
        for t in self.trucks.values():
            if t.parked or t.phase not in ("haul_loaded", "haul_empty"):
                continue
            vkm = t.speed_kmh * dt_h
            t.odometer_km += vkm
            spec = C.TRUCK_SPECS[t.cls]
            mean_w = spec["gvw_t"] - spec["payload_t"] / 2.0
            e = dust_model.pm10_kg_per_vkm(C.HAUL_ROAD_SILT_PCT, mean_w)
            pm10_kg += vkm * dust_model.controlled_pm10_kg_per_vkm(
                e, C.WATERING_CONTROL_EFFICIENCY, self.weather.temp_c)
        if dt_h > 0.0:
            a = min(1.0, dt_h / C.KPI_EMA_TAU_H)
            self.last_pm10_kg_h += (pm10_kg / dt_h - self.last_pm10_kg_h) * a
        self.diesel_total_l += truck_fuel_l

        # Trucks under the trolley line right now, in 793F-equivalents: each loaded ore truck counts
        # for the share of its haul spent on the trolley ramp, scaled by its engine power.
        ref_kw = C.TRUCK_SPECS["KOM830E"]["gross_power_kw"]
        trolley_n = sum(t.trolley_share * C.TRUCK_SPECS[t.cls]["gross_power_kw"] / ref_kw
                        for t in self.trucks.values()
                        if eff.trolley_on and not t.parked and t.route == "ore" and t.phase == "haul_loaded")
        trolley = energy_mod.trolley_tradeoff(trolley_n, dt_h,
                                               grid_ef_kg_kwh=C.GRID_CO2_KG_PER_KWH)

        if dt_h > 0.0:
            a = min(1.0, dt_h / C.KPI_EMA_TAU_H)
            self.ema_ore_tph += (ore_t / dt_h - self.ema_ore_tph) * a
            self.ema_waste_tph += (waste_t / dt_h - self.ema_waste_tph) * a
            self.ema_ore_cu_tph += (ore_cu_t / dt_h - self.ema_ore_cu_tph) * a

        plant = self._step_plant(dt_h, eff)
        self._check_buffer()
        self._step_kpi(dt_h, eff, truck_fuel_l, trolley, plant)

    # -------------------------------------------------------------------- weather
    def _step_weather(self, dt_h: float, eff: EffectiveParams) -> None:
        rate = min(1.0, dt_h * 12.0)  # weather front arrives over ~5 min of sim time
        self.weather.temp_c += (eff.ambient_temp_c - self.weather.temp_c) * rate
        self.weather.wind_ms += (eff.wind_ms - self.weather.wind_ms) * rate
        # Settle on the target once close, so thresholds such as -30 C are actually reached.
        if abs(eff.ambient_temp_c - self.weather.temp_c) < 0.1:
            self.weather.temp_c = eff.ambient_temp_c
        if abs(eff.wind_ms - self.weather.wind_ms) < 0.05:
            self.weather.wind_ms = eff.wind_ms
        if self.weather.is_extreme_cold:
            self.weather.condition = "blizzard" if self.weather.wind_ms > 8.0 else "extreme_cold"
            self.weather.visibility_m = 300.0 if self.weather.condition == "blizzard" else 2000.0
        elif self.weather.wind_ms < 1.0 and self.weather.temp_c < -5.0:
            self.weather.condition = "calm_inversion"
            self.weather.visibility_m = 2000.0
        else:
            self.weather.condition = "clear"
            self.weather.visibility_m = 2000.0

    # -------------------------------------------------------------------- truck FSM
    def _effective_rr_pct(self, eff: EffectiveParams) -> float:
        return C.RR_TYPICAL + eff.road_rr_bonus_pct

    def _route_segments(self, route: str, loaded: bool, eff: EffectiveParams) -> list[dict]:
        if route == "waste":
            segs = roster.WASTE_ROUTE if loaded else roster.WASTE_ROUTE_RETURN
        else:
            if eff.close_main_ore_ramp:
                segs = roster.ORE_ROUTE_DETOUR if loaded else roster.ORE_ROUTE_DETOUR_RETURN
            else:
                segs = roster.ORE_ROUTE_MAIN if loaded else roster.ORE_ROUTE_MAIN_RETURN
        return [roster.ROAD_SEGMENTS[s] | {"name": s} for s in segs]

    def _travel_time_and_speed(self, t: TruckState, loaded: bool, eff: EffectiveParams) -> tuple[float, float]:
        segs = self._route_segments(t.route, loaded, eff)
        rr = self._effective_rr_pct(eff)
        cold_cap = self.weather.road_speed_cap_kmh(ramp=False)
        vis_cap = self.weather.visibility_speed_cap_kmh()
        total_min = 0.0
        total_km = 0.0
        trolley_min = 0.0
        for seg in segs:
            is_ramp = seg["kind"] in ("ramp_up", "ramp_down")
            cold_cap_seg = self.weather.road_speed_cap_kmh(ramp=is_ramp)
            trolley = (eff.trolley_on and loaded and seg["name"] == "road-ramp-ore-up"
                       and C.TRUCK_SPECS[t.cls]["drive"] == "electric")
            v = truck_model.segment_speed_kmh(t.cls, loaded, seg["grade_pct"], rr,
                                               trolley_assist=trolley,
                                               cold_speed_cap_kmh=cold_cap_seg,
                                               visibility_speed_cap_kmh=vis_cap)
            seg_min = truck_model.segment_travel_time_min(seg["length_m"], v)
            total_min += seg_min
            if trolley:
                trolley_min += seg_min
            total_km += seg["length_m"] / 1000.0
        if loaded:
            t.trolley_share = trolley_min / total_min if total_min > 0 else 0.0
        # Remember where each segment of this leg ends (fraction of travel time) for road_segment.
        legs, acc = [], 0.0
        for seg in segs:
            is_ramp = seg["kind"] in ("ramp_up", "ramp_down")
            trolley_seg = (eff.trolley_on and loaded and seg["name"] == "road-ramp-ore-up"
                           and C.TRUCK_SPECS[t.cls]["drive"] == "electric")
            v = truck_model.segment_speed_kmh(t.cls, loaded, seg["grade_pct"], rr,
                                               trolley_assist=trolley_seg,
                                               cold_speed_cap_kmh=self.weather.road_speed_cap_kmh(ramp=is_ramp),
                                               visibility_speed_cap_kmh=vis_cap)
            acc += truck_model.segment_travel_time_min(seg["length_m"], v)
            legs.append((seg["name"], acc / total_min if total_min > 0 else 1.0))
        t.leg = tuple(legs)
        avg_speed = (total_km / (total_min / 60.0)) if total_min > 0 else 0.0
        return total_min * 60.0, avg_speed

    def _step_truck(self, t: TruckState, dt_s: float, dt_h: float, eff: EffectiveParams) -> None:
        if self.maint.is_down(t.name):
            t.last_dump_h = -1.0  # repair time is not haul-cycle time
            if t.phase != "down":
                t.phase = "down"
            t.speed_kmh = 0.0
            t.fuel_lph = 0.0
            return
        if t.phase == "down":
            t.phase = "init"  # rejoin via the full dispatch decision, not a stale assignment
            t.phase_remaining_s = 0.0
            t.assigned_shovel = ""

        idle_mult = self.weather.idle_fuel_multiplier()
        t.fuel_lph = energy_mod.truck_fuel_lph(t.cls, t.phase, idle_mult)

        t.phase_remaining_s -= dt_s
        if t.phase_remaining_s > 0.0:
            return
        self._transition_truck(t, eff)

    @staticmethod
    def _enter_phase(t: TruckState, phase: str, duration_s: float) -> None:
        t.phase = phase
        t.phase_total_s = max(duration_s, 0.01)
        t.phase_remaining_s = duration_s

    def _transition_truck(self, t: TruckState, eff: EffectiveParams) -> None:
        now_s = self.sim_time_h * 3600.0

        if t.phase in ("haul_empty", "init"):
            eligible = self._eligible_shovels(t.route)
            if eff.dispatch_policy == "fixed":
                planned = t.manual_shovel or roster.FIXED_SHOVEL_ASSIGNMENT.get(t.name, "")
                if eligible and planned not in eligible:
                    # No dispatch system: the truck waits at its broken shovel until a supervisor
                    # reassigns it by radio; the new assignment then holds until shift change.
                    if t.reassign_wait_since_h < 0.0:
                        t.reassign_wait_since_h = self.sim_time_h
                    if self.sim_time_h - t.reassign_wait_since_h < C.MANUAL_REASSIGN_H:
                        t.assigned_shovel = planned
                        self._enter_phase(t, "init", C.NO_SHOVEL_RETRY_S)
                        return
                    t.manual_shovel = eligible[0]
                    t.reassign_wait_since_h = -1.0
                    self._log(f"{t.name}: reassigned by radio to {t.manual_shovel} after "
                              f"{C.MANUAL_REASSIGN_H * 60:.0f} min idle (no dispatch system)")
                fixed_plan = {t.name: t.manual_shovel or roster.FIXED_SHOVEL_ASSIGNMENT.get(t.name, "")}
            else:
                t.manual_shovel = ""
                t.reassign_wait_since_h = -1.0
                fixed_plan = roster.FIXED_SHOVEL_ASSIGNMENT
            # With every shovel on this route down there is nothing to load from: wait and ask again.
            shovel = dispatch_mod.choose_shovel(eff.dispatch_policy, t.name, eligible,
                                                 self.shovel_busy_until_s, {s: self._shovel_grade(s) for s in eligible},
                                                 fixed_plan, now_s) if eligible else ""
            t.assigned_shovel = shovel
            if not shovel:
                t.last_dump_h = -1.0  # idle with no shovel to go to: not haul-cycle time
                self._enter_phase(t, "init", C.NO_SHOVEL_RETRY_S)
                return
            service_start = max(now_s, self.shovel_busy_until_s.get(shovel, now_s))
            wait_s = max(0.0, service_start - now_s)
            x80 = self.last_x80_mm
            hydraulic_pen = self.weather.hydraulic_penalty()
            swing_s = shovel_model.swing_time_s(x80_mm=x80, hydraulic_penalty=hydraulic_pen)
            n_pass = truck_model.passes_per_truck(C.TRUCK_SPECS[t.cls]["payload_t"],
                                                   C.SHOVEL_BUCKET_M3["ore" if t.route == "ore" else "waste"])
            load_s = truck_model.load_time_min(n_pass, swing_s / 60.0) * 60.0
            spot_mode = C.SPOT_AT_SHOVEL_TRI[1] * 60.0
            self.shovel_busy_until_s[shovel] = service_start + spot_mode + load_s
            self._enter_phase(t, "queue_shovel", wait_s)
            return

        if t.phase in ("queue_shovel", "spot_load") and t.assigned_shovel not in self._eligible_shovels(t.route):
            # The shovel broke down (or was closed off) while this truck waited: back to dispatch.
            t.assigned_shovel = ""
            self._enter_phase(t, "init", 0.0)
            return

        if t.phase == "queue_shovel":
            self._enter_phase(t, "spot_load", _tri(self.rng, *[x * 60.0 for x in C.SPOT_AT_SHOVEL_TRI]))
            return

        if t.phase == "spot_load":
            n_pass = truck_model.passes_per_truck(C.TRUCK_SPECS[t.cls]["payload_t"],
                                                    C.SHOVEL_BUCKET_M3["ore" if t.route == "ore" else "waste"])
            x80 = self.last_x80_mm
            hydraulic_pen = self.weather.hydraulic_penalty()
            swing_s = shovel_model.swing_time_s(x80_mm=x80, hydraulic_penalty=hydraulic_pen)
            self._enter_phase(t, "loading", truck_model.load_time_min(n_pass, swing_s / 60.0) * 60.0)
            t.grade_at_load_pct = self._shovel_grade(t.assigned_shovel) if t.route == "ore" else 0.0
            return

        if t.phase == "loading":
            t.payload_t = C.TRUCK_SPECS[t.cls]["payload_t"]
            dur_s, speed = self._travel_time_and_speed(t, loaded=True, eff=eff)
            t.speed_kmh = speed
            self._enter_phase(t, "haul_loaded", dur_s)
            return

        if t.phase == "haul_loaded":
            if t.route == "ore":
                bay = min(range(2), key=lambda i: self.dump_bay_busy_until_s[i])
                service_start = max(now_s, self.dump_bay_busy_until_s[bay])
                wait_s = max(0.0, service_start - now_s)
                dump_mode = C.SPOT_DUMP_TRI[1] * 60.0
                self.dump_bay_busy_until_s[bay] = service_start + dump_mode
                t.dump_bay = bay
                self._enter_phase(t, "queue_dump", wait_s)
            else:
                self._enter_phase(t, "queue_dump", 0.0)
            return

        if t.phase == "queue_dump":
            if t.route == "ore" and self.stockpile_rom.headroom() < t.payload_t:
                # The ROM pad is full because the plant is not drawing it down: wait at the dump.
                if not self.rom_full_alert:
                    self.rom_full_alert = True
                    self._log("stockpile-rom: pad full -> ore trucks wait at the crusher dump")
                self._enter_phase(t, "queue_dump", C.NO_SHOVEL_RETRY_S)
                return
            self._enter_phase(t, "dumping", _tri(self.rng, *[x * 60.0 for x in C.SPOT_DUMP_TRI]))
            return

        if t.phase == "dumping":
            if t.route == "ore":
                t.just_dumped_ore_t = t.payload_t
                t.just_dumped_ore_grade = t.grade_at_load_pct
            else:
                t.just_dumped_waste_t = t.payload_t
            t.trips_total += 1
            dur_s, speed = self._travel_time_and_speed(t, loaded=False, eff=eff)
            t.speed_kmh = speed
            t.payload_t = 0.0
            self._enter_phase(t, "haul_empty", dur_s)
            return

        # fallback / first tick
        self._enter_phase(t, "haul_empty", 1.0)

    # -------------------------------------------------------------------- plant
    def _step_plant(self, dt_h: float, eff: EffectiveParams) -> dict:
        pf_ratio = eff.blast_powder_factor
        crusher_power_factor = max(0.80, min(1.05, 1.0 - 0.24 * (pf_ratio - 1.0)))
        crusher_down = self.maint.is_down(roster.CRUSHER_NAME)
        crusher_cap_tph = 0.0 if crusher_down else (C.CRUSHER_RATED_TPH * eff.crusher_availability
                                                     * crusher_power_factor)
        # Grade control: when the ROM ore grade falls below target and the fleet-management
        # system is running (dynamic dispatch), a loader reclaims high-grade ore into the
        # crusher feed in the proportion that restores the target grade (capped by loader rate).
        # The crusher stops when the crushed-ore stockpile is full (plant back-pressure).
        crush_limit_t = min(crusher_cap_tph * dt_h, self.stockpile_crushed.headroom())
        rom_avail = min(crush_limit_t, self.stockpile_rom.mass_t)
        rom_grade = self.stockpile_rom.grade_pct
        hg_t = 0.0
        hg_grade = self.stockpile_hg.grade_pct
        if eff.dispatch_policy == "dynamic":  # grade control is part of the fleet-management system
            hg_t = grade_mod.high_grade_reclaim_t(rom_avail, rom_grade, hg_grade, self.stockpile_hg.mass_t,
                                                  C.GC_TARGET_GRADE_PCT, C.GC_RECLAIM_MAX_TPH * dt_h)
            if hg_t > 0.0:
                hg_t, hg_grade = self.stockpile_hg.draw(hg_t)
                rom_avail = min(rom_avail, max(0.0, crush_limit_t - hg_t))
        drawn_t, feed_grade = self.stockpile_rom.draw(rom_avail)
        if hg_t > 0.0:
            feed_grade = (drawn_t * feed_grade + hg_t * hg_grade) / (drawn_t + hg_t)
            drawn_t += hg_t
        self.gc_reclaim_tph = hg_t / dt_h if dt_h > 0 else 0.0
        if hg_t > 0.0:
            self.gc_last_reclaim_h = self.sim_time_h
        # Report reclaim as one episode until it has been idle for an hour (the ROM pad empties
        # between truck dumps, which would otherwise toggle it every few minutes).
        active = self.sim_time_h - self.gc_last_reclaim_h < 1.0
        if active != self.gc_active:
            self.gc_active = active
            if active:
                self._log(f"grade control: ROM grade {rom_grade:.3f}% below {C.GC_TARGET_GRADE_PCT:.2f}% target "
                          f"-> reclaiming high-grade stockpile (loader up to {C.GC_RECLAIM_MAX_TPH:,.0f} t/h)")
            else:
                self._log("grade control: ROM grade back on target, high-grade reclaim stopped")
        self.stockpile_crushed.add(drawn_t, feed_grade)
        self.last_crusher_tph = drawn_t / dt_h if dt_h > 0 else 0.0

        frag = blast_model.fragmentation_for_powder_factor(C.POWDER_FACTOR_BASE * pf_ratio)
        self.last_x80_mm = frag["x80_mm"]
        frag_ref = blast_model.fragmentation_for_powder_factor(C.POWDER_FACTOR_BASE)

        sag_down = self.maint.is_down(roster.MILL_SAG_NAME)
        sag_desired_tph = 0.0 if sag_down else comm_model.sag_tph_surrogate(
            C.SAG_RATED_TPH, eff.sag_power_fraction, eff.axb, C.AXB_BASE,
            frag_ref["x80_mm"], frag["x80_mm"], frag["fines_25mm_frac"], frag_ref["fines_25mm_frac"])
        balls_up = [n for n in roster.MILL_BALL_NAMES if not self.maint.is_down(n)]
        # Each ball mill takes half of the SAG product: one down halves the circuit's capacity.
        sag_desired_tph = min(sag_desired_tph, C.BALL_MILL_MAX_TPH * len(balls_up))
        sag_draw = min(sag_desired_tph * dt_h, self.stockpile_crushed.mass_t)
        sag_drawn_t, mill_feed_grade = self.stockpile_crushed.draw(sag_draw)
        self.last_sag_tph = sag_drawn_t / dt_h if dt_h > 0 else 0.0
        self.last_mill_feed_grade = mill_feed_grade if sag_drawn_t > 0 else self.last_mill_feed_grade

        p80 = comm_model.hardness_adjusted_p80(C.BOND_P80_UM_BASE, C.BWI_BASE_KWHT, eff.ore_wi_kwht,
                                                hold_tph=True)
        self.last_p80_um = p80
        self.last_sag_power_fraction = eff.sag_power_fraction
        cu_rec = flot_model.cu_recovery(self.last_mill_feed_grade, p80_um=p80,
                                         tph_now=self.last_sag_tph or 1.0, tph_ref=C.SAG_RATED_TPH)
        au_rec = flot_model.au_recovery(clay_fraction=0.0)
        self.last_cu_recovery = cu_rec
        self.last_au_recovery = au_rec

        # Mills draw their full available power while throughput is limited by power or ore hardness;
        # they draw less only when starved of feed (load = actual / possible throughput right now).
        nl = C.MILL_NO_LOAD_POWER_FRACTION
        load = min(1.0, self.last_sag_tph / sag_desired_tph) if sag_desired_tph > 0 else 0.0
        self.last_mill_power_kw = {roster.MILL_SAG_NAME: 0.0 if sag_down else
                                   C.SAG_POWER_MW * 1000.0 * eff.sag_power_fraction * (nl + (1 - nl) * load)}
        self.last_ball_tph = {}
        for n in roster.MILL_BALL_NAMES:
            b_tph = self.last_sag_tph / len(balls_up) if n in balls_up and balls_up else 0.0
            self.last_ball_tph[n] = b_tph
            self.last_mill_power_kw[n] = (0.0 if n not in balls_up or sag_down else
                                          C.BALL_MILL_POWER_MW_EACH * 1000.0 * eff.sag_power_fraction * (nl + (1 - nl) * load))
        mill_power_kw = sum(self.last_mill_power_kw.values())
        crusher_power_kw = 750.0  # [R] S3 gyratory rated power
        conveyor_power_kw = 3640.0 if self.last_crusher_tph > 0 else 500.0  # [R] S3 overland conveyor
        plant_fixed_power_kw = mill_power_kw + crusher_power_kw + conveyor_power_kw

        return {
            "crusher_tph": self.last_crusher_tph,
            "sag_tph": self.last_sag_tph,
            "mill_feed_grade_pct": self.last_mill_feed_grade,
            "p80_um": p80,
            "x80_mm": self.last_x80_mm,
            "cu_recovery": cu_rec,
            "au_recovery": au_rec,
            "plant_power_kw": plant_fixed_power_kw,
        }

    # -------------------------------------------------------------------- KPIs
    def _step_kpi(self, dt_h: float, eff: EffectiveParams, truck_fuel_l: float, trolley: dict,
                  plant: dict) -> None:
        tph = plant["sag_tph"]
        f_cu = plant["mill_feed_grade_pct"]
        r_cu = plant["cu_recovery"]
        r_au = plant["au_recovery"]
        g_au = f_cu * C.AU_TO_CU_GRADE_RATIO

        cu_tph = econ_model.cu_tph(tph, f_cu, r_cu)
        au_ozph = econ_model.au_ozph(tph, g_au, r_au)
        nsr = econ_model.nsr_usd_h(cu_tph, au_ozph, eff.cu_price_usd_t, C.AU_PRICE_USD_OZ, eff.tc_rc_usd_t)

        truck_fuel_lph = truck_fuel_l / dt_h if dt_h > 0 else 0.0
        # Instantaneous fleet burn swings with how many trucks are climbing loaded at this moment;
        # report it as a one-mine-hour moving average like the other pit-side rates.
        inst = truck_fuel_lph + trolley["diesel_l_h"]
        if self.ema_diesel_lph <= 0.0:
            self.ema_diesel_lph = inst
        else:
            self.ema_diesel_lph += (inst - self.ema_diesel_lph) * min(1.0, dt_h / C.KPI_EMA_TAU_H)
        diesel_lph = self.ema_diesel_lph
        # Trolley grid draw smoothed the same way, so diesel saved and grid added stay consistent.
        self.ema_trolley_kwh_h += (trolley["grid_kwh_h"] - self.ema_trolley_kwh_h) * min(1.0, dt_h / C.KPI_EMA_TAU_H)
        # Conveyor and crusher draw switch on and off with each truck dump; smooth like the rest.
        if self.ema_plant_kw <= 0.0:
            self.ema_plant_kw = plant["plant_power_kw"]
        else:
            self.ema_plant_kw += (plant["plant_power_kw"] - self.ema_plant_kw) * min(1.0, dt_h / C.KPI_EMA_TAU_H)
        grid_kwh_h = self.ema_plant_kw + self.ema_trolley_kwh_h

        strip_ratio = (self.waste_total_t / self.ore_total_t) if self.ore_total_t > 0 else C.STRIP_RATIO_BASE
        # diesel_lph and grid_kwh_h already include the trolley's diesel saved and grid added, so
        # margin and CO2 computed from them carry its net effect once (no separate trolley term).
        margin = econ_model.margin_usd_h(nsr, tph, strip_ratio, grid_kwh_h, diesel_lph)
        co2_t_h = econ_model.co2_t_h(grid_kwh_h / 1000.0, diesel_lph)

        self.cu_output_total_t += cu_tph * dt_h
        self.au_output_total_oz += au_ozph * dt_h
        self.diesel_total_l += 0.0  # already accumulated in step()
        self.grid_total_kwh += grid_kwh_h * dt_h
        self.co2_total_kg += co2_t_h * 1000.0 * dt_h

        self.last_kpi = {
            "tph": tph,
            "cu_tph": cu_tph,
            "au_ozph": au_ozph,
            "nsr_usd_h": nsr,
            "margin_usd_h": margin,
            "energy_kwh_h": grid_kwh_h,
            "fuel_l_h": diesel_lph,
            "co2_t_h": co2_t_h,
            "strip_ratio": strip_ratio,
            "ore_mined_tph": self.ema_ore_tph,
            "moved_tph": self.ema_ore_tph + self.ema_waste_tph,
            "mined_grade_pct": (100.0 * self.ema_ore_cu_tph / self.ema_ore_tph) if self.ema_ore_tph > 1.0 else 0.0,
            "cu_mined_tph": self.ema_ore_cu_tph,
            "haul_cycle_min": self.ema_cycle_min,
            "fleet_avail_pct": 100.0 * self.trucks_available() / len(roster.TRUCK_NAMES),
            "buffer_h": self.buffer_hours(),
            # Grinding energy per tonne milled (SAG + ball mills); 0 while nothing is milled.
            "mill_kwh_t": (sum(self.last_mill_power_kw.values()) / self.last_sag_tph) if self.last_sag_tph > 1.0 else 0.0,
        }
