# md-03 — RAG Document Q&A System

> **Mục tiêu:** Cho phép upload nhiều loại tài liệu, phân loại theo category, kiểm soát quyền truy cập (user khách hàng vs nội bộ), và AI trả lời dựa đúng trên nội dung tài liệu đó.

---

## 1. Có cần RAG không?

**Có — và bắt buộc nếu:**

| Tình huống | Cần RAG? | Lý do |
|---|---|---|
| 1 tài liệu ngắn < 8K token | Không | Nhét thẳng vào system prompt |
| Nhiều tài liệu / tài liệu dài | **Có** | Context window giới hạn, tốn tiền nếu gửi hết |
| Tài liệu update thường xuyên | **Có** | Cập nhật chunk không cần retrain |
| Phân loại bảo mật (nội bộ / khách) | **Có** | Filter theo category/namespace |

→ **Kết luận:** Cần RAG từ đầu, không nên skip dù MVP.

---

## 2. Kiến trúc tổng thể

```
┌──────────────────────────────────────────────────────────┐
│                    ADMIN / UPLOADER                       │
│   Upload file → chọn Category → POST /docs/upload        │
└─────────────────────────┬────────────────────────────────┘
                          │
                    ┌─────▼──────┐
                    │  api.py    │  POST /docs/upload
                    └─────┬──────┘
                          │
              ┌───────────▼────────────┐
              │   doc_processor.py     │
              │  • Parse (PDF/DOCX/TXT)│
              │  • Chunk (500 tokens)  │
              │  • Embed (MiniLM / API)│
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │   Vector Store (SQLite │
              │   + sqlite-vec         │
              │   hoặc ChromaDB local) │
              │                        │
              │  namespace = category  │
              └───────────┬────────────┘
                          │
┌──────────────────────────────────────────────────────────┐
│                    USER / CHAT                            │
│   POST /chat  { message, user_id, category? }            │
└─────────────────────────┬────────────────────────────────┘
                          │
                    ┌─────▼──────┐
                    │  api.py    │
                    └─────┬──────┘
                          │
              ┌───────────▼────────────┐
              │   rag.py               │
              │  1. Embed query        │
              │  2. Vector search      │
              │     (filter by allowed │
              │      categories)       │
              │  3. Return top-K chunks│
              └───────────┬────────────┘
                          │
              ┌───────────▼────────────┐
              │   bot.py               │
              │  system_prompt +=      │
              │  retrieved_context     │
              └───────────┬────────────┘
                          │
                    Claude API → trả lời
```

---

## 3. Categories & Access Control

### 3.1 Danh sách category đề xuất

| Category ID | Tên hiển thị | Ai được đọc |
|---|---|---|
| `customer_guide` | Hướng dẫn khách hàng | Tất cả (public) |
| `product_faq` | FAQ Sản phẩm | Tất cả (public) |
| `internal_policy` | Nội quy nội bộ | Nhân viên (internal) |
| `internal_pricing` | Bảng giá nội bộ | Nhân viên (internal) |
| `hr_handbook` | Quy chế nhân sự | Nhân viên (internal) |
| `training` | Tài liệu đào tạo | Nhân viên (internal) |

### 3.2 User roles

```
user_role ∈ { "customer", "staff", "admin" }
```

- **customer** → chỉ truy cập category `public = True`
- **staff** → truy cập tất cả
- **admin** → upload, xóa, quản lý docs

### 3.3 Allowed categories per role

```python
CATEGORY_ACCESS = {
    "customer": ["customer_guide", "product_faq"],
    "staff":    ["customer_guide", "product_faq",
                 "internal_policy", "internal_pricing",
                 "hr_handbook", "training"],
    "admin":    "*",   # all
}
```

**Bảo mật phía Vector Search:**  
Filter namespace trước khi search → dù user biết chunk_id, không thể query nội bộ.

---

## 4. Luồng chat có RAG

### Khi user chat:

```
1. Frontend gửi:
   POST /chat
   {
     "message": "Chính sách nghỉ phép là gì?",
     "user_id": "uuid",
     "user_role": "staff",          ← thêm field này
     "category_hint": "internal_policy"  ← optional, user chọn
   }

2. api.py:
   - Xác định allowed_categories từ user_role
   - Gọi rag.retrieve(query, allowed_categories, top_k=5)

3. rag.py:
   - Embed query → vector
   - sqlite-vec / ChromaDB: WHERE category IN allowed_categories
   - Trả về top-5 chunks có score cao nhất

4. bot.py:
   - Build system_prompt:
     [BASE_PROMPT]
     [USER_MEMORY]
     
     === Tài liệu tham khảo ===
     [Chunk 1 - Nguồn: noi_quy.pdf, Trang 3]
     ...nội dung...
     
     [Chunk 2 - Nguồn: hr_handbook.docx, Trang 12]
     ...nội dung...
     =========================

5. Claude trả lời dựa trên chunks đó
6. Trích dẫn nguồn: "Theo nội quy công ty (trang 3)..."
```

---

## 5. Database schema

### Bảng `doc_categories`
```sql
CREATE TABLE doc_categories (
    id          TEXT PRIMARY KEY,   -- "internal_policy"
    name        TEXT NOT NULL,      -- "Nội quy nội bộ"
    is_public   INTEGER DEFAULT 0,  -- 0=internal, 1=public
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);
```

### Bảng `documents`
```sql
CREATE TABLE documents (
    id          TEXT PRIMARY KEY,
    category_id TEXT REFERENCES doc_categories(id),
    filename    TEXT NOT NULL,
    file_type   TEXT,               -- "pdf", "docx", "txt", "md"
    file_size   INTEGER,
    total_chunks INTEGER,
    uploaded_by TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    is_active   INTEGER DEFAULT 1
);
```

### Bảng `doc_chunks`
```sql
CREATE TABLE doc_chunks (
    id          TEXT PRIMARY KEY,
    doc_id      TEXT REFERENCES documents(id),
    category_id TEXT,               -- denorm để filter nhanh
    chunk_index INTEGER,
    content     TEXT NOT NULL,
    page_num    INTEGER,
    token_count INTEGER,
    embedding   BLOB,               -- vector float32[]
    created_at  TEXT DEFAULT (datetime('now'))
);
-- Index để tìm theo category
CREATE INDEX idx_chunks_category ON doc_chunks(category_id);
```

---

## 6. File mới cần tạo

```
MVP-bot-api/
├── doc_processor.py    ← Parse file, chunk, embed, lưu DB
├── rag.py              ← Vector search, filter by category
├── docs_api.py         ← FastAPI router: /docs/upload, /docs/list, /docs/delete
└── embeddings.py       ← Wrapper: local model hoặc OpenAI/Anthropic embed API
```

### Thay đổi file hiện có:
- `api.py` — thêm `user_role` vào `ChatRequest`, include `docs_api` router
- `bot.py` / `skills.py` — nhận `retrieved_context`, inject vào system prompt
- `database.py` — thêm 3 bảng mới
- `index.html` — thêm dropdown chọn category (optional filter)

---

## 7. Embedding strategy — chọn gì?

### Option A: Local (miễn phí, offline)
```
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- Hỗ trợ tiếng Việt tốt
- ~420MB model download 1 lần
- 384 dimensions
- ~0.01s/chunk trên CPU
```

### Option B: Anthropic / OpenAI Embed API
```
- Không cần cài model
- Có phí (~$0.0001/1K tokens)
- Cần internet
```

**Đề xuất cho MVP:** Option A (local MiniLM) → không tốn tiền, phù hợp tài liệu tiếng Việt.

---

## 8. Vector store — chọn gì?

| Option | Ưu | Nhược |
|---|---|---|
| **sqlite-vec** | Cùng 1 file DB, zero setup | Mới, ít docs |
| **ChromaDB** | Mature, Python native, simple | Thêm service |
| **FAISS** | Rất nhanh | Không filter metadata dễ |
| **Qdrant** | Production-ready | Cần Docker |

**Đề xuất cho MVP:** **ChromaDB** — cài bằng pip, không cần Docker, hỗ trợ `where` filter theo metadata (category).

```python
# Ví dụ query với filter
collection.query(
    query_embeddings=[query_vec],
    n_results=5,
    where={"category_id": {"$in": allowed_categories}}
)
```

---

## 9. Frontend — UI đề xuất

### Tab / Dropdown chọn ngữ cảnh:
```
[ 💬 Trò chuyện chung ]  [ 📖 Hỏi tài liệu ▼ ]
                                  ├ Hướng dẫn khách hàng
                                  ├ FAQ Sản phẩm
                                  └ (nếu staff) Nội quy nội bộ
```

- Khi chọn "Hỏi tài liệu" → gửi `category_hint` trong request
- Bot sẽ hint: *"Tôi sẽ trả lời dựa trên [Hướng dẫn khách hàng]"*
- Nếu không tìm thấy chunk liên quan → bot nói: *"Tôi không tìm thấy thông tin về vấn đề này trong tài liệu."*

---

## 10. Implementation plan

### Phase 1 — Nền tảng (MVP)
- [ ] `embeddings.py` — MiniLM local wrapper
- [ ] `database.py` — thêm 3 bảng, seed categories
- [ ] `doc_processor.py` — parse PDF/TXT, chunk 500 tokens, embed, lưu ChromaDB
- [ ] `rag.py` — query ChromaDB với category filter, return chunks
- [ ] `docs_api.py` — `POST /docs/upload`, `GET /docs/list`
- [ ] `api.py` — thêm `user_role`, inject RAG context vào bot call
- [ ] `bot.py` — nhận `retrieved_context`, thêm vào system prompt

### Phase 2 — UI
- [ ] `index.html` — dropdown chọn category
- [ ] Admin page upload tài liệu (hoặc dùng Swagger `/docs`)

### Phase 3 — Production
- [ ] Auth / JWT để xác thực user_role thật
- [ ] Chunk overlap (50 tokens) để không mất context biên chunk
- [ ] Re-ranking chunks (cross-encoder)
- [ ] Streaming response

---

## 11. Dependency cần cài thêm

```bash
pip install chromadb
pip install sentence-transformers
pip install pypdf          # đọc PDF
pip install python-docx    # đọc DOCX
pip install tiktoken       # đếm token để chunk chính xác
```

---

## 12. Câu hỏi cần quyết định trước khi build

1. **Embedding:** Local MiniLM hay gọi API?
2. **user_role lưu ở đâu?** localStorage (tin trust frontend) hay DB users table?
3. **Ai upload tài liệu?** Chỉ admin qua Swagger, hay cần UI upload riêng?
4. **Chunk size:** 300–500 tokens? (ngắn = chính xác hơn, dài = context đủ)
5. **Khi không có doc liên quan:** bot fallback sang general knowledge hay nói "không biết"?
