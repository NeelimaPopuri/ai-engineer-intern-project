# AI usage log

A running record of what I asked AI tools to do, what they produced, what I verified or changed, and what I built myself. Swap this for the official program template if one is issued.

Tools used: Claude Code (pair programmer).

## Entries

| Date | Task | What I asked the AI | What it produced | What I verified or changed |
|---|---|---|---|---|
| 2026-09-29 | Initial Day 1 app | Build the FastAPI backend, React frontend, tests and docs | Backend with `/api/v1/chat`, React UI in DataFactZ branding, README, architecture doc | Ran and tested the app |
| 2026-11-18 | Diagnose "model provider returned an error" | Find why the UI showed a generic error | Reproduced the call and found the Anthropic key was rejected with a 401 | Confirmed the error myself in the UI; chose not to use a paid Anthropic account |
| 2026-11-18 | Switch LLM provider | Replace Anthropic with a free provider | Gemini integration via `httpx`, updated tests, config and docs | Created my own Gemini key in Google AI Studio and put it in `.env` |
| 2026-11-18 | Fix model errors | Find why Gemini still failed | Found a retired model name (404) and an overloaded model (503); switched to `gemini-3.1-flash-lite`; added retry on 429 and 503 | Ran the app and confirmed a reply |
| 2026-11-18 | Backend start error | Run the backend | Found `uvicorn.exe` blocked by an Application Control policy; ran it with `python -m uvicorn` instead | Confirmed the app works through the UI |
| 2026-11-18 | Broken page layout | Find why the page looked unstyled | Found a stale Vite dev server serving unprocessed Tailwind; restarted it | Confirmed the page rendered correctly |
| 2026-11-18 | Git workflow | Commit and push | Two commits and a branch push | Opened and merged the pull request myself |
| 2026-11-18 | Cost estimate | Write a pilot and production cost estimate | `docs/cost-estimate.md` with verified Gemini token prices | Token prices verified on Google's pricing page; hosting figures are planning estimates, not yet checked in the Azure pricing calculator |
| 2026-11-18 | UC1 problem statement | Pick an advanced scenario built on a current market problem, in the style of a professional services firm | Regulatory change navigator for EU sustainability reporting, written up in `uc1-rag-chatbot/docs/problem-statement.md` | Success targets are proposals; regulatory facts are not yet checked against official sources |
| 2026-11-18 | UC1 database design | Design the database for the chatbot | 8-table schema with an ERD, indexes and five decisions with rejected alternatives in `database-design.md` | Not yet reviewed in a mentor session |
| 2026-11-18 | UC1 solution design | Write the solution design document | Architecture, data flow, API routes and seven pattern justifications in `solution-design.md` | Azure feature and model claims are marked "verify" and are not yet checked |
| 2026-11-18 | UC1 backend foundation | Build the schema, migration and date-aware version lookup | SQLAlchemy models, an Alembic migration, `versions.py` and 7 tests | Ran the migration (8 tables created) and the tests |
| 2026-11-19 | Design doc update | Rewrite the design to match a local build, since there is no Azure access | Section 1.1 "Deviation from the required stack" and relabelled Azure options as target, local as pilot | Checked that no claim says Azure was deployed |
| 2026-11-19 | UC1 chunking and ingestion | Build document chunking and versioned ingestion | `chunking.py`, `ingestion.py` and 13 new tests (20 total passing) | Ran the full test suite |
| 2026-11-19 | UC1 source library | Collect public EU sustainability reporting documents | `collect_sources.py`, 10 documents (2.1 MB) in `data/sources/` and `sources.csv` | I approved the download list. Checked each legal text's title and in-force date against the Official Journal wording. The EUR-Lex bot check was not bypassed |
| 2026-11-19 | UC1 data loading | Load the library into the database | `load_sources.py`: 7 documents, 10 versions, 2,047 chunks, versions chained by date | Checked the version dates and end dates in the database |
| 2026-11-19 | UC1 embeddings and search | Add embeddings and local hybrid search with date and country filters | `embeddings.py`, `search.py`, `embed_chunks.py`, a migration and 5 new tests (25 passing) | Tests use a fake embedder. The live Gemini embedding call was run on 50 chunks before the full run |

## What I built or decided myself

- I understood the requirements for the Day 1 app.
- I chose Gemini over a paid account.
- I created my own Gemini API key.
- I ran and tested the app together with Claude Code.
- I opened the pull request and merged it.
- I reviewed the architecture document.
- I chose the direction for the UC1 scenario: an advanced case built on a current market problem, in the style of a professional services firm.
- I decided to build UC1 locally with Gemini because Azure access and the issued model keys were not available.
- I planned Week 1: two build days, a review day, a demo to friends and a presentation to my mentor.

## What I can explain

- **API key check:** I protect the chat endpoint with a key. The request must send the correct `X-API-Key` header, otherwise the API answers 401, so only my own frontend can use it.
- **Request validation:** I check the prompt before calling the model. It must be between 1 and 2,000 characters, otherwise the API answers 422 and no money is spent on the model.
- **Gemini call:** my backend sends the prompt to Gemini over HTTP with `httpx` and sends back the reply text and the model name.
- **Retry logic:** Gemini is sometimes overloaded and answers 503 or 429. My backend waits a moment and tries again, up to 3 times, so short overloads do not show up as errors for the user.
- **Error handling:** if Gemini still fails, my API answers 502, which means the problem is the model provider and not my server. If the key is wrong, the message tells me to check `GEMINI_API_KEY`.
- **Dev proxy:** the browser talks to the Vite dev server, which passes the request to FastAPI and adds the app key. This keeps the key out of the browser code. A `VITE_` variable would have exposed it.
- **Config:** the settings are read from `.env` into typed fields. If a key is missing, the app stops at startup, so I find the mistake right away.
- **Secrets:** `.env` is git-ignored and only `.env.example` is committed, so no real key is in the repository.
- **Tests:** six automated tests check health, the key check, validation, a good reply, a provider failure and a bad key. They use fake Gemini answers, so they never call the real API.
- **Cost:** one request costs about $0.000475, mostly from output tokens. That is about $36 a month for 100 users. The full math is in `cost-estimate.md`.
