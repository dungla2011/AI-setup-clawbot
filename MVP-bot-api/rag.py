"""
rag.py — Retrieval-Augmented Generation: find relevant chunks for a query.

Strategy: cosine similarity between query embedding and all chunk embeddings,
filtered by allowed categories (access control).
Vector store: SQLite BLOB (no external DB needed for MVP).
"""

import numpy as np
from typing import Optional
from database import get_db
from embeddings import embed, from_blob, cosine_similarity

# ── Access control ────────────────────────────────────────────────────────────

CATEGORY_ACCESS: dict[str, Optional[list[str]]] = {
    "customer": ["customer_guide", "product_faq"],
    "staff":    None,   # None = all categories
    "admin":    None,
}


def get_allowed_categories(user_role: str) -> Optional[list[str]]:
    """
    Return list of allowed category IDs for this role.
    None means ALL categories allowed.
    """
    return CATEGORY_ACCESS.get(user_role, CATEGORY_ACCESS["customer"])


# ── Retrieval ─────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    user_role: str = "customer",
    top_k: int = 5,
    min_score: float = 0.30,
    category_hint: Optional[str] = None,
) -> list[dict]:
    """
    Find the most relevant document chunks for `query`.

    Args:
        query:         User question
        user_role:     "customer" | "staff" | "admin"
        top_k:         Max chunks to return
        min_score:     Minimum cosine similarity threshold
        category_hint: Optional specific category the user selected in UI

    Returns:
        List of {content, category_id, source_file, page_num, score}
    """
    if not query.strip():
        return []

    allowed = get_allowed_categories(user_role)

    # If user chose a specific category, use it (only if it's in their allowed set)
    if category_hint:
        if allowed is None or category_hint in allowed:
            allowed = [category_hint]

    # Load chunks (with embeddings) filtered by allowed categories
    with get_db() as conn:
        cursor = conn.cursor()

        if allowed is None:
            # All categories
            cursor.execute("""
                SELECT c.id, c.content, c.category_id, c.page_num, c.embedding,
                       d.filename
                FROM doc_chunks c
                JOIN documents d ON c.doc_id = d.id
                WHERE d.is_active = 1 AND c.embedding IS NOT NULL
            """)
        else:
            placeholders = ",".join("?" * len(allowed))
            cursor.execute(f"""
                SELECT c.id, c.content, c.category_id, c.page_num, c.embedding,
                       d.filename
                FROM doc_chunks c
                JOIN documents d ON c.doc_id = d.id
                WHERE c.category_id IN ({placeholders})
                  AND d.is_active = 1
                  AND c.embedding IS NOT NULL
            """, allowed)

        rows = cursor.fetchall()

    if not rows:
        return []

    # Embed query
    query_vec = embed(query)

    # Score all chunks
    scored = []
    for row in rows:
        try:
            chunk_vec = from_blob(row["embedding"])
            score = cosine_similarity(query_vec, chunk_vec)
            if score >= min_score:
                scored.append({
                    "content":     row["content"],
                    "category_id": row["category_id"],
                    "source_file": row["filename"],
                    "page_num":    row["page_num"],
                    "score":       round(score, 4),
                })
        except Exception:
            continue

    # Sort by score descending, take top_k
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def format_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a context block for the system prompt.
    """
    if not chunks:
        return ""

    parts = ["=== Tài liệu tham khảo ==="]
    for i, c in enumerate(chunks, 1):
        source = f"{c['source_file']}"
        if c.get("page_num"):
            source += f", trang {c['page_num']}"
        parts.append(f"\n[{i}] Nguồn: {source} (score: {c['score']})\n{c['content']}")
    parts.append("\n=== Kết thúc tài liệu ===")
    return "\n".join(parts)
