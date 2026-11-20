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
| 2026-11-19 | UC1 chat API | Build conversations, cited answers, refusal and citation checks | `answer.py`, `llm.py`, routes in `main.py` and 10 new tests | Tests use fake models. A parsing bug (citations like [4, 6]) was found by running the real model and fixed |
| 2026-11-19 | UC1 evaluation | Write 20 test questions and a scoring script | `eval_questions.json`, `run_eval.py`, `evaluation-results.md`: 19 of 20 correct | I checked the expected facts against the source texts. One expectation was wrong and was corrected with a written reason, not tuned to pass |
| 2026-11-19 | UC1 chat screen | Build the React chat page with date and country filters | `uc1-rag-chatbot/frontend/` | Tried it in the browser: cited answer for 2026, refusal for 2024. Found and fixed a crash in the scroll effect |
| 2026-11-19 | UC1 cost estimate | Write the pilot and production cost estimate | `uc1-rag-chatbot/docs/cost-estimate.md` | Model and embedding prices read from Google's pricing page. Azure infrastructure prices are estimates and not verified |
| 2026-11-19 | UC1 source flag and citation numbering | Flag answers that mix legal text with news pages, and renumber citation markers to match saved ranks | Changes in `answer.py` and 3 new tests (40 passing). The numbering bug was reported by another Claude session working for me | Tests pass. The second session did not edit any files |
| 2026-11-19 | UC1 vector search | Switch search to a vector database | `VectorIndex` and `FallbackIndex` in `search.py`, a `SEARCH_BACKEND` setting and 8 new tests (48 passing) | ChromaDB, Qdrant and FAISS were tried and are blocked by Windows Application Control on this machine, so I did not bypass it and built an in-memory vector index instead. Checked: 60 of 60 chunks find themselves first, 16 ms. Live questions not yet tested because the embedding quota is exhausted |
| 2026-11-19 | UC1 infrastructure prices | Replace my guessed Azure prices with standard list prices | Cost estimate now uses prices from the Azure Retail Prices API: about $126 a month pilot, about $1,752 production | I asked for standard prices. Prices were read from Azure's public API, East US, 730 hours a month. Not priced: data transfer, monitoring, gateway |
| 2026-11-19 | UC1 model comparison | Run the same 20 questions on a second Gemini model | `model-comparison.md`: 18 of 20 against 17 of 20, with cost and speed | Prices read from Google's pricing page. Results vary between runs, so the gap is reported as noise, not a ranking |
| 2026-11-19 | UC1 status report and deck | Write the status report and a 13-slide deck | `status-report.md` and `uc1-deck.pptx` | Deck opens and has 13 slides. I could not render it here (no LibreOffice), so look at every slide before presenting |
| 2026-11-20 | UC1 vector search | Make vector search the default (done by a second Claude session at my request) and restore it after the files on disk were rolled back | `VectorIndex` and `FallbackIndex` in `search.py`, a `SEARCH_BACKEND` setting, `test_vector_index.py` | I chose vector search over hybrid. I checked the committed work, restored it from git, and ran the tests (62 passing). Search takes a median 16.4 ms over 1,830 vectors, measured |
| 2026-11-20 | UC1 embeddings, remainder | Embed the remaining chunks after the quota reset | 1,830 of 2,047 chunks (89%) now have vectors. The 217 left are old ESRS Set 1 text | Checked the count per document in the database. Found the job crashed on a dropped connection and added retries with tests |
| 2026-11-20 | UC1 environment fix | Windows Application Control started blocking SQLAlchemy's compiled files, so the backend could not restart | Renamed the blocked `.pyd` files to `.pyd.disabled` inside `backend/.venv` so SQLAlchemy uses its plain-Python versions | Reversible by removing `.disabled`. A rebuilt `.venv` will hit the same block. Tests pass with it |
| 2026-11-20 | UC1 full evaluation | Run all 40 questions on vector search | 36 of 40 correct (90%). All 7 date and 11 refusal questions correct | The quota ran out part way, so the run mixed vector and keyword search. I did not report it as a clean vector result, and the script now records the search mode per question |
| 2026-11-20 | UC1 bug fixes from the evaluation | Fix what the evaluation exposed | Prompt rule against paragraph numbers in brackets (they caused false refusals), retry on dropped connections for the chat model, a hashed on-disk cache for question vectors | Confirmed the prompt fix on a real call. 14 new tests. The cache stores a hash, never the question text |
| 2026-11-20 | UC1 design doc rewrite | Rewrite section 6 as architecture decision records: one line on why each choice beats the rest and one on what this project changes | `solution-design.md` sections 6.0 to 6.8, plus corrections where the text no longer matched the build | I checked each claim against the code. It had said endpoints were async, which was wrong, so I fixed it |
| 2026-11-20 | UC1 presenter notes and deck refresh | Write a talk track, demo script and options explainer, and update the deck with real numbers | `docs/presentation-notes.md` and the refreshed `uc1-deck.pptx` | Numbers come from the evaluation, database and tests. I could not render the deck here, so check every slide by eye before presenting |
| 2026-11-20 | UC1 option coverage | Check which database and vector options the docs cover, and add the missing ones | MongoDB Atlas, Cosmos DB for MongoDB, Pinecone, Weaviate and Elasticsearch added to the vector store options. A relational versus MongoDB decision added to the database design. A table of when each option would win. The database design was also corrected: it showed no `chunk_embeddings` table | I checked the docs by search before answering. I asked what "use" meant and chose to cover them in the design, not build adapters (they need accounts, and Weaviate's client is likely blocked here). Feature claims about Atlas and Cosmos DB are marked verify |
| 2026-11-20 | UC1 Pinecone adapter | Add Pinecone as an optional vector store behind the search interface | `pinecone_index.py`, `sync_pinecone.py`, settings, `pinecone-setup.md` and 14 new tests (74 total passing) | I chose to build only Pinecone, because Cosmos DB needs Azure and Weaviate's client is likely blocked here. Request formats were checked against Pinecone's official API docs. Tested against a fake service only: it has not run against a live index, because I cannot create the account or key. I will do that step myself |

## What I built or decided myself

- I understood the requirements for the Day 1 app.
- I chose Gemini over a paid account.
- I created my own Gemini API key.
- I ran and tested the app together with Claude Code.
- I opened the pull request and merged it.
- I reviewed the architecture document.
- I chose the direction for the UC1 scenario: an advanced case built on a current market problem, in the style of a professional services firm.
- I decided to build UC1 locally with Gemini because Azure access and the issued model keys were not available.
- I decided to stop embedding at the 950 chunks done, because the free-tier daily limit was reached.
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
