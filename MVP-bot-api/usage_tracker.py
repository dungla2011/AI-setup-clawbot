"""
Usage tracking và tính toán chi phí Claude API
"""
import json
import os
from datetime import datetime
from pathlib import Path

# Claude pricing (USD per 1M tokens)
PRICING = {
    "claude-sonnet-4-20250514": {
        "input": 3.00,
        "output": 15.00
    },
    "claude-3-7-sonnet-20250219": {
        "input": 3.00,
        "output": 15.00
    },
    "claude-3-5-sonnet-latest": {
        "input": 3.00,
        "output": 15.00
    },
    "claude-3-haiku-20240307": {
        "input": 0.25,
        "output": 1.25
    }
}

class UsageTracker:
    def __init__(self, log_file="usage_log.json"):
        self.log_file = Path(__file__).parent / log_file
        self.usage_data = self._load_data()
    
    def _load_data(self):
        """Load existing usage data"""
        if self.log_file.exists():
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            "sessions": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0
        }
    
    def _save_data(self):
        """Save usage data to file"""
        with open(self.log_file, 'w') as f:
            json.dump(self.usage_data, f, indent=2)
    
    def log_request(self, model, input_tokens, output_tokens):
        """Log một API request"""
        # Get pricing
        pricing = PRICING.get(model, {"input": 3.0, "output": 15.0})
        
        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        total_cost = input_cost + output_cost
        
        # Create session entry
        session = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(total_cost, 6)
        }
        
        # Update totals
        self.usage_data["sessions"].append(session)
        self.usage_data["total_input_tokens"] += input_tokens
        self.usage_data["total_output_tokens"] += output_tokens
        self.usage_data["total_cost_usd"] += total_cost
        
        # Save to file
        self._save_data()
        
        return session
    
    def get_stats(self):
        """Get current statistics"""
        total_tokens = self.usage_data["total_input_tokens"] + self.usage_data["total_output_tokens"]
        
        return {
            "total_requests": len(self.usage_data["sessions"]),
            "total_input_tokens": self.usage_data["total_input_tokens"],
            "total_output_tokens": self.usage_data["total_output_tokens"],
            "total_tokens": total_tokens,
            "total_cost_usd": round(self.usage_data["total_cost_usd"], 4),
            "total_cost_vnd": round(self.usage_data["total_cost_usd"] * 25000, 0),  # USD to VND
            "recent_sessions": self.usage_data["sessions"][-10:]  # Last 10 sessions
        }
    
    def reset_stats(self):
        """Reset all statistics"""
        self.usage_data = {
            "sessions": [],
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0
        }
        self._save_data()

# Global tracker instance
tracker = UsageTracker()
