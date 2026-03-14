"""
Telegram Bot MVP với Claude API + Function Calling
"""
import sys
# Fix UTF-8 encoding on Windows terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
import json
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic
from database import UsageStatsDB, ConversationDB, init_database
from skills import TOOLS, process_tool_call

# Debug: Print current working directory
print("="*60)
print("🔍 DEBUG - bot.py initialization")
print(f"📁 Current working directory: {os.getcwd()}")
print(f"📄 bot.py location: {Path(__file__).parent}")

# Load environment variables
env_path = Path(__file__).parent / '.env'
print(f"🔧 Looking for .env at: {env_path}")
print(f"✓ .env exists: {env_path.exists()}")

if env_path.exists():
    with open(env_path, 'r', encoding='utf-8') as f:
        print("📝 .env file contents (first 3 lines):")
        for i, line in enumerate(f):
            if i < 3:
                print(f"   {line.rstrip()}")

load_dotenv(dotenv_path=env_path, override=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Anthropic client with API key from environment
api_key = os.getenv("ANTHROPIC_API_KEY")
print(f"🔑 API Key from os.getenv: {api_key[:30] if api_key else 'None'}...{api_key[-10:] if api_key and len(api_key) > 40 else ''}")
print(f"📏 Key length: {len(api_key) if api_key else 0}")

if not api_key:
    raise ValueError("❌ ANTHROPIC_API_KEY not found in .env file!")

print(f"✅ Creating Anthropic client with key...")
client = Anthropic(api_key=api_key)
print(f"✅ Anthropic client created successfully")

# Initialize database
init_database()

# Get Claude model from environment
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
BASE_PROMPT = os.getenv("BASE_PROMPT", "Bạn là chatbot bán hàng thông minh. Trả lời tiếng Việt, thân thiện, hữu ích.")
print(f"🤖 Claude Model: {CLAUDE_MODEL}")
print("="*60)

# Main bot function
def build_system_prompt(user_memory: str = "") -> str:
    base = BASE_PROMPT

    if user_memory:
        base += f"\n\n---\n## Thông tin người dùng này (từ các cuộc trò chuyện trước)\n{user_memory}"

    return base


def chat_with_claude(user_message, conversation_history=None, conversation_id=None, user_memory: str = ""):
    """
    Chat với Claude, tự động gọi tools khi cần
    """
    if conversation_history is None:
        conversation_history = []
    
    # Add user message
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    # System prompt with injected user memory
    system_prompt = build_system_prompt(user_memory)
    
    # Call Claude with tools
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system_prompt,
        tools=TOOLS,
        messages=conversation_history
    )
    
    # Track usage
    if hasattr(response, 'usage'):
        UsageStatsDB.log_request(
            model=CLAUDE_MODEL,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            conversation_id=conversation_id
        )
    
    # Process response
    while response.stop_reason == "tool_use":
        # Find tool use block
        tool_use_block = None
        for block in response.content:
            if block.type == "tool_use":
                tool_use_block = block
                break
        
        if not tool_use_block:
            break
        
        # Execute tool
        tool_result = process_tool_call(
            tool_use_block.name,
            tool_use_block.input
        )
        
        # Add assistant response and tool result to history
        conversation_history.append({
            "role": "assistant",
            "content": response.content
        })
        
        conversation_history.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_block.id,
                    "content": json.dumps(tool_result)
                }
            ]
        })
        
        # Get next response
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=TOOLS,
            messages=conversation_history
        )
        
        # Track usage for follow-up
        if hasattr(response, 'usage'):
            UsageStatsDB.log_request(
                model=CLAUDE_MODEL,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                conversation_id=conversation_id
            )
    
    # Extract final text response
    final_response = ""
    for block in response.content:
        if hasattr(block, "text"):
            final_response = block.text
            break
    
    # Add final response to history
    conversation_history.append({
        "role": "assistant",
        "content": final_response
    })
    
    return final_response, conversation_history


if __name__ == "__main__":
    # Test
    print("Bot MVP - Claude + Function Calling")
    history = None
    
    while True:
        user_input = input("\nBạn: ").strip()
        if not user_input:
            continue
        if user_input.lower() in ["exit", "quit"]:
            break
        
        response, history = chat_with_claude(user_input, history)
        print(f"\nBot: {response}")
