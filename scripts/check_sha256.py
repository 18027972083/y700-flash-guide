#!/usr/bin/env python3
"""Verify a large flash package against its internal SHA256SUMS.txt manifest.

Works directly on the distributed zip (no need to extract first). Streams file
contents in 8 MiB chunks so memory usage stays flat on multi-GB packages.

Usage:
  python check_sha256.py --zip PACKAGE.zip --sums SHA256SUMS.txt [--prefix SUBDIR/]

Exit code 0 = PASS (all files match, no extras), 1 = FAIL.
"""
import argparse
import hashlib
import os
import sys
import zipfile


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify zip contents against a SHA256SUMS manifest.")
    ap.add_argument("--zip", required=True, help="the package zip file")
    ap.add_argument("--sums", required=True, help="SHA256SUMS.txt (digest + relative path per line)")
    ap.add_argument("--prefix", default=None,
                    help="path prefix inside the zip to strip (default: auto-detect common prefix)")
    args = ap.parse_args()

    expected = {}
    with open(args.sums, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            digest, path = line.split(None, 1)
            expected[path.lstrip("./")] = digest

    z = zipfile.ZipFile(args.zip)
    names = [n for n in z.namelist() if not n.endswith("/")]
    prefix = args.prefix if args.prefix is not None else os.path.commonprefix(names)
    print("zip entries: %d, manifest entries: %d, prefix: %r" % (len(names), len(expected), prefix), flush=True)

    ok = 0
    bad = []
    missing = []
    total_bytes = 0
    for i, name in enumerate(names):
        rel = name[len(prefix):] if prefix and name.startswith(prefix) else name
        if rel not in expected:
            missing.append(rel)
            continue
        h = hashlib.sha256()
        with z.open(name) as f:
            while chunk := f.read(8 * 1024 * 1024):
                h.update(chunk)
                total_bytes += len(chunk)
        got = h.hexdigest()
        if got != expected[rel]:
            bad.append((rel, got, expected[rel]))
            print("MISMATCH %s\n  got %s\n  exp %s" % (rel, got, expected[rel]), flush=True)
        else:
            ok += 1
        if (i + 1) % 10 == 0:
            print("... %d/%d files, %.2f GB hashed" % (i + 1, len(names), total_bytes / 1e9), flush=True)

    print()
    print("RESULT: ok=%d bad=%d not-in-manifest=%d" % (ok, len(bad), len(missing)))
    if missing:
        print("not in manifest:", missing)
    print("VERDICT:", "PASS" if not bad and not missing else "FAIL")
    return 0 if not bad and not missing else 1


if __name__ == "__main__":
    sys.exit(main())
