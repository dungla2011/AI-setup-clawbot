#!/bin/bash

# Script để chạy cả API + Web server cùng lúc

echo "🚀 Bot MVP - Full Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check venv
if [ ! -d "venv" ]; then
    echo "📦 Tạo virtual environment..."
    python -m venv venv
fi

# Activate venv
echo "✅ Activate venv..."
source venv/bin/activate || . venv/Scripts/activate

# Install dependencies
echo "📥 Install dependencies..."
pip install -q -r requirements.txt 2>/dev/null

# Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  Tạo .env file từ template..."
    cp .env.example .env
    echo "❌ CẢNH BÁO: Chỉnh sửa .env và thêm ANTHROPIC_API_KEY!"
    echo "Mở file .env, thay sk-ant-your-api-key-here bằng API key thực"
    read -p "Nhấn Enter khi đã sửa .env..."
fi

# Check API key
if grep -q "sk-ant-your-api-key-here" .env; then
    echo "❌ ERROR: Chưa cấu hình ANTHROPIC_API_KEY trong .env!"
    exit 1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Setup hoàn thành!"
echo ""
echo "Chạy 2 server trong 2 terminal khác nhau:"
echo ""
echo "📌 Terminal 1 (API Server):"
echo "   python api.py"
echo ""
echo "📌 Terminal 2 (Web Server):"
echo "   python web_server.py"
echo ""
echo "💻 Sau đó mở: http://localhost:8080/index.html"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
