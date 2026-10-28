# 🛡️ TruthLens AI — Multimodal Video Forensics & Fact-Checking Engine

<div align="center">

[![Live Production App](https://img.shields.io/badge/🚀_LIVE_PRODUCTION_DEMO-CLICK_TO_LAUNCH_APP-6366f1?style=for-the-badge&logo=railway&logoColor=white&labelColor=0B0D0E)](https://multimodal-video-forensics-fact-checking-engine.up.railway.app/)
[![Automated Tests](https://img.shields.io/badge/Automated_Tests-52%2F52_Passing_(100%25)-10b981?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/parthdahiphale6363-ui/HACKMEN)
[![Python Version](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-4f46e5?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2016%20%7C%20React%2019-0ea5e9?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![Cloud Host](https://img.shields.io/badge/Cloud_Host-Railway_PaaS-0B0D0E?style=for-the-badge&logo=railway&logoColor=white)](https://railway.app)
[![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)](LICENSE)

### 🌐 **[👉 Open Live Interactive Web Application 👈](https://multimodal-video-forensics-fact-checking-engine.up.railway.app/)**
**Live Production URL:** `https://multimodal-video-forensics-fact-checking-engine.up.railway.app/`

*An advanced multimodal intelligence system that verifies short-form viral videos (YouTube Shorts) by combining OpenCV computer vision forensics, acoustic telemetry, real-time web fact-checking (OSINT), and cryptographic audit dossiers.*

</div>

---

## 📖 Table of Contents
1. [What is TruthLens AI?](#-what-is-truthlens-ai)
2. [Supported Inputs](#-supported-inputs)
3. [The 5-Level Forensic Verdict System](#-the-5-level-forensic-verdict-system)
4. [How It Works (The 4-Track Pipeline)](#-how-it-works-the-4-track-pipeline)
5. [Built-in Case Studies (Zero Latency)](#-built-in-case-studies-zero-latency)
6. [☁️ Railway Cloud Deployment Guide (Exhaustive)](#️-railway-cloud-deployment-guide-exhaustive)
   - [Railway Configuration Files in This Project](#railway-configuration-files-in-this-project)
   - [Architecture on Railway](#architecture-on-railway)
   - [Step 1: Deploy Backend Service](#step-1-deploy-backend-service)
   - [Step 2: Deploy Frontend Service](#step-2-deploy-frontend-service)
   - [Private Networking (.railway.internal)](#private-networking-railwayinternal)
7. [💻 Local Development & Quick Start](#-local-development--quick-start)
8. [🧪 Automated Testing & Verification](#-automated-testing--verification)
9. [📁 File & Directory Map](#-file--directory-map)
10. [📄 License & Ethics](#-license--ethics)

---

## 💡 What is TruthLens AI?

Think of **TruthLens AI** as an **AI-powered forensic laboratory and digital investigator** for viral video clips.

When millions of people watch a video on social media, two critical questions must be answered:
1. **Is the media real, AI-generated, or tampered with?** (Deepfake faces, synthetic cloned voices, spliced cuts, altered frames).
2. **Are the spoken claims true, misleading, or outright false?** (Cross-referenced against verified news, scientific journals, and certified fact-checkers).

TruthLens AI answers both questions at the same time using an evidence-first approach:
- **No Hallucinations**: Every fact-check is backed by verbatim quote citations from verified domains.
- **Traceable Timestamps**: Clickable video timestamps jump right to the suspicious frame or audio interval.
- **Independent Modalities**: Visuals and audio are tested separately so you know exactly which part was manipulated.
- **Cryptographic Audit Dossier**: Download a SHA-256 signed Markdown report with a complete chain of custody.

---

## 🎬 Supported Inputs

> [!IMPORTANT]
> **YouTube Shorts Only**: TruthLens AI is specifically optimized for short-form viral videos.
> - **Supported:** `https://www.youtube.com/shorts/VIDEO_ID` (or `https://youtube.com/shorts/...`)
> - **Not Supported:** Standard long-form YouTube videos (`/watch?v=`), playlists, TikTok, Instagram, or local files. The backend URL gate validates and strictly enforces Shorts format.

---

## ⚖️ The 5-Level Forensic Verdict System

TruthLens AI evaluates media against 5 clear, technically defensible verdict categories:

| Verdict Category | Display Label | Meaning | Example |
|---|---|---|---|
| **A. AI-Generated** | `LIKELY AI-GENERATED` | Strong detector evidence confirms synthetic creation in video, audio, or both. | Sora/Runway AI video, or fully synthesized ElevenLabs cloned voice. |
| **B. Partially AI-Generated** | `LIKELY PARTIALLY AI-GENERATED / AI-EDITED` | Media contains a mixture of genuine and synthetic/modified elements. | Authentic news footage with an AI voiceover narration, or real video with deepfake face swap. |
| **C. Likely Authentic** | `LIKELY AUTHENTIC — NO STRONG AI INDICATORS DETECTED` | No anomalies detected across assessed streams. Includes honest disclaimer that undetected AI manipulation remains possible. | Raw camera footage from a verified phone or camera with natural acoustics. |
| **D. Likely Manipulated** | `LIKELY MANIPULATED — ORIGIN UNDETERMINED` | Credible signs of editing, splicing, or compression mismatch, but origin cannot be proven as AI. | Re-encoded video with abrupt scene jump-cuts or truncated audio. |
| **E. Inconclusive** | `INCONCLUSIVE` | Resolution too low, duration too short, models timed out, or conflicting signals. | Low-bitrate 144p clip, silent video without visual faces, or network timeout. |

> [!NOTE]
> **Modality Independence Invariant**: If one modality fails (e.g. audio times out), it is **never** treated as proof of authenticity. The system marks that modality as `FAILED` and bases its overall verdict solely on the successful modality.

---

## 🔬 How It Works (The 4-Track Pipeline)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Uploaded YouTube Shorts URL                           │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    yt-dlp Demux (Video Stream + Audio Stream)
                                       │
        ┌──────────────────────────────┴──────────────────────────────┐
        ▼                                                             ▼
┌───────────────────────────────┐             ┌───────────────────────────────┐
│  Track 1: Visual Forensics    │             │  Track 2: Audio Forensics     │
│  • OpenCV frame sampling      │             │  • FFprobe acoustic streams   │
│  • Error Level Analysis (ELA) │             │  • Silence burst anomalies    │
│  • 2D FFT spectral analysis   │             │  • Gemini multimodal analysis │
│  • Face boundary jitter       │             │  • Voice clone probability    │
│  • Scene-cut detection        │             │  • 504 timeout recovery       │
└───────────────┬───────────────┘             └───────────────┬───────────────┘
                │                                             │
        ┌───────┴─────────────────────────────────────────────┴───────┐
        ▼                                                             ▼
┌───────────────────────────────┐             ┌───────────────────────────────┐
│  Track 3: Epistemic Claims    │             │  Track 4: OSINT & Patterns    │
│  • Groq Whisper Large v3      │             │  • Google Fact Check (IFCN)   │
│  • Groq Llama 3.3 70B claims  │             │  • NewsAPI & NewsData.io      │
│  • DuckDuckGo search          │             │  • DuckDuckGo / Wikipedia RAG │
│  • Verbatim quote offset      │             │  • Isolation Forest outliers  │
└───────────────┬───────────────┘             └───────────────┬───────────────┘
                │                                             │
                └──────────────────────┬──────────────────────┘
                                       ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  Evidence Fusion Engine & Sovereign Constitutional Veto     │
        │  • If Deepfake ≥ 70% or IFCN Debunked: Overrides to FALSE   │
        │  • 5-Factor Calibrated Composite Confidence Score           │
        └──────────────────────────────┬──────────────────────────────┘
                                       ▼
        ┌─────────────────────────────────────────────────────────────┐
        │  Interactive Reactive Dashboard + SHA-256 Audit Dossier    │
        └─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Built-in Case Studies (Zero Latency)

Want to see TruthLens AI in action without waiting for download and processing? Click any built-in scenario on the dashboard:

1. **⚡ Elon Musk AI Scam & Crypto Bait**:
   - *Anomaly*: Synthetic voice clone paired with an advance-fee crypto giveaway template.
   - *Result*: Sovereign Veto triggered $\rightarrow$ **FALSE (Deepfake)**, 94% Severity.
2. **🧬 Venom Genes & Human Empathy**:
   - *Anomaly*: Transcript normalized into scientific queries cross-referenced with PNAS genomics and Anthrozoös psychology research.
   - *Result*: **TRUE (Verified)**, 89% Integrity with verbatim quote offsets.
3. **🛡️ Recycled Combat Video & Bot CGI**:
   - *Anomaly*: ARMA 3 video game combat footage passed off as live warfare.
   - *Result*: IFCN Debunk triggered $\rightarrow$ **MISLEADING (Recycled CGI)**, 96% Severity.

---

## ☁️ Railway Cloud Deployment Guide (Exhaustive)

TruthLens AI is designed with native cloud configurations for instant, reliable deployment on **[Railway](https://railway.app)**.

### Railway Configuration Files in This Project

This repository includes pre-configured deployment definitions:

| File Path | Component | Purpose |
|---|---|---|
| [`railway.json`](file:///c:/Parth%202D/railway.json) | **Backend Service** | Configures Railway build (`DOCKERFILE`), custom start command, healthcheck path (`/health`), 120s timeout, and auto-restart policy. |
| [`Dockerfile`](file:///c:/Parth%202D/Dockerfile) | **Backend Container** | Lightweight Debian (`python:3.12-slim`) base installing `ffmpeg`, `curl`, `nodejs` (for yt-dlp challenges), Python dependencies, and starts Uvicorn on dynamic `${PORT}`. |
| [`frontend/railway.json`](file:///c:/Parth%202D/frontend/railway.json) | **Frontend Service** | Configures Next.js service on Railway using `NIXPACKS` or Dockerfile, starts Next on `${PORT:-3000}` with healthcheck at `/`. |
| [`frontend/Dockerfile`](file:///c:/Parth%202D/frontend/Dockerfile) | **Frontend Container** | Multi-stage Node.js 20 Alpine container building Next.js 16 with optimized standalone caching and telemetry disabled. |
| [`frontend/src/app/api/[...path]/route.ts`](file:///c:/Parth%202D/frontend/src/app/api/%5B...path%5D/route.ts) | **Dynamic Cloud Proxy** | Resolves internal Railway private networking (`.railway.internal`), public URLs, and local loopbacks automatically with zero manual proxy configuration. |

---

### Architecture on Railway

```
                   ┌────────────────────────────────────────────────────────┐
                   │                     Railway Project                    │
                   │                                                        │
┌──────────────┐   │  ┌───────────────────────┐   Internal Private Net      │
│ User Browser │───┼─>│ Frontend Service      │  (Zero egress bandwidth)    │
│              │   │  │ Next.js 16 (Port 3000)│──────────────┐              │
└──────────────┘   │  └───────────────────────┘              │              │
                   │                                         ▼              │
                   │                              ┌──────────────────────┐  │
                   │                              │ Backend Service      │  │
                   │                              │ FastAPI (Port 8000)  │  │
                   │                              │ FFmpeg + yt-dlp      │  │
                   │                              └──────────────────────┘  │
                   └────────────────────────────────────────────────────────┘
```

---

### Step 1: Deploy Backend Service

1. Log in to [Railway.com](https://railway.app) and create a **New Project**.
2. Select **Deploy from GitHub repo** and pick this repository.
3. Railway will detect the root [`railway.json`](file:///c:/Parth%202D/railway.json) and [`Dockerfile`](file:///c:/Parth%202D/Dockerfile).
4. In the service **Variables** tab, add your environment variables:
   ```ini
   # Required for AI Reasoning and Whisper Transcription
   GROQ_API_KEY=gsk_your_groq_api_key_here

   # Optional for Deep Audio & Voice Forensics
   GEMINI_API_KEY=AIzaSy_your_gemini_api_key_here
   GEMINI_TIMEOUT_SECONDS=25.0

   # Optional OSINT API Keys (System uses DuckDuckGo/Wikipedia if omitted)
   GOOGLE_FACTCHECK_API_KEY=your_google_key_here
   NEWS_API_KEY=your_newsapi_org_key_here
   NEWSDATA_API_KEY=your_newsdata_io_key_here

   # Environment setting
   ENVIRONMENT=production
   ```
5. In **Settings** $\rightarrow$ **Networking**, click **Generate Domain** (e.g. `truthlens-api.up.railway.app`).
6. Verify deployment by visiting `https://your-backend.up.railway.app/health`. You should see `{"status": "ok"}`.

---

### Step 2: Deploy Frontend Service

1. In the **same Railway project**, click **+ New Service** $\rightarrow$ **GitHub Repo** $\rightarrow$ select the same repository.
2. In the newly created service, go to **Settings**:
   - **Root Directory**: Set to `/frontend`
   - **Build**: Uses [`frontend/railway.json`](file:///c:/Parth%202D/frontend/railway.json) (or [`frontend/Dockerfile`](file:///c:/Parth%202D/frontend/Dockerfile)).
3. In the service **Variables** tab, set:
   ```ini
   # Point to your backend's public domain or internal network name
   BACKEND_URL=https://your-backend.up.railway.app
   NEXT_PUBLIC_BACKEND_URL=https://your-backend.up.railway.app
   ```
4. In **Settings** $\rightarrow$ **Networking**, click **Generate Domain** (e.g. `truthlens.up.railway.app`).
5. Open your public domain in your browser!

---

### Private Networking (`.railway.internal`)

Railway supports direct container-to-container private networking with zero egress costs and minimal latency:
- If your backend service is named `backend`, you can set your frontend variable to:
  ```ini
  BACKEND_URL=http://backend.railway.internal:8000
  ```
- TruthLens AI's dynamic proxy [`frontend/src/app/api/[...path]/route.ts`](file:///c:/Parth%202D/frontend/src/app/api/%5B...path%5D/route.ts) automatically discovers `.railway.internal` hosts and routes requests privately behind the scenes.

---

## 💻 Local Development & Quick Start

### Prerequisites
- **Python 3.11 or 3.12**
- **Node.js 20 or 22**
- **FFmpeg** installed and added to your system `PATH`

### 1. Clone & Set Up Python Environment
```bash
git clone https://github.com/parthdahiphale6363-ui/HACKMEN.git
cd HACKMEN

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Set Up Frontend
```bash
cd frontend
npm install
cd ..
```

### 3. Environment Variables
Create a `.env` file in the project root:
```ini
GROQ_API_KEY=gsk_your_groq_api_key
GEMINI_API_KEY=AIzaSy_your_gemini_api_key
GEMINI_TIMEOUT_SECONDS=25.0
PORT=8000
```

### 4. Run the Project

#### Option A: One-Click Startup (Windows)
```bat
run.bat
```

#### Option B: Manual Startup
```bash
# Terminal 1: Launch FastAPI Backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Launch Next.js Frontend
cd frontend
npm run dev
```

- **Frontend App**: `http://localhost:3000`
- **FastAPI Interactive Docs**: `http://localhost:8000/docs`
- **Backend Health Check**: `http://localhost:8000/health`

---

## 🧪 Automated Testing & Verification

TruthLens AI includes a complete automated test suite covering unit tests, SSRF validation, multi-modal evidence fusion, timeout handling, and frontend contracts:

```bash
# Run all tests
python -m pytest tests/ -v
```

### Key Test Suites:
- `tests/test_unified_forensics_verdicts.py`: Validates all 5 verdict categories, `504 DEADLINE_EXCEEDED` recovery, and API key sanitization.
- `tests/test_unified_media_authenticity.py`: Validates C2PA provenance credentials, SSRF protection, and script mismatch detection.
- `tests/test_opencv_gemini_forensics.py`: Validates Error Level Analysis (ELA), 2D FFT spectral regularity, and face jitter heuristics.
- `tests/test_complete_frontend_and_backend.py`: Validates end-to-end pipeline flow, dossier cryptographic hashing, and OSINT consensus.

---

## 📁 File & Directory Map

```
.
├── backend/
│   ├── main.py                     # FastAPI entry point, CORS, dynamic port handling
│   ├── routers/
│   │   ├── jobs.py                 # Job lifecycle, SSE events, export endpoints
│   │   └── health.py               # Health checks and latency metrics
│   └── services/
│       ├── job_service.py          # Background worker dispatcher & veto aggregation
│       ├── visual_forensics.py     # OpenCV ELA, FFT, and scene boundary analysis
│       ├── gemini_audio.py         # Gemini multimodal audio audit with 504 timeout recovery
│       ├── audio_authenticity.py   # Acoustic stream validation & voice clone metrics
│       ├── evidence_fusion.py      # Multi-modal priority rules & Section 7 contract synthesis
│       ├── osint.py                # Google Fact Check Tools API, NewsAPI, NewsData.io
│       ├── data_mining.py          # TF-IDF, Isolation Forest, and scam template similarity
│       ├── demo_cases.py           # Pre-loaded zero-latency demonstration scenarios
│       └── export_service.py       # Tamper-evident SHA-256 Markdown dossier generator
├── frontend/
│   ├── Dockerfile                  # Production Next.js 16 container definition
│   ├── railway.json                # Railway configuration for frontend service
│   ├── package.json                # React 19, Lucide, Tailwind, Next.js dependencies
│   └── src/
│       ├── app/
│       │   ├── page.tsx            # Main interactive dashboard with video seek sync
│       │   └── api/[...path]/      # Intelligent dynamic proxy for Railway & local development
│       └── components/
│           ├── ForensicsPanel.tsx  # Modality cards, DEADLINE_EXCEEDED alert, interactive timeline
│           ├── OverallVerdictBanner.tsx # Dynamic headline verdict with confidence badge
│           └── ExportDossierModal.tsx   # Markdown & JSON cryptographic export modal
├── pipeline/
│   ├── ingest.py                   # yt-dlp YouTube Shorts ingestion & audio demuxing
│   ├── claims.py                   # Groq Llama 3.3 70B claim extraction & normalization
│   ├── search.py                   # DuckDuckGo multi-query search engine
│   └── page_fetcher.py             # SSRF-safe page fetcher with verbatim quote offset locator
├── shared/
│   ├── schemas/
│   │   ├── forensics.py            # Section 7 unified report schemas & verdict enums
│   │   └── verdict.py              # Claim verification and stance schemas
│   └── resilience.py               # Circuit breaker and retry backoff utilities
├── tests/                          # 52+ automated unit, regression, and integration tests
├── Dockerfile                      # Production backend container (Python 3.12 + FFmpeg)
├── railway.json                    # Production backend Railway configuration
├── docker-compose.yml              # Local multi-service container orchestration
├── requirements.txt                # Python backend dependencies
└── run.bat                         # One-click Windows startup script
```

---

## 📄 License & Ethics

TruthLens AI is licensed under the [MIT License](LICENSE).

### Responsible AI & Academic Disclaimer
Automated forensic detection, acoustic anomalies, and AI reasoning chains are engineered as **decision-support intelligence for journalists, fact-checkers, and researchers**. No automated software can guarantee 100% detection of every adversarial deepfake or subtle edit. All findings are presented with explicit confidence metrics, evidence citations, and technical boundaries.

<div align="center">
  <sub>TruthLens AI Intelligence Platform — Built with rigorous engineering standards for digital media authenticity.</sub>
</div>
