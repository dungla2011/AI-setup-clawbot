#!/usr/bin/env python3
"""
Start all services: API server + Web server + Telegram bot
"""
import subprocess
import sys
import time
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

print("\n" + "="*60)
print("🚀 Starting Bot MVP Services")
print("="*60)

# Start API server
print("\n1️⃣  Starting API Server on http://localhost:8100")
api_proc = subprocess.Popen(
    [sys.executable, "api.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)
time.sleep(2)

# Start Web server
print("2️⃣  Starting Web Server on http://localhost:8080")
web_proc = subprocess.Popen(
    [sys.executable, "web_server.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)
time.sleep(2)

print("\n3️⃣  Starting Telegram Bot")
telegram_proc = subprocess.Popen(
    [sys.executable, "telegram_bot.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

print("\n" + "="*60)
print("✅ All services started!")
print("="*60)
print("\n📍 URLs:")
print("   🌐 Web UI:  http://localhost:8080/index.html")
print("   📊 Stats:   http://localhost:8080/stats.html")
print("   🤖 API:     http://localhost:8100")
print("   📱 Telegram: @YourBotName (on Telegram)")
print("\n💡 Press Ctrl+C to stop all services\n")

try:
    # Wait for all processes
    api_proc.wait()
    web_proc.wait()
    telegram_proc.wait()
except KeyboardInterrupt:
    print("\n\n⛔ Stopping all services...")
    api_proc.terminate()
    web_proc.terminate()
    telegram_proc.terminate()
    time.sleep(1)
    api_proc.kill()
    web_proc.kill()
    telegram_proc.kill()
    print("✅ All services stopped")
    sys.exit(0)
