"""
test01-user-memory.py
=====================
Test long-term user memory summarization end-to-end.

What it does:
  1. Generate (or reuse) a fixed user_id
  2. Send N chat messages to POST /chat (each in the SAME conversation)
  3. After each exchange, poll GET /memory/{user_id}
  4. Print a clear timeline showing exactly when memory is created/updated
  5. Print the full memory diff whenever it changes

Run:
  python test01-user-memory.py                 # 15 messages, localhost:8100
  python test01-user-memory.py -n 20           # 20 messages
  python test01-user-memory.py -n 8 --host http://localhost:8100
  python test01-user-memory.py --fresh         # wipe memory before test
"""

import argparse
import json
import time
import uuid
import sys
import os
import urllib.request
import urllib.error
from datetime import datetime

# ── Colour helpers (work on Windows if ANSICON / WT / VS Code) ──────────────
def _c(code: str, text: str) -> str:
    if sys.stdout.isatty() or os.environ.get("TERM"):
        return f"\033[{code}m{text}\033[0m"
    return text

RED    = lambda t: _c("31", t)
GREEN  = lambda t: _c("32", t)
YELLOW = lambda t: _c("33", t)
CYAN   = lambda t: _c("36", t)
BOLD   = lambda t: _c("1",  t)
DIM    = lambda t: _c("2",  t)


# ── Sample messages — feel free to edit ──────────────────────────────────────
SAMPLE_MESSAGES = [
    "Xin chào! Tôi muốn xem danh sách đơn hàng gần đây.",
    "Đơn hàng ORD-001 đang ở trạng thái nào?",
    "Doanh thu tháng này là bao nhiêu?",
    "Tôi thường hỏi về đơn hàng của khách hàng Nguyễn Văn A.",
    "Còn đơn ORD-003 thì sao, đã giao chưa?",
    "Tôi muốn biết tổng doanh thu tuần này.",
    "Khách hàng hay hỏi về thời gian giao hàng, em trả lời thế nào?",
    "Cho tôi xem tất cả đơn hàng đang pending.",
    "Doanh thu hôm nay so với hôm qua thế nào?",
    "Có bao nhiêu đơn hàng bị cancelled không?",
    "Tôi cần báo cáo đơn hàng cho sếp, format nào phù hợp?",
    "Đơn ORD-005 của khách Lê Thị B đã xong chưa?",
    # ── Vượt ngưỡng 12 → memory trigger ─────────────────────────────────────
    "Tóm tắt lại tình hình kinh doanh cho tôi.",
    "Khách hàng VIP của chúng tôi là ai?",
    "Tôi muốn đặt thêm 50 đơn hàng mới cho tháng sau.",
    "Cảm ơn em đã hỗ trợ hôm nay!",
    "Ngày mai tôi sẽ hỏi thêm về chiến lược marketing nhé.",
    "Một câu hỏi nữa: hệ thống có thể tự gửi báo cáo email không?",
]


def _post(url: str, body: dict, timeout: float = 30.0) -> dict:
    data = json.dumps(body).encode()
    req  = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _get(url: str, timeout: float = 10.0) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _delete(url: str, timeout: float = 10.0) -> None:
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            pass
    except urllib.error.HTTPError:
        pass


def _print_memory(mem: str | None, label: str = "") -> None:
    if not mem:
        print(DIM("   (no memory yet)"))
        return
    print(CYAN(f"   ┌─ {label or 'Current Memory'} ({len(mem)} chars) ─────────────"))
    for line in mem.splitlines():
        print(CYAN("   │ ") + line)
    print(CYAN("   └──────────────────────────────────────────────────"))


def _memory_changed(old: str | None, new: str | None) -> bool:
    return (old or "").strip() != (new or "").strip()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test user memory summarization")
    parser.add_argument("-n", "--messages", type=int, default=15,
                        help="Number of messages to send (default: 15)")
    parser.add_argument("--host", default="http://localhost:8100",
                        help="API base URL (default: http://localhost:8100)")
    parser.add_argument("--user-id", default=None,
                        help="Fix a specific user_id (default: auto-generate)")
    parser.add_argument("--conv-id", default=None,
                        help="Reuse an existing conversation_id")
    parser.add_argument("--fresh", action="store_true",
                        help="Delete existing memory for this user before starting")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Seconds to wait between messages (default: 0.5)")
    args = parser.parse_args()

    host      = args.host.rstrip("/")
    user_id   = args.user_id or f"test-{uuid.uuid4().hex[:8]}"
    conv_id   = args.conv_id
    n         = min(args.messages, len(SAMPLE_MESSAGES))

    print(BOLD("\n╔══════════════════════════════════════════════════════╗"))
    print(BOLD("║      test01-user-memory — Memory Summarization       ║"))
    print(BOLD("╚══════════════════════════════════════════════════════╝"))
    print(f"  Host      : {host}")
    print(f"  User ID   : {YELLOW(user_id)}")
    print(f"  Messages  : {n}  (trigger every {BOLD('12')} msgs)")
    print(f"  Fresh run : {args.fresh}")
    print()

    # ── Health check ──────────────────────────────────────────────────────
    try:
        _get(f"{host}/health")
        print(GREEN("✓ API is online\n"))
    except Exception as e:
        print(RED(f"✗ API unreachable at {host}  → {e}"))
        print(RED("  Start the server first:  python api.py"))
        sys.exit(1)

    # ── Optional: wipe memory ─────────────────────────────────────────────
    if args.fresh:
        _delete(f"{host}/memory/{user_id}")
        print(YELLOW(f"🗑  Wiped memory for {user_id}\n"))

    # ── Snapshot baseline memory ──────────────────────────────────────────
    prev_memory: str | None = (_get(f"{host}/memory/{user_id}") or {}).get("memory")
    if prev_memory:
        print(YELLOW("📋 Existing memory found:"))
        _print_memory(prev_memory, "Baseline Memory")
        print()

    summarize_every = 12   # must match memory.py SUMMARIZE_EVERY
    triggers_expected = [i for i in range(1, n + 1) if i % (summarize_every // 2) == 0]
    # Each user message → 1 user msg + 1 bot msg = 2 messages in history
    # summarize fires when total msgs % 12 == 0  (= 6 exchanges)
    trigger_exchanges = [summarize_every // 2 * k for k in range(1, n)]

    print(BOLD(f"{'#':>3}  {'User message':40}  {'Memory status':20}  Resp(s)"))
    print("─" * 80)

    memory_updates = []

    for i in range(1, n + 1):
        msg = SAMPLE_MESSAGES[i - 1]
        display_msg = (msg[:37] + "...") if len(msg) > 40 else msg

        t0 = time.time()
        try:
            resp = _post(f"{host}/chat", {
                "message": msg,
                "conversation_id": conv_id,
                "user_id": user_id,
            })
        except Exception as e:
            print(RED(f"{i:>3}  ERROR: {e}"))
            break

        elapsed = time.time() - t0
        conv_id = resp.get("conversation_id", conv_id)  # latch first conv_id

        # Poll memory (small delay so background task has time to write)
        # Memory is written async — give it up to 3s after trigger exchanges
        is_trigger = (i in trigger_exchanges)
        if is_trigger:
            time.sleep(2.0)   # wait for background summarize task

        cur_memory_resp = _get(f"{host}/memory/{user_id}") or {}
        cur_memory: str | None = cur_memory_resp.get("memory")

        if _memory_changed(prev_memory, cur_memory):
            mem_status = GREEN("● UPDATED ←━━")
            memory_updates.append({"exchange": i, "memory": cur_memory})
        elif cur_memory:
            mem_status = DIM("  exists")
        else:
            mem_status = DIM("  —")

        trigger_marker = YELLOW(" ⚡") if is_trigger else "  "
        print(f"{i:>3}{trigger_marker} {display_msg:40}  {mem_status:20}  {elapsed:.1f}s")

        # Print memory diff on change
        if _memory_changed(prev_memory, cur_memory):
            print()
            _print_memory(cur_memory, f"Memory after exchange #{i}")
            print()
            prev_memory = cur_memory

        time.sleep(args.delay)

    # ── Summary ───────────────────────────────────────────────────────────
    print("\n" + BOLD("═" * 80))
    print(BOLD("SUMMARY"))
    print(BOLD("═" * 80))
    print(f"  conversation_id : {CYAN(conv_id or 'n/a')}")
    print(f"  user_id         : {YELLOW(user_id)}")
    print(f"  Messages sent   : {n}")
    print(f"  Memory updates  : {GREEN(str(len(memory_updates))) if memory_updates else RED('0')}")

    if memory_updates:
        print()
        for upd in memory_updates:
            print(f"  • Triggered at exchange #{upd['exchange']}:")
            _print_memory(upd["memory"])
    else:
        print()
        print(YELLOW("  ⚠  No memory was written.  Possible reasons:"))
        print(f"       - Need at least {summarize_every} messages in history "
              f"(sent only {n} → history has {n * 2} msgs, need multiple of {summarize_every})")
        print(f"       - Conversation uses tool calls whose content isn't plain text")
        print(f"       - Background task didn't finish within the 2s poll window — "
              f"try:  GET {host}/memory/{user_id}  after a few seconds")

    # ── Final memory ──────────────────────────────────────────────────────
    final = (_get(f"{host}/memory/{user_id}") or {}).get("memory")
    if final:
        print()
        print(BOLD("Final memory blob:"))
        _print_memory(final, "Final Memory")

    print()
    print(f"  Re-run to continue the SAME conversation:")
    print(f"    python test01-user-memory.py --user-id {user_id} --conv-id {conv_id} -n 10")
    print(f"  Wipe memory and start fresh:")
    print(f"    python test01-user-memory.py --user-id {user_id} --fresh")
    print()


if __name__ == "__main__":
    main()
