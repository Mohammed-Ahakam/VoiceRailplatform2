/**
 * Voice Widget — UI controller that wires AudioRecorder, AudioStreamer, and
 * GeminiLiveClient together behind a single mic button.
 *
 * States: idle -> connecting -> listening -> agent_speaking -> (back to listening
 * or idle on disconnect).
 */

document.addEventListener('DOMContentLoaded', () => {
  // ---------------------------------------------------------------------------
  // Inject widget HTML
  // ---------------------------------------------------------------------------
  const container = document.getElementById('voice-widget-container');
  if (!container) {
    console.warn('[VoiceWidget] #voice-widget-container not found');
    return;
  }

  container.innerHTML = `
    <span class="voice-status" id="voice-status" style="display:none;"></span>
    <button class="voice-btn" id="voice-btn" aria-label="Talk to Apex assistant">
      <svg class="mic-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3z"/>
        <path d="M19 11a1 1 0 0 0-2 0 5 5 0 0 1-10 0 1 1 0 0 0-2 0 7 7 0 0 0 6 6.93V20H8a1 1 0 0 0 0 2h8a1 1 0 0 0 0-2h-3v-2.07A7 7 0 0 0 19 11z"/>
      </svg>
    </button>
  `;

  const btn = document.getElementById('voice-btn');
  const statusEl = document.getElementById('voice-status');

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let state = 'idle'; // idle | connecting | listening | agent_speaking
  let recorder = null;
  let streamer = null;
  let client = null;

  function setState(newState, statusText) {
    state = newState;

    // CSS classes
    btn.classList.remove('voice-btn--active', 'voice-btn--connecting');
    if (newState === 'connecting') btn.classList.add('voice-btn--connecting');
    if (newState === 'listening') btn.classList.add('voice-btn--active');
    if (newState === 'agent_speaking') btn.classList.add('voice-btn--active');

    // Status text
    if (statusText) {
      statusEl.textContent = statusText;
      statusEl.style.display = '';
    } else if (newState === 'idle') {
      statusEl.style.display = 'none';
    }
  }

  // ---------------------------------------------------------------------------
  // Teardown helper
  // ---------------------------------------------------------------------------
  function stopEverything() {
    if (recorder) {
      recorder.stop();
      recorder = null;
    }
    if (streamer) {
      streamer.stop();
      streamer = null;
    }
    if (client) {
      client.disconnect();
      client = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Button click handler
  // ---------------------------------------------------------------------------
  btn.addEventListener('click', async () => {
    // If already active, stop
    if (state !== 'idle') {
      stopEverything();
      setState('idle');
      return;
    }

    // --- Begin connection flow ---
    setState('connecting', 'Connecting...');

    try {
      // Create instances — AudioContext & getUserMedia inside click handler for
      // browser autoplay / permission policies.
      streamer = new AudioStreamer();
      streamer.ensureContext(); // create AudioContext inside user gesture

      recorder = new AudioRecorder((base64) => {
        if (client && client.ready) {
          client.sendAudio(base64);
        }
      });

      // Request mic permission early so we fail fast if denied
      await recorder.start();

      client = new GeminiLiveClient();

      // --- Wire callbacks ---

      client.onready = () => {
        setState('listening', 'Listening...');
      };

      client.onaudio = (base64Data) => {
        if (state !== 'agent_speaking') {
          setState('agent_speaking', 'Speaking...');
        }
        streamer.addPCM16(base64Data);
      };

      client.ontranscript = (role, text) => {
        console.log(`[${role}]`, text);
      };

      client.onturncomplete = () => {
        // Agent finished its turn — go back to listening
        if (state === 'agent_speaking') {
          setState('listening', 'Listening...');
        }
      };

      client.oninterrupted = () => {
        // User barged in — immediately clear audio and go back to listening
        streamer.clearQueue();
        setState('listening', 'Listening...');
      };

      client.onclose = (code, reason) => {
        console.log(`[VoiceWidget] Connection closed: code=${code} reason="${reason}"`);
        stopEverything();
        const msg = reason ? `Closed: ${reason}` : 'Session ended';
        setState('idle', msg);
        setTimeout(() => {
          if (state === 'idle') statusEl.style.display = 'none';
        }, 4000);
      };

      client.onerror = (err) => {
        console.error('[VoiceWidget] Error:', err);
        stopEverything();
        setState('idle', 'Connection error');
        setTimeout(() => {
          if (state === 'idle') statusEl.style.display = 'none';
        }, 4000);
      };

      streamer.onended = () => {
        // Fallback: if turn_complete didn't fire, use audio end as signal
        if (state === 'agent_speaking') {
          setState('listening', 'Listening...');
        }
      };

      // --- Connect to server WebSocket relay ---
      await client.connect();

    } catch (err) {
      console.error('[VoiceWidget] Startup error:', err);
      stopEverything();

      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        setState('idle', 'Mic access denied');
      } else {
        setState('idle', err.message || 'Failed to connect');
      }

      // Auto-hide status
      setTimeout(() => {
        if (state === 'idle') statusEl.style.display = 'none';
      }, 4000);
    }
  });
});
