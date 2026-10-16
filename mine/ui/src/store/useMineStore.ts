import { create } from "zustand";
import type { ConnectionStatus, DittoThing, EventLogEntry } from "../types";
import { SCENARIO_THING_ID, KPI_THING_ID } from "../types";
import { fetchCatalogue, patchScenario, subscribeLive } from "../lib/ditto";
import { evaluateRules } from "../lib/eventLog";
import { toFeaturePatch, type ScenarioFieldPatch } from "../lib/scenarios";

interface MineState {
  things: Record<string, DittoThing>;
  loaded: boolean;
  loadError: string | null;
  catalogueCount: number;
  connectionStatus: ConnectionStatus;
  eventLog: EventLogEntry[];
  lastUpdateAt: number;
  /** Mine clock: last reported sim_time_h and the wall time it arrived. */
  simTimeH: number | null;
  simTimeAt: number;
  speedup: number;
  /** Rendering. */
  performanceMode: boolean;
  autoPerformance: boolean;
  fps: number;

  init: () => void;
  triggerScenario: (patch: ScenarioFieldPatch) => Promise<void>;
  resetScenario: (patch: ScenarioFieldPatch) => Promise<void>;
  setPerformanceMode: (v: boolean, auto?: boolean) => void;
  setFps: (fps: number) => void;
}

const MAX_LOG_ENTRIES = 300;
/** SSE delivers ~25 messages/s; React state is refreshed at most this often. */
const FLUSH_MS = 250;

type DiffFeatures = Record<string, { properties: { value: number | string } }>;

let initialised = false;

/** Extrapolated mine time in hours (advances smoothly between engine reports). */
export function mineTimeNow(s: Pick<MineState, "simTimeH" | "simTimeAt" | "speedup">): number | null {
  if (s.simTimeH === null) return null;
  const elapsedRealS = Math.min(30, (Date.now() - s.simTimeAt) / 1000);
  return s.simTimeH + (elapsedRealS * s.speedup) / 3600;
}

export const useMineStore = create<MineState>((set, get) => ({
  things: {},
  loaded: false,
  loadError: null,
  catalogueCount: 0,
  connectionStatus: "connecting",
  eventLog: [],
  lastUpdateAt: 0,
  simTimeH: null,
  simTimeAt: 0,
  speedup: 60,
  performanceMode: false,
  autoPerformance: false,
  fps: 0,

  init: () => {
    if (initialised) return;
    initialised = true;

    // Latest view of every twin, updated synchronously per SSE message (so
    // the event-log diff rules see every transition) and flushed to React
    // state at most every FLUSH_MS.
    const latest: Record<string, DittoThing> = {};
    let pendingEvents: EventLogEntry[] = [];
    let dirty = false;
    let flushTimer: ReturnType<typeof setTimeout> | null = null;

    const flush = () => {
      flushTimer = null;
      if (!dirty) return;
      dirty = false;
      const patch: Partial<MineState> = { things: { ...latest }, lastUpdateAt: Date.now() };
      if (pendingEvents.length > 0) {
        patch.eventLog = [...pendingEvents.reverse(), ...get().eventLog].slice(0, MAX_LOG_ENTRIES);
        pendingEvents = [];
      }
      set(patch);
    };
    const scheduleFlush = () => {
      dirty = true;
      if (!flushTimer) flushTimer = setTimeout(flush, FLUSH_MS);
    };

    fetchCatalogue(200, (count) => set({ catalogueCount: count }))
      .then((items) => {
        for (const t of items) {
          const live = latest[t.thingId];
          // Keep any live features that already arrived over SSE.
          latest[t.thingId] = live ? { ...t, features: { ...(t.features ?? {}), ...(live.features ?? {}) } } : t;
        }
        const kpi = latest[KPI_THING_ID];
        const st = kpi?.features?.sim_time_h?.properties.value;
        if (typeof st === "number" && get().simTimeH === null) set({ simTimeH: st, simTimeAt: Date.now() });
        set({ loaded: true });
        scheduleFlush();
      })
      .catch((err) => {
        set({ loadError: err instanceof Error ? err.message : String(err) });
      });

    subscribeLive(
      (msg) => {
        const thingId = msg.thingId;
        if (!thingId || !msg.features) return;
        const existing = latest[thingId];
        const prevFeatures = existing?.features as DiffFeatures | undefined;
        const merged: DittoThing = existing
          ? { ...existing, features: { ...(existing.features ?? {}), ...msg.features } }
          : { thingId, features: { ...msg.features } };
        latest[thingId] = merged;

        if (thingId === KPI_THING_ID) {
          const st = msg.features.sim_time_h?.properties.value;
          const sp = msg.features.speedup?.properties.value;
          const upd: Partial<MineState> = {};
          if (typeof st === "number") {
            upd.simTimeH = st;
            upd.simTimeAt = Date.now();
          }
          if (typeof sp === "number" && sp > 0) upd.speedup = sp;
          if (Object.keys(upd).length) set(upd);
        }

        const events = evaluateRules(
          { thingId, thing: merged, prevFeatures: prevFeatures as never, newFeatures: msg.features as never },
          latest
        );
        if (events.length > 0) {
          const t = mineTimeNow(get());
          for (const e of events) e.simTimeH = t ?? undefined;
          pendingEvents.push(...events);
        }
        scheduleFlush();
      },
      (status) => set({ connectionStatus: status })
    );
  },

  triggerScenario: async (patch) => {
    const fullPatch = { ...patch, run_id: `run-${Date.now()}` };
    await patchScenario(SCENARIO_THING_ID, toFeaturePatch(fullPatch));
  },

  resetScenario: async (patch) => {
    const fullPatch = { ...patch, run_id: `run-${Date.now()}` };
    await patchScenario(SCENARIO_THING_ID, toFeaturePatch(fullPatch));
  },

  setPerformanceMode: (v, auto = false) => set({ performanceMode: v, autoPerformance: v && auto }),
  setFps: (fps) => set({ fps })
}));
