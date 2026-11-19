# Use Case 1: Regulatory change navigator

A retrieval-augmented chatbot that answers EU sustainability reporting questions from a controlled library of public sources, with citations and date-aware answers.

**Stack as built:** Python 3.12, FastAPI, SQLAlchemy with Alembic (SQLite locally, PostgreSQL by changing `DATABASE_URL`), Gemini for chat and embeddings, local hybrid search, React (Vite), Tailwind CSS, Lucide icons. The Azure stack in the program brief is the design target; see the deviation in the [solution design](docs/solution-design.md).

**Status:** working end to end. 37 backend tests pass and 19 of 20 evaluation questions are correct.

## Documents

- [Problem statement](docs/problem-statement.md)
- [Database design](docs/database-design.md)
- [Solution design](docs/solution-design.md)
- [Cost estimate](docs/cost-estimate.md)
- [Evaluation results](docs/evaluation-results.md)

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
3. Rerun the evaluation after the embedding quota resets, and compare a second model.
4. Add conflict detection between sources and the company-size filter.
