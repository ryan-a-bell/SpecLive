"use client";

import type { EvidenceLink } from "@rdc/domain";

interface EvidenceTextProps {
  text: string;
  links: EvidenceLink[];
  onSelect: (artifactId: string) => void;
}

/**
 * Renders a transcript segment's text with the exact evidence spans
 * highlighted. Relationship (direct / supporting / contradicting / superseding
 * / contextual) drives the highlight color. Replaces the prototype's static
 * `<span class="evidence ...">` markup.
 */
export function EvidenceText({ text, links, onSelect }: EvidenceTextProps) {
  const spans = [...links]
    .filter((l) => l.quote_start >= 0 && l.quote_end <= text.length && l.quote_end > l.quote_start)
    .sort((a, b) => a.quote_start - b.quote_start);

  const parts: JSX.Element[] = [];
  let cursor = 0;
  spans.forEach((link, i) => {
    if (link.quote_start < cursor) return; // skip overlaps
    if (link.quote_start > cursor) {
      parts.push(<span key={`t-${i}`}>{text.slice(cursor, link.quote_start)}</span>);
    }
    parts.push(
      <span
        key={link.id}
        className={`evidence ${link.relationship}`}
        role="button"
        tabIndex={0}
        title={`${link.relationship} evidence`}
        onClick={() => onSelect(link.artifact_id)}
        onKeyDown={(e) => e.key === "Enter" && onSelect(link.artifact_id)}
      >
        {text.slice(link.quote_start, link.quote_end)}
      </span>,
    );
    cursor = link.quote_end;
  });
  if (cursor < text.length) parts.push(<span key="tail">{text.slice(cursor)}</span>);

  return <div className="text-[13px] leading-relaxed text-[#dfe8f4]">{parts}</div>;
}
