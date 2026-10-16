"""
modules/dispatch.py -- dynamic (match-factor/shortest-queue) dispatch optimizer vs a fixed-route
baseline. 03_domain.md §2.6, §2.8, §11-S11.

The dynamic/fixed difference is NOT a hardcoded multiplier -- it emerges from the assignment rule
itself: "dynamic" always sends a truck to whichever eligible shovel will free up soonest (an
MTCT/shortest-queue heuristic, 03_domain.md §2.8), so queueing self-balances; "fixed" sends every
truck back to its pre-assigned shovel regardless of that shovel's queue, so an imbalance (e.g. a
shovel down, or uneven face productivity) causes real queueing that this module does not correct.
"""
from __future__ import annotations

from typing import Optional

from models.truck import match_factor


def choose_shovel(
    policy: str,
    truck_name: str,
    eligible_shovels: list[str],
    shovel_busy_until_s: dict[str, float],
    shovel_grade_pct: dict[str, float],
    fixed_assignment: dict[str, str],
    now_s: float,
    target_grade_band: Optional[tuple[float, float]] = None,
) -> str:
    """
    Returns the shovel name this truck should head to next.
      policy == "fixed":   always the truck's pre-assigned shovel, even if it is busy/down,
                            unless that shovel is literally not in eligible_shovels (down/failed),
                            in which case fall back to *any* eligible shovel (a real dispatcher
                            would not strand a truck at a dead face) -- the realistic "degraded
                            mode" cost is the queueing this causes elsewhere, not a stranded truck.
      policy == "dynamic":  shortest-queue (MTCT heuristic): the eligible shovel with the earliest
                            busy_until time. If a blend target band is given and more than one
                            shovel ties within 1 minute of the shortest queue, prefer the one
                            whose face grade pulls the blend toward the target band (03_domain.md
                            §2.8 LP blend constraint, simplified to a tie-break rule here).
    """
    if not eligible_shovels:
        return fixed_assignment.get(truck_name, "")

    if policy == "fixed":
        assigned = fixed_assignment.get(truck_name)
        if assigned in eligible_shovels:
            return assigned
        return eligible_shovels[0]

    # dynamic
    ranked = sorted(eligible_shovels, key=lambda s: shovel_busy_until_s.get(s, now_s))
    best_wait = shovel_busy_until_s.get(ranked[0], now_s)
    near_ties = [s for s in ranked if shovel_busy_until_s.get(s, now_s) - best_wait <= 60.0]
    if target_grade_band and len(near_ties) > 1:
        lo, hi = target_grade_band
        mid = (lo + hi) / 2.0
        near_ties.sort(key=lambda s: abs(shovel_grade_pct.get(s, mid) - mid))
        return near_ties[0]
    return ranked[0]


def match_factor_diagnostic(n_trucks: int, t_load_min: float, n_shovels: int, t_cycle_min: float) -> float:
    return match_factor(n_trucks, t_load_min, n_shovels, t_cycle_min)


def fleet_size(base_count: int, truck_count_delta: int, min_fleet: int = 1) -> int:
    """Apply the scenario twin's truck_count_delta (or the fleet_minus_2 preset) to the active
    fleet size. Trucks beyond the active count are parked (not simulated as cycling)."""
    return max(min_fleet, base_count + truck_count_delta)
