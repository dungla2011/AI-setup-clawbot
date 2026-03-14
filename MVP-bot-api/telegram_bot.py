"""
Telegram Bot Interface for Bot MVP
Uses python-telegram-bot v22+ (async) with Claude AI
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from bot import chat_with_claude
from database import ConversationDB, init_database

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
init_database()

# Get Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not found in .env file!")

# Store conversation histories (in-memory for active sessions)
user_conversations = {}


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    await update.message.reply_text(
        f"Xin chào {user.first_name}! 👋\n\n"
        "Tôi là Bot MVP - trợ lý bán hàng thông minh.\n"
        "Bạn có thể hỏi tôi về:\n"
        "• Đơn hàng\n"
        "• Doanh thu\n"
        "• Tồn kho\n"
        "• Thống kê\n\n"
        "Hãy thử hỏi: 'Hôm nay bán được bao nhiêu?'"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
🤖 *Bot MVP - Hướng dẫn sử dụng*

*Các lệnh:*
/start - Bắt đầu trò chuyện
/help - Hiển thị hướng dẫn này
/new - Bắt đầu cuộc hội thoại mới
/stats - Xem thống kê chi phí API

*Ví dụ câu hỏi:*
• "Hôm nay có bao nhiêu đơn hàng?"
• "Doanh thu tuần này?"
• "Kiểm tra tồn kho sản phẩm X"
• "Đơn hàng nào đang pending?"

Cứ hỏi tự nhiên, tôi sẽ hiểu! 😊
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def new_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /new command - start new conversation"""
    user_id = str(update.effective_user.id)
    if user_id in user_conversations:
        del user_conversations[user_id]
    await update.message.reply_text(
        "🔄 Đã bắt đầu cuộc hội thoại mới!\n"
        "Tôi sẵn sàng trò chuyện với bạn."
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show usage statistics"""
    from database import UsageStatsDB
    stats = UsageStatsDB.get_stats()
    
    stats_text = f"""
📊 *Thống kê sử dụng API*

🔢 Tổng requests: {stats['total_requests']}
📥 Input tokens: {stats['total_input_tokens']:,}
📤 Output tokens: {stats['total_output_tokens']:,}
💰 Chi phí: ${stats['total_cost_usd']:.4f} (~{stats['total_cost_vnd']:,.0f} VND)

Xem chi tiết tại: http://localhost:8080/stats.html
"""
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages"""
    user = update.effective_user
    user_id = str(user.id)
    user_message = update.message.text
    
    logger.info(f"📩 Message from {user.first_name} (@{user.username}): {user_message}")
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    try:
        # Get or create conversation
        conversation_id = user_conversations.get(user_id)
        if conversation_id is None:
            import uuid
            conversation_id = f"tg_{user_id}_{uuid.uuid4().hex[:8]}"
            user_conversations[user_id] = conversation_id
            
            # Create conversation in DB
            ConversationDB.create_conversation(
                conversation_id=conversation_id,
                platform="telegram",
                user_id=user_id
            )
        
        # Save user message to DB
        ConversationDB.add_message(conversation_id, role="user", content=user_message)
        
        # Get conversation history from DB
        history_from_db = ConversationDB.get_conversation_history(conversation_id, limit=20)
        
        # Convert DB format to Claude format
        conversation_history = []
        for msg in history_from_db[:-1]:  # Exclude last message (current user message)
            conversation_history.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        # Chat with Claude
        bot_response, updated_history = chat_with_claude(
            user_message=user_message,
            conversation_history=conversation_history,
            conversation_id=conversation_id
        )
        
        # Save bot response to DB
        ConversationDB.add_message(conversation_id, role="assistant", content=bot_response)
        
        # Send response
        await update.message.reply_text(bot_response)
        
        logger.info(f"✅ Responded to {user.first_name}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        await update.message.reply_text(
            "Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau."
        )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Start the bot"""
    logger.info("🚀 Starting Telegram Bot...")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("new", new_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    logger.info("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
