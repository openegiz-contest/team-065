"""
Sourced constants for the Kyzyl-Tas digital-mine simulation.

Every constant below carries an evidence tag matching mine/docs/03_domain.md section 0:
  [R] operator-reported, [V] vendor/OEM spec, [L] literature/standard, [D] derived (shown), [A] assumption.
Each constant's comment names the 03_domain.md section it came from so SUBMISSION.md can cite it
directly. Do not add a numeric constant anywhere in engine/ without a matching tag + section ref here.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. Truck fleet (03_domain.md §2.2, §2.7, §2.10)
# ---------------------------------------------------------------------------
TRUCK_SPECS = {
    "CAT785C": {
        # [V] S11; [R] S3 -- Cat 785C, 03_domain.md §2.2
        "payload_t": 136.0,
        "gvw_t": 249.0,
        "net_power_kw": 1005.0,
        "gross_power_kw": 1082.0,
        "max_speed_loaded_kmh": 55.0,
        "drive": "mechanical",
        "fuel_tank_l": 3800.0,          # [A] OEM brochure, §2.7
        "tyre_tkph_rating": 5200.0,     # [A] typical 40.00R57 rating, §2.10
    },
    "KOM830E": {
        # [V] S12, 03_domain.md §2.2 -- Komatsu 830E-5, AC electric drive, trolley-ready
        "payload_t": 227.0,
        "gvw_t": 410.0,
        "net_power_kw": 1865.0,
        "gross_power_kw": 1940.0,       # [A] gross ~4 % above net, as for the Cat units
        "max_speed_loaded_kmh": 64.0,
        "drive": "electric",
        "fuel_tank_l": 4542.0,          # [A] OEM brochure class
        "tyre_tkph_rating": 8500.0,     # [A], §2.10
    },
    "CAT793F": {
        # [V] S10, 03_domain.md §2.2
        "payload_t": 226.8,
        "gvw_t": 386.0,
        "net_power_kw": 1848.0,
        "gross_power_kw": 1976.0,
        "max_speed_loaded_kmh": 60.0,
        "drive": "mechanical",
        "fuel_tank_l": 4354.0,          # [A] OEM brochure, §2.7
        "tyre_tkph_rating": 8500.0,     # [A], §2.10
    },
}

ETA_D_MECHANICAL = 0.80   # [A][T9] drivetrain efficiency, mechanical drive, §2.3
ETA_D_ELECTRIC = 0.85     # [A][T9] drivetrain efficiency, AC-electric drive, §2.3

# Rolling resistance, Cat rule of thumb (§2.3): RR = 2% + 0.6%*(tyre penetration cm)
RR_WELL_MAINTAINED = 2.0   # [S14][T9]
RR_TYPICAL = 3.0           # [S14][T9]
RR_WET_THAW = 4.5          # [S14][T9]  (4-5%)
RR_SOFT = 9.0              # [S14][T9]  (8-10%)

# §2.3 segment speed caps (km/h), used as hard ceilings on top of the rimpull/power model
SPEED_CAP_RAMP_LOADED = 14.0      # [D] upper end of 10-14 km/h loaded ramp band
SPEED_CAP_RAMP_EMPTY = 28.0       # [D] 22-28 km/h band, empty uphill ~2x loaded
SPEED_CAP_FLAT_LOADED = 45.0      # [D]/[A] site cap 50, typical 35-45
SPEED_CAP_FLAT_EMPTY = 50.0       # [D]/[A]
SPEED_CAP_DOWNRAMP_LOADED = 25.0  # [A] retarder-limited, 15-25 km/h band
SPEED_CAP_DOWNRAMP_EMPTY = 40.0   # [A] 30-40 km/h band
SPEED_CAP_LOAD_DUMP_ZONE = 18.0   # [A] <=15-20 km/h site rule

# §5.5 weather/visibility speed caps
SPEED_CAP_FOG_100M = 20.0   # [A]
SPEED_CAP_FOG_50M = 0.0     # [A] stop

# §2.4 cycle-time distributions (minutes), Triangular(low, mode, high)
SPOT_AT_SHOVEL_TRI = (0.3, 0.5, 1.0)     # [A][T9]
SPOT_DUMP_TRI = (0.7, 1.0, 1.5)          # [A][T9]
LOAD_SWING_MEAN_MIN = 0.55                # [A][T9][S13] t_swing ~ N(0.55, 0.08)
LOAD_SWING_SD_MIN = 0.08

# §2.4 bucket/pass parameters
RHO_INSITU_T_M3 = 2.70     # [A][T12]
SWELL_FACTOR = 1.45        # [A][T9] (1.4-1.5)
RHO_LOOSE_T_M3 = RHO_INSITU_T_M3 / SWELL_FACTOR  # [D] ~1.86 t/m3
FILL_FACTOR = 0.90         # [A][T9] (0.85-0.95)
SHOVEL_BUCKET_M3 = {
    "ore": 22.0,     # [A] Hitachi EX3600-class, §2.1/§2.4 (21-24 m3 class)
    "waste": 22.0,
}

# §2.6 productivity / job efficiency
JOB_EFFICIENCY_E = 50.0 / 60.0   # [T9] "E" factor

# §2.7 fuel burn: FC(L/h) = P_rated(kW)*LF*BSFC/rho_diesel
BSFC_KG_PER_KWH = 0.215           # [A][T9] 0.21-0.22
RHO_DIESEL_KG_L = 0.835           # [A][T9]
LOAD_FACTOR_HAUL_LOADED = 0.55    # [A][S14] high band 0.50-0.65
LOAD_FACTOR_HAUL_EMPTY = 0.35     # [A] medium band
LOAD_FACTOR_SPOT_DUMP = 0.30      # [A] low band
IDLE_FUEL_LH_785C = 20.0          # [A] 15-25 L/h, §2.7
IDLE_FUEL_LH_793F = 30.0          # [A] 25-35 L/h, §2.7
WINTER_IDLE_FUEL_MULT = 1.15      # [A] §5.4/§11-S2, +15% idle fuel in extreme cold

# §2.10 tyre wear multiplier: k = 1 + 0.03*(RR%-2) + 0.5*I(overload>10%) + 0.2*I(T<-25C)
TYRE_WEAR_BASE_LIFE_H = 6000.0    # [A] midpoint of 4000-8000 h, §2.10

# ---------------------------------------------------------------------------
# 2. Shovels & dispatch (03_domain.md §2.6, §2.8)
# ---------------------------------------------------------------------------
MATCH_FACTOR_TARGET = (0.9, 1.1)   # [T5] Douglas 1964, target band
DISPATCH_DYNAMIC_GAIN = 0.08       # [D]/[T6] +5-15% material moved, S11 midpoint used as tuning gain
DISPATCH_GRADE_BAND_HALFWIDTH = 0.02  # [D] S11: LP holds crusher feed grade within +-0.02% vs +-0.06% fixed

# ---------------------------------------------------------------------------
# 3. Drilling & blasting / Kuz-Ram (03_domain.md §4.1, §4.2)
# ---------------------------------------------------------------------------
HOLE_DIAMETER_MM = 251.0          # [A] within D55SP/PV-231 range, §4.1
BENCH_HEIGHT_M = 15.0             # [A][T9], §1.2/§4.1
SUBDRILL_M = 1.5                  # [A]
STEMMING_M = 5.5                  # [A]
BURDEN_ORE_M = 6.0                # [A] §4.1
SPACING_ORE_M = 7.0               # [A] §4.1
BURDEN_WASTE_M = 7.0              # [A]
SPACING_WASTE_M = 8.5             # [A]
EXPLOSIVE_DENSITY_KG_M3 = 1200.0  # [A] emulsion blend, §4.1 (1.15-1.25 g/cm3 wet)
RWS_ANFO = 100.0                  # [T2] reference weight strength
ROCK_FACTOR_A = 8.0               # [A] porphyry 7-10, §4.2
POWDER_FACTOR_BASE = 0.30         # [A] kg/t ore, §4.1 base case
POWDER_FACTOR_INTENSIFIED = 0.40  # [A] §4.1/§11-S3 intensified case
BLAST_UNIFORMITY_N_BASE = 1.3     # [D] worked example, §4.2

# §4.3 mine-to-mill coupling surrogate exponents
SAG_TPH_AXB_EXP = 0.8    # [A] 03_domain.md §4.3 surrogate
SAG_TPH_F80_EXP = 0.25   # [A]
SAG_TPH_FINES_EXP = 0.15 # [A]
SHOVEL_DIGRATE_X80_EXP = 0.4  # [A] midpoint of 0.3-0.5, §4.3 "dig time ~ X80^0.3-0.5"

# §4.4 blast exclusion & re-entry
BLAST_EXCLUSION_PERSONNEL_M = 500.0   # [A]
BLAST_EXCLUSION_EQUIPMENT_M = 300.0   # [A]
BLAST_REENTRY_MIN_MIN = 30.0          # [L] S30
BLAST_REENTRY_INVERSION_MIN = 150.0   # [D] §11-S8, 30 -> 150 min under winter inversion

# ---------------------------------------------------------------------------
# 4. Geology / grade control (03_domain.md §3)
# ---------------------------------------------------------------------------
HEAD_GRADE_MEAN_CU_PCT = 0.51      # [R] S1 Bozshakol 2020
LOM_GRADE_CU_PCT = 0.36            # [R] S1 LOM grade
AU_TO_CU_GRADE_RATIO = 0.26 / 0.51 # [D] from §1.1 (0.26 g/t Au per 0.51% Cu)
BWI_BASE_KWHT = 14.0               # [A] twin base, §7.3 (porphyry range 5.7-20.2)
BWI_SIGMA = 1.5                    # [A] §7.3
AXB_BASE = 45.0                    # [A] consistent with §11-S4 "Axb 45 -> 32"
GRADE_BAND_HALFWIDTH_PCT = 0.06    # [D] fixed-dispatch grade variance, §11-S11

# Cut-off grade, Lane mill-constrained (§3.4)
CUTOFF_GRADE_BASE_PCT = 0.20       # [A] matches KAZ 0.2% reporting cut-off
CUTOFF_GRADE_STRESSED_PCT = 0.23   # [A] §11-S10, under -25% Cu price

# ---------------------------------------------------------------------------
# 5. Comminution / processing (03_domain.md §7)
# ---------------------------------------------------------------------------
CRUSHER_RATED_TPH = 4186.0        # [R] S3 gyratory 60x113
CONVEYOR_RATED_TPH = 4880.0       # [R] S3
SAG_RATED_TPH = 3425.0            # [R] S3
SAG_POWER_MW = 28.0               # [R] S3
BALL_MILL_RATED_TPH_EACH = 1706.0 # [R] S3
BALL_MILL_POWER_MW_EACH = 22.0    # [R] S3
FLOTATION_RATED_TPH_SOLIDS = 1576.0  # [R] S3
ETA_CIRCUIT = 0.85                # [A] 0.75-0.90 operating/lab WI ratio, §7.3
BOND_F80_UM = 2500.0              # [D] §7.3 worked example
BOND_P80_UM_BASE = 180.0          # [R] S3 ball-circuit target P80
CRUSHED_STOCKPILE_START_FRACTION = 0.7  # [A] pile part-full at start, so it can fill or drain
CRUSHED_STOCKPILE_CAPACITY_T = 40000.0  # [A] ~12h SAG feed, §3.2
PLANT_AVAILABILITY_BASE = 0.93    # [A] 92-94%, §7.2

# ---------------------------------------------------------------------------
# 6. Flotation (03_domain.md §7.4)
# ---------------------------------------------------------------------------
CU_CONC_GRADE_PCT = 22.0          # [A] Bozshakol twin default, §7.4 ("c ~ 22%")
CU_TAILS_GRADE_PCT = 0.105        # [D] implied by Bozshakol 79.7% recovery @ f=0.51%%, c=22%%, §7.4.
                                   # Check: R=(22/0.51)*(0.51-0.105)/(22-0.105) = 0.798, matches 79.7%% reported.
AU_RECOVERY_BASE = 0.60           # [R] S1, 55-62% band, §7.4
AU_RECOVERY_SIGMA = 0.03          # [A]
FLOT_P80_PENALTY_COEF = 0.00603   # [D] calibrated directly to the two worked points the doc gives
                                   # for phi(P80) (180um:-0.5pp, 240um:-2.1pp, §7.4 Model B) --
                                   # the doc's own "0.0006" literal coefficient does not reproduce
                                   # its own -0.5pp/-2.1pp examples at exponent 1.3; this value does
                                   # (0.5/(30^1.3)=0.00602, 2.1/(90^1.3)=0.00604).
FLOT_P80_PENALTY_EXP = 1.3        # [A][T11]
FLOT_P80_REF_UM = 150.0           # [A][T11]
FLOT_CLAY_PENALTY_CU_PP = 3.5     # [R] S1 derived, -2 to -5 pp Cu, §7.4
FLOT_CLAY_PENALTY_AU_PP = 6.0     # [R] S1, -4 to -8 pp Au, §7.4
MO_RECOVERY_BASE = 0.75           # [R] S6
MO_CONC_GRADE_PCT = 46.3          # [R] S6

# ---------------------------------------------------------------------------
# 7. Reliability (03_domain.md §8.1)
# ---------------------------------------------------------------------------
# Weibull (beta, eta_hours) dominant failure mode per asset, plus MTTR band (hours)
WEIBULL_PARAMS = {
    "truck": {"beta": 1.5, "eta_h": 700.0, "mttr_h": (4.0, 8.0), "tow_h": (1.0, 2.0)},   # [A] §8.1 engine/cooling
    "shovel": {"beta": 1.2, "eta_h": 250.0, "mttr_h": (3.0, 6.0), "tow_h": (0.0, 0.0)},  # [A] §8.1 hydraulics
    "drill": {"beta": 1.5, "eta_h": 500.0, "mttr_h": (2.0, 5.0), "tow_h": (0.0, 0.0)},   # [A] §8.1 bit life proxy
    "crusher": {"beta": 2.5, "eta_h": 400.0, "mttr_h": (4.0, 12.0), "tow_h": (0.0, 0.0)},# [A] §8.1 spider bushing
    "mill": {"beta": 2.0, "eta_h": 1000.0, "mttr_h": (6.0, 24.0), "tow_h": (0.0, 0.0)},  # [A] §8.1 GMD trips+relines
}
# Failure modes other than the Weibull wear-out mode above (electrical, suspension, tyres, GET...),
# modelled as exponential (random, not predictable from the condition signal). MTBF is derived so
# that, together with the wear-out mode, the all-causes MTBF matches 03_domain.md §8.1:
#   1/MTBF_other = 1/MTBF_all - 1/(eta*Gamma(1+1/beta))
#   truck:  1/90 - 1/632 -> ~105 h;  shovel: 1/60 - 1/235 -> ~80 h;  drill: 1/45 - 1/451 -> ~50 h  [D]
OTHER_FAILURES = {
    "truck": {"mtbf_h": 105.0, "mttr_h": (4.0, 8.0), "tow_h": (0.5, 1.5)},
    "shovel": {"mtbf_h": 80.0, "mttr_h": (3.0, 6.0), "tow_h": (0.0, 0.0)},
    "drill": {"mtbf_h": 50.0, "mttr_h": (2.0, 5.0), "tow_h": (0.0, 0.0)},
}
SHOVEL_FAILURE_MTTR_H = 10.0       # [A] §11-S1 worked example (fixed for scenario reproducibility)
PREDICTIVE_LEAD_TIME_H = (24.0, 72.0)  # [A] §8.2, 24-72h lead time
PREDICTIVE_MTTR_H = (5.0, 7.0)         # [A] §8.1, planned job replacing 12-16h unplanned
PA_GAIN_PREDICTIVE_PP = 0.025          # [A] §11-S9, +2 to +3 pp truck PA
SHIFT_LENGTH_H = 12.0
KPI_EMA_TAU_H = 1.0           # [A] smoothing time constant for pit-side rate KPIs (1 h of mine time)
KPI_CYCLE_EMA_WEIGHT = 0.15   # [A] weight of each completed haul cycle in the cycle-time average
BUFFER_LOW_H = 6.0
NO_SHOVEL_RETRY_S = 300.0
ROM_PAD_CAPACITY_T = 150000.0  # [A] run-of-mine pad in front of the crusher (twin attribute capacity_t)
BALL_MILL_RATED_TPH = 1706.0   # [R] S3: each of the two ball mills takes half the SAG product
BALL_MILL_MAX_TPH = 1706.0 * 1.2  # [A] design margin: ball mills can take ~20 % above nominal
MILL_NO_LOAD_POWER_FRACTION = 0.25  # [A] mill draw with the drum turning but little charge
MANUAL_REASSIGN_H = 0.5        # [A] without the dispatch system a supervisor reassigns a truck by radio
     # [A] truck waits 5 min before asking dispatch again when no shovel is up
# Grade control (03_domain.md §3.2, §11-S1: LP dispatch with a grade constraint plus HG stockpile
# reclaim recovers about two-thirds of a grade loss; Bozshakol blended from HG piles in Q4 2020 [S1]).
GC_TARGET_GRADE_PCT = 0.50    # [A] crusher-feed grade floor, just below the 0.515% blended face grade
GC_RECLAIM_MAX_TPH = 800.0    # [A] one large wheel loader rehandling to the crusher
HG_STOCKPILE_T = 150000.0     # [A] high-grade reserve pile at start
HG_STOCKPILE_GRADE_PCT = 0.65 # [A] high-grade cut of the ore body, §3.1 grade distribution            # [A] alert when crushed ore covers less than half a shift of mill feed                  # [A] §1.2, 2x12h shifts

# Condition-monitoring thresholds (03_domain.md §8.2)
COOLANT_TEMP_NORMAL_C = (85.0, 95.0)
COOLANT_TEMP_WARN_C = 102.0
COOLANT_TEMP_SHUTDOWN_C = 107.0
OIL_FE_NORMAL_PPM = 30.0
OIL_FE_ALARM_PPM = 60.0

# ---------------------------------------------------------------------------
# 8. Environment / dust / gas (03_domain.md §5.1, §5.2)
# ---------------------------------------------------------------------------
PM10_AP42_K = 1.5    # [L] S27 US EPA AP-42 13.2.2
PM10_AP42_A = 0.9    # [L] S27
PM10_AP42_B = 0.45   # [L] S27
HAUL_ROAD_SILT_PCT = 8.0          # [A] mid of 5-15%, §5.1
WATERING_CONTROL_EFFICIENCY = 0.65  # [A] 50-75% typical, §5.1
PM10_WHO_24H_UGM3 = 45.0          # [L] S24
PM10_KZ_DAILY_MGM3 = 0.06         # [L] S25
GAS_REENTRY_BASE_MIN = 30.0       # [L] S30

# ---------------------------------------------------------------------------
# 9. Weather (03_domain.md §5.4)
# ---------------------------------------------------------------------------
TEMP_WINTER_EXTREME_C = -38.0      # [R] S3 ("down to -40C")
TEMP_SUMMER_MAX_C = 37.0           # [A] 35-40C band
TEMP_BASELINE_C = 15.0             # [A] mild baseline for the "none" scenario
WIND_BASELINE_MS = 4.0             # [A]
WIND_BLIZZARD_MS = 12.0            # [L] S34, 15-25 m/s gusts band (use conservative 12)
COLD_THRESHOLD_C = -30.0           # [A] §5.4 cold-effects threshold
COLD_HYDRAULIC_PENALTY = 0.15      # [A] -10-20% hydraulic response, §5.4
COLD_WARMUP_MIN = 40.0             # [A] +30-45 min warm-up, §5.4
COLD_TYRE_DAMAGE_MULT = 1.2        # [A] §5.4
COLD_SPEED_CAP_RAMP_KMH = 20.0     # [D] §11-S2
COLD_SPEED_CAP_FLAT_KMH = 30.0     # [D] §11-S2

# ---------------------------------------------------------------------------
# 10. Energy & emissions (03_domain.md §6)
# ---------------------------------------------------------------------------
GRID_TARIFF_KZT_PER_KWH = 19.0     # [A] 16-22 band, §6.1
DIESEL_PRICE_KZT_PER_L = 320.0     # [A] 300-340 band, §6.2
USD_KZT_FX = 457.0                 # [L] S43
DIESEL_PRICE_USD_PER_L = DIESEL_PRICE_KZT_PER_L / USD_KZT_FX   # [D]
GRID_TARIFF_USD_PER_KWH = GRID_TARIFF_KZT_PER_KWH / USD_KZT_FX # [D]
DIESEL_CO2_KG_PER_L = 2.68         # [L] S35/S36
GRID_CO2_KG_PER_KWH = 0.80         # [A] central, 0.60-1.05 sensitivity, §6.3
GRID_CO2_KG_PER_KWH_EKIBASTUZ = 1.05  # [A] direct coal supply, §6.3
TROLLEY_BREAKEVEN_GRID_FACTOR = 0.64  # [D] §6.4
TROLLEY_SPEED_GAIN = 1.0           # [L] S16 "up to 100%" speed-on-grade gain under trolley
TROLLEY_DIESEL_CUT = 0.90          # [L] S16, >90% diesel/engine cost cut on trolley sections
TROLLEY_RAMP_LENGTH_KM = 1.2       # [R]/[A] §11-S12 "1.2 km main ramp"
# §6.4 energy-conservation chain: 1 L diesel = 35.9 MJ = 9.97 kWh raw; at ~38% engine efficiency
# that is ~3.8 kWh of shaft/wheel work. An electric trolley needs ~4.2 kWh from the grid (at ~90%
# delivery efficiency) to do that SAME wheel work -- i.e. grid kWh needed per litre of diesel
# displaced is 3.8/0.90 = 4.2. [D], both numbers quoted directly in 03_domain.md §6.4.
TROLLEY_SHAFT_KWH_PER_L = 3.8
TROLLEY_GRID_KWH_PER_L_DISPLACED = 4.2

# ---------------------------------------------------------------------------
# 11. Economics (03_domain.md §9)
# ---------------------------------------------------------------------------
CU_PRICE_USD_T_BASE = 14500.0      # [D]/[L] S44, §9.3 base case
CU_PRICE_USD_T_SHOCK = 10900.0     # [A] §11-S10, -25%
AU_PRICE_USD_OZ = 4300.0           # [L] S45, §9.3 base case
PAY_CU = 0.965                     # [A] standard contract terms, §9.1
PAY_AU = 0.95                      # [A] §9.1
TC_RC_USD_PER_T = 0.0              # [L] S46 2026 benchmark
TC_RC_USD_PER_T_SHOCK = 80.0       # [A] §11-S10 reverse scenario value, turns positive (cost)
MET_CU_FRACTION = 0.0855           # [A, verify KZ Tax Code] §9.2
MET_AU_FRACTION = 0.0765           # [A, verify KZ Tax Code] §9.2
COST_MINING_USD_T_MOVED = 2.0      # [A] §9.2
COST_PROCESSING_USD_T_ORE = 5.5    # [A] §9.2
COST_GA_USD_T_ORE = 1.0            # [A] §9.2
OZ_PER_T_AU = 1.0 / 31.1035e-6     # [D] troy-oz conversion (g/t -> oz/t): 1/31.1035 g per oz
STRIP_RATIO_BASE = 0.70            # [R] S3 Bozshakol LOM
