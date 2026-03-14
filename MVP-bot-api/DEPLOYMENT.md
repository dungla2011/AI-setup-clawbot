# Deployment Guide - Bot MVP

Guide đầy đủ về cấu hình và deploy Bot MVP trên các môi trường khác nhau.

## 📋 Tải nhanh

| Môi trường | API Port | Web Port | Config |
|-----------|----------|----------|--------|
| 💻 Local  | 8000 | 8080 | `.env.example` |
| 🐳 Docker | 8000 | 8080 | `docker-compose.yml` |
| 🌐 Server | 8000 | 8080 | Custom .env |
| 🔒 HTTPS  | 8000 | 8080 | Nginx reverse proxy |

---

## 1️⃣ Local Development

Cấu hình cho máy tính cá nhân.

### Setup

```bash
# Tạo venv
python -m venv venv
source venv/bin/activate  # Unix/Mac
# hoặc venv\Scripts\activate  # Windows

# Cài dependencies
pip install -r requirements.txt

# Tạo .env
cp .env.example .env
```

### Edit .env

```env
API_HOST=127.0.0.1
API_PORT=8000
API_URL=http://localhost:8000

WEB_HOST=127.0.0.1
WEB_PORT=8080
WEB_URL=http://localhost:8080

ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Chạy

**Terminal 1 - API:**
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

**Terminal 2 - Web:**
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

### Test

Mở browser: **http://localhost:8080/index.html**

---

## 2️⃣ Docker Deployment

Dùng Docker Compose để chạy cả stack.

### File docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - API_HOST=0.0.0.0
      - API_PORT=8000
      - WEB_HOST=0.0.0.0
      - WEB_PORT=8080
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    command: python api.py
    networks:
      - bot-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  web:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - WEB_HOST=0.0.0.0
      - WEB_PORT=8080
      - API_URL=http://api:8000
    command: python web_server.py
    depends_on:
      - api
    networks:
      - bot-network

networks:
  bot-network:
    driver: bridge
```

### Chạy

```bash
# Build và run
docker-compose up --build

# Hay chỉ run (nếu đã build)
docker-compose up

# Chạy ở background
docker-compose up -d

# Stop
docker-compose down
```

### Test

```bash
# Chat via API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# Health check
curl http://localhost:8000/health

# Web UI
# http://localhost:8080/index.html
```

---

## 3️⃣ VPS/Cloud Server Deployment

Setup Bot MVP trên VPS (AWS EC2, DigitalOcean, v.v.)

### Prerequisites

- Ubuntu 20.04+ hoặc Linux distro tương tự
- Docker đã cài
- Domain name (tuỳ chọn)

### 1. SSH vào server

```bash
ssh user@your-server-ip
```

### 2. Clone repo

```bash
cd /opt
git clone https://github.com/your-repo/bot-mvp.git
cd bot-mvp
```

### 3. Tạo .env cho server

```bash
cat > .env << EOF
API_HOST=0.0.0.0
API_PORT=8000
API_URL=http://your-server-ip:8000

WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_URL=http://your-server-ip:8080

ANTHROPIC_API_KEY=sk-ant-your-key-here
TELEGRAM_BOT_TOKEN=your-token-here
EOF
```

### 4. Start Docker Compose

```bash
docker-compose up -d
```

### 5. Kiểm tra

```bash
# Logs
docker-compose logs -f

# Health
curl http://your-server-ip:8000/health

# Web UI
# Open http://your-server-ip:8080/index.html in browser
```

### Firewall Config (UFW)

```bash
sudo ufw allow 8000/tcp  # API
sudo ufw allow 8080/tcp  # Web
sudo ufw enable
```

---

## 4️⃣ HTTPS + Nginx Setup (Production)

Cấu hình SSL certificate và reverse proxy.

### Prerequisites

- Domain name (e.g., api.example.com)
- SSL certificate từ Let's Encrypt
- Nginx installed

### 1. Cài Nginx + Let's Encrypt

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --nginx -d api.example.com -d web.example.com
```

### 2. Cấu hình Nginx

**File: `/etc/nginx/sites-available/bot-mvp`**

```nginx
# API reverse proxy
upstream api_backend {
    server 127.0.0.1:8000;
}

# Web reverse proxy
upstream web_backend {
    server 127.0.0.1:8080;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.example.com web.example.com;
    return 301 https://$server_name$request_uri;
}

# API HTTPS
server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;

    client_max_body_size 20M;

    location / {
        proxy_pass http://api_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Web HTTPS
server {
    listen 443 ssl http2;
    server_name web.example.com;

    ssl_certificate /etc/letsencrypt/live/web.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/web.example.com/privkey.pem;

    location / {
        proxy_pass http://web_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Enable Nginx config

```bash
sudo ln -s /etc/nginx/sites-available/bot-mvp /etc/nginx/sites-enabled/
sudo nginx -t  # Test config
sudo systemctl restart nginx
```

### 4. Update .env

```env
API_HOST=0.0.0.0
API_PORT=8000
API_URL=https://api.example.com

WEB_HOST=0.0.0.0
WEB_PORT=8080
WEB_URL=https://web.example.com

ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 5. Restart services

```bash
docker-compose restart
```

### Test HTTPS

```bash
# API
curl https://api.example.com/health

# Web UI
# Open https://web.example.com in browser
```

### Auto-renew SSL

```bash
# Test renewal
sudo certbot renew --dry-run

# Cron job (automatic)
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## 5️⃣ Advanced Configuration

### Environment Variables Reference

| Variable | Default | Mô tả |
|----------|---------|-------|
| `API_HOST` | `0.0.0.0` | API server bind address |
| `API_PORT` | `8000` | API server port |
| `API_URL` | `http://localhost:8000` | API public URL (for web UI) |
| `WEB_HOST` | `0.0.0.0` | Web server bind address |
| `WEB_PORT` | `8080` | Web server port |
| `WEB_URL` | `http://localhost:8080` | Web public URL |
| `ANTHROPIC_API_KEY` | - | Claude API key (required) |
| `TELEGRAM_BOT_TOKEN` | - | Telegram bot token (optional) |

### Multi-Instance Deployment

Chạy multiple API instances phía sau load balancer:

```yaml
version: '3.8'

services:
  api-1:
    build: .
    ports: ["8001:8000"]
    environment:
      - API_PORT=8000
    command: python api.py

  api-2:
    build: .
    ports: ["8002:8000"]
    environment:
      - API_PORT=8000
    command: python api.py

  api-3:
    build: .
    ports: ["8003:8000"]
    environment:
      - API_PORT=8000
    command: python api.py

  nginx:
    image: nginx:latest
    ports: ["80:80"]
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    depends_on:
      - api-1
      - api-2
      - api-3

  web:
    build: .
    ports: ["8080:8080"]
    environment:
      - WEB_PORT=8080
      - API_URL=http://nginx
    command: python web_server.py
```

**File: `nginx-lb.conf`**

```nginx
upstream api_backend {
    server api-1:8000;
    server api-2:8000;
    server api-3:8000;
}

server {
    listen 80;
    location / {
        proxy_pass http://api_backend;
    }
}
```

### Database Integration (PostgreSQL)

Thay thế in-memory storage bằng database:

```python
# api.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot.db")

if DATABASE_URL.startswith("postgresql"):
    # Use PostgreSQL
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # Use SQLite
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Use SessionLocal() to get DB connection
```

**docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=bot_db
      - POSTGRES_USER=bot_user
      - POSTGRES_PASSWORD=secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  api:
    # ... other config
    environment:
      - DATABASE_URL=postgresql://bot_user:secure_password@postgres:5432/bot_db
    depends_on:
      - postgres

volumes:
  postgres_data:
```

---

## 🔍 Troubleshooting

### Port already in use

```bash
# Linux/Mac: Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Windows: 
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Docker not starting

```bash
# Check logs
docker-compose logs

# Rebuild
docker-compose down
docker-compose up --build

# Check disk space
docker system df
```

### API not responding

```bash
# Check if service is running
docker-compose ps

# Inspect logs
docker-compose logs api

# Test locally
curl http://localhost:8000/health
```

### CORS errors

- Ensure `web_server.py` has CORS headers
- Check `API_URL` is correct in `.env`
- Browser console should show exact error

### SSL certificate issues

```bash
# Check certificate
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal

# Debug
sudo certbot renew --dry-run -v
```

---

## 📊 Monitoring

### Health Check Endpoint

```bash
curl -X GET http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Logs

**Docker:**
```bash
docker-compose logs -f api
docker-compose logs -f web
```

**Direct:**
```bash
tail -f /var/log/bot-api.log
tail -f /var/log/bot-web.log
```

### Monitoring Stack (Optional)

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports: ["3000:3000"]
    depends_on:
      - prometheus
```

---

## ✅ Pre-Launch Checklist

- [ ] ANTHROPIC_API_KEY đã set
- [ ] Database (nếu dùng) đã cài
- [ ] SSL certificate đã cấu hình (nếu HTTPS)
- [ ] Firewall rules đã mở (port 8000, 8080)
- [ ] Health check endpoint trả về 200 OK
- [ ] Web UI tải được
- [ ] Chat endpoint hoạt động
- [ ] Load test hoàn thành
- [ ] Monitoring/logging setup xong
- [ ] Backup plan sẵn sàng

---

## 📞 Support

Nếu cần giúp:
1. Check logs: `docker-compose logs -f`
2. Test health: `curl http://localhost:8000/health`
3. Review .env file
4. Check firewall/network config
