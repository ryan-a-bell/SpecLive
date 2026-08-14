const OUTPUT_SAMPLE_RATE = 16_000;
const DEFAULT_FRAME_SAMPLES = 3_200; // 200 ms

export function calculateRms(samples: Float32Array): number {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (const sample of samples) sum += sample * sample;
  return Math.sqrt(sum / samples.length);
}

function encodePcm16(samples: readonly number[]): ArrayBuffer {
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);
  samples.forEach((sample, index) => {
    const clamped = Math.max(-1, Math.min(1, sample));
    const value = clamped < 0 ? Math.round(clamped * 32768) : Math.round(clamped * 32767);
    view.setInt16(index * 2, value, true);
  });
  return buffer;
}

/** Streaming linear resampler and fixed-size PCM16 frame encoder. */
export class PcmFrameEncoder {
  private readonly step: number;
  private source: number[] = [];
  private position = 0;
  private pending: number[] = [];

  constructor(
    inputSampleRate: number,
    private readonly frameSamples = DEFAULT_FRAME_SAMPLES,
  ) {
    if (inputSampleRate <= 0) throw new Error("Input sample rate must be positive");
    this.step = inputSampleRate / OUTPUT_SAMPLE_RATE;
  }

  push(input: Float32Array): ArrayBuffer[] {
    this.source.push(...input);
    while (this.position < this.source.length - 1) {
      const left = Math.floor(this.position);
      const fraction = this.position - left;
      const leftSample = this.source[left] ?? 0;
      const rightSample = this.source[left + 1] ?? leftSample;
      this.pending.push(leftSample + fraction * (rightSample - leftSample));
      this.position += this.step;
    }

    const consumed = Math.floor(this.position);
    if (consumed > 0) {
      this.source = this.source.slice(consumed);
      this.position -= consumed;
    }
    return this.takeFrames();
  }

  flush(): ArrayBuffer[] {
    const frames = this.takeFrames();
    if (this.pending.length > 0) {
      this.pending.push(...Array(this.frameSamples - this.pending.length).fill(0));
      frames.push(encodePcm16(this.pending));
      this.pending = [];
    }
    this.source = [];
    this.position = 0;
    return frames;
  }

  private takeFrames(): ArrayBuffer[] {
    const frames: ArrayBuffer[] = [];
    while (this.pending.length >= this.frameSamples) {
      frames.push(encodePcm16(this.pending.slice(0, this.frameSamples)));
      this.pending = this.pending.slice(this.frameSamples);
    }
    return frames;
  }
}
