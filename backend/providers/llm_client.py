import json

from openai import OpenAI

from backend.core.settings import settings
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

Example:
[
  "High return promise",
  "Expert-led trading",
  "Urgent transfer request",
  "Fake customer support"
]

`risk_keywords`:
List of risk keywords.

Requirements:
- Must be an array of strings
- Each item must be a high-risk phrase or keyword
- Used for subsequent keyword matching

Example:
[
  "Guaranteed profit",
  "Risk-free return",
  "No experience needed",
  "Earn $500 daily",
  "Transfer immediately"
]


## Output Requirements

You must strictly output a JSON object in the following format:

{
  "summary": "...",
  "category": "...",
  "patterns": [],
  "risk_keywords": []
}

Do not output:
- markdown
- comments
- explanations
- extra text
- ```json
- formatting instructions

If any field cannot be extracted:
- Return "Unknown" for string fields
- Return [] for array fields

The final output must be valid JSON that can be correctly parsed by Python json.loads().
"""

class LLMAnalyzer:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url or None)

    def analyze(self, text: str) -> ScamAnalysis:
        prompt = PROMPT.strip()
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return self._parse_analysis(content, original_text=text)

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
