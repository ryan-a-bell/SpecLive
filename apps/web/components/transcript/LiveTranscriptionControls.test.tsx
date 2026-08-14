import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi } from "vitest";
import { LiveTranscriptionControls } from "./LiveTranscriptionControls";

vi.mock("@/lib/hooks", async () => {
  const actual = await vi.importActual<typeof import("@/lib/hooks")>("@/lib/hooks");
  return {
    ...actual,
    useTranscriptionCapability: () => ({
      data: {
        available: false,
        supports_partials: false,
        supports_speaker_detection: false,
        audio: { encoding: "pcm_s16le", sample_rate: 16000, channels: 1 },
        max_frame_seconds: 5,
      },
      isLoading: false,
    }),
  };
});

describe("LiveTranscriptionControls", () => {
  it("disables recording when the service reports unavailable", () => {
    const client = new QueryClient();
    render(
      <QueryClientProvider client={client}>
        <LiveTranscriptionControls sessionId="SESSION" />
      </QueryClientProvider>,
    );

    expect(screen.getByRole("button", { name: "Start live transcription" })).toBeDisabled();
    expect(screen.getByText("Transcription unavailable")).toBeInTheDocument();
  });
});
