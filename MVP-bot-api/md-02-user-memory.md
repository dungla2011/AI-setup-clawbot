# User Memory — Thiết kế & Chuẩn bị Code

## Mục tiêu

Bot "nhớ" user qua nhiều conversation:
- Biết user là ai, làm gì, thói quen hỏi gì
- Không hỏi lại những gì đã biết
- Trả lời có context cá nhân hóa hơn

---

## Kiến trúc tổng quan

```
[Conversation kết thúc / đủ N turns]
            ↓
   memory_summarizer()
   Input:  old_memory (str, ~500 tokens)
         + new_conversation (list of {role, content})
            ↓
   Claude: merge & extract → new_memory (str, ~500 tokens)
            ↓
   Lưu vào DB: user_memory table
            ↓
[Conversation mới bắt đầu]
            ↓
   Load user_memory từ DB
            ↓
   Inject vào system prompt:
   "Thông tin về người dùng này: {memory}"
```

---

## DB Schema

### Bảng mới: `user_memory`

```sql
CREATE TABLE user_memory (
    user_id     TEXT PRIMARY KEY,   -- phone/telegram_id/session_id
    memory      TEXT NOT NULL,      -- blob text ~500 tokens
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Bảng mới: `user_facts` (structured, optional — Phase 2)

```sql
CREATE TABLE user_facts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     TEXT NOT NULL,
    key         TEXT NOT NULL,      -- vd: "sales_channel", "business_type"
    value       TEXT NOT NULL,      -- vd: "TikTok", "quần áo nữ"
    confidence  REAL DEFAULT 1.0,   -- 0.0 → 1.0
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, key)
);
```

> Phase 1 chỉ cần `user_memory` (text blob). `user_facts` thêm sau nếu cần query structured.

---

## Memory Summarizer Prompt

```python
MEMORY_SUMMARIZER_PROMPT = """
Bạn là hệ thống quản lý bộ nhớ dài hạn cho AI assistant.

Nhiệm vụ: Đọc [Bộ nhớ cũ] và [Conversation mới], 
tạo ra [Bộ nhớ mới] đã được merge và cập nhật.

Quy tắc:
- Giữ tối đa ~400 từ
- Ưu tiên: thông tin kinh doanh, thói quen hỏi, sở thích giao tiếp
- Xóa thông tin lỗi thời nếu có update mới
- Viết dạng bullet points ngắn gọn, tiếng Việt

Format output (chỉ trả về phần này, không giải thích):
## Thông tin cơ bản
- ...

## Nghiệp vụ / Business context  
- ...

## Thói quen & sở thích
- ...

## Ghi chú khác
- ...
"""
```

---

## Flow chi tiết

### Trigger summarize

```python
# Trigger sau khi bot trả lời, nếu:
SUMMARIZE_TRIGGER = (
    turns_in_conversation >= 6   # đủ dài để có info
    or conversation_explicitly_ended  # user nói "bye", "tạm biệt"...
)
# Chạy async (không block response cho user)
```

### Hàm chính

```python
async def update_user_memory(user_id: str, conversation: list[dict]):
    """
    conversation = [
        {"role": "user",      "content": "..."},
        {"role": "assistant", "content": "..."},
        ...
    ]
    """
    # 1. Load memory cũ
    old_memory = db.get_user_memory(user_id) or ""

    # 2. Format conversation thành text
    conv_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" 
        for m in conversation
    )

    # 3. Gọi Claude summarize
    new_memory = await claude.summarize_memory(
        system=MEMORY_SUMMARIZER_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"## Bộ nhớ cũ\n{old_memory}\n\n"
                f"## Conversation mới\n{conv_text}"
            )
        }]
    )

    # 4. Lưu DB
    db.upsert_user_memory(user_id, new_memory)
```

### Inject vào system prompt

```python
def build_system_prompt(user_id: str) -> str:
    memory = db.get_user_memory(user_id)
    
    base_prompt = "Bạn là bot bán hàng thông minh..."
    
    if memory:
        return base_prompt + f"\n\n---\n## Thông tin người dùng\n{memory}"
    
    return base_prompt
```

---

## Token estimate

| Thành phần | Tokens |
|---|---|
| old_memory | ~500 |
| new_conversation (10 turns) | ~1,500 |
| MEMORY_SUMMARIZER_PROMPT | ~200 |
| **Total input** | **~2,200** |
| Output (new_memory) | ~500 |
| **Cost (Claude Haiku)** | **~$0.001/lần** |

Nếu mỗi user chat 3 lần/ngày → **$0.003/user/ngày** — không đáng kể.

---

## File cần tạo / sửa

```
MVP-bot-api/
├── database.py          → THÊM: get_user_memory(), upsert_user_memory()
├── memory.py            → TẠO MỚI: update_user_memory(), MEMORY_SUMMARIZER_PROMPT
├── main.py (FastAPI)    → SỬA: build_system_prompt() inject memory
│                              SỬA: sau /chat → trigger update_user_memory async
└── models.py (nếu có)  → THÊM: UserMemory schema
```

---

## Thứ tự build (Phase 1)

- [x] 1. Thêm bảng `user_memory` vào DB init (`database.py`)
- [x] 2. Viết `database.py`: `UserMemoryDB.get_memory()`, `UserMemoryDB.upsert_memory()`
- [x] 3. Tạo `memory.py`: prompt + `update_user_memory_async()` + `should_summarize()`
- [x] 4. Sửa `bot.py`: `build_system_prompt(user_memory)` inject memory khi chat
- [x] 5. Sửa `api.py`: nhận `user_id` từ request, load memory, trigger async update sau response
- [x] 6. Sửa `index.html`: tạo persistent `userId` trong localStorage, gửi kèm mỗi request
- [ ] 7. Test: chat 12+ messages → kiểm tra memory được tạo → chat session mới → bot nhớ

---

## Câu hỏi đã xác định

- `user_id`: UUID tự tạo ở frontend, lưu `localStorage['botUserId']`, gửi kèm mỗi `/chat` request
- `database.py`: SQLite (`bot_data.db`)
- Model summarize: `claude-3-haiku-20240307` (override bằng env `MEMORY_MODEL`), trigger mỗi 6 turns (12 messages)
