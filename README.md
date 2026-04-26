# H A M — High-end AI Management

Professional AI Voice Solutions for businesses. This repository contains the core platform and demonstration projects for the H A M voice ecosystem.

## 🚀 Projects

### 1. [HAM Landing](file:///d:/Gemini%20Voice2/Gemini%20Voice2/ham-landing)
Professional sales landing page for H A M services, featuring our AI Voice packs (Standard & Agentic Pro).

### 2. [HAM Keyboard](file:///d:/Gemini%20Voice2/Gemini%20Voice2/ham-keyboard)
A live demonstration of the **Agentic Pro** pack integrated into a premium mechanical keyboard shop.
- **Voice Agent**: Powered by Gemini 3.1 Flash Live.
- **Abilities**: Answers product questions and executes actions (navigate, add to cart).

### 3. [SaaS Platform](file:///d:/Gemini%20Voice2/Gemini%20Voice2/saas-platform)
The core engine that hosts the voice widget and manages the real-time audio pipeline between the browser and the AI.

## 🛠️ Quick Start

1. **Setup Environment**:
   Ensure you have a `.env` file in the root with your `GOOGLE_API_KEY`.

2. **Launch SaaS Platform**:
   ```bash
   python saas-platform/server.py
   # Runs on http://127.0.0.1:8001
   ```

3. **Launch Keyboard Demo**:
   ```bash
   python ham-keyboard/server.py
   # Runs on http://127.0.0.1:8003
   ```

4. **View Landing Page**:
   Open `ham-landing/index.html` in your browser.

## 🏗️ Architecture
All projects use a unified real-time voice architecture:
- **Frontend**: Vanilla JS with `ApexVoice` widget.
- **Backend**: FastAPI with `websockets` for low-latency audio streaming.
- **AI**: Google Gemini 3.1 Flash Live (A2A) for human-like response quality.

---
&copy; 2026 H A M AI Management.
