"""
Measure every what-if scenario against the shadow baseline, the way the running engine compares
them: warm the mine up for a few mine hours, copy it as the baseline, apply the scenario to the
live copy only, and average the KPI differences over two windows.

Usage (from mine/engine):  python tools/measure_scenarios.py [seed]
Prints a Markdown table. Runs offline: no MQTT, Ditto or Docker needed.
"""
from __future__ import annotations

import dataclasses
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scenarios import BASELINE_EFFECTIVE, VALID_SCENARIOS, ScenarioFields, resolve_effective  # noqa: E402
from simulation import Simulation  # noqa: E402

DT_S = 12.0          # one engine tick at 60x: 12 s of mine time
TICKS_PER_H = 300
WARM_H = 4
WINDOWS = [("first 2 h", 0.0, 2.0), ("hours 2-10", 2.0, 10.0)]
KEYS = [("ore_mined_tph", "ore mined"), ("mined_grade_pct", "ore grade"), ("haul_cycle_min", "haul cycle"),
        ("buffer_h", "crushed-ore buffer"), ("tph", "mill feed"), ("cu_tph", "Cu output"),
        ("nsr_usd_h", "revenue"), ("fuel_l_h", "diesel"), ("energy_kwh_h", "grid energy"), ("co2_t_h", "CO2")]


def measure(sid: str, seed: int) -> dict[str, dict[str, float]]:
    real = Simulation(seed=seed, label="real")
    for _ in range(WARM_H * TICKS_PER_H):
        real.step(DT_S, BASELINE_EFFECTIVE)
    base = real.clone_as_baseline()
    eff = resolve_effective(dataclasses.replace(ScenarioFields(), active_scenario=sid, run_id="measure"))
    out: dict[str, dict[str, float]] = {}
    tick = 0
    for label, h0, h1 in WINDOWS:
        sums = {k: [0.0, 0.0] for k, _ in KEYS}
        while tick < h1 * TICKS_PER_H:
            real.step(DT_S, eff)
            base.step(DT_S, BASELINE_EFFECTIVE)
            if tick >= h0 * TICKS_PER_H:
                for k, _ in KEYS:
                    sums[k][0] += real.last_kpi.get(k, 0.0)
                    sums[k][1] += base.last_kpi.get(k, 0.0)
            tick += 1
        out[label] = {k: (100.0 * (c - b) / b if b else 0.0) for k, (c, b) in sums.items()}
    return out


def main() -> None:
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"Average change against the shadow baseline (seed {seed}); only changes of 1 % or more are listed.\n")
    print("| Scenario | First 2 mine hours | Mine hours 2-10 |")
    print("|---|---|---|")
    for sid in VALID_SCENARIOS:
        if sid == "none":
            continue
        res = measure(sid, seed)
        cells = []
        for label, _, _ in WINDOWS:
            parts = [f"{name} {v:+.0f} %" for k, name in KEYS if abs(v := res[label][k]) >= 1.0]
            cells.append(", ".join(parts) or "no change of 1 % or more")
        print(f"| {sid} | {cells[0]} | {cells[1]} |", flush=True)


if __name__ == "__main__":
    main()
