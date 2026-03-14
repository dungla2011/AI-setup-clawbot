"""
data_provider.py — Data access layer for bot tools.

Đây là nơi duy nhất bot lấy data. Hiện tại đọc từ SQLite (mock).
Để kết nối API thật: chỉ sửa các hàm trong file này, không cần đụng bot.py.

Swap guide:
  Thay dòng:  return OrdersDB.get_orders(limit)
  Bằng:       return real_api.fetch_orders(limit)
"""

from database import OrdersDB
from typing import Any


# ─────────────────────────────────────────────
# Tool: get_orders
# ─────────────────────────────────────────────
def get_orders(limit: int = 5) -> Any:
    """
    Lấy danh sách đơn hàng gần đây.

    [MOCK → DB]  Đọc từ bảng orders trong SQLite.
    [REAL API]   Thay bằng: requests.get(f"{API_BASE}/orders?limit={limit}").json()
    """
    orders = OrdersDB.get_orders(limit)
    if not orders:
        return {"message": "Không có đơn hàng nào."}
    return orders


# ─────────────────────────────────────────────
# Tool: check_status
# ─────────────────────────────────────────────
def check_status(order_id: str) -> Any:
    """
    Kiểm tra trạng thái một đơn hàng theo ID.

    [MOCK → DB]  Đọc từ bảng orders trong SQLite.
    [REAL API]   Thay bằng: requests.get(f"{API_BASE}/orders/{order_id}").json()
    """
    order = OrdersDB.get_order(order_id)
    if not order:
        return {"error": f"Không tìm thấy đơn hàng: {order_id}"}
    return order


# ─────────────────────────────────────────────
# Tool: get_revenue
# ─────────────────────────────────────────────
def get_revenue(period: str = "today") -> Any:
    """
    Lấy doanh thu theo kỳ: today | week | month.

    [MOCK → DB]  Tính SUM(amount) từ bảng orders trong SQLite.
    [REAL API]   Thay bằng: requests.get(f"{API_BASE}/revenue?period={period}").json()
    """
    return OrdersDB.get_revenue(period)
