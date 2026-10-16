import { useMemo, useRef } from "react";
import * as THREE from "three";
import { useFrame } from "@react-three/fiber";
import { useMineStore } from "../store/useMineStore";
import { featureNumber, featureString, getKpiThing, getScenarioThing } from "../lib/selectors";
import { SHOVEL_FACES, DRILL_FACES, facePosition, rampCenterline, SITE } from "./world";
import { ribbon } from "./Terrain";

// Scenario-driven 3D highlights. Everything here is keyed off live twin
// features (shovel `state`, road `closed`, radar `tarp_level`) or the
// scenario twin's `active_scenario`, so what is highlighted is what the
// engine reports.

const NS = "kz.kyzyltas.mine:";

/** Pulsing ground ring + vertical beacon marking an affected asset. */
export function PulseRing({ position, color, radius = 22, beacon = true }: { position: THREE.Vector3; color: string; radius?: number; beacon?: boolean }) {
  const ring = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (!ring.current) return;
    const k = (clock.getElapsedTime() * 0.8) % 1;
    ring.current.scale.setScalar(0.6 + k * 0.8);
    (ring.current.material as THREE.MeshBasicMaterial).opacity = 0.85 * (1 - k);
  });
  return (
    <group position={position}>
      <mesh ref={ring} position={[0, 1.2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[radius * 0.82, radius, 32]} />
        <meshBasicMaterial color={color} transparent opacity={0.8} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {beacon && (
        <mesh position={[0, 30, 0]}>
          <cylinderGeometry args={[1.4, 1.4, 60, 6, 1, true]} />
          <meshBasicMaterial color={color} transparent opacity={0.45} depthWrite={false} />
        </mesh>
      )}
    </group>
  );
}

export function ScenarioHighlights() {
  const things = useMineStore((s) => s.things);
  const active = featureString(getScenarioThing(things), "active_scenario", "none");
  const mainClosed = featureNumber(things[NS + "road-ramp-ore-up"], "closed", 0) === 1;

  const downShovels = SHOVEL_FACES.filter((f) => featureString(things[NS + f.key], "state") === "down");
  const blocked = SHOVEL_FACES.filter((f) => featureString(things[NS + f.key], "state") === "blocked");
  const downDrills = DRILL_FACES.filter((f) => featureString(things[NS + f.key], "state") === "down");
  const radarRed = featureString(things[NS + "slope-radar-01"], "tarp_level", "green") !== "green";

  const amber = "#f0b429";
  const amberAt: THREE.Vector3[] = [];
  // Rings follow twin data: a plant unit or the substation running away from its baseline,
  // trucks in the workshop, an extreme-cold reading at the weather station.
  const kpi = getKpiThing(things);
  if (Math.abs(featureNumber(kpi, "delta_tph_pct", 0)) > 3) amberAt.push(SITE.sag);
  if (Math.abs(featureNumber(kpi, "delta_energy_kwh_h_pct", 0)) > 3) amberAt.push(SITE.substation);
  const trucks = Object.values(things).filter((t) => t.attributes?.class === "HaulTruck" && t.attributes?._isType !== true);
  if (trucks.some((t) => featureNumber(t, "parked", 0) === 1 || featureNumber(t, "work_order_open", 0) === 1)) amberAt.push(SITE.workshop);
  const weather = Object.values(things).find((t) => t.attributes?.class === "WeatherStation" && t.attributes?._isType !== true);
  if (featureNumber(weather, "temp_c", 15) <= -10) amberAt.push(SITE.weather);
  if (active === "price_drop") amberAt.push(SITE.lowGradePile); // price is not a physical twin state

  return (
    <group>
      {downShovels.map((f) => (
        <PulseRing key={f.key} position={facePosition(f)} color="#ff3b30" radius={26} />
      ))}
      {downDrills.map((f) => (
        <PulseRing key={f.key} position={facePosition(f)} color="#ff3b30" radius={16} />
      ))}
      {blocked.map((f) => (
        <FumeCloud key={f.key} position={facePosition(f)} />
      ))}
      {amberAt.map((p, i) => (
        <PulseRing key={i} position={p} color={amber} radius={34} beacon={false} />
      ))}
      {(mainClosed || radarRed) && <PulseRing position={SITE.radarEast} color="#ff3b30" radius={20} />}
      {mainClosed && <RampOverlay color="#ff3b30" opacity={0.6} />}
      {active === "road_thaw" && <RampOverlay color="#5b3b1c" opacity={0.45} both />}
      {active === "trolley_assist" && <TrolleyLine />}
      {active === "blast_intensify" && <BlastPulse />}
    </group>
  );
}

function RampOverlay({ color, opacity, both = false }: { color: string; opacity: number; both?: boolean }) {
  const geos = useMemo(() => {
    const out = [ribbon(rampCenterline("main"), 17, 0.8)];
    if (both) out.push(ribbon(rampCenterline("alt"), 15, 0.8));
    return out;
  }, [both]);
  return (
    <group>
      {geos.map((g, i) => (
        <mesh key={i} geometry={g}>
          <meshBasicMaterial color={color} transparent opacity={opacity} depthWrite={false} polygonOffset polygonOffsetFactor={-4} polygonOffsetUnits={-4} />
        </mesh>
      ))}
    </group>
  );
}

/** Overhead trolley line on the upper main ramp (posts + energised cable). */
function TrolleyLine() {
  const { posts, cable } = useMemo(() => {
    const pts = rampCenterline("main", 0, 0.42);
    const posts: THREE.Vector3[] = [];
    const cablePts: number[] = [];
    for (let i = 0; i < pts.length; i += 4) {
      const p = pts[i];
      const q = pts[Math.min(pts.length - 1, i + 1)];
      const dx = q.x - p.x;
      const dz = q.z - p.z;
      const len = Math.hypot(dx, dz) || 1;
      posts.push(new THREE.Vector3(p.x - (dz / len) * 11, p.y, p.z + (dx / len) * 11));
    }
    for (let i = 0; i < posts.length - 1; i++) {
      cablePts.push(posts[i].x, posts[i].y + 14, posts[i].z, posts[i + 1].x, posts[i + 1].y + 14, posts[i + 1].z);
    }
    const cable = new THREE.BufferGeometry();
    cable.setAttribute("position", new THREE.Float32BufferAttribute(cablePts, 3));
    return { posts, cable };
  }, []);
  return (
    <group>
      {posts.map((p, i) => (
        <mesh key={i} position={[p.x, p.y + 7, p.z]}>
          <boxGeometry args={[1.2, 14, 1.2]} />
          <meshBasicMaterial color="#d0d7de" />
        </mesh>
      ))}
      <lineSegments geometry={cable}>
        <lineBasicMaterial color="#ffb000" />
      </lineSegments>
    </group>
  );
}

function FumeCloud({ position }: { position: THREE.Vector3 }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (ref.current) ref.current.scale.setScalar(1 + Math.sin(clock.getElapsedTime() * 1.3) * 0.08);
  });
  return (
    <mesh ref={ref} position={[position.x, position.y + 14, position.z]}>
      <sphereGeometry args={[42, 14, 10]} />
      <meshBasicMaterial color="#e2d27a" transparent opacity={0.28} depthWrite={false} />
    </mesh>
  );
}

function BlastPulse() {
  const ref = useRef<THREE.Mesh>(null);
  const pos = useMemo(() => facePosition(DRILL_FACES[0]), []);
  useFrame(({ clock }) => {
    if (!ref.current) return;
    const k = (clock.getElapsedTime() * 0.35) % 1;
    ref.current.scale.setScalar(4 + k * 40);
    (ref.current.material as THREE.MeshBasicMaterial).opacity = 0.7 * (1 - k);
  });
  return (
    <mesh ref={ref} position={[pos.x, pos.y + 2, pos.z]} rotation={[-Math.PI / 2, 0, 0]}>
      <ringGeometry args={[0.8, 1.1, 32]} />
      <meshBasicMaterial color="#ff9f1a" transparent opacity={0.7} depthWrite={false} side={THREE.DoubleSide} />
    </mesh>
  );
}

/**
 * Haul-road dust along both ramps. Particle density follows the engine's AP-42 haul-road PM10
 * emission (kpi twin feature road_pm10_kg_h): ~120-150 kg/h in normal running with road
 * watering, roughly double when watering stops below 0 °C.
 */
export function HaulDust() {
  const pm10 = useMineStore((s) => featureNumber(getKpiThing(s.things), "road_pm10_kg_h", 0));
  const performanceMode = useMineStore((s) => s.performanceMode);
  const MAX = 900;
  const geom = useMemo(() => {
    const pts = [...rampCenterline("main"), ...rampCenterline("alt")];
    const pos = new Float32Array(MAX * 3);
    const seed = new Float32Array(MAX);
    for (let i = 0; i < MAX; i++) {
      const p = pts[Math.floor((i / MAX) * pts.length)] ?? pts[0];
      pos[i * 3] = p.x + (Math.random() - 0.5) * 16;
      pos[i * 3 + 1] = p.y + 2 + Math.random() * 10;
      pos[i * 3 + 2] = p.z + (Math.random() - 0.5) * 16;
      seed[i] = Math.random();
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    return { g, base: pos.slice(), seed };
  }, []);
  const mat = useRef<THREE.PointsMaterial>(null);
  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();
    const pos = geom.g.attributes.position.array as Float32Array;
    for (let i = 0; i < MAX; i++) {
      pos[i * 3 + 1] = geom.base[i * 3 + 1] + ((t * 2 + geom.seed[i] * 12) % 12);
    }
    geom.g.attributes.position.needsUpdate = true;
  });
  // Show a share of the particles proportional to the emission (300 kg/h fills the pool).
  // Performance mode (software rendering) keeps a third of the particles rather than none.
  const count = Math.round(Math.min(1, pm10 / 300) * MAX * (performanceMode ? 0.35 : 1));
  geom.g.setDrawRange(0, count);
  if (count === 0) return null;
  return (
    <points geometry={geom.g}>
      <pointsMaterial ref={mat} color="#c8b593" size={6} sizeAttenuation transparent opacity={0.35} depthWrite={false} />
    </points>
  );
}


/**
 * Falling snow across the site while the weather-station twin reports freezing air; denser in a
 * blizzard (wind above 8 m/s). Fewer particles in performance mode.
 */
export function Snow() {
  const weather = useMineStore((s) =>
    Object.values(s.things).find((t) => t.attributes?.class === "WeatherStation" && t.attributes?._isType !== true)
  );
  const performanceMode = useMineStore((s) => s.performanceMode);
  const temp = featureNumber(weather, "temp_c", 15);
  const wind = featureNumber(weather, "wind_ms", 2);
  const MAX = 1500;
  const geom = useMemo(() => {
    const pos = new Float32Array(MAX * 3);
    for (let i = 0; i < MAX; i++) {
      pos[i * 3] = (Math.random() - 0.5) * 2200 + 150;
      pos[i * 3 + 1] = Math.random() * 400 - 150;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 1600;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    return g;
  }, []);
  useFrame((_, dt) => {
    const pos = geom.attributes.position.array as Float32Array;
    const drift = Math.min(wind, 15) * 3 * dt;
    for (let i = 0; i < MAX; i++) {
      pos[i * 3 + 1] -= 18 * dt;
      pos[i * 3] += drift;
      if (pos[i * 3 + 1] < -150) pos[i * 3 + 1] += 400;
      if (pos[i * 3] > 1250) pos[i * 3] -= 2200;
    }
    geom.attributes.position.needsUpdate = true;
  });
  if (temp > 0) return null;
  const share = (wind > 8 ? 1 : 0.5) * (performanceMode ? 0.35 : 1);
  geom.setDrawRange(0, Math.round(MAX * share));
  return (
    <points geometry={geom}>
      <pointsMaterial color="#ffffff" size={3} sizeAttenuation transparent opacity={0.8} depthWrite={false} />
    </points>
  );
}
