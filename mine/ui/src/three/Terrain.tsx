import { useMemo } from "react";
import * as THREE from "three";
import { PIT, SX, heightAt, isRiser, toWorld, ROADS, SITE, WASTE_DUMP, SHOVEL_FACES } from "./world";

// Static landscape: the terraced pit (one polar heightfield mesh with both
// spiral ramps carved in), the surrounding steppe, surface haul roads, the
// waste dump and the tailings pond.
//
// Lighting is baked into vertex colours once at build time and drawn with
// MeshBasicMaterial: on software WebGL (SwiftShader, no GPU) this costs far
// less per pixel than a lit material while looking the same for static rock.

const LIGHT_DIR = new THREE.Vector3(0.45, 0.8, 0.35).normalize();

function hash2(x: number, z: number): number {
  const s = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
  return s - Math.floor(s);
}
function noise2(x: number, z: number): number {
  const xi = Math.floor(x);
  const zi = Math.floor(z);
  const xf = x - xi;
  const zf = z - zi;
  const u = xf * xf * (3 - 2 * xf);
  const w = zf * zf * (3 - 2 * zf);
  const a = hash2(xi, zi);
  const b = hash2(xi + 1, zi);
  const c = hash2(xi, zi + 1);
  const d = hash2(xi + 1, zi + 1);
  return a + (b - a) * u + (c - a) * w + (a - b - c + d) * u * w;
}

function bakeLight(geometry: THREE.BufferGeometry, ambient = 0.52, diffuse = 0.62) {
  geometry.computeVertexNormals();
  const n = geometry.getAttribute("normal") as THREE.BufferAttribute;
  const c = geometry.getAttribute("color") as THREE.BufferAttribute;
  for (let i = 0; i < n.count; i++) {
    const d = Math.max(0, n.getX(i) * LIGHT_DIR.x + n.getY(i) * LIGHT_DIR.y + n.getZ(i) * LIGHT_DIR.z);
    const k = ambient + diffuse * d;
    c.setXYZ(i, c.getX(i) * k, c.getY(i) * k, c.getZ(i) * k);
  }
  c.needsUpdate = true;
}

const C_GROUND = new THREE.Color("#a39d76");
const C_GROUND2 = new THREE.Color("#8f9467");
const C_CLEARED = new THREE.Color("#a8987a");
const C_BENCH = new THREE.Color("#b09a7c");
const C_RISER = new THREE.Color("#7a6650");
const C_FLOOR = new THREE.Color("#9a876b");
const C_ROAD = new THREE.Color("#6a655f");
const C_ORE = new THREE.Color("#7f9a72");
const C_WASTE = new THREE.Color("#9b9590");

function buildPit(): THREE.BufferGeometry {
  const N = 128;
  const radii: number[] = [0.5];
  for (let r = 4; r < PIT.rTop + 4; r += 4) radii.push(r);
  for (const r of [PIT.rTop + 8, PIT.rTop + 18, PIT.rTop + 32, PIT.rTop + 50, PIT.rTop + PIT.rimPad]) radii.push(r);

  const oreThetas = SHOVEL_FACES.map((f) => ({ th: f.theta, ore: f.material === "ore" }));
  const positions: number[] = [];
  const colors: number[] = [];
  const tmp = new THREE.Vector3();
  const col = new THREE.Color();

  for (const r of radii) {
    for (let s = 0; s <= N; s++) {
      const th = (s / N) * Math.PI * 2;
      const h = heightAt(r, th);
      toWorld(r, th, h.y, tmp);
      positions.push(tmp.x, tmp.y, tmp.z);

      const nz = noise2(tmp.x * 0.05, tmp.z * 0.05);
      if (r >= PIT.rTop) {
        const k = THREE.MathUtils.clamp((r - PIT.rTop) / 45, 0, 1);
        col.copy(C_CLEARED).lerp(nz > 0.5 ? C_GROUND : C_GROUND2, k);
      } else if (r <= PIT.rBot) {
        col.copy(C_FLOOR);
      } else {
        col.copy(isRiser(r) ? C_RISER : C_BENCH);
        // Tint the faces around the shovels: green-grey for ore, grey for waste.
        for (const o of oreThetas) {
          let d = Math.abs(th - o.th) % (Math.PI * 2);
          if (d > Math.PI) d = Math.PI * 2 - d;
          if (d < 0.35) col.lerp(o.ore ? C_ORE : C_WASTE, (1 - d / 0.35) * 0.55);
        }
      }
      if (h.ramp > 0) col.lerp(C_ROAD, 0.85);
      const jitter = 0.9 + nz * 0.2;
      colors.push(col.r * jitter, col.g * jitter, col.b * jitter);
    }
  }

  const indices: number[] = [];
  const row = N + 1;
  for (let i = 0; i < radii.length - 1; i++) {
    for (let s = 0; s < N; s++) {
      const a = i * row + s;
      const b = a + 1;
      const c = a + row;
      const d = c + 1;
      indices.push(a, b, c, b, d, c);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  g.setIndex(indices);
  bakeLight(g);
  return g;
}

/**
 * Steppe around the pit: a polar grid with an elliptical hole for the pit,
 * mottled with two octaves of value noise baked into vertex colours (a
 * texture lookup per pixel is noticeably slower on software WebGL).
 */
function buildGround(): THREE.BufferGeometry {
  const N = 112;
  const radii: number[] = [];
  let r = PIT.rTop + 40;
  while (r < 4200) {
    radii.push(r);
    r += Math.max(18, r * 0.07);
  }
  radii.push(4200);
  const pos: number[] = [];
  const col: number[] = [];
  const c = new THREE.Color();
  for (const rr of radii) {
    for (let s = 0; s <= N; s++) {
      const th = (s / N) * Math.PI * 2;
      const x = Math.cos(th) * rr * SX;
      const z = Math.sin(th) * rr;
      pos.push(x, 0, z);
      const n = noise2(x * 0.012, z * 0.012) * 0.6 + noise2(x * 0.05, z * 0.05) * 0.4;
      c.copy(C_GROUND2).lerp(C_GROUND, n);
      const k = 0.9 + noise2(x * 0.11 + 7, z * 0.11) * 0.18;
      col.push(c.r * k, c.g * k, c.b * k);
    }
  }
  const idx: number[] = [];
  const row = N + 1;
  for (let i = 0; i < radii.length - 1; i++) {
    for (let s = 0; s < N; s++) {
      const a = i * row + s;
      idx.push(a, a + 1, a + row, a + 1, a + row + 1, a + row);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx);
  bakeLight(g);
  return g;
}

function ribbon(points: THREE.Vector3[], width: number, lift = 0.35): THREE.BufferGeometry {
  const pos: number[] = [];
  const idx: number[] = [];
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    const q = points[Math.min(points.length - 1, i + 1)];
    const o = points[Math.max(0, i - 1)];
    const dx = q.x - o.x;
    const dz = q.z - o.z;
    const len = Math.hypot(dx, dz) || 1;
    const nx = (-dz / len) * (width / 2);
    const nz = (dx / len) * (width / 2);
    pos.push(p.x + nx, p.y + lift, p.z + nz, p.x - nx, p.y + lift, p.z - nz);
    if (i > 0) {
      const b = i * 2;
      idx.push(b - 2, b - 1, b, b, b - 1, b + 1);
    }
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setIndex(idx);
  return g;
}

/** Densify a polyline so ribbons bend smoothly. */
function densify(points: THREE.Vector3[], step = 8): THREE.Vector3[] {
  const out: THREE.Vector3[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    const n = Math.max(1, Math.ceil(a.distanceTo(b) / step));
    for (let k = 0; k < n; k++) out.push(a.clone().lerp(b, k / n));
  }
  out.push(points[points.length - 1].clone());
  return out;
}

export { ribbon, densify };

function buildSky(): THREE.BufferGeometry {
  const g = new THREE.SphereGeometry(5000, 24, 12);
  const pos = g.getAttribute("position");
  const colors: number[] = [];
  const top = new THREE.Color("#5f8fc4");
  const horizon = new THREE.Color("#dfe7ee");
  const c = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i) / 5000;
    c.copy(horizon).lerp(top, THREE.MathUtils.clamp(y * 2.2, 0, 1));
    colors.push(c.r, c.g, c.b);
  }
  g.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  return g;
}

export function Terrain() {
  const pit = useMemo(buildPit, []);
  const groundGeo = useMemo(buildGround, []);
  const roads = useMemo(
    () => [
      ribbon(densify(ROADS.mainTopToCrusher), 18),
      ribbon(densify(ROADS.altTopToDump), 16),
      ribbon(densify(ROADS.rimRoad), 12),
      ribbon(densify(ROADS.toWorkshop), 10),
      ribbon(densify(ROADS.plantService), 8)
    ],
    []
  );

  return (
    <group>
      <mesh geometry={groundGeo} position={[0, -0.4, 0]}>
        <meshBasicMaterial vertexColors />
      </mesh>

      <mesh geometry={pit}>
        <meshBasicMaterial vertexColors />
      </mesh>

      {roads.map((g, i) => (
        <mesh key={i} geometry={g}>
          <meshBasicMaterial color="#6b6660" polygonOffset polygonOffsetFactor={-2} polygonOffsetUnits={-2} />
        </mesh>
      ))}

      {/* Waste dump: flat-topped mound north-west of the pit. */}
      <mesh position={[SITE.wasteDump.x, WASTE_DUMP.height / 2, SITE.wasteDump.z]}>
        <cylinderGeometry args={[WASTE_DUMP.rTop, WASTE_DUMP.rBottom, WASTE_DUMP.height, 20, 1]} />
        <meshLambertMaterial color="#8c8274" />
      </mesh>

      {/* Tailings storage facility: embankment ring + pond. */}
      <mesh position={[SITE.tailings.x, 3, SITE.tailings.z]} scale={[1.25, 1, 1]}>
        <cylinderGeometry args={[78, 88, 6, 28, 1]} />
        <meshLambertMaterial color="#8f8574" />
      </mesh>
      <mesh position={[SITE.tailings.x, 6.2, SITE.tailings.z]} rotation={[-Math.PI / 2, 0, 0]} scale={[1.25, 1, 1]}>
        <circleGeometry args={[72, 28]} />
        <meshBasicMaterial color="#9fb3b8" />
      </mesh>
    </group>
  );
}
