"""
modules/grade_control.py -- grade control at the crusher: when the run-of-mine ore grade falls
below target, reclaim high-grade stockpile ore into the crusher feed in the proportion that
restores the target. 03_domain.md §3.2 and §11-S1 (Bozshakol blended from high-grade piles
during its Q4 2020 grade dip).
"""
from __future__ import annotations


def high_grade_reclaim_t(rom_t: float, rom_grade_pct: float, hg_grade_pct: float, hg_available_t: float,
                         target_grade_pct: float, max_reclaim_t: float) -> float:
    """Tonnes of high-grade ore to blend with rom_t tonnes of ROM ore this step.

    Solves (rom_t*g_rom + x*g_hg) / (rom_t + x) = target for x, then caps it by the loader's
    capacity this step and by what is left in the high-grade pile. Returns 0 when the ROM ore
    already meets the target or nothing can raise it."""
    if rom_t <= 0.0 or rom_grade_pct >= target_grade_pct or hg_grade_pct <= target_grade_pct:
        return 0.0
    need = rom_t * (target_grade_pct - rom_grade_pct) / (hg_grade_pct - target_grade_pct)
    return max(0.0, min(need, max_reclaim_t, hg_available_t))


if __name__ == "__main__":
    x = high_grade_reclaim_t(1000.0, 0.45, 0.65, 1e6, 0.50, 1e6)
    blended = (1000.0 * 0.45 + x * 0.65) / (1000.0 + x)
    assert abs(blended - 0.50) < 1e-9, blended
    assert high_grade_reclaim_t(1000.0, 0.52, 0.65, 1e6, 0.50, 1e6) == 0.0
    assert high_grade_reclaim_t(1000.0, 0.45, 0.65, 1e6, 0.50, 100.0) == 100.0
    print("modules/grade_control.py self-check OK:", round(x, 1))
