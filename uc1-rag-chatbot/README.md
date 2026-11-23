# Use Case 1: Regulatory change navigator

A retrieval-augmented chatbot that answers EU sustainability reporting questions from a controlled library of public sources, with citations and date-aware answers.

**Stack as built:** Python 3.12, FastAPI, SQLAlchemy with Alembic (SQLite locally, PostgreSQL by changing `DATABASE_URL`), Gemini for chat and embeddings, local vector search (switchable to hybrid with `SEARCH_BACKEND`), React (Vite), Tailwind CSS, Lucide icons. The Azure stack in the program brief is the design target; see the deviation in the [solution design](docs/solution-design.md).

**Status:** working end to end on vector search. 62 backend tests pass. The first full 40-question run scored 36 correct (90%); a clean rerun is pending the embedding quota reset.

## Documents

- [Problem statement](docs/problem-statement.md)
- [Database design](docs/database-design.md)
- [Solution design](docs/solution-design.md)
- [Architecture walkthrough](docs/architecture-walkthrough.md) (a speaking guide: every step, the options, and why we chose what we chose)
- [Cost estimate](docs/cost-estimate.md)
- [Evaluation results](docs/evaluation-results.md)
- [Model comparison](docs/model-comparison.md)
- [Status report](docs/status-report.md)
- [Pinecone setup](docs/pinecone-setup.md) (optional vector store)

## Run it

Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and `APP_API_KEY`. Then, from this folder:

```bash
# backend (first time: create the venv and install requirements.txt and requirements-dev.txt)
cd backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe ../scripts/load_sources.py
.venv/Scripts/python.exe ../scripts/embed_chunks.py     # optional, limited by the free-tier daily quota
.venv/Scripts/python.exe -m uvicorn app.main:app --port 8001
```

```bash
# frontend, in a second terminal (first time: npm ci --legacy-peer-deps)
cd frontend
npm run dev
```

Open the address Vite prints (port 5174, or the next free one).

Other commands, from `backend`:

```bash
.venv/Scripts/python.exe -m pytest                       # unit tests, no real model calls
.venv/Scripts/python.exe ../scripts/run_eval.py          # evaluation questions, calls Gemini
.venv/Scripts/python.exe ../scripts/collect_sources.py   # re-download the source library
```

## Next steps

1. Confirm the scenario against the UC1 brief.
2. Get Azure access and issued keys, then swap in Azure AI Search and Azure OpenAI.
3. Rerun the evaluation with 40 questions after the embedding quota resets.
4. Compare a Claude or Azure OpenAI model once keys are available.
