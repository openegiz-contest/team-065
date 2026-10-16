"""
Flotation recovery models. 03_domain.md §7.4.
Model A (constant-tails) is the primary driver (best fit to KAZ data); Model B's kinetic
adjustments (P80, residence time, ore-type penalty) ride on top of it for the what-if scenarios.
"""
from __future__ import annotations

import math

from . import constants as C


def constant_tails_recovery(head_grade_pct: float, conc_grade_pct: float = C.CU_CONC_GRADE_PCT,
                             tails_grade_pct: float = C.CU_TAILS_GRADE_PCT) -> float:
    """
    Model A: R = (c/f) * (f-t) / (c-t). 03_domain.md §7.4.
    Recovery falls with head grade when t is fixed and c is roughly fixed -- matches the doc's
    "recovery falls with head grade" statement and the Aktogay validation (f=0.361%% c=24.3%% t=0.059%% -> R=83.9%%).
    """
    f, c, t = head_grade_pct, conc_grade_pct, tails_grade_pct
    if f <= t or c <= t:
        return 0.0
    r = (c / f) * (f - t) / (c - t)
    return max(0.0, min(1.0, r))


def residence_time_min(cell_volume_m3: float, voidage: float, slurry_qph_m3: float) -> float:
    """tau = V_cells * eps / Q_slurry. 03_domain.md §7.4 Model B."""
    if slurry_qph_m3 <= 0:
        return 0.0
    return (cell_volume_m3 * voidage) / slurry_qph_m3 * 60.0


def p80_coarse_penalty_pp(p80_um: float) -> float:
    """phi(P80) penalty in recovery percentage points, calibrated to 03_domain.md §7.4 Model B's
    own worked examples (180um: -0.5pp, 240um: -2.1pp) -- see constants.py for the calibration."""
    delta = max(0.0, p80_um - C.FLOT_P80_REF_UM)
    return C.FLOT_P80_PENALTY_COEF * (delta ** C.FLOT_P80_PENALTY_EXP)


def throughput_residence_penalty_pp(tph_now: float, tph_ref: float, sensitivity_pp_per_x: float = 1.5) -> float:
    """
    Higher throughput -> shorter tau -> lower recovery (03_domain.md §7.4 Model B: 'throughput up => tau
    down => R down'; and §11-S3/§11-S5 give -0.3pp at +8%% TPH, +0.5pp at -25%% TPH). We linearise:
    delta_R_pp = -sensitivity * (tph_now/tph_ref - 1).
    """
    if tph_ref <= 0:
        return 0.0
    return -sensitivity_pp_per_x * (tph_now / tph_ref - 1.0)


def ore_type_penalty_pp(clay_fraction: float) -> tuple[float, float]:
    """
    ore-type penalty for clay/oxidised/high-S feed, 03_domain.md §7.4:
    -2 to -5 pp Cu, -4 to -8 pp Au, scaled by the fraction of clay/high-S feed in the blend.
    Returns (cu_penalty_pp, au_penalty_pp).
    """
    return clay_fraction * C.FLOT_CLAY_PENALTY_CU_PP, clay_fraction * C.FLOT_CLAY_PENALTY_AU_PP


def cu_recovery(head_grade_pct: float, p80_um: float = C.BOND_P80_UM_BASE, tph_now: float = 3600.0,
                 tph_ref: float = 3600.0, clay_fraction: float = 0.0,
                 conc_grade_pct: float = C.CU_CONC_GRADE_PCT) -> float:
    """Full Cu recovery: constant-tails base, minus coarse-grind penalty, residence-time effect and
    ore-type penalty. Returns a fraction 0-1."""
    r_base_pct = constant_tails_recovery(head_grade_pct, conc_grade_pct) * 100.0
    r_pct = (r_base_pct - p80_coarse_penalty_pp(p80_um)
             + throughput_residence_penalty_pp(tph_now, tph_ref)
             - ore_type_penalty_pp(clay_fraction)[0])
    return max(0.0, min(1.0, r_pct / 100.0))


def au_recovery(clay_fraction: float = 0.0, base: float = C.AU_RECOVERY_BASE) -> float:
    """R_Au ~ 0.60 +- 0.03, minus the ore-type (clay/high-S) penalty. 03_domain.md §7.4."""
    r = base - ore_type_penalty_pp(clay_fraction)[1] / 100.0
    return max(0.0, min(1.0, r))


def mass_pull_to_conc_pct(head_grade_pct: float, recovery_frac: float,
                           conc_grade_pct: float = C.CU_CONC_GRADE_PCT) -> float:
    """mass pull = f*R/c. 03_domain.md §7.5."""
    if conc_grade_pct <= 0:
        return 0.0
    return head_grade_pct * recovery_frac / conc_grade_pct


if __name__ == "__main__":
    r_akt = constant_tails_recovery(0.361, 24.3, 0.059)
    assert abs(r_akt - 0.839) < 0.01, r_akt  # 03_domain.md §7.4 Aktogay check: 83.9%
    r_boz_045 = constant_tails_recovery(0.45, 22.0, C.CU_TAILS_GRADE_PCT)
    r_boz_055 = constant_tails_recovery(0.55, 22.0, C.CU_TAILS_GRADE_PCT)
    assert r_boz_045 < r_boz_055, (r_boz_045, r_boz_055)  # recovery falls with lower head grade
    print("models/flotation.py self-check OK:", r_akt, r_boz_045, r_boz_055)
