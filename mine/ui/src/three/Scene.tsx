import { Suspense, useEffect, useRef } from "react";
import * as THREE from "three";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import { Terrain } from "./Terrain";
import { Equipment } from "./Equipment";
import { Plant } from "./Plant";
import { HaulDust, ScenarioHighlights, Snow } from "./Effects";
import { LabelProjector } from "./Labels";
import { VIEWS } from "./world";
import { useMineStore } from "../store/useMineStore";
import { getScenarioThing, featureNumber, featureString, listByClass } from "../lib/selectors";

export type ViewName = keyof typeof VIEWS;

interface SceneProps {
  onSelect: (thingId: string) => void;
  view: ViewName;
  viewNonce: number;
}

/**
 * The 3D mine scene, tuned for software WebGL (SwiftShader / llvmpipe, no GPU):
 * - device pixel ratio capped at 1 (0.7 in performance mode), no MSAA
 * - static terrain uses baked vertex lighting + MeshBasicMaterial
 * - equipment uses MeshLambertMaterial, one hemisphere + one directional light
 * - trucks are a single InstancedMesh; no shadows, no post-processing
 * - performance mode switches on automatically if the frame rate stays
 *   below 15 fps for 3 s.
 */
export function Scene({ onSelect, view, viewNonce }: SceneProps) {
  const performanceMode = useMineStore((s) => s.performanceMode);
  const dpr = performanceMode ? 0.7 : Math.min(1, window.devicePixelRatio || 1);
  return (
    <Canvas
      dpr={dpr}
      shadows={false}
      gl={{ antialias: false, alpha: false, powerPreference: "high-performance", stencil: false }}
      camera={{ position: VIEWS.overview.pos, fov: 40, near: 2, far: 12000 }}
      onPointerMissed={() => onSelect("")}
      aria-label="3D view of the Kyzyl-Tas open pit, haul roads, trucks, shovels and processing plant"
    >
      <SceneContents onSelect={onSelect} view={view} viewNonce={viewNonce} />
    </Canvas>
  );
}

function SceneContents({ onSelect, view, viewNonce }: SceneProps) {
  const things = useMineStore((s) => s.things);
  const active = featureString(getScenarioThing(things), "active_scenario", "none");
  const weather = listByClass(things, "WeatherStation")[0];
  const condition = featureString(weather, "condition", "clear");
  // Weather comes from the weather-station twin, whatever caused it.
  const tempC = featureNumber(weather, "temp_c", 15);
  const cold = tempC <= -10 || condition === "blizzard" || condition === "extreme_cold";
  const inversion = condition === "calm_inversion";
  const fogColor = cold ? "#d9e2ea" : inversion ? "#cfd3d6" : "#dfe7ee";
  const fogNear = condition === "blizzard" ? 300 : cold || inversion ? 500 : 1100;
  const fogFar = condition === "blizzard" ? 1600 : cold || inversion ? 2200 : 3800;

  return (
    <>
      <color attach="background" args={[cold ? "#d3dde6" : "#c3d4e4"]} />
      <fog attach="fog" args={[fogColor, fogNear, fogFar]} />
      <hemisphereLight args={["#e8f0f8", "#6b5d4a", 0.9]} />
      <directionalLight position={[300, 500, 250]} intensity={1.6} />

      <Suspense fallback={null}>
        <Terrain />
        <Plant onSelect={onSelect} />
        <Equipment onSelect={onSelect} />
        <ScenarioHighlights />
        <HaulDust />
        <Snow />
      </Suspense>
      <LabelProjector />
      <FpsMonitor />
      <CameraRig view={view} viewNonce={viewNonce} />
    </>
  );
}

/** Smoothly moves camera + orbit target to a named framing when the view changes. */
function CameraRig({ view, viewNonce }: { view: ViewName; viewNonce: number }) {
  const controls = useRef<OrbitControlsImpl>(null);
  const camera = useThree((s) => s.camera);
  const anim = useRef<{ t: number; fromPos: THREE.Vector3; fromTarget: THREE.Vector3 } | null>(null);
  const toPos = useRef(new THREE.Vector3(...VIEWS.overview.pos));
  const toTarget = useRef(new THREE.Vector3(...VIEWS.overview.target));

  useEffect(() => {
    const c = controls.current;
    if (!c) return;
    toPos.current.set(...VIEWS[view].pos);
    toTarget.current.set(...VIEWS[view].target);
    anim.current = { t: 0, fromPos: camera.position.clone(), fromTarget: c.target.clone() };
  }, [view, viewNonce, camera]);

  useFrame((_, delta) => {
    const a = anim.current;
    const c = controls.current;
    if (!a || !c) return;
    a.t = Math.min(1, a.t + delta / 1.1);
    const e = a.t * a.t * (3 - 2 * a.t);
    camera.position.lerpVectors(a.fromPos, toPos.current, e);
    c.target.lerpVectors(a.fromTarget, toTarget.current, e);
    c.update();
    if (a.t >= 1) anim.current = null;
  });

  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enableDamping={false}
      minDistance={80}
      maxDistance={2200}
      maxPolarAngle={Math.PI / 2 - 0.08}
      target={VIEWS.overview.target}
    />
  );
}

/** Measures frame rate; enables performance mode after 3 s below 15 fps. */
function FpsMonitor() {
  const sc = useThree((s) => s.scene);
  const gl = useThree((s) => s.gl);
  (window as unknown as Record<string, unknown>).__dbg = { sc, gl }; // TEMP-DEBUG
  const frames = useRef(0);
  const since = useRef(performance.now());
  const slowSeconds = useRef(0);
  const warmup = useRef(2);
  useFrame(() => {
    frames.current++;
    const now = performance.now();
    const dt = now - since.current;
    if (dt < 1000) return;
    const fps = (frames.current * 1000) / dt;
    frames.current = 0;
    since.current = now;
    const st = useMineStore.getState();
    st.setFps(Math.round(fps));
    if (warmup.current > 0) {
      warmup.current--;
      return;
    }
    if (!st.performanceMode && fps < 15) {
      slowSeconds.current++;
      if (slowSeconds.current >= 3) st.setPerformanceMode(true, true);
    } else {
      slowSeconds.current = 0;
    }
  });
  return null;
}
