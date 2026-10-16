import { useMineStore } from "../store/useMineStore";
import { formatMineStamp } from "./Header";

const SEVERITY_LABEL = { critical: "Critical", warning: "Warning", info: "Info" } as const;

/**
 * Causal event log, newest first. Lines come from the engine's own causal
 * events (kpi.last_event / event_seq) plus UI-side diff rules on live twin
 * transitions (lib/eventLog.ts).
 */
export function EventLog() {
  const events = useMineStore((s) => s.eventLog);

  return (
    <section className="event-log" aria-labelledby="event-heading">
      <div className="event-head">
        <h2 id="event-heading">Event log</h2>
        <span className="event-count">{events.length} events · newest first</span>
      </div>
      {events.length === 0 && (
        <p className="empty-state">
          Waiting for events - failures, reroutes, queue build-ups, work orders and scenario effects appear here as the
          twins report them.
        </p>
      )}
      <ol className="event-list" aria-live="polite">
        {events.map((e) => (
          <li key={e.id} className={`event-item sev-${e.severity}`}>
            <span className="event-sev">{SEVERITY_LABEL[e.severity]}</span>
            <span className="event-time" title={new Date(e.t).toLocaleTimeString(undefined, { hour12: false })}>
              {formatMineStamp(e.simTimeH) || new Date(e.t).toLocaleTimeString(undefined, { hour12: false })}
            </span>
            <span className="event-text">{e.text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
