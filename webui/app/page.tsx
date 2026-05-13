"use client";

import { useEffect, useMemo, useState } from "react";

import { detectRisk } from "@/lib/detect-api";
import { ingestKnowledge } from "@/lib/kb-api";
import type { DetectResponse, EvidenceItem } from "@/types/detect";
import type { IngestItem, IngestResponse } from "@/types/ingest";

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

  const [ingestText, setIngestText] = useState("");
  const [ingestSource, setIngestSource] = useState("manual_upload");
  const [ingestRetryTimes, setIngestRetryTimes] = useState(2);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestError, setIngestError] = useState("");
  const [ingestResult, setIngestResult] = useState<IngestResponse | null>(null);

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

  async function onIngestSingleText() {
    const trimmed = ingestText.trim();
    if (!trimmed) {
      setIngestError("Please enter scam text before ingestion.");
      return;
    }

    setIngestLoading(true);
    setIngestError("");
    try {
      const payload = {
        items: [{ text: trimmed, source: ingestSource.trim() || "manual_upload" }],
        retry_times: ingestRetryTimes,
      };
      const data = await ingestKnowledge(payload);
      setIngestResult(data);
      setIngestText("");
    } catch (err) {
      setIngestError(err instanceof Error ? err.message : "Ingestion request failed");
    } finally {
      setIngestLoading(false);
    }
  }

  async function onUploadFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setIngestLoading(true);
    setIngestError("");
    try {
      const content = await file.text();
      const lines = content.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);

      const items: IngestItem[] = [];
      for (const line of lines) {
        if (line.startsWith("{")) {
          const obj = JSON.parse(line) as { text?: string; source?: string };
          const parsedText = (obj.text || "").trim();
          if (!parsedText) continue;
          items.push({
            text: parsedText,
            source: (obj.source || ingestSource || "manual_upload").trim(),
          });
        } else {
          items.push({ text: line, source: ingestSource.trim() || "manual_upload" });
        }
      }

      if (items.length === 0) {
        throw new Error("Uploaded file contains no valid text items.");
      }

      const data = await ingestKnowledge({
        items,
        retry_times: ingestRetryTimes,
      });
      setIngestResult(data);
    } catch (err) {
      setIngestError(err instanceof Error ? err.message : "Failed to parse or ingest file");
    } finally {
      event.target.value = "";
      setIngestLoading(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-6xl p-6 md:p-10">
      <header className="mb-6 card overflow-hidden">
        <div className="bg-gradient-to-r from-amber-500 to-orange-500 p-5 text-white">
          <p className="text-xs uppercase tracking-[0.2em]">Fraud Intelligence Console</p>
          <h1 className="mt-2 text-2xl font-semibold">FinFraud-RAG</h1>
          <p className="mt-2 text-sm text-amber-50">
            Intelligent Financial Fraud Governance System, supporting: (1) Fraud text identification, (2) Fraud text analysis and upload, to realize a self-evolving risk governance system.
          </p>
        </div>
      </header>

      <section className="card p-5">
        <h2 className="text-sm font-semibold uppercase tracking-[0.16em] text-slate-600">Knowledge Ingestion</h2>
        <p className="mt-2 text-sm text-slate-600">
          Add new scam texts to the knowledge base via direct input or file upload.
        </p>

        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <label className="text-sm text-slate-700 md:col-span-2">
            Source tag
            <input
              type="text"
              value={ingestSource}
              onChange={(e) => setIngestSource(e.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-amber-500"
              placeholder="manual_upload"
            />
          </label>
          <label className="text-sm text-slate-700">
            Retry times
            <input
              type="number"
              min={0}
              max={5}
              value={ingestRetryTimes}
              onChange={(e) => setIngestRetryTimes(Math.max(0, Math.min(5, Number(e.target.value) || 0)))}
              className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-amber-500"
            />
          </label>
        </div>

        <label htmlFor="ingest-text" className="mt-4 block text-sm font-semibold text-slate-700">
          Single scam text
        </label>
        <textarea
          id="ingest-text"
          value={ingestText}
          onChange={(e) => setIngestText(e.target.value)}
          rows={4}
          className="mt-2 w-full rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-amber-500 focus:ring-2 focus:ring-amber-200"
          placeholder="Enter a scam-related text to ingest..."
        />

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onIngestSingleText}
            disabled={ingestLoading}
            className="cursor-pointer rounded-lg bg-amber-500 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-amber-300"
          >
            {ingestLoading ? "Ingesting..." : "Ingest Single Text"}
          </button>

          <label className="cursor-pointer rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-100">
            Upload txt/jsonl
            <input type="file" accept=".txt,.jsonl" onChange={onUploadFile} className="hidden" />
          </label>
        </div>

        {ingestError && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {ingestError}
          </p>
        )}

        {ingestResult && (
          <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
            <p>
              Ingest result: total={ingestResult.total}, success={ingestResult.success}, failed={ingestResult.failed}
            </p>
            {ingestResult.errors.length > 0 && (
              <p className="mt-1 text-red-700">Errors: {ingestResult.errors.slice(0, 3).join(" | ")}</p>
            )}
          </div>
        )}
      </section>

      <section className="mt-6 card p-5">
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
