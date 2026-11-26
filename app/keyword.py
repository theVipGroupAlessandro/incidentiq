"""Keyword search with BM25, in plain Python. Baseline for the retrieval benchmark.

Same interface as SemanticIndex (search returns (document, score) pairs, best first),
so the benchmark can run both in the same way.
"""
import math
import re
from collections import Counter

# Very common English words that say nothing about the topic.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "in", "is", "it",
    "its", "of", "on", "or", "that", "the", "to", "was", "were", "with", "what", "when",
    "which", "who", "why", "how", "this", "these", "those", "there", "their", "our", "we",
    "should", "been", "being", "do", "does", "did", "not", "no",
}


def tokenize(text):
    """Lowercase words and numbers, without stopwords."""
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if token not in STOPWORDS]


class BM25Index:
    """BM25: a document scores high when it contains the query words, especially rare ones.

    k1 limits how much repeating a word helps; b corrects for document length
    (a long document contains many words just by being long).
    """

    def __init__(self, documents, k1=1.5, b=0.75):
        self.documents = documents
        self.model_key = "bm25"
        self.k1, self.b = k1, b
        self.term_counts = [Counter(tokenize(doc["text"])) for doc in documents]
        self.lengths = [sum(counts.values()) for counts in self.term_counts]
        self.average_length = sum(self.lengths) / len(self.lengths)
        # In how many documents each word appears: rare words are worth more.
        document_frequency = Counter(word for counts in self.term_counts for word in counts)
        n = len(documents)
        self.idf = {word: math.log(1 + (n - df + 0.5) / (df + 0.5)) for word, df in document_frequency.items()}

    def score(self, query_tokens, i):
        counts, length = self.term_counts[i], self.lengths[i]
        total = 0.0
        for word in query_tokens:
            if word in counts:
                tf = counts[word]
                total += self.idf[word] * tf * (self.k1 + 1) / (
                    tf + self.k1 * (1 - self.b + self.b * length / self.average_length))
        return total

    def search(self, query, top_k=5, where=None):
        query_tokens = tokenize(query)
        scored = [(self.score(query_tokens, i), i) for i in range(len(self.documents))]
        scored.sort(key=lambda pair: -pair[0])
        results = []
        for score, i in scored:
            if where is None or where(self.documents[i]):
                results.append((self.documents[i], score))
                if len(results) == top_k:
                    break
        return results