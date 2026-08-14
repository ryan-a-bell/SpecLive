"use client";

import { useDiscoveryTree } from "@/lib/hooks";
import { Panel } from "@/components/ui/Panel";
import { TreeNodeRow } from "./TreeNode";

export function DiscoveryTree({ sessionId }: { sessionId: string }) {
  const tree = useDiscoveryTree(sessionId);
  return (
    <Panel
      title="Live discovery tree"
      subtitle="Nodes populate and strengthen as evidence accumulates"
      aside={<span className="status">Auto-linking on</span>}
      className="min-h-[320px]"
    >
      {tree.isLoading && <p className="text-xs text-[var(--muted)]">Loading tree…</p>}
      {tree.data?.roots.map((root) => (
        <TreeNodeRow key={root.id} node={root} />
      ))}
      {tree.data && tree.data.roots.length === 0 && (
        <p className="text-xs text-[var(--muted)]">
          No artifacts yet. Add a statement and analyze to populate the tree.
        </p>
      )}
    </Panel>
  );
}
