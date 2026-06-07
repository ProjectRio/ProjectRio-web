#!/usr/bin/env python3
"""
Benchmark the /games/ endpoint against a running server.

Usage:
    # Run a benchmark and save results
    python scripts/bench_games.py --base-url http://127.0.0.1:5000 --label main

    # Compare two saved result files
    python scripts/bench_games.py --compare scripts/bench_results/20260607_120000_main.json \\
                                             scripts/bench_results/20260607_130000_optimized.json

Results are saved to scripts/bench_results/<timestamp>_<label>.json (git-ignored).
"""

import argparse
import json
import math
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

RESULTS_DIR = Path(__file__).parent / "bench_results"
DEFAULT_WARMUP = 3
DEFAULT_RUNS = 20


# ---------------------------------------------------------------------------
# Stats helpers
# ---------------------------------------------------------------------------

def _percentile(sorted_data, p):
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * p / 100
    lo, hi = int(k), math.ceil(k)
    if lo == hi:
        return sorted_data[lo]
    return sorted_data[lo] + (sorted_data[hi] - sorted_data[lo]) * (k - lo)


def _stats(times):
    s = sorted(times)
    return {
        'mean_ms': statistics.mean(s),
        'p50_ms': _percentile(s, 50),
        'p95_ms': _percentile(s, 95),
        'p99_ms': _percentile(s, 99),
        'min_ms': s[0],
        'max_ms': s[-1],
        'stddev_ms': statistics.stdev(s) if len(s) > 1 else 0.0,
    }


# ---------------------------------------------------------------------------
# Core benchmark
# ---------------------------------------------------------------------------

def _timed_get(session, url, params):
    t0 = time.perf_counter()
    r = session.get(url, params=params, timeout=60)
    return r, (time.perf_counter() - t0) * 1000


def run_scenario(session, base_url, name, path, params, warmup, runs):
    url = base_url.rstrip('/') + path
    print(f"  {name:50s} ", end='', flush=True)

    for _ in range(warmup):
        try:
            _timed_get(session, url, params)
        except Exception:
            pass
        print('.', end='', flush=True)
    print(' | ', end='', flush=True)

    times, failures = [], 0
    for _ in range(runs):
        try:
            r, ms = _timed_get(session, url, params)
            if r.status_code == 200:
                times.append(ms)
                print('✓', end='', flush=True)
            else:
                failures += 1
                print('✗', end='', flush=True)
        except Exception:
            failures += 1
            print('!', end='', flush=True)
    print()

    result = {'name': name, 'params': params or {}, 'n_ok': len(times), 'n_fail': failures}
    if times:
        result.update(_stats(times))
    else:
        result['error'] = 'all_failed'
    return result


# ---------------------------------------------------------------------------
# Scenario discovery
# ---------------------------------------------------------------------------

BENCH_USERNAME = 'MattGree'


def build_scenarios(session, base_url, include_no_limit):
    username = BENCH_USERNAME
    print(f"  username={username!r}\n")

    S13 = 'S13SuperstarsOff'

    scenarios = [
        # (display name,                           path,      params)

        # --- No tag filter (full dataset) ---
        ('default (limit 50)',                     '/games/', None),
        ('limit 10',                               '/games/', {'limit_games': '10'}),
        ('limit 500',                              '/games/', {'limit_games': '500'}),
        ('include_linescore',                      '/games/', {'limit_games': '50', 'include_linescore': '1'}),
        ('include_scoring_plays',                  '/games/', {'limit_games': '50', 'include_scoring_plays': '1'}),
        ('linescore + scoring_plays',              '/games/', {'limit_games': '50', 'include_linescore': '1', 'include_scoring_plays': '1'}),

        # --- S13SuperstarsOff (stable completed season) ---
        ('S13 default (limit 50)',                 '/games/', {'tag': S13}),
        ('S13 limit 500',                          '/games/', {'tag': S13, 'limit_games': '500'}),
        ('S13 linescore + scoring_plays',          '/games/', {'tag': S13, 'limit_games': '50', 'include_linescore': '1', 'include_scoring_plays': '1'}),
    ]

    if username:
        scenarios.append((f'username={username}',      '/games/', {'username': username, 'limit_games': '50'}))
        scenarios.append((f'S13 username={username}',  '/games/', {'tag': S13, 'username': username, 'limit_games': '50'}))

    if include_no_limit:
        scenarios.append(('no limit (all games)', '/games/', {'limit_games': 'False'}))

    return scenarios


# ---------------------------------------------------------------------------
# Output: table
# ---------------------------------------------------------------------------

def _print_table(results):
    col_w = max(len(r['name']) for r in results) + 2
    hdr = f"  {'Scenario':<{col_w}} {'Mean':>8}  {'p50':>8}  {'p95':>8}  {'p99':>8}  {'Min':>8}  {'Max':>8}  {'OK/N':>6}"
    print(hdr)
    print('  ' + '-' * (len(hdr) - 2))
    for r in results:
        total = r['n_ok'] + r['n_fail']
        if 'error' in r:
            print(f"  {r['name']:<{col_w}}  FAILED ({r['n_fail']} errors)")
            continue
        print(
            f"  {r['name']:<{col_w}}"
            f" {r['mean_ms']:>7.0f}ms"
            f"  {r['p50_ms']:>7.0f}ms"
            f"  {r['p95_ms']:>7.0f}ms"
            f"  {r['p99_ms']:>7.0f}ms"
            f"  {r['min_ms']:>7.0f}ms"
            f"  {r['max_ms']:>7.0f}ms"
            f"  {r['n_ok']}/{total}"
        )


# ---------------------------------------------------------------------------
# Compare two result files
# ---------------------------------------------------------------------------

def _delta_str(a, b):
    if a == 0:
        return '  n/a'
    pct = (b - a) / a * 100
    sign = '+' if pct >= 0 else ''
    # green for improvements (negative), red for regressions (positive) when run in a terminal
    color = '\033[92m' if pct < -2 else ('\033[91m' if pct > 2 else '')
    reset = '\033[0m' if color else ''
    return f"{color}{sign}{pct:5.1f}%{reset}"


def compare_results(file_a, file_b):
    with open(file_a) as f:
        data_a = json.load(f)
    with open(file_b) as f:
        data_b = json.load(f)

    label_a = data_a['meta']['label']
    label_b = data_b['meta']['label']

    print(f"\nComparing runs:")
    print(f"  A ({label_a}):  {data_a['meta']['timestamp']}  →  {file_a}")
    print(f"  B ({label_b}):  {data_b['meta']['timestamp']}  →  {file_b}")
    print(f"\n  Negative Δ = faster in B. Positive Δ = slower in B.\n")

    by_name_a = {r['name']: r for r in data_a['scenarios']}
    by_name_b = {r['name']: r for r in data_b['scenarios']}
    all_names = list(dict.fromkeys(list(by_name_a) + list(by_name_b)))
    col_w = max(len(n) for n in all_names) + 2

    hdr = (f"  {'Scenario':<{col_w}}"
           f"  {'A mean':>9}  {'B mean':>9}  {'Δ mean':>8}"
           f"  {'A p95':>8}  {'B p95':>8}  {'Δ p95':>8}")
    print(hdr)
    print('  ' + '-' * (len(hdr) - 2))

    for name in all_names:
        ra = by_name_a.get(name)
        rb = by_name_b.get(name)
        if not ra or not rb or 'error' in ra or 'error' in rb:
            print(f"  {name:<{col_w}}  (missing or failed in one run)")
            continue
        print(
            f"  {name:<{col_w}}"
            f"  {ra['mean_ms']:>8.0f}ms  {rb['mean_ms']:>8.0f}ms  {_delta_str(ra['mean_ms'], rb['mean_ms']):>8}"
            f"  {ra['p95_ms']:>7.0f}ms  {rb['p95_ms']:>7.0f}ms  {_delta_str(ra['p95_ms'], rb['p95_ms']):>8}"
        )

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Benchmark /games/ endpoint',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--base-url', default='http://127.0.0.1:5000',
                        help='Server base URL (default: http://127.0.0.1:5000)')
    parser.add_argument('--label', default='run',
                        help='Label for this run, e.g. "main" or "optimized"')
    parser.add_argument('--warmup', type=int, default=DEFAULT_WARMUP,
                        help=f'Warmup requests per scenario (default: {DEFAULT_WARMUP})')
    parser.add_argument('--runs', type=int, default=DEFAULT_RUNS,
                        help=f'Timed requests per scenario (default: {DEFAULT_RUNS})')
    parser.add_argument('--include-no-limit', action='store_true',
                        help='Add a no-limit (all games) scenario — may be slow on large DBs')
    parser.add_argument('--compare', nargs=2, metavar=('FILE_A', 'FILE_B'),
                        help='Compare two saved result files instead of running a benchmark')
    args = parser.parse_args()

    if args.compare:
        compare_results(*args.compare)
        return

    RESULTS_DIR.mkdir(exist_ok=True)

    session = requests.Session()

    # Sanity check: server must be reachable before we start
    try:
        probe = session.get(args.base_url.rstrip('/') + '/games/', params={'limit_games': '1'}, timeout=120)
        probe.raise_for_status()
    except Exception as e:
        print(f"Error: cannot reach {args.base_url}: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nBenchmarking  {args.base_url}  (label={args.label!r})")
    print(f"Warmup: {args.warmup} requests  |  Timed: {args.runs} requests per scenario")
    print(f"Key: . = warmup  ✓ = ok  ✗ = non-200  ! = exception\n")

    scenarios = build_scenarios(session, args.base_url, args.include_no_limit)

    print("Running:")
    results = [
        run_scenario(session, args.base_url, name, path, params, args.warmup, args.runs)
        for name, path, params in scenarios
    ]

    print("\nResults (all times in ms):")
    _print_table(results)

    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    safe_label = args.label.replace('/', '-').replace(' ', '_')
    out_path = RESULTS_DIR / f"{ts}_{safe_label}.json"

    payload = {
        'meta': {
            'label': args.label,
            'base_url': args.base_url,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'warmup_runs': args.warmup,
            'timed_runs': args.runs,
        },
        'scenarios': results,
    }

    with open(out_path, 'w') as f:
        json.dump(payload, f, indent=2)

    print(f"\nSaved → {out_path}")
    print(f"\nTo compare with another run:")
    print(f"  python scripts/bench_games.py --compare {out_path} <other_result.json>")


if __name__ == '__main__':
    main()
