import type { Speaker } from "@rdc/domain";

export interface ImportedTranscriptSegment {
  speaker: Speaker;
  text: string;
  speaker_id?: string;
  speaker_name?: string;
  speaker_source: "manual";
}

const SPEAKERS = new Set<Speaker>(["facilitator", "customer", "participant", "system", "unknown"]);

const FACILITATOR_LABELS = new Set([
  "facilitator",
  "interviewer",
  "host",
  "moderator",
  "sales",
  "salesperson",
  "rep",
  "se",
]);

const CUSTOMER_LABELS = new Set(["customer", "client", "prospect", "buyer", "respondent"]);

function identityForLabel(
  label: string,
): Pick<ImportedTranscriptSegment, "speaker" | "speaker_id" | "speaker_name"> {
  const normalized = label.trim().toLowerCase();
  const speaker = FACILITATOR_LABELS.has(normalized)
    ? "facilitator"
    : CUSTOMER_LABELS.has(normalized)
      ? "customer"
      : "participant";
  return {
    speaker,
    speaker_id: `import:${normalized.replace(/[^a-z0-9]+/g, "-")}`,
    speaker_name: label.trim(),
  };
}

function parseJsonSegment(value: unknown, index: number): ImportedTranscriptSegment {
  if (typeof value === "string") {
    const text = value.trim();
    if (!text) throw new Error(`Transcript segment ${index + 1} is empty`);
    return { speaker: "participant", text, speaker_source: "manual" };
  }
  if (value == null || typeof value !== "object") {
    throw new Error(`Transcript segment ${index + 1} must be text or an object`);
  }

  const item = value as Record<string, unknown>;
  const text = typeof item.text === "string" ? item.text.trim() : "";
  if (!text) throw new Error(`Transcript segment ${index + 1} needs text`);
  const rawSpeaker = typeof item.speaker === "string" ? item.speaker.toLowerCase() : "participant";
  const speaker = SPEAKERS.has(rawSpeaker as Speaker) ? (rawSpeaker as Speaker) : "participant";
  const speakerName = typeof item.speaker_name === "string" ? item.speaker_name.trim() : "";
  const speakerId = typeof item.speaker_id === "string" ? item.speaker_id.trim() : "";

  return {
    speaker,
    text,
    speaker_source: "manual",
    ...(speakerName ? { speaker_name: speakerName } : {}),
    ...(speakerId ? { speaker_id: speakerId } : {}),
  };
}

function parseJsonTranscript(contents: string): ImportedTranscriptSegment[] {
  const parsed: unknown = JSON.parse(contents);
  const values =
    parsed != null && typeof parsed === "object" && !Array.isArray(parsed)
      ? (parsed as Record<string, unknown>).segments
      : parsed;
  if (!Array.isArray(values)) {
    throw new Error("JSON transcripts must be an array or contain a segments array");
  }
  return values.map(parseJsonSegment);
}

function parseTextTranscript(contents: string): ImportedTranscriptSegment[] {
  const segments: ImportedTranscriptSegment[] = [];
  const timestamp = /^\[?\d{1,2}:\d{2}(?::\d{2}(?:[.,]\d{1,3})?)?\]?\s*/;
  const subtitleTimestamp = /^\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3}\s+-->\s+/;

  for (const rawLine of contents.replace(/\r\n?/g, "\n").split("\n")) {
    const line = rawLine.trim();
    if (!line || line === "WEBVTT" || /^\d+$/.test(line) || subtitleTimestamp.test(line)) continue;

    const withoutTimestamp = line.replace(timestamp, "").trim();
    const labeled = withoutTimestamp.match(/^([^:]{1,80}):\s*(.+)$/);
    if (labeled) {
      const [, label = "Participant", text = ""] = labeled;
      segments.push({
        ...identityForLabel(label),
        text: text.trim(),
        speaker_source: "manual",
      });
    } else {
      segments.push({
        speaker: "participant",
        text: withoutTimestamp,
        speaker_source: "manual",
      });
    }
  }
  return segments;
}

export function parseTranscriptFile(
  contents: string,
  filename: string,
): ImportedTranscriptSegment[] {
  let segments: ImportedTranscriptSegment[];
  if (filename.toLowerCase().endsWith(".json")) {
    segments = parseJsonTranscript(contents);
  } else {
    segments = parseTextTranscript(contents);
  }
  if (segments.length === 0) throw new Error("The transcript file did not contain any dialogue");
  return segments;
}
