import type { DetectRequest, DetectResponse } from "@/types/detect";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

export async function detectRisk(payload: DetectRequest): Promise<DetectResponse> {
  const response = await fetch(`${API_BASE_URL}/detect`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  const raw = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = typeof raw?.detail === "string" ? raw.detail : "Request failed";
    throw new Error(detail);
  }

  return raw as DetectResponse;
}
