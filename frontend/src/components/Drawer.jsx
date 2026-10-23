import React, { useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";

// Slide-over panel from the right. Escape closes; focus moves inside on open.
export default function Drawer({ open, onClose, labelledBy, children, className = "", width }) {
  const ref = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const prev = document.activeElement;
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    setTimeout(() => ref.current?.querySelector("button, input, textarea, select")?.focus(), 50);
    return () => { window.removeEventListener("keydown", onKey); prev?.focus?.(); };
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="overlay" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
          <motion.aside
            ref={ref}
            className={`drawer ${className}`}
            style={width ? { width } : undefined}
            role="dialog"
            aria-modal="true"
            aria-labelledby={labelledBy}
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 380, damping: 38 }}
          >
            {children}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
