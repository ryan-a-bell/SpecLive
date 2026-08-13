"use client";

import { useConversationGraph, useScriptState } from "@/lib/hooks";

const ROUTE_CLASS: Record<string, string> = {
  main_script: "route-main",
  states_exceptions: "route-main",
  device: "route-device",
  integration: "route-integration",
  offline: "route-offline",
};

/**
 * Conversation subway: persistent topic routes with transfer points where a
 * branch reconnects to the script or shares evidence with another branch.
 */
export function SubwayView({ sessionId }: { sessionId: string }) {
  const graph = useConversationGraph(sessionId);
  const script = useScriptState(sessionId);

  const stages = script.data?.script.stages ?? [];
  const columns = Math.max(stages.length, 7);
  const stageSeq = new Map(stages.map((s, i) => [s.id, i]));
  const branches = graph.data?.branches ?? [];

  const gridStyle = { gridTemplateColumns: `160px repeat(${columns}, 1fr)` };

  return (
    <div className="subway">
      {/* Main discovery line */}
      <div className="station-row route-main" style={gridStyle}>
        <div className="route-name">Main discovery line</div>
        {stages.map((stage) => (
          <div className="station filled" key={stage.id}>
            <i />
            <strong>{stage.title}</strong>
          </div>
        ))}
        {Array.from({ length: columns - stages.length }).map((_, i) => (
          <div className="station" key={`pad-${i}`} />
        ))}
      </div>

      {/* Topic routes */}
      {branches
        .filter((b) => b.topic !== "main_script")
        .map((branch) => {
          const offset = (branch.source_stage_id && stageSeq.get(branch.source_stage_id)) || 2;
          const routeClass = ROUTE_CLASS[branch.topic] ?? "route-integration";
          const nodes = branch.nodes ?? [];
          return (
            <div className={`station-row ${routeClass}`} style={gridStyle} key={branch.id}>
              <div className="route-name">{branch.name}</div>
              {Array.from({ length: columns }).map((_, col) => {
                const node = nodes[col - offset];
                return (
                  <div key={col} className={`station ${node ? "filled" : ""}`}>
                    {node && (
                      <>
                        <i />
                        <strong>{node.label}</strong>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
    </div>
  );
}
