/**
 * PcmProcessor - AudioWorkletProcessor for 16kHz PCM mono capture.
 *
 * Downsamples the microphone input from the AudioContext sample rate to
 * 16000 Hz (required by ElevenLabs Scribe Realtime), converts float32 samples
 * to int16 PCM, accumulates a 1-second buffer (32000 bytes), and posts it to
 * the main thread as a transferable ArrayBuffer.
 *
 * Usage:
 *   await audioContext.audioWorklet.addModule('/worklets/pcm-processor.js');
 *   const node = new AudioWorkletNode(audioContext, 'pcm-processor');
 *   node.port.onmessage = (e) => { // e.data is ArrayBuffer of PCM int16 };
 *   micSource.connect(node);
 */

const TARGET_SAMPLE_RATE = 16000;
// 1 second of 16kHz 16-bit mono audio = 16000 samples * 2 bytes = 32000 bytes
const CHUNK_BYTE_SIZE = TARGET_SAMPLE_RATE * 2;

class PcmProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Accumulate int16 samples until we have a 1-second chunk
    this._buffer = new Int16Array(TARGET_SAMPLE_RATE);
    this._bufferOffset = 0;
    // Fractional phase for downsampling — persists across process() calls
    // to avoid drift at non-integer ratios (e.g. 44100 / 16000 = 2.75625)
    this._downsamplePhase = 0;

    // Handle flush command from main thread — post remaining partial buffer
    this.port.onmessage = (e) => {
      if (e.data?.type === 'flush') {
        if (this._bufferOffset > 0) {
          const byteLength = this._bufferOffset * 2; // int16 = 2 bytes per sample
          const arrayBuffer = this._buffer.buffer.slice(0, byteLength);
          this.port.postMessage(arrayBuffer, [arrayBuffer]);
          this._buffer = new Int16Array(TARGET_SAMPLE_RATE);
          this._bufferOffset = 0;
        }
        this.port.postMessage({ type: 'flushed' });
      }
    };
  }

  /**
   * Process audio frames from the mic.
   *
   * @param {Float32Array[][]} inputs - Array of input channels per input port.
   * @returns {boolean} true to keep the processor alive.
   */
  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    const channel = input[0];
    if (!channel || channel.length === 0) return true;

    // Downsample ratio: e.g. 48000 / 16000 = 3, or 44100 / 16000 = 2.75625
    const ratio = sampleRate / TARGET_SAMPLE_RATE;

    let i = this._downsamplePhase;
    for (; i < channel.length; i += ratio) {
      const srcIndex = Math.floor(i);
      const sample = channel[srcIndex];

      // Clamp to [-1, 1] and convert float32 to int16
      const clamped = Math.max(-1, Math.min(1, sample));
      const int16 = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;

      this._buffer[this._bufferOffset++] = Math.round(int16);

      // When we have collected 1 second of audio, post the buffer
      if (this._bufferOffset >= TARGET_SAMPLE_RATE) {
        const arrayBuffer = this._buffer.buffer.slice(0, CHUNK_BYTE_SIZE);
        this.port.postMessage(arrayBuffer, [arrayBuffer]);
        // Create a fresh buffer for the next chunk
        this._buffer = new Int16Array(TARGET_SAMPLE_RATE);
        this._bufferOffset = 0;
      }
    }

    // Persist how far past the buffer end the next sample falls,
    // so the next process() call starts at the correct fractional offset
    this._downsamplePhase = i - channel.length;

    return true;
  }
}

registerProcessor('pcm-processor', PcmProcessor);
