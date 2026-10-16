import { useMineStore } from "../store/useMineStore";
import { formatNumber } from "../lib/kpi";

interface InspectorProps {
  selectedId: string;
  onClear: () => void;
}

function pretty(name: string): string {
  return name.replace(/_/g, " ").replace(/\bpct\b/, "%").replace(/\btph\b/, "t/h");
}

/** Live twin data for the asset clicked in the 3D view (or its label) - real DOM text. */
export function Inspector({ selectedId, onClear }: InspectorProps) {
  const thing = useMineStore((s) => (selectedId ? s.things[selectedId] : undefined));
  if (!selectedId || !thing) return null;
  const features = Object.entries(thing.features ?? {});

  return (
    <section className="inspector" aria-label={`Live twin data: ${thing.attributes?.name ?? thing.thingId}`}>
      <div className="inspector-header">
        <h2>{thing.attributes?.name ?? thing.thingId}</h2>
        <button type="button" className="inspector-close" onClick={onClear} aria-label="Close inspector">
          ✕
        </button>
      </div>
      <p className="inspector-id">
        <code>{thing.thingId}</code>
        {thing.attributes?.class ? ` · ${thing.attributes.class}` : ""}
      </p>
      {thing.attributes?.description && <p className="inspector-desc">{thing.attributes.description}</p>}
      <dl className="inspector-features inspector-relations" aria-label="Relations">
        {typeof thing.attributes?._parents === "string" && (
          <div className="inspector-row">
            <dt>part of</dt>
            <dd>{thing.attributes._parents.split(":").pop()}</dd>
          </div>
        )}
        {thing.definition && (
          <div className="inspector-row">
            <dt>type</dt>
            <dd>{thing.definition.split(":").slice(1).join(":")}</dd>
          </div>
        )}
        {typeof thing.attributes?.bench === "string" && (
          <div className="inspector-row">
            <dt>digs</dt>
            <dd>{thing.attributes.bench.split(":").pop()}</dd>
          </div>
        )}
        {Array.isArray(thing.attributes?.feeds) && (
          <div className="inspector-row">
            <dt>feeds</dt>
            <dd>{(thing.attributes.feeds as string[]).map((f) => f.split(":").pop()).join(", ")}</dd>
          </div>
        )}
      </dl>
      {features.length === 0 ? (
        <p className="empty-state">No live features received for this twin yet.</p>
      ) : (
        <dl className="inspector-features">
          {features.map(([name, f]) => (
            <div key={name} className="inspector-row">
              <dt>{pretty(name)}</dt>
              <dd>
                {typeof f.properties.value === "number" ? formatNumber(f.properties.value) : String(f.properties.value) || "-"}{" "}
                {f.properties.unit}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </section>
  );
}
