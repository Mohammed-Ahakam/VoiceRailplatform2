# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Aria** is a real-time voice assistant powered by Gemini 3.1 Flash Live API. It streams bidirectional audio over WebSocket between a browser client and Google's Gemini live model, with server-side tool execution for ClickUp task management and Google Calendar.

## Running the App

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the main voice assistant (port 8000)
python server.py

# Run the keyboard demo (port 3001, Python version)
cd keyboard-demo && python server.py

# Run the keyboard demo (port 3001, Node version)
cd keyboard-demo && npm start
```

The app requires a `.env` file with `GOOGLE_API_KEY` and `CLICKUP_API_KEY`. Google Calendar OAuth uses `client_secret_*.json` and `token.json` at the project root.

## Architecture

### Main App (root)

- **server.py** — FastAPI server with a single WebSocket endpoint (`/ws`). On connection, opens a Gemini Live session with bidirectional audio streaming. Two concurrent async tasks handle browser→Gemini and Gemini→browser message flow. Tool calls from Gemini are intercepted, executed server-side, and results sent back to the model.
- **index.html** — Single-file browser client. Captures mic audio via AudioWorklet (16kHz PCM), sends base64-encoded chunks over WebSocket. Plays back Gemini's 24kHz PCM audio responses. Shows real-time transcription and tool call indicators.
- **tools/clickup.py** — ClickUp API v2 wrapper. All functions return `{"status": "success"|"error", ...}` dicts. Hierarchy: workspaces → spaces → folders → lists → tasks.
- **tools/calendar.py** — Google Calendar API wrapper using OAuth 2.0 (not API key). First run triggers browser-based OAuth flow that creates `token.json`. Same return dict pattern as clickup.

### Audio Pipeline

- Browser captures at 16kHz mono PCM → base64 → WebSocket → server decodes → sends to Gemini as `audio/pcm;rate=16000`
- Gemini responds with 24kHz PCM audio → server base64-encodes → WebSocket → browser decodes and plays via Web Audio API
- Barge-in supported: when user interrupts, playback queue is cleared

### Tool Execution Pattern

Tools are registered in two parallel structures in `server.py`:
1. `TOOLS` dict — maps function name strings to Python callables
2. `TOOL_DECLARATIONS` list — JSON schema declarations sent to Gemini

When adding a new tool: add the function to `tools/`, add to both `TOOLS` and `TOOL_DECLARATIONS` in `server.py`, and update the `SYSTEM_PROMPT`.

### keyboard-demo/

Standalone demo variant — an e-commerce keyboard landing page with voice sales assistant. Has both a Python (FastAPI) and Node (Express) server. The Node version serves the API key via `/api/token` endpoint for client-side Gemini connection. The Python version proxies through WebSocket like the main app.

## Key Details

- Model: `gemini-3.1-flash-live-preview` (Gemini Live API, not standard Gemini)
- Timezone: hardcoded to America/Chicago (Central Time) for the assistant persona
- All tool functions are synchronous (using `requests`), called from async context via `execute_tool()`
- The system prompt is generated at import time (captures current time), so the server must be restarted for time context to update
