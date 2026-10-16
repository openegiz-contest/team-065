"""
Reproduce the validation and module figures quoted in SUBMISSION.md, offline (no MQTT, Ditto or Docker):
  1. 1,000 mine hours (six weeks) of normal running (validation against the reference site);
  2. Shovel S2 failure with the fleet-management system on and off, averaged over 8 seeds;
  3. predictive against reactive maintenance over 200 mine hours, summed over 8 seeds.
Equipment failures are random, so single short runs vary; these longer runs and averages are the figures
SUBMISSION.md quotes.

Usage (from mine/engine):  python tools/validate.py [seed]      (takes several minutes)
"""
from __future__ import annotations

import dataclasses
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scenarios import BASELINE_EFFECTIVE, ScenarioFields, resolve_effective  # noqa: E402
from simulation import Simulation  # noqa: E402

DT_S, PER_H = 12.0, 300
SEEDS = range(1, 9)
HOURS = 1000


def eff(sid: str, **fields):
    return resolve_effective(dataclasses.replace(ScenarioFields(), active_scenario=sid, run_id="validate", **fields))


def long_run(seed: int) -> None:
    sim = Simulation(seed=seed, label="long")
    keys = ["tph", "cu_tph", "haul_cycle_min", "fleet_avail_pct", "ore_mined_tph", "buffer_h"]
    acc = {k: 0.0 for k in keys}
    n = 0
    starved_h = 0.0
    for h in range(HOURS):
        for _ in range(PER_H):
            sim.step(DT_S, BASELINE_EFFECTIVE)
            if sim.stockpile_crushed.mass_t < 1.0:
                starved_h += DT_S / 3600
        if h >= 4:
            for k in keys:
                acc[k] += sim.last_kpi[k]
            n += 1
    avg = {k: v / n for k, v in acc.items()}
    weeks = HOURS / 168
    print(f"## {HOURS} mine hours of normal running (seed {seed})")
    print(f"- mill feed {avg['tph']:,.0f} t/h ({avg['tph'] * 8760 / 1e6:.1f} Mt/a)")
    print(f"- copper recovery {100 * sim.last_cu_recovery:.1f} % (end of run)")
    print(f"- copper in concentrate per tonne milled {1000 * avg['cu_tph'] / avg['tph']:.2f} kg/t")
    print(f"- truck fleet availability {avg['fleet_avail_pct']:.1f} %")
    print(f"- haul cycle {avg['haul_cycle_min']:.1f} min")
    print(f"- ore mined {avg['ore_mined_tph']:,.0f} t/h; crushed-ore buffer {avg['buffer_h']:.1f} h")
    print(f"- unplanned failures {sim.unplanned_failures_total} ({sim.unplanned_failures_total / weeks:.0f} per week); "
          f"strip ratio {sim.waste_total_t / sim.ore_total_t:.2f}; mill starved {starved_h:.1f} h\n")


def fleet_management() -> None:
    print(f"## Shovel S2 failure, 12 mine hours, fleet-management system on and off (mean of seeds {SEEDS.start}-{SEEDS.stop - 1})")
    for policy in ("dynamic", "fixed"):
        ore_d, cu_d = [], []
        for seed in SEEDS:
            real = Simulation(seed=seed, label="real")
            for _ in range(4 * PER_H):
                real.step(DT_S, BASELINE_EFFECTIVE)
            base = real.clone_as_baseline()
            e = eff("shovel_failure", dispatch_policy=policy)
            ore0, base0 = real.ore_total_t, base.ore_total_t
            cu = [0.0, 0.0]
            for h in range(12):
                for _ in range(PER_H):
                    real.step(DT_S, e)
                    base.step(DT_S, BASELINE_EFFECTIVE)
                    if h >= 2:
                        cu[0] += real.last_kpi["cu_tph"]
                        cu[1] += base.last_kpi["cu_tph"]
            ore, ore_b = real.ore_total_t - ore0, base.ore_total_t - base0
            ore_d.append(100 * (ore - ore_b) / ore_b)
            cu_d.append(100 * (cu[0] - cu[1]) / cu[1])
        label = "system on" if policy == "dynamic" else "system offline"
        print(f"- {label}: ore mined {sum(ore_d) / len(ore_d):+.0f} %, copper output (hours 2-12) "
              f"{sum(cu_d) / len(cu_d):+.1f} %")
    print()


def maintenance() -> None:
    print(f"## Predictive against reactive maintenance, 200 mine hours (seeds {SEEDS.start}-{SEEDS.stop - 1})")
    e = eff("predictive_maintenance")
    fails = [0, 0]
    planned = 0
    av = [0.0, 0.0]
    for seed in SEEDS:
        real, base = Simulation(seed=seed, label="real"), Simulation(seed=seed, label="base")
        for _ in range(200):
            for _ in range(PER_H):
                real.step(DT_S, e)
                base.step(DT_S, BASELINE_EFFECTIVE)
            av[0] += real.last_kpi["fleet_avail_pct"]
            av[1] += base.last_kpi["fleet_avail_pct"]
        fails[0] += real.unplanned_failures_total
        fails[1] += base.unplanned_failures_total
        planned += real.planned_repairs_total
    n = 200 * len(SEEDS)
    print(f"- unplanned failures: predictive {fails[0]}, reactive {fails[1]} "
          f"({100 * (fails[0] - fails[1]) / fails[1]:+.0f} %); planned repairs {planned}")
    print(f"- mean fleet availability: predictive {av[0] / n:.2f} %, reactive {av[1] / n:.2f} %\n")


if __name__ == "__main__":
    s = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    long_run(s)
    fleet_management()
    maintenance()
