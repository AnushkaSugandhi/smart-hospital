import { useEffect, useState } from "react";

const TOKENS = ["series-1", "series-2", "grid", "axis", "muted", "text", "text-2", "surface-solid", "accent",
  "status-good", "status-warning", "status-critical"];

function read() {
  const css = getComputedStyle(document.documentElement);
  return Object.fromEntries(TOKENS.map((t) => [t, css.getPropertyValue(`--${t}`).trim()]));
}

// Resolved colour tokens for libraries that need literal colours (Recharts
// sets SVG attributes). Re-reads when the theme attribute changes.
export default function useThemeColors() {
  const [colors, setColors] = useState(read);
  useEffect(() => {
    const observer = new MutationObserver(() => setColors(read()));
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);
  return colors;
}
