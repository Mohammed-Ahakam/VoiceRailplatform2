/**
 * AudioStreamer — plays back base64-encoded PCM16 audio at 24 kHz from Gemini
 * responses using look-ahead scheduling to avoid gaps between chunks.
 *
 * Usage:
 *   const streamer = new AudioStreamer();
 *   streamer.onended = () => console.log('done speaking');
 *   streamer.addPCM16(base64Data);
 *   streamer.stop();
 */
class AudioStreamer {
  constructor() {
    this.context = null;
    this.gainNode = null;
    this.queue = [];           // Array of Float32Arrays waiting to be scheduled
    this.isPlaying = false;
    this.scheduledEndTime = 0; // AudioContext time when the last scheduled buffer ends
    this.checkInterval = null;
    this.onended = null;       // callback when all queued audio has finished
    this._endedTimeout = null;
  }

  /**
   * Ensure the AudioContext exists and is running.
   * MUST be called from a user-gesture handler the first time (browser autoplay policy).
   */
  ensureContext() {
    if (!this.context) {
      this.context = new AudioContext({ sampleRate: 24000 });
      this.gainNode = this.context.createGain();
      this.gainNode.connect(this.context.destination);
    }
    if (this.context.state === 'suspended') {
      this.context.resume();
    }
  }

  /**
   * Decode base64 PCM16 data and queue it for playback.
   */
  addPCM16(base64Data) {
    this.ensureContext();

    // Decode base64 -> raw bytes -> Int16Array -> Float32Array
    const raw = atob(base64Data);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) {
      bytes[i] = raw.charCodeAt(i);
    }
    const int16 = new Int16Array(bytes.buffer);
    const float32 = new Float32Array(int16.length);
    for (let i = 0; i < int16.length; i++) {
      float32[i] = int16[i] / 0x8000;
    }

    this.queue.push(float32);
    this._scheduleNext();

    // Start periodic check for end-of-playback
    if (!this.checkInterval) {
      this.checkInterval = setInterval(() => this._checkEnded(), 100);
    }
  }

  /**
   * Schedule queued buffers with look-ahead so playback is gapless.
   */
  _scheduleNext() {
    if (!this.context || this.queue.length === 0) return;

    while (this.queue.length > 0) {
      const samples = this.queue.shift();
      const buffer = this.context.createBuffer(1, samples.length, 24000);
      buffer.getChannelData(0).set(samples);

      const source = this.context.createBufferSource();
      source.buffer = buffer;
      source.connect(this.gainNode);

      const startAt = Math.max(this.context.currentTime, this.scheduledEndTime);
      source.start(startAt);
      this.scheduledEndTime = startAt + buffer.duration;
      this.isPlaying = true;
    }
  }

  /**
   * Check if all scheduled audio has finished playing.
   */
  _checkEnded() {
    if (!this.context) return;
    if (this.isPlaying && this.context.currentTime >= this.scheduledEndTime && this.queue.length === 0) {
      this.isPlaying = false;
      this._clearCheck();
      if (this.onended) {
        this.onended();
      }
    }
  }

  _clearCheck() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
  }

  /**
   * Clear queued audio and stop current playback without destroying the context.
   * Used for barge-in / interruption — the context stays alive for the next turn.
   */
  clearQueue() {
    this.queue = [];
    this.isPlaying = false;
    this.scheduledEndTime = 0;
    this._clearCheck();
    // Disconnect and recreate the gain node to instantly silence any scheduled sources
    if (this.gainNode && this.context) {
      this.gainNode.disconnect();
      this.gainNode = this.context.createGain();
      this.gainNode.connect(this.context.destination);
    }
  }

  /**
   * Immediately stop all playback, clear the queue, and close the context.
   */
  stop() {
    this.queue = [];
    this.isPlaying = false;
    this.scheduledEndTime = 0;
    this._clearCheck();
    if (this.context) {
      this.context.close().catch(() => {});
      this.context = null;
      this.gainNode = null;
    }
  }
}
