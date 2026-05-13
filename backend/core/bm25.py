from collections import Counter
import math
import re


def tokenize_for_bm25(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9$%]+|[\u4e00-\u9fff]{2,}", text)]


class BM25Index:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.doc_count = len(documents)
        self.doc_lens = [len(doc) for doc in documents]
        self.avgdl = sum(self.doc_lens) / self.doc_count if self.doc_count else 0.0
        self.tf = [Counter(doc) for doc in documents]
        self.df: Counter[str] = Counter()
        for tf in self.tf:
            self.df.update(tf.keys())

    def score(self, query_tokens: list[str], doc_idx: int) -> float:
        if self.doc_count == 0 or doc_idx >= self.doc_count:
            return 0.0
        if not query_tokens:
            return 0.0

        tf = self.tf[doc_idx]
        dl = self.doc_lens[doc_idx]
        denom_norm = self.k1 * (1 - self.b + self.b * (dl / self.avgdl)) if self.avgdl > 0 else self.k1

        score = 0.0
        for token in query_tokens:
            if token not in tf:
                continue
            df = self.df.get(token, 0)
            idf = math.log(1 + (self.doc_count - df + 0.5) / (df + 0.5))
            freq = tf[token]
            numerator = freq * (self.k1 + 1)
            denominator = freq + denom_norm
            score += idf * (numerator / denominator)

        return score
