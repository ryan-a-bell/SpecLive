import { describe, expect, it } from "vitest";
import { calculateRms, PcmFrameEncoder } from "./audio";

describe("PcmFrameEncoder", () => {
  it("emits fixed-size little-endian PCM16 frames", () => {
    const encoder = new PcmFrameEncoder(16_000, 4);
    const frames = encoder.push(new Float32Array([0, 0.5, -0.5, 1, -1]));
    expect(frames).toHaveLength(1);
    const view = new DataView(frames[0]!);
    expect(view.getInt16(0, true)).toBe(0);
    expect(view.getInt16(2, true)).toBe(16_384);
    expect(view.getInt16(4, true)).toBe(-16_384);
    expect(view.getInt16(6, true)).toBe(32_767);
  });

  it("resamples 48 kHz input and pads the final frame", () => {
    const encoder = new PcmFrameEncoder(48_000, 4);
    expect(encoder.push(new Float32Array([0, 0.3, 0.6, 0.9, 0.6, 0.3, 0]))).toHaveLength(0);
    const finalFrames = encoder.flush();
    expect(finalFrames).toHaveLength(1);
    expect(finalFrames[0]?.byteLength).toBe(8);
  });
});

describe("calculateRms", () => {
  it("returns a normalized voice level", () => {
    expect(calculateRms(new Float32Array([1, -1]))).toBe(1);
    expect(calculateRms(new Float32Array())).toBe(0);
  });
});
