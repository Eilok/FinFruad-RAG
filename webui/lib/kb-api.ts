import type { IngestRequest, IngestResponse } from "@/types/ingest";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export async function ingestKnowledge(payload: IngestRequest): Promise<IngestResponse> {
  const response = await fetch(`${API_BASE_URL}/kb/ingest`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const raw = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof raw?.detail === "string" ? raw.detail : "Ingestion request failed";
    throw new Error(detail);
  }

  return raw as IngestResponse;
}
