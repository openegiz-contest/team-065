// What-if scenario catalogue for the scenario control twin
// (kz.kyzyltas.mine:scenario).
//
// The twin has exactly 8 features (see types.ts). Four scenarios set a field
// beyond active_scenario/run_id; the engine keys every other scenario's
// physics off the `active_scenario` id (mine/engine/scenarios.py presets).
// Descriptions below follow the engine's own preset narratives.
//
// Every scenario button PATCHes only the fields it changes, plus a fresh
// `run_id` and the matching `active_scenario` id. "Undo" PATCHes all 8
// fields back to SCENARIO_DEFAULTS.

import type { DittoThing, ScenarioFeatures } from "../types";
import { SCENARIO_DEFAULTS } from "../types";

export type ScenarioFieldPatch = Partial<ScenarioFeatures>;

export type ScenarioGroup = "pit" | "plant" | "market";

export interface ScenarioDef {
  id: string; // matches active_scenario value - canonical enum, see types.ts SCENARIO_IDS
  label: string;
  group: ScenarioGroup;
  /** One-line effect summary shown on the button. */
  short: string;
  description: string;
  /** Cause -> effect steps shown in the active-scenario banner. */
  chain: string[];
  /** KPI keys (lib/kpi.ts METRICS) to watch while this scenario runs. */
  watch: string[];
  domainRef: string; // which 03_domain.md §11 causal chain this demonstrates
  /** Resolve the field patch at click time (needs live thing ids for the shovel-failure default). */
  buildPatch: (things: Record<string, DittoThing>) => ScenarioFieldPatch;
}

const ORE_SHOVEL_ID = "kz.kyzyltas.mine:shovel-s2";

function findOreShovel(things: Record<string, DittoThing>): string {
  if (things[ORE_SHOVEL_ID]) return ORE_SHOVEL_ID;
  // Defensive fallback in case the exact id differs.
  const shovels = Object.values(things).filter((t) => t.attributes?.class === "Shovel" && !t.attributes?._isType);
  const ore = shovels.find((t) => /ore|s1|s2/i.test(t.attributes?.name ?? t.thingId));
  return (ore ?? shovels[0])?.thingId ?? ORE_SHOVEL_ID;
}

export const SCENARIO_GROUPS: { id: ScenarioGroup; title: string }[] = [
  { id: "pit", title: "Pit & haulage" },
  { id: "plant", title: "Plant & processing" },
  { id: "market", title: "Energy, market & maintenance" }
];

export const SCENARIOS: ScenarioDef[] = [
  {
    id: "shovel_failure",
    label: "Shovel S2 failure",
    group: "pit",
    short: "Best ore face lost; grade control reclaims high-grade ore",
    description:
      "Ore shovel S2 (the 0.58% Cu face) has a hydraulic failure with a 10-hour repair. Dispatch moves its trucks to S1: over the first two mine hours ore mined falls ~15%, ore grade ~5% and the haul cycle rises ~18%. Grade control reclaims the high-grade stockpile and the crushed-ore buffer keeps the mill fed, so copper output falls only ~3%. If another shovel fails at random during the outage, ore mined drops much further.",
    chain: [
      "S2 hydraulic failure (10 h repair)",
      "Trucks rerouted to S1: ore −15%, grade −5%, cycle +18%",
      "Grade control reclaims high-grade stockpile",
      "Buffer keeps the mill fed: Cu output only −3%"
    ],
    watch: ["ore_mined_tph", "mined_grade_pct", "gc_reclaim_tph", "cu_tph", "buffer_h"],
    domainRef: "03_domain.md §11 S1",
    buildPatch: (things) => ({ shovel_down_id: findOreShovel(things) })
  },
  {
    id: "slope_alarm",
    label: "Slope radar alarm (east wall)",
    group: "pit",
    short: "Main ramp closed; ore detours via the west ramp",
    description:
      "The east-wall slope radar goes red and the main ore ramp is closed. Ore trucks detour via the west ramp (2.7 km instead of 1.2 km): the haul cycle rises ~19-28% and ore mined falls ~16-30%.",
    chain: [
      "Slope radar red alarm",
      "Main ore ramp closed",
      "Detour 2.7 km instead of 1.2 km",
      "Cycle +19-28%, ore mined −16-30%"
    ],
    watch: ["haul_cycle_min", "ore_mined_tph", "buffer_h", "tph"],
    domainRef: "03_domain.md §11 S7",
    buildPatch: () => ({})
  },
  {
    id: "blast_delay",
    label: "Post-blast fume delay (winter inversion)",
    group: "pit",
    short: "S1 and S3 idle ~150 min in the fume exclusion",
    description:
      "Blast fumes are trapped by a winter inversion, so re-entry takes ~150 min instead of 30. Shovels S1 and S3 stand idle meanwhile: ore mined falls ~15% over the first two mine hours, then recovers once the exclusion lifts.",
    chain: [
      "Fumes trapped by inversion",
      "Re-entry ~150 min",
      "S1 and S3 idle",
      "Ore mined −15%, then recovery"
    ],
    watch: ["ore_mined_tph", "moved_tph", "buffer_h"],
    domainRef: "03_domain.md §11 S8",
    buildPatch: () => ({})
  },
  {
    id: "weather_cold_snap",
    label: "Siberian cold snap (−38 °C)",
    group: "pit",
    short: "Slower haulage; road watering stops, dust doubles",
    description:
      "Temperature drops to −38 °C with 12 m/s wind. Winter speed caps and slower shovel hydraulics stretch the haul cycle by ~9-15% and ore mined falls ~5-13%. Haul roads cannot be watered below 0 °C, so road dust (PM10) about doubles. The crushed-ore buffer protects the mill.",
    chain: [
      "−38 °C, 12 m/s wind",
      "Speed caps, slower hydraulics",
      "Cycle +9-15%, ore −5-13%",
      "No watering: road PM10 ≈ ×2"
    ],
    watch: ["haul_cycle_min", "ore_mined_tph", "road_pm10_kg_h", "buffer_h"],
    domainRef: "03_domain.md §11 S2",
    buildPatch: () => ({})
  },
  {
    id: "road_thaw",
    label: "Spring thaw (wet haul roads)",
    group: "pit",
    short: "Soft roads: cycle +27-39%, ore −14-26%",
    description:
      "Spring thaw softens every haul road (rolling resistance +2.5 points). Loaded climbs slow down: the haul cycle rises ~27-39% and ore mined falls ~14-26%.",
    chain: [
      "Spring thaw",
      "Rolling resistance +2.5 points",
      "Slower loaded climbs",
      "Cycle +27-39%, ore −14-26%"
    ],
    watch: ["haul_cycle_min", "ore_mined_tph", "fuel_l_h", "buffer_h"],
    domainRef: "03_domain.md §11 S6",
    buildPatch: () => ({})
  },
  {
    id: "fleet_minus_2",
    label: "Fleet cut (−2 trucks)",
    group: "pit",
    short: "Two trucks parked: ore −10-14%",
    description:
      "Two ore trucks are parked. Ore mined falls ~10-14%: the remaining ten ore trucks queue less at the two ore shovels, which absorbs part of the loss.",
    chain: [
      "Two trucks parked",
      "Less queueing at the ore shovels",
      "Ore mined −10-14%"
    ],
    watch: ["ore_mined_tph", "moved_tph", "buffer_h"],
    domainRef: "03_domain.md §11 S11 variant",
    buildPatch: () => ({ truck_count_delta: -2 })
  },
  {
    id: "dispatch_fixed",
    label: "Fleet-management system offline",
    group: "pit",
    short: "No dispatch or grade control; trucks wait for radio reassignment",
    description:
      "The fleet-management system goes offline: trucks keep their shift-plan shovels, a truck whose shovel breaks waits ~30 min for a supervisor to reassign it by radio, and grade control stops. In normal running the effect is small (about 0%) because the shovels are balanced; the system's value shows when a shovel fails or the ore grade drops.",
    chain: [
      "Dispatch and grade control offline",
      "Trucks keep shift-plan shovels",
      "Broken shovel: trucks idle ~30 min until radio reassignment",
      "Normal running: about 0%"
    ],
    watch: ["ore_mined_tph", "moved_tph", "mined_grade_pct"],
    domainRef: "03_domain.md §11 S11",
    buildPatch: () => ({ dispatch_policy: "fixed" })
  },
  {
    id: "blast_intensify",
    label: "Intensify blast (PF 0.30 -> 0.40 kg/t)",
    group: "plant",
    short: "Finer feed: plant output +11% at once",
    description:
      "Powder factor rises from 0.30 to 0.40 kg/t. Finer fragmentation lets the SAG mill take ~11% more ore: mill feed, copper output and revenue rise ~11% at once, and the crushed-ore buffer is drawn down ~10% over ten mine hours.",
    chain: [
      "Powder factor 0.30 -> 0.40 kg/t",
      "Finer SAG feed (Kuz-Ram X50 −21%)",
      "Mill feed, Cu, revenue +11%"
    ],
    watch: ["tph", "cu_tph", "nsr_usd_h", "buffer_h"],
    domainRef: "03_domain.md §11 S3",
    buildPatch: () => ({ blast_powder_factor: 1.33 })
  },
  {
    id: "hard_ore_domain",
    label: "Harder ore domain (BWi 14 -> 16)",
    group: "plant",
    short: "Harder rock: plant output −24%",
    description:
      "The pit reaches a harder ore domain (Bond Wi 14 -> 16 kWh/t, Axb 45 -> 32). At fixed mill power the SAG mill takes ~24% less ore: mill feed, copper output and revenue fall ~24%, and the crushed-ore buffer covers more hours of feed.",
    chain: [
      "Harder ore (Wi 14 -> 16, Axb 45 -> 32)",
      "More grinding energy per tonne",
      "Mill feed, Cu, revenue −24%",
      "Buffer covers more hours of feed"
    ],
    watch: ["tph", "cu_tph", "nsr_usd_h", "buffer_h"],
    domainRef: "03_domain.md §11 S4",
    buildPatch: () => ({})
  },
  {
    id: "grid_curtailment",
    label: "Grid power curtailment (mills at 75%)",
    group: "plant",
    short: "Mills derated: output −25%, grid energy −13-23%",
    description:
      "The grid operator orders a curtailment and the SAG and ball mills are limited to 75% of their power (about 18 MW less). Mill feed and copper output fall ~25%, grid energy and CO₂ fall ~13-23%, and the crushed-ore buffer covers more hours of feed.",
    chain: [
      "Grid curtailment: mills limited to 75% power",
      "Mill feed, Cu −25%",
      "Grid energy and CO₂ −13-23%",
      "Buffer covers more hours of feed"
    ],
    watch: ["tph", "cu_tph", "energy_kwh_h", "co2_t_h"],
    domainRef: "03_domain.md §11 S5",
    buildPatch: () => ({})
  },
  {
    id: "trolley_assist",
    label: "Enable trolley assist",
    group: "market",
    short: "Electric trucks on trolley: diesel −4-7%",
    description:
      "Trolley assist is energised on the main ore ramp. Only the two Komatsu 830E trucks have AC electric drive and can use it: they climb faster and burn less diesel (fleet diesel −4-7%, ore mined up to +5%). On the coal-heavy Kazakh grid the electricity they draw emits about as much CO₂ as the diesel it replaces.",
    chain: [
      "Trolley line energised",
      "Two electric 830E trucks climb faster",
      "Fleet diesel −4-7%",
      "CO₂ about unchanged: coal-heavy grid"
    ],
    watch: ["haul_cycle_min", "ore_mined_tph", "fuel_l_h", "co2_t_h"],
    domainRef: "03_domain.md §11 S12",
    buildPatch: () => ({})
  },
  {
    id: "price_drop",
    label: "Copper price drop (−25%)",
    group: "market",
    short: "Revenue −19%, physical KPIs unchanged",
    description:
      "The copper price falls 25% ($14,500 -> $10,900/t) and treatment charges turn positive. Net smelter revenue falls ~19%; the mine and plant run exactly as before.",
    chain: [
      "Cu $14,500 -> $10,900/t",
      "TC/RC +$80/dmt",
      "Revenue −19%",
      "Physical KPIs unchanged"
    ],
    watch: ["nsr_usd_h", "margin_usd_h", "cu_tph"],
    domainRef: "03_domain.md §11 S10",
    buildPatch: () => ({})
  },
  {
    id: "predictive_maintenance",
    label: "Predictive maintenance (vs reactive)",
    group: "market",
    short: "Fewer breakdowns over days of mine time",
    description:
      "Condition monitoring raises work orders for trucks whose coolant and oil-iron trends show wear, and they are repaired at the next shift change instead of failing in service. The gain builds over days of mine time: averaged over 8 seeded runs of 200 mine hours (about 3.3 real hours), unplanned failures fell ~23%, while fleet availability stayed about the same because planned repairs also take trucks out. Compare unplanned failures against the baseline.",
    chain: [
      "Condition signals flag wear",
      "Work orders: repair at shift change",
      "Fewer unplanned failures and tows",
      "~23% fewer failures over 200 mine hours"
    ],
    watch: ["fleet_avail_pct", "unplanned_failures", "planned_repairs"],
    domainRef: "03_domain.md §11 S9",
    buildPatch: () => ({})
  }
];

/** Build the full merge-patch feature object Ditto expects for a field patch. */
export function toFeaturePatch(
  patch: ScenarioFieldPatch
): Record<string, { properties: { value: number | string; unit?: string } }> {
  const out: Record<string, { properties: { value: number | string; unit?: string } }> = {};
  for (const [key, value] of Object.entries(patch)) {
    if (value === undefined) continue;
    out[key] = { properties: { value } };
  }
  return out;
}

/** The complete default feature set (all 13 fields), used by the global Undo button. */
export function buildResetPatch(): ScenarioFieldPatch {
  return { ...SCENARIO_DEFAULTS };
}

/**
 * Live checks for banner chain lines (same index as `chain`). A line whose check is not met yet
 * is shown muted with what it is waiting for, so the banner never claims what the stand does not show.
 */
export interface ChainCheck {
  thing: string; // thingId
  feature: string;
  test: "gt0" | "eq";
  value?: string | number;
  waiting: string;
}

const NS_ = "kz.kyzyltas.mine:";
export const CHAIN_CHECKS: Record<string, (ChainCheck | null)[]> = {
  shovel_failure: [
    { thing: NS_ + "shovel-s2", feature: "state", test: "eq", value: "down", waiting: "S2 not down yet" },
    null,
    { thing: NS_ + "kpi", feature: "gc_reclaim_tph", test: "gt0", waiting: "ROM ore still on grade, no reclaim needed yet" },
    { thing: NS_ + "kpi", feature: "current_tph", test: "gt0", waiting: "SAG mill is down" }
  ],
  slope_alarm: [
    { thing: NS_ + "slope-radar-01", feature: "tarp_level", test: "eq", value: "red", waiting: "radar not red yet" },
    { thing: NS_ + "road-ramp-ore-up", feature: "closed", test: "eq", value: 1, waiting: "ramp still open" }
  ],
  hard_ore_domain: [null, null, { thing: NS_ + "kpi", feature: "current_tph", test: "gt0", waiting: "SAG mill is down" }],
  grid_curtailment: [null, { thing: NS_ + "kpi", feature: "current_tph", test: "gt0", waiting: "SAG mill is down" }],
  blast_intensify: [null, null, { thing: NS_ + "kpi", feature: "current_tph", test: "gt0", waiting: "SAG mill is down" }]
};

export function chainCheckMet(c: ChainCheck, things: Record<string, DittoThing>): boolean {
  const v = things[c.thing]?.features?.[c.feature]?.properties.value;
  if (c.test === "gt0") return typeof v === "number" && v > 0;
  return v === c.value;
}
