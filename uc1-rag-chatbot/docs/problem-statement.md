# Problem statement: Regulatory change navigator

Use Case 1, RAG knowledge chatbot. Written for a client executive.

## The business problem

Sustainability reporting rules in the European Union are changing while companies are preparing to comply. The Corporate Sustainability Reporting Directive (CSRD) and its reporting standards (ESRS) have been delayed, simplified and reinterpreted through a series of legislative and guidance updates. For a global professional services firm, every client asks the same question: which obligations apply to us today, and by when?

Today, advisory teams answer that question by hand. A manager searches regulations, official guidance and internal briefings, checks whether each source has been replaced by a newer one, and writes an answer with citations. This takes hours per question, depends on who remembers the latest change, and carries real risk: an answer built on a superseded rule can lead a client to the wrong compliance decision.

## The user

Advisory managers and senior consultants at a firm like PwC who answer client regulatory questions across several countries. They are experts in the topic, short on time, and accountable for every statement they send to a client.

## What the solution does

A conversational assistant that answers regulatory questions only from a controlled library of public sources, and shows its evidence for every answer.

- Answers in plain language with numbered citations that link to the exact passage used.
- States which version of a rule applies on a date the user chooses, and flags when a source has been superseded.
- Filters by jurisdiction and company size, because the same rule applies differently by country and by size of company.
- Says when the library does not contain enough evidence, and does not guess.
- Keeps each conversation saved, so a manager can return to an earlier answer and its sources.

## Why this is an advanced case

| Challenge | What it demands from the design |
|---|---|
| Rules change over time | Documents carry effective dates and replacement links; retrieval respects the date in the question |
| Sources conflict or overlap | The assistant shows both sources and explains which one takes precedence |
| Same question, different answer by country and company size | Metadata filtering combined with semantic search |
| A wrong answer has professional and legal consequences | Required citations, refusal when evidence is weak, and a measured evaluation set |
| Client confidentiality | The library holds public sources only; the design explains how client documents would be isolated in a later phase |

## Success criteria

1. At least 90 percent of answers in a set of 40 test questions cite the correct source passage.
2. The assistant refuses or flags uncertainty on at least 90 percent of questions the library cannot answer.
3. For questions about a past or future date, the assistant picks the version of the rule in force on that date.
4. Median answer time under 8 seconds.
5. Every answer shows at least one citation, and every citation opens the source passage.

These targets are proposals. Confirm them against the UC1 brief and adjust.

## Out of scope

- Legal advice. The assistant supports advisors and never replaces their judgment.
- Client documents and confidential data. The pilot uses public sources only.
- Rules outside sustainability reporting, such as tax or financial reporting.
- Automatic monitoring of new legislation. The library is updated by hand in the pilot.
- Languages other than English.

## Source library for the pilot

Public texts only, to be downloaded from official sources: EU legislation on EUR-Lex, the ESRS standards, and official European Commission and EFRAG guidance. The status of each rule, including delays and simplification measures, changes often. Every regulatory statement in the design documents must be checked against the official source before it is used, as the program requires.

## Open questions for the UC1 brief

- Is a specific scenario or document set required?
- Which chat model is expected: Azure OpenAI or the Claude API?
- Are there required accuracy or response time targets?
