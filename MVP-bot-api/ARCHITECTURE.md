# Architecture Overview - Bot MVP

Hướng dẫn chi tiết về cách các component của Bot MVP hoạt động và giao tiếp với nhau.

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                     Internet / Browser                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ HTTP Request
                         │ GET /index.html
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  Web Server (web_server.py)                Port: 8080            │
│  ✓ Serve static files (HTML/CSS/JS)                              │
│  ✓ CORS headers: Allow cross-origin                              │
│  ✓ Reads from .env: WEB_PORT, API_URL                           │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ index.html loads
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  Web UI (index.html)                                              │
│  ✓ Beautiful chatbox interface                                   │
│  ✓ Auto-detects API: http://{hostname}:8000                     │
│  ✓ Sends: {"message": "user input"}                             │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ POST /chat
                         │ (JSON payload)
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  API Server (api.py)                    Port: 8000               │
│  ✓ FastAPI framework                                             │
│  ✓ Reads from .env: API_PORT, API_HOST                          │
│  ✓ Endpoint: POST /chat                                         │
│  ✓ Manages: Conversation history                                │
│  ✓ Calls: bot.chat_with_claude()                               │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ chat_with_claude(message, history)
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  Bot Logic (bot.py)                                               │
│  ✓ Claude AI integration                                         │
│  ✓ Function calling loop                                        │
│  ✓ Tools:                                                       │
│    - get_orders() → fetch mock orders                           │
│    - check_status(order_id) → check status                      │
│    - get_revenue(period) → get revenue                          │
│  ✓ Handles tool execution                                       │
│  ✓ Formats response                                             │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ messages = [
                         │   {"role": "user", "content": "..."},
                         │   {"role": "assistant", "content": "..."}
                         │ ]
                         │ tools = [list of available tools]
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  Anthropic Claude API                                             │
│  ✓ Model: claude-3-5-sonnet-20241022                             │
│  ✓ Function calling: Returns tool_use objects                    │
│  ✓ Tool selection: Claude autonomously chooses tools             │
│  ✓ Response: Final assistant message                             │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ Response with tool results
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  API Response                                                     │
│  {                                                                │
│    "response": "You have 3 orders...",                          │
│    "tools_used": ["get_orders"],                                │
│    "conversation_id": "user-123"                                │
│  }                                                                │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         │ JSON response
                         ↓
┌──────────────────────────────────────────────────────────────────┐
│  Web UI (index.html)                                              │
│  ✓ Display response in chatbox                                  │
│  ✓ Add to conversation history                                  │
│  ✓ Ready for next message                                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔧 Configuration System

Bot MVP sử dụng hệ thống cấu hình thông minh dựa trên file `.env`.

### 📝 Configuration Flow

```
.env file (tạo từ .env.example)
   │
   ├─→ api.py: Đọc API_HOST, API_PORT
   │         → Binding trên 0.0.0.0:{API_PORT}
   │         → In API_URL khi startup
   │
   ├─→ web_server.py: Đọc WEB_HOST, WEB_PORT, API_URL
   │                → Binding trên 0.0.0.0:{WEB_PORT}
   │                → Serve index.html + CORS headers
   │
   └─→ index.html (JavaScript): Đọc window.location.hostname
                              → Tạo API_URL = http://{hostname}:{API_PORT}
                              → POST request đến API
```

### 🌐 Network Configuration Scenarios

#### Scenario 1: Local Development
```
.env:
API_PORT=8000
WEB_PORT=8080
API_URL=http://localhost:8000

Kết quả:
- API Server chạy trên: http://127.0.0.1:8000
- Web Server chạy trên: http://127.0.0.1:8080
- Web UI gọi API tại: http://localhost:8000
- Truy cập UI tại: http://localhost:8080/index.html
```

#### Scenario 2: Production Server
```
.env:
API_PORT=8000
API_URL=https://api.example.com
WEB_PORT=8080
WEB_URL=https://web.example.com

Kết quả:
- API chạy trên port 8000 (behind nginx reverse proxy)
- Web chạy trên port 8080 (behind nginx reverse proxy)
- nginx chuyển tiếp: https://api.example.com → http://localhost:8000
- nginx chuyển tiếp: https://web.example.com → http://localhost:8080
- Web UI gọi API tại: https://api.example.com (via CORS)
```

#### Scenario 3: Docker Container Network
```
docker-compose.yml environment:
API_URL=http://api-service:8000
(hoặc http://api:8000 nếu service name là 'api')

Kết quả:
- Container web gọi container api qua internal network
- Không cần hardcode localhost
- Scalable: có thể chạy multiple API instances
```

---

## 💬 Message Flow - Detailed

### 1️⃣ User Sends Message

**Web UI (JavaScript):**
```javascript
// index.html
const userMessage = inputField.value;
const conversation_id = "user-123";

const response = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: userMessage,
        conversation_id: conversation_id
    })
});
```

### 2️⃣ API Receives Request

**API Server (api.py):**
```python
@app.post("/chat")
async def chat(request: ChatRequest):
    message = request.message
    conversation_id = request.conversation_id
    
    # Get conversation history
    history = conversations.get(conversation_id, [])
    
    # Call bot
    response = chat_with_claude(message, history)
    
    # Store in memory
    conversations[conversation_id] = response['history']
    
    return ChatResponse(
        response=response['text'],
        tools_used=response['tools_used'],
        conversation_id=conversation_id
    )
```

### 3️⃣ Bot Processes Message

**Bot Logic (bot.py):**
```python
def chat_with_claude(user_message, history):
    # Add user message to history
    messages = history + [{"role": "user", "content": user_message}]
    
    # Call Claude API
    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        tools=TOOLS,  # Our functions
        messages=messages
    )
    
    # Process tool calls if any
    tools_used = []
    for block in response.content:
        if block.type == "tool_use":
            tool_name = block.name
            tool_input = block.input
            
            # Execute tool
            tool_result = process_tool_call(tool_name, tool_input)
            tools_used.append(tool_name)
    
    # Extract final text response
    final_text = response.content[-1].text
    
    return {
        'text': final_text,
        'tools_used': tools_used,
        'history': messages + [{"role": "assistant", "content": final_text}]
    }
```

### 4️⃣ Claude Autonomous Decision Making

**Claude Function Calling:**

User: "How many orders do I have?"

Claude decides:
- ✅ Use tool: `get_orders`
- Returns tool_use block with name="get_orders"
- Bot executes: `get_orders()` → returns mock data
- Claude gets result, formulates response
- Claude: "You have 3 pending orders and 2 completed orders"

---

## 🔐 Data Flow & Storage

### In-Memory Storage

**Current Implementation:**
```python
# api.py
conversations = {}

# Example structure
conversations = {
    "user-123": [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        ...
    ],
    "user-456": [
        ...
    ]
}
```

### Problems with In-Memory:
- ❌ Lost if server restarts
- ❌ Doesn't scale across multiple servers
- ❌ No persistence

### Production Solution: Database

```python
# Use SQLAlchemy + PostgreSQL
from sqlalchemy import Column, String, JSON, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String, primary_key=True)
    messages = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# In api.py
@app.post("/chat")
async def chat(request: ChatRequest):
    # Query DB
    conv = session.query(Conversation).filter_by(id=request.conversation_id).first()
    history = conv.messages if conv else []
    
    # ... same logic ...
    
    # Save to DB
    if conv:
        conv.messages = response['history']
        conv.updated_at = datetime.utcnow()
    else:
        conv = Conversation(id=request.conversation_id, messages=response['history'])
    session.add(conv)
    session.commit()
```

---

## 🛠️ Component Responsibilities

### bot.py
```
Input:  User message + conversation history
Output: Response with tool calls executed

Responsibilities:
- Create Claude API client
- Manage tool definitions
- Execute function calling loop
- Handle tool results
- Format final response
```

### api.py
```
Input:  HTTP POST /chat with JSON
Output: JSON response with bot reply

Responsibilities:
- FastAPI server setup
- CORS middleware
- Conversation storage
- Route requests to bot.py
- Format HTTP responses
- Load config from .env
```

### web_server.py
```
Input:  HTTP GET requests for static files
Output: HTML/CSS/JS files + CORS headers

Responsibilities:
- Serve index.html
- Add CORS headers
- Handle static file serving
- Load config from .env
- Log requests
```

### index.html
```
Input:  User typing in chatbox
Output: Visual display of conversation

Responsibilities:
- Beautiful UI
- Handle user input
- Make API calls
- Display responses
- Track conversation history
- Auto-detect API URL
```

---

## 🚀 Startup Sequence

### When API starts:
```bash
python api.py
```

1. ✅ Import libraries (anthropic, fastapi, etc.)
2. ✅ Load .env via python-dotenv
3. ✅ Read: API_HOST, API_PORT from environment
4. ✅ Create FastAPI app
5. ✅ Add CORS middleware
6. ✅ Create routes
7. ✅ Start server: `uvicorn.run(app, host=API_HOST, port=API_PORT)`
8. ✅ Print startup info:
   ```
   🚀 Bot MVP API Server
   📍 API URL: http://localhost:8000
   🔌 Port: 8000
   📚 Docs: http://localhost:8000/docs
   ```

### When Web Server starts:
```bash
python web_server.py
```

1. ✅ Import libraries
2. ✅ Load .env
3. ✅ Read: WEB_HOST, WEB_PORT, API_URL
4. ✅ Create HTTP server class with CORS
5. ✅ Start server: `server.serve_forever()`
6. ✅ Print startup info:
   ```
   💻 Bot MVP Web Server
   🌐 Web URL: http://localhost:8080/index.html
   🔌 Port: 8080
   🤖 API URL: http://localhost:8000
   ```

### When User opens index.html:
```
1. Browser GETs http://localhost:8080/index.html
2. web_server.py serves file with CORS headers
3. JavaScript executes
4. Detects hostname: window.location.hostname = "localhost"
5. Creates API_URL = "http://localhost:8000"
6. UI ready for input
```

---

## 📊 Request Lifecycle Example

User: "What's my revenue this week?"

### Timeline:

```
T=0ms    User types and clicks Send

T=10ms   Web UI prepares request:
         POST http://localhost:8000/chat
         {"message": "What's my revenue this week?", "conversation_id": "user-1"}

T=20ms   API receives request in route handler

T=25ms   API calls: bot.chat_with_claude(message, history)

T=30ms   bot.py creates API request to Claude:
         - messages: [{"role": "user", "content": "..."}]
         - tools: [get_orders, check_status, get_revenue]

T=100ms  Claude responds with tool_use block:
         tool_name: "get_revenue"
         input: {"time_period": "week"}

T=110ms  bot.py executes: get_revenue("week")
         Returns: {"revenue": 50000000, "currency": "VND"}

T=120ms  Claude processes tool result, generates response:
         "Your revenue this week is 50,000,000 VND!"

T=130ms  bot.py returns response to api.py

T=135ms  api.py formats JSON and sends back

T=145ms  Web UI receives response

T=150ms  Web UI renders message in chatbox
         User sees: "Your revenue this week is 50,000,000 VND!"
```

**Total time: ~150ms** (depends on Claude API latency)

---

## 🔄 Architecture Benefits

### ✅ Separation of Concerns
- **bot.py** = AI logic
- **api.py** = HTTP layer
- **web_server.py** = Frontend serving
- **index.html** = UI

### ✅ Environment-Aware Configuration
- No hardcoding
- Easy to switch between dev/prod
- Docker-ready
- Multiple deployment scenarios

### ✅ Scalability
- Can run multiple API instances
- Load balancer compatible
- Stateless (conversation stored separately)
- Database-ready

### ✅ Extensibility
- Add new tools easily
- Modify Claude prompts
- Add authentication
- Connect to real databases

### ✅ Testing
- Can test bot.py independently
- Can test api.py with curl
- Can test UI in browser
- No dependencies between components

---

## 🎯 Customization Points

### Add New Tool
```python
# bot.py - Add to TOOLS list
{
    "name": "send_email",
    "description": "Send email to customer",
    "input_schema": {
        "type": "object",
        "properties": {
            "email": {"type": "string"},
            "subject": {"type": "string"}
        }
    }
}

# Then implement handler
def send_email(email: str, subject: str) -> str:
    # Your email logic
    return f"Email sent to {email}"

# Add to process_tool_call
elif tool_name == "send_email":
    return send_email(**tool_input)
```

### Change API Response Format
```python
# api.py - Modify ChatResponse model
class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    tools_used: List[str]
    timestamp: datetime  # Add timestamp
    metadata: dict  # Add custom metadata
```

### Modify UI
```javascript
// index.html - Customize display
// Add user avatar, timestamps, tool display
// Change color scheme
// Add voice input/output
```

---

## 📚 Key Files Reference

| File | Purpose | Edits |
|------|---------|-------|
| `.env` | Configuration | ✏️ Update ports, API keys |
| `bot.py` | AI logic | ✏️ Add tools, change prompts |
| `api.py` | HTTP API | ✏️ Add endpoints, modify responses |
| `web_server.py` | Frontend server | ⭕ Rarely edit |
| `index.html` | Web UI | ✏️ Customize styling, layout |
| `requirements.txt` | Dependencies | ✏️ Add new libraries |
| `docker-compose.yml` | Container config | ✏️ For production deployment |

---

## 🔍 Debug Mode

Enable detailed logging:

```python
# bot.py
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# In functions
logger.debug(f"Tool called: {tool_name} with {tool_input}")
logger.debug(f"Claude response: {response}")
```

```bash
# Run with logging
PYTHONUNBUFFERED=1 python api.py
```

Browser console (F12):
```javascript
// Check API_URL detection
console.log("API_URL:", API_URL);
console.log("Hostname:", window.location.hostname);
```

---

This architecture supports the entire workflow from user input through Claude AI's autonomous decision-making, tool execution, and response delivery - all configured through a single `.env` file.
