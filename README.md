<<<<<<< HEAD
# jevdemo
System One Model - Jev
=======
# 🏁 LLM Grand Prix

A car-racing benchmark for LLMs. Each model is a car in its own lane. When you press **Start Race**, the backend sends the same random **multiple-choice** (A–D) math or trivia question to every model at once over streaming chat completions.

- Cars move forward as tokens stream in. Reasoning/"thinking" tokens count too.
- A car crosses the finish line when its response completes with a **correct** answer.
- **Wrong answer** → the car crashes 💥 just short of the line.
- **Error / timeout / unreachable / missing key** → the car stalls 🛑 where it is. The other cars keep racing.
- The **first correct finisher wins**.

### Why multiple choice? (Jev)

`typesafe/jev-1.13.0` is a TypeSafe **decision model**, not a text generator. It only answers typed questions (yes/no, choice, score) passed via `response_format: {"type": "questions", ...}`, and it doesn't stream. So that every car gets the same question, every race is multiple choice:

- Chat models see the question and options A–D, and reply ending with `ANSWER: <letter>`.
- Jev gets the same options as a `choice` question and returns its pick plus a confidence score.
- Jev's car sits at the start while it decides, then jumps to the line when its one-shot answer arrives. Its TTFT equals its total time, and tok/s is n/a.

Models are marked `"kind": "jev"` or `"kind": "chat"` (the default) in `models.json`.

After each race you get a results table: TTFT, total time, tokens/sec, input/output tokens, cost, and correctness. Click a row to see the full response. A persistent championship scoreboard tracks wins, C/W/E counts, average tok/s, average time, and total cost.

```
backend/   FastAPI + OpenAI Python SDK, SSE stream  (port 8010)
frontend/  React + Vite + TypeScript + Tailwind v4  (port 5173, proxies /api → 8010)
```

## Setup

Prerequisites: Python 3.11+, Node 20+, and (optionally) [Ollama](https://ollama.com) running locally.

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env
```

Put your keys in `backend/.env`. They are only read by the backend and never sent to the browser.

```
KODEKLOUD_API_KEY=...
GEMINI_API_KEY=...
```

For the local car: `ollama pull llama3.2:3b`

Verify the model IDs against each provider's `GET /models`:

```powershell
python -m app.verify_models
```

It prints `OK`, or `NOT FOUND - did you mean: ...` with the closest IDs the provider lists. Fix any mismatches in `backend/models.json`. The same check also runs (as warnings) every time the server starts.

Run the backend:

```powershell
uvicorn app.main:app --port 8010 --reload
```

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

If the backend is on another host or port, set `BACKEND_URL` first: `$env:BACKEND_URL="http://localhost:9000"; npm run dev`.

## Configuration: `backend/models.json`

All racers live in this one file. Each entry is an OpenAI-compatible endpoint:

```json
{
  "id": "gemini",
  "name": "Gemini 2.5 Flash (free)",
  "model": "gemini-2.5-flash",
  "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
  "api_key_env": "GEMINI_API_KEY",
  "color": "#eab308",
  "price_input_per_m": 0,
  "price_output_per_m": 0
}
```

- `api_key_env: null` is for keyless local servers (Ollama).
- `race.timeout_seconds` is the hard per-model limit. `race.connect_timeout_seconds` is how quickly an unreachable host is declared stalled. `race.max_tokens` caps each response.
- Add a racer by adding an entry to this file. No code changes are needed.

**Prices** are USD per 1M tokens. The defaults for the KodeKloud models are placeholders, so edit them in the **Prices** panel in the UI (saved to `backend/data/prices.json`) or in `models.json`. Ollama and Gemini free tier are $0.

## How it's measured

| Metric | Definition |
|---|---|
| TTFT | Request sent → first content or reasoning token |
| Total time | Request sent → stream closed |
| Tokens/sec | Output tokens ÷ (total time − TTFT) |
| Tokens | From the provider's `usage` (`stream_options.include_usage`). If a provider omits it, the count is estimated (~4 chars/token) and marked `~` |
| Cost | `in_tokens × input_price + out_tokens × output_price` (per 1M) |
| Correct | The chosen option letter matches the correct one. Chat answers like `B`, `(B)`, `B) 1110`, or just the option text are accepted |

## Troubleshooting

- **`CERTIFICATE_VERIFY_FAILED`**: antivirus or a corporate proxy is inspecting HTTPS. The backend uses [`truststore`](https://pypi.org/project/truststore/) to trust the OS certificate store, which normally fixes this.
- **A car stalls with a 404**: the model ID is wrong. Run `python -m app.verify_models`.

## API

| Method | Path | |
|---|---|---|
| GET | `/api/config` | Models and prices (never includes keys, only `has_key`) |
| GET | `/api/race/stream?models=a,b` | **SSE**: runs a race. Events: `race_start`, `progress`, `finish`, `race_end` |
| PUT | `/api/prices/{id}` | `{ "input": 0.5, "output": 1.5 }` |
| GET | `/api/scoreboard` | Running scoreboard |
| POST | `/api/scoreboard/reset` | Reset scoreboard |
| GET | `/api/verify-models` | Check model IDs against providers' `/models` |

Scoreboard and price overrides are stored in `backend/data/`. Delete that folder to start fresh.
>>>>>>> 5a83a29 (adding jevdemo project initial setup)
