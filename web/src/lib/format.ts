export function fmtCost(value: number): string {
  if (value === 0) return "$0";
  return value < 0.01 ? `$${value.toFixed(5)}` : `$${value.toFixed(3)}`;
}

export function fmtMs(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(2)}s` : `${Math.round(value)}ms`;
}

/** Fixed locale and time zone so server and client render the same string. */
const dateFormat = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
  timeZone: "UTC",
});

export function fmtDate(value: Date | string): string {
  return `${dateFormat.format(new Date(value))} UTC`;
}

export function fmtShortDate(value: Date | string): string {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", timeZone: "UTC" }).format(
    new Date(value),
  );
}

/** Percentage change vs a baseline, or null when there is nothing to compare. */
export function pctDelta(actual: number, baseline: number | null): number | null {
  if (baseline === null || baseline <= 0) return null;
  return ((actual - baseline) / baseline) * 100;
}

export function fmtPct(value: number | null): string {
  if (value === null) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(0)}%`;
}

export type DiffRow = { marker: " " | "-" | "+"; value: string };

/** Line diff of two tool sequences using a longest-common-subsequence table. */
export function sequenceDiff(baseline: string[], actual: string[]): DiffRow[] {
  const m = baseline.length;
  const n = actual.length;
  const lcs = Array.from({ length: m + 1 }, () => new Array<number>(n + 1).fill(0));
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      lcs[i][j] =
        baseline[i] === actual[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const rows: DiffRow[] = [];
  let i = 0;
  let j = 0;
  while (i < m && j < n) {
    if (baseline[i] === actual[j]) {
      rows.push({ marker: " ", value: baseline[i] });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      rows.push({ marker: "-", value: baseline[i++] });
    } else {
      rows.push({ marker: "+", value: actual[j++] });
    }
  }
  while (i < m) rows.push({ marker: "-", value: baseline[i++] });
  while (j < n) rows.push({ marker: "+", value: actual[j++] });
  return rows;
}

export function pretty(value: unknown): string {
  if (value === null || value === undefined) return "—";
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}
