"use client";

import { ConversationStructure } from "@/components/viz/ConversationStructure";

/** Full-surface conversation-structure views (Q&A / git / subway / coverage). */
export function StructureView({ sessionId }: { sessionId: string }) {
  return (
    <div className="[&>section]:mx-0 [&>section]:mb-0">
      <ConversationStructure sessionId={sessionId} />
    </div>
  );
}
