# Bot MVP - API + Web UI

Chatbot thông minh với Claude AI + Function Calling. Có thể gọi via API hoặc Web UI.

## Tính năng

- ✅ Claude 3.5 Sonnet với Function Calling
- ✅ 3 Skills: `get_orders`, `check_status`, `get_revenue`
- ✅ FastAPI server (REST API)
- ✅ Web UI đẹp tương tác realtime
- ✅ Conversation history
- ✅ CORS hỗ trợ

## Cấu trúc

```
MVP-bot-api/
├── bot.py          # Main bot logic (Claude + tools)
├── api.py          # FastAPI server
├── index.html      # Web UI
├── requirements.txt
└── README.md
```

## Installation

### 1. Tải dependencies
```bash
pip install -r requirements.txt
```

### 2. Tạo file .env
```bash
cp .env.example .env
```

Edit `.env` file:
```env
# API Server (port mặc định: 8000)
API_PORT=8000
API_URL=http://localhost:8000

# Web Server (port mặc định: 8080)
WEB_PORT=8080
WEB_URL=http://localhost:8080

# Bắt buộc: Key từ Anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Tuỳ chọn: Telegram bot token
TELEGRAM_BOT_TOKEN=your-token-here
```

**Giải thích cấu hình:**
- `API_PORT` - Port API chạy trên (FastAPI)
- `WEB_PORT` - Port web server chạy trên
- `API_URL` - URL công khai để web UI gọi API
- Tất cả đều **tự động** - không cần sửa code!

## Chạy

### Cách 1: Chạy đầy đủ (API + Web UI) ⭐ Khuyên dùng

**Terminal 1 - API Server:**
```bash
python api.py
```
Output: `🚀 Bot MVP API Server... Docs: http://localhost:8000/docs`

**Terminal 2 - Web Server (terminal khác):**
```bash
python web_server.py
```
Output: `💻 Bot MVP Web Server... http://localhost:8080/index.html`

Rồi mở browser: **http://localhost:8080/index.html**

### Cách 2: Chỉ API Server
```bash
python api.py
```
Server sẽ chạy trên `http://localhost:8000`

Docs: `http://localhost:8000/docs`

### Cách 3: Test nhanh (CLI)
```bash
python bot.py
```

## API Endpoints

### POST /chat
Chat với bot

**Request:**
```json
{
  "message": "Hôm nay bán được bao nhiêu?",
  "conversation_id": "optional-uuid" 
}
```

**Response:**
```json
{
  "conversation_id": "uuid",
  "user_message": "Hôm nay bán được bao nhiêu?",
  "bot_response": "Hôm nay bạn đã bán được 5,200,000 VNĐ!",
  "timestamp": "2026-03-13T10:30:00"
}
```

### GET /conversations/{conversation_id}
Lấy history của conversation

### DELETE /conversations/{conversation_id}
Xóa conversation

### GET /health
Health check

## Web UI

Mở file `index.html` trên trình duyệt (hoặc serve bằng nginx/python http.server)

```bash
# Python built-in server
python -m http.server 8080 --directory .
```

Sau đó truy cập `http://localhost:8080/index.html`

## Cấu hình Port - Cách hoạt động ⚙️

**Bot MVP** sử dụng hệ thống cấu hình thông minh:

### 🔴 Component 1: API Server (api.py)
- Đọc `API_PORT`, `API_URL` từ `.env`
- Chạy trên port được cấu hình
- In ra API docs khi khởi động

### 🟢 Component 2: Web Server (web_server.py)  
- Đọc `WEB_PORT`, `API_URL` từ `.env`
- Serve `index.html` + CORS
- In ra URL để truy cập

### 🔵 Component 3: Web UI (index.html)
- Tự động phát hiện hostname từ trình duyệt
- Gọi API tại: `http://{hostname}:{API_PORT}`
- Không cần hardcode port!

### Các kịch bản cấu hình

**Local Development:**
```env
API_PORT=8000
API_URL=http://localhost:8000
WEB_PORT=8080
```

**Production (Server riêng):**
```env
API_PORT=8000
API_URL=https://api.example.com
WEB_PORT=8080
```

**Docker (Container network):**
```env
API_PORT=8000
API_URL=http://api-service:8000
WEB_PORT=8080
```

## Test cURL

```bash
# Chat
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Xem đơn hàng mới nhất"}'

# Get health
curl http://localhost:8000/health
```

## Cấu hình Tools

Edit danh sách tools trong `bot.py`:
```python
TOOLS = [
    {
        "name": "ten_tool",
        "description": "Mô tả",
        "input_schema": {...}
    }
]
```

Rồi implement function xử lý:
```python
def process_tool_call(tool_name, tool_input):
    if tool_name == "ten_tool":
        return ten_tool_handler(tool_input)
```

## Production

Để deploy:
1. Use database thay vì memory storage
2. Add authentication
3. Use environment variables
4. Deploy API trên VPS/Cloud
5. Serve Web UI bằng nginx

Ví dụ production stack:
- Python + FastAPI
- PostgreSQL (lưu conversations)
- Nginx (reverse proxy)
- Docker (containerize)
- Environment variables (.env)

## Troubleshooting

**"403 Unauthorized" từ Anthropic:**
- Check API key đúng
- Check quota Anthropic account

**CORS error từ Web:**
- Chắc chắn API server chạy trên `localhost:8000`
- Browser chặn CORS → add `Allow-Origin: *` headers (done)

**Bot không gọi tool:**
- Check tool definition hợp lệ
- Thêm logging để debug
- Test bằng cURL trước
