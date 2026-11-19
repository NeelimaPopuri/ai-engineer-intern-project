import { useEffect, useRef, useState } from "react";
import { AlertCircle, BookOpen, CalendarDays, Loader2, Send, ShieldAlert } from "lucide-react";

const today = new Date().toISOString().slice(0, 10);

async function api(path, options) {
  const res = await fetch(`/api/v1${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Request failed");
  return data;
}

function Citation({ number, c }) {
  const [open, setOpen] = useState(false);
  const range = `${c.effective_from} to ${c.effective_to ?? "today"}`;
  return (
    <li className="rounded-md border border-white/10 bg-black/20 p-3 text-xs">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-2 text-left"
        aria-expanded={open}
        aria-label={`Source ${number}: ${c.document_title}, version ${c.version_number}`}
      >
        <span className="brand-button rounded px-1.5 py-0.5 font-semibold">{number}</span>
        <span className="flex-1">
          <span className="block font-medium text-slate-200">{c.document_title}</span>
          <span className="block text-slate-400">
            Version {c.version_number} in force {range}
            {c.section_ref ? `, ${c.section_ref}` : ""}
          </span>
        </span>
      </button>
      {open && <p className="mt-3 whitespace-pre-wrap leading-relaxed text-slate-300">{c.quoted_text}</p>}
    </li>
  );
}

function Message({ m }) {
  if (m.role === "user") {
    return <div className="ml-auto max-w-[85%] rounded-lg bg-white/10 p-3 text-sm">{m.content}</div>;
  }
  const refused = m.answer_status === "insufficient_evidence";
  return (
    <div className="card max-w-[95%] p-4 text-sm">
      {m.answer_status === "conflict" && (
        <p className="mb-2 flex items-center gap-2 text-xs font-medium text-amber-300">
          <ShieldAlert size={14} strokeWidth={2} /> Sources of different authority: legal text prevails
        </p>
      )}
      {refused && (
        <p className="mb-2 flex items-center gap-2 text-xs font-medium text-amber-300">
          <ShieldAlert size={14} strokeWidth={2} /> Not enough evidence in the source library
        </p>
      )}
      <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>
      {m.citations.length > 0 && (
        <>
          <p className="mt-4 flex items-center gap-2 text-xs font-medium text-slate-400">
            <BookOpen size={14} strokeWidth={2} /> Sources
          </p>
          <ul className="mt-2 space-y-2">
            {m.citations.map((c) => (
              <Citation key={c.id} number={c.rank} c={c} />
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export default function App() {
  const [asOf, setAsOf] = useState(today);
  const [jurisdiction, setJurisdiction] = useState("EU");
  const [conversationId, setConversationId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const bottom = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // Filters belong to a conversation, so changing them starts a fresh one.
  function changeFilter(setter) {
    return (e) => {
      setter(e.target.value);
      setConversationId(null);
      setMessages([]);
    };
  }

  async function submit(e) {
    e.preventDefault();
    const text = question.trim();
    if (text.length < 3 || loading) return;
    setLoading(true);
    setError(null);
    try {
      let id = conversationId;
      if (!id) {
        const created = await api("/conversations", {
          method: "POST",
          body: JSON.stringify({ jurisdiction: jurisdiction || null, as_of_date: asOf }),
        });
        id = created.id;
        setConversationId(id);
      }
      setMessages((prev) => [...prev, { id: `q${Date.now()}`, role: "user", content: text, citations: [] }]);
      setQuestion("");
      const answer = await api(`/conversations/${id}/messages`, {
        method: "POST",
        body: JSON.stringify({ question: text }),
      });
      setMessages((prev) => [...prev, answer]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col px-6 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">
        Regulatory Change <span className="brand-gradient-text">Navigator</span>
      </h1>
      <p className="mt-2 text-sm text-slate-300">
        Ask about EU sustainability reporting. Answers come only from the source library, with the version that applied on the date you pick.
      </p>

      <div className="card mt-6 flex flex-wrap items-end gap-4 p-4 text-sm">
        <label className="flex flex-col gap-1">
          <span className="flex items-center gap-1 text-xs text-slate-400">
            <CalendarDays size={14} strokeWidth={2} /> Answer as of
          </span>
          <input type="date" value={asOf} onChange={changeFilter(setAsOf)} className="rounded-md border border-white/10 bg-black/20 p-2" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-xs text-slate-400">Jurisdiction</span>
          <select value={jurisdiction} onChange={changeFilter(setJurisdiction)} className="rounded-md border border-white/10 bg-black/20 p-2">
            <option value="EU">EU</option>
            <option value="">All</option>
          </select>
        </label>
      </div>

      <section className="mt-6 flex flex-1 flex-col gap-4" aria-live="polite">
        {messages.length === 0 && (
          <p className="text-sm text-slate-400">
            Try asking what net turnover and employee numbers Member States can use to exempt undertakings, then change the date to 2024 and ask again.
          </p>
        )}
        {messages.map((m) => (
          <Message key={m.id} m={m} />
        ))}
        {loading && (
          <p className="flex items-center gap-2 text-sm text-slate-400">
            <Loader2 size={16} strokeWidth={2} className="animate-spin" /> Searching the library
          </p>
        )}
        <div ref={bottom} />
      </section>

      {error && (
        <div role="alert" className="card mt-4 flex items-start gap-3 p-4 text-sm text-red-300">
          <AlertCircle size={18} strokeWidth={2} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={submit} className="card mt-4 flex items-end gap-3 p-4">
        <label htmlFor="q" className="sr-only">
          Your question
        </label>
        <textarea
          id="q"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }}
          rows={2}
          maxLength={1000}
          placeholder="Ask a question about the reporting rules"
          className="flex-1 rounded-md border border-white/10 bg-black/20 p-3 text-sm"
        />
        <button
          type="submit"
          disabled={loading || question.trim().length < 3}
          className="brand-button inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
        >
          {loading ? <Loader2 size={16} strokeWidth={2} className="animate-spin" /> : <Send size={16} strokeWidth={2} />}
          Ask
        </button>
      </form>
    </main>
  );
}
