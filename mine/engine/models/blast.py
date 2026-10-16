"""
Drilling & blasting / Kuz-Ram fragmentation model. 03_domain.md §4.1-§4.3.
"""
from __future__ import annotations

import math

from . import constants as C


def charge_mass_kg(hole_diameter_mm: float = C.HOLE_DIAMETER_MM, bench_height_m: float = C.BENCH_HEIGHT_M,
                    subdrill_m: float = C.SUBDRILL_M, stemming_m: float = C.STEMMING_M,
                    explosive_density_kg_m3: float = C.EXPLOSIVE_DENSITY_KG_M3) -> float:
    """Q (kg) = charge column length * linear charge density. 03_domain.md §4.2 worked example."""
    charge_length_m = bench_height_m + subdrill_m - stemming_m
    charge_length_m = max(charge_length_m, 0.5)
    hole_area_m2 = math.pi * (hole_diameter_mm / 1000.0 / 2.0) ** 2
    linear_density_kg_m = hole_area_m2 * explosive_density_kg_m3
    return charge_length_m * linear_density_kg_m


def x50_cm(powder_factor_kg_t: float, charge_kg: float, rock_factor_a: float = C.ROCK_FACTOR_A,
           rws: float = C.RWS_ANFO) -> float:
    """
    Kuznetsov-Cunningham: X50(cm) = A * K^-0.8 * Q^(1/6) * (115/RWS)^(19/20). 03_domain.md §4.2.
    K is the powder factor expressed in kg/m^3 (we use kg/t as a close proxy scaled by in-situ
    density, consistent with the twin's worked example which quotes PF directly in the K slot).
    """
    k = powder_factor_kg_t * C.RHO_INSITU_T_M3  # kg/t -> kg/m3 approx, [D]
    return rock_factor_a * (k ** -0.8) * (charge_kg ** (1.0 / 6.0)) * ((115.0 / rws) ** (19.0 / 20.0))


def uniformity_n(burden_m: float, spacing_m: float, hole_diameter_mm: float, bcl_m: float, ccl_m: float,
                  total_length_m: float, bench_height_m: float = C.BENCH_HEIGHT_M) -> float:
    """
    Cunningham (1987) uniformity index, 03_domain.md §4.2:
        n = (2.2 - 14*B/d) * sqrt((1+S/B)/2) * (1-W/B) * (|BCL-CCL|/L + 0.1)^0.1 * (L/H)
    B, S, L, H in metres; d (hole diameter) in millimetres, as in the standard Cunningham form.
    The twin has no deck charges, so W/B (deck-charge burden offset) = 0.
    """
    t1 = 2.2 - 14.0 * (burden_m * 1000.0 / hole_diameter_mm) * 1e-3
    t2 = math.sqrt((1.0 + spacing_m / burden_m) / 2.0)
    t3 = 1.0 - 0.0  # no deck charges in the twin model
    t4 = (abs(bcl_m - ccl_m) / max(total_length_m, 0.1) + 0.1) ** 0.1
    t5 = total_length_m / bench_height_m
    return max(0.6, t1 * t2 * t3 * t4 * t5)


def x80_from_x50(x50: float, n: float) -> float:
    """X80 = X50 * (ln5/ln2)^(1/n) = X50 * 2.322^(1/n). 03_domain.md §4.2."""
    return x50 * (math.log(5) / math.log(2)) ** (1.0 / n)


def passing_fraction(x_mm: float, x50_mm: float, n: float) -> float:
    """Rosin-Rammler P(x) = 1 - exp(-0.693*(x/X50)^n). 03_domain.md §4.2."""
    if x50_mm <= 0:
        return 0.0
    return 1.0 - math.exp(-0.693 * (x_mm / x50_mm) ** n)


def fragmentation_for_powder_factor(powder_factor_kg_t: float) -> dict:
    """
    Convenience wrapper used by engine.py / modules.dispatch to go from a powder-factor setting
    (controlled by the scenario twin's blast_powder_factor multiplier) straight to X50/X80.
    Calibrated against 03_domain.md §4.2's worked table (PF 0.30 -> X50 272mm/X80 520mm;
    PF 0.40 -> X50 216mm/X80 413mm).
    """
    q = charge_mass_kg()
    x50mm = x50_cm(powder_factor_kg_t, q) * 10.0  # cm -> mm
    n = C.BLAST_UNIFORMITY_N_BASE
    x80mm = x80_from_x50(x50mm, n)
    fines_25mm_frac = passing_fraction(25.0, x50mm, n)
    return {"x50_mm": x50mm, "x80_mm": x80mm, "n": n, "fines_25mm_frac": fines_25mm_frac}


if __name__ == "__main__":
    base = fragmentation_for_powder_factor(C.POWDER_FACTOR_BASE)
    intensified = fragmentation_for_powder_factor(C.POWDER_FACTOR_INTENSIFIED)
    # 03_domain.md §4.2 table: base X50~272mm/X80~520mm; intensified X50~216mm(-21%)/X80~413mm.
    assert 200 < base["x50_mm"] < 340, base
    assert intensified["x50_mm"] < base["x50_mm"], (intensified, base)
    reduction_pct = 100.0 * (1.0 - intensified["x50_mm"] / base["x50_mm"])
    assert 10.0 < reduction_pct < 35.0, reduction_pct
    print("models/blast.py self-check OK:", base, intensified, f"X50 reduction {reduction_pct:.1f}%")
