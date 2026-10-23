import { useEffect } from "react";

// Adds a subtle ripple to every .btn on click (one delegated listener).
export default function useRipple() {
  useEffect(() => {
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return undefined;
    function onDown(e) {
      const btn = e.target.closest?.(".btn");
      if (!btn || btn.disabled) return;
      const rect = btn.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const span = document.createElement("span");
      span.className = "ripple";
      span.style.width = span.style.height = `${size}px`;
      span.style.left = `${e.clientX - rect.left - size / 2}px`;
      span.style.top = `${e.clientY - rect.top - size / 2}px`;
      btn.appendChild(span);
      setTimeout(() => span.remove(), 650);
    }
    document.addEventListener("pointerdown", onDown);
    return () => document.removeEventListener("pointerdown", onDown);
  }, []);
}
