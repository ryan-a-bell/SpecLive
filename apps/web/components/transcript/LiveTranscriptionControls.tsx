"use client";

import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { TranscriptionServerFrame } from "@rdc/domain";
import { api } from "@/lib/api";
import { calculateRms, PcmFrameEncoder } from "@/lib/audio";
import { queryKeys, useSession, useTranscriptionCapability } from "@/lib/hooks";
import { useToast } from "@/lib/toast";
import { parseTranscriptFile } from "@/lib/transcript-import";

type CapturePhase = "idle" | "requesting" | "recording" | "stopping" | "error";

export function LiveTranscriptionControls({ sessionId }: { sessionId: string }) {
  const capability = useTranscriptionCapability();
  const session = useSession(sessionId);
  const queryClient = useQueryClient();
  const toast = useToast((state) => state.show);
  const [phase, setPhase] = useState<CapturePhase>("idle");
  const [level, setLevel] = useState(0);
  const [partialText, setPartialText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [autoDetect, setAutoDetect] = useState(true);
  const [manualSpeaker, setManualSpeaker] = useState<"facilitator" | "customer" | "participant">(
    "facilitator",
  );
  const [manualName, setManualName] = useState("");
  const [partialSpeaker, setPartialSpeaker] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [importingTranscript, setImportingTranscript] = useState(false);
  const recordingInputRef = useRef<HTMLInputElement | null>(null);
  const transcriptInputRef = useRef<HTMLInputElement | null>(null);
  const phaseRef = useRef<CapturePhase>("idle");
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorRef = useRef<AudioWorkletNode | null>(null);
  const encoderRef = useRef<PcmFrameEncoder | null>(null);
  const partialsRef = useRef(new Map<string, string>());

  function transition(next: CapturePhase) {
    phaseRef.current = next;
    setPhase(next);
  }

  async function releaseAudio() {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    processorRef.current = null;
    sourceRef.current = null;
    streamRef.current = null;
    const context = contextRef.current;
    contextRef.current = null;
    if (context && context.state !== "closed") await context.close();
    setLevel(0);
  }

  function fail(message: string) {
    setError(message);
    transition("error");
    toast(message);
  }

  // The name to attribute manual-mode segments to: an explicit override, else
  // the session's facilitator/customer, else a generic fallback per role.
  function resolveSpeakerName(): string {
    const fallback =
      manualSpeaker === "facilitator"
        ? (session.data?.facilitator ?? "Facilitator")
        : manualSpeaker === "customer"
          ? (session.data?.customer ?? "Customer")
          : "Participant";
    return manualName || fallback;
  }

  async function start() {
    if (!capability.data?.available || phaseRef.current === "recording") return;
    setError(null);
    setPartialText("");
    setPartialSpeaker(null);
    partialsRef.current.clear();
    transition("requesting");

    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true },
      });
      streamRef.current = mediaStream;
      const context = new AudioContext();
      contextRef.current = context;
      encoderRef.current = new PcmFrameEncoder(context.sampleRate);
      await context.audioWorklet.addModule("/audio-processor.js");

      const socket = new WebSocket(api.transcriptionSocketUrl(sessionId));
      socketRef.current = socket;
      await new Promise<void>((resolve, reject) => {
        let settled = false;
        const rejectReady = (message: string) => {
          if (settled) return;
          settled = true;
          window.clearTimeout(timeout);
          reject(new Error(message));
        };
        const timeout = window.setTimeout(
          () => rejectReady("Transcription service did not become ready"),
          10_000,
        );
        socket.onerror = () => rejectReady("Could not connect to transcription service");
        socket.onmessage = (message) => {
          if (typeof message.data !== "string") return;
          let frame: TranscriptionServerFrame;
          try {
            frame = api.parseTranscriptionFrame(message.data);
          } catch {
            if (!settled) rejectReady("Transcription service returned an invalid response");
            else fail("Transcription service returned an invalid response");
            return;
          }
          if (frame.type === "transcription.ready") {
            const speakerName = resolveSpeakerName();
            socket.send(
              JSON.stringify(
                autoDetect
                  ? { type: "configure", speaker_mode: "auto" }
                  : {
                      type: "configure",
                      speaker_mode: "manual",
                      speaker: manualSpeaker,
                      speaker_id: `manual:${manualSpeaker}:${speakerName}`,
                      speaker_name: speakerName,
                    },
              ),
            );
            settled = true;
            window.clearTimeout(timeout);
            resolve();
            return;
          }
          if (frame.type === "transcript.partial") {
            partialsRef.current.set(frame.segment_id, frame.text);
            setPartialText(Array.from(partialsRef.current.values()).join(" "));
            setPartialSpeaker(frame.speaker_name);
            return;
          }
          if (frame.type === "transcript.final") {
            partialsRef.current.delete(frame.segment_id);
            setPartialText(Array.from(partialsRef.current.values()).join(" "));
            if (partialsRef.current.size === 0) setPartialSpeaker(null);
            void queryClient.invalidateQueries({ queryKey: queryKeys.transcript(sessionId) });
            return;
          }
          if (frame.type === "transcription.error") {
            const message = frame.message ?? "Transcription service failed";
            if (!settled) rejectReady(message);
            else {
              fail(message);
              void releaseAudio();
              socket.close();
            }
            return;
          }
          if (frame.type === "transcription.stopped") {
            socket.close();
            socketRef.current = null;
            encoderRef.current = null;
            transition("idle");
          }
        };
        socket.onclose = () => {
          socketRef.current = null;
          if (!settled) rejectReady("Transcription connection closed unexpectedly");
          else if (phaseRef.current === "recording" || phaseRef.current === "requesting") {
            fail("Transcription connection closed unexpectedly");
            void releaseAudio();
          }
        };
      });

      const source = context.createMediaStreamSource(mediaStream);
      const processor = new AudioWorkletNode(context, "speclive-audio-processor");
      const silentOutput = context.createGain();
      silentOutput.gain.value = 0;
      processor.port.onmessage = (message: MessageEvent<Float32Array>) => {
        const samples = message.data;
        setLevel(Math.min(1, calculateRms(samples) * 4));
        const encoder = encoderRef.current;
        const activeSocket = socketRef.current;
        if (!encoder || activeSocket?.readyState !== WebSocket.OPEN) return;
        encoder.push(samples).forEach((frame) => activeSocket.send(frame));
      };
      source.connect(processor);
      processor.connect(silentOutput);
      silentOutput.connect(context.destination);
      sourceRef.current = source;
      processorRef.current = processor;
      transition("recording");
      toast("Live transcription started");
    } catch (caught) {
      await releaseAudio();
      socketRef.current?.close();
      socketRef.current = null;
      const message = caught instanceof Error ? caught.message : "Microphone could not start";
      fail(message);
    }
  }

  async function stop() {
    if (phaseRef.current !== "recording") return;
    transition("stopping");
    const socket = socketRef.current;
    const encoder = encoderRef.current;
    await releaseAudio();
    if (socket?.readyState === WebSocket.OPEN) {
      encoder?.flush().forEach((frame) => socket.send(frame));
      socket.send(JSON.stringify({ type: "stop" }));
    } else {
      encoderRef.current = null;
      transition("idle");
    }
  }

  async function uploadRecording(file: File) {
    if (uploading || phaseRef.current === "recording") return;
    setError(null);
    setUploading(true);
    try {
      const result = await api.uploadRecording(sessionId, file, {
        filename: file.name,
        speakerMode: autoDetect ? "auto" : "manual",
        speaker: autoDetect ? undefined : manualSpeaker,
        speakerName: autoDetect ? undefined : resolveSpeakerName(),
      });
      await queryClient.invalidateQueries({ queryKey: queryKeys.transcript(sessionId) });
      toast(
        result.segment_count > 0
          ? `Transcribed ${file.name} (${result.segment_count} segments)`
          : `Processed ${file.name}, no speech detected`,
      );
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Could not transcribe recording";
      setError(message);
      toast(message);
    } finally {
      setUploading(false);
    }
  }

  async function uploadTranscript(file: File) {
    if (
      importingTranscript ||
      phaseRef.current === "recording" ||
      phaseRef.current === "requesting" ||
      phaseRef.current === "stopping"
    ) {
      return;
    }
    setError(null);
    setImportingTranscript(true);
    try {
      const segments = parseTranscriptFile(await file.text(), file.name);
      // Preserve transcript order: each append receives the next sequence number
      // from the API, so concurrent requests could race one another.
      for (const segment of segments) {
        await api.addSegment(sessionId, segment);
      }
      await api.buildConversationGraph(sessionId);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: queryKeys.transcript(sessionId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.artifacts(sessionId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.sessionEvidence(sessionId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.tree(sessionId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.graph(sessionId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.coverage(sessionId) }),
        queryClient.invalidateQueries({ queryKey: queryKeys.recommendations(sessionId) }),
      ]);
      toast(`Imported ${segments.length} transcript segments from ${file.name}`);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Could not import transcript";
      setError(message);
      toast(message);
    } finally {
      setImportingTranscript(false);
    }
  }

  useEffect(
    () => () => {
      processorRef.current?.disconnect();
      sourceRef.current?.disconnect();
      streamRef.current?.getTracks().forEach((track) => track.stop());
      void contextRef.current?.close();
      socketRef.current?.close();
    },
    [],
  );

  const unavailable = capability.isLoading || !capability.data?.available;
  const busy = phase === "recording" || phase === "requesting" || phase === "stopping";
  const fileBusy = busy || uploading || importingTranscript;
  const statusLabel = capability.isLoading
    ? "Checking transcription…"
    : unavailable
      ? "Transcription unavailable"
      : phase === "recording"
        ? "Listening"
        : phase === "requesting"
          ? "Connecting…"
          : phase === "stopping"
            ? "Finalizing…"
            : "Ready to transcribe";

  return (
    <div className="border-b border-[var(--border)] bg-[rgba(9,19,33,0.72)] px-3 py-2">
      <fieldset className="mb-2 flex flex-wrap items-center gap-2" disabled={fileBusy}>
        <legend className="sr-only">Speaker identification</legend>
        <label className="flex cursor-pointer items-center gap-2 text-[11px] font-semibold">
          <input
            type="checkbox"
            checked={autoDetect}
            onChange={(event) => setAutoDetect(event.target.checked)}
          />
          Auto-detect voices
        </label>
        {autoDetect ? (
          <span className="text-[10px] text-[var(--muted)]">
            {capability.data?.supports_speaker_detection
              ? "Voice identities will be grouped automatically"
              : "Uses detected voice labels when the service provides them"}
          </span>
        ) : (
          <>
            <label className="sr-only" htmlFor="manual-speaker-role">
              Speaker role
            </label>
            <select
              id="manual-speaker-role"
              className="rounded-md border border-[var(--border)] bg-[#0b1525] px-2 py-1 text-[11px]"
              value={manualSpeaker}
              onChange={(event) => {
                const role = event.target.value as typeof manualSpeaker;
                setManualSpeaker(role);
                setManualName(
                  role === "facilitator"
                    ? (session.data?.facilitator ?? "")
                    : role === "customer"
                      ? (session.data?.customer ?? "")
                      : "",
                );
              }}
            >
              <option value="facilitator">Facilitator</option>
              <option value="customer">Customer</option>
              <option value="participant">Participant</option>
            </select>
            <label className="sr-only" htmlFor="manual-speaker-name">
              Speaker name
            </label>
            <input
              id="manual-speaker-name"
              className="min-w-32 rounded-md border border-[var(--border)] bg-[#0b1525] px-2 py-1 text-[11px]"
              value={manualName}
              placeholder={
                manualSpeaker === "facilitator"
                  ? session.data?.facilitator
                  : manualSpeaker === "customer"
                    ? session.data?.customer
                    : "Participant name"
              }
              onChange={(event) => setManualName(event.target.value)}
            />
          </>
        )}
      </fieldset>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="btn primary"
          onClick={start}
          disabled={unavailable || busy || uploading || importingTranscript}
          aria-label="Start recording"
        >
          {phase === "requesting" ? "Starting…" : "Start recording"}
        </button>
        <button
          type="button"
          className={`btn${phase === "recording" ? " recording" : ""}`}
          onClick={stop}
          disabled={phase !== "recording"}
          aria-label="Stop recording"
        >
          {phase === "stopping" ? "Stopping…" : "Stop recording"}
        </button>
        <input
          ref={recordingInputRef}
          type="file"
          accept="audio/*,.mp3,.m4a,.wav,.ogg,.webm,.flac"
          className="hidden"
          data-testid="recording-file-input"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) void uploadRecording(file);
          }}
        />
        <button
          type="button"
          className="btn"
          onClick={() => recordingInputRef.current?.click()}
          disabled={unavailable || busy || uploading || importingTranscript}
          aria-label="Upload an audio recording to transcribe"
        >
          {uploading ? "Transcribing…" : "Upload recording"}
        </button>
        <input
          ref={transcriptInputRef}
          type="file"
          accept=".txt,.md,.json,.vtt,.srt,text/plain,application/json,text/vtt"
          className="hidden"
          data-testid="transcript-file-input"
          onChange={(event) => {
            const file = event.target.files?.[0];
            event.target.value = "";
            if (file) void uploadTranscript(file);
          }}
        />
        <button
          type="button"
          className="btn"
          onClick={() => transcriptInputRef.current?.click()}
          disabled={busy || uploading || importingTranscript}
          aria-label="Upload a transcript file"
        >
          {importingTranscript ? "Importing…" : "Upload transcript"}
        </button>
        <span className="text-[11px] text-[var(--muted)]">{statusLabel}</span>
        <div
          className="h-2 min-w-20 flex-1 overflow-hidden rounded-full bg-[#07101d]"
          role="meter"
          aria-label="Microphone level"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={Math.round(level * 100)}
        >
          <div
            className="h-full rounded-full bg-[linear-gradient(90deg,var(--green),var(--yellow))] transition-[width] duration-75"
            style={{ width: `${Math.round(level * 100)}%` }}
          />
        </div>
      </div>
      {partialText ? (
        <div
          data-testid="live-partial"
          className="mt-2 rounded-lg border border-dashed border-[rgba(103,168,255,0.45)] bg-[rgba(103,168,255,0.08)] px-3 py-2 text-xs leading-relaxed text-[#d6e7ff]"
        >
          <span className="mr-2 text-[10px] font-bold uppercase tracking-wide text-[var(--blue)]">
            {partialSpeaker ?? "Live"}
          </span>
          {partialText}
        </div>
      ) : null}
      {error ? <div className="mt-2 text-[11px] text-[var(--red)]">{error}</div> : null}
    </div>
  );
}
