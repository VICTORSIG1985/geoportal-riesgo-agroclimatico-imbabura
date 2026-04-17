"use client";
import dynamic from "next/dynamic";
import { IR_BY_CULTIVO_SSP_HORIZ, HORIZONTES, CULTIVOS } from "@/data/ranking";
const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const COLORS: Record<string,string> = {
  "SSP1-2.6": "#2166AC",
  "SSP3-7.0": "#EF8A62",
  "SSP5-8.5": "#B2182B",
};

export default function IRChart({ cultivo = "papa" }: { cultivo?: string }) {
  const d: any = (IR_BY_CULTIVO_SSP_HORIZ as any)[cultivo];
  if (!d) return null;
  const traces = Object.keys(d).map(ssp => ({
    x: HORIZONTES, y: d[ssp], name: ssp, mode: "lines+markers",
    line: { color: COLORS[ssp], width: 3 }, marker: { size: 10 },
  }));
  return (
    <Plot
      data={traces as any}
      layout={{
        title: { text: `IR medio provincial — ${cultivo.charAt(0).toUpperCase() + cultivo.slice(1)}` },
        xaxis: { title: { text: "Horizonte" } },
        yaxis: { title: { text: "IR medio" }, range: [0.25, 0.75] },
        margin: { l: 60, r: 20, t: 50, b: 50 },
        autosize: true,
        paper_bgcolor: "#fff", plot_bgcolor: "#F7FAFC",
        font: { family: "Inter, system-ui" },
        legend: { orientation: "h", y: -0.25 },
      } as any}
      config={{ responsive: true, displayModeBar: false } as any}
      style={{ width: "100%", height: 380 }}
      useResizeHandler
    />
  );
}
