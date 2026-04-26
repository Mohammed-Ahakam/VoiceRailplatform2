/**
 * AudioRecorder — captures microphone audio and outputs base64-encoded PCM16 at 16 kHz.
 *
 * Usage:
 *   const recorder = new AudioRecorder((base64) => sendToGemini(base64));
 *   await recorder.start();
 *   recorder.stop();
 */
class AudioRecorder {
  constructor(onData) {
    this.onData = onData; // callback: (base64String) => void
    this.stream = null;
    this.context = null;
    this.processor = null;
  }

  async start() {
    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
    });

    this.context = new AudioContext({ sampleRate: 16000 });
    const source = this.context.createMediaStreamSource(this.stream);

    // ScriptProcessorNode — deprecated but universally supported and fine for a demo.
    this.processor = this.context.createScriptProcessor(4096, 1, 1);
    this.processor.onaudioprocess = (e) => {
      const float32 = e.inputBuffer.getChannelData(0);
      const int16 = new Int16Array(float32.length);
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]));
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
      }
      const base64 = this._arrayBufferToBase64(int16.buffer);
      this.onData(base64);
    };

    source.connect(this.processor);
    // Connect to destination to keep the processor ticking (required by spec).
    this.processor.connect(this.context.destination);
  }

  stop() {
    if (this.processor) {
      this.processor.disconnect();
      this.processor.onaudioprocess = null;
      this.processor = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = null;
    }
    if (this.context) {
      this.context.close().catch(() => {});
      this.context = null;
    }
  }

  /**
   * Convert an ArrayBuffer to a base64 string without blowing up the stack on
   * large buffers (avoids Function.prototype.apply / spread on huge arrays).
   */
  _arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    const CHUNK = 0x8000; // 32 KB chunks
    let binary = '';
    for (let i = 0; i < bytes.length; i += CHUNK) {
      const slice = bytes.subarray(i, i + CHUNK);
      binary += String.fromCharCode.apply(null, slice);
    }
    return btoa(binary);
  }
}
