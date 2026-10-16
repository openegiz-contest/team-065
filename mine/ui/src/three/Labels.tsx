import { useMemo } from "react";
import * as THREE from "three";
import { useFrame, useThree } from "@react-three/fiber";
import { useMineStore } from "../store/useMineStore";
import { featureNumber, featureString, getKpiThing, getScenarioThing, shovelColor } from "../lib/selectors";
import { SHOVEL_FACES, facePosition, rampCenterline, SITE, WASTE_DUMP } from "./world";
import { fmt } from "../lib/kpi";

// Floating asset labels. They are ordinary DOM buttons (real text, keyboard
// accessible, click = inspect), positioned over the canvas each frame by
// <LabelProjector/> which writes CSS transforms directly (no React render).

const NS = "kz.kyzyltas.mine:";
const registry = new Map<string, { el: HTMLElement; anchor: THREE.Vector3 }>();

interface LabelDef {
  key: string;
  anchor: THREE.Vector3;
  thingId?: string;
}

function anchors(): LabelDef[] {
  const out: LabelDef[] = SHOVEL_FACES.map((f) => ({
    key: f.key,
    anchor: facePosition(f).add(new THREE.Vector3(0, 24, 0)),
    thingId: NS + f.key
  }));
  const at = (v: THREE.Vector3, y: number) => new THREE.Vector3(v.x, y, v.z);
  out.push(
    { key: "crusher", anchor: at(SITE.crusher, 36), thingId: NS + "crusher-01" },
    { key: "crushed", anchor: at(SITE.crushedPile, 40), thingId: NS + "stockpile-crushed" },
    { key: "sag", anchor: at(SITE.sag, 38), thingId: NS + "mill-sag-01" },
    { key: "flotation", anchor: at(SITE.flotation, 22), thingId: NS + "flotation-01" },
    { key: "tailings", anchor: at(SITE.tailings, 12), thingId: NS + "tailings-01" },
    { key: "dump", anchor: at(SITE.wasteDump, WASTE_DUMP.height + 8) },
    { key: "hg", anchor: at(SITE.hgPile, 26), thingId: NS + "stockpile-hg" },
    { key: "lowgrade", anchor: at(SITE.lowGradePile, 24), thingId: NS + "stockpile-waste" },
    { key: "workshop", anchor: at(SITE.workshop, 26) },
    { key: "substation", anchor: at(SITE.substation, 28), thingId: NS + "substation-01" },
    { key: "radar", anchor: at(SITE.radarEast, 16), thingId: NS + "slope-radar-01" },
    { key: "mainramp", anchor: rampCenterline("main", 0.2, 0.2)[0].add(new THREE.Vector3(0, 6, 0)), thingId: NS + "road-ramp-ore-up" },
    { key: "altramp", anchor: rampCenterline("alt", 0.22, 0.22)[0].add(new THREE.Vector3(0, 6, 0)), thingId: NS + "road-ramp-waste-up" }
  );
  return out;
}

export const LABEL_DEFS = anchors();

const _v = new THREE.Vector3();
const sizes = new Map<HTMLElement, { w: number; h: number }>();
let frameNo = 0;

interface Placed {
  el: HTMLElement;
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Inside the Canvas: projects each registered label anchor to screen space every frame, then
 * resolves overlaps by nudging labels upward (lowest on screen placed first), so neighbouring
 * labels such as the shovels stay readable while still sitting above their asset.
 */
export function LabelProjector() {
  const camera = useThree((s) => s.camera);
  const size = useThree((s) => s.size);
  useFrame(() => {
    frameNo++;
    const items: Placed[] = [];
    for (const { el, anchor } of registry.values()) {
      _v.copy(anchor).project(camera);
      if (_v.z > 1 || _v.x < -1.1 || _v.x > 1.1 || _v.y < -1.1 || _v.y > 1.1) {
        if (el.style.visibility !== "hidden") el.style.visibility = "hidden";
        continue;
      }
      let sz = sizes.get(el);
      if (!sz || frameNo % 30 === 0) {
        sz = { w: el.offsetWidth || 120, h: el.offsetHeight || 22 };
        sizes.set(el, sz);
      }
      items.push({ el, x: ((_v.x + 1) / 2) * size.width, y: ((1 - _v.y) / 2) * size.height, w: sz.w, h: sz.h });
    }
    items.sort((a, b) => b.y - a.y);
    const placed: { x0: number; x1: number; y0: number; y1: number }[] = [];
    for (const it of items) {
      // Keep labels inside the view rather than clipped at its edge.
      it.x = Math.min(Math.max(it.x, it.w / 2 + 4), size.width - it.w / 2 - 4);
      const x0 = it.x - it.w / 2 - 2;
      const x1 = it.x + it.w / 2 + 2;
      let bottom = it.y;
      for (let guard = 0; guard < 12; guard++) {
        const top = bottom - it.h;
        const hit = placed.find((p) => x0 < p.x1 && x1 > p.x0 && top < p.y1 && bottom > p.y0);
        if (!hit) break;
        bottom = hit.y0 - 2;
      }
      placed.push({ x0, x1, y0: bottom - it.h, y1: bottom });
      it.el.style.transform = `translate(${it.x.toFixed(1)}px, ${bottom.toFixed(1)}px) translate(-50%, -100%)`;
      if (it.el.style.visibility !== "visible") it.el.style.visibility = "visible";
    }
  });
  return null;
}

interface LabelView {
  text: string;
  sub?: string;
  tone: "normal" | "bad" | "warn" | "muted";
  dot?: string;
  hidden?: boolean;
}

/** Outside the Canvas (overlay): the label elements themselves. */
export function SceneLabels({ onSelect }: { onSelect: (id: string) => void }) {
  const things = useMineStore((s) => s.things);
  const kpi = getKpiThing(things);
  const active = featureString(getScenarioThing(things), "active_scenario", "none");
  const views = useMemo(() => {
    const m = new Map<string, LabelView>();
    for (const f of SHOVEL_FACES) {
      const t = things[NS + f.key];
      const st = featureString(t, "state", "");
      const q = featureNumber(t, "queue_length", 0);
      const grade = featureNumber(t, "face_grade_pct", 0);
      const what = f.material === "ore" ? `ore ${grade.toFixed(2)}% Cu` : "waste";
      const status = st === "down" ? "DOWN - failed" : st === "blocked" ? "idle - fume exclusion" : q > 0 ? `${q} truck${q > 1 ? "s" : ""} queued` : "digging";
      m.set(f.key, {
        text: `${f.short} · ${what}`,
        sub: status,
        tone: st === "down" ? "bad" : st === "blocked" ? "warn" : "normal",
        dot: shovelColor(st)
      });
    }
    const crusher = things[NS + "crusher-01"];
    m.set("crusher", { text: "Primary crusher", sub: `${fmt(featureNumber(crusher, "throughput_tph", 0))} t/h`, tone: "normal" });
    const buffer = featureNumber(kpi, "current_buffer_h", NaN);
    m.set("crushed", {
      text: "Crushed-ore stockpile",
      sub: Number.isFinite(buffer) ? `${buffer.toFixed(1)} h of feed` : undefined,
      tone: Number.isFinite(buffer) && buffer < 4 ? "bad" : Number.isFinite(buffer) && buffer < 8 ? "warn" : "normal"
    });
    const sag = things[NS + "mill-sag-01"];
    m.set("sag", {
      text: "SAG mill",
      sub: `${fmt(featureNumber(sag, "throughput_tph", 0))} t/h`,
      tone: active === "grid_curtailment" || active === "hard_ore_domain" ? "warn" : "normal"
    });
    const flot = things[NS + "flotation-01"];
    const rec = featureNumber(flot, "cu_recovery_pct", NaN);
    m.set("flotation", { text: "Flotation", sub: Number.isFinite(rec) ? `Cu recovery ${rec.toFixed(1)}%` : undefined, tone: "normal" });
    m.set("tailings", { text: "Tailings", tone: "muted", hidden: true });
    m.set("dump", { text: "Waste dump", tone: "muted" });
    const hg = things[NS + "stockpile-hg"];
    const reclaim = featureNumber(hg, "reclaim_tph", 0);
    m.set("hg", {
      text: "High-grade stockpile",
      sub: reclaim > 1 ? `reclaiming ${fmt(reclaim)} t/h` : undefined,
      tone: reclaim > 1 ? "warn" : "muted"
    });
    m.set("lowgrade", { text: "Low-grade stockpile", tone: active === "price_drop" ? "warn" : "muted", hidden: active !== "price_drop" });
    const parked = Object.values(things).filter((t) => t.attributes?.class === "HaulTruck" && featureNumber(t, "parked", 0) === 1).length;
    m.set("workshop", {
      text: "Truck workshop",
      sub: parked > 0 ? `${parked} parked` : undefined,
      tone: parked > 0 ? "warn" : "muted",
      hidden: parked === 0 && active !== "predictive_maintenance"
    });
    const sub = things[NS + "substation-01"];
    m.set("substation", {
      text: "Substation",
      sub: `${(featureNumber(sub, "load_kw", 0) / 1000).toFixed(0)} MW`,
      tone: active === "grid_curtailment" || active === "trolley_assist" ? "warn" : "muted",
      hidden: active !== "grid_curtailment" && active !== "trolley_assist"
    });
    const radar = things[NS + "slope-radar-01"];
    const tarp = featureString(radar, "tarp_level", "green");
    m.set("radar", {
      text: `Slope radar: ${tarp.toUpperCase()}`,
      sub: `${featureNumber(radar, "velocity_mmday", 0).toFixed(0)} mm/day`,
      tone: tarp === "red" ? "bad" : "warn",
      hidden: tarp === "green"
    });
    const closed = featureNumber(things[NS + "road-ramp-ore-up"], "closed", 0) === 1;
    m.set("mainramp", {
      text: closed ? "Main ramp CLOSED" : active === "trolley_assist" ? "Main ramp · trolley line ON" : "Main ore ramp",
      tone: closed ? "bad" : active === "trolley_assist" ? "warn" : "muted"
    });
    m.set("altramp", { text: closed ? "West ramp (ore detour)" : "West ramp (waste)", tone: closed ? "warn" : "muted" });
    return m;
  }, [things, kpi, active]);

  return (
    <div className="scene-labels" aria-label="Asset labels">
      {LABEL_DEFS.map((d) => {
        const v = views.get(d.key);
        if (!v || v.hidden) return null;
        return (
          <button
            key={d.key}
            type="button"
            className={`scene-label tone-${v.tone}`}
            style={{ visibility: "hidden" }}
            ref={(el) => {
              if (el) registry.set(d.key, { el, anchor: d.anchor });
              else registry.delete(d.key);
            }}
            onClick={() => d.thingId && onSelect(d.thingId)}
            aria-label={`${v.text}${v.sub ? `, ${v.sub}` : ""}${d.thingId ? " - show live twin data" : ""}`}
          >
            {v.dot && <span className="scene-label-dot" style={{ background: v.dot }} aria-hidden="true" />}
            <span className="scene-label-text">{v.text}</span>
            {v.sub && <span className="scene-label-sub">{v.sub}</span>}
          </button>
        );
      })}
    </div>
  );
}
