# TestGen AI 🧪

> **AI-powered unit test generation** using **NVIDIA Nemotron** on **Nebius AI Cloud**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Powered by Nebius](https://img.shields.io/badge/Powered%20by-Nebius%20AI%20Cloud-purple)](https://nebius.com)
[![NVIDIA Nemotron](https://img.shields.io/badge/Model-NVIDIA%20Nemotron-76b900)](https://www.nvidia.com/en-us/ai/)

---

## What It Does

TestGen AI is an intelligent agent that:

1. 🔍 **Analyzes** your Python code using AST parsing
2. 📋 **Plans** a comprehensive test strategy (happy paths, edge cases, error conditions)
3. ⚡ **Generates** a full `pytest` test file using **NVIDIA Nemotron** on **Nebius AI Cloud**
4. 🧪 **Executes** tests in a sandboxed subprocess environment
5. 🔧 **Iteratively fixes** any failing tests automatically (up to 3 iterations)

All powered by a multi-step agentic pipeline with real-time streaming feedback.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                      │
│  Monaco Editor │ Agent Log (SSE) │ Test Results          │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP + Server-Sent Events
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                          │
│  POST /api/stream  →  Agent Pipeline (SSE streaming)     │
│  POST /api/generate → Agent Pipeline (blocking)          │
└────────────────────────┬────────────────────────────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
              ▼                     ▼
┌─────────────────────┐  ┌──────────────────────┐
│  Nebius AI Cloud     │  │  Local Sandbox        │
│  NVIDIA Nemotron     │  │  subprocess + pytest  │
│  (OpenAI-compatible) │  │  temp directory       │
└─────────────────────┘  └──────────────────────┘
```

## NVIDIA Nemotron Usage

| Pipeline Step | Model | Why |
|---|---|---|
| Test Strategy Planning | Nemotron 70B | Fast analysis of code structure |
| Test Code Generation | Nemotron 70B | Complex reasoning to write correct tests |
| Iterative Test Fixing | Nemotron 70B | Reasoning about failures + fixes |

**Nebius AI Cloud** provides OpenAI-compatible inference endpoints for Nemotron models, accessed at `https://api.studio.nebius.ai/v1/`.

---

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A **Nebius AI Cloud** API key → [Get one at studio.nebius.ai](https://studio.nebius.ai)

### 1. Clone & Configure

```bash
git clone https://github.com/YOUR_USERNAME/testgen-ai
cd testgen-ai
```

### 2. Backend

```bash
cd backend
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env and add your NEBIUS_API_KEY

# Start the server
uvicorn main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit **http://localhost:3000** 🎉

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `NEBIUS_API_KEY` | Your Nebius AI Cloud API key | **Required** |
| `NEBIUS_BASE_URL` | Nebius API base URL | `https://api.studio.nebius.ai/v1/` |
| `MODEL_FAST` | Model for analysis steps | `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF` |
| `MODEL_SMART` | Model for generation/fixing | `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF` |
| `MAX_FIX_ITERATIONS` | Max auto-fix iterations | `3` |
| `SANDBOX_TIMEOUT` | Test execution timeout (s) | `30` |

---

## How It Works (Technical Detail)

### Multi-Step Agent Pipeline (`backend/agent.py`)

```
Step 1: AST Parse → extract functions, types, docstrings
Step 2: Nemotron → plan 8-12 test scenarios
Step 3: Nemotron → generate full pytest file
Step 4: subprocess → run pytest with JSON report
Step 5: (if failures) Nemotron → fix failing tests → re-run
```

### Sandbox Execution (`backend/sandbox.py`)
- Writes source + test files to an ephemeral `tempfile.TemporaryDirectory`
- Runs `pytest` via subprocess with 30s timeout
- Parses structured JSON report (`pytest-json-report`)
- Returns per-test pass/fail/duration/error details

### Streaming (`/api/stream`)
- Uses **Server-Sent Events** for real-time step updates
- Frontend consumes SSE and updates UI progressively
- Each pipeline step emits a structured event

---

## Nebius Tools Used

- **Nebius AI Studio / Token Factory** — Hosted NVIDIA Nemotron inference endpoint
- **OpenAI-compatible API** at `https://api.studio.nebius.ai/v1/`

---

## License

MIT © 2024
