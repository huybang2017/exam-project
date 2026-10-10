"""Kịch bản đo tải cho hệ thống thi trực tuyến (asyncio + httpx).

Chạy (khi API đang bật và đã seed đủ sinh viên, nhớ RATE_LIMIT_ENABLED=false):

    python -m bench.load_test io     --base http://localhost:8000 --n 200
    python -m bench.load_test exam   --base http://localhost:8000 --users 100 --exam-id 1
    python -m bench.load_test resume --base http://localhost:8000 --users 100 --repeat 20 --exam-id 1
    python -m bench.load_test ws     --base http://localhost:8000 --users 100 --hold 15 --exam-id 1

Mỗi lần chạy `exam`/`resume`/`ws` tự tạo một đề mới (sao chép câu hỏi từ --exam-id) nên chạy lại bao nhiêu lần
cũng được mà không cần seed lại.
Tỉ lệ lỗi = phản hồi 5xx + timeout + lỗi kết nối; mã 4xx ngoài dự kiến được báo riêng ("4xx").
"""
import argparse
import asyncio
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

import httpx


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, round(p / 100 * (len(s) - 1)))]


class Stats:
    def __init__(self) -> None:
        self.lat: dict[str, list[float]] = defaultdict(list)
        self.errors: dict[str, int] = defaultdict(int)
        self.bad4xx: dict[str, int] = defaultdict(int)

    def report(self, wall: float) -> None:
        print(f"\n{'endpoint':<14}{'n':>6}{'p50 ms':>10}{'p95 ms':>10}{'p99 ms':>10}{'5xx/timeout':>13}{'4xx':>6}")
        total = 0
        for name, lat in self.lat.items():
            total += len(lat)
            print(f"{name:<14}{len(lat):>6}{percentile(lat, 50) * 1000:>10.1f}{percentile(lat, 95) * 1000:>10.1f}"
                  f"{percentile(lat, 99) * 1000:>10.1f}{self.errors[name]:>13}{self.bad4xx[name]:>6}")
        errs = sum(self.errors.values())
        print(f"\nTổng {total} request trong {wall:.2f}s -> {total / wall:.1f} RPS; "
              f"lỗi 5xx/timeout: {errs} ({errs / max(total, 1) * 100:.2f}%)")


async def timed(client: httpx.AsyncClient, stats: Stats, name: str, method: str, url: str, **kw) -> httpx.Response | None:
    start = time.perf_counter()
    try:
        r = await client.request(method, url, **kw)
    except httpx.HTTPError:
        stats.lat[name].append(time.perf_counter() - start)
        stats.errors[name] += 1
        return None
    stats.lat[name].append(time.perf_counter() - start)
    if r.status_code >= 500:
        stats.errors[name] += 1
    elif r.status_code >= 400:
        stats.bad4xx[name] += 1
    return r


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def login(client, stats, username: str, password: str, name: str = "login") -> str | None:
    r = await timed(client, stats, name, "POST", "/api/auth/login", data={"username": username, "password": password})
    return r.json()["access_token"] if r is not None and r.status_code == 200 else None


# ---------------------------------------------------------------- io
async def scenario_io(base: str, n: int) -> None:
    async with httpx.AsyncClient(base_url=base, timeout=60, limits=httpx.Limits(max_connections=n + 10)) as client:
        for path in ("/api/demo/sync-io", "/api/demo/async-io"):
            stats = Stats()
            start = time.perf_counter()
            await asyncio.gather(*(timed(client, stats, path.rsplit("/", 1)[1], "GET", path) for _ in range(n)))
            print(f"\n== {path} ({n} request đồng thời)")
            stats.report(time.perf_counter() - start)


# ---------------------------------------------------------------- chuẩn bị đề mới + đăng nhập
async def prepare(client, stats: Stats, users: int, template_exam_id: int):
    teacher = await login(client, stats, "teacher01", "Teacher@123", name="login-teacher")
    if teacher is None:
        raise SystemExit("Không đăng nhập được teacher01 - đã chạy `python -m app.seed` chưa?")
    r = await client.get(f"/api/exams/{template_exam_id}", headers=auth(teacher))
    r.raise_for_status()
    template = r.json()
    now = datetime.now(UTC)
    r = await client.post("/api/exams", headers=auth(teacher), json={
        "title": f"Bench {now:%H:%M:%S}", "duration_minutes": 60,
        "start_time": (now - timedelta(minutes=5)).isoformat(), "end_time": (now + timedelta(days=1)).isoformat(),
        "items": [{"question_id": q["id"]} for q in template["questions"]],
    })
    r.raise_for_status()
    exam_id = r.json()["id"]
    (await client.post(f"/api/exams/{exam_id}/publish", headers=auth(teacher))).raise_for_status()
    detail = (await client.get(f"/api/exams/{exam_id}", headers=auth(teacher))).json()
    correct = {c["id"] for q in detail["questions"] for c in q["choices"] if c["is_correct"]}

    tokens = await asyncio.gather(*(login(client, stats, f"student{i:02d}", "Student@123") for i in range(1, users + 1)))
    if None in tokens:
        raise SystemExit("Có sinh viên không đăng nhập được - seed đủ sinh viên chưa (python -m app.seed N)?")
    return exam_id, tokens, correct


# ---------------------------------------------------------------- exam
async def one_student(client, stats: Stats, exam_id: int, idx: int, token: str, correct: set[int], mismatches: list):
    h = auth(token)
    r = await timed(client, stats, "start", "POST", f"/api/exams/{exam_id}/attempts", headers=h)
    if r is None or r.status_code >= 400:
        return
    attempt = r.json()
    qs = attempt["questions"]
    picks = [(q["id"], q["choices"][(idx + n) % len(q["choices"])]["id"]) for n, q in enumerate(qs)]
    step = max(1, len(picks) // 3)
    for i in range(0, len(picks), step):  # lưu dần như autosave thật
        chunk = [{"question_id": q, "choice_id": c} for q, c in picks[i:i + step]]
        await timed(client, stats, "answers", "PUT", f"/api/attempts/{attempt['id']}/answers", headers=h, json={"answers": chunk})
    r = await timed(client, stats, "submit", "POST", f"/api/attempts/{attempt['id']}/submit", headers=h)
    if r is not None and r.status_code == 200:
        points = {q["id"]: q["points"] for q in qs}
        expected = round(sum(points[q] for q, c in picks if c in correct) / sum(points.values()) * 10, 2)
        if abs(r.json()["score"] - expected) > 1e-9:
            mismatches.append((idx, expected, r.json()["score"]))


async def scenario_exam(base: str, users: int, template: int) -> None:
    limits = httpx.Limits(max_connections=users + 20)
    async with httpx.AsyncClient(base_url=base, timeout=120, limits=limits) as client:
        stats = Stats()
        t0 = time.perf_counter()
        exam_id, tokens, correct = await prepare(client, stats, users, template)
        print(f"Chuẩn bị xong (đề #{exam_id}, {users} sinh viên đã đăng nhập) sau {time.perf_counter() - t0:.2f}s")
        mismatches: list = []
        start = time.perf_counter()
        await asyncio.gather(*(one_student(client, stats, exam_id, i, t, correct, mismatches) for i, t in enumerate(tokens)))
        wall = time.perf_counter() - start
        print(f"\n== Luồng thi đầy đủ, {users} sinh viên đồng thời (không tính bước đăng nhập vào thời gian toàn bộ)")
        stats.report(wall)
        print(f"Chấm sai so với tính tay: {len(mismatches)} / {users}  {mismatches[:3] if mismatches else ''}")


# ---------------------------------------------------------------- resume
async def scenario_resume(base: str, users: int, repeat: int, template: int) -> None:
    limits = httpx.Limits(max_connections=users + 20)
    async with httpx.AsyncClient(base_url=base, timeout=120, limits=limits) as client:
        stats = Stats()
        exam_id, tokens, _ = await prepare(client, stats, users, template)
        stats.lat.clear()
        starts = await asyncio.gather(*(client.post(f"/api/exams/{exam_id}/attempts", headers=auth(t)) for t in tokens))
        attempts = [s.json()["id"] for s in starts]

        async def refresh(token: str, attempt_id: int):
            for _ in range(repeat):
                await timed(client, stats, "get_attempt", "GET", f"/api/attempts/{attempt_id}", headers=auth(token))

        start = time.perf_counter()
        await asyncio.gather(*(refresh(t, a) for t, a in zip(tokens, attempts)))
        print(f"\n== resume: {users} sinh viên x {repeat} lần tải lại bài làm")
        stats.report(time.perf_counter() - start)


# ---------------------------------------------------------------- ws
async def scenario_ws(base: str, users: int, hold: float, template: int) -> None:
    import websockets

    limits = httpx.Limits(max_connections=users + 20)
    async with httpx.AsyncClient(base_url=base, timeout=120, limits=limits) as client:
        stats = Stats()
        exam_id, tokens, _ = await prepare(client, stats, users, template)
        starts = await asyncio.gather(*(client.post(f"/api/exams/{exam_id}/attempts", headers=auth(t)) for t in tokens))
        attempts = [s.json()["id"] for s in starts]
    ws_base = base.replace("http://", "ws://").replace("https://", "wss://")
    counts: list[int] = []

    async def hold_socket(token: str, attempt_id: int):
        n = 0
        try:
            async with websockets.connect(f"{ws_base}/ws/attempts/{attempt_id}?token={token}") as ws:
                end = time.monotonic() + hold
                while time.monotonic() < end:
                    await asyncio.wait_for(ws.recv(), timeout=5)
                    n += 1
        except Exception as exc:  # noqa: BLE001
            print("WebSocket lỗi:", repr(exc))
        counts.append(n)

    print(f"Mở {users} WebSocket và giữ {hold:.0f}s ... (lúc này hãy đếm kết nối PostgreSQL ở terminal khác)")
    await asyncio.gather(*(hold_socket(t, a) for t, a in zip(tokens, attempts)))
    print(f"WebSocket thành công: {sum(1 for c in counts if c > 0)}/{users}; "
          f"số thông điệp 'remaining' trung bình mỗi WebSocket: {sum(counts) / max(len(counts), 1):.1f}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scenario", choices=["io", "exam", "resume", "ws"])
    p.add_argument("--base", default="http://localhost:8000")
    p.add_argument("--n", type=int, default=200, help="io: số request mỗi endpoint")
    p.add_argument("--users", type=int, default=50)
    p.add_argument("--repeat", type=int, default=20, help="resume: số lần tải lại mỗi sinh viên")
    p.add_argument("--hold", type=float, default=15, help="ws: số giây giữ kết nối")
    p.add_argument("--exam-id", type=int, default=1, help="đề mẫu để sao chép câu hỏi")
    a = p.parse_args()
    if a.scenario == "io":
        asyncio.run(scenario_io(a.base, a.n))
    elif a.scenario == "exam":
        asyncio.run(scenario_exam(a.base, a.users, a.exam_id))
    elif a.scenario == "resume":
        asyncio.run(scenario_resume(a.base, a.users, a.repeat, a.exam_id))
    else:
        asyncio.run(scenario_ws(a.base, a.users, a.hold, a.exam_id))


if __name__ == "__main__":
    main()
