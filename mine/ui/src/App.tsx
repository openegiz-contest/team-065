import { useEffect, useState } from "react";
import { Scene, type ViewName } from "./three/Scene";
import { SceneLabels } from "./three/Labels";
import { Header } from "./components/Header";
import { KpiPanel } from "./components/KpiPanel";
import { BaselineDelta } from "./components/BaselineDelta";
import { EventLog } from "./components/EventLog";
import { ScenarioPanel } from "./components/ScenarioPanel";
import { ScenarioBanner } from "./components/ScenarioBanner";
import { Minimap } from "./components/Minimap";
import { Inspector } from "./components/Inspector";
import { TrendChart } from "./components/TrendChart";
import { TwinModel } from "./components/TwinModel";
import { DayNight } from "./components/DayNight";
import { useMineStore } from "./store/useMineStore";

const VIEW_BUTTONS: { id: ViewName; label: string }[] = [
  { id: "overview", label: "Whole site" },
  { id: "pit", label: "Pit" },
  { id: "plant", label: "Plant" }
];

export default function App() {
  const init = useMineStore((s) => s.init);
  const [selectedId, setSelectedId] = useState("");
  const [view, setView] = useState<ViewName>("overview");
  const [viewNonce, setViewNonce] = useState(0);
  const [showMap, setShowMap] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [showModel, setShowModel] = useState(false);

  useEffect(() => {
    init();
  }, [init]);

  return (
    <div className="app-root">
      <Header />
      <main className="app-main">
        <aside className="col-left" aria-label="Scenario controls">
          <ScenarioPanel />
        </aside>

        <div className="col-center">
          <div className="scene-wrap">
            <Scene onSelect={setSelectedId} view={view} viewNonce={viewNonce} />
            <DayNight />
            {showLabels && <SceneLabels onSelect={setSelectedId} />}
            <ScenarioBanner />
            <div className="view-controls" role="toolbar" aria-label="3D view controls">
              {VIEW_BUTTONS.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  aria-pressed={view === b.id}
                  onClick={() => {
                    setView(b.id);
                    setViewNonce((n) => n + 1);
                  }}
                >
                  {b.label}
                </button>
              ))}
              <button type="button" aria-pressed={showLabels} onClick={() => setShowLabels((v) => !v)}>
                Labels
              </button>
              <button type="button" aria-pressed={showMap} onClick={() => setShowMap((v) => !v)}>
                Map
              </button>
              <button type="button" aria-pressed={showModel} onClick={() => setShowModel((v) => !v)}>
                Twin model
              </button>
            </div>
            {showMap && (
              <div className="minimap-overlay">
                <Minimap onSelect={setSelectedId} />
              </div>
            )}
            {showModel && (
              <TwinModel
                onSelect={(id) => {
                  setSelectedId(id);
                }}
                onClose={() => setShowModel(false)}
              />
            )}
            <Inspector selectedId={selectedId} onClear={() => setSelectedId("")} />
            <p className="scene-hint">Drag to orbit · scroll to zoom · click a truck, shovel, plant item or label for live twin data</p>
          </div>
          <EventLog />
        </div>

        <aside className="col-right" aria-label="KPIs and baseline comparison">
          <KpiPanel />
          <BaselineDelta />
          <TrendChart />
        </aside>
      </main>
    </div>
  );
}
