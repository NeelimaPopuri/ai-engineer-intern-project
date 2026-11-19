"""Run the evaluation questions against the real search and model, then write a results report.

Run from the backend folder:
    .venv\Scripts\python.exe ..\scripts\run_eval.py

Nothing is saved to the database (the run is rolled back). Results go to docs/evaluation-results.md.
"""

import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.answer import answer_question  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.config import settings  # noqa: E402
from app.llm import LLMError  # noqa: E402
from app.models import Conversation  # noqa: E402
from app.search import LocalHybridIndex  # noqa: E402


# Paid-tier prices in USD per 1M tokens (input, output), read from the Gemini pricing page on 2026-11-19.
PRICES = {"gemini-3.1-flash-lite": (0.25, 1.50), "gemini-3.5-flash-lite": (0.30, 2.50)}
DEFAULT_MODEL = "gemini-3.1-flash-lite"


def grade(q: dict, msg) -> tuple[bool, str]:
    refused = msg.answer_status == "insufficient_evidence"
    if q["expect"] == "refuse":
        return refused, "refused" if refused else "answered, should have refused"
    if refused:
        return False, "refused, should have answered"
    for c in msg.citations:
        version = c.chunk.version
        right_doc = q["doc"].lower() in version.document.title.lower()
        right_version = version.version_number == q["version"]
        has_terms = not q["terms"] or any(t.lower() in c.quoted_text.lower() for t in q["terms"])
        if right_doc and right_version and has_terms:
            return True, "correct source cited"
    return False, "answered but wrong source or version"


def main() -> int:
    questions = json.loads((ROOT / "data" / "eval_questions.json").read_text(encoding="utf-8"))
    rows, latencies, tokens_in, tokens_out = [], [], 0, 0
    with SessionLocal() as session:
        index = LocalHybridIndex(session)
        for q in questions:
            conversation = Conversation(as_of_date=date.fromisoformat(q["as_of"]))
            session.add(conversation)
            session.flush()
            started = time.monotonic()
            try:
                msg = answer_question(session, conversation, q["question"], index)
                ok, note = grade(q, msg)
                status = msg.answer_status
                tokens_in += msg.input_tokens or 0
                tokens_out += msg.output_tokens or 0
            except LLMError as exc:
                ok, note, status = False, f"model error: {exc}", "error"
            latencies.append(time.monotonic() - started)
            rows.append((q, ok, note, status))
            print(f"{'PASS' if ok else 'FAIL'}  #{q['id']:>2} {q['group']:<10} {note}")
            time.sleep(1)
        session.rollback()

    groups = {}
    for q, ok, *_ in rows:
        groups.setdefault(q["group"], []).append(ok)
    total = sum(ok for _, ok, *_ in rows)
    median = sorted(latencies)[len(latencies) // 2]
    price = PRICES.get(settings.gemini_model)
    cost = (tokens_in * price[0] + tokens_out * price[1]) / 1_000_000 if price else None
    lines = [
        "# Evaluation results", "",
        f"Run on {date.today().isoformat()} with {len(rows)} questions from `data/eval_questions.json`.", "",
        f"- Overall: {total} of {len(rows)} correct ({100 * total // len(rows)}%)",
        *[f"- {g}: {sum(v)} of {len(v)}" for g, v in groups.items()],
        f"- Model: {settings.gemini_model}",
        f"- Median time per question: {median:.1f}s",
        f"- Tokens: {tokens_in:,} in, {tokens_out:,} out" + (f", about ${cost:.4f} for the run ({cost / len(rows):.5f} per question)" if cost is not None else ""), "",
        "| # | Group | Question | Result | Note |", "|---|---|---|---|---|",
        *[f"| {q['id']} | {q['group']} | {q['question']} | {'pass' if ok else 'fail'} | {note} |" for q, ok, note, _ in rows],
    ]
    name = "evaluation-results.md" if settings.gemini_model == DEFAULT_MODEL else f"evaluation-results-{settings.gemini_model}.md"
    (ROOT / "docs" / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
