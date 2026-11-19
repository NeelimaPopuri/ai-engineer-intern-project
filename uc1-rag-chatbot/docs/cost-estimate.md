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

Standard pay-as-you-go list prices for the Azure target, East US, from the Azure Retail Prices API (`prices.azure.com/api/retail/prices`), retrieved 2026-11-19. Monthly figure = hourly price x 730 hours. No reservations, discounts or taxes. Prices change, so confirm in the [Azure pricing calculator](https://azure.microsoft.com/pricing/calculator/) before quoting them to a client.

| Item | SKU | Hourly price | Pilot per month | Production per month |
|---|---|---|---|---|
| Search service | Pilot: AI Search Basic. Production: Standard S1 | $0.101 and $0.336 | $73.73 | $245.28 |
| Backend hosting | App Service Linux. Pilot: B1, one instance. Production: S1, three instances | $0.017 and $0.095 | $12.41 | $208.05 (3 x $69.35) |
| PostgreSQL | Flexible Server. Pilot: Burstable B1MS, 32 GB. Production: General Purpose D2s v3 (2 vCores at $0.0855), 128 GB | $0.017 and $0.171 | $16.09 ($12.41 + $3.68 storage) | $139.55 ($124.83 + $14.72 storage) |
| Database storage price | Flexible Server storage | $0.115 per GB per month | included above | included above |
| Document and chat storage | Blob Storage, Hot LRS | $0.0208 per GB per month | $0.02 (1 GB) | $0.10 (5 GB) |
| Frontend hosting | Served by the same App Service in the pilot. Production: static files in Blob Storage | | $0 | under $1 |
| **Infrastructure total** | | | **$102.25** | **$593** |

What is not included, and why:
1. The model is Gemini, so no Azure OpenAI charge appears. Moving to Azure OpenAI changes the token lines, not these.
2. Azure AI Search semantic ranker is not used. It would add a charge per 1,000 queries.
3. Outbound data transfer, monitoring, backups beyond the free allowance and a load balancer or gateway are not priced. Add them before quoting a client.
4. A search service price for Basic and S1 assumes one replica and one partition. The library is 2.1 MB, so the pilot is far below the limits.

## Monthly total

| | Pilot (100 users) | Production (5,000 users) |
|---|---|---|
| Tokens | $23.27 | $1,159.22 |
| Infrastructure (Azure target) | $102.25 | $593 |
| **Total** | **about $126** | **about $1,752** |
| Per user | about $1.26 | about $0.35 |
| Pilot as built (Gemini and local search, one B1 App Service) | about $36 | not applicable |

Infrastructure is 81 percent of the pilot cost and 34 percent of production. At pilot size the search service alone ($73.73) costs three times the model tokens, which is a reason to start on Basic and to question whether a pilot needs a managed search service at all.

## Cost levers

1. Retrieve fewer sources per question, or trim their length.
2. Use a smaller model for easy questions and a larger one only when retrieval is uncertain.
3. Cache answers to repeated questions on the same date.
4. Cap output length (already 150 words in the prompt).
5. Embed only new or changed document versions. The ingestion job already skips unchanged text.
