"""
Equipment roster: the exact twin IDs this engine publishes to.

These IDs are fixed by agreement with mine/setup (see the coordinator sync note recorded in
mine/setup/model.json) -- mine/setup creates these twins; mine/engine must use exactly these names, not its
own invented convention. Namespace is kz.kyzyltas.mine; thingId = f"{NAMESPACE}:{name}".

Twin ID source of truth (from mine/setup, final):
  trucks        truck-01..truck-14   (12x Cat 785C, 2x Komatsu 830E-5 AC electric: truck-11/12,
                                       the only trucks that can run on the trolley line)
  shovels       shovel-s1..shovel-s4 (s1/s2 ore faces: s1=0.45%% Cu, s2=0.58%% Cu; s3/s4 waste)
  drills        drill-01, drill-02
  crusher       crusher-01
  conveyors     conveyor-01, conveyor-02
  mills         mill-sag-01, mill-ball-01, mill-ball-02
  flotation     flotation-01
  tailings      tailings-01
  stockpiles    stockpile-rom, stockpile-crushed, stockpile-waste
  fans          fan-plant-01, fan-pit-01
  substation    substation-01
  weather       weather-station-01
  slope radar   slope-radar-01, slope-radar-02
  benches       bench-01..bench-10 (01-06 ore faces, 07-10 waste faces)
  roads         road-ramp-ore-up, road-ramp-ore-down, road-ramp-ore2-up, road-ramp-ore2-down,
                road-ramp-waste-up, road-ramp-waste-down, road-haul-crusher-in, road-haul-crusher-out,
                road-haul-dump-in, road-haul-dump-out, road-service-plant, road-service-plant-return
  groups        dispatch, plant, pit, mine (root)
  roll-ups      kpi, scenario
"""
from __future__ import annotations

NAMESPACE = "kz.kyzyltas.mine"


def thing_id(name: str) -> str:
    return f"{NAMESPACE}:{name}"


# --- Trucks -----------------------------------------------------------------
TRUCK_NAMES = [f"truck-{i:02d}" for i in range(1, 15)]           # truck-01..truck-14
TRUCK_830E_NAMES = {"truck-11", "truck-12"}                       # AC electric drive, trolley-ready


def truck_class(name: str) -> str:
    return "KOM830E" if name in TRUCK_830E_NAMES else "CAT785C"


# Route split: 10 ore (truck-01..05, truck-10, truck-13, truck-14 and the two 830E on the ore ramp,
# see trolley_assist), 4 waste. Sized so ore haulage covers the 3,425 t/h SAG feed at ~90 % fleet
# availability: with 12 trucks the pit averaged ~2,940 t/h and the mill ran short.
TRUCK_ROUTE = {
    "truck-01": "ore", "truck-02": "ore", "truck-03": "ore", "truck-04": "ore", "truck-05": "ore",
    "truck-06": "waste", "truck-07": "waste", "truck-08": "waste", "truck-09": "waste", "truck-10": "ore",
    "truck-11": "ore", "truck-12": "ore", "truck-13": "ore", "truck-14": "ore",
}

# Fixed/locked per-truck shovel assignment -- the "fixed" dispatch_policy baseline (03_domain.md
# §2.8: "Fixed... hard-assigned to a shovel each shift"). "dynamic" dispatch ignores this and
# picks live by shortest queue (modules/dispatch.py).
FIXED_SHOVEL_ASSIGNMENT = {
    "truck-01": "shovel-s1", "truck-02": "shovel-s1", "truck-03": "shovel-s1", "truck-11": "shovel-s1",
    "truck-04": "shovel-s2", "truck-05": "shovel-s2", "truck-10": "shovel-s2", "truck-12": "shovel-s2",
    "truck-13": "shovel-s1", "truck-14": "shovel-s2",
    "truck-06": "shovel-s3", "truck-07": "shovel-s3", "truck-08": "shovel-s3",
    "truck-09": "shovel-s4",
}


# --- Shovels ------------------------------------------------------------------
SHOVEL_NAMES = ["shovel-s1", "shovel-s2", "shovel-s3", "shovel-s4"]
SHOVEL_ROLE = {"shovel-s1": "ore", "shovel-s2": "ore", "shovel-s3": "waste", "shovel-s4": "waste"}
SHOVEL_FACE_GRADE_PCT = {"shovel-s1": 0.45, "shovel-s2": 0.58, "shovel-s3": 0.0, "shovel-s4": 0.0}
# Ore lies at depth under a waste cap (bench materials as in mine/setup/model.json): the ore
# shovels work benches 06-07, the waste shovels benches 02-03.
SHOVEL_BENCH = {"shovel-s1": "bench-06", "shovel-s2": "bench-07",
                "shovel-s3": "bench-02", "shovel-s4": "bench-03"}
ORE_SHOVELS = [n for n in SHOVEL_NAMES if SHOVEL_ROLE[n] == "ore"]
WASTE_SHOVELS = [n for n in SHOVEL_NAMES if SHOVEL_ROLE[n] == "waste"]

# --- Drills, fixed plant, conveyors -------------------------------------------
DRILL_NAMES = ["drill-01", "drill-02"]
CRUSHER_NAME = "crusher-01"
CONVEYOR_NAMES = ["conveyor-01", "conveyor-02"]
MILL_SAG_NAME = "mill-sag-01"
MILL_BALL_NAMES = ["mill-ball-01", "mill-ball-02"]
FLOTATION_NAME = "flotation-01"
TAILINGS_NAME = "tailings-01"

# --- Stockpiles -----------------------------------------------------------
STOCKPILE_ROM = "stockpile-rom"
STOCKPILE_CRUSHED = "stockpile-crushed"
STOCKPILE_WASTE = "stockpile-waste"
STOCKPILE_HG = "stockpile-hg"  # high-grade reserve used by grade control

# --- Fans, substation, weather, radar ---------------------------------------
FAN_NAMES = ["fan-plant-01", "fan-pit-01"]
SUBSTATION_NAME = "substation-01"
WEATHER_NAME = "weather-station-01"
RADAR_NAMES = ["slope-radar-01", "slope-radar-02"]

# --- Benches ------------------------------------------------------------------
BENCH_NAMES = [f"bench-{i:02d}" for i in range(1, 11)]  # bench-01..bench-10
BENCH_ROLE = {f"bench-{i:02d}": ("ore" if i in (5, 6, 7, 8, 10) else "waste") for i in range(1, 11)}

# --- Road segments --------------------------------------------------------
# grade_pct: + = uphill for a loaded truck travelling "up"/"in" direction; length_m one-way.
ROAD_SEGMENTS = {
    # Main ore ramp (closed by slope_alarm TARP red; trolley_assist applies here per §11-S12).
    "road-ramp-ore-up":    {"grade_pct": 9.0,  "length_m": 1200.0, "kind": "ramp_up"},
    "road-ramp-ore-down":  {"grade_pct": -9.0, "length_m": 1200.0, "kind": "ramp_down"},
    # Alternate/detour ore ramp (longer) -- used when the main ramp is closed.
    "road-ramp-ore2-up":   {"grade_pct": 8.0,  "length_m": 2700.0, "kind": "ramp_up"},
    "road-ramp-ore2-down": {"grade_pct": -8.0, "length_m": 2700.0, "kind": "ramp_down"},
    # Waste ramp
    "road-ramp-waste-up":   {"grade_pct": 8.0,  "length_m": 1000.0, "kind": "ramp_up"},
    "road-ramp-waste-down": {"grade_pct": -8.0, "length_m": 1000.0, "kind": "ramp_down"},
    # Flat haul to/from the crusher (ore route)
    "road-haul-crusher-in":  {"grade_pct": 0.0, "length_m": 1800.0, "kind": "flat"},
    "road-haul-crusher-out": {"grade_pct": 0.0, "length_m": 1800.0, "kind": "flat"},
    # Flat haul to/from the waste dump
    "road-haul-dump-in":  {"grade_pct": 0.0, "length_m": 2500.0, "kind": "flat"},
    "road-haul-dump-out": {"grade_pct": 0.0, "length_m": 2500.0, "kind": "flat"},
    # Low-traffic plant service road (ancillary vehicles only, not part of the truck cycle)
    "road-service-plant":        {"grade_pct": 0.0, "length_m": 600.0, "kind": "service"},
    "road-service-plant-return": {"grade_pct": 0.0, "length_m": 600.0, "kind": "service"},
}

# Ore haul route (loaded): main ramp up + flat in; detour variant uses ramp2.
ORE_ROUTE_MAIN = ["road-ramp-ore-up", "road-haul-crusher-in"]
ORE_ROUTE_MAIN_RETURN = ["road-haul-crusher-out", "road-ramp-ore-down"]
ORE_ROUTE_DETOUR = ["road-ramp-ore2-up", "road-haul-crusher-in"]
ORE_ROUTE_DETOUR_RETURN = ["road-haul-crusher-out", "road-ramp-ore2-down"]
WASTE_ROUTE = ["road-ramp-waste-up", "road-haul-dump-in"]
WASTE_ROUTE_RETURN = ["road-haul-dump-out", "road-ramp-waste-down"]

# --- Groups / roll-ups ------------------------------------------------------
GROUP_DISPATCH = "dispatch"
GROUP_PLANT = "plant"
GROUP_PIT = "pit"
GROUP_MINE = "mine"
KPI_NAME = "kpi"
SCENARIO_NAME = "scenario"
