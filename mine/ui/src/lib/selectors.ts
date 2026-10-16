import type { DittoThing } from "../types";
import { KPI_THING_ID, SCENARIO_THING_ID } from "../types";

export function getScenarioThing(things: Record<string, DittoThing>): DittoThing | undefined {
  return things[SCENARIO_THING_ID];
}

export function getKpiThing(things: Record<string, DittoThing>): DittoThing | undefined {
  return things[KPI_THING_ID];
}

export function listByClass(things: Record<string, DittoThing>, className: string): DittoThing[] {
  return Object.values(things)
    .filter((t) => t.attributes?.class === className && !t.attributes?._isType)
    .sort((a, b) => a.thingId.localeCompare(b.thingId));
}

export function sortedRoadIds(things: Record<string, DittoThing>): string[] {
  return listByClass(things, "RoadSegment").map((t) => t.thingId);
}

export function featureNumber(thing: DittoThing | undefined, name: string, fallback = 0): number {
  const v = thing?.features?.[name]?.properties.value;
  return typeof v === "number" ? v : fallback;
}

export function featureString(thing: DittoThing | undefined, name: string, fallback = ""): string {
  const v = thing?.features?.[name]?.properties.value;
  return typeof v === "string" ? v : fallback;
}

export function featureUnit(thing: DittoThing | undefined, name: string): string {
  return thing?.features?.[name]?.properties.unit ?? "";
}

/** Truck haul-cycle phase colours (engine `state` values). */
export const TRUCK_STATE_LEGEND: { key: string; label: string; color: string }[] = [
  { key: "hauling", label: "Hauling (loaded)", color: "#f0883e" },
  { key: "returning", label: "Returning (empty)", color: "#58a6ff" },
  { key: "loading", label: "Spotting / loading", color: "#3fb950" },
  { key: "queued", label: "Queued", color: "#e3d341" },
  { key: "dumping", label: "Dumping", color: "#d2a8ff" },
  { key: "down", label: "Down (failure)", color: "#ff4d4d" },
  { key: "parked", label: "Parked", color: "#8b949e" }
];
const LEGEND_COLOR = Object.fromEntries(TRUCK_STATE_LEGEND.map((l) => [l.key, l.color]));

export function truckColor(state: string, parked = false): string {
  if (parked) return LEGEND_COLOR.parked;
  if (state === "hauling") return LEGEND_COLOR.hauling;
  if (state === "returning") return LEGEND_COLOR.returning;
  if (state === "loading" || state === "spotting") return LEGEND_COLOR.loading;
  if (state.startsWith("queued")) return LEGEND_COLOR.queued;
  if (state === "dumping") return LEGEND_COLOR.dumping;
  if (state === "down") return LEGEND_COLOR.down;
  return "#c9d1d9";
}

/** Shovel/drill/plant state colour: working green, blocked/starved amber, down red. */
export function shovelColor(state: string): string {
  if (state === "down" || state === "failed" || state === "breakdown") return "#ff4d4d";
  if (state === "blocked" || state === "starved" || state === "idle") return "#e3b341";
  return "#3fb950";
}

export function stateColor(state: string | undefined): string {
  if (!state) return "#8b949e";
  return shovelColor(state);
}
