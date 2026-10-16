import { useMemo } from "react";
import { useMineStore } from "../store/useMineStore";
import type { DittoThing } from "../types";

interface TwinModelProps {
  onSelect: (thingId: string) => void;
  onClose: () => void;
}

interface Node {
  thing: DittoThing;
  children: Node[];
}

function parentOf(t: DittoThing): string {
  const p = t.attributes?._parents;
  return typeof p === "string" ? p : "";
}

/** Short live status for a twin row: its state feature, if it has one. */
function status(t: DittoThing): string {
  const v = t.features?.state?.properties.value;
  return typeof v === "string" ? v : "";
}

function statusClass(s: string): string {
  if (s === "down" || s === "failed") return "tm-status bad";
  if (s.startsWith("queued") || s === "starved" || s === "idle") return "tm-status warn";
  return s ? "tm-status good" : "tm-status";
}

/**
 * The twin model as stored in Ditto: every instance twin under its parent
 * (attributes._parents), and every type twin with its instance count.
 */
export function TwinModel({ onSelect, onClose }: TwinModelProps) {
  const things = useMineStore((s) => s.things);

  const { roots, types, instanceCount } = useMemo(() => {
    const all = Object.values(things);
    const instances = all.filter((t) => t.attributes?._isType !== true);
    const typeTwins = all.filter((t) => t.attributes?._isType === true);
    const byId = new Map<string, Node>();
    for (const t of instances) byId.set(t.thingId, { thing: t, children: [] });
    const rootNodes: Node[] = [];
    for (const node of byId.values()) {
      const parent = byId.get(parentOf(node.thing));
      if (parent) parent.children.push(node);
      else rootNodes.push(node);
    }
    const byName = (a: Node, b: Node) => a.thing.thingId.localeCompare(b.thing.thingId);
    const sortTree = (nodes: Node[]) => {
      nodes.sort(byName);
      nodes.forEach((n) => sortTree(n.children));
    };
    sortTree(rootNodes);
    const counts = new Map<string, number>();
    for (const t of instances) {
      const c = t.attributes?.class ?? "";
      counts.set(c, (counts.get(c) ?? 0) + 1);
    }
    const typeRows = typeTwins
      .map((t) => ({
        thing: t,
        className: t.attributes?.class ?? t.thingId.split(":").pop() ?? "",
      }))
      .map((r) => ({ ...r, count: counts.get(r.className) ?? 0 }))
      .sort((a, b) => a.className.localeCompare(b.className));
    return { roots: rootNodes, types: typeRows, instanceCount: instances.length };
  }, [things]);

  const renderNode = (n: Node, depth: number) => {
    const t = n.thing;
    const s = status(t);
    return (
      <li key={t.thingId}>
        <button type="button" className="tm-row" style={{ paddingLeft: 8 + depth * 16 }} onClick={() => onSelect(t.thingId)}>
          <span className="tm-name">{t.attributes?.name ?? t.thingId}</span>
          <span className="tm-class">{t.attributes?.class ?? ""}</span>
          <code className="tm-id">{t.thingId.split(":").pop()}</code>
          <span className={statusClass(s)}>{s}</span>
          {n.children.length > 0 && <span className="tm-count">{n.children.length} children</span>}
        </button>
        {n.children.length > 0 && <ul>{n.children.map((c) => renderNode(c, depth + 1))}</ul>}
      </li>
    );
  };

  return (
    <section className="twin-model" aria-label="Twin model">
      <div className="tm-header">
        <h2>Twin model</h2>
        <p>
          {instanceCount} instance twins and {types.length} type twins in Eclipse Ditto, namespace{" "}
          <code>kz.kyzyltas.mine</code>. Hierarchy from each twin's <code>_parents</code> attribute; status is the live{" "}
          <code>state</code> feature. Click a twin for all its live features.
        </p>
        <button type="button" className="inspector-close" onClick={onClose} aria-label="Close twin model">
          ✕
        </button>
      </div>
      <div className="tm-body">
        <div className="tm-tree">
          <h3>Hierarchy</h3>
          <ul>{roots.map((r) => renderNode(r, 0))}</ul>
        </div>
        <div className="tm-types">
          <h3>Types</h3>
          <table>
            <thead>
              <tr>
                <th scope="col">Type</th>
                <th scope="col">Instances</th>
              </tr>
            </thead>
            <tbody>
              {types.map((r) => (
                <tr key={r.thing.thingId}>
                  <td title={r.thing.attributes?.description ?? ""}>{r.thing.attributes?.name ?? r.className}</td>
                  <td>{r.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
