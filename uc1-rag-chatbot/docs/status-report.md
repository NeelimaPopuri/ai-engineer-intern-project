# Status report: Regulatory change navigator (UC1)

Date: 2026-11-19. Prepared by Neelima Popuri.

## Summary

The chatbot works end to end on a local stack. It answers EU sustainability reporting questions with citations, picks the document version that applied on the date the user chooses, and refuses when the evidence is weak. It runs on Gemini and a local search index because Azure access and issued keys were not available.

## Numbers

| Measure | Result |
|---|---|
| Source documents loaded | 10 documents, 7 titles, 10 versions, 2,047 chunks |
| Chunks with embeddings | 1,830 of 2,047 (89%); the rest are old ESRS Set 1 text |
| Backend tests | 62 passing, none call a real model |
| Evaluation | 36 of 40 correct (90%) on the first full run; all 7 date questions and all 11 refusals correct. That run mixed vector and keyword search, so a clean vector rerun is pending |
| Correct refusals | 8 of 8 |
| Median time per question | about 3.5s end to end; the search itself takes 16 ms |
| Cost per question | about $0.0005 (model tokens only) |
| Estimated monthly cost | about $126 for 100 users, about $1,752 for 5,000 users |

## Done

1. Problem statement, database design (8 tables), solution design with rejected alternatives, cost estimate.
2. Public source library with recorded URLs, retrieval dates and verified effective dates.
3. Structure-aware chunking and versioned ingestion. A new version closes the old one.
4. Hybrid search with date and jurisdiction filters, falling back to keywords when needed.
5. Cited chat API with refusal, citation checks, source-authority flag and proper error codes.
6. React chat screen with date and jurisdiction filters and expandable citations.
7. Evaluation set, scoring script and a two-model comparison.
8. AI usage log with every AI-assisted step and how it was checked.

## Risks and gaps

| Item | Impact | Plan |
|---|---|---|
| No Azure access or issued keys | The required stack is not demonstrated; Azure claims are unverified | Request access from the mentor. Search and model sit behind interfaces, so the swap touches two files |
| Free-tier embedding limit (1,000 a day) | The quota ran out during evaluation, so part of the run used keyword search. 217 chunks have no vector | Rerun the evaluation after the quota resets. Question vectors are now cached, so repeats cost nothing |
| Small evaluation set (20, target 40) | Scores are indicative | Extend to 40 questions |
| Results vary between runs | 18 versus 19 of 20 on the earlier set | Report a range, not a single figure |
| Free tier may use content to improve Google products | Client data must not use it | Paid tier or Azure before any client material |
| Azure prices are list prices from 2026-11-19 | Actual bills depend on region, discounts and extras not priced | Confirm in the Azure pricing calculator |
| No UC1 brief from the mentor | Scenario and targets are proposals | Confirm in the next mentor session |

## Next

1. Confirm the scenario and success targets with the mentor.
2. Get Azure access and keys, then verify the claims marked "verify" in the design.
3. Extend the evaluation to 40 questions and rerun with full hybrid search.
4. Demo to friends, then present to the mentor.
