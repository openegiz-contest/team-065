import { useState } from "react";
import { useMineStore } from "../store/useMineStore";
import { getScenarioThing, featureString } from "../lib/selectors";
import { SCENARIOS, SCENARIO_GROUPS, buildResetPatch } from "../lib/scenarios";
import { CustomScenario } from "./CustomScenario";

/**
 * What-if scenario controls. Each button PATCHes the
 * scenario twin with its field mapping from lib/scenarios.ts; Undo PATCHes
 * every field back to SCENARIO_DEFAULTS.
 */
export function ScenarioPanel() {
  const scenarioThing = useMineStore((s) => getScenarioThing(s.things));
  const things = useMineStore((s) => s.things);
  const triggerScenario = useMineStore((s) => s.triggerScenario);
  const resetScenario = useMineStore((s) => s.resetScenario);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeId = featureString(scenarioThing, "active_scenario", "none");
  const activeDef = SCENARIOS.find((s) => s.id === activeId);

  async function handleTrigger(id: string) {
    const def = SCENARIOS.find((s) => s.id === id);
    if (!def) return;
    setPendingId(id);
    setError(null);
    try {
      // Start from the defaults so switching scenarios never leaves a previous one's field behind.
      await triggerScenario({ ...buildResetPatch(), ...def.buildPatch(things), active_scenario: def.id });
    } catch (err) {
      setError(`Could not apply "${def.label}": ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setPendingId(null);
    }
  }

  async function handleUndo() {
    setPendingId("__undo__");
    setError(null);
    try {
      await resetScenario(buildResetPatch());
    } catch (err) {
      setError(`Could not reset scenario: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setPendingId(null);
    }
  }

  return (
    <section className="scenario-panel" aria-labelledby="scenario-heading">
      <div className="scenario-head">
        <h2 id="scenario-heading">What-if scenarios</h2>
        <p className="scenario-status" role="status">
          {activeDef ? (
            <>
              Active: <strong>{activeDef.label}</strong>
            </>
          ) : activeId === "custom" ? (
            <>
              Active: <strong>Custom what-if</strong>
            </>
          ) : activeId !== "none" ? (
            <>
              Active: <strong>{activeId}</strong>
            </>
          ) : (
            "Baseline - no scenario active"
          )}
        </p>
        <button
          type="button"
          className="undo-btn"
          disabled={pendingId !== null || activeId === "none"}
          onClick={handleUndo}
        >
          {pendingId === "__undo__" ? "Resetting..." : "↺ Undo - back to baseline"}
        </button>
        {error && (
          <p className="scenario-error" role="alert">
            {error}
          </p>
        )}
      </div>

      <div className="scenario-scroll">
        <CustomScenario disabled={pendingId !== null} />
        {SCENARIO_GROUPS.map((g) => (
          <div key={g.id} className="scenario-group" role="group" aria-label={g.title}>
            <h3>{g.title}</h3>
            {SCENARIOS.filter((s) => s.group === g.id).map((def) => {
              const isActive = activeId === def.id;
              return (
                <button
                  key={def.id}
                  type="button"
                  className={`scenario-btn${isActive ? " is-active" : ""}`}
                  disabled={pendingId !== null}
                  aria-pressed={isActive}
                  aria-label={`${def.label}: ${def.short}`}
                  aria-describedby={`desc-${def.id}`}
                  onClick={() => handleTrigger(def.id)}
                  title={def.description}
                >
                  <span className="scenario-btn-label">{pendingId === def.id ? "Applying..." : def.label}</span>
                  <span className="scenario-btn-short">{def.short}</span>
                  <span id={`desc-${def.id}`} className="visually-hidden">
                    {def.description}
                  </span>
                </button>
              );
            })}
          </div>
        ))}
        <p className="scenario-hint">
          Each scenario runs against a shadow baseline on the same mine clock; the right-hand panel compares both.
          Undo restores every scenario-control field to its default.
        </p>
      </div>
    </section>
  );
}
