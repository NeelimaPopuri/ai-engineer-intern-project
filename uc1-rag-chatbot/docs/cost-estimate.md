# Cost estimate: Regulatory change navigator

Monthly cost in US dollars for a pilot of 100 users and production of 5,000 users. Follows the format of the Day 1 [cost estimate](../../day1-hello-world/docs/cost-estimate.md).

## Verified pricing

Source: Gemini API pricing page (`ai.google.dev/gemini-api/docs/pricing`), checked 2026-11-19. The page shows no last-updated date, so re-check before quoting these figures in a client document.

| Item | Paid tier price |
|---|---|
| `gemini-3.1-flash-lite` input, text | $0.25 per 1M tokens |
| `gemini-3.1-flash-lite` output, text (includes thinking tokens) | $1.50 per 1M tokens |
| `gemini-embedding-001` input | $0.15 per 1M tokens |

Two things on the same page matter for the design:
1. The free tier is free of charge but is marked "used to improve our products". Client documents must never go through the free tier.
2. The free tier limits embedding to 1,000 requests a day (seen in the API error on 2026-11-19). This stopped the pilot's embedding run at 950 of 2,047 chunks.

## Usage assumptions

My assumptions, not measurements. Replace them with real numbers once there are users.

| Assumption | Value | Basis |
|---|---|---|
| Questions per user per working day | 10 | Research-style use by advisory staff, lighter than chat |
| Working days per month | 22 | Standard month |
| Chat input tokens per question | 2,400 | 6 sources of about 350 tokens, plus instructions and the question |
| Chat output tokens per question | 300 | 150-word limit, plus thinking tokens |
| Query embedding tokens | 25 | One short question |
| Library size | 595,299 tokens | Sum of chunk token estimates in the database (2,047 chunks) |

## Token cost

Cost per question: (2,400 / 1,000,000 x $0.25) + (300 / 1,000,000 x $1.50) = $0.0006 + $0.00045 = **$0.00105**

| | Pilot (100 users) | Production (5,000 users) |
|---|---|---|
| Questions per month | 100 x 10 x 22 = 22,000 | 5,000 x 10 x 22 = 1,100,000 |
| Chat model cost | 22,000 x $0.00105 = $23.10 | 1,100,000 x $0.00105 = $1,155.00 |
| Query embeddings | 22,000 x 25 = 0.55M tokens x $0.15 = $0.08 | 27.5M tokens x $0.15 = $4.13 |
| One-time library embedding | 0.595M tokens x $0.15 = $0.09 | $0.09 |
| **Token total** | **$23.27** | **$1,159.22** |

Chat input is about 57 percent of the model cost. Fewer or shorter retrieved sources (the `TOP_K` setting) is the biggest lever.

## Infrastructure and storage

These are planning estimates for the Azure target. They are not verified against Azure pricing and must be checked in the Azure pricing calculator before they appear in a client document.

| Item | Pilot | Production | Notes |
|---|---|---|---|
| Backend hosting | about $15 | about $150 | One small container, then three behind a load balancer |
| Search service (Azure AI Search) | about $75 | about $250 | Pilot as built uses the local index and pays $0 here |
| PostgreSQL | about $15 | about $100 | Pilot as built uses SQLite and pays $0 |
| Frontend hosting | $0 | about $10 | Static files |
| Storage | under $1 | under $5 | Library text is 2.1 MB, vectors about 6 MB, messages grow with use |

## Monthly total

| | Pilot (100 users) | Production (5,000 users) |
|---|---|---|
| Tokens | $23.27 | $1,159.22 |
| Infrastructure (Azure target) | about $105 | about $510 |
| **Total** | **about $128** | **about $1,669** |
| Per user | about $1.28 | about $0.33 |
| Pilot as built (local stack) | about $38 | not applicable |

## Cost levers

1. Retrieve fewer sources per question, or trim their length.
2. Use a smaller model for easy questions and a larger one only when retrieval is uncertain.
3. Cache answers to repeated questions on the same date.
4. Cap output length (already 150 words in the prompt).
5. Embed only new or changed document versions. The ingestion job already skips unchanged text.
