"""
SQLite Database Manager for Bot MVP
Handles: conversation history, usage stats, messages
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import json

DB_PATH = "bot_data.db"


@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """Initialize database with all required tables"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT UNIQUE NOT NULL,
                platform TEXT NOT NULL,  -- 'telegram' or 'web'
                user_id TEXT,  -- Telegram user_id or web session
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,  -- 'user' or 'assistant'
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # Usage stats table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model TEXT NOT NULL,
                input_tokens INTEGER NOT NULL,
                output_tokens INTEGER NOT NULL,
                cost_usd REAL NOT NULL,
                conversation_id TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id)
            )
        """)
        
        # User memory table (long-term per-user memory)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_memory (
                user_id     TEXT PRIMARY KEY,
                memory      TEXT NOT NULL,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Orders table (mock data — replace with real API source later)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id            TEXT PRIMARY KEY,
                customer      TEXT NOT NULL,
                amount        REAL NOT NULL,
                status        TEXT NOT NULL,   -- shipped, processing, delivered, cancelled
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expected_delivery DATE,
                delivered_at  TIMESTAMP
            )
        """)

        # Seed mock orders if table is empty
        cursor.execute("SELECT COUNT(*) as cnt FROM orders")
        if cursor.fetchone()["cnt"] == 0:
            mock_orders = [
                ("ORD001", "Nguyễn A", 500000, "shipped",   "2026-03-18", None),
                ("ORD002", "Trần B",   750000, "processing", "2026-03-20", None),
                ("ORD003", "Phạm C",   1200000, "delivered", None,         "2026-03-10 14:30:00"),
                ("ORD004", "Lê D",     320000, "delivered",  None,         "2026-03-12 09:15:00"),
                ("ORD005", "Hoàng E",   890000, "cancelled",  None,         None),
            ]
            cursor.executemany("""
                INSERT INTO orders (id, customer, amount, status, expected_delivery, delivered_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, mock_orders)
            print("   🌱 Seeded mock orders into DB")

        # Create indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_stats(timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conv_platform ON conversations(platform)")
        
        print("✅ Database initialized successfully")


class ConversationDB:
    """Manage conversations and messages"""
    
    @staticmethod
    def create_conversation(conversation_id: str, platform: str, user_id: Optional[str] = None):
        """Create new conversation"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO conversations (conversation_id, platform, user_id)
                VALUES (?, ?, ?)
            """, (conversation_id, platform, user_id))
    
    @staticmethod
    def add_message(conversation_id: str, role: str, content: str):
        """Add message to conversation"""
        with get_db() as conn:
            cursor = conn.cursor()
            # Update conversation timestamp
            cursor.execute("""
                UPDATE conversations 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE conversation_id = ?
            """, (conversation_id,))
            
            # Insert message
            cursor.execute("""
                INSERT INTO messages (conversation_id, role, content)
                VALUES (?, ?, ?)
            """, (conversation_id, role, content))
    
    @staticmethod
    def get_conversation_history(conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT role, content, created_at
                FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at ASC
                LIMIT ?
            """, (conversation_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_all_conversations(platform: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all conversations, optionally filtered by platform"""
        with get_db() as conn:
            cursor = conn.cursor()
            if platform:
                cursor.execute("""
                    SELECT c.*, COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                    WHERE c.platform = ?
                    GROUP BY c.conversation_id
                    ORDER BY c.updated_at DESC
                    LIMIT ?
                """, (platform, limit))
            else:
                cursor.execute("""
                    SELECT c.*, COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON c.conversation_id = m.conversation_id
                    GROUP BY c.conversation_id
                    ORDER BY c.updated_at DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]


class UserMemoryDB:
    """Manage long-term per-user memory"""

    @staticmethod
    def get_memory(user_id: str) -> Optional[str]:
        """Return memory blob for a user, or None if not exists"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT memory FROM user_memory WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            return row["memory"] if row else None

    @staticmethod
    def upsert_memory(user_id: str, memory: str):
        """Insert or update memory blob for a user"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_memory (user_id, memory, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    memory = excluded.memory,
                    updated_at = CURRENT_TIMESTAMP
            """, (user_id, memory))
        print(f"🧠 Memory updated for user: {user_id[:8]}...")


class OrdersDB:
    """
    Data access layer for orders.
    Currently reads from local SQLite (mock data).
    To switch to real API: replace method bodies only — callers stay the same.
    """

    @staticmethod
    def get_orders(limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent orders, newest first."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, customer, amount, status, expected_delivery, delivered_at, created_at
                FROM orders
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_order(order_id: str) -> Optional[Dict[str, Any]]:
        """Get a single order by ID."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def get_revenue(period: str = "today") -> Dict[str, Any]:
        """
        Compute revenue from orders table.
        period: 'today' | 'week' | 'month'
        """
        period_filter = {
            "today": "DATE(created_at) = DATE('now')",
            "week":  "created_at >= DATE('now', '-7 days')",
            "month": "created_at >= DATE('now', '-30 days')",
        }.get(period, "1=1")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                SELECT
                    COUNT(*) as order_count,
                    COALESCE(SUM(amount), 0) as revenue
                FROM orders
                WHERE status != 'cancelled'
                AND {period_filter}
            """)
            row = dict(cursor.fetchone())
            return {"period": period, "revenue": row["revenue"], "order_count": row["order_count"]}

    @staticmethod
    def upsert_order(order: Dict[str, Any]):
        """Insert or update an order (useful for syncing from real API)."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO orders (id, customer, amount, status, expected_delivery, delivered_at)
                VALUES (:id, :customer, :amount, :status, :expected_delivery, :delivered_at)
                ON CONFLICT(id) DO UPDATE SET
                    customer = excluded.customer,
                    amount = excluded.amount,
                    status = excluded.status,
                    expected_delivery = excluded.expected_delivery,
                    delivered_at = excluded.delivered_at
            """, order)


class UsageStatsDB:
    """Manage usage statistics"""
    
    # Pricing table (same as usage_tracker.py)
    PRICING = {
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-3-7-sonnet-20250219": {"input": 3.0, "output": 15.0},
        "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
        "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
    }
    
    USD_TO_VND = 20000  # Exchange rate
    
    @staticmethod
    def log_request(model: str, input_tokens: int, output_tokens: int, conversation_id: Optional[str] = None):
        """Log API request usage"""
        # Calculate cost
        pricing = UsageStatsDB.PRICING.get(model, {"input": 3.0, "output": 15.0})
        cost_usd = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usage_stats (model, input_tokens, output_tokens, cost_usd, conversation_id)
                VALUES (?, ?, ?, ?, ?)
            """, (model, input_tokens, output_tokens, cost_usd, conversation_id))
        
        print(f"📊 Logged usage: {input_tokens} in + {output_tokens} out = ${cost_usd:.4f}")
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Get aggregated usage statistics"""
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Total stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_requests,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(cost_usd) as total_cost_usd
                FROM usage_stats
            """)
            totals = dict(cursor.fetchone())
            
            # Recent sessions (last 10)
            cursor.execute("""
                SELECT 
                    timestamp,
                    model,
                    input_tokens,
                    output_tokens,
                    cost_usd,
                    conversation_id
                FROM usage_stats
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            recent = [dict(row) for row in cursor.fetchall()]
            
            # Calculate derived values
            total_tokens = (totals["total_input_tokens"] or 0) + (totals["total_output_tokens"] or 0)
            total_cost_vnd = (totals["total_cost_usd"] or 0) * UsageStatsDB.USD_TO_VND
            
            return {
                "total_requests": totals["total_requests"] or 0,
                "total_input_tokens": totals["total_input_tokens"] or 0,
                "total_output_tokens": totals["total_output_tokens"] or 0,
                "total_tokens": total_tokens,
                "total_cost_usd": round(totals["total_cost_usd"] or 0, 4),
                "total_cost_vnd": round(total_cost_vnd, 2),
                "recent_sessions": recent
            }
    
    @staticmethod
    def reset_stats():
        """Clear all usage statistics"""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM usage_stats")
            print("🗑️ Usage stats reset")


# Initialize database when module is imported
if __name__ == "__main__":
    init_database()
    print("Database ready!")
