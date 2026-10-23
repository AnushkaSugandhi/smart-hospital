import React from "react";

// Very subtle heartbeat line drifting behind the app. Purely decorative;
// the CSS animation is disabled under prefers-reduced-motion.
export default function EcgBackground() {
  const beat = "h60 l8 -18 l8 36 l8 -48 l8 30 l6 0 h70";
  const path = `M0 60 ${Array.from({ length: 8 }, () => beat).join(" ")}`;
  return (
    <div className="ecg-bg" aria-hidden="true">
      <div className="ecg-glow" />
      <svg className="ecg-line" viewBox="0 0 1344 120" preserveAspectRatio="none">
        <path d={path} />
      </svg>
    </div>
  );
}
