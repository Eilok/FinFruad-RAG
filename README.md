# FinFraud-RAG

A financial fraud risk governance system (RAG) that supports:
- Offline knowledge base construction (LLM structured extraction + vector ingestion)
- Online dual-retrieval detection (BM25 + vector)
- Frontend interaction (detection + new text ingestion)
- Automated comparative evaluation (RAG vs NoRAG)

## Project Structure

```text
.
├─ backend/
│  ├─ service/                  # Interface-layer code only
│  ├─ core/                     # Core business workflows
│  ├─ providers/                # LLM/Embedding adapters
│  ├─ storage/                  # Chroma wrapper
│  ├─ scripts/                  # Backend script entrypoints
│  └─ outputs/eval/             # Evaluation artifacts
├─ webui/                       # Next.js frontend
├─ data/                        # Datasets
├─ scripts/                     # Unified Windows command entrypoints
├─ SPECS/                       # Phase specification docs
└─ AGENTS.md                    # Development conventions
```

## Requirements

1. Python 3.12+
2. Node.js 18+
3. `uv`

## Installation and Setup

### 1) Install Dependencies

Backend:

```bash
uv sync
```

Frontend:

```bash
cd webui
npm install
```

### 2) Configure Environment Variables

```bash
cp .env.example .env
```

Key variables:
- `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`: LLM configuration
- `SILICONFLOW_API_KEY` / `SILICONFLOW_BASE_URL` / `EMBEDDING_MODEL`: embedding model configuration
- `CHROMA_PERSIST_DIR`: vector database persistence path
- `CHROMA_COLLECTION_NAME`: default online collection (used by frontend/online detection)
- `EVAL_COLLECTION_PREFIX`: prefix for isolated evaluation collections
- `REQUEST_TIMEOUT_SECONDS`: external request timeout (seconds)
- `CORS_ORIGINS`: allowed CORS origins, comma-separated
- `NEXT_PUBLIC_API_BASE_URL`: frontend backend endpoint

## Unified Command Entrypoints (Windows)

Run from project root:

- Start backend:

```powershell
./scripts/start_backend.ps1
```

- Start frontend:

```powershell
./scripts/start_webui.ps1
```

- Ingest a single fraud text:

```powershell
./scripts/ingest_one.ps1 -Text "Limited-time investment plan, guaranteed 20% daily return" -Source manual
```

- Run full evaluation:

```powershell
./scripts/run_eval.ps1 -TestLimit 500 -TrainPositiveLimit 0 -KeywordTopK 3 -VectorTopK 3
```

- Run quick smoke evaluation (1–5 samples):

```powershell
./scripts/run_eval_smoke.ps1 -TestLimit 2 -TrainPositiveLimit 3
```

## Quick Start (End-to-End)

1. Start backend: `./scripts/start_backend.ps1`
2. Start frontend: `./scripts/start_webui.ps1`
3. Open frontend: `http://localhost:3000`
4. In the frontend, run `Knowledge Ingestion` first (input or upload text)
5. Then run `Run Detection` in the detection area

Backend health check:

```bash
curl http://localhost:8000/healthz
```

## Offline Knowledge Base Construction

### API Method

`POST /kb/ingest`

Request example:

```json
{
  "items": [
    {
      "text": "No experience needed, earn high commission daily, pay deposit first.",
      "source": "manual"
    }
  ],
  "retry_times": 2
}
```

### CLI Method

- Single text:

```bash
uv run python -m backend.scripts.ingest_kb --text "High return, instant transfer required" --source manual
```

- Batch mode (`txt/jsonl`):

```bash
uv run python -m backend.scripts.ingest_kb --input-file data/sample_ingest.jsonl --source dataset --retry-times 2
```

## Online Detection (BM25 + Vector)

`POST /detect`

Request example:

```json
{
  "text": "Support asks me to transfer money now to avoid subscription charges.",
  "keyword_top_k": 3,
  "vector_top_k": 3,
  "return_evidence": true
}
```

Response:
- `keyword_hits` (BM25 channel)
- `vector_hits`
- `fused_hits`
- `detection` (`is_scam/confidence/reason/evidence_refs`)

Notes:
- Evidence references in prompts are compressed to short IDs (`ref_id=1,2,3...`) to save tokens.
- The final `evidence_refs` returned to users are mapped back to real `record_id` values.

## Frontend Features

The frontend supports:
1. New fraud text ingestion
- Single-text ingestion
- Batch ingestion by uploading `.txt/.jsonl`
2. Online detection
- BM25 top-k / vector top-k parameter configuration
- Detection results and three-channel evidence display
3. Interaction
- `Retry / Clear / Copy JSON`

## Automated Evaluation and Experiment Isolation

### Data Preparation

Download `job_scams` and `sms` subsets from the [difraud](https://huggingface.co/datasets/difraud/difraud) dataset and place them under `data/`.

### Default Isolation Strategy

`run_eval` uses isolated collections by default and does not contaminate the online collection:

- Auto name: `{EVAL_COLLECTION_PREFIX}_{run_id}`
- Manual override: `--collection-name`

### Full Evaluation

```bash
uv run python -m backend.scripts.run_eval --test-limit 500 --train-positive-limit 0 --keyword-top-k 3 --vector-top-k 3
```

### Smoke Evaluation (recommended first)

```bash
uv run python -m backend.scripts.run_eval_smoke --test-limit 2 --train-positive-limit 3
```

### Real-Time Logging Guarantee

Evaluation logs are flushed per sample in real time (not written only at the end):
- `no_rag_logs.jsonl`
- `rag_logs.jsonl`

So completed records are preserved even if execution is interrupted.

## Output Directories

- Vector DB directory: `backend/.chroma/`
- Runtime logs: `backend/logs/`
- Evaluation artifacts: `backend/outputs/eval/{run_id}/`
  - `no_rag_logs.jsonl`
  - `rag_logs.jsonl`
  - `summary.json`

## FAQ

1. Frontend `OPTIONS /detect` returns 405
- Check whether `CORS_ORIGINS` contains your frontend domain.

2. `Collection ... does not exist`
- Self-healing rebinding is implemented; if it still happens, ensure you are not running multiple reset tasks concurrently on the same collection.

3. No retrieval results
- Confirm ingestion has completed and verify the service is using the expected collection.

4. Model call failures
- Check API key, base URL, model name, and network availability.

## Minimal Pre-Release Checklist

1. `uv sync` succeeds and dependencies are consistent.
2. Required `.env` fields are configured.
3. Backend `healthz` is healthy.
4. Frontend can complete one ingestion + one detection.
5. Smoke evaluation runs and generates `summary.json`.
6. Isolation between evaluation collections and online collection is verified.
