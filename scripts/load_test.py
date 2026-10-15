#!/usr/bin/env python3
"""
Simple latency check for NFR-01 (p95 < 1 s). Standard library only.

Start the API first (scripts/start_api.*), then:
    python scripts/load_test.py --requests 50 --concurrency 5
"""
import argparse
import statistics
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ENDPOINTS = ["/api/overview", "/api/trends", "/api/sla-performance", "/api/root-causes",
             "/api/team-performance", "/api/customer-analysis", "/api/tickets"]
QS = "?start_date=2025-07-01&end_date=2025-12-31"


def hit(url: str) -> tuple[float, int]:
    t0 = time.perf_counter()
    with urllib.request.urlopen(url, timeout=30) as r:
        r.read()
        status = r.status
    return (time.perf_counter() - t0) * 1000, status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--requests", type=int, default=30, help="requests per endpoint")
    ap.add_argument("--concurrency", type=int, default=4)
    a = ap.parse_args()
    print(f"{'endpoint':28s} {'p50 ms':>8s} {'p95 ms':>8s} {'max ms':>8s}  status")
    worst = 0.0
    for ep in ENDPOINTS:
        url = a.base + ep + QS
        with ThreadPoolExecutor(a.concurrency) as pool:
            res = list(pool.map(hit, [url] * a.requests))
        ms = sorted(r[0] for r in res)
        p95 = ms[max(0, int(round(0.95 * len(ms))) - 1)]
        worst = max(worst, p95)
        print(f"{ep:28s} {statistics.median(ms):8.0f} {p95:8.0f} {ms[-1]:8.0f}  {set(r[1] for r in res)}")
    print(f"\nWorst p95: {worst:.0f} ms -> NFR-01 {'PASS' if worst < 1000 else 'FAIL'} (target < 1000 ms)")


if __name__ == "__main__":
    main()
