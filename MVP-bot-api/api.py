"""
FastAPI server để expose bot MVP thành API
"""
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
from usage_tracker import tracker

app = FastAPI(title="Bot MVP API", version="1.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"status": "ok"}

@app.get("/stats")
def get_stats():
    """Get usage statistics and cost"""
    return tracker.get_stats()

@app.delete("/stats")
def reset_stats():
    """Reset usage statistics"""
    tracker.reset_stats()
    return {"status": "reset", "message": "Statistics cleared"}

@app.post("/chat")
def chat(request: ChatRequest):
    """
    Chat with bot via API
    
    - If conversation_id is provided, continue existing conversation
    - Otherwise create new conversation
    """
    try:
        # Get or create conversation
        conv_id = request.conversation_id or str(uuid.uuid4())
        history = conversations.get(conv_id, None)
        
        # Get bot response
        bot_response, history = chat_with_claude(request.message, history)
        
        # Store conversation
        conversations[conv_id] = history
        
        from datetime import datetime
        return ChatResponse(
            conversation_id=conv_id,
            user_message=request.message,
            bot_response=bot_response,
            timestamp=datetime.now().isoformat()
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    """Get conversation history"""
    if conversation_id not in conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return {"conversation_id": conversation_id, "history": conversations[conversation_id]}

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
