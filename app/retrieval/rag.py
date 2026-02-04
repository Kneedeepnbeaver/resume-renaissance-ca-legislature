"""RAG retrieval logic with keyword-augmented semantic search."""
import re
from typing import Optional

from app.ingestion.vector_store import VectorStore

# Common CA Legislature / government job terms to boost retrieval
CA_LEG_KEYWORDS = [
    "legislative", "constituent", "policy", "committee", "hearing", "briefing",
    "assembly", "senate", "district", "campaign", "constituency", "bill",
    "amendment", "stakeholder", "appropriations", "budget", "analysis",
    "communications", "outreach", "scheduling", "correspondence",
]


def extract_keywords(text: str, max_keywords: int = 25) -> list[str]:
    """
    Extract semantically important keywords from job description for better retrieval.
    Uses: capitalized phrases, bullet items, common CA Leg terms, and meaningful words.
    """
    if not text or not text.strip():
        return []
    text_lower = text.lower()
    seen = set()
    keywords = []

    # 1. Add CA Leg terms that appear in the text
    for term in CA_LEG_KEYWORDS:
        if term in text_lower and term not in seen:
            keywords.append(term)
            seen.add(term)

    # 2. Extract phrases from bullet lines (- item, * item)
    for m in re.finditer(r"^[\*\-]\s*(.+?)(?:\n|$)", text, re.MULTILINE | re.IGNORECASE):
        phrase = m.group(1).strip()[:60]
        # Take first few significant words
        words = [w for w in re.split(r"\W+", phrase) if len(w) > 2][:5]
        for w in words:
            wl = w.lower()
            if wl not in seen and len(wl) > 2:
                keywords.append(wl)
                seen.add(wl)

    # 3. Extract capitalized multi-word phrases (likely job requirements)
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
        phrase = m.group(1).lower()
        if phrase not in seen and 3 <= len(phrase) <= 40:
            keywords.append(phrase)
            seen.add(phrase)

    # 4. Meaningful words (4+ chars, not common stopwords)
    stop = {"that", "this", "with", "from", "have", "will", "your", "they", "when", "what"}
    for m in re.finditer(r"\b([a-z]{4,})\b", text_lower):
        w = m.group(1)
        if w not in seen and w not in stop:
            keywords.append(w)
            seen.add(w)

    return keywords[:max_keywords]


def build_augmented_query(job_description: str) -> str:
    """Build query that combines full description with extracted keywords for richer semantic match."""
    keywords = extract_keywords(job_description)
    if not keywords:
        return job_description
    kw_block = " ".join(keywords)
    return f"{job_description}\n\nKeywords for matching: {kw_block}"


def retrieve_context(
    vector_store: VectorStore,
    query: str,
    top_k: int = 12,
    include_doc_types: Optional[list[str]] = None,
    use_keyword_augmentation: bool = True,
) -> tuple[str, list[dict]]:
    """
    Retrieve relevant chunks using keyword-augmented semantic search.
    Extracts keywords from job description and augments the query for better chunk matching.
    Returns (context_string, list of chunk dicts for preview).
    """
    search_query = build_augmented_query(query) if use_keyword_augmentation else query
    results = vector_store.search(
        query=search_query,
        top_k=top_k,
        include_doc_types=include_doc_types,
    )

    chunks_for_preview = [
        {
            "content": r["content"],
            "source": r["metadata"].get("source", "unknown"),
            "doc_type": r["metadata"].get("doc_type", "unknown"),
        }
        for r in results
    ]

    # Build context string with source labels
    context_parts = []
    for i, r in enumerate(results):
        source = r["metadata"].get("source", "unknown")
        doc_type = r["metadata"].get("doc_type", "unknown")
        context_parts.append(f"[Source: {source} ({doc_type})]\n{r['content']}")
    context = "\n\n---\n\n".join(context_parts)

    return context, chunks_for_preview
