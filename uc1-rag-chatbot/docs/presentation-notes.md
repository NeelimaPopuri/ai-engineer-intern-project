# Presentation notes: Regulatory change navigator

For the friends demo (Thursday) and the mentor presentation (Friday). Read this once, then use the demo script.

## The 30-second version

EU sustainability reporting rules changed three times in 14 months. Advisers need to know which version applied on which date, with a source they can check. This chatbot answers from 10 public documents, shows citations, picks the version in force on the date you choose, and says "not enough evidence" instead of guessing.

## Talk track (about 8 minutes)

| Slide | Say | Time |
|---|---|---|
| 1 Title | One sentence: what it does and for whom | 20s |
| 2 Rules keep changing | The CSRD has 3 versions. An answer right today can be wrong for last year's report | 45s |
| 3 Users and targets | Advisory managers. Targets are my proposals until the brief is confirmed | 45s |
| 4 Architecture | One question, six steps. Search and model sit behind interfaces so Azure can replace them | 90s |
| 5 Source library | 10 documents, 2,047 chunks, 89% with vectors and all text in force today covered | 45s |
| 6 Date-aware | Three versions, each closes the last. Same question, different answers by date | 60s |
| 7 Safeguards | It refuses before it guesses: weak evidence, no citation, invented source | 60s |
| 8 Demo | Run it live (script below) | 2 min |
| 9 Evaluation | 36 of 40 correct (90%). All 7 date questions and all 11 refusals right. Say the run mixed two search modes and a clean rerun is planned | 60s |
| 10 Model comparison | Two models, same questions. Gap is within noise | 45s |
| 11 Cost | About $126 a month for 100 users. Prices are official list prices | 45s |
| 12 What was missing | Be direct: no Azure access, so I built on Gemini and a local index | 60s |
| 13 Next steps | Ask for the brief and Azure access | 30s |

## Live demo script

Open http://localhost:5176 (or the address `npm run dev` prints). Hard refresh first.

1. Set **Answer as of** to **1 June 2026**. Ask: *What net turnover and employee numbers can Member States use to exempt undertakings from the sustainability reporting measures?* Expect EUR 450,000,000 and 1,000 employees, with sources. Click a source to show the exact passage and its version dates.
2. Change the date to **1 June 2024** and ask the same question. Expect a refusal. Say: the exemption did not exist yet, so nothing supports an answer. This is the main point of the project.
3. Ask *What is the capital of France?* Expect a refusal. Say: it does not use the model's general knowledge.
4. If someone asks "does it make things up?", point to the refusal and the source panel.

Warm up with one question 5 minutes before. If an answer is slow, the free Gemini tier is busy: wait and retry.

## The options, and how each one works

This is the "what are the options" part of the project. Know one sentence for each.

### Finding the right passages (retrieval)

| Option | How it works | Good at | Weak at | What I used |
|---|---|---|---|---|
| Keyword search (BM25) | Scores passages by how often the question's words appear, weighting rare words more | Exact terms like "Article 29b" | Different wording for the same idea | Fallback only |
| Vector search | An embedding model turns text into a list of 768 numbers that capture meaning. Questions and passages that mean the same end up close together, measured by cosine similarity | Paraphrased questions | Exact identifiers and numbers | **Default** |
| Hybrid | Run both, merge the two rankings | Both kinds of question | More moving parts | Available by a setting (`SEARCH_BACKEND=hybrid`) |

### Where the vectors live

| Option | What it is | Why or why not |
|---|---|---|
| Azure AI Search | Managed search service, the required stack | The target. No access during the pilot |
| In-memory vector index (numpy) | The vectors sit in one matrix; a question is compared with all allowed rows in about 16 ms | **Used.** No native components, so it runs under this machine's Windows security policy |
| ChromaDB, Qdrant local, FAISS | Real vector databases and libraries | All three were tried and failed to load here: Application Control blocks their native files |
| pgvector (PostgreSQL) | Vector search inside the main database | Outside the required stack; a good option if Azure is not used |

### Cutting documents into pieces (chunking)

Structure-aware chunks split at Article and Section headings, with a size limit (350 tokens) and a small overlap (40 tokens). Fixed-size chunks cut sentences in half. Whole-document embeddings are too coarse to cite.

### Handling changing rules

Each document has versions with effective dates. Search first keeps only the version in force on the chosen date, then ranks. Keeping only the latest version cannot answer past dates.

### The chat model

Gemini 3.1 Flash-Lite for answers and gemini-embedding-001 for vectors. Compared against Gemini 3.5 Flash-Lite. A Claude or Azure OpenAI model could not be compared because no keys were available.

## Questions your mentor may ask, with honest answers

**Why not Azure AI Search, as the brief says?** I had no access to the shared resource group and no issued keys. I built behind interfaces, so search and the model are each one class to swap. None of the Azure claims in the design were tested, and the doc marks them "verify".

**Why a numpy matrix and not a vector database?** I tried Chroma, Qdrant and FAISS. Windows Application Control blocked all three on this machine. The matrix has the same behavior (filter, then cosine similarity) and is easy to explain. At 2,047 chunks it takes about 16 ms. It would not scale to millions of chunks, which is where Azure AI Search or pgvector comes in.

**How do you know it is accurate?** I wrote 40 test questions from the source texts: answerable, date-sensitive and should-refuse. First full run: 36 of 40 correct, with every date and refusal question right. The misses were one network drop, one question where a news page outranked the legal text, and two that the model refused. One of those two was a real bug in how I handled paragraph numbers in citations, which I found and fixed. The set is small, results move a little between runs, and I wrote the questions myself, so treat the score as indicative.

**What happens when the Gemini quota runs out?** Questions that cannot be embedded fall back to keyword search, so the app keeps working with weaker retrieval. The free tier allows 1,000 embedding requests a day.

**Can it leak client data?** The library is public documents only. Gemini's free tier is marked as used to improve Google products, so no client material may go through it. Client use needs a paid tier or Azure.

**What did you decide yourself, and what did AI do?** Everything AI did is in `ai-usage-log.md`, with how each result was checked. My decisions: choosing Gemini over a paid account, the scenario and success targets, keeping the current embedded set and stopping at the quota, and which questions count as correct.

**What would you do with another week?** Get Azure access and swap in Azure AI Search and Azure OpenAI. Extend the evaluation beyond 40 questions with a second reviewer. Test with real adviser questions. Add a way to upload new document versions.

## Numbers to remember

| Fact | Number |
|---|---|
| Documents, versions, chunks | 10, 10, 2,047 |
| Backend tests | 62 |
| Evaluation questions | 40 |
| Cost per question (model tokens) | about $0.001 |
| Monthly cost, 100 and 5,000 users | about $126 and $1,752 |
| Search speed over the vectors | about 16 ms |
