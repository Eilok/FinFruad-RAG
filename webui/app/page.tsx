"use client";

import { useEffect, useMemo, useState } from "react";

import { detectRisk } from "@/lib/detect-api";
import type { DetectResponse, EvidenceItem } from "@/types/detect";

type RequestOptions = {
  keywordTopK: number;
  vectorTopK: number;
  returnEvidence: boolean;
};

const SESSION_KEY = "finfraud_detect_session";
const INITIAL_TEXT =
  "Customer support asks me to transfer money immediately to cancel an auto-renew subscription.";
const DEFAULT_OPTIONS: RequestOptions = {
  keywordTopK: 3,
  vectorTopK: 3,
  returnEvidence: true,
};

function EvidenceList({ title, items }: { title: string; items: EvidenceItem[] }) {
  return (
    <section className="card p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-600">{title}</h3>
        <span className="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600">{items.length}</span>
      </div>
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">No evidence returned.</p>
      ) : (
        <ul className="space-y-3">
          {items.map((item) => (
            <li key={`${title}-${item.record_id}`} className="rounded-xl border border-slate-200 bg-slate-50/70 p-3">
              <div className="flex flex-wrap items-center gap-2 text-xs text-slate-600">
                <span className="rounded bg-white px-2 py-1">{item.record_id}</span>
                <span>{item.source}</span>
                <span>{item.category}</span>
                <span className="font-semibold text-slate-800">score {item.score.toFixed(3)}</span>
              </div>
              <p className="mt-2 text-sm text-slate-800">{item.summary}</p>
              <p className="mt-2 text-xs text-slate-600">Patterns: {item.patterns.join(", ") || "-"}</p>
              <p className="mt-1 text-xs text-slate-600">Risk keywords: {item.risk_keywords.join(", ") || "-"}</p>
              {item.matched_keywords.length > 0 && (
                <p className="mt-1 text-xs text-amber-700">Matched keywords: {item.matched_keywords.join(", ")}</p>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function Home() {
  const [text, setText] = useState(INITIAL_TEXT);
  const [options, setOptions] = useState<RequestOptions>(DEFAULT_OPTIONS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");
  const [result, setResult] = useState<DetectResponse | null>(null);

  useEffect(() => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify({ text, options, result }));
  }, [text, options, result]);

  const detectionTone = useMemo(() => {
    if (!result) return "text-slate-600";
    return result.detection.is_scam ? "text-red-700" : "text-teal-700";
  }, [result]);

  async function onDetect() {
    setLoading(true);
    setError("");
    try {
      const data = await detectRisk({
        text,
        keyword_top_k: options.keywordTopK,
        vector_top_k: options.vectorTopK,
        return_evidence: options.returnEvidence,
      });
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown request error");
    } finally {
      setLoading(false);
    }
  }

  function onClear() {
    setText("");
    setResult(null);
    setError("");
  }

  async function onCopy() {
    if (!result) return;
    await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
  }

  return (
    <main className="mx-auto w-full max-w-6xl p-6 md:p-10">
      <header className="mb-6 card overflow-hidden">
        <div className="bg-gradient-to-r from-amber-500 to-orange-500 p-5 text-white">
          <p className="text-xs uppercase tracking-[0.2em]">Fraud Intelligence Console</p>
          <h1 className="mt-2 text-2xl font-semibold">FinFraud-RAG Risk Detection</h1>
          <p className="mt-2 text-sm text-amber-50">
            Hybrid retrieval combines BM25 matching and semantic similarity before LLM decision.
          </p>
        </div>
      </header>

      <section className="card p-5">
        <label htmlFor="input-text" className="text-sm font-semibold text-slate-700">
          Input text for risk analysis
        </label>
        <textarea
          id="input-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-200"
          placeholder="Paste message, email, ad copy, or chat transcript here..."
        />

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="text-sm text-slate-700">
            BM25 top-k
            <input
              type="number"
              min={1}
              max={20}
              value={options.keywordTopK}
              onChange={(e) =>
                setOptions((prev) => ({ ...prev, keywordTopK: Number(e.target.value) || 1 }))
              }
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-amber-500"
            />
          </label>
          <label className="text-sm text-slate-700">
            Vector top-k
            <input
              type="number"
              min={1}
              max={20}
              value={options.vectorTopK}
              onChange={(e) => setOptions((prev) => ({ ...prev, vectorTopK: Number(e.target.value) || 1 }))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-amber-500"
            />
          </label>
          <label className="flex items-center gap-2 pt-7 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={options.returnEvidence}
              onChange={(e) => setOptions((prev) => ({ ...prev, returnEvidence: e.target.checked }))}
            />
            Return retrieval evidence
          </label>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          <button
            type="button"
            onClick={onDetect}
            disabled={loading}
            className="cursor-pointer rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-amber-300"
          >
            {loading ? "Detecting..." : "Run Detection"}
          </button>
          <button
            type="button"
            onClick={onClear}
            className="cursor-pointer rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-100"
          >
            Clear
          </button>
          <button
            type="button"
            onClick={onDetect}
            className="cursor-pointer rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-100"
          >
            Retry
          </button>
          <button
            type="button"
            onClick={onCopy}
            disabled={!result}
            className="cursor-pointer rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-400"
          >
            Copy JSON
          </button>
        </div>

        {error && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}
      </section>

      <section className="mt-6 card p-5">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-600">Detection Result</h2>
        {!result ? (
          <p className="mt-2 text-sm text-slate-500">No result yet. Submit a text to start detection.</p>
        ) : (
          <div className="mt-3 space-y-2">
            <p className={`text-lg font-semibold ${detectionTone}`}>
              Verdict: {result.detection.is_scam ? "Likely Fraud" : "Likely Safe"}
            </p>
            <p className="text-sm text-slate-700">Confidence: {result.detection.confidence.toFixed(3)}</p>
            <p className="text-sm text-slate-700">Reason: {result.detection.reason}</p>
            <p className="text-sm text-slate-700">
              Evidence refs: {result.detection.evidence_refs.length > 0 ? result.detection.evidence_refs.join(", ") : "-"}
            </p>
          </div>
        )}
      </section>

      <section className="mt-6 grid gap-4 lg:grid-cols-3">
        <EvidenceList title="BM25 Retrieval" items={result?.keyword_hits ?? []} />
        <EvidenceList title="Vector Retrieval" items={result?.vector_hits ?? []} />
        <EvidenceList title="Fused Evidence" items={result?.fused_hits ?? []} />
      </section>
    </main>
  );
}
