import { describe, expect, it } from "vitest";
import { parseTranscriptFile } from "./transcript-import";

describe("parseTranscriptFile", () => {
  it("maps labeled plain-text dialogue to speaker roles", () => {
    const segments = parseTranscriptFile(
      "Facilitator: What matters most?\nCustomer: Faster fulfillment.\nJordan: Fewer errors.",
      "call.txt",
    );

    expect(segments).toEqual([
      expect.objectContaining({ speaker: "facilitator", text: "What matters most?" }),
      expect.objectContaining({ speaker: "customer", text: "Faster fulfillment." }),
      expect.objectContaining({
        speaker: "participant",
        speaker_name: "Jordan",
        text: "Fewer errors.",
      }),
    ]);
  });

  it("accepts exported JSON transcript segments", () => {
    const segments = parseTranscriptFile(
      JSON.stringify({
        segments: [{ speaker: "customer", speaker_name: "Maya", text: "We need live status." }],
      }),
      "call.json",
    );

    expect(segments[0]).toEqual({
      speaker: "customer",
      speaker_name: "Maya",
      speaker_source: "manual",
      text: "We need live status.",
    });
  });

  it("rejects empty transcripts", () => {
    expect(() => parseTranscriptFile("\n\n", "call.txt")).toThrow("did not contain any dialogue");
  });
});
