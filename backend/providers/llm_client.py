import json

from openai import OpenAI

from backend.core.settings import settings
from backend.models.api import DetectionResult
from backend.models.knowledge import ScamAnalysis

PROMPT = """
You are a financial anti-fraud knowledge extraction system.

Your task is:
Extract fraud-related knowledge from the input text and return the result as a JSON object for building a financial fraud risk knowledge base.

## Field Definitions

`summary`:
- Use 1~3 complete natural language sentences
- Summarize the core fraudulent content
- Must preserve key fraud-related semantics
- Used for subsequent vector retrieval
- Do not simply copy the original text
- Do not omit important fraudulent behaviors

`category`:
Fraud category.

You must select the single most appropriate category from the following list:

- Investment Scam
- Recruitment Scam
- Fake Loan Scam
- Impersonation of Financial Institutions
- Telecom Fraud
- Task/Commission Scam
- Fake Prize Scam
- Customer Service Impersonation
- Phishing Scam
- Cryptocurrency Scam
- Romance Scam
- Other Scam

`patterns`:
List of fraud patterns.

Requirements:
- Must be an array of strings
- Each item must be a concise phrase
- Each item must not exceed 20 words
- Summarize fraudulent tactics
- Do not use complete sentences

`risk_keywords`:
List of risk keywords.

Requirements:
- Must be an array of strings
- Each item must be a high-risk phrase or keyword
- Used for subsequent keyword matching

## Output Requirements

You must strictly output a JSON object in the following format:

{
  "summary": "...",
  "category": "...",
  "patterns": [],
  "risk_keywords": []
}

Do not output markdown, comments, explanations, or extra text.
If any field cannot be extracted, return "Unknown" for string fields and [] for array fields.
"""

DETECT_PROMPT = """
You are a financial fraud risk decision engine.

You are given:
1) A user input text.
2) Retrieved evidence from a fraud knowledge base.

Task:
Judge whether the user text is likely fraud-related.

Output JSON format only:
{
  "is_scam": true,
  "confidence": 0.0,
  "reason": "...",
  "evidence_refs": ["record_id_1", "record_id_2"]
}

Rules:
- confidence must be in [0, 1].
- reason should be concise and based on both text and evidence.
- evidence_refs should reference the most relevant evidence ids; return [] if none is useful.
- Output JSON only.
"""

NO_RAG_PROMPT = """
You are a financial fraud classifier.

Given only the input text, decide if it is likely scam-related.
Return JSON only:
{
  "is_scam": true,
  "confidence": 0.0,
  "reason": "...",
  "evidence_refs": []
}

Rules:
- Use only the input text. Do not assume external context.
- confidence must be in [0,1].
- Keep reason concise.
"""


class LLMAnalyzer:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url or None)

    def analyze(self, text: str) -> ScamAnalysis:
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": PROMPT.strip()},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_analysis(content, original_text=text)

    def detect(self, text: str, evidence_context: str) -> DetectionResult:
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": DETECT_PROMPT.strip()},
                {
                    "role": "user",
                    "content": f"Input text:\n{text}\n\nRetrieved evidence:\n{evidence_context}",
                },
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_detection(content)

    def detect_no_rag(self, text: str) -> DetectionResult:
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": NO_RAG_PROMPT.strip()},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_detection(content)

    @staticmethod
    def _parse_analysis(content: str, original_text: str) -> ScamAnalysis:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = {}

        summary = str(payload.get("summary") or "").strip() or original_text[:180]
        category = str(payload.get("category") or "Unknown").strip() or "Unknown"

        patterns_raw = payload.get("patterns") or []
        keywords_raw = payload.get("risk_keywords") or []

        patterns = [str(x).strip() for x in patterns_raw if str(x).strip()] if isinstance(patterns_raw, list) else []
        risk_keywords = [str(x).strip() for x in keywords_raw if str(x).strip()] if isinstance(keywords_raw, list) else []

        return ScamAnalysis(
            summary=summary,
            category=category,
            patterns=patterns,
            risk_keywords=risk_keywords,
        )

    @staticmethod
    def _parse_detection(content: str) -> DetectionResult:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError:
            payload = {}

        is_scam = bool(payload.get("is_scam", False))
        confidence = float(payload.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))
        reason = str(payload.get("reason") or "Insufficient evidence.").strip() or "Insufficient evidence."

        refs_raw = payload.get("evidence_refs") or []
        evidence_refs = [str(x).strip() for x in refs_raw if str(x).strip()] if isinstance(refs_raw, list) else []

        return DetectionResult(
            is_scam=is_scam,
            confidence=confidence,
            reason=reason,
            evidence_refs=evidence_refs,
        )
