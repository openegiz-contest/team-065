"""
Weather state and cold-weather equipment effects. 03_domain.md §5.4.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import constants as C


@dataclass
class WeatherState:
    temp_c: float = C.TEMP_BASELINE_C
    wind_ms: float = C.WIND_BASELINE_MS
    condition: str = "clear"   # clear | fog | blizzard
    visibility_m: float = 2000.0

    @property
    def is_extreme_cold(self) -> bool:
        return self.temp_c <= C.COLD_THRESHOLD_C

    def road_speed_cap_kmh(self, ramp: bool) -> float | None:
        if self.is_extreme_cold:
            return C.COLD_SPEED_CAP_RAMP_KMH if ramp else C.COLD_SPEED_CAP_FLAT_KMH
        return None

    def visibility_speed_cap_kmh(self) -> float | None:
        """03_domain.md §5.5: fog/blizzard <100m -> cap 20 km/h, <50m -> stop."""
        if self.visibility_m < 50.0:
            return 0.0
        if self.visibility_m < 100.0:
            return C.SPEED_CAP_FOG_100M
        return None

    def hydraulic_penalty(self) -> float:
        return C.COLD_HYDRAULIC_PENALTY if self.is_extreme_cold else 0.0

    def warmup_penalty_min_per_shift(self) -> float:
        return C.COLD_WARMUP_MIN if self.is_extreme_cold else 0.0

    def idle_fuel_multiplier(self) -> float:
        return C.WINTER_IDLE_FUEL_MULT if self.is_extreme_cold else 1.0

    def tyre_strut_hazard_multiplier(self) -> float:
        return C.COLD_TYRE_DAMAGE_MULT if self.is_extreme_cold else 1.0

    def watering_possible(self) -> bool:
        return self.temp_c >= 0.0

    def stability_class_f(self) -> bool:
        """Winter inversion: calm wind + cold -> stable atmosphere, poor gas dispersion. §5.2."""
        return self.temp_c < -10.0 and self.wind_ms < 2.0


if __name__ == "__main__":
    w = WeatherState(temp_c=-38.0, wind_ms=12.0)
    assert w.is_extreme_cold
    assert w.road_speed_cap_kmh(ramp=True) == C.COLD_SPEED_CAP_RAMP_KMH
    assert not w.watering_possible()
    print("models/weather.py self-check OK:", w)
