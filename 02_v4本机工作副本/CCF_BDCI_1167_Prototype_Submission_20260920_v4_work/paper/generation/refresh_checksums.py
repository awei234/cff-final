"""Sync every CHECKSUMS.sha256 entry under paper/ with the actual files.

Idempotent: run it after any change under paper/ (source, PDF, records).
Stale paper/ entries whose file no longer exists are dropped.

Usage: python refresh_checksums.py
"""
import hashlib
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CHECKSUMS = os.path.join(ROOT, "CHECKSUMS.sha256")
PREFIX = "paper/"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    lines = io.open(CHECKSUMS, encoding="utf-8").read().splitlines()
    entries = []
    for line in lines:
        if not line.strip():
            continue
        digest, rel = line.split("  ", 1)
        if rel.startswith(PREFIX):
            continue  # rebuilt below
        entries.append((rel, digest.lower()))

    index = {rel for rel, _ in entries}
    rebuilt = []
    for dirpath, _dirnames, filenames in os.walk(os.path.join(ROOT, "paper")):
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
            if rel in index:
                raise SystemExit("duplicate entry outside paper/: " + rel)
            rebuilt.append((rel, sha256_file(path)))

    rebuilt.sort()
    entries.extend(rebuilt)

    with io.open(CHECKSUMS, "w", encoding="utf-8", newline="\n") as fh:
        for rel, digest in entries:
            fh.write("%s  %s\n" % (digest, rel))

    print("paper/ entries synced:", len(rebuilt))
    for rel, digest in rebuilt:
        print("  %s  %s" % (digest, rel))
    print("total entries:", len(entries))


if __name__ == "__main__":
    main()
