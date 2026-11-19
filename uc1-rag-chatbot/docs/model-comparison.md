# Model comparison

The program expects at least two models compared on accuracy, cost and speed. Both runs use the same 20 questions, the same search and the same prompt. Only the chat model changes.

| | gemini-3.1-flash-lite | gemini-3.5-flash-lite |
|---|---|---|
| Correct answers | 18 of 20 (90%) | 17 of 20 (85%) |
| Answerable questions | 7 of 8 | 6 of 8 |
| Date-sensitive questions | 3 of 4 | 3 of 4 |
| Correct refusals | 8 of 8 | 8 of 8 |
| Median time per question | 3.6s | 2.4s |
| Tokens in / out (20 questions) | 28,604 / 1,411 | 28,668 / 847 |
| Cost per question | $0.00046 | $0.00054 |
| Price per 1M tokens (in / out) | $0.25 / $1.50 | $0.30 / $2.50 |

Prices are from the Gemini pricing page, checked 2026-11-19. Full per-question results are in [evaluation-results.md](evaluation-results.md) and [evaluation-results-gemini-3.5-flash-lite.md](evaluation-results-gemini-3.5-flash-lite.md).

## Reading the numbers

1. Both models refused every question they should have refused (8 of 8). Refusal is mostly decided by the search score, not the model.
2. The first model is slightly more accurate and about 15 percent cheaper per question. The second is about 1.2 seconds faster per question because it writes shorter answers (847 against 1,411 output tokens).
3. The second model refused three questions it should have answered (Article 29b, the revised ESRS start year, and the revised ESRS content). It is more cautious.
4. The difference is 1 question out of 20. That is within run-to-run noise: the same model scored 19 of 20 and then 18 of 20 on two runs of the same set. Do not treat this as proof that one model is better.

## Recommendation

Keep `gemini-3.1-flash-lite` as the default. It is cheaper, at least as accurate here, and already used in the cost estimate. Rerun the comparison with the 40-question set and full hybrid search before choosing for production.

## Limits

1. Both models are from the same provider. A Claude or Azure OpenAI model could not be compared because no keys were available.
2. Search ran mostly in keyword fallback during both runs (embedding quota used up), which affects both models equally.
3. Twenty questions is too small for a firm ranking.
