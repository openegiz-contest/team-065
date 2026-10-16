import { useEffect, useMemo, useState } from "react";
import { useMineStore } from "../store/useMineStore";
import { featureNumber, featureString, shovelColor, TRUCK_STATE_LEGEND } from "../lib/selectors";
import { PIT, STEP, SX, SITE, ROADS, SHOVEL_FACES, facePosition, rampCenterline, WASTE_DUMP } from "../three/world";
import { truckRuntime } from "../three/Equipment";

// Top-down map of the same schematic layout the 3D view uses: bench
// contours, both ramps, surface roads, plant, waste dump, shovels and live
// truck positions (read from the 3D view's smoothed truck state).

const NS = "kz.kyzyltas.mine:";
const VB = { x: -500, y: -400, w: 1290, h: 700 };

function pts(list: { x: number; z: number }[]): string {
  return list.map((p) => `${p.x.toFixed(0)},${p.z.toFixed(0)}`).join(" ");
}

export function Minimap({ onSelect }: { onSelect: (id: string) => void }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((t) => t + 1), 300);
    return () => clearInterval(id);
  }, []);
  const things = useMineStore((s) => s.things);
  const mainClosed = featureNumber(things[NS + "road-ramp-ore-up"], "closed", 0) === 1;

  const statics = useMemo(
    () => ({
      contours: Array.from({ length: PIT.benches + 1 }, (_, b) => PIT.rTop - b * STEP),
      main: pts(rampCenterline("main")),
      alt: pts(rampCenterline("alt")),
      roads: [ROADS.mainTopToCrusher, ROADS.altTopToDump, ROADS.rimRoad, ROADS.toWorkshop].map(pts),
      shovels: SHOVEL_FACES.map((f) => ({ f, p: facePosition(f) }))
    }),
    []
  );

  const trucks = Array.from(truckRuntime.entries());

  return (
    <section className="minimap" aria-label="Minimap: top-down view of the pit, roads, plant and live equipment">
      <svg viewBox={`${VB.x} ${VB.y} ${VB.w} ${VB.h}`} role="img" aria-label="Top-down schematic with live truck positions">
        <rect x={VB.x} y={VB.y} width={VB.w} height={VB.h} fill="#c9c3a4" />
        {statics.contours.map((r, i) => (
          <ellipse key={i} cx={0} cy={0} rx={r * SX} ry={r} fill={i === 0 ? "#a8977b" : "none"} stroke="#6f5f4a" strokeWidth={i === 0 ? 4 : 2} opacity={0.9} />
        ))}
        {statics.roads.map((d, i) => (
          <polyline key={i} points={d} fill="none" stroke="#5c5852" strokeWidth={12} strokeLinejoin="round" />
        ))}
        <polyline points={statics.main} fill="none" stroke={mainClosed ? "#e5383b" : "#5c5852"} strokeWidth={14} strokeDasharray={mainClosed ? "24 14" : undefined} />
        <polyline points={statics.alt} fill="none" stroke="#5c5852" strokeWidth={12} />
        <circle cx={SITE.wasteDump.x} cy={SITE.wasteDump.z} r={WASTE_DUMP.rBottom} fill="#9a8f80" stroke="#6f665a" strokeWidth={3} />
        <ellipse cx={SITE.tailings.x} cy={SITE.tailings.z} rx={100} ry={80} fill="#a9bcc0" stroke="#7d8f93" strokeWidth={3} />
        {[SITE.crusher, SITE.hgPile, SITE.crushedPile, SITE.sag, SITE.ball1, SITE.flotation, SITE.substation, SITE.workshop].map((p, i) => (
          <rect key={i} x={p.x - 16} y={p.z - 16} width={32} height={32} fill="#6e7781" stroke="#30363d" strokeWidth={3} />
        ))}
        <text x={SITE.crusher.x - 30} y={SITE.crusher.z - 34} className="mm-label">Crusher</text>
        <text x={SITE.sag.x - 10} y={SITE.sag.z - 34} className="mm-label">Plant</text>
        <text x={SITE.wasteDump.x - 80} y={SITE.wasteDump.z + 12} className="mm-label">Waste dump</text>
        <text x={SITE.tailings.x - 60} y={SITE.tailings.z + 12} className="mm-label">Tailings</text>
        <text x={-50} y={PIT.rTop + 70} className="mm-label">Pit</text>
        {statics.shovels.map(({ f, p }) => {
          const st = featureString(things[NS + f.key], "state", "");
          return (
            <g key={f.key} onClick={() => onSelect(NS + f.key)} style={{ cursor: "pointer" }}>
              <rect x={p.x - 14} y={p.z - 14} width={28} height={28} fill={shovelColor(st)} stroke="#111" strokeWidth={4} />
              <text x={p.x + 20} y={p.z + 14} className="mm-label mm-strong">
                {f.short}
              </text>
            </g>
          );
        })}
        {trucks.map(([id, rt]) => (
          <circle key={id} cx={rt.pos.x} cy={rt.pos.z} r={11} fill={rt.color} stroke="#111" strokeWidth={3} />
        ))}
      </svg>
      <ul className="mm-legend" aria-label="Truck colour legend">
        {TRUCK_STATE_LEGEND.map((l) => (
          <li key={l.key}>
            <span className="legend-dot" style={{ background: l.color }} aria-hidden="true" />
            {l.label}
          </li>
        ))}
      </ul>
    </section>
  );
}

