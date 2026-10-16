// Shared data types for the Kyzyl-Tas Mine UI.
//
// These mirror the Ditto "thing" shape.
// Optional fields below cover shapes not every twin has
// a running engine and had to infer from 03_domain.md.

export interface Vec3 {
  x: number;
  y: number;
  z: number;
}

/** One Ditto feature: always `{ properties: { value, unit } }`, value type stable per feature. */
export interface DittoFeature {
  properties: {
    value: number | string;
    unit?: string;
  };
}

export type DittoFeatures = Record<string, DittoFeature>;

export interface DittoAttributes {
  _isType?: boolean;
  _parents?: string | string[] | Record<string, unknown>;
  name?: string;
  description?: string;
  class?: string;
  geometry?: Vec3;
  /** Road segments / graph edges: optional endpoints. */
  from?: string;
  to?: string;
  length_m?: number;
  grade_pct?: number;
  [key: string]: unknown;
}

export interface DittoThing {
  thingId: string;
  policyId?: string;
  definition?: string;
  attributes?: DittoAttributes;
  features?: DittoFeatures;
}

export interface SearchThingsResponse {
  items: DittoThing[];
  cursor?: string;
  nextPageOffset?: string;
}

/**
 * Scenario control twin features, as created by mine/setup/model.json (13 fields).
 */
export interface ScenarioFeatures {
  active_scenario: string;
  run_id: string;
  truck_count_delta: number;
  shovel_down_id: string;
  crusher_availability: number;
  blast_powder_factor: number;
  fan_speed_factor: number;
  dispatch_policy: "dynamic" | "fixed";
  ambient_temp_c: number;
  ore_bwi_kwht: number;
  mill_power_factor: number;
  road_rr_bonus_pct: number;
  cu_price_usd_t: number;
}

export const SCENARIO_THING_ID = "kz.kyzyltas.mine:scenario";
export const KPI_THING_ID = "kz.kyzyltas.mine:kpi";
export const NAMESPACE = "kz.kyzyltas.mine";

/** Baseline/default values, as created by mine/setup/model.json. */
export const SCENARIO_DEFAULTS: ScenarioFeatures = {
  active_scenario: "none",
  run_id: "baseline",
  truck_count_delta: 0,
  shovel_down_id: "",
  crusher_availability: 1.0,
  blast_powder_factor: 1.0,
  fan_speed_factor: 1.0,
  dispatch_policy: "dynamic",
  ambient_temp_c: 15,
  ore_bwi_kwht: 14,
  mill_power_factor: 1.0,
  road_rr_bonus_pct: 0,
  cu_price_usd_t: 14500
};

/**
 * active_scenario ids shared with mine/engine/scenarios.py, mapped to
 * 03_domain.md §11 S1-S12 (S11 has two variants), plus "custom".
 */
export const SCENARIO_IDS = [
  "none",
  "shovel_failure",
  "weather_cold_snap",
  "blast_intensify",
  "hard_ore_domain",
  "grid_curtailment",
  "road_thaw",
  "slope_alarm",
  "blast_delay",
  "predictive_maintenance",
  "price_drop",
  "dispatch_fixed",
  "fleet_minus_2",
  "trolley_assist",
  "custom"
] as const;

export type ConnectionStatus = "connecting" | "live" | "reconnecting" | "error";

export interface EventLogEntry {
  id: string;
  t: number; // ms epoch, client-side wall clock at detection time
  text: string;
  severity: "info" | "warning" | "critical";
  /** Mine time (hours since start) when the event was seen, if known. */
  simTimeH?: number;
}
