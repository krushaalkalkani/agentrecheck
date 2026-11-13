"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export type RunPoint = {
  label: string;
  passed: number;
  failed: number;
  costUsd: number;
  latencyMs: number;
};

const axis = { stroke: "var(--muted-foreground)", fontSize: 11, tickLine: false, axisLine: false };
const tooltip = {
  contentStyle: {
    background: "var(--popover)",
    border: "1px solid var(--border)",
    borderRadius: 8,
    fontSize: 12,
  },
  labelStyle: { color: "var(--muted-foreground)" },
  cursor: { fill: "var(--muted)", opacity: 0.4 },
};

function ChartCard({ title, children }: { title: string; children: React.ReactElement }) {
  return (
    <div className="rounded-xl border bg-card p-4">
      <h3 className="mb-3 text-sm font-medium">{title}</h3>
      <div className="h-44">
        <ResponsiveContainer width="100%" height="100%">
          {children}
        </ResponsiveContainer>
      </div>
    </div>
  );
}

/** Pass/fail history plus cost and latency trends, oldest run on the left. */
export function RunCharts({ data }: { data: RunPoint[] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <ChartCard title="Pass / fail per run">
        <BarChart data={data} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="label" {...axis} minTickGap={24} />
          <YAxis allowDecimals={false} {...axis} />
          <Tooltip {...tooltip} />
          <Bar isAnimationActive={false} dataKey="passed" name="Passed" stackId="a" fill="var(--pass)" radius={[0, 0, 2, 2]} />
          <Bar isAnimationActive={false} dataKey="failed" name="Failed" stackId="a" fill="var(--fail)" radius={[2, 2, 0, 0]} />
        </BarChart>
      </ChartCard>
      <ChartCard title="Total cost per run (USD)">
        <LineChart data={data} margin={{ top: 4, right: 8, left: 4, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="label" {...axis} minTickGap={24} />
          <YAxis {...axis} width={56} tickFormatter={(v: number) => `$${v.toFixed(4)}`} />
          <Tooltip {...tooltip} formatter={(v) => [`$${Number(v).toFixed(5)}`, "Cost"]} />
          <Line isAnimationActive={false} dataKey="costUsd" stroke="var(--brand)" strokeWidth={2} dot={{ r: 2 }} />
        </LineChart>
      </ChartCard>
      <ChartCard title="Average latency per case (ms)">
        <LineChart data={data} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--border)" />
          <XAxis dataKey="label" {...axis} minTickGap={24} />
          <YAxis {...axis} />
          <Tooltip {...tooltip} formatter={(v) => [`${Math.round(Number(v))} ms`, "Latency"]} />
          <Line isAnimationActive={false} dataKey="latencyMs" stroke="oklch(0.75 0.14 235)" strokeWidth={2} dot={{ r: 2 }} />
        </LineChart>
      </ChartCard>
    </div>
  );
}
