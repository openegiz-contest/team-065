"""
Scenario control: the 13-field kz.kyzyltas.mine:scenario twin (created by mine/setup),
the active_scenario ids shared with the interface (mine/ui/src/lib/scenarios.ts), echo-suppressing
event parsing, and the mapping from (active_scenario, the fields) to the concrete internal
simulation parameters that realise each of 03_domain.md §11's 12 what-if causal chains, the S11
fleet-size variant and the "custom" scenario (the twin's fields applied as set).

Each scenario is a documented preset (SCENARIO_PRESETS below). The twin's fields are live knobs that
compose with any preset: a field left at its baseline value leaves the preset in charge, a field set
away from it overrides the preset (e.g. a cold snap at a different temperature, or shovel_down_id
singling out another shovel). Wind, slope-radar velocity and fume-delay length exist only in presets.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from models import constants as C

# active_scenario values; the interface uses the same ids.
VALID_SCENARIOS = [
    "none",
    "shovel_failure",          # S1
    "weather_cold_snap",       # S2
    "blast_intensify",         # S3
    "hard_ore_domain",         # S4
    "grid_curtailment",        # S5
    "road_thaw",               # S6
    "slope_alarm",             # S7
    "blast_delay",             # S8
    "predictive_maintenance",  # S9
    "price_drop",              # S10
    "dispatch_fixed",          # S11
    "fleet_minus_2",           # S11 variant
    "trolley_assist",          # S12
    "custom",                  # parameters set directly on the scenario twin
]


@dataclass(frozen=True)
class ScenarioFields:
    """Mirrors kz.kyzyltas.mine:scenario exactly: 13 fields."""
    active_scenario: str = "none"
    run_id: str = "baseline"
    truck_count_delta: float = 0.0
    shovel_down_id: str = ""
    crusher_availability: float = 1.0
    blast_powder_factor: float = 1.0
    fan_speed_factor: float = 1.0
    dispatch_policy: str = "dynamic"
    # Numeric what-if parameters; at their baseline value they leave the preset in charge.
    ambient_temp_c: float = C.TEMP_BASELINE_C
    ore_bwi_kwht: float = C.BWI_BASE_KWHT
    mill_power_factor: float = 1.0
    road_rr_bonus_pct: float = 0.0
    cu_price_usd_t: float = C.CU_PRICE_USD_T_BASE


@dataclass(frozen=True)
class Preset:
    """Internal-only parameters a scenario drives, beyond the 8 twin fields."""
    ambient_temp_c: float = C.TEMP_BASELINE_C
    wind_ms: float = C.WIND_BASELINE_MS
    ore_wi_kwht: float = C.BWI_BASE_KWHT
    axb: float = C.AXB_BASE
    road_rr_bonus_pct: float = 0.0       # added to the base RR of every road segment
    slope_velocity_mmday: float = 0.0
    gas_extra_delay_min: float = 0.0
    cu_price_usd_t: float = C.CU_PRICE_USD_T_BASE
    tc_rc_usd_t: float = C.TC_RC_USD_PER_T
    trolley_on: bool = False
    predictive_maintenance_on: bool = False
    default_shovel_down: str = ""
    default_truck_count_delta: float = 0.0
    default_dispatch_policy: Optional[str] = None
    default_blast_powder_factor: Optional[float] = None
    sag_power_fraction: float = 1.0
    gas_block_shovels: tuple = ()
    close_main_ore_ramp: bool = False
    narrative: str = "Baseline operation, no scenario active."


SCENARIO_PRESETS: dict[str, Preset] = {
    "none": Preset(narrative="Baseline: all parameters at twin defaults."),
    "shovel_failure": Preset(
        default_shovel_down="shovel-s2",
        narrative=('Ore shovel S2 (the 0.58% Cu face) is down for a 10-hour hydraulic repair -> dispatch sends its trucks to the other ore shovel -> less ore and lower-grade ore reach the ROM pad -> grade control reclaims the high-grade stockpile while the crushed-ore buffer feeds the mill. 03_domain.md §11-S1.'),
    ),
    "weather_cold_snap": Preset(
        ambient_temp_c=C.TEMP_WINTER_EXTREME_C, wind_ms=C.WIND_BLIZZARD_MS,
        narrative=('-38 C and 12 m/s wind until undone -> winter speed caps, slower shovel hydraulics, more idle fuel, no haul-road watering below 0 C -> longer haul cycles, less ore mined, more road dust. 03_domain.md §11-S2.'),
    ),
    "blast_intensify": Preset(
        default_blast_powder_factor=C.POWDER_FACTOR_INTENSIFIED / C.POWDER_FACTOR_BASE,  # ~1.333
        narrative=('Powder factor 0.30 -> 0.40 kg/t -> finer fragmentation (Kuz-Ram) -> the SAG mill takes more ore -> more copper and revenue; the crushed-ore stockpile is drawn down. 03_domain.md §11-S3.'),
    ),  # blast_powder_factor is read live from the twin field; this default only applies if the
        # UI hasn't already set that field away from 1.0 (see resolve_effective()).
    "hard_ore_domain": Preset(
        ore_wi_kwht=16.0, axb=32.0,
        narrative=('Harder ore domain (Bond Wi 14 -> 16 kWh/t, Axb 45 -> 32) -> more grinding energy per tonne at full mill power -> lower mill throughput, copper and revenue; the crushed-ore buffer covers more hours of mill feed. 03_domain.md §11-S4.'),
    ),
    "grid_curtailment": Preset(
        sag_power_fraction=0.75,
        narrative=('Grid curtailment until undone -> SAG and ball mills limited to 75% of their power -> lower mill throughput and copper, less grid energy and CO2; the crushed-ore buffer covers more hours of feed. 03_domain.md §11-S5.'),
    ),
    "road_thaw": Preset(
        road_rr_bonus_pct=2.5,
        narrative=('Spring thaw: haul-road rolling resistance +2.5 points on every segment -> slower loaded climbs -> longer haul cycles, less ore mined, more fuel per tonne. 03_domain.md §11-S6.'),
    ),
    "slope_alarm": Preset(
        slope_velocity_mmday=55.0, close_main_ore_ramp=True,
        narrative=('East-wall slope radar red alarm -> main ore ramp closed -> ore trucks detour via the alternate ramp (2.7 km instead of 1.2 km) -> longer haul cycles, less ore mined. 03_domain.md §11-S7.'),
    ),
    "blast_delay": Preset(
        gas_extra_delay_min=120.0, wind_ms=0.5, ambient_temp_c=-12.0,
        gas_block_shovels=("shovel-s1", "shovel-s3"),
        narrative=('Post-blast fumes trapped by a winter inversion -> re-entry 30 -> 150 min -> shovels S1 and S3 idle for the clearance window -> less ore mined, then recovery; the stockpile protects the mill. 03_domain.md §11-S8.'),
    ),
    "predictive_maintenance": Preset(
        predictive_maintenance_on=True,
        narrative=("Condition monitoring (coolant temperature, oil iron trend) raises work orders for "
                   "trucks nearing a wear-out failure and repairs them at the next shift change instead "
                   "of running them to failure -> fewer unplanned failures and tows; the gain builds "
                   "over days of mine time (literature: +2..3 pp availability). Random faults stay "
                   "unpredictable. 03_domain.md §11-S9."),
    ),
    "price_drop": Preset(
        cu_price_usd_t=C.CU_PRICE_USD_T_SHOCK, tc_rc_usd_t=C.TC_RC_USD_PER_T_SHOCK,
        narrative=('Copper price $14,500 -> $10,900/t and TC/RC +$80/dmt -> lower net smelter revenue with unchanged physical output. 03_domain.md §11-S10.'),
    ),
    "dispatch_fixed": Preset(
        default_dispatch_policy="fixed",
        narrative=("Fleet-management system offline (e.g. a comms outage): trucks stay on their "
                   "shift-plan shovels and grade control stops reclaiming high-grade ore. With balanced "
                   "shovels and a truck-limited fleet (match factor < 1) the tonnage loss is small; the "
                   "system's value shows when a shovel fails or the ore grade drops. 03_domain.md §11-S11."),
    ),
    "fleet_minus_2": Preset(
        default_truck_count_delta=-2.0,
        narrative=("Fleet reduced by 2 trucks (breakdown/reassignment) -> match factor falls -> "
                   "shovel-limited queueing drops but material moved falls roughly in proportion "
                   "to the lost truck-hours. 03_domain.md §11-S11 variant (fleet-size lever)."),
    ),
    "custom": Preset(
        narrative=("Custom what-if: the values on the scenario twin apply directly -- shovel out of service, trucks "
                   "parked, crusher availability, blast powder factor, dispatch mode, air temperature, ore hardness, "
                   "mill power, haul-road rolling resistance and copper price."),
    ),
    "trolley_assist": Preset(
        trolley_on=True,
        narrative=("Trolley assist energised on the 1.2 km main ore ramp -> the two AC-electric Komatsu 830E "
                   "trucks climb it about twice as fast on grid power -> their diesel falls and grid draw "
                   "rises, so CO2 stays about flat on the coal-heavy Kazakh grid (break-even ~0.64 kg/kWh, "
                   "grid here 0.80). 03_domain.md §11-S12 / §6.4."),
    ),
}


@dataclass(frozen=True)
class EffectiveParams:
    """Fully-resolved parameters for one simulation tick, combining the live twin fields with
    the active scenario's preset. This is what Simulation.step() actually consumes."""
    active_scenario: str
    run_id: str
    ambient_temp_c: float
    wind_ms: float
    ore_wi_kwht: float
    axb: float
    road_rr_bonus_pct: float
    slope_velocity_mmday: float
    gas_extra_delay_min: float
    cu_price_usd_t: float
    tc_rc_usd_t: float
    trolley_on: bool
    predictive_maintenance_on: bool
    shovel_down_id: str
    truck_count_delta: int
    dispatch_policy: str
    crusher_availability: float
    blast_powder_factor: float
    fan_speed_factor: float
    close_main_ore_ramp: bool
    sag_power_fraction: float
    gas_block_shovels: tuple
    narrative: str


def resolve_effective(fields: ScenarioFields) -> EffectiveParams:
    """Pure function: twin fields + active_scenario -> fully resolved simulation parameters."""
    preset = SCENARIO_PRESETS.get(fields.active_scenario, SCENARIO_PRESETS["none"])

    # Accept a full thingId ("kz.kyzyltas.mine:shovel-s2") as well as the bare name ("shovel-s2").
    shovel_down = (fields.shovel_down_id or preset.default_shovel_down).split(":")[-1]
    truck_delta = fields.truck_count_delta
    if truck_delta == 0.0 and preset.default_truck_count_delta:
        truck_delta = preset.default_truck_count_delta
    dispatch_policy = fields.dispatch_policy
    if dispatch_policy == "dynamic" and preset.default_dispatch_policy:
        dispatch_policy = preset.default_dispatch_policy

    blast_powder_factor = fields.blast_powder_factor
    if blast_powder_factor == 1.0 and preset.default_blast_powder_factor:
        blast_powder_factor = preset.default_blast_powder_factor

    def chosen(field_value: float, baseline: float, preset_value: float) -> float:
        """A twin field set away from its baseline wins; otherwise the scenario preset applies."""
        return float(field_value) if abs(float(field_value) - baseline) > 1e-9 else preset_value

    ambient_temp_c = chosen(fields.ambient_temp_c, C.TEMP_BASELINE_C, preset.ambient_temp_c)
    ore_wi = chosen(fields.ore_bwi_kwht, C.BWI_BASE_KWHT, preset.ore_wi_kwht)
    # [A] Axb falls as Bond Wi rises, on the line through (14, 45) and (16, 32) of §11-S4.
    axb = preset.axb if ore_wi == preset.ore_wi_kwht else max(10.0, C.AXB_BASE - 6.5 * (ore_wi - C.BWI_BASE_KWHT))
    sag_power_fraction = chosen(fields.mill_power_factor, 1.0, preset.sag_power_fraction)
    road_rr_bonus = chosen(fields.road_rr_bonus_pct, 0.0, preset.road_rr_bonus_pct)
    cu_price = chosen(fields.cu_price_usd_t, C.CU_PRICE_USD_T_BASE, preset.cu_price_usd_t)

    return EffectiveParams(
        active_scenario=fields.active_scenario,
        run_id=fields.run_id,
        ambient_temp_c=ambient_temp_c,
        wind_ms=preset.wind_ms,
        ore_wi_kwht=ore_wi,
        axb=axb,
        road_rr_bonus_pct=road_rr_bonus,
        slope_velocity_mmday=preset.slope_velocity_mmday,
        gas_extra_delay_min=preset.gas_extra_delay_min,
        cu_price_usd_t=cu_price,
        tc_rc_usd_t=preset.tc_rc_usd_t,
        trolley_on=preset.trolley_on,
        predictive_maintenance_on=preset.predictive_maintenance_on,
        shovel_down_id=shovel_down,
        truck_count_delta=int(truck_delta),
        dispatch_policy=dispatch_policy,
        crusher_availability=fields.crusher_availability,
        blast_powder_factor=blast_powder_factor,
        fan_speed_factor=max(fields.fan_speed_factor, 0.01),
        close_main_ore_ramp=preset.close_main_ore_ramp,
        sag_power_fraction=sag_power_fraction,
        gas_block_shovels=preset.gas_block_shovels,
        narrative=preset.narrative,
    )


BASELINE_FIELDS = ScenarioFields()
BASELINE_EFFECTIVE = resolve_effective(BASELINE_FIELDS)


class ScenarioEventParser:
    """
    Parses Ditto-protocol events arriving on opentwins/twin/events/<ns>/scenario and extracts
    the (possibly partial) feature values, suppressing echoes of our own no-op writes.
    """

    def __init__(self) -> None:
        self.last_applied = BASELINE_FIELDS

    @staticmethod
    def _extract_feature_values(payload: dict) -> dict:
        path = payload.get("path", "")
        value = payload.get("value")
        out: dict = {}
        if value is None:
            return out
        if path == "/features" and isinstance(value, dict):
            for fname, fval in value.items():
                if isinstance(fval, dict) and "properties" in fval:
                    out[fname] = fval["properties"].get("value")
        elif path == "/" and isinstance(value, dict):
            feats = value.get("features", {})
            for fname, fval in feats.items():
                if isinstance(fval, dict) and "properties" in fval:
                    out[fname] = fval["properties"].get("value")
        elif path.startswith("/features/"):
            # Narrow path -- not the convention, but handle defensively.
            parts = path.split("/")
            if len(parts) >= 3:
                fname = parts[2]
                if isinstance(value, dict) and "value" in value:
                    out[fname] = value["value"]
                elif not isinstance(value, dict):
                    out[fname] = value
        return out

    def apply_event(self, payload: dict) -> Optional[ScenarioFields]:
        """Returns the new ScenarioFields if anything actually changed, else None (echo/no-op)."""
        changes = self._extract_feature_values(payload)
        if not changes:
            return None
        current = self.last_applied
        kwargs = {}
        changed_any = False
        for fname, fval in changes.items():
            if not hasattr(current, fname):
                continue
            if getattr(current, fname) != fval:
                kwargs[fname] = fval
                changed_any = True
        if not changed_any:
            return None  # echo of our own last-applied state -- ignore
        new_fields = replace(current, **kwargs)
        self.last_applied = new_fields
        return new_fields

    def seed(self, fields: ScenarioFields) -> None:
        self.last_applied = fields
