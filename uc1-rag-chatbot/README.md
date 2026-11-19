# Use Case 1: Regulatory change navigator

A retrieval-augmented chatbot that answers EU sustainability reporting questions from a controlled library of public sources, with citations and date-aware answers.

**Stack (planned):** Python 3.11+, FastAPI, PostgreSQL with Alembic, Azure AI Search, Azure OpenAI or Claude API, React (Vite), Tailwind CSS, Lucide icons.

**Status:** backend foundation, chunking and ingestion built and tested. Retrieval and the chat API come next.

## Documents

- [Problem statement](docs/problem-statement.md)
- [Database design](docs/database-design.md)
- [Solution design](docs/solution-design.md)

## Next steps

1. Confirm the scenario against the UC1 brief.
2. Design the database and write the solution design document with rejected alternatives.
3. Collect the public source library.
4. Build ingestion, the chat API and the chat interface.
