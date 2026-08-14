"use client";

import { coverageClass } from "@rdc/ui";
import { useCoverage } from "@/lib/hooks";

/**
 * Coverage matrix: discovery-script stages (columns) × conversation branches
 * (rows). Cell shading reflects the coverage state.
 */
export function CoverageMatrix({ sessionId }: { sessionId: string }) {
  const coverage = useCoverage(sessionId);
  if (!coverage.data) return <p className="text-xs text-[var(--muted)]">Loading coverage…</p>;

  const { stages, rows } = coverage.data;

  return (
    <div className="overflow-x-auto">
      <table className="matrix">
        <thead>
          <tr>
            <th>Conversation branch</th>
            {stages.map((s) => (
              <th key={s.id}>{s.title}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.branch_id}>
              <td className="rowhead">{row.branch}</td>
              {row.cells.map((cell) => (
                <td key={cell.stage_id} className={coverageClass[cell.state] ?? ""}>
                  {cell.title && <div className="cell-title">{cell.title}</div>}
                  {cell.meta && <div className="cell-meta">{cell.meta}</div>}
                  {!cell.title && cell.state !== "unanswered" && (
                    <div className="cell-title capitalize">{cell.state.replace(/_/g, " ")}</div>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
