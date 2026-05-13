import httpx

from backend.core.settings import settings


class EmbeddingClient:
    def __init__(self) -> None:
        self.base_url = settings.siliconflow_base_url.rstrip("/")
        self.api_key = settings.siliconflow_api_key
        self.model = settings.embedding_model

    def embed_text(self, text: str) -> list[float]:
        if not self.api_key:
            raise ValueError("SILICONFLOW_API_KEY 未配置")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"input": text, "model": self.model}

        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("data") or []
        if not items:
            raise ValueError("Embedding 接口返回为空")
        vector = items[0].get("embedding")
        if not isinstance(vector, list) or not vector:
            raise ValueError("Embedding 向量格式非法")
        return [float(v) for v in vector]
