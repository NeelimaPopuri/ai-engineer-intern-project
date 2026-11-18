# Cost estimate

What the Day 1 app costs to run for a pilot of 100 users and production of 5,000 users. All figures are monthly, in US dollars.

## Verified pricing

Source: Google AI Studio pricing page (`aistudio.google.com/docs/pricing`), checked 2026-11-18. The page shows no last-updated date, so re-check before quoting these figures in a client document.

| Item | Price |
|---|---|
| `gemini-3.1-flash-lite` input, text | $0.25 per 1M tokens |
| `gemini-3.1-flash-lite` output, text | $1.50 per 1M tokens (includes thinking tokens) |
| Free tier | Listed as free of charge; rate limits not stated on the page |

## Usage assumptions

These are my assumptions, not measurements. Replace them with real numbers once the app has users.

| Assumption | Value | Basis |
|---|---|---|
| Requests per user per working day | 20 | Light interactive use |
| Working days per month | 22 | Standard month |
| Input tokens per request | 100 | Short prompt; the API caps prompts at 2,000 characters |
| Output tokens per request | 300 | The backend caps output at 500 tokens; 300 is a typical reply with thinking tokens |

## Token cost

Cost per request: (100 / 1,000,000 x $0.25) + (300 / 1,000,000 x $1.50) = $0.000025 + $0.00045 = **$0.000475**

| | Pilot (100 users) | Production (5,000 users) |
|---|---|---|
| Requests per month | 100 x 20 x 22 = 44,000 | 5,000 x 20 x 22 = 2,200,000 |
| Input tokens | 44,000 x 100 = 4.4M | 2,200,000 x 100 = 220M |
| Output tokens | 44,000 x 300 = 13.2M | 2,200,000 x 300 = 660M |
| Input cost | 4.4 x $0.25 = $1.10 | 220 x $0.25 = $55.00 |
| Output cost | 13.2 x $1.50 = $19.80 | 660 x $1.50 = $990.00 |
| **Token total** | **$20.90** | **$1,045.00** |

Output tokens are about 95 percent of the bill. Capping `maxOutputTokens` or asking for shorter replies is the biggest cost lever.

## Infrastructure and storage

These figures are planning estimates and are not verified against Azure pricing. Check them in the Azure pricing calculator before they appear in a client document.

| Item | Pilot | Production | Notes |
|---|---|---|---|
| Backend hosting | about $15 | about $150 | Pilot: one small container instance. Production: three instances behind a load balancer, since the API is stateless. |
| Frontend hosting | $0 | about $10 | Static files only |
| Database | $0 | $0 | Day 1 has no database |
| Storage | $0 | $0 | Day 1 stores no files or history |

## Monthly total

| | Pilot (100 users) | Production (5,000 users) |
|---|---|---|
| Tokens | $20.90 | $1,045.00 |
| Infrastructure | about $15 | about $160 |
| **Total** | **about $36** | **about $1,205** |
| Per user | about $0.36 | about $0.24 |

## What would change the numbers

- **Free tier:** the pilot's token cost could be $0 on the free tier, but its rate limits and data-use terms need checking first. It is not suitable for client data.
- **Model choice:** a larger Gemini model costs more per token. Compare prices before switching.
- **Usage:** doubling requests per user doubles the token cost. The token bill grows with usage, while hosting stays nearly flat.
- **Caching:** the Day 1 app sends unrelated prompts, so caching would save little. It matters in the RAG chatbot, where questions repeat.
