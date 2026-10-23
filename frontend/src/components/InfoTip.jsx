import React, { useId, useState } from "react";
import { Info } from "lucide-react";

// Small "i" button that reveals a tooltip on hover, focus or tap.
export default function InfoTip({ children, label = "More information" }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span
      className="infotip"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        className="infotip-btn"
        aria-label={label}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((v) => !v)}
      >
        <Info size={13} aria-hidden="true" />
      </button>
      {open && (
        <span role="tooltip" id={id} className="infotip-body">
          {children}
        </span>
      )}
    </span>
  );
}
