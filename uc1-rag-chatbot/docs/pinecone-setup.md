# Pinecone setup

Optional. The app already works without Pinecone, using its own in-memory vector search. This adds Pinecone as an alternative vector store, behind the same `SearchIndex` interface. Only vectors, chunk ids and a few filter fields (version dates, jurisdiction) go to Pinecone. The passage text stays in our database.

Status: the adapter is built and tested against a fake Pinecone (14 tests). It has not been run against a live index yet, because that needs your account and key. Step 6 is that first live test.

## What you do (I cannot create accounts or keys for you)

1. **Create a free account** at https://app.pinecone.io and sign in.
2. **Create an API key** in the console (API keys section). Copy it once. Do not paste it into chat, a commit, or a screenshot.
3. **Create an index** with these settings. Pinecone's page layout changes, so match the settings and not the button names:
   - Type: a plain **dense** index where you **bring your own vectors**. Do not choose integrated embedding (that makes Pinecone embed the text itself, and our vectors come from Gemini).
   - **Dimension: 768** (the size of our `gemini-embedding-001` vectors).
   - **Metric: cosine**.
   - Cloud and region: whatever the free plan offers.
   - Name: anything, for example `uc1-chunks`.
4. **Copy the index host** from the index page. It looks like `uc1-chunks-xxxxxxx.svc.xxxx.pinecone.io`.
5. **Put both values in `uc1-rag-chatbot/.env`** (this file is git-ignored):
   ```
   PINECONE_API_KEY=your-key-here
   PINECONE_INDEX_HOST=uc1-chunks-xxxxxxx.svc.xxxx.pinecone.io
   ```

## What to run after that

From `uc1-rag-chatbot\backend`:

```powershell
# 6. copy the 1,830 stored vectors to Pinecone (about 5.6 MB, safe to repeat)
.\.venv\Scripts\python.exe ..\scripts\sync_pinecone.py

# 7. switch the app to Pinecone: add this line to .env, then restart the backend
SEARCH_BACKEND=pinecone
```

Step 6 should print `upserted 1830 vectors into namespace 'uc1'`. If it stops with an HTTP error, send me the message (not the key) and I will fix the adapter. An error like 401 means the key is wrong, and 404 usually means the host is wrong.

To go back, set `SEARCH_BACKEND=vector` or delete the line.

## Behaviour to know

- **Fallback.** If Pinecone is not configured, unreachable, or the question cannot be embedded, search falls back to the local vector search and then to keywords. The app keeps answering.
- **Stale dates cannot leak.** Pinecone stores each chunk's version dates from the last sync. After ingesting a new document version, run `sync_pinecone.py` again. Even before you do, every hit is re-checked against our database, so a superseded rule is dropped and never shown as current.
- **Quota.** Each question still costs one Gemini embedding request, the same as local vector search.
- **Cost.** Check Pinecone's pricing page for the current free plan limits. 1,830 vectors of 768 numbers is about 5.6 MB, which is tiny.
- **Privacy.** The library is public documents. Pinecone receives vectors and ids, not text. Do not store client material in it without checking the terms and data location with your mentor.
