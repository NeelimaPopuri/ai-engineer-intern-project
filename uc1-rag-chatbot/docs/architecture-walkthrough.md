# Architecture walkthrough: how to explain every choice

A speaking guide for the mentor presentation. It follows the path of the data, from source document to cited answer. Every step answers the same four questions:

1. What are the types of solution that exist?
2. Which did we choose?
3. Why, for this project in particular?
4. Why not the others, and when would we change our mind?

**The sentence to reuse at every step:** "We needed X. The options were A, B and C. We chose B because of Y, which matters here because of Z. We gave up W, and we would revisit it if V."

The decision records with full option tables are in the [solution design](solution-design.md) section 6. This document is the spoken version.

## The system in one paragraph

Advisers ask questions about EU sustainability reporting rules. The rules changed three times in 14 months, so the answer depends on the date. We keep 10 public source documents (7 titles, 10 versions) cut into 2,047 passages. For each question we keep only the passages from the version in force on the chosen date, find the ones closest in meaning, give six of them to a language model, and accept the answer only if it cites those passages correctly. If the evidence is weak, it says so instead of guessing.

## The pipeline at a glance, with the exact technology used

### A. Preparing the library (runs when documents change)

| # | Step | What happens | Technology exactly used | Why |
|---|---|---|---|---|
| 1 | Collect | 10 public EU documents are fetched from official publishers, with URL, date and effective date recorded | Python script with `httpx` (HTTP client). Legal texts through the Publications Office CELEX resolver (`publications.europa.eu`). Record kept in a CSV file | A legal assistant is only as trustworthy as its sources |
| 2 | Clean | HTML is turned into plain text, keeping headings | Python standard library `html.parser` with a small custom class and regular expressions | Sources already have structure, so a small parser is enough |
| 3 | Version | Each document is stored as dated versions. A new version closes the old one | SQLAlchemy 2 (ORM) and Alembic (migrations) on SQLite in the pilot, PostgreSQL as the target. SHA-256 content hash so a repeat load changes nothing | The rules changed 3 times in 14 months, so the answer depends on the date |
| 4 | Chunk | Text is split at Article and Section headings, about 350 tokens each, with a 40-token overlap | Custom Python (`chunking.py`) with regular expressions for headings. Token count estimated at about 4 characters per token | A citation then points to a real article. This gives 2,047 chunks |
| 5 | Embed | Each chunk becomes 768 numbers | Google Gemini API, model `gemini-embedding-001`, task type RETRIEVAL_DOCUMENT, called over REST with `httpx`. Vectors stored in a `chunk_embeddings` table (JSON column) | Matches questions by meaning, so "who must report" finds "undertakings" |

### B. Answering one question (every time)

| # | Step | What happens | Technology exactly used | Why |
|---|---|---|---|---|
| 1 | Filter | Keep only chunks from the version in force on the chosen date, and for the chosen country | SQL query through SQLAlchemy (date range on `effective_from` and `effective_to`, plus jurisdiction) | The date is part of correctness. An old rule must never outrank the current one |
| 2 | Embed the question | The question becomes a vector, cached so repeats cost nothing | Same Gemini embedding model, task type RETRIEVAL_QUERY. Cache is a local JSON file keyed by a SHA-256 hash, so no question text is stored | Same space as the chunks, and it saves quota |
| 3 | Vector search | Rank the remaining chunks by cosine similarity and take the top 6 | `numpy`: one in-memory matrix of normalised vectors (our `VectorIndex` class), about 16 ms. Keyword fallback is our own BM25 implementation | Fast and exact at this size, and nothing blocked by the machine's security policy |
| 4 | Evidence check | If the best match scores under 0.6, answer "not enough evidence" without calling the model | Plain Python threshold in `answer.py` | Cheaper, and it never guesses |
| 5 | Generate | The model gets the 6 numbered passages and writes a short answer with citations | Google Gemini API, model `gemini-3.1-flash-lite`, `generateContent` over REST with `httpx`, temperature 0.1, up to 1,024 output tokens | The model only rewrites supplied text, so a small model is enough |
| 6 | Citation check, in code | Every citation must point to a passage we supplied. Otherwise it is replaced by a refusal | Python with a regular expression for `[n]` and `[n, m]` markers, then renumbering | A prompt can be ignored by the model. Code cannot |
| 7 | Flag and save | Legal text mixed with news pages is flagged. The answer, citations and token counts are saved | SQLAlchemy writing to the `messages` and `citations` tables | Advisers need to see which source outranks which |

### C. Around the pipeline

| Layer | Technology exactly used |
|---|---|
| API | FastAPI with Pydantic models, served by `uvicorn`, API-key header on every route |
| Screen | React 18, Vite, Tailwind CSS 4, Lucide icons. The Vite dev proxy adds the API key so the browser never holds it |
| Tests | `pytest`, 74 tests, none call a real model |
| Evaluation | A script that runs 40 labelled questions against the real search and model, and scores each one |
| Optional | Pinecone adapter (REST with `httpx`), tested against a fake service only |

If a question cannot be embedded (quota or outage), step B3 falls back to keyword search. The app keeps answering with weaker retrieval.

## Step 0. Why retrieval at all?

| Type | What it is | Why it fits or fails here |
|---|---|---|
| **Retrieval-augmented generation (RAG)** (chosen) | Find relevant passages first, then have the model answer from them | Answers can cite a source, and updating the rules means adding a document version, not retraining |
| Fine-tuning a model on the documents | Teach the model the text by training | Knowledge is frozen at training time, cannot cite a passage, and cannot answer "as of last year" |
| Long context: paste every document into every prompt | No search step at all | The library is about 595,000 tokens. At $0.25 per million input tokens that is about $0.15 per question, against about $0.001 now, roughly 140 times more. It is also slower and harder to cite |
| Plain keyword search with no model | Return matching passages | Cheap and exact, but advisers get a pile of passages and not an answer |

**Why this matters here:** the rules change, and users need a source they can check. Both point to RAG.

## Step 1. Getting the source documents

| Type | Strength | Weakness |
|---|---|---|
| **Official publisher services** (chosen) | The authoritative text, with stable identifiers and dates | Needs care per publisher |
| Scraping the public website | Simple | The EUR-Lex website answers automated requests with a bot check. We did not work around it |
| Commercial legal databases | Clean, consolidated, supported | Licence cost and a vendor dependency |
| Manual download | Reliable once | Does not repeat, and nobody can show where a file came from |

**What we did:** a script fetches legal texts through the Publications Office service, which is the official route for machines, and web pages directly. It records the URL, retrieval date and effective date of every document in `sources.csv`. Effective dates were checked against the text itself, and two of my first guesses were wrong and corrected.

**Why this matters here:** a legal assistant is only as trustworthy as its sources, and an auditor will ask where each passage came from.

## Step 2. Turning documents into clean text

| Type | Best for |
|---|---|
| **A small parser for the format we have** (chosen: HTML and XHTML) | Sources that are already structured, as these are |
| PDF text extractors | Digital PDFs |
| OCR (optical character recognition) | Scanned documents |
| Managed document services such as Azure AI Document Intelligence | Mixed, messy, layout-heavy files, with tables and forms |
| General document-loading libraries | Quick starts across many formats |

**Why we chose the small parser:** every source arrives as web markup, which already carries headings. A managed service would add cost and a dependency to solve a problem we do not have.

**When we would change:** the first scanned or table-heavy PDF. Then a managed service earns its place.

## Step 3. Chunking: cutting text into passages

| Type | How it works | Weakness |
|---|---|---|
| **Structure-aware** (chosen) | Split at the document's own headings (Article, Section, Annex), cap at about 350 tokens, add a 40-token overlap when a long section must be cut | Needs heading rules per document type |
| Fixed-size | Every N characters | Cuts articles mid-sentence, so citations are unreadable |
| Recursive splitting | Try paragraph, then sentence, then word until it fits | Better than fixed-size, but still ignores legal structure |
| Semantic chunking | Cut where the meaning shifts, found with embeddings | Costs embedding calls at ingestion and is harder to explain |
| Parent and child chunks | Search small pieces, return the larger section | Good for long answers, but adds a second structure to maintain |
| Whole document | One vector per document | Far too coarse to cite |

**Why this matters here:** in legal work the citation is the deliverable. When the chunk boundary is the article boundary, every citation points to something a lawyer recognises.

**Trade-off:** heading detection is rule-based. It fits EU legal text well and web pages less well. Chunk size and overlap were set from common practice and are not yet tuned on the evaluation set.

## Step 4. Storing documents, versions and dates

| Type | Fit for this data |
|---|---|
| **Relational database with a version table** (chosen: PostgreSQL target, SQLite pilot) | The data is relational and the key rules are relational |
| Document database (MongoDB, Cosmos DB for MongoDB) | Good for schema-free content, but would leave integrity rules to application code |
| Graph database | Strong when relationships are the question. Ours are a simple chain |
| Files in object storage | Cheap, but no queries |

**The central design idea:** each document has versions, each version has an effective start and end date, and each version has passages. A new version closes the previous one on its start date. Search keeps only versions in force on the chosen date.

**Why not keep only the latest version:** it cannot answer a question about last year's report, which is exactly what advisers ask.

**Why relational:** two rules matter most. "Find the version in force on this date" is a date-range lookup. "Every citation must point to a real passage" is a foreign key. A relational database enforces both. The brief also names PostgreSQL.

## Step 5. Embeddings: turning text into numbers

An embedding is a list of numbers that places a piece of text on a map of meaning. Texts that mean the same land close together, even when the words differ.

| Type | What it is | Strength | Weakness |
|---|---|---|---|
| Sparse (TF-IDF, BM25) | Counts words, weighted by rarity | Exact terms, no model needed | Cannot match "who must report" with "undertakings" |
| **Dense, from a hosted API** (chosen: `gemini-embedding-001`) | A neural model returns a vector of a fixed size | Handles paraphrase, no hosting | Per-token cost or a free-tier quota, and text leaves your network |
| Dense, open-source model run locally (BGE, E5, sentence-transformers) | Same idea, on your own machine | No quota, text stays local | You host it, and a model download is needed |
| Learned sparse (SPLADE) | A model predicts weighted words | Keeps exact-term strength with some semantics | Less common tooling |
| Multi-vector or late interaction (ColBERT) | One vector per word, matched in detail | Often more accurate | Much more storage and complexity |
| Fine-tuned or domain-specific embeddings | Trained on legal or sustainability text | Best fit for specialist language | Needs training data and effort |

**What we chose and the size:** `gemini-embedding-001` at 768 dimensions. The model offers larger vectors, and asking for 768 keeps storage small: 2,047 passages at 768 numbers is about 6 MB. We have not measured whether larger vectors would improve accuracy on our questions.

**Why we chose it:** one provider and one key already cover the chat model, it is free to start, and the Azure alternative was not available to us.

**What went wrong, honestly:** the free tier allows 1,000 embedding requests a day. We hit it while embedding the library and again during evaluation. Search was built to fall back to keywords when a question cannot be embedded, and question vectors are cached so a repeated question costs nothing.

**When we would change:** a local open-source model removes the quota and keeps text on the machine. It is the obvious next step if the quota keeps hurting, and Azure OpenAI embeddings are the target once access exists. The embedding call sits behind one function, so it is a one-file change. Changing the model means re-embedding everything, because vectors from different models cannot be compared.

## Step 6. The search engine and vector store

| Type | Examples | Where it fits |
|---|---|---|
| **In-memory index** (chosen for the pilot) | A numpy matrix | Small, fixed libraries. Exact results, nothing to install |
| Embedded vector databases | ChromaDB, Qdrant local | Prototypes needing persistence and filters |
| Vector libraries | FAISS | Fast search inside your own code, no filtering or storage by default |
| Vector extension of an existing database | pgvector for PostgreSQL | One database for everything. Needs a PostgreSQL server |
| Managed search service | **Azure AI Search** (the target), Elasticsearch, OpenSearch | Production scale, hybrid search and filters in one service |
| Managed vector databases | Pinecone, Weaviate | Scale without running servers |
| Document databases with vector search | MongoDB Atlas, Azure Cosmos DB for MongoDB | When your data is already in them |

**Why the in-memory index:** ChromaDB, Qdrant and FAISS were all tried on this machine and none would load, because Windows Application Control blocks their native components. We did not bypass the block. A numpy matrix has no extra component to block. It also suits the size: 2,047 passages, so exact comparison takes about 16 ms and an approximate index would add complexity and no benefit.

**Why not the managed options now:** no Azure access, and nothing at this size justifies another system.

**What makes it replaceable:** search sits behind one interface. We also built an adapter for Pinecone, tested against a fake service, to show the swap is real. It has not run against a live index.

**When we would change:** Azure AI Search when access arrives (the stated target). pgvector as the cheapest fallback. Pinecone or a similar service if the library reaches millions of passages.

## Step 7. Retrieval strategy: how to pick the passages

| Type | How it works | Good at | Weak at |
|---|---|---|---|
| Keyword search (BM25) | Scores passages by how rare the question's words are inside them | Exact terms like "Article 29b" | Different wording for the same idea |
| **Vector search with metadata filters** (chosen) | Filter by date and country first, then rank by closeness in meaning | Plain-language questions, and guarantees the right version | Exact identifiers rank lower |
| Hybrid search | Run both and merge the rankings (we use reciprocal rank fusion) | Both kinds of question | Two scores to tune and explain |
| Reranking | A second model re-scores the top results | Precision | Extra cost and delay |
| Query rewriting (multi-query, HyDE) | Rewrite or expand the question before searching | Vague questions | Extra model calls, and the rewrite can drift |

**The key design decision is the order:** filter, then rank. The date is part of correctness, not relevance. A superseded paragraph must never outrank the text in force, and ranking by similarity alone cannot promise that.

**Why vector as the default:** advisers ask in plain language and the law uses its own terms. We kept hybrid available as a setting and keyword search as the fallback.

**What we have not done, and should say plainly:**
1. We have not run a measured comparison of vector against hybrid on the full question set.
2. We have no reranker. It is the first accuracy improvement we would test.
3. We do not rewrite queries.

## Step 8. The language model that writes the answer

| Type | Examples | Trade-off |
|---|---|---|
| **Small, fast hosted model** (chosen: Gemini 3.1 Flash-Lite) | Gemini Flash-Lite, small GPT and Claude tiers | Cheap and quick. Enough when the job is to rewrite supplied passages |
| Large frontier model | Larger Gemini, GPT and Claude tiers | Better at hard reasoning, many times the cost |
| Azure OpenAI | The target | Same cloud as search, data stays in Azure. Not available to us |
| Open-source model we host | Llama, Mistral families | Full control and no per-token cost, but hosting effort and weaker answers at small sizes |

**Why a small model is defensible here:** the model does not recall law. It rewrites six supplied passages into an answer with citations. That is a constrained task. Open-ended legal advice would be a different decision.

**Evidence:** we ran the first 20 questions on a second model, Gemini 3.5 Flash-Lite. It scored 17 against 18, which is within the run-to-run variation we saw. We chose the cheaper and at least as accurate one. Both are Gemini, because no other keys were available.

**Caveat:** the free tier is marked as used to improve the provider's products, so client material must never go through it.

## Step 9. Grounding and citations: making wrong answers hard

| Type | How it works | Weakness |
|---|---|---|
| Prompt instructions only | Tell the model to use only the sources | The model can ignore them |
| **Checks in code plus prompt rules** (chosen) | Code enforces the rules whatever the model does | Can refuse a question the model could have answered |
| A second model as judge | Another model checks the answer | More cost and delay, and its own failure modes |
| Fine-tune the model to behave | Train the behaviour in | Heavy, and still not enforceable |

**What our code enforces:**
1. If the best match is below the evidence threshold (0.6 similarity), it refuses without calling the model.
2. Every citation number must point to a source the model was given. An answer with none, or with an invented one, is replaced by a refusal.
3. Citation markers are renumbered so they match the saved citations.
4. An answer that cites both legal text and a news or guidance page is flagged, and the note says the legal text prevails.

**Why this matters here:** advisers' output goes to clients. A confident wrong answer costs more than "I could not find support for this", so the system is built to prefer refusal.

**A real example of why code beats prompts:** a good answer was refused because the model wrote a paragraph number in square brackets, `[1, 37]`, and the check read 37 as a missing source. The strict check was right to refuse. The fix was in the prompt, and we found it only because the evaluation exposed it.

## Step 10. Orchestration: how the steps are wired together

| Type | Examples | Trade-off |
|---|---|---|
| **Plain code with direct API calls** (chosen) | Python services | Every step visible and testable |
| LLM frameworks | LangChain, LlamaIndex | Fast starts and many parts, but they hide the retrieval and prompt steps |
| Microsoft stack | Semantic Kernel, Azure AI Foundry | Natural in Azure, an extra layer to learn |
| Visual or low-code builders | Prompt flow, Copilot Studio | Quick, harder to test and version |

**Why plain code:** the value of this system is its guard rails, and we must explain them line by line to a reviewer. Frameworks make that harder.

## Step 11. The application layer

| Layer | Chosen | Main alternative and why not |
|---|---|---|
| API | FastAPI | Flask has no built-in validation. Django REST is heavier than needed |
| Screen | React with Vite and Tailwind | The brief names React. A notebook or Streamlit would be faster but is not a product screen |
| Security | API-key header on every route, key never shipped to the browser | A login system is out of scope. The brief asks for key authentication |

## Step 12. Evaluation: how we know it works

| Type | Strength | Weakness |
|---|---|---|
| **Labelled question set with expected sources** (chosen: 40 questions) | Objective and repeatable | Takes effort to write, and only as good as the questions |
| Manual spot checks | Quick | Not repeatable |
| Model as judge (for example RAGAS-style metrics) | Scales to many questions | The judge can be wrong, and it needs its own validation |
| User feedback in production | Real usage | Needs users and time |

**What the set contains:** answerable questions, questions whose answer depends on the date, and questions that must be refused. Each answerable question names the document version and key words the citation must contain.

**Results, said plainly:** 36 of 40 correct (90 percent) on the first full run. All 7 date questions and all 11 refusals were right. But the embedding quota ran out part way, so that run mixed vector and keyword search. A clean rerun is planned, and the script now records the search mode per question.

**Why this matters:** the evaluation found two real bugs the unit tests could not. That is its job.

## Step 13. Security, privacy and cost

| Concern | Decision |
|---|---|
| Secrets | Keys live in a git-ignored `.env`, and the browser never holds them |
| Prompt injection | Retrieved text is treated as data, and the prompt tells the model to ignore instructions inside it |
| Privacy | Public documents only. Questions are not stored in the embedding cache, only a hash. No client material on a free tier |
| Cost | About $0.001 per question for the model. About $126 a month for 100 users and $1,752 for 5,000 on the Azure target. Prices were read from the vendors' official price lists. The Azure prices are list prices and should be confirmed in the calculator |

## The whole architecture in 60 seconds

"This is a retrieval system built around one fact: the rules change by date. We store each regulation as dated versions in a relational database, because 'which version applied then' is a date-range query and 'every citation is real' is a foreign key. Documents are split at article boundaries so a citation points to something a lawyer recognises. Each passage becomes a vector, and a question is answered by filtering to the version in force on the chosen date and then ranking by meaning. A small language model writes the answer from six passages, and code, not the prompt, rejects any answer without a valid citation. We chose the simplest option at each step that met the need, behind interfaces so Azure AI Search and Azure OpenAI can replace the pilot parts. We could not get Azure access, so those claims are untested. We measured it on 40 questions and got about 90 percent, with every date and refusal question right."

## What is not done, so you can say it first

1. Azure AI Search and Azure OpenAI were not available, so the required stack is not demonstrated.
2. The 90 percent mixes search modes. A clean vector run is pending.
3. No reranker, no query rewriting, and no measured vector-versus-hybrid comparison.
4. 217 passages (old ESRS Set 1 text) have no vector.
5. The Pinecone adapter has not run against a live index.
6. Forty questions written by one person is a small test set.

Saying these first is a strength. It shows you know where the evidence stops.
