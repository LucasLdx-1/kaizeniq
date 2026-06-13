# Running KaizenIQ locally

This guide walks through running KaizenIQ end to end, including the
**Foundry Local** integration (a real Microsoft Foundry-hosted model running
on your machine). It mirrors the exact setup that was used to build and test
the project.

KaizenIQ has three execution modes, selected by the `FOUNDRY_MODE` environment
variable:

- **`mock`** (default) — fully offline, no model, deterministic responses. The
  whole portal works; great for a first run.
- **`local`** — a real Microsoft Foundry model runs on your device via Foundry
  Local. This is the recommended mode for the demo.
- **`live`** — real Azure Foundry IQ (requires Azure AI Search + Azure OpenAI).

You can run the entire project in **mock mode with zero AI setup**. Foundry
Local is only needed for `local` mode.

---

## Prerequisites

- **Python 3.10+** (3.13 was used in development)
- **Node.js 18+** (for the React frontend)
- **Windows, macOS, or Linux**. Steps below are written for Windows; the
  commands are nearly identical elsewhere.

> Tip: if `python`, `node`, or `npm` are "not recognized", the tool is either
> not installed or not on your PATH. On Windows you can add a portable install
> to the current terminal session, e.g. in PowerShell:
> `$env:Path = "C:\path\to\node;" + $env:Path`

---

## 1. Backend (mock mode — no AI setup needed)

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs to see the API, or
http://localhost:8000/api/health — `foundry_iq.mode` will read `mock`.

## 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The portal loads with all pages:
Dashboard, Talk to Agents, Add Process, Company Map, Agent Portfolio,
Non-Conformities, and Telemetry & Safety.

At this point everything works in mock mode. To use a real Microsoft Foundry
model, continue to step 3.

---

## 3. Foundry Local (real Microsoft Foundry model, on-device)

Foundry Local runs a curated Foundry catalog model (here, `phi-3.5-mini`)
locally and exposes an OpenAI-compatible endpoint. **No Azure subscription is
required.**

### 3.1 Install Foundry Local

```bash
winget install Microsoft.FoundryLocal
```

(installs without administrator rights). Verify:

```bash
foundry --version
```

### 3.2 Download and run the model

```bash
foundry model run phi-3.5-mini
```

The first run downloads the model (a few minutes; cached afterwards). When you
see the interactive `>` prompt and a response to a test message, the model is
loaded. You can type `/exit` to leave the chat — **the service keeps running**.

> The startup log may print a few `Failed to process model ... page` lines
> while it fetches the catalog list. As long as it ends with
> `Model ... loaded successfully`, you are fine. If the model does not load on
> the first attempt, restart the service:
> `foundry service stop` then `foundry service start`, and run the model again.

### 3.3 Find the service endpoint

Foundry Local picks a **random port** each time it starts. Find it with:

```bash
foundry service status
```

Look for a URL like `http://127.0.0.1:61980/...`. Note the port number.

You can sanity-check the OpenAI-compatible endpoint directly (replace the port):

```bash
python -c "from openai import OpenAI; c = OpenAI(base_url='http://127.0.0.1:61980/v1', api_key='not-needed'); print([m.id for m in c.models.list().data])"
```

It should print the loaded model id, e.g. `['phi-3.5-mini-instruct-...']`.

### 3.4 Point KaizenIQ at Foundry Local

Install the extra backend dependencies (if not already):

```bash
cd backend
python -m pip install foundry-local-sdk openai
```

Create a `backend/.env` file (this file is git-ignored and must never be
committed). Use the port from step 3.3:

```env
FOUNDRY_MODE=local
FOUNDRY_LOCAL_MODEL=phi-3.5-mini
FOUNDRY_LOCAL_ENDPOINT=http://127.0.0.1:61980/v1
```

> The backend can also auto-discover the endpoint via `foundry service status`,
> but setting `FOUNDRY_LOCAL_ENDPOINT` explicitly is the most reliable approach
> because the port changes on every restart.

### 3.5 Restart the backend

Stop the backend (Ctrl+C) and start it again:

```bash
python -m uvicorn main:app --reload --port 8000
```

On startup you should see a line like:

```
Foundry Local CONNECTED (model=phi-3.5-mini-instruct-..., endpoint=http://127.0.0.1:61980/v1)
```

Confirm at http://localhost:8000/api/health — `foundry_iq.mode` now reads
`local` and a `foundry_local_model` field appears.

---

## 4. Try it

With backend (local mode) and frontend running, and Foundry Local serving:

- **Talk to the Agents** — ask "Which processes are most critical?"; the local
  Foundry model answers, grounded in the catalog, with `[PROC-xxx]` citations.
- **Add Process** — paste a name, area, and steps; the model infers the ISO
  clause and KPIs, draws the flowchart, and folds the process into the live
  analysis and the Company Map.
- **Telemetry & Safety** — watch model/agent call counts and latencies update.

---

## Common issues

| Symptom | Fix |
|---|---|
| `No module named uvicorn` | Wrong Python active. Use the environment where you ran `pip install` (e.g. `conda activate base`), or `python -m pip install -r requirements.txt` again. |
| `/api/health` shows `mock` after setup | Foundry Local service not running, or `FOUNDRY_LOCAL_ENDPOINT` port is stale. Re-run `foundry service status`, update `.env`, restart the backend. |
| `npm` not recognized | Node not on PATH for this terminal. Add it (see the PATH tip above). On Windows PowerShell, use `npm.cmd` to avoid script-execution prompts. |
| Model fails to load on first run | `foundry service stop && foundry service start`, then `foundry model run phi-3.5-mini` again. |
| Port already in use (8000) | Start uvicorn on another port: `--port 8010` (and update the frontend proxy in `vite.config.js` if needed). |

---

## Notes on data and safety

All data is synthetic (the fictional "Meridian Industries Ltd."). No real or
personal data is used. The `.env` file is git-ignored; never commit secrets or
endpoints to a public repository.
