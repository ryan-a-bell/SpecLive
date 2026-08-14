"use client";

import { useConversationGraph, useScriptState } from "@/lib/hooks";
import { useWorkspaceStore } from "@/lib/store";

/**
 * Git-style conversation view: the script is the main branch; customer answers
 * branch into follow-ups that merge back as findings/requirements.
 */
export function GitBranchView({ sessionId }: { sessionId: string }) {
  const graph = useConversationGraph(sessionId);
  const script = useScriptState(sessionId);
  const selectArtifact = useWorkspaceStore((s) => s.selectArtifact);
  const selectSegment = useWorkspaceStore((s) => s.selectSegment);

  const stages = script.data?.script.stages ?? [];
  const currentIndex = script.data?.current_index ?? 0;
  const stageSeq = new Map(stages.map((s, i) => [s.id, i]));

  const branches = (graph.data?.branches ?? []).filter((b) => b.topic !== "main_script");
  const columns = Math.max(stages.length, 7);

  return (
    <div className="git-canvas">
      {/* Main script lane */}
      <div className="git-grid" style={{ gridTemplateColumns: `120px repeat(${columns}, 150px)` }}>
        <div className="lane-label">Main script</div>
        {stages.map((stage, i) => (
          <div className="commit" key={stage.id}>
            <div
              className={`commit-node ${i < currentIndex ? "done" : i === currentIndex ? "current" : ""}`}
            >
              <div className="id">S{i + 1}</div>
              <div className="title">{stage.title}</div>
              <div className="state">
                {i < currentIndex ? "Answered" : i === currentIndex ? "Current anchor" : "Planned"}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Side branches */}
      {branches.map((branch) => {
        const offset = (branch.source_stage_id && stageSeq.get(branch.source_stage_id)) || 2;
        const nodes = branch.nodes ?? [];
        return (
          <div
            className="branch-lane"
            key={branch.id}
            style={{ gridTemplateColumns: `120px repeat(${columns}, 150px)` }}
          >
            <div className="lane-label">{branch.name}</div>
            {Array.from({ length: columns }).map((_, col) => {
              const node = nodes[col - offset];
              const started = col >= offset && col < offset + nodes.length;
              return (
                <div key={col} className={`branch-cell ${started ? "line" : ""}`}>
                  {node && (
                    <button
                      className={`branch-node ${node.node_type}`}
                      onClick={() => {
                        if (node.artifact_id) selectArtifact(node.artifact_id);
                        if (node.transcript_segment_id) selectSegment(node.transcript_segment_id);
                      }}
                    >
                      <div className="title">{node.label}</div>
                      <div className="meta">
                        {node.artifact_id ?? node.transcript_segment_id ?? node.node_type}
                      </div>
                    </button>
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
