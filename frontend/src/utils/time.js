// Backend timestamps are UTC; SQLite returns them without an offset.
export function parseUtc(value) {
  if (!value) return null;
  return new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(value) ? value : `${value}Z`);
}

export const formatUtc = (value) => parseUtc(value)?.toLocaleString() ?? "—";
