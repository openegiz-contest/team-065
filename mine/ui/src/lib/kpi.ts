// KPI catalogue for the engine's kpi twin (kz.kyzyltas.mine:kpi), which
// publishes current_<k>, baseline_<k> and delta_<k>_pct for every metric k
// below (mine/engine/publish.py build_kpi_features). Baseline is the
// engine's shadow simulation running the same clock with no scenario.

import type { DittoThing } from "../types";

export type Direction = "up" | "down" | "neutral";
export type KpiGroup = "pit" | "plant" | "econ";

export interface MetricDef {
  key: string;
  label: string;
  unit: string;
  group: KpiGroup;
  /** Which direction is good for the operation. */
  good: Direction;
  /** Optional display scaling (e.g. kWh/h -> MW). */
  scale?: number;
  digits?: number;
  hint?: string;
  /** A single live feature on the kpi twin (no baseline pair). */
  plain?: boolean;
}

export const METRICS: MetricDef[] = [
  // Pit: haulage and mining - react within about a minute of a haulage scenario.
  { key: "ore_mined_tph", label: "Ore mined", unit: "t/h", group: "pit", good: "up" },
  { key: "moved_tph", label: "Material moved (ore + waste)", unit: "t/h", group: "pit", good: "up" },
  { key: "mined_grade_pct", label: "Mined ore grade", unit: "% Cu", group: "pit", good: "up", digits: 3 },
  { key: "cu_mined_tph", label: "Contained Cu mined", unit: "t/h", group: "pit", good: "up", digits: 2 },
  { key: "haul_cycle_min", label: "Haul cycle time", unit: "min", group: "pit", good: "down", digits: 1 },
  { key: "fleet_avail_pct", label: "Truck fleet availability", unit: "%", group: "pit", good: "up", digits: 1 },
  // Plant: fed from the crushed-ore stockpile, so haulage losses arrive later.
  { key: "buffer_h", label: "Crushed-ore buffer", unit: "h at full rate", group: "plant", good: "up", digits: 1 },
  { key: "tph", label: "SAG mill feed", unit: "t/h", group: "plant", good: "up" },
  { key: "mill_kwh_t", label: "Grinding energy", unit: "kWh/t", group: "plant", good: "down", digits: 1 },
  { key: "cu_tph", label: "Cu in concentrate", unit: "t/h", group: "plant", good: "up", digits: 2 },
  { key: "au_ozph", label: "Au in concentrate", unit: "oz/h", group: "plant", good: "up", digits: 1 },
  // Economics & energy.
  { key: "nsr_usd_h", label: "Net smelter revenue", unit: "$/h", group: "econ", good: "up" },
  { key: "margin_usd_h", label: "Operating margin", unit: "$/h", group: "econ", good: "up" },
  { key: "energy_kwh_h", label: "Grid power draw", unit: "MW", group: "econ", good: "down", scale: 1 / 1000, digits: 1 },
  { key: "fuel_l_h", label: "Diesel burn", unit: "L/h", group: "econ", good: "down" },
  { key: "co2_t_h", label: "CO₂ emissions", unit: "t/h", group: "econ", good: "down", digits: 1 }
];

export const GROUPS: { id: KpiGroup; title: string; note: string }[] = [
  { id: "pit", title: "Pit - haulage & mining", note: "Responds within about a minute (about 1 mine hour) of a haulage change." },
  {
    id: "plant",
    title: "Plant - concentrator",
    note: "Fed from the crushed-ore stockpile: a haulage loss only reaches the mill once the buffer runs down."
  },
  { id: "econ", title: "Economics & energy", note: "Revenue follows plant output and the copper price; energy and CO₂ follow fleet and mill load." }
];

/** Extra indicators used in the scenario banner (not in the comparison table). */
export const EXTRA_METRICS: MetricDef[] = [
  { key: "gc_reclaim_tph", label: "High-grade stockpile reclaim", unit: "t/h", group: "pit", good: "neutral", plain: true },
  { key: "road_pm10_kg_h", label: "Haul-road dust (PM10)", unit: "kg/h", group: "econ", good: "down", plain: true, digits: 0 },
  { key: "unplanned_failures", label: "Unplanned failures", unit: "count", group: "pit", good: "down", digits: 0 },
  { key: "planned_repairs", label: "Planned repairs", unit: "count", group: "pit", good: "neutral", digits: 0 }
];

export function metric(key: string): MetricDef | undefined {
  return METRICS.find((m) => m.key === key) ?? EXTRA_METRICS.find((m) => m.key === key);
}

export interface MetricReading {
  def: MetricDef;
  current: number | null;
  baseline: number | null;
  deltaPct: number | null;
}

function num(thing: DittoThing | undefined, name: string): number | null {
  const v = thing?.features?.[name]?.properties.value;
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

export function readMetric(kpi: DittoThing | undefined, def: MetricDef): MetricReading {
  const s = def.scale ?? 1;
  if (def.plain) {
    const v = num(kpi, def.key);
    return { def, current: v === null ? null : v * s, baseline: null, deltaPct: null };
  }
  const c = num(kpi, `current_${def.key}`);
  const b = num(kpi, `baseline_${def.key}`);
  let d = num(kpi, `delta_${def.key}_pct`);
  if (d === null && c !== null && b !== null && b !== 0) d = ((c - b) / Math.abs(b)) * 100;
  return { def, current: c === null ? null : c * s, baseline: b === null ? null : b * s, deltaPct: d };
}

/** "good" | "bad" | "flat" for a delta, given which direction is good. */
export function deltaTone(deltaPct: number | null, good: Direction, threshold = 0.5): "good" | "bad" | "flat" {
  if (deltaPct === null || Math.abs(deltaPct) < threshold || good === "neutral") return "flat";
  const up = deltaPct > 0;
  return (good === "up") === up ? "good" : "bad";
}

export function formatDelta(deltaPct: number | null): string {
  if (deltaPct === null) return "-";
  if (Math.abs(deltaPct) < 0.05) return "±0.0%";
  const sign = deltaPct > 0 ? "+" : "−";
  return `${sign}${Math.abs(deltaPct).toFixed(Math.abs(deltaPct) < 10 ? 1 : 0)}%`;
}

/** Compact number formatting with thin grouping. */
export function fmt(value: number | null | undefined, digits?: number): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "-";
  const a = Math.abs(value);
  if (digits !== undefined) return value.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  if (a >= 100) return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (a >= 10) return value.toFixed(1);
  return value.toFixed(2);
}

/** Money: $242.2k / $1.25M. */
export function fmtMoney(value: number | null): string {
  if (value === null || !Number.isFinite(value)) return "-";
  const a = Math.abs(value);
  const sign = value < 0 ? "−" : "";
  if (a >= 1e6) return `${sign}$${(a / 1e6).toFixed(2)}M`;
  if (a >= 1e3) return `${sign}$${(a / 1e3).toFixed(1)}k`;
  return `${sign}$${a.toFixed(0)}`;
}

export function formatMetric(def: MetricDef, value: number | null): string {
  if (def.unit === "$/h") return fmtMoney(value);
  return fmt(value, def.digits);
}

export function unitFor(def: MetricDef): string {
  return def.unit === "$/h" ? "/h" : def.unit;
}

/** Back-compat helper used by the inspector. */
export function formatNumber(value: number): string {
  return fmt(value);
}
