import { ReactNode } from "react";
import { Series } from "../../api";
import { useFilters } from "../../state/FiltersContext";

type Props = {
  title: string; meta?: ReactNode; spanClass: string; tall?: boolean;
  csvKey?: string; csvData?: Series[]; children: ReactNode;
};

export default function Card({ title, meta, spanClass, tall, csvKey, csvData, children }: Props) {
  const { state } = useFilters();
  const download = () => {
    if (!csvData?.length || !csvKey) return;
    const cols = Object.keys(csvData[0]);
    const csv = [
      cols.join(","),
      ...csvData.map((r) => cols.map((c) => `"${String((r as any)[c] ?? "").replace(/"/g, '""')}"`).join(",")),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url; a.download = `${csvKey}_${state.season}.csv`; a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div className={`card ${spanClass}${tall ? " tall" : ""}`}>
      <div className="card-h">
        <span className="lbl">{title}</span>
        {meta != null && <span className="meta">{meta}</span>}
      </div>
      <div className="chart">{children}</div>
      {csvData && csvData.length > 0 && (
        <button className="dl" title="Download CSV" onClick={(e) => { e.stopPropagation(); download(); }}>⤓</button>
      )}
    </div>
  );
}
