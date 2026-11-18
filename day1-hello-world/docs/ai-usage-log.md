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

## What I built or decided myself

- I understood the requirements for the Day 1 app.
- I chose Gemini over a paid account.
- I created my own Gemini API key.
- I ran and tested the app together with Claude Code.
- I opened the pull request and merged it.
- I reviewed the architecture document.

## What I can explain

- **API key check:** every request to `/api/v1/chat` must send an `X-API-Key` header that matches `APP_API_KEY` in `.env`. If it does not, the API returns 401, so only my own frontend can call it.
- **Request validation:** a Pydantic model checks that the prompt is 1 to 2,000 characters. An empty or oversized prompt returns 422 before any model call, which saves cost.
- **Gemini call:** the backend sends the prompt to Gemini's REST API with `httpx`, using my Gemini key from `.env`, and returns the reply text and model name.
- **Retry logic:** if Gemini returns 429 (rate limit) or 503 (overloaded), the backend waits 1.5 seconds, then 3 seconds, and tries up to 3 times. Brief overloads then do not show up as errors in the UI.
- **Error handling:** if Gemini still fails, the API returns 502 Bad Gateway, which means the model provider failed, not my server. A rejected key (400, 401 or 403) gets a clearer message that points to `GEMINI_API_KEY`.
- **Dev proxy:** the browser calls `/api/v1/chat` on the Vite dev server, which forwards it to FastAPI and adds the app key. The key never ships in the browser code, which is why it is not a `VITE_` variable.
- **Config:** `pydantic-settings` reads `.env` into typed settings and stops the app at startup if a key is missing, so mistakes show up early.
- **Secrets:** `.env` is git-ignored and only `.env.example` is committed, so no real key is in the repository.
- **Tests:** six automated tests use fake Gemini responses to check health, auth, validation, a successful reply, a provider failure and a bad key. They never call the real API.
- **Cost:** a request costs about $0.000475, mostly from output tokens, so Day 1 costs about $36 per month for 100 users. The math is in `cost-estimate.md`.
