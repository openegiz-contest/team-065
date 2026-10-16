import { useEffect, useState } from "react";
import { useMineStore, mineTimeNow } from "../store/useMineStore";
import { hourOfDay } from "./Header";

/**
 * Light of day over the 3D view, from the mine clock: full daylight 07:00-18:00, dusk and dawn
 * fades, a light night tint 21:00-05:00 (kept subtle so the scene stays readable). Sits above
 * the canvas and below the labels; ignores the pointer.
 */
export function DayNight() {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 2000);
    return () => clearInterval(id);
  }, []);
  const h = mineTimeNow(useMineStore.getState());
  if (h === null) return null;
  const hour = hourOfDay(h);
  let night = 0;
  if (hour >= 21 || hour < 5) night = 1;
  else if (hour >= 18) night = (hour - 18) / 3;
  else if (hour < 7) night = 1 - (hour - 5) / 2;
  const alpha = 0.24 * night;
  if (alpha <= 0.005) return null;
  return (
    <div
      className="day-night"
      aria-hidden="true"
      style={{ background: `rgba(12, 22, 48, ${alpha.toFixed(3)})` }}
      title={night >= 1 ? "Night shift" : "Dusk / dawn"}
    />
  );
}
