/**
 * ApexVoice — The SaaS Widget Library
 * This file is intended to be the only script embedded by the client.
 */

(function() {
  'use strict';

  // --- Audio Recorder ---
  class AudioRecorder {
    constructor(onData) {
      this.onData = onData;
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
      this.processor = this.context.createScriptProcessor(4096, 1, 1);
      this.processor.onaudioprocess = (e) => {
        const float32 = e.inputBuffer.getChannelData(0);
        const int16 = new Int16Array(float32.length);
        for (let i = 0; i < float32.length; i++) {
          const s = Math.max(-1, Math.min(1, float32[i]));
          int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        const bytes = new Uint8Array(int16.buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i += 8192) {
          binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 8192));
        }
        this.onData(btoa(binary));
      };
      source.connect(this.processor);
      this.processor.connect(this.context.destination);
    }
    stop() {
      if (this.processor) {
        this.processor.disconnect();
        this.processor = null;
      }
      if (this.stream) {
        this.stream.getTracks().forEach(t => t.stop());
        this.stream = null;
      }
      if (this.context) {
        this.context.close().catch(() => {});
        this.context = null;
      }
    }
  }

  // --- Audio Streamer ---
  class AudioStreamer {
    constructor() {
      this.context = null;
      this.gainNode = null;
      this.queue = [];
      this.isPlaying = false;
      this.scheduledEndTime = 0;
      this.onended = null;
    }
    ensureContext() {
      if (!this.context) {
        this.context = new AudioContext({ sampleRate: 24000 });
        this.gainNode = this.context.createGain();
        this.gainNode.connect(this.context.destination);
      }
      if (this.context.state === 'suspended') this.context.resume();
    }
    addPCM16(base64Data) {
      this.ensureContext();
      const raw = atob(base64Data);
      const int16 = new Int16Array(raw.length / 2);
      for (let i = 0; i < int16.length; i++) {
        int16[i] = (raw.charCodeAt(i * 2) & 0xFF) | (raw.charCodeAt(i * 2 + 1) << 8);
      }
      const float32 = new Float32Array(int16.length);
      for (let i = 0; i < int16.length; i++) float32[i] = int16[i] / 0x8000;
      this.queue.push(float32);
      this._scheduleNext();
    }
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
    clearQueue() {
      this.queue = [];
      this.isPlaying = false;
      this.scheduledEndTime = 0;
      if (this.gainNode && this.context) {
        this.gainNode.disconnect();
        this.gainNode = this.context.createGain();
        this.gainNode.connect(this.context.destination);
      }
    }
    stop() {
      this.clearQueue();
      if (this.context) {
        this.context.close().catch(() => {});
        this.context = null;
      }
    }
  }

  // --- SaaS Client Library ---
  const ApexVoice = {
    config: null,
    ws: null,
    recorder: null,
    streamer: null,
    state: 'idle', // idle | connecting | active

    init(config) {
      this.config = config;
      this._injectStyles();
      this._injectWidget();
      console.log('[ApexVoice] Initialized for:', config.apiKey);
    },

    async _startSession() {
      if (this.state !== 'idle') return;
      this._updateStatus('Connecting...');
      this.state = 'connecting';

      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // In production, this would be your SaaS domain
        const wsUrl = `${protocol}//127.0.0.1:8001/ws`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
          // Send setup configuration
          const setup = {
            type: 'setup',
            apiKey: this.config.apiKey,
            settings: {
              system_instruction: this.config.systemInstruction,
              tools: this.config.tools || []
            }
          };
          this.ws.send(JSON.stringify(setup));
        };

        this.ws.onmessage = async (event) => {
          const msg = JSON.parse(event.data);
          
          switch(msg.type) {
            case 'status':
              if (msg.message === 'Connected to Gemini SaaS Engine') {
                this.state = 'active';
                this.currentWhatsapp = msg.whatsapp;
                this.currentCompanyName = msg.companyName;
                this._updateStatus('Listening...');
                this._startAudio();
              }
              break;
            case 'audio':
              this.streamer.addPCM16(msg.data);
              break;
            case 'action':
              console.log('[ApexVoice] Action received:', msg.name, msg.args);
              if (msg.name === 'checkout') {
                this._showCheckout(msg.args);
              } else if (this.config.actions && this.config.actions[msg.name]) {
                this.config.actions[msg.name](msg.args);
              }
              break;
            case 'interrupted':
              this.streamer.clearQueue();
              break;
            case 'error':
              console.error('[ApexVoice] Server error:', msg.message);
              this._stopSession();
              break;
          }
        };

        this.ws.onclose = () => this._stopSession();
        this.ws.onerror = (e) => {
          console.error('[ApexVoice] WS error:', e);
          this._stopSession();
        };

      } catch (err) {
        console.error('[ApexVoice] Failed to start:', err);
        this._stopSession();
      }
    },

    _stopSession() {
      if (this.recorder) this.recorder.stop();
      if (this.streamer) this.streamer.stop();
      if (this.ws) this.ws.close();
      this.state = 'idle';
      this._updateStatus(null);
      this.recorder = null;
      this.streamer = null;
      this.ws = null;
    },

    async _startAudio() {
      this.streamer = new AudioStreamer();
      this.streamer.ensureContext();
      this.recorder = new AudioRecorder((base64) => {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'audio', data: base64 }));
        }
      });
      await this.recorder.start();
    },

    _updateStatus(text) {
      const btn = document.getElementById('apex-voice-btn');
      const status = document.getElementById('apex-voice-status');
      if (!btn || !status) return;

      if (text) {
        status.textContent = text;
        status.style.display = 'block';
        btn.classList.add('apex-active');
      } else {
        status.style.display = 'none';
        btn.classList.remove('apex-active');
      }
    },

    _injectWidget() {
      const container = document.createElement('div');
      container.id = 'apex-voice-widget';
      container.innerHTML = `
        <div id="apex-voice-status" style="display:none"></div>
        <button id="apex-voice-btn" aria-label="Talk to AI">
          <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"/>
            <path d="M19 11a1 1 0 0 0-2 0 5 5 0 0 1-10 0 1 1 0 0 0-2 0 7 7 0 0 0 6 6.93V20H8a1 1 0 0 0 0 2h8a1 1 0 0 0 0-2h-3v-2.07A7 7 0 0 0 19 11z"/>
          </svg>
        </button>
      `;
      document.body.appendChild(container);

      document.getElementById('apex-voice-btn').onclick = () => {
        if (this.state === 'idle') this._startSession();
        else this._stopSession();
      };

      // Create checkout modal
      const modal = document.createElement('div');
      modal.id = 'apex-checkout-modal';
      modal.style.cssText = 'display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.8); z-index:20000; align-items:center; justify-content:center; font-family:sans-serif;';
      modal.innerHTML = `
        <div style="background:white; padding:30px; border-radius:15px; width:90%; max-width:400px; color:#333;">
          <h2 style="margin-top:0;">Finaliser la Commande</h2>
          <p style="font-size:14px; color:#666;">Veuillez entrer vos informations pour envoyer la commande via WhatsApp.</p>
          <div style="margin-bottom:15px;">
            <label style="display:block; font-size:12px; font-weight:bold; margin-bottom:5px;">Nom Complet</label>
            <input type="text" id="apex-name" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:8px; box-sizing:border-box;">
          </div>
          <div style="margin-bottom:15px;">
            <label style="display:block; font-size:12px; font-weight:bold; margin-bottom:5px;">Téléphone</label>
            <input type="text" id="apex-phone" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:8px; box-sizing:border-box;">
          </div>
          <div style="margin-bottom:20px;">
            <label style="display:block; font-size:12px; font-weight:bold; margin-bottom:5px;">Adresse de Livraison</label>
            <textarea id="apex-address" style="width:100%; padding:10px; border:1px solid #ddd; border-radius:8px; box-sizing:border-box; height:60px;"></textarea>
          </div>
          <div style="display:flex; gap:10px;">
            <button id="apex-cancel" style="flex:1; padding:12px; border:none; border-radius:8px; background:#eee; cursor:pointer;">Annuler</button>
            <button id="apex-confirm" style="flex:2; padding:12px; border:none; border-radius:8px; background:#6c5ce7; color:white; font-weight:bold; cursor:pointer;">Confirmer sur WhatsApp</button>
          </div>
        </div>
      `;
      document.body.appendChild(modal);

      document.getElementById('apex-cancel').onclick = () => modal.style.display = 'none';
      document.getElementById('apex-confirm').onclick = () => this._sendWhatsApp();
    },

    _sendWhatsApp() {
      const name = document.getElementById('apex-name').value;
      const phone = document.getElementById('apex-phone').value;
      const address = document.getElementById('apex-address').value;
      
      if (!name || !phone || !address) {
        alert('Veuillez remplir tous les champs.');
        return;
      }

      const products = this.pendingOrder || "Commande du catalogue";
      const message = `Bonjour ${this.config.companyName},
Je souhaite commander : ${products}
      
Infos Client :
Nom : ${name}
Tél : ${phone}
Adresse : ${address}
      
(Envoyé via HAM voice bot)`;

      const encoded = encodeURIComponent(message);
      // Use the dynamic whatsapp number or fallback, cleaned of spaces/dashes
      let targetNumber = this.currentWhatsapp || "212600000000";
      targetNumber = targetNumber.replace(/\D/g, ''); // Remove non-digits
      const whatsappUrl = `https://wa.me/${targetNumber}?text=${encoded}`;
      window.open(whatsappUrl, '_blank');
      document.getElementById('apex-checkout-modal').style.display = 'none';
      this._stopSession();
    },

    _showCheckout(args) {
      this.pendingOrder = args.product || "Un produit du catalogue";
      document.getElementById('apex-checkout-modal').style.display = 'flex';
      console.log('[ApexVoice] Checkout opened for:', this.pendingOrder);
    },

    _injectStyles() {
      const css = `
        #apex-voice-widget {
          position: fixed; bottom: 30px; right: 30px; z-index: 10000;
          display: flex; flex-direction: column; align-items: flex-end; gap: 10px;
          font-family: sans-serif;
        }
        #apex-voice-btn {
          width: 60px; height: 60px; border-radius: 50%; border: none;
          background: #6c5ce7; color: white; cursor: pointer;
          box-shadow: 0 4px 15px rgba(108, 92, 231, 0.4); transition: all 0.2s;
          display: flex; align-items: center; justify-content: center;
        }
        #apex-voice-btn:hover { transform: scale(1.05); background: #7c6ef0; }
        #apex-voice-btn.apex-active { animation: apex-pulse 1.5s infinite; background: #7c6ef0; }
        #apex-voice-status {
          background: white; color: #333; padding: 6px 14px; border-radius: 20px;
          font-size: 12px; font-weight: 600; box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        @keyframes apex-pulse {
          0% { box-shadow: 0 0 0 0 rgba(108, 92, 231, 0.6); }
          70% { box-shadow: 0 0 0 15px rgba(108, 92, 231, 0); }
          100% { box-shadow: 0 0 0 0 rgba(108, 92, 231, 0); }
        }
      `;
      const style = document.createElement('style');
      style.textContent = css;
      document.head.appendChild(style);
    }
  };

  window.ApexVoice = ApexVoice;
  const json = JSON; // Alias for safety
})();
