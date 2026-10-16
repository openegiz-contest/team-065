"""
Weibull reliability model: MTBF/MTTR, hazard rate, and synthetic condition-monitoring signals.
03_domain.md §8.1, §8.2.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from . import constants as C


def weibull_sample(beta: float, eta_h: float, rng: random.Random) -> float:
    """Sample a time-to-failure (hours) from Weibull(beta, eta). Inverse-CDF method."""
    u = rng.random()
    # avoid log(0)
    u = min(max(u, 1e-9), 1.0 - 1e-9)
    return eta_h * (-math.log(1.0 - u)) ** (1.0 / beta)


def reliability_r(t_h: float, beta: float, eta_h: float) -> float:
    """R(t) = exp(-(t/eta)^beta). 03_domain.md §8.1."""
    if eta_h <= 0:
        return 0.0
    return math.exp(-((t_h / eta_h) ** beta))


def hazard_h(t_h: float, beta: float, eta_h: float) -> float:
    """h(t) = (beta/eta)*(t/eta)^(beta-1). 03_domain.md §8.1."""
    if eta_h <= 0 or t_h <= 0:
        return 0.0
    return (beta / eta_h) * (t_h / eta_h) ** (beta - 1.0)


def inherent_availability(mtbf_h: float, mttr_h: float) -> float:
    """A = MTBF/(MTBF+MTTR). 03_domain.md §8.1."""
    if mtbf_h + mttr_h <= 0:
        return 0.0
    return mtbf_h / (mtbf_h + mttr_h)


@dataclass
class AssetReliability:
    """
    Per-asset reliability state machine. Supports two maintenance strategies
    (03_domain.md §8.1/§8.2/§11-S9):
      - "reactive": run-to-failure. The asset fails exactly when operating_hours_since_repair
        reaches the Weibull-sampled time_to_failure; MTTR is the full unplanned repair (+tow).
      - "predictive": a synthetic condition signal (coolant temp proxy) rises as the asset
        approaches its sampled failure time. Once the signal crosses the "watch" threshold, a
        work order is raised and the asset is pulled at the NEXT shift boundary for a shorter
        planned repair, avoiding the unplanned failure and its longer MTTR -- the causal chain
        behind the +2 to +3 pp fleet availability gain in §11-S9.
    """
    asset_class: str
    rng: random.Random
    operating_hours_since_repair: float = 0.0
    time_to_failure_h: float = field(default=0.0)
    down: bool = False
    down_remaining_h: float = 0.0
    health_pct: float = 100.0
    coolant_temp_c: float = 88.0
    oil_fe_ppm: float = 15.0
    work_order_open: bool = False
    pending_planned_repair: bool = False
    last_event: str = ""
    down_mode: str = ""  # "wear" | "other" | "planned" | "forced"
    other_ttf_h: float = 0.0  # operating hours until the next non-wear (random) failure
    hours_since_other: float = 0.0

    def __post_init__(self) -> None:
        params = C.WEIBULL_PARAMS[self.asset_class]
        self.time_to_failure_h = weibull_sample(params["beta"], params["eta_h"], self.rng)
        # [A] An operating fleet is at mixed points in its maintenance cycle, not all fresh
        # from overhaul: start each asset at a uniform random fraction of its sampled life.
        # The fixed plant (crusher, mills) starts just after a scheduled shutdown and reline
        # (mills are relined ~3 times a year, 03_domain.md §8.1), so early in its life.
        span = 0.3 if self.asset_class in ("crusher", "mill") else 0.97
        self.operating_hours_since_repair = self.rng.uniform(0.0, span) * self.time_to_failure_h
        self._sample_other()

    def _sample_other(self) -> None:
        other = C.OTHER_FAILURES.get(self.asset_class)
        self.hours_since_other = 0.0
        self.other_ttf_h = self.rng.expovariate(1.0 / other["mtbf_h"]) if other else float("inf")

    def _resample(self) -> None:
        params = C.WEIBULL_PARAMS[self.asset_class]
        self.operating_hours_since_repair = 0.0
        self.time_to_failure_h = weibull_sample(params["beta"], params["eta_h"], self.rng)
        self.work_order_open = False
        self.pending_planned_repair = False
        self.health_pct = 100.0
        self.coolant_temp_c = 88.0
        self.oil_fe_ppm = 15.0

    def step(self, dt_h: float, predictive: bool, at_shift_boundary: bool, forced_down_h: float = 0.0) -> None:
        """Advance this asset by dt_h operating hours. forced_down_h lets a scenario
        (e.g. shovel_failure) impose a deterministic outage on top of the Weibull model."""
        if forced_down_h > 0.0 and not self.down:
            self.down = True
            self.down_mode = "forced"
            self.down_remaining_h = forced_down_h
            self.last_event = f"forced down by scenario ({forced_down_h:.1f} h)"

        if self.down:
            self.down_remaining_h -= dt_h
            if self.down_remaining_h <= 0.0:
                self.down = False
                if self.down_mode == "other":
                    self._sample_other()  # repaired a random fault; wear-out age carries on
                else:
                    self._resample()
                    self._sample_other()
                self.down_mode = ""
                self.last_event = "returned to service"
            return

        self.operating_hours_since_repair += dt_h
        frac = min(1.0, self.operating_hours_since_repair / max(self.time_to_failure_h, 1e-6))
        self.health_pct = max(0.0, 100.0 * (1.0 - frac))
        # synthetic condition signal rising non-linearly as failure approaches (§8.2)
        self.coolant_temp_c = 88.0 + 20.0 * (frac ** 2) + self.rng.uniform(-0.5, 0.5)
        self.oil_fe_ppm = 15.0 + 60.0 * (frac ** 2)

        watch = self.coolant_temp_c >= C.COOLANT_TEMP_WARN_C - 2.0 or self.oil_fe_ppm >= C.OIL_FE_ALARM_PPM
        if predictive and watch and not self.work_order_open:
            self.work_order_open = True
            self.pending_planned_repair = True
            self.last_event = f"predictive work order raised (coolant {self.coolant_temp_c:.0f}C)"

        if predictive and self.pending_planned_repair and at_shift_boundary:
            lo, hi = C.PREDICTIVE_MTTR_H
            self.down = True
            self.down_mode = "planned"
            self.down_remaining_h = self.rng.uniform(lo, hi)
            self.pending_planned_repair = False
            self.last_event = f"planned repair at shift change ({self.down_remaining_h:.1f} h)"
            return

        if frac >= 1.0:
            params = C.WEIBULL_PARAMS[self.asset_class]
            lo, hi = params["mttr_h"]
            tow_lo, tow_hi = params["tow_h"]
            self.down = True
            self.down_mode = "wear"
            self.down_remaining_h = self.rng.uniform(lo, hi) + self.rng.uniform(tow_lo, tow_hi)
            self.last_event = f"unplanned failure (wear-out, missed by inspection), MTTR {self.down_remaining_h:.1f} h"
            return

        self.hours_since_other += dt_h
        if self.hours_since_other >= self.other_ttf_h:
            other = C.OTHER_FAILURES[self.asset_class]
            lo, hi = other["mttr_h"]
            tow_lo, tow_hi = other["tow_h"]
            self.down = True
            self.down_mode = "other"
            self.down_remaining_h = self.rng.uniform(lo, hi) + self.rng.uniform(tow_lo, tow_hi)
            self.last_event = f"unplanned failure (random fault), MTTR {self.down_remaining_h:.1f} h"

    def degradation_estimate(self) -> float:
        """Wear fraction (0..1) read back from the condition signal, as a monitoring system would
        infer it -- not the asset's hidden sampled failure time."""
        return min(1.0, math.sqrt(max(0.0, self.coolant_temp_c - 88.0) / 20.0))

    @property
    def estimated_health_pct(self) -> float:
        return 100.0 * (1.0 - self.degradation_estimate())

    @property
    def next_pm_due_h(self) -> float:
        """Estimated hours to wear-out: the class's Weibull mean life scaled by the wear left
        according to the condition signal. Individual assets fail earlier or later than this."""
        params = C.WEIBULL_PARAMS[self.asset_class]
        mean_life = params["eta_h"] * math.gamma(1.0 + 1.0 / params["beta"])
        return max(0.0, mean_life * (1.0 - self.degradation_estimate()))


if __name__ == "__main__":
    rng = random.Random(42)
    r = reliability_r(700.0, 1.5, 700.0)
    assert abs(r - math.exp(-1.0)) < 1e-9
    a = inherent_availability(80.0, 6.0)
    assert abs(a - 80.0 / 86.0) < 1e-9
    asset = AssetReliability("truck", rng)
    for _ in range(2000):
        asset.step(dt_h=1.0, predictive=False, at_shift_boundary=False)
    print("models/reliability.py self-check OK:", r, a, asset.health_pct, asset.last_event)
