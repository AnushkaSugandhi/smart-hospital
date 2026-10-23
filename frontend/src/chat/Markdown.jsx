import React from "react";

// Minimal, safe renderer for assistant answers: paragraphs, "- " bullets,
// **bold** and [S1] citation markers. Builds React nodes (no innerHTML).
function inline(text, onCite, keyBase) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\[S\d+\])/g;
  let last = 0;
  let m;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const token = m[0];
    if (token.startsWith("**")) out.push(<strong key={`${keyBase}-b${i++}`}>{token.slice(2, -2)}</strong>);
    else {
      const ref = token.slice(1, -1);
      out.push(
        <button key={`${keyBase}-c${i++}`} type="button" className="cite" onClick={() => onCite?.(ref)} aria-label={`Source ${ref}`}>
          {ref}
        </button>,
      );
    }
    last = m.index + token.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export default function Markdown({ text, onCite }) {
  const blocks = text.split(/\n{2,}/);
  return (
    <div className="md">
      {blocks.map((block, bi) => {
        const lines = block.split("\n").filter((l) => l.trim());
        if (lines.length && lines.every((l) => /^\s*[-•]\s+/.test(l))) {
          return (
            <ul key={bi}>
              {lines.map((l, li) => <li key={li}>{inline(l.replace(/^\s*[-•]\s+/, ""), onCite, `${bi}-${li}`)}</li>)}
            </ul>
          );
        }
        return <p key={bi}>{lines.map((l, li) => <React.Fragment key={li}>{li > 0 && <br />}{inline(l, onCite, `${bi}-${li}`)}</React.Fragment>)}</p>;
      })}
    </div>
  );
}
