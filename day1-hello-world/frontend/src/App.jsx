import { useState } from "react";
import { Loader2, Send, AlertCircle } from "lucide-react";

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [reply, setReply] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setReply(null);
    try {
      const res = await fetch("/api/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Request failed");
      setReply(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-4xl font-semibold tracking-tight">
        DataFactZ <span className="brand-gradient-text">Hello World</span>
      </h1>
      <p className="mt-3 text-slate-300">
        A smoke test for your team's environment: FastAPI, React, and one model call.
      </p>

      <form onSubmit={submit} className="card mt-10 p-6">
        <label htmlFor="prompt" className="text-sm font-medium text-slate-300">
          Ask the model anything
        </label>
        <textarea
          id="prompt"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          rows={3}
          maxLength={2000}
          className="mt-2 w-full rounded-md border border-white/10 bg-black/20 p-3 text-sm"
          placeholder="Say hello in one sentence"
        />
        <button
          type="submit"
          disabled={loading || !prompt.trim()}
          className="brand-button mt-4 inline-flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold disabled:opacity-50"
        >
          {loading ? <Loader2 size={16} strokeWidth={2} className="animate-spin" /> : <Send size={16} strokeWidth={2} />}
          Send prompt
        </button>
      </form>

      {error && (
        <div role="alert" className="card mt-6 flex items-start gap-3 p-4 text-sm text-red-300">
          <AlertCircle size={18} strokeWidth={2} className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {reply && (
        <section className="card mt-6 p-6">
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{reply.reply}</p>
          <p className="mt-4 text-xs text-slate-400">Model: {reply.model}</p>
        </section>
      )}
    </main>
  );
}
