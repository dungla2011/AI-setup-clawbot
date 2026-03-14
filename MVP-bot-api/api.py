"""
FastAPI server để expose bot MVP thành API
"""
import sys
# Fix UTF-8 encoding on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
import os
from pathlib import Path
from dotenv import load_dotenv

# Debug: Print api.py initialization
print("="*60)
print("🔍 DEBUG - api.py initialization")
print(f"📁 Current working directory: {os.getcwd()}")
print(f"📄 api.py location: {Path(__file__).parent}")

# Load environment variables FIRST before importing bot
env_path = Path(__file__).parent / '.env'
print(f"🔧 Loading .env from: {env_path}")
print(f"✓ .env exists: {env_path.exists()}")
load_dotenv(dotenv_path=env_path, override=True)

api_key_check = os.getenv("ANTHROPIC_API_KEY")
print(f"🔑 API Key in api.py: {api_key_check[:30] if api_key_check else 'None'}...{api_key_check[-10:] if api_key_check and len(api_key_check) > 40 else ''}")
print("="*60)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
from bot import chat_with_claude
from database import UsageStatsDB, ConversationDB, init_database

app = FastAPI(title="Bot MVP API", version="1.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request logging middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        print(f"\n📨 [API] {request.method} {request.url.path}")
        response = await call_next(request)
        print(f"   ↳ Status: {response.status_code}")
        return response

app.add_middleware(LoggingMiddleware)

# Store conversations in memory (in production use database)
conversations = {}

# Models
class Message(BaseModel):
    content: str

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    user_message: str
    bot_response: str
    timestamp: str

# Routes
@app.get("/health")
def health_check():
    """Health check endpoint"""
    print("\n🔍 [API] GET /health called")
    print("   ✅ API is alive\n")
    return {"status": "ok"}

@app.get("/stats")
def get_stats():
    """Get usage statistics and cost"""
    return UsageStatsDB.get_stats()

@app.delete("/stats")
def reset_stats():
    """Reset usage statistics"""
    UsageStatsDB.reset_stats()
    return {"status": "reset", "message": "Statistics cleared"}

@app.post("/chat")
def chat(request: ChatRequest):
    """
    Chat with bot via API
    
    - If conversation_id is provided, continue existing conversation
    - Otherwise create new conversation
    """
    print(f"\n🔍 [API] POST /chat called")
    print(f"   Message: {request.message[:50]}...")
    print(f"   Conv ID: {request.conversation_id}")
    
    try:
        # Get or create conversation
        conv_id = request.conversation_id or str(uuid.uuid4())
        history = conversations.get(conv_id, None)
        
        # Create conversation in DB if new
        if conv_id not in conversations:
            print(f"   ✅ Creating new conversation: {conv_id}")
            ConversationDB.create_conversation(conv_id, platform="web")
        
        # Save user message to DB
        ConversationDB.add_message(conv_id, role="user", content=request.message)
        
        # Get bot response
        bot_response, history = chat_with_claude(request.message, history, conv_id)
        
        # Save bot response to DB
        ConversationDB.add_message(conv_id, role="assistant", content=bot_response)
        
        # Store conversation in memory (for backward compatibility)
        conversations[conv_id] = history
        
        from datetime import datetime
        print(f"   ✅ Chat response saved\n")
        return ChatResponse(
            conversation_id=conv_id,
            user_message=request.message,
            bot_response=bot_response,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/latest")
def get_latest_conversation():
    """Get the most recent conversation from database"""
    print("\n🔍 [API] GET /conversations/latest called")
    conversations_list = ConversationDB.get_all_conversations(limit=1)
    print(f"   Found {len(conversations_list)} conversation(s)")
    
    if not conversations_list:
        print("   ❌ No conversations found!")
        raise HTTPException(status_code=404, detail="No conversations found")
    
    latest_conv = conversations_list[0]
    conversation_id = latest_conv["conversation_id"]
    print(f"   ✅ Latest conversation: {conversation_id}")
    
    # Get full history
    history = ConversationDB.get_conversation_history(conversation_id, limit=100)
    print(f"   📝 History has {len(history)} message(s)")
    
    # Convert to format expected by frontend
    formatted_history = [
        {"role": msg["role"], "content": msg["content"], "timestamp": msg["created_at"]}
        for msg in history
    ]
    
    print(f"   ✅ Returning conversation {conversation_id} with {len(formatted_history)} messages\n")
    return {"conversation_id": conversation_id, "history": formatted_history}

@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    """Get conversation history from database"""
    history = ConversationDB.get_conversation_history(conversation_id, limit=100)
    
    if not history:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Convert to format expected by frontend
    formatted_history = [
        {"role": msg["role"], "content": msg["content"], "timestamp": msg["created_at"]}
        for msg in history
    ]
    
    return {"conversation_id": conversation_id, "history": formatted_history}

@app.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    if conversation_id in conversations:
        del conversations[conversation_id]
        return {"message": "Conversation deleted"}
    raise HTTPException(status_code=404, detail="Conversation not found")

@app.get("/")
def root():
    """API Info"""
    return {
        "name": "Bot MVP API",
        "version": "1.0",
        "endpoints": {
            "chat": "POST /chat",
            "get_conversation": "GET /conversations/{conversation_id}",
            "delete_conversation": "DELETE /conversations/{conversation_id}",
            "health": "GET /health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get config from .env
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8000"))
    api_url = os.getenv("API_URL", "http://localhost:8000")
    
    print(f"\n{'='*50}")
    print(f"🚀 Bot MVP API Server")
    print(f"{'='*50}")
    print(f"📍 API URL: {api_url}")
    print(f"🔧 Host: {api_host}")
    print(f"🔌 Port: {api_port}")
    print(f"\n📚 Docs: http://localhost:{api_port}/docs")
    print(f"{'='*50}\n")
    
    uvicorn.run(app, host=api_host, port=api_port)
