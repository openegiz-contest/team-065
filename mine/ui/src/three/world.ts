import * as THREE from "three";

// Schematic world layout for the 3D scene and the minimap.
//
// The twins' attributes.geometry anchors are coarse (the plant, shovels and
// trucks all sit 1.6-2 km east of the pit centre), so the scene uses one
// coherent, compact layout keyed by twin id instead: an elliptical terraced
// pit with two spiral ramps, the crusher / stockpile / mill / flotation
// cluster on the east rim and the waste dump to the north-west. Every twin's
// *state* drives what is drawn; only its placement is schematic.

/** x-stretch applied to the circular pit model to make it elliptical (the real pit is 3.0 x 1.8 km). */
export const SX = 1.3;

export const PIT = {
  rTop: 240,
  rBot: 60,
  benches: 8,
  benchH: 12,
  driveFrac: 0.5,
  rimPad: 70
};
export const STEP = (PIT.rTop - PIT.rBot) / PIT.benches;
export const FLOOR_Y = -PIT.benches * PIT.benchH;

/** Height of the terraced pit surface at local radius r (before ramp carving). */
export function benchProfile(r: number): number {
  if (r >= PIT.rTop) return 0;
  if (r <= PIT.rBot) return FLOOR_Y;
  const b = Math.min(PIT.benches - 1, Math.floor((PIT.rTop - r) / STEP));
  const rOut = PIT.rTop - b * STEP;
  const local = rOut - r;
  const yb = -b * PIT.benchH;
  const drive = STEP * PIT.driveFrac;
  if (local <= drive) return yb;
  const f = (local - drive) / (STEP - drive);
  return yb - f * PIT.benchH;
}

/** 0 = flat bench top, 1 = riser wall, used for colouring. */
export function isRiser(r: number): boolean {
  if (r >= PIT.rTop || r <= PIT.rBot) return false;
  const b = Math.min(PIT.benches - 1, Math.floor((PIT.rTop - r) / STEP));
  const rOut = PIT.rTop - b * STEP;
  return rOut - r > STEP * PIT.driveFrac;
}

export type RampId = "main" | "alt";
export interface RampDef {
  id: RampId;
  theta0: number;
  turns: number;
  halfW: number;
}

// Main ore ramp tops out on the east rim (towards the crusher); the
// alternate (west) ramp serves the waste dump and is the ore detour when the
// main ramp is closed (slope_alarm).
export const RAMPS: Record<RampId, RampDef> = {
  main: { id: "main", theta0: 0, turns: 1.55, halfW: 9 },
  alt: { id: "alt", theta0: Math.PI, turns: 1.55, halfW: 8 }
};
const R_START = PIT.rTop - 2;
const R_END = PIT.rBot + 6;

export function rampLocal(ramp: RampDef, t: number): { r: number; theta: number; y: number } {
  const c = THREE.MathUtils.clamp(t, 0, 1);
  return {
    r: R_START + (R_END - R_START) * c,
    theta: ramp.theta0 + c * ramp.turns * Math.PI * 2,
    y: c * FLOOR_Y
  };
}

export function toWorld(r: number, theta: number, y: number, out = new THREE.Vector3()): THREE.Vector3 {
  return out.set(Math.cos(theta) * r * SX, y, Math.sin(theta) * r);
}

const TWO_PI = Math.PI * 2;

/** Terrain height at local polar coords, with ramp carving. Returns ramp weight for colouring. */
export function heightAt(r: number, theta: number): { y: number; ramp: number } {
  let y = benchProfile(r);
  let best = Infinity;
  let bestY = 0;
  let bestHalfW = 8;
  for (const key of ["main", "alt"] as RampId[]) {
    const ramp = RAMPS[key];
    let a = (theta - ramp.theta0) % TWO_PI;
    if (a < 0) a += TWO_PI;
    for (let k = 0; k <= Math.ceil(ramp.turns); k++) {
      const t = (a + TWO_PI * k) / (TWO_PI * ramp.turns);
      if (t > 1) break;
      const rl = R_START + (R_END - R_START) * t;
      const d = Math.abs(r - rl);
      if (d < best) {
        best = d;
        bestY = t * FLOOR_Y;
        bestHalfW = ramp.halfW;
      }
    }
  }
  const shoulder = 7;
  let rampW = 0;
  if (best < bestHalfW) {
    y = bestY;
    rampW = 1;
  } else if (best < bestHalfW + shoulder && r < PIT.rTop + 2) {
    const w = (best - bestHalfW) / shoulder;
    const s = w * w * (3 - 2 * w);
    y = bestY + (y - bestY) * s;
  }
  return { y, ramp: rampW };
}

export function worldHeight(x: number, z: number): number {
  const lx = x / SX;
  const r = Math.hypot(lx, z);
  if (r >= PIT.rTop + 1) return 0;
  return heightAt(r, Math.atan2(z, lx)).y;
}

// --- Bench / shovel placement -------------------------------------------

export function benchDriveRadius(b: number): number {
  return PIT.rTop - b * STEP - STEP * PIT.driveFrac * 0.5;
}
export function benchY(b: number): number {
  return -b * PIT.benchH;
}

/** Ramp parameter where a ramp passes bench b's elevation. */
export function rampTAtBench(b: number): number {
  return (b * PIT.benchH) / -FLOOR_Y;
}

function deg(d: number): number {
  return (d * Math.PI) / 180;
}

function rampClear(b: number, theta: number): boolean {
  // Is the bench drive at this angle at least ~30 m from either ramp?
  for (const dt of [-0.12, 0, 0.12]) {
    const r = benchDriveRadius(b);
    if (heightAt(r, theta + dt).ramp > 0) return false;
    if (Math.abs(heightAt(r, theta + dt).y - benchY(b)) > 1.5) return false;
  }
  return true;
}

function clearTheta(b: number, desired: number): number {
  for (let i = 0; i < 40; i++) {
    for (const sgn of [1, -1]) {
      const th = desired + sgn * i * 0.03;
      if (rampClear(b, th)) return th;
    }
  }
  return desired;
}

export interface FaceDef {
  key: string; // twin id suffix, e.g. "shovel-s1"
  short: string; // "S1"
  material: "ore" | "waste";
  bench: number;
  theta: number;
}

export const SHOVEL_FACES: FaceDef[] = [
  { key: "shovel-s1", short: "S1", material: "ore", bench: 6, theta: clearTheta(6, deg(232)) },
  { key: "shovel-s2", short: "S2", material: "ore", bench: 5, theta: clearTheta(5, deg(292)) },
  { key: "shovel-s3", short: "S3", material: "waste", bench: 2, theta: clearTheta(2, deg(205)) },
  { key: "shovel-s4", short: "S4", material: "waste", bench: 3, theta: clearTheta(3, deg(328)) }
];

export const DRILL_FACES: FaceDef[] = [
  { key: "drill-01", short: "D1", material: "ore", bench: 4, theta: clearTheta(4, deg(255)) },
  { key: "drill-02", short: "D2", material: "waste", bench: 1, theta: clearTheta(1, deg(305)) }
];

export function facePosition(f: FaceDef, out = new THREE.Vector3()): THREE.Vector3 {
  // Shovel sits near the toe of the wall above its bench (outer edge of the drive).
  const r = PIT.rTop - f.bench * STEP - 4;
  return toWorld(r, f.theta, benchY(f.bench), out);
}

// --- Surface layout -------------------------------------------------------

const v = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);

export const SITE = {
  crusher: v(420, 0, -58),
  crusherDump: v(398, 0, -52),
  romPad: v(468, 0, 38),
  hgPile: v(418, 0, 26),
  lowGradePile: v(372, 0, 92),
  crushedPile: v(512, 0, -58),
  sag: v(584, 0, -70),
  ball1: v(584, 0, -28),
  ball2: v(616, 0, -28),
  flotation: v(664, 0, -54),
  thickener: v(650, 0, 30),
  tailings: v(700, 0, 130),
  substation: v(528, 0, -160),
  workshop: v(424, 0, -160),
  wasteDump: v(-392, 0, -292),
  wasteDumpTip: v(-372, 22, -246),
  weather: v(-170, 0, 300),
  radarEast: v(0, 0, 0), // set below (rim)
  radarWest: v(0, 0, 0),
  fanPit: v(-60, 0, 312),
  fanPlant: v(552, 0, 30)
};
toWorld(PIT.rTop + 14, deg(-22), 0, SITE.radarEast);
toWorld(PIT.rTop + 14, deg(160), 0, SITE.radarWest);

export const WASTE_DUMP = { rTop: 62, rBottom: 100, height: 22 };

/** Parking slots in front of the workshop for trucks with parked=1. */
export function parkingSlot(i: number, out = new THREE.Vector3()): THREE.Vector3 {
  return out.set(SITE.workshop.x - 40 + (i % 6) * 15, 0, SITE.workshop.z + 34 + Math.floor(i / 6) * 22);
}

// --- Haul paths -----------------------------------------------------------

export interface Polyline {
  pts: THREE.Vector3[];
  cum: number[];
  total: number;
}

export function makePolyline(pts: THREE.Vector3[]): Polyline {
  const cum = [0];
  for (let i = 1; i < pts.length; i++) cum.push(cum[i - 1] + pts[i].distanceTo(pts[i - 1]));
  return { pts, cum, total: cum[cum.length - 1] || 1 };
}

const _a = new THREE.Vector3();
const _b = new THREE.Vector3();

/** Sample a polyline at fraction u (0..1); writes position, returns heading (rotation.y). */
export function samplePolyline(pl: Polyline, u: number, lane: number, out: THREE.Vector3): number {
  const target = THREE.MathUtils.clamp(u, 0, 1) * pl.total;
  let lo = 0;
  let hi = pl.cum.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (pl.cum[mid] <= target) lo = mid;
    else hi = mid;
  }
  const segLen = pl.cum[hi] - pl.cum[lo] || 1;
  const f = (target - pl.cum[lo]) / segLen;
  _a.copy(pl.pts[lo]);
  _b.copy(pl.pts[hi]);
  out.copy(_a).lerp(_b, f);
  const dx = _b.x - _a.x;
  const dz = _b.z - _a.z;
  const len = Math.hypot(dx, dz) || 1;
  // Right-hand lane offset (perpendicular in the ground plane).
  out.x += (-dz / len) * lane;
  out.z += (dx / len) * lane;
  return Math.atan2(dx, dz);
}

function rampPoints(ramp: RampDef, tFrom: number, tTo: number): THREE.Vector3[] {
  const pts: THREE.Vector3[] = [];
  const n = Math.max(2, Math.ceil(Math.abs(tTo - tFrom) * 120));
  for (let i = 0; i <= n; i++) {
    const t = tFrom + ((tTo - tFrom) * i) / n;
    const p = rampLocal(ramp, t);
    pts.push(toWorld(p.r, p.theta, p.y + 0.2));
  }
  return pts;
}

function benchArc(b: number, thFrom: number, thTo: number): THREE.Vector3[] {
  let d = (thTo - thFrom) % TWO_PI;
  if (d > Math.PI) d -= TWO_PI;
  if (d < -Math.PI) d += TWO_PI;
  const n = Math.max(2, Math.ceil(Math.abs(d) / 0.04));
  const r = benchDriveRadius(b);
  const pts: THREE.Vector3[] = [];
  for (let i = 0; i <= n; i++) pts.push(toWorld(r, thFrom + (d * i) / n, benchY(b) + 0.2));
  return pts;
}

export const ROADS = {
  mainTopToCrusher: [toWorld(R_START, 0, 0), v(338, 0, -14), v(366, 0, -38), SITE.crusherDump.clone()],
  altTopToDump: [
    toWorld(R_START, Math.PI, 0),
    v(-338, 0, -30),
    v(-352, 0, -110),
    v(-356, 0, -168),
    v(-362, 8, -200),
    SITE.wasteDumpTip.clone()
  ],
  rimRoad: (() => {
    const pts: THREE.Vector3[] = [toWorld(R_START, Math.PI, 0)];
    for (let i = 1; i <= 24; i++) {
      const th = Math.PI + (Math.PI * 0.94 * i) / 24;
      pts.push(toWorld(PIT.rTop + 26, th, 0));
    }
    pts.push(v(366, 0, -38), SITE.crusherDump.clone());
    return pts;
  })(),
  toWorkshop: [v(338, 0, -14), v(380, 0, -110), v(SITE.workshop.x - 10, 0, SITE.workshop.z + 26)],
  plantService: [SITE.crusher.clone().setY(0), v(470, 0, -110), SITE.substation.clone()]
};

const pathCache = new Map<string, Polyline>();

/**
 * Loaded haul path from a shovel face to a destination via a ramp.
 * dest "crusher" uses the main ramp unless `rampId` is "alt" (detour via
 * the west ramp and the north rim road); dest "dump" goes to the waste dump.
 */
export function haulPath(face: FaceDef, rampId: RampId, dest: "crusher" | "dump"): Polyline {
  const key = `${face.key}|${rampId}|${dest}`;
  const hit = pathCache.get(key);
  if (hit) return hit;
  const ramp = RAMPS[rampId];
  const tb = rampTAtBench(face.bench);
  const rb = rampLocal(ramp, tb);
  const pts: THREE.Vector3[] = [];
  const loadSpot = toWorld(PIT.rTop - face.bench * STEP - 11, face.theta + 0.03, benchY(face.bench) + 0.2);
  pts.push(loadSpot);
  pts.push(...benchArc(face.bench, face.theta + 0.03, rb.theta));
  pts.push(...rampPoints(ramp, tb, 0));
  if (dest === "dump") pts.push(...ROADS.altTopToDump.slice(1));
  else if (rampId === "main") pts.push(...ROADS.mainTopToCrusher.slice(1));
  else pts.push(...ROADS.rimRoad.slice(1));
  const pl = makePolyline(pts);
  pathCache.set(key, pl);
  return pl;
}

export function faceByKey(key: string): FaceDef | undefined {
  const k = key.includes(":") ? key.split(":")[1] : key;
  return SHOVEL_FACES.find((f) => f.key === k);
}

/** Sampled ramp centreline in world coords (for overlays: closed ramp, trolley line). */
export function rampCenterline(rampId: RampId, tFrom = 0, tTo = 1): THREE.Vector3[] {
  return rampPoints(RAMPS[rampId], tFrom, tTo);
}

/** Default camera framings. */
export const VIEWS = {
  overview: { pos: [330, 560, 820] as [number, number, number], target: [170, -50, -40] as [number, number, number] },
  pit: { pos: [40, 300, 400] as [number, number, number], target: [0, -55, -40] as [number, number, number] },
  plant: { pos: [690, 190, 210] as [number, number, number], target: [540, 0, -40] as [number, number, number] }
};
