import React, { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "framer-motion";

// Counts up from 0 on mount and animates from the previous value on change.
export default function AnimatedNumber({ value, decimals = 0, duration = 0.9, className }) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(reduce ? value : 0);
  const from = useRef(reduce ? value : 0);

  useEffect(() => {
    if (value == null || Number.isNaN(Number(value))) return undefined;
    if (reduce) {
      setDisplay(value);
      from.current = value;
      return undefined;
    }
    const controls = animate(from.current, Number(value), {
      duration,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setDisplay(v),
    });
    from.current = Number(value);
    return () => controls.stop();
  }, [value, reduce, duration]);

  if (value == null) return <span className={className}>—</span>;
  return (
    <span className={className}>
      {Number(display).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}
    </span>
  );
}
