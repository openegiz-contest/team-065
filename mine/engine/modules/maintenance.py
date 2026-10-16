"""
modules/maintenance.py -- Weibull-based failure injection + condition signals -> predictive work
orders, vs reactive (run-to-failure) baseline. 03_domain.md §8.

Wraps models.reliability.AssetReliability for every truck/shovel/drill/crusher/mill in the
roster, exposing a single step() that returns the per-asset feature dict to publish (health,
next_pm_due, state hints) plus any human-readable events for the engine's event log.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from models.reliability import AssetReliability
from models import constants as C


@dataclass
class MaintenanceManager:
    rng: random.Random
    assets: dict[str, AssetReliability] = field(default_factory=dict)
    seed: int = 0

    def register(self, name: str, asset_class: str) -> None:
        # One random stream per asset (common random numbers): the scenario run and the shadow
        # baseline draw identical failure times for the same machine.
        self.assets[name] = AssetReliability(asset_class=asset_class,
                                             rng=random.Random(f"{self.seed}:{name}"))

    def step(self, name: str, dt_h: float, predictive: bool, at_shift_boundary: bool,
              forced_down_h: float = 0.0) -> dict:
        asset = self.assets[name]
        prev_event = asset.last_event
        asset.step(dt_h=dt_h, predictive=predictive, at_shift_boundary=at_shift_boundary,
                   forced_down_h=forced_down_h)
        event = asset.last_event if asset.last_event != prev_event else ""
        return {
            "down": asset.down,
            "health_pct": round(asset.estimated_health_pct, 1),
            "next_pm_due_h": round(asset.next_pm_due_h, 1),
            "coolant_temp_c": round(asset.coolant_temp_c, 1),
            "oil_fe_ppm": round(asset.oil_fe_ppm, 1),
            "event": event,
        }

    def is_down(self, name: str) -> bool:
        return self.assets[name].down

    def fleet_availability(self, names: list[str]) -> float:
        if not names:
            return 1.0
        up = sum(0 if self.assets[n].down else 1 for n in names)
        return up / len(names)

    def pending_pa_gain(self, predictive: bool) -> float:
        """03_domain.md §11-S9: predictive maintenance applied fleet-wide gives +2 to +3 pp truck
        physical availability. Used as a reporting figure on the kpi twin, not to double-count
        with the per-asset Weibull outcomes already captured in fleet_availability()."""
        return C.PA_GAIN_PREDICTIVE_PP if predictive else 0.0
