#!/usr/bin/env python3
"""Segmented parallel downloader for large firmware files (HTTP Range based).

Splits the file into N segments fetched by a thread pool with per-segment
resume and exponential backoff, then merges and size-verifies. Segments live
in <out>.segs/ and are cleaned up on success, so a rerun resumes instead of
redownloading.

Usage:
  python dl_official.py --url URL --out FILE.7z [--segments 256] [--workers 12]
                        [--size BYTES]   # only needed if the server ignores HEAD
"""
import argparse
import os
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


def probe_size(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return int(r.headers.get("Content-Length", 0)) or None
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Segmented parallel downloader with resume.")
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", required=True, help="merged output file path")
    ap.add_argument("--segments", type=int, default=256)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--size", type=int, default=None, help="total size in bytes (fallback if HEAD fails)")
    args = ap.parse_args()

    total = args.size or probe_size(args.url)
    if not total:
        print("cannot determine file size: HEAD failed and --size not given")
        return 2
    seg_dir = args.out + ".segs"
    os.makedirs(seg_dir, exist_ok=True)
    seg = (total + args.segments - 1) // args.segments
    lock = threading.Lock()
    done = [0]
    t0 = time.time()

    def seg_path(i):
        return os.path.join(seg_dir, "s%04d" % i)

    def fetch(i) -> bool:
        want = min((i + 1) * seg, total) - i * seg
        p = seg_path(i)
        if os.path.exists(p) and os.path.getsize(p) == want:
            with lock:
                done[0] += want
            return True
        for attempt in range(15):
            try:
                have = os.path.getsize(p) if os.path.exists(p) else 0
                if have >= want:
                    with lock:
                        done[0] += want
                    return True
                start = i * seg
                end = min((i + 1) * seg, total) - 1
                req = urllib.request.Request(args.url, headers={
                    "Range": "bytes=%d-%d" % (start + have, end),
                    "User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=40) as r, open(p, "ab") as f:
                    while chunk := r.read(256 * 1024):
                        f.write(chunk)
                        with lock:
                            done[0] += len(chunk)
                if os.path.getsize(p) == want:
                    return True
            except Exception:
                time.sleep(min(2 ** min(attempt, 5), 20))
        return False

    def progress() -> None:
        while True:
            time.sleep(60)
            elapsed = time.time() - t0
            with lock:
                d = done[0]
            if elapsed > 0:
                speed = d / elapsed / 1048576
                print("progress %d/%d MB (%.1f%%) %.2f MB/s, ETA %.0f min" % (
                    d // 1048576, total // 1048576, d * 100.0 / total, speed,
                    (total - d) / max(d / elapsed, 1) / 60), flush=True)

    threading.Thread(target=progress, daemon=True).start()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        results = list(ex.map(fetch, range(args.segments)))

    bad = [i for i, ok in enumerate(results) if not ok]
    if bad:
        print("FAILED segs:", bad)
        return 1

    print("merging...", flush=True)
    with open(args.out, "wb") as out:
        for i in range(args.segments):
            with open(seg_path(i), "rb") as f:
                while chunk := f.read(8 * 1024 * 1024):
                    out.write(chunk)
    print("merged ->", args.out, os.path.getsize(args.out), "expect", total, flush=True)
    print("VERIFY:", "PASS" if os.path.getsize(args.out) == total else "FAIL")
    if os.path.getsize(args.out) == total:
        for i in range(args.segments):
            os.remove(seg_path(i))
        os.rmdir(seg_dir)
        print("segs cleaned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
