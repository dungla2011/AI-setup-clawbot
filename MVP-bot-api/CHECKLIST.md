# CONFIGURATION CHECKLIST

Danh sách kiểm tra để đảm bảo Bot MVP chạy đúng.

## ✅ Pre-Start Checklist

### 1. Environment Setup
- [ ] Python 3.8+ đã cài (`python --version`)
- [ ] venv đã tạo và kích hoạt
- [ ] Dependencies đã cài (`pip list | grep anthropic`)
- [ ] `.env` file đã tạo từ `.env.example`
- [ ] `ANTHROPIC_API_KEY` đã set trong `.env`

### 2. File Configuration
- [ ] `.env` file tồn tại
- [ ] `bot.py` tồn tại
- [ ] `api.py` tồn tại  
- [ ] `web_server.py` tồn tại
- [ ] `index.html` tồn tại
- [ ] `requirements.txt` tồn tại

### 3. Port Configuration (trong .env)
```env
✓ API_HOST=0.0.0.0
✓ API_PORT=8000
✓ API_URL=http://localhost:8000
✓ WEB_HOST=0.0.0.0
✓ WEB_PORT=8080
✓ WEB_URL=http://localhost:8080
✓ ANTHROPIC_API_KEY=sk-ant-...
```

---

## 🔴 Troubleshooting Common Issues

### Issue 1: "ModuleNotFoundError: No module named 'anthropic'"

**Nguyên nhân:** Dependencies chưa được cài

**Cách sửa:**
```bash
# Kiểm tra venv có kích hoạt không
which python  # Should show venv path

# Cài lại dependencies
pip install -r requirements.txt

# Kiểm tra
python -c "import anthropic; print('OK')"
```

---

### Issue 2: "Port 8000 already in use"

**Nguyên nhân:** Có process khác đang dùng port

**Cách sửa:**

**Linux/Mac:**
```bash
# Tìm process
lsof -i :8000

# Kill process (nếu cần)
kill -9 <PID>

# Hoặc dùng port khác
# Edit .env
API_PORT=8001
```

**Windows:**
```cmd
netstat -ano | findstr :8000
taskkill /PID <PID> /F

REM Hoặc dùng port khác
API_PORT=8001
```

---

### Issue 3: "ANTHROPIC_API_KEY not found"

**Nguyên nhân:** API key không được set

**Cách sửa:**

```bash
# Kiểm tra .env
cat .env | grep ANTHROPIC

# Nếu không có, thêm vào .env
echo "ANTHROPIC_API_KEY=sk-ant-your-key" >> .env

# Kiểm tra Python có đọc được không
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv('ANTHROPIC_API_KEY'))"
```

---

### Issue 4: "Connect timeout: http://localhost:8000"

**Nguyên nhân:** API server không chạy

**Cách sửa:**

```bash
# Terminal 1: Kiểm tra API chạy không
python api.py

# Nếu có lỗi, xem chi tiết
python api.py --verbose

# Test API từ terminal khác
curl http://localhost:8000/health
```

---

### Issue 5: "Web UI blank / không load chat"

**Nguyên nhân:** Web server không chạy hoặc API không kết nối được

**Cách sửa:**

```bash
# 1. Kiểm tra web server chạy
python web_server.py

# 2. Kiểm tra API chạy
python api.py

# 3. Check browser console (F12)
# - Network tab: xem request đi đâu
# - Console tab: xem có error gì

# 4. Test API trực tiếp
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hi"}'
```

---

### Issue 6: "401 Unauthorized from Anthropic"

**Nguyên nhân:** API key sai hoặc hết hạn

**Cách sửa:**

```bash
# 1. Kiểm tra API key còn hiệu lực
# Visit: https://console.anthropic.com/account/keys

# 2. Generate key mới nếu cần
# Update .env
ANTHROPIC_API_KEY=sk-ant-new-key-here

# 3. Restart API server
# Kill current: Ctrl+C
# Start lại: python api.py
```

---

### Issue 7: Docker "build failed"

**Nguyên nhân:** Dockerfile có lỗi hoặc dependencies không cài được

**Cách sửa:**

```bash
# Xem chi tiết lỗi
docker-compose build --verbose

# Clear cache (nếu cần)
docker-compose down
docker system prune -a
docker-compose up --build

# Kiểm tra Dockerfile syntax
docker build --no-cache .
```

---

### Issue 8: "CORS error" từ browser

**Nguyên nhân:** Web UI không kết nối được API

**Cách sửa:**

```bash
# 1. Kiểm tra web_server.py có CORS headers
# Should have: response.headers["Access-Control-Allow-Origin"] = "*"

# 2. Kiểm tra .env có API_URL đúng
cat .env | grep API_URL

# 3. Browser console (F12)
# Xem exact error message

# 4. Test từ curl (không cần CORS)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

---

## 🧪 Verification Steps

### Step 1: Check Python & Installation
```bash
python --version
pip list | grep -E "anthropic|fastapi|dotenv"
```

Expected output:
```
Python 3.11.x
anthropic          0.7.x
fastapi            0.x.x
python-dotenv      1.0.x
```

### Step 2: Check .env Configuration
```bash
# Print .env (hide sensitive keys)
cat .env | grep -v "^#"
```

Expected output:
```
API_HOST=0.0.0.0
API_PORT=8000
API_URL=http://localhost:8000
WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_URL=http://localhost:8080
ANTHROPIC_API_KEY=sk-ant-...
```

### Step 3: Test API Server
```bash
# Start API
python api.py

# In another terminal, test
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "timestamp": "2024-01-15T10:30:00Z"}
```

### Step 4: Test Chat Endpoint
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "conversation_id": "test-1"}'
```

Expected response:
```json
{
  "response": "Hello! How can I help you?",
  "conversation_id": "test-1",
  "tools_used": []
}
```

### Step 5: Test Web Server
```bash
# Start web server (new terminal)
python web_server.py

# Visit in browser
# http://localhost:8080/index.html
```

Expected: Chatbox UI loads with styles

### Step 6: Test Full Flow
1. Start API: `python api.py`
2. Start Web: `python web_server.py`
3. Open: `http://localhost:8080/index.html`
4. Type message: "How many orders do I have?"
5. Expected: Bot responds with tool call result

---

## 📊 Performance Tuning

### Slow Response Time?

```bash
# 1. Check CPU/Memory
top  # Linux/Mac
tasklist | findstr python  # Windows

# 2. Check API logs
# Look for slow endpoints
python api.py  # Check output timing

# 3. Test API directly (no web layer)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# 4. If still slow, check Anthropic API
# Visit: https://status.anthropic.com
```

### High Memory Usage?

```python
# Edit api.py - limit conversation history
MAX_CONVERSATIONS = 100
MAX_HISTORY_PER_CONVERSATION = 50

# Or add cleanup
def cleanup_old_conversations():
    # Remove conversations older than 24 hours
```

---

## 🔒 Security Checklist

Before going to production:

- [ ] ANTHROPIC_API_KEY uses environment variable (never hardcode)
- [ ] .env file is in .gitignore
- [ ] API has rate limiting
- [ ] Web UI validates input
- [ ] HTTPS enabled (if public)
- [ ] CORS properly configured
- [ ] No sensitive data in logs
- [ ] Database credentials encrypted
- [ ] Auth tokens have expiration

---

## 📞 Quick Support Matrix

| Problem | Quick Fix | Deep Dive |
|---------|-----------|-----------|
| Port in use | Change port in .env | `lsof -i :8000` + `kill -9` |
| No API key | Set in .env | Check console.anthropic.com |
| CORS error | Check .env | Browser F12 Network tab |
| Slow response | Restart servers | Check Anthropic status |
| Docker build fail | `docker system prune` | Review Dockerfile logs |
| CSS not loading | Hard refresh (Cmd+Shift+R) | Check web_server paths |

---

## 🚀 Ready to Launch?

Run this one-liner to verify all systems:

```bash
echo "=== Checking Setup ===" && \
python --version && \
python -c "import anthropic; print('✓ anthropic')" && \
python -c "import fastapi; print('✓ fastapi')" && \
python -c "import dotenv; print('✓ dotenv')" && \
test -f .env && echo "✓ .env exists" && \
test -f bot.py && echo "✓ bot.py exists" && \
test -f api.py && echo "✓ api.py exists" && \
test -f index.html && echo "✓ index.html exists" && \
echo "✅ All checks passed!"
```

If all green, you're ready to: `python api.py` + `python web_server.py`
