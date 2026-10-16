import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMineStore } from "../store/useMineStore";
import { listByClass, featureNumber, featureString, truckColor, shovelColor } from "../lib/selectors";
import {
  SHOVEL_FACES,
  DRILL_FACES,
  facePosition,
  faceByKey,
  haulPath,
  samplePolyline,
  parkingSlot,
  type FaceDef,
  type RampId
} from "./world";
import type { DittoThing } from "../types";

// Trucks follow the schematic haul network (world.ts): the engine publishes
// each truck's haul-cycle phase (`state`), its progress through that phase
// (`route_progress_pct`), its `assigned_shovel` and `route` (ore|waste).
// Hauling = loaded trip shovel -> ramp -> crusher/dump; returning = the same
// path backwards in the other lane. Progress is extrapolated between ~1 Hz
// updates so trucks glide instead of jumping.

const MAX_TRUCKS = 24;

export interface TruckRuntime {
  phase: string;
  target: number; // last reported progress 0..1
  shown: number; // displayed progress 0..1
  rate: number; // progress per second, estimated
  lastAt: number;
  pos: THREE.Vector3;
  heading: number;
  color: string;
}

/** Live smoothed truck positions, shared with the minimap. */
export const truckRuntime = new Map<string, TruckRuntime>();

function hash01(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

function buildTruckGeometry(): THREE.BufferGeometry {
  const parts: THREE.BufferGeometry[] = [];
  const add = (w: number, h: number, l: number, x: number, y: number, z: number, shade: number) => {
    const g = new THREE.BoxGeometry(w, h, l);
    g.translate(x, y, z);
    const n = g.getAttribute("position").count;
    const c = new Float32Array(n * 3).fill(shade);
    g.setAttribute("color", new THREE.BufferAttribute(c, 3));
    parts.push(g);
  };
  add(8, 2.6, 15, 0, 2.6, 0, 0.32); // chassis / wheels band (dark)
  add(8.6, 4, 10, 0, 6, -2.4, 1.0); // dump body (state colour)
  add(7.2, 1.2, 3.6, 0, 8.6, 5, 1.0); // canopy over the cab
  add(3.6, 3, 3.6, -2, 6, 5, 0.75); // cab
  const merged = mergeGeometries(parts)!;
  parts.forEach((p) => p.dispose());
  return merged;
}

export function Equipment({ onSelect }: { onSelect: (thingId: string) => void }) {
  const truckMesh = useRef<THREE.InstancedMesh>(null);
  const loadMesh = useRef<THREE.InstancedMesh>(null);
  const beaconMesh = useRef<THREE.InstancedMesh>(null);
  const beaconGeo = useMemo(() => new THREE.CylinderGeometry(1.6, 1.6, 50, 6, 1, true).translate(0, 32, 0), []);
  const truckGeo = useMemo(buildTruckGeometry, []);
  const loadGeo = useMemo(() => new THREE.BoxGeometry(7, 2.2, 8).translate(0, 8.6, -2.4), []);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const col = useMemo(() => new THREE.Color(), []);
  const tmp = useMemo(() => new THREE.Vector3(), []);
  const [truckIds, setTruckIds] = useState<string[]>([]);

  useEffect(() => {
    const recompute = () => {
      const ids = listByClass(useMineStore.getState().things, "HaulTruck").map((t) => t.thingId);
      setTruckIds((prev) => (prev.length === ids.length && prev.every((p, i) => p === ids[i]) ? prev : ids));
    };
    recompute();
    return useMineStore.subscribe(recompute);
  }, []);

  useFrame((_, delta) => {
    const mesh = truckMesh.current;
    const loads = loadMesh.current;
    const beacons = beaconMesh.current;
    if (!mesh || !loads || !beacons) return;
    const dt = Math.min(delta, 0.2);
    const things = useMineStore.getState().things;
    const mainClosed = featureNumber(things["kz.kyzyltas.mine:road-ramp-ore-up"], "closed", 0) === 1;
    const now = performance.now();
    let parkedIdx = 0;

    for (let i = 0; i < MAX_TRUCKS; i++) {
      const id = truckIds[i];
      const thing = id ? things[id] : undefined;
      if (!thing) {
        dummy.position.set(0, -5000, 0);
        dummy.scale.setScalar(0.0001);
        dummy.updateMatrix();
        mesh.setMatrixAt(i, dummy.matrix);
        loads.setMatrixAt(i, dummy.matrix);
        beacons.setMatrixAt(i, dummy.matrix);
        continue;
      }
      const rt = updateTruck(thing, now, dt, mainClosed, parkedIdx, tmp);
      if (featureNumber(thing, "parked", 0) === 1) parkedIdx++;

      dummy.position.copy(rt.pos);
      dummy.rotation.set(0, rt.heading, 0);
      dummy.scale.setScalar(1);
      dummy.updateMatrix();
      mesh.setMatrixAt(i, dummy.matrix);
      col.set(rt.color);
      mesh.setColorAt(i, col);

      if (rt.phase === "down") {
        beacons.setMatrixAt(i, dummy.matrix);
      } else {
        dummy.scale.setScalar(0.0001);
        dummy.updateMatrix();
        beacons.setMatrixAt(i, dummy.matrix);
        dummy.scale.setScalar(1);
        dummy.updateMatrix();
      }
      const payload = featureNumber(thing, "payload_t", 0);
      if (payload > 5 && rt.phase !== "dumping") {
        loads.setMatrixAt(i, dummy.matrix);
      } else {
        dummy.scale.setScalar(0.0001);
        dummy.updateMatrix();
        loads.setMatrixAt(i, dummy.matrix);
      }
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    loads.instanceMatrix.needsUpdate = true;
    beacons.instanceMatrix.needsUpdate = true;
  });

  function handleClick(e: ThreeEvent<MouseEvent>) {
    e.stopPropagation();
    if (e.instanceId !== undefined && truckIds[e.instanceId]) onSelect(truckIds[e.instanceId]);
  }

  return (
    <group>
      <instancedMesh
        ref={truckMesh}
        args={[truckGeo, undefined, MAX_TRUCKS]}
        onClick={handleClick}
        frustumCulled={false}
      >
        <meshLambertMaterial vertexColors />
      </instancedMesh>
      <instancedMesh ref={loadMesh} args={[loadGeo, undefined, MAX_TRUCKS]} frustumCulled={false} raycast={() => null}>
        <meshLambertMaterial color="#7a5a3a" />
      </instancedMesh>
      <instancedMesh ref={beaconMesh} args={[beaconGeo, undefined, MAX_TRUCKS]} frustumCulled={false} raycast={() => null}>
        <meshBasicMaterial color="#ff3b30" transparent opacity={0.55} depthWrite={false} />
      </instancedMesh>
      {SHOVEL_FACES.map((f) => (
        <Shovel key={f.key} face={f} onSelect={onSelect} />
      ))}
      {DRILL_FACES.map((f) => (
        <Drill key={f.key} face={f} onSelect={onSelect} />
      ))}
    </group>
  );
}

function updateTruck(
  thing: DittoThing,
  now: number,
  dt: number,
  mainClosed: boolean,
  parkedIdx: number,
  tmp: THREE.Vector3
): TruckRuntime {
  const id = thing.thingId;
  const phase = featureString(thing, "state", "hauling");
  const pct = THREE.MathUtils.clamp(featureNumber(thing, "route_progress_pct", 0) / 100, 0, 1);
  const parked = featureNumber(thing, "parked", 0) === 1;
  let rt = truckRuntime.get(id);
  if (!rt) {
    rt = { phase, target: pct, shown: pct, rate: 0, lastAt: now, pos: new THREE.Vector3(), heading: 0, color: "#888" };
    truckRuntime.set(id, rt);
  }
  // New report?
  if (phase !== rt.phase) {
    rt.phase = phase;
    rt.target = pct;
    rt.shown = pct;
    rt.rate = 0;
    rt.lastAt = now;
  } else if (pct !== rt.target) {
    const dts = (now - rt.lastAt) / 1000;
    if (pct > rt.target && dts > 0.05) rt.rate = THREE.MathUtils.lerp(rt.rate, (pct - rt.target) / dts, 0.5);
    rt.target = pct;
    rt.lastAt = now;
  }
  // Extrapolate a little past the last report, then ease toward it.
  rt.shown = Math.min(rt.shown + rt.rate * dt, rt.target + rt.rate * 1.2, 1);
  if (rt.shown < rt.target) rt.shown += (rt.target - rt.shown) * Math.min(1, dt * 3);

  const face = faceByKey(featureString(thing, "assigned_shovel", "")) ?? SHOVEL_FACES[hash01(id) < 0.5 ? 0 : 1];
  const route = featureString(thing, "route", face.material === "waste" ? "waste" : "ore");
  const dest = route === "waste" ? "dump" : "crusher";
  const rampId: RampId = route === "waste" || mainClosed ? "alt" : "main";
  const path = haulPath(face, rampId, dest);
  const h = hash01(id);
  let heading: number;
  const lane = 3.6;

  if (parked) {
    parkingSlot(parkedIdx, tmp);
    heading = Math.PI;
  } else if (phase === "hauling") {
    heading = samplePolyline(path, rt.shown, lane, tmp);
  } else if (phase === "returning") {
    heading = samplePolyline(path, 1 - rt.shown, -lane, tmp) + Math.PI;
  } else if (phase === "queued_at_dump") {
    heading = samplePolyline(path, 1 - (0.015 + h * 0.03) * (dest === "dump" ? 1.6 : 1), lane, tmp);
  } else if (phase === "dumping") {
    heading = samplePolyline(path, 1, 0, tmp);
  } else if (phase === "loading" || phase === "spotting") {
    heading = samplePolyline(path, 0, 0, tmp) + Math.PI;
  } else if (phase === "queued_at_shovel") {
    heading = samplePolyline(path, 0.012 + h * 0.03, -lane, tmp) + Math.PI;
  } else if (phase === "down") {
    heading = samplePolyline(path, 0.25 + h * 0.5, lane * 2.2, tmp);
  } else {
    heading = samplePolyline(path, 0, 0, tmp);
  }

  // Ease position (covers phase switches and lane changes) and heading.
  const k = Math.min(1, dt * 6);
  if (rt.pos.lengthSq() === 0) rt.pos.copy(tmp);
  else rt.pos.lerp(tmp, rt.pos.distanceToSquared(tmp) > 160 * 160 ? 1 : k);
  let dh = ((heading - rt.heading + Math.PI) % (Math.PI * 2)) - Math.PI;
  if (dh < -Math.PI) dh += Math.PI * 2;
  rt.heading += dh * k;
  rt.color = truckColor(phase, parked);
  return rt;
}

function Shovel({ face, onSelect }: { face: FaceDef; onSelect: (id: string) => void }) {
  const id = `kz.kyzyltas.mine:${face.key}`;
  const thing = useMineStore((s) => s.things[id]);
  const state = featureString(thing, "state", "loading");
  const color = shovelColor(state);
  const pos = useMemo(() => facePosition(face), [face]);
  // Face the pit wall (outward).
  const rotY = Math.atan2(pos.x, pos.z);
  const down = state === "down";
  return (
    <group
      position={pos}
      rotation={[0, rotY, 0]}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(id);
      }}
    >
      <mesh position={[0, 2, 0]}>
        <boxGeometry args={[14, 4, 14]} />
        <meshLambertMaterial color="#3b3b3b" />
      </mesh>
      <mesh position={[0, 8, -1]}>
        <boxGeometry args={[11, 8, 12]} />
        <meshLambertMaterial color={down ? "#c0392b" : "#e0a526"} />
      </mesh>
      <mesh position={[0, 14, 7]} rotation={[0.9, 0, 0]}>
        <boxGeometry args={[2.4, 2.4, 16]} />
        <meshLambertMaterial color={down ? "#8e2b20" : "#c98f1d"} />
      </mesh>
      <mesh position={[0, 12, 14]}>
        <boxGeometry args={[6, 5, 5]} />
        <meshLambertMaterial color="#444" />
      </mesh>
      {/* State disc under the machine. */}
      <mesh position={[0, 0.5, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[13, 20]} />
        <meshBasicMaterial color={color} transparent opacity={0.55} depthWrite={false} />
      </mesh>
    </group>
  );
}

function Drill({ face, onSelect }: { face: FaceDef; onSelect: (id: string) => void }) {
  const id = `kz.kyzyltas.mine:${face.key}`;
  const thing = useMineStore((s) => s.things[id]);
  const down = featureString(thing, "state", "drilling") === "down";
  const pos = useMemo(() => facePosition(face).setX(facePosition(face).x * 0.97).setZ(facePosition(face).z * 0.97), [face]);
  return (
    <group
      position={pos}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(id);
      }}
    >
      <mesh position={[0, 2.5, 0]}>
        <boxGeometry args={[7, 5, 11]} />
        <meshLambertMaterial color={down ? "#c0392b" : "#d8c25a"} />
      </mesh>
      <mesh position={[0, 14, -3]}>
        <boxGeometry args={[1.6, 22, 1.6]} />
        <meshLambertMaterial color="#9aa0a6" />
      </mesh>
    </group>
  );
}
