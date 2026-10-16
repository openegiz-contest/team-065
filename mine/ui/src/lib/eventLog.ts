// Causal event-log rule engine.
//
// We have no backend to test against, so this derives human-readable log
// lines purely from feature-value *transitions* we observe on the SSE
// stream, using the simple rules below.
// It does not invent numbers: every figure in a log line comes from a twin
// feature we actually saw change.
//
// Design: each rule looks at (previous value, new value, thing) for one
// feature name and returns zero or one log line. The scenario-activation
// rule also seeds a line from the scenario's own description (lib/scenarios.ts),
// which already encodes the expected causal chain from 03_domain.md §11 -
// the lines that follow it in the feed (queue/throughput/health changes)
// read as that chain's observed consequences because they arrive right after.

import type { DittoThing, EventLogEntry } from "../types";
import { SCENARIO_THING_ID } from "../types";
import { SCENARIOS } from "./scenarios";

let seq = 0;

// Routine changes (truck reroutes, queue swings, throughput wobble) happen every
// haul cycle at the engine's sim speed-up; without a per-thing cooldown they
// would bury the failures and scenario consequences the log exists to show.
const lastFired = new Map<string, number>();
function cooled(key: string, minMs: number): boolean {
  const now = Date.now();
  const last = lastFired.get(key) ?? 0;
  if (now - last < minMs) return false;
  lastFired.set(key, now);
  return true;
}
function nextId(): string {
  seq += 1;
  return `evt-${Date.now()}-${seq}`;
}

function displayName(thing: DittoThing | undefined, fallbackId: string): string {
  return thing?.attributes?.name ?? thing?.attributes?.description ?? fallbackId.split(":").pop() ?? fallbackId;
}

function num(v: unknown): number | undefined {
  return typeof v === "number" ? v : undefined;
}

function str(v: unknown): string | undefined {
  return typeof v === "string" ? v : undefined;
}

export interface DiffInput {
  thingId: string;
  thing: DittoThing | undefined; // post-update thing (for name lookup)
  prevFeatures: Record<string, { properties: { value: number | string } }> | undefined;
  newFeatures: Record<string, { properties: { value: number | string } }>;
}

/**
 * Evaluate every rule against one thing's feature delta and return any
 * log lines produced. Called once per incoming SSE message (per thing).
 */
export function evaluateRules(input: DiffInput, allThings: Record<string, DittoThing>): EventLogEntry[] {
  const events: EventLogEntry[] = [];
  const { thingId, thing, prevFeatures, newFeatures } = input;
  const name = displayName(thing, thingId);

  const prevOf = (f: string) => prevFeatures?.[f]?.properties.value;
  const newOf = (f: string) => newFeatures?.[f]?.properties.value;
  const changed = (f: string) => f in newFeatures && prevOf(f) !== newOf(f);

  // --- Rule: scenario activation / undo -------------------------------
  if (thingId === SCENARIO_THING_ID && changed("active_scenario")) {
    const nextId_ = str(newOf("active_scenario")) ?? "none";
    if (nextId_ === "none") {
      events.push(mk("Scenario reset to baseline - all control fields restored to their defaults.", "info"));
    } else {
      const def = SCENARIOS.find((s) => s.id === nextId_);
      events.push(
        mk(
          def ? `Scenario activated: ${def.label}` : nextId_ === "custom" ? "Custom what-if applied" : `Scenario activated: ${nextId_}`,
          "warning"
        )
      );
    }
  }

  // --- Rule: engine-published causal events (kpi twin) -----------------
  // mine-engine publishes its own human-readable event (failures, work
  // orders, fume exclusions, scenario narratives) as kpi.last_event with an
  // increasing kpi.event_seq. These are authoritative, so always shown.
  if (changed("event_seq")) {
    const text = str(newOf("last_event"));
    if (text) {
      const lower = text.toLowerCase();
      const sev: EventLogEntry["severity"] =
        /failure|forced down|starved|breakdown|failed|red alarm|closed/.test(lower) ? "critical"
        : /scenario|exclusion|work order|at risk|below|detour|derate|curtail/.test(lower) ? "warning"
        : "info";
      // The UI stamps every line with mine time, so drop the engine's "[t=..h]" prefix.
      events.push(mk(text.replace(/^\[t=[^\]]*\]\s*/, ""), sev));
    }
  }

  // --- Rule: equipment state transition --------------------------------
  if (changed("state")) {
    const from = str(prevOf("state")) ?? "unknown";
    const to = str(newOf("state")) ?? "unknown";
    if (to === "breakdown" || to === "failed" || to === "down") {
      events.push(mk(`${name} failed (state: ${from} -> ${to})`, "critical"));
    } else if (from === "breakdown" || from === "failed" || from === "down") {
      events.push(mk(`${name} back in service (state: ${from} -> ${to})`, "info"));
    }
  }

  // --- Rule: queue length change ---------------------------------------
  if (changed("queue_length")) {
    const from = num(prevOf("queue_length"));
    const to = num(newOf("queue_length"));
    if (from !== undefined && to !== undefined && Math.abs(to - from) >= 2 && cooled(`${thingId}:queue`, 15000)) {
      const delta = to - from;
      const sign = delta > 0 ? "+" : "";
      events.push(mk(`${name} queue ${from} -> ${to} (${sign}${delta})`, delta > 0 ? "warning" : "info"));
    }
  }

  // --- Rule: dispatcher reassignment (per truck) ------------------------
  if (changed("assigned_shovel")) {
    const from = str(prevOf("assigned_shovel"));
    const to = str(newOf("assigned_shovel"));
    // Routine shortest-queue choices happen every cycle; log only reroutes away from a shovel
    // that is down, which is what an outage looks like to the haul fleet.
    const fromState = from ? str(allThings[from]?.features?.state?.properties.value) : undefined;
    if (from && to && from !== to && fromState === "down" && cooled(`${thingId}:reroute`, 30000)) {
      const fromName = displayName(allThings[from], from);
      const toName = displayName(allThings[to], to);
      events.push(mk(`${name} rerouted: ${fromName} -> ${toName}`, "info"));
    }
  }

  // --- Rule: throughput-type change (crusher/mill/kpi twins) ------------
  // Throughput swings matter at the SAG mill; crusher and conveyors follow every truck dump.
  for (const f of ["throughput_tph"]) {
    if (thingId === "kz.kyzyltas.mine:mill-sag-01" && changed(f)) {
      const from = num(prevOf(f));
      const to = num(newOf(f));
      if (from && to && from > 0) {
        const pct = ((to - from) / from) * 100;
        if (Math.abs(pct) >= 5 && cooled(`${thingId}:${f}`, 15000)) {
          const sign = pct > 0 ? "+" : "";
          events.push(
            mk(`${name} ${f.replace(/_/g, " ")} ${from.toFixed(0)} -> ${to.toFixed(0)} t/h (${sign}${pct.toFixed(0)}%)`, pct < 0 ? "warning" : "info")
          );
        }
      }
    }
  }

  // --- Rule: maintenance / health ---------------------------------------
  if (changed("health_pct")) {
    const from = num(prevOf("health_pct"));
    const to = num(newOf("health_pct"));
    if (from !== undefined && to !== undefined && ((from >= 50 && to < 50) || (from >= 25 && to < 25)) &&
        cooled(`${thingId}:health`, 600000)) {
      events.push(mk(`${name} health ${from.toFixed(0)}% -> ${to.toFixed(0)}% - condition degrading`, "warning"));
    }
  }
  // Repairs are reported by the engine itself ("returned to service", "planned repair"),
  // so next_pm_due_h -- an estimate from a noisy condition signal -- is not logged here.

  // --- Rule: crusher/mill availability -----------------------------------
  if (changed("availability")) {
    const from = num(prevOf("availability"));
    const to = num(newOf("availability"));
    if (from !== undefined && to !== undefined && to < from) {
      events.push(mk(`${name} availability ${(from * 100).toFixed(0)}% -> ${(to * 100).toFixed(0)}%`, "warning"));
    }
  }

  return events;

  function mk(text: string, severity: EventLogEntry["severity"]): EventLogEntry {
    return { id: nextId(), t: Date.now(), text, severity };
  }
}
