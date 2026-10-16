"""
Stockpile mass/grade balance (well-mixed tank) and buffer dynamics. 03_domain.md §3.2.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Stockpile:
    name: str
    mass_t: float
    grade_pct: float            # Cu grade, weighted average of what's in the pile
    capacity_t: float

    def add(self, mass_t: float, grade_pct: float) -> None:
        """dG/dt = Q_in*(g_in - G)/M, implemented as an exact mixing update per tick.
        03_domain.md §3.2 well-mixed tank model."""
        if mass_t <= 0:
            return
        new_mass = self.mass_t + mass_t
        if new_mass <= 0:
            self.grade_pct = grade_pct
            self.mass_t = 0.0
            return
        self.grade_pct = (self.mass_t * self.grade_pct + mass_t * grade_pct) / new_mass
        # Mass is conserved: callers check headroom() before adding, so nothing is lost here.
        self.mass_t = new_mass

    def headroom(self) -> float:
        return max(0.0, self.capacity_t - self.mass_t)

    def draw(self, mass_t: float) -> tuple[float, float]:
        """Remove up to mass_t tonnes; grade is unchanged by drawing (well-mixed assumption).
        Returns (actual_mass_drawn_t, grade_pct)."""
        actual = min(mass_t, self.mass_t)
        self.mass_t -= actual
        return actual, self.grade_pct

    @property
    def fill_fraction(self) -> float:
        if self.capacity_t <= 0:
            return 0.0
        return self.mass_t / self.capacity_t

    def hours_of_buffer(self, draw_rate_tph: float) -> float:
        if draw_rate_tph <= 0:
            return float("inf")
        return self.mass_t / draw_rate_tph


def blend_grade(components: list[tuple[float, float]]) -> float:
    """Weighted blend grade from a list of (mass_or_flow, grade_pct) tuples. 03_domain.md §3.2/§2.8 LP blend."""
    total = sum(m for m, _ in components)
    if total <= 0:
        return 0.0
    return sum(m * g for m, g in components) / total


if __name__ == "__main__":
    sp = Stockpile("crushed-ore", mass_t=40000.0, grade_pct=0.50, capacity_t=40000.0)
    sp.draw(3600.0)
    assert abs(sp.mass_t - 36400.0) < 1e-6
    sp.add(1800.0, 0.60)
    assert sp.grade_pct > 0.50
    bg = blend_grade([(100.0, 0.5), (50.0, 0.3)])
    assert abs(bg - ((100 * 0.5 + 50 * 0.3) / 150)) < 1e-9
    print("models/stockpile.py self-check OK:", sp.mass_t, sp.grade_pct, bg)
