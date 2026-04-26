/**
 * GeminiLiveClient — connects to the local FastAPI WebSocket relay which
 * bridges audio between the browser and the Gemini Live API.
 *
 * Protocol (browser ↔ server):
 *   Send:    {"type": "audio", "data": "<base64 pcm16 16kHz>"}
 *   Receive: {"type": "audio", "data": "<base64 pcm16 24kHz>"}
 *            {"type": "status", "message": "..."}
 *            {"type": "input_transcript", "text": "..."}
 *            {"type": "output_transcript", "text": "..."}
 *            {"type": "turn_complete"}
 *            {"type": "interrupted"}
 *            {"type": "error", "message": "..."}
 */

class GeminiLiveClient {
  constructor() {
    this.ws = null;
    this.ready = false;

    // Public callbacks
    this.onready = null;
    this.onaudio = null;
    this.ontranscript = null;
    this.onturncomplete = null;
    this.oninterrupted = null;
    this.onclose = null;
    this.onerror = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const url = `${protocol}//${window.location.host}/ws`;

      console.log('[GeminiLiveClient] Connecting to', url);
      this.ws = new WebSocket(url);

      this.ws.addEventListener('open', () => {
        console.log('[GeminiLiveClient] WebSocket open, waiting for Gemini session...');
      });

      this.ws.addEventListener('message', (event) => {
        let msg;
        try {
          msg = JSON.parse(event.data);
        } catch {
          console.warn('[GeminiLiveClient] Non-JSON message:', event.data);
          return;
        }

        switch (msg.type) {
          case 'status':
            console.log('[GeminiLiveClient] Status:', msg.message);
            if (msg.message === 'Connected to Gemini') {
              this.ready = true;
              resolve();
              if (this.onready) this.onready();
            }
            break;

          case 'audio':
            if (this.onaudio) this.onaudio(msg.data);
            break;

          case 'input_transcript':
            console.log('[You]', msg.text);
            if (this.ontranscript) this.ontranscript('user', msg.text);
            break;

          case 'output_transcript':
            console.log('[Agent]', msg.text);
            if (this.ontranscript) this.ontranscript('agent', msg.text);
            break;

          case 'turn_complete':
            if (this.onturncomplete) this.onturncomplete();
            break;

          case 'interrupted':
            console.log('[GeminiLiveClient] Interrupted (barge-in)');
            if (this.oninterrupted) this.oninterrupted();
            break;

          case 'error':
            console.error('[GeminiLiveClient] Server error:', msg.message);
            if (this.onerror) this.onerror(new Error(msg.message));
            break;

          default:
            console.log('[GeminiLiveClient] Unknown message type:', msg.type);
        }
      });

      this.ws.addEventListener('close', (event) => {
        console.log(`[GeminiLiveClient] WebSocket closed: code=${event.code} reason="${event.reason}"`);
        this.ready = false;
        if (!this.ready && !event.wasClean) {
          reject(new Error(`WebSocket closed (code: ${event.code})`));
        }
        if (this.onclose) this.onclose(event.code, event.reason);
      });

      this.ws.addEventListener('error', (err) => {
        console.error('[GeminiLiveClient] WebSocket error:', err);
        this.ready = false;
        reject(new Error('WebSocket connection error'));
        if (this.onerror) this.onerror(err);
      });
    });
  }

  sendAudio(base64Data) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({
      type: 'audio',
      data: base64Data
    }));
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.ready = false;
  }
}
