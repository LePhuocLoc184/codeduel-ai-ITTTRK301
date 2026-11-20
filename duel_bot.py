"""
duel_bot.py - Bot đối thủ để TEST trận đấu CodeDuel mà không cần mở 2 tài khoản.

File này độc lập: KHÔNG nằm trong frontend/ hay backend/, không sửa gì ở backend.
Bot đi đúng đường của một người chơi thật: đăng nhập -> vào hàng đợi/phòng -> WebSocket ->
gõ phím (để bạn thấy "Đối thủ đang gõ code...") -> nộp bài qua /execute/submit.

Cần: Python 3.10+ và thư viện `websockets` (backend của bạn đã cần nó rồi: pip install websockets).
Chạy trong cùng venv với backend:

    python duel_bot.py queue                 # bot vào hàng đợi Ranked, ghép với BẠN (rating gần 1200)
    python duel_bot.py create                # bot tạo phòng, in mã phòng; bạn vào phòng bằng mã đó
    python duel_bot.py join ABC123           # bot vào phòng do bạn tạo (mã 6 ký tự)

Tùy chọn:
    --mode win      bot nộp lời giải ĐÚNG sau --delay giây   (bạn thua nếu nộp chậm hơn)   [mặc định]
    --mode lose     bot nộp lời giải SAI (bạn vẫn thắng nếu nộp đúng)
    --mode idle     bot chỉ gõ phím, không nộp (đủ để thử đồng hồ / chỉ báo gõ / hết giờ hòa)
    --delay 40      số giây bot chờ rồi mới nộp (mặc định 30)
    --user NAME     tài khoản bot (mặc định bot_duel; tự đăng ký nếu chưa có), --password, --base
"""
import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request

try:
    import websockets
except ImportError:  # pragma: no cover
    sys.exit("Thiếu thư viện websockets. Chạy: pip install websockets")

# Lời giải Python (đọc stdin, in kết quả) cho 6 bài trong seed của backend.
SOLUTIONS = {
    "two sum": '''import sys, ast
lines = sys.stdin.read().split("\\n")
nums = ast.literal_eval(lines[0])
target = int(lines[1])
seen = {}
for i, n in enumerate(nums):
    if target - n in seen:
        print([seen[target - n], i])
        break
    seen[n] = i
''',
    "palindrome": '''import sys
s = sys.stdin.readline().rstrip("\\n")
t = [c.lower() for c in s if c.isalnum()]
print("true" if t == t[::-1] else "false")
''',
    "reverse integer": '''x = int(input())
r = int(str(abs(x))[::-1])
print(-r if x < 0 else r)
''',
    "longest increasing": '''import ast, bisect
nums = ast.literal_eval(input())
tails = []
for n in nums:
    i = bisect.bisect_left(tails, n)
    if i == len(tails):
        tails.append(n)
    else:
        tails[i] = n
print(len(tails))
''',
    "valid parentheses": '''s = input().strip()
pairs = {")": "(", "]": "[", "}": "{"}
st = []
ok = True
for c in s:
    if c in "([{":
        st.append(c)
    elif not st or st.pop() != pairs[c]:
        ok = False
        break
print("true" if ok and not st else "false")
''',
    "coin change": '''import ast
coins = ast.literal_eval(input())
amount = int(input())
INF = float("inf")
dp = [0] + [INF] * amount
for a in range(1, amount + 1):
    for c in coins:
        if c <= a and dp[a - c] + 1 < dp[a]:
            dp[a] = dp[a - c] + 1
print(dp[amount] if dp[amount] != INF else -1)
''',
}
WRONG_CODE = 'print("sai")\n'


def log(message):
    print(f"[bot {time.strftime('%H:%M:%S')}] {message}", flush=True)


def http(method, base, path, body=None, token=None):
    """Gọi API, trả (status_code, json). Không ném lỗi với mã 4xx/5xx."""
    request = urllib.request.Request(
        base + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read() or b"{}")
        except ValueError:
            return error.code, {}
    except urllib.error.URLError as error:
        sys.exit(f"Không kết nối được backend {base}: {error.reason}. Backend đã chạy chưa?")


def authenticate(base, user, password):
    status, data = http("POST", base, "/api/v1/auth/login", {"username": user, "password": password})
    if status >= 400:
        log(f"Chưa có tài khoản {user}, đang đăng ký...")
        status, data = http(
            "POST", base, "/api/v1/auth/register",
            {"username": user, "email": f"{user}@gmail.com", "password": password},
        )
    if status >= 400:
        sys.exit(f"Không đăng nhập/đăng ký được bot: {status} {data}")
    payload = data["data"]
    log(f"Đã đăng nhập bot '{payload['user']['username']}' (rating {payload['user'].get('rating')}).")
    return payload["access_token"], payload["user"]


def find_room_code(base, token, command, code):
    if command == "create":
        status, data = http("POST", base, "/api/v1/rooms/create", {}, token)
        if status >= 400:
            sys.exit(f"Bot không tạo được phòng: {data.get('message', data)}")
        room_code = data["data"]["room_code"]
        log(f"Đã tạo phòng. MÃ PHÒNG: {room_code}  -> vào phòng này bằng tài khoản của bạn rồi bấm Sẵn sàng.")
        return room_code

    if command == "join":
        status, data = http("POST", base, "/api/v1/rooms/join", {"room_code": code.upper()}, token)
        if status >= 400:
            sys.exit(f"Bot không vào được phòng {code}: {data.get('message', data)}")
        return data["data"]["room_code"]

    # queue: vào hàng đợi Ranked rồi chờ được ghép
    status, data = http("GET", base, "/api/v1/matchmaking/status", token=token)
    if (data.get("data") or {}).get("status") not in ("searching", "matched"):
        status, data = http("POST", base, "/api/v1/matchmaking/join", {"game_mode": "RANKED_1V1"}, token)
        if status >= 400:
            sys.exit(f"Bot không vào được hàng đợi: {data.get('message', data)}")
    log("Bot đang tìm trận Ranked... hãy bấm 'Tìm trận' bằng tài khoản của bạn (rating chênh <=150, sau 30s <=300).")
    waited = 0
    while True:
        time.sleep(2)
        waited += 2
        status, data = http("GET", base, "/api/v1/matchmaking/status", token=token)
        info = data.get("data") or {}
        if info.get("status") == "matched" and info.get("room_code"):
            log(f"Đã ghép với {info.get('opponent', {}).get('username', '?')} -> phòng {info['room_code']}.")
            return info["room_code"]
        if info.get("status") == "idle":
            sys.exit("Lượt chờ của bot đã bị hủy/kết thúc ngoài ý muốn.")
        if waited % 10 == 0:
            log(f"...vẫn đang chờ ({waited}s). Bạn đã bấm 'Tìm trận' chưa? Rating hai bên có chênh quá 300 không?")


def pick_solution(title, mode):
    if mode == "lose":
        return WRONG_CODE
    lowered = (title or "").lower()
    for key, code in SOLUTIONS.items():
        if key in lowered:
            return code
    log(f"Không có lời giải mẫu cho bài '{title}', bot sẽ nộp code sai.")
    return WRONG_CODE


async def fight(base, token, ws, room, args):
    """Gõ phím liên tục rồi nộp bài sau --delay giây."""
    question = room.get("question") or {}
    title = question.get("title", "")
    log(f"Trận bắt đầu! Bài: '{title}'. Chế độ bot: {args.mode}, nộp sau {args.delay}s.")
    deadline = time.time() + args.delay
    while time.time() < deadline:
        await ws.send(json.dumps({"action": "player_typing", "is_typing": True}))
        await asyncio.sleep(1)
    await ws.send(json.dumps({"action": "player_typing", "is_typing": False}))

    if args.mode == "idle":
        log("Chế độ idle: bot không nộp bài.")
        return

    code = pick_solution(title, args.mode)
    log("Bot đang nộp bài...")
    status, data = await asyncio.to_thread(
        http, "POST", base, "/api/v1/execute/submit",
        {"question_id": question["id"], "language": "python", "code_content": code, "room_id": room["room_id"]},
        token,
    )
    result = data.get("data") or {}
    log(f"Kết quả nộp: HTTP {status}, {result.get('status')} {result.get('passed_test_cases')}/{result.get('total_test_cases')}"
        + (f" - {data.get('message')}" if status >= 400 else ""))


async def run(args):
    base = args.base.rstrip("/")
    token, user = authenticate(base, args.user, args.password)
    room_code = find_room_code(base, token, args.command, args.code)
    ws_url = base.replace("http", "ws", 1) + f"/api/v1/rooms/ws/arena/{room_code}?token={token}"
    log(f"Kết nối WebSocket vào phòng {room_code}...")

    fighter = None
    room_id = None
    async with websockets.connect(ws_url) as ws:
        if args.command != "queue":
            await ws.send(json.dumps({"action": "player_ready"}))
        async for raw in ws:
            message = json.loads(raw)
            event, data = message.get("event"), message.get("data") or {}
            if event == "COUNTDOWN":
                log(f"Đếm ngược vào trận: {data.get('value')}")
            elif event not in ("TIME_SYNC", "OPPONENT_TYPING"):
                log(f"Sự kiện: {event}")

            # Nhớ room_id từ ROOM_STATE (cần khi nộp bài).
            if event == "ROOM_STATE":
                room_id = data.get("room_id") or room_id

            # Trận bắt đầu: backend gửi COUNTDOWN_START kèm đề bài (hoặc ROOM_STATE PLAYING khi vào lại phòng).
            started = None
            if event == "COUNTDOWN_START" and isinstance(data.get("question"), dict):
                started = {"question": data["question"], "room_id": room_id}
            elif event == "ROOM_STATE" and data.get("status") == "PLAYING" and data.get("question"):
                started = {"question": data["question"], "room_id": room_id}
            if fighter is None and started and started["room_id"]:
                fighter = asyncio.create_task(fight(base, token, ws, started, args))

            if event in ("GAME_OVER", "MATCH_DRAW", "ROOM_CANCELLED"):
                log(f"Trận kết thúc: {event} {json.dumps(data, ensure_ascii=False)[:200]}")
                break

    if fighter:
        fighter.cancel()


def main():
    parser = argparse.ArgumentParser(description="Bot đối thủ để test trận đấu CodeDuel.")
    parser.add_argument("command", choices=["queue", "create", "join"])
    parser.add_argument("code", nargs="?", help="Mã phòng 6 ký tự (khi dùng 'join')")
    parser.add_argument("--mode", choices=["win", "lose", "idle"], default="win")
    parser.add_argument("--delay", type=int, default=30, help="Số giây bot chờ rồi mới nộp bài")
    parser.add_argument("--user", default="bot_duel")
    parser.add_argument("--password", default="Password123")
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    if args.command == "join" and not args.code:
        parser.error("Lệnh 'join' cần mã phòng, ví dụ: python duel_bot.py join ABC123")
    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        log("Đã dừng bot.")


if __name__ == "__main__":
    main()
