#!/usr/bin/env python3
"""
engine.py -- entry point. Runs the Kyzyl-Tas mine simulation, publishes Ditto-protocol merge
commands over MQTT at a rate-limited cadence, subscribes to the scenario control twin, and runs a
shadow baseline (scenario always "none") in parallel so delta-vs-baseline can be published on the
kpi twin. Environment: MQTT_HOST, MQTT_PORT, SEED, SPEEDUP, TICK_HZ, PUBLISH_RATE_HZ, DITTO_URL/USER/PASSWORD.
"""
from __future__ import annotations

import logging
import os
import random
import time

import roster
import publish
import scenarios
from ditto_io import DittoConnection
from scenarios import ScenarioEventParser, resolve_effective, BASELINE_EFFECTIVE
from simulation import Simulation

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"),
                     format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("engine")


def env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


MQTT_HOST = os.environ.get("MQTT_HOST", "mosquitto")
MQTT_PORT = env_int("MQTT_PORT", 1883)
SEED = env_int("SEED", 3)
SPEEDUP = env_float("SPEEDUP", 60.0)
TICK_HZ = env_float("TICK_HZ", 5.0)
PUBLISH_RATE_HZ = env_float("PUBLISH_RATE_HZ", 28.0)

# Per-category publish rates (Hz). Sum(count * rate) is tuned to land at ~25-29 cmd/s total,
# inside a budget of <=20-30 Ditto commands/s across ALL twins. See below for the
# worked total.
RATE_TRUCK = 1.0
RATE_SHOVEL = 0.5
RATE_DRILL = 0.3
RATE_CRUSHER = 0.5
RATE_CONVEYOR = 0.5
RATE_MILL = 0.5
RATE_FLOTATION = 0.5
RATE_TAILINGS = 0.2
RATE_STOCKPILE = 0.3
RATE_FAN = 0.3
RATE_SUBSTATION = 0.5
RATE_WEATHER = 0.2
RATE_RADAR = 0.3
RATE_BENCH = 0.1
RATE_ROAD = 0.1
RATE_GROUP = 0.3
RATE_KPI = 1.0


class DueScheduler:
    """Tracks per-twin next-publish-due times (wall clock) so each twin is only built/enqueued
    at its own configured cadence, independent of the (much faster) simulation tick rate."""

    def __init__(self) -> None:
        self._next_due: dict[str, float] = {}

    def due(self, name: str, interval_s: float, now: float) -> bool:
        nd = self._next_due.get(name)
        if nd is None:
            # stagger first publish with a small jittered offset so twins don't all fire together
            self._next_due[name] = now + random.uniform(0.0, interval_s)
            return False
        if now >= nd:
            self._next_due[name] = now + interval_s
            return True
        return False


def _load_scenario_from_twin(parser: ScenarioEventParser) -> None:
    """Read the scenario twin once at start-up, so a restarted engine continues an active scenario."""
    import base64
    import json
    import urllib.request

    url = os.environ.get("DITTO_URL", "http://ditto-nginx:80").rstrip("/")
    user = os.environ.get("DITTO_USER", "ditto")
    password = os.environ.get("DITTO_PASSWORD", "")
    if not password:
        return
    req = urllib.request.Request(f"{url}/api/2/things/{roster.NAMESPACE}:scenario/features")
    req.add_header("Authorization", "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode())
    for _ in range(30):
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                features = json.loads(r.read().decode("utf-8"))
            fields = parser.apply_event({"topic": f"{roster.NAMESPACE}/scenario/things/twin/events/modified",
                                         "path": "/features", "value": features})
            if fields is not None:
                logger.info("start-up scenario from twin: active_scenario=%s", fields.active_scenario)
            return
        except Exception as exc:  # Ditto may still be warming up
            logger.info("scenario twin not readable yet (%s); retrying", exc)
            time.sleep(5)


def main() -> None:
    logger.info("starting mine engine: seed=%s speedup=%s mqtt=%s:%s", SEED, SPEEDUP, MQTT_HOST, MQTT_PORT)

    parser = ScenarioEventParser()

    def on_scenario_event(payload: dict) -> None:
        new_fields = parser.apply_event(payload)
        if new_fields is not None:
            logger.info("scenario updated: active_scenario=%s run_id=%s", new_fields.active_scenario,
                        new_fields.run_id)

    conn = DittoConnection(MQTT_HOST, MQTT_PORT, on_scenario_event, publish_rate_hz=PUBLISH_RATE_HZ)
    conn.start()
    if not conn.wait_connected(timeout=15.0):
        logger.warning("mqtt not yet connected after 15s; continuing, connect loop keeps retrying")

    _load_scenario_from_twin(parser)

    sim_real = Simulation(seed=SEED, label="real")
    sim_base = Simulation(seed=SEED, label="baseline")

    sched = DueScheduler()
    tick_interval_s = 1.0 / max(TICK_HZ, 0.1)

    try:
        _run_loop(conn, parser, sim_real, sim_base, sched, tick_interval_s)
    except KeyboardInterrupt:
        logger.info("interrupted, shutting down")
    finally:
        conn.stop()


def _run_loop(conn: DittoConnection, parser: ScenarioEventParser, sim_real: Simulation,
              sim_base: Simulation, sched: DueScheduler, tick_interval_s: float) -> None:
    pub = conn.publisher
    next_tick = time.monotonic()
    last_run_id = None
    while True:
        now = time.monotonic()
        if now < next_tick:
            time.sleep(min(next_tick - now, tick_interval_s))
            continue
        next_tick = now + tick_interval_s

        dt_sim_s = tick_interval_s * SPEEDUP
        fields = parser.last_applied
        eff = resolve_effective(fields)
        if eff.run_id != last_run_id:
            # A scenario was applied or undone: restart the shadow baseline as a copy of the live
            # mine, so the comparison measures this scenario rather than earlier history.
            if last_run_id is not None:
                sim_base = sim_real.clone_as_baseline()
            last_run_id = eff.run_id

        try:
            sim_real.step(dt_sim_s, eff)
            sim_base.step(dt_sim_s, BASELINE_EFFECTIVE)
        except Exception:
            # Never let a physics bug take the whole process down.
            logger.exception("simulation step failed, skipping this tick")
            continue

        _publish_all(pub, sched, now, sim_real, sim_base, eff)


def _publish_all(pub, sched: DueScheduler, now: float, sim: Simulation, sim_base: Simulation,
                  eff) -> None:
    for name in roster.TRUCK_NAMES:
        if sched.due(name, 1.0 / RATE_TRUCK, now):
            t = sim.trucks[name]
            feats = publish.build_truck_features(t)
            feats.update(publish.build_truck_health_features(sim, name))
            pub.enqueue(name, feats)

    for name in roster.SHOVEL_NAMES:
        if sched.due(name, 1.0 / RATE_SHOVEL, now):
            pub.enqueue(name, publish.build_shovel_features(sim, name))

    for name in roster.DRILL_NAMES:
        if sched.due(name, 1.0 / RATE_DRILL, now):
            pub.enqueue(name, publish.build_drill_features(sim, name, eff.blast_powder_factor))

    if sched.due(roster.CRUSHER_NAME, 1.0 / RATE_CRUSHER, now):
        pub.enqueue(roster.CRUSHER_NAME, publish.build_crusher_features(sim, eff))

    for i, name in enumerate(roster.CONVEYOR_NAMES):
        if sched.due(name, 1.0 / RATE_CONVEYOR, now):
            pub.enqueue(name, publish.build_conveyor_features(sim, i))

    if sched.due(roster.MILL_SAG_NAME, 1.0 / RATE_MILL, now):
        pub.enqueue(roster.MILL_SAG_NAME, publish.build_mill_features(sim, is_sag=True))
    for name in roster.MILL_BALL_NAMES:
        if sched.due(name, 1.0 / RATE_MILL, now):
            pub.enqueue(name, publish.build_mill_features(sim, is_sag=False, name=name))

    if sched.due(roster.FLOTATION_NAME, 1.0 / RATE_FLOTATION, now):
        pub.enqueue(roster.FLOTATION_NAME, publish.build_flotation_features(sim))

    if sched.due(roster.TAILINGS_NAME, 1.0 / RATE_TAILINGS, now):
        pub.enqueue(roster.TAILINGS_NAME, publish.build_tailings_features(sim))

    for name, sp in ((roster.STOCKPILE_ROM, sim.stockpile_rom),
                      (roster.STOCKPILE_CRUSHED, sim.stockpile_crushed),
                      (roster.STOCKPILE_WASTE, sim.stockpile_waste),
                      (roster.STOCKPILE_HG, sim.stockpile_hg)):
        if sched.due(name, 1.0 / RATE_STOCKPILE, now):
            feats = publish.build_stockpile_features(sp)
            if name == roster.STOCKPILE_HG:
                feats["reclaim_tph"] = publish.feat(round(sim.gc_reclaim_tph, 0), "t/h")
            pub.enqueue(name, feats)

    for name in roster.FAN_NAMES:
        if sched.due(name, 1.0 / RATE_FAN, now):
            pub.enqueue(name, publish.build_fan_features(eff, sim if name == "fan-pit-01" else None))

    if sched.due(roster.SUBSTATION_NAME, 1.0 / RATE_SUBSTATION, now):
        pub.enqueue(roster.SUBSTATION_NAME, publish.build_substation_features(sim))

    if sched.due(roster.WEATHER_NAME, 1.0 / RATE_WEATHER, now):
        pub.enqueue(roster.WEATHER_NAME, publish.build_weather_features(sim))

    for i, name in enumerate(roster.RADAR_NAMES):
        if sched.due(name, 1.0 / RATE_RADAR, now):
            pub.enqueue(name, publish.build_radar_features(eff, is_primary=(i == 0), sim=sim, name=name))

    for name in roster.BENCH_NAMES:
        if sched.due(name, 1.0 / RATE_BENCH, now):
            pub.enqueue(name, publish.build_bench_features(name))

    for name in roster.ROAD_SEGMENTS:
        if sched.due(name, 1.0 / RATE_ROAD, now):
            pub.enqueue(name, publish.build_road_features(sim, eff, name))

    if sched.due(roster.GROUP_DISPATCH, 1.0 / RATE_GROUP, now):
        pub.enqueue(roster.GROUP_DISPATCH, publish.build_group_dispatch_features(sim, eff))
    if sched.due(roster.GROUP_PIT, 1.0 / RATE_GROUP, now):
        pub.enqueue(roster.GROUP_PIT, publish.build_group_pit_features(sim))
    if sched.due(roster.GROUP_PLANT, 1.0 / RATE_GROUP, now):
        pub.enqueue(roster.GROUP_PLANT, publish.build_group_plant_features(sim))
    if sched.due(roster.GROUP_MINE, 1.0 / RATE_GROUP, now):
        pub.enqueue(roster.GROUP_MINE, publish.build_group_mine_features(sim))

    if sched.due(roster.KPI_NAME, 1.0 / RATE_KPI, now):
        pub.enqueue(roster.KPI_NAME, publish.build_kpi_features(sim, sim_base, eff))


if __name__ == "__main__":
    main()
