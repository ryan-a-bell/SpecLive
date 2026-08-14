"use client";

import { useState } from "react";
import type { Speaker, TranscriptSegment } from "@rdc/domain";
import { useCorrectTranscriptSpeaker } from "@/lib/hooks";

const EDITABLE_ROLES: Array<{ value: Speaker; label: string }> = [
  { value: "facilitator", label: "Facilitator" },
  { value: "customer", label: "Customer" },
  { value: "participant", label: "Participant" },
  { value: "unknown", label: "Unknown" },
];

type SpeakerSegment = Omit<TranscriptSegment, "speaker_source"> & {
  speaker_source?: TranscriptSegment["speaker_source"];
};

function defaultName(segment: SpeakerSegment): string {
  return segment.speaker_name ?? segment.speaker.replace("_", " ");
}

export function SpeakerLabelEditor({
  sessionId,
  segment,
}: {
  sessionId: string;
  segment: SpeakerSegment;
}) {
  const correction = useCorrectTranscriptSpeaker(sessionId);
  const [editing, setEditing] = useState(false);
  const [role, setRole] = useState<Speaker>(segment.speaker);
  const [name, setName] = useState(() => defaultName(segment));
  const [applyToVoice, setApplyToVoice] = useState(Boolean(segment.speaker_id));

  async function save() {
    if (!name.trim()) return;
    await correction.mutateAsync({
      segmentId: segment.id,
      speaker: role,
      speaker_name: name.trim(),
      apply_to_voice: applyToVoice,
    });
    setEditing(false);
  }

  if (!editing) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="text-xs font-extrabold hover:text-[var(--blue)]"
          onClick={() => setEditing(true)}
          aria-label={`Correct speaker ${defaultName(segment)}`}
        >
          {defaultName(segment)}
        </button>
        <span className="rounded-full border border-[var(--border)] px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-[var(--muted)]">
          {segment.speaker_source === "detected" ? "Auto" : (segment.speaker_source ?? "unknown")}
        </span>
        {segment.speaker_confidence != null ? (
          <span className="text-[9px] text-[var(--muted)]">
            {Math.round(segment.speaker_confidence * 100)}%
          </span>
        ) : null}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2 rounded-md border border-[var(--border)] bg-[#0b1525] p-2">
      <label className="sr-only" htmlFor={`speaker-role-${segment.id}`}>
        Speaker role
      </label>
      <select
        id={`speaker-role-${segment.id}`}
        className="rounded border border-[var(--border)] bg-[#101d30] px-2 py-1 text-[11px]"
        value={role}
        onChange={(event) => setRole(event.target.value as Speaker)}
      >
        {EDITABLE_ROLES.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <label className="sr-only" htmlFor={`speaker-name-${segment.id}`}>
        Speaker name
      </label>
      <input
        id={`speaker-name-${segment.id}`}
        className="min-w-28 rounded border border-[var(--border)] bg-[#101d30] px-2 py-1 text-[11px]"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      {segment.speaker_id ? (
        <label className="flex items-center gap-1 text-[10px] text-[var(--muted)]">
          <input
            type="checkbox"
            checked={applyToVoice}
            onChange={(event) => setApplyToVoice(event.target.checked)}
          />
          Apply to this voice
        </label>
      ) : null}
      <button type="button" className="btn primary" onClick={save} disabled={correction.isPending}>
        Save
      </button>
      <button type="button" className="btn" onClick={() => setEditing(false)}>
        Cancel
      </button>
    </div>
  );
}
