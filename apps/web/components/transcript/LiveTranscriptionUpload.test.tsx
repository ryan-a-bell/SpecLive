import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LiveTranscriptionControls } from "./LiveTranscriptionControls";

const uploadRecording = vi.fn().mockResolvedValue({
  session_id: "SESSION",
  source_filename: "call.mp3",
  audio_seconds: 3.2,
  segment_count: 2,
  segments: [],
});
const addSegment = vi.fn().mockResolvedValue({});
const buildConversationGraph = vi.fn().mockResolvedValue({ branches: [] });

vi.mock("@/lib/api", () => ({
  api: {
    uploadRecording: (...args: unknown[]) => uploadRecording(...args),
    addSegment: (...args: unknown[]) => addSegment(...args),
    buildConversationGraph: (...args: unknown[]) => buildConversationGraph(...args),
  },
}));

vi.mock("@/lib/hooks", async () => {
  const actual = await vi.importActual<typeof import("@/lib/hooks")>("@/lib/hooks");
  return {
    ...actual,
    useTranscriptionCapability: () => ({
      data: {
        available: true,
        supports_partials: true,
        supports_speaker_detection: true,
        audio: { encoding: "pcm_s16le", sample_rate: 16000, channels: 1 },
        max_frame_seconds: 5,
      },
      isLoading: false,
    }),
    useSession: () => ({ data: { facilitator: "Ryan", customer: "Acme" } }),
  };
});

function renderControls() {
  const client = new QueryClient();
  const invalidate = vi.spyOn(client, "invalidateQueries").mockResolvedValue();
  render(
    <QueryClientProvider client={client}>
      <LiveTranscriptionControls sessionId="SESSION" />
    </QueryClientProvider>,
  );
  return { invalidate };
}

describe("LiveTranscriptionControls upload", () => {
  beforeEach(() => {
    uploadRecording.mockClear();
    addSegment.mockClear();
    buildConversationGraph.mockClear();
  });

  it("uploads a selected recording through the API and refreshes the transcript", async () => {
    const { invalidate } = renderControls();
    const input = screen.getByTestId("recording-file-input") as HTMLInputElement;

    const file = new File([new Uint8Array([1, 2, 3, 4])], "call.mp3", { type: "audio/mpeg" });
    await userEvent.upload(input, file);

    await waitFor(() => expect(uploadRecording).toHaveBeenCalledTimes(1));
    expect(uploadRecording).toHaveBeenCalledWith(
      "SESSION",
      file,
      expect.objectContaining({ filename: "call.mp3", speakerMode: "auto" }),
    );
    await waitFor(() => expect(invalidate).toHaveBeenCalled());
  });

  it("imports a text transcript in order and rebuilds the conversation graph", async () => {
    const { invalidate } = renderControls();
    const input = screen.getByTestId("transcript-file-input") as HTMLInputElement;
    const file = new File(
      ["Facilitator: What matters most?\nCustomer: Faster fulfillment."],
      "call.txt",
      { type: "text/plain" },
    );
    Object.defineProperty(file, "text", {
      value: () =>
        Promise.resolve("Facilitator: What matters most?\nCustomer: Faster fulfillment."),
    });

    await userEvent.upload(input, file);

    await waitFor(() => expect(addSegment).toHaveBeenCalledTimes(2));
    expect(addSegment).toHaveBeenNthCalledWith(
      1,
      "SESSION",
      expect.objectContaining({ speaker: "facilitator", text: "What matters most?" }),
    );
    expect(addSegment).toHaveBeenNthCalledWith(
      2,
      "SESSION",
      expect.objectContaining({ speaker: "customer", text: "Faster fulfillment." }),
    );
    expect(buildConversationGraph).toHaveBeenCalledWith("SESSION");
    await waitFor(() => expect(invalidate).toHaveBeenCalled());
  });
});
