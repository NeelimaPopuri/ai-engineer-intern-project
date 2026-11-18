# Day 1: Hello World

A full-stack smoke test: FastAPI backend with one authenticated LLM endpoint, and a React frontend in DataFactZ branding.

**Stack:** Python 3.12, FastAPI, Pydantic, Gemini API (via httpx), React (Vite), Tailwind CSS, Lucide icons.

## Features

- Versioned REST API under `/api/v1` with generated OpenAPI docs at `/docs`
- API-key authentication and correct status codes (401, 422, 502)
- Typed configuration from environment variables
- Loading and error states in the UI
- Automated tests for auth, validation, success, and provider failure

## Run locally (Windows PowerShell)

1. `copy .env.example .env`, then fill in your keys. Never commit `.env`.
2. Backend:
   ```
   cd backend
   uv venv
   .venv\Scripts\activate
   uv pip install -r requirements-dev.txt
   uvicorn app.main:app --reload --port 8000
   ```
3. Frontend, in a second terminal:
   ```
   cd frontend
   npm install
   npm run dev
   ```
4. Open http://localhost:5173

## Tests

```
cd backend
pytest
```

## Documentation

See [docs/architecture.md](docs/architecture.md) for the diagram, design decisions, and scaling notes, and [docs/cost-estimate.md](docs/cost-estimate.md) for pilot and production running costs.
