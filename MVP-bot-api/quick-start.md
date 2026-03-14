# Quick Start - Bot MVP

## ⚡ 3 bước để chạy trong 5 phút

### 1️⃣ Setup

```bash
# Clone hoặc tải repo
cd MVP-bot-api

# Tạo venv
python -m venv venv
source venv/bin/activate  # Unix/Mac
# hoặc
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Tạo .env file
cp .env.example .env
# Sửa .env: ANTHROPIC_API_KEY=sk-ant-...
```

### Cấu hình port trong .env (tuỳ chọn)

Edit `.env` file:

```env
# API Server (default 8000)
API_PORT=8000
API_URL=http://localhost:8000

# Web Server (default 8080)  
WEB_PORT=8080
WEB_URL=http://localhost:8080
```

**Giải thích:**
- `API_PORT` - API server chạy trên port này
- `WEB_PORT` - Web server chạy trên port này
- `API_URL` - URL để Web UI gọi API (auto-detect nếu cùng localhost)

### 2️⃣ Chạy 2 server (terminal khác nhau)

**Terminal 1 - API Server:**
```bash
python api.py
```
Output: 
```
🚀 Bot MVP API Server
📍 API URL: http://localhost:8000
🔌 Port: 8000
📚 Docs: http://localhost:8000/docs
```

**Terminal 2 - Web Server:**
```bash
python web_server.py
```
Output:
```
💻 Bot MVP Web Server
🌐 Web URL: http://localhost:8080/index.html
🔌 Port: 8080
🤖 API URL: http://localhost:8000
```

### 3️⃣ Mở Web UI

Truy cập: **http://localhost:8080/index.html**

✅ Xong! 🎉

---

## 🧪 Test API

**CURL:**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hôm nay bán được bao nhiêu?"}'
```

**Python:**
```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={"message": "Xem đơn hàng"}
)
print(response.json())
```

**JavaScript (fetch):**
```javascript
fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({message: "Đơn hàng mới nhất"})
})
.then(r => r.json())
.then(data => console.log(data.bot_response))
```

---

## 🎯 Thử lệnh

Bot có 3 tools:
- `get_orders` - Liệt kê đơn hàng
- `check_status` - Kiểm tra trạng thái
- `get_revenue` - Xem doanh thu

Thử hỏi:
- ✅ "Show me recent orders"
- ✅ "What's the status of ORD001?"
- ✅ "Tell me today's revenue"
- ✅ "Xem doanh thu tháng này"
- ✅ "Đơn hàng của tôi ở đâu rồi?"

---

## 📁 File structure

```
MVP-bot-api/
├── bot.py              ← Claude + tools logic
├── api.py              ← FastAPI server
├── index.html          ← Web UI (mở direct)
├── requirements.txt    ← Dependencies
├── Dockerfile          ← Docker build
├── docker-compose.yml  ← Docker compose
├── .env.example        ← Config template
├── README.md           ← Full docs
└── quick-start.md      ← This file
```

---

## 🚀 Deploy

### Docker
```bash
# Build image
docker build -t bot-mvp .

# Run container
docker run -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  bot-mvp
```

### VPS/Cloud
1. Clone repository
2. Setup venv
3. Run: `python api.py`
4. Setup nginx reverse proxy
5. Deploy Web UI

---

## ❓ FAQ

**Q: API không chạy?**
A: Check firewall, port 8000 bị dùng, hoặc API_KEY sai

**Q: Web UI không connect API?**
A: API phải cho phép CORS (done), và API phải chạy trên http://localhost:8000

**Q: Bot reply chậm?**
A: Claude API call tốn ~1-2s, bình thường

**Q: Muốn thêm tool mới?**
A: Edit `TOOLS` list trong `bot.py`, thêm function xử lý, done!

---

## 💡 Tiếp theo

1. Thêm database (PostgreSQL) để lưu conversation
2. Thêm authentication (JWT tokens)
3. Tích hợp Telegram bot
4. Thêm more tools (email, SMS, etc.)
5. Deploy production

**Tất cả có thể làm trong 1 ngày nữa!**

---

🎉 **Xong! Bạn có chatbot MVP đầy đủ với API + Web UI.**
