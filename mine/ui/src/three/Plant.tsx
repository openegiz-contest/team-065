import { useRef } from "react";
import * as THREE from "three";
import { useFrame, type ThreeEvent } from "@react-three/fiber";
import { useMineStore } from "../store/useMineStore";
import { featureNumber, featureString } from "../lib/selectors";
import { SITE } from "./world";

// Surface plant cluster on the east rim: primary crusher -> conveyor ->
// crushed-ore stockpile -> SAG + ball mills -> flotation -> thickener ->
// tailings, plus ROM / low-grade stockpiles, substation, truck workshop,
// weather station, slope radars and dust stations. Placement is schematic
// (see world.ts); colours and motion follow live twin features.

const NS = "kz.kyzyltas.mine:";

function useThing(key: string) {
  return useMineStore((s) => s.things[NS + key]);
}

function clickTo(onSelect: (id: string) => void, key: string) {
  return (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    onSelect(NS + key);
  };
}

const STEEL = "#9aa3ad";
const DARK = "#4d5560";

export function Plant({ onSelect }: { onSelect: (thingId: string) => void }) {
  return (
    <group>
      <Crusher onSelect={onSelect} />
      <Conveyor from={[SITE.crusher.x + 10, 22, SITE.crusher.z]} to={[SITE.crushedPile.x - 6, 30, SITE.crushedPile.z]} id="conveyor-02" onSelect={onSelect} />
      <Conveyor from={[SITE.crushedPile.x + 18, 4, SITE.crushedPile.z - 6]} to={[SITE.sag.x - 14, 16, SITE.sag.z]} id="conveyor-01" onSelect={onSelect} />
      <Stockpile pos={SITE.crushedPile} id="stockpile-crushed" color="#8d8579" maxR={30} maxH={32} onSelect={onSelect} />
      <Stockpile pos={SITE.romPad} id="stockpile-rom" color="#a5865c" maxR={26} maxH={18} onSelect={onSelect} />
      <Stockpile pos={SITE.hgPile} id="stockpile-hg" color="#7d8f6a" maxR={26} maxH={20} onSelect={onSelect} />
      <Stockpile pos={SITE.lowGradePile} id="stockpile-waste" color="#7f776b" maxR={30} maxH={18} onSelect={onSelect} />
      <Mill pos={SITE.sag} id="mill-sag-01" radius={13} length={16} onSelect={onSelect} />
      <Mill pos={SITE.ball1} id="mill-ball-01" radius={7.5} length={18} onSelect={onSelect} />
      <Mill pos={SITE.ball2} id="mill-ball-02" radius={7.5} length={18} onSelect={onSelect} />
      <Flotation onSelect={onSelect} />
      <Thickeners onSelect={onSelect} />
      <Substation onSelect={onSelect} />
      <Workshop />
      <Mast pos={SITE.weather} id="weather-station-01" height={16} color="#e6ecf1" onSelect={onSelect} />
      <Radar pos={SITE.radarEast} id="slope-radar-01" onSelect={onSelect} />
      <Radar pos={SITE.radarWest} id="slope-radar-02" onSelect={onSelect} />
      <Mast pos={SITE.fanPit} id="fan-pit-01" height={8} color="#6aa9d8" onSelect={onSelect} />
      <Mast pos={SITE.fanPlant} id="fan-plant-01" height={8} color="#6aa9d8" onSelect={onSelect} />
    </group>
  );
}

function Crusher({ onSelect }: { onSelect: (id: string) => void }) {
  const t = useThing("crusher-01");
  const state = featureString(t, "state", "crushing");
  const body = state === "down" ? "#c0392b" : state === "starved" ? "#c99a2e" : "#b8bec6";
  const p = SITE.crusher;
  return (
    <group position={[p.x, 0, p.z]} onClick={clickTo(onSelect, "crusher-01")}>
      {/* Tipping wall + dump pocket. */}
      <mesh position={[-14, 4, 0]}>
        <boxGeometry args={[10, 8, 30]} />
        <meshLambertMaterial color="#8a8377" />
      </mesh>
      <mesh position={[4, 13, 0]}>
        <boxGeometry args={[24, 26, 24]} />
        <meshLambertMaterial color={body} />
      </mesh>
      <mesh position={[4, 28, 0]}>
        <boxGeometry args={[26, 3, 26]} />
        <meshLambertMaterial color="#59626d" />
      </mesh>
    </group>
  );
}

function Conveyor({
  from,
  to,
  id,
  onSelect
}: {
  from: [number, number, number];
  to: [number, number, number];
  id: string;
  onSelect: (id: string) => void;
}) {
  const t = useThing(id);
  const running = featureString(t, "state", "running") === "running";
  const a = new THREE.Vector3(...from);
  const b = new THREE.Vector3(...to);
  const mid = a.clone().add(b).multiplyScalar(0.5);
  const len = a.distanceTo(b);
  const dir = b.clone().sub(a).normalize();
  const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), dir);
  return (
    <group onClick={clickTo(onSelect, id)}>
      <mesh position={mid} quaternion={quat}>
        <boxGeometry args={[len, 2.4, 5]} />
        <meshLambertMaterial color={running ? "#5d6773" : "#7b4b45"} />
      </mesh>
      <mesh position={[mid.x, mid.y / 2, mid.z]}>
        <boxGeometry args={[1.2, mid.y, 1.2]} />
        <meshLambertMaterial color={DARK} />
      </mesh>
    </group>
  );
}

function Stockpile({
  pos,
  id,
  color,
  maxR,
  maxH,
  onSelect
}: {
  pos: THREE.Vector3;
  id: string;
  color: string;
  maxR: number;
  maxH: number;
  onSelect: (id: string) => void;
}) {
  const t = useThing(id);
  const fill = THREE.MathUtils.clamp(featureNumber(t, "fill_pct", 60) / 100, 0.05, 1);
  const s = 0.35 + 0.65 * Math.cbrt(fill);
  const h = maxH * s;
  return (
    <mesh position={[pos.x, h / 2, pos.z]} onClick={clickTo(onSelect, id)}>
      <coneGeometry args={[maxR * s, h, 18, 1]} />
      <meshLambertMaterial color={color} />
    </mesh>
  );
}

function Mill({
  pos,
  id,
  radius,
  length,
  onSelect
}: {
  pos: THREE.Vector3;
  id: string;
  radius: number;
  length: number;
  onSelect: (id: string) => void;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const t = useThing(id);
  const state = featureString(t, "state", "grinding");
  const running = state === "grinding" || state === "running";
  useFrame((_, delta) => {
    if (ref.current && running) ref.current.rotation.y += delta * 0.9;
  });
  const color = state === "down" ? "#c0392b" : state === "starved" ? "#c99a2e" : "#c7cdd4";
  return (
    <group position={[pos.x, 0, pos.z]} onClick={clickTo(onSelect, id)}>
      <mesh position={[0, 3, 0]}>
        <boxGeometry args={[radius * 2 + 4, 6, length + 8]} />
        <meshLambertMaterial color="#6b7480" />
      </mesh>
      <group position={[0, radius + 6, 0]} rotation={[Math.PI / 2, 0, 0]}>
        <mesh ref={ref}>
          <cylinderGeometry args={[radius, radius, length, 16, 1]} />
          <meshLambertMaterial color={color} />
        </mesh>
      </group>
    </group>
  );
}

function Flotation({ onSelect }: { onSelect: (id: string) => void }) {
  const p = SITE.flotation;
  return (
    <group position={[p.x, 0, p.z]} onClick={clickTo(onSelect, "flotation-01")}>
      <mesh position={[0, 1.5, 0]}>
        <boxGeometry args={[16, 3, 64]} />
        <meshLambertMaterial color="#5e6772" />
      </mesh>
      {[-24, -12, 0, 12, 24].map((z) => (
        <mesh key={z} position={[0, 8, z]}>
          <cylinderGeometry args={[5.2, 5.2, 10, 12, 1]} />
          <meshLambertMaterial color="#5f9c8a" />
        </mesh>
      ))}
    </group>
  );
}

function Thickeners({ onSelect }: { onSelect: (id: string) => void }) {
  const p = SITE.thickener;
  return (
    <group position={[p.x, 0, p.z]} onClick={clickTo(onSelect, "tailings-01")}>
      {[-16, 16].map((x) => (
        <mesh key={x} position={[x, 3, 0]}>
          <cylinderGeometry args={[13, 13, 6, 20, 1]} />
          <meshLambertMaterial color="#8fa3ad" />
        </mesh>
      ))}
    </group>
  );
}

function Substation({ onSelect }: { onSelect: (id: string) => void }) {
  const t = useThing("substation-01");
  const load = featureNumber(t, "load_kw", 0);
  const cap = featureNumber(t, "capacity_kw", 214000);
  const hot = cap > 0 && load / cap > 0.85;
  const p = SITE.substation;
  return (
    <group position={[p.x, 0, p.z]} onClick={clickTo(onSelect, "substation-01")}>
      <mesh position={[0, 0.6, 0]}>
        <boxGeometry args={[40, 1.2, 30]} />
        <meshLambertMaterial color="#8d9196" />
      </mesh>
      {[-12, 0, 12].map((x) => (
        <mesh key={x} position={[x, 6, -4]}>
          <boxGeometry args={[6, 10, 6]} />
          <meshLambertMaterial color={hot ? "#d29922" : "#6d7682"} />
        </mesh>
      ))}
      {[-16, 16].map((x) => (
        <mesh key={x} position={[x, 12, 10]}>
          <boxGeometry args={[1.2, 24, 1.2]} />
          <meshLambertMaterial color={STEEL} />
        </mesh>
      ))}
    </group>
  );
}

function Workshop() {
  const p = SITE.workshop;
  return (
    <group position={[p.x, 0, p.z]}>
      <mesh position={[0, 9, 0]}>
        <boxGeometry args={[60, 18, 30]} />
        <meshLambertMaterial color="#7d8fa3" />
      </mesh>
      <mesh position={[0, 0.3, 40]}>
        <boxGeometry args={[100, 0.6, 50]} />
        <meshLambertMaterial color="#8a8780" />
      </mesh>
    </group>
  );
}

function Mast({
  pos,
  id,
  height,
  color,
  onSelect
}: {
  pos: THREE.Vector3;
  id: string;
  height: number;
  color: string;
  onSelect: (id: string) => void;
}) {
  return (
    <group position={[pos.x, 0, pos.z]} onClick={clickTo(onSelect, id)}>
      <mesh position={[0, height / 2, 0]}>
        <boxGeometry args={[1.2, height, 1.2]} />
        <meshLambertMaterial color={STEEL} />
      </mesh>
      <mesh position={[0, height, 0]}>
        <boxGeometry args={[4, 2.5, 4]} />
        <meshLambertMaterial color={color} />
      </mesh>
    </group>
  );
}

function Radar({ pos, id, onSelect }: { pos: THREE.Vector3; id: string; onSelect: (id: string) => void }) {
  const t = useThing(id);
  const level = featureString(t, "tarp_level", "green");
  const color = level === "red" ? "#ff4d4d" : level === "amber" ? "#e3b341" : "#3fb950";
  const face = Math.atan2(-pos.x, -pos.z);
  return (
    <group position={[pos.x, 0, pos.z]} rotation={[0, face, 0]} onClick={clickTo(onSelect, id)}>
      <mesh position={[0, 2, 0]}>
        <boxGeometry args={[6, 4, 8]} />
        <meshLambertMaterial color="#d7dbe0" />
      </mesh>
      <mesh position={[0, 7, 2]} rotation={[0.5, 0, 0]}>
        <boxGeometry args={[7, 5, 0.8]} />
        <meshLambertMaterial color={color} />
      </mesh>
    </group>
  );
}
