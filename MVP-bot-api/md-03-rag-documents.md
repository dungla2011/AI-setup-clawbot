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

---

## 13. Phân quyền đầy đủ — User / Role / Category (đã implement)

> Thay thế hoàn toàn phần 3.3 (hardcoded dict). Mọi thứ đều đọc từ DB.

### 13.1 Ba bảng mới trong `database.py`

```sql
-- Bảng roles: danh sách vai trò, tên lấy từ đây (không hardcode)
CREATE TABLE IF NOT EXISTS roles (
    id          TEXT PRIMARY KEY,   -- "customer", "staff", "admin"
    name        TEXT NOT NULL,      -- "Khách hàng", "Nhân viên", "Quản trị"
    description TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- Bảng users: mỗi người dùng có 1 role và 1 UUID cố định
CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,          -- UUID, dùng làm user_id qua API
    username     TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    role_id      TEXT NOT NULL REFERENCES roles(id),
    is_active    INTEGER DEFAULT 1,
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_users_role ON users(role_id);

-- Bảng role_category_access: ma trận role ↔ category, thay cho hardcoded dict
CREATE TABLE IF NOT EXISTS role_category_access (
    role_id     TEXT NOT NULL REFERENCES roles(id),
    category_id TEXT NOT NULL REFERENCES doc_categories(id),
    PRIMARY KEY (role_id, category_id)
);
```

**Seed mặc định khi DB mới:**
- Roles: `customer` / `staff` / `admin`
- Users: `customer01` / `staff01` / `admin01` (1 user/role)
- `customer` → `customer_guide`, `product_faq`
- `staff`, `admin` → tất cả 6 categories

### 13.2 `rag.py` — `get_allowed_categories()` đọc từ DB

Trước đây là hardcoded `CATEGORY_ACCESS` dict. Nay:

```python
def get_allowed_categories(user_role: str) -> Optional[list[str]]:
    rows = SELECT category_id FROM role_category_access WHERE role_id = ?

    if not rows:
        return []    # role không có quyền gì → chặn hoàn toàn

    allowed = [r["category_id"] for r in rows]

    total_cats = SELECT COUNT(*) FROM doc_categories
    if len(allowed) >= total_cats:
        return None  # None = unrestricted (all categories — không filter)

    return allowed   # list cụ thể → WHERE category_id IN (...)
```

→ Thêm category mới, thay đổi quyền → chỉ cần sửa DB, không đụng code.

### 13.3 `api.py` — Resolve role từ DB, không tin frontend

```python
# Bước 1: Lấy role từ DB nếu user_id khớp users.id
db_user = get_user_by_id(request.user_id)   # helper mới trong database.py
effective_role = db_user["role_id"] if db_user else request.user_role or "customer"

# Bước 2: Kiểm tra role có bị giới hạn category không
allowed = get_allowed_categories(effective_role)
restricted_access = (allowed is not None)   # True nếu có whitelist cụ thể

# Bước 3: RAG dùng effective_role (đã được DB verify)
chunks = rag_retrieve(message, effective_role, ...)
```

**Tại sao quan trọng:** Frontend có thể gửi `user_role: "admin"` bừa — nếu `user_id` khớp 1 user trong `users` table thì dùng `role_id` của row đó, bỏ qua field frontend gửi lên.

### 13.4 `bot.py` — `restricted_access` flag ngăn Claude trả tự do

Vấn đề gốc: RAG trả 0 chunk → `retrieved_context = ""` → không có instruction nào → Claude dùng general knowledge trả lời thoải mái.

Giải pháp: thêm param `restricted_access: bool` vào `build_system_prompt()`:

```python
def build_system_prompt(user_memory, retrieved_context,
                        user_role, restricted_access=False):
    ...
    if retrieved_context:
        # Có doc → "CHỈ dựa trên tài liệu"
        base += "=== Tài liệu tham khảo ===\n" + retrieved_context
        base += "\nHãy trả lời CHỈ dựa trên tài liệu tham khảo ở trên."

    elif restricted_access:
        # Không có doc PHÙ HỢP với role này → từ chối, không dùng kiến thức chung
        base += (
            "Không có tài liệu nào trong phạm vi quyền hạn của vai trò này "
            "có liên quan đến câu hỏi này. "
            "TUYỆT ĐỐI KHÔNG trả lời dựa trên kiến thức chung, lịch sử trò chuyện, "
            "hay bất kỳ nguồn nào khác. "
            "Hãy trả lời: 'Xin lỗi, tôi không có thông tin này trong tài liệu dành cho [role].'"
        )
    # else: unrestricted role + 0 chunk → Claude tự trả lời bình thường
```

**Ba trường hợp:**

| retrieved_context | restricted_access | Hành vi Claude |
|---|---|---|
| Có chunks | bất kỳ | Trả lời CHỈ dựa trên tài liệu |
| Không có | `True` (whitelist) | Từ chối, báo "không có trong tài liệu dành cho \[role\]" |
| Không có | `False` (unrestricted) | Trả lời tự do từ general knowledge |

### 13.5 `role_label` lấy từ DB (`roles.name`)

```python
# database.py — helper mới
def get_role_label(role_id: str) -> str:
    row = SELECT name FROM roles WHERE id = ?
    return row["name"] if row else role_id

# bot.py dùng
role_label = get_role_label(user_role)   # "Khách hàng", "Nhân viên"...
# Không còn _ROLE_LABELS dict hardcode
```

### 13.6 Frontend — `user_id` dùng `users.id` thật từ nav dropdown

```javascript
// nav.js: user dropdown top-right
// Khi chọn user → lưu users.id vào localStorage
window.getCurrentUser = () => _currentUser      // { id, username, role_id, ... }
window.getCurrentUserRole = () => _currentUser?.role_id || "customer"

// index.html: dùng users.id khi có (thay vì browser-generated UUID)
function getEffectiveUserId() {
    const navUser = window.getCurrentUser && window.getCurrentUser();
    return navUser ? navUser.id : browserUserId;   // fallback: localStorage UUID
}

// Gửi lên API:
{ user_id: getEffectiveUserId(), user_role: getCurrentUserRole() }
// → api.py tìm user_id trong users table → lấy role_id từ DB
```

`roleSelect` trong chat UI: **disabled** (readonly), tự động sync khi `navUserChanged` event fire.

### 13.7 `settings.html` — UI quản lý Users / Roles / Permissions

Trang mới với 3 tab Bootstrap:

| Tab | Nội dung |
|---|---|
| **Users** | Bảng list users + Add/Edit/Delete (modal) |
| **Roles** | Bảng list roles + Add/Edit/Delete |
| **Permissions** | Matrix checkbox: rows=Roles, cols=Categories → PUT /roles/{id}/categories |

**API endpoints mới trong `api.py`:**

```
GET    /users
POST   /users                    { username, display_name, role_id }
PUT    /users/{id}               { display_name?, role_id?, is_active? }
DELETE /users/{id}

GET    /roles
POST   /roles                    { id, name, description }
PUT    /roles/{id}               { name?, description? }
DELETE /roles/{id}               (lỗi nếu còn user dùng role này)

GET    /roles/{id}/categories    → list category_id
PUT    /roles/{id}/categories    { category_ids: [...] }  → replace toàn bộ

GET    /categories               → list doc_categories
```

### 13.8 Luồng đầy đủ khi chat (sau khi triển khai)

```
1. User chọn "customer01" trên nav dropdown
   → getCurrentUser() = { id: "0460b8eb-...", role_id: "customer" }

2. POST /chat { user_id: "0460b8eb-...", user_role: "customer", message: "..." }

3. api.py:
   get_user_by_id("0460b8eb-...") → { role_id: "customer" }  ← trust DB
   effective_role = "customer"

   get_allowed_categories("customer")
   → SELECT ... FROM role_category_access WHERE role_id="customer"
   → ["customer_guide", "product_faq"]
   → restricted_access = True  (whitelist != None)

   rag_retrieve(query, "customer") → 0 chunks (không có doc phù hợp)

4. build_system_prompt(retrieved_context="", restricted_access=True)
   → inject "TUYỆT ĐỐI KHÔNG trả lời từ kiến thức chung..."

5. Claude trả lời:
   "Xin lỗi, tôi không có thông tin này trong tài liệu dành cho Khách hàng."
```

